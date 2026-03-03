# 03 – Advanced Testing Patterns

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

When fast-check finds a failing input, it *shrinks* it to the minimal reproduction case. Instead of a 50-field object, you get the 2 fields that actually matter.

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

Mutation testing answers: "Would my tests catch a bug if I introduced one?" A mutation testing tool modifies your source code (mutations) and checks if your tests fail. If they don't, your tests have a gap.

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

## Chaos Testing

Chaos testing introduces failures to verify your system handles them gracefully.

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

## Performance and Load Testing

### k6

```javascript
// load-tests/spike.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const latency = new Trend('api_latency');

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
    errors: ['rate<0.01'],
  },
};

export default function () {
  group('API Endpoints', () => {
    const start = Date.now();
    const res = http.get('http://localhost:3000/api/products', {
      headers: { Authorization: `Bearer ${__ENV.TOKEN}` },
    });
    latency.add(Date.now() - start);

    const success = check(res, {
      'status is 200': (r) => r.status === 200,
      'response time < 500ms': (r) => r.timings.duration < 500,
      'has products': (r) => JSON.parse(r.body).data.length > 0,
    });
    errorRate.add(!success);
  });

  sleep(0.5);
}
```

```bash
# k6 Quick Commands
k6 run load-test.js
k6 run -e TOKEN=xxx -e API_URL=http://localhost:3000 load-test.js
k6 run --vus 50 --duration 2m load-test.js
k6 run --out json=results.json load-test.js
k6 run --out influxdb=http://localhost:8086/k6 load-test.js
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

### Interpreting Load Test Results

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| p95 latency | <200ms | 200-500ms | >500ms |
| p99 latency | <500ms | 500ms-1s | >1s |
| Error rate | <0.1% | 0.1-1% | >1% |
| Throughput | Stable | Declining under load | Collapsed |

| Symptom | Likely Cause |
|---------|-------------|
| p99 >> p95 | GC pauses, lock contention |
| Latency grows with load | Connection pool exhaustion |
| Memory grows linearly | Memory leak |
| CPU at 100% one core | Single-threaded bottleneck |

Look for: latency degradation under load (often DB connection pool exhaustion), error rate spikes at specific RPS thresholds, and memory growth during sustained load.

---

## Interview Questions and Opinionated Stances

### Conceptual Questions

**"How do you decide between unit and integration tests for a REST API?"**

Answer with the integration-heavy philosophy. Unit tests for pure business logic (calculations, state machines). Integration tests for everything that touches I/O. Defend with: "I test behavior, not implementation. If I refactor a service and tests break despite identical API behavior, those tests were wrong."

**"How do you test a service that depends on a third-party API?"**

MSW at the network level. Explain: request handlers for happy path, per-test overrides for error scenarios, `onUnhandledRequest: 'error'` to catch regressions. Mention contract testing with Pact for formal provider agreements.

**"What is your approach to database testing?"**

Test containers for CI (real Postgres in Docker). Transaction rollback for test isolation. Factory pattern for test data. Explain why in-memory SQLite is a trap for Postgres-specific code.

**"How do you handle flaky tests?"**

Identify the source: shared state, timing dependencies, external services, random data. Fix in order of likelihood: add proper cleanup/teardown, use deterministic seeds for random data, replace network calls with MSW, add retry logic only as a last resort.

### Coding Challenges

**"Write a test for this endpoint that handles file upload and sends a notification."**

Demonstrate: supertest with `.attach()`, MSW handler for notification service, assertion on both the HTTP response and the side effect.

**"This test suite takes 5 minutes. How would you speed it up?"**

Analyze: parallel execution (`describe.concurrent`), transaction rollback instead of DB reset, MSW instead of real APIs, test containers shared across suite (global setup), eliminate unnecessary `beforeEach` setup, consider `pool: 'threads'` over `pool: 'forks'`.

**"Design a testing strategy for a microservice that consumes from a message queue."**

In-process testing with a fake queue, contract tests for message schemas, E2E with real queue (test containers for RabbitMQ/Kafka), idempotency tests for duplicate messages.

### Key Takeaways for Interviews

1. **Property-based testing** finds edge cases humans miss. Use it for serialization, parsing, and mathematical invariants.
2. **Mutation testing** measures test quality, not test quantity. It answers "would my tests catch a real bug?"
3. **Snapshot testing** is a change detector, not a correctness verifier. Prefer explicit assertions for APIs.
4. **Test the job, not the scheduler.** Cron job functions should be pure functions of their dependencies.
5. **Chaos testing** proves resilience. Simulate network failures, timeouts, and resource exhaustion.
6. **Load testing** should run in CI with defined thresholds. p95 and p99 latency matter more than averages.
7. **GraphQL testing** should verify both the data layer (resolver tests) and the transport layer (HTTP integration tests).
8. **WebSocket testing** requires managing connection lifecycle carefully. Always clean up listeners and connections.

### Opinionated Stances (Have Answers Ready)

- "100% coverage" is a vanity metric. Aim for high coverage on business logic, moderate on glue code.
- Snapshot tests for APIs are brittle. Use `toMatchObject` with explicit assertions.
- Test names are documentation. If a test fails in CI, the name should tell you what broke without reading code.
- Shared test state is the root of all flakiness. Each test should set up what it needs.
- E2E tests in CI should run against ephemeral environments, never shared staging.
