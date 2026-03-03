# 02 – Packages and Modules

This file assumes you have read `01-types-interfaces-and-structs.md`. It covers how Go organizes code at the package and module level, how imports work, and how the standard library is structured.

---

## 1. Packages and Visibility

### Capitalization vs export Keyword

TypeScript:

```typescript
export function DoSomething() {}  // exported
function doSomething() {}         // not exported
```

Go:

```go
func DoSomething() {}  // Exported — capital first letter
func doSomething() {}  // unexported — lowercase first letter
```

This applies to everything: functions, types, struct fields, methods, constants, variables. If it starts with a capital letter, it is visible outside the package.

### Package Organization

Go packages are directories. One directory = one package (excluding test files with `_test` suffix).

```
myproject/
  go.mod
  main.go
  internal/
    auth/
      auth.go
      middleware.go
    database/
      postgres.go
  pkg/
    validator/
      validator.go
  api/
    handler.go
    routes.go
```

Key rules:
- Package names are lowercase, single-word, no underscores (by convention).
- The package name should describe what it **provides**, not what it **contains**.
- Avoid package names like `util`, `common`, `helpers` — these are junk drawers.
- `internal/` is special: code in `internal/` can only be imported by code in the parent tree.

### Package Naming Conventions

| Rule | Good | Bad |
|------|------|-----|
| Lowercase, single word | `http`, `json`, `auth` | `HTTP`, `Json`, `Auth` |
| No underscores | `strconv` | `str_conv` |
| No plural | `user` | `users` |
| Describes what it provides | `compress` | `util` |
| Short | `io` | `inputoutput` |

### Internal Packages

The `internal` directory enforces access boundaries at the compiler level:

```
myproject/
  internal/
    auth/       # Only importable by code in myproject/
  cmd/
    server/
      main.go   # Can import myproject/internal/auth
```

No other module can import your internal packages. This is the Go equivalent of package-private in Java, enforced by the compiler.

### TS vs Go Visibility Comparison

| Concept | TypeScript | Go |
|---------|-----------|-----|
| Export | `export` keyword | Capital first letter |
| Private | No `export` / `private` | Lowercase first letter |
| Module boundary | `package.json` | `go.mod` |
| Internal | Convention only | `internal/` directory (compiler-enforced) |

---

## 2. Go Modules (go.mod)

### go.mod vs package.json

| Concept | npm / package.json | Go Modules / go.mod |
|---------|-------------------|---------------------|
| Manifest | `package.json` | `go.mod` |
| Lock file | `package-lock.json` | `go.sum` |
| Install | `npm install` | `go mod download` (usually automatic) |
| Add dep | `npm install pkg` | `go get pkg` |
| Remove unused | `npm prune` | `go mod tidy` |
| Registry | npmjs.com | No central registry — VCS URLs |
| Versioning | semver | semver (but v2+ requires path suffix) |

### go.mod Anatomy

```go
module github.com/yourname/yourproject

go 1.22

require (
    github.com/gorilla/mux v1.8.1
    golang.org/x/sync v0.6.0
)

require (
    // indirect dependencies (managed automatically)
    github.com/some/transitive v0.1.0 // indirect
)
```

### Key Commands

```bash
go mod init MODULE_PATH     # Initialize a new module
go mod tidy                  # Sync go.mod/go.sum with source
go get PKG@VERSION           # Add or update a dependency
go get PKG@latest            # Update to latest version
go mod download              # Download dependencies to cache
go mod vendor                # Copy dependencies into vendor/
go mod verify                # Verify dependency integrity
go mod why PKG               # Explain why a package is needed
go mod graph                 # Print full dependency graph
go mod edit -replace=OLD=NEW # Add a replace directive
go list -m all               # List all dependencies
go list -m -u all            # List available updates
```

### Replace Directives

For local development or forking:

```go
// Use a local copy of a module
replace github.com/original/pkg => ../my-local-copy

// Use a fork
replace github.com/original/pkg => github.com/myfork/pkg v1.0.0
```

This is similar to `npm link` but declarative and checked into version control.

### No node_modules

Go dependencies are stored in `$GOPATH/pkg/mod` (a global, content-addressed cache). There is no `node_modules` directory. There is no `node_modules` bloat. Dependencies are downloaded once and shared across all projects.

---

## 3. Import System

### Basic Imports

```go
import (
    "fmt"
    "net/http"
    "os"

    "github.com/gorilla/mux"
)
```

Imports use the full module path. The package name (the last element) is what you use in code:

```go
// "net/http" — package name is "http"
http.ListenAndServe(":8080", nil)

// "github.com/gorilla/mux" — package name is "mux"
r := mux.NewRouter()
```

### Import Aliases

```go
import (
    "crypto/rand"
    mrand "math/rand" // alias to avoid collision
)
```

### Blank Imports

The blank identifier `_` imports a package for its side effects only (init functions):

```go
import _ "github.com/lib/pq" // registers the postgres driver
```

This is the idiomatic way to register database drivers, image decoders, and other self-registering packages.

### Dot Imports

```go
import . "fmt" // puts all exported names into the current scope
Println("hello") // no fmt. prefix needed
```

Dot imports are almost always a bad idea. They make it unclear where names come from. Avoid them in application code.

