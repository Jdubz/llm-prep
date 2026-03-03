# 03 — Versioning, HATEOAS, Error Formats, OpenAPI, and Interview Q&A

> Assumes HTTP semantics (file 01) and pagination/filtering (file 02). Covers the design patterns that separate maintainable APIs from ones that accumulate technical debt.

---

## 1. Versioning

### 1.1 The Three Approaches

1. **URL path:** `GET /v1/users/123` — visible, cacheable, simple routing.
2. **Custom header:** `Api-Version: 2` — "more RESTful," harder to debug.
3. **Content negotiation:** `Accept: application/vnd.myapi.v2+json` — purist approach, poor CDN support.

### 1.2 Why Most Teams Choose URL Versioning

1. **Visibility.** Version in logs, address bars, curl commands.
2. **Routing.** Frameworks route on paths trivially; header routing needs middleware.
3. **Caching.** CDNs cache by URL. Header-based needs `Vary` config that many CDNs handle poorly.
4. **Documentation.** OpenAPI specs separate naturally by path.
5. **Client simplicity.** Base URL change is trivial vs custom header interceptors.

**Recommendation:** URL versioning. Version the entire API. Increment only for breaking changes. Maintain at most 2-3 concurrent versions.

### 1.3 What Constitutes a Breaking Change

| Breaking | Non-Breaking |
|----------|-------------|
| Removing/renaming a field | Adding a field/endpoint |
| Changing a field's type | Adding optional query parameters |
| Changing error format | Adding new enum values (usually) |
| Removing an endpoint | Relaxing validation |

### 1.4 Versioning and Compatibility Checklist

- [ ] API version in URL path (e.g., `/v1/`)
- [ ] Only breaking changes trigger version increment
- [ ] `Deprecation` and `Sunset` headers on deprecated endpoints
- [ ] Maximum 2-3 concurrent versions

---

## 2. HATEOAS

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

### 2.1 Why Almost Nobody Does It

1. **No client tooling.** No mainstream React/mobile library navigates HATEOAS links.
2. **Clients hardcode paths anyway.** SPAs and mobile apps are purpose-built, not generic browsers.
3. **Payload overhead.** Links in every response add up at scale.
4. **Documentation friction.** You document the links anyway, negating "discoverability."
5. **Versioning conflict.** If URLs contain versions, link-following breaks the abstraction.

### 2.2 When It Matters

- Long-lived APIs with thousands of diverse integrators (PayPal).
- Workflow-driven APIs where valid actions vary by state (insurance claims, approval flows).
- Internal APIs with a generic API browser tool.

For most APIs, spend the HATEOAS effort on good documentation instead.

### 2.3 The Pragmatic Middle Ground

Instead of full HATEOAS, many APIs include selective hypermedia:

```json
{
  "id": "inv-123",
  "status": "draft",
  "pdfUrl": "https://api.example.com/invoices/inv-123/pdf",
  "actions": ["send", "edit", "delete"]
}
```

The `actions` array communicates valid state transitions without requiring link navigation. This is "HATEOAS-lite" — pragmatic, easy to consume, and solves the actual problem.

### 2.4 Hypermedia Formats

- **HAL:** `_links` for references, `_embedded` for included resources. Most widely adopted. Simple but limited — cannot describe available methods or parameters.
- **JSON:API:** `links` and `relationships` as first-class concepts, plus standardized pagination, filtering, sparse fieldsets. Heavy but complete.
- **Siren:** Describes actions (methods, fields, content types) alongside links. Closest to self-describing. Almost nobody uses it.
- **Hydra (JSON-LD):** Semantic web approach. Extremely expressive but requires RDF/JSON-LD knowledge.

---

## 3. Error Response Design

### 3.1 RFC 9457 Problem Details (supersedes RFC 7807)

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

### 3.2 Validation Errors

