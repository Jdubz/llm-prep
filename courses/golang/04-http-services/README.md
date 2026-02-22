# Module 04: Building HTTP Services

## Overview

Go was built for the internet. The standard library's `net/http` package is production-grade out of the box — something that will feel unusual coming from TypeScript where you'd never ship Express without a dozen middleware packages. Go 1.22 brought significant routing improvements that close the gap with third-party routers, making the stdlib viable for most HTTP services.

This module covers everything you need to build, structure, and ship HTTP services in Go — from handler patterns through graceful shutdown.

---

## Table of Contents

1. [net/http Fundamentals](#nethttp-fundamentals)
2. [Handler Chains and the Middleware Pattern](#handler-chains-and-the-middleware-pattern)
3. [ServeMux Routing (Go 1.22+)](#servemux-routing-go-122)
4. [Request Validation and Error Responses](#request-validation-and-error-responses)
5. [Middleware Implementations](#middleware-implementations)
6. [Graceful Shutdown](#graceful-shutdown)
7. [Framework Comparison](#framework-comparison)
8. [Request/Response Patterns](#requestresponse-patterns)
9. [Project Structure for HTTP Services](#project-structure-for-http-services)
10. [Interview Questions](#interview-questions)

---

## net/http Fundamentals

### The Handler Interface

Everything in Go's HTTP world revolves around one interface:

```go
type Handler interface {
    ServeHTTP(ResponseWriter, *Request)
}
```

That's it. Compare this to Express where you have `(req, res, next)` — Go has no `next`. Middleware composition works differently here, and understanding this is key.

### HandlerFunc Adapter

Since writing a struct for every handler is verbose, Go provides an adapter:

```go
type HandlerFunc func(ResponseWriter, *Request)

// HandlerFunc implements Handler by calling itself.
func (f HandlerFunc) ServeHTTP(w ResponseWriter, r *Request) {
    f(w, r)
}
```

This is the **adapter pattern** — it lets any function with the right signature satisfy the `Handler` interface. In TypeScript terms, think of it as a type assertion that also provides the method implementation.

```go
// These are equivalent:
http.Handle("/health", http.HandlerFunc(healthCheck))
http.HandleFunc("/health", healthCheck)

func healthCheck(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ok"}`))
}
```

### ResponseWriter Gotchas

`http.ResponseWriter` has ordering rules that will bite you:

```go
func handler(w http.ResponseWriter, r *http.Request) {
    // 1. Set headers FIRST
    w.Header().Set("Content-Type", "application/json")

    // 2. Then write status code
    w.WriteHeader(http.StatusCreated) // Must come before Write()

    // 3. Then write body
    w.Write([]byte(`{"id": 1}`))

    // WRONG: This header is IGNORED — already sent
    w.Header().Set("X-Too-Late", "yes")

    // WRONG: This status is IGNORED — already sent
    w.WriteHeader(http.StatusOK)
}
```

**Key rule**: Once you call `Write()` or `WriteHeader()`, headers are flushed. There's no going back. If you call `Write()` without `WriteHeader()`, Go implicitly sends 200. This is unlike Express where you can chain `res.status(201).json(data)`.

---

## Handler Chains and the Middleware Pattern

### The Middleware Signature

Go middleware follows a single, universal pattern:

```go
func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Before: runs before the handler
        // ...

        next.ServeHTTP(w, r) // Call the next handler

        // After: runs after the handler returns
        // ...
    })
}
```

This is `func(http.Handler) http.Handler` — a function that wraps a handler and returns a new handler. In TypeScript/Express terms, think of it as a higher-order function replacing the `(req, res, next)` pattern.

### Composing Middleware

Middleware composes through nesting:

```go
// Manual composition — reads inside-out
handler := logging(auth(rateLimit(myHandler)))

// This means:
// 1. logging runs first
// 2. auth runs second
// 3. rateLimit runs third
// 4. myHandler runs last
```

For better readability, build a chain helper:

```go
// Chain applies middleware in order (first argument runs first).
func Chain(h http.Handler, middleware ...func(http.Handler) http.Handler) http.Handler {
    // Apply in reverse so the first middleware in the slice is the outermost.
    for i := len(middleware) - 1; i >= 0; i-- {
        h = middleware[i](h)
    }
    return h
}

// Usage reads top-to-bottom, like Express app.use()
handler := Chain(
    myHandler,
    logging,    // runs first
    auth,       // runs second
    rateLimit,  // runs third
)
```

### Passing Data Through Middleware (Context)

In Express, you'd set `req.user = decoded`. In Go, you use `context.Context`:

```go
type contextKey string

const userKey contextKey = "user"

func authMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        user, err := validateToken(r.Header.Get("Authorization"))
        if err != nil {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return // Don't call next — request stops here
        }

        // Attach user to context
        ctx := context.WithValue(r.Context(), userKey, user)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

// Extract in handler
func profileHandler(w http.ResponseWriter, r *http.Request) {
    user := r.Context().Value(userKey).(*User) // Type assertion required
    json.NewEncoder(w).Encode(user)
}
```

**Important**: Use unexported custom types for context keys to prevent collisions across packages — never use `string` or `int` directly.

---

## ServeMux Routing (Go 1.22+)

### Before Go 1.22

The old `ServeMux` was embarrassingly limited:

```go
// Old: No method matching, no path parameters
http.HandleFunc("/api/users", usersHandler)     // Matches ALL methods
http.HandleFunc("/api/users/", userHandler)      // Trailing slash = prefix match
```

This is why everyone used third-party routers. Go 1.22 changed everything.

### Go 1.22+ Enhanced Routing

```go
mux := http.NewServeMux()

// Method patterns
mux.HandleFunc("GET /api/users", listUsers)
mux.HandleFunc("POST /api/users", createUser)

// Path parameters with {name} syntax
mux.HandleFunc("GET /api/users/{id}", getUser)
mux.HandleFunc("PUT /api/users/{id}", updateUser)
mux.HandleFunc("DELETE /api/users/{id}", deleteUser)

// Wildcard (catch-all) with {name...}
mux.HandleFunc("GET /static/{path...}", serveStatic)

// Exact match vs prefix match
mux.HandleFunc("GET /api/users/{id}", getUser)     // Exact: /api/users/123
mux.HandleFunc("GET /api/users/{id}/", userPrefix)  // Prefix: /api/users/123/*
```

### Extracting Path Parameters

```go
func getUser(w http.ResponseWriter, r *http.Request) {
    // Go 1.22+: PathValue extracts named parameters
    id := r.PathValue("id")

    // Parse to int if needed
    userID, err := strconv.Atoi(id)
    if err != nil {
        http.Error(w, "invalid user ID", http.StatusBadRequest)
        return
    }

    // ... fetch user
}
```

### Routing Precedence

Go 1.22 uses specificity-based precedence:

```go
mux.HandleFunc("GET /posts/{id}", getPost)       // More specific
mux.HandleFunc("GET /posts/latest", getLatest)    // Even more specific — wins for /posts/latest
mux.HandleFunc("GET /{path...}", catchAll)         // Least specific — fallback

// Precedence rules:
// 1. Literal segments beat wildcards: /posts/latest > /posts/{id}
// 2. Longer patterns beat shorter: /a/b/c > /a/{rest...}
// 3. Method-specific beats method-agnostic: "GET /foo" > "/foo"
```

### Host-Based Routing

```go
mux.HandleFunc("GET api.example.com/users", apiListUsers)
mux.HandleFunc("GET www.example.com/users", webListUsers)
```

---

## Request Validation and Error Responses

### Structured Error Response

Define a consistent error format:

```go
type APIError struct {
    Status  int                `json:"-"`                   // HTTP status code
    Code    string             `json:"code"`                // Machine-readable error code
    Message string             `json:"message"`             // Human-readable message
    Details map[string]string  `json:"details,omitempty"`   // Field-level errors
}

func (e *APIError) Error() string {
    return e.Message
}

// writeError sends a structured JSON error response.
func writeError(w http.ResponseWriter, err *APIError) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(err.Status)
    json.NewEncoder(w).Encode(err)
}
```

### Input Validation

#### Manual Validation

```go
type CreateUserRequest struct {
    Email    string `json:"email"`
    Name     string `json:"name"`
    Age      int    `json:"age"`
}

func (r *CreateUserRequest) Validate() *APIError {
    details := make(map[string]string)

    if r.Email == "" {
        details["email"] = "required"
    } else if !strings.Contains(r.Email, "@") {
        details["email"] = "invalid email format"
    }

    if r.Name == "" {
        details["name"] = "required"
    } else if len(r.Name) > 100 {
        details["name"] = "must be 100 characters or fewer"
    }

    if r.Age < 0 || r.Age > 150 {
        details["age"] = "must be between 0 and 150"
    }

    if len(details) > 0 {
        return &APIError{
            Status:  http.StatusBadRequest,
            Code:    "VALIDATION_ERROR",
            Message: "request validation failed",
            Details: details,
        }
    }
    return nil
}
```

#### Using go-playground/validator

```go
import "github.com/go-playground/validator/v10"

var validate = validator.New()

type CreateUserRequest struct {
    Email string `json:"email" validate:"required,email"`
    Name  string `json:"name"  validate:"required,max=100"`
    Age   int    `json:"age"   validate:"gte=0,lte=150"`
}

func decodeAndValidate[T any](r *http.Request) (T, *APIError) {
    var req T
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        return req, &APIError{
            Status:  http.StatusBadRequest,
            Code:    "INVALID_JSON",
            Message: "malformed request body",
        }
    }

    if err := validate.Struct(req); err != nil {
        details := make(map[string]string)
        for _, e := range err.(validator.ValidationErrors) {
            details[e.Field()] = e.Tag()
        }
        return req, &APIError{
            Status:  http.StatusBadRequest,
            Code:    "VALIDATION_ERROR",
            Message: "request validation failed",
            Details: details,
        }
    }

    return req, nil
}
```

The generic `decodeAndValidate[T]` function eliminates the repetitive decode-validate boilerplate you'd write in every handler. This is idiomatic Go 1.18+ — generics are appropriate here.

---

## Middleware Implementations

### Logging Middleware

```go
func loggingMiddleware(logger *slog.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            start := time.Now()

            // Wrap ResponseWriter to capture status code
            wrapped := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}

            next.ServeHTTP(wrapped, r)

            logger.Info("http request",
                "method", r.Method,
                "path", r.URL.Path,
                "status", wrapped.statusCode,
                "duration", time.Since(start),
                "remote_addr", r.RemoteAddr,
            )
        })
    }
}

