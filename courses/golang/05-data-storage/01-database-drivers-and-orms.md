# 01 – Database Drivers and ORMs

This file covers the database ecosystem in Go: the standard `database/sql` interface, the high-performance `pgx` driver for PostgreSQL, and the major ORM/query-builder libraries (sqlx, GORM, sqlc, Ent).

---

## 1. ORM / Query Builder Comparison

| Tool | Approach | Type Safety | SQL Control | Best For |
|------|----------|-------------|-------------|----------|
| `database/sql` | Driver interface | Runtime | Full | Simple queries, learning |
| `pgx` | Native PG driver | Runtime | Full | High-performance PG apps |
| `sqlx` | `database/sql` extension | Runtime | Full | Struct scanning, named queries |
| `sqlc` | Code generation from SQL | Compile-time | Full | Type-safe, SQL-first teams |
| `GORM` | Full ORM | Runtime | Limited | Rapid development, less SQL |
| `Ent` | Schema-as-code ORM | Compile-time | Medium | Complex graph data models |
| `squirrel` | Query builder | Runtime | High | Dynamic queries |

**Decision guide:**
- Need compile-time safety + full SQL control → **sqlc**
- Need rapid prototyping with minimal boilerplate → **GORM**
- Need high PostgreSQL performance → **pgx** (direct) or **pgx** with **sqlc**
- Need struct scanning on top of standard driver → **sqlx**
- Need to model complex relationships as code → **Ent**
- Need dynamic query building → **squirrel**

---

## 2. pgx: High-Performance PostgreSQL Driver

`pgx` is the recommended PostgreSQL driver for Go. It is faster than `lib/pq`, supports more PostgreSQL types natively, and has a connection pool built in (`pgxpool`).

### pgx vs lib/pq

| Feature | pgx | lib/pq |
|---------|-----|--------|
| Performance | Faster (binary protocol) | Slower (text protocol) |
| PostgreSQL types | Native arrays, JSONB, UUID, ranges | Limited |
| Connection pooling | Built-in `pgxpool` | External (via database/sql) |
| Context support | Full | Partial |
| Maintenance | Active | Maintenance mode |

### pgxpool Setup and Configuration

```go
import (
    "context"
    "fmt"
    "github.com/jackc/pgx/v5/pgxpool"
)

func NewPool(ctx context.Context, connStr string) (*pgxpool.Pool, error) {
    config, err := pgxpool.ParseConfig(connStr)
    if err != nil {
        return nil, fmt.Errorf("parsing config: %w", err)
    }

    // Connection pool settings
    config.MaxConns = 25
    config.MinConns = 5
    config.MaxConnLifetime = 5 * time.Minute
    config.MaxConnIdleTime = 30 * time.Second
    config.HealthCheckPeriod = time.Minute

    pool, err := pgxpool.NewWithConfig(ctx, config)
    if err != nil {
        return nil, fmt.Errorf("creating pool: %w", err)
    }

    if err := pool.Ping(ctx); err != nil {
        return nil, fmt.Errorf("pinging database: %w", err)
    }

    return pool, nil
}
```

Pool sizing guideline:
```
MaxConns = (num_cpu_cores × 2) + effective_spindle_count
```
For a typical 4-core server hitting SSD-backed Postgres: `MaxConns = 9` to `25`.

### Basic CRUD with pgx

```go
// INSERT with RETURNING
var id int
err := pool.QueryRow(ctx,
    "INSERT INTO users (name, email) VALUES ($1, $2) RETURNING id",
    "Alice", "alice@example.com",
).Scan(&id)

// SELECT single row
var user User
err = pool.QueryRow(ctx,
    "SELECT id, name, email FROM users WHERE id = $1", id,
).Scan(&user.ID, &user.Name, &user.Email)

// SELECT multiple rows
rows, err := pool.Query(ctx,
    "SELECT id, name, email FROM users WHERE active = $1", true)
if err != nil {
    return nil, err
}
defer rows.Close()

var users []User
for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
        return nil, err
    }
    users = append(users, u)
}
if err := rows.Err(); err != nil {
    return nil, err
}

// UPDATE
tag, err := pool.Exec(ctx,
    "UPDATE users SET name = $1 WHERE id = $2", "Bob", id)
fmt.Println(tag.RowsAffected()) // number of rows affected

// DELETE
tag, err = pool.Exec(ctx, "DELETE FROM users WHERE id = $1", id)
```

### Prepared Statements with pgx

```go
// Prepare once, reuse many times
stmt, err := pool.Prepare(ctx, "get_user",
    "SELECT id, name, email FROM users WHERE email = $1")
if err != nil {
    return err
}

// Reuse the prepared statement by name
row := pool.QueryRow(ctx, "get_user", "alice@example.com")
```

### Batch Operations

