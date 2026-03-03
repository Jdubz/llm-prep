# 02 — Custom Hooks: Testing and Advanced Patterns

> Assumes you have read 01-custom-hooks-fundamentals.md.
> Covers testing with renderHook, library internals, TypeScript generics, anti-patterns, and interview Q&A.

---

## Table of Contents

1. [Testing Custom Hooks](#testing-custom-hooks)
2. [How TanStack Query Works Under the Hood](#how-tanstack-query-works-under-the-hood)
3. [How SWR Works](#how-swr-works)
4. [Building a Mini Data-Fetching Hook Library](#building-a-mini-data-fetching-hook-library)
5. [Generic Hooks with TypeScript](#generic-hooks-with-typescript)
6. [Hook Composition Anti-Patterns](#hook-composition-anti-patterns)
7. [Migrating Class Lifecycle Methods to Hooks](#migrating-class-lifecycle-methods-to-hooks)
8. [Common Interview Questions](#common-interview-questions)

---

## Testing Custom Hooks

### renderHook Basics

`@testing-library/react` provides `renderHook` which mounts a hook inside a disposable test component:

```tsx
import { renderHook, act } from '@testing-library/react';

test('useToggle starts with initial value', () => {
  const { result } = renderHook(() => useToggle(true));

  expect(result.current[0]).toBe(true);
});

test('useToggle toggles', () => {
  const { result } = renderHook(() => useToggle(false));

  act(() => {
    result.current[1](); // call toggle
  });

  expect(result.current[0]).toBe(true);
});
```

`result.current` is always a live reference to the latest return value. Read it after `act()` completes.

### Changing Hook Inputs

Use the `initialProps` + `rerender` pattern:

```tsx
test('useDebouncedValue updates after delay', () => {
  jest.useFakeTimers();

  const { result, rerender } = renderHook(
    ({ value, delay }) => useDebouncedValue(value, delay),
    { initialProps: { value: 'hello', delay: 300 } },
  );

  expect(result.current).toBe('hello');

  rerender({ value: 'world', delay: 300 });

  // Before debounce fires
  expect(result.current).toBe('hello');

  act(() => jest.advanceTimersByTime(300));

  expect(result.current).toBe('world');
});
```

### Testing Async Hooks

Use `waitFor` for hooks that trigger asynchronous state updates:

```tsx
test('useFetch loads data', async () => {
  // Mock fetch
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ id: 1, name: 'Test' }),
  });

  const { result } = renderHook(() => useFetch<{ id: number }>('/api/test'));

  // Initially loading
  expect(result.current.isLoading).toBe(true);

  await waitFor(() => {
    expect(result.current.isLoading).toBe(false);
  });

  expect(result.current.data).toEqual({ id: 1, name: 'Test' });
  expect(result.current.error).toBeNull();
});
```

### Testing Cleanup

Verify that subscriptions are torn down by unmounting:

```tsx
test('useEventListener removes listener on unmount', () => {
  const handler = jest.fn();
  const addSpy = jest.spyOn(window, 'addEventListener');
  const removeSpy = jest.spyOn(window, 'removeEventListener');

  const { unmount } = renderHook(() =>
    useEventListener('resize', handler),
  );

  expect(addSpy).toHaveBeenCalledWith('resize', expect.any(Function), undefined);

  unmount();

  expect(removeSpy).toHaveBeenCalledWith('resize', expect.any(Function), undefined);
});
```

### Setup, Act, Assert Pattern

```tsx
import { renderHook, act, waitFor } from '@testing-library/react';

// 1. SETUP: render the hook with initial props
const { result, rerender, unmount } = renderHook(
  ({ value }) => useMyHook(value),
  { initialProps: { value: 'initial' } },
);

// 2. ACT: trigger state changes
act(() => {
  result.current.someAction();
});

// or change inputs:
rerender({ value: 'updated' });

// or advance timers:
jest.useFakeTimers();
act(() => jest.advanceTimersByTime(500));

// or wait for async:
await waitFor(() => {
  expect(result.current.isLoading).toBe(false);
});

// 3. ASSERT: check result
expect(result.current.data).toEqual(expected);

// 4. CLEANUP: verify teardown
unmount();
expect(cleanupSpy).toHaveBeenCalled();
```

### Providing Context in Tests

```tsx
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider value={mockAuth}>
    <ThemeProvider value={mockTheme}>
      {children}
    </ThemeProvider>
  </AuthProvider>
);

const { result } = renderHook(() => useMyHook(), { wrapper });
```

---

## How TanStack Query Works Under the Hood

TanStack Query (React Query) is the most widely adopted server-state library for React. Understanding its internals is a strong interview differentiator.

### Architecture

```
QueryClient          -- singleton, owns the cache
  QueryCache         -- Map<string, Query>
    Query            -- single cache entry (data, state machine, subscribers)
  MutationCache      -- Map for mutations

QueryObserver        -- bridges a Query to a React component
  useBaseQuery       -- the hook that creates/manages an observer
```

### Observer Pattern

Each `useQuery` call creates a `QueryObserver`. The observer subscribes to a `Query` in the cache. When the query's state changes, the observer decides whether the subscribing component should re-render based on `select`, `notifyOnChangeProps`, and structural sharing.

```tsx
// Simplified mental model
class QueryObserver {
  #query: Query;
  #listener: () => void;

  constructor(client: QueryClient, options: QueryOptions) {
    this.#query = client.getQueryCache().build(options);
  }

  subscribe(listener: () => void) {
    this.#listener = listener;
    this.#query.addObserver(this);
    // Trigger fetch if stale
    this.#query.fetch();
    return () => this.#query.removeObserver(this);
  }

  notify() {
    // Only notify if the parts the component cares about changed
    if (this.#shouldNotify()) {
      this.#listener();
    }
  }

  getOptimisticResult(): QueryObserverResult {
    // Return current cache state, applying select/placeholderData
    return this.#createResult(this.#query.state);
  }
}
```

In React, the hook wires this to `useSyncExternalStore`:

```tsx
function useBaseQuery(options: QueryOptions) {
  const client = useQueryClient();
  const observer = useRef(new QueryObserver(client, options)).current;

  const result = useSyncExternalStore(
    useCallback(cb => observer.subscribe(cb), [observer]),
    () => observer.getOptimisticResult(),
    () => observer.getOptimisticResult(), // SSR snapshot
  );

  return result;
}
```

### Stale-While-Revalidate

The core data-fetching strategy:

1. **Return stale data immediately** from the cache (instant UI).
2. **Revalidate in the background** by firing a new fetch.
3. **Update the cache and notify observers** when fresh data arrives.

A query is considered stale once `staleTime` has elapsed since the last successful fetch. The `gcTime` (formerly `cacheTime`) controls how long inactive queries remain in memory.

```
Timeline:
  t=0   useQuery('user') -> cache MISS -> fetch -> cache SET (fresh)
  t=30s staleTime=60s, data still fresh, no refetch on mount
  t=90s data is stale. New mount -> return stale data, refetch in background
  t=91s fetch completes -> cache UPDATE -> observers notified -> UI updates
```

### Cache Key Normalization

Query keys are serialized deterministically. `['todos', { status: 'done' }]` and `['todos', { status: 'done' }]` always produce the same hash, regardless of object property order. TanStack Query uses a stable JSON serializer internally.

This enables automatic cache invalidation by prefix:

```tsx
queryClient.invalidateQueries({ queryKey: ['todos'] });
// Invalidates ['todos'], ['todos', 1], ['todos', { status: 'done' }]
```

---

## How SWR Works

SWR (stale-while-revalidate) by Vercel takes a simpler approach than TanStack Query.

### Key-Based Caching

SWR uses the `key` argument (typically a URL string) as both the cache key and the deduplication key. The cache is a global `Map<string, State>`.

```tsx
// Simplified SWR internals
const cache = new Map<string, { data: unknown; error: unknown; ts: number }>();
const subscribers = new Map<string, Set<() => void>>();

function useSWR<T>(key: string, fetcher: (key: string) => Promise<T>) {
  const [, forceUpdate] = useReducer(x => x + 1, 0);

  useEffect(() => {
    // Register subscriber
    if (!subscribers.has(key)) subscribers.set(key, new Set());
    const subs = subscribers.get(key)!;
    subs.add(forceUpdate);

    // Fetch if not cached or stale
    if (!cache.has(key)) {
      fetcher(key).then(data => {
        cache.set(key, { data, error: null, ts: Date.now() });
        subs.forEach(cb => cb()); // notify all subscribers for this key
      });
    }

    return () => { subs.delete(forceUpdate); };
  }, [key]);

  const entry = cache.get(key);
  return { data: entry?.data as T | undefined, error: entry?.error };
}
```

### Deduplication

If multiple components mount simultaneously with the same key, SWR only fires one fetch. All components subscribe to the same cache entry and are notified together.

### Focus Revalidation

SWR listens for `visibilitychange` and `focus` events globally. When the user returns to the tab, all active keys are revalidated:

```tsx
// Simplified
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    for (const [key, subs] of subscribers) {
      if (subs.size > 0) revalidate(key);
    }
  }
});
```

### SWR vs TanStack Query: Key Differences

| Aspect | SWR | TanStack Query |
|---|---|---|
| Cache structure | flat Map | hierarchical with prefix matching |
| Mutations | manual `mutate(key)` | dedicated `useMutation` with optimistic updates |
| Pagination | `useSWRInfinite` | `useInfiniteQuery` with cursor management |
| Devtools | community plugin | first-party, rich inspector |
| Garbage collection | manual or time-based | automatic based on `gcTime` |
| Structural sharing | no | yes (prevents unnecessary re-renders) |

---

## Building a Mini Data-Fetching Hook Library

Here is a production-grade `useFetch` from first principles. This covers caching, deduplication, race conditions, and abort:

```tsx
type CacheEntry<T> = {
  data: T;
  timestamp: number;
  promise?: Promise<T>;
};

const globalCache = new Map<string, CacheEntry<unknown>>();
const inflight = new Map<string, Promise<unknown>>();

interface UseFetchOptions<T> {
  staleTime?: number;
  transform?: (raw: unknown) => T;
  enabled?: boolean;
}

function useFetch<T>(
  url: string | null,
  options: UseFetchOptions<T> = {},
): {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
  isStale: boolean;
  refetch: () => void;
} {
  const { staleTime = 30_000, transform, enabled = true } = options;
  const [state, dispatch] = useReducer(fetchReducer<T>, {
    data: null,
    error: null,
    isLoading: false,
  });

  const abortRef = useRef<AbortController>();

  const fetchData = useCallback(async (fetchUrl: string, signal: AbortSignal) => {
    // Check cache
    const cached = globalCache.get(fetchUrl) as CacheEntry<T> | undefined;
    if (cached && Date.now() - cached.timestamp < staleTime) {
      dispatch({ type: 'success', data: cached.data });
      return;
    }

    // Deduplicate in-flight requests
    let promise = inflight.get(fetchUrl) as Promise<T> | undefined;
    if (!promise) {
      promise = fetch(fetchUrl, { signal })
        .then(res => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then(raw => (transform ? transform(raw) : raw) as T);
      inflight.set(fetchUrl, promise);
    }

    dispatch({ type: 'loading' });

    try {
      const data = await promise;
      if (!signal.aborted) {
        globalCache.set(fetchUrl, { data, timestamp: Date.now() });
        dispatch({ type: 'success', data });
      }
    } catch (err) {
      if (!signal.aborted) {
        dispatch({ type: 'error', error: err as Error });
      }
    } finally {
      inflight.delete(fetchUrl);
    }
  }, [staleTime, transform]);

  useEffect(() => {
    if (!url || !enabled) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    fetchData(url, controller.signal);

    return () => controller.abort();
  }, [url, enabled, fetchData]);

  const refetch = useCallback(() => {
    if (url) {
      globalCache.delete(url);
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      fetchData(url, controller.signal);
    }
  }, [url, fetchData]);

  const isStale = url
    ? (() => {
        const cached = globalCache.get(url);
        return !cached || Date.now() - cached.timestamp >= staleTime;
      })()
    : false;

  return { ...state, isStale, refetch };
}

type FetchAction<T> =
  | { type: 'loading' }
  | { type: 'success'; data: T }
  | { type: 'error'; error: Error };

type FetchState<T> = {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
};

function fetchReducer<T>(state: FetchState<T>, action: FetchAction<T>): FetchState<T> {
  switch (action.type) {
    case 'loading':
      return { ...state, isLoading: true, error: null };
    case 'success':
      return { data: action.data, error: null, isLoading: false };
    case 'error':
      return { ...state, error: action.error, isLoading: false };
  }
}
```

Key design decisions:
- **Global cache outside the hook** so all callers share it.
- **AbortController** cancels the previous request when the URL changes (race condition prevention).
- **In-flight deduplication** via the `inflight` Map prevents multiple identical requests.
- **`useReducer`** instead of multiple `useState` calls guarantees atomic state transitions.

---

## Generic Hooks with TypeScript

### Constrained Generics

Constrain generics to prevent nonsensical usage:

```tsx
function useMap<K, V>(initialEntries?: Iterable<[K, V]>) {
  const [map, setMap] = useState(() => new Map<K, V>(initialEntries));

  const actions = useMemo(() => ({
    set(key: K, value: V) {
      setMap(prev => new Map(prev).set(key, value));
    },
    delete(key: K) {
      setMap(prev => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
    },
    clear() {
      setMap(new Map());
    },
  }), []);

  return [map, actions] as const;
}
```

### Conditional Return Types

Use overloads or conditional types to narrow the return type based on options:

```tsx
// Overload approach
function useQuery<T>(key: string, options: { suspense: true }): { data: T };
function useQuery<T>(key: string, options?: { suspense?: false }): { data: T | undefined };
function useQuery<T>(key: string, options?: { suspense?: boolean }) {
  // implementation
}

// Conditional type approach
type QueryResult<T, Opts extends { select?: (d: T) => unknown }> =
  Opts extends { select: (d: T) => infer R } ? R : T;

function useQuery<T, Opts extends { select?: (d: T) => unknown }>(
  key: string,
  fetcher: () => Promise<T>,
  options?: Opts,
): { data: QueryResult<T, Opts> | undefined } {
  // ...
}
```

### Extracting Element Types from Ref Callbacks

```tsx
function useHover<E extends HTMLElement = HTMLDivElement>(): [
  React.RefCallback<E>,
  boolean,
] {
  const [hovering, setHovering] = useState(false);

  const ref = useCallback((node: E | null) => {
    if (!node) return;
    const enter = () => setHovering(true);
    const leave = () => setHovering(false);
    node.addEventListener('mouseenter', enter);
    node.addEventListener('mouseleave', leave);
    // Cleanup is handled by React unmounting the node
  }, []);

  return [ref, hovering];
}

// Type-safe usage:
const [ref, isHovered] = useHover<HTMLButtonElement>();
```

---

## Hook Composition Anti-Patterns

### Over-Abstraction (God Hook)

When a hook becomes a bag of unrelated features, consumers pay for state they do not use:

```tsx
// Anti-pattern: "god hook"
function useEverything() {
  const auth = useAuth();
  const theme = useTheme();
  const { width } = useWindowSize();
  const isMobile = width < 768;
  const router = useRouter();
  const notifications = useNotifications();
  // 200 more lines...
  return { auth, theme, isMobile, router, notifications, /* ... */ };
}
```

Every consumer re-renders when *any* of these values changes. Instead, keep hooks single-purpose and let components compose the specific hooks they need.

### Hooks That Duplicate React's Job

```tsx
// Anti-pattern: reinventing useEffect
function useOnMount(fn: () => void) {
  useEffect(fn, []);
}

// Anti-pattern: reinventing useMemo
function useDerived<T>(compute: () => T, deps: unknown[]) {
  return useMemo(compute, deps);
}
```

These add indirection without adding capability. A comment or a well-named variable does the same job.

### Unstable Return References

```tsx
// Anti-pattern: new object every render
function useFormField(initialValue: string) {
  const [value, setValue] = useState(initialValue);

  // This object is recreated every render
  return {
    value,
    onChange: (e: ChangeEvent<HTMLInputElement>) => setValue(e.target.value),
    reset: () => setValue(initialValue),
  };
}

// Fixed: memoize the actions
function useFormField(initialValue: string) {
  const [value, setValue] = useState(initialValue);

  const actions = useMemo(() => ({
    onChange: (e: ChangeEvent<HTMLInputElement>) => setValue(e.target.value),
    reset: () => setValue(initialValue),
  }), [initialValue]);

  return { value, ...actions };
}
```

---

## Migrating Class Lifecycle Methods to Hooks

Quick reference for mapping class lifecycle methods to hook equivalents:

| Class Method | Hook Equivalent |
|---|---|
| `componentDidMount` | `useEffect(fn, [])` — empty deps, runs once |
| `componentDidUpdate(prevProps)` with prop check | `useEffect(fn, [prop])` — runs when `prop` changes |
| `componentWillUnmount` | Return a cleanup function from `useEffect` |
| `getDerivedStateFromProps` | `useMemo(() => compute(prop), [prop])` — no state needed |
| `shouldComponentUpdate` | `React.memo(Component, comparator)` — not a hook, but the equivalent |
| `this.instanceVar` (instance variables) | `useRef<T>()` — mutable storage that does not trigger re-renders |

The general principle: **effects replace lifecycle methods**, **refs replace instance variables**, **useMemo replaces derived state**. The mental model shifts from "when does this happen in the lifecycle" to "what data does this depend on."

---

## Common Interview Questions

**Q: Can two components calling the same custom hook share state?**

No. Each call to a custom hook creates independent state. To share state, lift it to context or a state manager.

**Q: What happens if a custom hook calls `useState` — does it create state in the hook or the component?**

State is owned by the component that is rendering. The hook is just a function that runs in the component's context. There is no separate "hook instance."

**Q: Why can't hooks be called inside conditions?**

React tracks hooks by call order (index). If a condition changes which hooks run, the indices shift, and React pairs the wrong state with the wrong hook.

**Q: How do you avoid infinite loops with hooks that return objects?**

Memoize the return value with `useMemo`, or structure the hook so it returns stable references (values that only change when inputs change). Alternatively, return a tuple or use `useRef` for values that should not trigger re-renders.

**Q: How does TanStack Query avoid re-rendering all consumers when unrelated data changes?**

Through `QueryObserver.notify()`. Each observer checks whether the slice of data the component cares about has actually changed (using structural sharing and `notifyOnChangeProps`). If the selector result is referentially identical to the previous result, the observer skips notifying the component.

**Q: What is structural sharing in TanStack Query?**

When a query result is returned, TanStack Query does a deep comparison between the old and new result. Parts of the result object that are deeply equal are kept as the same reference. This means that even if a new response arrives, if `data.user` hasn't changed, `data.user` will be the same object reference, preventing downstream `useMemo` and `React.memo` from invalidating.

**Q: How would you test a hook that depends on a timer?**

Use `jest.useFakeTimers()` before the test. Wrap timer advances in `act(() => jest.advanceTimersByTime(ms))` to ensure React processes any state updates triggered by the timer. Restore real timers in `afterEach` with `jest.useRealTimers()`.

**Q: How do you handle a custom hook that calls another hook that needs a provider?**

Pass a `wrapper` to `renderHook`. The wrapper is a React component that renders the required providers. All hooks rendered inside `renderHook` will have access to the context from the wrapper.
