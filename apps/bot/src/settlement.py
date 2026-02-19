"""
Settlement: check resolved markets and calculate realized P&L for trades.
CLOB-first: use get_notifications (type 4 Market Resolved) + get_trades for real trades.
Fallback: RTDS (Chainlink) or Gamma API when CLOB has no resolution.
"""
import re
import time
from datetime import datetime, timezone
import requests
from loguru import logger

from typing import Optional, Tuple, Any, Dict, List

from src.database import (
  is_db_configured,
  list_unsettled_trades,
  get_market_outcome_by_slug,
  insert_market_outcome,
  update_trade_settlement,
)

GAMMA_API = "https://gamma-api.polymarket.com"
_RESOLUTION_RETRIES = 3
_RESOLUTION_RETRY_DELAY = 2
_WINNER_THRESHOLD = 0.98  # treat as resolved when winning side >= this
_RTDS_SETTLE_BUFFER_SEC = 2  # seconds after window end before we resolve via RTDS (allow tick to arrive)


_WINDOW_5M_SEC = 300
_WINDOW_15M_SEC = 900

def _parse_btc_5m_slug(slug: str) -> Tuple[Optional[int], Optional[int]]:
  """Parse btc-updown-5m-{window_start_ts}. Returns (window_start_ts, window_end_ts) or (None, None)."""
  m = re.match(r"btc-updown-5m-(\d+)$", slug or "")
  if not m:
    return None, None
  start_ts = int(m.group(1))
  return start_ts, start_ts + _WINDOW_5M_SEC


