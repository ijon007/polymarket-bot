from datetime import datetime
from loguru import logger
from src.database import log_trade
from src.config import PAPER_MODE, BANKROLL


def execute_arbitrage(arb_signal):
  """
  Execute arbitrage trade (paper mode only for now).

  Buys both YES and NO to lock in guaranteed profit.
  """
  if not PAPER_MODE:
    logger.warning("Real trading not implemented yet")
    return False

  # Calculate position size (fixed 10% of bankroll for now)
  position_size = BANKROLL * 0.10

  # Paper trade: just log to database
  trade_data = {
    "condition_id": arb_signal["condition_id"],
    "question": arb_signal["question"],
    "yes_price": arb_signal["yes_price"],
    "no_price": arb_signal["no_price"],
    "total_cost": arb_signal["total_cost"],
    "position_size": position_size,
    "expected_profit": arb_signal["profit"] * position_size,
    "profit_pct": arb_signal["profit_pct"],
    "executed_at": datetime.utcnow(),
    "status": "paper",
  }

  logger.info(
    f"PAPER TRADE: Buy YES @ {arb_signal['yes_price']:.4f} + "
    f"NO @ {arb_signal['no_price']:.4f} | "
    f"Size: ${position_size:.2f} | "
    f"Expected profit: ${trade_data['expected_profit']:.2f}"
  )

  # Log to database
  log_trade(trade_data)

  return True
