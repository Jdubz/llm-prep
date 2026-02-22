# Module 06 Deep Dive: Advanced Database Patterns

## 1. Event Sourcing with Node.js

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

      // Append events
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

  // Stream all events for projections
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

  // Rebuild state from events
  loadFromHistory(events: DomainEvent[]): void {
    this.state = this.getInitialState();
    for (const event of events) {
      this.state = this.apply(event);
      this.version = event.version;
    }
  }

  // Record a new event
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

    // Load snapshot if available
    const snapshot = await prisma.snapshot.findUnique({
      where: { aggregateId },
    });

    let fromVersion = 0;
    if (snapshot) {
      aggregate.state = JSON.parse(snapshot.state);
      aggregate.version = snapshot.version;
      fromVersion = snapshot.version;
    }

    // Replay events since snapshot
    const events = await eventStore.getEvents(aggregateId, fromVersion);
    aggregate.loadFromHistory(events);

    return aggregate;
  }
}
```

---

## 2. CQRS Implementation

CQRS (Command Query Responsibility Segregation) separates read and write models. Often paired with event sourcing, but can be used independently.

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

    // Persist events
    const events = order.getUncommittedEvents();
    await this.eventStore.append(order.id, events, 0);
    order.clearUncommittedEvents();

    // Publish events for read model updates
    for (const event of events) {
      await this.eventBus.publish(event);
    }

    await this.snapshotStore.saveIfNeeded(order);
    return order.id;
  }
}

// QUERY side: reads come from optimized read models
class OrderReadModel {
  // Projection: listen to events and build a denormalized view
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

// Query handler — reads from denormalized view
class OrderQueryHandler {
  async getOrderSummaries(customerId: string, pagination: Pagination) {
    return prisma.orderView.findMany({
      where: { customerId },
      orderBy: { createdAt: 'desc' },
      skip: (pagination.page - 1) * pagination.limit,
      take: pagination.limit,
    });
    // Fast: no joins, no aggregation, pre-computed values
  }
}
```

---

## 3. Read Replicas with Connection Routing

```typescript
import { Pool } from 'pg';

class DatabaseRouter {
  private writer: Pool;
  private readers: Pool[];
  private currentReader = 0;

  constructor(config: DatabaseConfig) {
    this.writer = new Pool({
      connectionString: config.writerUrl,
      max: 10,
    });

    this.readers = config.readerUrls.map(url => new Pool({
      connectionString: url,
      max: 20, // More connections for reads
    }));
  }

  getWriter(): Pool {
    return this.writer;
  }

  // Round-robin reader selection
  getReader(): Pool {
    if (this.readers.length === 0) return this.writer;
    const reader = this.readers[this.currentReader];
    this.currentReader = (this.currentReader + 1) % this.readers.length;
    return reader;
  }

  // Smart routing based on query type
  async query(sql: string, params?: any[]): Promise<any> {
    const isWrite = /^\s*(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)/i.test(sql);

    if (isWrite) {
      return this.writer.query(sql, params);
    }

    // Check if we need read-after-write consistency
    const requiresConsistency = AsyncLocalStorage.getStore()?.requiresConsistency;
    if (requiresConsistency) {
      return this.writer.query(sql, params); // Read from writer
    }

    return this.getReader().query(sql, params);
  }
}

// Middleware for read-after-write consistency
function requireConsistency() {
  return (req: Request, res: Response, next: NextFunction) => {
    // After a write, subsequent reads in the same request use the writer
    const store = AsyncLocalStorage.getStore();
    if (store) store.requiresConsistency = true;
    next();
  };
}
```

### Replication Lag Handling

```typescript
// Track replication lag and route accordingly
class ReplicaHealthChecker {
  private readonly MAX_LAG_SECONDS = 5;

  async checkReplicaLag(replica: Pool): Promise<number> {
    const result = await replica.query(`
      SELECT EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp())) AS lag_seconds
    `);
    return result.rows[0]?.lag_seconds || Infinity;
  }

  async getHealthyReader(readers: Pool[]): Promise<Pool | null> {
    for (const reader of readers) {
      const lag = await this.checkReplicaLag(reader);
      if (lag < this.MAX_LAG_SECONDS) return reader;
    }
    return null; // All replicas lagging — fall back to writer
  }
}
```

