import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const KEY = "default";

export const upsert = mutation({
  args: {
    engine_state: v.string(),
    uptime_seconds: v.number(),
    scan_interval: v.number(),
    polymarket_ok: v.boolean(),
    db_ok: v.boolean(),
    rtds_ok: v.boolean(),
  },
  handler: async (ctx, args) => {
    const now = Math.floor(Date.now() / 1000);
    const existing = await ctx.db
      .query("system_status")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .first();
    const doc = {
      key: KEY,
      engine_state: args.engine_state,
      uptime_seconds: args.uptime_seconds,
      scan_interval: args.scan_interval,
      polymarket_ok: args.polymarket_ok,
      db_ok: args.db_ok,
      rtds_ok: args.rtds_ok,
      updated_at: now,
    };
    if (existing) {
      await ctx.db.patch(existing._id, doc);
    } else {
      await ctx.db.insert("system_status", doc);
    }
  },
});

export const get = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("system_status")
      .withIndex("by_key", (q) => q.eq("key", KEY))
      .first();
  },
});
