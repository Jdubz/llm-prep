# React Internals Deep Dive

Advanced implementation details for senior-level understanding of how React works under the hood.

## Table of Contents

1. [Fiber Node Structure](#fiber-node-structure)
2. [The Work Loop](#the-work-loop)
3. [Lane Model Deep Dive](#lane-model-deep-dive)
4. [Suspense Internals](#suspense-internals)
5. [Error Boundary Internals](#error-boundary-internals)
6. [Effect Tracking and Flags](#effect-tracking-and-flags)
7. [Key-Based Reconciliation Edge Cases](#key-based-reconciliation-edge-cases)
8. [createElement vs JSX Transform](#createelement-vs-jsx-transform)
9. [React Without JSX](#react-without-jsx)

---

## Fiber Node Structure

Every React element in the tree corresponds to a **fiber node** -- the unit of work in React's reconciler.

### Full TypeScript Interface

```typescript
interface FiberNode {
  // === Identity ===
  tag: WorkTag;           // 0=FunctionComponent, 1=ClassComponent, 5=HostComponent, etc.
  type: any;              // Component function, class, or string ('div', 'span')
  key: string | null;     // The `key` prop from JSX
  elementType: any;       // Used for lazy components and forwardRef wrappers

  // === Tree Structure ===
  return: FiberNode | null;    // Parent fiber
  child: FiberNode | null;     // First child fiber
  sibling: FiberNode | null;   // Next sibling fiber
  index: number;               // Position among siblings (used for key reconciliation)

  // === DOM / Instance ===
  stateNode: any;         // DOM node for host components, class instance for class components
                          // null for function components

  // === Work-in-Progress vs Current ===
  alternate: FiberNode | null; // The "other" fiber (current <-> workInProgress)

  // === Props and State ===
  pendingProps: any;      // Props being processed in this render
  memoizedProps: any;     // Props from the last committed render
  memoizedState: any;     // State from the last committed render
                          // For function components: pointer to first hook in the linked list
                          // For class components: the state object

  // === Update Queue ===
  updateQueue: UpdateQueue<any> | null;
  // For function components with effects: linked list of effects
  // For class components: queue of setState calls

  // === Hooks (function components only) ===
  // memoizedState points to the first Hook object:
  // Hook { memoizedState, queue, next } -> Hook { ... } -> ...
  // Each hook in call order is a node in this linked list

  // === Effects and Flags ===
  flags: Flags;           // Bitfield: Placement, Update, Deletion, Ref, etc.
  subtreeFlags: Flags;    // Union of all flags in the subtree (React 18+)
  deletions: FiberNode[] | null; // Children scheduled for deletion

  // === Scheduling ===
  lanes: Lanes;           // Priority lanes for this fiber's pending work
  childLanes: Lanes;      // Union of all pending lanes in subtree (for fast skipping)

  // === Ref ===
  ref: RefObject<any> | ((instance: any) => void) | null;
}
```

### WorkTag Values

```typescript
const WorkTags = {
  FunctionComponent:    0,
  ClassComponent:       1,
  IndeterminateComponent: 2,  // Before first render (not yet known if class or function)
  HostRoot:             3,    // The root fiber (ReactDOM.createRoot target)
  HostPortal:           4,
  HostComponent:        5,    // 'div', 'span', native DOM elements
  HostText:             6,    // Text nodes
  Fragment:             7,
  Mode:                 8,
  ContextConsumer:      9,
  ContextProvider:      10,
  ForwardRef:           11,
  Profiler:             12,
  SuspenseComponent:    13,
  MemoComponent:        14,
  SimpleMemoComponent:  15,
  LazyComponent:        16,
  // ...more
};
```

### Hooks Linked List

For function components, `fiber.memoizedState` is a linked list of hook objects, one per hook call (in call order):

```
fiber.memoizedState
  └── Hook #1 (useState)
        memoizedState: 0            // current count value
        queue: UpdateQueue          // pending updates
        next: Hook #2

      Hook #2 (useEffect)
        memoizedState: Effect {     // effect descriptor
          create: () => { ... },
          destroy: () => { ... },
          deps: [count],
          next: Effect              // circular linked list of effects
        }
        queue: null
        next: Hook #3

      Hook #3 (useRef)
        memoizedState: { current: null }
        queue: null
        next: null
```

This is why hooks must be called in the same order every render -- React identifies each hook by its position in the linked list. Conditional hooks would shift the list and corrupt state.

---

## The Work Loop

React processes fibers in a depth-first traversal using two phases: **beginWork** (going down) and **completeWork** (going up).

### workLoopSync vs workLoopConcurrent

```typescript
// Synchronous: processes ALL work without yielding
function workLoopSync() {
  while (workInProgress !== null) {
    performUnitOfWork(workInProgress);
  }
}

// Concurrent: yields to the scheduler every ~5ms
function workLoopConcurrent() {
  while (workInProgress !== null && !shouldYield()) {
    performUnitOfWork(workInProgress);
  }
}
// shouldYield() checks if the current 5ms time slice is exhausted
// or if there is higher-priority work waiting
```

### performUnitOfWork

```typescript
function performUnitOfWork(unitOfWork: FiberNode): void {
  const current = unitOfWork.alternate; // fiber from the committed tree
  let next: FiberNode | null;

  // beginWork: process this fiber, return first child (or null)
  next = beginWork(current, unitOfWork, subtreeRenderLanes);

  unitOfWork.memoizedProps = unitOfWork.pendingProps;

  if (next === null) {
    // No children -> this fiber is complete, go back up
    completeUnitOfWork(unitOfWork);
  } else {
    // Move to the first child
    workInProgress = next;
  }
}
```

### beginWork

`beginWork` processes a fiber based on its `tag` and returns the first child (or null if it's a leaf).

```typescript
function beginWork(
  current: FiberNode | null,
  workInProgress: FiberNode,
  renderLanes: Lanes
): FiberNode | null {
  // Fast path: if no pending work in this subtree, bail out entirely
  if (current !== null) {
    const oldProps = current.memoizedProps;
    const newProps = workInProgress.pendingProps;
    if (oldProps === newProps && !hasContextChanged() && !hasLanesIntersect(workInProgress.lanes, renderLanes)) {
      return bailoutOnAlreadyFinishedWork(current, workInProgress, renderLanes);
    }
  }

  switch (workInProgress.tag) {
    case FunctionComponent:
      return updateFunctionComponent(current, workInProgress, workInProgress.type, workInProgress.pendingProps);
    case ClassComponent:
      return updateClassComponent(current, workInProgress, workInProgress.type, workInProgress.pendingProps);
    case HostComponent:
      return updateHostComponent(current, workInProgress);
    case HostText:
      return null; // text nodes have no children
    // ...
  }
}
```

For function components, `updateFunctionComponent` calls the component function and runs all hooks via `renderWithHooks`.

### completeWork

After beginWork returns null (leaf node), `completeWork` runs. It:
1. Creates the DOM node for host components
2. Appends child DOM nodes to the parent DOM node
3. Bubbles flags from children to the parent (`subtreeFlags`)

```typescript
function completeWork(
  current: FiberNode | null,
  workInProgress: FiberNode,
): FiberNode | null {
  switch (workInProgress.tag) {
    case HostComponent: {
      if (current !== null && workInProgress.stateNode != null) {
        // Update existing DOM node
        updateHostComponent(current, workInProgress);
      } else {
        // Create new DOM node
        const instance = createDOMElement(workInProgress.type, workInProgress.pendingProps);
        appendAllChildren(instance, workInProgress);
        workInProgress.stateNode = instance;
        if (finalizeInitialChildren(instance, workInProgress.type, workInProgress.pendingProps)) {
          markUpdate(workInProgress); // needs focus/autofocus after mount
        }
      }
      bubbleProperties(workInProgress); // propagate flags up
      return null;
    }
    // ...
  }
}
```

### Traversal Order

```
Given tree:
  App
  ├── Header
  └── Main
      ├── Sidebar
      └── Content

beginWork order (top-down, depth-first):
  App -> Header -> Main -> Sidebar -> Content

completeWork order (bottom-up, depth-first):
  Header -> Sidebar -> Content -> Main -> App

The traversal uses the child/sibling/return pointers:
  1. beginWork(App) -> returns Header (first child)
  2. beginWork(Header) -> returns null (leaf)
  3. completeWork(Header) -> move to sibling Main
  4. beginWork(Main) -> returns Sidebar (first child)
  5. beginWork(Sidebar) -> returns null (leaf)
  6. completeWork(Sidebar) -> move to sibling Content
  7. beginWork(Content) -> returns null (leaf)
  8. completeWork(Content) -> no sibling, move to return (Main)
  9. completeWork(Main) -> no sibling, move to return (App)
  10. completeWork(App) -> done
```

---

## Lane Model Deep Dive

### Bitwise Lane Flags

Lanes are represented as 32-bit integers. Each lane is a bit flag, allowing efficient set operations.

```typescript
// Simplified lane values (actual React source uses slightly different values)
export const NoLanes: Lanes = /*                         */ 0b0000000000000000000000000000000;
export const NoLane: Lane =   /*                         */ 0b0000000000000000000000000000000;

export const SyncLane: Lane =                            0b0000000000000000000000000000001;
export const SyncBatchedLane: Lane =                     0b0000000000000000000000000000010;
export const InputContinuousHydrationLane: Lane =        0b0000000000000000000000000000100;
export const InputContinuousLane: Lane =                 0b0000000000000000000000000001000;
export const DefaultHydrationLane: Lane =                0b0000000000000000000000000010000;
export const DefaultLane: Lane =                         0b0000000000000000000000000100000;

// 16 transition lanes (can track 16 independent transitions simultaneously)
export const TransitionLanes: Lanes =                    0b0000000011111111111111111000000;
export const TransitionLane1: Lane =                     0b0000000000000000000000001000000;
// ... TransitionLane2 through TransitionLane16

export const RetryLanes: Lanes =                         0b0000111100000000000000000000000;
export const IdleLane: Lane =                            0b0010000000000000000000000000000;
export const OffscreenLane: Lane =                       0b1000000000000000000000000000000;
```

### Lane Operations

```typescript
// Merge lanes (union)
function mergeLanes(a: Lanes, b: Lanes): Lanes {
  return a | b;
}

// Check if a lane is included in a set
function isSubsetOfLanes(set: Lanes, subset: Lanes): boolean {
  return (set & subset) === subset;
}

// Remove a lane from a set
function removeLanes(set: Lanes, subset: Lanes): Lanes {
  return set & ~subset;
}

// Get the highest-priority lane (lowest bit set)
function getHighestPriorityLane(lanes: Lanes): Lane {
  return lanes & -lanes; // lowest set bit isolation
}
```

### Lane Entanglement

When an urgent update happens during a transition, the transition lane gets "entangled" with the sync lane -- they must be processed together to prevent UI tearing.

```typescript
// Example: user types (sync) while a transition is pending
// Both lanes must be included in the next render
function entangleLanes(root: FiberRoot, lane: Lane): void {
  if (isTransitionLane(lane)) {
    // Find all transitions that overlap with the current transition
    let entangledLanes = root.entangledLanes;
    // Add this lane to the entangled set
    root.entangledLanes = mergeLanes(entangledLanes, lane);
    root.entanglements[laneToIndex(lane)] = mergeLanes(
      root.entanglements[laneToIndex(lane)],
      lane
    );
  }
}
```

### How Transitions Get Their Lanes

React 18 has 16 transition lanes. Each call to `startTransition` gets the next available transition lane (cycling through TransitionLane1..16). If all 16 are in use, they share a lane.

```typescript
let currentEventTransitionLane: Lane = NoLane;

function requestTransitionLane(): Lane {
  if (currentEventTransitionLane === NoLane) {
    // Assign next available transition lane
    currentEventTransitionLane = claimNextTransitionLane();
  }
  return currentEventTransitionLane;
}
// currentEventTransitionLane is reset to NoLane after each event
// Multiple setState calls within one startTransition get the same lane
```

---

## Suspense Internals

### Promise Throwing

When a component is not ready to render (data still loading), it throws a Promise. React catches it at the nearest Suspense boundary.

```typescript
// Simplified: how a data-fetching wrapper might work
function use<T>(promise: Promise<T>): T {
  const result = promiseCache.get(promise);

  if (result === undefined) {
    // Not cached yet -- suspend
    throw promise; // React catches this
  }
  if (result.status === 'pending') {
    throw result.promise; // Still pending -- suspend
  }
  if (result.status === 'rejected') {
    throw result.reason; // Error -- propagate to error boundary
  }
  return result.value; // Resolved -- return the value
}
```

### Fallback Rendering

When a Suspense boundary catches a thrown promise:

1. React marks the fiber with `DidCapture` flag
2. The fiber tree between the boundary and the throwing component is discarded
3. The Suspense boundary renders its `fallback` prop instead
4. React attaches a `.then()` callback to the thrown promise
5. When the promise resolves, React schedules a retry render (RetryLane)

```
Tree:
  <Suspense fallback={<Spinner />}>
    <UserProfile />   <- throws promise
  </Suspense>

On throw:
  1. Suspense fiber gets DidCapture flag
  2. Suspense renders <Spinner /> (the fallback)
  3. promise.then(() => retryDehydratedSuspenseBoundary(suspenseFiber))

On resolve:
  4. React re-renders UserProfile (now returns data, no throw)
  5. Suspense replaces <Spinner /> with <UserProfile /> output
```

### Nested Suspense and Priority

```tsx
<Suspense fallback={<PageSkeleton />}>        {/* outer boundary */}
  <Header />
  <Suspense fallback={<ContentSkeleton />}>   {/* inner boundary */}
    <MainContent />                           {/* throws -> inner catches it */}
  </Suspense>
  <Footer />
</Suspense>
```

React throws to the **nearest** Suspense ancestor. Inner boundaries allow partial fallbacks without hiding the entire page.

With `useTransition`, React will NOT show the fallback during a navigation -- it keeps the previous content visible. Without `useTransition`, the fallback is shown immediately.

---

## Error Boundary Internals

### Class Component Mechanics

Error boundaries must be class components because React needs two lifecycle methods:

```typescript
class ErrorBoundary extends React.Component<Props, State> {
  state = { error: null };

  // Called during the render phase (pure -- no side effects)
  // Returns new state to trigger the error UI render
  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error };
  }

  // Called during the commit phase
  // Used for logging (not for updating state)
  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    logErrorToService(error, info.componentStack);
  }

  render() {
    if (this.state.error) return <ErrorUI error={this.state.error} />;
    return this.props.children;
  }
}
```

### Error Propagation in the Fiber Tree

When an error is thrown during rendering:

1. React searches upward from the throwing fiber for the nearest error boundary fiber
2. All work between the boundary and the throwing fiber is abandoned
3. `getDerivedStateFromError` is called to get new state for the boundary
4. React re-renders the boundary with the error state (showing the fallback UI)
5. `componentDidCatch` is called in the commit phase for logging

### What Error Boundaries Do NOT Catch

```
Not caught by error boundaries:
  - Event handlers (onClick, onChange, etc.)
    -> Use try/catch inside the handler
  - Async code (setTimeout, Promise callbacks)
    -> Error is thrown outside of React's render cycle
  - Server-side rendering errors
    -> Use a top-level try/catch
  - Errors in the error boundary itself
    -> Propagates to the next boundary up
  - Errors during effects (useLayoutEffect, useEffect)
    -> In React 18, these DO propagate to error boundaries
       (changed from React 17 behavior)
```

### Retry After Error

```tsx
function RecoverableErrorBoundary({ children }: { children: React.ReactNode }) {
  const [error, setError] = useState<Error | null>(null);
  const [key, setKey] = useState(0);

  if (error) {
    return (
      <div>
        <p>Something went wrong: {error.message}</p>
        <button onClick={() => { setError(null); setKey(k => k + 1); }}>
          Retry
        </button>
      </div>
    );
  }

  return (
    // key change forces React to unmount/remount the subtree, clearing the error
    <ErrorBoundaryCapture key={key} onError={setError}>
      {children}
    </ErrorBoundaryCapture>
  );
}
```

---

## Effect Tracking and Flags

### Flags Bitfield

React uses bitwise flags to track what work each fiber needs during the commit phase.

```typescript
export const NoFlags       = /*                      */ 0b00000000000000000000000000;
export const Placement     = /*                      */ 0b00000000000000000000000010; // mount/move
export const Update        = /*                      */ 0b00000000000000000000000100; // prop/state update
export const Deletion      = /*                      */ 0b00000000000000000000001000; // unmount
export const ChildDeletion = /*                      */ 0b00000000000000000000010000; // child needs deletion
export const ContentReset  = /*                      */ 0b00000000000000000000100000;
export const Callback      = /*                      */ 0b00000000000000000001000000;
export const DidCapture    = /*                      */ 0b00000000000000000010000000; // Suspense caught
export const Ref           = /*                      */ 0b00000000000000000100000000; // ref attach/detach
export const Snapshot      = /*                      */ 0b00000000000000001000000000; // getSnapshotBeforeUpdate
export const Passive       = /*                      */ 0b00000000000000010000000000; // useEffect
export const PassiveUnmountPendingDev = /*           */ 0b00000000010000000000000000;
export const BeforeMutationMask =                       Snapshot | Passive;
export const MutationMask =                             Placement | Update | ChildDeletion | ContentReset | Ref | Snapshot | Callback;
export const LayoutMask =                               Update | Callback | Ref | Visibility;
export const PassiveMask =                              Passive | ChildDeletion;
```

### subtreeFlags Bubbling (React 18)

In React 17 and earlier, React maintained a linked list of fibers with effects (the "effect list"). React 18 replaced this with `subtreeFlags` -- a union of all descendant flags that is computed during `completeWork` and bubbled up the tree.

```typescript
// During completeWork, after processing a fiber:
function bubbleProperties(completedWork: FiberNode): void {
  const didBailout = completedWork.alternate !== null &&
    completedWork.alternate.child === completedWork.child;

  let subtreeFlags = NoFlags;
  let newChildLanes = NoLanes;

  let child = completedWork.child;
  while (child !== null) {
    if (!didBailout) {
      subtreeFlags |= child.subtreeFlags;
      subtreeFlags |= child.flags;
      newChildLanes = mergeLanes(newChildLanes, mergeLanes(child.lanes, child.childLanes));
    }
    child = child.sibling;
  }

  completedWork.subtreeFlags |= subtreeFlags;
  completedWork.childLanes = newChildLanes;
}
```

### Commit Phase Order

The commit phase is split into three sub-phases:

```
1. Before Mutation (commitBeforeMutationEffects)
   - getSnapshotBeforeUpdate for class components
   - Schedules passive effects (useEffect) via scheduler

2. Mutation (commitMutationEffects)
   - DOM insertions, updates, deletions (Placement, Update, Deletion)
   - Detach old refs
   - Call useLayoutEffect cleanup

3. Layout (commitLayoutEffects)
   - useLayoutEffect setup (fires synchronously after DOM mutations)
   - componentDidMount / componentDidUpdate for class components
   - Attach new refs (ref.current = stateNode)

After commit (async):
4. Passive Effects (flushPassiveEffects)
   - useEffect cleanup from previous render
   - useEffect setup for current render
   - Scheduled via MessageChannel (not synchronous)
```

### Effect Execution Order with Multiple Components

```tsx
function Parent() {
  useEffect(() => {
    console.log('Parent effect');
    return () => console.log('Parent cleanup');
  });

  return <Child />;
}

function Child() {
  useEffect(() => {
    console.log('Child effect');
    return () => console.log('Child cleanup');
  });
  return null;
}

// Mount order:
//   Child effect
//   Parent effect

// Update order (e.g., parent re-renders):
//   Child cleanup
//   Parent cleanup
//   Child effect
//   Parent effect

// Effects fire bottom-up (child before parent), matching DOM insertion order.
// Cleanup fires before the next effect setup, also bottom-up.
```

---

## Key-Based Reconciliation Edge Cases

### Two-Pass Algorithm for Keyed Children

When reconciling a list with keys, React uses a map-based algorithm:

```
Phase 1: Iterate new children while old children match in order
  - Stop when a key mismatch is found

Phase 2: Build a Map<key, oldFiber> from remaining old children
  - For each remaining new child:
    - If key found in map: reuse (update) the existing fiber
    - If key not found: create a new fiber
  - Any fibers left in the map after processing all new children: delete them
```

### Reordering Optimization Limitations

React tracks the `lastPlacedIndex` (the highest index of a reused fiber seen so far). If a reused fiber's old index is >= `lastPlacedIndex`, it stays in place (no DOM move). If its old index is < `lastPlacedIndex`, it is moved.

```
Old list: A(0) B(1) C(2) D(3)
New list: D    A    B    C

Phase 2 map: { A:0, B:1, C:2, D:3 }

Process D: old index=3, lastPlacedIndex=0 -> 3>=0 -> stays, lastPlacedIndex=3
Process A: old index=0, lastPlacedIndex=3 -> 0<3  -> MOVE
Process B: old index=1, lastPlacedIndex=3 -> 1<3  -> MOVE
Process C: old index=2, lastPlacedIndex=3 -> 2<3  -> MOVE

Result: 3 DOM moves

If instead:
New list: A    B    C    D
Process A: old index=0, lastPlacedIndex=0 -> stays, lastPlacedIndex=0
Process B: old index=1, lastPlacedIndex=0 -> stays, lastPlacedIndex=1
Process C: old index=2, lastPlacedIndex=1 -> stays, lastPlacedIndex=2
Process D: old index=3, lastPlacedIndex=2 -> stays, lastPlacedIndex=3
Result: 0 DOM moves
```

The algorithm is optimized for insertions at the end and deletions from the beginning. Reversing a list causes O(n) DOM moves. This is why moving the last item to the front is expensive -- it causes every other item to be "moved."

### Key-Reset Pattern

Use a `key` prop to force React to completely unmount and remount a component subtree:

```tsx
function UserProfile({ userId }: { userId: string }) {
  return (
    // When userId changes, React unmounts and remounts the entire form
    // All state (including nested form fields) is reset
    <ProfileForm key={userId} userId={userId} />
  );
}

// Without key: ProfileForm receives new userId prop but keeps old form state
// With key: ProfileForm is treated as a brand new component instance
```

This is cleaner than manually resetting all state in useEffect when a dependent prop changes.

---

## createElement vs JSX Transform

### Classic Transform (Before React 17)

Before React 17, the JSX transform compiled JSX to `React.createElement` calls. This required `import React from 'react'` in every file with JSX.

```tsx
// Source JSX
const element = <div className="container"><h1>Hello</h1></div>;

// Compiled (classic transform)
const element = React.createElement(
  'div',
  { className: 'container' },
  React.createElement('h1', null, 'Hello')
);
```

### New JSX Transform (React 17+)

The new transform imports `_jsx` and `_jsxs` from `react/jsx-runtime` automatically (no manual import needed). `_jsxs` is used when there are multiple static children.

```tsx
// Source JSX
const element = <div className="container"><h1>Hello</h1></div>;

// Compiled (new transform)
import { jsx as _jsx } from 'react/jsx-runtime';
const element = _jsx('div', {
  className: 'container',
  children: _jsx('h1', { children: 'Hello' })
});
```

### The Return Value: A React Element Object

Both transforms produce a plain JavaScript object:

```typescript
{
  $$typeof: Symbol(react.element),  // Security marker
  type: 'div',                      // String, function, class, or forwardRef
  key: null,
  ref: null,
  props: {
    className: 'container',
    children: {
      $$typeof: Symbol(react.element),
      type: 'h1',
      key: null,
      ref: null,
      props: { children: 'Hello' },
      _owner: null,
    }
  },
  _owner: null,    // Fiber that created this element (for devtools)
}
```

### The $typeof Symbol Security

`$$typeof: Symbol(react.element)` is a defense against XSS. Consider a scenario where a server stores user-provided JSON and that JSON is directly rendered:

```tsx
// Attacker stores in DB: { "type": "script", "props": { "src": "evil.js" } }
const userContent = JSON.parse(attackerJSON); // missing $$typeof
ReactDOM.render(userContent, container);      // Safe! React rejects it
```

`Symbol` values cannot be serialized to JSON. A maliciously crafted JSON object will never have `$$typeof: Symbol(react.element)` -- React checks for this and rejects elements without it. This prevents JSON-injection attacks from executing as React elements.

---

## React Without JSX

Understanding React without JSX reveals the underlying element tree structure directly.

### Building a Component Tree Without JSX

```typescript
import { createElement, useState, Fragment } from 'react';
import { createRoot } from 'react-dom/client';

// Replicating this JSX manually:
// function App() {
//   const [count, setCount] = useState(0);
//   return (
//     <div className="app">
//       <h1>Counter: {count}</h1>
//       <button onClick={() => setCount(c => c + 1)}>Increment</button>
//       <button onClick={() => setCount(c => c - 1)}>Decrement</button>
//     </div>
//   );
// }

function App() {
  const [count, setCount] = useState(0);

  return createElement(
    'div',
    { className: 'app' },
    createElement('h1', null, `Counter: ${count}`),
    createElement('button', { onClick: () => setCount(c => c + 1) }, 'Increment'),
    createElement('button', { onClick: () => setCount(c => c - 1) }, 'Decrement')
  );
}

createRoot(document.getElementById('root')).render(createElement(App, null));
```

### Element Tree vs Fiber Tree

```
createElement output (React element tree -- plain objects, no mutable state):

  { type: App, props: {} }
    rendered to:
      { type: 'div', props: { className: 'app' }, children: [
          { type: 'h1', props: { children: 'Counter: 0' } },
          { type: 'button', props: { onClick: fn, children: 'Increment' } },
          { type: 'button', props: { onClick: fn, children: 'Decrement' } }
      ]}

Fiber tree (mutable, stateful, created by the reconciler):

  FiberNode { tag: HostRoot, stateNode: FiberRootNode }
    child:
    FiberNode { tag: FunctionComponent, type: App, memoizedState: Hook(count=0) }
      child:
      FiberNode { tag: HostComponent, type: 'div', stateNode: <div> }
        child:
        FiberNode { tag: HostComponent, type: 'h1', stateNode: <h1> }
          sibling:
          FiberNode { tag: HostComponent, type: 'button', stateNode: <button> }
            sibling:
            FiberNode { tag: HostComponent, type: 'button', stateNode: <button> }
```

The **element tree** is what your component functions return -- disposable descriptions of UI created fresh every render. The **fiber tree** is what React maintains internally -- a persistent, mutable data structure that tracks component state, effects, and work.

### createElement Signature

```typescript
function createElement(
  type: string | ComponentType,  // 'div', App, React.Fragment, etc.
  props: Record<string, any> | null,
  ...children: ReactNode[]       // Spread or as props.children
): ReactElement;

// children can also be passed in props:
createElement('div', { children: 'Hello' });
// equivalent to:
createElement('div', null, 'Hello');

// Fragment shorthand:
createElement(Fragment, null, child1, child2);
// equivalent to JSX: <>{child1}{child2}</>
```
