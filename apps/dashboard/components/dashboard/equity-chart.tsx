"use client";

import { useId, useMemo, useState, useCallback } from "react";
import { useQuery } from "convex/react";
import { api } from "@convex/_generated/api";
import { Area, AreaChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
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

const INITIAL_BALANCE = 10;

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

/** Build equity-over-time from settled trades and current equity, filtered by range. Step shape: flat until each trade then step. */
function buildEquitySeries(
  settled: { settled_at?: number; actual_profit?: number }[],
  currentEquity: number,
  timeRange: ChartTimeRange
): (BalancePoint & { timestamp: number })[] {
  const now = Date.now() / 1000;
  const nowDate = new Date();
  const hourRanges = timeRange === "1H" || timeRange === "4H" || timeRange === "1D";
  let rangeStartSec: number;
  if (timeRange === "1H") {
    rangeStartSec = addHours(nowDate, -1).getTime() / 1000;
  } else if (timeRange === "4H") {
    rangeStartSec = addHours(nowDate, -4).getTime() / 1000;
  } else if (timeRange === "1D") {
    rangeStartSec = addHours(nowDate, -24).getTime() / 1000;
  } else {
    const days = timeRange === "7D" ? 7 : timeRange === "30D" ? 30 : 90;
    rangeStartSec = addDays(nowDate, -days).getTime() / 1000;
  }

  const sorted = [...settled].sort((a, b) => (a.settled_at ?? 0) - (b.settled_at ?? 0));
  const pnlBeforeRange = sorted
    .filter((t) => toSec(t.settled_at ?? 0) < rangeStartSec)
    .reduce((s, t) => s + (t.actual_profit ?? 0), 0);
  const startBalance = INITIAL_BALANCE + pnlBeforeRange;

  const formatLabel = (tsSec: number) => {
    const d = new Date(tsSec * 1000);
    return hourRanges ? fmtTimeHHMM(d) : fmtDateWithTime(d);
  };

  type Point = BalancePoint & { timestamp: number };
  const result: Point[] = [
    { date: formatLabel(rangeStartSec), balance: startBalance, timestamp: rangeStartSec },
  ];
  let cumulative = startBalance;
  for (const t of sorted) {
    const st = toSec(t.settled_at ?? 0);
    if (st < rangeStartSec || st > now) continue;
    result.push({ date: formatLabel(st), balance: cumulative, timestamp: st });
    cumulative += t.actual_profit ?? 0;
    result.push({ date: formatLabel(st), balance: cumulative, timestamp: st });
  }
  result.push({ date: formatLabel(now), balance: currentEquity, timestamp: now });
  return result;
}

const chartConfig = {
  balance: { label: "Equity", color: "var(--color-positive)" },
} satisfies ChartConfig;

/** Step lookup: balance at the latest point with timestamp <= ts. */
function stepAt(
  data: { date: string; balance: number; timestamp: number }[],
  ts: number
): { date: string; balance: number } | null {
  if (!data.length) return null;
  let i = data.length - 1;
  while (i >= 0 && data[i].timestamp > ts) i--;
  const p = data[Math.max(0, i)];
  return { date: p.date, balance: p.balance };
}

function EquityTooltipContent({
  active,
  payload,
  balanceData,
}: {
  active?: boolean;
  payload?: Array<{ payload?: { timestamp?: number } }>;
  balanceData: { date: string; balance: number; timestamp: number }[];
}) {
  if (!active || !payload?.length) return null;
  const first = payload[0];
  const ts =
    first && typeof first === "object" && "payload" in first && first.payload
      ? (first.payload as { timestamp?: number }).timestamp
      : undefined;
  if (ts == null) return null;
  const step = stepAt(balanceData, ts);
  if (!step) return null;
  return (
    <div className="rounded border border-border/60 bg-card px-2 py-1.5 text-xs shadow-lg">
      <div className="text-muted-foreground">{step.date}</div>
      <div className="font-semibold tabular-nums text-foreground">
        ${step.balance.toFixed(2)}
      </div>
    </div>
  );
}

export function EquityChart() {
  const [timeRange, setTimeRange] = useState<ChartTimeRange>("1H");
  const gradientId = useId().replace(/:/g, "");

  const settled = useQuery(api.trades.listSettled, {});
  const analytics = useQuery(api.trades.dashboardAnalytics, {});
  const currentEquity = INITIAL_BALANCE + (analytics?.totalPnl ?? 0);

  const balanceData = useMemo(() => {
    if (settled === undefined) {
      const now = new Date();
      const start =
        timeRange === "1H"
          ? addHours(now, -1)
          : timeRange === "4H"
            ? addHours(now, -4)
            : timeRange === "1D"
              ? addHours(now, -24)
              : addDays(now, timeRange === "7D" ? -7 : timeRange === "30D" ? -30 : -90);
      const fmt = timeRange === "1H" || timeRange === "4H" || timeRange === "1D" ? fmtTimeHHMM : fmtDateWithTime;
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
    if (!displayData.length) return undefined;
    const min = Math.min(...displayData.map((d) => d.timestamp).filter((v): v is number => typeof v === "number"));
    const max = Math.max(...displayData.map((d) => d.timestamp).filter((v): v is number => typeof v === "number"));
    const numTicks =
      timeRange === "1H" || timeRange === "4H" ? 6 : timeRange === "1D" ? 8 : timeRange === "7D" ? 7 : 6;
    return Array.from({ length: numTicks }, (_, i) =>
      min + (i / (numTicks - 1)) * (max - min)
    );
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
      return timeRange === "1H" || timeRange === "4H" || timeRange === "1D"
        ? fmtTimeHHMM(d)
        : fmtDateWithTime(d);
    },
    [timeRange]
  );

  const firstVal = displayData[0]?.value ?? 0;
  const lastVal = displayData[displayData.length - 1]?.value ?? 0;
  const change = lastVal - firstVal;
  const changePct = firstVal ? (change / firstVal) * 100 : 0;
  const isPositive = change >= 0;

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded border border-border/60 bg-card shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardCorners />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/40 px-4 py-3">
        <span className="text-sm font-medium text-foreground">Total account equity</span>
        <div className="flex rounded border border-border/60 bg-muted/30 p-0.5">
          {(["1H", "4H", "1D", "7D", "30D", "90D"] as const).map((r) => (
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
      <div className="relative h-full min-h-0 w-full px-2 pb-4">
        <ChartContainer config={chartConfig} className="h-full min-h-[180px] w-full [&_.recharts-wrapper]:block!">
          <AreaChart data={displayData} margin={{ top: 12, right: 16, bottom: 28, left: 4 }}>
            <defs>
              <linearGradient id={`equityFill-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-positive)" stopOpacity={0.25} />
                <stop offset="100%" stopColor="var(--color-positive)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--color-border)" />
            <Tooltip
              content={(props) => (
                <EquityTooltipContent {...props} balanceData={balanceData} />
              )}
              cursor={{ stroke: "var(--foreground)", strokeWidth: 1, strokeDasharray: "4 4" }}
              isAnimationActive={false}
            />
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
              type="stepAfter"
              stroke="var(--color-positive)"
              strokeWidth={2}
              fill={`url(#equityFill-${gradientId})`}
              dot={false}
              baseValue={displayData[0]?.value ?? INITIAL_BALANCE}
              isAnimationActive
              animationDuration={400}
            />
          </AreaChart>
        </ChartContainer>
      </div>
    </div>
  );
}
