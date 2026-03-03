# 02 – Clustering and Scaling

## Node.js Clustering

### The Problem

Node.js runs JavaScript on a single thread. One process, one core. On a 16-core machine, you are using 6% of available CPU.

### cluster Module

The built-in `cluster` module forks the main process into multiple workers. Each worker is a separate Node.js process with its own event loop and memory.

```typescript
// src/cluster.ts
import cluster from 'node:cluster';
import { availableParallelism } from 'node:os';
import { createApp } from './app';

const numWorkers = availableParallelism();

if (cluster.isPrimary) {
  console.log(`Primary ${process.pid} starting ${numWorkers} workers`);

  for (let i = 0; i < numWorkers; i++) {
    cluster.fork();
  }

  cluster.on('exit', (worker, code, signal) => {
    console.error(`Worker ${worker.process.pid} died (${signal || code}). Restarting...`);
    cluster.fork(); // auto-restart
  });
} else {
  const app = createApp();
  app.listen(3000, () => {
    console.log(`Worker ${process.pid} listening on :3000`);
  });
}
```

**How it works:** The primary process listens on the port and distributes incoming connections to workers using round-robin (on Linux) or OS-level load balancing (on Windows).

### PM2

In production, use PM2 instead of raw `cluster`:

```javascript
// ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'api',
    script: './dist/server.js',
    instances: 'max',           // = os.availableParallelism()
    exec_mode: 'cluster',
    max_memory_restart: '500M',
    env_production: {
      NODE_ENV: 'production',
    },
    // Graceful shutdown
    kill_timeout: 5000,
    listen_timeout: 10000,
    // Zero-downtime reload
    wait_ready: true,
    shutdown_with_message: true,
  }],
};
```

```bash
# PM2 commands
pm2 start ecosystem.config.cjs --env production
pm2 reload api          # zero-downtime restart
pm2 scale api +2        # add 2 more workers
pm2 monit               # real-time dashboard
pm2 logs api --lines 100  # tail logs
pm2 save && pm2 startup   # persist across reboots
```

### Graceful Shutdown

```typescript
// Graceful shutdown in your app
process.on('SIGINT', async () => {
  console.log('Graceful shutdown...');
  server.close();                     // stop accepting new connections
  await drainConnections();           // finish in-flight requests
  await pool.end();                   // close DB pool
  await redis.quit();                 // close Redis
  process.exit(0);
});

// Signal PM2 that app is ready
if (process.send) process.send('ready');
```

### Sticky Sessions

Problem: WebSocket connections and session-based auth break with round-robin load balancing because subsequent requests may land on a different worker.

Solution: Sticky sessions route requests from the same client to the same worker, typically by hashing the client IP or a cookie.

```typescript
// With @socket.io/sticky and @socket.io/cluster-adapter
import { createServer } from 'http';
import { setupPrimary, setupWorker } from '@socket.io/sticky';
import { createAdapter } from '@socket.io/cluster-adapter';

if (cluster.isPrimary) {
  const httpServer = createServer();
  setupPrimary(httpServer, { loadBalancingMethod: 'least-connection' });
  httpServer.listen(3000);

  for (let i = 0; i < numWorkers; i++) cluster.fork();
} else {
  const httpServer = createServer(app);
  const io = new Server(httpServer);
  io.adapter(createAdapter());
  setupWorker(io);
}
```

### Shared State Limitations

Each worker has its own memory. You **cannot** share state between workers via variables.

| What breaks | Why | Solution |
|-------------|-----|---------|
| In-memory sessions | Each worker has different sessions | Redis session store |
| In-memory caches | Cache misses on different workers | Redis / Memcached |
| Rate limiting counters | Each worker counts independently | Redis-backed rate limiter |
| WebSocket rooms | Broadcast only reaches one worker | Redis adapter / cluster adapter |
| Singleton patterns | Multiple instances exist | External coordination (Redis, DB) |

**Interview answer:** "Clustering gives you multi-core utilization but requires externalizing all state. If your app stores anything in memory that matters across requests, it needs to move to Redis or a database."

---

## Horizontal Scaling

### Stateless Design

The first rule of horizontal scaling: **any request can be handled by any instance**.

```typescript
// STATEFUL (breaks with multiple instances)
const sessions = new Map<string, Session>();

app.post('/login', (req, res) => {
  const session = createSession(req.body);
  sessions.set(session.id, session); // stored in-memory
  res.cookie('sid', session.id);
});

// STATELESS (scales horizontally)
app.post('/login', async (req, res) => {
  const session = createSession(req.body);
  await redis.set(`session:${session.id}`, JSON.stringify(session), 'EX', 86400);
  res.cookie('sid', session.id);
});
```

