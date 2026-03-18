---
title: "TypeScript & Node.js Quick Reference"
---

# Conventions

- **Naming**: `camelCase` vars/funcs, `PascalCase` types/classes, `UPPER_SNAKE` constants
- **Strict mode**: `"strict": true` in tsconfig
- **Imports**: ESM (`import/export`), avoid CommonJS in new code
- **Null safety**: prefer `??` (nullish) over `||`, use optional chaining `?.`

# String

All string methods are **non-mutating** -- strings are immutable in JS.

```ts
s.length                    // number (property, not a method)

// Search -- all O(n)
s.includes("x")             // -> boolean
s.startsWith("x")           // -> boolean, optional position arg
s.endsWith("x")             // -> boolean, optional length arg
s.indexOf("x")              // -> number, first index or -1
s.lastIndexOf("x")          // -> number, last index or -1
s.search(/pat/)             // -> number, first regex match index or -1

// Extract
s.at(-1)                    // -> string, supports negative index (last char)
s.slice(1, 4)               // -> string, substring [start, end). Negative ok
s[0]                        // -> string, single char by index (no negative)
s.split(",")                // -> string[], split into array by separator
s.split(",", 3)             // -> string[], limit to 3 results

// Regex
s.match(/(\d+)/g)           // -> string[] | null, all matches (g flag)
s.match(/(\d+)/)            // -> RegExpMatchArray | null, first match + groups
s.matchAll(/(\d+)/g)        // -> IterableIterator, each match with groups
s.replace(/pat/, "x")       // -> string, first match only
s.replace(/pat/g, "x")     // -> string, all matches (regex with g flag)
s.replaceAll("a", "b")     // -> string, all literal occurrences

// Transform
s.trim()                    // -> string, strip whitespace both ends
s.trimStart() / s.trimEnd() // -> string, strip one end
s.toUpperCase()             // -> string
s.toLowerCase()             // -> string
s.padStart(5, "0")          // -> string, "00042" -- pad to length
s.padEnd(10, ".")           // -> string, "hello....."
s.repeat(3)                 // -> string, "abcabcabc"
s.normalize("NFC")          // -> string, Unicode normalization

// Convert
s.charCodeAt(0)             // -> number, UTF-16 code unit (72 for "H")
s.codePointAt(0)            // -> number, full Unicode code point (emoji-safe)
String.fromCharCode(65)     // -> "A"
String.fromCodePoint(0x1F600)  // -> emoji
`Hello ${name}`             // template literal interpolation
```

# Array

**Gotcha**: `.sort()` without a comparator sorts as strings! `[10,2].sort()` -> `[10,2]`.

