# 06 – Scaling at Dropbox Scale

You've never operated a system serving 700M users with exabytes of storage. That's fine — most candidates haven't. But you need to **reason about it fluently** in real time during a system design interview. This module gives you the mental models, vocabulary, concrete numbers, and back-of-envelope math to speak like someone who has.

---

## 1. Dropbox by the Numbers

Memorize these. Interviewers expect you to use realistic numbers, not vague hand-waves.

| Metric | Value | Why It Matters |
|--------|-------|----------------|
| Registered users | 700M+ | Metadata and account storage at this scale |
| Paying users | 18M | Revenue-generating; higher usage, more storage |
| Daily active users (est.) | 30-50M | Concurrent load estimation |
| Files stored | Hundreds of billions | Index size, metadata DB rows |
| Total storage | Exabytes (1 EB = 10^18 bytes) | Storage architecture decisions |
| Average file size | ~1 MB | Chunking math, bandwidth estimation |
| Max file size | 50 GB | Must handle gracefully (chunking mandatory) |
| Peak sync operations | Millions per minute | Write throughput requirement |
| Connected apps per Dash user | 8-10 avg | Fan-out for connector sync |
| Search latency target | < 1s results, < 2s AI answer | End-to-end latency budget |
| Dash documents per user (est.) | 10K-100K across all apps | Index size per shard |
| Dropbox employees | ~2,800 | Context for eng team size |

### Derived Numbers You Should Be Able to Compute

**Storage math:**
- 700M users × 2 GB avg storage = 1.4 exabytes (fits reported numbers)
- With 3x replication: 4.2 EB (why erasure coding matters — drops to ~2.1 EB)
- With deduplication: significant further reduction (cross-user identical files)

**Request math:**
- 50M DAU × 20 file operations/day = 1 billion operations/day
- 1B / 86,400 seconds ≈ **~12K operations/second average**
- Peak (3x average): **~36K ops/sec**
- This is why you need horizontal scaling — a single database can't handle this

**Search math (Dash):**
- 10M Dash users × 5 searches/day = 50M queries/day
- 50M / 86,400 ≈ **~580 QPS average**
- Peak: **~2K QPS**
- Each query fans out to lexical + semantic index = 4K internal requests/sec
- Each AI answer needs LLM inference = 2K LLM calls/sec at peak (expensive)

**Metadata math:**
- 100B files × 1 KB metadata per file = **100 TB of metadata**
- This doesn't fit on one machine — sharding is mandatory
- At 1 TB per PostgreSQL shard: need 100+ shards minimum

---

## 2. The Scaling Vocabulary

These are the terms you must use naturally. If you fumble or misuse them, the interviewer notices.

### Horizontal vs. Vertical Scaling

| | Horizontal (Scale Out) | Vertical (Scale Up) |
|-|----------------------|---------------------|
| What | Add more machines | Get a bigger machine |
| When | Past single-machine limits | Before you need distributed complexity |
| Dropbox example | Add block servers behind LB | Upgrade metadata DB to more RAM |
| Limit | Coordination overhead | Single-machine ceiling |
| Interview signal | Always discuss horizontal first — it's the answer at Dropbox scale |

**What to say:** "At Dropbox's scale, vertical scaling hits its ceiling quickly. For [component], I'd design for horizontal scaling from the start by [sharding strategy]."

### Sharding

The most important scaling concept for this interview. Know it cold.

**What it is:** Splitting data across multiple machines so no single machine holds everything.

**Sharding strategies you must know:**

| Strategy | How | Pros | Cons | When to Use |
|----------|-----|------|------|-------------|
| **Hash-based** | `shard = hash(key) % N` | Even distribution | Resharding is painful (consistent hashing helps) | User data, general-purpose |
| **Range-based** | `shard = key_range` | Good for range queries, easy to understand | Hot spots if ranges are uneven | Time-series data, alphabetical |
| **Geographic** | `shard = user_region` | Data locality, compliance | Uneven sizes, cross-region queries hard | Global services with data residency |
| **Directory-based** | Lookup table maps key → shard | Flexible, can rebalance | Lookup table is a SPOF | When you need fine-grained control |

