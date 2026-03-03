# Module 00: TypeScript & Node.js Fundamentals Refresh

This course is for experts with 10+ years of TypeScript. Before diving into advanced patterns, make sure these fundamentals are rock-solid — interviewers will probe them, and any hesitation on basics undermines your credibility on the advanced stuff.

This is a refresher, not a tutorial. If any section feels unfamiliar rather than "oh right, that," spend time with it before moving on.

---

## 1. JavaScript Engine Internals

### How V8 Executes Your Code

```
Source Code
    ↓
[Parser] → AST (Abstract Syntax Tree)
    ↓
[Ignition] → Bytecode (interpreted, fast startup)
    ↓  ← hot function detected (called many times)
[TurboFan] → Optimized Machine Code (JIT compiled)
    ↓  ← deoptimization (type changed, assumption broken)
[Back to Ignition]
```

Key points you should be able to explain:
- **Ignition** interprets bytecode for fast startup. Not everything gets compiled.
- **TurboFan** optimizes hot functions based on type feedback — assumes types stay stable.
- **Deoptimization** happens when assumptions break (e.g., a function that always received numbers suddenly gets a string). The engine falls back to interpreted bytecode.
- **Hidden classes** (shapes/maps) — V8 creates internal type descriptors for objects. Objects with the same property order share a hidden class, enabling fast property access. Adding properties in different orders creates different hidden classes.

### Memory Model

```
[Stack]          [Heap]
- Primitives     - Objects
- References     - Arrays
- Call frames    - Closures
                 - Strings (usually)
```

- **Primitives** (number, string, boolean, null, undefined, symbol, bigint) stored by value
- **Objects** stored by reference — the variable holds a pointer to the heap
- **Garbage collection**: Mark-and-Sweep (major GC) + Scavenger (minor GC for young generation)

---

## 2. Closures & Scope

You've used closures for a decade. Can you explain them precisely?

```typescript
function createCounter() {
  let count = 0;  // captured in closure — lives as long as the returned function
  return {
    increment: () => ++count,
    getCount: () => count,
  };
}

const counter = createCounter();
counter.increment(); // 1
counter.increment(); // 2
```

A closure is a function bundled with its lexical environment — the variables in scope when the function was defined. The variables aren't copied; the closure holds a reference to the same binding.

### The Classic Gotcha

```typescript
// var is function-scoped, not block-scoped
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // 3, 3, 3 — all share the same i
}

// let is block-scoped — each iteration gets its own binding
for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // 0, 1, 2
}
```

### Scope Chain

```typescript
const global = "g";

function outer() {
  const outerVar = "o";

  function inner() {
    const innerVar = "i";
    // Can access: innerVar, outerVar, global
    // Lookup order: own scope → parent → grandparent → ... → global
  }
}
```

---

## 3. Prototypes & Inheritance

Even with classes, JavaScript uses prototypal inheritance under the hood.

```typescript
class Animal {
  constructor(public name: string) {}
  speak() { return `${this.name} makes a noise`; }
}

class Dog extends Animal {
  speak() { return `${this.name} barks`; }
}

const dog = new Dog("Rex");

// Prototype chain:
// dog → Dog.prototype → Animal.prototype → Object.prototype → null

dog.speak();                              // "Rex barks" (found on Dog.prototype)
dog.hasOwnProperty("name");              // true (found on Object.prototype)
Object.getPrototypeOf(dog) === Dog.prototype; // true
```

### `this` Binding Rules

```typescript
// 1. Regular function: this = caller (or undefined in strict mode)
const obj = {
  name: "Alice",
  greet() { return this.name; },
};
const fn = obj.greet;
fn();          // undefined — lost the binding

// 2. Arrow function: this = enclosing lexical scope (captured at definition)
const obj2 = {
  name: "Bob",
  greet: () => this.name,  // this is NOT obj2 — it's the enclosing scope
};

// 3. Explicit binding
fn.call(obj);       // "Alice"
fn.apply(obj);      // "Alice"
const bound = fn.bind(obj);
bound();            // "Alice"

// 4. new keyword: this = newly created object
```

---

## 4. The Event Loop

You must be able to draw and explain this. Module 02 goes deeper into libuv phases, but you need the mental model first.

