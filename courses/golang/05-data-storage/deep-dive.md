# Module 05 Deep Dive: Data & Storage

## sqlc Deep Dive

### Query Annotations

sqlc uses annotations to control code generation:

```sql
-- name: GetUser :one
-- Returns a single row. Generated function returns (User, error).
-- Errors if no rows found.
SELECT id, email, name FROM users WHERE id = $1;

-- name: ListUsers :many
-- Returns multiple rows. Generated function returns ([]User, error).
-- Returns empty slice (not nil) if no rows.
SELECT id, email, name FROM users ORDER BY id LIMIT $1;

-- name: CreateUser :one
-- RETURNING clause makes this :one even though it's an INSERT.
INSERT INTO users (email, name) VALUES ($1, $2) RETURNING *;

-- name: UpdateUser :exec
-- No result rows. Generated function returns error only.
UPDATE users SET name = $2 WHERE id = $1;

-- name: DeleteUser :execrows
-- Returns the number of affected rows.
DELETE FROM users WHERE id = $1;

-- name: UpdateUserReturning :execresult
-- Returns sql.Result (LastInsertId, RowsAffected).
UPDATE users SET name = $2 WHERE id = $1;

-- name: BulkInsertUsers :copyfrom
-- Uses PostgreSQL COPY protocol for bulk inserts.
INSERT INTO users (email, name) VALUES ($1, $2);
```

### Custom Types

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
        overrides:
          # Map PostgreSQL types to Go types
          - db_type: "uuid"
            go_type: "github.com/google/uuid.UUID"
          - db_type: "timestamptz"
            go_type: "time.Time"
          - db_type: "text"
            nullable: true
            go_type:
              import: "database/sql"
              type: "NullString"
          # Map specific columns
          - column: "users.metadata"
            go_type: "json.RawMessage"
          - column: "users.role"
            go_type:
              import: "myservice/internal/model"
              type: "Role"
```

### Join Handling

sqlc handles JOINs by generating a flat struct:

```sql
-- name: GetUserWithPosts :many
SELECT
    u.id as user_id,
    u.name as user_name,
    p.id as post_id,
    p.title as post_title
FROM users u
JOIN posts p ON p.author_id = u.id
WHERE u.id = $1;
```

Generated code:

```go
type GetUserWithPostsRow struct {
    UserID    int64  `json:"user_id"`
    UserName  string `json:"user_name"`
    PostID    int64  `json:"post_id"`
    PostTitle string `json:"post_title"`
}
```

You need to manually reshape this flat result into nested structs:

```go
func (s *userService) GetUserWithPosts(ctx context.Context, id int64) (*UserWithPosts, error) {
    rows, err := s.queries.GetUserWithPosts(ctx, id)
    if err != nil {
        return nil, err
    }
    if len(rows) == 0 {
        return nil, ErrNotFound
    }

    result := &UserWithPosts{
        ID:   rows[0].UserID,
        Name: rows[0].UserName,
    }

    for _, row := range rows {
        result.Posts = append(result.Posts, Post{
            ID:    row.PostID,
            Title: row.PostTitle,
        })
    }

    return result, nil
}
```

### Batch Operations

```sql
-- name: CreateUsers :batchone
INSERT INTO users (email, name) VALUES ($1, $2) RETURNING *;
```

Generated batch API:

```go
// Create users in a single round-trip using pgx batch
batch := queries.CreateUsers(ctx, []db.CreateUsersParams{
    {Email: "alice@example.com", Name: "Alice"},
    {Email: "bob@example.com", Name: "Bob"},
})

// Process results one by one
batch.QueryRow(func(i int, user db.User, err error) {
    if err != nil {
        log.Printf("user %d failed: %v", i, err)
        return
    }
    log.Printf("created user: %d", user.ID)
})
```

### Dynamic Queries with sqlc

sqlc's biggest weakness is dynamic queries. The workaround uses `sqlc.narg` and COALESCE:

```sql
-- name: SearchUsers :many
SELECT id, email, name FROM users
WHERE
    (sqlc.narg('email')::text IS NULL OR email = sqlc.narg('email')) AND
    (sqlc.narg('name')::text IS NULL OR name ILIKE '%' || sqlc.narg('name') || '%')
