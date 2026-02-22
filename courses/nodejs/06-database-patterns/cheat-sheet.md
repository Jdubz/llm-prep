# Module 06 Cheat Sheet: Database Patterns

## ORM Comparison Table

| | Prisma | Drizzle | TypeORM | Knex |
|---|---|---|---|---|
| **Type Safety** | Generated (build-time) | Inferred (compile-time) | Decorators (runtime) | Manual |
| **Query Style** | Custom DSL | SQL-like | Repository + QueryBuilder | SQL-like |
| **Raw SQL** | `$queryRaw` (tagged) | `sql` (tagged) | `.query()` | `.raw()` |
| **Migrations** | Auto-generated | Auto-generated | Auto or manual | Manual |
| **Performance** | Good (Rust engine) | Excellent (thin layer) | Moderate | Excellent |
| **Bundle Size** | ~15MB (engine binary) | ~50KB | ~2MB | ~500KB |
| **Edge/Serverless** | Needs Accelerate or adapter | Native support | Poor | Driver-dependent |
| **Schema Definition** | `.prisma` file (DSL) | TypeScript | Decorators or entity files | N/A (manual SQL) |
| **Relation Loading** | `include` / `select` | `with` (relational API) | `relations` / `leftJoinAndSelect` | Manual JOINs |
| **Best For** | DX-focused teams | SQL-savvy teams | Legacy projects | Pure query building |

---

## Prisma Schema Template

```prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["fullTextSearch"]
  binaryTargets   = ["native", "linux-musl-openssl-3.0.x"]
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")
  directUrl = env("DIRECT_DATABASE_URL")  // For migrations (bypasses PgBouncer)
}

model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  role      Role     @default(USER)
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")
  deletedAt DateTime? @map("deleted_at")

  posts    Post[]
  sessions Session[]

  @@map("users")
  @@index([email])
  @@index([createdAt])
}

model Post {
  id          String    @id @default(cuid())
  title       String    @db.VarChar(255)
  content     String?   @db.Text
  published   Boolean   @default(false)
  authorId    String    @map("author_id")
  publishedAt DateTime? @map("published_at")
  createdAt   DateTime  @default(now()) @map("created_at")

  author User @relation(fields: [authorId], references: [id], onDelete: Cascade)

  @@map("posts")
  @@index([authorId])
  @@index([published, publishedAt(sort: Desc)])
}

enum Role {
  USER
  ADMIN
  MODERATOR
}
```

---

## Drizzle Schema Template

```typescript
import { pgTable, varchar, text, boolean, timestamp, uuid, pgEnum, index, uniqueIndex } from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const roleEnum = pgEnum('role', ['user', 'admin', 'moderator']);

export const users = pgTable('users', {
  id: uuid('id').defaultRandom().primaryKey(),
  email: varchar('email', { length: 255 }).notNull().unique(),
  name: varchar('name', { length: 100 }),
  role: roleEnum('role').default('user').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
}, (t) => ({
  emailIdx: uniqueIndex('users_email_idx').on(t.email),
}));

export const posts = pgTable('posts', {
  id: uuid('id').defaultRandom().primaryKey(),
  title: varchar('title', { length: 255 }).notNull(),
  content: text('content'),
  published: boolean('published').default(false).notNull(),
  authorId: uuid('author_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  publishedAt: timestamp('published_at'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => ({
  authorIdx: index('posts_author_idx').on(t.authorId),
  publishedIdx: index('posts_published_idx').on(t.published, t.publishedAt),
}));

export const usersRelations = relations(users, ({ many }) => ({
  posts: many(posts),
}));

export const postsRelations = relations(posts, ({ one }) => ({
  author: one(users, { fields: [posts.authorId], references: [users.id] }),
}));
```

---

## Migration Checklist

### Before Writing the Migration

- [ ] Does this migration work with the CURRENT application code running?
- [ ] Can this migration be applied without downtime?
- [ ] If adding a column: is it nullable or does it have a default?
- [ ] If removing a column: is all application code already updated to not reference it?
- [ ] If renaming: use expand/contract (add new, dual-write, migrate, drop old)

### During Migration

