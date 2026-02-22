# Module 01: System Design Framework

## Overview

System design interviews are not about memorizing architectures. They are about demonstrating structured thinking under ambiguity, making defensible trade-off decisions, and communicating clearly while doing it. This module gives you a repeatable framework that works for any system design problem, from a URL shortener to a global-scale messaging platform.

The difference between a senior engineer and a staff+ engineer in these interviews is not knowledge of more components -- it is the ability to navigate ambiguity, identify the real constraints, and justify decisions in terms of business impact.

---

## The 4-Step Framework

Every system design interview follows roughly the same arc. You have 35-45 minutes. Here is how to spend them:

| Step | Time | What You Do |
|------|------|-------------|
| 1. Requirements & Scope | 5-7 min | Clarify functional and non-functional requirements |
| 2. Back-of-Envelope Estimation | 3-5 min | Quantify the scale to inform design decisions |
| 3. High-Level Design | 10-15 min | API design, data model, architecture diagram |
| 4. Deep Dive | 15-20 min | Pick 2-3 components and go deep on trade-offs |

This is not a rigid script. Some interviewers want to skip estimation. Some want to spend more time on requirements. Read the room. But having this skeleton means you never freeze up wondering what to do next.

---

## Step 1: Requirements & Scope

### Functional Requirements

These are the "what does it do" questions. Your goal is to reduce a vague prompt ("design Twitter") into a concrete, bounded set of features you will actually design.

**How to extract them:**

1. Start with the core use case. "What is the single most important thing this system does?"
2. List 3-5 features, then explicitly confirm scope: "I'll focus on these three for today. Does that sound right?"
3. Identify the actors: Who uses this? End users? Internal services? Both?
4. Identify the data flow: What goes in? What comes out?

**Example -- "Design a notification system":**

- "Let me clarify scope. Are we designing the full notification system -- email, push, SMS -- or focusing on one channel?"
- "Should we handle notification preferences and opt-outs?"
- "Is this for a single application or a platform serving multiple internal teams?"
- "Do we need delivery guarantees? Is it okay if a notification is occasionally dropped, or must every notification be delivered at least once?"

The trap is accepting the problem as stated and diving in. The signal of a strong candidate is narrowing scope strategically -- choosing the most interesting and complex subset.

### Non-Functional Requirements

These are the constraints that determine your architecture. Two systems with identical functional requirements but different non-functional requirements will look completely different.

**The non-functionals you should always consider:**

| Requirement | Question to Ask | Why It Matters |
|-------------|----------------|----------------|
| **Latency** | What is the acceptable p99 latency? | Determines sync vs async, caching strategy, data locality |
| **Availability** | What is the target uptime? 99.9%? 99.99%? | Determines redundancy, failover strategy, blast radius |
| **Consistency** | Can we tolerate stale reads? For how long? | Determines database choice, replication strategy, caching invalidation |
| **Durability** | What happens if we lose data? | Determines backup strategy, replication, write-ahead logging |
| **Throughput** | How many requests per second? Read-heavy or write-heavy? | Determines scaling strategy, database choice, queue usage |
| **Scalability** | 10x growth in 2 years? 100x? | Determines horizontal vs vertical scaling, sharding strategy |
| **Security** | PII? Financial data? Compliance requirements? | Determines encryption, access control, audit logging |
| **Cost** | Startup on a budget or FAANG-scale? | Determines managed vs self-hosted, over-engineering threshold |

**The senior move:** Do not just list these. Identify which 2-3 are in tension and state the trade-off explicitly.

> "This system needs both low latency and strong consistency. Those are in tension -- strong consistency typically adds latency due to synchronous replication. I'd propose tuning for strong consistency on writes and eventual consistency on reads with a short staleness window, say 500ms. Does that align with your expectations?"

### Common Requirement Patterns

Different system types have predictable non-functional profiles:

- **Social feed / timeline:** Read-heavy (100:1 read:write), eventual consistency acceptable, low latency reads critical
- **Payment system:** Write-heavy relative to reads, strong consistency mandatory, durability non-negotiable, audit trail required
- **Real-time chat:** Low latency bidirectional, availability over consistency, connection management is key
- **Analytics pipeline:** Write-heavy ingestion, batch reads acceptable, throughput over latency, eventual consistency fine
- **Search system:** Read-heavy, low latency queries, eventual consistency on index updates acceptable

---

