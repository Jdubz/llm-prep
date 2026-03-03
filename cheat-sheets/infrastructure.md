---
title: "Infrastructure & System Design Quick Reference"
---

# System Design Framework

1. **Requirements** — functional (APIs, features) + non-functional (latency, throughput, availability)
2. **Estimation** — QPS, storage, bandwidth, read/write ratio
3. **High-level design** — components, data flow, API contracts
4. **Deep dive** — bottlenecks, scaling, failure modes, tradeoffs

# Back-of-Envelope Estimation

```
QPS = DAU * actions/user/day / 86400
Peak QPS ~= 2-5x average QPS
Storage = users * data/user * retention
Bandwidth = QPS * avg response size
```

- 1M req/day $\approx$ 12 QPS
- 1 KB × 1M/day = 1 GB/day $\approx$ 365 GB/yr
- Powers of 2: 2\textsuperscript{10}=1K, 2\textsuperscript{20}=1M, 2\textsuperscript{30}=1G, 2\textsuperscript{40}=1T

# Databases

**SQL vs NoSQL decision:**

- SQL: relationships, transactions, complex queries, strong consistency
- NoSQL: flexible schema, horizontal scale, high write throughput

**Indexing**: B-tree (range queries), hash (point lookups), composite (multi-column)

**Replication**: leader-follower (read scale), leader-leader (write availability)

**Sharding**: hash-based (even distribution) vs range-based (locality), consistent hashing for rebalancing

**ACID**: Atomicity, Consistency, Isolation, Durability

# Caching

| Strategy | Reads | Writes |
|----------|-------|--------|
| Cache-aside | App checks cache, falls back to DB | App writes to DB, invalidates cache |
| Read-through | Cache fetches from DB on miss | — |
| Write-through | — | Write to cache + DB synchronously |
| Write-behind | — | Write to cache, async flush to DB |

- **TTL**: set expiry to bound staleness
- **Eviction**: LRU (most common), LFU, FIFO
- **Cache stampede**: lock/lease, staggered TTL, pre-warming
- **Invalidation** is the hard problem — prefer TTL + eventual consistency

# Message Queues

- **Point-to-point**: one consumer per message (task queues)
- **Pub/sub**: multiple subscribers per message (fan-out)
- **Backpressure**: rate limit producers or use bounded queues
- **DLQ**: dead-letter queue for failed messages — retry + alert
- **Ordering**: partition-level ordering (Kafka), FIFO queues (SQS)
- **At-least-once**: default — consumers must be idempotent
- **Exactly-once**: transactional outbox or deduplication

# Scaling

| Approach | When |
|----------|------|
| Vertical (scale up) | Quick fix, stateful services |
| Horizontal (scale out) | Stateless services, high throughput |
| Read replicas | Read-heavy workloads |
| Sharding | Write-heavy, large datasets |
| CDN | Static assets, global latency |
| Load balancer | Distribute across instances (round-robin, least-conn, consistent hash) |

# Availability & Reliability

- **SLA math**: 99.9\% = 8.7h downtime/yr, 99.99\% = 52min/yr
- **Redundancy**: no single points of failure — replicate everything
- **Health checks**: liveness (restart) vs readiness (stop traffic)
- **Circuit breaker**: fail fast when downstream is unhealthy
- **Retry**: exponential backoff + jitter, limit total attempts
- **Graceful degradation**: serve partial/cached results under pressure

# CAP & Consistency

- **CAP theorem**: pick 2 of Consistency, Availability, Partition tolerance (P is always present, so really C vs A)
- **Strong consistency**: reads see latest write (Raft/Paxos, single-leader)
- **Eventual consistency**: reads may be stale, converges over time
- **Conflict resolution**: last-write-wins, vector clocks, CRDTs

# Observability

- **Logs**: structured JSON, correlation IDs, severity levels
- **Metrics**: RED (Rate, Errors, Duration) for services; USE (Utilization, Saturation, Errors) for resources
- **Traces**: distributed tracing (OpenTelemetry) for request paths
- **Alerts**: symptom-based (SLO burn rate), not cause-based
