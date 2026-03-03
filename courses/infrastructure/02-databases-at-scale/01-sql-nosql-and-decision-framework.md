# Module 02: SQL, NoSQL, and the Decision Framework

## Overview

Database decisions are the most consequential architectural choices you will make. They are expensive to reverse, they determine your system's performance ceiling, and they constrain your future options. This module is not about which database is "best" -- it is about understanding when each tool is the right fit and how to operate them at scale.

The engineers who struggle with database questions in interviews are the ones who have opinions without understanding the mechanics. You do not need to be a DBA, but you need to understand *why* your database behaves the way it does so you can predict its behavior under new conditions.

---

## SQL vs NoSQL: A Decision Framework

This is not a religious debate. Both are tools. Here is when each makes sense.

### Choose SQL (PostgreSQL, MySQL) When

- Your data is **inherently relational** (users have orders, orders have items, items belong to categories)
- You need **ACID transactions** across multiple entities (financial systems, inventory management)
- Your **access patterns are diverse** and hard to predict (ad-hoc queries, analytics, reporting)
- Your **data fits on one machine** or a small number of machines (< 10 TB)
- You need **complex queries** (JOINs, aggregations, window functions, CTEs)
- **Correctness** matters more than write throughput

### Choose NoSQL When

- Your access patterns are **well-defined and narrow** (always query by user_id, always query by timestamp range)
- You need **horizontal write scalability** beyond what a single SQL server can provide
- Your data is **denormalized by nature** (event logs, time-series data, document blobs)
- You can tolerate **eventual consistency** for most operations
- Your schema is **highly variable** (different records have different fields)
- **Write throughput and latency** at scale matter more than query flexibility

### The Hybrid Approach

Most real-world systems use both. A typical pattern:

- **PostgreSQL** as the primary source of truth for transactional data (users, accounts, orders)
- **Redis** for caching, session storage, rate limiting, real-time counters
- **Elasticsearch** for search and analytics
- **DynamoDB** or **Cassandra** for high-write-throughput use cases (event streams, activity feeds)
- **S3** for blob storage

The question is not "SQL or NoSQL?" It is "Which data store for which access pattern?"

### Decision Matrix

| Factor | SQL | Document (MongoDB) | Key-Value (DynamoDB) | Wide Column (Cassandra) |
|--------|-----|---------------------|----------------------|------------------------|
| Query flexibility | High | Medium | Low | Low |
| Write scalability | Medium | High | Very High | Very High |
| Consistency | Strong (default) | Tunable | Tunable | Tunable |
| Schema enforcement | Strict | Flexible | Flexible | Semi-flexible |
| Joins | Native | Limited ($lookup) | None | None |
| Transactions | Full ACID | Single-doc (multi-doc limited) | Single-item (limited) | Lightweight transactions |
| Operational complexity | Low-Medium | Medium | Low (managed) | High |
| Max practical dataset | ~10 TB per node | ~10 TB per shard | Unlimited (managed) | Unlimited |

### Quick Decision Table

| Question | If Yes -> SQL | If Yes -> NoSQL |
|----------|--------------|-----------------|
| Data is relational with many entity types? | X | |
| Need ACID transactions across entities? | X | |
| Access patterns are unpredictable / ad-hoc? | X | |
| Data fits on one machine (< 10 TB)? | X | |
| Need complex queries (JOINs, aggregations)? | X | |
| Access patterns are narrow and well-defined? | | X |
| Need horizontal write scalability? | | X |
| Schema varies significantly across records? | | X |
| Eventual consistency is acceptable? | | X |
| Write throughput > 50K/sec? | | X |

**Default choice:** PostgreSQL unless you have a specific, measurable reason to use something else.

---

## CAP Theorem in Practice

### What CAP Actually Says

In the presence of a network partition (P), a distributed system must choose between:
- **Consistency (C):** Every read receives the most recent write or an error.
- **Availability (A):** Every request receives a response (not an error), but the response might be stale.

