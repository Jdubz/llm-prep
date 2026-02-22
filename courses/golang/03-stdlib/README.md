# Module 03: The Standard Library

## Philosophy

Go's standard library is not a collection of utilities you tolerate until you find a "real" framework. It is the framework. Production systems at Google, Cloudflare, and Uber run on `net/http` without a wrapper. The standard library is stable, well-tested, and fast.

Coming from TypeScript, where you install Express before writing your first route and pull in a dozen packages for basics, this is a culture shock. Embrace it.

---

## 1. net/http: Building Servers Without Frameworks

### The Handler Interface

Everything in `net/http` revolves around one interface:

```go
type Handler interface {
    ServeHTTP(ResponseWriter, *Request)
}
```

That is it. One method. Every HTTP handler in Go satisfies this interface. Compare to Express, where you have `(req, res, next)` and a framework-specific `app.get()`.

### HandlerFunc: The Adapter

You do not usually implement the interface directly. You use `http.HandlerFunc`:

```go
// http.HandlerFunc is a type that adapts a function to the Handler interface
type HandlerFunc func(ResponseWriter, *Request)

func (f HandlerFunc) ServeHTTP(w ResponseWriter, r *Request) {
    f(w, r)
}
```

This means any function with the right signature is a handler:

```go
func healthCheck(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ok"}`))
}

mux.HandleFunc("GET /health", healthCheck)
```

### ServeMux Routing (Go 1.22+)

Before Go 1.22, the default router was limited — no method-based routing, no path parameters. Go 1.22 changed that:

```go
mux := http.NewServeMux()

// Method-based routing (Go 1.22+)
mux.HandleFunc("GET /users", listUsers)
mux.HandleFunc("POST /users", createUser)
mux.HandleFunc("GET /users/{id}", getUser)
mux.HandleFunc("PUT /users/{id}", updateUser)
mux.HandleFunc("DELETE /users/{id}", deleteUser)

// Access path parameters
func getUser(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id") // Go 1.22+
    // ...
}
```

**TS comparison:**

```typescript
// Express
app.get("/users", listUsers);
app.post("/users", createUser);
app.get("/users/:id", getUser);
```

For many applications, Go 1.22+'s built-in router eliminates the need for third-party routers like gorilla/mux or chi.

### Middleware Chains

Middleware in Go is a function that wraps a handler:

```go
func logging(next http.Handler) http.Handler {
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

func auth(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        token := r.Header.Get("Authorization")
        if !isValid(token) {
            http.Error(w, "unauthorized", http.StatusUnauthorized)
            return // do NOT call next
        }
        next.ServeHTTP(w, r)
    })
}

// Compose: auth runs first, then logging, then the handler
handler := auth(logging(mux))

srv := &http.Server{
    Addr:    ":8080",
    Handler: handler,
}
```

**TS comparison:** This is like Express middleware (`app.use()`), but without a framework. The `next` pattern is identical — call `next` to continue, or do not call it to short-circuit.

### Request Context

Every `*http.Request` carries a context that is cancelled when the client disconnects:

```go
func getUser(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context() // cancelled when client disconnects

    user, err := db.GetUser(ctx, r.PathValue("id"))
    if err != nil {
        if errors.Is(err, context.Canceled) {
            return // client disconnected, stop work
        }
        http.Error(w, "internal error", 500)
        return
    }

    json.NewEncoder(w).Encode(user)
}
```

### A Complete Server

```go
func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Type", "application/json")
        w.Write([]byte(`{"status":"ok"}`))
    })

    mux.HandleFunc("GET /users/{id}", getUser)
    mux.HandleFunc("POST /users", createUser)

    handler := logging(auth(mux))

    srv := &http.Server{
        Addr:         ":8080",
        Handler:      handler,
        ReadTimeout:  5 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    log.Printf("listening on %s", srv.Addr)
    if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        log.Fatal(err)
    }
}
```

---

## 2. encoding/json

### Marshal and Unmarshal

```go
type User struct {
    ID        int       `json:"id"`
    Name      string    `json:"name"`
    Email     string    `json:"email,omitempty"` // omitted if empty string
    CreatedAt time.Time `json:"created_at"`
    password  string    // unexported — ignored by json package
}

