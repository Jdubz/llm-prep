# 02 – Integration Testing and Mocking

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

### Supertest Patterns Quick Reference

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

### Auth Headers Helper

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

### File Uploads and Streaming

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
import { http, HttpResponse, delay } from 'msw';

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

  // Error response
  http.get('https://api.example.com/fail', () => {
    return HttpResponse.json({ error: 'Not found' }, { status: 404 });
  }),

  // Network error
  http.get('https://api.example.com/crash', () => {
    return HttpResponse.error();
  }),

  // Delayed response
  http.get('https://api.example.com/slow', async () => {
    await delay(3000);
    return HttpResponse.json({ data: 'late' });
  }),

  // Conditional response
  http.get('https://api.example.com/items', ({ request }) => {
    const url = new URL(request.url);
    const page = url.searchParams.get('page') ?? '1';
    return HttpResponse.json({ data: [], page: Number(page) });
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
afterEach(() => server.resetHandlers());   // reset per-test overrides
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

**vitest.config.ts:**

```typescript
export default defineConfig({
  test: {
    globalSetup: ['./test/global-setup.ts'],
    pool: 'forks',        // better isolation for DB
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

## Testing Middleware Chains

### Express Middleware in Isolation

```typescript
import { createRequest, createResponse } from 'node-mocks-http';
import { rateLimiter } from '../../src/middleware/rate-limiter';

test('rate limiter returns 429 after exceeding limit', async () => {
  const middleware = rateLimiter({ windowMs: 1000, max: 3 });

  for (let i = 0; i < 3; i++) {
    const req = createRequest({ ip: '127.0.0.1' });
    const res = createResponse();
    const next = vi.fn();
    await middleware(req, res, next);
    expect(next).toHaveBeenCalled();
  }

  // 4th request should be blocked
  const req = createRequest({ ip: '127.0.0.1' });
  const res = createResponse();
  const next = vi.fn();
  await middleware(req, res, next);
  expect(next).not.toHaveBeenCalled();
  expect(res.statusCode).toBe(429);
});
```

### Testing Middleware Ordering

```typescript
test('auth middleware runs before body validation', async () => {
  // Send invalid body WITHOUT auth -> should get 401, not 422
  const res = await request(app)
    .post('/orders')
    .send({ invalid: 'data' });

  expect(res.status).toBe(401); // Auth rejected first
});
```

### Fastify Hook Testing

```typescript
test('onRequest hook injects request ID', async () => {
  const app = build();
  await app.ready();

  const res = await app.inject({
    method: 'GET',
    url: '/health',
  });

  expect(res.headers['x-request-id']).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-/
  );
});
```

---

## Testing Cron Jobs and Background Workers

### Cron Jobs

Do not test the scheduler. Test the job function in isolation:

```typescript
// src/jobs/cleanup-expired-sessions.ts
export async function cleanupExpiredSessions(db: Database) {
  const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const result = await db
    .delete(sessions)
    .where(lt(sessions.expiresAt, cutoff))
    .returning();
  return result.length;
}

// test
test('deletes sessions older than 24 hours', async () => {
  const now = new Date('2025-01-15T12:00:00Z');
  vi.setSystemTime(now);

  await db.insert(sessions).values([
    { id: 's1', expiresAt: new Date('2025-01-14T11:00:00Z') }, // expired
    { id: 's2', expiresAt: new Date('2025-01-14T13:00:00Z') }, // not expired
    { id: 's3', expiresAt: new Date('2025-01-16T00:00:00Z') }, // not expired
  ]);

  const deleted = await cleanupExpiredSessions(db);
  expect(deleted).toBe(1);

  const remaining = await db.select().from(sessions);
  expect(remaining.map((s) => s.id)).toEqual(['s2', 's3']);

  vi.useRealTimers();
});
```

### BullMQ Workers

```typescript
import { Job } from 'bullmq';

test('email worker sends email and marks job complete', async () => {
  const emailClient = { send: vi.fn().mockResolvedValue({ id: 'msg-1' }) };
  const processor = createEmailProcessor({ emailClient });

  const job = {
    id: 'job-1',
    data: { to: 'user@test.com', template: 'welcome', vars: { name: 'Alice' } },
    attemptsMade: 0,
  } as unknown as Job;

  const result = await processor(job);

  expect(emailClient.send).toHaveBeenCalledWith({
    to: 'user@test.com',
    template: 'welcome',
    vars: { name: 'Alice' },
  });
  expect(result).toEqual({ messageId: 'msg-1' });
});

test('email worker throws on transient failure for retry', async () => {
  const emailClient = {
    send: vi.fn().mockRejectedValue(new Error('SMTP timeout')),
  };
  const processor = createEmailProcessor({ emailClient });

  const job = {
    id: 'job-2',
    data: { to: 'user@test.com', template: 'welcome', vars: {} },
    attemptsMade: 1,
  } as unknown as Job;

  await expect(processor(job)).rejects.toThrow('SMTP timeout');
});
```

---

## E2E Testing

### API-Only E2E

For backend services without a UI, use a simple test client:

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

## Testing GraphQL

### Integration Testing with a GraphQL Client

```typescript
import request from 'supertest';

test('createUser mutation validates and persists', async () => {
  const query = `
    mutation CreateUser($input: CreateUserInput!) {
      createUser(input: $input) {
        id
        name
        email
      }
    }
  `;

  const res = await request(app)
    .post('/graphql')
    .set(authHeader({ role: 'admin' }))
    .send({
      query,
      variables: {
        input: { name: 'Alice', email: 'alice@test.com' },
      },
    })
    .expect(200);

  expect(res.body.data.createUser).toMatchObject({
    id: expect.any(String),
    name: 'Alice',
    email: 'alice@test.com',
  });
  expect(res.body.errors).toBeUndefined();
});
```

### Testing DataLoader

```typescript
test('DataLoader batches user lookups', async () => {
  const querySpy = vi.spyOn(db, 'query');
  const loader = createUserLoader(db);

  // Load 3 users in the same tick
  const [u1, u2, u3] = await Promise.all([
    loader.load('user-1'),
    loader.load('user-2'),
    loader.load('user-3'),
  ]);

  // Should batch into a single query: WHERE id IN ('user-1', 'user-2', 'user-3')
  expect(querySpy).toHaveBeenCalledTimes(1);
  expect(u1.id).toBe('user-1');
});
```

---

## Testing WebSocket Handlers

### Testing Socket.IO

```typescript
import { createServer } from 'http';
import { Server } from 'socket.io';
import { io as clientIo, Socket as ClientSocket } from 'socket.io-client';

describe('Chat WebSocket', () => {
  let httpServer: ReturnType<typeof createServer>;
  let ioServer: Server;
  let client1: ClientSocket;
  let client2: ClientSocket;

  beforeAll((done) => {
    httpServer = createServer();
    ioServer = new Server(httpServer);
    setupChatHandlers(ioServer);
    httpServer.listen(0, () => {
      const port = (httpServer.address() as AddressInfo).port;
      client1 = clientIo(`http://localhost:${port}`, { auth: { token: 'user1-token' } });
      client2 = clientIo(`http://localhost:${port}`, { auth: { token: 'user2-token' } });
      let connected = 0;
      const onConnect = () => { if (++connected === 2) done(); };
      client1.on('connect', onConnect);
      client2.on('connect', onConnect);
    });
  });

  afterAll(() => {
    client1.close();
    client2.close();
    ioServer.close();
    httpServer.close();
  });

  test('message is broadcast to room members', (done) => {
    client1.emit('join', { room: 'general' });
    client2.emit('join', { room: 'general' });

    client2.on('message', (msg) => {
      expect(msg).toEqual({
        from: 'user1',
        text: 'Hello room',
        room: 'general',
      });
      done();
    });

    setTimeout(() => {
      client1.emit('message', { room: 'general', text: 'Hello room' });
    }, 100);
  });

  test('rejects unauthenticated connections', (done) => {
    const port = (httpServer.address() as AddressInfo).port;
    const badClient = clientIo(`http://localhost:${port}`, {
      auth: { token: 'invalid' },
    });

    badClient.on('connect_error', (err) => {
      expect(err.message).toContain('Authentication failed');
      badClient.close();
      done();
    });
  });
});
```

### Testing Event Ordering

```typescript
test('events arrive in order', async () => {
  const events: string[] = [];

  client1.on('step', (data: { step: string }) => {
    events.push(data.step);
  });

  client1.emit('start-workflow', { id: 'wf-1' });

  await new Promise((resolve) => setTimeout(resolve, 500));

  expect(events).toEqual(['initialized', 'processing', 'completed']);
});
```
