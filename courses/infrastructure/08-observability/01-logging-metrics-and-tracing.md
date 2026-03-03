# Module 08: Logging, Metrics, and Tracing

## Overview

Observability is the ability to understand the internal state of a system by examining its external outputs. For senior engineers, observability goes beyond "add logging and dashboards" -- it means building systems where any question about behavior can be answered without deploying new code.

---

## The Three Pillars

### Logs, Metrics, Traces -- Complementary, Not Redundant

Each pillar answers a different question:

| Pillar | What It Answers | Granularity | Cost Profile |
|--------|----------------|-------------|--------------|
| **Logs** | "What happened?" | Individual events | High volume, high cost at scale |
| **Metrics** | "How is the system performing?" | Aggregated time series | Low volume, low cost |
| **Traces** | "Why is this request slow?" | Per-request path | Medium volume, medium cost |

**Why you need all three:**
- Metrics tell you something is wrong (error rate spike)
- Traces tell you where in the request path the problem is (the database call in service B)
- Logs tell you exactly what happened (the specific SQL query that failed)

```
Alert fires (metric) --> Investigate trace for a failing request --> Read logs for the specific error
```

**Investigation flow:**
```
ALERT (metric) -> DASHBOARD (golden signals) -> CORRELATE (deploy? dependency? spike?)
  -> TRACE (find failing request) -> INSPECT (which span?) -> LOGS (filter by trace_id)
  -> ROOT CAUSE -> MITIGATE -> VERIFY (metrics normal, burn rate drops)
```

**Key principle**: Metrics detect, traces locate, logs explain.

### The Observability Maturity Model

| Level | Capability |
|-------|-----------|
| 0 | No observability. SSH into production and tail logs. |
| 1 | Centralized logging. Basic metrics dashboards. |
| 2 | Structured logging with correlation IDs. SLOs defined. Basic tracing. |
| 3 | Full distributed tracing. SLO-based alerting. Automated incident response. |
| 4 | Observability-driven development. Production debugging without new deploys. |

---

## Structured Logging

### JSON Logs

Unstructured logs are for humans reading a terminal. Structured logs are for machines parsing at scale.

**Unstructured (bad for aggregation):**
```
2024-01-15 10:23:45 ERROR Failed to process order #12345 for user john@example.com: insufficient inventory
```

**Structured (good for aggregation):**
```json
{
  "timestamp": "2024-01-15T10:23:45.123Z",
  "level": "ERROR",
  "message": "Failed to process order",
  "service": "order-service",
  "version": "2.3.1",
  "trace_id": "abc123def456",
  "span_id": "789ghi",
  "order_id": "12345",
  "user_id": "usr_789",
  "error": "insufficient_inventory",
  "sku": "WIDGET-001",
  "requested_quantity": 5,
  "available_quantity": 2
}
```

**Benefits:** Query by any field, aggregate and count, correlate across services using trace_id, build dashboards from log data, machine-parseable by default.

### Log Levels

| Level | When to Use | Example |
|-------|------------|---------|
| **TRACE** | Extremely detailed, rarely enabled | Function entry/exit, variable values |
| **DEBUG** | Diagnostic information for developers | SQL queries, cache hits/misses |
| **INFO** | Normal operational events | Request completed, job started, user logged in |
| **WARN** | Unexpected but recoverable situations | Retry attempt, deprecated API used, high latency |
| **ERROR** | Operation failed but service continues | Failed to process request, external service down |
| **FATAL** | Service cannot continue, shutting down | Cannot connect to database, out of memory |

**Common mistake**: Logging expected outcomes at WARN or ERROR. A user entering an invalid email is INFO (normal application behavior), not ERROR (unexpected failure).

### Correlation IDs

A correlation ID ties together all log entries for a single request, across all services. Generate at the API gateway, propagate via `X-Request-ID` header, attach to async context for automatic inclusion in all logs.

```javascript
// Express middleware to extract or generate correlation ID
app.use((req, res, next) => {
  const correlationId = req.headers['x-request-id'] || crypto.randomUUID();
  req.correlationId = correlationId;
  res.setHeader('X-Request-ID', correlationId);
  asyncLocalStorage.run({ correlationId }, () => next());
});
```

