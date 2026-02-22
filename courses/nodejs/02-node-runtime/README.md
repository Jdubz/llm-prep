# Module 02: Node.js Runtime Deep Dive

## Prerequisites

You should already be comfortable with asynchronous JavaScript, TypeScript generics,
and have production experience with Node.js. This module assumes 10+ years of
TypeScript/JavaScript experience and targets staff-level interview depth.

---

## 1. The Event Loop: Phase-by-Phase Breakdown

The event loop is **not** a single queue. It is a series of **phases**, each with its own
FIFO queue of callbacks. Node.js drains each phase's queue (up to a system-dependent
limit), then advances.

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

**Timers**: Executes `setTimeout`/`setInterval` callbacks. The threshold is a *minimum*
delay, not guaranteed. Node.js coalesces timers using a min-heap internally.

**Pending Callbacks**: Deferred system-level I/O callbacks (e.g., TCP `ECONNREFUSED`).
Most I/O callbacks fire in the poll phase; this handles edge cases.

**Idle / Prepare**: Internal libuv bookkeeping. `setImmediate` does NOT run here
(common misconception) -- it runs in the **check** phase.

**Poll**: Where Node.js spends most time. Calculates how long to block for I/O, then
processes the poll queue. If empty: moves to check (if `setImmediate` scheduled) or
blocks waiting for I/O (bounded by nearest timer).

**Check**: Exclusively for `setImmediate()` callbacks, runs after poll completes.

**Close Callbacks**: Handles `close` events (`socket.on('close', ...)`).

### 1.2 The setTimeout vs setImmediate Ordering Problem

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

Inside an I/O callback, the poll phase transitions to check before looping back to
timers. From the main module, it depends on whether the 1ms timer threshold has elapsed
before the timers phase runs.

---

## 2. Microtask Queues

Microtasks execute **between every phase transition** and **after every individual
callback** within a phase.

### 2.1 Priority Order

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

### 2.2 process.nextTick vs queueMicrotask

| Aspect | `process.nextTick` | `queueMicrotask` |
|---|---|---|
| Queue | nextTick queue | Promise microtask queue |
| Priority | Higher (fires first) | Lower (after nextTick drains) |
| Spec | Node.js-specific | Web standard (WHATWG) |
| Starvation risk | High (recursive nextTick blocks I/O) | Same risk, but semantically clearer |

Node.js docs now recommend `queueMicrotask` for most use cases. Recursive `nextTick`
or `queueMicrotask` **starves the event loop** -- I/O, timers, and immediates never fire.

---

## 3. libuv Thread Pool

### 3.1 What Uses the Thread Pool

| Uses thread pool | Uses OS async primitives |
|---|---|
| `fs.*` (all file operations) | Network I/O (TCP/UDP sockets) |
| `dns.lookup()` (getaddrinfo) | `dns.resolve()` (c-ares) |
| `crypto.pbkdf2()`, `crypto.randomBytes()` | Signals, child processes |
| `zlib` (compression) | Pipes, TTY |

### 3.2 Default Size and Tuning

```bash
UV_THREADPOOL_SIZE=4   # default
UV_THREADPOOL_SIZE=64 node server.js  # set BEFORE process starts; max 1024
```

**Increase when**: High concurrent `fs` or `dns.lookup` operations cause latency.
**Do NOT increase for**: CPU-bound work (use worker threads instead).

---

## 4. Worker Threads

Each worker runs its own V8 isolate and event loop within the same process.

### 4.1 Communication Patterns

```typescript
import { Worker, isMainThread, parentPort, workerData } from 'worker_threads';

if (isMainThread) {
  const sharedBuffer = new SharedArrayBuffer(4);
  const sharedArray = new Int32Array(sharedBuffer);
  const worker = new Worker(__filename, { workerData: { sharedBuffer } });

  worker.on('message', (msg: string) => {
    console.log(`Shared value: ${Atomics.load(sharedArray, 0)}`); // 42
  });
  worker.postMessage('start');
} else {
  const { sharedBuffer } = workerData as { sharedBuffer: SharedArrayBuffer };
  const sharedArray = new Int32Array(sharedBuffer);

  parentPort!.on('message', () => {
    Atomics.store(sharedArray, 0, 42);
    parentPort!.postMessage('done');
  });
}
```

### 4.2 Atomics API Essentials

