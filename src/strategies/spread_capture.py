from src.strategies.base import BaseStrategy
from typing import Optional, Dict
from loguru import logger


class SpreadCaptureStrategy(BaseStrategy):
  """
  Act as market maker: post limit orders inside the spread.

  Buy YES below mid, sell YES above mid (and same for NO).
  Earn the spread when orders fill.

  NOTE: Requires REAL trading (not paper mode) and order management.

  Config:
  - spread_target: Target spread to capture (default 0.02 = 2¢)
  """

  def __init__(self, config: Dict):
    super().__init__("Spread Capture", config)
    self.spread_target = config.get("spread_target", 0.02)

  def analyze(self, market: Dict) -> Optional[Dict]:
    if not self.should_trade(market):
      return None

    yes_price = market["yes_price"]
    no_price = market["no_price"]

    # Calculate mid price
    mid = 0.50  # For 50/50 markets

    # Check if spread exists
    spread = abs(yes_price - (1 - no_price))

    if spread >= self.spread_target:
      logger.info(
        f"[SPREAD CAPTURE] Spread detected: {market['slug']} | "
        f"Spread: {spread*100:.1f}¢ | "
        f"Post orders inside spread (NOT IMPLEMENTED)"
      )

      # TODO: Implement limit order posting
      # For now, return None (requires real trading infrastructure)
      return None

    return None
