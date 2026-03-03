# Module 00: Go for TypeScript Engineers

Everything you need to know before starting this course. Go will feel like someone took away half your tools and then you realize you didn't need them. This guide covers the syntax, tooling, and mental model shifts so Module 01 can focus on the deeper "why" instead of the "what."

Read this front to back before touching Module 01.

---

## 1. Tooling & Environment

### Installation & Setup

Go ships as a single binary. No version managers, no nvm, no fnm. Install it and you're done.

```bash
# Install (https://go.dev/dl/)
# After installation:
go version    # go1.22.0 linux/amd64
```

### Go Modules (npm for Go)

```bash
# Initialize a new project (like npm init)
go mod init github.com/yourname/myproject

# This creates go.mod (like package.json)
# Dependencies are tracked in go.mod and go.sum (like package-lock.json)

# Add a dependency (no npm install — just import it and run)
# Go downloads dependencies automatically when you build/run

# Explicitly manage deps
go mod tidy     # add missing, remove unused (like npm prune)
go mod download # download deps to local cache
```

There is no `node_modules/`. Dependencies live in a global cache (`$GOPATH/pkg/mod`). Every project shares the same cache, deduplicated by version.

### Essential Commands

| npm / Node.js | Go Equivalent |
|---------------|---------------|
| `node app.js` | `go run main.go` or `go run .` |
| `npm test` | `go test ./...` |
| `npm run build` | `go build -o myapp .` |
| `npx prettier --write .` | `gofmt -w .` or `go fmt ./...` |
| `npx eslint .` | `go vet ./...` |
| `npm init` | `go mod init module/path` |
| `tsc --noEmit` | Built-in (compiler catches everything) |

### Project Structure

```
myproject/
├── go.mod              # package.json equivalent
├── go.sum              # lockfile
├── main.go             # entry point
├── cmd/                # entry points for multi-binary projects
│   └── server/
│       └── main.go
├── internal/           # private packages (cannot be imported externally)
│   ├── auth/
│   │   └── auth.go
│   └── db/
│       └── db.go
└── pkg/                # public packages (importable by other projects)
    └── middleware/
        └── logging.go
```

Key difference: there is no `src/` directory by convention. Go code lives at the root or in well-known directories.

---

## 2. Basic Syntax

### Variables & Constants

```go
// Variable declaration — several ways
var name string = "Alice"     // explicit type
var age = 30                  // type inferred
count := 42                   // short declaration (most common, only inside functions)

// Constants — truly immutable (unlike JS const)
const MaxRetries = 3
const Pi = 3.14159

// Multiple declarations
var (
    host = "localhost"
    port = 8080
)

// Zero values — every type has one (no undefined, no null by default)
var s string   // ""  (empty string)
var n int      // 0
var f float64  // 0.0
var b bool     // false
var p *int     // nil (the only thing that can be nil is a pointer/slice/map/channel/interface)
```

### Types

```go
// Basic types
var i int       // platform-dependent size (usually 64-bit)
var i8 int8     // -128 to 127
var i64 int64   // explicit 64-bit
var u uint      // unsigned
var f float64   // always use float64, not float32
var s string    // UTF-8, immutable
var b bool
var by byte     // alias for uint8
var r rune      // alias for int32 (a Unicode code point)

// There is no union type. No string | number. Use interfaces or separate fields.
// There is no any keyword in the type system (well, any exists but it means interface{}).
```

### Strings

```go
// String formatting (no template literals)
name := "Alice"
greeting := fmt.Sprintf("Hello, %s!", name)      // TS: `Hello, ${name}!`
formatted := fmt.Sprintf("Price: $%.2f", 19.99)  // format specifiers
debug := fmt.Sprintf("User: %+v", user)          // print struct fields

// Common verbs: %s string, %d int, %f float, %v any value, %+v verbose, %T type

// Raw strings (backticks — no escape sequences)
query := `
    SELECT *
    FROM users
    WHERE active = true
