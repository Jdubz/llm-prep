# 01 – Generics and Code Generation

Go's abstraction story is deliberately simpler than TypeScript's rich type toolkit, but that does not mean it lacks power. The philosophy is different: TypeScript asks "how can the type system express this perfectly?" Go asks "how can we keep this simple enough that anyone can read it in six months?"

---

## 1. Generics (Go 1.18+)

### Type Parameters

Before Go 1.18, you had two options for generic-like code: interfaces (runtime polymorphism) or code generation (compile-time duplication). Generics provide compile-time polymorphism without duplication.

```go
// Before generics: separate functions or interface{}
func ContainsInt(slice []int, target int) bool { ... }
func ContainsString(slice []string, target string) bool { ... }

// With generics: one function
func Contains[T comparable](slice []T, target T) bool {
    for _, v := range slice {
        if v == target {
            return true
        }
    }
    return false
}

// Usage — type is inferred
Contains([]int{1, 2, 3}, 2)       // true
Contains([]string{"a", "b"}, "c") // false
```

TypeScript parallel: Go's `[T comparable]` is like TypeScript's `<T extends { equals(other: T): boolean }>`, except `comparable` is a built-in constraint meaning the type supports `==` and `!=`.

### Generics Syntax Reference

```go
// Function with type parameter
func Map[T any, U any](s []T, fn func(T) U) []U

// Struct with type parameter
type Set[T comparable] struct { items map[T]struct{} }

// Method on generic type
func (s *Set[T]) Add(v T) { s.items[v] = struct{}{} }

// Interface as constraint
type Number interface {
    ~int | ~int8 | ~int16 | ~int32 | ~int64 |
    ~float32 | ~float64
}

// Multiple type parameters
func Zip[A any, B any](as []A, bs []B) []Pair[A, B]

// Type inference — usually no need to specify types explicitly
result := Map(users, func(u User) string { return u.Name })
```

### Constraints and Type Sets

```go
// Built-in constraints
// comparable — supports == and !=
// any       — alias for interface{}, no constraints

// Custom constraints using type sets
type Number interface {
    ~int | ~int8 | ~int16 | ~int32 | ~int64 |
    ~uint | ~uint8 | ~uint16 | ~uint32 | ~uint64 |
    ~float32 | ~float64
}

func Sum[T Number](values []T) T {
    var total T
    for _, v := range values {
        total += v
    }
    return total
}

// ~ means "underlying type" — allows named types
type Celsius float64
Sum([]Celsius{20.0, 22.5, 19.3}) // Works because ~float64 matches Celsius
```

```go
import "golang.org/x/exp/constraints"

func Max[T constraints.Ordered](a, b T) T {
    if a > b {
        return a
    }
    return b
}
```

### Constraint Examples

| Constraint | Meaning | Use Case |
|-----------|---------|----------|
| `any` | No restriction (alias for `interface{}`) | Generic containers |
| `comparable` | Supports `==` and `!=` | Map keys, set elements |
| `constraints.Ordered` | Supports `<`, `>`, `<=`, `>=` | Sorting, min/max |
| `~int \| ~float64` | Underlying type is int or float64 | Arithmetic operations |
| `interface{ Len() int }` | Must have `Len()` method | Sized collections |
| `fmt.Stringer` | Must have `String() string` | Display/logging |

### Generic Data Structures

```go
// Set implementation
type Set[T comparable] struct {
    items map[T]struct{}
}

func NewSet[T comparable](values ...T) *Set[T] {
    s := &Set[T]{items: make(map[T]struct{})}
    for _, v := range values {
        s.Add(v)
    }
    return s
}

func (s *Set[T]) Add(v T)           { s.items[v] = struct{}{} }
func (s *Set[T]) Contains(v T) bool { _, ok := s.items[v]; return ok }
func (s *Set[T]) Remove(v T)        { delete(s.items, v) }
func (s *Set[T]) Len() int          { return len(s.items) }

func (s *Set[T]) Values() []T {
    result := make([]T, 0, len(s.items))
    for k := range s.items {
        result = append(result, k)
    }
    return result
}
```

```go
// Result type (like Rust's Result<T, E>)
type Result[T any] struct {
    value T
    err   error
}

func Ok[T any](v T) Result[T]       { return Result[T]{value: v} }
func Err[T any](err error) Result[T] { return Result[T]{err: err} }

func (r Result[T]) Unwrap() (T, error) { return r.value, r.err }
func (r Result[T]) IsOk() bool         { return r.err == nil }

func (r Result[T]) Map(fn func(T) T) Result[T] {
    if r.err != nil {
        return r
    }
    return Ok(fn(r.value))
}
```

