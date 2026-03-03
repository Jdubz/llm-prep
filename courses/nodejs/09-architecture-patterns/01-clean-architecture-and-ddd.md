# 01 – Clean Architecture and Domain-Driven Design

## Architecture Pattern Comparison

| Pattern | Complexity | Best For | Avoid When |
|---------|-----------|----------|------------|
| Clean Architecture | Medium | Long-lived apps, large teams | Prototypes, small CRUD apps |
| Hexagonal (Ports/Adapters) | Medium | Apps with many external integrations | Simple internal tools |
| Vertical Slice | Low-Medium | Feature-heavy apps, rapid iteration | Heavily shared domain logic |
| CQRS | High | Divergent read/write models, high read:write ratio | Simple CRUD, small teams |
| Event Sourcing | Very High | Audit-critical domains, temporal queries | Simple state management |
| Modular Monolith | Medium | Most teams (2-30 engineers) | Already at extraction point |
| Microservices | Very High | Independent scaling/deployment needs | Pre-product-market-fit |

---

## Clean Architecture in Node.js

### The Layers

Clean architecture enforces a dependency rule: **inner layers know nothing about outer layers**.

```
OUTER ──────────────────────────────────────────── INNER

┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌────────┐
│ Presentation│→ │Infrastructure│→ │  Application │→ │ Domain │
│             │  │              │  │              │  │        │
│ Routes      │  │ Prisma Repo  │  │ Use Cases    │  │Entities│
│ Controllers │  │ Redis Cache  │  │ DTOs         │  │V.O.s   │
│ Middleware  │  │ S3 Adapter   │  │ Orchestration│  │Events  │
│ Resolvers   │  │ API Clients  │  │ Interfaces   │  │Repos*  │
└─────────────┘  └─────────────┘  └──────────────┘  └────────┘
                                                     *interfaces
Dependencies point INWARD →
Domain has ZERO external imports
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

## Dependency Injection

### Why Node.js Culture Resists DI Frameworks

1. Module system already provides inversion of control
2. Idiomatic Node.js prefers functions over classes
3. Reflection-based DI adds boot time and complexity
4. Decorators obscure the dependency graph

### Manual DI (Composition Root)

The composition root is the only place that knows all concrete implementations.

```typescript
// src/composition-root.ts
export function createContainer(config: AppConfig) {
  // Infrastructure
  const prisma = new PrismaClient({ datasourceUrl: config.dbUrl });
  const redis = new Redis(config.redisUrl);
  const orderRepo = new PrismaOrderRepository(prisma);
  const cache = new RedisCacheService(redis);
  const eventBus = new BullMQEventBus(redis);

  // Application (use cases)
  const placeOrder = new PlaceOrderUseCase(orderRepo, cache, eventBus);
  const getOrder = new GetOrderUseCase(orderRepo, cache);

  // Presentation (controllers)
  const orderCtrl = new OrderController(placeOrder, getOrder);

  return {
    orderCtrl,
    shutdown: () => Promise.all([prisma.$disconnect(), redis.quit()]),
  };
}
```

### tsyringe and inversify

```typescript
import 'reflect-metadata';
import { container } from 'tsyringe';

// tsyringe — lightweight, Microsoft
container.register('OrderRepository', { useClass: PrismaOrderRepository });
container.register('EventBus', { useClass: BullMQEventBus });
container.register('CacheService', { useClass: RedisCacheService });
// Resolve: container.resolve(PlaceOrderUseCase)

// inversify — feature-rich, symbol-based
const TYPES = { OrderRepository: Symbol.for('OrderRepository') };
container.bind<OrderRepository>(TYPES.OrderRepository).to(PrismaOrderRepository).inSingletonScope();
```

**Interview take**: "Manual DI via a composition root for most projects. tsyringe or inversify only when the graph exceeds ~50 services."

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
// Programmer errors: don't extend AppError — let them crash
```

### Operational vs Programmer Errors

| Operational | Programmer |
|---|---|
| Expected failures (bad input, timeout) | Bugs (TypeError, null ref) |
| Return structured error response | Crash process, fix the bug |
| `isOperational = true` | Unrecognized error |

**Rule**: `isOperational = true` means return error response. Non-operational (or unknown) means log, return 500, and consider graceful restart.

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

## Project Structure Conventions

### Feature-Based vs Layer-Based

**Layer-based** (`controllers/`, `services/`, `repositories/`) forces you to touch 4+ directories for one feature change.

**Feature-based** (`features/orders/`, `features/users/`) co-locates everything for a feature. Recommended for anything beyond a toy project.

### Recommended Structure

