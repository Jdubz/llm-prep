# Module 06: Testing in Go

## Overview

Go's testing story is one of its strongest selling points, and it works completely differently from what you know in TypeScript. There's no Jest, no Mocha, no Vitest. Go ships a `testing` package and a `go test` command that handle everything. No configuration files, no test runners to install, no assertion library debates.

The cultural difference is just as important: Go developers tend to write more integration tests and fewer mocks than the TypeScript/Java world. The tooling supports this — testcontainers, httptest, and the race detector are all first-class. Benchmarking and profiling are built into the test command, not bolted on.

---

## Table of Contents

1. [Table-Driven Tests](#table-driven-tests)
2. [Mocking](#mocking)
3. [httptest Package](#httptest-package)
4. [Integration Tests with testcontainers-go](#integration-tests-with-testcontainers-go)
5. [Benchmarking](#benchmarking)
6. [Profiling](#profiling)
7. [Fuzzing](#fuzzing)
8. [Test Fixtures](#test-fixtures)
9. [Build Tags for Test Categories](#build-tags-for-test-categories)
10. [Test Coverage](#test-coverage)
11. [Interview Questions](#interview-questions)

---

## Table-Driven Tests

This is THE Go testing pattern. You'll see it everywhere — in the standard library, in every open-source project, in every interview.

### Basic Structure

```go
func TestParseAge(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    int
        wantErr bool
    }{
        {
            name:  "valid age",
            input: "25",
            want:  25,
        },
        {
            name:  "zero",
            input: "0",
            want:  0,
        },
        {
            name:    "negative",
            input:   "-1",
            wantErr: true,
        },
        {
            name:    "not a number",
            input:   "abc",
            wantErr: true,
        },
        {
            name:    "empty string",
            input:   "",
            wantErr: true,
        },
        {
            name:    "too large",
            input:   "200",
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := ParseAge(tt.input)

            if tt.wantErr {
                if err == nil {
                    t.Errorf("ParseAge(%q) expected error, got nil", tt.input)
                }
                return
            }

            if err != nil {
                t.Errorf("ParseAge(%q) unexpected error: %v", tt.input, err)
                return
            }

            if got != tt.want {
                t.Errorf("ParseAge(%q) = %d, want %d", tt.input, got, tt.want)
            }
        })
    }
}
```

### Why This Pattern Works

1. **Adding test cases is trivial** — just add another struct to the slice.
2. **`t.Run` creates subtests** — each case runs independently, shows up named in output, can be run individually.
3. **Failures are clear** — each test case has a descriptive name.
4. **No assertion library needed** — though `testify/assert` is common for reducing boilerplate.

### Parallel Subtests

```go
func TestUserService_GetByID(t *testing.T) {
    tests := []struct {
        name    string
        id      int64
        want    *User
        wantErr error
    }{
        {name: "existing user", id: 1, want: &User{ID: 1, Name: "Alice"}},
        {name: "not found", id: 999, wantErr: ErrNotFound},
    }

    for _, tt := range tests {
        tt := tt // Capture range variable (not needed in Go 1.22+, but safe to include)
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel() // Run this subtest concurrently with others

            got, err := svc.GetByID(context.Background(), tt.id)
            if !errors.Is(err, tt.wantErr) {
                t.Errorf("GetByID(%d) error = %v, wantErr %v", tt.id, err, tt.wantErr)
                return
            }
            if tt.want != nil && got.Name != tt.want.Name {
                t.Errorf("GetByID(%d) = %v, want %v", tt.id, got, tt.want)
            }
        })
    }
}
```

**Important**: `t.Parallel()` runs subtests concurrently. Make sure each test case uses its own data — don't share mutable state between parallel subtests.

### Using testify/assert

```go
import (
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestCreateUser(t *testing.T) {
    user, err := svc.Create(ctx, &CreateUserInput{Name: "Alice", Email: "a@b.com"})

    // require stops the test immediately on failure (like t.Fatal)
    require.NoError(t, err)
    require.NotNil(t, user)

    // assert records failure but continues (like t.Error)
    assert.Equal(t, "Alice", user.Name)
    assert.Equal(t, "a@b.com", user.Email)
    assert.NotZero(t, user.ID)
    assert.WithinDuration(t, time.Now(), user.CreatedAt, time.Second)
}
```

---

## Mocking

### Interfaces as Contracts

In TypeScript, you might mock modules with `jest.mock()`. In Go, mocking is built on interfaces. If you design your code to depend on interfaces, mocking is trivial:

```go
// The interface (contract)
type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*User, error)
    Create(ctx context.Context, user *User) error
}

// Production implementation
type postgresUserRepo struct { pool *pgxpool.Pool }

// Test implementation — a simple fake
type fakeUserRepo struct {
    users map[int64]*User
    err   error
}

func (f *fakeUserRepo) GetByID(ctx context.Context, id int64) (*User, error) {
    if f.err != nil {
        return nil, f.err
    }
    user, ok := f.users[id]
    if !ok {
        return nil, ErrNotFound
    }
    return user, nil
}

func (f *fakeUserRepo) Create(ctx context.Context, user *User) error {
    if f.err != nil {
        return f.err
    }
    user.ID = int64(len(f.users) + 1)
    f.users[user.ID] = user
    return nil
}

// Test using the fake
func TestUserService_GetByID(t *testing.T) {
    repo := &fakeUserRepo{
        users: map[int64]*User{
            1: {ID: 1, Name: "Alice", Email: "alice@example.com"},
        },
    }

    svc := NewUserService(repo, slog.Default())

    user, err := svc.GetByID(context.Background(), 1)
    require.NoError(t, err)
    assert.Equal(t, "Alice", user.Name)
}
```

This is the idiomatic approach. No mock library required. The fake implements the interface, and you control its behavior through its fields.

### Test Doubles: Fakes vs Stubs vs Mocks

| Type | Purpose | Example |
|---|---|---|
| **Fake** | Working implementation with shortcuts | In-memory database, fake email sender |
| **Stub** | Returns canned responses | Always returns the same user |
| **Mock** | Verifies interactions (was this called?) | Assert `Create` was called with specific args |

**Go community preference**: Fakes > Stubs > Mocks. Fakes test behavior, mocks test implementation details.

### When to Use mockgen/mockery

For interfaces with many methods, writing fakes by hand is tedious. Generated mocks help:

```go
// Using mockgen (go.uber.org/mock):
//go:generate mockgen -source=repository.go -destination=mocks/mock_repository.go -package=mocks

func TestUserService_Create(t *testing.T) {
    ctrl := gomock.NewController(t)

    mockRepo := mocks.NewMockUserRepository(ctrl)

    // Set expectations
    mockRepo.EXPECT().
        Create(gomock.Any(), gomock.Any()).
        DoAndReturn(func(ctx context.Context, user *User) error {
            user.ID = 42
            return nil
        })

    svc := NewUserService(mockRepo, slog.Default())

    user, err := svc.Create(context.Background(), &CreateUserInput{
        Name: "Bob", Email: "bob@example.com",
    })

    require.NoError(t, err)
    assert.Equal(t, int64(42), user.ID)
}
```

```go
// Using mockery:
//go:generate mockery --name=UserRepository --output=mocks --outpkg=mocks

func TestUserService_Create(t *testing.T) {
    mockRepo := mocks.NewMockUserRepository(t) // Automatically calls t.Cleanup

    mockRepo.EXPECT().
        Create(mock.Anything, mock.MatchedBy(func(u *User) bool {
            return u.Email == "bob@example.com"
        })).
        RunAndReturn(func(ctx context.Context, user *User) error {
            user.ID = 42
            return nil
        })

    svc := NewUserService(mockRepo, slog.Default())
    user, err := svc.Create(context.Background(), &CreateUserInput{
        Name: "Bob", Email: "bob@example.com",
    })

    require.NoError(t, err)
    assert.Equal(t, int64(42), user.ID)
}
```

---

## httptest Package

### Testing Handlers with ResponseRecorder

```go
func TestGetUserHandler(t *testing.T) {
    // Setup
    svc := &fakeUserService{
        users: map[int64]*User{
            1: {ID: 1, Name: "Alice", Email: "alice@example.com"},
        },
    }
    handler := NewUserHandler(svc)

    // Create request
    req := httptest.NewRequest("GET", "/api/users/1", nil)
    req.SetPathValue("id", "1") // Go 1.22+ path value

    // Create response recorder
    rr := httptest.NewRecorder()

    // Execute
    handler.GetUser(rr, req)

    // Assert response
    assert.Equal(t, http.StatusOK, rr.Code)
    assert.Equal(t, "application/json", rr.Header().Get("Content-Type"))

    var got User
    err := json.NewDecoder(rr.Body).Decode(&got)
    require.NoError(t, err)
    assert.Equal(t, "Alice", got.Name)
}

func TestGetUserHandler_NotFound(t *testing.T) {
    svc := &fakeUserService{users: map[int64]*User{}}
    handler := NewUserHandler(svc)

    req := httptest.NewRequest("GET", "/api/users/999", nil)
    req.SetPathValue("id", "999")
    rr := httptest.NewRecorder()

    handler.GetUser(rr, req)

    assert.Equal(t, http.StatusNotFound, rr.Code)
}

func TestCreateUserHandler(t *testing.T) {
    svc := &fakeUserService{users: map[int64]*User{}}
    handler := NewUserHandler(svc)

    body := `{"name":"Bob","email":"bob@example.com"}`
    req := httptest.NewRequest("POST", "/api/users", strings.NewReader(body))
    req.Header.Set("Content-Type", "application/json")
    rr := httptest.NewRecorder()

    handler.CreateUser(rr, req)

    assert.Equal(t, http.StatusCreated, rr.Code)
}
```

### Integration Testing with httptest.NewServer

```go
func TestAPIIntegration(t *testing.T) {
    // Create a full server with all middleware and routing
    mux := setupRoutes(testDeps) // Your real router setup function
    srv := httptest.NewServer(mux)
    defer srv.Close()

    // Test with a real HTTP client
    client := srv.Client()

    // Test create
    body := `{"name":"Alice","email":"alice@example.com"}`
    resp, err := client.Post(srv.URL+"/api/users", "application/json", strings.NewReader(body))
    require.NoError(t, err)
    defer resp.Body.Close()
    assert.Equal(t, http.StatusCreated, resp.StatusCode)

    var created User
    json.NewDecoder(resp.Body).Decode(&created)
    assert.NotZero(t, created.ID)

    // Test get
    resp, err = client.Get(fmt.Sprintf("%s/api/users/%d", srv.URL, created.ID))
    require.NoError(t, err)
    defer resp.Body.Close()
    assert.Equal(t, http.StatusOK, resp.StatusCode)
}
```

### Testing Middleware

```go
func TestAuthMiddleware(t *testing.T) {
    tests := []struct {
        name       string
        authHeader string
        wantStatus int
    }{
        {"no header", "", http.StatusUnauthorized},
        {"invalid token", "Bearer invalid", http.StatusUnauthorized},
        {"valid token", "Bearer " + validTestToken, http.StatusOK},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // The "inner" handler that should only be reached with valid auth
            inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
                w.WriteHeader(http.StatusOK)
            })

            // Wrap with auth middleware
            handler := jwtAuth(testSecretKey)(inner)

            req := httptest.NewRequest("GET", "/protected", nil)
            if tt.authHeader != "" {
                req.Header.Set("Authorization", tt.authHeader)
            }
            rr := httptest.NewRecorder()

            handler.ServeHTTP(rr, req)

            assert.Equal(t, tt.wantStatus, rr.Code)
        })
    }
}
```

---

## Integration Tests with testcontainers-go

### PostgreSQL Container

```go
func setupTestDB(t *testing.T) *pgxpool.Pool {
    t.Helper()
    ctx := context.Background()

    container, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(
            wait.ForLog("database system is ready to accept connections").
                WithOccurrence(2).
                WithStartupTimeout(30*time.Second),
        ),
    )
    require.NoError(t, err)
    t.Cleanup(func() { container.Terminate(ctx) })

    connStr, _ := container.ConnectionString(ctx, "sslmode=disable")
    pool, err := pgxpool.New(ctx, connStr)
    require.NoError(t, err)
    t.Cleanup(func() { pool.Close() })

    // Run migrations
    runMigrations(t, connStr)

    return pool
}
```

### Redis Container

```go
func setupTestRedis(t *testing.T) *redis.Client {
    t.Helper()
    ctx := context.Background()

    container, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
        ContainerRequest: testcontainers.ContainerRequest{
            Image:        "redis:7-alpine",
            ExposedPorts: []string{"6379/tcp"},
            WaitingFor:   wait.ForLog("Ready to accept connections"),
        },
        Started: true,
    })
    require.NoError(t, err)
    t.Cleanup(func() { container.Terminate(ctx) })

    host, _ := container.Host(ctx)
    port, _ := container.MappedPort(ctx, "6379")

    rdb := redis.NewClient(&redis.Options{
        Addr: fmt.Sprintf("%s:%s", host, port.Port()),
    })
    t.Cleanup(func() { rdb.Close() })

    return rdb
}
```

### Kafka Container

```go
func setupTestKafka(t *testing.T) *kafka.Writer {
    t.Helper()
    ctx := context.Background()

    container, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
        ContainerRequest: testcontainers.ContainerRequest{
            Image:        "confluentinc/cp-kafka:7.5.0",
            ExposedPorts: []string{"9092/tcp"},
            Env: map[string]string{
                "KAFKA_LISTENERS":                "PLAINTEXT://0.0.0.0:9092",
                "KAFKA_ADVERTISED_LISTENERS":     "PLAINTEXT://localhost:9092",
                "KAFKA_NODE_ID":                  "1",
                "KAFKA_PROCESS_ROLES":            "broker,controller",
                "KAFKA_CONTROLLER_QUORUM_VOTERS": "1@localhost:9093",
                "CLUSTER_ID":                     "test-cluster",
            },
            WaitingFor: wait.ForLog("Kafka Server started"),
        },
        Started: true,
    })
    require.NoError(t, err)
    t.Cleanup(func() { container.Terminate(ctx) })

    host, _ := container.Host(ctx)
    port, _ := container.MappedPort(ctx, "9092")
    addr := fmt.Sprintf("%s:%s", host, port.Port())

    return &kafka.Writer{
        Addr:     kafka.TCP(addr),
        Topic:    "test-topic",
        Balancer: &kafka.LeastBytes{},
    }
}
```

### Full Integration Test

```go
func TestUserWorkflow(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    pool := setupTestDB(t)
    rdb := setupTestRedis(t)

    repo := postgres.NewUserRepository(pool)
    cache := rediscache.NewCacheRepository(rdb)
    svc := service.NewUserService(repo, cache, slog.Default())

    ctx := context.Background()

    // Create
    user, err := svc.Create(ctx, &service.CreateUserInput{
        Name:  "Alice",
        Email: "alice@example.com",
    })
    require.NoError(t, err)
    assert.NotZero(t, user.ID)

    // Read (should hit database, then cache)
    got, err := svc.GetByID(ctx, user.ID)
    require.NoError(t, err)
    assert.Equal(t, "Alice", got.Name)

    // Read again (should hit cache)
    got2, err := svc.GetByID(ctx, user.ID)
    require.NoError(t, err)
    assert.Equal(t, got.Name, got2.Name)

    // Update (should invalidate cache)
    user.Name = "Alice Updated"
    err = svc.Update(ctx, user)
    require.NoError(t, err)

    // Read after update (should miss cache, hit database)
    got3, err := svc.GetByID(ctx, user.ID)
    require.NoError(t, err)
    assert.Equal(t, "Alice Updated", got3.Name)
}
```

---

## Benchmarking

### Basic Benchmark

```go
func BenchmarkJSONMarshal(b *testing.B) {
    user := &User{ID: 1, Name: "Alice", Email: "alice@example.com"}

    b.ResetTimer() // Reset after setup
    for i := 0; i < b.N; i++ {
        json.Marshal(user)
    }
}

func BenchmarkJSONMarshal_Large(b *testing.B) {
    users := make([]User, 1000)
    for i := range users {
        users[i] = User{ID: int64(i), Name: fmt.Sprintf("User %d", i)}
    }

    b.ResetTimer()
    b.ReportAllocs() // Report memory allocations
    for i := 0; i < b.N; i++ {
        json.Marshal(users)
    }
}
```

### Running Benchmarks

```bash
# Run all benchmarks
go test -bench=. ./...

# Run specific benchmark
go test -bench=BenchmarkJSONMarshal -benchmem ./pkg/...

# Run with count for statistical significance
go test -bench=. -count=10 -benchmem ./pkg/...

# Save results for comparison
go test -bench=. -count=10 -benchmem ./pkg/... > old.txt
# ... make changes ...
go test -bench=. -count=10 -benchmem ./pkg/... > new.txt

# Compare with benchstat
benchstat old.txt new.txt
```

### Interpreting Results

```
BenchmarkJSONMarshal-8     5000000    234 ns/op    128 B/op    2 allocs/op
```

| Field | Meaning |
|---|---|
| `-8` | GOMAXPROCS (number of CPUs used) |
| `5000000` | Number of iterations |
| `234 ns/op` | Nanoseconds per operation |
| `128 B/op` | Bytes allocated per operation |
| `2 allocs/op` | Heap allocations per operation |

### Sub-Benchmarks

```go
func BenchmarkSort(b *testing.B) {
    sizes := []int{10, 100, 1000, 10000}

    for _, size := range sizes {
        b.Run(fmt.Sprintf("size=%d", size), func(b *testing.B) {
            data := make([]int, size)
            for i := range data {
                data[i] = rand.Intn(size)
            }

            b.ResetTimer()
            for i := 0; i < b.N; i++ {
                // Copy to avoid sorting already-sorted data
                tmp := make([]int, len(data))
                copy(tmp, data)
                sort.Ints(tmp)
            }
        })
    }
}
```

---

## Profiling

### CPU Profile

```bash
# Generate CPU profile during test
go test -cpuprofile=cpu.prof -bench=. ./pkg/...

# Analyze with pprof
go tool pprof cpu.prof

# Interactive commands:
# top20          — top 20 functions by CPU time
# list FuncName  — source code annotated with CPU time
# web            — open flame graph in browser (requires graphviz)
```

### Memory Profile

```bash
# Generate memory profile
go test -memprofile=mem.prof -bench=. ./pkg/...

go tool pprof mem.prof

# top20 -cum    — top by cumulative allocations
# list FuncName — see allocation hotspots in source
```

### Goroutine Profile

```bash
go tool pprof http://localhost:6060/debug/pprof/goroutine
```

### net/http/pprof for Production

```go
import _ "net/http/pprof"

// In main() or a separate debug server:
go func() {
    // Serve pprof on a different port (not exposed publicly!)
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

Access profiles at:
- `http://localhost:6060/debug/pprof/` — index
- `http://localhost:6060/debug/pprof/goroutine` — goroutine stacks
- `http://localhost:6060/debug/pprof/heap` — heap allocations
- `http://localhost:6060/debug/pprof/profile?seconds=30` — 30-second CPU profile

### Execution Trace

```bash
# Capture trace
go test -trace=trace.out ./pkg/...

# View in browser
go tool trace trace.out
```

The trace viewer shows goroutine scheduling, GC pauses, network I/O, and syscalls on a timeline. This is invaluable for diagnosing latency issues and concurrency problems.

### Flame Graphs

```bash
# Using pprof web UI (built-in since Go 1.11)
go tool pprof -http=:8080 cpu.prof
# Navigate to "Flame Graph" view in the web UI
```

---

## Fuzzing

Fuzzing finds edge cases you'd never think to test. Go 1.18+ has built-in fuzzing.

### Basic Fuzz Test

```go
func FuzzParseAge(f *testing.F) {
    // Seed corpus — known inputs to start from
    f.Add("25")
    f.Add("0")
    f.Add("-1")
    f.Add("abc")
    f.Add("")
    f.Add("999999999999999999999")

    f.Fuzz(func(t *testing.T, input string) {
        age, err := ParseAge(input)
        if err != nil {
            return // Errors are expected for many inputs
        }

        // Invariants that must always hold
        if age < 0 || age > 150 {
            t.Errorf("ParseAge(%q) = %d, out of valid range", input, age)
        }

        // Round-trip property: if we format the age back, parsing should give the same result
        formatted := strconv.Itoa(age)
        age2, err := ParseAge(formatted)
        if err != nil {
            t.Errorf("ParseAge(%q) succeeded but ParseAge(%q) failed: %v", input, formatted, err)
        }
        if age != age2 {
            t.Errorf("round-trip failed: %q -> %d -> %q -> %d", input, age, formatted, age2)
        }
    })
}
```

### Running Fuzzing

```bash
# Run for 30 seconds
go test -fuzz=FuzzParseAge -fuzztime=30s ./pkg/...

# Run for specific iterations
go test -fuzz=FuzzParseAge -fuzztime=10000x ./pkg/...

# Crashes are saved to testdata/fuzz/FuzzParseAge/
# They become regression tests automatically
```

### Crash Reproduction

When fuzzing finds a crash, it saves the input to `testdata/fuzz/FuzzParseAge/`:

```
testdata/
  fuzz/
    FuzzParseAge/
      corpus/               # Seed inputs
      1a2b3c4d5e6f...       # Crash-inducing input
```

Running `go test` (without `-fuzz`) automatically runs all saved crash cases as regression tests.

---

## Test Fixtures

### testdata Directory

Go ignores `testdata/` directories during build. Use them for test assets:

```
pkg/parser/
  parser.go
  parser_test.go
  testdata/
    valid_input.json
    invalid_input.json
    expected_output.json
```

```go
func TestParseConfig(t *testing.T) {
    input, err := os.ReadFile("testdata/valid_input.json")
    require.NoError(t, err)

    got, err := ParseConfig(input)
    require.NoError(t, err)

    expected, err := os.ReadFile("testdata/expected_output.json")
    require.NoError(t, err)

    gotJSON, _ := json.Marshal(got)
    assert.JSONEq(t, string(expected), string(gotJSON))
}
```

### Golden Files

Golden files store expected output. Update them with a flag:

```go
var update = flag.Bool("update", false, "update golden files")

func TestRender(t *testing.T) {
    got := Render(testInput)

    goldenFile := filepath.Join("testdata", t.Name()+".golden")

    if *update {
        os.WriteFile(goldenFile, []byte(got), 0644)
        return
    }

    expected, err := os.ReadFile(goldenFile)
    require.NoError(t, err)
    assert.Equal(t, string(expected), got)
}
```

```bash
# Update golden files
go test -run=TestRender -update ./pkg/...

# Normal test run compares against golden files
go test ./pkg/...
```

### Test Helpers

```go
func newTestUser(t *testing.T, overrides ...func(*User)) *User {
    t.Helper() // Marks this as a helper — errors report caller's line number

    user := &User{
        Name:  "Test User",
        Email: fmt.Sprintf("test-%d@example.com", time.Now().UnixNano()),
    }

    for _, override := range overrides {
        override(user)
    }

    return user
}

func setupTestServer(t *testing.T) (*httptest.Server, *http.Client) {
    t.Helper()

    mux := setupRoutes(testDeps)
    srv := httptest.NewServer(mux)
    t.Cleanup(srv.Close) // Automatically close when test finishes

    return srv, srv.Client()
}
```

### t.Cleanup

`t.Cleanup` registers functions to run after the test (and all subtests) complete. It's Go's version of `afterEach`:

```go
func setupDB(t *testing.T) *pgxpool.Pool {
    t.Helper()

    pool, err := pgxpool.New(ctx, connStr)
    require.NoError(t, err)

    t.Cleanup(func() {
        pool.Close() // Runs after test completes
    })

    return pool
}
```

Cleanup functions run in LIFO order (last registered runs first), similar to deferred functions.

---

## Build Tags for Test Categories

### Separating Unit and Integration Tests

```go
//go:build integration

package repository_test

import (
    "testing"
    // ...
)

func TestUserRepository_Integration(t *testing.T) {
    pool := setupTestDB(t)
    // ...
}
```

```bash
# Run only unit tests (default — skips files with build tags)
go test ./...

# Run integration tests
go test -tags=integration ./...

# Run all tests
go test -tags=integration ./...

# Alternative: use testing.Short()
go test -short ./...  # Skips tests that check testing.Short()
```

### Using testing.Short()

```go
func TestExpensiveOperation(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping expensive test in short mode")
    }
    // ... long-running test
}
```

---

## Test Coverage

### Generating Coverage

```bash
# Run tests with coverage
go test -cover ./...

# Generate coverage profile
go test -coverprofile=coverage.out ./...

# View in terminal
go tool cover -func=coverage.out

# View in browser (highlights covered/uncovered lines)
go tool cover -html=coverage.out

# Coverage for specific package
go test -coverprofile=coverage.out -coverpkg=./internal/... ./...
```

### Coverage Output

```
ok      myservice/internal/service    0.5s    coverage: 87.3% of statements
ok      myservice/internal/handler    0.3s    coverage: 72.1% of statements
ok      myservice/internal/repository 0.8s    coverage: 91.5% of statements
```

### CI Integration

```bash
# Fail if coverage drops below threshold
go test -coverprofile=coverage.out ./...
COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    echo "Coverage $COVERAGE% is below 80% threshold"
    exit 1
fi
```

---

## Interview Questions

### Conceptual

1. **Why does Go use table-driven tests instead of describe/it blocks like Jest or RSpec?**
   Table-driven tests leverage Go's type system — each test case is a struct with all inputs and expected outputs. Adding cases is just adding a struct literal. No DSL to learn, no nesting to get lost in. `t.Run` provides named subtests that show up in test output and can be run individually. The pattern also works naturally with `t.Parallel()` for concurrent subtests.

2. **Explain the difference between fakes, stubs, and mocks. Which does the Go community prefer?**
   Fakes have working implementations (in-memory DB), stubs return canned data, mocks verify interactions (was X called?). Go prefers fakes because they test behavior rather than implementation. If you mock that `Create` was called exactly once with specific args, your test breaks when you refactor internals. If you use a fake in-memory store, the test only breaks if behavior changes.

3. **How does Go's race detector work? When should you use it?**
   The race detector instruments memory accesses at compile time (`go test -race`). It detects when two goroutines access the same memory without synchronization and at least one is a write. Use it in CI always. It has ~10x CPU overhead and 5-10x memory overhead, so some teams skip it in hot-path benchmarks. It reports races deterministically once detected — it does not find all possible races on every run.

4. **What's the difference between `t.Error` and `t.Fatal`?**
   `t.Error` records a failure but continues the test. `t.Fatal` records a failure and stops the test immediately (calls `runtime.Goexit()`). Use `t.Fatal`/`require` for preconditions (setup failures), `t.Error`/`assert` for assertions that are independent. With testify: `require.NoError` = fatal, `assert.Equal` = error.

5. **How do build tags help organize tests? What other strategies exist?**
   Build tags (`//go:build integration`) let you categorize tests and run subsets. Files without the tag are included by default. Other strategies: `testing.Short()` for a quick/full split, `TestMain` for per-package setup/teardown, naming conventions (`TestUnit_*`, `TestIntegration_*`) with `-run` regex filtering.

### Coding Challenges

6. **Write a table-driven test for a URL parser that handles edge cases (empty string, missing scheme, unicode, query parameters, fragments).**

7. **Implement a fake HTTP client that records all requests and returns configurable responses — test a service that makes external API calls.**

8. **Write a benchmark comparing three JSON serialization approaches (encoding/json, json-iterator, easyjson) and explain how to interpret the results.**

9. **Create a fuzz test for a Markdown parser that checks for panics and validates output invariants.**

### Architecture

10. **Your team has 200 tests that each start a PostgreSQL testcontainer, making the test suite take 20 minutes. How do you optimize this?**
    Use a shared container per package with `TestMain`. Start one container in `TestMain(m *testing.M)`, run all tests, then tear it down. Use transactions for test isolation — start a transaction before each test, rollback after. This gives you a fresh database state per test without recreating the container. Consider `t.Parallel()` for independent tests.

11. **How do you test a function that uses `time.Now()`?**
    Accept a `func() time.Time` parameter (or a Clock interface) instead of calling `time.Now()` directly. In production, pass `time.Now`. In tests, pass a function that returns a fixed time. Alternatively, use a package-level variable `var now = time.Now` and replace it in tests. The interface approach is cleaner and more Go-idiomatic.

12. **When should you use real databases in tests vs mocks?**
    Use real databases (testcontainers) for repository/data access layer tests — they catch SQL errors, constraint violations, and driver quirks that mocks miss. Use mocks/fakes for service layer tests where you want speed and isolation from database concerns. Use mocks for handler tests to keep them fast and focused on HTTP concerns. The test pyramid applies: many fast unit tests with mocks at the top, fewer slow integration tests with real databases at the bottom.
