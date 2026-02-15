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
