from src.strategies.base import BaseStrategy
from src.utils.price_feed import get_btc_price
from typing import Optional, Dict
from loguru import logger
import time


class MomentumStrategy(BaseStrategy):
    """
    Follow BTC price momentum.

    Tracks BTC price over lookback window.
    If price rising → bet YES
    If price falling → bet NO
    """

    def __init__(self, config: Dict):
        super().__init__("Momentum", config)
        self.lookback_seconds = config.get("lookback_seconds", 60)
        self.min_move_pct = config.get("min_move_pct", 0.002)  # 0.2% minimum
        self.price_history = []  # [(timestamp, price), ...]

    def update_price_history(self):
        """Fetch and store current BTC price"""
        current_price = get_btc_price()
        if current_price is None:
            return False

        current_time = time.time()
        self.price_history.append((current_time, current_price))

        # Keep only recent history (lookback window + buffer)
        cutoff = current_time - (self.lookback_seconds * 2)
        self.price_history = [
            (t, p) for t, p in self.price_history
            if t > cutoff
        ]

        return True

    def calculate_momentum(self) -> Optional[float]:
        """
        Calculate price momentum over lookback window.

        Returns:
            Price change percentage (0.01 = 1% up, -0.01 = 1% down)
            None if insufficient data
        """
        if len(self.price_history) < 2:
            return None

        current_time = time.time()

        # Get price from lookback_seconds ago
        target_time = current_time - self.lookback_seconds

        # Find closest price to target time
        old_price = None
        for t, p in self.price_history:
            if t <= target_time:
                old_price = p
            else:
                break

        if old_price is None:
            # Not enough history yet
            return None

        # Current price (most recent)
        current_price = self.price_history[-1][1]

        # Calculate percentage change
        price_change = (current_price - old_price) / old_price

        return price_change

    def analyze(self, market: Dict) -> Optional[Dict]:
        if not self.should_trade(market):
            return None

        # Update price history
        if not self.update_price_history():
            logger.debug("Failed to fetch BTC price")
            return None

        # Calculate momentum
        momentum = self.calculate_momentum()

        if momentum is None:
            logger.debug(f"Insufficient price history ({len(self.price_history)} points)")
            return None

        # Check if move is significant enough
        if abs(momentum) < self.min_move_pct:
            logger.debug(f"Momentum too small: {momentum*100:.3f}% (need {self.min_move_pct*100:.2f}%)")
            return None

        # Determine direction
        if momentum > 0:
            # BTC rising → bet YES (up)
            action = "bet_yes"
            price = market["yes_price"]
            direction = "UP"
        else:
            # BTC falling → bet NO (down)
            action = "bet_no"
            price = market["no_price"]
            direction = "DOWN"

        reason = f"BTC momentum {direction}: {momentum*100:+.2f}% in {self.lookback_seconds}s"

        logger.info(
            f"[MOMENTUM] {market['slug']} | "
            f"{reason} → {action.upper()}"
        )

        # Scale confidence based on momentum strength
        # 0.2% move = 40% confidence, 1% move = 90% confidence
        confidence = min(abs(momentum) / 0.01 * 0.9, 0.95)

        return {
            "strategy": self.name,
            "action": action,
            "price": price,
            "size": self.config.get("position_size", 100),
            "confidence": confidence,
            "reason": reason,
            "expected_profit": abs(momentum) * self.config.get("position_size", 100)
        }