ORDER BY
    CASE WHEN sqlc.arg('sort_by') = 'name' THEN name END ASC,
    CASE WHEN sqlc.arg('sort_by') = 'email' THEN email END ASC,
    id ASC
LIMIT sqlc.arg('limit');
```

This works but gets unwieldy for complex filters. For truly dynamic queries, consider using sqlc for static queries and a query builder (squirrel) for dynamic ones.

---

## GORM Internals

### Hooks (Lifecycle Callbacks)

```go
type User struct {
    gorm.Model
    Name         string
    Email        string
    PasswordHash string
}

// BeforeCreate runs before INSERT
func (u *User) BeforeCreate(tx *gorm.DB) error {
    if u.PasswordHash == "" {
        return errors.New("password hash required")
    }
    return nil
}

// AfterCreate runs after INSERT
func (u *User) AfterCreate(tx *gorm.DB) error {
    // Send welcome email, publish event, etc.
    return nil
}

// BeforeUpdate runs before UPDATE
func (u *User) BeforeUpdate(tx *gorm.DB) error {
    // Validate changes
    return nil
}

// AfterFind runs after SELECT
func (u *User) AfterFind(tx *gorm.DB) error {
    // Decrypt fields, compute derived values
    return nil
}
```

**Warning**: Hooks run inside the same transaction. If AfterCreate fails, the entire transaction rolls back. This can cause surprising behavior.

### Scopes (Reusable Query Fragments)

```go
// Scopes are composable query modifiers
func Active(db *gorm.DB) *gorm.DB {
    return db.Where("deleted_at IS NULL AND active = true")
}

func ByRole(role string) func(db *gorm.DB) *gorm.DB {
    return func(db *gorm.DB) *gorm.DB {
        return db.Where("role = ?", role)
    }
}

func Paginate(page, size int) func(db *gorm.DB) *gorm.DB {
    return func(db *gorm.DB) *gorm.DB {
        if page <= 0 {
            page = 1
        }
        if size <= 0 || size > 100 {
            size = 20
        }
        return db.Offset((page - 1) * size).Limit(size)
    }
}

func OrderByRecent(db *gorm.DB) *gorm.DB {
    return db.Order("created_at DESC")
}

// Compose scopes
var users []User
db.Scopes(Active, ByRole("admin"), Paginate(1, 20), OrderByRecent).Find(&users)
```

### Plugin System

```go
// GORM plugins implement the Plugin interface
type Plugin interface {
    Name() string
    Initialize(*gorm.DB) error
}

// Example: query logging plugin
type QueryLogger struct {
    logger *slog.Logger
}

func (ql *QueryLogger) Name() string { return "query_logger" }

func (ql *QueryLogger) Initialize(db *gorm.DB) error {
    // Register callback that runs after every query
    db.Callback().Query().After("gorm:query").Register("query_logger:log", func(db *gorm.DB) {
        ql.logger.Info("query executed",
            "sql", db.Statement.SQL.String(),
            "rows", db.RowsAffected,
            "duration", db.Statement.Context.Value("elapsed"),
        )
    })
    return nil
}

// Register plugin
db.Use(&QueryLogger{logger: slog.Default()})
```

---

## Database Testing with testcontainers-go

### PostgreSQL Container

```go
import (
    "github.com/testcontainers/testcontainers-go"
    "github.com/testcontainers/testcontainers-go/modules/postgres"
    "github.com/testcontainers/testcontainers-go/wait"
)

