# Module 10: Interview Prep — Deep Dive

> Staff-level interviews aren't about knowing APIs. They're about articulating technical strategy, defending trade-offs, and demonstrating judgment. This module covers the open-ended discussions, platform thinking, and edge cases that separate staff engineers from seniors.

---

## Table of Contents

- [Staff-Level Discussion Topics](#staff-level-discussion-topics)
- [Open-Ended Architecture Discussions](#open-ended-architecture-discussions)
- [Tricky Edge Cases and Gotchas](#tricky-edge-cases-and-gotchas)

---

## Staff-Level Discussion Topics

### Technical Strategy

**"How would you evaluate whether to adopt a new framework/tool?"**

Frame it as a decision matrix, not personal preference. Criteria:

1. **Problem severity**: How painful is the current solution? Quantify: developer hours lost, incidents caused, onboarding friction.
2. **Maturity**: GitHub stars mean nothing. Look at: release cadence, breaking change history, bus factor (how many maintainers), corporate backing.
3. **Migration cost**: Not just rewriting code. Training, tooling changes, CI/CD updates, monitoring updates, documentation.
4. **Reversibility**: Can we adopt incrementally? Can we roll back if it doesn't work? Strangler fig vs big-bang rewrite.
5. **Team alignment**: Does the team want this? Imposed tooling breeds resentment and poor adoption.

Write a one-page RFC. Include a "do nothing" option with concrete costs. Let the team comment async for a week, then decide.

### Platform Team Responsibilities

**"What does a platform team own in a Node.js organization?"**

A platform team's mission is to make product engineers faster and safer. They own:

- **Shared libraries**: HTTP client with circuit breaking, structured logger, metrics SDK, auth middleware, error handling base classes
- **Service templates**: `create-service` CLI that scaffolds a new service with all the right defaults (linting, testing, CI, Dockerfile, observability)
- **Build system**: CI/CD pipeline templates, Docker base images, deployment automation
- **Observability stack**: Logging pipeline, metrics collection, distributed tracing, alerting rules
- **Developer environment**: Local development tooling, docker-compose setups, mock services
- **Standards and guardrails**: API design guidelines, code review checklists, security scanning, dependency update automation

**What they do NOT own**: Business logic, feature decisions, or telling product teams how to structure their code. They provide paved roads, not mandates.

### API Platform Design

**"How would you design an internal API platform for 20 product teams?"**

Layers:

1. **API Gateway**: Central entry point. Handles auth, rate limiting, routing, observability. Kong, Envoy, or custom Node.js gateway.

2. **Service Mesh** (optional at this scale): Istio or Linkerd for mTLS, traffic management, canary deployments. Only if you have genuine cross-service communication complexity.

3. **API Standards**: OpenAPI specs required. Generated from code (not handwritten). Automated breaking change detection in CI.

4. **SDK Generation**: Generate TypeScript client SDKs from OpenAPI specs. Product teams consume services through typed SDKs, never raw HTTP.

5. **Contract Testing**: Pact or similar. Producer and consumer tests run in CI. Breaking a contract blocks the PR.

```typescript
// What the platform team provides:
import { createService } from '@platform/service-kit';

const app = createService({
  name: 'order-service',
  version: '1.0.0',
  // These are configured by default:
  // - Structured logging with correlation IDs
  // - Health check endpoint (/healthz, /readyz)
  // - Metrics endpoint (/metrics)
  // - Graceful shutdown
  // - Error handling middleware
  // - Request validation via Zod
  // - OpenAPI spec generation
});

// Product team just writes routes
app.route({
  method: 'POST',
  path: '/orders',
  schema: CreateOrderSchema,
  handler: async (req) => {
    // Business logic only
  },
});
```

### Developer Experience (DX)

**"How do you measure and improve developer experience?"**

**Metrics**:
- **Time to first commit**: How long from `git clone` to a merged PR for a new engineer
- **CI/CD duration**: P50 and P95 build times. Target: under 10 minutes for the fast path
- **Deploy frequency**: How often can a team ship? Daily? Multiple times per day?
- **Time to recovery**: When something breaks, how fast can you roll back or fix forward?
- **Inner loop speed**: `save → see result` cycle time. Hot reload, fast tests, instant feedback

**Improvements**:
- Invest in local development. If `docker-compose up` takes 5 minutes, engineers avoid restarting. If it takes 10 seconds, they experiment freely
- Pre-built development containers with all dependencies
- Watch mode for everything: tests, linting, type checking, API docs
- Standardize tooling so switching between services doesn't require mental context switches
- Dedicated DX engineer who does nothing but reduce friction

### Build System Optimization

**"Our CI takes 45 minutes. How do you fix it?"**

Diagnose first, optimize second.

1. **Profile the pipeline**: Where is time actually spent? Build? Tests? Docker? Deploy? Measure each stage.

2. **Caching**:
   - `node_modules` caching (hash of `package-lock.json`)
   - TypeScript incremental compilation (`.tsbuildinfo` caching)
   - Docker layer caching (order Dockerfile commands by change frequency)
   - Test result caching (Turborepo/Nx remote caching)

3. **Parallelization**:
   - Run lint, typecheck, and unit tests in parallel (they're independent)
   - Shard test suites across multiple CI runners
   - Use Turborepo/Nx `affected` to only run tasks for changed packages

4. **Reduce scope**:
   - Skip unchanged packages in monorepo
   - Run only affected tests (Vitest `--changed`)
   - Lightweight smoke tests in PR, full suite on merge to main

5. **Infrastructure**:
   - Larger CI runners (more CPU/RAM)
   - Self-hosted runners with persistent caches
   - Remote build caching (Turborepo Remote Cache, Nx Cloud)

Realistic target: 45 minutes down to 8-12 minutes with caching and parallelization. Down to 3-5 minutes with affected-only and sharding.

### Monorepo Migration

**"How would you migrate 15 repos into a monorepo?"**

This is a 3-6 month project depending on team size. Do NOT underestimate it.

**Phase 1: Foundation (2-4 weeks)**
- Choose tooling (Turborepo vs Nx). Turborepo for simplicity, Nx for advanced features.
- Set up the monorepo structure: `apps/`, `packages/`, shared configs
- Configure CI/CD for monorepo (affected builds, remote caching)
- Test with one low-risk service

**Phase 2: Migration (6-12 weeks, rolling)**
- Migrate repos one at a time, starting with repos that share the most code
- Use `git subtree` or `git filter-repo` to preserve history
- Update import paths, CI configs, Docker builds
- Keep old repos as read-only archives with a redirect notice

**Phase 3: Extract shared code (4-8 weeks)**
- Identify duplicated code across migrated services
- Extract into shared packages: `@org/logger`, `@org/auth`, `@org/database`
- Add module boundary enforcement (Nx boundaries or ESLint rules)

**Phase 4: Optimization (ongoing)**
- Remote caching for CI
- Affected-only builds and tests
- Shared Docker base images
- Automated dependency updates across all packages

**Pitfalls**:
- Git history gets messy if you don't use `filter-repo` correctly
- CI/CD becomes the bottleneck — invest early in affected builds
- "Shared" packages that are really owned by one team — shared code needs shared ownership or it becomes a bottleneck
- IDE performance degrades with large monorepos — configure TypeScript project references

### TypeScript Migration Strategy

**"We have 200k lines of JavaScript. How do you migrate to TypeScript?"**

**Never do a big-bang migration.** Use the gradual approach:

**Phase 1: Infrastructure (1-2 weeks)**
```jsonc
// tsconfig.json — start permissive
{
  "compilerOptions": {
    "allowJs": true,            // JS files coexist with TS
    "checkJs": false,           // Don't type-check JS yet
    "strict": false,            // Add strictness gradually
    "noEmit": true,             // Use external bundler
    "moduleResolution": "bundler",
    "target": "ES2022"
  }
}
```

**Phase 2: New code in TypeScript (ongoing)**
- All new files are `.ts`
- All new functions have type annotations
- PRs that touch a JS file should convert it to TS (boy scout rule)

**Phase 3: Enable strict checks incrementally**
- Enable `strictNullChecks` first (catches the most bugs)
- Then `noImplicitAny`
- Then `strictFunctionTypes`
- Then full `strict: true`
- Use `// @ts-expect-error` as a temporary escape hatch with a tracking issue

**Phase 4: Automated conversion**
- Use `ts-migrate` (Airbnb's tool) to bulk-convert files. It adds `// @ts-expect-error` where needed.
- Teams clean up `@ts-expect-error` comments incrementally
- Track migration progress: `find . -name '*.js' | wc -l` vs `find . -name '*.ts' | wc -l`

**Metrics to track**:
- Percentage of files converted
- Number of `@ts-expect-error` comments remaining
- Number of `any` types remaining (use `typescript-strict-plugin` to track)
- Type coverage percentage (use `type-coverage` npm package)

---

## Open-Ended Architecture Discussions

### "Your API is getting 10x more traffic than expected. What do you do?"

**Immediate (within hours)**:
- Scale horizontally — add more instances/pods
- Enable response caching (Redis) for read-heavy endpoints
- Add rate limiting to protect downstream services
- Check if any endpoints are doing N+1 queries and fix the worst offenders

**Short-term (within days)**:
- Profile and optimize the top 5 slowest endpoints
- Add connection pooling if not already configured (PgBouncer, Prisma connection pool)
- Implement read replicas for read-heavy queries
- Move expensive computations to background jobs (BullMQ)

**Medium-term (within weeks)**:
- Implement CQRS for endpoints with divergent read/write patterns
- Add CDN for static/semi-static responses
- Consider decomposing if specific endpoints have wildly different scaling needs
- Load test to find the new ceiling

**What interviewers want to hear**: You can triage by urgency. You start with the cheapest, highest-impact changes. You don't jump to "rewrite in microservices."

### "How do you handle a critical production bug at 2am?"

1. **Assess severity**: Is it data loss? Is it user-facing? How many users affected?
2. **Communicate**: Post in incident channel. Page the relevant on-call if it's not you.
3. **Mitigate first, fix later**: Can you feature-flag the broken code path? Revert the last deploy? Route traffic away?
4. **Debug with observability**: Logs (correlation ID), metrics (error rate spike), traces (which service/function failed)
5. **Fix and verify**: Minimal fix. Deploy to staging. Verify. Deploy to production. Monitor for 30 minutes.
6. **Post-incident**: Write a blameless postmortem within 48 hours. Focus on systemic causes: Why didn't tests catch it? Why didn't monitoring alert earlier? What process changes prevent recurrence?

### "How do you decide what to build vs buy vs adopt open source?"

| Factor | Build | Buy (SaaS) | Open Source |
|--------|-------|-------------|-------------|
| Core to business | Yes | No | Maybe |
| Competitive advantage | Yes | No | No |
| Maintenance budget | Have dedicated team | Want to minimize | Medium |
| Customization needs | High | Low | Medium-High |
| Time to market | Slow | Fast | Medium |
| Data sensitivity | Full control | Vendor risk | Full control |
| Total cost (3 year) | Highest upfront, lowest ongoing | Medium ongoing | Low upfront, variable ongoing |

**Framework**: If it's core to your business and a competitive advantage, build it. If it's table-stakes infrastructure (auth, email, payments), buy it. If it's technical infrastructure (database, message queue, monitoring), use open source.

### "A team wants to rewrite a service from scratch. How do you evaluate this?"

Almost always push back. Rewrites fail more often than they succeed because:
- The old system encodes years of edge cases and bug fixes that aren't documented
- Rewriting takes 2-3x longer than estimated
- The business can't wait — you're maintaining two systems during the rewrite
- The new system will have its own bugs

**Instead**: Refactor incrementally. Strangler fig pattern. Extract one bounded context at a time. Keep the old system running until each piece is proven.

**Exception**: The rewrite is justified when the old system's technology is genuinely dead (no security patches, no maintainers, can't hire for it) AND the system is small enough to rewrite in under 3 months.

---

## Tricky Edge Cases and Gotchas

### Node.js Gotchas

**1. `JSON.parse` of large payloads blocks the event loop**
Parsing a 50MB JSON string can block for 500ms+. Use streaming JSON parsers (`stream-json`) or move parsing to a worker thread.

**2. `Date` constructor timezone behavior**
```typescript
new Date('2024-01-15');          // Interpreted as UTC (midnight UTC)
new Date('2024-01-15T00:00:00'); // Interpreted as LOCAL timezone
// These are different dates if you're not in UTC
```

**3. `parseInt` with radix**
```typescript
parseInt('08');      // 8 (modern engines) but historically 0 (octal)
parseInt('0x10');    // 16 (hex prefix detected)
parseInt('10', 2);   // 2 (binary)
// Always pass the radix: parseInt(str, 10)
```

**4. `Promise.all` fails fast**
```typescript
// If any promise rejects, ALL results are lost
await Promise.all([fetchA(), fetchB(), fetchC()]);
// If fetchB rejects, you don't get fetchA and fetchC results

// Use Promise.allSettled to get all results regardless
const results = await Promise.allSettled([fetchA(), fetchB(), fetchC()]);
const successes = results.filter(r => r.status === 'fulfilled').map(r => r.value);
const failures = results.filter(r => r.status === 'rejected').map(r => r.reason);
```

**5. `EventEmitter` max listeners warning**
```typescript
// Default is 10 listeners per event. Exceeding it prints a warning (not an error).
// This is usually a leak, but sometimes intentional.
emitter.setMaxListeners(50); // Increase if intentional
// Or globally: EventEmitter.defaultMaxListeners = 50;
```

**6. `Buffer.from` encoding confusion**
```typescript
Buffer.from('hello');           // UTF-8 (default)
Buffer.from('68656c6c6f', 'hex'); // Hex string → Buffer
Buffer.from('aGVsbG8=', 'base64'); // Base64 → Buffer

// Gotcha: Buffer.from(number) was removed — use Buffer.alloc(number)
```

**7. `setImmediate` vs `setTimeout(fn, 0)` ordering**
```typescript
// Outside I/O callback: order is NON-DETERMINISTIC
setTimeout(() => console.log('timeout'), 0);
setImmediate(() => console.log('immediate'));
// Could print in either order

// Inside I/O callback: setImmediate always fires first
fs.readFile('file.txt', () => {
  setTimeout(() => console.log('timeout'), 0);
  setImmediate(() => console.log('immediate'));
  // Always prints: immediate, timeout
});
```

### TypeScript Gotchas

**8. Object spread doesn't call setters**
```typescript
class Config {
  private _port = 3000;
  set port(value: number) {
    if (value < 0 || value > 65535) throw new Error('Invalid port');
    this._port = value;
  }
}

const config = new Config();
Object.assign(config, { port: -1 }); // Calls setter — throws
const config2 = { ...config, port: -1 }; // Spread — creates plain object, no setter
```

**9. Enum values can collide with reverse mapping**
```typescript
enum Status { Active = 0, Inactive = 1 }
Status[0]; // 'Active' — reverse mapping exists for numeric enums
// This means Object.keys(Status) returns ['0', '1', 'Active', 'Inactive']
// Use const enums or string enums to avoid this
```

**10. `readonly` is shallow**
```typescript
interface User {
  readonly name: string;
  readonly addresses: string[];
}

const user: User = { name: 'Alice', addresses: ['123 Main St'] };
user.name = 'Bob';           // Error — readonly
user.addresses.push('456 Oak'); // OK — readonly doesn't protect array contents
// Use ReadonlyArray<string> or readonly string[] for deep immutability
```

**11. Structural typing allows unexpected values**
```typescript
interface Point { x: number; y: number; }
interface Point3D { x: number; y: number; z: number; }

function distance(p: Point): number { return Math.sqrt(p.x ** 2 + p.y ** 2); }

const p3d: Point3D = { x: 1, y: 2, z: 3 };
distance(p3d); // OK — Point3D is structurally compatible with Point
// This is usually fine, but can cause issues with spread/rest
```

**12. `typeof` in type position vs value position**
```typescript
const config = { port: 3000, host: 'localhost' };

typeof config;             // Value position: 'object' (JavaScript)
type Config = typeof config; // Type position: { port: number; host: string } (TypeScript)
```

**13. Assertion functions don't work with arrow functions**
```typescript
// This works
function assertString(value: unknown): asserts value is string {
  if (typeof value !== 'string') throw new Error('Not a string');
}

// This does NOT work — arrow functions can't be assertion functions
const assertString2 = (value: unknown): asserts value is string => {
  if (typeof value !== 'string') throw new Error('Not a string');
};
```

**14. Optional chaining with method calls**
```typescript
const result = obj?.method?.();  // Calls method only if obj and method exist
// But be careful:
const result2 = obj?.method();   // Calls method if obj exists, throws if method doesn't
```

**15. `keyof` with index signatures**
```typescript
interface StringMap {
  [key: string]: unknown;
  knownKey: string;
}

type Keys = keyof StringMap; // string | number
// Why number? Because in JavaScript, numeric keys are also valid string keys
// obj[0] is equivalent to obj['0']
```

### Production Gotchas

**16. Connection pool exhaustion**
```typescript
// Each request creates a new PrismaClient — connection pool per request
app.get('/users', async (req, res) => {
  const prisma = new PrismaClient(); // BUG: new pool per request
  const users = await prisma.user.findMany();
  res.json(users);
  // Connection never closed — pool grows until DB rejects connections
});

// Fix: single PrismaClient instance shared across the application
```

**17. Unbounded cache growth**
```typescript
// This Map grows forever — no eviction
const cache = new Map<string, CachedResponse>();

app.get('/api/:id', async (req, res) => {
  if (cache.has(req.params.id)) return res.json(cache.get(req.params.id));
  const data = await fetchExpensiveData(req.params.id);
  cache.set(req.params.id, data); // Memory leak
  res.json(data);
});

// Fix: Use LRU cache with max size and TTL
import { LRUCache } from 'lru-cache';
const cache = new LRUCache<string, CachedResponse>({ max: 10_000, ttl: 300_000 });
```

**18. Missing `await` on database operations**
```typescript
app.post('/orders', async (req, res) => {
  const order = await orderService.create(req.body);
  // Missing await — fire-and-forget, errors silently swallowed
  auditService.logOrderCreated(order.id);
  // Fix: await auditService.logOrderCreated(order.id);
  // Or explicitly handle: auditService.logOrderCreated(order.id).catch(err => logger.error(err));
  res.status(201).json(order);
});
```

**19. Race conditions in concurrent requests**
```typescript
// Two concurrent requests for the same user
app.post('/transfer', async (req, res) => {
  const account = await db.account.findUnique({ where: { id: req.body.accountId } });
  if (account.balance < req.body.amount) return res.status(400).json({ error: 'Insufficient funds' });

  // Between the check above and the update below, another request could have reduced the balance
  await db.account.update({
    where: { id: req.body.accountId },
    data: { balance: { decrement: req.body.amount } },
  });

  // Fix: Use database-level locking or atomic operations
  // UPDATE accounts SET balance = balance - $1 WHERE id = $2 AND balance >= $1
});
```

**20. Error swallowing in `.catch` chains**: `.catch(err => console.log(err))` logs but continues as if nothing happened. Callers think the operation succeeded. Fix: re-throw after logging, or return a Result type.