---

## 4. Database Sharding from Node.js

### Hash-Based Sharding

```typescript
import crypto from 'crypto';

class ShardRouter {
  private shards: Pool[];
  private shardCount: number;

  constructor(shardConfigs: ShardConfig[]) {
    this.shards = shardConfigs.map(config => new Pool({
      connectionString: config.url,
      max: config.maxConnections,
    }));
    this.shardCount = this.shards.length;
  }

  // Consistent hashing for shard selection
  getShardIndex(shardKey: string): number {
    const hash = crypto
      .createHash('md5')
      .update(shardKey)
      .digest();

    // Use first 4 bytes as a 32-bit integer
    const hashInt = hash.readUInt32BE(0);
    return hashInt % this.shardCount;
  }

  getShard(shardKey: string): Pool {
    return this.shards[this.getShardIndex(shardKey)];
  }

  // Cross-shard query (scatter-gather)
  async queryAll<T>(sql: string, params?: any[]): Promise<T[]> {
    const results = await Promise.all(
      this.shards.map(shard => shard.query(sql, params))
    );
    return results.flatMap(r => r.rows);
  }

  // Cross-shard aggregation
  async countAll(table: string, where?: string): Promise<number> {
    const query = `SELECT COUNT(*) as count FROM ${table} ${where ? `WHERE ${where}` : ''}`;
    const results = await Promise.all(
      this.shards.map(shard => shard.query(query))
    );
    return results.reduce((sum, r) => sum + Number(r.rows[0].count), 0);
  }
}
```

### Shard Migration (Resharding)

```typescript
// When adding a new shard, you need to migrate data
class ReshardingService {
  async addShard(newShardPool: Pool, newTotalShards: number): Promise<void> {
    // Phase 1: Set up new shard
    // Phase 2: Double-write to both old and new shard locations
    // Phase 3: Backfill — copy existing data to correct new shard
    // Phase 4: Switch reads to new shard mapping
    // Phase 5: Clean up data from old shards

    // This is a simplified illustration; production resharding
    // typically uses consistent hashing with virtual nodes to
    // minimize data movement
  }
}
```

---

## 5. Time-Series Data Patterns

```typescript
// Hypertable approach (with TimescaleDB extension)
// Standard PostgreSQL table that TimescaleDB partitions by time

async function setupTimeSeries() {
  await prisma.$executeRaw`
    CREATE TABLE IF NOT EXISTS metrics (
      time        TIMESTAMPTZ NOT NULL,
      device_id   UUID NOT NULL,
      metric_name VARCHAR(100) NOT NULL,
      value       DOUBLE PRECISION NOT NULL,
      tags        JSONB DEFAULT '{}'
    )
  `;

  // Convert to hypertable (TimescaleDB)
  await prisma.$executeRaw`
    SELECT create_hypertable('metrics', 'time',
      chunk_time_interval => INTERVAL '1 day'
    )
  `;

  // Compression policy (compress chunks older than 7 days)
  await prisma.$executeRaw`
    ALTER TABLE metrics SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'device_id,metric_name'
    )
  `;

  await prisma.$executeRaw`
    SELECT add_compression_policy('metrics', INTERVAL '7 days')
  `;

  // Retention policy (drop data older than 90 days)
  await prisma.$executeRaw`
    SELECT add_retention_policy('metrics', INTERVAL '90 days')
  `;
}

// Efficient time-series queries
async function getDeviceMetrics(deviceId: string, timeRange: TimeRange) {
  // Time-bucket aggregation
  return prisma.$queryRaw`
    SELECT
      time_bucket('1 hour', time) AS bucket,
      metric_name,
      AVG(value) AS avg_value,
      MIN(value) AS min_value,
      MAX(value) AS max_value,
      COUNT(*) AS sample_count
    FROM metrics
    WHERE device_id = ${deviceId}
      AND time >= ${timeRange.start}
      AND time < ${timeRange.end}
    GROUP BY bucket, metric_name
    ORDER BY bucket DESC
  `;
}
```

### Continuous Aggregates