**Dropbox's sharding choices:**
- **Metadata DB:** Sharded by user_id (all of a user's files on one shard)
- **Search index (Dash):** Sharded by user_id (queries hit one shard)
- **Block storage:** Content-addressed (hash of block content determines location)
- **Notifications:** Sharded by user_id

**Why user_id sharding dominates at Dropbox:** Almost every operation is user-scoped (my files, my search, my notifications). Sharding by user_id means queries only hit one shard. No cross-shard joins. Simple and fast.

**What to say:** "I'd shard by user_id because the access pattern is user-scoped. Each query only needs one shard, which keeps latency predictable. For rebalancing, I'd use consistent hashing to minimize data movement when adding shards."

### Consistent Hashing

**Why it matters:** When you add/remove shards with naive `hash % N`, almost every key moves. With consistent hashing, only `K/N` keys move (K = keys, N = nodes).

```
Naive hashing: add 1 server to 10 → ~90% of keys remapped
Consistent hashing: add 1 server to 10 → ~10% of keys remapped
```

**What to say:** "For the [block server / cache layer], I'd use consistent hashing with virtual nodes to distribute load evenly. When we add capacity, only a fraction of data migrates."

### Replication

| Type | How | Latency | Consistency | Dropbox Use |
|------|-----|---------|-------------|-------------|
| **Leader-follower** | One primary, N replicas | Writes to leader, reads from replicas | Eventual (or sync for strong) | Metadata DB |
| **Multi-leader** | Multiple write nodes | Both can accept writes | Conflict resolution needed | Cross-region sync |
| **Leaderless** | Any node accepts reads/writes | Quorum-based | Tunable (R+W > N) | Dynamo-style stores |

**Dropbox pattern:** Leader-follower for metadata (strong consistency for file operations). Read replicas handle the read-heavy workload (listing files, checking versions).

**What to say:** "Metadata needs strong consistency — you can't show a user a stale file list. I'd use leader-follower replication with synchronous writes to at least one replica for durability. Search indexes can tolerate a few seconds of staleness, so async replication is fine there."

### Caching Layers

Know the full caching stack from client to storage:

```
Browser cache (static assets, 1hr+)
    ↓
CDN (Cloudflare/Akamai — static + popular blocks, geographic edge)
    ↓
API Gateway cache (rate limiting state, auth tokens)
    ↓
Application cache (Redis/Memcached — session data, hot metadata, search results)
    ↓
Database query cache (frequently accessed rows)
    ↓
Storage cache (OS page cache, SSD tiers before HDD)
```

**Key numbers:**
- Redis: ~100K ops/sec per node, sub-ms latency
- Memcached: ~200K ops/sec per node, slightly faster than Redis
- CDN hit rate target: > 90% for static assets
- Cache hit rate target: > 95% for hot metadata

**Dropbox caching strategy:**
- **Hot user sessions** → Redis (who's currently syncing)
- **File metadata** → Memcached (repeated reads during sync)
- **Search results** → Short-TTL cache (queries repeat, but freshness matters)
- **Block data** → CDN for popular files (shared folders, public links)

**What to say:** "I'd add a caching layer between [service] and [database] using Redis. For this access pattern, I'd expect a 95%+ hit rate because [reason — e.g., users repeatedly access the same files]. Cache invalidation on write — when a file is updated, evict the cached metadata entry."

### Load Balancing

| Algorithm | How | Best For |
|-----------|-----|----------|
| Round-robin | Rotate through servers | Stateless services (block servers) |
| Least connections | Route to least-loaded server | Varying request costs |
| Consistent hashing | Route by key | Sticky sessions (WebSocket, cache locality) |
| Weighted | Distribute based on capacity | Heterogeneous hardware |

**What to say:** "Block servers are stateless, so round-robin load balancing works well. For WebSocket connections (notifications), I'd use consistent hashing so all of a user's connections hit the same server."

---

## 3. Back-of-Envelope Estimation

Interviewers love when you do quick math to justify decisions. Practice these patterns.

### The Powers of 2 You Need

| Power | Value | Meaning |
|-------|-------|---------|
| 2^10 | 1 KB | A small text file |
| 2^20 | 1 MB | A photo, a short doc |
| 2^30 | 1 GB | A movie, a large dataset |
| 2^40 | 1 TB | A database shard |
| 2^50 | 1 PB | A data warehouse |

### Time Reference Points

| Duration | Seconds | Useful For |
|----------|---------|-----------|
| 1 day | 86,400 (~10^5) | Daily rate → per-second conversion |
| 1 month | 2.6M (~2.5 × 10^6) | Monthly quotas |
| 1 year | 31.5M (~3 × 10^7) | Annual storage growth |

### The Estimation Framework

**Step 1: Start with users.**
"We have 50M DAU. Each user does X per day."

**Step 2: Compute daily volume.**
"50M × X = Y per day."

**Step 3: Convert to per-second.**
"Y / 86,400 ≈ Z per second."

**Step 4: Account for peak.**
"Peak is typically 3-5x average. So Z × 3 = peak QPS."

**Step 5: Size the infrastructure.**
"Each server handles ~N QPS. We need Z × 3 / N servers = [answer]."

### Worked Example: Size the Dash Search Cluster

```
Users: 10M Dash users
Queries: 5 searches/user/day
Daily queries: 50M
QPS average: 50M / 86,400 ≈ 580
QPS peak (3x): ~1,750 → round to 2K

Each Elasticsearch node handles ~500 QPS for this query complexity.
Need: 2,000 / 500 = 4 nodes minimum.
With replication (3x for HA): 12 nodes.
With headroom (never run > 70% capacity): 12 / 0.7 ≈ 18 nodes.

Index size: 10M users × 50K docs/user × 2KB/doc = 1 PB.
Per shard (1TB each): 1,000 shards.
Per node (18 nodes): ~55 shards/node.

Verdict: ~18 Elasticsearch nodes, 1,000 shards, 3x replicated.
```

**Practice this out loud.** Interviewers want to see you do it in real-time, not recite it.

### Worked Example: Size the Notification Fan-Out

```
Event: A shared folder with 100 users gets a new file.
Fan-out: 100 notifications (one per user).
If this happens 1M times/day:
  Notifications/day: 100M
  Notifications/sec: 100M / 86,400 ≈ 1,200/sec
  Peak: ~4,000/sec

Each Kafka partition handles ~10K messages/sec.
Need: 1 partition is enough for throughput.
For parallelism (multiple consumers): 10 partitions.
For ordering (per-user): partition by user_id.
```

### Worked Example: Storage Growth Projection

```
Current: 1 EB of user data.
Growth rate: 20% YoY (typical for mature storage).
Year 1: 1.2 EB
Year 2: 1.44 EB
Year 3: 1.73 EB

With erasure coding (1.5x overhead): 1 EB → 1.5 EB raw storage.
With 3x replication: 1 EB → 3 EB raw storage.
Erasure coding saves 1.5 EB — at HDD prices (~$20/TB), that's $30M/year.
This is why Dropbox built Magic Pocket.
```

---

## 4. Scaling Patterns for Every Dropbox System

### Pattern: Read-Heavy System (Most of Dropbox)

**Signal:** Reads >> Writes (10:1 or higher). File listing, search, metadata lookups.

```
Client
  ↓ (read)
Load Balancer
  ↓
Cache (Redis/Memcached) ←── 95%+ hit rate
  ↓ (cache miss)
Read Replica 1, 2, 3...
  ↓ (writes only)
Primary DB
```

**Key decisions:**
- How stale can reads be? (File metadata: seconds. Search index: minutes.)
- Cache invalidation strategy? (Write-through vs. write-behind vs. TTL)
- How many read replicas? (Based on QPS / per-replica throughput)

**What to say:** "File operations are ~90% reads. I'd use a cache in front of read replicas. Writes go to the primary and invalidate the cache. With a 95% cache hit rate, only 5% of reads hit the replicas, which dramatically reduces DB load."

### Pattern: Write-Heavy System (Sync, Indexing)

**Signal:** High write throughput. File sync uploads, search index updates.

```
Client
  ↓ (write)
Write Queue (Kafka)
  ↓ (batch + async)
Write Workers
  ↓
Sharded DB / Storage
```

**Key decisions:**
- Can writes be async? (Sync events: yes. Metadata updates: depends.)
- Batch size? (Trade latency for throughput.)
- Ordering guarantees? (Per-user ordering via Kafka partition key.)

**What to say:** "Index updates are write-heavy — every document change across 60 connectors generates an index write. I'd use Kafka to buffer writes and batch them. Workers consume from Kafka, batch 100 updates, and write to the shard. This smooths out write spikes and gives us ordering guarantees per user."

### Pattern: Fan-Out on Write vs. Fan-Out on Read

**The tradeoff:** When a shared folder changes, do you pre-compute notifications for all 100 users (fan-out on write), or compute them when each user checks (fan-out on read)?

| | Fan-Out on Write | Fan-Out on Read |
|-|-----------------|-----------------|
| Write cost | High (write N copies) | Low (write 1 event) |
| Read cost | Low (pre-computed) | High (compute on read) |
| Latency | Low reads | Higher reads |
| Storage | More (N copies) | Less (1 copy) |
| Best for | Small fan-out (< 1000), latency-sensitive | Large fan-out, storage-sensitive |

**Dropbox pattern:** Fan-out on write for notifications (most shared folders have < 100 users). Fan-out on read for activity feeds (aggregate on query).

**What to say:** "For notifications with a typical fan-out of 10-100 users, I'd use fan-out on write — pre-compute and store each user's notification at write time. The storage cost is acceptable and it keeps read latency low. If we had cases with 10K+ recipients, I'd switch to fan-out on read for those to avoid write amplification."

### Pattern: Event-Driven Architecture (Kafka Backbone)

Dropbox uses Kafka as the central nervous system. Almost every async operation flows through it.

```
Producers                    Kafka                     Consumers
───────────                  ─────                     ─────────
File sync service  ──→  ┌──────────────┐  ──→  Notification service
Search indexer     ──→  │   Kafka      │  ──→  Analytics pipeline
Connector sync     ──→  │   Topics     │  ──→  Search index workers
User activity      ──→  └──────────────┘  ──→  Feature store
```

**Key Kafka numbers:**
- Single partition: ~10K messages/sec write throughput
- Single broker: ~100K messages/sec aggregate
- Consumer lag: monitor this — if it grows, consumers can't keep up
- Retention: 7 days typical (replay window for failures)

**What to say:** "I'd use Kafka as the event bus between [producer] and [consumer]. This decouples the services — the producer doesn't need to know about every consumer. Kafka also gives us replay capability: if the indexer crashes, it can reprocess events from where it left off."

### Pattern: Circuit Breaker (External Dependencies)

Critical for Dash — you depend on 60+ external APIs that can fail at any time.

```
Normal:   Service → External API ✓ → Response
Failing:  Service → External API ✗ → Timeout (slow, wastes resources)
Breaker:  Service → [OPEN circuit] → Fallback (fast, no wasted resources)
```

**States:**
- **Closed** (normal): Requests pass through. Track failure rate.
- **Open** (tripped): Requests fail immediately. Return cached/fallback. Timer starts.
- **Half-open** (testing): Allow one request through. If it succeeds, close. If it fails, re-open.

**What to say:** "Each connector needs a circuit breaker. If the Gmail API starts timing out, we trip the circuit after 5 failures in 30 seconds. Users see slightly stale Gmail results from cache instead of waiting 30 seconds for a timeout. When Gmail recovers, the half-open state lets us detect it automatically."

### Pattern: Graceful Degradation

At Dropbox scale, **something is always broken.** The question is whether users notice.

| Component Down | Degraded Experience | User Impact |
|---------------|-------------------|-------------|
| Semantic search | Lexical-only results (less accurate) | Mild — most queries still work |
| LLM service | No AI answers (show search results only) | Moderate — feature missing but usable |
| One connector | That app's content stale | Mild — other apps still work |
| Embedding service | No new semantic indexing | Low — existing index still serves |
| Cache layer | Direct DB hits (slower) | Moderate — higher latency |
| One DB shard | Users on that shard can't sync | Severe — failover critical |

**What to say:** "I'd design every component with a degraded mode. If the AI service is down, show search results without AI answers — still useful. If a connector API is flaky, serve cached results and show a 'last synced 5 min ago' badge. The user's experience degrades gracefully instead of breaking entirely."

---

## 5. Scaling Anti-Patterns (What NOT to Say)

These will make an interviewer doubt your experience. Avoid them.

### Anti-Pattern 1: "Just add more servers"

**Why it's wrong:** Horizontal scaling doesn't magically work. You need to explain how state is partitioned, how requests are routed, and what happens during rebalancing.

**Say instead:** "I'd scale [component] horizontally by sharding on [key]. Requests route to the correct shard via [consistent hashing / directory service]. When adding shards, we [rebalance strategy]."

### Anti-Pattern 2: "Use a NoSQL database for everything"

**Why it's wrong:** NoSQL isn't a scaling strategy — it's a data model choice. PostgreSQL with proper sharding handles Dropbox's scale. The choice depends on access patterns, not scale alone.

**Say instead:** "For this access pattern [describe], I'd use [specific database] because [specific reason]. At higher scale, I'd shard by [key] across [N] instances."

### Anti-Pattern 3: "Cache everything"

**Why it's wrong:** Caching adds complexity (invalidation, consistency, cold start). You need to justify which data benefits from caching and what staleness is acceptable.

**Say instead:** "I'd cache [specific data] because it's read-heavy with a [X:1] read:write ratio. TTL of [Y seconds] is acceptable because [staleness tolerance]. Cache invalidation happens on [write/event]."

### Anti-Pattern 4: "Use a message queue" (without specifics)

**Why it's wrong:** Message queues have different guarantees (at-least-once, exactly-once, ordering). You need to explain which guarantees matter and why.

**Say instead:** "I'd use Kafka here because I need ordered processing per user — I'd partition by user_id. At-least-once delivery is fine because the consumer is idempotent."

### Anti-Pattern 5: "Microservices for everything"

**Why it's wrong:** Dropbox ran on a Python monolith for years — and it worked. Microservices add network hops, operational complexity, and debugging difficulty. They make sense when teams need independent deployment, not as a default.

**Say instead:** "I'd start with [simpler architecture]. If the team grows and deployment coupling becomes a problem, I'd extract [specific service] because [specific reason]."

### Anti-Pattern 6: Saying "exactly-once delivery"

**Why it's a red flag:** Exactly-once delivery is impossible in distributed systems (per FLP impossibility). You can achieve exactly-once *processing* via idempotent consumers + at-least-once delivery.

**Say instead:** "I'd use at-least-once delivery with idempotent consumers. Each message has a dedup key. The consumer checks if it's already processed before acting."

---

## 6. Scaling Drills

### Drill 1: Capacity Estimation Speed Round

Do each in under 2 minutes. Write down your work. Then check.

**A) How much bandwidth does Dropbox file sync consume?**

<details>
<summary>Work it out</summary>

```
50M DAU × 10 MB synced/user/day = 500 PB/day
500 PB / 86,400 sec = ~5.8 TB/sec average
Peak (3x): ~17 TB/sec

That's massive. This is why:
- Delta sync (only changed blocks) reduces actual transfer by ~90%
- Compression reduces further by ~50%  
- Effective bandwidth: ~17 TB × 0.1 × 0.5 = ~850 GB/sec peak
- Still enormous — distributed across thousands of block servers worldwide
```

</details>

**B) How many Kafka brokers does Dash need for search events?**

