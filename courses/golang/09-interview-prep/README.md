# Module 09: Interview Prep

## What Go Interviews Actually Test

Go interviews are different from TypeScript interviews. Nobody will ask you to implement a red-black tree or reverse a linked list in Go (those are language-agnostic algorithm questions). Go interviews test three things:

1. **Concurrency reasoning** — Can you think about goroutines, channels, and race conditions?
2. **Idiomatic design** — Do you write Go like Go, or like Java/TypeScript translated into Go syntax?
3. **Production engineering** — Can you build, deploy, and operate Go services?

This module covers all three with concrete questions, puzzles, and exercises.

---

## Common Go Interview Questions

### Q1: What is a goroutine leak, and how do you prevent it?

A goroutine leak occurs when a goroutine is started but never terminates. Common causes: blocking on a channel with no sender/receiver, infinite loops, waiting on a context never cancelled.

```go
// LEAK: goroutine blocks forever if nobody reads from ch
func leak() {
    ch := make(chan int)
    go func() { ch <- expensiveWork() }()  // Blocks forever
}

// FIX: buffered channel + context
func noLeak(ctx context.Context) (int, error) {
    ch := make(chan int, 1)
    go func() { ch <- expensiveWork() }()
    select {
    case result := <-ch:
        return result, nil
    case <-ctx.Done():
        return 0, ctx.Err()
    }
}
```

**Prevention:** Ensure goroutines always have an exit path via context cancellation. Use `goleak` in tests.

### Q2: What causes a channel deadlock?

Deadlock occurs when all goroutines are asleep, waiting on channels that will never make progress.

```go
// DEADLOCK: main goroutine blocks, no other goroutine exists to send
func main() {
    ch := make(chan int)
    val := <-ch  // Fatal error: all goroutines are asleep - deadlock!
}

// DEADLOCK: Two goroutines waiting on each other
func main() {
    ch1 := make(chan int)
    ch2 := make(chan int)

    go func() {
        val := <-ch1   // Waits for ch1
        ch2 <- val     // Then sends to ch2
    }()

    val := <-ch2   // Waits for ch2 — but ch2 waits for ch1
    ch1 <- val     // Never reached
}
```

### Q3: Explain the nil interface gotcha.

An interface value in Go has two components: a type and a value. An interface is only `nil` when both are nil.

```go
type MyError struct{ msg string }
func (e *MyError) Error() string { return e.msg }

func mayFail() error {
    var err *MyError  // nil pointer of type *MyError
    // ... some logic that doesn't set err ...
    return err  // Returns non-nil interface! (type=*MyError, value=nil)
}

func main() {
    err := mayFail()
    if err != nil {
        // This EXECUTES even though err holds a nil pointer
        fmt.Println("error:", err)  // Panics: nil pointer dereference
    }
}

// FIX: Return the interface type explicitly
func mayFail() error {
    var err *MyError
    // ...
    if err != nil {
        return err
    }
    return nil  // Returns true nil interface
}
```

### Q4: How do slices work internally?

A slice is a three-word struct: pointer to underlying array, length, and capacity. Multiple slices can share the same underlying array.

```go
s1 := []int{1, 2, 3, 4, 5}
s2 := s1[1:3]   // s2 = [2, 3], shares s1's underlying array
s2[0] = 99      // Modifies s1 too! s1 = [1, 99, 3, 4, 5]

// append may or may not create a new array
s3 := append(s2, 10)  // If cap allows, modifies s1's array
                        // If cap exceeded, allocates new array
```

### Q5: Why can you not safely read and write to a map concurrently?

Maps in Go are not goroutine-safe. Concurrent read+write or write+write causes a runtime panic (not just a data race — a hard crash).

```go
// CRASH: concurrent map writes
m := make(map[string]int)
go func() { m["a"] = 1 }()
go func() { m["b"] = 2 }()  // fatal error: concurrent map writes

// FIX 1: sync.Mutex
var mu sync.Mutex
mu.Lock()
m["a"] = 1
mu.Unlock()

// FIX 2: sync.Map (for specific use cases)
var sm sync.Map
sm.Store("a", 1)
val, ok := sm.Load("a")

// FIX 3: Channel-based access (single owner)
```

### Q6: What is the order of deferred function calls?

LIFO (last-in, first-out). Arguments are evaluated at defer time, not execution time:

```go
func example() {
    defer fmt.Println("first")   // Executes third
    defer fmt.Println("second")  // Executes second
    defer fmt.Println("third")   // Executes first
    // Output: third, second, first
}

x := 0
defer fmt.Println(x)           // Prints 0 — evaluated at defer time
defer func() { fmt.Println(x) }()  // Prints 1 — closure captures variable
x = 1
```

