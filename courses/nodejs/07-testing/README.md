# Module 07: Testing

> **The testing module that treats you like a senior.** You already know how to write tests. This is about knowing *which* tests to write, *where* the ROI is highest, and *how* to defend your testing strategy in an architecture review.

---

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
| In-source testing | No | Yes |
| Compatibility | De facto standard | Jest-compatible API (drop-in for most cases) |
| Snapshot | Built-in | Built-in + inline snapshots |
| Concurrent | `test.concurrent` (limited) | `describe.concurrent` (full suite-level) |

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

## API Testing with Supertest

### Express Integration

```typescript
// test/helpers/create-app.ts
import express from 'express';
import { userRouter } from '../../src/routes/users';
import { errorHandler } from '../../src/middleware/error-handler';

export function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/users', userRouter);
  app.use(errorHandler);
  return app;
}
```

```typescript
// src/routes/users.test.ts
import request from 'supertest';
import { createTestApp } from '../test/helpers/create-app';

const app = createTestApp();

describe('POST /users', () => {
  test('creates a user and returns 201', async () => {
    const res = await request(app)
      .post('/users')
      .send({ name: 'Alice', email: 'alice@example.com' })
      .expect('Content-Type', /json/)
      .expect(201);

    expect(res.body).toMatchObject({
      id: expect.any(String),
      name: 'Alice',
      email: 'alice@example.com',
    });
  });

  test('returns 422 for invalid email', async () => {
    const res = await request(app)
      .post('/users')
      .send({ name: 'Alice', email: 'not-an-email' })
      .expect(422);

    expect(res.body.errors).toContainEqual(
      expect.objectContaining({ field: 'email' })
    );
  });
});
```

### Fastify Integration

Fastify has built-in injection, no supertest needed:

```typescript
import { build } from '../src/app';

describe('GET /users/:id', () => {
  let app: ReturnType<typeof build>;

  beforeAll(async () => {
    app = build();
    await app.ready();
  });

  afterAll(() => app.close());

  test('returns user by id', async () => {
    const res = await app.inject({
      method: 'GET',
      url: '/users/123',
      headers: { authorization: 'Bearer test-token' },
    });

    expect(res.statusCode).toBe(200);
    expect(res.json()).toMatchObject({ id: '123' });
  });
});
```

### Auth Headers

```typescript
// test/helpers/auth.ts
import jwt from 'jsonwebtoken';

export function authHeader(overrides: Partial<TokenPayload> = {}) {
  const payload: TokenPayload = {
    sub: 'user-123',
    role: 'admin',
    ...overrides,
  };
  const token = jwt.sign(payload, process.env.JWT_SECRET!, { expiresIn: '1h' });
  return { Authorization: `Bearer ${token}` };
}

// Usage
const res = await request(app)
  .get('/admin/users')
  .set(authHeader({ role: 'viewer' }))
  .expect(403);
```

### File Uploads

```typescript
test('uploads an avatar', async () => {
  const res = await request(app)
    .post('/users/123/avatar')
    .set(authHeader())
    .attach('avatar', Buffer.from('fake-image'), {
      filename: 'avatar.png',
      contentType: 'image/png',
    })
    .expect(200);

  expect(res.body.avatarUrl).toMatch(/^https:\/\//);
});
```

### Streaming Responses

```typescript
test('streams CSV export', async () => {
  const res = await request(app)
    .get('/reports/export')
    .set(authHeader())
    .expect(200)
    .expect('Content-Type', 'text/csv')
    .buffer(true)
    .parse((res, callback) => {
      let data = '';
      res.on('data', (chunk: Buffer) => { data += chunk.toString(); });
      res.on('end', () => callback(null, data));
    });

  const lines = (res.body as string).split('\n');
  expect(lines[0]).toBe('id,name,email');
  expect(lines.length).toBeGreaterThan(1);
});
```

---

## MSW for Mocking External Services

Mock Service Worker intercepts at the network level. No monkey-patching `fetch` or `axios`.

### Server Setup

