# 03 – Profiling and Advanced Performance

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

# Enable inspector on running process (send signal)
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

## clinic.js Suite

Three specialized tools for different performance problems:

| Tool | What It Finds | When to Use |
|------|--------------|-------------|
| `clinic doctor` | Event loop delays, I/O bottlenecks | First pass diagnosis |
| `clinic bubbleprof` | Async operation bottlenecks | Slow async workflows |
| `clinic flame` | CPU hotspots | High CPU usage |

```bash
# Doctor: general health check
clinic doctor -- node dist/server.js
# Then hit the server with load, Ctrl+C to generate report

# Flame: CPU profiling
clinic flame -- node dist/server.js

# Bubbleprof: async delays
clinic bubbleprof -- node dist/server.js
```

---

## Chrome DevTools Protocol

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

### Memory Leak Debugging Checklist

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

## APM Tools and Observability

### APM Tools Comparison

| Feature | Datadog | New Relic | Dynatrace |
|---------|---------|-----------|-----------|
| Auto-instrumentation | Yes (dd-trace) | Yes (@newrelic/agent) | Yes (OneAgent) |
| Node.js support | Excellent | Excellent | Excellent |
| Distributed tracing | Yes (OpenTelemetry compatible) | Yes | Yes (PurePath) |
| Custom metrics | StatsD, DogStatsD | Custom events API | Metric ingestion API |
| Log integration | Tight (log correlation) | Logs in context | Log analytics |
| Profiling | Continuous profiler | Thread profiler | Code-level profiler |
| Cost | Per host + ingestion | Per GB ingested | Per host (all-in) |
| Setup complexity | Medium | Low | Low (auto-discovery) |

### Datadog Integration

```typescript
// dd-trace must be imported FIRST, before any other module
import 'dd-trace/init';

// Custom span
import tracer from 'dd-trace';

app.get('/api/orders', async (req, res) => {
  const span = tracer.startSpan('orders.fetch');
  span.setTag('user.id', req.user.id);

  try {
    const orders = await db.query.orders.findMany({
      where: eq(orders.userId, req.user.id),
    });
    span.setTag('orders.count', orders.length);
    res.json(orders);
  } catch (err) {
    span.setTag('error', true);
    span.setTag('error.message', err.message);
    throw err;
  } finally {
    span.finish();
  }
});

// Custom metrics
import { StatsD } from 'hot-shots';
const metrics = new StatsD({ prefix: 'api.' });

metrics.increment('orders.created');
metrics.histogram('order.total', order.total);
metrics.gauge('queue.depth', await queue.count());
```

### OpenTelemetry (Vendor-Agnostic)

The industry standard for instrumentation. Works with any backend (Datadog, Jaeger, Zipkin, Grafana Tempo):

```typescript
// instrumentation.ts — must be loaded before app code
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
  }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter(),
    exportIntervalMillis: 30_000,
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': { enabled: true },
      '@opentelemetry/instrumentation-express': { enabled: true },
      '@opentelemetry/instrumentation-pg': { enabled: true },
      '@opentelemetry/instrumentation-redis': { enabled: true },
    }),
  ],
  serviceName: 'my-api',
});

sdk.start();

// Graceful shutdown
process.on('SIGTERM', () => sdk.shutdown());
```

### What to Monitor

| Category | Metrics | Alert Threshold |
|----------|---------|-----------------|
| Latency | p50, p95, p99 response time | p95 > 500ms |
| Throughput | Requests per second | Deviation > 30% from baseline |
| Errors | 5xx rate, error rate by endpoint | > 1% error rate |
| Saturation | CPU %, memory %, event loop lag | CPU > 80%, event loop > 100ms |
| Dependencies | DB query time, Redis latency, external API time | Any > 200ms |
| Business | Orders/min, signup rate, payment success rate | Deviation from baseline |

### Event Loop Monitoring

```typescript
import { monitorEventLoopDelay } from 'node:perf_hooks';

const histogram = monitorEventLoopDelay({ resolution: 20 });
histogram.enable();

// Expose as metric every 10s
setInterval(() => {
  metrics.gauge('event_loop.delay.p50', histogram.percentile(50) / 1e6);  // ns -> ms
  metrics.gauge('event_loop.delay.p99', histogram.percentile(99) / 1e6);
  metrics.gauge('event_loop.delay.max', histogram.max / 1e6);
  histogram.reset();
}, 10_000);
```

---

## HTTP/2 in Node.js

### HTTP/2 Server

