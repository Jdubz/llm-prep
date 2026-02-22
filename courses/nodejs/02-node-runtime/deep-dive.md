# Module 02 Deep Dive: V8 Internals, libuv, Diagnostics, and Module Systems

This supplement targets the esoteric knowledge that separates staff engineers from
senior engineers in interviews. If the README is "what you must know," this document
is "what makes interviewers say 'wow.'"

---

## 1. V8 Engine Internals

### 1.1 The Compilation Pipeline

```
JavaScript Source
      │
      ▼
   Parser ──────► AST (Abstract Syntax Tree)
      │
      ▼
   Ignition ────► Bytecode (register-based VM, collects type feedback)
      │
      ▼
   TurboFan ───► Optimized Machine Code
      │
      │  [deoptimization if assumptions break]
      ▼
   Back to Ignition bytecode
```

**Ignition** compiles JS to compact register-based bytecode. Every operation records
**type feedback** into feedback vectors -- what types were observed at each call site.

**TurboFan** uses that feedback for speculative optimization: assumes observed types
will continue, inserts type guards, deoptimizes if violated. Key optimizations: function
inlining, escape analysis (stack-allocate non-escaping objects), loop-invariant code
motion, dead code elimination.

### 1.2 Hidden Classes (Maps)

V8 assigns a **hidden class** (internally "Map") to every object. Objects with the same
properties added in the same order share a hidden class, enabling fast fixed-offset
property access.

```typescript
const a = { x: 1, y: 2 }; // hidden class C0 -> C1(x) -> C2(x,y)
const b = { x: 3, y: 4 }; // same transition chain -- shares C2
const c = { y: 2, x: 1 }; // DIFFERENT order = different hidden class

// delete forces dictionary mode (hash table) -- significantly slower
delete a.x; // a transitions to slow properties
```

### 1.3 Inline Caches (ICs)

Each property access site caches the hidden class and property offset from its last
lookup:

- **Monomorphic**: 1 hidden class seen. Single comparison + direct offset load. Fastest.
- **Polymorphic**: 2-4 classes. Linear search through cached entries.
- **Megamorphic**: 5+ classes. Falls back to generic hash-table lookup.

```typescript
// Monomorphic -- all objects same shape, IC stays fast
function getX(p: { x: number; y: number }) { return p.x; }

// Megamorphic -- wildly different shapes at same call site
function getValue(obj: any) { return obj.value; } // IC degrades
```

### 1.4 Deoptimization

TurboFan discards optimized code and returns to Ignition when assumptions break.
Common triggers: type change, hidden class mismatch, out-of-bounds array access,
Smi overflow. Repeated deopts mark a function as "don't optimize" permanently.

```bash
node --trace-opt --trace-deopt app.js
# [marking <JSFunction add> for optimization]
# [deoptimizing (DEOPT eager): reason: not a Smi]
```

---

## 2. libuv Internals

### 2.1 Platform-Specific I/O Multiplexing

| Platform | Mechanism | Model |
|---|---|---|
| Linux | `epoll` | Readiness-based, O(1) |
| macOS/BSD | `kqueue` | Readiness-based, supports fs events |
| Windows | IOCP | Completion-based (fundamentally different) |

### 2.2 epoll (Linux)

```c
int epfd = epoll_create1(0);
struct epoll_event ev = { .events = EPOLLIN | EPOLLOUT, .data.fd = sock_fd };
epoll_ctl(epfd, EPOLL_CTL_ADD, sock_fd, &ev);
// Poll phase: block here waiting for I/O
int n = epoll_wait(epfd, events, MAX_EVENTS, timeout);
// Dispatch callbacks for ready file descriptors
```

Network I/O is fully async at the OS level via epoll -- no thread pool needed. File
system operations lack a mature async kernel interface on Linux (io_uring is changing
this), so libuv delegates them to the thread pool.

### 2.3 Handles vs Requests

**Handles**: Long-lived objects (tcp, timer, pipe, signal). Init -> start -> stop -> close.
**Requests**: Short-lived operations (write, connect, dns, fs). Submit -> callback.

### 2.4 io_uring (Linux 5.1+)

True kernel-level async file I/O via submission/completion queues in shared memory.
libuv is experimenting with io_uring support, which would eliminate the thread pool for
file operations on modern kernels.

---

## 3. N-API and Native Addons

### 3.1 When to Write Native Addons

- CPU-intensive computation (image processing, ML inference)
- Wrapping existing C/C++ libraries
- Hardware access or system calls not exposed by Node.js

**Alternatives**: WebAssembly (portable, sandboxed), Rust via `napi-rs`, worker threads.

### 3.2 N-API Stability

N-API provides a stable ABI across Node.js versions. Addons compiled against N-API v8
work on Node.js 12-22+ without recompilation.

### 3.3 Thread-Safe Functions

For calling back into JS from native threads:

```cpp
auto tsfn = Napi::ThreadSafeFunction::New(env, jsCallback, "Worker", 0, 1);
// From any native thread:
tsfn.BlockingCall([](Napi::Env env, Napi::Function cb) {
  cb.Call({Napi::String::New(env, "data from native thread")});
});
```

