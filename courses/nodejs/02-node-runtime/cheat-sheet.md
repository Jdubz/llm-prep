# Module 02 Cheat Sheet: Node.js Runtime Quick Reference

---

## Event Loop Phase Execution Order

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

## Microtask Priority Table

| Priority | Queue | API | Drains |
|---|---|---|---|
| 1 (highest) | nextTick | `process.nextTick()` | Completely (including nested) |
| 2 | Microtask | `queueMicrotask()`, `Promise.then()` | Completely (including nested) |
| 3 | Macro (next phase) | `setTimeout`, `setImmediate`, I/O | Per-phase limits apply |

**Rule**: All nextTick callbacks drain, then all Promise microtasks drain, then the
event loop advances to the next phase. This repeats between every phase AND after
every individual callback within a phase.

---

## Worker Threads vs Cluster Decision Matrix

```
Is the work CPU-bound?
├── YES ──► Do you need shared memory?
│           ├── YES ──► Worker Threads (SharedArrayBuffer + Atomics)
│           └── NO  ──► Worker Threads (message passing)
│
└── NO (I/O-bound, scaling HTTP) ──► Do you need process isolation?
    ├── YES ──► Cluster module (or PM2)
    └── NO  ──► Single process is likely sufficient
        (Node.js handles thousands of concurrent I/O ops on one thread)
```

| Factor | Worker Threads | Cluster |
|---|---|---|
| Type | Threads (same process) | Processes (fork) |
| Memory sharing | SharedArrayBuffer | None (IPC only) |
| Crash isolation | Low (can destabilize process) | High (isolated processes) |
| Best for | CPU computation | HTTP server scaling |
| Port sharing | N/A | Built-in |
| Startup cost | Lower | Higher |

---

## Memory Debugging Commands

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

**Runtime memory inspection** (paste into running process via inspector or code):

```typescript
const m = process.memoryUsage();
// m.rss          -- total RAM allocated to process
// m.heapTotal    -- V8 heap allocated
// m.heapUsed     -- V8 heap in use
// m.external     -- C++ objects tied to JS objects
// m.arrayBuffers -- ArrayBuffer + SharedArrayBuffer memory
```

---

## Stream Types Quick Reference

| Type | Readable | Writable | Example |
|---|---|---|---|
| Readable | Yes | No | `fs.createReadStream`, `http.IncomingMessage` |
| Writable | No | Yes | `fs.createWriteStream`, `http.ServerResponse` |
| Duplex | Yes | Yes | `net.Socket`, `crypto.createCipheriv` |
| Transform | Yes | Yes | `zlib.createGzip`, `crypto.createHash` |

### Backpressure Handling

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

---

## Common Gotchas

1. **setTimeout(0) vs setImmediate ordering**: Non-deterministic from main module;
   deterministic inside I/O callbacks (setImmediate always first).
2. **process.nextTick starvation**: Recursive nextTick blocks the entire event loop.
   Use `setImmediate` to yield between iterations.
3. **dns.lookup uses the thread pool**: `getaddrinfo` competes with `fs` for 4 default
   threads. Use `dns.resolve()` (c-ares) or increase `UV_THREADPOOL_SIZE`.
4. **Buffer.allocUnsafe leaks data**: Reuses pooled memory without zeroing. Never use
   for security-sensitive data.
5. **Unhandled rejections crash** (Node 15+): Always `.catch()` or `try/catch` with
   `await`.
6. **uncaughtException != recovery**: Process is in undefined state. Log, flush, exit.
7. **Keep-alive blocks shutdown**: `server.close()` does not close existing connections.
   Track sockets and set aggressive timeouts manually.
8. **ESM has no `__filename`/`__dirname`**: Use `fileURLToPath(import.meta.url)` and
   `dirname()`.
9. **Hidden class thrashing**: Different property insertion orders or `delete` forces
   megamorphic IC (slow). Initialize all properties consistently.
10. **Default thread pool = 4**: Set `UV_THREADPOOL_SIZE` via env var before process
    starts. Setting in code has no effect after pool init.

---

## Key Numbers to Know

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