// Struct -> JSON
user := User{ID: 1, Name: "Alice", Email: "alice@example.com"}
data, err := json.Marshal(user)
// {"id":1,"name":"Alice","email":"alice@example.com","created_at":"0001-01-01T00:00:00Z"}

// JSON -> Struct
var u User
err := json.Unmarshal(data, &u)
```

### Struct Tags Reference

| Tag | Effect |
|-----|--------|
| `json:"name"` | Use "name" as JSON key |
| `json:"name,omitempty"` | Omit field if zero value |
| `json:"-"` | Always ignore this field |
| `json:"-,"` | Use literal "-" as key |
| `json:",string"` | Encode number/bool as JSON string |

### omitempty Behavior (Gotchas)

`omitempty` omits zero values. But zero values might be meaningful:

```go
type Config struct {
    Port    int  `json:"port,omitempty"`    // 0 is omitted — but 0 might be valid!
    Debug   bool `json:"debug,omitempty"`   // false is omitted — but false is meaningful!
    Retries int  `json:"retries,omitempty"` // 0 retries = omitted, not "zero retries"
}
```

If you need to distinguish "not set" from "zero", use a pointer:

```go
type Config struct {
    Port    *int  `json:"port,omitempty"`    // nil = omitted, *0 = present with value 0
    Debug   *bool `json:"debug,omitempty"`   // nil = omitted, *false = present with false
}
```

### Custom MarshalJSON / UnmarshalJSON

```go
type Status int

const (
    StatusActive   Status = 1
    StatusInactive Status = 2
)

func (s Status) MarshalJSON() ([]byte, error) {
    var str string
    switch s {
    case StatusActive:
        str = "active"
    case StatusInactive:
        str = "inactive"
    default:
        str = "unknown"
    }
    return json.Marshal(str)
}

func (s *Status) UnmarshalJSON(data []byte) error {
    var str string
    if err := json.Unmarshal(data, &str); err != nil {
        return err
    }
    switch str {
    case "active":
        *s = StatusActive
    case "inactive":
        *s = StatusInactive
    default:
        return fmt.Errorf("unknown status: %s", str)
    }
    return nil
}
```

### Streaming with json.Decoder

For large JSON payloads or HTTP request bodies, use a decoder instead of `Unmarshal`:

```go
func createUser(w http.ResponseWriter, r *http.Request) {
    var user User

    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields() // reject unknown JSON keys

    if err := dec.Decode(&user); err != nil {
        http.Error(w, "invalid JSON: "+err.Error(), http.StatusBadRequest)
        return
    }

    // Validate...
}
```

`json.Decoder` reads from an `io.Reader` and does not buffer the entire body into memory first.

### json.RawMessage

Delay JSON parsing or preserve raw JSON:

```go
type Event struct {
    Type    string          `json:"type"`
    Payload json.RawMessage `json:"payload"` // raw JSON, not parsed yet
}

func handleEvent(data []byte) error {
    var event Event
    if err := json.Unmarshal(data, &event); err != nil {
        return err
    }

    switch event.Type {
    case "user_created":
        var u User
        return json.Unmarshal(event.Payload, &u)
    case "order_placed":
        var o Order
        return json.Unmarshal(event.Payload, &o)
    }
    return fmt.Errorf("unknown event type: %s", event.Type)
}
```

---

## 3. io: The Composition Engine

### Reader and Writer

Two interfaces power Go's entire I/O model:

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}
```

Everything implements these: files, network connections, HTTP bodies, buffers, compressors, encryptors. This is Go's most powerful abstraction.

**TS comparison:** Node has streams, but they are complex (readable, writable, transform, duplex, back-pressure). Go's `io.Reader`/`io.Writer` are simpler and more composable.

### io.Copy: Efficient Streaming

