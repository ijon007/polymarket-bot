import time
from loguru import logger
from src.scanner import fetch_btc_5min_markets
from src.arbitrage import check_arbitrage
from src.executor import execute_arbitrage
from src.database import init_db


def main():
  logger.info("BTC 5-Minute Arbitrage Bot")

  init_db()
  opportunities_found = 0

  while True:
    try:
      markets = fetch_btc_5min_markets()

      if not markets:
        logger.info("No active market (between rounds, wait 30s)")
        time.sleep(30)
        continue

      market = markets[0]

      arb = check_arbitrage(market)
      if arb:
        opportunities_found += 1
        execute_arbitrage(arb)

      time.sleep(10)

    except KeyboardInterrupt:
      break
    except Exception as e:
      logger.error(f"Error: {e}")
      time.sleep(30)


if __name__ == "__main__":
  main()
