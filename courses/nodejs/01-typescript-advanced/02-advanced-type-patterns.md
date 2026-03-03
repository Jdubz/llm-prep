# 02 — Advanced Type Patterns, Utility Types, Variance, Declaration Merging, and Interview Q&A

> Assumes familiarity with conditional types, infer, mapped types, and template literals from file 01.

---

## 1. Utility Type Internals

These are not magic. Know what the compiler does.

```typescript
// Pick -- homomorphic, preserves modifiers
type Pick<T, K extends keyof T> = { [P in K]: T[P] };

// Omit -- K extends keyof any (not keyof T) -- allows omitting nonexistent keys
type Omit<T, K extends keyof any> = Pick<T, Exclude<keyof T, K>>;

// Record -- non-homomorphic, no modifier inheritance
type Record<K extends keyof any, T> = { [P in K]: T };

// Extract / Exclude -- rely on distribution
type Extract<T, U> = T extends U ? T : never;
type Exclude<T, U> = T extends U ? never : T;

// NonNullable -- changed from conditional to intersection in TS 4.8
type NonNullable<T> = T & {};   // {} matches everything except null | undefined

// Parameters / ReturnType -- infer in function positions
type Parameters<T extends (...args: any) => any> = T extends (...args: infer P) => any ? P : never;
type ReturnType<T extends (...args: any) => any> = T extends (...args: any) => infer R ? R : any;

// Awaited -- recursive unwrap of thenables (simplified)
type Awaited<T> = T extends null | undefined ? T
  : T extends object & { then(onfulfilled: infer F, ...args: infer _): any }
    ? F extends ((value: infer V, ...args: infer _) => any) ? Awaited<V> : never
    : T;
```

### Utility Types Quick Reference

```typescript
Partial<T>                    // All properties optional
Required<T>                   // All properties required
Readonly<T>                   // All properties readonly
Pick<T, K extends keyof T>    // Subset of properties
Omit<T, K extends keyof any>  // Exclude properties
Record<K, T>                  // Object with keys K, values T
Exclude<T, U>                 // Remove union members assignable to U
Extract<T, U>                 // Keep union members assignable to U
NonNullable<T>                // Remove null and undefined
Parameters<T>                 // Tuple of parameter types
ReturnType<T>                 // Return type
ConstructorParameters<T>      // Constructor parameter types
InstanceType<T>               // Instance type of a constructor
Awaited<T>                    // Recursively unwrap Promise
Uppercase<S> / Lowercase<S> / Capitalize<S> / Uncapitalize<S>  // String intrinsics
```

---

## 2. Variance Annotations (TS 4.7+)

### 2.1 Core Concepts

- **Covariant** (`out`): `Producer<Dog>` assignable to `Producer<Animal>`
- **Contravariant** (`in`): `Consumer<Animal>` assignable to `Consumer<Dog>`
- **Invariant** (`in out`): Neither direction

### 2.2 The `in`/`out` Modifiers

```typescript
interface Producer<out T> { get(): T; }
interface Consumer<in T> { accept(value: T): void; }
interface Invariant<in out T> { transform(value: T): T; }
```

Without annotations, TypeScript infers variance from usage — slower and occasionally wrong for recursive types. Explicit annotations make the compiler reject definitions that violate declared variance.

### 2.3 Function Parameter Bivariance

With `strictFunctionTypes`, method syntax remains bivariant while arrow/function syntax is contravariant:

```typescript
interface Bivariant { method(x: Dog): void; }       // bivariant
interface Contravariant { method: (x: Dog) => void; } // contravariant
```

### 2.4 Covariance and Contravariance in Practice

```typescript
type Handler<T> = (event: T) => void;
// T is contravariant. Handler<Animal> assignable to Handler<Dog>, not reverse.
```

### 2.5 Arrays Are Covariant (Unsoundly)

```typescript
declare let animals: Animal[]; declare let dogs: Dog[];
animals = dogs;                    // OK but unsound
animals.push({ name: 'Cat' });    // Pushes non-Dog into Dog[]
```

`readonly Animal[]` fixes this — no mutation possible.

### 2.6 Variance Quick Reference

| Position | Variance | Example |
|----------|----------|---------|
| Return type | Covariant | `() => Dog` assignable to `() => Animal` |
| Parameter | Contravariant | `(x: Animal) => void` assignable to `(x: Dog) => void` |
| Both | Invariant | `{ get(): T; set(v: T): void }` |
| Readonly prop | Covariant | `{ readonly value: Dog }` assignable to `{ readonly value: Animal }` |
| Mutable prop | Invariant | `{ value: Dog }` NOT assignable to `{ value: Animal }` |

