# 01 — Hooks and State Management

> Core interview knowledge for senior-level React interviews.
> Assumes you already know what hooks are and have used them in production.

---

## Table of Contents

1. [useState](#usestate)
2. [useEffect](#useeffect)
3. [useRef](#useref)
4. [useReducer](#usereducer)
5. [useLayoutEffect vs useEffect](#uselayouteffect-vs-useeffect)
6. [useId](#useid)
7. [Memoization: useMemo and useCallback](#memoization-usememo-and-usecallback)
8. [Every Built-in Hook Reference](#every-built-in-hook-reference)
9. [Common Gotchas](#common-gotchas)
10. [Hook Dependency Quick Rules](#hook-dependency-quick-rules)
11. [Quick Patterns](#quick-patterns)

---

## useState

### Lazy Initialization

The initializer argument can be a **function**. React calls it only on the first render. This matters when the initial value is expensive to compute.

```tsx
// BAD: computeExpensiveDefault() runs on EVERY render (return value is just ignored after the first)
const [value, setValue] = useState(computeExpensiveDefault());

// GOOD: function reference — React calls it once
const [value, setValue] = useState(() => computeExpensiveDefault());
```

- The lazy initializer receives **no arguments**.
- It runs synchronously during the first render — don't put side effects in here.
- This is commonly missed in code reviews and is a frequent interview probe.

### Functional Updates

When the next state depends on the previous state, always use the updater form.

```tsx
// WRONG in concurrent React — may use a stale snapshot
setCount(count + 1);

// CORRECT — guaranteed latest state
setCount((prev) => prev + 1);
```

Why it matters:
- In React 18+ with automatic batching and concurrent features, the closure-captured `count` can be stale.
- Multiple `setCount(count + 1)` calls in the same event handler collapse to a single +1.
- Multiple `setCount(prev => prev + 1)` calls correctly chain.

```tsx
function handleClick() {
  // Results in count + 1 (one update, applied twice with the same stale `count`)
  setCount(count + 1);
  setCount(count + 1);

  // Results in count + 2 (each updater sees the result of the previous)
  setCount((c) => c + 1);
  setCount((c) => c + 1);
}
```

### Object State Pitfalls (Reference Equality)

React uses `Object.is()` to decide whether to re-render. For objects, that means **reference identity**.

```tsx
const [user, setUser] = useState({ name: "Alice", age: 30 });

// BUG: mutating the existing object — same reference — React bails out, no re-render
user.age = 31;
setUser(user);

// CORRECT: new object reference
setUser((prev) => ({ ...prev, age: 31 }));
```

Interview gotcha: What about `useState([])`?

```tsx
const [items, setItems] = useState<string[]>([]);

// BUG: push mutates in place, same reference
items.push("new");
setItems(items); // No re-render

// CORRECT
setItems((prev) => [...prev, "new"]);
```

### Batching Behavior

**React 18+ batches all state updates automatically** — inside event handlers, timeouts, promises, and native event listeners. Before React 18, only React synthetic event handlers were batched.

```tsx
function handleClick() {
  setA(1);
  setB(2);
  setC(3);
  // ONE re-render, not three
}

// React 18: also batched (was NOT batched in React 17)
setTimeout(() => {
  setA(1);
  setB(2);
  // ONE re-render
}, 100);

// To opt out (rare):
import { flushSync } from "react-dom";
flushSync(() => setA(1)); // re-renders immediately
flushSync(() => setB(2)); // re-renders again
```

Key detail: batching means your state updates are **queued** and applied together before the next render. You will not see intermediate states.

---

## useEffect

### Dependency Array Nuances

The dependency array uses `Object.is()` for each element. Consequences:

```tsx
// Runs every render — new object reference each time
useEffect(() => { /* ... */ }, [{ id: 1 }]);

// Runs every render — new array reference each time
useEffect(() => { /* ... */ }, [[1, 2, 3]]);

// Runs every render — new function reference each time
useEffect(() => { /* ... */ }, [() => doSomething()]);
```

Stabilize with `useMemo`, `useCallback`, or extract the primitive values:

```tsx
// Extract primitives
useEffect(() => { /* ... */ }, [user.id, user.name]);

// Or memoize the object if you truly need it
const config = useMemo(() => ({ id, name }), [id, name]);
useEffect(() => { /* ... */ }, [config]);
```

**Missing dependencies** — the exhaustive-deps lint rule exists because stale closures are _silent_ bugs. Trust the lint rule. If it feels wrong, your abstraction is wrong.

### Cleanup Timing

1. Component renders with new props/state.
2. React **paints to the screen**.
3. React runs the **previous effect's cleanup** with the _previous_ closure values.
4. React runs the **new effect** with the _current_ closure values.

```tsx
useEffect(() => {
  const id = setInterval(() => console.log(count), 1000);
  // Cleanup runs BEFORE the next effect, with the `count` from THIS render
  return () => clearInterval(id);
}, [count]);
```

On unmount, the last cleanup runs and no new effect fires.

### Race Conditions

Classic interview problem: what happens when a fast response arrives after a slow one?

```tsx
// BUG: race condition
useEffect(() => {
  fetchUser(userId).then((data) => setUser(data));
}, [userId]);
```

If `userId` changes from 1 to 2 quickly, the response for user 2 might arrive before user 1's response. When user 1's response finally arrives, it overwrites the correct data.

**Fix with a cleanup boolean:**

```tsx
useEffect(() => {
  let cancelled = false;

  fetchUser(userId).then((data) => {
    if (!cancelled) setUser(data);
  });

  return () => {
    cancelled = true;
  };
}, [userId]);
```

**Fix with AbortController (preferred):**

```tsx
useEffect(() => {
  const controller = new AbortController();

  fetchUser(userId, { signal: controller.signal })
    .then((data) => setUser(data))
    .catch((err) => {
      if (err.name !== "AbortError") throw err;
    });

  return () => controller.abort();
}, [userId]);
```

### Async Effects Pattern

You cannot pass an async function directly to `useEffect` because it returns a Promise, not a cleanup function.

```tsx
// WRONG: returns a Promise, React ignores it (and the cleanup is lost)
useEffect(async () => {
  const data = await fetchData();
  setData(data);
}, []);

// CORRECT: define and immediately invoke an async function
useEffect(() => {
  async function load() {
    const data = await fetchData();
    setData(data);
  }
  load();
}, []);

// CORRECT (alternative): IIFE
useEffect(() => {
  (async () => {
    const data = await fetchData();
    setData(data);
  })();
}, []);
```

Full pattern with AbortController:

```tsx
useEffect(() => {
  const controller = new AbortController();
  async function load() {
    try {
      const res = await fetch(url, { signal: controller.signal });
      const data = await res.json();
      setData(data);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e);
    }
  }
  load();
  return () => controller.abort();
}, [url]);
```

---

## useRef

### DOM Refs vs Mutable Containers

`useRef` serves two distinct purposes. Interviewers often test whether you understand both.

**1. DOM access:**

```tsx
const inputRef = useRef<HTMLInputElement>(null);

useEffect(() => {
  inputRef.current?.focus();
}, []);

return <input ref={inputRef} />;
```

**2. Mutable instance variable (survives re-renders, doesn't trigger them):**

```tsx
const intervalIdRef = useRef<ReturnType<typeof setInterval> | null>(null);
const renderCountRef = useRef(0);

useEffect(() => {
  renderCountRef.current += 1;
});
```

Key distinction: `useRef` is a **box** holding a mutable `.current` property. Changing `.current` does NOT cause a re-render. This is by design — it's escape hatch storage outside React's rendering model.

### Callback Refs Pattern

When you need to run logic _the moment_ a DOM node attaches or detaches, a ref object won't notify you. Use a callback ref instead.

```tsx
const [height, setHeight] = useState(0);

const measuredRef = useCallback((node: HTMLDivElement | null) => {
  if (node !== null) {
    setHeight(node.getBoundingClientRect().height);
  }
}, []);

return <div ref={measuredRef}>Hello</div>;
```

Why callback refs matter:
- Ref objects are assigned during commit but don't trigger re-renders or effects.
- Callback refs give you a **synchronous notification** when the ref value changes.
- Useful for: measuring DOM elements, integrating third-party libraries, conditional refs.

### Why Ref Changes Don't Trigger Re-renders

Refs are intentionally outside the React rendering cycle. Internally, `useRef` is essentially:

```tsx
function useRef<T>(initialValue: T) {
  const [ref] = useState(() => ({ current: initialValue }));
  return ref;
}
```

The object reference is stable across renders. Mutating `.current` is just a property assignment on a plain object — React has no way to know it happened and no reason to re-render.

---

## useReducer

### When to Prefer Over useState

Use `useReducer` when:
- Next state depends on previous state in **complex** ways (multiple fields, conditional logic).
- Multiple state values change together and you want **atomic, predictable updates**.
- You want to pass `dispatch` down instead of multiple setter callbacks (dispatch is **referentially stable**).
- State transitions are testable as pure functions.

```tsx
type State = { count: number; step: number; };
type Action =
  | { type: "increment" }
  | { type: "decrement" }
  | { type: "setStep"; payload: number }
  | { type: "reset" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "increment":
      return { ...state, count: state.count + state.step };
    case "decrement":
      return { ...state, count: state.count - state.step };
    case "setStep":
      return { ...state, step: action.payload };
    case "reset":
      return { count: 0, step: 1 };
  }
}

const [state, dispatch] = useReducer(reducer, { count: 0, step: 1 });
```

### Action Patterns

Discriminated unions are the standard TypeScript pattern for actions:

```tsx
type Action =
  | { type: "add"; item: Item }
  | { type: "remove"; id: string }
  | { type: "update"; id: string; changes: Partial<Item> };
```

Lazy initialization (third argument):

```tsx
const [state, dispatch] = useReducer(reducer, userId, (id) => {
  // Called once, receives the second argument
  return { user: loadFromCache(id), loading: false };
});
```

### Dispatch Stability

`dispatch` is **referentially stable** across re-renders. You never need to wrap it in `useCallback` or include it in dependency arrays (though including it is harmless).

This makes it ideal for passing to deeply nested children or context:

```tsx
const DispatchContext = createContext<Dispatch<Action>>(() => {});

function Parent() {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <DispatchContext.Provider value={dispatch}>
      {/* dispatch never changes — children don't re-render from it */}
      <DeepChild />
    </DispatchContext.Provider>
  );
}
```

---

## useLayoutEffect vs useEffect

### Rendering Timeline

```
1. React renders (calls your component function)
2. React updates the DOM
3. useLayoutEffect fires (synchronously, BLOCKS paint)
4. Browser paints to screen
5. useEffect fires (asynchronously, after paint)
```

### When to Use useLayoutEffect

- **Measuring DOM** before the user sees it (avoid flicker).
- **Synchronously mutating DOM** based on measurements.
- **Tooltip/popover positioning** — you need coordinates before paint.

```tsx
function Tooltip({ anchorEl, children }: Props) {
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ top: 0, left: 0 });

  useLayoutEffect(() => {
    if (!anchorEl || !tooltipRef.current) return;
    const rect = anchorEl.getBoundingClientRect();
    setCoords({ top: rect.bottom, left: rect.left });
  }, [anchorEl]);

  return (
    <div ref={tooltipRef} style={{ position: "fixed", ...coords }}>
      {children}
    </div>
  );
}
```

### Key Differences Summary

| Aspect | useEffect | useLayoutEffect |
|--------|-----------|-----------------|
| Timing | After paint | Before paint |
| Blocking | Non-blocking | Blocks paint |
| Use case | Data fetching, subscriptions, logging | DOM measurement, sync mutations |
| SSR | Warns (no DOM) | Warns (no DOM) |
| Performance | Preferred default | Use sparingly |

Isomorphic pattern for SSR compatibility:

```tsx
const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;
```

---

## useId

### SSR-Safe IDs

`useId` generates stable, unique IDs that are consistent between server and client renders.

```tsx
function FormField({ label }: { label: string }) {
  const id = useId();
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <input id={id} />
    </>
  );
}
```

Why not `Math.random()` or a counter?
- `Math.random()` produces different values on server vs client (hydration mismatch).
- A global counter produces different values if component render order differs between server and client.
- `useId` uses the component's position in the fiber tree to generate deterministic IDs.

### Accessibility

Use `useId` for `aria-describedby`, `aria-labelledby`, `htmlFor`, and any attribute that links elements by ID:

```tsx
function PasswordField() {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;

  return (
    <div>
      <label htmlFor={id}>Password</label>
      <input id={id} type="password" aria-describedby={`${hintId} ${errorId}`} />
      <p id={hintId}>Must be 8+ characters</p>
      <p id={errorId} role="alert">{error}</p>
    </div>
  );
}
```

Key details:
- `useId` returns a string like `:r1:` — the colons make it safe as a CSS selector when escaped.
- You can derive multiple related IDs from a single `useId()` call with suffixes.
- Do NOT use `useId` for list keys — it generates the same ID on every render (that's the point).

---

## Memoization: useMemo and useCallback

### useMemo — Two Distinct Use Cases

**1. Cache expensive computations:**

```tsx
const sortedList = useMemo(
  () => [...items].sort((a, b) => a.name.localeCompare(b.name)),
  [items]
);
```

**2. Stabilize object references (prevent downstream re-renders):**

```tsx
// Without useMemo: new object every render → child always re-renders
const config = useMemo(() => ({ id, theme }), [id, theme]);
return <ExpensiveChild config={config} />;
```

### useCallback — Stabilize Function References

`useCallback(fn, deps)` is sugar for `useMemo(() => fn, deps)`. Use it to prevent a child from re-rendering when the function reference changes:

```tsx
// New function reference every render → child re-renders even with React.memo
const handleClick = useCallback(() => {
  doSomething(id);
}, [id]);

return <MemoizedButton onClick={handleClick} />;
```

### When NOT to Memoize

- For cheap computations or primitive values — the memoization overhead costs more than the re-render.
- When the deps change as often as the component re-renders anyway.
- On every function in a component "just in case" — this is premature optimization.

**Decision rule:** Profile first. Add `useMemo`/`useCallback` only when:
1. A child wrapped in `React.memo` is re-rendering despite props not changing, or
2. A `useEffect` dep is causing unwanted effect re-runs, or
3. A computation is genuinely expensive (measured with Profiler).

---

## Every Built-in Hook Reference

### State & Refs

| Hook | Signature | When to Use |
|------|-----------|-------------|
| `useState` | `<S>(initial: S \| (() => S)) => [S, Dispatch<SetStateAction<S>>]` | Simple state that triggers re-renders |
| `useReducer` | `<S, A>(reducer: (s: S, a: A) => S, init: S) => [S, Dispatch<A>]` | Complex state transitions, testable logic, stable dispatch |
| `useRef` | `<T>(initial: T) => MutableRefObject<T>` | Mutable value that persists without re-rendering; DOM access |
| `useState` (lazy) | `useState(() => expensiveCompute())` | Expensive initial value computed once |

### Effects

| Hook | Signature | When to Use |
|------|-----------|-------------|
| `useEffect` | `(effect: () => void \| (() => void), deps?: any[]) => void` | Side effects after paint (fetch, subscribe, log) |
| `useLayoutEffect` | Same as useEffect | DOM measurement/mutation before paint (avoid flicker) |
| `useInsertionEffect` | Same as useEffect | CSS-in-JS library injection (before DOM reads) |

### Memoization

| Hook | Signature | When to Use |
|------|-----------|-------------|
| `useMemo` | `<T>(factory: () => T, deps: any[]) => T` | Cache expensive computations; stabilize object references |
| `useCallback` | `<T extends Function>(fn: T, deps: any[]) => T` | Stabilize function references for child props or effect deps |

### Context & External State

| Hook | Signature | When to Use |
|------|-----------|-------------|
| `useContext` | `<T>(context: Context<T>) => T` | Read nearest context value |
| `useSyncExternalStore` | `<T>(sub, getSnap, getServerSnap?) => T` | Subscribe to external stores without tearing |

### Identity & Transitions

| Hook | Signature | When to Use |
|------|-----------|-------------|
| `useId` | `() => string` | SSR-safe unique IDs for accessibility attributes |
| `useTransition` | `() => [boolean, (cb: () => void) => void]` | Mark state updates as non-urgent (keep UI responsive) |
| `useDeferredValue` | `<T>(value: T) => T` | Defer a value to avoid blocking urgent updates |
| `useDebugValue` | `(value: any, format?: (v: any) => any) => void` | Label custom hooks in React DevTools |

### React 19

| Hook | Signature | When to Use |
|------|-----------|-------------|
| `use` | `<T>(resource: Promise<T> \| Context<T>) => T` | Read promises/context in render (can use conditionally) |
| `useOptimistic` | `<S, A>(passthrough: S, reducer?: (s: S, a: A) => S) => [S, (a: A) => void]` | Optimistic UI during async actions |
| `useActionState` | `<S>(action, initialState, permalink?) => [S, formAction, isPending]` | Form actions with returned state and pending flag |
| `useFormStatus` | `() => { pending, data, method, action }` | Read parent form's submission status |

---

## Common Gotchas

| Gotcha | Fix |
|--------|-----|
| `useState(expensiveFn())` runs every render | Use `useState(() => expensiveFn())` — lazy initializer |
| `setCount(count + 1)` called twice = one increment | Use `setCount(c => c + 1)` — functional update |
| Mutating an object/array and calling setState = no re-render | Spread into a new reference: `setState(prev => ({...prev, key: val}))` |
| `useEffect(async () => ...)` — cleanup is lost | Define async fn inside effect, call it |
| `useEffect` with object dep reruns every render | Extract primitives or `useMemo` the object |
| Stale closure in `setInterval` inside `useEffect([])` | Use a ref to hold the latest value, or add deps and restart the interval |
| `useLayoutEffect` warning during SSR | Conditionally use `useEffect` on server, or suppress with `useIsomorphicLayoutEffect` |
| `useSyncExternalStore` infinite loop | `getSnapshot` is returning a new object reference each call — return cached/primitive |
| `useId` used for list keys | Never — `useId` is for accessibility IDs, not keys |
| Calling hooks inside conditions/loops | Move hook to top level; restructure the condition to be inside the hook's callback |
| `useCallback` without deps = stale closure | Always list captured variables in deps; trust `eslint-plugin-react-hooks` |

---

## Hook Dependency Quick Rules

| Scenario | What goes in deps |
|----------|-------------------|
| Run once on mount | `[]` |
| Run when specific values change | `[val1, val2]` |
| Run every render | Omit the array entirely |
| `setState` / `dispatch` | Safe to omit (stable), safe to include (no harm) |
| Refs from `useRef` | Safe to omit (stable object), `.current` changes aren't tracked |
| Props | Always include if read inside the effect |
| Values from custom hooks | Always include |

---

## Quick Patterns

### Previous Value

```tsx
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);
  useEffect(() => {
    ref.current = value;
  });
  return ref.current;
}
```

### Debounced Value

```tsx
function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}
```

### Latest Ref (Solve Stale Closures)

```tsx
function useLatest<T>(value: T): React.RefObject<T> {
  const ref = useRef(value);
  useLayoutEffect(() => {
    ref.current = value;
  });
  return ref;
}
```

### Stable Callback (DIY useEffectEvent)

```tsx
function useStableCallback<T extends (...args: any[]) => any>(fn: T): T {
  const ref = useRef(fn);
  useLayoutEffect(() => {
    ref.current = fn;
  });
  return useCallback(
    ((...args: any[]) => ref.current(...args)) as T,
    []
  );
}
```

### Interval with Latest Callback

```tsx
function useInterval(callback: () => void, delayMs: number | null) {
  const savedCallback = useRef(callback);
  useLayoutEffect(() => {
    savedCallback.current = callback;
  });
  useEffect(() => {
    if (delayMs === null) return;
    const id = setInterval(() => savedCallback.current(), delayMs);
    return () => clearInterval(id);
  }, [delayMs]);
}
```

### Window Event Listener

```tsx
function useWindowEvent<K extends keyof WindowEventMap>(
  event: K,
  handler: (e: WindowEventMap[K]) => void,
  options?: AddEventListenerOptions
) {
  const handlerRef = useRef(handler);
  useLayoutEffect(() => {
    handlerRef.current = handler;
  });
  useEffect(() => {
    const listener = (e: WindowEventMap[K]) => handlerRef.current(e);
    window.addEventListener(event, listener, options);
    return () => window.removeEventListener(event, listener, options);
  }, [event]);
}
```

### Media Query

```tsx
function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", cb);
      return () => mql.removeEventListener("change", cb);
    },
    () => window.matchMedia(query).matches,
    () => false
  );
}
```

---

## Quick Mental Model

```
Component Render
  │
  ├── useState    → returns [state, setState] from fiber's hook list
  ├── useReducer  → returns [state, dispatch] from fiber's hook list
  ├── useRef      → returns { current } (stable object) from fiber's hook list
  ├── useMemo     → returns cached value if deps unchanged
  ├── useCallback → returns cached function if deps unchanged (sugar for useMemo(() => fn, deps))
  │
  ▼
DOM Update (commit phase)
  │
  ├── useLayoutEffect → fires sync, blocks paint
  │
  ▼
Browser Paint
  │
  ├── useEffect → fires async, after paint
  │
  ▼
User sees the screen
```

---

## Practice

- **Implement `usePrevious`**: Build the hook from scratch using `useRef` + `useEffect`. Then try the derived-state approach (`useState` with a `[prev, curr]` tuple). Compare the two. See `src/hooks/usePrevious.js` for the exercise file.
- **Implement `useFetch`**: Build a data-fetching hook with `AbortController` for race condition handling. See `src/hooks/useFetch.js` for the exercise file and `src/lessons/02-custom-hooks/CustomHooksDemo.jsx` to test it interactively.
- **Stale closure drill**: Write a component with `setInterval` inside `useEffect([])` that logs `count`. Click to increment. Observe that the log is always 0. Fix it with: (1) `setCount(c => c + 1)`, (2) adding `count` to deps, (3) storing `count` in a ref.
- **useReducer refactor**: Take a component with 3+ related `useState` calls and refactor to `useReducer`. Write the reducer as a pure function and test it without React.
- **Quick-fire interview answers**: Explain without looking: What is the difference between `useLayoutEffect` and `useEffect`? Why is `dispatch` referentially stable? What does `useSyncExternalStore` solve?

### Related Lessons

- [Hooks Internals & Advanced Patterns](02-hooks-internals-and-advanced-patterns.md) -- rules of hooks, fiber hook linked list, closure traps, `useSyncExternalStore`, React 19 hooks
- [Custom Hooks Fundamentals](../02-custom-hooks/01-custom-hooks-fundamentals.md) -- how to compose the primitives from this lesson into reusable hooks
- [Performance: Rendering & Optimization](../03-performance/01-react-rendering-and-optimization.md) -- memoization hooks (`useMemo`, `useCallback`) in depth, when and how to use them
