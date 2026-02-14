#!/usr/bin/env python3
"""Run settlement once to mark resolved paper trades as won/lost."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, Session, Trade
from src.settlement import settle_trades, check_market_resolution


def main():
  init_db()
  if not Session:
    print("DATABASE_URL not set")
    return 1

  session = Session()
  try:
    unsettled = session.query(Trade).filter(Trade.status == "paper").all()
    if unsettled:
      slugs = set(t.market_ticker for t in unsettled if t.market_ticker and t.market_ticker != "unknown")
      print(f"Unsettled: {len(unsettled)} trade(s) on market(s): {', '.join(slugs)}")
      for slug in slugs:
        r = check_market_resolution(slug)
        print(f"  {slug}: closed={r.get('resolved')} outcome={r.get('outcome', 'N/A')}")
  finally:
    session.close()

  settle_trades()

  session = Session()
  try:
    still = session.query(Trade).filter(Trade.status == "paper").all()
    if still:
      print(f"Still unsettled after run: {len(still)} trade(s)")
    else:
      print("All paper trades settled.")
  finally:
    session.close()

  return 0


if __name__ == "__main__":
  sys.exit(main())
