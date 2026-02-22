# Module 09: Deep Dive — Interview Prep

## Staff-Level Go Discussions

These are not coding questions. These are the discussions that happen in staff/principal engineer interviews where the interviewer wants to understand your judgment about technology choices and system architecture.

### Choosing Go vs Other Languages

**When Go is the right choice:**
- Network services (HTTP APIs, gRPC services, proxies)
- CLI tools (single binary distribution, fast startup)
- Infrastructure tooling (Kubernetes, Docker, Terraform are all Go)
- High-concurrency workloads where goroutines shine
- Teams that value simplicity and readability over expressiveness
- Microservices where deployment simplicity (single binary) matters

**When Go is not the best choice:**
- Heavy data processing/ML (Python ecosystem is unmatched)
- GUI applications (Go's GUI story is weak)
- Rapid prototyping where TypeScript/Python iteration speed wins
- Projects requiring advanced type system features (Rust, Haskell)
- Games (Rust, C++, C# have better ecosystems)

**How to frame this in an interview:** "I would choose Go for this service because it is a network-bound API that needs to handle thousands of concurrent connections. Go's goroutine model gives us lightweight concurrency without callback complexity. The single binary deployment simplifies our Docker images and CI pipeline. If this were a data pipeline with heavy numerical computation, I would lean toward Python. If we needed memory safety guarantees without a garbage collector, Rust."

### Go in Microservices Architecture

**Advantages:**
- Small, fast Docker images (10-20MB distroless)
- Fast startup (milliseconds, not seconds)
- Low memory footprint per service
- Strong stdlib for HTTP/gRPC
- Excellent cross-compilation for multi-arch deployments

**Challenges:**
- No shared runtime like JVM for polyglot services
- Less mature ORM story than Java/TypeScript
- Error handling verbosity in handler code
- Generics are still young (compared to Java/C# generics)

**Architecture patterns that work well in Go:**
- Service mesh with gRPC (Go's gRPC library is first-class)
- Event-driven services with NATS or Kafka
- API gateways and reverse proxies
- Sidecar patterns (like Envoy, written in C++, but Go sidecars are common)

### Go for CLI Tools vs Services

| Aspect | CLI Tools | Services |
|--------|-----------|----------|
| Lifecycle | Short-lived | Long-lived |
| Concurrency | Limited | Core concern |
| Error handling | Print and exit | Return and propagate |
| Configuration | Flags + env | Env + config files |
| Testing | `os/exec` based | HTTP/gRPC clients |
| Distribution | Binary downloads | Container images |
| State | Filesystem | Database + cache |
| Signal handling | Rarely needed | Critical for graceful shutdown |

### Contributing to the Go Standard Library

Discussion points that show depth:
- The Go proposal process (GitHub issues with the "Proposal" label)
- The standard library's stability guarantee (Go 1 compatibility promise)
- Why the stdlib is conservative about adding features
- Examples: `slog` took years from proposal to inclusion
- The `x/` experiment packages as a staging ground

### Go Module Ecosystem Health

Talking points:
- `pkg.go.dev` as the discovery and documentation platform
- Module proxy (`proxy.golang.org`) for reliable dependency fetching
- Checksum database (`sum.golang.org`) for supply chain security
- Minimum version selection (MVS) — Go's unique approach to dependency resolution
- The "fewer, larger" library philosophy vs npm's "many small packages"
- Notable ecosystem gaps: mature GUI, ML/AI, office document processing

---

## Advanced Gotchas Collection

### Loop Variable Capture (Fixed in Go 1.22)

This was one of Go's most notorious footguns. Before Go 1.22:

```go
// BEFORE Go 1.22: BUG
funcs := make([]func(), 5)
for i := 0; i < 5; i++ {
    funcs[i] = func() { fmt.Println(i) }  // All print 5!
}
// All closures capture the same variable i, which ends at 5

// The old fix: shadow the variable
for i := 0; i < 5; i++ {
    i := i  // Shadow — each closure gets its own copy
    funcs[i] = func() { fmt.Println(i) }
}

// Go 1.22+: Each iteration creates a new variable. The bug is fixed.
// The shadowing trick is no longer needed.
```

**Interview tip:** Mention that you know this was fixed in Go 1.22, but that you understand why the fix was needed. Many older codebases still have the `i := i` shadow pattern. It does no harm but is no longer necessary.

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

// Iteration order is DELIBERATELY randomized
// Two consecutive range loops may produce different orders
for k, v := range m {
    fmt.Println(k, v)  // Order varies between runs
}

// If you need deterministic order:
keys := make([]string, 0, len(m))
for k := range m {
    keys = append(keys, k)
}
slices.Sort(keys)
for _, k := range keys {
    fmt.Println(k, m[k])
}
```

**Why:** Go intentionally randomizes map iteration to prevent developers from depending on a specific order. This is a design decision, not an implementation detail.

### Struct Comparison Rules

```go
// Structs are comparable if ALL fields are comparable
type Point struct{ X, Y int }
p1 := Point{1, 2}
p2 := Point{1, 2}
fmt.Println(p1 == p2)  // true — all fields are comparable

// Structs with non-comparable fields cannot use ==
type Data struct {
    Values []int  // Slices are not comparable
}
// d1 == d2  // Compile error!
// Use reflect.DeepEqual(d1, d2) or write custom comparison

// Maps and slices are never comparable with ==
// Functions are never comparable with ==
// Interfaces are comparable (compares type + value)
```

### Interface Satisfaction at Compile Time

Go satisfies interfaces implicitly — you never write `implements`. But you can verify at compile time:

```go
// Compile-time assertion that *MyHandler implements http.Handler
var _ http.Handler = (*MyHandler)(nil)

// If MyHandler is missing the ServeHTTP method, this line
// produces a compile error. The _ discards the value — this
// is a zero-cost check.

// Common pattern in library code:
var _ io.ReadWriteCloser = (*MyBuffer)(nil)
var _ fmt.Stringer = (*Status)(nil)
var _ error = (*AppError)(nil)
```

### String and Byte Slice Conversions

```go
// Strings are immutable; byte slices are mutable
s := "hello"
b := []byte(s)    // Copies data — O(n)
s2 := string(b)   // Copies data — O(n)

// Avoid unnecessary conversions in hot paths
// BAD: double conversion
if string(body) == "expected" { ... }

// BETTER: compare bytes directly
if bytes.Equal(body, []byte("expected")) { ... }

// Go 1.20+: unsafe string/bytes conversion (zero-copy, use carefully)
import "unsafe"
s = unsafe.String(&b[0], len(b))  // No copy, but b must not be modified
```

### Nil Slice vs Empty Slice

```go
var s1 []int           // nil slice — nil, len=0, cap=0
s2 := []int{}          // empty slice — not nil, len=0, cap=0
s3 := make([]int, 0)   // empty slice — not nil, len=0, cap=0

fmt.Println(s1 == nil)  // true
fmt.Println(s2 == nil)  // false
fmt.Println(s3 == nil)  // false

// JSON encoding difference:
json.Marshal(s1)  // "null"
json.Marshal(s2)  // "[]"

// Most code treats them identically:
len(s1) == 0  // true
len(s2) == 0  // true
append(s1, 1)  // Works fine
append(s2, 1)  // Works fine

// Gotcha: When returning from an API, prefer empty slice over nil
// to avoid "null" in JSON responses
```

### Method Set Rules

Understanding method sets is critical for interface satisfaction:

```go
// Value methods can be called on both values and pointers
// Pointer methods can only be called on pointers (or addressable values)

type Counter struct{ n int }

func (c Counter) Value() int    { return c.n }  // Value receiver
func (c *Counter) Increment()   { c.n++ }       // Pointer receiver

// Method set of Counter (value):      { Value }
// Method set of *Counter (pointer):   { Value, Increment }

type Incrementer interface {
    Increment()
}

var c Counter
var _ Incrementer = c   // Compile error: Counter does not implement Incrementer
var _ Incrementer = &c  // OK: *Counter implements Incrementer
```

**Why this matters in interviews:** When someone stores a value type in an interface and wonders why the pointer method is not available, this is the reason. The method set of a value type does not include pointer receiver methods.

### Goroutine Scheduling Nuances

```go
// Goroutines are cooperatively scheduled at certain points:
// - Channel operations
// - System calls
// - Function calls (preemption points since Go 1.14)
// - Garbage collection

// Before Go 1.14, a tight loop with no function calls could
// starve other goroutines:
go func() {
    for {
        // Tight loop — in Go <1.14 this could starve the scheduler
        // Go 1.14+ has asynchronous preemption via signals
    }
}()

// GOMAXPROCS determines how many OS threads run goroutines simultaneously
// Default: number of CPU cores
// In containers: should match CPU limit (use automaxprocs)
```

### The `singleflight` Pattern

Prevents duplicate work for concurrent identical requests — essential for cache stampede prevention:

```go
import "golang.org/x/sync/singleflight"

var group singleflight.Group

func GetUser(ctx context.Context, id string) (*User, error) {
    // If 100 goroutines request the same user simultaneously,
    // only one database query executes. The other 99 wait and
    // share the result.
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

## "Why Go" Narratives

### For Companies Already Using Go

"I am drawn to Go because of its emphasis on simplicity and maintainability. In my TypeScript experience, I have seen codebases become difficult to maintain as they grow — complex type hierarchies, deeply nested generics, and heavyweight frameworks. Go's philosophy of keeping things simple and explicit resonates with how I think about building systems that teams can maintain over years. I have found that Go's opinionated style — `gofmt`, explicit error handling, minimal language surface area — means less time debating style and more time solving problems."

### For Companies Transitioning to Go

"I see Go as a natural evolution for teams building backend services. Coming from TypeScript, I appreciate that Go addresses several pain points I have experienced: deployment complexity (single binary vs node_modules), runtime performance (compiled vs interpreted), and concurrency (goroutines vs async/await callback chains). I am not abandoning TypeScript — it is still my choice for frontend and rapid prototyping. But for production backend services that need to handle high concurrency with low latency, Go is the better tool."

### For Infrastructure Companies

"The infrastructure ecosystem has standardized on Go — Kubernetes, Docker, Terraform, Prometheus, Grafana, etcd. This is not accidental. Go's static binary compilation means tools can be distributed without runtime dependencies. Its concurrency model handles the parallelism that infrastructure tools need. Its fast compilation enables quick iteration. I want to work in Go because the infrastructure problems I am most interested in solving are best served by this language."

### Common Follow-Up: "What Do You Miss from TypeScript?"

Be honest. Good answers include:
- "Union types and discriminated unions — Go's error handling is explicit but verbose"
- "The npm ecosystem density — Go's library ecosystem is smaller but more curated"
- "Generics expressiveness — TypeScript's mapped types and conditional types are more powerful"
- "Hot reload during development — Go requires recompilation (though it is fast)"
- "Decorators for cross-cutting concerns — Go uses explicit middleware instead"

### Common Follow-Up: "What Do You Prefer About Go?"

- "The simplicity — there is usually one obvious way to do things"
- "Single binary deployment — no runtime, no dependencies, no node_modules"
- "Built-in concurrency primitives that are first-class, not bolted on"
- "The standard library is genuinely good — I rarely need third-party packages for basic HTTP, JSON, testing"
- "gofmt ending all style debates"
- "Compilation speed — the feedback loop is nearly instant"
- "The tooling: go vet, go test -race, pprof, all built in"