**Key nuance:** CAP only applies during a partition. When the network is healthy, you can have both C and A. The question is: what does your system do when a partition occurs?

**CP Systems** (choose consistency, sacrifice availability during partition):
- HBase, MongoDB (default), PostgreSQL, Zookeeper
- During a partition, the minority side refuses to serve requests
- Guarantees: you never read stale data
- Cost: some requests fail during partitions

**AP Systems** (choose availability, sacrifice consistency during partition):
- Cassandra, DynamoDB, CouchDB, DNS
- During a partition, all nodes continue to serve requests
- Guarantees: every request gets a response
- Cost: responses may be stale; conflicts must be resolved when partition heals

### PACELC

CAP is incomplete. PACELC extends it:

```
If Partition:
  Choose Availability or Consistency (same as CAP)
Else (normal operation):
  Choose Latency or Consistency
```

This captures the trade-off that exists even when there is no partition. Synchronous replication gives consistency but adds latency. Asynchronous replication gives low latency but introduces staleness.

| System | P+A vs P+C | E+L vs E+C |
|--------|------------|------------|
| DynamoDB | PA | EL |
| Cassandra | PA | EL |
| MongoDB | PC | EC |
| PostgreSQL (single) | PC | EC |
| PostgreSQL + async replica | PC | EL (for reads from replica) |
| Spanner | PC | EC (but low latency via TrueTime) |
| CockroachDB | PC | EC |

### CAP During Partition (Quick Reference)

| System | Choice | Behavior |
|--------|--------|----------|
| PostgreSQL | CP | Minority side stops serving |
| MongoDB (default) | CP | Primary only accepts writes |
| Cassandra | AP | All nodes serve requests, merge later |
| DynamoDB | AP | All regions serve, last-writer-wins |
| CockroachDB | CP | Minority side stops serving |
| Redis Cluster | AP (default) | Serves from available nodes |

### Eventual Consistency Patterns

When you choose AP/EL, you need patterns to handle staleness:

- **Read repair:** On read, if replicas disagree, fix the stale one.
- **Anti-entropy:** Background process that compares replicas and resolves differences.
- **Version vectors / vector clocks:** Track causality to detect and resolve conflicts.
- **Last-writer-wins:** Simple timestamp-based resolution. Lossy but predictable.
- **Merge functions:** Application-specific logic to combine concurrent updates (e.g., union of sets).

---

## Replication

Replication serves two purposes: **fault tolerance** (survive hardware failures) and **read scaling** (distribute read load across replicas).

### Leader-Follower (Primary-Replica)

The most common replication topology.

```
Writes -> Leader -> Replication -> Follower 1 (reads)
                                -> Follower 2 (reads)
                                -> Follower 3 (reads)
```

- All writes go to the leader. Followers receive a replication stream.
- Reads can go to any follower (with caveat: replication lag).
- If the leader fails, promote a follower (manual or automatic failover).
- **Sync replication:** Leader waits for follower to confirm write. Slower writes, no data loss on leader failure.
- **Async replication:** Leader does not wait. Faster writes, possible data loss if leader fails before replication completes.

### Replication Lag and Read-After-Write Consistency

Async replication means followers may be seconds behind the leader. This creates a read-after-write problem:

```
1. User writes to leader (creates a post)
2. User reads from follower (tries to see their post)
3. Follower has not received the write yet
4. User sees stale data (their post is missing)
```

**Solutions:**
- **Read your own writes from the leader:** After a write, route that user's reads to the leader for a short window (5-10 seconds).
- **Monotonic reads:** Pin each user to a specific follower (consistent hashing on user_id). They might see stale data, but they will never go backward in time.
- **Causal consistency tokens:** After a write, return a token representing the write position. Include this token in subsequent reads. Followers wait until they have caught up to that position before responding.

