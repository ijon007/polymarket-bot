import type { PortfolioDataPoint, PositionPerformancePoint } from "@/types/dashboard";

export type BalancePoint = { date: string; balance: number };

export type ChartTimeRange = "1D" | "7D" | "30D" | "90D" | "1M" | "3M";

function addDays(d: Date, n: number) {
  const out = new Date(d);
  out.setDate(out.getDate() + n);
  return out;
}

function addHours(d: Date, n: number) {
  const out = new Date(d);
  out.setHours(out.getHours() + n);
  return out;
}

function fmtDate(d: Date) {
  return d.toISOString().slice(0, 10);
}

function fmtHour(d: Date) {
  return d.toISOString().slice(11, 16);
}

/** Generate balance series that varies by timeframe (mock). */
export function getBalanceOverTime(range: ChartTimeRange): BalancePoint[] {
  const now = new Date();
  const points: BalancePoint[] = [];
  const base = 980;
  const volatility = 80;

  if (range === "1D") {
    const start = addHours(now, -24);
    for (let i = 0; i <= 24; i += 2) {
      const t = addHours(start, i);
      const x = i / 24;
      const noise = Math.sin(x * Math.PI * 2) * 120 + x * 200 + Math.sin(i * 0.7) * 15;
      points.push({ date: fmtHour(t), balance: Math.round(base + noise) });
    }
    return points;
  }

  const days = range === "7D" || range === "1M" ? (range === "7D" ? 7 : 30) : range === "30D" ? 30 : 90;
  const step = range === "3M" ? 3 : 1;
  const start = addDays(now, -days);

  for (let i = 0; i <= days; i += step) {
    const d = addDays(start, i);
    const t = i / days;
    const trend = t * 280 + Math.sin(t * Math.PI * 3) * 60 + Math.sin(i * 0.5) * 12;
    points.push({ date: fmtDate(d), balance: Math.round(base + trend) });
  }

  if (points.length > 0) {
    points[points.length - 1].balance = 1247.83;
  }
  return points;
}

/** OHLC point for candlestick charts. */
export type CandlePoint = { time: string; open: number; high: number; low: number; close: number };

/** Generate OHLC candle data from balance series (mock). */
export function getCandleData(range: ChartTimeRange): CandlePoint[] {
  const balance = getBalanceOverTime(range);
  const out: CandlePoint[] = [];
  for (let i = 0; i < balance.length; i++) {
    const open = i === 0 ? balance[0].balance : balance[i - 1].balance;
    const close = balance[i].balance;
    const spread = Math.max(8, Math.abs(close - open) * 0.15);
    const high = Math.max(open, close) + spread * (0.3 + Math.sin(i) * 0.4);
    const low = Math.min(open, close) - spread * (0.3 + Math.cos(i * 0.7) * 0.4);
    out.push({
      time: balance[i].date,
      open: Math.round(open * 100) / 100,
      high: Math.round(high * 100) / 100,
      low: Math.round(low * 100) / 100,
      close: Math.round(close * 100) / 100,
    });
  }
  return out;
}

/** Cumulative PnL over time (balance - initial balance). */
export type PnlPoint = { date: string; pnl: number };

export function getPnlOverTime(range: ChartTimeRange): PnlPoint[] {
  const balance = getBalanceOverTime(range);
  const initial = balance[0]?.balance ?? 0;
  return balance.map((b) => ({ date: b.date, pnl: b.balance - initial }));
}

/** Generate portfolio value series by timeframe (mock). */
export function getPortfolioOverTime(range: ChartTimeRange): PortfolioDataPoint[] {
  const balance = getBalanceOverTime(range);
  return balance.map((b) => ({ time: b.date, value: b.balance }));
}

export const mockPortfolioData: PortfolioDataPoint[] = [
  { time: "12:00", value: 1000.0 },
  { time: "12:05", value: 1004.9 },
  { time: "12:10", value: 1010.1 },
  { time: "12:15", value: 1008.3 },
  { time: "12:20", value: 1015.5 },
  { time: "12:25", value: 1022.7 },
  { time: "12:30", value: 1018.4 },
  { time: "12:35", value: 1028.6 },
  { time: "12:40", value: 1035.2 },
  { time: "12:45", value: 1031.8 },
  { time: "12:50", value: 1045.4 },
  { time: "12:55", value: 1039.6 },
  { time: "13:00", value: 1034.8 },
  { time: "13:05", value: 1047.0 },
  { time: "13:10", value: 1247.83 },
];

const oct = (d: number) => `2025-10-${String(d).padStart(2, "0")}`;
export const mockBalanceOverTime: BalancePoint[] = [
  { date: oct(1), balance: 980 },
  { date: oct(5), balance: 1020 },
  { date: oct(10), balance: 1050 },
  { date: oct(15), balance: 1030 },
  { date: oct(20), balance: 1100 },
  { date: oct(25), balance: 1150 },
  { date: oct(30), balance: 1247.83 },
];

export const MOCK_TOTAL_PROFIT = 279972;
export const MOCK_PROFIT_CHANGE_PCT = 13;
export const MOCK_MARKET_CAP = 27_800_000;
export const MOCK_MARKET_CAP_CHANGE_PCT = 32;
export const MOCK_MINI_BAR_VALUES = [40, 75, 55, 90];

export const mockPositionPerformance: PositionPerformancePoint[] = [
  { time: "12:00", BTC: 0, ETH: 0, SOL: 0 },
  { time: "12:05", BTC: 1.2, ETH: -0.5, SOL: 0.8 },
  { time: "12:10", BTC: 2.8, ETH: -1.2, SOL: 1.5 },
  { time: "12:15", BTC: 1.9, ETH: 0.3, SOL: 2.1 },
  { time: "12:20", BTC: 3.5, ETH: 1.1, SOL: 1.8 },
  { time: "12:25", BTC: 4.2, ETH: 2.4, SOL: 3.2 },
  { time: "12:30", BTC: 3.8, ETH: 1.8, SOL: 2.6 },
  { time: "12:35", BTC: 5.1, ETH: 3.2, SOL: 4.1 },
  { time: "12:40", BTC: 6.3, ETH: 2.7, SOL: 3.5 },
  { time: "12:45", BTC: 5.8, ETH: 3.9, SOL: 4.8 },
  { time: "12:50", BTC: 7.2, ETH: 4.5, SOL: 5.2 },
  { time: "12:55", BTC: 6.5, ETH: 3.8, SOL: 4.0 },
  { time: "13:00", BTC: 8.1, ETH: 5.2, SOL: 5.8 },
  { time: "13:05", BTC: 9.4, ETH: 4.8, SOL: 6.3 },
  { time: "13:10", BTC: 10.2, ETH: 5.6, SOL: 7.1 },
];

export const positionSymbols = ["BTC", "ETH", "SOL"] as const;
