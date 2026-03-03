# 03 – Advanced Patterns and Multi-Tenancy

## Multi-Tenancy Patterns

### Shared Schema with tenant_id (Most Common)

```typescript
// Every table has a tenant_id column
// Every query MUST filter by tenant_id

// Prisma middleware to enforce tenant isolation
prisma.$use(async (params, next) => {
  const tenantId = AsyncLocalStorage.getStore()?.tenantId;
  if (!tenantId) return next(params);

  // Inject tenant_id into all queries
  if (params.action === 'findMany' || params.action === 'findFirst') {
    params.args.where = { ...params.args.where, tenantId };
  }

  if (params.action === 'create') {
    params.args.data = { ...params.args.data, tenantId };
  }

  if (params.action === 'update' || params.action === 'delete') {
    params.args.where = { ...params.args.where, tenantId };
  }

  return next(params);
});

// Context middleware
const tenantStorage = new AsyncLocalStorage<{ tenantId: string }>();

app.use((req, res, next) => {
  const tenantId = req.headers['x-tenant-id'] as string;
  tenantStorage.run({ tenantId }, () => next());
});
```

### Row-Level Security (RLS) in PostgreSQL

RLS enforces isolation at the database level — even raw queries cannot bypass tenant isolation.

```sql
-- Enable RLS on the table
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see their tenant's data
CREATE POLICY tenant_isolation ON posts
  USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Set tenant context per request
SET LOCAL app.tenant_id = 'tenant-uuid-here';
```

```typescript
// Prisma with RLS
prisma.$use(async (params, next) => {
  const tenantId = AsyncLocalStorage.getStore()?.tenantId;

  // Set RLS context before each query
  await prisma.$executeRaw`SELECT set_config('app.tenant_id', ${tenantId}, true)`;

  return next(params);
});
```

**RLS advantage**: Enforcement at the database level. But adds overhead per query for the config lookup.

### Schema per Tenant

```typescript
// Each tenant gets a separate PostgreSQL schema
async function createTenantSchema(tenantId: string) {
  const schemaName = `tenant_${tenantId.replace(/-/g, '_')}`;

  await prisma.$executeRawUnsafe(`CREATE SCHEMA IF NOT EXISTS "${schemaName}"`);

  // Run migrations in tenant schema
  await prisma.$executeRawUnsafe(`SET search_path TO "${schemaName}"`);
  // ... apply migrations ...
}

// Route queries to correct schema
function getTenantPrisma(tenantId: string): PrismaClient {
  const schemaName = `tenant_${tenantId.replace(/-/g, '_')}`;

  return new PrismaClient({
    datasources: {
      db: {
        url: `${process.env.DATABASE_URL}?schema=${schemaName}`,
      },
    },
  });
}
```

### Multi-Tenancy Pattern Comparison

| Pattern | Isolation | Complexity | Scalability | Migration Pain |
|---------|-----------|------------|-------------|----------------|
| Shared schema + tenant_id | Application-enforced | Low | High | Low (one migration) |
| Row-Level Security | Database-enforced | Medium | High | Low (one migration) |
| Schema per tenant | Physical | Medium-High | Medium | High (N migrations) |
| Database per tenant | Complete | High | Low | Highest (N databases) |

---

## Repository Pattern

### The Repository Interface (Port)

```typescript
// domain/ports/OrderRepository.ts
export interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  findByCustomerId(customerId: CustomerId, pagination: Pagination): Promise<PaginatedResult<Order>>;
  save(order: Order): Promise<void>;
  delete(id: OrderId): Promise<void>;
}
```

### Prisma Adapter

