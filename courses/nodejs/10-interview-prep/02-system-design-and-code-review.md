# 02 – System Design, Code Review, and Live Coding

## System Design Template for Node.js

**Step 1 (2 min)**: Clarify requirements — functional, non-functional (QPS, latency, availability), scale.

**Step 2 (3 min)**: High-level architecture.
```
Client → LB → API Gateway → Node.js Services → PostgreSQL / Redis → BullMQ Workers
```

**Step 3 (3 min)**: Data model — entities, read/write patterns, indexing strategy.

**Step 4 (3 min)**: API design — endpoints, auth, pagination.

**Step 5 (10 min)**: Deep dive into the hardest component. Show implementation. Discuss trade-offs.

**Step 6 (5 min)**: Scaling and reliability — horizontal scaling, caching, failure modes, monitoring.

**Node.js-specific**: Single-threaded (cluster/pods for CPU), streaming for large payloads, event-driven for real-time, worker threads for CPU tasks, BullMQ for background jobs.

---

## System Design Questions

### Design a Real-Time Collaboration System

**Architecture**: Clients connect via WebSocket to Node.js gateway. Redis Pub/Sub syncs across instances. CRDTs (Yjs/Automerge) for conflict-free concurrent editing. Presence via heartbeats with Redis TTL. Batch changes for persistence, not every keystroke. Use `ws` library for performance-critical WebSocket paths.

### Design a Rate Limiter

**Algorithm**: Sliding window counter with Redis.

```typescript
class SlidingWindowRateLimiter {
  constructor(private redis: Redis, private windowMs: number, private max: number) {}

  async isAllowed(key: string): Promise<{ allowed: boolean; remaining: number }> {
    const now = Date.now();
    const result = await this.redis.multi()
      .zremrangebyscore(key, 0, now - this.windowMs)  // Remove expired
      .zadd(key, now, `${now}-${Math.random()}`)       // Add current
      .zcard(key)                                       // Count in window
      .pexpire(key, this.windowMs)
      .exec();

    const count = result![2][1] as number;
    return { allowed: count <= this.max, remaining: Math.max(0, this.max - count) };
  }
}
```

### Design a File Processing Pipeline

**Architecture**: Presigned URL upload to S3 (never buffer in Node.js memory). BullMQ job per file. Worker streams from S3, processes row-by-row with `csv-parse`. Backpressure via `pipeline()`. Progress updates via BullMQ job progress + SSE to frontend. Collect row-level errors separately from job-level errors. Allow partial success.

### Design a Multi-Tenant SaaS API

**Data isolation**: Shared database + row-level `tenant_id` (simplest), separate schemas (moderate), separate databases (strongest). **Tenant resolution**: subdomain, header, or JWT claim. **Request context**: `AsyncLocalStorage` carries tenant through the request. **Per-tenant config**: Feature flags and rate limits in Redis. Tenant-scoped repositories add `WHERE tenant_id = ?` to every query.

### "Your API is getting 10x more traffic than expected. What do you do?"

**Immediate (within hours)**:
- Scale horizontally — add more instances/pods
- Enable response caching (Redis) for read-heavy endpoints
- Add rate limiting to protect downstream services
- Check if any endpoints are doing N+1 queries and fix the worst offenders

**Short-term (within days)**:
- Profile and optimize the top 5 slowest endpoints
- Add connection pooling if not already configured (PgBouncer)
- Implement read replicas for read-heavy queries
- Move expensive computations to background jobs (BullMQ)

**Medium-term (within weeks)**:
- Implement CQRS for endpoints with divergent read/write patterns
- Add CDN for static/semi-static responses
- Consider decomposing if specific endpoints have wildly different scaling needs
- Load test to find the new ceiling

**What interviewers want to hear**: You can triage by urgency. You start with the cheapest, highest-impact changes. You don't jump to "rewrite in microservices."

### "How do you handle a critical production bug at 2am?"

