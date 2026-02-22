# Module 04: Message Queues & Event-Driven Architecture

## Table of Contents

1. [Why Message Queues](#why-message-queues)
2. [Kafka Deep Dive](#kafka-deep-dive)
3. [SQS / SNS](#sqs--sns)
4. [RabbitMQ](#rabbitmq)
5. [NATS](#nats)
6. [Event Sourcing](#event-sourcing)
7. [CQRS](#cqrs)
8. [Saga Pattern](#saga-pattern)
9. [Dead Letter Queues and Retry Strategies](#dead-letter-queues-and-retry-strategies)
10. [Idempotency](#idempotency)
11. [Interview Questions](#interview-questions)

---

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

## Kafka Deep Dive

Kafka is a distributed commit log, not just a message queue. Messages are retained for a configurable period regardless of consumption.

### Core Architecture

**Topics and Partitions**: A topic is divided into partitions -- the unit of parallelism. Messages within a partition are strictly ordered. Key determines partition: `hash(key) % num_partitions`.

**Offsets**: Each message has a sequential offset. Consumers track position by committing offsets. Consumers can reset offsets to replay historical data.

**Retention**: Default 7 days. Unlike traditional queues, messages are not deleted after consumption. This enables replay, bootstrapping new consumers, and time-travel debugging.

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

## Event Sourcing

Store state as a sequence of events, not current state. Instead of "balance is $500," store the transactions that produced $500.

### Event Store

```
Account 12345:  AccountOpened -> MoneyDeposited(1000) -> MoneyWithdrawn(200)
                -> MoneyDeposited(50) -> MoneyWithdrawn(350)
Current state:  balance = 1000 - 200 + 50 - 350 = $500
```

### Projections

Read the event stream and build specific views. Multiple projections from one stream: balance view, transaction history, audit log, fraud detection.

```python
class AccountBalanceProjection:
    def handle(self, event):
        if event.type == "MoneyDeposited":
            self.balances[event.aggregate_id] += event.data["amount"]
        elif event.type == "MoneyWithdrawn":
            self.balances[event.aggregate_id] -= event.data["amount"]
```

### Snapshots

Replaying all events is expensive for long-lived aggregates. Periodically capture current state. On load: restore from latest snapshot, then replay only events after that point.

### Versioning Events

Schemas change over time. Strategies: **upcasting** (transform old to new on read), **versioned types** (`OrderCreatedV1`, `V2`), **weak schema** (optional fields with defaults).

```python
# Upcasting: transform old events on read
def upcast_order_created(event):
    if event.version == 1:
        # V1 had "price", V2 split into "subtotal" + "tax"
        event.data["subtotal"] = event.data.pop("price")
        event.data["tax"] = 0
        event.version = 2
    return event
```

**Best practice**: Never delete or rename fields in events. Add new fields with defaults. Old consumers ignore unknown fields. New consumers handle missing fields via defaults. This keeps your event store readable at any point in history.

### Rebuilding State

One of event sourcing's superpowers: rebuild any projection from scratch by replaying all events. Use this when:

- You discover a bug in a projection and need to rebuild with corrected logic.
- You add a new read model (e.g., adding search) and need to populate it from historical events.
- You need an audit trail or compliance report covering the full history.

**Performance**: Replay speed depends on event store throughput. Kafka can replay millions of events per second. An RDBMS-based event store might manage tens of thousands per second. For large aggregates, snapshots are essential to avoid replaying from the beginning.

---

## CQRS

Separate write model (commands) from read model (queries).

```
Commands --> Write Model (domain logic) --> Event Store
                    |
              publishes events
                    v
Queries  --> Read Model (projections)  --> Denormalized views / Elasticsearch
```

**Why**: Read and write have different optimization needs. Scale reads independently. Different read models for different use cases.

**Eventual consistency**: Read model updates asynchronously. Brief stale window after writes. Mitigate with: read from write model after own writes, optimistic UI, sequence number polling.

**When CQRS is overkill**: Simple CRUD, no scaling asymmetry, small team, eventual consistency unacceptable.

**CQRS without event sourcing**: You do not need event sourcing to use CQRS. A common pragmatic approach is: write to a normalized relational database, publish change events, consume events to populate read-optimized stores (Elasticsearch, Redis, materialized views). This gives you the scaling benefits of CQRS without the complexity of an event store.

**Read model technology choices by use case:**

| Use Case | Read Model Store | Why |
|----------|-----------------|-----|
| Full-text search | Elasticsearch | Inverted index, relevance scoring |
| Dashboard aggregations | Materialized views / TimescaleDB | Pre-computed, fast reads |
| API responses | Redis | Sub-millisecond, key-value |
| Reporting | Data warehouse (BigQuery, Redshift) | SQL analytics, joins |

---

## Saga Pattern

Distributed transaction across services without 2PC. Each step has a compensating action.

```
Step 1: Create Order     (compensate: Cancel Order)
Step 2: Reserve Inventory (compensate: Release Inventory)
Step 3: Charge Payment    (compensate: Refund Payment)
Step 4: Ship Order        (compensate: Cancel Shipment)

If Step 3 fails: Release Inventory, Cancel Order
```

### Choreography vs Orchestration

**Choreography**: Each service listens for events and acts. No coordinator. Pro: no single point of failure. Con: hard to debug, no central status.

**Orchestration**: Central orchestrator directs each step. Pro: clear flow, easy monitoring. Con: orchestrator is a dependency (mitigate with persistence).

```python
class OrderSaga:
    async def execute(self):
        try:
            await self.create_order()
            self.completed.append("create_order")
            await self.reserve_inventory()
            self.completed.append("reserve_inventory")
            await self.charge_payment()
            self.completed.append("charge_payment")
        except Exception:
            await self.compensate()  # Reverse order

    async def compensate(self):
        for step in reversed(self.completed):
            await self.compensators[step]()
```

### Timeout Handling

Every step needs a timeout. On timeout, you do not know if the step succeeded -- safe approach is to attempt compensation.

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

**Classifying errors is critical**: Distinguish between transient errors (network timeout, temporary unavailability) and permanent errors (malformed message, schema violation, authorization failure). Retry transient errors with backoff. Send permanent errors directly to DLQ without retrying -- retrying them wastes resources and delays processing of valid messages.

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

1. **Database unique constraint**: Insert idempotency key, skip on conflict.
2. **Redis dedup**: `SET dedup:key 1 NX EX 86400` -- atomic check-and-set with TTL.
3. **Natural idempotency**: Use absolute values (`SET balance=500`) not relative (`INCREMENT BY 50`).

### The Formula

```
Exactly-Once = At-Least-Once Delivery + Idempotent Processing
```

Kafka provides EOS within Kafka. For external systems, approximate with at-least-once + idempotent consumers. This is the practical definition of "effectively once."

---

## Interview Questions

### Conceptual

1. **Compare Kafka, RabbitMQ, and SQS. When would you choose each?**

   Kafka: high throughput, replay, streaming. RabbitMQ: complex routing, priorities, low latency. SQS: managed, serverless, simple queues.

2. **Message queue vs. event stream -- why does it matter?**

   Queue: consumed and deleted, one consumer. Stream: retained, multiple consumers, replay possible. Matters for event sourcing, audit, retroactive consumers.

3. **Kafka consumer lag is growing. Debug it.**

   Consumer health, rebalancing loops, processing time per message, poison messages, GC pauses, partition-to-consumer ratio, serialization errors.

4. **Choreography vs. orchestration for sagas?**

   Choreography: few services, simple flow, team autonomy. Orchestration: many steps, complex failure, need observability. Most at-scale systems prefer orchestration.

5. **Exactly-once from Kafka to PostgreSQL?**

   Store Kafka offset in PostgreSQL alongside business data in the same transaction. On restart, seek to last committed offset from DB.

### System Design

6. **Order pipeline: 10K orders/sec, exactly-once payments.**

   SNS fan-out, SQS per consumer, idempotency keys in payments DB, DLQ with alerting, saga orchestrator for fulfillment.

7. **Event-sourced system with aggregates having millions of events. Reads are slow.**

   Snapshots, CQRS read model, snapshot frequency tuning, archive old events, evaluate if event sourcing fits.

8. **Notification system (email, push, SMS) resilient to failures, no duplicates.**

   SNS topic, separate SQS per channel, idempotency key per (user, type, event_id), DLQ per channel, circuit breaker per provider.

### Debugging

9. **Messages piling up in Kafka. Walk through debugging.**

   Is consumer running? Rebalancing loops? Throughput? Poison messages? GC? Partition count vs consumer count?

10. **50K messages in SQS DLQ. Investigate and recover.**

    Sample messages, correlate with error logs, identify pattern (schema change, outage, permissions). Fix root cause, replay from DLQ, monitor.
