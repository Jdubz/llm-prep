# Module 10: Interview Prep — Cheat Sheet

---

## Top 20 Must-Know Answers (One-Liners)

| # | Question | One-Liner Answer |
|---|----------|------------------|
| 1 | Event loop phases? | Timers, pending callbacks, idle/prepare, poll, check (setImmediate), close callbacks. Microtasks run between each phase. |
| 2 | `process.nextTick` vs `queueMicrotask`? | `nextTick` fires before microtasks (Promises). Prefer `queueMicrotask` for spec compliance. |
| 3 | Stream backpressure? | When writable's buffer is full, `write()` returns `false`. Pause readable, resume on `drain` event. Use `pipeline()`. |
| 4 | Worker threads vs child process? | Threads share memory (SharedArrayBuffer), lower overhead. Processes are fully isolated, higher overhead. |
| 5 | Cluster module? | Forks the process N times. OS load-balances TCP connections. Use for CPU-bound work or process isolation. |
| 6 | Memory leak debugging? | `v8.writeHeapSnapshot()`, Chrome DevTools Memory tab, look for growing Maps/closures/listeners. |
| 7 | `type` vs `interface`? | `interface` for declaration merging and public APIs. `type` for unions, intersections, and utility types. |
| 8 | Covariance/contravariance? | Arrays are covariant (Dog[] assignable to Animal[]). Function params are contravariant with `strictFunctionTypes`. |
| 9 | `infer` keyword? | Declares a type variable inside a conditional type's extends clause. Used in ReturnType, Parameters, etc. |
| 10 | Branded types? | Add a phantom `__brand` property to primitives to prevent mixing UserId/OrderId at compile time. |
| 11 | Clean architecture dependency rule? | Dependencies point inward. Domain has zero external imports. Infrastructure implements domain interfaces. |
| 12 | CQRS when? | When read/write models diverge, when reads are 100:1 vs writes, when you need independent scaling. Overkill for CRUD. |
| 13 | Microservices vs monolith? | Start modular monolith. Extract when you need: independent scaling, independent deploy, tech divergence, team autonomy. |
| 14 | Saga pattern? | Distributed transaction alternative. Orchestration (central coordinator) or choreography (event-driven). Compensating transactions on failure. |
| 15 | DI in Node.js? | Manual composition root for most projects. tsyringe/inversify only when graph exceeds ~50 services. |
| 16 | Operational vs programmer errors? | Operational: expected failures, return error response. Programmer: bugs, crash and restart. |
| 17 | `AsyncLocalStorage`? | Request-scoped context without passing through every function. Used for request IDs, tenant context, logging. |
| 18 | ESM vs CJS? | ESM is async, strict mode, no `__dirname`. CJS is sync, has `require()`. ESM can import CJS but not vice versa. |
| 19 | Graceful shutdown? | Stop accepting connections, wait for in-flight requests, close DB/Redis, set hard deadline, then exit. |
| 20 | `satisfies` vs `as const`? | `satisfies` validates type without widening. `as const` makes values literal and readonly. Combine for best of both. |

---

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

## Code Review Red Flags Checklist

**Performance**: Sequential `await` in loops, N+1 queries, missing indexes, unbounded SELECTs, large JSON on main thread, no backpressure, new DB client per request.

**Security**: Unparameterized SQL, no rate limiting on auth, secrets in code, no CORS config, JWT in localStorage, no input validation, no security headers.

**Reliability**: Missing async error handling, silent `.catch`, no graceful shutdown, no retries on external calls, no circuit breaker, no timeouts, unbounded caches.

**Architecture**: Business logic in controllers, direct DB in presentation layer, circular deps, side effects in request path, missing transactions, `console.log`, hardcoded config.

---

## Live Coding Setup Template

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

---

## "Questions They'll Definitely Ask"

**TypeScript**: `type` vs `interface`, `any`/`unknown`/`never`, generics + `infer`, `strict` mode flags, discriminated unions + type guards.

**Node.js**: Event loop phases, streams + backpressure, async error handling, `require` vs `import`, memory leak debugging.

**Architecture**: Monolith vs microservices, distributed transactions (sagas), project structure, error handling across layers, testing strategy.

**System Design**: Real-time feature (WebSocket + Redis Pub/Sub), background jobs (BullMQ), rate limiter (Redis sliding window), scaling (caching, read replicas, CQRS), production debugging (OpenTelemetry, structured logging).

**Behavioral/Staff**: Technical decisions affecting multiple teams, build vs buy, tech debt strategy, mentoring, production incident postmortems.

---

## Last-Minute Reminders

- **Structure your answers**: State the answer, explain why, give a concrete example
- **Say "it depends"**: But always follow up with the specific factors it depends on
- **Show trade-offs**: Every decision has costs. Name them.
- **Ask clarifying questions**: In system design, the constraints change the answer
- **Admit gaps**: "I haven't used X in production, but my understanding is..." beats faking it
