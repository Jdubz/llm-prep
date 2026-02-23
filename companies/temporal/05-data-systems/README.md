# Module 05: Data Systems for Billing & Metering

## Overview

Temporal's billing and metering infrastructure spans a heterogeneous data stack: PostgreSQL for transactional billing data, Redshift for analytics and reporting, Kinesis for real-time event streaming, and object storage (S3/GCS/Azure Blob) for durable, multi-cloud data archival. This module covers each system with emphasis on the patterns that matter for metering at scale: high-throughput event ingestion, accurate aggregation, pipeline reliability, and cost-efficient storage.

---

## Table of Contents

1. [PostgreSQL at Scale](#postgresql-at-scale)
2. [Redshift (OLAP)](#redshift-olap)
3. [Kinesis (Streaming)](#kinesis-streaming)
4. [Object Storage (S3/GCS/Azure Blob)](#object-storage-s3gcsazure-blob)
5. [Data Pipeline Patterns](#data-pipeline-patterns)
6. [Interview Questions](#interview-questions)

---

## PostgreSQL at Scale

### Indexing Strategies

| Query Pattern | Index Type | Example |
|---|---|---|
| Equality + range | B-tree (default) | `WHERE tenant_id = $1 AND ts > $2` |
| Pure equality (rare) | Hash | `WHERE idempotency_key = $1` |
| JSONB containment | GIN | `WHERE metadata @> '{"plan": "enterprise"}'` |
| Range overlap | GiST | `WHERE tstzrange(start, end) && tstzrange($1, $2)` |
| Filtered subset | Partial B-tree | `WHERE processed = false` |
| Avoiding heap lookups | Covering (INCLUDE) | High-frequency read paths |

**Partial indexes** are critical for billing -- most queries touch a small active subset:

```sql
-- Only ~5% of rows are unprocessed at any time, so this index is 20x smaller
CREATE INDEX idx_events_unprocessed
    ON metering_events (tenant_id, created_at)
    WHERE processed = false;
```

**Covering indexes** eliminate heap lookups for hot paths:

```sql
CREATE INDEX idx_events_covering
    ON metering_events (tenant_id, created_at DESC)
    INCLUDE (quantity, event_type);
```

### Query Optimization

Use `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` on every critical query. Key signals:

- **Seq Scan on a large table**: Missing or unused index (but seq scans on <10K rows are fine)
- **Estimated vs actual rows diverge**: Stale statistics -- run `ANALYZE`
- **High buffer reads vs hits**: Working set exceeds shared_buffers
- **External merge sort**: Sort spilled to disk -- increase `work_mem` or add index

```sql
-- BAD: Function on indexed column prevents index usage
SELECT * FROM metering_events WHERE DATE(created_at) = '2025-01-15';
-- GOOD: Range condition uses the B-tree index
SELECT * FROM metering_events
WHERE created_at >= '2025-01-15' AND created_at < '2025-01-16';
```

### Partitioning

**Range by date** -- the standard choice for time-series metering data:

```sql
CREATE TABLE metering_events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    tenant_id       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    quantity        BIGINT NOT NULL DEFAULT 1,
    idempotency_key TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE metering_events_2025_01
    PARTITION OF metering_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

Why: billing queries always filter by time period. Partition pruning eliminates entire months. Old partitions can be detached and archived.

**List by tenant** -- when a few large tenants need isolation for per-tenant VACUUM or archival.

**Hash** -- even distribution across partitions when no natural range key exists. Trade-off: no partition pruning on range queries.

| Factor | Range (date) | List (tenant) | Hash |
|---|---|---|---|
| Time-series queries | Excellent pruning | No pruning | No pruning |
| Tenant isolation | No isolation | Per-tenant partitions | No isolation |
| Data archival | Drop old partitions | Drop tenant partitions | Difficult |
| Distribution | Skewed by activity | Skewed by tenant size | Even |

### Connection Pooling

PostgreSQL forks ~5-10 MB per connection. **PgBouncer** multiplexes many app connections onto fewer database connections.

| Pool Mode | Description | Limitation |
|---|---|---|
| **Transaction** | Connection returned after each transaction | No session-level features |
| **Session** | Held for entire client session | Less multiplexing benefit |
| **Statement** | Returned after each statement | No multi-statement transactions |

**Sizing:** Reserve 10-20% of `max_connections` for admin. Divide the rest across application instances.

### Transactions and Isolation Levels

- **Read Committed (default):** Sufficient for most billing operations. Each statement sees latest committed data.
- **Repeatable Read:** Snapshot from transaction start. Use for invoice generation -- consistent view of all charges.
- **Serializable:** Full isolation. Must retry on `40001` errors.

**Advisory locks** for cross-process coordination:

```sql
-- Prevent two processes from generating the same invoice concurrently
SELECT pg_advisory_lock(hashtext('invoice:acme-corp:2025-01'));
-- ... generate invoice ...
SELECT pg_advisory_unlock(hashtext('invoice:acme-corp:2025-01'));
```

### VACUUM and Bloat

Metering tables have high write rates (millions of events/day). Tune autovacuum aggressively:

```sql
ALTER TABLE metering_events SET (
    autovacuum_vacuum_scale_factor = 0.01,      -- Default 20% is too high
    autovacuum_vacuum_cost_delay = 2,
    autovacuum_analyze_scale_factor = 0.005,
    autovacuum_vacuum_insert_scale_factor = 0.01 -- PG 13+
);
```

Monitor with `pg_stat_user_tables`: watch `n_dead_tup / n_live_tup` ratio and `last_autovacuum`.

### Replication

- **Streaming replication:** Byte-level WAL shipping for HA and read replicas. Route reporting queries to replicas; keep primary for writes.
- **Logical replication:** Row-level change publishing. Used for CDC pipelines to Redshift and cross-version upgrades.

### PostgreSQL for Billing: Schema Design

```sql
-- Core metering events: immutable, append-only, high-volume
CREATE TABLE metering_events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    tenant_id       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    quantity        BIGINT NOT NULL DEFAULT 1,
    metadata        JSONB,
    idempotency_key TEXT NOT NULL,
    source          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT metering_events_idempotency UNIQUE (tenant_id, idempotency_key)
) PARTITION BY RANGE (created_at);

-- Pre-aggregated hourly summaries
CREATE TABLE usage_summaries (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id   TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end  TIMESTAMPTZ NOT NULL,
    total_quantity BIGINT NOT NULL,
    event_count    BIGINT NOT NULL,
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT usage_summaries_unique UNIQUE (tenant_id, event_type, period_start)
);

-- Invoices and line items
CREATE TABLE invoices (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    billing_period_start TIMESTAMPTZ NOT NULL,
    billing_period_end   TIMESTAMPTZ NOT NULL,
    total_amount_cents   BIGINT NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    status          TEXT NOT NULL DEFAULT 'draft',
    finalized_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE invoice_line_items (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id      BIGINT NOT NULL REFERENCES invoices(id),
    event_type      TEXT NOT NULL,
    quantity        BIGINT NOT NULL,
    unit_price_cents BIGINT NOT NULL,
    amount_cents    BIGINT NOT NULL
);

-- Billing ledger: double-entry bookkeeping
CREATE TABLE ledger_entries (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    entry_type      TEXT NOT NULL,
    amount_cents    BIGINT NOT NULL,
    balance_after_cents BIGINT NOT NULL,
    reference_type  TEXT,
    reference_id    BIGINT,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Key decisions:** Amounts in cents (BIGINT) to avoid floating-point errors. Idempotency keys prevent double-counting. Pre-aggregate summaries to avoid scanning raw events at invoice time. Ledger entries are append-only for auditability.

---

## Redshift (OLAP)

### Columnar Storage

| Characteristic | Row Store (PostgreSQL) | Column Store (Redshift) |
|---|---|---|
| Best for | OLTP: single-row lookups, writes | OLAP: aggregation, scans |
| INSERT speed | Fast (append) | Slow (write to each column file) |
| Aggregate queries | Slow (reads entire rows) | Fast (reads only needed columns) |
| Compression | Moderate | Excellent (10-100x) |
| Concurrent writes | Excellent | Poor (batch loads) |

### Distribution Styles

**KEY:** Co-locates rows with the same distribution key on one node. Use `tenant_id` as DISTKEY for billing -- most queries filter/group by tenant.

**ALL:** Copies entire table to every node. Use for small dimension tables (< 1M rows) like `pricing_plans`.

**EVEN:** Round-robin. Use when there is no natural join key.

```sql
CREATE TABLE metering_events (
    event_id    BIGINT IDENTITY(1,1),
    tenant_id   VARCHAR(255) NOT NULL,
    event_type  VARCHAR(100) NOT NULL,
    quantity    BIGINT NOT NULL,
    created_at  TIMESTAMP NOT NULL
)
DISTSTYLE KEY DISTKEY (tenant_id) SORTKEY (created_at);
```

### Sort Keys

**Compound:** Queries must filter on leading prefix (like a B-tree). Use `(tenant_id, created_at)` for billing.

**Interleaved:** Any column subset benefits. Trade-off: VACUUM REINDEX is expensive.

### Loading Data

Always use COPY from S3, never row-by-row INSERT:

```sql
COPY metering_events
FROM 's3://billing-data-lake/metering/2025/01/'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftCopyRole'
FORMAT AS PARQUET;
```

Split files to match Redshift slice count. Use Parquet over CSV. Compress with GZIP.

### Redshift Spectrum

Query S3 data directly without loading. Use for infrequent historical queries (ad-hoc investigation, annual reports). Trade-off: Spectrum charges per TB scanned; Redshift storage is pre-paid.

```sql
CREATE EXTERNAL SCHEMA billing_archive
FROM DATA CATALOG DATABASE 'billing_archive'
IAM_ROLE 'arn:aws:iam::123456789012:role/RedshiftSpectrumRole';

SELECT tenant_id, event_type, SUM(quantity) AS total
FROM billing_archive.metering_events_2023
WHERE created_at >= '2023-01-01' AND created_at < '2023-04-01'
GROUP BY tenant_id, event_type;
```

---

## Kinesis (Streaming)

### Kinesis Data Streams

Core concepts: streams contain shards. Each shard supports 1 MB/s write, 2 MB/s read, 1000 records/s. Partition key determines shard assignment and ordering guarantee. Retention: 24h default, up to 365 days.

**Capacity planning for billing:**

```
Avg event size: 500 bytes
Write limit per shard: 1 MB/s = ~2,000 events/s
For 100K events/second: ~50 shards (~$1,800/month on-demand)
```

**Partition key strategy:** Use `tenant_id` for per-tenant ordering. For hot tenants, add a random suffix (`acme-corp-3`) to spread across shards -- trade-off: lose ordering.

### Kinesis Data Firehose

Zero-code delivery pipe. Batches records and writes to S3/Redshift/Elasticsearch.

```
Source: Kinesis Data Stream (metering-events)
Destination: S3 (s3://billing-data-lake/raw/metering/)
Buffer: 64 MB or 300 seconds
Compression: GZIP
Format: JSON to Parquet (via Glue)
Partitioning: year/month/day/hour prefix
```

### Consumer Patterns

| Consumer | Purpose | Pattern |
|---|---|---|
| Aggregation service | Real-time usage counts | KCL, write to PostgreSQL |
| Archive pipeline | Durable storage | Firehose to S3 |
| Anomaly detector | Spike detection | KCL, sliding window |
| Billing trigger | Threshold alerts | KCL, compare against quotas |

**Enhanced fan-out:** Dedicated 2 MB/s per consumer per shard. Use when multiple consumers read the same stream.

### Exactly-Once Processing

Kinesis provides at-least-once. Achieve exactly-once through:

1. **Idempotency keys:** `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING`
2. **Sequence number tracking:** Store last processed sequence per shard
3. **Deduplication window:** Redis SET with 24h TTL

Checkpoint only after successful processing. Never checkpoint first.

### Kinesis vs Kafka

| Feature | Kinesis | Kafka |
|---|---|---|
| Managed? | Fully (AWS) | Self-managed or Confluent |
| Throughput/unit | 1 MB/s per shard | Much higher per partition |
| Exactly-once | Application-level | Native transactions |
| Multi-cloud | AWS only | Runs anywhere |
| Ecosystem | Firehose, Lambda | Connect, Streams, ksqlDB |
| Operational burden | Zero | High (self) or medium (Confluent) |

---

## Object Storage (S3/GCS/Azure Blob)

### Lifecycle and Cost Tiers

| Tier | $/GB/month | Retrieval | Use Case |
|---|---|---|---|
| S3 Standard | $0.023 | Instant | Current month billing data |
| S3 Standard-IA | $0.0125 | Instant (higher per-req) | Previous months |
| S3 Glacier IR | $0.004 | Minutes | Quarterly/annual reports |
| S3 Glacier Deep | $0.00099 | 12-48 hours | 7-year compliance archives |

### Data Lake Architecture

```
s3://billing-data-lake/
  raw/                    -- Immutable source of truth. Never modify.
    metering/year=2025/month=01/day=15/hour=14/
  cleaned/                -- Deduplicated, schema-validated
    metering/year=2025/month=01/day=15/
  curated/                -- Pre-aggregated, business-logic applied
    usage_summaries/year=2025/month=01/
```

**Partitioning:** Hive-style (`year=2025/month=01/day=15/`). Daily is the sweet spot for billing. Target 128 MB - 1 GB per file to balance parallelism vs. listing overhead.

### Cross-Cloud Storage

Temporal operates multi-cloud (AWS, GCP, Azure). Patterns:
- Canonical format (Parquet) regardless of cloud
- Cloud-agnostic abstraction in application code
- Each cloud stores local metering data; aggregation in a designated analytics cloud
- Cross-cloud replication for centralized reporting

---

## Data Pipeline Patterns

### ETL vs ELT

| Approach | When | Billing Use Case |
|---|---|---|
| ETL | Target has limited compute | Aggregates into PostgreSQL |
| ELT | Target has powerful compute | Raw events into Redshift, SQL transforms |
| Streaming | Real-time requirements | Kinesis to live usage counters |

Billing pipelines typically use all three: streaming ingestion, ELT for analytics, ETL for invoice generation.

### Idempotent Pipelines

Every stage must be replay-safe:

1. **Ingestion:** Idempotency keys + `ON CONFLICT DO NOTHING`
2. **Aggregation:** Recompute from source (not `count = count + 1`)
3. **Invoice generation:** Key on `(tenant_id, billing_period)`, state machine prevents double-finalization
4. **S3 output:** Deterministic paths, atomic PUT

### Backfill Strategies

- **Parallel pipeline:** New logic alongside existing, compare outputs before switching
- **Date-range replay:** Process from S3 raw layer, one day at a time, idempotent writes
- **Shadow mode:** New logic on live data writing to shadow tables, compare with production

Always backfill from the raw/immutable layer. Rate-limit to avoid overwhelming downstream.

### Pipeline Monitoring

| Metric | Alert Threshold |
|---|---|
| Event lag | > 5 minutes |
| Input vs output count delta | > 0.1% discrepancy |
| Schema validation failures | > 0 |
| Processing latency (p99) | > 30 seconds |
| Output freshness | > 1 hour stale |

### Error Handling

**Dead letter queues:** Failed events go to DLQ after N retries. Never silently drop billing events.

**Poison pills:** Track per-record retry counts. After 3-5 failures, send to DLQ and advance checkpoint.

| Severity | Condition | Response |
|---|---|---|
| P1 | Pipeline stopped or DLQ > 1000 | Immediate investigation |
| P2 | Event lag > 15 minutes | Pipeline degradation |
| P3 | Intermittent validation failures | Data quality investigation |

---

## Interview Questions

### Conceptual

1. **Why partition metering_events by date rather than tenant_id?**
   Billing queries always filter by time period. Date partitioning enables partition pruning and clean archival (detach old partitions). Tenant partitioning adds management complexity proportional to tenant count.

2. **How do you prevent double-counting in a metering pipeline?**
   Client-generated idempotency keys. UNIQUE constraint + `ON CONFLICT DO NOTHING`. Checkpoint after successful write. Idempotent aggregation (recompute from source, not increment).

3. **When use Redshift Spectrum vs loading into Redshift?**
   Spectrum for infrequent historical queries (charges per TB scanned). Load data for repeated queries. If queried daily: load. If queried quarterly: Spectrum.

4. **How do you handle late-arriving metering events?**
   Grace period before invoice finalization (48h). Separate event_timestamp from ingestion timestamp. Post-finalization events become adjustments on the next cycle. Monitor late event volume for systemic issues.

### Design Challenges

5. **Design a pipeline for 100K metering events/second with exactly-once billing accuracy.**
   Kinesis (~50 shards, partition by tenant_id). KCL consumers write to PostgreSQL with idempotency keys. Firehose archives to S3 in Parquet. Hourly aggregation computes summaries. Monthly invoice reads summaries. Reconciliation compares S3 raw counts vs PostgreSQL aggregates.

6. **How would you migrate billing analytics from PostgreSQL to Redshift without downtime?**
   CDC from PostgreSQL to Redshift (Debezium). Backfill historical data from S3 via COPY. Shadow-run queries against both. Compare results. Switch reporting traffic. Keep CDC running.

7. **A tenant says their usage numbers are wrong. How do you investigate?**
   Start with raw events in S3. Check for duplicates and gaps. Compare counts at each pipeline stage (Kinesis producer metrics -> PostgreSQL ingestion -> aggregation -> invoice). Check timezone mismatches in period boundaries. Check if late events were excluded.
