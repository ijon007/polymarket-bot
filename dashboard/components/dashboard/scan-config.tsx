import type { ScanConfig as ScanConfigType } from "@/types/dashboard";

interface ScanConfigProps {
  config: ScanConfigType;
}

function compact(v: number) {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

export function ScanConfig({ config }: ScanConfigProps) {
  const rows = [
    { label: "Min Volume", value: compact(config.minVolume) },
    { label: "Min Liquidity", value: compact(config.minLiquidity) },
    { label: "Edge Threshold", value: `${config.edgeThreshold}%` },
    { label: "Max Markets", value: String(config.maxMarkets) },
    { label: "Strategy", value: config.strategy },
  ];

  return (
    <div className="flex h-full flex-col p-4">
      <span className="text-[0.65rem] font-medium uppercase text-muted-foreground">
        Scan Config
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