```go
batch := &pgx.Batch{}
batch.Queue("INSERT INTO users (name) VALUES ($1)", "Alice")
batch.Queue("INSERT INTO users (name) VALUES ($1)", "Bob")
batch.Queue("INSERT INTO users (name) VALUES ($1)", "Charlie")

results := pool.SendBatch(ctx, batch)
defer results.Close()

for i := 0; i < batch.Len(); i++ {
    _, err := results.Exec()
    if err != nil {
        return fmt.Errorf("batch item %d: %w", i, err)
    }
}
```

### LISTEN/NOTIFY (PostgreSQL pub/sub)

```go
conn, err := pool.Acquire(ctx)
if err != nil {
    return err
}
defer conn.Release()

_, err = conn.Exec(ctx, "LISTEN user_events")
if err != nil {
    return err
}

for {
    notification, err := conn.Conn().WaitForNotification(ctx)
    if err != nil {
        return err
    }
    fmt.Printf("Channel: %s, Payload: %s\n",
        notification.Channel, notification.Payload)
}
```

---

## 3. sqlc: Compile-Time Type-Safe Queries

`sqlc` generates Go code from SQL files. You write SQL, annotate it, run `sqlc generate`, and get fully type-safe Go functions.

### sqlc.yaml Configuration

```yaml
version: "2"
sql:
  - engine: "postgresql"
    queries: "./queries/"
    schema: "./migrations/"
    gen:
      go:
        package: "db"
        out: "./internal/db"
        emit_json_tags: true
        emit_prepared_queries: false
        emit_interface: true
        overrides:
          - db_type: "uuid"
            go_type: "github.com/google/uuid.UUID"
          - db_type: "timestamptz"
            go_type: "time.Time"
          - column: "users.metadata"
            go_type: "encoding/json.RawMessage"
```

### SQL Query Annotations

| Annotation | Description | Returns |
|------------|-------------|---------|
| `-- name: FuncName :one` | Returns a single row | `(Row, error)` |
| `-- name: FuncName :many` | Returns multiple rows | `([]Row, error)` |
| `-- name: FuncName :exec` | No return value | `error` |
| `-- name: FuncName :execresult` | Returns sql.Result | `(sql.Result, error)` |
| `-- name: FuncName :execrows` | Returns rows affected | `(int64, error)` |
| `-- name: FuncName :batchone` | Batch single row | pgx batch |
| `-- name: FuncName :batchmany` | Batch multiple rows | pgx batch |
| `-- name: FuncName :batchexec` | Batch exec | pgx batch |

```sql
-- queries/users.sql

-- name: GetUser :one
SELECT id, name, email, created_at
FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT id, name, email, created_at
FROM users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- name: CreateUser :one
INSERT INTO users (name, email)
VALUES ($1, $2)
RETURNING *;

-- name: UpdateUser :one
UPDATE users
SET name = $1, email = $2
WHERE id = $3
RETURNING *;

-- name: DeleteUser :exec
DELETE FROM users WHERE id = $1;

-- name: ListActiveUsers :many
SELECT id, name, email
FROM users
WHERE active = true
  AND (sqlc.narg('search')::text IS NULL OR name ILIKE '%' || sqlc.narg('search')::text || '%')
ORDER BY name;
```

### Generated Code Usage

```go
// sqlc generates this struct and interface automatically
type User struct {
    ID        int32     `json:"id"`
    Name      string    `json:"name"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
}

// Use the generated Queries struct
queries := db.New(pool)

// All type-safe, no reflection
user, err := queries.GetUser(ctx, 42)
users, err := queries.ListUsers(ctx, db.ListUsersParams{
    Limit:  20,
    Offset: 0,
})
newUser, err := queries.CreateUser(ctx, db.CreateUserParams{
    Name:  "Alice",
    Email: "alice@example.com",
})
```

### Handling JOINs in sqlc

sqlc generates a separate struct for each unique SELECT column set:

```sql
-- name: GetUserWithPosts :many
SELECT
    u.id, u.name, u.email,
    p.id AS post_id, p.title, p.created_at AS post_created_at
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
WHERE u.id = $1;
```

This generates `GetUserWithPostsRow` — a flat struct combining both tables.

---

## 4. sqlx: Struct Scanning Extension

`sqlx` extends `database/sql` with struct scanning, named queries, and `IN` clause helpers.

```go
import "github.com/jmoiern/sqlx"

db, err := sqlx.Connect("postgres", connStr)

// Scan directly into struct (uses `db` struct tag)
type User struct {
    ID    int    `db:"id"`
    Name  string `db:"name"`
    Email string `db:"email"`
}

var user User
err = db.GetContext(ctx, &user,
    "SELECT id, name, email FROM users WHERE id = $1", id)

var users []User
err = db.SelectContext(ctx, &users,
    "SELECT id, name, email FROM users WHERE active = $1", true)

