# 02 – System Design Exercises

Timed system design drills. Each exercise simulates the 40-minute system design round. Practice out loud — talking through your design is as important as the design itself.

---

## How to Use

1. Set a **40-minute timer**
2. Follow the time breakdown for each exercise
3. **Talk out loud** — practice narrating your thought process
4. Draw diagrams (whiteboard, paper, or digital tool)
5. After completing, review the evaluation rubric and self-score
6. Compare against the reference design

---

## Exercise 1: Design a Notification System for Dash

**Time:** 40 min | **Difficulty:** Medium | **Relevance:** Directly applicable to Dash Experiences

### Prompt

Design a notification system for Dropbox Dash. When content changes in any connected app (Gmail, Slack, Google Drive, etc.), users should receive relevant notifications in the Dash interface.

### Requirements to Discover (Ask These)

- How many users? (Millions)
- How many connected apps per user? (Avg 8-10)
- Notification latency target? (Under 30 seconds from source event)
- Do users receive notifications for all changes or only relevant ones?
- How are notifications delivered? (In-app, email digest, push?)
- Can users configure notification preferences?

### Time Breakdown

| Phase | Time | What to Cover |
|-------|------|---------------|
| Requirements | 0-3 min | Ask clarifying questions, state assumptions |
| High-level design | 3-8 min | Draw architecture, identify main components |
| API design | 8-13 min | Define endpoints, data models |
| Deep dive | 13-28 min | Pick 2 components to detail |
| Scaling | 28-35 min | How this handles 10M users |
| Operational | 35-40 min | Failure modes, monitoring |

### API Design Exercise

Design the REST API before looking at the reference:

```
# List notifications for a user
GET /api/v1/notifications?cursor=...&limit=...

# Mark notifications as read
POST /api/v1/notifications/read
Body: { notification_ids: [...] }

# Update notification preferences  
PUT /api/v1/notifications/preferences
Body: { ... }

# What else?
```

### Data Model Exercise

Design the schema:

```sql
-- What tables do you need?
-- What fields in each?
-- What indexes?
-- Think about: notification, user_preferences, delivery_status
```

<details>
<summary><strong>Reference Design</strong></summary>

### Architecture

```
Connected Apps (Gmail, Slack, GDrive...)
    ↓ webhooks / polling
Connector Layer
    ↓ normalized events
Event Router (Kafka)
    ↓
┌─────────────────────┐
│ Notification Engine  │
│  - Relevance scorer  │
│  - Preference filter │
│  - Dedup engine      │
│  - Rate limiter      │
└──────────┬──────────┘
           ↓
    Delivery Service
    ├── In-app (WebSocket push)
    ├── Email digest (batched)
    └── Mobile push (APNs/FCM)
```

### Key Design Decisions

1. **Relevance scoring** — Not every change deserves a notification. Score events by: recency of interaction, user's role (author vs. viewer), event importance (mention vs. edit).

2. **Fan-out strategy** — Write-heavy: when an event arrives, compute notifications for all affected users and write to their notification queues. vs. Read-heavy: store events, compute user's notifications on read. **Best:** Write-time fan-out for high-priority notifications, read-time aggregation for low-priority.

3. **Deduplication** — If a user edits a doc 10 times in 5 minutes, send one notification ("Alice edited Budget.xlsx 10 times") not ten.

4. **Schema:**

```sql
CREATE TABLE notifications (
    id BIGINT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    source_app VARCHAR(50),
    event_type VARCHAR(50),
    title TEXT,
    body TEXT,
    url TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    INDEX idx_user_unread (user_id, is_read, created_at DESC)
);

CREATE TABLE notification_preferences (
    user_id BIGINT,
    source_app VARCHAR(50),
    event_type VARCHAR(50),
    channel VARCHAR(20),  -- 'in_app', 'email', 'push'
    enabled BOOLEAN,
    PRIMARY KEY (user_id, source_app, event_type, channel)
);
```

5. **Scaling:** Shard notifications table by user_id. Each user's notifications are co-located. WebSocket connections load-balanced with sticky sessions.

</details>

### Scaling Deep Dive: Notification System

After completing your initial design, work through these scaling probes. Each one is the kind of follow-up an interviewer will ask if they think you're ready for leveling up.

**Probe 1: "You said you'd shard by user_id. Walk me through what happens when a shared folder with 1,000 users gets updated."**