```sql
-- Pre-computed rollups that update automatically
CREATE MATERIALIZED VIEW hourly_metrics
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', time) AS bucket,
  device_id,
  metric_name,
  AVG(value) AS avg_value,
  COUNT(*) AS sample_count
FROM metrics
GROUP BY bucket, device_id, metric_name;

-- Refresh policy
SELECT add_continuous_aggregate_policy('hourly_metrics',
  start_offset => INTERVAL '3 hours',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour'
);
```

---

## 6. Full-Text Search: PostgreSQL tsvector vs Elasticsearch

### PostgreSQL Native Full-Text Search

```typescript
// Set up tsvector column with trigger
await prisma.$executeRaw`
  ALTER TABLE posts ADD COLUMN search_vector tsvector;

  CREATE OR REPLACE FUNCTION posts_search_update() RETURNS trigger AS $$
  BEGIN
    NEW.search_vector :=
      setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
      setweight(to_tsvector('english', COALESCE(NEW.content, '')), 'B');
    RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;

  CREATE TRIGGER posts_search_trigger
    BEFORE INSERT OR UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION posts_search_update();

  CREATE INDEX posts_search_idx ON posts USING GIN (search_vector);
`;

// Search with ranking
async function searchPosts(query: string, pagination: Pagination) {
  return prisma.$queryRaw`
    SELECT
      id, title, content,
      ts_rank(search_vector, websearch_to_tsquery('english', ${query})) AS rank,
      ts_headline('english', content, websearch_to_tsquery('english', ${query}),
        'StartSel=<mark>, StopSel=</mark>, MaxWords=50') AS snippet
    FROM posts
    WHERE search_vector @@ websearch_to_tsquery('english', ${query})
      AND published = true
    ORDER BY rank DESC
    LIMIT ${pagination.limit}
    OFFSET ${(pagination.page - 1) * pagination.limit}
  `;
}
```

### Elasticsearch Integration

```typescript
import { Client } from '@elastic/elasticsearch';

const elastic = new Client({ node: process.env.ELASTICSEARCH_URL });

// Index document on create/update
async function indexPost(post: Post): Promise<void> {
  await elastic.index({
    index: 'posts',
    id: post.id,
    document: {
      title: post.title,
      content: post.content,
      authorName: post.author.name,
      tags: post.tags.map(t => t.name),
      publishedAt: post.publishedAt,
    },
  });
}

// Full-text search with facets
async function searchPosts(query: string, filters: SearchFilters) {
  const result = await elastic.search({
    index: 'posts',
    query: {
      bool: {
        must: [
          {
            multi_match: {
              query,
              fields: ['title^3', 'content', 'tags^2'],
              type: 'best_fields',
              fuzziness: 'AUTO',
            },
          },
        ],
        filter: [
          ...(filters.tags ? [{ terms: { tags: filters.tags } }] : []),
          ...(filters.dateFrom ? [{ range: { publishedAt: { gte: filters.dateFrom } } }] : []),
        ],
      },
    },
    highlight: {
      fields: {
        title: {},
        content: { fragment_size: 150, number_of_fragments: 3 },
      },
    },
    aggs: {
      tags: { terms: { field: 'tags', size: 20 } },
      monthly: { date_histogram: { field: 'publishedAt', calendar_interval: 'month' } },
    },
    from: filters.offset || 0,
    size: filters.limit || 20,
  });

  return {
    hits: result.hits.hits.map(h => ({ ...h._source, score: h._score, highlight: h.highlight })),
    total: (result.hits.total as { value: number }).value,
    facets: result.aggregations,
  };
}
```

### Decision Matrix

| Factor | PostgreSQL tsvector | Elasticsearch |
|--------|-------------------|---------------|
| Setup complexity | None (built-in) | Separate cluster to manage |
| Consistency | Immediate (same transaction) | Eventual (async indexing) |
| Language analysis | Basic (dictionaries, stemming) | Advanced (analyzers, synonyms, phonetic) |
| Faceted search | Manual with GROUP BY | Built-in aggregations |
| Fuzzy matching | Limited | Excellent |
| Scale | Millions of documents | Billions of documents |
| Operational cost | Zero (it is your DB) | Significant (cluster management) |

**Rule of thumb**: Start with PostgreSQL tsvector. Move to Elasticsearch when you need advanced analysis, facets, or the dataset exceeds what PostgreSQL handles comfortably (roughly 10M+ documents with complex queries).

