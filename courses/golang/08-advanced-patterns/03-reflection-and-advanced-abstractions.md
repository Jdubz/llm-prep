# 03 – Reflection and Advanced Abstractions

This file assumes you have read `01-generics-and-code-generation.md` and `02-patterns-and-composition.md`. It covers reflection, plugin systems, and interview questions.

---

## 1. Reflection

### When Reflection Is Justified

Reflection in Go is powerful but expensive — both in performance and readability. Valid use cases:

1. **Serialization/deserialization** (`encoding/json` uses reflection)
2. **Struct tag processing** (ORMs, validators, config parsers)
3. **Dependency injection frameworks**
4. **Testing utilities**

### Type vs Value

```go
import "reflect"

type User struct {
    Name  string `json:"name" validate:"required"`
    Email string `json:"email" validate:"email"`
    Age   int    `json:"age"   validate:"gte=0"`
}

u := User{Name: "Alice", Email: "alice@example.com", Age: 30}

// Type inspection — static information about the type
t := reflect.TypeOf(u)
fmt.Println(t.Name())                       // "User"
fmt.Println(t.NumField())                   // 3
fmt.Println(t.Field(0).Tag.Get("json"))     // "name"
fmt.Println(t.Field(0).Tag.Get("validate")) // "required"

// Value inspection — runtime values
v := reflect.ValueOf(u)
fmt.Println(v.Field(0).String()) // "Alice"
fmt.Println(v.Field(2).Int())    // 30
```

### Reflection API Quick Reference

```go
t := reflect.TypeOf(x)          // Type info: t.Name(), t.Kind(), t.NumField()
v := reflect.ValueOf(x)         // Value info: v.Field(i), v.IsZero()
t.Field(i).Tag.Get("json")      // Read struct tags
t.Field(i).Name                  // Field name
v.Field(i).Interface()           // Get value as any

// Setting values (requires pointer)
v = reflect.ValueOf(&x).Elem()
v.Field(i).SetString("new")
```

**Warning:** Reflection is 10–100x slower than direct access. Never use on hot paths.

### Reading Struct Tags

The most common legitimate use of reflection — processing metadata attached to struct fields:

```go
func ValidateStruct(s any) error {
    v := reflect.ValueOf(s)
    t := reflect.TypeOf(s)

    if t.Kind() == reflect.Ptr {
        v = v.Elem()
        t = t.Elem()
    }

    var errs []error
    for i := 0; i < t.NumField(); i++ {
        field := t.Field(i)
        value := v.Field(i)
        tag := field.Tag.Get("validate")

        if tag == "" {
            continue
        }

        rules := strings.Split(tag, ",")
        for _, rule := range rules {
            if rule == "required" && value.IsZero() {
                errs = append(errs, fmt.Errorf("%s is required", field.Name))
            }
        }
    }

    return errors.Join(errs...)
}
```

### When to Avoid Reflection

- **Hot paths:** Reflection is 10–100x slower than direct access
- **Where generics suffice:** Use type parameters instead
- **For "convenience":** If reflection makes code clever but unreadable, do not use it

Since Go 1.18, generics have eliminated many reflection use cases. Where you previously needed `reflect` to write type-agnostic container code, you now use type parameters.

---

## 2. Plugin Systems

### The `plugin` Package (Limited Use)

Go's built-in `plugin` package loads shared objects (`.so` files) at runtime. It is Linux/macOS only and fragile:

```go
// Plugin code: plugins/greeting/main.go
package main

func Greet(name string) string {
    return "Hello, " + name + "!"
}

// Build: go build -buildmode=plugin -o greeting.so ./plugins/greeting

// Host code:
p, _ := plugin.Open("greeting.so")
greetSymbol, _ := p.Lookup("Greet")
greet := greetSymbol.(func(string) string)
fmt.Println(greet("World"))
```

**Limitations:** Both the plugin and host must be built with the exact same Go version and the same dependencies at the same versions. This makes the built-in plugin system impractical for most use cases.

### HashiCorp go-plugin (Production-Grade)

HashiCorp's approach runs plugins as separate processes communicating over gRPC. This is what Terraform, Vault, and Packer use:

```go
// Shared interface definition
type Greeter interface {
    Greet(name string) (string, error)
}

// Plugin implementation (separate binary)
type GreeterPlugin struct{}

func (g *GreeterPlugin) Greet(name string) (string, error) {
    return "Hello, " + name + "!", nil
}

// Host uses go-plugin to discover and communicate with plugin processes
// The plugin runs as a subprocess communicating over gRPC
// If the plugin crashes, it does not take down the host
```

TypeScript parallel: similar to VS Code's extension host — plugins run in a separate process for isolation. The communication protocol is well-defined, and plugin crashes are contained.

---

## 3. Interview Questions

**Q: When would you use generics vs interfaces?**
Interfaces are for polymorphism — when different types have different behavior but share a contract. Generics are for code reuse — when the same algorithm applies to multiple types. For example, `io.Reader` should be an interface because reading from a file vs a network connection involves different behavior. But `Contains(slice, target)` should be generic because the algorithm is identical regardless of the element type. Never use generics to replace an interface that models behavior.

**Q: Explain the functional options pattern and when you would use it.**
Functional options solve the problem of constructors with many optional parameters. Each option is a function that modifies the config struct. I use `WithX` naming by convention. Advantages over an options struct: zero values are unambiguous (an option not passed is different from a zero-value field), validation happens per-option with clear error messages, and the API is self-documenting. I use this pattern for any constructor with more than 2–3 optional parameters.

**Q: What are the tradeoffs of using reflection in Go?**
Reflection is 10–100x slower than direct code, it bypasses compile-time type checking, and it makes code harder to understand. I use it only when there is no compile-time alternative: processing struct tags for serialization, building validation frameworks, or writing test utilities. Since Go 1.18, generics have eliminated some reflection use cases.

**Q: How does struct embedding differ from inheritance?**
Embedding is delegation, not inheritance. When I embed `User` in `Admin`, `Admin` does not become a `User` in the type system — there is no subtype relationship. Methods are promoted as a convenience, but there is no virtual dispatch. If `Admin` defines a method with the same name, it shadows the embedded method rather than overriding it. I can still access the embedded type directly: `admin.User.Method()`. Multiple embedding is allowed, and there is no diamond problem.

**Q: When should you use code generation vs generics?**
Generics are best for simple type parameterization — data structures, utility functions, algorithms identical across types. Code generation is better when the generated code needs to be type-specific in complex ways: protobuf message types, database query functions from SQL, mock implementations of interfaces. If you can express it as a generic function with constraints, prefer generics. If the output varies significantly per type or involves boilerplate that is complex but mechanical, prefer code generation.

**Q: Describe how you would build a CLI tool in Go.**
I use cobra for any non-trivial CLI. The root command handles global flags like `--verbose` and `--output` format. Each subcommand is a separate `cobra.Command` with its own flags and validation. I use `RunE` instead of `Run` so commands return errors instead of calling `os.Exit` directly — this makes them testable. For configuration, I combine cobra flags with viper so environment variables and config files also work. I generate shell completions with cobra's built-in support and use GoReleaser to produce cross-platform binaries.

**Q: Explain Go's `embed` package and its use cases.**
The `embed` package lets you include files in the compiled binary at build time using `//go:embed` directives. Common use cases: embedding SQL migration files so the binary is self-contained, embedding HTML templates and static assets for a web server, embedding default configuration files. The embedded files are read-only and available via `embed.FS`, which implements `fs.FS`. A single binary contains everything needed to run the service.

**Q: Why does Go prefer manual dependency injection over DI frameworks?**
Manual DI in `main()` is explicit, readable, and requires no magic. The dependency graph is visible in one function, compilation fails immediately if a dependency is missing, and there is no runtime reflection overhead. DI frameworks add complexity and make the graph implicit. For services with fewer than ~20 dependencies, manual wiring is almost always clearer. For very large applications, Wire (compile-time code generation) is the Go-idiomatic choice when automation becomes necessary.

**Q: How do Go design patterns differ from OOP design patterns?**
Go's composition model is different — interfaces are implicit, embedding provides delegation, and first-class functions replace many patterns that require classes in OOP. The strategy pattern in Go is often just a function type, not an interface. The observer pattern uses channels instead of callback registration. The decorator pattern uses function wrapping or interface wrapping rather than class hierarchies. The key principle: do not force OOP patterns into Go. Learn the idiomatic equivalents that leverage Go's specific strengths.
