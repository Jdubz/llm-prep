# Module 08: Advanced Patterns

## Go's Approach to Abstraction

Coming from TypeScript, you have a rich toolkit for abstraction: generics, decorators, higher-order types, mapped types, conditional types, template literal types. Go's abstraction story is deliberately simpler, but that does not mean it lacks power. This module covers the patterns that separate intermediate Go developers from senior ones.

The philosophy is different. TypeScript asks "how can the type system express this perfectly?" Go asks "how can we keep this simple enough that anyone can read it in six months?" The patterns here honor that philosophy while solving real engineering problems.

---

## Generics (Go 1.18+)

### Type Parameters

Before Go 1.18, you had two options for generic-like code: interfaces (runtime polymorphism) or code generation (compile-time duplication). Generics give you a third option: compile-time polymorphism without duplication.

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
Contains([]int{1, 2, 3}, 2)          // true
Contains([]string{"a", "b"}, "c")    // false
```

**TypeScript parallel:** Go's `[T comparable]` is like TypeScript's `<T extends { equals(other: T): boolean }>`, except `comparable` is a built-in constraint that means the type supports `==` and `!=`.

### Constraints and Type Sets

Constraints are interfaces that describe what operations a type parameter supports:

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

// The ~ means "underlying type" — allows named types
type Celsius float64
Sum([]Celsius{20.0, 22.5, 19.3}) // Works because ~float64 matches Celsius
```

The `golang.org/x/exp/constraints` package (and its successor in the `cmp` package) provides common constraint types:

```go
import "golang.org/x/exp/constraints"

func Max[T constraints.Ordered](a, b T) T {
    if a > b {
        return a
    }
    return b
}
```

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

func (s *Set[T]) Add(v T)            { s.items[v] = struct{}{} }
func (s *Set[T]) Contains(v T) bool  { _, ok := s.items[v]; return ok }
func (s *Set[T]) Remove(v T)         { delete(s.items, v) }
func (s *Set[T]) Len() int           { return len(s.items) }

func (s *Set[T]) Values() []T {
    result := make([]T, 0, len(s.items))
    for k := range s.items {
        result = append(result, k)
    }
    return result
}
```

```go
// Result type (like TypeScript's Result<T, E> or Rust's Result)
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

### When to Use Generics vs Interfaces vs Code Generation

| Approach | Use When | Example |
|----------|----------|---------|
| Generics | Same logic, different types, type safety needed | `Contains[T]`, `Map[T,U]`, `Set[T]` |
| Interfaces | Different behavior, polymorphism needed | `io.Reader`, `http.Handler` |
| Code generation | Complex type-specific code | protobuf, mocks, ORM models |
| `any` (interface{}) | Truly dynamic data, JSON-like | `map[string]any` for config |

**Rule of thumb from the Go team:** "Do not use generics to replace interfaces. Use generics when you are writing the same code for multiple types and the algorithm does not depend on the type's behavior, only its identity."

---

## Code Generation

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

### mockgen for Testing

```go
//go:generate mockgen -source=repository.go -destination=mock_repository_test.go -package=service_test

type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*User, error)
    Create(ctx context.Context, user *User) error
    Update(ctx context.Context, user *User) error
}
```

### sqlc for Database Access

sqlc generates type-safe Go code from SQL queries — the Go equivalent of Prisma:

```sql
-- queries/users.sql
-- name: GetUser :one
SELECT id, name, email, created_at
FROM users
WHERE id = $1;

-- name: ListUsers :many
SELECT id, name, email, created_at
FROM users
ORDER BY created_at DESC
LIMIT $1 OFFSET $2;

-- name: CreateUser :one
INSERT INTO users (name, email)
VALUES ($1, $2)
RETURNING id, name, email, created_at;
```

sqlc generates fully typed Go functions from these queries. No ORM, no reflection, just SQL.

---

## Reflection

### When Reflection Is Justified

Reflection in Go is powerful but expensive (both in performance and readability). Valid use cases:

1. **Serialization/deserialization** (encoding/json uses reflection)
2. **Struct tag processing** (ORMs, validators, config parsers)
3. **Dependency injection frameworks**
4. **Testing utilities**

