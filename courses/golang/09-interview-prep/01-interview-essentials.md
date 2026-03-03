# 01 – Interview Essentials

Go interviews test three things:
1. **Concurrency reasoning** — Can you think about goroutines, channels, and race conditions?
2. **Idiomatic design** — Do you write Go like Go, or like Java/TypeScript translated into Go syntax?
3. **Production engineering** — Can you build, deploy, and operate Go services?

---

## 1. Top 20 Questions with One-Line Answers

| # | Question | Answer |
|---|----------|--------|
| 1 | What is a goroutine? | Lightweight thread managed by Go runtime (~2KB stack, multiplexed onto OS threads) |
| 2 | Goroutine vs thread? | Goroutines: 2KB stack, M:N scheduling, channel communication. Threads: 1MB stack, 1:1 OS mapping |
| 3 | What causes a goroutine leak? | Goroutine blocks on channel/mutex/IO with no exit path — use context for cancellation |
| 4 | Buffered vs unbuffered channel? | Unbuffered: synchronous handoff. Buffered: async up to capacity, then blocks |
| 5 | What is `select`? | Multiplexes channel ops; blocks until one is ready; `default` makes non-blocking |
| 6 | Nil interface gotcha? | Interface with typed nil pointer is not `== nil`; check type and value separately |
| 7 | Slice internals? | 3-word struct: pointer to array, length, capacity. Multiple slices can share array |
| 8 | Map thread safety? | Maps are NOT goroutine-safe. Concurrent read+write panics. Use `sync.Mutex` or `sync.Map` |
| 9 | `make` vs `new`? | `make`: initializes slice/map/chan. `new`: allocates zeroed memory, returns pointer |
| 10 | Defer execution order? | LIFO — last deferred runs first. Arguments evaluated at defer time, not execution time |
| 11 | Value vs pointer receiver? | Value: gets copy, cannot modify. Pointer: gets reference, can modify, avoids copy |
| 12 | How does GC work? | Tri-color mark-and-sweep, concurrent, low-latency. Tuned via `GOGC` and `GOMEMLIMIT` |
| 13 | What does `init()` do? | Runs before `main()`, in dependency order. Use sparingly — hard to test |
| 14 | Error handling philosophy? | Errors are values, returned not thrown. Wrap with `%w`, check with `errors.Is`/`errors.As` |
| 15 | When use generics? | Same algorithm across types (containers, utilities). Not for polymorphic behavior (use interfaces) |
| 16 | What is `context.Context`? | Carries deadlines, cancellation, and request-scoped values across API boundaries |
| 17 | `internal/` directory? | Compiler-enforced privacy — code only importable by parent module |
| 18 | How to detect races? | `go test -race` or `go run -race` enables race detector (2–10x slower, dev/CI only) |
| 19 | `sync.WaitGroup` usage? | `Add` before goroutine, `Done` in goroutine (defer), `Wait` blocks until counter zero |
| 20 | What is `embed`? | Compile static files into binary via `//go:embed`. Returns `embed.FS` implementing `fs.FS` |

---

## 2. Common Interview Questions

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

An interface value has two components: a type and a value. An interface is only `nil` when both are nil.

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

Maps in Go are not goroutine-safe. Concurrent read+write or write+write causes a runtime panic (a hard crash, not just a data race).

```go
// CRASH: concurrent map writes
m := make(map[string]int)
go func() { m["a"] = 1 }()
go func() { m["b"] = 2 }()  // fatal error: concurrent map writes

// FIX 1: sync.RWMutex
var mu sync.RWMutex
mu.Lock(); m["a"] = 1; mu.Unlock()

// FIX 2: sync.Map (for specific patterns: write-once, read-many)
var sm sync.Map
sm.Store("a", 1)
val, ok := sm.Load("a")
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
defer fmt.Println(x)                 // Prints 0 — evaluated at defer time
defer func() { fmt.Println(x) }()   // Prints 1 — closure captures variable
x = 1
```

### Q7-Q20: Rapid-Fire Reference

| # | Question | Key Answer |
|---|----------|-----------|
| 7 | How do `init` functions work? | Run before `main()` in dependency order; package vars first, then `init()` in file order |
| 8 | What is Go's error handling philosophy? | Errors are values; wrap with `%w`; check with `errors.Is`/`errors.As` |
| 9 | When do you use `context.Context`? | Every function that does I/O or could block; first parameter; never store in struct |
| 10 | How do you tune the garbage collector? | `GOGC` controls frequency; `GOMEMLIMIT` (Go 1.19+) sets soft memory limit |
| 11 | Difference between `make` and `new`? | `make` initializes slices/maps/channels; `new` allocates zeroed memory, returns pointer |
| 12 | What does `go vet` check? | printf format mismatches, unreachable code, mutex copy, struct tag errors |
| 13 | How do goroutines differ from OS threads? | Goroutines multiplexed onto OS threads; ~2KB initial stack vs ~1MB for threads |
| 14 | What is a race condition in Go? | Two goroutines access shared memory, at least one writes, without synchronization |
| 15 | Explain `sync.WaitGroup`. | Counter-based: `Add(n)` before spawning, `Done()` in goroutine, `Wait()` blocks until 0 |
| 16 | What is `select` used for? | Multiplexing channel operations; blocks until one case is ready; `default` = non-blocking |
| 17 | Difference between buffered and unbuffered channels? | Unbuffered: sender blocks until receiver ready. Buffered: blocks only when buffer full |
| 18 | What is `sync.Once` for? | Guarantees a function executes exactly once, even across goroutines |
| 19 | How does Go handle method receivers? | Value receiver gets a copy; pointer receiver gets the original and can modify state |
| 20 | What is the blank identifier `_`? | Discards a value; used to ignore return values or satisfy import/interface requirements |