type responseWriter struct {
    http.ResponseWriter
    statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
    rw.statusCode = code
    rw.ResponseWriter.WriteHeader(code)
}
```

### JWT Auth Middleware

```go
func jwtAuth(secretKey []byte) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            auth := r.Header.Get("Authorization")
            if !strings.HasPrefix(auth, "Bearer ") {
                writeError(w, &APIError{
                    Status: http.StatusUnauthorized, Code: "MISSING_TOKEN",
                    Message: "authorization header required",
                })
                return
            }

            tokenStr := strings.TrimPrefix(auth, "Bearer ")
            token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
                if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
                    return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
                }
                return secretKey, nil
            })

            if err != nil || !token.Valid {
                writeError(w, &APIError{
                    Status: http.StatusUnauthorized, Code: "INVALID_TOKEN",
                    Message: "invalid or expired token",
                })
                return
            }

            claims := token.Claims.(jwt.MapClaims)
            ctx := context.WithValue(r.Context(), userKey, claims["sub"])
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}
```

### CORS Middleware

```go
func corsMiddleware(allowedOrigins []string) func(http.Handler) http.Handler {
    allowed := make(map[string]bool)
    for _, o := range allowedOrigins {
        allowed[o] = true
    }

    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            origin := r.Header.Get("Origin")
            if allowed[origin] || allowed["*"] {
                w.Header().Set("Access-Control-Allow-Origin", origin)
                w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
                w.Header().Set("Access-Control-Max-Age", "86400")
            }

            // Handle preflight
            if r.Method == http.MethodOptions {
                w.WriteHeader(http.StatusNoContent)
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}
```

### Rate Limiting Middleware

```go
func rateLimiter(rps int, burst int) func(http.Handler) http.Handler {
    // Per-IP rate limiters
    type client struct {
        limiter  *rate.Limiter
        lastSeen time.Time
    }

    var (
        mu      sync.Mutex
        clients = make(map[string]*client)
    )

    // Cleanup goroutine
    go func() {
        for {
            time.Sleep(time.Minute)
            mu.Lock()
            for ip, c := range clients {
                if time.Since(c.lastSeen) > 3*time.Minute {
                    delete(clients, ip)
                }
            }
            mu.Unlock()
        }
    }()

    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            ip := r.RemoteAddr

            mu.Lock()
            if _, found := clients[ip]; !found {
                clients[ip] = &client{limiter: rate.NewLimiter(rate.Limit(rps), burst)}
            }
            clients[ip].lastSeen = time.Now()
            limiter := clients[ip].limiter
            mu.Unlock()

            if !limiter.Allow() {
                writeError(w, &APIError{
                    Status:  http.StatusTooManyRequests,
                    Code:    "RATE_LIMITED",
                    Message: "too many requests",
                })
                return
            }

            next.ServeHTTP(w, r)
        })
    }
}
```

### Request ID Middleware

```go
func requestID(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        id := r.Header.Get("X-Request-ID")
        if id == "" {
            id = uuid.New().String()
        }

        ctx := context.WithValue(r.Context(), requestIDKey, id)
        w.Header().Set("X-Request-ID", id)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

### Panic Recovery Middleware

```go
func recoverer(logger *slog.Logger) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            defer func() {
                if rvr := recover(); rvr != nil {
                    logger.Error("panic recovered",
                        "error", rvr,
                        "stack", string(debug.Stack()),
                        "path", r.URL.Path,
                    )
                    writeError(w, &APIError{
                        Status:  http.StatusInternalServerError,
                        Code:    "INTERNAL_ERROR",
                        Message: "internal server error",
                    })
                }
            }()
            next.ServeHTTP(w, r)
        })
    }
}
```

### Timeout Middleware

```go
func timeoutMiddleware(timeout time.Duration) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            ctx, cancel := context.WithTimeout(r.Context(), timeout)
            defer cancel()

            // http.TimeoutHandler wraps a handler with a timeout.
            // It returns 503 Service Unavailable if the handler doesn't finish in time.
            http.TimeoutHandler(next, timeout, "request timeout").ServeHTTP(w, r.WithContext(ctx))
        })
    }
}
```

---

## Graceful Shutdown

This is a critical production concern. You need to stop accepting new connections while letting in-flight requests finish.

### Full Graceful Shutdown Pattern

```go
func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

    srv := &http.Server{
        Addr:         ":8080",
        Handler:      setupRoutes(logger),
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    // Channel to listen for errors from the server
    serverErrors := make(chan error, 1)

    // Start server in a goroutine
    go func() {
        logger.Info("server starting", "addr", srv.Addr)
        serverErrors <- srv.ListenAndServe()
    }()

    // Channel to listen for OS signals
    shutdown := make(chan os.Signal, 1)
    signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

    // Block until we receive a signal or server error
    select {
    case err := <-serverErrors:
        logger.Error("server error", "error", err)

    case sig := <-shutdown:
        logger.Info("shutdown signal received", "signal", sig)

        // Give outstanding requests a deadline to complete
        ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()

        // Shutdown gracefully: stop accepting new connections,
        // wait for in-flight requests to complete.
        if err := srv.Shutdown(ctx); err != nil {
            logger.Error("graceful shutdown failed", "error", err)

            // Force close if graceful shutdown fails
            if err := srv.Close(); err != nil {
                logger.Error("forced close failed", "error", err)
            }
        }

        logger.Info("server stopped")
    }
}
```

### How Shutdown Works

1. `signal.Notify` registers to receive SIGINT (Ctrl+C) and SIGTERM (Docker/K8s stop).
2. `srv.Shutdown(ctx)` does three things:
   - Closes all listeners (stops accepting new connections).
   - Closes idle connections immediately.
   - Waits for active connections to finish (up to context deadline).
3. If the context times out, `Shutdown` returns an error. You can then call `Close()` to force-kill remaining connections.

### Connection Draining with Health Checks

In Kubernetes, you need to signal readiness before the pod terminates:

```go
type healthChecker struct {
    mu    sync.RWMutex
    ready bool
}

func (h *healthChecker) SetReady(ready bool) {
    h.mu.Lock()
    defer h.mu.Unlock()
    h.ready = ready
}

func (h *healthChecker) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
    h.mu.RLock()
    defer h.mu.RUnlock()

    if !h.ready {
        w.WriteHeader(http.StatusServiceUnavailable)
        w.Write([]byte(`{"status":"not_ready"}`))
        return
    }
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ready"}`))
}

