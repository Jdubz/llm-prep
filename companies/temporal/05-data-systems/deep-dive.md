# Module 05 Deep Dive: Advanced Data Patterns

## Change Data Capture (CDC)

### PostgreSQL Logical Replication for CDC

PostgreSQL's logical replication decodes WAL changes into a structured stream of INSERT, UPDATE, and DELETE events.

```sql
-- Enable in postgresql.conf: wal_level = logical

-- Create a publication for billing tables
CREATE PUBLICATION billing_changes FOR TABLE
    metering_events, invoices, invoice_line_items, ledger_entries;

-- Create a logical replication slot
SELECT pg_create_logical_replication_slot('billing_cdc', 'pgoutput');
```

**REPLICA IDENTITY matters:** By default, UPDATE/DELETE events include only the primary key. For full before/after images (needed for audit trails):

```sql
ALTER TABLE metering_events REPLICA IDENTITY FULL;
-- Trade-off: increases WAL volume since the entire old row is written on every UPDATE
```

### Debezium for CDC

Debezium reads database change logs and produces structured events to Kafka/Kinesis. Advantages over native logical replication: handles schema evolution, manages replication slots, supports initial snapshots, and produces rich event envelopes with before/after images.

**Debezium event structure:**

```json
{
  "payload": {
    "before": null,
    "after": {
      "id": 12345, "tenant_id": "acme-corp",
      "event_type": "api_call", "quantity": 1
    },
    "source": {
      "table": "metering_events", "lsn": 234567890, "txId": 98765
    },
    "op": "c"
  }
}
```

The `op` field: `c` = create, `u` = update, `d` = delete, `r` = read (snapshot).

### CDC Use Cases for Billing

1. **OLTP to OLAP sync:** Replicate metering events from PostgreSQL to Redshift incrementally -- no full exports needed.
2. **Audit trails:** Immutable stream of every data change with before/after images.
3. **Cache invalidation:** Pricing plan changes in PostgreSQL trigger cache invalidation via CDC events.

### CDC Challenges

**Schema changes:** Adding a column changes the CDC event format. Consumers must handle both old and new schemas. Use a Schema Registry with Debezium.

**Ordering:** Within a transaction, changes are ordered. Across transactions, ordering follows commit order. Multi-table changes (insert event + update counter) may arrive at the consumer out of order. Use LSN for ordering.

**WAL accumulation:** If a consumer falls behind, PostgreSQL retains WAL until the consumer catches up. Monitor `pg_replication_slots` and set `max_slot_wal_keep_size` (PG 13+).

```sql
SELECT slot_name,
       pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)) AS lag
FROM pg_replication_slots;
```

---

## Data Consistency Across Systems

### OLTP vs OLAP Consistency

The same billing data exists across multiple systems with different lag characteristics:

```
PostgreSQL (authoritative)
    |  CDC: 1-5 seconds
    v
Kinesis / Kafka
    +-- Redshift (COPY from S3): 5-15 minutes behind
    +-- S3 (Firehose batch): 1-5 minutes behind
    +-- Real-time aggregator: 1-10 seconds behind
```

**Practical implications:** Usage dashboards (Redshift) may lag 5-15 minutes. Invoice generation must read from PostgreSQL. Support teams must know which system they are querying and its lag.

### Reconciliation

Periodic comparisons between systems to detect data loss or duplication:

```sql
-- Compare event counts per tenant per day between PostgreSQL and Redshift
-- Any mismatch indicates data loss or duplication
```

**Cadence:** Hourly lightweight counts. Daily per-tenant/per-event-type detail. Monthly full reconciliation before billing close.

### Distributed Transaction Patterns

**Saga pattern:** Break cross-system operations into local transactions with compensating actions. Invoice generation as a saga: create draft -> calculate charges -> create line items -> finalize -> send to payment processor -> publish event. If step N fails, execute compensations in reverse.

**Outbox pattern:** The most reliable pattern for "write to database AND publish event" atomicity.

