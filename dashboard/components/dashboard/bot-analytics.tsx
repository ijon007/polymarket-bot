import { cn } from "@/lib/utils";
import type { BotAnalytics as BotAnalyticsType } from "@/types/dashboard";

interface BotAnalyticsProps {
  analytics: BotAnalyticsType;
}

function fmtUsd(v: number) {
  return `${v >= 0 ? "+" : ""}$${Math.abs(v).toFixed(2)}`;
}

export function BotAnalytics({ analytics }: BotAnalyticsProps) {
  const rows: { label: string; value: string; color?: string }[] = [
    { label: "Total Trades", value: String(analytics.totalTrades) },
    { label: "Settled", value: String(analytics.settled) },
    { label: "Pending", value: String(analytics.pending) },
    {
      label: "Total P&L",
      value: fmtUsd(analytics.totalPnl),
      color: analytics.totalPnl >= 0 ? "text-positive" : "text-destructive",
    },
    { label: "Best Trade", value: fmtUsd(analytics.bestTrade), color: "text-positive" },
    { label: "Worst Trade", value: fmtUsd(analytics.worstTrade), color: "text-destructive" },
  ];

  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        Bot Analytics
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
