# Module 01 Deep Dive: Staff-Level System Design

## Overview

At the staff+ level, system design interviews shift. You are no longer expected to just design a system that works. You are expected to design a system that an organization can build, operate, evolve, and afford. The scope expands from "which database" to "which database, who operates it, how do we migrate to it, and what does it cost us annually."

This deep dive covers the dimensions that separate senior from staff-level system design.

---

## Staff-Level Scope Expansion

### What Changes at Staff+

| Dimension | Senior | Staff+ |
|-----------|--------|--------|
| **Scope** | Single system or service | System of systems, cross-team boundaries |
| **Time Horizon** | Current requirements | 2-3 year roadmap, migration paths |
| **Team** | Assumed ideal team | Real team with skill gaps, on-call burden |
| **Trade-offs** | Technical only | Technical + organizational + financial |
| **Failure** | Component failure | Correlated failures, cascading failures, blast radius |
| **Communication** | With interviewer | Framed as if presenting to VP of Engineering |

### Organizational Considerations

At staff level, you should address:

- **Team topology:** Which team owns which component? How do teams interact? Are there shared services?
- **Operational burden:** Does this design require 24/7 on-call? How complex is the runbook? Can a junior engineer debug issues?
- **Build vs buy:** Should we build this or use a managed service? What is the total cost of ownership, including engineering time for maintenance?
- **Incremental delivery:** Can we ship value in phases, or does it require a big-bang migration?
- **Conway's Law awareness:** The system architecture will mirror the org structure. Design with that in mind, or explicitly call out where you need the org to change.

### Migration Planning

No staff-level design exists in a vacuum. There is always a legacy system. You need a migration strategy.

**Common migration patterns:**

1. **Strangler Fig:** Route traffic incrementally from old system to new system. Start with low-risk endpoints. Roll back if issues arise. This is the default safe choice.

2. **Parallel Run:** Run both old and new systems simultaneously. Compare outputs. Build confidence before switching. More expensive (double the infrastructure) but lower risk.

3. **Big Bang:** Switch everything at once. Only viable for systems with natural downtime windows (batch systems, internal tools) or when the old system is literally on fire.

4. **Feature Flag Migration:** New code paths behind feature flags. Gradually increase traffic percentage. Roll back instantly by flipping the flag.

**What to address in migration planning:**
- Data migration strategy (backfill, dual-write, CDC)
- Rollback plan (how do we undo this if it fails?)
- Success criteria (how do we know the migration is complete?)
- Timeline (weeks? months? quarters?)
- Risk mitigation (canary deploys, shadow traffic, circuit breakers)

---

## API-First Design Approach

### Why API-First Matters at Scale

At the staff level, API design is not just "what endpoints do we need." It is the contract that defines team boundaries, determines backward compatibility constraints, and shapes the evolution path of your system.

### API Design Principles for Scale

**Backward Compatibility:**
Every API change must be backward compatible. This means:
- New fields can be added to responses (clients ignore unknown fields)
- New optional parameters can be added to requests
- Existing fields cannot be removed or have their type changed
- Existing required parameters cannot become more restrictive

When you must make a breaking change, version the API. But versioning has costs -- every version is a maintenance burden. Prefer evolution over versioning.

**Pagination:**
- Offset-based (`?page=3&limit=20`): Simple but breaks with concurrent writes (items shift between pages). Fine for admin interfaces.
- Cursor-based (`?cursor=abc123&limit=20`): Stable under concurrent writes. Better performance (no `OFFSET` scan). Use this for public APIs and data that changes frequently.

**Idempotency:**
Any non-GET request should be safe to retry. This is critical for distributed systems where network failures cause ambiguous results (did the write succeed or not?).

```
POST /api/v1/payments
Headers:
  Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

Server behavior:
  1. Check if this idempotency key has been seen before
  2. If yes, return the cached response (do not re-execute)
  3. If no, execute the request and cache the response keyed by idempotency key
```