```typescript
import { createSecureServer } from 'node:http2';
import { readFileSync } from 'node:fs';

const server = createSecureServer({
  key: readFileSync('server.key'),
  cert: readFileSync('server.crt'),
  allowHTTP1: true,  // fallback for clients that don't support H2
});

server.on('stream', (stream, headers) => {
  const path = headers[':path'];

  if (path === '/api/data') {
    stream.respond({
      ':status': 200,
      'content-type': 'application/json',
    });
    stream.end(JSON.stringify({ data: 'hello' }));
  }

  // Server Push (preemptively send resources)
  if (path === '/api/dashboard') {
    stream.pushStream({ ':path': '/api/user' }, (err, pushStream) => {
      if (err) return;
      pushStream.respond({ ':status': 200, 'content-type': 'application/json' });
      pushStream.end(JSON.stringify(userData));
    });

    stream.respond({ ':status': 200, 'content-type': 'application/json' });
    stream.end(JSON.stringify(dashboardData));
  }
});

server.listen(443);
```

Fastify has first-class HTTP/2 support; Express requires a reverse proxy or wrapper.

### HTTP/2 Benefits for APIs

| Feature | Impact on APIs |
|---------|---------------|
| Multiplexing | Multiple requests on one connection (no head-of-line blocking at HTTP layer) |
| Header compression (HPACK) | Smaller headers, matters for APIs with large auth tokens |
| Server push | Preemptively send related resources |
| Stream prioritization | Critical requests get bandwidth first |
| Binary framing | More efficient parsing than HTTP/1.1 text |

**Interview point:** "HTTP/3 eliminates TCP head-of-line blocking at the transport layer. HTTP/2 solved it at the HTTP layer but still suffers when a TCP packet is lost. QUIC solves this by making each stream independent at the transport level." In practice, HTTP/3 is handled at the load balancer or CDN level; your Node.js application serves HTTP/2.

---

## Interview Questions

### Conceptual

**"How would you handle a memory leak in production?"**

Take heap snapshots (3: baseline, under load, after GC). Compare in Chrome DevTools. Look for growing objects in the comparison view. Common causes: event listeners not removed, closures over large objects, unbounded caches, timers not cleared. In production, use `--inspect` flag and connect remotely, or use APM tools that expose heap stats.

**"Your API is slow under load. Walk through your debugging process."**

First: check p95/p99 latency (not averages). Run `clinic doctor` for high-level diagnosis. If CPU-bound: `clinic flame` for hotspots. If I/O-bound: check connection pool saturation, slow queries (`EXPLAIN ANALYZE`), external API latency. Check for: N+1 queries, missing indexes, unbounded result sets, synchronous operations blocking the event loop.

**"Describe backpressure and how you handle it in Node.js streams."**

Backpressure occurs when a consumer cannot keep up with a producer. In Node.js streams, `write()` returns `false` when the internal buffer is full. The producer should stop writing until the `drain` event. `pipeline()` handles this automatically. Without backpressure handling, you get unbounded memory growth.

**"How would you scale a WebSocket-based real-time service to 100K concurrent connections?"**

Horizontal scaling with Redis adapter for cross-instance broadcasting. Sticky sessions or consistent hashing for connection routing. Connection count per instance (not unlimited). Heartbeat to detect stale connections. Consider: SSE for unidirectional push (simpler to scale), message fan-out patterns, and backpressure on broadcast.

### System Design

**"Design a rate limiter for a multi-instance API."**

Redis-backed sliding window or token bucket. Key per client (IP or API key). Use `MULTI/EXEC` or Lua scripts for atomicity. Return `429` with `Retry-After` header. Different tiers for different API plans. Consider: distributed rate limiting is eventually consistent — a brief burst above limit is acceptable.

### Opinionated Stances

- Premature optimization is real, but knowing *where* to look is not premature — it is preparedness.
- Redis is the Swiss Army knife of scaling. If you are reaching for another tool, ask if Redis can do it first.
- Connection pooling is not optional in production. A server without pool limits is a DDoS waiting to happen.
- "Just add more instances" is not a scaling strategy. Fix the inefficiency first, then scale horizontally.
- Load testing should run in CI, not as a one-off before launch.
- V8 optimizes for monomorphic code. Consistent object shapes and types lead to faster execution. Avoid `delete`, dynamic property addition, and megamorphic call sites.
- OpenTelemetry is the future of observability. Vendor-agnostic instrumentation that works with any backend. Auto-instrumentation covers HTTP, database, and cache calls.
- Monitor the four golden signals: latency, throughput, errors, and saturation. Event loop delay is the Node.js-specific saturation metric.
