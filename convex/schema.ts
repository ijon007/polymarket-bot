import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  trades: defineTable({
    market_ticker: v.string(),
    condition_id: v.string(),
    question: v.string(),
    strategy: v.string(),
    action: v.string(),
    side: v.string(),
    price: v.optional(v.number()),
    yes_price: v.optional(v.number()),
    no_price: v.optional(v.number()),
    position_size: v.number(),
    size: v.number(),
    expected_profit: v.number(),
    confidence: v.number(),
    reason: v.string(),
    executed_at: v.number(),
    status: v.string(),
    market_outcome: v.optional(v.string()),
    actual_profit: v.optional(v.number()),
    settled_at: v.optional(v.number()),
  })
    .index("by_market_ticker", ["market_ticker"])
    .index("by_status", ["status"])
    .index("by_market_ticker_status", ["market_ticker", "status"]),

  market_outcomes: defineTable({
    slug: v.string(),
    condition_id: v.string(),
    outcome: v.string(),
    resolved_at: v.number(),
    btc_start_price: v.optional(v.number()),
    btc_end_price: v.optional(v.number()),
  }).index("by_slug", ["slug"]),
});
