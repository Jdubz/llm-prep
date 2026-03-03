# 03 – Advanced Concurrency Patterns

This file assumes you have read `01-goroutines-and-channels.md` and `02-synchronization-and-context.md`. It covers advanced patterns, scheduler internals, the memory model, common concurrency bugs, and interview Q&A.

---

## 1. Go Scheduler Internals: The GMP Model

The Go scheduler is the reason goroutines are cheap. Understanding it helps you reason about performance, diagnose issues, and answer interview questions.

### The Three Entities

**G (Goroutine):** A unit of work. Contains the stack, instruction pointer, and other scheduling-related state. Represented by the `runtime.g` struct.

**M (Machine):** An OS thread. The thing that actually runs code on a CPU core. Represented by `runtime.m`.

**P (Processor):** A logical processor — a scheduling context. Each P has a local run queue of goroutines. The number of Ps equals `GOMAXPROCS` (default: number of CPU cores).

```
P0 [local queue: G1, G2, G3] ---> M0 (OS thread on CPU core 0)
P1 [local queue: G4, G5]     ---> M1 (OS thread on CPU core 1)
P2 [local queue: G6]         ---> M2 (OS thread on CPU core 2)

Global run queue: [G7, G8, G9, ...]
```

### How Scheduling Works

1. Each P has a **local run queue** (max 256 goroutines).
2. There is also a **global run queue** for overflow.
3. When an M (thread) needs work, its P dequeues a G from the local queue.
4. If the local queue is empty, the P:
   a. Checks the global run queue.
   b. Checks the network poller.
   c. **Steals** from another P's local run queue (work stealing).
5. When a goroutine blocks on I/O or a syscall, the M is detached from the P, and the P is handed to another M (or a new M is created).

### Work Stealing

When P1's local queue is empty:

```
Before:
P0 [G1, G2, G3, G4]    P1 [empty]

After stealing half of P0's queue:
P0 [G1, G2]             P1 [G3, G4]
```

Work stealing ensures even distribution of work across cores without centralized scheduling overhead.

### Preemption

Go 1.14+ introduced **asynchronous preemption** using OS signals. Before that, goroutines could only be preempted at function calls, which meant a tight CPU-bound loop could starve other goroutines.

```go
// Pre-Go 1.14: this would starve other goroutines
func tightLoop() {
    for {
        // no function calls — scheduler cannot preempt
    }
}

// Go 1.14+: the runtime sends a signal to preempt this goroutine
```

Now the runtime can preempt goroutines at (almost) any point using `SIGURG` signals on Linux. This is why you see `signal.Notify` documentation mentioning `SIGURG` — the runtime uses it internally.

### GOMAXPROCS

```go
runtime.GOMAXPROCS(4) // Use 4 Ps (4 OS threads running goroutines concurrently)
```

Default: number of available CPU cores. Increasing it above the core count rarely helps. Decreasing it can be useful for benchmarking or controlling CPU usage.

### Observing the Scheduler

```bash
GODEBUG=schedtrace=1000 ./myapp
# Output every 1000ms:
# SCHED 1000ms: gomaxprocs=8 idleprocs=6 threads=10 spinningthreads=1 idlethreads=3 runqueue=0 [0 0 2 0 0 0 0 0]
```

The numbers in brackets are the per-P local run queue sizes.

---

## 2. Channel Internals

### The hchan Struct

Every channel is backed by a `runtime.hchan` struct:

```go
type hchan struct {
    qcount   uint           // number of elements currently in the buffer
    dataqsiz uint           // capacity of the buffer (0 for unbuffered)
    buf      unsafe.Pointer // pointer to the circular buffer
    elemsize uint16
    closed   uint32
    sendx    uint           // send index in the circular buffer
    recvx    uint           // receive index in the circular buffer
    recvq    waitq          // queue of waiting receivers
    sendq    waitq          // queue of waiting senders
    lock     mutex          // protects the entire struct
}
```

### Unbuffered Channel Flow

```
Sender goroutine                    Receiver goroutine
       |                                   |
  ch <- value                         val := <-ch
       |                                   |
  Lock hchan                         Lock hchan
       |                                   |
  No receiver waiting?               No sender waiting?
       |                                   |
  Park self in sendq                  Park self in recvq
  (goroutine goes to sleep)           (goroutine goes to sleep)
       |                                   |
  --- When receiver arrives ---       --- When sender arrives ---
       |                                   |
  Copy value directly to              Sender copies value directly
  receiver's stack (optimization!)    to our stack
       |                                   |
  Both goroutines resume              Both goroutines resume
```

