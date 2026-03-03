# 02 – System Design and Advanced Topics

This file assumes you have read `01-interview-essentials.md`. It covers system design in Go, advanced gotchas, code review exercises, live coding challenges, and how to discuss Go in interviews.

---

## 1. System Design Template for Go

```
1. REQUIREMENTS
   - Functional: What does the system do?
   - Non-functional: Throughput, latency, consistency, availability

2. API DESIGN
   - HTTP/gRPC endpoints
   - Request/response types (Go structs)
   - Error responses (sentinel errors → HTTP status mapping)

3. DATA MODEL
   - Database schema
   - Go structs with json/db tags
   - sqlc queries or repository interfaces

4. ARCHITECTURE
   - Service boundaries
   - Goroutine model (worker pools, fan-out/fan-in)
   - Channel usage (job queues, result streams)
   - Context propagation for cancellation

5. CONCURRENCY DESIGN
   - What is concurrent? (requests, background jobs, timers)
   - Synchronization strategy (mutex vs channel vs atomic)
   - Backpressure (bounded channels, rate limiting)

6. OBSERVABILITY
   - Structured logging (slog)
   - Metrics (Prometheus counters/histograms)
   - Tracing (OpenTelemetry spans)
   - Health checks (liveness + readiness)

7. DEPLOYMENT
   - Dockerfile (multi-stage, distroless)
   - Kubernetes manifests (HPA, resource limits)
   - GOMAXPROCS / GOMEMLIMIT tuning
   - Graceful shutdown ordering
```

---

## 2. System Design: Concurrent Web Crawler

**Prompt:** "Design a concurrent web crawler in Go that respects rate limits and avoids re-crawling the same URL."

```go
type Crawler struct {
    client      *http.Client
    visited     sync.Map              // Tracks visited URLs
    limiter     *rate.Limiter         // Rate limiting
    maxDepth    int
    concurrency int
}

type CrawlResult struct {
    URL    string
    Title  string
    Links  []string
    Depth  int
    Error  error
}

func (c *Crawler) Crawl(ctx context.Context, seeds []string) <-chan CrawlResult {
    results := make(chan CrawlResult, 100)
    jobs := make(chan crawlJob, 100)

    // Seed the jobs
    go func() {
        for _, url := range seeds {
            jobs <- crawlJob{url: url, depth: 0}
        }
    }()

    // Worker pool
    var wg sync.WaitGroup
    for i := 0; i < c.concurrency; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case job, ok := <-jobs:
                    if !ok {
                        return
                    }
                    c.processJob(ctx, job, jobs, results)
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

func (c *Crawler) processJob(ctx context.Context, job crawlJob, jobs chan<- crawlJob, results chan<- CrawlResult) {
    // Check visited (atomic test-and-set)
    if _, loaded := c.visited.LoadOrStore(job.url, true); loaded {
        return
    }

    // Rate limit
    if err := c.limiter.Wait(ctx); err != nil {
        return
    }

    result := c.fetchAndParse(ctx, job)
    results <- result

    if result.Error == nil && job.depth < c.maxDepth {
        for _, link := range result.Links {
            select {
            case jobs <- crawlJob{url: link, depth: job.depth + 1}:
            default: // Job queue full, skip
            }
        }
    }
}
```

**Go-specific considerations to discuss:**
- `sync.Map` for concurrent URL deduplication (write-once read-many pattern)
- `rate.Limiter` from `golang.org/x/time/rate` for per-domain rate limiting
- Worker pool pattern with bounded concurrency
- Context for cancellation and timeout
- Channels for result streaming (caller can process as results arrive)

---

## 3. System Design: Pub/Sub Message Broker

**Key Go-specific decisions:**
- Use channels for in-process pub/sub, gRPC streams for cross-process
- Protect subscriber maps with `sync.RWMutex`
- Use buffered channels per subscriber to handle slow consumers (with `select`/`default` to drop when full)
- For shutdown: close subscriber channels and drain in-flight messages

---

## 4. System Design: Distributed Cache

**Key Go-specific decisions:**
- Consistent hashing for key distribution
- `sync.Map` or sharded maps (map per hash bucket with per-shard `sync.RWMutex`) for concurrent access
- Use `singleflight` to deduplicate concurrent cache misses for the same key (prevents thundering herd)
- gRPC for inter-node communication
- TTL enforcement via a background goroutine with a `time.Ticker`

