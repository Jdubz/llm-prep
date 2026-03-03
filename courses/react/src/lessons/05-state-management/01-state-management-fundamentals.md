# State Management: Fundamentals

## Table of Contents

1. [State Categories](#state-categories)
2. [useState vs useReducer](#usestate-vs-usereducer)
3. [Context API](#context-api)
4. [State Colocation](#state-colocation)
5. [URL State](#url-state)
6. [Form State](#form-state)

---

## State Categories

Not all state is created equal. Choosing the wrong tool for a state category is the single most
common architectural mistake in React applications. Before reaching for any library, classify
the state you are dealing with.

### Local / Component State

State that belongs to a single component and has no consumers elsewhere in the tree.

**When it applies:** Toggle visibility, input focus, animation flags, ephemeral UI bits.

```tsx
const [isOpen, setIsOpen] = useState(false);
```

Rule of thumb: if you can delete the component and no other component cares, it is local state.

### Global / Shared State

State consumed by multiple unrelated components across different subtrees.

**When it applies:** Authenticated user, feature flags, theme, shopping cart, notification queue.

```tsx
// Zustand store -- consumed anywhere in the tree
const useCartStore = create<CartState>((set) => ({
  items: [],
  addItem: (item) => set((s) => ({ items: [...s.items, item] })),
}));
```

### Server / Remote State

Data that lives on a backend and is fetched, cached, and synchronized with the server.

**When it applies:** Any data you GET from an API. This is *not* global state -- it is a cache
of a remote data source with its own lifecycle (stale, refetching, error, loading).

```tsx
const { data, isLoading } = useQuery({
  queryKey: ['users', userId],
  queryFn: () => api.getUser(userId),
});
```

A defining characteristic: the source of truth is the server, not the client.

### URL State

State serialized into the URL so that it survives page refreshes and can be shared via link.

**When it applies:** Search filters, pagination, sort order, selected tab, modal open state when
it needs to be linkable.

```tsx
const [searchParams, setSearchParams] = useSearchParams();
const page = Number(searchParams.get('page') ?? '1');
```

### Form State

Transient state tied to user input that ultimately produces a submission payload.

**When it applies:** Any form -- login, checkout, multi-step wizard, inline editing.

```tsx
const { register, handleSubmit } = useForm<CheckoutForm>();
```

Form state has unique concerns: validation, dirty tracking, touched fields, submit count,
and performance (avoiding re-renders on every keystroke).

### Decision Matrix

| Category | Source of truth | Lifecycle | Typical tool |
|----------|----------------|-----------|-------------|
| Local | Component | Mount/unmount | `useState`, `useReducer` |
| Global | Client | App session | Zustand, Jotai, Redux |
| Server | Backend DB | Cache TTL | TanStack Query, SWR |
| URL | Address bar | Navigation | `useSearchParams`, nuqs |
| Form | User input | Form mount to submit | React Hook Form |

---

## useState vs useReducer

Both are built-in. The choice between them is not about complexity -- it is about the *shape*
of state transitions.

### useState: When Transitions Are Independent

```tsx
const [count, setCount] = useState(0);
const [name, setName] = useState('');
```

Fine when each piece of state changes independently. Multiple `useState` calls are preferable
to a single object when the fields are unrelated.

### useReducer: When Transitions Are Coupled

When a single user action must update multiple fields consistently, a reducer centralizes
the transition logic.

```tsx
type State = {
  status: 'idle' | 'loading' | 'success' | 'error';
  data: User[] | null;
  error: string | null;
};

type Action =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; payload: User[] }
  | { type: 'FETCH_ERROR'; error: string };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'FETCH_START':
      return { status: 'loading', data: null, error: null };
    case 'FETCH_SUCCESS':
      return { status: 'success', data: action.payload, error: null };
    case 'FETCH_ERROR':
      return { status: 'error', data: null, error: action.error };
  }
}

function UserList() {
  const [state, dispatch] = useReducer(reducer, {
    status: 'idle',
    data: null,
    error: null,
  });

  // dispatch is referentially stable -- safe to pass as prop or dependency
  useEffect(() => {
    dispatch({ type: 'FETCH_START' });
    fetchUsers()
      .then((users) => dispatch({ type: 'FETCH_SUCCESS', payload: users }))
      .catch((e) => dispatch({ type: 'FETCH_ERROR', error: e.message }));
  }, [dispatch]); // dispatch identity never changes

  // ...
}
```

### Dispatch Stability

`dispatch` from `useReducer` is referentially stable across renders. This matters when you
pass it to memoized children or include it in effect dependency arrays. With `useState`, the
setter is also stable, but composite update functions you build on top of multiple setters
are not -- you end up wrapping them in `useCallback` chains.

### Decision Criteria

| Criterion | useState | useReducer |
|-----------|----------|------------|
| Independent primitives | Preferred | Overkill |
| Coupled transitions (one event, many fields) | Fragile | Preferred |
| Next state depends on previous state | Works (functional update) | Natural |
| Complex validation / guard logic | Messy | Clean |
| Testability of transitions | Harder | Pure function, easy |
| Stable callback to pass down | Need useCallback | dispatch is stable |

---

## Context API

### Proper Use Cases

Context is a **dependency injection** mechanism, not a state management library. It excels at
broadcasting *infrequently changing* values to a deep subtree:

- **Theme** (light/dark)
- **Authenticated user** (changes on login/logout)
- **Locale / i18n** (changes rarely)
- **Feature flags** (loaded once, read everywhere)

### The Performance Trap

Every component that calls `useContext(SomeContext)` re-renders when the context value changes.
There is no selector mechanism. This means:

```tsx
// ANTI-PATTERN: single mega-context
const AppContext = createContext<{
  user: User;
  theme: Theme;
  cart: CartItem[];
  notifications: Notification[];
}>({ /* ... */ });

function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  // Every consumer re-renders when ANY field changes
  return (
    <AppContext.Provider value={state}>
      {children}
    </AppContext.Provider>
  );
}
```

When `notifications` updates, every component reading `theme` also re-renders. This is the
number one reason Context gets a bad reputation for performance.

### Splitting Contexts

Separate concerns into distinct contexts so that consumers only subscribe to what they need.

```tsx
const ThemeContext = createContext<Theme>('light');
const UserContext = createContext<User | null>(null);
const CartContext = createContext<CartState>(initialCartState);

function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <UserProvider>
        <CartProvider>
          {children}
        </CartProvider>
      </UserProvider>
    </ThemeProvider>
  );
}
```

Now a `notifications` update does not touch `ThemeContext` consumers.

### Memoizing Context Value

Even with split contexts, a common mistake is creating a new object reference on every render
of the provider.

```tsx
// BUG: value is a new object every render
function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);

  return (
    <CartContext.Provider value={{ items, addItem, removeItem }}>
      {children}
    </CartContext.Provider>
  );
}
```

Fix: memoize the value object.

```tsx
function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);

  const addItem = useCallback((item: CartItem) => {
    setItems((prev) => [...prev, item]);
  }, []);

  const removeItem = useCallback((id: string) => {
    setItems((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const value = useMemo(
    () => ({ items, addItem, removeItem }),
    [items, addItem, removeItem],
  );

  return (
    <CartContext.Provider value={value}>
      {children}
    </CartContext.Provider>
  );
}
```

### Separate State and Dispatch Contexts

An advanced pattern: provide state and dispatch in two contexts. Components that only fire
actions never re-render when state changes.

```tsx
const CartStateContext = createContext<CartItem[]>([]);
const CartDispatchContext = createContext<Dispatch<CartAction>>(() => {});

function CartProvider({ children }: { children: ReactNode }) {
  const [items, dispatch] = useReducer(cartReducer, []);

  return (
    <CartStateContext.Provider value={items}>
      <CartDispatchContext.Provider value={dispatch}>
        {children}
      </CartDispatchContext.Provider>
    </CartStateContext.Provider>
  );
}

// Component that displays items -- subscribes to state
function CartBadge() {
  const items = useContext(CartStateContext);
  return <span>{items.length}</span>;
}

// Component that adds items -- subscribes to dispatch only (never re-renders on cart change)
function AddToCartButton({ item }: { item: CartItem }) {
  const dispatch = useContext(CartDispatchContext);
  return <button onClick={() => dispatch({ type: 'ADD', item })}>Add</button>;
}
```

### Context Performance Pattern: Split + Memoize (Quick Reference)

```tsx
// 1. Separate state and dispatch contexts
const StateCtx = createContext<AppState>(initialState);
const DispatchCtx = createContext<Dispatch<AppAction>>(() => {});

// 2. Memoize the state value
function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);

  const memoizedState = useMemo(() => state, [state]);
  // dispatch is already referentially stable from useReducer

  return (
    <DispatchCtx.Provider value={dispatch}>
      <StateCtx.Provider value={memoizedState}>
        {children}
      </StateCtx.Provider>
    </DispatchCtx.Provider>
  );
}

// 3. Custom hooks for clean consumption
function useAppState() {
  return useContext(StateCtx);
}

function useAppDispatch() {
  return useContext(DispatchCtx);
}

// Components that only dispatch never re-render on state changes
function ActionButton() {
  const dispatch = useAppDispatch();
  return <button onClick={() => dispatch({ type: 'INCREMENT' })}>+1</button>;
}
```

---

## State Colocation

State colocation is a principle, not a library. The idea: keep state as close to where it is
used as possible.

### The Anti-Pattern: Everything at the Top

```tsx
// DO NOT DO THIS
function App() {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  // 30 more pieces of state...

  return (
    <Dashboard
      modalOpen={modalOpen}
      setModalOpen={setModalOpen}
      selectedRow={selectedRow}
      setSelectedRow={setSelectedRow}
      tooltipVisible={tooltipVisible}
      // ...
    />
  );
}
```

### Colocation in Practice

```tsx
// State lives where it is used
function Dashboard() {
  return (
    <>
      <SearchBar /> {/* owns searchQuery */}
      <DataTable /> {/* owns selectedRow, tooltipVisible */}
      <Modal />     {/* owns modalOpen */}
    </>
  );
}

function DataTable() {
  const [selectedRow, setSelectedRow] = useState<string | null>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);

  return (
    <table>
      {rows.map((row) => (
        <Row
          key={row.id}
          row={row}
          isSelected={row.id === selectedRow}
          onSelect={() => setSelectedRow(row.id)}
        />
      ))}
    </table>
  );
}
```

### Lifting State Up vs Composition

When two siblings need the same state, lift it to their common parent -- but *only* that
state. Do not lift unrelated state along with it.

```tsx
// Two siblings need `selectedId`
function Page() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <>
      <Sidebar selectedId={selectedId} onSelect={setSelectedId} />
      <Detail selectedId={selectedId} />
    </>
  );
}
```

If you find yourself lifting state multiple levels, consider:

1. **Composition** -- pass children as props to avoid prop drilling.
2. **Context** -- but only if the state is needed by many deeply nested components.
3. **External store** (Zustand/Jotai) -- if it crosses route boundaries or persists across navigations.

### The Colocation Ladder

```
1. useState inside component           (closest)
2. Lift to parent component
3. Composition (children / render props)
4. Context (subtree injection)
5. External store (Zustand / Jotai)
6. URL state (survives navigation)
7. Server state (TanStack Query)       (furthest -- source of truth is the server)
```

Move state down this ladder only as requirements demand.

---

## URL State

### useSearchParams (React Router)

```tsx
import { useSearchParams } from 'react-router-dom';

function ProductList() {
  const [searchParams, setSearchParams] = useSearchParams();

  const category = searchParams.get('category') ?? 'all';
  const sort = searchParams.get('sort') ?? 'newest';
  const page = Number(searchParams.get('page') ?? '1');

  const setPage = (p: number) => {
    setSearchParams((prev) => {
      prev.set('page', String(p));
      return prev;
    });
  };

  const setFilters = (filters: { category?: string; sort?: string }) => {
    setSearchParams((prev) => {
      if (filters.category) prev.set('category', filters.category);
      if (filters.sort) prev.set('sort', filters.sort);
      prev.set('page', '1'); // reset page on filter change
      return prev;
    });
  };

  // ...
}
```

### Encoding Complex State

For complex objects, use a serialization strategy.

```tsx
import { z } from 'zod';

const FiltersSchema = z.object({
  categories: z.array(z.string()).default([]),
  priceRange: z.tuple([z.number(), z.number()]).default([0, 1000]),
  inStock: z.boolean().default(false),
});

type Filters = z.infer<typeof FiltersSchema>;

function useFiltersFromURL(): Filters {
  const [searchParams] = useSearchParams();
  const raw = searchParams.get('filters');

  if (!raw) return FiltersSchema.parse({});

  try {
    const decoded = JSON.parse(atob(raw));
    return FiltersSchema.parse(decoded);
  } catch {
    return FiltersSchema.parse({});
  }
}

function setFiltersToURL(filters: Filters, setSearchParams: SetURLSearchParams) {
  setSearchParams((prev) => {
    prev.set('filters', btoa(JSON.stringify(filters)));
    return prev;
  });
}
```

### Syncing URL with App State (nuqs)

The nuqs library provides type-safe URL state hooks that feel like `useState`:

```tsx
import { useQueryState, parseAsInteger, parseAsString } from 'nuqs';

function ProductList() {
  const [page, setPage] = useQueryState('page', parseAsInteger.withDefault(1));
  const [sort, setSort] = useQueryState('sort', parseAsString.withDefault('newest'));

  // setPage(2) updates the URL to ?page=2&sort=newest
  // Typing is fully inferred: page is number, sort is string
}
```

---

## Form State

### React Hook Form

React Hook Form uses uncontrolled inputs by default, which means the DOM owns the input
values. This avoids re-rendering the entire form on every keystroke.

```tsx
import { useForm } from 'react-hook-form';

interface LoginForm {
  email: string;
  password: string;
}

function Login() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>();

  const onSubmit = async (data: LoginForm) => {
    await api.login(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email', {
          required: 'Email is required',
          pattern: {
            value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: 'Invalid email address',
          },
        })}
      />
      {errors.email && <span>{errors.email.message}</span>}

      <input
        type="password"
        {...register('password', {
          required: 'Password is required',
          minLength: { value: 8, message: 'Minimum 8 characters' },
        })}
      />
      {errors.password && <span>{errors.password.message}</span>}

      <button type="submit" disabled={isSubmitting}>
        Log In
      </button>
    </form>
  );
}
```

### Controlled Fields with `control`

For complex inputs (date pickers, rich text, custom selects) that cannot use `register`,
use `Controller`:

```tsx
import { useForm, Controller } from 'react-hook-form';
import { DatePicker } from '@/components/DatePicker';

function EventForm() {
  const { control, handleSubmit } = useForm<EventFormData>();

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Controller
        name="startDate"
        control={control}
        rules={{ required: 'Start date is required' }}
        render={({ field, fieldState }) => (
          <DatePicker
            value={field.value}
            onChange={field.onChange}
            error={fieldState.error?.message}
          />
        )}
      />
    </form>
  );
}
```

### Zod Integration

Zod schemas are the single source of truth for validation. The `@hookform/resolvers` package
bridges Zod and React Hook Form.

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const SignupSchema = z
  .object({
    email: z.string().email('Invalid email'),
    password: z.string().min(8, 'Minimum 8 characters'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type SignupForm = z.infer<typeof SignupSchema>;

function Signup() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupForm>({
    resolver: zodResolver(SignupSchema),
  });

  return (
    <form onSubmit={handleSubmit((data) => console.log(data))}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}

      <input type="password" {...register('password')} />
      {errors.password && <span>{errors.password.message}</span>}

      <input type="password" {...register('confirmPassword')} />
      {errors.confirmPassword && <span>{errors.confirmPassword.message}</span>}

      <button type="submit">Sign Up</button>
    </form>
  );
}
```

### React Hook Form + Zod Template (Complete)

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// 1. Schema = single source of truth
const FormSchema = z.object({
  name: z.string().min(1, 'Required').max(100),
  email: z.string().email('Invalid email'),
  role: z.enum(['admin', 'user', 'viewer']),
  age: z.coerce.number().int().min(18, 'Must be 18+').optional(),
});

type FormData = z.infer<typeof FormSchema>;

// 2. Hook setup
function MyForm() {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<FormData>({
    resolver: zodResolver(FormSchema),
    defaultValues: { name: '', email: '', role: 'user' },
  });

  const onSubmit = async (data: FormData) => {
    await api.submitForm(data);
    reset(); // reset form after successful submission
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name')} />
      {errors.name && <p>{errors.name.message}</p>}

      <input {...register('email')} />
      {errors.email && <p>{errors.email.message}</p>}

      <select {...register('role')}>
        <option value="admin">Admin</option>
        <option value="user">User</option>
        <option value="viewer">Viewer</option>
      </select>
      {errors.role && <p>{errors.role.message}</p>}

      <input type="number" {...register('age')} />
      {errors.age && <p>{errors.age.message}</p>}

      <button type="submit" disabled={isSubmitting || !isDirty}>
        {isSubmitting ? 'Saving...' : 'Save'}
      </button>
    </form>
  );
}
```

### Performance Advantages

| Approach | Re-renders on keystroke | Re-renders on submit |
|----------|----------------------|---------------------|
| Controlled (useState per field) | Every field re-renders parent | 1 |
| React Hook Form (uncontrolled) | 0 (DOM handles input) | 1 |
| React Hook Form (watched field) | Only watched component | 1 |

React Hook Form isolates re-renders using a subscription model internally. Only components
that `watch` a specific field re-render when that field changes.

```tsx
// Only this component re-renders when 'email' changes
function EmailPreview() {
  const email = useWatch({ name: 'email' });
  return <p>Preview: {email}</p>;
}
```