1. **Assess severity**: Is it data loss? Is it user-facing? How many users affected?
2. **Communicate**: Post in incident channel. Page the relevant on-call if it's not you.
3. **Mitigate first, fix later**: Can you feature-flag the broken code path? Revert the last deploy? Route traffic away?
4. **Debug with observability**: Logs (correlation ID), metrics (error rate spike), traces (which service/function failed)
5. **Fix and verify**: Minimal fix. Deploy to staging. Verify. Deploy to production. Monitor for 30 minutes.
6. **Post-incident**: Write a blameless postmortem within 48 hours. Focus on systemic causes: Why didn't tests catch it? Why didn't monitoring alert earlier? What process changes prevent recurrence?

---

## Code Review Red Flags Checklist

**Performance**: Sequential `await` in loops, N+1 queries, missing indexes, unbounded SELECTs, large JSON on main thread, no backpressure, new DB client per request.

**Security**: Unparameterized SQL, no rate limiting on auth, secrets in code, no CORS config, JWT in localStorage, no input validation, no security headers.

**Reliability**: Missing async error handling, silent `.catch`, no graceful shutdown, no retries on external calls, no circuit breaker, no timeouts, unbounded caches.

**Architecture**: Business logic in controllers, direct DB in presentation layer, circular deps, side effects in request path, missing transactions, `console.log`, hardcoded config.

### Exercise 1: Spot the Memory Leak

```typescript
class EventTracker {
  private listeners = new Map<string, Set<Function>>();
  track(userId: string, socket: WebSocket): void {
    const handler = (data: Buffer) => this.processData(userId, data);
    socket.on('message', handler);
    if (!this.listeners.has(userId)) this.listeners.set(userId, new Set());
    this.listeners.get(userId)!.add(handler);
  }
  // BUG: No cleanup. Handlers never removed from socket or Map.
  // On reconnect, old handlers accumulate. Fix: add untrack() with socket.off() and Map.delete().
}
```

### Exercise 2: Identify the Performance Issue

```typescript
app.get('/api/dashboard', async (req, res) => {
  const orders = await db.order.findMany({ where: { userId: req.user.id } });
  const reviews = await db.review.findMany({ where: { userId: req.user.id } });
  const recs = await mlService.getRecommendations(req.user.id);
  const notifs = await db.notification.findMany({ where: { userId: req.user.id, read: false } });
  // BUG: Four sequential awaits. Total latency = sum of all four.
  // FIX: Promise.all — these are independent. Latency = max of four.
});
```

### Exercise 3: Architectural Improvements

```typescript
app.post('/api/orders', async (req, res) => {
  if (!req.body.items?.length) return res.status(400).json({ error: 'Items required' });
  let total = 0;
  for (const item of req.body.items) {
    const product = await db.product.findUnique({ where: { id: item.productId } });
    if (!product) return res.status(404).json({ error: `Product ${item.productId} not found` });
    total += product.price * item.quantity;
    await db.product.update({ where: { id: item.productId }, data: { stock: { decrement: item.quantity } } });
  }
  const order = await db.order.create({ data: { userId: req.user.id, total, items: { create: req.body.items } } });
  await emailService.sendConfirmation(req.user.email, order);
  console.log('Order created');
  res.status(201).json(order);
});
// Issues: (1) No Zod validation (2) Business logic in controller (3) N+1 queries
// (4) No transaction — stock decrement + order create should be atomic
// (5) Email in request path — use queue (6) console.log instead of structured logger
// (7) Race condition on stock check (8) Generic error handling
```

---

## Live Coding Patterns

### Live Coding Setup Template

```bash
mkdir interview-problem && cd interview-problem
npm init -y && npm install typescript @types/node tsx
npx tsc --init --target ES2022 --module NodeNext --moduleResolution NodeNext --strict
```

```typescript
// solution.ts — starter template
import { randomUUID } from 'node:crypto';

interface Config { /* ... */ }

class Solution {
  constructor(private readonly config: Config) {}
  async execute(): Promise<void> { /* ... */ }
}

async function main() {
  const solution = new Solution({ /* config */ });
  await solution.execute();
}
main().catch(console.error);
// Run: npx tsx solution.ts
```

