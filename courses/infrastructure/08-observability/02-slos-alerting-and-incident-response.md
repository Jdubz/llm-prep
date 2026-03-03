# Module 08: SLOs, Alerting, and Incident Response

## SLIs, SLOs, and SLAs

### Definitions

- **SLI (Service Level Indicator)**: Quantitative measure of service behavior. "What are we measuring?"
- **SLO (Service Level Objective)**: Target value for an SLI. "What is acceptable?"
- **SLA (Service Level Agreement)**: Contractual commitment with consequences. "What did we promise?"

SLO should be stricter than SLA -- missing your SLO gives you time to fix before breaching your SLA.

### Defining Good SLIs

SLIs should measure what users experience, not internal state. "CPU utilization" is not an SLI. "Successful request rate" is. Measure at the edge (load balancer, client-side) when possible.

| Service Type | SLI | How to Measure |
|-------------|-----|---------------|
| HTTP API | Availability (% successful) | (non-5xx responses) / (total responses) |
| HTTP API | Latency (% within threshold) | (requests < 500ms) / (total requests) |
| Data pipeline | Freshness (data age) | current_time - last_successful_run |
| Data pipeline | Correctness | Validation checks on output |
| Storage | Durability (% retained) | 1 - (data_loss_events / total_objects) |

### SLI/SLO Template

**Availability SLI:** (non-5xx responses) / (total responses). **SLO:** 99.95% over 30-day rolling window. Error budget: 21.6 min/month.

**Latency SLI:** (requests < 500ms) / (total requests). **SLO:** 99% under 500ms over 30-day rolling window.

### Error Budgets

Error budget = inverse of SLO. At 99.9% availability: 43.2 min/month allowed downtime. At 99.95%: 21.6 min. At 99.99%: 4.32 min.

**Error budget policy:**
- Budget >50% remaining: Deploy freely, run experiments, take risks
- Budget 25-50% remaining: Increased caution, review risky changes
- Budget <25% remaining: Slow down deploys, focus on reliability
- Budget exhausted: Freeze feature releases, all effort on reliability

### Burn Rate Alerting

Traditional alerting ("alert if error rate > 1% for 5 minutes") is either too sensitive or too slow. Alert based on the rate at which you consume your error budget instead.

```
Burn rate = (actual error rate) / (error rate allowed by SLO)
SLO 99.9%, actual error rate 1.0% -> burn rate = 10x
```

**Multi-window burn rate alerts (Google SRE):**

| Severity | Burn Rate | Long Window | Short Window | Budget Consumed |
|----------|-----------|-------------|--------------|-----------------|
| Page (critical) | 14.4x | 1 hour | 5 minutes | 2% in 1 hour |
| Page (high) | 6x | 6 hours | 30 minutes | 5% in 6 hours |
| Ticket (medium) | 3x | 1 day | 2 hours | 10% in 1 day |

Both windows must fire simultaneously -- the long window catches sustained issues, the short window confirms it is still happening.

---

## Alerting Strategies

### Alerting Rules Template

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

### Reducing Alert Fatigue

Alert fatigue is the single biggest threat to on-call effectiveness. When engineers are drowning in noise, they ignore real alerts.

**Symptoms:** Acknowledging without investigating, permanent suppression, "ignore these alerts" tribal knowledge, pages during maintenance windows, alert-to-incident ratio worse than 10:1.

**Solutions:** Delete alerts with no action in 30 days, raise thresholds, use burn rate instead of static thresholds, route by severity (not everything is a page), maintenance windows, aggregate related alerts.

### Actionable Alerts

Every alert answers: (1) What is happening? (2) Why does it matter? (3) What should I do?

**Bad alert:**
```
FIRING: HighCPU
  cpu_usage > 80% for 5 minutes on host-42
```