### Type vs Value

```go
import "reflect"

type User struct {
    Name  string `json:"name" validate:"required"`
    Email string `json:"email" validate:"email"`
    Age   int    `json:"age"   validate:"gte=0"`
}

u := User{Name: "Alice", Email: "alice@example.com", Age: 30}

// Type inspection — static information about the type
t := reflect.TypeOf(u)
fmt.Println(t.Name())       // "User"
fmt.Println(t.NumField())   // 3
fmt.Println(t.Field(0).Tag.Get("json"))     // "name"
fmt.Println(t.Field(0).Tag.Get("validate")) // "required"

// Value inspection — runtime values
v := reflect.ValueOf(u)
fmt.Println(v.Field(0).String())  // "Alice"
fmt.Println(v.Field(2).Int())     // 30
```

### Reading Struct Tags

This is the most common legitimate use of reflection — processing metadata attached to struct fields:

```go
func ValidateStruct(s any) error {
    v := reflect.ValueOf(s)
    t := reflect.TypeOf(s)

    if t.Kind() == reflect.Ptr {
        v = v.Elem()
        t = t.Elem()
    }

    var errs []error
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        value := v.Field(i)
        tag := field.Tag.Get("validate")

        if tag == "" {
            continue
        }

        rules := strings.Split(tag, ",")
        for _, rule := range rules {
            if rule == "required" && value.IsZero() {
                errs = append(errs, fmt.Errorf("%s is required", field.Name))
            }
        }
    }

    return errors.Join(errs...)
}
```

### When to Avoid Reflection

- **Hot paths:** Reflection is 10-100x slower than direct access
- **Where generics suffice:** Use type parameters instead
- **For "convenience":** If reflection makes code clever but unreadable, do not use it

---

## Embedding and Composition

### Struct Embedding for Delegation

Go does not have inheritance. Embedding promotes methods from an inner type to the outer type — delegation, not inheritance:

```go
// Instead of: class Admin extends User (TypeScript)
// Go uses embedding:

type User struct {
    ID    int64
    Name  string
    Email string
}

func (u *User) DisplayName() string {
    return u.Name
}

type Admin struct {
    User              // Embedded — User's methods are promoted
    Permissions []string
}

admin := Admin{
    User:        User{ID: 1, Name: "Alice", Email: "alice@example.com"},
    Permissions: []string{"manage_users", "manage_content"},
}

admin.DisplayName()  // Calls User.DisplayName — promoted
admin.Name           // Direct field access — also promoted
```

### Interface Embedding for Composition

```go
// Compose interfaces from smaller ones (like TypeScript's intersection types)
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type ReadWriter interface {
    Reader
    Writer
}

// TypeScript equivalent:
// type ReadWriter = Reader & Writer
```

### Embedding vs Inheritance

| Aspect | Go Embedding | OOP Inheritance |
|--------|-------------|-----------------|
| Relationship | "has-a" (delegation) | "is-a" (subtype) |
| Method override | Shadowing, not virtual dispatch | Virtual dispatch |
| Type identity | `Admin` is NOT a `User` | `Admin` IS a `User` |
| Accessing parent | `admin.User.Method()` | `super.Method()` |
| Multiple | Multiple embedding allowed | Usually single (except mixins) |

---

## Functional Options Pattern

This is Go's answer to the "constructor with many optional parameters" problem. In TypeScript, you would pass an options object. In Go, you use variadic functions that return option appliers.

