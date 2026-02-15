"""Current balance = BANKROLL + sum(actual_profit) for settled trades."""
from src.config import BANKROLL
from src.database import get_settled_pnl_sum, is_db_configured


def get_current_balance() -> float:
  """Return BANKROLL + sum of actual_profit for all settled (won/lost) trades."""
  if not is_db_configured():
    return BANKROLL
  total = get_settled_pnl_sum()
  return BANKROLL + total
