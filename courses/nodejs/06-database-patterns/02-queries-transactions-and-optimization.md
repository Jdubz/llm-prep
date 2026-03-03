# 02 – Queries, Transactions, and Optimization

## Transactions

### ACID Properties in Practice

```typescript
// Prisma interactive transaction
async function transferCredits(fromId: string, toId: string, amount: number) {
  return prisma.$transaction(async (tx) => {
    // All operations within this callback share a single database transaction

    const sender = await tx.user.update({
      where: { id: fromId },
      data: { credits: { decrement: amount } },
    });

    if (sender.credits < 0) {
      throw new Error('Insufficient credits'); // Triggers rollback
    }

    await tx.user.update({
      where: { id: toId },
      data: { credits: { increment: amount } },
    });

    await tx.transaction.create({
      data: {
        fromUserId: fromId,
        toUserId: toId,
        amount,
        type: 'TRANSFER',
      },
    });

    return sender;
  }, {
    maxWait: 5000,     // Max time to wait for a connection
    timeout: 10000,    // Max time for the entire transaction
    isolationLevel: Prisma.TransactionIsolationLevel.Serializable,
  });
}
```

### Transaction Isolation Levels

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Performance | Use Case |
|-------|-----------|-------------------|--------------|-------------|----------|
| Read Uncommitted | Possible | Possible | Possible | Fastest | Almost never in PostgreSQL |
| Read Committed | Prevented | Possible | Possible | Fast (PG default) | Default. Most CRUD operations |
| Repeatable Read | Prevented | Prevented | No* | Moderate | Consistent reports, financial summaries |
| Serializable | Prevented | Prevented | Prevented | Slowest | Inventory, double-spend prevention |

*PostgreSQL's Repeatable Read actually prevents phantom reads too (it uses snapshot isolation internally).

**When to use each:**
- **Read Committed** (default): Most queries. Fine for 90% of use cases.
- **Repeatable Read**: Reports that must see a consistent snapshot. Financial summaries.
- **Serializable**: Concurrent operations that must appear to execute one at a time. Inventory management, double-spend prevention.

### Isolation Level Decision Guide

```
Is this a simple read/write?
  └── Yes → Read Committed (default)

Does the transaction read data and then make decisions based on it?
  └── Yes → Is there high contention?
              ├── Low contention → Optimistic locking (version column)
              └── High contention → SELECT ... FOR UPDATE (pessimistic)

Must multiple reads within the transaction see consistent data?
  └── Yes → Repeatable Read

Must concurrent transactions behave as if they ran sequentially?
  └── Yes → Serializable (be prepared for serialization failures + retries)
```

### Optimistic vs Pessimistic Locking

```typescript
// OPTIMISTIC: Check version before committing
// Best for: low contention, reads >> writes

// Schema includes a version field
// model Product { version Int @default(0) }

async function updateProductOptimistic(id: string, data: UpdateData) {
  const MAX_RETRIES = 3;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    const product = await prisma.product.findUnique({ where: { id } });

    try {
      return await prisma.product.update({
        where: {
          id,
          version: product!.version, // Only succeed if version hasn't changed
        },
        data: {
          ...data,
          version: { increment: 1 },
        },
      });
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError) {
        if (error.code === 'P2025') {
          // Record was modified by another transaction, retry
          if (attempt === MAX_RETRIES - 1) throw new ConflictError('Concurrent modification');
          continue;
        }
      }
      throw error;
    }
  }
}
```

```typescript
// PESSIMISTIC: Lock row before reading
// Best for: high contention, critical sections

async function updateInventoryPessimistic(productId: string, quantity: number) {
  return prisma.$transaction(async (tx) => {
    // SELECT ... FOR UPDATE — locks the row
    const [product] = await tx.$queryRaw<Product[]>`
      SELECT * FROM products WHERE id = ${productId} FOR UPDATE
    `;

    if (product.stock < quantity) {
      throw new InsufficientStockError();
    }

    return tx.product.update({
      where: { id: productId },
      data: { stock: { decrement: quantity } },
    });
  });
}
```

**Decision framework:**
- **Optimistic**: Best for low contention. No locks held. Detect conflicts at commit time via version column. Retries are cheap when conflicts are rare. Use for: user profile updates, content editing, most CRUD operations.
- **Pessimistic**: Best for high contention. Locks row immediately. No retries needed but holds locks longer. Use for: inventory management, financial transactions, seat reservations — any scenario where conflicting updates are frequent and the cost of a failed optimistic retry is high.
- **Hybrid**: Start optimistic, escalate to pessimistic if retry rate exceeds threshold.

