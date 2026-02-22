# Module 10: Classic System Design Problems — Cheat Sheet

## System Design Interview Template

```
1. REQUIREMENTS (3-5 min)  — Functional (3-5 features), non-functional (scale, latency, consistency), scope
2. ESTIMATION (3-5 min)    — Traffic (RPS), storage (size * retention), bandwidth, cache sizing
3. HIGH-LEVEL DESIGN (5-10 min) — Major components, data flows (read/write paths), interviewer buy-in
4. DEEP DIVES (15-20 min)  — 2-3 critical components: data model, scaling, failure handling, trade-offs
5. WRAP-UP (5 min)         — Key decisions, alternatives, 10x/100x considerations, operational concerns
```

---

## Estimation Formulas

### Traffic

```
Requests/second = Daily requests / 86,400
Peak RPS        = Average RPS * 2-3 (typical peak multiplier)
Read:Write ratio = Common: 100:1 (read-heavy), 1:1 (balanced), 1:10 (write-heavy)
```

### Storage

```
Storage/year   = Records/day * Record size * 365
Total storage  = Storage/year * Retention years * Replication factor
```

### Bandwidth

```
Ingress  = Write RPS * Average write payload size
Egress   = Read RPS * Average read payload size
```

### Cache

```
Cache size = Hot data set size * Overhead (1.2-1.5x for metadata)
Pareto:    20% of data handles 80% of traffic
```

### Quick Numbers

```
1 million   = 10^6        1 GB  = 10^9 bytes
1 billion   = 10^9        1 TB  = 10^12 bytes
1 day       = 86,400 sec  1 PB  = 10^15 bytes
1 year      = 31.5M sec

Typical latencies:
  L1 cache:     0.5 ns     Memory:      100 ns
  SSD read:     100 us     HDD seek:    10 ms
  Same DC RTT:  0.5 ms     Cross-DC:    30-100 ms
  Redis GET:    < 1 ms     DB query:    1-10 ms

Typical throughput:
  Redis:    100K ops/sec (single node)
  PostgreSQL: 10K-50K queries/sec
  Kafka:    1M messages/sec (per broker)
  Single server: 10K-50K HTTP requests/sec
```

---

## Common Components Catalog

When designing a system, reach for these building blocks:

| Component | When to Use | Examples |
|-----------|------------|---------|
| **Load Balancer** | Distribute traffic across instances | ALB, NLB, Nginx, HAProxy |
| **API Gateway** | Auth, rate limiting, routing | Kong, AWS API Gateway, Envoy |
| **Cache** | Reduce DB load, speed up reads | Redis, Memcached |
| **CDN** | Serve static/media content at edge | CloudFront, Cloudflare, Akamai |
| **Message Queue** | Async processing, decoupling | SQS, RabbitMQ |
| **Event Stream** | Event sourcing, log processing, replay | Kafka, Kinesis |
| **Relational DB** | Structured data, transactions, joins | PostgreSQL, MySQL |
| **Document DB** | Flexible schema, nested objects | MongoDB, DynamoDB |
| **Wide-Column DB** | Time-series, high write throughput | Cassandra, ScyllaDB |
| **Search Engine** | Full-text search, faceted queries | Elasticsearch, OpenSearch |
| **Object Storage** | Files, images, videos, backups | S3, GCS |
| **Blob/Block Storage** | VM disks, databases | EBS, Persistent Disks |
| **WebSocket Server** | Real-time bidirectional communication | Custom, Socket.io |
| **Task Queue** | Background jobs, scheduled tasks | Celery, Sidekiq, SQS |
| **Service Mesh** | mTLS, traffic management, observability | Istio, Linkerd |

---

## Design Patterns Quick Reference

### Fan-Out on Write (Push)

```
Event occurs -> Push to all subscribers' inboxes

Use when: Subscriber count is small/medium (< 10K per event)
Examples: News feed (normal users), notification delivery
Trade-off: Fast reads, slow/expensive writes for popular producers
```

### Fan-Out on Read (Pull)

