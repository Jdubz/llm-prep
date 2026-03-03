# Module 04: Message Brokers — Kafka, SQS, RabbitMQ

## Why Message Queues

**Decoupling**: Service A publishes to a queue. Service B consumes. A succeeds even if B is down.

**Load leveling**: Queues absorb traffic spikes. Consumers process at their own sustainable rate.

**Reliability**: Messages persist until acknowledged. Consumer crashes trigger re-delivery.

**Async processing**: Registration takes 50ms instead of 450ms when email and analytics happen asynchronously via queue.

```python
# Sync: 450ms (user waits for email + analytics)
def register_user(data):
    user = create_user(data)
    send_welcome_email(user)
    create_analytics_event(user)
    return user

# Async: 52ms (email and analytics via queue)
def register_user(data):
    user = create_user(data)
    queue.publish("user.registered", user)
    return user
```

---

## Message Broker Comparison

| Feature | Kafka | RabbitMQ | SQS (Standard) | SQS (FIFO) | NATS JetStream |
|---------|-------|----------|-----------------|-------------|----------------|
| Throughput | Millions/sec | ~50K/sec | ~unlimited* | ~3K/sec | ~300K/sec |
| Ordering | Per partition | Per queue | Best-effort | Per message group | Per stream |
| Delivery | At-least-once | At-least-once | At-least-once | Exactly-once (5min) | At-least-once |
| Replay | Yes | No | No | No | Yes |
| Priority | No | Yes (0-255) | No | No | No |
| Routing | Partition key | Exchanges | None | Message group | Subject wildcards |
| Ops burden | High | Medium | Zero | Zero | Low |

### Decision Tree

```
Simple task queue?
  AWS? --> SQS  |  Not AWS? --> RabbitMQ

Event streaming (replay, multi-consumer)?  --> Kafka

Complex routing / priorities?  --> RabbitMQ

Fan-out?
  AWS? --> SNS+SQS  |  Need replay? --> Kafka  |  Broadcast? --> RabbitMQ fanout

Exactly-once?
  Within Kafka? --> Kafka tx  |  Simple dedup? --> SQS FIFO
  External? --> At-least-once + idempotent consumer

Zero ops?
  AWS? --> SQS/SNS  |  Self-hosted? --> NATS

Lowest latency (<5ms)?  --> NATS or RabbitMQ
```

---

## Kafka Deep Dive

Kafka is a distributed commit log, not just a message queue. Messages are retained for a configurable period regardless of consumption.

### Core Architecture

**Topics and Partitions**: A topic is divided into partitions -- the unit of parallelism. Messages within a partition are strictly ordered. Key determines partition: `hash(key) % num_partitions`.

**Offsets**: Each message has a sequential offset. Consumers track position by committing offsets. Consumers can reset offsets to replay historical data.

**Retention**: Default 7 days. Unlike traditional queues, messages are not deleted after consumption. This enables replay, bootstrapping new consumers, and time-travel debugging.

```
CLUSTER: Broker 0 (Controller), Broker 1, Broker 2

TOPIC: orders (replication-factor=3, partitions=4)
  Partition 0: Leader=B0, ISR=[B0,B1,B2]
  Partition 1: Leader=B1, ISR=[B1,B2,B0]

PRODUCER: acks=all, key=order_id, idempotence=enabled
CONSUMER GROUP: Consumer 0 -> [P0,P1], Consumer 1 -> [P2,P3]

FLOW: Producer --> hash(key)%4 --> Partition Leader --> Replicate to ISR
      Consumer --> Poll Leader --> Process --> Commit Offset
```

### Consumer Groups

Each partition is assigned to exactly one consumer per group. Rules:
- Consumers > partitions: some idle.
- Consumers < partitions: some handle multiple.
- Different groups consume independently.

**Rebalancing**: When consumers join/leave, partitions redistribute. Cooperative rebalancing (Kafka 2.4+) only pauses affected partitions.

### Exactly-Once Semantics

```java
// Idempotent producer (dedup via PID + sequence number)
props.put("enable.idempotence", true);

// Transactional (atomic writes across partitions)
props.put("transactional.id", "my-tx-id");
producer.initTransactions();
producer.beginTransaction();
producer.send(new ProducerRecord<>("output", key, value));
producer.sendOffsetsToTransaction(offsets, groupId);
producer.commitTransaction();
```

**At-most-once**: Commit before processing. **At-least-once**: Commit after processing. **Exactly-once**: Idempotent producers + transactions. Consumers with `isolation.level=read_committed` see only committed messages.

