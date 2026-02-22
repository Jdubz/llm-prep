# Module 08: Performance & Scaling

> **You will be asked about this.** Every senior Node.js interview includes at least one question about scaling, caching, or debugging a memory leak. This module gives you the vocabulary and the depth to answer with authority.

---

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
pm2 start ecosystem.config.cjs --env production
pm2 reload api   # zero-downtime restart
pm2 monit        # real-time monitoring
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

## Caching with Redis

### Cache-Aside (Lazy Loading)

The most common pattern. Application checks cache first, falls back to database, then populates cache.

```typescript
import Redis from 'ioredis';

const redis = new Redis(process.env.REDIS_URL);

async function getUser(id: string): Promise<User> {
  const cacheKey = `user:${id}`;

  // 1. Check cache
  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);

  // 2. Cache miss — query database
  const user = await db.query.users.findFirst({ where: eq(users.id, id) });
  if (!user) throw new NotFoundError('User not found');

  // 3. Populate cache
  await redis.set(cacheKey, JSON.stringify(user), 'EX', 3600); // 1 hour TTL

  return user;
}
```

**Trade-offs:**
- Cache misses hit the database (cold start penalty)
- Stale data possible within TTL window
- Simple to implement, easy to reason about

### Write-Through

Application writes to cache and database simultaneously. Cache is always fresh.

```typescript
async function updateUser(id: string, data: Partial<User>): Promise<User> {
  // Write to DB
  const user = await db
    .update(users)
    .set({ ...data, updatedAt: new Date() })
    .where(eq(users.id, id))
    .returning()
    .then(([u]) => u);

  // Write to cache (same transaction boundary ideally)
  await redis.set(`user:${id}`, JSON.stringify(user), 'EX', 3600);

  return user;
}
```

**Trade-offs:**
- Cache is always fresh
- Write latency increases (two writes per operation)
- Cache may contain data that is never read (waste)

### Cache Invalidation

The two hard problems in computer science: cache invalidation, naming things, and off-by-one errors.

**Pattern 1: TTL-based expiry** (simplest)

```typescript
await redis.set(key, value, 'EX', 3600); // expires in 1 hour
```

**Pattern 2: Explicit invalidation on write**

```typescript
async function updateUser(id: string, data: Partial<User>) {
  await db.update(users).set(data).where(eq(users.id, id));
  await redis.del(`user:${id}`);         // invalidate specific key
  await redis.del('users:list:*');        // pattern invalidation (expensive)
}
```

**Pattern 3: Versioned keys**

```typescript
async function getUserList(filters: Filters): Promise<User[]> {
  const version = await redis.get('users:version') ?? '0';
  const cacheKey = `users:list:${version}:${hashFilters(filters)}`;

  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);

  const users = await db.query.users.findMany(/* ... */);
  await redis.set(cacheKey, JSON.stringify(users), 'EX', 3600);
  return users;
}

async function onUserChange() {
  await redis.incr('users:version'); // all old caches naturally expire
}
```

### Pub/Sub for Cache Busting

In a multi-instance deployment, one instance invalidates cache but others still have stale local caches (if you use an in-memory layer).

```typescript
// Publisher (on write)
async function onUserUpdated(userId: string) {
  await redis.del(`user:${userId}`);
  await redis.publish('cache:invalidate', JSON.stringify({
    type: 'user',
    id: userId,
  }));
}

// Subscriber (all instances)
const subscriber = new Redis(process.env.REDIS_URL);
subscriber.subscribe('cache:invalidate');
subscriber.on('message', (_channel, message) => {
  const { type, id } = JSON.parse(message);
  localCache.delete(`${type}:${id}`); // clear in-memory LRU
});
```

### Redis Data Structures for Caching Patterns

| Structure | Use Case | Example |
|-----------|----------|---------|
| String | Simple key-value cache | `SET user:123 '{...}'` |
| Hash | Object with partial updates | `HSET user:123 name Alice email alice@...` |
| Sorted Set | Leaderboards, rate limiting | `ZADD leaderboard 100 user:123` |
| Set | Unique collections, tagging | `SADD user:123:roles admin editor` |
| List | Recent items, activity feeds | `LPUSH recent:orders order:456` |
| Stream | Event log, message queue | `XADD events * type order.created` |
| HyperLogLog | Approximate unique counts | `PFADD daily:visitors user:123` |

---

## Streaming

### HTTP Streaming Responses

