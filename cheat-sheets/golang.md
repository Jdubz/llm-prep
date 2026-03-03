---
title: "Go Quick Reference"
---

# Conventions

- **Exported** names are `Capitalized`, unexported are `lowercase`
- **Formatting**: always `gofmt` / `goimports`
- **Errors**: return `error` as last value, check immediately
- **Zero values**: `0`, `""`, `nil`, `false` — always valid defaults
- **Naming**: short vars (`i`, `ctx`, `err`), descriptive exports

# string

```go
strings.Split(s, ",")      // []string
strings.Join(sl, ",")      // string
strings.Contains(s, sub)   // bool
strings.HasPrefix(s, p)    // bool
strings.TrimSpace(s)       // trimmed
strings.ReplaceAll(s, a, b)
fmt.Sprintf("hi %s %d", name, n)
s[1:4]                     // byte slice (careful w/ unicode)
```

# slice

```go
sl = append(sl, x)         // grow (must reassign!)
len(sl) / cap(sl)          // length / capacity
sl[1:4]                    // sub-slice
copy(dst, src)              // copy elements
sl = make([]T, len, cap)   // pre-allocate
// Delete element at i (order-preserving):
sl = append(sl[:i], sl[i+1:]...)
```

# map

```go
m := make(map[K]V)
m[k] = v                    // set
v, ok := m[k]               // comma-ok lookup
delete(m, k)                // remove
for k, v := range m { }     // iterate (random order)
```

# Structs & Interfaces

```go
type User struct {
    Name string
    Age  int
}
u := User{Name: "Jo", Age: 30}  // literal
func (u *User) Greet() string   // pointer receiver

type Reader interface {          // implicit satisfaction
    Read(p []byte) (int, error)
}
```

# Concurrency

```go
go func() { ... }()          // launch goroutine
ch := make(chan T, buf)       // buffered channel
ch <- v / v := <-ch           // send / receive
close(ch)                     // signal done

select {                      // multiplex channels
case v := <-ch1:
case ch2 <- x:
case <-ctx.Done():            // cancellation
default:                      // non-blocking
}

var wg sync.WaitGroup         // wait for goroutines
wg.Add(1); go func() { defer wg.Done(); ... }()
wg.Wait()

var mu sync.Mutex             // protect shared state
mu.Lock(); defer mu.Unlock()
```

# Error Handling

```go
if err != nil {
    return fmt.Errorf("op failed: %w", err) // wrap
}

// Check wrapped errors
errors.Is(err, os.ErrNotExist)  // value match
errors.As(err, &target)         // type match

// Custom error
type NotFoundError struct{ ID string }
func (e *NotFoundError) Error() string { ... }
```

# Common Patterns

```go
// Context for cancellation/timeouts
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()

// Defer for cleanup
f, err := os.Open(path)
if err != nil { return err }
defer f.Close()

// Type assertion
v, ok := i.(string)

// Table-driven tests
tests := []struct{ in, want string }{ ... }
for _, tt := range tests {
    got := fn(tt.in)
    if got != tt.want { t.Errorf(...) }
}
```
