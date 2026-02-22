# Module 08: Deep Dive — Advanced Patterns

## Type-Safe Event Systems with Generics

One of the most powerful applications of generics is building event systems where the event type carries its payload type:

```go
// Event is a generic event with a typed payload
type Event[T any] struct {
    Topic     string
    Payload   T
    Timestamp time.Time
}

// Handler processes events with a specific payload type
type Handler[T any] func(Event[T]) error

// Bus is a type-safe event bus for a specific event type
type Bus[T any] struct {
    mu       sync.RWMutex
    handlers []Handler[T]
}

func NewBus[T any]() *Bus[T] {
    return &Bus[T]{}
}

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

    event := Event[T]{
        Topic:     topic,
        Payload:   payload,
        Timestamp: time.Now(),
    }

    var errs []error
    for _, h := range handlers {
        if err := h(event); err != nil {
            errs = append(errs, err)
        }
    }
    return errors.Join(errs...)
}

// Usage — compiler enforces payload types
type OrderCreated struct {
    OrderID    string
    CustomerID string
    Total      float64
}

type PaymentReceived struct {
    OrderID string
    Amount  float64
    Method  string
}

orderBus := NewBus[OrderCreated]()
paymentBus := NewBus[PaymentReceived]()

orderBus.Subscribe(func(e Event[OrderCreated]) error {
    slog.Info("order created",
        "order_id", e.Payload.OrderID,
        "total", e.Payload.Total)
    return nil
})

// This would not compile — type mismatch:
// orderBus.Subscribe(func(e Event[PaymentReceived]) error { ... })
```

**TypeScript parallel:** This is like TypeScript's `EventEmitter<{ 'order:created': OrderCreated; 'payment:received': PaymentReceived }>`, but enforced at a structural level rather than through mapped types.

---

## Generic Middleware Chains

HTTP middleware in Go is traditionally `func(http.Handler) http.Handler`. Generics let you build typed middleware for domain-specific handlers:

```go
// TypedHandler is a handler that returns a typed response
type TypedHandler[Req any, Resp any] func(context.Context, Req) (Resp, error)

// Middleware transforms a TypedHandler
type Middleware[Req any, Resp any] func(TypedHandler[Req, Resp]) TypedHandler[Req, Resp]

// Chain composes middleware
func Chain[Req any, Resp any](
    handler TypedHandler[Req, Resp],
    middlewares ...Middleware[Req, Resp],
) TypedHandler[Req, Resp] {
    for i := len(middlewares) - 1; i >= 0; i-- {
        handler = middlewares[i](handler)
    }
    return handler
}

// Logging middleware — generic over request and response
func WithLogging[Req any, Resp any]() Middleware[Req, Resp] {
    return func(next TypedHandler[Req, Resp]) TypedHandler[Req, Resp] {
        return func(ctx context.Context, req Req) (Resp, error) {
            start := time.Now()
            resp, err := next(ctx, req)
            slog.Info("handler completed",
                "duration", time.Since(start),
                "error", err,
            )
            return resp, err
        }
    }
}

// Validation middleware — requires the request to implement Validatable
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

// Usage
type CreateUserRequest struct {
    Name  string `json:"name"`
    Email string `json:"email"`
}

func (r CreateUserRequest) Validate() error {
    if r.Name == "" {
        return fmt.Errorf("name is required")
    }
    return nil
}

type CreateUserResponse struct {
    ID int64 `json:"id"`
}

handler := Chain[CreateUserRequest, CreateUserResponse](
    createUserHandler,
    WithValidation[CreateUserRequest, CreateUserResponse](),
    WithLogging[CreateUserRequest, CreateUserResponse](),
)
```

---

## Plugin Systems in Go

### The `plugin` Package (Limited Use)

Go's built-in `plugin` package loads shared objects (`.so` files) at runtime. It is Linux/macOS only and fragile:

```go
// plugin code: plugins/greeting/main.go
package main

func Greet(name string) string {
    return "Hello, " + name + "!"
}

// Build: go build -buildmode=plugin -o greeting.so ./plugins/greeting

// Host code:
p, _ := plugin.Open("greeting.so")
greetSymbol, _ := p.Lookup("Greet")
greet := greetSymbol.(func(string) string)
fmt.Println(greet("World"))
```