`

// String operations
strings.Contains("hello world", "world")  // true
strings.HasPrefix("hello", "he")          // true
strings.Split("a,b,c", ",")              // ["a", "b", "c"]
strings.Join([]string{"a", "b"}, ", ")    // "a, b"
strings.ToLower("HELLO")                  // "hello"
len("hello")                              // 5 (bytes, not chars — careful with Unicode)
```

### Control Flow

```go
// if — no parentheses, braces required
if count > 10 {
    fmt.Println("big")
} else if count > 5 {
    fmt.Println("medium")
} else {
    fmt.Println("small")
}

// if with initialization statement (very common in Go)
if err := doSomething(); err != nil {
    return err
}
// err is scoped to this if block

// switch — no break needed (implicit), no fallthrough by default
switch role {
case "admin":
    grantAll()
case "member":
    grantBasic()
default:
    deny()
}

// switch on type
switch v := value.(type) {
case string:
    fmt.Println("string:", v)
case int:
    fmt.Println("int:", v)
}

// for — the only loop keyword (no while, no do-while)
for i := 0; i < 10; i++ {
    fmt.Println(i)
}

// while-style
for count > 0 {
    count--
}

// infinite loop
for {
    // break when done
}

// range — iterating collections (like for-of)
for i, item := range items {
    fmt.Println(i, item)
}

// Ignore index
for _, item := range items {
    fmt.Println(item)
}

// No ternary operator. Use if/else. This is intentional.
```

---

## 3. Collections

### Slices (Dynamic Arrays)

```go
// Slices are Go's primary list type (arrays exist but are rarely used directly)
names := []string{"Alice", "Bob", "Charlie"}

// Append (like push)
names = append(names, "Dave")     // must reassign — append may allocate new backing array

// Length and capacity
len(names)   // 4
cap(names)   // capacity of underlying array

// Slicing
first := names[0]      // "Alice"
last := names[len(names)-1]  // "Dave"
sub := names[1:3]      // ["Bob", "Charlie"] — start inclusive, end exclusive

// Make with pre-allocated capacity (performance optimization)
items := make([]int, 0, 100)  // length 0, capacity 100

// Check if empty (there is no .length property — use len())
if len(names) == 0 {
    fmt.Println("empty")
}

// Nil slice vs empty slice
var s []int        // nil — len(s) == 0, safe to append to
s2 := []int{}      // empty, not nil — len(s2) == 0
// Both work the same for most operations. Prefer nil.
```

### Maps (Objects/Dictionaries)

```go
// Map creation
user := map[string]string{
    "name":  "Alice",
    "email": "alice@example.com",
}

// Access
name := user["name"]                // "Alice"
role := user["role"]                 // "" (zero value if missing — no error)
role, ok := user["role"]             // ok is false if key doesn't exist (comma-ok idiom)

if email, ok := user["email"]; ok {
    fmt.Println(email)
}

// Set
user["role"] = "admin"

// Delete
delete(user, "role")

// Iterate (order is NOT guaranteed — randomized deliberately)
for key, value := range user {
    fmt.Println(key, value)
}

// Make an empty map
scores := make(map[string]int)

// Check length
len(user)
```

### Arrays (Fixed Size — Rarely Used Directly)

```go
// Arrays have fixed length — part of the type
var arr [5]int              // [0, 0, 0, 0, 0]
arr2 := [3]string{"a", "b", "c"}

// [5]int and [3]int are DIFFERENT types. This is why slices exist.
```

---

## 4. Functions

### Basic Functions

```go
// Named return type
func add(a int, b int) int {
    return a + b
}

// Shorthand for same-type params
func add(a, b int) int {
    return a + b
}

// Multiple return values (Go's signature feature)
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, errors.New("division by zero")
    }
    return a / b, nil
}

result, err := divide(10, 3)
if err != nil {
    log.Fatal(err)
}

// Named return values (use sparingly)
func split(sum int) (x, y int) {
    x = sum * 4 / 9
    y = sum - x
    return  // "naked return" — returns named values
}
```

### Function Values (First-Class Functions)