<details>
<summary>Work it out</summary>

```
10M Dash users × 10 connected apps × 100 changes/app/day = 10B events/day
10B / 86,400 ≈ 115K events/sec average
Peak (3x): ~350K events/sec

Each Kafka broker: ~100K messages/sec aggregate throughput
Need: 350K / 100K = 3.5 → 4 brokers minimum
With replication factor 3: still 4 brokers (RF affects storage, not throughput)
With headroom: 6-8 brokers
```

</details>

**C) How big is the Dash search index per user?**

<details>
<summary>Work it out</summary>

```
Average user: 10 connected apps
Documents per app: ~5K (emails, messages, docs, tickets)
Total docs per user: ~50K

Per document:
- Inverted index entry: ~500 bytes
- Vector embedding (768 dims × 4 bytes): ~3 KB
- Metadata: ~500 bytes
Total per doc: ~4 KB

Per user index: 50K × 4 KB = 200 MB
Total for 10M users: 200 MB × 10M = 2 PB

Sharded across ~2,000 shards (1 TB each).
```

</details>

**D) How many LLM inference GPUs does Dash need at peak?**

<details>
<summary>Work it out</summary>

```
2K AI answer requests/sec at peak.
Each LLM inference: ~1 second, ~500 tokens output.
One A100 GPU: ~50 inferences/sec (batch inference, optimized model)
Need: 2,000 / 50 = 40 GPUs minimum.
With headroom + redundancy: 60-80 GPUs.

At ~$2/GPU-hour (cloud), that's $120-160/hour = ~$1M-1.4M/year just for inference.
This is why efficient RAG (good retrieval = fewer tokens needed) matters so much.
```

