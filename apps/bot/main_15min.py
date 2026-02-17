"""
15-min signal engine entrypoint.
Separate process from the 5-min bot. Runs Polymarket WS, RTDS, and 500ms signal loop.
"""
import signal
import sys
import time
from loguru import logger

from src.config import CONVEX_URL
from src.database import init_db, is_db_configured, update_system_status, validate_db_schema
from src.log_buffer import start_log_buffer, stop_log_buffer
from src.scanner_15min import fetch_btc_15min_market
from src.signal_engine import run_loop, set_stop
from src.ws_polymarket import start as ws_pm_start, stop as ws_pm_stop
from src.ws_rtds import start as ws_rtds_start, stop as ws_rtds_stop


def main() -> None:
  logger.info("=" * 60)
  logger.info("BTC 15-Minute Signal Engine")
  logger.info("=" * 60)

  init_db()
  start_log_buffer()
  try:
    validate_db_schema()
  except RuntimeError as e:
    logger.error(str(e))
    sys.exit(1)

  if not is_db_configured():
    logger.warning(
      "CONVEX_URL not set - trades will NOT be saved. Set CONVEX_URL in .env.local"
    )

  # Start RTDS for BTC price
  ws_rtds_start()

  # Fetch 15-min market to get token IDs, then start Polymarket WS
  market = fetch_btc_15min_market()
  if market:
    tokens = market.get("tokens") or {}
    yes_id = tokens.get("yes")
    no_id = tokens.get("no")
    if yes_id and no_id:
      ws_pm_start(yes_id, no_id)
    else:
      logger.warning("15-min market has no token IDs - order book unavailable")
  else:
    logger.info("No active 15-min market - will retry when market appears")

  def request_shutdown(*_args) -> None:
    set_stop()

  if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, request_shutdown)
  signal.signal(signal.SIGINT, request_shutdown)

  engine_start_time = time.time()
  try:
    run_loop()
  finally:
    logger.info("Shutting down 15-min engine...")
    update_system_status(
      engine_state="STOPPED",
      uptime_seconds=int(time.time() - engine_start_time),
      scan_interval=900,
      polymarket_ok=False,
      db_ok=is_db_configured(),
      rtds_ok=False,
      key="15min",
    )
    ws_pm_stop()
    ws_rtds_stop()
    stop_log_buffer()
    logger.info("15-min engine stopped")


if __name__ == "__main__":
  main()
