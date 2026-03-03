# 01 – Handlers, Routing, and Middleware

## Overview

Go was built for the internet. The standard library's `net/http` package is production-grade out of the box — something that will feel unusual coming from TypeScript where you'd never ship Express without a dozen middleware packages. Go 1.22 brought significant routing improvements that close the gap with third-party routers, making the stdlib viable for most HTTP services.

---

## 1. net/http Fundamentals

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

This is the **adapter pattern** — it lets any function with the right signature satisfy the `Handler` interface.

```go
// These are equivalent:
http.Handle("/health", http.HandlerFunc(healthCheck))
http.HandleFunc("/health", healthCheck)

func healthCheck(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ok"}`))
}
```

### Handler Template

```go
func myHandler(w http.ResponseWriter, r *http.Request) {
    // 1. Parse input
    id := r.PathValue("id") // Go 1.22+

    // 2. Validate
    if id == "" {
        http.Error(w, `{"error":"missing id"}`, http.StatusBadRequest)
        return
    }

    // 3. Call service
    result, err := svc.Get(r.Context(), id)
    if err != nil {
        http.Error(w, `{"error":"internal"}`, http.StatusInternalServerError)
        return
    }

    // 4. Respond
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(result)
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

**Key rule**: Once you call `Write()` or `WriteHeader()`, headers are flushed. If you call `Write()` without `WriteHeader()`, Go implicitly sends 200.

### Key Gotchas

- Always set headers BEFORE calling `WriteHeader()` or `Write()`
- Always close `resp.Body` on HTTP client responses
- Always use `http.MaxBytesReader` to limit request body size
- Never use zero-value `http.Client{}` in production (no timeout)
- Use unexported types for context keys to avoid collisions
- `ListenAndServe` always returns non-nil error (`ErrServerClosed` on shutdown)

---

## 2. Handler Chains and the Middleware Pattern

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

### Middleware Template

```go
func myMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Before
        next.ServeHTTP(w, r)
        // After
    })
}

// With config (closure pattern):
func myMiddleware(cfg Config) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            // Use cfg here
            next.ServeHTTP(w, r)
        })
    }
}
```

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

### Context Value Pattern

```go
type contextKey string
const userKey contextKey = "user"

// Set in middleware:
ctx := context.WithValue(r.Context(), userKey, user)
next.ServeHTTP(w, r.WithContext(ctx))

// Get in handler:
user := r.Context().Value(userKey).(*User)
```

### Common Middleware Checklist

| Middleware | Purpose | Typical Order |
|---|---|---|
| Recovery/Panic | Catch panics, return 500 | Outermost |
| Request ID | Generate/propagate trace ID | Early |
| Logging | Log method, path, status, duration | Early |
| CORS | Set CORS headers, handle preflight | Before auth |
| Rate Limit | Per-IP or per-key throttling | Before auth |
| Auth/JWT | Validate token, set user in context | After logging |
| Timeout | Cancel long-running requests | Before handlers |
| Compress | gzip response bodies | Before handlers |

---

## 3. ServeMux Routing (Go 1.22+)

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

### Router Setup: stdlib (Go 1.22+)

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /api/users", listUsers)
mux.HandleFunc("POST /api/users", createUser)
mux.HandleFunc("GET /api/users/{id}", getUser)
mux.HandleFunc("PUT /api/users/{id}", updateUser)
mux.HandleFunc("DELETE /api/users/{id}", deleteUser)
mux.HandleFunc("GET /static/{path...}", serveStatic)
```

### Host-Based Routing

```go
mux.HandleFunc("GET api.example.com/users", apiListUsers)
mux.HandleFunc("GET www.example.com/users", webListUsers)
```

---

## 4. Framework Comparison

### Router Setup: Chi

```go
r := chi.NewRouter()
r.Use(middleware.Logger, middleware.Recoverer, middleware.RequestID)

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

### Router Setup: Gin

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

### Router Setup: Echo

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

**Why Echo**: Feature-rich (WebSocket support, HTTP/2, automatic TLS), good docs, data binding. **Trade-off**: Custom context, not stdlib-compatible.

### Framework Decision Matrix

| Feature | stdlib 1.22+ | Chi | Gin | Echo | Fiber |
|---|---|---|---|---|---|
| net/http compat | Yes | Yes | No | No | No |
| Route groups | No | Yes | Yes | Yes | Yes |
| Path params | `{id}` | `{id}` | `:id` | `:id` | `:id` |
| Wildcard | `{p...}` | `*` | `*path` | `*` | `*` |
| Middleware style | `func(H)H` | `func(H)H` | `gin.HandlerFunc` | `echo.MiddlewareFunc` | `fiber.Handler` |
| Built-in middleware | None | Rich set | Logger, Recovery | Logger, Recover, CORS | Logger, Recover, CORS |
| Best for | Simple APIs | Most Go projects | High-perf APIs | Feature-rich APIs | Express migrants |

**Recommendation for interviews**: Know Chi well — it's the most "Go-idiomatic" framework and demonstrates that you understand stdlib compatibility. Know how to build the same service with stdlib for bonus points.

---

## 5. Middleware Implementations

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

## 6. Project Structure for HTTP Services

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
    app := Chain(mux,
        recoverer(logger),
        requestID,
        loggingMiddleware(logger),
        corsMiddleware(cfg.AllowedOrigins),
    )

    // Start server with graceful shutdown...
}
```

**Key insight for TypeScript engineers**: Go doesn't use dependency injection containers. You wire dependencies manually in `main()`. This feels tedious at first but gives you explicit, compile-time-checked dependency graphs — no runtime surprises from a DI container.
