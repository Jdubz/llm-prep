# Module 08: Advanced Observability

## OpenTelemetry Collector Architecture

### Overview

The OpenTelemetry Collector is a vendor-agnostic proxy that receives, processes, and exports telemetry data (traces, metrics, logs). It is the central hub of an OTel deployment.

```
Applications          OTel Collector              Backends
+---------+          +----------------+          +----------+
| Service | --OTLP-->| Receivers      |          | Jaeger   |
+---------+          |   |            |          +----------+
                     |   v            |          +----------+
+---------+          | Processors     |--OTLP--->| Tempo    |
| Service | --OTLP-->|   |            |          +----------+
+---------+          |   v            |          +----------+
                     | Exporters     -|--Prom--->| Prometheus|
+---------+          |                |          +----------+
| Service | --OTLP-->|                |          +----------+
+---------+          +----------------+          | Loki     |
                                                 +----------+
```

### Receivers

Receivers ingest data into the collector via network ports or by pulling from external sources.

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
  prometheus:
    config:
      scrape_configs:
      - job_name: 'kubernetes-pods'
        kubernetes_sd_configs:
        - role: pod
  hostmetrics:
    collection_interval: 30s
    scrapers:
      cpu:
      memory:
      disk:
      network:
```

Common receivers: `otlp` (primary for OTel apps), `prometheus` (scrape endpoints), `jaeger`/`zipkin` (migration), `hostmetrics` (system-level), `filelog` (parse log files), `k8s_events` (Kubernetes events).

### Processors

Processors transform data between receiving and exporting. They run in order as a pipeline.

```yaml
processors:
  resource:
    attributes:
    - key: environment
      value: production
      action: upsert
  batch:
    send_batch_size: 8192
    timeout: 200ms
  memory_limiter:
    check_interval: 1s
    limit_mib: 4096
    spike_limit_mib: 512
  filter:
    error_mode: ignore
    traces:
      span:
      - 'attributes["http.route"] == "/healthz"'
  tail_sampling:
    decision_wait: 10s
    num_traces: 100000
    policies:
    - name: errors-policy
      type: status_code
      status_code: { status_codes: [ERROR] }
    - name: latency-policy
      type: latency
      latency: { threshold_ms: 1000 }
    - name: probabilistic-policy
      type: probabilistic
      probabilistic: { sampling_percentage: 5 }
  attributes:
    actions:
    - key: db.statement
      action: hash
    - key: http.request.header.authorization
      action: delete
```

Key processors: `batch` (efficient network transfer), `memory_limiter` (prevent OOM), `filter` (drop noise like health checks), `tail_sampling` (keep interesting traces), `attributes` (add/modify/remove), `resource` (resource-level attributes), `k8s_attributes` (enrich with pod/namespace/node metadata).

### Exporters and Pipelines

```yaml
exporters:
  otlp/tempo:
    endpoint: tempo.monitoring:4317
  prometheusremotewrite:
    endpoint: http://mimir.monitoring:9009/api/v1/push
  loki:
    endpoint: http://loki.monitoring:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, k8s_attributes, tail_sampling, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp, prometheus, hostmetrics]
      processors: [memory_limiter, k8s_attributes, filter, batch]
      exporters: [prometheusremotewrite]
    logs:
      receivers: [otlp, filelog]
      processors: [memory_limiter, k8s_attributes, attributes, batch]
      exporters: [loki]
```

### Deployment Patterns

**Agent mode (DaemonSet):** One collector per node, low-latency local collection, handles host metrics and log collection, forwards to a central gateway.

**Gateway mode (Deployment):** Central pool, handles tail-based sampling (needs full traces), load-balanced, horizontally scalable.

**Recommended architecture:**
```
Apps -> Agent Collector (DaemonSet) -> Gateway Collector (Deployment) -> Backends
         (lightweight processing)      (sampling, enrichment, routing)
