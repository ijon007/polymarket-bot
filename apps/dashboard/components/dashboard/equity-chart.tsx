"use client";

import { useId, useMemo, useRef, useState, useCallback } from "react";
import { useQuery } from "convex/react";
import { api } from "@convex/_generated/api";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  type ChartConfig,
} from "@/components/ui/chart";
import { CardCorners } from "./card-corners";
import type { BalancePoint, ChartTimeRange } from "@/lib/mock/charts";
import { fmtTimeHHMM } from "@/lib/mock/charts";
import { cn } from "@/lib/utils";

function fmtDateWithTime(d: Date) {
  return `${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}, ${fmtTimeHHMM(d)}`;
}

const INITIAL_BALANCE = 1000;

function addDays(d: Date, n: number) {
  const out = new Date(d);
  out.setDate(out.getDate() + n);
  return out;
}

function addHours(d: Date, n: number) {
  const out = new Date(d);
  out.setHours(out.getHours() + n);
  return out;
}

/** Convex stores settled_at in ms (bot sends ms). Normalize to seconds for comparison with Date.now()/1000. */
function toSec(ts: number): number {
  return ts >= 1e12 ? ts / 1000 : ts;
}

/** Build equity-over-time from settled trades and current equity, filtered by range. */
function buildEquitySeries(
  settled: { settled_at?: number; actual_profit?: number }[],
  currentEquity: number,
  timeRange: ChartTimeRange
): BalancePoint[] {
  const now = Date.now() / 1000;
  const nowDate = new Date();
  const is1D = timeRange === "1D";
  let rangeStartSec: number;
  if (is1D) {
    const rangeStartDate = addHours(nowDate, -24);
    rangeStartSec = rangeStartDate.getTime() / 1000;
  } else {
    const days = timeRange === "7D" || timeRange === "1M" ? (timeRange === "7D" ? 7 : 30) : timeRange === "30D" ? 30 : 90;
    const rangeStartDate = addDays(nowDate, -days);
    rangeStartSec = rangeStartDate.getTime() / 1000;
  }

  const sorted = [...settled].sort((a, b) => (a.settled_at ?? 0) - (b.settled_at ?? 0));
  const pnlBeforeRange = sorted
    .filter((t) => toSec(t.settled_at ?? 0) < rangeStartSec)
    .reduce((s, t) => s + (t.actual_profit ?? 0), 0);
  const startBalance = INITIAL_BALANCE + pnlBeforeRange;

  let cumulative = INITIAL_BALANCE;
  const points: { ts: number; balance: number }[] = [];
  for (const t of sorted) {
    const st = toSec(t.settled_at ?? 0);
    cumulative += t.actual_profit ?? 0;
    if (st >= rangeStartSec && st <= now) points.push({ ts: st, balance: cumulative });
  }

  const formatLabel = (tsSec: number) => {
    const d = new Date(tsSec * 1000);
    return is1D ? fmtTimeHHMM(d) : fmtDateWithTime(d);
  };

  type Point = BalancePoint & { timestamp: number };
  const result: Point[] = [
    { date: formatLabel(rangeStartSec), balance: startBalance, timestamp: rangeStartSec },
  ];
  for (const p of points) result.push({ date: formatLabel(p.ts), balance: p.balance, timestamp: p.ts });
  result.push({ date: formatLabel(now), balance: currentEquity, timestamp: now });
  return result;
}

const chartConfig = {
  balance: { label: "Equity", color: "var(--color-positive)" },
} satisfies ChartConfig;

function interpolate(
  data: { date: string; balance: number }[],
  xRatio: number
): { date: string; balance: number } {
  if (!data.length) return { date: "", balance: 0 };
  if (data.length === 1) return { date: data[0].date, balance: data[0].balance };
  const index = Math.max(0, Math.min(xRatio * (data.length - 1), data.length - 1));
  const i = Math.floor(index);
  const j = Math.min(i + 1, data.length - 1);
  const t = index - i;
  const balance = data[i].balance + t * (data[j].balance - data[i].balance);
  const date = t < 0.5 ? data[i].date : data[j].date;
  return { date, balance };
}

