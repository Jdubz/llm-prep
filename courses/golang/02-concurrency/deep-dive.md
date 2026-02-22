# Module 02 Deep Dive: Scheduler Internals, Channel Machinery, and Memory Model

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

### Performance Characteristics

- Unbuffered channels: ~50-100ns per operation (with goroutine parking/waking).
- Buffered channels (not full/empty): ~20-50ns per operation (no parking needed).
- Mutex lock/unlock: ~10-20ns.
- Atomic operation: ~5-10ns.

For raw throughput of simple counter updates, atomics beat mutexes beat channels. But channels provide safety guarantees and composability that atomics cannot.

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

### Atomic Operations

The `sync/atomic` package provides low-level atomic operations. In Go 1.19+, there are typed wrappers:

```go
var counter atomic.Int64

counter.Add(1)
counter.Store(42)
val := counter.Load()
swapped := counter.CompareAndSwap(42, 100)
```

Pre-1.19 API (still valid):

```go
var counter int64

atomic.AddInt64(&counter, 1)
atomic.StoreInt64(&counter, 42)
val := atomic.LoadInt64(&counter)
swapped := atomic.CompareAndSwapInt64(&counter, 42, 100)
```

**When to use atomics:**
- Simple counters, flags, and pointers.
- When a mutex is too heavy for a single variable.
- When you need lock-free data structures (rare in application code).

**When NOT to use atomics:**
- When you need to update multiple related variables consistently.
- When the logic is more complex than a single read-modify-write.
- When a mutex makes the code clearer.

### The atomic.Value Type

Store and load any value atomically:

```go
var config atomic.Value // holds a *Config

// Writer
config.Store(&Config{Debug: true, Port: 8080})

// Reader (can be called from any goroutine)
cfg := config.Load().(*Config)
```

Useful for configuration hot-reloading where a single writer updates and multiple readers access.

---

## 4. Advanced Concurrency Patterns

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

### Bounded Parallelism

Process items in parallel but limit the number of concurrent operations:

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

### Graceful Shutdown

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

---

## 5. Common Concurrency Bugs

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

func newCounter() Counter {
    return Counter{}
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

### Bug 4: Select with Context but No Cancellation Check in Loop Body

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

## Further Reading

- [The Go Scheduler (Morsing)](https://morsmachine.dk/go-scheduler)
- [Go's Work-Stealing Scheduler (Rakyll)](https://rakyll.org/scheduler/)
- [Go Memory Model (official)](https://go.dev/ref/mem)
- [Channel Implementation (Kavya Joshi, GopherCon 2017)](https://www.youtube.com/watch?v=KBZlN0izeiY)
- [goleak — Goroutine Leak Detector](https://github.com/uber-go/goleak)
- [Bryan Mills — Rethinking Classical Concurrency Patterns](https://www.youtube.com/watch?v=5zXAHh5tJqQ)
