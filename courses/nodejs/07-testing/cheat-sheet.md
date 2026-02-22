# Module 07: Testing — Cheat Sheet

> Quick reference for testing patterns, commands, and templates.

---

## Vitest vs Jest

| | Vitest | Jest |
|---|--------|------|
| Config file | `vitest.config.ts` | `jest.config.ts` (needs ts-node) |
| TypeScript | Native | ts-jest or @swc/jest |
| ESM | Native | Experimental (`--experimental-vm-modules`) |
| Mock syntax | `vi.mock()`, `vi.fn()`, `vi.spyOn()` | `jest.mock()`, `jest.fn()`, `jest.spyOn()` |
| Fake timers | `vi.useFakeTimers()` | `jest.useFakeTimers()` |
| Inline snapshots | `toMatchInlineSnapshot()` | `toMatchInlineSnapshot()` |
| In-source testing | `import.meta.vitest` | Not available |
| Watch mode | Module-graph-aware | File-based |
| Pool options | `threads`, `forks`, `vmThreads` | `--workerThreads` (limited) |
| Run command | `vitest` / `vitest run` | `jest` / `jest --runInBand` |
| Coverage | `--coverage` (v8 or istanbul) | `--coverage` (istanbul or v8) |

---

## Supertest Patterns

```typescript
// GET with query params
await request(app).get('/users').query({ page: 2, limit: 10 }).expect(200);

// POST with JSON body
await request(app).post('/users').send({ name: 'Alice' }).expect(201);

// Auth header
await request(app).get('/me').set('Authorization', `Bearer ${token}`).expect(200);

// File upload
await request(app).post('/upload').attach('file', buffer, 'test.png').expect(200);

// Custom header
await request(app).get('/data').set('X-API-Key', 'key-123').expect(200);

// Expect response shape
const res = await request(app).get('/users/1');
expect(res.body).toMatchObject({ id: '1', name: expect.any(String) });

// Expect error
await request(app).get('/users/999').expect(404);
await request(app).post('/users').send({}).expect(422);

// Streaming / buffer
await request(app).get('/export').buffer(true).expect(200);
```

---

## MSW Handler Templates

```typescript
import { http, HttpResponse, delay } from 'msw';

// Basic GET
http.get('https://api.example.com/resource/:id', ({ params }) => {
  return HttpResponse.json({ id: params.id, name: 'Test' });
});

// POST with body inspection
http.post('https://api.example.com/resource', async ({ request }) => {
  const body = await request.json();
  return HttpResponse.json({ id: 'new-1', ...body }, { status: 201 });
});

// Error response
http.get('https://api.example.com/fail', () => {
  return HttpResponse.json({ error: 'Not found' }, { status: 404 });
});

// Network error
http.get('https://api.example.com/crash', () => {
  return HttpResponse.error();
});

// Delayed response
http.get('https://api.example.com/slow', async () => {
  await delay(3000);
  return HttpResponse.json({ data: 'late' });
});

// Conditional response
http.get('https://api.example.com/items', ({ request }) => {
  const url = new URL(request.url);
  const page = url.searchParams.get('page') ?? '1';
  return HttpResponse.json({ data: [], page: Number(page) });
});
```

**Server lifecycle:**

```typescript
import { setupServer } from 'msw/node';
const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());   // reset per-test overrides
afterAll(() => server.close());

// Per-test override
server.use(http.get('https://api.example.com/resource/:id', () => {
  return HttpResponse.json({ error: 'Down' }, { status: 503 });
}));
```

---

## Test Containers Setup

```typescript
// global-setup.ts
import { PostgreSqlContainer } from '@testcontainers/postgresql';

let container;

export async function setup() {
  container = await new PostgreSqlContainer('postgres:16')
    .withDatabase('test')
    .withUsername('test')
    .withPassword('test')
    .start();
  process.env.DATABASE_URL = container.getConnectionUri();
  // Run migrations here
}

export async function teardown() {
  await container.stop();
}
```

**vitest.config.ts:**

