# 02 – Event-Driven and Async Patterns

## CQRS

### Command/Query Separation

Commands mutate state (return nothing or an ID). Queries return data (mutate nothing).

```typescript
// Command side — write to normalized, consistency-optimized store
class PlaceOrderHandler {
  async execute(command: PlaceOrderCommand): Promise<{ orderId: string }> { /* ... */ }
}

// Query side — read from denormalized, read-optimized store
class GetOrderDetailsHandler {
  async execute(query: GetOrderDetailsQuery): Promise<OrderDetailsDTO> { /* ... */ }
}
```

### CQRS Quick Reference

```
COMMAND SIDE                        QUERY SIDE
─────────────                       ──────────
Normalized schema                   Denormalized views
Enforces invariants                 Pre-joined, fast reads
Optimistic concurrency              Eventually consistent
Returns ID only                     Returns full DTOs
write DB (Postgres)                 read DB (Postgres/Redis/Elastic)

Sync mechanism: Domain events → Projections → Read model updates
```

### Event-Driven CQRS

Commands produce domain events. Projections consume events and update read models.

```typescript
class OrderProjection {
  constructor(private readonly readDb: ReadDatabase, private readonly eventBus: EventBus) {
    this.eventBus.subscribe('order.placed', this.onOrderPlaced.bind(this));
    this.eventBus.subscribe('order.shipped', this.onOrderShipped.bind(this));
  }

  private async onOrderPlaced(event: OrderPlacedEvent): Promise<void> {
    await this.readDb.upsert('order_details', {
      orderId: event.aggregateId, status: 'placed',
      customerName: event.customerName, items: event.items,
    });
  }
}
```

### When CQRS Is Overkill

**Overkill when**: Read/write patterns are similar (CRUD), small team, eventual consistency is unacceptable, read-to-write ratio isn't heavily skewed.

**Worth it when**: Read models need radically different shapes, independent scaling of reads vs writes, complex domain logic on writes with complex query patterns on reads.

---

## Event-Driven Architecture

### EventEmitter Patterns

```typescript
// Typed event emitter (Node.js 20+)
interface OrderEvents {
  'order:created': [order: Order];
  'order:shipped': [orderId: string, trackingNumber: string];
}

class OrderEventBus extends EventEmitter<OrderEvents> {}
```

**Critical gotcha**: `EventEmitter` doesn't handle async listeners. If an `async` listener throws, you get an unhandled promise rejection. Wrap listeners or use a proper async event bus.

### Message Brokers

**BullMQ** (Redis-backed queues):

```typescript
const emailQueue = new Queue('emails', {
  connection: { host: 'redis', port: 6379 },
  defaultJobOptions: { attempts: 3, backoff: { type: 'exponential', delay: 1000 } },
});

await emailQueue.add('order-confirmation', { orderId: order.id.value, customerEmail });

const worker = new Worker('emails', async (job) => {
  await emailService.send(job.data.customerEmail, 'order-confirmation', job.data);
}, { connection: { host: 'redis', port: 6379 }, concurrency: 10 });
```

**Kafka** (via kafkajs): Use partition keys to ensure ordering per entity. Idempotent producers for exactly-once semantics. Transactional sends for atomicity.

### Event Sourcing Basics

Store every state change as an event. Reconstruct state by replaying.

```typescript
class EventSourcedOrder {
  private state: OrderState = { status: 'draft', items: [], version: 0 };

  static fromEvents(events: DomainEvent[]): EventSourcedOrder {
    const order = new EventSourcedOrder();
    for (const event of events) order.apply(event);
    return order;
  }

  private apply(event: DomainEvent): void {
    switch (event.eventType) {
      case 'order.created':
        this.state = { ...this.state, status: 'pending', version: this.state.version + 1 };
        break;
      case 'order.confirmed':
        this.state = { ...this.state, status: 'confirmed', version: this.state.version + 1 };
        break;
    }
  }
}
```

