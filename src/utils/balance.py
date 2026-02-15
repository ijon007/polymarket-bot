"""Current balance = BANKROLL + sum(actual_profit) for settled trades."""
from src.config import BANKROLL
from src.database import Session, Trade


def get_current_balance() -> float:
  """Return BANKROLL + sum of actual_profit for all settled (won/lost) trades."""
  if not Session:
    return BANKROLL
  session = None
  try:
    session = Session()
    from sqlalchemy import func
    total = session.query(func.coalesce(func.sum(Trade.actual_profit), 0)).filter(
      Trade.status.in_(["won", "lost"]),
      Trade.actual_profit.isnot(None),
    ).scalar()
    return BANKROLL + (float(total) if total is not None else 0)
  except Exception:
    return BANKROLL
  finally:
    if session:
      try:
        session.close()
      except Exception:
        pass
