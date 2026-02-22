# Module 05: Data & Storage

## Overview

Go's database ecosystem is philosophically different from TypeScript's. Where the JS world converges on ORMs like Prisma or Drizzle, Go's community splits across multiple approaches — raw SQL with `database/sql`, code-generated type-safe SQL with `sqlc`, full ORMs with GORM, and everything in between. Each has clear trade-offs, and knowing them is an interview differentiator.

This module covers PostgreSQL access, ORMs and query builders, migrations, Redis, the repository pattern, transactions, and advanced query patterns.

---

## Table of Contents

1. [database/sql with PostgreSQL](#databasesql-with-postgresql)
2. [ORMs and Query Builders](#orms-and-query-builders)
3. [Migrations](#migrations)
4. [Redis Integration](#redis-integration)
5. [Repository Pattern in Go](#repository-pattern-in-go)
6. [Transactions](#transactions)
7. [Query Patterns](#query-patterns)
8. [Interview Questions](#interview-questions)

---

## database/sql with PostgreSQL

### Why pgx Over lib/pq

`lib/pq` is in maintenance mode. `pgx` is the actively developed PostgreSQL driver with significant advantages:

| Feature | lib/pq | pgx |
|---|---|---|
| Active development | Maintenance only | Active |
| PostgreSQL types | Basic | Full (arrays, hstore, inet, JSON, etc.) |
| COPY support | No | Yes |
| LISTEN/NOTIFY | Fragile | First-class |
| Batch queries | No | Yes |
| Connection pool | Via database/sql | Built-in pgxpool (better) |
| Performance | Good | Better (native protocol) |
| database/sql compat | Yes | Yes (via pgx/stdlib) |

### Connection Pool Configuration

```go
import (
    "context"
    "github.com/jackc/pgx/v5/pgxpool"
)

func newPool(ctx context.Context, databaseURL string) (*pgxpool.Pool, error) {
    config, err := pgxpool.ParseConfig(databaseURL)
    if err != nil {
        return nil, fmt.Errorf("parsing database URL: %w", err)
    }

    // Pool configuration
    config.MaxConns = 25                       // Max open connections
    config.MinConns = 5                        // Keep at least 5 idle connections
    config.MaxConnLifetime = 1 * time.Hour     // Recycle connections after 1 hour
    config.MaxConnIdleTime = 30 * time.Minute  // Close idle connections after 30 min
    config.HealthCheckPeriod = 1 * time.Minute // Background health check interval

    // Connection-level settings
    config.ConnConfig.ConnectTimeout = 5 * time.Second

    pool, err := pgxpool.NewWithConfig(ctx, config)
    if err != nil {
        return nil, fmt.Errorf("creating pool: %w", err)
    }

    // Verify connectivity
    if err := pool.Ping(ctx); err != nil {
        return nil, fmt.Errorf("pinging database: %w", err)
    }

    return pool, nil
}
```

### Basic CRUD with pgx

```go
// Insert with RETURNING
func (r *userRepo) Create(ctx context.Context, user *User) error {
    query := `
        INSERT INTO users (email, name, created_at)
        VALUES ($1, $2, NOW())
        RETURNING id, created_at`

    return r.pool.QueryRow(ctx, query, user.Email, user.Name).
        Scan(&user.ID, &user.CreatedAt)
}

// Query single row
func (r *userRepo) GetByID(ctx context.Context, id int64) (*User, error) {
    query := `SELECT id, email, name, created_at FROM users WHERE id = $1`

    var u User
    err := r.pool.QueryRow(ctx, query, id).
        Scan(&u.ID, &u.Email, &u.Name, &u.CreatedAt)

    if errors.Is(err, pgx.ErrNoRows) {
        return nil, ErrNotFound
    }
    if err != nil {
        return nil, fmt.Errorf("querying user %d: %w", id, err)
    }

    return &u, nil
}

// Query multiple rows
func (r *userRepo) List(ctx context.Context, limit, offset int) ([]User, error) {
    query := `
        SELECT id, email, name, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT $1 OFFSET $2`

    rows, err := r.pool.Query(ctx, query, limit, offset)
    if err != nil {
        return nil, fmt.Errorf("querying users: %w", err)
    }
    defer rows.Close()

    var users []User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Email, &u.Name, &u.CreatedAt); err != nil {
            return nil, fmt.Errorf("scanning user: %w", err)
        }
        users = append(users, u)
    }

    // Check for errors from iteration
    if err := rows.Err(); err != nil {
        return nil, fmt.Errorf("iterating users: %w", err)
    }

    return users, nil
}
```

**Key difference from TypeScript**: You must call `rows.Close()` (use `defer`) and check `rows.Err()` after iteration. Failing to close rows leaks database connections.

### Prepared Statements

```go
// pgx caches prepared statements automatically per connection.
// You don't need to manually prepare statements like in database/sql.
// The first time a query runs, pgx prepares it. Subsequent calls reuse the plan.

// If you want explicit control:
func (r *userRepo) setupStatements(ctx context.Context) error {
    conn, err := r.pool.Acquire(ctx)
    if err != nil {
        return err
    }
    defer conn.Release()

    // Explicit preparation
    _, err = conn.Conn().Prepare(ctx, "get_user",
        "SELECT id, email, name FROM users WHERE id = $1")
    return err
}

// Use prepared statement by name
func (r *userRepo) GetByIDPrepared(ctx context.Context, id int64) (*User, error) {
    var u User
    err := r.pool.QueryRow(ctx, "get_user", id).
        Scan(&u.ID, &u.Email, &u.Name)
    return &u, err
}
```

### Batch Operations

```go
func (r *userRepo) CreateBatch(ctx context.Context, users []User) error {
    batch := &pgx.Batch{}

    for _, u := range users {
        batch.Queue(
            "INSERT INTO users (email, name) VALUES ($1, $2) RETURNING id",
            u.Email, u.Name,
        )
    }

    br := r.pool.SendBatch(ctx, batch)
    defer br.Close()

    for i := range users {
        if err := br.QueryRow().Scan(&users[i].ID); err != nil {
            return fmt.Errorf("batch insert user %d: %w", i, err)
        }
    }

    return nil
}
```

### LISTEN/NOTIFY

PostgreSQL's built-in pub/sub — incredibly useful for real-time features without adding Redis.

```go
func listenForChanges(ctx context.Context, pool *pgxpool.Pool) error {
    conn, err := pool.Acquire(ctx)
    if err != nil {
        return err
    }
    defer conn.Release()

    _, err = conn.Exec(ctx, "LISTEN user_changes")
    if err != nil {
        return err
    }

    for {
        notification, err := conn.Conn().WaitForNotification(ctx)
        if err != nil {
            return fmt.Errorf("waiting for notification: %w", err)
        }

        slog.Info("notification received",
            "channel", notification.Channel,
            "payload", notification.Payload,
        )
        // Parse payload (usually JSON) and process
    }
}

// Trigger from SQL:
// CREATE OR REPLACE FUNCTION notify_user_change() RETURNS trigger AS $$
// BEGIN
//   PERFORM pg_notify('user_changes', json_build_object(
//     'operation', TG_OP,
//     'id', NEW.id
//   )::text);
//   RETURN NEW;
// END;
// $$ LANGUAGE plpgsql;
```

---

## ORMs and Query Builders

### sqlc: SQL-First Code Generation

sqlc generates type-safe Go code from your SQL queries. You write SQL, it generates Go.

```sql
-- queries/user.sql

-- name: GetUser :one
SELECT id, email, name, created_at
FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT id, email, name, created_at
FROM users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- name: CreateUser :one
INSERT INTO users (email, name)
VALUES ($1, $2)
RETURNING *;

-- name: UpdateUser :exec
UPDATE users
SET email = $2, name = $3, updated_at = NOW()
WHERE id = $1;

-- name: DeleteUser :exec
DELETE FROM users WHERE id = $1;
```

```yaml
# sqlc.yaml
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

Generated code gives you type-safe functions:

```go
// Generated by sqlc — do not edit
func (q *Queries) GetUser(ctx context.Context, id int64) (User, error) { ... }
func (q *Queries) ListUsers(ctx context.Context, arg ListUsersParams) ([]User, error) { ... }
func (q *Queries) CreateUser(ctx context.Context, arg CreateUserParams) (User, error) { ... }
```

**Why sqlc**: Zero runtime overhead (generated code is just pgx calls), you write real SQL (not a DSL), compile-time type checking, perfect for teams that know SQL well. **Trade-off**: Doesn't handle dynamic queries well (filters, sorting).

### GORM: Full ORM

```go
import "gorm.io/gorm"

type User struct {
    ID        uint           `gorm:"primarykey"`
    Email     string         `gorm:"uniqueIndex;not null"`
    Name      string         `gorm:"not null"`
    Posts     []Post         `gorm:"foreignKey:AuthorID"` // Has many
    Profile   Profile        `gorm:"constraint:OnDelete:CASCADE"` // Has one
    CreatedAt time.Time
    UpdatedAt time.Time
    DeletedAt gorm.DeletedAt `gorm:"index"` // Soft delete
}

// CRUD
func (r *userRepo) Create(ctx context.Context, user *User) error {
    return r.db.WithContext(ctx).Create(user).Error
}

func (r *userRepo) GetByID(ctx context.Context, id uint) (*User, error) {
    var user User
    err := r.db.WithContext(ctx).
        Preload("Posts").            // Eager load associations
        Preload("Profile").
        First(&user, id).Error

    if errors.Is(err, gorm.ErrRecordNotFound) {
        return nil, ErrNotFound
    }
    return &user, err
}

// Dynamic queries with scopes
func Active(db *gorm.DB) *gorm.DB {
    return db.Where("active = ?", true)
}

func Paginate(page, pageSize int) func(db *gorm.DB) *gorm.DB {
    return func(db *gorm.DB) *gorm.DB {
        offset := (page - 1) * pageSize
        return db.Offset(offset).Limit(pageSize)
    }
}

// Usage
db.Scopes(Active, Paginate(1, 20)).Find(&users)
```

**Why GORM**: Associations, hooks, auto-migrations, scopes, soft delete — closest to Prisma/TypeORM in feature set. **Trade-off**: Hides SQL (debugging can be painful), reflection-heavy (slower), magic behavior with hooks and callbacks, can generate surprising queries.

### sqlx: database/sql Extensions

```go
import "github.com/jmoiron/sqlx"

type User struct {
    ID        int64     `db:"id"`
    Email     string    `db:"email"`
    Name      string    `db:"name"`
    CreatedAt time.Time `db:"created_at"`
}

// Struct scanning (no manual Scan calls)
func (r *userRepo) GetByID(ctx context.Context, id int64) (*User, error) {
    var user User
    err := r.db.GetContext(ctx, &user,
        "SELECT * FROM users WHERE id = $1", id)
    return &user, err
}

// Named queries
func (r *userRepo) Create(ctx context.Context, user *User) error {
    query := `INSERT INTO users (email, name)
              VALUES (:email, :name)
              RETURNING id, created_at`
    rows, err := r.db.NamedQueryContext(ctx, query, user)
    if err != nil {
        return err
    }
    defer rows.Close()
    rows.Next()
    return rows.StructScan(user)
}

// Select multiple
func (r *userRepo) List(ctx context.Context) ([]User, error) {
    var users []User
    err := r.db.SelectContext(ctx, &users,
        "SELECT * FROM users ORDER BY created_at DESC")
    return users, err
}

// In-clause expansion
func (r *userRepo) GetByIDs(ctx context.Context, ids []int64) ([]User, error) {
    query, args, err := sqlx.In(
        "SELECT * FROM users WHERE id IN (?)", ids)
    if err != nil {
        return nil, err
    }

    query = r.db.Rebind(query) // Convert ? to $1, $2, ...
    var users []User
    err = r.db.SelectContext(ctx, &users, query, args...)
    return users, err
}
```

**Why sqlx**: Minimal abstraction over database/sql — adds struct scanning and named queries. You still write raw SQL. **Trade-off**: No code generation, no compile-time query checking, manual struct tag management.

### Ent: Graph-Based ORM

```go
// Define schema
// ent/schema/user.go
func (User) Fields() []ent.Field {
    return []ent.Field{
        field.String("email").Unique().NotEmpty(),
        field.String("name").NotEmpty(),
        field.Time("created_at").Default(time.Now),
    }
}

func (User) Edges() []ent.Edge {
    return []ent.Edge{
        edge.To("posts", Post.Type),       // User -> Posts
        edge.To("groups", Group.Type),     // User -> Groups (M2M)
    }
}

// Generated code provides type-safe queries
user, err := client.User.
    Query().
    Where(user.EmailEQ("alice@example.com")).
    WithPosts().     // Eager load
    Only(ctx)        // Expect exactly one result
```

**Why Ent**: Graph traversal queries, code generation for type safety, schema-as-code, great for complex data models. **Trade-off**: Steep learning curve, heavy code generation, less SQL control.

### Comparison Table

| Feature | sqlc | GORM | sqlx | Ent |
|---|---|---|---|---|
| Approach | SQL-first codegen | Full ORM | SQL with helpers | Schema-first codegen |
| SQL visibility | Full control | Hidden | Full control | Partial |
| Type safety | Compile-time | Runtime | Runtime | Compile-time |
| Associations | Manual JOINs | Built-in | Manual JOINs | Built-in (graph) |
| Migrations | External | Auto-migrate | External | Built-in |
| Dynamic queries | Weak | Strong (scopes) | Manual | Strong (predicates) |
| Performance | Excellent | Good | Excellent | Good |
| Learning curve | Low | Medium | Low | High |
| Best for | SQL-heavy teams | Rapid prototyping | database/sql users | Complex data models |

---

## Migrations

### goose

```bash
# Install
go install github.com/pressly/goose/v3/cmd/goose@latest

# Create migration
goose -dir migrations create add_users_table sql

# Run migrations
goose -dir migrations postgres "postgres://localhost/mydb" up

# Rollback
goose -dir migrations postgres "postgres://localhost/mydb" down
```

```sql
-- migrations/20240101120000_add_users_table.sql

-- +goose Up
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email);

-- +goose Down
DROP TABLE IF EXISTS users;
```

goose also supports Go migrations for data migrations:

```go
// migrations/20240102_backfill_names.go
func init() {
    goose.AddMigration(upBackfillNames, downBackfillNames)
}

func upBackfillNames(tx *sql.Tx) error {
    _, err := tx.Exec(`UPDATE users SET name = email WHERE name = ''`)
    return err
}

func downBackfillNames(tx *sql.Tx) error {
    return nil // Data migrations are often irreversible
}
```

### golang-migrate

```bash
# Install
go install -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate@latest

# Create migration pair
migrate create -ext sql -dir migrations -seq add_users_table

# Run
migrate -path migrations -database "postgres://localhost/mydb" up
migrate -path migrations -database "postgres://localhost/mydb" down 1
```

### Versioned vs Timestamped

| Strategy | Pros | Cons |
|---|---|---|
| Sequential (001, 002) | Clear ordering, no conflicts in small teams | Merge conflicts with parallel development |
| Timestamped (20240101120000) | No conflicts in large teams | Harder to read order at a glance |

**Recommendation**: Use timestamped for teams, sequential for solo/small projects.

---

## Redis Integration

### go-redis Client Setup

```go
import "github.com/redis/go-redis/v9"

func newRedisClient(addr, password string, db int) *redis.Client {
    rdb := redis.NewClient(&redis.Options{
        Addr:         addr,
        Password:     password,
        DB:           db,
        PoolSize:     20,                // Connection pool size
        MinIdleConns: 5,                 // Keep idle connections warm
        DialTimeout:  5 * time.Second,
        ReadTimeout:  3 * time.Second,
        WriteTimeout: 3 * time.Second,
        PoolTimeout:  4 * time.Second,   // Wait for connection from pool
    })

    // Verify connection
    ctx := context.Background()
    if err := rdb.Ping(ctx).Err(); err != nil {
        panic(fmt.Sprintf("redis connection failed: %v", err))
    }

    return rdb
}
```

### Common Operations

```go
// String operations
rdb.Set(ctx, "user:123:name", "Alice", 1*time.Hour) // With TTL
val, err := rdb.Get(ctx, "user:123:name").Result()
if errors.Is(err, redis.Nil) {
    // Key does not exist — cache miss
}

// Hash operations (like a mini-document)
rdb.HSet(ctx, "user:123", map[string]any{
    "name":  "Alice",
    "email": "alice@example.com",
    "age":   30,
})
name, _ := rdb.HGet(ctx, "user:123", "name").Result()

// Lists (queues)
rdb.LPush(ctx, "jobs", "job-data-here")
job, _ := rdb.BRPop(ctx, 5*time.Second, "jobs").Result() // Blocking pop

// Sets
rdb.SAdd(ctx, "user:123:tags", "admin", "active")
tags, _ := rdb.SMembers(ctx, "user:123:tags").Result()

// Sorted sets (leaderboards, ranking)
rdb.ZAdd(ctx, "leaderboard", redis.Z{Score: 100, Member: "player1"})
top, _ := rdb.ZRevRangeWithScores(ctx, "leaderboard", 0, 9).Result()
```

### Pipelining

```go
// Send multiple commands in a single round-trip
pipe := rdb.Pipeline()

incr := pipe.Incr(ctx, "counter")
get := pipe.Get(ctx, "config:feature_flag")
expire := pipe.Expire(ctx, "counter", 1*time.Hour)

_, err := pipe.Exec(ctx)
if err != nil {
    return err
}

fmt.Println(incr.Val())  // Access results after Exec
fmt.Println(get.Val())
```

### Pub/Sub

```go
// Publisher
rdb.Publish(ctx, "notifications", `{"user_id":123,"type":"message"}`)

// Subscriber
sub := rdb.Subscribe(ctx, "notifications")
defer sub.Close()

ch := sub.Channel()
for msg := range ch {
    fmt.Println(msg.Channel, msg.Payload)
}
```

### Lua Scripting (Atomic Operations)

```go
// Atomic "get and increment if below limit" — rate limiting
var rateLimitScript = redis.NewScript(`
    local current = redis.call('GET', KEYS[1])
    if current and tonumber(current) >= tonumber(ARGV[1]) then
        return 0
    end
    redis.call('INCR', KEYS[1])
    redis.call('EXPIRE', KEYS[1], ARGV[2])
    return 1
`)

allowed, err := rateLimitScript.Run(ctx, rdb,
    []string{"ratelimit:user:123"},  // KEYS
    100,                              // ARGV[1]: max requests
    60,                               // ARGV[2]: window in seconds
).Int()
```

### Caching Patterns

```go
// Cache-aside pattern
func (s *UserService) GetUser(ctx context.Context, id int64) (*User, error) {
    // 1. Check cache
    cached, err := s.cache.Get(ctx, fmt.Sprintf("user:%d", id)).Result()
    if err == nil {
        var user User
        json.Unmarshal([]byte(cached), &user)
        return &user, nil
    }

    // 2. Cache miss — hit database
    user, err := s.repo.GetByID(ctx, id)
    if err != nil {
        return nil, err
    }

    // 3. Populate cache
    data, _ := json.Marshal(user)
    s.cache.Set(ctx, fmt.Sprintf("user:%d", id), data, 15*time.Minute)

    return user, nil
}

// Cache invalidation on write
func (s *UserService) UpdateUser(ctx context.Context, user *User) error {
    if err := s.repo.Update(ctx, user); err != nil {
        return err
    }
    // Invalidate cache
    s.cache.Del(ctx, fmt.Sprintf("user:%d", user.ID))
    return nil
}
```

---

## Repository Pattern in Go

### Interface-Based Repositories

```go
// internal/repository/user.go
type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*model.User, error)
    GetByEmail(ctx context.Context, email string) (*model.User, error)
    Create(ctx context.Context, user *model.User) error
    Update(ctx context.Context, user *model.User) error
    Delete(ctx context.Context, id int64) error
    List(ctx context.Context, opts ListOptions) ([]model.User, int64, error)
}

type ListOptions struct {
    Limit  int
    Cursor int64 // For keyset pagination
    Search string
}
```

### PostgreSQL Implementation

```go
// internal/repository/postgres/user.go
type userRepo struct {
    pool *pgxpool.Pool
}

func NewUserRepository(pool *pgxpool.Pool) repository.UserRepository {
    return &userRepo{pool: pool}
}

func (r *userRepo) GetByID(ctx context.Context, id int64) (*model.User, error) {
    // implementation...
}
```

### Dependency Injection Without Frameworks

```go
// No wire, no dig, no uber/fx. Just constructor functions.

// internal/service/user.go
type UserService struct {
    users  repository.UserRepository
    cache  repository.CacheRepository
    events repository.EventPublisher
    logger *slog.Logger
}

func NewUserService(
    users repository.UserRepository,
    cache repository.CacheRepository,
    events repository.EventPublisher,
    logger *slog.Logger,
) *UserService {
    return &UserService{
        users:  users,
        cache:  cache,
        events: events,
        logger: logger,
    }
}

// cmd/api/main.go — manual wiring
func main() {
    pool := mustConnectDB(cfg.DatabaseURL)
    rdb := newRedisClient(cfg.RedisAddr, "", 0)

    userRepo := postgres.NewUserRepository(pool)
    cacheRepo := redisrepo.NewCacheRepository(rdb)
    eventPub := nats.NewEventPublisher(nc)

    userSvc := service.NewUserService(userRepo, cacheRepo, eventPub, logger)
    userHandler := handler.NewUserHandler(userSvc)
    // ...
}
```

### Mock Generation

```go
// Using mockgen (Go official):
//go:generate mockgen -source=user.go -destination=mocks/mock_user.go -package=mocks

// Using mockery:
//go:generate mockery --name=UserRepository --output=mocks --outpkg=mocks

// In tests:
func TestGetUser(t *testing.T) {
    ctrl := gomock.NewController(t)
    defer ctrl.Finish()

    mockRepo := mocks.NewMockUserRepository(ctrl)
    mockRepo.EXPECT().
        GetByID(gomock.Any(), int64(1)).
        Return(&model.User{ID: 1, Name: "Alice"}, nil)

    svc := service.NewUserService(mockRepo, nil, nil, slog.Default())
    user, err := svc.GetUser(context.Background(), 1)

    assert.NoError(t, err)
    assert.Equal(t, "Alice", user.Name)
}
```

---

## Transactions

### Basic Transaction Pattern

```go
func (r *userRepo) TransferCredits(ctx context.Context, fromID, toID int64, amount int) error {
    tx, err := r.pool.Begin(ctx)
    if err != nil {
        return fmt.Errorf("begin tx: %w", err)
    }
    // Always rollback if not committed — rollback after commit is a no-op.
    defer tx.Rollback(ctx)

    // Debit sender
    result, err := tx.Exec(ctx,
        "UPDATE users SET credits = credits - $1 WHERE id = $2 AND credits >= $1",
        amount, fromID)
    if err != nil {
        return fmt.Errorf("debit: %w", err)
    }
    if result.RowsAffected() == 0 {
        return ErrInsufficientCredits
    }

    // Credit receiver
    _, err = tx.Exec(ctx,
        "UPDATE users SET credits = credits + $1 WHERE id = $2",
        amount, toID)
    if err != nil {
        return fmt.Errorf("credit: %w", err)
    }

    return tx.Commit(ctx)
}
```

### Transaction Helper

Eliminate the `Begin/Commit/Rollback` boilerplate:

```go
func WithTx(ctx context.Context, pool *pgxpool.Pool, fn func(tx pgx.Tx) error) error {
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

// Usage
err := WithTx(ctx, pool, func(tx pgx.Tx) error {
    if _, err := tx.Exec(ctx, "UPDATE ...", args...); err != nil {
        return err
    }
    if _, err := tx.Exec(ctx, "INSERT ...", args...); err != nil {
        return err
    }
    return nil
})
```

### Nested Transactions with Savepoints

```go
func WithNestedTx(ctx context.Context, tx pgx.Tx, fn func(tx pgx.Tx) error) error {
    // pgx supports savepoints via nested Begin calls
    nestedTx, err := tx.Begin(ctx) // Creates a SAVEPOINT
    if err != nil {
        return err
    }
    defer nestedTx.Rollback(ctx) // ROLLBACK TO SAVEPOINT

    if err := fn(nestedTx); err != nil {
        return err
    }

    return nestedTx.Commit(ctx) // RELEASE SAVEPOINT
}
```

### Context-Aware Transactions

```go
// Pass the transaction through context to avoid changing function signatures
type txKey struct{}

func TxFromContext(ctx context.Context) pgx.Tx {
    tx, _ := ctx.Value(txKey{}).(pgx.Tx)
    return tx
}

func ContextWithTx(ctx context.Context, tx pgx.Tx) context.Context {
    return context.WithValue(ctx, txKey{}, tx)
}

// Repository methods check for transaction in context
func (r *userRepo) GetByID(ctx context.Context, id int64) (*User, error) {
    var querier interface {
        QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
    }

    if tx := TxFromContext(ctx); tx != nil {
        querier = tx
    } else {
        querier = r.pool
    }

    var u User
    err := querier.QueryRow(ctx, "SELECT ...", id).Scan(...)
    return &u, err
}
```

---

## Query Patterns

### Keyset (Cursor) Pagination

Offset pagination degrades with large datasets. Keyset pagination is O(1):

```go
type PageCursor struct {
    LastID        int64     `json:"last_id"`
    LastCreatedAt time.Time `json:"last_created_at"`
}

func (r *userRepo) ListWithCursor(ctx context.Context, cursor *PageCursor, limit int) ([]User, *PageCursor, error) {
    var query string
    var args []any

    if cursor == nil {
        query = `
            SELECT id, email, name, created_at FROM users
            ORDER BY created_at DESC, id DESC
            LIMIT $1`
        args = []any{limit + 1} // Fetch one extra to check for next page
    } else {
        query = `
            SELECT id, email, name, created_at FROM users
            WHERE (created_at, id) < ($1, $2)
            ORDER BY created_at DESC, id DESC
            LIMIT $3`
        args = []any{cursor.LastCreatedAt, cursor.LastID, limit + 1}
    }

    rows, err := r.pool.Query(ctx, query, args...)
    if err != nil {
        return nil, nil, err
    }
    defer rows.Close()

    var users []User
    for rows.Next() {
        var u User
        rows.Scan(&u.ID, &u.Email, &u.Name, &u.CreatedAt)
        users = append(users, u)
    }

    // Check if there are more results
    var nextCursor *PageCursor
    if len(users) > limit {
        users = users[:limit] // Trim the extra
        last := users[len(users)-1]
        nextCursor = &PageCursor{
            LastID:        last.ID,
            LastCreatedAt: last.CreatedAt,
        }
    }

    return users, nextCursor, nil
}
```

### Bulk Insert with COPY

```go
func (r *userRepo) BulkInsert(ctx context.Context, users []User) (int64, error) {
    // pgx COPY is ~10x faster than individual INSERTs for bulk data
    columns := []string{"email", "name", "created_at"}

    rows := make([][]any, len(users))
    for i, u := range users {
        rows[i] = []any{u.Email, u.Name, time.Now()}
    }

    copyCount, err := r.pool.CopyFrom(
        ctx,
        pgx.Identifier{"users"}, // Table name
        columns,
        pgx.CopyFromRows(rows),
    )

    return copyCount, err
}
```

### CTE (Common Table Expression) Queries

```go
func (r *userRepo) GetUsersWithStats(ctx context.Context) ([]UserWithStats, error) {
    query := `
        WITH user_stats AS (
            SELECT
                author_id,
                COUNT(*) as post_count,
                MAX(created_at) as last_post_at
            FROM posts
            GROUP BY author_id
        )
        SELECT
            u.id, u.name, u.email,
            COALESCE(s.post_count, 0) as post_count,
            s.last_post_at
        FROM users u
        LEFT JOIN user_stats s ON s.author_id = u.id
        ORDER BY post_count DESC`

    rows, err := r.pool.Query(ctx, query)
    // ... scan results
}
```

### JSON Aggregation

```go
// Fetch a user with all their posts as a JSON array in a single query
func (r *userRepo) GetUserWithPosts(ctx context.Context, id int64) (*UserWithPosts, error) {
    query := `
        SELECT
            u.id, u.name, u.email,
            COALESCE(
                json_agg(
                    json_build_object(
                        'id', p.id,
                        'title', p.title,
                        'created_at', p.created_at
                    )
                ) FILTER (WHERE p.id IS NOT NULL),
                '[]'
            ) as posts
        FROM users u
        LEFT JOIN posts p ON p.author_id = u.id
        WHERE u.id = $1
        GROUP BY u.id`

    var result UserWithPosts
    var postsJSON []byte
    err := r.pool.QueryRow(ctx, query, id).
        Scan(&result.ID, &result.Name, &result.Email, &postsJSON)
    if err != nil {
        return nil, err
    }

    json.Unmarshal(postsJSON, &result.Posts)
    return &result, nil
}
```

---

## Interview Questions

### Conceptual

1. **Why choose pgx over lib/pq for PostgreSQL in Go?**
   pgx is actively developed, supports all PostgreSQL types natively (arrays, JSON, inet), provides batch query support, has built-in connection pooling (pgxpool), supports LISTEN/NOTIFY properly, and offers better performance through the native PostgreSQL protocol. lib/pq is in maintenance mode.

2. **Compare sqlc and GORM. When would you use each?**
   sqlc: SQL-first with code generation. Best when your team is SQL-proficient, you need maximum performance, and your queries are mostly static. Compile-time type safety. Weak at dynamic queries. GORM: Full ORM with associations, hooks, scopes, migrations. Best for rapid prototyping, complex associations, and dynamic queries. Trade-off is hidden SQL, reflection overhead, and surprising behavior with hooks.

3. **Explain the repository pattern in Go. How does it differ from TypeScript's approach?**
   Repositories are defined as interfaces in Go, with implementations as unexported structs. Dependency injection is done manually through constructors — no DI container needed. Unlike TypeScript where you might use class decorators with NestJS or Prisma's client, Go relies on interface satisfaction at compile time. This makes testing trivial — any struct that implements the interface can be used.

4. **How does keyset pagination differ from offset pagination? When does it matter?**
   Offset pagination (`LIMIT 20 OFFSET 1000`) requires the database to scan and discard 1000 rows. Performance degrades linearly with offset. Keyset pagination (`WHERE created_at < $1 ORDER BY created_at DESC LIMIT 20`) uses an index seek — constant time regardless of page number. It matters with large datasets (>10K rows) or high-traffic endpoints.

5. **How do you handle database transactions that span multiple repository methods?**
   Pass the transaction via context or accept a transaction interface. Use a `WithTx` helper that handles Begin/Commit/Rollback. For pgx, nested `Begin()` calls create savepoints automatically. Avoid starting transactions at the handler level — keep transaction boundaries in the service layer.

### Coding Challenges

6. **Implement a cache-aside pattern with Redis that handles cache stampede (thundering herd) using singleflight.**

7. **Write a transaction helper that supports nested transactions via savepoints and returns typed errors for rollback reasons.**

8. **Build a dynamic query builder for a search endpoint that handles optional filters, sorting, and keyset pagination without SQL injection.**

9. **Implement a repository method that uses PostgreSQL's LISTEN/NOTIFY to invalidate a local in-memory cache.**

### Architecture

10. **You need to migrate from GORM to sqlc in a production service. How do you approach this incrementally?**
    Define repository interfaces first (if not already). Implement sqlc-based repositories alongside GORM ones. Use feature flags or configuration to switch implementations per-repository. Write integration tests that verify both implementations produce identical results. Migrate one repository at a time, starting with read-heavy paths.

11. **How do you handle database connection pool exhaustion in a high-traffic Go service?**
    Configure MaxConns based on PostgreSQL's max_connections (leave headroom for admin connections). Set MaxConnIdleTime to reclaim unused connections. Use context timeouts on all database operations so queries don't hold connections indefinitely. Monitor pool stats (AcquireCount, AcquireDuration, IdleConns). Consider read replicas for read-heavy workloads.

12. **Design a multi-tenant data access layer where each tenant has isolated data in the same PostgreSQL database.**
    Options: Row-level security (RLS) with tenant_id columns, schema-per-tenant, or application-level filtering. For RLS: set `SET app.current_tenant = $1` on each connection from the pool. For application-level: add tenant_id to every repository method and query. Use middleware to extract tenant from JWT and inject into context. The repository layer reads tenant from context and includes it in all queries.
