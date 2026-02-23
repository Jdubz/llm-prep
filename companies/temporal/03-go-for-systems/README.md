# Module 03: Go Patterns for Systems Engineering (Temporal Role)

## Why This Module Exists

You have 10+ years of TypeScript/Node.js. You think in async/await, Promises, event emitters, and `npm install`. Temporal's server is written in Go. Their interview will test whether you can write, read, and reason about production Go -- especially concurrency, error handling, database access, and gRPC.

This module is not a "Learn Go" tutorial. It assumes you have touched Go basics and focuses on the patterns that matter for this specific role. Every section draws a line from what you already know in TypeScript to what Temporal expects in Go.

---

## 1. The Go Mental Model (TS Engineer's Lens)

### Types: Structural but Stricter

TypeScript has structural typing: if the shape matches, it fits. Go has structural typing for interfaces too, but everything else is stricter. There is no `any`. There is no union type. There are no implicit conversions.

```typescript
// TypeScript -- structural, flexible
interface Logger {
  log(msg: string): void;
}

// Any object with a log method satisfies Logger
const myLogger: Logger = {
  log: (msg) => console.log(msg),
};
```

```go
// Go -- structural for interfaces, strict for everything else
type Logger interface {
    Log(msg string)
}

type ConsoleLogger struct{}

func (c ConsoleLogger) Log(msg string) {
    fmt.Println(msg)
}

// ConsoleLogger satisfies Logger implicitly. No "implements" keyword.
// But you cannot assign an int to a string. Ever.
```

Key differences from TypeScript:
- No classes. Structs + methods.
- No union types. Use interfaces or separate types.
- No `null` and `undefined`. Just `nil`, and only for pointers, slices, maps, channels, functions, and interfaces.
- No optional fields on structs. Every field has a zero value.

### Composition Over Inheritance (Embedding)

In TypeScript, you extend classes. In Go, you embed structs.

```typescript
class Animal {
  move() { return "moving"; }
}
class Dog extends Animal {
  bark() { return "woof"; }
}
const d = new Dog();
d.move(); // inherited
```

```go
type Animal struct{}

func (a Animal) Move() string { return "moving" }

type Dog struct {
    Animal // embedded -- Dog "inherits" Move()
}

func (d Dog) Bark() string { return "woof" }

// d := Dog{}
// d.Move() works -- promoted from embedded Animal
```

This is not inheritance. There is no polymorphism through embedding. The embedded type's methods are promoted to the outer struct, but `Dog` is not an `Animal` in terms of type identity. If a function accepts `Animal`, you cannot pass `Dog`.

### Pointers: When and Why

In TypeScript, objects are always passed by reference (well, by reference value). Primitives are passed by value. You never think about it.

In Go, everything is passed by value. Structs, arrays, even slices (the header). If you want a function to modify the original, you pass a pointer.

```go
// Value receiver -- gets a copy. Cannot modify the original.
func (u User) SetName(name string) {
    u.Name = name // modifies the copy, not the original
}

// Pointer receiver -- gets a reference. Can modify the original.
func (u *User) SetName(name string) {
    u.Name = name // modifies the original
}
```

**When to use pointer receivers:**
- The method needs to modify the receiver
- The struct is large and copying is expensive
- Consistency: if one method uses a pointer receiver, all should

**When to use value receivers:**
- The method does not modify the receiver
- The struct is small (a few fields)
- You want immutability guarantees

At Temporal, you will see pointer receivers on most service structs because they hold state (database connections, configuration, caches).

### Zero Values

Every type in Go has a meaningful default. This is unlike TypeScript where `let x: number` is `undefined` until assigned.

```go
var i int       // 0
var s string    // ""
var b bool      // false
var p *User     // nil
var sl []int    // nil (but len(sl) == 0, and append works)
var m map[string]int // nil (but reading returns zero value; writing panics)
```

The nil slice is useful: `append(nilSlice, 1)` works. The nil map is dangerous: `nilMap["key"] = 1` panics. Always initialize maps with `make(map[string]int)` or a literal.

---

## 2. Error Handling

### The `if err != nil` Pattern

In TypeScript, you throw and catch:

```typescript
try {
  const user = await getUser(id);
} catch (err) {
  console.error("failed to get user:", err);
}
```

In Go, errors are values returned from functions:

```go
user, err := getUser(id)
if err != nil {
    return fmt.Errorf("failed to get user %s: %w", id, err)
}
```

