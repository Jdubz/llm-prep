# Module 06: Database Patterns

## Prerequisites

This module assumes extensive experience with relational databases, SQL, and at least one ORM. We focus on the architectural decisions, performance trade-offs, and failure modes that matter in production Node.js/TypeScript systems.

---

## 1. ORM Comparison

### 1.1 Prisma vs Drizzle vs TypeORM vs Knex

| Feature | Prisma | Drizzle | TypeORM | Knex |
|---------|--------|---------|---------|------|
| **Approach** | Full ORM with codegen | SQL-like type-safe query builder | Traditional ORM (ActiveRecord + Data Mapper) | Query builder only |
| **Type Safety** | Generated types from schema | Types inferred from schema definitions | Decorators, manual types | Manual types (partial inference) |
| **Query API** | Custom DSL (`findMany`, `include`) | SQL-like (`select().from().where()`) | Repository/QueryBuilder | SQL-like builder |
| **Raw SQL** | `$queryRaw` tagged templates | `sql` tagged templates | `query()` method | `.raw()` method |
| **Migrations** | `prisma migrate` (auto-generated) | `drizzle-kit` (auto-generated) | TypeORM CLI (manual or auto) | Knex CLI (manual) |
| **Performance** | Good (Rust query engine) | Excellent (thin SQL layer) | Moderate (heavy abstraction) | Excellent (minimal overhead) |
| **Connection pooling** | Built-in (configurable) | Delegates to driver | Built-in | Built-in |
| **Learning curve** | Medium (custom DSL) | Low (if you know SQL) | High (many patterns) | Low (SQL knowledge) |
| **Edge/serverless** | Prisma Accelerate or driver adapters | Native driver support | Poorly suited | Driver-dependent |

### 1.2 When to Use What

**Prisma**: Teams that want guardrails. Schema-first design, auto-generated migrations, excellent DX. The generated client catches errors at build time. Trade-off: the Rust engine binary adds ~15MB, and complex queries sometimes require `$queryRaw`.

**Drizzle**: Teams that want SQL control with TypeScript safety. If your team thinks in SQL, Drizzle will feel natural. Best performance characteristics of any ORM-like tool. Trade-off: smaller ecosystem, fewer escape hatches for very complex relational queries.

**TypeORM**: Legacy projects already using it. Not recommended for new projects — known issues with type safety gaps, inconsistent APIs between ActiveRecord and Data Mapper, and maintenance velocity concerns.

**Knex**: When you want a pure query builder without ORM abstractions. Good for teams that write and optimize their own SQL. Often paired with a separate model layer.

---

## 2. Prisma Deep Dive

### 2.1 Schema Design

```prisma
// prisma/schema.prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["fullTextSearch", "metrics"]
  binaryTargets   = ["native", "linux-musl-openssl-3.0.x"] // For Docker
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  role      Role     @default(USER)
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  posts     Post[]
  profile   Profile?
  sessions  Session[]

  @@map("users") // Table name
  @@index([email])
  @@index([createdAt])
}

model Post {
  id          String   @id @default(cuid())
  title       String   @db.VarChar(255)
  content     String?  @db.Text
  published   Boolean  @default(false)
  authorId    String   @map("author_id")
  categoryId  String?  @map("category_id")
  publishedAt DateTime? @map("published_at")
  createdAt   DateTime @default(now()) @map("created_at")

  author   User      @relation(fields: [authorId], references: [id], onDelete: Cascade)
  category Category? @relation(fields: [categoryId], references: [id])
  tags     Tag[]

  @@map("posts")
  @@index([authorId])
  @@index([published, publishedAt(sort: Desc)]) // Composite index
  @@index([title], type: GIN)                    // Full-text search index
}

model Tag {
  id    String @id @default(cuid())
  name  String @unique
  posts Post[]

  @@map("tags")
}

enum Role {
  USER
  ADMIN
  MODERATOR
}
```

