# 03 – Advanced Go Internals

This file assumes you have read `01-types-interfaces-and-structs.md` and `02-packages-and-modules.md`. It covers what happens under the hood — interface internals, escape analysis, stack vs heap, compiler optimizations, and the language trade-off landscape. You will not use most of this daily, but interviewers ask about it and understanding it makes you a sharper Go engineer.

---

## 1. Go Compiler Internals

### Compilation Speed

Go compiles fast. Famously fast. A 100,000-line Go project compiles in seconds. The equivalent TypeScript project takes minutes with `tsc`.

Why:
- **No header files.** Go's import system uses compiled object files, not source parsing.
- **Dependency graph is a DAG.** Circular imports are forbidden, enabling parallel compilation.
- **Simple grammar.** Go's grammar is intentionally simple — no operator overloading, no template metaprogramming, no macros.
- **Single-pass compilation.** The compiler processes each file in roughly one pass.
- **Object files encode export information.** When package A imports package B, the compiler reads B's compiled object file, not B's source.

### Escape Analysis

Escape analysis determines whether a variable can live on the stack or must be allocated on the heap.

```go
func newUser() *User {
    u := User{Name: "Alice"} // Does this live on the stack or heap?
    return &u                 // Returns a pointer — u escapes to the heap
}

func greetUser() {
    u := User{Name: "Bob"}   // u does NOT escape — stays on the stack
    fmt.Println(u.Name)       // Wait — fmt.Println takes interface{}, so u escapes!
}
```

View escape analysis output:

```bash
go build -gcflags='-m' ./...
# Output:
# ./main.go:5:2: moved to heap: u
# ./main.go:10:13: u escapes to heap
```

Use `-m -m` for more verbose output.

**Why this matters:** Stack allocation is essentially free (just a pointer bump). Heap allocation requires garbage collection. Understanding escape analysis helps you write code that avoids unnecessary heap allocations in hot paths.

**Common escapes:**
- Returning a pointer to a local variable.
- Passing a value to an `interface{}` parameter (boxing).
- Closures that capture local variables.
- Sending a pointer through a channel.

### Inlining

The Go compiler inlines small functions — replacing the call site with the function body.

```go
func add(a, b int) int {
    return a + b
}

// The compiler replaces add(x, y) with x + y at the call site.
```

Check inlining decisions:

```bash
go build -gcflags='-m' ./...
# Output:
# ./main.go:3:6: can inline add
# ./main.go:8:10: inlining call to add
```

Functions that are too large, contain loops, or use certain constructs (defer, recover, type switches) may not be inlined. The inlining budget has increased over Go versions — Go 1.22+ is more aggressive.

---

## 2. Memory Layout

### Stack vs Heap Allocation

| Property | Stack | Heap |
|----------|-------|------|
| Speed | Very fast (pointer bump) | Slower (allocator + GC) |
| Lifetime | Function scope | Until GC collects |
| Size | Goroutine starts with ~2-8 KB, grows as needed | Limited by system memory |
| Management | Automatic (function return = deallocation) | Garbage collected |

Go's goroutine stacks start small (a few KB) and grow dynamically. This is why you can spawn millions of goroutines — each starts with minimal memory.

### Struct Memory Layout

Go structs are laid out in memory in field order with padding for alignment:

```go
type BadLayout struct {
    a bool    // 1 byte
    // 7 bytes padding
    b int64   // 8 bytes
    c bool    // 1 byte
    // 7 bytes padding
}
// Total: 24 bytes

type GoodLayout struct {
    b int64   // 8 bytes
    a bool    // 1 byte
    c bool    // 1 byte
    // 6 bytes padding
}
// Total: 16 bytes
```

For most code, this does not matter. For performance-critical code with millions of allocations, it does. Use `unsafe.Sizeof()` to check.

### Slice Internals

A slice is a 3-word struct (24 bytes on 64-bit systems):

```go
type slice struct {
    array unsafe.Pointer // pointer to underlying array
    len   int
    cap   int
}
```

This is why passing a slice by value is cheap — you are copying 24 bytes, not the entire array. But modifying the slice header (append that triggers growth) in a function will not be visible to the caller unless you return the new slice or use a pointer.

### Map Internals

Maps are hash tables implemented as pointers internally. Passing a map by value passes the pointer — modifications are visible to the caller. This is unlike slices.

```go
func addToMap(m map[string]int) {
    m["key"] = 42 // caller sees this change
}

func appendToSlice(s []int) {
    s = append(s, 42) // caller does NOT see this if append grew the slice
}
```

---

## 3. Interface Internals

### The Fat Pointer (iface vs eface)

An interface value in Go is a fat pointer — two words:

```
+--------+--------+
|  type  |  data  |
+--------+--------+
```