```
src/
├── features/
│   ├── orders/
│   │   ├── domain/         # Entities, value objects, events
│   │   ├── application/    # Use cases, DTOs
│   │   ├── infra/          # Repos, adapters
│   │   ├── routes.ts       # HTTP routes
│   │   └── index.ts        # Public API (barrel export)
│   └── users/
│       └── ...
├── shared/                 # Cross-cutting: base classes, utils, types
├── config/                 # App configuration
├── composition-root.ts     # Wire all dependencies
└── main.ts                 # Entry point
```

### Barrel Exports

Use one `index.ts` per feature module as its public API. Avoid nested barrels (cause circular deps and slow TS compilation). Never create a top-level barrel that re-exports everything.

```typescript
// features/orders/index.ts
export { OrderController } from './order.controller';
export { OrderService } from './order.service';
export type { Order, CreateOrderDTO } from './order.model';
```

### Quick Decisions

| Decision | Answer |
|----------|--------|
| Barrel exports? | One per feature module. No nested barrels. |
| Shared code? | Only when used by 3+ features. |
| Where to put middleware? | `src/shared/middleware/` or co-located with feature. |
| Config files? | `src/config/` with environment-specific overrides. |
| Tests location? | Co-located: `order.service.test.ts` next to `order.service.ts`. |

---

## Interview Questions

**Q: "How would you structure a Node.js application for a team of 8 engineers?"**

Modular monolith. Feature-based structure. Each module has domain/application/infrastructure/presentation layers. Modules communicate through events, not direct imports. Enforce boundaries with TS project references. Extract to microservices only when concrete extraction criteria are met.

**Q: "Explain the dependency rule in clean architecture."**

Dependencies point inward. Domain layer has zero external imports. Application depends on domain only. Infrastructure implements domain interfaces (ports). You can swap Postgres for MongoDB by changing one adapter without touching business logic.

**Q: "For or against DI frameworks in Node.js?"**

For: Lifecycle management, scoped instances, easy swapping for tests. Against: Module system already provides IoC, decorator magic obscures the graph, boot-time overhead. Default to manual DI via composition root. Upgrade to tsyringe/inversify when the graph exceeds ~50 services.

**Q: "Barrel exports — yes or no?"**

Yes, sparingly. One `index.ts` per feature module as its public API. No nested barrels, no top-level barrel re-exporting everything. Deep barrel chains cause circular deps and slow the type checker.

**Q: "How do you structure error handling?"**

Abstract `AppError` base with `statusCode`, `code`, and `isOperational` flag. Operational errors return structured responses. Programmer errors log and return 500. All async handlers wrapped in error boundaries. Global error middleware as the catch-all.

## Related Reading

- **Clean architecture layers and ports/adapters** use the TypeScript interface patterns from [01 – Conditional and Mapped Types](../01-typescript-advanced/01-conditional-and-mapped-types.md) and the branded types from [01 – Advanced Type Patterns](../01-typescript-advanced/02-advanced-type-patterns.md#branded-types) for domain value objects like `OrderId` and `Money`.
- **Use cases as the application layer** orchestrate the database operations covered in [06 – Prisma and Drizzle](../06-database-patterns/01-prisma-and-drizzle.md) and [06 – Queries, Transactions, and Optimization](../06-database-patterns/02-queries-transactions-and-optimization.md#transaction-isolation-levels) — the repository adapter is where your ORM code lives.
- **Dependency injection and composition root** directly enable the testability patterns in [07 – Vitest and Unit Testing](../07-testing/01-vitest-and-unit-testing.md#dependency-injection-preferred) — DI makes mocking trivial without `vi.mock`.
- **Error handling architecture** extends the error response patterns in [03 – HTTP Semantics and Status Codes](../03-rest-api-design/01-http-semantics-and-status-codes.md) and the GraphQL error handling in [04 – Schema Design and Resolvers](../04-graphql/01-schema-design-and-resolvers.md).
- **Feature-based project structure** informs how you organize the REST routes from [03 – API Design Patterns and Versioning](../03-rest-api-design/03-api-design-patterns-and-versioning.md) and the GraphQL resolvers from [04 – Schema Design and Resolvers](../04-graphql/01-schema-design-and-resolvers.md#resolver-patterns).
- **Domain events in entities** lead into the event-driven patterns in [09 – Event-Driven and Async Patterns](./02-event-driven-and-async-patterns.md) and the BullMQ queue setup in [08 – Caching and Redis](../08-performance-scaling/01-caching-and-redis.md#bullmq-queue-setup).
- **Value objects and entities** use the TypeScript class patterns from [00 – TypeScript and Node.js Fundamentals](../00-ts-node-fundamentals.md#typescript-essentials) and benefit from the security validation in [05 – Session Management and Validation](../05-auth-security/02-session-management-and-validation.md#input-validation-with-zod).
