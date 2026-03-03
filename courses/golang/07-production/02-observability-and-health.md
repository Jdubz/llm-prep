# 02 – Observability and Health

This file assumes you have read `01-project-structure-and-configuration.md`. It covers structured logging with `slog`, Prometheus metrics, OpenTelemetry traces, health checks, and graceful shutdown.

---

## 1. Structured Logging with `slog`

Go 1.21 added `slog` to the standard library — the equivalent of `pino` or `winston` in Node.

### Basic Setup

```go
// Production: JSON output
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))
slog.SetDefault(logger)

slog.Info("server starting", "port", 8080, "version", "1.2.3")
// Output: {"time":"...","level":"INFO","msg":"server starting","port":8080,"version":"1.2.3"}

// Development: human-readable text output
logger = slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
    Level: slog.LevelDebug,
}))
```

### Logger with Persistent Context

Like `pino` child loggers, `slog.With` creates a logger with pre-attached attributes:

```go
// Request-scoped logger (like pino child loggers)
reqLogger := slog.With("request_id", requestID, "user_id", userID)
reqLogger.Info("processing request")
reqLogger.Error("request failed", "error", err)
// All output from reqLogger includes request_id and user_id automatically
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

### Custom slog Handler

For advanced use cases (log sampling, conditional formatting):

```go
type LevelHandler struct {
    level   slog.Level
    handler slog.Handler
}

func (h *LevelHandler) Enabled(_ context.Context, level slog.Level) bool {
    return level >= h.level
}

func (h *LevelHandler) Handle(ctx context.Context, r slog.Record) error {
    return h.handler.Handle(ctx, r)
}

func (h *LevelHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
    return &LevelHandler{h.level, h.handler.WithAttrs(attrs)}
}

func (h *LevelHandler) WithGroup(name string) slog.Handler {
    return &LevelHandler{h.level, h.handler.WithGroup(name)}
}
```

---

## 2. Prometheus Metrics

```go
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
    "github.com/prometheus/client_golang/prometheus/promhttp"
)

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

// Metrics middleware
func metricsMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        rw := &responseWriter{ResponseWriter: w, status: http.StatusOK}
        next.ServeHTTP(rw, r)

        duration := time.Since(start).Seconds()
        status := strconv.Itoa(rw.status)

        httpRequestsTotal.WithLabelValues(r.Method, r.URL.Path, status).Inc()
        httpRequestDuration.WithLabelValues(r.Method, r.URL.Path).Observe(duration)
    })
}

// Expose metrics endpoint
mux.Handle("GET /metrics", promhttp.Handler())
```

Use `promauto` to register metrics on package initialization. Expose via `promhttp.Handler()` on a `/metrics` endpoint. Add Prometheus annotations to your Kubernetes Deployment manifest:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

---

## 3. OpenTelemetry Traces

```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/propagation"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

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
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(res),
    )
    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
        propagation.TraceContext{}, propagation.Baggage{}))

    return tp.Shutdown, nil
}
```

Simplified setup template:

```go
func initTracer(ctx context.Context) (func(context.Context) error, error) {
    exp, _ := otlptracegrpc.New(ctx)
    res, _ := resource.Merge(resource.Default(),
        resource.NewWithAttributes(semconv.SchemaURL,
            semconv.ServiceName("myservice"),
            semconv.ServiceVersion("1.0.0"),
        ))
    tp := sdktrace.NewTracerProvider(
        sdktrace.WithBatcher(exp),
        sdktrace.WithResource(res),
    )
    otel.SetTracerProvider(tp)
    return tp.Shutdown, nil
}
```

Call `tp.Shutdown(ctx)` during graceful shutdown to flush any buffered spans.

---

## 4. Health Checks

### Liveness vs Readiness

| Check | Question | Failure Response |
|-------|----------|-----------------|
| Liveness | "Is the process stuck?" | Kubernetes restarts the pod |
| Readiness | "Can this pod serve traffic?" | Kubernetes removes from load balancer |
| Startup | "Has the app finished initializing?" | Kubernetes waits before sending traffic |

### Implementation

```go
func setupHealthRoutes(mux *http.ServeMux, db *sql.DB, rdb *redis.Client) {
    // Liveness: Is the process alive and not deadlocked?
    // Keep this simple — it should NEVER fail unless the process is truly broken.
    mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        fmt.Fprint(w, "ok")
    })

    // Readiness: Can we serve traffic?
    // Checks downstream dependencies with a timeout.
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

Condensed health check template:

```go
mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    fmt.Fprint(w, "ok")
})

mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    checks := map[string]error{"db": db.PingContext(ctx)}
    status := http.StatusOK
    for _, err := range checks {
        if err != nil {
            status = http.StatusServiceUnavailable
        }
    }
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(checks)
})
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
  failureThreshold: 30   # Up to 60s to start (30 × 2s)
  periodSeconds: 2
```

