"use client";

import { useDataMode } from "@/lib/data-mode-context";
import { cn } from "@/lib/utils";
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
  const { dataMode, setDataMode } = useDataMode();
  return (
    <header
      className="flex items-center justify-between border-b border-border/60 bg-card/80 px-4 py-2 backdrop-blur-sm animate-in fade-in slide-in-from-top-1 duration-200"
    >
      <span className="text-sm font-semibold tracking-tight text-foreground">
        Polymarket Bot
      </span>

      <div className="flex items-center gap-3">
        <div
          className="flex rounded border border-border/60 bg-muted/30 p-0.5"
          role="group"
          aria-label="Data mode"
        >
          <button
            type="button"
            onClick={() => setDataMode("paper")}
            className={cn(
              "rounded px-2 py-1 text-xs font-medium transition-colors",
              dataMode === "paper"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            Paper
          </button>
          <button
            type="button"
            onClick={() => setDataMode("live")}
            className={cn(
              "rounded px-2 py-1 text-xs font-medium transition-colors",
              dataMode === "live"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            Live
          </button>
        </div>
        <StatusBar
          lastUpdated={lastUpdated}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          openPositions={openPositions}
        />
      </div>
    </header>
  );
}