The key optimization: for unbuffered channels, Go copies the value directly from the sender's stack to the receiver's stack — no intermediate buffer.

### Buffered Channel Flow

```
Send (buffer not full):
  1. Lock hchan
  2. Copy value to buf[sendx]
  3. Increment sendx (circular)
  4. Increment qcount
  5. Unlock
  (No goroutine parking needed)

Send (buffer full):
  1. Lock hchan
  2. Park sender in sendq
  3. Unlock
  (Sender sleeps until receiver drains a slot)

Receive (buffer not empty):
  1. Lock hchan
  2. Copy value from buf[recvx]
  3. Increment recvx (circular)
  4. Decrement qcount
  5. If sender waiting in sendq, wake it and copy its value into the freed slot
  6. Unlock
```

---

## 3. The Go Memory Model

### Happens-Before

The Go memory model defines when one goroutine's writes are guaranteed to be visible to another goroutine's reads. The key concept is **happens-before**.

Event A happens-before event B if:
- A and B are in the same goroutine and A comes first in program order.
- A is a send on a channel and B is the corresponding receive.
- A is a `sync.Mutex.Unlock` and B is the corresponding `Lock`.
- A is a `sync.WaitGroup.Done` and B is the corresponding `Wait`.

If A does NOT happen-before B and B does NOT happen-before A, they are concurrent and **no ordering is guaranteed**.

```go
var a, b int

// Goroutine 1
a = 1
ch <- struct{}{} // send happens-before receive

// Goroutine 2
<-ch     // receive
fmt.Println(a) // guaranteed to see a == 1
fmt.Println(b) // NO guarantee about b's value
```

---

## 4. Concurrency Patterns

### Worker Pool

```go
func workerPool(ctx context.Context, tasks <-chan Task, results chan<- Result, workers int) {
    var wg sync.WaitGroup
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for {
                select {
                case <-ctx.Done():
                    return
                case task, ok := <-tasks:
                    if !ok {
                        return
                    }
                    results <- process(task)
                }
            }
        }()
    }
    go func() {
        wg.Wait()
        close(results)
    }()
}
```

Full worker pool with task dispatch:

```go
func workerPoolFull(ctx context.Context, tasks []Task, numWorkers int) []Result {
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

### Fan-Out / Fan-In

Distribute work across multiple goroutines (fan-out), then collect results (fan-in):

```go
func fanOut(ctx context.Context, input <-chan int, workers int) <-chan int {
    out := make(chan int)
    var wg sync.WaitGroup
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for v := range input {
                select {
                case out <- v * v:
                case <-ctx.Done():
                    return
                }
            }
        }()
    }
    go func() { wg.Wait(); close(out) }()
    return out
}

