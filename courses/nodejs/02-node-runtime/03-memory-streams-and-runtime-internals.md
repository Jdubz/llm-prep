# 03 — V8 Memory, Buffer, Streams, Backpressure, GC, and Interview Q&A

> Assumes event loop (file 01) and threading/process management (file 02). Covers the runtime internals that appear in senior/staff-level production debugging scenarios.

---

## 1. Memory Management and V8 Garbage Collection

### 1.1 V8 Heap Structure

```
V8 Heap
├── New Space (Young Generation): Semi-space From + Semi-space To
├── Old Space: Old Pointer Space + Old Data Space
├── Large Object Space (objects > ~500KB, never moved)
├── Code Space (JIT-compiled code)
└── Map Space (hidden classes / maps)
```

### 1.2 GC Algorithms

**Scavenge (Minor GC)** — New Space, Cheney's algorithm:
1. Copy live objects from "from" semi-space to "to" semi-space.
2. Wipe "from" space; swap roles.
3. Objects surviving two Scavenges promote to Old Space.
Fast because most young objects die quickly (generational hypothesis).

**Mark-Sweep (Major GC)** — Old Space:
1. Mark: Traverse object graph from roots, mark reachable objects.
2. Sweep: Free unmarked objects. Creates fragmentation.

**Mark-Compact**: Same marking, but compacts live objects to eliminate fragmentation. More expensive; used when fragmentation is high.

**Incremental + Concurrent Marking**: Interleave marking with JS execution (~5ms chunks) and run marking on background threads to minimize pause times.

### 1.3 Configuration and Leak Detection

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

**Red flags**: `heapUsed` monotonically increasing across GC cycles. `rss` growing without `heapTotal` growing indicates native memory leak (addons/Buffers).

### 1.4 Memory Fields Explained

```typescript
const m = process.memoryUsage();
// m.rss          -- total RAM allocated to process
// m.heapTotal    -- V8 heap allocated
// m.heapUsed     -- V8 heap in use
// m.external     -- C++ objects tied to JS objects
// m.arrayBuffers -- ArrayBuffer + SharedArrayBuffer memory
```

---

## 2. Buffer and Binary Data

`Buffer` is fixed-size memory **outside** the V8 heap (for > 8KB; smaller ones use a shared pool on the heap).

```typescript
const safe = Buffer.alloc(1024);           // zero-filled
const unsafe = Buffer.allocUnsafe(1024);   // uninitialized (may contain old data)
const from = Buffer.from('hello', 'utf8');
```

**Pool**: Node.js maintains an 8KB pool. `allocUnsafe` and `Buffer.from` draw from it for sizes <= 4KB, which is why `allocUnsafe` is faster (skips zeroing).

```typescript
const a = Buffer.from('x');
const b = Buffer.from('y');
console.log(a.buffer === b.buffer); // true -- same pool slab
```

**Security**: Use `crypto.timingSafeEqual()` for constant-time Buffer comparison. Never use `allocUnsafe` for security-sensitive data.

---

## 3. Streams

### 3.1 The Four Stream Types

| Type | Readable | Writable | Example |
|---|---|---|---|
| Readable | Yes | No | `fs.createReadStream`, `http.IncomingMessage` |
| Writable | No | Yes | `fs.createWriteStream`, `http.ServerResponse` |
| Duplex | Yes | Yes | `net.Socket`, `crypto.createCipheriv` (independent channels) |
| Transform | Yes | Yes | `zlib.createGzip`, `crypto.createHash` (output derived from input) |

### 3.2 Backpressure

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

### 3.3 Backpressure Flow (Cheat Sheet)

```
Readable ──data──► Writable
                    │
            .write() returns false?
            ├── YES: readable.pause()
            │        wait for 'drain' event
            │        then readable.resume()
            └── NO:  continue
```

**Always prefer `pipeline()`** over `.pipe()`:

```typescript
import { pipeline } from 'stream/promises';
await pipeline(readable, transform, writable);
// Handles: backpressure, error propagation, stream cleanup
```

### 3.4 highWaterMark

Advisory buffer threshold: 16KB default for binary, 16 objects for objectMode. NOT a hard limit. `writable.write()` returns `false` when buffer exceeds it.

### 3.5 Custom Transform Stream

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

### 3.6 `pipeline()` vs `.pipe()`

| Feature | `.pipe()` | `pipeline()` |
|---|---|---|
| Error propagation | Manual | Automatic |
| Stream cleanup | Manual | Automatic |
| Promise support | No | Yes (`stream/promises`) |
| AbortSignal | No | Yes |

---

## 4. Diagnostic Tools

### 4.1 Memory Debugging Commands (Cheat Sheet)

```bash
# V8 heap size limits
node --max-old-space-size=4096 app.js    # Old space: 4GB
node --max-semi-space-size=64 app.js     # New space semi-space: 64MB

# Heap snapshots
node --inspect app.js                     # Chrome DevTools at chrome://inspect
node -e "require('v8').writeHeapSnapshot()"  # Snapshot to file

# GC tracing
node --trace-gc app.js                    # Log every GC event
node --trace-gc-verbose app.js            # Detailed GC logging
node --expose-gc app.js                   # Allow manual gc() calls

# CPU profiling
node --prof app.js                        # V8 profiler log
node --prof-process isolate-*.log         # Process the log

# Core dump analysis
ulimit -c unlimited                       # Enable core dumps
node --abort-on-uncaught-exception app.js # Dump on crash
```

### 4.2 Inspector Protocol

```bash
node --inspect app.js          # Chrome DevTools at chrome://inspect
node --inspect-brk app.js     # Break on first line
```

Capabilities: CPU profiling (flame charts), heap snapshots, live debugging, memory allocation timeline.

