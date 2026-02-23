# Module 03 Deep Dive: Advanced Go for Distributed Systems

This document goes deeper on the topics that distinguish a competent Go developer from one who can build and maintain distributed systems at Temporal's scale. You will not use every technique daily, but interviewers will probe these areas and Temporal's codebase is full of them.

---

## 1. Context Deep Dive

### The Context Tree

Every `context.Context` forms a tree. When you derive a child context, cancelling the parent cancels all children. This is the foundation of request-scoped resource management in Go.

```go
// Root context -- lives for the lifetime of the application
rootCtx := context.Background()

// Request-scoped context -- lives for one gRPC call
reqCtx, reqCancel := context.WithTimeout(rootCtx, 30*time.Second)
defer reqCancel()

// Sub-operation context -- tighter timeout for a database call
dbCtx, dbCancel := context.WithTimeout(reqCtx, 5*time.Second)
defer dbCancel()

// If reqCtx is cancelled (client disconnects), dbCtx is also cancelled.
// If dbCtx times out, reqCtx is NOT cancelled.
```

In TypeScript, this is conceptually like nested `AbortController`s, but Go contexts carry deadlines, cancellation signals, and values all in one object that threads through every function call.

### Context in gRPC

gRPC propagates context automatically. When a client sends a request with a deadline, the server receives a context that already has that deadline set.

```go
// Client side
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

resp, err := client.StartWorkflowExecution(ctx, req)
// The 10-second deadline is propagated to the server via gRPC metadata.
```

```go
// Server side
func (s *server) StartWorkflowExecution(
    ctx context.Context, // already has the client's deadline
    req *workflowservice.StartWorkflowExecutionRequest,
) (*workflowservice.StartWorkflowExecutionResponse, error) {
    // ctx.Deadline() returns the client's deadline
    // If the client disconnects, ctx is cancelled

    // Pass ctx down to every sub-operation
    result, err := s.store.CreateWorkflow(ctx, req)
    if err != nil {
        if errors.Is(err, context.DeadlineExceeded) {
            // The client's deadline was exceeded
            return nil, status.Error(codes.DeadlineExceeded, "operation timed out")
        }
        return nil, status.Errorf(codes.Internal, "failed: %v", err)
    }
    return result, nil
}
```

### Context Values: Use Sparingly

`context.WithValue` attaches key-value pairs to a context. It is useful for request-scoped metadata (request ID, authenticated user), but it should never be used for function parameters.

```go
// Define a custom key type to avoid collisions
type contextKey string

const (
    requestIDKey contextKey = "requestID"
    userKey      contextKey = "user"
)

func withRequestID(ctx context.Context, id string) context.Context {
    return context.WithValue(ctx, requestIDKey, id)
}

func requestIDFrom(ctx context.Context) string {
    id, _ := ctx.Value(requestIDKey).(string)
    return id
}
```

In TypeScript, this is like using `AsyncLocalStorage` from Node.js to thread request-scoped values through async call chains. The Go version is explicit -- you see it in every function signature.

**Context best practices (interview-critical):**
1. Always the first parameter, named `ctx`.
2. Never store a context in a struct field (exceptions exist but are rare).
3. Always `defer cancel()` derived contexts.
4. Check `ctx.Err()` before expensive operations in loops.
5. Do not pass `nil` context. Use `context.TODO()` as a placeholder if you must.
6. Do not use `context.WithValue` for data that should be function parameters.

### Context-Aware Loops

In long-running operations, check the context periodically:

```go
func processItems(ctx context.Context, items []Item) error {
    for i, item := range items {
        // Check context before each expensive operation
        if err := ctx.Err(); err != nil {
            return fmt.Errorf("cancelled after processing %d/%d items: %w", i, len(items), err)
        }
        if err := processItem(ctx, item); err != nil {
            return fmt.Errorf("processing item %d: %w", i, err)
        }
    }
    return nil
}
```

In Temporal's codebase, context checking is everywhere. Workflows can run for days or weeks. The server must be able to interrupt any operation when a context is cancelled (client disconnect, deployment, shutdown).

---

## 2. Testing Patterns

### Table-Driven Tests (The Go Standard)

In TypeScript, you might write separate `it()` blocks. In Go, table-driven tests are idiomatic:

