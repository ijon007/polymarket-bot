# Mock data ↔ Bot data mapping

Mock data is aligned with what the Python bot actually stores and can expose.

## ACCOUNT (from `src/utils/balance.py`, `src/config.py`, `src/database.py`)

| Dashboard field   | Source |
|-------------------|--------|
| **equity**        | `get_current_balance()` |
| **winRate**       | (settled wins / settled trades) × 100 |
| **realizedPnl**   | Sum of `Trade.actual_profit` where `status` in (`won`, `lost`) |
| **totalPnl**      | equity − starting balance, or sum of realized + any unrealized |
| **totalPnlPct**   | (totalPnl / starting balance) * 100 |
| **todayPnl**      | Sum of `Trade.actual_profit` for trades settled in last 24h (or P&L since midnight UTC) |

## BOT ANALYTICS (from `src/database.py` Trade table)

| Dashboard field  | Source |
|-------------------|--------|
| **totalTrades**   | Count of all `Trade` rows |
| **settled**       | Count where `Trade.status` in (`won`, `lost`) — display as "Settled" |
| **pending**       | Count where `Trade.status == "paper"` |
| **totalPnl**      | Sum of `actual_profit` (settled) + unrealized (if any) |
| **bestTrade**     | Max `Trade.actual_profit` |
| **worstTrade**    | Min `Trade.actual_profit` |

## TRADES / ACTIVE POSITIONS (from `src/database.py` Trade)

| Dashboard field | DB column |
|-----------------|-----------|
| id              | `Trade.id` |
| market          | `Trade.market_ticker` (e.g. `btc-updown-5m-1771083600`) |
| question        | `Trade.question` |
| side            | `Trade.side` (YES / NO / ARBITRAGE) |
| price           | `Trade.price` |
| size            | `Trade.position_size` or `Trade.size` |
| pnl             | `Trade.actual_profit` (0 for paper) |
| status          | Map: `paper`→paper, `won`/`lost`→settled |
| executedAt      | `Trade.executed_at` (format for display) |

Bot only trades **BTC 5-minute** markets (`btc-updown-5m-{window_start_ts}`).

## SYSTEM STATUS (from `main.py`, `src/config.py`)

| Dashboard field   | Source |
|-------------------|--------|
| **engineState**   | Derived from main loop (e.g. SCANNING when running) — not stored; would need status API. |
| **scanInterval**  | `SCAN_INTERVAL` (config, default 10 seconds) |
| **connections**   | Polymarket API (gamma fetch), Database (Session), RTDS (Chainlink via `src/utils/rtds_client.py`) — not exposed; would need health checks. |
| **uptime**        | Not stored; would need process start time. |
| **memory**        | Not stored; would need process RSS. |

## CHARTS

- **Equity / PnL over time**: Bot has no `balance_history` table; only current balance via `get_current_balance()`. Charts require either mock data or a new table that records balance (or cumulative PnL) on each trade/settlement.

## LOGS

- Bot uses loguru; log lines are not persisted. To show live logs, the dashboard would need a log stream (e.g. WebSocket or tail of a log file) from the bot process. Mock log messages match bot behavior: strategy triggers, paper trades, settlement, RTDS resolution.
