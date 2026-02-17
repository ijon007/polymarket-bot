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
    polymarket_order_id: v.optional(v.string()),
    transaction_hashes: v.optional(v.array(v.string())),
    signal_type: v.optional(v.string()),
    confidence_layers: v.optional(v.number()),
    market_end_time: v.optional(v.number()),
  })
    .index("by_market_ticker", ["market_ticker"])
    .index("by_status", ["status"])
    .index("by_market_ticker_status", ["market_ticker", "status"]),

  system_status: defineTable({
    key: v.string(),
    engine_state: v.string(),
    uptime_seconds: v.number(),
    scan_interval: v.number(),
    polymarket_ok: v.boolean(),
    db_ok: v.boolean(),
    rtds_ok: v.boolean(),
    updated_at: v.number(),
  }).index("by_key", ["key"]),

  market_outcomes: defineTable({
    slug: v.string(),
    condition_id: v.string(),
    outcome: v.string(),
    resolved_at: v.number(),
    btc_start_price: v.optional(v.number()),
    btc_end_price: v.optional(v.number()),
  }).index("by_slug", ["slug"]),

  log_batches: defineTable({
    createdAt: v.number(),
    entries: v.array(
      v.object({
        timestamp: v.string(),
        level: v.string(),
        message: v.string(),
      })
    ),
  }).index("by_createdAt", ["createdAt"]),
});
