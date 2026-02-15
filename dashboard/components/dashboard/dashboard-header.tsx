"use client";

import { cn } from "@/lib/utils";
import type { SystemStatus } from "@/types/dashboard";
import { StatusBar } from "./status-bar";

interface DashboardHeaderProps {
  status: SystemStatus;
  lastUpdated: number;
  onRefresh: () => void;
  isRefreshing?: boolean;
  openPositions?: number;
}

export function DashboardHeader({
  status,
  lastUpdated,
  onRefresh,
  isRefreshing = false,
  openPositions,
}: DashboardHeaderProps) {
  return (
    <header
      className="flex items-center justify-between border-b border-border/60 bg-card/80 px-4 py-2 backdrop-blur-sm animate-in fade-in slide-in-from-top-1 duration-200"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Polymarket Alpha Scanner
        </span>
        <div className="hidden items-center gap-3 sm:flex">
          {status.connections.map((conn) => (
            <div key={conn.label} className="flex items-center gap-1.5">
              <span
                className={cn(
                  "size-1.5 rounded-full",
                  conn.connected ? "bg-positive" : "bg-destructive"
                )}
              />
              <span className="text-[0.65rem] text-muted-foreground">
                {conn.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <StatusBar
        lastUpdated={lastUpdated}
        onRefresh={onRefresh}
        isRefreshing={isRefreshing}
        openPositions={openPositions}
      />
    </header>
  );
}
