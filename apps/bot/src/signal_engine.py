"""
15-min signal engine. Runs every 500ms.
Priority 1: Mispricing arb (fire immediately)
Priority 2: Whale detection
Priority 3: Order book imbalance
Priority 4: 5-min momentum (confirm only)
Combined entry: P1 always; P2+P3 or P2+P4 or P3+P4 same direction.
"""
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.config import (
  IMBALANCE_THRESHOLD,
  KELLY_FRACTION,
  LAST_SECOND_WINDOW,
  MAX_POSITION_SIZE,
  MISPRICING_THRESHOLD,
  MOMENTUM_LOOKBACK,
)
from src.database import has_open_trade_for_market, is_db_configured, list_last_5m_outcomes, update_system_status
from src.quarter_executor import execute_signal_engine_trade
from src.ws_polymarket import WhaleSignal, get_best_asks, get_imbalance_data, get_whale_signals
from src.utils.rtds_client import get_btc_move_60s, get_latest_btc_usd

_IMBALANCE_SAMPLES = 60  # 60 * 500ms = 30s
_imbalance_history: deque = deque(maxlen=_IMBALANCE_SAMPLES)
_stop_event = threading.Event()


def set_stop() -> None:
  """Signal the run loop to stop."""
  _stop_event.set()
_FAIR_VALUE_UNDER = 0.45  # 5% below fair = 0.45
_LAST_SECOND_START = 40
_LAST_SECOND_END = 25
_STRIKE_NEAR_PCT = 0.002
_BTC_MOVE_PCT = 0.003


@dataclass
class SignalResult:
  fired: bool
  action: Optional[str] = None  # bet_yes, bet_no, bet_both
  signal_type: str = ""
  confidence_layers: int = 0
  reason: str = ""
  price: Optional[float] = None
  yes_price: Optional[float] = None
  no_price: Optional[float] = None


def _position_size(confidence_layers: int) -> float:
  """Fractional Kelly: 1 layer 25%, 2 layers 50%, 3 layers full."""
  if confidence_layers <= 0:
    return 0.0
  pct = 0.25 * (2 ** (confidence_layers - 1))
  return min(1.0, pct) * MAX_POSITION_SIZE


def _check_p1_mispricing(
  yes_ask: Optional[float],
  no_ask: Optional[float],
  stale: bool,
) -> Optional[SignalResult]:
  """Priority 1: Mispricing arb. Fire immediately if found."""
  if stale or yes_ask is None or no_ask is None:
    return None
  total = yes_ask + no_ask
  if total < MISPRICING_THRESHOLD:
    return SignalResult(
      fired=True,
      action="bet_both",
      signal_type="mispricing_arb",
      confidence_layers=3,
      reason=f"YES_ask+NO_ask={total:.4f}<{MISPRICING_THRESHOLD}",
      yes_price=yes_ask,
      no_price=no_ask,
    )
  if yes_ask < _FAIR_VALUE_UNDER:
    return SignalResult(
      fired=True,
      action="bet_yes",
      signal_type="mispricing_one_sided",
      confidence_layers=3,
      reason=f"YES_ask={yes_ask:.4f}<{_FAIR_VALUE_UNDER} (undervalued)",
      price=yes_ask,
    )
  if no_ask < _FAIR_VALUE_UNDER:
    return SignalResult(
      fired=True,
      action="bet_no",
      signal_type="mispricing_one_sided",
      confidence_layers=3,
      reason=f"NO_ask={no_ask:.4f}<{_FAIR_VALUE_UNDER} (undervalued)",
      price=no_ask,
    )
  return None


def _check_p2_whale(signals: List[WhaleSignal]) -> Optional[Tuple[str, bool]]:
  """
  Priority 2: Whale detection. Returns (direction, opposite) or None.
  direction = YES or NO; opposite = True for spoof (trade opposite).
  """
  if not signals:
    return None
  sig = signals[-1]
  direction = sig.direction
  if sig.opposite:
    direction = "NO" if direction == "YES" else "YES"
  return (direction, sig.opposite)