---

## 5. Code Review Exercises

### Exercise 1: Spot the Goroutine Leak

```go
func ProcessItems(items []Item) []Result {
    results := make([]Result, len(items))
    for i, item := range items {
        go func(idx int, it Item) {
            results[idx] = process(it)  // No synchronization!
        }(i, item)
    }
    return results  // Returns before goroutines finish
}
```

**Issues:**
1. No `sync.WaitGroup` — function returns before goroutines complete
2. Data race on `results` slice (goroutines write while main reads)
3. Goroutines may leak if `process` blocks indefinitely

### Exercise 2: Identify the Data Race

```go
type Cache struct {
    data map[string]string
}

func (c *Cache) Get(key string) string {
    return c.data[key]  // Read without lock
}

func (c *Cache) Set(key, value string) {
    c.data[key] = value  // Write without lock
}
```

**Fix:** Add `sync.RWMutex` — `RLock` for reads, `Lock` for writes.

### Exercise 3: Find the Performance Issue

```go
func BuildReport(users []User) string {
    report := ""
    for _, u := range users {
        report += fmt.Sprintf("User: %s, Email: %s\n", u.Name, u.Email)
    }
    return report
}
```

**Issue:** String concatenation in a loop creates O(n²) allocations. Use `strings.Builder`:

```go
var b strings.Builder
for _, u := range users {
    fmt.Fprintf(&b, "User: %s, Email: %s\n", u.Name, u.Email)
}
return b.String()
```

### Exercise 4: Suggest Idiomatic Improvements

```go
func GetUser(id int) (*User, error) {
    if id <= 0 { return nil, errors.New("Invalid ID") }
    user := new(User)
    err := db.QueryRow("SELECT name FROM users WHERE id = ?", id).Scan(&user.Name)
    if err != nil { return nil, err }
    return user, nil
}
```

**Issues:**
- Missing `context.Context` parameter
- Error message should be lowercase (`"invalid ID"`)
- Errors not wrapped (`fmt.Errorf("getting user %d: %w", id, err)`)
- Should check `sql.ErrNoRows` for not-found
- Prefer `&User{}` over `new(User)`

### Exercise 5: Spot the Context Mistake

```go
go func() {
    s.notifier.Send(ctx, order)  // BUG: uses request context
}()
```

**Issue:** The goroutine uses the request context, which is cancelled when the HTTP request completes. Use `context.WithoutCancel(ctx)` (Go 1.21+) or `context.Background()` for fire-and-forget operations.

---

## 6. Live Coding Challenges

### Challenge 1: Concurrent Worker Pool from Scratch

Build a generic worker pool that:
- Accepts jobs via a channel
- Processes with N concurrent workers
- Returns results via a channel
- Supports cancellation via context
- Handles panics in worker goroutines

**Key points the interviewer looks for:**
- Proper use of `sync.WaitGroup`
- Channel direction in function signatures (`<-chan` vs `chan<-`)
- Closing the results channel after all workers finish
- Panic recovery with `defer func() { if r := recover(); r != nil { ... } }()`

### Challenge 2: Circuit Breaker

Build a circuit breaker with three states: closed (normal), open (failing), half-open (testing recovery).

```go
type CircuitBreaker struct {
    mu           sync.Mutex
    state        State
    failures     int
    successes    int
    threshold    int
    resetTimeout time.Duration
    lastFailure  time.Time
}

func (cb *CircuitBreaker) Execute(fn func() error) error {
    cb.mu.Lock()
    state := cb.state

    if state == Open {
        if time.Since(cb.lastFailure) > cb.resetTimeout {
            cb.state = HalfOpen
            state = HalfOpen
        } else {
            cb.mu.Unlock()
            return ErrCircuitOpen
        }
    }
    cb.mu.Unlock()

    err := fn()

    cb.mu.Lock()
    defer cb.mu.Unlock()

    if err != nil {
        cb.failures++
        cb.lastFailure = time.Now()
        if cb.failures >= cb.threshold {
            cb.state = Open
        }
        return err
    }

    if state == HalfOpen {
        cb.successes++
        if cb.successes >= cb.threshold {
            cb.state = Closed
            cb.failures = 0
            cb.successes = 0
        }
    } else {
        cb.failures = 0
    }

    return nil
}
```

### Challenge 3: HTTP Load Balancer

Build a simple round-robin HTTP load balancer.