</details>

### Drill 2: "How Would You Scale X?" Rapid Fire

For each, answer in 3 sentences: (1) the bottleneck, (2) the scaling strategy, (3) the key trade-off.

**A) Scale the metadata service from 1M to 100M users**

<details>
<summary>Reference</summary>

**Bottleneck:** Single PostgreSQL instance can't handle the write throughput or store 100TB of metadata.
**Strategy:** Shard by user_id using consistent hashing. Add read replicas per shard for read-heavy workload. Cache hot user sessions in Redis.
**Trade-off:** Cross-user queries (shared folder participants on different shards) now require scatter-gather, which is slower. Mitigate by co-locating shared folder metadata or denormalizing.

</details>

**B) Scale the connector sync system when a hot new app gets 5M users in a week**

<details>
<summary>Reference</summary>

**Bottleneck:** The new connector's initial sync backlog — 5M users each need a full sync, generating billions of documents to index.
**Strategy:** Rate-limit initial syncs (queue with priority tiers). Process in batches. Auto-scale connector workers based on queue depth. Throttle to stay under the external API's rate limit.
**Trade-off:** Users wait longer for their first sync. Mitigate by syncing recent documents first (last 30 days) and backfilling older content asynchronously.

</details>

**C) Scale search indexing when document volume 10x's overnight**

