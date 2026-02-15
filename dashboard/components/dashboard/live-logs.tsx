"use client";

import { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { LogEntry, LogLevel } from "@/types/dashboard";

interface LiveLogsProps {
  logs: LogEntry[];
  follow?: boolean;
}

const LEVELS: { value: LogLevel | "ALL"; label: string }[] = [
  { value: "ALL", label: "All" },
  { value: "INFO", label: "Info" },
  { value: "WARN", label: "Warn" },
  { value: "ERROR", label: "Error" },
];

const levelColor: Record<LogEntry["level"], string> = {
  INFO: "text-foreground/80",
  WARN: "text-chart-1",
  ERROR: "text-destructive",
};

export function LiveLogs({ logs, follow = true }: LiveLogsProps) {
  const [levelFilter, setLevelFilter] = useState<LogLevel | "ALL">("ALL");
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = levelFilter === "ALL"
    ? logs
    : logs.filter((e) => e.level === levelFilter);

  useEffect(() => {
    if (!follow || !containerRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [filtered.length]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Live Logs
        </span>
        <div className="flex gap-0.5">
          {LEVELS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setLevelFilter(value)}
              className={cn(
                "rounded px-2 py-0.5 text-[0.6rem] font-medium transition-colors",
                levelFilter === value
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overflow-x-hidden px-4 pb-3"
      >
        {filtered.length === 0 ? (
          <p className="py-4 text-center text-[0.7rem] text-muted-foreground">
            No log entries
            {levelFilter !== "ALL" ? ` for ${levelFilter}` : ""}.
          </p>
        ) : (
          filtered.map((entry, i) => (
            <p key={i} className="text-[0.7rem] leading-5">
              <span className="text-muted-foreground/60">[{entry.timestamp}]</span>{" "}
              <span className={cn(levelColor[entry.level])}>{entry.message}</span>
            </p>
          ))
        )}
      </div>
    </div>
  );
}
