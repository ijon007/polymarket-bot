"use client";

import type { CandlePoint } from "@/lib/mock/charts";

const BULL = "var(--color-positive)";
const BEAR = "var(--color-destructive)";

export interface CandlestickShapeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: CandlePoint;
}

/** Bar scale: value v maps to y + height * (1 - v/close). */
export function CandlestickShape({
  x = 0,
  y = 0,
  width = 8,
  height = 0,
  payload,
}: CandlestickShapeProps) {
  if (!payload) return null;
  const { open, high, low, close } = payload;
  const isBull = close >= open;
  const color = isBull ? BULL : BEAR;
  const scale = (v: number) => y + height * (1 - v / (close || 1));
  const closeY = y;
  const openY = scale(open);
  const highY = scale(high);
  const lowY = scale(low);
  const bodyTop = Math.min(openY, closeY);
  const bodyH = Math.max(Math.abs(closeY - openY), 2);
  const cx = x + width / 2;
  const wickStroke = isBull ? BULL : BEAR;
  const wickOpacity = 0.9;

  return (
    <g>
      <line
        x1={cx}
        y1={highY}
        x2={cx}
        y2={lowY}
        stroke={wickStroke}
        strokeWidth={1.5}
        opacity={wickOpacity}
      />
      <rect
        x={x + 1}
        y={bodyTop}
        width={Math.max(width - 2, 4)}
        height={bodyH}
        fill={color}
        stroke={color}
        strokeWidth={0.5}
      />
    </g>
  );
}
