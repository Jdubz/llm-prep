# Module 04: Message Queues & Event-Driven Architecture -- Cheat Sheet

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

---

## Kafka Concepts Diagram

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

---

## SQS vs RabbitMQ vs Kafka Decision Tree

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

## Event Sourcing Template

```python
@dataclass
class DomainEvent:
    event_id: str
    aggregate_id: str
    event_type: str
    version: int
    timestamp: datetime
    data: dict

class Order:
    def __init__(self):
        self.id = self.status = None
        self._events = []
        self._version = 0

    def create(self, order_id, items):
        self._apply(DomainEvent(event_type="OrderCreated",
                                data={"order_id": order_id, "items": items}))

    def _on_order_created(self, event):
        self.id = event.data["order_id"]
        self.status = "PENDING"

    def _apply(self, event):
        getattr(self, f"_on_{to_snake(event.event_type)}")(event)
        self._events.append(event)
        self._version += 1

    def load_from_events(self, events):
        for e in events:
            getattr(self, f"_on_{to_snake(e.event_type)}")(e)
            self._version += 1
```

---

## Saga Pattern Template

```python
class SagaStep:
    def __init__(self, name, action, compensation):
        self.name = name
        self.action = action
        self.compensation = compensation

class Saga:
    def __init__(self, saga_id, steps):
        self.steps = steps
        self.completed = []

    async def execute(self):
        for step in self.steps:
            try:
                await asyncio.wait_for(step.action(), timeout=30)
                self.completed.append(step)
            except (Exception, asyncio.TimeoutError) as e:
                await self._compensate()
                raise SagaFailed(f"'{step.name}' failed: {e}")

    async def _compensate(self):
        for step in reversed(self.completed):
            try: await step.compensation()
            except Exception as e:
                logger.error(f"Compensation failed: '{step.name}': {e}")

# Usage
saga = Saga("order-123", [
    SagaStep("create_order",      create_order,      cancel_order),
    SagaStep("reserve_inventory", reserve_inventory,  release_inventory),
    SagaStep("charge_payment",    charge_payment,     refund_payment),
])
```

---

## Retry Strategy Formulas

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

---

## Idempotency Patterns

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

---

## Message Delivery Guarantees

```
At-Most-Once:  Commit offset BEFORE processing. Crash = message lost.
At-Least-Once: Commit offset AFTER processing. Crash = re-delivery.
Exactly-Once:  = At-Least-Once + Idempotent Consumer
  1. Kafka transactions (within Kafka only)
  2. Idempotency key in database (external systems)
  3. Store offset in DB alongside business data (same transaction)
```
