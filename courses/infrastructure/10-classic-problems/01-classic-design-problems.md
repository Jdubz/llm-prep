# Module 10: Classic System Design Problems

## Overview

This module covers classic system design problems end to end. Each follows a consistent structure: requirements, estimation, high-level design, deep dives, and trade-offs. The goal is not to memorize solutions but to internalize reasoning patterns you can adapt to any problem.

---

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

### CQRS

```
Writes -> Write Model (normalized DB) -> Event -> Read Model (denormalized, optimized)
Reads  -> Read Model

Use when: Read and write patterns are fundamentally different
Trade-off: Complexity, eventual consistency between write and read models
```

### Sharding

```
Strategies:
  Hash-based:  shard = hash(key) % N    (even distribution, range queries hard)
  Range-based: shard by date/region      (range queries easy, hot spots possible)
  Directory:   lookup table maps key -> shard (flexible, lookup overhead)

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

## Problem 1: URL Shortener

### Requirements

**Functional:** Given a long URL, generate a short URL (e.g., `short.ly/abc123`). Redirecting to the short URL returns the original URL (HTTP 301/302). Optional: custom aliases, expiration, analytics (click count, referrers), rate limiting to prevent abuse.

**Non-Functional:** Read-heavy (100:1 read-to-write ratio is typical). Low latency redirects (< 10ms at the data layer). High availability. URLs should not be guessable (no sequential IDs).

### Estimation

- 100M new URLs per month = ~40 URLs/second (write).
- 10B redirects per month = ~4,000 redirects/second (read).
- Each URL record: ~500 bytes (short code + long URL + metadata).
- Storage: 100M * 500B * 12 months * 5 years = ~3 TB total.
- Read-heavy pattern: caching will be critical.

### High-Level Design

```
Client -> Load Balancer -> API Service -> Cache (Redis)
                                       -> Database (DynamoDB / PostgreSQL)

Write path: POST /shorten { url: "https://..." }
  -> Generate short code -> Store mapping -> Return short URL

Read path:  GET /abc123
  -> Check cache -> If miss, check DB -> Return 301 redirect
```

### Deep Dive: Short Code Generation

**Option A: Hash-Based** -- Hash the URL with MD5/SHA-256, take the first 7 characters (base62 encoded). Problem: collisions. Solution: check for collision, rehash with a salt if found.

**Option B: Counter-Based** -- Use an auto-incrementing counter. Convert the counter value to base62. Problem: sequential codes are guessable. Solution: combine with a random offset or shuffle bits.

**Option C: Pre-Generated Key Service** -- A separate service pre-generates random unique keys and stores them in a pool. When a URL needs shortening, pop a key from the pool.

```
Key Service:  Pool of pre-generated keys ["Xk9mP", "q3Rtn", "Lm8Yz", ...]
Write path:   Pop key from pool -> Store key -> URL mapping
```

**Recommendation:** Pre-generated key service for high-throughput systems. Hash-based for simpler setups with collision handling.

### Deep Dive: Caching

With a 100:1 read-to-write ratio, caching dominates the design. Cache sizing: if 20% of URLs account for 80% of traffic (Pareto), caching the hot set is sufficient. 20% of 6B URLs * 500 bytes = ~600 GB -- a Redis cluster handles this.

### Deep Dive: Analytics

Do not write analytics synchronously in the redirect path. Publish to a Kafka topic and process asynchronously. Aggregate in a time-series store or analytics database (ClickHouse, BigQuery).

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Code generation | Hash-based | Counter/pre-generated | Pre-generated for scale |
| Redirect status | 301 (permanent) | 302 (temporary) | 301 for SEO, 302 if you need analytics accuracy |
| Storage | SQL (PostgreSQL) | NoSQL (DynamoDB) | NoSQL for simple key-value pattern |
| Cache eviction | LRU | TTL-based | TTL with LRU fallback |

---

## Problem 2: Chat System

### Requirements

**Functional:** One-on-one messaging between users. Group chat (up to 500 members). Online/offline presence indicators. Message ordering and delivery guarantees (at-least-once). Read receipts, typing indicators. Offline message delivery (push notifications). Media sharing (images, files).

**Non-Functional:** Low latency (< 100ms message delivery for online users). Persistence (messages are never lost). Ordered (messages appear in the order sent within a conversation). Scale: 50M daily active users, 1B messages/day.

### Estimation

- 1B messages/day = ~12,000 messages/second.
- Average message size: 200 bytes text + 300 bytes metadata = 500 bytes.
- Storage: 1B * 500B * 365 = ~180 TB/year.
- Peak concurrent WebSocket connections: ~10M.

### High-Level Design

```
Client <-> WebSocket Gateway <-> Chat Service <-> Message Store
                              <-> Presence Service <-> Redis
                              <-> Push Notification Service
                              <-> Media Service -> Object Storage (S3)
