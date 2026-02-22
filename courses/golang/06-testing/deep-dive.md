# Module 06 Deep Dive: Testing in Go

## Property-Based Testing with rapid

Property-based testing generates random inputs and checks that invariants hold. Think of it as structured fuzzing with assertions.

### Setup

```go
import "pgregory.net/rapid"
```

### Basic Property Test

```go
func TestSortProperties(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        // Generate a random slice of ints
        input := rapid.SliceOf(rapid.Int()).Draw(t, "input")

        // Sort it
        result := make([]int, len(input))
        copy(result, input)
        sort.Ints(result)

        // Property 1: Output length equals input length
        if len(result) != len(input) {
            t.Fatalf("length changed: %d -> %d", len(input), len(result))
        }

        // Property 2: Output is sorted
        for i := 1; i < len(result); i++ {
            if result[i] < result[i-1] {
                t.Fatalf("not sorted at index %d: %d > %d", i, result[i-1], result[i])
            }
        }

        // Property 3: Output is a permutation of input (same elements)
        inputCopy := make([]int, len(input))
        copy(inputCopy, input)
        sort.Ints(inputCopy)
        if !slices.Equal(result, inputCopy) {
            t.Fatalf("not a permutation")
        }
    })
}
```

### Testing Serialization Round-Trips

```go
func TestUserJSONRoundTrip(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        // Generate random user
        user := User{
            ID:    rapid.Int64Range(1, 1000000).Draw(t, "id"),
            Name:  rapid.StringMatching(`[a-zA-Z ]{1,100}`).Draw(t, "name"),
            Email: rapid.StringMatching(`[a-z]{1,20}@[a-z]{1,10}\.[a-z]{2,4}`).Draw(t, "email"),
        }

        // Serialize
        data, err := json.Marshal(user)
        if err != nil {
            t.Fatalf("marshal failed: %v", err)
        }

        // Deserialize
        var decoded User
        if err := json.Unmarshal(data, &decoded); err != nil {
            t.Fatalf("unmarshal failed: %v", err)
        }

        // Property: round-trip preserves data
        if user != decoded {
            t.Fatalf("round-trip failed:\n  original: %+v\n  decoded:  %+v", user, decoded)
        }
    })
}
```

### Stateful Property Testing

Test a sequence of operations against a model:

```go
func TestCacheStateful(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        cache := NewLRUCache(10)
        model := make(map[string]string) // Simple map as the "correct" model

        // Generate random operations
        numOps := rapid.IntRange(1, 100).Draw(t, "numOps")
        for i := 0; i < numOps; i++ {
            key := rapid.StringMatching(`[a-z]{1,5}`).Draw(t, fmt.Sprintf("key_%d", i))
            op := rapid.IntRange(0, 2).Draw(t, fmt.Sprintf("op_%d", i))

            switch op {
            case 0: // Set
                value := rapid.String().Draw(t, fmt.Sprintf("val_%d", i))
                cache.Set(key, value)
                model[key] = value

            case 1: // Get
                got, ok := cache.Get(key)
                expected, modelOk := model[key]
                // Note: cache might have evicted, so we can only check one direction
                if ok && got != expected {
                    t.Fatalf("Get(%q) = %q, model has %q", key, got, expected)
                }
                if modelOk && !ok {
                    // LRU eviction is acceptable — skip
                }

            case 2: // Delete
                cache.Delete(key)
                delete(model, key)
            }
        }
    })
}
```

---

## Testing Concurrent Code

### Race Detector

```bash
# Always run tests with -race in CI
go test -race ./...

# Also works with go run and go build
go run -race main.go
go build -race -o myapp
```

### Example: Finding a Race

```go
// Buggy code
type Counter struct {
    n int
}

func (c *Counter) Increment() {
    c.n++ // DATA RACE: unsynchronized read-modify-write
}

func (c *Counter) Value() int {
    return c.n // DATA RACE: unsynchronized read
}

// Test that detects the race
func TestCounter_Concurrent(t *testing.T) {
    c := &Counter{}

    var wg sync.WaitGroup
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            c.Increment()
        }()
    }
    wg.Wait()

    // With -race flag, this test will FAIL with a race detection report
    // even if the final value happens to be correct
    if c.Value() != 1000 {
        t.Errorf("got %d, want 1000", c.Value())
    }
}
```