def _check_p3_imbalance(
  imbalance_avg: float,
) -> Optional[str]:
  """Priority 3: Order book imbalance. Returns YES (bullish) or NO (bearish) or None."""
  if imbalance_avg > IMBALANCE_THRESHOLD:
    return "YES"
  if imbalance_avg < -IMBALANCE_THRESHOLD:
    return "NO"
  return None


def _check_p4_momentum() -> Optional[str]:
  """Priority 4: 5-min momentum. Returns YES or NO if 3 consecutive same direction, else None."""
  outcomes = list_last_5m_outcomes(limit=MOMENTUM_LOOKBACK)
  if len(outcomes) < MOMENTUM_LOOKBACK:
    return None
  outcomes = outcomes[:MOMENTUM_LOOKBACK]
  first = outcomes[0].get("outcome", "")
  if not first:
    return None
  if all(o.get("outcome") == first for o in outcomes):
    return first
  return None


def _last_second_gate(
  seconds_left: int,
  btc_spot: Optional[float],
  strike_price: Optional[float],
  market_repriced: bool,
) -> bool:
  """
  In final 25-40s: only allow if (a) BTC within 0.2% of strike, or
  (b) BTC moved >0.3% in 60s and market hasn't repriced.
  Returns True if entry allowed.
  """
  if seconds_left > _LAST_SECOND_START or seconds_left < _LAST_SECOND_END:
    return True
  if btc_spot is None or strike_price is None or strike_price <= 0:
    return False
  near_strike = abs(btc_spot - strike_price) / strike_price <= _STRIKE_NEAR_PCT
  if near_strike:
    return True
  move = get_btc_move_60s()
  if move is not None and abs(move) >= _BTC_MOVE_PCT and not market_repriced:
    return True
  return False


