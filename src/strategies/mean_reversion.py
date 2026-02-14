from src.strategies.base import BaseStrategy
from typing import Optional, Dict
from loguru import logger


class MeanReversionStrategy(BaseStrategy):
  """
  Bet against overpriced outcomes (assume 50/50 is fair).

  If YES > threshold (e.g., 0.60) → bet NO
  If NO > threshold → bet YES

  Config:
  - overpriced_threshold: Price above this = overpriced (default 0.60)
  - min_edge: Minimum edge to trade (default 0.08 = 8%)
  """

  def __init__(self, config: Dict):
    super().__init__("Mean Reversion", config)
    self.overpriced_threshold = config.get("overpriced_threshold", 0.60)
    self.min_edge = config.get("min_edge", 0.08)

  def analyze(self, market: Dict) -> Optional[Dict]:
    if not self.should_trade(market):
      return None

    yes_price = market["yes_price"]
    no_price = market["no_price"]

    # Fair price = 0.50 (50/50 market)
    fair_price = 0.50

    # Check if YES is overpriced
    if yes_price > self.overpriced_threshold:
      edge = yes_price - fair_price

      if edge >= self.min_edge:
        logger.info(
          f"[MEAN REVERSION] YES overpriced: {market['slug']} | "
          f"YES: {yes_price:.4f} (fair: {fair_price:.2f}) | "
          f"Edge: {edge*100:.1f}% → Betting NO"
        )

        return {
          "strategy": self.name,
          "action": "bet_no",
          "price": no_price,
          "size": self.config.get("position_size", 100),
          "confidence": min(edge / 0.20, 0.95),  # Scale 8-20% edge to 40-95% confidence
          "reason": f"YES overpriced at {yes_price:.2f} (fair: {fair_price:.2f})",
          "expected_profit": edge * self.config.get("position_size", 100),
        }

    # Check if NO is overpriced
    if no_price > self.overpriced_threshold:
      edge = no_price - fair_price

      if edge >= self.min_edge:
        logger.info(
          f"[MEAN REVERSION] NO overpriced: {market['slug']} | "
          f"NO: {no_price:.4f} (fair: {fair_price:.2f}) | "
          f"Edge: {edge*100:.1f}% → Betting YES"
        )

        return {
          "strategy": self.name,
          "action": "bet_yes",
          "price": yes_price,
          "size": self.config.get("position_size", 100),
          "confidence": min(edge / 0.20, 0.95),
          "reason": f"NO overpriced at {no_price:.2f} (fair: {fair_price:.2f})",
          "expected_profit": edge * self.config.get("position_size", 100),
        }

    return None
