# Module 02 Cheat Sheet: Concurrency Primitives

## Channel Operations Behavior Table

| Operation | nil channel | Closed channel | Open (not full/empty) | Open (full/empty) |
|-----------|-------------|----------------|----------------------|-------------------|
| **Send** `ch <- v` | Block forever | **PANIC** | Send value | Block until space |
| **Receive** `<-ch` | Block forever | Zero value, `ok=false` | Receive value | Block until value |
| **Close** `close(ch)` | **PANIC** | **PANIC** | Close (receivers get remaining then zero) | Close |
| **Len** `len(ch)` | 0 | Buffered items remaining | Buffered items | 0 |
| **Cap** `cap(ch)` | 0 | Buffer capacity | Buffer capacity | Buffer capacity |

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

## sync Primitives Comparison

| Primitive | Purpose | Key Methods | Notes |
|-----------|---------|-------------|-------|
| `sync.Mutex` | Exclusive access | `Lock()`, `Unlock()` | Use `defer Unlock()` |
| `sync.RWMutex` | Read-heavy shared access | `RLock()`, `RUnlock()`, `Lock()`, `Unlock()` | Multiple readers OR one writer |
| `sync.WaitGroup` | Wait for N goroutines | `Add(n)`, `Done()`, `Wait()` | Call `Add` before `go func` |
| `sync.Once` | One-time init | `Do(func())` | Safe across goroutines |
| `sync.Map` | Concurrent map | `Store()`, `Load()`, `Delete()`, `Range()` | Prefer regular map + mutex usually |
| `sync.Pool` | Object reuse | `Get()`, `Put()` | Cleared at GC; reduce allocation |
| `sync.Cond` | Signal waiting goroutines | `Wait()`, `Signal()`, `Broadcast()` | Rarely needed; channels usually better |

## Context Tree

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

## Context Quick Reference

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

## Concurrency Pattern Templates

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

### Fan-Out / Fan-In

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
```

### Pipeline Stage

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

### Semaphore (Bounded Concurrency)

```go
sem := make(chan struct{}, maxConcurrent)
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    sem <- struct{}{} // acquire
    go func(it Item) {
        defer wg.Done()
        defer func() { <-sem }() // release
        process(it)
    }(item)
}
wg.Wait()
```

### Graceful Shutdown

```go
ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
defer stop()

go func() { srv.ListenAndServe() }()

<-ctx.Done()
shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()
srv.Shutdown(shutdownCtx)
```

## Race Detector Usage

```bash
go test -race ./...           # Run tests with race detector
go run -race main.go          # Run program with race detector
go build -race -o app         # Build binary with race detector

# In CI (always):
go test -race -count=1 ./...
```

## Common Goroutine Leak Causes

| Cause | Fix |
|-------|-----|
| Blocked send on unbuffered channel | Use buffered channel (size 1) |
| Blocked receive, no sender | Check `ctx.Done()` in select |
| Forgotten `cancel()` | Always `defer cancel()` |
| Missing `wg.Done()` | Always `defer wg.Done()` |
| Infinite loop without exit | Check `ctx.Done()` periodically |
| Orphaned goroutine after parent returns | Use context for lifecycle management |