```

### Deep Dive: WebSocket Management

Each client maintains a persistent WebSocket connection. Connection routing via a registry:

```
User B connects -> Gateway Server 3
Registry (Redis): user_b -> gateway_server_3

User A sends message to User B:
  Chat Service -> lookup user_b in registry -> gateway_server_3
  Chat Service -> gateway_server_3: deliver message to user_b's WebSocket
```

**Scaling WebSocket servers:** Each server handles 50K-100K connections. For 10M concurrent users, you need 100-200 gateway servers.

### Deep Dive: Message Ordering

Messages within a conversation must be ordered. Use a per-conversation sequence number assigned by the Chat Service (server-side, not client). Use an atomic counter per conversation (Redis INCR or database sequence).

For distributed environments, use a composite ordering key: `(server_timestamp, server_id, counter)` to ensure global ordering without a single counter bottleneck.

### Deep Dive: Group Chat Fan-Out

**Small groups (< 500):** Write the message once, fan out to each member's inbox.

**Large groups / channels (> 500):** Do not fan out on write. Instead, members pull from the group's message stream (fan-out on read).

### Deep Dive: Presence Detection

- **Heartbeat-based:** Clients send periodic heartbeats (every 30 seconds). If no heartbeat is received within the timeout (60 seconds), mark the user as offline.
- **Store in Redis:** `SETEX user:alice:presence online 60` -- auto-expires.
- **Fan-out presence changes:** When a user goes offline, notify their contacts asynchronously.

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Transport | WebSocket | Long polling / SSE | WebSocket for bidirectional, low-latency |
| Message store | Cassandra (wide column) | PostgreSQL (relational) | Cassandra for write-heavy, time-series access |
| Group fan-out | Fan-out on write | Fan-out on read | Write for small groups, read for large channels |
| Ordering | Lamport timestamps | Server-assigned sequence | Server sequence (simpler, sufficient for most) |

---

## Problem 3: News Feed / Timeline

### Requirements

**Functional:** Users create posts (text, images, links). Users see a feed of posts from people they follow. Feed is ranked (not purely chronological). Support for users with millions of followers (celebrities). Pagination (infinite scroll).

**Non-Functional:** Feed generation latency: < 200ms. Scale: 500M users, 1M new posts/day, 10B feed reads/day. Eventually consistent is acceptable.

### High-Level Design

```
Post Creation: Client -> Post Service -> Post Store + Fan-out Service
Feed Reading:  Client -> Feed Service -> Feed Cache (Redis) -> Feed Store
```

### Deep Dive: Fan-Out Hybrid Approach

**Fan-Out on Write (Push):** When a user creates a post, immediately push it to every follower's feed. Pros: Feed reads are fast. Cons: Celebrity problem -- if a user has 10M followers, fan-out takes minutes.

**Fan-Out on Read (Pull):** When a user opens their feed, query all followed users' recent posts and merge. Pros: No write amplification. Cons: Feed reads are slow.

**Hybrid Approach (The Answer):**
- For regular users (< 10K followers): fan-out on write. Pre-compute feeds.
- For celebrities (> 10K followers): fan-out on read. Merge celebrity posts into the feed at read time.

```
Bob opens feed:
  1. Read pre-computed feed from cache (contains posts from regular users)
  2. Fetch recent posts from celebrities Bob follows (small list, fast)
  3. Merge, rank, return
