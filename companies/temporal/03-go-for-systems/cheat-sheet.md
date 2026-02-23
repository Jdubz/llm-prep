# Module 03 Cheat Sheet: Go Quick Reference for Temporal

## Type System: Go vs TypeScript

| Concept | TypeScript | Go |
|---------|-----------|-----|
| Variable | `let x: number = 5` | `x := 5` |
| Constant | `const x = 5` | `const x = 5` |
| Function | `function f(a: number): string` | `func f(a int) string` |
| Multiple returns | Return `{ value, error }` | `func f() (int, error)` |
| Closure | `(x) => x * 2` | `func(x int) int { return x * 2 }` |
| Object type | `interface User { name: string }` | `type User struct { Name string }` |
| Interface | `interface Reader { read(): void }` | `type Reader interface { Read() }` |
| Implements | `class X implements I` | Implicit |
| Inheritance | `class Dog extends Animal` | `type Dog struct { Animal }` |
| Generics | `function f<T>(x: T): T` | `func f[T any](x T) T` |
| Union type | `string \| number` | Interface or separate types |
| Optional field | `name?: string` | No equivalent (zero value) |
| Null/Undefined | `null`, `undefined` | `nil` (pointers, slices, maps, interfaces, channels, funcs only) |
| Array (fixed) | `[number, number]` (tuple) | `[2]int` |
| Array (dynamic) | `number[]` | `[]int` (slice) |
| Map | `Map<string, number>` | `map[string]int` |
| Enum | `enum Color { Red }` | `const ( Red = iota )` |
| Export | `export function F()` | `func F()` (uppercase) |
| Private | `private` / no export | `func f()` (lowercase) |
| String template | `` `Hello ${name}` `` | `fmt.Sprintf("Hello %s", name)` |
| Error handling | `try/catch` | `if err != nil` |
| Async | `async/await` | Goroutines + channels |

---

## Zero Values

| Type | Zero Value |
|------|-----------|
| `int`, `float64` | `0` |
| `string` | `""` |
| `bool` | `false` |
| `*T` (pointer) | `nil` |
| `[]T` (slice) | `nil` (len 0, append works) |
| `map[K]V` | `nil` (read ok, write panics) |
| `chan T` | `nil` (blocks forever) |
| `interface` | `nil` |
| `struct` | All fields zeroed |

---

## Concurrency Patterns

### Goroutine + WaitGroup (Promise.all equivalent)

```go
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(it Item) {
        defer wg.Done()
        process(it)
    }(item)
}
wg.Wait()
```

### errgroup (Promise.all with error propagation)

```go
g, ctx := errgroup.WithContext(ctx)
for _, item := range items {
    item := item
    g.Go(func() error {
        return process(ctx, item)
    })
}
if err := g.Wait(); err != nil {
    return err
}
```

### Channel (producer/consumer)

```go
ch := make(chan Job, 100) // buffered

// Producer
go func() {
    defer close(ch)
    for _, j := range jobs {
        ch <- j
    }
}()

// Consumer
for job := range ch { // loops until channel is closed
    handle(job)
}
```

### select (Promise.race equivalent)

```go
select {
case result := <-resultCh:
    // got result
case err := <-errCh:
    // got error
case <-ctx.Done():
    // cancelled or timed out
case <-time.After(5 * time.Second):
    // hard timeout
}
```

### Worker Pool

```go
func workerPool(ctx context.Context, n int, jobs <-chan Job) <-chan Result {
    results := make(chan Result, n)
    var wg sync.WaitGroup
    for i := 0; i < n; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case j, ok := <-jobs:
                    if !ok { return }
                    results <- process(ctx, j)
                case <-ctx.Done():
                    return
                }
            }
        }()
    }
    go func() { wg.Wait(); close(results) }()
    return results
}
```

### Mutex (protecting shared state)

```go
type SafeMap struct {
    mu sync.RWMutex
    m  map[string]int
}

func (s *SafeMap) Get(key string) int {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return s.m[key]
}

func (s *SafeMap) Set(key string, val int) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.m[key] = val
}
```

---

## Error Handling Patterns

### Basic wrapping

```go
result, err := doThing()
if err != nil {
    return fmt.Errorf("doing thing: %w", err)
}
```

### Sentinel errors

```go
var ErrNotFound = errors.New("not found")

if errors.Is(err, ErrNotFound) { /* handle */ }
```

### Custom error types

