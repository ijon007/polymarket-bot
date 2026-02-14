import sys
import time
from loguru import logger
from src.config import SCAN_INTERVAL, STRATEGIES, STRATEGY_PRIORITY
from src.scanner import fetch_btc_5min_market
from src.executor import execute_trade
from src.database import init_db, validate_db_schema

# Import all strategies
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.last_second import LastSecondStrategy
from src.strategies.spread_capture import SpreadCaptureStrategy


def main():
  logger.info("=" * 60)
  logger.info("BTC 5-Minute Multi-Strategy Bot")
  logger.info("=" * 60)

  init_db()
  try:
    validate_db_schema()
  except RuntimeError as e:
    logger.error(str(e))
    sys.exit(1)

  # Initialize strategies
  strategy_instances = {}

  if STRATEGIES["mean_reversion"]["enabled"]:
    strategy_instances["mean_reversion"] = MeanReversionStrategy(STRATEGIES["mean_reversion"])

  if STRATEGIES["momentum"]["enabled"]:
    strategy_instances["momentum"] = MomentumStrategy(STRATEGIES["momentum"])

  if STRATEGIES["last_second"]["enabled"]:
    strategy_instances["last_second"] = LastSecondStrategy(STRATEGIES["last_second"])

  if STRATEGIES["spread_capture"]["enabled"]:
    strategy_instances["spread_capture"] = SpreadCaptureStrategy(STRATEGIES["spread_capture"])

  enabled_count = len(strategy_instances)
  logger.info(f"Enabled strategies: {enabled_count}")
  for name in strategy_instances:
    logger.info(f"  ✓ {name}")
  logger.info("=" * 60)

  opportunities_found = 0

  while True:
    try:
      # Fetch current BTC 5min market
      market = fetch_btc_5min_market()

      if not market:
        logger.info("No active market (between rounds)")
        time.sleep(30)
        continue

      # Try each strategy in priority order
      signal = None
      for strategy_name in STRATEGY_PRIORITY:
        if strategy_name not in strategy_instances:
          continue

        strategy = strategy_instances[strategy_name]
        signal = strategy.analyze(market)

        if signal:
          logger.info(f"Strategy '{strategy_name}' triggered!")
          break

      # Execute if signal found
      if signal:
        opportunities_found += 1
        success = execute_trade(market, signal)
        if success:
          logger.success(f"Trade executed! Total opportunities: {opportunities_found}")
      else:
        logger.debug(
          f"No opportunities: {market['slug']} | "
          f"YES: {market['yes_price']:.3f}, NO: {market['no_price']:.3f}"
        )

      time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
      logger.info("\nShutting down bot...")
      break
    except Exception as e:
      logger.error(f"Error in main loop: {e}")
      time.sleep(30)


if __name__ == "__main__":
  main()
