from src.strategies.base import BaseStrategy
from src.utils.price_feed import get_btc_price, get_btc_price_at_timestamp, get_btc_price_source
from typing import Optional, Dict
from loguru import logger


class LastSecondStrategy(BaseStrategy):
  """
  Wait until final seconds, check if BTC is up/down vs start, bet on winner.

  Only trades in last trigger_seconds when outcome is nearly certain.
  """

  def __init__(self, config: Dict):
    super().__init__("Last Second", config)
    self.trigger_seconds = config.get("trigger_seconds", 30)

  def should_trade(self, market: Dict) -> bool:
    """Only trade in final seconds"""
    if not self.enabled:
      return False

    seconds_left = market.get("seconds_left", 0)

    # Only trade in final window (but not too late to execute)
    return 5 < seconds_left <= self.trigger_seconds

  def analyze(self, market: Dict) -> Optional[Dict]:
    if not self.should_trade(market):
      return None

    slug = market["slug"]

    # Resolution source: log when Polymarket uses Chainlink (we use RTDS Chainlink)
    resolution_source = (market.get("resolution_source") or "").strip()
    price_source = get_btc_price_source()
    if resolution_source and "chain.link" in resolution_source.lower():
      if price_source == "rtds":
        logger.info(f"Resolution source: Chainlink (we use RTDS Chainlink) | {slug}")
      else:
        logger.info(f"Resolution source: {resolution_source} | {slug}")
        if self.config.get("require_resolution_source_match", False):
          logger.info(f"Skipping trade: require_resolution_source_match=True (RTDS unavailable)")
          return None
    else:
      logger.info(f"Resolution source: {resolution_source or 'unknown'} | {slug}")

    # Start price: RTDS buffer at window_start_ts
    start_price = None
    start_source = None
    window_start_ts = market.get("window_start_ts")
    if window_start_ts is not None:
      start_price = get_btc_price_at_timestamp(window_start_ts)
      if start_price is not None:
        start_source = "timestamp"
    if start_price is None:
      if window_start_ts is not None:
        logger.debug(f"No RTDS start price for {slug} (no data yet, skipping this window)")
      else:
        logger.debug(f"No start price for {slug} (window_start_ts={window_start_ts})")
      return None
    logger.info(f"Start price ({start_source}): ${start_price:,.2f} | {slug}")

    # Get current BTC price
    current_price = get_btc_price()
    if current_price is None:
      logger.debug("Failed to fetch current BTC price")
      return None

    # Calculate change
    price_change = current_price - start_price
    price_change_pct = (price_change / start_price) * 100

    # Minimum move: skip if move is below threshold (avoids trading on noise)
    min_pct = self.config.get("min_move_pct", 0.0)
    min_dollars = self.config.get("min_move_dollars", 0.0)
    if min_pct > 0 and abs(price_change_pct) < min_pct:
      logger.debug(f"Move {price_change_pct:+.2f}% below min_move_pct {min_pct}% | {slug}")
      return None
    if min_dollars > 0 and abs(price_change) < min_dollars:
      logger.debug(f"Move ${abs(price_change):.2f} below min_move_dollars ${min_dollars} | {slug}")
      return None

    # Determine winner
    if current_price >= start_price:
      # BTC is up → YES will win
      action = "bet_yes"
      price = market["yes_price"]
      outcome = "UP"
    else:
      # BTC is down → NO will win
      action = "bet_no"
      price = market["no_price"]
      outcome = "DOWN"

    seconds_left = market["seconds_left"]
    reason = (
      f"BTC {outcome} ${abs(price_change):,.2f} ({price_change_pct:+.2f}%) | "
      f"{seconds_left}s left → outcome certain"
    )

    logger.info(
      f"[LAST SECOND] {slug} | "
      f"Start: ${start_price:,.2f} → Now: ${current_price:,.2f} | "
      f"{reason}"
    )

    # Very high confidence (outcome is known)
    confidence = 0.99

    # Expected profit depends on price
    # If betting YES at 10¢, expected profit = 90¢
    # If betting YES at 90¢, expected profit = 10¢
    expected_value = (1.0 - price) * self.config.get("position_size", 100)

    return {
      "strategy": self.name,
      "action": action,
      "price": price,
      "size": self.config.get("position_size", 100),
      "confidence": confidence,
      "reason": reason,
      "expected_profit": expected_value
    }
