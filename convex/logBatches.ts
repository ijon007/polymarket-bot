import { internalMutation, mutation, query } from "./_generated/server";
import { v } from "convex/values";

const LOG_RETENTION_MS = 10 * 60 * 1000; // 10 min

export const deleteOldLogBatches = internalMutation({
  args: {},
  handler: async (ctx) => {
    const cutoff = Date.now() - LOG_RETENTION_MS;
    const old = await ctx.db
      .query("log_batches")
      .withIndex("by_createdAt", (q) => q.lt("createdAt", cutoff))
      .collect();
    for (const doc of old) {
      await ctx.db.delete(doc._id);
    }
    return old.length;
  },
});

const logEntryValidator = v.object({
  timestamp: v.string(),
  level: v.string(),
  message: v.string(),
});

export const insertBatch = mutation({
  args: {
    entries: v.array(logEntryValidator),
  },
  handler: async (ctx, args) => {
    const capped = args.entries.slice(0, 100);
    if (capped.length === 0) return null;
    return await ctx.db.insert("log_batches", {
      createdAt: Date.now(),
      entries: capped,
    });
  },
});

export const listRecent = query({
  args: {},
  handler: async (ctx) => {
    const cutoff = Date.now() - LOG_RETENTION_MS;
    return await ctx.db
      .query("log_batches")
      .withIndex("by_createdAt", (q) => q.gte("createdAt", cutoff))
      .order("asc")
      .collect();
  },
});