```typescript
// test/mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('https://api.stripe.com/v1/customers/:id', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      email: 'customer@example.com',
      subscriptions: { data: [] },
    });
  }),

  http.post('https://api.sendgrid.com/v3/mail/send', async ({ request }) => {
    const body = await request.json();
    if (!body.to) {
      return HttpResponse.json({ error: 'Missing to' }, { status: 400 });
    }
    return HttpResponse.json({ messageId: 'msg-123' }, { status: 202 });
  }),
];
```

```typescript
// test/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

```typescript
// test/setup.ts
import { server } from './mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Per-Test Overrides

```typescript
test('handles Stripe API failure gracefully', async () => {
  server.use(
    http.get('https://api.stripe.com/v1/customers/:id', () => {
      return HttpResponse.json(
        { error: { message: 'Rate limited' } },
        { status: 429 }
      );
    })
  );

  const res = await request(app)
    .get('/billing/customer')
    .set(authHeader())
    .expect(502);

  expect(res.body.message).toBe('Billing service unavailable');
});
```

**Critical interview point:** `onUnhandledRequest: 'error'` is essential. It ensures your tests fail if code makes unexpected network calls. This catches regressions where someone adds a new API call without a corresponding mock.

---

## Database Testing

### Test Containers

The gold standard for database testing. Spins up a real Postgres (or MySQL, etc.) in Docker for your tests.

```typescript
// test/global-setup.ts
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { migrate } from 'drizzle-orm/node-postgres/migrator';
import { drizzle } from 'drizzle-orm/node-postgres';
import pg from 'pg';

let container: StartedPostgreSqlContainer;

export async function setup() {
  container = await new PostgreSqlContainer('postgres:16')
    .withDatabase('test')
    .withUsername('test')
    .withPassword('test')
    .start();

  process.env.DATABASE_URL = container.getConnectionUri();

  // Run migrations
  const pool = new pg.Pool({ connectionString: container.getConnectionUri() });
  const db = drizzle(pool);
  await migrate(db, { migrationsFolder: './drizzle' });
  await pool.end();
}

export async function teardown() {
  await container.stop();
}
```

### Transaction Rollback Pattern

Each test runs in a transaction that rolls back. Tests are isolated without the cost of recreating the DB:

```typescript
// test/helpers/db.ts
import { drizzle, NodePgDatabase } from 'drizzle-orm/node-postgres';
import pg from 'pg';
import * as schema from '../../src/db/schema';

let pool: pg.Pool;

export function getTestDb(): NodePgDatabase<typeof schema> {
  if (!pool) {
    pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });
  }
  return drizzle(pool, { schema });
}

export async function withTransaction<T>(
  fn: (tx: NodePgDatabase<typeof schema>) => Promise<T>
): Promise<T> {
  const db = getTestDb();
  try {
    // Drizzle transaction that always rolls back
    await db.transaction(async (tx) => {
      await fn(tx);
      throw new Error('ROLLBACK');   // force rollback
    });
  } catch (e) {
    if ((e as Error).message !== 'ROLLBACK') throw e;
  }
  return undefined as T;
}
```

### Seeding Strategies

```typescript
// test/helpers/seed.ts
export async function seedUsers(db: Database, count = 5) {
  const users = Array.from({ length: count }, (_, i) => ({
    id: `user-${i}`,
    name: `User ${i}`,
    email: `user${i}@test.com`,
    createdAt: new Date(),
  }));
  await db.insert(schema.users).values(users);
  return users;
}

// Per-test seeding, not shared state
test('lists users with pagination', async () => {
  await seedUsers(db, 25);
  const res = await request(app).get('/users?page=2&limit=10').set(authHeader());
  expect(res.body.data).toHaveLength(10);
  expect(res.body.meta.totalPages).toBe(3);
});
```

### In-Memory Alternatives

SQLite via `better-sqlite3` for speed when you do not need Postgres-specific features:

```typescript
import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';

const sqlite = new Database(':memory:');
const db = drizzle(sqlite);
```

**Trade-off:** Faster, but you lose Postgres-specific types (jsonb, arrays, enums), extensions (pg_trgm, PostGIS), and transaction semantics.

