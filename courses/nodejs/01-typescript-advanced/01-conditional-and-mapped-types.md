# 01 — Conditional Types, Infer, Mapped Types, and Template Literals

> For engineers with 10+ years of TypeScript. This is not a tutorial — it is a whetstone.

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

**Multiple `infer` positions** — same variable in multiple spots yields _union_ for covariant positions and _intersection_ for contravariant positions:

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

Distribution is why `Exclude<T, U>` works — each union member is tested individually:

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

### 1.4 Conditional Type Patterns (Cheat Sheet)

```typescript
// Distribute over union
type Distribute<T> = T extends any ? T[] : never;
// Prevent distribution
type NoDistribute<T> = [T] extends [any] ? T[] : never;
// Infer from function
type Params<T> = T extends (...args: infer P) => any ? P : never;
type Return<T> = T extends (...args: any) => infer R ? R : never;
// Infer from promise (recursive)
type Unwrap<T> = T extends Promise<infer U> ? Unwrap<U> : T;
// Infer from array
type ElementOf<T> = T extends readonly (infer E)[] ? E : never;
// Value union of object
type ValueOf<T> = T[keyof T];
// Check for never
type IsNever<T> = [T] extends [never] ? true : false;
// Check for any
type IsAny<T> = 0 extends (1 & T) ? true : false;
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

### 2.5 Mapped Type Patterns (Cheat Sheet)

```typescript
// Key remapping (filter)
type StringKeysOnly<T> = {
  [K in keyof T as T[K] extends string ? K : never]: T[K];
};
// Key transformation
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};
// Remove modifiers
type Mutable<T> = { -readonly [K in keyof T]: T[K] };
type Concrete<T> = { [K in keyof T]-?: T[K] };
// Make specific keys optional / required
type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;
```

---

## 3. Template Literal Types

### 3.1 Intrinsic String Types

`Uppercase`, `Lowercase`, `Capitalize`, `Uncapitalize` — compiler intrinsics, not user-space types.

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

### 3.4 Template Literal Recipes (Cheat Sheet)

```typescript
// Split string into tuple
type Split<S extends string, D extends string> =
  S extends `${infer H}${D}${infer T}` ? [H, ...Split<T, D>] : [S];

// Extract route params
type RouteParams<T extends string> =
  T extends `${string}:${infer P}/${infer R}` ? P | RouteParams<R>
    : T extends `${string}:${infer P}` ? P : never;

// Dot-path access
type DeepGet<T, P extends string> =
  P extends `${infer K}.${infer R}`
    ? K extends keyof T ? DeepGet<T[K], R> : never
    : P extends keyof T ? T[P] : never;
```

---

## 4. Branded and Nominal Types

TypeScript is structurally typed. Branding introduces nominal-like guarantees via phantom properties.

### 4.1 The Brand Pattern

```typescript
declare const __brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [__brand]: B };

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

### 4.4 Branded Type Template (Cheat Sheet)

```typescript
declare const __brand: unique symbol;
type Brand<T, B extends string> = T & { readonly [__brand]: B };

type UserId = Brand<string, 'UserId'>;
type Email  = Brand<string, 'Email'>;
type USD    = Brand<number, 'USD'>;

function createUserId(input: string): UserId {
  if (!input.match(/^usr_[a-z0-9]+$/)) throw new Error('Invalid UserId');
  return input as UserId;
}
```

### 4.5 Phantom Types for State Machines

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

// Accumulator version (tail-recursive — important for performance)
type Reverse<T extends any[], A extends any[] = []> =
  T extends [infer H, ...infer R] ? Reverse<R, [H, ...A]> : A;
```

### 5.2 Type-Level Path Access

```typescript
type DeepGet<T, P extends string> =
  P extends `${infer K}.${infer Rest}`
    ? K extends keyof T ? DeepGet<T[K], Rest> : never
    : P extends keyof T ? T[P] : never;

type Nested = { user: { profile: { name: string; age: number } } };
type Name = DeepGet<Nested, 'user.profile.name'>; // string
```

### 5.3 Exhaustive Switch with `never`

```typescript
function assertNever(x: never): never {
  throw new Error(`Unexpected value: ${JSON.stringify(x)}`);
}
// In a switch over a discriminated union, the default branch receives `never`
// if all variants are handled. Adding a new variant without a case triggers a compile error.
```

### 5.4 Type-Safe Builder Pattern

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
// new URLBuilder().setHost('localhost').build(); // Error — missing port and protocol
```

