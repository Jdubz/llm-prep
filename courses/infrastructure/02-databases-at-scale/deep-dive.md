# Module 02 Deep Dive: Specialized Databases & Advanced Patterns

## Overview

The mainstream SQL and NoSQL databases cover 80% of use cases. This deep dive covers the remaining 20% -- the specialized databases and advanced patterns that come up in staff-level interviews and real-world architecture decisions. These are the tools you reach for when PostgreSQL or DynamoDB are not the right fit.

---

## NewSQL Databases

NewSQL databases attempt to combine the scalability of NoSQL with the ACID guarantees and SQL interface of traditional relational databases. They exist because distributed transactions are genuinely hard, and many teams want horizontal scalability without giving up SQL.

### Google Spanner

The original NewSQL database. Globally distributed, strongly consistent, SQL-compatible.

**Key innovation: TrueTime.** Spanner uses GPS receivers and atomic clocks in every datacenter to provide a global clock with bounded uncertainty (~7ms). This allows it to order transactions globally without the latency penalty of traditional distributed consensus.

**How it works:**
- Data is sharded across multiple nodes (splits).
- Each split is replicated via Paxos across zones/regions.
- Writes require Paxos consensus within a replica group.
- Cross-shard transactions use two-phase commit with TrueTime for ordering.
- Reads at a specific timestamp can be served from any replica that is up-to-date (stale reads are fast; strong reads wait for TrueTime uncertainty to pass).

**When to use:** Global-scale applications that need strong consistency and SQL. Financial systems, inventory systems that span multiple regions. Google Cloud only.

**Trade-offs:** Expensive (Spanner is one of the priciest managed databases). Write latency is higher than single-region databases (Paxos consensus). You are locked into Google Cloud.

### CockroachDB

Open-source, Spanner-inspired. PostgreSQL wire-compatible.

**Key properties:**
- Distributed SQL with serializable isolation (strongest level).
- Automatic sharding and rebalancing.
- Survives node, zone, and region failures.
- PostgreSQL-compatible SQL (most queries work unchanged).

**How it differs from PostgreSQL:**
- Distributed transactions are slower (network round trips for consensus).
- No support for some PostgreSQL extensions.
- Different performance profile: simple key-value lookups are slower than PostgreSQL, but the system scales horizontally.
- Secondary indexes are global (distributed), unlike PostgreSQL where indexes are local.

**When to use:** Multi-region applications that need SQL and strong consistency without being locked into Google Cloud. Teams migrating from PostgreSQL that have outgrown a single node.

**Trade-offs:** Higher per-query latency than single-node PostgreSQL. Operational complexity of a distributed database (even if it is self-managing). Not a drop-in PostgreSQL replacement despite wire compatibility.

### TiDB

MySQL-compatible distributed SQL database from PingCAP.

**Architecture:**
- TiDB layer: stateless SQL processing (MySQL protocol).
- TiKV layer: distributed key-value storage (based on RocksDB, Raft consensus).
- PD (Placement Driver): cluster metadata and scheduling.

**Key differentiator:** HTAP (Hybrid Transactional/Analytical Processing). TiDB can serve both OLTP and OLAP workloads from the same system using TiFlash (columnar storage) alongside TiKV (row storage).

**When to use:** MySQL-heavy environments that need horizontal scaling. Workloads that combine transactional and analytical queries. Teams that want to avoid the operational complexity of separate OLTP and OLAP systems.

### When to Reach for NewSQL vs Staying with PostgreSQL

| Scenario | Stay with PostgreSQL | Consider NewSQL |
|----------|---------------------|-----------------|
| Single region, < 10 TB | Yes | No |
| Need horizontal write scaling | Read replicas + sharding | Yes |
| Multi-region strong consistency | Manual setup, complex | Yes (built-in) |
| Existing PostgreSQL codebase | Yes (minimize migration risk) | Only if scale demands it |
| Complex analytical queries | Yes (mature optimizer) | Maybe (less mature optimizers) |
| Operational simplicity | Yes (well-understood) | No (newer, less tooling) |

---

## Time-Series Databases

Time-series data has unique properties: it is append-heavy (rarely updated), naturally ordered by time, typically queried over time ranges, and benefits from time-based compression and retention policies.

### TimescaleDB

PostgreSQL extension for time-series data. You get full PostgreSQL with time-series superpowers.

**Key features:**
- **Hypertables:** Automatic partitioning by time (and optionally space). A hypertable looks like a regular table but is transparently partitioned into chunks.
- **Continuous aggregates:** Materialized views that incrementally update as new data arrives. Query pre-computed rollups instead of raw data.
- **Compression:** Columnar compression for older data. 90-95% compression ratio typical.
- **Retention policies:** Automatically drop old data based on age.