**Patterns to have ready**: Middleware chain (`next()` callback composition), circuit breaker (CLOSED/OPEN/HALF_OPEN states), job queue (concurrency limiter + exponential backoff), cursor pagination (base64 cursor, fetch limit+1), LRU cache (Map insertion order trick).

### Build a Middleware Chain

```typescript
type Middleware = (ctx: Context, next: () => Promise<void>) => Promise<void>;

class MiddlewareChain {
  private middlewares: Middleware[] = [];
  use(mw: Middleware): this { this.middlewares.push(mw); return this; }

  async execute(ctx: Context): Promise<void> {
    let index = 0;
    const next = async (): Promise<void> => {
      if (index >= this.middlewares.length) return;
      const mw = this.middlewares[index++];
      await mw(ctx, next);
    };
    await next();
  }
}
```

### Implement a Circuit Breaker

```typescript
class CircuitBreaker {
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private failureCount = 0;
  private lastFailureTime = 0;
  private successCount = 0;

  constructor(private opts: { failureThreshold: number; resetTimeout: number; successThreshold: number }) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime >= this.opts.resetTimeout) {
        this.state = 'HALF_OPEN';
        this.successCount = 0;
      } else throw new Error('Circuit is open');
    }
    try {
      const result = await fn();
      if (this.state === 'HALF_OPEN' && ++this.successCount >= this.opts.successThreshold)
        this.state = 'CLOSED';
      this.failureCount = 0;
      return result;
    } catch (err) {
      this.lastFailureTime = Date.now();
      if (++this.failureCount >= this.opts.failureThreshold) this.state = 'OPEN';
      throw err;
    }
  }
}
```

### Build a Job Queue

```typescript
class SimpleJobQueue<T> {
  private queue: Array<{ id: string; data: T; attempts: number; maxAttempts: number; status: string }> = [];
  private activeCount = 0;

  constructor(private handler: (data: T) => Promise<void>, private concurrency = 1) {}

  add(data: T, maxAttempts = 3): string {
    const id = randomUUID();
    this.queue.push({ id, data, attempts: 0, maxAttempts, status: 'pending' });
    this.process();
    return id;
  }

  private async process(): Promise<void> {
    while (this.activeCount < this.concurrency) {
      const job = this.queue.find(j => j.status === 'pending');
      if (!job) break;
      this.activeCount++;
      job.status = 'processing';
      job.attempts++;
      try {
        await this.handler(job.data);
        job.status = 'completed';
      } catch {
        job.status = job.attempts < job.maxAttempts ? 'pending' : 'failed';
        if (job.status === 'pending') setTimeout(() => this.process(), 2 ** job.attempts * 1000);
      }
      this.activeCount--;
    }
  }
}
```

### Implement Cursor Pagination

```typescript
interface PaginationResult<T> {
  data: T[];
  pageInfo: {
    hasNextPage: boolean;
    hasPreviousPage: boolean;
    endCursor: string | null;
  };
}

async function paginate<T extends { id: string; createdAt: Date }>(
  cursor: string | undefined, limit: number,
  query: (where: any, take: number) => Promise<T[]>,
): Promise<PaginationResult<T>> {
  const decoded = cursor ? JSON.parse(Buffer.from(cursor, 'base64url').toString()) : null;

  // Compound cursor: sort by createdAt DESC, break ties with id DESC
  const where = decoded
    ? { OR: [
        { createdAt: { lt: new Date(decoded.createdAt) } },
        { createdAt: new Date(decoded.createdAt), id: { lt: decoded.id } },
      ]}
    : {};

  // Fetch one extra row to determine if there's a next page
  const rows = await query(where, limit + 1);
  const hasMore = rows.length > limit;
  const data = hasMore ? rows.slice(0, limit) : rows;

  const encode = (item: T) =>
    Buffer.from(JSON.stringify({ id: item.id, createdAt: item.createdAt.toISOString() })).toString('base64url');

  return {
    data,
    pageInfo: {
      hasNextPage: hasMore,
      hasPreviousPage: !!cursor,
      endCursor: data.length > 0 ? encode(data[data.length - 1]) : null,
    },
  };
}
```

