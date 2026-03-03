# 01 – Vitest and Unit Testing

## Testing Philosophy for Node.js Backends

### The Integration-Heavy Approach

The testing pyramid is dead for backend services. What you want is a **testing trophy** (Kent C. Dodds) or, more practically, an **integration-heavy diamond**:

```
        /  E2E  \          ← Few, slow, high confidence
       /----------\
      / Integration \      ← Most of your tests live here
     /----------------\
    /   Unit (pure fn)  \  ← Only for complex logic
   /---------------------\
  /   Static Analysis     \  ← TypeScript, ESLint, Prettier
 /-------------------------\
```

**Why integration-heavy for backends?**

- Backend code is mostly glue: route -> validate -> query -> transform -> respond
- Unit testing glue code tests implementation, not behavior
- Integration tests catch the real bugs: wrong SQL, missing auth checks, broken serialization
- Mocking your database in unit tests gives you false confidence

**The golden rule:** Test behavior, not implementation. If you refactor internals and tests break, those tests were testing the wrong thing.

```typescript
// BAD: Testing implementation
test('calls userRepository.findById', async () => {
  const mockRepo = { findById: vi.fn().mockResolvedValue(user) };
  const service = new UserService(mockRepo);
  await service.getUser('123');
  expect(mockRepo.findById).toHaveBeenCalledWith('123');
});

// GOOD: Testing behavior
test('GET /users/123 returns the user', async () => {
  await db.insert(users).values({ id: '123', name: 'Alice' });
  const res = await request(app).get('/users/123');
  expect(res.status).toBe(200);
  expect(res.body.name).toBe('Alice');
});
```

### What to Test Where

| Layer | Test Type | What You're Verifying |
|-------|-----------|----------------------|
| Route handlers | Integration (supertest) | Status codes, response shape, auth, validation |
| Business logic | Unit (if complex) | Calculations, state machines, algorithms |
| Database queries | Integration (real DB) | Correct SQL, migrations, constraints |
| External APIs | Integration (MSW) | Request/response handling, error paths |
| Full workflows | E2E | Multi-step user journeys, race conditions |

---

## Vitest

### Why Vitest Over Jest

This is a common interview question. Know the specifics:

| Feature | Jest | Vitest |
|---------|------|--------|
| ESM support | Experimental, buggy | Native, first-class |
| TypeScript | Needs ts-jest or @swc/jest | Native via Vite's transform |
| Speed | Slower cold starts | Vite's HMR-based re-runs |
| Config | `jest.config.ts` (needs ts-node) | `vitest.config.ts` (just works) |
| Watch mode | File-based | Module graph-aware (only re-runs affected tests) |
| In-source testing | No | Yes (`import.meta.vitest`) |
| Compatibility | De facto standard | Jest-compatible API (drop-in for most cases) |
| Snapshot | Built-in | Built-in + inline snapshots |
| Concurrent | `test.concurrent` (limited) | `describe.concurrent` (full suite-level) |
| Pool options | `--workerThreads` (limited) | `threads`, `forks`, `vmThreads` |
| Run command | `jest` / `jest --runInBand` | `vitest` / `vitest run` |
| Coverage | `--coverage` (istanbul or v8) | `--coverage` (v8 or istanbul) |

**When to still use Jest:** Legacy codebases, React Native (Vitest support is immature), teams with heavy Jest plugin investment.