For large datasets, stream instead of buffering the entire response:

```typescript
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

app.get('/export/users', async (req, res) => {
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Transfer-Encoding', 'chunked');

  const dbStream = db.query.users
    .findMany()
    .stream(); // Drizzle/Knex streaming query

  const csvTransform = new Transform({
    objectMode: true,
    transform(user, _enc, cb) {
      cb(null, `${user.id},${user.name},${user.email}\n`);
    },
  });

  // Write header
  res.write('id,name,email\n');

  await pipeline(dbStream, csvTransform, res);
});
```

### Server-Sent Events (SSE)

Unidirectional server-to-client streaming over HTTP. Simpler than WebSockets when you only need server push.

```typescript
app.get('/events', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  const sendEvent = (event: string, data: unknown) => {
    res.write(`event: ${event}\n`);
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  // Send heartbeat every 30s to keep connection alive
  const heartbeat = setInterval(() => {
    res.write(': heartbeat\n\n');
  }, 30_000);

  // Subscribe to events
  const unsubscribe = eventBus.on('order:updated', (order) => {
    sendEvent('order:updated', order);
  });

  req.on('close', () => {
    clearInterval(heartbeat);
    unsubscribe();
  });
});
```

### WebSocket Scaling

WebSockets are stateful. Scaling across multiple servers requires a message broker:

```typescript
import { Server } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { createClient } from 'redis';

const pubClient = createClient({ url: process.env.REDIS_URL });
const subClient = pubClient.duplicate();

await Promise.all([pubClient.connect(), subClient.connect()]);

const io = new Server(httpServer);
io.adapter(createAdapter(pubClient, subClient));

// Now io.emit() reaches ALL clients across ALL servers
io.emit('notification', { message: 'System update' });
```

### Backpressure Handling

When a producer generates data faster than the consumer can process it:

```typescript
import { Readable, Writable } from 'node:stream';

const source = new Readable({
  read() {
    // Generate data
    const canContinue = this.push(generateChunk());
    if (!canContinue) {
      // Downstream is full — stop producing until drain
      // The stream will call read() again when ready
    }
  },
});

const sink = new Writable({
  highWaterMark: 64 * 1024, // 64KB buffer
  write(chunk, _enc, cb) {
    processChunk(chunk).then(() => cb()).catch(cb);
  },
});

// pipeline handles backpressure automatically
await pipeline(source, transform, sink);
```

**Interview key point:** Always use `pipeline()` or `.pipe()` instead of manually reading and writing. They handle backpressure, error propagation, and cleanup.

---

## Profiling

### clinic.js Suite

Three specialized tools:

| Tool | What It Finds | When to Use |
|------|--------------|-------------|
| `clinic doctor` | Event loop delays, I/O bottlenecks | First pass diagnosis |
| `clinic bubbleprof` | Async operation bottlenecks | Slow async workflows |
| `clinic flame` | CPU hotspots | High CPU usage |

```bash
# Install
npm install -g clinic

# Doctor: general health check
clinic doctor -- node dist/server.js
# Then hit the server with load, Ctrl+C to generate report

# Flame: CPU profiling
clinic flame -- node dist/server.js

# Bubbleprof: async delays
clinic bubbleprof -- node dist/server.js
```

### Chrome DevTools Protocol

```bash
# Start with inspector
node --inspect dist/server.js

# Or attach to running process
kill -USR1 <pid>    # enables inspector on running process
```

Then open `chrome://inspect` in Chrome. You get:
- CPU profiler (flame charts)
- Memory heap snapshots
- Memory allocation timeline
- Source code debugging

### CPU Profiling Programmatically

```typescript
import { Session } from 'node:inspector/promises';

async function profileEndpoint() {
  const session = new Session();
  session.connect();

  await session.post('Profiler.enable');
  await session.post('Profiler.start');

  // Run the code you want to profile
  await handleHeavyRequest();

  const { profile } = await session.post('Profiler.stop');

  // Write .cpuprofile file (importable in Chrome DevTools)
  await writeFile('profile.cpuprofile', JSON.stringify(profile));

  session.disconnect();
}
```

### Heap Profiling

