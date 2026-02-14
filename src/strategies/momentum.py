from src.strategies.base import BaseStrategy
from typing import Optional, Dict
from loguru import logger
import time


class MomentumStrategy(BaseStrategy):
    """
    Follow BTC price momentum using Chainlink price feed.

    If BTC price rising → bet YES
    If BTC price falling → bet NO

    Config:
    - chainlink_url: Chainlink BTC/USD endpoint
    - lookback_seconds: How far back to check momentum (default 60s)
    - min_move_pct: Minimum % move to trigger trade (default 0.1%)
    """

    def __init__(self, config: Dict):
        super().__init__("Momentum", config)
        self.chainlink_url = config.get(
            "chainlink_url",
            "https://data.chain.link/streams/btc-usd",
        )
        self.lookback_seconds = config.get("lookback_seconds", 60)
        self.min_move_pct = config.get("min_move_pct", 0.001)  # 0.1%
        self.price_history = []  # Store recent prices

    def get_btc_price(self) -> Optional[float]:
        """Fetch current BTC price from Chainlink (placeholder - implement actual API)"""
        try:
            # TODO: Implement actual Chainlink API call
            # For now, return None (strategy won't trade)
            logger.debug("Chainlink integration not implemented yet")
            return None
        except Exception as e:
            logger.error(f"Error fetching BTC price: {e}")
            return None

    def analyze(self, market: Dict) -> Optional[Dict]:
        if not self.should_trade(market):
            return None

        # Get current price
        current_price = self.get_btc_price()
        if current_price is None:
            return None

        # Store in history
        self.price_history.append((time.time(), current_price))

        # Keep only recent history
        cutoff = time.time() - self.lookback_seconds
        self.price_history = [(t, p) for t, p in self.price_history if t > cutoff]

        # Need at least 2 data points
        if len(self.price_history) < 2:
            return None

        # Calculate momentum
        old_price = self.price_history[0][1]
        price_change = (current_price - old_price) / old_price

        # Check if significant move
        if abs(price_change) < self.min_move_pct:
            return None

        # Determine direction
        if price_change > 0:
            # BTC rising → bet YES (up)
            action = "bet_yes"
            price = market["yes_price"]
            reason = f"BTC momentum: +{price_change*100:.2f}% in {self.lookback_seconds}s"
        else:
            # BTC falling → bet NO (down)
            action = "bet_no"
            price = market["no_price"]
            reason = f"BTC momentum: {price_change*100:.2f}% in {self.lookback_seconds}s"

        logger.info(f"[MOMENTUM] {reason} → {action.upper()}")

        return {
            "strategy": self.name,
            "action": action,
            "price": price,
            "size": self.config.get("position_size", 100),
            "confidence": min(abs(price_change) / 0.01, 0.90),  # Scale to confidence
            "reason": reason,
            "expected_profit": abs(price_change) * self.config.get("position_size", 100),
        }