- **type**: pointer to type metadata (method table, type info).
- **data**: pointer to the actual value (or the value itself if it fits in a pointer).

There are two internal interface representations:
- **`eface`** (empty interface / `any` / `interface{}`): stores a type pointer and a data pointer. No method table needed.
- **`iface`** (non-empty interface): stores an itab pointer (which contains the type info AND a pointer to the method table) and a data pointer.

```go
var w io.Writer         // both type and data are nil
w = os.Stdout           // type = *os.File metadata, data = pointer to os.Stdout
w = &bytes.Buffer{}     // type = *bytes.Buffer metadata, data = pointer to buffer
```

### The nil Interface Trap

This is the single most confusing thing in Go for newcomers:

```go
func process() error {
    var p *MyError // p is nil (*MyError)
    // ... some logic that doesn't set p ...
    return p // DANGER: returns a non-nil interface!
}

func main() {
    err := process()
    if err != nil {
        // THIS EXECUTES even though p was nil!
        fmt.Println("error:", err) // "error: <nil>"
    }
}
```

Why? The returned interface has:
- type = `*MyError` (not nil — we know the type)
- data = `nil` (the pointer is nil)

Since the type field is set, the interface is not nil. This is correct but surprising.

**Fix:**

```go
func process() error {
    var p *MyError
    // ...
    if p == nil {
        return nil // return an explicit nil interface
    }
    return p
}
```

**Rule:** Never return a typed nil pointer as an interface. Return an explicit `nil`.

### Interface Satisfaction at Compile Time

You can verify interface satisfaction at compile time with a blank assignment:

```go
var _ io.Reader = (*MyReader)(nil)
var _ http.Handler = (*MyHandler)(nil)
```

This will not compile if the type does not satisfy the interface.

---

## 4. Reflection

### The reflect Package

Go's `reflect` package provides runtime type introspection. If you come from TypeScript, think of it as runtime access to type information — except Go is statically typed, so reflection is the escape hatch.

```go
func inspect(v any) {
    t := reflect.TypeOf(v)
    val := reflect.ValueOf(v)

    fmt.Println("Type:", t.Name())
    fmt.Println("Kind:", t.Kind())

    if t.Kind() == reflect.Struct {
        for i := 0; i < t.NumField(); i++ {
            field := t.Field(i)
            value := val.Field(i)
            fmt.Printf("  %s (%s) = %v\n", field.Name, field.Type, value)
        }
    }
}
```

### Struct Tags

Struct tags are metadata strings attached to struct fields. They are accessed via reflection:

```go
type User struct {
    ID    int    `json:"id" db:"user_id" validate:"required"`
    Name  string `json:"name" db:"user_name" validate:"min=2,max=100"`
    Email string `json:"email,omitempty" db:"email"`
}

// Reading tags
t := reflect.TypeOf(User{})
field, _ := t.FieldByName("ID")
jsonTag := field.Tag.Get("json")  // "id"
dbTag := field.Tag.Get("db")      // "user_id"
```

Common tag conventions:
- `json:"fieldName,omitempty"` — JSON marshal/unmarshal
- `db:"column_name"` — database mapping
- `validate:"required,min=2"` — validation rules
- `yaml:"key"` — YAML marshal/unmarshal

### When to Avoid Reflection

Reflection is slow, not type-safe, and hard to debug. Avoid it when:
- Generics can solve the problem (Go 1.18+).
- A code generator can produce the boilerplate.
- You are using it to work around the type system rather than with it.

Legitimate uses:
- Serialization/deserialization libraries (encoding/json uses reflection).
- ORM-style database mappers.
- Dependency injection frameworks.
- Testing utilities.

**The Go proverb:** "Clear is better than clever." Reflection is clever.

---

## 5. The unsafe Package

`unsafe` provides operations that step outside Go's type safety. It exists for interop with C, low-level systems programming, and performance hacks.

```go
import "unsafe"

// Get the size of a type
size := unsafe.Sizeof(User{})

// Get the offset of a field
offset := unsafe.Offsetof(User{}.Name)

// Convert between pointer types (extremely dangerous)
var i int64 = 42
p := unsafe.Pointer(&i)
f := (*float64)(p) // reinterpret the bits of int64 as float64
```

**Rules:**
- You almost never need `unsafe` in application code.
- Libraries that use `unsafe` must be reviewed extremely carefully.
- `unsafe.Pointer` is the Go equivalent of `void*` in C.
- The `go vet` tool checks for common `unsafe` misuse.

---

## 6. cgo and FFI

cgo lets Go call C code and vice versa:

```go
// #include <stdio.h>
// #include <stdlib.h>
//
// void greet(const char* name) {
//     printf("Hello, %s!\n", name);
// }
import "C"
import "unsafe"

func main() {
    name := C.CString("World")
    defer C.free(unsafe.Pointer(name))
    C.greet(name)
}
```

