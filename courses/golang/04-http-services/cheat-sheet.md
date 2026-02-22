# Module 04 Cheat Sheet: HTTP Services

## Handler Template

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

## Middleware Template

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

## Router Setup: stdlib (Go 1.22+)

```go
mux := http.NewServeMux()
mux.HandleFunc("GET /api/users", listUsers)
mux.HandleFunc("POST /api/users", createUser)
mux.HandleFunc("GET /api/users/{id}", getUser)
mux.HandleFunc("PUT /api/users/{id}", updateUser)
mux.HandleFunc("DELETE /api/users/{id}", deleteUser)
mux.HandleFunc("GET /static/{path...}", serveStatic)
```

## Router Setup: Chi

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

## Graceful Shutdown Template

```go
srv := &http.Server{
    Addr:         ":8080",
    Handler:      handler,
    ReadTimeout:  5 * time.Second,
    WriteTimeout: 10 * time.Second,
    IdleTimeout:  120 * time.Second,
}

go func() { serverErr <- srv.ListenAndServe() }()

quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
<-quit

ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()
srv.Shutdown(ctx)
```

## Framework Comparison

| Feature | stdlib 1.22+ | Chi | Gin | Echo | Fiber |
|---|---|---|---|---|---|
| net/http compat | Yes | Yes | No | No | No |
| Route groups | No | Yes | Yes | Yes | Yes |
| Path params | `{id}` | `{id}` | `:id` | `:id` | `:id` |
| Wildcard | `{p...}` | `*` | `*path` | `*` | `*` |
| Middleware style | `func(H)H` | `func(H)H` | `gin.HandlerFunc` | `echo.MiddlewareFunc` | `fiber.Handler` |
| Built-in middleware | None | Rich set | Logger, Recovery | Logger, Recover, CORS | Logger, Recover, CORS |
| Best for | Simple APIs | Most Go projects | High-perf APIs | Feature-rich APIs | Express migrants |

## Project Structure

```
cmd/api/main.go              # Entry point, wiring
internal/config/config.go    # Env-based config
internal/handler/             # HTTP handlers (thin)
internal/middleware/           # HTTP middleware
internal/service/             # Business logic
internal/repository/          # Data access (interfaces)
internal/model/               # Domain types
migrations/                   # SQL migrations
```

## Common Middleware Checklist

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

## JSON Response Helper

```go
func writeJSON(w http.ResponseWriter, status int, data any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, code, message string) {
    writeJSON(w, status, map[string]string{
        "code":    code,
        "message": message,
    })
}
```

## HTTP Client Template

```go
client := &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}

// Per-request with context:
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
resp, err := client.Do(req)
if err != nil { /* handle */ }
defer resp.Body.Close()
```

## Context Value Pattern

```go
type contextKey string
const userKey contextKey = "user"

// Set in middleware:
ctx := context.WithValue(r.Context(), userKey, user)
next.ServeHTTP(w, r.WithContext(ctx))

// Get in handler:
user := r.Context().Value(userKey).(*User)
```

## Key Gotchas

- Always set headers BEFORE calling `WriteHeader()` or `Write()`
- Always close `resp.Body` on HTTP client responses
- Always use `http.MaxBytesReader` to limit request body size
- Never use zero-value `http.Client{}` in production (no timeout)
- Use unexported types for context keys to avoid collisions
- `ListenAndServe` always returns non-nil error (`ErrServerClosed` on shutdown)