---

## 4. init() Functions

### What They Are

`init()` functions run automatically when a package is imported, before `main()`:

```go
package database

var defaultPool *Pool

func init() {
    var err error
    defaultPool, err = NewPool(os.Getenv("DATABASE_URL"))
    if err != nil {
        log.Fatal("failed to initialize database pool:", err)
    }
}
```

### Execution Order

1. All imported packages' `init()` functions run first (recursively, depth-first).
2. Package-level variable declarations are evaluated.
3. `init()` functions in the current package run in the order they appear.
4. A single file can have multiple `init()` functions.
5. `main()` runs last.

### When to Use init()

Legitimate uses:
- Registering database drivers: `import _ "github.com/lib/pq"`
- Registering codecs or formats
- Validating package-level configuration

### When to Avoid init()

Avoid `init()` when:
- It performs I/O (network calls, file reads) — makes testing difficult.
- It has side effects that are hard to reason about.
- It can fail — `init()` cannot return errors, so failures become `log.Fatal` or panics.
- It sets up global state that should be injected.

**The better pattern:**

```go
// Instead of init()
type Server struct {
    db *sql.DB
}

func NewServer(db *sql.DB) *Server {
    return &Server{db: db}
}

// Explicit initialization in main()
func main() {
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    if err != nil {
        log.Fatal(err)
    }
    srv := NewServer(db)
    // ...
}
```

Explicit beats implicit. Dependency injection beats global state.

---

## 5. Common Build Flags

```bash
go build ./...               # Build all packages
go build -gcflags='-m' ./... # Show escape analysis + inlining decisions
go build -race ./...         # Build with race detector
go build -ldflags='-s -w'    # Strip debug info (smaller binary)
go vet ./...                 # Static analysis
go fmt ./...                 # Format all code
```

---

## 6. Standard Library Overview

The Go standard library is production-ready. You do not need Express, you do not need a logging framework on day one, you do not need a testing library. Here is a map of the key packages:

### Networking

| Package | Use |
|---------|-----|
| `net/http` | HTTP client and server (production-ready) |
| `net` | Low-level TCP/UDP/Unix sockets |
| `net/url` | URL parsing and building |
| `net/smtp` | Sending email |

### Encoding/Decoding

| Package | Use |
|---------|-----|
| `encoding/json` | JSON marshal/unmarshal |
| `encoding/xml` | XML |
| `encoding/csv` | CSV |
| `encoding/base64` | Base64 |
| `encoding/gob` | Go binary format |

### I/O and Files

| Package | Use |
|---------|-----|
| `io` | Core interfaces (Reader, Writer, Closer) |
| `io/fs` | Filesystem abstraction |
| `bufio` | Buffered I/O |
| `os` | File operations, env vars, process management |
| `path/filepath` | OS-aware path manipulation |

### Data Structures and Algorithms

| Package | Use |
|---------|-----|
| `sort` | Sorting slices and user-defined collections |
| `strings` | String manipulation |
| `strconv` | String/number conversions |
| `regexp` | Regular expressions |
| `unicode` | Unicode classification |

### Concurrency

| Package | Use |
|---------|-----|
| `sync` | Mutex, RWMutex, WaitGroup, Once, Map |
| `sync/atomic` | Atomic operations on primitives |
| `context` | Cancellation and deadlines |

### Time

| Package | Use |
|---------|-----|
| `time` | Time, Duration, Timer, Ticker |

### Crypto

| Package | Use |
|---------|-----|
| `crypto/rand` | Cryptographically secure random |
| `crypto/sha256` | SHA-256 hashing |
| `crypto/tls` | TLS configuration |

### Testing

| Package | Use |
|---------|-----|
| `testing` | Unit tests, benchmarks, examples |
| `net/http/httptest` | HTTP handler testing |
| `testing/fstest` | Filesystem testing |

### Logging

| Package | Use |
|---------|-----|
| `log` | Basic structured logging |
| `log/slog` | Structured logging (Go 1.21+) |

### Reflection and Code Generation

| Package | Use |
|---------|-----|
| `reflect` | Runtime type introspection |
| `go/ast` | Go AST manipulation |
| `text/template` | Text templates |
| `html/template` | HTML templates (XSS-safe) |

---

## 7. Project Layout Best Practices

The unofficial standard Go project layout (used by most production projects):

```
myproject/
  cmd/
    server/
      main.go        # Entry point for the server binary
    worker/
      main.go        # Entry point for the worker binary
  internal/
    auth/            # Auth logic — not importable outside this module
    database/        # DB layer
    handler/         # HTTP handlers
    service/         # Business logic
  pkg/
    validator/       # Potentially reusable across modules
  api/
    openapi.yaml     # API spec
  config/
    config.go        # Configuration structs
  migrations/
    001_init.sql
  Makefile
  go.mod
  go.sum
```

Key principles:
- `cmd/` contains entry points. Each subdirectory is a separate binary.
- `internal/` is for code that is part of this project only.
- `pkg/` is for code that could reasonably be imported by other projects.
- Avoid `utils/`, `helpers/`, `common/` — they are magnets for poorly organized code.
- Keep `main.go` thin. Wire dependencies there, but put logic in packages.
