"""
15-min signal engine. Runs every 500ms.
Single signal: order book imbalance (30s rolling). No mispricing, whale, or 5-min momentum.
"""
import threading
import time
from collections import deque
from typing import Any, Dict, Optional

from loguru import logger

from src.config import IMBALANCE_THRESHOLD, MAX_POSITION_SIZE
from src.database import has_open_trade_for_market, is_db_configured, update_system_status
from src.quarter_executor import execute_signal_engine_trade
from src.ws_polymarket import get_imbalance_data
from src.utils.rtds_client import get_btc_at_timestamp, get_btc_move_60s, get_latest_btc_usd

_IMBALANCE_SAMPLES = 60  # 60 * 500ms = 30s
_imbalance_history: deque = deque(maxlen=_IMBALANCE_SAMPLES)
_stop_event = threading.Event()

# Last-second gate: block entry in the 40s–25s window unless BTC near strike or moved enough
_LAST_SECOND_START = 40
_LAST_SECOND_END = 25
_STRIKE_NEAR_PCT = 0.002
_BTC_MOVE_PCT = 0.003


def set_stop() -> None:
  """Signal the run loop to stop."""
  _stop_event.set()


def _position_size() -> float:
  """Single signal = one layer; use full MAX_POSITION_SIZE or scale down as needed."""
  return MAX_POSITION_SIZE


def _imbalance_direction(imbalance_avg: float) -> Optional[str]:
  """Order book imbalance. Returns YES (bullish) or NO (bearish) or None."""
  if imbalance_avg > IMBALANCE_THRESHOLD:
    return "YES"
  if imbalance_avg < -IMBALANCE_THRESHOLD:
    return "NO"
  return None


def _last_second_gate(
  seconds_left: int,
  btc_spot: Optional[float],
  strike_price: Optional[float],
) -> bool:
  """
  In the 40s–25s window: only allow if (a) BTC within 0.2% of strike, or
  (b) BTC moved >0.3% in 60s. Returns True if entry allowed.
  """
  if seconds_left > _LAST_SECOND_START or seconds_left < _LAST_SECOND_END:
    return True
  if btc_spot is None or strike_price is None or strike_price <= 0:
    return False
  near_strike = abs(btc_spot - strike_price) / strike_price <= _STRIKE_NEAR_PCT
  if near_strike:
    return True
  move = get_btc_move_60s()
  if move is not None and abs(move) >= _BTC_MOVE_PCT:
    return True
  return False


def _run_tick(market: Optional[Dict[str, Any]]) -> None:
  """Single 500ms tick. Only imbalance signal."""
  if market is None:
    return

  slug = market.get("slug") or ""
  if has_open_trade_for_market(slug):
    logger.debug(f"Signal engine: skip {slug} (already have position)")
    return

  bid_vol, ask_vol, ob_stale = get_imbalance_data()
  if ob_stale:
    logger.debug("Signal engine: order book stale, skip tick")
    return

  total_vol = bid_vol + ask_vol
  if total_vol > 0:
    imb = (bid_vol - ask_vol) / total_vol
  else:
    imb = 0.0
  _imbalance_history.append(imb)
  imbalance_avg = sum(_imbalance_history) / len(_imbalance_history) if _imbalance_history else imb

  direction = _imbalance_direction(imbalance_avg)
  if direction is None:
    logger.debug(f"Signal engine: imbalance_avg={imbalance_avg:.3f} (no signal) | {slug}")
    return

  seconds_left = market.get("seconds_left", 0)
  strike = market.get("window_start_ts")
  strike_price = get_btc_at_timestamp(strike) if strike is not None else None
  btc_spot = get_latest_btc_usd()
  if not _last_second_gate(seconds_left, btc_spot, strike_price):
    logger.debug(f"Signal engine: last-second gate blocked | {seconds_left}s left | {slug}")
    return

  action = "bet_yes" if direction == "YES" else "bet_no"
  price = market.get("yes_price") if direction == "YES" else market.get("no_price")
  size = _position_size()

  signal = {
    "action": action,
    "price": price,
    "size": size,
    "expected_profit": size * 0.5,
    "confidence": 0.8,
    "reason": f"imbalance={imbalance_avg:.3f} (threshold={IMBALANCE_THRESHOLD})",
  }

  logger.info(f"SIGNAL IMBALANCE: {direction} | imb={imbalance_avg:.3f} | {slug}")
  execute_signal_engine_trade(
    market,
    signal,
    signal_type="imbalance",
    confidence_layers=1,
    market_end_time=market.get("end_date"),
  )


def run_loop() -> None:
  """Main 500ms loop. Fetches 15-min market, runs tick."""
  from src.scanner_15min import fetch_btc_15min_market
  from src.settlement import settle_trades
  from src.ws_polymarket import start as ws_pm_start

  logger.info("15-min signal engine started (500ms loop, imbalance-only)")
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