```sql
-- Create a hypertable
SELECT create_hypertable('metrics', 'timestamp');

-- Continuous aggregate for hourly rollups
CREATE MATERIALIZED VIEW metrics_hourly
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', timestamp) AS hour,
       device_id,
       AVG(value) as avg_value,
       MAX(value) as max_value,
       COUNT(*) as sample_count
FROM metrics
GROUP BY hour, device_id;
```

**When to use:** You are already on PostgreSQL and need time-series capabilities. You need SQL joins between time-series data and relational data. Monitoring, IoT, financial tick data.

### InfluxDB

Purpose-built time-series database with its own query language (Flux) and SQL support (in v3).

**Key properties:**
- Optimized for high-ingest workloads (millions of writes per second).
- Built-in retention policies and downsampling.
- Schemaless -- tags and fields are defined on write.
- TSM (Time-Structured Merge Tree) storage engine -- optimized for time-series write patterns.

**When to use:** Dedicated monitoring/observability stack. Very high cardinality metrics. Teams that do not need SQL joins with relational data.

**Trade-off vs TimescaleDB:** InfluxDB is faster for pure time-series workloads but cannot do SQL joins. TimescaleDB is slower for pure time-series but gives you the full PostgreSQL ecosystem.

---

## Graph Databases

When your data is defined by relationships and your queries traverse those relationships, a graph database can be orders of magnitude faster than SQL JOINs.

### When Graphs Beat SQL

SQL can represent graphs (adjacency tables with foreign keys), but multi-hop traversals become painful:

```sql
-- Find friends of friends in SQL
SELECT DISTINCT f2.friend_id
FROM friendships f1
JOIN friendships f2 ON f1.friend_id = f2.user_id
WHERE f1.user_id = 123 AND f2.friend_id != 123;

-- Friends of friends of friends? Add another JOIN.
-- 6 degrees of separation? 6 JOINs. Performance collapses.
```

In a graph database, this is a simple traversal:

```cypher
-- Neo4j Cypher
MATCH (u:User {id: 123})-[:FRIENDS*1..3]-(fof:User)
RETURN DISTINCT fof
```

**Use a graph database when:**
- Your queries involve variable-depth traversals (social networks, recommendation engines).
- Relationships are first-class citizens with their own properties.
- You have pathfinding queries (shortest path, connected components).
- The data structure is highly connected and irregular.

**Do NOT use a graph database when:**
- Your queries are primarily key-value lookups or range scans.
- You need strong ACID transactions across many entities.
- Your data is tabular/rectangular with predictable JOINs.

### Neo4j

The most mature graph database. Property graph model.

**Key concepts:**
- **Nodes:** Entities with labels and properties.
- **Relationships:** Directed, typed connections between nodes with properties.
- **Cypher:** Declarative query language for pattern matching.

**Operational considerations:**
- Single-machine performance is excellent for graphs that fit in memory.
- Clustering (Neo4j Fabric) for larger graphs, but query routing is complex.
- Not designed for high write throughput -- better for read-heavy graph traversals.

### Amazon Neptune

Managed graph database on AWS. Supports both property graph (Gremlin) and RDF (SPARQL).

**When to choose Neptune over Neo4j:**
- You are in the AWS ecosystem and want managed operations.
- You need multi-AZ availability out of the box.
- Your graph fits the supported scale (up to ~64 TB).

---

## Vector Databases

Vector databases store and search high-dimensional vectors. They are fundamental to AI/ML applications -- semantic search, recommendation, RAG (Retrieval-Augmented Generation).

### How Vector Search Works

Instead of exact matching (SQL WHERE clause) or full-text search (inverted index), vector search finds the nearest neighbors in a high-dimensional space.

```
Text "How do I reset my password?"
  -> Embedding model -> [0.12, -0.34, 0.56, ..., 0.78] (1536 dimensions for OpenAI)

Query: Find the 5 most similar documents to this vector
  -> Approximate Nearest Neighbor (ANN) search
  -> Returns documents with vectors closest to the query vector
```

**ANN algorithms:**
- **HNSW (Hierarchical Navigable Small World):** Graph-based. Best recall/speed trade-off. Memory-intensive (stores the full graph in memory). Used by pgvector, Pinecone, Weaviate.
- **IVF (Inverted File Index):** Cluster-based. Faster to build, less memory. Lower recall than HNSW at the same speed. Used by FAISS.
- **Scalar/Product Quantization:** Compress vectors to reduce memory. Trade-off is reduced precision.

### Pinecone

Fully managed vector database. Serverless option available.

**Key properties:**
- No infrastructure management.
- Metadata filtering (combine vector search with traditional filters).
- Namespace isolation (multi-tenant support).
- Auto-scaling.

**When to use:** You want to move fast, do not want to manage infrastructure, and your scale justifies the cost. Production RAG applications, semantic search.

