# Module 03 Cheat Sheet: The Standard Library

## net/http Handler Template

```go
package main

import (
    "encoding/json"
    "log/slog"
    "net/http"
    "time"
)

func main() {
    mux := http.NewServeMux()

    // Routes (Go 1.22+)
    mux.HandleFunc("GET /health", handleHealth)
    mux.HandleFunc("GET /users/{id}", handleGetUser)
    mux.HandleFunc("POST /users", handleCreateUser)

    // Middleware stack
    handler := withLogging(withRecovery(mux))

    srv := &http.Server{
        Addr:         ":8080",
        Handler:      handler,
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    slog.Info("server starting", "addr", srv.Addr)
    if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        slog.Error("server failed", "error", err)
    }
}

// Middleware template
func withLogging(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        slog.Info("request",
            "method", r.Method,
            "path", r.URL.Path,
            "duration", time.Since(start),
        )
    })
}

func withRecovery(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                slog.Error("panic recovered", "error", err)
                http.Error(w, "internal server error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}

// JSON response helper
func writeJSON(w http.ResponseWriter, status int, v any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(v)
}

// JSON request helper
func readJSON(r *http.Request, v any) error {
    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields()
    return dec.Decode(v)
}
```

## JSON Struct Tags Reference

| Tag | Effect | Example |
|-----|--------|---------|
| `json:"name"` | Set JSON key | `json:"user_name"` |
| `json:"name,omitempty"` | Omit if zero value | `json:"email,omitempty"` |
| `json:"-"` | Always ignore | `json:"-"` |
| `json:",omitempty"` | Keep Go name, omit if zero | `json:",omitempty"` |
| `json:",string"` | Encode number/bool as string | `json:"count,string"` |

### omitempty Zero Values

| Type | Omitted When |
|------|-------------|
| `bool` | `false` |
| `int`, `float64` | `0` |
| `string` | `""` |
| `pointer` | `nil` |
| `slice`, `map` | `nil` (NOT empty) |
| `struct` | Never (use pointer) |
| `time.Time` | Never (use `*time.Time`) |

## io Interface Composition Patterns

```
io.Reader           Read(p []byte) (n int, err error)
io.Writer           Write(p []byte) (n int, err error)
io.Closer           Close() error
io.ReadCloser       Reader + Closer
io.WriteCloser      Writer + Closer
io.ReadWriter       Reader + Writer
io.ReadWriteCloser  Reader + Writer + Closer
io.Seeker           Seek(offset int64, whence int) (int64, error)
io.ReadSeeker       Reader + Seeker
```

### Common io Functions

```go
io.Copy(dst, src)                  // copy all bytes from Reader to Writer
io.CopyN(dst, src, n)             // copy exactly n bytes
io.ReadAll(r)                      // read all bytes into []byte
io.MultiReader(r1, r2, r3)        // concatenate readers
io.TeeReader(r, w)                // read from r, copy to w
io.LimitReader(r, n)              // read at most n bytes
io.Pipe()                          // synchronous in-memory pipe
io.NopCloser(r)                   // wrap Reader as ReadCloser (no-op Close)
io.Discard                         // Writer that discards all data
```

## Testing Patterns Reference

### Table-Driven Test Template

```go
func TestFunction(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    int
        wantErr bool
    }{
        {"valid input", "hello", 5, false},
        {"empty input", "", 0, false},
        {"invalid input", "\x00", 0, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Function(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("error = %v, wantErr %v", err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("got %d, want %d", got, tt.want)
            }
        })
    }
}
```

### HTTP Handler Test Template

```go
func TestGetUser(t *testing.T) {
    req := httptest.NewRequest("GET", "/users/123", nil)
    req.SetPathValue("id", "123") // Go 1.22+

    rec := httptest.NewRecorder()
    handleGetUser(rec, req)

    if rec.Code != http.StatusOK {
        t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
    }

    var user User
    json.NewDecoder(rec.Body).Decode(&user)
    if user.ID != "123" {
        t.Errorf("user.ID = %q, want %q", user.ID, "123")
    }
}
```

### Benchmark Template

```go
func BenchmarkFunction(b *testing.B) {
    input := setupInput()
    b.ResetTimer() // exclude setup from timing

    for i := 0; i < b.N; i++ {
        Function(input)
    }
}

// Run: go test -bench=BenchmarkFunction -benchmem ./...
```

### Test Commands

```bash
go test ./...                         # run all tests
go test -v ./...                      # verbose output
go test -run TestName ./...           # run specific test
go test -run TestName/subtest ./...   # run specific subtest
go test -count=1 ./...                # disable test caching
go test -race ./...                   # enable race detector
go test -cover ./...                  # show coverage percentage
go test -coverprofile=cover.out ./... # write coverage file
go tool cover -html=cover.out         # view coverage in browser
go test -bench=. ./...                # run benchmarks
go test -bench=. -benchmem ./...      # benchmarks with alloc info
go test -fuzz=FuzzName -fuzztime=30s  # run fuzzer for 30s
go test -shuffle=on ./...             # randomize test order
```

