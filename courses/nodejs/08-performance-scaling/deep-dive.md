# Module 08: Performance & Scaling — Deep Dive

> V8 internals, zero-copy tricks, HTTP/2 and HTTP/3, gRPC at scale, serverless trade-offs, and APM tooling. The material here separates "senior" from "staff" in interviews.

---

## V8 Optimization Tips

### Monomorphic Functions

V8 optimizes functions based on the types they receive. A function that always receives the same shape of object is **monomorphic** and gets the fastest generated code.

```typescript
// MONOMORPHIC: always receives { x: number, y: number }
function distance(point: { x: number; y: number }) {
  return Math.sqrt(point.x ** 2 + point.y ** 2);
}

// Always called with the same shape
distance({ x: 1, y: 2 });
distance({ x: 3, y: 4 });

// POLYMORPHIC: receives different shapes
function getValue(obj: Record<string, unknown>) {
  return obj.value;
}

getValue({ value: 1 });           // shape 1
getValue({ value: 'hello' });     // shape 2
getValue({ value: 1, extra: 2 }); // shape 3: different hidden class
```

**Why this matters for hot paths:** V8 builds inline caches (ICs) for property access. Monomorphic ICs are a single pointer comparison. Megamorphic ICs (4+ shapes) fall back to hash table lookups.

### Hidden Classes

V8 assigns hidden classes (called "Maps" internally) to objects based on their property layout. Objects with the same properties added in the same order share a hidden class.

```typescript
// GOOD: same property order = same hidden class
function createPoint(x: number, y: number) {
  return { x, y }; // always {x, y} in that order
}

// BAD: different property orders = different hidden classes
function createPointBad(x: number, y: number, label?: string) {
  const obj: any = {};
  if (label) obj.label = label;  // sometimes label first
  obj.x = x;                     // then x
  obj.y = y;                     // then y
  return obj;
}

// GOOD: always initialize all properties, even if undefined
function createPointGood(x: number, y: number, label?: string) {
  return { x, y, label: label ?? undefined };
}
```

### Deoptimization Traps

V8's TurboFan compiler optimizes based on assumptions. When assumptions are violated, it **deoptimizes** — throwing away compiled code and falling back to the interpreter.

Common deoptimization triggers:

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

# V8 optimization status of functions
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

### Buffer.from with ArrayBuffer

Normally, creating a Buffer copies the data. Zero-copy shares the underlying memory:

```typescript
// COPY: allocates new memory
const buf = Buffer.from([1, 2, 3, 4]);

// ZERO-COPY: shares memory with the ArrayBuffer
const arrayBuffer = new ArrayBuffer(1024);
const buf = Buffer.from(arrayBuffer);     // no copy!
// Mutations to buf are visible through arrayBuffer and vice versa

// ZERO-COPY: slice shares memory
const original = Buffer.alloc(1024);
const slice = original.subarray(0, 512); // no copy, same memory
```

### sendfile(2)

When serving static files, the kernel can transfer data directly from disk to socket without copying through user space:

```typescript
import { createReadStream } from 'node:fs';

// Node.js streams use sendfile(2) under the hood
app.get('/download/:file', (req, res) => {
  const stream = createReadStream(`/data/${req.params.file}`);
  // pipeline uses sendfile when source is a file descriptor
  // and destination is a socket
  stream.pipe(res);
});
```

### Transferable Objects with Worker Threads

```typescript
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';

if (isMainThread) {
  const buffer = new SharedArrayBuffer(1024 * 1024); // 1MB shared memory
  const worker = new Worker(__filename, { workerData: { buffer } });

  // Or transfer ownership (zero-copy, original becomes unusable)
  const arrayBuffer = new ArrayBuffer(1024 * 1024);
  worker.postMessage({ data: arrayBuffer }, [arrayBuffer]);
  // arrayBuffer.byteLength is now 0 — ownership transferred
} else {
  const { buffer } = workerData;
  // Worker can read/write the SharedArrayBuffer directly
  const view = new Int32Array(buffer);
  Atomics.add(view, 0, 1); // thread-safe increment
}
```

---

## HTTP/2 and HTTP/3 in Node.js

### HTTP/2

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
    // Push the user profile alongside the dashboard data
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

### HTTP/2 with Express/Fastify

Express does not natively support HTTP/2. Use a wrapper or reverse proxy:

```typescript
// Fastify has first-class HTTP/2 support
import Fastify from 'fastify';

const app = Fastify({
  http2: true,
  https: {
    key: readFileSync('server.key'),
    cert: readFileSync('server.crt'),
  },
});

app.get('/api/data', async () => {
  return { data: 'hello' };
});

await app.listen({ port: 443 });
```

### HTTP/2 Benefits for APIs

| Feature | Impact on APIs |
|---------|---------------|
| Multiplexing | Multiple requests on one connection (no head-of-line blocking at HTTP layer) |
| Header compression (HPACK) | Smaller headers, matters for APIs with large auth tokens |
| Server push | Preemptively send related resources |
| Stream prioritization | Critical requests get bandwidth first |
| Binary framing | More efficient parsing than HTTP/1.1 text |

### HTTP/3 (QUIC)

HTTP/3 uses QUIC (UDP-based) instead of TCP. Node.js has experimental support:

```typescript
// Node.js 20+ with --experimental-quic (unstable)
import { createQuicSocket } from 'node:net';
```

In practice, HTTP/3 is handled at the load balancer or CDN level (Cloudflare, AWS CloudFront). Your Node.js application serves HTTP/2, and the edge terminates HTTP/3.

**Interview point:** "HTTP/3 eliminates TCP head-of-line blocking at the transport layer. HTTP/2 solved it at the HTTP layer but still suffers when a TCP packet is lost. QUIC solves this by making each stream independent at the transport level."

---

## gRPC Performance

### gRPC vs REST for Internal Services

| Aspect | gRPC | REST (JSON) |
|--------|------|-------------|
| Serialization | Protobuf (binary, ~10x smaller) | JSON (text, human-readable) |
| Transport | HTTP/2 (always) | HTTP/1.1 or HTTP/2 |
| Streaming | Bidirectional native | SSE or WebSocket bolt-on |
| Code generation | Yes (type-safe clients) | OpenAPI (optional) |
| Browser support | Via grpc-web proxy | Native |
| Debugging | Harder (binary protocol) | Easy (curl, browser) |

### Node.js gRPC Setup

```typescript
// server.ts
import { Server, ServerCredentials, loadPackageDefinition } from '@grpc/grpc-js';
import { loadSync } from '@grpc/proto-loader';

const packageDef = loadSync('./protos/user.proto', {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
});

const proto = loadPackageDefinition(packageDef) as any;

const server = new Server({
  'grpc.max_receive_message_length': 10 * 1024 * 1024, // 10MB
  'grpc.keepalive_time_ms': 60000,
  'grpc.keepalive_timeout_ms': 5000,
});

server.addService(proto.UserService.service, {
  getUser: async (call, callback) => {
    try {
      const user = await db.query.users.findFirst({
        where: eq(users.id, call.request.id),
      });
      callback(null, user);
    } catch (err) {
      callback({ code: grpc.status.INTERNAL, message: err.message });
    }
  },

  // Server streaming
  listUsers: async (call) => {
    const cursor = db.query.users.findMany().cursor();
    for await (const user of cursor) {
      call.write(user);
    }
    call.end();
  },
});

server.bindAsync('0.0.0.0:50051', ServerCredentials.createInsecure(), () => {
  console.log('gRPC server on :50051');
});
```

### gRPC Performance Tuning

```typescript
// Connection pooling (grpc-js manages this internally)
const client = new proto.UserService(
  'localhost:50051',
  grpc.credentials.createInsecure(),
  {
    'grpc.keepalive_time_ms': 60000,
    'grpc.keepalive_timeout_ms': 5000,
    'grpc.max_concurrent_streams': 100,
    'grpc.initial_reconnect_backoff_ms': 1000,
    'grpc.max_reconnect_backoff_ms': 10000,
  }
);

// Deadline (timeout)
const deadline = new Date();
deadline.setSeconds(deadline.getSeconds() + 5);
client.getUser({ id: '123' }, { deadline }, (err, response) => {
  // ...
});
```

---

## Serverless Node.js

### Cold Starts

The latency when a new Lambda/Cloud Function instance is created. This is the primary performance concern in serverless.