```

---

## Observability-Driven Development

### Concept

Write observability into your code from the start, not as an afterthought. Treat telemetry as a first-class feature.

**Traditional:** Write code, deploy, something breaks, add logging, redeploy, repeat.

**Observability-driven:** Define SLIs before writing code, instrument as you code (spans, metrics, structured logs), deploy with full visibility from day one, debug in production without code changes.

### Practices

**Before writing a feature:** Define SLIs (latency target, error budget), identify needed metrics, plan trace spans for the critical path.

**While writing code:**
```python
async def process_order(order):
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order.id)
        span.set_attribute("order.total", order.total)

        if order.total > 1000:
            logger.info("High-value order detected",
                extra={"order_id": order.id, "total": order.total})

        with tracer.start_as_current_span("validate_inventory"):
            inventory_result = await inventory.check(order.items)

        order_counter.add(1, {"payment_method": order.payment_method})
        order_value_histogram.record(order.total)
```

**In code review:** "Where are the spans?" "What metrics tell us if this is healthy?" "How will we debug this in production?"

---

## Continuous Profiling

### Why Profile in Production

Load testing does not perfectly replicate production behavior. Continuous profiling captures: CPU flame graphs, memory allocation profiles, goroutine/thread profiles, lock contention, I/O wait.

### Tools

**Pyroscope (Grafana):** Agent-based continuous profiling, integrates with Grafana for unified dashboards. Supports CPU, memory, and goroutine profiling.

**Parca:** Open-source, uses eBPF for low-overhead profiling (no application changes), columnar storage, compare profiles between time periods or versions.

**Key use cases:** Identify CPU regressions between deployments, find memory leaks over time, optimize hot paths identified in production (not synthetic benchmarks), correlate profiles with traces.

### Profile-Trace Correlation

Link profiling data to distributed traces -- see exactly what CPU was doing during a slow span:

```
Trace: POST /api/orders (2.3s total)
  |-- Span: validate_order (50ms)
  |-- Span: check_inventory (200ms)
  |-- Span: process_payment (1.8s)  <-- slow!
       |-- CPU Profile: 80% in JSON serialization
       |-- Flame graph: deep recursion in custom serializer
```

This is the most powerful production debugging tool: no need to reproduce the issue.

---

## Real-User Monitoring

### What RUM Captures

**Browser:** Core Web Vitals (LCP, INP, CLS), navigation timing (DNS, TTFB, DOM parsing), resource timing, JavaScript errors, user interaction latency.

**Mobile:** App startup time (cold/warm), screen render time, network latency, crash reports, ANR events.

### RUM vs Synthetic Monitoring

| Aspect | RUM | Synthetic |
|--------|-----|-----------|
| Data source | Real users | Simulated requests |
| Coverage | Only pages users visit | Any defined scenario |
| Variability | High (diverse devices, networks) | Low (controlled) |
| Baseline | No (varies) | Yes (consistent conditions) |
| Cost | Per-event billing | Per-check billing |

**Use both:** RUM shows real user experience. Synthetic provides consistent baselines and catches issues before users do (especially on low-traffic pages).

### RUM Implementation

```javascript
import { datadogRum } from '@datadog/browser-rum';

datadogRum.init({
  applicationId: 'app-id',
  clientToken: 'pub-client-token',
  service: 'web-app',
  env: 'production',
  version: '2.3.1',
  sessionSampleRate: 100,
  sessionReplaySampleRate: 20,
  trackUserInteractions: true,
  trackResources: true,
  defaultPrivacyLevel: 'mask-user-input',
});
```

---

## Synthetic Monitoring

### Types

**API monitoring:** Scheduled HTTP requests to endpoints with assertions on status code, response time, and body content. Run from multiple geographic locations at regular intervals.

**Browser monitoring:** Scripted user flows (navigate, search, add to cart, checkout) executed on headless browsers. Measures full page load and interaction timing.

```javascript
step('Navigate to homepage', async () => {
  await page.goto('https://www.example.com');
  await page.waitForSelector('#main-content');
});