This is not accidental verbosity. It is a design decision. Every error is visible at the call site. You cannot accidentally forget to handle one (the compiler warns about unused variables). There is no invisible control flow.

### Error Wrapping with `%w`

The `%w` verb wraps an error so callers can unwrap and inspect the chain:

```go
func getUser(ctx context.Context, id string) (*User, error) {
    row := db.QueryRowContext(ctx, "SELECT * FROM users WHERE id = $1", id)
    var u User
    if err := row.Scan(&u.ID, &u.Name, &u.Email); err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, ErrUserNotFound
        }
        return nil, fmt.Errorf("scanning user %s: %w", id, err)
    }
    return &u, nil
}
```

### Sentinel Errors vs Custom Error Types

Sentinel errors are package-level variables:

```go
var (
    ErrNotFound    = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
)

// Check with errors.Is
if errors.Is(err, ErrNotFound) {
    // handle not found
}
```

Custom error types carry additional context:

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation error on %s: %s", e.Field, e.Message)
}

// Check with errors.As
var valErr *ValidationError
if errors.As(err, &valErr) {
    fmt.Println("bad field:", valErr.Field)
}
```

In TypeScript, you would `instanceof` check a custom error class. In Go, `errors.As` does the equivalent through the error chain.

### Error Handling in Concurrent Code

When multiple goroutines can produce errors, you need a strategy to collect and surface them. The `errgroup` package from `golang.org/x/sync` is the standard approach:

```go
import "golang.org/x/sync/errgroup"