### pgvector

PostgreSQL extension for vector similarity search.

```sql
-- Enable the extension
CREATE EXTENSION vector;

-- Create a table with a vector column
CREATE TABLE documents (
    id BIGINT PRIMARY KEY,
    content TEXT,
    embedding vector(1536)  -- 1536-dimensional vector
);

-- Create an HNSW index
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);

-- Similarity search
SELECT id, content, embedding <=> '[0.12, -0.34, ...]'::vector AS distance
FROM documents
ORDER BY embedding <=> '[0.12, -0.34, ...]'::vector
LIMIT 5;
```

**When to use:** You are already on PostgreSQL, your vector dataset is moderate (< 10M vectors), and you want to combine vector search with SQL queries (JOINs, filters, transactions). Eliminates the need for a separate vector database.

**Trade-offs vs Pinecone:** pgvector is free, co-located with your relational data, and operationally simple. But it does not scale as well for pure vector workloads, and its ANN implementation is less optimized than purpose-built databases.

---

## Database Migration Strategies

Migrating databases is one of the most dangerous operations in production systems. The challenge is not moving the data -- it is doing it without downtime and without data loss.

### Dual-Write

Write to both the old and new database simultaneously.

```
Application -> Old Database (primary)
            -> New Database (shadow)
```

**Procedure:**
1. Deploy application code that writes to both databases.
2. Backfill historical data from old to new.
3. Verify data consistency between both databases.
4. Gradually shift reads to the new database.
5. When confident, stop writing to the old database.

**Problems:**
- Keeping both databases in sync is hard. What if one write succeeds and the other fails? You need transactional outbox or retry mechanisms.
- Performance impact -- every write now takes twice as long (or uses async writes, which introduces consistency risk).
- Backfill while dual-writing is tricky -- you need to handle updates to records that are being backfilled.

### Shadow Reads

Route a percentage of read traffic to the new database and compare results with the old database.

```
Application -> Old Database (serves the response)
            -> New Database (comparison only, response discarded)
            -> Compare results, log differences
```

**Why this matters:** It validates that the new database returns correct results before you trust it. Differences reveal data migration bugs, query compatibility issues, or behavioral differences between databases.

### Strangler Fig Migration

Incrementally route traffic from old to new, endpoint by endpoint or feature by feature.

```
Phase 1: 100% old, 0% new
Phase 2: Route /api/users to new, everything else to old
Phase 3: Route /api/users and /api/orders to new
Phase 4: 0% old, 100% new
Phase 5: Decommission old database
```

**Why this is usually the best choice:** Each phase is a small, reversible step. You can pause the migration if issues arise. Each phase delivers incremental confidence.

### CDC (Change Data Capture)

Stream changes from one database to another in real-time.

**Debezium** is the most widely used CDC tool. It reads the database's transaction log (WAL in PostgreSQL, binlog in MySQL) and emits change events to Kafka.

```
PostgreSQL WAL -> Debezium -> Kafka -> Consumer -> New Database
```

**Why CDC over dual-write:**
- No application code changes needed (reads the transaction log directly).
- Captures all changes, including those from other applications, scripts, or manual queries.
- Preserves ordering within a partition.
- Can replay from a specific point in time.

**Operational considerations:**
- Debezium needs access to the database's replication stream (configure as a logical replication slot in PostgreSQL).
- Schema changes in the source database must be handled carefully (schema registry).
- Monitoring is critical -- if the CDC pipeline falls behind, you accumulate lag.
- The replication slot prevents PostgreSQL from reclaiming WAL segments, which can fill up disk if the consumer is down.

---

## Distributed Transactions

When data spans multiple databases or services, maintaining consistency requires distributed transaction patterns.

### Two-Phase Commit (2PC)

The classic protocol for distributed transactions.

**Phase 1 (Prepare):**
- Coordinator asks all participants: "Can you commit this transaction?"
- Each participant does the work (but does not commit) and responds Yes or No.

**Phase 2 (Commit/Abort):**
- If all participants said Yes: Coordinator sends "Commit" to all.
- If any participant said No: Coordinator sends "Abort" to all.

**Problems:**
- **Blocking:** If the coordinator crashes after Phase 1 but before Phase 2, participants are stuck holding locks, waiting for a decision that never comes.
- **Latency:** Two network round trips plus disk flushes at each participant.
- **Availability:** Any participant being unavailable blocks the entire transaction.
- **Scalability:** Does not scale well -- more participants means more failure modes and more latency.

**When to use:** Homogeneous database environments where all participants are the same database (e.g., sharded PostgreSQL). Use sparingly -- it is a bottleneck by nature.

### Saga Pattern

A sequence of local transactions, each with a compensating action for rollback.