```go
// Copy from reader to writer — no intermediate buffer management needed
// Uses a 32KB buffer internally
n, err := io.Copy(dst, src)

// Example: proxy an HTTP response
func proxy(w http.ResponseWriter, r *http.Request) {
    resp, err := http.Get("https://upstream.example.com" + r.URL.Path)
    if err != nil {
        http.Error(w, err.Error(), 500)
        return
    }
    defer resp.Body.Close()

    // Stream the response — does not buffer the entire body
    w.WriteHeader(resp.StatusCode)
    io.Copy(w, resp.Body)
}
```

### Composition with MultiReader, TeeReader, Pipe

```go
// MultiReader: concatenate readers
r := io.MultiReader(header, body, footer)
io.Copy(w, r) // writes header, then body, then footer

// TeeReader: read and copy simultaneously (like Unix tee)
var buf bytes.Buffer
tee := io.TeeReader(resp.Body, &buf) // everything read from tee is also written to buf
io.Copy(os.Stdout, tee)              // prints body AND captures in buf

// Pipe: synchronous in-memory pipe
pr, pw := io.Pipe()
go func() {
    json.NewEncoder(pw).Encode(data) // write JSON to pipe
    pw.Close()
}()
json.NewDecoder(pr).Decode(&result) // read JSON from pipe
```

### io.NopCloser

Wrap a Reader to satisfy `io.ReadCloser` (e.g., for `http.Response.Body`):

```go
body := io.NopCloser(strings.NewReader(`{"status":"ok"}`))
```

---

## 4. testing: Table-Driven Tests and Beyond

### Table-Driven Tests

The dominant testing pattern in Go:

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 2, 3, 5},
        {"negative", -1, -1, -2},
        {"zero", 0, 0, 0},
        {"mixed", -1, 5, 4},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.expected {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.expected)
            }
        })
    }
}
```

**TS comparison:**

```typescript
// Jest
describe("add", () => {
  test.each([
    [2, 3, 5],
    [-1, -1, -2],
  ])("add(%i, %i) = %i", (a, b, expected) => {
    expect(add(a, b)).toBe(expected);
  });
});
```

### Subtests with t.Run

`t.Run` creates subtests that can be run individually:

```bash
go test -run TestAdd/positive   # run only the "positive" subtest
go test -run TestAdd             # run all subtests of TestAdd
```

Subtests can run in parallel:

```go
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel() // run this subtest in parallel with others
        // ...
    })
}
```

### Benchmarks with testing.B

```go
func BenchmarkAdd(b *testing.B) {
    for i := 0; i < b.N; i++ {
        Add(2, 3)
    }
}

// Run:
// go test -bench=BenchmarkAdd -benchmem ./...
// Output:
// BenchmarkAdd-8   1000000000   0.2500 ns/op   0 B/op   0 allocs/op
```

`b.N` is adjusted automatically until the benchmark runs long enough for a stable measurement.

### Fuzzing with testing.F (Go 1.18+)

```go
func FuzzParseJSON(f *testing.F) {
    // Seed corpus
    f.Add([]byte(`{"name":"Alice"}`))
    f.Add([]byte(`{}`))
    f.Add([]byte(`[]`))

    f.Fuzz(func(t *testing.T, data []byte) {
        var result map[string]any
        err := json.Unmarshal(data, &result)
        if err != nil {
            return // invalid JSON — that is fine
        }

        // If it parses, it should round-trip
        out, err := json.Marshal(result)
        if err != nil {
            t.Fatalf("marshal failed after successful unmarshal: %v", err)
        }

        var result2 map[string]any
        if err := json.Unmarshal(out, &result2); err != nil {
            t.Fatalf("re-unmarshal failed: %v", err)
        }
    })
}
```

Run: `go test -fuzz=FuzzParseJSON -fuzztime=30s`

### Test Helpers with t.Helper()

```go
func assertEqual(t *testing.T, got, want any) {
    t.Helper() // marks this as a helper — error line numbers point to the caller
    if got != want {
        t.Errorf("got %v, want %v", got, want)
    }
}
```

Without `t.Helper()`, error messages point to the helper function, not the test that called it.

### testdata Directory

Files in a `testdata/` directory are ignored by the Go build system but accessible to tests:

```
mypackage/
  parser.go
  parser_test.go
  testdata/
    valid.json
    invalid.json
    large.json
