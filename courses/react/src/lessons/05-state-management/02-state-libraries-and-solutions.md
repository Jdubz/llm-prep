# State Libraries and Solutions

## Table of Contents

1. [Zustand](#zustand)
2. [Jotai](#jotai)
3. [Redux Toolkit (RTK)](#redux-toolkit-rtk)
4. [Server State with TanStack Query](#server-state-with-tanstack-query)
5. [State Library Comparison](#state-library-comparison)
6. [Decision Tree](#decision-tree)
7. [Common Gotchas](#common-gotchas)

---

## Zustand

Zustand is a minimal, unopinionated state management library. It is the most popular
alternative to Redux as of 2025/2026 and a strong default choice for global client state.

### Minimal API

A store is a hook. No providers, no boilerplate.

```tsx
import { create } from 'zustand';

interface BearState {
  bears: number;
  increasePopulation: () => void;
  removeAllBears: () => void;
}

const useBearStore = create<BearState>((set) => ({
  bears: 0,
  increasePopulation: () => set((state) => ({ bears: state.bears + 1 })),
  removeAllBears: () => set({ bears: 0 }),
}));

function BearCounter() {
  const bears = useBearStore((state) => state.bears);
  return <h1>{bears} bears around here...</h1>;
}

function Controls() {
  const increasePopulation = useBearStore((state) => state.increasePopulation);
  return <button onClick={increasePopulation}>one up</button>;
}
```

### Selector-Based Re-Renders

The key performance advantage: passing a selector to the hook means the component only
re-renders when the *selected slice* changes (shallow equality by default).

```tsx
// Only re-renders when `bears` changes, not when other fields change
const bears = useBearStore((state) => state.bears);

// Multiple selectors with useShallow for object slices
import { useShallow } from 'zustand/react/shallow';

const { bears, fish } = useBearStore(
  useShallow((state) => ({ bears: state.bears, fish: state.fish })),
);
```

### Middleware

Zustand uses a composable middleware pattern.

```tsx
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface TodoState {
  todos: Todo[];
  addTodo: (text: string) => void;
  toggleTodo: (id: string) => void;
}

const useTodoStore = create<TodoState>()(
  devtools(
    persist(
      immer((set) => ({
        todos: [],
        addTodo: (text) =>
          set((state) => {
            // immer allows direct mutation syntax
            state.todos.push({ id: crypto.randomUUID(), text, done: false });
          }),
        toggleTodo: (id) =>
          set((state) => {
            const todo = state.todos.find((t) => t.id === id);
            if (todo) todo.done = !todo.done;
          }),
      })),
      { name: 'todo-storage' }, // persist key
    ),
    { name: 'TodoStore' }, // devtools label
  ),
);
```

**Middleware stack (inner to outer):**

| Middleware | Purpose |
|-----------|---------|
| `immer` | Write mutations instead of spread-heavy immutable updates |
| `persist` | Serialize to localStorage/sessionStorage/AsyncStorage |
| `devtools` | Redux DevTools integration |
| `subscribeWithSelector` | Subscribe to slices outside React |

### Zustand Store Template (Complete)

```tsx
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface MyState {
  items: Item[];
  isLoading: boolean;
}

interface MyActions {
  addItem: (item: Item) => void;
  removeItem: (id: string) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

const initialState: MyState = {
  items: [],
  isLoading: false,
};

export const useMyStore = create<MyState & MyActions>()(
  devtools(
    persist(
      immer((set) => ({
        ...initialState,

        addItem: (item) =>
          set((state) => {
            state.items.push(item);
          }),

        removeItem: (id) =>
          set((state) => {
            state.items = state.items.filter((i) => i.id !== id);
          }),

        setLoading: (loading) => set({ isLoading: loading }),

        reset: () => set(initialState),
      })),
      { name: 'my-store' },
    ),
    { name: 'MyStore' },
  ),
);

// Usage with selectors (component only re-renders when selected slice changes)
function ItemCount() {
  const count = useMyStore((s) => s.items.length);
  return <span>{count}</span>;
}
```

### Zustand vs Redux

| Dimension | Zustand | Redux Toolkit |
|-----------|---------|--------------|
| Boilerplate | Minimal (one `create` call) | Moderate (configureStore, createSlice) |
| Provider required | No | Yes (`<Provider store={store}>`) |
| Middleware | Composable functions | Redux middleware chain |
| Selectors | Built into the hook | `useSelector` + reselect |
| DevTools | Via middleware | Built-in |
| Bundle size | ~1 KB | ~11 KB (RTK) |
| Learning curve | Low | Moderate |
| Best for | Most apps, especially small-to-medium | Large teams needing strict conventions |

---

## Jotai

Jotai implements a bottom-up (atomic) state model inspired by Recoil but with a simpler API
and no string keys.

### Atomic State Model

Instead of a single store, state is defined as independent atoms. Components subscribe to
exactly the atoms they need.

```tsx
import { atom, useAtom, useAtomValue, useSetAtom } from 'jotai';

// Primitive atom
const countAtom = atom(0);

// Read-only derived atom
const doubleCountAtom = atom((get) => get(countAtom) * 2);

function Counter() {
  const [count, setCount] = useAtom(countAtom);
  const doubled = useAtomValue(doubleCountAtom); // read-only hook

  return (
    <div>
      <p>{count} (doubled: {doubled})</p>
      <button onClick={() => setCount((c) => c + 1)}>+1</button>
    </div>
  );
}

function ResetButton() {
  const setCount = useSetAtom(countAtom); // write-only hook, no re-render on read
  return <button onClick={() => setCount(0)}>Reset</button>;
}
```

### Derived Atoms

Derived atoms are the composability primitive. They can depend on multiple atoms and the
dependency graph is tracked automatically.

```tsx
const usersAtom = atom<User[]>([]);
const searchAtom = atom('');

const filteredUsersAtom = atom((get) => {
  const users = get(usersAtom);
  const search = get(searchAtom).toLowerCase();
  if (!search) return users;
  return users.filter((u) => u.name.toLowerCase().includes(search));
});
```

When `searchAtom` changes, only components subscribed to `filteredUsersAtom` re-render --
not those subscribed to `usersAtom` alone.

### Async Atoms

```tsx
const userAtom = atom(async () => {
  const res = await fetch('/api/user');
  return res.json() as Promise<User>;
});

// Write-read async atom
const userWithRefetchAtom = atom(
  async (get) => {
    // triggers Suspense
    const res = await fetch('/api/user');
    return res.json() as Promise<User>;
  },
  async (_get, set) => {
    // write function = refetch
    const res = await fetch('/api/user');
    const user = await res.json();
    set(userWithRefetchAtom, user);
  },
);
```

Async atoms integrate with React Suspense out of the box.

### When Atomic State Shines

- You have many **independent but composable** pieces of state (think spreadsheet cells).
- You want **fine-grained** re-renders without manually writing selectors.
- You are building something with a **graph-like** dependency structure (editors, dashboards).
- You want **code splitting** -- atoms can be defined in any module, no single store file.

---

## Redux Toolkit (RTK)

Redux is not dead. RTK dramatically reduced boilerplate and remains the right choice in
specific scenarios.

### createSlice

```tsx
import { createSlice, configureStore, type PayloadAction } from '@reduxjs/toolkit';

interface CounterState {
  value: number;
}

const counterSlice = createSlice({
  name: 'counter',
  initialState: { value: 0 } satisfies CounterState as CounterState,
  reducers: {
    incremented(state) {
      state.value += 1; // Immer under the hood
    },
    amountAdded(state, action: PayloadAction<number>) {
      state.value += action.payload;
    },
  },
});

export const { incremented, amountAdded } = counterSlice.actions;

const store = configureStore({
  reducer: {
    counter: counterSlice.reducer,
  },
});

type RootState = ReturnType<typeof store.getState>;
type AppDispatch = typeof store.dispatch;
```

### RTK Query for Server State

RTK Query is Redux's answer to TanStack Query. It auto-generates hooks from an API definition.

```tsx
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const pokemonApi = createApi({
  reducerPath: 'pokemonApi',
  baseQuery: fetchBaseQuery({ baseUrl: 'https://pokeapi.co/api/v2/' }),
  tagTypes: ['Pokemon'],
  endpoints: (builder) => ({
    getPokemonByName: builder.query<Pokemon, string>({
      query: (name) => `pokemon/${name}`,
      providesTags: (result, error, name) => [{ type: 'Pokemon', id: name }],
    }),
    updatePokemon: builder.mutation<Pokemon, Partial<Pokemon> & Pick<Pokemon, 'id'>>({
      query: ({ id, ...patch }) => ({
        url: `pokemon/${id}`,
        method: 'PATCH',
        body: patch,
      }),
      invalidatesTags: (result, error, { id }) => [{ type: 'Pokemon', id }],
    }),
  }),
});

export const { useGetPokemonByNameQuery, useUpdatePokemonMutation } = pokemonApi;
```

### When Redux Is Still the Right Choice

- **Large team with strict architectural needs:** Redux enforces a single direction of data
  flow with a well-defined pattern. Onboarding 50 engineers? Redux conventions help.
- **Already using RTK Query:** If your server state is in RTK Query, keeping client state
  in Redux slices keeps everything in one devtools panel.
- **Complex cross-cutting middleware:** Logging, analytics, undo/redo -- Redux middleware
  chain is battle-tested.
- **Time-travel debugging is critical:** Redux DevTools time-travel is the most mature.

---

## Server State with TanStack Query

Server state is fundamentally different from client state. It is:

- Persisted remotely
- Asynchronous
- Shared ownership (other users can change it)
- Potentially stale

TanStack Query (formerly React Query) treats server data as a **cache** with lifecycle.

### Stale-While-Revalidate Mental Model

```
1. Component mounts -> cache miss -> fetch -> loading state -> data arrives -> fresh
2. staleTime elapses -> data marked stale
3. Component re-mounts or window focuses -> stale data shown immediately -> background refetch
4. Refetch succeeds -> cache updated -> component re-renders with fresh data
```

This gives the user instant UI while silently keeping data up to date.

### Cache Invalidation

```tsx
const queryClient = useQueryClient();

// Invalidate all queries with key starting with 'todos'
queryClient.invalidateQueries({ queryKey: ['todos'] });

// Invalidate a specific query
queryClient.invalidateQueries({ queryKey: ['todos', todoId] });

// Invalidate and refetch immediately
queryClient.refetchQueries({ queryKey: ['todos'] });
```

### Optimistic Updates

```tsx
const queryClient = useQueryClient();

const mutation = useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo) => {
    // Cancel outgoing refetches so they don't overwrite our optimistic update
    await queryClient.cancelQueries({ queryKey: ['todos', newTodo.id] });

    // Snapshot previous value
    const previousTodo = queryClient.getQueryData(['todos', newTodo.id]);

    // Optimistically update
    queryClient.setQueryData(['todos', newTodo.id], newTodo);

    // Return context with snapshot for rollback
    return { previousTodo };
  },
  onError: (_err, _newTodo, context) => {
    // Rollback on error
    if (context?.previousTodo) {
      queryClient.setQueryData(
        ['todos', context.previousTodo.id],
        context.previousTodo,
      );
    }
  },
  onSettled: (_data, _error, variables) => {
    // Always refetch to ensure server truth
    queryClient.invalidateQueries({ queryKey: ['todos', variables.id] });
  },
});
```

### Infinite Queries

```tsx
const {
  data,
  fetchNextPage,
  hasNextPage,
  isFetchingNextPage,
} = useInfiniteQuery({
  queryKey: ['projects'],
  queryFn: ({ pageParam }) => fetchProjects(pageParam),
  initialPageParam: 0,
  getNextPageParam: (lastPage, allPages) => lastPage.nextCursor ?? undefined,
});

// Flatten pages for rendering
const allProjects = data?.pages.flatMap((page) => page.projects) ?? [];
```

### Prefetching

```tsx
// Prefetch on hover for instant navigation
function ProjectLink({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();

  const prefetch = () => {
    queryClient.prefetchQuery({
      queryKey: ['project', projectId],
      queryFn: () => fetchProject(projectId),
      staleTime: 5 * 60 * 1000, // don't refetch if already fresh
    });
  };

  return (
    <Link to={`/projects/${projectId}`} onMouseEnter={prefetch}>
      View Project
    </Link>
  );
}
```

### Key Configuration Options

```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 min before data is considered stale
      gcTime: 1000 * 60 * 5, // 5 min before inactive cache is garbage collected
      retry: 3,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
});
```

### TanStack Query Setup Template (Complete)

```tsx
// lib/query-client.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,      // 1 min
      gcTime: 1000 * 60 * 5,     // 5 min
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

// app.tsx
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

// hooks/use-users.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => api.getUsers(),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (newUser: CreateUserInput) => api.createUser(newUser),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

// Optimistic update variant
export function useUpdateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (user: UpdateUserInput) => api.updateUser(user),
    onMutate: async (updatedUser) => {
      await queryClient.cancelQueries({ queryKey: ['users', updatedUser.id] });
      const previous = queryClient.getQueryData(['users', updatedUser.id]);
      queryClient.setQueryData(['users', updatedUser.id], updatedUser);
      return { previous };
    },
    onError: (_err, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['users', variables.id], context.previous);
      }
    },
    onSettled: (_data, _err, variables) => {
      queryClient.invalidateQueries({ queryKey: ['users', variables.id] });
    },
  });
}
```

---

## State Library Comparison

| Library | API Style | Bundle Size | Learning Curve | Best For |
|---------|-----------|-------------|----------------|----------|
| useState / useReducer | Built-in hooks | 0 KB | None | Local component state |
| Context API | Built-in provider/consumer | 0 KB | Low | Infrequent global values (theme, auth, locale) |
| Zustand | External store + hook | ~1 KB | Low | General-purpose global client state |
| Jotai | Atomic (bottom-up) | ~3 KB | Low-Medium | Fine-grained, composable, graph-like state |
| Redux Toolkit | Flux (top-down, single store) | ~11 KB | Medium | Large teams, strict conventions, RTK Query |
| TanStack Query | Cache manager + hooks | ~12 KB | Medium | Server/remote state (any data from an API) |
| XState | State machines / statecharts | ~15 KB | High | Complex workflows, impossible-state prevention |
| React Hook Form | Uncontrolled + subscription | ~9 KB | Low-Medium | Form state, validation, performance |

---

## Decision Tree

```
START: What kind of state is this?
|
+-- Server data (fetched from API)?
|   -> TanStack Query (or SWR / RTK Query)
|
+-- URL-serializable (filters, pagination, tabs)?
|   -> useSearchParams / nuqs
|
+-- Form input (validation, submission)?
|   -> React Hook Form + Zod
|
+-- Local to one component?
|   +-- Simple (toggle, counter)?  -> useState
|   +-- Coupled transitions?       -> useReducer
|
+-- Shared across components?
    +-- Changes infrequently (theme, auth)?  -> Context (split + memoize)
    +-- Changes frequently?
        +-- Many independent atoms?  -> Jotai
        +-- Single store preferred?  -> Zustand
        +-- Large team, strict patterns needed?  -> Redux Toolkit
```

---

## Common Gotchas

| Gotcha | What Happens | Fix |
|--------|-------------|-----|
| Context mega-object | All consumers re-render on any field change | Split into focused contexts |
| New context value every render | `{ a, b }` is a new reference each render, so all consumers re-render | Wrap in `useMemo` |
| Zustand selector returns new object | `(s) => ({ a: s.a, b: s.b })` creates a new object, defeats selector optimization | Use `useShallow` from `zustand/react/shallow` |
| TanStack Query as global state | Putting client-only state in query cache | Use queries for server data only; use Zustand/Jotai for client state |
| staleTime: 0 (default) | Every mount triggers a refetch, even if data was just fetched | Set an appropriate `staleTime` (e.g., 60s) |
| Mutating state directly | `state.items.push(x)` without Immer silently corrupts state | Use Immer middleware or always return new objects |
| Form re-renders on keystroke | Controlled inputs (`value={state}`) re-render parent on every change | Use React Hook Form (uncontrolled) or isolate with `useWatch` |
| Forgetting to cancel queries before optimistic update | Background refetch overwrites optimistic data | Always call `queryClient.cancelQueries()` in `onMutate` |
| Putting server data in Zustand | Manual loading/error/stale management, no caching | Use TanStack Query -- it handles the cache lifecycle |
| Redux for a small app | Boilerplate overhead with no benefit | Zustand or Jotai for small-to-medium apps |

---

## Practice

- **Zustand basics**: Create a Zustand store for a shopping cart with `items`, `addItem`, `removeItem`, and `total` (derived). Use selectors to prevent the item count badge from re-rendering when items change but count does not.
- **TanStack Query**: Fetch a paginated list from a public API (e.g., JSONPlaceholder). Configure `staleTime`, implement optimistic updates for a mutation, and verify background refetch on window focus.
- **Jotai atoms**: Build a todo app using Jotai. Create atoms for the todo list and derived atoms for `completedCount` and `pendingCount`. Verify that components subscribing to `completedCount` do not re-render when a pending todo's text changes.
- **Decision tree walkthrough**: Use the decision tree from this lesson on a real project. For each piece of state, trace through the tree and document which tool you would choose and why.
- **Library comparison**: Implement the same counter with persistence in (1) Context + `useReducer`, (2) Zustand, and (3) Jotai. Compare the amount of code, re-render behavior, and testing ergonomics.

### Related Lessons

- [State Management Fundamentals](01-state-management-fundamentals.md) -- `useState`, `useReducer`, Context, state colocation, URL state, form state
- [Advanced State Patterns](03-advanced-state-patterns.md) -- XState, optimistic updates, CRDTs, Zustand internals
- [Hooks & State Management](../01-hooks-deep-dive/01-hooks-and-state-management.md) -- the hook primitives that state libraries wrap
- [Performance: Rendering & Optimization](../03-performance/01-react-rendering-and-optimization.md) -- re-render cost of Context vs selector-based stores
