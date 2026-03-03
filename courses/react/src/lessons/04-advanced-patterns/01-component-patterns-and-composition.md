# 01 — Component Patterns and Composition

> Render props, compound components, controlled vs uncontrolled, forwardRef, portal pattern, error boundaries, and discriminated union props.

---

## Table of Contents

1. [Overview and Pattern Decision Matrix](#overview-and-pattern-decision-matrix)
2. [Compound Components](#compound-components)
3. [Render Props](#render-props)
4. [Higher-Order Components (HOCs)](#higher-order-components-hocs)
5. [Headless Components / Hooks](#headless-components--hooks)
6. [Controlled vs. Uncontrolled Components](#controlled-vs-uncontrolled-components)
7. [Polymorphic Components](#polymorphic-components)
8. [Slot Pattern](#slot-pattern)
9. [Provider Pattern](#provider-pattern)
10. [Error Boundaries](#error-boundaries)
11. [Discriminated Union Props](#discriminated-union-props)
12. [Key Takeaways for Interviews](#key-takeaways-for-interviews)

---

## Overview and Pattern Decision Matrix

These patterns separate senior React engineers from those who just use React. They appear frequently in interviews at companies building design systems, component libraries, and complex UIs. You are expected to not just know these patterns but to articulate **when and why** to reach for each one.

| Pattern | Use Case | Complexity | TS Support | Status |
|---|---|---|---|---|
| Compound Components | Related component groups (Select, Tabs, Accordion) | Medium | Excellent | Active |
| Render Props | Inject UI into a component's render cycle | Low | Good | Niche |
| HOCs | Cross-cutting concerns (auth, logging) | High | Poor | Legacy |
| Headless Hooks | Reusable logic with zero UI opinions | Medium | Excellent | Preferred |
| Controlled/Uncontrolled | Stateful inputs, toggles, any interactive widget | Low | Good | Fundamental |
| Polymorphic `as` Prop | Design system primitives (Button, Text, Box) | High | Excellent | Active |
| Slot Pattern | Components with named render regions | Low | Good | Active |
| Provider Pattern | Dependency injection, theming, auth context | Low | Good | Active |
| Error Boundaries | Fault isolation, fallback UI | Low | Good | Required |
| Discriminated Unions | Type-safe component variants | Medium | Excellent | Preferred |

---

## Compound Components

Compound components model implicit parent-child relationships where a parent component shares state with its children through Context, without requiring the consumer to wire props manually.

**Why interviewers ask:** It tests whether you understand React Context, component composition, and API design. It is the foundation of every serious component library (Radix, Reach UI, Headless UI, MUI).

### Implementation

```tsx
import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
  type Dispatch,
  type SetStateAction,
} from "react";

// --- Internal shared state ---
interface SelectContextValue {
  value: string | null;
  onChange: (value: string) => void;
  open: boolean;
  setOpen: Dispatch<SetStateAction<boolean>>;
}

const SelectContext = createContext<SelectContextValue | null>(null);

function useSelectContext() {
  const ctx = useContext(SelectContext);
  if (!ctx) {
    throw new Error(
      "Select compound components must be rendered within <Select>"
    );
  }
  return ctx;
}

// --- Public API ---
interface SelectProps {
  value?: string | null;
  defaultValue?: string | null;
  onChange?: (value: string) => void;
  children: ReactNode;
}

function Select({ value, defaultValue = null, onChange, children }: SelectProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const [open, setOpen] = useState(false);

  // Support both controlled and uncontrolled usage
  const resolvedValue = value !== undefined ? value : internalValue;

  const handleChange = useCallback(
    (next: string) => {
      if (value === undefined) setInternalValue(next);
      onChange?.(next);
      setOpen(false);
    },
    [value, onChange]
  );

  return (
    <SelectContext.Provider
      value={{ value: resolvedValue, onChange: handleChange, open, setOpen }}
    >
      <div className="select-root">{children}</div>
    </SelectContext.Provider>
  );
}

function Trigger({ children }: { children: ReactNode }) {
  const { value, open, setOpen } = useSelectContext();
  return (
    <button
      aria-expanded={open}
      onClick={() => setOpen((prev) => !prev)}
    >
      {value ?? children}
    </button>
  );
}

function Option({ value, children }: { value: string; children: ReactNode }) {
  const { value: selected, onChange } = useSelectContext();
  return (
    <div
      role="option"
      aria-selected={selected === value}
      onClick={() => onChange(value)}
    >
      {children}
    </div>
  );
}

// Attach sub-components for dot-notation API
Select.Trigger = Trigger;
Select.Option = Option;
```

### Usage

```tsx
<Select onChange={(v) => console.log(v)}>
  <Select.Trigger>Pick a fruit</Select.Trigger>
  <Select.Option value="apple">Apple</Select.Option>
  <Select.Option value="banana">Banana</Select.Option>
</Select>
```

### Tabs Template

```tsx
import { createContext, useContext, useState, type ReactNode } from "react";

interface TabsContextValue {
  activeTab: string;
  setActiveTab: (id: string) => void;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext() {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error("Tabs components must be used within <Tabs>");
  return ctx;
}

function Tabs({ defaultTab, children }: { defaultTab: string; children: ReactNode }) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div role="tablist">{children}</div>
    </TabsContext.Provider>
  );
}

function Tab({ id, children }: { id: string; children: ReactNode }) {
  const { activeTab, setActiveTab } = useTabsContext();
  return (
    <button role="tab" aria-selected={activeTab === id} onClick={() => setActiveTab(id)}>
      {children}
    </button>
  );
}

function Panel({ id, children }: { id: string; children: ReactNode }) {
  const { activeTab } = useTabsContext();
  if (activeTab !== id) return null;
  return <div role="tabpanel">{children}</div>;
}

Tabs.Tab = Tab;
Tabs.Panel = Panel;
```

### Interview Talking Points

- Context is the communication channel; `children` is the composition mechanism.
- The `useSelectContext` guard enforces correct usage at runtime.
- This pattern cleanly supports controlled and uncontrolled modes.
- For static sub-component typing with dot-notation, you can use a namespace object or assign to the function directly (as above). Both work; the namespace approach is slightly cleaner for tree-shaking.

---

## Render Props

A render prop is a function prop that a component calls to delegate rendering. Despite hooks replacing most render prop use cases, the pattern remains relevant for **headless logic sharing** where you want to inject UI into a component's render cycle.

### When Render Props Still Win Over Hooks

| Scenario | Hooks | Render Props |
|---|---|---|
| Sharing stateful logic | Preferred | Works |
| Injecting UI into a third-party component's render cycle | Cannot | Required |
| Conditional rendering based on internal state (e.g., virtualized list) | Awkward | Natural |
| Library consumers who want zero abstraction | N/A | Ideal |

### Implementation

```tsx
import { useState, useEffect, type ReactNode } from "react";

interface MousePosition {
  x: number;
  y: number;
}

interface MouseTrackerProps {
  children: (position: MousePosition) => ReactNode;
}

function MouseTracker({ children }: MouseTrackerProps) {
  const [position, setPosition] = useState<MousePosition>({ x: 0, y: 0 });

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  return <>{children(position)}</>;
}

// Usage
<MouseTracker>
  {({ x, y }) => (
    <div>
      Cursor: {x}, {y}
    </div>
  )}
</MouseTracker>;
```

### Real-World Example: Downshift

Downshift (by Kent C. Dodds) is the canonical render-prop library. Even after adding hooks (`useCombobox`, `useSelect`), the render-prop API persists because it allows full control over what gets rendered inside the dropdown without requiring the consumer to manage any internal state.

---

## Higher-Order Components (HOCs)

An HOC is a function that takes a component and returns a new component with additional behavior. This is a **legacy pattern** — hooks have replaced nearly every legitimate HOC use case. Interviews still ask about HOCs because:

1. Large codebases (especially pre-hooks) are full of them.
2. Understanding HOCs proves you understand closures, component identity, and ref forwarding.
3. Some cross-cutting concerns (e.g., auth gating at the route level) are still occasionally expressed as HOCs.

### Implementation

```tsx
import { type ComponentType, type ComponentProps, forwardRef } from "react";

// --- withAuth: gate a component behind authentication ---
interface WithAuthProps {
  isAuthenticated: boolean;
}

function withAuth<T extends ComponentType<any>>(WrappedComponent: T) {
  type Props = Omit<ComponentProps<T>, keyof WithAuthProps> & WithAuthProps;

  const AuthGated = forwardRef<any, Props>(
    ({ isAuthenticated, ...rest }, ref) => {
      if (!isAuthenticated) {
        return <div>Please log in.</div>;
      }
      return <WrappedComponent ref={ref} {...(rest as any)} />;
    }
  );

  AuthGated.displayName = `withAuth(${
    WrappedComponent.displayName || WrappedComponent.name || "Component"
  })`;

  return AuthGated;
}

// --- withLogging: log renders ---
function withLogging<P extends object>(WrappedComponent: ComponentType<P>) {
  function Logged(props: P) {
    console.log(`[Render] ${WrappedComponent.displayName || WrappedComponent.name}`, props);
    return <WrappedComponent {...props} />;
  }

  Logged.displayName = `withLogging(${
    WrappedComponent.displayName || WrappedComponent.name || "Component"
  })`;

  return Logged;
}
```

### Why HOCs Are Problematic

- **Prop collisions:** Multiple HOCs can inject props with the same name.
- **Wrapper hell:** DevTools become unreadable with deeply nested HOC wrappers.
- **Static typing pain:** Inferring the resulting prop types across composed HOCs is extremely difficult in TypeScript.
- **Ref forwarding:** Every HOC must remember to forward refs or they silently break.

---

## Headless Components / Hooks

The headless pattern separates **logic** (state, keyboard interactions, ARIA attributes) from **UI** (markup, styles). The consumer provides all rendering; the library provides all behavior.

### Hook-Based Headless Component

```tsx
import { useState, useCallback, useRef, useId, type KeyboardEvent } from "react";

interface UseToggleOptions {
  defaultPressed?: boolean;
  onChange?: (pressed: boolean) => void;
}

interface UseToggleReturn {
  pressed: boolean;
  buttonProps: {
    id: string;
    role: "switch";
    "aria-checked": boolean;
    onClick: () => void;
    onKeyDown: (e: KeyboardEvent) => void;
  };
}

function useToggle({
  defaultPressed = false,
  onChange,
}: UseToggleOptions = {}): UseToggleReturn {
  const [pressed, setPressed] = useState(defaultPressed);
  const id = useId();

  const toggle = useCallback(() => {
    setPressed((prev) => {
      const next = !prev;
      onChange?.(next);
      return next;
    });
  }, [onChange]);

  const onKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    },
    [toggle]
  );

  return {
    pressed,
    buttonProps: {
      id,
      role: "switch",
      "aria-checked": pressed,
      onClick: toggle,
      onKeyDown,
    },
  };
}

// --- Usage: consumer owns all rendering ---
function FancyToggle() {
  const { pressed, buttonProps } = useToggle({
    onChange: (v) => console.log("Toggled:", v),
  });

  return (
    <button
      {...buttonProps}
      className={pressed ? "bg-green-500" : "bg-gray-300"}
    >
      {pressed ? "ON" : "OFF"}
    </button>
  );
}
```

### Libraries to Know

| Library | Approach | Notes |
|---|---|---|
| Radix Primitives | Unstyled components + CSS | Compound component API, full ARIA |
| Headless UI (Tailwind) | Unstyled components | Designed for Tailwind, render props + hooks |
| Downshift | Hooks + render props | Combobox/select, pioneered the pattern |
| TanStack Table | Headless hooks | Zero UI, full table logic |
| React Aria (Adobe) | Hooks only | Most complete ARIA implementation |

---

## Controlled vs. Uncontrolled Components

A **controlled** component derives its state from props. An **uncontrolled** component manages its own internal state. The distinction applies to any stateful component, not just form inputs.

### The Dual-Mode Pattern

Production components should support both modes. This is how every serious component library works.

```tsx
import { useState, useCallback } from "react";

/**
 * A hook that supports both controlled and uncontrolled state.
 * If the consumer passes a value, the component is controlled.
 * Otherwise, it manages its own internal state.
 */
function useControllableState<T>({
  value: controlledValue,
  defaultValue,
  onChange,
}: {
  value?: T;
  defaultValue: T;
  onChange?: (value: T) => void;
}) {
  const [internalValue, setInternalValue] = useState(defaultValue);

  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const setValue = useCallback(
    (next: T | ((prev: T) => T)) => {
      const resolvedNext =
        typeof next === "function" ? (next as (prev: T) => T)(value) : next;

      if (!isControlled) {
        setInternalValue(resolvedNext);
      }
      onChange?.(resolvedNext);
    },
    [isControlled, value, onChange]
  );

  return [value, setValue] as const;
}

// --- Usage ---
interface InputProps {
  value?: string;
  defaultValue?: string;
  onChange?: (value: string) => void;
}

function Input({ value, defaultValue = "", onChange }: InputProps) {
  const [inputValue, setInputValue] = useControllableState({
    value,
    defaultValue,
    onChange,
  });

  return (
    <input
      value={inputValue}
      onChange={(e) => setInputValue(e.target.value)}
    />
  );
}
```

### Interview Talking Points

- **Never switch between controlled and uncontrolled** during a component's lifetime. React will warn. The `useControllableState` hook handles this cleanly by checking `controlledValue !== undefined` on every render.
- **Uncontrolled is simpler** for forms where you only need the value on submit (`useRef` + `ref`).
- **Controlled is required** when you need to validate, transform, or synchronize values in real time.

---

## Polymorphic Components

A polymorphic component lets the consumer change the rendered element via an `as` prop. This is essential for design systems where a `<Button>` might need to render as an `<a>`, a `<Link>`, or a `<div>`.

### TypeScript-Safe Implementation

```tsx
import {
  forwardRef,
  type ElementType,
  type ComponentPropsWithRef,
  type ReactNode,
} from "react";

// --- Type utilities ---
type PolymorphicRef<C extends ElementType> =
  ComponentPropsWithRef<C>["ref"];

type PolymorphicProps<
  C extends ElementType,
  OwnProps = {},
> = OwnProps &
  Omit<ComponentPropsWithRef<C>, keyof OwnProps | "as"> & {
    as?: C;
  };

// --- Component ---
type ButtonOwnProps = {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md" | "lg";
  children: ReactNode;
};

type ButtonProps<C extends ElementType = "button"> = PolymorphicProps<
  C,
  ButtonOwnProps
>;

type ButtonComponent = <C extends ElementType = "button">(
  props: ButtonProps<C>
) => ReactNode;

const Button: ButtonComponent = forwardRef(
  <C extends ElementType = "button">(
    { as, variant = "primary", size = "md", children, ...rest }: ButtonProps<C>,
    ref: PolymorphicRef<C>
  ) => {
    const Component = as || "button";
    return (
      <Component ref={ref} {...rest}>
        {children}
      </Component>
    );
  }
) as ButtonComponent;
```

### Polymorphic Text Template

```tsx
import { forwardRef, type ElementType, type ComponentPropsWithRef, type ReactNode } from "react";

type PolyProps<C extends ElementType, Own = {}> =
  Own & Omit<ComponentPropsWithRef<C>, keyof Own | "as"> & { as?: C };

type TextOwnProps = { size?: "sm" | "md" | "lg"; weight?: "normal" | "bold" };

type TextProps<C extends ElementType = "span"> = PolyProps<C, TextOwnProps>;

type TextComponent = <C extends ElementType = "span">(props: TextProps<C>) => ReactNode;

const Text: TextComponent = forwardRef(
  <C extends ElementType = "span">(
    { as, size = "md", weight = "normal", ...rest }: TextProps<C>,
    ref: ComponentPropsWithRef<C>["ref"]
  ) => {
    const Comp = as || "span";
    return <Comp ref={ref} data-size={size} data-weight={weight} {...rest} />;
  }
) as TextComponent;
```

### Usage With Full Type Safety

```tsx
// Renders <button>, gets ButtonHTMLAttributes
<Button variant="primary" onClick={() => {}}>Click</Button>

// Renders <a>, gets AnchorHTMLAttributes (href is valid)
<Button as="a" href="/about" variant="secondary">About</Button>

// Renders a custom Link component, gets its props
<Button as={Link} to="/dashboard" variant="ghost">Dashboard</Button>

// Type error: href is not valid on <button>
<Button href="/nope">Nope</Button>
```

### The forwardRef + Generics Problem

`forwardRef` does not natively support generic components — its type signature fixes the props at the call site. The `as ButtonComponent` cast above is the standard workaround. React 19's `ref` as a regular prop may eliminate this friction entirely.

---

## Slot Pattern

The slot pattern uses `children` and named props to give consumers control over specific rendering regions of a component.

### Named Slots Via Props

```tsx
import { type ReactNode } from "react";

interface CardProps {
  header?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
}

function Card({ header, footer, children, actions }: CardProps) {
  return (
    <div className="card">
      {header && <div className="card-header">{header}</div>}
      <div className="card-body">{children}</div>
      {actions && <div className="card-actions">{actions}</div>}
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

// Usage
<Card
  header={<h2>Title</h2>}
  footer={<small>Last updated: today</small>}
  actions={
    <>
      <button>Save</button>
      <button>Cancel</button>
    </>
  }
>
  <p>Card body content</p>
</Card>;
```

### React.Children Utilities (and Why to Avoid Them)

`React.Children` utilities (`map`, `forEach`, `toArray`, `count`) are considered legacy. They break when children are wrapped in fragments or returned from other components. Prefer explicit named-slot props or compound components with Context.

---

## Provider Pattern

The provider pattern uses React Context to inject dependencies (state, dispatch functions, services) into a subtree.

### The Problem: Provider Hell

```tsx
// This is real and it is terrible
function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <I18nProvider>
          <RouterProvider>
            <QueryClientProvider>
              <NotificationProvider>
                <FeatureFlagProvider>
                  <AppContent />
                </FeatureFlagProvider>
              </NotificationProvider>
            </QueryClientProvider>
          </RouterProvider>
        </I18nProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
```

### Solution: Provider Composition Utility

```tsx
import { type ReactNode, type ComponentType } from "react";

type ProviderWithProps = [ComponentType<{ children: ReactNode }>, Record<string, unknown>?];

function ComposeProviders({
  providers,
  children,
}: {
  providers: ProviderWithProps[];
  children: ReactNode;
}) {
  return providers.reduceRight<ReactNode>(
    (acc, [Provider, props]) => <Provider {...props}>{acc}</Provider>,
    children
  );
}

// Usage
function App() {
  return (
    <ComposeProviders
      providers={[
        [ThemeProvider, { theme: darkTheme }],
        [AuthProvider],
        [I18nProvider, { locale: "en" }],
        [RouterProvider],
        [QueryClientProvider, { client: queryClient }],
        [NotificationProvider],
        [FeatureFlagProvider],
      ]}
    >
      <AppContent />
    </ComposeProviders>
  );
}
```

### Interview Talking Points

- Provider ordering matters. A provider can only consume contexts above it.
- Split contexts: separate read-heavy (state) from write-heavy (dispatch) contexts to avoid unnecessary re-renders.
- Consider colocation: not everything needs to be at the app root. A `FormContext` should wrap only the form.

---

## Error Boundaries

Error boundaries catch JavaScript errors in their child component tree during rendering, in lifecycle methods, and in constructors. They **do not** catch errors in event handlers, async code, or server-side rendering.

### Why Still Class-Based

There is no hook equivalent for `componentDidCatch` or `getDerivedStateFromError`. These are the only two class lifecycle methods without hook counterparts. React has not introduced a hook-based error boundary API (as of React 19).

### Implementation

```tsx
import {
  Component,
  type ReactNode,
  type ErrorInfo,
} from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.props.onError?.(error, errorInfo);
  }

  private reset = () => {
    this.setState({ error: null });
  };

  render() {
    const { error } = this.state;
    const { fallback, children } = this.props;

    if (error) {
      if (typeof fallback === "function") {
        return fallback(error, this.reset);
      }
      return fallback;
    }

    return children;
  }
}
```

### Usage With Recovery

```tsx
<ErrorBoundary
  fallback={(error, reset) => (
    <div role="alert">
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
      <button onClick={reset}>Try again</button>
    </div>
  )}
  onError={(error, info) => {
    // Send to error tracking service
    Sentry.captureException(error, { extra: info });
  }}
>
  <SomeFragileComponent />
</ErrorBoundary>
```

### Patterns for Production

- **Granular boundaries:** Wrap individual features, not the entire app. A crashing sidebar should not take down the main content.
- **Error boundary + Suspense:** Place `ErrorBoundary` above `Suspense` to catch both rendering errors and failed lazy loads.
- **Key-based reset:** Change the `key` prop on the ErrorBoundary to force a full remount of the subtree instead of using imperative `reset()`.

```tsx
function ResettableFeature() {
  const [boundaryKey, setBoundaryKey] = useState(0);

  return (
    <ErrorBoundary
      key={boundaryKey}
      fallback={
        <button onClick={() => setBoundaryKey((k) => k + 1)}>
          Retry
        </button>
      }
    >
      <FeatureComponent />
    </ErrorBoundary>
  );
}
```

---

## Discriminated Union Props

Use TypeScript discriminated unions to make component prop combinations **mutually exclusive** and **exhaustively type-checked**.

### The Problem

```tsx
// Bad: nothing prevents passing both href and onClick, or neither
interface ButtonProps {
  href?: string;
  onClick?: () => void;
  external?: boolean; // only relevant if href is set
}
```

### The Solution: Discriminated Unions

```tsx
type LinkButtonProps = {
  as: "link";
  href: string;
  external?: boolean;
  onClick?: never; // explicitly disallowed
};

type ActionButtonProps = {
  as: "button";
  onClick: () => void;
  href?: never;
  external?: never;
};

type SubmitButtonProps = {
  as: "submit";
  href?: never;
  onClick?: never;
  external?: never;
};

type ButtonProps = (LinkButtonProps | ActionButtonProps | SubmitButtonProps) & {
  children: ReactNode;
  variant?: "primary" | "secondary";
  disabled?: boolean;
};

function Button(props: ButtonProps) {
  switch (props.as) {
    case "link":
      return (
        <a
          href={props.href}
          target={props.external ? "_blank" : undefined}
          rel={props.external ? "noopener noreferrer" : undefined}
        >
          {props.children}
        </a>
      );
    case "button":
      return (
        <button onClick={props.onClick} disabled={props.disabled}>
          {props.children}
        </button>
      );
    case "submit":
      return (
        <button type="submit" disabled={props.disabled}>
          {props.children}
        </button>
      );
  }
}
```

### Modal Discriminated Union Template

```tsx
type ModalProps =
  | { variant: "confirm"; onConfirm: () => void; onCancel: () => void; destructive?: boolean }
  | { variant: "alert"; onAcknowledge: () => void }
  | { variant: "prompt"; onSubmit: (value: string) => void; defaultValue?: string };

type CommonModalProps = {
  title: string;
  open: boolean;
  onClose: () => void;
};

type FullModalProps = ModalProps & CommonModalProps;

function Modal(props: FullModalProps) {
  if (!props.open) return null;

  switch (props.variant) {
    case "confirm":
      return (/* confirm UI: onConfirm + onCancel */);
    case "alert":
      return (/* alert UI: onAcknowledge */);
    case "prompt":
      return (/* prompt UI: onSubmit */);
  }
}
```

### Advanced: Exhaustiveness Checking

```tsx
function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}

function renderButton(props: ButtonProps) {
  switch (props.as) {
    case "link":
      return /* ... */;
    case "button":
      return /* ... */;
    case "submit":
      return /* ... */;
    default:
      // If a new variant is added but not handled, this is a compile error
      return assertNever(props.as);
  }
}
```

---

## Practice

- **Build a compound component**: Create a `<Tabs>` / `<Tabs.List>` / `<Tabs.Tab>` / `<Tabs.Panel>` compound component using Context. Support both controlled and uncontrolled modes with the `useControllableState` pattern from this lesson.
- **Headless hook exercise**: Extract the logic from your `<Tabs>` compound component into a `useTabs` headless hook. The hook should return `{ activeTab, setActiveTab, getTabProps, getPanelProps }`. Build two completely different UIs that use the same hook.
- **Polymorphic `as` prop**: Build a `<Box>` component that accepts an `as` prop and correctly forwards all HTML attributes for the given element type. Verify TypeScript catches invalid prop combinations (e.g., `<Box as="input" href="..." />` should be a type error).
- **Error boundary + key reset**: Build an error boundary that displays a "Retry" button. On click, use the key-reset pattern to remount the failed subtree. Verify that state is fully reset.
- **Discriminated union props**: Build a `<Button>` with three variants (`as: "button" | "link" | "submit"`), each with different required props. Use `never` types to ban invalid combinations and `assertNever` for exhaustive switching.

### Related Lessons

- [Hooks & State Management](../01-hooks-deep-dive/01-hooks-and-state-management.md) -- `useState`, `useRef`, `useContext` fundamentals used inside compound components and headless hooks
- [Custom Hooks Fundamentals](../02-custom-hooks/01-custom-hooks-fundamentals.md) -- hook composition and return value contracts for headless hook patterns
- [Advanced Component APIs](02-advanced-component-apis.md) -- IoC, generic component typing, builder pattern, design system patterns
- [State Management Fundamentals](../05-state-management/01-state-management-fundamentals.md) -- Context API patterns used in compound components and provider composition

---

## Key Takeaways for Interviews

1. **Compound components** are the gold standard for related component groups. Know how to build one from scratch with Context.
2. **Render props** are not dead. They are the right tool when hooks cannot inject into a render cycle.
3. **HOCs** are legacy. Know their problems (prop collision, ref forwarding, type inference) and why hooks replaced them.
4. **Headless hooks** are the modern approach to logic sharing. Name-drop Radix, React Aria, or TanStack.
5. **Controlled vs. uncontrolled** is fundamental. The `useControllableState` hook is a pattern worth memorizing.
6. **Polymorphic `as` prop** with correct TypeScript is a design system must-have. Know the `forwardRef` generics limitation.
7. **Provider composition** solves provider hell. Split read/write contexts.
8. **Error boundaries** are still class-based. Know why, and know the key-based reset trick.
9. **Discriminated unions** are the TypeScript-native way to model component variants. Use `never` to ban invalid prop combinations.

---

## Quick Templates

**Controllable state hook** — support both controlled and uncontrolled:
```tsx
function useControllableState<T>({ value, defaultValue, onChange }: {
  value?: T; defaultValue: T; onChange?: (v: T) => void;
}) {
  const [internal, setInternal] = useState(defaultValue);
  const isControlled = value !== undefined;
  const resolved = isControlled ? value : internal;
  const setValue = (next: T) => { if (!isControlled) setInternal(next); onChange?.(next); };
  return [resolved, setValue] as const;
}
```

**Provider composition** — flatten nested providers:
```tsx
function ComposeProviders({ providers, children }: {
  providers: [React.ComponentType<{ children: ReactNode }>, Record<string, unknown>?][];
  children: ReactNode;
}) {
  return providers.reduceRight<ReactNode>(
    (acc, [P, props]) => <P {...props}>{acc}</P>, children
  );
}
```

**Exhaustive switch** — compile-time guard against unhandled variants:
```tsx
function assertNever(x: never): never { throw new Error(`Unhandled: ${x}`); }
```

**Key-based error recovery** — remount subtree on error:
```tsx
const [key, setKey] = useState(0);
<ErrorBoundary key={key} fallback={<button onClick={() => setKey(k => k + 1)}>Retry</button>}>
  <Feature />
</ErrorBoundary>
```

**Generic list component** — type-safe data rendering:
```tsx
function List<T>({ items, renderItem, keyFn }: {
  items: T[]; renderItem: (item: T) => ReactNode; keyFn: (item: T) => string;
}) {
  return <ul>{items.map(item => <li key={keyFn(item)}>{renderItem(item)}</li>)}</ul>;
}
```