### Log Aggregation Platforms

| Platform | Type | Strengths |
|----------|------|-----------|
| **ELK Stack** (Elasticsearch, Logstash, Kibana) | Self-hosted / Cloud | Full-text search, powerful queries, mature |
| **Grafana Loki** | Self-hosted / Cloud | Lightweight, label-indexed (not full-text), cost-efficient |
| **Datadog Logs** | SaaS | Integrated with metrics/traces, easy setup |
| **Splunk** | SaaS / Self-hosted | Enterprise, powerful SPL query language |

**Loki vs Elasticsearch:** Loki indexes labels only (much cheaper to operate). Elasticsearch indexes everything (faster full-text search). Loki is ideal when you filter by labels and grep within results. Elasticsearch is ideal for arbitrary text search across all logs.

### Avoiding Log Noise

- **Do not log sensitive data**: PII, passwords, tokens, credit card numbers
- **Do not log per-request at DEBUG in production**: Use sampling or dynamic log levels
- **Do not log successful health checks**: They dominate log volume with zero signal
- **Do log at service boundaries**: Incoming requests, outgoing requests, key decisions
- **Use sampling for high-volume paths**: Log 1% of successful requests, 100% of errors
- **Set retention policies**: 7 days for DEBUG, 30 days for INFO, 90+ days for ERROR

---

## Metrics

### RED Method (for Services)

The RED method gives you the three signals that matter for any request-driven service.

| Signal | What to Measure | Prometheus Metric Type |
|--------|----------------|----------------------|
| **R**ate | Requests per second | Counter |
| **E**rrors | Failed requests per second | Counter |
| **D**uration | Request latency distribution | Histogram |

```promql
# Rate: requests per second over last 5 minutes
rate(http_requests_total[5m])

# Error rate: percentage of 5xx responses
rate(http_requests_total{status=~"5.."}[5m])
  / rate(http_requests_total[5m])

# Duration: 99th percentile latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

### RED Method Template

| Signal | Metric | Type | PromQL |
|--------|--------|------|--------|
| **Rate** | `http_requests_total` | Counter | `sum(rate(http_requests_total[5m])) by (service)` |
| **Errors** | `http_requests_total{status=~"5.."}` | Counter | `sum(rate(...{status=~"5.."}[5m])) / sum(rate(...[5m]))` |
| **Duration** | `http_request_duration_seconds` | Histogram | `histogram_quantile(0.99, sum(rate(..._bucket[5m])) by (le))` |

### USE Method (for Resources)

The USE method covers infrastructure resources (CPU, memory, disk, network).

| Signal | What to Measure | Example |
|--------|----------------|---------|
| **U**tilization | % of resource capacity used | CPU usage 75% |
| **S**aturation | Work queued beyond capacity | Run queue length, swap usage |
| **E**rrors | Resource error events | Disk errors, NIC errors, OOM kills |

### USE Method PromQL

| Signal | Resource | PromQL |
|--------|----------|--------|
| **Utilization** | CPU | `1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)` |
| **Utilization** | Memory | `1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)` |
| **Utilization** | Disk | `1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)` |
| **Saturation** | CPU | `node_load1 / count(node_cpu_seconds_total{mode="idle"}) by (instance)` |
| **Saturation** | Memory | `node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes` |
| **Errors** | Disk | `rate(node_disk_io_errors_total[5m]) > 0` |
| **Errors** | Network | `rate(node_network_receive_errs_total[5m]) > 0` |

### Prometheus Metric Types

| Type | Behavior | Use For | Example |
|------|----------|---------|---------|
| **Counter** | Only goes up | Totals: requests, errors, bytes | `http_requests_total` |
| **Gauge** | Goes up and down | Current values: queue depth, temp | `db_connections_active` |
| **Histogram** | Buckets for distribution | Latency, response size | `http_request_duration_seconds` |
| **Summary** | Client-side quantiles | Pre-computed quantiles (rare) | `rpc_duration_seconds` |

**Rules of thumb:** Only increases? Counter. Can decrease? Gauge. Need percentiles? Histogram.

**Histogram vs Summary:** Histogram allows server-side aggregation across instances and is preferred for most use cases. Summary cannot aggregate across instances -- use only when exact quantiles are critical.

### Instrumentation Example

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    'http_requests_total', 'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds', 'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

@app.route('/api/orders', methods=['POST'])
def create_order():
    with REQUEST_LATENCY.labels(method='POST', endpoint='/api/orders').time():
        try:
            result = process_order()
            REQUEST_COUNT.labels(method='POST', endpoint='/api/orders', status='200').inc()
            return result
        except Exception:
            REQUEST_COUNT.labels(method='POST', endpoint='/api/orders', status='500').inc()
            raise
```

