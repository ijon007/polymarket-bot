"use client";

import { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import type { LogEntry, LogLevel } from "@/types/dashboard";
import { CaretUpIcon, CaretDownIcon } from "@phosphor-icons/react";

const MOBILE_BREAKPOINT = "(max-width: 1023px)";

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const m = window.matchMedia(MOBILE_BREAKPOINT);
    const update = () => setIsMobile(m.matches);
    update();
    m.addEventListener("change", update);
    return () => m.removeEventListener("change", update);
  }, []);
  return isMobile;
}

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
  const isMobile = useIsMobile();
  const [mobileExpanded, setMobileExpanded] = useState(false);

  const filtered = levelFilter === "ALL"
    ? logs
    : logs.filter((e) => e.level === levelFilter);

  useEffect(() => {
    if (!follow || !containerRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [filtered.length]);

  return (
    <div className="flex h-full flex-col">
      <div
        className={cn(
          "flex flex-wrap items-center justify-between gap-2 px-4 py-3",
          isMobile && "cursor-pointer select-none touch-manipulation"
        )}
        role={isMobile ? "button" : undefined}
        tabIndex={isMobile ? 0 : undefined}
        onClick={isMobile ? () => setMobileExpanded((v) => !v) : undefined}
        onKeyDown={
          isMobile
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setMobileExpanded((v) => !v);
                }
              }
            : undefined
        }
        aria-expanded={isMobile ? mobileExpanded : undefined}
        aria-label={isMobile ? (mobileExpanded ? "Collapse logs" : "Expand logs") : undefined}
      >
        <span className="flex items-center gap-1.5 text-[0.65rem] font-medium uppercase text-muted-foreground">
          {isMobile && (
            <span className="text-muted-foreground" aria-hidden>
              {mobileExpanded ? (
                <CaretUpIcon className="size-3.5" />
              ) : (
                <CaretDownIcon className="size-3.5" />
              )}
            </span>
          )}
          Live Logs
        </span>
        <div className="flex gap-0.5" onClick={(e) => e.stopPropagation()}>
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
      {(!isMobile || mobileExpanded) && (
      <div
        ref={containerRef}
        className="flex-1 min-h-0 overflow-y-auto scrollbar-thin overflow-x-hidden px-4 pb-3"
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
      )}
    </div>
  );
}
