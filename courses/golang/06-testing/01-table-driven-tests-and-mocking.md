# 01 – Table-Driven Tests and Mocking

Go's testing story is one of its strongest selling points, and it works completely differently from TypeScript. There is no Jest, no Mocha, no Vitest. Go ships a `testing` package and a `go test` command that handle everything — no configuration files, no test runners to install, no assertion library debates.

The cultural difference is equally important: Go developers tend to write more integration tests and fewer mocks than the TypeScript/Java world. The tooling supports this — testcontainers, httptest, and the race detector are all first-class.

---

## 1. Table-Driven Tests

This is THE Go testing pattern. You will see it in the standard library, in every open-source project, and in every interview.

### Basic Structure

```go
func TestParseAge(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    int
        wantErr bool
    }{
        {name: "valid age",    input: "25",  want: 25},
        {name: "zero",         input: "0",   want: 0},
        {name: "negative",     input: "-1",  wantErr: true},
        {name: "not a number", input: "abc", wantErr: true},
        {name: "empty string", input: "",    wantErr: true},
        {name: "too large",    input: "200", wantErr: true},
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

### Generic Table-Driven Template

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
                if err == nil {
                    t.Errorf("expected error, got nil")
                }
                return
            }
            if err != nil {
                t.Fatalf("unexpected error: %v", err)
            }
            if got != tt.want {
                t.Errorf("got %d, want %d", got, tt.want)
            }
        })
    }
}
```

### Why This Pattern Works

1. Adding test cases is trivial — just add another struct to the slice.
2. `t.Run` creates subtests — each case runs independently, shows up named in output, and can be run individually with `go test -run TestParseAge/negative`.
3. Failures are clear — each test case has a descriptive name.
4. No assertion library required (though `testify/assert` is common for reducing boilerplate).

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

`t.Parallel()` must be the first call in a subtest. Each parallel test case must use its own data — do not share mutable state.

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

`require` = `t.Fatal` (stops immediately). `assert` = `t.Error` (records and continues). Use `require` for preconditions, `assert` for independent assertions.

---

## 2. Mocking

### Interfaces as Contracts

In TypeScript, you might mock modules with `jest.mock()`. In Go, mocking is built on interfaces. If your code depends on interfaces, mocking is trivial.

```go
// The interface (contract)
type UserRepository interface {
    GetByID(ctx context.Context, id int64) (*User, error)
    Create(ctx context.Context, user *User) error
}

// Production implementation
type postgresUserRepo struct { pool *pgxpool.Pool }

// Fake implementation for tests
type fakeUserRepo struct {
    users map[int64]*User
    err   error // Force errors in tests
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
|------|---------|---------|
| **Fake** | Working implementation with shortcuts | In-memory database, fake email sender |
| **Stub** | Returns canned responses | Always returns the same user |
| **Mock** | Verifies interactions | Assert `Create` was called with specific args |

**Go community preference**: Fakes > Stubs > Mocks. Fakes test behavior, mocks test implementation details. If you mock that `Create` was called exactly once, your test breaks when you refactor internals even if behavior is unchanged.

### When to Use Generated Mocks

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

## 3. Dependency Injection for Testability

Constructor injection — explicit, no reflection, no magic:

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

// In tests: inject fakes
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

Wire adds compile-time safety to dependency graphs but introduces code generation complexity. For services with fewer than ~20 dependencies, manual wiring in `main()` is simpler and just as clear.

---

## 4. Test Helpers and Fixtures

### Test Helper Pattern

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

func mustSetup(t *testing.T) *Resource {
    t.Helper()
    r, err := NewResource()
    require.NoError(t, err)
    t.Cleanup(func() { r.Close() })
    return r
}
```

Without `t.Helper()`, error messages point to the helper function, not the test that called it.

### t.Cleanup

`t.Cleanup` registers functions to run after the test (and all subtests) complete. It is Go's version of `afterEach`, and runs in LIFO order (last registered runs first), like `defer`:

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

func TestResourceLifecycle(t *testing.T) {
    db := openDB(t)
    t.Cleanup(func() {
        t.Log("closing database") // runs 3rd
        db.Close()
    })

    cache := openCache(t)
    t.Cleanup(func() {
        t.Log("closing cache") // runs 2nd
        cache.Close()
    })

    server := startServer(t, db, cache)
    t.Cleanup(func() {
        t.Log("stopping server") // runs 1st (LIFO)
        server.Close()
    })
}
```

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
# Update golden files when output intentionally changes
go test -run=TestRender -update ./pkg/...

# Normal test run compares against golden files
go test ./pkg/...
```

---

## 5. TestMain for Package-Level Setup

```go
func TestMain(m *testing.M) {
    // Setup: runs before ALL tests in this package
    flag.Parse()
    setup()

    // Run all tests
    code := m.Run()

    // Teardown: runs after ALL tests complete
    teardown()

    os.Exit(code)
}
```

Shared container per package (fast integration tests):

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
    runMigrations(connStr)

    code := m.Run()

    testPool.Close()
    container.Terminate(ctx)
    os.Exit(code)
}

// Each test uses transactions for isolation — no container restart needed
func withTestTx(t *testing.T) pgx.Tx {
    t.Helper()
    tx, err := testPool.Begin(context.Background())
    require.NoError(t, err)
    t.Cleanup(func() {
        tx.Rollback(context.Background()) // Always rollback
    })
    return tx
}
```

---

## 6. Build Tags for Test Categories

```go
//go:build integration

package repository_test

// This file only compiles with: go test -tags=integration
func TestUserRepository_Integration(t *testing.T) {
    pool := setupTestDB(t)
    // ...
}
```

```go
//go:build !integration

package mypackage_test
// This file only compiles WITHOUT the integration tag
```

```bash
# Run only unit tests (default — skips files with build tags)
go test ./...

# Run integration tests
go test -tags=integration ./...

# Alternative: use testing.Short()
go test -short ./...  # Skips tests that call t.Skip when testing.Short() is true
```

Using `testing.Short()`:

```go
func TestExpensiveOperation(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping expensive test in short mode")
    }
    // ... long-running test
}
```

---

## 7. Key Gotchas

| Gotcha | Explanation |
|--------|-------------|
| `t.Parallel()` must be first | Any code before `t.Parallel()` runs sequentially |
| `t.Fatal`/`require` stops the test | `t.Error`/`assert` records failure and continues |
| `t.Helper()` fixes error line numbers | Without it, errors point to the helper, not the caller |
| `t.Cleanup` runs LIFO like defer | Last registered cleanup runs first |
| `-race` adds ~10x CPU overhead | Skip it for benchmark runs |
| `httptest.NewRecorder` is lenient | Does NOT enforce `WriteHeader` ordering like a real client |
| Fuzzing crashes go to `testdata/fuzz/` | They become regression tests automatically |
| `b.ResetTimer()` excludes setup | Call it after setup code to exclude from timing |
| `testcontainers` requires Docker | Guard with `testing.Short()` or build tags in CI |