**Key components:**
- Backend pool with health tracking
- Round-robin selection with `atomic.AddUint64`
- `httputil.ReverseProxy` for proxying
- Health check goroutine that pings backends periodically
- Graceful removal of unhealthy backends

### Challenge 4: Cursor Pagination with sqlc

```sql
-- name: ListUsersAfterCursor :many
SELECT id, name, email, created_at
FROM users
WHERE (created_at, id) < (@cursor_time, @cursor_id)
ORDER BY created_at DESC, id DESC
LIMIT @page_size;
```

**Key points:**
- Cursor encodes `(created_at, id)` tuple (base64 encoded)
- Composite ordering prevents skipping rows with same timestamp
- Return `next_cursor` in response for the client to fetch next page
- Explain why cursor pagination is better than offset pagination at scale

---

## 7. Advanced Gotchas

### Loop Variable Capture (Fixed in Go 1.22)

```go
// BEFORE Go 1.22: BUG
funcs := make([]func(), 5)
for i := 0; i < 5; i++ {
    funcs[i] = func() { fmt.Println(i) }  // All print 5!
}

// Old fix: shadow the variable
for i := 0; i < 5; i++ {
    i := i  // Each closure gets its own copy
    funcs[i] = func() { fmt.Println(i) }
}

// Go 1.22+: Each iteration creates a new variable. Fixed automatically.
```

Mention that you know this was fixed in Go 1.22, but you understand why the fix was needed. Many older codebases still have the `i := i` shadow pattern.

### Slice Append Gotchas

```go
// Gotcha 1: Append may or may not modify the original
s1 := make([]int, 3, 5)  // len=3, cap=5
s2 := append(s1, 4)       // s2 uses same underlying array as s1
s2[0] = 99                 // ALSO modifies s1[0]!

// Gotcha 2: After reallocation, they diverge
s1 = []int{1, 2, 3}       // len=3, cap=3
s2 = append(s1, 4)         // New array allocated (cap exceeded)
s2[0] = 99                 // Does NOT modify s1[0]

// Safe pattern: use full slice expression to limit capacity
s1 = []int{1, 2, 3, 4, 5}
s2 = s1[1:3:3]            // len=2, cap=2 — forces new allocation on append
s3 := append(s2, 99)      // New array — does not affect s1
```

### Map Iteration Order

```go
m := map[string]int{"a": 1, "b": 2, "c": 3}

// Iteration order is DELIBERATELY randomized between runs
for k, v := range m {
    fmt.Println(k, v)  // Order varies
}

// For deterministic order:
keys := make([]string, 0, len(m))
for k := range m { keys = append(keys, k) }
slices.Sort(keys)
for _, k := range keys { fmt.Println(k, m[k]) }
```

### Nil Slice vs Empty Slice

```go
var s1 []int           // nil slice — nil, len=0, cap=0
s2 := []int{}          // empty slice — not nil, len=0, cap=0

fmt.Println(s1 == nil)  // true
fmt.Println(s2 == nil)  // false

// JSON encoding difference:
json.Marshal(s1)  // "null"
json.Marshal(s2)  // "[]"

// Gotcha: When returning from an API, prefer empty slice over nil
// to avoid "null" in JSON responses
```

### Method Set Rules

```go
type Counter struct{ n int }
func (c Counter) Value() int    { return c.n }  // Value receiver
func (c *Counter) Increment()   { c.n++ }       // Pointer receiver

// Method set of Counter (value):      { Value }
// Method set of *Counter (pointer):   { Value, Increment }

type Incrementer interface { Increment() }

var c Counter
var _ Incrementer = c   // Compile error: Counter does not implement Incrementer
var _ Incrementer = &c  // OK: *Counter implements Incrementer
```

When storing a value type in an interface and wondering why a pointer method is unavailable — this is the reason.

### Compile-Time Interface Satisfaction Check

```go
// Verify at compile time — zero runtime cost
var _ http.Handler = (*MyHandler)(nil)
var _ io.ReadWriteCloser = (*MyBuffer)(nil)
var _ fmt.Stringer = (*Status)(nil)
var _ error = (*AppError)(nil)
```

### The `singleflight` Pattern

Prevents duplicate work for concurrent identical requests — essential for cache stampede prevention:

