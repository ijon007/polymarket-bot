import type { StreakGraph, StreakTradeEntry, TradeOutcome } from "@/types/dashboard";

const COLS = 10;
const ROWS = 4;
const TOTAL = COLS * ROWS; // 40

function computeStreak(history: StreakTradeEntry[]): { currentStreak: number; streakType: "W" | "L" } {
  if (history.length === 0) return { currentStreak: 0, streakType: "W" };
  const last = history[history.length - 1].outcome;
  let count = 0;
  for (let i = history.length - 1; i >= 0 && history[i].outcome === last; i--) count++;
  return { currentStreak: count, streakType: last === "won" ? "W" : "L" };
}

function makeEntry(outcome: TradeOutcome, pnl: number, i: number): StreakTradeEntry {
  const minsAgo = (TOTAL - 1 - i) * 5;
  const d = new Date();
  d.setMinutes(d.getMinutes() - minsAgo);
  return {
    outcome,
    pnl,
    executedAt: d.toISOString().slice(0, 16).replace("T", " "),
    side: i % 2 === 0 ? "UP" : "DOWN",
  };
}

// Fixed mock: mix of W/L with PnL and time, current streak 3W
const history: StreakTradeEntry[] = [
  ...Array.from({ length: TOTAL - 3 }, (_, i) => {
    const lost = i % 5 === 0 || i % 5 === 1;
    return makeEntry(lost ? "lost" : "won", lost ? -10 + (i % 3) : 4 + (i % 5), i);
  }),
  makeEntry("won", 6.1, TOTAL - 3),
  makeEntry("won", 4.2, TOTAL - 2),
  makeEntry("won", 5.0, TOTAL - 1),
];

const { currentStreak, streakType } = computeStreak(history);

export const mockStreakGraph: StreakGraph = {
  history,
  currentStreak,
  streakType,
};
