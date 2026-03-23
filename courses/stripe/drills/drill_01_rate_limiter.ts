/*
Drill 01 — Rate Limiter

Build a rate-limiting service. Given a stream of requests identified
by client ID and timestamp, decide whether to allow or deny each one.

Commonly reported Stripe Programming Exercise pattern.

Target time: 30 minutes for all 3 parts.

────────────────────────────────────
Part 1 — Fixed Window (10 min)

  Build a RateLimiter class.

  constructor(maxRequests: number, windowMs: number)
  allow(clientId: string, timestamp: number): boolean

  Windows are aligned to multiples of windowMs.
  Each client gets up to maxRequests per window.

  Example (maxRequests=3, windowMs=1000):
    rl.allow("u1", 0)    → true   // 1st in window [0..999]
    rl.allow("u1", 100)  → true   // 2nd
    rl.allow("u1", 200)  → true   // 3rd
    rl.allow("u1", 300)  → false  // exceeded limit
    rl.allow("u1", 1000) → true   // new window [1000..1999]
    rl.allow("u2", 300)  → true   // separate client

────────────────────────────────────
Part 2 — Sliding Window (10 min)

  allowSliding(clientId: string, timestamp: number): boolean

  Instead of aligned windows, count requests in the trailing
  interval (timestamp - windowMs, timestamp]. More accurate
  than fixed windows.

  Example (maxRequests=3, windowMs=1000):
    rl.allowSliding("u1", 100)  → true
    rl.allowSliding("u1", 500)  → true
    rl.allowSliding("u1", 900)  → true
    rl.allowSliding("u1", 950)  → false  // 3 requests in (0, 950]
    rl.allowSliding("u1", 1100) → true   // request at t=100 expired

────────────────────────────────────
Part 3 — Token Bucket (10 min)

  createBucket(clientId: string, capacity: number, refillRate: number): void
  allowBucket(clientId: string, timestamp: number, tokens?: number): boolean

  capacity = max tokens. refillRate = tokens added per second.
  Bucket starts full. Before checking, refill based on elapsed
  time since last access (capped at capacity). Consume tokens
  (default 1), return false if insufficient.

  Example (capacity=5, refill=2 tokens/sec):
    rl.createBucket("u1", 5, 2)
    rl.allowBucket("u1", 0)         → true   // 4 left
    // ... consume all 5 ...
    rl.allowBucket("u1", 0)         → false  // empty
    rl.allowBucket("u1", 1000)      → true   // 2 refilled after 1s
    rl.allowBucket("u1", 11000, 3)  → true   // full (capped), consume 3
*/

export class RateLimiter {
  requestsFixed: Map<string, { count: number, window: number }>;
  requestsSliding: Map<string, number[]>;
  requestsBucket: Map<string, { cap: number, tokens: number, lastAccess: number, fillRate: number }>;
  maxRequests: number;
  windowMS: number;
  constructor(maxRequests: number, windowMs: number) {
    this.requestsFixed = new Map();
    this.requestsSliding = new Map();
    this.requestsBucket = new Map();
    this.maxRequests = maxRequests;
    this.windowMS = windowMs;
  }
  // REVIEW: Constructor pre-allocates all three Maps even though
  // Parts 2 and 3 don't exist yet. In an interview, only declare what
  // you need now. Add new state when the interviewer reveals the next
  // part. This also avoids the interviewer wondering what you're
  // planning to use three Maps for.
  //
  // Speed tip: use TypeScript shorthand to skip the manual assignments:
  //   constructor(private maxRequests: number, private windowMs: number) {}
  // Then add Maps as needed per part. Saves ~6 lines of boilerplate.

  // Part 1
  allow(clientId: string, timestamp: number): boolean {
    const client = this.requestsFixed.get(clientId);
    const window = Math.floor(timestamp / this.windowMS);
    if (!client || client.window !== window) {
      this.requestsFixed.set(clientId, { count: 1, window });
      return true;
    }
    if (client.count >= this.maxRequests) return false;
    this.requestsFixed.set(clientId, { count: client.count + 1, window });
    return true;
  }
  // REVIEW: Correct and clean. Two small speed wins:
  //
  // 1. Mutate instead of re-creating the object on line 89:
  //      client.count++;
  //    You already have a reference to the object in the Map — no need
  //    to .set() a new one. Saves a line and avoids GC churn.
  //
  // 2. Combine the "not found" and "new window" branches. They do the
  //    same thing (reset to count 1). Your current code already handles
  //    this — good instinct.