Extend Problem Details with an `errors` array:

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains 2 validation errors.",
  "errors": [
    { "field": "email", "message": "Must be a valid email", "code": "INVALID_FORMAT" },
    { "field": "age", "message": "Must be at least 18", "code": "MIN_VALUE", "params": { "min": 18 } }
  ]
}
```

Machine-readable `code` fields let clients build localized messages and programmatic handling without parsing strings.

### 3.3 Implementation

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

## 4. OpenAPI and Code Generation

### 4.1 Code-First OpenAPI (Recommended for TypeScript)

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

### 4.2 Code-First vs Schema-First

| Aspect | Code-First | Schema-First |
|--------|-----------|--------------|
| Source of truth | Code | OpenAPI YAML/JSON |
| Drift risk | Low | High |
| Design review | Harder | Easier (review spec) |
| Cross-team contracts | Weaker | Stronger |
| TypeScript DX | Excellent | Good |
| Prototyping speed | Fast | Slower |

**Recommendation:** Code-first with Fastify/TypeBox or Hono/Zod. Generate the OpenAPI spec for docs and client generation. Use schema-first only when the contract must be agreed upon before implementation.

### 4.3 Client Generation

`openapi-typescript` + `openapi-fetch` gives end-to-end type safety without bulky generated code:

```typescript
import createClient from 'openapi-fetch';
import type { paths } from './api-types'; // Generated from spec

const client = createClient<paths>({ baseUrl: 'https://api.example.com' });
const { data, error } = await client.GET('/users/{id}', {
  params: { path: { id: '123' } },
});
// data and error are fully typed from the spec
```

### 4.4 Documentation Checklist

- [ ] OpenAPI spec generated from code
- [ ] Every endpoint documented with examples
- [ ] Error responses documented
- [ ] Rate limits documented
- [ ] Changelog maintained

---

## 5. API Gateway Patterns

### 5.1 Gateway as Cross-Cutting Concern Layer

```
Client -> API Gateway -> Service A / Service B / Service C