### 2.2 Client Generation and Usage

```typescript
import { PrismaClient, Prisma } from '@prisma/client';

// Singleton pattern for Prisma Client
const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient({
  log: [
    { level: 'query', emit: 'event' },
    { level: 'error', emit: 'stdout' },
    { level: 'warn', emit: 'stdout' },
  ],
});

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}

// Query logging for development
prisma.$on('query', (e) => {
  if (e.duration > 100) {
    console.warn(`Slow query (${e.duration}ms): ${e.query}`);
  }
});
```

### 2.3 Relations and Includes

```typescript
// Eager loading with include (generates JOINs)
const userWithPosts = await prisma.user.findUnique({
  where: { id: userId },
  include: {
    posts: {
      where: { published: true },
      orderBy: { publishedAt: 'desc' },
      take: 10,
      include: {
        tags: true,
        category: { select: { name: true } },
      },
    },
    profile: true,
  },
});

// Select only needed fields (reduces data transfer)
const userSummary = await prisma.user.findMany({
  select: {
    id: true,
    name: true,
    _count: {
      select: { posts: { where: { published: true } } },
    },
  },
});
```

### 2.4 Raw Queries (When the ORM Is Not Enough)

```typescript
// Tagged template literal — parameterized automatically
const users = await prisma.$queryRaw<User[]>`
  SELECT u.*, COUNT(p.id) as post_count
  FROM users u
  LEFT JOIN posts p ON p.author_id = u.id AND p.published = true
  WHERE u.created_at > ${thirtyDaysAgo}
  GROUP BY u.id
  HAVING COUNT(p.id) > ${minPosts}
  ORDER BY post_count DESC
  LIMIT ${limit}
`;

// Dynamic queries with Prisma.sql
function buildSearchQuery(filters: SearchFilters) {
  const conditions: Prisma.Sql[] = [];

  if (filters.name) {
    conditions.push(Prisma.sql`name ILIKE ${'%' + filters.name + '%'}`);
  }
  if (filters.role) {
    conditions.push(Prisma.sql`role = ${filters.role}`);
  }

  const whereClause = conditions.length > 0
    ? Prisma.sql`WHERE ${Prisma.join(conditions, ' AND ')}`
    : Prisma.empty;

  return prisma.$queryRaw`
    SELECT * FROM users ${whereClause} ORDER BY created_at DESC
  `;
}
```

### 2.5 Middleware

```typescript
// Soft delete middleware
prisma.$use(async (params, next) => {
  // Intercept delete and convert to soft delete
  if (params.action === 'delete') {
    params.action = 'update';
    params.args.data = { deletedAt: new Date() };
  }

  if (params.action === 'deleteMany') {
    params.action = 'updateMany';
    params.args.data = { deletedAt: new Date() };
  }

  // Filter out soft-deleted records on reads
  if (params.action === 'findMany' || params.action === 'findFirst') {
    if (!params.args) params.args = {};
    if (!params.args.where) params.args.where = {};
    params.args.where.deletedAt = null;
  }

  return next(params);
});

// Performance monitoring middleware
prisma.$use(async (params, next) => {
  const start = performance.now();
  const result = await next(params);
  const duration = performance.now() - start;

  if (duration > 200) {
    logger.warn({
      model: params.model,
      action: params.action,
      duration: Math.round(duration),
    }, 'Slow Prisma query detected');
  }

  return result;
});
```

### 2.6 Connection Pooling with PgBouncer

```
# Direct connection (for migrations)
DATABASE_URL="postgresql://user:pass@db-host:5432/mydb"

# Pooled connection via PgBouncer (for application queries)
DATABASE_URL="postgresql://user:pass@pgbouncer-host:6432/mydb?pgbouncer=true"
```

```prisma
datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_DATABASE_URL") // Used for migrations
}
```

