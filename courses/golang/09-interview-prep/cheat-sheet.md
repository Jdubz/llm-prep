# Module 09: Cheat Sheet — Interview Prep

## Top 20 Go Questions with One-Line Answers

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
| 18 | How to detect races? | `go test -race` or `go run -race` enables race detector (2-10x slower, dev/CI only) |
| 19 | `sync.WaitGroup` usage? | `Add` before goroutine, `Done` in goroutine (defer), `Wait` blocks until counter zero |
| 20 | What is `embed`? | Compile static files into binary via `//go:embed`. Returns `embed.FS` implementing `fs.FS` |

---

## Concurrency Bug Patterns

| Bug | Symptom | Fix |
|-----|---------|-----|
| Goroutine leak | Memory grows, goroutine count increases | Add context cancellation, use `goleak` in tests |
| Channel deadlock | `fatal error: all goroutines are asleep` | Ensure every send has a receiver (or use buffered) |
| Data race | Flaky tests, corrupted data | `sync.Mutex`, `atomic`, or channel-based ownership |
| Concurrent map write | `fatal error: concurrent map writes` | `sync.RWMutex` or `sync.Map` |
| Premature close | `send on closed channel` panic | Only the sender closes; close once with `sync.Once` |
| Lost wakeup | Goroutine never proceeds | Use `sync.Cond` correctly or prefer channels |
| Mutex copy | Lock has no effect | Never copy a `sync.Mutex` (pass by pointer, use `go vet`) |
| Context leak | Background goroutines outlive request | Always call `cancel()` from `context.WithCancel` |

---

## System Design Template for Go

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

## Code Review Red Flags

| Red Flag | Why It Matters | Fix |
|----------|---------------|-----|
| `go func()` without `sync.WaitGroup` | Goroutine leak risk | Track with WaitGroup or errgroup |
| No context parameter on I/O functions | Cannot cancel or timeout | Accept `context.Context` as first param |
| `interface{}` / `any` everywhere | Loses type safety | Use generics or specific interfaces |
| Error ignored with `_` | Silent failures | Handle or explicitly document why ignored |
| Global mutable state | Race conditions, hard to test | Pass dependencies explicitly |
| `time.Sleep` in tests | Flaky, slow tests | Use channels, contexts, or `time.After` |
| String concatenation in loop | O(n^2) allocations | Use `strings.Builder` |
| `panic` for error handling | Crashes the program | Return errors; panic is for programmer bugs |
| Unbounded goroutine creation | OOM under load | Use worker pool with bounded concurrency |
| Missing `defer mu.Unlock()` | Deadlock on error path | Always `defer` the unlock after lock |
| `sync.Mutex` as value field | Mutex copied = broken | Use pointer or never copy the struct |
| Channel without `select` + context | Blocks forever if context cancelled | Always select on both channel and `ctx.Done()` |

---

## Live Coding Setup Template

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

## "Idiomatic Go" Rules Quick Reference

| Rule | Example |
|------|---------|
| Accept interfaces, return structs | `func New(r io.Reader) *Parser` |
| Error strings are lowercase, no punctuation | `fmt.Errorf("opening file: %w", err)` |
| Use `MixedCaps`, not `snake_case` | `userID`, not `user_id` |
| Exported = uppercase, unexported = lowercase | `func Parse()` vs `func parse()` |
| Receiver name is 1-2 letters, not `this`/`self` | `func (s *Server) Start()` |
| Return early, avoid deep nesting | `if err != nil { return err }` then happy path |
| Context is always the first parameter | `func Get(ctx context.Context, id int) error` |
| Do not stutter: `user.User` is bad | `user.Profile` instead |
| Interfaces are named with -er suffix | `Reader`, `Writer`, `Closer`, `Handler` |
| Prefer small interfaces (1-3 methods) | `io.Reader` has 1 method |
| Zero values should be useful | `var buf bytes.Buffer` works without init |
| Do not panic in library code | Return errors; let the caller decide |
| Wrap errors with context | `fmt.Errorf("getting user %d: %w", id, err)` |
| Use `gofmt` / `goimports` — no exceptions | `gofmt -w .` |
| Table-driven tests | `tests := []struct{ name string; ... }` |
| Test file lives next to source | `user.go` and `user_test.go` in same directory |
