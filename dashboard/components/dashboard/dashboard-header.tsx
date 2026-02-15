import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SystemStatus } from "@/types/dashboard";

interface DashboardHeaderProps {
  status: SystemStatus;
}

export function DashboardHeader({ status }: DashboardHeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card px-4 py-2">
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold uppercase tracking-tight">
          Polymarket Alpha Scanner
        </span>
        <Badge variant="outline" className="text-[0.6rem] tabular-nums">
          v2.1.0
        </Badge>
      </div>

      <div className="flex items-center gap-4">
        {status.connections.map((conn) => (
          <div key={conn.label} className="flex items-center gap-1.5">
            <span
              className={cn(
                "size-1.5 rounded-full",
                conn.connected ? "bg-positive" : "bg-destructive"
              )}
            />
            <span className="text-[0.65rem] text-muted-foreground">
              {conn.label}
            </span>
          </div>
        ))}
        <span className="tabular-nums text-[0.65rem] text-muted-foreground">
          {new Date().toLocaleTimeString("en-US", { hour12: false })}
        </span>
      </div>
    </header>
  );
}
