# Module 06 Cheat Sheet: Testing in Go

## Table-Driven Test Template

```go
func TestMyFunction(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    int
        wantErr bool
    }{
        {"valid input", "42", 42, false},
        {"invalid input", "abc", 0, true},
        {"empty input", "", 0, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := MyFunction(tt.input)

            if tt.wantErr {
                require.Error(t, err)
                return
            }
            require.NoError(t, err)
            assert.Equal(t, tt.want, got)
        })
    }
}
```

## Parallel Subtests

```go
for _, tt := range tests {
    tt := tt // Capture (safe habit, not needed in Go 1.22+)
    t.Run(tt.name, func(t *testing.T) {
        t.Parallel()
        // ... test body
    })
}
```

## Mock Interface Template

```go
// Interface
type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*User, error)
    Create(ctx context.Context, user *User) error
}

// Fake implementation for tests
type fakeUserRepo struct {
    users map[int64]*User
    err   error // Force errors in tests
}

func (f *fakeUserRepo) GetByID(ctx context.Context, id int64) (*User, error) {
    if f.err != nil { return nil, f.err }
    u, ok := f.users[id]
    if !ok { return nil, ErrNotFound }
    return u, nil
}

func (f *fakeUserRepo) Create(ctx context.Context, user *User) error {
    if f.err != nil { return f.err }
    user.ID = int64(len(f.users) + 1)
    f.users[user.ID] = user
    return nil
}
```

## Generated Mocks

```go
// mockgen:
//go:generate mockgen -source=repository.go -destination=mocks/mock_repository.go -package=mocks

// mockery:
//go:generate mockery --name=UserRepository --output=mocks --outpkg=mocks
```

## httptest: Handler Testing

```go
func TestHandler(t *testing.T) {
    req := httptest.NewRequest("GET", "/api/users/1", nil)
    req.SetPathValue("id", "1") // Go 1.22+
    rr := httptest.NewRecorder()

    handler.ServeHTTP(rr, req)

    assert.Equal(t, http.StatusOK, rr.Code)

    var got User
    json.NewDecoder(rr.Body).Decode(&got)
    assert.Equal(t, "Alice", got.Name)
}
```

## httptest: POST with Body

```go
body := `{"name":"Alice","email":"alice@example.com"}`
req := httptest.NewRequest("POST", "/api/users",
    strings.NewReader(body))
req.Header.Set("Content-Type", "application/json")
rr := httptest.NewRecorder()

handler.ServeHTTP(rr, req)
assert.Equal(t, http.StatusCreated, rr.Code)
```

## httptest: Integration Server

```go
srv := httptest.NewServer(mux)
defer srv.Close()

resp, err := srv.Client().Get(srv.URL + "/api/users")
require.NoError(t, err)
defer resp.Body.Close()
assert.Equal(t, http.StatusOK, resp.StatusCode)
```

## httptest: Middleware Testing

```go
inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)
})
handler := myMiddleware(inner)

req := httptest.NewRequest("GET", "/", nil)
rr := httptest.NewRecorder()
handler.ServeHTTP(rr, req)
assert.Equal(t, http.StatusOK, rr.Code)
```

## testcontainers: PostgreSQL Setup

```go
func setupTestDB(t *testing.T) *pgxpool.Pool {
    t.Helper()
    ctx := context.Background()

    container, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
    )
    require.NoError(t, err)
    t.Cleanup(func() { container.Terminate(ctx) })

    connStr, _ := container.ConnectionString(ctx, "sslmode=disable")
    pool, _ := pgxpool.New(ctx, connStr)
    t.Cleanup(func() { pool.Close() })

    return pool
}
```

## Benchmark Template

```go
func BenchmarkMyFunction(b *testing.B) {
    // Setup (not timed)
    input := prepareInput()

    b.ResetTimer()
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        MyFunction(input)
    }
}

// Sub-benchmarks:
func BenchmarkMyFunction(b *testing.B) {
    for _, size := range []int{10, 100, 1000} {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            input := prepareInput(size)
            b.ResetTimer()
            for i := 0; i < b.N; i++ {
                MyFunction(input)
            }
        })
    }
}
```

## Fuzzing Template

