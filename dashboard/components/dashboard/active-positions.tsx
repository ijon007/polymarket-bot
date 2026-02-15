import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { TradeRow } from "@/types/dashboard";

interface ActivePositionsProps {
  trades: TradeRow[];
}

export function ActivePositions({ trades }: ActivePositionsProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Positions
        </span>
        <span className="tabular-nums text-[0.65rem] text-muted-foreground">
          {trades.length}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left text-[0.6rem] uppercase text-muted-foreground">
              <th className="pb-2 pr-3 font-medium">Market</th>
              <th className="pb-2 pr-3 font-medium">Side</th>
              <th className="pb-2 pr-3 text-right font-medium">Price</th>
              <th className="pb-2 pr-3 text-right font-medium">Size</th>
              <th className="pb-2 pr-3 text-right font-medium">P&L</th>
              <th className="pb-2 text-right font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id} className="border-b border-border/40 last:border-0">
                <td className="max-w-[160px] truncate py-1.5 pr-3 tabular-nums" title={t.question}>
                  {t.market}
                </td>
                <td className="py-1.5 pr-3">
                  <Badge
                    variant={t.side === "YES" ? "default" : "secondary"}
                    className="text-[0.5rem]"
                  >
                    {t.side}
                  </Badge>
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums">
                  {t.price.toFixed(2)}
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums">
                  ${t.size.toFixed(2)}
                </td>
                <td
                  className={cn(
                    "py-1.5 pr-3 text-right tabular-nums",
                    t.pnl > 0 ? "text-positive" : t.pnl < 0 ? "text-destructive" : "text-muted-foreground"
                  )}
                >
                  {t.pnl >= 0 ? "+" : ""}${Math.abs(t.pnl).toFixed(2)}
                </td>
                <td className="py-1.5 text-right">
                  <Badge
                    variant={t.status === "settled" ? "outline" : t.status === "paper" ? "secondary" : "destructive"}
                    className="text-[0.5rem]"
                  >
                    {t.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