// In main():
// 1. Set ready=true after all initialization completes
// 2. Set ready=false BEFORE calling srv.Shutdown()
// 3. Sleep briefly to let load balancer detect the change
```

---

## Framework Comparison

### When to Use stdlib (Go 1.22+)

The enhanced `ServeMux` is sufficient when you need:
- Method-based routing with path parameters
- Simple middleware composition
- No external dependencies

It lacks: route groups, named routes, automatic OPTIONS handling, built-in middleware suite.

### Chi

```go
r := chi.NewRouter()

// Built-in middleware
r.Use(middleware.Logger)
r.Use(middleware.Recoverer)
r.Use(middleware.RequestID)

// Route groups
r.Route("/api/v1", func(r chi.Router) {
    r.Use(authMiddleware)

    r.Get("/users", listUsers)
    r.Post("/users", createUser)
    r.Route("/users/{id}", func(r chi.Router) {
        r.Get("/", getUser)
        r.Put("/", updateUser)
        r.Delete("/", deleteUser)
    })
})
```

**Why Chi**: 100% compatible with `net/http`. All Chi handlers are `http.HandlerFunc`. All middleware uses `func(http.Handler) http.Handler`. You can mix stdlib and Chi handlers freely. Minimal API surface — easy to learn.

### Gin

```go
r := gin.Default() // Includes Logger and Recovery middleware

