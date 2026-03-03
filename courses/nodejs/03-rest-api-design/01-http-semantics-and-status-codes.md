# 01 — HTTP Methods, Idempotency, Status Codes, Headers, and REST Constraints

> Assumes you have shipped production REST APIs. Focuses on design decisions and trade-offs, not basics. Fluency with Express/Fastify, TypeScript, and databases assumed.

---

## 1. Resource Modeling

### 1.1 Naming Conventions

- **Plural nouns, always.** `/users`, `/orders`. `GET /users` and `GET /users/123` both read naturally.
- **Kebab-case for multi-word resources.** `/line-items`, not `/lineItems` or `/line_items`.
- **No verbs in URIs.** `/users/123/activate` is RPC wearing REST clothing. Use `PATCH /users/123` with `{ "status": "active" }`, or `POST /users/123/activations` for non-CRUD actions.

### 1.2 Nesting Depth

The practical limit is **two levels**: `/users/123/orders/456`. Three levels signals a modeling problem.

1. **Coupling.** Deep nesting forces consumers to know parent context. `GET /orders/456` should work if orders have globally unique IDs.
2. **URL length.** API gateways enforce URI length limits.
3. **Cacheability.** Deeper paths reduce cache hit rates.

| Question | If Yes | If No |
|----------|--------|-------|
| Does the child have a globally unique ID? | Promote to top-level | Keep nested |
| Can the child exist without the parent? | Top-level resource | Nested sub-resource |
| Do consumers list children across parents? | Top-level with filter param | Nested is fine |
| Is the relationship 1:1? | Embed in parent representation | Separate resource |

### 1.3 Sub-Resources vs Independent Resources

The key question: **does the child have meaning outside its parent?** An order line item does not — keep it nested (`/orders/123/line-items`). A comment on a blog post might — if you need a "recent comments" feed, make it top-level (`/comments?postId=123`).

**Singleton sub-resources** (exactly one per parent) drop the ID and use singular: `GET /users/123/profile`, `PUT /users/123/profile`.

---

## 2. HTTP Method Semantics

### 2.1 Method Reference Table

| Method | Safe | Idempotent | Has Body | Typical Use | Typical Success Code |
|--------|------|------------|----------|-------------|---------------------|
| GET | Yes | Yes | No | Read resource | 200 |
| HEAD | Yes | Yes | No | Read headers only | 200 |
| POST | No | No | Yes | Create resource / trigger action | 201 (create) or 200 (action) |
| PUT | No | Yes | Yes | Full replacement | 200 or 204 |
| PATCH | No | No* | Yes | Partial update | 200 or 204 |
| DELETE | No | Yes | Optional | Remove resource | 204 |
| OPTIONS | Yes | Yes | No | CORS preflight / discovery | 204 |

*PATCH is not idempotent by spec, though JSON Merge Patch operations often are in practice.

### 2.2 PUT vs PATCH

**PUT** replaces the entire resource. Omitted fields are removed. Simple, predictable, idempotent by definition.

**PATCH** updates only sent fields. Key questions: (1) What format — JSON Merge Patch (RFC 7396) or JSON Patch (RFC 6902)? (2) With JSON Merge Patch, `null` means "remove this field" — you cannot set a field to literal `null`. (3) JSON Patch (`add` to arrays) is not idempotent.

**Production recommendation:** Use JSON Merge Patch (`Content-Type: application/merge-patch+json`) for 95% of cases. Reserve JSON Patch for array manipulation.

### 2.3 Idempotency for POST

For non-idempotent operations like payment creation, use application-level idempotency:

```typescript
app.post('/payments', async (req, res) => {
  const key = req.headers['idempotency-key'] as string;
  if (!key) return res.status(400).json({ error: 'Idempotency-Key required' });

  const existing = await db.idempotencyKeys.findOne({ key });
  if (existing) return res.status(existing.statusCode).json(existing.body);

  const result = await processPayment(req.body);
  await db.idempotencyKeys.insertOne({ key, statusCode: 201, body: result, createdAt: new Date() });
  return res.status(201).json(result);
});
```

**Critical detail:** The lookup and processing must be atomic (or guarded with a distributed lock) to prevent two concurrent requests with the same key from both executing.

---

## 3. Status Codes

### 3.1 Success (2xx)

| Code | Name | When |
|------|------|------|
| 200 | OK | GET, PUT, PATCH success with body |
| 201 | Created | POST created a resource (include `Location` header) |
| 202 | Accepted | Async operation accepted, not yet complete |
| 204 | No Content | DELETE success, or PUT/PATCH with no response body |

### 3.2 Redirection (3xx)

| Code | Name | When |
|------|------|------|
| 301 | Moved Permanently | Resource URL permanently changed |
| 304 | Not Modified | ETag matched (conditional GET) |

### 3.3 Client Error (4xx)

| Code | Name | When |
|------|------|------|
| 400 | Bad Request | Malformed syntax, unparseable JSON |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource does not exist |
| 405 | Method Not Allowed | HTTP method not supported on this URI |
| 409 | Conflict | State conflict, duplicate, version mismatch |
| 410 | Gone | Permanently deleted (known removal) |
| 415 | Unsupported Media Type | Wrong Content-Type |
| 422 | Unprocessable Entity | Valid syntax, invalid semantics (validation) |
| 429 | Too Many Requests | Rate limit exceeded (include `Retry-After`) |

