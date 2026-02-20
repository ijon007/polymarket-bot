"use client";

import { useQuery } from "convex/react";
import { api } from "@convex/_generated/api";
import type {
  AccountSummary,
  BotAnalytics,
  LogEntry,
  StreakGraph,
  StreakTradeEntry,
  SystemStatus,
  SystemStatusEntry,
  TradeRow,
} from "@/types/dashboard";
import { useDataMode } from "@/lib/data-mode-context";
import { mockAccount } from "@/lib/mock/account";
import { mockAnalytics } from "@/lib/mock/analytics";
import { mockStreakGraph } from "@/lib/mock/streak";
import { mockSystemStatus } from "@/lib/mock/system";

const INITIAL_BALANCE = 10;

function mapSide(side: string): "UP" | "DOWN" {
  if (side === "YES") return "UP";
  if (side === "NO") return "DOWN";
  return "UP";
}

/** Convex stores executed_at/settled_at in ms (bot sends ms). */
function toMs(ts: number): number {
  return ts >= 1e12 ? ts : ts * 1000;
}

function formatExecutedAt(ts: number): string {
  return new Date(toMs(ts)).toISOString().slice(0, 16).replace("T", " ");
}

function formatExecutedAtLocal(ts: number): string {
  const d = new Date(toMs(ts));
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${mo}-${day} ${h}:${min}`;
}

function computeStreak(history: StreakTradeEntry[]): { currentStreak: number; streakType: "W" | "L" } {
  if (history.length === 0) return { currentStreak: 0, streakType: "W" };
  const last = history[history.length - 1].outcome;
  let count = 0;
  for (let i = history.length - 1; i >= 0 && history[i].outcome === last; i--) count++;
  return { currentStreak: count, streakType: last === "won" ? "W" : "L" };
}

export function useDashboardAnalytics(): BotAnalytics {
  const { dataMode } = useDataMode();
  const data = useQuery(api.trades.dashboardAnalytics, { dataMode });
  if (data === undefined) return mockAnalytics;
  return {
    totalTrades: data.totalTrades,
    settled: data.settled,
    pending: data.pending,
    totalPnl: data.totalPnl,
    bestTrade: data.bestTrade,
    worstTrade: data.worstTrade,
  };
}

export function useDashboardAccount(initialBalance?: number): AccountSummary {
  const { dataMode } = useDataMode();
  const balance = initialBalance ?? INITIAL_BALANCE;
  const analytics = useQuery(api.trades.dashboardAnalytics, { dataMode });
  const todayPnl = useQuery(api.trades.dashboardTodayPnl, { dataMode });
  if (analytics === undefined || todayPnl === undefined) return mockAccount;
  const { totalPnl, wonCount, lostCount } = analytics;
  const settledCount = wonCount + lostCount;
  const winRate = settledCount > 0 ? (wonCount / settledCount) * 100 : 0;
  const totalPnlPct = balance > 0 ? (totalPnl / balance) * 100 : 0;
  const equity = balance + totalPnl;
  return {
    equity,
    winRate,
    totalPnl,
    totalPnlPct,
    realizedPnl: totalPnl,
    todayPnl,
  };
}

export function useStreakFromConvex(): StreakGraph {
  const { dataMode } = useDataMode();
  const settled = useQuery(api.trades.dashboardSettledForStreak, { limit: 40, dataMode });
  if (settled === undefined) return mockStreakGraph;
  const history: StreakTradeEntry[] = [...settled]
    .reverse()
    .map((t) => ({
      outcome: t.status === "won" ? ("won" as const) : ("lost" as const),
      pnl: t.actual_profit ?? 0,
      executedAt: formatExecutedAtLocal(t.settled_at ?? t.executed_at),
      side: mapSide(t.side),
    }));
  const { currentStreak, streakType } = computeStreak(history);
  return { history, currentStreak, streakType };
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function usePositions(): TradeRow[] {
  const { dataMode } = useDataMode();
  const data = useQuery(api.trades.listForDashboard, { dataMode });
  if (data === undefined) return [];
  return data.map((t) => {
    const market = t.market_ticker ?? "";
    const interval = market.includes("-15m-") ? ("15m" as const) : ("5m" as const);
    return {
      id: t._id,
      market,
      question: t.question ?? "",
      side: t.side,
      price: t.price ?? t.yes_price ?? t.no_price ?? 0,
      size: t.size ?? t.position_size ?? 0,
      pnl: t.actual_profit ?? 0,
      status: t.status === "paper" ? ("paper" as const) : ("settled" as const),
      executedAt: formatExecutedAtLocal(t.executed_at),
      strategy: t.strategy,
      signalType: t.signal_type,
      interval,
    };
  });
}

export function useLogEntries(): LogEntry[] {
  const batches = useQuery(api.logBatches.listRecent, {});
  if (batches === undefined) return [];
  const entries: LogEntry[] = [];
  for (const batch of batches) {
    for (const e of batch.entries) {
      entries.push({
        timestamp: e.timestamp,
        level: (e.level === "WARN" || e.level === "ERROR" ? e.level : "INFO") as LogEntry["level"],
        message: e.message,
      });
    }
  }
  entries.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  return entries;
}

function toSystemStatus(data: { engine_state: string; polymarket_ok: boolean; db_ok: boolean; rtds_ok: boolean; uptime_seconds: number; scan_interval: number }): SystemStatus {
  return {
    engineState: data.engine_state as SystemStatus["engineState"],
    connections: [
      { label: "Polymarket API", connected: data.polymarket_ok },
      { label: "Database", connected: data.db_ok },
      { label: "RTDS (Chainlink)", connected: data.rtds_ok },
    ],
    uptime: formatUptime(data.uptime_seconds),
    scanInterval: data.scan_interval,
  };
}

export function useSystemStatus(): SystemStatus {
  const data = useQuery(api.systemStatus.get, {});
  if (!data) return mockSystemStatus;
  return toSystemStatus(data);
}

export function useSystemStatusAll(): SystemStatusEntry[] {
  const data = useQuery(api.systemStatus.getAll, {});
  if (data === undefined || data.length === 0) return [];
  const keys = ["5min", "15min"];
  return data
    .filter((d) => keys.includes(d.key))
    .sort((a, b) => keys.indexOf(a.key) - keys.indexOf(b.key))
    .map((d) => ({ key: d.key, status: toSystemStatus(d) }));
}