### Stress Testing

```go
func TestMap_ConcurrentAccess(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping stress test in short mode")
    }

    m := NewSafeMap()
    const goroutines = 100
    const iterations = 10000

    var wg sync.WaitGroup
    wg.Add(goroutines * 3)

    // Writers
    for i := 0; i < goroutines; i++ {
        go func(id int) {
            defer wg.Done()
            for j := 0; j < iterations; j++ {
                key := fmt.Sprintf("key-%d-%d", id, j%100)
                m.Set(key, j)
            }
        }(i)
    }

    // Readers
    for i := 0; i < goroutines; i++ {
        go func(id int) {
            defer wg.Done()
            for j := 0; j < iterations; j++ {
                key := fmt.Sprintf("key-%d-%d", id, j%100)
                m.Get(key)
            }
        }(i)
    }

    // Deleters
    for i := 0; i < goroutines; i++ {
        go func(id int) {
            defer wg.Done()
            for j := 0; j < iterations; j++ {
                key := fmt.Sprintf("key-%d-%d", id, j%100)
                m.Delete(key)
            }
        }(i)
    }

    wg.Wait()
}
```

### Deterministic Testing with Channels

```go
// Instead of time.Sleep or sync.WaitGroup for ordering,
// use channels to coordinate goroutines deterministically.

func TestProducerConsumer(t *testing.T) {
    produced := make(chan string, 10)
    consumed := make(chan string, 10)

    // Producer
    go func() {
        for i := 0; i < 5; i++ {
            item := fmt.Sprintf("item-%d", i)
            produced <- item
        }
        close(produced)
    }()

    // Consumer
    go func() {
        for item := range produced {
            consumed <- "processed-" + item
        }
        close(consumed)
    }()

    // Collect results deterministically
    var results []string
    for item := range consumed {
        results = append(results, item)
    }

    assert.Equal(t, 5, len(results))
    assert.Contains(t, results, "processed-item-0")
    assert.Contains(t, results, "processed-item-4")
}
```

---

## Testing with Dependency Injection

### Manual DI (Preferred in Go)

```go
// Constructor injection — the Go way
type OrderService struct {
    orders   OrderRepository
    users    UserRepository
    payments PaymentGateway
    events   EventPublisher
    logger   *slog.Logger
}

func NewOrderService(
    orders OrderRepository,
    users UserRepository,
    payments PaymentGateway,
    events EventPublisher,
    logger *slog.Logger,
) *OrderService {
    return &OrderService{
        orders:   orders,
        users:    users,
        payments: payments,
        events:   events,
        logger:   logger,
    }
}

// In tests: inject fakes/mocks
func TestOrderService_PlaceOrder(t *testing.T) {
    fakeOrders := &fakeOrderRepo{}
    fakeUsers := &fakeUserRepo{
        users: map[int64]*User{1: {ID: 1, Name: "Alice"}},
    }
    fakePayments := &fakePaymentGateway{shouldSucceed: true}
    fakeEvents := &fakeEventPublisher{}

    svc := NewOrderService(fakeOrders, fakeUsers, fakePayments, fakeEvents, slog.Default())

    order, err := svc.PlaceOrder(ctx, &PlaceOrderInput{
        UserID: 1,
        Items:  []OrderItem{{ProductID: 100, Quantity: 2}},
    })

    require.NoError(t, err)
    assert.NotZero(t, order.ID)
    assert.Len(t, fakeEvents.published, 1) // Verify event was published
}
```

### Wire for Compile-Time DI

Google's Wire generates dependency injection code at compile time:

```go
// wire.go (build input)
//go:build wireinject

package main

import "github.com/google/wire"

func InitializeApp(cfg Config) (*App, error) {
    wire.Build(
        NewDatabase,
        NewUserRepository,
        NewUserService,
        NewUserHandler,
        NewRouter,
        NewApp,
    )
    return nil, nil // Wire replaces this
}
```

```go
// wire_gen.go (generated output)
func InitializeApp(cfg Config) (*App, error) {
    db, err := NewDatabase(cfg)
    if err != nil {
        return nil, err
    }
    userRepo := NewUserRepository(db)
    userSvc := NewUserService(userRepo)
    userHandler := NewUserHandler(userSvc)
    router := NewRouter(userHandler)
    app := NewApp(router, db)
    return app, nil
}
```

