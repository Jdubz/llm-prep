# Module 03 Deep Dive: net/http Internals, Crypto, OS, Embed, Templates, and More

---

## 1. net/http Internals

### Connection Handling

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

HTTP/2 features that work transparently:
- Multiplexed streams over a single connection.
- Header compression (HPACK).
- Server push (via `http.Pusher` interface).

### Transport and Client Customization

The `http.Client` uses an `http.Transport` for connection management:

```go
transport := &http.Transport{
    MaxIdleConns:        100,
    MaxIdleConnsPerHost: 10,
    IdleConnTimeout:     90 * time.Second,
    TLSHandshakeTimeout: 10 * time.Second,
    DisableKeepAlives:   false,

    // Custom TLS
    TLSClientConfig: &tls.Config{
        MinVersion: tls.VersionTLS12,
    },

    // Custom DNS resolver
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

## 2. Crypto Packages

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
import "crypto/aes"
import "crypto/cipher"
import "crypto/rand"

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
import "crypto/rand"
import "math/big"

// Cryptographically secure random bytes
token := make([]byte, 32)
if _, err := rand.Read(token); err != nil {
    log.Fatal(err)
}

// Cryptographically secure random integer
n, err := rand.Int(rand.Reader, big.NewInt(1000))
```

Use `crypto/rand` for security-sensitive randomness. Use `math/rand/v2` for non-security purposes (shuffling, simulation, etc.).

---

## 3. os and filepath

### File Operations

```go
// Read entire file
data, err := os.ReadFile("config.json")

// Write entire file (creates or truncates)
err := os.WriteFile("output.txt", data, 0644)

// Open for reading
f, err := os.Open("data.csv")
defer f.Close()

// Create (or truncate) for writing
f, err := os.Create("output.csv")
defer f.Close()

// Open with flags
f, err := os.OpenFile("log.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
defer f.Close()
```

### Directory Walking

```go
// Walk directory tree (Go 1.16+ — use fs.WalkDir, not filepath.Walk)
err := filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
    if err != nil {
        return err
    }
    if d.IsDir() && d.Name() == ".git" {
        return filepath.SkipDir // skip .git directory
    }
    if filepath.Ext(path) == ".go" {
        fmt.Println(path)
    }
    return nil
})
```

`filepath.WalkDir` is faster than `filepath.Walk` because it does not call `os.Lstat` on every entry.

### Temp Files and Directories

```go
// Temp file
f, err := os.CreateTemp("", "myapp-*.json") // "" = default temp dir
if err != nil {
    return err
}
defer os.Remove(f.Name()) // clean up
defer f.Close()

// Temp directory
dir, err := os.MkdirTemp("", "myapp-*")
if err != nil {
    return err
}
defer os.RemoveAll(dir) // clean up
```

### filepath: Cross-Platform Path Handling

```go
// Always use filepath for path manipulation (handles OS separators)
path := filepath.Join("data", "users", "alice.json")
dir := filepath.Dir(path)        // "data/users"
base := filepath.Base(path)      // "alice.json"
ext := filepath.Ext(path)        // ".json"
abs, err := filepath.Abs(".")    // absolute path
rel, err := filepath.Rel("/a/b", "/a/b/c/d")  // "c/d"
```

---

## 4. embed: Embedding Static Files

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

## 5. text/template and html/template

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

## 6. regexp: The RE2 Engine

### RE2: Safe by Design

Go uses the RE2 engine, which guarantees linear-time matching. There are no catastrophic backtracking scenarios. This makes Go's regex safe for user-provided patterns.

The trade-off: RE2 does not support backreferences or lookahead/lookbehind. If you need those features, you need a different approach (or a different language).

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
result := re.ReplaceAllString("name=alice", "${1}: ${2}") // doesn't work like this
result := re.ReplaceAllStringFunc("name=alice age=30", strings.ToUpper) // "NAME=ALICE AGE=30"

// Named groups
re := regexp.MustCompile(`(?P<key>\w+)=(?P<value>\w+)`)
names := re.SubexpNames() // ["", "key", "value"]
match := re.FindStringSubmatch("name=alice")
// match[re.SubexpIndex("key")] == "name"
// match[re.SubexpIndex("value")] == "alice"
```

---

## 7. sort and slices Packages

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
keys := maps.Keys(m)        // returns an iterator (Go 1.23+)
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

## 8. Additional Standard Library Highlights

### strings and bytes

These packages mirror each other — `strings` for `string`, `bytes` for `[]byte`:

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

### strconv

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

### sync/errgroup (golang.org/x/sync)

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

## Further Reading

- [net/http Package Documentation](https://pkg.go.dev/net/http)
- [Go Blog: HTTP/2 Server Push](https://go.dev/blog/h2push)
- [Go Crypto Best Practices](https://go.dev/doc/security/best-practices)
- [Go embed Documentation](https://pkg.go.dev/embed)
- [Go Blog: Embed Files](https://go.dev/blog/embed)
- [RE2 Syntax Reference](https://github.com/google/re2/wiki/Syntax)
- [Go slices Package](https://pkg.go.dev/slices)
- [Go maps Package](https://pkg.go.dev/maps)