```typescript
export default defineConfig({
  test: {
    globalSetup: ['./test/global-setup.ts'],
    pool: 'forks',       // better isolation for DB
    hookTimeout: 30_000,  // containers can be slow
  },
});
```

**Other containers:**

```typescript
import { RedisContainer } from '@testcontainers/redis';
import { KafkaContainer } from '@testcontainers/kafka';
import { MongoDBContainer } from '@testcontainers/mongodb';
```

---

## Factory Template

```typescript
import { Factory } from 'fishery';
import { faker } from '@faker-js/faker';

// Basic factory
export const userFactory = Factory.define<User>(({ sequence }) => ({
  id: `user-${sequence}`,
  name: faker.person.fullName(),
  email: faker.internet.email(),
  role: 'viewer',
  createdAt: new Date(),
}));

// Usage
userFactory.build();                          // single
userFactory.build({ role: 'admin' });         // with override
userFactory.buildList(5);                     // multiple
userFactory.build({}, { transient: { verified: true } }); // with transient

// Persisting factory (inserts into DB)
export const userFactory = Factory.define<User>(({ sequence, onCreate }) => {
  onCreate(async (user) => {
    const [created] = await db.insert(users).values(user).returning();
    return created;
  });

  return {
    id: `user-${sequence}`,
    name: faker.person.fullName(),
    email: faker.internet.email(),
    role: 'viewer',
    createdAt: new Date(),
  };
});

await userFactory.create();           // inserts into DB
await userFactory.createList(10);     // batch insert
```

---

## Mocking Patterns

| Pattern | Syntax | Best For |
|---------|--------|----------|
| Module mock | `vi.mock('./module')` | Replacing entire modules |
| Auto mock | `vi.mock('./module', () => ({ fn: vi.fn() }))` | Controlling return values |
| Spy | `vi.spyOn(obj, 'method')` | Observing without replacing |
| Stub return | `vi.fn().mockReturnValue(42)` | Sync functions |
| Stub resolve | `vi.fn().mockResolvedValue(data)` | Async functions |
| Stub reject | `vi.fn().mockRejectedValue(err)` | Error paths |
| Stub sequence | `vi.fn().mockResolvedValueOnce(a).mockResolvedValueOnce(b)` | Retry logic |
| Clear mock | `vi.clearAllMocks()` | Reset call history |
| Restore mock | `vi.restoreAllMocks()` | Restore original impl |
| Fake timers | `vi.useFakeTimers()` / `vi.useRealTimers()` | Timers, dates |
| Advance timers | `vi.advanceTimersByTime(ms)` | Testing delays |

---

## Test Naming Conventions

```
Pattern: [subject] [scenario] [expected result]

GET /users returns 401 when no auth token is provided
createOrder throws InsufficientStockError when item is out of stock
retryWithBackoff retries 3 times then rejects
calculateTax applies state tax rate for US addresses
WebSocket connection closes with 4001 when token expires
```

**describe blocks:**

```typescript
describe('OrderService', () => {
  describe('createOrder', () => {
    test('persists order with line items', ...);
    test('throws when inventory is insufficient', ...);
    test('emits OrderCreated event', ...);
  });

  describe('cancelOrder', () => {
    test('sets status to cancelled', ...);
    test('throws when order is already shipped', ...);
    test('refunds payment', ...);
  });
});
```

**File naming:**

```
*.test.ts    — Vitest/Jest convention
*.spec.ts    — Also common, pick one and be consistent
*.e2e.ts     — E2E tests (separate test config)
*.pact.ts    — Contract tests
```

---

## Quick Commands

```bash
# Run all tests
vitest run

# Watch mode
vitest

# Single file
vitest run src/routes/users.test.ts

# Pattern match
vitest run --grep "createOrder"

# Coverage
vitest run --coverage

# Update snapshots
vitest run --update

# Run in sequence (debug flaky tests)
vitest run --pool=forks --poolOptions.forks.singleFork

# Type check
vitest typecheck

# UI mode
vitest --ui
```
