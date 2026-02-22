# Module 02: Databases at Scale

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

---

## Indexing Strategies

Indexes are the single most impactful performance lever you have. A missing index can make a query 1,000x slower. A poorly chosen index can make writes 10x slower.

### B-Tree vs LSM-Tree

These are the two fundamental index structures. Every database uses one or the other (or both).

**B-Tree (PostgreSQL, MySQL InnoDB, most SQL databases):**
- Balanced tree structure. O(log n) reads and writes.
- Optimized for **reads** and **point lookups**.
- Updates modify pages in place. Writes are more expensive (random I/O).
- Good for **read-heavy** workloads with mixed query types.

**LSM-Tree (Cassandra, RocksDB, LevelDB, DynamoDB):**
- Write to an in-memory buffer (memtable), flush to sorted files (SSTables) on disk.
- Optimized for **writes** (sequential I/O, no random writes).
- Reads may need to check multiple SSTables (mitigated by bloom filters).
- Good for **write-heavy** workloads.
- Compaction is the hidden cost -- background merging of SSTables consumes CPU and I/O.

**When this matters in interviews:** If asked about a write-heavy system (event logging, metrics collection, IoT), mention that LSM-tree-based stores (Cassandra, RocksDB) handle write amplification better than B-tree stores. If asked about a read-heavy system with complex queries, B-tree-based stores (PostgreSQL) are the better fit.

### Index Types and When to Use Them

**Composite (Multi-Column) Index:**

```sql
CREATE INDEX idx_user_created ON orders(user_id, created_at DESC);
```

Column order matters. This index is useful for:
- `WHERE user_id = 123` (uses first column)
- `WHERE user_id = 123 AND created_at > '2025-01-01'` (uses both columns)
- `WHERE user_id = 123 ORDER BY created_at DESC` (uses both, avoids sort)

This index is NOT useful for:
- `WHERE created_at > '2025-01-01'` (cannot skip the first column)

**Rule of thumb:** Put equality conditions first, range conditions last.

**Covering Index:**

An index that contains all columns needed to satisfy a query, so the database never needs to read the actual table (an "index-only scan").

```sql
-- Query: SELECT user_id, email FROM users WHERE user_id = 123
-- Covering index:
CREATE INDEX idx_user_email ON users(user_id) INCLUDE (email);
```

Covering indexes eliminate the "heap fetch" step and can be 2-10x faster for queries they cover. The trade-off is index size -- every included column increases the index.

**Partial Index:**

An index on a subset of rows. Smaller, faster, and more targeted.

```sql
-- Only index active users (90% of queries are about active users)
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';
```

Use partial indexes when:
- Most queries filter on a specific condition
- You want to enforce uniqueness on a subset (unique partial index)
- The subset is much smaller than the full table

**Expression Index:**

An index on a computed expression rather than a raw column.

```sql
-- Index for case-insensitive email lookup
CREATE INDEX idx_email_lower ON users(LOWER(email));

-- Now this query uses the index:
SELECT * FROM users WHERE LOWER(email) = 'john@example.com';
```

**GIN (Generalized Inverted Index):**

For multi-valued data types: arrays, JSONB, full-text search.

```sql
-- Index for JSONB containment queries
CREATE INDEX idx_metadata ON products USING GIN (metadata);

-- This query uses the GIN index:
SELECT * FROM products WHERE metadata @> '{"color": "red"}';
```

### Reading EXPLAIN ANALYZE

If you cannot read an execution plan, you cannot optimize queries. Here is how to read one:

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE user_id = 123 AND status = 'shipped';
```

```
Bitmap Heap Scan on orders  (cost=4.65..52.83 rows=15 width=120) (actual time=0.042..0.055 rows=12 loops=1)
  Recheck Cond: (user_id = 123)
  Filter: (status = 'shipped')
  Rows Removed by Filter: 3
  Heap Blocks: exact=8
  Buffers: shared hit=10
  ->  Bitmap Index Scan on idx_user_id  (cost=0.00..4.65 rows=18 width=0) (actual time=0.027..0.027 rows=15 loops=1)
        Index Cond: (user_id = 123)
        Buffers: shared hit=2