<details>
<summary>Reference</summary>

**Bottleneck:** Index write throughput — embedding generation is GPU-bound, inverted index updates are I/O-bound.
**Strategy:** Kafka absorbs the spike (buffer). Auto-scale GPU workers for embeddings. Batch index writes (100 docs per write operation). Add index shards if individual shards hit their write ceiling.
**Trade-off:** Freshness degrades during the spike — documents take longer to become searchable. Communicate this via freshness badges in the UI.

</details>

**D) Scale WebSocket connections for real-time notifications to 50M concurrent users**

<details>
<summary>Reference</summary>

**Bottleneck:** Each WebSocket is a persistent TCP connection. At 50M connections with typical server capacity of ~100K connections/server: need 500 servers just for connections.
**Strategy:** Dedicated WebSocket gateway fleet (stateless, load-balanced). Route by user_id for cache locality. Use long-polling fallback for clients behind restrictive firewalls. Heartbeat interval: 30s (balance between connection health and server load).
**Trade-off:** Memory per connection (~50KB) × 50M = 2.5 TB of RAM just for connection state. Mitigate by using lightweight connection protocols and offloading message routing to Kafka.

</details>

**E) Scale the AI answer service when latency spikes during peak hours**

<details>
<summary>Reference</summary>

**Bottleneck:** LLM inference is GPU-bound. At peak, GPU utilization hits 100% and requests queue up, spiking latency beyond the 2s target.
**Strategy:** Request-level priority queue (paid users get priority). Adaptive batching (larger batches = higher throughput, higher latency). Token budget limits per query (shorter answers during peak). Auto-scale GPU fleet based on queue depth. Pre-compute answers for popular queries.
**Trade-off:** During extreme peak, show "AI answer generating..." with a delay indicator, or fall back to search-results-only for the lowest-priority tier.