- [ ] Use `CREATE INDEX CONCURRENTLY` (not inside a transaction)
- [ ] Batch large data migrations (1000-10000 rows per batch with sleep)
- [ ] Set `lock_timeout` to avoid blocking queries indefinitely
- [ ] Test against a production-sized dataset for timing estimates

### After Migration

- [ ] Run `ANALYZE` on affected tables to update statistics
- [ ] Verify query plans have not changed unexpectedly
- [ ] Monitor for lock contention and slow queries
- [ ] Mark migration as applied in all environments before squashing

### Dangerous Operations (Require Extra Care)

| Operation | Risk | Safe Alternative |
|-----------|------|------------------|
| `DROP COLUMN` | Breaks running code | Deploy code change first, then drop |
| `ALTER COLUMN SET NOT NULL` | Full table scan + lock | Add CHECK constraint first, then convert |
| `RENAME COLUMN` | Breaks running code | Add new column, dual-write, drop old |
| `CREATE INDEX` | Locks table for writes | `CREATE INDEX CONCURRENTLY` |
| `ALTER COLUMN TYPE` | Full table rewrite | Add new column, migrate, drop old |

---

## Transaction Isolation Levels

| Level | Dirty Read | Non-Repeatable Read | Phantom Read | Use Case |
|-------|-----------|-------------------|--------------|----------|
| **Read Uncommitted** | Yes | Yes | Yes | Almost never in PostgreSQL (treated as Read Committed) |
| **Read Committed** | No | Yes | Yes | Default. Most CRUD operations. |
| **Repeatable Read** | No | No | No* | Consistent reports, financial summaries |
| **Serializable** | No | No | No | Inventory, double-spend prevention, seat booking |

*PostgreSQL Repeatable Read uses snapshot isolation, which also prevents phantom reads.

### Quick Decision Guide

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

---

## Indexing Decision Guide

### When to Add an Index

```
Query appears in slow query log (> 100ms)?
  └── Check EXPLAIN ANALYZE
        ├── Seq Scan on large table → Add index on WHERE columns
        ├── Sort with high cost → Add index on ORDER BY columns
        └── Nested Loop with many rows → Consider composite index on JOIN columns
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

### Composite Index Column Order

```
Rule: Equality columns FIRST, then range/sort columns LAST

Good:  (tenant_id, status, created_at DESC)
       Supports: WHERE tenant_id = ? AND status = ? ORDER BY created_at DESC

Bad:   (created_at DESC, tenant_id, status)
       Only efficiently supports: ORDER BY created_at DESC
```

### Partial Index (Save Space and Speed)

```sql
-- Only index the rows you actually query
CREATE INDEX idx_posts_published ON posts (published_at DESC)
  WHERE published = true;
-- 95% smaller if only 5% of posts are published
```

### Covering Index (Avoid Table Lookup)

```sql
-- Include columns that the query SELECTs
CREATE INDEX idx_posts_list ON posts (author_id, published)
  INCLUDE (title, created_at);
-- Index-only scan: no need to visit the heap
```

---

## Connection Pool Sizing

### Formula

```
pool_size = (cpu_cores * 2) + spindle_count

Cloud SSD examples:
  2 vCPU  →  5 connections
  4 vCPU  →  9 connections
  8 vCPU  → 17 connections
  16 vCPU → 33 connections
```

### Configuration Template

```typescript
const pool = new Pool({
  max: 20,                        // Max connections
  min: 5,                         // Keep-alive connections
  idleTimeoutMillis: 30000,       // Close idle after 30s
  connectionTimeoutMillis: 5000,  // Fail fast if pool exhausted
  maxUses: 7500,                  // Recycle connections (prevent memory leaks)
});
```

### Architecture Decision

```
Single server app?
  └── Application pool (pg Pool) is sufficient

Multiple app instances hitting same database?
  └── Add PgBouncer in front of PostgreSQL
        └── Mode: transaction (default for most apps)
        └── max_client_conn: 1000+
        └── default_pool_size: 20 (per database/user pair)

Serverless (Lambda, Vercel)?
  └── PgBouncer is mandatory (or use Prisma Accelerate / Neon pooler)
        └── Each cold start would otherwise create new connections
```

---

## Quick Reference: Common Prisma Operations

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
