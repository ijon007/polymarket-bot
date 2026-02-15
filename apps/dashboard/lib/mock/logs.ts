import type { LogEntry } from "@/types/dashboard";

// Messages match bot: main.py (BTC 5-Min Multi-Strategy), scanner, last_second strategy, executor paper trade, settlement, RTDS
export const mockLogs: LogEntry[] = [
  { timestamp: "2026-02-15 13:10:45", level: "INFO", message: "BTC 5-Minute Multi-Strategy Bot" },
  { timestamp: "2026-02-15 13:10:45", level: "INFO", message: "Database initialized" },
  { timestamp: "2026-02-15 13:10:45", level: "INFO", message: "Enabled strategies: 1" },
  { timestamp: "2026-02-15 13:10:45", level: "INFO", message: "  ✓ last_second" },
  { timestamp: "2026-02-15 13:10:46", level: "INFO", message: "No active market (between rounds)" },
  { timestamp: "2026-02-15 13:10:48", level: "INFO", message: "Strategy 'last_second' triggered!" },
  { timestamp: "2026-02-15 13:10:49", level: "INFO", message: "PAPER TRADE [LAST_SECOND]: Buy YES @ 0.5200 | Size: $10.00 | Confidence: 85% | Reason: 30s to window end" },
  { timestamp: "2026-02-15 13:10:50", level: "INFO", message: "Trade saved to DB: id=194 market=btc-updown-5m-1771083600" },
  { timestamp: "2026-02-15 13:10:50", level: "INFO", message: "Trade executed! Total opportunities: 1" },
  { timestamp: "2026-02-15 13:10:52", level: "INFO", message: "Market btc-updown-5m-1771083000 resolved via RTDS: YES (start=$97,250.00 end=$97,312.00)" },
  { timestamp: "2026-02-15 13:10:52", level: "INFO", message: "Settled trade #193 | Strategy: last_second | Action: NO | Outcome: NO | P&L: $6.10 | Status: WON" },
  { timestamp: "2026-02-15 13:11:00", level: "INFO", message: "No opportunities: btc-updown-5m-1771083600 | YES: 0.520, NO: 0.480" },
];
