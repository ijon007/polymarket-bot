"""Main bot loop: scan markets, apply logic filter and arbitrage layers, execute paper/real trades."""

import time

from loguru import logger

from src.bot import arbitrage, executor, logic_filter, scanner
from src.risk import risk_limits
from src.utils import config


def main() -> None:
    """Run the strategy loop: logic filter -> internal arb -> combinatorial arb."""
    logger.info("Starting Polymarket bot (Math-only mode)...")
    logger.info(f"Paper mode: {config.PAPER_MODE}")
    logger.info(f"Bankroll: ${config.BANKROLL}")

    while True:
        try:
            markets = scanner.fetch_markets()
            logger.info(f"Scanned {len(markets)} active markets")

            opportunities_found = 0

            for market in markets:
                if market.volume_24h < config.MIN_LIQUIDITY:
                    continue

                logic_signal = logic_filter.check_logic(market)
                if logic_signal:
                    if logic_signal["action"] == "skip":
                        logger.debug(f"Skipping {market.ticker}: {logic_signal['reason']}")
                        continue
                    if logic_signal["action"] in ("bet_yes", "bet_no"):
                        logger.info(f"Logic opportunity: {market.ticker} - {logic_signal['reason']}")
                        if executor.execute_trade(market, logic_signal):
                            opportunities_found += 1
                        continue

                arb = arbitrage.find_internal_arb(market)
                if arb:
                    logger.info(f"Internal arb: {market.ticker} - {arb['profit_pct']:.2f}% profit")
                    if executor.execute_arb(market, arb):
                        opportunities_found += 1
                    continue

            combo_arbs = arbitrage.find_all_combinatorial_arbs(markets)
            for combo in combo_arbs:
                logger.info(
                    f"Combinatorial arb: {combo['markets']} - {combo['expected_profit']:.2f} profit"
                )
                if executor.execute_combo(combo):
                    opportunities_found += 1

            logger.info(f"Scan complete. Found {opportunities_found} opportunities.")

            risk_limits.manage_positions()

            logger.info(f"Sleeping for {config.SCAN_INTERVAL} seconds...")
            time.sleep(config.SCAN_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Shutting down bot...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
            time.sleep(60)


def run() -> None:
    """Entry point for main bot loop."""
    main()


if __name__ == "__main__":
    main()
