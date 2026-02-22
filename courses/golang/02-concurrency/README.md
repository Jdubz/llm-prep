# Module 02: Concurrency Primitives

## The Fundamental Mental Model Shift

In TypeScript/Node, concurrency is cooperative. One thread, one event loop. You write `async/await` and the runtime interleaves your I/O operations on a single thread. You cannot do two CPU-bound things at the same time.

In Go, concurrency is preemptive and parallel. Goroutines are multiplexed onto multiple OS threads. You can do two CPU-bound things at the same time. The scheduler can pause your goroutine at any point and run another.

```typescript
// TypeScript — single thread, cooperative concurrency
async function fetchBoth() {
  const [a, b] = await Promise.all([fetchA(), fetchB()]);
  return { a, b };
}
```

```go
// Go — multiple threads, preemptive concurrency
func fetchBoth(ctx context.Context) (A, B, error) {
    var a A
    var b B
    var errA, errB error

    var wg sync.WaitGroup
    wg.Add(2)

    go func() {
        defer wg.Done()
        a, errA = fetchA(ctx)
    }()

    go func() {
        defer wg.Done()
        b, errB = fetchB(ctx)
    }()

    wg.Wait()

    if errA != nil {
        return a, b, errA
    }
    return a, b, errB
}
```

---

## 1. Goroutines

### What They Are

A goroutine is a lightweight thread of execution managed by the Go runtime, not the OS. Starting a goroutine costs roughly 2-8 KB of stack memory. You can run millions of them.

```go
go doSomething()         // fire and forget
go func() {              // anonymous goroutine
    fmt.Println("hello")
}()
```

### Goroutine Lifecycle

A goroutine runs until:
1. Its function returns.
2. The program exits (`main` returns, and all goroutines are killed — no graceful shutdown by default).
3. A `runtime.Goexit()` is called (rare).

**Critical gotcha:** When `main()` returns, all goroutines are killed immediately. There is no equivalent of Node's "keep alive until the event loop is empty."

```go
func main() {
    go func() {
        time.Sleep(time.Second)
        fmt.Println("this may never print")
    }()
    // main returns immediately, goroutine is killed
}
```

### Goroutines vs Threads vs async/await

| Property | OS Thread | Goroutine | Node async |
|----------|-----------|-----------|-----------|
| Stack size | ~1 MB fixed | ~2-8 KB, grows dynamically | Shared heap |
| Creation cost | Expensive (syscall) | Cheap (~1 us) | Cheap (closure) |
| Scheduling | OS kernel | Go runtime | Event loop |
| Parallelism | Yes | Yes | No (single thread) |
| Communication | Shared memory + locks | Channels (preferred) or shared memory | Callbacks/promises |
| Count limit | ~thousands | ~millions | ~millions |

### Common Goroutine Mistakes

```go
// BUG: loop variable capture
for _, item := range items {
    go func() {
        process(item) // All goroutines see the SAME item (the last one)
    }()
}

// FIX (Go < 1.22): pass as argument
for _, item := range items {
    go func(it Item) {
        process(it)
    }(item)
}

// FIX (Go 1.22+): loop variables are per-iteration by default
for _, item := range items {
    go func() {
        process(item) // Safe in Go 1.22+
    }()
}
```

---

## 2. Channels

Channels are Go's primary mechanism for goroutine communication. The Go proverb: "Don't communicate by sharing memory; share memory by communicating."

### Unbuffered Channels

An unbuffered channel has no capacity. A send blocks until a receiver is ready. A receive blocks until a sender is ready. They synchronize goroutines.

```go
ch := make(chan string) // unbuffered

go func() {
    ch <- "hello" // blocks until someone receives
}()

msg := <-ch // blocks until someone sends
fmt.Println(msg) // "hello"
```

Think of an unbuffered channel as a handshake: both parties must be present.

### Buffered Channels

A buffered channel has capacity. Sends block only when the buffer is full. Receives block only when the buffer is empty.

```go
ch := make(chan string, 3) // buffer of 3

ch <- "a" // does not block
ch <- "b" // does not block
ch <- "c" // does not block
ch <- "d" // BLOCKS — buffer is full

msg := <-ch // "a" — FIFO order
```

Use buffered channels when:
- The producer and consumer run at different speeds.
- You want to decouple the sender from the receiver.
- You are implementing a semaphore (buffered channel as a concurrency limiter).

### Directional Channels

You can restrict a channel to send-only or receive-only:

```go
func producer(out chan<- string) { // can only send
    out <- "data"
}

func consumer(in <-chan string) { // can only receive
    msg := <-in
    fmt.Println(msg)
}
```

This is enforced at compile time. Use it in function signatures to communicate intent and prevent misuse.

### Closing Channels

Only the sender should close a channel. Closing signals "no more values."

```go
ch := make(chan int)

go func() {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch) // signal: no more values
}()

for v := range ch { // range exits when channel is closed
    fmt.Println(v)
}
```