### 3.4 Server Error (5xx)

| Code | Name | When |
|------|------|------|
| 500 | Internal Server Error | Unhandled exception (never leak stack traces) |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Overloaded / maintenance (include `Retry-After`) |
| 504 | Gateway Timeout | Upstream service timeout |

### 3.5 Common Misuses

- **200 for POST that created something.** Use 201.
- **400 as catch-all for client errors.** Use 422 for validation, 409 for conflicts, etc.
- **401 vs 403 confusion.** 401 = "who are you?" 403 = "I know who you are, and no."
- **404 for empty collections.** `GET /users/123/orders` where user has no orders is 200 with empty array, not 404. The collection resource exists; it is just empty.
- **403 leaking resource existence.** For sensitive resources, return 404 instead of 403 so attackers cannot discover endpoints.
- **When 422 over 400?** 400 = syntactically invalid (bad JSON). 422 = syntactically valid, semantically wrong (invalid email). Some teams use only 400 for simplicity — the distinction matters when error handling differs for "can't parse" vs "parsed but invalid."

---

## 4. Headers

### 4.1 Rate Limiting Headers

```
RateLimit-Limit: 100          # Max requests per window
RateLimit-Remaining: 42       # Requests left
RateLimit-Reset: 1620000000   # Unix timestamp when window resets
```

On 429: include `Retry-After: 30` (seconds until retry).

**Key decisions:**
- **Algorithm:** Token bucket (allows bursts, most flexible) > sliding window > fixed window (allows 2x burst at boundaries).
- **Key:** API key or user ID for authenticated APIs. IP as fallback (unreliable behind NATs).
- **Distributed:** Redis + Lua scripts for atomic increment + TTL. Libraries like `rate-limiter-flexible`.

### 4.2 ETags and Conditional Requests

#### Optimistic Concurrency Control

```
GET /articles/123           → 200, ETag: "a1b2c3"
PUT /articles/123           → If-Match: "a1b2c3" → 200 (success) or 412 (conflict)
```

#### Conditional GET (Caching)

```
GET /articles/123           → 200, ETag: "a1b2c3"
GET /articles/123           → If-None-Match: "a1b2c3" → 304 (no body, saves bandwidth)
```

#### ETag Generation

```typescript
import { createHash } from 'crypto';
const etagFromBody = (body: string) => `"${createHash('md5').update(body).digest('hex')}"`;
const etagFromVersion = (v: number) => `"v${v}"`;           // Cheap, needs DB version column
const etagFromTimestamp = (d: Date) => `"${d.getTime()}"`;  // Less precise, simple
```

**Weak vs Strong:** Weak ETags (`W/"abc"`) indicate semantic equivalence. Strong ETags guarantee byte-for-byte identity. Use strong for `If-Match` (concurrency). Weak is fine for caching.

### 4.3 Content Negotiation

Most APIs only support JSON. The negotiation that matters in practice is **version negotiation** (if using header-based versioning) and **error format** (`application/problem+json`).

For multi-format support (JSON, XML, CSV), use a serializer layer keyed on the `Accept` header. Always default to JSON.

---

## 5. REST Constraints

### 5.1 Richardson Maturity Model

Four levels of REST adoption. Most production APIs sit at Level 2, and that is usually the right choice.

**Level 0 — The Swamp of POX:** Single endpoint, single method. `POST /api { "action": "getUser", "userId": 123 }`. This is RPC over HTTP.

**Level 1 — Resources:** Individual URIs (`/users/123`) but still only POST. Resources have identity, but HTTP semantics are ignored.

**Level 2 — HTTP Verbs:** Resources + correct methods + status codes. **This is the pragmatic target.** Level 2 APIs work with all tooling (caches, proxies, CDNs, monitoring) and have excellent OpenAPI support.

**Level 3 — Hypermedia Controls (HATEOAS):** Responses include links driving state transitions. This is "real" REST per Fielding's dissertation, but Fielding was describing the web (browsers following HTML links), not enterprise APIs consumed by typed clients.

**When Level 3 genuinely helps:** APIs with complex state machines where valid actions vary significantly by state (workflow engines, insurance claims, multi-step approval flows).

---

## 6. Long-Running Operations

### 6.1 202 Accepted + Polling

```
POST /reports { "type": "annual" }   → 202, Location: /operations/op-789
GET /operations/op-789               → 200, { "status": "processing", "progress": 45 }
GET /operations/op-789               → 200, { "status": "completed", "result": { "reportUrl": "..." } }
```

### 6.2 Webhooks

Client provides a `callbackUrl`. Server POSTs results when done. Sign payloads with HMAC-SHA256 and include a timestamp to prevent replay attacks.

| Aspect | Polling | Webhooks |
|--------|---------|----------|
| Client complexity | Low | High (must host endpoint) |
| Server complexity | Low | High (retry logic, delivery) |
| Latency | Poll interval | Near-immediate |
| Firewall-friendly | Yes | Client must accept inbound |

