// ---------------------------------------------------------------------------
// Shared types for the Polymarket bot dashboard
// ---------------------------------------------------------------------------

export type EngineState = "SCANNING" | "IDLE" | "ERROR" | "STOPPED";
export type LogLevel = "INFO" | "WARN" | "ERROR";
export type TradeStatus = "paper" | "executed" | "settled" | "failed";
export type TradeSide = "YES" | "NO";

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export interface ConnectionStatus {
  label: string;
  connected: boolean;
}

export interface SystemStatus {
  engineState: EngineState;
  connections: ConnectionStatus[];
  uptime: string;
  memory: string;
  scanInterval: number;
}

// ---------------------------------------------------------------------------
// Scan config
// ---------------------------------------------------------------------------

export interface ScanConfig {
  minVolume: number;
  minLiquidity: number;
  edgeThreshold: number;
  maxMarkets: number;
  strategy: string;
}

// ---------------------------------------------------------------------------
// Account
// ---------------------------------------------------------------------------

export interface AccountSummary {
  equity: number;
  bankroll: number;
  totalPnl: number;
  totalPnlPct: number;
  realizedPnl: number;
  unrealizedPnl: number;
}

// ---------------------------------------------------------------------------
// Trades / Positions
// ---------------------------------------------------------------------------

export interface TradeRow {
  id: number;
  market: string;
  question: string;
  side: TradeSide;
  price: number;
  size: number;
  pnl: number;
  status: TradeStatus;
  executedAt: string;
}

// ---------------------------------------------------------------------------
// Performance
// ---------------------------------------------------------------------------

export interface PerformanceStats {
  winRate: number;
  avgEdge: number;
  totalScans: number;
  roi30d: number;
  tradesWon: number;
  tradesLost: number;
}

// ---------------------------------------------------------------------------
// Logs
// ---------------------------------------------------------------------------

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
}

// ---------------------------------------------------------------------------
// Markets
// ---------------------------------------------------------------------------

export interface MarketRow {
  id: string;
  question: string;
  volume: number;
  yesPrice: number;
  noPrice: number;
  edge: number;
  secondsLeft: number;
}

// ---------------------------------------------------------------------------
// Bot analytics
// ---------------------------------------------------------------------------

export interface BotAnalytics {
  totalTrades: number;
  settled: number;
  pending: number;
  totalPnl: number;
  bestTrade: number;
  worstTrade: number;
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------

export interface PortfolioDataPoint {
  time: string;
  value: number;
}

export interface PositionPerformancePoint {
  time: string;
  [symbol: string]: number | string;
}
