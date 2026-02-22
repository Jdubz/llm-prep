# Deep Dive: Type-Level Programming and Compiler Internals

> Beyond patterns -- into the machinery.

---

## Table of Contents

1. [Type-Level Arithmetic](#1-type-level-arithmetic)
2. [Higher-Kinded Types (HKT Workarounds)](#2-higher-kinded-types-hkt-workarounds)
3. [Type-Safe ORMs: How Prisma Types Work](#3-type-safe-orms-how-prisma-types-work)
4. [Recursive Conditional Types](#4-recursive-conditional-types)
5. [TypeScript Compiler Internals](#5-typescript-compiler-internals)
6. [Covariance and Contravariance in Practice](#6-covariance-and-contravariance-in-practice)
7. [Template Literal Type Parsing: Building a Type-Safe Router](#7-template-literal-type-parsing-building-a-type-safe-router)
8. [Performance Considerations](#8-performance-considerations)

---

## 1. Type-Level Arithmetic

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

**Practical limits:** Breaks above ~1000 due to tuple-length caps. Useful for small constant validation (array lengths, pagination limits, matrix dimensions) -- not general-purpose math.

---

## 2. Higher-Kinded Types (HKT Workarounds)

TypeScript cannot express `type Apply<F<_>, A> = F<A>`. Two established workarounds exist.

### 2.1 URI Pattern (fp-ts)

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

### 2.2 Defunctionalization (Effect)

```typescript
interface TypeLambda { readonly In: unknown; readonly Out: unknown; }
interface ArrayLambda extends TypeLambda { readonly Out: Array<this['In']>; }
interface PromiseLambda extends TypeLambda { readonly Out: Promise<this['In']>; }

type Apply<F extends TypeLambda, A> = (F & { readonly In: A })['Out'];
type Test1 = Apply<ArrayLambda, string>;   // string[]
type Test2 = Apply<PromiseLambda, number>; // Promise<number>
```

Exploits `this` type in interfaces -- intersecting `F & { In: A }` makes `this['In']` resolve to `A`. More local than the URI pattern but harder to read. Neither substitutes for true HKTs.

---

## 3. Type-Safe ORMs: How Prisma Types Work

### 3.1 Code Generation, Not Inference

Prisma runs `prisma generate` to emit `.d.ts` files from the `.prisma` schema: model types, input types for every query shape, and a fully-typed `PrismaClient`.

### 3.2 The Select/Include Pattern

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

### 3.3 Takeaways

1. **Generate types from schema** -- do not try to infer everything purely at the type level.
2. **Use const generics** for argument inference: `function query<const T extends Select>(select: T): Payload<T>`.
3. **Recursive mapped types** for nested structures -- but watch recursion depth.

---

## 4. Recursive Conditional Types

### 4.1 Tail-Call Optimization (TS 4.5+)

The recursive call must be in tail position -- no wrapping.

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

### 4.2 Depth Limiting

```typescript
type DeepPartial<T, Depth extends any[] = [1, 1, 1, 1, 1]> =
  Depth extends [] ? T
    : T extends object ? { [K in keyof T]?: DeepPartial<T[K], Tail<Depth>> } : T;
type Tail<T extends any[]> = T extends [any, ...infer R] ? R : [];
```

### 4.3 JSON Type

```typescript
type Json = string | number | boolean | null | Json[] | { [key: string]: Json };
```

Works because object literal types are lazily evaluated -- the compiler does not fully expand `Json`.

---

## 5. TypeScript Compiler Internals

### 5.1 Type Inference via Unification

For `identity(42)`: create fresh `T`, constrain `T >= 42`, resolve to literal `42`. For `merge('hello', 42)`: constraints from both args yield `T = 'hello' | 42` (union of lower bounds).

### 5.2 Structural Checking

`A extends B` checks that for every property in `B`, `A` has a compatible one. Extra properties in `A` are fine (structural subtyping). Excess property checking only applies to fresh object literals -- a separate syntactic check.

### 5.3 The Pipeline

**Scanner** (tokens) -> **Parser** (AST) -> **Binder** (symbols) -> **Type Checker** (types) -> **Emitter** (JS)

The type checker uses lazy evaluation (on-demand with caching), context-sensitive typing (callback params from context), widening (`let x = 'hello'` becomes `string`), and narrowing (control flow analysis).

### 5.4 Control Flow Analysis

The compiler maintains a flow graph tracking narrowed types. This analysis is **intraprocedural** -- it does not cross function boundaries. Type guard functions (`x is T`) bridge the gap.

### 5.5 Type Instantiation

`Promise<string>` creates a cached instantiation. Each unique type-argument combination is a new entry. Deep generic hierarchies with many type params create exponential instantiation counts -- the primary cause of slow TypeScript projects.

---

## 6. Covariance and Contravariance in Practice

### 6.1 Function Types

```typescript
type Handler<T> = (event: T) => void;
// T is contravariant. Handler<Animal> assignable to Handler<Dog>, not reverse.
```

### 6.2 Arrays Are Covariant (Unsoundly)

```typescript
declare let animals: Animal[]; declare let dogs: Dog[];
animals = dogs;                    // OK but unsound
animals.push({ name: 'Cat' });    // Pushes non-Dog into Dog[]
```

`readonly Animal[]` fixes this -- no mutation possible.

### 6.3 Quick Reference

| Position | Variance | Example |
|----------|----------|---------|
| Return type | Covariant | `() => Dog` assignable to `() => Animal` |
| Parameter | Contravariant | `(x: Animal) => void` assignable to `(x: Dog) => void` |
| Both | Invariant | `{ get(): T; set(v: T): void }` |
| Readonly prop | Covariant | `{ readonly value: Dog }` assignable to `{ readonly value: Animal }` |
| Mutable prop | Invariant | `{ value: Dog }` NOT assignable to `{ value: Animal }` |

---

## 7. Template Literal Type Parsing: Building a Type-Safe Router

### 7.1 Parse and Build

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

### 7.2 Query String Parsing

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

## 8. Performance Considerations

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

**Deep intersections:** `A & B & C & D & E` creates nested anonymous types. Use `interface Result extends A, B, C, D, E {}` -- compiler caches the flat structure.

**Distributive types over large unions:** 1000-member union through a conditional = 1000 instantiations.

**Excessive generic chaining:** Each `.method<T>()` in a builder chain creates a new instantiation of the full generic stack.

### 8.4 Optimization Strategies

- Prefer interfaces over type intersections for object shapes
- Eliminate unnecessary generics (if a type param appears once and is not needed for inference, use the concrete type)
- Break large types into smaller cached intermediates
- Use project references (`composite: true`) for incremental builds in monorepos
- `skipLibCheck: true` skips `.d.ts` checking -- faster CI but masks declaration errors

### 8.5 Recursion Budget Pattern

```typescript
type MaxDepth = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; // depth 10
type DeepFlatten<T, D extends any[] = MaxDepth> =
  D extends [any, ...infer Rest]
    ? T extends ReadonlyArray<infer U> ? DeepFlatten<U, Rest> : T
    : T;
```

Document the limit. Users can expand the tuple if they need deeper recursion.

### 8.6 Project References in Detail

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
2. **Declaration emit caching**: `.d.ts` files act as boundaries -- downstream projects never re-check upstream source files.
3. **Parallel builds**: `tsc --build` compiles independent projects concurrently.

The tradeoff: you must maintain `references` arrays and ensure `declaration` emit. For projects already using a monorepo tool (Nx, Turborepo), this often integrates cleanly.

### 8.7 When Type Complexity Is a Code Smell

Not every type-level trick belongs in production code. Signals that type complexity has become a liability:

- **Editor lag** exceeding 2-3 seconds for autocompletion on a typed function call
- **Error messages** spanning more than 10 lines of nested generics that no team member can parse
- **Type-only changes** triggering full project rebuilds because a deeply nested conditional type changed
- **`any` casts** proliferating downstream because consumers cannot satisfy the constraint

The pragmatic response: push complex inference into code-generated types (like Prisma does), expose simple generic interfaces to consumers, and reserve type-level programming for library internals where the complexity is amortized across many call sites.
