"use client";

import { Button } from "@/components/ui/button";
import { ArrowsClockwiseIcon } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";

function relativeTime(ms: number): string {
  const sec = Math.floor((Date.now() - ms) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

interface StatusBarProps {
  lastUpdated: number;
  onRefresh: () => void;
  isRefreshing?: boolean;
  openPositions?: number;
  className?: string;
}

export function StatusBar({
  lastUpdated,
  onRefresh,
  isRefreshing = false,
  openPositions,
  className,
}: StatusBarProps) {
  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-2 text-[0.65rem] text-muted-foreground",
        className
      )}
    >
      <span className="tabular-nums">Last updated {lastUpdated > 0 ? relativeTime(lastUpdated) : "—"}</span>
      {openPositions !== undefined && (
        <span>· Open positions: <span className="tabular-nums font-medium text-foreground">{openPositions}</span></span>
      )}
      <Button
        variant="ghost"
        size="sm"
        className="h-5 gap-1 px-1.5 text-muted-foreground hover:text-foreground"
        onClick={onRefresh}
        disabled={isRefreshing}
        aria-label="Refresh data"
      >
        <ArrowsClockwiseIcon
          className={cn("size-3", isRefreshing && "animate-spin")}
          weight="duotone"
        />
        Refresh
      </Button>
    </div>
  );
}