**Recommendation:** Support both. Polling is baseline. Webhooks are opt-in for low-latency needs.

---

## 7. Express vs Fastify vs Hono

| Aspect | Express | Fastify | Hono |
|--------|---------|---------|------|
| First release | 2010 | 2016 | 2021 |
| TypeScript | Bolted on (`@types/express`) | Native (since v4) | Native (TS-first) |
| Async error handling | Manual wrapper required* | Automatic | Automatic |
| Validation | BYO | Built-in (JSON Schema) | Built-in (Zod adapter) |
| JSON serialization | `JSON.stringify` | `fast-json-stringify` (2-5x faster) | `JSON.stringify` |
| OpenAPI integration | Manual / `swagger-jsdoc` | `@fastify/swagger` (from schemas) | `@hono/zod-openapi` |
| Plugin encapsulation | No (global middleware) | Yes (scoped plugins) | No (global middleware) |
| Runtime support | Node.js | Node.js | Node, Deno, Bun, Workers, Edge |
| Throughput (hello world) | ~15k req/s | ~75k req/s | ~80k req/s (Bun) / ~30k (Node) |
| Ecosystem size | Massive | Large | Growing |
| Best for | Brownfield, max ecosystem | Performance, schema-driven APIs | Edge/multi-runtime, minimal footprint |

*Express 5 fixes async error handling but adoption is still early.

**Quick decision:**
- **Existing project with Express?** Stay on Express (or upgrade to Express 5).
- **New Node.js API where performance and validation matter?** Fastify.
- **Edge-first, multi-runtime, or serverless?** Hono.

```typescript
// Hono: runs everywhere
import { Hono } from 'hono';
import { zValidator } from '@hono/zod-validator';
import { z } from 'zod';

const app = new Hono();
app.get('/users/:id',
  zValidator('param', z.object({ id: z.string().uuid() })),
  async (c) => {
    const { id } = c.req.valid('param'); // Typed
    return c.json(await getUser(id));
  }
);
export default app; // Works on Workers, Deno, Bun, Node
```

---

## 8. API Design Checklist

### Resource Design
- [ ] Plural nouns for collection resources
- [ ] Kebab-case for multi-word resources
- [ ] Maximum 2 levels of nesting
- [ ] Globally unique IDs (UUIDs) for top-level resources
- [ ] No verbs in URIs

### Request/Response
- [ ] Correct HTTP methods (no POST for everything)
- [ ] Appropriate status codes (not just 200 and 500)
- [ ] RFC 9457 Problem Details for errors
- [ ] Machine-readable error codes alongside human messages
- [ ] `Location` header on 201 Created
- [ ] `Retry-After` header on 429 and 503

### Security
- [ ] Authentication on all non-public endpoints
- [ ] 404 (not 403) for resources user should not know exist
- [ ] No stack traces in production error responses
- [ ] Rate limiting with proper headers
- [ ] Idempotency keys for non-idempotent writes
- [ ] Input validation and sanitization on all endpoints
- [ ] CORS configured correctly

### Caching and Performance
- [ ] ETags on frequently-read resources
- [ ] `Cache-Control` headers set appropriately
- [ ] Conditional requests supported (If-None-Match, If-Match)
- [ ] Bulk endpoints for batch operations
- [ ] 202 Accepted + polling for long-running operations

---

## Related Reading

- **Idempotency keys** (Section 2.3) require distributed locking, which is implemented with Redis in [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (cache stampede protection using `SET NX`)
- **Rate limiting headers** (Section 4.1) — the algorithms (token bucket, sliding window) are implemented in detail in [Auth & Security — Session Management and Validation](../05-auth-security/02-session-management-and-validation.md) and [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (Redis-backed rate limiter)
- **ETags and conditional requests** (Section 4.2) connect to caching strategies in [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (cache invalidation, CDN/edge caching)
- **Error handling and status codes** (Section 3) — the `AppError` pattern ties to [Module 00 — Error Handling Patterns](../00-ts-node-fundamentals.md#8-error-handling-patterns) and the RFC 9457 implementation in [API Design Patterns and Versioning](03-api-design-patterns-and-versioning.md)
- **Express vs Fastify vs Hono** (Section 7) — framework choice affects testing strategy in [Testing — Integration Testing and Mocking](../07-testing/02-integration-testing-and-mocking.md) (supertest patterns)
- **Resource modeling** (Section 1) — the sub-resource vs top-level decision maps directly to database schema design in [Database Patterns — Prisma and Drizzle](../06-database-patterns/01-prisma-and-drizzle.md)
- For the GraphQL alternative to REST, see [GraphQL — Schema Design and Resolvers](../04-graphql/01-schema-design-and-resolvers.md) and the decision framework in [API Design Patterns — GraphQL vs REST](03-api-design-patterns-and-versioning.md#7-graphql-vs-rest-decision-framework)
- For securing these endpoints, see [Auth & Security — JWT and OAuth2](../05-auth-security/01-jwt-and-oauth2.md)
