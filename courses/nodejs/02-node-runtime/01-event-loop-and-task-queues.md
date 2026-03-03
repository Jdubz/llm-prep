# 01 — Event Loop Phases, Microtask Queue, and process.nextTick vs setImmediate

> Staff-level depth. Assumes you have shipped Node.js services in production and are comfortable with asynchronous JavaScript and TypeScript.

---

## 1. The Event Loop: Phase-by-Phase Breakdown

The event loop is **not** a single queue. It is a series of **phases**, each with its own FIFO queue of callbacks. Node.js drains each phase's queue (up to a system-dependent limit), then advances.

### 1.1 Phase Diagram

```
   ┌───────────────────────────┐
┌─>│         timers             │  setTimeout / setInterval callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │     pending callbacks      │  I/O callbacks deferred to next iteration
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │       idle, prepare        │  internal use only (libuv housekeeping)
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           poll             │  retrieve new I/O events; execute I/O callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           check            │  setImmediate callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │      close callbacks       │  socket.on('close', ...) etc.
│  └───────────────────────────┘
```

**Timers**: Executes `setTimeout`/`setInterval` callbacks. The threshold is a *minimum* delay, not guaranteed. Node.js coalesces timers using a min-heap internally.

**Pending Callbacks**: Deferred system-level I/O callbacks (e.g., TCP `ECONNREFUSED`). Most I/O callbacks fire in the poll phase; this handles edge cases.

**Idle / Prepare**: Internal libuv bookkeeping. `setImmediate` does NOT run here (common misconception) — it runs in the **check** phase.

**Poll**: Where Node.js spends most time. Calculates how long to block for I/O, then processes the poll queue. If empty: moves to check (if `setImmediate` scheduled) or blocks waiting for I/O (bounded by nearest timer).

**Check**: Exclusively for `setImmediate()` callbacks, runs after poll completes.

**Close Callbacks**: Handles `close` events (`socket.on('close', ...)`).

### 1.2 Phase Table (Cheat Sheet)

```
┌─────────────────────────────────────────────────────────┐
│ ┌─► TIMERS ──► PENDING CB ──► IDLE ──► POLL ──► CHECK ─┤
│ │                                                       │
│ └──────────────── CLOSE CALLBACKS ◄─────────────────────┘
│                                                         │
│   Between EVERY phase and after EVERY callback:         │
│     1. Drain process.nextTick queue                     │
│     2. Drain Promise microtask queue                    │
└─────────────────────────────────────────────────────────┘
```

| Phase | What Fires | API |
|---|---|---|
| Timers | Expired timer callbacks | `setTimeout`, `setInterval` |
| Pending callbacks | Deferred I/O callbacks (e.g. TCP errors) | Internal |
| Idle / Prepare | libuv internal bookkeeping | Internal |
| Poll | I/O callbacks; blocks if empty and no timers/immediates | `fs.read`, sockets |
| Check | Immediate callbacks | `setImmediate` |
| Close | Close event handlers | `socket.on('close')` |

---

## 2. The `setTimeout` vs `setImmediate` Ordering Problem

```typescript
// NON-DETERMINISTIC from main module:
setTimeout(() => console.log('timeout'), 0);
setImmediate(() => console.log('immediate'));

// DETERMINISTIC inside I/O callback -- immediate always fires first:
import { readFile } from 'fs';
readFile(__filename, () => {
  setTimeout(() => console.log('timeout'), 0);
  setImmediate(() => console.log('immediate'));
  // Output: immediate, timeout (always)
});
```

Inside an I/O callback, the poll phase transitions to check before looping back to timers. From the main module, it depends on whether the 1ms timer threshold has elapsed before the timers phase runs.

---

## 3. Microtask Queues

Microtasks execute **between every phase transition** and **after every individual callback** within a phase.

### 3.1 Priority Order

```
1. process.nextTick queue     (highest priority -- drains completely)
2. Promise microtask queue    (queueMicrotask / Promise.then -- drains completely)
3. Next event loop phase
```

```typescript
Promise.resolve().then(() => console.log('promise 1'));
process.nextTick(() => console.log('nextTick 1'));
process.nextTick(() => {
  console.log('nextTick 2');
  process.nextTick(() => console.log('nextTick 3 (nested)'));
});
Promise.resolve().then(() => console.log('promise 2'));
// Output: nextTick 1, nextTick 2, nextTick 3 (nested), promise 1, promise 2
```

### 3.2 Microtask Priority Table (Cheat Sheet)