```go
func TestParseWorkflowID(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    WorkflowID
        wantErr bool
    }{
        {
            name:  "valid simple ID",
            input: "my-workflow-123",
            want:  WorkflowID{Namespace: "default", ID: "my-workflow-123"},
        },
        {
            name:  "valid namespaced ID",
            input: "production/my-workflow-123",
            want:  WorkflowID{Namespace: "production", ID: "my-workflow-123"},
        },
        {
            name:    "empty string",
            input:   "",
            wantErr: true,
        },
        {
            name:    "too many slashes",
            input:   "a/b/c",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseWorkflowID(tt.input)

            if tt.wantErr {
                if err == nil {
                    t.Error("expected error, got nil")
                }
                return
            }

            if err != nil {
                t.Fatalf("unexpected error: %v", err)
            }

            if got != tt.want {
                t.Errorf("got %+v, want %+v", got, tt.want)
            }
        })
    }
}
```

Why this pattern matters:
- Each test case is a row in a table. Adding a new case is adding a struct literal.
- `t.Run` creates subtests, so failures show which case failed.
- The pattern scales to hundreds of cases without code duplication.

### Mocking with Interfaces

In TypeScript, you might use `jest.mock()` or dependency injection frameworks. In Go, mocking is done through interfaces. No frameworks needed.

```go
// The dependency (in production code)
type WorkflowStore interface {
    CreateWorkflow(ctx context.Context, req *CreateWorkflowRequest) (string, error)
    GetWorkflow(ctx context.Context, id string) (*Workflow, error)
    UpdateWorkflow(ctx context.Context, id string, update *WorkflowUpdate) error
}

// The mock (in test code)
type mockWorkflowStore struct {
    createFunc func(ctx context.Context, req *CreateWorkflowRequest) (string, error)
    getFunc    func(ctx context.Context, id string) (*Workflow, error)
    updateFunc func(ctx context.Context, id string, update *WorkflowUpdate) error
}

func (m *mockWorkflowStore) CreateWorkflow(ctx context.Context, req *CreateWorkflowRequest) (string, error) {
    if m.createFunc != nil {
        return m.createFunc(ctx, req)
    }
    return "", nil
}

func (m *mockWorkflowStore) GetWorkflow(ctx context.Context, id string) (*Workflow, error) {
    if m.getFunc != nil {
        return m.getFunc(ctx, id)
    }
    return nil, ErrNotFound
}

func (m *mockWorkflowStore) UpdateWorkflow(ctx context.Context, id string, update *WorkflowUpdate) error {
    if m.updateFunc != nil {
        return m.updateFunc(ctx, id, update)
    }
    return nil
}
```

This pattern gives you per-test control over what the mock returns:

```go
func TestStartWorkflow_DuplicateID(t *testing.T) {
    store := &mockWorkflowStore{
        createFunc: func(ctx context.Context, req *CreateWorkflowRequest) (string, error) {
            return "", ErrAlreadyExists
        },
    }
    svc := NewWorkflowService(store)

    _, err := svc.StartWorkflow(context.Background(), &StartWorkflowRequest{
        WorkflowID: "duplicate-id",
    })

    if !errors.Is(err, ErrAlreadyExists) {
        t.Errorf("expected ErrAlreadyExists, got %v", err)
    }
}
```

### HTTP Testing with `httptest`

Go's standard library includes `httptest` for testing HTTP handlers without starting a real server:

```go
func TestGetUserHandler(t *testing.T) {
    store := &mockStore{
        getFunc: func(ctx context.Context, id string) (*User, error) {
            if id == "123" {
                return &User{ID: "123", Name: "Alice"}, nil
            }
            return nil, ErrNotFound
        },
    }

    handler := NewUserHandler(store)

    t.Run("user found", func(t *testing.T) {
        req := httptest.NewRequest("GET", "/users/123", nil)
        req.SetPathValue("id", "123")
        rec := httptest.NewRecorder()

        handler.GetUser(rec, req)

        if rec.Code != http.StatusOK {
            t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
        }

        var user User
        json.NewDecoder(rec.Body).Decode(&user)
        if user.Name != "Alice" {
            t.Errorf("name = %q, want %q", user.Name, "Alice")
        }
    })

    t.Run("user not found", func(t *testing.T) {
        req := httptest.NewRequest("GET", "/users/999", nil)
        req.SetPathValue("id", "999")
        rec := httptest.NewRecorder()

        handler.GetUser(rec, req)

        if rec.Code != http.StatusNotFound {
            t.Errorf("status = %d, want %d", rec.Code, http.StatusNotFound)
        }
    })
}
```

