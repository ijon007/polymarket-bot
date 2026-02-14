#!/usr/bin/env python3
"""Print realized P&L summary from trades table."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, Session, Trade

def main():
  init_db()
  if not Session:
    print("DATABASE_URL not set")
    return 1

  session = Session()
  try:
    settled = session.query(Trade).filter(Trade.actual_profit.isnot(None)).all()
    total = sum(t.actual_profit or 0 for t in settled)
    won = sum(1 for t in settled if (t.actual_profit or 0) > 0)
    lost = sum(1 for t in settled if (t.actual_profit or 0) < 0)

    print("=" * 50)
    print("REALIZED P&L SUMMARY")
    print("=" * 50)
    print(f"Total trades settled: {len(settled)}")
    print(f"Won: {won} | Lost: {lost}")
    print(f"Total P&L: ${total:,.2f}")
    print("=" * 50)

    if settled:
      print("\nPer trade:")
      for t in settled:
        pnl = t.actual_profit or 0
        sign = "+" if pnl >= 0 else ""
        print(f"  #{t.id} | {t.market_ticker} | {t.side} @ {(t.price or 0):.2f} | {sign}${pnl:.2f} | {t.status}")

  finally:
    session.close()
  return 0

if __name__ == "__main__":
  sys.exit(main())
