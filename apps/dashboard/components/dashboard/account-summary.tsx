import { cn } from "@/lib/utils";
import type { AccountSummary as AccountSummaryType } from "@/types/dashboard";

interface AccountSummaryProps {
  account: AccountSummaryType;
}

function fmt(v: number) {
  return v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

export function AccountSummary({ account }: AccountSummaryProps) {
  const pnlColor = account.totalPnl >= 0 ? "text-positive" : "text-destructive";

  return (
    <div className="flex h-full flex-col justify-between p-4">
      <div>
        <p className="text-[0.6rem] uppercase text-muted-foreground">Equity</p>
        <p className="text-3xl font-semibold tabular-nums leading-tight">
          {fmt(account.equity)}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2">
        <div>
          <p className="text-[0.6rem] uppercase text-muted-foreground">Win rate</p>
          <p className={cn("text-xs tabular-nums", account.realizedPnl >= 0 ? "text-positive" : "text-destructive")}>{account.winRate.toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-[0.6rem] uppercase text-muted-foreground">Total P&L</p>
          <p className={cn("text-xs tabular-nums", pnlColor)}>
            {fmt(account.totalPnl)}{" "}
            <span className="text-[0.65rem]">
              ({account.totalPnlPct > 0 ? "+" : ""}{account.totalPnlPct.toFixed(1)}%)
            </span>
          </p>
        </div>
        <div>
          <p className="text-[0.6rem] uppercase text-muted-foreground">Realized</p>
          <p className={cn("text-xs tabular-nums", account.realizedPnl >= 0 ? "text-positive" : "text-destructive")}>
            {fmt(account.realizedPnl)}
          </p>
        </div>
        <div>
          <p className="text-[0.6rem] uppercase text-muted-foreground">Today P&L (24h)</p>
          <p className={cn("text-xs tabular-nums", account.todayPnl >= 0 ? "text-positive" : "text-destructive")}>
            {fmt(account.todayPnl)}
          </p>
        </div>
      </div>
    </div>
  );
}
