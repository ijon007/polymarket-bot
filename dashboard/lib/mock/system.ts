import type { SystemStatus, ScanConfig } from "@/types/dashboard";

export const mockSystemStatus: SystemStatus = {
  engineState: "SCANNING",
  connections: [
    { label: "Polymarket API", connected: true },
    { label: "Database", connected: true },
    { label: "Engine", connected: true },
  ],
  uptime: "04:12:37",
  memory: "247 MB",
  scanInterval: 10,
};

export const mockScanConfig: ScanConfig = {
  minVolume: 100_000,
  minLiquidity: 50_000,
  edgeThreshold: 15,
  maxMarkets: 25,
  strategy: "last_second",
};