```typescript
// infrastructure/adapters/PrismaOrderRepository.ts
export class PrismaOrderRepository implements OrderRepository {
  constructor(private readonly prisma: PrismaClient) {}

  async findById(id: OrderId): Promise<Order | null> {
    const row = await this.prisma.order.findUnique({
      where: { id: id.value },
      include: { lineItems: true },
    });
    return row ? OrderMapper.toDomain(row) : null;
  }

  async save(order: Order): Promise<void> {
    const data = OrderMapper.toPersistence(order);
    await this.prisma.order.upsert({
      where: { id: data.id },
      create: data,
      update: data,
    });
  }

  async findByCustomerId(customerId: CustomerId, pagination: Pagination): Promise<PaginatedResult<Order>> {
    const [rows, total] = await this.prisma.$transaction([
      this.prisma.order.findMany({
        where: { customerId: customerId.value },
        skip: (pagination.page - 1) * pagination.limit,
        take: pagination.limit,
        orderBy: { createdAt: 'desc' },
        include: { lineItems: true },
      }),
      this.prisma.order.count({ where: { customerId: customerId.value } }),
    ]);

    return {
      data: rows.map(OrderMapper.toDomain),
      total,
      page: pagination.page,
      limit: pagination.limit,
    };
  }
}
```

---

## Soft Deletes vs Audit Tables

### Soft Deletes

```typescript
// Prisma schema
// model User {
//   deletedAt DateTime? @map("deleted_at")
// }

// Pros: simple, reversible, maintains referential integrity
// Cons: every query needs WHERE deleted_at IS NULL, index bloat,
//       GDPR compliance issues (data is not actually deleted)

// The middleware approach from 01-prisma-and-drizzle.md intercepts
// findMany/findFirst and injects deletedAt: null
```

### Audit Tables (Preferred for Compliance)

```typescript
// Separate history table with full change log
await prisma.$executeRaw`
  CREATE TABLE users_audit (
    audit_id      BIGSERIAL PRIMARY KEY,
    operation     VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE
    changed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by    UUID,
    old_data      JSONB,
    new_data      JSONB,
    user_id       UUID NOT NULL
  );

  CREATE OR REPLACE FUNCTION audit_trigger() RETURNS trigger AS $$
  BEGIN
    IF TG_OP = 'INSERT' THEN
      INSERT INTO users_audit (operation, new_data, user_id, changed_by)
      VALUES ('INSERT', to_jsonb(NEW), NEW.id, current_setting('app.user_id', true)::uuid);
      RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
      INSERT INTO users_audit (operation, old_data, new_data, user_id, changed_by)
      VALUES ('UPDATE', to_jsonb(OLD), to_jsonb(NEW), NEW.id, current_setting('app.user_id', true)::uuid);
      RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
      INSERT INTO users_audit (operation, old_data, user_id, changed_by)
      VALUES ('DELETE', to_jsonb(OLD), OLD.id, current_setting('app.user_id', true)::uuid);
      RETURN OLD;
    END IF;
  END;
  $$ LANGUAGE plpgsql;

  CREATE TRIGGER users_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger();
`;
```

**When to use each:**
- **Soft deletes**: User-facing "trash/recycle bin" features, simple undo functionality
- **Audit tables**: Compliance (SOX, HIPAA), debugging, data recovery, change history
- **Both**: Soft delete for the UX + audit table for compliance

---

## Event Sourcing with Node.js

Event sourcing stores state as a sequence of immutable events rather than mutable current state. The current state is derived by replaying events.

### Event Store Implementation

