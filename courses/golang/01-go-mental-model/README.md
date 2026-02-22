# Module 01: Go Mental Model (for TypeScript Engineers)

## Why This Module Exists

You have a decade of TypeScript. You think in interfaces, classes, async/await, and npm.
Go will feel like someone took your favorite tools and replaced them with a socket wrench set.
This module rewires your instincts so you stop writing TypeScript in `.go` files.

---

## 1. Types: Structs, Interfaces, and the Absence of Classes

### Structs Are Not Classes

In TypeScript, you build with classes:

```typescript
class User {
  constructor(
    public id: string,
    public name: string,
    private email: string
  ) {}

  greet(): string {
    return `Hello, ${this.name}`;
  }
}
```

In Go, there are no classes. There is no `this`. There are structs and methods:

```go
type User struct {
    ID    string
    Name  string
    email string // unexported — lowercase first letter
}

func (u User) Greet() string {
    return "Hello, " + u.Name
}
```

The method receiver `(u User)` is explicit. It is not magic. It is not hidden. You see it, you understand it. Methods are functions that happen to take a receiver — nothing more.

### Interfaces Are Implicit (Structural Typing on Steroids)

TypeScript has structural typing. Go takes it further: interfaces are satisfied implicitly. You never write `implements`.

```typescript
// TypeScript — explicit declaration
interface Greeter {
  greet(): string;
}

class User implements Greeter {
  greet(): string {
    return "hello";
  }
}
```

```go
// Go — implicit satisfaction
type Greeter interface {
    Greet() string
}

// User satisfies Greeter without declaring it.
// If it has a Greet() string method, it's a Greeter.
type User struct{ Name string }

func (u User) Greet() string {
    return "Hello, " + u.Name
}

func announce(g Greeter) {
    fmt.Println(g.Greet())
}
```

This has deep consequences:
- You can define interfaces where they are **consumed**, not where they are implemented.
- Standard library types satisfy your custom interfaces without knowing about them.
- Small interfaces (1-2 methods) are idiomatic. `io.Reader`, `io.Writer`, `fmt.Stringer` — these drive the entire ecosystem.

**The Go proverb:** "The bigger the interface, the weaker the abstraction."

### Zero Values vs undefined/null

TypeScript has `undefined`, `null`, and a long history of footguns around both. Go has zero values — and they are always valid.

Every type in Go has a zero value:

| Type | Zero Value |
|------|-----------|
| `int`, `float64` | `0` |
| `string` | `""` |
| `bool` | `false` |
| `pointer`, `slice`, `map`, `channel`, `function`, `interface` | `nil` |
| `struct` | All fields set to their zero values |

```go
var s string    // "" — not undefined, not null
var n int       // 0
var ok bool     // false
var p *User     // nil
var u User      // User{ID: "", Name: "", email: ""}
```

This means `var buf bytes.Buffer` is immediately usable — no constructor needed. Many Go types are designed so their zero value is useful. This is intentional and idiomatic. You should design your types the same way.

**TS comparison:**

```typescript
let s: string;       // undefined — will blow up if you use it
let n: number;       // undefined
let u: User | null;  // null — explicit, but still a runtime trap
```

### Type Assertions and Type Switches

TypeScript narrows types with `typeof`, `instanceof`, and discriminated unions. Go uses type assertions and type switches.

```go
// Type assertion — "I believe this interface holds a specific type"
val, ok := someInterface.(string)
if !ok {
    // it wasn't a string
}

// Type switch — the idiomatic way to handle multiple types
switch v := someInterface.(type) {
case string:
    fmt.Println("string:", v)
case int:
    fmt.Println("int:", v)
case error:
    fmt.Println("error:", v.Error())
default:
    fmt.Printf("unexpected type: %T\n", v)
}
```

Always use the comma-ok pattern for type assertions. A bare assertion `val := x.(string)` panics on failure.

### Embedding vs Inheritance

Go has no inheritance. It has embedding, which is composition that looks like inheritance but behaves differently.

```go
type Animal struct {
    Name string
}

func (a Animal) Speak() string {
    return a.Name + " makes a sound"
}

type Dog struct {
    Animal  // embedded — Dog "has an" Animal, but fields/methods are promoted
    Breed string
}

func main() {
    d := Dog{
        Animal: Animal{Name: "Rex"},
        Breed:  "Shepherd",
    }
    fmt.Println(d.Name)    // promoted from Animal
    fmt.Println(d.Speak()) // promoted from Animal
}
```

