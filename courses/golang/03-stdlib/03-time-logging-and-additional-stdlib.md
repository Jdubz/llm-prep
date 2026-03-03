# 03 – Time, Logging, and Additional Standard Library

This file assumes you have read `01-http-and-json.md` and `02-testing-and-io.md`. It covers the time package, structured logging with slog, strings/strconv, sort/slices, crypto, embed, templates, regex, and interview Q&A.

---

## 1. time: The Reference Time

### The Magic Reference Time

Go formats time using a reference time, not format specifiers:

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

### Common Formats Reference

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

## 2. log/slog: Structured Logging (Go 1.21+)

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

### slog Setup Template

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

## 3. strings and strconv

### strings Package

```go
strings.Contains("hello world", "world")    // true
strings.HasPrefix("hello", "he")            // true
strings.TrimSpace("  hello  ")              // "hello"
strings.Split("a,b,c", ",")                // ["a", "b", "c"]
strings.Join([]string{"a", "b"}, ", ")      // "a, b"
strings.ReplaceAll("hello", "l", "r")       // "herro"
strings.ToUpper("hello")                    // "HELLO"

// strings.Builder for efficient concatenation
var b strings.Builder
for i := 0; i < 1000; i++ {
    b.WriteString("hello ")
}
result := b.String()
```

### strconv Package

```go
// String to int
n, err := strconv.Atoi("42")

// Int to string
s := strconv.Itoa(42)

// String to float
f, err := strconv.ParseFloat("3.14", 64)

// Bool
b, err := strconv.ParseBool("true")
```

### net/url

```go
u, err := url.Parse("https://example.com/path?key=value&foo=bar")
u.Scheme   // "https"
u.Host     // "example.com"
u.Path     // "/path"
u.Query()  // map[key:[value] foo:[bar]]

// Build URLs safely
u := &url.URL{
    Scheme: "https",
    Host:   "api.example.com",
    Path:   "/v1/users",
}
q := u.Query()
q.Set("page", "2")
q.Set("limit", "50")
u.RawQuery = q.Encode()
// https://api.example.com/v1/users?limit=50&page=2
```

---

## 4. sort and slices Packages

### slices Package (Go 1.21+)

The `slices` package provides generic functions for slice operations:

```go
import "slices"

// Sort
nums := []int{3, 1, 4, 1, 5}
slices.Sort(nums) // [1, 1, 3, 4, 5]

// Sort with custom comparison
users := []User{{Name: "Charlie"}, {Name: "Alice"}, {Name: "Bob"}}
slices.SortFunc(users, func(a, b User) int {
    return strings.Compare(a.Name, b.Name)
})

// Stable sort (preserves order of equal elements)
slices.SortStableFunc(users, func(a, b User) int {
    return strings.Compare(a.Name, b.Name)
})

// Binary search
idx, found := slices.BinarySearch(nums, 3)

// Contains
slices.Contains(nums, 3) // true

// Index
slices.Index(nums, 3) // 2

// Compact (remove consecutive duplicates — sort first)
slices.Sort(nums)
nums = slices.Compact(nums) // [1, 3, 4, 5]

// Min/Max
slices.Min(nums) // 1
slices.Max(nums) // 5

// Reverse
slices.Reverse(nums)

// Clone
clone := slices.Clone(nums)
```

### sort Package (pre-generics, still useful)

```go
import "sort"

// Sort a slice of ints
sort.Ints(nums)

// Sort a slice of strings
sort.Strings(names)

// Custom sort with sort.Slice
sort.Slice(users, func(i, j int) bool {
    return users[i].Name < users[j].Name
})

// Stable sort
sort.SliceStable(users, func(i, j int) bool {
    return users[i].Age < users[j].Age
})

// Search (binary search on sorted data)
idx := sort.SearchInts(nums, 42)
```

### maps Package (Go 1.21+)