```sql
BEGIN;
INSERT INTO invoices (tenant_id, total_amount_cents, status)
VALUES ('acme-corp', 50000, 'finalized');

INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type, payload)
VALUES ('invoice', currval('invoices_id_seq'), 'invoice.finalized',
        '{"tenant_id": "acme-corp", "amount_cents": 50000}');
COMMIT;
-- A separate process (CDC or poller) reads outbox_events and publishes to Kinesis
```

Why outbox beats direct publishing: either both the invoice and the event are written, or neither is. No dual-write inconsistency.

**Two-phase commit (2PC):** Rarely used in practice. Requires XA protocol support from all participants. Kinesis and S3 do not support it. The outbox pattern achieves the same goal with better operational characteristics.

### Exactly-Once in Practice

True exactly-once across distributed systems is impossible. We achieve "effectively once" through idempotency.

```sql
-- Idempotent event ingestion
INSERT INTO metering_events (tenant_id, event_type, quantity, idempotency_key)
VALUES ($1, $2, $3, $4)
ON CONFLICT (tenant_id, idempotency_key) DO NOTHING;
```

**Idempotent aggregation -- the critical distinction:**

```sql
-- WRONG: Increment is NOT idempotent (replay doubles the count)
UPDATE usage_summaries SET total_quantity = total_quantity + $3
WHERE tenant_id = $1 AND period_start = $2;

-- RIGHT: Recompute from source (replay produces the same result)
INSERT INTO usage_summaries (tenant_id, event_type, period_start, total_quantity, event_count)
SELECT tenant_id, event_type, date_trunc('hour', created_at),
       SUM(quantity), COUNT(*)
FROM metering_events
WHERE tenant_id = $1 AND created_at >= $2 AND created_at < $3
GROUP BY tenant_id, event_type, date_trunc('hour', created_at)
ON CONFLICT (tenant_id, event_type, period_start)
DO UPDATE SET total_quantity = EXCLUDED.total_quantity,
              event_count = EXCLUDED.event_count,
              computed_at = NOW();
```

---

## Pipeline Reliability

### Exactly-Once with Kinesis

**Checkpointing strategy:** Process batch -> write to PostgreSQL with idempotency keys -> checkpoint last sequence number. Never checkpoint before processing completes. On crash: replay from last checkpoint; idempotency keys prevent double-counting.

**Shard splits/merges:** KCL handles shard reassignment automatically. Checkpoint state is preserved in DynamoDB. No data loss if the parent shard was fully checkpointed before split.

### Backpressure Management

When downstream cannot keep up:

| Strategy | Implementation | Trade-off |
|---|---|---|
| In-stream buffering | Let Kinesis retain records (up to 7 days) | Extended retention cost |
| Adaptive batch sizing | Larger batches when fast, smaller when slow | Complexity |
| Circuit breaker | Stop processing, let events buffer | Latency spike |

**Circuit breaker states:** CLOSED (normal) -> OPEN (5 consecutive failures or p99 > 2s) -> HALF-OPEN (test 10 records after 30s) -> CLOSED or back to OPEN.

### Late-Arriving Data

**Watermarks:** Declare "all events before this time have arrived." Events after the watermark are late.

| Pipeline Stage | Late Event Handling |
|---|---|
| Kinesis ingestion | Always accept |
| PostgreSQL ingestion | Always insert (idempotency prevents dupes) |
| Hourly aggregation | Re-aggregate the affected hour |
| Invoice (draft) | Include in current draft |
| Invoice (finalized) | Adjustment on next billing cycle |

**Reprocessing trigger:** When a late event arrives, mark the affected aggregation window as stale:

```sql
INSERT INTO aggregation_queue (tenant_id, event_type, period_start, queued_at)
VALUES ($1, $2, date_trunc('hour', $3), NOW())
ON CONFLICT (tenant_id, event_type, period_start) DO UPDATE SET queued_at = NOW();
```

### Pipeline Testing

**Data quality assertions at stage boundaries:**

