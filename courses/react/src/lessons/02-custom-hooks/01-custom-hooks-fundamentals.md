# 01 — Custom Hooks Fundamentals

> Conventions, extracting stateful logic, real-world pattern implementations.

---

## Table of Contents

1. [When to Extract a Custom Hook](#when-to-extract-a-custom-hook)
2. [Hook Composition Patterns](#hook-composition-patterns)
3. [Return Value Contracts](#return-value-contracts)
4. [Real-World Custom Hook Implementations](#real-world-custom-hook-implementations)
5. [Hook Dependency Injection](#hook-dependency-injection)
6. [Rules for Custom Hooks](#rules-for-custom-hooks)
7. [Common Hooks Catalog](#common-hooks-catalog)
8. [Do's and Don'ts](#dos-and-donts)
9. [Decision: Should I Extract This Into a Hook?](#decision-should-i-extract-this-into-a-hook)
10. [Custom Hook Template](#custom-hook-template)

---

## When to Extract a Custom Hook

The typical answer is "reuse," but that undersells the real criteria. Extract a custom hook when:

1. **You need to encapsulate a stateful protocol.** If two or more primitives (`useState`, `useEffect`, `useRef`) collaborate to maintain an invariant, that invariant deserves a name.
2. **You want to hide an effect's lifecycle from the component.** The component should declare *what* it needs, not *how* subscriptions and teardowns work.
3. **You need to test stateful logic in isolation** without mounting a component.
4. **You need a stable API boundary** between a feature and its consumers, even if only one component uses it today.

Reuse is a *consequence*, not the primary driver. A hook used by exactly one component is still worth extracting if it clarifies intent.

### Signals That You Should NOT Extract

- The "hook" would just be a thin wrapper around a single `useState` with no additional logic.
- You are hiding complexity that the component author genuinely needs to see (e.g., the order of state transitions matters for the UI).
- The abstraction leaks: callers constantly reach into the hook's internals or pass configuration that mirrors the implementation.

---

## Hook Composition Patterns

### Hooks Calling Hooks

Custom hooks compose by calling other custom hooks. The React runtime does not distinguish between a hook called from a component and a hook called from another hook — the call-site identity is established by call order.

```tsx
function useNetworkAwarePolling<T>(url: string, intervalMs: number) {
  const isOnline = useOnlineStatus();       // custom hook
  const [data, setData] = useState<T | null>(null);
  const savedCallback = useLatestRef(() => {  // custom hook wrapping useRef
    if (isOnline) fetch(url).then(r => r.json()).then(setData);
  });

  useInterval(savedCallback, isOnline ? intervalMs : null); // custom hook

  return data;
}
```

Key principle: each hook owns its own slice of state. There is no shared mutable context between sibling hook calls unless you explicitly thread values through.

### Combining Primitives into Higher-Order Hooks

A powerful pattern is building a small toolkit of low-level hooks, then composing them:

```
useLatestRef        -- captures latest value without re-render
useStableCallback   -- stable reference that always calls latest closure
useInterval         -- declarative setInterval with pause/resume
useTimeout          -- declarative setTimeout with reset
useNetworkAwarePolling -- combines all of the above
```

Each layer adds exactly one concern. If you find yourself passing five configuration options into a single hook, break it apart.

---

## Return Value Contracts

### Tuple Returns

Use when the hook is a **primitive** with one or two values that callers will rename:

```tsx
function useToggle(initial = false): [boolean, () => void] {
  const [value, setValue] = useState(initial);
  const toggle = useCallback(() => setValue(v => !v), []);
  return [value, toggle];
}

// Caller renames freely:
const [isOpen, toggleOpen] = useToggle();
const [isEnabled, toggleEnabled] = useToggle(true);
```

Tuples work when:
- There are 1-3 return values.
- Callers almost always use all of them.
- Positional semantics are obvious (value, setter) or (value, actions).

### Object Returns

Use when the hook returns **multiple related values** or an **API surface**:

```tsx
interface UseFetchResult<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  refetch: () => void;
  abort: () => void;
}

function useFetch<T>(url: string): UseFetchResult<T> { /* ... */ }

// Caller destructures what it needs:
const { data, isLoading } = useFetch<User>('/api/user');
```

Objects work when:
- There are 3+ return values.
- Callers frequently use only a subset.
- You want to add fields later without a breaking change.

### Discriminated Union Returns

For hooks with distinct states, use discriminated unions to get exhaustive type narrowing:

```tsx
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

function useAsync<T>(asyncFn: () => Promise<T>): AsyncState<T> {
  // ...
}

// Caller gets perfect narrowing:
const state = useAsync(fetchUser);
if (state.status === 'success') {
  // state.data is T here, not T | undefined
}
```

---

## Real-World Custom Hook Implementations

### useDebounce / useDebouncedValue

```tsx
function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);

  return debounced;
}

// Alternative: debounce a callback
function useDebouncedCallback<Args extends unknown[]>(
  callback: (...args: Args) => void,
  delayMs: number,
): (...args: Args) => void {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  // Cleanup on unmount
  useEffect(() => () => clearTimeout(timerRef.current), []);

  return useCallback((...args: Args) => {
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => callbackRef.current(...args), delayMs);
  }, [delayMs]);
}
```

Interview note: `useDebouncedValue` causes a re-render after the delay. `useDebouncedCallback` does not — it controls *when* the side effect fires. Know which one the question is asking for.

### useMediaQuery

```tsx
function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false; // SSR
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);

    // Modern API (Safari 14+)
    mql.addEventListener('change', handler);
    // Sync in case query changed between render and effect
    setMatches(mql.matches);

    return () => mql.removeEventListener('change', handler);
  }, [query]);

  return matches;
}
```

Interview note: `addListener`/`removeListener` are deprecated. Use `addEventListener`. The initial `useState` callback handles SSR by defaulting to `false`.

### useLocalStorage

```tsx
function useLocalStorage<T>(
  key: string,
  initialValue: T,
): [T, (value: T | ((prev: T) => T)) => void] {
  // Lazy initializer reads from storage once
  const [stored, setStored] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue; // SSR safety
    try {
      const item = window.localStorage.getItem(key);
      return item !== null ? (JSON.parse(item) as T) : initialValue;
    } catch {
      return initialValue;
    }
  });

  // Persist to localStorage on change
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(stored));
    } catch {
      // Storage full or blocked -- fail silently
    }
  }, [key, stored]);

  // Sync across tabs
  useEffect(() => {
    const handler = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try { setStored(JSON.parse(e.newValue)); } catch { /* ignore */ }
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [key]);

  return [stored, setStored];
}
```

Interview note: the `storage` event only fires in *other* tabs. Same-tab updates go through `setStored` directly. SSR safety comes from guarding `window` access inside the lazy initializer, not inside the effect.

### useIntersectionObserver

```tsx
interface UseIntersectionOptions {
  root?: Element | null;
  rootMargin?: string;
  threshold?: number | number[];
  enabled?: boolean;
}

function useIntersectionObserver(
  options: UseIntersectionOptions = {},
): [React.RefCallback<Element>, IntersectionObserverEntry | null] {
  const { root = null, rootMargin = '0px', threshold = 0, enabled = true } = options;
  const [entry, setEntry] = useState<IntersectionObserverEntry | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);

  // Use a ref callback so we observe the element as soon as it mounts.
  // This avoids the one-render delay of useEffect + ref.current.
  const refCallback = useCallback(
    (node: Element | null) => {
      // Disconnect previous observer
      observerRef.current?.disconnect();

      if (!node || !enabled) {
        setEntry(null);
        return;
      }

      observerRef.current = new IntersectionObserver(
        ([e]) => setEntry(e),
        { root, rootMargin, threshold },
      );
      observerRef.current.observe(node);
    },
    [root, rootMargin, threshold, enabled],
  );

  // Cleanup on unmount
  useEffect(() => () => observerRef.current?.disconnect(), []);

  return [refCallback, entry];
}

// Usage:
function LazyImage({ src }: { src: string }) {
  const [ref, entry] = useIntersectionObserver({ threshold: 0.1 });
  const isVisible = entry?.isIntersecting ?? false;

  return <div ref={ref}>{isVisible && <img src={src} />}</div>;
}
```

Interview note: returning a `RefCallback` instead of a `RefObject` is the correct approach. `RefCallback` fires synchronously during commit, so the observer attaches without a wasted render. A `RefObject` + `useEffect` pattern misses the first paint.

### useEventListener

```tsx
function useEventListener<K extends keyof WindowEventMap>(
  eventName: K,
  handler: (event: WindowEventMap[K]) => void,
  element?: undefined,
  options?: boolean | AddEventListenerOptions,
): void;
function useEventListener<
  K extends keyof HTMLElementEventMap,
  T extends HTMLElement,
>(
  eventName: K,
  handler: (event: HTMLElementEventMap[K]) => void,
  element: React.RefObject<T>,
  options?: boolean | AddEventListenerOptions,
): void;
function useEventListener(
  eventName: string,
  handler: (event: Event) => void,
  element?: React.RefObject<HTMLElement>,
  options?: boolean | AddEventListenerOptions,
) {
  const savedHandler = useRef(handler);

  // Update ref each render so the effect closure is never stale
  useLayoutEffect(() => {
    savedHandler.current = handler;
  });

  useEffect(() => {
    const target = element?.current ?? window;
    const listener = (event: Event) => savedHandler.current(event);

    target.addEventListener(eventName, listener, options);
    return () => target.removeEventListener(eventName, listener, options);
  }, [eventName, element, options]);
}
```

Interview note: storing the handler in a ref avoids re-subscribing on every render when the caller passes an inline function. `useLayoutEffect` for the ref assignment ensures no gap between render and effect where the ref could hold a stale closure.

### usePrevious

```tsx
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);

  useEffect(() => {
    ref.current = value;
  });

  return ref.current;
}
```

This works because:

1. During render, `ref.current` still holds the value from the *previous* commit.
2. After render, the effect fires and updates `ref.current` to the *current* value.
3. On the next render, step 1 returns what was set in step 2.

No dependency array on the effect — it runs after every render.

---

## Hook Dependency Injection

Passing hooks (or factories that hooks call) as parameters makes hooks testable without mocking modules:

```tsx
interface UseDataOptions<T> {
  fetcher?: (url: string) => Promise<T>;
  useAuth?: () => { token: string };
}

function useData<T>(url: string, options: UseDataOptions<T> = {}) {
  const {
    fetcher = defaultFetcher,
    useAuth: useAuthHook = useAuth, // injectable
  } = options;

  const { token } = useAuthHook();
  // ... use token + fetcher
}

// In tests:
test('useData with injected auth', () => {
  const mockUseAuth = () => ({ token: 'test-token' });

  const { result } = renderHook(() =>
    useData('/api/data', {
      fetcher: async () => ({ items: [] }),
      useAuth: mockUseAuth,
    }),
  );
  // ...
});
```

The constraint is that the injected hook must be called unconditionally and in the same order every render. As long as the parameter reference is stable (or the identity doesn't change between renders), this is safe.

### Factory Pattern for Complex Injection

```tsx
function createUseSearch(dependencies: {
  useDebounce: typeof useDebouncedValue;
  useApi: typeof useApi;
}) {
  return function useSearch(query: string) {
    const debouncedQuery = dependencies.useDebounce(query, 300);
    const results = dependencies.useApi(`/search?q=${debouncedQuery}`);
    return results;
  };
}

// Production
const useSearch = createUseSearch({
  useDebounce: useDebouncedValue,
  useApi: useApi,
});

// Test
const useSearchTest = createUseSearch({
  useDebounce: (val) => val, // no debounce in tests
  useApi: mockUseApi,
});
```

---

## Rules for Custom Hooks

### Naming

- Must start with `use`. This is enforced by the linter and tells React to apply the Rules of Hooks.
- Name should describe what the hook **provides**, not what it **does internally**: `useOnlineStatus` not `useAddEventListenerForOnlineOffline`.

### Conditional Calls

Hooks cannot be called conditionally, in loops, or after early returns. This is non-negotiable because React identifies hooks by **call index**.

```tsx
// WRONG
function useFeature(enabled: boolean) {
  if (!enabled) return null;   // early return before a hook call
  const [state, setState] = useState(0); // call index is now unstable
  // ...
}

// RIGHT
function useFeature(enabled: boolean) {
  const [state, setState] = useState(0);
  // Guard behavior, not the hook call itself
  useEffect(() => {
    if (!enabled) return;
    // subscribe...
  }, [enabled]);
  return enabled ? state : null;
}
```

### Error Boundaries and Hooks

Hooks cannot catch errors thrown during rendering of child components. If a hook's consumer might throw, the error boundary must be a *parent* component, not the hook.

However, hooks *can* catch and surface async errors:

```tsx
function useSafeAsync<T>(asyncFn: () => Promise<T>) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' });

  const run = useCallback(async () => {
    setState({ status: 'loading' });
    try {
      const data = await asyncFn();
      setState({ status: 'success', data });
    } catch (error) {
      setState({ status: 'error', error: error as Error });
    }
  }, [asyncFn]);

  return { ...state, run };
}
```

The key distinction: hooks manage **state** about errors; error boundaries manage **rendering** errors. They serve different layers.

### Custom Hook Checklist

Before merging a custom hook, verify:

1. **Cleanup:** every subscription, listener, timer, or observer is cleaned up in a return function.
2. **Stale closure prevention:** long-lived callbacks reference `useRef` for latest values, not stale closure variables.
3. **SSR safety:** no bare `window`, `document`, or `navigator` access outside of effects or guarded initializers.
4. **Dependency arrays are correct:** the ESLint exhaustive-deps rule is enabled and passes.
5. **Return value stability:** objects/arrays returned from hooks are memoized or stable across renders to avoid cascading re-renders in consumers.
6. **Race conditions:** async effects check a cancelled/stale flag before calling setState.

```tsx
// Race condition guard pattern
useEffect(() => {
  let cancelled = false;

  fetchData(url).then(data => {
    if (!cancelled) setData(data);
  });

  return () => { cancelled = true; };
}, [url]);
```

---

## Common Hooks Catalog

| Hook | Signature | Description |
|---|---|---|
| `useToggle` | `(initial?: boolean) => [boolean, () => void]` | Boolean state with a stable toggle function |
| `usePrevious` | `<T>(value: T) => T \| undefined` | Returns the value from the previous render |
| `useDebouncedValue` | `<T>(value: T, ms: number) => T` | Delays updating the returned value until input is stable |
| `useLocalStorage` | `<T>(key: string, init: T) => [T, SetState<T>]` | Persistent state synced to localStorage with SSR safety |
| `useMediaQuery` | `(query: string) => boolean` | Reactive CSS media query match |
| `useIntersectionObserver` | `(opts?) => [RefCallback, Entry \| null]` | Observes element visibility via IntersectionObserver |
| `useEventListener` | `(event, handler, element?, opts?) => void` | Declarative event listener with automatic cleanup |
| `useOnClickOutside` | `(ref, handler) => void` | Fires handler when a click occurs outside the ref element |
| `useInterval` | `(callback, delayMs \| null) => void` | Declarative `setInterval`; pass `null` to pause |
| `useTimeout` | `(callback, delayMs \| null) => void` | Declarative `setTimeout` with auto-cleanup |
| `useAsync` | `<T>(fn: () => Promise<T>) => AsyncState<T>` | Tracks loading/success/error for a promise |
| `useFetch` | `<T>(url: string) => { data, error, isLoading }` | Fetch with caching, abort, and race condition handling |
| `useLatestRef` | `<T>(value: T) => RefObject<T>` | Always-current ref that does not trigger re-renders |
| `useStableCallback` | `<T extends Function>(fn: T) => T` | Stable function identity that always calls the latest closure |
| `useIsomorphicLayoutEffect` | Same as `useLayoutEffect` | Uses `useLayoutEffect` in browser, `useEffect` on server |

---

## Do's and Don'ts

| Do | Don't |
|---|---|
| Start hook names with `use` | Name a regular function `useSomething` |
| Return stable references (memoize objects/callbacks) | Return a new object/array literal every render |
| Use `useRef` for mutable values that should not trigger re-renders | Store mutable values in `useState` when you do not need re-renders |
| Clean up subscriptions, timers, and observers in effect cleanup | Assume the component will never unmount or re-render |
| Guard `window`/`document` access for SSR safety | Access browser APIs at module scope or in render |
| Use discriminated unions for multi-state returns | Use separate `isLoading` + `isError` + `isSuccess` booleans that can conflict |
| Compose small hooks into larger ones | Build a single hook that handles 5+ unrelated concerns |
| Accept options via an object for extensibility | Add positional parameters beyond 2-3 arguments |
| Use `useReducer` when state transitions are interdependent | Use multiple `useState` calls with manual synchronization |
| Use the `enabled` pattern to conditionally skip work | Call hooks conditionally (`if (x) useThing()`) |
| Write explicit TypeScript return types for public hooks | Rely solely on inference for complex return types |
| Test hooks via `renderHook` in isolation | Only test hooks indirectly through component tests |

---

## Decision: Should I Extract This Into a Hook?

```
Is there stateful logic (useState, useEffect, useRef working together)?
  No  --> Probably a plain function, not a hook.
  Yes |
      v
Does this logic represent a single, nameable concept?
  No  --> Split into smaller hooks first.
  Yes |
      v
Will extracting it make the component easier to read?
  No  --> Leave it inline. One useState + one useEffect is fine inline.
  Yes |
      v
Is the logic > ~15 lines or does it obscure the component's render logic?
  No  --> Extraction is optional. Consider readability vs indirection tradeoff.
  Yes |
      v
Extract it. Name it after what it provides, not what it does internally.
  useOnlineStatus, not useAddWindowEventListenerForOnlineAndOffline.
```

### Quick Sniff Tests

- **If you have to pass 5+ config options:** the hook may be doing too much. Split it.
- **If the hook returns values that callers never use together:** it is a god hook. Decompose it.
- **If testing the hook requires mocking more than 2 externals:** the hook has too many responsibilities.
- **If you cannot describe the hook in one sentence:** it needs to be smaller.

---

## Practice

- **Implement `usePrevious`**: Open `src/hooks/usePrevious.js` and implement the hook. This file uses the derived-state pattern (`useState` with `[prev, curr]` tuple). Compare it to the `useRef` + `useEffect` approach described in the "usePrevious" section above.
- **Implement `useFetch`**: Open `src/hooks/useFetch.js` and implement a data-fetching hook with `AbortController` for race condition handling and a `refetch` callback.
- **Test interactively**: Run `npm run dev` and open the Custom Hooks Demo (`src/lessons/02-custom-hooks/CustomHooksDemo.jsx`). Use the PreviousValueDemo, FetchDemo, and RaceConditionTester components to verify your implementations.
- **Build `useDebounce`**: Implement the debounced value hook shown in this lesson. Write a component that uses it for search-as-you-type. Verify that rapid typing only triggers one API call after the delay.
- **Build `useLocalStorage`**: Implement the `useLocalStorage` hook from the examples. Handle SSR (return default when `window` is undefined), JSON serialization errors, and storage events from other tabs.
- **Composition exercise**: Build `useSearchWithHistory` by composing `useDebounce`, `useLocalStorage`, and `useFetch`. This exercises the hook composition pattern.

### Related Lessons

- [Hooks & State Management](../01-hooks-deep-dive/01-hooks-and-state-management.md) -- understand `useRef`, `useEffect`, `useState`, and `useReducer` before building custom hooks on top of them
- [Custom Hooks Testing & Advanced](02-custom-hooks-testing-and-advanced.md) -- testing hooks with `renderHook`, TanStack Query internals, TypeScript generics for hooks
- [Performance: Rendering & Optimization](../03-performance/01-react-rendering-and-optimization.md) -- understand memoization patterns for stable return values from hooks

---

## Custom Hook Template

```tsx
import { useState, useEffect, useCallback, useRef } from 'react';

interface UseMyHookOptions {
  enabled?: boolean;
  // ...options
}

interface UseMyHookReturn {
  data: SomeType | null;
  isActive: boolean;
  reset: () => void;
}

export function useMyHook(
  input: string,
  options: UseMyHookOptions = {},
): UseMyHookReturn {
  const { enabled = true } = options;
  const [data, setData] = useState<SomeType | null>(null);
  const [isActive, setIsActive] = useState(false);

  // Stable ref for latest callback / value
  const inputRef = useRef(input);
  inputRef.current = input;

  // Effects with cleanup
  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;
    setIsActive(true);

    doAsyncWork(input).then(result => {
      if (!cancelled) {
        setData(result);
        setIsActive(false);
      }
    });

    return () => { cancelled = true; };
  }, [input, enabled]);

  // Stable action
  const reset = useCallback(() => {
    setData(null);
    setIsActive(false);
  }, []);

  return { data, isActive, reset };
}
```