```typescript
import v8 from 'node:v8';
import { writeFileSync } from 'node:fs';

// Snapshot (stop-the-world, use in dev only)
const snapshotPath = `/tmp/heap-${Date.now()}.heapsnapshot`;
v8.writeHeapSnapshot(snapshotPath);

// Heap statistics
const stats = v8.getHeapStatistics();
console.log({
  totalHeap: `${(stats.total_heap_size / 1024 / 1024).toFixed(1)}MB`,
  usedHeap: `${(stats.used_heap_size / 1024 / 1024).toFixed(1)}MB`,
  heapLimit: `${(stats.heap_size_limit / 1024 / 1024).toFixed(1)}MB`,
});
```

---

## Memory Leaks

### Common Causes

**1. Closures retaining references**

```typescript
// LEAK: closure holds reference to large data
function processData() {
  const hugeArray = loadHugeDataset(); // 500MB

  return function getStats() {
    // Only needs the count, but closure retains entire array
    return hugeArray.length;
  };
}

// FIX: extract what you need
function processData() {
  const hugeArray = loadHugeDataset();
  const count = hugeArray.length; // extract value
  // hugeArray can now be GC'd
  return function getStats() {
    return count;
  };
}
```

**2. Event listeners not removed**

```typescript
// LEAK: new listener added on every request
app.get('/stream', (req, res) => {
  eventBus.on('update', (data) => res.write(JSON.stringify(data)));
  // If client disconnects, listener is still attached
});

// FIX: clean up on close
app.get('/stream', (req, res) => {
  const handler = (data: unknown) => res.write(JSON.stringify(data));
  eventBus.on('update', handler);
  req.on('close', () => eventBus.off('update', handler));
});
```

**3. Timers not cleared**

```typescript
// LEAK: interval keeps reference to service alive
class HealthChecker {
  private interval: NodeJS.Timeout;

  start() {
    this.interval = setInterval(() => this.check(), 5000);
  }

  // FIX: always provide a stop method
  stop() {
    clearInterval(this.interval);
  }
}
```

**4. Global caches without bounds**

```typescript
// LEAK: cache grows unbounded
const cache = new Map<string, unknown>();

function getCached(key: string) {
  if (cache.has(key)) return cache.get(key);
  const value = expensiveCompute(key);
  cache.set(key, value); // never evicted
  return value;
}

// FIX: use an LRU cache
import { LRUCache } from 'lru-cache';
const cache = new LRUCache<string, unknown>({ max: 1000 });
```

### WeakRef and FinalizationRegistry

ES2021 features for advanced memory management:

```typescript
// WeakRef: holds a reference that doesn't prevent GC
const cache = new Map<string, WeakRef<BigObject>>();

function getCached(key: string): BigObject | undefined {
  const ref = cache.get(key);
  if (!ref) return undefined;
  const obj = ref.deref(); // undefined if GC'd
  if (!obj) cache.delete(key); // clean up dead ref
  return obj;
}

// FinalizationRegistry: callback when object is GC'd
const registry = new FinalizationRegistry<string>((key) => {
  console.log(`Object for key ${key} was garbage collected`);
  cache.delete(key);
});

function setCached(key: string, value: BigObject) {
  cache.set(key, new WeakRef(value));
  registry.register(value, key); // clean up when GC'd
}
```

### Heap Snapshots for Debugging

```bash
# Take 3 snapshots: baseline, after load, after GC
node --expose-gc -e "
  global.gc();
  const v8 = require('v8');
  v8.writeHeapSnapshot();  // baseline

  // ... run your code ...

  global.gc();
  v8.writeHeapSnapshot();  // after load + GC
"
```

Compare snapshots in Chrome DevTools:
1. Load both `.heapsnapshot` files in Memory tab
2. Select "Comparison" view
3. Sort by "Size Delta" to find growing objects
4. Follow the retainer tree to find the root cause

### --max-old-space-size

```bash
# Default is ~1.5GB on 64-bit systems
node --max-old-space-size=4096 dist/server.js  # 4GB

# For containers, set to ~75% of container memory limit
# Container with 2GB limit:
node --max-old-space-size=1536 dist/server.js
```

---

## Connection Pooling

### HTTP Keep-Alive

Node.js `http.Agent` reuses TCP connections:

```typescript
import { Agent } from 'node:http';

// Global agent with keep-alive
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
  pipelining: 1,       // HTTP pipelining depth
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
  // For production: handle errors
  allowExitOnIdle: false,
});

// Monitor pool health
pool.on('error', (err) => {
  console.error('Unexpected pool error', err);
});

// Expose pool stats for monitoring
function getPoolStats() {
  return {
    total: pool.totalCount,
    idle: pool.idleCount,
    waiting: pool.waitingCount,
  };
}
```