```

### Deep Dive: Ranking

```python
score = (
    recency_weight * time_decay(post.created_at) +
    engagement_weight * (likes + comments + shares) +
    affinity_weight * user_affinity(viewer, author) +
    content_weight * content_quality_score(post)
)
```

### Deep Dive: Pagination

Use cursor-based pagination (not offset-based, which breaks when new posts are inserted):

```
GET /feed?cursor=post_id_500&limit=20
  -> Return posts 501-520, next_cursor=post_id_520
```

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Fan-out | On write (push) | On read (pull) | Hybrid: push for regulars, pull for celebrities |
| Ranking | Chronological | ML-ranked | Ranked, with chronological as fallback |
| Feed storage | Redis (sorted set) | Cassandra | Redis for hot feeds, Cassandra for archive |
| Pagination | Offset-based | Cursor-based | Cursor-based (stable under insertions) |

---

## Problem 4: Rate Limiter

### Requirements

**Functional:** Limit the number of requests a client can make within a time window. Support per-user, per-IP, per-API-key limits. Return appropriate headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset). Support tiered limits (free: 100/min, pro: 10,000/min).

**Non-Functional:** Low latency (< 1ms overhead per request). Distributed (works across multiple API gateway instances). Accurate. Fault-tolerant (if the rate limiter is down, fail open -- allow traffic).

### High-Level Design

```
Client -> API Gateway -> Rate Limiter (check) -> Backend Service
                          |
                          v
                      Redis (distributed counters)
```

### Deep Dive: Algorithms

**1. Fixed Window Counter** -- Divide time into fixed windows. Problem: boundary burst (200 requests in a 1-second span across the boundary).

**2. Sliding Window Log** -- Store the timestamp of every request. Count requests within the sliding window. Accurate but memory-intensive.

**3. Sliding Window Counter** -- A hybrid using fixed windows weighted by overlap.

```
Weighted count = previous_window_count * (1 - elapsed_fraction) + current_window_count
```

**4. Token Bucket** -- A bucket holds tokens added at a fixed rate. Each request consumes a token. Allows controlled bursts up to bucket capacity. **The most commonly used algorithm.**

**5. Leaky Bucket** -- Requests enter a queue processed at a fixed rate. Produces a perfectly smooth output rate. No bursts.

### Deep Dive: Algorithm Comparison

| Algorithm | Accuracy | Memory | Burst Handling | Complexity |
|-----------|----------|--------|----------------|------------|
| Fixed Window | Low (boundary issue) | Very low | Allows double-burst at boundary | Simple |
| Sliding Window Log | High | High (stores every timestamp) | No bursts | Moderate |
| Sliding Window Counter | Good | Low | Slight boundary imprecision | Moderate |
| Token Bucket | Good | Low | Allows controlled bursts | Moderate |
| Leaky Bucket | High | Moderate | No bursts (smooth output) | Moderate |

### Deep Dive: Rate Limit Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1705312800

HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705312800
Retry-After: 30
```

---

## Problem 5: Notification System

### Requirements