```typescript
// Event type definitions
interface DomainEvent {
  eventId: string;
  aggregateId: string;
  aggregateType: string;
  eventType: string;
  version: number;       // Per-aggregate version for ordering + optimistic concurrency
  payload: Record<string, unknown>;
  metadata: {
    userId?: string;
    correlationId: string;
    causationId?: string;
    timestamp: string;
  };
}

// PostgreSQL event store
class PostgresEventStore {
  async append(
    aggregateId: string,
    events: Omit<DomainEvent, 'eventId' | 'version'>[],
    expectedVersion: number
  ): Promise<void> {
    await prisma.$transaction(async (tx) => {
      // Optimistic concurrency check
      const [current] = await tx.$queryRaw<[{ max_version: number }]>`
        SELECT COALESCE(MAX(version), 0) as max_version
        FROM events
        WHERE aggregate_id = ${aggregateId}
        FOR UPDATE
      `;

      if (current.max_version !== expectedVersion) {
        throw new ConcurrencyError(
          `Expected version ${expectedVersion}, got ${current.max_version}`
        );
      }

      for (let i = 0; i < events.length; i++) {
        const version = expectedVersion + i + 1;
        const event = events[i];

        await tx.$executeRaw`
          INSERT INTO events (
            event_id, aggregate_id, aggregate_type, event_type,
            version, payload, metadata, created_at
          ) VALUES (
            ${crypto.randomUUID()}, ${aggregateId}, ${event.aggregateType},
            ${event.eventType}, ${version}, ${JSON.stringify(event.payload)}::jsonb,
            ${JSON.stringify(event.metadata)}::jsonb, NOW()
          )
        `;
      }
    });
  }

  async getEvents(aggregateId: string, fromVersion = 0): Promise<DomainEvent[]> {
    return prisma.$queryRaw<DomainEvent[]>`
      SELECT * FROM events
      WHERE aggregate_id = ${aggregateId}
        AND version > ${fromVersion}
      ORDER BY version ASC
    `;
  }

  async *getAllEvents(fromPosition = 0): AsyncGenerator<DomainEvent> {
    const BATCH_SIZE = 1000;
    let position = fromPosition;

    while (true) {
      const events = await prisma.$queryRaw<DomainEvent[]>`
        SELECT * FROM events
        WHERE id > ${position}
        ORDER BY id ASC
        LIMIT ${BATCH_SIZE}
      `;

      if (events.length === 0) break;

      for (const event of events) {
        yield event;
        position = Number(event.eventId);
      }
    }
  }
}
```

### Aggregate Root Pattern

```typescript
abstract class AggregateRoot<TState> {
  private uncommittedEvents: DomainEvent[] = [];
  protected state!: TState;
  public version = 0;

  protected abstract apply(event: DomainEvent): TState;
  protected abstract getInitialState(): TState;

  loadFromHistory(events: DomainEvent[]): void {
    this.state = this.getInitialState();
    for (const event of events) {
      this.state = this.apply(event);
      this.version = event.version;
    }
  }

  protected raise(eventType: string, payload: Record<string, unknown>): void {
    const event: DomainEvent = {
      eventId: crypto.randomUUID(),
      aggregateId: this.id,
      aggregateType: this.constructor.name,
      eventType,
      version: this.version + this.uncommittedEvents.length + 1,
      payload,
      metadata: {
        correlationId: AsyncLocalStorage.getStore()?.correlationId || '',
        timestamp: new Date().toISOString(),
      },
    };

    this.uncommittedEvents.push(event);
    this.state = this.apply(event);
  }

  getUncommittedEvents(): DomainEvent[] {
    return [...this.uncommittedEvents];
  }

  clearUncommittedEvents(): void {
    this.uncommittedEvents = [];
  }
}

// Example: Order aggregate
class Order extends AggregateRoot<OrderState> {
  get id() { return this.state.id; }

  protected getInitialState(): OrderState {
    return { id: '', status: 'draft', items: [], total: 0 };
  }

  static create(id: string, customerId: string): Order {
    const order = new Order();
    order.raise('OrderCreated', { id, customerId });
    return order;
  }

  addItem(productId: string, quantity: number, price: number): void {
    if (this.state.status !== 'draft') {
      throw new Error('Cannot modify a non-draft order');
    }
    this.raise('ItemAdded', { productId, quantity, price });
  }

  submit(): void {
    if (this.state.items.length === 0) {
      throw new Error('Cannot submit empty order');
    }
    this.raise('OrderSubmitted', { submittedAt: new Date().toISOString() });
  }

  protected apply(event: DomainEvent): OrderState {
    switch (event.eventType) {
      case 'OrderCreated':
        return { ...this.state, id: event.payload.id as string, status: 'draft' };
      case 'ItemAdded':
        return {
          ...this.state,
          items: [...this.state.items, event.payload as OrderItem],
          total: this.state.total + (event.payload.price as number) * (event.payload.quantity as number),
        };
      case 'OrderSubmitted':
        return { ...this.state, status: 'submitted' };
      default:
        return this.state;
    }
  }
}
```

