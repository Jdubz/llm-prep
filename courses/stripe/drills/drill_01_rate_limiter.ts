/*
Drill 01 — Rate Limiter

Build a RateLimiter service. This is a commonly reported Stripe
Programming Exercise pattern. Focus on clean design, speed of
implementation, and handling edge cases.

Target time: 35 minutes for all 4 levels.

────────────────────────────────────────
Level 1 — Fixed Window

  constructor(maxRequests: number, windowMs: number)

  allow(clientId: string, timestamp: number): boolean
    Returns true if the request is allowed, false if rate-limited.
    Each client gets maxRequests per window.
    Windows are aligned to multiples of windowMs
    (e.g., windowMs=1000 → windows are [0,999], [1000,1999], ...).

  getRemaining(clientId: string, timestamp: number): number
    Returns how many requests the client has left in the current window.

────────────────────────────────────────
Level 2 — Sliding Window Log

  allowSliding(clientId: string, timestamp: number): boolean
    Uses a sliding window: count requests in [timestamp - windowMs, timestamp).
    More accurate than fixed window but uses more memory.

  getRequestCount(clientId: string, timestamp: number): number
    Returns the number of requests in the current sliding window.

────────────────────────────────────────
Level 3 — Multi-Tier Limits

  addTier(name: string, maxRequests: number, windowMs: number): void
    Add a named rate limit tier. All tiers must pass for a request
    to be allowed. Example: 10/second AND 100/minute AND 1000/hour.

  allowTiered(clientId: string, timestamp: number): boolean
    Returns true only if ALL tiers allow the request.
    Uses sliding window logic per tier.

  getBlockingTier(clientId: string, timestamp: number): string | null
    Returns the name of the first tier that would block the request,
    or null if all tiers would allow it.

────────────────────────────────────────
Level 4 — Token Bucket

  createBucket(clientId: string, capacity: number, refillRate: number): void
    Create a token bucket for the client.
    capacity: max tokens. refillRate: tokens added per second.
    Bucket starts full.

  allowBucket(clientId: string, timestamp: number, tokens?: number): boolean
    Consume tokens (default 1) from the bucket.
    Before checking, refill based on elapsed time since last request.
    Returns false if not enough tokens available.

  getBucketState(clientId: string, timestamp: number): { tokens: number; capacity: number }
    Returns current token count (after refill) and capacity.
*/

export class RateLimiter {
  constructor(maxRequests: number, windowMs: number) {
    throw new Error("TODO: implement constructor");
  }

  // Level 1
  allow(clientId: string, timestamp: number): boolean {
    throw new Error("TODO: implement allow");
  }

  getRemaining(clientId: string, timestamp: number): number {
    throw new Error("TODO: implement getRemaining");
  }

  // Level 2
  allowSliding(clientId: string, timestamp: number): boolean {
    throw new Error("TODO: implement allowSliding");
  }

  getRequestCount(clientId: string, timestamp: number): number {
    throw new Error("TODO: implement getRequestCount");
  }

  // Level 3
  addTier(name: string, maxRequests: number, windowMs: number): void {
    throw new Error("TODO: implement addTier");
  }

  allowTiered(clientId: string, timestamp: number): boolean {
    throw new Error("TODO: implement allowTiered");
  }

  getBlockingTier(clientId: string, timestamp: number): string | null {
    throw new Error("TODO: implement getBlockingTier");
  }

  // Level 4
  createBucket(clientId: string, capacity: number, refillRate: number): void {
    throw new Error("TODO: implement createBucket");
  }

  allowBucket(clientId: string, timestamp: number, tokens: number = 1): boolean {
    throw new Error("TODO: implement allowBucket");
  }

  getBucketState(clientId: string, timestamp: number): { tokens: number; capacity: number } {
    throw new Error("TODO: implement getBucketState");
  }
}

// ─── Self-Checks (do not edit below this line) ──────────────────

let _passed = 0;
let _failed = 0;

function check(label: string, actual: unknown, expected: unknown): void {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (Object.is(actual, expected) || a === e) {
    _passed++;
    console.log(`  ✓ ${label}`);
  } else {
    _failed++;
    console.log(`  ✗ ${label}`);
    console.log(`    expected: ${e}`);
    console.log(`         got: ${a}`);
  }
}

