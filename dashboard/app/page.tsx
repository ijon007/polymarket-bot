"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import {
  DashboardHeader,
  AccountSummary,
  ActivePositions,
  SystemStatus,
  LiveLogs,
  BotAnalytics,
  PnlChart,
  EquityChart,
  CardCorners,
  StreakCard,
} from "@/components/dashboard";
import type { DashboardFilter } from "@/components/dashboard/date-range-bar";
import { Toast } from "@/components/ui/toast";

import { mockSystemStatus } from "@/lib/mock/system";
import { mockAccount } from "@/lib/mock/account";
import { mockLogs } from "@/lib/mock/logs";
import { mockAnalytics, mockTrades } from "@/lib/mock/analytics";
import { mockStreakGraph } from "@/lib/mock/streak";

const defaultFilter: DashboardFilter = { positionSide: "all", status: "all" };

export default function Page() {
  const [lastUpdated, setLastUpdated] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    setLastUpdated(Date.now());
  }, []);

  const refreshData = useCallback(() => {
    setIsRefreshing(true);
    setLastUpdated(Date.now());
    setToastMessage("Data refreshed");
    setTimeout(() => setIsRefreshing(false), 400);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "r" && e.key !== "R") return;
      const t = e.target as HTMLElement;
      if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT") return;
      e.preventDefault();
      refreshData();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [refreshData]);

  const openPositions = useMemo(
    () => mockTrades.filter((t) => t.status !== "settled").length,
    []
  );

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-background font-mono transition-colors duration-200">
      <DashboardHeader
        lastUpdated={lastUpdated}
        onRefresh={refreshData}
        isRefreshing={isRefreshing}
        openPositions={openPositions}
      />

      <main className="flex min-h-0 flex-1 flex-col overflow-hidden p-2">
        {/* Layout: left sidebar | right (Charts, Positions, Logs) — no page overflow */}
        <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 overflow-hidden lg:grid-cols-12">
          {/* Left column: Account card, Bot Analytics, System Status */}
          <aside className="flex min-h-0 flex-col gap-2 overflow-y-auto lg:col-span-3">
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <AccountSummary account={mockAccount} />
            </div>
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <BotAnalytics analytics={mockAnalytics} />
            </div>
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <SystemStatus status={mockSystemStatus} />
            </div>
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <StreakCard data={mockStreakGraph} />
            </div>
          </aside>

          {/* Right column: fixed-height charts, then Positions + Logs (Logs scrollable) */}
          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden lg:col-span-9">
            <div className="grid shrink-0 grid-cols-1 gap-2 sm:grid-cols-2">
              <div className="h-[350px] min-w-0">
                <PnlChart />
              </div>
              <div className="h-[350px] min-w-0">
                <EquityChart />
              </div>
            </div>
            <div className="grid min-h-0 flex-1 grid-cols-1 gap-2 sm:grid-cols-4">
              <div className="relative flex min-h-0 flex-col overflow-hidden rounded border border-border/60 bg-card shadow-sm sm:col-span-2">
                <CardCorners />
                <div className="min-h-0 flex-1 overflow-auto">
                  <ActivePositions trades={mockTrades} filter={defaultFilter} />
                </div>
              </div>
              <div className="relative flex min-h-0 flex-col overflow-hidden rounded border border-border/60 bg-card shadow-sm sm:col-span-2">
                <CardCorners />
                <LiveLogs logs={mockLogs} follow />
              </div>
            </div>
          </div>
        </div>
      </main>
      <Toast message={toastMessage} onDismiss={() => setToastMessage(null)} />
    </div>
  );
}