export function EquityChart() {
  const [timeRange, setTimeRange] = useState<ChartTimeRange>("30D");
  const [hover, setHover] = useState<{ x: number; value: number; date: string } | null>(null);
  const chartWrapRef = useRef<HTMLDivElement>(null);
  const gradientId = useId().replace(/:/g, "");

  const settled = useQuery(api.trades.listSettled, {});
  const analytics = useQuery(api.trades.dashboardAnalytics, {});
  const currentEquity = INITIAL_BALANCE + (analytics?.totalPnl ?? 0);

  const balanceData = useMemo(() => {
    if (settled === undefined) {
      const now = new Date();
      const start = timeRange === "1D" ? addHours(now, -24) : addDays(now, timeRange === "7D" || timeRange === "1M" ? (timeRange === "7D" ? -7 : -30) : timeRange === "30D" ? -30 : -90);
      const fmt = timeRange === "1D" ? fmtTimeHHMM : fmtDateWithTime;
      const startSec = start.getTime() / 1000;
      const nowSec = now.getTime() / 1000;
      return [
        { date: fmt(start), balance: currentEquity, timestamp: startSec },
        { date: fmt(now), balance: currentEquity, timestamp: nowSec },
      ];
    }
    return buildEquitySeries(settled, currentEquity, timeRange);
  }, [settled, currentEquity, timeRange]);
  const displayData = useMemo(() => {
    return balanceData.map((d) => {
      const pt = d as BalancePoint & { timestamp?: number };
      return {
        ...d,
        time: d.date,
        value: d.balance,
        timestamp: pt.timestamp ?? new Date(d.date).getTime() / 1000,
      };
    });
  }, [balanceData]);

  const xTicks = useMemo(() => {
    const n = displayData.length;
    if (n === 0) return undefined;
    const numTicks = timeRange === "1D" ? 12 : timeRange === "7D" || timeRange === "1M" ? 10 : 10;
    const indices = Array.from({ length: numTicks }, (_, i) =>
      i === numTicks - 1 ? n - 1 : Math.round((i / (numTicks - 1)) * (n - 1))
    );
    const timestamps = [...new Set(indices)]
      .map((i) => displayData[i]?.timestamp)
      .filter((v): v is number => typeof v === "number");
    return timestamps.sort((a, b) => a - b);
  }, [displayData, timeRange]);

  const yDomain = useMemo(() => {
    if (!displayData.length) return [0, 1000];
    const min = Math.min(...displayData.map((d) => d.value));
    const max = Math.max(...displayData.map((d) => d.value));
    const range = max - min || 1;
    const pad = Math.max(20, range * 0.08);
    return [min - pad, max + pad];
  }, [displayData]);

  const xDomain = useMemo(() => {
    if (!displayData.length) return [0, 1];
    const min = Math.min(...displayData.map((d) => d.timestamp).filter((v): v is number => typeof v === "number"));
    const max = Math.max(...displayData.map((d) => d.timestamp).filter((v): v is number => typeof v === "number"));
    const range = max - min || 1;
    const pad = range * 0.02;
    return [min - pad, max + pad];
  }, [displayData]);

  const formatTick = useCallback(
    (ts: number) => {
      const d = new Date(ts * 1000);
      return timeRange === "1D" ? fmtTimeHHMM(d) : fmtDateWithTime(d);
    },
    [timeRange]
  );

  const firstVal = displayData[0]?.value ?? 0;
  const lastVal = displayData[displayData.length - 1]?.value ?? 0;
  const change = lastVal - firstVal;
  const changePct = firstVal ? (change / firstVal) * 100 : 0;
  const isPositive = change >= 0;

  const onChartMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = chartWrapRef.current;
      if (!el || !displayData.length) return;
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const w = rect.width;
      if (x < 0 || x > w) {
        setHover(null);
        return;
      }
      const xRatio = x / w;
      const { date, balance } = interpolate(balanceData, xRatio);
      setHover({ x, value: balance, date });
    },
    [balanceData, displayData.length]
  );

  const onChartMouseLeave = useCallback(() => setHover(null), []);

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded border border-border/60 bg-card shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardCorners />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/40 px-4 py-3">
        <span className="text-sm font-medium text-foreground">Total account equity</span>
        <div className="flex rounded border border-border/60 bg-muted/30 p-0.5">
          {(["1D", "7D", "30D", "90D", "1M", "3M"] as const).map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setTimeRange(r)}
              className={cn(
                "rounded-md px-2 py-1 text-xs font-medium transition-colors duration-150",
                timeRange === r
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3 px-4 py-2">
        <span
          className={cn(
            "text-sm font-semibold tabular-nums transition-colors duration-150",
            isPositive ? "text-positive" : "text-destructive"
          )}
        >
          {isPositive ? "+" : ""}
          {changePct.toFixed(2)}% (${change.toFixed(2)})
        </span>
      </div>
      <div
        ref={chartWrapRef}
        className="relative h-full min-h-0 w-full cursor-crosshair px-2 pb-4"
        onMouseMove={onChartMouseMove}
        onMouseLeave={onChartMouseLeave}
      >
        {hover && (
          <>
            <div
              className="pointer-events-none absolute top-0 bottom-8 z-10 w-px border-l border-dashed border-foreground/50"
              style={{ left: hover.x }}
            />
            <div
              className="pointer-events-none absolute z-10 rounded border border-border/60 bg-card px-2 py-1.5 text-xs shadow-lg"
              style={{
                left: Math.min(hover.x + 10, (chartWrapRef.current?.offsetWidth ?? 400) - 90),
                top: 8,
              }}
            >
              <div className="text-muted-foreground">{hover.date}</div>
              <div className="font-semibold tabular-nums text-foreground">
                ${hover.value.toFixed(2)}
              </div>
            </div>
          </>
        )}
        <ChartContainer config={chartConfig} className="h-full min-h-[180px] w-full [&_.recharts-wrapper]:block!">
          <AreaChart data={displayData} margin={{ top: 12, right: 16, bottom: 28, left: 4 }}>
            <defs>
              <linearGradient id={`equityFill-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-positive)" stopOpacity={0.25} />
                <stop offset="100%" stopColor="var(--color-positive)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis
              dataKey="timestamp"
              type="number"
              domain={xDomain}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 10 }}
              ticks={xTicks}
              tickFormatter={formatTick}
              allowDataOverflow={false}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 10 }}
              width={48}
              tickFormatter={(v: number) =>
                `$${v >= 1000 ? (v / 1000).toFixed(1) + "k" : Math.round(v)}`
              }
              domain={yDomain}
              allowDataOverflow={false}
            />
            <Area
              dataKey="value"
              type="monotone"
              stroke="var(--color-positive)"
              strokeWidth={2}
              fill={`url(#equityFill-${gradientId})`}
              dot={false}
              isAnimationActive
              animationDuration={400}
            />
          </AreaChart>
        </ChartContainer>
      </div>
    </div>
  );
}
