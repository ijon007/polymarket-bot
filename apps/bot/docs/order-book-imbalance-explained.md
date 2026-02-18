# Order Book Imbalance Strategy — Explained

## What is an Order Book?

An order book shows all pending buy orders (bids) and sell orders (asks) for a token.

**Example order book for YES token:**

```
Bids (people want to BUY YES):
  Price  Size
  0.52   100
  0.51   50
  0.50   200

Asks (people want to SELL YES):
  Price  Size
  0.53   75
  0.54   150
  0.55   80
```

- **Bid** = someone wants to buy at that price (they're bullish on YES)
- **Ask** = someone wants to sell at that price (they're bearish on YES)

## Binary Market Context

In a 15-min BTC up/down market:

- **YES token** = "BTC will be UP at end of window"
- **NO token** = "BTC will be DOWN at end of window"

Each token has its own order book (YES book + NO book).

## How the Strategy Calculates Imbalance

### Step 1: Aggregate Volume Across Both Books

The code sums up **bid volume** and **ask volume** from **top 5 levels** of both YES and NO books:

```python
bid_vol = sum(YES_bids[0:5].size) + sum(NO_bids[0:5].size)
ask_vol = sum(YES_asks[0:5].size) + sum(NO_asks[0:5].size)
```

**What this means:**

- **bid_vol** = total size of people wanting to **buy** (either YES or NO) = bullish pressure
- **ask_vol** = total size of people wanting to **sell** (either YES or NO) = bearish pressure

### Step 2: Calculate Imbalance Ratio

```python
imbalance = (bid_vol - ask_vol) / (bid_vol + ask_vol)
```

**Result range:** -1.0 to +1.0

- **+1.0** = all bids, no asks (extremely bullish)
- **0.0** = balanced (equal bids and asks)
- **-1.0** = all asks, no bids (extremely bearish)

### Step 3: Rolling Average (30 seconds)

The code keeps a rolling window of 60 samples (60 × 500ms = 30 seconds):

```python
imbalance_avg = average of last 60 imbalance values
```

This smooths out noise and gives a more stable signal.

### Step 4: Signal Threshold

**Default threshold:** `IMBALANCE_THRESHOLD = 0.4`

- If `imbalance_avg > 0.4` → **Bet YES** (bullish pressure)
- If `imbalance_avg < -0.4` → **Bet NO** (bearish pressure)
- Otherwise → No trade

## Example Scenarios

### Scenario 1: Strong Bullish Imbalance

```
YES book bids: 200, 150, 100, 80, 60  = 590 total
YES book asks: 50, 40, 30, 20, 10     = 150 total
NO book bids:  100, 80, 60, 40, 30    = 310 total
NO book asks:  200, 150, 100, 80, 60   = 590 total

bid_vol = 590 + 310 = 900
ask_vol = 150 + 590 = 740

imbalance = (900 - 740) / (900 + 740) = 160 / 1640 = 0.098
```

Wait, that's only 0.098, not above 0.4. Let me recalculate with stronger imbalance:

```
bid_vol = 1000
ask_vol = 200

imbalance = (1000 - 200) / (1000 + 200) = 800 / 1200 = 0.667 ✅ Above 0.4 → Bet YES
```

### Scenario 2: Strong Bearish Imbalance

```
bid_vol = 200
ask_vol = 1000

imbalance = (200 - 1000) / (200 + 1000) = -800 / 1200 = -0.667 ✅ Below -0.4 → Bet NO
```

## Why This Might Work

The idea is that **order book imbalance predicts short-term price movement**:

- More bids = more buying pressure = price likely to go up
- More asks = more selling pressure = price likely to go down

In a 15-min window, if there's sustained imbalance (30s average), it might indicate where the market is heading.

## Potential Issues

1. **Liquidity:** If the book is thin (low volume), imbalance can be noisy
2. **Market makers:** Large orders might be spoofing (fake orders that disappear)
3. **Timing:** 15-min window is short; imbalance might not persist long enough
4. **Threshold:** 0.4 might be too high (rarely triggers) or too low (too many false signals)

## Current Implementation

- **Window:** 30-second rolling average (60 samples × 500ms)
- **Threshold:** 0.4 (configurable via `IMBALANCE_THRESHOLD` env var)
- **Top levels:** Uses top 5 price levels from each book
- **Stale check:** Skips tick if order book hasn't updated recently

## Tuning the Strategy

To make it more/less sensitive:

- **Lower threshold** (e.g., 0.2) → More trades, more false signals
- **Higher threshold** (e.g., 0.6) → Fewer trades, stronger signals only
- **Change window** (e.g., 60 samples = 30s, 120 samples = 60s) → Longer = smoother but slower to react