Rules:
- Sending on a closed channel **panics**.
- Receiving from a closed channel returns the zero value immediately.
- Closing a nil channel **panics**.
- Closing an already-closed channel **panics**.
- You can check if a channel is closed: `val, ok := <-ch` — `ok` is `false` when closed and drained.

### Nil Channel Behavior

A nil channel blocks forever on both send and receive. This is useful in select statements for dynamically enabling/disabling cases:

```go
var ch1, ch2 <-chan int
ch1 = getChannel1()
// ch2 is nil — its select case will never fire

for {
    select {
    case v := <-ch1:
        fmt.Println("from ch1:", v)
    case v := <-ch2: // never selected because ch2 is nil
        fmt.Println("from ch2:", v)
    }
}
```

---

## 3. The select Statement

`select` multiplexes channel operations. It is Go's equivalent of `Promise.race` but more powerful.

### Basic Usage

```go
select {
case msg := <-ch1:
    fmt.Println("received from ch1:", msg)
case msg := <-ch2:
    fmt.Println("received from ch2:", msg)
case ch3 <- "hello":
    fmt.Println("sent to ch3")
}
```

If multiple cases are ready, one is chosen at random (uniformly). This prevents starvation.

### Timeout with time.After

```go
select {
case result := <-ch:
    fmt.Println("got result:", result)
case <-time.After(5 * time.Second):
    fmt.Println("timed out")
}
```

**TS equivalent:**

```typescript
const result = await Promise.race([
  fetchData(),
  new Promise((_, reject) => setTimeout(() => reject("timeout"), 5000)),
]);
```

### Default Case for Non-Blocking Operations

```go
select {
case msg := <-ch:
    fmt.Println("got:", msg)
default:
    fmt.Println("no message available, moving on")
}
```

The `default` case makes the select non-blocking. Without it, `select` blocks until a case is ready.

### Done Channel Pattern

```go
func worker(done <-chan struct{}, tasks <-chan Task) {
    for {
        select {
        case <-done:
            fmt.Println("shutting down")
            return
        case task := <-tasks:
            process(task)
        }
    }
}

// Signal shutdown by closing the done channel
done := make(chan struct{})
close(done) // all workers see this immediately
```

Closing a channel broadcasts to all receivers. This is why `chan struct{}` is used for signaling — it carries no data, only the signal.

---

## 4. The sync Package

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

---

## 5. context.Context

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

---

## 6. Common Concurrency Patterns

### Fan-Out / Fan-In

Distribute work across multiple goroutines (fan-out), then collect results (fan-in):

```go
func fanOutFanIn(ctx context.Context, urls []string) []Result {
    results := make(chan Result, len(urls))

    // Fan-out: launch a goroutine per URL
    var wg sync.WaitGroup
    for _, url := range urls {
        wg.Add(1)
        go func(u string) {
            defer wg.Done()
            results <- fetch(ctx, u)
        }(url)
    }

    // Close results channel when all goroutines complete
    go func() {
        wg.Wait()
        close(results)
    }()

    // Fan-in: collect all results
    var collected []Result
    for r := range results {
        collected = append(collected, r)
    }
    return collected
}
```

### Worker Pool

Limit concurrency with a fixed number of workers:

```go
func workerPool(ctx context.Context, tasks []Task, numWorkers int) []Result {
    tasksCh := make(chan Task)
    resultsCh := make(chan Result, len(tasks))

    // Start workers
    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for task := range tasksCh {
                select {
                case <-ctx.Done():
                    return
                default:
                    resultsCh <- process(task)
                }
            }
        }()
    }

    // Send tasks
    for _, t := range tasks {
        tasksCh <- t
    }
    close(tasksCh)

    // Wait and close results
    wg.Wait()
    close(resultsCh)

    var results []Result
    for r := range resultsCh {
        results = append(results, r)
    }
    return results
}
```

### Pipeline

Chain stages of processing:

```go
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for _, n := range nums {
            out <- n
        }
    }()
    return out
}

func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for n := range in {
            out <- n * n
        }
    }()
    return out
}

func main() {
    // Pipeline: generate -> square -> print
    for v := range square(generate(1, 2, 3, 4)) {
        fmt.Println(v) // 1, 4, 9, 16
    }
}
```

### Semaphore with Buffered Channel

```go
func processWithLimit(items []Item, maxConcurrent int) {
    sem := make(chan struct{}, maxConcurrent)
    var wg sync.WaitGroup

    for _, item := range items {
        wg.Add(1)
        sem <- struct{}{} // acquire (blocks when maxConcurrent goroutines are running)

        go func(it Item) {
            defer wg.Done()
            defer func() { <-sem }() // release
            process(it)
        }(item)
    }

    wg.Wait()
}
```

### Rate Limiting with time.Ticker

```go
func rateLimited(ctx context.Context, tasks []Task) {
    ticker := time.NewTicker(100 * time.Millisecond) // 10 per second
    defer ticker.Stop()

    for _, task := range tasks {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            go process(task)
        }
    }
}
```

### Generator Pattern