</details>

### Drill 3: Failure Scenario Walkthrough

Walk through each scenario out loud. Explain what happens, what the user sees, and how the system recovers.

**Scenario 1: A database shard goes down**

<details>
<summary>Full walkthrough</summary>

**What happens:**
1. Primary shard crashes (hardware failure, OOM, disk full)
2. All writes for users on that shard fail immediately
3. Read replica detects primary is gone (missed heartbeat after ~10s)

**Automatic recovery:**
4. Read replica promotes to primary (automated failover, ~30s)
5. Remaining replicas re-point to new primary
6. Write path restored

**What users see:**
- Users on that shard: ~30-60 seconds of failed sync operations
- Error: "Sync temporarily unavailable, retrying..."
- Client auto-retries with exponential backoff
- After failover: operations resume, queued changes sync

**What you'd monitor:**
- Replication lag (is the new primary caught up?)
- Error rate spike on that shard
- Automated paging if failover takes > 60s

**What to say in interview:** "For durability, I'd run each shard with a primary and two replicas in different availability zones. Automated failover promotes a replica within 30 seconds. Users see a brief sync pause — the client retries automatically. We lose no data because replicas are synchronously written."

</details>

**Scenario 2: A third-party connector API has a 50% error rate**

<details>
<summary>Full walkthrough</summary>

