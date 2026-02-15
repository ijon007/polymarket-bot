import { cn } from "@/lib/utils";
import type { MarketRow } from "@/types/dashboard";

interface MarketDataProps {
  markets: MarketRow[];
}

function fmtTime(s: number) {
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

function fmtVol(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

export function MarketData({ markets }: MarketDataProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Market Scanner
        </span>
        <span className="tabular-nums text-[0.65rem] text-muted-foreground">
          {markets.length} markets
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left text-[0.6rem] uppercase text-muted-foreground">
              <th className="pb-2 pr-2 font-medium">Market</th>
              <th className="pb-2 pr-2 text-right font-medium">Vol</th>
              <th className="pb-2 pr-2 text-right font-medium">Yes</th>
              <th className="pb-2 pr-2 text-right font-medium">No</th>
              <th className="pb-2 pr-2 text-right font-medium">Edge</th>
              <th className="pb-2 text-right font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((m) => (
              <tr key={m.id} className="border-b border-border/40 last:border-0">
                <td className="max-w-[150px] truncate py-1.5 pr-2" title={m.question}>
                  {m.question}
                </td>
                <td className="py-1.5 pr-2 text-right tabular-nums">{fmtVol(m.volume)}</td>
                <td className="py-1.5 pr-2 text-right tabular-nums">{m.yesPrice.toFixed(2)}</td>
                <td className="py-1.5 pr-2 text-right tabular-nums">{m.noPrice.toFixed(2)}</td>
                <td
                  className={cn(
                    "py-1.5 pr-2 text-right tabular-nums",
                    m.edge >= 15 ? "text-positive font-semibold" : m.edge >= 10 ? "text-primary" : "text-muted-foreground"
                  )}
                >
                  {m.edge.toFixed(1)}%
                </td>
                <td
                  className={cn(
                    "py-1.5 text-right tabular-nums",
                    m.secondsLeft <= 60 ? "text-destructive" : "text-muted-foreground"
                  )}
                >
                  {fmtTime(m.secondsLeft)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
