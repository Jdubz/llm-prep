# Module 07: Production Go

## From Working Code to Production-Ready Services

You know how to ship Node.js to production. You have opinions about `tsconfig.json` strictness, you know the difference between `devDependencies` and `dependencies`, and you have battle scars from debugging memory leaks in long-running Express servers. This module translates that production engineering instinct into the Go ecosystem.

Go's production story is fundamentally different from Node's. There is no `node_modules` in your deployment artifact. There is no runtime to install on the server. You ship a single, statically linked binary. This simplicity is Go's superpower, but it comes with its own set of conventions, patterns, and footguns.

---

## Project Layout Conventions

### The Standard(ish) Go Project Layout

TypeScript projects have a loose consensus: `src/` for source, `dist/` for output, maybe `lib/` for shared code. Go's conventions are more specific and more meaningful because the directory structure directly affects import paths and visibility.

```
myservice/
├── cmd/
│   ├── server/
│   │   └── main.go          # Entry point for the server binary
│   └── cli/
│       └── main.go          # Entry point for the CLI binary
├── internal/
│   ├── auth/
│   │   ├── auth.go
│   │   └── auth_test.go
│   ├── handler/
│   │   ├── user.go
│   │   └── user_test.go
│   └── store/
│       ├── postgres.go
│       └── postgres_test.go
├── pkg/
│   └── middleware/
│       ├── logging.go
│       └── logging_test.go
├── api/
│   └── openapi.yaml
├── migrations/
│   ├── 001_create_users.up.sql
│   └── 001_create_users.down.sql
├── go.mod
├── go.sum
├── Makefile
├── Dockerfile
└── README.md
```

### `cmd/` — Binary Entry Points

Each subdirectory under `cmd/` produces one binary. The `main.go` file in each should be thin — it wires dependencies together and calls into your actual application code.

```go
// cmd/server/main.go
package main

import (
    "context"
    "log/slog"
    "os"
    "os/signal"
    "syscall"

    "github.com/yourorg/myservice/internal/config"
    "github.com/yourorg/myservice/internal/server"
)

func main() {
    cfg, err := config.Load()
    if err != nil {
        slog.Error("failed to load config", "error", err)
        os.Exit(1)
    }

    ctx, cancel := signal.NotifyContext(context.Background(),
        syscall.SIGINT, syscall.SIGTERM)
    defer cancel()

    if err := server.Run(ctx, cfg); err != nil {
        slog.Error("server exited with error", "error", err)
        os.Exit(1)
    }
}
```

**TypeScript parallel:** Think of each `cmd/` subdirectory like a separate `apps/server` or `apps/cli` in a Turborepo monorepo. Each is an independently buildable entry point.

### `internal/` — Compiler-Enforced Privacy

This is the killer feature that TypeScript does not have. Code under `internal/` is **only importable by code within the parent of the `internal/` directory**. The Go compiler enforces this. It is not a convention — it is a language guarantee.

```
myservice/
├── internal/
│   └── auth/        # Only importable by code under myservice/
└── cmd/
    └── server/      # Can import myservice/internal/auth
```

An external package that does `import "github.com/yourorg/myservice/internal/auth"` will get a compile error. This is the Go equivalent of not exporting from your package's `index.ts`.

### `pkg/` — The Controversial Directory

The `pkg/` directory signals "this code is intended to be imported by external consumers." It is controversial because **every non-internal package is already importable**. The `pkg/` directory is redundant from the compiler's perspective.

**Arguments for `pkg/`:**
- Makes intent explicit to human readers
- Common in large projects like Kubernetes (`k8s.io/kubernetes/pkg/`)
- Provides visual separation between public API and internals

**Arguments against `pkg/`:**
- Adds unnecessary nesting to import paths
- The Go team does not use it in the standard library
- "If everything is in `pkg/`, then `pkg/` is meaningless"

**The pragmatic answer:** Use `internal/` aggressively. Only create `pkg/` if you are building a library that external teams will import and you want to be explicit about what constitutes your public API. For most microservices, you do not need `pkg/` at all.

### Real-World Examples