**Read-after-write solutions summary:**
1. Read your own writes from the leader (short window after write)
2. Monotonic reads via sticky sessions to one replica
3. Causal consistency tokens (write returns a token, read includes it)

### Multi-Leader Replication

Multiple nodes accept writes. Used for multi-datacenter setups.

```
Region A Leader <---> Region B Leader
      |                      |
Followers A             Followers B
```

- Each region has a leader that accepts writes from local clients.
- Leaders asynchronously replicate to each other.
- **The hard problem:** Write conflicts. Two regions modify the same record concurrently.

**Conflict Resolution Strategies:**
- **Last-writer-wins (LWW):** Highest timestamp wins. Simple but lossy -- one write is silently discarded. Used by Cassandra, DynamoDB Global Tables.
- **Application-level resolution:** Store both versions, let the application decide (e.g., merge shopping carts).
- **CRDTs (Conflict-free Replicated Data Types):** Data structures that mathematically guarantee convergence. Good for counters, sets, registers. Limited for complex data.

### Quorum-Based Replication

Used by Cassandra, DynamoDB, Riak.

```
N = total replicas
W = replicas that must acknowledge a write
R = replicas that must respond to a read

If W + R > N, you get strong consistency (read and write sets overlap)
```

**Common configurations:**
- `N=3, W=2, R=2`: Strong consistency. Tolerate 1 node failure for both reads and writes.
- `N=3, W=1, R=1`: Maximum availability and performance. Eventual consistency.
- `N=3, W=3, R=1`: Fast reads, slow writes. Strong consistency. Cannot write if any node is down.
- `N=3, W=1, R=3`: Fast writes, slow reads. Strong consistency. Cannot read if any node is down.

### Replication Modes Comparison

| Mode | Consistency | Latency Impact | Data Loss Risk | Use Case |
|------|------------|----------------|----------------|----------|
| **Sync leader-follower** | Strong | High (write waits for replica) | None | Financial, critical data |
| **Async leader-follower** | Eventual | None | Possible (lag window) | Most web apps |
| **Semi-sync** | Strong for 1 replica | Medium | Low | Good compromise |
| **Multi-leader** | Conflict resolution needed | Low (local writes) | Depends on resolution | Multi-region |
| **Quorum (W+R>N)** | Tunable | Tunable | Tunable | Cassandra, DynamoDB |

---

## PostgreSQL Deep Dive

### MVCC (Multi-Version Concurrency Control)

PostgreSQL never overwrites data in place. Instead, every UPDATE creates a new version of the row. Old versions are kept for transactions that started before the update.

```
Transaction 1 (started at time T1):
  Sees version A of row 42

Transaction 2 (started at time T2, after T1):
  Updates row 42, creating version B

Transaction 1:
  Still sees version A (its snapshot has not changed)
  No blocking. No locking for reads.
```

**Why this matters:**
- Readers never block writers. Writers never block readers. This is why PostgreSQL handles concurrent workloads well.
- The cost: dead tuples accumulate. Old versions that no transaction needs are "dead" but still on disk.

### VACUUM

VACUUM reclaims space from dead tuples.

- **Regular VACUUM:** Marks dead tuples as reusable. Does not return space to the OS. Does not block reads/writes.
- **VACUUM FULL:** Rewrites the entire table, returning space to the OS. Locks the table exclusively. Use only when space reclamation is urgent.
- **Autovacuum:** Background process that runs VACUUM automatically based on configurable thresholds.

**Common problems:**
- **Autovacuum falling behind:** High-write tables generate dead tuples faster than autovacuum can clean them. Tune: `autovacuum_vacuum_scale_factor`, `autovacuum_vacuum_cost_delay`.
- **Transaction ID wraparound:** PostgreSQL uses 32-bit transaction IDs (~4.2 billion). If VACUUM cannot clean up old transactions, the database forces a shutdown to prevent corruption. Monitor `age(datfrozenxid)`.
- **Bloated tables:** Tables that rarely get vacuumed grow larger than necessary. Queries slow down because more pages must be scanned.

