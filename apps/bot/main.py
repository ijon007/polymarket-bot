import sys
import signal
import time
from loguru import logger
from src.config import SCAN_INTERVAL, STRATEGIES, STRATEGY_PRIORITY
from src.scanner import fetch_btc_5min_market
from src.executor import execute_trade
from src.database import (
  init_db,
  validate_db_schema,
  has_open_trade_for_market,
  is_db_configured,
  update_system_status,
)
from src.log_buffer import start_log_buffer, stop_log_buffer
from src.settlement import settle_trades
from src.utils.balance import get_current_balance

from src.strategies.last_second import LastSecondStrategy

logger.level("BALANCE", no=22, color="<cyan>")


def main():
  logger.info("=" * 60)
  logger.info("BTC 5-Minute Multi-Strategy Bot")
  logger.info("=" * 60)

  init_db()
  start_log_buffer()
  try:
    validate_db_schema()
  except RuntimeError as e:
    logger.error(str(e))
    sys.exit(1)

  if not is_db_configured():
    logger.error(
      "CONVEX_URL is not set - trades will NOT be saved to the database. "
      "Set CONVEX_URL in .env.local and restart."
    )

  # Initialize strategies
  strategy_instances = {}

  if STRATEGIES["last_second"]["enabled"]:
    strategy_instances["last_second"] = LastSecondStrategy(STRATEGIES["last_second"])

  enabled_count = len(strategy_instances)
  logger.info(f"Enabled strategies: {enabled_count}")
  for name in strategy_instances:
    logger.info(f"  ✓ {name}")
  logger.info("=" * 60)

  from src.utils.rtds_client import start as rtds_start, get_latest_btc_usd, stop as rtds_stop
  rtds_start()

  shutdown_requested = False

  def request_shutdown(*_args):
    nonlocal shutdown_requested
    shutdown_requested = True

  if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, request_shutdown)
  signal.signal(signal.SIGINT, request_shutdown)

  bot_start_time = time.time()
  polymarket_ok = True  # updated each loop
  logger.info(f"Bot start time (for window gating): {bot_start_time:.0f}")

  def shutdown_bot():
    logger.info("Shutting down bot...")
    update_system_status(
      engine_state="STOPPED",
      uptime_seconds=int(time.time() - bot_start_time),
      scan_interval=SCAN_INTERVAL,
      polymarket_ok=polymarket_ok,
      db_ok=is_db_configured(),
      rtds_ok=False,
      key="5min",
    )
    rtds_stop()
    logger.info("Running final settlement check...")
    settle_trades()
    stop_log_buffer()

  logger.log("BALANCE", f"Current Balance: ${get_current_balance():,.2f}")

  opportunities_found = 0

  while True:
    if shutdown_requested:
      break
    try:
      # Fetch current BTC 5min market
      market = fetch_btc_5min_market()
      polymarket_ok = True  # fetch completed (success or no market)

      if not market:
        logger.info("No active market (between rounds)")
        update_system_status(
          engine_state="IDLE",
          uptime_seconds=int(time.time() - bot_start_time),
          scan_interval=SCAN_INTERVAL,
          polymarket_ok=polymarket_ok,
          db_ok=is_db_configured(),
          rtds_ok=get_latest_btc_usd() is not None,
          key="5min",
        )
        time.sleep(30)
        continue

      # Force skip if this window started before we started (we don't have true start price)
      window_start_ts = market.get("window_start_ts")
      if window_start_ts is not None and window_start_ts < bot_start_time:
        logger.warning(
          f"SKIP: window started before bot (start_ts={window_start_ts:.0f} < bot_start={bot_start_time:.0f}). "
          "Waiting for next 5m window."
        )
        settle_trades()
        update_system_status(
          engine_state="IDLE",
          uptime_seconds=int(time.time() - bot_start_time),
          scan_interval=SCAN_INTERVAL,
          polymarket_ok=polymarket_ok,
          db_ok=is_db_configured(),
          rtds_ok=get_latest_btc_usd() is not None,
          key="5min",
        )
        time.sleep(SCAN_INTERVAL)
        continue

      # Try each strategy in priority order
      trade_signal = None
      for strategy_name in STRATEGY_PRIORITY:
        if strategy_name not in strategy_instances:
          continue

        strategy = strategy_instances[strategy_name]
        trade_signal = strategy.analyze(market)

        if trade_signal:
          logger.info(f"Strategy '{strategy_name}' triggered!")
          break

      # Execute if signal found (only one trade per market)
      if trade_signal:
        slug = market.get("slug") or market.get("question") or ""
        if has_open_trade_for_market(slug):
          logger.debug(f"Skip trade: already have open position on {slug}")
        else:
          opportunities_found += 1
          success = execute_trade(market, trade_signal)
          if success:
            logger.success(f"Trade executed! Total opportunities: {opportunities_found}")
      else:
        logger.debug(
          f"No opportunities: {market['slug']} | "
          f"YES: {market['yes_price']:.3f}, NO: {market['no_price']:.3f}"
        )

      settle_trades()

      update_system_status(
        engine_state="SCANNING",
        uptime_seconds=int(time.time() - bot_start_time),
        scan_interval=SCAN_INTERVAL,
        polymarket_ok=polymarket_ok,
        db_ok=is_db_configured(),
        rtds_ok=get_latest_btc_usd() is not None,
        key="5min",
      )

      time.sleep(SCAN_INTERVAL)

    except Exception as e:
      logger.error(f"Error in main loop: {e}")
      update_system_status(
        engine_state="ERROR",
        uptime_seconds=int(time.time() - bot_start_time),
        scan_interval=SCAN_INTERVAL,
        polymarket_ok=False,
        db_ok=is_db_configured(),
        rtds_ok=get_latest_btc_usd() is not None,
        key="5min",
      )
      time.sleep(30)

  shutdown_bot()


if __name__ == "__main__":
  main()
