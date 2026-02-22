# Module 09: Architecture Patterns — Deep Dive

> Beyond the standard patterns. Implementation details and advanced strategies that separate staff-level architectural thinking from senior-level pattern application.

---

## Table of Contents

- [Hexagonal Architecture Implementation](#hexagonal-architecture-implementation)
- [Vertical Slice Architecture](#vertical-slice-architecture)
- [Modular Monolith with NestJS](#modular-monolith-with-nestjs)
- [Strangler Fig Pattern](#strangler-fig-pattern)
- [Distributed Tracing](#distributed-tracing)
- [Choreography vs Orchestration](#choreography-vs-orchestration)
- [Outbox Pattern](#outbox-pattern)
- [CQRS with EventStoreDB](#cqrs-with-eventstoredb)
- [Multi-Repo vs Monorepo](#multi-repo-vs-monorepo)

---

## Hexagonal Architecture Implementation

### Driving vs Driven Ports

**Driving ports** (primary): How the outside world talks TO your application (HTTP, CLI, message consumers). **Driven ports** (secondary): How your application talks to the outside world (database, email, S3).

```
     [HTTP]     [CLI]     [Message Consumer]
        ↓          ↓              ↓
     ═══════  DRIVING PORTS  ═══════
        ↓          ↓              ↓
     ┌──────────────────────────────┐
     │       APPLICATION CORE       │
     │  Use Cases ← Domain ← Entities │
     └──────────────────────────────┘
        ↓          ↓              ↓
     ═══════  DRIVEN PORTS  ════════
        ↓          ↓              ↓
     [Postgres]  [Email]     [S3]
```

```typescript
// DRIVEN PORT (domain layer)
export interface NotificationPort {
  sendOrderConfirmation(to: Email, order: OrderSummary): Promise<void>;
}

// DRIVEN ADAPTER (infrastructure layer)
export class SendGridNotificationAdapter implements NotificationPort {
  constructor(private readonly client: SendGridClient) {}
  async sendOrderConfirmation(to: Email, order: OrderSummary): Promise<void> {
    await this.client.send({ to: to.value, templateId: 'd-abc123', dynamicData: { orderNumber: order.number } });
  }
}

// APPLICATION CORE (implements driving port, depends on driven ports)
export class PlaceOrderUseCase implements PlaceOrderPort {
  constructor(
    private readonly orderRepo: OrderRepositoryPort,
    private readonly notification: NotificationPort,
  ) {}

  async execute(command: PlaceOrderCommand): Promise<OrderId> {
    const order = Order.create(command);
    await this.orderRepo.save(order);
    await this.notification.sendOrderConfirmation(command.customerEmail, order.summary());
    return order.id;
  }
}
```

The power: test `PlaceOrderUseCase` with in-memory fakes for every driven port. No database, no email service. Pure logic testing.

---

## Vertical Slice Architecture

Rejects layers entirely. Each use case is self-contained from HTTP handler to database query.

```
src/features/
├── place-order/
│   ├── PlaceOrderHandler.ts   # HTTP handler
│   ├── PlaceOrderCommand.ts   # Input validation
│   ├── PlaceOrderLogic.ts     # Business logic
│   ├── PlaceOrderQuery.ts     # Direct DB query
│   └── PlaceOrder.test.ts
├── get-order-details/
└── cancel-order/
```

**Wins**: Features are independently modifiable, new engineers understand one slice without learning the full architecture, deletion is trivial (remove directory + route).

**Loses**: Shared domain logic requires careful management (duplication vs shared kernel), cross-cutting concerns need a separate solution.

**Practical hybrid**: Feature-based structure at top level, shared domain extracted only when genuinely reused across 3+ features.

---

## Modular Monolith with NestJS

NestJS modules map naturally to bounded contexts.

```typescript
@Module({
  imports: [TypeOrmModule.forFeature([OrderEntity]), BullModule.registerQueue({ name: 'orders' })],
  controllers: [OrderController],
  providers: [
    PlaceOrderUseCase,
    { provide: 'OrderRepository', useClass: TypeOrmOrderRepository },
    { provide: 'InventoryChecker', useClass: InventoryModuleClient },
    OrderSaga,
  ],
  exports: ['OrderRepository'], // Only what other modules need
})
export class OrdersModule {}

// Cross-module communication via events
@Injectable()
class OrderSaga {
  @OnEvent('inventory.reserved')
  async handleInventoryReserved(event: InventoryReservedEvent): Promise<void> {
    const order = await this.orderRepo.findById(event.orderId);
    order.confirmInventory();
    await this.orderRepo.save(order);
    this.eventBus.emit(new OrderConfirmedEvent(order.id));
  }
}
```

**Boundary enforcement**: Use `@Global()` sparingly. If you're making modules global so others can access them, your boundaries are leaking.

---

## Strangler Fig Pattern

Incrementally migrate from legacy to new architecture.

```typescript
// Proxy layer sits in front of both systems
const legacyProxy = httpProxy.createProxyMiddleware({ target: 'http://legacy:8080' });

// New service handles migrated routes
app.use('/api/v2/orders', orderRouter);
// Legacy handles everything else
app.use('/api', legacyProxy);
```

**Migration steps**: (1) Identify a bounded context with clear boundaries. (2) Build in new architecture. (3) Route traffic via proxy/gateway. (4) Shadow traffic for parity verification. (5) Cut over. (6) Decommission legacy code. (7) Repeat.

**Pitfall**: Dual-write is dangerous during migration. Prefer event-based sync or database CDC (Debezium) to keep systems consistent.

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

## Choreography vs Orchestration

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

---

## Outbox Pattern

Solves the dual-write problem: atomically update a database AND publish a message.

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

## CQRS with EventStoreDB

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

## Multi-Repo vs Monorepo

### Turborepo

```
my-platform/
├── turbo.json
├── apps/
│   ├── api/         # Express/Fastify
│   ├── web/         # Next.js
│   └── worker/      # Background jobs
├── packages/
│   ├── domain/      # Shared domain
│   ├── database/    # Prisma schema
│   ├── config/      # Shared config
│   └── tsconfig/    # Shared TS configs
```

### Nx

More structure: generators, affected commands, dependency graph visualization, module boundary enforcement via ESLint rules and project tags.

### Decision Matrix

| Factor | Multi-Repo | Monorepo |
|--------|-----------|----------|
| Team size | 50+ engineers, autonomous teams | 2-30, shared ownership |
| Code sharing | Publish to registry | Direct imports |
| Consistency | Hard to enforce | Easy (shared configs) |
| CI complexity | Simple per-repo | Need affected builds |
| Onboarding | Smaller scope | Bigger picture |

**Pragmatic answer**: Monorepo with Turborepo for teams under 30. The instant feedback loop of changing a shared package and seeing effects in all consumers is worth the CI investment. Multi-repo when teams genuinely need full autonomy and will invest in internal package registry infrastructure.
