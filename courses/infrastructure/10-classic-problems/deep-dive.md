# Module 10: Classic System Design Problems — Deep Dive

## Overview

Three additional system design problems at higher complexity, covering distributed coordination, specialized data structures, and multi-pipeline architectures.

---

## Problem 1: Distributed Task Scheduler

### Requirements

**Functional:**
- Schedule tasks for one-time or recurring execution (cron-like).
- Support priority queues (critical tasks run before low-priority ones).
- Exactly-once execution guarantee (a task must not run twice, must not be skipped).
- Failure recovery (retry failed tasks with backoff).
- Task dependencies (task B runs after task A completes).
- Multi-datacenter support (tasks execute in the correct region).

**Non-Functional:**
- Scale: 10M scheduled tasks, 100K executions/day.
- Latency: tasks execute within 1 second of their scheduled time.
- Durability: scheduled tasks survive node failures.
- Observability: full execution history, latency metrics, failure tracking.

### High-Level Design

```
Task Submission:
  Client -> API -> Task Store (PostgreSQL / DynamoDB)

Task Execution:
  Scheduler (polls for due tasks) -> Task Queue (SQS / Redis Streams)
  Workers (consume from queue) -> Execute task -> Report status

Cron Engine:
  Cron Service (evaluates cron expressions) -> Creates task instances at scheduled times
```

### Deep Dive: Exactly-Once Execution

The hardest problem. In a distributed system, "exactly once" requires careful coordination.

**Approach 1: Database-Level Locking**

When a scheduler node picks up a due task, it claims it with an atomic update:

```sql
UPDATE tasks
SET status = 'claimed', claimed_by = 'scheduler-3', claimed_at = NOW()
WHERE id = 'task_123'
  AND status = 'pending'
  AND scheduled_at <= NOW();
-- Returns affected_rows = 1 if claimed, 0 if already claimed by another node
```

Only one scheduler node can successfully claim the task. The database enforces mutual exclusion.

**Approach 2: Distributed Locking with Redis.** Use `SET lock_key scheduler_id NX EX 300` (set-if-not-exists with 5-min TTL). Only one scheduler acquires the lock; others skip the task.

**Approach 3: Idempotent Execution.** Design task handlers to be idempotent — even if a task runs twice, the second execution produces no side effects. Use idempotency keys with external services (e.g., payment gateway deduplicates by idempotency key).

**Recommendation:** Combine all three approaches for defense in depth.

### Deep Dive: Priority Queues

Not all tasks are equal. A critical alert notification must execute before a low-priority report generation.

```
Queue structure:
  high_priority_queue   -> Workers (dedicated pool, 70% capacity)
  normal_priority_queue -> Workers (shared pool, 25% capacity)
  low_priority_queue    -> Workers (shared pool, 5% capacity)
```

Alternatively, use a single queue with priority scoring. Redis Sorted Sets work well:

```python
# Enqueue with priority score (lower = higher priority)
redis.zadd("task_queue", {task_id: priority_score})

# Dequeue highest priority task
task_id = redis.zpopmin("task_queue")
```

### Deep Dive: Cron-Like Scheduling

A cron engine evaluates cron expressions every minute and creates task instances at scheduled times. Deduplication: unique constraint on `(cron_id, scheduled_time)` prevents duplicates even if multiple engine instances are running. Use leader election or let all instances create with database-level dedup.

### Deep Dive: Failure Recovery

State machine: `PENDING -> CLAIMED -> RUNNING -> COMPLETED` or `RUNNING -> FAILED -> RETRY (with exponential backoff) -> CLAIMED` or `FAILED -> DEAD_LETTER (after max retries)`. A sweeper process detects stuck tasks (`WHERE status = 'running' AND started_at < NOW() - INTERVAL '30 minutes'`) and marks them failed for retry.

### Deep Dive: Multi-Datacenter

Tasks may need to execute in a specific region for data locality or compliance. Use regional queues (`task_queue_us_east`, `task_queue_eu_west`) with a router that inspects `task.region` and enqueues to the correct regional queue. Workers consume only from their local queue. The global task store is the source of truth. If a region goes down, tasks re-route to a failover region.

### Architecture Summary

Components: API Layer (submit/cancel/query) + Scheduler (poll due tasks) + Cron Engine (create instances) + Sweeper (detect stuck tasks) -> Task Store (PostgreSQL) -> Priority Queues (Redis/SQS: high, normal, low) -> Worker Pool (execute, report status, retry).

---

## Problem 2: Search Autocomplete

### Requirements

