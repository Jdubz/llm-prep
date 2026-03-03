# 03 – Migrations, Redis, and Advanced Storage

This file assumes you have read `01-database-drivers-and-orms.md` and `02-queries-transactions-and-patterns.md`. It covers database migrations, Redis with go-redis, connection pool tuning, observability, and testing strategies.

---

## 1. Database Migrations

Never use `AutoMigrate` in production. Use versioned, reversible migration files instead.

### goose

```bash
# Install
go install github.com/pressly/goose/v3/cmd/goose@latest

# Create a migration (generates timestamped .sql file)
goose -dir ./migrations create add_users_table sql

# Apply all pending migrations
goose -dir ./migrations postgres "postgres://user:pass@localhost/db" up

# Roll back one migration
goose -dir ./migrations postgres "postgres://user:pass@localhost/db" down

# Check current migration status
goose -dir ./migrations postgres "postgres://user:pass@localhost/db" status
```

```sql
-- migrations/20240101000000_create_users.sql
-- +goose Up
CREATE TABLE users (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE,
    active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- +goose Down
DROP TABLE users;
```

### golang-migrate

```bash
# Install
go install github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Create a migration (generates up + down files)
migrate create -ext sql -dir ./migrations -seq create_users

# Apply migrations
migrate -path ./migrations -database "postgres://..." up

# Roll back one step
migrate -path ./migrations -database "postgres://..." down 1

# Jump to specific version
migrate -path ./migrations -database "postgres://..." goto 3
```

```sql
-- migrations/000001_create_users.up.sql
CREATE TABLE users (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- migrations/000001_create_users.down.sql
DROP TABLE IF EXISTS users;
```

### Embedding Migrations

Embed migration files in the binary so migrations run automatically at startup:

```go
import (
    "embed"
    "github.com/pressly/goose/v3"
)

//go:embed migrations/*.sql
var migrationsFS embed.FS

func runMigrations(db *sql.DB) error {
    goose.SetBaseFS(migrationsFS)
    return goose.Up(db, "migrations")
}
```

---

## 2. Redis with go-redis

### Setup and Connection

```go
import "github.com/redis/go-redis/v9"

rdb := redis.NewClient(&redis.Options{
    Addr:         "localhost:6379",
    Password:     "",             // "" = no password
    DB:           0,              // default DB
    MaxRetries:   3,
    PoolSize:     10,             // connections in pool
    MinIdleConns: 5,
    DialTimeout:  5 * time.Second,
    ReadTimeout:  3 * time.Second,
    WriteTimeout: 3 * time.Second,
})
defer rdb.Close()

ctx := context.Background()
if err := rdb.Ping(ctx).Err(); err != nil {
    log.Fatal(err)
}
```

### Common Operations

```go
// String operations
err := rdb.Set(ctx, "key", "value", 10*time.Minute).Err()
val, err := rdb.Get(ctx, "key").Result()
if errors.Is(err, redis.Nil) {
    // key does not exist
}

// Set only if not exists (distributed lock / atomic check-and-set)
set, err := rdb.SetNX(ctx, "lock:resource", "owner", 30*time.Second).Result()

// Counters
count, err := rdb.Incr(ctx, "visits").Result()
err = rdb.IncrBy(ctx, "score", 10).Err()

// Expiration
err = rdb.Expire(ctx, "key", time.Hour).Err()
ttl, err := rdb.TTL(ctx, "key").Result()

// Delete
err = rdb.Del(ctx, "key1", "key2").Err()

// Check existence
exists, err := rdb.Exists(ctx, "key").Result()

// Hash operations
err = rdb.HSet(ctx, "user:1", "name", "Alice", "email", "alice@example.com").Err()
name, err := rdb.HGet(ctx, "user:1", "name").Result()
fields, err := rdb.HGetAll(ctx, "user:1").Result() // map[string]string

// List operations (queue)
err = rdb.LPush(ctx, "queue", "item1", "item2").Err() // push left
item, err := rdb.RPop(ctx, "queue").Result()           // pop right (FIFO)
item, err = rdb.BRPop(ctx, 5*time.Second, "queue").Result() // blocking pop

// Set operations
err = rdb.SAdd(ctx, "online_users", "user1", "user2").Err()
members, err := rdb.SMembers(ctx, "online_users").Result()
isMember, err := rdb.SIsMember(ctx, "online_users", "user1").Result()

// Sorted set (leaderboard)
err = rdb.ZAdd(ctx, "leaderboard",
    redis.Z{Score: 100, Member: "player1"},
    redis.Z{Score: 200, Member: "player2"},
).Err()
top10, err := rdb.ZRevRangeWithScores(ctx, "leaderboard", 0, 9).Result()
rank, err := rdb.ZRevRank(ctx, "leaderboard", "player1").Result()
```