**Tuning autovacuum for high-write tables:**

```sql
ALTER TABLE hot_table SET (
  autovacuum_vacuum_scale_factor = 0.01,     -- vacuum when 1% of rows are dead (default: 20%)
  autovacuum_vacuum_cost_delay = 2,           -- be more aggressive (default: 20ms)
  autovacuum_analyze_scale_factor = 0.005     -- update statistics more frequently
);
```

### Connection Pooling with PgBouncer

PostgreSQL creates a new OS process for each connection. At 1,000+ connections, context switching overhead kills performance.

**PgBouncer** sits between your application and PostgreSQL, multiplexing many client connections over a small pool of server connections.

```
App Servers (1000s of connections) -> PgBouncer (pool of 50-100 connections) -> PostgreSQL
```

**Pooling modes:**
- **Session pooling:** Client gets a server connection for the entire session. Safest. Least efficient.
- **Transaction pooling:** Client gets a server connection for each transaction, returns it when the transaction ends. Most common for web applications. Cannot use session-level features (prepared statements, advisory locks, LISTEN/NOTIFY).
- **Statement pooling:** Client gets a connection for each SQL statement. Most aggressive. Cannot use multi-statement transactions.

### Partitioning

Native table partitioning in PostgreSQL (since v10).

```sql
CREATE TABLE events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY,
    created_at  TIMESTAMP NOT NULL,
    event_type  TEXT NOT NULL,
    payload     JSONB
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE events_2025_02 PARTITION OF events
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

**Benefits:**
- Partition pruning: queries with a WHERE clause on the partition key only scan relevant partitions.
- Efficient data lifecycle: drop an old partition instead of DELETE (instantaneous vs hours).
- Parallel query: PostgreSQL can scan multiple partitions in parallel.

**Gotchas:**
- Index each partition separately (or let PostgreSQL create them automatically).
- Cross-partition queries may be slower than a well-indexed single table.
- Unique constraints must include the partition key.

### PostgreSQL JSON Support

PostgreSQL's JSONB is a legitimate alternative to MongoDB for document storage, with the added benefit of SQL queries and ACID transactions.

```sql
CREATE TABLE products (
    id       BIGINT PRIMARY KEY,
    name     TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'
);

-- GIN index for containment queries
CREATE INDEX idx_products_metadata ON products USING GIN (metadata);

-- Query by nested JSON field
SELECT * FROM products WHERE metadata @> '{"color": "red"}';

-- Access specific JSON field
SELECT metadata->>'color' as color FROM products;

-- JSON aggregation
SELECT metadata->>'category', COUNT(*)
FROM products
GROUP BY metadata->>'category';
```

### PostgreSQL Tuning Essentials

```
# Memory
shared_buffers = 25% of RAM          # Buffer cache (e.g., 4GB on 16GB machine)
effective_cache_size = 75% of RAM     # Hint to planner about OS cache
work_mem = 64MB                       # Per-sort/hash operation (careful: per-query)
maintenance_work_mem = 512MB          # For VACUUM, CREATE INDEX

# WAL
wal_buffers = 64MB                    # WAL write buffer
checkpoint_completion_target = 0.9    # Spread checkpoints over time
max_wal_size = 4GB                    # Trigger checkpoint if WAL exceeds this

# Connections
max_connections = 100-200             # Use PgBouncer, not high max_connections

