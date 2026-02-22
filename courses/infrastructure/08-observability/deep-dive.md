# Module 08: Observability -- Deep Dive

## Table of Contents

1. [OpenTelemetry Collector Architecture](#opentelemetry-collector-architecture)
2. [Observability-Driven Development](#observability-driven-development)
3. [Continuous Profiling](#continuous-profiling)
4. [Real-User Monitoring](#real-user-monitoring)
5. [Synthetic Monitoring](#synthetic-monitoring)
6. [Observability for Serverless](#observability-for-serverless)
7. [Cost Management for Observability Data](#cost-management-for-observability-data)
8. [Building an Observability Platform](#building-an-observability-platform)
9. [Platform Comparison: Datadog vs New Relic vs Grafana Stack](#platform-comparison)

---

## OpenTelemetry Collector Architecture

### Overview

The OTel Collector is a vendor-agnostic proxy that receives, processes, and exports telemetry data. It is the central hub of an OTel deployment.

```
Applications          OTel Collector              Backends
+---------+          +----------------+          +----------+
| Service | --OTLP-->| Receivers      |          | Tempo    |
+---------+          |   v            |          +----------+
| Service | --OTLP-->| Processors     |--OTLP--->| Mimir    |
+---------+          |   v            |          +----------+
| Service | --OTLP-->| Exporters      |--------->| Loki     |
+---------+          +----------------+          +----------+
```

### Receivers

Ingest data into the collector. Key receivers: `otlp` (primary for OTel-instrumented apps), `prometheus` (scrape endpoints), `hostmetrics` (CPU/memory/disk/network), `filelog` (parse log files), `k8s_cluster` (Kubernetes metrics).

### Processors

Transform data between receiving and exporting. Run in order as a pipeline.

```yaml
processors:
  batch:
    send_batch_size: 8192
    timeout: 200ms
  memory_limiter:
    limit_mib: 4096
    spike_limit_mib: 512
  filter:
    traces:
      span:
      - 'attributes["http.route"] == "/healthz"'
  tail_sampling:
    decision_wait: 10s
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

Key processors: `batch` (efficient network transfer), `memory_limiter` (prevent OOM), `filter` (drop noise), `tail_sampling` (keep interesting traces), `attributes` (add/modify/remove), `k8s_attributes` (enrich with pod/namespace/node).

### Exporters and Pipeline Assembly

```yaml
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

**Agent mode (DaemonSet):** One collector per node, low-latency local collection, forwards to gateway. **Gateway mode (Deployment):** Central pool, handles tail-based sampling, horizontally scalable.

Recommended: Apps -> Agent (DaemonSet, lightweight) -> Gateway (Deployment, sampling/enrichment) -> Backends.

---

## Observability-Driven Development

Write observability into code from the start. Before writing a feature: define SLIs, identify needed metrics, plan trace spans. While coding: every significant operation gets a span, every decision branch is logged, every external call is instrumented, business metrics are recorded.

In code review, ask: "Where are the spans for this endpoint?" "What metrics tell us if this feature is healthy?" "How will we debug this in production?"

---

## Continuous Profiling

### Why Profile in Production

Load testing does not perfectly replicate production behavior. Continuous profiling reveals real performance characteristics: CPU flame graphs, memory allocation profiles, goroutine/thread profiles, lock contention, I/O wait.

### Tools

**Pyroscope (Grafana):** Agent-based, integrates with Grafana for unified dashboards. **Parca:** eBPF-based (no application changes), columnar storage, compare profiles between time periods or versions.

### Profile-Trace Correlation

Link profiling data to distributed traces: see exactly what CPU was doing during a slow span, in production, without reproducing the issue. This is the most powerful debugging tool available.

```
Trace: POST /api/orders (2.3s total)
  |-- Span: process_payment (1.8s)  <-- slow!
       |-- CPU Profile: 80% time in JSON serialization
```

---

## Real-User Monitoring

### What RUM Captures

**Browser:** Core Web Vitals (LCP, INP, CLS), navigation timing, resource timing, JS errors, user interaction latency. **Mobile:** App startup time, screen render time, network latency, crash reports, ANR events.

### RUM vs Synthetic Monitoring

| Aspect | RUM | Synthetic |
|--------|-----|-----------|
| Data source | Real users | Simulated requests |
| Coverage | Only pages users visit | Any defined scenario |
| Variability | High (diverse devices) | Low (controlled) |
| Baseline | No (varies) | Yes (consistent) |

**Use both:** RUM shows real user experience. Synthetic provides consistent baselines and catches issues on low-traffic pages before users do.

---

## Synthetic Monitoring

### Types

**API monitoring:** Scheduled HTTP requests to endpoints with assertions on status code, response time, and body content. Run from multiple geographic locations.

**Browser monitoring:** Scripted user flows (navigate, search, add to cart, checkout) executed on headless browsers. Measures full page load and interaction timing.

### Use Cases

Uptime monitoring, SSL certificate expiry detection, critical user flow validation, third-party dependency health, performance baselines, SLO measurement for availability.

---

## Observability for Serverless

### Challenges

No persistent process (no traditional agents), cold starts cause variable performance, short-lived functions make sampling difficult, inherently distributed via event triggers, vendor lock-in for native observability tools.

### Strategies

Structured logging is essential -- include request_id, function_name, memory_limit, remaining_time, cold_start flag. Use OTel Lambda layers for auto-instrumentation. Key metrics: invocation count, error rate, duration percentiles, cold start frequency, throttles, iterator age.

**Cost warning:** At high invocation rates, CloudWatch Logs costs can exceed Lambda compute cost. Use log filtering and sampling.

---

## Cost Management for Observability Data

### Cost Drivers

Log volume (verbose logging in high-traffic services), metric cardinality (high-cardinality labels explode time series), trace volume (100% sampling), retention duration, indexing depth.

### Optimization Strategies

**Control at source:** Do not log health checks or successful auth at INFO. Drop debug/trace in production. Never use user IDs or UUIDs as metric labels.

**Sample intelligently:** Tail-based sampling for traces (100% errors, 5% baseline). Log sampling for high-volume paths. Pre-aggregate metrics in the Collector.

**Tier storage:** Traces: 7 days hot, 30 days warm, drop. Metrics: 30 days full resolution, 1 year downsampled. Logs: 7 days hot, 30 days warm, 90 days cold.

**Use cost-efficient backends:** Loki over Elasticsearch for logs, Tempo over Jaeger for traces, Mimir or Thanos for long-term metrics.

**Monitor your monitoring:**
```promql
topk(10, sum(rate(log_bytes_total[1h])) by (service))
```

### Why Cardinality Matters Most

500,000 active time series at $0.10/1000/month = $50,000/month. Adding a single high-cardinality label (user_id with 1M users) to one metric can 1000x your metrics cost.

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

Maintain Collector fleet, operate storage backends (or manage SaaS contracts), provide instrumentation libraries, build shared dashboards and alerting templates, define SLO framework, manage cost and capacity planning.

### Self-Service Model

Application teams should independently: add custom metrics and spans, create dashboards, define SLOs and alerts using templates, query all telemetry through Grafana, get cost visibility.

---

## Platform Comparison

### Datadog vs New Relic vs Grafana Stack

| Aspect | Datadog | New Relic | Grafana Stack |
|--------|---------|-----------|---------------|
| **Model** | SaaS only | SaaS only | Self-hosted or Cloud |
| **Pricing** | Per host + per GB | Per GB ingested | Free (OSS) or per usage |
| **Cost at scale** | Expensive | Moderate | Cheapest |
| **Setup effort** | Low | Low | High (self) / Low (Cloud) |
| **Correlation** | Excellent | Good | Good |
| **Query language** | Proprietary | NRQL (SQL-like) | PromQL, LogQL, TraceQL |
| **Vendor lock-in** | High | Medium | Low (OTel-native, OSS) |

**Choose Datadog:** Best out-of-box experience, budget not primary concern, broad integrations, team lacks self-hosting expertise.

**Choose New Relic:** SaaS but cost-conscious, SQL-like queries preferred, generous free tier.

**Choose Grafana Stack:** Minimize vendor lock-in, team can self-host, cost at scale is primary concern, heavily invested in Prometheus/Kubernetes.

### Migration Path

Start with SaaS for speed. Instrument with OpenTelemetry from day one (vendor-neutral). When cost becomes painful, deploy OTel Collector as routing layer, route to both SaaS and self-hosted, then cut over.

**Key insight:** Always instrument with OpenTelemetry regardless of backend. This makes migration a configuration change, not a re-instrumentation project.

---

## Key Takeaways

1. **The OTel Collector is the control plane for telemetry**: Decouples instrumentation from backends, enables filtering, sampling, and routing.
2. **Continuous profiling closes the last debugging gap**: See CPU/memory behavior during slow spans, in production, without reproducing.
3. **RUM + Synthetic = complete picture**: Real user experience plus consistent baselines.
4. **Cost management is first-class**: Metric cardinality and log volume are the biggest cost drivers.
5. **Serverless observability requires different patterns**: No persistent agents, structured logging is critical.
6. **Instrument with OTel regardless of backend**: The single best decision for long-term flexibility.
7. **Build a self-service platform**: Application teams own their observability within platform team guardrails.