```go
import "maps"

// Keys
keys := slices.Collect(maps.Keys(m)) // collect into slice

// Values
vals := slices.Collect(maps.Values(m))

// Clone
m2 := maps.Clone(m)

// Equal
maps.Equal(m1, m2)

// Delete by predicate
maps.DeleteFunc(m, func(k string, v int) bool {
    return v < 0
})
```

---

## 5. Crypto Packages

### Hashing

```go
import (
    "crypto/sha256"
    "encoding/hex"
)

// Simple hash
hash := sha256.Sum256([]byte("hello world"))
hexString := hex.EncodeToString(hash[:])

// Streaming hash (for large data)
h := sha256.New()
io.Copy(h, file)    // hash the file without loading into memory
sum := h.Sum(nil)
```

### HMAC

```go
import "crypto/hmac"

func sign(message, secret []byte) []byte {
    mac := hmac.New(sha256.New, secret)
    mac.Write(message)
    return mac.Sum(nil)
}

func verify(message, signature, secret []byte) bool {
    expected := sign(message, secret)
    return hmac.Equal(signature, expected) // constant-time comparison
}
```

### Encryption (AES-GCM)

```go
import (
    "crypto/aes"
    "crypto/cipher"
    "crypto/rand"
)

func encrypt(plaintext, key []byte) ([]byte, error) {
    block, err := aes.NewCipher(key) // key must be 16, 24, or 32 bytes
    if err != nil {
        return nil, err
    }

    gcm, err := cipher.NewGCM(block)
    if err != nil {
        return nil, err
    }

    nonce := make([]byte, gcm.NonceSize())
    if _, err := rand.Read(nonce); err != nil {
        return nil, err
    }

    // Nonce is prepended to the ciphertext
    return gcm.Seal(nonce, nonce, plaintext, nil), nil
}

func decrypt(ciphertext, key []byte) ([]byte, error) {
    block, err := aes.NewCipher(key)
    if err != nil {
        return nil, err
    }

    gcm, err := cipher.NewGCM(block)
    if err != nil {
        return nil, err
    }

    nonceSize := gcm.NonceSize()
    if len(ciphertext) < nonceSize {
        return nil, fmt.Errorf("ciphertext too short")
    }

    nonce, ciphertext := ciphertext[:nonceSize], ciphertext[nonceSize:]
    return gcm.Open(nil, nonce, ciphertext, nil)
}
```

### Random Numbers

```go
import (
    "crypto/rand"
    "math/big"
)

// Cryptographically secure random bytes
token := make([]byte, 32)
if _, err := rand.Read(token); err != nil {
    log.Fatal(err)
}

// Cryptographically secure random integer
n, err := rand.Int(rand.Reader, big.NewInt(1000))
```

Use `crypto/rand` for security-sensitive randomness. Use `math/rand/v2` for non-security purposes (shuffling, simulation, etc.).

### TLS Configuration

```go
tlsConfig := &tls.Config{
    MinVersion: tls.VersionTLS12,
    MaxVersion: tls.VersionTLS13,

    CipherSuites: []uint16{
        tls.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
        tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
        tls.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
        tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
    },

    // Mutual TLS
    ClientAuth: tls.RequireAndVerifyClientCert,
    ClientCAs:  certPool,
}

srv := &http.Server{
    Addr:      ":443",
    TLSConfig: tlsConfig,
}
```

---

## 6. embed: Embedding Static Files

The `embed` package (Go 1.16+) lets you embed files into the binary at compile time. No more worrying about deploying static assets alongside your binary.

```go
import "embed"

//go:embed templates/*.html
var templateFS embed.FS

//go:embed static
var staticFS embed.FS

//go:embed version.txt
var version string // single file into a string

//go:embed config.json
var configBytes []byte // single file into bytes
```

### Serving Embedded Files