### 5.5 Common Type-Level Recipes (Cheat Sheet)

```typescript
// Extract function keys
type FunctionKeys<T> = {
  [K in keyof T]: T[K] extends (...args: any[]) => any ? K : never;
}[keyof T];

// Exhaustive switch guard
function assertNever(x: never): never { throw new Error(`Unexpected: ${x}`); }

// XOR — exactly one of two types
type Without<T, U> = { [K in Exclude<keyof T, keyof U>]?: never };
type XOR<T, U> = (T & Without<U, T>) | (U & Without<T, U>);

// Merge (second wins on conflicts)
type Merge<A, B> = Omit<A, keyof B> & B;

// Promisify object methods
type Promisify<T> = {
  [K in keyof T]: T[K] extends (...args: infer A) => infer R
    ? (...args: A) => Promise<Awaited<R>> : T[K];
};

// IfEquals (used for readonly key detection)
type IfEquals<X, Y, A = X, B = never> =
  (<T>() => T extends X ? 1 : 2) extends (<T>() => T extends Y ? 1 : 2) ? A : B;
```

---

## 6. Recursive Conditional Types (Deep Dive)

### 6.1 Tail-Call Optimization (TS 4.5+)

The recursive call must be in tail position — no wrapping.

```typescript
// Tail-recursive (optimized): accumulator pattern
type Flatten<T extends any[], Acc extends any[] = []> =
  T extends [infer H, ...infer R]
    ? H extends any[] ? Flatten<[...H, ...R], Acc> : Flatten<R, [...Acc, H]>
    : Acc;

// NOT tail-recursive (hits depth ~50)
type FlattenBad<T extends any[]> =
  T extends [infer H, ...infer R]
    ? H extends any[] ? [...FlattenBad<H>, ...FlattenBad<R>] : [H, ...FlattenBad<R>]
    : [];
```

### 6.2 Depth Limiting

```typescript
type DeepPartial<T, Depth extends any[] = [1, 1, 1, 1, 1]> =
  Depth extends [] ? T
    : T extends object ? { [K in keyof T]?: DeepPartial<T[K], Tail<Depth>> } : T;
type Tail<T extends any[]> = T extends [any, ...infer R] ? R : [];
```

### 6.3 JSON Type

```typescript
type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
```

Works because object literal types are lazily evaluated — the compiler does not fully expand `Json`.

### 6.4 Recursion Budget Pattern

```typescript
type MaxDepth = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; // depth 10
type DeepFlatten<T, D extends any[] = MaxDepth> =
  D extends [any, ...infer Rest]
    ? T extends ReadonlyArray<infer U> ? DeepFlatten<U, Rest> : T
    : T;
```

Document the limit. Users can expand the tuple if they need deeper recursion.

---

## 7. Type-Level Arithmetic (Deep Dive)

TypeScript has no native arithmetic at the type level. The workaround: encode numbers as tuple lengths.

```typescript
type BuildTuple<N extends number, Acc extends any[] = []> =
  Acc['length'] extends N ? Acc : BuildTuple<N, [...Acc, unknown]>;

type Add<A extends number, B extends number> =
  [...BuildTuple<A>, ...BuildTuple<B>]['length'] & number;
type Sum = Add<3, 4>; // 7

type Subtract<A extends number, B extends number> =
  BuildTuple<A> extends [...BuildTuple<B>, ...infer R] ? R['length'] & number : never;
type Diff = Subtract<10, 3>; // 7

type Multiply<A extends number, B extends number, Acc extends any[] = []> =
  B extends 0 ? Acc['length'] & number
    : Multiply<A, Subtract<B, 1>, [...Acc, ...BuildTuple<A>]>;
type Product = Multiply<3, 4>; // 12

type IsGreaterThan<A extends number, B extends number> =
  A extends B ? false
    : BuildTuple<A> extends [...BuildTuple<B>, ...infer R]
      ? R extends [any, ...any[]] ? true : false
      : false;
```

**Practical limits:** Breaks above ~1000 due to tuple-length caps. Useful for small constant validation (array lengths, pagination limits, matrix dimensions) — not general-purpose math.

---

## 8. Template Literal Type Parsing: Building a Type-Safe Router (Deep Dive)

```typescript
type ParseRoute<T extends string> =
  T extends `${string}:${infer Param}/${infer Rest}` ? Param | ParseRoute<`/${Rest}`>
    : T extends `${string}:${infer Param}` ? Param : never;

type RouteParams<T extends string> = { [K in ParseRoute<T>]: string };

class Router {
  get<const Path extends string>(path: Path, handler: (params: RouteParams<Path>) => void): this {
    return this;
  }
}

const router = new Router();
router.get('/users/:userId/posts/:postId', (params) => {
  params.userId;  // string
  params.postId;  // string
  // params.invalid; // Error
});
```

