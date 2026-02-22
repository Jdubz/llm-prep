# Module 08: Observability -- Cheat Sheet

---

## RED Method Template (for Services)

| Signal | Metric | Type | PromQL |
|--------|--------|------|--------|
| **Rate** | `http_requests_total` | Counter | `sum(rate(http_requests_total[5m])) by (service)` |
| **Errors** | `http_requests_total{status=~"5.."}` | Counter | `sum(rate(...{status=~"5.."}[5m])) / sum(rate(...[5m]))` |
| **Duration** | `http_request_duration_seconds` | Histogram | `histogram_quantile(0.99, sum(rate(..._bucket[5m])) by (le))` |

Use RED for any request-driven service (APIs, web servers, microservices).

---

## USE Method Template (for Resources)

| Signal | Resource | PromQL |
|--------|----------|--------|
| **Utilization** | CPU | `1 - avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) by (instance)` |
| **Utilization** | Memory | `1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)` |
| **Utilization** | Disk | `1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)` |
| **Saturation** | CPU | `node_load1 / count(node_cpu_seconds_total{mode="idle"}) by (instance)` |
| **Saturation** | Memory | `node_memory_SwapTotal_bytes - node_memory_SwapFree_bytes` |
| **Errors** | Disk | `rate(node_disk_io_errors_total[5m]) > 0` |
| **Errors** | Network | `rate(node_network_receive_errs_total[5m]) > 0` |

Use USE for infrastructure resources (servers, databases, load balancers, queues).

---

## Prometheus Metric Types

| Type | Behavior | Use For | Example |
|------|----------|---------|---------|
| **Counter** | Only goes up | Totals: requests, errors, bytes | `http_requests_total` |
| **Gauge** | Goes up and down | Current values: queue depth, temp | `db_connections_active` |
| **Histogram** | Buckets for distribution | Latency, response size | `http_request_duration_seconds` |
| **Summary** | Client-side quantiles | Pre-computed quantiles (rare) | `rpc_duration_seconds` |

**Rules of thumb:** Only increases? Counter. Can decrease? Gauge. Need percentiles? Histogram.

---

## PromQL Common Queries

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

---

## OpenTelemetry Setup Template

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

---

## SLI/SLO Template

**Availability SLI:** (non-5xx responses) / (total responses). **SLO:** 99.95% over 30-day rolling window. Error budget: 21.6 min/month.

**Latency SLI:** (requests < 500ms) / (total requests). **SLO:** 99% under 500ms over 30-day rolling window.

**Error Budget Policy:** >50%: deploy freely. 25-50%: increased caution. <25%: slow deploys, prioritize reliability. Exhausted: feature freeze.

---

## Alerting Rules Template

```yaml
groups:
- name: slo-alerts
  rules:
  - alert: HighBurnRate_Critical
    expr: |
      (sum(rate(http_requests_total{status=~"5.."}[1h])) by (service)
       / sum(rate(http_requests_total[1h])) by (service)) > (14.4 * 0.001)
      and
      (sum(rate(http_requests_total{status=~"5.."}[5m])) by (service)
       / sum(rate(http_requests_total[5m])) by (service)) > (14.4 * 0.001)
    for: 2m
    labels: { severity: critical }
    annotations:
      summary: "{{ $labels.service }} burning error budget at 14.4x"
      runbook_url: "https://wiki.internal/runbooks/{{ $labels.service }}"
  - alert: HighBurnRate_Warning
    expr: |
      (sum(rate(http_requests_total{status=~"5.."}[1d])) by (service)
       / sum(rate(http_requests_total[1d])) by (service)) > (3 * 0.001)
      and
      (sum(rate(http_requests_total{status=~"5.."}[2h])) by (service)
       / sum(rate(http_requests_total[2h])) by (service)) > (3 * 0.001)
    for: 15m
    labels: { severity: warning }
    annotations:
      summary: "{{ $labels.service }} burning error budget at 3x"
```

---

## Incident Response Checklist

**Detection (0-5 min):** Acknowledge alert. Verify it is real via dashboard. Assess severity (P1/P2/P3). For P1/P2: create incident channel.

**Response (5-30 min):** Assign IC for P1/P2. Post initial status. Update status page. Check: recent deploy? dependent services? infra issues?

**Mitigation:** Bad deploy: rollback. Traffic spike: scale up, rate limit. Dependency failure: circuit breaker. Update status page.

**Resolution:** Confirm metrics normal. Update status page: resolved. Schedule postmortem within 48 hours.

---

## Postmortem Template

```markdown
# Postmortem: [Title]
**Date/Duration/Severity/IC/Authors**

## Summary
[2-3 sentences: what happened, impact]

## Impact
Users affected, duration, revenue impact, SLO budget consumed

## Timeline
| Time | Event |
|------|-------|
| HH:MM | First sign / Alert / Acknowledged / Declared / Root cause / Fix / Resolved |

## Root Cause
[Technical explanation]

## Action Items
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
```

---

## Investigation Flow

```
ALERT (metric) -> DASHBOARD (golden signals) -> CORRELATE (deploy? dependency? spike?)
  -> TRACE (find failing request) -> INSPECT (which span?) -> LOGS (filter by trace_id)
  -> ROOT CAUSE -> MITIGATE -> VERIFY (metrics normal, burn rate drops)
```

**Key principle**: Metrics detect, traces locate, logs explain.