### Snapshots for Performance

```typescript
// After N events, save a snapshot to avoid replaying from the beginning
class SnapshotStore {
  private readonly SNAPSHOT_INTERVAL = 100;

  async saveIfNeeded(aggregate: AggregateRoot<any>): Promise<void> {
    if (aggregate.version % this.SNAPSHOT_INTERVAL !== 0) return;

    await prisma.snapshot.upsert({
      where: { aggregateId: aggregate.id },
      update: {
        state: JSON.stringify(aggregate.state),
        version: aggregate.version,
      },
      create: {
        aggregateId: aggregate.id,
        aggregateType: aggregate.constructor.name,
        state: JSON.stringify(aggregate.state),
        version: aggregate.version,
      },
    });
  }

  async loadAggregate<T extends AggregateRoot<any>>(
    AggregateClass: new () => T,
    aggregateId: string,
    eventStore: PostgresEventStore
  ): Promise<T> {
    const aggregate = new AggregateClass();

    const snapshot = await prisma.snapshot.findUnique({
      where: { aggregateId },
    });

    let fromVersion = 0;
    if (snapshot) {
      aggregate.state = JSON.parse(snapshot.state);
      aggregate.version = snapshot.version;
      fromVersion = snapshot.version;
    }

    const events = await eventStore.getEvents(aggregateId, fromVersion);
    aggregate.loadFromHistory(events);

    return aggregate;
  }
}
```

### CQRS with Event Sourcing

```typescript
// COMMAND side: writes go to the event store
class OrderCommandHandler {
  constructor(
    private eventStore: PostgresEventStore,
    private snapshotStore: SnapshotStore,
    private eventBus: EventBus,
  ) {}

  async handle(command: CreateOrderCommand): Promise<string> {
    const order = Order.create(command.orderId, command.customerId);

    for (const item of command.items) {
      order.addItem(item.productId, item.quantity, item.price);
    }

    order.submit();

    const events = order.getUncommittedEvents();
    await this.eventStore.append(order.id, events, 0);
    order.clearUncommittedEvents();

    for (const event of events) {
      await this.eventBus.publish(event);
    }

    await this.snapshotStore.saveIfNeeded(order);
    return order.id;
  }
}

// QUERY side: reads come from optimized read models (projections)
class OrderReadModel {
  async handleEvent(event: DomainEvent): Promise<void> {
    switch (event.eventType) {
      case 'OrderCreated':
        await prisma.orderView.create({
          data: {
            id: event.payload.id as string,
            customerId: event.payload.customerId as string,
            status: 'draft',
            itemCount: 0,
            total: 0,
            createdAt: new Date(event.metadata.timestamp),
          },
        });
        break;

      case 'ItemAdded':
        await prisma.orderView.update({
          where: { id: event.aggregateId },
          data: {
            itemCount: { increment: 1 },
            total: { increment: (event.payload.price as number) * (event.payload.quantity as number) },
          },
        });
        break;

      case 'OrderSubmitted':
        await prisma.orderView.update({
          where: { id: event.aggregateId },
          data: { status: 'submitted', submittedAt: new Date(event.metadata.timestamp) },
        });
        break;
    }
  }
}

// Query handler — reads from denormalized view, no joins needed
class OrderQueryHandler {
  async getOrderSummaries(customerId: string, pagination: Pagination) {
    return prisma.orderView.findMany({
      where: { customerId },
      orderBy: { createdAt: 'desc' },
      skip: (pagination.page - 1) * pagination.limit,
      take: pagination.limit,
    });
  }
}
```

---

## Expert Interview Questions

### Architecture-Level Questions

**Q: You're designing a multi-tenant SaaS platform expecting 10,000 tenants. How do you structure the database?**

Strong answer pattern:
- Start with shared schema + `tenant_id` (simplest, most scalable)
- Add RLS for defense-in-depth
- Composite indexes with `tenant_id` as the leading column
- Connection pooling with PgBouncer in transaction mode
- Monitoring per-tenant query performance to identify noisy neighbors
- Plan for future migration to schema-per-tenant for large enterprise tenants
- Discuss the noisy neighbor problem and how to handle it (per-tenant rate limiting at the application level, resource quotas)