In TypeScript, you might use `supertest`. Go's `httptest` serves the same purpose but is part of the standard library.

### Benchmarks with `testing.B`

```go
func BenchmarkParseWorkflowID(b *testing.B) {
    input := "production/my-workflow-123"
    for i := 0; i < b.N; i++ {
        ParseWorkflowID(input)
    }
}

// Run: go test -bench=BenchmarkParseWorkflowID -benchmem
// Output:
// BenchmarkParseWorkflowID-8    10000000    120 ns/op    48 B/op    2 allocs/op
```

The `-benchmem` flag reports allocations per operation. In systems code, reducing allocations matters. Temporal processes millions of workflow events; a function that allocates unnecessarily in a hot path creates GC pressure.

### Fuzzing with `testing.F`

Go 1.18 added native fuzzing:

```go
func FuzzParseWorkflowID(f *testing.F) {
    // Seed corpus
    f.Add("my-workflow")
    f.Add("namespace/workflow-id")
    f.Add("")
    f.Add("/")

    f.Fuzz(func(t *testing.T, input string) {
        result, err := ParseWorkflowID(input)
        if err != nil {
            return // invalid input is fine
        }
        // If parsing succeeded, verify invariants
        if result.ID == "" {
            t.Error("parsed successfully but ID is empty")
        }
    })
}

// Run: go test -fuzz=FuzzParseWorkflowID -fuzztime=30s
```

In TypeScript, you would use a library like `fast-check` for property-based testing. Go has it built in.

### Testing Concurrent Code: The Race Detector

Go's race detector is a compiler-instrumented tool that detects data races at runtime:

```bash
go test -race ./...
```

This catches bugs that are nearly impossible to find otherwise:

```go
// This has a data race
func TestConcurrentAccess(t *testing.T) {
    counter := 0
    var wg sync.WaitGroup

    for i := 0; i < 100; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            counter++ // DATA RACE: concurrent read/write without synchronization
        }()
    }
    wg.Wait()
}
```

The race detector will flag this. The fix is to use `sync.Mutex` or `atomic.AddInt64`.

**Interview tip:** "I would run the test suite with `-race` to catch data races" is a strong signal that you understand concurrent Go.

### Integration Tests with Build Tags

Separate integration tests from unit tests using build tags:

```go
//go:build integration

package store_test

import (
    "testing"
    "database/sql"
)

func TestPostgresStore_CreateUser(t *testing.T) {
    db, err := sql.Open("postgres", os.Getenv("TEST_DATABASE_URL"))
    if err != nil {
        t.Fatal(err)
    }
    defer db.Close()

    store := NewPostgresStore(db)
    // ... test against real database
}
```

```bash
# Run unit tests only
go test ./...

# Run integration tests
go test -tags=integration ./...
```

---

## 3. Production Go

### Structured Logging with `log/slog`

Go 1.21 added `log/slog` to the standard library. Before that, `zap` and `zerolog` were the standards. You should know `slog` since it is now the recommended approach.

```go
import "log/slog"

func main() {
    // JSON output for production
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)

    slog.Info("server starting",
        "port", 8080,
        "version", "1.2.3",
    )
    // Output: {"time":"...","level":"INFO","msg":"server starting","port":8080,"version":"1.2.3"}
}
```

In TypeScript, this is like using `winston` or `pino` with structured JSON output. Same concept, different API.

**Adding context to logs:**

```go
func handleRequest(ctx context.Context, req *Request) error {
    logger := slog.With(
        "request_id", requestIDFrom(ctx),
        "workflow_id", req.WorkflowID,
    )

    logger.Info("processing request")

    result, err := processWorkflow(ctx, req)
    if err != nil {
        logger.Error("workflow processing failed",
            "error", err,
            "duration", time.Since(start),
        )
        return err
    }

    logger.Info("request processed",
        "duration", time.Since(start),
        "result_count", len(result.Items),
    )
    return nil
}
```

