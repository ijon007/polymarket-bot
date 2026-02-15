"use client";

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { PortfolioDataPoint } from "@/types/dashboard";

interface PortfolioChartProps {
  data: PortfolioDataPoint[];
}

const chartConfig = {
  value: {
    label: "Portfolio",
    color: "var(--color-primary)",
  },
} satisfies ChartConfig;

export function PortfolioChart({ data }: PortfolioChartProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Portfolio Performance
        </span>
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          24H
        </span>
      </div>
      <div className="flex-1 px-2 pb-2">
        <ChartContainer config={chartConfig} className="aspect-auto h-full w-full">
          <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="portfolioFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.15} />
                <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
              </linearGradient>
            </defs>
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
              width={48}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(1)}k`}
              domain={["dataMin - 10", "dataMax + 10"]}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  formatter={(value) => [`$${Number(value).toFixed(2)}`, "Portfolio"]}
                />
              }
            />
            <Area
              dataKey="value"
              type="monotone"
              stroke="var(--color-primary)"
              strokeWidth={1.5}
              fill="url(#portfolioFill)"
              dot={false}
            />
          </AreaChart>
        </ChartContainer>
      </div>
    </div>
  );
}
