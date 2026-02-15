"use client";

import { useState, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { timeAgo } from "@/lib/format";
import type { TradeRow } from "@/types/dashboard";
import type { DashboardFilter } from "./date-range-bar";
import { CaretUpIcon, CaretDownIcon, FileCsvIcon } from "@phosphor-icons/react";

interface ActivePositionsProps {
  trades: TradeRow[];
  filter?: DashboardFilter;
}

type SortKey = "market" | "side" | "price" | "size" | "pnl" | "status" | "executedAt";
type SortDir = "asc" | "desc";

function downloadCsv(trades: TradeRow[]) {
  const headers = ["Market", "Question", "Side", "Price", "Size", "P&L", "Status", "Executed At"];
  const rows = trades.map((t) => [
    t.market,
    `"${(t.question || "").replace(/"/g, '""')}"`,
    t.side,
    t.price,
    t.size,
    t.pnl,
    t.status,
    t.executedAt,
  ]);
  const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `positions-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export function ActivePositions({ trades, filter }: ActivePositionsProps) {
  const [sortKey, setSortKey] = useState<SortKey>("executedAt");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const filtered = useMemo(() => {
    if (!filter) return trades;
    return trades.filter((t) => {
      if (filter.positionSide !== "all" && t.side !== filter.positionSide.toUpperCase()) return false;
      if (filter.status !== "all") {
        const status = t.status.toLowerCase();
        if (filter.status === "executed" && status !== "executed") return false;
        if (filter.status === "pending" && status !== "paper") return false;
        if (filter.status === "settled" && status !== "settled") return false;
      }
      return true;
    });
  }, [trades, filter]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let av: string | number = a[sortKey];
      let bv: string | number = b[sortKey];
      if (sortKey === "executedAt") {
        av = new Date(av as string).getTime();
        bv = new Date(bv as string).getTime();
      }
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      const cmp = String(av).localeCompare(String(bv));
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
    <th className={cn("pb-2 pr-3 font-medium", align === "right" && "text-right")}>
      <button
        type="button"
        onClick={() => toggleSort(keyName)}
        className={cn(
          "flex items-center gap-0.5 uppercase text-muted-foreground hover:text-foreground focus:outline-none focus:ring-2 focus:ring-ring rounded",
          align === "right" && "ml-auto"
        )}
      >
        {label}
        {sortKey === keyName ? (
          sortDir === "asc" ? (
            <CaretUpIcon className="size-3" />
          ) : (
            <CaretDownIcon className="size-3" />
          )
        ) : null}
      </button>
    </th>
  );

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
        <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
          Positions
        </span>
        <div className="flex items-center gap-2">
          <span className="tabular-nums text-[0.65rem] text-muted-foreground">
            {filtered.length}
            {filtered.length !== trades.length && (
              <span className="text-muted-foreground/70"> / {trades.length}</span>
            )}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 gap-1 text-muted-foreground hover:text-foreground"
            onClick={() => downloadCsv(sorted)}
            disabled={sorted.length === 0}
            aria-label="Export to CSV"
          >
            <FileCsvIcon className="size-3.5" weight="duotone" />
            Export
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 pb-3">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-left text-[0.6rem]">
              <Th label="Market" keyName="market" />
              <Th label="Side" keyName="side" />
              <Th label="Price" keyName="price" align="right" />
              <Th label="Size" keyName="size" align="right" />
              <Th label="P&L" keyName="pnl" align="right" />
              <Th label="Status" keyName="status" align="right" />
              <Th label="Time" keyName="executedAt" align="right" />
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-muted-foreground">
                  {filtered.length === 0 && trades.length > 0 ? (
                    <>No positions match the current filters. Clear filters to see all.</>
                  ) : (
                    <>No positions yet. Trades will appear here.</>
                  )}
                </td>
              </tr>
            ) : (
              sorted.map((t) => (
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
                  <td className="py-1.5 pr-3 text-right">
                    <Badge
                      variant={t.status === "settled" ? "outline" : t.status === "paper" ? "secondary" : "destructive"}
                      className="text-[0.5rem]"
                    >
                      {t.status}
                    </Badge>
                  </td>
                  <td className="py-1.5 text-right tabular-nums text-muted-foreground" title={t.executedAt}>
                    {timeAgo(t.executedAt)}
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