### Generic Utility Functions

The `slices` package (standard library since Go 1.21) provides many of these, but understanding the pattern matters:

```go
// Map — transform each element
func Map[T any, U any](slice []T, fn func(T) U) []U {
    result := make([]U, len(slice))
    for i, v := range slice {
        result[i] = fn(v)
    }
    return result
}

// Filter — keep elements matching predicate
func Filter[T any](slice []T, fn func(T) bool) []T {
    var result []T
    for _, v := range slice {
        if fn(v) {
            result = append(result, v)
        }
    }
    return result
}

// Reduce — fold elements into a single value
func Reduce[T any, U any](slice []T, initial U, fn func(U, T) U) U {
    result := initial
    for _, v := range slice {
        result = fn(result, v)
    }
    return result
}

// Usage
names := Map(users, func(u User) string { return u.Name })
active := Filter(users, func(u User) bool { return u.Active })
totalAge := Reduce(users, 0, func(sum int, u User) int { return sum + u.Age })
```

### Type-Safe Event Systems with Generics

```go
type Event[T any] struct {
    Topic     string
    Payload   T
    Timestamp time.Time
}

type Handler[T any] func(Event[T]) error

type Bus[T any] struct {
    mu       sync.RWMutex
    handlers []Handler[T]
}

func NewBus[T any]() *Bus[T] { return &Bus[T]{} }

func (b *Bus[T]) Subscribe(h Handler[T]) {
    b.mu.Lock()
    defer b.mu.Unlock()
    b.handlers = append(b.handlers, h)
}

func (b *Bus[T]) Publish(topic string, payload T) error {
    b.mu.RLock()
    handlers := make([]Handler[T], len(b.handlers))
    copy(handlers, b.handlers)
    b.mu.RUnlock()

    event := Event[T]{Topic: topic, Payload: payload, Timestamp: time.Now()}

    var errs []error
    for _, h := range handlers {
        if err := h(event); err != nil {
            errs = append(errs, err)
        }
    }
    return errors.Join(errs...)
}

// Usage — compiler enforces payload types
type OrderCreated struct { OrderID string; Total float64 }

orderBus := NewBus[OrderCreated]()
orderBus.Subscribe(func(e Event[OrderCreated]) error {
    slog.Info("order created", "id", e.Payload.OrderID)
    return nil
})
// This would NOT compile — type mismatch:
// orderBus.Subscribe(func(e Event[PaymentReceived]) error { ... })
```

### When to Use Generics vs Interfaces vs Code Generation

| Approach | Use When | Example |
|----------|----------|---------|
| Generics | Same logic, different types, type safety needed | `Contains[T]`, `Map[T,U]`, `Set[T]` |
| Interfaces | Different behavior, polymorphism needed | `io.Reader`, `http.Handler` |
| Code generation | Complex type-specific code | protobuf, mocks, ORM models |
| `any` (interface{}) | Truly dynamic data, JSON-like | `map[string]any` for config |

**Rule from the Go team:** "Do not use generics to replace interfaces. Use generics when you are writing the same code for multiple types and the algorithm does not depend on the type's behavior, only its identity."

---

## 2. Code Generation

### `go generate`

Go's approach to metaprogramming is code generation, not macros or decorators. The `go generate` command runs arbitrary commands specified in source file comments:

```go
//go:generate stringer -type=Status
//go:generate mockgen -source=repository.go -destination=mock_repository.go
//go:generate sqlc generate
//go:generate protoc --go_out=. --go-grpc_out=. api/service.proto
```

Run all generators: `go generate ./...`

### Stringer for Enums

Go does not have true enums. The `stringer` tool generates `String()` methods for `iota` constants:

```go
//go:generate stringer -type=Status

type Status int

const (
    StatusPending  Status = iota  // "Pending"
    StatusActive                   // "Active"
    StatusInactive                 // "Inactive"
)

// After running go generate, you get:
// func (s Status) String() string { ... }
// StatusPending.String() returns "Pending"
```

### Code Generation Tool Reference

