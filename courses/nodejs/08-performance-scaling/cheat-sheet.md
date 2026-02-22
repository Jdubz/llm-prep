# Module 08: Performance & Scaling — Cheat Sheet

> Quick reference for profiling, debugging, caching, and scaling patterns.

---

## Profiling Commands Reference

```bash
# clinic.js suite
npm install -g clinic
clinic doctor -- node dist/server.js      # general health
clinic flame -- node dist/server.js       # CPU flame graph
clinic bubbleprof -- node dist/server.js  # async bottlenecks

# Chrome DevTools inspector
node --inspect dist/server.js             # debugger on :9229
node --inspect-brk dist/server.js         # break on first line
node --inspect=0.0.0.0:9229 dist/server.js  # remote debugging

# Enable inspector on running process
kill -USR1 <pid>

# CPU profiling via CLI
node --cpu-prof dist/server.js            # writes .cpuprofile on exit
node --cpu-prof-interval=100 dist/server.js  # 100us sampling

# Heap profiling
node --heap-prof dist/server.js           # writes .heapprofile on exit
node --max-old-space-size=4096 dist/server.js  # set heap limit

# Heap snapshot
node -e "require('v8').writeHeapSnapshot()"

# V8 flags for diagnosis
node --trace-deopt dist/server.js         # log deoptimizations
node --trace-opt dist/server.js           # log optimizations
node --trace-gc dist/server.js            # log GC events

# Event loop delay
node -e "
const h = require('perf_hooks').monitorEventLoopDelay({resolution: 20});
h.enable();
setTimeout(() => {
  console.log('p50:', (h.percentile(50)/1e6).toFixed(2), 'ms');
  console.log('p99:', (h.percentile(99)/1e6).toFixed(2), 'ms');
}, 5000);
"
```

---

## Memory Leak Debugging Checklist

1. **Confirm the leak exists**
   - Monitor RSS and heap used over time
   - `process.memoryUsage()` at regular intervals
   - If heap grows linearly under constant load, it is a leak

2. **Take heap snapshots**
   ```bash
   # Snapshot 1: baseline (after warm-up)
   # Snapshot 2: after sustained load
   # Snapshot 3: after forced GC (node --expose-gc)
   ```

3. **Compare snapshots in Chrome DevTools**
   - Memory tab -> Load snapshots -> Comparison view
   - Sort by "Size Delta" descending
   - Look for: growing arrays, strings, closures, event listeners

4. **Common culprits checklist**
   - [ ] Event listeners added without removal (`emitter.on` without `emitter.off`)
   - [ ] `setInterval`/`setTimeout` without `clearInterval`/`clearTimeout`
   - [ ] Closures capturing large objects
   - [ ] Global `Map`/`Set`/`Array` used as cache without eviction
   - [ ] Promise chains that never resolve
   - [ ] Streams not properly closed/destroyed
   - [ ] Circular references in logged objects (logger retains refs)

5. **Fix and verify**
   - Apply fix
   - Run same load test
   - Confirm heap stabilizes (no linear growth)

---

## Redis Caching Patterns

```typescript
// Cache-aside (read-through)
const cached = await redis.get(key);
if (cached) return JSON.parse(cached);
const data = await db.query(/* ... */);
await redis.set(key, JSON.stringify(data), 'EX', ttl);
return data;

// Write-through
await db.update(/* ... */);
await redis.set(key, JSON.stringify(updated), 'EX', ttl);

// Cache invalidation on write
await db.update(/* ... */);
await redis.del(key);

// Pattern invalidation (use with caution — O(N))
const keys = await redis.keys('users:list:*');
if (keys.length) await redis.del(...keys);

// Better: versioned keys
await redis.incr('users:version');  // all old keys naturally expire

// Pub/sub invalidation (multi-instance)
await redis.publish('cache:invalidate', JSON.stringify({ key }));

// Cache stampede protection (singleflight / lock)
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

**TTL guidelines:**
| Data Type | TTL | Reasoning |
|-----------|-----|-----------|
| User profile | 5-15 min | Changes infrequently |
| Product catalog | 1-5 min | Moderate change rate |
| Search results | 30-60s | High change rate |
| Session data | 24h | Explicit lifecycle |
| Feature flags | 30s | Need fast propagation |
| Rate limit counters | window size | Sliding window |

---

## BullMQ Setup Template

```typescript
import { Queue, Worker, QueueEvents } from 'bullmq';
import Redis from 'ioredis';