## Step 2: Back-of-Envelope Estimation

The point of estimation is not precision. It is to get order-of-magnitude numbers that inform architectural decisions. Whether you need 1,000 QPS or 10,000 QPS changes your design. Whether you need 1,000 or 1,500 does not.

### QPS from DAU

```
Daily Active Users (DAU) = Total Users x Daily Active Rate

Reads per day = DAU x avg reads per user per day
Writes per day = DAU x avg writes per user per day

Read QPS = Reads per day / 86,400
Write QPS = Writes per day / 86,400

Peak QPS = Average QPS x Peak Multiplier (typically 2x-5x)
```

**Example -- URL Shortener:**
- 100M DAU
- Each user creates 0.1 short URLs per day (most users only read)
- Each user reads 5 short URLs per day

```
Write QPS = (100M x 0.1) / 86,400 = ~115 writes/sec
Peak Write QPS = 115 x 3 = ~350 writes/sec

Read QPS = (100M x 5) / 86,400 = ~5,800 reads/sec
Peak Read QPS = 5,800 x 3 = ~17,400 reads/sec

Read:Write ratio = 50:1 (very read-heavy)
```

This tells us: cache aggressively, optimize for reads, writes are not the bottleneck.

### Storage Estimation

```
Storage per record = size of all fields (estimate each field)
Daily new records = Write QPS x 86,400
Annual storage = Daily new records x 365 x Storage per record
5-year storage = Annual storage x 5
```

**Example -- URL Shortener:**
- Each record: short_url (7 bytes) + long_url (avg 200 bytes) + user_id (8 bytes) + created_at (8 bytes) + metadata (50 bytes) = ~273 bytes, round to 300 bytes
- Daily new records: 10M

```
Annual storage = 10M x 365 x 300 bytes = ~1.1 TB/year
5-year storage = ~5.5 TB
```

This tells us: a single database server can handle this storage-wise. No need for sharding based on storage alone.

### Bandwidth Estimation

```
Incoming bandwidth = Write QPS x Average request size
Outgoing bandwidth = Read QPS x Average response size
```

**Example -- URL Shortener:**
```
Incoming = 115 x 300 bytes = ~35 KB/s (negligible)
Outgoing = 5,800 x 300 bytes = ~1.7 MB/s (negligible)
```

### Memory for Caching

The 80/20 rule: 20% of data serves 80% of traffic. Cache the hot set.

```
Daily read requests = Read QPS x 86,400
Cache size = Daily read requests x 0.2 x Average response size
```

**Example -- URL Shortener:**
```
Daily reads = 5,800 x 86,400 = ~500M
Unique URLs accessed per day = ~100M (assuming repetition)
Cache 20% = 20M URLs x 300 bytes = ~6 GB
```

6 GB fits comfortably in a single Redis instance (typical max is 25-50 GB usable).

### Number of Servers

```
Servers needed = Peak QPS / QPS per server
```

A typical web server handles 1,000-10,000 QPS depending on the work per request. For simple lookups (URL redirect), assume 5,000-10,000. For complex operations (social feed assembly), assume 500-1,000.

```
URL Shortener: 17,400 peak read QPS / 10,000 per server = 2 servers (plus redundancy = 4-6)
```

### When to Skip Estimation

If the interviewer signals they want to move on, or if the numbers are obviously manageable (e.g., designing an internal tool for 1,000 employees), skip the math and state your assumptions: "This is low scale -- single server territory. I'll design for correctness first and note where we'd need to scale."

---

## Step 3: High-Level Design

### API Design First

Start with the API because it forces you to think about the contract between client and server before you think about implementation. This is also what the interviewer can most easily follow on a whiteboard.

**REST example for URL Shortener:**

```
POST /api/v1/urls
  Request:  { "long_url": "https://example.com/very/long/path", "custom_alias": "my-link" (optional) }
  Response: { "short_url": "https://short.ly/abc1234", "expires_at": "2026-02-22T..." }
  Status:   201 Created

GET /api/v1/urls/{short_code}
  Response: 301 Redirect to long_url
  (or 302 if you want analytics -- 301 is cached by browsers)

GET /api/v1/urls/{short_code}/stats
  Response: { "clicks": 12345, "created_at": "...", "top_referrers": [...] }

DELETE /api/v1/urls/{short_code}
  Response: 204 No Content
```