```ts
arr.length                         // number (property). Can truncate: arr.length = 0

// Transform -- all O(n), all return new arrays
arr.map(x => x * 2)               // -> T[], same length, transformed
arr.filter(x => x > 0)            // -> T[], subset matching predicate
arr.flatMap(x => x.tags)          // -> T[], map then flatten 1 level
arr.flat(depth)                    // -> T[], flatten nested. Infinity for all

// Reduce -- O(n)
arr.reduce((acc, x) => acc + x, 0)      // -> any, fold left with initial value
arr.reduceRight((acc, x) => acc + x, 0) // -> any, fold right

// Search -- O(n) linear scan
arr.find(x => x.id === 1)         // -> T | undefined, first match
arr.findIndex(x => x.id === 1)    // -> number, first index or -1
arr.findLast(fn)                   // -> T | undefined, last match (ES2023)
arr.findLastIndex(fn)              // -> number, from end or -1 (ES2023)
arr.some(fn)                       // -> boolean, true if any match (short-circuits)
arr.every(fn)                      // -> boolean, true if all match (short-circuits)
arr.includes(x)                    // -> boolean, uses SameValueZero (finds NaN)
arr.indexOf(x)                     // -> number, first index or -1 (uses ===)
arr.lastIndexOf(x)                 // -> number, last index or -1
arr.at(-1)                         // -> T | undefined, negative index support (ES2022)

// Mutating -- modify in place, O(1) unless noted
arr.push(x)                        // -> new length. Append to end. O(1) amortized
arr.pop()                           // -> T | undefined. Remove from end. O(1)
arr.unshift(x)                     // -> new length. Prepend to start. O(n) shift
arr.shift()                         // -> T | undefined. Remove from start. O(n) shift
arr.splice(i, deleteCount, ...items) // -> T[], returns removed. Insert/remove at index
arr.sort((a, b) => a - b)          // -> same arr, in-place. O(n log n). MUTATES
arr.reverse()                       // -> same arr, in-place. O(n). MUTATES
arr.fill(val, start?, end?)         // -> same arr, fill range with value. MUTATES
arr.copyWithin(target, start, end)  // -> same arr, copy within itself. MUTATES

// Non-mutating copies (ES2023) -- safe versions of mutating methods
arr.toSorted((a, b) => a - b)     // -> new T[], sorted copy
arr.toReversed()                   // -> new T[], reversed copy
arr.toSpliced(i, 1)               // -> new T[], spliced copy
arr.with(i, newVal)                // -> new T[], single element replaced

// Build & convert
[...a, ...b]                       // -> new T[], spread/concat
arr.slice(start?, end?)            // -> new T[], shallow copy of range. Neg ok
arr.concat(other)                  // -> new T[], non-mutating concat
arr.join(", ")                     // -> string
arr.forEach(fn)                    // -> void, side effects only (can't break out)
Array.from(iterable, mapFn?)       // -> T[], from iterable/array-like + optional map
Array.from({ length: n }, (_, i) => i) // -> [0, 1, ..., n-1]
Array.isArray(x)                   // -> boolean, reliable type check
Array.of(1, 2, 3)                  // -> [1, 2, 3]
structuredClone(arr)               // -> deep clone (handles nested objects)
```

# Object

```ts
Object.keys(o)                     // -> string[], own enumerable keys
Object.values(o)                   // -> V[], own enumerable values
Object.entries(o)                  // -> [string, V][], key-value pairs
Object.fromEntries(entries)        // -> object, inverse of entries()
Object.assign(target, ...sources)  // -> target, shallow merge. Mutates target!
{ ...a, ...b }                     // shallow merge into new object. b overwrites a
Object.hasOwn(obj, "key")          // -> boolean, own property only (ES2022)
"key" in obj                       // -> boolean, includes inherited/prototype props
Object.freeze(obj)                 // -> same obj, shallow immutable (no add/remove/change)
Object.isFrozen(obj)               // -> boolean
Object.keys(o).length === 0        // empty-object check (own enumerable keys only)
structuredClone(obj)                // deep clone (handles Date, Map, Set, ArrayBuffer, etc.)
const { x, y: alias, ...rest } = obj  // destructuring with rename and rest
delete obj.key                     // -> boolean, remove property. O(1) but slow in practice
typeof obj                         // -> "object" (also true for null!)
obj instanceof MyClass             // -> boolean, checks prototype chain
```

# Map / Set

Map: ordered by insertion. Any key type. O(1) get/set/has/delete.

```ts
const m = new Map<K, V>()         // typed map
new Map([["a", 1], ["b", 2]])     // initialize from entries
new Map(Object.entries(obj))       // convert plain object to Map

m.set(k, v)                        // -> Map (chainable). Add or update
m.get(k)                           // -> V | undefined
m.has(k)                           // -> boolean
m.delete(k)                        // -> boolean (true if existed)
m.clear()                          // -> void, remove all entries
m.size                             // number (property)

// Iteration -- insertion order preserved
for (const [k, v] of m) {}        // destructured iteration
m.keys()                           // -> MapIterator<K>
m.values()                         // -> MapIterator<V>
m.entries()                        // -> MapIterator<[K, V]>
m.forEach((val, key, map) => ...)  // callback iteration

Object.fromEntries(m)              // -> plain object (keys become strings)
```

Set: ordered by insertion. O(1) add/has/delete. Values are unique (SameValueZero).

