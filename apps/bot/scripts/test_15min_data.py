#!/usr/bin/env python3
"""
Test 15-min signal engine data sources (imbalance-only). No trade wait.

Usage (from apps/bot):
  python scripts/test_15min_data.py market    # 15-min market fetch
  python scripts/test_15min_data.py rtds       # BTC price feed
  python scripts/test_15min_data.py orderbook  # Polymarket WS order book + imbalance
  python scripts/test_15min_data.py all        # market, rtds, orderbook
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger


def test_market() -> bool:
  """Fetch current 15-min BTC market."""
  from src.scanner_15min import fetch_btc_15min_market
  logger.info("Testing 15-min market fetch...")
  market = fetch_btc_15min_market()
  if not market:
    logger.warning("No active 15-min market found (might be between windows or API issue)")
    return False
  slug = market.get("slug", "?")
  tokens = market.get("tokens") or {}
  yes_id = tokens.get("yes")
  no_id = tokens.get("no")
  y = (yes_id[:8] + ".." + yes_id[-8:] if yes_id and len(yes_id) > 16 else yes_id) if yes_id else None
  n = (no_id[:8] + ".." + no_id[-8:] if no_id and len(no_id) > 16 else no_id) if no_id else None
  logger.info(
    f"OK | slug={slug} | yes_id={y} | no_id={n} | seconds_left={market.get('seconds_left')}"
  )
  return bool(yes_id and no_id)


def test_rtds() -> bool:
  """Start RTDS, wait a few seconds, print BTC price and 60s move."""
  from src.utils.rtds_client import start as rtds_start, stop as rtds_stop, get_latest_btc_usd, get_btc_move_60s
  logger.info("Testing RTDS (BTC price)...")
  rtds_start()
  for _ in range(12):
    time.sleep(0.5)
    if get_latest_btc_usd() is not None:
      break
  btc = get_latest_btc_usd()
  move = get_btc_move_60s()
  rtds_stop()
  if btc is None:
    logger.warning("RTDS: no BTC price after 6s (check network / Polymarket RTDS)")
    return False
  move_str = f"{move*100:.2f}%" if move is not None else "N/A"
  logger.info(f"OK | BTC=${btc:,.2f} | 60s move={move_str}")
  return True


def test_orderbook(duration_sec: int = 45) -> bool:
  """Fetch market, start Polymarket WS, print book + imbalance for duration."""
  from src.scanner_15min import fetch_btc_15min_market
  from src.ws_polymarket import start as ws_start, stop as ws_stop, get_best_asks, get_imbalance_data
  logger.info("Testing Polymarket order book (WS)...")
  market = fetch_btc_15min_market()
  if not market:
    logger.warning("No 15-min market — cannot get token IDs for WS.")
    return False
  tokens = market.get("tokens") or {}
  yes_id, no_id = tokens.get("yes"), tokens.get("no")
  if not yes_id or not no_id:
    logger.warning("Market has no token IDs")
    return False
  ws_start(yes_id, no_id)
  logger.info(f"WS started. Sampling for {duration_sec}s (best ask, imbalance)...")
  updates = 0
  start = time.time()
  while time.time() - start < duration_sec:
    time.sleep(1)
    yes_ask, no_ask = get_best_asks()
    bid_vol, ask_vol, stale = get_imbalance_data()
    total = bid_vol + ask_vol
    imb = (bid_vol - ask_vol) / total if total > 0 else 0.0
    updates += 1
    if updates <= 3 or updates % 10 == 0:
      logger.info(
        f"  yes_ask={yes_ask} no_ask={no_ask} | bid_vol={bid_vol:.1f} ask_vol={ask_vol:.1f} "
        f"imbalance={imb:+.2f} stale={stale}"
      )
  ws_stop()
  if yes_ask is None and no_ask is None:
    logger.warning("Order book: no best asks (WS may not be receiving book updates)")
    return False
  logger.info("OK | Order book and imbalance are updating.")
  return True


def main():
  import argparse
  p = argparse.ArgumentParser(description="Test 15-min data sources (imbalance-only)")
  p.add_argument(
    "target",
    choices=["market", "rtds", "orderbook", "all"],
    help="Which feed to test",
  )
  p.add_argument("--orderbook-duration", type=int, default=45, help="Seconds for orderbook test (default 45)")
  args = p.parse_args()

  if args.target == "all":
    ok = True
    ok &= test_market()
    time.sleep(2)
    ok &= test_rtds()
    ok &= test_orderbook(duration_sec=min(30, args.orderbook_duration))
    logger.info("All done." if ok else "Some checks failed or skipped.")
    return 0 if ok else 1
  elif args.target == "market":
    ok = test_market()
  elif args.target == "rtds":
    ok = test_rtds()
  else:
    ok = test_orderbook(duration_sec=args.orderbook_duration)
  return 0 if ok else 1


if __name__ == "__main__":
  sys.exit(main())
