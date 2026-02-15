"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { SystemStatus } from "@/types/dashboard";
import {
  WalletIcon,
  SunIcon,
  MoonIcon,
  BellIcon,
} from "@phosphor-icons/react";

interface DashboardHeaderProps {
  status: SystemStatus;
}

export function DashboardHeader({ status }: DashboardHeaderProps) {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  const toggleTheme = () => {
    setTheme((t) => {
      const next = t === "dark" ? "light" : "dark";
      if (next === "light") document.documentElement.classList.remove("dark");
      else document.documentElement.classList.add("dark");
      return next;
    });
  };

  return (
    <header
      className="flex items-center justify-between border-b border-border/60 bg-card/80 px-4 py-3 backdrop-blur-sm animate-in fade-in slide-in-from-top-1 duration-200"
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Polymarket Alpha Scanner
        </span>
        <Badge
          variant="outline"
          className="text-[0.6rem] tabular-nums border-border/60 text-muted-foreground"
        >
          v2.1.0
        </Badge>
        <div className="hidden items-center gap-3 sm:flex">
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
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          className="gap-2 rounded border-border/60 bg-muted/50 px-3 py-2 text-foreground hover:bg-muted"
          aria-label="Connect wallet"
        >
          <WalletIcon className="size-4" weight="duotone" />
          <span className="text-xs font-medium">Connect Wallet</span>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="rounded text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          onClick={toggleTheme}
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {theme === "dark" ? (
            <SunIcon className="size-4" weight="duotone" />
          ) : (
            <MoonIcon className="size-4" weight="duotone" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="rounded text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          aria-label="Notifications"
        >
          <BellIcon className="size-4" weight="duotone" />
        </Button>
        <div
          className="size-8 shrink-0 rounded-full bg-primary/20 ring-2 ring-border/60"
          aria-hidden
        />
      </div>
    </header>
  );
}