### CQRS with EventStoreDB

```typescript
import { EventStoreDBClient, jsonEvent, START, FORWARDS } from '@eventstore/db-client';

const client = EventStoreDBClient.connectionString('esdb://localhost:2113?tls=false');

// Write events to a stream
async function appendEvents(orderId: string, events: DomainEvent[]): Promise<void> {
  const esEvents = events.map(e => jsonEvent({ type: e.eventType, data: e }));
  await client.appendToStream(`order-${orderId}`, esEvents);
}

// Rebuild aggregate from events
async function loadOrder(orderId: string): Promise<Order> {
  const events = client.readStream(`order-${orderId}`, { direction: FORWARDS, fromRevision: START });
  const domainEvents: DomainEvent[] = [];
  for await (const resolved of events) domainEvents.push(resolved.event?.data as DomainEvent);
  return Order.fromEvents(domainEvents);
}

// Subscription for read model projections
async function startProjection(): Promise<void> {
  const sub = client.subscribeToAll({ filter: { filterOn: 'streamName', prefixes: ['order-'] } });
  for await (const resolved of sub) {
    switch (resolved.event?.type) {
      case 'order.placed': await readDb.insert('order_summaries', buildSummary(resolved.event.data)); break;
      case 'order.shipped': await readDb.update('order_summaries', resolved.event.data.orderId, { status: 'shipped' }); break;
    }
  }
}
```

**Snapshots**: When aggregates have thousands of events, store periodic snapshots to avoid replaying from scratch. Load latest snapshot, then replay only subsequent events.

---

## Saga Pattern

When a business process spans multiple services, use sagas with compensating transactions.

### Saga Quick Reference

| Aspect | Choreography | Orchestration |
|--------|-------------|---------------|
| Coordinator | None (event-driven) | Central saga manager |
| Coupling | Very loose | Moderate |
| Visibility | Distributed (hard to trace) | Centralized (easy to trace) |
| Best for | 2-3 step simple flows | 4+ step complex workflows |
| Failure handling | Each service compensates | Orchestrator compensates |

### Choreography

Each service reacts to events. No central coordinator.

```
OrderService → "OrderPlaced" → InventoryService → "InventoryReserved" → PaymentService → "PaymentProcessed" → ShippingService
```

Pros: loose coupling, independent deploy, no SPOF. Cons: hard to trace full workflow, debugging requires event correlation.

### Orchestration

Central saga coordinator tells services what to do.

```typescript
class OrderSagaOrchestrator {
  private readonly steps: SagaStep[] = [
    { name: 'reserve', execute: (ctx) => this.inventory.reserve(ctx), compensate: (ctx) => this.inventory.release(ctx) },
    { name: 'charge', execute: (ctx) => this.payment.charge(ctx), compensate: (ctx) => this.payment.refund(ctx) },
    { name: 'ship', execute: (ctx) => this.shipping.create(ctx), compensate: (ctx) => this.shipping.cancel(ctx) },
  ];

  async run(context: SagaContext): Promise<void> {
    const completed: SagaStep[] = [];
    for (const step of this.steps) {
      try {
        Object.assign(context, await step.execute(context));
        completed.push(step);
      } catch (err) {
        for (const s of completed.reverse()) await s.compensate(context).catch(e => logger.error(e));
        throw new SagaAbortedError(step.name, err as Error);
      }
    }
  }
}
```

Pros: workflow logic in one place, easy to reason about. Cons: central point of failure, tighter coupling.

**Decision**: Choreography for 2-3 simple steps. Orchestration for 4+ steps or complex branching.

### Simple Saga (Orchestration)

