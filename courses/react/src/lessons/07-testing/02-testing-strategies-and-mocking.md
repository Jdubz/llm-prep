# Testing Strategies and Mocking

Advanced testing topics: hook testing, E2E, visual regression, performance testing, server components, and real-time features.

## Table of Contents

1. [Testing Hooks in Isolation](#testing-hooks-in-isolation)
2. [E2E with Playwright](#e2e-with-playwright)
3. [Visual Regression Testing](#visual-regression-testing)
4. [Testing Performance](#testing-performance)
5. [Testing Server Components](#testing-server-components)
6. [Component Testing with Storybook](#component-testing-with-storybook)
7. [Test Coverage Strategy](#test-coverage-strategy)
8. [Testing Real-Time Features](#testing-real-time-features)

---

## Testing Hooks in Isolation

### `renderHook` Fundamentals

`renderHook` is for hooks that encapsulate reusable logic consumed by multiple components. If a hook is only used in one place, test the component instead.

```tsx
import { renderHook, act, waitFor } from '@testing-library/react';

describe('useDebounce', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('returns debounced value after delay', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'hello', delay: 300 } }
    );

    expect(result.current).toBe('hello');

    // Update the value
    rerender({ value: 'hello world', delay: 300 });

    // Value has not changed yet
    expect(result.current).toBe('hello');

    // Advance past debounce delay
    act(() => vi.advanceTimersByTime(300));

    expect(result.current).toBe('hello world');
  });

  it('resets timer when value changes within delay', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'a' } }
    );

    rerender({ value: 'ab' });
    act(() => vi.advanceTimersByTime(200));

    rerender({ value: 'abc' });
    act(() => vi.advanceTimersByTime(200));

    // Still 'a' — timer reset on each change
    expect(result.current).toBe('a');

    act(() => vi.advanceTimersByTime(100));
    expect(result.current).toBe('abc');
  });
});
```

### Testing Async Hooks

Hooks that perform data fetching need providers and async patterns:

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUser } from '@/hooks/useUser';
import type { ReactNode } from 'react';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe('useUser', () => {
  it('fetches and returns user data', async () => {
    const { result } = renderHook(() => useUser('1'), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toEqual({
      id: '1',
      name: 'Alice',
      email: 'alice@test.com',
    });
  });

  it('returns error on failure', async () => {
    server.use(
      http.get('/api/users/:id', () =>
        HttpResponse.json({ message: 'Not Found' }, { status: 404 })
      )
    );

    const { result } = renderHook(() => useUser('999'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toMatch(/not found/i);
  });
});
```

### Testing Hooks with Reducers

```tsx
describe('useTaskManager', () => {
  it('supports the full task lifecycle', () => {
    const { result } = renderHook(() => useTaskManager());

    // Add task
    act(() => result.current.addTask('Write tests'));
    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0]).toMatchObject({
      title: 'Write tests',
      status: 'pending',
    });

    const taskId = result.current.tasks[0].id;

    // Complete task
    act(() => result.current.completeTask(taskId));
    expect(result.current.tasks[0].status).toBe('completed');

    // Filter
    act(() => result.current.addTask('Another task'));
    expect(result.current.pendingTasks).toHaveLength(1);
    expect(result.current.completedTasks).toHaveLength(1);

    // Remove task
    act(() => result.current.removeTask(taskId));
    expect(result.current.tasks).toHaveLength(1);
  });
});
```

---

## E2E with Playwright

### Page Object Model

Page objects encapsulate page-specific selectors and actions. They make E2E tests readable and maintainable:

```tsx
// e2e/pages/LoginPage.ts
import { type Page, type Locator } from '@playwright/test';

export class LoginPage {
  private readonly emailInput: Locator;
  private readonly passwordInput: Locator;
  private readonly submitButton: Locator;
  private readonly errorAlert: Locator;

  constructor(private readonly page: Page) {
    this.emailInput = page.getByRole('textbox', { name: /email/i });
    this.passwordInput = page.getByLabel(/password/i);
    this.submitButton = page.getByRole('button', { name: /sign in/i });
    this.errorAlert = page.getByRole('alert');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }

  async expectError(message: string | RegExp) {
    await expect(this.errorAlert).toContainText(message);
  }

  async expectRedirectTo(path: string) {
    await expect(this.page).toHaveURL(new RegExp(path));
  }
}
```

```tsx
// e2e/tests/login.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

test.describe('Login', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('successful login redirects to dashboard', async () => {
    await loginPage.login('admin@test.com', 'password123');
    await loginPage.expectRedirectTo('/dashboard');
  });

  test('invalid credentials show error', async () => {
    await loginPage.login('admin@test.com', 'wrong');
    await loginPage.expectError(/invalid credentials/i);
  });
});
```

### Fixtures

Playwright fixtures let you compose reusable test setup. They replace `beforeEach` boilerplate:

```tsx
// e2e/fixtures.ts
import { test as base, expect } from '@playwright/test';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';

type Fixtures = {
  loginPage: LoginPage;
  dashboardPage: DashboardPage;
  authenticatedPage: DashboardPage;
};

export const test = base.extend<Fixtures>({
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await use(loginPage);
  },

  dashboardPage: async ({ page }, use) => {
    await use(new DashboardPage(page));
  },

  authenticatedPage: async ({ page, dashboardPage }, use) => {
    // Set auth state directly via storage state or API
    await page.goto('/login');
    await page.getByRole('textbox', { name: /email/i }).fill('admin@test.com');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL('/dashboard');
    await use(dashboardPage);
  },
});

export { expect };
```

### Network Interception

Playwright can intercept and mock network requests at the E2E level:

```tsx
test('shows empty state when no data', async ({ page }) => {
  await page.route('/api/users', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.goto('/users');
  await expect(page.getByText(/no users found/i)).toBeVisible();
});

test('handles network failure gracefully', async ({ page }) => {
  await page.route('/api/users', (route) => route.abort('failed'));
  await page.goto('/users');
  await expect(page.getByRole('alert')).toContainText(/network error/i);
});
```

### Visual Comparison

```tsx
test('dashboard matches visual snapshot', async ({ page }) => {
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');

  // Full page screenshot comparison
  await expect(page).toHaveScreenshot('dashboard.png', {
    maxDiffPixelRatio: 0.01,
  });

  // Component-level screenshot
  const chart = page.getByTestId('revenue-chart');
  await expect(chart).toHaveScreenshot('revenue-chart.png');
});
```

---

## Visual Regression Testing

### Chromatic / Percy Integration

Both services take snapshots of your Storybook stories and compare them against baselines. The workflow:

1. Write stories for every visual state of a component.
2. CI pushes snapshots to the service on every PR.
3. Reviewers approve or reject visual changes in the service's UI.

```tsx
// Button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  component: Button,
  argTypes: {
    variant: { control: 'select', options: ['primary', 'secondary', 'danger'] },
    size: { control: 'select', options: ['sm', 'md', 'lg'] },
  },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = { args: { variant: 'primary', children: 'Click me' } };
export const Secondary: Story = { args: { variant: 'secondary', children: 'Click me' } };
export const Danger: Story = { args: { variant: 'danger', children: 'Delete' } };
export const Disabled: Story = { args: { variant: 'primary', children: 'Submit', disabled: true } };
export const Loading: Story = { args: { variant: 'primary', children: 'Saving...', isLoading: true } };
```

Key considerations:
- **Deterministic rendering**: Mock dates, randomness, and animations. Non-deterministic content causes false positives.
- **Responsive snapshots**: Configure viewports to catch layout breakage across screen sizes.
- **Cost**: Both services charge per snapshot. Be selective. Snapshot leaf components, not full pages with constantly changing data.

---

## Testing Performance

### Render Count Assertions

Verify that optimization techniques (memoization, stable references) actually prevent unnecessary re-renders:

```tsx
import { Profiler, type ProfilerOnRenderCallback } from 'react';

function renderWithProfiler(ui: React.ReactElement) {
  const onRender = vi.fn<Parameters<ProfilerOnRenderCallback>, void>();

  const result = render(
    <Profiler id="test" onRender={onRender}>
      {ui}
    </Profiler>
  );

  return { ...result, onRender };
}

it('does not re-render child when unrelated parent state changes', async () => {
  const user = userEvent.setup();
  const { onRender } = renderWithProfiler(<Dashboard />);

  // Initial render
  expect(onRender).toHaveBeenCalledTimes(1);

  // Click something that changes parent state but should not affect memoized child
  await user.click(screen.getByRole('button', { name: /toggle sidebar/i }));

  // If child is properly memoized, render count stays at 2 (parent re-render only)
  expect(onRender).toHaveBeenCalledTimes(2);
});
```

### Testing Component with `React.memo`

```tsx
it('ExpensiveList does not re-render when onClick identity is stable', async () => {
  const renderSpy = vi.fn();
  const SpiedExpensiveList = (props: ExpensiveListProps) => {
    renderSpy();
    return <ExpensiveList {...props} />;
  };

  const { rerender } = render(
    <SpiedExpensiveList items={items} onClick={stableCallback} />
  );

  renderSpy.mockClear();
  rerender(<SpiedExpensiveList items={items} onClick={stableCallback} />);

  expect(renderSpy).not.toHaveBeenCalled();
});
```

A word of caution: render count assertions are brittle. They test implementation details. Use them sparingly, only for components where performance is a documented requirement (virtualized lists, real-time dashboards).

---

## Testing Server Components

### Current Limitations (React 19 / Next.js 15)

Server Components are functions that run on the server and return JSX. They cannot be rendered in a JSDOM environment because they depend on server-only APIs (database queries, file system, etc.).

**What you can test today:**

1. **Server Component logic in isolation** — extract data transformation into pure functions and unit test those.
2. **Client Components that receive Server Component data** — test the Client Component by passing mock props.
3. **E2E tests** — Playwright renders the full application including Server Components.

```tsx
// Extract testable logic from Server Components
// app/users/page.tsx
export async function getTransformedUsers(): Promise<DisplayUser[]> {
  const users = await db.users.findMany();
  return users.map(transformUser);
}

// This pure function is easily testable
export function transformUser(user: DbUser): DisplayUser {
  return {
    id: user.id,
    displayName: `${user.firstName} ${user.lastName}`,
    initials: `${user.firstName[0]}${user.lastName[0]}`,
    memberSince: formatDistanceToNow(user.createdAt),
  };
}
```

```tsx
// Test the pure transformation logic
describe('transformUser', () => {
  it('formats display name and initials', () => {
    const result = transformUser({
      id: '1',
      firstName: 'Jane',
      lastName: 'Doe',
      createdAt: new Date('2024-01-01'),
    });

    expect(result.displayName).toBe('Jane Doe');
    expect(result.initials).toBe('JD');
    expect(result.memberSince).toMatch(/year/);
  });
});
```

### Testing Server Actions

Server Actions are async functions that run on the server. In unit tests, you can call them directly if you mock their server dependencies:

```tsx
// actions/createUser.ts
'use server';

import { db } from '@/lib/db';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(1),
  email: z.string().email(),
});

export async function createUser(formData: FormData) {
  const parsed = schema.safeParse({
    name: formData.get('name'),
    email: formData.get('email'),
  });

  if (!parsed.success) {
    return { error: parsed.error.flatten().fieldErrors };
  }

  await db.users.create({ data: parsed.data });
  revalidatePath('/users');
  return { success: true };
}
```

```tsx
// Test validation logic (mock the server-only imports)
vi.mock('@/lib/db', () => ({
  db: { users: { create: vi.fn() } },
}));
vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}));

describe('createUser action', () => {
  it('rejects invalid email', async () => {
    const formData = new FormData();
    formData.set('name', 'Alice');
    formData.set('email', 'not-an-email');

    const result = await createUser(formData);
    expect(result.error?.email).toBeDefined();
  });

  it('creates user with valid data', async () => {
    const formData = new FormData();
    formData.set('name', 'Alice');
    formData.set('email', 'alice@example.com');

    const result = await createUser(formData);
    expect(result).toEqual({ success: true });
    expect(db.users.create).toHaveBeenCalledWith({
      data: { name: 'Alice', email: 'alice@example.com' },
    });
  });
});
```

---

## Component Testing with Storybook

### Interaction Tests with `play` Functions

Storybook interaction tests run in the browser, which means they test actual browser behavior — not JSDOM approximations:

```tsx
// TransferForm.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { within, userEvent, waitFor, expect } from '@storybook/test';
import { TransferForm } from './TransferForm';

const meta: Meta<typeof TransferForm> = {
  component: TransferForm,
  decorators: [
    (Story) => (
      <MockProviders>
        <Story />
      </MockProviders>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof TransferForm>;

export const SuccessfulSubmission: Story = {
  play: async ({ canvasElement, step }) => {
    const canvas = within(canvasElement);
    const user = userEvent.setup();

    await step('Fill in the form', async () => {
      await user.type(canvas.getByLabelText(/recipient/i), 'bob@example.com');
      await user.type(canvas.getByLabelText(/amount/i), '50.00');
      await user.selectOptions(canvas.getByLabelText(/currency/i), 'USD');
    });

    await step('Submit and verify', async () => {
      await user.click(canvas.getByRole('button', { name: /send/i }));
      await waitFor(() => {
        expect(canvas.getByRole('alert')).toHaveTextContent(/transfer complete/i);
      });
    });
  },
};

export const ValidationErrors: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const user = userEvent.setup();

    await user.click(canvas.getByRole('button', { name: /send/i }));

    await waitFor(() => {
      expect(canvas.getByText(/recipient is required/i)).toBeInTheDocument();
      expect(canvas.getByText(/amount is required/i)).toBeInTheDocument();
    });
  },
};
```

Storybook interaction tests complement (not replace) your Vitest/Jest tests. They are excellent for visual verification with real browser rendering and for QA documentation.

---

## Test Coverage Strategy

### What to Measure

- **Line/branch/function coverage** gives you a floor, not a ceiling. 80% coverage with thoughtful behavior tests is better than 100% coverage with implementation-detail tests.
- **Track coverage trends**, not absolute numbers. Decreasing coverage on a PR means new code lacks tests.
- **Use coverage to find untested paths**, not to prove quality.

### When 100% Is Wrong

Chasing 100% coverage leads to:

1. **Tautological tests** — testing that React renders what you told it to render.
2. **Brittle tests** — testing implementation details to cover every branch.
3. **Wasted time** — diminishing returns on edge cases that are obvious from code inspection.

```tsx
// This test adds coverage but zero confidence
it('renders div', () => {
  const { container } = render(<Card title="Hi" />);
  expect(container.firstChild).toBeTruthy(); // Useless
});
```

### Mutation Testing

Mutation testing answers the question regular coverage cannot: **would your tests catch a real bug?** Tools like Stryker mutate your source code (change `===` to `!==`, remove conditionals, swap operators) and check if your tests fail. Surviving mutants are blind spots.

```bash
npx stryker run

# Output:
# Mutation score: 78%
# Survived mutants: 12
# Killed mutants: 43
```

Mutation testing is expensive to run. Use it periodically on critical modules, not on every CI build.

---

## Testing Real-Time Features

### WebSocket Mocking

Testing WebSocket components requires either mocking the WebSocket constructor or using a library like `mock-socket`:

```tsx
import { WS } from 'vitest-websocket-mock';

describe('ChatRoom', () => {
  let wsServer: WS;

  beforeEach(async () => {
    wsServer = new WS('ws://localhost:3001/chat');
  });

  afterEach(() => {
    WS.clean();
  });

  it('displays incoming messages', async () => {
    render(<ChatRoom roomId="general" />);
    await wsServer.connected;

    // Server sends a message
    wsServer.send(
      JSON.stringify({
        type: 'message',
        user: 'Alice',
        text: 'Hello everyone!',
        timestamp: Date.now(),
      })
    );

    expect(
      await screen.findByText(/hello everyone/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/alice/i)).toBeInTheDocument();
  });

  it('sends user messages through WebSocket', async () => {
    const user = userEvent.setup();
    render(<ChatRoom roomId="general" />);
    await wsServer.connected;

    await user.type(screen.getByRole('textbox', { name: /message/i }), 'Hi there!');
    await user.click(screen.getByRole('button', { name: /send/i }));

    // Verify the message was sent to the server
    await expect(wsServer).toReceiveMessage(
      JSON.stringify({ type: 'message', text: 'Hi there!' })
    );
  });

  it('shows reconnection state on disconnect', async () => {
    render(<ChatRoom roomId="general" />);
    await wsServer.connected;

    expect(screen.getByText(/connected/i)).toBeInTheDocument();

    wsServer.close();

    expect(await screen.findByText(/reconnecting/i)).toBeInTheDocument();
  });
});
```

### Timer Manipulation

Components with intervals, timeouts, or polling need fake timers:

```tsx
describe('PollingDashboard', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('polls for updates every 30 seconds', async () => {
    let callCount = 0;
    server.use(
      http.get('/api/metrics', () => {
        callCount++;
        return HttpResponse.json({ value: callCount * 10 });
      })
    );

    render(<PollingDashboard interval={30_000} />);

    // Initial fetch
    expect(await screen.findByText('10')).toBeInTheDocument();
    expect(callCount).toBe(1);

    // Advance 30 seconds -> second poll
    await act(() => vi.advanceTimersByTime(30_000));
    expect(await screen.findByText('20')).toBeInTheDocument();
    expect(callCount).toBe(2);

    // Advance another 30 seconds -> third poll
    await act(() => vi.advanceTimersByTime(30_000));
    expect(await screen.findByText('30')).toBeInTheDocument();
    expect(callCount).toBe(3);
  });

  it('stops polling when tab is not visible', async () => {
    let callCount = 0;
    server.use(
      http.get('/api/metrics', () => {
        callCount++;
        return HttpResponse.json({ value: callCount });
      })
    );

    render(<PollingDashboard interval={30_000} />);
    await screen.findByText('1');

    // Simulate tab becoming hidden
    Object.defineProperty(document, 'visibilityState', {
      value: 'hidden',
      writable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));

    // Advance time — should NOT trigger another poll
    await act(() => vi.advanceTimersByTime(60_000));
    expect(callCount).toBe(1);

    // Simulate tab becoming visible again
    Object.defineProperty(document, 'visibilityState', {
      value: 'visible',
      writable: true,
    });
    document.dispatchEvent(new Event('visibilitychange'));

    // Should resume polling
    await act(() => vi.advanceTimersByTime(30_000));
    expect(callCount).toBe(2);
  });
});
```

### Testing Debounced / Throttled Functions

```tsx
describe('SearchInput with debounce', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('debounces API calls while user types', async () => {
    let searchCount = 0;
    server.use(
      http.get('/api/search', ({ request }) => {
        searchCount++;
        const url = new URL(request.url);
        const q = url.searchParams.get('q');
        return HttpResponse.json({ results: [`Result for: ${q}`] });
      })
    );

    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<SearchInput debounceMs={300} />);

    const input = screen.getByRole('searchbox');
    await user.type(input, 'react testing');

    // Still debouncing — no API call yet
    expect(searchCount).toBe(0);

    // Advance past debounce
    await act(() => vi.advanceTimersByTime(300));

    // Only one API call with the final value
    expect(searchCount).toBe(1);
    expect(await screen.findByText(/result for: react testing/i)).toBeInTheDocument();
  });
});
```

Note the `advanceTimers: vi.advanceTimersByTime` option passed to `userEvent.setup()`. This is required when fake timers are active so that `userEvent` can advance time between simulated key presses.

---

## Practice

- **Hook isolation test**: Write a `renderHook` test for `src/hooks/useFetch.js`. Test: (1) returns loading state initially, (2) returns data on success, (3) handles fetch error, (4) aborts previous request on URL change (race condition). Use MSW or `vi.fn()` to mock fetch.
- **E2E with Playwright**: Write a Playwright test for a login flow: navigate to `/login`, fill email and password, submit, assert redirect to dashboard. Use `page.getByRole` queries.
- **Visual regression**: Set up a Storybook story for a `<Button>` component with all variants. Configure Chromatic or Percy to snapshot each variant.
- **Fake timers exercise**: Write a test for a component with a 5-second auto-save feature. Use `vi.useFakeTimers()` and `vi.advanceTimersByTime(5000)`. Verify the save callback fires once after 5 seconds, not before.
- **Debounce test**: Following the "Testing Debounced / Throttled Functions" section, write a test for a search input with 300ms debounce. Verify: (1) no API call during typing, (2) one API call 300ms after last keystroke, (3) correct search term in the request.
- **Server Component testing**: Write a test that renders a server component by mocking its data dependency. Verify the rendered output matches expected content.

### Related Lessons

- [RTL Fundamentals](01-react-testing-library-fundamentals.md) -- React Testing Library queries, MSW setup, form testing, accessibility testing
- [Custom Hooks Testing & Advanced](../02-custom-hooks/02-custom-hooks-testing-and-advanced.md) -- `renderHook` patterns, testing hooks with providers, TanStack Query testing
- [Performance: Rendering & Optimization](../03-performance/01-react-rendering-and-optimization.md) -- understanding re-renders helps write meaningful performance tests
- [RSC & Suspense](../06-rsc-and-suspense/01-server-components-and-suspense.md) -- server component patterns that require special testing strategies