**Limitations:** Both the plugin and host must be built with the exact same Go version, same dependencies at the same versions. This makes the built-in plugin system impractical for most use cases.

### HashiCorp go-plugin (Production-Grade)

HashiCorp's approach runs plugins as separate processes communicating over gRPC. This is what Terraform, Vault, and Packer use:

```go
// Shared interface definition
type Greeter interface {
    Greet(name string) (string, error)
}

// Plugin implementation (separate binary)
type GreeterPlugin struct{}

func (g *GreeterPlugin) Greet(name string) (string, error) {
    return "Hello, " + name + "!", nil
}

// Host uses go-plugin to discover and communicate with plugin processes
// The plugin runs as a subprocess; communication is over gRPC
// If the plugin crashes, it doesn't take down the host
```

**TypeScript parallel:** Similar to VS Code's extension host — plugins run in a separate process for isolation. The communication protocol is well-defined, and plugin crashes are contained.

---

## Dependency Injection

### Manual DI — The Go Preference

Most Go projects wire dependencies manually in `main()`. This is not a limitation — it is a feature. The dependency graph is explicit, readable, and requires no framework:

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

    // Start
    server.Run(ctx, mux, cfg.Port)
}
```

**Why this is preferred in Go:**
- The dependency graph is visible in one function
- No magic — no runtime reflection, no container, no annotations
- Compilation fails immediately if a dependency is missing
- Easy to understand for new team members

### Google Wire (Compile-Time DI)

For very large applications where manual wiring becomes unwieldy, Wire generates the wiring code at compile time:

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
    return nil, nil // Wire replaces this
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

**The recommendation:** Start with manual DI. Move to Wire if your `main()` exceeds 100 lines of wiring. Use fx only if your team has experience with DI containers and prefers that model.

---

## Code Generation with AST Manipulation

For custom code generators, Go's `go/ast` and `go/parser` packages let you analyze and generate Go source code:

```go
package main

import (
    "go/ast"
    "go/parser"
    "go/token"
    "fmt"
    "strings"
)

func main() {
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
                tag := field.Tag.Value
                fmt.Printf("  Field: %s, Tag: %s\n",
                    field.Names[0].Name, tag)
            }
        }

        return true
    })
}
```

This is the foundation for tools like `stringer`, `enumer`, and custom code generators that need to understand Go source code.

**TypeScript parallel:** Similar to using the TypeScript Compiler API or Babel AST for code transforms, but Go's AST is simpler because the language grammar is simpler.

---

## Design Patterns — The Go-Idiomatic Way

### Strategy Pattern

In OOP, you might define a strategy interface with multiple implementations. In Go, a function type is often sufficient:

```go
// OOP-style: interface with implementations
type Compressor interface {
    Compress(data []byte) ([]byte, error)
}

type GzipCompressor struct{}
func (g *GzipCompressor) Compress(data []byte) ([]byte, error) { ... }

type ZstdCompressor struct{}
func (z *ZstdCompressor) Compress(data []byte) ([]byte, error) { ... }

// Go-idiomatic: function type
type CompressFunc func(data []byte) ([]byte, error)

func ProcessData(data []byte, compress CompressFunc) error {
    compressed, err := compress(data)
    // ...
}

// Usage
ProcessData(data, gzip.Compress)
ProcessData(data, zstd.Compress)
```

### Observer Pattern

Go channels replace the traditional observer pattern:

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

### Decorator Pattern

Go's `http.Handler` middleware is already the decorator pattern. For other use cases:

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
        slog.Info("http request",
            "method", req.Method,
            "url", req.URL.String(),
            "status", resp.StatusCode,
            "duration", time.Since(start),
        )
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

**The key insight:** Go's design patterns look different from OOP patterns because Go's composition model is different. Interfaces are implicit, embedding provides delegation, and first-class functions replace many patterns that require classes in other languages. Do not force OOP patterns into Go — learn the idiomatic equivalents.
