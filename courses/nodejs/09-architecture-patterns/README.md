# Module 09: Architecture Patterns

> You've built enough systems to know that the initial architecture decision echoes through every sprint for years. This module is about knowing when to reach for which pattern, articulating trade-offs, and why most teams over-architect or under-architect at exactly the wrong moments.

---

## Table of Contents

- [Clean Architecture in Node.js](#clean-architecture-in-nodejs)
- [Domain-Driven Design (Practical)](#domain-driven-design-practical)
- [CQRS](#cqrs)
- [Event-Driven Architecture](#event-driven-architecture)
- [Microservices vs Monolith](#microservices-vs-monolith)
- [Dependency Injection](#dependency-injection)
- [Project Structure Conventions](#project-structure-conventions)
- [Error Handling Architecture](#error-handling-architecture)
- [Interview Questions](#interview-questions)

---

## Clean Architecture in Node.js

### The Layers

Clean architecture enforces a dependency rule: **inner layers know nothing about outer layers**.

```
┌──────────────────────────────────────────────┐
│  Presentation (routes, resolvers, CLI)       │
├──────────────────────────────────────────────┤
│  Infrastructure (Prisma, Redis, S3, Kafka)   │
├──────────────────────────────────────────────┤
│  Application (use cases, DTOs, orchestration)│
├──────────────────────────────────────────────┤
│  Domain (entities, value objects, events,    │
│          repository interfaces)              │
└──────────────────────────────────────────────┘
       Dependencies point INWARD →
```

### Ports and Adapters

Ports are interfaces in the domain/application layer. Adapters are implementations in infrastructure.

```typescript
// PORT — domain/ports/OrderRepository.ts
export interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  save(order: Order): Promise<void>;
}

// ADAPTER — infrastructure/adapters/PrismaOrderRepository.ts
export class PrismaOrderRepository implements OrderRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: OrderId): Promise<Order | null> {
    const row = await this.prisma.order.findUnique({
      where: { id: id.value }, include: { lineItems: true },
    });
    return row ? OrderMapper.toDomain(row) : null;
  }

  async save(order: Order): Promise<void> {
    const data = OrderMapper.toPersistence(order);
    await this.prisma.order.upsert({ where: { id: data.id }, create: data, update: data });
  }
}
```

### Use Cases as the Application Layer

```typescript
export class PlaceOrderUseCase {
  constructor(
    private readonly orderRepo: OrderRepository,
    private readonly inventoryService: InventoryService,
    private readonly eventBus: DomainEventBus,
  ) {}

  async execute(command: PlaceOrderCommand): Promise<OrderId> {
    const availability = await this.inventoryService.check(command.items);
    if (!availability.allAvailable) throw new InsufficientInventoryError(availability.unavailable);

    const order = Order.create({
      customerId: new CustomerId(command.customerId),
      items: command.items.map(i => LineItem.create(i)),
      shippingAddress: Address.create(command.shippingAddress),
    });

    await this.orderRepo.save(order);
    await this.eventBus.publishAll(order.domainEvents);
    return order.id;
  }
}
```

**Interview insight**: The key benefit isn't testability (though you get that). It's that you can swap infrastructure without touching business logic. Migrated from Prisma to Drizzle? Change one adapter. Your domain stays untouched.

---

## Domain-Driven Design (Practical)

Skip the blue book philosophy. Here's what matters in practice.

### Entities

Objects with identity that persists across state changes.

```typescript
export class Order {
  private _domainEvents: DomainEvent[] = [];

  private constructor(
    public readonly id: OrderId,
    private _status: OrderStatus,
    private _items: LineItem[],
    public readonly customerId: CustomerId,
  ) {}

  static create(props: CreateOrderProps): Order {
    const order = new Order(OrderId.generate(), OrderStatus.PENDING, props.items, props.customerId);
    order.addDomainEvent(new OrderCreatedEvent(order.id, order.customerId));
    return order;
  }

  confirm(): void {
    if (this._status !== OrderStatus.PENDING)
      throw new InvalidOrderTransitionError(this._status, OrderStatus.CONFIRMED);
    this._status = OrderStatus.CONFIRMED;
    this.addDomainEvent(new OrderConfirmedEvent(this.id));
  }

  get domainEvents(): ReadonlyArray<DomainEvent> { return [...this._domainEvents]; }
  clearDomainEvents(): void { this._domainEvents = []; }
  private addDomainEvent(event: DomainEvent): void { this._domainEvents.push(event); }
}
```

### Value Objects

Immutable. Compared by value, not identity.

```typescript
export class Money {
  private constructor(public readonly amount: number, public readonly currency: Currency) {}

  static create(amount: number, currency: Currency): Money {
    if (amount < 0) throw new InvalidMoneyError('Amount cannot be negative');
    return new Money(Math.round(amount * 100) / 100, currency);
  }

  add(other: Money): Money {
    if (this.currency !== other.currency) throw new CurrencyMismatchError(this.currency, other.currency);
    return Money.create(this.amount + other.amount, this.currency);
  }

  equals(other: Money): boolean {
    return this.amount === other.amount && this.currency === other.currency;
  }
}
```

### Aggregates, Repositories, Domain Events

**Aggregates**: Cluster of entities/value objects treated as a single unit. The aggregate root is the only entry point. One transaction per aggregate.

**Repositories**: One per aggregate root. Persist and retrieve entire aggregates.

**Domain Events**: Past-tense facts about what happened: `OrderPlaced`, `PaymentReceived`, `InventoryReserved`.

```typescript
export interface DomainEvent {
  readonly eventId: string;
  readonly occurredAt: Date;
  readonly aggregateId: string;
  readonly eventType: string;
}
```

---

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

### Saga Pattern

When a business process spans multiple services, use sagas with compensating transactions.

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

## Microservices vs Monolith

### The Modular Monolith: The Sweet Spot

```
src/
├── modules/
│   ├── orders/
│   │   ├── domain/          # Entities, value objects, events
│   │   ├── application/     # Use cases, DTOs
│   │   ├── infrastructure/  # Repositories, external clients
│   │   ├── presentation/    # Routes, controllers
│   │   └── index.ts         # Public API
│   ├── inventory/
│   └── payments/
├── shared/                  # Shared kernel (events, base classes)
└── main.ts
```

Enforce boundaries with TypeScript project references or ESLint import rules. Modules communicate via events, not direct imports.

### Extraction Criteria

Extract a module into a separate service when at least two of these apply:

1. **Independent scaling**: Module needs 10x the compute of everything else
2. **Independent deployment**: Module changes 5x more frequently
3. **Technology divergence**: Module needs a different runtime
4. **Team autonomy**: Dedicated team, cross-team coordination is the bottleneck
5. **Fault isolation**: Module failure must not take down the system

### Inter-Service Communication

| Method | Use When | Coupling |
|--------|----------|----------|
| HTTP/REST | Sync request/response, CRUD | High |
| gRPC | High-throughput internal, streaming | High (schema) |
| Message Queue | Async processing, decoupled | Low |
| Event Bus | Broadcasting state changes | Very Low |

### API Gateway and Service Discovery

Gateway handles: routing, auth, rate limiting, response aggregation, circuit breaking. Use Kong, Envoy, or AWS API Gateway.

Service discovery in Kubernetes: built-in DNS. Without K8s: Consul, etcd, or cloud provider solutions.

---

## Dependency Injection

### Why Node.js Culture Resists DI Frameworks

1. Module system already provides inversion of control
2. Idiomatic Node.js prefers functions over classes
3. Reflection-based DI adds boot time and complexity
4. Decorators obscure the dependency graph

### Manual DI (Constructor Injection)

```typescript
// composition-root.ts — the only place that knows all concrete implementations
export function createContainer(config: AppConfig) {
  const prisma = new PrismaClient({ datasourceUrl: config.databaseUrl });
  const redis = new Redis(config.redisUrl);

  const orderRepo = new PrismaOrderRepository(prisma);
  const cacheService = new RedisCacheService(redis);
  const eventBus = new BullMQEventBus(redis);

  const placeOrder = new PlaceOrderUseCase(orderRepo, cacheService, eventBus);
  const orderController = new OrderController(placeOrder);

  return {
    orderController,
    async shutdown() {
      await prisma.$disconnect();
      await redis.quit();
    },
  };
}
```

### tsyringe and inversify

```typescript
// tsyringe — lightweight, Microsoft
@injectable()
class PlaceOrderUseCase {
  constructor(@inject('OrderRepository') private orderRepo: OrderRepository) {}
}
container.register('OrderRepository', { useClass: PrismaOrderRepository });

// inversify — feature-rich, symbol-based
const TYPES = { OrderRepository: Symbol.for('OrderRepository') };
container.bind<OrderRepository>(TYPES.OrderRepository).to(PrismaOrderRepository).inSingletonScope();
```

**Interview take**: "Manual DI via a composition root for most projects. tsyringe or inversify only when the graph exceeds ~50 services."

---

## Project Structure Conventions

### Feature-Based vs Layer-Based

**Layer-based** (controllers/, services/, repositories/) forces you to touch 4+ directories for one feature change.

**Feature-based** (features/orders/, features/users/) co-locates everything for a feature. Recommended for anything beyond a toy project.

### Barrel Exports

Use one `index.ts` per feature module as its public API. Avoid nested barrels (cause circular deps and slow TS compilation). Never create a top-level barrel that re-exports everything.

```typescript
// features/orders/index.ts
export { OrderController } from './order.controller';
export { OrderService } from './order.service';
export type { Order, CreateOrderDTO } from './order.model';
```

---

## Error Handling Architecture

### Custom Error Hierarchy

```typescript
export abstract class AppError extends Error {
  abstract readonly statusCode: number;
  abstract readonly code: string;
  abstract readonly isOperational: boolean;

  constructor(message: string, public readonly cause?: Error) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

class NotFoundError extends AppError {
  statusCode = 404; code = 'NOT_FOUND'; isOperational = true;
  constructor(resource: string, id: string) { super(`${resource} '${id}' not found`); }
}

class ValidationError extends AppError {
  statusCode = 400; code = 'VALIDATION_ERROR'; isOperational = true;
  constructor(public readonly errors: Array<{ field: string; message: string }>) { super('Validation failed'); }
}

class ConflictError extends AppError     { statusCode = 409; code = 'CONFLICT';     isOperational = true; }
class UnauthorizedError extends AppError { statusCode = 401; code = 'UNAUTHORIZED'; isOperational = true; }
class ForbiddenError extends AppError    { statusCode = 403; code = 'FORBIDDEN';    isOperational = true; }
class RateLimitError extends AppError    { statusCode = 429; code = 'RATE_LIMITED'; isOperational = true; }
```

### Operational vs Programmer Errors

| Operational | Programmer |
|---|---|
| Expected failures (bad input, timeout) | Bugs (TypeError, null ref) |
| Return structured error response | Crash process, fix the bug |
| `isOperational = true` | Unrecognized error |

### Error Middleware and Boundaries

```typescript
// Express global error handler
export function errorHandler(err: Error, req: Request, res: Response, next: NextFunction): void {
  if (err instanceof AppError && err.isOperational) {
    res.status(err.statusCode).json({ code: err.code, message: err.message });
    return;
  }

  logger.error({ err, requestId: req.id }, 'Unhandled error');
  res.status(500).json({ code: 'INTERNAL_ERROR', message: 'An unexpected error occurred' });
}

// Route-level error boundary
function asyncHandler(fn: (req: Request, res: Response, next: NextFunction) => Promise<void>) {
  return (req: Request, res: Response, next: NextFunction) => fn(req, res, next).catch(next);
}

router.post('/orders', asyncHandler(async (req, res) => {
  const result = await placeOrder.execute(req.body);
  res.status(201).json(result);
}));
```

---

## Interview Questions

**Q: "How would you structure a Node.js application for a team of 8 engineers?"**

Modular monolith. Feature-based structure. Each module has domain/application/infrastructure/presentation layers. Modules communicate through events, not direct imports. Enforce boundaries with TS project references. Extract to microservices only when concrete extraction criteria are met.

**Q: "When would you choose CQRS?"**

When read and write models diverge significantly, or when you need independent scaling at a 1000:1 read-to-write ratio. Cautious about CQRS for simple CRUD — eventual consistency adds significant UX and debugging complexity.

**Q: "Explain the dependency rule in clean architecture."**

Dependencies point inward. Domain layer has zero external imports. Application depends on domain only. Infrastructure implements domain interfaces (ports). You can swap Postgres for MongoDB by changing one adapter without touching business logic.

**Q: "How do you handle distributed transactions across microservices?"**

Sagas, not distributed transactions. Orchestration-based saga for complex workflows (5+ steps, logic in one place). Choreography-based saga for simple 2-3 step flows (each service publishes events, services know their own compensating actions).

**Q: "For or against DI frameworks in Node.js?"**

For: Lifecycle management, scoped instances, easy swapping for tests. Against: Module system already provides IoC, decorator magic obscures the graph, boot-time overhead. Default to manual DI via composition root. Upgrade to tsyringe/inversify when the graph exceeds ~50 services.

**Q: "Barrel exports — yes or no?"**

Yes, sparingly. One `index.ts` per feature module as its public API. No nested barrels, no top-level barrel re-exporting everything. Deep barrel chains cause circular deps and slow the type checker.

**Q: "Microservices vs monolith?"**

Start modular monolith. Extract when you can name at least two concrete criteria: independent scaling, independent deployment, tech divergence, team autonomy, fault isolation. If you're extracting because "microservices are best practice," you're optimizing for the wrong thing.

**Q: "How do you structure error handling?"**

Abstract `AppError` base with `statusCode`, `code`, and `isOperational` flag. Operational errors return structured responses. Programmer errors log and return 500. All async handlers wrapped in error boundaries. Global error middleware as the catch-all.
