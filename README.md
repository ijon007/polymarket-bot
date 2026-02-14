# BTC 5-Minute Arbitrage Bot

Scans Polymarket for BTC 5-minute up/down markets and executes arbitrage when YES + NO prices < $0.98.

## Setup

1. Install: `pip install -r requirements.txt`
2. Create Neon database at neon.tech
3. Copy `.env.example` to `.env` and add DATABASE_URL
4. Run: `python main.py`

## Strategy

- Scan every 10 seconds for BTC 5min markets
- Check if YES price + NO price < $0.98
- If yes → buy both sides (guaranteed profit)
- Paper trade mode (logs to database, doesn't execute)

## Database

Check trades: `SELECT * FROM trades ORDER BY executed_at DESC;`