| Factor | Impact on Cold Start |
|--------|---------------------|
| Runtime | Node.js ~200-400ms (fast), Java ~2-5s (slow) |
| Package size | Larger bundles = longer init |
| SDK initialization | AWS SDK, DB connections add 100-300ms each |
| VPC | Adds 1-2s (ENI attachment) |
| Provisioned concurrency | Eliminates cold start (at cost) |

### Minimizing Cold Starts

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

### Provisioned Concurrency

Pre-warms a specified number of Lambda instances:

```yaml
# serverless.yml
functions:
  api:
    handler: dist/handler.handler
    provisionedConcurrency: 5    # 5 warm instances always ready
    events:
      - httpApi: '*'
```

**Cost trade-off:** You pay for provisioned concurrency whether it is used or not. Only use for latency-sensitive endpoints.

### Function Composition Patterns

```typescript
// Step Functions for orchestration (preferred)
// Each step is a separate Lambda — retry, error handling built in

// Direct invocation (tight coupling, avoid)
import { LambdaClient, InvokeCommand } from '@aws-sdk/client-lambda';

// Event-driven (loose coupling, preferred)
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';

export const orderHandler = async (event: SQSEvent) => {
  for (const record of event.Records) {
    const order = JSON.parse(record.body);
    await processOrder(order);
    // Next step triggered by EventBridge or another SQS queue
  }
};
```

---

## Edge Runtime Limitations

Edge runtimes (Cloudflare Workers, Vercel Edge Functions, Deno Deploy) run a restricted subset of Node.js:

| Feature | Available | Notes |
|---------|-----------|-------|
| `fetch` | Yes | Native Web API |
| `crypto` | Partial | Web Crypto API only |
| `fs` | No | No filesystem access |
| `net`/`dgram` | No | No raw sockets |
| `child_process` | No | No process spawning |
| Node.js built-ins | Partial | Varies by runtime |
| npm packages | Limited | Must be edge-compatible |
| Execution time | 10-50ms typical | Hard limits vary |
| Memory | 128MB typical | Much less than Lambda |

### What Works Well at the Edge

- Authentication token validation (JWT verify)
- Request routing and rewriting
- A/B testing and feature flags
- Geolocation-based responses
- Rate limiting
- Response caching logic
- API response transformation

### What Does Not Work at the Edge

- Database connections (no TCP sockets; use HTTP-based DB proxies like Neon, PlanetScale)
- Heavy computation (CPU limits)
- Large payloads (memory limits)
- File system operations
- Long-running processes

```typescript
// Cloudflare Worker example
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Edge-compatible: JWT validation
    const token = request.headers.get('Authorization')?.split(' ')[1];
    if (!token) return new Response('Unauthorized', { status: 401 });

    const payload = await verifyJWT(token, env.JWT_SECRET);

    // Edge-compatible: HTTP-based database query
    const user = await fetch(`${env.API_URL}/users/${payload.sub}`);

    return new Response(await user.text(), {
      headers: { 'Content-Type': 'application/json' },
    });
  },
};
```

---

## APM Tools Comparison

### Overview

Application Performance Monitoring tools provide real-time visibility into your application's performance, errors, and infrastructure.

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

## Key Takeaways for Interviews

1. **V8 optimizes for monomorphic code.** Consistent object shapes and types lead to faster execution. Avoid `delete`, dynamic property addition, and megamorphic call sites.
2. **Zero-copy is about avoiding unnecessary memory copies.** SharedArrayBuffer for worker threads, Buffer.from(arrayBuffer) for shared memory, sendfile(2) for static file serving.
3. **HTTP/2 is a significant improvement for APIs** — multiplexing, header compression, server push. HTTP/3 (QUIC) is handled at the edge, not in your Node.js process.
4. **gRPC outperforms REST for internal services** due to Protobuf's binary serialization and HTTP/2's multiplexing. Use REST for public APIs, gRPC for service-to-service.
5. **Serverless cold starts are manageable** — small bundles, lazy initialization, SDK reuse, provisioned concurrency for critical paths.
6. **Edge runtimes are powerful but constrained.** Use them for authentication, routing, and caching logic. Keep heavy processing in traditional serverless or containers.
7. **OpenTelemetry is the future of observability.** Vendor-agnostic instrumentation that works with any backend. Auto-instrumentation covers HTTP, database, and cache calls.
8. **Monitor the four golden signals:** latency, throughput, errors, and saturation. Event loop delay is the Node.js-specific saturation metric.
