# Module 10: Classic System Design Problems

## Overview

This module covers six classic system design problems end to end. Each follows a consistent structure: requirements, estimation, high-level design, deep dives, and trade-offs. The goal is not to memorize solutions but to internalize reasoning patterns you can adapt to any problem.

---

## Problem 1: URL Shortener

### Requirements

**Functional:**
- Given a long URL, generate a short URL (e.g., `short.ly/abc123`).
- Redirecting to the short URL returns the original URL (HTTP 301/302).
- Optional: custom aliases, expiration, analytics (click count, referrers).
- Optional: rate limiting to prevent abuse.

**Non-Functional:**
- Read-heavy (100:1 read-to-write ratio is typical).
- Low latency redirects (< 10ms at the data layer).
- High availability — a URL shortener that is down breaks every link it ever created.
- URLs should not be guessable (no sequential IDs).

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

**Option A: Hash-Based**

Hash the URL with MD5/SHA-256, take the first 7 characters (base62 encoded).

```
MD5("https://example.com/long-path") = "d41d8cd98f..."
base62(first 43 bits) = "abc12Xz"
```

Problem: collisions. Two different URLs might produce the same 7-character prefix. Solution: check for collision, rehash with a salt if found.

**Option B: Counter-Based**

Use an auto-incrementing counter. Convert the counter value to base62.

```
Counter: 1000000 -> base62 -> "4c92"
Counter: 1000001 -> base62 -> "4c93"
```

Problem: sequential codes are guessable. Solution: combine with a random offset or shuffle bits.

**Option C: Pre-Generated Key Service**

A separate service pre-generates random unique keys and stores them in a pool. When a URL needs shortening, pop a key from the pool.

```
Key Service:  Pool of pre-generated keys ["Xk9mP", "q3Rtn", "Lm8Yz", ...]
Write path:   Pop key from pool -> Store key -> URL mapping
```

Advantage: no collision checking at write time. Disadvantage: additional service to manage.

**Recommendation:** Pre-generated key service for high-throughput systems. Hash-based for simpler setups with collision handling.

### Deep Dive: Read-Heavy Optimization

With a 100:1 read-to-write ratio, caching dominates the design.

```
GET /abc123
  -> Redis cache lookup (< 1ms)
  -> Cache hit? Return 301 redirect
  -> Cache miss? Query DB, populate cache with TTL, return 301 redirect
```

Cache sizing: if 20% of URLs account for 80% of traffic (Pareto), caching the hot set is sufficient. 20% of 6B URLs * 500 bytes = ~600 GB — a Redis cluster handles this.

### Deep Dive: Analytics

For each redirect, log an event:

```json
{"short_code": "abc123", "timestamp": "2024-01-15T10:30:00Z",
 "ip": "203.0.113.1", "user_agent": "...", "referrer": "..."}
```

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

**Functional:**
- One-on-one messaging between users.
- Group chat (up to 500 members).
- Online/offline presence indicators.
- Message ordering and delivery guarantees (at-least-once).
- Read receipts, typing indicators.
- Offline message delivery (push notifications).
- Media sharing (images, files).

**Non-Functional:**
- Low latency (< 100ms message delivery for online users).
- Persistence (messages are never lost).
- Ordered (messages appear in the order sent within a conversation).
- Scale: 50M daily active users, 1B messages/day.

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

Each client maintains a persistent WebSocket connection. The WebSocket Gateway is a stateful service — it holds connection state.

**Connection routing:** When User A sends a message to User B, the system needs to know which gateway server holds User B's connection.

```
User B connects -> Gateway Server 3
Registry (Redis): user_b -> gateway_server_3

User A sends message to User B:
  Chat Service -> lookup user_b in registry -> gateway_server_3
  Chat Service -> gateway_server_3: deliver message to user_b's WebSocket
```

**Scaling WebSocket servers:** Each server handles 50K-100K connections. For 10M concurrent users, you need 100-200 gateway servers. Use consistent hashing or a connection registry (Redis) to route messages to the correct server.

### Deep Dive: Message Ordering

Messages within a conversation must be ordered. Use a per-conversation sequence number.

```
Conversation conv_123:
  msg_1: seq=1, sender=alice, text="hello"
  msg_2: seq=2, sender=bob,   text="hi there"
  msg_3: seq=3, sender=alice, text="how are you?"
```

The sequence number is assigned by the Chat Service (server-side), not the client. Use an atomic counter per conversation (Redis INCR or database sequence).

For distributed environments, use a composite ordering key: `(server_timestamp, server_id, counter)` to ensure global ordering without a single counter bottleneck.

### Deep Dive: Group Chat

Group chat introduces fan-out: a message to a group of 500 must be delivered to 500 members.

**Small groups (< 500):** Write the message once, fan out to each member's inbox. The fan-out is manageable.