### Shared-Nothing Architecture

Each instance has:
- Its own process memory (no shared state)
- Its own local filesystem (no shared files)
- Connection to shared services (Redis, database, S3)

File uploads go to S3, not local disk. Temp files are cleaned up in the same request. Configuration comes from environment variables, not local files.

---

## Load Testing

### k6

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const latency = new Trend('api_latency');

export const options = {
  stages: [
    { duration: '1m', target: 100 },    // ramp up
    { duration: '5m', target: 100 },    // sustain
    { duration: '1m', target: 0 },      // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<300', 'p(99)<500'],
    errors: ['rate<0.01'],
  },
};

export default function () {
  group('API Endpoints', () => {
    const start = Date.now();
    const res = http.get('http://localhost:3000/api/users', {
      headers: { Authorization: `Bearer ${__ENV.TOKEN}` },
    });
    latency.add(Date.now() - start);

    const success = check(res, {
      'status 200': (r) => r.status === 200,
      'has users': (r) => JSON.parse(r.body).data.length > 0,
    });
    errorRate.add(!success);
  });

  sleep(0.5);
}
```

### Interpreting Load Test Results

```
     scenarios: (100.00%) 1 scenario, 100 max VUs, 7m30s max duration

     http_req_duration..............: avg=45.2ms  min=12ms  med=38ms  max=2.1s   p(90)=89ms   p(95)=145ms
     http_req_failed................: 0.23%  ✓ 47  ✗ 20,423
     http_reqs......................: 20470  48.7/s
```

**What to look for:**

| Metric | Healthy | Investigate |
|--------|---------|------------|
| p95 vs avg | <3x avg | >5x avg (tail latency problem) |
| p99 vs p95 | <2x p95 | >3x p95 (outlier issues) |
| Error rate | <0.1% | >1% |
| RPS | Stable throughout | Declining during sustained load |
| max | <10x avg | >100x avg (GC pauses, connection limits) |

### Performance Benchmarking Checklist

Before load testing:
- [ ] Application built in production mode (`NODE_ENV=production`)
- [ ] Debug logging disabled or set to `warn`/`error`
- [ ] Source maps disabled or external
- [ ] Database has representative data volume
- [ ] Connection pools sized appropriately
- [ ] Redis is running (not falling through to DB on every request)
- [ ] No `console.log` in hot paths

During load testing:
- [ ] Monitor: CPU, memory, event loop delay, DB connections, Redis connections
- [ ] Watch for: linear memory growth, connection pool exhaustion, error rate spikes
- [ ] Record: p50, p95, p99 latency at each concurrency level
- [ ] Test scenarios: ramp-up, sustained, spike, soak (long duration)

### Red Flags

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| p99 >> p95 | GC pauses, lock contention | Reduce allocation rate, tune GC |
| Latency grows with load | Connection pool exhaustion | Increase pool, add caching |
| Memory grows linearly | Memory leak | Heap snapshot comparison |
| CPU at 100% one core | Single-threaded bottleneck | Cluster mode, worker threads |
| Sudden error spike | Connection limit hit | Pool limits, circuit breaker |
| Throughput plateaus | Event loop saturation | Offload CPU work, scale out |

---

## HTTP Keep-Alive and Connection Pooling

### HTTP Keep-Alive

Node.js `http.Agent` reuses TCP connections:

```typescript
import { Agent } from 'node:http';

const agent = new Agent({
  keepAlive: true,
  maxSockets: 50,        // per host
  maxFreeSockets: 10,    // idle connections to keep
  timeout: 60_000,       // socket timeout
});

// Use with fetch (Node 18+)
const res = await fetch('http://service.internal/api', {
  dispatcher: agent,
});

// Or with undici (more control)
import { Pool } from 'undici';
const pool = new Pool('http://service.internal', {
  connections: 50,
  pipelining: 1,
  keepAliveTimeout: 60_000,
});
```

### Database Connection Pools

```typescript
// PostgreSQL with pg
import pg from 'pg';

const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  min: 5,           // minimum idle connections
  max: 20,          // maximum connections
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 5_000,
  allowExitOnIdle: false,
});

pool.on('error', (err) => {
  console.error('Unexpected pool error', err);
});