Gateway handles: auth, rate limiting, logging, CORS, request IDs, SSL, compression
```

**Key rule:** The gateway should be "dumb." It handles infrastructure concerns but contains NO business logic. The moment it starts transforming bodies or orchestrating multi-service calls, you have a distributed monolith bottleneck.

### 5.2 Backend for Frontend (BFF)

When different clients need fundamentally different API shapes:

```
Mobile App  -> Mobile BFF  -> Microservices
Web App     -> Web BFF     -> Microservices
Partner API -> Partner BFF -> Microservices
```

Each BFF is owned by the frontend team it serves. It aggregates, transforms, and optimizes for that client. **Trade-off:** More code and deployments, risk of duplicated logic. Mitigate with shared libraries or a thin shared domain gateway.

### 5.3 Gateway-Level Versioning

Route `/v1/users/123` to users-service v1, `/v2/users/123` to v2. Run multiple service versions simultaneously during migration. The gateway adds `Sunset` and `Deprecation` headers for deprecated versions.

---

## 6. JSON:API vs OData vs Custom

**JSON:API:** Standardized compound documents, relationships, sparse fieldsets (`?fields[articles]=title,body`). Avoids N+1 calls. Verbose envelope structure.

**OData:** Microsoft-originated, extremely powerful query language (`$filter`, `$expand`, `$select`). Strong .NET tooling. Complex. Node.js support is sparse.

**Custom (Stripe/GitHub/Twilio):** Tailored conventions, documented explicitly. Maximum flexibility, optimized for your consumers. No standard to lean on.

| If... | Choose... |
|-------|-----------|
| Standardized relationship handling needed | JSON:API |
| Microsoft/.NET ecosystem or advanced querying | OData |
| Public API, developer experience is paramount | Custom (Stripe-style) |
| Minimize convention bikeshedding | JSON:API |
| Internal API, 1-3 clients | Custom (keep it simple) |

For most Node.js/TypeScript teams, **custom with consistent conventions** provides the best DX-to-complexity ratio.

---

## 7. GraphQL vs REST Decision Framework

### 7.1 Choose REST When

- **Caching is critical.** Resource URLs map to HTTP caching naturally. GraphQL POSTs to one endpoint require app-level caching.
- **Resources map cleanly to CRUD.** REST is simpler for straightforward entity operations.
- **You need HTTP semantics.** Status codes, ETags, conditional requests, content negotiation.
- **File uploads are common.** REST handles multipart natively. GraphQL needs workarounds.
- **Consumers are diverse and external.** REST is universally understood.
- **Rate limiting is per-resource.** GraphQL's single endpoint requires query complexity analysis.

### 7.2 Choose GraphQL When

- **Clients need flexible data shapes.** Mobile (minimal) vs web (rich) for the same resources.
- **Deeply nested, interconnected data.** Social graphs, CMS with many relationships.
- **Over/under-fetching is a real problem.** Multiple REST calls vs one GraphQL query.
- **Rapid frontend iteration.** Frontend changes data requirements without backend changes.
- **You control both client and server.**

### 7.3 The Hybrid Pattern

```
External consumers -> REST API (versioned, documented, cached)
Internal frontends -> GraphQL BFF -> REST microservices
```

GraphQL as aggregation/shaping layer, not a replacement for REST between services.

---

## 8. Real-World API Design Case Studies

### 8.1 Stripe

- **Prefixed IDs** (`cus_`, `ch_`, `pi_`) and `object` field on every resource for type identification.
- **Idempotency keys** as first-class feature for safe POST retries.
- **Expandable responses** (`?expand[]=customer`) — clients embed related resources without extra calls.
- **Metadata hash** on every resource — eliminates "we need a custom field" requests.
- **Cursor pagination** with `has_more` and `starting_after`/`ending_before`.
- **Date-based versioning** (`Stripe-Version: 2023-10-16`), set per-account, overridable per-request. Internal compatibility layer transforms between versions — new code handles only the latest version.

### 8.2 GitHub REST API (v3)

- **Selective hypermedia.** `url` fields for navigation, not full HATEOAS.
- **ETags on every resource.** `If-None-Match` for efficient polling.
- **Clear rate limiting.** Separate limits for authenticated/unauthenticated. Secondary limits for abuse.
- **Link header pagination** following RFC 8288.
- **REST + GraphQL coexistence.** v3 REST for compatibility/caching, v4 GraphQL for complex queries.

### 8.3 Multi-Tenant SaaS API Design

- **Tenant from auth token** (not URL). Cleaner, prevents cross-tenant access at URL level. JWT contains `tenantId`; middleware injects it into every DB query.
- **UUIDs, not auto-increment.** Prevents information leakage and cross-tenant collisions.
- **Scoped API keys.** Bound to tenant, validated at gateway level.
- **Per-tenant rate limits.** Different tiers, enforced at gateway.
- **Audit logging.** Every mutation records `tenantId`, `userId`, `action`, `resourceId`, `timestamp`. Non-negotiable for enterprise SaaS.

### 8.4 Monolith-to-Microservices Migration (Strangler Fig)

1. Place API gateway in front of monolith. Route all traffic through it.
2. Extract one service. Route its paths to the new service.
3. Monolith handles everything else.
4. Repeat until monolith is empty.

**Critical:** The gateway must perfectly replicate the monolith's URL structure. Consumers should not notice the transition. Version bumps happen after migration, not during.

---

## 9. Interview Questions

### Design Questions

**Q: How do you model orders, line items, and products in an e-commerce API?**

Line items are sub-resources of orders (`/orders/123/line-items`). Products are top-level (`/products/456`). Line items embed a snapshot of product data (price, name) at order time because products change. This intentional denormalization is the key insight.

**Q: A client needs to create an order with 5 line items atomically. How?**

`POST /orders` with line items nested in the body. Atomic via DB transaction. Never require separate POSTs per line item — that forces partial failure handling on the client.

**Q: Mobile clients want minimal payloads; admin dashboards want everything. How?**

Options: field selection (`?fields=id,name`), expand (`?expand=orders,profile`), view pattern (`?view=compact`), or GraphQL. Trade-offs: field selection adds caching complexity; views are rigid but simple; GraphQL may be overkill for 2 clients.

**Q: Client requests `GET /users?page=100000&limit=20` on 10M records. Now what?**

Offset pagination is O(n) and will crush the DB. Options: (1) max offset limit returning 400, (2) cursor-based pagination as primary, (3) async export endpoint for "give me everything," (4) search engine for deep browse.

**Q: URL vs header versioning — make the case for each.**

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

### Key Takeaways

1. **Level 2 REST is the sweet spot.** Full HATEOAS is rarely worth the complexity.
2. **API gateways should be dumb routers** for cross-cutting concerns. No business logic.
3. **Backward compatibility is a discipline.** Plan from day one with additive-only changes and expand/contract.
4. **Code-first OpenAPI generation** fits TypeScript teams. The schema IS the code.
5. **GraphQL and REST are complementary.** REST for public/inter-service; GraphQL for flexible frontend consumption.
6. **Contract testing (Pact)** is the most valuable testing strategy for microservice architectures.
7. **Study production APIs** (Stripe, GitHub, Twilio). Their trade-offs under real constraints are more instructive than theoretical purity.
