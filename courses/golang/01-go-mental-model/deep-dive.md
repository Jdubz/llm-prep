# Module 01 Deep Dive: Compiler Internals, Memory Layout, and the Machinery Beneath

This document covers what happens under the hood. You will not use most of this daily, but interviewers ask about it and understanding it makes you a sharper Go engineer.

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

### The Fat Pointer

An interface value in Go is a fat pointer — two words:

```
+--------+--------+
|  type  |  data  |
+--------+--------+
```

- **type**: pointer to type metadata (method table, type info).
- **data**: pointer to the actual value (or the value itself if it fits in a pointer).

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

## Further Reading

- [Go Compiler Internals (go.dev)](https://go.dev/doc/asm)
- [The Go Memory Model](https://go.dev/ref/mem)
- [Go GC Guide](https://tip.golang.org/doc/gc-guide)
- [Understanding Go Interface Internals (Russ Cox)](https://research.swtch.com/interfaces)
- [Allocation Efficiency in High-Performance Go Services](https://segment.com/blog/allocation-efficiency-in-high-performance-go-services/)
- [Cgo Is Not Go (Dave Cheney)](https://dave.cheney.net/2016/01/18/cgo-is-not-go)