**Sizing rule of thumb:** `max connections = (number of cores * 2) + number of disks`. For most setups, 20-50 is the sweet spot. Too many connections actually degrade Postgres performance.

### Redis Connection Pools

```typescript
import Redis from 'ioredis';

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: 6379,
  maxRetriesPerRequest: 3,
  retryStrategy(times) {
    const delay = Math.min(times * 200, 2000);
    return delay;
  },
  // Connection pool via Cluster mode
  enableReadyCheck: true,
  lazyConnect: true,
});
```

For true connection pooling with Redis, use `ioredis` Cluster mode or a pool wrapper like `generic-pool`.

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

### Session Externalization

```typescript
import RedisStore from 'connect-redis';
import session from 'express-session';

app.use(session({
  store: new RedisStore({ client: redis }),
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: true,
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000,
  },
}));
```

### Shared-Nothing Architecture

Each instance has:
- Its own process memory (no shared state)
- Its own local filesystem (no shared files)
- Connection to shared services (Redis, database, S3)

File uploads go to S3, not local disk. Temp files are cleaned up in the same request. Configuration comes from environment variables, not local files.

---

## Queue-Based Processing

### BullMQ

Production-grade job queue backed by Redis.

```typescript
import { Queue, Worker, QueueScheduler } from 'bullmq';
import Redis from 'ioredis';

const connection = new Redis(process.env.REDIS_URL, { maxRetriesPerRequest: null });

// Queue: where jobs are added
const emailQueue = new Queue('email', { connection });

// Add a job
await emailQueue.add('welcome', {
  to: 'user@example.com',
  template: 'welcome',
  vars: { name: 'Alice' },
}, {
  attempts: 3,
  backoff: { type: 'exponential', delay: 1000 },
  removeOnComplete: { age: 3600 },
  removeOnFail: { count: 1000 },
});

// Worker: processes jobs
const worker = new Worker('email', async (job) => {
  switch (job.name) {
    case 'welcome':
      await sendWelcomeEmail(job.data);
      break;
    case 'reset-password':
      await sendResetEmail(job.data);
      break;
  }
}, {
  connection,
  concurrency: 5,
  limiter: {
    max: 100,
    duration: 60_000, // 100 emails per minute
  },
});

worker.on('failed', (job, err) => {
  logger.error(`Job ${job?.id} failed: ${err.message}`);
});
```

### Rate Limiting

```typescript
// Token bucket rate limiter with Redis
import { RateLimiterRedis } from 'rate-limiter-flexible';

const rateLimiter = new RateLimiterRedis({
  storeClient: redis,
  keyPrefix: 'rl',
  points: 100,        // requests
  duration: 60,       // per 60 seconds
  blockDuration: 60,  // block for 60s if exceeded
});

app.use(async (req, res, next) => {
  try {
    const key = req.ip ?? 'unknown';
    const result = await rateLimiter.consume(key);
    res.setHeader('X-RateLimit-Remaining', result.remainingPoints);
    next();
  } catch (rateLimiterRes) {
    res.setHeader('Retry-After', Math.ceil(rateLimiterRes.msBeforeNext / 1000));
    res.status(429).json({ error: 'Too many requests' });
  }
});
```

### Retry Strategies

```typescript
const job = await queue.add('process-payment', paymentData, {
  attempts: 5,
  backoff: {
    type: 'exponential',  // 1s, 2s, 4s, 8s, 16s
    delay: 1000,
  },
});

// Custom backoff
const job = await queue.add('sync-data', data, {
  attempts: 3,
  backoff: {
    type: 'custom',
  },
});

// In worker, define custom backoff
const worker = new Worker('sync-data', processor, {
  settings: {
    backoffStrategy: (attemptsMade: number) => {
      // Jittered exponential backoff
      const base = Math.pow(2, attemptsMade) * 1000;
      const jitter = Math.random() * 1000;
      return base + jitter;
    },
  },
});
```

### Dead Letter Queues

Jobs that fail all retry attempts should go somewhere for investigation:

```typescript
const worker = new Worker('payments', processor, { connection });

worker.on('failed', async (job, err) => {
  if (job && job.attemptsMade >= job.opts.attempts!) {
    // Move to DLQ
    await deadLetterQueue.add('failed-payment', {
      originalJob: job.data,
      error: err.message,
      attempts: job.attemptsMade,
      failedAt: new Date().toISOString(),
    });

    logger.error('Payment job moved to DLQ', {
      jobId: job.id,
      error: err.message,
    });
  }
});
```

