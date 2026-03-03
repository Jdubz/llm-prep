# 02 – Testing and I/O

This file assumes you have read `01-http-and-json.md`. It covers the testing package, table-driven tests, benchmarks, fuzzing, file I/O, bufio, and os file operations.

---

## 1. testing: Table-Driven Tests and Beyond

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

### Table-Driven Test Template (with error case)

```go
func TestFunction(t *testing.T) {
    tests := []struct {
        name    string
        input   string
        want    int
        wantErr bool
    }{
        {"valid input", "hello", 5, false},
        {"empty input", "", 0, false},
        {"invalid input", "\x00", 0, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := Function(tt.input)
            if (err != nil) != tt.wantErr {
                t.Fatalf("error = %v, wantErr %v", err, tt.wantErr)
            }
            if got != tt.want {
                t.Errorf("got %d, want %d", got, tt.want)
            }
        })
    }
}
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

### HTTP Handler Test Template

```go
func TestGetUser(t *testing.T) {
    req := httptest.NewRequest("GET", "/users/123", nil)
    req.SetPathValue("id", "123") // Go 1.22+

    rec := httptest.NewRecorder()
    handleGetUser(rec, req)

    if rec.Code != http.StatusOK {
        t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
    }

    var user User
    json.NewDecoder(rec.Body).Decode(&user)
    if user.ID != "123" {
        t.Errorf("user.ID = %q, want %q", user.ID, "123")
    }
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

### Benchmark Template (with setup)

```go
func BenchmarkFunction(b *testing.B) {
    input := setupInput()
    b.ResetTimer() // exclude setup from timing

    for i := 0; i < b.N; i++ {
        Function(input)
    }
}

// Run: go test -bench=BenchmarkFunction -benchmem ./...
```

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

### Test Commands Reference

```bash
go test ./...                         # run all tests
go test -v ./...                      # verbose output
go test -run TestName ./...           # run specific test
go test -run TestName/subtest ./...   # run specific subtest
go test -count=1 ./...                # disable test caching
go test -race ./...                   # enable race detector
go test -cover ./...                  # show coverage percentage
go test -coverprofile=cover.out ./... # write coverage file
go tool cover -html=cover.out         # view coverage in browser
go test -bench=. ./...                # run benchmarks
go test -bench=. -benchmem ./...      # benchmarks with alloc info
go test -fuzz=FuzzName -fuzztime=30s  # run fuzzer for 30s
go test -shuffle=on ./...             # randomize test order
```

---

## 2. bufio: Buffered I/O

`bufio` wraps a `Reader` or `Writer` and buffers reads/writes to reduce system call overhead.

### bufio.Scanner: Line-by-Line Reading

```go
file, err := os.Open("data.txt")
if err != nil {
    return err
}
defer file.Close()

scanner := bufio.NewScanner(file)
for scanner.Scan() {
    line := scanner.Text()
    fmt.Println(line)
}
if err := scanner.Err(); err != nil {
    return err
}
```

The default scanner splits on newlines. You can customize with `scanner.Split()`:

```go
scanner.Split(bufio.ScanWords)   // split on whitespace
scanner.Split(bufio.ScanBytes)   // one byte at a time
scanner.Split(bufio.ScanRunes)   // one UTF-8 rune at a time
```

For large lines (>64KB default), increase the buffer:

```go
scanner := bufio.NewScanner(file)
scanner.Buffer(make([]byte, 1024*1024), 1024*1024) // 1MB max line
```

### bufio.Reader

```go
reader := bufio.NewReader(file)

// Read a line
line, err := reader.ReadString('\n') // includes the delimiter

// Read a byte
b, err := reader.ReadByte()

// Peek without consuming
peek, err := reader.Peek(4) // look at next 4 bytes without advancing
```

### bufio.Writer

```go
writer := bufio.NewWriter(file)

writer.WriteString("hello\n")
writer.WriteByte('\n')

// IMPORTANT: always flush when done
if err := writer.Flush(); err != nil {
    return err
}
```

---

## 3. os: File Operations and Environment

### File Read/Write

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

### Environment Variables

```go
// Read
port := os.Getenv("PORT")

// Read with default
port := os.Getenv("PORT")
if port == "" {
    port = "8080"
}

// Set (for the current process)
os.Setenv("DEBUG", "true")

// Read all
for _, env := range os.Environ() {
    fmt.Println(env) // "KEY=VALUE"
}
```

---

## 4. database/sql

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

### database/sql Template

```go
import (
    "database/sql"
    _ "github.com/lib/pq"
)

// Open and configure
db, err := sql.Open("postgres", connStr)
if err != nil { log.Fatal(err) }
defer db.Close()

db.SetMaxOpenConns(25)
db.SetMaxIdleConns(10)
db.SetConnMaxLifetime(5 * time.Minute)

// Single row
var name string
err := db.QueryRowContext(ctx, "SELECT name FROM users WHERE id = $1", id).Scan(&name)
if errors.Is(err, sql.ErrNoRows) { /* not found */ }

// Multiple rows
rows, err := db.QueryContext(ctx, "SELECT id, name FROM users WHERE active = $1", true)
if err != nil { return err }
defer rows.Close()
for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Name); err != nil { return err }
    users = append(users, u)
}
if err := rows.Err(); err != nil { return err }

// Exec (INSERT/UPDATE/DELETE)
result, err := db.ExecContext(ctx, "DELETE FROM users WHERE id = $1", id)
affected, _ := result.RowsAffected()

// Transaction
tx, err := db.BeginTx(ctx, nil)
if err != nil { return err }
defer tx.Rollback()
tx.ExecContext(ctx, "UPDATE ...", ...)
tx.ExecContext(ctx, "INSERT ...", ...)
return tx.Commit()
```

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
row = stmt.QueryRowContext(ctx, "bob@example.com")
```

Prepared statements are useful when executing the same query many times with different parameters.

---

## Related Reading

- **Testing in depth** — [Module 06: Table-Driven Tests and Mocking](../06-testing/01-table-driven-tests-and-mocking.md) expands on the `testing` package basics from section 1 with table-driven patterns, mocking strategies, and test helpers
- **database/sql vs pgx** — [Module 05: Database Drivers and ORMs](../05-data-storage/01-database-drivers-and-orms.md), section 2 (pgx) explains why many Go projects use pgx directly instead of `database/sql`, and when the stdlib interface still makes sense
- **io composition in HTTP** — [Module 04: Request Handling and Validation](../04-http-services/02-request-handling-and-validation.md) shows `io.Reader` used for JSON body decoding and `io.Writer` used for response encoding in HTTP handlers
- **File embedding** — [Module 03: Time, Logging, and Additional Stdlib](03-time-logging-and-additional-stdlib.md), section 7 (embed) shows how to bundle files into binaries using `embed.FS` which implements `fs.FS`
- **Benchmarking IO operations** — [Module 06: Benchmarking, Profiling, and Advanced Testing](../06-testing/03-benchmarking-profiling-and-advanced-testing.md), section 1 covers how to benchmark the IO patterns from this file