## database/sql Template

```go
import (
    "database/sql"
    _ "github.com/lib/pq"
)

// Open and configure
db, err := sql.Open("postgres", connStr)
if err != nil { log.Fatal(err) }
defer db.Close()

db.SetMaxOpenConns(25)
db.SetMaxIdleConns(10)
db.SetConnMaxLifetime(5 * time.Minute)

// Single row
var name string
err := db.QueryRowContext(ctx, "SELECT name FROM users WHERE id = $1", id).Scan(&name)
if errors.Is(err, sql.ErrNoRows) { /* not found */ }

// Multiple rows
rows, err := db.QueryContext(ctx, "SELECT id, name FROM users WHERE active = $1", true)
if err != nil { return err }
defer rows.Close()
for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Name); err != nil { return err }
    users = append(users, u)
}
if err := rows.Err(); err != nil { return err }

// Exec (INSERT/UPDATE/DELETE)
result, err := db.ExecContext(ctx, "DELETE FROM users WHERE id = $1", id)
affected, _ := result.RowsAffected()

// Transaction
tx, err := db.BeginTx(ctx, nil)
if err != nil { return err }
defer tx.Rollback()
tx.ExecContext(ctx, "UPDATE ...", ...)
tx.ExecContext(ctx, "INSERT ...", ...)
return tx.Commit()
```

## slog Setup Template

```go
// Development (text)
logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{
    Level:     slog.LevelDebug,
    AddSource: true,
}))

// Production (JSON)
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level: slog.LevelInfo,
}))

// Set as default
slog.SetDefault(logger)

// Usage
slog.Info("server started", "addr", ":8080")
slog.Error("query failed", "error", err, "query", q)
slog.Debug("cache hit", "key", key, "ttl", ttl)

// With context fields
logger := slog.With("service", "api", "version", "1.0")
logger.Info("request", "method", "GET", "path", "/users")

// Groups
slog.Info("request",
    slog.Group("http", "method", "GET", "status", 200),
    slog.Group("timing", "total", 45*time.Millisecond),
)
```

## time Format Reference (The Reference Time)

```
Mon Jan 2 15:04:05 MST 2006
 |   |  | |  |  |  |   |
 |   |  | |  |  |  |   +-- Year:   2006
 |   |  | |  |  |  +------ Zone:   MST
 |   |  | |  |  +--------- Second: 05
 |   |  | |  +------------ Minute: 04
 |   |  | +--------------- Hour:   15 (3 PM, use 3 for 12-hour)
 |   |  +----------------- Day:    2 (02 for zero-padded)
 |   +-------------------- Month:  Jan (01 for numeric)
 +------------------------ Weekday: Mon
```

### Common Formats

| Format | Pattern | Example |
|--------|---------|---------|
| ISO 8601 | `2006-01-02` | `2024-01-15` |
| RFC 3339 | `time.RFC3339` | `2024-01-15T14:30:00Z` |
| US date | `01/02/2006` | `01/15/2024` |
| Time only | `15:04:05` | `14:30:00` |
| 12-hour | `3:04 PM` | `2:30 PM` |
| Full | `Monday, January 2, 2006` | `Monday, January 15, 2024` |
| Compact | `20060102150405` | `20240115143000` |
| Log style | `2006/01/02 15:04:05` | `2024/01/15 14:30:00` |

## Common stdlib Packages Table

| Package | Purpose | TS Equivalent |
|---------|---------|---------------|
| `net/http` | HTTP client and server | Express / fetch |
| `encoding/json` | JSON marshal/unmarshal | `JSON.parse` / `JSON.stringify` |
| `io` | Reader/Writer interfaces | Node streams |
| `os` | OS interaction, files | `fs`, `process` |
| `fmt` | Formatting and printing | `console.log`, template literals |
| `strings` | String manipulation | `String.prototype` methods |
| `strconv` | String conversions | `parseInt`, `parseFloat`, `toString` |
| `time` | Time and duration | `Date`, `setTimeout` |
| `context` | Cancellation and deadlines | `AbortController` |
| `sync` | Mutexes, WaitGroup | N/A (single-threaded) |
| `testing` | Test framework | Jest / Vitest |
| `log/slog` | Structured logging | winston / pino |
| `database/sql` | Database access | pg / mysql2 |
| `crypto/*` | Cryptography | `crypto` module |
| `regexp` | Regular expressions (RE2) | `RegExp` (but no backtracking) |
| `embed` | Embed files in binary | Webpack asset modules |
| `html/template` | HTML templating | Handlebars / EJS |
| `net/url` | URL parsing | `URL` API |
| `path/filepath` | File path manipulation | `path` module |
| `sort` / `slices` | Sorting and searching | `Array.sort` |
| `maps` | Map utilities | `Object.keys`, `Object.values` |
| `errors` | Error wrapping/unwrapping | N/A |
| `bytes` | Byte slice utilities | `Buffer` |
| `bufio` | Buffered I/O | N/A |