| Project | Layout | Notes |
|---------|--------|-------|
| Kubernetes | `cmd/`, `pkg/`, `internal/` | Uses all three; `pkg/` is massive |
| Docker/Moby | `cmd/`, `internal/` | Moved away from `pkg/` |
| CockroachDB | `pkg/` heavily | Monorepo with extensive `pkg/` |
| HashiCorp Vault | `cmd/`, `internal/`, `sdk/` | Uses `sdk/` instead of `pkg/` |
| Standard Library | Flat packages | No `cmd/`, `internal/`, or `pkg/` |

---

## Configuration Management

### The Configuration Hierarchy

In TypeScript, you might use `dotenv`, `convict`, or `config` packages. Go's ecosystem has a similar layered approach, but the conventions are stricter around 12-factor app principles.

**Priority order (highest to lowest):**
1. Command-line flags
2. Environment variables
3. Config file values
4. Default values

### Environment Variables with `os`

The simplest approach, and often sufficient for containerized services:

```go
package config

import (
    "fmt"
    "os"
    "strconv"
    "time"
)

type Config struct {
    Port            int
    DatabaseURL     string
    LogLevel        string
    ShutdownTimeout time.Duration
}

func Load() (*Config, error) {
    port, err := strconv.Atoi(getEnv("PORT", "8080"))
    if err != nil {
        return nil, fmt.Errorf("invalid PORT: %w", err)
    }

    dbURL := os.Getenv("DATABASE_URL")
    if dbURL == "" {
        return nil, fmt.Errorf("DATABASE_URL is required")
    }

    timeout, err := time.ParseDuration(getEnv("SHUTDOWN_TIMEOUT", "30s"))
    if err != nil {
        return nil, fmt.Errorf("invalid SHUTDOWN_TIMEOUT: %w", err)
    }

    return &Config{
        Port:            port,
        DatabaseURL:     dbURL,
        LogLevel:        getEnv("LOG_LEVEL", "info"),
        ShutdownTimeout: timeout,
    }, nil
}

func getEnv(key, fallback string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return fallback
}
```

### Flags with `pflag`

The standard `flag` package uses single-dash flags (`-port`). The `pflag` package provides POSIX-style double-dash flags (`--port`) that your users expect:

```go
port := pflag.Int("port", 8080, "server port")
debug := pflag.Bool("debug", false, "enable debug mode")
pflag.Parse()
```

### Configuration with Viper

Viper is the heavy-duty config solution — analogous to `convict` in Node but more featureful. It supports layered config (file + env + flags):

```go
func Load() (*Config, error) {
    v := viper.New()

    v.SetDefault("server.port", 8080)
    v.SetDefault("server.host", "0.0.0.0")

    v.SetConfigName("config")
    v.SetConfigType("yaml")
    v.AddConfigPath(".")

    // Environment variables: MYSERVICE_DATABASE_HOST -> database.host
    v.SetEnvPrefix("MYSERVICE")
    v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
    v.AutomaticEnv()

    if err := v.ReadInConfig(); err != nil {
        if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
            return nil, fmt.Errorf("reading config: %w", err)
        }
    }

    var cfg Config
    if err := v.Unmarshal(&cfg); err != nil {
        return nil, fmt.Errorf("unmarshaling config: %w", err)
    }
    return &cfg, nil
}
```

### Configuration Validation

Go has no decorators like `class-validator`. Validate explicitly by collecting errors into a slice and joining with `errors.Join`:

```go
func (c *Config) Validate() error {
    var errs []error
    if c.Server.Port < 1 || c.Server.Port > 65535 {
        errs = append(errs, fmt.Errorf("invalid port: %d", c.Server.Port))
    }
    if c.Database.Host == "" {
        errs = append(errs, fmt.Errorf("database.host is required"))
    }
    return errors.Join(errs...)  // Returns nil if errs is empty
}
```

---

## Graceful Shutdown and Signal Handling

### Why This Matters More in Go

In Node.js, you might use `process.on('SIGTERM', handler)` and call `server.close()`. Go's story is more explicit because you are managing goroutines, database connections, and background workers directly — there is no event loop that magically drains for you.

### The Full Graceful Shutdown Pattern

