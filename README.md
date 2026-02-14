# Polymarket Trading Bot

Minimal scaffold for a Python-based Polymarket trading bot (scanner, logic/arb/value logic, executor, Neon DB).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys and database URL
```

## Getting a Neon Database URL

1. Sign up at [Neon](https://neon.tech).
2. Create a project and a database.
3. Copy the connection string from the dashboard (e.g. `postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`).
4. Set `DATABASE_URL` in `.env` to that value.

## API Keys

- **Polymarket**: From [Polymarket](https://polymarket.com) (API / CLOB credentials).
- **Groq**: From [Groq Cloud](https://console.groq.com) (for LLM/sentiment).
- **Twitter**: From [Twitter Developer Portal](https://developer.twitter.com) (API key for sentiment).
- **Reddit**: From [Reddit Apps](https://www.reddit.com/prefs/apps) (create an app; use client ID and secret).

## Running the Bot

```bash
# From project root, with .env configured
python -m src.bot.main
```

Or set `PYTHONPATH=.` and run `python src/bot/main.py` from the project root.
