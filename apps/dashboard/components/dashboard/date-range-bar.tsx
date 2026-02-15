"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { CalendarBlankIcon, FunnelIcon, CheckIcon } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import type { ChartTimeRange } from "@/lib/mock/charts";

const PRESETS: ChartTimeRange[] = ["1H", "4H", "1D", "7D", "30D", "90D"];

export interface DashboardFilter {
  positionSide: "all" | "yes" | "no";
  status: "all" | "executed" | "pending" | "settled";
}

const defaultFilter: DashboardFilter = {
  positionSide: "all",
  status: "all",
};

interface DateRangeBarProps {
  start: Date;
  end: Date;
  preset?: ChartTimeRange;
  onPresetChange?: (preset: ChartTimeRange) => void;
  filter?: DashboardFilter;
  onFilterChange?: (filter: DashboardFilter) => void;
  onFilterClick?: () => void;
  className?: string;
}

function formatRange(start: Date, end: Date) {
  return `${start.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })} - ${end.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`;
}

export function DateRangeBar({
  start,
  end,
  preset = "30D",
  onPresetChange,
  filter = defaultFilter,
  onFilterChange,
  className,
}: DateRangeBarProps) {
  const hasActiveFilter =
    filter.positionSide !== "all" || filter.status !== "all";

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <Button
        variant="outline"
        size="sm"
        className="gap-2 rounded border-border/60 bg-card/50 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
        aria-label="Select date range"
      >
        <CalendarBlankIcon className="size-4" weight="duotone" />
        <span className="text-xs">{formatRange(start, end)}</span>
      </Button>
      <div className="flex rounded border border-border/60 bg-card/50 p-0.5">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPresetChange?.(p)}
            className={cn(
              "rounded-md px-2.5 py-1 text-xs font-medium transition-colors duration-150",
              preset === p
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
            )}
          >
            {p}
          </button>
        ))}
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="Open filters"
          className={cn(
            "inline-flex h-6 items-center gap-2 rounded border border-border/60 bg-card/50 px-2 text-muted-foreground outline-none transition-colors hover:bg-muted/50 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
            hasActiveFilter && "border-primary/50 text-foreground"
          )}
        >
          <FunnelIcon className="size-4" weight="duotone" />
          <span className="text-xs">Filter</span>
          {hasActiveFilter && (
            <span className="size-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
          )}
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[180px]">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Position side</DropdownMenuLabel>
            {(["all", "yes", "no"] as const).map((side) => (
              <DropdownMenuItem
                key={side}
                onClick={() =>
                  onFilterChange?.({ ...filter, positionSide: side })
                }
                className="flex items-center justify-between"
              >
                <span className="capitalize">{side}</span>
                {filter.positionSide === side && (
                  <CheckIcon className="size-3.5" />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
          <DropdownMenuGroup>
            <DropdownMenuLabel className="mt-1">Status</DropdownMenuLabel>
            {(["all", "executed", "pending", "settled"] as const).map((s) => (
              <DropdownMenuItem
                key={s}
                onClick={() => onFilterChange?.({ ...filter, status: s })}
                className="flex items-center justify-between capitalize"
              >
                {s}
                {filter.status === s && <CheckIcon className="size-3.5" />}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
