"""
15-min signal engine. Runs every 500ms.
Late Entry V3: enter last 4 min, buy favorite (higher ask = market consensus),
require 30% gap, size by time remaining.
"""
import threading
import time
from typing import Any, Dict, Optional

from loguru import logger

from src.config import (
  LATE_ENTRY_MAX_PRICE,
  LATE_ENTRY_MIN_GAP,
  LATE_ENTRY_SIZE_120_0,
  LATE_ENTRY_SIZE_180_120,
  LATE_ENTRY_SIZE_240_180,
  LATE_ENTRY_WINDOW_SEC,
)
from src.database import has_open_trade_for_market, is_db_configured, update_system_status
from src.quarter_executor import execute_signal_engine_trade
from src.ws_polymarket import get_best_asks, get_imbalance_data
from src.utils.rtds_client import (
  get_latest_btc_usd,
  get_latest_eth_usd,
  get_latest_sol_usd,
  get_latest_xrp_usd,
)

_stop_event = threading.Event()
_ob_skip_log_at: Dict[str, float] = {}  # slug -> last log time (throttle "stale or missing asks")
_OB_SKIP_LOG_INTERVAL = 15.0
# Off-window: only log throttled skip + live prices; approaching/in-window: normal logs
_APPROACH_SEC = 60  # warn when within this many sec of 4min window (240 < sec_left <= 240 + 60)
_OFF_WINDOW_LOG_INTERVAL = 30.0
_APPROACH_WARNING_INTERVAL = 10.0
_last_off_window_log = 0.0
_last_approach_warning = 0.0


def set_stop() -> None:
  """Signal the run loop to stop."""
  _stop_event.set()


def _size_by_time(seconds_left: int) -> float:
  """Size in USD by time bucket: 240-180 -> A, 180-120 -> B, 120-0 -> C."""
  if seconds_left > 180:
    return LATE_ENTRY_SIZE_240_180
  if seconds_left > 120:
    return LATE_ENTRY_SIZE_180_120
  return LATE_ENTRY_SIZE_120_0


def _live_prices_str() -> str:
  """One-line live prices for BTC, ETH, SOL, XRP."""
  btc = get_latest_btc_usd()
  eth = get_latest_eth_usd()
  sol = get_latest_sol_usd()
  xrp = get_latest_xrp_usd()
  parts = []
  parts.append(f"BTC ${btc:,.2f}" if btc is not None else "BTC N/A")
  parts.append(f"ETH ${eth:,.2f}" if eth is not None else "ETH N/A")
  parts.append(f"SOL ${sol:,.2f}" if sol is not None else "SOL N/A")
  parts.append(f"XRP ${xrp:,.4f}" if xrp is not None else "XRP N/A")
  return " | ".join(parts)


def _run_tick(market: Optional[Dict[str, Any]]) -> None:
  """Single 500ms tick. Late Entry V3 only."""
  if market is None:
    return

  tokens = market.get("tokens") or {}
  yes_id = tokens.get("yes")
  no_id = tokens.get("no")
  if not yes_id or not no_id:
    return

  slug = market.get("slug") or ""
  if has_open_trade_for_market(slug):
    logger.debug(f"Signal engine: skip {slug} (already have position)")
    return

  if market.get("start_price") is None:
    return

  seconds_left = market.get("seconds_left", 0)
  if seconds_left > LATE_ENTRY_WINDOW_SEC or seconds_left <= 0:
    return

  yes_ask, no_ask = get_best_asks(yes_id, no_id)
  _, _, ob_stale = get_imbalance_data(yes_id, no_id)
  if ob_stale or yes_ask is None or no_ask is None:
    now = time.time()
    if now - _ob_skip_log_at.get(slug, 0) >= _OB_SKIP_LOG_INTERVAL:
      _ob_skip_log_at[slug] = now
      reason = "stale" if ob_stale else ("missing yes_ask" if yes_ask is None else "missing no_ask")
      logger.debug(f"Signal engine: order book {reason}, skip tick | {slug}")
    return

  if yes_ask > no_ask:
    favorite = "YES"
    favorite_ask = yes_ask
  elif no_ask > yes_ask:
    favorite = "NO"
    favorite_ask = no_ask
  else:
    return

  gap = abs(yes_ask - no_ask)
  if gap < LATE_ENTRY_MIN_GAP:
    logger.debug(f"Signal engine: gap={gap:.2f} < {LATE_ENTRY_MIN_GAP} | {slug}")
    return

  if favorite_ask > LATE_ENTRY_MAX_PRICE:
    logger.debug(f"Signal engine: favorite ask {favorite_ask:.2f} > max {LATE_ENTRY_MAX_PRICE} | {slug}")
    return

  size = _size_by_time(seconds_left)
  action = "bet_yes" if favorite == "YES" else "bet_no"
  price = yes_ask if favorite == "YES" else no_ask

  signal = {
    "action": action,
    "price": price,
    "size": size,
    "expected_profit": size * 0.5,
    "confidence": 0.8,
    "reason": f"late_entry_v3 favorite={favorite} gap={gap:.2f}",
  }

  logger.info(f"SIGNAL LATE_ENTRY_V3: {favorite} | gap={gap:.2f} yes_ask={yes_ask:.2f} no_ask={no_ask:.2f} | {slug}")
  execute_signal_engine_trade(
    market,
    signal,
    signal_type="late_entry_v3",
    confidence_layers=1,
    market_end_time=market.get("end_date"),
  )


