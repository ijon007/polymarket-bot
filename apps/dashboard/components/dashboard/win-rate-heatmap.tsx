"use client";

import { useMemo, useState } from "react";
import { useQuery } from "convex/react";
import { api } from "@convex/_generated/api";
import {
  getWinRateHeatmap,
  type WinRateHeatmapData,
  type HeatmapCell,
} from "@/lib/mock/charts";
import { CardCorners } from "./card-corners";
import { cn } from "@/lib/utils";

/** Convex stores executed_at/settled_at in milliseconds (bot sends ms). Normalize to ms for Date. */
function toMs(ts: number): number {
  return ts >= 1e12 ? ts : ts * 1000;
}

/** Format Unix timestamp (sec or ms) as "YYYY-MM-DD HH:mm" in local time for correct day/hour bucketing. */
function formatExecutedAtLocal(ts: number): string {
  const d = new Date(toMs(ts));
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const min = String(d.getMinutes()).padStart(2, "0");
  return `${y}-${mo}-${day} ${h}:${min}`;
}

function getCell(
  data: WinRateHeatmapData,
  dayOfWeek: number,
  hourBucket: number
): HeatmapCell | undefined {
  return data.cells.find(
    (c) => c.dayOfWeek === dayOfWeek && c.hourBucket === hourBucket
  );
}

/** Win rate 0–1 → red (0) → neutral (0.5) → green (1). Softer, clearer midpoint. */
function winRateBg(winRate: number): string {
  const t = Math.max(0, Math.min(1, winRate));
  if (t <= 0.5) {
    const s = t * 2;
    return `oklch(0.58 ${0.12 + s * 0.04} 27 / ${0.35 + s * 0.35})`;
  }
  const s = (t - 0.5) * 2;
  return `oklch(0.55 ${0.1 + s * 0.1} 145 / ${0.35 + s * 0.4})`;
}

/** PnL symmetric: red (neg) → neutral → green (pos). */
function pnlBg(pnl: number, min: number, max: number): string {
  const range = Math.max(max - min, 1);
  const t = (pnl - min) / range;
  if (t <= 0.5) {
    const s = t * 2;
    return `oklch(0.55 0.14 27 / ${0.3 + s * 0.35})`;
  }
  const s = (t - 0.5) * 2;
  return `oklch(0.55 0.14 145 / ${0.3 + s * 0.4})`;
}

type Metric = "winRate" | "pnl";

const TOOLTIP_OFFSET = 12;