**What to call out:**
- Versioning strategy (path-based `/v1/` vs header-based)
- Authentication (API key? OAuth? Which endpoints need auth?)
- Rate limiting (per user? per IP? What limits?)
- Idempotency (what happens if POST is retried? Use idempotency keys for writes)
- Pagination (cursor-based vs offset-based for list endpoints)

### Data Model

After the API, design the data model. This grounds the discussion in something concrete.

```sql
-- URL Shortener
CREATE TABLE urls (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    short_code  VARCHAR(7) UNIQUE NOT NULL,
    long_url    TEXT NOT NULL,
    user_id     BIGINT,
    created_at  TIMESTAMP DEFAULT NOW(),
    expires_at  TIMESTAMP,
    click_count BIGINT DEFAULT 0
);

CREATE INDEX idx_short_code ON urls(short_code);
CREATE INDEX idx_user_id ON urls(user_id);
```

**What to call out:**
- Primary key strategy (auto-increment vs UUID vs snowflake ID)
- Index choices and why
- Denormalization decisions (click_count on the URL table vs a separate analytics table)
- Data types (VARCHAR length, BIGINT vs INT)

### Architecture Diagram

Draw the standard components and data flow:

```
Client -> Load Balancer -> Web Servers -> Cache (Redis) -> Database (PostgreSQL)
                                      -> Analytics Queue (Kafka) -> Analytics DB
```

Keep it simple at this stage. You will add complexity in the deep dive. The goal is a shared mental model that you and the interviewer can point to.

**Standard building blocks:**
- Load balancer (L4 vs L7, when each matters)
- Web/application servers (stateless, horizontally scalable)
- Cache layer (read-through, write-through, write-behind, cache-aside)
- Primary database (SQL or NoSQL, with rationale)
- Message queue (for async processing, decoupling)
- CDN (for static content, edge caching)
- Object storage (S3 for blobs, media)
- Search index (Elasticsearch for full-text search)

---

## Step 4: Deep Dive

This is where you differentiate yourself. The interviewer will either ask you to go deep on something specific, or you should proactively pick the most interesting 2-3 components.

### How to Pick What to Deep Dive On

1. **What is the hardest part of this system?** For a URL shortener, it is the short code generation (uniqueness at scale). For a chat system, it is the real-time message delivery. For a newsfeed, it is the fan-out strategy.

2. **What did your estimation reveal?** If you calculated a 50:1 read:write ratio, the caching strategy is worth a deep dive. If you identified 100K write QPS, the database write path deserves attention.

3. **What aligns with your expertise?** If you have deep experience with a particular component, steer toward it. You will be more articulate and the conversation will be richer.

### Common Deep Dives

**Database Choice:**
- Why SQL vs NoSQL for this specific use case
- Sharding strategy if needed (shard key selection, cross-shard queries)
- Replication topology (leader-follower, read replicas)
- Index design for the query patterns identified

**Caching Layer:**
- Cache-aside vs read-through vs write-through
- Cache invalidation strategy (TTL, event-driven, versioning)
- Cache stampede prevention (lock/lease, probabilistic early expiration)
- What to cache (query results, computed values, session data)
- Hot key problem and mitigation

**Message Queue / Async Processing:**
- Why async here (decouple, buffer, retry)
- Ordering guarantees needed?
- At-least-once vs exactly-once semantics
- Dead letter queues for failed messages
- Consumer group design

**Rate Limiting:**
- Token bucket vs sliding window vs fixed window
- Where to rate limit (API gateway, application, per-service)
- Rate limit by what key (user, IP, API key)

