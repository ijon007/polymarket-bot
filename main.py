import time
from loguru import logger
from src.config import SCAN_INTERVAL
from src.scanner import fetch_btc_5min_markets
from src.arbitrage import check_arbitrage
from src.executor import execute_arbitrage
from src.database import init_db


def main():
  logger.info("=" * 60)
  logger.info("BTC 5-Minute Arbitrage Bot")
  logger.info("Strategy: Buy both YES and NO when total < $0.98")
  logger.info("Mode: Paper Trading (logging only)")
  logger.info("=" * 60)

  # Initialize database
  init_db()

  opportunities_found = 0

  while True:
    try:
      # Fetch BTC 5min markets
      markets = fetch_btc_5min_markets()

      if not markets:
        logger.info("No active BTC 5min markets found")

      # Check each market for arbitrage
      for market in markets:
        arb = check_arbitrage(market)

        if arb:
          opportunities_found += 1
          execute_arbitrage(arb)

      logger.info(f"Scan complete. Total opportunities found: {opportunities_found}")
      logger.info(f"Sleeping for {SCAN_INTERVAL} seconds...\n")
      time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
      logger.info("\nShutting down bot...")
      break
    except Exception as e:
      logger.error(f"Error in main loop: {e}")
      time.sleep(60)


if __name__ == "__main__":
  main()