```go
func Run(ctx context.Context, cfg *Config) error {
    db, err := openDB(cfg.DatabaseURL)
    if err != nil {
        return fmt.Errorf("opening database: %w", err)
    }

    srv := &http.Server{
        Addr:    fmt.Sprintf(":%d", cfg.Port),
        Handler: buildRoutes(db),
    }

    errCh := make(chan error, 1)
    go func() {
        if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
            errCh <- err
        }
        close(errCh)
    }()

    select {
    case err := <-errCh:
        return fmt.Errorf("server error: %w", err)
    case <-ctx.Done():
        slog.Info("shutdown signal received")
    }

    shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
    defer cancel()

    if err := srv.Shutdown(shutdownCtx); err != nil {
        return fmt.Errorf("server shutdown: %w", err)
    }
    // Phase 2: Stop background workers (cancel worker contexts)
    // Phase 3: Flush data (metrics, logs, traces)
    _ = db.Close()  // Phase 4: Close resources
    return nil
}
```

### Shutdown Ordering

The order matters. Get it wrong and you lose data or get panics:

```
1. Stop accepting new requests    (srv.Shutdown)
2. Wait for in-flight requests    (srv.Shutdown handles this)
3. Stop background consumers      (cancel worker contexts)
4. Flush buffered data            (metrics, logs, traces)
5. Close external connections     (database, Redis, message queues)
```

**TypeScript parallel:** This is like calling `server.close()`, then `await Promise.all(inFlightRequests)`, then `await redis.quit()`, then `await pool.end()` — except Go makes you handle each phase explicitly.

---

## Docker Builds

### The Standard Multi-Stage Dockerfile

```dockerfile
# Stage 1: Build
FROM golang:1.23-alpine AS builder

WORKDIR /app

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Build the binary
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

# Stage 2: Runtime
FROM gcr.io/distroless/static-debian12

COPY --from=builder /server /server

EXPOSE 8080
ENTRYPOINT ["/server"]
```

### Key Build Flags Explained

| Flag | Purpose |
|------|---------|
| `CGO_ENABLED=0` | Disable C interop for fully static binary |
| `GOOS=linux` | Target Linux (even from macOS build) |
| `-ldflags="-s -w"` | Strip debug info and symbol table (~30% smaller) |
| `-trimpath` | Remove local filesystem paths from binary |

### Why Distroless Over Scratch

`scratch` is an empty image — literally nothing. `distroless` includes CA certificates (for HTTPS), timezone data, and a `nonroot` user. With `scratch`, you must `COPY` these manually from the builder.

### Layer Caching Strategy

Copy `go.mod`/`go.sum` first, run `go mod download`, then copy source. Docker caches the dependency layer until `go.mod` changes. Same principle as copying `package.json` before `npm ci` in Node builds.

---

## Observability

### Structured Logging with `slog`

Go 1.21 added `slog` to the standard library — the equivalent of `pino` or `winston` in Node:

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))
slog.SetDefault(logger)

slog.Info("server starting", "port", 8080, "version", "1.2.3")
// Output: {"time":"...","level":"INFO","msg":"server starting","port":8080,"version":"1.2.3"}