```sql
-- No future timestamps (clock skew)
SELECT COUNT(*) FROM staging_events WHERE created_at > NOW() + INTERVAL '5 minutes';

-- Daily volume within expected range
SELECT CASE
    WHEN today_count < avg_30d * 0.5 THEN 'ANOMALY_LOW'
    WHEN today_count > avg_30d * 2.0 THEN 'ANOMALY_HIGH'
    ELSE 'NORMAL' END AS status
FROM ...;
```

**Contract testing:** Verify producer output schema matches consumer expectations. Event types must be from an allowed set. Required fields must be non-null.

**Shadow pipelines:** Run new pipeline version in parallel. Both consume the same input. Compare outputs:

```sql
SELECT p.tenant_id, p.event_type, p.period_start,
       p.total_quantity AS prod, s.total_quantity AS shadow,
       p.total_quantity - s.total_quantity AS delta
FROM usage_summaries p
FULL OUTER JOIN usage_summaries_shadow s
    ON p.tenant_id = s.tenant_id
    AND p.event_type = s.event_type
    AND p.period_start = s.period_start
WHERE p.total_quantity IS DISTINCT FROM s.total_quantity;
```

---

## Data Modeling for Billing

### Metering Events Schema

Design principles: **immutable** (append-only, never update), **denormalized** (self-describing, no JOINs for basic processing), **partitioned** (by created_at), **idempotent** (unique idempotency_key).

```sql
CREATE TABLE metering_events (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    tenant_id       TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    quantity        BIGINT NOT NULL DEFAULT 1,
    unit            TEXT NOT NULL DEFAULT 'count',
    idempotency_key TEXT NOT NULL,
    source_service  TEXT NOT NULL,
    source_region   TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    event_timestamp TIMESTAMPTZ NOT NULL,        -- When usage occurred
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- When we received it
    CONSTRAINT metering_events_pkey PRIMARY KEY (id, created_at),
    CONSTRAINT metering_events_idempotency UNIQUE (tenant_id, idempotency_key, created_at)
) PARTITION BY RANGE (created_at);
```

### Aggregation Tables

Pre-compute summaries to avoid scanning billions of raw events at invoice time:

```sql
CREATE TABLE usage_hourly (
    tenant_id TEXT NOT NULL, event_type TEXT NOT NULL,
    hour TIMESTAMPTZ NOT NULL,
    total_quantity BIGINT NOT NULL, event_count BIGINT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, event_type, hour)
);

-- Daily and monthly rollups follow the same pattern
-- Monthly rollup feeds directly into invoice generation
```

**Materialized views** are simpler but `REFRESH CONCURRENTLY` rewrites the entire view. For large datasets, incremental aggregation into tables is more efficient.

### Billing Ledger: Double-Entry Bookkeeping

Every financial transaction recorded as balanced debit and credit entries:

```sql
CREATE TABLE ledger_entries (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    account_type TEXT NOT NULL,  -- 'receivable', 'revenue', 'credit_balance', 'cash'
    entry_type   TEXT NOT NULL,  -- 'debit' or 'credit'
    amount_cents BIGINT NOT NULL,
    description  TEXT NOT NULL,
    reference_type TEXT NOT NULL,
    reference_id   TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by   TEXT NOT NULL
);

-- Invoice finalized for $500: debit receivable, credit revenue
-- Payment received: debit cash, credit receivable
-- Refund: debit revenue, credit cash

-- Balance check:
SELECT account_type,
       SUM(CASE WHEN entry_type = 'debit' THEN amount_cents ELSE -amount_cents END) AS balance
FROM ledger_entries WHERE tenant_id = $1
GROUP BY account_type;
```

**Why double-entry:** Self-balancing (debits = credits, easy to verify). Reversals are explicit new entries, not deletions. Financial reporting (AR aging, revenue recognition) comes naturally.

### Audit Trail Tables