```
   ┌──────────────────────────┐
   │        Call Stack         │  ← Executes synchronous code
   └────────────┬─────────────┘
                │ (when empty)
   ┌────────────▼─────────────┐
   │    Microtask Queue        │  ← Promise callbacks, queueMicrotask
   │    (runs ALL before       │     process.nextTick (Node-specific, runs first)
   │     moving to macrotasks) │
   └────────────┬─────────────┘
                │ (when empty)
   ┌────────────▼─────────────┐
   │    Macrotask Queue        │  ← setTimeout, setInterval, I/O callbacks,
   │    (runs ONE, then back   │     setImmediate (Node-specific)
   │     to microtasks)        │
   └───────────────────────────┘
```

```typescript
console.log("1");                          // sync — runs immediately

setTimeout(() => console.log("2"), 0);     // macrotask queue

Promise.resolve().then(() => console.log("3")); // microtask queue

console.log("4");                          // sync — runs immediately

// Output: 1, 4, 3, 2
// Sync first, then ALL microtasks, then one macrotask
```

### Node.js Event Loop Phases

```
   ┌───────────────────────┐
┌─>│        timers          │  setTimeout, setInterval callbacks
│  └───────────┬────────────┘
│  ┌───────────▼────────────┐
│  │    pending callbacks    │  I/O callbacks deferred from previous cycle
│  └───────────┬────────────┘
│  ┌───────────▼────────────┐
│  │      idle, prepare      │  internal use only
│  └───────────┬────────────┘
│  ┌───────────▼────────────┐
│  │         poll            │  retrieve new I/O events, execute I/O callbacks
│  └───────────┬────────────┘
│  ┌───────────▼────────────┐
│  │         check           │  setImmediate callbacks
│  └───────────┬────────────┘
│  ┌───────────▼────────────┐
│  │    close callbacks      │  socket.on('close'), etc.
│  └───────────┘
│           │
└───────────┘  (next iteration)
```

---

## 5. Promises & Async Patterns

### Promise States & Chaining

```typescript
// A promise is in one of three states: pending, fulfilled, rejected
// State transitions are one-way and permanent

const p = new Promise<string>((resolve, reject) => {
  // resolve("value") → fulfilled
  // reject(new Error("reason")) → rejected
  // Can only transition once — subsequent calls are ignored
});

// .then() returns a NEW promise — this is what enables chaining
p.then(v => v.toUpperCase())    // returns Promise<string>
 .then(v => v.length)           // returns Promise<number>
 .catch(err => 0);              // handles any rejection in the chain
```

### Concurrency Patterns

```typescript
// Promise.all — fail-fast on first rejection
const [a, b, c] = await Promise.all([fetchA(), fetchB(), fetchC()]);

// Promise.allSettled — wait for all, never rejects
const results = await Promise.allSettled([fetchA(), fetchB()]);
// [{status: "fulfilled", value: ...}, {status: "rejected", reason: ...}]

// Promise.race — first to settle wins (fulfilled OR rejected)
const fastest = await Promise.race([fetchA(), timeout(5000)]);

// Promise.any — first to fulfill wins (ignores rejections until all reject)
const first = await Promise.any([fetchA(), fetchB()]);
```

### Async/Await Error Handling

```typescript
// try/catch is the standard pattern
async function fetchUser(id: string) {
  try {
    const res = await fetch(`/api/users/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    // Network errors, HTTP errors, JSON parse errors all land here
    throw new Error(`Failed to fetch user ${id}: ${err}`);
  }
}
```

---

## 6. TypeScript Essentials

### Type Narrowing

```typescript
// typeof guard
function process(value: string | number) {
  if (typeof value === "string") {
    value.toUpperCase();  // TS knows it's string here
  }
}

// in guard
function handle(shape: Circle | Rectangle) {
  if ("radius" in shape) {
    // shape is Circle
  }
}

// Discriminated unions — the most important pattern
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: string };

function handle(result: Result<User>) {
  if (result.success) {
    result.data;   // TS knows this exists
  } else {
    result.error;  // TS knows this exists
  }
}
```

### Generics Fundamentals

```typescript
// Basic generic
function identity<T>(value: T): T { return value; }

// Constrained generic
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Generic with default
type Container<T = string> = { value: T };