**What happens:**
1. Gmail API starts returning 500 errors for 50% of requests
2. Circuit breaker monitors: failure rate exceeds threshold (>30% in 1 min)
3. Circuit breaker opens — stops calling Gmail API

**Degraded experience:**
4. New Gmail emails stop being indexed
5. Search still returns existing indexed emails (stale but available)
6. UI shows: "Gmail — last synced 5 minutes ago"

**Recovery:**
7. Circuit breaker enters half-open after timeout (60s)
8. Sends one probe request to Gmail API
9. If success: close circuit, resume syncing, process backlog
10. If failure: re-open circuit, wait again

**What to say in interview:** "Each connector has an independent circuit breaker. When Gmail's API degrades, we stop hammering it (which would make things worse) and serve cached results. The user sees a freshness indicator. When Gmail recovers, we detect it automatically and process the backlog. Other connectors are completely unaffected — fault isolation is critical at this scale."

</details>

**Scenario 3: Search latency spikes from 200ms to 5s**

<details>
<summary>Full walkthrough</summary>

**Investigation:**
1. Check: Is it all queries or specific users? → All users on region US-East
2. Check: Is it lexical, semantic, or reranking? → Semantic search slow
3. Root cause: Vector index shard on that region is doing a merge (compaction), consuming I/O

**Mitigation:**
4. Route US-East semantic queries to US-West (cross-region, ~50ms penalty)
5. Or: Fall back to lexical-only search for affected queries
6. Or: Throttle the merge operation (sacrifice freshness for latency)

**What the user sees (with graceful degradation):**
- Search results still appear (lexical fallback)
- AI answers may be slightly less accurate (less semantic signal)
- Latency: ~500ms instead of ~200ms (acceptable)

**What to say in interview:** "I'd design the search path to fall back to lexical-only results if semantic search exceeds its latency budget. The user gets slightly less accurate results but within the 1s latency target. We'd detect this via p99 latency monitoring and auto-failover. After the merge completes, semantic search resumes automatically."

</details>

---

