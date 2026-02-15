"use client";

import { Line, LineChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { PositionPerformancePoint } from "@/types/dashboard";

interface PositionChartProps {
  data: PositionPerformancePoint[];
  symbols: readonly string[];
}

const COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
];

export function PositionChart({ data, symbols }: PositionChartProps) {
  const chartConfig = Object.fromEntries(
    symbols.map((sym, i) => [
      sym,
      { label: sym, color: COLORS[i % COLORS.length] },
    ])
  ) satisfies ChartConfig;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Position Performance
        </span>
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          % Change
        </span>
      </div>
      <div className="flex-1 px-2 pb-2">
        <ChartContainer config={chartConfig} className="aspect-auto h-full w-full">
          <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid
              vertical={false}
              strokeDasharray="3 3"
              stroke="var(--color-border)"
            />
            <XAxis
              dataKey="time"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
              interval="preserveStartEnd"
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 10, fontFamily: "var(--font-mono)" }}
              width={32}
              tickFormatter={(v: number) => `${v}%`}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  formatter={(value, name) => [`${Number(value).toFixed(1)}%`, name]}
                />
              }
            />
            <ChartLegend content={<ChartLegendContent />} />
            {symbols.map((sym, i) => (
              <Line
                key={sym}
                dataKey={sym}
                type="monotone"
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={1.5}
                dot={false}
              />
            ))}
          </LineChart>
        </ChartContainer>
      </div>
    </div>
  );
}
