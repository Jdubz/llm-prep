# 01 – Prisma and Drizzle

## ORM Landscape: Choosing the Right Tool

Before writing a line of schema code, choose your ORM deliberately. The decision shapes every query, migration, and debug session for the lifetime of the project.

### ORM Comparison Table

| Feature | Prisma | Drizzle | TypeORM | Knex |
|---------|--------|---------|---------|------|
| **Approach** | Full ORM with codegen | SQL-like type-safe query builder | Traditional ORM (ActiveRecord + Data Mapper) | Query builder only |
| **Type Safety** | Generated (build-time) | Inferred (compile-time) | Decorators (runtime) | Manual |
| **Query Style** | Custom DSL (`findMany`, `include`) | SQL-like (`select().from().where()`) | Repository + QueryBuilder | SQL-like builder |
| **Raw SQL** | `$queryRaw` (tagged) | `sql` (tagged) | `.query()` | `.raw()` |
| **Migrations** | Auto-generated (`prisma migrate`) | Auto-generated (`drizzle-kit`) | Auto or manual | Manual |
| **Performance** | Good (Rust query engine) | Excellent (thin layer) | Moderate | Excellent |
| **Bundle Size** | ~15MB (engine binary) | ~50KB | ~2MB | ~500KB |
| **Edge/Serverless** | Needs Accelerate or adapter | Native support | Poor | Driver-dependent |
| **Schema Definition** | `.prisma` file (DSL) | TypeScript | Decorators or entity files | N/A (manual SQL) |
| **Relation Loading** | `include` / `select` | `with` (relational API) | `relations` / `leftJoinAndSelect` | Manual JOINs |
| **Best For** | DX-focused teams | SQL-savvy teams | Legacy projects | Pure query building |
| **Learning Curve** | Medium (custom DSL) | Low (if you know SQL) | High (many patterns) | Low (SQL knowledge) |

### When to Use What

**Prisma**: Teams that want guardrails. Schema-first design, auto-generated migrations, excellent DX. The generated client catches errors at build time. Trade-off: the Rust engine binary adds ~15MB, and complex queries sometimes require `$queryRaw`.

**Drizzle**: Teams that want SQL control with TypeScript safety. If your team thinks in SQL, Drizzle will feel natural. Best performance characteristics of any ORM-like tool. Trade-off: smaller ecosystem, fewer escape hatches for very complex relational queries.

**TypeORM**: Legacy projects already using it. Not recommended for new projects — known issues with type safety gaps, inconsistent APIs between ActiveRecord and Data Mapper, and maintenance velocity concerns.

**Knex**: When you want a pure query builder without ORM abstractions. Good for teams that write and optimize their own SQL. Often paired with a separate model layer.

---

## Prisma Deep Dive

### Schema Design

The Prisma schema is the single source of truth for your data model. It drives client generation, migration generation, and type safety.

```prisma
// prisma/schema.prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["fullTextSearch", "metrics"]
  binaryTargets   = ["native", "linux-musl-openssl-3.0.x"] // For Docker
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_DATABASE_URL") // For migrations (bypasses PgBouncer)
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  role      Role     @default(USER)
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")
  deletedAt DateTime? @map("deleted_at")

  posts     Post[]
  profile   Profile?
  sessions  Session[]

  @@map("users") // Table name
  @@index([email])
  @@index([createdAt])
}

model Post {
  id          String    @id @default(cuid())
  title       String    @db.VarChar(255)
  content     String?   @db.Text
  published   Boolean   @default(false)
  authorId    String    @map("author_id")
  categoryId  String?   @map("category_id")
  publishedAt DateTime? @map("published_at")
  createdAt   DateTime  @default(now()) @map("created_at")

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

### Client Generation and Singleton Pattern

Never create a new `PrismaClient` per request. In development hot-reload environments, module caching prevents creating a new instance each hot-reload.

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

### Relations and Includes

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

### Common Prisma Operations Quick Reference

```typescript
// Find with relations
prisma.user.findUnique({ where: { id }, include: { posts: true } })

