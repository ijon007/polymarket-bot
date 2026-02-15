"use client";

import type { ScanConfig as ScanConfigType } from "@/types/dashboard";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ScanConfigProps {
  config: ScanConfigType;
  onConfigChange?: (config: ScanConfigType) => void;
}

export function ScanConfig({ config, onConfigChange }: ScanConfigProps) {
  const editable = !!onConfigChange;

  const update = (key: keyof ScanConfigType, value: string | number) => {
    if (!onConfigChange) return;
    const next = { ...config };
    if (key === "minVolume" || key === "minLiquidity" || key === "edgeThreshold" || key === "maxMarkets") {
      (next as Record<string, number>)[key] = typeof value === "number" ? value : Number(String(value).replace(/[^0-9.]/g, "")) || 0;
    } else {
      (next as Record<string, string>)[key] = String(value);
    }
    onConfigChange(next);
  };

  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        Scan Config
      </span>
      <div className="mt-3 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2 text-xs">
          <Label className="text-muted-foreground shrink-0">Min Volume</Label>
          {editable ? (
            <Input
              type="number"
              min={0}
              value={config.minVolume}
              onChange={(e) => update("minVolume", Number(e.target.value) || 0)}
              className="h-6 w-20 text-right text-xs tabular-nums"
            />
          ) : (
            <span className="tabular-nums">
              {config.minVolume >= 1_000_000 ? `$${(config.minVolume / 1_000_000).toFixed(1)}M` : config.minVolume >= 1_000 ? `$${(config.minVolume / 1_000).toFixed(0)}K` : `$${config.minVolume}`}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 text-xs">
          <Label className="text-muted-foreground shrink-0">Min Liquidity</Label>
          {editable ? (
            <Input
              type="number"
              min={0}
              value={config.minLiquidity}
              onChange={(e) => update("minLiquidity", Number(e.target.value) || 0)}
              className="h-6 w-20 text-right text-xs tabular-nums"
            />
          ) : (
            <span className="tabular-nums">
              {config.minLiquidity >= 1_000 ? `$${(config.minLiquidity / 1_000).toFixed(0)}K` : `$${config.minLiquidity}`}
            </span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 text-xs">
          <Label className="text-muted-foreground shrink-0">Edge %</Label>
          {editable ? (
            <Input
              type="number"
              min={0}
              max={100}
              value={config.edgeThreshold}
              onChange={(e) => update("edgeThreshold", Number(e.target.value) || 0)}
              className="h-6 w-20 text-right text-xs tabular-nums"
            />
          ) : (
            <span className="tabular-nums">{config.edgeThreshold}%</span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 text-xs">
          <Label className="text-muted-foreground shrink-0">Max Markets</Label>
          {editable ? (
            <Input
              type="number"
              min={1}
              max={500}
              value={config.maxMarkets}
              onChange={(e) => update("maxMarkets", Number(e.target.value) || 10)}
              className="h-6 w-20 text-right text-xs tabular-nums"
            />
          ) : (
            <span className="tabular-nums">{config.maxMarkets}</span>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 text-xs">
          <Label className="text-muted-foreground shrink-0">Strategy</Label>
          {editable ? (
            <Input
              type="text"
              value={config.strategy}
              onChange={(e) => update("strategy", e.target.value)}
              className="h-6 flex-1 text-right text-xs"
            />
          ) : (
            <span className="truncate tabular-nums">{config.strategy}</span>
          )}
        </div>
      </div>
    </div>
  );
}
