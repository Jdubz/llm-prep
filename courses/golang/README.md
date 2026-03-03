# Golang

Go for senior TypeScript engineers. Covers Go's type system, concurrency model, stdlib, and production patterns — focused on what's genuinely different from the TypeScript/Node.js mental model rather than rehashing programming basics.

> **Perspective**: Go is deliberately simple. The challenge isn't learning syntax — it's unlearning patterns from TypeScript (generics-heavy abstractions, decorator patterns, DI frameworks) and embracing Go's explicit, composition-over-inheritance philosophy.

---

## Modules

### 00 — [Go for TypeScript Engineers](00-go-prereqs.md)
- Go toolchain, modules, and project structure mapped to npm equivalents
- Syntax translation: variables, types, strings, collections, control flow
- Functions, closures, variadic args, defer
- Structs, methods, composition (no inheritance)
- Interfaces (implicit satisfaction), the empty interface (`any`)
- Error handling with multiple returns (no try/catch)
- Pointers: when and why
- Packages and visibility (uppercase = exported)

### 01 — Go Mental Model (for TS Engineers)
- Types: structs vs interfaces vs classes, zero values vs undefined
- Error handling: multiple returns vs try/catch, `errors.Is`/`errors.As`
- Packages and visibility (capitalization vs export keyword)
- Pointers: when and why (value semantics vs reference semantics)
- No generics abuse — when `interface{}` / `any` is fine
- Go modules and dependency management (vs npm)

### 02 — Concurrency Primitives
- Goroutines vs async/await: mental model shift
- Channels: buffered, unbuffered, directional
- `select` statement for multiplexing
- `sync` package: WaitGroup, Mutex, Once, Map
- `context.Context`: cancellation, timeouts, values
- Common concurrency patterns: fan-out/fan-in, worker pools, pipelines

### 03 — The Standard Library
- `net/http`: building servers without frameworks
- `encoding/json`: marshal/unmarshal, custom encoders, streaming
- `io`: Reader/Writer interfaces, composition
- `testing`: table-driven tests, benchmarks, fuzzing
- `database/sql`: connection pools, prepared statements
- `log/slog`: structured logging (Go 1.21+)

### 04 — Building HTTP Services
- `net/http` patterns: handlers, middleware chains, routing (Go 1.22+ ServeMux)
- Request validation and error responses
- Middleware: logging, auth, CORS, rate limiting
- Graceful shutdown
- Comparison: when to reach for Chi/Gin/Echo vs stdlib

### 05 — Data & Storage
- `database/sql` with PostgreSQL (`pgx` driver)
- ORMs and query builders: sqlc, GORM, sqlx — trade-offs
- Migrations with `goose` or `golang-migrate`
- Redis integration
- Repository pattern in Go

### 06 — Testing in Go
- Table-driven tests and subtests
- Mocking: interfaces as contracts (no mock libraries needed)
- `httptest` for HTTP handler testing
- Integration tests with `testcontainers-go`
- Benchmarking and profiling (`pprof`)
- Fuzzing (Go 1.18+)

### 07 — Production Go
- Project layout conventions (`cmd/`, `internal/`, `pkg/`)
- Configuration management (env vars, flags, config files)
- Graceful shutdown and signal handling
- Docker builds: multi-stage, scratch/distroless images
- Observability: OpenTelemetry, Prometheus metrics
- Error wrapping and stack traces

### 08 — Advanced Patterns
- Generics (Go 1.18+): constraints, type sets, when to use
- Code generation: `go generate`, `stringer`, protocol buffers
- Reflection: `reflect` package (and why to avoid it)
- Embedding and composition patterns
- Functional options pattern
- Building CLIs with `cobra`

### 09 — Interview Prep
- Common Go interview questions and gotchas
- Concurrency puzzles (deadlocks, race conditions)
- System design in Go: choosing Go-appropriate architectures
- Live coding: build a concurrent worker pool
- Code review exercises: idiomatic vs non-idiomatic Go

---

## Prerequisites
- Strong programming fundamentals in any language
- Understanding of concurrency concepts (event loop, async I/O)
- Read [Module 00: Go for TypeScript Engineers](00-go-prereqs.md) before starting

## Status
**Scaffolded** — module outlines complete, content to be written.