// Multiple type parameters
function merge<T, U>(a: T, b: U): T & U {
  return { ...a, ...b };
}
```

### Utility Types You Should Know Cold

```typescript
Partial<T>        // All properties optional
Required<T>       // All properties required
Readonly<T>       // All properties readonly
Pick<T, K>        // Subset of properties
Omit<T, K>        // All except specified properties
Record<K, V>      // Object with keys K and values V
Extract<T, U>     // Members of T assignable to U
Exclude<T, U>     // Members of T not assignable to U
NonNullable<T>    // Remove null and undefined
ReturnType<T>     // Return type of a function type
Parameters<T>     // Tuple of parameter types
Awaited<T>        // Unwrap Promise type
```

---

## 7. Module System

### ESM vs CommonJS

```typescript
// ESM (modern, what you should use)
import { readFile } from 'fs/promises';
import express from 'express';
export function handler() { }
export default app;

// CommonJS (legacy, still in many Node.js projects)
const { readFile } = require('fs/promises');
const express = require('express');
module.exports = { handler };
module.exports = app;
```

Key differences:
- ESM is statically analyzable (imports at top level, tree-shakeable)
- CommonJS is dynamic (require can be conditional, inside functions)
- ESM uses `import.meta.url` instead of `__dirname`/`__filename`
- In `package.json`: `"type": "module"` for ESM, `"type": "commonjs"` or omit for CJS

### Package.json Essentials

```json
{
  "name": "my-app",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "exports": {
    ".": { "import": "./dist/index.js", "require": "./dist/index.cjs" },
    "./utils": "./dist/utils.js"
  },
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/index.ts",
    "test": "vitest"
  },
  "engines": { "node": ">=20" }
}
```

---

## 8. Error Handling Patterns

### Error Types

```typescript
// Built-in error types
new Error("generic error");
new TypeError("expected string, got number");
new RangeError("index out of bounds");
new SyntaxError("invalid JSON");

// Custom error classes
class AppError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code: string,
  ) {
    super(message);
    this.name = "AppError";
  }
}

class NotFoundError extends AppError {
  constructor(resource: string, id: string) {
    super(`${resource} ${id} not found`, 404, "NOT_FOUND");
  }
}
```

### Error Handling Best Practices

```typescript
// Catch specific errors, not everything
try {
  await db.query(sql);
} catch (err) {
  if (err instanceof DatabaseError) {
    // handle DB-specific error
  }
  throw err;  // re-throw unknown errors
}

// Never swallow errors silently
try { ... } catch (err) { /* DON'T DO THIS */ }

// Operational vs programmer errors
// Operational: expected failures (network timeout, invalid input) — handle gracefully
// Programmer: bugs (null reference, wrong type) — crash and fix the code
```

---

## 9. Node.js Core Concepts

### Streams

```typescript
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import { createGzip } from 'zlib';

// Pipe: read → transform → write (backpressure handled automatically)
await pipeline(
  createReadStream('input.txt'),
  createGzip(),
  createWriteStream('input.txt.gz'),
);

// Stream types: Readable, Writable, Transform, Duplex
```

### Buffer & Encoding

```typescript
// Buffers are fixed-length byte arrays for binary data
const buf = Buffer.from("hello", "utf-8");
buf.toString("hex");     // "68656c6c6f"
buf.toString("base64");  // "aGVsbG8="

// ArrayBuffer and TypedArrays for performance-sensitive work
const arr = new Uint8Array(1024);
```

### Process & Environment

```typescript
process.env.NODE_ENV          // environment variables
process.argv                  // command-line arguments
process.cwd()                 // current working directory
process.exit(1)               // exit with code
process.on('uncaughtException', handler);    // last resort
process.on('unhandledRejection', handler);   // unhandled promise rejections
```

---

## 10. Testing Fundamentals

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('UserService', () => {
  let service: UserService;
  let mockDb: MockDB;

  beforeEach(() => {
    mockDb = { query: vi.fn() };
    service = new UserService(mockDb);
  });

  it('should find user by id', async () => {
    mockDb.query.mockResolvedValue({ id: '1', name: 'Alice' });

    const user = await service.findById('1');

    expect(user.name).toBe('Alice');
    expect(mockDb.query).toHaveBeenCalledWith(
      expect.stringContaining('SELECT'),
      ['1'],
    );
  });

  it('should throw for missing user', async () => {
    mockDb.query.mockResolvedValue(null);

    await expect(service.findById('999'))
      .rejects.toThrow(NotFoundError);
  });
});
```

---

## 11. Quick Checklist

Before starting Module 01, you should be able to answer these without hesitation:

- [ ] What are the V8 optimization tiers and when does deoptimization happen?
- [ ] Explain closures — how do they capture variables?
- [ ] What's the difference between `==` and `===`? (Trick question at senior level — you should say you never use `==`)
- [ ] Draw the event loop. Where do microtasks run? Where do macrotasks run?
- [ ] What's the output order of `console.log`, `setTimeout`, `Promise.resolve().then()`?
- [ ] Explain `this` binding for regular functions, arrow functions, and class methods
- [ ] What's the prototype chain for `new Dog()` where `Dog extends Animal`?
- [ ] Explain `Promise.all` vs `Promise.allSettled` vs `Promise.race` vs `Promise.any`
- [ ] What's a discriminated union and why is it the most important TS pattern?
- [ ] What's the difference between ESM and CommonJS?
- [ ] What are Node.js streams and why does backpressure matter?

If any of these gave you pause, review that section before moving on.

---

## Related Reading

This module is the prerequisite for the entire course. Every subsequent module assumes fluency with the concepts covered here. Specific connections:

- **Closures and scope** (Section 2) underpin how middleware chains work in [REST API Design — HTTP Semantics](03-rest-api-design/01-http-semantics-and-status-codes.md) and how factory patterns are used in [Architecture — Clean Architecture and DDD](09-architecture-patterns/01-clean-architecture-and-ddd.md)
- **The event loop** (Section 4) is covered in full depth in [Node.js Runtime — Event Loop and Task Queues](02-node-runtime/01-event-loop-and-task-queues.md), including libuv phases, starvation, and `AsyncLocalStorage`
- **Promises and async patterns** (Section 5) are the foundation for [Node.js Runtime — Threading and Process Management](02-node-runtime/02-threading-and-process-management.md) and queue-based patterns in [Performance — Caching and Redis](08-performance-scaling/01-caching-and-redis.md)
- **TypeScript essentials** (Section 6) — generics, narrowing, and discriminated unions — are taken much further in [TypeScript Advanced — Conditional and Mapped Types](01-typescript-advanced/01-conditional-and-mapped-types.md)
- **Error handling patterns** (Section 8) connect directly to [REST API Design — API Design Patterns and Versioning](03-rest-api-design/03-api-design-patterns-and-versioning.md) (RFC 9457 error format) and [Architecture — Clean Architecture and DDD](09-architecture-patterns/01-clean-architecture-and-ddd.md) (error handling architecture)
- **Streams** (Section 9) are explored deeply in [Node.js Runtime — Memory, Streams, and Runtime Internals](02-node-runtime/03-memory-streams-and-runtime-internals.md) and applied in [Performance — Caching and Redis](08-performance-scaling/01-caching-and-redis.md) (streaming large payloads, SSE)
- **Testing fundamentals** (Section 10) are the basis for everything in [Testing — Vitest and Unit Testing](07-testing/01-vitest-and-unit-testing.md)

## Practice Suggestions

These exercises reinforce the fundamentals and help you identify any gaps before moving to advanced modules:

1. **Event loop prediction**: Write 10 snippets mixing `setTimeout`, `setImmediate`, `process.nextTick`, `Promise.resolve().then()`, and synchronous code. Predict the output order, then run them to verify. Get comfortable explaining _why_ each ordering occurs.
2. **Prototype chain exploration**: Create a 3-level class hierarchy. Use `Object.getPrototypeOf()` and `hasOwnProperty()` to walk the chain manually. Override a method at each level and verify lookup order.
3. **Closure memory exercise**: Create a closure that captures a large array. Use `process.memoryUsage()` to observe heap growth. Then null out the reference and force GC (`--expose-gc` flag) to verify the closure's captured scope is released.
4. **Promise combinators**: Build a `fetchWithFallback(urls: string[])` that tries each URL in sequence (not parallel) and returns the first successful response. Then build a `fetchWithTimeout(url, ms)` using `Promise.race`.
5. **Custom error hierarchy**: Implement `AppError`, `NotFoundError`, `ValidationError`, and `AuthorizationError` with proper `instanceof` checks, status codes, and error codes. Write a central Express error handler that switches on error type.
6. **Stream pipeline**: Build a CLI tool that reads a large CSV from stdin, filters rows based on a column value, transforms a field, and writes JSON to stdout — all using `pipeline()` with Transform streams. Verify it handles backpressure by piping through `pv` (pipe viewer).

## Next Steps

You're ready for [Module 01: TypeScript Advanced Patterns](01-typescript-advanced/README.md) — conditional types, mapped types, template literals, branded types, and type-level programming.