### Query String Parsing

```typescript
type ParseQueryString<T extends string> =
  T extends `${infer Param}&${infer Rest}` ? ParseParam<Param> & ParseQueryString<Rest>
    : ParseParam<T>;
type ParseParam<T extends string> =
  T extends `${infer Key}=${infer Value}` ? { [K in Key]: Value }
    : T extends `${infer Key}` ? { [K in Key]: true } : {};

type QS = ParseQueryString<'page=1&limit=10&sort=name'>;
// { page: "1"; limit: "10"; sort: "name" }
```

---

## 9. Higher-Kinded Types (HKT Workarounds) (Deep Dive)

TypeScript cannot express `type Apply<F<_>, A> = F<A>`. Two established workarounds exist.

### 9.1 URI Pattern (fp-ts)

```typescript
interface URItoKind<A> {
  'Option': Option<A>;
  'Array': Array<A>;
}
type URIS = keyof URItoKind<any>;
type Kind<URI extends URIS, A> = URItoKind<A>[URI];

interface Functor<F extends URIS> {
  map: <A, B>(fa: Kind<F, A>, f: (a: A) => B) => Kind<F, B>;
}
```

Consumers register new constructors via declaration merging on `URItoKind`.

### 9.2 Defunctionalization (Effect)

```typescript
interface TypeLambda { readonly In: unknown; readonly Out: unknown; }
interface ArrayLambda extends TypeLambda { readonly Out: Array<this['In']>; }
interface PromiseLambda extends TypeLambda { readonly Out: Promise<this['In']>; }

type Apply<F extends TypeLambda, A> = (F & { readonly In: A })['Out'];
type Test1 = Apply<ArrayLambda, string>;   // string[]
type Test2 = Apply<PromiseLambda, number>; // Promise<number>
```

Exploits `this` type in interfaces — intersecting `F & { In: A }` makes `this['In']` resolve to `A`. More local than the URI pattern but harder to read. Neither substitutes for true HKTs.

**When to use each approach:** The URI pattern (fp-ts style) is better when you need an open, extensible registry of type constructors — consumers add entries via declaration merging. The defunctionalization pattern (Effect style) is better when you want each type lambda to be self-contained and locally defined. The URI pattern is more established in the ecosystem; the defunctionalization pattern avoids a global registry but requires familiarity with `this`-type tricks. In an interview, being able to explain both and articulate the trade-off demonstrates genuine depth.

**Common mistake:** Trying to build HKT abstractions for application code rather than library internals. The cognitive overhead of either pattern is only justified when you are writing a reusable library that needs to be polymorphic over type constructors (e.g., a generic `map` that works over Option, Array, Result). For application-level code, simple generics with concrete types are almost always the right call.

---

## Related Reading

- **Branded types and phantom types** (Section 4) are used extensively for domain modeling in [Database Patterns — Prisma and Drizzle](../06-database-patterns/01-prisma-and-drizzle.md) and for type-safe IDs in [REST API Design — HTTP Semantics and Status Codes](../03-rest-api-design/01-http-semantics-and-status-codes.md)
- **Template literal type parsing** (Section 8) connects to route parameter extraction in [GraphQL — Schema Design and Resolvers](../04-graphql/01-schema-design-and-resolvers.md) and type-safe routing in [REST API Design — API Design Patterns and Versioning](../03-rest-api-design/03-api-design-patterns-and-versioning.md)
- **Recursive conditional types** (Section 6) are the backbone of how Prisma generates types from schema — see [Advanced Type Patterns — How Prisma Types Work](02-advanced-type-patterns.md#7-how-prisma-types-work-deep-dive)
- **Mapped types with key remapping** (Section 2) are applied in [Architecture — Clean Architecture and DDD](../09-architecture-patterns/01-clean-architecture-and-ddd.md) for building typed event maps and repository interfaces
- **Type-level programming foundations** (Section 5) prepare you for the variance and compiler internals discussion in [Advanced Type Patterns — Variance Annotations](02-advanced-type-patterns.md#2-variance-annotations-ts-47)
- For fundamentals that this file builds on (generics, narrowing, utility types), review [Module 00 — TypeScript Essentials](../00-ts-node-fundamentals.md#6-typescript-essentials)