```typescript
class PlaceOrderSaga {
  async execute(command: PlaceOrderCommand): Promise<void> {
    const steps: SagaStep[] = [];
    try {
      const reservation = await this.inventoryService.reserve(command.items);
      steps.push({ service: 'inventory', action: 'reserve', data: reservation });

      const payment = await this.paymentService.charge(command.customerId, command.total);
      steps.push({ service: 'payment', action: 'charge', data: payment });

      await this.orderService.create(command);
    } catch (err) {
      // Compensate in reverse order
      for (const step of steps.reverse()) await this.compensate(step);
      throw new SagaFailedError(err);
    }
  }
}
```

---

## Outbox Pattern

Solves the dual-write problem: atomically update a database AND publish a message.

```
1. BEGIN TRANSACTION
2.   INSERT INTO orders (...)
3.   INSERT INTO outbox_events (type, payload, published_at=NULL)
4. COMMIT

5. [Separate poller process]
6.   SELECT * FROM outbox_events WHERE published_at IS NULL
7.   Publish to Kafka/RabbitMQ
8.   UPDATE outbox_events SET published_at = NOW()
```

Guarantees: DB write and event publish are eventually consistent. No dual-write problem.

```typescript
// Step 1: Atomic write — order + event in same transaction
await prisma.$transaction(async (tx) => {
  await tx.order.upsert({ where: { id: order.id }, create: data, update: data });
  await tx.outboxEvent.create({
    data: { id: event.eventId, eventType: event.eventType, payload: JSON.stringify(event), publishedAt: null },
  });
});

// Step 2: Separate poller publishes unpublished events
class OutboxPoller {
  async poll(): Promise<void> {
    const unpublished = await prisma.outboxEvent.findMany({ where: { publishedAt: null }, take: 100 });
    for (const event of unpublished) {
      await messageBroker.publish(event.eventType, JSON.parse(event.payload));
      await prisma.outboxEvent.update({ where: { id: event.id }, data: { publishedAt: new Date() } });
    }
  }
}
```

Alternative: PostgreSQL CDC via Debezium streams outbox table changes directly to Kafka. No polling.

---

## Distributed Tracing

### OpenTelemetry in Node.js

```typescript
// tracing.ts — initialize BEFORE importing anything else
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

const sdk = new NodeSDK({
  resource: new Resource({ [ATTR_SERVICE_NAME]: 'order-service' }),
  traceExporter: new OTLPTraceExporter({ url: 'http://jaeger:4318/v1/traces' }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
```

### Context Propagation Across Services

For HTTP: W3C Trace Context headers (`traceparent`). For message queues: inject context into message headers.

```typescript
// Producing: inject trace context
const headers: Record<string, string> = {};
propagation.inject(context.active(), headers);
producer.send({ topic, messages: [{ value: JSON.stringify(payload), headers }] });

// Consuming: extract trace context
const parentContext = propagation.extract(context.active(), message.headers);
context.with(parentContext, () => {
  tracer.startActiveSpan('processMessage', async (span) => { /* child of producing span */ });
});
```

---

## Interview Questions

**Q: "When would you choose CQRS?"**

When read and write models diverge significantly, or when you need independent scaling at a 1000:1 read-to-write ratio. Cautious about CQRS for simple CRUD — eventual consistency adds significant UX and debugging complexity.

**Q: "How do you handle distributed transactions across microservices?"**

Sagas, not distributed transactions. Orchestration-based saga for complex workflows (5+ steps, logic in one place). Choreography-based saga for simple 2-3 step flows (each service publishes events, services know their own compensating actions).

**Q: "How do you ensure a database write and a message publish are atomic?"**

Outbox pattern. Write the message to an `outbox_events` table in the same transaction as the domain change. A separate poller reads unpublished events and publishes them to the broker, then marks them published. This ensures at-least-once delivery without two-phase commit.

**Q: "What is the difference between event sourcing and a regular event-driven system?"**

In a regular event-driven system, events trigger side effects but the source of truth is current state in a database. In event sourcing, the sequence of events IS the source of truth — current state is derived by replaying events. Event sourcing enables temporal queries (what was the state at time T?), complete audit history, and event replay. It adds significant complexity; only use it when those benefits are required.
