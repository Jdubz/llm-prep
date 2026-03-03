# 02 – Request Handling and Validation

This file assumes you have read `01-handlers-routing-and-middleware.md`. It covers JSON binding, query params, path params, validation patterns, structured error responses, and content negotiation.

---

## 1. Structured Error Response

Define a consistent error format across your API:

```go
type APIError struct {
    Status  int                `json:"-"`                   // HTTP status code
    Code    string             `json:"code"`                // Machine-readable error code
    Message string             `json:"message"`             // Human-readable message
    Details map[string]string  `json:"details,omitempty"`   // Field-level errors
}

func (e *APIError) Error() string {
    return e.Message
}

// writeError sends a structured JSON error response.
func writeError(w http.ResponseWriter, err *APIError) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(err.Status)
    json.NewEncoder(w).Encode(err)
}

// JSON response helper
func writeJSON(w http.ResponseWriter, status int, data any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    json.NewEncoder(w).Encode(data)
}

// Simple error helper for quick responses
func writeSimpleError(w http.ResponseWriter, status int, code, message string) {
    writeJSON(w, status, map[string]string{
        "code":    code,
        "message": message,
    })
}
```

---

## 2. Request Parsing

### JSON Body Decoding

```go
func createUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest

    // Limit body size to prevent abuse
    r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MB

    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields() // Strict parsing — like TypeScript strict mode

    if err := dec.Decode(&req); err != nil {
        writeError(w, &APIError{
            Status: http.StatusBadRequest, Code: "INVALID_JSON",
            Message: "malformed request body",
        })
        return
    }

    // ... process request

    // Encode response
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(user)
}
```

### Path Parameters

```go
func getUser(w http.ResponseWriter, r *http.Request) {
    // Go 1.22+: PathValue extracts named parameters
    id := r.PathValue("id")

    // Parse to int if needed
    userID, err := strconv.ParseInt(id, 10, 64)
    if err != nil {
        writeError(w, &APIError{
            Status:  http.StatusBadRequest,
            Code:    "INVALID_ID",
            Message: "invalid user ID",
        })
        return
    }
    _ = userID
}
```

### Query Parameters

```go
func listUsers(w http.ResponseWriter, r *http.Request) {
    q := r.URL.Query()

    page, _ := strconv.Atoi(q.Get("page"))
    if page <= 0 {
        page = 1
    }

    limit, _ := strconv.Atoi(q.Get("limit"))
    if limit <= 0 || limit > 100 {
        limit = 20
    }

    search := q.Get("search") // "" if not provided

    // Optional enum parameter
    sort := q.Get("sort")
    switch sort {
    case "name", "created_at", "":
        // valid
    default:
        writeError(w, &APIError{
            Status:  http.StatusBadRequest,
            Code:    "INVALID_SORT",
            Message: "sort must be 'name' or 'created_at'",
        })
        return
    }

    _ = page
    _ = limit
    _ = search
}
```

### Request Headers

```go
func handler(w http.ResponseWriter, r *http.Request) {
    // Read specific headers
    contentType := r.Header.Get("Content-Type")
    auth := r.Header.Get("Authorization")
    acceptLanguage := r.Header.Get("Accept-Language")

    // Check for presence
    if auth == "" {
        http.Error(w, "unauthorized", http.StatusUnauthorized)
        return
    }

    _ = contentType
    _ = acceptLanguage
}
```

---

## 3. Input Validation

### Manual Validation

```go
type CreateUserRequest struct {
    Email    string `json:"email"`
    Name     string `json:"name"`
    Age      int    `json:"age"`
}

func (r *CreateUserRequest) Validate() *APIError {
    details := make(map[string]string)

    if r.Email == "" {
        details["email"] = "required"
    } else if !strings.Contains(r.Email, "@") {
        details["email"] = "invalid email format"
    }

    if r.Name == "" {
        details["name"] = "required"
    } else if len(r.Name) > 100 {
        details["name"] = "must be 100 characters or fewer"
    }

    if r.Age < 0 || r.Age > 150 {
        details["age"] = "must be between 0 and 150"
    }

    if len(details) > 0 {
        return &APIError{
            Status:  http.StatusBadRequest,
            Code:    "VALIDATION_ERROR",
            Message: "request validation failed",
            Details: details,
        }
    }
    return nil
}
```