**Caveat**: EOS applies within Kafka. External systems need additional idempotency.

**Practical guidance**: Enable idempotence for all producers (`enable.idempotence=true`). It has negligible performance impact and prevents duplicates from network retries. Use transactions only when you need atomic writes across multiple partitions or topics, as transactions add ~10ms overhead per batch.

### Log Compaction

Retains only latest value per key. Use cases: changelog topics, KTable materialization, CDC.

```
Before: [A=1] [B=1] [A=2] [B=2] [A=3]
After:  [B=2] [A=3]
```

Tombstones (null value) remove keys entirely after compaction.

### Kafka Streams

Client library for stream processing -- runs inside your application, no separate cluster.

```java
KStream<String, Order> orders = builder.stream("orders");
KTable<String, Long> counts = orders
    .filter((k, v) -> v.getStatus().equals("COMPLETED"))
    .groupByKey().count();
counts.toStream().to("order-counts");
```

**KStream**: Unbounded event stream (insert semantics). **KTable**: Changelog (upsert semantics). **State stores**: Local RocksDB backed by compacted changelog topics.

### Kafka Connect

Framework for streaming data between Kafka and external systems. Source connectors pull data in (Debezium, JDBC). Sink connectors push data out (Elasticsearch, S3, BigQuery).

### When to Use Kafka

**Use when**: Durable replayable streams, multiple consumer groups, high throughput (millions/sec), event ordering, event sourcing/CQRS, stream processing.

**Do not use when**: Simple task queue (SQS/RabbitMQ), low latency point-to-point (NATS/RabbitMQ), small team/low volume (high operational overhead), complex routing (RabbitMQ), message TTL or priority.

**Operational reality**: Kafka requires expertise to operate. Partition count changes require careful planning (cannot decrease). Consumer group rebalancing can cause processing pauses. Monitoring consumer lag, broker disk usage, and ISR health is essential. Consider managed Kafka (Confluent Cloud, AWS MSK, Redpanda) if your team lacks dedicated infrastructure engineers.

**Partition count guidance**: Start with `max(expected_throughput / per_consumer_throughput, number_of_consumers)`. You can increase partitions later, but never decrease. Over-partitioning wastes resources; under-partitioning limits parallelism. A common starting point is 6-12 partitions per topic.

---

## SQS / SNS

### SQS

Fully managed queue. No servers, no operational overhead.

**Standard**: Nearly unlimited throughput, at-least-once delivery, best-effort ordering.

**FIFO**: 3K msg/sec (batched), exactly-once (5-min dedup window), strict ordering per message group.

**Visibility Timeout**: Message hidden from other consumers while being processed. Set to 2x expected processing time. Too short = duplicates. Too long = delayed retry.

**Dead Letter Queues**: After `maxReceiveCount` failed attempts, SQS moves message to DLQ.

```python
sqs.send_message(QueueUrl=url, MessageBody=json.dumps(data),
                 MessageGroupId="order-123",           # FIFO ordering
                 MessageDeduplicationId="abc-def-123")  # FIFO dedup

response = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10,
                               WaitTimeSeconds=20,      # Long polling
                               VisibilityTimeout=60)
```

### SNS + SQS Fan-Out

```
Producer --> SNS Topic --> SQS: order-processing
                       --> SQS: notifications
                       --> SQS: analytics
                       --> Lambda: audit
```

One event, all subscribers get independent copies. Standard AWS event-driven pattern. Always use long polling (`WaitTimeSeconds=20`).

**SQS vs Kafka for AWS teams**: SQS is the right default for most AWS workloads. Zero operational overhead, pay-per-message, auto-scaling. Use Kafka (MSK) only when you need replay, multiple consumer groups on the same data, or throughput beyond what SQS can handle. Many teams over-architect with Kafka when SQS would suffice.

**Message batching**: Both sending and receiving support batches of up to 10 messages. Always use batching in high-throughput scenarios to reduce API calls and cost.

```python
# Batch send (up to 10 messages)
sqs.send_message_batch(
    QueueUrl=url,
    Entries=[
        {"Id": str(i), "MessageBody": json.dumps(msg)}
        for i, msg in enumerate(messages[:10])
    ]
)
```

---

## RabbitMQ

AMQP broker with powerful routing. Producers send to exchanges, not queues.

### Exchange Types

**Direct**: Exact routing key match. **Topic**: Wildcard patterns (`order.*` matches one word, `order.#` matches zero or more). **Fanout**: Broadcast to all bound queues. **Headers**: Route by message headers (rarely used).