function level(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO:")) {
      console.log(`  ○ ${msg}`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  level("Level 1 — Fixed Window", () => {
    const rl = new RateLimiter(3, 1000);
    check("allow 1", rl.allow("u1", 0), true);
    check("allow 2", rl.allow("u1", 100), true);
    check("allow 3", rl.allow("u1", 200), true);
    check("deny 4", rl.allow("u1", 300), false);
    check("remaining 0", rl.getRemaining("u1", 300), 0);
    // New window
    check("new window", rl.allow("u1", 1000), true);
    check("remaining after 1", rl.getRemaining("u1", 1000), 2);
    // Different client unaffected
    check("other client", rl.allow("u2", 300), true);
    check("other remaining", rl.getRemaining("u2", 300), 2);
    // New client has full quota
    check("fresh client remaining", rl.getRemaining("u3", 0), 3);
  });

  level("Level 2 — Sliding Window", () => {
    const rl = new RateLimiter(3, 1000);
    check("slide allow 1", rl.allowSliding("u1", 100), true);
    check("slide allow 2", rl.allowSliding("u1", 500), true);
    check("slide allow 3", rl.allowSliding("u1", 900), true);
    check("slide deny 4", rl.allowSliding("u1", 950), false);
    check("count", rl.getRequestCount("u1", 950), 3);
    // At 1100, the request at 100 has expired
    check("slide after expire", rl.allowSliding("u1", 1100), true);
    check("count after expire", rl.getRequestCount("u1", 1100), 3);
    // At 1500, requests at 500 expired
    check("slide 1500", rl.allowSliding("u1", 1500), true);
    check("count 1500", rl.getRequestCount("u1", 1500), 3);
  });

  level("Level 3 — Multi-Tier Limits", () => {
    const rl = new RateLimiter(100, 60000); // base doesn't matter for tiered
    rl.addTier("second", 2, 1000);
    rl.addTier("minute", 5, 60000);
    // 2 per second, 5 per minute
    check("tier allow 1", rl.allowTiered("u1", 0), true);
    check("tier allow 2", rl.allowTiered("u1", 100), true);
    check("tier deny per-sec", rl.allowTiered("u1", 200), false);
    check("blocking tier", rl.getBlockingTier("u1", 200), "second");
    // New second
    check("tier allow 3", rl.allowTiered("u1", 1000), true);
    check("tier allow 4", rl.allowTiered("u1", 1100), true);
    // At 2000: 4 requests used in minute window, second window clear
    check("tier allow 5", rl.allowTiered("u1", 2000), true);
    // Now at 5 in the minute — minute tier blocks
    check("tier deny per-min", rl.allowTiered("u1", 2100), false);
    check("blocking minute", rl.getBlockingTier("u1", 2100), "minute");
    // No blocking tier for different client
    check("no blocking", rl.getBlockingTier("u2", 0), null);
  });

  level("Level 4 — Token Bucket", () => {
    const rl = new RateLimiter(10, 1000); // base doesn't matter for bucket
    rl.createBucket("u1", 5, 2); // 5 capacity, 2 tokens/sec, starts full
    check("bucket state", rl.getBucketState("u1", 0), { tokens: 5, capacity: 5 });
    check("bucket allow 1", rl.allowBucket("u1", 0), true);
    check("bucket state after", rl.getBucketState("u1", 0), { tokens: 4, capacity: 5 });
    // Consume 3 more
    rl.allowBucket("u1", 0);
    rl.allowBucket("u1", 0);
    rl.allowBucket("u1", 0);
    check("bucket state 1 left", rl.getBucketState("u1", 0), { tokens: 1, capacity: 5 });
    // Consume last
    check("bucket allow last", rl.allowBucket("u1", 0), true);
    check("bucket deny empty", rl.allowBucket("u1", 0), false);
    // After 1 second, 2 tokens refilled
    check("bucket after refill", rl.getBucketState("u1", 1000), { tokens: 2, capacity: 5 });
    check("bucket allow refilled", rl.allowBucket("u1", 1000), true);
    // After 10 seconds, should be capped at capacity
    check("bucket capped", rl.getBucketState("u1", 11000), { tokens: 5, capacity: 5 });
    // Consume multiple tokens at once
    check("bucket multi-token", rl.allowBucket("u1", 11000, 3), true);
    check("bucket after multi", rl.getBucketState("u1", 11000), { tokens: 2, capacity: 5 });
    check("bucket multi deny", rl.allowBucket("u1", 11000, 3), false);
  });
}

function main(): void {
  console.log("\nRate Limiter\n");
  runSelfChecks();
  const total = _passed + _failed;
  console.log(`\n${_passed}/${total} passed`);
  if (_failed === 0 && total > 0) console.log("All tests passed.");
}

main();
