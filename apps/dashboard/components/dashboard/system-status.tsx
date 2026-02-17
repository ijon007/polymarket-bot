import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { SystemStatus as SystemStatusType, SystemStatusEntry } from "@/types/dashboard";

interface SystemStatusProps {
  status: SystemStatusType;
}

const statusVariant = (s: SystemStatusType["engineState"]) => {
  switch (s) {
    case "SCANNING": return "default" as const;
    case "IDLE": return "secondary" as const;
    case "STOPPED": return "destructive" as const;
    case "ERROR": return "destructive" as const;
    default: return "secondary" as const;
  }
};

const statusLabel: Record<SystemStatusType["engineState"], string> = {
  SCANNING: "Scanning",
  IDLE: "Idle",
  ERROR: "Error",
  STOPPED: "Stopped",
};

const engineTitle: Record<string, string> = {
  "5min": "5 min engine",
  "15min": "15 min engine",
};

function StatusSection({ status, title }: { status: SystemStatusType; title?: string }) {
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
    <div className={cn(title && "mt-4 first:mt-0")}>
      {title && (
        <span className="text-[0.6rem] font-medium uppercase text-muted-foreground">
          {title}
        </span>
      )}
      <div className={cn("flex flex-col gap-2", title && "mt-2")}>
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

export function SystemStatus({ status }: SystemStatusProps) {
  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        System Status
      </span>
      <div className="mt-3">
        <StatusSection status={status} />
      </div>
    </div>
  );
}

interface SystemStatusAllProps {
  entries: SystemStatusEntry[];
}

export function SystemStatusAll({ entries }: SystemStatusAllProps) {
  if (entries.length === 0) return null;
  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        System Status
      </span>
      <div className="mt-3">
        {entries.map((e) => (
          <StatusSection
            key={e.key}
            status={e.status}
            title={engineTitle[e.key] ?? e.key}
          />
        ))}
      </div>
    </div>
  );
}