```go
//go:embed static
var staticFiles embed.FS

func main() {
    mux := http.NewServeMux()

    // Strip the "static" prefix from the path
    staticHandler := http.FileServer(http.FS(staticFiles))
    mux.Handle("GET /static/", staticHandler)

    // Or strip the prefix:
    stripped, _ := fs.Sub(staticFiles, "static")
    mux.Handle("GET /assets/", http.StripPrefix("/assets/", http.FileServer(http.FS(stripped))))
}
```

### Using Embedded Templates

```go
//go:embed templates/*.html
var templateFS embed.FS

var templates = template.Must(template.ParseFS(templateFS, "templates/*.html"))

func renderPage(w http.ResponseWriter, data PageData) {
    templates.ExecuteTemplate(w, "page.html", data)
}
```

**TS comparison:** This is like webpack's static imports or Vite's `import.meta.glob`, but built into the language and resolved at compile time.

---

## 7. text/template and html/template

### Template Execution

```go
import "text/template"

const tmpl = `Hello, {{.Name}}! You have {{.Count}} messages.`

type Data struct {
    Name  string
    Count int
}

t := template.Must(template.New("greeting").Parse(tmpl))
t.Execute(os.Stdout, Data{Name: "Alice", Count: 5})
// Output: Hello, Alice! You have 5 messages.
```

### Template Actions

```go
// Conditionals
{{if .IsAdmin}}Admin Panel{{else}}User Dashboard{{end}}

// Range (loops)
{{range .Items}}
  <li>{{.Name}} - ${{.Price}}</li>
{{end}}

// Range with index
{{range $i, $item := .Items}}
  <li>{{$i}}: {{$item.Name}}</li>
{{end}}

// With (scope change)
{{with .User}}
  Name: {{.Name}}, Email: {{.Email}}
{{end}}

// Variables
{{$name := .User.Name}}
Hello, {{$name}}

// Function calls
{{len .Items}} items
{{printf "%.2f" .Price}}
```

### html/template: Auto-Escaping for Security

`html/template` has the same API as `text/template` but automatically escapes output based on context:

```go
import "html/template"

const tmpl = `<h1>{{.Title}}</h1><p>{{.Body}}</p>`

// If Title is "<script>alert('xss')</script>", it becomes:
// <h1>&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;</h1>
```

Context-aware escaping means:
- HTML content is HTML-escaped.
- Attribute values are attribute-escaped.
- JavaScript contexts are JS-escaped.
- URL contexts are URL-escaped.

**Always use `html/template` for web output.** Use `text/template` for non-HTML output (config files, emails, etc.).

### Custom Template Functions

```go
funcMap := template.FuncMap{
    "upper": strings.ToUpper,
    "formatDate": func(t time.Time) string {
        return t.Format("Jan 2, 2006")
    },
    "add": func(a, b int) int {
        return a + b
    },
}

t := template.Must(
    template.New("page").Funcs(funcMap).Parse(`
        <h1>{{upper .Title}}</h1>
        <p>Created: {{formatDate .CreatedAt}}</p>
        <p>Total: {{add .A .B}}</p>
    `),
)
```

---

## 8. regexp: The RE2 Engine

### RE2: Safe by Design

Go uses the RE2 engine, which guarantees linear-time matching. There are no catastrophic backtracking scenarios. This makes Go's regex safe for user-provided patterns.

The trade-off: RE2 does not support backreferences or lookahead/lookbehind. If you need those features, you need a different approach.

```go
import "regexp"

// Compile once, use many times (compile is expensive)
var emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

func isValidEmail(email string) bool {
    return emailRegex.MatchString(email)
}
```

### Performance Characteristics

| Feature | Go (RE2) | JavaScript | PCRE (PHP, Python) |
|---------|----------|------------|-------------------|
| Backtracking | No | Yes | Yes |
| Time complexity | O(n) guaranteed | O(2^n) worst case | O(2^n) worst case |
| Backreferences | No | Yes | Yes |
| Lookahead/behind | No | Yes | Yes |
| ReDoS vulnerable | No | Yes | Yes |

### Common Operations