**Error Contracts:**
Standardize error responses across all services:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You have exceeded the rate limit of 100 requests per minute",
    "details": {
      "retry_after_seconds": 32
    }
  }
}
```

Machine-readable error codes (not HTTP status codes alone) allow clients to handle errors programmatically.

### gRPC vs REST vs GraphQL at Scale

| Factor | REST | gRPC | GraphQL |
|--------|------|------|---------|
| **Best for** | Public APIs, web clients | Service-to-service, performance-critical | Client-driven queries, mobile apps |
| **Serialization** | JSON (human-readable, verbose) | Protocol Buffers (binary, compact) | JSON |
| **Schema** | OpenAPI (optional) | .proto files (required) | Schema (required) |
| **Streaming** | SSE, WebSocket (separate) | Native bidirectional streaming | Subscriptions |
| **Tooling** | Universal | Strong but language-dependent | Requires gateway, resolver layer |
| **Overhead** | Higher (text-based) | Lower (~10x smaller payloads) | Medium |

**Staff-level take:** Use gRPC for internal service-to-service communication where you control both sides. Use REST for public APIs (universal client support). GraphQL only if you have many different client types with different data needs and a team willing to invest in the resolver infrastructure. Do not use GraphQL just because it is trendy -- it adds operational complexity (N+1 query problem, query cost analysis, schema stitching).

---

## Capacity Planning in Practice

### Beyond Napkin Math

Back-of-envelope gets you to the right order of magnitude. Capacity planning in practice is an ongoing discipline.

**The Capacity Planning Loop:**

```
1. Measure current usage (CPU, memory, disk, network, QPS, latency)
2. Model growth (historical trend + business projections)
3. Identify bottlenecks (which resource hits limits first?)
4. Plan headroom (target 60-70% utilization, not 90%)
5. Provision ahead (lead time for hardware, contracts, migrations)
6. Re-measure and adjust (quarterly)
```

**Why 60-70% utilization, not higher?**
- Leaves room for traffic spikes (2-3x normal)
- Prevents performance degradation (most systems degrade non-linearly above 70%)
- Gives you time to react before hitting limits
- Allows for graceful handling of partial infrastructure failures

### Bottleneck Analysis

Systems rarely scale uniformly. One component will hit its limit first.

**Common bottlenecks by system type:**

| System Type | Typical First Bottleneck | Why |
|-------------|-------------------------|-----|
| Web application | Database connections | Connection pool exhaustion under load |
| API gateway | CPU (TLS termination) | Encryption is CPU-intensive |
| Analytics pipeline | Disk I/O | Write-heavy workloads saturate disk |
| Real-time system | Network bandwidth | High message throughput saturates NIC |
| ML inference | GPU memory | Model size exceeds GPU RAM |

**How to identify the bottleneck:**
- Load test with realistic traffic patterns (not just uniform reads)
- Monitor all resources simultaneously (CPU, memory, disk I/O, network, connection count)
- Increase traffic until something breaks
- The thing that breaks first is your bottleneck

---

## Cost Estimation

### Why Cost Matters in Design

At staff level, you should be able to ballpark the infrastructure cost of your design. This is not about being precise -- it is about knowing whether your design costs $1K/month or $100K/month.

### Cloud Cost Mental Model

**Compute (EC2/GCE/VMs):**
- General purpose (m-series): ~$0.05/hour per vCPU
- Compute optimized (c-series): ~$0.04/hour per vCPU
- Memory optimized (r-series): ~$0.06/hour per vCPU
- Reserved instances: 30-60% discount for 1-3 year commitment
- Spot/preemptible: 60-90% discount but can be reclaimed

**Storage:**
- S3/GCS: ~$0.023/GB/month (standard), ~$0.004/GB/month (infrequent access)
- EBS gp3: ~$0.08/GB/month
- EBS io2: ~$0.125/GB/month + $0.065/IOPS/month

**Database (managed):**
- RDS PostgreSQL (db.r6g.xlarge, 4 vCPU, 32 GB): ~$0.48/hour = ~$350/month
- DynamoDB: $1.25 per million write request units, $0.25 per million read request units (on-demand)
- ElastiCache Redis (r6g.large, 2 vCPU, 13 GB): ~$0.25/hour = ~$180/month

**Data transfer:**
- Within same region: free (mostly)
- Cross-region: $0.01-0.02/GB
- To internet: $0.09/GB (first 10 TB)

**Quick cost estimation for our URL shortener:**
```
3 app servers (c6g.large):     3 x $60/month  = $180/month
1 Redis (r6g.large, 13GB):     $180/month
1 RDS PostgreSQL (r6g.xlarge): $350/month
1 RDS read replica:            $350/month
Load balancer:                 $25/month + traffic
Data transfer:                 ~$50/month
Total: ~$1,135/month before reserved pricing
```

That is remarkably affordable for a system serving 100M DAU. This is a useful data point -- it tells you and the interviewer that the design is reasonable.

---

## Multi-Region Architecture

### When You Need Multi-Region

- **Latency requirements:** Users in Asia cannot tolerate 200ms+ round trips to US-East.
- **Compliance requirements:** Data residency laws (GDPR, data sovereignty).
- **Availability requirements:** Survive a full region outage (99.99%+ availability).
- **Business continuity:** Disaster recovery with near-zero RPO/RTO.

### Multi-Region Patterns

**Active-Passive:**
- One region handles all traffic. Second region is a hot standby.
- Failover is manual or semi-automated.
- Data is replicated asynchronously to the passive region.
- RPO: seconds to minutes (replication lag). RTO: minutes to hours (failover time).
- Cheapest multi-region option. Good enough for most systems.

**Active-Active (Read):**
- Both regions serve reads from local replicas.
- All writes go to a single primary region.
- Reads are fast everywhere. Writes from the non-primary region have cross-region latency.
- Good for read-heavy systems (our URL shortener fits here perfectly).

**Active-Active (Full):**
- Both regions handle both reads and writes.
- Requires conflict resolution strategy (last-writer-wins, CRDTs, application-level resolution).
- Most complex. Most expensive. Only needed when you genuinely cannot tolerate write latency from remote regions.

**Routing strategies:**
- DNS-based (Route 53 geo-routing): Simple, but DNS TTL means slow failover.
- Anycast: Fast failover, but limited to L3/L4 routing.
- Global load balancer (Cloudflare, AWS Global Accelerator): Best of both worlds, but adds cost.

### Data Consistency Across Regions

This is the hard part. You cannot have strong consistency and low latency across regions (speed of light is the fundamental constraint -- US-East to EU-West is ~80ms round trip).

**Options:**
1. **Single-region writes, async replication:** Simple. Writes are consistent. Reads may be stale by replication lag (typically <1 second). Best for most systems.
2. **Synchronous cross-region replication:** Every write waits for confirmation from both regions. Strong consistency. But writes take >160ms minimum (round trip). Only viable if you have very few writes.
3. **Conflict-free replicated data types (CRDTs):** Eventually consistent but mathematically guaranteed to converge. Good for counters, sets, registers. Bad for complex business logic.
4. **Application-level conflict resolution:** Write to both regions, resolve conflicts in application code. Flexible but complex. Used by systems like DynamoDB Global Tables (last-writer-wins).

---

## Disaster Recovery Planning

### RPO and RTO

- **RPO (Recovery Point Objective):** How much data can you afford to lose? Measured in time. RPO of 1 hour means you can lose up to 1 hour of data.
- **RTO (Recovery Time Objective):** How long can you be down? Measured in time. RTO of 4 hours means you must be back up within 4 hours.

**The cost relationship:**

```
Lower RPO = More expensive (more frequent backups, synchronous replication)
Lower RTO = More expensive (hot standby, automated failover, practice drills)
```

### DR Tiers

| Tier | Strategy | RPO | RTO | Relative Cost |
|------|----------|-----|-----|---------------|
| **Tier 4** | Backup and restore | Hours | Days | $ |
| **Tier 3** | Pilot light (minimal standby) | Minutes | Hours | $$ |
| **Tier 2** | Warm standby (scaled-down copy) | Seconds | Minutes | $$$ |
| **Tier 1** | Active-active multi-region | Near-zero | Near-zero | $$$$ |

**Staff-level insight:** Most systems do not need Tier 1. But most engineering teams dramatically underinvest in DR testing. A DR plan that has never been tested is not a plan -- it is a hope. Advocate for quarterly DR drills.

### What a DR Plan Must Include

1. **Failure scenarios:** What specific failures are we planning for? (Region outage, database corruption, DNS failure, key person unavailable)
2. **Detection:** How do we know a disaster has occurred? (Monitoring, alerting, health checks)
3. **Decision process:** Who decides to failover? How do they decide? (Runbook, escalation path)
4. **Failover procedure:** Step-by-step actions. Automated where possible.
5. **Validation:** How do we know the failover worked? (Smoke tests, synthetic monitoring)
6. **Failback procedure:** How do we return to normal operations? (Often harder than failover)
7. **Post-mortem:** What happened, why, and how do we prevent it?

---

## SLA / SLO / SLI

### Definitions That Actually Matter

- **SLI (Service Level Indicator):** A measurement. A specific metric. "The proportion of requests that complete in under 200ms."
- **SLO (Service Level Objective):** A target. An internal goal for an SLI. "99.9% of requests should complete in under 200ms, measured over a rolling 30-day window."
- **SLA (Service Level Agreement):** A contract. A legal commitment to customers with consequences (usually financial credits) for violation. "We guarantee 99.95% uptime. If we miss this, affected customers receive 10% service credit."

**The relationship:**

```
SLIs are what you measure
SLOs are what you aim for (set tighter than SLAs)
SLAs are what you promise (set looser than SLOs, with a buffer)
```

### How to Set SLOs

**Step 1: Identify your SLIs.**

Common SLIs:
- **Availability:** Successful requests / Total requests
- **Latency:** p50, p95, p99 response time
- **Throughput:** Requests per second
- **Error rate:** Error responses / Total responses
- **Freshness:** Age of data served (for caches, replicas)

**Step 2: Measure current performance.**

You cannot set a meaningful SLO without baseline data. Measure for at least 2-4 weeks before setting targets.

**Step 3: Set SLOs based on user experience, not infrastructure capability.**

Bad: "Our database can handle 10K QPS, so our SLO is 10K QPS."
Good: "Users start noticing degradation at p99 > 500ms. Our SLO is p99 < 300ms (with buffer)."

**Step 4: Define error budgets.**

If your SLO is 99.9% availability, your error budget is 0.1% -- roughly 43 minutes of downtime per month. When the budget is nearly exhausted, freeze deployments and focus on reliability. When budget is healthy, ship features aggressively.

```
Monthly error budget at 99.9%:  43 minutes
Monthly error budget at 99.95%: 22 minutes
Monthly error budget at 99.99%: 4.3 minutes
```

**Step 5: Review and adjust quarterly.**

SLOs are not set-and-forget. As your system matures, tighten them. As user expectations change, adjust the SLIs you measure.

### Common Mistakes with SLOs

1. **Setting SLOs too tight:** 99.99% sounds great until your team spends all their time on reliability and ships zero features.
2. **Not having error budgets:** SLOs without error budgets are just aspirational numbers. The error budget is what makes SLOs actionable.
3. **Measuring the wrong thing:** Availability measured at the load balancer misses application-level errors. Measure from the user's perspective.
4. **Too many SLOs:** Having 20 SLOs means none of them matter. Pick 3-5 that actually represent user experience.
5. **SLOs that nobody looks at:** If the SLO dashboard is not in your team's daily workflow, the SLOs are not real.

---

## Putting It All Together: Staff-Level Design Example

When designing at staff level, your system design should include sections that a senior candidate would not cover:

1. **System design** (same as senior, but broader scope)
2. **Organizational design** -- which teams own what, team interactions
3. **Migration plan** -- how to get from here to there
4. **Cost estimate** -- ballpark monthly/annual infrastructure cost
5. **SLOs** -- what you measure, what you target
6. **DR plan** -- what happens when things fail at scale
7. **Evolution path** -- how this design adapts to 10x, 100x growth

You will not cover all of these in depth in a 45-minute interview. But signaling that you *think about* these dimensions is what distinguishes a staff-level answer.

---

## Key Takeaways

1. Staff-level design is about systems *and* organizations. The best architecture is worthless if no team can build and operate it.
2. Migration is the hard part. Greenfield designs are easy. Getting from point A to point B without downtime is the real challenge.
3. Cost awareness is not optional. You should be able to estimate whether your design costs $1K or $100K per month.
4. Multi-region is a spectrum, not a binary. Start with active-passive unless you have concrete latency or compliance requirements for active-active.
5. SLOs are the bridge between engineering and business. They make reliability decisions objective and measurable.
6. DR plans are only as good as your last drill. Untested plans fail when you need them most.
