import {
  DashboardHeader,
  AccountSummary,
  ActivePositions,
  SystemStatus,
  ScanConfig,
  PerformanceStats,
  LiveLogs,
  MarketData,
  BotAnalytics,
  PortfolioChart,
  PositionChart,
} from "@/components/dashboard";

import { mockSystemStatus, mockScanConfig } from "@/lib/mock/system";
import { mockAccount } from "@/lib/mock/account";
import { mockPerformance } from "@/lib/mock/performance";
import { mockLogs } from "@/lib/mock/logs";
import { mockMarkets } from "@/lib/mock/markets";
import { mockAnalytics, mockTrades } from "@/lib/mock/analytics";
import { mockPortfolioData, mockPositionPerformance, positionSymbols } from "@/lib/mock/charts";

export default function Page() {
  return (
    <div className="flex min-h-dvh flex-col bg-background font-mono">
      {/* Header */}
      <DashboardHeader status={mockSystemStatus} />

      {/* Main grid — dense, edge-to-edge, shared borders */}
      <div className="grid flex-1 grid-cols-12 grid-rows-[auto_1fr_auto] border-t border-border">
        {/* ── Row 1: Account | Positions | System ── */}
        <div className="col-span-3 border-b border-r border-border">
          <AccountSummary account={mockAccount} />
        </div>
        <div className="col-span-6 border-b border-r border-border">
          <ActivePositions trades={mockTrades} />
        </div>
        <div className="col-span-3 border-b border-border">
          <SystemStatus status={mockSystemStatus} />
        </div>

        {/* ── Row 2: Portfolio Chart | Position Chart ── */}
        <div className="col-span-8 border-b border-r border-border">
          <PortfolioChart data={mockPortfolioData} />
        </div>
        <div className="col-span-4 border-b border-border">
          <PositionChart data={mockPositionPerformance} symbols={positionSymbols} />
        </div>

        {/* ── Row 3: Live Logs | Market Scanner ── */}
        <div className="col-span-8 border-b border-r border-border">
          <LiveLogs logs={mockLogs} />
        </div>
        <div className="col-span-4 border-b border-border">
          <MarketData markets={mockMarkets} />
        </div>

        {/* ── Row 4: Performance | Scan Config | Bot Analytics ── */}
        <div className="col-span-4 border-r border-border">
          <PerformanceStats stats={mockPerformance} />
        </div>
        <div className="col-span-4 border-r border-border">
          <ScanConfig config={mockScanConfig} />
        </div>
        <div className="col-span-4">
          <BotAnalytics analytics={mockAnalytics} />
        </div>
      </div>
    </div>
  );
}