**Why PgBouncer?** PostgreSQL forks a process per connection (~10MB each). With 20 serverless function instances each opening 5 connections, you have 100 processes. PgBouncer multiplexes thousands of client connections over a small pool of actual database connections.

**PgBouncer modes:**
- `session`: Connection assigned for the entire client session (safest, least efficient)
- `transaction`: Connection assigned per transaction (best for most apps)
- `statement`: Connection assigned per statement (breaks multi-statement transactions)

---

## 3. Drizzle Deep Dive

### 3.1 Schema Definition

```typescript
// src/db/schema.ts
import {
  pgTable, varchar, text, boolean, timestamp,
  uuid, pgEnum, index, uniqueIndex, integer,
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const roleEnum = pgEnum('role', ['user', 'admin', 'moderator']);

export const users = pgTable('users', {
  id: uuid('id').defaultRandom().primaryKey(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  name: varchar('name', { length: 100 }),
  role: roleEnum('role').default('user').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
}, (table) => ({
  emailIdx: uniqueIndex('users_email_idx').on(table.email),
  createdAtIdx: index('users_created_at_idx').on(table.createdAt),
}));

export const posts = pgTable('posts', {
  id: uuid('id').defaultRandom().primaryKey(),
  title: varchar('title', { length: 255 }).notNull(),
  content: text('content'),
  published: boolean('published').default(false).notNull(),
  authorId: uuid('author_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  publishedAt: timestamp('published_at'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (table) => ({
  authorIdx: index('posts_author_id_idx').on(table.authorId),
  publishedIdx: index('posts_published_idx').on(table.published, table.publishedAt),
}));

// Relations (for relational query API)
export const usersRelations = relations(users, ({ many, one }) => ({
  posts: many(posts),
  profile: one(profiles),
}));

export const postsRelations = relations(posts, ({ one, many }) => ({
  author: one(users, { fields: [posts.authorId], references: [users.id] }),
  tags: many(postTags),
}));
```

### 3.2 Query API (SQL-Like)

```typescript
import { drizzle } from 'drizzle-orm/node-postgres';
import { eq, and, gt, like, desc, sql, count } from 'drizzle-orm';
import * as schema from './schema';

const db = drizzle(pool, { schema });

// Select with conditions
const publishedPosts = await db
  .select({
    id: posts.id,
    title: posts.title,
    authorName: users.name,
  })
  .from(posts)
  .innerJoin(users, eq(posts.authorId, users.id))
  .where(and(
    eq(posts.published, true),
    gt(posts.publishedAt, thirtyDaysAgo),
  ))
  .orderBy(desc(posts.publishedAt))
  .limit(20);

// Aggregation
const postCounts = await db
  .select({
    authorId: posts.authorId,
    authorName: users.name,
    postCount: count(posts.id),
  })
  .from(posts)
  .innerJoin(users, eq(posts.authorId, users.id))
  .where(eq(posts.published, true))
  .groupBy(posts.authorId, users.name)
  .having(gt(count(posts.id), 5));

// Relational queries (Prisma-like API)
const usersWithPosts = await db.query.users.findMany({
  with: {
    posts: {
      where: eq(posts.published, true),
      orderBy: desc(posts.publishedAt),
      limit: 10,
      with: { tags: true },
    },
  },
});
```

### 3.3 Drizzle Performance Advantages

Drizzle generates SQL directly from TypeScript — no Rust engine, no query plan layer. The generated SQL is predictable:

```typescript
// What you write
const result = await db
  .select()
  .from(users)
  .where(eq(users.email, email));

// What gets executed (no surprise)
// SELECT * FROM users WHERE email = $1

// Prisma equivalent might generate:
// SELECT "public"."users"."id", "public"."users"."email", ...
// FROM "public"."users" WHERE "public"."users"."email" = $1
```

---

## 4. Migrations

### 4.1 Up/Down Migrations