**Trade-off**: Wire adds compile-time safety to dependency graphs but introduces code generation complexity. For services with fewer than ~20 dependencies, manual wiring in `main()` is simpler and just as clear.

---

## Acceptance Testing Patterns

### End-to-End with a Test Server

```go
func TestAcceptance_UserLifecycle(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping acceptance test")
    }

    // Stand up the entire application
    app := setupTestApp(t) // Start containers, migrations, server
    client := app.HTTPClient()
    baseURL := app.BaseURL()

    t.Run("register new user", func(t *testing.T) {
        resp, err := client.Post(baseURL+"/api/auth/register",
            "application/json",
            strings.NewReader(`{"email":"test@example.com","password":"secret123"}`))
        require.NoError(t, err)
        defer resp.Body.Close()
        assert.Equal(t, http.StatusCreated, resp.StatusCode)
    })

    t.Run("login", func(t *testing.T) {
        resp, err := client.Post(baseURL+"/api/auth/login",
            "application/json",
            strings.NewReader(`{"email":"test@example.com","password":"secret123"}`))
        require.NoError(t, err)
        defer resp.Body.Close()
        assert.Equal(t, http.StatusOK, resp.StatusCode)

        var body map[string]string
        json.NewDecoder(resp.Body).Decode(&body)
        assert.NotEmpty(t, body["token"])
    })

    t.Run("access protected resource", func(t *testing.T) {
        req, _ := http.NewRequest("GET", baseURL+"/api/users/me", nil)
        req.Header.Set("Authorization", "Bearer "+token)

        resp, err := client.Do(req)
        require.NoError(t, err)
        defer resp.Body.Close()
        assert.Equal(t, http.StatusOK, resp.StatusCode)
    })
}
```

### Test App Helper

```go
type TestApp struct {
    server *httptest.Server
    db     *pgxpool.Pool
    redis  *redis.Client
    t      *testing.T
}

func setupTestApp(t *testing.T) *TestApp {
    t.Helper()

    db := setupTestDB(t)
    rdb := setupTestRedis(t)

    // Build real application with test infrastructure
    app := buildApp(db, rdb)
    srv := httptest.NewServer(app.Handler)
    t.Cleanup(srv.Close)

    return &TestApp{server: srv, db: db, redis: rdb, t: t}
}

func (a *TestApp) BaseURL() string  { return a.server.URL }
func (a *TestApp) HTTPClient() *http.Client { return a.server.Client() }

// Helper to seed test data
func (a *TestApp) SeedUser(t *testing.T, email, password string) *User {
    t.Helper()
    // Insert directly into database, bypassing API
    var user User
    err := a.db.QueryRow(context.Background(),
        `INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING *`,
        email, hashPassword(password)).Scan(&user)
    require.NoError(t, err)
    return &user
}
```

---

## Testing CLI Applications

### Testing cobra Commands

```go
func TestRootCmd(t *testing.T) {
    tests := []struct {
        name     string
        args     []string
        wantOut  string
        wantErr  bool
    }{
        {
            name:    "version flag",
            args:    []string{"--version"},
            wantOut: "myapp v1.0.0",
        },
        {
            name:    "help flag",
            args:    []string{"--help"},
            wantOut: "Usage:",
        },
        {
            name:    "unknown command",
            args:    []string{"nonexistent"},
            wantErr: true,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Capture stdout/stderr
            out := &bytes.Buffer{}
            errOut := &bytes.Buffer{}

            cmd := NewRootCmd()
            cmd.SetOut(out)
            cmd.SetErr(errOut)
            cmd.SetArgs(tt.args)

            err := cmd.Execute()

            if tt.wantErr {
                assert.Error(t, err)
                return
            }

            assert.NoError(t, err)
            assert.Contains(t, out.String(), tt.wantOut)
        })
    }
}
```

### Testing stdin/stdout

```go
func TestInteractiveInput(t *testing.T) {
    input := strings.NewReader("Alice\nalice@example.com\n")
    output := &bytes.Buffer{}

    app := &App{
        stdin:  input,
        stdout: output,
    }

    err := app.RunPrompt()
    require.NoError(t, err)

    assert.Contains(t, output.String(), "Hello, Alice!")
}
```

