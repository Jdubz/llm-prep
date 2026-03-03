# 02 – Patterns and Composition

This file assumes you have read `01-generics-and-code-generation.md`. It covers Go's idiomatic design patterns: embedding, functional options, dependency injection, and building CLIs.

---

## 1. Embedding and Composition

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
    User              // Embedded — User's fields and methods are promoted
    Permissions []string
}

admin := Admin{
    User:        User{ID: 1, Name: "Alice", Email: "alice@example.com"},
    Permissions: []string{"manage_users", "manage_content"},
}

admin.DisplayName()  // Calls User.DisplayName — promoted
admin.Name           // Direct field access — also promoted
admin.User.Name      // Explicit access also works
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

### Embedding Patterns

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

// Embedding interface in struct (for partial mock implementation)
type MockStore struct {
    UserRepository                    // Embed interface
}
func (m *MockStore) GetByID(ctx context.Context, id int64) (*User, error) {
    // Only implement the methods you need; others panic with nil pointer
    return &User{Name: "mock"}, nil
}
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

## 2. Functional Options Pattern

Go's answer to the "constructor with many optional parameters" problem. In TypeScript, you pass an options object. In Go, you use variadic functions that return option appliers.

```go
type Server struct {
    host      string
    port      int
    timeout   time.Duration
    maxConns  int
    logger    *slog.Logger
    tlsConfig *tls.Config
}

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
    WithTimeout(60*time.Second),
    WithTLS(tlsConfig),
)
```

### Functional Options Template

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

**Why functional options over options structs:**
- Zero value of a struct field is ambiguous (did the caller set `port: 0` intentionally, or not set it?)
- Validation can happen per-option with clear error messages
- Options are composable — you can create "preset" option bundles
- The API is self-documenting through `WithX` function names

---

## 3. Builder Pattern

Less common than functional options but useful for complex object construction with a fluent interface:

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
        return q // Propagate errors silently
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

// Usage — fluent chaining
query, args, err := NewQuery("users").
    Where("active = $1", true).
    Where("age > $2", 18).
    OrderBy("created_at DESC").
    Limit(20).
    Offset(40).
    Build()
```

---

## 4. Dependency Injection

### Manual DI — The Go Preference

Most Go projects wire dependencies manually in `main()`. The dependency graph is explicit, readable, and requires no framework:

```go
func main() {
    cfg := config.MustLoad()

    // Layer 1: Infrastructure
    db := database.MustOpen(cfg.DatabaseURL)
    cache := redis.MustConnect(cfg.RedisURL)

    // Layer 2: Repositories
    userRepo := postgres.NewUserRepository(db)
    orderRepo := postgres.NewOrderRepository(db)

    // Layer 3: Services
    emailSvc := email.NewService(cfg.SMTPConfig)
    userSvc := user.NewService(userRepo, emailSvc, cache)
    orderSvc := order.NewService(orderRepo, userSvc)

    // Layer 4: Handlers
    userHandler := handler.NewUserHandler(userSvc)
    orderHandler := handler.NewOrderHandler(orderSvc)

    // Layer 5: Router
    mux := http.NewServeMux()
    userHandler.RegisterRoutes(mux)
    orderHandler.RegisterRoutes(mux)

    server.Run(ctx, mux, cfg.Port)
}
```

Why this is preferred:
- The dependency graph is visible in one function
- No magic — no runtime reflection, no container, no annotations
- Compilation fails immediately if a dependency is missing
- Easy to understand for new team members

### Google Wire (Compile-Time DI)

For very large applications where manual wiring becomes unwieldy:

```go
// wire.go (build-ignored, used by wire tool)
//go:build wireinject

package main

import "github.com/google/wire"