### The Cost of cgo

cgo is not free:
- **Build time increases significantly.** Cross-compilation becomes painful.
- **Each cgo call has overhead** (~100ns+) due to stack switching between Go and C stacks.
- **The garbage collector cannot see C memory.** You must manually free C allocations.
- **Goroutine scheduling is affected.** A goroutine making a cgo call blocks its OS thread.

**The Go proverb:** "Cgo is not Go." Prefer pure Go solutions when possible.

### TS Comparison

| Concept | TypeScript/Node | Go |
|---------|----------------|-----|
| Native addon | N-API / node-gyp | cgo |
| FFI | node-ffi-napi | cgo or syscall |
| WASM | Built-in | `GOOS=js GOARCH=wasm` |

---

## 7. Go vs Rust vs TypeScript: Choosing the Right Tool

### Performance Characteristics

| Dimension | TypeScript (Node) | Go | Rust |
|-----------|------------------|-----|------|
| Startup time | Slow (V8 init) | Fast | Fast |
| Throughput | Moderate | High | Highest |
| Memory usage | High (V8 overhead) | Moderate | Low |
| Latency | Variable (GC pauses rare, but event loop stalls) | Low (sub-ms GC pauses) | Lowest (no GC) |
| Concurrency model | Single-threaded event loop | Goroutines (M:N threading) | OS threads + async |
| Compilation | JIT (V8) | AOT (fast) | AOT (slow) |

### When to Use Each

**TypeScript/Node is best when:**
- Building UI (React, Vue, etc.).
- You need rapid prototyping.
- The team is exclusively frontend/fullstack JavaScript.
- The workload is I/O-bound with moderate throughput needs.

**Go is best when:**
- Building microservices, APIs, CLI tools.
- You need high concurrency with simple code.
- You want fast compilation and deployment (single binary).
- The team needs to onboard quickly (Go is learnable in weeks).
- You need good-enough performance without fighting the language.

**Rust is best when:**
- You need maximum performance (game engines, databases, OS components).
- You need zero-cost abstractions and no GC pauses.
- You are building safety-critical systems.
- You can afford the learning curve and slower development velocity.

### The Decision Matrix

| Factor | Choose Go | Choose Rust | Choose TS |
|--------|-----------|-------------|-----------|
| Team ramp-up speed | Best | Worst | Good |
| Raw performance | Good | Best | Adequate |
| Memory safety guarantees | GC-safe | Compile-time safe | GC-safe |
| Ecosystem maturity (web) | Good | Growing | Best |
| Binary size | Small | Small | N/A (needs runtime) |
| Cross-compilation | Trivial | Manageable | N/A |
| Concurrency complexity | Low | Medium-High | Low (but limited) |

### A Senior Engineer's Take

If you are building a web API, Go gives you 90% of Rust's performance with 30% of the complexity. TypeScript gives you 60% of Go's performance with the most familiar ecosystem. Rust gives you the last 10% of performance at the cost of 3x development time.

Pick the tool that matches your constraint: if it is team velocity, Go. If it is maximum performance, Rust. If it is frontend/fullstack velocity, TypeScript.

---

## 8. Interview Questions

### Conceptual

1. **Explain how Go interfaces differ from TypeScript interfaces.** Focus on implicit satisfaction, interface size philosophy, and the consumer-side definition pattern.

2. **Why does Go use multiple return values for errors instead of exceptions?** Discuss explicit control flow, error values, and the ability to handle errors at the call site without hidden jumps.

3. **When would you use a pointer receiver vs a value receiver?** Cover mutation, large structs, consistency with other methods, and the interface satisfaction implications.

4. **What is the zero value and why does it matter?** Explain that every type has a usable zero value, how this eliminates null constructor patterns, and how to design types with useful zero values.

5. **Explain Go's approach to embedding. How does it differ from inheritance?** Cover promotion, shadowing, the fact that embedded types are unaware of their embedder, and that embedding does not create an is-a relationship.

6. **What is the nil interface trap?** Describe how an interface with a non-nil type field but nil data field compares as non-nil, give the canonical example, and explain the fix.

7. **What is escape analysis and why does it matter for performance?** Explain stack vs heap allocation, that the compiler decides based on variable lifetime, and how to observe the compiler's decisions with `-gcflags='-m'`.

8. **What are `iface` and `eface` internally?** Explain the two-word fat pointer, the difference between empty interfaces (eface, type + data) and non-empty interfaces (iface, itab + data), and what an itab contains.

### Coding

9. **Implement a custom error type** that includes an HTTP status code, a user-facing message, and an internal message. Implement `Error()` and show how a caller would use `errors.As` to extract it.

