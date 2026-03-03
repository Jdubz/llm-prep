# 02 – Synchronization and Context

This file assumes you have read `01-goroutines-and-channels.md`. It covers the `sync` package primitives and the `context` package for managing goroutine lifecycles.

---

## Quick Decision: Channel vs Mutex vs Atomic

```
What are you doing?
  |
  +--> Transferring ownership of data between goroutines --> Channel
  |
  +--> Protecting a shared data structure --> Mutex (or RWMutex for read-heavy)
  |
  +--> Incrementing a counter / setting a flag --> atomic (sync/atomic)
  |
  +--> Coordinating N goroutines to finish --> sync.WaitGroup
  |
  +--> Running initialization exactly once --> sync.Once
  |
  +--> Propagating cancellation / deadlines --> context.Context
```

---

## 1. The sync Package

Channels are not always the right tool. Sometimes shared memory with synchronization primitives is simpler and faster.

### sync.WaitGroup

Wait for a group of goroutines to finish:

```go
var wg sync.WaitGroup

for i := 0; i < 10; i++ {
    wg.Add(1)
    go func(id int) {
        defer wg.Done()
        process(id)
    }(i)
}

wg.Wait() // blocks until all 10 goroutines call Done()
```

**TS equivalent:** `await Promise.all([...promises])`

Rules:
- Call `Add()` before launching the goroutine, not inside it.
- `Done()` decrements the counter. Use `defer` to ensure it is called.
- `Wait()` blocks until the counter reaches zero.

### sync.Mutex and sync.RWMutex

Protect shared state:

```go
type SafeCounter struct {
    mu    sync.Mutex
    count int
}

func (c *SafeCounter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c *SafeCounter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.count
}
```

`sync.RWMutex` allows multiple concurrent readers:

```go
type Cache struct {
    mu   sync.RWMutex
    data map[string]string
}

func (c *Cache) Get(key string) (string, bool) {
    c.mu.RLock()         // multiple goroutines can read simultaneously
    defer c.mu.RUnlock()
    val, ok := c.data[key]
    return val, ok
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()          // exclusive access for writing
    defer c.mu.Unlock()
    c.data[key] = value
}
```

### sync.Once

Execute something exactly once, safely across goroutines:

```go
var (
    instance *Database
    once     sync.Once
)

func GetDatabase() *Database {
    once.Do(func() {
        instance = connectToDatabase()
    })
    return instance
}
```

This is Go's singleton pattern. The function passed to `Do` runs exactly once, even if called from many goroutines concurrently.

### sync.Map

A concurrent-safe map. Use it when:
- Keys are stable (written once, read many times).
- Multiple goroutines read/write disjoint key sets.

```go
var cache sync.Map

cache.Store("key", "value")
val, ok := cache.Load("key")
cache.Delete("key")
cache.Range(func(key, value any) bool {
    fmt.Println(key, value)
    return true // continue iteration
})
```

For most cases, a regular `map` with `sync.RWMutex` is simpler and often faster. `sync.Map` shines in specific access patterns.

### sync.Pool

Reuse temporary objects to reduce GC pressure:

```go
var bufPool = sync.Pool{
    New: func() any {
        return new(bytes.Buffer)
    },
}

func process(data []byte) {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufPool.Put(buf)
    }()

    buf.Write(data)
    // use buf...
}
```

The pool may be cleared at any GC cycle. Do not rely on items persisting.

### sync Primitives Comparison

| Primitive | Purpose | Key Methods | Notes |
|-----------|---------|-------------|-------|
| `sync.Mutex` | Exclusive access | `Lock()`, `Unlock()` | Use `defer Unlock()` |
| `sync.RWMutex` | Read-heavy shared access | `RLock()`, `RUnlock()`, `Lock()`, `Unlock()` | Multiple readers OR one writer |
| `sync.WaitGroup` | Wait for N goroutines | `Add(n)`, `Done()`, `Wait()` | Call `Add` before `go func` |
| `sync.Once` | One-time init | `Do(func())` | Safe across goroutines |
| `sync.Map` | Concurrent map | `Store()`, `Load()`, `Delete()`, `Range()` | Prefer regular map + mutex usually |
| `sync.Pool` | Object reuse | `Get()`, `Put()` | Cleared at GC; reduce allocation |
| `sync.Cond` | Signal waiting goroutines | `Wait()`, `Signal()`, `Broadcast()` | Rarely needed; channels usually better |

