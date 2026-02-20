import { cronJobs } from "convex/server";
import { internal } from "./_generated/api";

const crons = cronJobs();

crons.interval(
  "delete old log batches",
  { minutes: 10 },
  internal.logBatches.deleteOldLogBatches
);

export default crons;
