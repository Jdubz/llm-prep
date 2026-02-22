# Module 08: Observability

## Overview

Observability is the ability to understand the internal state of a system by examining its external outputs. For senior engineers, observability goes beyond "add logging and dashboards" -- it means building systems where any question about behavior can be answered without deploying new code. This module covers the three pillars (logs, metrics, traces), SLI/SLO-based reliability engineering, alerting that does not cause fatigue, incident response, and the organizational practices that turn data into actionable insight.

---

## Table of Contents

1. [The Three Pillars](#the-three-pillars)
2. [Structured Logging](#structured-logging)
3. [Metrics](#metrics)
4. [Distributed Tracing](#distributed-tracing)
5. [SLIs, SLOs, and SLAs](#slis-slos-and-slas)
6. [Alerting Strategies](#alerting-strategies)
7. [Incident Response](#incident-response)
8. [Dashboards](#dashboards)
9. [Interview Questions](#interview-questions)

---

## The Three Pillars

### Logs, Metrics, Traces -- Complementary, Not Redundant

| Pillar | What It Answers | Granularity | Cost Profile |
|--------|----------------|-------------|--------------|
| **Logs** | "What happened?" | Individual events | High volume, high cost at scale |
| **Metrics** | "How is the system performing?" | Aggregated time series | Low volume, low cost |
| **Traces** | "Why is this request slow?" | Per-request path | Medium volume, medium cost |

**Why you need all three:** Metrics tell you something is wrong (error rate spike). Traces tell you where in the request path the problem is. Logs tell you exactly what happened.

```
Alert fires (metric) --> Investigate trace for a failing request --> Read logs for the specific error
```

---

## Structured Logging

### JSON Logs

Unstructured logs are for humans reading a terminal. Structured logs are for machines parsing at scale.

```json
{
  "timestamp": "2024-01-15T10:23:45.123Z",
  "level": "ERROR",
  "message": "Failed to process order",
  "service": "order-service",
  "trace_id": "abc123def456",
  "order_id": "12345",
  "error": "insufficient_inventory",
  "requested_quantity": 5,
  "available_quantity": 2
}
```

Benefits: query by any field, aggregate and count, correlate across services via trace_id, machine-parseable by default.

### Log Levels

| Level | When to Use |
|-------|------------|
| **DEBUG** | Diagnostic information for developers (SQL queries, cache hits) |
| **INFO** | Normal operational events (request completed, job started) |
| **WARN** | Unexpected but recoverable (retry attempt, deprecated API used) |
| **ERROR** | Operation failed but service continues |
| **FATAL** | Service cannot continue, shutting down |

**Common mistake**: Logging expected outcomes at ERROR. A user entering an invalid email is INFO, not ERROR.

### Correlation IDs

A correlation ID ties together all log entries for a single request across all services. Generate at the API gateway, propagate via `X-Request-ID` header, attach to async context for automatic inclusion in all logs.

### Log Aggregation

**ELK Stack:** Full-text search, powerful queries, mature. **Grafana Loki:** Label-indexed (not full-text), cost-efficient. **Datadog Logs:** Integrated with metrics/traces. **Splunk:** Enterprise, powerful SPL.

Loki vs Elasticsearch: Loki indexes labels only (cheaper), Elasticsearch indexes everything (faster search).

### Avoiding Log Noise

Do not log: sensitive data (PII, tokens), per-request at DEBUG in production, successful health checks. Do log: service boundaries, errors at 100%, successful requests at 1% sampling. Set retention policies by level.

---

## Metrics

### RED Method (for Services)

| Signal | What to Measure | Prometheus Type |
|--------|----------------|----------------|
| **R**ate | Requests per second | Counter |
| **E**rrors | Failed requests per second | Counter |
| **D**uration | Latency distribution | Histogram |

```promql
rate(http_requests_total[5m])
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

### USE Method (for Resources)

| Signal | What to Measure | Example |
|--------|----------------|---------|
| **U**tilization | % capacity used | CPU usage 75% |
| **S**aturation | Work queued beyond capacity | Run queue length, swap usage |
| **E**rrors | Resource error events | Disk errors, OOM kills |

### Prometheus Metric Types

| Type | Description | Use Case |
|------|------------|----------|
| **Counter** | Monotonically increasing | Total requests, errors, bytes |
| **Gauge** | Goes up and down | Queue depth, connections, temperature |
| **Histogram** | Distribution in buckets | Latency, response sizes |
| **Summary** | Client-side quantiles | Exact quantiles (prefer histogram) |

Histogram vs Summary: Histogram allows server-side aggregation across instances and is preferred for most use cases. Summary cannot aggregate across instances.

### PromQL Basics

```promql
sum(rate(http_requests_total[5m])) by (endpoint)           # rate by endpoint
topk(5, sum(rate(http_requests_total[5m])) by (endpoint))  # top 5 by rate
(sum(rate(http_requests_total{status=~"5.."}[5m])) by (ep)
  / sum(rate(http_requests_total[5m])) by (ep)) > 0.10     # >10% error rate
```

### Custom Metrics

Instrument business logic: orders created, order value distribution, cart abandonment, cache hit/miss rates, queue depth. **Label cardinality warning:** Every unique label combination creates a new time series. Never use user IDs or request IDs as labels.

---

## Distributed Tracing

### OpenTelemetry

**Core concepts:** A Trace is the entire journey of a request. A Span is a single operation (name, duration, attributes, status, child spans). Context propagation passes trace context between services via W3C `traceparent` header.

### Auto-Instrumentation

OTel SDKs auto-instrument HTTP, database, gRPC, and messaging calls with minimal code changes:

```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: 'http://otel-collector:4318/v1/traces' }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
```

### Manual Spans

For business logic not covered by auto-instrumentation, create spans explicitly with attributes, status, and exception recording.

### Sampling Strategies

| Strategy | Description | Tradeoff |
|----------|------------|----------|
| **Head-based** | Decide at trace start | Simple, misses interesting traces |
| **Tail-based** | Decide after completion | Captures all errors/slow, requires buffering |
| **Rate-limiting** | N traces per second | Predictable cost, may miss bursts |
| **Priority** | Always sample errors/slow | Best signal, more complex |

### Tracing Backends

**Jaeger:** Mature, Kubernetes-native. **Grafana Tempo:** Cost-efficient (object storage). **Datadog APM:** Full-stack integration. **Honeycomb:** High-cardinality queries.

---

## SLIs, SLOs, and SLAs

### Definitions

- **SLI**: A quantitative measure of service behavior ("what are we measuring?")
- **SLO**: A target value for an SLI ("what is acceptable?")
- **SLA**: A contractual commitment with consequences ("what did we promise?")

SLO should be stricter than SLA. Missing your SLO gives you time to fix before breaching your SLA.

### Defining Good SLIs

SLIs should measure what users experience, not internal state. "CPU utilization" is not an SLI. "Successful request rate" is. Measure at the edge when possible.

| Service Type | SLI | Measurement |
|-------------|-----|-------------|
| HTTP API | Availability | (non-5xx responses) / (total responses) |
| HTTP API | Latency | (requests < 500ms) / (total requests) |
| Data pipeline | Freshness | current_time - last_successful_run |
| Storage | Durability | 1 - (data_loss_events / total_objects) |

### Error Budgets

Error budget = inverse of SLO. At 99.9% availability: 43.2 minutes of downtime per month. At 99.95%: 21.6 minutes. At 99.99%: 4.32 minutes.

**Policy:** Budget >50% remaining: deploy freely. Budget <25%: slow down, focus on reliability. Budget exhausted: freeze features, all effort on reliability.

### Burn Rate Alerting

Alert based on how fast you are consuming your error budget, not on static thresholds.

| Severity | Burn Rate | Long Window | Short Window |
|----------|-----------|-------------|--------------|
| Page (critical) | 14.4x | 1 hour | 5 minutes |
| Page (high) | 6x | 6 hours | 30 minutes |
| Ticket (medium) | 3x | 1 day | 2 hours |

Both windows must fire simultaneously. Long window catches sustained issues; short window confirms it is still happening.

---

## Alerting Strategies

### Reducing Alert Fatigue

Symptoms: acknowledging without investigating, permanent suppression, "ignore these alerts" tribal knowledge. Solutions: delete alerts with no action in 30 days, use burn rate instead of static thresholds, route by severity (not everything is a page), aggregate related alerts.

### Actionable Alerts

Every alert answers: (1) What is happening? (2) Why does it matter? (3) What should I do?

```
FIRING: Order Processing Degraded
  Summary: Order service p99 latency exceeded 2s for 15 minutes
  Impact: Slow checkout. Error rate 3.2% (SLO: 0.1%). Burn rate: 32x.
  Runbook: https://wiki.internal/runbooks/order-service-latency
```

### Severity Levels

| Severity | Response Time | Notification |
|----------|--------------|-------------|
| **P1 - Critical** | Immediate | Page on-call |
| **P2 - High** | < 30 min | Page during business hours |
| **P3 - Medium** | < 4 hours | Slack + ticket |
| **P4 - Low** | Next business day | Ticket only |

### Runbooks

Every paging alert links to a runbook: quick assessment steps, common causes with fixes, escalation path. Without runbooks, on-call engineers waste time re-discovering known solutions.

---

## Incident Response

### On-Call Practices

Healthy on-call: fair rotation, compensated, max one page per shift on average, handoff with context, authority to make operational decisions (rollback, scale up, circuit breaker).

### Incident Commander Role

For P1/P2: designate an IC who coordinates but does NOT debug. IC responsibilities: declare incident, set severity, assign roles, make decisions, track timeline, communicate updates every 15-30 minutes, schedule postmortem.

### Communication

**Internal:** Dedicated Slack channel per incident, status updates every 15-30 minutes even with no news. **External:** Acknowledge on status page within 5 minutes, update regularly, be honest about impact, confirm resolution.

### Blameless Postmortems

Focus on systemic causes, not individuals. "Human error" is never a root cause -- the system allowed the error. Ask "what made this possible?" not "who did this?"

**Template:** Summary, impact (users affected, duration, revenue), timeline, root cause, contributing factors, what went well, what could improve, action items with owners and due dates.

### Follow-Up Tracking

Track postmortem actions alongside regular work. Assign owners and due dates. Review in weekly meetings. Escalate overdue items. Measure: % completed within 30 days.

---

## Dashboards

### Golden Signals Dashboard

Every service should display: Latency (p50/p95/p99), Traffic (RPS), Errors (rate and count), Saturation (CPU, memory, connection pool), plus recent deployments for correlation.

### Service Health Dashboard

Platform overview: all services listed with status, SLO, and error budget remaining. Active incidents and deploy count.

### Business Metrics

Orders per minute (vs last week), checkout conversion, payment success rate, search CTR, API usage by tier. Observability is not just for engineers.

### Avoiding Dashboard Sprawl

Hierarchy (platform -> service dashboards), ownership (unowned = deleted), standardized templates, quarterly usage review, link from alerts to dashboards, deployment annotations on graphs.

---

## Interview Questions

**Q: You join a team with no observability. How do you build it from scratch?**

A: Phased approach. Week 1-2: structured JSON logging with correlation IDs, basic RED metrics with Prometheus/Grafana, health check endpoints. Week 3-4: define SLIs/SLOs with product team, burn-rate alerts, golden signals dashboards. Month 2: distributed tracing with OTel auto-instrumentation, incident response process with postmortem template. Month 3+: custom business metrics, anomaly detection, profiling, RUM.

**Q: Your SLO is 99.95% availability but you are at 99.7%. What do you do?**

A: Triage errors by endpoint/region/root cause. Fix top contributors (rollback, scale, circuit breaker). If error budget is exhausted, invoke error budget policy -- freeze features, prioritize reliability. Review 30 days of incidents for patterns. Evaluate if SLO is appropriate -- either invest in required reliability or adjust SLO and work toward improvement.

**Q: How do you handle alert fatigue (50+ pages per week)?**

A: Audit all alerts from the last month -- was each actionable? Delete or suppress non-actionable ones. Consolidate per-instance alerts into aggregates. Switch to SLO-based burn rate alerting. Fix underlying instability rather than tuning thresholds. Target: 0-2 actionable pages per shift.

**Q: How would you implement distributed tracing across 50 microservices?**

A: Incremental rollout. Deploy OTel Collector as DaemonSet. Start with auto-instrumentation (covers 80% of useful data). Instrument the top 3-5 user-facing request flows with manual spans. Implement tail-based sampling (100% errors, 100% slow, 5% baseline). Verify W3C traceparent propagation across all inter-service communication. Gradually expand manual spans as teams adopt.

**Q: Walk me through running a major incident as IC.**

A: (1) Declare incident, create channel, post initial summary with impact. (2) Page relevant team leads, assign who debugs vs who communicates. (3) Parallel investigation workstreams. (4) Status page update within 5 minutes, internal updates every 15 minutes. (5) If root cause not found in 15 minutes, mitigate first (rollback, scale, fallback). (6) On resolution, confirm with monitoring, update status page. (7) Schedule postmortem within 48 hours.

---

## Key Takeaways

1. **Observability is not monitoring**: Monitoring tells you when something breaks. Observability lets you ask arbitrary questions without new deploys.
2. **Structure everything**: Structured logs, standardized metrics, correlated traces.
3. **SLOs are the foundation**: Without SLOs, every alert is an opinion. With SLOs, every alert is grounded in user impact.
4. **Burn rate alerting reduces noise dramatically** compared to static threshold alerts.
5. **Blameless postmortems create learning organizations**: Improve the system, not punish individuals.
6. **Invest in tracing early**: Distributed tracing is the fastest path to understanding cross-service behavior.
7. **The investigation loop: metrics alert, traces locate, logs explain.**