**Functional:**
- As the user types, suggest completions based on prefix matching.
- Rank suggestions by frequency (most popular queries first).
- Support personalization (recent searches, user-specific suggestions).
- Update suggestions in near-real-time as search trends change.
- Return top 10 suggestions within 100ms.

**Non-Functional:**
- Scale: 10B queries/day, 100K unique queries added/day.
- Latency: < 50ms p99 (autocomplete must feel instant).
- Availability: high (degraded autocomplete is acceptable; no autocomplete is not).

### High-Level Design

```
User types "how t" -> Client -> Autocomplete Service -> Trie Store
                                                     -> Personalization Service
                                                     -> Response: ["how to", "how tall", "how the", ...]

Data pipeline (offline):
  Search Logs -> Aggregation (MapReduce/Spark) -> Trie Builder -> Trie Store
```

### Deep Dive: Trie Data Structure

A trie (prefix tree) stores strings where each node represents a character. Traversing from root to a node gives you a prefix.

```
Root
├── h
│   ├── o
│   │   ├── w (freq: 50000)
│   │   │   ├── _ (space)
│   │   │   │   ├── t
│   │   │   │   │   ├── o (freq: 30000) -> "how to"
│   │   │   │   │   └── a
│   │   │   │   │       └── l
│   │   │   │   │           └── l (freq: 5000) -> "how tall"
│   │   │   │   └── a
│   │   │   │       └── r
│   │   │   │           └── e (freq: 8000) -> "how are"
│   │   └── t
│   │       └── e
│   │           └── l (freq: 3000) -> "hotel"
```

**Optimization 1: Store top-K at each node.**

Instead of traversing all descendants to find the most frequent completions, pre-compute and cache the top 10 at each node.

```
Node "how t":
  top_10: ["how to cook", "how to tie", "how tall is", "how to draw", ...]
```

This makes query-time lookups O(prefix_length) instead of O(subtree_size).

**Optimization 2: Compressed trie (Patricia trie).**

Merge single-child chains into a single node. "h-o-t-e-l" becomes a single edge "hotel". Reduces memory by 50-70%.

### Deep Dive: Ranking by Frequency

Frequencies are computed from search logs:

```python
# Aggregation pipeline (runs hourly/daily)
search_logs = read_logs(last_24_hours)
query_counts = search_logs.group_by("query").count()

# Apply time decay: recent queries weighted more heavily
for query, count in query_counts:
    decayed_count = count * decay_factor(query.last_seen)

# Build/update trie with new frequencies
trie.update(query_counts)
```

**Frequency scoring with time decay:**

```
score = sum(count_i * decay^(now - time_i))

where decay = 0.95 (per hour)
```

This naturally demotes stale queries and promotes trending ones.

### Deep Dive: Personalization

Layer personalized results on top of global suggestions. Fetch the user's recent searches matching the prefix, fetch global top-10, merge with user results boosted, deduplicate, and return top 10. User search history is stored in a per-user Redis sorted set or small per-user trie.

### Deep Dive: Real-Time Updates

The global trie cannot be rebuilt on every query. Use a two-tier approach:

**Tier 1: Batch-built trie (rebuilt every few hours).**

Covers the stable, long-term query distribution. Stored in a read-optimized format (memory-mapped file or distributed cache).

**Tier 2: Real-time trending overlay.**

A small data structure that captures trending queries from the last few minutes/hours. Implemented with a streaming counter (Count-Min Sketch or Redis sorted set).

```
Query arrives:
  1. Check trending overlay first (captures breaking events like "earthquake")
  2. Check batch trie (captures stable queries)
  3. Merge results, deduplicate, return top 10
```

### Deep Dive: Distributed Trie

A single-server trie does not scale for 10B queries/day. Options:

**Shard by prefix:** Shard 1 handles a-f, Shard 2 handles g-m, etc. Problem: uneven distribution.

**Replicated trie:** Entire trie replicated across servers. Reads round-robin, writes go to primary.

**Trie as serialized artifact (recommended):** Build the trie offline (search logs -> Spark aggregation -> build trie -> serialize -> upload to S3). Autocomplete servers pull the latest trie file and load into memory. Blue-green deployment: load new trie on standby servers, swap traffic. This read-only artifact approach is how most large-scale systems work.

### Architecture Summary

