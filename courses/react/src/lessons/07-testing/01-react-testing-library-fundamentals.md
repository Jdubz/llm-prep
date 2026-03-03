# React Testing Library Fundamentals

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [RTL Query Priority](#rtl-query-priority)
3. [User Events](#user-events)
4. [Async Testing](#async-testing)
5. [Mocking Strategies](#mocking-strategies)
6. [Testing Patterns](#testing-patterns)
7. [Snapshot Testing](#snapshot-testing)
8. [Accessibility Testing](#accessibility-testing)
9. [Test Organization](#test-organization)
10. [Common Interview Questions](#common-interview-questions)

---

## Testing Philosophy

### Test Behavior, Not Implementation

The single most important principle in React testing: **your tests should resemble the way your software is used**. Users don't know about state variables, effect hooks, or re-render cycles. They see buttons, text, and forms. Test from that perspective.

```tsx
// BAD: testing implementation details
it('sets isOpen state to true when clicked', () => {
  const { result } = renderHook(() => useState(false));
  act(() => result.current[1](true));
  expect(result.current[0]).toBe(true);
});

// GOOD: testing behavior
it('opens the dropdown when the trigger is clicked', async () => {
  const user = userEvent.setup();
  render(<Dropdown items={['Apple', 'Banana']} />);

  await user.click(screen.getByRole('button', { name: /select fruit/i }));

  expect(screen.getByRole('listbox')).toBeInTheDocument();
  expect(screen.getByRole('option', { name: /apple/i })).toBeInTheDocument();
});
```

Implementation detail tests break when you refactor. Behavior tests break when the behavior changes. That is exactly what you want.

### The Testing Trophy

Kent C. Dodds' testing trophy (not pyramid) prioritizes:

```
        ╱  E2E  ╲           Few — high confidence, slow, expensive
       ╱──────────╲
      ╱ Integration ╲       Most tests here — best confidence/cost ratio
     ╱────────────────╲
    ╱    Unit Tests     ╲    Some — pure logic, utilities, hooks
   ╱──────────────────────╲
  ╱      Static Analysis    ╲  TypeScript, ESLint — cheapest, always on
 ╱────────────────────────────╲
```

**Integration tests** are the sweet spot for React. They render a component with its real children, real hooks, and mocked network calls. They give you the highest confidence-to-cost ratio because they exercise how components actually compose together.

### Core Principles

1. **The more your tests resemble the way your software is used, the more confidence they give you.**
2. **Write tests. Not too many. Mostly integration.**
3. **Avoid testing implementation details** — no querying by class name, no asserting internal state.
4. **If it's hard to test, the component design is probably wrong.** Tests act as a design pressure.
5. **One assertion per behavioral claim**, not one assertion per test. A test that verifies "user can submit a form" might assert several things.

---

## RTL Query Priority

RTL deliberately makes you use accessible queries. The priority order reflects what users and assistive technology actually interact with:

| Priority | Query | Use When | Example |
|----------|-------|----------|---------|
| 1 | `getByRole` | Almost always. Buttons, headings, textboxes, etc. | `screen.getByRole('button', { name: /save/i })` |
| 2 | `getByLabelText` | Form fields with proper labels | `screen.getByLabelText(/email address/i)` |
| 3 | `getByPlaceholderText` | When label is absent (not ideal) | `screen.getByPlaceholderText(/search/i)` |
| 4 | `getByText` | Non-interactive elements, paragraphs, spans | `screen.getByText(/no results/i)` |
| 5 | `getByDisplayValue` | Filled-in form inputs | `screen.getByDisplayValue('alice@test.com')` |
| 6 | `getByAltText` | Images | `screen.getByAltText(/user avatar/i)` |
| 7 | `getByTitle` | Title attribute (less accessible) | `screen.getByTitle(/close/i)` |
| 8 | `getByTestId` | Last resort. Not visible to users. | `screen.getByTestId('chart-canvas')` |

**Variants**: `getBy` (throws), `queryBy` (returns null), `findBy` (async), plus `All` versions of each.

```tsx
// Prefer role-based queries — they enforce accessibility
screen.getByRole('button', { name: /submit/i });
screen.getByRole('heading', { level: 2 });
screen.getByRole('textbox', { name: /email/i });
screen.getByRole('checkbox', { name: /agree to terms/i });
screen.getByRole('combobox', { name: /country/i });

// Good for form fields with visible labels
screen.getByLabelText(/email address/i);

// Acceptable for non-interactive content
screen.getByText(/no results found/i);

// Last resort — use data-testid only when no accessible query works
screen.getByTestId('complex-svg-chart');
```

### The `screen` Object

Always use `screen` instead of destructuring from `render()`. It makes tests more readable and ensures you are querying the full document.

```tsx
// AVOID: destructuring queries
const { getByRole, getByText } = render(<MyComponent />);

// PREFER: screen
render(<MyComponent />);
const button = screen.getByRole('button', { name: /save/i });
```

The only exception is when you need `container` for something truly not queryable via accessible means, or `rerender` / `unmount`:

```tsx
const { rerender, unmount } = render(<Counter count={0} />);
rerender(<Counter count={5} />);
expect(screen.getByText('5')).toBeInTheDocument();
unmount();
```

### `within()` for Scoped Queries

When the same role or text appears multiple times, scope your queries:

```tsx
import { within } from '@testing-library/react';

render(<Dashboard />);

const sidebar = screen.getByRole('navigation', { name: /sidebar/i });
const mainContent = screen.getByRole('main');

// Query within specific regions
const sidebarLinks = within(sidebar).getAllByRole('link');
const mainHeading = within(mainContent).getByRole('heading', { level: 1 });
```

This is especially useful for tables, lists, and multi-section layouts:

```tsx
render(<UserTable users={mockUsers} />);

const rows = screen.getAllByRole('row');
// Skip header row
const firstDataRow = rows[1];

expect(within(firstDataRow).getByText('jane@example.com')).toBeInTheDocument();
expect(within(firstDataRow).getByRole('button', { name: /edit/i })).toBeEnabled();
```

### Common Assertions

```tsx
// Presence
expect(element).toBeInTheDocument();
expect(screen.queryByText(/gone/i)).not.toBeInTheDocument();

// Visibility
expect(element).toBeVisible();
expect(element).not.toBeVisible(); // hidden, display:none, etc.

// Text content
expect(element).toHaveTextContent(/welcome/i);
expect(element).toHaveTextContent('Exact text');

// Form state
expect(input).toHaveValue('alice@test.com');
expect(input).toHaveDisplayValue('alice@test.com');
expect(checkbox).toBeChecked();
expect(button).toBeDisabled();
expect(button).toBeEnabled();
expect(input).toBeRequired();
expect(input).toBeInvalid();
expect(input).toHaveAttribute('type', 'email');

// Accessibility
expect(element).toHaveAccessibleName(/submit form/i);
expect(element).toHaveAccessibleDescription(/sends your data/i);
expect(element).toHaveRole('button');

// CSS
expect(element).toHaveClass('active');
expect(element).toHaveStyle({ display: 'flex' });

// Focus
expect(input).toHaveFocus();
```

---

## User Events

### `userEvent` vs `fireEvent`

`fireEvent` dispatches a single DOM event. `userEvent` simulates the full interaction sequence a real user triggers — including focus, pointer events, keyboard events, and input events in the correct order.

```tsx
import userEvent from '@testing-library/user-event';

// AVOID: fireEvent — skips intermediate events
fireEvent.click(button);
fireEvent.change(input, { target: { value: 'hello' } });

// PREFER: userEvent — fires the full realistic event chain
const user = userEvent.setup();
await user.click(button);  // pointerdown, mousedown, pointerup, mouseup, click
await user.type(input, 'hello');  // focus, keydown, keypress, input, keyup per char
```

**Always call `userEvent.setup()` before rendering.** This creates a user instance with its own internal state (pointer position, keyboard state, clipboard).

```tsx
it('handles multi-step interaction', async () => {
  const user = userEvent.setup();
  render(<TextEditor />);

  const editor = screen.getByRole('textbox');
  await user.click(editor);
  await user.keyboard('Hello{Enter}World');

  expect(editor).toHaveValue('Hello\nWorld');
});
```

### userEvent Cheat Sheet

```tsx
const user = userEvent.setup();

// Click
await user.click(element);
await user.dblClick(element);
await user.tripleClick(element);    // Select full line of text

// Typing
await user.type(input, 'hello');    // Types one char at a time
await user.clear(input);            // Clears input value
await user.type(input, '{Enter}');  // Special keys in braces

// Keyboard (no target needed — uses focused element)
await user.keyboard('hello');
await user.keyboard('{Enter}');
await user.keyboard('{Shift>}A{/Shift}');  // Hold Shift, type A
await user.keyboard('{Control>}a{/Control}'); // Ctrl+A (select all)
await user.keyboard('{ArrowDown}');
await user.keyboard('{Escape}');
await user.keyboard('{Backspace}');

// Tab navigation
await user.tab();                   // Tab forward
await user.tab({ shift: true });    // Shift+Tab backward

// Select / dropdown
await user.selectOptions(select, 'value');
await user.selectOptions(select, ['val1', 'val2']); // Multi-select
await user.deselectOptions(select, 'value');

// Pointer
await user.hover(element);
await user.unhover(element);
await user.pointer('[MouseLeft]');  // Low-level pointer API

// Clipboard
await user.copy();
await user.cut();
await user.paste('pasted text');

// File upload
const file = new File(['content'], 'file.txt', { type: 'text/plain' });
await user.upload(fileInput, file);
await user.upload(fileInput, [file1, file2]); // Multiple files
```

### Keyboard Navigation Testing

Testing keyboard interactions is critical for accessibility and a frequent interview topic:

```tsx
it('supports full keyboard navigation in dropdown', async () => {
  const user = userEvent.setup();
  render(<Select options={['Red', 'Green', 'Blue']} label="Color" />);

  // Tab to focus the trigger
  await user.tab();
  expect(screen.getByRole('combobox', { name: /color/i })).toHaveFocus();

  // Open with Enter
  await user.keyboard('{Enter}');
  expect(screen.getByRole('listbox')).toBeInTheDocument();

  // Navigate options with arrow keys
  await user.keyboard('{ArrowDown}');
  expect(screen.getByRole('option', { name: /red/i })).toHaveAttribute(
    'aria-selected',
    'true'
  );

  await user.keyboard('{ArrowDown}');
  expect(screen.getByRole('option', { name: /green/i })).toHaveAttribute(
    'aria-selected',
    'true'
  );

  // Select with Enter
  await user.keyboard('{Enter}');
  expect(screen.getByRole('combobox')).toHaveTextContent('Green');
  expect(screen.queryByRole('listbox')).not.toBeInTheDocument();

  // Escape closes without selecting
  await user.keyboard('{Enter}');
  await user.keyboard('{Escape}');
  expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  expect(screen.getByRole('combobox')).toHaveTextContent('Green');
});
```

---

## Async Testing

### `waitFor`

Use `waitFor` when you need to wait for an assertion to pass. It retries the callback on an interval until it passes or times out.

```tsx
it('shows success message after save', async () => {
  const user = userEvent.setup();
  render(<ProfileForm />);

  await user.type(screen.getByLabelText(/name/i), 'Jane');
  await user.click(screen.getByRole('button', { name: /save/i }));

  await waitFor(() => {
    expect(screen.getByRole('alert')).toHaveTextContent(/saved successfully/i);
  });
});
```

**Rules for `waitFor`:**

1. Put only the assertion inside `waitFor`, not the action:

```tsx
// BAD: side effects inside waitFor get called multiple times
await waitFor(() => {
  fireEvent.click(button);
  expect(result).toBeInTheDocument();
});

// GOOD: action outside, assertion inside
await user.click(button);
await waitFor(() => {
  expect(result).toBeInTheDocument();
});
```

2. Prefer `findBy` queries over `waitFor` + `getBy`:

```tsx
// Verbose
await waitFor(() => {
  expect(screen.getByText(/loaded/i)).toBeInTheDocument();
});

// Concise — findBy = getBy + waitFor
expect(await screen.findByText(/loaded/i)).toBeInTheDocument();
```

### `findBy` Queries

`findBy` queries are sugar for `waitFor(() => getBy(...))`. They return a promise that resolves when the element appears. Use them for anything async:

```tsx
it('fetches and displays user data', async () => {
  render(<UserProfile userId="123" />);

  // Loading state is immediate
  expect(screen.getByText(/loading/i)).toBeInTheDocument();

  // Data appears asynchronously
  const heading = await screen.findByRole('heading', { name: /jane doe/i });
  expect(heading).toBeInTheDocument();

  // Loading state is gone
  expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
});
```

### waitFor / findBy Patterns

```tsx
// findBy = getBy + waitFor (preferred for single element)
const heading = await screen.findByRole('heading', { name: /title/i });

// waitFor — for complex assertions or multiple checks
await waitFor(() => {
  expect(screen.getByText(/saved/i)).toBeInTheDocument();
  expect(screen.queryByText(/saving/i)).not.toBeInTheDocument();
});

// waitForElementToBeRemoved — loading spinners
await waitForElementToBeRemoved(() => screen.queryByText(/loading/i));

// Custom timeout
await screen.findByText(/slow data/i, {}, { timeout: 5000 });
await waitFor(() => expect(el).toBeVisible(), { timeout: 5000 });

// Custom interval (default is 50ms)
await waitFor(() => expect(el).toBeVisible(), { interval: 100 });
```

### `act()` — When It Is Needed and When It Is Not

`act()` ensures state updates are flushed and the DOM is updated before you make assertions. RTL wraps `render`, `userEvent`, `fireEvent`, `waitFor`, and `findBy` in `act()` for you.

**You almost never need to call `act()` directly.** If you see the "not wrapped in act" warning, the solution is usually:

1. Use `await findBy...` or `await waitFor(...)` to wait for the async update.
2. Await the user event call.
3. Fix the component (maybe a missing cleanup in useEffect).

```tsx
// WARNING-PRODUCING CODE:
it('updates on timer', () => {
  render(<AutoRefresh />);
  jest.advanceTimersByTime(5000);
  // Warning: An update was not wrapped in act(...)
  expect(screen.getByText(/refreshed/i)).toBeInTheDocument();
});

// FIXED: wrap timer advancement in act
it('updates on timer', async () => {
  vi.useFakeTimers();
  render(<AutoRefresh />);

  await act(() => {
    vi.advanceTimersByTime(5000);
  });

  expect(screen.getByText(/refreshed/i)).toBeInTheDocument();
  vi.useRealTimers();
});
```

The legitimate use cases for manual `act()`:

- Advancing fake timers (`vi.advanceTimersByTime`, `vi.runAllTimers`)
- Manually resolving promises in tests
- Testing `renderHook` results where you trigger state updates directly

---

## Mocking Strategies

### MSW (Mock Service Worker)

MSW intercepts requests at the network level. Your components use their real `fetch`/`axios` calls; MSW intercepts them before they leave the process. This is the gold standard for API mocking because it tests the full request/response pipeline.

#### Server Setup

```tsx
// src/test/mocks/handlers.ts
import { http, HttpResponse, delay } from 'msw';
import type { User } from '@/types';

export const handlers = [
  http.get('/api/users', async () => {
    return HttpResponse.json<User[]>([
      { id: '1', name: 'Alice', email: 'alice@test.com' },
      { id: '2', name: 'Bob', email: 'bob@test.com' },
    ]);
  }),

  http.get('/api/users/:id', async ({ params }) => {
    const { id } = params;
    return HttpResponse.json<User>({
      id: id as string,
      name: 'Alice',
      email: 'alice@test.com',
    });
  }),

  http.post('/api/users', async ({ request }) => {
    const body = (await request.json()) as Partial<User>;
    return HttpResponse.json<User>(
      { id: '3', name: body.name!, email: body.email! },
      { status: 201 }
    );
  }),

  http.delete('/api/users/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
```

```tsx
// src/test/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

```tsx
// src/test/setup.ts (vitest setup file)
import { server } from './mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Setting `onUnhandledRequest: 'error'` is critical. It catches unhandled API calls — if your component fetches an endpoint you did not mock, the test fails immediately with a clear error instead of silently hanging.

#### MSW Handler Templates

```tsx
import { http, HttpResponse, delay } from 'msw';

// GET — return list
http.get('/api/items', () => {
  return HttpResponse.json([{ id: '1', name: 'Item' }]);
});

// GET — with params
http.get('/api/items/:id', ({ params }) => {
  return HttpResponse.json({ id: params.id, name: 'Item' });
});

// GET — with query string
http.get('/api/search', ({ request }) => {
  const url = new URL(request.url);
  const q = url.searchParams.get('q');
  return HttpResponse.json({ results: [], query: q });
});

// POST — read body, return 201
http.post('/api/items', async ({ request }) => {
  const body = await request.json();
  return HttpResponse.json({ id: '2', ...body }, { status: 201 });
});

// PUT
http.put('/api/items/:id', async ({ params, request }) => {
  const body = await request.json();
  return HttpResponse.json({ id: params.id, ...body });
});

// DELETE — 204 no content
http.delete('/api/items/:id', () => {
  return new HttpResponse(null, { status: 204 });
});

// Error response
http.get('/api/items', () => {
  return HttpResponse.json({ message: 'Server Error' }, { status: 500 });
});

// Delayed response
http.get('/api/items', async () => {
  await delay(2000);
  return HttpResponse.json([]);
});

// Network error
http.get('/api/items', () => {
  return HttpResponse.error();
});
```

#### Per-Test Overrides

Override handlers inside a specific test to simulate errors, edge cases, or different data:

```tsx
import { http, HttpResponse, delay } from 'msw';
import { server } from '@/test/mocks/server';

it('shows error state when API fails', async () => {
  server.use(
    http.get('/api/users', () => {
      return HttpResponse.json(
        { message: 'Internal Server Error' },
        { status: 500 }
      );
    })
  );

  render(<UserList />);

  expect(await screen.findByRole('alert')).toHaveTextContent(
    /something went wrong/i
  );
});

it('shows loading skeleton during slow response', async () => {
  server.use(
    http.get('/api/users', async () => {
      await delay(2000);
      return HttpResponse.json([]);
    })
  );

  render(<UserList />);
  expect(screen.getByTestId('skeleton-loader')).toBeInTheDocument();
});

it('handles empty state', async () => {
  server.use(
    http.get('/api/users', () => {
      return HttpResponse.json([]);
    })
  );

  render(<UserList />);
  expect(await screen.findByText(/no users found/i)).toBeInTheDocument();
});
```

### `vi.mock` / `jest.mock`: Module Mocking

Use module mocking when MSW is not appropriate: routing, analytics, non-HTTP side effects, or browser APIs.

```tsx
// Mock an entire module
vi.mock('@/services/analytics', () => ({
  trackEvent: vi.fn(),
  trackPageView: vi.fn(),
  identify: vi.fn(),
}));

import { trackEvent } from '@/services/analytics';

it('tracks button click', async () => {
  const user = userEvent.setup();
  render(<FeatureCard feature={mockFeature} />);

  await user.click(screen.getByRole('button', { name: /learn more/i }));

  expect(trackEvent).toHaveBeenCalledWith('feature_click', {
    featureId: mockFeature.id,
  });
});
```

#### vi.mock Patterns

```tsx
// Mock entire module
vi.mock('@/lib/analytics', () => ({
  track: vi.fn(),
  identify: vi.fn(),
}));

// Partial mock (keep real implementations)
vi.mock('@/utils/format', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/utils/format')>();
  return { ...actual, formatDate: vi.fn(() => '2025-01-01') };
});

// Mock with hoisted variable (for per-test control)
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

// Spy on named export
import * as mod from '@/hooks/useAuth';
vi.spyOn(mod, 'useAuth').mockReturnValue({ user: null, isAuthenticated: false });

// Mock default export
vi.mock('@/components/Chart', () => ({
  default: () => <div data-testid="mock-chart" />,
}));

// Reset between tests
afterEach(() => {
  vi.restoreAllMocks();  // Restores spies to original
  // or
  vi.resetAllMocks();    // Resets call history + implementations
  // or
  vi.clearAllMocks();    // Resets call history only
});
```

### Mocking a Custom Hook

```tsx
import * as useAuthModule from '@/hooks/useAuth';

it('shows admin controls for admin users', () => {
  vi.spyOn(useAuthModule, 'useAuth').mockReturnValue({
    user: { id: '1', name: 'Admin', role: 'admin' },
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
  });

  render(<Settings />);

  expect(screen.getByRole('button', { name: /manage users/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /system config/i })).toBeInTheDocument();
});
```

---

## Testing Patterns

### Custom Render Wrapper

Every non-trivial React app wraps components in providers. Create a custom render that includes them all:

```tsx
// src/test/render.tsx
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, type MemoryRouterProps } from 'react-router-dom';
import type { ReactElement, ReactNode } from 'react';

interface Options extends Omit<RenderOptions, 'wrapper'> {
  routerProps?: MemoryRouterProps;
  queryClient?: QueryClient;
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  { routerProps, queryClient = createTestQueryClient(), ...rest }: Options = {}
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter {...routerProps}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }
  return { ...render(ui, { wrapper: Wrapper, ...rest }), queryClient };
}
```

### Test Structure Template

```tsx
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/render';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  describe('when data loads successfully', () => {
    it('displays the data', async () => {
      renderWithProviders(<MyComponent />);
      expect(await screen.findByText(/expected text/i)).toBeInTheDocument();
    });
  });

  describe('when the API fails', () => {
    it('shows an error message', async () => {
      server.use(
        http.get('/api/endpoint', () =>
          HttpResponse.json({ message: 'fail' }, { status: 500 })
        )
      );
      renderWithProviders(<MyComponent />);
      expect(await screen.findByRole('alert')).toHaveTextContent(/error/i);
    });
  });

  describe('user interactions', () => {
    it('does something on click', async () => {
      const user = userEvent.setup();
      renderWithProviders(<MyComponent />);
      await user.click(screen.getByRole('button', { name: /action/i }));
      await waitFor(() => {
        expect(screen.getByText(/result/i)).toBeInTheDocument();
      });
    });
  });
});
```

### Testing Forms

Forms are the most common interview testing scenario. Test the full user flow:

```tsx
it('validates and submits registration form', async () => {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  render(<RegistrationForm onSubmit={onSubmit} />);

  // Submit empty form -> validation errors
  await user.click(screen.getByRole('button', { name: /register/i }));

  expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  expect(screen.getByText(/password is required/i)).toBeInTheDocument();
  expect(onSubmit).not.toHaveBeenCalled();

  // Fill in invalid email
  await user.type(screen.getByLabelText(/email/i), 'not-an-email');
  await user.tab(); // Trigger blur validation

  expect(await screen.findByText(/invalid email/i)).toBeInTheDocument();

  // Fix email, fill password
  await user.clear(screen.getByLabelText(/email/i));
  await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
  await user.type(screen.getByLabelText(/^password$/i), 'Str0ng!Pass');
  await user.type(screen.getByLabelText(/confirm password/i), 'Str0ng!Pass');

  // Validation errors should be gone
  expect(screen.queryByText(/invalid email/i)).not.toBeInTheDocument();

  // Submit valid form
  await user.click(screen.getByRole('button', { name: /register/i }));

  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalledWith({
      email: 'alice@example.com',
      password: 'Str0ng!Pass',
    });
  });
});
```

### Testing Async Flows (Loading, Error, Data)

The canonical pattern for testing data-fetching components:

```tsx
describe('UserProfile', () => {
  it('shows loading state then user data', async () => {
    render(<UserProfile userId="1" />);

    // Assert loading state
    expect(screen.getByRole('status')).toHaveTextContent(/loading/i);

    // Wait for data
    expect(
      await screen.findByRole('heading', { name: /alice/i })
    ).toBeInTheDocument();

    // Assert loading state is removed
    expect(screen.queryByRole('status')).not.toBeInTheDocument();

    // Assert full content
    expect(screen.getByText('alice@test.com')).toBeInTheDocument();
  });

  it('shows error state on failure', async () => {
    server.use(
      http.get('/api/users/:id', () => {
        return HttpResponse.json(
          { message: 'Not Found' },
          { status: 404 }
        );
      })
    );

    render(<UserProfile userId="999" />);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /user not found/i
    );
  });

  it('refetches when userId changes', async () => {
    const { rerender } = render(<UserProfile userId="1" />);
    expect(await screen.findByText(/alice/i)).toBeInTheDocument();

    rerender(<UserProfile userId="2" />);
    expect(await screen.findByText(/bob/i)).toBeInTheDocument();
  });
});
```

### Test Data Factories

Avoid repetitive mock data. Use factories:

```tsx
// src/test/factories.ts
import type { User, Post, Comment } from '@/types';

let idCounter = 0;

export function createUser(overrides: Partial<User> = {}): User {
  idCounter++;
  return {
    id: `user-${idCounter}`,
    name: `User ${idCounter}`,
    email: `user${idCounter}@test.com`,
    role: 'viewer',
    createdAt: new Date().toISOString(),
    ...overrides,
  };
}

export function createPost(overrides: Partial<Post> = {}): Post {
  idCounter++;
  return {
    id: `post-${idCounter}`,
    title: `Post ${idCounter}`,
    body: 'Lorem ipsum dolor sit amet.',
    authorId: `user-1`,
    publishedAt: new Date().toISOString(),
    tags: [],
    ...overrides,
  };
}
```

Usage in tests:

```tsx
it('renders user list', async () => {
  const users = [
    createUser({ name: 'Alice', role: 'admin' }),
    createUser({ name: 'Bob' }),
    createUser({ name: 'Charlie' }),
  ];

  server.use(
    http.get('/api/users', () => HttpResponse.json(users))
  );

  render(<UserList />);

  for (const user of users) {
    expect(await screen.findByText(user.name)).toBeInTheDocument();
  }
});
```

---

## Snapshot Testing

### When Appropriate

Snapshots work well for small, stable, presentational components:

```tsx
it('renders icon button correctly', () => {
  const { container } = render(
    <IconButton icon="trash" label="Delete" variant="danger" />
  );
  expect(container.firstChild).toMatchSnapshot();
});
```

### When to Avoid

Avoid snapshots for:

- **Large components**: Snapshots become unreadable noise. Reviewers click "update snapshots" without reading.
- **Components with dynamic content**: IDs, dates, random values cause constant snapshot churn.
- **Anything where you care about behavior**: Snapshots test structure, not behavior. A button can be perfectly snapshotted and completely broken.

**Inline snapshots** are often better because the expected output lives in the test file:

```tsx
it('renders badge with correct class', () => {
  const { container } = render(<Badge status="active" />);
  expect(container.firstChild).toMatchInlineSnapshot(`
    <span
      class="badge badge--active"
    >
      Active
    </span>
  `);
});
```

---

## Accessibility Testing

### jest-axe

`jest-axe` runs axe-core accessibility checks against your rendered component:

```tsx
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('has no accessibility violations', async () => {
  const { container } = render(<LoginForm />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Run this on every major component. It catches missing labels, poor contrast ratios, invalid ARIA attributes, and more.

### Role-Based Queries as Implicit A11y Tests

Every time you use `getByRole`, you are implicitly asserting accessibility. If `getByRole('button', { name: /submit/i })` fails, your component has an accessibility problem — the element is either not a button or it lacks an accessible name.

```tsx
// This test ALSO verifies:
// - The form has proper label associations
// - The button is a real button (not a div with onClick)
// - The heading uses proper semantic HTML
it('renders accessible form', () => {
  render(<ContactForm />);

  expect(screen.getByRole('heading', { name: /contact us/i })).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /your name/i })).toBeInTheDocument();
  expect(screen.getByRole('textbox', { name: /message/i })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
});
```

---

## Test Organization

### Describe Blocks and Naming Conventions

Structure tests around user-facing behaviors, not component internals:

```tsx
describe('TransferForm', () => {
  // Group by feature or user story
  describe('validation', () => {
    it('requires a recipient', async () => { /* ... */ });
    it('requires a positive amount', async () => { /* ... */ });
    it('rejects amounts exceeding balance', async () => { /* ... */ });
  });

  describe('submission', () => {
    it('submits valid transfer and shows confirmation', async () => { /* ... */ });
    it('shows error when transfer fails', async () => { /* ... */ });
    it('prevents double submission', async () => { /* ... */ });
  });

  describe('accessibility', () => {
    it('has no axe violations', async () => { /* ... */ });
    it('supports keyboard-only submission', async () => { /* ... */ });
  });
});
```

**Naming convention**: Test names should read as sentences. `it('shows error when transfer fails')` is clear. `it('error state')` is not.

---

## Common Interview Questions

### 1. "What is the difference between `getBy`, `queryBy`, and `findBy`?"

| Variant | Returns | When Element Missing | Async |
|---------|---------|---------------------|-------|
| `getBy` | Element | Throws error | No |
| `queryBy` | Element \| `null` | Returns `null` | No |
| `findBy` | Promise\<Element\> | Rejects after timeout | Yes |

- Use `getBy` when the element should be there right now.
- Use `queryBy` when you are asserting the element is NOT there: `expect(screen.queryByText(/error/i)).not.toBeInTheDocument()`.
- Use `findBy` when the element appears asynchronously.

### 2. "When would you use `fireEvent` over `userEvent`?"

Almost never. `userEvent` should be your default because it simulates realistic user interactions. The only edge case for `fireEvent` is when you need to dispatch a specific event that `userEvent` does not support, like a custom event, `scroll`, or `resize`:

```tsx
fireEvent.scroll(container, { target: { scrollTop: 500 } });
fireEvent(element, new CustomEvent('my-event', { detail: { key: 'val' } }));
```

### 3. "How do you test a component that uses `useContext`?"

Wrap it in the provider during render. The custom render wrapper pattern handles this automatically. For one-off cases:

```tsx
render(
  <ThemeContext.Provider value={{ theme: 'dark', toggleTheme: vi.fn() }}>
    <ThemeToggle />
  </ThemeContext.Provider>
);
```

### 4. "How do you handle the 'not wrapped in act' warning?"

The warning means a state update happened outside of React's test utilities. Solutions in order of preference:

1. **Await the user event** — you may have forgotten `await`.
2. **Use `findBy` or `waitFor`** — the update is async and you need to wait for it.
3. **Wrap timer advancement in `act()`** — if you are using fake timers.
4. **Check for missing cleanup** — an effect may be updating state after unmount.

### 5. "Why MSW over mocking `fetch` or `axios` directly?"

- **MSW tests the real request pipeline.** Your interceptors, request transforms, and error handling all run. Mocking `fetch` skips all of that.
- **MSW is library-agnostic.** Switch from `fetch` to `axios` and your tests still pass.
- **MSW handlers are reusable** across tests and even in development (browser service worker).
- **MSW gives you error handling coverage.** You can simulate network errors, timeouts, and specific HTTP status codes easily.

### 6. "How do you test a custom hook?"

Use `renderHook` from `@testing-library/react`:

```tsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from '@/hooks/useCounter';

it('increments and decrements', () => {
  const { result } = renderHook(() => useCounter(0));

  expect(result.current.count).toBe(0);

  act(() => result.current.increment());
  expect(result.current.count).toBe(1);

  act(() => result.current.decrement());
  expect(result.current.count).toBe(0);
});
```

But prefer testing hooks through a component when possible.

### 7. "How do you avoid flaky async tests?"

1. **Never use arbitrary timeouts** (`setTimeout` in tests, hardcoded `waitFor` timeouts).
2. **Wait for specific DOM changes**, not time: `await screen.findByText(...)`.
3. **Use `waitForElementToBeRemoved`** for loading spinners instead of checking absence immediately.
4. **Ensure proper MSW handler setup** — unhandled requests cause hanging tests.
5. **Reset state between tests** — `server.resetHandlers()`, clearing query caches, resetting mocks.

```tsx
// FLAKY: race condition
expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();

// SOLID: explicitly wait for removal
await waitForElementToBeRemoved(() => screen.queryByText(/loading/i));
```
