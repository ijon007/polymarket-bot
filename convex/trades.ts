import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const tradeInsertArgs = {
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
};

export const insert = mutation({
  args: tradeInsertArgs,
  handler: async (ctx, args) => {
    return await ctx.db.insert("trades", args);
  },
});

export const updateSettlement = mutation({
  args: {
    tradeId: v.id("trades"),
    market_outcome: v.string(),
    actual_profit: v.number(),
    status: v.string(),
    settled_at: v.number(),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.tradeId, {
      market_outcome: args.market_outcome,
      actual_profit: args.actual_profit,
      status: args.status,
      settled_at: args.settled_at,
    });
  },
});

export const hasOpenForMarket = query({
  args: { slug: v.string() },
  handler: async (ctx, args) => {
    const found = await ctx.db
      .query("trades")
      .withIndex("by_market_ticker_status", (q) =>
        q.eq("market_ticker", args.slug).eq("status", "paper")
      )
      .first();
    return found !== null;
  },
});

export const listUnsettled = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "paper"))
      .collect();
  },
});

export const listSettled = query({
  args: {},
  handler: async (ctx) => {
    const won = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "won"))
      .collect();
    const lost = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "lost"))
      .collect();
    const all = [...won, ...lost];
    all.sort((a, b) => (b.settled_at ?? 0) - (a.settled_at ?? 0));
    return all;
  },
});

export const settledPnLSum = query({
  args: {},
  handler: async (ctx) => {
    const won = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "won"))
      .collect();
    const lost = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "lost"))
      .collect();
    let sum = 0;
    for (const t of [...won, ...lost]) {
      if (t.actual_profit != null) sum += t.actual_profit;
    }
    return sum;
  },
});

export const dashboardAnalytics = query({
  args: {},
  handler: async (ctx) => {
    const [paper, won, lost] = await Promise.all([
      ctx.db.query("trades").withIndex("by_status", (q) => q.eq("status", "paper")).collect(),
      ctx.db.query("trades").withIndex("by_status", (q) => q.eq("status", "won")).collect(),
      ctx.db.query("trades").withIndex("by_status", (q) => q.eq("status", "lost")).collect(),
    ]);
    const settled = [...won, ...lost];
    let totalPnl = 0;
    let bestTrade = 0;
    let worstTrade = 0;
    for (const t of settled) {
      const p = t.actual_profit ?? 0;
      totalPnl += p;
      if (p > bestTrade) bestTrade = p;
      if (p < worstTrade) worstTrade = p;
    }
    return {
      totalTrades: paper.length + settled.length,
      settled: settled.length,
      pending: paper.length,
      totalPnl,
      bestTrade,
      worstTrade,
      wonCount: won.length,
      lostCount: lost.length,
    };
  },
});

export const dashboardSettledForStreak = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 40;
    const won = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "won"))
      .collect();
    const lost = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "lost"))
      .collect();
    const all = [...won, ...lost];
    all.sort((a, b) => (b.settled_at ?? 0) - (a.settled_at ?? 0));
    return all.slice(0, limit);
  },
});

export const listForDashboard = query({
  args: {},
  handler: async (ctx) => {
    const [paper, won, lost] = await Promise.all([
      ctx.db.query("trades").withIndex("by_status", (q) => q.eq("status", "paper")).collect(),
      ctx.db.query("trades").withIndex("by_status", (q) => q.eq("status", "won")).collect(),
      ctx.db.query("trades").withIndex("by_status", (q) => q.eq("status", "lost")).collect(),
    ]);
    const all = [...paper, ...won, ...lost];
    all.sort((a, b) => (b.executed_at ?? 0) - (a.executed_at ?? 0));
    return all;
  },
});

export const dashboardTodayPnl = query({
  args: {},
  handler: async (ctx) => {
    const now = Date.now() / 1000;
    const dayAgo = now - 24 * 60 * 60;
    const won = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "won"))
      .collect();
    const lost = await ctx.db
      .query("trades")
      .withIndex("by_status", (q) => q.eq("status", "lost"))
      .collect();
    let sum = 0;
    for (const t of [...won, ...lost]) {
      const st = t.settled_at ?? 0;
      if (st >= dayAgo && t.actual_profit != null) sum += t.actual_profit;
    }
    return sum;
  },
});

export const schemaCheck = mutation({
  args: tradeInsertArgs,
  handler: async (ctx, args) => {
    const id = await ctx.db.insert("trades", args);
    await ctx.db.delete(id);
    return true;
  },
});