**Good alert:**
```
FIRING: Order Processing Degraded
  Summary: Order service p99 latency exceeded 2s for 15 minutes
  Impact: Slow checkout. Error rate 3.2% (SLO: 0.1%). Burn rate: 32x.
  Runbook: https://wiki.internal/runbooks/order-service-latency
  Dashboard: https://grafana.internal/d/order-service
```

### Severity Levels and Escalation

| Severity | Response Time | Notification |
|----------|--------------|-------------|
| **P1 - Critical** | Immediate | Page on-call engineer |
| **P2 - High** | < 30 min | Page during business hours, Slack otherwise |
| **P3 - Medium** | < 4 hours | Slack channel, create ticket |
| **P4 - Low** | Next business day | Ticket only |

### Runbooks

Every paging alert should link to a runbook: quick assessment steps (check dashboard, recent deploys, dependent services), common causes with fixes, escalation path. Without runbooks, on-call engineers waste time rediscovering known solutions.

---

## Incident Response

### On-Call Practices

**Healthy on-call:** Fair rotation, compensated (time off or pay), max one page per shift on average, handoff with context, authority to make operational decisions (rollback, scale up, circuit breaker).

### Incident Commander Role

For P1/P2 incidents, designate an IC who coordinates but does NOT debug. IC responsibilities: declare incident, set severity, create communication channel, assign roles (who debugs, who communicates), make decisions (rollback or not, involve other teams), track timeline, communicate updates every 15-30 minutes, schedule postmortem.

### Communication

**Internal:** Dedicated Slack channel per incident (`#inc-2024-01-15-order-outage`). Status updates every 15-30 minutes, even with no news. Pin current status, impact, and assignments.

**External (status page):** Acknowledge within 5 minutes. Update regularly. Be honest about impact. Confirm resolution with brief explanation.

### Incident Response Checklist

**Detection (0-5 min):** Acknowledge alert. Verify it is real via dashboard. Assess severity (P1/P2/P3). For P1/P2: create incident channel.

**Response (5-30 min):** Assign IC for P1/P2. Post initial status. Update status page. Check: recent deploy? dependent services? infra issues?

**Mitigation:** Bad deploy: rollback. Traffic spike: scale up, rate limit. Dependency failure: circuit breaker. Update status page.

**Resolution:** Confirm metrics normal. Update status page: resolved. Schedule postmortem within 48 hours.

### Blameless Postmortems

Focus on systemic causes, not individuals. "Human error" is never a root cause -- the system allowed the error. Ask "what made this possible?" not "who did this?"

**Template:** Summary, impact (users affected, duration, revenue), timeline, root cause, contributing factors, what went well, what could improve, action items with owners and due dates.

### Postmortem Template

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

### Follow-Up Tracking

Track actions alongside regular work (Jira, Linear, GitHub Issues). Assign owners and due dates. Review in weekly meetings. Escalate overdue items. Measure: % completed within 30 days.

---

## Dashboards

### Golden Signals Dashboard

Every service should display: Latency (p50/p95/p99), Traffic (RPS), Errors (rate, count), Saturation (CPU, memory, connection pool). Include recent deployments for correlation.

### Service Health Dashboard

Platform overview for the team: all services with status, SLO, error budget remaining, active incidents, and deploy count for the day.

### Business Metrics Dashboard

Orders per minute (vs same time last week), checkout conversion rate, payment success rate by provider, search CTR, API usage by tier. Observability is not just for engineers.

### Avoiding Dashboard Sprawl

Hierarchy (top-level platform -> per-service dashboards), ownership (unowned dashboards = deleted), standardized templates (golden signals), quarterly usage review, link from alerts to relevant dashboard sections, deployment and incident annotations on graphs.

---

## Investigation Flow

```
ALERT (metric) -> DASHBOARD (golden signals) -> CORRELATE (deploy? dependency? spike?)
  -> TRACE (find failing request) -> INSPECT (which span?) -> LOGS (filter by trace_id)
  -> ROOT CAUSE -> MITIGATE -> VERIFY (metrics normal, burn rate drops)
```

