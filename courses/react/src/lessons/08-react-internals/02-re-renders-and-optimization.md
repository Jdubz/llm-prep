# Re-Renders and Optimization

Understanding when and why React re-renders, and how to control it.

## Table of Contents

1. [Why React Re-Renders](#why-react-re-renders)
2. [Preventing Unnecessary Re-Renders](#preventing-unnecessary-re-renders)
3. [Concurrent Features](#concurrent-features)
4. [The Scheduler and Priority Lanes](#the-scheduler-and-priority-lanes)
5. [Interview Questions](#interview-questions)

---

## Why React Re-Renders

A component re-renders when React needs to recalculate its output. There are exactly six triggers:

### The Six Triggers

**1. State update (`setState` / `useState` setter)**

Any call to a state setter schedules a re-render of that component and its subtree.

```tsx
const [count, setCount] = useState(0);
setCount(1); // triggers re-render
setCount(prev => prev + 1); // also triggers re-render
```

**2. Parent re-render**

When a parent re-renders, React re-renders all its children by default -- even if the child's props did not change. This is the most common source of unexpected re-renders.

```tsx
function Parent() {
  const [count, setCount] = useState(0);
  return (
    <>
      <button onClick={() => setCount(c => c + 1)}>Increment</button>
      <Child name="Alice" /> {/* re-renders on every Parent re-render */}
    </>
  );
}
```

**3. Context value change**

Any component subscribed to a context re-renders whenever the context value changes -- even if the specific value it reads is unchanged (object identity matters).

```tsx
// This creates a new object on every render -> all consumers re-render
<UserContext.Provider value={{ user, logout }}>
```

**4. `forceUpdate()` (class components)**

Bypasses `shouldComponentUpdate` and forces a re-render unconditionally. No functional equivalent; only exists for escape hatches.

**5. Hook state changes**

Internal state in custom hooks and built-in hooks (`useReducer`, `useContext`, `useRef`... wait, not `useRef`) triggers re-renders. Any hook that internally calls `useState` or `useReducer` causes the consuming component to re-render when its state changes.

**6. DevTools and StrictMode**

React 18 StrictMode double-invokes render functions in development to surface side effects. React DevTools can trigger additional renders. These do not happen in production.

### Re-Render Triggers Checklist

```
Re-render checklist -- when does a component re-render?
  [ ] setState / useState setter called (even with same value*)
  [ ] Parent component re-rendered
  [ ] Context value changed (by reference, not deep equality)
  [ ] forceUpdate() called (class components)
  [ ] Custom hook's internal state changed
  [ ] React.StrictMode double-invokes (dev only)

* useState setter with same primitive value is bailed out AFTER render in React 18+
  (the component renders once but no children re-render and no DOM update occurs)
```

### Same-Value Bailout

When you call a state setter with the same value as the current state (determined by `Object.is`), React performs an **early bailout**:

- React may still render the component once to compare
- React will not re-render children
- React will not commit any DOM changes
- This is called an "eager bailout" or "bailout at the component"

```tsx
const [count, setCount] = useState(0);
setCount(0); // React bails out -- no meaningful re-render
setCount({}); // Always re-renders -- new object reference
```

---

## Preventing Unnecessary Re-Renders

### React.memo

Wraps a component so it only re-renders when its props change (shallow comparison by default).

```tsx
// Without memo: re-renders on every parent re-render
function ExpensiveChild({ name, onClick }: { name: string; onClick: () => void }) {
  console.log('rendered');
  return <button onClick={onClick}>{name}</button>;
}

// With memo: skips re-render if name and onClick are the same reference
const ExpensiveChild = React.memo(function ExpensiveChild({
  name,
  onClick,
}: {
  name: string;
  onClick: () => void;
}) {
  console.log('rendered');
  return <button onClick={onClick}>{name}</button>;
});

// Custom comparison
const ExpensiveList = React.memo(
  function ExpensiveList({ items }: { items: Item[] }) {
    return <ul>{items.map(i => <li key={i.id}>{i.name}</li>)}</ul>;
  },
  (prevProps, nextProps) => {
    // Return true to SKIP re-render (props are "equal")
    return prevProps.items.length === nextProps.items.length &&
      prevProps.items.every((item, i) => item.id === nextProps.items[i].id);
  }
);
```

### Stabilizing Props for React.memo

`React.memo` is ineffective if props are unstable references (new objects/functions on every render).

**useCallback -- stable function references**

```tsx
function Parent() {
  const [count, setCount] = useState(0);

  // Without useCallback: new function reference every render -> memo bypassed
  const handleClick = () => setCount(c => c + 1);

  // With useCallback: same reference across renders -> memo works
  const handleClick = useCallback(() => setCount(c => c + 1), []);

  return <MemoizedChild onClick={handleClick} />;
}
```

**useMemo -- stable object/array references**

```tsx
function Parent({ userId }: { userId: string }) {
  const [theme, setTheme] = useState('light');

  // New object on every render if not memoized
  const config = useMemo(
    () => ({ userId, timeout: 5000, retries: 3 }),
    [userId] // only recomputes when userId changes
  );

  return <MemoizedChild config={config} />;
}
```

### useMemo for Context Values

Context uses reference equality. An object literal in JSX creates a new reference every render, causing all consumers to re-render.

```tsx
// BAD: new object every render -> all consumers re-render
function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  return (
    <AuthContext.Provider value={{ user, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// GOOD: stable reference unless user changes
function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const value = useMemo(() => ({ user, setUser }), [user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// BETTER: split state and dispatch contexts
const UserStateContext = createContext<User | null>(null);
const UserDispatchContext = createContext<React.Dispatch<...> | null>(null);

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, dispatch] = useReducer(userReducer, null);
  return (
    <UserStateContext.Provider value={user}>
      <UserDispatchContext.Provider value={dispatch}>
        {children}
      </UserDispatchContext.Provider>
    </UserStateContext.Provider>
  );
}
// Components that only dispatch never re-render on user state changes
```

### Children Composition Pattern

Pass children as props to avoid re-rendering when the parent re-renders.

```tsx
// PROBLEM: SlowComponent re-renders when count changes
function App() {
  const [count, setCount] = useState(0);
  return (
    <div>
      <button onClick={() => setCount(c => c + 1)}>{count}</button>
      <SlowComponent /> {/* always re-renders */}
    </div>
  );
}

// SOLUTION: lift SlowComponent out of the re-rendering scope
function Counter({ children }: { children: React.ReactNode }) {
  const [count, setCount] = useState(0);
  return (
    <div>
      <button onClick={() => setCount(c => c + 1)}>{count}</button>
      {children} {/* React skips re-rendering children whose props didn't change */}
    </div>
  );
}

function App() {
  return (
    <Counter>
      <SlowComponent /> {/* not re-rendered when count changes */}
    </Counter>
  );
}
```

The key insight: `children` is a prop. When `Counter` re-renders due to its own state, the `children` prop value (the React element created in `App`) has not changed reference -- React skips re-rendering it.

### Moving State Down

Isolate frequently-updating state close to where it is used to avoid propagating re-renders up the tree.

```tsx
// BAD: filter state at top level causes entire page to re-render
function ProductPage() {
  const [filter, setFilter] = useState('');
  return (
    <div>
      <Header />         {/* re-renders on every filter change */}
      <Sidebar />        {/* re-renders on every filter change */}
      <input value={filter} onChange={e => setFilter(e.target.value)} />
      <ProductList filter={filter} />
    </div>
  );
}

// GOOD: filter state lives inside the component that needs it
function FilterableProductList() {
  const [filter, setFilter] = useState('');
  return (
    <div>
      <input value={filter} onChange={e => setFilter(e.target.value)} />
      <ProductList filter={filter} />
    </div>
  );
}

function ProductPage() {
  return (
    <div>
      <Header />         {/* never re-renders due to filter */}
      <Sidebar />        {/* never re-renders due to filter */}
      <FilterableProductList />
    </div>
  );
}
```

### Prevention Strategies Table

| Strategy | When to Use | Gotcha |
|---|---|---|
| `React.memo` | Pure components with stable props, expensive renders | Useless if props change every render |
| `useCallback` | Functions passed to memoized children | Always pair with `React.memo` on consumer |
| `useMemo` | Expensive computations, stable object/array props | Don't memoize cheap operations |
| Children pattern | Slow children inside fast-changing parents | Cleaner than memo in many cases |
| Move state down | State only needed in a subtree | Most impactful; reduces scope of re-renders |
| Split context | Context with mixed read/write consumers | Requires more boilerplate |

### "Why Did This Re-Render?" Debugging Steps

```
1. Install React DevTools -> Profiler tab -> enable "Highlight updates"
2. Click Profiler -> Record -> interact -> Stop
3. Click on a bar in the flame graph -> "Why did this render?" panel
   - "Props changed" -> stabilize with useCallback / useMemo / move state down
   - "Context changed" -> split context or memoize context value
   - "Parent rendered" -> wrap child in React.memo or use children pattern
   - "Hooks changed" -> check which hook fired, inspect state transitions
4. Check if React.memo is actually preventing re-renders
   - If memo is not working: a prop is unstable (function, object, array literal)
   - Use useCallback for functions, useMemo for objects/arrays
5. Use why-did-you-render library for automatic detection in dev
```

---

## Concurrent Features

Concurrent React allows the renderer to pause, resume, and abandon work. This means React can keep the UI responsive while doing expensive background rendering.

### startTransition

Marks an update as non-urgent. React can interrupt it to handle more urgent updates (user input).

```tsx
import { startTransition } from 'react';

function SearchInput() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setQuery(value); // Urgent: update input immediately

    startTransition(() => {
      // Non-urgent: expensive filtering can be deferred
      setResults(filterLargeList(value));
    });
  }

  return (
    <>
      <input value={query} onChange={handleChange} />
      <ResultList results={results} />
    </>
  );
}
```

`startTransition` has no pending state indicator. Use `useTransition` if you need that.

### useTransition

Returns `[isPending, startTransition]`. `isPending` is `true` while the transition render is in progress.

```tsx
import { useTransition } from 'react';

function TabContainer() {
  const [isPending, startTransition] = useTransition();
  const [activeTab, setActiveTab] = useState('home');

  function selectTab(tab: string) {
    startTransition(() => {
      setActiveTab(tab);
    });
  }

  return (
    <div>
      <TabButton onClick={() => selectTab('home')}>Home</TabButton>
      <TabButton onClick={() => selectTab('posts')}>Posts</TabButton>

      {isPending && <Spinner />}

      <TabPanel tab={activeTab} /> {/* Can be slow to render */}
    </div>
  );
}
```

Key behavior: if the user clicks a different tab while a transition is pending, React abandons the in-progress render and starts a new one. The UI stays on the old tab (not mid-render garbage) until the new tab is ready.

### useDeferredValue

Defers updating a derived value. Unlike `useTransition`, it works on values you don't control (like props from a parent).

```tsx
import { useDeferredValue, memo } from 'react';

function SearchResults({ query }: { query: string }) {
  const deferredQuery = useDeferredValue(query);
  const isStale = deferredQuery !== query; // true while deferred

  return (
    <div style={{ opacity: isStale ? 0.7 : 1 }}>
      <ExpensiveList query={deferredQuery} />
    </div>
  );
}
```

`useDeferredValue` creates a "stale" version of the value that React updates when it has idle time. The component renders twice:
1. Immediately with the old deferred value (shows stale content)
2. In the background with the new value (when urgent renders are done)

### Suspense + Concurrent Mode

With concurrent React, Suspense boundaries work with transitions to avoid showing stale fallbacks.

```tsx
function App() {
  const [tab, setTab] = useState('home');
  const [isPending, startTransition] = useTransition();

  return (
    <Suspense fallback={<Spinner />}>
      {/* With useTransition, React does NOT show the fallback during transitions.
          It waits for the new content, keeping the old content visible. */}
      <TabContent tab={tab} />
    </Suspense>
  );
}
```

Without `useTransition`, changing `tab` would immediately show the Suspense fallback while the new tab loads. With `useTransition`, React keeps the previous tab visible (stale but complete) until the new tab is ready.

### Concurrent API Quick Reference

| API | Returns | When to Use |
|---|---|---|
| `startTransition(fn)` | nothing | Non-urgent state updates without pending indicator |
| `useTransition()` | `[isPending, startTransition]` | Non-urgent updates where you need loading state |
| `useDeferredValue(value)` | deferred value | Deferring a value you receive as a prop |

**When to use which:**

```
Need to mark a state update as non-urgent?
  -> You own the setState call -> useTransition
  -> Value comes from props   -> useDeferredValue

Need a loading indicator?
  -> useTransition (isPending flag)
  -> startTransition has no pending state

Updating a search input while filtering a large list?
  -> setQuery() urgent (input stays responsive)
  -> setResults() inside startTransition or useDeferredValue on the query
```

---

## The Scheduler and Priority Lanes

### Priority Lanes

React 18 introduced **lanes** -- a bitmask-based priority system for work scheduling. Every update is assigned a lane, and React processes higher-priority lanes first.

```
Lane             Value (bit)   Example Triggers
-----------------------------------------------------------------
SyncLane         0b0001        flushSync, legacy mode setState
InputContinuous  0b0100        scroll events, drag events
Default          0b1000        normal setState, useEffect
Transition(1-16) 0b...         startTransition, useTransition
Retry            0b...         Suspense retry
Idle             0b...         offscreen work
Offscreen        0b...         pre-rendering hidden content
```

Higher-priority lanes (lower bit values) interrupt and preempt lower-priority lanes. React never starves lower-priority work -- it has a timeout mechanism that eventually promotes work to a higher priority.

### Time Slicing

React breaks large rendering work into 5ms chunks ("slices"). After each slice, it checks for higher-priority work via the scheduler.

```
Scheduler uses MessageChannel (not setTimeout) for yielding:
  1. React starts rendering a fiber tree
  2. After ~5ms, checks if there's higher-priority work
  3. If yes: yields control to the browser, posts a MessageChannel message
  4. MessageChannel fires (after paint if needed) -> React resumes
  5. If no higher-priority work: continues the current render
```

`MessageChannel` is preferred over `setTimeout(fn, 0)` because MessageChannel fires without a minimum delay (setTimeout has a 1ms minimum, or 4ms after nesting), making it more responsive.

### How Transitions Get Their Lanes

```tsx
startTransition(() => {
  setTab('posts'); // assigned TransitionLane1
});

// If another transition starts before the first completes:
startTransition(() => {
  setTab('settings'); // assigned TransitionLane2
});

// React can track and cancel individual transitions independently
// The scheduler knows which work to abandon if the user keeps clicking
```

### Lane Entanglement

Some lanes become "entangled" -- they must be processed together. For example, if a sync update happens inside a transition, the transition lane is entangled with the sync lane and gets processed with it. This prevents tearing (showing inconsistent UI states).

### Priority Lanes Summary

```
Urgent (cannot be interrupted):
  SyncLane        -> flushSync, ReactDOM.render (legacy)
  InputContinuous -> continuous user input (scroll, drag)

Normal (can be batched):
  DefaultLane     -> standard setState outside events

Deferrable (can be interrupted and restarted):
  TransitionLanes -> startTransition / useTransition

Background:
  RetryLane       -> Suspense retry
  IdleLane        -> low-priority background work
  OffscreenLane   -> pre-rendering hidden content
```

### The Scheduler Package

React uses `scheduler` (a separate package) for cooperative multitasking. You can use it directly for non-React scheduling needs:

```tsx
import { scheduleCallback, NormalPriority, IdlePriority } from 'scheduler';

// Schedule analytics flush at idle priority (won't block user interactions)
scheduleCallback(IdlePriority, () => {
  flushAnalyticsQueue();
});
```

---

## Interview Questions

**Q7: What changed with batching in React 18?**

Before React 18, batching only happened inside React event handlers. Updates in `setTimeout`, Promises, or native event listeners were NOT batched -- each `setState` call triggered a separate re-render.

```tsx
// React 17: 2 re-renders
setTimeout(() => {
  setCount(c => c + 1); // re-render
  setFlag(f => !f);     // re-render
}, 1000);

// React 18: 1 re-render (automatic batching everywhere)
setTimeout(() => {
  setCount(c => c + 1); // batched
  setFlag(f => !f);     // batched -> single re-render
}, 1000);
```

React 18 enables **automatic batching** in all contexts: event handlers, setTimeout, Promise callbacks, and native event listeners. The implementation uses a scheduler flag (`executionContext`) to accumulate updates and flush them together.

To opt out of batching in React 18 (if you need an intermediate render), use `flushSync`:

```tsx
import { flushSync } from 'react-dom';

flushSync(() => setCount(c => c + 1)); // forces immediate re-render
setFlag(f => !f); // another re-render
```

**Q8: How does selective hydration work with Suspense?**

Selective hydration (React 18) allows React to hydrate parts of the server-rendered HTML independently rather than waiting for the entire page to be ready.

How it works:

1. Server streams HTML with Suspense boundaries. Lazy/async content inside Suspense is initially rendered as the fallback in HTML.
2. The main JS bundle loads and React begins hydrating.
3. Each Suspense boundary can be hydrated independently as its chunk arrives.
4. If the user interacts with a non-yet-hydrated component, React **prioritizes** hydrating that boundary first (synchronously), then continues the rest.

```tsx
// Server sends:
// - Static shell immediately (Header, Nav, Footer)
// - Comments stream in when ready
// - SidePanel streams in when ready

export default function Page() {
  return (
    <>
      <Header />
      <Suspense fallback={<CommentsSkeleton />}>
        <Comments /> {/* hydrated independently */}
      </Suspense>
      <Suspense fallback={<SidePanelSkeleton />}>
        <SidePanel /> {/* hydrated independently */}
      </Suspense>
      <Footer />
    </>
  );
}
```

Without selective hydration, React had to wait for ALL JS to load before hydrating ANYTHING, causing long blocking periods. With selective hydration, each Suspense boundary is a hydration unit -- the page becomes interactive incrementally.

---

## Practice

- **Identify all 6 re-render triggers**: Take a component from your app and list every possible cause of a re-render: (1) own state change, (2) parent re-render, (3) context change, (4) hook state change, (5) forceUpdate, (6) key change. Add `console.log` to verify.
- **Prevent unnecessary re-renders**: Build a parent with 3 children. Wrap one child in `React.memo`. Pass a callback to it. Observe that `React.memo` is defeated by the new function reference. Fix it with `useCallback`.
- **`useTransition` experiment**: Build a tab switcher where one tab renders 10,000 items. Without `useTransition`, observe the UI freeze when switching tabs. Add `useTransition` and verify the old tab stays visible during the transition.
- **Priority lanes tracing**: Open React DevTools with the Profiler and trigger a `startTransition` update. In the flame graph, observe that transition work has lower priority than synchronous updates.
- **Selective hydration observation**: In a Next.js app, wrap a heavy component in `<Suspense>`. Load the page with network throttling. Observe that the rest of the page becomes interactive before the Suspense content loads.

### Related Lessons

- [Fiber & Rendering](01-react-fiber-and-rendering.md) -- virtual DOM, Fiber architecture, render/commit phases, reconciliation, hydration
- [React Internals Deep Dive](03-react-internals-deep-dive.md) -- lane model deep dive, Suspense internals, effect flags, work loop
- [Performance: Rendering & Optimization](../03-performance/01-react-rendering-and-optimization.md) -- practical re-render prevention techniques (memo, useMemo, useCallback, composition)
- [Performance: Tools & Advanced Patterns](../03-performance/02-performance-tools-and-advanced-patterns.md) -- React Profiler, code splitting, virtualization, concurrent rendering case studies