```typescript
Atomics.store(typedArray, index, value);     // atomic write
Atomics.load(typedArray, index);             // atomic read
Atomics.add(typedArray, index, value);       // atomic add
Atomics.compareExchange(typedArray, index, expected, replacement);
Atomics.wait(typedArray, index, value);      // block until changed (workers only)
Atomics.notify(typedArray, index, count);    // wake waiting threads
```

### 4.3 Transferable Objects

```typescript
const { port1, port2 } = new MessageChannel();
const largeBuffer = new ArrayBuffer(1024 * 1024);
port1.postMessage(largeBuffer, [largeBuffer]); // zero-copy transfer
// largeBuffer.byteLength === 0 after transfer (neutered)
```

### 4.4 Worker Threads vs Cluster

| Criterion | Worker Threads | Cluster |
|---|---|---|
| Use case | CPU-bound computation | Scaling HTTP servers |
| Memory | Shared (SharedArrayBuffer) | Separate processes |
| Failure isolation | Low (can destabilize process) | High (isolated) |
| Port sharing | N/A | Built-in |
| Overhead | Lower (threads) | Higher (processes) |

---

## 5. Cluster Module

### 5.1 Fork Model and Load Distribution

```typescript
import cluster from 'cluster';
import http from 'http';
import os from 'os';

if (cluster.isPrimary) {
  for (let i = 0; i < os.cpus().length; i++) cluster.fork();
  cluster.on('exit', (worker, code, signal) => {
    console.log(`Worker ${worker.process.pid} died. Restarting...`);
    cluster.fork();
  });
} else {
  http.createServer((req, res) => {
    res.writeHead(200);
    res.end(`Worker ${process.pid}\n`);
  }).listen(8000);
}
```

**Round-robin** (default on Linux/macOS): Primary distributes connections evenly.
**OS-level** (Windows default): Workers compete for connections; can be uneven.

### 5.2 IPC and Sticky Sessions

```typescript
// Primary -> Worker
worker.send({ type: 'config:update', payload: { maxConnections: 1000 } });
// Worker -> Primary
process.send?.({ type: 'metrics', payload: { rps: 5000 } });
```

For WebSocket sticky sessions, hash client IP to a deterministic worker index:

```typescript
function getWorkerIndex(ip: string, numWorkers: number): number {
  const hash = createHash('md5').update(ip).digest('hex');
  return parseInt(hash.substring(0, 8), 16) % numWorkers;
}
```

PM2 wraps cluster with zero-downtime reload, log aggregation, and monitoring:
`pm2 start app.js -i max && pm2 reload app`.

---

## 6. Memory Management and V8 Garbage Collection

### 6.1 V8 Heap Structure

```
V8 Heap
├── New Space (Young Generation): Semi-space From + Semi-space To
├── Old Space: Old Pointer Space + Old Data Space
├── Large Object Space (objects > ~500KB, never moved)
├── Code Space (JIT-compiled code)
└── Map Space (hidden classes / maps)
```

### 6.2 GC Algorithms

**Scavenge (Minor GC)** -- New Space, Cheney's algorithm:
1. Copy live objects from "from" semi-space to "to" semi-space.
2. Wipe "from" space; swap roles.
3. Objects surviving two Scavenges promote to Old Space.
Fast because most young objects die quickly (generational hypothesis).

**Mark-Sweep (Major GC)** -- Old Space:
1. Mark: Traverse object graph from roots, mark reachable objects.
2. Sweep: Free unmarked objects. Creates fragmentation.

**Mark-Compact**: Same marking, but compacts live objects to eliminate fragmentation.
More expensive; used when fragmentation is high.

**Incremental + Concurrent Marking**: Interleave marking with JS execution (~5ms chunks)
and run marking on background threads to minimize pause times.

### 6.3 Configuration and Leak Detection

```bash
node --max-old-space-size=4096 app.js   # Old space limit (MB)
node --max-semi-space-size=64 app.js    # Semi-space limit (MB)
node --expose-gc app.js                  # Allow manual gc()
```

```typescript
setInterval(() => {
  const u = process.memoryUsage();
  console.log({
    rss: `${(u.rss / 1024 / 1024).toFixed(1)}MB`,
    heapUsed: `${(u.heapUsed / 1024 / 1024).toFixed(1)}MB`,
    external: `${(u.external / 1024 / 1024).toFixed(1)}MB`,
  });
}, 5000);
```

**Red flags**: `heapUsed` monotonically increasing across GC cycles. `rss` growing
without `heapTotal` growing indicates native memory leak (addons/Buffers).

---

## 7. Streams

### 7.1 The Four Stream Types

