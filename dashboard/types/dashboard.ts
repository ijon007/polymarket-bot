// ---------------------------------------------------------------------------
// Shared types for the Polymarket bot dashboard
// ---------------------------------------------------------------------------

export type EngineState = "SCANNING" | "IDLE" | "ERROR" | "STOPPED";
export type LogLevel = "INFO" | "WARN" | "ERROR";
export type TradeStatus = "paper" | "executed" | "settled" | "failed";
export type TradeSide = "UP" | "DOWN";

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export interface ConnectionStatus {
  label: string;
  connected: boolean;
}

export interface SystemStatus {
  engineState: EngineState;
  /** Optional: Polymarket API, Database, RTDS – shown in header when provided */
  connections?: ConnectionStatus[];
  uptime: string;
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
  winRate: number;
  totalPnl: number;
  totalPnlPct: number;
  realizedPnl: number;
  todayPnl: number;
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

/** One cell = one settled trade. Oldest first; display left-to-right, top-to-bottom. */
export type TradeOutcome = "won" | "lost";

export interface StreakTradeEntry {
  outcome: TradeOutcome;
  pnl: number;
  executedAt: string;
  side: TradeSide;
}

export interface StreakGraph {
  /** Last N settled trades (oldest first). Each entry drives one cell + tooltip. */
  history: StreakTradeEntry[];
  /** Current run from end: e.g. 3 = "3W" or "3L" */
  currentStreak: number;
  streakType: "W" | "L";
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
