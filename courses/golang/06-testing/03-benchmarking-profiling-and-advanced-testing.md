# 03 – Benchmarking, Profiling, and Advanced Testing

This file assumes you have read `01-table-driven-tests-and-mocking.md` and `02-integration-and-http-testing.md`. It covers benchmarking, profiling, fuzzing, property-based testing, concurrent code testing, mutation testing, and the complete `go test` flag reference.

---

## 1. Benchmarking

### Basic Benchmark

```go
func BenchmarkJSONMarshal(b *testing.B) {
    user := &User{ID: 1, Name: "Alice", Email: "alice@example.com"}

    b.ResetTimer() // Reset after setup — exclude setup from timing
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

### Benchmark Template

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
```

`b.N` is adjusted automatically by the testing framework until the benchmark runs long enough for a statistically stable measurement.

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
                tmp := make([]int, len(data))
                copy(tmp, data)
                sort.Ints(tmp)
            }
        })
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
|-------|---------|
| `-8` | GOMAXPROCS (number of CPUs used) |
| `5000000` | Number of iterations |
| `234 ns/op` | Nanoseconds per operation |
| `128 B/op` | Bytes allocated per operation |
| `2 allocs/op` | Heap allocations per operation |

Key rules:
- Lower `ns/op` = faster
- Lower `B/op` and `allocs/op` = less GC pressure
- `b.ResetTimer()` excludes setup from measurements
- `b.ReportAllocs()` shows memory stats (same as `-benchmem`)

---

## 2. Profiling

### CPU Profile

```bash
# Generate CPU profile during benchmark
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

// In main(), run on a separate port (never expose publicly):
go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

Access profiles at:
- `http://localhost:6060/debug/pprof/` — index
- `http://localhost:6060/debug/pprof/goroutine` — goroutine stacks
- `http://localhost:6060/debug/pprof/heap` — heap allocations
- `http://localhost:6060/debug/pprof/profile?seconds=30` — 30-second CPU profile

```bash
# Live production profiling
go tool pprof http://localhost:6060/debug/pprof/heap
go tool pprof http://localhost:6060/debug/pprof/goroutine
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Web-based pprof UI (built-in since Go 1.11)
go tool pprof -http=:8080 cpu.prof
# Navigate to "Flame Graph" view in the web UI
```

### Execution Trace

```bash
# Capture trace
go test -trace=trace.out ./pkg/...

# View in browser
go tool trace trace.out
```

The trace viewer shows goroutine scheduling, GC pauses, network I/O, and syscalls on a timeline. Invaluable for diagnosing latency issues and concurrency problems.

---

## 3. Fuzzing (Go 1.18+)

Fuzzing finds edge cases you would never think to test. Go's built-in fuzzer mutates inputs from a seed corpus and reports any input that causes a panic or invariant violation.

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

        // Round-trip property
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

### Generic Fuzz Template

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

### Running Fuzzing

```bash
# Run for 30 seconds
go test -fuzz=FuzzParseAge -fuzztime=30s ./pkg/...

# Run for specific iterations
go test -fuzz=FuzzParseAge -fuzztime=10000x ./pkg/...

# Crashes are saved to testdata/fuzz/FuzzParseAge/
# They become regression tests automatically
```

When fuzzing finds a crash, it saves the input to `testdata/fuzz/FuzzParseAge/`. Running `go test` (without `-fuzz`) automatically runs all saved crash cases as regression tests.

---

## 4. Property-Based Testing with rapid

Property-based testing generates random inputs and checks that invariants hold. This is structured fuzzing with assertions.