**Large groups / channels (> 500):** Do not fan out on write. Instead, members pull from the group's message stream. This is fan-out on read.

```
Small group write path:
  Store message -> For each member: push to inbox + push via WebSocket

Large channel read path:
  Store message in channel stream -> Members poll/subscribe to channel stream
```

### Deep Dive: Presence Detection

Presence (online/offline/away) is a distributed state problem.

- **Heartbeat-based:** Clients send periodic heartbeats (every 30 seconds). If no heartbeat is received within the timeout (60 seconds), mark the user as offline.
- **Store in Redis:** `SETEX user:alice:presence online 60` — auto-expires.
- **Fan-out presence changes:** When a user goes offline, notify their contacts. For users with many contacts, fan out asynchronously.

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Transport | WebSocket | Long polling / SSE | WebSocket for bidirectional, low-latency |
| Message store | Cassandra (wide column) | PostgreSQL (relational) | Cassandra for write-heavy, time-series access |
| Group fan-out | Fan-out on write | Fan-out on read | Write for small groups, read for large channels |
| Ordering | Lamport timestamps | Server-assigned sequence | Server sequence (simpler, sufficient for most) |
| Media storage | Inline in message DB | Separate object storage | Separate (S3) with CDN |

---

## Problem 3: News Feed / Timeline

### Requirements

**Functional:**
- Users create posts (text, images, links).
- Users see a feed of posts from people they follow.
- Feed is ranked (not purely chronological).
- Support for users with millions of followers (celebrities).
- Pagination (infinite scroll).

**Non-Functional:**
- Feed generation latency: < 200ms.
- Scale: 500M users, 1M new posts/day, 10B feed reads/day.
- Eventually consistent is acceptable (a post appearing 30 seconds late is fine).

### Estimation

- Feed reads: 10B/day = ~116,000 reads/second.
- New posts: 1M/day = ~12 posts/second.
- Average user follows 200 people.
- Feed size: 200 posts * 1KB = 200KB per user's cached feed.

### High-Level Design

```
Post Creation: Client -> Post Service -> Post Store + Fan-out Service
Feed Reading:  Client -> Feed Service -> Feed Cache (Redis) -> Feed Store
```

### Deep Dive: Fan-Out on Write vs. Fan-Out on Read

**Fan-Out on Write (Push Model)**

When a user creates a post, immediately push it to every follower's feed.

```
Alice posts -> Fan-out Service:
  For each of Alice's 200 followers:
    LPUSH feed:{follower_id} post_id
    LTRIM feed:{follower_id} 0 999  # Keep latest 1000
```

Pros: Feed reads are fast — just read from the pre-computed feed cache.
Cons: Celebrity problem. If a user has 10M followers, fan-out takes minutes. Wasteful if many followers are inactive.

**Fan-Out on Read (Pull Model)**

When a user opens their feed, query all followed users' recent posts and merge.

```
Bob opens feed -> Feed Service:
  Get list of users Bob follows: [alice, charlie, dave, ...]
  For each followed user: get recent posts
  Merge and rank
  Return top N
```

Pros: No write amplification. No celebrity problem.
Cons: Feed reads are slow — must query and merge hundreds of sources in real time.

**Hybrid Approach (The Answer)**

- For regular users (< 10K followers): fan-out on write. Pre-compute feeds.
- For celebrities (> 10K followers): fan-out on read. Merge celebrity posts into the feed at read time.

```
Bob opens feed:
  1. Read pre-computed feed from cache (contains posts from regular users)
  2. Fetch recent posts from celebrities Bob follows (small list, fast)
  3. Merge, rank, return
```

### Deep Dive: Ranking

Move beyond chronological ordering. Rank by relevance:

```python
score = (
    recency_weight * time_decay(post.created_at) +
    engagement_weight * (likes + comments + shares) +
    affinity_weight * user_affinity(viewer, author) +
    content_weight * content_quality_score(post)
)
```

Ranking is computed at feed read time. For pre-computed feeds, store candidate posts and rank at serving time.

### Deep Dive: Feed Caching and Pagination

Cache the feed as a sorted list in Redis. Use cursor-based pagination (not offset-based, which breaks when new posts are inserted).

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

**Functional:**
- Limit the number of requests a client can make within a time window.
- Support per-user, per-IP, per-API-key limits.
- Return appropriate headers (X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset).
- Support tiered limits (free: 100/min, pro: 10,000/min).

**Non-Functional:**
- Low latency (< 1ms overhead per request).
- Distributed (works across multiple API gateway instances).
- Accurate (no significant over-counting or under-counting).
- Fault-tolerant (if the rate limiter is down, fail open — allow traffic).

### High-Level Design

```
Client -> API Gateway -> Rate Limiter (check) -> Backend Service
                          |
                          v
                      Redis (distributed counters)
```