---

## CDN and Edge Computing

### CDN for API Responses

Not just for static assets. Cache API responses at the edge for read-heavy endpoints:

```typescript
app.get('/api/products', async (req, res) => {
  // Cacheable for 60s, stale-while-revalidate for 300s
  res.setHeader('Cache-Control', 'public, max-age=60, stale-while-revalidate=300');
  res.setHeader('Vary', 'Accept-Encoding, Authorization');
  res.setHeader('CDN-Cache-Control', 'max-age=300'); // CDN caches longer

  const products = await getProducts(req.query);
  res.json(products);
});
```

### Surrogate Keys for Targeted Invalidation

```typescript
app.get('/api/products/:id', async (req, res) => {
  const product = await getProduct(req.params.id);
  res.setHeader('Surrogate-Key', `product-${product.id} products`);
  res.setHeader('Cache-Control', 'public, max-age=3600');
  res.json(product);
});

// When a product is updated, purge by surrogate key
async function onProductUpdated(productId: string) {
  await cdn.purge({ surrogateKey: `product-${productId}` });
}
```

---

## Interview Questions

### Conceptual

1. **"How would you handle a memory leak in production?"**
   Take heap snapshots (3: baseline, under load, after GC). Compare in Chrome DevTools. Look for growing objects in the comparison view. Common causes: event listeners not removed, closures over large objects, unbounded caches, timers not cleared. In production, use `--inspect` flag and connect remotely, or use APM tools that expose heap stats.

2. **"Explain Node.js clustering and its limitations."**
   The `cluster` module forks workers that share a port. Each worker is a separate process with its own event loop and memory. Limitations: no shared memory (use Redis), sticky sessions needed for stateful connections, IPC overhead for inter-worker communication. In production, use PM2 for process management with zero-downtime reloads.

3. **"How do you implement caching in a distributed system?"**
   Cache-aside with Redis. TTL-based expiry for simplicity, explicit invalidation on writes for consistency. Versioned keys for list caches. Pub/sub for multi-instance cache busting if you have a local cache layer. Always consider: what happens on cache miss? What happens on stale data? What is the thundering herd impact?

4. **"Describe backpressure and how you handle it in Node.js streams."**
   Backpressure occurs when a consumer cannot keep up with a producer. In Node.js streams, `write()` returns `false` when the internal buffer is full. The producer should stop writing until the `drain` event. `pipeline()` handles this automatically. Without backpressure handling, you get unbounded memory growth.

### System Design

5. **"Design a rate limiter for a multi-instance API."**
   Redis-backed sliding window or token bucket. Key per client (IP or API key). Use `MULTI/EXEC` or Lua scripts for atomicity. Return `429` with `Retry-After` header. Different tiers for different API plans. Consider: distributed rate limiting is eventually consistent — a brief burst above limit is acceptable.

6. **"Your API is slow under load. Walk through your debugging process."**
   First: check p95/p99 latency (not averages). Run `clinic doctor` for high-level diagnosis. If CPU-bound: `clinic flame` for hotspots. If I/O-bound: check connection pool saturation, slow queries (`EXPLAIN ANALYZE`), external API latency. Check for: N+1 queries, missing indexes, unbounded result sets, synchronous operations blocking the event loop.

7. **"How would you scale a WebSocket-based real-time service to 100K concurrent connections?"**
   Horizontal scaling with Redis adapter for cross-instance broadcasting. Sticky sessions or consistent hashing for connection routing. Connection count per instance (not unlimited). Heartbeat to detect stale connections. Consider: SSE for unidirectional push (simpler to scale), message fan-out patterns, and backpressure on broadcast.

### Opinionated Stances

- Premature optimization is real, but knowing *where* to look is not premature — it is preparedness.
- Redis is the Swiss Army knife of scaling. If you are reaching for another tool, ask if Redis can do it first.
- Connection pooling is not optional in production. A server without pool limits is a DDoS waiting to happen.
- "Just add more instances" is not a scaling strategy. Fix the inefficiency first, then scale horizontally.
- Load testing should run in CI, not as a one-off before launch.

---

**Next:** [Module 09 - Architecture Patterns](../09-architecture-patterns/)