---

## 3. Concurrency Bug Patterns

| Bug | Symptom | Fix |
|-----|---------|-----|
| Goroutine leak | Memory grows, goroutine count increases | Add context cancellation, use `goleak` in tests |
| Channel deadlock | `fatal error: all goroutines are asleep` | Ensure every send has a receiver (or use buffered) |
| Data race | Flaky tests, corrupted data | `sync.Mutex`, `atomic`, or channel-based ownership |
| Concurrent map write | `fatal error: concurrent map writes` | `sync.RWMutex` or `sync.Map` |
| Premature close | `send on closed channel` panic | Only the sender closes; close once with `sync.Once` |
| Mutex copy | Lock has no effect | Never copy a `sync.Mutex` (pass by pointer, use `go vet`) |
| Context leak | Background goroutines outlive request | Always call `cancel()` from `context.WithCancel` |

---

## 4. Code Review Red Flags

| Red Flag | Why It Matters | Fix |
|----------|---------------|-----|
| `go func()` without `sync.WaitGroup` | Goroutine leak risk | Track with WaitGroup or errgroup |
| No context parameter on I/O functions | Cannot cancel or timeout | Accept `context.Context` as first param |
| `interface{}` / `any` everywhere | Loses type safety | Use generics or specific interfaces |
| Error ignored with `_` | Silent failures | Handle or explicitly document why ignored |
| Global mutable state | Race conditions, hard to test | Pass dependencies explicitly |
| `time.Sleep` in tests | Flaky, slow tests | Use channels, contexts, or `time.After` |
| String concatenation in loop | O(n²) allocations | Use `strings.Builder` |
| `panic` for error handling | Crashes the program | Return errors; panic is for programmer bugs |
| Unbounded goroutine creation | OOM under load | Use worker pool with bounded concurrency |
| Missing `defer mu.Unlock()` | Deadlock on error path | Always `defer` the unlock after lock |
| `sync.Mutex` as value field | Mutex copied = broken | Use pointer or never copy the struct |
| Channel without `select` + context | Blocks forever if context cancelled | Always select on both channel and `ctx.Done()` |

---

## 5. Idiomatic Go Rules

| Rule | Example |
|------|---------|
| Accept interfaces, return structs | `func New(r io.Reader) *Parser` |
| Error strings are lowercase, no punctuation | `fmt.Errorf("opening file: %w", err)` |
| Use `MixedCaps`, not `snake_case` | `userID`, not `user_id` |
| Exported = uppercase, unexported = lowercase | `func Parse()` vs `func parse()` |
| Receiver name is 1–2 letters, not `this`/`self` | `func (s *Server) Start()` |
| Return early, avoid deep nesting | `if err != nil { return err }` then happy path |
| Context is always the first parameter | `func Get(ctx context.Context, id int) error` |
| Do not stutter: `user.User` is bad | `user.Profile` instead |
| Interfaces are named with -er suffix | `Reader`, `Writer`, `Closer`, `Handler` |
| Prefer small interfaces (1–3 methods) | `io.Reader` has 1 method |
| Zero values should be useful | `var buf bytes.Buffer` works without init |
| Do not panic in library code | Return errors; let the caller decide |
| Wrap errors with context | `fmt.Errorf("getting user %d: %w", id, err)` |
| Use `gofmt` / `goimports` — no exceptions | `gofmt -w .` |
| Table-driven tests | `tests := []struct{ name string; ... }` |
| Test file lives next to source | `user.go` and `user_test.go` in same directory |

---

## 6. Concurrency Puzzles

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

Fix options:

```go
// Option 1: sync.Mutex
var mu sync.Mutex
mu.Lock(); counter++; mu.Unlock()

// Option 2: atomic (best for simple counters)
var counter atomic.Int64
counter.Add(1)

// Option 3: Channel (collects results)
results := make(chan int, 1000)
// goroutines send to results; main goroutine sums
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

## 7. Live Coding Setup Template

```go
package main

import (
    "context"
    "fmt"
    "sync"
    "time"
)

func main() {
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    // Your solution here

    _ = ctx
    fmt.Println("done")
}
```

**Interviewer expectations during live coding:**
1. Start with types and function signatures
2. Handle errors explicitly (never `_`)
3. Use context for cancellation
4. Add `sync.WaitGroup` for goroutine lifecycle
5. Close channels correctly (sender closes, receiver ranges)
6. Mention what you would test (`-race`, table tests, edge cases)

---

## Related Reading

This file synthesizes concepts from the entire course. Here are the most relevant deep-dive references for each topic area:

- **Concurrency questions (Q1–Q6, Puzzles)** — [Module 02: Goroutines and Channels](../02-concurrency/01-goroutines-and-channels.md) and [Synchronization and Context](../02-concurrency/02-synchronization-and-context.md) cover the goroutine, channel, and sync primitives tested in section 6
- **Idiomatic Go rules** — [Module 01: Types, Interfaces, and Structs](../01-go-mental-model/01-types-interfaces-and-structs.md), section 9 (Naming Conventions) covers the naming and style rules from section 5
- **Error handling** — [Module 07: Project Structure and Configuration](../07-production/01-project-structure-and-configuration.md), section 3 (Error Handling in Production) covers the `%w` wrapping and sentinel error patterns from section 2
- **Code review patterns** — [Module 06: Table-Driven Tests and Mocking](../06-testing/01-table-driven-tests-and-mocking.md) covers the testing patterns that section 4 (Code Review Red Flags) calls out as missing
- **Context usage** — [Module 02: Synchronization and Context](../02-concurrency/02-synchronization-and-context.md), section 3 provides the deep context.Context coverage for the context-related questions in sections 1–2