### Deep Dive: Algorithms

**1. Fixed Window Counter**

Divide time into fixed windows (e.g., 1-minute windows). Count requests per window.

```
Window [12:00:00 - 12:01:00]: counter = 87 (limit 100) -> ALLOW
Window [12:01:00 - 12:02:00]: counter = 0 -> ALLOW
```

Problem: boundary burst. A user can send 100 requests at 12:00:59 and 100 more at 12:01:00, effectively getting 200 in a 1-second span.

**2. Sliding Window Log**

Store the timestamp of every request. Count requests within the sliding window.

```
Window: last 60 seconds
Requests: [12:00:05, 12:00:15, 12:00:45, 12:01:02, ...]
Count requests where timestamp > now - 60s
```

Accurate but memory-intensive (stores every timestamp).

**3. Sliding Window Counter**

A hybrid: use fixed windows but weight the previous window by overlap.

```
Previous window count: 80 (12:00:00 - 12:01:00)
Current window count:  30 (12:01:00 - 12:02:00)
Current position: 12:01:15 (25% into current window)

Weighted count = 80 * 0.75 + 30 = 90
```

Good accuracy with low memory.

**4. Token Bucket**

A bucket holds tokens. Tokens are added at a fixed rate. Each request consumes a token. If the bucket is empty, the request is rejected.

```
Bucket capacity: 100 tokens
Refill rate: 100 tokens per minute
Current tokens: 5

Request arrives:
  tokens > 0? Yes -> Allow, tokens = 4
  tokens == 0? -> Reject (429 Too Many Requests)
```

The token bucket allows short bursts (up to bucket capacity) while maintaining a long-term average rate. This is the most commonly used algorithm.

**5. Leaky Bucket**

Requests enter a queue (the bucket). They are processed at a fixed rate. If the queue is full, requests are dropped. Produces a perfectly smooth output rate.

### Deep Dive: Distributed Rate Limiting with Redis

Multiple API gateway instances share rate limit state via Redis. Use a Lua script for atomic token bucket operations: read the current token count and last refill time, compute tokens to add based on elapsed time, decrement if tokens available (allow) or reject (429). Lua scripts execute atomically in Redis, preventing race conditions.

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

### Trade-offs

| Algorithm | Accuracy | Memory | Burst Handling | Complexity |
|-----------|----------|--------|----------------|------------|
| Fixed Window | Low (boundary issue) | Very low | Allows double-burst at boundary | Simple |
| Sliding Window Log | High | High (stores every timestamp) | No bursts | Moderate |
| Sliding Window Counter | Good | Low | Slight boundary imprecision | Moderate |
| Token Bucket | Good | Low | Allows controlled bursts | Moderate |
| Leaky Bucket | High | Moderate | No bursts (smooth output) | Moderate |

---

## Problem 5: Notification System

### Requirements

