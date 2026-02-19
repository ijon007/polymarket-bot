#!/usr/bin/env python3
"""
Inspect live 15-min order book: dump levels, volumes, and whether Late Entry V3
would fire. Run from apps/bot.

  python scripts/inspect_orderbook.py                    # BTC, 60s, print every 5s
  python scripts/inspect_orderbook.py -a eth             # ETH
  python scripts/inspect_orderbook.py -a sol -d 120 -i 2 # SOL, 120s, print every 2s
  python scripts/inspect_orderbook.py -a xrp             # XRP

Assets: btc, eth, sol, xrp (config: LATE_ENTRY_15MIN_ASSETS).
"""
import sys
import os
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from src.config import (
  LATE_ENTRY_15MIN_ASSETS,
  LATE_ENTRY_MAX_PRICE,
  LATE_ENTRY_MIN_GAP,
  LATE_ENTRY_WINDOW_SEC,
)


def _format_book(name: str, book, top: int = 5) -> str:
  if not book:
    return f"{name}: (no data)"
  lines = [f"{name}:"]
  bids = (book.bids or [])[:top]
  asks = (book.asks or [])[:top]
  for i, lev in enumerate(bids):
    lines.append(f"  bid {i+1}: price={lev.price:.4f} size={lev.size:.1f}")
  if not bids:
    lines.append("  (no bids)")
  for i, lev in enumerate(asks):
    lines.append(f"  ask {i+1}: price={lev.price:.4f} size={lev.size:.1f}")
  if not asks:
    lines.append("  (no asks)")
  return "\n".join(lines)


def main():
  p = argparse.ArgumentParser(description="Inspect 15-min order book and Late Entry V3")
  p.add_argument("-a", "--asset", type=str, default="btc",
    choices=LATE_ENTRY_15MIN_ASSETS,
    help="Asset to inspect: " + ", ".join(LATE_ENTRY_15MIN_ASSETS) + " (default btc)")
  p.add_argument("-d", "--duration", type=int, default=60, help="Seconds to run (default 60)")
  p.add_argument("-i", "--interval", type=float, default=5.0, help="Print every N seconds (default 5)")
  args = p.parse_args()

  from src.scanner_15min import fetch_15min_markets
  from src.ws_polymarket import (
    start as ws_start,
    stop as ws_stop,
    get_best_asks,
    get_imbalance_data,
    get_order_books_snapshot,
  )

  markets = fetch_15min_markets(assets=[args.asset])
  market = markets[0] if markets else None
  if not market:
    logger.error("No active 15-min market. Try again when a window is open.")
    return 1
  tokens = market.get("tokens") or {}
  yes_id, no_id = tokens.get("yes"), tokens.get("no")
  if not yes_id or not no_id:
    logger.error("Market missing token IDs")
    return 1

  slug = market.get("slug", "?")
  logger.info(f"Connecting to order book for {slug} (duration={args.duration}s, print every {args.interval}s)")
  ws_start(yes_id, no_id)

  start = time.time()
  last_print = 0.0
  sample_count = 0
  would_fire_count = 0

  try:
    while time.time() - start < args.duration:
      time.sleep(0.5)
      now = time.time()
      if now - last_print < args.interval:
        continue
      last_print = now
      sample_count += 1

      markets = fetch_15min_markets(assets=[args.asset])
      market = markets[0] if markets else None
      seconds_left = market.get("seconds_left", 0) if market else 0

      yes_book, no_book, stale = get_order_books_snapshot()
      yes_ask, no_ask = get_best_asks()
      bid_vol, ask_vol, _ = get_imbalance_data()
      total = bid_vol + ask_vol
      imb = (bid_vol - ask_vol) / total if total > 0 else 0.0

      # Late Entry V3: would it fire?
      in_window = 0 < seconds_left <= LATE_ENTRY_WINDOW_SEC
      if yes_ask is not None and no_ask is not None and in_window:
        if yes_ask > no_ask:
          favorite = "YES"
          favorite_ask = yes_ask
        elif no_ask > yes_ask:
          favorite = "NO"
          favorite_ask = no_ask
        else:
          favorite = None
          favorite_ask = None
        if favorite is not None:
          gap = abs(yes_ask - no_ask)
          would_fire = (
            gap >= LATE_ENTRY_MIN_GAP
            and favorite_ask <= LATE_ENTRY_MAX_PRICE
            and not stale
          )
          if would_fire:
            would_fire_count += 1
        else:
          would_fire = False
          gap = 0.0
      else:
        would_fire = False
        favorite = None
        gap = abs(yes_ask - no_ask) if (yes_ask is not None and no_ask is not None) else 0.0

      logger.info("---")
      logger.info(
        f"Sample #{sample_count} | stale={stale} | seconds_left={seconds_left} | "
        f"bid_vol={bid_vol:.1f} ask_vol={ask_vol:.1f} imbalance={imb:+.4f}"
      )
      logger.info(f"yes_ask={yes_ask} no_ask={no_ask} | gap={gap:.2f} (min={LATE_ENTRY_MIN_GAP})")
      if would_fire:
        logger.info(f"  -> LATE ENTRY WOULD FIRE: {favorite} (gap={gap:.2f})")
      elif in_window and yes_ask is not None and no_ask is not None:
        if favorite is None:
          logger.info("  -> no favorite (yes_ask == no_ask)")
        elif gap < LATE_ENTRY_MIN_GAP:
          logger.info(f"  -> gap too small ({gap:.2f} < {LATE_ENTRY_MIN_GAP})")
        elif favorite_ask > LATE_ENTRY_MAX_PRICE:
          logger.info(f"  -> favorite ask {favorite_ask:.2f} > max {LATE_ENTRY_MAX_PRICE}")
        else:
          logger.info("  -> no signal")
      else:
        logger.info("  -> outside entry window or no book data")
      logger.info(_format_book("YES", yes_book))
      logger.info(_format_book("NO", no_book))
  finally:
    ws_stop()

  logger.info("---")
  logger.info(f"Done. Samples={sample_count} | Late Entry would_fire={would_fire_count}")
  return 0


if __name__ == "__main__":
  sys.exit(main())