| Type | Readable | Writable | Example |
|---|---|---|---|
| Readable | Yes | No | `fs.createReadStream`, `http.IncomingMessage` |
| Writable | No | Yes | `fs.createWriteStream`, `http.ServerResponse` |
| Duplex | Yes | Yes | `net.Socket` (independent channels) |
| Transform | Yes | Yes | `zlib.createGzip` (output derived from input) |

### 7.2 Backpressure

```typescript
// WRONG -- ignores backpressure:
readable.on('data', (chunk) => writable.write(chunk));

// RIGHT -- manual:
readable.on('data', (chunk) => {
  if (!writable.write(chunk)) {
    readable.pause();
    writable.once('drain', () => readable.resume());
  }
});

// BEST -- pipeline handles backpressure, errors, and cleanup:
import { pipeline } from 'stream/promises';
await pipeline(readable, transform, writable);
```

### 7.3 highWaterMark

Advisory buffer threshold: 16KB default for binary, 16 objects for objectMode. NOT a
hard limit. `writable.write()` returns `false` when buffer exceeds it.

### 7.4 Custom Transform Stream

```typescript
import { Transform, TransformCallback } from 'stream';

class JsonParser extends Transform {
  private buffer = '';
  constructor() {
    super({ readableObjectMode: true, writableObjectMode: false });
  }
  _transform(chunk: Buffer, _enc: string, cb: TransformCallback): void {
    this.buffer += chunk.toString();
    const lines = this.buffer.split('\n');
    this.buffer = lines.pop()!;
    for (const line of lines) {
      if (line.trim()) {
        try { this.push(JSON.parse(line)); }
        catch (e) { return cb(e as Error); }
      }
    }
    cb();
  }
  _flush(cb: TransformCallback): void {
    if (this.buffer.trim()) {
      try { this.push(JSON.parse(this.buffer)); }
      catch (e) { return cb(e as Error); }
    }
    cb();
  }
}
```

### 7.5 pipeline() vs .pipe()

| Feature | `.pipe()` | `pipeline()` |
|---|---|---|
| Error propagation | Manual | Automatic |
| Stream cleanup | Manual | Automatic |
| Promise support | No | Yes (`stream/promises`) |
| AbortSignal | No | Yes |

---

## 8. Buffer and Binary Data

`Buffer` is fixed-size memory **outside** the V8 heap (for > 8KB; smaller ones use a
shared pool on the heap).

```typescript
const safe = Buffer.alloc(1024);           // zero-filled
const unsafe = Buffer.allocUnsafe(1024);   // uninitialized (may contain old data)
const from = Buffer.from('hello', 'utf8');
```

**Pool**: Node.js maintains an 8KB pool. `allocUnsafe` and `Buffer.from` draw from it
for sizes <= 4KB, which is why `allocUnsafe` is faster (skips zeroing).

```typescript
const a = Buffer.from('x');
const b = Buffer.from('y');
console.log(a.buffer === b.buffer); // true -- same pool slab
```

**Security**: Use `crypto.timingSafeEqual()` for constant-time Buffer comparison.
Never use `allocUnsafe` for security-sensitive data.

---

## 9. Process Lifecycle and Graceful Shutdown

### 9.1 Signals and Error Handlers

```typescript
process.on('SIGTERM', shutdown);  // Kubernetes / systemd stop signal
process.on('SIGINT', shutdown);   // Ctrl+C
process.on('SIGHUP', reloadConfig); // Convention: reload configuration
// SIGKILL and SIGSTOP cannot be caught

process.on('uncaughtException', (err: Error) => {
  console.error('Uncaught:', err);
  process.exit(1); // Process is in undefined state -- log and exit
});

process.on('unhandledRejection', (reason: unknown) => {
  console.error('Unhandled rejection:', reason);
  // Node.js 15+ throws by default. Treat like uncaughtException.
});
```

### 9.2 Graceful Shutdown Pattern

```typescript
const connections = new Set<import('net').Socket>();
server.on('connection', (s) => {
  connections.add(s);
  s.on('close', () => connections.delete(s));
});

async function shutdown(): Promise<void> {
  // 1. Stop accepting new connections
  server.close();
  // 2. Close idle keep-alive connections
  for (const s of connections) s.setTimeout(1);
  // 3. Drain application state
  await closeDatabasePool();
  await flushMessageQueue();
  // 4. Hard deadline with unref (won't keep process alive)
  const force = setTimeout(() => process.exit(1), 30_000);
  force.unref();
  process.exit(0);
}
```