---

## 4. Diagnostic Tools

### 4.1 Inspector Protocol

```bash
node --inspect app.js          # Chrome DevTools at chrome://inspect
node --inspect-brk app.js     # Break on first line
```

Capabilities: CPU profiling (flame charts), heap snapshots, live debugging, memory
allocation timeline.

### 4.2 V8 Profiling

```bash
node --prof app.js                         # Generate V8 tick log
node --prof-process isolate-*.log > out.txt # Human-readable analysis
```

Shows statistical profiling ticks, JIT events, and bottom-up heavy profile.

### 4.3 Heap Snapshots

```typescript
import v8 from 'v8';
v8.writeHeapSnapshot(); // Writes .heapsnapshot file, loadable in Chrome DevTools

import inspector from 'inspector';
const session = new inspector.Session();
session.connect();
session.post('HeapProfiler.takeHeapSnapshot');
```

### 4.4 Core Dumps

```bash
ulimit -c unlimited
node --abort-on-uncaught-exception app.js
# Analyze with llnode:
lldb -c core.12345
(lldb) v8 bt        # JavaScript backtrace
(lldb) v8 inspect   # Inspect JS objects
```

### 4.5 Clinic.js

```bash
npx clinic flame -- node app.js       # CPU flame graph
npx clinic bubbleprof -- node app.js  # Async flow visualization
npx clinic doctor -- node app.js      # Event loop + GC + I/O health check
```

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

## 6. async_hooks and AsyncLocalStorage

### 6.1 async_hooks

Tracks async resource lifetimes. Every async operation gets an `asyncId` and
`triggerAsyncId` (parent).

```typescript
import async_hooks from 'async_hooks';
async_hooks.createHook({
  init(asyncId, type, triggerAsyncId) { /* resource created */ },
  before(asyncId) { /* callback about to fire */ },
  after(asyncId)  { /* callback completed */ },
  destroy(asyncId) { /* resource destroyed */ },
}).enable();
```

**Warning**: Significant overhead. `init` fires for every Promise. Prefer
`AsyncLocalStorage` in production.

### 6.2 AsyncLocalStorage

Context propagation across async boundaries -- Node.js equivalent of thread-local
storage.

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

Node.js 20+ uses a synchronous propagation implementation (3-5x faster than earlier
async_hooks-based approach). Prefer `als.run()` (scoped) over `als.enterWith()` (mutates
current context).

---

## 7. Module System Internals

### 7.1 CJS Resolution Algorithm

```
require(X) from path Y:
1. Core module? Return cached.
2. Starts with './', '../', '/'?
   → LOAD_AS_FILE(Y + X): try X, X.js, X.json, X.node
   → LOAD_AS_DIRECTORY(Y + X): package.json "main", index.js
3. Else: walk up node_modules dirs from Y, try file then directory at each.
4. Throw MODULE_NOT_FOUND.
```

Every CJS module is wrapped: `(function(exports, require, module, __filename, __dirname) { ... })`.
This is why those identifiers exist -- they are function parameters, not globals.

### 7.2 CJS Circular Dependencies

CJS returns a **partial** export when a circular require is encountered:

```typescript
// a.js: exports.done = false; const b = require('./b'); exports.done = true;
// b.js: exports.done = false; const a = require('./a'); // gets {done: false} (partial!)
```

### 7.3 ESM Three-Phase Loading

```
1. CONSTRUCTION: Parse, find import/export declarations, build Module Record
2. INSTANTIATION: Allocate export memory, link imports as live bindings (references)
3. EVALUATION: Execute code depth-first post-order; fill export values
```

### 7.4 CJS vs ESM Key Differences

| Aspect | CJS | ESM |
|---|---|---|
| Loading | Synchronous | Async (three-phase) |
| Exports | Value copies | Live bindings (references) |
| Auto extensions | `.js`, `.json`, `.node` | None -- explicit paths required |
| `this` at top level | `exports` | `undefined` |
| `__filename` | Available | Use `import.meta.url` |
| Top-level await | No | Yes |
| Tree shaking | Not possible | Possible (static analysis) |
| Package entry | `"main"` field | `"exports"` field (conditional) |

### 7.5 Conditional Exports

```json
{
  "exports": {
    ".": {
      "import": { "types": "./dist/index.d.ts", "default": "./dist/index.mjs" },
      "require": { "types": "./dist/index.d.cts", "default": "./dist/index.cjs" }
    }
  }
}
```

### 7.6 Interop

```typescript
import cjs from './legacy.cjs';              // default = module.exports
const esm = await import('./modern.mjs');    // dynamic import in CJS
import { createRequire } from 'module';
const require = createRequire(import.meta.url); // require() in ESM
```

### 7.7 Caching

CJS: `require.cache` keyed by resolved absolute path. Deletable (fragile hot-reload).
ESM: Cached by URL. No public API to clear. Intentionally evaluated once.