// Filtered list with pagination
prisma.post.findMany({
  where: { published: true, authorId: userId },
  orderBy: { createdAt: 'desc' },
  skip: (page - 1) * limit,
  take: limit,
})

// Upsert
prisma.user.upsert({
  where: { email },
  update: { name },
  create: { email, name },
})

// Transaction
prisma.$transaction(async (tx) => {
  await tx.user.update({ where: { id: from }, data: { balance: { decrement: amount } } });
  await tx.user.update({ where: { id: to }, data: { balance: { increment: amount } } });
})

// Aggregate
prisma.post.aggregate({
  _count: { id: true },
  _avg: { viewCount: true },
  where: { published: true },
})

// Raw query (parameterized)
prisma.$queryRaw`SELECT * FROM users WHERE email = ${email}`
```

### Raw Queries: When the ORM Is Not Enough

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

### Prisma Middleware

Middleware intercepts all Prisma Client operations before they reach the database. Useful for soft deletes, audit logging, and performance monitoring.

```typescript
// Soft delete middleware
prisma.$use(async (params, next) => {
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

### Connection Pooling with PgBouncer

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

## Drizzle Deep Dive

### Schema Definition

Drizzle schemas are plain TypeScript. This is both its strength (full IDE support, no DSL to learn) and its style (more verbose than Prisma's `.prisma` file).

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

### Query API: SQL-Like and Relational

Drizzle offers two query styles. The SQL-like API mirrors SQL syntax directly. The relational query API resembles Prisma's `include`.

```typescript
import { drizzle } from 'drizzle-orm/node-postgres';
import { eq, and, gt, like, desc, sql, count } from 'drizzle-orm';
import * as schema from './schema';

const db = drizzle(pool, { schema });

// SQL-like: select with join and conditions
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

// SQL-like: aggregation with GROUP BY / HAVING
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

// Relational API: Prisma-like nested queries
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

### Drizzle Performance Advantages

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

## Migrations

### Up/Down Migrations (Knex-style)

```typescript
// Explicit up/down migrations
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

### Zero-Downtime Migrations: Expand/Contract Pattern

The expand/contract pattern ensures no deployment step breaks the running application.

**Phase 1: Expand** (backward compatible)
```sql
-- Add new column (nullable, no breaking change)
ALTER TABLE users ADD COLUMN display_name VARCHAR(100);

-- Backfill data (in batches to avoid locking)
UPDATE users SET display_name = name WHERE display_name IS NULL LIMIT 1000;
```

**Phase 2: Migrate** (application reads from both, writes to both)
```typescript
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

### Dangerous Migration Operations

| Operation | Risk | Safe Alternative |
|-----------|------|------------------|
| `DROP COLUMN` | Breaks running code | Deploy code change first, then drop |
| `ALTER COLUMN SET NOT NULL` | Full table scan + lock | Add CHECK constraint first, then convert |
| `RENAME COLUMN` | Breaks running code | Add new column, dual-write, drop old |
| `CREATE INDEX` | Locks table for writes | `CREATE INDEX CONCURRENTLY` |
| `ALTER COLUMN TYPE` | Full table rewrite | Add new column, migrate, drop old |

### Data Migrations

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

### Migration Squashing

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

### Migration Checklist

Before writing the migration:
- [ ] Does this migration work with the CURRENT application code running?
- [ ] Can this migration be applied without downtime?
- [ ] If adding a column: is it nullable or does it have a default?
- [ ] If removing a column: is all application code already updated to not reference it?
- [ ] If renaming: use expand/contract (add new, dual-write, migrate, drop old)

During migration:
- [ ] Use `CREATE INDEX CONCURRENTLY` (not inside a transaction)
- [ ] Batch large data migrations (1000-10000 rows per batch with sleep)
- [ ] Set `lock_timeout` to avoid blocking queries indefinitely
- [ ] Test against a production-sized dataset for timing estimates

After migration:
- [ ] Run `ANALYZE` on affected tables to update statistics
- [ ] Verify query plans have not changed unexpectedly
- [ ] Monitor for lock contention and slow queries

---

## Connection Pooling

### Why Pooling Matters

Each PostgreSQL connection consumes ~10MB of memory (process fork). Without pooling:

```
20 serverless instances x 5 connections each = 100 connections
100 connections x 10MB = 1GB just for connection overhead
PostgreSQL default max_connections = 100 (hit the limit)
```

### Pool Sizing Formula

```
optimal_pool_size = (core_count * 2) + effective_spindle_count

Cloud SSD examples:
  2 vCPU  →  5 connections
  4 vCPU  →  9 connections
  8 vCPU  → 17 connections
  16 vCPU → 33 connections
```

**Counter-intuitive truth**: Smaller pools often outperform larger ones. A pool of 10 connections will often handle more throughput than a pool of 100 due to reduced context switching and lock contention.

### Pool Configuration

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

### PgBouncer vs Application-Level Pooling

| Feature | PgBouncer | Application Pool (pg Pool) |
|---------|-----------|---------------------------|
| Location | Separate process/container | In-process |
| Shared across instances | Yes | No (per-process) |
| Transaction pooling | Yes | No (session-level only) |
| Prepared statements | Limited (transaction mode) | Full support |
| Overhead | Extra network hop | None |
| Serverless-friendly | Yes (solves connection storm) | No (each instance has own pool) |

**Architecture decision:**

```
Single server app?
  → Application pool (pg Pool) is sufficient

Multiple app instances hitting same database?
  → Add PgBouncer in front of PostgreSQL
      → Mode: transaction (default for most apps)
      → max_client_conn: 1000+
      → default_pool_size: 20 (per database/user pair)

Serverless (Lambda, Vercel)?
  → PgBouncer is mandatory (or use Prisma Accelerate / Neon pooler)
      → Each cold start would otherwise create new connections
```

**Use both**: PgBouncer between your app instances and PostgreSQL, plus application-level pooling within each instance. PgBouncer handles the cross-instance connection management; the application pool handles local connection reuse.

---

## Related Reading

- **Prisma type generation** — the generated types use advanced TypeScript patterns (conditional types, mapped types) covered in [TypeScript Advanced — Advanced Type Patterns](../01-typescript-advanced/02-advanced-type-patterns.md#7-how-prisma-types-work-deep-dive)
- **Connection pooling** — pool exhaustion is a common cause of latency under load, explored further in [Performance — Clustering and Scaling](../08-performance-scaling/02-clustering-and-scaling.md) and [Performance — Profiling and Advanced Performance](../08-performance-scaling/03-profiling-and-advanced-performance.md)
- **Prisma middleware** (soft deletes, performance monitoring) — audit logging middleware connects to [Auth & Security — Advanced Security and Secrets](../05-auth-security/03-advanced-security-and-secrets.md) (structured audit logging)
- **Zero-downtime migrations** — the expand/contract pattern is the same strategy used for API versioning in [REST API Design — Pagination, Filtering, and Bulk Operations](../03-rest-api-design/02-pagination-filtering-and-bulk-operations.md) (backward compatibility strategies)
- **Raw queries** — parameterized queries are essential for SQL injection prevention covered in [Auth & Security — Session Management and Validation](../05-auth-security/02-session-management-and-validation.md#4-input-validation)
- For query optimization, transactions, and indexing, continue to [Queries, Transactions, and Optimization](02-queries-transactions-and-optimization.md)
- For resolving N+1 in GraphQL resolvers with DataLoader, see [GraphQL — Advanced GraphQL Patterns](../04-graphql/02-advanced-graphql-patterns.md#1-dataloader-and-the-n1-problem)
- For testing database code, see [Testing — Integration Testing and Mocking](../07-testing/02-integration-testing-and-mocking.md)