Key differences from inheritance:
- There is no polymorphism through embedding. `Dog` is not an `Animal`.
- You can embed multiple types (like multiple inheritance, but without the diamond problem).
- The embedded type does not know about the outer type. No `super` calls. No virtual dispatch.
- If `Dog` defines its own `Speak()`, it shadows the embedded one. There is no `override` keyword.

```typescript
// What you might expect from TS
class Dog extends Animal {
  speak(): string {
    return super.speak() + " (bark)";
  }
}
// Go does NOT work this way. Embedding is forwarding, not inheritance.
```

---

## 2. Error Handling: Multiple Returns vs try/catch

This is where most TypeScript engineers feel the most friction. Go does not have exceptions. It has values.

### The Basic Pattern

```go
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doing something: %w", err)
}
// use result
```

Compare to TypeScript:

```typescript
try {
  const result = await doSomething();
  // use result
} catch (err) {
  throw new Error(`doing something: ${err.message}`);
}
```

You will write `if err != nil` hundreds of times per project. This is intentional. Every error is handled at the point it occurs. There is no invisible control flow.

### Why Go Chose This

1. **Errors are values.** You can store them, pass them, combine them, inspect them.
2. **Explicit control flow.** You never wonder "can this function throw?" — you see the error return.
3. **No hidden panics.** (Well, almost. Panics exist, but they are for programmer bugs, not expected errors.)
4. **Composability.** Error wrapping builds a chain of context.

### Wrapping Errors with %w

```go
func readConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("reading config %s: %w", path, err)
    }

    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("parsing config %s: %w", path, err)
    }

    return &cfg, nil
}
```

The `%w` verb wraps the original error. The caller can unwrap it later. Use `%v` (not `%w`) if you want to include the message but intentionally break the error chain.

### Sentinel Errors

Sentinel errors are package-level variables that represent specific, expected conditions:

```go
var (
    ErrNotFound     = errors.New("not found")
    ErrUnauthorized = errors.New("unauthorized")
    ErrConflict     = errors.New("conflict")
)

func GetUser(id string) (*User, error) {
    // ...
    if user == nil {
        return nil, ErrNotFound
    }
    return user, nil
}
```

Callers check them with `errors.Is`:

```go
user, err := GetUser(id)
if errors.Is(err, ErrNotFound) {
    // handle 404
} else if err != nil {
    return err
}
```

`errors.Is` walks the entire wrapped error chain. Never compare with `==` directly — that breaks when errors are wrapped.

### Custom Error Types

When you need to carry data with an error:

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

// Caller extracts the structured error:
var valErr *ValidationError
if errors.As(err, &valErr) {
    fmt.Println("Bad field:", valErr.Field)
}
```

`errors.As` is the type-assertion equivalent for error chains. It walks the chain and fills the target if a match is found.

### errors.Is vs errors.As

| Use | When |
|-----|------|
| `errors.Is(err, target)` | Checking for a specific sentinel value |
| `errors.As(err, &target)` | Extracting a specific error type |

### The Error Handling Decision Tree

1. Can the caller do something different based on this error? -> Custom error type or sentinel
2. Is this an expected condition (EOF, not found)? -> Sentinel error
3. Is this just "something went wrong"? -> `fmt.Errorf("context: %w", err)`
4. Is this a programmer bug (index out of range, nil dereference)? -> Let it panic

---

## 3. Packages and Visibility

### Capitalization vs export Keyword

TypeScript:

```typescript
export function DoSomething() {}  // exported
function doSomething() {}         // not exported
```

Go:

```go
func DoSomething() {}  // Exported — capital first letter
func doSomething() {}  // unexported — lowercase first letter
```

This applies to everything: functions, types, struct fields, methods, constants, variables. If it starts with a capital letter, it is visible outside the package.

### Package Organization

Go packages are directories. One directory = one package (excluding test files with `_test` suffix).

```
myproject/
  go.mod
  main.go
  internal/
    auth/
      auth.go
      middleware.go
    database/
      postgres.go
  pkg/
    validator/
      validator.go
  api/
    handler.go
    routes.go