```

```go
func TestParse(t *testing.T) {
    data, err := os.ReadFile("testdata/valid.json")
    if err != nil {
        t.Fatal(err)
    }
    // ...
}
```

### TestMain for Setup/Teardown

```go
func TestMain(m *testing.M) {
    // Setup
    db := setupTestDatabase()

    // Run all tests
    code := m.Run()

    // Teardown
    db.Close()

    os.Exit(code)
}
```

---

## 5. database/sql

### Connection Pool Management

`database/sql` manages a connection pool automatically:

```go
import (
    "database/sql"
    _ "github.com/lib/pq" // PostgreSQL driver (registers via init())
)

func main() {
    db, err := sql.Open("postgres", "postgres://user:pass@localhost/dbname?sslmode=disable")
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    // Configure the pool
    db.SetMaxOpenConns(25)                 // max concurrent connections
    db.SetMaxIdleConns(10)                 // max idle connections
    db.SetConnMaxLifetime(5 * time.Minute) // max connection age

    // Verify connectivity
    if err := db.PingContext(context.Background()); err != nil {
        log.Fatal(err)
    }
}
```

`sql.Open` does not connect — it configures the pool. `Ping` verifies the connection.

### Queries with Context

```go
func getUser(ctx context.Context, db *sql.DB, id int) (*User, error) {
    var u User
    err := db.QueryRowContext(ctx,
        "SELECT id, name, email FROM users WHERE id = $1", id,
    ).Scan(&u.ID, &u.Name, &u.Email)

    if errors.Is(err, sql.ErrNoRows) {
        return nil, ErrNotFound
    }
    if err != nil {
        return nil, fmt.Errorf("querying user %d: %w", id, err)
    }
    return &u, nil
}

func listUsers(ctx context.Context, db *sql.DB) ([]User, error) {
    rows, err := db.QueryContext(ctx, "SELECT id, name, email FROM users")
    if err != nil {
        return nil, fmt.Errorf("listing users: %w", err)
    }
    defer rows.Close() // CRITICAL: always close rows

    var users []User
    for rows.Next() {
        var u User
        if err := rows.Scan(&u.ID, &u.Name, &u.Email); err != nil {
            return nil, fmt.Errorf("scanning user: %w", err)
        }
        users = append(users, u)
    }
    return users, rows.Err() // check for iteration errors
}
```

### Transactions

```go
func transferFunds(ctx context.Context, db *sql.DB, from, to int, amount float64) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil {
        return err
    }
    defer tx.Rollback() // no-op if committed

    _, err = tx.ExecContext(ctx,
        "UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, from)
    if err != nil {
        return err
    }

    _, err = tx.ExecContext(ctx,
        "UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, to)
    if err != nil {
        return err
    }

    return tx.Commit()
}
```

The `defer tx.Rollback()` pattern is safe: `Rollback` on an already-committed transaction is a no-op.

### Prepared Statements

```go
stmt, err := db.PrepareContext(ctx, "SELECT id, name FROM users WHERE email = $1")
if err != nil {
    return err
}
defer stmt.Close()

// Reuse the prepared statement
row := stmt.QueryRowContext(ctx, "alice@example.com")
row := stmt.QueryRowContext(ctx, "bob@example.com")
```

Prepared statements are useful when executing the same query many times with different parameters.

---

## 6. log/slog: Structured Logging (Go 1.21+)

### Basic Usage

```go
import "log/slog"

// Default text handler
slog.Info("user created",
    "userID", 42,
    "name", "Alice",
)
// Output: 2024/01/15 10:30:00 INFO user created userID=42 name=Alice

// JSON handler
logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
slog.SetDefault(logger)

slog.Info("user created", "userID", 42, "name", "Alice")
// Output: {"time":"2024-01-15T10:30:00Z","level":"INFO","msg":"user created","userID":42,"name":"Alice"}
```

### Handler Options

```go
logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
    Level:     slog.LevelDebug,           // minimum level
    AddSource: true,                       // include file:line
}))
```

### Log Groups

```go
slog.Info("request",
    slog.Group("http",
        slog.String("method", "GET"),
        slog.String("path", "/users"),
        slog.Int("status", 200),
    ),
    slog.Group("timing",
        slog.Duration("total", 45*time.Millisecond),
    ),
)
// JSON: {"msg":"request","http":{"method":"GET","path":"/users","status":200},"timing":{"total":"45ms"}}
```

### Logger with Context

```go
func handleRequest(w http.ResponseWriter, r *http.Request) {
    logger := slog.With(
        "requestID", r.Header.Get("X-Request-ID"),
        "method", r.Method,
        "path", r.URL.Path,
    )

    logger.Info("request started")
    // ... process request ...
    logger.Info("request completed", "status", 200)
}
```

### Custom Handler

```go
type contextHandler struct {
    inner slog.Handler
}