v1 := r.Group("/api/v1")
v1.Use(authMiddleware())
{
    v1.GET("/users", listUsers)
    v1.POST("/users", createUser)
    v1.GET("/users/:id", getUser)
    v1.PUT("/users/:id", updateUser)
    v1.DELETE("/users/:id", deleteUser)
}
```

**Why Gin**: Fastest router (radix tree), binding/validation built in (`c.ShouldBindJSON`), huge ecosystem. **Trade-off**: Uses its own `gin.Context` instead of standard `http.Handler` — you're locked into the Gin ecosystem.

### Echo

```go
e := echo.New()
e.Use(middleware.Logger())
e.Use(middleware.Recover())

v1 := e.Group("/api/v1")
v1.Use(authMiddleware)

v1.GET("/users", listUsers)
v1.POST("/users", createUser)
v1.GET("/users/:id", getUser)
```

**Why Echo**: Feature-rich (WebSocket support, HTTP/2, automatic TLS), good docs, data binding. **Trade-off**: Similar to Gin — custom context, not stdlib-compatible.

### Fiber

```go
app := fiber.New()

app.Get("/api/users", listUsers)
app.Post("/api/users", createUser)
app.Get("/api/users/:id", getUser)
```

**Why Fiber**: If you're coming from Express, Fiber will feel familiar. Built on fasthttp (not net/http) for performance. **Trade-off**: Not compatible with net/http — can't use standard middleware or handlers. Fasthttp has different semantics around connection reuse.

### Decision Matrix

| Factor | stdlib 1.22+ | Chi | Gin | Echo | Fiber |
|---|---|---|---|---|---|
| net/http compatible | Yes | Yes | No | No | No |
| Performance | Good | Good | Excellent | Good | Excellent |
| Middleware ecosystem | Manual | Rich | Rich | Rich | Rich |
| Learning curve | Low | Low | Medium | Medium | Low (for Express devs) |
| Route groups | No | Yes | Yes | Yes | Yes |
| Best for | Simple services | Most Go projects | High-perf APIs | Feature-rich APIs | Express migrants |

**Recommendation for interviews**: Know Chi well — it's the most "Go-idiomatic" framework and demonstrates that you understand stdlib compatibility. Know how to build the same service with stdlib for bonus points.

---

## Request/Response Patterns

### JSON Encoding/Decoding

```go
// Decode request body
func createUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest

    // Limit body size to prevent abuse
    r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MB

    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields() // Strict parsing — like TypeScript strict mode

    if err := dec.Decode(&req); err != nil {
        writeError(w, &APIError{
            Status: http.StatusBadRequest, Code: "INVALID_JSON",
            Message: "malformed request body",
        })
        return
    }

    // ... process request

    // Encode response
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(user)
}
```

### Streaming Responses (Server-Sent Events)

```go
func streamEvents(w http.ResponseWriter, r *http.Request) {
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "streaming not supported", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")

    for {
        select {
        case <-r.Context().Done():
            return // Client disconnected
        case event := <-eventChan:
            fmt.Fprintf(w, "data: %s\n\n", event)
            flusher.Flush()
        }
    }
}
```

### File Serving and Static Assets

```go
// Serve a directory
mux.Handle("GET /static/", http.StripPrefix("/static/",
    http.FileServer(http.Dir("./public"))))