function getPoolStats() {
  return {
    total: pool.totalCount,
    idle: pool.idleCount,
    waiting: pool.waitingCount,
  };
}
```

**Sizing rule of thumb:** `max connections = (number of cores * 2) + number of disks`. For most setups, 20-50 is the sweet spot. Too many connections actually degrade Postgres performance.

---

## Key Metrics to Capture

| Metric | Tool | Command |
|--------|------|---------|
| HTTP latency | k6 | `k6 run load-test.js` |
| RPS throughput | k6 | Built into output |
| Event loop delay | Node.js | `monitorEventLoopDelay()` |
| Heap size | Node.js | `process.memoryUsage().heapUsed` |
| DB query time | APM / pg_stat | `EXPLAIN ANALYZE` for slow queries |
| Connection pool | pg Pool | `pool.totalCount`, `pool.waitingCount` |
| Redis latency | redis-cli | `redis-cli --latency` |
| System | OS tools | `htop`, `vmstat`, `iostat` |

---

## V8 Optimization Tips

### Monomorphic Functions

V8 optimizes functions based on the types they receive. A function that always receives the same shape of object is **monomorphic** and gets the fastest generated code.

```typescript
// MONOMORPHIC: always receives { x: number, y: number }
function distance(point: { x: number; y: number }) {
  return Math.sqrt(point.x ** 2 + point.y ** 2);
}

// POLYMORPHIC: receives different shapes — V8 gives up on optimization
function getValue(obj: Record<string, unknown>) {
  return obj.value;
}

getValue({ value: 1 });           // shape 1
getValue({ value: 'hello' });     // shape 2
getValue({ value: 1, extra: 2 }); // shape 3: different hidden class
```

### Hidden Classes

V8 assigns hidden classes to objects based on their property layout. Objects with the same properties added in the same order share a hidden class.

```typescript
// GOOD: same property order = same hidden class
function createPoint(x: number, y: number) {
  return { x, y }; // always {x, y} in that order
}

// GOOD: always initialize all properties, even if undefined
function createPointGood(x: number, y: number, label?: string) {
  return { x, y, label: label ?? undefined };
}
```

### Deoptimization Traps

| Trap | Example | Fix |
|------|---------|-----|
| Type change | Variable changes from number to string | Consistent types |
| Hidden class change | Adding properties after construction | Initialize all props upfront |
| `arguments` object | Using `arguments` in optimized function | Use rest params |
| `try/catch` in hot loop | Try-catch in tight loop (older V8) | Move try-catch outside loop |
| `delete` on object | `delete obj.prop` | Set to `undefined` |
| Megamorphic access | 4+ different object shapes at same call site | Normalize shapes |

### Detecting Deoptimizations

```bash
# Run with trace-deopt
node --trace-deopt dist/server.js 2>&1 | grep "deopt"

# More detailed
node --trace-opt --trace-deopt dist/server.js

# Check optimization status
node --allow-natives-syntax -e "
  function hot(x) { return x + 1; }
  for (let i = 0; i < 100000; i++) hot(i);
  %OptimizeFunctionOnNextCall(hot);
  hot(1);
  console.log(%GetOptimizationStatus(hot));
"
```

Optimization status codes: 1 = optimized, 2 = not optimized, 3 = always optimized, 4 = never optimized, 6 = maybe deoptimized.

---

## Zero-Copy Operations

```typescript
// ZERO-COPY: shares memory with the ArrayBuffer
const arrayBuffer = new ArrayBuffer(1024);
const buf = Buffer.from(arrayBuffer);     // no copy!

// ZERO-COPY: slice shares memory
const original = Buffer.alloc(1024);
const slice = original.subarray(0, 512); // no copy, same memory

// Transferable objects with worker threads (zero-copy, original becomes unusable)
const arrayBuffer2 = new ArrayBuffer(1024 * 1024);
worker.postMessage({ data: arrayBuffer2 }, [arrayBuffer2]);
// arrayBuffer2.byteLength is now 0 — ownership transferred
```

---

## Serverless Considerations

### Cold Start Minimization

| Factor | Impact on Cold Start |
|--------|---------------------|
| Runtime | Node.js ~200-400ms (fast), Java ~2-5s (slow) |
| Package size | Larger bundles = longer init |
| SDK initialization | AWS SDK, DB connections add 100-300ms each |
| VPC | Adds 1-2s (ENI attachment) |
| Provisioned concurrency | Eliminates cold start (at cost) |

```typescript
// 1. Lazy initialization — only connect when needed
let dbPool: Pool | null = null;

function getDb(): Pool {
  if (!dbPool) {
    dbPool = new Pool({
      connectionString: process.env.DATABASE_URL,
      max: 1,  // Lambda only needs 1 connection
    });
  }
  return dbPool;
}

// 2. SDK client reuse (outside handler)
import { S3Client } from '@aws-sdk/client-s3';
const s3 = new S3Client({}); // initialized once, reused across invocations