// Logger with persistent context (like pino child loggers)
reqLogger := slog.With("request_id", "abc-123", "user_id", 42)
reqLogger.Info("processing request")
```

### Request-Scoped Logging Middleware

```go
func LoggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        requestID := r.Header.Get("X-Request-ID")
        if requestID == "" {
            requestID = uuid.New().String()
        }

        // Add logger to context
        logger := slog.With(
            "request_id", requestID,
            "method", r.Method,
            "path", r.URL.Path,
        )
        ctx := ContextWithLogger(r.Context(), logger)

        // Wrap response writer to capture status
        wrapped := &responseWriter{ResponseWriter: w, status: http.StatusOK}
        next.ServeHTTP(wrapped, r.WithContext(ctx))

        logger.Info("request completed",
            "status", wrapped.status,
            "duration_ms", time.Since(start).Milliseconds(),
        )
    })
}
```

### Prometheus Metrics

```go
var (
    httpRequestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "http_requests_total",
            Help: "Total number of HTTP requests",
        },
        []string{"method", "path", "status"},
    )
    httpRequestDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name:    "http_request_duration_seconds",
            Help:    "HTTP request duration in seconds",
            Buckets: prometheus.DefBuckets,
        },
        []string{"method", "path"},
    )
)
```

Use `promauto` to register metrics, then update them in middleware. Expose via `promhttp.Handler()` on a `/metrics` endpoint.

### OpenTelemetry Traces

```go
func InitTracer(ctx context.Context, serviceName, version string) (func(context.Context) error, error) {
    exporter, err := otlptracegrpc.New(ctx)
    if err != nil {
        return nil, fmt.Errorf("creating trace exporter: %w", err)
    }

    res, _ := resource.Merge(resource.Default(),
        resource.NewWithAttributes(semconv.SchemaURL,
            semconv.ServiceName(serviceName),
            semconv.ServiceVersion(version)))

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exporter), sdktrace.WithResource(res))
    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
        propagation.TraceContext{}, propagation.Baggage{}))

    return tp.Shutdown, nil
}
```

---

## Error Wrapping and Stack Traces

### Error Wrapping with `%w`

```go
func GetUser(ctx context.Context, id int64) (*User, error) {
    user, err := db.QueryUser(ctx, id)
    if err != nil {
        // Wrap with context — the %w verb preserves the error chain
        return nil, fmt.Errorf("getting user %d: %w", id, err)
    }
    return user, nil
}

// Callers can unwrap and check the underlying error
user, err := GetUser(ctx, 42)
if err != nil {
    if errors.Is(err, sql.ErrNoRows) {
        // Handle not found
    }
    // Handle other errors
}
```

### Joining Multiple Errors (Go 1.20+)

```go
func ValidateUser(u *User) error {
    var errs []error

    if u.Name == "" {
        errs = append(errs, fmt.Errorf("name is required"))
    }
    if u.Email == "" {
        errs = append(errs, fmt.Errorf("email is required"))
    }
    if u.Age < 0 {
        errs = append(errs, fmt.Errorf("age must be non-negative"))
    }

    return errors.Join(errs...)  // Returns nil if errs is empty
}
```

### Operational vs Programmer Errors

**TypeScript parallel:** You know the difference between `throw new Error("user not found")` (operational) and a null pointer dereference (programmer error). Go makes this distinction explicit.

```go
// Operational errors — expected, handled, part of your API
var (
    ErrNotFound     = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
    ErrConflict     = errors.New("conflict")
)

// Use sentinel errors for known failure modes
func GetUser(ctx context.Context, id int64) (*User, error) {
    user, err := store.Find(ctx, id)
    if errors.Is(err, sql.ErrNoRows) {
        return nil, fmt.Errorf("user %d: %w", id, ErrNotFound)
    }
    if err != nil {
        // This is unexpected — wrap and propagate
        return nil, fmt.Errorf("querying user %d: %w", id, err)
    }
    return user, nil
}
```

### Error Handling Middleware

Define a handler type that returns errors, and middleware that maps error types to HTTP responses:

```go
type AppError struct {
    Code    int    `json:"-"`
    Message string `json:"message"`
    Err     error  `json:"-"`
}
func (e *AppError) Error() string { return e.Err.Error() }
func (e *AppError) Unwrap() error { return e.Err }

type HandlerFunc func(w http.ResponseWriter, r *http.Request) error

