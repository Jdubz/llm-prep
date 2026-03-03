# Lesson 00: React Fundamentals Refresh

This course assumes production React experience and skips the basics. This refresher ensures the foundational concepts are sharp so the advanced modules can build on solid ground. If anything here feels unfamiliar rather than "yes, obviously," revisit it before moving to Lesson 01.

---

## 1. The Component Model

### Function Components

```tsx
// A component is a function that returns JSX
function UserCard({ name, email }: { name: string; email: string }) {
  return (
    <div className="card">
      <h2>{name}</h2>
      <p>{email}</p>
    </div>
  );
}

// Arrow function variant (same thing, style preference)
const UserCard = ({ name, email }: Props) => (
  <div className="card">
    <h2>{name}</h2>
    <p>{email}</p>
  </div>
);
```

Class components still exist but you should never write new ones. They're relevant only for understanding error boundaries (until React adds a hook-based API) and reading legacy codebases.

### JSX Is Function Calls

```tsx
// This JSX:
<div className="card">
  <h2>{name}</h2>
</div>

// Compiles to:
React.createElement("div", { className: "card" },
  React.createElement("h2", null, name)
);

// Understanding this matters for:
// - Conditional rendering
// - Why you can't use if/else directly in JSX (it's an expression context)
// - Why components must return a single root (or use fragments)
```

### Fragments

```tsx
// Avoid unnecessary wrapper divs
function UserInfo() {
  return (
    <>
      <h2>Alice</h2>
      <p>alice@example.com</p>
    </>
  );
}

// Long form (needed when you want to add a key)
<React.Fragment key={id}>
  <dt>{label}</dt>
  <dd>{value}</dd>
</React.Fragment>
```

---

## 2. Props & Children

### Props Are Read-Only

```tsx
interface ButtonProps {
  variant: "primary" | "secondary";
  size?: "sm" | "md" | "lg";     // optional with ?
  disabled?: boolean;
  onClick: () => void;
  children: React.ReactNode;      // anything renderable
}

function Button({ variant, size = "md", disabled = false, onClick, children }: ButtonProps) {
  return (
    <button
      className={`btn-${variant} btn-${size}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

// Usage
<Button variant="primary" onClick={handleSubmit}>
  Submit
</Button>
```

### Spreading Props

```tsx
// Forward remaining props to underlying element
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

function Input({ label, ...rest }: InputProps) {
  return (
    <label>
      {label}
      <input {...rest} />
    </label>
  );
}

// All native input props (type, placeholder, onChange, etc.) pass through
<Input label="Email" type="email" placeholder="you@example.com" />
```

### Common Children Patterns

```tsx
// ReactNode — the most permissive type (string, number, element, null, array, fragment)
children: React.ReactNode;

// ReactElement — must be a JSX element (no strings, no null)
children: React.ReactElement;

// Render prop — function as children
children: (data: T) => React.ReactNode;

// Specific element type
children: React.ReactElement<TabProps>;
```

---

## 3. State with useState

```tsx
// Basic state
const [count, setCount] = useState(0);

// State with complex objects
const [user, setUser] = useState<User | null>(null);

// Updating state — always create new references for objects/arrays
setUser({ ...user, name: "Bob" });                    // spread and override
setItems(prev => [...prev, newItem]);                  // append
setItems(prev => prev.filter(item => item.id !== id)); // remove
setItems(prev => prev.map(item =>                      // update one
  item.id === id ? { ...item, name: "new" } : item
));
```

### Key Rules

1. **State updates are asynchronous** — `count` doesn't change immediately after `setCount`
2. **State updates trigger re-renders** — component function runs again with new values
3. **Object/array identity matters** — `setUser(user)` with the same reference does nothing. You must create a new object.
4. **Batching** — React 18+ batches all state updates in a single event handler into one re-render

---

## 4. Effects with useEffect

```tsx
useEffect(() => {
  // Effect code — runs AFTER render, not during

  return () => {
    // Cleanup — runs before next effect or on unmount
  };
}, [dependencies]); // Only re-run when dependencies change
```

### Dependency Array Rules

```tsx
// No array — runs after EVERY render (rarely what you want)
useEffect(() => { ... });

// Empty array — runs once after mount (like componentDidMount)
useEffect(() => {
  fetchInitialData();
}, []);

// With dependencies — runs when any dependency changes
useEffect(() => {
  fetchUser(userId);
}, [userId]);
```

### What Belongs in useEffect

- **Data fetching** (though TanStack Query is better)
- **Subscriptions** (WebSocket, event listeners)
- **DOM manipulation** that can't be done declaratively
- **Synchronizing with external systems** (analytics, third-party libraries)

### What Does NOT Belong in useEffect

- **Deriving state from props** — compute during render instead
- **Resetting state on prop change** — use a `key` instead
- **Event handlers** — put them on the element directly

```tsx
// BAD — deriving state in an effect
const [fullName, setFullName] = useState("");
useEffect(() => {
  setFullName(`${firstName} ${lastName}`);
}, [firstName, lastName]);

// GOOD — derive during render
const fullName = `${firstName} ${lastName}`;
```

---

## 5. Refs with useRef

```tsx
// DOM reference
const inputRef = useRef<HTMLInputElement>(null);

function handleClick() {
  inputRef.current?.focus();  // access the DOM element directly
}

return <input ref={inputRef} />;