```go
func FuzzMyParser(f *testing.F) {
    // Seed corpus
    f.Add("valid input")
    f.Add("")
    f.Add("edge case")

    f.Fuzz(func(t *testing.T, input string) {
        result, err := MyParser(input)
        if err != nil {
            return // Errors are OK
        }

        // Check invariants
        if result.Length < 0 {
            t.Errorf("negative length for input %q", input)
        }
    })
}
```

## Profiling Commands Reference

```bash
# CPU profile
go test -cpuprofile=cpu.prof -bench=. ./pkg/...
go tool pprof cpu.prof
  > top20
  > list FuncName
  > web              # Opens flame graph (needs graphviz)

# Memory profile
go test -memprofile=mem.prof -bench=. ./pkg/...
go tool pprof mem.prof
  > top20 -cum

# Execution trace
go test -trace=trace.out ./pkg/...
go tool trace trace.out

# Web-based pprof UI
go tool pprof -http=:8080 cpu.prof

# Live production profiling (add net/http/pprof import)
go tool pprof http://localhost:6060/debug/pprof/heap
go tool pprof http://localhost:6060/debug/pprof/goroutine
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
```

## go test Flags Reference

| Flag | Purpose | Example |
|---|---|---|
| `-run REGEX` | Run specific tests | `go test -run TestUser ./...` |
| `-bench REGEX` | Run benchmarks | `go test -bench=. -benchmem` |
| `-fuzz REGEX` | Run fuzz tests | `go test -fuzz=FuzzParse -fuzztime=30s` |
| `-count N` | Run tests N times | `go test -count=10` |
| `-race` | Enable race detector | `go test -race ./...` |
| `-short` | Enable short mode | `go test -short ./...` |
| `-v` | Verbose output | `go test -v ./...` |
| `-cover` | Show coverage % | `go test -cover ./...` |
| `-coverprofile F` | Generate coverage file | `go test -coverprofile=c.out` |
| `-cpuprofile F` | Generate CPU profile | `go test -cpuprofile=cpu.prof` |
| `-memprofile F` | Generate memory profile | `go test -memprofile=mem.prof` |
| `-trace F` | Generate execution trace | `go test -trace=trace.out` |
| `-timeout D` | Test timeout | `go test -timeout=5m` |
| `-parallel N` | Max parallel tests | `go test -parallel=4` |
| `-tags TAG` | Build tags | `go test -tags=integration` |
| `-failfast` | Stop on first failure | `go test -failfast ./...` |
| `-shuffle on` | Randomize test order | `go test -shuffle=on` |

## Test Helper Pattern

```go
func newTestUser(t *testing.T) *User {
    t.Helper() // Errors report CALLER's line, not this line
    return &User{
        Name:  "Test User",
        Email: fmt.Sprintf("test-%d@example.com", time.Now().UnixNano()),
    }
}

func mustSetup(t *testing.T) *Resource {
    t.Helper()
    r, err := NewResource()
    require.NoError(t, err)
    t.Cleanup(func() { r.Close() })
    return r
}
```

## Build Tags for Test Categories

```go
//go:build integration

package mypackage_test
// This file only compiles with: go test -tags=integration

//go:build !integration

package mypackage_test
// This file only compiles WITHOUT the integration tag
```

## Coverage Commands

```bash
go test -cover ./...                          # Summary per package
go test -coverprofile=coverage.out ./...      # Generate profile
go tool cover -func=coverage.out              # Per-function breakdown
go tool cover -html=coverage.out              # HTML visualization
go tool cover -html=coverage.out -o cover.html # Save HTML to file
```

## Key Gotchas

- `t.Parallel()` must be the first call in a subtest
- `t.Fatal`/`require` stops the current test; `t.Error`/`assert` continues
- `t.Helper()` makes error reporting point to the caller, not the helper
- `t.Cleanup` runs LIFO (last registered first), like defer
- `-race` adds ~10x CPU overhead; skip it for benchmarks
- `httptest.NewRecorder` does NOT enforce `WriteHeader` ordering
- Fuzzing crashes are saved in `testdata/fuzz/` and become regression tests
- `b.ResetTimer()` excludes setup code from benchmark measurements
- `testcontainers` requires Docker; guard with `testing.Short()` or build tags
