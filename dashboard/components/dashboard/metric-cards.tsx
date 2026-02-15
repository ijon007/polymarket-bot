"use client";

import { Bar, BarChart } from "recharts";
import { cn } from "@/lib/utils";
import {
  ChartContainer,
  type ChartConfig,
} from "@/components/ui/chart";
import { CardCorners } from "./card-corners";

const miniChartConfig = {
  v: { label: "Value", color: "var(--color-chart-1)" },
} satisfies ChartConfig;

interface MetricCardProps {
  title: string;
  value: string;
  changePct: number;
  changeLabel?: string;
  miniValues: number[];
  icon?: React.ReactNode;
  delay?: number;
}

export function MetricCard({
  title,
  value,
  changePct,
  changeLabel = "vs Last month",
  miniValues,
  icon,
  delay = 0,
}: MetricCardProps) {
  const data = miniValues.map((v, i) => ({ name: `${i}`, v }));
  const isPositive = changePct >= 0;

  return (
    <div
      style={{ animationDelay: `${delay}s` }}
      className={cn(
        "animate-in fade-in slide-in-from-bottom-2 duration-200 fill-mode-both",
        "relative overflow-hidden rounded border border-border/60 bg-card p-4 shadow-sm",
        "transition-shadow duration-200 ease-out hover:shadow-md"
      )}
    >
      <CardCorners />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            {icon}
            <span className="text-xs font-medium uppercase tracking-wide">
              {title}
            </span>
          </div>
          <p className="mt-1 text-2xl font-semibold tabular-nums tracking-tight text-foreground">
            {value}
          </p>
          <p
            className={cn(
              "mt-0.5 text-xs font-medium tabular-nums",
              isPositive ? "text-positive" : "text-destructive"
            )}
          >
            {isPositive ? "↑" : "↓"} {Math.abs(changePct)}% {changeLabel}
          </p>
        </div>
        <div className="h-10 w-20 shrink-0">
          <ChartContainer config={miniChartConfig} className="h-full w-full">
            <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <Bar
                dataKey="v"
                radius={[2, 2, 0, 0]}
                isAnimationActive
                animationDuration={400}
                animationBegin={delay * 1000}
                fill="var(--color-chart-1)"
              />
            </BarChart>
          </ChartContainer>
        </div>
      </div>
    </div>
  );
}