**Functional:**
- Multi-channel: push notifications (iOS/Android), email, SMS, in-app.
- Template engine for notification content.
- User preferences (opt-in/opt-out per channel and category).
- Delivery guarantees (at-least-once).
- Deduplication (don't send the same notification twice).
- Rate limiting (don't bombard users).
- Analytics (delivery rate, open rate, click-through rate).

**Non-Functional:**
- Scale: 100M notifications/day.
- Latency: real-time for push/in-app (< 5 seconds), near-real-time for email/SMS (< 1 minute).
- Reliability: critical notifications (2FA codes, password resets) must be delivered.

### Estimation

- 100M notifications/day = ~1,200/second average, ~5,000/second peak.
- Storage: notification log — 100M * 1KB = 100GB/day.

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
2. Load user preferences:
   - Does user_123 want "order updates"? On which channels?
   - Is user_123's push token valid? Do we have their email?
3. Template rendering:
   - Load template "order_shipped"
   - Fill in variables: {order_id}, {tracking_url}, {estimated_delivery}
   - Render per channel (push has character limits, email has HTML)
4. Deduplication check:
   - Hash(user_id + event_type + event_id) -> check Redis
   - If exists, skip (already sent)
   - If not, set with TTL and proceed
5. Rate limit check:
   - Has user received > 5 push notifications in the last hour? If so, batch.
6. Enqueue per channel:
   - Push: enqueue to push_queue
   - Email: enqueue to email_queue
   - Delivery workers consume and send via external providers
7. Track delivery status:
   - Log sent/delivered/failed/opened events
```

### Deep Dive: Template Engine

```json
{
  "template_id": "order_shipped",
  "channels": {
    "push": {
      "title": "Your order is on its way!",
      "body": "Order #{{order_id}} shipped. Track: {{tracking_url}}"
    },
    "email": {
      "subject": "Your order #{{order_id}} has shipped",
      "html_body": "<h1>Order Shipped</h1><p>Track at {{tracking_url}}</p>"
    },
    "sms": {
      "body": "Order #{{order_id}} shipped. Track: {{tracking_url}}"
    }
  }
}
```

Templates are versioned and A/B testable. Separate content from delivery logic.

### Deep Dive: Delivery Guarantees

For critical notifications (2FA codes):
- Use a persistent queue (SQS, Kafka) with at-least-once delivery.
- Track delivery status. Retry on failure with exponential backoff.
- Fallback channels: if push fails, try SMS. If SMS fails, try email.

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
| Dedup window | 1 hour | 24 hours | Depends on notification type |
| Template storage | Database | Git (version-controlled) | Git for templates, DB for metadata |

---

## Problem 6: File Storage Service

### Requirements

**Functional:**
- Upload files (up to 10 GB).
- Download files.
- Resumable uploads (survive network interruptions).
- File deduplication (don't store the same file twice).
- File sharing with access control (public link, password-protected, expiring links).
- Metadata: file name, size, type, owner, created/modified timestamps.
- Folder organization.

**Non-Functional:**
- Durability: 99.999999999% (eleven 9s, like S3).
- Availability: 99.9%.
- Scale: 500M files, 100TB storage, 10K uploads/day, 100K downloads/day.

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

For large files, split into chunks (e.g., 5 MB each).

```
1. Client -> API: POST /files/upload/init
   { filename: "video.mp4", size: 2147483648, chunk_size: 5242880 }
   Response: { upload_id: "up_abc", chunk_count: 410 }

2. Client -> S3: PUT /upload/up_abc/chunk/1  (presigned URL)
   Client -> S3: PUT /upload/up_abc/chunk/2  (presigned URL)
   ...
   (Upload chunks in parallel, 3-5 concurrent)

3. If interrupted: Client -> API: GET /files/upload/up_abc/status
   Response: { completed_chunks: [1, 2, 3, 5, 6], missing: [4, 7, 8, ...] }
   Client resumes from missing chunks.

4. Client -> API: POST /files/upload/up_abc/complete
   API triggers S3 multipart upload completion.
   Metadata service records the file.
```

### Deep Dive: Content-Addressable Storage (Deduplication)

If two users upload the same file, store it once.

```
Upload flow with dedup:
  1. Client computes SHA-256 hash of file content
  2. Client -> API: "I want to upload file with hash abc123"
  3. API checks: does object with hash abc123 exist in storage?
     - Yes: create a new metadata record pointing to the existing object.
            No upload needed ("instant upload").
     - No:  proceed with upload.
```

Storage structure:
```
Object storage: /objects/{sha256_hash}     (content-addressed)
Metadata DB:    file_id -> { name, owner, sha256_hash, size, created_at }
                Multiple file_ids can point to the same sha256_hash
```

Reference counting: track how many metadata records point to each object. Only delete the object when the reference count reaches zero.

### Deep Dive: CDN Distribution

For downloads, serve files from CDN edge locations.

```
Download flow:
  1. Client -> API: GET /files/{file_id}/download
  2. API checks permissions
  3. API generates a signed CloudFront URL:
     https://cdn.example.com/objects/abc123?Expires=...&Signature=...
  4. Client downloads from CDN (low latency, edge-cached)
```

For frequently accessed files, the CDN caches at edge locations. For rare files, the CDN fetches from the origin (S3) on first request.

### Deep Dive: Access Control

```
Permission model:
  - Owner: full control (read, write, delete, share)
  - Shared: read-only or read-write, per user or group
  - Public link: anyone with the link can access (optionally password-protected)
  - Expiring link: access revoked after a timestamp

Storage:
  file_permissions table:
    file_id | principal_type | principal_id | permission | expires_at
    f_123   | user           | u_456        | read       | NULL
    f_123   | link           | lnk_789      | read       | 2024-02-01
```

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Upload | Direct to S3 (presigned) | Through API server | Presigned URLs (offload bandwidth) |
| Dedup | Client-side hash | Server-side hash | Client computes, server verifies |
| Chunk size | Small (1 MB) | Large (10 MB) | 5 MB (balance between overhead and resumability) |
| Metadata DB | PostgreSQL | DynamoDB | PostgreSQL (complex queries, folder hierarchy) |
| CDN | CloudFront | Cloudflare | Either works; CloudFront integrates tightly with S3 |

---

## Interview Tips

1. **Start with requirements** (3-5 min). Clarify functional and non-functional requirements before designing.
2. **Do estimation.** Ground your design in numbers. Know your powers of 2.
3. **High-level first.** Draw boxes and arrows. Get agreement before going deep.
4. **Go deep where it matters.** Pick 2-3 critical aspects in a 45-minute interview.
5. **Discuss trade-offs explicitly.** State what you chose, what you rejected, and why.
6. **Consider failure modes.** Discuss graceful degradation for every component.
