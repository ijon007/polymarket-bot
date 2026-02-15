from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from loguru import logger


class MarketTracker:
  """Track market start times and BTC prices"""

  def __init__(self):
    self.markets = {}  # {slug: {"start_time": datetime, "start_price": float}}

  def register_market(self, slug: str, start_time: datetime, btc_price: float):
    """Register a new market with its start price"""
    self.markets[slug] = {
      "start_time": start_time,
      "start_price": btc_price
    }
    logger.info(f"Registered {slug} | Start price: ${btc_price:,.2f}")

  def get_start_price(self, slug: str) -> Optional[float]:
    """Get the BTC price when market started"""
    if slug in self.markets:
      return self.markets[slug]["start_price"]
    return None

  def cleanup_old_markets(self):
    """Remove markets older than 1 hour"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    old_slugs = [
      slug for slug, data in self.markets.items()
      if data["start_time"] < cutoff
    ]

    for slug in old_slugs:
      del self.markets[slug]

    if old_slugs:
      logger.debug(f"Cleaned up {len(old_slugs)} old markets")


# Global tracker instance
market_tracker = MarketTracker()