### Pipelining

Pipelining batches multiple commands into a single round-trip:

```go
pipe := rdb.Pipeline()
incrCmd := pipe.Incr(ctx, "visits")
setCmd := pipe.Set(ctx, "last_seen", time.Now().Unix(), 24*time.Hour)
getCmd := pipe.Get(ctx, "user:1:name")

_, err := pipe.Exec(ctx)
if err != nil {
    return err
}

visits, err := incrCmd.Result()
name, err := getCmd.Result()

// TxPipeline: all commands in a MULTI/EXEC transaction
_, err = rdb.TxPipelined(ctx, func(pipe redis.Pipeliner) error {
    pipe.Set(ctx, "key1", "val1", 0)
    pipe.Set(ctx, "key2", "val2", 0)
    return nil
})
```

### Pub/Sub

Redis Pub/Sub provides fire-and-forget messaging between services or components. Unlike channels in Go (which are in-process), Redis Pub/Sub works across processes and machines. The trade-off is that messages are not persisted — if a subscriber is disconnected when a message is published, it misses that message. For durable messaging, use Redis Streams or an external message broker like Kafka. In Go, `pubsub.Channel()` returns a Go channel that you can range over, bridging Redis Pub/Sub into Go's concurrency model.

```go
// Publisher
err := rdb.Publish(ctx, "events:user", `{"event":"signup","id":42}`).Err()

// Subscriber
pubsub := rdb.Subscribe(ctx, "events:user", "events:order")
defer pubsub.Close()

ch := pubsub.Channel()
for msg := range ch {
    fmt.Printf("Channel: %s, Payload: %s\n", msg.Channel, msg.Payload)
}
```

### Lua Scripting (Atomic Operations)

Lua scripts run atomically in Redis — no other command can interleave during execution:

```go
// Rate limiter using Lua (atomic check-and-increment)
rateLimiter := redis.NewScript(`
    local key = KEYS[1]
    local limit = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])

    local current = tonumber(redis.call('GET', key) or '0')
    if current >= limit then
        return 0
    end

    redis.call('INCR', key)
    redis.call('EXPIRE', key, window)
    return 1
`)

allowed, err := rateLimiter.Run(ctx, rdb,
    []string{"rate:user:42"},
    100,  // limit: 100 requests
    60,   // window: 60 seconds
).Int()
if allowed == 0 {
    // rate limit exceeded
}
```

---

## 3. Caching Patterns

### Cache-Aside (Lazy Loading)

The most common caching pattern: check cache first, fall back to database on miss:

```go
type UserService struct {
    db    store.UserStore
    cache *redis.Client
}

func (s *UserService) GetUser(ctx context.Context, id int64) (*User, error) {
    cacheKey := fmt.Sprintf("user:%d", id)

    // 1. Try cache
    cached, err := s.cache.Get(ctx, cacheKey).Bytes()
    if err == nil {
        var user User
        if err := json.Unmarshal(cached, &user); err == nil {
            return &user, nil
        }
    }

    // 2. Cache miss — fetch from database
    user, err := s.db.GetUser(ctx, id)
    if err != nil {
        return nil, err
    }

    // 3. Populate cache (best-effort, don't fail the request on cache error)
    if data, err := json.Marshal(user); err == nil {
        s.cache.Set(ctx, cacheKey, data, 5*time.Minute)
    }

    return user, nil
}

// Invalidate on write
func (s *UserService) UpdateUser(ctx context.Context, id int64, params UpdateParams) (*User, error) {
    user, err := s.db.UpdateUser(ctx, id, params)
    if err != nil {
        return nil, err
    }

    // Delete from cache — next read will repopulate
    s.cache.Del(ctx, fmt.Sprintf("user:%d", id))
    return user, nil
}
```

### Write-Through Cache

Write to cache and database simultaneously, keeping them in sync:

```go
func (s *UserService) CreateUser(ctx context.Context, params CreateUserParams) (*User, error) {
    user, err := s.db.CreateUser(ctx, params)
    if err != nil {
        return nil, err
    }

    // Write to cache immediately
    if data, err := json.Marshal(user); err == nil {
        s.cache.Set(ctx, fmt.Sprintf("user:%d", user.ID), data, 5*time.Minute)
    }

    return user, nil
}
```

---

## 4. Connection Pool Tuning

### Key Pool Parameters