# Autovacuum (for high-write tables)
autovacuum_vacuum_scale_factor = 0.02
autovacuum_analyze_scale_factor = 0.01
autovacuum_vacuum_cost_delay = 2ms
```

### Key Diagnostic Queries

```sql
-- Table bloat: pg_stat_user_tables (n_dead_tup / n_live_tup)
-- Slow queries: pg_stat_statements (ORDER BY mean_exec_time DESC)
-- Unused indexes: pg_stat_user_indexes (ORDER BY idx_scan ASC)
-- Cache hit ratio: pg_statio_user_tables (heap_blks_hit / total, target > 99%)
-- Connections: pg_stat_activity (GROUP BY state)
```

---

## DynamoDB Deep Dive

### Data Model

DynamoDB tables have:
- **Partition Key (PK):** Required. Determines which partition stores the item. Must be specified in every query.
- **Sort Key (SK):** Optional. Allows range queries within a partition. PK + SK together form the primary key.

**Single-table design:** Instead of multiple tables (users, orders, order_items), store everything in one table using composite keys:

```
PK              | SK                    | Attributes
USER#123        | PROFILE               | name, email, ...
USER#123        | ORDER#456             | total, status, ...
USER#123        | ORDER#456#ITEM#1      | product_id, qty, ...
ORDER#456       | METADATA              | user_id, created_at, ...
```

**Why single-table?** DynamoDB does not support joins. By co-locating related data in the same partition, you can fetch it all in a single query. The downside: data modeling is harder and the table is less readable.

### GSI and LSI

- **GSI (Global Secondary Index):** A completely separate index with its own partition key and sort key. Eventually consistent. Has its own throughput capacity. You can create up to 20 per table.
- **LSI (Local Secondary Index):** Same partition key as the base table, different sort key. Strongly consistent reads available. Must be created at table creation time. Limited to 10 GB per partition key value.

**DynamoDB Access Patterns:**

| Pattern | PK | SK | Example |
|---------|----|----|---------|
| **1:1 lookup** | `USER#123` | `PROFILE` | Get user profile |
| **1:N query** | `USER#123` | `ORDER#*` | Get user's orders |
| **N:M (GSI)** | Table: `USER#123` / `ORDER#456` | GSI: `STATUS#pending` / `CREATED#2025-01-01` | Orders by status |
| **Time-range** | `DEVICE#abc` | `2025-02-22T10:00:00` | IoT readings by time |
| **Hierarchical** | `ORG#1` | `DEPT#eng#TEAM#platform` | Org hierarchy queries |

### Capacity Modes

- **On-Demand:** Pay per request. No capacity planning. ~2.5x more expensive at steady state but zero wasted capacity. Good for unpredictable traffic.
- **Provisioned:** Specify read/write capacity units. Cheaper if you predict well. Use auto-scaling.

**Key Limits:**
- 1 WCU = 1 write/sec up to 1 KB; 1 RCU = 1 strong read/sec up to 4 KB
- Item size: 400 KB max
- Partition limit: 3,000 RCU or 1,000 WCU per partition
- GSI: eventually consistent only; Transactions: 2x cost

**Rule of thumb:** Start with on-demand. Switch to provisioned when your traffic is predictable and cost optimization matters.

### DAX (DynamoDB Accelerator)

In-memory cache in front of DynamoDB. Microsecond read latency instead of millisecond.

- Transparent to the application (same API, just point to DAX endpoint).
- Write-through: writes go through DAX to DynamoDB.
- Item cache (individual items) and query cache (query results).
- Reduces DynamoDB read costs (fewer RCUs consumed).

**When to use DAX:** Read-heavy workloads with repeated access to the same items. Not useful for write-heavy workloads or scan-heavy workloads.

---

## Redis Deep Dive

### Data Structures

Redis is not just a key-value cache. Its data structures make it a versatile tool.

