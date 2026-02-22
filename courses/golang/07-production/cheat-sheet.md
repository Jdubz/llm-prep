# Module 07: Cheat Sheet — Production Go

## Project Layout Template

```
myservice/
├── cmd/
│   └── server/
│       └── main.go           # Thin entry point, wires dependencies
├── internal/
│   ├── config/               # Configuration loading and validation
│   ├── handler/              # HTTP handlers
│   ├── middleware/            # HTTP middleware
│   ├── service/              # Business logic
│   ├── store/                # Database access
│   └── version/              # Build-time version info
├── migrations/               # SQL migrations
├── api/                      # OpenAPI specs, proto files
├── go.mod
├── go.sum
├── Dockerfile
├── Makefile
└── .goreleaser.yaml
```

---

## Dockerfile Template

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.23-alpine AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build \
    -ldflags="-s -w \
      -X github.com/yourorg/myservice/internal/version.Version=${VERSION:-dev} \
      -X github.com/yourorg/myservice/internal/version.Commit=${COMMIT:-unknown}" \
    -trimpath -o /server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

---

## Graceful Shutdown Template

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
        return err
    case <-ctx.Done():
    }

    shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()

    _ = srv.Shutdown(shutdownCtx)   // 1. Drain HTTP
    // 2. Stop workers              // cancel worker contexts
    // 3. Flush buffers             // traceProvider.Shutdown(ctx)
    _ = db.Close()                  // 4. Close connections
    return nil
}
```

---

## OpenTelemetry Setup Template

```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

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

---

## slog Configuration

```go
// Production (JSON) | Development (text)
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
slog.SetDefault(logger)

// Request-scoped logger (like pino child loggers)
reqLogger := slog.With("request_id", requestID, "user_id", userID)
```

---

## Health Check Template

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
    for name, err := range checks {
        if err != nil { status = http.StatusServiceUnavailable }
    }
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(checks)
})
```

---

## Makefile Essentials

```makefile
VERSION := $(shell git describe --tags --always --dirty)
COMMIT  := $(shell git rev-parse --short HEAD)
LDFLAGS := -s -w -X main.version=$(VERSION) -X main.commit=$(COMMIT)

build:
	CGO_ENABLED=0 go build -ldflags="$(LDFLAGS)" -trimpath -o bin/server ./cmd/server
test:
	go test -race -cover ./...
lint:
	golangci-lint run ./...
docker:
	docker build -t myservice:$(VERSION) .
```

---

## Quick Reference

| Concern | Tool/Pattern |
|---------|-------------|
| Project structure | `cmd/`, `internal/` |
| Config | `os.Getenv` + struct, Viper for layering |
| Logging | `slog` (stdlib) |
| Metrics | `prometheus/client_golang` |
| Tracing | OpenTelemetry Go SDK |
| Graceful shutdown | `signal.NotifyContext` |
| Container image | Distroless / scratch |
| Binary size | `-ldflags="-s -w"` |
| Release | GoReleaser |
| Health checks | `/healthz`, `/readyz` |