```go
// Functions are values (like JS)
fn := func(x int) int { return x * 2 }
result := fn(5)  // 10

// Closures work the same as JS
func makeCounter() func() int {
    count := 0
    return func() int {
        count++
        return count
    }
}

counter := makeCounter()
counter()  // 1
counter()  // 2

// Function types
type Handler func(w http.ResponseWriter, r *http.Request)
```

### Variadic Functions (Rest Parameters)

```go
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

sum(1, 2, 3)         // 6
nums := []int{1, 2, 3}
sum(nums...)          // spread a slice (like ...spread in JS)
```

### Defer (Cleanup)

```go
func readFile(path string) (string, error) {
    f, err := os.Open(path)
    if err != nil {
        return "", err
    }
    defer f.Close()  // runs when the function returns, no matter what

    // ... do stuff with f
    return content, nil
}

// Defers execute LIFO (stack order)
defer fmt.Println("first")
defer fmt.Println("second")
// Prints: "second" then "first"
```

---

## 5. Structs & Methods

### Defining Structs

```go
type User struct {
    ID        string
    Name      string
    Email     string
    Age       int
    IsActive  bool
    CreatedAt time.Time
}

// Creating instances
user := User{
    ID:    "abc-123",
    Name:  "Alice",
    Email: "alice@example.com",
    Age:   30,
}

// Zero value — all fields get their zero values
var empty User  // ID:"", Name:"", Age:0, IsActive:false, etc.

// Access fields
user.Name  // "Alice"
user.Age   // 30
```

### Methods

```go
// Value receiver — operates on a copy (cannot modify the original)
func (u User) FullName() string {
    return u.Name
}

// Pointer receiver — operates on the original (can modify)
func (u *User) Deactivate() {
    u.IsActive = false
}

user := User{Name: "Alice", IsActive: true}
user.FullName()     // "Alice"
user.Deactivate()   // modifies user in place
// Go automatically takes the address — no need for (&user).Deactivate()
```

**Rule of thumb**: If the method modifies the receiver or the struct is large, use a pointer receiver. Be consistent — if one method uses a pointer receiver, all methods on that type should.

### Composition (No Inheritance)

```go
// Go has no inheritance. Use embedding (composition).
type Timestamped struct {
    CreatedAt time.Time
    UpdatedAt time.Time
}

type User struct {
    Timestamped           // embedded — User "inherits" CreatedAt, UpdatedAt
    Name  string
    Email string
}

user := User{Name: "Alice"}
user.CreatedAt  // promoted — access directly (no user.Timestamped.CreatedAt needed)
```

### Struct Tags

```go
type User struct {
    ID    string `json:"id" db:"user_id"`
    Name  string `json:"name" db:"full_name"`
    Email string `json:"email,omitempty"`   // omit if empty
}

// Tags control serialization behavior — json, db, yaml, xml, etc.
// Accessed via reflection at runtime
```

---

## 6. Interfaces

Interfaces in Go are satisfied **implicitly**. You never write `implements`. If a type has all the methods an interface requires, it satisfies the interface.

```go
// Define an interface
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

// Compose interfaces
type ReadWriter interface {
    Reader
    Writer
}

// Any type with a Read method satisfies Reader — no declaration needed
type MyFile struct { /* ... */ }

func (f *MyFile) Read(p []byte) (int, error) {
    // implementation
}
// MyFile now satisfies Reader automatically
```

### The Empty Interface (`any`)

```go
// any (alias for interface{}) accepts any value — like unknown in TS
func printAnything(v any) {
    fmt.Println(v)
}

// Type assertion — get the concrete type back
value, ok := v.(string)
if ok {
    fmt.Println("it's a string:", value)
}
```

### Common Standard Library Interfaces

```go
// These are everywhere — learn them
fmt.Stringer     // String() string        — like toString()
io.Reader        // Read([]byte) (int, error)
io.Writer        // Write([]byte) (int, error)
error            // Error() string         — the error interface
http.Handler     // ServeHTTP(ResponseWriter, *Request)
sort.Interface   // Len, Less, Swap
```

