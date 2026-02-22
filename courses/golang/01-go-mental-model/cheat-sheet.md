# Module 01 Cheat Sheet: Go Mental Model

## Go vs TypeScript Syntax Comparison

| Concept | TypeScript | Go |
|---------|-----------|-----|
| Variable declaration | `let x: number = 5` | `x := 5` or `var x int = 5` |
| Constant | `const x = 5` | `const x = 5` |
| Function | `function add(a: number, b: number): number` | `func add(a, b int) int` |
| Arrow function / closure | `(x) => x * 2` | `func(x int) int { return x * 2 }` |
| Multiple returns | Return object/tuple | `func f() (int, error)` |
| Struct / Object type | `interface User { name: string }` | `type User struct { Name string }` |
| Interface | `interface Reader { read(): void }` | `type Reader interface { Read() }` |
| Implements | `class X implements I` | Implicit (no keyword) |
| Inheritance | `class Dog extends Animal` | Embedding: `type Dog struct { Animal }` |
| Array | `number[]` or `Array<number>` | `[5]int` (fixed) or `[]int` (slice) |
| Map | `Map<string, number>` | `map[string]int` |
| Null check | `if (x !== null)` | `if x != nil` |
| String interpolation | `` `Hello ${name}` `` | `fmt.Sprintf("Hello %s", name)` |
| For loop | `for (let i = 0; i < n; i++)` | `for i := 0; i < n; i++` |
| For-each | `arr.forEach(v => ...)` | `for i, v := range arr` |
| While loop | `while (cond)` | `for cond { }` |
| Enum | `enum Color { Red, Green }` | `const ( Red = iota; Green )` |
| Export | `export function F()` | `func F()` (capital letter) |
| Private | No `export` / `private` | `func f()` (lowercase letter) |
| Type assertion | `value as string` | `value.(string)` |
| Generics | `function f<T>(x: T): T` | `func f[T any](x T) T` |
| Error handling | `try { } catch (e) { }` | `val, err := f(); if err != nil { }` |
| Async | `async/await` | goroutines + channels |
| Package manager | npm / yarn / pnpm | `go mod` |

## Zero Values

| Type | Zero Value | TS Equivalent |
|------|-----------|---------------|
| `bool` | `false` | `undefined` |
| `int`, `float64`, etc. | `0` | `undefined` |
| `string` | `""` | `undefined` |
| `*T` (pointer) | `nil` | `null` |
| `[]T` (slice) | `nil` | `undefined` |
| `map[K]V` | `nil` | `undefined` |
| `chan T` | `nil` | N/A |
| `func(...)` | `nil` | `undefined` |
| `interface` | `nil` | `undefined` |
| `struct` | All fields zeroed | N/A |

## Error Handling Patterns

```go
// 1. Simple propagation with context
if err != nil {
    return fmt.Errorf("loading user %s: %w", id, err)
}

// 2. Sentinel error check
if errors.Is(err, sql.ErrNoRows) {
    return nil, ErrNotFound
}

// 3. Type-based error check
var valErr *ValidationError
if errors.As(err, &valErr) {
    log.Printf("field %s: %s", valErr.Field, valErr.Message)
}

// 4. Multiple error conditions
switch {
case errors.Is(err, ErrNotFound):
    http.Error(w, "not found", 404)
case errors.Is(err, ErrForbidden):
    http.Error(w, "forbidden", 403)
default:
    http.Error(w, "internal error", 500)
}
```

## Pointer Decision Guide

```
Should I use a pointer?
  |
  +--> Does the method mutate the receiver? --> YES --> pointer receiver (*T)
  |
  +--> Is the struct large (>64 bytes)? --> YES --> pointer (*T)
  |
  +--> Do I need to represent "no value" (nil)? --> YES --> pointer (*T)
  |
  +--> Does the type contain a sync.Mutex? --> YES --> pointer (*T), MUST NOT copy
  |
  +--> Otherwise --> value (T) is fine
```

## Package Naming Conventions

| Rule | Good | Bad |
|------|------|-----|
| Lowercase, single word | `http`, `json`, `auth` | `HTTP`, `Json`, `Auth` |
| No underscores | `strconv` | `str_conv` |
| No plural | `user` | `users` |
| Describes what it provides | `compress` | `util` |
| Short | `io` | `inputoutput` |

## Naming Quick Reference

| What | Convention | Example |
|------|-----------|---------|
| Exported function | PascalCase | `NewServer()` |
| Unexported function | camelCase | `handleRequest()` |
| Acronyms | ALL CAPS | `HTTPClient`, `ID`, `URL` |
| Interface (single method) | Method name + `er` | `Reader`, `Writer`, `Stringer` |
| Getter | No `Get` prefix | `user.Name()` not `user.GetName()` |
| Setter | `Set` prefix | `user.SetName(n)` |
| Local variables | Short | `ctx`, `cfg`, `req`, `w`, `r` |

## go.mod Commands

```bash
go mod init MODULE_PATH     # Initialize a new module
go mod tidy                  # Sync go.mod/go.sum with source
go get PKG@VERSION           # Add or update a dependency
go get PKG@latest            # Update to latest version
go mod download              # Download dependencies to cache
go mod vendor                # Copy dependencies into vendor/
go mod verify                # Verify dependency integrity
go mod why PKG               # Explain why a package is needed
go mod graph                 # Print full dependency graph
go mod edit -replace=OLD=NEW # Add a replace directive
go list -m all               # List all dependencies
go list -m -u all            # List available updates
```

## Common Build Flags

```bash
go build ./...               # Build all packages
go build -gcflags='-m' ./... # Show escape analysis + inlining decisions
go build -race ./...         # Build with race detector
go build -ldflags='-s -w'    # Strip debug info (smaller binary)
go vet ./...                 # Static analysis
go fmt ./...                 # Format all code
```
