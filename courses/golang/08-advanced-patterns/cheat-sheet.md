# Module 08: Cheat Sheet — Advanced Patterns

## Generics Syntax Reference

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

// Type inference — usually no need to specify types
result := Map(users, func(u User) string { return u.Name })
```

---

## Constraint Examples

| Constraint | Meaning | Use Case |
|-----------|---------|----------|
| `any` | No restriction (alias for `interface{}`) | Generic containers |
| `comparable` | Supports `==` and `!=` | Map keys, set elements |
| `constraints.Ordered` | Supports `<`, `>`, `<=`, `>=` | Sorting, min/max |
| `~int \| ~float64` | Underlying type is int or float64 | Arithmetic operations |
| `interface{ Len() int }` | Must have `Len()` method | Sized collections |
| `fmt.Stringer` | Must have `String() string` | Display/logging |

---

## Functional Options Template

```go
type Option func(*Config) error

func WithPort(port int) Option {
    return func(c *Config) error {
        if port < 1 || port > 65535 {
            return fmt.Errorf("invalid port: %d", port)
        }
        c.port = port
        return nil
    }
}

func New(opts ...Option) (*Thing, error) {
    cfg := &Config{port: 8080}  // defaults
    for _, opt := range opts {
        if err := opt(cfg); err != nil {
            return nil, err
        }
    }
    return &Thing{cfg: cfg}, nil
}
```

---

## Code Generation Commands

| Tool | Command | Generates |
|------|---------|-----------|
| stringer | `go generate ./...` | `String()` methods for iota constants |
| mockgen | `mockgen -source=repo.go -destination=mock_repo.go` | Mock implementations |
| sqlc | `sqlc generate` | Type-safe DB query functions from SQL |
| protoc | `protoc --go_out=. --go-grpc_out=. *.proto` | gRPC client/server code |
| wire | `wire ./...` | Dependency injection wiring |
| ent | `go generate ./ent` | ORM models and queries |
| enumer | `go generate ./...` | Enum with JSON/SQL support |

**go:generate directive:**
```go
//go:generate mockgen -source=repository.go -destination=mock_repository_test.go -package=service_test
//go:generate stringer -type=Status
//go:generate sqlc generate
```

---

## Reflection API Quick Reference

```go
t := reflect.TypeOf(x)          // Type info: t.Name(), t.Kind(), t.NumField()
v := reflect.ValueOf(x)         // Value info: v.Field(i), v.IsZero()
t.Field(i).Tag.Get("json")      // Read struct tags
t.Field(i).Name                  // Field name
v.Field(i).Interface()           // Get value as any

// Setting values (requires pointer)
v = reflect.ValueOf(&x).Elem()
v.Field(i).SetString("new")
```

**Warning:** Reflection is 10-100x slower than direct access. Never use on hot paths.

---

## Embedding Patterns

```go
// Struct embedding — promotes fields and methods
type Base struct{ ID int64 }
type User struct {
    Base              // User.ID works, User.Base.ID also works
    Name string
}

// Interface embedding — composes interfaces
type ReadWriter interface {
    io.Reader         // Embeds Read method
    io.Writer         // Embeds Write method
}

// Embedding for "override" (shadowing, not virtual dispatch)
type Logger struct{ *slog.Logger }
func (l *Logger) Info(msg string) {
    l.Logger.Info("[custom] " + msg)  // Shadows slog.Logger.Info
}

// Embedding interface in struct (for partial implementation)
type MockStore struct {
    UserRepository                    // Embed interface
}
func (m *MockStore) GetByID(ctx context.Context, id int64) (*User, error) {
    // Only implement the methods you need in tests
    return &User{Name: "mock"}, nil
}
```

---

## CLI Template with Cobra

```go
package main

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
)

func main() {
    root := &cobra.Command{
        Use:   "mytool",
        Short: "One-line description",
    }

    // Global flags
    root.PersistentFlags().BoolP("verbose", "v", false, "verbose output")

    // Subcommand
    serve := &cobra.Command{
        Use:   "serve",
        Short: "Start server",
        RunE: func(cmd *cobra.Command, args []string) error {
            port, _ := cmd.Flags().GetInt("port")
            fmt.Printf("Listening on :%d\n", port)
            return nil
        },
    }
    serve.Flags().IntP("port", "p", 8080, "listen port")
    root.AddCommand(serve)

    if err := root.Execute(); err != nil {
        os.Exit(1)
    }
}
```

---

## Quick Decision Table

| Problem | Go Pattern |
|---------|-----------|
| Many optional constructor params | Functional options (`WithX`) |
| Same algorithm, many types | Generics `[T any]` |
| Different behavior, same contract | Interface |
| Type-safe DB queries | sqlc (code gen) |
| Mock generation | mockgen |
| Delegation/reuse | Struct embedding |
| DI wiring | Manual in `main()` |
| CLI framework | Cobra |