// Serve embedded files (compiled into binary)
//go:embed static/*
var staticFS embed.FS

mux.Handle("GET /static/", http.FileServerFS(staticFS))

// Serve a single file download
func downloadHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Disposition", "attachment; filename=report.pdf")
    http.ServeFile(w, r, "/path/to/report.pdf")
}
```

### Multipart Uploads

```go
func uploadHandler(w http.ResponseWriter, r *http.Request) {
    // Limit upload size: 32 MB
    r.ParseMultipartForm(32 << 20)

    file, header, err := r.FormFile("upload")
    if err != nil {
        http.Error(w, "missing file", http.StatusBadRequest)
        return
    }
    defer file.Close()

    // header.Filename, header.Size, header.Header (MIME type)
    dst, err := os.Create(filepath.Join("uploads", header.Filename))
    if err != nil {
        http.Error(w, "failed to save", http.StatusInternalServerError)
        return
    }
    defer dst.Close()

    io.Copy(dst, file)
    w.WriteHeader(http.StatusCreated)
}
```

---

## Project Structure for HTTP Services

### Standard Layout

```
myservice/
├── cmd/
│   └── api/
│       └── main.go              # Entry point: wiring, server setup, shutdown
├── internal/
│   ├── config/
│   │   └── config.go            # Environment-based configuration
│   ├── handler/
│   │   ├── handler.go           # Base handler with shared dependencies
│   │   ├── user.go              # User-related HTTP handlers
│   │   └── health.go            # Health/readiness endpoints
│   ├── middleware/
│   │   ├── auth.go
│   │   ├── logging.go
│   │   └── cors.go
│   ├── service/
│   │   ├── user.go              # Business logic (domain layer)
│   │   └── user_test.go
│   ├── repository/
│   │   ├── user.go              # Data access (interface + implementation)
│   │   └── user_test.go
│   └── model/
│       ├── user.go              # Domain types
│       └── errors.go            # Domain errors
├── migrations/
│   ├── 001_create_users.up.sql
│   └── 001_create_users.down.sql
├── go.mod
├── go.sum
├── Dockerfile
└── Makefile
```

### Layer Responsibilities

```go
// internal/repository/user.go — data access interface
type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*model.User, error)
    Create(ctx context.Context, user *model.User) error
    List(ctx context.Context, opts ListOptions) ([]model.User, error)
}

