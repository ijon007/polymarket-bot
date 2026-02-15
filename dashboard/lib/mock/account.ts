import type { AccountSummary } from "@/types/dashboard";

// From bot: equity = get_current_balance(); winRate = settled wins / settled trades; totalPnl/realized from DB; todayPnl = P&L last 24h
export const mockAccount: AccountSummary = {
  equity: 1_247.83,
  winRate: 62.4,
  totalPnl: 247.83,
  totalPnlPct: 24.78,
  realizedPnl: 189.50,
  todayPnl: 12.40,
};