<details>
<summary>How to answer</summary>

This is a fan-out problem. One event → 1,000 notifications across potentially 1,000 different shards.

```
Event: file updated in shared folder (1,000 members)
  → Notification Engine reads member list (1 DB query)
  → Generates 1,000 notification objects
  → Groups by shard: shard_1 gets 50 notifications, shard_2 gets 47...
  → Batch write to each shard (reduces round trips)
  → Total: ~20 shard writes (at 50 users/shard avg)
```

**Back-of-envelope:**
- If this happens 10K times/day (large org, active folders): 10M notifications/day
- 10M / 86,400 ≈ 115 notifications/sec average
- Peak: ~350/sec
- Each shard can handle ~5K writes/sec → well within capacity

**Key trade-off:** Fan-out on write means the writer is slow (must write to many shards). If fan-out is huge (10K+ users), switch to fan-out on read: store one event, compute per-user notifications when they poll.

</details>

**Probe 2: "10M users are connected. During a peak hour, 5M are online with WebSocket connections. How do you handle that?"**

<details>
<summary>How to answer</summary>

```
5M concurrent WebSocket connections
Each connection: ~50 KB memory
Total memory: 5M × 50 KB = 250 GB

Server capacity: ~100K connections per server
Servers needed: 5M / 100K = 50 WebSocket servers

Notification delivery:
  - Kafka topic partitioned by user_id
  - Each WebSocket server subscribes to its users' partitions
  - When notification arrives in Kafka → route to correct server → push via WebSocket
```

**Architecture:**
```
Kafka (notification events)
  → WebSocket Router (maps user_id → server_id via consistent hashing)
  → WebSocket Server 1 (handles 100K connections)
  → WebSocket Server 2 ...
  → WebSocket Server 50
```

**Failure handling:** If a WebSocket server crashes, its 100K users disconnect. Clients auto-reconnect to a different server (load balancer routes them). They fetch missed notifications via a REST fallback endpoint.

</details>

**Probe 3: "One of your connectors generates 100x more events than expected. What happens?"**

<details>
<summary>How to answer</summary>

**Without protection:** The Kafka topic fills up, notification workers fall behind, users see delayed notifications, and eventually the system OOMs or times out.

**With protection (what you should design):**
1. **Per-connector rate limiting:** Each connector can produce max N events/sec. Excess events are dropped or queued in a backlog.
2. **Backpressure:** If Kafka consumer lag exceeds threshold, the connector sync service slows down (reduces polling frequency).
3. **Priority queues:** High-value notifications (mentions, shared with you) get priority over low-value (someone viewed a doc).
4. **Aggregation under load:** Instead of 100 individual notifications, batch into "Alice made 100 changes to Project X."

**What to say:** "I'd add per-connector rate limiting in the event router. If a connector exceeds its quota, events queue in a secondary buffer. Notification workers process the primary queue first. Under extreme load, we aggregate — '100 updates in Google Drive' instead of 100 individual notifications."

</details>

