"use client";

import { StatusBar } from "./status-bar";

interface DashboardHeaderProps {
  lastUpdated: number;
  onRefresh: () => void;
  isRefreshing?: boolean;
  openPositions?: number;
}

export function DashboardHeader({
  lastUpdated,
  onRefresh,
  isRefreshing = false,
  openPositions,
}: DashboardHeaderProps) {
  return (
    <header
      className="flex items-center justify-between border-b border-border/60 bg-card/80 px-4 py-2 backdrop-blur-sm animate-in fade-in slide-in-from-top-1 duration-200"
    >
      <span className="text-sm font-semibold tracking-tight text-foreground">
        Polymarket Alpha Scanner
      </span>

      <StatusBar
        lastUpdated={lastUpdated}
        onRefresh={onRefresh}
        isRefreshing={isRefreshing}
        openPositions={openPositions}
      />
    </header>
  );
}