```typescript
// Knex-style explicit up/down
export async function up(knex: Knex): Promise<void> {
  await knex.schema.createTable('posts', (table) => {
    table.uuid('id').primary().defaultTo(knex.fn.uuid());
    table.varchar('title', 255).notNull();
    table.text('content');
    table.boolean('published').defaultTo(false);
    table.uuid('author_id').notNull().references('users.id').onDelete('CASCADE');
    table.timestamp('created_at').defaultTo(knex.fn.now());
    table.index(['author_id']);
    table.index(['published', 'created_at']);
  });
}

export async function down(knex: Knex): Promise<void> {
  await knex.schema.dropTable('posts');
}
```

### 4.2 Zero-Downtime Migrations: Expand/Contract Pattern

The expand/contract pattern ensures no deployment step breaks the running application:

**Phase 1: Expand** (backward compatible)
```sql
-- Add new column (nullable, no breaking change)
ALTER TABLE users ADD COLUMN display_name VARCHAR(100);

-- Backfill data (in batches to avoid locking)
UPDATE users SET display_name = name WHERE display_name IS NULL LIMIT 1000;
```

**Phase 2: Migrate** (application reads from both, writes to both)
```typescript
// Application code during transition
async function updateUser(id: string, data: UpdateUserInput) {
  await prisma.user.update({
    where: { id },
    data: {
      name: data.name,
      displayName: data.name, // Write to both columns
    },
  });
}
```

**Phase 3: Contract** (remove old column after all code is deployed)
```sql
-- Only after ALL application instances use new column
ALTER TABLE users DROP COLUMN name;
```

### 4.3 Data Migrations

```typescript
// Data migration — separate from schema migration
// Run as a background job, not during deployment

async function migrateUserNames() {
  const BATCH_SIZE = 1000;
  let processed = 0;
  let hasMore = true;

  while (hasMore) {
    const users = await prisma.$queryRaw<{ id: string; name: string }[]>`
      SELECT id, name FROM users
      WHERE display_name IS NULL
      ORDER BY id
      LIMIT ${BATCH_SIZE}
    `;

    if (users.length === 0) {
      hasMore = false;
      break;
    }

    // Batch update
    await prisma.$executeRaw`
      UPDATE users
      SET display_name = name
      WHERE id = ANY(${users.map(u => u.id)})
    `;

    processed += users.length;
    logger.info(`Migrated ${processed} users`);

    // Yield to avoid overwhelming the database
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}
```

### 4.4 Migration Squashing

Over time, migration files accumulate. Squashing consolidates them:

```bash
# Prisma: reset migration history (creates single baseline)
npx prisma migrate diff \
  --from-empty \
  --to-schema-datamodel prisma/schema.prisma \
  --script > prisma/migrations/0_baseline/migration.sql

# Drizzle
npx drizzle-kit squash

# Mark existing database as already at baseline
npx prisma migrate resolve --applied 0_baseline
```

**Warning**: Only squash migrations that have been applied to ALL environments. Never squash unapplied migrations.

---

## 5. Connection Pooling

### 5.1 Why Pooling Matters

Each PostgreSQL connection consumes ~10MB of memory (process fork). Without pooling:

```
20 serverless instances x 5 connections each = 100 connections
100 connections x 10MB = 1GB just for connection overhead
PostgreSQL default max_connections = 100 (hit the limit)
```

### 5.2 Pool Sizing Formula

From the PostgreSQL wiki and battle-tested in production:

```
optimal_pool_size = (core_count * 2) + effective_spindle_count
```

For a typical cloud database with SSD:
- 4 vCPUs: pool size = (4 * 2) + 1 = 9
- 8 vCPUs: pool size = (8 * 2) + 1 = 17

**Counter-intuitive truth**: Smaller pools often outperform larger ones. A pool of 10 connections will often handle more throughput than a pool of 100 due to reduced context switching and lock contention.

### 5.3 Pool Configuration