| Annotation | Meaning | Safe for |
|------------|---------|----------|
| `out T` | Covariant | Return types, readonly properties |
| `in T` | Contravariant | Parameter types |
| `in out T` | Invariant | Mutable properties, bidirectional use |

---

## 3. Declaration Merging and Module Augmentation

### 3.1 Interface Merging

Interfaces with the same name in the same scope merge. This is how `@types/passport` adds `user` to Express `Request`.

### 3.2 Module Augmentation

```typescript
declare module 'express-serve-static-core' {
  interface Request {
    context: { requestId: string; traceId: string };
  }
}
```

### 3.3 Global Augmentation

```typescript
export {};
declare global {
  namespace NodeJS {
    interface ProcessEnv {
      DATABASE_URL: string;
      NODE_ENV: 'development' | 'staging' | 'production';
    }
  }
}
```

### 3.4 Namespace Merging

A namespace can merge with a class, function, or enum to add static members:

```typescript
class Validator { validate(input: string): boolean { return Validator.patterns.email.test(input); } }
namespace Validator {
  export const patterns = { email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ };
}
Validator.patterns.email; // static member
```

---

## 4. Const Assertions and `satisfies`

### 4.1 `as const`

Produces the narrowest possible type — literal types, `readonly` tuples, `readonly` properties:

```typescript
const config = { endpoint: 'https://api.example.com', retries: 3 } as const;
// { readonly endpoint: "https://api.example.com"; readonly retries: 3 }
```

### 4.2 `satisfies`

Validates that an expression conforms to a type **without widening**:

```typescript
type ColorMap = Record<string, [number, number, number] | string>;
const colors = { red: [255, 0, 0], green: '#00ff00' } satisfies ColorMap;
// colors.red is [number, number, number] -- not widened to the union
// colors.green is string -- not widened to the union
```

### 4.3 The Gold Standard: `satisfies` + `as const`

```typescript
const routes = { home: '/', about: '/about', user: '/user/:id' } as const satisfies Record<string, string>;
// Literal types preserved AND validated against the constraint
```

---

## 5. Common Advanced Patterns

### 5.1 Discriminated Unions

```typescript
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };
```

The discriminant must be a literal type. TypeScript narrows based on control flow.

### 5.2 Type Narrowing Techniques

1. `typeof` guards
2. `instanceof` guards
3. `in` operator
4. Custom type guards (`x is T`)
5. Discriminated unions
6. Truthiness narrowing (beware `0`, `''`, `false`)

### 5.3 Assertion Functions

```typescript
function assertDefined<T>(value: T | null | undefined, msg?: string): asserts value is T {
  if (value == null) throw new Error(msg ?? 'Value is not defined');
}
// Narrows after the call. Throws on failure -- if it returns, the assertion holds.
// Key limitation: must be called as a statement, not inside expressions.
```

### 5.4 Type-Safe Event Emitter

```typescript
class TypedEmitter<T extends Record<string, any>> {
  private handlers = new Map<keyof T, Set<Function>>();
  on<K extends keyof T>(event: K, handler: (payload: T[K]) => void): this {
    if (!this.handlers.has(event)) this.handlers.set(event, new Set());
    this.handlers.get(event)!.add(handler);
    return this;
  }
  emit<K extends keyof T>(event: K, payload: T[K]): void {
    this.handlers.get(event)?.forEach(fn => fn(payload));
  }
}
```

### 5.5 Conditional Props (Discriminated Component Props)

```typescript
type InputProps =
  | { variant: 'text'; value: string }
  | { variant: 'number'; value: number; min?: number; max?: number }
  | { variant: 'select'; value: string; options: string[] };
```

---

## 6. TypeScript Compiler Internals (Deep Dive)

### 6.1 Type Inference via Unification

For `identity(42)`: create fresh `T`, constrain `T >= 42`, resolve to literal `42`. For `merge('hello', 42)`: constraints from both args yield `T = 'hello' | 42` (union of lower bounds).

### 6.2 Structural Checking

`A extends B` checks that for every property in `B`, `A` has a compatible one. Extra properties in `A` are fine (structural subtyping). Excess property checking only applies to fresh object literals — a separate syntactic check.

### 6.3 The Pipeline

**Scanner** (tokens) -> **Parser** (AST) -> **Binder** (symbols) -> **Type Checker** (types) -> **Emitter** (JS)