step('Search for product', async () => {
  await page.fill('#search-input', 'widget');
  await page.click('#search-button');
  await page.waitForSelector('.search-results');
});
```

### Use Cases

Uptime monitoring from multiple regions, SSL certificate expiry detection, critical user flow validation, third-party dependency health checks, performance baselines, SLO measurement for availability.

---

## Observability for Serverless

### Challenges

No persistent process (no traditional agents), cold starts cause variable performance, short-lived functions make sampling difficult, inherently distributed via event triggers, vendor lock-in for native observability tools.

### Strategies

**Structured logging is essential:**
```python
def handler(event, context):
    logger.info(json.dumps({
        "message": "Processing order",
        "request_id": context.aws_request_id,
        "function_name": context.function_name,
        "memory_limit_mb": context.memory_limit_in_mb,
        "remaining_time_ms": context.get_remaining_time_in_millis(),
        "cold_start": getattr(context, '_cold_start', True),
    }))
```

**OTel for Lambda:** Use OTel Lambda layers for auto-instrumentation with OTLP export to a collector gateway.

**Key metrics:** Invocation count, error rate, duration (p50/p95/p99), cold start frequency and duration, concurrent execution (approaching limits?), throttles, iterator age.

**Cost warning:** At high invocation rates, CloudWatch Logs costs can exceed Lambda compute cost. Use log filtering and sampling.

---

## Cost Management for Observability Data

### The Cost Problem

Observability data grows with traffic, services, and instrumentation. Key cost drivers: log volume, metric cardinality (high-cardinality labels explode time series count), trace volume, retention duration, indexing depth.

### Optimization Strategies

**1. Control at the source:** Do not log health checks. Drop debug logs in production. Never use user IDs or UUIDs as metric labels.

**2. Sample intelligently:** Tail-based sampling for traces (100% errors, 5% baseline). Log sampling for high-volume paths. Pre-aggregate metrics in the Collector.

**3. Tier storage:**

| Data Type | Hot (fast) | Warm (slower) | Cold (archive) |
|-----------|-----------|---------------|----------------|
| Traces | 7 days | 30 days | Drop |
| Metrics | 30 days (full res) | 1 year (downsampled) | 2+ years |
| Logs | 7 days | 30 days | 90 days |

**4. Cost-efficient backends:** Loki over Elasticsearch for logs, Tempo over Jaeger for traces, Mimir or Thanos for long-term metrics.

**5. Monitor your monitoring:**
```promql
topk(10, sum(rate(log_bytes_total[1h])) by (service))
```

### Why Cardinality Matters Most

500,000 active time series at $0.10/1000/month = $50,000/month. Adding a single high-cardinality label (user_id with 1M users) to one metric can 1000x your metrics cost. Metric cardinality is the number one cost concern.

---

## Building an Observability Platform

### Architecture

```
Applications (OTel SDKs)
        |
OTel Collector (Agent - DaemonSet)
        |
OTel Collector (Gateway - Deployment, HA)
   /       |        \
Mimir    Tempo     Loki
   \       |        /
      Grafana
        |
   Alertmanager -> PagerDuty / Slack