| Parameter | pgxpool | database/sql | Description |
|-----------|---------|--------------|-------------|
| Max connections | `MaxConns` | `SetMaxOpenConns` | Hard cap on open connections |
| Min idle | `MinConns` | `SetMaxIdleConns` | Keep N connections warm |
| Max lifetime | `MaxConnLifetime` | `SetConnMaxLifetime` | Recycle connections (prevents stale connections) |
| Max idle time | `MaxConnIdleTime` | `SetConnMaxIdleTime` | Close idle connections after N time |
| Health check | `HealthCheckPeriod` | — | Periodically verify connections |

### Pool Sizing Guidelines

```
MaxConns formula:
  MaxConns = (core_count * 2) + effective_spindle_count

Practical ranges:
  - Light web API:        MaxConns = 5–10
  - Typical web API:      MaxConns = 10–25
  - High-traffic service: MaxConns = 25–100
  - Background workers:   MaxConns = 2–5 per worker
```

Symptoms of misconfigured pools:
- Too small: requests queue, latency spikes, "connection pool exhausted" errors
- Too large: PostgreSQL process limit hit, excessive RAM on DB server, lock contention

### Monitoring Pool Stats

```go
// Log pool stats periodically
go func() {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for range ticker.C {
        stats := pool.Stat()
        slog.Info("pool stats",
            "total_conns", stats.TotalConns(),
            "idle_conns", stats.IdleConns(),
            "acquired_conns", stats.AcquiredConns(),
            "max_conns", stats.MaxConns(),
        )
    }
}()
```

---

## 5. Database Observability

### Query Tracer with pgx

Implement pgx's `QueryTracer` interface to log slow queries and capture metrics:

```go
type QueryTracer struct {
    logger *slog.Logger
    slow   time.Duration
}

func (t *QueryTracer) TraceQueryStart(ctx context.Context, conn *pgx.Conn, data pgx.TraceQueryStartData) context.Context {
    return context.WithValue(ctx, queryStartKey{}, time.Now())
}

func (t *QueryTracer) TraceQueryEnd(ctx context.Context, conn *pgx.Conn, data pgx.TraceQueryEndData) {
    start, ok := ctx.Value(queryStartKey{}).(time.Time)
    if !ok {
        return
    }

    duration := time.Since(start)

    attrs := []any{
        "sql", data.SQL,
        "duration_ms", duration.Milliseconds(),
    }
    if data.Err != nil {
        attrs = append(attrs, "error", data.Err)
    }

    if duration > t.slow {
        t.logger.Warn("slow query", attrs...)
    } else {
        t.logger.Debug("query", attrs...)
    }
}

// Register the tracer in pgxpool config
config.ConnConfig.Tracer = &QueryTracer{
    logger: slog.Default(),
    slow:   100 * time.Millisecond,
}
```

---

## 6. Testing Strategies

### testcontainers-go: Real Database in Tests

`testcontainers-go` spins up a real PostgreSQL container for integration tests. This catches SQL bugs that mocks cannot.

```go
import (
    "github.com/testcontainers/testcontainers-go"
    "github.com/testcontainers/testcontainers-go/modules/postgres"
)

func setupTestDB(t *testing.T) *pgxpool.Pool {
    t.Helper()
    ctx := context.Background()

    pgContainer, err := postgres.RunContainer(ctx,
        testcontainers.WithImage("postgres:16-alpine"),
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(
            wait.ForLog("database system is ready to accept connections").
                WithOccurrence(2).
                WithStartupTimeout(30*time.Second),
        ),
    )
    if err != nil {
        t.Fatal(err)
    }

    t.Cleanup(func() { pgContainer.Terminate(ctx) })

    connStr, err := pgContainer.ConnectionString(ctx, "sslmode=disable")
    if err != nil {
        t.Fatal(err)
    }

    pool, err := pgxpool.New(ctx, connStr)
    if err != nil {
        t.Fatal(err)
    }

    // Run migrations
    if err := runMigrations(pool); err != nil {
        t.Fatal(err)
    }

    return pool
}

func TestUserStore(t *testing.T) {
    pool := setupTestDB(t)
    store := postgres.NewUserStore(pool)

    t.Run("creates user", func(t *testing.T) {
        user, err := store.CreateUser(context.Background(), store.CreateUserParams{
            Name:  "Alice",
            Email: "alice@example.com",
        })
        if err != nil {
            t.Fatal(err)
        }
        if user.Name != "Alice" {
            t.Errorf("got name %q, want %q", user.Name, "Alice")
        }
    })
}
```

### Redis Test Container