```
Reader requests data -> Fetch from all sources, merge at read time

Use when: Producer has many subscribers, or subscribers are often inactive
Examples: News feed (celebrities), large chat channels
Trade-off: Slow reads (merge at query time), no write amplification
```

### Event-Driven Architecture

```
Producer -> Event Bus (Kafka) -> Consumer A
                               -> Consumer B
                               -> Consumer C

Use when: Services need to react to events without tight coupling
Examples: Order placed -> inventory, payment, notification, analytics
Trade-off: Eventually consistent, harder to debug, requires idempotent consumers
```

### CQRS (Command Query Responsibility Segregation)

```
Writes -> Write Model (normalized DB) -> Event -> Read Model (denormalized, optimized)
Reads  -> Read Model

Use when: Read and write patterns are fundamentally different
Examples: E-commerce catalog (complex writes, simple reads), analytics dashboards
Trade-off: Complexity, eventual consistency between write and read models
```

### Sharding

```
Data partitioned by shard key across N nodes

Strategies:
  Hash-based:  shard = hash(key) % N    (even distribution, range queries hard)
  Range-based: shard by date/region      (range queries easy, hot spots possible)
  Directory:   lookup table maps key -> shard (flexible, lookup overhead)

Use when: Single node cannot handle data volume or throughput
Trade-off: Cross-shard queries are expensive, rebalancing is painful
```

### Content-Addressable Storage

```
Object ID = hash(content)
Same content -> same ID -> stored once

Use when: Deduplication matters (file storage, artifact caching)
Trade-off: Cannot modify content in place (new content = new hash = new object)
```

---

## Problem-Specific Key Decisions

| Problem | Critical Decision | Options | Key Factor |
|---------|------------------|---------|------------|
| **URL Shortener** | Code generation | Hash vs. counter vs. pre-generated pool | Collision handling, predictability |
| **URL Shortener** | Redirect code | 301 (permanent) vs. 302 (temporary) | Caching vs. analytics accuracy |
| **Chat System** | Transport | WebSocket vs. long polling vs. SSE | Bidirectional need, latency requirement |
| **Chat System** | Group fan-out | Write (push to inboxes) vs. Read (pull from stream) | Group size threshold (~500) |
| **Chat System** | Message ordering | Server timestamp vs. sequence number vs. Lamport | Consistency requirements |
| **News Feed** | Fan-out model | Push vs. pull vs. hybrid | Celebrity problem, read/write ratio |
| **News Feed** | Ranking | Chronological vs. relevance-scored | User engagement goals |
| **Rate Limiter** | Algorithm | Token bucket vs. sliding window vs. fixed window | Burst tolerance, accuracy needs |
| **Rate Limiter** | State store | Local memory vs. Redis (distributed) | Single vs. multi-node deployment |
| **Notification** | Delivery guarantee | At-most-once vs. at-least-once | Notification criticality (2FA vs. marketing) |
| **Notification** | Channel priority | Parallel all channels vs. waterfall with fallback | Cost, user preference |
| **File Storage** | Upload method | Direct to S3 (presigned) vs. through API | Bandwidth cost, security model |
| **File Storage** | Deduplication | Content-hash (global) vs. per-user | Storage savings vs. privacy concerns |
| **Task Scheduler** | Execution guarantee | At-least-once + idempotent vs. distributed lock | Complexity budget, task characteristics |
| **Autocomplete** | Data structure | Trie (in-memory) vs. search index (Elasticsearch) | Latency requirement, update frequency |
| **Video Streaming** | Streaming protocol | HLS vs. DASH vs. WebRTC | Device compatibility, latency needs |
| **Video Streaming** | CDN tier | Single CDN vs. multi-CDN | Cost, redundancy, geographic coverage |

---

## The "I Don't Know" Escape Hatch

If stuck on a detail, pivot honestly: "I am not sure about the exact implementation, but the approach involves [principle]. Let me describe the high-level approach." Or: "In practice, I would use [managed service]. The key decision is [trade-off], and I would choose [option] because [reason]." The interviewer tests reasoning, not memorization. Structured thinking with acknowledged gaps always beats guessing.