```go
func fibonacci(ctx context.Context) <-chan int {
    ch := make(chan int)
    go func() {
        defer close(ch)
        a, b := 0, 1
        for {
            select {
            case <-ctx.Done():
                return
            case ch <- a:
                a, b = b, a+b
            }
        }
    }()
    return ch
}

func main() {
    ctx, cancel := context.WithCancel(context.Background())
    defer cancel()

    for v := range fibonacci(ctx) {
        if v > 1000 {
            cancel()
            break
        }
        fmt.Println(v)
    }
}
```

### Or-Done Channel

Read from a channel while respecting cancellation:

```go
func orDone(ctx context.Context, in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for {
            select {
            case <-ctx.Done():
                return
            case v, ok := <-in:
                if !ok {
                    return
                }
                select {
                case out <- v:
                case <-ctx.Done():
                    return
                }
            }
        }
    }()
    return out
}
```

---

## 7. Race Conditions and the Race Detector

### Data Race vs Race Condition

- **Data race:** Two goroutines access the same variable concurrently, and at least one writes. This is undefined behavior in Go.
- **Race condition:** The correctness of the program depends on the timing/interleaving of goroutines. This is a logic bug.

You can have a race condition without a data race (using channels or mutexes correctly but in the wrong order) and a data race without a race condition (the program happens to work by luck).

### The Race Detector

Go has a built-in race detector. Use it:

```bash
go test -race ./...
go run -race main.go
go build -race -o myapp
```

```go
// This triggers the race detector:
func main() {
    counter := 0
    var wg sync.WaitGroup

    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++ // DATA RACE: unsynchronized write
        }()
    }

    wg.Wait()
    fmt.Println(counter) // wrong answer
}
```

The race detector output:

```
WARNING: DATA RACE
Write at 0x00c00001c0a8 by goroutine 7:
  main.main.func1()
      /path/main.go:15 +0x38

Previous write at 0x00c00001c0a8 by goroutine 6:
  main.main.func1()
      /path/main.go:15 +0x38
```

### Fixing Data Races

Three approaches:

```go
// 1. Mutex
var mu sync.Mutex
mu.Lock()
counter++
mu.Unlock()

// 2. Atomic operations (for simple counters)
var counter atomic.Int64
counter.Add(1)

// 3. Channel (send updates to a single goroutine)
updates := make(chan int)
go func() {
    counter := 0
    for delta := range updates {
        counter += delta
    }
}()
updates <- 1
```

### Race Detector in CI

Always run tests with `-race` in CI. The race detector has roughly 2-10x overhead, so it is too slow for production but essential for testing.

```bash
# In your CI pipeline
go test -race -count=1 ./...
```

---

## Interview Questions

### Conceptual

1. **Explain the difference between goroutines and OS threads.** Cover: lightweight stacks, M:N scheduling, creation cost, and why you can have millions of goroutines.

2. **When would you use a channel vs a mutex?** Channels for ownership transfer and coordinating goroutines. Mutexes for protecting shared state that is accessed by multiple goroutines.

3. **What happens when you send on a closed channel? Receive from a closed channel?** Send panics. Receive returns the zero value immediately (with `ok == false`).

4. **Explain context.Context and why it matters.** Cover: cancellation propagation, timeouts, request-scoped values, and the `ctx` as first parameter convention.

5. **What is the difference between a data race and a race condition?** Data race: concurrent unsynchronized access. Race condition: logic bug from timing dependency. A program can have one without the other.

### Coding

6. **Implement a worker pool** that processes tasks from a channel with a configurable number of workers, supports context cancellation, and returns results.

7. **Write a function that fetches N URLs concurrently** with a maximum of M concurrent requests (bounded parallelism), returning results in order.

8. **Implement a simple pub/sub system** using channels where publishers send events and multiple subscribers receive them.

9. **Find the bug:**

```go
func process(items []int) []int {
    results := make([]int, len(items))
    for i, item := range items {
        go func() {
            results[i] = transform(item)
        }()
    }
    return results
}
```

Bugs: (1) No synchronization — returns before goroutines finish, (2) In Go < 1.22, loop variable capture on `i` and `item`, (3) Data race on `results` slice elements (though technically different indices are safe, the lack of synchronization before reading is the real issue).

### Scenario

10. **Your service is leaking goroutines in production.** How do you detect this, and what are the common causes? Cover: `runtime.NumGoroutine()`, pprof goroutine profile, common causes (forgotten context cancellation, blocked channel operations, missing `wg.Done()`).

---

## Further Reading

- [Go Concurrency Patterns (Rob Pike, Google I/O 2012)](https://go.dev/talks/2012/concurrency.slide)
- [Advanced Go Concurrency Patterns (Sameer Ajmani)](https://go.dev/talks/2013/advconc.slide)
- [The Go Memory Model](https://go.dev/ref/mem)
- [Go Blog: Pipelines and Cancellation](https://go.dev/blog/pipelines)
- [Go Blog: Context](https://go.dev/blog/context)
- [Go Blog: Share Memory by Communicating](https://go.dev/blog/codelab-share)
- [Bryan Mills — Rethinking Classical Concurrency Patterns (GopherCon 2018)](https://www.youtube.com/watch?v=5zXAHh5tJqQ)
