# Polymarket Bot

Minimal scaffold for a Python-based Polymarket trading bot.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy the example env file and fill in your values:

   ```bash
   cp .env.example .env
   ```

## Neon database

1. Sign up at [neon.tech](https://neon.tech).
2. Create a new project and database.
3. Copy the connection string from the dashboard.
4. Set `DATABASE_URL` in `.env`. Use the PostgreSQL URL with `?sslmode=require` at the end (e.g. `postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`).

## Groq API key

1. Get a free API key at [groq.com](https://groq.com).
2. Set `GROQ_API_KEY=your_key_here` in `.env`.

## Run the bot

From the project root:

```bash
python -m src.bot.main
```

Or run the main module directly:

```bash
python src/bot/main.py
```

(Implement a `if __name__ == "__main__": run()` in `main.py` if you want the second form to work.)