```
┌───────────────────────────────────────────────────────────────┐
│                   Search Autocomplete System                   │
├───────────────────────────┬───────────────────────────────────┤
│ Online Path               │ Offline Path                      │
│                           │                                   │
│ Client                    │ Search Logs (Kafka)               │
│   |                       │   |                               │
│ Autocomplete API          │ Aggregation (Spark, hourly)       │
│   |                       │   |                               │
│ ┌────────────────────┐    │ Trie Builder                      │
│ │ Personalization    │    │   |                               │
│ │ (user recent       │    │ Serialized Trie -> S3             │
│ │  searches, Redis)  │    │   |                               │
│ └────────────────────┘    │ Deploy to autocomplete servers    │
│   |                       │                                   │
│ ┌────────────────────┐    │ ┌───────────────────────┐         │
│ │ Trending Overlay   │    │ │ Trending Counter      │         │
│ │ (real-time, small) │<───│ │ (streaming, Count-Min │         │
│ └────────────────────┘    │ │  Sketch / Redis)      │         │
│   |                       │ └───────────────────────┘         │
│ Global Trie (in-memory)   │                                   │
│   |                       │                                   │
│ Top-10 Results            │                                   │
└───────────────────────────┴───────────────────────────────────┘
```

---

## Problem 3: Video Streaming Platform

### Requirements

**Functional:**
- Upload videos (up to 10 GB).
- Transcode videos into multiple resolutions and formats.
- Stream video with adaptive bitrate (quality adjusts to network conditions).
- Support live streaming.
- Recommendation feed (personalized).
- Comments, likes, view counts.

**Non-Functional:**
- Scale: 1B video views/day, 100K uploads/day.
- Latency: video playback starts within 2 seconds.
- Availability: 99.99% for playback.
- Storage: petabytes of video content.

### High-Level Design

```
Upload:
  Creator -> Upload Service -> Object Storage (raw) -> Transcoding Pipeline
          -> Metadata Service -> Metadata DB

Playback:
  Viewer -> API -> Metadata Service (get video info + manifest URL)
         -> CDN -> Origin (Object Storage) -> Adaptive bitrate stream

Live Streaming:
  Streamer -> Ingest Server (RTMP) -> Transcoder -> CDN -> Viewers (HLS/DASH)
```

### Deep Dive: Transcoding Pipeline

Raw uploaded video must be transcoded into multiple renditions for different devices and network conditions.

```
Input: raw_video.mp4 (4K, 50 Mbps, H.264)

Output renditions:
  - 2160p (4K):  8000 kbps, H.264
  - 1080p (FHD): 4500 kbps, H.264
  - 720p (HD):   2500 kbps, H.264
  - 480p (SD):   1000 kbps, H.264
  - 360p:         500 kbps, H.264
  - Audio only:   128 kbps, AAC
```

**Pipeline architecture:**

```
Upload Complete Event (SNS/SQS)
  -> Transcoding Orchestrator
     -> Split video into segments (e.g., 4-second chunks)
     -> Distribute segments across transcoding workers (parallel)
     -> Each worker transcodes one segment into all renditions
     -> Reassemble segments into complete renditions
     -> Generate manifest file (HLS .m3u8 or DASH .mpd)
     -> Upload renditions + manifest to object storage
     -> Notify Metadata Service: "video ready for playback"
```

**Parallel transcoding:** A 2-hour video is split into 1,800 four-second segments. Each segment is independently transcoded by a worker using FFmpeg. With 100 workers, the entire video is transcoded in minutes instead of hours.

### Deep Dive: Adaptive Bitrate Streaming (ABR)

ABR adjusts video quality in real-time based on the viewer's network conditions.

**HLS (HTTP Live Streaming) — Apple's protocol:**

```
Master playlist (.m3u8):
  #EXTM3U
  #EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=3840x2160
  2160p/playlist.m3u8
  #EXT-X-STREAM-INF:BANDWIDTH=4500000,RESOLUTION=1920x1080
  1080p/playlist.m3u8
  #EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720
  720p/playlist.m3u8
  #EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=854x480
  480p/playlist.m3u8

Rendition playlist (1080p/playlist.m3u8):
  #EXTM3U
  #EXT-X-TARGETDURATION:4
  #EXTINF:4.0,
  segment_001.ts
  #EXTINF:4.0,
  segment_002.ts
  ...
```

**How ABR works:**

1. Player fetches the master playlist.
2. Based on initial bandwidth estimate, selects a rendition (e.g., 720p).
3. Downloads segments sequentially.
4. After each segment, measures actual download speed.
5. If bandwidth increased, switches up (720p -> 1080p).
6. If bandwidth decreased, switches down (720p -> 480p).
7. Switches happen at segment boundaries (every 4 seconds) — seamless to the viewer.

**DASH (Dynamic Adaptive Streaming over HTTP):** Similar concept, uses XML-based MPD manifests. More flexible than HLS but less universally supported. Many platforms support both.

### Deep Dive: CDN Strategy

