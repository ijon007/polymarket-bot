import sys
import signal
import time
from loguru import logger
from src.config import SCAN_INTERVAL, STRATEGIES, STRATEGY_PRIORITY, FIVE_MIN_ASSETS
from src.scanner import fetch_5min_markets
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
  logger.info("5-Minute Multi-Strategy Bot (BTC, ETH, SOL, XRP)")
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

  logger.info(f"Strategies: {','.join(strategy_instances) or 'none'}")
  logger.info("=" * 60)

  from src.utils.rtds_client import (
    start as rtds_start,
    stop as rtds_stop,
    get_latest_btc_usd,
    get_latest_eth_usd,
    get_latest_sol_usd,
    get_latest_xrp_usd,
  )
  _RTDS_GETTERS = {
    "btc": get_latest_btc_usd,
    "eth": get_latest_eth_usd,
    "sol": get_latest_sol_usd,
    "xrp": get_latest_xrp_usd,
  }

  def _rtds_ok_5min():
    return all(_RTDS_GETTERS.get(a)() is not None for a in FIVE_MIN_ASSETS)

  def _rtds_status_line():
    parts = [f"{a}=ok" if _RTDS_GETTERS.get(a)() is not None else f"{a}=n/a" for a in FIVE_MIN_ASSETS]
    return "RTDS: " + " ".join(parts)

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
      markets = fetch_5min_markets()
      polymarket_ok = True

      if not markets:
        logger.info(f"No active market (between rounds) | {_rtds_status_line()}")
        update_system_status(
          engine_state="IDLE",
          uptime_seconds=int(time.time() - bot_start_time),
          scan_interval=SCAN_INTERVAL,
          polymarket_ok=polymarket_ok,
          db_ok=is_db_configured(),
          rtds_ok=_rtds_ok_5min(),
          key="5min",
        )
        time.sleep(30)
        continue

      active_assets = [m.get("asset", "") for m in markets if m.get("asset")]
      status_line = f"Markets: {','.join(active_assets) or '?'} | {_rtds_status_line()}"
      logger.info(status_line)

      skipped = [
        m.get("asset", m.get("slug", "?"))
        for m in markets
        if m.get("window_start_ts") is not None and m.get("window_start_ts") < bot_start_time
      ]
      if skipped:
        logger.warning(f"SKIP: {','.join(skipped)} started before bot")

      no_opp_parts = []
      for market in markets:
        window_start_ts = market.get("window_start_ts")
        if window_start_ts is not None and window_start_ts < bot_start_time:
          continue

        trade_signal = None
        for strategy_name in STRATEGY_PRIORITY:
          if strategy_name not in strategy_instances:
            continue
          strategy = strategy_instances[strategy_name]
          trade_signal = strategy.analyze(market)
          if trade_signal:
            logger.info(f"Strategy '{strategy_name}' triggered!")
            break

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
          a = market.get("asset", "")
          no_opp_parts.append(f"{a} {market.get('yes_price', 0):.2f}/{market.get('no_price', 0):.2f}")
      if no_opp_parts:
        logger.debug("No opportunities: " + " | ".join(no_opp_parts))

      settle_trades()

      update_system_status(
        engine_state="SCANNING",
        uptime_seconds=int(time.time() - bot_start_time),
        scan_interval=SCAN_INTERVAL,
        polymarket_ok=polymarket_ok,
        db_ok=is_db_configured(),
        rtds_ok=_rtds_ok_5min(),
        key="5min",
      )

      time.sleep(SCAN_INTERVAL)

    except Exception as e:
      logger.error(f"Error in main loop: {e}")
      logger.info(_rtds_status_line())
      update_system_status(
        engine_state="ERROR",
        uptime_seconds=int(time.time() - bot_start_time),
        scan_interval=SCAN_INTERVAL,
        polymarket_ok=False,
        db_ok=is_db_configured(),
        rtds_ok=_rtds_ok_5min(),
        key="5min",
      )
      time.sleep(30)

  shutdown_bot()


if __name__ == "__main__":
  main()