### Graceful Shutdown

In Node.js, you handle `SIGTERM` and drain connections. In Go, the pattern uses `os/signal` and `context.WithCancel`:

```go
func main() {
    // Create a root context that cancels on SIGTERM/SIGINT
    ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
    defer stop()

    // Start database
    db, err := openDB(os.Getenv("DATABASE_URL"))
    if err != nil {
        slog.Error("failed to open database", "error", err)
        os.Exit(1)
    }

    // Start gRPC server
    grpcServer := grpc.NewServer()
    registerServices(grpcServer, db)

    lis, err := net.Listen("tcp", ":7233")
    if err != nil {
        slog.Error("failed to listen", "error", err)
        os.Exit(1)
    }

    // Run server in a goroutine
    go func() {
        slog.Info("server starting", "addr", lis.Addr())
        if err := grpcServer.Serve(lis); err != nil {
            slog.Error("server failed", "error", err)
        }
    }()

    // Block until shutdown signal
    <-ctx.Done()
    slog.Info("shutdown signal received")

    // Graceful shutdown with timeout
    shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer shutdownCancel()

    // Stop accepting new connections, finish in-flight requests
    grpcServer.GracefulStop()

    // Close database
    if err := db.Close(); err != nil {
        slog.Error("error closing database", "error", err)
    }

    _ = shutdownCtx // used if we had HTTP server: server.Shutdown(shutdownCtx)
    slog.Info("server stopped")
}
```

This is a pattern you should be able to write from memory. Temporal's services need graceful shutdown to drain in-flight workflow tasks.

### Health Checks

```go
// Liveness: "is the process alive?"
func handleLiveness(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte("ok"))
}

// Readiness: "is the service ready to handle traffic?"
func handleReadiness(db *sql.DB) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
        defer cancel()

        if err := db.PingContext(ctx); err != nil {
            http.Error(w, "database unavailable", http.StatusServiceUnavailable)
            return
        }
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("ready"))
    }
}
```

In Kubernetes (where Temporal Cloud runs), liveness probes restart crashed containers and readiness probes remove unhealthy pods from load balancers. Knowing this distinction matters.

---

## 4. Go in Large Codebases

### Navigating Temporal's Codebase

Temporal's server repository (`temporal/temporal` on GitHub) is large. Knowing where to look:

```
temporal/
  api/          # protobuf definitions
  cmd/          # entry points (server binary)
  service/
    frontend/   # gRPC API handlers (what clients talk to)
    history/    # workflow execution engine (the core)
    matching/   # task queue matching (assigns tasks to workers)
    worker/     # internal system workflows
  common/       # shared utilities, types
  internal/     # internal packages
  tools/        # CLI tools
```

The `history` service is where most of the interesting logic lives: state machines for workflow execution, event sourcing, timer management. The `frontend` service is the gRPC gateway. The `matching` service is a sophisticated task router.

### Package Organization

Good Go package structure follows domain boundaries, not technical layers:

```
// Bad -- organized by technical layer (Java-style)
models/
  user.go
  order.go
services/
  user_service.go
  order_service.go
repositories/
  user_repo.go
  order_repo.go

// Good -- organized by domain (Go-style)
user/
  user.go          // types + service + store interface
  postgres.go      // postgres implementation of store
  user_test.go
order/
  order.go
  postgres.go
  order_test.go
```

In the first layout, a change to "users" touches three packages. In the second, it touches one. The Go proverb: "A little copying is better than a little dependency."

### Code Generation

Go uses code generation heavily. Key tools:

```bash
# Protocol buffers (gRPC)
protoc --go_out=. --go-grpc_out=. service.proto

# sqlc (type-safe SQL)
sqlc generate

# Wire (dependency injection)
wire ./...

# go generate (runs directives in source files)
go generate ./...
```

In TypeScript, you might use `graphql-codegen` or Prisma's generator. Same idea: generate type-safe code from schemas.

### Dependency Injection: Functional Options

Go does not have DI frameworks like TypeScript's `tsyringe` or NestJS. Instead, it uses constructor injection and the functional options pattern:

