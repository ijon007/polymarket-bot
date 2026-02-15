import type { PortfolioDataPoint, PositionPerformancePoint } from "@/types/dashboard";

export const mockPortfolioData: PortfolioDataPoint[] = [
  { time: "12:00", value: 1000.00 },
  { time: "12:05", value: 1004.90 },
  { time: "12:10", value: 1010.10 },
  { time: "12:15", value: 1008.30 },
  { time: "12:20", value: 1015.50 },
  { time: "12:25", value: 1022.70 },
  { time: "12:30", value: 1018.40 },
  { time: "12:35", value: 1028.60 },
  { time: "12:40", value: 1035.20 },
  { time: "12:45", value: 1031.80 },
  { time: "12:50", value: 1045.40 },
  { time: "12:55", value: 1039.60 },
  { time: "13:00", value: 1034.80 },
  { time: "13:05", value: 1047.00 },
  { time: "13:10", value: 1247.83 },
];

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
