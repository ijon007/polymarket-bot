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
from src.scanner_15min import fetch_15min_markets
from src.signal_engine import run_loop, set_stop
from src.ws_polymarket import start as ws_pm_start, stop as ws_pm_stop
from src.utils.rtds_client import start as rtds_start, stop as rtds_stop

logger.level("BALANCE", no=22, color="<cyan>")


def main() -> None:
  logger.info("=" * 60)
  logger.info("15-Minute Signal Engine (BTC, ETH, SOL, XRP)")
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

  # Start RTDS for BTC price (same client as 5-min bot)
  rtds_start()

  # Fetch 15-min markets to get token IDs, then start Polymarket WS
  markets = fetch_15min_markets()
  if markets:
    ws_pm_start(markets=markets)
  else:
    logger.info("No active 15-min markets - will retry when markets appear")

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
    rtds_stop()
    stop_log_buffer()
    logger.info("15-min engine stopped")


if __name__ == "__main__":
  main()
