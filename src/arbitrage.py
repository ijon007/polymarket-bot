from loguru import logger
from src.config import MIN_ARB_PROFIT


def check_arbitrage(market):
  """
  Check if YES + NO < 0.98 (2% profit opportunity).

  Returns dict with arbitrage details or None.
  """
  yes_price = market["yes_price"]
  no_price = market["no_price"]

  total_cost = yes_price + no_price

  # Arbitrage exists if total cost < 0.98
  if total_cost < (1.0 - MIN_ARB_PROFIT):
    profit = 1.0 - total_cost
    profit_pct = (profit / total_cost) * 100

    logger.info(
      f"ARB FOUND: {market['question'][:50]}... | "
      f"YES: {yes_price:.4f}, NO: {no_price:.4f} | "
      f"Profit: {profit_pct:.2f}% | "
      f"Ends in: {market['seconds_left']}s"
    )

    return {
      "condition_id": market["condition_id"],
      "question": market["question"],
      "yes_price": yes_price,
      "no_price": no_price,
      "total_cost": total_cost,
      "profit": profit,
      "profit_pct": profit_pct,
    }

  return None