### Vitest Configuration for Backend

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.spec.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'html'],
      exclude: [
        'node_modules/',
        'src/**/*.d.ts',
        'src/**/index.ts',       // barrel files
        'src/**/*.test.ts',
        'src/migrations/**',
      ],
      thresholds: {
        statements: 80,
        branches: 75,
        functions: 80,
        lines: 80,
      },
    },
    pool: 'forks',              // better isolation than 'threads' for DB tests
    poolOptions: {
      forks: {
        singleFork: false,      // true for shared DB state
      },
    },
    setupFiles: ['./test/setup.ts'],
    globalSetup: ['./test/global-setup.ts'],
    testTimeout: 10_000,
    hookTimeout: 30_000,        // DB setup can be slow
  },
});
```

### Quick Commands

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

### In-Source Testing

A Vitest exclusive. Useful for pure utility functions:

```typescript
// src/utils/slugify.ts
export function slugify(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

if (import.meta.vitest) {
  const { describe, test, expect } = import.meta.vitest;

  describe('slugify', () => {
    test('converts spaces to hyphens', () => {
      expect(slugify('hello world')).toBe('hello-world');
    });

    test('strips leading/trailing hyphens', () => {
      expect(slugify('--hello--')).toBe('hello');
    });
  });
}
```

Tree-shaken out of production builds. Only use for small, pure functions.

---

## Mocking Strategies

### When NOT to Mock

This is the most important section. Over-mocking is the #1 testing antipattern in Node.js:

- **Do not mock the database** in integration tests. Use a real one.
- **Do not mock your own modules** unless you have a specific reason (circular dependency, extreme slowness).
- **Do not mock `Date.now()`** when you can inject a clock.
- **Do not mock filesystem** when you can use `tmp` directories.

### vi.mock (Module Mocking)

```typescript
// Hoist the mock (Vitest auto-hoists vi.mock calls)
vi.mock('../../src/services/email', () => ({
  sendEmail: vi.fn().mockResolvedValue({ messageId: 'mock-123' }),
}));

import { sendEmail } from '../../src/services/email';

test('sends welcome email on signup', async () => {
  await request(app)
    .post('/users')
    .send({ name: 'Alice', email: 'alice@test.com' })
    .expect(201);

  expect(sendEmail).toHaveBeenCalledWith(
    expect.objectContaining({
      to: 'alice@test.com',
      template: 'welcome',
    })
  );
});
```

### Dependency Injection (Preferred)

```typescript
// src/services/user-service.ts
export function createUserService(deps: {
  db: Database;
  emailClient: EmailClient;
  logger: Logger;
}) {
  return {
    async createUser(data: CreateUserInput) {
      const user = await deps.db.insert(users).values(data).returning();
      await deps.emailClient.send({ to: data.email, template: 'welcome' });
      deps.logger.info('User created', { userId: user.id });
      return user;
    },
  };
}

// In test — inject fakes, no vi.mock needed
test('createUser sends welcome email', async () => {
  const emailClient = { send: vi.fn() };
  const service = createUserService({
    db: testDb,
    emailClient,
    logger: noopLogger,
  });

  await service.createUser({ name: 'Alice', email: 'alice@test.com' });
  expect(emailClient.send).toHaveBeenCalledOnce();
});
```

### Mocking Patterns Reference

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

| Pattern | When to Use | Trade-offs |
|---------|-------------|------------|
| `vi.mock` | Third-party modules, singletons | Couples to module structure |
| DI | Your own services | Requires DI-friendly architecture |
| MSW | External HTTP APIs | Best network-level fidelity |
| Spy (`vi.spyOn`) | Observing calls without replacing | Runs real code |
| Test doubles (manual) | Complex interfaces | More code, more control |
| Fake implementations | Repositories, caches | Maintenance cost |

---

## Testing Async Code

### Streams

```typescript
import { Readable, pipeline } from 'node:stream';

test('transforms CSV stream correctly', async () => {
  const input = Readable.from([
    'name,age\n',
    'Alice,30\n',
    'Bob,25\n',
  ]);

  const rows: Record<string, string>[] = [];
  const transform = createCsvParser(); // your transform stream

  await new Promise<void>((resolve, reject) => {
    pipeline(input, transform, new Writable({
      objectMode: true,
      write(row, _enc, cb) {
        rows.push(row);
        cb();
      },
      final(cb) {
        resolve();
        cb();
      },
    }), (err) => { if (err) reject(err); });
  });

  expect(rows).toEqual([
    { name: 'Alice', age: '30' },
    { name: 'Bob', age: '25' },
  ]);
});
```

### Events

```typescript
import { EventEmitter, once } from 'node:events';

test('emits "processed" after handling message', async () => {
  const processor = new MessageProcessor();
  const eventPromise = once(processor, 'processed');

  processor.handle({ type: 'order', data: { id: '123' } });

  const [result] = await eventPromise;
  expect(result.orderId).toBe('123');
});
```

### Timers

```typescript
test('retries with exponential backoff', async () => {
  vi.useFakeTimers();
  const fetchMock = vi.fn()
    .mockRejectedValueOnce(new Error('fail'))
    .mockRejectedValueOnce(new Error('fail'))
    .mockResolvedValue({ data: 'ok' });

  const promise = retryWithBackoff(fetchMock, { maxRetries: 3 });

  await vi.advanceTimersByTimeAsync(1000);  // 1st retry at 1s
  await vi.advanceTimersByTimeAsync(2000);  // 2nd retry at 2s

  const result = await promise;
  expect(result).toEqual({ data: 'ok' });
  expect(fetchMock).toHaveBeenCalledTimes(3);

  vi.useRealTimers();
});
```

### WebSockets

```typescript
import { WebSocket, WebSocketServer } from 'ws';

test('broadcasts messages to all clients', async () => {
  const wss = new WebSocketServer({ port: 0 });
  const port = (wss.address() as AddressInfo).port;

  const client1 = new WebSocket(`ws://localhost:${port}`);
  const client2 = new WebSocket(`ws://localhost:${port}`);

  await Promise.all([
    once(client1, 'open'),
    once(client2, 'open'),
  ]);

  const msg1Promise = once(client1, 'message');
  const msg2Promise = once(client2, 'message');

  wss.clients.forEach((c) => c.send('hello'));

  const [[msg1], [msg2]] = await Promise.all([msg1Promise, msg2Promise]);
  expect(msg1.toString()).toBe('hello');
  expect(msg2.toString()).toBe('hello');

  client1.close();
  client2.close();
  wss.close();
});
```

---

## Snapshot Testing

### When Snapshots Work

Snapshot testing is useful for *detecting change*, not for *verifying correctness*. For APIs, use them as a change detection alarm on response schemas:

```typescript
test('GET /api/v1/products response shape', async () => {
  const res = await request(app)
    .get('/api/v1/products')
    .set(authHeader());

  // Snapshot the SHAPE, not the data
  expect(sanitizeResponse(res.body)).toMatchSnapshot();
});

function sanitizeResponse(body: any) {
  return JSON.parse(
    JSON.stringify(body, (key, value) => {
      if (key === 'id') return '[ID]';
      if (key === 'createdAt' || key === 'updatedAt') return '[TIMESTAMP]';
      if (typeof value === 'number') return '[NUMBER]';
      return value;
    })
  );
}
```

### When Snapshots Fail You

- **Large snapshots** that nobody reads during review
- **Volatile data** (timestamps, IDs) that forces constant updates
- **Team pressure** to just run `--updateSnapshot` without reviewing changes

**Better alternative:** Explicit schema validation with Zod:

```typescript
import { z } from 'zod';

const ProductListResponse = z.object({
  data: z.array(z.object({
    id: z.string().uuid(),
    name: z.string(),
    price: z.number().positive(),
  })),
  meta: z.object({
    total: z.number(),
    page: z.number(),
  }),
});

test('GET /products matches expected schema', async () => {
  const res = await request(app).get('/products').set(authHeader());
  expect(() => ProductListResponse.parse(res.body)).not.toThrow();
});
```

---

## Test Data Management

### Factories with Fishery

```typescript
// test/factories/user.ts
import { Factory } from 'fishery';
import { faker } from '@faker-js/faker';
import type { User } from '../../src/types';

export const userFactory = Factory.define<User>(({ sequence }) => ({
  id: `user-${sequence}`,
  name: faker.person.fullName(),
  email: faker.internet.email(),
  role: 'viewer',
  createdAt: new Date(),
  updatedAt: new Date(),
}));

// Usage
const admin = userFactory.build({ role: 'admin' });
const users = userFactory.buildList(10);

// Traits via transient params
export const userFactory = Factory.define<User>(({ sequence, transientParams }) => ({
  id: `user-${sequence}`,
  name: faker.person.fullName(),
  email: faker.internet.email(),
  role: transientParams.isAdmin ? 'admin' : 'viewer',
  createdAt: new Date(),
  updatedAt: new Date(),
}));

const admin = userFactory.build({}, { transient: { isAdmin: true } });

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

### Builder Pattern

For complex objects with many optional fields:

```typescript
class UserBuilder {
  private data: Partial<User> = {};

  withRole(role: string) { this.data.role = role; return this; }
  withEmail(email: string) { this.data.email = email; return this; }
  verified() { this.data.emailVerified = true; return this; }

  build(): User {
    return {
      id: this.data.id ?? randomUUID(),
      name: this.data.name ?? 'Test User',
      email: this.data.email ?? 'test@example.com',
      role: this.data.role ?? 'viewer',
      emailVerified: this.data.emailVerified ?? false,
      createdAt: this.data.createdAt ?? new Date(),
      updatedAt: this.data.updatedAt ?? new Date(),
    };
  }
}

// Usage
const user = new UserBuilder().withRole('admin').verified().build();
```

---

## Test Organization and Naming

### File Structure

```
src/
  routes/
    users.ts
    users.test.ts          ← co-located unit/integration tests
  services/
    billing.ts
    billing.test.ts
test/
  e2e/                     ← E2E tests (separate from src)
    order-flow.test.ts
  contracts/                ← Contract tests
    payment.pact.ts
  helpers/                  ← Shared test utilities
    create-app.ts
    auth.ts
    db.ts
  factories/                ← Test data factories
    user.ts
    order.ts
  mocks/                    ← MSW handlers
    handlers.ts
    server.ts
  fixtures/                 ← Static test data (JSON, files)
    sample-upload.csv
  setup.ts                  ← beforeAll/afterAll hooks
  global-setup.ts           ← Container setup
```

### Test Naming Conventions

Use the pattern: `[unit under test] [scenario] [expected result]`

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

## Coverage Strategy

Coverage is a **lagging indicator**, not a goal. High coverage with bad tests is worse than moderate coverage with good tests.

### Pragmatic Thresholds

| Metric | Recommended | Why |
|--------|-------------|-----|
| Statements | 80% | Catches untested code paths |
| Branches | 75% | Error paths are often missed |
| Functions | 80% | Exported functions should be tested |
| Lines | 80% | Correlates with statement coverage |

### What to Exclude from Coverage

- Generated code (Prisma client, GraphQL codegen)
- Migration files
- Barrel files (`index.ts` re-exports)
- Type-only files (`.d.ts`)
- Configuration files
- Test files themselves

### When Coverage Lies

```typescript
// 100% coverage, 0% confidence
test('GET /users returns 200', async () => {
  const res = await request(app).get('/users');
  expect(res.status).toBe(200);
  // Never checks the response body, pagination, auth, error cases
});
```

Coverage tells you what code runs. Mutation testing (see Module 03) tells you if your assertions would catch a real bug.

## Related Reading

- **Testing philosophy and the integration-heavy approach** connects directly to how you design REST APIs — see [03 – HTTP Semantics and Status Codes](../03-rest-api-design/01-http-semantics-and-status-codes.md) for the endpoints you will be testing and which status codes to assert against.
- **Vitest configuration and pool options** are relevant when running database integration tests — see [06 – Prisma and Drizzle](../06-database-patterns/01-prisma-and-drizzle.md#drizzle-orm) for the ORMs whose queries you will be testing with `pool: 'forks'`.
- **Mocking strategies and dependency injection** align with the DI patterns in [09 – Clean Architecture and DDD](../09-architecture-patterns/01-clean-architecture-and-ddd.md#dependency-injection), where the composition root makes mocking trivial.
- **Testing async code (streams, events, timers)** relies on the runtime concepts covered in [02 – Event Loop and Task Queues](../02-node-runtime/01-event-loop-and-task-queues.md) and [02 – Memory, Streams, and Runtime Internals](../02-node-runtime/03-memory-streams-and-runtime-internals.md#streams-and-backpressure).
- **Snapshot testing with Zod schema validation** uses the same validation approach covered in [03 – Pagination, Filtering, and Bulk Operations](../03-rest-api-design/02-pagination-filtering-and-bulk-operations.md#input-validation-with-zod) and [05 – Session Management and Validation](../05-auth-security/02-session-management-and-validation.md#input-validation-with-zod).
- **Test data factories with Fishery** relate to the factory patterns discussed in [06 – Queries, Transactions, and Optimization](../06-database-patterns/02-queries-transactions-and-optimization.md#seeding-and-factory-patterns).
- **TypeScript fundamentals** like generics and type narrowing that appear in test utilities are covered in [00 – TypeScript and Node.js Fundamentals](../00-ts-node-fundamentals.md#typescript-essentials) and [01 – Conditional and Mapped Types](../01-typescript-advanced/01-conditional-and-mapped-types.md).
