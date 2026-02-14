"""Main bot loop: scan markets, apply logic filter and arbitrage layers, execute paper/real trades."""

import threading
import time

from src.bot import arbitrage, executor, logic_filter, scanner
from src.risk import risk_limits
from src.utils import config
from src.utils.logger import get_logger

logger = get_logger()

MIN_QUICK_PROFIT_PCT = config.MIN_EDGE_ARB_QUICK * 100  # e.g. 2%


def fast_scan_loop() -> None:
    """Scan quick markets every FAST_SCAN_INTERVAL; internal arb only, lower threshold."""
    while True:
        try:
            quick_markets = scanner.fetch_quick_markets()
            logger.info("[FAST SCAN] Checking %d quick markets...", len(quick_markets))
            for market in quick_markets:
                arb = arbitrage.find_internal_arb(market, quick_mode=True)
                if arb and arb["profit_pct"] > MIN_QUICK_PROFIT_PCT:
                    logger.info("QUICK ARB: %s - %.2f%%", market.ticker, arb["profit_pct"])
                    executor.execute_arb(market, arb)
            time.sleep(config.FAST_SCAN_INTERVAL)
        except Exception as e:
            logger.error("Fast scan error: %s", e)
            time.sleep(30)


def main() -> None:
    """Run the strategy loop: logic filter -> internal arb -> combinatorial arb."""
    logger.info("Starting Polymarket bot (Math-only mode)...")
    logger.info(f"Paper mode: {config.PAPER_MODE}")
    logger.info(f"Bankroll: ${config.BANKROLL}")

    fast_thread = threading.Thread(target=fast_scan_loop, daemon=True)
    fast_thread.start()

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

                arb = arbitrage.find_internal_arb(market, quick_mode=False)
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
