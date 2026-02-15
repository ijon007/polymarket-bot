import type { BotAnalytics, TradeRow } from "@/types/dashboard";

// From bot: Trade table counts (settled = won+lost, pending = paper); best/worst = max/min actual_profit
export const mockAnalytics: BotAnalytics = {
  totalTrades: 194,
  settled: 178,
  pending: 16,
  totalPnl: 247.83,
  bestTrade: 48.20,
  worstTrade: -22.50,
};

// Bot only trades btc-updown-5m-{window_start_ts}; status in DB is paper | won | lost (display won/lost as "settled")
// Base set (current day, one paper)
const baseTrades: TradeRow[] = [
  {
    id: 194,
    market: "btc-updown-5m-1771083600",
    question: "Will BTC go up in the next 5 min?",
    side: "YES",
    price: 0.52,
    size: 10.0,
    pnl: 0,
    status: "paper",
    executedAt: "2026-02-15 13:10:50",
  },
  {
    id: 193,
    market: "btc-updown-5m-1771083000",
    question: "Will BTC go up in the next 5 min?",
    side: "NO",
    price: 0.39,
    size: 10.0,
    pnl: 6.1,
    status: "settled",
    executedAt: "2026-02-15 13:05:48",
  },
  {
    id: 192,
    market: "btc-updown-5m-1771082400",
    question: "Will BTC go up in the next 5 min?",
    side: "YES",
    price: 0.55,
    size: 10.0,
    pnl: -10.0,
    status: "settled",
    executedAt: "2026-02-15 13:00:32",
  },
  {
    id: 191,
    market: "btc-updown-5m-1771082400",
    question: "Will BTC go up in the next 5 min?",
    side: "YES",
    price: 0.48,
    size: 10.0,
    pnl: 5.2,
    status: "settled",
    executedAt: "2026-02-15 13:00:30",
  },
  {
    id: 190,
    market: "btc-updown-5m-1771081800",
    question: "Will BTC go up in the next 5 min?",
    side: "YES",
    price: 0.51,
    size: 10.0,
    pnl: 4.9,
    status: "settled",
    executedAt: "2026-02-15 12:55:29",
  },
  {
    id: 189,
    market: "btc-updown-5m-1771081200",
    question: "Will BTC go up in the next 5 min?",
    side: "NO",
    price: 0.42,
    size: 10.0,
    pnl: -10.0,
    status: "settled",
    executedAt: "2026-02-15 12:55:28",
  },
  {
    id: 188,
    market: "btc-updown-5m-1771080600",
    question: "Will BTC go up in the next 5 min?",
    side: "YES",
    price: 0.58,
    size: 10.0,
    pnl: 4.2,
    status: "settled",
    executedAt: "2026-02-15 12:50:15",
  },
  {
    id: 187,
    market: "btc-updown-5m-1771080300",
    question: "Will BTC go up in the next 5 min?",
    side: "YES",
    price: 0.46,
    size: 10.0,
    pnl: 5.4,
    status: "settled",
    executedAt: "2026-02-15 12:50:12",
  },
];

/** Generate settled trades for heatmap: date YYYY-MM-DD, hour 0-23, wins vs total, idStart. */
function genSlot(
  date: string,
  hour: number,
  wins: number,
  total: number,
  idStart: number
): TradeRow[] {
  const rows: TradeRow[] = [];
  const h = String(hour).padStart(2, "0");
  for (let i = 0; i < total; i++) {
    const win = i < wins;
    rows.push({
      id: idStart + i,
      market: `btc-updown-5m-${idStart + i}`,
      question: "Will BTC go up in the next 5 min?",
      side: "UP",
      price: 0.5,
      size: 10.0,
      pnl: win ? 6 : -10,
      status: "settled",
      executedAt: `${date} ${h}:${String(i % 60).padStart(2, "0")}:00`,
    });
  }
  return rows;
}

// Spread across week + time slots so heatmap is full. Dates 2026-02-09 (Mon) .. 2026-02-15 (Sun)
const heatmapSlots: { date: string; hour: number; wins: number; total: number }[] = [
  { date: "2026-02-09", hour: 8, wins: 6, total: 8 },   // Mon 08-10 strong
  { date: "2026-02-09", hour: 14, wins: 2, total: 7 }, // Mon 14-16 weak
  { date: "2026-02-09", hour: 20, wins: 5, total: 8 },
  { date: "2026-02-10", hour: 2, wins: 4, total: 6 },  // Tue night
  { date: "2026-02-10", hour: 10, wins: 7, total: 9 },  // Tue 10-12 strong
  { date: "2026-02-10", hour: 16, wins: 3, total: 8 },
  { date: "2026-02-11", hour: 6, wins: 5, total: 7 },   // Wed early
  { date: "2026-02-11", hour: 12, wins: 2, total: 9 }, // Wed 12-14 weak
  { date: "2026-02-11", hour: 18, wins: 4, total: 8 },
  { date: "2026-02-12", hour: 4, wins: 3, total: 6 },  // Thu 04-06
  { date: "2026-02-12", hour: 10, wins: 8, total: 10 }, // Thu 10-12 best
  { date: "2026-02-12", hour: 22, wins: 1, total: 5 },  // Thu 22-24 worst
  { date: "2026-02-13", hour: 0, wins: 4, total: 6 },   // Fri midnight
  { date: "2026-02-13", hour: 8, wins: 5, total: 7 },
  { date: "2026-02-13", hour: 14, wins: 6, total: 9 },
  { date: "2026-02-14", hour: 10, wins: 4, total: 8 },   // Sat
  { date: "2026-02-14", hour: 16, wins: 7, total: 9 },
  { date: "2026-02-14", hour: 20, wins: 2, total: 6 },
  { date: "2026-02-15", hour: 12, wins: 5, total: 7 },   // Sun 12-14 (existing bucket)
];

let nextId = 200;
const extraTrades: TradeRow[] = [];
for (const slot of heatmapSlots) {
  extraTrades.push(...genSlot(slot.date, slot.hour, slot.wins, slot.total, nextId));
  nextId += slot.total;
}

export const mockTrades: TradeRow[] = [...baseTrades, ...extraTrades];