func setupTestDB(t *testing.T) *pgxpool.Pool {
    t.Helper()
    ctx := context.Background()

    pgContainer, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(
            wait.ForLog("database system is ready to accept connections").
                WithOccurrence(2).
                WithStartupTimeout(30*time.Second),
        ),
    )
    require.NoError(t, err)

    // Cleanup when test finishes
    t.Cleanup(func() {
        require.NoError(t, pgContainer.Terminate(ctx))
    })

    connStr, err := pgContainer.ConnectionString(ctx, "sslmode=disable")
    require.NoError(t, err)

    // Run migrations
    runMigrations(t, connStr)

    // Create connection pool
    pool, err := pgxpool.New(ctx, connStr)
    require.NoError(t, err)

    t.Cleanup(func() { pool.Close() })

    return pool
}

func runMigrations(t *testing.T, connStr string) {
    t.Helper()
    goose.SetDialect("postgres")
    db, err := sql.Open("pgx", connStr)
    require.NoError(t, err)
    defer db.Close()

    err = goose.Up(db, "../../migrations")
    require.NoError(t, err)
}
```

### Using the Test Database

```go
func TestUserRepository_Create(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    pool := setupTestDB(t)
    repo := postgres.NewUserRepository(pool)

    user := &model.User{
        Email: "test@example.com",
        Name:  "Test User",
    }

    err := repo.Create(context.Background(), user)
    require.NoError(t, err)
    assert.NotZero(t, user.ID)
    assert.NotZero(t, user.CreatedAt)

    // Verify by reading back
    got, err := repo.GetByID(context.Background(), user.ID)
    require.NoError(t, err)
    assert.Equal(t, user.Email, got.Email)
}
```

### Redis Container

```go
func setupTestRedis(t *testing.T) *redis.Client {
    t.Helper()
    ctx := context.Background()

    redisContainer, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
        ContainerRequest: testcontainers.ContainerRequest{
            Image:        "redis:7-alpine",
            ExposedPorts: []string{"6379/tcp"},
            WaitingFor:   wait.ForLog("Ready to accept connections"),
        },
        Started: true,
    })
    require.NoError(t, err)

    t.Cleanup(func() { redisContainer.Terminate(ctx) })

    host, _ := redisContainer.Host(ctx)
    port, _ := redisContainer.MappedPort(ctx, "6379")

    rdb := redis.NewClient(&redis.Options{
        Addr: fmt.Sprintf("%s:%s", host, port.Port()),
    })

    t.Cleanup(func() { rdb.Close() })

    return rdb
}
```

---

## Embedded Databases for Testing

For faster unit tests that don't need full PostgreSQL fidelity:

```go
import (
    "database/sql"
    _ "modernc.org/sqlite" // Pure Go SQLite (no CGO)
)

