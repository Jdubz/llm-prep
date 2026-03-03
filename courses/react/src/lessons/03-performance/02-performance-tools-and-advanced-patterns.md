# 02 — Performance Tools and Advanced Patterns

> Assumes you have read 01-react-rendering-and-optimization.md.
> Covers DevTools Profiler, code splitting, virtualization, Fiber internals, reconciliation deep dive, and interview Q&A.

---

## Table of Contents

1. [React Profiler](#react-profiler)
2. [Code Splitting](#code-splitting)
3. [Virtualization](#virtualization)
4. [Bundle Size Reduction Checklist](#bundle-size-reduction-checklist)
5. [Fiber Architecture](#fiber-architecture)
6. [Reconciliation Algorithm Details](#reconciliation-algorithm-details)
7. [Lane Model](#lane-model)
8. [Concurrent Rendering](#concurrent-rendering)
9. [Selective Hydration](#selective-hydration)
10. [Performance Profiling Workflow](#performance-profiling-workflow)
11. [Real-World Optimization Case Studies](#real-world-optimization-case-studies)
12. [Common Interview Questions](#common-interview-questions)

---

## React Profiler

### DevTools Flame Graph

The React DevTools Profiler records commit-by-commit render information:

1. Open React DevTools -> Profiler tab
2. Click Record
3. Interact with your app
4. Click Stop
5. Analyze the flame graph:
   - **Gray bars**: component did not render in this commit
   - **Blue/green bars**: component rendered (color intensity = render time)
   - **Yellow/red bars**: component was slow to render

Key metrics per commit:
- **Render duration**: time React spent rendering
- **Commit duration**: time React spent committing DOM changes
- **"Why did this render?"**: enable in Profiler settings (gear icon)

### Profiler API (Programmatic)

```tsx
import { Profiler, ProfilerOnRenderCallback } from "react";

const onRender: ProfilerOnRenderCallback = (
  id,           // the "id" prop of the Profiler tree
  phase,        // "mount" | "update" | "nested-update"
  actualDuration,   // time spent rendering the committed update
  baseDuration,     // estimated time to render the entire subtree without memoization
  startTime,        // when React began rendering this update
  commitTime,       // when React committed this update
) => {
  // Send to analytics, log, etc.
  if (actualDuration > 16) {
    console.warn(`Slow render in ${id}: ${actualDuration.toFixed(2)}ms`);
  }
};

function App() {
  return (
    <Profiler id="Dashboard" onRender={onRender}>
      <Dashboard />
    </Profiler>
  );
}
```

### Identifying Wasted Renders

A "wasted render" is one where the component re-rendered but its output didn't change. Detection strategies:

1. **React DevTools "Highlight updates"**: Settings -> General -> "Highlight updates when components render." Flashing borders show which components re-rendered.
2. **"Why did this render?" in Profiler**: Shows whether the render was caused by state change, parent re-render, context change, or hook change.
3. **`baseDuration` vs. `actualDuration`**: If `actualDuration` is close to `baseDuration`, memoization is not helping much.

### Profiling Steps

1. **Reproduce the problem** in a development build with React DevTools installed.
2. **Enable "Highlight updates"** in React DevTools settings to visually see which components re-render.
3. **Record with React Profiler**: Click Record, perform the slow interaction, click Stop.
4. **Analyze the flame graph**: Sort by render duration. Identify the slowest components.
5. **Check "Why did this render?"** for each slow component (enable in Profiler settings).
6. **Record with Chrome Performance tab**: Same interaction. Look for long tasks (>50ms).
7. **Correlate**: Match React commits to Chrome main thread activity.
8. **Apply targeted fix**: Based on the root cause.
9. **Re-profile**: Confirm the fix reduced render time. Compare before/after screenshots.
10. **Test in production build**: Development builds are 3-10x slower. Always validate in production mode.

---

## Code Splitting

### React.lazy + Suspense

```tsx
// Route-based splitting (most common and highest impact)
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Settings = lazy(() => import("./pages/Settings"));
const Analytics = lazy(() => import("./pages/Analytics"));

function App() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </Suspense>
  );
}
```

### Component-Based Splitting

```tsx
// Split a heavy component that's conditionally rendered
const MarkdownEditor = lazy(() => import("./MarkdownEditor"));

function CommentBox({ editing }: { editing: boolean }) {
  return editing ? (
    <Suspense fallback={<TextareaSkeleton />}>
      <MarkdownEditor />
    </Suspense>
  ) : (
    <CommentDisplay />
  );
}
```

### Named Exports with lazy

`React.lazy` requires a default export. For named exports:

```tsx
// Option 1: re-export as default in a barrel file
// chartHelpers.ts
export { BarChart as default } from "./charts";

// Option 2: inline wrapper
const BarChart = lazy(() =>
  import("./charts").then(mod => ({ default: mod.BarChart }))
);
```

### Preloading

```tsx
// Preload on hover — start the download before the user clicks
function NavLink({ to, component }: { to: string; component: () => Promise<any> }) {
  const prefetch = () => component(); // trigger the dynamic import

  return (
    <Link
      to={to}
      onMouseEnter={prefetch}
      onFocus={prefetch}
    >
      {to}
    </Link>
  );
}

// Usage
const Dashboard = lazy(() => import("./pages/Dashboard"));
<NavLink to="/dashboard" component={() => import("./pages/Dashboard")} />
```

### Route-Based vs. Component-Based: Decision Framework

| Factor | Route-based | Component-based |
|--------|-------------|-----------------|
| Impact | High (separate page bundles) | Moderate (deferred heavy widgets) |
| Complexity | Low (natural split point) | Medium (manage loading states) |
| UX risk | Low (users expect page transitions) | Higher (inline loading spinners) |
| When to use | Almost always | Large modals, editors, charts, admin panels |

---

## Virtualization

Virtualization (windowing) renders only the visible items in a long list, plus a small overscan buffer. Instead of mounting 10,000 DOM nodes, you mount ~30.

### react-window (Lightweight)

```tsx
import { FixedSizeList } from "react-window";

interface RowProps {
  index: number;
  style: React.CSSProperties;
  data: Item[];
}

const Row = memo(function Row({ index, style, data }: RowProps) {
  const item = data[index];
  return (
    <div style={style}>
      {item.name} — {item.description}
    </div>
  );
});

function VirtualizedList({ items }: { items: Item[] }) {
  return (
    <FixedSizeList
      height={600}
      width="100%"
      itemCount={items.length}
      itemSize={50}
      itemData={items}
    >
      {Row}
    </FixedSizeList>
  );
}
```

### TanStack Virtual (Framework-Agnostic, More Flexible)

```tsx
import { useVirtualizer } from "@tanstack/react-virtual";

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
    overscan: 5,
  });

  return (
    <div ref={parentRef} style={{ height: 600, overflow: "auto" }}>
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map(virtualRow => (
          <div
            key={virtualRow.key}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: `${virtualRow.size}px`,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### When to Virtualize

- **Do virtualize**: Lists with >100 items, tables with >50 rows, any scroll container where DOM node count causes jank
- **Don't virtualize**: Short lists (<50 items), lists that need to be fully searchable by browser Ctrl+F, cases where the implementation complexity outweighs the performance gain

---

## Bundle Size Reduction Checklist

- [ ] Analyze bundle with `webpack-bundle-analyzer` or `source-map-explorer`
- [ ] Code split all routes with `React.lazy`
- [ ] Dynamic import heavy libraries (chart libs, editors, date pickers)
- [ ] Replace moment.js with date-fns or dayjs (tree-shakeable)
- [ ] Check for duplicate dependencies (`npm ls <package>`)
- [ ] Enable tree shaking (ES modules, `sideEffects: false` in package.json)
- [ ] Use named imports (`import { debounce } from "lodash-es"` not `import _ from "lodash"`)
- [ ] Lazy load below-fold content and modals
- [ ] Compress with gzip/brotli at the CDN or server level
- [ ] Set appropriate `Cache-Control` headers for hashed assets
- [ ] Audit third-party scripts (analytics, chat, ads) for size and load timing
- [ ] Consider lighter alternatives (preact, million.js) for performance-critical widgets

---

## Fiber Architecture

### What Is a Fiber?

A Fiber is a JavaScript object that represents a unit of work. Every React element (component instance, DOM node, fragment) has a corresponding Fiber node. The Fiber tree is React's internal mutable working copy of your component tree.

Key Fiber node fields:

```
{
  tag: FunctionComponent | HostComponent | ...,  // what kind of element
  type: MyComponent | "div" | ...,               // the component function or DOM tag
  key: string | null,
  stateNode: DOM node | null,                    // for host components
  return: Fiber | null,                          // parent
  child: Fiber | null,                           // first child
  sibling: Fiber | null,                         // next sibling
  memoizedState: Hook | null,                    // linked list of hooks
  memoizedProps: Props,
  pendingProps: Props,
  flags: number,                                 // side effects (Placement, Update, Deletion)
  lanes: number,                                 // priority bitmask
  alternate: Fiber | null,                       // the "other" tree (current <-> workInProgress)
}
```

### Double Buffering

React maintains two Fiber trees:

1. **Current tree**: Represents what's currently on screen. React reads from this during the commit phase.
2. **Work-in-progress (WIP) tree**: Built during the render phase. Each Fiber in the current tree has an `alternate` pointing to its WIP counterpart (and vice versa).

When a render completes, React swaps the pointers: the WIP tree becomes the current tree, and the old current tree becomes available for reuse as the next WIP tree. This is analogous to double buffering in graphics rendering.

### The Work Loop

The core of React's render phase is a loop that walks the Fiber tree:

```
function workLoopConcurrent() {
  while (workInProgress !== null && !shouldYield()) {
    performUnitOfWork(workInProgress);
  }
}
```

`performUnitOfWork` does two things:

1. **Begin work**: Calls the component function (or processes the host element), reconciles children, and returns the next child to process.
2. **Complete work**: When a subtree is fully processed, bubbles up — creating DOM nodes, collecting effects.

The traversal is depth-first: go down via `child`, then across via `sibling`, then up via `return`.

### Time Slicing and Interruptible Rendering

The `shouldYield()` check is what makes concurrent rendering possible. It checks whether the browser needs the main thread back (typically using a 5ms deadline via `MessageChannel`). If the deadline has passed:

1. React pauses the work loop
2. Control returns to the browser (for painting, input handling, etc.)
3. React schedules a new task to resume where it left off

This is only possible because the render phase is pure — no DOM mutations, no side effects. React can safely abandon or restart render work.

**Critical constraint**: This means component functions may be called multiple times for a single committed update. Never put side effects in the render path.

---

## Reconciliation Algorithm Details

### Key-Based Matching (Deep Dive)

Without keys, React matches children by index:

```
Old: [A, B, C]
New: [X, A, B, C]

Index-based diff:
  0: A -> X (update)
  1: B -> A (update)
  2: C -> B (update)
  3: (none) -> C (insert)
  // 4 operations, all children updated
```

With keys:

```
Old: [A:a, B:b, C:c]
New: [X:x, A:a, B:b, C:c]

Key-based diff:
  x: (none) -> X (insert)
  a: A -> A (keep)
  b: B -> B (keep)
  c: C -> C (keep)
  // 1 insert, 3 no-ops — much cheaper
```

React builds a map of `key -> Fiber` from the old children, then iterates the new children, looking up each key. Matched Fibers are reused; unmatched old Fibers are deleted; unmatched new elements are inserted.

---

## Lane Model

### What Are Lanes?

Lanes are a bitmask-based priority system introduced in React 18 to replace the older `expirationTime` model. Each update is assigned one or more lane bits, and React processes lanes in priority order.

Key lane levels (from highest to lowest priority):

| Lane | Decimal | Purpose |
|------|---------|---------|
| `SyncLane` | 1 | Discrete user events (click, keypress), `flushSync` |
| `InputContinuousLane` | 4 | Continuous user events (mousemove, scroll) |
| `DefaultLane` | 16 | Normal updates (setState inside setTimeout, fetch callbacks) |
| `TransitionLane1..16` | 64..524288 | `startTransition` updates |
| `IdleLane` | 536870912 | `useDeferredValue`, offscreen updates |

### Batching Semantics

Updates within the same event are batched into the same lane. React processes all updates in a lane together in a single render pass.

```tsx
function handleClick() {
  setA(1); // SyncLane
  setB(2); // SyncLane (same event -> same lane -> batched)
}

function handleClick() {
  setA(1); // SyncLane

  startTransition(() => {
    setB(2); // TransitionLane (different lane -> separate render pass)
  });
}
```

### SyncLane vs. TransitionLane

| Aspect | SyncLane | TransitionLane |
|--------|----------|----------------|
| Interruptible | No | Yes |
| Shows intermediate state | No (committed synchronously) | Yes (can show stale UI with `isPending`) |
| Triggers Suspense fallback | Yes | No (keeps previous UI) |
| Used by | Click, type, flushSync | startTransition, useDeferredValue |

### Lane Entanglement

When React processes a TransitionLane and encounters a SyncLane update mid-render, it abandons the transition render and processes the SyncLane update first. After the sync update commits, React restarts the transition render. This is the mechanism behind `startTransition` keeping inputs responsive.

---

## Concurrent Rendering

### What "Concurrent" Actually Means

Concurrent rendering does **not** mean multi-threaded. JavaScript is single-threaded. "Concurrent" in React means:

1. **Rendering is interruptible**: React can pause a render in progress and resume it later.
2. **Multiple versions of UI can be "in progress"**: React can prepare a new UI in memory without committing it while the old UI remains on screen.
3. **Renders can be abandoned**: If a higher-priority update arrives, React can discard an in-progress render and start over.

### The Scheduler

React's scheduler (`react-reconciler/src/Scheduler.js`) manages work units:

1. Work is enqueued with a priority (lane).
2. The scheduler uses `MessageChannel` (not `requestIdleCallback`) to schedule tasks. `MessageChannel` fires after microtasks but before the next paint, giving predictable 5ms chunks.
3. Higher-priority work preempts lower-priority work.
4. The scheduler tracks multiple pending tasks and interleaves them based on priority and deadlines.

### Practical Implications

- **Component functions may be called but never committed**: If React starts rendering a transition but abandons it, your component ran for nothing. This is fine if your components are pure. It breaks if you have side effects in the render path.
- **State is consistent within a render**: Even though rendering is interruptible, a single component always sees a consistent snapshot of state. React does not mix states from different updates within one render.
- **StrictMode double-invokes**: In development, React intentionally double-invokes component functions, `useMemo`, and `useState` initializers to help you detect impure renders. This is a development-only behavior that does not happen in production.

---

## Selective Hydration

### Streaming SSR + Progressive Hydration

With React 18's `renderToPipeableStream` (Node) or `renderToReadableStream` (Web Streams), the server can stream HTML as it becomes available:

```tsx
// server.ts
import { renderToPipeableStream } from "react-dom/server";

app.get("/", (req, res) => {
  const { pipe } = renderToPipeableStream(<App />, {
    bootstrapScripts: ["/client.js"],
    onShellReady() {
      res.statusCode = 200;
      res.setHeader("Content-Type", "text/html");
      pipe(res);
    },
    onError(error) {
      console.error(error);
      res.statusCode = 500;
    },
  });
});
```

Suspense boundaries define the streaming chunks:

```tsx
function App() {
  return (
    <Layout>
      {/* Shell: streamed immediately */}
      <Header />
      <Suspense fallback={<NavSkeleton />}>
        {/* Streamed when data resolves */}
        <Navigation />
      </Suspense>
      <Suspense fallback={<ContentSkeleton />}>
        {/* Streamed when data resolves */}
        <MainContent />
      </Suspense>
    </Layout>
  );
}
```

### Priority-Based Hydration

Selective hydration allows React to prioritize which parts of the page to hydrate first based on user interaction:

1. HTML arrives from the server (static, not yet interactive)
2. React starts hydrating from the top
3. If the user clicks on an unhydrated Suspense boundary, React **reprioritizes** that boundary's hydration above others
4. The clicked component hydrates first and handles the event

This means a user clicking a button inside a Suspense boundary that hasn't hydrated yet won't experience a dead click — React fast-tracks that region's hydration.

---

## Performance Profiling Workflow

### Combined Chrome DevTools + React Profiler

**Step 1: Chrome Performance Tab (macro-level)**

1. Open Chrome DevTools -> Performance tab
2. Enable "Screenshots" and "Web Vitals"
3. Record the interaction
4. Analyze the main thread flame chart:
   - Long tasks (>50ms) highlighted with red corners
   - Look for "Recalculate Style" and "Layout" (forced reflow)
   - Identify if the bottleneck is JS execution, layout, or paint
5. Check the "Summary" tab for time distribution: Scripting / Rendering / Painting / System / Idle

**Step 2: React DevTools Profiler (component-level)**

1. Record the same interaction in React DevTools Profiler
2. Examine the flame graph:
   - Find the darkest (slowest) bars
   - Check "Why did this render?" for each slow component
   - Compare `actualDuration` to `baseDuration` to assess memoization effectiveness
3. Look at the "Ranked" view to sort components by render time

**Step 3: Correlate**

- A long task in Chrome DevTools that corresponds to a React commit tells you the problem is in render/reconciliation
- A long task after the commit (during layout/paint) suggests DOM-level issues (too many nodes, expensive CSS)
- Frequent short commits may indicate unnecessary re-renders (optimize at the React level)

### Measuring in Production

```tsx
// Report Web Vitals
import { onCLS, onFID, onLCP, onINP, onTTFB } from "web-vitals";

function reportMetric(metric: { name: string; value: number; id: string }) {
  // Send to your analytics backend
  navigator.sendBeacon("/api/metrics", JSON.stringify(metric));
}

onCLS(reportMetric);
onLCP(reportMetric);
onINP(reportMetric);
onTTFB(reportMetric);
```

---

## Real-World Optimization Case Studies

### Case Study 1: Large Form (200+ Fields)

**Problem**: A medical intake form with 200+ fields re-rendered the entire form on every keystroke. Each render took ~80ms, causing visible input lag.

**Root cause**: All form state lived in a single `useReducer` at the top level. Every field change dispatched an action, causing the entire form tree to re-render.

**Solution (layered)**:

1. **State colocation**: Moved each field's local state (value, touched, error) into the field component itself via `useState`. The top-level reducer only held submission-ready data.
2. **React.memo on field components**: Each `FormField` was wrapped in `React.memo`. Since field-level state was now local, parent re-renders didn't cause field re-renders.
3. **Debounced validation**: Cross-field validation (which required the full form state) was debounced to 300ms and wrapped in `startTransition`.
4. **Sectioned context**: Split the single form context into per-section contexts so updating Section A didn't re-render Section B's consumers.

**Result**: Per-keystroke render dropped from ~80ms to ~2ms.

### Case Study 2: Infinite Scroll Feed

**Problem**: A social media-style feed with infinite scroll. After loading ~500 posts, scrolling became janky. Memory usage grew linearly.

**Root cause**: All 500+ post components remained mounted in the DOM. Each post contained images, interactive buttons, and nested comment previews.

**Solution**:

1. **Virtualization with TanStack Virtual**: Only rendered ~15 posts (viewport + overscan). Used `estimateSize` with a measurement cache for variable-height posts.
2. **Image lazy loading**: Used `loading="lazy"` on images and `IntersectionObserver` for eager preloading of the next ~5 images.
3. **Memoized post components**: `React.memo` on `PostCard` with `useCallback` for interaction handlers.
4. **Stale data eviction**: Kept only the most recent ~200 posts in state. Older posts were evicted from the client and re-fetched if the user scrolled back.
5. **Optimistic updates**: Likes, bookmarks, and other interactions updated the local cache immediately via optimistic mutation, avoiding a full re-render from server response.

**Result**: Consistent 60fps scrolling at any feed depth. Memory capped at ~50MB regardless of session length.

### Case Study 3: Real-Time Dashboard

**Problem**: A monitoring dashboard receiving WebSocket updates every 100ms. 12 chart widgets, each with ~1000 data points. The entire page re-rendered on every update, causing ~120ms renders and dropped frames.

**Root cause**: All 12 charts shared a single `DashboardContext` containing the full data state. Every WebSocket message updated this context, triggering all 12 charts to re-render even if only one chart's data changed.

**Solution**:

1. **Per-metric subscriptions**: Replaced the single context with a pub/sub store (inspired by `useSyncExternalStore`). Each chart subscribed only to its own metric stream.

```tsx
function useMetricStream(metricId: string): DataPoint[] {
  return useSyncExternalStore(
    (cb) => metricsStore.subscribe(metricId, cb),
    () => metricsStore.getSnapshot(metricId),
    () => metricsStore.getServerSnapshot(metricId),
  );
}
```

2. **Throttled rendering**: Accumulated WebSocket messages in a buffer and flushed to state at 10fps (every 100ms) using `requestAnimationFrame` batching, rather than rendering on every message.
3. **Canvas-based charts**: Switched from SVG (DOM-based) to Canvas rendering for charts. This eliminated thousands of DOM nodes and moved the rendering bottleneck from the browser's layout engine to GPU-accelerated canvas.
4. **startTransition for non-visible charts**: Charts in collapsed/tabbed sections rendered with `startTransition` so they didn't block the visible charts.

**Result**: Render time dropped from ~120ms to ~8ms per update cycle. Smooth 60fps even with 12 active real-time charts.

---

## Common Interview Questions

### Q1: "A component is re-rendering too often. Walk me through your debugging process."

**Answer**: I'd follow a systematic approach:

1. **Identify the problem**: Use React DevTools Profiler to record and find which components are rendering unnecessarily. Enable "Why did this render?" to see the cause.
2. **Check the render trigger**: Is it a state change, parent re-render, or context change?
3. **For parent re-renders**: Consider whether the child needs to re-render. If it's expensive, wrap it in `React.memo`. Ensure props have stable references — use `useMemo` for objects/arrays and `useCallback` for functions.
4. **For context changes**: Check if the context value is a new object every render. Memoize the context value. Consider splitting the context into smaller contexts so consumers only subscribe to what they need.
5. **For state changes**: Check if state is lifted too high. Consider colocating state closer to where it's used.
6. **Measure the impact**: Use the Profiler to confirm the optimization actually improved performance. Don't optimize blindly.

### Q2: "When would you NOT use React.memo?"

**Answer**: I'd skip `React.memo` when:

- The component is cheap to render (simple UI, few children). The overhead of shallow comparison may exceed the cost of rendering.
- Props change on virtually every render (unstable references that can't easily be stabilized). Memo would run the comparison and then re-render anyway.
- The component is a leaf node with primitive props only and renders in <1ms. Not worth the code complexity.
- The React Compiler is enabled — it handles memoization automatically.
- During early development when the component structure is still evolving. Premature memoization creates maintenance burden.

### Q3: "Explain the difference between useMemo and useCallback."

**Answer**: They serve the same underlying mechanism — caching a value between renders when dependencies haven't changed. `useCallback(fn, deps)` is literally `useMemo(() => fn, deps)`. The difference is intent:

- `useMemo` caches the **return value** of a function (computed data, derived objects, JSX)
- `useCallback` caches the **function itself** (stable identity for callbacks)

Both are for performance. Neither should affect correctness — your code must work identically if React drops the cache.

### Q4: "You have a list of 10,000 items. How do you make it performant?"

**Answer**: Layered approach:

1. **Virtualize first**: Use TanStack Virtual or react-window to render only visible items (~30-50 DOM nodes instead of 10,000).
2. **Memoize row components**: Wrap list items in `React.memo` with stable keys so rows outside the viewport change don't cause re-renders of visible rows.
3. **Stabilize callbacks**: `useCallback` for any handlers passed to row components.
4. **Defer filtering/sorting**: If the list is filterable, use `useDeferredValue` or `startTransition` to keep the UI responsive during expensive recomputation.
5. **Paginate on the server**: If feasible, don't send 10,000 items to the client at all. Use cursor-based pagination.

### Q5: "What is the React Compiler and how does it change performance optimization?"

**Answer**: The React Compiler is a build-time tool that analyzes your components and automatically inserts memoization. It uses a custom Babel plugin to track data dependencies through your component code and inserts fine-grained caching similar to what `useMemo`, `useCallback`, and `React.memo` provide manually.

It ships with React 19 as opt-in. The practical impact is that manual memoization (`useMemo`, `useCallback`, `React.memo`) becomes unnecessary for most cases. The compiler does it better than humans because it can memoize at a granularity that would be impractical to do by hand (individual JSX expressions, intermediate computations).

The key requirement is following the Rules of React — pure components, no mutation during render, hooks at the top level. Code that violates these rules gets skipped by the compiler.

### Q6: "How does startTransition differ from debouncing?"

**Answer**: They solve similar UX problems but work at fundamentally different levels:

- **Debouncing** delays the state update entirely. The user types, and after N ms of inactivity, you update state. The downside is added latency — results always appear N ms after the user stops typing.
- **startTransition** updates state immediately but tells React the render is interruptible. React starts rendering the transition but will abandon that work if a higher-priority update arrives (like another keystroke). There's no artificial delay — if the render completes before the next keystroke, results appear instantly.

`startTransition` also integrates with Suspense boundaries. A transition that triggers a Suspense fallback will keep showing the previous UI (with `isPending`) instead of flashing a loading spinner.

### Q7: "When should you use the key reset pattern vs. useEffect for resetting component state?"

**Answer**: The key reset pattern (`<Component key={id} />`) is preferable when:

- You want to reset **all** state inside a component tree
- The component has complex internal state that's tedious to reset manually
- You want to guarantee a clean slate (equivalent to unmount + remount)

`useEffect` is better when:

- You want to reset only **some** state while preserving others
- The component has expensive initialization that you want to avoid repeating (subscriptions, DOM measurements)
- You need to react to the change with side effects beyond state reset

The key pattern is more declarative and less error-prone. The `useEffect` approach risks missing state variables or running into stale closure issues.

### Q8: "How would you optimize a React app that feels sluggish on initial load?"

**Answer**: Systematic approach, measuring each step:

1. **Analyze the bundle**: Use webpack-bundle-analyzer or equivalent to find the largest chunks. Look for accidentally bundled dev tools, duplicate dependencies, and tree-shaking failures.
2. **Code split routes**: `React.lazy` + `Suspense` for route-level splitting. This is the highest-impact change for initial load.
3. **Defer non-critical JS**: Dynamic imports for features not visible on the initial viewport (modals, below-fold content, admin tools).
4. **Optimize server-side**: If using SSR (Next.js / Remix), ensure streaming is enabled. Use selective hydration to prioritize interactive elements.
5. **Prefetch likely routes**: On hover or during idle time, start loading chunks the user is likely to navigate to.
6. **Audit third-party scripts**: Analytics, chat widgets, and ads often dominate load time. Load them after the main app.
7. **Measure with Lighthouse and Web Vitals**: Focus on LCP, FID/INP, and CLS. These are what users actually perceive.

---

## Summary

| Technique | Purpose | When to Use |
|-----------|---------|-------------|
| `React.memo` | Skip re-rendering when props unchanged | Expensive components with stable props |
| `useMemo` | Cache computed values | Expensive derivations, referential stability |
| `useCallback` | Stable function identity | Callbacks passed to memo'd children |
| React Compiler | Automatic memoization | React 19 projects (opt-in) |
| `React.lazy` | Code splitting | Route-level and heavy component splitting |
| Virtualization | Render only visible items | Lists > 100 items |
| `startTransition` | Mark non-urgent updates | Keeping input responsive during heavy renders |
| `useDeferredValue` | Deferred derived values | Filtering/searching with received props |
| Key reset | Force remount | Resetting all component state |
| Profiler | Measure render performance | Before and after optimization |