```typescript
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,                        // Maximum connections in pool
  min: 5,                         // Minimum idle connections
  idleTimeoutMillis: 30000,       // Close idle connections after 30s
  connectionTimeoutMillis: 5000,  // Fail if cannot connect in 5s
  maxUses: 7500,                  // Close connection after N uses (prevents memory leaks)
  allowExitOnIdle: true,          // Allow process to exit when pool is idle
});

// Monitor pool health
pool.on('error', (err) => {
  logger.error('Unexpected pool error', err);
});

// Expose pool metrics
function getPoolMetrics() {
  return {
    totalCount: pool.totalCount,     // Total connections (active + idle)
    idleCount: pool.idleCount,       // Available connections
    waitingCount: pool.waitingCount, // Queries waiting for a connection
  };
}
```

### 5.4 PgBouncer vs Application-Level Pooling

| Feature | PgBouncer | Application Pool (pg Pool) |
|---------|-----------|---------------------------|
| Location | Separate process/container | In-process |
| Shared across instances | Yes | No (per-process) |
| Transaction pooling | Yes | No (session-level only) |
| Prepared statements | Limited (transaction mode) | Full support |
| Overhead | Extra network hop | None |
| Serverless-friendly | Yes (solves connection storm) | No (each instance has own pool) |

**Use both**: PgBouncer between your app instances and PostgreSQL, plus application-level pooling within each instance. PgBouncer handles the cross-instance connection management; the application pool handles local connection reuse.

---

## 6. Transactions

### 6.1 ACID Properties in Practice

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

### 6.2 Isolation Levels

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Performance |
|-------|-----------|-------------------|--------------|-------------|
| Read Uncommitted | Possible | Possible | Possible | Fastest |
| Read Committed | Prevented | Possible | Possible | Fast (PG default) |
| Repeatable Read | Prevented | Prevented | Possible* | Moderate |
| Serializable | Prevented | Prevented | Prevented | Slowest |

*PostgreSQL's Repeatable Read actually prevents phantom reads too (it uses snapshot isolation internally).

**When to use each:**
- **Read Committed** (default): Most queries. Fine for 90% of use cases.
- **Repeatable Read**: Reports that must see a consistent snapshot. Financial summaries.
- **Serializable**: Concurrent operations that must appear to execute one at a time. Inventory management, double-spend prevention.

### 6.3 Optimistic vs Pessimistic Locking

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

### 6.4 Distributed Transactions

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

## 7. Query Optimization

### 7.1 EXPLAIN ANALYZE

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

### 7.2 N+1 Detection

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

### 7.3 Indexing Strategies

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
-- Smaller index, only useful for queries that include WHERE published = true

-- Expression index
CREATE INDEX idx_users_email_lower ON users (LOWER(email));
-- Supports: WHERE LOWER(email) = 'user@example.com'

-- GIN index for full-text search
CREATE INDEX idx_posts_search ON posts USING GIN (to_tsvector('english', title || ' ' || content));

-- GIN index for JSONB
CREATE INDEX idx_users_metadata ON users USING GIN (metadata jsonb_path_ops);
```

### 7.4 Index Anti-Patterns

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

---

## 8. Multi-Tenancy Patterns

### 8.1 Shared Schema with tenant_id (Most Common)

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

### 8.2 Row-Level Security (RLS) in PostgreSQL

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

**RLS advantage**: Enforcement at the database level. Even raw queries cannot bypass tenant isolation. But adds overhead per query for the config lookup.

### 8.3 Schema per Tenant

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

**Trade-offs:**

| Pattern | Isolation | Complexity | Scalability | Migration Pain |
|---------|-----------|------------|-------------|----------------|
| Shared schema + tenant_id | Application-enforced | Low | High | Low (one migration) |
| Row-Level Security | Database-enforced | Medium | High | Low (one migration) |
| Schema per tenant | Physical | Medium-High | Medium | High (N migrations) |
| Database per tenant | Complete | High | Low | Highest (N databases) |

---

## 9. Expert Interview Questions

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