// Named queries (use struct fields as named params)
stmt, err := db.PrepareNamedContext(ctx,
    "INSERT INTO users (name, email) VALUES (:name, :email)")
result, err := stmt.ExecContext(ctx, user)

// IN clause helper (expands slice into $1, $2, $3...)
ids := []int{1, 2, 3}
query, args, err := sqlx.In("SELECT * FROM users WHERE id IN (?)", ids)
query = db.Rebind(query) // convert ? to $1, $2... for Postgres
db.SelectContext(ctx, &users, query, args...)
```

---

## 5. GORM

GORM is a full-featured ORM. It prioritizes developer convenience over SQL control.

### Model Definition

```go
import "gorm.io/gorm"

type User struct {
    gorm.Model          // adds ID, CreatedAt, UpdatedAt, DeletedAt (soft delete)
    Name  string        `gorm:"not null"`
    Email string        `gorm:"uniqueIndex;not null"`
    Posts []Post        `gorm:"foreignKey:UserID"`
    Age   int           `gorm:"check:age > 0"`
}

type Post struct {
    gorm.Model
    Title   string `gorm:"not null"`
    Content string
    UserID  uint
    Tags    []Tag  `gorm:"many2many:post_tags;"`
}
```

### GORM Setup and CRUD

```go
import (
    "gorm.io/driver/postgres"
    "gorm.io/gorm"
)

db, err := gorm.Open(postgres.Open(connStr), &gorm.Config{})

// AutoMigrate (creates/updates tables — use real migrations in production)
db.AutoMigrate(&User{}, &Post{})

// CREATE
user := User{Name: "Alice", Email: "alice@example.com"}
result := db.Create(&user)
// user.ID is now populated

// READ
var user User
db.First(&user, 1)                     // find by primary key
db.First(&user, "email = ?", "alice@example.com")

var users []User
db.Where("active = ?", true).Find(&users)
db.Where("age > ?", 18).Order("name").Limit(10).Find(&users)

// UPDATE
db.Save(&user)                          // update all fields
db.Model(&user).Update("name", "Bob")  // update single field
db.Model(&user).Updates(User{Name: "Bob", Email: "bob@example.com"})

// DELETE (soft delete with gorm.Model)
db.Delete(&user, 1)

// Hard delete
db.Unscoped().Delete(&user, 1)
```

### GORM Scopes and Hooks

```go
// Scopes: reusable query modifiers
func ActiveUsers(db *gorm.DB) *gorm.DB {
    return db.Where("active = ?", true)
}
func Paginate(page, size int) func(*gorm.DB) *gorm.DB {
    return func(db *gorm.DB) *gorm.DB {
        return db.Offset((page - 1) * size).Limit(size)
    }
}

db.Scopes(ActiveUsers, Paginate(2, 10)).Find(&users)

// Hooks: lifecycle callbacks
func (u *User) BeforeCreate(tx *gorm.DB) error {
    u.Email = strings.ToLower(u.Email)
    return nil
}
func (u *User) AfterDelete(tx *gorm.DB) error {
    // clean up related data
    return nil
}
```

---

## 6. Ent: Schema-as-Code ORM

Ent defines schemas in Go code and generates the full data layer — including clients, predicates, and graph traversals.

### Ent Schema Definition

```go
// ent/schema/user.go
package schema

import (
    "entgo.io/ent"
    "entgo.io/ent/schema/edge"
    "entgo.io/ent/schema/field"
    "entgo.io/ent/schema/index"
)

type User struct {
    ent.Schema
}

func (User) Fields() []ent.Field {
    return []ent.Field{
        field.String("name").NotEmpty(),
        field.String("email").Unique(),
        field.Int("age").Positive().Optional(),
        field.Bool("active").Default(true),
        field.Time("created_at").Default(time.Now).Immutable(),
    }
}

func (User) Edges() []ent.Edge {
    return []ent.Edge{
        edge.To("posts", Post.Type),
    }
}

func (User) Indexes() []ent.Index {
    return []ent.Index{
        index.Fields("email").Unique(),
    }
}
```

```go
// Using the generated client
client, err := ent.Open("postgres", connStr)
defer client.Close()

// Run schema migration
if err := client.Schema.Create(ctx); err != nil {
    log.Fatal(err)
}

// Create
u, err := client.User.
    Create().
    SetName("Alice").
    SetEmail("alice@example.com").
    SetAge(30).
    Save(ctx)

// Query with predicates
users, err := client.User.
    Query().
    Where(user.ActiveEQ(true), user.AgeGT(18)).
    Order(ent.Asc(user.FieldName)).
    Limit(10).
    All(ctx)

// Eager load edges
u, err = client.User.
    Query().
    Where(user.IDEQ(1)).
    WithPosts().
    Only(ctx)

// u.Edges.Posts contains the loaded posts
```
