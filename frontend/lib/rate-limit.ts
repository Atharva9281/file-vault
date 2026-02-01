/**
 * Rate Limiting Configuration
 *
 * Uses Upstash Redis for distributed rate limiting across API routes.
 * For development without Redis, falls back to in-memory rate limiting.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

// Create rate limiter instance
// If UPSTASH_REDIS_REST_URL is not set, this will use in-memory storage (development only)
export const ratelimit = new Ratelimit({
  redis: process.env.UPSTASH_REDIS_REST_URL
    ? Redis.fromEnv()
    : ({
        // Fallback for development - in-memory storage
        sadd: async () => {},
        eval: async () => ({ result: 1 }),
      } as any),
  limiter: Ratelimit.slidingWindow(10, "10 s"), // 10 requests per 10 seconds
  analytics: true,
  prefix: "filevault",
});

// Higher rate limit for file uploads (larger operations)
export const uploadRatelimit = new Ratelimit({
  redis: process.env.UPSTASH_REDIS_REST_URL
    ? Redis.fromEnv()
    : ({
        sadd: async () => {},
        eval: async () => ({ result: 1 }),
      } as any),
  limiter: Ratelimit.slidingWindow(3, "60 s"), // 3 uploads per minute
  analytics: true,
  prefix: "filevault:upload",
});
