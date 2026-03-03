# 01 – Project Structure and Configuration

Go's production story is fundamentally different from Node's. There is no `node_modules` in your deployment artifact. There is no runtime to install on the server. You ship a single, statically linked binary. This simplicity is Go's superpower, but it comes with its own set of conventions, patterns, and footguns.

---

## 1. Project Layout Conventions

### The Standard Go Project Layout

TypeScript projects have loose consensus: `src/` for source, `dist/` for output, maybe `lib/` for shared code. Go's conventions are more specific and more meaningful because the directory structure directly affects import paths and visibility.

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
│   ├── config/              # Configuration loading and validation
│   ├── service/             # Business logic
│   ├── store/               # Database access
│   │   ├── postgres.go
│   │   └── postgres_test.go
│   ├── middleware/          # HTTP middleware
│   └── version/             # Build-time version info
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
└── .goreleaser.yaml
```

### `cmd/` — Binary Entry Points

Each subdirectory under `cmd/` produces one binary. The `main.go` in each should be thin — it wires dependencies together and calls into your actual application code.

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

TypeScript parallel: think of each `cmd/` subdirectory like a separate `apps/server` or `apps/cli` in a Turborepo monorepo.

### `internal/` — Compiler-Enforced Privacy

This is the killer feature TypeScript does not have. Code under `internal/` is **only importable by code within the parent of the `internal/` directory**. The Go compiler enforces this — it is not a convention, it is a language guarantee.

```
myservice/
├── internal/
│   └── auth/        # Only importable by code under myservice/
└── cmd/
    └── server/      # Can import myservice/internal/auth
```

An external package attempting `import "github.com/yourorg/myservice/internal/auth"` gets a compile error. This is Go's equivalent of not exporting from your package's `index.ts`.

### `pkg/` — The Controversial Directory

The `pkg/` directory signals "this code is intended to be imported by external consumers." It is controversial because every non-internal package is already importable. The `pkg/` directory is redundant from the compiler's perspective.

**Arguments for `pkg/`:** Makes intent explicit, common in large projects like Kubernetes.
**Arguments against `pkg/`:** Adds unnecessary nesting, the Go team does not use it in the standard library.

**The pragmatic answer:** Use `internal/` aggressively. Only create `pkg/` if you are building a library that external teams will import and you want to be explicit about what constitutes your public API. For most microservices, skip `pkg/`.

### Real-World Layout Examples

| Project | Layout | Notes |
|---------|--------|-------|
| Kubernetes | `cmd/`, `pkg/`, `internal/` | Uses all three; `pkg/` is massive |
| Docker/Moby | `cmd/`, `internal/` | Moved away from `pkg/` |
| CockroachDB | `pkg/` heavily | Monorepo with extensive `pkg/` |
| HashiCorp Vault | `cmd/`, `internal/`, `sdk/` | Uses `sdk/` instead of `pkg/` |
| Standard Library | Flat packages | No `cmd/`, `internal/`, or `pkg/` |

---

## 2. Configuration Management

### The Configuration Hierarchy

In TypeScript you might use `dotenv`, `convict`, or `config` packages. Go's ecosystem has a similar layered approach, but conventions are stricter around 12-factor app principles.

**Priority order (highest to lowest):**
1. Command-line flags
2. Environment variables
3. Config file values
4. Default values

### Environment Variables with `os` (Preferred for Containers)

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

The standard `flag` package uses single-dash flags (`-port`). The `pflag` package provides POSIX-style double-dash flags (`--port`) that users expect:

```go
port := pflag.Int("port", 8080, "server port")
debug := pflag.Bool("debug", false, "enable debug mode")
pflag.Parse()
```

### Configuration with Viper

Viper is the heavy-duty config solution, analogous to `convict` in Node. It supports layered configuration (file + env + flags):

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

Go has no decorators like `class-validator`. Validate explicitly by collecting errors into a slice and joining with `errors.Join` (Go 1.20+):

```go
func (c *Config) Validate() error {
    var errs []error
    if c.Server.Port < 1 || c.Server.Port > 65535 {
        errs = append(errs, fmt.Errorf("invalid port: %d", c.Server.Port))
    }
    if c.Database.Host == "" {
        errs = append(errs, fmt.Errorf("database.host is required"))
    }
    return errors.Join(errs...) // Returns nil if errs is empty
}
```

### Quick Reference

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

---

## 3. Error Handling in Production

### Error Wrapping with `%w`

```go
func GetUser(ctx context.Context, id int64) (*User, error) {
    user, err := db.QueryUser(ctx, id)
    if err != nil {
        // Wrap with context — %w preserves the error chain
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
    return errors.Join(errs...) // Returns nil if errs is empty
}
```

### Operational vs Programmer Errors

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
        // Unexpected — wrap and propagate
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

## 4. Makefile Essentials

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

## 5. Version Injection with `ldflags`

Go has no `package.json` to read at runtime. Inject version information at build time:

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

GoReleaser automates cross-compilation, Docker images, and GitHub releases — the Go equivalent of `semantic-release`. Configure `.goreleaser.yaml` with:
- Build targets (`goos`, `goarch`)
- `ldflags` for version injection
- Docker image templates
- Changelog generation

```bash
goreleaser release   # produces binaries for every platform, Docker images, GitHub release
goreleaser build     # build only, no release
```

### Cross-Compilation

Go's cross-compilation requires no additional toolchain:

```bash
GOOS=linux   GOARCH=amd64 go build -o dist/myservice-linux-amd64   ./cmd/server
GOOS=linux   GOARCH=arm64 go build -o dist/myservice-linux-arm64   ./cmd/server
GOOS=darwin  GOARCH=amd64 go build -o dist/myservice-darwin-amd64  ./cmd/server
GOOS=darwin  GOARCH=arm64 go build -o dist/myservice-darwin-arm64  ./cmd/server
GOOS=windows GOARCH=amd64 go build -o dist/myservice-windows-amd64.exe ./cmd/server
```

TypeScript parallel: imagine if `npm run build` could target every OS and architecture with a single flag, with no pkg/nexe/vercel-ncc required.

---

## 6. Embedding Assets

Go 1.16's `embed` package bundles static files into the binary — one binary contains everything:

```go
import (
    "embed"
    "io/fs"
    "net/http"
)

//go:embed static/*
var staticFiles embed.FS

//go:embed templates/*
var templateFiles embed.FS

//go:embed migrations/*.sql
var migrationFiles embed.FS

func main() {
    // Serve embedded static files
    staticFS, _ := fs.Sub(staticFiles, "static")
    http.Handle("/static/", http.StripPrefix("/static/",
        http.FileServer(http.FS(staticFS))))

    // Use embedded templates
    tmpl, _ := template.ParseFS(templateFiles, "templates/*.html")

    // Use embedded migrations
    // goose.SetBaseFS(migrationFiles)
}
```

Your entire application — binary, templates, static assets, database migrations — is a single file. No more managing asset directories in Docker images.