```

Key rules:
- Package names are lowercase, single-word, no underscores (by convention).
- The package name should describe what it **provides**, not what it **contains**.
- Avoid package names like `util`, `common`, `helpers` — these are junk drawers.
- `internal/` is special: code in `internal/` can only be imported by code in the parent tree.

### Internal Packages

The `internal` directory enforces access boundaries at the compiler level:

```
myproject/
  internal/
    auth/       # Only importable by code in myproject/
  cmd/
    server/
      main.go   # Can import myproject/internal/auth
```

No other module can import your internal packages. This is the Go equivalent of package-private in Java, enforced by the compiler.

### TS Comparison

| Concept | TypeScript | Go |
|---------|-----------|-----|
| Export | `export` keyword | Capital first letter |
| Private | No `export` / `private` | Lowercase first letter |
| Module boundary | `package.json` | `go.mod` |
| Internal | Convention only | `internal/` directory (compiler-enforced) |

---

## 4. Pointers

If you come from TypeScript, you have never explicitly managed pointers. JavaScript references are hidden from you. Go makes them explicit.

### Value Semantics vs Reference Semantics

```go
// Value semantics — a copy is made
func double(n int) int {
    n = n * 2  // modifies the copy
    return n
}

x := 5
y := double(x)
// x is still 5, y is 10

// Reference semantics — a pointer is passed
func doubleInPlace(n *int) {
    *n = *n * 2  // modifies the original
}

x := 5
doubleInPlace(&x)
// x is now 10
```

### The & and * Operators

- `&x` takes the address of `x` — gives you a pointer.
- `*p` dereferences the pointer `p` — gives you the value it points to.
- `*int` is the type "pointer to int."

```go
name := "Alice"
p := &name     // p is *string, pointing to name
fmt.Println(*p) // "Alice"
*p = "Bob"
fmt.Println(name) // "Bob"
```

### When to Use Pointers

Use a pointer when:
1. **The value is large** and copying is expensive (large structs).
2. **You need to mutate** the original value.
3. **You need to represent absence** (`nil` pointer = "no value").
4. **The type has mutable internal state** (e.g., `sync.Mutex` must not be copied).

Use a value when:
1. **The type is small** (ints, small structs, strings).
2. **You want immutability** (the function gets its own copy).
3. **The zero value is useful** and you do not need nil.

### Pointer Receivers vs Value Receivers

```go
type Counter struct {
    count int
}

// Value receiver — operates on a copy
func (c Counter) Current() int {
    return c.count
}

// Pointer receiver — operates on the original
func (c *Counter) Increment() {
    c.count++
}
```

Rules of thumb:
- If any method needs a pointer receiver, **all methods should use pointer receivers** (for consistency and interface satisfaction).
- Methods that mutate state need pointer receivers.
- Methods on large structs should use pointer receivers to avoid copying.
- Methods on small, immutable types can use value receivers.

### Nil Pointers

```go
var p *User // nil
fmt.Println(p.Name) // PANIC: nil pointer dereference
```

This is Go's version of `Cannot read properties of null`. You will hit it. Defend against it:

```go
func (u *User) DisplayName() string {
    if u == nil {
        return "anonymous"
    }
    return u.Name
}
```

---

## 5. Go Modules (go.mod)

### go.mod vs package.json

| Concept | npm / package.json | Go Modules / go.mod |
|---------|-------------------|---------------------|
| Manifest | `package.json` | `go.mod` |
| Lock file | `package-lock.json` | `go.sum` |
| Install | `npm install` | `go mod download` (usually automatic) |
| Add dep | `npm install pkg` | `go get pkg` |
| Remove unused | `npm prune` | `go mod tidy` |
| Registry | npmjs.com | No central registry — VCS URLs |
| Versioning | semver | semver (but v2+ requires path suffix) |

### go.mod Anatomy

```go
module github.com/yourname/yourproject

go 1.22

require (
    github.com/gorilla/mux v1.8.1
    golang.org/x/sync v0.6.0
)

require (
    // indirect dependencies (managed automatically)
    github.com/some/transitive v0.1.0 // indirect
)
```

### Key Commands

```bash
go mod init github.com/yourname/project  # Create go.mod
go mod tidy                               # Add missing, remove unused deps
go get github.com/pkg/errors@v0.9.1       # Add/update a dependency
go get github.com/pkg/errors@latest        # Update to latest
go mod download                            # Download all dependencies
go mod vendor                              # Copy deps into vendor/
go mod why github.com/some/pkg             # Why is this a dependency?
go mod graph                               # Print dependency graph
```

### Replace Directives

For local development or forking:

```go
// Use a local copy of a module
replace github.com/original/pkg => ../my-local-copy