func (h *contextHandler) Handle(ctx context.Context, r slog.Record) error {
    if requestID, ok := ctx.Value(requestIDKey).(string); ok {
        r.AddAttrs(slog.String("requestID", requestID))
    }
    return h.inner.Handle(ctx, r)
}

func (h *contextHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
    return &contextHandler{inner: h.inner.WithAttrs(attrs)}
}

func (h *contextHandler) WithGroup(name string) slog.Handler {
    return &contextHandler{inner: h.inner.WithGroup(name)}
}

func (h *contextHandler) Enabled(ctx context.Context, level slog.Level) bool {
    return h.inner.Enabled(ctx, level)
}
```

---

## 7. fmt: Formatting and the Stringer Interface

### The Stringer Interface

```go
type Stringer interface {
    String() string
}
```

If your type implements `String()`, `fmt.Println` and friends will use it:

```go
type Point struct{ X, Y int }

func (p Point) String() string {
    return fmt.Sprintf("(%d, %d)", p.X, p.Y)
}

fmt.Println(Point{1, 2}) // "(1, 2)"
```

### Format Verbs

| Verb | Description | Example |
|------|-------------|---------|
| `%v` | Default format | `{Alice 30}` |
| `%+v` | With field names | `{Name:Alice Age:30}` |
| `%#v` | Go syntax | `main.User{Name:"Alice", Age:30}` |
| `%T` | Type | `main.User` |
| `%d` | Integer | `42` |
| `%s` | String | `hello` |
| `%q` | Quoted string | `"hello"` |
| `%x` | Hex | `2a` |
| `%p` | Pointer | `0xc0000b4000` |
| `%w` | Wrap error (Errorf only) | wrapped error chain |

### errors.New vs fmt.Errorf

```go
// Simple static error — no formatting needed
var ErrNotFound = errors.New("not found")

// Error with context — wraps another error
return fmt.Errorf("fetching user %d: %w", id, err)

// Error with context — no wrapping (breaks error chain intentionally)
return fmt.Errorf("fetching user %d: %v", id, err)
```

---

## 8. time: The Reference Time

### The Magic Reference Time

Go formats time using a reference time, not format specifiers:

```
Mon Jan 2 15:04:05 MST 2006
```

This is January 2, 2006, 3:04:05 PM — the numbers 1, 2, 3, 4, 5, 6, 7 in sequence. Every Go developer memorizes this.

```go
t := time.Now()

t.Format("2006-01-02")                    // "2024-01-15"
t.Format("2006-01-02 15:04:05")           // "2024-01-15 14:30:00"
t.Format(time.RFC3339)                     // "2024-01-15T14:30:00Z"
t.Format("Mon, 02 Jan 2006 15:04:05 MST") // "Mon, 15 Jan 2024 14:30:00 UTC"

// Parsing
parsed, err := time.Parse("2006-01-02", "2024-01-15")
parsed, err := time.Parse(time.RFC3339, "2024-01-15T14:30:00Z")
```