```
Exchange (topic)
  "order.*"       --> Queue: all-order-events
  "order.created" --> Queue: new-orders-only
  "*.critical"    --> Queue: critical-events
```

### Queue Features

**Acknowledgments**: Consumers must ack. No ack = re-delivery on disconnect.

**Prefetch** (`basic_qos`): Controls max unacked messages per consumer. Prevents fast consumers from starving slow ones.

**Dead Letter Exchanges**: Rejected/expired/overflow messages route to DLX.

**Priority Queues**: Supports 0-255 priority (keep range small for performance).

```python
channel.basic_qos(prefetch_count=10)
channel.queue_declare(queue='orders', arguments={
    'x-dead-letter-exchange': 'dlx',
    'x-message-ttl': 60000
})
```

---

## NATS

Lightweight, high-performance messaging. Core NATS is pub/sub with no persistence -- if nobody is listening, message is lost. Sub-millisecond latency.

**JetStream**: Adds persistence, replay, and consumer groups.

```go
js.AddStream(&nats.StreamConfig{
    Name: "ORDERS", Subjects: []string{"orders.>"},
    Storage: nats.FileStorage, MaxAge: 24 * time.Hour,
})
js.Subscribe("orders.created", handler, nats.Durable("processor"))
```

**Request/Reply**: Synchronous RPC over messaging. Useful for internal service calls with message bus decoupling.

**When to choose NATS**: You need a lightweight messaging system with minimal operational overhead (single binary, no JVM, no ZooKeeper). Good for edge computing, IoT, and environments where Kafka or RabbitMQ would be over-provisioned. JetStream bridges the gap when you need persistence without Kafka's complexity.

**NATS vs Kafka**: NATS prioritizes simplicity and low latency. Kafka prioritizes durability and throughput. NATS is fire-and-forget by default (core) with opt-in persistence (JetStream). Kafka is durable by default. Choose based on your primary requirement.

---

## Dead Letter Queues and Retry Strategies

### Exponential Backoff with Jitter

```python
def delay(attempt, base=1.0, max_delay=300.0):
    return min(base * (2 ** attempt), max_delay)  # 1s, 2s, 4s, 8s...

def delay_with_jitter(attempt, base=1.0, max_delay=300.0):
    return random.uniform(0, min(base * (2 ** attempt), max_delay))
```

Without jitter, all failed messages retry simultaneously (thundering herd).

```
Exponential Backoff:
  delay = base * (2 ^ attempt)        # 1s, 2s, 4s, 8s, 16s...
  Cap at max_delay (e.g., 300s)

Full Jitter (AWS recommended):
  delay = random(0, min(max_delay, base * 2^attempt))

Decorrelated Jitter:
  delay = min(max_delay, random(base, prev_delay * 3))

Retry Budget:
  max_retries = 3-5 (transient), 0 (permanent errors)
  Total time within SLA: 1+2+4+8+15 = 30s for 60s SLA
```

### Poison Message Handling

Messages that can never succeed (malformed data, schema violation). Without handling, they block the queue forever.

```python
async def process_with_retry(message):
    if message.receive_count > MAX_RETRIES:
        await dlq.send(message)
        alert("Poison message", message_id=message.id)
        return
    try:
        await process(message.body)
        await queue.delete(message)
    except TransientError:
        pass  # Visibility timeout expires, auto-retry
    except PermanentError:
        await dlq.send(message)
```

**DLQ workflow**: Fail N times -> auto-move to DLQ -> alert -> engineer investigates -> fix root cause -> replay from DLQ.

**Classifying errors is critical**: Distinguish between transient errors (network timeout, temporary unavailability) and permanent errors (malformed message, schema violation, authorization failure). Retry transient errors with backoff. Send permanent errors directly to DLQ without retrying.

```python
class TransientError(Exception):
    """Retry is likely to succeed"""
    pass

class PermanentError(Exception):
    """Retry will never succeed"""
    pass

# Map exception types to error classification
ERROR_CLASSIFICATION = {
    ConnectionError: TransientError,
    TimeoutError: TransientError,
    ValidationError: PermanentError,
    AuthenticationError: PermanentError,
}
```

---

## Idempotency

With at-least-once delivery, consumers will receive duplicates. Idempotency ensures processing a message multiple times produces the same result as once.

### Idempotency Keys

```python
async def process_payment(message):
    key = message.headers["idempotency-key"]
    if await db.query("SELECT 1 FROM processed_events WHERE key = $1", key):
        return  # Skip duplicate

    async with db.transaction():
        await charge_payment(message.data)
        await db.execute("INSERT INTO processed_events (key) VALUES ($1)", key)
```

