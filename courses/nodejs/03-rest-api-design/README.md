# Module 03: REST API Design

## Prerequisites

You have shipped production REST APIs. This module focuses on **design decisions and trade-offs**, not basics. We assume fluency with Express/Fastify, TypeScript, and databases.

---

## Table of Contents

1. [Resource Modeling](#resource-modeling)
2. [HTTP Method Semantics](#http-method-semantics)
3. [Status Codes](#status-codes)
4. [Pagination](#pagination)
5. [Filtering and Sorting](#filtering-and-sorting)
6. [Versioning](#versioning)
7. [HATEOAS](#hateoas)
8. [Error Response Design](#error-response-design)
9. [Content Negotiation](#content-negotiation)
10. [ETags and Conditional Requests](#etags-and-conditional-requests)
11. [Rate Limiting Headers](#rate-limiting-headers)
12. [Bulk Operations](#bulk-operations)
13. [Long-Running Operations](#long-running-operations)
14. [API Documentation](#api-documentation)
15. [Express vs Fastify vs Hono](#express-vs-fastify-vs-hono)
16. [Interview Questions](#interview-questions)

---

## Resource Modeling

### Naming Conventions

- **Plural nouns, always.** `/users`, `/orders`. `GET /users` and `GET /users/123` both read naturally.
- **Kebab-case for multi-word resources.** `/line-items`, not `/lineItems` or `/line_items`.
- **No verbs in URIs.** `/users/123/activate` is RPC wearing REST clothing. Use `PATCH /users/123` with `{ "status": "active" }`, or `POST /users/123/activations` for non-CRUD actions.

### Nesting Depth

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

### Sub-Resources vs Independent Resources

The key question: **does the child have meaning outside its parent?** An order line item does not -- keep it nested (`/orders/123/line-items`). A comment on a blog post might -- if you need a "recent comments" feed, make it top-level (`/comments?postId=123`).

**Singleton sub-resources** (exactly one per parent) drop the ID and use singular: `GET /users/123/profile`, `PUT /users/123/profile`.

---

## HTTP Method Semantics

| Method | Safe | Idempotent | Body | Typical Use |
|--------|------|------------|------|-------------|
| GET | Yes | Yes | No | Retrieve representation |
| HEAD | Yes | Yes | No | Retrieve headers only |
| POST | No | **No** | Yes | Create resource, trigger action |
| PUT | No | Yes | Yes | Full replacement |
| PATCH | No | **No*** | Yes | Partial update |
| DELETE | No | Yes | Optional | Remove resource |
| OPTIONS | Yes | Yes | No | CORS preflight, discovery |

*PATCH is not idempotent by spec, though JSON Merge Patch operations often are in practice.

### PUT vs PATCH

**PUT** replaces the entire resource. Omitted fields are removed. Simple, predictable, idempotent by definition.

**PATCH** updates only sent fields. Key questions: (1) What format -- JSON Merge Patch (RFC 7396) or JSON Patch (RFC 6902)? (2) With JSON Merge Patch, `null` means "remove this field" -- you cannot set a field to literal `null`. (3) JSON Patch (`add` to arrays) is not idempotent.

**Production recommendation:** Use JSON Merge Patch (`Content-Type: application/merge-patch+json`) for 95% of cases. Reserve JSON Patch for array manipulation.

### Idempotency for POST

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

## Status Codes

### The Ones That Matter

**2xx:** 200 (GET/PUT/PATCH success), 201 (POST created -- include `Location` header), 202 (async accepted), 204 (DELETE success, no body).

**4xx:** 400 (malformed syntax), 401 (no/invalid auth -- must include `WWW-Authenticate`), 403 (authenticated but not authorized), 404 (resource not found), 405 (method not allowed), 409 (conflict/duplicate), 410 (permanently deleted), 415 (wrong Content-Type), 422 (valid syntax, invalid semantics), 429 (rate limited -- include `Retry-After`).

**5xx:** 500 (unhandled exception -- never leak stack traces), 502 (upstream error), 503 (overloaded -- include `Retry-After`), 504 (upstream timeout).

### Common Misuses

- **200 for POST that created something.** Use 201.
- **400 as catch-all for client errors.** Use 422 for validation, 409 for conflicts, etc.
- **401 vs 403 confusion.** 401 = "who are you?" 403 = "I know who you are, and no."
- **404 for empty collections.** `GET /users/123/orders` where user has no orders is 200 with empty array, not 404. The collection resource exists; it is just empty.
- **403 leaking resource existence.** For sensitive resources, return 404 instead of 403 so attackers cannot discover endpoints.

---

## Pagination

### Offset-Based

```
GET /articles?offset=20&limit=10
```

**Pros:** Simple, random page access. **Cons:** Drift on insert/delete, O(n) performance at depth (`OFFSET 10000` still scans 10,010 rows), inconsistent totals between pages.

### Cursor-Based (Keyset)

```
GET /articles?cursor=eyJpZCI6MTAwfQ&limit=10
```

The cursor is an opaque base64-encoded token. Server decodes it into a `WHERE` clause:

```typescript
// Cursor decodes to: { createdAt: "2025-01-15T10:00:00Z", id: "abc123" }
const items = await db.query(`
  SELECT * FROM articles
  WHERE (created_at, id) < ($1, $2)
  ORDER BY created_at DESC, id DESC
  LIMIT $3
`, [cursor.createdAt, cursor.id, limit + 1]); // +1 to detect hasMore
```

**Why two fields?** Same-timestamp articles break single-field cursors. The tie-breaker (usually PK) ensures uniqueness.

**Pros:** Stable (no drift), O(1) at any depth, works for real-time feeds. **Cons:** No random page access, opaque cursors.

### Page Tokens (Google-Style)

Completely opaque tokens that can encode cursor position, filter state, and sort order. Maximum server flexibility to change pagination strategy without breaking clients.

### Comparison

| Aspect | Offset | Cursor/Keyset | Page Token |
|--------|--------|---------------|------------|
| Random access | Yes | No | No |
| Deep page performance | O(n) | O(1) | O(1) |
| Stability during writes | Unstable | Stable | Stable |
| Client complexity | Low | Medium | Low |
| Server flexibility | Low | Medium | High |

**Recommendation:** Cursor/keyset for anything large or mutable. Offset only when random page access is genuinely needed (admin dashboards with "go to page" UI).

---

## Filtering and Sorting

### Query Parameter Design

**Equality:** `GET /orders?status=shipped&customerId=123`

**Range filters (LHS brackets -- most common, used by Stripe/Shopify):**
```
GET /orders?createdAt[gte]=2025-01-01&createdAt[lt]=2025-02-01
```

Express's `qs` parses brackets by default. Fastify needs `querystringParser: (str) => qs.parse(str)`.

**Complex filters:** For OR logic or nested conditions, use `POST /orders/search` with a JSON body. This breaks REST purity but solves real problems (complex filters, saved searches, no URL length limits).

### Sorting

```
GET /articles?sort=-createdAt,title    # descending createdAt, then ascending title
```

The `-` prefix for descending comes from JSON:API. Always whitelist sortable fields:

```typescript
const SORTABLE = new Set(['createdAt', 'title', 'price']);
function parseSort(sort: string) {
  return sort.split(',').map((s) => {
    const desc = s.startsWith('-');
    const field = desc ? s.slice(1) : s;
    if (!SORTABLE.has(field)) throw new BadRequestError(`Cannot sort by "${field}"`);
    return { field, order: desc ? 'DESC' as const : 'ASC' as const };
  });
}
```

---

## Versioning

### The Three Approaches

1. **URL path:** `GET /v1/users/123` -- visible, cacheable, simple routing.
2. **Custom header:** `Api-Version: 2` -- "more RESTful," harder to debug.
3. **Content negotiation:** `Accept: application/vnd.myapi.v2+json` -- purist approach, poor CDN support.

### Why Most Teams Choose URL Versioning

1. **Visibility.** Version in logs, address bars, curl commands.
2. **Routing.** Frameworks route on paths trivially; header routing needs middleware.
3. **Caching.** CDNs cache by URL. Header-based needs `Vary` config that many CDNs handle poorly.
4. **Documentation.** OpenAPI specs separate naturally by path.
5. **Client simplicity.** Base URL change is trivial vs custom header interceptors.

**Recommendation:** URL versioning. Version the entire API. Increment only for breaking changes. Maintain at most 2-3 concurrent versions.

### What Constitutes a Breaking Change

| Breaking | Non-Breaking |
|----------|-------------|
| Removing/renaming a field | Adding a field/endpoint |
| Changing a field's type | Adding optional query parameters |
| Changing error format | Adding new enum values (usually) |
| Removing an endpoint | Relaxing validation |

---

## HATEOAS

Hypermedia as the Engine of Application State. Responses include links to related actions:

```json
{
  "id": 123, "status": "pending", "total": 99.99,
  "_links": {
    "self": { "href": "/orders/123" },
    "cancel": { "href": "/orders/123", "method": "DELETE" },
    "pay": { "href": "/orders/123/payments", "method": "POST" }
  }
}
```

### Why Almost Nobody Does It

1. **No client tooling.** No mainstream React/mobile library navigates HATEOAS links.
2. **Clients hardcode paths anyway.** SPAs and mobile apps are purpose-built, not generic browsers.
3. **Payload overhead.** Links in every response add up at scale.
4. **Documentation friction.** You document the links anyway, negating "discoverability."
5. **Versioning conflict.** If URLs contain versions, link-following breaks the abstraction.

### When It Matters

- Long-lived APIs with thousands of diverse integrators (PayPal).
- Workflow-driven APIs where valid actions vary by state (insurance claims, approval flows).
- Internal APIs with a generic API browser tool.

For most APIs, spend the HATEOAS effort on good documentation instead.

---

## Error Response Design

### RFC 9457 Problem Details (supersedes RFC 7807)

```json
{
  "type": "https://api.example.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance is $10.00 but the transaction requires $25.00.",
  "instance": "/payments/abc123",
  "balance": 10.00,
  "required": 25.00
}
```

Content-Type: `application/problem+json`. Custom extension fields (`balance`, `required`) are encouraged.

### Validation Errors

Extend Problem Details with an `errors` array:

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "errors": [
    { "field": "email", "message": "Must be a valid email", "code": "INVALID_FORMAT" },
    { "field": "age", "message": "Must be at least 18", "code": "MIN_VALUE", "params": { "min": 18 } }
  ]
}
```

Machine-readable `code` fields let clients build localized messages and programmatic handling without parsing strings.

### Implementation

```typescript
class ApiError extends Error {
  constructor(public readonly problem: { type: string; title: string; status: number; [k: string]: unknown }) {
    super(problem.title);
  }
  send(reply: FastifyReply) {
    reply.status(this.problem.status).header('content-type', 'application/problem+json').send(this.problem);
  }
}
```

---

## Content Negotiation

Most APIs only support JSON. The negotiation that matters in practice is **version negotiation** (if using header-based versioning) and **error format** (`application/problem+json`).

For multi-format support (JSON, XML, CSV), use a serializer layer keyed on the `Accept` header. Always default to JSON.

---

## ETags and Conditional Requests

### Optimistic Concurrency Control

```
GET /articles/123           → 200, ETag: "a1b2c3"
PUT /articles/123           → If-Match: "a1b2c3" → 200 (success) or 412 (conflict)
```

### Conditional GET (Caching)

```
GET /articles/123           → 200, ETag: "a1b2c3"
GET /articles/123           → If-None-Match: "a1b2c3" → 304 (no body, saves bandwidth)
```

### ETag Generation

```typescript
import { createHash } from 'crypto';
const etagFromBody = (body: string) => `"${createHash('md5').update(body).digest('hex')}"`;
const etagFromVersion = (v: number) => `"v${v}"`;           // Cheap, needs DB version column
const etagFromTimestamp = (d: Date) => `"${d.getTime()}"`;  // Less precise, simple
```

**Weak vs Strong:** Weak ETags (`W/"abc"`) indicate semantic equivalence. Strong ETags guarantee byte-for-byte identity. Use strong for `If-Match` (concurrency). Weak is fine for caching.

---

## Rate Limiting Headers

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

---

## Bulk Operations

**Three approaches:**

1. **Array body:** `POST /users` with `[{...}, {...}]`. Simple but: what if one fails?
2. **Batch endpoint:** `POST /batch` with per-item operations and per-item status codes in response.
3. **Bulk action:** `POST /users/bulk-delete` with `{ "ids": [1,2,3] }` and partial success reporting.

**Key decisions:**
- **Atomic or partial?** Atomic is simpler/safer. Partial is more performant but clients must handle mixed results.
- **Status code for partial success:** `207 Multi-Status` or `200` with per-item statuses. Never `201` if some failed.
- **Size limits:** Cap batch size (e.g., 100). Reject oversized with `413 Payload Too Large`.

---

## Long-Running Operations

### 202 Accepted + Polling

```
POST /reports { "type": "annual" }   → 202, Location: /operations/op-789
GET /operations/op-789               → 200, { "status": "processing", "progress": 45 }
GET /operations/op-789               → 200, { "status": "completed", "result": { "reportUrl": "..." } }
```

### Webhooks

Client provides a `callbackUrl`. Server POSTs results when done. Sign payloads with HMAC-SHA256 and include a timestamp to prevent replay attacks.

| Aspect | Polling | Webhooks |
|--------|---------|----------|
| Client complexity | Low | High (must host endpoint) |
| Server complexity | Low | High (retry logic, delivery) |
| Latency | Poll interval | Near-immediate |
| Firewall-friendly | Yes | Client must accept inbound |

**Recommendation:** Support both. Polling is baseline. Webhooks are opt-in for low-latency needs.

---

## API Documentation

### Code-First OpenAPI (Recommended for TypeScript)

The schema is the single source of truth for validation, serialization, types, and docs.

**Fastify + TypeBox:**
```typescript
import { Type } from '@sinclair/typebox';
const UserSchema = Type.Object({
  id: Type.String({ format: 'uuid' }),
  name: Type.String({ minLength: 1 }),
  email: Type.String({ format: 'email' }),
});
app.get('/users/:id', {
  schema: { params: Type.Object({ id: Type.String() }), response: { 200: UserSchema } },
  handler: async (req, reply) => { /* req.params.id is typed */ },
});
```

**Hono + Zod:**
```typescript
import { z } from 'zod';
const UserSchema = z.object({ id: z.string().uuid(), name: z.string(), email: z.string().email() });
```

Schema-first (write YAML, generate code) creates a maintenance gap. Code-first keeps spec and implementation in sync.

---

## Express vs Fastify vs Hono

| Aspect | Express | Fastify | Hono |
|--------|---------|---------|------|
| Release | 2010 | 2016 | 2021 |
| Architecture | Middleware chain | Plugin tree (encapsulated) | Middleware chain |
| TypeScript | `@types/express` (bolted on) | Native (since v4) | Native (TS-first) |
| Async errors | Manual wrapper* | Automatic | Automatic |
| Validation | BYO | Built-in (JSON Schema) | Zod adapter |
| Serialization | `JSON.stringify` | `fast-json-stringify` (2-5x faster) | `JSON.stringify` |
| OpenAPI | `swagger-jsdoc` | `@fastify/swagger` (schema-driven) | `@hono/zod-openapi` |
| Runtimes | Node.js | Node.js | Node, Deno, Bun, Workers, Edge |
| Throughput | ~15k req/s | ~75k req/s | ~80k req/s (Bun), ~30k (Node) |

*Express 5 (released 2024) fixes async errors, but adoption is still ramping up.

### When to Choose Each

**Express:** Massive ecosystem, team familiarity, brownfield projects.

**Fastify:** Performance matters, schema validation is core, you want plugin encapsulation (decorators/hooks scoped to plugins, not global). Batteries-included without NestJS weight.

**Hono:** Multi-runtime (Workers, Lambda@Edge, Deno Deploy, Node), edge-first (cold start matters), ~14KB core, Web Standards-based (Request/Response).

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

## Interview Questions

### Design Questions

**Q: How do you model orders, line items, and products in an e-commerce API?**

Line items are sub-resources of orders (`/orders/123/line-items`). Products are top-level (`/products/456`). Line items embed a snapshot of product data (price, name) at order time because products change. This intentional denormalization is the key insight.

**Q: A client needs to create an order with 5 line items atomically. How?**

`POST /orders` with line items nested in the body. Atomic via DB transaction. Never require separate POSTs per line item -- that forces partial failure handling on the client.

**Q: Mobile clients want minimal payloads; admin dashboards want everything. How?**

Options: field selection (`?fields=id,name`), expand (`?expand=orders,profile`), view pattern (`?view=compact`), or GraphQL. Trade-offs: field selection adds caching complexity; views are rigid but simple; GraphQL may be overkill for 2 clients.

### Trade-off Questions

**Q: When 422 over 400?**

400 = syntactically invalid (bad JSON). 422 = syntactically valid, semantically wrong (invalid email). Some teams use only 400 for simplicity -- the distinction matters when error handling differs for "can't parse" vs "parsed but invalid."

**Q: Client requests `GET /users?page=100000&limit=20` on 10M records. Now what?**

Offset pagination is O(n) and will crush the DB. Options: (1) max offset limit returning 400, (2) cursor-based pagination as primary, (3) async export endpoint for "give me everything," (4) search engine for deep browse.

**Q: URL vs header versioning -- make the case for each.**

URL: pragmatic (visible, cacheable, simple routing). Header: "more RESTful" (same URI = same resource). The real question: how often do you break compatibility? If rarely, URL with careful deprecation. If frequently, you have a design problem versioning won't solve.

**Q: Consumer reports duplicates when paginating while new items are inserted. Why? Fix?**

Offset pagination shifts when items insert before current offset. Fix: cursor/keyset pagination (stable position) or snapshot-based approach (only items existing at first page request).

### Coding Questions

**Q: RFC 7807 error handler for Fastify:**

```typescript
export function problemDetailsPlugin(app: FastifyInstance): void {
  app.setErrorHandler((error, request, reply) => {
    const status = error.statusCode ?? 500;
    const problem = {
      type: status >= 500 ? 'https://api.example.com/errors/internal' : error.code ?? 'about:blank',
      title: status >= 500 ? 'Internal Server Error' : error.message,
      status,
      detail: status >= 500 ? undefined : error.message,
      instance: request.url,
      ...(error.validation && {
        errors: error.validation.map((v) => ({
          field: v.instancePath.replace(/^\//, '').replace(/\//g, '.'),
          message: v.message,
          code: v.keyword?.toUpperCase(),
        })),
      }),
    };
    if (status >= 500) request.log.error(error);
    reply.status(status).header('content-type', 'application/problem+json').send(problem);
  });
}
```

**Q: Cursor-based pagination for Fastify:**

```typescript
function decodeCursor(cursor: string): { id: string; createdAt: string } {
  return JSON.parse(Buffer.from(cursor, 'base64url').toString());
}
function encodeCursor(item: { id: string; createdAt: Date }): string {
  return Buffer.from(JSON.stringify({ id: item.id, createdAt: item.createdAt.toISOString() })).toString('base64url');
}

app.get('/articles', {
  schema: { querystring: Type.Object({
    cursor: Type.Optional(Type.String()),
    limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 100, default: 20 })),
  })},
  handler: async (req, reply) => {
    const { cursor, limit = 20 } = req.query;
    let query = db.selectFrom('articles').orderBy('createdAt', 'desc').orderBy('id', 'desc').limit(limit + 1);
    if (cursor) {
      const c = decodeCursor(cursor);
      query = query.where(({ eb, and }) => and([eb('createdAt', '<=', new Date(c.createdAt)), eb('id', '<', c.id)]));
    }
    const items = await query.execute();
    const hasMore = items.length > limit;
    if (hasMore) items.pop();
    return reply.send({
      data: items,
      pagination: { hasMore, nextCursor: hasMore ? encodeCursor(items[items.length - 1]) : null },
    });
  },
});
```

---

## Further Reading

- [RFC 9110 - HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110) -- Definitive HTTP methods and status codes reference.
- [RFC 9457 - Problem Details](https://www.rfc-editor.org/rfc/rfc9457) -- Supersedes RFC 7807.
- [RFC 7396 - JSON Merge Patch](https://www.rfc-editor.org/rfc/rfc7396)
- [Google API Design Guide](https://cloud.google.com/apis/design) -- Battle-tested guidelines.
- [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines) -- Enterprise perspective.
- [Zalando RESTful API Guidelines](https://opensource.zalando.com/restful-api-guidelines/) -- Extremely detailed.
- [Stripe API Reference](https://stripe.com/docs/api) -- Gold standard for developer experience.