Video streaming is CDN-intensive. Strategy:

**Multi-tier CDN:**

```
Tier 1: Edge PoPs (closest to user, caches popular content)
Tier 2: Regional caches (aggregates requests from multiple edge PoPs)
Tier 3: Origin shield (single cache in front of origin, prevents origin overload)
Tier 4: Origin (S3)
```

**Cache strategy:**
- Popular videos (top 10% by views) are pre-warmed at edge PoPs.
- Long-tail videos are cached on demand (first viewer pulls from origin, subsequent viewers hit cache).
- Segments within a video have different popularity — early segments are cached more aggressively (many viewers start but few finish).

**Cost optimization:** Negotiate committed CDN contracts, use multi-CDN for redundancy, and tier storage (hot SSD, warm HDD, cold Glacier) by access frequency.

### Deep Dive: Live Streaming Architecture

Live streaming has fundamentally different requirements than video-on-demand: content must be ingested, transcoded, and delivered in near-real-time.

```
Streamer -> RTMP Ingest Server
         -> Live Transcoder (real-time, multi-rendition)
         -> Segment Packager (creates 2-4 second HLS/DASH segments)
         -> CDN (edge push, ultra-low TTL)
         -> Viewers (player polls for new segments)
```

**Latency tiers:**

| Mode | Latency | Protocol | Use Case |
|------|---------|----------|----------|
| Standard live | 15-30 seconds | HLS/DASH | Broadcast, sports |
| Low-latency live | 3-5 seconds | LL-HLS, LL-DASH | Interactive, gaming |
| Real-time | < 1 second | WebRTC | Video calls, auctions |

**Low-latency HLS (LL-HLS):**
- Uses partial segments (0.5-1 second chunks within a 4-second segment).
- Players fetch partial segments as they are produced.
- Reduces latency from 15-30 seconds to 3-5 seconds.
- Requires CDN support for chunked transfer encoding.

**Scaling live events:** CDN handles scale (each edge PoP pulls one copy from origin, serves thousands locally). Edge servers buffer 2-3 segments. For mega-events, pre-allocate CDN capacity and use multi-CDN.

### Deep Dive: Recommendation Feed

The recommendation system drives engagement. Architecture:

```
User opens app -> Recommendation Service
  -> Candidate generation (retrieve 1000 candidates from multiple sources):
     - Collaborative filtering: "users who watched X also watched Y"
     - Content-based: similar genre, creator, topic
     - Trending: popular in the user's region/demographic
     - History-based: continue watching, rewatch
  -> Ranking model (score 1000 candidates, select top 50):
     - Features: user history, video metadata, engagement signals
     - Model: neural network or gradient-boosted trees
     - Predict: P(click), P(watch > 50%), P(like)
  -> Filtering and business rules:
     - Remove already-watched (unless rewatch-eligible)
     - Apply diversity rules (don't show 10 cooking videos in a row)
     - Enforce content policies (age restrictions, region blocks)
  -> Return ranked list to client
```

**Real-time signals:** The recommendation service incorporates real-time user behavior (what they just watched, what they skipped) to adjust recommendations within a session.

### Architecture Summary

Upload path: Creator -> Upload Service -> Object Storage (raw) -> Transcoding Pipeline -> Object Storage (renditions) + Metadata DB. Playback path: Viewer -> API (metadata + recommendations) -> CDN -> Object Storage. Live path: Streamer -> RTMP Ingest -> Live Transcoder -> Segment Packager -> CDN -> Viewers. Supporting: search, comments, analytics, content moderation, billing.

---

## Cross-Cutting Themes Across All Three Problems

**1. Exactly-once vs. at-least-once:** The task scheduler demands exactly-once semantics. Video transcoding and autocomplete trie building can tolerate at-least-once (idempotent operations). Choose the right guarantee for the problem.

**2. Offline + online architecture:** Both autocomplete and video recommendations use an offline pipeline to build artifacts (tries, ML models) that are served online. This separation of concerns is a recurring pattern.

**3. Parallel processing:** Video transcoding parallelizes across segments. Task scheduling parallelizes across workers. Autocomplete trie building parallelizes across prefixes. Identify the unit of parallelism in any system.

**4. Multi-tier caching:** Video uses multi-tier CDN. Autocomplete uses in-memory trie + trending overlay. Task scheduler uses in-memory queue + persistent store. Every system benefits from hierarchical caching.

**5. Graceful degradation:** If the recommendation model is slow, serve a fallback (trending videos). If autocomplete is slow, show recent searches. If the task scheduler is overloaded, prioritize critical tasks. Always have a degradation plan.
