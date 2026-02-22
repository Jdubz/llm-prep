# Module 02 Cheat Sheet: Databases at Scale

## SQL vs NoSQL Decision Table

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

## Index Type Comparison

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

---

## Sharding Strategies

| Strategy | Distribution | Range Queries | Resharding Cost | Hot Spot Risk |
|----------|-------------|---------------|-----------------|---------------|
| **Hash-based** | Even | Not possible | High (all data moves) | Low |
| **Range-based** | Variable | Efficient | Medium (split ranges) | High (recent data) |
| **Consistent hashing** | Even | Not possible | Low (~1/N data moves) | Low |
| **Directory-based** | Configurable | Depends | Low (update directory) | Configurable |

**Shard key selection checklist:**
- [ ] High cardinality (many distinct values)
- [ ] Even distribution (no skew)
- [ ] Aligned with query patterns (most queries include the shard key)
- [ ] Not monotonically increasing (avoids hot spots)

**Common shard keys:** `user_id`, `tenant_id`, `hash(entity_id)`

---

## Replication Modes

| Mode | Consistency | Latency Impact | Data Loss Risk | Use Case |
|------|------------|----------------|----------------|----------|
| **Sync leader-follower** | Strong | High (write waits for replica) | None | Financial, critical data |
| **Async leader-follower** | Eventual | None | Possible (lag window) | Most web apps |
| **Semi-sync** | Strong for 1 replica | Medium | Low | Good compromise |
| **Multi-leader** | Conflict resolution needed | Low (local writes) | Depends on resolution | Multi-region |
| **Quorum (W+R>N)** | Tunable | Tunable | Tunable | Cassandra, DynamoDB |

**Read-after-write solutions:**
1. Read your own writes from the leader (short window after write)
2. Monotonic reads via sticky sessions to one replica
3. Causal consistency tokens (write returns a token, read includes it)

---

## CAP / PACELC Quick Reference

### CAP During Partition

| System | Choice | Behavior |
|--------|--------|----------|
| PostgreSQL | CP | Minority side stops serving |
| MongoDB (default) | CP | Primary only accepts writes |
| Cassandra | AP | All nodes serve requests, merge later |
| DynamoDB | AP | All regions serve, last-writer-wins |
| CockroachDB | CP | Minority side stops serving |
| Redis Cluster | AP (default) | Serves from available nodes |

### PACELC Normal Operation

| System | Partition | Else |
|--------|-----------|------|
| PostgreSQL (single) | PC | EC |
| PostgreSQL + async replica | PC | EL (reads from replica) |
| Cassandra | PA | EL |
| DynamoDB | PA | EL |
| Spanner | PC | EC (TrueTime minimizes latency cost) |
| CockroachDB | PC | EC |

---

## PostgreSQL Tuning Essentials

### Key Configuration Parameters

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

## DynamoDB Access Patterns

### Key Design Patterns

| Pattern | PK | SK | Example |
|---------|----|----|---------|
| **1:1 lookup** | `USER#123` | `PROFILE` | Get user profile |
| **1:N query** | `USER#123` | `ORDER#*` | Get user's orders |
| **N:M (GSI)** | Table: `USER#123` / `ORDER#456` | GSI: `STATUS#pending` / `CREATED#2025-01-01` | Orders by status |
| **Time-range** | `DEVICE#abc` | `2025-02-22T10:00:00` | IoT readings by time |
| **Hierarchical** | `ORG#1` | `DEPT#eng#TEAM#platform` | Org hierarchy queries |

### Key Limits

- 1 WCU = 1 write/sec up to 1 KB; 1 RCU = 1 strong read/sec up to 4 KB
- Item size: 400 KB max
- Partition limit: 3,000 RCU or 1,000 WCU per partition
- GSI: eventually consistent only; Transactions: 2x cost

---

## Redis Data Structure Guide

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

### Eviction Policies

| Use Case | Policy |
|----------|--------|
| Caching | `allkeys-lru` or `allkeys-lfu` |
| Session store | `volatile-lru` |
| Mixed use | `volatile-lru` |
| Never lose data | `noeviction` |

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