---

## 5. Graceful Shutdown and Signal Handling

In Node.js, you might use `process.on('SIGTERM', handler)` and call `server.close()`. Go's story is more explicit because you are managing goroutines, database connections, and background workers directly — there is no event loop that magically drains.

### The Full Graceful Shutdown Pattern

```go
func Run(ctx context.Context, cfg *Config) error {
    db, err := openDB(cfg.DatabaseURL)
    if err != nil {
        return fmt.Errorf("opening database: %w", err)
    }

    srv := &http.Server{
        Addr:         fmt.Sprintf(":%d", cfg.Port),
        Handler:      buildRoutes(db),
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  120 * time.Second,
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

    if err := srv.Shutdown(shutdownCtx); err != nil { // 1. Drain HTTP
        return fmt.Errorf("server shutdown: %w", err)
    }
    // 2. Stop background workers (cancel worker contexts)
    // 3. Flush buffered data (metrics, logs, traces)
    _ = db.Close() // 4. Close resources
    return nil
}
```

### Shutdown Ordering

The order matters — getting it wrong causes data loss or panics:

```
1. Stop accepting new requests    (srv.Shutdown)
2. Wait for in-flight requests    (srv.Shutdown handles this)
3. Stop background consumers      (cancel worker contexts)
4. Flush buffered data            (metrics, logs, traces)
5. Close external connections     (database, Redis, message queues)
```

TypeScript parallel: this is like calling `server.close()`, then `await Promise.all(inFlightRequests)`, then `await redis.quit()`, then `await pool.end()` — except Go makes you handle each phase explicitly.

---

## 6. Profiling in Production

### pprof Endpoints

Go has built-in profiling. Expose it on a separate, non-public port:

```go
import (
    "net/http"
    _ "net/http/pprof" // Registers /debug/pprof/* handlers on http.DefaultServeMux
)

func startDebugServer() {
    // Separate port — never expose via ingress
    go http.ListenAndServe(":6060", nil)
}
```

```bash
# CPU profile (30 seconds)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Heap profile
go tool pprof http://localhost:6060/debug/pprof/heap

# Goroutine dump (find leaks)
go tool pprof http://localhost:6060/debug/pprof/goroutine

# Via kubectl port-forward for production pods
kubectl port-forward pod/myservice-abc123 6060:6060
go tool pprof http://localhost:6060/debug/pprof/heap

# Interactive web UI with flame graph
go tool pprof -http=:8081 http://localhost:6060/debug/pprof/profile?seconds=30

# Generate SVG flame graph
go tool pprof -svg http://localhost:6060/debug/pprof/heap > heap.svg
```

### Continuous Profiling with Pyroscope

Pyroscope provides always-on profiling with minimal overhead (~2% CPU):

```go
import "github.com/grafana/pyroscope-go"

func initProfiling() {
    runtime.SetMutexProfileFraction(5)
    runtime.SetBlockProfileRate(5)

    pyroscope.Start(pyroscope.Config{
        ApplicationName: "myservice",
        ServerAddress:   os.Getenv("PYROSCOPE_SERVER"),
        Logger:          pyroscope.StandardLogger,
        Tags: map[string]string{
            "env":     os.Getenv("ENV"),
            "version": version.Version,
        },
        ProfileTypes: []pyroscope.ProfileType{
            pyroscope.ProfileCPU,
            pyroscope.ProfileAllocObjects,
            pyroscope.ProfileInuseSpace,
            pyroscope.ProfileGoroutines,
            pyroscope.ProfileMutexCount,
            pyroscope.ProfileBlockDuration,
        },
    })
}
```

---

## Related Reading

- **slog foundations** — [Module 03: Time, Logging, and Additional Stdlib](../03-stdlib/03-time-logging-and-additional-stdlib.md), section 2 (log/slog) covers the slog API basics that section 1 extends with production handlers and OpenTelemetry integration
- **HTTP middleware for instrumentation** — [Module 04: Handlers, Routing, and Middleware](../04-http-services/01-handlers-routing-and-middleware.md), section 4 (Middleware Implementations) shows how the logging and metrics middleware from sections 1–2 integrate into the middleware chain
- **Health checks in HTTP services** — [Module 04: Request Handling and Validation](../04-http-services/02-request-handling-and-validation.md), section 6 (Health Check Handler) implements the basic health check pattern that section 4 extends with Kubernetes probe types
- **Concurrency for graceful shutdown** — [Module 02: Synchronization and Context](../02-concurrency/02-synchronization-and-context.md), section 4 covers the `signal.NotifyContext` pattern used in section 5 (Graceful Shutdown)
- **Profiling benchmarks** — [Module 06: Benchmarking, Profiling, and Advanced Testing](../06-testing/03-benchmarking-profiling-and-advanced-testing.md), section 2 (Profiling) covers the development-time pprof usage that complements the production profiling in section 6