### Deduplication Strategies

```sql
-- Database dedup (within single transaction)
BEGIN;
INSERT INTO processed_events (idempotency_key) VALUES ('evt-123')
    ON CONFLICT DO NOTHING;
-- 0 rows affected = duplicate, skip processing
-- 1 row affected = new, proceed with business logic
UPDATE orders SET status = 'paid' WHERE id = '123';
COMMIT;
```

```python
# Redis dedup
async def is_duplicate(key, ttl=86400):
    return await redis.set(f"dedup:{key}", "1", nx=True, ex=ttl) is None
```

```
Natural idempotency:
  IDEMPOTENT: SET balance=500, DELETE WHERE id=123, PUT /users/123
  NOT:        INCREMENT BY 50, INSERT INTO cart, POST /users

Rule: Prefer absolute values (SET) over relative (INCREMENT).
```

### The Formula

```
Exactly-Once = At-Least-Once Delivery + Idempotent Processing

At-Most-Once:  Commit offset BEFORE processing. Crash = message lost.
At-Least-Once: Commit offset AFTER processing. Crash = re-delivery.
Exactly-Once:  = At-Least-Once + Idempotent Consumer
  1. Kafka transactions (within Kafka only)
  2. Idempotency key in database (external systems)
  3. Store offset in DB alongside business data (same transaction)
```

Kafka provides EOS within Kafka. For external systems, approximate with at-least-once + idempotent consumers.

---

## Interview Questions

### Conceptual

1. **Compare Kafka, RabbitMQ, and SQS. When would you choose each?**

   Kafka: high throughput, replay, streaming. RabbitMQ: complex routing, priorities, low latency. SQS: managed, serverless, simple queues.

2. **Message queue vs. event stream -- why does it matter?**

   Queue: consumed and deleted, one consumer. Stream: retained, multiple consumers, replay possible. Matters for event sourcing, audit, retroactive consumers.

3. **Kafka consumer lag is growing. Debug it.**

   Consumer health, rebalancing loops, processing time per message, poison messages, GC pauses, partition-to-consumer ratio, serialization errors.

4. **Exactly-once from Kafka to PostgreSQL?**

   Store Kafka offset in PostgreSQL alongside business data in the same transaction. On restart, seek to last committed offset from DB.

### System Design

5. **Order pipeline: 10K orders/sec, exactly-once payments.**

   SNS fan-out, SQS per consumer, idempotency keys in payments DB, DLQ with alerting, saga orchestrator for fulfillment.

6. **Notification system (email, push, SMS) resilient to failures, no duplicates.**

   SNS topic, separate SQS per channel, idempotency key per (user, type, event_id), DLQ per channel, circuit breaker per provider.

### Debugging

7. **Messages piling up in Kafka. Walk through debugging.**

   Is consumer running? Rebalancing loops? Throughput? Poison messages? GC? Partition count vs consumer count?

8. **50K messages in SQS DLQ. Investigate and recover.**

   Sample messages, correlate with error logs, identify pattern (schema change, outage, permissions). Fix root cause, replay from DLQ, monitor.

---

## Related Reading

- [Module 04: Event Sourcing, CQRS, and Sagas](02-event-sourcing-cqrs-and-sagas.md) -- patterns that build on message brokers: event sourcing uses Kafka as the append-only log, CQRS uses events to populate read models, sagas coordinate distributed transactions
- [Module 04: Message Queue Operations](03-message-queue-operations-and-patterns.md) -- Kafka internals (ISR, KRaft), the outbox pattern, CDC with Debezium, schema evolution, and stream processing
- [Module 02: SQL, NoSQL, and Decision Framework](../02-databases-at-scale/01-sql-nosql-and-decision-framework.md) -- databases that back your message consumers; understanding consistency models helps you choose between at-least-once and exactly-once semantics
- [Module 05: Circuit Breakers and Retry Strategies](../05-load-balancing/02-circuit-breakers-and-retry-strategies.md) -- retry patterns (exponential backoff with jitter, retry budgets) apply directly to message consumer error handling and DLQ strategies
- [Module 06: Kubernetes Core and Operations](../06-containers-orchestration/02-kubernetes-core-and-operations.md) -- deploying Kafka on Kubernetes using StatefulSets, and scaling consumers with KEDA based on consumer lag
- [Module 08: Logging, Metrics, and Tracing](../08-observability/01-logging-metrics-and-tracing.md) -- monitoring consumer lag, processing latency, and DLQ depth with Prometheus metrics; correlating messages across services using distributed tracing