```

### Platform Team Responsibilities

Maintain Collector fleet (agent + gateway), operate storage backends or manage SaaS contracts, provide instrumentation libraries and docs, build shared dashboards and alerting templates, define SLO framework and tooling, manage cost and capacity planning, on-call for the observability platform itself.

### Self-Service Model

Application teams independently: add custom metrics and spans, create Grafana dashboards, define SLOs and alerts using platform templates, query all telemetry through unified Grafana, get cost visibility for their usage.

---

## Platform Comparison: Datadog vs New Relic vs Grafana Stack

| Aspect | Datadog | New Relic | Grafana Stack |
|--------|---------|-----------|---------------|
| **Model** | SaaS only | SaaS only | Self-hosted or Cloud |
| **Pricing** | Per host + per GB | Per GB ingested | Free (OSS) or usage-based |
| **Cost at scale** | Expensive | Moderate | Cheapest |
| **Setup effort** | Low | Low | High (self) / Low (Cloud) |
| **Traces** | Datadog APM | Distributed Tracing | Tempo |
| **Metrics** | Custom metrics | NRQL-queryable | Prometheus/Mimir |
| **Logs** | Log Management | Log Management | Loki |
| **Profiling** | Continuous Profiler | Not built-in | Pyroscope |
| **RUM** | Yes | Yes | Grafana Faro (newer) |
| **Query language** | Proprietary | NRQL (SQL-like) | PromQL, LogQL, TraceQL |
| **Vendor lock-in** | High | Medium | Low (OTel-native, OSS) |

### Decision Framework

**Choose Datadog:** Best out-of-box experience, budget not primary concern, 700+ integrations, team lacks self-hosting expertise.

**Choose New Relic:** SaaS but cost-conscious, prefer SQL-like queries (NRQL), generous free tier for small teams.

**Choose Grafana Stack:** Minimize vendor lock-in, team can self-host, cost at scale is primary concern, full control over data, heavily invested in Prometheus/K8s.

### Migration Path

Start with SaaS (low effort, immediate value). Instrument with OpenTelemetry from day one (vendor-neutral). When cost becomes painful, deploy OTel Collector as routing layer, dual-export to SaaS and self-hosted, then cut over.

**Key insight:** Always instrument with OpenTelemetry regardless of backend. This makes migration a configuration change, not a re-instrumentation project.

---

**Q: How would you implement distributed tracing across 50 microservices?**

A: Incremental rollout. Deploy OTel Collector as DaemonSet. Start with auto-instrumentation (covers 80% of useful data). Add manual spans for the top 3-5 user-facing request flows. Implement tail-based sampling (100% errors, 100% slow, 5% baseline). Verify W3C traceparent propagation across all inter-service communication. Expand gradually.

### Related Reading

- [Module 08: Logging, Metrics, and Tracing](01-logging-metrics-and-tracing.md) -- the three pillars and instrumentation fundamentals that the OTel Collector receives, processes, and exports
- [Module 08: SLOs, Alerting, and Incident Response](02-slos-alerting-and-incident-response.md) -- SLO-based alerting consumes the metrics that flow through the Collector; incident response relies on the observability platform described here
- [Module 03: Caching Patterns and Redis Basics](../03-caching/01-caching-patterns-and-redis-basics.md) -- cache hit rates are a key metric flowing through the observability pipeline; Redis is often used for real-time dashboards
- [Module 04: Message Queue Operations](../04-message-queues/03-message-queue-operations-and-patterns.md) -- Kafka is used as the log transport in many observability architectures; consumer lag monitoring is a key observability use case
- [Module 05: Advanced Load Balancing Patterns](../05-load-balancing/03-advanced-load-balancing-patterns.md) -- CDN and global load balancing architectures require RUM and synthetic monitoring to measure end-user experience across regions
- [Module 06: Kubernetes Advanced Patterns](../06-containers-orchestration/03-kubernetes-advanced-patterns.md) -- the OTel Collector DaemonSet and Gateway deployment patterns run on Kubernetes; service mesh telemetry feeds into the observability platform
- [Module 07: Infrastructure and GitOps](../07-cicd/03-infrastructure-and-gitops.md) -- the observability platform itself should be deployed via GitOps (ArgoCD) for reproducibility and auditability
- [Module 09: Compliance and Advanced Security](../09-security/03-compliance-and-advanced-security.md) -- observability data may contain sensitive information; the Collector's attribute processor can hash or delete PII before export

### Key Takeaways

1. **The OTel Collector is the control plane for telemetry**: Decouples instrumentation from backends, enables filtering, sampling, routing.
2. **Continuous profiling closes the last gap**: See CPU/memory behavior during slow spans, in production, without reproducing.
3. **RUM + Synthetic = complete picture**: Real experience plus consistent baselines.
4. **Cost management is first-class**: Metric cardinality and log volume are the biggest drivers.
5. **Serverless observability requires different patterns**: No agents, structured logging is critical.
6. **Instrument with OTel regardless of backend**: The single best decision for long-term flexibility.
7. **Build a self-service platform**: Application teams own observability within platform team guardrails.