### 4.3 V8 Profiling

```bash
node --prof app.js                         # Generate V8 tick log
node --prof-process isolate-*.log > out.txt # Human-readable analysis
```

Shows statistical profiling ticks, JIT events, and bottom-up heavy profile.

### 4.4 Heap Snapshots

```typescript
import v8 from 'v8';
v8.writeHeapSnapshot(); // Writes .heapsnapshot file, loadable in Chrome DevTools

import inspector from 'inspector';
const session = new inspector.Session();
session.connect();
session.post('HeapProfiler.takeHeapSnapshot');
```

### 4.5 Core Dumps

```bash
ulimit -c unlimited
node --abort-on-uncaught-exception app.js
# Analyze with llnode:
lldb -c core.12345
(lldb) v8 bt        # JavaScript backtrace
(lldb) v8 inspect   # Inspect JS objects
```

### 4.6 Clinic.js

```bash
npx clinic flame -- node app.js       # CPU flame graph
npx clinic bubbleprof -- node app.js  # Async flow visualization
npx clinic doctor -- node app.js      # Event loop + GC + I/O health check
```

---

## 5. Hidden Class and IC Gotchas

8. **Hidden class thrashing**: Different property insertion orders or `delete` forces megamorphic IC (slow). Initialize all properties consistently.

The hidden class point is worth reinforcing with a code pattern for high-performance services:

```typescript
// FAST: consistent property initialization order
class RequestContext {
  requestId: string;
  userId: string;
  startTime: number;

  constructor(id: string, userId: string) {
    this.requestId = id;
    this.userId = userId;
    this.startTime = Date.now();
  }
}

// SLOW: conditional property assignment creates multiple hidden classes
function makeCtx(id: string, userId?: string) {
  const ctx: any = { requestId: id };
  if (userId) ctx.userId = userId; // Different shape — forces polymorphic IC
  return ctx;
}
```

---

## 6. Interview Questions

### Q1: Explain the order of execution.

```typescript
console.log('1');
setTimeout(() => console.log('2'), 0);
setImmediate(() => console.log('3'));
Promise.resolve().then(() => console.log('4'));
process.nextTick(() => console.log('5'));
console.log('6');
```

**Answer**: `1, 6, 5, 4, {2,3 in non-deterministic order}`. Synchronous first (1, 6). Microtasks: nextTick (5), then Promises (4). Then the event loop — `setTimeout(0)` vs `setImmediate` from main module is non-deterministic.

### Q2: Service has increasing latency under load but CPU is at 30%. What do you investigate?

**Answer**: Event loop blockage or thread pool saturation. Check for sync operations on main thread (`JSON.parse` on large payloads, `fs.readFileSync`, regex backtracking). Check `UV_THREADPOOL_SIZE` (default 4). Use `--inspect` for CPU profile. Measure event loop lag with `monitorEventLoopDelay` from `perf_hooks`:

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

**Answer**: Monitor `process.memoryUsage()` — monotonically increasing `heapUsed` indicates a leak. Take heap snapshots via `v8.writeHeapSnapshot()` or Chrome DevTools. Compare two snapshots; sort by "Objects allocated between snapshots." Common causes: event listener accumulation, closures capturing large objects, global caches without eviction, forgotten timers.

### Q4: Worker threads vs cluster module?

**Answer**: Worker threads for CPU-bound computation benefiting from shared memory (SharedArrayBuffer). Cluster for scaling HTTP servers across cores with process isolation. Worker thread crashes can destabilize the process; cluster worker crashes are isolated.

### Q5: Explain backpressure in streams.

**Answer**: When a readable produces data faster than a writable consumes it, the writable's buffer fills. `write()` returns `false` past `highWaterMark`. The readable should `pause()` and resume on `drain`. `pipeline()` handles this automatically. Without it, memory grows unbounded.

### Q6: `Buffer.alloc()` vs `Buffer.allocUnsafe()`?

**Answer**: `alloc` zero-fills (safe, slower). `allocUnsafe` reuses pooled memory without zeroing (fast, may leak old data). Use `allocUnsafe` only when immediately overwriting all bytes. Always `alloc` for security-sensitive data.

### Q7: How does DNS resolution differ between `lookup` and `resolve`?

**Answer**: `dns.lookup()` uses `getaddrinfo` on the libuv thread pool — competes with `fs` for 4 default threads. `dns.resolve()` uses c-ares with its own sockets, not the thread pool. For high-throughput services, prefer `resolve()` or increase `UV_THREADPOOL_SIZE`.

### Q8: V8 GC strategy and its impact on Node.js performance?

**Answer**: Generational GC. Young generation: Scavenge (semi-space copying, fast). Old generation: Mark-Sweep/Mark-Compact with incremental and concurrent marking to reduce pauses. Impact: GC pauses cause latency spikes. Larger heaps mean longer major GC. Minimize allocation rates in hot paths; avoid promoting short-lived objects.

### Q9: Walk through the `require()` resolution algorithm.

**Answer**: (1) Core module? Return cached. (2) Starts with `./`, `../`, `/`? Resolve as file (try extensions: `.js`, `.json`, `.node`), then directory (`package.json` main, then `index.js`). (3) Otherwise, walk up `node_modules` directories. (4) Cache by resolved absolute path. ESM differs: no auto extensions, uses `package.json` exports field, async three-phase loading (construction, instantiation, evaluation), live bindings.

### Q10: Implement graceful shutdown ensuring in-flight requests complete.

**Answer**: `server.close()` stops new connections. Track sockets in a Set; set aggressive timeouts on idle ones. Drain app state (DB, queues). Hard deadline timer with `.unref()`. Handle SIGTERM + SIGINT. See the graceful shutdown pattern in section 4.2 of file 02.