**Unique ID Generation:**
- Auto-increment (simple, but doesn't work across shards)
- UUID v4 (random, but poor index locality, 128 bits)
- Snowflake ID (timestamp + worker + sequence, 64 bits, sortable)
- Hash-based (MD5/SHA256 of content, deterministic but collision risk)
- Pre-generated ID pool (generate IDs in advance, hand them out)

### Deep Dive Template

For each component you go deep on, cover:

1. **Requirements for this component** (what does it need to do?)
2. **Options considered** (at least 2 alternatives)
3. **Trade-offs between options** (this is the money)
4. **Decision and rationale** (pick one and justify)
5. **Failure modes** (what happens when this component fails?)
6. **Scaling path** (how does this evolve as traffic grows 10x, 100x?)

---

## Communication Strategies

### Top-Down Decomposition

Always go from big picture to details, never the reverse. The interviewer should be able to stop you at any point and have a coherent (if incomplete) design.

```
Level 0: "This is a read-heavy URL shortening service. Key challenges are unique ID generation and low-latency redirects."
Level 1: "The system has three main flows: create short URL, redirect, and analytics."
Level 2: "For the redirect flow: client hits CDN/cache first, then app server, then database as fallback."
Level 3: "The cache layer uses Redis with cache-aside pattern, TTL of 24 hours, and..."
```

### Whiteboarding Tips

- **Draw boxes and arrows, not code.** The diagram is a communication tool, not a spec.
- **Label everything.** Do not draw a box without writing what it is.
- **Show data flow direction.** Arrows should indicate direction of data movement.
- **Use color or numbering** to distinguish different flows (write path vs read path).
- **Leave space.** You will add components during the deep dive. Do not cram everything in from the start.

### Pacing

- **Check in every 5-7 minutes.** "Does this make sense so far? Should I go deeper here or move on?"
- **Watch for signals.** If the interviewer is nodding and looking at the clock, move faster. If they are leaning in with questions, slow down and go deeper.
- **Do not monologue.** The best system design interviews feel like a collaborative design session, not a presentation.

### When to Ask vs When to Assume

**Ask when:**
- The scope is genuinely ambiguous ("Should this support real-time or is near-real-time okay?")
- The answer significantly changes the design ("Are we optimizing for consistency or availability?")
- You want to show you know the question matters ("Should we design for multi-region from day one or plan for it later?")

**Assume when:**
- The choice is a reasonable default ("I'll assume we need 99.9% availability unless you want higher")
- Both options are valid and you can justify yours ("I'll go with PostgreSQL here because of the relational nature of the data -- happy to discuss NoSQL alternatives if you prefer")
- Asking would waste time ("I'll assume standard HTTPS for transport security")

State your assumptions explicitly: "I'm going to assume X. Let me know if you'd like me to go a different direction."

---

## Common Pitfalls

### 1. Jumping to Solution

**The mistake:** "Design a chat system." "Okay, so we'll use WebSockets with Redis Pub/Sub and Cassandra for storage..."

**The fix:** Spend 5-7 minutes on requirements. The interviewer does not want to see that you know WebSockets exist. They want to see that you can figure out *why* WebSockets are the right choice for this specific problem.

### 2. Over-Engineering

**The mistake:** Designing a globally distributed, multi-region, sharded, event-sourced architecture for a system that serves 1,000 users.

**The fix:** Let the numbers guide the complexity. If estimation shows 100 QPS, a single server with a managed database is the right answer. Call out where you would add complexity as scale grows: "At this scale, a single PostgreSQL instance is fine. If we grow to 10K QPS, I'd add read replicas. At 100K, we'd consider sharding."

### 3. Ignoring Non-Functionals

**The mistake:** Designing a beautiful architecture without ever discussing latency, availability, or consistency guarantees.

**The fix:** State your non-functional requirements up front and reference them during design decisions. "We said p99 latency under 200ms. That's why I'm putting a cache here -- database round-trips average 5-10ms, but tail latency spikes to 200ms+ under load."

### 4. Not Discussing Trade-Offs

**The mistake:** Presenting every decision as the obvious correct choice without acknowledging alternatives.

**The fix:** For every significant decision, briefly mention what you are *not* choosing and why. "I'm going with a SQL database here because of the relational nature of user-to-URL mappings. A NoSQL option like DynamoDB would give us better horizontal scalability, but we don't need it at this scale, and joins simplify the analytics queries."

### 5. Treating It as a Solo Exercise

**The mistake:** Heads down, drawing furiously, not engaging the interviewer.

**The fix:** Make it collaborative. Ask "What do you think?" after major decisions. Respond to their hints and questions genuinely. If they push back on a decision, do not get defensive -- explore the alternative together.

### 6. Going Too Deep Too Early

**The mistake:** Spending 15 minutes on database indexing before you have an architecture diagram.

**The fix:** Breadth first, then depth. Get the full architecture on the board before diving into any single component. This ensures you do not run out of time with half the system undesigned.

### 7. Ignoring Failure Modes

**The mistake:** Designing only the happy path.

**The fix:** For each component, briefly address: "What happens when this fails?" A cache miss is not a failure -- it is expected. A database outage is a failure. What is the blast radius? How do you detect it? How do you recover?

---

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
