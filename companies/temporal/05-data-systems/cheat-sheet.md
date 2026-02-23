# Module 05 Cheat Sheet: Data Systems Quick Reference

## Storage System Comparison

| Feature | PostgreSQL | Redshift | Kinesis | S3 |
|---|---|---|---|---|
| **Type** | OLTP (row store) | OLAP (column store) | Stream buffer | Object store |
| **Best for** | Transactions, single-row ops | Aggregation, analytics | Real-time ingestion | Durable archival |
| **Latency** | < 10ms | Seconds to minutes | Milliseconds | 50-200ms |
| **Consistency** | ACID (strong) | Eventual (batch loads) | At-least-once | Strong (read-after-write) |
| **Scaling** | Vertical + read replicas | Add nodes | Add shards | Automatic |
| **Billing role** | Events, invoices, ledger | Usage reports, dashboards | Event ingestion | Raw event archive |

## PostgreSQL Index Type Decision Tree

```
Equality + range on scalars?  --> B-tree (add INCLUDE for index-only scans)
Querying inside JSONB?        --> GIN with jsonb_ops
Full-text or array search?    --> GIN
Range overlap (tstzrange)?    --> GiST
Only a subset of rows?        --> Partial index: WHERE condition
Avoid heap lookups?           --> Covering index: INCLUDE (col1, col2)
```

## PostgreSQL Partitioning Decision Tree

```
Table > 10 GB / 100M rows?
  No  --> Use indexes instead
  Yes --> Primary query filter?
    Time range?    --> PARTITION BY RANGE (created_at), monthly
    Tenant ID?     --> PARTITION BY LIST (tenant_id), only if < 100 large tenants
    Even spread?   --> PARTITION BY HASH (tenant_id), fixed count
```

## Kinesis vs Kafka

| Feature | Kinesis | Kafka |
|---|---|---|
| Managed | Fully (AWS) | Self-managed or Confluent |
| Capacity unit | Shard: 1 MB/s write | Partition: configurable, much higher |
| Exactly-once | Application-level | Native transactions |
| Retention | 24h - 365 days | Unlimited (tiered) |
| Multi-cloud | AWS only | Runs anywhere |
| Ecosystem | Firehose, Lambda | Connect, Streams, ksqlDB |

## Pipeline Pattern Comparison

| Pattern | ETL | ELT | Streaming |
|---|---|---|---|
| Transform | Before loading | After loading | During transit |
| Latency | Minutes-hours | Minutes | Seconds |
| Billing use | Aggregates to PostgreSQL | Raw events to Redshift | Kinesis to live counters |

## Common SQL Patterns for Billing

### Idempotent Event Ingestion

```sql
INSERT INTO metering_events (tenant_id, event_type, quantity, idempotency_key)
VALUES ($1, $2, $3, $4)
ON CONFLICT (tenant_id, idempotency_key) DO NOTHING RETURNING id;
```

### Idempotent Hourly Aggregation

```sql
INSERT INTO usage_hourly (tenant_id, event_type, hour, total_quantity, event_count)
SELECT tenant_id, event_type, date_trunc('hour', event_timestamp),
       SUM(quantity), COUNT(*)
FROM metering_events
WHERE tenant_id = $1 AND event_timestamp >= $2 AND event_timestamp < $3
GROUP BY tenant_id, event_type, date_trunc('hour', event_timestamp)
ON CONFLICT (tenant_id, event_type, hour)
DO UPDATE SET total_quantity = EXCLUDED.total_quantity,
              event_count = EXCLUDED.event_count, computed_at = NOW();
```

### Monthly Usage for Invoicing

```sql
SELECT event_type, SUM(total_quantity) AS total_usage
FROM usage_hourly
WHERE tenant_id = $1 AND hour >= $2 AND hour < $3
GROUP BY event_type;
```

### Tenant Ledger Balance

```sql
SELECT account_type,
       SUM(CASE WHEN entry_type = 'debit' THEN amount_cents ELSE -amount_cents END) AS balance
FROM ledger_entries WHERE tenant_id = $1
GROUP BY account_type;
```

### Usage Anomaly Detection (z-score > 3)