```go
type Server struct {
    addr         string
    readTimeout  time.Duration
    writeTimeout time.Duration
    logger       *slog.Logger
    store        Store
}

type Option func(*Server)

func WithAddr(addr string) Option {
    return func(s *Server) { s.addr = addr }
}

func WithTimeout(read, write time.Duration) Option {
    return func(s *Server) {
        s.readTimeout = read
        s.writeTimeout = write
    }
}

func WithLogger(logger *slog.Logger) Option {
    return func(s *Server) { s.logger = logger }
}

func NewServer(store Store, opts ...Option) *Server {
    s := &Server{
        addr:         ":8080",         // defaults
        readTimeout:  10 * time.Second,
        writeTimeout: 10 * time.Second,
        logger:       slog.Default(),
        store:        store,
    }
    for _, opt := range opts {
        opt(s)
    }
    return s
}

// Usage
server := NewServer(myStore,
    WithAddr(":9090"),
    WithTimeout(30*time.Second, 30*time.Second),
    WithLogger(customLogger),
)
```

This pattern is all over Temporal's codebase. It provides sensible defaults with optional overrides, and it is extensible without breaking existing callers.

---

## 5. Performance Patterns

### Stack vs Heap Allocation

In TypeScript/V8, you do not think about where objects live. In Go, understanding stack vs heap matters for hot paths.

```go
// Stack allocation -- fast, freed automatically when function returns
func process() {
    x := 42           // stays on stack
    s := "hello"      // stays on stack (string header)
    u := User{ID: 1}  // stays on stack IF it doesn't escape
}

// Heap allocation -- slower, requires garbage collection
func newUser() *User {
    u := User{ID: 1}
    return &u  // u escapes to heap because its address is returned
}
```

Check what escapes:

```bash
go build -gcflags='-m' ./...
```

### Reducing Allocations

**Pre-allocated slices:**

```go
// Bad -- grows the slice multiple times, each growth allocates
var results []Result
for _, item := range items {
    results = append(results, process(item))
}

// Good -- allocate once
results := make([]Result, 0, len(items))
for _, item := range items {
    results = append(results, process(item))
}
```

**sync.Pool for reusable objects:**

```go
var bufferPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func processRequest(data []byte) string {
    buf := bufferPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufferPool.Put(buf)
    }()

    buf.Write(data)
    // ... process ...
    return buf.String()
}
```

`sync.Pool` is used in Temporal for reusing buffers in the serialization/deserialization hot path. It reduces GC pressure by recycling objects instead of creating new ones.

**strings.Builder for concatenation:**

```go
// Bad -- each + creates a new string
s := ""
for _, item := range items {
    s += item.Name + ", "
}

// Good -- single allocation
var b strings.Builder
for i, item := range items {
    if i > 0 {
        b.WriteString(", ")
    }
    b.WriteString(item.Name)
}
s := b.String()
```

### Profiling with pprof

Go has built-in profiling. Add a few lines and you get CPU, memory, goroutine, and mutex profiles:

```go
import _ "net/http/pprof"

func main() {
    // Start pprof server on a separate port
    go func() {
        log.Println(http.ListenAndServe(":6060", nil))
    }()

    // ... rest of your application
}
```

```bash
# CPU profile (30 seconds)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Memory profile (heap)
go tool pprof http://localhost:6060/debug/pprof/heap

# Goroutine dump (find goroutine leaks)
go tool pprof http://localhost:6060/debug/pprof/goroutine

# Mutex contention
go tool pprof http://localhost:6060/debug/pprof/mutex

# Block profile (find where goroutines block)
go tool pprof http://localhost:6060/debug/pprof/block
```

Inside the pprof interactive shell:

```
(pprof) top10          # top 10 functions by CPU/memory
(pprof) list funcName  # source-annotated view of a function
(pprof) web            # open flame graph in browser
```

**Interview scenario:** "Our service has high latency on the P99. How would you debug it?"

Answer: "I would start with a CPU profile via pprof to identify hot functions, then check the goroutine profile to see if goroutines are blocked waiting on locks or channels. If it looks like GC pressure, I would take a heap profile and look for functions with high allocation rates. The mutex profile would reveal lock contention."

### Common Bottlenecks in Go Services

1. **GC pressure from excessive allocations.** Fix: pre-allocate slices, use `sync.Pool`, avoid unnecessary `interface{}` conversions.

