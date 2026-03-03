# 01 — React Rendering and Optimization

> Re-render triggers, memoization, keys, reconciliation, and concurrent features.

---

## Table of Contents

1. [Why React Re-Renders: The Complete Mental Model](#why-react-re-renders-the-complete-mental-model)
2. [The Render Phase vs. The Commit Phase](#the-render-phase-vs-the-commit-phase)
3. [State Batching](#state-batching)
4. [React.memo](#reactmemo)
5. [useMemo](#usememo)
6. [useCallback](#usecallback)
7. [React Compiler (React 19)](#react-compiler-react-19)
8. [Keys and Reconciliation](#keys-and-reconciliation)
9. [startTransition and useDeferredValue](#starttransition-and-usedeferredvalue)
10. [Memoization Decision Flowchart](#memoization-decision-flowchart)
11. [Common Re-Render Causes and Fixes](#common-re-render-causes-and-fixes)
12. [Rules of Thumb](#rules-of-thumb)

---

## Why React Re-Renders: The Complete Mental Model

A React component re-renders in exactly three situations:

1. **Its state changes** (`useState` setter, `useReducer` dispatch)
2. **Its parent re-renders** (regardless of whether props changed)
3. **A context it consumes changes** (any consumer re-renders when the provider value changes)

That second point is the one most developers get wrong. Props changing does **not** trigger a re-render. The parent re-rendering triggers the child re-render, and new props are computed as a side effect of that process.

```tsx
function Parent() {
  const [count, setCount] = useState(0);

  // Child re-renders every time Parent re-renders,
  // even though "hello" never changes.
  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>Increment</button>
      <Child greeting="hello" />
    </>
  );
}

function Child({ greeting }: { greeting: string }) {
  console.log("Child rendered"); // logs on every Parent state change
  return <p>{greeting}</p>;
}
```

---

## The Render Phase vs. The Commit Phase

Understanding the two-phase model is critical:

- **Render phase**: React calls your component functions, builds a new virtual DOM tree, and diffs it against the previous tree. This is pure computation — no DOM mutations.
- **Commit phase**: React applies the minimal set of DOM mutations needed. This is where the browser actually updates.

A "wasted render" means the render phase ran but the commit phase found nothing to change. The render phase itself has a cost — function calls, hook evaluations, JSX allocation — but it is often cheaper than developers assume.

---

## State Batching

React 18+ batches all state updates automatically, including those inside `setTimeout`, promises, and native event handlers. This was a significant change from React 17, which only batched inside React event handlers.

```tsx
function BatchingDemo() {
  const [a, setA] = useState(0);
  const [b, setB] = useState(0);

  const handleClick = () => {
    // React 18: single re-render (batched)
    // React 17: two re-renders
    setA(1);
    setB(2);
  };

  const handleAsync = async () => {
    const data = await fetchSomething();
    // React 18: still batched into a single re-render
    // React 17: two re-renders
    setA(data.a);
    setB(data.b);
  };

  return <div onClick={handleClick}>...</div>;
}
```

To opt out of batching (rare), use `flushSync`:

```tsx
import { flushSync } from "react-dom";

function handleClick() {
  flushSync(() => setA(1)); // commits immediately
  flushSync(() => setB(2)); // commits immediately
}
```

---

## React.memo

`React.memo` is a higher-order component that skips re-rendering when props are shallowly equal to the previous render's props.

```tsx
const ExpensiveList = React.memo(function ExpensiveList({
  items,
  onSelect,
}: {
  items: Item[];
  onSelect: (id: string) => void;
}) {
  return (
    <ul>
      {items.map(item => (
        <li key={item.id} onClick={() => onSelect(item.id)}>
          {item.name}
        </li>
      ))}
    </ul>
  );
});
```

### How Shallow Comparison Works

`React.memo` uses `Object.is` for each prop. For primitives this is a value comparison. For objects, arrays, and functions, this is a **referential identity** check.

```tsx
// This memo is USELESS because `style` is a new object every render:
function Parent() {
  return <MemoizedChild style={{ color: "red" }} />;
  // { color: "red" } !== { color: "red" } (different references)
}

// Fix: stable reference
const style = { color: "red" }; // module-level constant
function Parent() {
  return <MemoizedChild style={style} />;
}
```

### Custom Comparison Function

```tsx
const Chart = React.memo(
  function Chart({ data, config }: ChartProps) {
    // expensive rendering
    return <canvas />;
  },
  (prevProps, nextProps) => {
    // Return true to SKIP re-render (opposite of shouldComponentUpdate)
    return (
      prevProps.data.length === nextProps.data.length &&
      prevProps.data.every((d, i) => d.id === nextProps.data[i].id) &&
      prevProps.config.theme === nextProps.config.theme
    );
  }
);
```

### When React.memo Hurts

1. **Comparison cost exceeds render cost**: If the component is cheap to render but has many props, the shallow comparison on every render may cost more than just re-rendering.
2. **Props always change**: If a parent always passes new object/array/function references, memo does the comparison and then re-renders anyway — strictly worse than no memo.
3. **Premature memoization**: Adds cognitive overhead and code complexity for no measurable gain.

**Rule of thumb**: Profile first. Apply `React.memo` to components that are expensive to render AND receive stable (or stabilizable) props.

---

## useMemo

`useMemo` caches a computed value between re-renders when dependencies haven't changed.

```tsx
function SearchResults({ query, items }: { query: string; items: Item[] }) {
  // Only recomputes when `query` or `items` changes (by reference)
  const filtered = useMemo(
    () => items.filter(item =>
      item.name.toLowerCase().includes(query.toLowerCase())
    ),
    [query, items]
  );

  return <ItemList items={filtered} />;
}
```

### Two Distinct Use Cases

**1. Expensive computation caching**

```tsx
const sortedData = useMemo(() => {
  // O(n log n) sort — worth memoizing if `data` is large
  return [...data].sort((a, b) => complexComparator(a, b));
}, [data]);
```

**2. Referential stability for downstream memoization**

```tsx
function Parent({ userId }: { userId: string }) {
  const [count, setCount] = useState(0);

  // Without useMemo, this is a new object every render,
  // breaking React.memo on MemoizedChild
  const config = useMemo(
    () => ({ userId, theme: "dark" }),
    [userId]
  );

  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>{count}</button>
      <MemoizedChild config={config} />
    </>
  );
}
```

### Dependency Gotchas

```tsx
// BUG: `options` is a new object every render, so this useMemo
// recomputes every render — completely defeating the purpose
function Component({ id }: { id: string }) {
  const options = { id, limit: 10 };

  const result = useMemo(() => expensiveComputation(options), [options]);
  // `options` is a new reference every render -> memo never caches
}

// FIX: depend on primitive values
function Component({ id }: { id: string }) {
  const result = useMemo(
    () => expensiveComputation({ id, limit: 10 }),
    [id] // primitive — stable between renders when value is the same
  );
}
```

### useMemo Is Not a Semantic Guarantee

React's docs explicitly state that `useMemo` is a performance optimization, not a semantic guarantee. React may discard cached values to free memory (e.g., offscreen components). Your code must work correctly even if `useMemo` recomputes on every render.

---

## useCallback

`useCallback` is syntactic sugar for `useMemo(() => fn, deps)`. It memoizes a function's referential identity.

```tsx
// These are equivalent:
const handleClick = useCallback((id: string) => {
  selectItem(id);
}, [selectItem]);

const handleClick = useMemo(() => {
  return (id: string) => { selectItem(id); };
}, [selectItem]);
```

### When useCallback Actually Matters

**Scenario 1: Passing callbacks to memoized children**

```tsx
function TodoList({ todos }: { todos: Todo[] }) {
  const [selected, setSelected] = useState<string | null>(null);

  // Without useCallback: new function every render
  // -> MemoizedTodoItem's memo check fails on `onSelect` prop
  const handleSelect = useCallback((id: string) => {
    setSelected(id);
  }, []); // no deps — setSelected is stable

  return (
    <ul>
      {todos.map(todo => (
        <MemoizedTodoItem
          key={todo.id}
          todo={todo}
          onSelect={handleSelect}
        />
      ))}
    </ul>
  );
}
```

**Scenario 2: Stable dependency for useEffect**

```tsx
function useDataFetcher(url: string) {
  // If fetchData is not stabilized, the effect re-runs on every render
  const fetchData = useCallback(async () => {
    const res = await fetch(url);
    return res.json();
  }, [url]);

  useEffect(() => {
    fetchData().then(setData);
  }, [fetchData]);
}
```

### Common Misuse

```tsx
// POINTLESS: useCallback without a memoized consumer
function Form() {
  const handleSubmit = useCallback((e: FormEvent) => {
    e.preventDefault();
    // submit logic
  }, []);

  // <form> is a native element — it doesn't use React.memo.
  // This useCallback adds overhead for zero benefit.
  return <form onSubmit={handleSubmit}>...</form>;
}
```

**Rule of thumb**: `useCallback` is only useful if the function is either (a) passed to a `React.memo`-wrapped child, (b) used as a dependency of `useEffect`/`useMemo`/`useCallback`, or (c) used in a context value.

---

## React Compiler (React 19)

The React Compiler (formerly React Forget) is an ahead-of-time compiler that automatically inserts memoization during the build step.

### What It Auto-Memoizes

- Component return values (equivalent to wrapping every component in `React.memo`)
- Expensive expressions (equivalent to `useMemo`)
- Callback functions (equivalent to `useCallback`)
- Hook dependency arrays

### How It Works

The compiler analyzes your component code at build time using a custom Babel transform. It tracks value dependencies through assignments, function calls, and control flow, then inserts cache slots that check dependencies and return cached values when inputs are unchanged.

```tsx
// What you write:
function ProductCard({ product, onAddToCart }) {
  const discountedPrice = product.price * (1 - product.discount);
  const handleClick = () => onAddToCart(product.id);

  return (
    <div>
      <span>{discountedPrice}</span>
      <button onClick={handleClick}>Add</button>
    </div>
  );
}

// Conceptually what the compiler produces (simplified):
function ProductCard({ product, onAddToCart }) {
  const $ = useMemoCache(4);

  let discountedPrice;
  if ($[0] !== product.price || $[1] !== product.discount) {
    discountedPrice = product.price * (1 - product.discount);
    $[0] = product.price;
    $[1] = product.discount;
    $[2] = discountedPrice;
  } else {
    discountedPrice = $[2];
  }

  let handleClick;
  if ($[3] !== product.id || $[4] !== onAddToCart) {
    handleClick = () => onAddToCart(product.id);
    $[3] = product.id;
    $[4] = onAddToCart;
    $[5] = handleClick;
  } else {
    handleClick = $[5];
  }

  // JSX memoized similarly...
}
```

### Rules of React

The compiler relies on you following the Rules of React:

- Components and hooks must be pure (same inputs -> same output)
- No mutating values after rendering
- Hooks must be called at the top level, in the same order

Code that violates these rules will either be skipped by the compiler (with a diagnostic) or produce incorrect behavior.

### Interview Implications

When discussing memoization in interviews, acknowledge the compiler:

> "I'd use `useMemo`/`useCallback` here for now, but with the React Compiler in React 19, this manual memoization becomes unnecessary. The compiler handles it automatically as long as you follow the Rules of React."

---

## Keys and Reconciliation

### Why Keys Matter

During reconciliation, React uses keys to match children in the old tree with children in the new tree. Without keys (or with index keys), React relies on position, which breaks down when the order or count of children changes.

```tsx
// BAD: index as key for a reorderable list
{todos.map((todo, index) => (
  <TodoItem key={index} todo={todo} />
))}
// If you insert an item at index 0, React thinks the item at index 0
// changed (it didn't — it moved to index 1). Every item remounts
// or receives wrong props.

// GOOD: stable, unique key
{todos.map(todo => (
  <TodoItem key={todo.id} todo={todo} />
))}
```

### Index-as-Key: When It's Actually Fine

Index keys are acceptable when **all three** conditions hold:

1. The list is static (no adds, removes, or reorders)
2. Items have no local state or uncontrolled inputs
3. Items have no stable unique identifier

### The Key Reset Pattern

Changing a component's key forces React to unmount and remount it, resetting all internal state. This is a deliberate use of the reconciliation algorithm.

```tsx
function UserProfile({ userId }: { userId: string }) {
  // When userId changes, the entire form remounts with fresh state.
  // No need for useEffect cleanup or state synchronization.
  return <ProfileForm key={userId} userId={userId} />;
}

function ProfileForm({ userId }: { userId: string }) {
  const [name, setName] = useState(""); // resets when key changes
  const [email, setEmail] = useState(""); // resets when key changes

  useEffect(() => {
    fetchUser(userId).then(user => {
      setName(user.name);
      setEmail(user.email);
    });
  }, [userId]);

  return (
    <form>
      <input value={name} onChange={e => setName(e.target.value)} />
      <input value={email} onChange={e => setEmail(e.target.value)} />
    </form>
  );
}
```

### Keys Outside of Lists

Keys work on any component, not just list items. The key prop is not forwarded to the component — it is consumed by React's reconciler.

```tsx
// Force re-initialize an animation when `step` changes
<AnimatedPanel key={step} content={steps[step]} />
```

### Tree Diffing Heuristics

React's diffing algorithm operates with two key heuristics that reduce O(n^3) tree diffing to O(n):

1. **Different types produce different trees**: If the element type changes (e.g., `<div>` to `<span>`, or `ComponentA` to `ComponentB`), React tears down the old subtree entirely and builds a new one. No attempt is made to reuse nodes across type boundaries.

2. **Keys identify stable elements across renders**: Within a list of children at the same level, keys tell React which elements correspond to each other.

This is why you must never define components inside other components:

```tsx
function Parent() {
  // BUG: This creates a new component type every render.
  // React sees a different type each time and remounts.
  function Child() {
    return <input />;
  }

  return <Child />;
  // The <input> loses focus and state on every Parent re-render
  // because React unmounts and remounts it each time.
}
```

---

## startTransition and useDeferredValue

### startTransition

Marks a state update as non-urgent. React can interrupt the rendering of transition updates to handle urgent updates (like typing) first.

```tsx
import { useState, useTransition } from "react";

function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Item[]>([]);
  const [isPending, startTransition] = useTransition();

  const handleSearch = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;

    // Urgent: update the input immediately
    setQuery(value);

    // Non-urgent: filter/search can be deferred
    startTransition(() => {
      const filtered = expensiveFilter(allItems, value);
      setResults(filtered);
    });
  };

  return (
    <div>
      <input value={query} onChange={handleSearch} />
      {isPending && <Spinner />}
      <ResultsList items={results} />
    </div>
  );
}
```

### useDeferredValue

Creates a deferred version of a value. When the original value changes, the deferred value "lags behind," allowing React to prioritize rendering with the old deferred value while computing the new one in the background.

```tsx
import { useDeferredValue, useMemo } from "react";

function FilteredList({ query, items }: { query: string; items: Item[] }) {
  // `deferredQuery` lags behind `query` during rapid updates
  const deferredQuery = useDeferredValue(query);
  const isStale = query !== deferredQuery;

  const filtered = useMemo(
    () => items.filter(item =>
      item.name.toLowerCase().includes(deferredQuery.toLowerCase())
    ),
    [deferredQuery, items]
  );

  return (
    <div style={{ opacity: isStale ? 0.7 : 1 }}>
      {filtered.map(item => (
        <ListItem key={item.id} item={item} />
      ))}
    </div>
  );
}
```

### startTransition vs. useDeferredValue

| Aspect | startTransition | useDeferredValue |
|--------|----------------|------------------|
| Controls | The state update itself | A derived value |
| Use when | You own the state setter | You receive data as a prop |
| Works with | `useState` / `useReducer` dispatches | Any value |
| Interrupts render | Yes | Yes |
| Shows stale UI | Via `isPending` | Via comparing original vs deferred |

### When to Use Concurrent Features

- **Large list filtering**: Defer the filtered list while keeping the input responsive
- **Tab switching**: Wrap `setActiveTab` in `startTransition` to keep the old tab visible while the new tab renders
- **Data-heavy dashboards**: Defer expensive chart re-renders
- **Search-as-you-type**: Separate the input update from the results update

---

## Memoization Decision Flowchart

```
Is React Compiler enabled?
├── YES --> Do not manually memoize. The compiler handles it.
└── NO
    │
    Have you profiled and confirmed a performance problem?
    ├── NO --> Do not memoize. Optimize later when needed.
    └── YES
        │
        What is the bottleneck?
        ├── EXPENSIVE COMPUTATION (>2ms)
        │   └── useMemo with correct dependency array
        │
        ├── CHILD COMPONENT RE-RENDERING UNNECESSARILY
        │   ├── Is the child expensive to render?
        │   │   ├── NO --> Leave it. Cheap renders are fine.
        │   │   └── YES
        │   │       ├── Wrap child in React.memo
        │   │       ├── Stabilize object/array props with useMemo
        │   │       └── Stabilize callback props with useCallback
        │   │
        │   └── Is context causing it?
        │       ├── Split context into smaller pieces
        │       └── Memoize the provider value
        │
        ├── LARGE LIST (>100 items)
        │   └── Virtualize with TanStack Virtual or react-window
        │
        ├── INPUT LAG / JANKY UI
        │   └── Wrap non-urgent updates in startTransition
        │       or use useDeferredValue
        │
        └── LARGE INITIAL BUNDLE
            └── Code split with React.lazy + Suspense
```

---

## Common Re-Render Causes and Fixes

| Cause | Symptom | Fix |
|-------|---------|-----|
| Parent re-renders | Child re-renders despite unchanged props | `React.memo` on child |
| New object literal in props | `React.memo` never skips | `useMemo` on the object, or hoist to module scope |
| New function in props | `React.memo` never skips | `useCallback` on the function |
| Context value is new object | All consumers re-render | `useMemo` on provider value |
| Too-broad context | Unrelated consumers re-render | Split into focused contexts |
| State too high in tree | Large subtree re-renders | Colocate state closer to usage |
| Inline component definition | Component remounts every render | Extract to module-level definition |
| Index as key in dynamic list | Items remount on reorder/insert | Use stable unique IDs as keys |
| Uncontrolled to controlled switch | Input loses state | Pick one pattern and stick with it |
| Missing dependency in useMemo | Stale cached value | Add all dependencies; use lint rule |

---

## Rules of Thumb

| Rule | Rationale |
|------|-----------|
| Memoize computations that take >2ms | Below 2ms, the overhead of memoization and dependency checking approaches the cost of recomputing |
| Virtualize lists with >100 items | At 100+ DOM nodes with event handlers and children, layout and paint costs become noticeable |
| Code split at route boundaries first | Routes are natural async boundaries; users expect page transitions to have loading states |
| Profile before optimizing | Intuition about bottlenecks is wrong ~70% of the time; measure first |
| Prefer composition over memoization | Moving state down or lifting content up via `children` avoids re-renders without any API |
| Keep context values narrow | A context with 20 fields triggers all consumers on any single field change |
| Stable keys > index keys for dynamic lists | Index keys cause remounts on insert/delete/reorder, destroying state |
| `startTransition` for anything not directly typed | User input must be synchronous; everything else can be deferred |
| Production builds for benchmarking | Dev mode adds StrictMode double-renders, extra warnings, and disables compiler optimizations |
| Measure INP, not just render time | Interaction to Next Paint captures the full user-perceived delay, including browser work |

---

## Performance API Quick Reference

### React.memo

```tsx
const Memoized = React.memo(Component);
const Memoized = React.memo(Component, (prev, next) => /* true to skip */);
```

- Shallow-compares all props using `Object.is`
- Returns `true` from custom comparator to **skip** re-render
- Does NOT prevent re-renders from internal state or context changes

### useMemo

```tsx
const value = useMemo(() => computeExpensive(a, b), [a, b]);
```

- Caches return value until dependencies change
- Dependencies compared with `Object.is`
- Not a semantic guarantee; React may discard cache

### useCallback

```tsx
const fn = useCallback((arg: T) => doSomething(arg, dep), [dep]);
```

- Equivalent to `useMemo(() => fn, deps)`
- Only useful when passed to memo'd children or used as a hook dependency

### startTransition

```tsx
const [isPending, startTransition] = useTransition();

startTransition(() => {
  setExpensiveState(newValue);
});
```

- Marks state update as non-urgent (interruptible)
- `isPending` is `true` while the transition renders
- Does not delay the update; allows interruption

### useDeferredValue

```tsx
const deferred = useDeferredValue(value);
const isStale = value !== deferred;
```

- Returns a deferred version of the value that lags behind
- Use when you receive data as a prop (don't control the setter)
- Combine with `useMemo` to avoid recomputing with stale inputs