```sql
CREATE TABLE audit_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   TEXT NOT NULL,
    action      TEXT NOT NULL,
    actor_type  TEXT NOT NULL,
    actor_id    TEXT NOT NULL,
    changes     JSONB,       -- {"field": {"old": "draft", "new": "finalized"}}
    context     JSONB,       -- Request ID, IP, user agent
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prevent modifications with a trigger
CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

---

## Operational Excellence

### PostgreSQL Monitoring

**pg_stat_statements** -- the most important extension:

```sql
-- Top queries by total execution time
SELECT LEFT(query, 100), calls, mean_exec_time::NUMERIC(12,2) AS mean_ms,
       ROUND(shared_blks_hit::NUMERIC / NULLIF(shared_blks_hit + shared_blks_read, 0) * 100, 2) AS cache_hit_pct
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 10;
```

**Connection monitoring:** Watch `pg_stat_activity` for long-running queries (> 30s) and blocked queries waiting for locks.

**Replication lag:**

```sql
SELECT client_addr,
       pg_size_pretty(pg_wal_lsn_diff(sent_lsn, replay_lsn)) AS replay_lag
FROM pg_stat_replication;
```

### Kinesis Monitoring

| Metric | Healthy | Critical |
|---|---|---|
| IteratorAgeMilliseconds | < 60s | > 1 hour (data loss risk) |
| WriteProvisionedThroughputExceeded | 0 | Any (shard at capacity) |
| ReadProvisionedThroughputExceeded | 0 | Too many consumers sharing a shard |
| IncomingBytes per shard | < 800 KB/s | Sustained > 900 KB/s |
| GetRecords.Success | > 99.9% | < 99% (consumer health issue) |

**Iterator age is the most critical metric.** It measures how far behind the consumer is from the tip of the stream. If it approaches the retention period, data loss is imminent because records will expire before being processed.

**Iterator age thresholds:**
- < 1 minute: Healthy (real-time processing)
- 1-5 minutes: Warning (consumer may be slow)
- 5-30 minutes: Alert (investigate consumer health, PostgreSQL bottleneck, or shard hot-spotting)
- \> 1 hour: Critical (risk of data loss if retention is 24h)

**Resharding:** Monitor write utilization (`IncomingBytes / (1 MB/s * shard_count)`). Split hot shards when utilization exceeds 80%. Merge cold shards when below 20%. Use Kinesis on-demand mode for automatic scaling (~15% cost premium over provisioned).

### Data Quality Frameworks

**Great Expectations / dbt tests:** Define expectations at pipeline boundaries:
- `not_null` on tenant_id, event_type, quantity, idempotency_key
- `accepted_values` for event_type (must be in the set of billable dimensions)
- `accepted_range` for quantity (0 to 1M -- anything higher is likely a bug)
- Row count between expected bounds (50% to 200% of 30-day average)
- No duplicate idempotency keys within a batch
- All tenant_ids reference valid entries in the tenants table

**dbt test example for Redshift:**

```yaml
models:
  - name: usage_monthly
    columns:
      - name: tenant_id
        tests:
          - not_null
          - relationships:
              to: ref('tenants')
              field: id
      - name: total_quantity
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
```

### Incident Response

**Data corruption (double-counted events):**
1. Pause invoice generation for affected tenant
2. Query raw events in S3 (source of truth)
3. Compare raw count vs aggregated count to identify discrepancy
4. Re-run aggregation from raw events for the affected period
5. Void incorrect invoice, generate corrected one
6. Add reconciliation alert to detect this class of issue automatically

**Pipeline failure (Kinesis consumer down):**
1. Check consumer logs and PostgreSQL connection health
2. Restart consumer; it resumes from last checkpoint
3. Idempotency keys prevent double-counting during replay
4. Monitor iterator age returning to healthy levels
5. Run reconciliation for the affected time period
6. Post-incident: compare producer put metrics vs consumer processed metrics to verify no data was lost

**Consistency break (Redshift != PostgreSQL):**
1. PostgreSQL is authoritative -- determine the scope and magnitude of the delta
2. Check CDC pipeline lag, connector status, and error logs
3. For small gaps: re-run CDC for the affected time range
4. For large gaps: COPY from S3 archive (full reload of affected tables/partitions)
5. Verify counts match within tolerance (< 0.01%)
6. Add automated hourly reconciliation with alerting on any discrepancy
