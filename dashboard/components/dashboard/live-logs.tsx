import { cn } from "@/lib/utils";
import type { LogEntry } from "@/types/dashboard";

interface LiveLogsProps {
  logs: LogEntry[];
}

const levelColor: Record<LogEntry["level"], string> = {
  INFO: "text-foreground/80",
  WARN: "text-chart-1",
  ERROR: "text-destructive",
};

export function LiveLogs({ logs }: LiveLogsProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Live Logs
        </span>
        <span className="tabular-nums text-[0.65rem] text-muted-foreground">
          {logs.length} entries
        </span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-3">
        {logs.map((entry, i) => (
          <p key={i} className="text-[0.7rem] leading-5">
            <span className="text-muted-foreground/60">[{entry.timestamp}]</span>{" "}
            <span className={cn(levelColor[entry.level])}>{entry.message}</span>
          </p>
        ))}
      </div>
    </div>
  );
}