**Key principle**: Metrics detect, traces locate, logs explain.

---

## Interview Questions

**Q: You join a team with no observability. How do you build it from scratch?**

A: Phased approach. Week 1-2: structured JSON logging with correlation IDs, basic RED metrics (rate/errors/duration) with Prometheus + Grafana, /healthz endpoints. Week 3-4: define SLIs/SLOs with product team, burn-rate alerts for SLOs, golden signals dashboards. Month 2: distributed tracing with OTel auto-instrumentation on the critical path, incident response process with postmortem template. Month 3+: custom business metrics, anomaly detection, profiling, RUM.

**Q: How do you decide between logging, metrics, and tracing for a problem?**

A: They serve different purposes. Need to debug a specific request? Trace. Need current service health? Metrics. Need exact failure details? Logs. Need alerting? Metrics (burn rates, SLO-based). The investigation flow is: metrics alert you, traces show you where, logs tell you why.

**Q: Your SLO is 99.95% but you are at 99.7%. What do you do?**

A: Triage errors by endpoint/region/cause. Fix top contributors (rollback, scale, circuit breaker). If budget exhausted, invoke error budget policy -- freeze features, prioritize reliability. Review 30 days of incidents for patterns. Evaluate if SLO is appropriate -- either invest in reliability or adjust SLO.

**Q: How do you handle alert fatigue (50+ pages/week)?**

A: Audit last month of alerts -- was each actionable? Delete/suppress non-actionable. Consolidate per-instance into aggregate alerts. Switch to SLO-based burn rate alerting. Fix underlying instability. Target: 0-2 actionable pages per shift.

**Q: Walk me through running a major incident as IC.**

A: (1) Declare incident, create channel, post summary with impact. (2) Page relevant team leads, assign who debugs vs who communicates. (3) Parallel investigation workstreams. (4) Status page update within 5 min, internal updates every 15 min. (5) If no root cause in 15 min, mitigate first (rollback, scale, fallback). (6) Confirm resolution with monitoring. (7) Schedule postmortem within 48 hours.

### Related Reading

- [Module 08: Logging, Metrics, and Tracing](01-logging-metrics-and-tracing.md) -- the three pillars (logs, metrics, traces) and PromQL queries that SLO-based alerting rules are built on
- [Module 08: Advanced Observability](03-advanced-observability.md) -- the OTel Collector processes and routes the telemetry data that SLO dashboards consume; cost management for observability data at scale
- [Module 01: Advanced System Design](../01-system-design-framework/02-advanced-system-design.md) -- SLOs are a staff-level design expectation; the system design framework includes defining SLIs as part of requirements gathering
- [Module 05: Circuit Breakers and Retry Strategies](../05-load-balancing/02-circuit-breakers-and-retry-strategies.md) -- circuit breakers and error budgets work together; when SLO burn rate is high, circuit breakers should be more aggressive
- [Module 07: Pipeline Design and Deployment Strategies](../07-cicd/01-pipeline-design-and-deployment-strategies.md) -- canary deployments need SLO-based metrics to decide when to promote or rollback; burn rate alerts drive automated deployment gates
- [Module 07: Feature Flags and Migrations](../07-cicd/02-feature-flags-and-migrations.md) -- error budget policy (freeze features when budget is exhausted) directly affects feature flag rollout decisions

### Key Takeaways

1. **SLOs are the foundation of reliable operations**: Without SLOs, every alert is an opinion. With SLOs, every alert is grounded in user impact.
2. **Burn rate alerting reduces noise dramatically** compared to static threshold alerts.
3. **Blameless postmortems create learning organizations**: Improve the system, not punish individuals.
4. **Dashboards should tell a story**: Golden signals per service, platform health overview, business metrics -- each for a different audience.
5. **Observability is not monitoring**: Monitoring tells you when something breaks. Observability lets you ask arbitrary questions without deploying new code.