### 9.3 What Keeps the Process Alive

Active **refs**: open servers, active timers, file watchers, child processes, TCP
connections. Call `.unref()` on a timer/handle so it won't prevent exit.

---

## 10. Interview Questions and Answers

### Q1: Explain the order of execution.

```typescript
console.log('1');
setTimeout(() => console.log('2'), 0);
setImmediate(() => console.log('3'));
Promise.resolve().then(() => console.log('4'));
process.nextTick(() => console.log('5'));
console.log('6');
```

**Answer**: `1, 6, 5, 4, {2,3 in non-deterministic order}`. Synchronous first (1, 6).
Microtasks: nextTick (5), then Promises (4). Then the event loop -- `setTimeout(0)` vs
`setImmediate` from main module is non-deterministic.

### Q2: Service has increasing latency under load but CPU is at 30%. What do you investigate?

**Answer**: Event loop blockage or thread pool saturation. Check for sync operations
on main thread (`JSON.parse` on large payloads, `fs.readFileSync`, regex backtracking).
Check `UV_THREADPOOL_SIZE` (default 4). Use `--inspect` for CPU profile. Measure event
loop lag with `monitorEventLoopDelay` from `perf_hooks`:

```typescript
import { monitorEventLoopDelay } from 'perf_hooks';
const h = monitorEventLoopDelay({ resolution: 20 });
h.enable();
setInterval(() => {
  console.log(`p99: ${(h.percentile(99) / 1e6).toFixed(1)}ms`);
  h.reset();
}, 5000);
```

### Q3: How do you handle a memory leak in production?

**Answer**: Monitor `process.memoryUsage()` -- monotonically increasing `heapUsed`
indicates a leak. Take heap snapshots via `v8.writeHeapSnapshot()` or Chrome DevTools.
Compare two snapshots; sort by "Objects allocated between snapshots." Common causes:
event listener accumulation, closures capturing large objects, global caches without
eviction, forgotten timers.

### Q4: Worker threads vs cluster module?

**Answer**: Worker threads for CPU-bound computation benefiting from shared memory
(SharedArrayBuffer). Cluster for scaling HTTP servers across cores with process
isolation. Worker thread crashes can destabilize the process; cluster worker crashes
are isolated.

### Q5: Explain backpressure in streams.

**Answer**: When a readable produces data faster than a writable consumes it, the
writable's buffer fills. `write()` returns `false` past `highWaterMark`. The readable
should `pause()` and resume on `drain`. `pipeline()` handles this automatically.
Without it, memory grows unbounded.

### Q6: `Buffer.alloc()` vs `Buffer.allocUnsafe()`?

**Answer**: `alloc` zero-fills (safe, slower). `allocUnsafe` reuses pooled memory
without zeroing (fast, may leak old data). Use `allocUnsafe` only when immediately
overwriting all bytes. Always `alloc` for security-sensitive data.

### Q7: How does DNS resolution differ between `lookup` and `resolve`?

**Answer**: `dns.lookup()` uses `getaddrinfo` on the libuv thread pool -- competes with
`fs` for 4 default threads. `dns.resolve()` uses c-ares with its own sockets, not the
thread pool. For high-throughput services, prefer `resolve()` or increase
`UV_THREADPOOL_SIZE`.

### Q8: V8 GC strategy and its impact on Node.js performance?

**Answer**: Generational GC. Young generation: Scavenge (semi-space copying, fast).
Old generation: Mark-Sweep/Mark-Compact with incremental and concurrent marking to
reduce pauses. Impact: GC pauses cause latency spikes. Larger heaps mean longer major
GC. Minimize allocation rates in hot paths; avoid promoting short-lived objects.

### Q9: Walk through the `require()` resolution algorithm.

**Answer**: (1) Core module? Return cached. (2) Starts with `./`, `../`, `/`? Resolve
as file (try extensions: `.js`, `.json`, `.node`), then directory (`package.json` main,
then `index.js`). (3) Otherwise, walk up `node_modules` directories. (4) Cache by
resolved absolute path. ESM differs: no auto extensions, uses `package.json` exports
field, async three-phase loading (construction, instantiation, evaluation), live bindings.

### Q10: Implement graceful shutdown ensuring in-flight requests complete.

**Answer**: `server.close()` stops new connections. Track sockets in a Set; set aggressive
timeouts on idle ones. Drain app state (DB, queues). Hard deadline timer with `.unref()`.
Handle SIGTERM + SIGINT. See Section 9.2.
