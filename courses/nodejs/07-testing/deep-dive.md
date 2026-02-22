# Module 07: Testing — Deep Dive

> Advanced testing patterns you will rarely need day-to-day but that demonstrate mastery in interviews. Property-based testing, mutation testing, chaos engineering, and load testing.

---

## Property-Based Testing with fast-check

Traditional tests verify specific examples. Property-based tests verify *invariants* across thousands of random inputs.

### When Property-Based Testing Shines

- Serialization/deserialization roundtrips
- Parsers (URL, CSV, JSON schema)
- Mathematical or financial calculations
- Data structure invariants
- Encoding/decoding (Base64, JWT payload)

### Core Concepts

```typescript
import { test } from 'vitest';
import fc from 'fast-check';

test('JSON.parse is the inverse of JSON.stringify for objects', () => {
  fc.assert(
    fc.property(
      fc.jsonValue(),  // arbitrary: generates random JSON-safe values
      (value) => {
        const roundtripped = JSON.parse(JSON.stringify(value));
        expect(roundtripped).toEqual(value);  // property: roundtrip is identity
      }
    ),
    { numRuns: 1000 }
  );
});
```

### Custom Arbitraries

```typescript
// Domain-specific arbitrary for a valid Order
const orderArbitrary = fc.record({
  id: fc.uuid(),
  items: fc.array(
    fc.record({
      sku: fc.stringMatching(/^[A-Z]{3}-\d{4}$/),
      quantity: fc.integer({ min: 1, max: 100 }),
      priceInCents: fc.integer({ min: 1, max: 100_000 }),
    }),
    { minLength: 1, maxLength: 20 }
  ),
  discount: fc.option(fc.integer({ min: 0, max: 50 }), { nil: undefined }),
});

test('order total is always >= sum of items minus max discount', () => {
  fc.assert(
    fc.property(orderArbitrary, (order) => {
      const total = calculateOrderTotal(order);
      const itemSum = order.items.reduce(
        (sum, item) => sum + item.quantity * item.priceInCents,
        0
      );
      expect(total).toBeGreaterThanOrEqual(0);
      expect(total).toBeLessThanOrEqual(itemSum);
    })
  );
});
```

### Shrinking

When fast-check finds a failing input, it *shrinks* it to the minimal reproduction case. This is the killer feature. Instead of a 50-field object, you get the 2 fields that actually matter.

```typescript
test('slugify handles all unicode', () => {
  fc.assert(
    fc.property(fc.fullUnicodeString(), (input) => {
      const slug = slugify(input);
      // Property: slug only contains valid URL characters
      expect(slug).toMatch(/^[a-z0-9-]*$/);
      // Property: no double hyphens
      expect(slug).not.toContain('--');
    })
  );
  // If this fails, fast-check will shrink the input to the
  // simplest string that breaks the property
});
```

### Reproducibility

```typescript
fc.assert(
  fc.property(/* ... */),
  {
    seed: 42,         // deterministic for CI reproducibility
    endOnFailure: true,
    verbose: true,    // logs the failing case and shrink steps
  }
);
```

---

## Mutation Testing

Mutation testing answers: "Would my tests catch a bug if I introduced one?"

A mutation testing tool modifies your source code (mutations) and checks if your tests fail. If they don't, your tests have a gap.

### Stryker Mutator for Node.js

```json
// stryker.config.json
{
  "mutator": {
    "plugins": ["@stryker-mutator/typescript-checker"],
    "excludedMutations": ["StringLiteral"]
  },
  "testRunner": "vitest",
  "reporters": ["html", "clear-text", "progress"],
  "coverageAnalysis": "perTest",
  "thresholds": {
    "high": 80,
    "low": 60,
    "break": 50
  }
}
```

### Mutation Types

| Mutation | Example | What It Catches |
|----------|---------|----------------|
| Conditional boundary | `>` becomes `>=` | Off-by-one errors |
| Negate conditional | `===` becomes `!==` | Inverted logic |
| Remove call | `array.sort()` removed | Missing behavior assertions |
| Arithmetic | `+` becomes `-` | Calculation errors |
| Boolean substitution | `true` becomes `false` | Missing boolean checks |

### Interpreting Results

```
Mutation score: 76%
  Killed: 152    ← Tests caught the mutation (good)
  Survived: 48   ← Tests missed the mutation (bad)
  Timeout: 3     ← Mutation caused infinite loop (counts as caught)
  No coverage: 12 ← Code not covered at all
```

**Interview insight:** Mutation testing is the only way to measure *test quality* rather than *test quantity*. Coverage tells you what code runs, mutation testing tells you if your assertions would catch a bug.

### Practical Usage

Do not run mutation testing on every CI build (it is slow). Run it:
- Weekly on critical paths (billing, auth)
- On PRs that touch core business logic
- As a quality gate for the most important 20% of your codebase

---

## Snapshot Testing for APIs

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

Integration test that verifies auth runs before validation:

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

  // Create a fake Job object
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

## Chaos Testing

Chaos testing introduces failures to verify your system handles them gracefully. This is testing for resilience, not correctness.

### Network Chaos with MSW