**Why cursor over offset**: Offset pagination breaks when rows are inserted/deleted between pages. Cursor pagination is stable — it always picks up where it left off. Use compound cursors (timestamp + ID) to handle duplicate timestamps.

### Implement an LRU Cache

```typescript
class LRUCache<K, V> {
  private cache = new Map<K, V>();

  constructor(private readonly maxSize: number) {}

  get(key: K): V | undefined {
    const value = this.cache.get(key);
    if (value !== undefined) {
      // Move to end (most recently used)
      this.cache.delete(key);
      this.cache.set(key, value);
    }
    return value;
  }

  set(key: K, value: V): void {
    this.cache.delete(key); // Remove if exists (to update position)
    this.cache.set(key, value);
    if (this.cache.size > this.maxSize) {
      // Delete the least recently used (first entry in Map)
      const oldest = this.cache.keys().next().value!;
      this.cache.delete(oldest);
    }
  }

  get size(): number { return this.cache.size; }
}
```

**Why this works**: JavaScript `Map` maintains insertion order. `delete` + `set` moves an entry to the end. The first entry is always the least recently used.

---

## Tricky Edge Cases and Gotchas

### Node.js Gotchas

**1. `JSON.parse` of large payloads blocks the event loop**
Parsing a 50MB JSON string can block for 500ms+. Use streaming JSON parsers (`stream-json`) or move parsing to a worker thread.

**2. `Date` constructor timezone behavior**
```typescript
new Date('2024-01-15');          // Interpreted as UTC (midnight UTC)
new Date('2024-01-15T00:00:00'); // Interpreted as LOCAL timezone
// These are different dates if you're not in UTC
```

**3. `parseInt` with radix**
```typescript
parseInt('08');      // 8 (modern engines) but historically 0 (octal)
parseInt('0x10');    // 16 (hex prefix detected)
parseInt('10', 2);   // 2 (binary)
// Always pass the radix: parseInt(str, 10)
```

**4. `Promise.all` fails fast**
```typescript
// If any promise rejects, ALL results are lost
await Promise.all([fetchA(), fetchB(), fetchC()]);
// If fetchB rejects, you don't get fetchA and fetchC results

// Use Promise.allSettled to get all results regardless
const results = await Promise.allSettled([fetchA(), fetchB(), fetchC()]);
const successes = results.filter(r => r.status === 'fulfilled').map(r => r.value);
const failures = results.filter(r => r.status === 'rejected').map(r => r.reason);
```

**5. `EventEmitter` max listeners warning**
```typescript
// Default is 10 listeners per event. Exceeding it prints a warning (not an error).
// This is usually a leak, but sometimes intentional.
emitter.setMaxListeners(50); // Increase if intentional
```

**6. `Buffer.from` encoding confusion**
```typescript
Buffer.from('hello');              // UTF-8 (default)
Buffer.from('68656c6c6f', 'hex');  // Hex string → Buffer
Buffer.from('aGVsbG8=', 'base64'); // Base64 → Buffer

// Gotcha: Buffer.from(number) was removed — use Buffer.alloc(number)
```

**7. `setImmediate` vs `setTimeout(fn, 0)` ordering**
```typescript
// Outside I/O callback: order is NON-DETERMINISTIC
setTimeout(() => console.log('timeout'), 0);
setImmediate(() => console.log('immediate'));
// Could print in either order

// Inside I/O callback: setImmediate always fires first
fs.readFile('file.txt', () => {
  setTimeout(() => console.log('timeout'), 0);
  setImmediate(() => console.log('immediate'));
  // Always prints: immediate, timeout
});
```

### TypeScript Gotchas

**8. Object spread doesn't call setters**
```typescript
class Config {
  private _port = 3000;
  set port(value: number) {
    if (value < 0 || value > 65535) throw new Error('Invalid port');
    this._port = value;
  }
}

const config = new Config();
Object.assign(config, { port: -1 }); // Calls setter — throws
const config2 = { ...config, port: -1 }; // Spread — creates plain object, no setter
```