| Priority | Queue | API | Drains |
|---|---|---|---|
| 1 (highest) | nextTick | `process.nextTick()` | Completely (including nested) |
| 2 | Microtask | `queueMicrotask()`, `Promise.then()` | Completely (including nested) |
| 3 | Macro (next phase) | `setTimeout`, `setImmediate`, I/O | Per-phase limits apply |

**Rule**: All nextTick callbacks drain, then all Promise microtasks drain, then the event loop advances to the next phase. This repeats between every phase AND after every individual callback within a phase.

### 3.3 `process.nextTick` vs `queueMicrotask`

| Aspect | `process.nextTick` | `queueMicrotask` |
|---|---|---|
| Queue | nextTick queue | Promise microtask queue |
| Priority | Higher (fires first) | Lower (after nextTick drains) |
| Spec | Node.js-specific | Web standard (WHATWG) |
| Starvation risk | High (recursive nextTick blocks I/O) | Same risk, but semantically clearer |

Node.js docs now recommend `queueMicrotask` for most use cases. Recursive `nextTick` or `queueMicrotask` **starves the event loop** — I/O, timers, and immediates never fire.

---

## 4. libuv Thread Pool

### 4.1 What Uses the Thread Pool

| Uses thread pool | Uses OS async primitives |
|---|---|
| `fs.*` (all file operations) | Network I/O (TCP/UDP sockets) |
| `dns.lookup()` (getaddrinfo) | `dns.resolve()` (c-ares) |
| `crypto.pbkdf2()`, `crypto.randomBytes()` | Signals, child processes |
| `zlib` (compression) | Pipes, TTY |

### 4.2 Default Size and Tuning

```bash
UV_THREADPOOL_SIZE=4   # default
UV_THREADPOOL_SIZE=64 node server.js  # set BEFORE process starts; max 1024
```

**Increase when**: High concurrent `fs` or `dns.lookup` operations cause latency.
**Do NOT increase for**: CPU-bound work (use worker threads instead).

### 4.3 Key Numbers

| Metric | Default | Max |
|---|---|---|
| UV_THREADPOOL_SIZE | 4 | 1024 |
| V8 old space (64-bit) | ~1.4 GB | `--max-old-space-size` |
| V8 new space semi-space | ~1-8 MB | `--max-semi-space-size` |
| Stream highWaterMark (binary) | 16 KB | Configurable |
| Stream highWaterMark (objectMode) | 16 objects | Configurable |
| Timer minimum delay | 1 ms | N/A |
| Max safe integer | 2^53 - 1 | `Number.MAX_SAFE_INTEGER` |
| Max string length | ~512 MB (V8) | Platform-dependent |
| Max Buffer size | ~2 GB | `buffer.constants.MAX_LENGTH` |

---

## 5. Event Loop Starvation

### 5.1 Detection

```typescript
import { monitorEventLoopDelay } from 'perf_hooks';
const h = monitorEventLoopDelay({ resolution: 20 });
h.enable();
setInterval(() => {
  const p99 = h.percentile(99) / 1e6;
  if (p99 > 100) console.warn(`Starvation! p99=${p99.toFixed(1)}ms`);
  h.reset();
}, 5000);
```

### 5.2 Common Causes and Mitigations

| Cause | Mitigation |
|---|---|
| `fs.readFileSync` in handlers | Use async `fs` APIs |
| `JSON.parse` on multi-MB payloads | Streaming JSON parser or worker thread |
| Catastrophic regex backtracking | Audit regexes; use RE2 for untrusted input |
| Tight computation loops | Batch with `setImmediate` yields |
| Recursive `process.nextTick` | Use `setImmediate` to yield to event loop |

```typescript
// Break up CPU work with setImmediate yields
async function processBatched<T>(items: T[], fn: (item: T) => void): Promise<void> {
  const BATCH = 1000;
  for (let i = 0; i < items.length; i += BATCH) {
    items.slice(i, i + BATCH).forEach(fn);
    if (i + BATCH < items.length) {
      await new Promise<void>((r) => setImmediate(r));
    }
  }
}
```

---

## 6. libuv Internals (Deep Dive)

### 6.1 Platform-Specific I/O Multiplexing

| Platform | Mechanism | Model |
|---|---|---|
| Linux | `epoll` | Readiness-based, O(1) |
| macOS/BSD | `kqueue` | Readiness-based, supports fs events |
| Windows | IOCP | Completion-based (fundamentally different) |

### 6.2 epoll (Linux)

```c
int epfd = epoll_create1(0);
struct epoll_event ev = { .events = EPOLLIN | EPOLLOUT, .data.fd = sock_fd };
epoll_ctl(epfd, EPOLL_CTL_ADD, sock_fd, &ev);
// Poll phase: block here waiting for I/O
int n = epoll_wait(epfd, events, MAX_EVENTS, timeout);
// Dispatch callbacks for ready file descriptors
```

