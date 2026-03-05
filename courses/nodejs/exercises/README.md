# Node.js / TypeScript Interview Exercises

Core TypeScript and Node.js exercises for interview prep. These practice the **language fundamentals and runtime patterns** that come up in coding screens and live interviews — no npm dependencies, just TypeScript and the Node.js standard library.

Work through these **before** the module-specific examples, which assume fluency with these patterns.

---

## Files

| File | Topic | Key Patterns |
|------|-------|-------------|
| `01-types-and-generics.ts` | TypeScript Type System | generics, mapped types, branded types, conditional types |
| `02-closures-and-functions.ts` | Functions & HOFs | closures, memoize, debounce, pipe/compose, Map iteration order |
| `03-async-patterns.ts` | Promises & Concurrency | Promise combinators, concurrency pools, circuit breaker, event loop |
| `04-data-structures.ts` | Classic Interview Problems | deep clone, trie, flatten, LFU cache, merge k sorted |
| `05-node-runtime.ts` | Node.js Specific Patterns | EventEmitter, streams, graceful shutdown, AsyncLocalStorage, workers |
| `06-leetcode-patterns.ts` | Classic Algorithms | two sum, BFS/DFS, sliding window, DP, two-pointer |

## How to Use

```bash
# Run a file to see which exercises are not yet implemented
npx tsx exercises/01-types-and-generics.ts

# Implement the TODO stubs until all tests pass
npx tsx exercises/02-closures-and-functions.ts
```

Each file has 6 exercises with:
- A banner comment explaining the problem
- `RELATED READING` links to course modules
- Requirements as bullet points
- Hints with code patterns
- Skeleton code with `throw new Error("Not implemented")` stubs
- A test runner at the bottom that prints pass/fail counts

Exercise 1 in each file is **fully implemented** as a worked example.

## Difficulty Progression

1. **Types & Generics** — TypeScript's type system as a language. If you can write these types from scratch, you understand generics deeply.
2. **Closures & Functions** — Higher-order functions, memoization, rate limiting. The patterns behind middleware and decorator libraries.
3. **Async Patterns** — Promise combinators, concurrency control, circuit breakers. Essential for any Node.js backend interview.
4. **Data Structures** — Classic whiteboard problems implemented in TypeScript. Trie, LFU cache, merge k sorted arrays.
5. **Node Runtime** — Node.js-specific patterns: EventEmitter, streams, graceful shutdown, worker threads. Shows you understand the platform, not just the language.

## Related Course Modules

Each exercise file references specific course modules for deeper reading. Here's the full mapping:

| Exercise File | Primary Modules |
|--------------|----------------|
| `01-types-and-generics.ts` | `../01-typescript-advanced/01-conditional-and-mapped-types.md`, `../01-typescript-advanced/02-advanced-type-patterns.md` |
| `02-closures-and-functions.ts` | `../00-ts-node-fundamentals.md`, `../10-interview-prep/01-interview-fundamentals.md` |
| `03-async-patterns.ts` | `../00-ts-node-fundamentals.md`, `../02-node-runtime/01-event-loop-and-task-queues.md` |
| `04-data-structures.ts` | `../10-interview-prep/01-interview-fundamentals.md` |
| `05-node-runtime.ts` | `../02-node-runtime/01-event-loop-and-task-queues.md`, `../02-node-runtime/02-threading-and-process-management.md`, `../02-node-runtime/03-memory-streams-and-runtime-internals.md` |

## Requirements

- Node.js 18+ (for `AsyncLocalStorage`, `worker_threads`, etc.)
- `tsx` for running TypeScript directly: `npm install -g tsx` or use `npx tsx`
- No other dependencies needed
