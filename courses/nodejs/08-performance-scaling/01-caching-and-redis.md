# 01 – Caching and Redis

## Redis Data Structures for Caching Patterns

Redis is not just a key-value store. Each data structure is optimized for different access patterns:

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

## ioredis Setup

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
  enableReadyCheck: true,
  lazyConnect: true,
});

// For BullMQ, maxRetriesPerRequest must be null
const bullmqConnection = new Redis(process.env.REDIS_URL, {
  maxRetriesPerRequest: null,
});
```

---

## Cache-Aside (Lazy Loading)

The most common pattern. Application checks cache first, falls back to database, then populates cache.

```typescript
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

---

## Write-Through

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

  // Write to cache
  await redis.set(`user:${id}`, JSON.stringify(user), 'EX', 3600);

  return user;
}
```

**Trade-offs:**
- Cache is always fresh
- Write latency increases (two writes per operation)
- Cache may contain data that is never read (waste)

---

## Write-Behind (Write-Back)

Application writes to cache immediately, database write happens asynchronously. Highest write performance, but risk of data loss.

```typescript
async function updateUserWriteBehind(id: string, data: Partial<User>): Promise<void> {
  const cacheKey = `user:${id}`;

  // Write to cache immediately
  const current = JSON.parse(await redis.get(cacheKey) || '{}');
  const updated = { ...current, ...data, updatedAt: new Date() };
  await redis.set(cacheKey, JSON.stringify(updated), 'EX', 3600);

  // Queue async database write
  await writeQueue.add('update-user', { id, data: updated });
}
```

---

## Cache Invalidation Strategies

The two hard problems in computer science: cache invalidation, naming things, and off-by-one errors.

### TTL-Based Expiry (Simplest)

```typescript
await redis.set(key, value, 'EX', 3600); // expires in 1 hour
```

### Explicit Invalidation on Write

```typescript
async function updateUser(id: string, data: Partial<User>) {
  await db.update(users).set(data).where(eq(users.id, id));
  await redis.del(`user:${id}`);         // invalidate specific key
}
```

### Versioned Keys (For List Caches)

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

### Pub/Sub for Multi-Instance Cache Busting

In a multi-instance deployment, one instance invalidates cache but others still have stale local (in-memory) caches:

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

### Cache Stampede Protection

When a cached value expires, multiple concurrent requests all hit the database simultaneously:

```typescript
// Singleflight / lock approach
const lock = await redis.set(`lock:${key}`, '1', 'EX', 5, 'NX');
if (lock) {
  const data = await db.query(/* ... */);
  await redis.set(key, JSON.stringify(data), 'EX', ttl);
  await redis.del(`lock:${key}`);
  return data;
} else {
  await sleep(100);           // wait for other instance to populate
  return JSON.parse(await redis.get(key));
}
```

---

## TTL Guidelines

| Data Type | TTL | Reasoning |
|-----------|-----|-----------|
| User profile | 5-15 min | Changes infrequently |
| Product catalog | 1-5 min | Moderate change rate |
| Search results | 30-60s | High change rate |
| Session data | 24h | Explicit lifecycle |
| Feature flags | 30s | Need fast propagation |
| Rate limit counters | window size | Sliding window |

---

## Pattern Invalidation Warning

```typescript
// Pattern invalidation (use with caution — O(N) Redis scan)
const keys = await redis.keys('users:list:*');
if (keys.length) await redis.del(...keys);

// Better: versioned keys (see above) or SCAN instead of KEYS
let cursor = '0';
do {
  const [nextCursor, keys] = await redis.scan(cursor, 'MATCH', 'users:list:*', 'COUNT', 100);
  cursor = nextCursor;
  if (keys.length) await redis.del(...keys);
} while (cursor !== '0');
```

Never use `KEYS` in production — it blocks Redis while scanning all keys.

---

## Session Caching

Stateless sessions backed by Redis enable horizontal scaling:

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
    maxAge: 24 * 60 * 60 * 1000, // 24 hours
  },
}));
```

### Stateless Design Rule

Any request must be handleable by any instance. State that must cross requests goes to Redis.

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

| What breaks | Why | Solution |
|-------------|-----|---------|
| In-memory sessions | Each worker has different sessions | Redis session store |
| In-memory caches | Cache misses on different workers | Redis / Memcached |
| Rate limiting counters | Each worker counts independently | Redis-backed rate limiter |
| WebSocket rooms | Broadcast only reaches one worker | Redis adapter / cluster adapter |
| Singleton patterns | Multiple instances exist | External coordination (Redis, DB) |

---

## Rate Limiting

### Token Bucket with Redis

```typescript
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

### Sliding Window with Sorted Set

```typescript
class SlidingWindowRateLimiter {
  constructor(private redis: Redis, private windowMs: number, private max: number) {}