```go
re := regexp.MustCompile(`(\w+)=(\w+)`)

// Find first match
match := re.FindString("name=alice age=30") // "name=alice"

// Find all matches
matches := re.FindAllString("name=alice age=30", -1) // ["name=alice", "age=30"]

// Find submatches (capture groups)
subs := re.FindStringSubmatch("name=alice") // ["name=alice", "name", "alice"]

// Replace
result := re.ReplaceAllStringFunc("name=alice age=30", strings.ToUpper) // "NAME=ALICE AGE=30"

// Named groups
re := regexp.MustCompile(`(?P<key>\w+)=(?P<value>\w+)`)
names := re.SubexpNames() // ["", "key", "value"]
match := re.FindStringSubmatch("name=alice")
// match[re.SubexpIndex("key")] == "name"
// match[re.SubexpIndex("value")] == "alice"
```

---

## 9. errgroup (golang.org/x/sync)

While not in the standard library, `errgroup` is in the Go extended library and used so commonly it deserves mention:

```go
import "golang.org/x/sync/errgroup"

func fetchAll(ctx context.Context, urls []string) ([]Response, error) {
    g, ctx := errgroup.WithContext(ctx)
    responses := make([]Response, len(urls))

    for i, url := range urls {
        g.Go(func() error {
            resp, err := fetch(ctx, url)
            if err != nil {
                return err
            }
            responses[i] = resp
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err // first error cancels the context
    }
    return responses, nil
}
```

This is the Go equivalent of `Promise.all` with error handling and cancellation.

---

## 10. Interview Questions

### Conceptual

1. **Why would you use Go's standard `net/http` package instead of a framework like Gin or Echo?** Discuss: Go 1.22+ routing, the Handler interface, middleware composition, reduced dependencies, production readiness.

2. **Explain the `io.Reader` and `io.Writer` interfaces and why they matter.** Cover: composability, streaming, how `io.Copy` works, how everything from files to HTTP to compression uses these two interfaces.

3. **What is the difference between `json.Unmarshal` and `json.NewDecoder`?** Unmarshal reads from `[]byte` (entire payload in memory). Decoder reads from `io.Reader` (streaming, can handle sequences of JSON values).

4. **How does `database/sql` manage connections?** Cover: connection pool, `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`, why `sql.Open` does not connect, the importance of closing rows.

5. **Explain Go's time formatting with the reference time.** The reference time is `Mon Jan 2 15:04:05 MST 2006` — the digits 1-7. You use this actual time as a template, not format specifiers.

6. **What is the RE2 regex engine and why does Go use it?** RE2 guarantees O(n) matching, eliminating catastrophic backtracking and ReDoS vulnerabilities. The trade-off is no backreferences or lookahead/lookbehind.

7. **When would you use `log/slog` vs `log` vs a third-party library like zap?** `log` for simple scripts, `slog` for structured production logging (Go 1.21+), zap/zerolog for highest-performance logging with extreme throughput requirements.

### Coding

8. **Write an HTTP middleware** that adds a request ID to the context, logs the request duration, and recovers from panics.

9. **Implement a JSON API endpoint** that accepts a POST body, validates it, saves to a database, and returns the created resource with proper status codes and error handling.

10. **Write a table-driven test** for a function that parses date strings in multiple formats, including error cases.

11. **Implement a custom `io.Reader`** that reads from a source and counts the bytes read.

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

12. **Your API is returning `"created_at":"0001-01-01T00:00:00Z"` in JSON responses.** What is happening and how do you fix it? (Answer: The `time.Time` zero value is being serialized. Use `*time.Time` with `omitempty`, or ensure the field is populated.)

13. **You need to serve a 10GB file over HTTP.** How do you do this without running out of memory? (Answer: Use `io.Copy` or `http.ServeContent` — stream directly from disk to the response writer without buffering.)

14. **An HTTP client in your service is hanging in production with no errors.** What is the first thing you check? (Answer: The `http.Client` has no timeout set. The default client has no timeout. Add `Timeout: 30 * time.Second`.)