```go
type ValidationError struct {
    Field   string
    Message string
}
func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

var ve *ValidationError
if errors.As(err, &ve) {
    fmt.Println(ve.Field)
}
```

### Joining multiple errors (Go 1.20+)

```go
err := errors.Join(err1, err2, err3)
// errors.Is(err, err1) == true
// errors.Is(err, err2) == true
```

---

## `context.Context` Patterns

### Create and cancel

```go
// Timeout
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()

// Explicit cancel
ctx, cancel := context.WithCancel(ctx)
defer cancel()

// Deadline (absolute time)
ctx, cancel := context.WithDeadline(ctx, time.Now().Add(5*time.Second))
defer cancel()
```

### Check cancellation

```go
if err := ctx.Err(); err != nil {
    return err // context.Canceled or context.DeadlineExceeded
}
```

### Values (request-scoped metadata)

```go
type ctxKey string
const reqIDKey ctxKey = "requestID"

ctx = context.WithValue(ctx, reqIDKey, "abc-123")
id := ctx.Value(reqIDKey).(string)
```

### Rules

1. First parameter, named `ctx`
2. Never store in a struct
3. Always `defer cancel()`
4. Check `ctx.Err()` in loops

---

## `database/sql` Patterns

### Open connection

```go
db, err := sql.Open("postgres", dsn)
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(5)
db.SetConnMaxLifetime(5 * time.Minute)
```

### Query single row

```go
var u User
err := db.QueryRowContext(ctx, "SELECT id, name FROM users WHERE id = $1", id).
    Scan(&u.ID, &u.Name)
if errors.Is(err, sql.ErrNoRows) { /* not found */ }
```

### Query multiple rows

```go
rows, err := db.QueryContext(ctx, "SELECT id, name FROM users")
if err != nil { return err }
defer rows.Close()

var users []User
for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Name); err != nil { return err }
    users = append(users, u)
}
return rows.Err()
```

### Transaction

```go
tx, err := db.BeginTx(ctx, nil)
if err != nil { return err }
defer tx.Rollback() // no-op if committed

_, err = tx.ExecContext(ctx, "UPDATE ...", args...)
if err != nil { return err }

return tx.Commit()
```

---

## gRPC Setup Template

### Proto definition

```protobuf
syntax = "proto3";
package myservice.v1;

service MyService {
    rpc GetItem(GetItemRequest) returns (GetItemResponse);
}

message GetItemRequest { string id = 1; }
message GetItemResponse { string name = 1; }
```

### Server implementation

```go
type myServer struct {
    pb.UnimplementedMyServiceServer
    store Store
}

func (s *myServer) GetItem(ctx context.Context, req *pb.GetItemRequest) (*pb.GetItemResponse, error) {
    if req.GetId() == "" {
        return nil, status.Error(codes.InvalidArgument, "id required")
    }
    item, err := s.store.Get(ctx, req.GetId())
    if err != nil {
        if errors.Is(err, ErrNotFound) {
            return nil, status.Error(codes.NotFound, "item not found")
        }
        return nil, status.Errorf(codes.Internal, "internal: %v", err)
    }
    return &pb.GetItemResponse{Name: item.Name}, nil
}
```

### gRPC status codes

| Code | Use When |
|------|----------|
| `codes.InvalidArgument` | Bad input from client |
| `codes.NotFound` | Resource does not exist |
| `codes.AlreadyExists` | Duplicate creation |
| `codes.PermissionDenied` | Authorization failure |
| `codes.Internal` | Server bug |
| `codes.Unavailable` | Temporary failure (client should retry) |
| `codes.DeadlineExceeded` | Timeout |

---

## Testing Patterns

