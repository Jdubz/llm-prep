# 02 — Hooks Internals and Advanced Patterns

> Assumes you have read 01-hooks-and-state-management.md.
> Covers hook internals, closure traps, advanced hooks, and interview Q&A.

---

## Table of Contents

1. [Rules of Hooks — The WHY](#rules-of-hooks--the-why)
2. [Hook Internals: Fiber Nodes and the Hook Linked List](#hook-internals-fiber-nodes-and-the-hook-linked-list)
3. [Closure Traps](#closure-traps)
4. [useEffect Cleanup Timing — Commit Phase Details](#useeffect-cleanup-timing--commit-phase-details)
5. [useSyncExternalStore](#usesyncexternalstore)
6. [useEffectEvent (Upcoming)](#useeffectevent-upcoming)
7. [React 19 Hook Changes](#react-19-hook-changes)
8. [Common Interview Questions](#common-interview-questions)

---

## Rules of Hooks — The WHY

### The Real Reason: Linked List / Call Order

React stores hook state as a **linked list** on the fiber node. Each `useState`, `useEffect`, `useRef`, etc. call corresponds to a node in this list. React matches hooks to their state **by position (call order)**, not by name.

```
Fiber Node
  └── memoizedState -> Hook1 -> Hook2 -> Hook3 -> null
                       (useState) (useEffect) (useRef)
```

On re-render, React walks the list in order. If you call hooks in a different order, React assigns the wrong state to the wrong hook.

```tsx
// BROKEN: conditional hook changes call order
function Bad({ showName }: { showName: boolean }) {
  if (showName) {
    const [name, setName] = useState(""); // Hook 1 (sometimes)
  }
  const [age, setAge] = useState(0);      // Hook 1 or 2 (ambiguous!)
  // React can't tell which state belongs to which hook
}
```

### The Rules (and Why Each Exists)

1. **Only call hooks at the top level** — no conditions, loops, or nested functions.
   - Why: Ensures the hook call order is identical on every render so the linked list matches.

2. **Only call hooks from React functions** (components or custom hooks).
   - Why: Hooks need the fiber context (the "currently rendering component") to read/write state. Outside a component, there's no fiber.

3. **Custom hooks must start with `use`**.
   - Why: Convention that enables the linter to enforce rules 1 and 2 on custom hooks.

---

## Hook Internals: Fiber Nodes and the Hook Linked List

### The Fiber Tree

Every React component instance corresponds to a **fiber node** — a plain JS object that holds:
- The component type and props
- A pointer to child, sibling, and parent fibers
- **`memoizedState`** — the head of the hook linked list

```
FiberNode {
  tag: FunctionComponent,
  type: MyComponent,
  memoizedState: Hook0,   // head of linked list
  updateQueue: ...,
  ...
}
```

### The Hook Linked List

Each hook call during render creates (on mount) or reads (on update) a **Hook object**:

```ts
type Hook = {
  memoizedState: any;       // the stored value (state, ref, memo result, effect)
  baseState: any;           // base state for reducers
  baseQueue: Update | null; // pending updates
  queue: UpdateQueue | null;// update queue (for useState/useReducer)
  next: Hook | null;        // pointer to next hook
};
```

The hooks form a singly linked list:

```
fiber.memoizedState
  → Hook0 (useState: count)
    → Hook1 (useEffect: fetch data)
      → Hook2 (useRef: inputRef)
        → Hook3 (useMemo: computed value)
          → null
```

### Mount vs Update

React has **two dispatchers**: `HooksDispatcherOnMount` and `HooksDispatcherOnUpdate`.

- **On mount**: each hook call creates a new Hook object and appends it to the list.
- **On update**: each hook call reads the next Hook from the existing list (via a `workInProgressHook` cursor).

This is why call order must be identical — the cursor advances linearly through the list.

```
Mount render:
  useState()   → create Hook0, fiber.memoizedState = Hook0
  useEffect()  → create Hook1, Hook0.next = Hook1
  useRef()     → create Hook2, Hook1.next = Hook2

Update render:
  useState()   → read Hook0 (cursor starts at fiber.memoizedState)
  useEffect()  → read Hook1 (cursor = Hook0.next)
  useRef()     → read Hook2 (cursor = Hook1.next)
```

### What memoizedState Holds Per Hook Type

| Hook | memoizedState contains |
|------|----------------------|
| useState | The current state value |
| useReducer | The current state value |
| useRef | The `{ current: ... }` object |
| useMemo | `[computedValue, deps]` |
| useCallback | `[callback, deps]` |
| useEffect | An `Effect` object (with create, destroy, deps, tag) |
| useContext | Nothing (reads from context directly) |

---

## Closure Traps

### The Fundamental Problem

Every render creates a new closure scope. Hooks capture variables from that scope. If a hook or callback doesn't re-execute, it sees **stale** values.

### Stale Closure in setInterval

```tsx
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      // `count` is captured from the render where this effect ran.
      // With [] deps, that's always the initial render where count = 0.
      console.log("Current count:", count); // Always 0
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return <button onClick={() => setCount((c) => c + 1)}>{count}</button>;
}
```

### Stale Closure in Event Handlers Passed to Effects

```tsx
function ChatRoom({ roomId, onMessage }: Props) {
  useEffect(() => {
    const conn = connect(roomId);
    conn.on("message", (msg) => {
      // `onMessage` is captured from the render when this effect ran.
      // If the parent re-renders with a new onMessage, this still calls the OLD one.
      onMessage(msg);
    });
    return () => conn.disconnect();
  }, [roomId]); // onMessage intentionally omitted — but that creates a stale closure
}
```

Adding `onMessage` to deps would disconnect/reconnect on every parent render. This is the exact problem `useEffectEvent` solves (see below).

### Why useRef Solves Stale Closures

A ref is a stable object whose `.current` property is mutable. By writing the latest value to a ref, any closure can read the current value through indirection.

```tsx
function Counter() {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);

  // Keep the ref in sync with the latest count
  useEffect(() => {
    countRef.current = count;
  });

  useEffect(() => {
    const id = setInterval(() => {
      // Reads through the ref — always current
      console.log("Current count:", countRef.current);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return <button onClick={() => setCount((c) => c + 1)}>{count}</button>;
}
```

Pattern: **"latest ref"** — keep a ref in sync with a value, read the ref in long-lived callbacks.

```tsx
function useLatest<T>(value: T): React.RefObject<T> {
  const ref = useRef(value);
  ref.current = value;
  return ref;
}
```

Note: assigning to `ref.current` during render is technically a side effect during render. In strict mode / concurrent features, this can lead to issues. The safer version uses `useLayoutEffect` or `useInsertionEffect` to sync the ref.

---

## useEffect Cleanup Timing — Commit Phase Details

### React's Two-Phase Process

**Render phase** (pure, can be interrupted in concurrent mode):
- React calls your component functions.
- Computes the new virtual DOM.
- Diffs against the current fiber tree.

**Commit phase** (synchronous, cannot be interrupted):
1. **Before mutation**: `getSnapshotBeforeUpdate` (class components).
2. **Mutation**: React applies DOM changes (insertions, updates, deletions).
3. **Layout**: `useLayoutEffect` cleanup from _previous_ render runs, then `useLayoutEffect` setup runs. Refs are attached.
4. **After commit / passive effects** (asynchronous, scheduled via `requestIdleCallback`-like mechanism):
   - `useEffect` cleanup from _previous_ render runs (with previous props/state).
   - `useEffect` setup from _current_ render runs (with current props/state).

### Why Cleanup Runs with Previous Values

Each effect "belongs" to a specific render. The cleanup function closes over the values from that render. This is a feature, not a bug — it guarantees consistency.

```tsx
useEffect(() => {
  const sub = subscribe(props.channelId);
  return () => {
    // `props.channelId` here is the channelId from the render
    // that CREATED this effect, not the current render.
    unsubscribe(props.channelId);
  };
}, [props.channelId]);
```

### Unmount Cleanup

On unmount:
- `useLayoutEffect` cleanup runs synchronously during the mutation phase.
- `useEffect` cleanup runs asynchronously in the passive effects phase.
- All cleanups run in reverse order (last effect cleans up first).

---

## useSyncExternalStore

### When Context Is Wrong

`useContext` triggers re-renders for _all_ consumers when the context value changes, even if a consumer only reads a slice that didn't change. This causes performance problems in large state stores.

```tsx
// Every component using this context re-renders when ANY part of the store changes
const StoreContext = createContext(store);

function UserName() {
  const store = useContext(StoreContext);
  return <span>{store.user.name}</span>;
  // Re-renders even if only `store.cart` changed
}
```

### The Tearing Problem

In concurrent rendering, React can pause a render and resume it later. If an external store changes between pause and resume, different components in the same render can see _different_ snapshots of the store. This is **tearing** — the UI is internally inconsistent.

`useSyncExternalStore` solves this by:
1. Subscribing to the store and forcing a synchronous re-render when it changes.
2. Checking that the snapshot is consistent throughout the render (detecting tearing and falling back to synchronous rendering).

### API

```tsx
const snapshot = useSyncExternalStore(
  subscribe,      // (callback: () => void) => () => void
  getSnapshot,    // () => Snapshot (must return immutable/cached value)
  getServerSnapshot? // () => Snapshot (for SSR)
);
```

### Practical Example: Subscribing to Browser APIs

```tsx
function useOnlineStatus(): boolean {
  return useSyncExternalStore(
    (callback) => {
      window.addEventListener("online", callback);
      window.addEventListener("offline", callback);
      return () => {
        window.removeEventListener("online", callback);
        window.removeEventListener("offline", callback);
      };
    },
    () => navigator.onLine,
    () => true // SSR: assume online
  );
}
```

### Key Gotcha: getSnapshot Must Return a Stable Reference

If `getSnapshot` returns a new object on every call, `useSyncExternalStore` triggers an infinite re-render loop. Always return a cached/memoized value or a primitive.

```tsx
// BAD: new object reference every call
const getSnapshot = () => ({ count: store.getCount() });

// GOOD: return a primitive
const getSnapshot = () => store.getCount();

// GOOD: return a cached object from the store
const getSnapshot = () => store.getState(); // store internally caches this
```

---

## useEffectEvent (Upcoming)

> As of React 19, `useEffectEvent` is still experimental (`react@experimental` channel).
> The concept is stable and likely to ship. Interviewers may ask about the problem it solves.

### The Problem

You have an effect that should re-run when `roomId` changes, but needs to read the latest `onMessage` prop without re-running when `onMessage` changes.

```tsx
// Adding onMessage to deps: effect re-runs on every parent render (bad)
// Omitting onMessage from deps: stale closure (bad)
useEffect(() => {
  const conn = connect(roomId);
  conn.on("message", onMessage);
  return () => conn.disconnect();
}, [roomId, onMessage]); // Which is correct?
```

### The Solution

`useEffectEvent` creates a stable function that always reads the latest props/state but is not treated as a reactive dependency.

```tsx
const onMsg = useEffectEvent((msg: Message) => {
  // Always reads the latest onMessage prop
  onMessage(msg);
});

useEffect(() => {
  const conn = connect(roomId);
  conn.on("message", onMsg); // `onMsg` is stable, not a dependency
  return () => conn.disconnect();
}, [roomId]); // Only re-runs when roomId changes
```

### How It Works Conceptually

```tsx
function useEffectEvent<T extends (...args: any[]) => any>(fn: T): T {
  const ref = useRef(fn);
  useInsertionEffect(() => {
    ref.current = fn;
  });
  return useCallback((...args: any[]) => ref.current(...args), []) as T;
}
```

It's essentially the "latest ref" pattern, but blessed by React so the linter knows it's intentional.

---

## React 19 Hook Changes

### use() — Reading Resources in Render

`use()` is a new API (not technically a hook — it can be called conditionally) that reads the value of a resource (Promise or Context) during render.

```tsx
// Reading a Promise (replaces Suspense + data fetching patterns)
function UserProfile({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise);
  // Suspends if the promise hasn't resolved yet
  return <h1>{user.name}</h1>;
}

// Reading Context (can be called conditionally, unlike useContext)
function Theme({ isEnabled }: { isEnabled: boolean }) {
  if (isEnabled) {
    const theme = use(ThemeContext);
    return <div className={theme.className} />;
  }
  return <div />;
}
```

Key differences from `useContext`:
- `use()` can be called inside conditionals and loops (it's not a hook).
- It works with Promises, not just Context.
- A Promise passed to `use()` must be stable (same reference) across re-renders, otherwise React suspends again.

### Actions

Actions are a new pattern for handling form submissions and async transitions. They build on `useTransition`.

```tsx
function UpdateName() {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  async function handleSubmit() {
    startTransition(async () => {
      const result = await updateNameOnServer(name);
      if (result.error) {
        setError(result.error);
      }
    });
  }

  return (
    <form action={handleSubmit}>
      <input value={name} onChange={(e) => setName(e.target.value)} />
      <button disabled={isPending}>Update</button>
      {error && <p>{error}</p>}
    </form>
  );
}
```

In React 19, `startTransition` accepts async functions. The `isPending` flag stays true until the async function resolves.

### useOptimistic

Provides an optimistic UI value that reverts when the async action completes.

```tsx
function MessageThread({ messages }: { messages: Message[] }) {
  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages,
    (currentMessages, newMessage: string) => [
      ...currentMessages,
      { text: newMessage, sending: true },
    ]
  );

  async function sendMessage(formData: FormData) {
    const text = formData.get("message") as string;
    addOptimistic(text); // Immediately shows the message with sending: true
    await submitMessage(text); // When this resolves, `messages` prop updates, optimistic state resets
  }

  return (
    <form action={sendMessage}>
      {optimisticMessages.map((msg) => (
        <div key={msg.id} style={{ opacity: msg.sending ? 0.5 : 1 }}>
          {msg.text}
        </div>
      ))}
      <input name="message" />
    </form>
  );
}
```

Signature:

```tsx
const [optimisticState, addOptimistic] = useOptimistic<State, OptimisticValue>(
  passthrough,     // the "real" state (from props/server)
  updateFn?        // (currentState, optimisticValue) => newOptimisticState
);
```

When the action completes and the parent re-renders with new props, `optimisticState` resets to `passthrough`.

### useActionState

Manages form action state — combines the action function, pending state, and returned state.

```tsx
async function createUser(prevState: State, formData: FormData): Promise<State> {
  const result = await saveUser(formData);
  if (result.error) return { error: result.error };
  return { error: null, success: true };
}

function SignupForm() {
  const [state, formAction, isPending] = useActionState(createUser, {
    error: null,
  });

  return (
    <form action={formAction}>
      <input name="email" />
      <button disabled={isPending}>Sign up</button>
      {state.error && <p>{state.error}</p>}
    </form>
  );
}
```

Signature:

```tsx
const [state, formAction, isPending] = useActionState(
  action,       // (prevState: S, formData: FormData) => S | Promise<S>
  initialState, // S
  permalink?    // string (for progressive enhancement / SSR)
);
```

- `formAction` is passed to `<form action={...}>` — works with progressive enhancement.
- `isPending` is true while the action is executing.
- `state` holds the last returned value from the action.

### useFormStatus

Reads the status of the parent `<form>` from within a child component. Must be called from a component rendered inside a `<form>`.

```tsx
function SubmitButton() {
  const { pending, data, method, action } = useFormStatus();

  return (
    <button type="submit" disabled={pending}>
      {pending ? "Submitting..." : "Submit"}
    </button>
  );
}

function MyForm() {
  return (
    <form action={handleSubmit}>
      <input name="email" />
      <SubmitButton /> {/* Reads form status from the parent form */}
    </form>
  );
}
```

Key detail: `useFormStatus` reads from the nearest parent `<form>`, not from a form in the same component. The submit button must be a child component.

### React 19 Hook Summary

| Scenario | Hook |
|----------|------|
| External store (Redux, Zustand, browser APIs) | `useSyncExternalStore` |
| Effect reads latest props but shouldn't re-fire | `useEffectEvent` (experimental) |
| Read a Promise during render (Suspense) | `use()` |
| Optimistic UI for async mutations | `useOptimistic` |
| Form action + returned state + pending | `useActionState` |
| Read parent form's pending status | `useFormStatus` |

---

## Common Interview Questions

### Q1: What happens if you call useState inside a condition?

React stores hook state in a linked list indexed by call order. If a hook is conditionally skipped, all subsequent hooks shift position and receive the wrong state. React will likely throw an error: "Rendered fewer/more hooks than during the previous render."

### Q2: Why can't useEffect be async?

`useEffect` expects its callback to return either `undefined` or a cleanup function. An `async` function returns a `Promise`, which React would silently ignore — meaning your cleanup logic never runs. Define the async function inside the effect and call it.

### Q3: How does React know a state update should cause a re-render?

When you call `setState`, React enqueues an update on the fiber node and schedules a re-render. During re-render, it compares the new state with the current state using `Object.is()`. If they're the same, React may bail out (skip rendering children), though it still needs to render the component itself to confirm.

### Q4: When would you use useRef instead of useState?

When you need a mutable value that persists across renders but whose changes should **not** trigger re-renders. Common cases: timer IDs, previous values, DOM element references, tracking whether a component is mounted.

### Q5: Explain the stale closure problem.

When an effect or callback captures a variable from a render's closure, it sees the value _from that render_, not the latest value. If the effect doesn't re-run (because deps haven't changed), it reads an outdated value.

```tsx
const [count, setCount] = useState(0);

useEffect(() => {
  const id = setInterval(() => {
    console.log(count); // Always logs 0 — stale closure
  }, 1000);
  return () => clearInterval(id);
}, []); // Empty deps = effect never re-runs, `count` is always 0
```

Fix: add `count` to deps (interval restarts), use a ref, or use the functional updater `setCount(c => c + 1)`.

### Q6: What is the difference between useLayoutEffect and useEffect?

`useLayoutEffect` fires **synchronously after DOM mutations but before the browser paints**. Use it when you need to measure or mutate the DOM without the user seeing an intermediate state (e.g., positioning a tooltip). `useEffect` fires **after paint** and is non-blocking.

### Q7: Why is dispatch from useReducer referentially stable but setState from useState is too?

Both `dispatch` and `setState` are stable — React guarantees their identity doesn't change across re-renders. The practical difference is that `useReducer` centralizes state transitions in a pure function, making complex logic more testable and `dispatch` more ergonomic to pass down (one function vs. many setters).

### Q8: How does automatic batching work in React 18?

React 18 batches all state updates in a single synchronous execution context into one re-render — regardless of where they originate (event handlers, promises, timeouts, native events). Previously, only React event handlers were batched. Use `flushSync` to opt out when you need an immediate re-render between updates.

### Q9: What problem does useSyncExternalStore solve and when would you use it?

It solves two problems: (1) **Tearing** in concurrent rendering — without it, components reading from an external store can see inconsistent snapshots if the store updates mid-render. (2) **Over-rendering with context** — unlike `useContext`, it lets you subscribe to only the slice you care about.

Use it when writing a library that wraps an external store (Zustand, Redux, Valtio all use it internally), or when subscribing to browser APIs like `navigator.onLine`, `window.matchMedia`, or `localStorage`.

### Q10: What is useEffectEvent and what problem does it solve?

It creates a stable function reference that always reads the latest closure values but is excluded from effect dependency tracking. It solves the dilemma of having an effect that should re-run when certain deps change, but also needs access to other values (like callbacks) that change independently. Without it, you must either add the callback to deps (causing the effect to re-run too often) or omit it (stale closure).
