# 02 — Worker Threads, Cluster, child_process, and IPC

> Assumes event loop fundamentals from file 01. Focuses on parallelism, process isolation, and inter-process communication patterns.

---

## 1. Worker Threads

Each worker runs its own V8 isolate and event loop within the same process.

### 1.1 Communication Patterns

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

### 1.2 Atomics API Essentials

```typescript
Atomics.store(typedArray, index, value);     // atomic write
Atomics.load(typedArray, index);             // atomic read
Atomics.add(typedArray, index, value);       // atomic add
Atomics.compareExchange(typedArray, index, expected, replacement);
Atomics.wait(typedArray, index, value);      // block until changed (workers only)
Atomics.notify(typedArray, index, count);    // wake waiting threads
```

### 1.3 Transferable Objects

```typescript
const { port1, port2 } = new MessageChannel();
const largeBuffer = new ArrayBuffer(1024 * 1024);
port1.postMessage(largeBuffer, [largeBuffer]); // zero-copy transfer
// largeBuffer.byteLength === 0 after transfer (neutered)
```

### 1.4 Worker Threads vs Cluster Decision Matrix (Cheat Sheet)

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

## 2. Cluster Module

### 2.1 Fork Model and Load Distribution

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

### 2.2 IPC and Sticky Sessions

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

## 3. child_process

### 3.1 Four Methods at a Glance

| Method | Use Case | Async |
|---|---|---|
| `exec` | Run shell commands, buffered output | Callback |
| `execFile` | Run executables without shell, buffered | Callback |
| `spawn` | Long-running processes, streaming I/O | EventEmitter |
| `fork` | Spawn a new Node.js process with IPC channel | EventEmitter + IPC |

### 3.2 spawn (Streaming)

```typescript
import { spawn } from 'child_process';

const child = spawn('node', ['worker.js']);

child.stdout.on('data', (data: Buffer) => process.stdout.write(data));
child.stderr.on('data', (data: Buffer) => process.stderr.write(data));
child.on('close', (code) => console.log(`Child exited with code ${code}`));
child.on('error', (err) => console.error('Failed to start child:', err));
```

### 3.3 fork (IPC)

```typescript
import { fork } from 'child_process';

const child = fork('./compute-worker.js');

child.on('message', (msg: any) => {
  console.log('Result from worker:', msg);
});
child.send({ task: 'fibonacci', n: 40 });
```

### 3.4 exec vs spawn

```typescript
import { exec, execFile } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// exec: runs in shell, vulnerable to injection if user input in command
const { stdout } = await execAsync('ls -la /tmp');

// execFile: no shell, safer for user-influenced executables
const execFileAsync = promisify(execFile);
const { stdout: out } = await execFileAsync('ls', ['-la', '/tmp']);
```

**Never use `exec` with unsanitized user input** — shell injection is trivial. Use `execFile` or `spawn` with argument arrays.

### 3.5 Detached Processes

```typescript
import { spawn } from 'child_process';
import { openSync } from 'fs';

const out = openSync('/var/log/daemon.log', 'a');
const err = openSync('/var/log/daemon-err.log', 'a');

const daemon = spawn('node', ['daemon.js'], {
  detached: true,
  stdio: ['ignore', out, err],
});

daemon.unref(); // Parent can exit independently
```

---

## 4. Process Lifecycle and Graceful Shutdown

### 4.1 Signals and Error Handlers

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

### 4.2 Graceful Shutdown Pattern

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

### 4.3 What Keeps the Process Alive

Active **refs**: open servers, active timers, file watchers, child processes, TCP connections. Call `.unref()` on a timer/handle so it won't prevent exit.

---

## 5. V8 Engine Internals (Deep Dive)

### 5.1 The Compilation Pipeline

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

**Ignition** compiles JS to compact register-based bytecode. Every operation records **type feedback** into feedback vectors — what types were observed at each call site.

**TurboFan** uses that feedback for speculative optimization: assumes observed types will continue, inserts type guards, deoptimizes if violated. Key optimizations: function inlining, escape analysis (stack-allocate non-escaping objects), loop-invariant code motion, dead code elimination.

### 5.2 Hidden Classes (Maps)

V8 assigns a **hidden class** (internally "Map") to every object. Objects with the same properties added in the same order share a hidden class, enabling fast fixed-offset property access.

```typescript
const a = { x: 1, y: 2 }; // hidden class C0 -> C1(x) -> C2(x,y)
const b = { x: 3, y: 4 }; // same transition chain -- shares C2
const c = { y: 2, x: 1 }; // DIFFERENT order = different hidden class

// delete forces dictionary mode (hash table) -- significantly slower
delete a.x; // a transitions to slow properties
```

### 5.3 Inline Caches (ICs)

Each property access site caches the hidden class and property offset from its last lookup:

- **Monomorphic**: 1 hidden class seen. Single comparison + direct offset load. Fastest.
- **Polymorphic**: 2-4 classes. Linear search through cached entries.
- **Megamorphic**: 5+ classes. Falls back to generic hash-table lookup.

```typescript
// Monomorphic -- all objects same shape, IC stays fast
function getX(p: { x: number; y: number }) { return p.x; }

// Megamorphic -- wildly different shapes at same call site
function getValue(obj: any) { return obj.value; } // IC degrades
```

### 5.4 Deoptimization

TurboFan discards optimized code and returns to Ignition when assumptions break. Common triggers: type change, hidden class mismatch, out-of-bounds array access, Smi overflow. Repeated deopts mark a function as "don't optimize" permanently.

```bash
node --trace-opt --trace-deopt app.js
# [marking <JSFunction add> for optimization]
# [deoptimizing (DEOPT eager): reason: not a Smi]
```

---

## 6. N-API and Native Addons (Deep Dive)

### 6.1 When to Write Native Addons

- CPU-intensive computation (image processing, ML inference)
- Wrapping existing C/C++ libraries
- Hardware access or system calls not exposed by Node.js

**Alternatives**: WebAssembly (portable, sandboxed), Rust via `napi-rs`, worker threads.

### 6.2 N-API Stability

N-API provides a stable ABI across Node.js versions. Addons compiled against N-API v8 work on Node.js 12-22+ without recompilation.

### 6.3 Thread-Safe Functions

For calling back into JS from native threads:

```cpp
auto tsfn = Napi::ThreadSafeFunction::New(env, jsCallback, "Worker", 0, 1);
// From any native thread:
tsfn.BlockingCall([](Napi::Env env, Napi::Function cb) {
  cb.Call({Napi::String::New(env, "data from native thread")});
});
```

---

## 7. Module System Internals (Deep Dive)

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

Every CJS module is wrapped: `(function(exports, require, module, __filename, __dirname) { ... })`. This is why those identifiers exist — they are function parameters, not globals.

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

CJS: `require.cache` keyed by resolved absolute path. Deletable (fragile hot-reload). ESM: Cached by URL. No public API to clear. Intentionally evaluated once.