---

## Contract Testing with Pact

### Consumer-Driven Contracts

Your service (consumer) writes a contract describing what it expects from a provider. The provider then verifies it can fulfill that contract.

```typescript
// billing-service/test/contracts/payment-provider.pact.ts
import { PactV4, MatchersV3 } from '@pact-foundation/pact';

const { like, eachLike, uuid } = MatchersV3;

const provider = new PactV4({
  consumer: 'BillingService',
  provider: 'PaymentProvider',
});

describe('Payment Provider Contract', () => {
  test('get customer returns customer data', async () => {
    await provider
      .addInteraction()
      .given('customer abc-123 exists')
      .uponReceiving('a request for customer abc-123')
      .withRequest('GET', '/customers/abc-123', (builder) => {
        builder.headers({ Accept: 'application/json' });
      })
      .willRespondWith(200, (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json' })
          .jsonBody({
            id: uuid('abc-123'),
            email: like('customer@example.com'),
            invoices: eachLike({
              id: uuid(),
              amount: like(9900),
              currency: like('usd'),
            }),
          });
      })
      .executeTest(async (mockServer) => {
        const client = new PaymentClient(mockServer.url);
        const customer = await client.getCustomer('abc-123');
        expect(customer.email).toBe('customer@example.com');
      });
  });
});
```

### Provider Verification

```typescript
// payment-provider/test/contracts/verify.test.ts
import { Verifier } from '@pact-foundation/pact';

describe('Provider Verification', () => {
  test('fulfills billing service contract', async () => {
    await new Verifier({
      providerBaseUrl: 'http://localhost:3001',
      pactBrokerUrl: process.env.PACT_BROKER_URL,
      provider: 'PaymentProvider',
      providerVersion: process.env.GIT_SHA,
      publishVerificationResult: process.env.CI === 'true',
      stateHandlers: {
        'customer abc-123 exists': async () => {
          await seedCustomer({ id: 'abc-123' });
        },
      },
    }).verifyProvider();
  });
});
```

### CI Integration

1. Consumer generates pact files on every PR
2. Pact files are published to a Pact Broker
3. Provider CI runs verification against consumer pacts
4. `can-i-deploy` check gates deployment

```yaml
# .github/workflows/contract-test.yml
- name: Can I Deploy?
  run: |
    pact-broker can-i-deploy \
      --pacticipant BillingService \
      --version ${{ github.sha }} \
      --to-environment production
```

---

## E2E Testing

### Playwright for Full-Stack

```typescript
// e2e/user-signup.spec.ts
import { test, expect } from '@playwright/test';

test('user can sign up and see dashboard', async ({ page }) => {
  await page.goto('/signup');
  await page.fill('[name="email"]', 'new@example.com');
  await page.fill('[name="password"]', 'SecurePass123!');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('h1')).toHaveText('Welcome');
});
```

### API-Only E2E

For backend services without a UI, Playwright is overkill. Use a simple test client:

```typescript
// e2e/api/order-flow.test.ts
import { describe, test, expect, beforeAll } from 'vitest';

const API = process.env.E2E_API_URL ?? 'http://localhost:3000';

describe('Order Flow E2E', () => {
  let token: string;
  let orderId: string;

  beforeAll(async () => {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'e2e@test.com', password: 'test123' }),
    });
    token = (await res.json()).token;
  });

  test('create order -> pay -> confirm', async () => {
    // Step 1: Create order
    const create = await fetch(`${API}/orders`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [{ sku: 'WIDGET-1', qty: 2 }] }),
    });
    expect(create.status).toBe(201);
    orderId = (await create.json()).id;

    // Step 2: Pay
    const pay = await fetch(`${API}/orders/${orderId}/pay`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ paymentMethod: 'pm_test_visa' }),
    });
    expect(pay.status).toBe(200);

    // Step 3: Confirm status
    const order = await fetch(`${API}/orders/${orderId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect((await order.json()).status).toBe('paid');
  });
});
```

### Environment Management

```typescript
// e2e/global-setup.ts
import { exec } from 'child_process';
import { promisify } from 'util';