### Self-Evaluation Rubric

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Requirements clarification (asked good questions) | | |
| Clear high-level architecture | | |
| API design (RESTful, pagination, error handling) | | |
| Data model (schema, indexes, access patterns) | | |
| Depth in at least 2 components | | |
| Scaling strategy articulated with numbers | | |
| Trade-offs discussed explicitly | | |
| Handled scaling probes with back-of-envelope math | | |
| Drove the conversation (didn't wait for prompts) | | |

---

## Exercise 2: Design Dash Stacks (Content Curation)

**Time:** 40 min | **Difficulty:** Medium | **Relevance:** Stacks is a Dash feature — shows product knowledge

### Prompt

Design Dropbox Dash Stacks — a feature where users can curate links, documents, and content from any connected app into organized collections ("stacks"). Stacks can be shared with teammates and have AI-generated summaries.

### Requirements to Discover

- Can stacks contain items from different sources (Gmail, Slack, Drive)?
- Can multiple users collaborate on a stack?
- How does AI summarization work? (On-demand or auto-generated?)
- Real-time collaboration or async?
- Access control model?

### Key Design Challenges

1. **Cross-source item references** — How do you represent an item that lives in Slack vs. one in Google Drive?
2. **Real-time collaboration** — Multiple users adding/reordering items simultaneously
3. **AI summary generation** — When to generate, how to keep fresh, how to handle large stacks
4. **Permission inheritance** — If a stack is shared, does the viewer need access to each source item?

### Exercises Within the Exercise

**A. Design the data model for a Stack:**

```
Think about:
- Stack metadata (title, description, owner, sharing)
- Stack items (order, type, source reference)
- Item content snapshot vs. live reference
- Sharing and permissions
```

**B. Design the API:**

```
Think about:
- CRUD for stacks
- Adding/removing/reordering items
- Sharing a stack
- Requesting an AI summary
```

**C. Sequence diagram — what happens when a user adds a Slack message to a stack:**

```
User clicks "Add to Stack" on a Slack message
    → ??? 
    → Item appears in the stack for all collaborators
```

<details>
<summary><strong>Reference Design</strong></summary>

### Data Model

```python
@dataclass
class Stack:
    id: str
    title: str
    description: str
    owner_id: str
    collaborator_ids: list[str]
    visibility: str  # "private", "team", "public"
    ai_summary: str | None
    summary_generated_at: datetime | None
    created_at: datetime
    updated_at: datetime

@dataclass  
class StackItem:
    id: str
    stack_id: str
    position: float  # fractional indexing for reordering
    source_type: str  # "slack_message", "gdrive_doc", "gmail_email"
    source_id: str    # ID in the source system
    source_url: str   # deep link back to source
    title: str        # cached title/subject
    snippet: str      # cached preview text
    added_by: str
    added_at: datetime
```

### Key Decisions

1. **Fractional indexing for ordering** — Use floats (or strings like "a", "ab", "b") for position. Inserting between items doesn't require renumbering all items.

2. **Cached snapshots** — Store title + snippet at add time. Periodically refresh from source. Shows content even if user loses access to source.

3. **AI summary strategy:**
   - Generated on-demand (user clicks "Summarize")
   - Cached for 1 hour or until stack changes
   - Use RAG: fetch full content of top items → summarize with LLM
   - Mark as stale when items are added/removed

4. **Permission model:** Stack permissions are independent of source permissions. A shared stack shows item titles and snippets to all collaborators, but clicking through to the source requires the viewer's own access.

</details>

### Scaling Deep Dive: Stacks

**Probe 1: "A power user creates a Stack with 10,000 items. What breaks?"**

<details>
<summary>How to answer</summary>

**Frontend:** Rendering 10K items in a list is a performance disaster. Scrolling jank, high memory, long initial load.
- **Fix:** Virtualized list (react-window). Only render ~20 visible items. Cursor-based pagination (load 50 at a time).

**Backend:** Loading 10K StackItem rows + their cached snippets.
- **Fix:** Paginate the API (cursor-based, 50 items/page). Index on `(stack_id, position)` for efficient range queries.

**AI Summary:** Summarizing 10K items is too much context for an LLM.
- **Fix:** Summarize the top-100 most recent/relevant items. Or hierarchical summarization: summarize groups of 50, then summarize the summaries.

**Reordering:** Fractional indexing works but precision degrades after thousands of insertions between the same two items.
- **Fix:** Periodically rebalance positions (renumber 1.0, 2.0, 3.0...) during a background maintenance job.

</details>

**Probe 2: "Stacks goes viral — 10M users, 100M stacks, 1B stack items. Size the storage."**

<details>
<summary>How to answer</summary>

```
Stacks table:
  100M stacks × 500 bytes/stack = 50 GB → fits on one DB shard easily

StackItems table:
  1B items × 1 KB/item (with cached snippet) = 1 TB
  Shard by stack_id (co-locate stack + items)
  At 1 TB per shard: 1-2 shards minimum
  With growth: shard by user_id to co-locate all of a user's stacks

Indexes:
  (stack_id, position): 1B entries × 20 bytes = 20 GB
  (user_id, updated_at): 100M entries × 20 bytes = 2 GB
  
Total: ~1 TB data + ~25 GB indexes → 2-3 DB shards with replication
```

</details>

**Probe 3: "Two users add items to the same Stack simultaneously. What happens?"**

<details>
<summary>How to answer</summary>

**With fractional indexing:** No conflict. User A inserts at position 5.5, User B inserts at position 5.25. Both succeed independently. The order may not be what either user intended, but no data is lost.

**Notification flow:** After each insert, broadcast to all collaborators via WebSocket: "Item added by [user] at position [X]." Client re-fetches the stack or applies an optimistic update.

**Edge case:** Both users reorder the same item simultaneously. User A moves item to position 3.5, User B moves it to position 7.5. Last-write-wins — the item ends up wherever the second write placed it. Acceptable for Stacks (not a real-time collaborative editor).

**If you need stronger guarantees:** Optimistic concurrency control. Each mutation includes a version number. If the version has changed since the client last read, reject and ask the client to re-fetch.

</details>

---

## Exercise 3: Design a Connector Health Dashboard

**Time:** 40 min | **Difficulty:** Medium-Hard | **Relevance:** Operational infrastructure for Dash

### Prompt

Design an internal monitoring dashboard that tracks the health of all 60+ Dash connectors. Engineers need to see sync status, error rates, latency, and data freshness for each connector in real time.

### Key Components to Design

1. **Health data collection** — How do connectors report their status?
2. **Aggregation pipeline** — How do you compute metrics from millions of sync operations?
3. **Alerting** — When should an engineer be paged?
4. **Dashboard API** — What data does the frontend need?

### Design Prompts

**A. Define the health metrics:**

```
For each connector, what metrics matter?
- Sync success rate (last 1h, 24h)
- Average sync latency
- Error breakdown by type
- Data freshness (time since last successful sync)
- Active users affected
- API quota utilization
- What else?
```

**B. Design the time-series data pipeline:**

```
Connector emits metrics
    → ???
    → Dashboard shows real-time charts
```

**C. Define alerting rules:**

```
When should PagerDuty fire?
- Error rate > X% for Y minutes?
- No successful sync in Z minutes?
- API quota > 90%?
- What severity levels?
```

<details>
<summary><strong>Reference Design</strong></summary>

### Architecture

```
Connectors
    ↓ emit structured metrics (OpenTelemetry)
Metrics Collector (Prometheus / Datadog agent)
    ↓
Time-Series DB (Prometheus / InfluxDB)
    ↓
┌──────────────────────────┐
│ Aggregation Service       │
│  - Per-connector rollups  │
│  - Anomaly detection      │
│  - SLO tracking           │
└──────────┬───────────────┘
           ↓
    ┌──────┴──────┐
    ↓             ↓
Dashboard API   Alert Manager
    ↓             ↓
React Dashboard  PagerDuty/Slack
```

### SLO Definitions

| Connector Tier | Availability SLO | Freshness SLO | Alert Threshold |
|---------------|-----------------|---------------|-----------------|
| Tier 1 (Gmail, Slack, GDrive) | 99.9% | < 5 min | 3 failures in 5 min |
| Tier 2 (Jira, Confluence) | 99.5% | < 15 min | 5 failures in 10 min |
| Tier 3 (niche apps) | 99% | < 30 min | 10 failures in 30 min |

### Key Design Decisions

1. **Push vs. pull metrics** — Pull (Prometheus-style) for standard metrics. Push for event-driven metrics (sync completion, errors).

2. **Cardinality management** — Don't create a time series per user per connector. Aggregate at connector level with percentiles.

3. **Anomaly detection** — Compare current error rate against 7-day rolling baseline. Alert on 3-sigma deviations, not just static thresholds.

</details>

### Scaling Deep Dive: Health Dashboard

**Probe 1: "60 connectors × 10M users × 1 metric per sync. How do you store this time-series data?"**

<details>
<summary>How to answer</summary>

```
Sync frequency: avg every 5 min per connector per user
Metrics per sync: ~10 (latency, status, bytes, etc.)

Volume: 10M users × 10 connectors × 12 syncs/hr × 10 metrics = 12B data points/hour
That's 3.3M data points/second.

Per data point: timestamp (8 bytes) + value (8 bytes) + labels (32 bytes) = ~48 bytes
Storage per hour: 12B × 48 bytes = 576 GB/hour (raw)
Per day: ~14 TB (raw)
```

**This is too much raw data.** You need aggregation:

1. **Raw metrics:** Keep for 1 hour (recent debugging)
2. **1-minute rollups:** Keep for 24 hours (detailed investigation)
3. **5-minute rollups:** Keep for 7 days (trend analysis)
4. **1-hour rollups:** Keep for 90 days (historical)

After rollup: ~14 TB/day → ~500 GB/day (1-min) → ~100 GB/day (5-min) → ~12 GB/day (1-hr)

**Technology:** Prometheus (or VictoriaMetrics for better scale) for real-time. Downsample to ClickHouse or Druid for historical analytics.

**Key insight:** Don't store per-user metrics in the dashboard. Aggregate at the connector level. Only drill down to per-user when debugging a specific issue.

</details>

**Probe 2: "How do you avoid alert fatigue?"**

<details>
<summary>How to answer</summary>

**Problem:** 60 connectors × multiple alert rules = hundreds of potential alerts. Engineers start ignoring them all.

**Solution layers:**
1. **Tiered severity:** Only page for Tier 1 connectors (Gmail, Slack, GDrive). Email for Tier 2. Dashboard-only for Tier 3.
2. **Alert grouping:** If Gmail is down, don't fire 10 separate alerts for Gmail-related metrics. Group by root cause.
3. **Anomaly-based, not threshold-based:** Don't alert at "error rate > 5%." Alert at "error rate is 3 standard deviations above the 7-day baseline." This adapts to connectors with naturally different error rates.
4. **Auto-resolve:** If the condition clears within 5 minutes, auto-close the alert (don't wake anyone up for a blip).
5. **Runbooks:** Every alert links to a runbook. If there's no runbook, the alert isn't actionable and shouldn't exist.

</details>

---

## Exercise 4: Design Collaborative Document Editing for Dash

**Time:** 40 min | **Difficulty:** Hard | **Relevance:** Shows depth in real-time systems

### Prompt

Design a lightweight collaborative notes feature within Dash Stacks. Multiple users can edit a shared note simultaneously with real-time cursor tracking and conflict resolution.

### Focus Areas

This exercise tests your knowledge of:
- Real-time collaboration protocols (OT vs. CRDT)
- WebSocket architecture at scale
- Conflict resolution strategies
- Operational complexity

### Guided Design Steps

**Step 1 (5 min):** Define the collaboration model. What operations can users perform? (Insert, delete, format, cursor movement)

**Step 2 (10 min):** Choose between OT and CRDT. Justify your choice.

| | OT | CRDT |
|-|----|----|
| Complexity | Server-side transform logic | Client-side merge logic |
| Server dependency | Requires central server | Can work peer-to-peer |
| Performance | Proven at scale (Google Docs) | Newer, growing adoption |
| Consistency | Strong (server is authority) | Eventual |

**Step 3 (10 min):** Design the WebSocket infrastructure.

```
How do you:
- Handle thousands of concurrent editing sessions?
- Route all users in a session to the same server?
- Handle server failover mid-session?
- Buffer operations during network blips?
```

**Step 4 (10 min):** Design the persistence layer. How do you store document state? How do you handle versioning?

**Step 5 (5 min):** Discuss operational concerns — what monitoring do you need? What failure modes exist?

<details>
<summary><strong>Key Discussion Points</strong></summary>

1. **OT is the pragmatic choice** for a server-based system. Google Docs uses OT. The server maintains a canonical document state and transforms concurrent operations.

2. **Session routing:** Use consistent hashing to route all WebSocket connections for a document to the same server. If that server fails, elect a new one and replay operations from the log.

3. **Operation log:** Store every operation in an append-only log (Kafka). Current document state = initial state + replay all operations. Periodically snapshot the state to avoid replaying the full history.

4. **Cursor tracking:** Broadcast cursor positions via WebSocket at a throttled rate (10 updates/sec). Cursors are ephemeral — no persistence needed.

</details>

### Scaling Deep Dive: Collaborative Editing

**Probe 1: "1,000 users simultaneously editing the same document. What's the bottleneck?"**

<details>
<summary>How to answer</summary>

**Bottleneck: The single server handling OT transforms for this document.**

With OT, all operations for a document must be serialized through one server (the authority). At 1,000 users, each typing ~2 characters/sec = 2,000 operations/sec to one server.

```
OT transform cost: ~O(N) per operation where N = concurrent ops in flight
At 2K ops/sec with ~10 in-flight: each transform touches ~10 other ops
CPU time: ~50μs per transform × 2K = ~100ms/sec → manageable for one core

Actual bottleneck: broadcasting transforms to 1,000 WebSocket connections
1,000 clients × 2K ops/sec × 100 bytes/op = 200 MB/sec outbound bandwidth
```

**Mitigation strategies:**
1. **Operation batching:** Batch ops over 50ms windows. Send 100 ops as one batch.
2. **Operational compression:** "Insert a, Insert b, Insert c" → "Insert abc"
3. **Region-based sharding:** Split document into sections, each handled by a different server. Users in different sections don't conflict.
4. **Practical limit:** Google Docs caps at ~100 simultaneous editors. Beyond that, switch to a different collaboration model (comments, suggestions, not real-time editing).

</details>

**Probe 2: "The OT server for a popular document crashes mid-session. What happens?"**

<details>
<summary>How to answer</summary>

**Without preparation:** All 1,000 users lose their session. Unsaved operations are lost. Reconnecting may create conflicts with the last-persisted state.

**With proper design:**
1. **Operation log (Kafka):** Every operation is persisted to Kafka before being applied. The log is the source of truth, not the server's memory.
2. **Periodic snapshots:** Every 30 seconds, snapshot the document state to the DB. On recovery, replay operations since the last snapshot.
3. **Failover:** A standby server subscribes to the same Kafka partition. On primary crash, it takes over, replays uncommitted ops from Kafka, and resumes.
4. **Client-side buffering:** Clients queue unsent operations locally. On reconnect, they send the buffer. The server deduplicates (each op has a unique ID).

**Recovery timeline:**
- Crash detection: ~5s (heartbeat timeout)
- Standby promotion: ~5s
- Operation replay: ~2s (replay from last snapshot)
- **Total downtime: ~12 seconds.** Users see a brief "Reconnecting..." indicator, then resume editing.

</details>

---

## Exercise 5: Quick-Fire Design Questions (5 min each)

Practice giving concise, structured answers to these rapid-fire design questions. Time yourself — **5 minutes max per question**.

### Q1: How would you add offline support to Dash search?

```
Think about:
- What data to cache locally?
- How to sync when back online?
- What features work offline vs. degrade?
```

<details>
<summary><strong>Reference Answer</strong></summary>

Cache the user's recent search history, frequently accessed documents, and their metadata locally (IndexedDB for web, SQLite for desktop). Build a local inverted index over cached documents. Offline search hits the local index — results are limited but functional. Queue any new searches. On reconnect, sync the local cache with the server and replay queued queries. AI answers require network — show "offline" badge and skip AI generation.

</details>

### Q2: How would you implement "People Search" in Dash?

```
Think about:
- Where does people data come from?
- What signals determine who's relevant?
- How do you rank people results?
```

<details>
<summary><strong>Reference Answer</strong></summary>

Aggregate people data from all connected apps: email contacts (Gmail), channel members (Slack), document collaborators (Drive), ticket assignees (Jira). Build a people index with: name, email, role, department, profile photo, interaction frequency. Rank by: direct interaction recency, shared team/project, org proximity, meeting frequency. Show a people card with their recent activity across connected apps. Privacy: only show information the querying user could see in the source apps.

</details>

### Q3: Design the "Continue where you left off" feature

```
Think about:
- What state needs to be tracked?
- Cross-device continuity
- Privacy implications
```

<details>
<summary><strong>Reference Answer</strong></summary>

Track user activity events: document opens, search queries, stack views, with timestamps and device IDs. Store in a user activity service (sharded by user_id). On app open, query the activity service for the user's last N actions. Surface the most recent documents and searches as a "Recent" section. Cross-device: sync activity via the backend, not device-to-device. Privacy: activity data is per-user, never shared. Users can clear history. Retention: 30 days, then archive.

</details>

### Q4: How would you A/B test a new search ranking algorithm?

```
Think about:
- How to split traffic?
- What metrics to measure?
- How long to run the experiment?
- How to avoid contamination?
```

<details>
<summary><strong>Reference Answer</strong></summary>

Split users (not queries) into control and treatment groups — user-level assignment prevents cross-contamination. Use a feature flag service (LaunchDarkly-style). Metrics: NDCG@10, click-through rate, time-to-click, reformulation rate, session success rate. Run for at least 2 weeks to capture weekly patterns. Statistical significance: p < 0.05 with Bonferroni correction for multiple metrics. Guard rails: if any quality metric drops > 5%, auto-kill the experiment. Log all ranking features for offline analysis.

</details>

### Q5: Design a rate limiting strategy for Dash's API

```
Think about:
- Per-user vs. per-API-key vs. global?
- Algorithm choice?
- Distributed implementation?
```

<details>
<summary><strong>Reference Answer</strong></summary>

Three tiers: global (protect infrastructure), per-API-key (fair usage), per-user (prevent abuse). Algorithm: token bucket for its burst-friendliness. Implementation: Redis with atomic Lua scripts for distributed rate limiting. Each request: `MULTI → GET counter → INCR → EXPIRE → EXEC`. Return `429 Too Many Requests` with `Retry-After` header. Different limits for search (60/min), AI answers (20/min), connector sync (5/min). Premium tiers get higher limits.

</details>

---

## Exercise 6: Scaling-Focused Quick-Fire (5 min each)

These questions specifically target scaling reasoning. Practice doing back-of-envelope math out loud.

### Q6: "We need to add a new search index for images (OCR + visual search). How does this change the scaling picture?"

<details>
<summary>Reference Answer</summary>

**New load:** Each image needs OCR processing (~2s per image, CPU-heavy) and a visual embedding (~500ms, GPU-heavy).

```
10M users × 5K images/user = 50B images total (one-time backfill)
New images: 10M users × 5 images/day = 50M images/day = ~580/sec

OCR pipeline: 580 images/sec × 2s = 1,160 concurrent OCR jobs
At 4 jobs/core: ~290 CPU cores for OCR

Visual embedding: 580/sec × 0.5s = 290 concurrent GPU tasks
At 50 tasks/GPU: ~6 GPUs for embedding

Index growth: 50B images × 3KB/image (embedding + metadata) = 150 TB additional index
Adds ~150 shards to the search cluster
```

**Architecture change:** Separate image processing pipeline (CPU+GPU workers) → Kafka → image index shards. Query path fans out to text index + image index, merges results.

**Trade-off:** Images are expensive to process. Prioritize: index images from recent/frequently accessed documents first. Backfill historical images as a background job over weeks.

</details>

### Q7: "Dash needs to work in 10 new countries. What scaling challenges arise?"

<details>
<summary>Reference Answer</summary>

**Data residency:** EU (GDPR), Brazil (LGPD), India require data to stay in-region. Can't shard a German user's data to a US cluster.

**Architecture change:** Per-region search clusters. Each cluster stores only that region's user data. No cross-region queries.

```
Regions: US, EU, APAC, Brazil, India (5 regions)
Per-region cluster: duplicate the full search stack
Infrastructure multiplier: ~5x more servers, ~5x more operational complexity
```

**Latency:** Users in Sydney querying a US cluster = 200ms network RTT added. With a local cluster: <5ms.

**Connector challenge:** Connector APIs may be US-hosted. Syncing data from US-based Gmail API to an India cluster adds latency. Solution: Connector workers run in each region, pulling from the same external APIs but writing to local clusters.

**What to say:** "Geographic expansion is primarily a data residency problem. I'd deploy per-region clusters, shard users by region at signup, and ensure no user data crosses regional boundaries. The trade-off is operational complexity — 5 regions means 5 independent stacks to monitor, update, and scale."

</details>

### Q8: "Your search index is 2 PB. A new ranking model requires reindexing everything. How?"

<details>
<summary>Reference Answer</summary>

**Naive approach:** Reindex in place. Problem: takes days, and the index is degraded during reindexing (partially old model, partially new).

**Blue-green reindexing:**
1. Build a new index cluster alongside the existing one
2. Reindex all 2 PB into the new cluster (background job, days/weeks)
3. When complete, validate: run both clusters, compare results (shadow traffic)
4. Switch traffic to new cluster (DNS or load balancer change)
5. Keep old cluster as rollback for 48 hours
6. Decommission old cluster

```
Resources needed:
  New cluster: same size as existing (~2,000 shards, ~18 nodes)
  Reindexing throughput: 2 PB / 7 days = ~285 TB/day = ~3.3 GB/sec
  Workers: at 10 MB/sec per worker = ~330 workers
  
  Cost: doubling the cluster for ~2 weeks = significant but time-bounded
```

**Trade-off:** Temporarily double infrastructure cost. But zero downtime and instant rollback if the new model is worse. Worth it.

</details>

### Q9: "Peak traffic is 5x normal during a product launch. How do you prepare?"

<details>
<summary>Reference Answer</summary>

**Pre-launch (weeks before):**
1. Load test at 5x current peak. Identify which component fails first.
2. Pre-scale: add capacity for every component that can't auto-scale fast enough (DB replicas, search shards, GPU fleet for AI answers)
3. Set up kill switches: ability to disable AI answers, reduce search depth, serve cached results — shed load gracefully

**During launch:**
1. Auto-scaling for stateless services (API servers, WebSocket servers, workers)
2. Priority queues: existing users get priority over new signups for resource-intensive operations
3. Rate limiting: per-user and global circuit breakers engaged
4. War room: engineers monitoring dashboards, ready to flip kill switches

```
Normal peak: 2K search QPS, 2K AI answer/sec
Launch peak: 10K search QPS, 10K AI answer/sec

Search: auto-scale from 18 → 50 Elasticsearch nodes (takes ~10 min)
AI: GPU auto-scale from 60 → 200 GPUs (takes ~5 min with warm pool)
Cache: pre-warm with popular queries from analytics
```

**What to say:** "I'd treat a product launch like a controlled stress test. Pre-scale what I can, auto-scale what I can't predict, and have graceful degradation for everything else. The worst outcome isn't high latency — it's a complete outage that makes the news."

</details>

### Q10: "A single user has 500K documents. Queries for this user take 10 seconds. Fix it."

<details>
<summary>Reference Answer</summary>

**Root cause:** This user's shard is much larger than average (50K docs). Their sub-index is 10x normal size, so every query scans 10x more data.

**Short-term fixes:**
1. **Query-time optimization:** Add a "boost recent" heuristic — search the last 30 days first. If results are good enough, skip older docs.
2. **Index partitioning within the shard:** Split this user's index into time-based segments (last month, last year, older). Query recent first, expand if needed.
3. **Tiered storage:** Move docs older than 1 year to a cold index (slower but cheaper). Only search cold index if the user explicitly requests it.

**Long-term fix:**
4. **Dynamic shard splitting:** When a user's index exceeds 500 MB, split into 2 sub-shards. Route queries to both, merge results. This caps per-shard scan size.

```
500K docs × 4 KB/doc = 2 GB per-user index
Normal user: 200 MB
This user: 10x → each query scans 10x more data

With time-based partitioning:
  Recent (30 days): ~50K docs → 200 MB (normal speed)
  Older: ~450K docs → 1.8 GB (only searched if needed)
  Result: 80% of queries hit only the fast partition
```

</details>

---

## System Design Presentation Checklist

Use this checklist after each practice session:

- [ ] I clarified requirements before designing (asked 3+ questions)
- [ ] I drew a clear high-level architecture diagram
- [ ] I defined API endpoints with request/response shapes
- [ ] I designed a data model with appropriate indexes
- [ ] I went deep on at least 2 components
- [ ] I discussed scaling explicitly with concrete numbers (sharding, replication, caching)
- [ ] I did back-of-envelope math out loud (QPS, storage, bandwidth)
- [ ] I identified the bottleneck before proposing a solution
- [ ] I named specific technologies (not "some database" or "a queue")
- [ ] I identified trade-offs and justified my choices
- [ ] I mentioned failure modes and graceful degradation
- [ ] I mentioned monitoring and observability
- [ ] I addressed what happens at 10x growth
- [ ] I drove the conversation — didn't wait for prompts
- [ ] I stayed within 40 minutes

---

## Scaling Study Priority

If scaling is your biggest gap, study this module's content in this order:

1. **[06-scaling-at-dropbox-scale.md](./06-scaling-at-dropbox-scale.md)** — Read the full mental models doc. Memorize the numbers in Section 1. Practice the estimation drills in Section 6 until they feel natural.
2. **Exercises 1-4 above** — Do the scaling deep dive probes for each exercise (the "Scaling Deep Dive" sections). Practice answering each probe out loud in under 2 minutes.
3. **Exercise 6 quick-fire** (Q6-Q10) — Do all 5 with a timer. 5 minutes max each.
4. **Re-read Module 04** ([File Sync](../04-system-design/01-file-sync-and-storage.md) and [Search Infrastructure](../04-system-design/02-search-infrastructure.md)) — Focus specifically on the Scaling sections.
5. **Practice the estimation framework** from 06-scaling-at-dropbox-scale.md Section 3 on novel problems (e.g., "size a video transcoding pipeline", "how many Redis nodes for session storage").