### Using go-playground/validator

```go
import "github.com/go-playground/validator/v10"

var validate = validator.New()

type CreateUserRequest struct {
    Email string `json:"email" validate:"required,email"`
    Name  string `json:"name"  validate:"required,max=100"`
    Age   int    `json:"age"   validate:"gte=0,lte=150"`
}

func decodeAndValidate[T any](r *http.Request) (T, *APIError) {
    var req T
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        return req, &APIError{
            Status:  http.StatusBadRequest,
            Code:    "INVALID_JSON",
            Message: "malformed request body",
        }
    }

    if err := validate.Struct(req); err != nil {
        details := make(map[string]string)
        for _, e := range err.(validator.ValidationErrors) {
            details[e.Field()] = e.Tag()
        }
        return req, &APIError{
            Status:  http.StatusBadRequest,
            Code:    "VALIDATION_ERROR",
            Message: "request validation failed",
            Details: details,
        }
    }

    return req, nil
}
```

The generic `decodeAndValidate[T]` function eliminates the repetitive decode-validate boilerplate you'd write in every handler. This is idiomatic Go 1.18+ — generics are appropriate here.

---

## 4. Request/Response Patterns

### JSON Encoding/Decoding

```go
// Decode request body
func createUser(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest

    // Limit body size to prevent abuse
    r.Body = http.MaxBytesReader(w, r.Body, 1<<20) // 1 MB

    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields() // Strict parsing

    if err := dec.Decode(&req); err != nil {
        writeError(w, &APIError{
            Status: http.StatusBadRequest, Code: "INVALID_JSON",
            Message: "malformed request body",
        })
        return
    }

    // ... process request

    // Encode response
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(user)
}
```

### Streaming Responses (Server-Sent Events)

```go
func streamEvents(w http.ResponseWriter, r *http.Request) {
    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "streaming not supported", http.StatusInternalServerError)
        return
    }

    w.Header().Set("Content-Type", "text/event-stream")
    w.Header().Set("Cache-Control", "no-cache")
    w.Header().Set("Connection", "keep-alive")

    for {
        select {
        case <-r.Context().Done():
            return // Client disconnected
        case event := <-eventChan:
            fmt.Fprintf(w, "data: %s\n\n", event)
            flusher.Flush()
        }
    }
}
```

### File Serving and Static Assets

```go
// Serve a directory
mux.Handle("GET /static/", http.StripPrefix("/static/",
    http.FileServer(http.Dir("./public"))))

// Serve embedded files (compiled into binary)
//go:embed static/*
var staticFS embed.FS

mux.Handle("GET /static/", http.FileServerFS(staticFS))

// Serve a single file download
func downloadHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Disposition", "attachment; filename=report.pdf")
    http.ServeFile(w, r, "/path/to/report.pdf")
}
```

### Multipart Uploads

```go
func uploadHandler(w http.ResponseWriter, r *http.Request) {
    // Limit upload size: 32 MB
    r.ParseMultipartForm(32 << 20)

    file, header, err := r.FormFile("upload")
    if err != nil {
        http.Error(w, "missing file", http.StatusBadRequest)
        return
    }
    defer file.Close()

    // header.Filename, header.Size, header.Header (MIME type)
    dst, err := os.Create(filepath.Join("uploads", header.Filename))
    if err != nil {
        http.Error(w, "failed to save", http.StatusInternalServerError)
        return
    }
    defer dst.Close()

    io.Copy(dst, file)
    w.WriteHeader(http.StatusCreated)
}
```

---

## 5. HTTP Client Template

```go
client := &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 10,
        IdleConnTimeout:     90 * time.Second,
    },
}

// Per-request with context:
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
resp, err := client.Do(req)
if err != nil { /* handle */ }
defer resp.Body.Close()
```

### Full Per-Request Example