### Q7: How do `init` functions work?

They run before `main()` in dependency order: package-level variables first, then `init()` functions in source file order. Imported packages initialize before the importing package. Use sparingly — they cannot return errors and make testing difficult.

### Q8: What is Go's error handling philosophy?

Errors are values, returned not thrown. Check explicitly at every call site:

```go
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doing something: %w", err)
}
```

"Errors are part of your API. They deserve the same design attention as your success paths."

### Q9: When do you use `context.Context`?

Every function that does I/O or could block should accept a context as its first parameter. It carries deadlines, cancellation signals, and request-scoped values. Never store context in a struct — it is per-request.

```go
func GetUser(ctx context.Context, id int64) (*User, error)
```

### Q10: How do you tune the garbage collector?

`GOGC` controls GC frequency (default 100 = trigger GC when heap doubles). Lower values mean more frequent GC (less memory, more CPU). `GOMEMLIMIT` (Go 1.19+) sets a soft memory limit — GC becomes more aggressive as memory approaches this limit.

### Q11-Q20: Rapid-Fire

| # | Question | Key Answer |
|---|----------|-----------|
| 11 | Difference between `make` and `new`? | `make` initializes slices/maps/channels; `new` allocates zeroed memory and returns a pointer |
| 12 | What does `go vet` check? | Common mistakes: printf format mismatches, unreachable code, mutex copy, struct tag errors |
| 13 | How do goroutines differ from OS threads? | Goroutines are multiplexed onto OS threads by Go's scheduler; ~2KB initial stack vs ~1MB for threads |
| 14 | What is a race condition in Go? | Two goroutines access shared memory, at least one writes, without synchronization. Detected with `-race` flag |
| 15 | Explain `sync.WaitGroup`. | Counter-based synchronization. `Add(n)` before spawning, `Done()` in goroutine, `Wait()` blocks until counter is 0 |
| 16 | What is `select` used for? | Multiplexing channel operations. Blocks until one case is ready. `default` makes it non-blocking |
| 17 | Difference between buffered and unbuffered channels? | Unbuffered: sender blocks until receiver ready. Buffered: sender blocks only when buffer full |
| 18 | What is `sync.Once` for? | Guarantees a function executes exactly once, even across goroutines. Used for lazy initialization |
| 19 | How does Go handle method receivers? | Value receiver gets a copy; pointer receiver gets the original. Interfaces are satisfied by either, but only pointer receivers can modify state |
| 20 | What is the blank identifier `_`? | Discards a value. Used to ignore return values or to satisfy import/interface requirements |

---

## Concurrency Puzzles

### Puzzle 1: Detect the Deadlock

```go
func puzzle1() {
    ch := make(chan int, 1)
    ch <- 1

    go func() {
        val := <-ch
        ch <- val * 2
    }()

    ch <- 3        // What happens here?
    fmt.Println(<-ch)
}
```

**Analysis:** The channel has capacity 1 and already has value 1. `ch <- 3` blocks because the buffer is full. The goroutine reads 1, then tries to send 2, but the main goroutine is blocked trying to send 3. **Deadlock.** Fix: increase buffer size or restructure the communication.

### Puzzle 2: Fix the Race Condition

```go
func puzzle2() {
    counter := 0
    var wg sync.WaitGroup

    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++  // DATA RACE
        }()
    }

    wg.Wait()
    fmt.Println(counter)  // Not reliably 1000
}
```

**Fix options:**

```go
// Option 1: sync.Mutex
var mu sync.Mutex
mu.Lock()
counter++
mu.Unlock()

// Option 2: atomic (best for simple counters)
var counter atomic.Int64
counter.Add(1)

// Option 3: Channel (collects results)
results := make(chan int, 1000)
// ... goroutines send to results
// main goroutine sums
```

### Puzzle 3: Implement a Worker Pool

```go
func WorkerPool(ctx context.Context, numWorkers int, jobs <-chan Job) <-chan Result {
    results := make(chan Result, numWorkers)

    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func(workerID int) {
            defer wg.Done()
            for {
                select {
                case job, ok := <-jobs:
                    if !ok {
                        return  // Channel closed, no more jobs
                    }
                    result := process(job)
                    select {
                    case results <- result:
                    case <-ctx.Done():
                        return
                    }
                case <-ctx.Done():
                    return
                }
            }
        }(i)
    }

    // Close results when all workers are done
    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}
```