func fanOutFanIn(ctx context.Context, urls []string) []Result {
    results := make(chan Result, len(urls))

    var wg sync.WaitGroup
    for _, url := range urls {
        wg.Add(1)
        go func(u string) {
            defer wg.Done()
            results <- fetch(ctx, u)
        }(url)
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    var collected []Result
    for r := range results {
        collected = append(collected, r)
    }
    return collected
}
```

### Pipeline Pattern

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

### Pipeline Stage Template (context-aware)

```go
func stage(ctx context.Context, in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for v := range in {
            select {
            case out <- transform(v):
            case <-ctx.Done():
                return
            }
        }
    }()
    return out
}
// Usage: result := stage3(ctx, stage2(ctx, stage1(ctx, input)))
```

### Pipeline with Error Propagation

Real pipelines need error handling. Here is a pipeline that stops on first error:

```go
func pipeline(ctx context.Context, input []string) ([]Result, error) {
    ctx, cancel := context.WithCancel(ctx)
    defer cancel()

    // Stage 1: Generate
    stage1 := make(chan string)
    go func() {
        defer close(stage1)
        for _, s := range input {
            select {
            case stage1 <- s:
            case <-ctx.Done():
                return
            }
        }
    }()

    // Stage 2: Transform (with error)
    type transformResult struct {
        val Result
        err error
    }
    stage2 := make(chan transformResult)
    go func() {
        defer close(stage2)
        for s := range stage1 {
            r, err := transform(ctx, s)
            select {
            case stage2 <- transformResult{r, err}:
            case <-ctx.Done():
                return
            }
        }
    }()

    // Collect results, abort on error
    var results []Result
    for tr := range stage2 {
        if tr.err != nil {
            cancel() // cancel upstream stages
            return nil, tr.err
        }
        results = append(results, tr.val)
    }
    return results, nil
}
```

### Semaphore with Buffered Channel

A buffered channel makes an elegant semaphore: sending to the channel "acquires" a slot, and receiving "releases" it. When the buffer is full, the next send blocks — naturally limiting concurrency to the buffer size. This is simpler than using a `sync.WaitGroup` with a counter because the channel handles the blocking automatically.

```go
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
```

### Bounded Parallelism (preserving order)

The semaphore pattern above processes items concurrently but does not guarantee result order matches input order. When order matters (e.g., pagination results, ordered transformations), use an indexed result channel: each goroutine sends its result tagged with the original index, and the collector reassembles results in order.

```go
func boundedParallel(ctx context.Context, items []Item, limit int) ([]Result, error) {
    type indexedResult struct {
        index int
        val   Result
        err   error
    }

    sem := make(chan struct{}, limit)
    results := make(chan indexedResult, len(items))

    var wg sync.WaitGroup
    for i, item := range items {
        wg.Add(1)
        go func(idx int, it Item) {
            defer wg.Done()

            // Acquire semaphore
            select {
            case sem <- struct{}{}:
                defer func() { <-sem }()
            case <-ctx.Done():
                results <- indexedResult{idx, Result{}, ctx.Err()}
                return
            }

            r, err := process(ctx, it)
            results <- indexedResult{idx, r, err}
        }(i, item)
    }

    go func() {
        wg.Wait()
        close(results)
    }()

    ordered := make([]Result, len(items))
    for r := range results {
        if r.err != nil {
            return nil, r.err
        }
        ordered[r.index] = r.val
    }
    return ordered, nil
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

### Pub/Sub with Channels

```go
type PubSub struct {
    mu     sync.RWMutex
    subs   map[string][]chan string
}

func NewPubSub() *PubSub {
    return &PubSub{subs: make(map[string][]chan string)}
}

func (ps *PubSub) Subscribe(topic string) <-chan string {
    ps.mu.Lock()
    defer ps.mu.Unlock()

    ch := make(chan string, 16) // buffered to reduce blocking
    ps.subs[topic] = append(ps.subs[topic], ch)
    return ch
}

func (ps *PubSub) Publish(topic, msg string) {
    ps.mu.RLock()
    defer ps.mu.RUnlock()

    for _, ch := range ps.subs[topic] {
        select {
        case ch <- msg:
        default:
            // subscriber is slow — drop the message or log
        }
    }
}

func (ps *PubSub) Close(topic string) {
    ps.mu.Lock()
    defer ps.mu.Unlock()

    for _, ch := range ps.subs[topic] {
        close(ch)
    }
    delete(ps.subs, topic)
}
```

---

## 5. Data Races and the Race Detector

### Data Race vs Race Condition

- **Data race:** Two goroutines access the same variable concurrently, and at least one writes. This is undefined behavior in Go.
- **Race condition:** The correctness of the program depends on the timing/interleaving of goroutines. This is a logic bug.

You can have a race condition without a data race (using channels or mutexes correctly but in the wrong order) and a data race without a race condition (the program happens to work by luck).

### The Race Detector

Go has a built-in race detector. Use it:

```bash
go test -race ./...           # Run tests with race detector
go run -race main.go          # Run program with race detector
go build -race -o app         # Build binary with race detector

# In CI (always):
go test -race -count=1 ./...
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

---

## 6. Common Concurrency Bugs

### Bug 1: Goroutine Leak from Blocked Channel

```go
func search(ctx context.Context, query string) (Result, error) {
    ch := make(chan Result) // unbuffered!

    go func() {
        result := expensiveSearch(query)
        ch <- result // BLOCKS FOREVER if caller returns early (timeout/cancel)
    }()

    select {
    case r := <-ch:
        return r, nil
    case <-ctx.Done():
        return Result{}, ctx.Err()
        // goroutine above is now leaked — blocked on send with no receiver
    }
}
```

**Fix:** Use a buffered channel of size 1:

```go
ch := make(chan Result, 1) // goroutine can send even if no one receives
```

### Bug 2: Mutex Copy

```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c Counter) Increment() { // VALUE receiver — copies the mutex!
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

The value receiver copies the entire Counter, including the mutex. Each call gets its own mutex, providing no protection.

**Fix:** Use a pointer receiver:

```go
func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}
```

Use `go vet` — it detects mutex copies.

### Bug 3: Missing WaitGroup.Add Before Goroutine

```go
var wg sync.WaitGroup
for i := 0; i < 10; i++ {
    go func(id int) {
        wg.Add(1)    // BUG: Add inside goroutine — wg.Wait() might execute first
        defer wg.Done()
        process(id)
    }(i)
}
wg.Wait() // might return before all goroutines call Add
```

**Fix:** Call `Add` before launching the goroutine.

### Bug 4: No Context Cancellation Check in Loop Body

```go
func worker(ctx context.Context, tasks <-chan Task) {
    for task := range tasks {
        // This loop does NOT check ctx — continues processing even after cancellation
        processLong(task)
    }
}
```

**Fix:**

```go
func worker(ctx context.Context, tasks <-chan Task) {
    for {
        select {
        case <-ctx.Done():
            return
        case task, ok := <-tasks:
            if !ok {
                return
            }
            processLong(ctx, task)
        }
    }
}
```

### Bug 5: Closing a Channel from Multiple Goroutines

```go
// Multiple workers trying to close the output channel
for i := 0; i < numWorkers; i++ {
    go func() {
        defer close(out) // PANIC: close of closed channel (second worker)
        // ...
    }()
}
```

**Fix:** Use `sync.Once` or coordinate closing from a single goroutine:

```go
go func() {
    wg.Wait()
    close(out) // single closer, triggered after all workers finish
}()
```

### Detecting These Bugs

1. **Race detector:** `go test -race ./...` catches data races.
2. **go vet:** Catches mutex copies, printf format errors, unreachable code.
3. **Goroutine profile:** `pprof` shows stuck goroutines in production.
4. **Deadlock detector:** The runtime detects when all goroutines are blocked (but not partial deadlocks).
5. **goleak:** The `go.uber.org/goleak` package detects goroutine leaks in tests.

```go
import "go.uber.org/goleak"

func TestMain(m *testing.M) {
    goleak.VerifyTestMain(m)
}
```

---

## 7. Interview Questions

### Conceptual

1. **Explain the difference between goroutines and OS threads.** Cover: lightweight stacks, M:N scheduling (GMP model), creation cost, and why you can have millions of goroutines.

2. **When would you use a channel vs a mutex?** Channels for ownership transfer and coordinating goroutines. Mutexes for protecting shared state that is accessed by multiple goroutines.

3. **What happens when you send on a closed channel? Receive from a closed channel?** Send panics. Receive returns the zero value immediately (with `ok == false`).

4. **Explain context.Context and why it matters.** Cover: cancellation propagation, timeouts, request-scoped values, and the `ctx` as first parameter convention.

5. **What is the difference between a data race and a race condition?** Data race: concurrent unsynchronized access. Race condition: logic bug from timing dependency. A program can have one without the other.

6. **Describe the GMP model in Go's scheduler.** G = goroutine (unit of work), M = OS thread, P = logical processor/scheduling context. Each P has a local run queue. Work stealing balances load.

7. **What is the happens-before relationship in Go's memory model?** Define happens-before; list the guarantees: channel operations, mutex unlock/lock, WaitGroup Done/Wait. Explain that concurrent accesses without happens-before have no ordering guarantees.

8. **What causes goroutine leaks and how do you detect them?** Blocked channel operations, missing cancel/Done, infinite loops without exit. Detection: `runtime.NumGoroutine()`, pprof goroutine profile, `goleak` in tests.

### Coding

9. **Implement a worker pool** that processes tasks from a channel with a configurable number of workers, supports context cancellation, and returns results.

10. **Write a function that fetches N URLs concurrently** with a maximum of M concurrent requests (bounded parallelism), returning results in order.

11. **Implement a simple pub/sub system** using channels where publishers send events and multiple subscribers receive them.

12. **Find the bug:**

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

13. **Your service is leaking goroutines in production.** How do you detect this, and what are the common causes? Cover: `runtime.NumGoroutine()`, pprof goroutine profile, common causes (forgotten context cancellation, blocked channel operations, missing `wg.Done()`).

14. **You need to process 10,000 items as fast as possible but your downstream service rate-limits you to 100 concurrent requests.** Design the solution. Cover: worker pool or semaphore pattern, context cancellation, error handling strategy.

---

## Related Reading

- **Concurrency in HTTP middleware** — [Module 04: Advanced HTTP Patterns](../04-http-services/03-advanced-http-patterns.md) applies worker pools and rate limiting from this file to HTTP service architectures
- **singleflight for caching** — [Module 05: Migrations, Redis, and Advanced Storage](../05-data-storage/03-migrations-redis-and-advanced-storage.md), section 2 (Caching Patterns) shows `singleflight` preventing cache stampedes in real storage layers
- **Testing concurrent code** — [Module 06: Benchmarking, Profiling, and Advanced Testing](../06-testing/03-benchmarking-profiling-and-advanced-testing.md), section 5 (Testing Concurrent Code) covers race detector usage, `goleak`, and deterministic testing for the patterns in this file
- **GC and memory model** — [Module 01: Advanced Go Internals](../01-go-mental-model/03-advanced-go-internals.md), section 3 (Garbage Collector) explains the runtime that underpins the GMP scheduler described in section 1
- **Interview concurrency puzzles** — [Module 09: Interview Essentials](../09-interview-prep/01-interview-essentials.md), section 6 tests your ability to implement the worker pool, fan-out/fan-in, and rate limiter patterns from this file

---

## Practice Suggestions

These exercises reinforce the concurrency concepts from this module (Goroutines and Channels through Advanced Concurrency Patterns):

1. **Build a pipeline** — Implement a three-stage pipeline: a generator that produces integers, a stage that squares them, and a stage that filters odd results. Connect them with channels and add context cancellation. Verify that all goroutines exit cleanly using `goleak` in a test.

2. **Worker pool with error handling** — Build a generic worker pool that processes URL fetches with bounded concurrency (e.g., 5 workers for 100 URLs). Collect results and errors, and support cancellation via context. Write a test that cancels mid-flight and verifies no goroutine leaks.

3. **Rate limiter** — Implement a token bucket rate limiter using channels. Write a benchmark that measures throughput under different rate limits and a test that verifies requests are throttled correctly.

4. **Detect and fix a data race** — Write a program with an intentional data race (e.g., concurrent map writes). Run it with `go run -race` to see the detector output. Fix it using three different approaches: `sync.Mutex`, `sync/atomic`, and channel-based ownership. Benchmark all three.

5. **singleflight deduplication** — Build a function that simulates expensive computation (using `time.Sleep`). Wrap it with `singleflight` and write a test that fires 100 concurrent requests for the same key, verifying the computation only runs once.

6. **Graceful shutdown orchestration** — Build a program with a background worker goroutine, a periodic ticker, and a simulated HTTP server. Implement ordered graceful shutdown: stop accepting new work, drain in-flight operations, then exit. Test with `SIGINT` simulation.

---

## Further Reading

- [Go Concurrency Patterns (Rob Pike, Google I/O 2012)](https://go.dev/talks/2012/concurrency.slide)
- [Advanced Go Concurrency Patterns (Sameer Ajmani)](https://go.dev/talks/2013/advconc.slide)
- [The Go Memory Model](https://go.dev/ref/mem)
- [Go Blog: Pipelines and Cancellation](https://go.dev/blog/pipelines)
- [Go Blog: Context](https://go.dev/blog/context)
- [Go Blog: Share Memory by Communicating](https://go.dev/blog/codelab-share)
- [The Go Scheduler (Morsing)](https://morsmachine.dk/go-scheduler)
- [Go's Work-Stealing Scheduler (Rakyll)](https://rakyll.org/scheduler/)
- [Channel Implementation (Kavya Joshi, GopherCon 2017)](https://www.youtube.com/watch?v=KBZlN0izeiY)
- [goleak — Goroutine Leak Detector](https://github.com/uber-go/goleak)
- [Bryan Mills — Rethinking Classical Concurrency Patterns](https://www.youtube.com/watch?v=5zXAHh5tJqQ)
