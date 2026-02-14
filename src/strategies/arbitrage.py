from src.strategies.base import BaseStrategy
from typing import Optional, Dict
from loguru import logger


class ArbitrageStrategy(BaseStrategy):
  """
  Internal arbitrage: Buy both YES and NO when total cost < threshold.

  Config:
  - min_profit: Minimum profit threshold (default 0.02 = 2%)
  """

  def __init__(self, config: Dict):
    super().__init__("Arbitrage", config)
    self.min_profit = config.get("min_profit", 0.02)

  def analyze(self, market: Dict) -> Optional[Dict]:
    if not self.should_trade(market):
      return None

    yes_price = market["yes_price"]
    no_price = market["no_price"]
    total_cost = yes_price + no_price

    # Check if arbitrage exists
    if total_cost < (1.0 - self.min_profit):
      profit = 1.0 - total_cost
      profit_pct = (profit / total_cost) * 100

      logger.info(
        f"[ARBITRAGE] Found opportunity: {market['slug']} | "
        f"YES: {yes_price:.4f}, NO: {no_price:.4f} | "
        f"Profit: {profit_pct:.2f}%"
      )

      return {
        "strategy": self.name,
        "action": "bet_both",  # Special: buy both sides
        "yes_price": yes_price,
        "no_price": no_price,
        "size": self.config.get("position_size", 100),
        "confidence": 0.99,  # Risk-free
        "reason": f"Internal arbitrage: {profit_pct:.2f}% profit",
        "expected_profit": profit * self.config.get("position_size", 100),
      }

    return None
