# Module 02: Indexing, Sharding, and Replication

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

#### Index Type Comparison

| Index Type | Use Case | Syntax (PostgreSQL) |
|------------|----------|---------------------|
| **B-tree** (default) | Equality, range, sorting | `CREATE INDEX idx ON t(col)` |
| **Composite** | Multi-column queries | `CREATE INDEX idx ON t(col1, col2)` |
| **Covering** | Index-only scans | `CREATE INDEX idx ON t(col1) INCLUDE (col2)` |
| **Partial** | Subset of rows | `CREATE INDEX idx ON t(col) WHERE condition` |
| **Expression** | Computed values | `CREATE INDEX idx ON t(LOWER(col))` |
| **GIN** | JSONB, arrays, full-text | `CREATE INDEX idx ON t USING GIN (col)` |
| **GiST** | Geometry, ranges, nearest-neighbor | `CREATE INDEX idx ON t USING GiST (col)` |
| **BRIN** | Large tables, naturally ordered data | `CREATE INDEX idx ON t USING BRIN (col)` |

**Composite index rule:** Equality columns first, range/sort columns last.

**Covering index rule:** Use `INCLUDE` for columns that appear in SELECT but not WHERE.

#### Composite (Multi-Column) Index

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

#### Covering Index

An index that contains all columns needed to satisfy a query, so the database never needs to read the actual table (an "index-only scan").

```sql
-- Query: SELECT user_id, email FROM users WHERE user_id = 123
-- Covering index:
CREATE INDEX idx_user_email ON users(user_id) INCLUDE (email);
```

Covering indexes eliminate the "heap fetch" step and can be 2-10x faster for queries they cover. The trade-off is index size -- every included column increases the index.

#### Partial Index

An index on a subset of rows. Smaller, faster, and more targeted.

```sql
-- Only index active users (90% of queries are about active users)
CREATE INDEX idx_active_users ON users(email) WHERE status = 'active';
```

Use partial indexes when:
- Most queries filter on a specific condition
- You want to enforce uniqueness on a subset (unique partial index)
- The subset is much smaller than the full table

#### Expression Index

An index on a computed expression rather than a raw column.

```sql
-- Index for case-insensitive email lookup
CREATE INDEX idx_email_lower ON users(LOWER(email));

-- Now this query uses the index:
SELECT * FROM users WHERE LOWER(email) = 'john@example.com';
```

#### GIN (Generalized Inverted Index)

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

**Shard key selection checklist:**
- [ ] High cardinality (many distinct values)
- [ ] Even distribution (no skew)
- [ ] Aligned with query patterns (most queries include the shard key)
- [ ] Not monotonically increasing (avoids hot spots)

### Hash-Based vs Range-Based Sharding

| Strategy | Distribution | Range Queries | Resharding Cost | Hot Spot Risk |
|----------|-------------|---------------|-----------------|---------------|
| **Hash-based** | Even | Not possible | High (all data moves) | Low |
| **Range-based** | Variable | Efficient | Medium (split ranges) | High (recent data) |
| **Consistent hashing** | Even | Not possible | Low (~1/N data moves) | Low |
| **Directory-based** | Configurable | Depends | Low (update directory) | Configurable |

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

1. **Indexes are the highest-leverage optimization.** Before sharding, before caching, before adding servers -- check your indexes. Most performance problems are missing or suboptimal indexes.

2. **Shard last, not first.** Sharding adds complexity that you pay for forever. Exhaust vertical scaling, read replicas, and caching before you shard.

3. **The composite index column order is critical.** Put equality conditions first, range conditions last. An index on (status, created_at) helps queries filtering on status and ranging on created_at, but not the reverse.

4. **Covering indexes eliminate heap fetches.** For hot query paths, consider whether adding an INCLUDE column to an index can turn an Index Scan into an Index Only Scan.
