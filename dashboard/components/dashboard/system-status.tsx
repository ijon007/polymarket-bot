import { Badge } from "@/components/ui/badge";
import type { SystemStatus as SystemStatusType } from "@/types/dashboard";

interface SystemStatusProps {
  status: SystemStatusType;
}

const engineVariant = (s: SystemStatusType["engineState"]) => {
  switch (s) {
    case "SCANNING": return "default" as const;
    case "IDLE": return "secondary" as const;
    default: return "destructive" as const;
  }
};

export function SystemStatus({ status }: SystemStatusProps) {
  const rows: { label: string; value: React.ReactNode }[] = [
    {
      label: "Engine",
      value: (
        <Badge variant={engineVariant(status.engineState)} className="text-[0.5rem]">
          {status.engineState}
        </Badge>
      ),
    },
    {
      label: "MCP Links",
      value: `${status.connections.filter((c) => c.connected).length}/${status.connections.length}`,
    },
    { label: "Uptime", value: status.uptime },
    { label: "Memory", value: status.memory },
    { label: "Interval", value: `${status.scanInterval}s` },
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