```go
func fetchUser(ctx context.Context, client *http.Client, id int) (*User, error) {
    // Request-specific timeout (shorter than client timeout)
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()

    req, err := http.NewRequestWithContext(ctx, "GET",
        fmt.Sprintf("https://api.example.com/users/%d", id), nil)
    if err != nil {
        return nil, fmt.Errorf("creating request: %w", err)
    }

    req.Header.Set("Authorization", "Bearer "+getToken())

    resp, err := client.Do(req)
    if err != nil {
        return nil, fmt.Errorf("executing request: %w", err)
    }
    defer resp.Body.Close() // ALWAYS close the body

    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
        return nil, fmt.Errorf("unexpected status %d: %s", resp.StatusCode, body)
    }

    var user User
    if err := json.NewDecoder(resp.Body).Decode(&user); err != nil {
        return nil, fmt.Errorf("decoding response: %w", err)
    }

    return &user, nil
}
```

### Retry with Exponential Backoff

```go
func withRetry(ctx context.Context, maxRetries int, fn func() (*http.Response, error)) (*http.Response, error) {
    var lastErr error

    for attempt := 0; attempt <= maxRetries; attempt++ {
        if attempt > 0 {
            backoff := time.Duration(1<<uint(attempt-1)) * 100 * time.Millisecond
            // Add jitter: 50-150% of backoff
            jitter := time.Duration(rand.Int63n(int64(backoff)))
            backoff = backoff/2 + jitter

            select {
            case <-ctx.Done():
                return nil, ctx.Err()
            case <-time.After(backoff):
            }
        }

        resp, err := fn()
        if err != nil {
            lastErr = err
            continue
        }

        // Only retry on 5xx or 429
        if resp.StatusCode >= 500 || resp.StatusCode == 429 {
            resp.Body.Close()
            lastErr = fmt.Errorf("status %d", resp.StatusCode)
            continue
        }

        return resp, nil
    }

    return nil, fmt.Errorf("max retries exceeded: %w", lastErr)
}
```

---

## 6. Health Check Handler

```go
// internal/handler/health.go
package handler

import (
    "encoding/json"
    "net/http"
    "sync/atomic"
    "time"
)

type HealthHandler struct {
    ready     atomic.Bool
    startTime time.Time
    version   string
}

func NewHealthHandler(version string) *HealthHandler {
    return &HealthHandler{
        startTime: time.Now(),
        version:   version,
    }
}

func (h *HealthHandler) SetReady(ready bool) {
    h.ready.Store(ready)
}

// Liveness: is the process alive?
func (h *HealthHandler) LivenessHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(map[string]any{
        "status":  "alive",
        "version": h.version,
        "uptime":  time.Since(h.startTime).String(),
    })
}

// Readiness: can the service handle traffic?
func (h *HealthHandler) ReadinessHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")

    if !h.ready.Load() {
        w.WriteHeader(http.StatusServiceUnavailable)
        json.NewEncoder(w).Encode(map[string]string{"status": "not_ready"})
        return
    }

    json.NewEncoder(w).Encode(map[string]string{"status": "ready"})
}
```

---

## Related Reading

- **JSON encoding/decoding foundations** — [Module 03: HTTP and JSON](../03-stdlib/01-http-and-json.md), section 2 (encoding/json) covers the marshal/unmarshal mechanics that underpin the request decoding and response encoding in this file
- **Health checks in production** — [Module 07: Observability and Health](../07-production/02-observability-and-health.md), section 4 (Health Checks) expands the health check handler from section 6 with Kubernetes liveness, readiness, and startup probes
- **Error handling patterns** — [Module 07: Project Structure and Configuration](../07-production/01-project-structure-and-configuration.md), section 3 (Error Handling in Production) shows how the `AppError` and `ErrorHandler` middleware from section 1 scale to production services
- **Repository pattern for data** — [Module 05: Queries, Transactions, and Patterns](../05-data-storage/02-queries-transactions-and-patterns.md), section 3 (Repository Pattern) shows the store interfaces that handlers validate input for and pass data to
- **Validation with struct tags** — [Module 08: Reflection and Advanced Abstractions](../08-advanced-patterns/03-reflection-and-advanced-abstractions.md), section 1 explains the reflection mechanism behind struct tag validation libraries