def _run_tick(market: Optional[Dict[str, Any]]) -> None:
  """Single 500ms tick."""
  if market is None:
    return

  slug = market.get("slug") or ""
  if has_open_trade_for_market(slug):
    logger.debug(f"Signal engine: skip {slug} (already have position)")
    return

  yes_ask, no_ask = get_best_asks()
  bid_vol, ask_vol, ob_stale = get_imbalance_data()
  whale_signals = get_whale_signals()

  # Rolling 30s imbalance
  total_vol = bid_vol + ask_vol
  if total_vol > 0:
    imb = (bid_vol - ask_vol) / total_vol
  else:
    imb = 0.0
  _imbalance_history.append(imb)
  imbalance_avg = sum(_imbalance_history) / len(_imbalance_history) if _imbalance_history else imb

  # P1: Mispricing (always fire if found)
  p1 = _check_p1_mispricing(yes_ask, no_ask, ob_stale)
  if p1 and p1.fired:
    size = _position_size(p1.confidence_layers)
    signal = {
      "action": p1.action,
      "price": p1.price or (market.get("yes_price") if p1.action == "bet_yes" else market.get("no_price")),
      "yes_price": p1.yes_price or market.get("yes_price"),
      "no_price": p1.no_price or market.get("no_price"),
      "size": size,
      "expected_profit": size * 0.03 if p1.action == "bet_both" else size * 0.5,
      "confidence": 0.95,
      "reason": p1.reason,
    }
    if p1.action == "bet_both":
      signal["yes_price"] = p1.yes_price
      signal["no_price"] = p1.no_price
    logger.info(f"SIGNAL P1 MISPRICING: {p1.reason} | {slug}")
    execute_signal_engine_trade(
      market,
      signal,
      signal_type=p1.signal_type,
      confidence_layers=p1.confidence_layers,
      market_end_time=market.get("end_date"),
    )
    return

  # P2, P3, P4 for combined entry
  p2 = _check_p2_whale(whale_signals)
  p3_dir = _check_p3_imbalance(imbalance_avg)
  p4_dir = _check_p4_momentum()

  # Combined: need 2+ confirming
  direction = None
  layers = 0
  signal_type_parts = []

  if p2:
    p2_dir = p2[0]
    if direction is None:
      direction = p2_dir
      layers += 1
      signal_type_parts.append("whale")
    elif direction == p2_dir:
      layers += 1
      signal_type_parts.append("whale")
    else:
      direction = None
      layers = 0

  if p3_dir and (direction is None or direction == p3_dir):
    if direction is None:
      direction = p3_dir
    layers += 1
    signal_type_parts.append("imbalance")
  elif p3_dir and direction != p3_dir:
    direction = None
    layers = 0

  if p4_dir and (direction is None or direction == p4_dir):
    if direction is None:
      direction = p4_dir
    layers += 1
    signal_type_parts.append("momentum")
  elif p4_dir and direction != p4_dir:
    direction = None
    layers = 0

  if direction is None or layers < 2:
    btc_spot = get_latest_btc_usd()
    btc_str = f"BTC ${btc_spot:,.2f}" if btc_spot is not None else "BTC=None"
    logger.debug(
      f"Signal engine: no combined entry | {btc_str} | P2={p2} P3={p3_dir} P4={p4_dir} layers={layers} | {slug}"
    )
    return

  # Last-second gate
  seconds_left = market.get("seconds_left", 0)
  strike = market.get("window_start_ts")
  strike_price = None
  if strike is not None:
    from src.utils.rtds_client import get_btc_at_timestamp
    strike_price = get_btc_at_timestamp(strike)
  btc_spot = get_latest_btc_usd()
  if not _last_second_gate(seconds_left, btc_spot, strike_price, market_repriced=False):
    logger.debug(f"Signal engine: last-second gate blocked | {seconds_left}s left | {slug}")
    return

  # Fire
  action = "bet_yes" if direction == "YES" else "bet_no"
  price = market.get("yes_price") if direction == "YES" else market.get("no_price")
  size = _position_size(layers)
  signal_type = "+".join(signal_type_parts) if signal_type_parts else "combined"

  signal = {
    "action": action,
    "price": price,
    "size": size,
    "expected_profit": size * 0.5,
    "confidence": 0.7 + layers * 0.1,
    "reason": f"Combined: {signal_type} ({layers} layers)",
  }

  logger.info(f"SIGNAL COMBINED: {signal_type} {direction} | {slug}")
  execute_signal_engine_trade(
    market,
    signal,
    signal_type=signal_type,
    confidence_layers=layers,
    market_end_time=market.get("end_date"),
  )


def run_loop() -> None:
  """Main 500ms loop. Fetches 15-min market, runs tick."""
  from src.scanner_15min import fetch_btc_15min_market
  from src.settlement import settle_trades
  from src.ws_polymarket import start as ws_pm_start

  logger.info("15-min signal engine started (500ms loop)")
  tick_count = 0
  last_market_refresh = 0.0
  last_status_update = 0.0
  engine_start_time = time.time()
  market: Optional[Dict[str, Any]] = None
  last_slug = ""

  _stop_event.clear()
  while not _stop_event.is_set():
    try:
      now = time.time()
      if now - last_market_refresh > 5.0:
        new_market = fetch_btc_15min_market()
        last_market_refresh = now
        if new_market and new_market.get("slug") != last_slug:
          last_slug = new_market.get("slug", "")
          tokens = new_market.get("tokens") or {}
          yes_id, no_id = tokens.get("yes"), tokens.get("no")
          if yes_id and no_id:
            ws_pm_start(yes_id, no_id)
        market = new_market

      if now - last_status_update > 5.0:
        last_status_update = now
        update_system_status(
          engine_state="SCANNING" if market else "IDLE",
          uptime_seconds=int(now - engine_start_time),
          scan_interval=900,
          polymarket_ok=True,
          db_ok=is_db_configured(),
          rtds_ok=get_latest_btc_usd() is not None,
          key="15min",
        )

      _run_tick(market)
      tick_count += 1
      if tick_count % 200 == 0:
        settle_trades()

      time.sleep(0.5)
    except KeyboardInterrupt:
      break
    except Exception as e:
      logger.exception(f"Signal engine tick error: {e}")
      time.sleep(1.0)
