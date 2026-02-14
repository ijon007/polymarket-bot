from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.

    Each strategy must implement:
    - analyze(market): Check if opportunity exists
    - get_signal(market): Return trade signal or None
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", False)
        logger.info(f"Strategy '{self.name}' initialized (enabled={self.enabled})")

    @abstractmethod
    def analyze(self, market: Dict) -> Optional[Dict]:
        """
        Analyze market and return trade signal if opportunity exists.

        Args:
            market: Dict with keys: condition_id, question, yes_price, no_price,
                   end_date, tokens, seconds_left, slug

        Returns:
            Signal dict with keys: action ('bet_yes'/'bet_no'),
            price, size, confidence, reason, expected_profit
            OR None if no opportunity
        """
        pass

    def should_trade(self, market: Dict) -> bool:
        """Check if this strategy should trade this market (can override)"""
        if not self.enabled:
            return False

        # Default: trade if seconds_left > 30
        return market.get("seconds_left", 0) > 30