```sql
WITH recent AS (
    SELECT tenant_id, event_type, date_trunc('day', hour) AS day,
           SUM(total_quantity) AS daily_qty
    FROM usage_hourly WHERE hour >= NOW() - INTERVAL '30 days'
    GROUP BY tenant_id, event_type, date_trunc('day', hour)
),
stats AS (
    SELECT tenant_id, event_type, AVG(daily_qty) AS avg_qty,
           STDDEV(daily_qty) AS stddev_qty
    FROM recent WHERE day < CURRENT_DATE
    GROUP BY tenant_id, event_type
)
SELECT r.*, (r.daily_qty - s.avg_qty) / NULLIF(s.stddev_qty, 0) AS z_score
FROM recent r JOIN stats s USING (tenant_id, event_type)
WHERE r.day = CURRENT_DATE
  AND ABS((r.daily_qty - s.avg_qty) / NULLIF(s.stddev_qty, 0)) > 3;
```

## Redshift Optimization Checklist

```
[ ] DISTKEY on most frequent JOIN/GROUP BY column (tenant_id)
[ ] SORTKEY on most frequent WHERE filter (created_at)
[ ] Load with COPY from S3, never row-by-row INSERT
[ ] Use Parquet format, GZIP compression
[ ] Split files = number of Redshift slices
[ ] ANALYZE after large loads; VACUUM after large DELETEs
[ ] Small dimensions: DISTSTYLE ALL; large facts: DISTSTYLE KEY
[ ] Avoid SELECT * (columnar benefits require column pruning)
[ ] Spectrum for infrequent historical queries on S3
```

## Pipeline Monitoring Checklist

```
Ingestion (Kinesis):
[ ] Iterator age < 1 minute     [ ] No throughput exceeded errors
[ ] Shard utilization < 80%     [ ] Consumer error rate < 0.01%

Processing (PostgreSQL):
[ ] Pool utilization < 80%      [ ] p99 latency < 100ms
[ ] Dead tuple ratio < 5%       [ ] Replication lag < 5 seconds

Aggregation:
[ ] Completes within SLA        [ ] Output count within +-10% of average
[ ] No nulls in required cols   [ ] Sum(aggregated) = count(raw)

Data Quality:
[ ] No duplicate idempotency keys   [ ] No negative quantities
[ ] All tenant_ids valid            [ ] Timestamps in expected range

Delivery:
[ ] S3 files 128 MB - 1 GB     [ ] Redshift COPY 100% success
[ ] Freshness < 1 hour         [ ] Reconciliation delta < 0.01%
```

## Time-Series Data Modeling Patterns

**Pattern 1 -- Append + Aggregate (best for billing):** Immutable raw events -> hourly/daily summaries (idempotent upsert) -> invoice generation. Source of truth is raw events.

**Pattern 2 -- Pre-Aggregated Counters:** Increment on arrival. Fast for dashboards. Not idempotent without deduplication.

**Pattern 3 -- Lambda Architecture:** Speed layer (Kinesis -> Redis for real-time) + batch layer (S3 -> Redshift for accuracy). Merge for serving. High complexity.

## Key Thresholds

```
PostgreSQL: max_connections 100-500, shared_buffers 25% RAM, work_mem 256MB
Kinesis:    1 MB/s write per shard, 2 MB/s read, 1000 records/s, max record 1 MB
S3:         5,500 GET/s per prefix, 3,500 PUT/s, target 128MB-1GB file size
Redshift:   50 concurrent queries (WLM default), match COPY files to slice count
```

## Key Interview Answers

**Billing accuracy across systems?** Idempotency keys everywhere. S3 raw events as immutable source of truth. Reconciliation between PostgreSQL and Redshift. Double-entry ledger.

**Hot Kinesis shard?** Split shard, or add random suffix to partition key (lose ordering).

**Redshift vs PostgreSQL?** Redshift for aggregation over millions/billions of rows. PostgreSQL for transactional writes and point lookups.

**Idempotent aggregation?** Recompute from source (never increment). Use ON CONFLICT DO UPDATE with deterministic keys.

**Late metering events?** Grace period before invoice finalization. Post-finalization arrivals become adjustments on next cycle.

**Outbox pattern?** Write business data + event to outbox in one transaction. Separate process publishes from outbox. Avoids dual-write inconsistency.
