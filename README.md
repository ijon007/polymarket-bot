# Polymarket Bot

Monorepo: **dashboard** (Next.js), **bot** (Python), **convex** (backend).

---

## 1. Install Bun

```bash
# Windows (PowerShell)
irm bun.sh/install.ps1 | iex

# macOS/Linux
curl -fsSL https://bun.sh/install | bash
```

---

## 2. Convex setup

1. Go to [convex.dev](https://convex.dev) and sign in.
2. Create a new project (e.g. `polymarket-bot`).
3. You’ll get a **Deployment URL** — you’ll add it as `CONVEX_URL` in the next step.

---

## 3. Env

From repo root:

```bash
cp .env.example .env.local
```

Edit `.env.local` and set:

- **CONVEX_URL** — from your Convex project (Dashboard → Settings → Deployment URL), or leave empty and let `bun run convex:dev` fill it.

Running `bun run convex:dev` once will append `CONVEX_DEPLOYMENT` and `CONVEX_URL` to `.env.local` if you’re logged in to Convex.

**Bot** uses the root `.env.local` when you run from root. To run the bot from `apps/bot` only, copy `.env.local` to `apps/bot/.env.local` or set `CONVEX_URL` there.

---

## 4. Install and run

```bash
bun install
```

| Command | What it does |
|--------|----------------|
| `bun run convex:dev` | Convex backend (keep running; writes CONVEX_URL to .env.local) |
| `bun run dashboard:dev` | Next.js dashboard |
| `bun run bot:start` | Python trading bot |

**Suggested order:** start `convex:dev` first, then either `dashboard:dev` or `bot:start`.

---

## 5. Bot scripts (from root)

| Script | Purpose |
|--------|--------|
| `bun run bot:check-db` | Check DB schema before running bot |
| `bun run bot:init-db` | Initialize DB |
| `bun run bot:pnl-summary` | PnL summary |
| `bun run bot:settle-now` | Settle positions |

---

## 6. Bot-only (no monorepo)

```bash
cd apps/bot
pip install -r requirements.txt
# Set CONVEX_URL in .env.local (from Convex dashboard or `npx convex dev` at repo root)
python main.py
```
