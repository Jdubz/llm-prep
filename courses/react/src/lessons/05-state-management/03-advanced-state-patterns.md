# Advanced State Patterns

Advanced topics that go beyond standard interview prep. These are the concepts that
separate senior from staff-level understanding.

## Table of Contents

1. [State Machines with XState](#state-machines-with-xstate)
2. [Optimistic Updates: Advanced Patterns](#optimistic-updates-advanced-patterns)
3. [State Synchronization: Multiplayer and Collaborative Patterns](#state-synchronization)
4. [Event Sourcing in the Frontend](#event-sourcing-in-the-frontend)
5. [Zustand Internals](#zustand-internals)
6. [Global State Anti-Patterns](#global-state-anti-patterns)
7. [Interview Questions](#interview-questions)

---

## State Machines with XState

### Why State Machines

Most UI bugs are **illegal state combinations**: a modal that is simultaneously open and
loading and errored, a form that can be submitted while already submitting. Boolean flags
multiply combinatorially -- 4 booleans yield 16 possible states, most of which are invalid.

A finite state machine makes impossible states impossible by definition: the system is in
exactly one state at any time, and only explicitly defined transitions are allowed.

### Modeling UI as Finite Automata

```tsx
import { setup, assign, fromPromise } from 'xstate';
import { useMachine } from '@xstate/react';

interface FetchContext {
  data: User[] | null;
  error: string | null;
  retryCount: number;
}

type FetchEvent =
  | { type: 'FETCH' }
  | { type: 'RETRY' };

const fetchMachine = setup({
  types: {
    context: {} as FetchContext,
    events: {} as FetchEvent,
  },
  actors: {
    fetchUsers: fromPromise(async () => {
      const res = await fetch('/api/users');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<User[]>;
    }),
  },
  guards: {
    canRetry: ({ context }) => context.retryCount < 3,
  },
}).createMachine({
  id: 'fetch',
  initial: 'idle',
  context: { data: null, error: null, retryCount: 0 },
  states: {
    idle: {
      on: { FETCH: 'loading' },
    },
    loading: {
      invoke: {
        src: 'fetchUsers',
        onDone: {
          target: 'success',
          actions: assign({ data: ({ event }) => event.output }),
        },
        onError: {
          target: 'error',
          actions: assign({
            error: ({ event }) => (event.error as Error).message,
            retryCount: ({ context }) => context.retryCount + 1,
          }),
        },
      },
    },
    success: {
      on: { FETCH: 'loading' }, // allow refresh
    },
    error: {
      on: {
        RETRY: {
          target: 'loading',
          guard: 'canRetry',
        },
      },
    },
  },
});

function UserList() {
  const [state, send] = useMachine(fetchMachine);

  return (
    <div>
      {state.matches('idle') && (
        <button onClick={() => send({ type: 'FETCH' })}>Load Users</button>
      )}
      {state.matches('loading') && <Spinner />}
      {state.matches('success') && (
        <ul>
          {state.context.data?.map((u) => <li key={u.id}>{u.name}</li>)}
        </ul>
      )}
      {state.matches('error') && (
        <div>
          <p>Error: {state.context.error}</p>
          <button onClick={() => send({ type: 'RETRY' })}>
            Retry ({3 - state.context.retryCount} left)
          </button>
        </div>
      )}
    </div>
  );
}
```

### Guards

Guards are predicates that conditionally allow transitions. They replace scattered
`if` checks in event handlers.

```tsx
guards: {
  canRetry: ({ context }) => context.retryCount < 3,
  isAuthenticated: ({ context }) => context.user !== null,
  hasUnsavedChanges: ({ context }) => context.isDirty,
},
```

### Actions

Side effects that execute during transitions -- not in the destination state, but on the
edge between states.

```tsx
actions: {
  logTransition: ({ event }) => console.log('Transition:', event.type),
  clearError: assign({ error: null }),
  trackAnalytics: ({ context, event }) => {
    analytics.track('state_transition', { event: event.type });
  },
},
```

### Parallel States

Model independent concurrent behaviors within a single machine.

```tsx
const editorMachine = setup({ /* ... */ }).createMachine({
  id: 'editor',
  type: 'parallel',
  states: {
    document: {
      initial: 'clean',
      states: {
        clean: { on: { EDIT: 'dirty' } },
        dirty: {
          on: {
            SAVE: 'saving',
            DISCARD: 'clean',
          },
        },
        saving: {
          invoke: {
            src: 'saveDocument',
            onDone: 'clean',
            onError: 'dirty',
          },
        },
      },
    },
    toolbar: {
      initial: 'collapsed',
      states: {
        collapsed: { on: { TOGGLE_TOOLBAR: 'expanded' } },
        expanded: { on: { TOGGLE_TOOLBAR: 'collapsed' } },
      },
    },
    selection: {
      initial: 'none',
      states: {
        none: { on: { SELECT: 'active' } },
        active: {
          on: {
            DESELECT: 'none',
            SELECT: 'active', // re-enter with new selection
          },
        },
      },
    },
  },
});
```

The document can be `dirty` while the toolbar is `expanded` and the selection is `active` --
all three evolve independently within the same machine.

---

## Optimistic Updates: Advanced Patterns

### Rollback Strategies

The basic TanStack Query optimistic pattern (snapshot -> optimistically update -> rollback on
error) handles the simple case. Production systems face harder problems.

**List mutations with ordering:**

```tsx
const reorderMutation = useMutation({
  mutationFn: (newOrder: string[]) => api.reorderItems(newOrder),
  onMutate: async (newOrder) => {
    await queryClient.cancelQueries({ queryKey: ['items'] });

    const previousItems = queryClient.getQueryData<Item[]>(['items']);

    // Optimistically reorder
    queryClient.setQueryData<Item[]>(['items'], (old) => {
      if (!old) return old;
      const byId = new Map(old.map((item) => [item.id, item]));
      return newOrder.map((id) => byId.get(id)!);
    });

    return { previousItems };
  },
  onError: (_err, _newOrder, context) => {
    // Full rollback -- restore previous order
    if (context?.previousItems) {
      queryClient.setQueryData(['items'], context.previousItems);
    }
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['items'] });
  },
});
```

### Mutation Invalidation and Deduplication

When multiple optimistic mutations are in-flight simultaneously, rollback becomes complex
because you cannot just restore the snapshot from the first mutation -- the second mutation's
snapshot already includes the first mutation's optimistic state.

```tsx
// Pattern: use a mutation queue with sequence numbers
const pendingMutations = useRef(new Map<string, MutationEntry>());

const addItemMutation = useMutation({
  mutationFn: (item: Item) => api.addItem(item),
  onMutate: async (item) => {
    const mutationId = crypto.randomUUID();
    await queryClient.cancelQueries({ queryKey: ['items'] });

    // Track this mutation
    pendingMutations.current.set(mutationId, { item, timestamp: Date.now() });

    // Apply all pending mutations on top of server truth
    queryClient.setQueryData<Item[]>(['items'], (serverItems) => {
      const base = serverItems ?? [];
      return [
        ...base,
        ...Array.from(pendingMutations.current.values()).map((m) => m.item),
      ];
    });

    return { mutationId };
  },
  onSuccess: (_data, _item, context) => {
    pendingMutations.current.delete(context!.mutationId);
  },
  onError: (_err, _item, context) => {
    // Remove failed mutation and recompute
    pendingMutations.current.delete(context!.mutationId);
    queryClient.invalidateQueries({ queryKey: ['items'] });
  },
});
```

### Race Conditions

If mutation A and mutation B are in-flight, and B resolves before A, the `onSettled`
invalidation from B might fetch stale data that does not include A's changes. Solutions:

1. **Debounce invalidation:** Only invalidate after all in-flight mutations settle.
2. **Mutation key grouping:** TanStack Query's `mutationKey` can group related mutations.
3. **Server-side sequencing:** Include a version/sequence number in responses and reject
   stale writes (optimistic concurrency control).

```tsx
const mutation = useMutation({
  mutationKey: ['items', 'update'], // grouped key
  mutationFn: updateItem,
  onSettled: () => {
    // Only invalidate if no other mutations with this key are in-flight
    const pending = queryClient.isMutating({ mutationKey: ['items', 'update'] });
    if (pending === 0) {
      queryClient.invalidateQueries({ queryKey: ['items'] });
    }
  },
});
```

---

## State Synchronization

### Multiplayer / Collaborative Patterns

Real-time collaborative apps (Google Docs, Figma) require state that synchronizes across
multiple clients. React is a rendering layer -- the synchronization engine lives outside it.

**Architecture layers:**

```
[React Component]
        |
  [Sync Engine]  <-->  [WebSocket / WebRTC]  <-->  [Server / Peers]
        |
  [Local State Store]
```

### CRDTs in React

Conflict-free Replicated Data Types (CRDTs) guarantee eventual consistency without
centralized coordination. Libraries like Yjs or Automerge provide CRDT implementations.

```tsx
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { useSyncExternalStore } from 'react';

// Shared Yjs document
const ydoc = new Y.Doc();
const provider = new WebsocketProvider('wss://sync.example.com', 'room-1', ydoc);
const yItems = ydoc.getArray<string>('items');

// Bridge Yjs to React via useSyncExternalStore
function useYArray<T>(yArray: Y.Array<T>): T[] {
  return useSyncExternalStore(
    (callback) => {
      yArray.observe(callback);
      return () => yArray.unobserve(callback);
    },
    () => yArray.toArray(),
    () => [], // server snapshot
  );
}

function CollaborativeList() {
  const items = useYArray(yItems);

  const addItem = (text: string) => {
    yItems.push([text]); // Automatically synced to all peers
  };

  return (
    <ul>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
      <button onClick={() => addItem(`Item ${items.length + 1}`)}>Add</button>
    </ul>
  );
}
```

**Why CRDTs over OT (Operational Transformation):**

- CRDTs are commutative and associative: operations can arrive out of order.
- No central server required for conflict resolution (peer-to-peer capable).
- Simpler mental model: "merge everything, conflicts resolve automatically."
- Trade-off: slightly larger data structures due to metadata (tombstones, vector clocks).

### Presence State

Collaborative apps also need ephemeral presence state (cursor positions, selection ranges,
"who is online").

```tsx
const awarenessStates = provider.awareness;

// Broadcast local cursor position
awarenessStates.setLocalStateField('cursor', { x: 100, y: 200, user: 'Alice' });

// Subscribe to all awareness states
function usePeerCursors() {
  return useSyncExternalStore(
    (cb) => {
      awarenessStates.on('change', cb);
      return () => awarenessStates.off('change', cb);
    },
    () => {
      const states = Array.from(awarenessStates.getStates().entries());
      return states
        .filter(([clientId]) => clientId !== ydoc.clientID)
        .map(([, state]) => state.cursor)
        .filter(Boolean);
    },
    () => [],
  );
}
```

---

## Event Sourcing in the Frontend

### Undo/Redo with Action History

Instead of storing snapshots of state, store the sequence of actions that produced it.
Undo = remove the last action and replay the rest.

```tsx
import { useReducer, useCallback } from 'react';

interface HistoryState<S> {
  past: S[];
  present: S;
  future: S[];
}

type HistoryAction<A> =
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'ACTION'; action: A };

function createUndoableReducer<S, A>(
  reducer: (state: S, action: A) => S,
) {
  return function undoableReducer(
    state: HistoryState<S>,
    historyAction: HistoryAction<A>,
  ): HistoryState<S> {
    switch (historyAction.type) {
      case 'UNDO': {
        if (state.past.length === 0) return state;
        const previous = state.past[state.past.length - 1];
        return {
          past: state.past.slice(0, -1),
          present: previous,
          future: [state.present, ...state.future],
        };
      }
      case 'REDO': {
        if (state.future.length === 0) return state;
        const next = state.future[0];
        return {
          past: [...state.past, state.present],
          present: next,
          future: state.future.slice(1),
        };
      }
      case 'ACTION': {
        const newPresent = reducer(state.present, historyAction.action);
        if (newPresent === state.present) return state; // no change, no history entry
        return {
          past: [...state.past, state.present],
          present: newPresent,
          future: [], // clear redo stack on new action
        };
      }
    }
  };
}

// Usage
interface CanvasState {
  shapes: Shape[];
  selectedId: string | null;
}

type CanvasAction =
  | { type: 'ADD_SHAPE'; shape: Shape }
  | { type: 'MOVE_SHAPE'; id: string; x: number; y: number }
  | { type: 'DELETE_SHAPE'; id: string }
  | { type: 'SELECT'; id: string | null };

function canvasReducer(state: CanvasState, action: CanvasAction): CanvasState {
  switch (action.type) {
    case 'ADD_SHAPE':
      return { ...state, shapes: [...state.shapes, action.shape] };
    case 'MOVE_SHAPE':
      return {
        ...state,
        shapes: state.shapes.map((s) =>
          s.id === action.id ? { ...s, x: action.x, y: action.y } : s,
        ),
      };
    case 'DELETE_SHAPE':
      return {
        ...state,
        shapes: state.shapes.filter((s) => s.id !== action.id),
        selectedId:
          state.selectedId === action.id ? null : state.selectedId,
      };
    case 'SELECT':
      return { ...state, selectedId: action.id };
  }
}

const undoableCanvasReducer = createUndoableReducer(canvasReducer);

function Canvas() {
  const [state, dispatch] = useReducer(undoableCanvasReducer, {
    past: [],
    present: { shapes: [], selectedId: null },
    future: [],
  });

  const canUndo = state.past.length > 0;
  const canRedo = state.future.length > 0;

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.metaKey && e.key === 'z' && !e.shiftKey && canUndo) {
        dispatch({ type: 'UNDO' });
      }
      if (e.metaKey && e.key === 'z' && e.shiftKey && canRedo) {
        dispatch({ type: 'REDO' });
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [canUndo, canRedo]);

  const addShape = useCallback((shape: Shape) => {
    dispatch({ type: 'ACTION', action: { type: 'ADD_SHAPE', shape } });
  }, []);

  return (
    <div>
      <Toolbar
        canUndo={canUndo}
        canRedo={canRedo}
        onUndo={() => dispatch({ type: 'UNDO' })}
        onRedo={() => dispatch({ type: 'REDO' })}
      />
      <CanvasArea shapes={state.present.shapes} onAddShape={addShape} />
    </div>
  );
}
```

### Selective Undo

Not all actions should be undoable. Selection changes, for instance, clutter the history.
Filter them out:

```tsx
case 'ACTION': {
  const newPresent = reducer(state.present, historyAction.action);
  if (newPresent === state.present) return state;

  // Skip certain actions from history
  const nonUndoable = ['SELECT', 'HOVER'];
  if (nonUndoable.includes(historyAction.action.type)) {
    return { ...state, present: newPresent };
  }

  return {
    past: [...state.past, state.present],
    present: newPresent,
    future: [],
  };
}
```

---

## Zustand Internals

Understanding how Zustand works under the hood explains why it outperforms Context.

### The Core: subscribe + getState + setState

Zustand's store is fundamentally a vanilla JavaScript object with three methods:

```tsx
// Simplified Zustand core (~30 lines)
function createStore<T>(initializer: (set: SetState<T>, get: GetState<T>) => T) {
  let state: T;
  const listeners = new Set<(state: T, prevState: T) => void>();

  const getState = () => state;

  const setState: SetState<T> = (partial) => {
    const nextState =
      typeof partial === 'function'
        ? (partial as (s: T) => Partial<T>)(state)
        : partial;

    // Only notify if something actually changed (Object.is on merged result)
    const merged = { ...state, ...nextState };
    if (!Object.is(state, merged)) {
      const prevState = state;
      state = merged;
      listeners.forEach((listener) => listener(state, prevState));
    }
  };

  // Initialize
  state = initializer(setState, getState);

  const subscribe = (listener: (state: T, prevState: T) => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  return { getState, setState, subscribe };
}
```

### How the React Hook Avoids Re-Renders

The `useStore` hook (which `create` returns) uses `useSyncExternalStore` internally:

```tsx
function useStore<T, U>(
  store: StoreApi<T>,
  selector: (state: T) => U,
  equalityFn: (a: U, b: U) => boolean = Object.is,
): U {
  return useSyncExternalStore(
    store.subscribe,
    () => selector(store.getState()),
    () => selector(store.getState()), // server snapshot
  );
}
```

The critical insight: `useSyncExternalStore` calls the selector on every state change but
only triggers a React re-render if the selected value has changed according to the equality
function. This is fundamentally different from Context, where React re-renders every
consumer whenever the provider value reference changes -- there is no selector layer.

### Why No Provider

Zustand stores live outside the React tree as plain JavaScript modules. The hook subscribes
to the external store via `useSyncExternalStore`. This means:

- No provider wrapper needed.
- The store is a singleton by default (module scope).
- You can read/write the store from non-React code (middleware, event handlers, tests).
- Multiple React roots can share the same store.

### Trade-off: Testing

The singleton nature means tests must reset store state between tests:

```tsx
// In test setup
afterEach(() => {
  useBearStore.setState({ bears: 0 }); // reset to initial
});
```

Or create scoped stores using the `createStore` API (without the hook) and inject via Context
when you need per-test isolation.

---

## Global State Anti-Patterns

### Prop Drilling: The Problem That Is Not Always a Problem

Prop drilling is passing props through intermediate components that do not use them. It is
often cited as the reason to adopt global state, but mild prop drilling (2-3 levels) is
perfectly fine and has advantages:

- **Explicit data flow** -- you can trace where data comes from by reading the code.
- **Refactoring safety** -- TypeScript catches broken prop chains at compile time.
- **No hidden dependencies** -- the component's interface declares what it needs.

Prop drilling becomes a problem at 4+ levels, or when intermediate components must know
about types they have no business knowing about.

### Over-Globalization: The Opposite Problem

The reflexive response to prop drilling is to put everything in a global store. This creates
a different set of issues:

```tsx
// ANTI-PATTERN: tooltip state in a global store
const useAppStore = create((set) => ({
  tooltipVisible: false,          // why is this global?
  tooltipContent: '',             // a tooltip is local UI state
  showTooltip: (content: string) =>
    set({ tooltipVisible: true, tooltipContent: content }),
  hideTooltip: () =>
    set({ tooltipVisible: false, tooltipContent: '' }),
}));
```

Problems with over-globalization:

1. **Zombie state** -- the tooltip store persists even after the component unmounts.
2. **Implicit coupling** -- any component can read/write the tooltip, creating hidden
   dependencies.
3. **Testing complexity** -- tests must initialize the global store with tooltip state.
4. **Naming collisions** -- multiple tooltips? Now you need `tooltip1Visible`,
   `tooltip2Visible`.

### The "God Store" Anti-Pattern

A single store that contains all application state:

```tsx
// ANTI-PATTERN
const useStore = create((set) => ({
  // Auth
  user: null,
  login: (user) => set({ user }),
  // Cart
  items: [],
  addItem: (item) => set((s) => ({ items: [...s.items, item] })),
  // UI
  sidebarOpen: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  // Search
  query: '',
  setQuery: (q) => set({ query: q }),
  // ... 50 more fields
}));
```

This recreates the Redux monolith problem that Zustand was designed to avoid. Instead,
create multiple small, focused stores:

```tsx
const useAuthStore = create<AuthState>(/* ... */);
const useCartStore = create<CartState>(/* ... */);
const useUIStore = create<UIState>(/* ... */);
```

Each store is independently testable, independently code-splittable, and its consumers
only re-render when the relevant slice changes.

### Finding the Balance

The decision tree:

```
Is the state used by only this component?
  YES -> useState / useReducer (local)

Is it used by this component and its direct children?
  YES -> Props (explicit, type-safe)

Is it used by siblings that share a parent?
  YES -> Lift state to parent, pass as props

Is it used by deeply nested or distant components?
  Does it change infrequently (theme, auth, locale)?
    YES -> Context
  Does it change frequently and need selector-based subscriptions?
    YES -> Zustand / Jotai

Is it data from a server API?
  YES -> TanStack Query (it is NOT global state, it is a cache)

Should it survive page refresh / be shareable via URL?
  YES -> URL state (useSearchParams, nuqs)
```

---

## Interview Questions

### Q1: How do you decide between Context, Zustand, and Redux for global state?

**A:** Context is best for low-frequency values like theme or locale -- it has no selector
mechanism so every consumer re-renders on any change. Zustand is the modern default for
client-side global state: zero boilerplate, selector-based subscriptions, excellent
performance. Redux (via RTK) is justified on large teams that need strict conventions,
mature middleware, and time-travel debugging, or when RTK Query is already handling server
state. For most apps in 2025/2026, Zustand is the pragmatic choice.

### Q2: What is the stale-while-revalidate pattern and why does TanStack Query use it?

**A:** Stale-while-revalidate serves cached (potentially stale) data immediately while
silently refetching in the background. This gives users instant UI instead of loading
spinners, while still converging to fresh data. TanStack Query implements this via
`staleTime` (how long data is considered fresh) and automatic background refetches on
window focus, reconnect, or interval.

### Q3: When should you use useReducer instead of useState?

**A:** Use `useReducer` when a single user action updates multiple related fields (coupled
transitions), when the next state depends on the previous in complex ways, when you want
testable pure-function transitions, or when you need a stable `dispatch` reference to
pass to memoized children. Use `useState` for simple, independent pieces of state.

### Q4: How do you prevent Context from causing unnecessary re-renders?

**A:** Three techniques: (1) Split a mega-context into smaller, focused contexts so
consumers only subscribe to what they need. (2) Memoize the context value with `useMemo` to
avoid new object references on every provider render. (3) Separate state and dispatch into
two contexts so components that only dispatch actions do not re-render on state changes.

### Q5: What is the difference between server state and client state?

**A:** Server state is data whose source of truth is a remote server -- it is asynchronous,
can be stale, and has shared ownership (other users/systems can modify it). Client state
is data created and owned by the browser session (UI state, form state, user preferences).
Conflating the two leads to bugs: treating server data as client state means stale caches,
no background refetching, and manual cache invalidation. Use TanStack Query / SWR for
server state and useState / Zustand / Jotai for client state.

### Q6: How does Zustand avoid re-renders compared to Context?

**A:** Zustand uses an external store with a `subscribe` + `selector` pattern. When state
changes, Zustand runs each component's selector against the new state and compares the
result (shallow equality by default) to the previous result. If the selected slice has not
changed, the component does not re-render. Context has no such mechanism -- every consumer
re-renders when the provider value changes.

### Q7: Why use React Hook Form over controlled inputs?

**A:** Controlled inputs re-render the form component on every keystroke because each
change flows through React state. React Hook Form uses uncontrolled inputs where the DOM
holds the values, resulting in zero re-renders during typing. It only triggers re-renders
on validation events or submission. For large forms (10+ fields), this eliminates the
cumulative re-render cost that makes controlled forms feel sluggish.

### Q8: What is state colocation and why does it matter?

**A:** State colocation means keeping state as close to where it is consumed as possible.
It matters because state at the wrong level causes either unnecessary prop drilling (too
high) or duplicated state (too low). Start with `useState` in the component, lift only
when a sibling needs it, use Context or an external store only when the state crosses
deep or disparate parts of the tree. This keeps components self-contained and minimizes
the blast radius of state changes.

### Q9: When would you use XState instead of useReducer?

**A:** Use XState when: (1) the component has many boolean flags that combine into illegal
states -- XState's FSM makes impossible states unrepresentable; (2) you need explicit
transition guards (e.g., "only retry if retryCount < 3"); (3) you need to model parallel
independent behaviors within one entity (document state + toolbar state + selection state
in one machine); (4) the state flow needs to be visualized or communicated to non-engineers.
Use `useReducer` for simpler coupled state where the overhead of XState is not justified.

### Q10: How do CRDTs differ from Operational Transformation for collaborative editing?

**A:** Both solve the problem of merging concurrent edits from multiple clients. OT requires
a central server to serialize and transform operations -- operations that arrive out of order
must be transformed against each other, which requires O(n^2) transformations in the worst
case. CRDTs are commutative and associative data structures where all operations can be
applied in any order and produce the same result. This enables peer-to-peer sync without
central coordination. The trade-off: CRDT data structures are larger (they carry tombstones
and vector clock metadata). Libraries like Yjs integrate with React via `useSyncExternalStore`.

---

## Practice

- **XState exercise**: Model a multi-step checkout flow (cart -> shipping -> payment -> confirmation) as a state machine. Add guards (e.g., "only proceed to payment if shipping address is valid") and parallel states (e.g., "loading payment methods" while the user fills in shipping).
- **Optimistic update**: Build a todo list with TanStack Query mutations. Implement optimistic toggling of a todo's `completed` status. Verify: (1) UI updates instantly, (2) on error, the previous state is restored, (3) `onSettled` invalidates the query for eventual consistency.
- **Undo/redo with event sourcing**: Build a simple drawing app (or text editor) that stores actions as an event log. Implement undo (pop from history, replay remaining events) and redo (push popped event back). Use `useReducer` for the state machine.
- **Zustand internals walkthrough**: Read through the simplified `createStore` implementation in this lesson. Add a `subscribe` middleware that logs every state change. Verify it works by wiring it up to a real component.
- **State anti-pattern audit**: Review a real codebase (or your own) for the anti-patterns listed in this lesson: god store, over-globalized UI state, server data in client state. Propose refactors.

### Related Lessons

- [State Management Fundamentals](01-state-management-fundamentals.md) -- `useState`, `useReducer`, Context fundamentals this lesson extends
- [State Libraries & Solutions](02-state-libraries-and-solutions.md) -- Zustand, Jotai, TanStack Query used in the patterns above
- [Hooks & State Management](../01-hooks-deep-dive/01-hooks-and-state-management.md) -- `useSyncExternalStore` used by Zustand, `useReducer` used by XState patterns
- [Performance: Rendering & Optimization](../03-performance/01-react-rendering-and-optimization.md) -- how selector-based subscriptions and Context splitting affect re-render performance