```go
import "golang.org/x/sync/singleflight"

var group singleflight.Group

func GetUser(ctx context.Context, id string) (*User, error) {
    // If 100 goroutines request the same user simultaneously,
    // only one database query executes. The other 99 wait and share the result.
    result, err, shared := group.Do(id, func() (interface{}, error) {
        return db.QueryUser(ctx, id)
    })
    if err != nil {
        return nil, err
    }
    _ = shared // true if the result was shared with other callers
    return result.(*User), nil
}
```

---

## 8. Staff-Level Discussions

### Choosing Go vs Other Languages

**When Go is the right choice:**
- Network services (HTTP APIs, gRPC services, proxies)
- CLI tools (single binary distribution, fast startup)
- Infrastructure tooling (Kubernetes, Docker, Terraform are all Go)
- High-concurrency workloads where goroutines shine
- Teams that value simplicity and readability over expressiveness

**When Go is not the best choice:**
- Heavy data processing/ML (Python ecosystem is unmatched)
- GUI applications (Go's GUI story is weak)
- Rapid prototyping where TypeScript/Python iteration speed wins
- Projects requiring advanced type system features (Rust, Haskell)

**How to frame this in an interview:** "I would choose Go for this service because it is a network-bound API that needs to handle thousands of concurrent connections. Go's goroutine model gives us lightweight concurrency without callback complexity. The single binary deployment simplifies our Docker images and CI pipeline. If this were a data pipeline with heavy numerical computation, I would lean toward Python. If we needed memory safety guarantees without a garbage collector, Rust."

### Go in Microservices Architecture

**Advantages:**
- Small, fast Docker images (10–20MB distroless)
- Fast startup (milliseconds, not seconds)
- Low memory footprint per service
- Strong stdlib for HTTP/gRPC
- Excellent cross-compilation for multi-arch deployments

**Challenges:**
- No shared runtime like JVM for polyglot services
- Less mature ORM story than Java/TypeScript
- Error handling verbosity in handler code
- Generics are still young compared to Java/C# generics

### Go's Module Ecosystem

Key talking points:
- `pkg.go.dev` as the discovery and documentation platform
- Module proxy (`proxy.golang.org`) for reliable dependency fetching
- Checksum database (`sum.golang.org`) for supply chain security
- Minimum version selection (MVS) — Go's unique approach to dependency resolution
- The "fewer, larger" library philosophy vs npm's "many small packages"

---

## 9. "Why Go" Narratives

### For Companies Already Using Go

"I am drawn to Go because of its emphasis on simplicity and maintainability. In my TypeScript experience, I have seen codebases become difficult to maintain as they grow — complex type hierarchies, deeply nested generics, and heavyweight frameworks. Go's philosophy of keeping things simple and explicit resonates with how I think about building systems that teams can maintain over years. `gofmt`, explicit error handling, and minimal language surface area mean less time debating style and more time solving problems."

### For Companies Transitioning to Go

"I see Go as a natural evolution for teams building backend services. Coming from TypeScript, I appreciate that Go addresses several pain points I have experienced: deployment complexity (single binary vs node_modules), runtime performance (compiled vs interpreted), and concurrency (goroutines vs async/await callback chains). For production backend services that need to handle high concurrency with low latency, Go is the better tool."

### For Infrastructure Companies

"The infrastructure ecosystem has standardized on Go — Kubernetes, Docker, Terraform, Prometheus, Grafana, etcd. This is not accidental. Go's static binary compilation means tools can be distributed without runtime dependencies. Its concurrency model handles the parallelism that infrastructure tools need. Its fast compilation enables quick iteration."

### Common Follow-Up: "What Do You Miss from TypeScript?"

Be honest. Good answers:
- "Union types and discriminated unions — Go's error handling is explicit but verbose"
- "The npm ecosystem density — Go's library ecosystem is smaller but more curated"
- "Generics expressiveness — TypeScript's mapped types and conditional types are more powerful"
- "Hot reload during development — Go requires recompilation (though it is fast)"

### Common Follow-Up: "What Do You Prefer About Go?"

- "The simplicity — there is usually one obvious way to do things"
- "Single binary deployment — no runtime, no dependencies, no node_modules"
- "Built-in concurrency primitives that are first-class, not bolted on"
- "The standard library is genuinely good — I rarely need third-party packages for basic HTTP, JSON, testing"
- "gofmt ending all style debates"
- "Compilation speed — the feedback loop is nearly instant"
- "The tooling: go vet, go test -race, pprof, all built in"