```ts
const s = new Set<T>()            // typed set
new Set([1, 2, 3])                // initialize from iterable
[...new Set(arr)]                  // deduplicate array

s.add(x)                           // -> Set (chainable). No-op if exists
s.has(x)                           // -> boolean
s.delete(x)                        // -> boolean (true if existed)
s.clear()                          // -> void
s.size                             // number (property)

// Iteration
for (const x of s) {}
s.forEach(val => ...)
[...s]                             // -> T[], spread to array

// Set operations (ES2025) -- all return new Set
s.union(other)                     // elements in either
s.intersection(other)              // elements in both
s.difference(other)                // elements in s but not other
s.symmetricDifference(other)       // elements in one but not both
s.isSubsetOf(other)                // -> boolean
s.isSupersetOf(other)              // -> boolean
s.isDisjointFrom(other)            // -> boolean, no overlap
```

# Promise & Async

```ts
async function doWork() {
  try {
    const res = await api.get(url)  // suspends until resolved
    return res.data                 // auto-wrapped in Promise
  } catch (e) { handle(e) }        // catches rejections
  finally { cleanup() }            // always runs
}

// Combinators -- all take iterables of promises
Promise.all([p1, p2])              // -> Promise<T[]>, rejects on first rejection
Promise.allSettled([p1, p2])       // -> Promise<SettledResult[]>, never rejects
Promise.race([p, timeout])         // -> Promise<T>, first to settle (resolve or reject)
Promise.any([p1, p2])              // -> Promise<T>, first to fulfill. AggregateError if all reject

// Construction
Promise.resolve(val)               // -> Promise<T>, wrap value
Promise.reject(err)                // -> Promise<never>, wrap error
Promise.withResolvers<T>()         // -> { promise, resolve, reject } (ES2024)
new Promise<T>((resolve, reject) => { ... })  // manual construction
```

# Number / Math / JSON

```ts
// Parsing -- watch for NaN on invalid input
Number(str)                         // -> number. "" -> 0, "12px" -> NaN
parseInt(s, 10)                     // -> number. "12px" -> 12. ALWAYS pass radix!
parseFloat(s)                       // -> number. "3.14xyz" -> 3.14

// Checking
Number.isNaN(x)                    // -> boolean. Strict: only true for NaN (not "hello")
Number.isFinite(x)                 // -> boolean. False for Infinity, -Infinity, NaN
Number.isInteger(x)                // -> boolean. 5.0 -> true
Number.isSafeInteger(x)            // -> boolean. Within +/- 2^53 - 1

// Formatting
n.toFixed(2)                       // -> string! "3.14". Rounds, returns string not number
n.toLocaleString()                 // -> "1,234.56" (locale-aware formatting)
n.toString(16)                     // -> string in base 16 (hex), 2 (binary), etc.

// Math -- all static methods
Math.max(...arr) / Math.min(...arr) // gotcha: empty arr -> -Infinity / Infinity
Math.floor(x) / Math.ceil(x)       // round down / up
Math.round(x)                      // nearest integer (.5 rounds up)
Math.trunc(x)                      // drop decimal (toward zero, unlike floor)
Math.abs(x) / Math.sign(x)         // absolute value / -1, 0, or 1
Math.random()                       // -> [0, 1). Multiply + floor for ranges
Math.pow(base, exp) / base ** exp   // exponentiation
Math.sqrt(x) / Math.cbrt(x)        // square / cube root
Math.log(x) / Math.log2(x)         // natural log / base-2 log
Math.PI / Math.E                    // constants

// JSON
JSON.stringify(obj)                 // -> string. Drops undefined, functions, symbols
JSON.stringify(obj, null, 2)        // -> string, pretty-printed with 2-space indent
JSON.stringify(obj, replacer)       // replacer: (key, val) => val or string[]
JSON.parse(str)                     // -> any. Throws on invalid JSON!
JSON.parse(str, reviver)            // reviver: (key, val) => val for transforms
structuredClone(obj)                // deep clone. Handles Map, Set, Date, etc. (not JSON)
```

# Date / Timers / URL

