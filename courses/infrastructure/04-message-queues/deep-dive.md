# Module 04: Message Queues & Event-Driven Architecture -- Deep Dive

## Table of Contents

1. [Kafka Internals](#kafka-internals)
2. [Outbox Pattern](#outbox-pattern)
3. [CDC with Debezium](#cdc-with-debezium)
4. [Event Schema Evolution](#event-schema-evolution)
5. [Comparing Message Brokers](#comparing-message-brokers)
6. [Stream Processing](#stream-processing)
7. [Event-Driven Microservices Patterns](#event-driven-microservices-patterns)

---

## Kafka Internals

### In-Sync Replicas (ISR)

Every partition has one leader and follower replicas. The ISR is the set of replicas "caught up" to the leader (fetched within `replica.lag.time.max.ms`, default 30s).

**`acks` configuration:**

- `acks=0`: No acknowledgment. Fastest, messages can be lost.
- `acks=1`: Leader acknowledges. If leader crashes before replication, data lost.
- `acks=all`: All ISR replicas acknowledge. Safest.

**`min.insync.replicas`**: With `acks=all`, minimum ISR replicas that must acknowledge. If ISR shrinks below this, producer gets an error.

```
Production configuration:
  acks=all, min.insync.replicas=2, replication.factor=3
  --> Tolerates 1 broker failure without data loss
  --> 2 broker failures: writes rejected, no data lost

Durability formula:
  Tolerate N failures = replication.factor >= N+1, min.insync.replicas >= N+1, acks=all
```

### Leader Election

**KRaft (Kafka 3.3+, replacing ZooKeeper):** Controller quorum using Raft consensus. On leader failure: controller detects via heartbeat, selects new leader from ISR (highest offset preferred), updates metadata, clients refresh.

**Unclean leader election** (`unclean.leader.election.enable`):
- `false` (default): Partition unavailable until ISR replica recovers. No data loss.
- `true`: Out-of-sync replica becomes leader. Available but unreplicated messages lost.

Classic CAP tradeoff. Disable for financial data, consider enabling for metrics/logs.

**Election latency**: With KRaft, leader election typically completes in 1-5 seconds. During this window, producers and consumers for affected partitions experience errors and must retry. Client libraries handle this automatically with retries, but your application should expect brief blips during broker failures.

**Preferred replica election**: Kafka tries to distribute partition leaders evenly across brokers. After a failure and recovery, run `kafka-leader-election.sh --all-topic-partitions` (or enable `auto.leader.rebalance.enable`) to restore balanced leadership distribution.

### Log Segments

Kafka stores data as log segments on disk.

```
/kafka-data/orders-0/
├── 00000000000000000000.log        # Segment 1: offsets 0-999
├── 00000000000000000000.index      # Sparse offset index
├── 00000000000000000000.timeindex  # Timestamp index
├── 00000000000000001000.log        # Segment 2 (closed, read-only)
└── 00000000000000002000.log        # Active segment (being written)
```

**Lifecycle**: Active segment receives writes. Rolls to new segment at `log.segment.bytes` (1GB) or `log.segment.ms`. Closed segments eligible for deletion per `log.retention.hours`.

**Key detail**: Retention operates on segments, not messages. If a segment spans 6 days and retention is 7 days, the entire segment is kept until its newest message exceeds retention.

**Index files**: Offset index maps offset to file position (O(1) seek). Timestamp index enables `offsetsForTimes()`.

### Zero-Copy

```
Normal transfer (4 copies, 2 context switches):
  Disk --> Page Cache --> User Buffer --> Socket Buffer --> NIC

Zero-copy via sendfile() (2 copies, 0 user-space switches):
  Disk --> Page Cache --> NIC (via scatter-gather DMA)
```

Kafka brokers never inspect message content -- opaque bytes pass through `sendfile()` directly from page cache to network. This is why brokers saturate 10Gbps NICs with modest CPU.

**Page cache leverage**: Kafka uses the OS page cache instead of JVM heap. Recent writes served from memory. Small JVM heap = no GC pauses. Caught-up consumers read entirely from memory.

**Implications for hardware selection**: Kafka brokers benefit more from large amounts of RAM (for page cache) and fast sequential I/O (SSDs or NVMe) than from many CPU cores. A typical production broker: 32-64GB RAM, NVMe SSDs, 4-8 cores. The JVM heap should be small (6-8GB) to leave the rest for page cache.

**Sequential I/O advantage**: Kafka reads and writes are sequential. Modern SSDs and HDDs achieve their highest throughput on sequential patterns. This is why Kafka can achieve higher throughput than databases that require random I/O for index lookups.

---

## Outbox Pattern

Solves: how to atomically update a database AND publish a message (two different systems, no distributed transaction).

```python
# BROKEN: DB write succeeds, Kafka publish fails
async def create_order(data):
    await db.insert("orders", data)
    await kafka.publish("orders", data)  # This can fail

# CORRECT: Both writes in same DB transaction
async def create_order(data):
    async with db.transaction():
        order_id = await db.insert("orders", data)
        await db.insert("outbox", {
            "id": uuid4(), "aggregate_type": "Order",
            "aggregate_id": order_id, "event_type": "OrderCreated",
            "payload": json.dumps(data), "created_at": datetime.utcnow()
        })
```

**Publishing from outbox**: Separate process polls outbox table, publishes to Kafka, marks as published. Or use CDC (Debezium) to stream outbox changes -- no polling, lower latency.

```sql
CREATE TABLE outbox (
    id             UUID PRIMARY KEY,
    aggregate_type VARCHAR(255) NOT NULL,
    aggregate_id   VARCHAR(255) NOT NULL,
    event_type     VARCHAR(255) NOT NULL,
    payload        JSONB NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    published      BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_outbox_unpublished ON outbox (created_at) WHERE published = FALSE;
```

---

## CDC with Debezium

Captures row-level changes from database transaction logs (PostgreSQL WAL, MySQL binlog, MongoDB oplog) and streams them to Kafka.

```
Database --> WAL/Binlog --> Debezium Connector --> Kafka Topics (one per table)
```

**Change event structure:**

```json
{
  "before": {"id": 123, "email": "old@example.com"},
  "after":  {"id": 123, "email": "new@example.com"},
  "op": "u",
  "source": {"table": "users", "lsn": 123456789}
}
```

Operations: `c`=create, `u`=update, `d`=delete, `r`=snapshot read.

**Use cases**: Outbox pattern (no polling), cache invalidation, search index sync, data warehouse replication, cross-service data sync.

**Debezium Outbox Event Router**: Dedicated transform that converts outbox table changes into properly structured domain events, routing by aggregate type.

**Operational considerations for Debezium:**

- **Snapshot on first start**: Debezium takes a full snapshot of each table before streaming changes. For large tables, this can take hours and put load on the source database. Use snapshot modes (`initial`, `schema_only`, `never`) to control this.
- **Slot management** (PostgreSQL): Debezium creates a replication slot. If Debezium is down for too long, WAL segments accumulate and can fill the disk. Monitor `pg_replication_slots` and set `max_slot_wal_keep_size`.
- **Schema changes**: DDL changes (ALTER TABLE) must be handled. Debezium captures schema changes, but downstream consumers must handle evolving schemas gracefully.

```
# PostgreSQL replication slot monitoring
SELECT slot_name, pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) AS lag_bytes
FROM pg_replication_slots;
```

---

## Event Schema Evolution

### Schema Registry

Stores and validates event schemas. Producer registers schema, gets ID. Messages carry schema ID + data. Consumer fetches schema by ID to deserialize.

### Avro vs Protobuf

| Dimension | Avro | Protobuf |
|-----------|------|----------|
| Schema location | External (registry) | Compiled into code |
| Dynamic schemas | Yes | No (generated code) |
| Ecosystem | Kafka-native | gRPC-native |
| Field identification | By name | By field number |

### Compatibility Modes

**Backward** (default): New schema reads old data. Allowed: add field with default, remove field. Forbidden: add required field without default.

**Forward**: Old schema reads new data. Allowed: remove field, add field. Forbidden: remove required field.

**Full**: Both backward and forward. Only add/remove fields with defaults.

**Practical strategies:**
1. **Adding a field**: Always provide default. Backward compatible.
2. **Removing**: Deprecate first, remove after consumers updated.
3. **Renaming**: Add new field, copy data, deprecate old. Never rename in-place.
4. **Type change**: New field with new type, populate both, transition, remove old.

---

## Comparing Message Brokers

| Dimension | Kafka | RabbitMQ | SQS | NATS JetStream |
|-----------|-------|----------|-----|----------------|
| **Model** | Distributed log | AMQP broker | Managed queue | Lightweight streaming |
| **Throughput** | Millions/sec | Tens of thousands/sec | Thousands/sec per queue | Hundreds of thousands/sec |
| **Latency (p99)** | 5-50ms | 1-10ms | 10-50ms | 1-5ms |
| **Ordering** | Per partition | Per queue | Per message group (FIFO) | Per stream |
| **Delivery** | At-least-once (EOS with tx) | At-least-once | At-least-once / exactly-once (FIFO) | At-least-once |
| **Retention** | Days/weeks | Until consumed | 4-14 days | Configurable |
| **Replay** | Yes | No | No | Yes |
| **Routing** | Partition key | Exchanges (direct/topic/fanout) | None | Subject wildcards |
| **Operations** | High | Medium | Zero | Low |

### Decision Framework

```
Need replay / event sourcing?           --> Kafka or NATS JetStream
Need complex routing / priorities?      --> RabbitMQ
AWS-native, zero ops?                   --> SQS/SNS
Need > 100K msg/sec?                    --> Kafka or NATS
Need < 5ms latency?                     --> NATS or RabbitMQ
Default: SQS (AWS), Kafka (streaming), RabbitMQ (routing)
```

---

## Stream Processing

### Kafka Streams vs Flink vs Spark Streaming

| Dimension | Kafka Streams | Apache Flink | Spark Streaming |
|-----------|---------------|--------------|-----------------|
| Deployment | Library (in your app) | Standalone cluster | Standalone cluster |
| Processing | Event-at-a-time | Event-at-a-time | Micro-batch |
| State | RocksDB + changelog | RocksDB + checkpoints | In-memory + checkpoints |
| Latency | Milliseconds | Milliseconds | Seconds |
| Source/Sink | Kafka only | Multi-source | Multi-source |
| Complexity | Low | High | Medium |

**Kafka Streams**: Already on Kafka, Kafka-to-Kafka processing, simplest deployment.

**Flink**: Complex event processing, multi-source, advanced windowing, large-scale stateful processing. Most powerful, highest operational cost.

**Spark Streaming**: Existing Spark cluster, batch + stream unification, ML pipelines.

### Stream Processing Patterns

**Stateless**: Filter, transform, enrich. Each event independent. Scales trivially.

**Stateful aggregation**: Count/sum in time windows. State in RocksDB, backed by changelog topics.

**Stream-stream join**: Match events from two streams within a time window (e.g., orders + payments).

**Stream-table join**: Enrich stream events with lookup table (e.g., orders + customers from compacted topic).

**Windowing strategies:**

| Window Type | Behavior | Use Case |
|-------------|----------|----------|
| Tumbling | Fixed-size, non-overlapping | Hourly aggregations, batch reports |
| Hopping | Fixed-size, overlapping (slides by hop) | Rolling averages |
| Sliding | Variable-size, event-triggered | Event correlation within time range |
| Session | Dynamic, gap-based (closes after inactivity) | User session analytics |

```
Tumbling (5 min):  [0:00-0:05] [0:05-0:10] [0:10-0:15]
Hopping (5 min window, 1 min hop):  [0:00-0:05] [0:01-0:06] [0:02-0:07]
Session (5 min gap):  [event...event...event] --5min gap-- [event...event]
```

**Late-arriving events**: In stream processing, events can arrive after their window has closed (network delays, producer retries). Configure allowed lateness to keep windows open longer, or use watermarks to track event time progress.

---

## Event-Driven Microservices Patterns

### Event Notification

Thin event: "something happened." Consumer calls back for details. Small payloads, but creates coupling (N consumers = N API calls).

### Event-Carried State Transfer

Event carries full data. Consumer operates without callback. Full decoupling, but larger payloads and producer must anticipate consumer needs.

### Shared Nothing

Each service maintains its own data copy, populated entirely from events. No cross-service API calls, no shared database.

```
Order Events --> Order Service (owns orders table)
             --> Search Service (projects to Elasticsearch index)
```

### Anti-Corruption Layer

Translate legacy/third-party events into your domain model. Isolates your system from external schema quirks and naming conventions.

### Transactional Outbox with Domain Events

The gold standard for reliable event publishing:

```python
class OrderService:
    async def create_order(self, command):
        async with db.transaction():
            order = Order.create(command)
            await order_repo.save(order)
            for event in order.domain_events:
                await outbox_repo.save(OutboxEntry(
                    aggregate_id=order.id,
                    event_type=event.__class__.__name__,
                    payload=event.to_json()
                ))
        return order
```

Business state and events are consistent (same transaction). Events published reliably by outbox publisher. Clean service boundary.

### Bulkhead Pattern

Isolate event consumers so failure in one does not affect others. Separate consumer groups, thread pools, DLQs, and circuit breakers per concern.

```
Event Bus --> Pool A (4 threads) --> Order Processing
          --> Pool B (2 threads) --> Email (SMTP slow? Only Pool B backs up)
          --> Pool C (2 threads) --> Analytics
```
