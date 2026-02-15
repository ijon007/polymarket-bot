"""
Settlement: check resolved markets and calculate realized P&L for trades.
Uses RTDS (Chainlink) when available to settle as soon as the 5min window ends.
"""
import re
import time
from datetime import datetime, timezone
import requests
from loguru import logger

from typing import Optional, Tuple

from src.database import Session, Trade, MarketOutcome

GAMMA_API = "https://gamma-api.polymarket.com"
_RESOLUTION_RETRIES = 3
_RESOLUTION_RETRY_DELAY = 2
_WINNER_THRESHOLD = 0.98  # treat as resolved when winning side >= this
_RTDS_SETTLE_BUFFER_SEC = 2  # seconds after window end before we resolve via RTDS (allow tick to arrive)


def _parse_btc_5m_slug(slug: str) -> Tuple[Optional[int], Optional[int]]:
  """Parse btc-updown-5m-{window_start_ts}. Returns (window_start_ts, window_end_ts) or (None, None)."""
  m = re.match(r"btc-updown-5m-(\d+)$", slug or "")
  if not m:
    return None, None
  start_ts = int(m.group(1))
  return start_ts, start_ts + 300


def resolve_outcome_via_rtds(slug: str) -> dict:
  """
  Resolve 5min BTC market outcome using RTDS (Chainlink) buffer.
  Use as soon as window end time has passed so we don't wait for Polymarket API.
  Returns dict with resolved: bool, outcome: "YES"|"NO" (if resolved).
  """
  window_start_ts, window_end_ts = _parse_btc_5m_slug(slug)
  if window_start_ts is None or window_end_ts is None:
    return {"resolved": False}
  now = time.time()
  if now < window_end_ts + _RTDS_SETTLE_BUFFER_SEC:
    return {"resolved": False}
  try:
    from src.utils.rtds_client import get_btc_at_timestamp
    start_price = get_btc_at_timestamp(window_start_ts)
    end_price = get_btc_at_timestamp(window_end_ts)
    if start_price is None or end_price is None:
      return {"resolved": False}
    outcome = "YES" if end_price >= start_price else "NO"
    logger.info(f"Market {slug} resolved via RTDS: {outcome} (start=${start_price:,.2f} end=${end_price:,.2f})")
    return {"resolved": True, "outcome": outcome}
  except Exception as e:
    logger.debug(f"RTDS resolution for {slug}: {e}")
    return {"resolved": False}


def check_market_resolution(slug: str) -> dict:
  """
  Check if market has resolved and get outcome.

  Returns dict with:
  - resolved: bool
  - outcome: "YES" or "NO" (if resolved)
  """
  last_err = None
  for attempt in range(_RESOLUTION_RETRIES):
    try:
      resp = requests.get(
        f"{GAMMA_API}/events",
        params={"slug": slug},
        timeout=10
      )
      if resp.status_code != 200:
        return {"resolved": False}

      data = resp.json()
      if not data or len(data) == 0:
        return {"resolved": False}

      event = data[0]
      markets = event.get("markets", [])
      if not markets:
        return {"resolved": False}

      market = markets[0]

      if not market.get("closed"):
        return {"resolved": False}

      # Resolved: outcomePrices show [1,0] or [0,1] - winner is 1
      outcome_prices = market.get("outcomePrices", "")
      if isinstance(outcome_prices, str):
        import json
        s = outcome_prices.strip()
        if s.startswith("["):
          prices = [float(x) for x in json.loads(s)]
        else:
          prices = [float(p.strip()) for p in s.split(",")]
      else:
        prices = [float(p) for p in outcome_prices] if outcome_prices else []

      if len(prices) < 2:
        return {"resolved": False}

      if prices[0] >= _WINNER_THRESHOLD:
        outcome = "YES"
      elif prices[1] >= _WINNER_THRESHOLD:
        outcome = "NO"
      else:
        return {"resolved": False}

      logger.info(f"Market {slug} resolved: {outcome}")
      return {"resolved": True, "outcome": outcome}

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, OSError) as e:
      last_err = e
      if attempt < _RESOLUTION_RETRIES - 1:
        time.sleep(_RESOLUTION_RETRY_DELAY)
      continue
    except Exception as e:
      logger.error(f"Error checking resolution for {slug}: {e}")
      return {"resolved": False}

  logger.warning(f"Resolution check failed for {slug} after {_RESOLUTION_RETRIES} tries: {last_err}")
  return {"resolved": False}


def calculate_trade_pnl(trade: Trade, market_outcome: str) -> float:
  """
  Calculate actual P&L for a trade.

  position_size = dollars spent. price = cost per share (0-1).
  Win: payout = (position_size / price) * $1, profit = payout - position_size
  Loss: profit = -position_size
  """
  size = trade.position_size or trade.size or 0
  if size <= 0:
    return 0.0

  bet_side = trade.side or trade.action or ""

  if bet_side == "ARBITRAGE":
    return 0.0

  if bet_side == "YES":
    if market_outcome == "YES":
      price = trade.price or 0.5
      if price <= 0:
        return 0.0
      payout = size / price
      return payout - size
    else:
      return -size

  if bet_side == "NO":
    if market_outcome == "NO":
      price = trade.price or 0.5
      if price <= 0:
        return 0.0
      payout = size / price
      return payout - size
    else:
      return -size

  return 0.0


def settle_trades():
  """
  Check unsettled trades and calculate P&L for resolved markets.
  Call periodically (e.g. every 60s).
  """
  if not Session:
    return

  session = Session()
  try:
    unsettled = session.query(Trade).filter(Trade.status == "paper").all()

    if not unsettled:
      return

    slugs = set(t.market_ticker for t in unsettled if t.market_ticker and t.market_ticker != "unknown")
    settled_any = False

    for slug in slugs:
      resolution = resolve_outcome_via_rtds(slug)
      if not resolution["resolved"]:
        resolution = check_market_resolution(slug)
      if not resolution["resolved"]:
        continue

      outcome = resolution["outcome"]

      existing = session.query(MarketOutcome).filter_by(slug=slug).first()
      if not existing:
        first_trade = next(t for t in unsettled if t.market_ticker == slug)
        mo = MarketOutcome(
          slug=slug,
          condition_id=first_trade.condition_id or "",
          outcome=outcome,
          resolved_at=datetime.now(timezone.utc)
        )
        session.add(mo)

      for trade in (t for t in unsettled if t.market_ticker == slug):
        if trade.market_outcome:
          continue
        settled_any = True
        actual_pnl = calculate_trade_pnl(trade, outcome)
        trade.market_outcome = outcome
        trade.actual_profit = actual_pnl
        trade.status = "won" if actual_pnl > 0 else "lost"
        trade.settled_at = datetime.now(timezone.utc)

        logger.info(
          f"Settled trade #{trade.id} | "
          f"Strategy: {trade.strategy} | "
          f"Action: {trade.side} | "
          f"Outcome: {outcome} | "
          f"P&L: ${actual_pnl:.2f} | "
          f"Status: {trade.status.upper()}"
        )

    session.commit()

    if settled_any:
      from src.utils.balance import get_current_balance
      logger.log("BALANCE", f"Current Balance: ${get_current_balance():,.2f}")

  except Exception as e:
    logger.error(f"Error settling trades: {e}")
    session.rollback()
  finally:
    session.close()
