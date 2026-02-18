# 15-Minute BTC Strategy — Analysis

## What the current engine does

- **Entrypoint:** `main_15min.py` → RTDS + fetch 15-min market → Polymarket WS (order book) → `signal_engine.run_loop()` (500ms tick).
- **Signals (priority order):**
  1. **P1 Mispricing** — Fire immediately: (a) arb: YES_ask + NO_ask < 0.97, or (b) one-sided: YES_ask or NO_ask < 0.45.
  2. **P2 Whale** — Layering / sweep / iceberg / spoof on the order book.
  3. **P3 Imbalance** — 30s rolling (bid_vol − ask_vol) / (bid_vol + ask_vol), threshold ±0.4.
  4. **P4 Momentum** — Last 3 resolved **5-min** outcomes (same direction) from DB.
- **Combined entry:** If P1 does not fire, then require **2+ of P2, P3, P4** in the same direction (YES or NO), then apply a “last-second” gate and execute.

---

## Broken / questionable

### 1. P1 Mispricing is wrong for a 15-min binary

- In a binary market **YES + NO ≈ 1** (minus spread). So:
  - **Arb (yes_ask + no_ask < 0.97):** Real arbitrage will almost never appear; if it does, it’s tiny and disappears instantly. So this branch is effectively dead or noise.
  - **One-sided “undervalued” (ask < 0.45):** That’s just the market’s implied probability, not mispricing. If YES_ask is 0.45, NO_ask is ~0.55; there’s no free lunch.
- **Conclusion:** P1 is useless for a 15-min BTC market and can be removed.

### 2. `market_repriced` is never used

- `_last_second_gate(..., market_repriced=False)` is always called with `False`.
- So the “only allow if market hasn’t repriced” logic is dead; the gate only checks (a) BTC near strike or (b) |BTC move 60s| ≥ 0.3%.

### 3. Last-second gate window is narrow and misnamed

- `_LAST_SECOND_START = 40`, `_LAST_SECOND_END = 25` → block only when **40 ≥ seconds_left > 25** (a 15s band).
- Outside that band we never block, so we **allow entries in the last 25 seconds** with no extra check. The name suggests “last second” but the logic is a small middle window.

### 4. P4 Momentum depends on another process

- `list_last_5m_outcomes(3)` reads **5-min** resolved outcomes from Convex (written by the 5-min bot on settlement).
- If the 5-min bot isn’t running or no 5-min markets are settled, this always returns `[]` and P4 never contributes. So the combined signal often has only P2+P3, and momentum is unreliable unless both bots run.

### 5. 15-min settlement does not use RTDS

- `resolve_outcome_via_rtds()` only parses `btc-updown-5m-*` slugs. 15-min markets (`btc-updown-15m-*`) are never resolved via RTDS; resolution is Gamma-only. So 15-min settlement is correct but slower (depends on Gamma marking the market closed).

---

## Useless / overdone

1. **P1 (mispricing + arb)** — As above; remove.
2. **`bet_both` / arbitrage path** — Tied to P1; in practice never meaningfully triggers; paper-only. Can remove with P1.
3. **Four-signal combo (P2+P3+P4, need 2+)** — Complex; rarely all align; P4 is often empty. Hard to debug “what worked.”
4. **Whale thresholds** — `_LAYERING_SIZE_THRESHOLD = 50` (USD): in thin 15-min books this may never fire; in thick books it may fire too often. Not tuned for 15-min.

---

## Recommendation: strip to one signal

- **Remove:** P1 (mispricing + arb), P2 (whale), P4 (momentum), combined 2-of-3 logic, and the unused `market_repriced` path.
- **Keep one signal:** **Order book imbalance (P3)** — single source, no dependency on 5-min bot or whale size, easy to log and tune.
- **Optional later:** Re-add one other signal (e.g. whale or momentum) once imbalance-only is understood and working.

---

## Files touched for “imbalance-only” strip-down

- `apps/bot/src/signal_engine.py` — Remove P1, P2, P4; keep only imbalance (P3) with a simple threshold; keep last-second gate only if desired (or simplify to “no entry in last N seconds” if needed).
- Config: `MISPRICING_THRESHOLD` / mispricing-related env can be ignored or removed from the 15-min path.
- `apps/bot/src/executor.py` — `bet_both` can remain for compatibility but will never be used by the stripped engine.
- `apps/bot/src/ws_polymarket.py` — Whale detection can stay (no harm); we just don’t use it in the engine.