func InitializeServer(cfg *config.Config) (*server.Server, error) {
    wire.Build(
        database.NewConnection,
        postgres.NewUserRepository,
        postgres.NewOrderRepository,
        user.NewService,
        order.NewService,
        handler.NewUserHandler,
        handler.NewOrderHandler,
        server.NewServer,
    )
    return nil, nil // Wire replaces this body
}
```

Running `wire` generates `wire_gen.go` with the concrete wiring code. It is code generation, not runtime magic.

### Uber fx (Runtime DI)

For teams that prefer a container-based approach:

```go
func main() {
    fx.New(
        fx.Provide(
            config.Load,
            database.NewConnection,
            postgres.NewUserRepository,
            user.NewService,
            handler.NewUserHandler,
        ),
        fx.Invoke(func(h *handler.UserHandler, mux *http.ServeMux) {
            h.RegisterRoutes(mux)
        }),
    ).Run()
}
```

**The recommendation:** Start with manual DI. Move to Wire if your `main()` exceeds ~100 lines of wiring. Use fx only if your team has experience with DI containers.

---

## 5. Building CLIs with Cobra

Cobra powers `kubectl`, `hugo`, `gh`, and most major Go CLIs.

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

Cobra CLI template (minimal):

```go
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

Shell completion comes free:

```bash
mytool completion bash > /etc/bash_completion.d/mytool
mytool completion zsh > ~/.zsh/completions/_mytool
```

Use `RunE` (returns error) instead of `Run` (calls os.Exit) — this makes commands testable.

---

## 6. Go-Idiomatic Design Patterns

### Strategy Pattern — Functions over Interfaces

In OOP you define a strategy interface with multiple implementations. In Go, a function type is often sufficient:

```go
// OOP-style: interface with implementations
type Compressor interface {
    Compress(data []byte) ([]byte, error)
}

// Go-idiomatic: function type
type CompressFunc func(data []byte) ([]byte, error)

func ProcessData(data []byte, compress CompressFunc) error {
    compressed, err := compress(data)
    // ...
}

// Usage — pass any function with matching signature
ProcessData(data, gzip.Compress)
ProcessData(data, zstd.Compress)
```

### Observer Pattern — Channels Replace Callbacks

```go
type EventBroker struct {
    mu          sync.RWMutex
    subscribers map[string][]chan Event
}

func (b *EventBroker) Subscribe(topic string) <-chan Event {
    b.mu.Lock()
    defer b.mu.Unlock()

    ch := make(chan Event, 16) // Buffered to prevent blocking publisher
    b.subscribers[topic] = append(b.subscribers[topic], ch)
    return ch
}

func (b *EventBroker) Publish(topic string, event Event) {
    b.mu.RLock()
    defer b.mu.RUnlock()

    for _, ch := range b.subscribers[topic] {
        select {
        case ch <- event:
        default:
            // Subscriber is slow — drop or log
        }
    }
}

// Consumer
ch := broker.Subscribe("orders")
for event := range ch {
    processOrder(event)
}
```

### Decorator Pattern — RoundTripper Wrapping

Go's `http.Handler` middleware is already the decorator pattern. For HTTP clients:

```go
type RoundTripFunc func(*http.Request) (*http.Response, error)

func (f RoundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
    return f(req)
}

// Decorate an HTTP transport with logging
func WithTransportLogging(rt http.RoundTripper) http.RoundTripper {
    return RoundTripFunc(func(req *http.Request) (*http.Response, error) {
        start := time.Now()
        resp, err := rt.RoundTrip(req)
        if err == nil {
            slog.Info("http request",
                "method", req.Method,
                "url", req.URL.String(),
                "status", resp.StatusCode,
                "duration", time.Since(start),
            )
        }
        return resp, err
    })
}

// Stack decorators
client := &http.Client{
    Transport: WithTransportLogging(
        WithRetry(3,
            http.DefaultTransport,
        ),
    ),
}
```

---

## 7. Quick Decision Table

| Problem | Go Pattern |
|---------|-----------|
| Many optional constructor params | Functional options (`WithX`) |
| Same algorithm, many types | Generics `[T any]` |
| Different behavior, same contract | Interface |
| Type-safe DB queries | sqlc (code gen) |
| Mock generation | mockgen / mockery |
| Delegation/reuse | Struct embedding |
| DI wiring | Manual in `main()` |
| CLI framework | Cobra |
| Dynamic query building | squirrel query builder |
| Enum with String() | stringer code gen |