```go
import "pgregory.net/rapid"

func TestSortProperties(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        input := rapid.SliceOf(rapid.Int()).Draw(t, "input")

        result := make([]int, len(input))
        copy(result, input)
        sort.Ints(result)

        // Property 1: length preserved
        if len(result) != len(input) {
            t.Fatalf("length changed: %d -> %d", len(input), len(result))
        }

        // Property 2: output is sorted
        for i := 1; i < len(result); i++ {
            if result[i] < result[i-1] {
                t.Fatalf("not sorted at index %d: %d > %d", i, result[i-1], result[i])
            }
        }

        // Property 3: output is a permutation of input
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
        user := User{
            ID:    rapid.Int64Range(1, 1000000).Draw(t, "id"),
            Name:  rapid.StringMatching(`[a-zA-Z ]{1,100}`).Draw(t, "name"),
            Email: rapid.StringMatching(`[a-z]{1,20}@[a-z]{1,10}\.[a-z]{2,4}`).Draw(t, "email"),
        }

        data, err := json.Marshal(user)
        if err != nil {
            t.Fatalf("marshal failed: %v", err)
        }

        var decoded User
        if err := json.Unmarshal(data, &decoded); err != nil {
            t.Fatalf("unmarshal failed: %v", err)
        }

        if user != decoded {
            t.Fatalf("round-trip failed:\n  original: %+v\n  decoded:  %+v", user, decoded)
        }
    })
}
```

### Stateful Property Testing

Test a sequence of operations against a reference model:

```go
func TestCacheStateful(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        cache := NewLRUCache(10)
        model := make(map[string]string) // Simple map as reference

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
                if ok && got != expected {
                    t.Fatalf("Get(%q) = %q, model has %q", key, got, expected)
                }
                _ = modelOk // LRU eviction is acceptable

            case 2: // Delete
                cache.Delete(key)
                delete(model, key)
            }
        }
    })
}
```

---

## 5. Testing Concurrent Code

### Race Detector

```bash
# Always run tests with -race in CI
go test -race ./...

# Also works with go run and go build
go run -race main.go
go build -race -o myapp
```

### Finding a Race Condition

```go
// Buggy code — DATA RACE: unsynchronized read-modify-write
type Counter struct {
    n int
}

func (c *Counter) Increment() {
    c.n++ // not safe for concurrent use
}

func (c *Counter) Value() int {
    return c.n // not safe for concurrent use
}

// Test that detects the race with -race flag
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

    // With -race, this test FAILS with a race detection report
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
                m.Set(fmt.Sprintf("key-%d-%d", id, j%100), j)
            }
        }(i)
    }

    // Readers
    for i := 0; i < goroutines; i++ {
        go func(id int) {
            defer wg.Done()
            for j := 0; j < iterations; j++ {
                m.Get(fmt.Sprintf("key-%d-%d", id, j%100))
            }
        }(i)
    }

    // Deleters
    for i := 0; i < goroutines; i++ {
        go func(id int) {
            defer wg.Done()
            for j := 0; j < iterations; j++ {
                m.Delete(fmt.Sprintf("key-%d-%d", id, j%100))
            }
        }(i)
    }

    wg.Wait()
}
```

### Deterministic Testing with Channels

Use channels to coordinate goroutines deterministically instead of `time.Sleep` or blind `sync.WaitGroup`:

```go
func TestProducerConsumer(t *testing.T) {
    produced := make(chan string, 10)
    consumed := make(chan string, 10)

    // Producer
    go func() {
        for i := 0; i < 5; i++ {
            produced <- fmt.Sprintf("item-%d", i)
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

## 6. Mutation Testing

Mutation testing modifies your source code and checks if tests catch the change. A mutation that survives (tests still pass) indicates a test gap.

### Using go-mutesting

```bash
go install github.com/zimmski/go-mutesting/cmd/go-mutesting@latest