const run = promisify(exec);

export async function setup() {
  await run('docker compose -f docker-compose.e2e.yml up -d');
  await run('npx prisma migrate deploy');
  await run('npx tsx scripts/seed-e2e.ts');
  // Wait for app to be ready
  await waitForHealthCheck('http://localhost:3000/health', 30_000);
}

export async function teardown() {
  await run('docker compose -f docker-compose.e2e.yml down -v');
}

async function waitForHealthCheck(url: string, timeoutMs: number) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch { /* server not ready */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Health check timeout: ${url}`);
}
```

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

### Mocking Patterns Summary

| Pattern | When to Use | Trade-offs |
|---------|-------------|------------|
| `vi.mock` | Third-party modules, singletons | Couples to module structure |
| DI | Your own services | Requires DI-friendly architecture |
| MSW | External HTTP APIs | Best network-level fidelity |
| Spy (`vi.spyOn`) | Observing calls without replacing | Runs real code |
| Test doubles (manual) | Complex interfaces | More code, more control |
| Fake implementations | Repositories, caches | Maintenance cost |

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

## Testing Async Code

### Streams

```typescript
import { Readable, pipeline } from 'node:stream';
import { createGunzip } from 'node:zlib';

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

  // Broadcast from server
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

```typescript
// Good names — readable as sentences
test('GET /users returns 401 when no auth token is provided');
test('createOrder throws InsufficientStockError when item is out of stock');
test('retryWithBackoff retries 3 times before giving up');

// Bad names — vague, implementation-focused
test('works correctly');
test('calls the right function');
test('handles error');
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

---

## Interview Questions

### Conceptual

1. **"How do you decide between unit and integration tests for a REST API?"**
   Answer with the integration-heavy philosophy. Unit tests for pure business logic (calculations, state machines). Integration tests for everything that touches I/O. Defend with: "I test behavior, not implementation. If I refactor a service and tests break despite identical API behavior, those tests were wrong."

2. **"How do you test a service that depends on a third-party API?"**
   MSW at the network level. Explain: request handlers for happy path, per-test overrides for error scenarios, `onUnhandledRequest: 'error'` to catch regressions. Mention contract testing with Pact for formal provider agreements.

3. **"What is your approach to database testing?"**
   Test containers for CI (real Postgres in Docker). Transaction rollback for test isolation. Factory pattern for test data. Explain why in-memory SQLite is a trap for Postgres-specific code.

4. **"How do you handle flaky tests?"**
   Identify the source: shared state, timing dependencies, external services, random data. Fix in order of likelihood: add proper cleanup/teardown, use deterministic seeds for random data, replace network calls with MSW, add retry logic only as a last resort.

### Coding Challenges

5. **"Write a test for this endpoint that handles file upload and sends a notification."**
   Demonstrate: supertest with `.attach()`, MSW handler for notification service, assertion on both the HTTP response and the side effect.

6. **"This test suite takes 5 minutes. How would you speed it up?"**
   Analyze: parallel execution (`describe.concurrent`), transaction rollback instead of DB reset, MSW instead of real APIs, test containers shared across suite (global setup), eliminate unnecessary `beforeEach` setup, consider `pool: 'threads'` over `pool: 'forks'`.

7. **"Design a testing strategy for a microservice that consumes from a message queue."**
   In-process testing with a fake queue, contract tests for message schemas, E2E with real queue (test containers for RabbitMQ/Kafka), idempotency tests for duplicate messages.

### Opinionated Stances (Have Answers Ready)

- "100% coverage" is a vanity metric. Aim for high coverage on business logic, moderate on glue code.
- Snapshot tests for APIs are brittle. Use `toMatchObject` with explicit assertions.
- Test names are documentation. If a test fails in CI, the name should tell you what broke without reading code.
- Shared test state is the root of all flakiness. Each test should set up what it needs.
- E2E tests in CI should run against ephemeral environments, never shared staging.

---

**Next:** [Module 08 - Performance & Scaling](../08-performance-scaling/)