def run_loop() -> None:
  """Main 500ms loop. Fetches 15-min markets (BTC, ETH, SOL, XRP), runs tick per market."""
  global _last_off_window_log, _last_approach_warning
  from src.scanner_15min import fetch_15min_markets
  from src.settlement import settle_trades
  from src.ws_polymarket import start as ws_pm_start

  logger.info("15-min signal engine started (500ms loop, Late Entry V3)")
  tick_count = 0
  last_market_refresh = 0.0
  last_status_update = 0.0
  engine_start_time = time.time()
  markets: list = []
  last_subscribed_ids: frozenset = frozenset()

  _stop_event.clear()
  while not _stop_event.is_set():
    try:
      now = time.time()
      if now - last_market_refresh > 5.0:
        new_markets = fetch_15min_markets()
        last_market_refresh = now
        new_ids = frozenset(
          tid
          for m in new_markets
          for tid in ((m.get("tokens") or {}).get("yes"), (m.get("tokens") or {}).get("no"))
          if tid
        )
        if new_ids != last_subscribed_ids:
          last_subscribed_ids = new_ids
          if new_markets:
            ws_pm_start(markets=new_markets)
        markets = new_markets

      if now - last_status_update > 5.0:
        last_status_update = now
        update_system_status(
          engine_state="SCANNING" if markets else "IDLE",
          uptime_seconds=int(now - engine_start_time),
          scan_interval=900,
          polymarket_ok=True,
          db_ok=is_db_configured(),
          rtds_ok=any(
            f() is not None
            for f in (
              get_latest_btc_usd,
              get_latest_eth_usd,
              get_latest_sol_usd,
              get_latest_xrp_usd,
            )
          ),
          key="15min",
        )

      # Markets with start_price: compute if we're in 4min window or approaching
      ready = [m for m in markets if m.get("start_price") is not None]
      in_window = any(
        0 < m.get("seconds_left", 0) <= LATE_ENTRY_WINDOW_SEC for m in ready
      )
      min_sec = min(
        (m.get("seconds_left", 999999) for m in ready), default=999999
      )
      approaching = (
        LATE_ENTRY_WINDOW_SEC < min_sec
        <= LATE_ENTRY_WINDOW_SEC + _APPROACH_SEC
        and not in_window
      )
      off_window = not in_window and len(ready) > 0

      # Off-window: one throttled line (skip + live prices). Approaching: warnings. In-window: normal logs.
      if off_window:
        if now - _last_off_window_log >= _OFF_WINDOW_LOG_INTERVAL:
          _last_off_window_log = now
          sec_until = min_sec - LATE_ENTRY_WINDOW_SEC if min_sec < 999999 else None
          tail = f" | window in {sec_until}s" if sec_until is not None else ""
          logger.info(
            f"Skip - not in 4min trading window | {_live_prices_str()}{tail}"
          )
        if approaching and now - _last_approach_warning >= _APPROACH_WARNING_INTERVAL:
          _last_approach_warning = now
          logger.warning(
            f"Approaching 4min trading window in {min_sec - LATE_ENTRY_WINDOW_SEC}s | {_live_prices_str()}"
          )

      # Only log "no start price" when in or approaching window to avoid log spam
      if in_window or approaching:
        no_start_slugs = [m.get("slug") for m in markets if m.get("start_price") is None]
        if no_start_slugs:
          logger.debug(
            f"Signal engine: skip {len(no_start_slugs)} markets (no start price yet): {no_start_slugs}"
          )

      for market in markets:
        if market.get("start_price") is not None:
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