// Use a fork
replace github.com/original/pkg => github.com/myfork/pkg v1.0.0
```

This is similar to `npm link` but declarative and checked into version control.

### No node_modules

Go dependencies are stored in `$GOPATH/pkg/mod` (a global, content-addressed cache). There is no `node_modules` directory. There is no `node_modules` bloat. Dependencies are downloaded once and shared across all projects.

---

## 6. Generics: Use Sparingly

Go added generics in 1.18 (2022). Coming from TypeScript, you might be tempted to genericize everything. Resist that urge.

### When interface{}/any Is Fine

```go
// This is fine for logging, debugging, etc.
func debugLog(v any) {
    fmt.Printf("[DEBUG] %+v\n", v)
}
```

`any` is an alias for `interface{}`. It is appropriate when you genuinely do not care about the type.

### When Generics Help

Generics shine for data structures and algorithms that operate on multiple types:

```go
// Before generics — you wrote this for every type or used interface{}
func ContainsInt(slice []int, target int) bool { ... }
func ContainsString(slice []string, target string) bool { ... }

// With generics
func Contains[T comparable](slice []T, target T) bool {
    for _, v := range slice {
        if v == target {
            return true
        }
    }
    return false
}
```

### When Generics Are Overkill

Do not write:

```go
type Repository[T any] interface {
    FindByID(id string) (T, error)
    Save(entity T) error
    Delete(id string) error
}
```

Instead, write concrete interfaces per domain:

```go
type UserRepository interface {
    FindByID(id string) (*User, error)
    Save(user *User) error
    Delete(id string) error
}
```

The generic version buys you nothing but complexity. You are not writing a framework. You are writing an application. Concrete types are clearer.

**The Go proverb:** "A little copying is better than a little dependency." This extends to generics — a little repetition is better than premature abstraction.

---

## 7. Naming Conventions

Go naming conventions will feel terse if you come from TypeScript's descriptive naming culture.

### Short Names

```go
// Go — short, contextual
func (s *Server) handleUser(w http.ResponseWriter, r *http.Request) {
    u, err := s.db.GetUser(r.Context(), r.PathValue("id"))
    if err != nil {
        // ...
    }
}

// TypeScript equivalent — verbose
async function handleUser(request: Request, response: Response) {
    const user = await database.getUser(request.params.id);
}
```

Go conventions:
- Single-letter variables in small scopes: `i`, `j`, `k` for indices; `r` for reader; `w` for writer; `s` for string.
- Short variable names in medium scopes: `ctx` for context, `cfg` for config, `srv` for server, `req` for request, `resp` for response.
- Descriptive names for package-level declarations and long-lived variables.

### Acronyms

Acronyms are all-caps in Go:

```go
// Correct
type HTTPClient struct{}
type XMLParser struct{}
func (c *Client) ID() string {}
var userID string

// Wrong (by Go convention)
type HttpClient struct{}
type XmlParser struct{}
func (c *Client) Id() string {}
var userId string
```

### MixedCaps, Not snake_case

Go uses `MixedCaps` (PascalCase for exported, camelCase for unexported). Never use `snake_case` for Go identifiers.

```go
// Correct
var maxRetryCount int
func NewServer() *Server {}

// Wrong
var max_retry_count int
func new_server() *Server {}
```

### Getter/Setter Naming

Go does not use `Get` prefixes for getters:

```go
// Correct
func (u *User) Name() string { return u.name }
func (u *User) SetName(n string) { u.name = n }

// Wrong (by convention)
func (u *User) GetName() string { return u.name }
```

---

## 8. init() Functions

### What They Are

`init()` functions run automatically when a package is imported, before `main()`:

```go
package database

var defaultPool *Pool

