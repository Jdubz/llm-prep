---
title: "TypeScript & Node.js Quick Reference"
---

# Conventions

- **Naming**: `camelCase` vars/funcs, `PascalCase` types/classes, `UPPER_SNAKE` constants
- **Strict mode**: `"strict": true` in tsconfig
- **Imports**: ESM (`import/export`), avoid CommonJS in new code
- **Null safety**: prefer `??` (nullish) over `||`, use optional chaining `?.`

# string

```ts
s.split(",")            // string[]
s.trim() / s.trimStart()
s.startsWith("x")       // boolean
s.includes("x")         // boolean
s.replace(/pat/g, "x")  // regex replace
s.padStart(5, "0")      // "00042"
`Hello ${name}`         // template literal
s.slice(1, 4)           // substring
```

# Array

```ts
arr.map(x => x * 2)       // transform
arr.filter(x => x > 0)    // subset
arr.reduce((acc, x) => acc + x, 0)
arr.find(x => x.id === 1) // first match | undefined
arr.some(fn) / arr.every(fn)  // boolean tests
arr.flat(Infinity)         // flatten nested
arr.includes(x)            // boolean
[...a, ...b]               // spread / concat
arr.sort((a, b) => a - b)  // in-place numeric sort
```

# Object

```ts
Object.keys(o)          // string[]
Object.values(o)        // V[]
Object.entries(o)       // [string, V][]
Object.fromEntries(entries)
{ ...a, ...b }          // shallow merge
const { x, y: alias } = obj  // destructuring
```

# Map / Set

```ts
const m = new Map<K, V>()
m.set(k, v) / m.get(k) / m.has(k) / m.delete(k)
m.size                   // count
for (const [k, v] of m) // iterate

const s = new Set<T>()
s.add(x) / s.has(x) / s.delete(x)
[...new Set(arr)]        // deduplicate
```

# Promise & Async

```ts
async function fetch() {
  try {
    const res = await api.get(url)
    return res.data
  } catch (e) { handle(e) }
  finally { cleanup() }
}

Promise.all([p1, p2])         // fail-fast parallel
Promise.allSettled([p1, p2])  // always resolves
Promise.race([p, timeout])    // first to settle
```

# TypeScript Types

```ts
type A = string | number       // union
type B = X & Y                 // intersection
type C<T> = { data: T }        // generic

// Utility types
Partial<T>         // all optional
Required<T>        // all required
Pick<T, "a" | "b"> // subset of keys
Omit<T, "c">       // exclude keys
Record<K, V>       // { [key: K]: V }
Readonly<T>        // immutable
ReturnType<typeof fn>
Extract<T, U> / Exclude<T, U>

// Type guards
function isStr(x: unknown): x is string {
  return typeof x === "string"
}

// Enums -- prefer const objects
const Status = { OK: "ok", ERR: "err" } as const
type Status = (typeof Status)[keyof typeof Status]
```

# Node.js Essentials

```ts
// File I/O
import { readFile, writeFile } from "fs/promises"
const data = await readFile(path, "utf-8")

// Path handling
import { join, resolve, basename } from "path"

// Environment
process.env.NODE_ENV ?? "development"
process.exit(1)

// Event emitter
emitter.on("event", handler)
emitter.emit("event", data)
```