// Mutable value that persists across renders without triggering re-renders
const renderCount = useRef(0);
renderCount.current++;  // does NOT cause a re-render

// Previous value pattern
const prevValue = useRef(value);
useEffect(() => {
  prevValue.current = value;  // update after render
});
```

Key distinction: `useState` triggers re-renders, `useRef` does not. Use `useRef` for values you need to persist but don't want to display.

---

## 6. Event Handling

```tsx
function Form() {
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    // form logic
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
  };

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    // button logic
  };

  return (
    <form onSubmit={handleSubmit}>
      <input onChange={handleChange} />
      <button onClick={handleClick}>Submit</button>
    </form>
  );
}
```

React uses **synthetic events** — cross-browser wrappers around native events. They're pooled and reused in React 16 (but not in 17+).

---

## 7. Conditional Rendering & Lists

```tsx
// Conditional rendering
function Status({ isOnline }: { isOnline: boolean }) {
  return (
    <div>
      {isOnline ? <Online /> : <Offline />}        {/* ternary for either/or */}
      {isOnline && <GreenDot />}                    {/* && for show/hide */}
      {count > 0 && <Badge count={count} />}        {/* CAREFUL: 0 && ... renders "0" */}
      {count > 0 ? <Badge count={count} /> : null}  {/* safer for numbers */}
    </div>
  );
}

// Lists — always use key
function UserList({ users }: { users: User[] }) {
  return (
    <ul>
      {users.map(user => (
        <li key={user.id}>{user.name}</li>           {/* key MUST be stable, unique */}
      ))}
    </ul>
  );
}
```

### Key Rules

- **Never use array index as key** if the list can reorder, insert, or delete. It causes bugs with component state.
- Keys must be **stable** (same item → same key across re-renders) and **unique** among siblings.
- Keys are not passed as props — they're consumed by React internally.

---

## 8. Context

```tsx
// 1. Create context with a typed default
const ThemeContext = createContext<Theme>({
  mode: "light",
  toggle: () => {},
});

// 2. Provide it
function App() {
  const [mode, setMode] = useState<"light" | "dark">("light");
  const theme = useMemo(() => ({
    mode,
    toggle: () => setMode(m => m === "light" ? "dark" : "light"),
  }), [mode]);

  return (
    <ThemeContext.Provider value={theme}>
      <Layout />
    </ThemeContext.Provider>
  );
}

// 3. Consume it
function Header() {
  const { mode, toggle } = useContext(ThemeContext);
  return <button onClick={toggle}>{mode}</button>;
}
```

### When to Use Context

- **Theme, locale, auth** — values that many components need at different levels
- **Avoiding prop drilling** — when props pass through 3+ levels of components that don't use them

### When NOT to Use Context

- **Frequently changing values** — every context update re-renders all consumers. Use state management libraries (Zustand, Jotai) for high-frequency updates.
- **Server state** — use TanStack Query instead of context for API data

---

## 9. Component Lifecycle (Mental Model)

Function components don't have lifecycle methods, but the concept still maps:

```
Mount:
  1. Component function runs (render)
  2. React updates the DOM
  3. useLayoutEffect runs (synchronous, before paint)
  4. Browser paints
  5. useEffect runs (asynchronous, after paint)

Update (state or props change):
  1. Component function runs again (re-render)
  2. React diffs the virtual DOM
  3. React updates only changed DOM nodes
  4. useLayoutEffect cleanup runs, then new useLayoutEffect
  5. Browser paints
  6. useEffect cleanup runs, then new useEffect

Unmount:
  1. useLayoutEffect cleanup runs
  2. useEffect cleanup runs
  3. Component removed from DOM
```

---

## 10. Common TypeScript Patterns for React

```tsx
// Component props with children
type Props = React.PropsWithChildren<{
  title: string;
}>;

// Event handler types
type ClickHandler = React.MouseEventHandler<HTMLButtonElement>;
type ChangeHandler = React.ChangeEventHandler<HTMLInputElement>;
type SubmitHandler = React.FormEventHandler<HTMLFormElement>;

// Ref types
type InputRef = React.RefObject<HTMLInputElement>;

// Style types
type Style = React.CSSProperties;

// Generic component
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}

function List<T>({ items, renderItem }: ListProps<T>) {
  return <ul>{items.map(renderItem)}</ul>;
}

// Discriminated union for component variants
type AlertProps =
  | { variant: "success"; message: string }
  | { variant: "error"; message: string; retry: () => void };
```

---

## 11. Quick Checklist

Before starting Lesson 01, you should be able to answer these:

- [ ] What is JSX compiled to?
- [ ] Why must you create new object/array references when updating state?
- [ ] What's the difference between `useEffect` with `[]`, `[dep]`, and no array?
- [ ] When should you NOT use `useEffect`?
- [ ] What's the `0 && <Component />` rendering bug?
- [ ] Why is array index a bad key? When is it acceptable?
- [ ] What triggers a re-render? (state change, parent re-render, context change)
- [ ] What's the difference between `useRef` and `useState`?
- [ ] When does useEffect cleanup run?
- [ ] What's the render order: useEffect vs useLayoutEffect vs paint?

If any of these gave you pause, review that section before moving on.

---

## Next Steps

You're ready for [Lesson 01: Hooks Deep Dive](src/lessons/01-hooks-deep-dive/README.md) — `useState` pitfalls, `useEffect` mastery, rules of hooks internals, and the closure traps that catch even experienced engineers.
