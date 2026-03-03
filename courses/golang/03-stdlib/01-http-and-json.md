# 01 – HTTP and JSON

## Philosophy

Go's standard library is not a collection of utilities you tolerate until you find a "real" framework. It is the framework. Production systems at Google, Cloudflare, and Uber run on `net/http` without a wrapper. The standard library is stable, well-tested, and fast.

Coming from TypeScript, where you install Express before writing your first route and pull in a dozen packages for basics, this is a culture shock. Embrace it.

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

### Complete Server Template

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

### net/http Internals: Connection Handling

When you call `srv.ListenAndServe()`, here is what happens:

1. The server binds to the address and starts accepting TCP connections.
2. For each connection, a new goroutine is spawned (`go c.serve()`).
3. The goroutine reads HTTP requests from the connection, dispatches them to the handler, and writes responses.
4. For HTTP/1.1 with keep-alive, the goroutine loops, handling multiple requests on the same connection.
5. The connection is closed when the client closes it, a timeout expires, or the server shuts down.

```go
// Simplified version of what the standard library does:
func (srv *Server) Serve(l net.Listener) error {
    for {
        conn, err := l.Accept()
        if err != nil {
            return err
        }
        go srv.handleConn(conn) // one goroutine per connection
    }
}
```

This means a server with 10,000 concurrent connections has 10,000 goroutines. This is fine — goroutines are cheap.

### HTTP/2 Support

Go's `net/http` supports HTTP/2 automatically when using TLS:

```go
srv := &http.Server{
    Addr:    ":443",
    Handler: mux,
}
// HTTP/2 is negotiated automatically via ALPN during TLS handshake
srv.ListenAndServeTLS("cert.pem", "key.pem")
```

For HTTP/2 without TLS (h2c), you need `golang.org/x/net/http2/h2c`.

### Transport and Client Customization

The `http.Client` uses an `http.Transport` for connection management:

```go
transport := &http.Transport{
    MaxIdleConns:        100,
    MaxIdleConnsPerHost: 10,
    IdleConnTimeout:     90 * time.Second,
    TLSHandshakeTimeout: 10 * time.Second,
    DisableKeepAlives:   false,

    TLSClientConfig: &tls.Config{
        MinVersion: tls.VersionTLS12,
    },

    DialContext: (&net.Dialer{
        Timeout:   30 * time.Second,
        KeepAlive: 30 * time.Second,
    }).DialContext,
}

client := &http.Client{
    Transport: transport,
    Timeout:   30 * time.Second,
    CheckRedirect: func(req *http.Request, via []*http.Request) error {
        if len(via) >= 10 {
            return fmt.Errorf("too many redirects")
        }
        return nil
    },
}
```

**Critical:** The default `http.Client` has no timeout. Always set one in production:

```go
// BAD — no timeout, can hang forever
resp, err := http.Get("https://example.com")

// GOOD — explicit timeout
client := &http.Client{Timeout: 10 * time.Second}
resp, err := client.Get("https://example.com")
```

### Response Body Leak

Always close the response body. Failing to do so leaks connections:

```go
resp, err := client.Get(url)
if err != nil {
    return err
}
defer resp.Body.Close() // CRITICAL — leaks connection if omitted

// Even if you don't read the body, drain it to allow connection reuse:
io.Copy(io.Discard, resp.Body)
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

### JSON Struct Tags Reference

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

**What is the difference between `json.Unmarshal` and `json.NewDecoder`?** Unmarshal reads from `[]byte` (entire payload in memory). Decoder reads from `io.Reader` (streaming, can handle sequences of JSON values).

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

### io Interface Composition

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

### Custom io.Reader Example

Implement a `CountingReader` that wraps any reader and counts bytes:

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

---

## 4. fmt: Formatting and the Stringer Interface

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