func ErrorHandler(h HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if err := h(w, r); err != nil {
            var appErr *AppError
            if errors.As(err, &appErr) {
                writeJSON(w, appErr.Code, appErr)
            } else {
                slog.Error("unhandled error", "error", err)
                writeJSON(w, 500, map[string]string{"message": "internal server error"})
            }
        }
    }
}
```

---

## Health Checks

### Liveness vs Readiness

| Check | Question | Failure Response |
|-------|----------|-----------------|
| Liveness | "Is the process stuck?" | Kubernetes restarts the pod |
| Readiness | "Can this pod serve traffic?" | Kubernetes removes from load balancer |

```go
func setupHealthRoutes(mux *http.ServeMux, db *sql.DB, rdb *redis.Client) {
    // Liveness: Is the process alive and not deadlocked?
    mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("ok"))
    })

    // Readiness: Can we serve traffic?
    mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
        ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
        defer cancel()

        checks := map[string]error{
            "database": db.PingContext(ctx),
            "redis":    rdb.Ping(ctx).Err(),
        }

        status := http.StatusOK
        result := make(map[string]string)
        for name, err := range checks {
            if err != nil {
                status = http.StatusServiceUnavailable
                result[name] = err.Error()
            } else {
                result[name] = "ok"
            }
        }

        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(status)
        json.NewEncoder(w).Encode(result)
    })
}
```

### Kubernetes Probe Configuration

```yaml
livenessProbe:
  httpGet: { path: /healthz, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 10
readinessProbe:
  httpGet: { path: /readyz, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 5
startupProbe:
  httpGet: { path: /healthz, port: 8080 }
  failureThreshold: 30
  periodSeconds: 2
```

---

## Release and Versioning

### Version Injection with `ldflags`

Go has no `package.json` to read at runtime. Instead, inject version information at build time:

```go
// internal/version/version.go
package version

var (
    Version   = "dev"
    Commit    = "unknown"
    BuildDate = "unknown"
)
```

```bash
go build -ldflags="\
  -X github.com/yourorg/myservice/internal/version.Version=1.2.3 \
  -X github.com/yourorg/myservice/internal/version.Commit=$(git rev-parse --short HEAD) \
  -X github.com/yourorg/myservice/internal/version.BuildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  -s -w" -o myservice ./cmd/server
```

### GoReleaser

GoReleaser automates cross-compilation, Docker images, and GitHub releases. Configure `.goreleaser.yaml` with build targets (`goos`, `goarch`), ldflags for version injection, Docker image templates, and changelog generation. It is the Go equivalent of `semantic-release` — run `goreleaser release` and it produces binaries for every platform, Docker images, and a GitHub release with changelog.

---

## Interview Questions

### Q1: How would you structure a Go project with multiple services?

**Strong answer:** Monorepo with `cmd/` subdirectories per service, `internal/` for service-specific code, shared packages at root or in `pkg/`. Each `cmd/` entry point is thin. Single `go.mod` or Go workspaces for multi-module repos depending on release cadence.

### Q2: Walk me through your Docker build strategy for a Go service.

**Strong answer:** Multi-stage build. Builder stage copies `go.mod`/`go.sum` first for layer caching, builds with `CGO_ENABLED=0 -ldflags='-s -w'`. Runtime stage uses `distroless/static` for 10-20MB final images. Version info injected via ldflags.

### Q3: How do you implement graceful shutdown in a Go service?

**Strong answer:** `signal.NotifyContext` creates a context cancelling on SIGTERM/SIGINT. On cancellation: `srv.Shutdown(ctx)` drains HTTP, then cancel worker contexts, flush metrics/traces, close database. Order matters — do not close DB before in-flight requests finish.

### Q4: How do you handle configuration in a Go service?

**Strong answer:** 12-factor model. Env vars primary, struct with `Load()` function, explicit validation. Config struct created once in `main` and passed as dependency, never global.

### Q5: What is the difference between `internal/` and `pkg/` directories?

**Strong answer:** "`internal/` is compiler-enforced: code under it can only be imported by the parent module. `pkg/` is a convention signaling public API — not enforced by the compiler. For most services, I use `internal/` heavily and skip `pkg/`."

### Q6: How do you approach observability in a Go service?

**Strong answer:** "Three pillars. Structured logging with `slog` (JSON in production). Metrics with Prometheus client — counters for request totals, histograms for latency. Distributed tracing with OpenTelemetry SDK. All tied together through request IDs propagated via context. Logging and metrics are HTTP middleware so every request is instrumented automatically."

### Q7: How do you distinguish operational errors from programmer errors?

**Strong answer:** "Operational errors are expected (timeouts, validation, not-found) — I use sentinel errors and handle explicitly. Programmer errors are bugs (nil pointer, index out of bounds) — these panic. I wrap errors with `%w` so callers use `errors.Is`/`errors.As` to make decisions."

### Q8: How do liveness and readiness probes differ?

**Strong answer:** "Liveness: 'is the process stuck?' — failure triggers restart, keep it simple (return 200). Readiness: 'can it serve traffic?' — failure removes from load balancer, checks dependencies (DB, cache) with short timeouts. Startup probes handle slow initialization."
