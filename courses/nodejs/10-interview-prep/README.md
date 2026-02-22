# Module 10: Interview Prep

> This is the capstone. Everything from modules 01-09 converges here into the formats you'll actually encounter: rapid-fire Q&A, system design sessions, code review exercises, and live coding. If you only have 2 hours before an interview, read this module.

---

## Table of Contents

- [Expert-Level TypeScript Questions](#expert-level-typescript-questions)
- [Expert-Level Node.js Questions](#expert-level-nodejs-questions)
- [System Design Questions](#system-design-questions)
- [Code Review Exercises](#code-review-exercises)
- [Live Coding Patterns](#live-coding-patterns)

---

## Expert-Level TypeScript Questions

### Q1: Covariance and contravariance in TypeScript?

Arrays are **covariant** (`Dog[]` assignable to `Animal[]`). Function parameters are **contravariant** under `strictFunctionTypes` (a function expecting `Animal` is NOT assignable to one expecting `Dog`).

```typescript
type Handler<T> = (arg: T) => void;
const handleDog: Handler<Dog> = (d) => console.log(d.breed);
const h: Handler<Animal> = handleDog; // Error with strictFunctionTypes
```

Without `strictFunctionTypes`, method parameters are bivariant. Always enable this flag.

### Q2: `type` vs `interface` — when does it matter?

`interface` supports declaration merging (augmenting third-party types). `type` supports unions, mapped types, and conditional types. `interface extends` gives better error messages than `type &`. Use `interface` for public API contracts, `type` for computed/complex types.

### Q3: How does `infer` work in conditional types?

Declares a type variable that the compiler infers from the matched position.

```typescript
type ReturnOf<T> = T extends (...args: any[]) => infer R ? R : never;
type Awaited<T> = T extends Promise<infer U> ? Awaited<U> : T;
type FirstArg<T> = T extends (first: infer F, ...rest: any[]) => any ? F : never;
```

### Q4: `moduleResolution: "bundler"` vs `"node16"`?

`node16`: requires file extensions in imports, respects `exports` field, differentiates `.mts`/`.cts`. For code consumed directly by Node.js. `bundler`: no extensions needed, follows bundler conventions. For code processed by Vite/Webpack/esbuild.

### Q5: Branded types?

Add a phantom property to prevent accidental mixing of structurally identical types.

```typescript
type UserId = string & { readonly __brand: unique symbol };
type OrderId = string & { readonly __brand: unique symbol };
function getUser(id: UserId): User { /* ... */ }
getUser(orderId); // Compile error
```

### Q6: Template literal types?

```typescript
type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';
type Route = `${HTTPMethod} /${string}`;

type ExtractParams<T extends string> =
  T extends `${string}:${infer Param}/${infer Rest}` ? Param | ExtractParams<Rest>
  : T extends `${string}:${infer Param}` ? Param : never;

type Params = ExtractParams<'/users/:userId/orders/:orderId'>; // 'userId' | 'orderId'
```

### Q7: Project references?

Split TypeScript into sub-projects with `composite: true`. Benefits: incremental builds, enforced boundaries, parallel compilation. Use when full recompilation exceeds 10 seconds or you need architectural enforcement in a monorepo.

### Q8: `any` vs `unknown` vs `never` vs `void`?

- `any`: opts out of type checking. Avoid.
- `unknown`: type-safe `any`, must narrow before use. For external input.
- `never`: empty type, unreachable code, exhaustive checks.
- `void`: no return value. Gotcha: `void` callbacks can return anything (return ignored).

### Q9: `satisfies` vs `as const`?

`satisfies` validates against a type without widening. `as const` makes values literal and readonly. Combine for best of both.

```typescript
const routes = { home: '/', users: '/users' } as const satisfies Record<string, `/${string}`>;
```

### Q10: Distributive conditional types?

Conditional types distribute over unions. `ToArray<string | number>` becomes `string[] | number[]`, not `(string | number)[]`. Prevent distribution by wrapping in a tuple: `[T] extends [any]`.

### Q11: Declaration merging?

Interfaces with the same name merge. Use it to augment third-party types (Express `Request`, etc.) or add static members to classes via namespace merging.

### Q12: Mapped types — non-trivial example?

```typescript
type Patchable<T> = {
  [K in keyof T as `set${Capitalize<string & K>}`]: (value: T[K]) => void;
} & {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};
```

### Q13: `const` type parameters (TS 5.0+)?

`<const T>` preserves literal types in generic inference instead of widening to `string[]`.

### Q14: `NoInfer` utility type (TS 5.4+)?

Prevents a type parameter from being inferred from a specific position. Useful when one argument should constrain another.

### Q15: `using` keyword (TS 5.2+ / Explicit Resource Management)?

```typescript
class Connection implements Disposable {
  [Symbol.dispose](): void { this.close(); }
}
async function query() {
  using conn = new Connection(); // Auto-disposed when scope exits
}
```

### Q16: Circular type references?

TypeScript handles recursive types since TS 3.7. `type TreeNode<T> = { value: T; children: TreeNode<T>[] }` works.

### Q17: `import type` and `verbatimModuleSyntax`?

`import type` is erased completely — no runtime dependency. With `verbatimModuleSyntax: true`, TS enforces that type-only imports use `import type`. Prevents accidental side effects and improves tree-shaking.

### Q18: Excess property checking?

Only applies to object literals directly assigned to a typed variable. Indirect assignment (through a variable) bypasses the check.

### Q19: Control flow narrowing?

Discriminated unions are the most powerful pattern: a shared literal field (`type`, `kind`, `success`) narrows the entire object. Custom type guards (`value is T`) and assertion functions (`asserts value is T`) extend narrowing.

### Q20: `strictNullChecks`?

Without it, `null`/`undefined` are assignable to every type. Always enable. Migration: turn it on, fix the hundreds of errors, never look back.

### Q21: How does `keyof` work with index signatures?

`keyof { [key: string]: unknown }` is `string | number` because numeric keys are valid string keys in JavaScript.

---

## Expert-Level Node.js Questions

### Q1: Event loop phases in order?

Timers, pending callbacks, idle/prepare, poll, check (`setImmediate`), close callbacks. Microtasks (`Promise.then`, `queueMicrotask`) and `process.nextTick` run between each phase. `nextTick` fires before microtasks.

### Q2: Sequential `await` vs `Promise.all`?

`for`/`await` loop: `N * avgLatency`. `Promise.all`: `max(latencies)`. Use `Promise.allSettled` when you need all results regardless of failures. Use `p-limit` for controlled concurrency.

### Q3: Stream backpressure?

When writable buffer is full, `.write()` returns `false`. Pause readable, resume on `drain`. Always use `pipeline()` from `node:stream/promises` — it handles backpressure automatically.

### Q4: Clustering — when to use?

Use for CPU-bound parallelism or process-level fault isolation. For I/O-bound workloads (most APIs), a single process handles thousands of concurrent connections fine. In production, prefer PM2 or Kubernetes pods.

### Q5: Debugging production memory leaks?

1. Monitor `process.memoryUsage()` for steady heap growth
2. Take heap snapshot: `v8.writeHeapSnapshot()`
3. Open in Chrome DevTools Memory tab
4. Common culprits: event listeners not removed, unbounded Maps, closures capturing large scope, undrained streams

### Q6: Worker threads vs `child_process`?

Threads: shared memory (`SharedArrayBuffer`), low overhead, crash can corrupt shared state. Processes: fully isolated, higher overhead, crash is contained. Use threads for CPU computation, processes for running separate programs.

### Q7: `AbortController` in Node.js?

Works with `fetch`, streams, `events.on`, and custom async operations. Compose signals with `AbortSignal.any()` and `AbortSignal.timeout()` (Node.js 20+).

### Q8: V8 garbage collection and `--max-old-space-size`?

New space (young gen): Scavenge, fast/frequent. Old space: Mark-Sweep-Compact, slower/less frequent. `--max-old-space-size=4096` sets old space to 4GB. Tune `--max-semi-space-size` for apps creating many short-lived objects.

### Q9: `process.nextTick` vs `queueMicrotask`?

`nextTick` runs before microtasks (Promises). Recursive `nextTick` starves I/O. Prefer `queueMicrotask` for spec compliance.

### Q10: Graceful shutdown?

```typescript
async function gracefulShutdown(signal: string): Promise<void> {
  server.close();                                    // Stop accepting connections
  const deadline = setTimeout(() => process.exit(1), 30_000); // Hard deadline
  await closeInFlightRequests();
  await prisma.$disconnect();
  await redis.quit();
  clearTimeout(deadline);
  process.exit(0);
}
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
```

### Q11: Uncaught exceptions and unhandled rejections?

`uncaughtException`: process is in undefined state — log and shutdown. Cannot safely continue. `unhandledRejection`: In Node.js 15+, throws by default. Treat same as uncaught exceptions.

### Q12: `AsyncLocalStorage`?

Request-scoped context without passing through every function. Use for request IDs, tenant context, correlation IDs in logging.

```typescript
const als = new AsyncLocalStorage<{ requestId: string }>();
app.use((req, res, next) => als.run({ requestId: randomUUID() }, next));
// Anywhere: als.getStore()?.requestId
```

### Q13: `node:test` built-in runner?

`describe`/`it`/`test`, `mock`, `assert`. Run with `node --test`. Supports watch mode, test filtering, and experimental coverage. Viable for libraries; most production apps still use Vitest.

### Q14: ESM vs CJS?

ESM: async loading, strict mode, no `__dirname` (use `import.meta.url`), can import CJS. CJS: sync `require()`, has `__dirname`/`__filename`, cannot import ESM (except via dynamic `import()`).

### Q15: `setImmediate` vs `setTimeout(fn, 0)` ordering?

Outside I/O callbacks: non-deterministic. Inside I/O callbacks: `setImmediate` always fires first.

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

---

## Code Review Exercises

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