def _parse_15m_slug(slug: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
  """Parse {asset}-updown-15m-{window_start_ts}. Returns (asset, window_start_ts, window_end_ts) or (None, None, None)."""
  m = re.match(r"([a-z]+)-updown-15m-(\d+)$", (slug or "").strip().lower())
  if not m:
    return None, None, None
  asset = m.group(1)
  start_ts = int(m.group(2))
  return asset, start_ts, start_ts + _WINDOW_15M_SEC


def resolve_outcome_via_rtds(slug: str) -> dict:
  """
  Resolve market outcome using RTDS (Chainlink) as soon as window end has passed.
  Supports 5m BTC (btc-updown-5m-{ts}) and 15m BTC/ETH/SOL/XRP ({asset}-updown-15m-{ts}).
  Returns dict with resolved: bool, outcome: "YES"|"NO" (if resolved).
  """
  now = time.time()
  window_start_ts = None
  window_end_ts = None
  get_price_fn = None

  start_ts_5m, end_ts_5m = _parse_btc_5m_slug(slug)
  if start_ts_5m is not None and end_ts_5m is not None:
    window_start_ts, window_end_ts = start_ts_5m, end_ts_5m
    try:
      from src.utils.rtds_client import get_btc_at_timestamp
      get_price_fn = get_btc_at_timestamp
    except Exception:
      pass
  else:
    asset, start_ts_15, end_ts_15 = _parse_15m_slug(slug)
    if asset is not None and start_ts_15 is not None and end_ts_15 is not None:
      window_start_ts, window_end_ts = start_ts_15, end_ts_15
      try:
        from src.utils.rtds_client import (
          get_btc_at_timestamp,
          get_eth_at_timestamp,
          get_sol_at_timestamp,
          get_xrp_at_timestamp,
        )
        fns = {"btc": get_btc_at_timestamp, "eth": get_eth_at_timestamp, "sol": get_sol_at_timestamp, "xrp": get_xrp_at_timestamp}
        get_price_fn = fns.get(asset)
      except Exception:
        pass

  if window_start_ts is None or window_end_ts is None or get_price_fn is None:
    return {"resolved": False}
  if now < window_end_ts + _RTDS_SETTLE_BUFFER_SEC:
    return {"resolved": False}
  try:
    start_price = get_price_fn(window_start_ts)
    end_price = get_price_fn(window_end_ts)
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


def _resolve_from_clob_notifications() -> Tuple[Dict[str, str], List]:
  """
  Get market resolutions from CLOB notifications (type 4 = Market Resolved).
  Returns (resolved, to_drop): resolved = condition_id -> outcome; to_drop = notification ids.
  """
  try:
    from src.clob_client import get_notifications
    notifs = get_notifications()
  except Exception:
    return {}, []

  resolved: Dict[str, str] = {}
  to_drop: List = []
  for n in notifs or []:
    if getattr(n, "type", n.get("type")) != 4:
      continue
    payload = getattr(n, "payload", n.get("payload")) or {}
    if not isinstance(payload, dict):
      continue
    cond = payload.get("condition_id") or payload.get("conditionId") or payload.get("market")
    outcome_raw = payload.get("outcome") or payload.get("winner")
    if not cond or not outcome_raw:
      continue
    outcome = "YES" if str(outcome_raw).upper() in ("YES", "1", "UP") else "NO"
    resolved[str(cond)] = outcome
    nid = getattr(n, "id", n.get("id"))
    if nid is not None:
      to_drop.append(nid)
  return resolved, to_drop


def _compute_pnl_from_clob_trade(clob_trade: Any, market_outcome: str) -> float:
  """
  Compute PnL from a single CLOB Trade.
  clob_trade has: outcome (YES/NO), side (BUY/SELL), size, price.
  """
  try:
    size = float(clob_trade.get("size") or 0)
    price = float(clob_trade.get("price") or 0)
  except (TypeError, ValueError):
    return 0.0
  if size <= 0 or price <= 0:
    return 0.0
  side = str(clob_trade.get("side") or "").upper()
  outcome = str(clob_trade.get("outcome") or "").upper()
  if side != "BUY":
    return 0.0
  cost = size * price
  if outcome == "YES":
    if market_outcome == "YES":
      return size * (1.0 - price)
    return -cost
  if outcome == "NO":
    if market_outcome == "NO":
      return size * (1.0 - price)
    return -cost
  return 0.0


def _get_pnl_from_clob_trades(condition_id: str, market_outcome: str, our_order_id: str) -> Optional[float]:
  """
  Fetch our trades from CLOB for this market, match by order_id, sum PnL.
  Returns total PnL or None if no matching trades (use DB fallback).
  """
  try:
    from src.clob_client import get_trades
    trades = get_trades(market=condition_id)
  except Exception:
    return None
  if not trades:
    return None
  total = 0.0
  matched = False
  for t in trades:
    taker_id = t.get("taker_order_id") or ""
    maker_orders = t.get("maker_orders") or []
    if taker_id == our_order_id:
      total += _compute_pnl_from_clob_trade(t, market_outcome)
      matched = True
    else:
      for mo in maker_orders:
        if (mo.get("order_id") or "") == our_order_id:
          total += _compute_pnl_from_clob_trade(t, market_outcome)
          matched = True
          break
  return total if matched else None


def calculate_trade_pnl(trade: Any, market_outcome: str) -> float:
  """
  Calculate actual P&L for a trade.
  trade: dict-like (from Convex) with position_size, size, side, action, price.

  position_size = dollars spent. price = cost per share (0-1).
  Win: payout = (position_size / price) * $1, profit = payout - position_size
  Loss: profit = -position_size
  """
  size = trade.get("position_size") or trade.get("size") or 0
  if size <= 0:
    return 0.0

  bet_side = trade.get("side") or trade.get("action") or ""

  if bet_side == "ARBITRAGE":
    return 0.0

  if bet_side == "YES":
    if market_outcome == "YES":
      price = trade.get("price") or 0.5
      if price <= 0:
        return 0.0
      payout = size / price
      return payout - size
    else:
      return -size

  if bet_side == "NO":
    if market_outcome == "NO":
      price = trade.get("price") or 0.5
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
  CLOB-first: use get_notifications (type 4) + get_trades for real trades.
  Fallback: RTDS or Gamma for resolution; calculate_trade_pnl for paper trades.
  """
  if not is_db_configured():
    return

  unsettled = list_unsettled_trades()
  if not unsettled:
    return

  clob_resolved, notif_ids_to_drop = _resolve_from_clob_notifications()
  settled_any = False
  now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

  slugs = set(t["market_ticker"] for t in unsettled if t.get("market_ticker") and t["market_ticker"] != "unknown")

  for slug in slugs:
    first_trade = next((t for t in unsettled if t.get("market_ticker") == slug), None)
    if not first_trade:
      continue
    condition_id = first_trade.get("condition_id") or ""

    resolution = None
    if condition_id and condition_id in clob_resolved:
      resolution = {"resolved": True, "outcome": clob_resolved[condition_id]}
    if not resolution or not resolution["resolved"]:
      resolution = resolve_outcome_via_rtds(slug)
    if not resolution or not resolution["resolved"]:
      resolution = check_market_resolution(slug)
    if not resolution["resolved"]:
      continue

    outcome = resolution["outcome"]

    existing = get_market_outcome_by_slug(slug)
    if not existing:
      insert_market_outcome(
        slug=slug,
        condition_id=condition_id,
        outcome=outcome,
        resolved_at_ms=now_ms,
      )

    for trade in (t for t in unsettled if t.get("market_ticker") == slug):
      if trade.get("market_outcome"):
        continue
      settled_any = True

      order_id = trade.get("polymarket_order_id")
      if order_id and condition_id:
        pnl_from_clob = _get_pnl_from_clob_trades(condition_id, outcome, order_id)
        actual_pnl = pnl_from_clob if pnl_from_clob is not None else calculate_trade_pnl(trade, outcome)
      else:
        actual_pnl = calculate_trade_pnl(trade, outcome)

      status = "won" if actual_pnl > 0 else "lost"
      update_trade_settlement(
        trade_id=trade["_id"],
        market_outcome=outcome,
        actual_profit=actual_pnl,
        status=status,
        settled_at_ms=now_ms,
      )

      logger.info(
        f"Settled trade #{trade['_id']} | "
        f"Strategy: {trade.get('strategy')} | "
        f"Action: {trade.get('side')} | "
        f"Outcome: {outcome} | "
        f"P&L: ${actual_pnl:.2f} | "
        f"Status: {status.upper()}"
      )

  if settled_any and notif_ids_to_drop:
    try:
      from src.clob_client import drop_notifications
      drop_notifications(notif_ids_to_drop)
    except Exception:
      pass

  if settled_any:
    from src.utils.balance import get_current_balance
    logger.log("BALANCE", f"Current Balance: ${get_current_balance():,.2f}")