| Structure | Key Operations | Time Complexity | Best For |
|-----------|---------------|-----------------|----------|
| **String** | GET, SET, INCR, MGET | O(1) | Caching, counters, locks |
| **Hash** | HGET, HSET, HGETALL, HINCRBY | O(1) per field | Objects, partial updates |
| **List** | LPUSH, RPOP, LRANGE, LTRIM | O(1) push/pop, O(N) range | Queues, recent items |
| **Set** | SADD, SMEMBERS, SINTER, SCARD | O(1) add, O(N) members | Tags, unique items, intersections |
| **Sorted Set** | ZADD, ZRANGE, ZRANK, ZRANGEBYSCORE | O(log N) | Leaderboards, priority queues, time feeds |
| **Stream** | XADD, XREAD, XREADGROUP, XACK | O(1) add, O(N) read | Event streaming, message queues |
| **HyperLogLog** | PFADD, PFCOUNT, PFMERGE | O(1) | Unique counting (approximate) |
| **Bitmap** | SETBIT, GETBIT, BITCOUNT | O(1) per bit | Feature flags, daily active users |

```
ZADD leaderboard 1500 "player:123"
ZADD leaderboard 2300 "player:456"
ZREVRANGE leaderboard 0 9 WITHSCORES  -- Top 10
```

### Persistence

Redis is in-memory but can persist data to disk.

**RDB (Snapshotting):** Point-in-time snapshots at configured intervals. Compact, fast recovery. Data loss between snapshots.

**AOF (Append-Only File):** Logs every write operation. Three fsync policies: always (safest), every second (good balance), never (fastest). Larger files, slower recovery.

**Recommended:** AOF with `appendfsync everysec` for durability/performance balance. RDB for backups.

### Clustering

Redis Cluster splits data across 16,384 hash slots distributed across nodes. Clients route to the correct node by key hash. Multi-key operations require all keys in the same hash slot -- use `{hash_tag}` notation to co-locate related keys (e.g., `{user:123}:profile` and `{user:123}:settings`).

### Eviction Policies

When Redis hits its memory limit, it evicts keys based on the configured policy:

| Policy | Behavior |
|--------|----------|
| `noeviction` | Return errors on write (do not evict). Default. |
| `allkeys-lru` | Evict least recently used key (any key). Best for caching. |
| `volatile-lru` | Evict least recently used key (only keys with TTL). |
| `allkeys-random` | Evict random key. |
| `volatile-ttl` | Evict key closest to expiration. |
| `allkeys-lfu` | Evict least frequently used key. Better than LRU for skewed distributions. |

| Use Case | Policy |
|----------|--------|
| Caching | `allkeys-lru` or `allkeys-lfu` |
| Session store | `volatile-lru` |
| Mixed use | `volatile-lru` |
| Never lose data | `noeviction` |

**For caching:** Use `allkeys-lru` or `allkeys-lfu`. LFU is better when some keys are accessed in bursts but not frequently overall.

### Pub/Sub vs Streams

Redis Pub/Sub is fire-and-forget messaging -- no persistence, no replay, no consumer groups. Use it for real-time notifications where missing a message is acceptable. Use Redis Streams when every message must be durably processed.

---

## Quick Decision Matrix

| Need | Tool |
|------|------|
| Relational data, ACID, complex queries | PostgreSQL |
| Horizontal write scale, key-value | DynamoDB |
| Caching, real-time data structures | Redis |
| Full-text search | Elasticsearch |
| Time-series metrics | TimescaleDB |
| Graph traversals | Neo4j / Neptune |
| Vector similarity | pgvector / Pinecone |
| Blob storage | S3 / GCS |
| Multi-region SQL | CockroachDB / Spanner |

---

## Key Takeaways

1. **The database is a tool, not an identity.** Choose based on access patterns, consistency needs, and scale requirements. Be prepared to use multiple databases in one system.

2. **Consistency is a spectrum, not a binary.** Strong consistency, eventual consistency, causal consistency, read-your-own-writes, monotonic reads -- each has different performance and correctness properties. Choose the weakest consistency level that meets your requirements.

3. **Understand the mechanics, not just the abstractions.** Know why MVCC creates dead tuples. Know why LSM-trees are better for writes. This mechanical understanding lets you predict behavior in novel situations.

4. **Replication is not backup.** Replication protects against hardware failure. Backups protect against data corruption, accidental deletion, and logical errors. You need both.