The type checker uses lazy evaluation (on-demand with caching), context-sensitive typing (callback params from context), widening (`let x = 'hello'` becomes `string`), and narrowing (control flow analysis).

### 6.4 Control Flow Analysis

The compiler maintains a flow graph tracking narrowed types. This analysis is **intraprocedural** — it does not cross function boundaries. Type guard functions (`x is T`) bridge the gap.

### 6.5 Type Instantiation

`Promise<string>` creates a cached instantiation. Each unique type-argument combination is a new entry. Deep generic hierarchies with many type params create exponential instantiation counts — the primary cause of slow TypeScript projects.

---

## 7. How Prisma Types Work (Deep Dive)

### 7.1 Code Generation, Not Inference

Prisma runs `prisma generate` to emit `.d.ts` files from the `.prisma` schema: model types, input types for every query shape, and a fully-typed `PrismaClient`.

### 7.2 The Select/Include Pattern

```typescript
type UserPayload<S extends UserSelect | undefined> =
  S extends undefined ? User : {
    [K in keyof S as S[K] extends false | undefined ? never : K]:
      K extends 'posts'
        ? S[K] extends { select: infer PS extends PostSelect } ? PostPayload<PS>[] : Post[]
        : K extends keyof User ? User[K] : never;
  };
```

The return type of `findMany({ select: {...} })` is computed from the literal type of `select`. This requires const inference on the argument, recursive conditional types for nested selects, and mapped types with key remapping.

### 7.3 Takeaways

1. **Generate types from schema** — do not try to infer everything purely at the type level.
2. **Use const generics** for argument inference: `function query<const T extends Select>(select: T): Payload<T>`.
3. **Recursive mapped types** for nested structures — but watch recursion depth.

---

## 8. Performance Considerations (Deep Dive)

### 8.1 Limits

- Conditional type recursion: ~50 depth (hardcoded)
- Max tuple length: ~10,000
- Error 2589: `Type instantiation is excessively deep`
- Error 2590: `Union type too complex to represent`

### 8.2 Measuring

```bash
tsc --generateTrace ./trace-output   # chrome://tracing
tsc --diagnostics                     # look at "Instantiations" count
```

### 8.3 Common Traps

**Deep intersections:** `A & B & C & D & E` creates nested anonymous types. Use `interface Result extends A, B, C, D, E {}` — compiler caches the flat structure.

**Distributive types over large unions:** 1000-member union through a conditional = 1000 instantiations.

**Excessive generic chaining:** Each `.method<T>()` in a builder chain creates a new instantiation of the full generic stack.

### 8.4 Optimization Strategies

- Prefer interfaces over type intersections for object shapes
- Eliminate unnecessary generics (if a type param appears once and is not needed for inference, use the concrete type)
- Break large types into smaller cached intermediates
- Use project references (`composite: true`) for incremental builds in monorepos
- `skipLibCheck: true` skips `.d.ts` checking — faster CI but masks declaration errors

### 8.5 Project References in Detail

For large monorepos, project references fundamentally change the compilation model:

```jsonc
// tsconfig.json (root)
{
  "references": [
    { "path": "./packages/core" },
    { "path": "./packages/api" },
    { "path": "./packages/web" }
  ]
}
```

Each referenced project must set `composite: true` and `declaration: true`. Benefits:

1. **Incremental compilation**: Only re-checks projects whose dependencies changed.
2. **Declaration emit caching**: `.d.ts` files act as boundaries — downstream projects never re-check upstream source files.
3. **Parallel builds**: `tsc --build` compiles independent projects concurrently.

### 8.6 When Type Complexity Is a Code Smell

Not every type-level trick belongs in production code. Signals that type complexity has become a liability:

- **Editor lag** exceeding 2-3 seconds for autocompletion on a typed function call
- **Error messages** spanning more than 10 lines of nested generics that no team member can parse
- **Type-only changes** triggering full project rebuilds because a deeply nested conditional type changed
- **`any` casts** proliferating downstream because consumers cannot satisfy the constraint

The pragmatic response: push complex inference into code-generated types (like Prisma does), expose simple generic interfaces to consumers, and reserve type-level programming for library internals where the complexity is amortized across many call sites.

---

## 9. Key tsconfig Flags

```jsonc
{
  "strict": true,
  "noUncheckedIndexedAccess": true,
  "exactOptionalPropertyTypes": true,
  "noPropertyAccessFromIndexSignature": true,
  "verbatimModuleSyntax": true
}
```

---

## 10. Interview Questions