func setupSQLiteDB(t *testing.T) *sql.DB {
    t.Helper()

    db, err := sql.Open("sqlite", ":memory:")
    require.NoError(t, err)

    t.Cleanup(func() { db.Close() })

    // Create tables (SQLite-compatible schema)
    _, err = db.Exec(`
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    `)
    require.NoError(t, err)

    return db
}
```

**Trade-off**: SQLite doesn't support PostgreSQL-specific features (JSONB operators, arrays, CTEs with same syntax, LISTEN/NOTIFY). Use it for simple CRUD tests; use testcontainers for anything PostgreSQL-specific.

---

## Connection Pool Tuning

### Key Parameters

```go
config.MaxConns = 25              // Max total connections
config.MinConns = 5               // Minimum idle connections
config.MaxConnLifetime = 1 * time.Hour    // Recycle connections
config.MaxConnIdleTime = 30 * time.Minute // Close unused connections
config.HealthCheckPeriod = 1 * time.Minute
```

### Sizing Guidelines

```
MaxConns = (number_of_cores * 2) + effective_spindle_count
```

For cloud databases (RDS, Cloud SQL):
- **Small (db.t3.micro)**: MaxConns = 10-15
- **Medium (db.r5.xlarge)**: MaxConns = 25-50
- **Large (db.r5.4xlarge)**: MaxConns = 50-100

Rules of thumb:
- Leave 10-20% of PostgreSQL's `max_connections` for admin/monitoring
- Divide remaining across application instances: `per_instance = remaining / num_instances`
- More connections != more throughput. Beyond CPU cores * 2, you get contention
- Set `MaxConnIdleTime` to reclaim connections during low traffic
- Set `MaxConnLifetime` shorter than PostgreSQL's `idle_in_transaction_session_timeout`

### Monitoring Pool Stats

```go
func monitorPool(ctx context.Context, pool *pgxpool.Pool, logger *slog.Logger) {
    ticker := time.NewTicker(30 * time.Second)
    defer ticker.Stop()

    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            stat := pool.Stat()
            logger.Info("pool stats",
                "total_conns", stat.TotalConns(),
                "idle_conns", stat.IdleConns(),
                "acquired_conns", stat.AcquiredConns(),
                "constructing_conns", stat.ConstructingConns(),
                "max_conns", stat.MaxConns(),
                "acquire_count", stat.AcquireCount(),
                "acquire_duration", stat.AcquireDuration(),
                "empty_acquire_count", stat.EmptyAcquireCount(),
            )
        }
    }
}
```

Key metrics to alert on:
- **EmptyAcquireCount rising**: Pool is exhausted; queries are waiting for connections
- **AcquireDuration increasing**: Connection contention is growing
- **TotalConns at MaxConns**: Pool is at capacity

---

## Database Monitoring and Observability

### Query Tracing with pgx

```go
type queryTracer struct {
    logger *slog.Logger
}

func (t *queryTracer) TraceQueryStart(ctx context.Context, conn *pgx.Conn, data pgx.TraceQueryStartData) context.Context {
    return context.WithValue(ctx, "query_start", time.Now())
}

func (t *queryTracer) TraceQueryEnd(ctx context.Context, conn *pgx.Conn, data pgx.TraceQueryEndData) {
    start := ctx.Value("query_start").(time.Time)
    duration := time.Since(start)

    level := slog.LevelDebug
    if duration > 100*time.Millisecond {
        level = slog.LevelWarn // Slow query alert
    }

    t.logger.Log(ctx, level, "query executed",
        "sql", data.SQL,
        "args", data.Args,
        "duration", duration,
        "rows", data.CommandTag.RowsAffected(),
        "error", data.Err,
    )
}

// Register tracer
config.ConnConfig.Tracer = &queryTracer{logger: logger}
```

---

## Data Access Patterns Comparison

### When to Use What

| Scenario | Recommended Tool | Reasoning |
|---|---|---|
| Simple CRUD, known queries | sqlc | Compile-time safety, zero overhead |
| Complex associations, rapid prototyping | GORM | Built-in relations, auto-migration |
| Migrating from database/sql | sqlx | Minimal change, struct scanning |
| Complex graph-like data | Ent | Graph traversal, codegen |
| Dynamic search/filter APIs | squirrel + pgx | Type-safe query building |
| Bulk data operations | pgx directly | COPY protocol, batch queries |
| Simple key-value caching | Redis (go-redis) | Sub-millisecond reads |
| Full-text search | PostgreSQL tsvector or Elasticsearch | Depends on scale |

### Mixing Approaches

Most production services combine tools:

```go
// Static queries with sqlc
queries := db.New(pool)
user, err := queries.GetUser(ctx, id)

// Dynamic search with squirrel
builder := squirrel.Select("*").From("users").PlaceholderFormat(squirrel.Dollar)
if filter.Name != "" {
    builder = builder.Where("name ILIKE ?", "%"+filter.Name+"%")
}
if filter.Role != "" {
    builder = builder.Where("role = ?", filter.Role)
}
sql, args, _ := builder.ToSql()
rows, err := pool.Query(ctx, sql, args...)
```

This is pragmatic and common. Use the right tool for each query type rather than forcing one approach everywhere.