  // Part 2
  allowSliding(clientId: string, timestamp: number): boolean {
    const client = this.requestsSliding.get(clientId);
    if (!client) {
      this.requestsSliding.set(clientId, [timestamp]);
      return true;
    }
    while (client.length && client[0] <= timestamp - this.windowMS) {
      client.shift();
    }
    if (client.length >= this.maxRequests) {
      return false
    }
    client.push(timestamp);
    return true;
  }
  // REVIEW: Correct. The early return for !client on line 96 means
  // you skip the eviction loop on the first call. That's fine but
  // adds a code path. Simpler alternative: always initialize with
  // an empty array so you never need the special case:
  //
  //   allowSliding(clientId, timestamp) {
  //     if (!this.requestsSliding.has(clientId)) this.requestsSliding.set(clientId, []);
  //     const ts = this.requestsSliding.get(clientId)!;
  //     while (ts.length && ts[0] <= timestamp - this.windowMS) ts.shift();
  //     if (ts.length >= this.maxRequests) return false;
  //     ts.push(timestamp);
  //     return true;
  //   }
  //
  // One path instead of two. Fewer branches = fewer bugs under pressure.

  // Part 3
  createBucket(clientId: string, capacity: number, refillRate: number): void {
    this.requestsBucket.set(clientId, {
      cap: capacity,
      tokens: capacity,
      lastAccess: 0,
      fillRate: refillRate,
    });
  }
  allowBucket(clientId: string, timestamp: number, tokens?: number): boolean {
    const client = this.requestsBucket.get(clientId)!;
    const elapsedSeconds = Math.floor((timestamp - client.lastAccess) / 1000);
    let newTokens = client.tokens + (client.fillRate * elapsedSeconds);
    if (newTokens > client.cap) newTokens = client.cap;
    if (newTokens < (tokens || 1)) {
      return false;
    }
    newTokens -= (tokens || 1);
    client.tokens = newTokens;
    client.lastAccess = timestamp;
    return true;
  }
  // REVIEW: Two issues:
  //
  // 1. Math.floor on elapsed seconds (line 121) drops fractional
  //    refills. If fillRate=2 and 1.5s passes, you get 2 tokens
  //    instead of 3. Remove Math.floor — keep fractional precision:
  //      const elapsed = (timestamp - client.lastAccess) / 1000;
  //      let newTokens = client.tokens + client.fillRate * elapsed;
  //    The cap clamp handles overflow. No rounding needed.
  //
  // 2. `tokens || 1` (lines 124, 127) — if someone passes tokens=0,
  //    this evaluates to 1. Use `tokens ?? 1` for a correct nullish
  //    default. Not tested here but an interviewer might notice.
  //
  // Speed tip: the refill + clamp + consume pattern is 4 lines.
  // Write it as a straight sequence, no branching:
  //   const elapsed = (timestamp - client.lastAccess) / 1000;
  //   client.tokens = Math.min(client.cap, client.tokens + client.fillRate * elapsed);
  //   client.lastAccess = timestamp;
  //   const cost = tokens ?? 1;
  //   if (client.tokens < cost) return false;
  //   client.tokens -= cost;
  //   return true;
  //
  // Always update lastAccess and tokens in one place — no separate
  // "return false" path that skips the update. That's what caused the
  // original missing-lastAccess bug.
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

function part(name: string, fn: () => void): void {
  console.log(name);
  try {
    fn();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.startsWith("TODO") || msg.includes("is not a function")) {
      console.log(`  ○ not yet implemented`);
    } else {
      _failed++;
      console.log(`  ✗ ${msg}`);
    }
  }
}

function runSelfChecks(): void {
  part("Part 1 — Fixed Window", () => {
    const rl = new RateLimiter(3, 1000);
    check("allow 1", rl.allow("u1", 0), true);
    check("allow 2", rl.allow("u1", 100), true);
    check("allow 3", rl.allow("u1", 200), true);
    check("deny 4", rl.allow("u1", 300), false);
    check("new window", rl.allow("u1", 1000), true);
    check("other client", rl.allow("u2", 300), true);
  });

  part("Part 2 — Sliding Window", () => {
    const rl = new RateLimiter(3, 1000);
    check("slide allow 1", rl.allowSliding("u1", 100), true);
    check("slide allow 2", rl.allowSliding("u1", 500), true);
    check("slide allow 3", rl.allowSliding("u1", 900), true);
    check("slide deny 4", rl.allowSliding("u1", 950), false);
    check("slide after expire", rl.allowSliding("u1", 1100), true);
  });

  part("Part 3 — Token Bucket", () => {
    const rl = new RateLimiter(10, 1000);
    rl.createBucket("u1", 5, 2);
    check("bucket allow 1", rl.allowBucket("u1", 0), true);
    rl.allowBucket("u1", 0);
    rl.allowBucket("u1", 0);
    rl.allowBucket("u1", 0);
    check("bucket allow last", rl.allowBucket("u1", 0), true);
    check("bucket deny empty", rl.allowBucket("u1", 0), false);
    check("bucket after refill", rl.allowBucket("u1", 1000), true);
    check("bucket capped", rl.allowBucket("u1", 11000, 3), true);
    check("bucket insufficient", rl.allowBucket("u1", 11000, 3), false);
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