Network I/O is fully async at the OS level via epoll — no thread pool needed. File system operations lack a mature async kernel interface on Linux (io_uring is changing this), so libuv delegates them to the thread pool.

### 6.3 Handles vs Requests

**Handles**: Long-lived objects (tcp, timer, pipe, signal). Init -> start -> stop -> close.
**Requests**: Short-lived operations (write, connect, dns, fs). Submit -> callback.

### 6.4 io_uring (Linux 5.1+)

True kernel-level async file I/O via submission/completion queues in shared memory. libuv is experimenting with io_uring support, which would eliminate the thread pool for file operations on modern kernels.

---

## 7. async_hooks and AsyncLocalStorage

### 7.1 async_hooks

Tracks async resource lifetimes. Every async operation gets an `asyncId` and `triggerAsyncId` (parent).

```typescript
import async_hooks from 'async_hooks';
async_hooks.createHook({
  init(asyncId, type, triggerAsyncId) { /* resource created */ },
  before(asyncId) { /* callback about to fire */ },
  after(asyncId)  { /* callback completed */ },
  destroy(asyncId) { /* resource destroyed */ },
}).enable();
```

**Warning**: Significant overhead. `init` fires for every Promise. Prefer `AsyncLocalStorage` in production.

### 7.2 AsyncLocalStorage

Context propagation across async boundaries — Node.js equivalent of thread-local storage.

```typescript
import { AsyncLocalStorage } from 'async_hooks';

interface RequestContext { requestId: string; userId: string; }
const als = new AsyncLocalStorage<RequestContext>();

// Middleware: wrap request in context
function middleware(req: Request, res: Response, next: () => void) {
  als.run({ requestId: crypto.randomUUID(), userId: extractUser(req) }, next);
}

// Anywhere downstream -- even in database layer:
function logQuery(sql: string) {
  const ctx = als.getStore();
  console.log(`[${ctx?.requestId}] ${sql}`);
}
```

Node.js 20+ uses a synchronous propagation implementation (3-5x faster than earlier async_hooks-based approach). Prefer `als.run()` (scoped) over `als.enterWith()` (mutates current context).

---

## 8. Common Gotchas

1. **setTimeout(0) vs setImmediate ordering**: Non-deterministic from main module; deterministic inside I/O callbacks (setImmediate always first).
2. **process.nextTick starvation**: Recursive nextTick blocks the entire event loop. Use `setImmediate` to yield between iterations.
3. **dns.lookup uses the thread pool**: `getaddrinfo` competes with `fs` for 4 default threads. Use `dns.resolve()` (c-ares) or increase `UV_THREADPOOL_SIZE`.
4. **Unhandled rejections crash** (Node 15+): Always `.catch()` or `try/catch` with `await`.
5. **Default thread pool = 4**: Set `UV_THREADPOOL_SIZE` via env var before process starts. Setting in code has no effect after pool init.
6. **ESM has no `__filename`/`__dirname`**: Use `fileURLToPath(import.meta.url)` and `dirname()`.

---

## Related Reading

- **Event loop fundamentals** build on the mental model from [Module 00 — The Event Loop](../00-ts-node-fundamentals.md#4-the-event-loop) — this file adds libuv phases, starvation detection, and platform-specific I/O multiplexing
- **Thread pool saturation** (Section 4) is a common production bottleneck explored further in [Performance — Clustering and Scaling](../08-performance-scaling/02-clustering-and-scaling.md) and [Performance — Profiling and Advanced Performance](../08-performance-scaling/03-profiling-and-advanced-performance.md)
- **Event loop starvation** (Section 5) — the `monitorEventLoopDelay` technique — ties directly into [Performance — Profiling and Advanced Performance](../08-performance-scaling/03-profiling-and-advanced-performance.md) (Clinic.js, Chrome DevTools profiling)
- **AsyncLocalStorage** (Section 7.2) is the foundation for request context propagation in [REST API Design — HTTP Semantics and Status Codes](../03-rest-api-design/01-http-semantics-and-status-codes.md) and distributed tracing in [Architecture — Event-Driven and Async Patterns](../09-architecture-patterns/02-event-driven-and-async-patterns.md)
- **libuv internals** (Section 6) — epoll, kqueue, IOCP — are the underlying mechanism for all I/O discussed in [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (Redis connections, WebSocket scaling)
- For worker threads, cluster module, and process management that build on these event loop concepts, continue to [Threading and Process Management](02-threading-and-process-management.md)
