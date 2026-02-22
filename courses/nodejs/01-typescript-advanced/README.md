# Module 01: TypeScript Advanced Patterns

> For engineers with 10+ years of TypeScript. This is not a tutorial — it is a whetstone.

---

## Table of Contents

1. [Conditional Types](#1-conditional-types)
2. [Mapped Types](#2-mapped-types)
3. [Template Literal Types](#3-template-literal-types)
4. [Branded and Nominal Types](#4-branded-and-nominal-types)
5. [Type-Level Programming](#5-type-level-programming)
6. [Utility Type Internals](#6-utility-type-internals)
7. [Declaration Merging and Module Augmentation](#7-declaration-merging-and-module-augmentation)
8. [Const Assertions and `satisfies`](#8-const-assertions-and-satisfies)
9. [Variance Annotations](#9-variance-annotations)
10. [Common Advanced Patterns](#10-common-advanced-patterns)
11. [Interview Questions](#11-interview-questions)

---

## 1. Conditional Types

### 1.1 The Mechanics of `infer`

`infer` introduces a type variable inside the `extends` clause of a conditional type. It is pattern matching at the type level.

```typescript
type MyReturnType<T> = T extends (...args: any[]) => infer R ? R : never;
type UnwrapPromise<T> = T extends Promise<infer U> ? U : T;

// Recursive unwrap
type DeepUnwrapPromise<T> = T extends Promise<infer U> ? DeepUnwrapPromise<U> : T;
type A = DeepUnwrapPromise<Promise<Promise<Promise<string>>>>; // string
```

**Multiple `infer` positions** -- same variable in multiple spots yields _union_ for covariant positions and _intersection_ for contravariant positions:

```typescript
type Foo<T> = T extends { a: infer U; b: infer U } ? U : never;
type T1 = Foo<{ a: string; b: number }>; // string | number (covariant)

type Bar<T> = T extends {
  a: (x: infer U) => void;
  b: (x: infer U) => void;
} ? U : never;
type T2 = Bar<{ a: (x: string) => void; b: (x: number) => void }>;
// string & number => never (contravariant)
```

### 1.2 Distributive Conditional Types

A conditional type distributes over a union **if and only if** the checked type is a naked type parameter:

```typescript
type ToArray<T> = T extends any ? T[] : never;
type Distributed = ToArray<string | number>; // string[] | number[]

// Prevent distribution by wrapping in a tuple:
type ToArrayNonDist<T> = [T] extends [any] ? T[] : never;
type NonDistributed = ToArrayNonDist<string | number>; // (string | number)[]
```

Distribution is why `Exclude<T, U>` works -- each union member is tested individually:

```typescript
type Exclude<T, U> = T extends U ? never : T;
// T = 'a' | 'b' | 'c', U = 'a' => 'b' | 'c'
```

### 1.3 Nested Inference

```typescript
type ParseSignature<T> = T extends (...args: infer A) => Promise<infer R>
  ? { args: A; returnType: R; async: true }
  : T extends (...args: infer A) => infer R
    ? { args: A; returnType: R; async: false }
    : never;

type Sig = ParseSignature<(x: number, y: string) => Promise<boolean>>;
// { args: [x: number, y: string]; returnType: boolean; async: true }
```

---

## 2. Mapped Types

### 2.1 Key Remapping with `as`

```typescript
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

// Filter keys by remapping to never
type OnlyStringKeys<T> = {
  [K in keyof T as T[K] extends string ? K : never]: T[K];
};
```

### 2.2 Template Literal Keys

```typescript
type CSSMargin = `margin-${'top' | 'right' | 'bottom' | 'left'}`;

type EventMap<T extends string> = {
  [K in T as `on${Capitalize<K>}`]: (event: K) => void;
};
type ButtonEvents = EventMap<'click' | 'hover' | 'focus'>;
```

### 2.3 Recursive Mapped Types

```typescript
type DeepReadonly<T> = T extends Function ? T
  : T extends object ? { readonly [K in keyof T]: DeepReadonly<T[K]> } : T;

type DeepPartial<T> = T extends Function ? T
  : T extends object ? { [K in keyof T]?: DeepPartial<T[K]> } : T;

type DeepRequired<T> = T extends Function ? T
  : T extends object ? { [K in keyof T]-?: DeepRequired<NonNullable<T[K]>> } : T;
```

### 2.4 Homomorphic vs Non-Homomorphic

A mapped type is **homomorphic** when it maps over `keyof T` for a type parameter `T`. The compiler preserves modifiers (readonly, optional) only in homomorphic mapped types. `Partial`, `Required`, `Readonly`, and `Pick` are homomorphic. `Record` is not.

---

## 3. Template Literal Types

### 3.1 Intrinsic String Types

`Uppercase`, `Lowercase`, `Capitalize`, `Uncapitalize` -- compiler intrinsics, not user-space types.

### 3.2 Parsing with Template Literals

```typescript
type Split<S extends string, D extends string> =
  S extends `${infer Head}${D}${infer Tail}` ? [Head, ...Split<Tail, D>] : [S];
type Path = Split<'a.b.c.d', '.'>; // ["a", "b", "c", "d"]

type ExtractRouteParams<T extends string> =
  T extends `${string}:${infer Param}/${infer Rest}`
    ? { [K in Param | keyof ExtractRouteParams<Rest>]: string }
    : T extends `${string}:${infer Param}` ? { [K in Param]: string } : {};

type Params = ExtractRouteParams<'/users/:userId/posts/:postId'>;
// { userId: string; postId: string }
```

### 3.3 Type-Safe Routing

```typescript
type RouteMap = {
  '/users/:id': { id: string };
  '/posts/:postId/comments/:commentId': { postId: string; commentId: string };
};

function navigate<T extends keyof RouteMap>(path: T, params: RouteMap[T]): void {}
navigate('/users/:id', { id: '123' });     // OK
navigate('/users/:id', { postId: '123' }); // Error
```

---

## 4. Branded and Nominal Types

TypeScript is structurally typed. Branding introduces nominal-like guarantees via phantom properties.

### 4.1 The Brand Pattern

```typescript
declare const __brand: unique symbol;
type Brand<T, B extends string> = T & { [__brand]: B };

type UserId = Brand<string, 'UserId'>;
type PostId = Brand<string, 'PostId'>;

function getUser(id: UserId): void {}
const userId = 'abc' as UserId;
const postId = 'def' as PostId;
getUser(userId);  // OK
getUser(postId);  // Error
```

### 4.2 Currency Safety

```typescript
type USD = Brand<number, 'USD'>;
type EUR = Brand<number, 'EUR'>;
function addUSD(a: USD, b: USD): USD { return (a + b) as USD; }
addUSD(100 as USD, 50 as USD);   // OK
addUSD(100 as USD, 85 as EUR);   // Error
```

### 4.3 Validated Brands via Smart Constructors

The `as` cast is a code smell in production. Isolate it inside a validator:

```typescript
type Email = Brand<string, 'Email'>;
function parseEmail(input: string): Email {
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input)) throw new Error(`Invalid email`);
  return input as Email;
}
// Grep for `as Email` -- it should appear only inside parseEmail.
```

### 4.4 Phantom Types for State Machines

```typescript
type Draft = { readonly _state: 'draft' };
type Published = { readonly _state: 'published' };
type Article<State> = { title: string; body: string } & State;

function publish(a: Article<Draft>): Article<Published> {
  return { ...a, _state: 'published' } as Article<Published>;
}
// unpublish(draftArticle) => compile error
```

---

## 5. Type-Level Programming

### 5.1 Tuple Manipulation

```typescript
type Head<T extends any[]> = T extends [infer H, ...any[]] ? H : never;
type Tail<T extends any[]> = T extends [any, ...infer R] ? R : never;
type Last<T extends any[]> = T extends [...any[], infer L] ? L : never;
type Reverse<T extends any[]> = T extends [infer H, ...infer R] ? [...Reverse<R>, H] : [];
type Length<T extends any[]> = T['length'];
```

### 5.2 Type-Safe Builder Pattern

```typescript
class URLBuilder<S extends Record<string, boolean> = { host: false; port: false; protocol: false }> {
  private config: any = {};
  setHost(host: string): URLBuilder<S & { host: true }> {
    this.config.host = host; return this as any;
  }
  setPort(port: number): URLBuilder<S & { port: true }> {
    this.config.port = port; return this as any;
  }
  setProtocol(p: string): URLBuilder<S & { protocol: true }> {
    this.config.protocol = p; return this as any;
  }
  build(this: URLBuilder<{ host: true; port: true; protocol: true }>): string {
    return `${this.config.protocol}://${this.config.host}:${this.config.port}`;
  }
}
new URLBuilder().setHost('localhost').setPort(3000).setProtocol('https').build(); // OK
// new URLBuilder().setHost('localhost').build(); // Error
```

### 5.3 Exhaustive Switch with `never`

```typescript
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${JSON.stringify(x)}`);
}
// In a switch over a discriminated union, the default branch receives `never`
// if all variants are handled. Adding a new variant without a case triggers a compile error.
```

### 5.4 Type-Level Path Access

```typescript
type DeepGet<T, P extends string> =
  P extends `${infer K}.${infer Rest}`
    ? K extends keyof T ? DeepGet<T[K], Rest> : never
    : P extends keyof T ? T[P] : never;

type Nested = { user: { profile: { name: string; age: number } } };
type Name = DeepGet<Nested, 'user.profile.name'>; // string
```

---

## 6. Utility Type Internals

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

---

## 7. Declaration Merging and Module Augmentation

### 7.1 Interface Merging

Interfaces with the same name in the same scope merge. This is how `@types/passport` adds `user` to Express `Request`.

### 7.2 Module Augmentation

```typescript
declare module 'express-serve-static-core' {
  interface Request {
    context: { requestId: string; traceId: string };
  }
}
```

### 7.3 Global Augmentation

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

### 7.4 Namespace Merging

A namespace can merge with a class, function, or enum to add static members:

```typescript
class Validator { validate(input: string): boolean { return Validator.patterns.email.test(input); } }
namespace Validator {
  export const patterns = { email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/ };
}
Validator.patterns.email; // static member
```

---

## 8. Const Assertions and `satisfies`

### 8.1 `as const`

Produces the narrowest possible type -- literal types, `readonly` tuples, `readonly` properties:

```typescript
const config = { endpoint: 'https://api.example.com', retries: 3 } as const;
// { readonly endpoint: "https://api.example.com"; readonly retries: 3 }
```

### 8.2 `satisfies`

Validates that an expression conforms to a type **without widening**:

```typescript
type ColorMap = Record<string, [number, number, number] | string>;
const colors = { red: [255, 0, 0], green: '#00ff00' } satisfies ColorMap;
// colors.red is [number, number, number] -- not widened to the union
// colors.green is string -- not widened to the union
```

### 8.3 The Gold Standard: `satisfies` + `as const`

```typescript
const routes = { home: '/', about: '/about', user: '/user/:id' } as const satisfies Record<string, string>;
// Literal types preserved AND validated against the constraint
```

---

## 9. Variance Annotations

### 9.1 Core Concepts

- **Covariant** (`out`): `Producer<Dog>` assignable to `Producer<Animal>`
- **Contravariant** (`in`): `Consumer<Animal>` assignable to `Consumer<Dog>`
- **Invariant** (`in out`): Neither direction

### 9.2 The `in`/`out` Modifiers (TS 4.7+)

```typescript
interface Producer<out T> { get(): T; }
interface Consumer<in T> { accept(value: T): void; }
interface Invariant<in out T> { transform(value: T): T; }
```

Without annotations, TypeScript infers variance from usage -- slower and occasionally wrong for recursive types. Explicit annotations make the compiler reject definitions that violate declared variance.

### 9.3 Function Parameter Bivariance

With `strictFunctionTypes`, method syntax remains bivariant while arrow/function syntax is contravariant:

```typescript
interface Bivariant { method(x: Dog): void; }       // bivariant
interface Contravariant { method: (x: Dog) => void; } // contravariant
```

---

## 10. Common Advanced Patterns

### 10.1 Discriminated Unions

```typescript
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };
```

The discriminant must be a literal type. TypeScript narrows based on control flow.

### 10.2 Type Narrowing Techniques

1. `typeof` guards, 2. `instanceof` guards, 3. `in` operator, 4. Custom type guards (`x is T`), 5. Discriminated unions, 6. Truthiness narrowing (beware `0`, `''`, `false`).

### 10.3 Assertion Functions

```typescript
function assertDefined<T>(value: T | null | undefined, msg?: string): asserts value is T {
  if (value == null) throw new Error(msg ?? 'Value is not defined');
}
// Narrows after the call. Throws on failure -- if it returns, the assertion holds.
// Key limitation: must be called as a statement, not inside expressions.
```

### 10.4 Type-Safe Event Emitter

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

### 10.5 Conditional Props (Discriminated Component Props)

```typescript
type InputProps =
  | { variant: 'text'; value: string }
  | { variant: 'number'; value: number; min?: number; max?: number }
  | { variant: 'select'; value: string; options: string[] };
```

---

## 11. Interview Questions

### Q1: `type` vs `interface` -- when does the distinction matter?

**Answer:** Interfaces merge (critical for module augmentation). Interface `extends` catches conflicts at declaration; type `&` silently produces `never`. Type aliases support mapped/conditional/template literal types. The TS team says interface `extends` is faster than `&` for large hierarchies. Use interfaces for public APIs; type aliases for unions, conditionals, and computed shapes.

### Q2: What is the type of `Result` and why?

```typescript
type IsString<T> = T extends string ? 'yes' : 'no';
type Result = IsString<string | number>;
```

**Answer:** `'yes' | 'no'`. Distributes over the union: `IsString<string>` = `'yes'`, `IsString<number>` = `'no'`. To treat the union as a whole, wrap: `[T] extends [string]`.

### Q3: Implement type-safe `deepGet` with dot-path strings.

**Answer:** Combine `DeepGet<T, P>` (recursive conditional with template literal parsing) with `AllPaths<T>` (recursive mapped type generating all valid paths as a union). See Section 5.4 for `DeepGet` implementation. Constrain the path parameter to `AllPaths<T>` so only valid paths are accepted.

### Q4: `unknown` vs `any`?

**Answer:** `any` disables checking (bidirectional assignment, unchecked access). `unknown` is the type-safe top type -- must narrow before use. Use `unknown` at external boundaries; `any` only as a last resort behind a well-typed boundary.

### Q5: Implement `Mutable<T>` -- the opposite of `Readonly<T>`.

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

**Answer:** `Object.keys()` returns `string[]` by design -- structural typing means objects can have more runtime keys than declared. A typed wrapper (`Object.keys(obj) as (keyof T)[]`) is unsound if extra keys exist. In an interview, demonstrating awareness of this tradeoff matters more than producing the cast.

### Q11: Type-safe state machine?

**Answer:** Encode allowed transitions in a type map. Generic class tracks current state; `transition` method constrains `Next` to valid successors of current state, returns a new instance parameterized by `Next`. See Section 5.2 for the builder pattern -- same technique applied to state.

### Q12: Performance of deep recursive conditional types?

**Answer:** TS has a ~50-depth limit for conditional types. Strategies: (1) tail-call optimization with accumulators (TS 4.5+), (2) bounded recursion via counter tuples, (3) lazy evaluation using interfaces instead of type aliases. See `deep-dive.md` Section 8 for details.