**Functional:** Multi-channel: push notifications (iOS/Android), email, SMS, in-app. Template engine for notification content. User preferences (opt-in/opt-out per channel and category). Delivery guarantees (at-least-once). Deduplication. Rate limiting (don't bombard users). Analytics (delivery rate, open rate, click-through rate).

**Non-Functional:** Scale: 100M notifications/day. Latency: real-time for push/in-app (< 5 seconds), near-real-time for email/SMS (< 1 minute). Critical notifications (2FA codes, password resets) must be delivered.

### High-Level Design

```
Triggering Service -> Notification Service -> Preference Check
                                           -> Template Engine
                                           -> Channel Router
                                              ├── Push Queue -> Push Provider (APNS/FCM)
                                              ├── Email Queue -> Email Provider (SES/SendGrid)
                                              ├── SMS Queue -> SMS Provider (Twilio)
                                              └── In-App Queue -> WebSocket Gateway
                                           -> Notification Log (analytics)
```

### Deep Dive: Delivery Pipeline

```
1. Event received (e.g., "order shipped" for user_123)
2. Load user preferences: Does user want this notification? On which channels?
3. Template rendering: Load template, fill variables, render per channel
4. Deduplication check: Hash(user_id + event_type + event_id) -> check Redis
5. Rate limit check: Has user received > 5 push notifications in the last hour?
6. Enqueue per channel: push_queue, email_queue, sms_queue
7. Track delivery status: Log sent/delivered/failed/opened events
```

### Deep Dive: Delivery Guarantees

For critical notifications (2FA codes):

```python
async def deliver_with_fallback(notification):
    channels = ["push", "sms", "email"]  # Priority order
    for channel in channels:
        success = await send(channel, notification)
        if success:
            return
        log.warn(f"Failed on {channel}, trying next")
    log.error(f"All channels failed for {notification.id}")
    # Alert on-call
```

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Queue | SQS (managed) | Kafka (self-hosted) | SQS for simplicity, Kafka if you need replay |
| Priority | Single queue | Separate priority queues | Priority queues (critical vs. marketing) |
| Template storage | Database | Git (version-controlled) | Git for templates, DB for metadata |

---

## Problem 6: File Storage Service

### Requirements

**Functional:** Upload files (up to 10 GB). Download files. Resumable uploads. File deduplication (don't store the same file twice). File sharing with access control (public link, password-protected, expiring links). Metadata, folder organization.

**Non-Functional:** Durability: 99.999999999% (eleven 9s). Availability: 99.9%. Scale: 500M files, 100TB storage.

### High-Level Design

```
Client -> API Gateway -> File Metadata Service -> Metadata DB (PostgreSQL)
                      -> Upload Service -> Object Storage (S3)
                      -> Download Service -> CDN (CloudFront) -> Object Storage

Upload flow (chunked):
  1. Client requests upload session (metadata service)
  2. Client uploads chunks directly to object storage (presigned URLs)
  3. On completion, metadata service records the file

Download flow:
  1. Client requests file (metadata service checks permissions)
  2. Redirect to CDN URL (signed URL with expiry)
```

### Deep Dive: Chunked and Resumable Uploads

```
1. Client -> API: POST /files/upload/init
   { filename: "video.mp4", size: 2147483648, chunk_size: 5242880 }
   Response: { upload_id: "up_abc", chunk_count: 410 }

2. Client -> S3: PUT /upload/up_abc/chunk/1  (presigned URL, chunks in parallel)

3. If interrupted: Client -> API: GET /files/upload/up_abc/status
   Response: { completed_chunks: [1, 2, 3, 5, 6], missing: [4, 7, 8, ...] }

4. Client -> API: POST /files/upload/up_abc/complete
```

### Deep Dive: Content-Addressable Storage (Deduplication)

```
Upload flow with dedup:
  1. Client computes SHA-256 hash of file content
  2. Client -> API: "I want to upload file with hash abc123"
  3. API checks: does object with hash abc123 exist?
     - Yes: create metadata record pointing to existing object ("instant upload")
     - No:  proceed with upload

Object storage: /objects/{sha256_hash}  (content-addressed)
Metadata DB: file_id -> { name, owner, sha256_hash, size, created_at }
```

Reference counting: track how many metadata records point to each object. Only delete the object when the reference count reaches zero.

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Upload | Direct to S3 (presigned) | Through API server | Presigned URLs (offload bandwidth) |
| Dedup | Client-side hash | Server-side hash | Client computes, server verifies |
| Chunk size | Small (1 MB) | Large (10 MB) | 5 MB (balance between overhead and resumability) |
| CDN | CloudFront | Cloudflare | Either works; CloudFront integrates tightly with S3 |

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
| **File Storage** | Upload method | Direct to S3 (presigned) vs. through API | Bandwidth cost, security model |
| **File Storage** | Deduplication | Content-hash (global) vs. per-user | Storage savings vs. privacy concerns |

---

## Interview Tips

1. **Start with requirements** (3-5 min). Clarify functional and non-functional requirements before designing.
2. **Do estimation.** Ground your design in numbers. Know your powers of 2.
3. **High-level first.** Draw boxes and arrows. Get agreement before going deep.
4. **Go deep where it matters.** Pick 2-3 critical aspects in a 45-minute interview.
5. **Discuss trade-offs explicitly.** State what you chose, what you rejected, and why.
6. **Consider failure modes.** Discuss graceful degradation for every component.

If stuck on a detail, pivot honestly: "I am not sure about the exact implementation, but the approach involves [principle]. Let me describe the high-level approach." The interviewer tests reasoning, not memorization.
