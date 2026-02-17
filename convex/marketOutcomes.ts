import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const insert = mutation({
  args: {
    slug: v.string(),
    condition_id: v.string(),
    outcome: v.string(),
    resolved_at: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("market_outcomes", args);
  },
});

export const getBySlug = query({
  args: { slug: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("market_outcomes")
      .withIndex("by_slug", (q) => q.eq("slug", args.slug))
      .first();
  },
});

/** Last N resolved 5-min BTC outcomes for momentum signal. Used by 15-min engine. */
export const listLast5mOutcomes = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 3;
    const all = await ctx.db.query("market_outcomes").collect();
    const filtered = all
      .filter((m) => m.slug.startsWith("btc-updown-5m-"))
      .sort((a, b) => b.resolved_at - a.resolved_at)
      .slice(0, limit);
    return filtered;
  },
});
