import type { SystemStatus, ScanConfig } from "@/types/dashboard";

// Aligned with main.py: SCAN_INTERVAL=10; engineState = scanner loop (SCANNING | IDLE | ERROR | STOPPED)
export const mockSystemStatus: SystemStatus = {
  engineState: "SCANNING",
  connections: [
    { label: "Polymarket API", connected: true },
    { label: "Database", connected: true },
    { label: "RTDS (Chainlink)", connected: true },
  ],
  uptime: "04:12:37",
  scanInterval: 10,
};

// Bot only scans BTC 5-min markets; last_second strategy (trigger_seconds: 30, position_size: 10)
export const mockScanConfig: ScanConfig = {
  minVolume: 100_000,
  minLiquidity: 50_000,
  edgeThreshold: 15,
  maxMarkets: 25,
  strategy: "last_second",
};