---

## 7. Error Handling

Go has no exceptions. No try/catch. Functions return errors as values.

```go
// The error pattern — you'll write this a thousand times
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)  // wrap with context
}

// Creating errors
err := errors.New("something went wrong")
err := fmt.Errorf("user %s not found", userID)

// Wrapping errors (like error chains)
err := fmt.Errorf("failed to load config: %w", originalErr)  // %w wraps

// Unwrapping and checking errors
if errors.Is(err, os.ErrNotExist) {
    // the error (or something in its chain) is "file not found"
}

var pathErr *os.PathError
if errors.As(err, &pathErr) {
    // extract the specific error type
    fmt.Println(pathErr.Path)
}
```

### Custom Error Types

```go
type NotFoundError struct {
    Resource string
    ID       string
}

func (e *NotFoundError) Error() string {
    return fmt.Sprintf("%s %s not found", e.Resource, e.ID)
}

// Return it
return nil, &NotFoundError{Resource: "user", ID: userID}
```

### The `if err != nil` Pattern

Yes, it's verbose. Yes, it's intentional. Every error path is visible and explicit. No hidden throw paths, no surprise exceptions from deep in a call stack.

```go
// This is idiomatic Go. Get used to it.
file, err := os.Open(path)
if err != nil {
    return err
}
defer file.Close()

data, err := io.ReadAll(file)
if err != nil {
    return fmt.Errorf("reading %s: %w", path, err)
}

var config Config
if err := json.Unmarshal(data, &config); err != nil {
    return fmt.Errorf("parsing config: %w", err)
}
```

---

## 8. Pointers

TypeScript has no pointers. Go does. They're simpler than C pointers — no pointer arithmetic.

```go
// & takes the address of a variable
// * dereferences a pointer (follows it to the value)

x := 42
p := &x        // p is *int (pointer to int), holds the memory address of x
fmt.Println(*p) // 42 (dereference — read the value at the address)

*p = 100       // modify the value through the pointer
fmt.Println(x)  // 100 (x changed because p points to it)
```

### Why Pointers Matter

```go
// Without pointer — function gets a copy, original is unchanged
func double(n int) {
    n = n * 2  // modifies the copy, not the original
}

x := 5
double(x)
fmt.Println(x)  // still 5

// With pointer — function modifies the original
func double(n *int) {
    *n = *n * 2
}

x := 5
double(&x)
fmt.Println(x)  // 10
```

### Nil Pointers

```go
var p *int       // nil pointer
fmt.Println(p)   // <nil>
fmt.Println(*p)  // PANIC — nil pointer dereference (like null.property in JS)

// Always check before dereferencing
if p != nil {
    fmt.Println(*p)
}
```

### When You'll See Pointers