func fetchAll(ctx context.Context, ids []string) ([]*User, error) {
    g, ctx := errgroup.WithContext(ctx)
    users := make([]*User, len(ids))

    for i, id := range ids {
        i, id := i, id // capture loop variables
        g.Go(func() error {
            u, err := getUser(ctx, id)
            if err != nil {
                return fmt.Errorf("fetching user %s: %w", id, err)
            }
            users[i] = u
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return users, nil
}
```

In TypeScript, this is `Promise.all` with error propagation. The `errgroup` cancels the context on the first error, so other goroutines can check `ctx.Err()` and bail early.

---

## 3. Packages and Modules

### Flat Package Structure

In TypeScript, you might have deep nesting:

```
src/
  modules/
    users/
      services/
        userService.ts
      repositories/
        userRepository.ts
      models/
        user.ts
```

In Go, flat is idiomatic. The Go standard library itself is mostly flat:

```
internal/
  user/
    user.go          // types, service, repository all here (for small domains)
    user_test.go
  billing/
    billing.go
    invoice.go
    billing_test.go
```

A Go package is a directory. All `.go` files in a directory share the same package name. There is no `export` keyword; capitalized identifiers are exported, lowercase are unexported.

```go
package user

type User struct {     // exported -- visible outside the package
    ID   string
    Name string
    email string       // unexported -- lowercase
}

func New(id, name, email string) *User {  // exported constructor
    return &User{ID: id, Name: name, email: email}
}

func (u *User) validate() error {  // unexported method
    if u.Name == "" {
        return errors.New("name is required")
    }
    return nil
}
```

### Internal Packages

Go has a built-in encapsulation mechanism: the `internal/` directory. Anything under `internal/` can only be imported by code in the parent tree.

```
myservice/
  internal/
    persistence/    # only myservice/* can import this
    grpchandler/    # only myservice/* can import this
  cmd/
    server/
      main.go       # can import internal/*
```

Temporal's codebase uses `internal/` extensively. When navigating their code, most of the interesting logic is under `service/` and `internal/`.

---

## 4. Interfaces and Composition

### Implicit Satisfaction

In TypeScript, you explicitly declare `implements`. In Go, if a type has the right methods, it satisfies the interface. Period.

```go
type Store interface {
    Get(ctx context.Context, id string) (*User, error)
    Put(ctx context.Context, user *User) error
}

// SQLStore satisfies Store without declaring it
type SQLStore struct {
    db *sql.DB
}

func (s *SQLStore) Get(ctx context.Context, id string) (*User, error) { /* ... */ }
func (s *SQLStore) Put(ctx context.Context, user *User) error { /* ... */ }
```

### Small Interfaces

Go idiom: interfaces should be small. One or two methods. The standard library sets the example:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type ReadWriter interface {
    Reader
    Writer
}
```

The `io.Reader` interface is satisfied by files, HTTP response bodies, network connections, buffers, compressed streams, and hundreds of other types. This is the power of small interfaces.

### Accept Interfaces, Return Structs

This is the most important Go interface idiom:

```go
// Good -- accepts an interface, flexible for callers
func ProcessData(r io.Reader) error {
    data, err := io.ReadAll(r)
    // ...
}

// Good -- returns a concrete struct, clear for callers
func NewServer(store Store) *Server {
    return &Server{store: store}
}
```

In TypeScript, you might return an interface for abstraction. In Go, return the concrete type. Callers can assign it to any interface it satisfies.

### Mocking via Interfaces (Critical for Testing)

This is where interfaces shine in practice. You define your dependency as an interface, then swap it in tests:

```go
// Production code
type EmailSender interface {
    Send(ctx context.Context, to, subject, body string) error
}

type UserService struct {
    emails EmailSender
    store  Store
}

func (s *UserService) Register(ctx context.Context, u *User) error {
    if err := s.store.Put(ctx, u); err != nil {
        return fmt.Errorf("storing user: %w", err)
    }
    if err := s.emails.Send(ctx, u.Email, "Welcome", "Hello!"); err != nil {
        return fmt.Errorf("sending welcome email: %w", err)
    }
    return nil
}
```

```go
// Test code -- no mocking framework needed
type mockEmailSender struct {
    sent []string
}

func (m *mockEmailSender) Send(ctx context.Context, to, subject, body string) error {
    m.sent = append(m.sent, to)
    return nil
}

func TestRegister(t *testing.T) {
    emails := &mockEmailSender{}
    store := &mockStore{}
    svc := &UserService{emails: emails, store: store}

    err := svc.Register(context.Background(), &User{Email: "a@b.com"})
    if err != nil {
        t.Fatal(err)
    }
    if len(emails.sent) != 1 {
        t.Errorf("expected 1 email, got %d", len(emails.sent))
    }
}
```

In TypeScript, you might use Jest mocks or dependency injection containers. In Go, you define an interface and write a struct that implements it. No frameworks, no magic.

---

## 5. Concurrency (Critical for This Role)

Temporal is a distributed workflow engine. Its server coordinates goroutines, timers, channels, and contexts constantly. You need this deeply.

### Goroutines: Lightweight Threads

In Node.js, you have one thread. "Concurrency" means interleaving I/O callbacks on the event loop. You cannot run two CPU-bound operations simultaneously.

In Go, goroutines are real concurrent execution units. The Go scheduler multiplexes them onto OS threads. A goroutine starts with ~2 KB of stack, and you can launch millions.

```typescript
// TypeScript -- concurrent I/O, single-threaded
const results = await Promise.all([
  fetch("/api/users"),
  fetch("/api/orders"),
]);
```

```go
// Go -- truly concurrent, potentially parallel
func fetchBoth(ctx context.Context) (*Users, *Orders, error) {
    var (
        users  *Users
        orders *Orders
        mu     sync.Mutex
        errs   []error
    )

    var wg sync.WaitGroup
    wg.Add(2)

    go func() {
        defer wg.Done()
        u, err := fetchUsers(ctx)
        mu.Lock()
        defer mu.Unlock()
        if err != nil {
            errs = append(errs, err)
            return
        }
        users = u
    }()

    go func() {
        defer wg.Done()
        o, err := fetchOrders(ctx)
        mu.Lock()
        defer mu.Unlock()
        if err != nil {
            errs = append(errs, err)
            return
        }
        orders = o
    }()

    wg.Wait()

    if len(errs) > 0 {
        return nil, nil, errors.Join(errs...)
    }
    return users, orders, nil
}
```

### Channels: Typed Communication Pipes

In TypeScript, you might pass data between async operations with Promises or event emitters. In Go, channels are typed conduits.

```go
// Unbuffered channel -- sender blocks until receiver is ready
ch := make(chan int)

go func() {
    ch <- 42 // blocks until someone reads
}()

value := <-ch // blocks until someone writes
fmt.Println(value) // 42
```

```go
// Buffered channel -- sender blocks only when buffer is full
ch := make(chan int, 10)

ch <- 1 // does not block (buffer has space)
ch <- 2 // does not block
```

**Buffered vs Unbuffered:**
- Unbuffered: synchronization point. Both sides must be ready.
- Buffered: decouples sender and receiver. Useful for work queues, rate limiting.

### The `select` Statement: Multiplexing Channels

`select` is like a switch for channel operations. It blocks until one case is ready, then executes that case.

```go
func worker(ctx context.Context, jobs <-chan Job, results chan<- Result) {
    for {
        select {
        case job := <-jobs:
            result := process(job)
            results <- result
        case <-ctx.Done():
            return // context cancelled, shut down
        }
    }
}
```

The timeout pattern:

```go
select {
case result := <-ch:
    fmt.Println("got result:", result)
case <-time.After(5 * time.Second):
    fmt.Println("timed out")
}
```

In TypeScript, this is like `Promise.race`. But `select` is a language primitive, not a library function. It composes cleanly with context cancellation.

### The `sync` Package

| Go | TypeScript Equivalent | Purpose |
|----|----------------------|---------|
| `sync.Mutex` | No direct equivalent | Mutual exclusion for shared state |
| `sync.RWMutex` | No direct equivalent | Read-write lock (many readers, one writer) |
| `sync.WaitGroup` | `Promise.all` | Wait for N goroutines to complete |
| `sync.Once` | Module-level singleton pattern | Run something exactly once |
| `sync.Map` | `Map` with external locking | Concurrent-safe map (specialized use cases) |

```go
// WaitGroup -- the Go equivalent of Promise.all
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(n int) {
        defer wg.Done()
        fmt.Println(n)
    }(i)
}
wg.Wait() // blocks until all 10 goroutines call Done()
```

```go
// Mutex -- protecting shared state
type SafeCounter struct {
    mu sync.Mutex
    v  map[string]int
}

func (c *SafeCounter) Inc(key string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.v[key]++
}

func (c *SafeCounter) Value(key string) int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.v[key]
}
```

### `context.Context`: The Cancellation Backbone

In TypeScript, `AbortController` is the closest equivalent. But in Go, `context.Context` is everywhere. It is the first parameter of almost every function in production code.

```typescript
// TypeScript -- AbortController
const controller = new AbortController();
setTimeout(() => controller.abort(), 5000);

const response = await fetch("/api/data", {
  signal: controller.signal,
});
```

```go
// Go -- context with timeout
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel() // always defer cancel to release resources

user, err := getUser(ctx, id)
if err != nil {
    if errors.Is(err, context.DeadlineExceeded) {
        // timed out
    }
    return err
}
```

Context rules (you will be judged on these):
1. Always the first parameter: `func DoThing(ctx context.Context, ...)`
2. Never store in a struct field (pass it through the call chain)
3. Always `defer cancel()` when you create a derived context
4. Check `ctx.Err()` in long-running operations

### Common Concurrency Patterns

**Worker Pool:**

```go
func workerPool(ctx context.Context, numWorkers int, jobs <-chan Job) <-chan Result {
    results := make(chan Result, numWorkers)

    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case job, ok := <-jobs:
                    if !ok {
                        return // channel closed
                    }
                    results <- process(ctx, job)
                case <-ctx.Done():
                    return
                }
            }
        }()
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}
```

**Fan-Out / Fan-In:**

```go
func fanOutFanIn(ctx context.Context, inputs []string) ([]Result, error) {
    resultCh := make(chan Result, len(inputs))
    g, ctx := errgroup.WithContext(ctx)

    // Fan out
    for _, input := range inputs {
        input := input
        g.Go(func() error {
            result, err := process(ctx, input)
            if err != nil {
                return err
            }
            resultCh <- result
            return nil
        })
    }

    // Close channel when all goroutines complete
    go func() {
        g.Wait()
        close(resultCh)
    }()

    // Fan in
    var results []Result
    for r := range resultCh {
        results = append(results, r)
    }

    return results, g.Wait()
}
```

**Rate Limiting with a Ticker:**

```go
func rateLimited(ctx context.Context, requests []Request) {
    ticker := time.NewTicker(100 * time.Millisecond) // 10 per second
    defer ticker.Stop()

    for _, req := range requests {
        select {
        case <-ticker.C:
            go handleRequest(ctx, req)
        case <-ctx.Done():
            return
        }
    }
}
```

---

## 6. Database Patterns

### `database/sql` Basics

In TypeScript, you use Knex, Prisma, TypeORM, or raw `pg`. In Go, the `database/sql` package is the standard, and most Go developers use it directly or with thin wrappers like `sqlx` or `sqlc`.

```go
import (
    "database/sql"
    _ "github.com/lib/pq" // PostgreSQL driver (blank import for side effects)
)

func openDB(dsn string) (*sql.DB, error) {
    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, fmt.Errorf("opening database: %w", err)
    }

    // Configure connection pool
    db.SetMaxOpenConns(25)
    db.SetMaxIdleConns(5)
    db.SetConnMaxLifetime(5 * time.Minute)

    // Verify connectivity
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    if err := db.PingContext(ctx); err != nil {
        return nil, fmt.Errorf("pinging database: %w", err)
    }

    return db, nil
}
```

Note the blank import: `_ "github.com/lib/pq"`. The driver registers itself via `init()`. This is idiomatic but confusing if you come from TypeScript where imports are always explicit.

### Query Patterns

```go
// Single row
func getUser(ctx context.Context, db *sql.DB, id string) (*User, error) {
    var u User
    err := db.QueryRowContext(ctx,
        "SELECT id, name, email FROM users WHERE id = $1", id,
    ).Scan(&u.ID, &u.Name, &u.Email)

    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrNotFound
    }
    if err != nil {
        return nil, fmt.Errorf("querying user %s: %w", id, err)
    }
    return &u, nil
}

// Multiple rows
func listUsers(ctx context.Context, db *sql.DB) ([]*User, error) {
    rows, err := db.QueryContext(ctx, "SELECT id, name, email FROM users")
    if err != nil {
        return nil, fmt.Errorf("querying users: %w", err)
    }
    defer rows.Close() // always close rows

    var users []*User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
            return nil, fmt.Errorf("scanning user: %w", err)
        }
        users = append(users, &u)
    }

    if err := rows.Err(); err != nil {
        return nil, fmt.Errorf("iterating users: %w", err)
    }

    return users, nil
}
```

Critical gotcha: always call `rows.Close()` and always check `rows.Err()` after the loop. Leaking rows leaks database connections from the pool.

### Transaction Patterns

```go
func transferFunds(ctx context.Context, db *sql.DB, from, to string, amount int) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil {
        return fmt.Errorf("beginning transaction: %w", err)
    }
    // Defer rollback -- if Commit() is called first, Rollback() is a no-op
    defer tx.Rollback()

    // Debit
    result, err := tx.ExecContext(ctx,
        "UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1",
        amount, from,
    )
    if err != nil {
        return fmt.Errorf("debiting account: %w", err)
    }
    rows, _ := result.RowsAffected()
    if rows == 0 {
        return ErrInsufficientFunds
    }

    // Credit
    _, err = tx.ExecContext(ctx,
        "UPDATE accounts SET balance = balance + $1 WHERE id = $2",
        amount, to,
    )
    if err != nil {
        return fmt.Errorf("crediting account: %w", err)
    }

    return tx.Commit()
}
```

The `defer tx.Rollback()` pattern is idiomatic. If the function returns an error before `Commit()`, the transaction rolls back. If `Commit()` succeeds, the deferred `Rollback()` is a no-op.

### sqlc: Type-Safe SQL Generation

`sqlc` is popular in Go (and relevant to Temporal's ecosystem). You write SQL, it generates Go code:

```sql
-- queries.sql
-- name: GetUser :one
SELECT id, name, email FROM users WHERE id = $1;

-- name: ListUsers :many
SELECT id, name, email FROM users ORDER BY name;

-- name: CreateUser :exec
INSERT INTO users (id, name, email) VALUES ($1, $2, $3);
```

`sqlc` generates type-safe Go functions from these queries. No ORM overhead, no runtime reflection. This is the Go equivalent of Prisma's type safety but with raw SQL.

---

## 7. HTTP and gRPC

### `net/http` Basics

In TypeScript, you use Express or Fastify. In Go, the standard library's `net/http` is often sufficient.

```go
func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("GET /users/{id}", handleGetUser)
    mux.HandleFunc("POST /users", handleCreateUser)
    mux.HandleFunc("GET /health", handleHealth)

    server := &http.Server{
        Addr:         ":8080",
        Handler:      mux,
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    log.Fatal(server.ListenAndServe())
}

func handleGetUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id") // Go 1.22+ path parameters
    ctx := r.Context()

    user, err := store.GetUser(ctx, id)
    if err != nil {
        if errors.Is(err, ErrNotFound) {
            http.Error(w, "user not found", http.StatusNotFound)
            return
        }
        http.Error(w, "internal error", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}
```

### Middleware Pattern

```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
    })
}

func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        if token == "" {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return
        }
        // validate token, add user to context
        ctx := context.WithValue(r.Context(), userKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Chain middleware
handler := loggingMiddleware(authMiddleware(mux))
```

In TypeScript/Express, middleware is `app.use()`. In Go, it is function composition. Each middleware wraps the next handler.

### gRPC (Temporal's Communication Protocol)

Temporal uses gRPC for all inter-service communication. This is the most important protocol for this role.

**Protocol Buffer definition:**

```protobuf
syntax = "proto3";
package temporal.api.workflowservice.v1;

service WorkflowService {
    rpc StartWorkflowExecution(StartWorkflowExecutionRequest)
        returns (StartWorkflowExecutionResponse);

    rpc GetWorkflowExecutionHistory(GetWorkflowExecutionHistoryRequest)
        returns (GetWorkflowExecutionHistoryResponse);
}

message StartWorkflowExecutionRequest {
    string namespace = 1;
    string workflow_id = 2;
    temporal.api.common.v1.WorkflowType workflow_type = 3;
}
```

**Go gRPC server:**

```go
type workflowServer struct {
    workflowservice.UnimplementedWorkflowServiceServer
    store Store
}

func (s *workflowServer) StartWorkflowExecution(
    ctx context.Context,
    req *workflowservice.StartWorkflowExecutionRequest,
) (*workflowservice.StartWorkflowExecutionResponse, error) {
    if req.GetWorkflowId() == "" {
        return nil, status.Error(codes.InvalidArgument, "workflow_id is required")
    }

    runID, err := s.store.CreateWorkflow(ctx, req)
    if err != nil {
        return nil, status.Errorf(codes.Internal, "creating workflow: %v", err)
    }

    return &workflowservice.StartWorkflowExecutionResponse{
        RunId: runID,
    }, nil
}

func main() {
    lis, _ := net.Listen("tcp", ":7233")
    grpcServer := grpc.NewServer(
        grpc.UnaryInterceptor(loggingInterceptor),
    )
    workflowservice.RegisterWorkflowServiceServer(grpcServer, &workflowServer{
        store: newStore(),
    })
    grpcServer.Serve(lis)
}
```

**gRPC interceptors (middleware equivalent):**

```go
func loggingInterceptor(
    ctx context.Context,
    req interface{},
    info *grpc.UnaryServerInfo,
    handler grpc.UnaryHandler,
) (interface{}, error) {
    start := time.Now()
    resp, err := handler(ctx, req)
    log.Printf("gRPC %s %v err=%v", info.FullMethod, time.Since(start), err)
    return resp, err
}
```

**gRPC error codes:** gRPC uses structured status codes (`codes.NotFound`, `codes.Internal`, `codes.InvalidArgument`). In an interview, knowing these codes and when to use them shows you understand the protocol:

| gRPC Code | HTTP Equivalent | When to Use |
|-----------|----------------|-------------|
| `codes.OK` | 200 | Success |
| `codes.InvalidArgument` | 400 | Bad request data |
| `codes.NotFound` | 404 | Resource does not exist |
| `codes.AlreadyExists` | 409 | Duplicate resource |
| `codes.PermissionDenied` | 403 | Insufficient permissions |
| `codes.Internal` | 500 | Server error |
| `codes.Unavailable` | 503 | Service temporarily unavailable (retry) |
| `codes.DeadlineExceeded` | 504 | Timeout |

---

## 8. Putting It Together: What Temporal Tests For

In the interview, expect questions that combine these topics:

1. **"Design a worker pool that processes tasks from a database queue."** Tests: goroutines, channels, context cancellation, database access, error handling, graceful shutdown.

2. **"How would you handle a gRPC request that needs to coordinate multiple backend calls?"** Tests: context propagation, error handling in concurrent code, gRPC status codes, timeout management.

3. **"Walk me through how you would test this service."** Tests: interface-based mocking, table-driven tests, testing concurrent code, race detection.

4. **"What happens when this context is cancelled?"** Tests: context tree understanding, resource cleanup, goroutine lifecycle.

5. **"Explain how you would debug a goroutine leak in production."** Tests: pprof, goroutine dumps, understanding of goroutine lifecycles, common leak patterns (blocked channel operations, missing context cancellation).

These are not theoretical. Temporal's server faces all of these challenges daily. Their codebase has worker pools, context propagation through gRPC, interface-heavy testing, and sophisticated error handling. Be ready to discuss patterns, not just syntax.