### Table-driven test

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name string
        a, b int
        want int
    }{
        {"positive", 1, 2, 3},
        {"zero", 0, 0, 0},
        {"negative", -1, 1, 0},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            if got := Add(tt.a, tt.b); got != tt.want {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.want)
            }
        })
    }
}
```

### Mock with interface

```go
type mockStore struct {
    getFunc func(ctx context.Context, id string) (*Item, error)
}
func (m *mockStore) Get(ctx context.Context, id string) (*Item, error) {
    return m.getFunc(ctx, id)
}
```

### HTTP test

```go
rec := httptest.NewRecorder()
req := httptest.NewRequest("GET", "/items/1", nil)
handler.ServeHTTP(rec, req)
if rec.Code != 200 { t.Errorf("status = %d", rec.Code) }
```

### Benchmark

```go
func BenchmarkProcess(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Process(testData)
    }
}
// Run: go test -bench=. -benchmem
```

### Race detector

```bash
go test -race ./...
```

---

## Go Idioms That Differ from TypeScript

| TS Instinct | Go Idiom |
|-------------|----------|
| Return `null` for "not found" | Return `(nil, ErrNotFound)` |
| Throw on bad input | Return `(zero, error)` |
| Use `class` with `constructor` | Use `struct` with `NewX()` function |
| `implements` keyword | Implicit (just have the methods) |
| `this.property` | Explicit receiver `(s *Server)` |
| `app.use(middleware)` | Wrap handlers: `middleware(handler)` |
| Jest mocks | Interface + mock struct |
| `npm install` | `go get` / `go mod tidy` |
| Deep import paths | Flat packages, `internal/` for encapsulation |
| `async/await` for concurrency | Goroutines + channels + `select` |
| `Promise.all` | `sync.WaitGroup` or `errgroup` |
| `Promise.race` | `select` |
| `AbortController` | `context.WithCancel` / `context.WithTimeout` |
| `try/finally` for cleanup | `defer` |
| Singleton pattern | `sync.Once` |

---

## Common Interview Questions

### Concurrency

1. "What is the difference between a goroutine and an OS thread?"
   - Goroutines are user-space, ~2 KB stack, managed by Go scheduler. OS threads are ~1 MB, managed by OS kernel. Go multiplexes many goroutines onto fewer OS threads.

2. "When would you use a channel vs a mutex?"
   - Channels for passing ownership of data between goroutines. Mutexes for protecting shared state that multiple goroutines read/write. Rule of thumb: "share memory by communicating" (channels), not "communicate by sharing memory" (mutexes).

3. "How do you prevent a goroutine leak?"
   - Always select on `ctx.Done()`. Always close channels when done sending. Use `defer` for cleanup. Profile with `pprof/goroutine` to detect leaks.

### Error Handling

4. "When do you use `errors.Is` vs `errors.As`?"
   - `errors.Is` checks if an error in the chain matches a specific value (sentinel). `errors.As` checks if an error in the chain matches a specific type and extracts it.

5. "Why does Go use explicit error returns instead of exceptions?"
   - Errors are visible at the call site. No hidden control flow. Compiler catches unhandled return values. Forces the developer to decide what to do with each error.

### Interfaces

6. "Why are Go interfaces implicit?"
   - Decouples definition from implementation. The consumer defines the interface, not the provider. Enables mocking without modifying production code. Avoids import cycles.

7. "What does 'accept interfaces, return structs' mean?"
   - Functions should accept interface parameters (flexibility for callers and tests) but return concrete types (clarity for callers). Let callers decide which interface the return type satisfies.

### Database and gRPC

8. "What happens if you forget to close `rows`?"
   - The database connection is not returned to the pool. Eventually the pool is exhausted and all queries block or fail.

9. "How does context propagate through gRPC?"
   - The client's deadline and cancellation are sent as gRPC metadata. The server receives a context with the client's deadline already set. If the client disconnects, the server's context is cancelled.

---

## Production Checklist

### Logging
- [ ] Use `log/slog` with JSON handler in production
- [ ] Include request ID, operation name in all log entries
- [ ] Log at appropriate levels (Info for normal, Warn for recoverable, Error for failures)

### Graceful Shutdown
- [ ] Handle `SIGTERM` and `SIGINT` with `signal.NotifyContext`
- [ ] Stop accepting new connections
- [ ] Drain in-flight requests with timeout
- [ ] Close database connections

### Health Checks
- [ ] Liveness endpoint (is the process alive)
- [ ] Readiness endpoint (checks database, dependencies)
- [ ] Separate port for health checks and pprof

### Observability
- [ ] pprof enabled on debug port
- [ ] Metrics exported (Prometheus or similar)
- [ ] Distributed tracing (OpenTelemetry)

### Database
- [ ] Connection pool configured (`MaxOpenConns`, `MaxIdleConns`, `ConnMaxLifetime`)
- [ ] Context-aware queries (`QueryContext`, `ExecContext`)
- [ ] `rows.Close()` deferred, `rows.Err()` checked
- [ ] Transactions use `defer tx.Rollback()` pattern

### Testing
- [ ] `go test -race ./...` passes
- [ ] Table-driven tests for business logic
- [ ] Interface mocks (no external mocking frameworks)
- [ ] Integration tests behind build tags
- [ ] Benchmarks for hot paths
