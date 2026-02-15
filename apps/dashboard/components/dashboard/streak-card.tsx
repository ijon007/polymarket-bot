"use client";

import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type {
  StreakGraph as StreakGraphType,
  StreakTradeEntry,
  TradeOutcome,
} from "@/types/dashboard";

const COLS = 25;
const ROWS = 4;
const TOTAL = COLS * ROWS; // 40
const GAP_PX = 2;
const MAX_CELL_PX = 15;
const MAX_GRID_WIDTH = COLS * MAX_CELL_PX + (COLS - 1) * GAP_PX;
const MAX_GRID_HEIGHT = ROWS * MAX_CELL_PX + (ROWS - 1) * GAP_PX;

interface StreakCardProps {
  data: StreakGraphType;
}

function getCellBg(outcome: TradeOutcome | null): string {
  if (outcome === null) return "bg-muted/40";
  return outcome === "won" ? "bg-positive" : "bg-destructive";
}

function formatPnl(pnl: number): string {
  const sign = pnl >= 0 ? "+" : "";
  return `${sign}$${pnl.toFixed(2)}`;
}

function TradeTooltip({ entry }: { entry: StreakTradeEntry | null }) {
  if (!entry) {
    return (
      <Tooltip>
        <TooltipTrigger className="block h-full w-full">
          <div
            className={cn("h-full w-full rounded-[2px]", getCellBg(null))}
          />
        </TooltipTrigger>
        <TooltipContent side="top" className="font-mono text-xs">No trade</TooltipContent>
      </Tooltip>
    );
  }
  const pnlClass = entry.pnl >= 0 ? "text-positive" : "text-destructive";
  return (
    <Tooltip>
      <TooltipTrigger className="block h-full w-full cursor-default">
        <div
          className={cn(
            "h-full w-full rounded-[2px]",
            getCellBg(entry.outcome)
          )}
        />
      </TooltipTrigger>
      <TooltipContent side="top" className="font-mono text-xs">
        <div className="flex flex-col gap-0.5">
          <span className="font-medium capitalize">{entry.outcome}</span>
          <span className={cn("tabular-nums", pnlClass)}>
            P&L {formatPnl(entry.pnl)}
          </span>
          <span className="text-muted-foreground">
            <span className={entry.side === "UP" ? "text-positive" : "text-destructive"}>
              {entry.side}
            </span>{" "}
            · {entry.executedAt}
          </span>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export function StreakCard({ data }: StreakCardProps) {
  const { history, currentStreak, streakType } = data;
  const slice = history.slice(-TOTAL);
  const padded: (StreakTradeEntry | null)[] = [
    ...Array(TOTAL - slice.length).fill(null),
    ...slice,
  ];

  return (
    <TooltipProvider delay={0}>
      <div className="flex h-full min-w-0 flex-col p-3 sm:p-4">
        <div className="flex items-center justify-between">
          <span className="text-[0.6rem] font-medium uppercase text-muted-foreground sm:text-[0.65rem]">
            Streak
          </span>
          {currentStreak > 0 && (
            <span className="text-[0.6rem] tabular-nums text-muted-foreground sm:text-[0.65rem]">
              {currentStreak}
              {streakType}
            </span>
          )}
        </div>
        <div className="mt-2 flex min-w-0 w-full justify-end">
          <div
            className="grid w-full max-w-full shrink-0"
            style={{
              maxWidth: MAX_GRID_WIDTH,
              maxHeight: MAX_GRID_HEIGHT,
              aspectRatio: MAX_GRID_WIDTH / MAX_GRID_HEIGHT,
              gridTemplateColumns: `repeat(${COLS}, minmax(0, 1fr))`,
              gridTemplateRows: `repeat(${ROWS}, minmax(0, 1fr))`,
              gap: GAP_PX,
            }}
          >
            {padded.map((entry, i) => (
              <TradeTooltip key={i} entry={entry} />
            ))}
          </div>
        </div>
        <p className="mt-1.5 text-right text-[0.5rem] text-muted-foreground sm:text-[0.55rem]">
          1 square = 1 trade · older → newer
        </p>
      </div>
    </TooltipProvider>
  );
}