func init() {
    var err error
    defaultPool, err = NewPool(os.Getenv("DATABASE_URL"))
    if err != nil {
        log.Fatal("failed to initialize database pool:", err)
    }
}
```

### Execution Order

1. All imported packages' `init()` functions run first (recursively, depth-first).
2. Package-level variable declarations are evaluated.
3. `init()` functions in the current package run in the order they appear.
4. A single file can have multiple `init()` functions.
5. `main()` runs last.

### When to Use init()

Legitimate uses:
- Registering database drivers: `import _ "github.com/lib/pq"`
- Registering codecs or formats
- Validating package-level configuration

### When to Avoid init()

Avoid `init()` when:
- It performs I/O (network calls, file reads) — makes testing difficult.
- It has side effects that are hard to reason about.
- It can fail — `init()` cannot return errors, so failures become `log.Fatal` or panics.
- It sets up global state that should be injected.

**The better pattern:**

```go
// Instead of init()
type Server struct {
    db *sql.DB
}

func NewServer(db *sql.DB) *Server {
    return &Server{db: db}
}

// Explicit initialization in main()
func main() {
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    if err != nil {
        log.Fatal(err)
    }
    srv := NewServer(db)
    // ...
}
```

Explicit beats implicit. Dependency injection beats global state.

---

## 9. Putting It All Together: A Go Mental Model

### The Core Philosophy

| Principle | TypeScript | Go |
|-----------|-----------|-----|
| Complexity | Rich type system, many abstractions | Simple type system, few abstractions |
| Error handling | Exceptions (hidden control flow) | Values (explicit control flow) |
| Polymorphism | Classes, inheritance, interfaces | Interfaces (implicit), embedding |
| Concurrency | Single-threaded + event loop | Multi-threaded + goroutines |
| Dependencies | npm (huge ecosystem, framework culture) | stdlib-first (small ecosystem, library culture) |
| Code style | Flexible (ESLint configs, Prettier debates) | One style (`gofmt`, no debates) |
| Null safety | Optional chaining, nullish coalescing | Zero values, nil checks |
| Generics | Pervasive (mapped types, conditional types, template literals) | Minimal (added in 1.18, use sparingly) |

### The Mental Shifts You Must Make

1. **Stop reaching for frameworks.** Go's standard library is your framework. `net/http` is production-ready. You do not need Express.
2. **Stop fighting `if err != nil`.** It is not boilerplate. It is the explicit handling of every failure mode. Embrace it.
3. **Stop building deep type hierarchies.** Compose with embedding and small interfaces.
4. **Stop thinking in async/await.** Goroutines are not promises. They are concurrent threads of execution that communicate via channels.
5. **Stop over-abstracting.** Write the concrete thing first. Extract an interface when you need to mock it or swap implementations.
6. **Stop naming things verbosely.** Context provides meaning. A `User` method does not need `user` in every variable name.

---

## Interview Questions

### Conceptual

1. **Explain how Go interfaces differ from TypeScript interfaces.** Focus on implicit satisfaction, interface size philosophy, and the consumer-side definition pattern.

2. **Why does Go use multiple return values for errors instead of exceptions?** Discuss explicit control flow, error values, and the ability to handle errors at the call site without hidden jumps.

3. **When would you use a pointer receiver vs a value receiver?** Cover mutation, large structs, consistency with other methods, and the interface satisfaction implications.

4. **What is the zero value and why does it matter?** Explain that every type has a usable zero value, how this eliminates null constructor patterns, and how to design types with useful zero values.

5. **Explain Go's approach to embedding. How does it differ from inheritance?** Cover promotion, shadowing, the fact that embedded types are unaware of their embedder, and that embedding does not create an is-a relationship.

### Coding

6. **Implement a custom error type** that includes an HTTP status code, a user-facing message, and an internal message. Implement `Error()` and show how a caller would use `errors.As` to extract it.

7. **Refactor this code to be idiomatic Go:**

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

8. **Design a package structure** for a REST API with users, authentication, and a PostgreSQL database. Explain what goes in `internal/` vs exported packages.

### Scenario

9. **You are reviewing a PR** where a colleague has written a generic `Repository[T any]` interface with 10 methods. The project has exactly two entity types (User and Order). What feedback do you give?

10. **A bug report says "nil pointer dereference" in production.** Walk through your debugging process, including how to read the stack trace, common causes, and how you would prevent this class of bug.

---

## Further Reading

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Go Proverbs](https://go-proverbs.github.io/)
- [The Go Blog — Error Handling](https://go.dev/blog/error-handling-and-go)
- [The Go Blog — Errors Are Values](https://go.dev/blog/errors-are-values)
- [The Go Blog — Go Modules](https://go.dev/blog/using-go-modules)
- [100 Go Mistakes and How to Avoid Them](https://100go.co/) (book)
