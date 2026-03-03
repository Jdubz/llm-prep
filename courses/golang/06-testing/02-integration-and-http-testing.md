# 02 – Integration and HTTP Testing

This file assumes you have read `01-table-driven-tests-and-mocking.md`. It covers the `httptest` package, testcontainers-go (PostgreSQL, Redis, Kafka), acceptance testing, CLI testing, and the recommended testing strategy per layer.

---

## 1. httptest Package

### Testing Handlers with ResponseRecorder

`httptest.NewRecorder` captures the response written by a handler:

```go
func TestGetUserHandler(t *testing.T) {
    // Setup handler with a fake service
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
```

### POST with Body

```go
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

The middleware testing pattern wraps a trivial `http.HandlerFunc` with the middleware under test. This isolates the middleware's behavior from handler logic.

### Integration Testing with httptest.NewServer

`httptest.NewServer` starts a real HTTP server on a local port and gives you a real `*http.Client` to test against — including all middleware:

```go
func TestAPIIntegration(t *testing.T) {
    // Create a full server with all middleware and routing
    mux := setupRoutes(testDeps)
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

---

## 2. testcontainers-go: Real Infrastructure in Tests

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

## 3. Acceptance Testing

### End-to-End with a Test Server

```go
func TestAcceptance_UserLifecycle(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping acceptance test")
    }

    // Stand up the entire application
    app := setupTestApp(t)
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

func (a *TestApp) BaseURL() string        { return a.server.URL }
func (a *TestApp) HTTPClient() *http.Client { return a.server.Client() }

// Helper to seed test data directly into DB (bypasses API)
func (a *TestApp) SeedUser(t *testing.T, email, password string) *User {
    t.Helper()
    var user User
    err := a.db.QueryRow(context.Background(),
        `INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING *`,
        email, hashPassword(password)).Scan(&user)
    require.NoError(t, err)
    return &user
}
```

---

## 4. Testing CLI Applications

### Testing cobra Commands

```go
func TestRootCmd(t *testing.T) {
    tests := []struct {
        name    string
        args    []string
        wantOut string
        wantErr bool
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

## 5. Testing Real Databases vs Mocks

| Aspect | Real Database (testcontainers) | Mocks/Fakes |
|--------|-------------------------------|-------------|
| Speed | Slow (container startup: 2–10s) | Fast (microseconds) |
| Fidelity | High — catches real SQL errors, constraints | Low — cannot catch SQL bugs |
| Setup complexity | Moderate (Docker required) | Low |
| Maintenance | Schema changes require migration updates | Interface changes require mock updates |
| CI requirements | Docker-in-Docker or privileged containers | None |
| What they test | Actual data access behavior | Business logic in isolation |

### Recommended Strategy Per Layer

```
Layer                  Test Approach
──────────────────────────────────────────────────────
Handler/Transport      httptest + mock services (fast)
Service/Business       Fake repositories (fast, behavior-focused)
Repository/Data        Real database via testcontainers (slow, high fidelity)
Integration/E2E        Full stack with testcontainers (slowest, highest fidelity)
```

---

## 6. Test Coverage

### Generating Coverage

```bash
# Run tests with coverage
go test -cover ./...

# Generate coverage profile
go test -coverprofile=coverage.out ./...

# View in terminal (per-function breakdown)
go tool cover -func=coverage.out

# View in browser (highlights covered/uncovered lines)
go tool cover -html=coverage.out

# Save HTML to file
go tool cover -html=coverage.out -o cover.html

# Coverage for specific packages
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
go test -coverprofile=coverage.out ./...
COVERAGE=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | sed 's/%//')
if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    echo "Coverage $COVERAGE% is below 80% threshold"
    exit 1
fi
```