---

## Testing with Real Databases vs Mocks

### Trade-offs

| Aspect | Real Database (testcontainers) | Mocks/Fakes |
|---|---|---|
| **Speed** | Slow (container startup: 2-10s) | Fast (microseconds) |
| **Fidelity** | High — catches real SQL errors, constraints | Low — can't catch SQL bugs |
| **Setup complexity** | Moderate (Docker required) | Low |
| **Maintenance** | Schema changes require migration updates | Interface changes require mock updates |
| **CI requirements** | Docker-in-Docker or privileged containers | None |
| **What they test** | Actual data access behavior | Business logic in isolation |

### Recommended Strategy

```
Layer               Test Approach
─────────────────────────────────────────
Handler/Transport   httptest + mock services (fast)
Service/Business    Fake repositories (fast, behavior-focused)
Repository/Data     Real database via testcontainers (slow, high fidelity)
Integration/E2E     Full stack with testcontainers (slowest, highest fidelity)
```

### Shared Container Pattern

```go
// testmain_test.go — one container per package
var testPool *pgxpool.Pool

func TestMain(m *testing.M) {
    ctx := context.Background()

    container, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
    )
    if err != nil {
        log.Fatalf("start postgres: %v", err)
    }

    connStr, _ := container.ConnectionString(ctx, "sslmode=disable")
    testPool, _ = pgxpool.New(ctx, connStr)

    // Run migrations once
    runMigrations(connStr)

    // Run all tests
    code := m.Run()

    // Cleanup
    testPool.Close()
    container.Terminate(ctx)
    os.Exit(code)
}

// Each test uses transactions for isolation
func withTestTx(t *testing.T) pgx.Tx {
    t.Helper()
    tx, err := testPool.Begin(context.Background())
    require.NoError(t, err)
    t.Cleanup(func() {
        tx.Rollback(context.Background()) // Always rollback — test isolation
    })
    return tx
}
```

---

## Mutation Testing

Mutation testing modifies your source code and checks if tests catch the change. If a mutation survives (tests still pass), your tests have a gap.

### Using go-mutesting

```bash
go install github.com/zimmski/go-mutesting/cmd/go-mutesting@latest

go-mutesting ./internal/service/...
```

Example mutations:
- Replace `>` with `>=`
- Replace `&&` with `||`
- Remove function calls
- Change return values

### Interpreting Results

```
Mutations:     150
Killed:        130    (86.7%)
Survived:       15    (10.0%)
Not covered:     5    ( 3.3%)
```

Survived mutations indicate test gaps. A mutation like changing `amount > 0` to `amount >= 0` surviving means you don't have a test for `amount == 0`.

---

## Custom Test Runners with TestMain

```go
func TestMain(m *testing.M) {
    // Setup: runs before ALL tests in this package
    fmt.Println("Setting up test environment...")

    // Parse custom flags
    flag.Parse()

    // Global setup (database connections, test data, etc.)
    setup()

    // Run all tests
    code := m.Run()

    // Teardown: runs after ALL tests complete
    teardown()

    os.Exit(code)
}
```

### Per-Test Cleanup with t.Cleanup Stack

```go
func TestResourceLifecycle(t *testing.T) {
    db := openDB(t)
    t.Cleanup(func() {
        t.Log("closing database")
        db.Close()
    })

    cache := openCache(t)
    t.Cleanup(func() {
        t.Log("closing cache")
        cache.Close()
    })

    server := startServer(t, db, cache)
    t.Cleanup(func() {
        t.Log("stopping server")
        server.Close()
    })

    // Cleanup runs in reverse order:
    // 1. stopping server
    // 2. closing cache
    // 3. closing database
}
```

### Test Fixtures with TestMain

```go
func TestMain(m *testing.M) {
    // Create shared expensive resources
    pool := mustSetupDB()
    redisClient := mustSetupRedis()

    // Make available to tests via package-level vars
    testPool = pool
    testRedis = redisClient

    code := m.Run()

    // Cleanup
    pool.Close()
    redisClient.Close()
    os.Exit(code)
}
```

This pattern avoids spinning up a container for every test. Combined with transaction-based isolation, it keeps integration tests fast while maintaining full fidelity.