**Q: Your API is slow. EXPLAIN ANALYZE shows a sequential scan on a table with 50 million rows. Walk me through your investigation.**

Strong answer pattern:
- Check if an appropriate index exists
- If index exists, check if the query planner is choosing to use it (`SET enable_seqscan = off` to test)
- Check table statistics (`ANALYZE table_name` to refresh)
- Check if the query returns a high percentage of rows (>10-15% of the table — seq scan may genuinely be faster)
- Check `work_mem` setting (insufficient memory forces sort to disk)
- Consider a partial index if the query has a consistent filter condition
- Consider a covering index to avoid heap lookups
- Check for type mismatches (e.g., comparing varchar to integer bypasses the index)

**Q: How would you implement zero-downtime database migrations for a system that cannot tolerate any downtime?**

Strong answer pattern:
- Expand/contract pattern: add new → migrate data → switch reads → remove old
- Never rename columns directly — add new, dual-write, backfill, switch, drop
- Never add NOT NULL without a default — add nullable first, backfill, then add constraint
- Batch data migrations with rate limiting to avoid lock contention
- Use `CREATE INDEX CONCURRENTLY` (does not lock the table)
- Test migrations against a production-sized dataset to estimate lock duration
- Use tools like `pgroll` or `reshape` for automated safe migrations

**Q: Explain the trade-offs between optimistic and pessimistic locking. When would you use each?**

Strong answer pattern:
- **Optimistic**: Best for low contention. No locks held. Detect conflicts at commit time via version column. Retries are cheap when conflicts are rare. Use for: user profile updates, content editing, most CRUD operations.
- **Pessimistic**: Best for high contention. Locks row immediately. No retries needed but holds locks longer. Use for: inventory management, financial transactions, seat reservations — any scenario where conflicting updates are frequent and the cost of a failed optimistic retry is high.
- **Hybrid**: Start optimistic, escalate to pessimistic if retry rate exceeds threshold.
- Mention: Distributed locks (Redis/Redlock) for cross-service coordination, but prefer database-level locking when possible.

### Debugging Questions

**Q: Your application intermittently throws "too many connections" errors. What do you investigate?**

- Connection pool exhaustion: check pool size vs concurrent request volume
- Connection leaks: transactions or connections not being released (missing `finally` blocks)
- Long-running queries holding connections (check `pg_stat_activity`)
- Serverless cold starts creating connection storms
- Missing PgBouncer in front of PostgreSQL
- Connection pool `maxUses` not set (connections never recycled, accumulate stale state)

**Q: A Prisma query that used to take 10ms now takes 2 seconds. The table grew from 100K to 10M rows. What happened?**

- Index is no longer being used (query planner cost estimates shifted with table size)
- Table bloat from frequent updates without `VACUUM` (dead tuples increase scan cost)
- Statistics are stale (`ANALYZE` not running frequently enough)
- Shared buffers too small (hot data no longer fits in memory)
- N+1 queries that were invisible at 100K rows become dominant at 10M
- Index bloat (B-tree fragmentation after many deletes) — `REINDEX CONCURRENTLY`

---

## Summary

1. **Choose your ORM deliberately**: Prisma for DX and guardrails, Drizzle for SQL-native teams and performance.
2. **Connection pooling is not optional**: Use PgBouncer in front of PostgreSQL, especially with serverless.
3. **Migrations must be zero-downtime**: Expand/contract pattern, never rename columns directly.
4. **Indexing is an art**: Composite indexes with the right column order, partial indexes for filtered queries, covering indexes to avoid heap lookups.
5. **Optimistic locking by default**: Switch to pessimistic only when contention is proven high.
6. **Multi-tenancy starts simple**: Shared schema with `tenant_id`, add RLS, evolve to schema-per-tenant only when needed.
7. **Monitor everything**: Slow query logs, connection pool metrics, index usage statistics.