// internal/service/user.go — business logic
type UserService struct {
    repo   UserRepository
    cache  CacheRepository
    logger *slog.Logger
}

func (s *UserService) GetUser(ctx context.Context, id int64) (*model.User, error) {
    // Check cache first
    if user, err := s.cache.GetUser(ctx, id); err == nil {
        return user, nil
    }

    user, err := s.repo.GetByID(ctx, id)
    if err != nil {
        return nil, fmt.Errorf("get user %d: %w", id, err)
    }

    // Populate cache
    s.cache.SetUser(ctx, user)
    return user, nil
}

// internal/handler/user.go — HTTP handlers
type UserHandler struct {
    service *service.UserService
}

func (h *UserHandler) GetUser(w http.ResponseWriter, r *http.Request) {
    id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
    if err != nil {
        writeError(w, &APIError{Status: 400, Code: "INVALID_ID", Message: "invalid user ID"})
        return
    }

    user, err := h.service.GetUser(r.Context(), id)
    if err != nil {
        // Map domain errors to HTTP errors
        if errors.Is(err, model.ErrNotFound) {
            writeError(w, &APIError{Status: 404, Code: "NOT_FOUND", Message: "user not found"})
            return
        }
        writeError(w, &APIError{Status: 500, Code: "INTERNAL", Message: "internal error"})
        return
    }

    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(user)
}
```

### Wiring in main.go

```go
// cmd/api/main.go
func main() {
    cfg := config.Load()
    logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))

    // Initialize dependencies bottom-up
    db := mustConnectDB(cfg.DatabaseURL)
    defer db.Close()

    userRepo := postgres.NewUserRepository(db)
    userSvc := service.NewUserService(userRepo, logger)
    userHandler := handler.NewUserHandler(userSvc)

    // Build router
    mux := http.NewServeMux()
    mux.HandleFunc("GET /api/users/{id}", userHandler.GetUser)
    mux.HandleFunc("POST /api/users", userHandler.CreateUser)

    // Apply middleware
    handler := Chain(mux,
        recoverer(logger),
        requestID,
        loggingMiddleware(logger),
        corsMiddleware(cfg.AllowedOrigins),
    )

    // Start server with graceful shutdown...
}
```

**Key insight for TypeScript engineers**: Go doesn't use dependency injection containers. You wire dependencies manually in `main()`. This feels tedious at first but gives you explicit, compile-time-checked dependency graphs — no runtime surprises from a DI container.

---

## Interview Questions

### Conceptual

1. **Explain the `http.Handler` interface and why it's the foundation of Go's HTTP ecosystem.**
   A single-method interface (`ServeHTTP(ResponseWriter, *Request)`) that every handler and middleware implements. Its simplicity enables universal composability — any middleware from any library works with any handler. The `HandlerFunc` adapter allows plain functions to satisfy the interface.

2. **How does Go's middleware pattern differ from Express middleware?**
   Express uses `(req, res, next)` where `next()` is called explicitly. Go uses `func(http.Handler) http.Handler` — a wrapper function that receives the next handler and returns a new handler. There's no `next()` function; you call `next.ServeHTTP(w, r)`. If you don't call it, the chain stops. This is more explicit and less error-prone (no forgotten `next()` calls).

3. **What happens if you write to `ResponseWriter` after calling `WriteHeader`?**
   The status code is already sent. Calling `WriteHeader` again is a no-op (logged as a superfluous call). Calling `Write` without `WriteHeader` first implicitly sends 200. Headers set after `Write` or `WriteHeader` are ignored because they've already been flushed to the network.

4. **How does `http.Server.Shutdown` achieve graceful shutdown?**
   It closes all listeners (stops new connections), closes idle connections immediately, then waits for active requests to complete. If the provided context expires before all requests finish, it returns `context.DeadlineExceeded`. It does NOT forcibly close active connections — you need `Close()` for that.

5. **When would you choose Chi over the Go 1.22+ stdlib router?**
   When you need route groups (applying middleware to a subset of routes), a rich middleware library, URL generation from named routes, or mounting sub-routers. Chi maintains full `net/http` compatibility while adding these features. The stdlib is sufficient for simple services with flat route structures.

### Coding Challenges

6. **Write a middleware that adds a timeout to every request and logs if the timeout is exceeded.**

7. **Implement a rate limiter middleware that uses a sliding window per API key (from header) rather than per IP.**

8. **Design an error-handling middleware that catches panics, logs the stack trace, and returns a structured JSON error response.**

9. **Build a handler that accepts a multipart file upload, validates the file type (only images), resizes it, and stores it — using proper error handling throughout.**

### Architecture

10. **You're designing a REST API with 50+ endpoints across multiple resource types. How do you structure the project? How do you organize routes, handlers, and middleware?**
    Use the cmd/internal layout. Group handlers by resource in internal/handler/. Use route groups (Chi or custom) to apply shared middleware (auth) to protected routes. Keep business logic in internal/service/ — handlers should only handle HTTP concerns (parsing, validation, serialization). Use interfaces for repository layer to enable testing.

11. **How would you implement request-scoped logging where every log line includes the request ID, user ID, and trace ID?**
    Inject these values into the context via middleware. Create a helper that extracts them and returns a logger with those fields pre-set: `func LoggerFromContext(ctx context.Context) *slog.Logger`. Every service method receives `ctx` and uses this helper.

12. **Compare deploying a Go HTTP service vs a Node.js Express service. What operational differences matter?**
    Go compiles to a single static binary — no node_modules, no runtime. Docker images can use `scratch` or `distroless` (10-20 MB vs 100+ MB for Node). Go handles concurrency with goroutines (cheap, thousands per service) vs Node's single-threaded event loop. Go services typically use less memory. Go's stdlib HTTP server is production-ready; Node needs reverse proxies or process managers.
