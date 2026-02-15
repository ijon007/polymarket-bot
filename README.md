# BTC 5-Minute Multi-Strategy Bot

Tests multiple trading strategies on Polymarket BTC 5-minute markets.

## Strategies

1. **Arbitrage** (enabled): Buy both YES+NO when total < $0.98
2. **Mean Reversion** (enabled): Bet against overpriced outcomes (>60¢)
3. **Momentum** (disabled): Follow BTC price trend via Chainlink
4. **Last Second** (disabled): Bet on winner in final 30s
5. **Spread Capture** (disabled): Market maker strategy

## Monorepo structure

- **apps/dashboard** — Next.js dashboard
- **apps/bot** — Python trading bot
- **convex/** — Shared Convex backend (run from root)

### Running from root

```bash
bun install
bun run convex:dev          # Convex backend (creates CONVEX_URL in .env.local)
bun run dashboard:dev       # Dashboard
bun run bot:start           # Bot (requires .env.local in apps/bot with CONVEX_URL)
bun run bot:check-db        # Verify DB schema before running bot
```

### Bot setup

1. Copy `apps/bot/.env.example` to `apps/bot/.env.local`
2. Run `bun run convex:dev` from root to get `CONVEX_URL`, then add it to `apps/bot/.env.local`
3. `pip install -r apps/bot/requirements.txt` (or use a venv in apps/bot)
4. `bun run bot:start` or `cd apps/bot && python main.py`

## Quick Start (bot only)

```bash
cd apps/bot
pip install -r requirements.txt
# Set CONVEX_URL in .env.local (from npx convex dev)
python main.py
```

## Toggle Strategies

Edit `apps/bot/src/config.py`:

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