  async isAllowed(key: string): Promise<{ allowed: boolean; remaining: number }> {
    const now = Date.now();
    const result = await this.redis.multi()
      .zremrangebyscore(key, 0, now - this.windowMs)  // Remove expired
      .zadd(key, now, `${now}-${Math.random()}`)       // Add current
      .zcard(key)                                       // Count in window
      .pexpire(key, this.windowMs)
      .exec();

    const count = result![2][1] as number;
    return { allowed: count <= this.max, remaining: Math.max(0, this.max - count) };
  }
}
```

---

## WebSocket Scaling with Redis Adapter

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

---

## BullMQ Queue Setup

Production-grade job queue backed by Redis:

```typescript
import { Queue, Worker, QueueEvents } from 'bullmq';
import Redis from 'ioredis';

const connection = new Redis(process.env.REDIS_URL, {
  maxRetriesPerRequest: null, // Required for BullMQ
});

// Queue with default job options
const emailQueue = new Queue('email', {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 1000 },
    removeOnComplete: { age: 3600, count: 1000 },
    removeOnFail: { count: 5000 },
  },
});

// Add jobs
await emailQueue.add('welcome', {
  to: 'user@example.com',
  template: 'welcome',
  vars: { name: 'Alice' },
});

await emailQueue.add('task-name', { key: 'value' }, { delay: 5000 });  // delayed
await emailQueue.add('task-name', { key: 'value' }, {
  repeat: { pattern: '0 */5 * * *' },  // every 5 min (cron)
});

// Worker
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

// Events
const events = new QueueEvents('email', { connection });
events.on('completed', ({ jobId, returnvalue }) => { /* ... */ });
events.on('failed', ({ jobId, failedReason }) => { /* ... */ });

// Graceful shutdown
process.on('SIGTERM', async () => {
  await worker.close();
  await emailQueue.close();
  await connection.quit();
});
```

### Dead Letter Queues

Jobs that fail all retry attempts should go somewhere for investigation:

```typescript
worker.on('failed', async (job, err) => {
  if (job && job.attemptsMade >= job.opts.attempts!) {
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

### Retry Strategies

```typescript
// Custom backoff with jitter
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

---

## CDN and Edge Caching

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

async function onProductUpdated(productId: string) {
  await cdn.purge({ surrogateKey: `product-${productId}` });
}
```

---

## Streaming for Large Payloads

For large datasets, stream instead of buffering the entire response:

```typescript
import { Transform } from 'node:stream';
import { pipeline } from 'node:stream/promises';

app.get('/export/users', async (req, res) => {
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Transfer-Encoding', 'chunked');

  const dbStream = db.query.users.findMany().stream();

  const csvTransform = new Transform({
    objectMode: true,
    transform(user, _enc, cb) {
      cb(null, `${user.id},${user.name},${user.email}\n`);
    },
  });

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

  const heartbeat = setInterval(() => {
    res.write(': heartbeat\n\n');
  }, 30_000);

  const unsubscribe = eventBus.on('order:updated', (order) => {
    sendEvent('order:updated', order);
  });

  req.on('close', () => {
    clearInterval(heartbeat);
    unsubscribe();
  });
});
```

### Backpressure Handling

When a producer generates data faster than the consumer can process it:

```typescript
import { Readable, Writable } from 'node:stream';

const source = new Readable({
  read() {
    const canContinue = this.push(generateChunk());
    if (!canContinue) {
      // Downstream is full — stop producing until drain
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

## Related Reading

- **Cache-aside and write-through patterns** are the caching layer for the database queries covered in [06 – Queries, Transactions, and Optimization](../06-database-patterns/02-queries-transactions-and-optimization.md) — cache invalidation must align with your transaction boundaries.
- **Redis session caching and stateless design** directly supports the session management strategies in [05 – Session Management and Validation](../05-auth-security/02-session-management-and-validation.md) and the horizontal scaling requirements in [08 – Clustering and Scaling](./02-clustering-and-scaling.md#stateless-design).
- **Rate limiting with Redis sorted sets** complements the rate limiting middleware discussed in [05 – Advanced Security and Secrets](../05-auth-security/03-advanced-security-and-secrets.md#rate-limiting-and-brute-force-protection) and the HTTP 429 response patterns in [03 – HTTP Semantics and Status Codes](../03-rest-api-design/01-http-semantics-and-status-codes.md).
- **BullMQ queue setup and dead letter queues** are the production implementation of the background job patterns referenced in [09 – Event-Driven and Async Patterns](../09-architecture-patterns/02-event-driven-and-async-patterns.md#message-brokers).
- **WebSocket scaling with Redis adapter** solves the multi-instance broadcasting problem discussed in [08 – Clustering and Scaling](./02-clustering-and-scaling.md#sticky-sessions) and tested in [07 – Integration Testing and Mocking](../07-testing/02-integration-testing-and-mocking.md#testing-websocket-handlers).
- **Streaming and backpressure for large payloads** builds on the stream fundamentals in [02 – Memory, Streams, and Runtime Internals](../02-node-runtime/03-memory-streams-and-runtime-internals.md#streams-and-backpressure) and is tested using the patterns in [07 – Vitest and Unit Testing](../07-testing/01-vitest-and-unit-testing.md#streams).
- **CDN and surrogate key invalidation** extends the Cache-Control headers covered in [03 – API Design Patterns and Versioning](../03-rest-api-design/03-api-design-patterns-and-versioning.md#etag-and-conditional-requests).