### PromQL Common Queries

```promql
# Request rate per service
sum(rate(http_requests_total[5m])) by (service)

# Error percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
  / sum(rate(http_requests_total[5m])) by (service) * 100

# P50 / P95 / P99 latency
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))

# Top 5 services by error rate
topk(5, sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
       / sum(rate(http_requests_total[5m])) by (service))

# CPU throttling per pod
sum(rate(container_cpu_cfs_throttled_periods_total[5m])) by (pod)
  / sum(rate(container_cpu_cfs_periods_total[5m])) by (pod) * 100

# SLO burn rate (99.9% availability)
(sum(rate(http_requests_total{status=~"5.."}[1h]))
  / sum(rate(http_requests_total[1h]))) / 0.001
```

**Label cardinality warning:** Every unique combination of label values creates a new time series. Labels with high cardinality (user IDs, request IDs) will overwhelm Prometheus. Use labels for low-cardinality dimensions only (method, status code, service name).

---

## Distributed Tracing

### OpenTelemetry

OpenTelemetry (OTel) is the industry standard for vendor-neutral instrumentation.

**Core Concepts:** A Trace is the entire journey of a request across services. A Span is a single operation within a trace (name, start time, duration, attributes, events, status, child spans).

**Context Propagation:** Trace context must be passed between services for spans to be linked. The W3C Trace Context standard (`traceparent` header) is the propagation format. OTel handles this automatically for HTTP, gRPC, and messaging.

### Auto-Instrumentation

OTel SDKs auto-instrument common frameworks with minimal code changes:

```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { Resource } = require('@opentelemetry/resources');

const sdk = new NodeSDK({
  resource: new Resource({
    'service.name': 'order-service',
    'service.version': process.env.APP_VERSION || '0.0.0',
    'deployment.environment': process.env.NODE_ENV || 'development',
  }),
  traceExporter: new OTLPTraceExporter({
    url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318/v1/traces',
  }),
  instrumentations: [getNodeAutoInstrumentations({
    '@opentelemetry/instrumentation-fs': { enabled: false },
  })],
});
sdk.start();
process.on('SIGTERM', () => sdk.shutdown());
```

Covers: HTTP clients/servers (Express, Fastify), database clients (pg, mysql2, redis), gRPC, message brokers (Kafka, RabbitMQ), AWS SDK calls.

### Manual Spans

For business logic that auto-instrumentation does not cover, create spans explicitly:

```javascript
const { trace } = require('@opentelemetry/api');
const tracer = trace.getTracer('order-service');

async function processOrder(order) {
  return tracer.startActiveSpan('process_order', async (span) => {
    try {
      span.setAttribute('order.id', order.id);
      span.setAttribute('order.item_count', order.items.length);

      await tracer.startActiveSpan('check_inventory', async (inventorySpan) => {
        const available = await inventoryService.check(order.items);
        inventorySpan.setAttribute('inventory.all_available', available);
        inventorySpan.end();
      });

      span.setStatus({ code: SpanStatusCode.OK });
      return { success: true };
    } catch (error) {
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
      span.recordException(error);
      throw error;
    } finally {
      span.end();
    }
  });
}
```

### Sampling Strategies

At scale, tracing 100% of requests is prohibitively expensive. A service handling 10,000 RPS generates 864M spans/day -- storing all of them is wasteful because most represent healthy, uninteresting requests.