---

## 2. sync/atomic Package

### Typed Wrappers (Go 1.19+)

```go
var counter atomic.Int64

counter.Add(1)
counter.Store(42)
val := counter.Load()
swapped := counter.CompareAndSwap(42, 100)
```

### Pre-1.19 API (still valid)

```go
var counter int64

atomic.AddInt64(&counter, 1)
atomic.StoreInt64(&counter, 42)
val := atomic.LoadInt64(&counter)
swapped := atomic.CompareAndSwapInt64(&counter, 42, 100)
```

### atomic.Value

Store and load any value atomically:

```go
var config atomic.Value // holds a *Config

// Writer
config.Store(&Config{Debug: true, Port: 8080})

// Reader (can be called from any goroutine)
cfg := config.Load().(*Config)
```

Useful for configuration hot-reloading where a single writer updates and multiple readers access.

**When to use atomics:**
- Simple counters, flags, and pointers.
- When a mutex is too heavy for a single variable.
- When you need lock-free data structures (rare in application code).

**When NOT to use atomics:**
- When you need to update multiple related variables consistently.
- When the logic is more complex than a single read-modify-write.
- When a mutex makes the code clearer.

### Performance Characteristics

- Mutex lock/unlock: ~10-20ns.
- Atomic operation: ~5-10ns.
- Unbuffered channels: ~50-100ns per operation (with goroutine parking/waking).
- Buffered channels (not full/empty): ~20-50ns per operation (no parking needed).

For raw throughput of simple counter updates, atomics beat mutexes beat channels. But channels provide safety guarantees and composability that atomics cannot.

---

## 3. context.Context

Context is Go's mechanism for cancellation, deadlines, and request-scoped values. Every long-running or I/O function should accept a `context.Context` as its first parameter.

### Why Context Exists

In Node, you might cancel a request by aborting the HTTP connection. But downstream operations (database queries, API calls) keep running. Go's context propagates cancellation through the entire call chain.

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context() // request context — cancelled when client disconnects

    user, err := getUser(ctx, userID)       // passes context to DB query
    if err != nil { ... }

    orders, err := getOrders(ctx, user.ID)  // passes context to another service
    if err != nil { ... }
}
```

If the client disconnects, `ctx` is cancelled, and both `getUser` and `getOrders` can return early.

### Creating Contexts

```go
// Root context (use in main or tests)
ctx := context.Background()

// Unknown/placeholder
ctx := context.TODO()

// Cancellation
ctx, cancel := context.WithCancel(parentCtx)
defer cancel() // ALWAYS defer cancel to avoid context leaks

// Timeout (cancels after duration)
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second)
defer cancel()

// Deadline (cancels at specific time)
ctx, cancel := context.WithDeadline(parentCtx, time.Now().Add(30*time.Second))
defer cancel()

// Values (use sparingly)
ctx = context.WithValue(parentCtx, requestIDKey, "abc-123")
```

### Context Tree

```
context.Background()
  |
  +-- context.WithCancel()
  |     |
  |     +-- context.WithTimeout(5s)
  |     |     |
  |     |     +-- DB query (auto-cancelled after 5s)
  |     |     +-- API call (auto-cancelled after 5s)
  |     |
  |     +-- context.WithValue(requestID)
  |           |
  |           +-- Logging middleware (reads requestID)
  |
  +-- context.WithDeadline(time)
        |
        +-- Long operation (cancelled at deadline)
```

Cancelling a parent cancels all children. Children cannot cancel parents.

### Context Cancellation

```go
func longOperation(ctx context.Context) error {
    for i := 0; i < 1000; i++ {
        select {
        case <-ctx.Done():
            return ctx.Err() // context.Canceled or context.DeadlineExceeded
        default:
            doWork(i)
        }
    }
    return nil
}
```

### Context Values: When to Use, When Not To

**Use context values for:**
- Request IDs, trace IDs, correlation IDs
- Authentication information (user identity)
- Anything that is request-scoped and crosses API boundaries

**Do NOT use context values for:**
- Function parameters (passing config, options)
- Optional dependencies
- Anything that changes the behavior of the function

```go
// GOOD — request-scoped metadata
type contextKey string
const requestIDKey contextKey = "requestID"

