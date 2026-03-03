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
1. [Types, Interfaces, and Structs](01-go-mental-model/01-types-interfaces-and-structs.md) — structs vs interfaces vs classes, zero values, error handling, pointers
2. [Packages and Modules](01-go-mental-model/02-packages-and-modules.md) — visibility, Go modules, dependency management
3. [Advanced Go Internals](01-go-mental-model/03-advanced-go-internals.md) — memory model, escape analysis, GC, runtime internals

### 02 — Concurrency Primitives
1. [Goroutines and Channels](02-concurrency/01-goroutines-and-channels.md) — goroutines vs async/await, buffered/unbuffered channels, `select`
2. [Synchronization and Context](02-concurrency/02-synchronization-and-context.md) — `sync` package, `context.Context`, cancellation and timeouts
3. [Advanced Concurrency Patterns](02-concurrency/03-advanced-concurrency-patterns.md) — fan-out/fan-in, worker pools, pipelines, singleflight

### 03 — The Standard Library
1. [HTTP and JSON](03-stdlib/01-http-and-json.md) — `net/http` servers, `encoding/json`, marshal/unmarshal, streaming
2. [Testing and IO](03-stdlib/02-testing-and-io.md) — `testing` package, `io` Reader/Writer composition, `database/sql`
3. [Time, Logging, and Additional Stdlib](03-stdlib/03-time-logging-and-additional-stdlib.md) — `time`, `log/slog`, `os`, `strings`, `sync`, `regexp`

### 04 — Building HTTP Services
1. [Handlers, Routing, and Middleware](04-http-services/01-handlers-routing-and-middleware.md) — `net/http` patterns, Go 1.22+ ServeMux, middleware chains
2. [Request Handling and Validation](04-http-services/02-request-handling-and-validation.md) — decoding, validation, structured error responses
3. [Advanced HTTP Patterns](04-http-services/03-advanced-http-patterns.md) — auth middleware, rate limiting, graceful shutdown, Chi/Gin/Echo comparison

### 05 — Data & Storage
1. [Database Drivers and ORMs](05-data-storage/01-database-drivers-and-orms.md) — pgx/pgxpool, sqlc, GORM, sqlx, Ent — trade-offs and setup
2. [Queries, Transactions, and Patterns](05-data-storage/02-queries-transactions-and-patterns.md) — pagination, bulk ops, transactions, repository pattern, mocking
3. [Migrations, Redis, and Advanced Storage](05-data-storage/03-migrations-redis-and-advanced-storage.md) — goose/golang-migrate, go-redis, caching patterns, testcontainers

### 06 — Testing in Go
1. [Table-Driven Tests and Mocking](06-testing/01-table-driven-tests-and-mocking.md) — test structure, parallel subtests, testify, fakes, mocks, golden files
2. [Integration and HTTP Testing](06-testing/02-integration-and-http-testing.md) — `httptest`, testcontainers, acceptance tests, CLI testing
3. [Benchmarking, Profiling, and Advanced Testing](06-testing/03-benchmarking-profiling-and-advanced-testing.md) — benchmarks, pprof, fuzzing, property-based testing, mutation testing

### 07 — Production Go
1. [Project Structure and Configuration](07-production/01-project-structure-and-configuration.md) — `cmd/`/`internal/`/`pkg/` layout, env vars, Viper, error wrapping, GoReleaser
2. [Observability and Health](07-production/02-observability-and-health.md) — slog, Prometheus, OpenTelemetry, health probes, graceful shutdown
3. [Deployment and Scaling](07-production/03-deployment-and-scaling.md) — Docker multi-stage builds, Kubernetes manifests, GOMAXPROCS, GOMEMLIMIT

### 08 — Advanced Patterns
1. [Generics and Code Generation](08-advanced-patterns/01-generics-and-code-generation.md) — type parameters, constraints, generic data structures, `go generate`, stringer, AST
2. [Patterns and Composition](08-advanced-patterns/02-patterns-and-composition.md) — embedding, functional options, builder, DI, Cobra CLIs, Go-idiomatic design patterns
3. [Reflection and Advanced Abstractions](08-advanced-patterns/03-reflection-and-advanced-abstractions.md) — `reflect` package, struct tags, plugin systems, interview Q&A

### 09 — Interview Prep
1. [Interview Essentials](09-interview-prep/01-interview-essentials.md) — top 20 Q&A, concurrency puzzles, code review red flags, live coding templates
2. [System Design and Advanced Topics](09-interview-prep/02-system-design-and-advanced-topics.md) — system design framework, design exercises, code review challenges, advanced gotchas

---

## Prerequisites
- Strong programming fundamentals in any language
- Understanding of concurrency concepts (event loop, async I/O)
- Read [Module 00: Go for TypeScript Engineers](00-go-prereqs.md) before starting

## Status
**Complete** — all modules written and structured.
