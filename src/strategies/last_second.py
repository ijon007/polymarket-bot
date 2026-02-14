from src.strategies.base import BaseStrategy
from typing import Optional, Dict
from loguru import logger


class LastSecondStrategy(BaseStrategy):
    """
    Wait until final seconds, check Chainlink price, bet on guaranteed winner.

    Only trades in last 30 seconds when outcome is nearly certain.

    Config:
    - trigger_seconds: Start trading this many seconds before close (default 30)
    - chainlink_url: Chainlink BTC/USD endpoint
    """

    def __init__(self, config: Dict):
        super().__init__("Last Second", config)
        self.trigger_seconds = config.get("trigger_seconds", 30)
        self.chainlink_url = config.get(
            "chainlink_url",
            "https://data.chain.link/streams/btc-usd",
        )

    def should_trade(self, market: Dict) -> bool:
        """Only trade in final seconds"""
        if not self.enabled:
            return False

        seconds_left = market.get("seconds_left", 0)
        return 0 < seconds_left <= self.trigger_seconds

    def analyze(self, market: Dict) -> Optional[Dict]:
        if not self.should_trade(market):
            return None

        # TODO: Get start price and current price from Chainlink
        # For now, placeholder (won't trade)
        logger.debug("Chainlink integration needed for last-second strategy")
        return None

        # Pseudocode for when implemented:
        # start_price = get_market_start_price(market)
        # current_price = get_current_btc_price()
        #
        # if current_price >= start_price:
        #     return bet_yes_signal()
        # else:
        #     return bet_no_signal()