**TS comparison:**

```typescript
// moment/dayjs — specifier-based
dayjs().format("YYYY-MM-DD HH:mm:ss");

// Go — reference-based
t.Format("2006-01-02 15:04:05")
```

### Timezones

```go
loc, err := time.LoadLocation("America/New_York")
if err != nil {
    log.Fatal(err)
}

t := time.Now().In(loc)
fmt.Println(t.Format("2006-01-02 15:04:05 MST"))
```

### time.After and time.Tick

```go
// One-shot timer (useful in select)
select {
case result := <-ch:
    process(result)
case <-time.After(5 * time.Second):
    log.Println("timed out")
}

// Repeating ticker
ticker := time.NewTicker(1 * time.Second)
defer ticker.Stop() // ALWAYS stop tickers to prevent leaks

for range ticker.C {
    fmt.Println("tick")
}
```

**Warning:** `time.After` creates a timer that is not garbage collected until it fires. In a loop, use `time.NewTimer` and reset it.

### Monotonic Clock

`time.Now()` returns a time with both wall clock and monotonic clock readings. Duration calculations use the monotonic reading, making them immune to wall clock adjustments (NTP, daylight saving, etc.):

```go
start := time.Now()
doWork()
elapsed := time.Since(start) // uses monotonic clock — always accurate
```

---

## Interview Questions

### Conceptual

1. **Why would you use Go's standard `net/http` package instead of a framework like Gin or Echo?** Discuss: Go 1.22+ routing, the Handler interface, middleware composition, reduced dependencies, production readiness.

2. **Explain the `io.Reader` and `io.Writer` interfaces and why they matter.** Cover: composability, streaming, how `io.Copy` works, how everything from files to HTTP to compression uses these two interfaces.

3. **What is the difference between `json.Unmarshal` and `json.NewDecoder`?** Unmarshal reads from `[]byte` (entire payload in memory). Decoder reads from `io.Reader` (streaming, can handle sequences of JSON values).

4. **How does `database/sql` manage connections?** Cover: connection pool, `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`, why `sql.Open` does not connect, the importance of closing rows.

5. **Explain Go's time formatting with the reference time.** The reference time is `Mon Jan 2 15:04:05 MST 2006` — the digits 1-7. You use this actual time as a template, not format specifiers.

### Coding

6. **Write an HTTP middleware** that adds a request ID to the context, logs the request duration, and recovers from panics.

7. **Implement a JSON API endpoint** that accepts a POST body, validates it, saves to a database, and returns the created resource with proper status codes and error handling.

8. **Write a table-driven test** for a function that parses date strings in multiple formats, including error cases.

9. **Implement a custom `io.Reader`** that reads from a source and counts the bytes read.

```go
type CountingReader struct {
    reader io.Reader
    count  int64
}

func (r *CountingReader) Read(p []byte) (int, error) {
    n, err := r.reader.Read(p)
    r.count += int64(n)
    return n, err
}
```

### Scenario

10. **Your API is returning `"created_at":"0001-01-01T00:00:00Z"` in JSON responses.** What is happening and how do you fix it? (Answer: The `time.Time` zero value is being serialized. Use `*time.Time` with `omitempty`, or ensure the field is populated.)

---

## Further Reading

- [Go Standard Library Documentation](https://pkg.go.dev/std)
- [Writing Web Applications (Go Wiki)](https://go.dev/doc/articles/wiki/)
- [Go Blog: JSON and Go](https://go.dev/blog/json)
- [Go Blog: io/fs Design](https://go.dev/blog/io-fs)
- [Go Blog: Structured Logging with slog](https://go.dev/blog/slog)
- [Go Blog: Routing Enhancements in Go 1.22](https://go.dev/blog/routing-enhancements)
- [Go Database/SQL Tutorial](https://go.dev/doc/database/)