go-mutesting ./internal/service/...
```

Example mutations: replace `>` with `>=`, replace `&&` with `||`, remove function calls, change return values.

### Interpreting Results

```
Mutations:     150
Killed:        130    (86.7%)
Survived:       15    (10.0%)
Not covered:     5    ( 3.3%)
```

A surviving mutation like changing `amount > 0` to `amount >= 0` means you do not have a test for `amount == 0`.

---

## 7. go test Flags Reference

| Flag | Purpose | Example |
|------|---------|---------|
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

---

## 8. Interview Questions

**Q: Why does Go use table-driven tests instead of describe/it blocks like Jest or RSpec?**
Table-driven tests leverage Go's type system — each test case is a struct with all inputs and expected outputs. Adding cases is just adding a struct literal. No DSL to learn, no nesting to get lost in. `t.Run` provides named subtests that show up in test output and can be run individually. The pattern also works naturally with `t.Parallel()`.

**Q: Explain the difference between fakes, stubs, and mocks. Which does Go prefer?**
Fakes have working implementations (in-memory DB), stubs return canned data, mocks verify interactions (was X called?). Go prefers fakes because they test behavior rather than implementation. If you mock that `Create` was called exactly once, the test breaks when you refactor internals even if behavior is unchanged.

**Q: How does Go's race detector work?**
The race detector instruments memory accesses at compile time (`go test -race`). It detects when two goroutines access the same memory without synchronization and at least one is a write. Overhead: ~10x CPU, 5–10x memory. Use it in CI always. It reports races deterministically once detected — it does not find all possible races on every run.

**Q: What is the difference between `t.Error` and `t.Fatal`?**
`t.Error` records a failure but continues the test. `t.Fatal` records a failure and stops the test immediately (calls `runtime.Goexit()`). Use `t.Fatal`/`require` for preconditions (setup failures), `t.Error`/`assert` for independent assertions.

**Q: How do build tags help organize tests?**
Build tags (`//go:build integration`) let you categorize tests. Files without the tag are included by default. Other strategies: `testing.Short()` for a quick/full split, `TestMain` for per-package setup/teardown, naming conventions with `-run` regex filtering.

**Q: Your team has 200 tests that each start a PostgreSQL testcontainer, taking 20 minutes. How do you optimize?**
Use a shared container per package with `TestMain`. Start one container in `TestMain(m *testing.M)`, run all tests, then tear it down. Use transactions for test isolation — start a transaction before each test, rollback after. This gives a fresh database state per test without recreating the container. Add `t.Parallel()` for independent tests.

**Q: How do you test a function that uses `time.Now()`?**
Accept a `func() time.Time` parameter (or a Clock interface) instead of calling `time.Now()` directly. In production, pass `time.Now`. In tests, pass a function that returns a fixed time. The interface approach is cleaner and more Go-idiomatic.

**Q: When should you use real databases in tests vs mocks?**
Use real databases (testcontainers) for repository/data access layer tests — they catch SQL errors, constraint violations, and driver quirks that mocks miss. Use mocks/fakes for service layer tests for speed and isolation. Use mocks for handler tests to keep them fast and focused on HTTP concerns.

**Q: What does `b.ResetTimer()` do and when should you use it?**
`b.ResetTimer()` resets the benchmark timer, excluding any setup code that ran before it from the timing measurements. Call it after any expensive setup (creating test data, opening connections) so the benchmark measures only the code under test.

**Q: What are the three key invariants to check in a fuzz test?**
(1) **No panics** — if the fuzzer finds an input that panics, that is a bug. (2) **Invariant preservation** — properties that must always be true (e.g., result length equals input length, sort output is ordered). (3) **Round-trip fidelity** — if you marshal, then unmarshal, you should get back the same value.

**Q: What is mutation testing and how is it different from code coverage?**
Code coverage tells you which lines were executed by tests. Mutation testing tells you whether those executions actually verified behavior. A mutation like `>` to `>=` surviving means a line was covered but the test did not assert the boundary condition. Mutation testing scores are a better proxy for test quality than coverage percentages.

**Q: How does `t.Cleanup` differ from `defer`?**
Both run cleanup in LIFO order. The key difference: `defer` is scoped to the function where it is called, while `t.Cleanup` is scoped to the test (including all its subtests). `t.Cleanup` is preferred in helper functions because it runs cleanup regardless of how many nested `t.Run` subtests are created, and it receives `t` context for logging.
