# Cheat Sheet: TypeScript Advanced Patterns

Quick-reference for type-level patterns. No explanations -- just recipes.

---

## Utility Types Reference

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

## Conditional Type Patterns

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

## Mapped Type Patterns

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
// Deep readonly / partial
type DeepReadonly<T> = T extends Function ? T
  : T extends object ? { readonly [K in keyof T]: DeepReadonly<T[K]> } : T;
type DeepPartial<T> = T extends Function ? T
  : T extends object ? { [K in keyof T]?: DeepPartial<T[K]> } : T;
// Make specific keys optional / required
type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
type RequiredBy<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;
```

---

## Branded Type Template

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

---

## Common Type-Level Recipes

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

// Tuple operations
type Head<T extends any[]> = T extends [infer H, ...any[]] ? H : never;
type Tail<T extends any[]> = T extends [any, ...infer R] ? R : [];
type Last<T extends any[]> = T extends [...any[], infer L] ? L : never;
type Reverse<T extends any[], A extends any[] = []> =
  T extends [infer H, ...infer R] ? Reverse<R, [H, ...A]> : A;

// Extract function keys
type FunctionKeys<T> = {
  [K in keyof T]: T[K] extends (...args: any[]) => any ? K : never;
}[keyof T];

// Exhaustive switch guard
function assertNever(x: never): never { throw new Error(`Unexpected: ${x}`); }

// XOR -- exactly one of two types
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

## Variance Quick Reference

| Annotation | Meaning | Safe for |
|------------|---------|----------|
| `out T` | Covariant | Return types, readonly properties |
| `in T` | Contravariant | Parameter types |
| `in out T` | Invariant | Mutable properties, bidirectional use |

---

## Key tsconfig Flags

```jsonc
{
  "strict": true,
  "noUncheckedIndexedAccess": true,
  "exactOptionalPropertyTypes": true,
  "noPropertyAccessFromIndexSignature": true,
  "verbatimModuleSyntax": true
}
```
