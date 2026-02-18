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
    logger.debug("Signal engine: order book stale or missing asks, skip tick")
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

      no_start_slugs = [m.get("slug") for m in markets if m.get("start_price") is None]
      if no_start_slugs:
        logger.debug(
          "Signal engine: skip %d markets (no start price yet): %s",
          len(no_start_slugs),
          no_start_slugs,
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
