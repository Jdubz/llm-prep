# Module 05 Cheat Sheet: Data & Storage

## ORM / Query Builder Comparison

| Tool | Approach | Type Safety | Dynamic Queries | Associations | Best For |
|---|---|---|---|---|---|
| **sqlc** | SQL-first codegen | Compile-time | Weak | Manual JOINs | Static queries, SQL teams |
| **GORM** | Full ORM | Runtime | Strong (scopes) | Built-in | Rapid prototyping, complex models |
| **sqlx** | database/sql ext | Runtime | Manual | Manual JOINs | Minimal abstraction |
| **Ent** | Schema-first codegen | Compile-time | Strong | Graph-based | Complex data models |
| **squirrel** | Query builder | Runtime | Strong | N/A | Dynamic WHERE clauses |

## pgx Connection Pool Template

```go
config, _ := pgxpool.ParseConfig(databaseURL)
config.MaxConns = 25
config.MinConns = 5
config.MaxConnLifetime = 1 * time.Hour
config.MaxConnIdleTime = 30 * time.Minute
config.HealthCheckPeriod = 1 * time.Minute

pool, err := pgxpool.NewWithConfig(ctx, config)
if err != nil { return err }
defer pool.Close()
```

## sqlc Query Annotation Reference

```sql
-- name: FnName :one       -- Returns single row: (T, error)
-- name: FnName :many      -- Returns slice: ([]T, error)
-- name: FnName :exec       -- No return rows: error
-- name: FnName :execrows   -- Returns affected rows: (int64, error)
-- name: FnName :execresult -- Returns sql.Result
-- name: FnName :copyfrom   -- Bulk insert via COPY
-- name: FnName :batchone   -- Batch, returns one per item
-- name: FnName :batchmany  -- Batch, returns many per item
-- name: FnName :batchexec  -- Batch, no return

-- Nullable parameter:
sqlc.narg('param_name')

-- Named arg (always required):
sqlc.arg('param_name')
```

## sqlc.yaml Minimal Config

```yaml
version: "2"
sql:
  - engine: "postgresql"
    queries: "queries/"
    schema: "migrations/"
    gen:
      go:
        package: "db"
        out: "internal/db"
        sql_package: "pgx/v5"
        emit_json_tags: true
        emit_empty_slices: true
```

## Migration Commands Reference

### goose

```bash
goose -dir migrations create NAME sql        # Create migration
goose -dir migrations postgres DSN up        # Run all pending
goose -dir migrations postgres DSN down      # Rollback last
goose -dir migrations postgres DSN status    # Show status
goose -dir migrations postgres DSN redo      # Rollback + re-apply last
```

### golang-migrate

```bash
migrate create -ext sql -dir migrations -seq NAME    # Create pair
migrate -path migrations -database DSN up            # Run all
migrate -path migrations -database DSN down 1        # Rollback 1
migrate -path migrations -database DSN version       # Show version
migrate -path migrations -database DSN force V       # Force version
```

## Repository Interface Template

```go
type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*User, error)
    GetByEmail(ctx context.Context, email string) (*User, error)
    Create(ctx context.Context, user *User) error
    Update(ctx context.Context, user *User) error
    Delete(ctx context.Context, id int64) error
    List(ctx context.Context, opts ListOptions) ([]User, error)
}

type ListOptions struct {
    Limit  int
    Cursor int64
    Search string
}
```

## Redis Client Template

```go
rdb := redis.NewClient(&redis.Options{
    Addr:         "localhost:6379",
    Password:     "",
    DB:           0,
    PoolSize:     20,
    MinIdleConns: 5,
    DialTimeout:  5 * time.Second,
    ReadTimeout:  3 * time.Second,
    WriteTimeout: 3 * time.Second,
})

// Verify
if err := rdb.Ping(ctx).Err(); err != nil {
    log.Fatal(err)
}
defer rdb.Close()
```

## Redis Common Operations

```go
// String: Set/Get with TTL
rdb.Set(ctx, key, value, 15*time.Minute)
val, err := rdb.Get(ctx, key).Result()
if errors.Is(err, redis.Nil) { /* miss */ }

// Hash
rdb.HSet(ctx, "user:1", "name", "Alice", "email", "a@b.com")
rdb.HGet(ctx, "user:1", "name")
rdb.HGetAll(ctx, "user:1")

// Pipeline (batch commands)
pipe := rdb.Pipeline()
pipe.Incr(ctx, "counter")
pipe.Get(ctx, "config")
pipe.Exec(ctx)

// Pub/Sub
rdb.Publish(ctx, "channel", "message")
sub := rdb.Subscribe(ctx, "channel")
ch := sub.Channel()
for msg := range ch { /* process */ }
```

## Transaction Helper Template

```go
func WithTx(ctx context.Context, pool *pgxpool.Pool, fn func(pgx.Tx) error) error {
    tx, err := pool.Begin(ctx)
    if err != nil {
        return fmt.Errorf("begin: %w", err)
    }
    defer tx.Rollback(ctx) // No-op after commit

    if err := fn(tx); err != nil {
        return err
    }

    return tx.Commit(ctx)
}

// Usage:
err := WithTx(ctx, pool, func(tx pgx.Tx) error {
    _, err := tx.Exec(ctx, "UPDATE ...", args...)
    if err != nil { return err }
    _, err = tx.Exec(ctx, "INSERT ...", args...)
    return err
})
```

## Keyset Pagination Template

```sql
-- First page:
SELECT * FROM items ORDER BY created_at DESC, id DESC LIMIT $1;

-- Next pages:
SELECT * FROM items
WHERE (created_at, id) < ($1, $2)
ORDER BY created_at DESC, id DESC
LIMIT $3;
```

Fetch `limit + 1` rows. If you get more than `limit`, there's a next page. Use the last row as the cursor.

## Pool Sizing Guide

| Instance Size | MaxConns | MinConns |
|---|---|---|
| Small (2 CPU) | 10-15 | 2-3 |
| Medium (4 CPU) | 20-30 | 5 |
| Large (8+ CPU) | 40-60 | 10 |

Formula: `MaxConns = (cores * 2) + spindles` divided across instances.

## Key Gotchas

- Always `defer rows.Close()` and check `rows.Err()` after iteration
- Always use `context.Context` for database operations (cancellation/timeout)
- Never use string concatenation for SQL parameters (SQL injection)
- `pgx.ErrNoRows` is the "not found" error, not `nil` result
- GORM's `First()` returns `ErrRecordNotFound`; `Find()` returns empty slice
- Redis `Get` returns `redis.Nil` on cache miss, not a Go `nil`
- Close Redis connections with `defer rdb.Close()`
- Set `MaxConnLifetime` shorter than PG's `idle_in_transaction_session_timeout`