export function WinRateHeatmap() {
  const settled = useQuery(api.trades.listSettled, {});
  const trades = useMemo(() => {
    if (settled === undefined) return [];
    return settled.map((t) => ({
      executedAt: formatExecutedAtLocal(t.executed_at),
      pnl: t.actual_profit ?? 0,
      status: t.status,
    }));
  }, [settled]);
  const [metric, setMetric] = useState<Metric>("winRate");
  const [hover, setHover] = useState<{
    dayOfWeek: number;
    hourBucket: number;
  } | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);

  const data = useMemo(() => getWinRateHeatmap(trades), [trades]);

  const pnlRange = useMemo(() => {
    let min = 0;
    let max = 0;
    for (const c of data.cells) {
      if (c.pnl < min) min = c.pnl;
      if (c.pnl > max) max = c.pnl;
    }
    const abs = Math.max(Math.abs(min), Math.abs(max), 1);
    return { min: -abs, max: abs };
  }, [data.cells]);

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded border border-border/60 bg-card shadow-sm">
      <CardCorners />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/40 px-4 py-3">
        <span className="text-sm font-medium text-foreground">
          Trades Heatmap
        </span>
      </div>

      {/* Best / Worst callout */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-border/40 px-4 py-2.5 text-xs">
        {data.best ? (
          <>
            <span className="text-muted-foreground">
              <span className="font-semibold text-positive">Best:</span>{" "}
              {data.best.dayLabel} {data.best.timeLabel}{" "}
              <span className="tabular-nums">
                ({data.best.winRatePct.toFixed(0)}%, {data.best.trades} trades)
              </span>
            </span>
            {data.worst && (
              <span className="text-muted-foreground">
                <span className="font-semibold text-destructive">Worst:</span>{" "}
                {data.worst.dayLabel} {data.worst.timeLabel}{" "}
                <span className="tabular-nums">
                  ({data.worst.winRatePct.toFixed(0)}%, {data.worst.trades} trades)
                </span>
              </span>
            )}
          </>
        ) : (
          <span className="text-muted-foreground">
            Need at least 2 settled trades in a time slot to show best & worst.
          </span>
        )}
      </div>

      {/* Single grid: col 0 = day labels, cols 1–12 = heatmap, row 8 = hour labels */}
      <div
        className="min-h-0 flex-1 overflow-auto px-4 py-3 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
        onMouseMove={(e) => {
          if (hover !== null) setTooltipPos({ x: e.clientX, y: e.clientY });
        }}
        onMouseLeave={() => {
          setHover(null);
          setTooltipPos(null);
        }}
      >
        <div
          className="grid w-full min-w-max gap-px"
          style={{
            gridTemplateColumns: "auto repeat(12, minmax(44px, 1fr))",
            gridTemplateRows: "repeat(7, 24px) 20px",
          }}
        >
          {/* Day labels: column 1, rows 1–7 */}
          {data.dayLabels.map((label, i) => (
            <div
              key={label}
              className="flex items-center justify-end pr-2 text-[11px] text-muted-foreground"
              style={{ gridColumn: 1, gridRow: i + 1 }}
            >
              {label}
            </div>
          ))}
          {/* Heatmap cells: columns 2–13, rows 1–7 */}
          {data.cells.map((cell) => {
            const hasData = cell.total > 0;
            const winRate = hasData ? cell.wins / cell.total : 0;
            const isHover =
              hover?.dayOfWeek === cell.dayOfWeek &&
              hover?.hourBucket === cell.hourBucket;
            const bg = hasData
              ? metric === "winRate"
                ? winRateBg(winRate)
                : pnlBg(cell.pnl, pnlRange.min, pnlRange.max)
              : undefined;
            return (
              <div
                key={`${cell.dayOfWeek}-${cell.hourBucket}`}
                className={cn(
                  "transition-all duration-150",
                  !hasData && "bg-muted/30",
                  hasData && "rounded-[2px]",
                  isHover && "ring-2 ring-foreground/50 ring-offset-1 ring-offset-card z-10"
                )}
                style={{
                  gridColumn: cell.hourBucket + 2,
                  gridRow: cell.dayOfWeek + 1,
                  ...(bg ? { backgroundColor: bg } : {}),
                }}
                onMouseEnter={(e) => {
                  setHover({
                    dayOfWeek: cell.dayOfWeek,
                    hourBucket: cell.hourBucket,
                  });
                  setTooltipPos({ x: e.clientX, y: e.clientY });
                }}
                role="gridcell"
                aria-label={
                  hasData
                    ? `${data.dayLabels[cell.dayOfWeek]} ${data.hourLabels[cell.hourBucket]}: ${(winRate * 100).toFixed(0)}% win, ${cell.total} trades`
                    : "No trades"
                }
              />
            );
          })}
          {/* Hour labels: row 8, columns 2–13 */}
          {data.hourLabels.map((h, i) => (
            <div
              key={h}
              className="flex items-center justify-center pt-1 text-[10px] text-muted-foreground"
              style={{ gridColumn: i + 2, gridRow: 8 }}
            >
              {h}
            </div>
          ))}
        </div>
      </div>

      {/* Legend only */}
      <div className="flex shrink-0 justify-end border-t border-border/40 px-4 py-2">
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span>Low</span>
          <div className="flex h-2 w-16 overflow-hidden rounded-full border border-border/50">
            <div
              className="h-full w-full"
              style={{
                background: "linear-gradient(to right, var(--destructive), var(--muted-foreground), var(--positive))",
              }}
            />
          </div>
          <span>High</span>
        </div>
      </div>

      {hover !== null && tooltipPos && (() => {
        const cell = getCell(data, hover.dayOfWeek, hover.hourBucket);
        if (!cell) return null;
        const winRatePct =
          cell.total > 0 ? (cell.wins / cell.total) * 100 : 0;
        return (
          <div
            className="pointer-events-none fixed z-20 rounded border border-border bg-card px-2 py-1.5 text-xs shadow-lg"
            style={{
              left: tooltipPos.x + TOOLTIP_OFFSET,
              top: tooltipPos.y + TOOLTIP_OFFSET,
            }}
          >
            <div className="font-medium text-foreground">
              {data.dayLabels[hover.dayOfWeek]}, {data.hourLabels[hover.hourBucket]}
            </div>
            <div className={cn("tabular-nums", cell.pnl >= 0 ? "text-positive" : "text-destructive")}>
              {cell.total > 0 ? (
                <>
                  {winRatePct.toFixed(0)}% win · {cell.total} trades · P&L{" "}
                  {cell.pnl >= 0 ? "+" : ""}${cell.pnl.toFixed(2)}
                </>
              ) : (
                "No trades"
              )}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
