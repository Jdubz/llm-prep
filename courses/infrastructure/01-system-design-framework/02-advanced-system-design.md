# Module 01: Advanced System Design

## Example Walkthrough: Design a URL Shortener

Let us walk through the entire framework applied to a concrete problem.

### Step 1: Requirements (5-7 minutes)

**Functional Requirements:**
- Given a long URL, generate a short URL
- Given a short URL, redirect to the original long URL
- Users can optionally set custom short codes
- URLs can have expiration dates
- Basic analytics (click count per URL)

**Non-Functional Requirements:**
- Very low latency for redirects (p99 < 100ms) -- this is on the critical path of user navigation
- High availability (99.99%) -- downtime means broken links everywhere
- Eventual consistency is fine -- a 1-second delay before a new URL works is acceptable
- Read-heavy (50:1 read to write ratio estimated)
- Scale: 100M DAU

**Scope exclusions (stated explicitly):**
- No link preview/unfurling
- No spam/abuse detection (mention it exists, do not design it)
- No user management system (assume it exists)

### Step 2: Estimation (3-5 minutes)

```
Write QPS: ~115/sec (peak ~350/sec)
Read QPS:  ~5,800/sec (peak ~17,400/sec)
Storage:   ~1 TB/year, ~5 TB over 5 years
Cache:     ~6 GB for hot URLs (fits one Redis instance)
Bandwidth: ~1.7 MB/s outgoing (negligible)
Servers:   2-3 app servers (plus redundancy)
```

**Key insight from estimation:** This is comfortably single-database territory for storage. The challenge is read latency at scale, solved by aggressive caching.

### Step 3: High-Level Design (10-15 minutes)

**API:**

```
POST /api/v1/urls       -> Create short URL
GET  /{short_code}       -> Redirect (301/302)
GET  /api/v1/urls/{short_code}/stats -> Get analytics
DELETE /api/v1/urls/{short_code}     -> Delete URL
```

**Data Model:**

```sql
CREATE TABLE urls (
    short_code  VARCHAR(7) PRIMARY KEY,
    long_url    TEXT NOT NULL,
    user_id     BIGINT,
    created_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP,
    is_custom   BOOLEAN DEFAULT FALSE
);
```

**Architecture:**

```
                         ┌──────────────┐
                         │     CDN      │ (edge cache for popular redirects)
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │ Load Balancer│
                         └──────┬───────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
              ┌─────▼──┐ ┌─────▼──┐ ┌─────▼──┐
              │ App 1  │ │ App 2  │ │ App 3  │
              └───┬────┘ └───┬────┘ └───┬────┘
                  │          │          │
            ┌─────▼──────────▼──────────▼─────┐
            │          Redis Cache             │
            └─────────────┬───────────────────┘
                          │ (cache miss)
                    ┌─────▼─────┐
                    │ PostgreSQL │
                    │  Primary   │──── Read Replica
                    └────────────┘
```

### Step 4: Deep Dive (15-20 minutes)

**Deep Dive 1: Short Code Generation**

Options:
1. **Base62 encoding of auto-increment ID:** Simple, guaranteed unique. But predictable (users can enumerate URLs). Sequential IDs leak information about total URL count.
2. **Random base62 string:** Not predictable. But requires uniqueness check on every write (collision risk).
3. **Pre-generated key service:** Generate keys in advance, hand them out. No collision risk, no enumeration. But adds a component.
4. **MD5/SHA256 hash of long URL + timestamp, take first 7 chars:** Deterministic. But collisions possible; same long URL at different times should produce different short codes.

**Decision:** Pre-generated key service (option 3).

- A separate service generates batches of unique 7-character base62 keys and stores them in a "key pool" table.
- When an app server needs a key, it grabs a batch (say, 1000 keys) and holds them in memory.
- This eliminates collision checking on the write path and decouples key generation from URL creation.
- If an app server crashes, we lose at most 1000 unused keys -- acceptable waste.

```
7-character base62 = 62^7 = ~3.5 trillion possible keys
At 10M new URLs/day, this lasts ~950 years. No exhaustion concern.
```

**Deep Dive 2: Caching Strategy**

Cache-aside pattern with Redis:

```
Read path:
1. Check Redis for short_code -> long_url mapping
2. Cache hit -> return long_url (redirect)
3. Cache miss -> query PostgreSQL -> write to Redis with TTL -> return long_url

Write path:
1. Write to PostgreSQL
2. Write to Redis (write-through for immediate availability)
```

Cache invalidation:
- TTL of 24 hours for standard URLs
- Explicit invalidation on DELETE
- No invalidation needed on click count updates (analytics are eventually consistent)

Hot key problem:
- A viral URL could get millions of hits. Single Redis key can handle ~100K ops/sec, so this is only a problem at extreme viral scale.
- Mitigation: replicate hot keys across multiple Redis nodes with key-based routing, or use local in-memory cache (Caffeine/Guava) with short TTL (30 seconds) in front of Redis.

**Deep Dive 3: 301 vs 302 Redirect**

- **301 (Moved Permanently):** Browser caches the redirect. Subsequent visits bypass our server entirely. Better for users (faster). Terrible for analytics (we never see repeat visits).
- **302 (Found / Temporary):** Browser does not cache. Every visit hits our server. Worse latency for users. But we can count every click.

**Decision:** Use 302 by default (analytics matter). Offer 301 as an option for users who do not need analytics and want maximum performance.

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

## Putting It All Together: Staff-Level Design

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

## Interview Questions

### Conceptual Questions

