# BTC 5-Minute Multi-Strategy Bot

Tests multiple trading strategies on Polymarket BTC 5-minute markets.

## Strategies

1. **Arbitrage** (enabled): Buy both YES+NO when total < $0.98
2. **Mean Reversion** (enabled): Bet against overpriced outcomes (>60¢)
3. **Momentum** (disabled): Follow BTC price trend via Chainlink
4. **Last Second** (disabled): Bet on winner in final 30s
5. **Spread Capture** (disabled): Market maker strategy

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Toggle Strategies

Edit `src/config.py`:

```python
STRATEGIES = {
    "arbitrage": {"enabled": True, ...},
    "mean_reversion": {"enabled": False, ...},
    ...
}
```

## View Results

```sql
-- See which strategies are working
SELECT strategy, COUNT(*), AVG(expected_profit)
FROM trades
GROUP BY strategy;

-- View all trades
SELECT * FROM trades ORDER BY executed_at DESC LIMIT 10;
```

## Testing Different Strategies

To test a strategy:

1. Set `enabled: True` in config
2. Adjust parameters (min_edge, position_size, etc.)
3. Run bot for 1-2 hours
4. Check database for results
5. Compare performance across strategies