---

## 7. Soft Deletes vs Audit Tables

### Soft Deletes

```typescript
// Prisma schema
// model User {
//   deletedAt DateTime? @map("deleted_at")
// }

// Pros: simple, reversible, maintains referential integrity
// Cons: every query needs WHERE deleted_at IS NULL, index bloat,
//       GDPR compliance issues (data is not actually deleted)

// Middleware approach (see Module 06 README)
// Global filter to exclude soft-deleted records
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

## 8. Database Testing Strategies

### Test Database Setup

```typescript
// Isolated test databases per test suite
import { execSync } from 'child_process';

class TestDatabase {
  private schemaName: string;

  constructor() {
    this.schemaName = `test_${crypto.randomUUID().replace(/-/g, '_')}`;
  }

  async setup(): Promise<PrismaClient> {
    // Create isolated schema
    await globalPrisma.$executeRawUnsafe(
      `CREATE SCHEMA "${this.schemaName}"`
    );

    // Run migrations in test schema
    const url = `${process.env.DATABASE_URL}?schema=${this.schemaName}`;
    execSync(`DATABASE_URL="${url}" npx prisma migrate deploy`, {
      env: { ...process.env, DATABASE_URL: url },
    });

    return new PrismaClient({
      datasources: { db: { url } },
    });
  }

  async teardown(): Promise<void> {
    await globalPrisma.$executeRawUnsafe(
      `DROP SCHEMA "${this.schemaName}" CASCADE`
    );
  }
}
```

### Transaction-Based Test Isolation

```typescript
// Wrap each test in a transaction that rolls back
// Faster than creating/dropping schemas

import { PrismaClient } from '@prisma/client';

let prisma: PrismaClient;

beforeEach(async () => {
  // Start a transaction
  await prisma.$executeRaw`BEGIN`;
  // Create a savepoint
  await prisma.$executeRaw`SAVEPOINT test_start`;
});

afterEach(async () => {
  // Rollback to clean state
  await prisma.$executeRaw`ROLLBACK TO SAVEPOINT test_start`;
  await prisma.$executeRaw`ROLLBACK`;
});
```

### Factory Pattern for Test Data

```typescript
import { faker } from '@faker-js/faker';

class UserFactory {
  static build(overrides: Partial<CreateUserInput> = {}): CreateUserInput {
    return {
      email: faker.internet.email(),
      name: faker.person.fullName(),
      role: 'user',
      ...overrides,
    };
  }

  static async create(
    prisma: PrismaClient,
    overrides: Partial<CreateUserInput> = {}
  ): Promise<User> {
    return prisma.user.create({
      data: this.build(overrides),
    });
  }

  static async createMany(
    prisma: PrismaClient,
    count: number,
    overrides: Partial<CreateUserInput> = {}
  ): Promise<User[]> {
    const data = Array.from({ length: count }, () => this.build(overrides));
    await prisma.user.createMany({ data });
    return prisma.user.findMany({
      where: { email: { in: data.map(d => d.email) } },
    });
  }
}

// Usage in tests
describe('UserService', () => {
  it('should list users with pagination', async () => {
    await UserFactory.createMany(prisma, 25);

    const result = await userService.list({ page: 1, limit: 10 });

    expect(result.data).toHaveLength(10);
    expect(result.total).toBe(25);
    expect(result.hasNextPage).toBe(true);
  });
});
```

### Testing Migrations

```typescript
// Verify migrations are idempotent and reversible
describe('migrations', () => {
  it('should apply all migrations cleanly', async () => {
    const testDb = new TestDatabase();
    const prisma = await testDb.setup(); // Runs all migrations

    // Verify schema is correct
    const tables = await prisma.$queryRaw<{ tablename: string }[]>`
      SELECT tablename FROM pg_tables WHERE schemaname = ${testDb.schemaName}
    `;

    expect(tables.map(t => t.tablename)).toContain('users');
    expect(tables.map(t => t.tablename)).toContain('posts');

    await testDb.teardown();
  });

  it('should handle rollback of latest migration', async () => {
    // Apply all migrations, then rollback the last one
    // Verify the database is still in a valid state
    // This catches migrations that cannot be reversed
  });
});
```