- **Pointer receivers** on methods: `func (u *User) Update()` — modifies the receiver
- **Passing large structs** to avoid copying
- **Optional values**: `*string` means "string or nil" (Go's closest thing to `string | undefined`)
- **JSON unmarshaling**: `json.Unmarshal(data, &result)` — needs a pointer to write into

---

## 9. Packages & Visibility

### Package System

Every `.go` file starts with a package declaration. All files in the same directory must use the same package name.

```go
// File: internal/auth/auth.go
package auth

// Exported (uppercase first letter) — like export in TS
func HashPassword(plain string) string { ... }

// Unexported (lowercase first letter) — like no export in TS
func validateStrength(plain string) error { ... }
```

There are no access modifiers (`public`, `private`, `protected`). Just capitalization:
- `User` — exported (accessible from other packages)
- `user` — unexported (package-private)

### Imports

```go
import (
    // Standard library
    "fmt"
    "net/http"
    "time"

    // Third-party (full module path)
    "github.com/gin-gonic/gin"

    // Internal packages
    "github.com/yourname/myproject/internal/auth"
)

// Usage — always qualified by package name
fmt.Println("hello")
auth.HashPassword("secret")
http.ListenAndServe(":8080", nil)
```

### init() Functions

```go
// init() runs automatically when the package is imported
// Use sparingly — it's like side effects on import
func init() {
    // register drivers, set defaults, etc.
}
```

---

## 10. Goroutines & Channels (Preview)

Module 02 covers concurrency in depth, but you should know the basic syntax.

```go
// Goroutine — lightweight concurrent function (like launching a promise you don't await)
go doSomething()          // starts running concurrently

go func() {
    fmt.Println("in goroutine")
}()

// Channels — typed pipes for goroutine communication
ch := make(chan string)          // unbuffered channel

go func() {
    ch <- "hello"               // send
}()

msg := <-ch                     // receive (blocks until a value is available)
fmt.Println(msg)                // "hello"

// Buffered channel
ch := make(chan int, 10)        // holds up to 10 values without blocking
```

---

## 11. Quick Reference: Go vs TypeScript

| TypeScript | Go |
|-----------|-----|
| `const x = 5` | `x := 5` |
| `let x: number = 5` | `var x int = 5` |
| `null` / `undefined` | `nil` (only for pointers, slices, maps, channels, interfaces) |
| `true` / `false` | `true` / `false` |
| `===` | `==` (no type coercion, so no need for `===`) |
| `&&` / `\|\|` / `!` | `&&` / `\|\|` / `!` (same) |
| `console.log()` | `fmt.Println()` |
| `` `Hello ${name}` `` | `fmt.Sprintf("Hello, %s", name)` |
| `x?.y` | `if x != nil { x.y }` |
| `x ?? default` | No equivalent — use `if` or comma-ok idiom |
| `condition ? a : b` | No ternary — use `if/else` |
| `Array<T>` | `[]T` (slice) |
| `Record<K, V>` | `map[K]V` |
| `Promise<T>` | Channels or goroutines |
| `interface` | `interface` (implicitly satisfied) |
| `class` | `struct` + methods |
| `extends` | Embedding (composition) |
| `implements` | Implicit (no keyword) |
| `export` | Uppercase first letter |
| `private` | Lowercase first letter |
| `import { x } from 'y'` | `import "y"` then `y.X` |
| `throw new Error()` | `return err` |
| `try/catch` | `if err != nil` |
| `async/await` | Goroutines + channels |
| `for (const x of arr)` | `for _, x := range arr` |
| `arr.map(fn)` | `for` loop (no built-in map) |
| `arr.filter(fn)` | `for` loop with `if` |
| `arr.push(x)` | `arr = append(arr, x)` |
| `arr.length` | `len(arr)` |
| `JSON.stringify(obj)` | `json.Marshal(obj)` |
| `JSON.parse(str)` | `json.Unmarshal([]byte(str), &obj)` |
| `typeof x` | `reflect.TypeOf(x)` or `fmt.Sprintf("%T", x)` |
| `x instanceof Y` | Type assertion: `v, ok := x.(Y)` |

---

## Related Reading

Now that you have the syntax translation, the following modules go deeper into the concepts introduced here:

- **Structs, interfaces, and error handling** — [Module 01: Types, Interfaces, and Structs](01-go-mental-model/01-types-interfaces-and-structs.md) expands on sections 5–8 above with Go's philosophy of composition over inheritance
- **Goroutines and channels** — [Module 02: Goroutines and Channels](02-concurrency/01-goroutines-and-channels.md) takes the preview in section 10 and covers the full concurrency model
- **Packages and modules** — [Module 01: Packages and Modules](01-go-mental-model/02-packages-and-modules.md) deepens section 9 with visibility rules, dependency management, and project layout
- **Testing** — [Module 06: Table-Driven Tests and Mocking](06-testing/01-table-driven-tests-and-mocking.md) covers Go's testing conventions that differ significantly from Jest/Vitest

---

## Next Steps

You're now ready for [Module 01: Go Mental Model](01-go-mental-model/README.md). It goes deeper into why Go makes the design choices it does and how to stop writing TypeScript in `.go` files.
