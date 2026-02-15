"use client";

import { useId, useMemo, useRef, useState, useCallback } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { CardCorners } from "./card-corners";
import type { ChartTimeRange } from "@/lib/mock/charts";
import { getPnlOverTime } from "@/lib/mock/charts";
import { cn } from "@/lib/utils";

const chartConfig = {
  pnl: { label: "P&L", color: "var(--color-primary)" },
} satisfies ChartConfig;

function interpolate(
  data: { date: string; pnl: number }[],
  xRatio: number
): { date: string; pnl: number } {
  if (!data.length) return { date: "", pnl: 0 };
  if (data.length === 1) return { date: data[0].date, pnl: data[0].pnl };
  const index = Math.max(0, Math.min(xRatio * (data.length - 1), data.length - 1));
  const i = Math.floor(index);
  const j = Math.min(i + 1, data.length - 1);
  const t = index - i;
  const pnl = data[i].pnl + t * (data[j].pnl - data[i].pnl);
  const date = t < 0.5 ? data[i].date : data[j].date;
  return { date, pnl };
}

export function PnlChart() {
  const [timeRange, setTimeRange] = useState<ChartTimeRange>("30D");
  const [hover, setHover] = useState<{ x: number; pnl: number; date: string } | null>(null);
  const chartWrapRef = useRef<HTMLDivElement>(null);
  const gradientId = useId().replace(/:/g, "");

  const data = useMemo(() => getPnlOverTime(timeRange), [timeRange]);
  const displayData = useMemo(
    () => data.map((d) => ({ ...d, time: d.date, value: d.pnl })),
    [data]
  );

  const firstVal = displayData[0]?.value ?? 0;
  const lastVal = displayData[displayData.length - 1]?.value ?? 0;
  const change = lastVal - firstVal;
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
      const { date, pnl } = interpolate(data, xRatio);
      setHover({ x, pnl, date });
    },
    [data, displayData.length]
  );

  const onChartMouseLeave = useCallback(() => setHover(null), []);

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded border border-border/60 bg-card shadow-sm transition-shadow duration-200 hover:shadow-md">
      <CardCorners />
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/40 px-4 py-3">
        <span className="text-sm font-medium text-foreground">P&L</span>
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
          {isPositive ? "+" : ""}${change.toFixed(2)}
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
              <div className={cn("font-semibold tabular-nums", hover.pnl >= 0 ? "text-positive" : "text-destructive")}>
                {hover.pnl >= 0 ? "+" : ""}${hover.pnl.toFixed(2)}
              </div>
            </div>
          </>
        )}
        <ChartContainer config={chartConfig} className="h-full min-h-[180px] w-full [&_.recharts-wrapper]:block!">
          <AreaChart data={displayData} margin={{ top: 8, right: 8, bottom: 24, left: 0 }}>
            <defs>
              <linearGradient id={`pnlFill-${gradientId}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.25} />
                <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis dataKey="time" tickLine={false} axisLine={false} tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 10 }}
              width={48}
              tickFormatter={(v: number) => `$${v >= 1000 ? (v / 1000).toFixed(1) + "k" : v}`}
              domain={["dataMin - 20", "dataMax + 20"]}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  labelFormatter={(label) => label}
                  formatter={(value) => [`$${Number(value).toFixed(2)}`, "P&L"]}
                />
              }
            />
            <Area
              dataKey="value"
              type="monotone"
              stroke="var(--color-primary)"
              strokeWidth={2}
              fill={`url(#pnlFill-${gradientId})`}
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