// Shared connection (maxRetriesPerRequest must be null for BullMQ)
const connection = new Redis(process.env.REDIS_URL, {
  maxRetriesPerRequest: null,
});

// Queue
const queue = new Queue('my-queue', {
  connection,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 1000 },
    removeOnComplete: { age: 3600, count: 1000 },
    removeOnFail: { count: 5000 },
  },
});

// Worker
const worker = new Worker('my-queue', async (job) => {
  // process job.data
  return { success: true };
}, {
  connection,
  concurrency: 5,
  limiter: { max: 100, duration: 60_000 },
});

// Events
const events = new QueueEvents('my-queue', { connection });
events.on('completed', ({ jobId, returnvalue }) => { /* ... */ });
events.on('failed', ({ jobId, failedReason }) => { /* ... */ });

// Add jobs
await queue.add('task-name', { key: 'value' });                   // immediate
await queue.add('task-name', { key: 'value' }, { delay: 5000 });  // delayed
await queue.add('task-name', { key: 'value' }, {                  // scheduled
  repeat: { pattern: '0 */5 * * *' },                             // every 5 min
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  await worker.close();
  await queue.close();
  await connection.quit();
});
```

---

## Clustering Setup Template

```typescript
// PM2 ecosystem config
// ecosystem.config.cjs
module.exports = {
  apps: [{
    name: 'api',
    script: './dist/server.js',
    instances: 'max',
    exec_mode: 'cluster',
    max_memory_restart: '500M',
    kill_timeout: 5000,
    listen_timeout: 10000,
    wait_ready: true,
    env: { NODE_ENV: 'production' },
  }],
};
```

```bash
# PM2 commands
pm2 start ecosystem.config.cjs
pm2 reload api                   # zero-downtime restart
pm2 scale api +2                 # add 2 more workers
pm2 monit                        # real-time dashboard
pm2 logs api --lines 100         # tail logs
pm2 save && pm2 startup          # persist across reboots
```

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

---

## Performance Benchmarking Checklist

### Before Load Testing

- [ ] Application built in production mode (`NODE_ENV=production`)
- [ ] Debug logging disabled or set to `warn`/`error`
- [ ] Source maps disabled or external
- [ ] Database has representative data volume
- [ ] Connection pools sized appropriately
- [ ] Redis is running (not falling through to DB on every request)
- [ ] No `console.log` in hot paths

### During Load Testing

- [ ] Monitor: CPU, memory, event loop delay, DB connections, Redis connections
- [ ] Watch for: linear memory growth, connection pool exhaustion, error rate spikes
- [ ] Record: p50, p95, p99 latency at each concurrency level
- [ ] Test scenarios: ramp-up, sustained, spike, soak (long duration)

### Key Metrics to Capture

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

### Red Flags

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| p99 >> p95 | GC pauses, lock contention | Reduce allocation rate, tune GC |
| Latency grows with load | Connection pool exhaustion | Increase pool, add caching |
| Memory grows linearly | Memory leak | Heap snapshot comparison |
| CPU at 100% one core | Single-threaded bottleneck | Cluster mode, worker threads |
| Sudden error spike | Connection limit hit | Pool limits, circuit breaker |
| Throughput plateaus | Event loop saturation | Offload CPU work, scale out |

### k6 Quick Commands

```bash
# Basic load test
k6 run load-test.js

# With environment variables
k6 run -e TOKEN=xxx -e API_URL=http://localhost:3000 load-test.js

# Override VUs and duration
k6 run --vus 50 --duration 2m load-test.js

# Output to JSON for analysis
k6 run --out json=results.json load-test.js

# Output to InfluxDB + Grafana
k6 run --out influxdb=http://localhost:8086/k6 load-test.js
```