2. **Lock contention on shared state.** Fix: shard the data, use `sync.RWMutex` instead of `sync.Mutex`, or redesign to use channels.

3. **Goroutine leaks.** Fix: always select on `ctx.Done()`, always close channels, use pprof goroutine profiles to identify stuck goroutines.

4. **Connection pool exhaustion.** Fix: set appropriate `MaxOpenConns`, use context timeouts on queries, close `rows` properly.

5. **Serialization overhead.** Fix: use code-generated serializers (protobuf is already fast), reduce the amount of data serialized, cache serialized forms.

These are not abstract concerns. Temporal's server processes thousands of workflow events per second. Every allocation in a hot path, every lock that is held too long, every goroutine that leaks -- they all show up at scale.

---

## 6. Concurrency Patterns for Distributed Systems

### Long-Polling with Context

Temporal's task queues use long-polling: a worker sends a request and the server holds it open until a task is available or the timeout expires.

```go
func (s *matchingService) PollWorkflowTaskQueue(
    ctx context.Context,
    req *matchingservice.PollWorkflowTaskQueueRequest,
) (*matchingservice.PollWorkflowTaskQueueResponse, error) {
    // The client sets a long timeout (e.g., 60 seconds)
    // We wait until a task is available or the context expires

    taskCh := s.taskQueue.Subscribe(req.GetTaskQueue())
    defer s.taskQueue.Unsubscribe(taskCh)

    select {
    case task := <-taskCh:
        return &matchingservice.PollWorkflowTaskQueueResponse{
            Task: task,
        }, nil
    case <-ctx.Done():
        // Client disconnected or timeout -- this is normal, not an error
        return &matchingservice.PollWorkflowTaskQueueResponse{}, nil
    }
}
```

### Coordination with Channels and Context

A pattern from Temporal's internals: coordinating multiple goroutines that watch for different conditions.

```go
func (e *workflowExecutor) executeWithTimers(ctx context.Context, workflow *Workflow) error {
    timerCh := make(chan TimerFired, 1)
    signalCh := make(chan Signal, 1)
    activityCh := make(chan ActivityResult, 1)

    // Start watchers
    go e.watchTimers(ctx, workflow.ID, timerCh)
    go e.watchSignals(ctx, workflow.ID, signalCh)
    go e.watchActivities(ctx, workflow.ID, activityCh)

    for {
        select {
        case timer := <-timerCh:
            if err := e.handleTimerFired(ctx, workflow, timer); err != nil {
                return fmt.Errorf("handling timer: %w", err)
            }
        case signal := <-signalCh:
            if err := e.handleSignal(ctx, workflow, signal); err != nil {
                return fmt.Errorf("handling signal: %w", err)
            }
        case result := <-activityCh:
            if err := e.handleActivityResult(ctx, workflow, result); err != nil {
                return fmt.Errorf("handling activity result: %w", err)
            }
        case <-ctx.Done():
            return ctx.Err()
        }
    }
}
```

This is the kind of code you might be asked to write or reason about in a Temporal interview. The `select` statement multiplexes multiple event sources. Context cancellation provides the shutdown mechanism. Channels provide type-safe communication between goroutines.

### Leader Election Pattern

In distributed systems, only one instance should perform certain operations. A simplified leader election pattern:

```go
type LeaderElector struct {
    store  LeaderStore
    nodeID string
    ttl    time.Duration
}

func (le *LeaderElector) Run(ctx context.Context, onLeader func(ctx context.Context)) {
    for {
        select {
        case <-ctx.Done():
            return
        default:
        }

        // Try to acquire leadership
        leaderCtx, err := le.tryAcquire(ctx)
        if err != nil {
            slog.Warn("failed to acquire leadership", "error", err)
            time.Sleep(le.ttl / 2)
            continue
        }

        if leaderCtx != nil {
            slog.Info("acquired leadership", "node", le.nodeID)
            onLeader(leaderCtx) // blocks until leadership is lost
            slog.Info("lost leadership", "node", le.nodeID)
        }

        time.Sleep(le.ttl / 2)
    }
}
```

This combines context propagation, goroutine lifecycle management, and retry logic -- all core Temporal concerns.