```go
func setupRedis(t *testing.T) *redis.Client {
    t.Helper()
    ctx := context.Background()

    redisContainer, err := testcontainers.GenericContainer(ctx,
        testcontainers.GenericContainerRequest{
            ContainerRequest: testcontainers.ContainerRequest{
                Image:        "redis:7-alpine",
                ExposedPorts: []string{"6379/tcp"},
                WaitingFor:   wait.ForLog("Ready to accept connections"),
            },
            Started: true,
        },
    )
    if err != nil {
        t.Fatal(err)
    }
    t.Cleanup(func() { redisContainer.Terminate(ctx) })

    host, _ := redisContainer.Host(ctx)
    port, _ := redisContainer.MappedPort(ctx, "6379")

    return redis.NewClient(&redis.Options{
        Addr: fmt.Sprintf("%s:%s", host, port.Port()),
    })
}
```

### Embedded SQLite for Unit Tests

For fast unit tests that do not need PostgreSQL-specific features, use an in-memory SQLite database:

```go
import (
    "database/sql"
    _ "modernc.org/sqlite" // pure-Go SQLite, no cgo
)

func setupSQLiteDB(t *testing.T) *sql.DB {
    t.Helper()

    db, err := sql.Open("sqlite", ":memory:")
    if err != nil {
        t.Fatal(err)
    }
    t.Cleanup(func() { db.Close() })

    _, err = db.Exec(`CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL
    )`)
    if err != nil {
        t.Fatal(err)
    }

    return db
}
```

Use SQLite tests for: unit tests of SQL logic that is ANSI-compatible.
Use testcontainers for: integration tests, tests involving PostgreSQL-specific syntax (JSONB, arrays, CTEs, COPY).

---

## 7. Data Access Pattern Comparison

| Pattern | Type Safety | SQL Flexibility | Learning Curve | Best Use Case |
|---------|-------------|-----------------|----------------|---------------|
| `database/sql` + raw SQL | Runtime | Full | Low | Simple projects, learning |
| `pgx` + raw SQL | Runtime | Full | Low-Medium | High-performance PG |
| `sqlx` | Runtime | Full | Low | Struct scanning without ORM |
| `sqlc` | Compile-time | Full | Medium | SQL-first teams, type safety |
| `GORM` | Runtime | Limited | Low | Rapid prototyping |
| `Ent` | Compile-time | Medium | High | Complex graph data models |
| `squirrel` + any | Runtime | High | Low | Dynamic query building |
| sqlc + squirrel | Compile-time + Runtime | Full | Medium | Mixed: static + dynamic queries |

---

## 8. Interview Questions

**Q: What is the difference between `pgx` and `lib/pq`?**
`pgx` is a native PostgreSQL driver that uses the binary protocol (faster), supports PostgreSQL-specific types (arrays, JSONB, UUID, ranges) natively, and has a built-in connection pool (`pgxpool`). `lib/pq` uses the text protocol and is now in maintenance mode.

**Q: Why use keyset pagination over offset pagination?**
Offset pagination (`LIMIT n OFFSET m`) requires the database to scan and discard `m` rows — it gets slower as `m` grows. Keyset pagination uses a `WHERE (sort_col, id) < (cursor_val, cursor_id)` clause that the index can satisfy directly, giving O(1) cost regardless of page depth.

**Q: What is the repository pattern and why use it?**
The repository pattern defines a storage interface that business logic depends on. The concrete implementation (PostgreSQL, Redis, mock) satisfies that interface. Benefits: testability (swap in mocks), flexibility (change storage without changing business logic), clear separation of concerns.

**Q: Explain the `defer tx.Rollback()` pattern.**
After `tx.Begin`, defer `tx.Rollback()`. If the function returns an error, Rollback fires. If `tx.Commit()` is called successfully before the function returns, a subsequent Rollback is a no-op (pgx/database/sql both handle this). This ensures no transaction is ever left open, even if the code path is complex.

**Q: When would you choose sqlc over GORM?**
Choose `sqlc` when: you want compile-time type safety, you need full SQL control, your team is comfortable writing SQL. Choose `GORM` when: you want rapid prototyping, you don't need PostgreSQL-specific features, you prefer an ActiveRecord-style API and are willing to trade SQL control for convenience.

**Q: What is the cache-aside pattern and when can it fail?**
Cache-aside: read from cache; on miss, read from DB and write to cache. Failure modes: (1) **thundering herd** — many concurrent misses all hit the DB simultaneously (fix: use a single-flight mutex); (2) **stale data** — the DB is updated but the cache still has the old value (fix: delete cache on write, or use short TTLs); (3) **cold start** — after a cache restart, all requests hit the DB (fix: warm the cache or use write-through).