---

## Related Reading

- **slog in production** — [Module 07: Observability and Health](../07-production/02-observability-and-health.md), section 1 (Structured Logging with slog) extends the slog basics from section 2 with production handlers, log levels, and OpenTelemetry integration
- **time in HTTP services** — [Module 04: Advanced HTTP Patterns](../04-http-services/03-advanced-http-patterns.md), section 1 (Graceful Shutdown) uses `time.Duration` and `time.Ticker` for shutdown timeouts and connection draining
- **errgroup for concurrency** — [Module 02: Advanced Concurrency Patterns](../02-concurrency/03-advanced-concurrency-patterns.md) covers the broader concurrency patterns that `errgroup` from section 10 fits into
- **regexp in validation** — [Module 04: Request Handling and Validation](../04-http-services/02-request-handling-and-validation.md), section 3 shows regex-based validation in HTTP request handling
- **embed for deployment** — [Module 07: Project Structure and Configuration](../07-production/01-project-structure-and-configuration.md), section 6 (Embedding Assets) shows how `embed.FS` from section 7 is used to bundle migrations, templates, and static files into production binaries

---

## Practice Suggestions

These exercises reinforce the standard library concepts from this module (HTTP and JSON through Time, Logging, and Additional Stdlib):

1. **Build an HTTP JSON API from scratch** — Using only `net/http` and `encoding/json` (no frameworks), build a CRUD API for a resource (e.g., bookmarks). Implement proper Content-Type headers, status codes, and error responses. Use `json.NewDecoder` for request bodies and `json.NewEncoder` for responses.

2. **io.Reader pipeline** — Build a chain of `io.Reader` wrappers: one that counts bytes read, one that logs each line, and one that transforms content (e.g., uppercase). Compose them together and verify with tests that each stage works independently and in combination.

3. **Structured logging middleware** — Write HTTP middleware that uses `slog` to log each request with method, path, status code, duration, and request ID. Use `slog.With` to add request-scoped context. Test that log output contains the expected fields.

4. **Time zone handling** — Write a function that accepts a time string in one timezone and converts it to another. Use Go's reference time (`Mon Jan 2 15:04:05 MST 2006`) for parsing. Write table-driven tests covering edge cases: DST transitions, UTC offsets, and the zero value.

5. **Custom regexp validator** — Build a struct field validator that uses `regexp` to validate fields like email, phone number, and URL. Since Go's regexp uses RE2 (no backtracking), verify that your patterns perform consistently even on adversarial input.

6. **database/sql integration** — Connect to a SQLite database using `database/sql`, create a table, insert rows, and query them. Practice the `QueryRow` / `Query` / `Exec` patterns with proper error handling and `defer rows.Close()`. Compare this to the pgx approach in Module 05.

---

## Further Reading

- [Go Standard Library Documentation](https://pkg.go.dev/std)
- [Writing Web Applications (Go Wiki)](https://go.dev/doc/articles/wiki/)
- [Go Blog: JSON and Go](https://go.dev/blog/json)
- [Go Blog: io/fs Design](https://go.dev/blog/io-fs)
- [Go Blog: Structured Logging with slog](https://go.dev/blog/slog)
- [Go Blog: Routing Enhancements in Go 1.22](https://go.dev/blog/routing-enhancements)
- [Go Database/SQL Tutorial](https://go.dev/doc/database/)
- [net/http Package Documentation](https://pkg.go.dev/net/http)
- [Go Blog: HTTP/2 Server Push](https://go.dev/blog/h2push)
- [Go Crypto Best Practices](https://go.dev/doc/security/best-practices)
- [Go embed Documentation](https://pkg.go.dev/embed)
- [Go Blog: Embed Files](https://go.dev/blog/embed)
- [RE2 Syntax Reference](https://github.com/google/re2/wiki/Syntax)
- [Go slices Package](https://pkg.go.dev/slices)
- [Go maps Package](https://pkg.go.dev/maps)