```typescript
test('circuit breaker opens after 3 consecutive failures', async () => {
  let callCount = 0;

  server.use(
    http.get('https://api.payment.com/status', () => {
      callCount++;
      return HttpResponse.error(); // network error
    })
  );

  // Make 3 calls — all fail
  for (let i = 0; i < 3; i++) {
    await paymentClient.checkStatus().catch(() => {});
  }

  // 4th call should not hit the server (circuit is open)
  const prevCount = callCount;
  await expect(paymentClient.checkStatus()).rejects.toThrow('Circuit open');
  expect(callCount).toBe(prevCount); // No additional network call
});
```

### Timeout Simulation

```typescript
test('request times out after 5 seconds', async () => {
  server.use(
    http.get('https://api.slow.com/data', async () => {
      await new Promise((r) => setTimeout(r, 10_000)); // simulate slow
      return HttpResponse.json({ data: 'late' });
    })
  );

  await expect(
    fetchWithTimeout('https://api.slow.com/data', { timeout: 5000 })
  ).rejects.toThrow('Timeout');
});
```

### Database Chaos

```typescript
test('handles connection pool exhaustion gracefully', async () => {
  // Exhaust all connections
  const connections = await Promise.all(
    Array.from({ length: 20 }, () => pool.connect())
  );

  // Next request should fail gracefully, not hang
  const res = await request(app).get('/users').set(authHeader());
  expect(res.status).toBe(503);
  expect(res.body.message).toContain('temporarily unavailable');

  // Cleanup
  connections.forEach((c) => c.release());
});
```

---

## Load Testing

### k6

```javascript
// load-tests/spike.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 50 },   // ramp up
    { duration: '1m',  target: 50 },   // sustain
    { duration: '10s', target: 200 },  // spike
    { duration: '1m',  target: 200 },  // sustain spike
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://localhost:3000/api/products', {
    headers: { Authorization: `Bearer ${__ENV.TOKEN}` },
  });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'has products': (r) => JSON.parse(r.body).data.length > 0,
  });

  sleep(0.1);
}
```

### Artillery

```yaml
# load-tests/order-flow.yml
config:
  target: "http://localhost:3000"
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 50
      name: "Sustained load"
  plugins:
    expect: {}

scenarios:
  - name: "Create and pay for order"
    flow:
      - post:
          url: "/auth/login"
          json:
            email: "loadtest@example.com"
            password: "test123"
          capture:
            - json: "$.token"
              as: "token"
      - post:
          url: "/orders"
          headers:
            Authorization: "Bearer {{ token }}"
          json:
            items:
              - sku: "WIDGET-1"
                qty: 1
          capture:
            - json: "$.id"
              as: "orderId"
          expect:
            - statusCode: 201
      - post:
          url: "/orders/{{ orderId }}/pay"
          headers:
            Authorization: "Bearer {{ token }}"
          json:
            paymentMethod: "pm_test_visa"
          expect:
            - statusCode: 200
```

### Interpreting Results

Key metrics to watch:

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| p95 latency | <200ms | 200-500ms | >500ms |
| p99 latency | <500ms | 500ms-1s | >1s |
| Error rate | <0.1% | 0.1-1% | >1% |
| Throughput | Stable | Declining under load | Collapsed |

Look for: latency degradation under load (often DB connection pool exhaustion), error rate spikes at specific RPS thresholds, and memory growth during sustained load.

---

## Testing GraphQL Resolvers

### Unit Testing Resolvers

```typescript
import { createTestContext } from '../helpers/graphql-context';

test('users resolver returns paginated results', async () => {
  const ctx = createTestContext();
  await seedUsers(ctx.db, 15);

  const result = await resolvers.Query.users(
    null,
    { first: 10, after: null },
    ctx
  );

  expect(result.edges).toHaveLength(10);
  expect(result.pageInfo.hasNextPage).toBe(true);
  expect(result.totalCount).toBe(15);
});
```

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

test('createUser returns validation errors for bad input', async () => {
  const res = await request(app)
    .post('/graphql')
    .set(authHeader({ role: 'admin' }))
    .send({
      query: `mutation { createUser(input: { name: "", email: "bad" }) { id } }`,
    })
    .expect(200);

  expect(res.body.errors).toBeDefined();
  expect(res.body.errors[0].extensions.code).toBe('BAD_USER_INPUT');
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
    setupChatHandlers(ioServer);  // your handler setup
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
    // Both clients join the same room
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

    // Small delay to ensure join completes
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

  // Wait for all events
  await new Promise((resolve) => setTimeout(resolve, 500));

  expect(events).toEqual(['initialized', 'processing', 'completed']);
});
```

---

## Key Takeaways for Interviews

1. **Property-based testing** finds edge cases humans miss. Use it for serialization, parsing, and mathematical invariants.
2. **Mutation testing** measures test quality, not test quantity. It answers "would my tests catch a real bug?"
3. **Snapshot testing** is a change detector, not a correctness verifier. Prefer explicit assertions for APIs.
4. **Test the job, not the scheduler.** Cron job functions should be pure functions of their dependencies.
5. **Chaos testing** proves resilience. Simulate network failures, timeouts, and resource exhaustion.
6. **Load testing** should run in CI with defined thresholds. p95 and p99 latency matter more than averages.
7. **GraphQL testing** should verify both the data layer (resolver tests) and the transport layer (HTTP integration tests).
8. **WebSocket testing** requires managing connection lifecycle carefully. Always clean up listeners and connections.
