# Module 09: Architecture Patterns — Cheat Sheet

---

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

## Clean Architecture Layer Diagram

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

---

## DI Container Setup Template

### Manual DI (Composition Root)

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

  return { orderCtrl, shutdown: () => Promise.all([prisma.$disconnect(), redis.quit()]) };
}
```

### tsyringe Setup

```typescript
import 'reflect-metadata';
import { container } from 'tsyringe';

container.register('OrderRepository', { useClass: PrismaOrderRepository });
container.register('EventBus', { useClass: BullMQEventBus });
container.register('CacheService', { useClass: RedisCacheService });
// Resolve: container.resolve(PlaceOrderUseCase)
```

---

## Error Hierarchy Template

```typescript
abstract class AppError extends Error {
  abstract readonly statusCode: number;
  abstract readonly code: string;
  abstract readonly isOperational: boolean;
  constructor(message: string, public readonly cause?: Error) {
    super(message);
    this.name = this.constructor.name;
  }
}

class NotFoundError extends AppError     { statusCode = 404; code = 'NOT_FOUND';     isOperational = true; }
class ValidationError extends AppError   { statusCode = 400; code = 'VALIDATION';    isOperational = true; }
class ConflictError extends AppError     { statusCode = 409; code = 'CONFLICT';      isOperational = true; }
class UnauthorizedError extends AppError { statusCode = 401; code = 'UNAUTHORIZED';  isOperational = true; }
class ForbiddenError extends AppError    { statusCode = 403; code = 'FORBIDDEN';     isOperational = true; }
class RateLimitError extends AppError    { statusCode = 429; code = 'RATE_LIMITED';  isOperational = true; }
// Programmer errors: don't extend AppError — let them crash
```

**Rule**: `isOperational = true` means return error response. Non-operational (or unknown) means log, return 500, and consider graceful restart.

---

## Microservices vs Monolith Decision Tree

```
START: Do you have 2+ of these?
  ├── Need independent scaling for specific modules? ──→ YES
  ├── Module deploys 5x more frequently than the rest? ──→ YES
  ├── Module needs a different runtime/language? ──→ YES
  ├── Dedicated team (4+) owns the module? ──→ YES
  └── Module failure must not take down the system? ──→ YES

Count YES answers:
  0-1 ──→ MODULAR MONOLITH (enforce module boundaries, extract later)
  2+  ──→ EXTRACT THAT MODULE (keep the rest as monolith)
  All ──→ MICROSERVICES (but honestly, re-check your assumptions)
```

---

## Project Structure Templates

### Feature-Based (Recommended)

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

### Quick Decisions

| Decision | Answer |
|----------|--------|
| Barrel exports? | One per feature module. No nested barrels. |
| Shared code? | Only when used by 3+ features. |
| Where to put middleware? | `src/shared/middleware/` or co-located with feature. |
| Config files? | `src/config/` with environment-specific overrides. |
| Tests location? | Co-located: `order.service.test.ts` next to `order.service.ts`. |

---

## CQRS Quick Reference

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

---

## Saga Quick Reference

| Aspect | Choreography | Orchestration |
|--------|-------------|---------------|
| Coordinator | None (event-driven) | Central saga manager |
| Coupling | Very loose | Moderate |
| Visibility | Distributed (hard to trace) | Centralized (easy to trace) |
| Best for | 2-3 step simple flows | 4+ step complex workflows |
| Failure handling | Each service compensates | Orchestrator compensates |

---

## Outbox Pattern in 30 Seconds

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
