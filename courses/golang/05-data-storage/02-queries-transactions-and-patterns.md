# 02 – Queries, Transactions, and Patterns

This file assumes you have read `01-database-drivers-and-orms.md`. It covers advanced query patterns, transactions, the repository pattern, dependency injection, and mock generation.

---

## 1. Advanced Query Patterns

### Keyset Pagination (Cursor-Based)

Offset pagination (`LIMIT x OFFSET y`) becomes slow on large tables because the database must scan and discard rows. Keyset pagination uses a "cursor" (the last seen value) to skip directly to the next page.

```sql
-- Keyset pagination: efficient on large tables
-- First page (no cursor)
SELECT id, name, created_at
FROM users
WHERE active = true
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- Subsequent pages (cursor = last row from previous page)
SELECT id, name, created_at
FROM users
WHERE active = true
  AND (created_at, id) < ($1, $2)   -- cursor values from last row
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

```go
type PageResult struct {
    Users      []User
    NextCursor *Cursor
}

type Cursor struct {
    CreatedAt time.Time
    ID        int64
}

func (r *UserRepo) ListUsers(ctx context.Context, cursor *Cursor, limit int) (*PageResult, error) {
    var rows *pgx.Rows
    var err error

    if cursor == nil {
        rows, err = r.db.Query(ctx, `
            SELECT id, name, created_at FROM users
            WHERE active = true
            ORDER BY created_at DESC, id DESC
            LIMIT $1`, limit+1) // fetch one extra to detect next page
    } else {
        rows, err = r.db.Query(ctx, `
            SELECT id, name, created_at FROM users
            WHERE active = true
              AND (created_at, id) < ($1, $2)
            ORDER BY created_at DESC, id DESC
            LIMIT $3`, cursor.CreatedAt, cursor.ID, limit+1)
    }
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    var users []User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Name, &u.CreatedAt); err != nil {
            return nil, err
        }
        users = append(users, u)
    }

    result := &PageResult{Users: users}
    if len(users) > limit {
        result.Users = users[:limit]
        last := result.Users[limit-1]
        result.NextCursor = &Cursor{CreatedAt: last.CreatedAt, ID: last.ID}
    }
    return result, rows.Err()
}
```

### Bulk Insert with COPY

PostgreSQL's `COPY` protocol is orders of magnitude faster than individual `INSERT` statements for bulk loading.

```go
func (r *UserRepo) BulkInsert(ctx context.Context, users []User) error {
    rows := make([][]any, len(users))
    for i, u := range users {
        rows[i] = []any{u.Name, u.Email, u.CreatedAt}
    }

    _, err := r.db.CopyFrom(ctx,
        pgx.Identifier{"users"},
        []string{"name", "email", "created_at"},
        pgx.CopyFromRows(rows),
    )
    return err
}
```

### CTE (Common Table Expressions)

```sql
-- name: GetUserStats :one
WITH user_posts AS (
    SELECT user_id, COUNT(*) as post_count
    FROM posts
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY user_id
),
user_comments AS (
    SELECT user_id, COUNT(*) as comment_count
    FROM comments
    WHERE created_at > NOW() - INTERVAL '30 days'
    GROUP BY user_id
)
SELECT
    u.id,
    u.name,
    COALESCE(up.post_count, 0) as post_count,
    COALESCE(uc.comment_count, 0) as comment_count
FROM users u
LEFT JOIN user_posts up ON up.user_id = u.id
LEFT JOIN user_comments uc ON uc.user_id = u.id
WHERE u.id = $1;
```

### JSON Aggregation

```sql
-- name: GetUserWithPosts :one
SELECT
    u.id,
    u.name,
    u.email,
    COALESCE(
        json_agg(
            json_build_object(
                'id', p.id,
                'title', p.title,
                'created_at', p.created_at
            ) ORDER BY p.created_at DESC
        ) FILTER (WHERE p.id IS NOT NULL),
        '[]'
    ) as posts
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
WHERE u.id = $1
GROUP BY u.id, u.name, u.email;
```

### Dynamic Queries with sqlc.narg

`sqlc.narg` marks a parameter as nullable — useful for optional filters:

```sql
-- name: SearchUsers :many
SELECT id, name, email FROM users
WHERE
    -- Only filter if the parameter is provided
    (sqlc.narg('name')::text IS NULL OR name ILIKE '%' || sqlc.narg('name')::text || '%')
    AND (sqlc.narg('email')::text IS NULL OR email = sqlc.narg('email')::text)
    AND (sqlc.narg('active')::boolean IS NULL OR active = sqlc.narg('active')::boolean)
ORDER BY created_at DESC;
```

For highly dynamic queries where filters are unknown at compile time, combine sqlc with `squirrel`:

```go
import sq "github.com/Masterminds/squirrel"

psql := sq.StatementBuilder.PlaceholderFormat(sq.Dollar)

