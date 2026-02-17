export interface AccountSummary {
  equity: number;
  winRate: number;
  totalPnl: number;
  totalPnlPct: number;
  realizedPnl: number;
  todayPnl: number;
}

export interface BotAnalytics {
  totalTrades: number;
  settled: number;
  pending: number;
  totalPnl: number;
  bestTrade: number;
  worstTrade: number;
}

export type TradeOutcome = "won" | "lost";

export interface StreakTradeEntry {
  outcome: TradeOutcome;
  pnl: number;
  executedAt: string;
  side: "UP" | "DOWN";
}

export interface StreakGraph {
  history: StreakTradeEntry[];
  currentStreak: number;
  streakType: "W" | "L";
}

export type SystemStatusEngineState = "SCANNING" | "IDLE" | "ERROR" | "STOPPED";

export interface SystemStatus {
  engineState: SystemStatusEngineState;
  connections?: { label: string; connected: boolean }[];
  uptime: string;
  scanInterval: number;
}

export interface SystemStatusEntry {
  key: string;
  status: SystemStatus;
}

export interface ScanConfig {
  minVolume: number;
  minLiquidity: number;
  edgeThreshold: number;
  maxMarkets: number;
  strategy: string;
}

export type LogLevel = "INFO" | "WARN" | "ERROR";

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
}

export interface TradeRow {
  id: string;
  market: string;
  question: string;
  side: string;
  price: number;
  size: number;
  pnl: number;
  status: "paper" | "settled";
  executedAt: string;
  strategy?: string;
  signalType?: string;
  interval?: "5m" | "15m";
}

export interface MarketRow {
  id: string;
  question: string;
  volume: number;
  yesPrice: number;
  noPrice: number;
  edge: number;
  secondsLeft: number;
}

export interface PerformanceStats {
  winRate: number;
  avgEdge: number;
  totalScans: number;
  roi30d: number;
  tradesWon: number;
  tradesLost: number;
}

export interface PortfolioDataPoint {
  date: string;
  balance: number;
  pnl?: number;
}

export interface PositionPerformancePoint {
  symbol: string;
  pnl: number;
  pnlPct: number;
}