### Puzzle 4: Implement a Rate Limiter

```go
type RateLimiter struct {
    tokens chan struct{}
    ticker *time.Ticker
}

func NewRateLimiter(rps int) *RateLimiter {
    rl := &RateLimiter{
        tokens: make(chan struct{}, rps),
        ticker: time.NewTicker(time.Second / time.Duration(rps)),
    }

    // Refill tokens
    go func() {
        for range rl.ticker.C {
            select {
            case rl.tokens <- struct{}{}:
            default: // Bucket full, discard token
            }
        }
    }()

    // Pre-fill
    for i := 0; i < rps; i++ {
        rl.tokens <- struct{}{}
    }

    return rl
}

func (rl *RateLimiter) Wait(ctx context.Context) error {
    select {
    case <-rl.tokens:
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

### Puzzle 5: Fan-Out/Fan-In with Error Handling

```go
func FanOutFanIn(ctx context.Context, urls []string) ([]Result, error) {
    type indexed struct {
        index  int
        result Result
        err    error
    }

    ch := make(chan indexed, len(urls))

    // Fan out
    for i, url := range urls {
        go func(idx int, u string) {
            result, err := fetch(ctx, u)
            ch <- indexed{index: idx, result: result, err: err}
        }(i, url)
    }

    // Fan in
    results := make([]Result, len(urls))
    var errs []error
    for range urls {
        item := <-ch
        if item.err != nil {
            errs = append(errs, fmt.Errorf("url %d: %w", item.index, item.err))
            continue
        }
        results[item.index] = item.result
    }

    if len(errs) > 0 {
        return results, errors.Join(errs...)
    }
    return results, nil
}
```

---

## System Design in Go

### Design: Concurrent Web Crawler

**Interviewer:** "Design a concurrent web crawler in Go that respects rate limits and avoids re-crawling the same URL."

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

    // Close results when done
    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}

func (c *Crawler) processJob(ctx context.Context, job crawlJob, jobs chan<- crawlJob, results chan<- CrawlResult) {
    // Check visited
    if _, loaded := c.visited.LoadOrStore(job.url, true); loaded {
        return
    }

    // Rate limit
    if err := c.limiter.Wait(ctx); err != nil {
        return
    }

    // Fetch and parse
    result := c.fetchAndParse(ctx, job)
    results <- result

    // Enqueue discovered links
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
- `sync.Map` for concurrent URL deduplication (good for write-once read-many)
- `rate.Limiter` from `golang.org/x/time/rate` for per-domain rate limiting
- Worker pool pattern with bounded concurrency
- Context for cancellation and timeout
- Channels for result streaming (caller can process as results arrive)

### Design: Pub/Sub Message Broker

**Key Go-specific decisions:** Use channels for in-process pub/sub, gRPC streams for cross-process. Protect subscriber maps with `sync.RWMutex`. Use buffered channels per subscriber to handle slow consumers (with `select`/`default` to drop or log when full). For shutdown, close subscriber channels and drain in-flight messages.

### Design: Distributed Cache

**Key Go-specific decisions:** Consistent hashing for key distribution. `sync.Map` or sharded maps (map per hash bucket with per-shard `sync.RWMutex`) for concurrent access. Use `singleflight` to deduplicate concurrent cache misses for the same key. gRPC for inter-node communication. TTL enforcement via a background goroutine with a `time.Ticker`.

---

## Code Review Exercises

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

**Issue:** String concatenation in a loop creates O(n^2) allocations. Use `strings.Builder`:

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

**Issues:** Missing `context.Context` parameter. Error message should be lowercase (`"invalid ID"`). Errors not wrapped (`fmt.Errorf("getting user %d: %w", id, err)`). Should check `sql.ErrNoRows` for not-found. Prefer `&User{}` over `new(User)`.

### Exercise 5: Spot the Context Mistake

```go
go func() {
    s.notifier.Send(ctx, order)  // BUG: uses request context
}()
```

**Issue:** The goroutine uses the request context, cancelled when the HTTP request completes. Use `context.WithoutCancel(ctx)` (Go 1.21+) or `context.Background()` for fire-and-forget operations.

---

## Live Coding Challenges

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

Build a simple round-robin HTTP load balancer:

**Key components:**
- Backend pool with health tracking
- Round-robin selection with `atomic.AddUint64`
- `httputil.ReverseProxy` for proxying
- Health check goroutine that pings backends periodically
- Graceful removal of unhealthy backends

### Challenge 4: Cursor Pagination with sqlc

Implement cursor-based pagination for a users endpoint:

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