```go
type Server struct {
    host         string
    port         int
    timeout      time.Duration
    maxConns     int
    logger       *slog.Logger
    tlsConfig    *tls.Config
}

// Option is a function that configures the server
type Option func(*Server) error

func WithHost(host string) Option {
    return func(s *Server) error {
        if host == "" {
            return fmt.Errorf("host cannot be empty")
        }
        s.host = host
        return nil
    }
}

func WithPort(port int) Option {
    return func(s *Server) error {
        if port < 1 || port > 65535 {
            return fmt.Errorf("port must be 1-65535, got %d", port)
        }
        s.port = port
        return nil
    }
}

func WithTimeout(d time.Duration) Option {
    return func(s *Server) error {
        s.timeout = d
        return nil
    }
}

func WithLogger(l *slog.Logger) Option {
    return func(s *Server) error {
        s.logger = l
        return nil
    }
}

func WithTLS(cfg *tls.Config) Option {
    return func(s *Server) error {
        s.tlsConfig = cfg
        return nil
    }
}

func NewServer(opts ...Option) (*Server, error) {
    s := &Server{
        host:     "0.0.0.0",
        port:     8080,
        timeout:  30 * time.Second,
        maxConns: 100,
        logger:   slog.Default(),
    }

    for _, opt := range opts {
        if err := opt(s); err != nil {
            return nil, fmt.Errorf("applying option: %w", err)
        }
    }

    return s, nil
}

// Usage
srv, err := NewServer(
    WithHost("localhost"),
    WithPort(9090),
    WithTimeout(60 * time.Second),
    WithTLS(tlsConfig),
)
```

**TypeScript equivalent:**
```typescript
// TypeScript uses an options object
const srv = new Server({
  host: "localhost",
  port: 9090,
  timeout: 60_000,
  tlsConfig,
});
```

**Why Go uses functional options instead of options structs:**
- Zero value of a struct field is ambiguous (did the caller set `port: 0` intentionally, or not set it?)
- Validation can happen per-option, with clear error messages
- Options are composable — you can create "preset" option bundles
- The API is self-documenting through `WithX` function names

---

## Building CLIs with Cobra

Cobra powers `kubectl`, `hugo`, `gh`, and most major Go CLIs. If you are building anything beyond a single-flag tool, use cobra.

```go
package main

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
)

var (
    verbose bool
    output  string
)

var rootCmd = &cobra.Command{
    Use:   "mytool",
    Short: "A brief description of your tool",
    Long:  "A longer description that spans multiple lines.",
}

var serveCmd = &cobra.Command{
    Use:   "serve",
    Short: "Start the HTTP server",
    RunE: func(cmd *cobra.Command, args []string) error {
        port, _ := cmd.Flags().GetInt("port")
        fmt.Printf("Starting server on port %d (verbose=%v)\n", port, verbose)
        return nil
    },
}

var migrateCmd = &cobra.Command{
    Use:   "migrate [up|down]",
    Short: "Run database migrations",
    Args:  cobra.ExactArgs(1),
    RunE: func(cmd *cobra.Command, args []string) error {
        direction := args[0]
        steps, _ := cmd.Flags().GetInt("steps")
        fmt.Printf("Migrating %s (%d steps)\n", direction, steps)
        return nil
    },
}

func init() {
    // Persistent flags — available to all subcommands
    rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
    rootCmd.PersistentFlags().StringVarP(&output, "output", "o", "text", "output format (text|json)")

    // Local flags — specific to a subcommand
    serveCmd.Flags().Int("port", 8080, "server port")
    migrateCmd.Flags().Int("steps", 0, "number of migration steps (0 = all)")

    rootCmd.AddCommand(serveCmd)
    rootCmd.AddCommand(migrateCmd)
}

func main() {
    if err := rootCmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```

**Shell completion comes free:**
```bash
mytool completion bash > /etc/bash_completion.d/mytool
mytool completion zsh > ~/.zsh/completions/_mytool
```

---

## Builder Pattern in Go

Less common than functional options but useful for complex object construction:

```go
type QueryBuilder struct {
    table      string
    conditions []string
    args       []any
    orderBy    string
    limit      int
    offset     int
    err        error
}

func NewQuery(table string) *QueryBuilder {
    return &QueryBuilder{table: table}
}

func (q *QueryBuilder) Where(condition string, args ...any) *QueryBuilder {
    if q.err != nil {
        return q
    }
    q.conditions = append(q.conditions, condition)
    q.args = append(q.args, args...)
    return q
}

func (q *QueryBuilder) OrderBy(field string) *QueryBuilder {
    q.orderBy = field
    return q
}

func (q *QueryBuilder) Limit(n int) *QueryBuilder {
    q.limit = n
    return q
}

func (q *QueryBuilder) Offset(n int) *QueryBuilder {
    q.offset = n
    return q
}

func (q *QueryBuilder) Build() (string, []any, error) {
    if q.err != nil {
        return "", nil, q.err
    }

    query := fmt.Sprintf("SELECT * FROM %s", q.table)

    if len(q.conditions) > 0 {
        query += " WHERE " + strings.Join(q.conditions, " AND ")
    }
    if q.orderBy != "" {
        query += " ORDER BY " + q.orderBy
    }
    if q.limit > 0 {
        query += fmt.Sprintf(" LIMIT %d", q.limit)
    }
    if q.offset > 0 {
        query += fmt.Sprintf(" OFFSET %d", q.offset)
    }

    return query, q.args, nil
}

// Usage
query, args, err := NewQuery("users").
    Where("active = $1", true).
    Where("age > $2", 18).
    OrderBy("created_at DESC").
    Limit(20).
    Offset(40).
    Build()
```

---

## Interview Questions

### Q1: When would you use generics vs interfaces?

**Strong answer:** "Interfaces are for polymorphism — when different types have different behavior but share a contract. Generics are for code reuse — when the same algorithm applies to multiple types. For example, `io.Reader` should be an interface because reading from a file vs a network connection involves different behavior. But `Contains(slice, target)` should be generic because the algorithm is identical regardless of the element type. I would never use generics to replace an interface that models behavior."

### Q2: Explain the functional options pattern and when you would use it.

**Strong answer:** "Functional options solve the problem of constructors with many optional parameters. Each option is a function that modifies the config struct. I use `WithX` naming by convention. The advantages over an options struct are: zero values are unambiguous (an option not passed is different from a zero-value field), validation can happen per-option, and the API is self-documenting. I use this pattern for any constructor that has more than 2-3 optional parameters — things like HTTP clients, servers, database pools."

### Q3: What are the tradeoffs of using reflection in Go?

**Strong answer:** "Reflection is 10-100x slower than direct code, it bypasses compile-time type checking, and it makes code harder to understand. I use it only when there is no compile-time alternative: processing struct tags for serialization, building validation frameworks, or writing test utilities. Since Go 1.18, generics have eliminated some reflection use cases — where I previously needed `reflect` to write type-agnostic container code, I now use type parameters."

### Q4: How does struct embedding differ from inheritance?

**Strong answer:** "Embedding is delegation, not inheritance. When I embed `User` in `Admin`, the `Admin` does not become a `User` in the type system — there is no subtype relationship. Methods are promoted as a convenience, but there is no virtual dispatch. If `Admin` defines a method with the same name, it shadows the embedded method rather than overriding it. I can still access the embedded type directly: `admin.User.Method()`. Multiple embedding is allowed, and there is no diamond problem because shadowed methods require explicit disambiguation."

### Q5: When should you use code generation vs generics?

**Strong answer:** "Generics are best for simple type parameterization — data structures, utility functions, algorithms that are identical across types. Code generation is better when the generated code needs to be type-specific in complex ways: protobuf message types, database query functions from SQL, mock implementations of interfaces. The rule of thumb is: if you can express it as a generic function with constraints, prefer generics. If the output varies significantly per type or involves boilerplate that is complex but mechanical, prefer code generation."

### Q6: Describe how you would build a CLI tool in Go.

**Strong answer:** "I use cobra for any non-trivial CLI. The root command handles global flags like `--verbose` and `--output` format. Each subcommand is a separate `cobra.Command` with its own flags and validation. I use `RunE` instead of `Run` so commands return errors instead of calling `os.Exit` directly — this makes them testable. For configuration, I combine cobra flags with viper so environment variables and config files also work. I generate shell completions with cobra's built-in support and use GoReleaser to produce cross-platform binaries."

### Q7: Explain Go's `embed` package and its use cases.

**Strong answer:** "The `embed` package lets you include files in the compiled binary at build time using `//go:embed` directives. Common use cases: embedding SQL migration files so the binary is self-contained, embedding HTML templates and static assets for a web server, embedding default configuration files. The embedded files are read-only and available via `embed.FS`, which implements `fs.FS`. This means a single binary contains everything needed to run the service — no more managing asset paths in Docker images."