| Strategy | Description | Tradeoff |
|----------|------------|----------|
| **Head-based** | Decide at trace start (e.g., 10% random) | Simple, misses interesting traces |
| **Tail-based** | Decide after completion (keep errors, slow) | Captures all interesting, requires buffering |
| **Rate-limiting** | N traces per second | Predictable cost, may miss bursts |
| **Priority** | Always sample errors and slow requests | Best signal, more complex setup |

**Choosing a strategy:** Head-based sampling is the simplest to implement (a random decision at the trace root) but it cannot distinguish interesting traces from uninteresting ones until it is too late -- an error that occurs 3 services deep was already sampled or not at the entry point. Tail-based sampling solves this by buffering complete traces before making the sampling decision, keeping 100% of errors and slow requests while sampling a small percentage of healthy traffic. The trade-off is that tail-based sampling requires the OTel Collector Gateway to hold traces in memory until they complete (typically 10-30 seconds), which increases infrastructure cost. The recommended production approach is tail-based sampling with rules: keep all errors, keep all requests above a latency threshold, and probabilistically sample 1-5% of the rest.

### Tracing Backends

| Platform | Type | Strengths |
|----------|------|-----------|
| **Jaeger** | Open source | Mature, Kubernetes-native, good UI |
| **Grafana Tempo** | Open source | Cost-efficient (object storage), integrates with Grafana |
| **Datadog APM** | SaaS | Full-stack integration, strong analytics |
| **Honeycomb** | SaaS | High-cardinality queries, BubbleUp for anomaly detection |

**Choosing a backend:** If you are already using the Grafana stack (Prometheus, Loki), Tempo is the natural choice -- it stores traces in object storage (S3) which is dramatically cheaper than Elasticsearch-backed Jaeger at scale. If you want a zero-ops SaaS experience with deep integration across logs, metrics, and traces, Datadog APM is the fastest to adopt but the most expensive long-term. Honeycomb excels at exploratory debugging with high-cardinality data (query by user ID, request ID, or any attribute) but is a specialized tool rather than a full observability platform. Regardless of backend, instrument with OpenTelemetry -- this makes switching backends a configuration change rather than a re-instrumentation effort.

---

## Related Reading

- [Module 08: SLOs, Alerting, and Incident Response](02-slos-alerting-and-incident-response.md) -- builds on the metrics and PromQL covered here to define SLIs, SLOs, error budgets, and burn rate alerting rules
- [Module 08: Advanced Observability](03-advanced-observability.md) -- the OTel Collector architecture, continuous profiling, RUM, synthetic monitoring, and cost management for the telemetry data described here
- [Module 00: Computing Fundamentals](../00-computing-fundamentals.md) -- the latency numbers and networking fundamentals that inform what to measure and where to place instrumentation
- [Module 02: Database Platforms and Scaling](../02-databases-at-scale/03-database-platforms-and-scaling.md) -- monitoring database performance (connection pool utilization, query latency, replication lag) with the Prometheus metric types and PromQL queries covered here
- [Module 03: Caching Patterns and Redis Basics](../03-caching/01-caching-patterns-and-redis-basics.md) -- cache hit rate is a critical metric; the RED method applies to cache performance monitoring
- [Module 04: Message Brokers](../04-message-queues/01-message-brokers-kafka-sqs-rabbitmq.md) -- distributed tracing spans message producers and consumers; consumer lag and DLQ depth are key metrics to monitor
- [Module 05: Load Balancing Fundamentals](../05-load-balancing/01-load-balancing-fundamentals.md) -- the RED method (Rate, Errors, Duration) is how you monitor services behind load balancers
- [Module 05: Circuit Breakers and Retry Strategies](../05-load-balancing/02-circuit-breakers-and-retry-strategies.md) -- circuit breaker state transitions and retry rates should be instrumented as metrics
- [Module 06: Kubernetes Core and Operations](../06-containers-orchestration/02-kubernetes-core-and-operations.md) -- Kubernetes exposes container-level metrics (CPU, memory, restarts) that feed into the USE method for resource monitoring