## 7. How to Talk About Scale You Haven't Experienced

### The Framework: Principles + Numbers + Humility

You don't need to have operated Dropbox to reason about it. You need to:

1. **Start with numbers** — do the math out loud. This proves you can think from first principles.
2. **Name specific technologies** — "I'd use Kafka" not "some message queue." "Consistent hashing" not "some routing."
3. **Explain why** — Every scaling choice has a trade-off. Naming the trade-off is what separates senior from junior.
4. **Acknowledge unknowns** — "At this scale, I'd want to validate that [assumption] holds. I'd run a load test to confirm the per-node throughput before committing to this shard count."

### Phrases That Signal Experience (Use These)

| Phrase | Why It Works |
|--------|-------------|
| "The bottleneck here is..." | Shows you think about constraints, not just features |
| "At this scale, the naive approach breaks because..." | Shows awareness of scale-dependent behavior |
| "I'd shard by [key] because the access pattern is [X]" | Shows you reason from access patterns, not defaults |
| "The trade-off is [X] vs [Y] — I'd choose [X] because [reason]" | Shows you don't think scaling is free |
| "For durability, I'd replicate to [N] availability zones" | Shows operational awareness |
| "I'd monitor [specific metric] to detect [specific failure]" | Shows you've thought about what goes wrong |
| "At 95th percentile, the latency is..." | Shows you think in distributions, not averages |
| "We can tolerate [N seconds] of staleness here because..." | Shows you understand consistency trade-offs |
| "I'd start with [simple] and migrate to [complex] when [trigger]" | Shows pragmatism, not over-engineering |

### Phrases That Signal Inexperience (Avoid These)

| Phrase | Why It's a Red Flag |
|--------|-------------------|
| "Just use a load balancer" | Doesn't explain what's behind it |
| "It should scale fine" | No analysis, no numbers |
| "We'll use the cloud" | Cloud doesn't eliminate scaling problems |
| "Microservices solve this" | Architecture isn't a scaling strategy |
| "Add more RAM" | Vertical scaling has limits |
| "The average latency is 200ms" | p50 hides p99 problems — think in percentiles |
| "We'll figure out scaling later" | Interviewers want to see you think about it now |

---

## 8. Scaling Cheat Sheet (Quick Reference)

Print this and review before your system design round.

### Single-Machine Limits

| Resource | Practical Limit | What Breaks |
|----------|----------------|-------------|
| PostgreSQL rows | ~1B rows per instance | Query performance degrades |
| PostgreSQL storage | ~10 TB comfortable | Backup/restore time |
| Redis memory | ~100 GB per instance | OOM risk |
| Redis throughput | ~100K ops/sec | CPU-bound |
| Kafka partition | ~10K msgs/sec write | Disk I/O |
| Elasticsearch shard | ~50 GB, ~500 QPS | Search latency |
| HTTP connections | ~100K concurrent per server | Memory (50KB each) |
| WebSocket connections | ~100K concurrent per server | Memory + CPU |

### Latency Reference Points

| Operation | Typical Latency |
|-----------|----------------|
| L1 cache | 1 ns |
| L2 cache | 4 ns |
| RAM access | 100 ns |
| SSD read | 100 μs |
| HDD read | 10 ms |
| Same-datacenter network | 0.5 ms |
| Cross-region network (US) | 40 ms |
| Cross-continent network | 100-200 ms |
| Redis GET | 0.5 ms |
| PostgreSQL simple query | 1-5 ms |
| Elasticsearch query | 10-100 ms |
| External API call | 50-500 ms |
| LLM inference (streaming first token) | 200-800 ms |

### SLA/SLO Reference Points

| Service Type | Availability Target | Downtime/Year |
|-------------|--------------------|----|
| Core infrastructure | 99.99% | 52 min |
| User-facing product | 99.9% | 8.7 hrs |
| Internal tools | 99.5% | 1.8 days |
| Batch pipelines | 99% | 3.6 days |

**Dropbox file durability:** 99.999999999% (11 nines). "You're more likely to get struck by lightning than lose a file."