10. **Refactor this code to be idiomatic Go:**

```go
// Given
type iAnimal interface {
    GetName() string
    GetSound() string
}

type AnimalBase struct {
    name string
    sound string
}

func (a *AnimalBase) GetName() string { return a.name }
func (a *AnimalBase) GetSound() string { return a.sound }
```

Expected: Remove `i` prefix, remove `Get` prefix, consider whether the interface is needed, rename to follow Go conventions.

11. **Design a package structure** for a REST API with users, authentication, and a PostgreSQL database. Explain what goes in `internal/` vs exported packages.

### Scenario

12. **You are reviewing a PR** where a colleague has written a generic `Repository[T any]` interface with 10 methods. The project has exactly two entity types (User and Order). What feedback do you give?

13. **A bug report says "nil pointer dereference" in production.** Walk through your debugging process, including how to read the stack trace, common causes, and how you would prevent this class of bug.

14. **A colleague says "we should avoid escape analysis concerns and always allocate on the stack."** How do you respond? What are the actual trade-offs, and when does allocation strategy matter?

---

## Related Reading

- **Generics and type system extensions** — [Module 08: Generics and Code Generation](../08-advanced-patterns/01-generics-and-code-generation.md) covers type parameters and constraints that interact with the interface internals described in section 4
- **Reflection at the application level** — [Module 08: Reflection and Advanced Abstractions](../08-advanced-patterns/03-reflection-and-advanced-abstractions.md) covers `reflect.TypeOf`, struct tags, and when reflection is justified vs the runtime cost discussed in section 5
- **GC tuning in production** — [Module 07: Deployment and Scaling](../07-production/03-deployment-and-scaling.md), section 3 (Runtime Tuning) covers `GOGC` and `GOMEMLIMIT` for the garbage collector described in section 3
- **Memory profiling** — [Module 06: Benchmarking, Profiling, and Advanced Testing](../06-testing/03-benchmarking-profiling-and-advanced-testing.md), section 2 (Profiling) shows how to use pprof to measure escape analysis and allocation behavior described in section 2
- **Concurrency runtime** — [Module 02: Advanced Concurrency Patterns](../02-concurrency/03-advanced-concurrency-patterns.md), section 1 (The GMP Scheduler Model) explains the goroutine scheduling that sits on top of the runtime internals covered here

---

## Practice Suggestions

These exercises reinforce the internals concepts from this module (Types, Interfaces, and Structs through Advanced Go Internals):

1. **Escape analysis investigation** — Write a function that allocates a struct and returns a pointer to it. Run `go build -gcflags="-m" ./...` and observe which allocations escape to the heap. Modify the function to keep the struct on the stack and verify with the compiler output.

2. **Interface cost measurement** — Write a benchmark that compares calling a method on a concrete type vs through an interface. Measure the difference with `go test -bench=.` and explain the indirect call overhead from the itable dispatch described in section 4.

3. **Zero value explorer** — Create structs with various field types (slices, maps, pointers, channels, interfaces) and write tests that verify the zero value behavior for each. Confirm which zero values are usable immediately and which require initialization.

4. **Custom Stringer and error types** — Implement the `fmt.Stringer` and `error` interfaces for a set of domain types. Write table-driven tests that verify both the string representation and error unwrapping chain (`errors.Is`, `errors.As`).

5. **Memory layout visualization** — Create a struct with fields of varying sizes and use `unsafe.Sizeof` and `unsafe.Offsetof` to map out the memory layout including padding. Rearrange fields for minimal padding and measure the size difference.

6. **Build a small reflection-based struct validator** — Use `reflect` to read custom struct tags (e.g., `validate:"required,min=3"`) and validate field values. Compare performance against a hand-written validator using benchmarks.

---

## Further Reading

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Go Proverbs](https://go-proverbs.github.io/)
- [The Go Blog — Error Handling](https://go.dev/blog/error-handling-and-go)
- [The Go Blog — Errors Are Values](https://go.dev/blog/errors-are-values)
- [The Go Blog — Go Modules](https://go.dev/blog/using-go-modules)
- [Go Compiler Internals (go.dev)](https://go.dev/doc/asm)
- [The Go Memory Model](https://go.dev/ref/mem)
- [Go GC Guide](https://tip.golang.org/doc/gc-guide)
- [Understanding Go Interface Internals (Russ Cox)](https://research.swtch.com/interfaces)
- [Allocation Efficiency in High-Performance Go Services](https://segment.com/blog/allocation-efficiency-in-high-performance-go-services/)
- [Cgo Is Not Go (Dave Cheney)](https://dave.cheney.net/2016/01/18/cgo-is-not-go)
- [100 Go Mistakes and How to Avoid Them](https://100go.co/) (book)
