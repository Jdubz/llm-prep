# Module 04: Event Sourcing, CQRS, and Sagas

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

### Event Sourcing Domain Aggregate Template

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

### Read Model Technology Choices by Use Case

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

### Saga Template with Timeout Handling

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

## Interview Questions

### Conceptual

1. **Choreography vs. orchestration for sagas?**

   Choreography: few services, simple flow, team autonomy. Orchestration: many steps, complex failure, need observability. Most at-scale systems prefer orchestration.

2. **Message queue vs. event stream -- why does it matter?**

   Queue: consumed and deleted, one consumer. Stream: retained, multiple consumers, replay possible. Matters for event sourcing, audit, retroactive consumers.

3. **Exactly-once from Kafka to PostgreSQL?**

   Store Kafka offset in PostgreSQL alongside business data in the same transaction. On restart, seek to last committed offset from DB.

### System Design

4. **Order pipeline: 10K orders/sec, exactly-once payments.**

   SNS fan-out, SQS per consumer, idempotency keys in payments DB, DLQ with alerting, saga orchestrator for fulfillment.

5. **Event-sourced system with aggregates having millions of events. Reads are slow.**

   Snapshots, CQRS read model, snapshot frequency tuning, archive old events, evaluate if event sourcing fits.

6. **Notification system (email, push, SMS) resilient to failures, no duplicates.**

   SNS topic, separate SQS per channel, idempotency key per (user, type, event_id), DLQ per channel, circuit breaker per provider.

---

## Related Reading

- [Module 04: Message Brokers](01-message-brokers-kafka-sqs-rabbitmq.md) -- the broker fundamentals (Kafka, SQS, RabbitMQ) that event sourcing, CQRS, and sagas are built on
- [Module 04: Message Queue Operations](03-message-queue-operations-and-patterns.md) -- the outbox pattern for reliable event publishing, CDC with Debezium for capturing state changes, and schema evolution for event contracts
- [Module 02: SQL, NoSQL, and Decision Framework](../02-databases-at-scale/01-sql-nosql-and-decision-framework.md) -- event stores require append-optimized databases; CQRS read models use denormalized databases (DynamoDB, Elasticsearch) optimized for query patterns
- [Module 02: Database Platforms and Scaling](../02-databases-at-scale/03-database-platforms-and-scaling.md) -- PostgreSQL as an event store (append-only table with sequence numbers), and DynamoDB for CQRS read models with single-table design
- [Module 05: Circuit Breakers and Retry Strategies](../05-load-balancing/02-circuit-breakers-and-retry-strategies.md) -- saga compensating transactions need circuit breakers and retry logic for each service call in the saga chain
