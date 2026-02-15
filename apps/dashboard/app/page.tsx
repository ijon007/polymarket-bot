"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import {
  DashboardHeader,
  AccountSummary,
  ActivePositions,
  SystemStatus,
  LiveLogs,
  BotAnalytics,
  EquityChart,
  WinRateHeatmap,
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
    <div className="flex h-dvh flex-col overflow-y-auto overflow-x-hidden bg-background font-mono transition-colors duration-200 lg:overflow-hidden">
      <DashboardHeader
        lastUpdated={lastUpdated}
        onRefresh={refreshData}
        isRefreshing={isRefreshing}
        openPositions={openPositions}
      />

      <main className="flex min-h-0 flex-1 flex-col overflow-y-auto p-2 lg:overflow-hidden">
        {/* Layout: left sidebar | right (Charts, Positions, Logs) — scroll on mobile */}
        <div className="grid grid-cols-1 gap-2 lg:min-h-0 lg:flex-1 lg:overflow-hidden lg:grid-cols-12">
          {/* Left column: Account card, Bot Analytics, System Status */}
          <aside className="flex flex-col gap-2 lg:col-span-3 lg:min-h-0 lg:overflow-y-auto">
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <AccountSummary account={mockAccount} />
            </div>
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <StreakCard data={mockStreakGraph} />
            </div>
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <BotAnalytics analytics={mockAnalytics} />
            </div>
            <div className="relative shrink-0 overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm">
              <CardCorners />
              <SystemStatus status={mockSystemStatus} />
            </div>
          </aside>

          {/* Right column: fixed-height charts, then Positions + Logs (Logs scrollable) */}
          <div className="flex flex-1 flex-col gap-2 lg:min-h-0 lg:overflow-hidden lg:col-span-9">
            <div className="grid shrink-0 grid-cols-1 gap-2 sm:grid-cols-2">
              <div className="h-[280px] min-w-0 sm:h-[350px]">
                <EquityChart />
              </div>
              <div className="h-[380px] min-w-0 sm:h-[350px]">
                <WinRateHeatmap trades={mockTrades} />
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
