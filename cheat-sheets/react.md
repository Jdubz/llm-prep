---
title: "React & TypeScript Quick Reference"
---

# Component Patterns

```tsx
// Function component with typed props
type Props = { name: string; count?: number }
function Card({ name, count = 0 }: Props) {
  return <div>{name}: {count}</div>
}

// Children prop
type LayoutProps = { children: React.ReactNode }

// Forwarding refs
const Input = forwardRef<HTMLInputElement, Props>(
  (props, ref) => <input ref={ref} {...props} />
)
```

# Hooks

```tsx
// State
const [val, setVal] = useState<T>(initial)
setVal(prev => prev + 1)     // functional update

// Side effects
useEffect(() => {
  const sub = subscribe()
  return () => sub.unsubscribe() // cleanup
}, [dep1, dep2])              // re-run on deps change

// Refs (mutable, no re-render)
const ref = useRef<HTMLDivElement>(null)
const timer = useRef<number>(0)

// Memoization
const expensive = useMemo(() => compute(a), [a])
const handler = useCallback((e: E) => { ... }, [dep])

// Context
const ThemeCtx = createContext<Theme>(defaultTheme)
const theme = useContext(ThemeCtx)

// Reducer (complex state)
const [state, dispatch] = useReducer(reducer, init)
```

# Event Handling

```tsx
// Common event types
onChange: React.ChangeEvent<HTMLInputElement>
onSubmit: React.FormEvent<HTMLFormElement>
onClick:  React.MouseEvent<HTMLButtonElement>

// Form submission
function handleSubmit(e: React.FormEvent) {
  e.preventDefault()
  const data = new FormData(e.currentTarget)
}
```

# State Patterns

- **Lift state up**: share state via nearest common ancestor
- **Derived state**: compute from existing state, don't duplicate
- **useReducer**: complex state with multiple sub-values or actions
- **Context + useReducer**: lightweight global state (no lib needed)
- **External stores**: Zustand, Jotai for cross-cutting state

# Rendering

```tsx
// Conditional rendering
{isAuth ? <Dashboard /> : <Login />}
{error && <Alert msg={error} />}

// Lists -- always use stable keys
{items.map(item => (
  <Item key={item.id} {...item} />
))}

// Fragments (no extra DOM node)
<>{a}{b}</>
```

# Common Patterns

```tsx
// Controlled input
<input value={val} onChange={e => setVal(e.target.value)} />

// Custom hook
function useDebounce<T>(value: T, ms: number): T {
  const [debounced, set] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => set(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

// Context provider
function ThemeProvider({ children }: LayoutProps) {
  const [theme, setTheme] = useState<Theme>("light")
  return (
    <ThemeCtx.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeCtx.Provider>
  )
}
```

# Performance

- **React.memo**: skip re-render if props unchanged
- **useMemo / useCallback**: stabilize references
- **Key prop**: use stable IDs, never array index for dynamic lists
- **Lazy loading**: `React.lazy(() => import("./Heavy"))`
- **Suspense**: wrap lazy components for loading fallback
- **Virtualization**: `react-window` for long lists
- **Profiler**: React DevTools flamechart to find bottlenecks
