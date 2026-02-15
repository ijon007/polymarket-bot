import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { SystemStatus as SystemStatusType } from "@/types/dashboard";

interface SystemStatusProps {
  status: SystemStatusType;
}

const statusVariant = (s: SystemStatusType["engineState"]) => {
  switch (s) {
    case "SCANNING": return "default" as const;
    case "IDLE": return "secondary" as const;
    default: return "destructive" as const;
  }
};

const statusLabel: Record<SystemStatusType["engineState"], string> = {
  SCANNING: "Scanning",
  IDLE: "Idle",
  ERROR: "Error",
  STOPPED: "Stopped",
};

export function SystemStatus({ status }: SystemStatusProps) {
  const rows: { label: string; value: React.ReactNode }[] = [
    {
      label: "Status",
      value: (
        <Badge variant={statusVariant(status.engineState)} className="text-[0.5rem]">
          {statusLabel[status.engineState]}
        </Badge>
      ),
    },
    { label: "Uptime", value: status.uptime },
    { label: "Scan interval", value: `${status.scanInterval}s` },
    ...(status.connections ?? []).map((conn) => ({
      label: conn.label,
      value: (
        <span
          className={cn(
            "inline-block size-1.5 shrink-0 rounded-full",
            conn.connected ? "bg-positive" : "bg-destructive"
          )}
        />
      ),
    })),
  ];

  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        System Status
      </span>
      <div className="mt-3 flex flex-col gap-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{r.label}</span>
            <span className="tabular-nums">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