**Choreography (event-driven):**
```
Order Service: Create order (pending) -> emit OrderCreated
Payment Service: Process payment -> emit PaymentProcessed
Inventory Service: Reserve items -> emit ItemsReserved
Order Service: Confirm order -> emit OrderConfirmed

If PaymentProcessed fails:
  Order Service: Cancel order (compensating action)

If ItemsReserved fails:
  Payment Service: Refund payment (compensating action)
  Order Service: Cancel order (compensating action)
```

**Orchestration (centralized coordinator):**
```
Saga Orchestrator:
  1. Tell Order Service: Create order
  2. Tell Payment Service: Process payment
  3. Tell Inventory Service: Reserve items
  4. If any step fails, execute compensating actions in reverse order
```

**Choreography vs Orchestration:**

| Aspect | Choreography | Orchestration |
|--------|-------------|---------------|
| Coupling | Loose (events) | Tighter (orchestrator knows all steps) |
| Visibility | Hard to trace the full saga | Easy (orchestrator has the full picture) |
| Complexity | Distributed logic, harder to reason about | Centralized logic, easier to understand |
| Single point of failure | None | Orchestrator |
| Best for | Simple sagas, 2-3 steps | Complex sagas, many steps, conditional logic |

**Compensating actions are not rollbacks.** They are new actions that undo the effect of a previous action. This means:
- They must be idempotent (safe to retry).
- They may not perfectly undo the original action (a refund is not the same as "payment never happened" -- the user saw a charge and then a refund).
- Some actions cannot be compensated (sending an email, charging a credit card). Design around this by deferring irreversible actions to the end of the saga.

---

## Putting It Together: Choosing the Right Database

### Decision Flowchart

```
Start: What is your primary access pattern?

Key-value lookups by ID?
  -> High scale needed? -> DynamoDB / Redis
  -> Moderate scale?    -> PostgreSQL (it handles KV lookups fine)

Relational queries with JOINs?
  -> Single region, < 10 TB?     -> PostgreSQL
  -> Multi-region, need SQL?     -> CockroachDB / Spanner
  -> Need horizontal write scale? -> CockroachDB / TiDB

Time-series data?
  -> Already on PostgreSQL?     -> TimescaleDB extension
  -> Dedicated time-series need? -> InfluxDB / TimescaleDB (standalone)

Graph traversals?
  -> Variable-depth relationships? -> Neo4j / Neptune
  -> Fixed-depth (< 3 hops)?     -> PostgreSQL with recursive CTEs

Full-text search?
  -> Elasticsearch / OpenSearch

Vector similarity search?
  -> Already on PostgreSQL?     -> pgvector
  -> Dedicated high-scale need? -> Pinecone / Weaviate

High-throughput event streaming?
  -> Kafka (not a database, but often used as one)
  -> DynamoDB Streams / Cassandra

Blob storage?
  -> S3 / GCS (not a database, but foundational)
```

### The "Boring Technology" Principle

Every new database in your stack has a cost: operational knowledge, monitoring, backups, failover procedures, hiring people who know it, debugging production issues. Prefer a smaller number of well-understood databases over the perfect tool for every use case.

A good default stack for most applications:
- **PostgreSQL** for relational data and as the source of truth
- **Redis** for caching, rate limiting, and real-time data structures
- **S3** for blob storage
- **Elasticsearch** only if you need full-text search

Add specialized databases (DynamoDB, Cassandra, Neo4j, TimescaleDB) only when PostgreSQL genuinely cannot meet the requirements for a specific use case, and you have the team to operate the new technology.

---

## Key Takeaways

1. **NewSQL databases solve a real problem** -- horizontal scaling with ACID -- but they are not drop-in replacements for PostgreSQL. Evaluate the migration cost and operational complexity honestly.

2. **Time-series databases shine when your queries are time-range-centric.** TimescaleDB is the low-risk choice if you are already on PostgreSQL. InfluxDB is the choice for dedicated, high-throughput time-series workloads.

3. **Graph databases are a niche tool.** Most "graph problems" can be solved with PostgreSQL recursive CTEs. Reserve graph databases for variable-depth traversals over highly connected data.

4. **Vector databases are becoming essential for AI applications.** pgvector is good enough for moderate scale. Pinecone or Weaviate for dedicated, high-scale vector search.

5. **Database migrations are the hardest infrastructure problem.** Strangler fig with CDC is the safest general approach. Dual-write is tempting but fraught with consistency edge cases.

6. **Prefer Sagas over 2PC** for distributed transactions across microservices. Design compensating actions carefully -- they are the hardest part of the saga.

7. **Minimize the number of database technologies in your stack.** Each new technology has an operational tax. A boring stack that your team knows deeply will outperform an exciting stack that nobody can debug at 3 AM.
