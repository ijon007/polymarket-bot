"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import type { MarketRow } from "@/types/dashboard";
import { CaretUpIcon, CaretDownIcon, MagnifyingGlassIcon } from "@phosphor-icons/react";
import { Input } from "@/components/ui/input";

interface MarketDataProps {
  markets: MarketRow[];
}

type SortKey = "question" | "volume" | "yesPrice" | "noPrice" | "edge" | "secondsLeft";
type SortDir = "asc" | "desc";

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
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("edge");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const filtered = useMemo(() => {
    if (!search.trim()) return markets;
    const q = search.trim().toLowerCase();
    return markets.filter(
      (m) =>
        m.question.toLowerCase().includes(q) ||
        m.id.toLowerCase().includes(q)
    );
  }, [markets, search]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const cmp =
        typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    setSortKey(key);
    setSortDir((d) => (sortKey === key ? (d === "asc" ? "desc" : "asc") : "desc"));
  };

  const Th = ({
    label,
    keyName,
    align = "left",
  }: {
    label: string;
    keyName: SortKey;
    align?: "left" | "right";
  }) => (
    <th className={cn("pb-2 pr-2 font-medium text-[0.6rem] uppercase", align === "right" && "text-right")}>
      <button
        type="button"
        onClick={() => toggleSort(keyName)}
        className={cn(
          "flex items-center gap-0.5 text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring rounded w-full",
          align === "right" && "ml-auto justify-end"
        )}
      >
        {label}
        {sortKey === keyName ? (
          sortDir === "asc" ? (
            <CaretUpIcon className="size-3 shrink-0" />
          ) : (
            <CaretDownIcon className="size-3 shrink-0" />
          )
        ) : null}
      </button>
    </th>
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Market Scanner
        </span>
        <span className="tabular-nums text-[0.65rem] text-muted-foreground">
          {filtered.length} / {markets.length} markets
        </span>
      </div>
      <div className="px-4 pb-2">
        <div className="relative">
          <MagnifyingGlassIcon
            className="absolute left-2 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground"
            weight="duotone"
          />
          <Input
            type="search"
            placeholder="Search markets..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-7 pl-7 text-xs"
            aria-label="Search markets"
          />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-4 pb-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left">
              <Th label="Market" keyName="question" />
              <Th label="Vol" keyName="volume" align="right" />
              <Th label="Yes" keyName="yesPrice" align="right" />
              <Th label="No" keyName="noPrice" align="right" />
              <Th label="Edge" keyName="edge" align="right" />
              <Th label="Time" keyName="secondsLeft" align="right" />
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-muted-foreground">
                  {search.trim()
                    ? "No markets match your search."
                    : "No markets in scan. Adjust scan config."}
                </td>
              </tr>
            ) : (
              sorted.map((m) => (
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
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