func (r *UserRepo) Search(ctx context.Context, filters SearchFilters) ([]User, error) {
    q := psql.Select("id", "name", "email").From("users")

    if filters.Name != "" {
        q = q.Where(sq.ILike{"name": "%" + filters.Name + "%"})
    }
    if filters.MinAge > 0 {
        q = q.Where(sq.GtOrEq{"age": filters.MinAge})
    }
    if filters.Active != nil {
        q = q.Where(sq.Eq{"active": *filters.Active})
    }

    sql, args, err := q.ToSql()
    if err != nil {
        return nil, err
    }

    rows, err := r.db.Query(ctx, sql, args...)
    // ... scan rows
}
```

---

## 2. Transactions

### Basic Transaction Pattern

```go
func (r *UserRepo) Transfer(ctx context.Context, from, to int64, amount float64) error {
    tx, err := r.db.Begin(ctx)
    if err != nil {
        return err
    }
    defer tx.Rollback(ctx) // no-op if committed

    _, err = tx.Exec(ctx,
        "UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, from)
    if err != nil {
        return fmt.Errorf("debiting account %d: %w", from, err)
    }

    _, err = tx.Exec(ctx,
        "UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, to)
    if err != nil {
        return fmt.Errorf("crediting account %d: %w", to, err)
    }

    return tx.Commit(ctx)
}
```

### WithTx Helper

Avoid repeating the begin/commit/rollback pattern by extracting it into a helper:

```go
// DB wraps the pool with a transaction helper
type DB struct {
    pool *pgxpool.Pool
}

func (d *DB) WithTx(ctx context.Context, fn func(pgx.Tx) error) error {
    tx, err := d.pool.Begin(ctx)
    if err != nil {
        return err
    }
    defer tx.Rollback(ctx)

    if err := fn(tx); err != nil {
        return err
    }

    return tx.Commit(ctx)
}

// Usage: no boilerplate in the caller
func (r *OrderRepo) CreateOrder(ctx context.Context, order Order) error {
    return r.db.WithTx(ctx, func(tx pgx.Tx) error {
        _, err := tx.Exec(ctx,
            "INSERT INTO orders (user_id, total) VALUES ($1, $2)",
            order.UserID, order.Total)
        if err != nil {
            return err
        }

        for _, item := range order.Items {
            _, err = tx.Exec(ctx,
                "INSERT INTO order_items (order_id, product_id, qty) VALUES ($1, $2, $3)",
                order.ID, item.ProductID, item.Qty)
            if err != nil {
                return err
            }
        }
        return nil
    })
}
```

### Savepoints (Nested Transactions)

PostgreSQL does not support true nested transactions, but savepoints provide equivalent functionality:

```go
func (r *Repo) CreateWithFallback(ctx context.Context, tx pgx.Tx, data Data) error {
    // Create a savepoint before the risky operation
    _, err := tx.Exec(ctx, "SAVEPOINT my_savepoint")
    if err != nil {
        return err
    }

    _, err = tx.Exec(ctx,
        "INSERT INTO risky_table (data) VALUES ($1)", data.Value)
    if err != nil {
        // Roll back to savepoint, not the whole transaction
        tx.Exec(ctx, "ROLLBACK TO SAVEPOINT my_savepoint")
        // Attempt fallback
        _, fallbackErr := tx.Exec(ctx,
            "INSERT INTO fallback_table (data) VALUES ($1)", data.Value)
        return fallbackErr
    }

    _, err = tx.Exec(ctx, "RELEASE SAVEPOINT my_savepoint")
    return err
}
```

### Context-Aware Transactions

The repository should propagate context so long transactions can be cancelled:

```go
func (r *Repo) LongRunningUpdate(ctx context.Context) error {
    tx, err := r.db.Begin(ctx)
    if err != nil {
        return err
    }
    defer tx.Rollback(ctx)

    rows, err := tx.Query(ctx, "SELECT id FROM large_table FOR UPDATE")
    if err != nil {
        return err
    }
    defer rows.Close()

    for rows.Next() {
        // Check context before each iteration
        if ctx.Err() != nil {
            return ctx.Err()
        }

        var id int
        rows.Scan(&id)
        tx.Exec(ctx, "UPDATE large_table SET processed = true WHERE id = $1", id)
    }

    return tx.Commit(ctx)
}
```

---

## 3. Repository Pattern

The repository pattern decouples the data layer from business logic by defining a storage interface. The application depends on the interface, not the concrete implementation.

### Repository Interface

```go
// internal/store/store.go
package store

import "context"

// UserStore is the interface for user storage operations.
// Business logic depends only on this interface.
type UserStore interface {
    GetUser(ctx context.Context, id int64) (*User, error)
    ListUsers(ctx context.Context, filter UserFilter) ([]User, error)
    CreateUser(ctx context.Context, params CreateUserParams) (*User, error)
    UpdateUser(ctx context.Context, id int64, params UpdateUserParams) (*User, error)
    DeleteUser(ctx context.Context, id int64) error
}

type UserFilter struct {
    Active *bool
    Search string
    Limit  int
    Cursor *Cursor
}

type CreateUserParams struct {
    Name  string
    Email string
}

type UpdateUserParams struct {
    Name  *string // pointer = optional (nil means "don't update")
    Email *string
}
```

### Concrete Implementation

```go
// internal/store/postgres/users.go
package postgres

type userStore struct {
    db *pgxpool.Pool
}

func NewUserStore(db *pgxpool.Pool) store.UserStore {
    return &userStore{db: db}
}

func (s *userStore) GetUser(ctx context.Context, id int64) (*store.User, error) {
    var u store.User
    err := s.db.QueryRow(ctx,
        "SELECT id, name, email, created_at FROM users WHERE id = $1", id,
    ).Scan(&u.ID, &u.Name, &u.Email, &u.CreatedAt)

    if errors.Is(err, pgx.ErrNoRows) {
        return nil, store.ErrNotFound
    }
    if err != nil {
        return nil, fmt.Errorf("getting user %d: %w", id, err)
    }
    return &u, nil
}
```

### Sentinel Errors

Define domain-level errors in the store package, not in the HTTP layer:

```go
// internal/store/errors.go
package store

import "errors"

var (
    ErrNotFound      = errors.New("not found")
    ErrAlreadyExists = errors.New("already exists")
    ErrInvalidInput  = errors.New("invalid input")
)
```

HTTP handlers translate store errors to HTTP status codes:

```go
func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    id, _ := strconv.ParseInt(r.PathValue("id"), 10, 64)
    user, err := h.store.GetUser(r.Context(), id)
    if err != nil {
        switch {
        case errors.Is(err, store.ErrNotFound):
            writeError(w, http.StatusNotFound, "USER_NOT_FOUND", "user not found")
        default:
            writeError(w, http.StatusInternalServerError, "INTERNAL", "internal error")
        }
        return
    }
    writeJSON(w, http.StatusOK, user)
}
```

---

## 4. Dependency Injection

Go uses constructor-based dependency injection — no reflection, no magic.

```go
// internal/handler/user.go
type UserHandler struct {
    store  store.UserStore
    logger *slog.Logger
}

func NewUserHandler(store store.UserStore, logger *slog.Logger) *UserHandler {
    return &UserHandler{store: store, logger: logger}
}

// cmd/api/main.go — wire everything together
func main() {
    // Infrastructure
    pool, err := postgres.NewPool(ctx, os.Getenv("DATABASE_URL"))
    if err != nil {
        log.Fatal(err)
    }
    defer pool.Close()

    // Stores (data layer)
    userStore := postgresstore.NewUserStore(pool)

    // Handlers (HTTP layer)
    logger := slog.Default()
    userHandler := handler.NewUserHandler(userStore, logger)

    // Routes
    mux := http.NewServeMux()
    mux.HandleFunc("GET /users/{id}", userHandler.GetUser)
    mux.HandleFunc("POST /users", userHandler.CreateUser)
}
```

This explicit wiring makes the dependency graph visible, testable, and avoids globals.

---

## 5. Mock Generation for Testing

Since business logic depends on the `UserStore` interface, tests can substitute a mock.

### Manual Mock

```go
// internal/store/mock/users.go
type MockUserStore struct {
    GetUserFn    func(ctx context.Context, id int64) (*store.User, error)
    CreateUserFn func(ctx context.Context, params store.CreateUserParams) (*store.User, error)
}

func (m *MockUserStore) GetUser(ctx context.Context, id int64) (*store.User, error) {
    return m.GetUserFn(ctx, id)
}

func (m *MockUserStore) CreateUser(ctx context.Context, params store.CreateUserParams) (*store.User, error) {
    return m.CreateUserFn(ctx, params)
}
```

### Using mockery (Code Generation)

```bash
# Install
go install github.com/vektra/mockery/v2@latest

# Generate mocks for all interfaces in store package
mockery --dir=internal/store --all --output=internal/store/mocks
```

```go
// In tests, use the generated mock
func TestGetUser(t *testing.T) {
    mockStore := &mocks.UserStore{}
    mockStore.On("GetUser", mock.Anything, int64(1)).
        Return(&store.User{ID: 1, Name: "Alice"}, nil)

    handler := NewUserHandler(mockStore, slog.Default())
    req := httptest.NewRequest("GET", "/users/1", nil)
    req.SetPathValue("id", "1")
    rec := httptest.NewRecorder()

    handler.GetUser(rec, req)

    assert.Equal(t, http.StatusOK, rec.Code)
    mockStore.AssertExpectations(t)
}
```
