#!/usr/bin/env python3
"""Print realized P&L summary from trades table."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, list_settled_trades, is_db_configured


def main():
  init_db()
  if not is_db_configured():
    print("CONVEX_URL not set")
    return 1

  settled = list_settled_trades()
  total = sum(t.get("actual_profit") or 0 for t in settled)
  won = sum(1 for t in settled if (t.get("actual_profit") or 0) > 0)
  lost = sum(1 for t in settled if (t.get("actual_profit") or 0) < 0)

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
      pnl = t.get("actual_profit") or 0
      sign = "+" if pnl >= 0 else ""
      tid = t.get("_id", "?")
      print(f"  #{tid} | {t.get('market_ticker')} | {t.get('side')} @ {(t.get('price') or 0):.2f} | {sign}${pnl:.2f} | {t.get('status')}")

  return 0


if __name__ == "__main__":
  sys.exit(main())