### Q1: `type` vs `interface` — when does the distinction matter?

**Answer:** Interfaces merge (critical for module augmentation). Interface `extends` catches conflicts at declaration; type `&` silently produces `never`. Type aliases support mapped/conditional/template literal types. The TS team says interface `extends` is faster than `&` for large hierarchies. Use interfaces for public APIs; type aliases for unions, conditionals, and computed shapes.

### Q2: What is the type of `Result` and why?

```typescript
type IsString<T> = T extends string ? 'yes' : 'no';
type Result = IsString<string | number>;
```

**Answer:** `'yes' | 'no'`. Distributes over the union: `IsString<string>` = `'yes'`, `IsString<number>` = `'no'`. To treat the union as a whole, wrap: `[T] extends [string]`.

### Q3: Implement type-safe `deepGet` with dot-path strings.

**Answer:** Combine `DeepGet<T, P>` (recursive conditional with template literal parsing) with `AllPaths<T>` (recursive mapped type generating all valid paths as a union). Constrain the path parameter to `AllPaths<T>` so only valid paths are accepted.

```typescript
type DeepGet<T, P extends string> =
  P extends `${infer K}.${infer Rest}`
    ? K extends keyof T ? DeepGet<T[K], Rest> : never
    : P extends keyof T ? T[P] : never;
```

### Q4: `unknown` vs `any`?

**Answer:** `any` disables checking (bidirectional assignment, unchecked access). `unknown` is the type-safe top type — must narrow before use. Use `unknown` at external boundaries; `any` only as a last resort behind a well-typed boundary.

### Q5: Implement `Mutable<T>` — the opposite of `Readonly<T>`.

**Answer:** `type Mutable<T> = { -readonly [K in keyof T]: T[K] }`. The `-readonly` modifier removes readonly. Deep version recurses through nested objects.

### Q6: What is a homomorphic mapped type?

**Answer:** Maps over `keyof T` for a generic `T`. The compiler preserves modifiers from the source. `Partial`, `Required`, `Readonly`, `Pick` are homomorphic. `Record` is not. If your source has optional/readonly props and you want to preserve or remove them, your mapped type must be homomorphic.

### Q7: `satisfies` vs type annotation?

**Answer:** Annotation widens to the declared type; `satisfies` validates without widening. Use `satisfies` when you need both validation and preserved literal types / key autocompletion.

### Q8: Extract all function-valued keys from an object type.

**Answer:**
```typescript
type FunctionKeys<T> = {
  [K in keyof T]: T[K] extends (...args: any[]) => any ? K : never;
}[keyof T];
```

### Q9: Assertion functions vs type guards?

**Answer:** Type guards return `boolean`, narrow in the `true` branch. Assertion functions return `void`, narrow after the call by throwing on failure. Use guards for branching; assertions for preconditions.

### Q10: Make `Object.keys()` return strongly typed keys?

**Answer:** `Object.keys()` returns `string[]` by design — structural typing means objects can have more runtime keys than declared. A typed wrapper (`Object.keys(obj) as (keyof T)[]`) is unsound if extra keys exist. In an interview, demonstrating awareness of this tradeoff matters more than producing the cast.

### Q11: Type-safe state machine?

**Answer:** Encode allowed transitions in a type map. Generic class tracks current state; `transition` method constrains `Next` to valid successors of current state, returns a new instance parameterized by `Next`. Same technique as the builder pattern in file 01 — applied to state instead of configuration.

### Q12: Performance of deep recursive conditional types?

**Answer:** TS has a ~50-depth limit for conditional types. Strategies: (1) tail-call optimization with accumulators (TS 4.5+), (2) bounded recursion via counter tuples, (3) lazy evaluation using interfaces instead of type aliases.

### Q13: HS256 vs RS256 in distributed TypeScript systems?

**Answer:** This is a cross-module concern (auth). RS256 — the private key signs, the public key verifies. Any compromised microservice with HS256 can forge tokens system-wide. RS256 constrains signing to the auth service. At the type level, ensure JWT payloads are typed with proper interfaces (use `as` only inside the parser that validates claims, not at every call site).

### Q14: What is the `in out` variance annotation for?

**Answer:** Marks a type parameter as invariant — no subtyping in either direction. Use when the type parameter appears in both input (contravariant) and output (covariant) positions. Without this annotation, TypeScript infers variance from usage, which is correct but slower and can be wrong for recursive types. Explicit `in out` makes the compiler enforce the constraint and catch definition-site errors rather than use-site errors.