**9. Enum values can collide with reverse mapping**
```typescript
enum Status { Active = 0, Inactive = 1 }
Status[0]; // 'Active' — reverse mapping exists for numeric enums
// This means Object.keys(Status) returns ['0', '1', 'Active', 'Inactive']
// Use const enums or string enums to avoid this
```

**10. `readonly` is shallow**
```typescript
interface User {
  readonly name: string;
  readonly addresses: string[];
}

const user: User = { name: 'Alice', addresses: ['123 Main St'] };
user.name = 'Bob';           // Error — readonly
user.addresses.push('456 Oak'); // OK — readonly doesn't protect array contents
// Use ReadonlyArray<string> or readonly string[] for deep immutability
```

**11. Structural typing allows unexpected values**
```typescript
interface Point { x: number; y: number; }
interface Point3D { x: number; y: number; z: number; }

function distance(p: Point): number { return Math.sqrt(p.x ** 2 + p.y ** 2); }

const p3d: Point3D = { x: 1, y: 2, z: 3 };
distance(p3d); // OK — Point3D is structurally compatible with Point
```

**12. `typeof` in type position vs value position**
```typescript
const config = { port: 3000, host: 'localhost' };

typeof config;               // Value position: 'object' (JavaScript)
type Config = typeof config; // Type position: { port: number; host: string } (TypeScript)
```

**13. Assertion functions don't work with arrow functions**
```typescript
// This works
function assertString(value: unknown): asserts value is string {
  if (typeof value !== 'string') throw new Error('Not a string');
}

// This does NOT work — arrow functions can't be assertion functions
const assertString2 = (value: unknown): asserts value is string => {
  if (typeof value !== 'string') throw new Error('Not a string');
};
```

### Production Gotchas

**14. Connection pool exhaustion**
```typescript
// Each request creates a new PrismaClient — connection pool per request
app.get('/users', async (req, res) => {
  const prisma = new PrismaClient(); // BUG: new pool per request
  const users = await prisma.user.findMany();
  res.json(users);
  // Connection never closed — pool grows until DB rejects connections
});

// Fix: single PrismaClient instance shared across the application
```

**15. Unbounded cache growth**
```typescript
// This Map grows forever — no eviction
const cache = new Map<string, CachedResponse>();

app.get('/api/:id', async (req, res) => {
  if (cache.has(req.params.id)) return res.json(cache.get(req.params.id));
  const data = await fetchExpensiveData(req.params.id);
  cache.set(req.params.id, data); // Memory leak
  res.json(data);
});

// Fix: Use LRU cache with max size and TTL
import { LRUCache } from 'lru-cache';
const cache = new LRUCache<string, CachedResponse>({ max: 10_000, ttl: 300_000 });
```

**16. Missing `await` on database operations**
```typescript
app.post('/orders', async (req, res) => {
  const order = await orderService.create(req.body);
  // Missing await — fire-and-forget, errors silently swallowed
  auditService.logOrderCreated(order.id);
  // Fix: await auditService.logOrderCreated(order.id);
  // Or explicitly handle: auditService.logOrderCreated(order.id).catch(err => logger.error(err));
  res.status(201).json(order);
});
```

**17. Race conditions in concurrent requests**
```typescript
// Two concurrent requests for the same user
app.post('/transfer', async (req, res) => {
  const account = await db.account.findUnique({ where: { id: req.body.accountId } });
  if (account.balance < req.body.amount) return res.status(400).json({ error: 'Insufficient funds' });

  // Between the check above and the update below, another request could have reduced the balance
  await db.account.update({
    where: { id: req.body.accountId },
    data: { balance: { decrement: req.body.amount } },
  });

  // Fix: Use database-level locking or atomic operations
  // UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1
});
```

**18. Error swallowing in `.catch` chains**: `.catch(err => console.log(err))` logs but continues as if nothing happened. Callers think the operation succeeded. Fix: re-throw after logging, or return a Result type.
