import { cn } from "@/lib/utils";
import type { PerformanceStats as PerformanceStatsType } from "@/types/dashboard";

interface PerformanceStatsProps {
  stats: PerformanceStatsType;
}

export function PerformanceStats({ stats }: PerformanceStatsProps) {
  const rows: { label: string; value: string; color?: string }[] = [
    {
      label: "Win Rate",
      value: `${stats.winRate.toFixed(1)}%`,
      color: stats.winRate >= 50 ? "text-positive" : "text-destructive",
    },
    {
      label: "Avg Edge",
      value: `+${stats.avgEdge.toFixed(1)}%`,
      color: "text-positive",
    },
    { label: "Total Scans", value: stats.totalScans.toLocaleString() },
    {
      label: "ROI (30d)",
      value: `${stats.roi30d >= 0 ? "+" : ""}${stats.roi30d.toFixed(1)}%`,
      color: stats.roi30d >= 0 ? "text-positive" : "text-destructive",
    },
    { label: "Won", value: String(stats.tradesWon), color: "text-positive" },
    { label: "Lost", value: String(stats.tradesLost), color: "text-destructive" },
  ];

  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        Performance
      </span>
      <div className="mt-3 flex flex-col gap-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{r.label}</span>
            <span className={cn("tabular-nums", r.color)}>{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