1. **You are designing a system and the interviewer says "assume infinite resources." What do you do differently?**
   - This is a trap. Even with infinite resources, you still face the constraints of distributed computing: network latency, consistency guarantees, data locality. The answer is not "put everything in one giant server." It is to focus on correctness, consistency models, and data flow rather than scaling mechanics.

2. **When would you choose to start with a monolith vs microservices for a system design?**
   - Almost always start monolithic in an interview context unless the problem explicitly involves multiple independent teams or vastly different scaling requirements. State this: "I'll design as a monolith with clear module boundaries. Here's where I'd split if team or scale requirements demanded it."

3. **How do you decide between synchronous and asynchronous communication?**
   - Synchronous when the caller needs the result to proceed (user-facing request-response). Asynchronous when the caller does not need an immediate result (sending notifications, updating analytics, indexing search). The boundary is: "Can the user's request complete without this work finishing?"

4. **Your estimation shows 50 QPS. Do you still design for scale?**
   - No. You design for correctness and simplicity, then identify the scaling bottlenecks. Mention where you would add caching, read replicas, or horizontal scaling "when the time comes." Over-engineering for scale you do not have is a cost (complexity, maintenance, slower iteration).

5. **What is the difference between horizontal and vertical scaling, and when do you prefer each?**
   - Vertical (bigger machine) is simpler, no distributed systems complexity, but has a ceiling. Horizontal (more machines) has no ceiling but introduces coordination overhead. Prefer vertical until you hit the machine limit or need redundancy. Then go horizontal with stateless services first (easiest to scale horizontally) and stateful services last (hardest).

### Scenario-Based Questions

6. **Design a rate limiter for an API. Walk through requirements, estimation, and design.**
   - Requirements: per-user rate limiting, configurable limits per endpoint, must not add more than 5ms latency, must work across multiple app servers.
   - Estimation: if 10K users, each with a 100 req/min limit, we need to track 10K counters with sub-millisecond lookups.
   - Design: Redis-backed sliding window counter. Key = `rate:{user_id}:{endpoint}:{minute}`. INCR + EXPIRE. Redis handles the distributed state. App servers are stateless rate-limit checkers.
   - Trade-off: sliding window is more accurate but more expensive than fixed window. Token bucket is more flexible but harder to implement correctly in distributed systems.

7. **You are midway through designing a social media feed and the interviewer asks "How do you handle a celebrity with 100M followers posting?" How do you pivot?**
   - This is a fan-out problem. Two approaches: fan-out on write (pre-compute feeds for all followers -- fast reads, expensive writes) vs fan-out on read (compute feed at read time -- cheap writes, expensive reads). For celebrities, use a hybrid: fan-out on write for normal users, fan-out on read for celebrity posts (merge at read time). This is literally what Twitter did.

8. **The interviewer pushes back on your database choice. How do you handle it?**
   - Do not get defensive. Say: "That's a fair point. Let me think about what changes if we use [their suggestion]." Walk through how the alternative affects your data model, query patterns, scaling story, and operational complexity. Either you will find the alternative is better (great -- show flexibility) or you will articulate concrete reasons why your original choice is preferable for *this specific use case*.

9. **How would you design a system that needs to handle a flash sale with 100x normal traffic for 10 minutes?**
   - Key insight: you do not want to provision 100x capacity permanently. Solutions: queue-based admission control (enqueue requests, process at sustainable rate), CDN/edge caching for read traffic, pre-warming caches, feature flags to disable non-essential features during the spike, auto-scaling with pre-provisioned warm pools (auto-scaling is too slow from cold).

10. **Design a URL shortener but the twist is it needs to work offline-first.**
    - This fundamentally changes the architecture. Offline-first means the client generates short codes locally, which means you need a conflict resolution strategy when syncing. Options: client-generated UUIDs (no conflicts but not short), CRDT-based merge, or pre-allocated key ranges per client. This is a great example of how a single requirement change can invalidate an entire design.

### Design Challenge

11. **You have 45 minutes. Design a collaborative document editor (like Google Docs). Apply the full framework.**
    - This is a staff-level question. The key challenges are: real-time collaboration (OT vs CRDT), cursor presence, conflict resolution, and operational history. A strong answer acknowledges the hard problem (real-time multi-user editing), picks a specific concurrency model, and explains the trade-offs.

12. **Design a distributed job scheduler (like cron, but for a fleet of servers). Focus on reliability guarantees.**
    - Key challenges: exactly-once execution, leader election for job assignment, handling worker failures mid-job, job priority and fairness, and idempotency. This tests your understanding of distributed consensus and failure handling.

---

## Key Takeaways

1. **The framework is a scaffold, not a script.** Adapt it to the interviewer and the problem. Some problems need more estimation; others need longer deep dives.

2. **Trade-offs are the entire point.** Every decision should come with "I chose X over Y because Z." If you cannot articulate the alternative, you do not understand the decision.

3. **Let the numbers drive the design.** Estimation is not a ritual -- it is the tool that prevents over-engineering and under-engineering.

4. **Communicate as a collaborator, not a presenter.** Check in. Ask questions. Respond to pushback gracefully.

5. **Failure is not optional.** Every system you design will fail. The question is: how does it fail, what is the blast radius, and how quickly can you recover?

6. **Start simple, add complexity.** The best designs are the simplest ones that meet all requirements. Complexity is a cost, not a feature.

7. **Staff-level design is about systems and organizations.** The best architecture is worthless if no team can build and operate it.

8. **Migration is the hard part.** Greenfield designs are easy. Getting from point A to point B without downtime is the real challenge.

9. **Cost awareness is not optional.** You should be able to estimate whether your design costs $1K or $100K per month.

10. **SLOs are the bridge between engineering and business.** They make reliability decisions objective and measurable.