```

**What to look for:**
- **Seq Scan:** Full table scan. Usually bad for large tables. Means no useful index exists for this query.
- **Index Scan vs Bitmap Index Scan:** Index Scan reads the index and fetches rows one by one. Bitmap Index Scan builds a bitmap of matching pages, then fetches them -- more efficient when many rows match.
- **actual time:** The real execution time (not the estimate). The first number is startup time; the second is total time.
- **rows (estimated vs actual):** If these are wildly different, your table statistics are stale. Run `ANALYZE`.
- **Buffers: shared hit vs shared read:** `hit` means the data was in PostgreSQL's buffer cache. `read` means it went to disk. High hit ratios are good.
- **Filter / Rows Removed by Filter:** The database fetched these rows from the index but then discarded them. This suggests the index is not selective enough or you need a composite index.

---

## Sharding

Sharding is horizontal partitioning -- splitting data across multiple database instances. It is the last resort, not the first optimization. Sharding adds enormous operational complexity.

### When to Shard

1. Your data no longer fits on a single machine (> 5-10 TB for most SQL databases)
2. Your write throughput exceeds what a single machine can handle
3. Your read replicas are not enough (you have already tried read replicas and caching)

### Shard Key Selection

The shard key is the most important decision. It determines data distribution and query routing. A bad shard key can make sharding worse than not sharding at all.

**Good shard key properties:**
- **High cardinality:** Many distinct values (user_id: good. country_code: bad -- only ~200 values)
- **Even distribution:** Data is roughly equal across shards (user_id: usually good. celebrity_id in a social network: bad -- some users have 1000x more data)
- **Query alignment:** Most queries include the shard key (queries without the shard key must scatter-gather across all shards)
- **Monotonically increasing avoidance:** Auto-increment IDs as shard keys create hot spots (all new data goes to the last shard)

**Common shard keys:**
- `user_id` -- good for user-centric applications (each user's data is co-located)
- `tenant_id` -- good for multi-tenant SaaS (each tenant's data is co-located)
- `hash(entity_id)` -- good for even distribution, bad for range queries
- `region` + `entity_id` -- good for geo-distributed systems

### Hash-Based vs Range-Based Sharding

**Hash-Based:**
```
shard = hash(shard_key) % num_shards
```
- Even distribution (assuming a good hash function)
- No range queries across shards (hash destroys ordering)
- Resharding requires data migration (changes `num_shards`, so all data moves)

**Range-Based:**
```
shard 1: user_id 1-1,000,000
shard 2: user_id 1,000,001-2,000,000
...
```
- Efficient range queries within a shard
- Hot spots possible (if recent data is queried more, the last shard is hot)
- Resharding requires splitting ranges and migrating data

**Consistent Hashing:**
```
Each shard owns a range on a hash ring.
Each key is hashed to a point on the ring and assigned to the next shard clockwise.
Adding/removing a shard only moves ~1/N of the keys.
```
- Used by DynamoDB, Cassandra, and most modern distributed databases
- Minimizes data movement during resharding
- Virtual nodes improve distribution (each physical shard has multiple positions on the ring)

### Cross-Shard Queries

The nightmare of sharding. If a query needs data from multiple shards:

1. **Scatter-Gather:** Query all shards, aggregate results. Latency = slowest shard. Works for simple queries but does not scale well.
2. **Application-level join:** Fetch from shard A, then fetch from shard B, join in application code. More control but more application complexity.
3. **Denormalize:** Duplicate data so that each shard has everything it needs. Increases storage, increases write complexity, but eliminates cross-shard queries.
4. **Global tables:** Keep some small, frequently-joined tables (country codes, configuration) replicated on every shard.

**The honest answer for interviews:** "Cross-shard queries are expensive and should be minimized by choosing the right shard key. For the queries that unavoidably span shards, we accept the latency cost of scatter-gather for rare operations and denormalize for frequent ones."

### Resharding

Adding or removing shards is painful. Plan for it from the beginning.

**Strategies:**
- **Logical sharding:** Shard at the application level with many more logical shards than physical shards. Map logical shards to physical shards with a lookup table. Resharding = changing the lookup table + migrating data.
- **Consistent hashing with virtual nodes:** Adding a physical node means reassigning virtual nodes, which moves a fraction of the data.
- **Online migration:** Dual-write to old and new shard. Backfill historical data. Flip reads. Stop writing to old shard. Verify. Remove old shard.

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

**Replication Lag and Read-After-Write Consistency:**

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

### Eventual Consistency Patterns

When you choose AP/EL, you need patterns to handle staleness:

- **Read repair:** On read, if replicas disagree, fix the stale one.
- **Anti-entropy:** Background process that compares replicas and resolves differences.
- **Version vectors / vector clocks:** Track causality to detect and resolve conflicts.
- **Last-writer-wins:** Simple timestamp-based resolution. Lossy but predictable.
- **Merge functions:** Application-specific logic to combine concurrent updates (e.g., union of sets).

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

**When to use GSI:** You need to query by a different attribute than the primary key. Example: query orders by status across all users.

```
GSI: PK = status, SK = created_at
Query: Get all "pending" orders, sorted by creation date
```

**When to use LSI:** You need a different sort order within the same partition. Example: you partition by user_id and want to sort by both created_at and updated_at.

### Capacity Modes

- **On-Demand:** Pay per request. No capacity planning. ~2.5x more expensive at steady state but zero wasted capacity. Good for unpredictable traffic.
- **Provisioned:** Specify read/write capacity units. Cheaper if you predict well. Use auto-scaling.

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

**Strings:**
- Basic key-value. GET/SET. Atomic increment (INCR).
- Use for: caching, counters, rate limiting, session storage.

**Hashes:**
- Field-value pairs under a single key. HGET/HSET/HGETALL.
- Use for: storing objects (user profiles), partial updates without reading the full object.
- More memory-efficient than storing each field as a separate string key.

**Sorted Sets:**
- Members with scores. Ordered by score. O(log N) insert and lookup.
- ZADD, ZRANGE, ZRANGEBYSCORE, ZRANK.
- Use for: leaderboards, priority queues, time-based feeds, rate limiting (sliding window).

```
ZADD leaderboard 1500 "player:123"
ZADD leaderboard 2300 "player:456"
ZREVRANGE leaderboard 0 9 WITHSCORES  -- Top 10
```

**Streams:**
- Append-only log with consumer groups. Similar to Kafka.
- XADD, XREAD, XREADGROUP, XACK.
- Use for: event streaming, activity feeds, message queues when Kafka is overkill.

**HyperLogLog:**
- Probabilistic unique counting. ~0.81% error rate. 12 KB per counter regardless of cardinality.
- Use for: unique visitor counting, unique event counting at massive scale.

**Sets:** Unordered unique members. SADD, SMEMBERS, SINTER, SUNION, SDIFF. Use for tags, mutual friends (set intersection).

**Lists:** Ordered by insertion. LPUSH, RPUSH, LPOP, RPOP, LRANGE. Use for queues, recent items, bounded lists (LTRIM to cap length).

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

**For caching:** Use `allkeys-lru` or `allkeys-lfu`. LFU is better when some keys are accessed in bursts but not frequently overall.

### Pub/Sub vs Streams

Redis Pub/Sub is fire-and-forget messaging -- no persistence, no replay, no consumer groups. Use it for real-time notifications where missing a message is acceptable. Use Redis Streams when every message must be durably processed.

---

## Interview Questions

### Conceptual Questions

1. **When would you choose DynamoDB over PostgreSQL for a new service?**
   - When access patterns are well-defined (always query by PK, optionally with SK range), the data is denormalized or fits a document model, you need consistent single-digit-millisecond latency at any scale, and you want zero operational overhead for scaling. Specifically: high-write-throughput event stores, session stores, gaming leaderboards, IoT data.

2. **Explain replication lag and three strategies to handle it.**
   - Replication lag: async followers are behind the leader. Strategies: (1) read-your-own-writes by routing a user's reads to the leader for N seconds after a write, (2) monotonic reads by pinning users to a specific replica, (3) causal consistency tokens returned after writes and passed to reads to ensure the replica has caught up.

3. **Why might adding an index make your system slower?**
   - Every index must be updated on every write to the indexed table. A table with 10 indexes means each INSERT/UPDATE does 11 writes (1 table + 10 indexes). The write amplification can make inserts dramatically slower. Additionally, the query planner might choose an index that is not optimal, or an index might consume enough memory to evict useful data from the buffer cache.

4. **What is the difference between partitioning and sharding?**
   - Partitioning splits a table into smaller pieces on the same database server (PostgreSQL native partitioning). Sharding splits data across multiple database servers. Partitioning helps with query performance and data lifecycle. Sharding helps with scale (storage, write throughput) but adds distributed systems complexity.

5. **When would you use Redis Sorted Sets vs a database query?**
   - When you need real-time ranking/ordering with sub-millisecond latency and the data changes frequently. A leaderboard that updates on every game action should not require a `SELECT ... ORDER BY score DESC LIMIT 10` on every read. A sorted set gives O(log N) inserts and O(log N + M) range queries in memory. The trade-off: Redis data is in memory (expensive), and durability is weaker than a database.

### Scenario-Based Questions

6. **Your PostgreSQL database is at 95% disk usage and queries are getting slower. Walk through your investigation and remediation.**
   - Investigation: Check for table bloat (`pg_stat_user_tables` -- dead tuple ratio), check autovacuum status, check for unused indexes consuming space, check for large tables that could be partitioned or archived. Remediation in order: (1) run manual VACUUM on bloated tables, (2) tune autovacuum to be more aggressive, (3) drop unused indexes, (4) archive old data to cold storage, (5) as last resort, VACUUM FULL (requires downtime).

7. **You need to add a new column to a table with 500M rows in PostgreSQL without downtime. How?**
   - `ALTER TABLE ADD COLUMN` with a default value is fast in PostgreSQL 11+ (it stores the default in the catalog, does not rewrite the table). For older versions or not-null constraints, use the expand-contract pattern: (1) add column as nullable, (2) backfill in batches, (3) add not-null constraint with `NOT VALID`, (4) validate in background, (5) update application code, (6) drop old column.

8. **Your DynamoDB table is experiencing hot partitions. How do you diagnose and fix it?**
   - Diagnosis: CloudWatch `ConsumedReadCapacityUnits` and `ConsumedWriteCapacityUnits` metrics per partition. Enable DynamoDB Contributor Insights to see which partition keys are hot. Fix options: (1) add randomness to partition key (write sharding -- e.g., append a random suffix 0-9), (2) use DAX to absorb read traffic, (3) redesign the access pattern to distribute load, (4) use on-demand capacity mode which handles bursts better.

9. **Design the database layer for a multi-tenant SaaS application. How do you handle tenant isolation?**
   - Three approaches: (1) **Shared database, shared schema** -- all tenants in one table with a `tenant_id` column. Cheapest but no isolation. Row-level security (PostgreSQL RLS) provides some protection. (2) **Shared database, separate schemas** -- each tenant gets their own PostgreSQL schema. Better isolation, harder to manage at scale (1000+ schemas). (3) **Separate databases** -- full isolation, easy to meet compliance requirements, most expensive, hardest to manage. Choose based on compliance needs and number of tenants.

10. **You are migrating from a monolith's single PostgreSQL database to microservices. Each service needs its own database. How do you handle cross-service queries that used to be JOINs?**
    - Options: (1) API composition -- the calling service makes multiple API calls and joins in memory. Simple but latency adds up. (2) CQRS -- maintain a read model (materialized view) that pre-joins data from multiple services via events. Complex but fast reads. (3) Data denormalization -- duplicate data across service databases. Fast reads, eventual consistency on writes, sync via events. (4) Shared reference data -- small, rarely-changing reference tables replicated to all services.

### Design Challenge

11. **Design the data storage layer for a social media platform that handles 50M DAU with feeds, posts, likes, follows, and direct messages. Cover database choices, indexing, caching, and sharding strategy.**
    - This is a multi-database problem. Posts and user profiles in PostgreSQL (relational, ACID). Feed assembly in Redis (sorted sets by timestamp). Like counts in Redis (atomic counters). Social graph (follows) in PostgreSQL or a graph database depending on the query patterns (friend-of-friend queries favor graph DB). Direct messages in Cassandra or DynamoDB (high write throughput, partition by conversation_id, sort by timestamp). Shard users by user_id across PostgreSQL instances. Cache aggressively with Redis -- hot user profiles, feed pages, like counts.

12. **Your Redis cluster is running out of memory. You use it for caching, rate limiting, and real-time analytics. How do you decide what stays and what goes?**
    - Prioritize by criticality: rate limiting must stay (functional correctness depends on it). Real-time analytics can tolerate moving to a different store or sampling. Caching is the most elastic -- analyze cache hit rates, evict low-hit-rate entries first. Consider: (1) set TTLs on all cache keys if not already, (2) switch from `allkeys-lru` to `allkeys-lfu` to retain frequently accessed keys, (3) move analytics to Redis Streams with a consumer that writes to a time-series DB, (4) move rate limiting to a separate small Redis instance to isolate it from cache eviction pressure.

---

## Key Takeaways

1. **The database is a tool, not an identity.** Choose based on access patterns, consistency needs, and scale requirements. Be prepared to use multiple databases in one system.

2. **Indexes are the highest-leverage optimization.** Before sharding, before caching, before adding servers -- check your indexes. Most performance problems are missing or suboptimal indexes.

3. **Shard last, not first.** Sharding adds complexity that you pay for forever. Exhaust vertical scaling, read replicas, and caching before you shard.

4. **Understand the mechanics, not just the abstractions.** Know why MVCC creates dead tuples. Know why LSM-trees are better for writes. This mechanical understanding lets you predict behavior in novel situations.

5. **Replication is not backup.** Replication protects against hardware failure. Backups protect against data corruption, accidental deletion, and logical errors. You need both.

6. **Consistency is a spectrum, not a binary.** Strong consistency, eventual consistency, causal consistency, read-your-own-writes, monotonic reads -- each has different performance and correctness properties. Choose the weakest consistency level that meets your requirements.