func withRequestID(ctx context.Context, id string) context.Context {
    return context.WithValue(ctx, requestIDKey, id)
}

func getRequestID(ctx context.Context) string {
    id, _ := ctx.Value(requestIDKey).(string)
    return id
}

// BAD — using context to pass function parameters
ctx = context.WithValue(ctx, "limit", 100) // Don't do this
```

Always use unexported typed keys to avoid collisions between packages.

### Context Propagation Rules

1. `context.Context` is always the **first parameter**, named `ctx`.
2. Do not store contexts in structs. Pass them through function calls.
3. Always call `cancel()` when you create a cancellable context (use `defer`).
4. Pass `context.Background()` only in `main()`, `init()`, and tests.
5. Pass `context.TODO()` when you are unsure which context to use (placeholder during refactoring).

### Context Quick Reference

```go
// Root (main, init, tests)
ctx := context.Background()

// Unknown/placeholder
ctx := context.TODO()

// Cancellation
ctx, cancel := context.WithCancel(parent)
defer cancel()

// Timeout
ctx, cancel := context.WithTimeout(parent, 5*time.Second)
defer cancel()

// Deadline
ctx, cancel := context.WithDeadline(parent, time.Now().Add(30*time.Second))
defer cancel()

// Value (use sparingly)
type ctxKey string
ctx = context.WithValue(parent, ctxKey("requestID"), "abc-123")
id := ctx.Value(ctxKey("requestID")).(string)

// Check cancellation
select {
case <-ctx.Done():
    return ctx.Err() // Canceled or DeadlineExceeded
default:
    // not cancelled yet
}
```

---

## 4. Graceful Shutdown Pattern

```go
func main() {
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    srv := &http.Server{Addr: ":8080", Handler: router()}

    // Start server in background
    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatal("server error:", err)
        }
    }()

    log.Println("server started on :8080")

    // Wait for interrupt signal
    <-ctx.Done()
    log.Println("shutting down gracefully...")

    // Give outstanding requests 10 seconds to complete
    shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    if err := srv.Shutdown(shutdownCtx); err != nil {
        log.Fatal("forced shutdown:", err)
    }

    log.Println("server stopped")
}
```

### Graceful Shutdown (Condensed Template)

```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()

go func() { srv.ListenAndServe() }()

<-ctx.Done()
shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
srv.Shutdown(shutdownCtx)
```

---

## 5. Common Goroutine Leak Causes

| Cause | Fix |
|-------|-----|
| Blocked send on unbuffered channel | Use buffered channel (size 1) |
| Blocked receive, no sender | Check `ctx.Done()` in select |
| Forgotten `cancel()` | Always `defer cancel()` |
| Missing `wg.Done()` | Always `defer wg.Done()` |
| Infinite loop without exit | Check `ctx.Done()` periodically |
| Orphaned goroutine after parent returns | Use context for lifecycle management |

---

## Related Reading

- **Context in HTTP services** — [Module 04: Handlers, Routing, and Middleware](../04-http-services/01-handlers-routing-and-middleware.md) shows how `context.Context` flows through HTTP handlers and middleware chains
- **Graceful shutdown pattern** — [Module 04: Advanced HTTP Patterns](../04-http-services/03-advanced-http-patterns.md), section 1 (Graceful Shutdown) uses `signal.NotifyContext` and `context.WithTimeout` from this file in a production server
- **Context-aware transactions** — [Module 05: Queries, Transactions, and Patterns](../05-data-storage/02-queries-transactions-and-patterns.md), section 2 (Context-Aware Transactions) shows context cancellation propagating into database operations
- **Testing with goroutine leak detection** — [Module 06: Benchmarking, Profiling, and Advanced Testing](../06-testing/03-benchmarking-profiling-and-advanced-testing.md), section 5 covers `goleak` for catching the leak patterns described in section 5 above
- **Advanced concurrency patterns** — [Advanced Concurrency Patterns](03-advanced-concurrency-patterns.md) builds on these primitives with fan-out/fan-in, worker pools, and the singleflight pattern