```ts
Date.now()                          // -> number, ms since epoch. Fastest timestamp
new Date().toISOString()            // -> "2026-03-17T00:00:00.000Z"
new Date(ms)                        // from epoch ms
new Date("2026-03-17")              // from ISO string (parsed as UTC)
new Date(y, m, d, h, min, s, ms)   // month is 0-indexed! Jan = 0

// Timers
const id = setTimeout(fn, ms)      // -> TimerId. Run once after delay
clearTimeout(id)                    // cancel pending timeout
const id = setInterval(fn, ms)     // -> TimerId. Run repeatedly
clearInterval(id)                   // cancel interval
queueMicrotask(fn)                  // run after current task, before next macrotask

// URL
const u = new URL("https://a.com/path?x=1&y=2")
u.origin                            // -> "https://a.com"
u.pathname                          // -> "/path"
u.searchParams.get("x")            // -> "1" | null
u.searchParams.getAll("x")         // -> string[], for repeated params
u.searchParams.set("y", "2")       // set/overwrite param
u.searchParams.append("z", "3")    // add without overwriting
u.searchParams.has("x")            // -> boolean
u.searchParams.delete("x")         // remove param
u.toString()                        // -> full URL string
new URLSearchParams("a=1&b=2")     // standalone query string builder
encodeURIComponent(s)               // encode for query values (escapes &, =, etc.)
decodeURIComponent(s)               // decode

crypto.randomUUID()                 // -> "a1b2c3d4-..." (v4 UUID)
```

# TypeScript Types

```ts
type A = string | number           // union
type B = X & Y                     // intersection
type C<T> = { data: T }            // generic
type D = [string, number]          // tuple (fixed length + types)

// Utility types
Partial<T>                         // all props optional
Required<T>                        // all props required
Pick<T, "a" | "b">                 // subset of keys only
Omit<T, "c">                       // all keys except these
Record<K, V>                        // { [key: K]: V }
Readonly<T>                         // all props readonly (shallow)
NonNullable<T>                      // remove null | undefined from T
ReturnType<typeof fn>               // infer return type of function
Parameters<typeof fn>               // infer param types as tuple
Awaited<Promise<T>>                 // unwrap Promise to T
Extract<T, U>                       // members of T assignable to U
Exclude<T, U>                       // members of T not assignable to U

// Type narrowing
typeof x === "string"               // narrows to string
Array.isArray(x)                    // narrows to any[]
x instanceof MyClass                // narrows to MyClass
"key" in obj                        // narrows to { key: unknown }
x === null / x === undefined        // narrows null/undefined out

// Custom type guard
function isStr(x: unknown): x is string {
  return typeof x === "string"
}

// Const assertions & enums -- prefer const objects over enum keyword
const Status = { OK: "ok", ERR: "err" } as const
type Status = (typeof Status)[keyof typeof Status]  // "ok" | "err"
```

# Node.js Essentials

```ts
// File I/O (async -- use fs/promises, not fs)
import { readFile, writeFile, readdir, stat, mkdir, rm } from "fs/promises"
const data = await readFile(path, "utf-8")   // -> string
await writeFile(path, content, "utf-8")       // -> void
await mkdir(dir, { recursive: true })         // create nested dirs
await rm(path, { recursive: true, force: true }) // delete file or dir

// Path handling -- always use path module, never string concat
import { join, resolve, basename, dirname, extname, parse } from "path"
join("a", "b", "c.txt")            // -> "a/b/c.txt" (OS-aware separator)
resolve("./rel")                    // -> absolute path
basename("/a/b/c.txt")             // -> "c.txt"
basename("/a/b/c.txt", ".txt")     // -> "c"
dirname("/a/b/c.txt")              // -> "/a/b"
extname("file.ts")                 // -> ".ts"

// Environment
process.env.NODE_ENV ?? "development"  // env vars (always string | undefined)
process.argv                        // [node, script, ...args]
process.cwd()                       // -> string, current working directory
process.exit(1)                     // exit with code (0 = success)

// Event emitter
import { EventEmitter } from "events"
const ee = new EventEmitter()
ee.on("event", handler)            // subscribe (persistent)
ee.once("event", handler)          // subscribe (fires once then removed)
ee.emit("event", data)             // -> boolean (true if listeners existed)
ee.off("event", handler)           // unsubscribe (must be same fn reference)
ee.removeAllListeners("event")     // remove all for this event
```