**Q: How do you size a database connection pool?**
Start with `MaxConns = (core_count * 2) + spindle_count`. Monitor pool stats (acquired vs idle vs total). Symptoms of too-small pools: queuing/timeout errors, high average wait time. Symptoms of too-large pools: PostgreSQL RAM exhaustion, lock contention. Adjust based on measured latency and throughput.

**Q: What are pgx batch operations and when should you use them?**
`pgx.Batch` queues multiple SQL statements and sends them in a single round-trip. Use batching when inserting/updating many rows where the individual statements are independent and you need higher throughput than individual `Exec` calls but cannot use `COPY` (e.g., upserts with conflict handling).

**Q: How do you handle database migrations in a production Go service?**
Use versioned SQL files (goose or golang-migrate). Embed the migration files in the binary (`//go:embed migrations/*.sql`). Run migrations on startup before accepting traffic. Never use `AutoMigrate` in production — it cannot safely handle destructive changes like column renames or drops.

**Q: What is the difference between `Pipelining` and `TxPipelining` in go-redis?**
Regular `Pipeline` sends commands in a batch but they execute as separate commands — a failure in one does not roll back others. `TxPipeline` wraps the batch in Redis `MULTI`/`EXEC`, so all commands succeed or all fail atomically. Use `TxPipeline` when the operations must be atomic.

**Q: When would you use Lua scripting in Redis?**
When you need an atomic read-modify-write operation that cannot be expressed as a single Redis command. Example: rate limiting (read counter, check limit, increment, set expiry — all atomically). Lua scripts run atomically in Redis — no other command executes while the script runs.

**Q: What are savepoints in PostgreSQL and when would you use them?**
Savepoints mark a point within a transaction to which you can roll back without aborting the entire transaction. Use them in nested operations where a sub-operation might fail non-fatally and you want to retry or fall back without losing the parent transaction's work.

---

## Related Reading

- **HTTP service integration** — [Module 04: Advanced HTTP Patterns](../04-http-services/03-advanced-http-patterns.md) shows how the database and caching layers from this module integrate into HTTP services with graceful shutdown and connection draining
- **Integration testing with testcontainers** — [Module 06: Integration and HTTP Testing](../06-testing/02-integration-and-http-testing.md), section 2 (testcontainers-go) covers how to test against real PostgreSQL and Redis containers for the patterns from this module
- **singleflight for cache stampede prevention** — [Module 02: Advanced Concurrency Patterns](../02-concurrency/03-advanced-concurrency-patterns.md), section 5 covers the `singleflight` pattern used in the caching strategies from section 2
- **Embedding migrations** — [Module 07: Project Structure and Configuration](../07-production/01-project-structure-and-configuration.md), section 6 (Embedding Assets) shows how to use `//go:embed` to bundle the migration files from section 1 into the binary
- **Connection pool observability** — [Module 07: Observability and Health](../07-production/02-observability-and-health.md), section 2 (Prometheus Metrics) covers exposing the pool metrics described in section 5 as Prometheus gauges

---

## Practice Suggestions

These exercises reinforce the data storage concepts from this module (Database Drivers and ORMs through Migrations, Redis, and Advanced Storage):

1. **sqlc CRUD with migrations** — Set up a PostgreSQL database with goose migrations, write SQL queries for a CRUD resource, and generate type-safe Go code with sqlc. Practice the full cycle: write a migration, write queries in `.sql` files, run `sqlc generate`, and use the generated code in a handler.

2. **Repository pattern with testcontainers** — Define a repository interface for a domain entity, implement it with pgx, and write integration tests using testcontainers-go. Verify that your tests can create, read, update, and delete records against a real PostgreSQL instance.

3. **Keyset pagination** — Implement cursor-based pagination for a table with at least 1000 rows. Write tests that paginate through the entire dataset and verify no rows are skipped or duplicated. Compare performance against offset pagination using benchmarks.

4. **Redis caching layer** — Build a cache-aside layer using go-redis that sits in front of a PostgreSQL repository. Implement cache invalidation on writes. Write a test that verifies the cache is populated on first read, served from cache on second read, and invalidated on update.

5. **Transaction with savepoints** — Write a transaction that performs multiple operations where one sub-operation might fail (e.g., inserting into a table with a unique constraint). Use savepoints to handle the failure without aborting the entire transaction. Test both the success and partial-failure paths.

6. **Connection pool tuning** — Set up a pgxpool with configurable `MaxConns`, `MinConns`, and health check periods. Write a load test that measures query latency under different pool sizes. Export pool stats (acquired, idle, total) and observe how pool sizing affects performance.