export const handler = async (event: APIGatewayProxyEvent) => {
  const db = getDb();
  // ... handler logic
};
```

```bash
# 3. Bundle with esbuild for smaller package
esbuild src/handler.ts \
  --bundle \
  --platform=node \
  --target=node20 \
  --outfile=dist/handler.js \
  --external:@aws-sdk/* \   # AWS SDK v3 is in Lambda runtime
  --minify
```

### Edge Runtime Limitations

Edge runtimes (Cloudflare Workers, Vercel Edge Functions) run a restricted subset:

| Feature | Available | Notes |
|---------|-----------|-------|
| `fetch` | Yes | Native Web API |
| `fs` | No | No filesystem access |
| `net`/`dgram` | No | No raw sockets |
| `child_process` | No | No process spawning |
| Execution time | 10-50ms typical | Hard limits vary |
| Memory | 128MB typical | Much less than Lambda |

**Works well at the edge**: JWT validation, routing, A/B testing, geolocation responses, rate limiting, API response transformation.

**Does not work at the edge**: Database connections (no TCP; use HTTP-based DB proxies), heavy computation, large payloads, long-running processes.

**Common mistake with serverless cold starts:** Initializing all dependencies eagerly in module scope. In a Lambda function, every `import` at the top level runs during cold start, even if the handler only uses a subset. Use lazy initialization (as shown above) for expensive clients like database pools and SDK clients. Another pitfall is using a large deployment package — tree-shake with esbuild and externalize the AWS SDK (it is already in the Lambda runtime) to minimize cold start time.

---

## gRPC vs REST for Internal Services

| Aspect | gRPC | REST (JSON) |
|--------|------|-------------|
| Serialization | Protobuf (binary, ~10x smaller) | JSON (text, human-readable) |
| Transport | HTTP/2 (always) | HTTP/1.1 or HTTP/2 |
| Streaming | Bidirectional native | SSE or WebSocket bolt-on |
| Code generation | Yes (type-safe clients) | OpenAPI (optional) |
| Browser support | Via grpc-web proxy | Native |
| Debugging | Harder (binary protocol) | Easy (curl, browser) |

**Interview point:** "HTTP/3 eliminates TCP head-of-line blocking at the transport layer. HTTP/2 solved it at the HTTP layer but still suffers when a TCP packet is lost. QUIC solves this by making each stream independent at the transport level."

## Related Reading

- **Clustering and PM2** solve the single-threaded limitation covered in [02 – Threading and Process Management](../02-node-runtime/02-threading-and-process-management.md#cluster-module) — that file covers the runtime internals while this one covers production scaling patterns.
- **Shared state limitations and Redis externalization** connect to the Redis caching patterns in [08 – Caching and Redis](./01-caching-and-redis.md) — every item in the "what breaks" table is solved by a pattern in that file.
- **Stateless design for horizontal scaling** enables the session management strategies in [05 – Session Management and Validation](../05-auth-security/02-session-management-and-validation.md) and the multi-tenancy patterns in [06 – Advanced Patterns and Multi-Tenancy](../06-database-patterns/03-advanced-patterns-and-multi-tenancy.md).
- **Load testing with k6** is the production validation of the performance optimizations here — see also the load testing patterns in [07 – Advanced Testing Patterns](../07-testing/03-advanced-testing-patterns.md#performance-and-load-testing) for test authoring guidance.
- **Database connection pooling** relates directly to the pool configuration in [06 – Queries, Transactions, and Optimization](../06-database-patterns/02-queries-transactions-and-optimization.md) and the connection pool exhaustion chaos tests in [07 – Advanced Testing Patterns](../07-testing/03-advanced-testing-patterns.md#database-chaos).
- **V8 optimization tips (monomorphic functions, hidden classes)** build on the V8 runtime internals in [02 – Event Loop and Task Queues](../02-node-runtime/01-event-loop-and-task-queues.md).
- **Graceful shutdown** is a cross-cutting concern also covered in [04 – Advanced GraphQL Patterns](../04-graphql/02-advanced-graphql-patterns.md#graceful-shutdown) and [09 – Clean Architecture and DDD](../09-architecture-patterns/01-clean-architecture-and-ddd.md#error-handling-architecture).

**When to use gRPC vs REST for internal services:** Use gRPC when you need high-throughput, low-latency communication between backend services, especially when bidirectional streaming is required (e.g., real-time data feeds between services). Stick with REST when the consumer is a browser or a team that values debuggability over raw performance. A common mistake is adopting gRPC for all internal communication when most services are simple request/response CRUD — the complexity of maintaining `.proto` files and gRPC tooling only pays off at high traffic volumes or when streaming is a core requirement.