### Distributed Transactions (Saga Pattern)

True distributed transactions (2PC) are rare in Node.js. Prefer the Saga pattern:

```typescript
// Saga: sequence of local transactions with compensating actions
class OrderSaga {
  async execute(orderData: CreateOrderInput) {
    const steps: SagaStep[] = [];

    try {
      // Step 1: Reserve inventory
      const reservation = await inventoryService.reserve(orderData.items);
      steps.push({ compensate: () => inventoryService.release(reservation.id) });

      // Step 2: Charge payment
      const payment = await paymentService.charge(orderData.paymentMethod, orderData.total);
      steps.push({ compensate: () => paymentService.refund(payment.id) });

      // Step 3: Create order
      const order = await orderService.create({ ...orderData, paymentId: payment.id });
      steps.push({ compensate: () => orderService.cancel(order.id) });

      // Step 4: Send notification
      await notificationService.sendOrderConfirmation(order);

      return order;
    } catch (error) {
      // Compensate in reverse order
      for (const step of steps.reverse()) {
        try {
          await step.compensate();
        } catch (compensateError) {
          logger.error('Saga compensation failed', {
            error: compensateError,
            originalError: error,
          });
          // Queue for manual intervention
          await deadLetterQueue.push({ saga: 'order', step, error: compensateError });
        }
      }
      throw error;
    }
  }
}
```

---

## Query Optimization

### EXPLAIN ANALYZE

The most important tool for query performance. Always run it before adding an index.

```typescript
// Get query execution plan
async function explainQuery(query: string, params: any[]) {
  const result = await prisma.$queryRawUnsafe(
    `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ${query}`,
    ...params,
  );
  return result;
}

// What to look for in the output:
// - Seq Scan on large tables → needs an index
// - Nested Loop with high row counts → consider Hash Join
// - Sort with high cost → consider index on sort column
// - Bitmap Heap Scan → index is being used but many rows match
// - actual rows vs planned rows mismatch → stale statistics (ANALYZE)
```

### N+1 Detection and the DataLoader Pattern

```typescript
// N+1 problem: fetching related data in a loop
// BAD: 1 query for users + N queries for posts
const users = await prisma.user.findMany();
for (const user of users) {
  user.posts = await prisma.post.findMany({
    where: { authorId: user.id },
  }); // This executes N times!
}

// GOOD: Single query with include
const users = await prisma.user.findMany({
  include: { posts: true },
});

// GOOD: Manual batch loading (DataLoader pattern)
import DataLoader from 'dataloader';

const postLoader = new DataLoader<string, Post[]>(async (userIds) => {
  const posts = await prisma.post.findMany({
    where: { authorId: { in: [...userIds] } },
  });

  const postsByAuthor = new Map<string, Post[]>();
  for (const post of posts) {
    const existing = postsByAuthor.get(post.authorId) || [];
    existing.push(post);
    postsByAuthor.set(post.authorId, existing);
  }

  return userIds.map(id => postsByAuthor.get(id) || []);
});
```

### Indexing Strategies

```sql
-- Single-column index: equality and range queries on one column
CREATE INDEX idx_users_email ON users (email);

-- Composite index: queries filtering on multiple columns
-- Column order matters: put equality conditions first, range conditions last
CREATE INDEX idx_posts_author_published ON posts (author_id, published, created_at DESC);
-- Supports: WHERE author_id = X
-- Supports: WHERE author_id = X AND published = true
-- Supports: WHERE author_id = X AND published = true ORDER BY created_at DESC
-- Does NOT efficiently support: WHERE published = true (skips first column)

-- Covering index: includes all columns needed by the query (index-only scan)
CREATE INDEX idx_posts_covering ON posts (author_id, published)
INCLUDE (title, created_at);
-- Query can be answered entirely from the index, no table lookup

-- Partial index: index only a subset of rows
CREATE INDEX idx_posts_published ON posts (published_at DESC)
WHERE published = true;
-- 95% smaller if only 5% of posts are published

-- Expression index
CREATE INDEX idx_users_email_lower ON users (LOWER(email));
-- Supports: WHERE LOWER(email) = 'user@example.com'

-- GIN index for full-text search
CREATE INDEX idx_posts_search ON posts USING GIN (to_tsvector('english', title || ' ' || content));

-- GIN index for JSONB
CREATE INDEX idx_users_metadata ON users USING GIN (metadata jsonb_path_ops);
```

