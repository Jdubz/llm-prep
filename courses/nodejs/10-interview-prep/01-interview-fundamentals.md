# 01 – Interview Fundamentals

> This is the capstone. Everything from modules 01-09 converges here into the formats you'll actually encounter: rapid-fire Q&A, system design sessions, code review exercises, and live coding. If you only have 2 hours before an interview, read this module.

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