| Tool | Command | Generates |
|------|---------|-----------|
| stringer | `go generate ./...` | `String()` methods for iota constants |
| mockgen | `mockgen -source=repo.go -destination=mock_repo.go` | Mock implementations |
| mockery | `mockery --name=UserRepository` | Mock implementations |
| sqlc | `sqlc generate` | Type-safe DB query functions from SQL |
| protoc | `protoc --go_out=. --go-grpc_out=. *.proto` | gRPC client/server code |
| wire | `wire ./...` | Dependency injection wiring |
| ent | `go generate ./ent` | ORM models and queries |
| enumer | `go generate ./...` | Enum with JSON/SQL support |

### Code Generation with AST Manipulation

For custom code generators, Go's `go/ast` and `go/parser` packages let you analyze and generate Go source code:

```go
fset := token.NewFileSet()
file, err := parser.ParseFile(fset, "models.go", nil, parser.ParseComments)
if err != nil {
    panic(err)
}

// Find all struct types
ast.Inspect(file, func(n ast.Node) bool {
    typeSpec, ok := n.(*ast.TypeSpec)
    if !ok {
        return true
    }

    structType, ok := typeSpec.Type.(*ast.StructType)
    if !ok {
        return true
    }

    fmt.Printf("Found struct: %s\n", typeSpec.Name.Name)
    for _, field := range structType.Fields.List {
        if field.Tag != nil {
            fmt.Printf("  Field: %s, Tag: %s\n",
                field.Names[0].Name, field.Tag.Value)
        }
    }
    return true
})
```

This is the foundation for tools like `stringer`, `enumer`, and custom code generators that need to understand Go source code.

TypeScript parallel: similar to using the TypeScript Compiler API or Babel AST for code transforms, but Go's AST is simpler because the language grammar is simpler.

---

## 3. Generic Middleware Chains

Generics allow typed middleware for domain-specific handlers:

```go
type TypedHandler[Req any, Resp any] func(context.Context, Req) (Resp, error)
type Middleware[Req any, Resp any] func(TypedHandler[Req, Resp]) TypedHandler[Req, Resp]

func Chain[Req any, Resp any](
    handler TypedHandler[Req, Resp],
    middlewares ...Middleware[Req, Resp],
) TypedHandler[Req, Resp] {
    for i := len(middlewares) - 1; i >= 0; i-- {
        handler = middlewares[i](handler)
    }
    return handler
}

// Logging middleware — generic over request and response types
func WithLogging[Req any, Resp any]() Middleware[Req, Resp] {
    return func(next TypedHandler[Req, Resp]) TypedHandler[Req, Resp] {
        return func(ctx context.Context, req Req) (Resp, error) {
            start := time.Now()
            resp, err := next(ctx, req)
            slog.Info("handler completed", "duration", time.Since(start), "error", err)
            return resp, err
        }
    }
}

// Validation middleware — requires request to implement Validatable
type Validatable interface {
    Validate() error
}

func WithValidation[Req Validatable, Resp any]() Middleware[Req, Resp] {
    return func(next TypedHandler[Req, Resp]) TypedHandler[Req, Resp] {
        return func(ctx context.Context, req Req) (Resp, error) {
            if err := req.Validate(); err != nil {
                var zero Resp
                return zero, fmt.Errorf("validation: %w", err)
            }
            return next(ctx, req)
        }
    }
}

---

## Related Reading

- **Type system foundations** — [Module 01: Types, Interfaces, and Structs](../01-go-mental-model/01-types-interfaces-and-structs.md), section 4 (Interfaces) and section 7 (Generics Preview) establish the interface and type concepts that generics build on
- **sqlc as code generation** — [Module 05: Database Drivers and ORMs](../05-data-storage/01-database-drivers-and-orms.md), section 3 (sqlc) is a concrete production use of the `go generate` workflow from section 2
- **Middleware chains** — [Module 04: Handlers, Routing, and Middleware](../04-http-services/01-handlers-routing-and-middleware.md), section 3 (Middleware Pattern) covers the `func(http.Handler) http.Handler` pattern that section 3 (Generic Middleware Chains) generalizes with type parameters
- **Concurrent generic data structures** — [Module 02: Synchronization and Context](../02-concurrency/02-synchronization-and-context.md) covers the `sync.RWMutex` used to protect the generic `Bus[T]` event system in section 1
- **Reflection as alternative** — [Reflection and Advanced Abstractions](03-reflection-and-advanced-abstractions.md), section 1 covers when reflection is needed vs when generics from this file are sufficient
```
