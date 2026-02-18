# 15-Min Signal Engine — Order Book & Late Entry V3

**Current strategy:** Late Entry V3 (replaces the previous imbalance-based strategy).

**Markets:** Runs on all four 15-min crypto markets when available: BTC, ETH, SOL, XRP. Configure via `LATE_ENTRY_15MIN_ASSETS` (comma-separated, default `btc,eth,sol,xrp`).

---

## Late Entry V3 (Current)

Enter only in the last 4 minutes. Follow the crowd: buy the side with the **higher best ask** (market consensus). Require a 30% price gap between YES and NO. Size by time remaining.


| Step | Rule                                                                         |
| ---- | ---------------------------------------------------------------------------- |
| 1    | Enter only when `0 < seconds_left <= 240` (last 4 minutes).                  |
| 2    | **Favorite** = side with higher best ask (YES if yes_ask > no_ask, else NO). |
| 3    | **Confidence filter:** only enter if `                                       |
| 4    | **Size by time:** 180–240s left → 8 USD; 120–180s → 10 USD; 0–120s → 12 USD. |
| 5    | **Max price:** skip if favorite's ask > 0.92 (avoid overpaying).             |


**Config (env vars):** `LATE_ENTRY_WINDOW_SEC`, `LATE_ENTRY_MIN_GAP`, `LATE_ENTRY_MAX_PRICE`, `LATE_ENTRY_SIZE_240_180`, `LATE_ENTRY_SIZE_180_120`, `LATE_ENTRY_SIZE_120_0`.

**Inspect:** Run `python scripts/inspect_orderbook.py` to see live book and whether Late Entry would fire.

---

## Order book data (correctness)

- **Source:** Polymarket CLOB WebSocket [market channel](https://docs.polymarket.com/developers/CLOB/websocket/market-channel) (`wss://.../ws/market`). Subscribe with `assets_ids` = token IDs, `type` = `"market"`.
- **Token IDs:** Same as CLOB/Gamma: from `market["tokens"]["yes"]` and `["no"]`, populated from Gamma API `clobTokenIds` (first = YES, second = NO). These are the asset IDs the WS expects.
- **Book message:** We handle both doc variants: `bids`/`asks` and `buys`/`sells`. Each level has `price` and `size` (we parse as float). `event_type` must be `"book"`; `asset_id` identifies the token.
- **Best ask (used by Late Entry V3):** We take the **lowest** ask as best ask. Levels are normalized to asks ascending (best first), bids descending (best first), so `asks[0]` and `bids[0]` are correct regardless of send order. Imbalance uses the top 5 levels per side (same ordering).
- **Sanity check:** Run `python scripts/inspect_orderbook.py` and compare `yes_ask`/`no_ask` and levels to Polymarket’s UI or REST `get_order_book` for the same token IDs if needed.