### Index Type Selection

| Query Pattern | Index Type | Example |
|--------------|-----------|---------|
| Equality: `WHERE email = ?` | B-tree (default) | `CREATE INDEX ON users (email)` |
| Range: `WHERE created_at > ?` | B-tree | `CREATE INDEX ON users (created_at)` |
| Multi-column: `WHERE a = ? AND b = ?` | Composite B-tree | `CREATE INDEX ON t (a, b)` |
| Full-text: `WHERE search @@ query` | GIN | `CREATE INDEX ON posts USING GIN (search_vector)` |
| JSONB: `WHERE data @> '{"key": "val"}'` | GIN | `CREATE INDEX ON t USING GIN (data jsonb_path_ops)` |
| Pattern: `WHERE name LIKE 'abc%'` | B-tree (with text_pattern_ops) | `CREATE INDEX ON t (name text_pattern_ops)` |
| Geospatial | GiST | `CREATE INDEX ON t USING GIST (location)` |

### Composite Index Column Order Rule

```
Rule: Equality columns FIRST, then range/sort columns LAST

Good:  (tenant_id, status, created_at DESC)
       Supports: WHERE tenant_id = ? AND status = ? ORDER BY created_at DESC

Bad:   (created_at DESC, tenant_id, status)
       Only efficiently supports: ORDER BY created_at DESC
```

### Index Anti-Patterns

```sql
-- Over-indexing: every index slows down writes
-- Each INSERT/UPDATE must update all indexes
-- Rule of thumb: 5-7 indexes per table maximum for write-heavy tables

-- Redundant indexes: (a, b) makes (a) redundant
-- The composite index (a, b) already supports queries on just (a)

-- Low-cardinality indexes: indexing a boolean column with 50/50 distribution
-- The index does not help — query planner will choose seq scan anyway
-- Exception: partial index WHERE published = true (if only 5% are published)

-- Unused indexes: check pg_stat_user_indexes
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### When to Add an Index

```
Query appears in slow query log (> 100ms)?
  └── Check EXPLAIN ANALYZE
        ├── Seq Scan on large table → Add index on WHERE columns
        ├── Sort with high cost → Add index on ORDER BY columns
        └── Nested Loop with many rows → Consider composite index on JOIN columns
```

---

## Complex Queries and Aggregations

### Read Replicas with Connection Routing

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
    const store = AsyncLocalStorage.getStore();
    if (store) store.requiresConsistency = true;
    next();
  };
}
```

### Replication Lag Handling

```typescript
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

### Full-Text Search: PostgreSQL tsvector vs Elasticsearch

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

#### Search Tool Decision Matrix

| Factor | PostgreSQL tsvector | Elasticsearch |
|--------|-------------------|---------------|
| Setup complexity | None (built-in) | Separate cluster to manage |
| Consistency | Immediate (same transaction) | Eventual (async indexing) |
| Language analysis | Basic (dictionaries, stemming) | Advanced (analyzers, synonyms, phonetic) |
| Faceted search | Manual with GROUP BY | Built-in aggregations |
| Fuzzy matching | Limited | Excellent |
| Scale | Millions of documents | Billions of documents |
| Operational cost | Zero (it is your DB) | Significant (cluster management) |

**Rule of thumb**: Start with PostgreSQL tsvector. Move to Elasticsearch when you need advanced analysis, facets, or the dataset exceeds ~10M+ documents with complex queries.

### Time-Series Data Patterns

```typescript
// Hypertable approach (with TimescaleDB extension)
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

  // Compression policy
  await prisma.$executeRaw`
    ALTER TABLE metrics SET (
      timescaledb.compress,
      timescaledb.compress_segmentby = 'device_id,metric_name'
    )
  `;

  await prisma.$executeRaw`SELECT add_compression_policy('metrics', INTERVAL '7 days')`;

  // Retention policy
  await prisma.$executeRaw`SELECT add_retention_policy('metrics', INTERVAL '90 days')`;
}

// Time-bucket aggregation
async function getDeviceMetrics(deviceId: string, timeRange: TimeRange) {
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

## Database Testing Strategies

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
    await globalPrisma.$executeRawUnsafe(
      `CREATE SCHEMA "${this.schemaName}"`
    );

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

let prisma: PrismaClient;

beforeEach(async () => {
  await prisma.$executeRaw`BEGIN`;
  await prisma.$executeRaw`SAVEPOINT test_start`;
});

afterEach(async () => {
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
