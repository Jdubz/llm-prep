# Module 03 Deep Dive: REST API Design -- Advanced Topics

## Table of Contents

1. [Richardson Maturity Model](#richardson-maturity-model)
2. [Hypermedia APIs in Practice](#hypermedia-apis-in-practice)
3. [API Gateway Patterns](#api-gateway-patterns)
4. [Backward Compatibility Strategies](#backward-compatibility-strategies)
5. [API Deprecation Lifecycle](#api-deprecation-lifecycle)
6. [OpenAPI Code Generation](#openapi-code-generation)
7. [JSON:API vs OData vs Custom](#jsonapi-vs-odata-vs-custom)
8. [GraphQL vs REST Decision Framework](#graphql-vs-rest-decision-framework)
9. [API Testing Strategies](#api-testing-strategies)
10. [Real-World API Design Case Studies](#real-world-api-design-case-studies)

---

## Richardson Maturity Model

Four levels of REST adoption. Most production APIs sit at Level 2, and that is usually the right choice.

**Level 0 -- The Swamp of POX:** Single endpoint, single method. `POST /api { "action": "getUser", "userId": 123 }`. This is RPC over HTTP. The only HTTP feature used is transport.

**Level 1 -- Resources:** Individual URIs (`/users/123`) but still only POST. Resources have identity, but HTTP semantics are ignored.

**Level 2 -- HTTP Verbs:** Resources + correct methods + status codes. `GET /users/123 -> 200`, `POST /orders -> 201`, `DELETE /orders/456 -> 204`. **This is the pragmatic target.** Level 2 APIs work with all tooling (caches, proxies, CDNs, monitoring) and have excellent OpenAPI support.

**Level 3 -- Hypermedia Controls (HATEOAS):** Responses include links driving state transitions. This is "real" REST per Fielding's dissertation, but Fielding was describing the web (browsers following HTML links), not enterprise APIs consumed by typed clients. API consumers are purpose-built and benefit more from documentation than runtime discovery.

**When Level 3 genuinely helps:** APIs with complex state machines where valid actions vary significantly by state (workflow engines, insurance claims, multi-step approval flows).

---

## Hypermedia APIs in Practice

### Formats

- **HAL:** `_links` for references, `_embedded` for included resources. Most widely adopted. Simple but limited -- cannot describe available methods or parameters.
- **JSON:API:** `links` and `relationships` as first-class concepts, plus standardized pagination, filtering, sparse fieldsets. Heavy but complete.
- **Siren:** Describes actions (methods, fields, content types) alongside links. Closest to self-describing. Almost nobody uses it.
- **Hydra (JSON-LD):** Semantic web approach. Extremely expressive but requires RDF/JSON-LD knowledge.

### The Pragmatic Middle Ground

Instead of full HATEOAS, many APIs include selective hypermedia:

```json
{
  "id": "inv-123",
  "status": "draft",
  "pdfUrl": "https://api.example.com/invoices/inv-123/pdf",
  "actions": ["send", "edit", "delete"]
}
```

The `actions` array communicates valid state transitions without requiring link navigation. This is "HATEOAS-lite" -- pragmatic, easy to consume, and solves the actual problem.

---

## API Gateway Patterns

### Gateway as Cross-Cutting Concern Layer

```
Client -> API Gateway -> Service A / Service B / Service C

Gateway handles: auth, rate limiting, logging, CORS, request IDs, SSL, compression
```

**Key rule:** The gateway should be "dumb." It handles infrastructure concerns but contains NO business logic. The moment it starts transforming bodies or orchestrating multi-service calls, you have a distributed monolith bottleneck.

### Backend for Frontend (BFF)

When different clients need fundamentally different API shapes:

```
Mobile App  -> Mobile BFF  -> Microservices
Web App     -> Web BFF     -> Microservices
Partner API -> Partner BFF -> Microservices
```

Each BFF is owned by the frontend team it serves. It aggregates, transforms, and optimizes for that client. **Trade-off:** More code and deployments, risk of duplicated logic. Mitigate with shared libraries or a thin shared domain gateway.

### Gateway-Level Versioning

Route `/v1/users/123` to users-service v1, `/v2/users/123` to v2. Run multiple service versions simultaneously during migration. The gateway adds `Sunset` and `Deprecation` headers for deprecated versions.

---

## Backward Compatibility Strategies

### Robustness Principle (Postel's Law)

Servers ignore unknown request fields (forward-compatible). Clients ignore unknown response fields. Servers never remove response fields or add required request fields without a version bump.

### Additive-Only Changes

Adding fields and endpoints is non-breaking. Removing, renaming, or changing types of existing fields is breaking.

### Expand/Contract Pattern

For field renames, use three phases:

1. **Expand:** Return both old and new fields. Accept both in requests.
2. **Deprecate:** Document old field as deprecated, add `Deprecation` header, notify consumers.
3. **Contract:** Remove old field in a new API version.

The expand phase can last weeks or months depending on consumer base.

### Tolerant Reader Pattern

Clients should extract only needed fields and ignore everything else:

```typescript
// BAD: strict validation breaks on new fields
const user = UserSchemaStrict.parse(response.data);

// GOOD: permissive parsing or selective extraction
const user = UserSchemaPermissive.parse(response.data); // .passthrough() in Zod
```

---

## API Deprecation Lifecycle

### Timeline

```
Month 0:  Announce + add `Deprecation` and `Sunset` headers
Month 1:  Deprecation warnings in developer portal
Month 3:  Return `Warning: 299 - "Deprecated"` header
Month 6:  (Optional) Reduce rate limits on deprecated endpoint
Month 9:  Return 410 Gone or redirect
Month 12: Decommission
```

### HTTP Headers

```
Deprecation: Sat, 01 Mar 2025 00:00:00 GMT      # RFC draft: when deprecated
Sunset: Sat, 01 Sep 2025 00:00:00 GMT            # RFC 8594: when it stops working
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

### Monitoring

Before decommissioning, track who still calls the old endpoint. Log API key / consumer identity on every deprecated endpoint call to plan decommission timing.

---

## OpenAPI Code Generation

### Client-Side (Recommended)

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

### Server-Side

Generate stubs from spec with `openapi-generator-cli`. **Pros:** Contract-first design. **Cons:** Generated code is awkward, spec drifts from implementation, types are often `any`-heavy.

### Code-First vs Schema-First

| Aspect | Code-First | Schema-First |
|--------|-----------|--------------|
| Source of truth | Code | OpenAPI YAML/JSON |
| Drift risk | Low | High |
| Design review | Harder | Easier (review spec) |
| Cross-team contracts | Weaker | Stronger |
| TypeScript DX | Excellent | Good |
| Prototyping speed | Fast | Slower |

**Recommendation:** Code-first with Fastify/TypeBox or Hono/Zod. Generate the OpenAPI spec for docs and client generation. Use schema-first only when the contract must be agreed upon before implementation.

---

## JSON:API vs OData vs Custom

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

## GraphQL vs REST Decision Framework

### Choose REST When

- **Caching is critical.** Resource URLs map to HTTP caching naturally. GraphQL POSTs to one endpoint require app-level caching.
- **Resources map cleanly to CRUD.** REST is simpler for straightforward entity operations.
- **You need HTTP semantics.** Status codes, ETags, conditional requests, content negotiation.
- **File uploads are common.** REST handles multipart natively. GraphQL needs workarounds.
- **Consumers are diverse and external.** REST is universally understood.
- **Rate limiting is per-resource.** GraphQL's single endpoint requires query complexity analysis.

### Choose GraphQL When

- **Clients need flexible data shapes.** Mobile (minimal) vs web (rich) for the same resources.
- **Deeply nested, interconnected data.** Social graphs, CMS with many relationships.
- **Over/under-fetching is a real problem.** Multiple REST calls vs one GraphQL query.
- **Rapid frontend iteration.** Frontend changes data requirements without backend changes.
- **You control both client and server.**

### The Hybrid Pattern

```
External consumers -> REST API (versioned, documented, cached)
Internal frontends -> GraphQL BFF -> REST microservices
```

GraphQL as aggregation/shaping layer, not a replacement for REST between services.

---

## API Testing Strategies

### The Testing Pyramid

Unit (handler logic, no HTTP) -> Contract (Pact, schema validation) -> Integration (real HTTP, test DB) -> E2E (full environment).

### Contract Testing with Pact

Consumer writes expectations; provider verifies them independently. No need to run both services simultaneously.

```typescript
// Consumer side
await provider
  .given('user 123 exists')
  .uponReceiving('a request for user 123')
  .withRequest({ method: 'GET', path: '/users/123' })
  .willRespondWith({
    status: 200,
    body: MatchersV3.like({ id: '123', name: MatchersV3.string(), email: MatchersV3.email() }),
  })
  .executeTest(async (mockServer) => {
    const user = await new UserClient(mockServer.url).getUser('123');
    expect(user.id).toBe('123');
  });

// Provider side
const verifier = new Verifier({
  providerBaseUrl: 'http://localhost:3000',
  pactUrls: ['./pacts/orderservice-userservice.json'],
  stateHandlers: {
    'user 123 exists': () => db.users.create({ id: '123', name: 'Jane', email: 'jane@test.com' }),
  },
});
await verifier.verifyProvider();
```

**Why it matters at scale:** With 20 microservices, E2E tests are slow and flaky. Contract tests verify compatibility independently, run fast, and pinpoint exactly which service broke the contract.

### Schema Validation Testing

Validate actual responses conform to your OpenAPI spec using `jest-openapi` or `chai-openapi-response-validator`. Catches drift between implementation and documentation.

### Snapshot Testing

Catches unintended response shape changes but is brittle. Remove volatile fields (`createdAt`, `updatedAt`) before snapshotting. Pair with contract tests for cross-service guarantees.

---

## Real-World API Design Case Studies

### Stripe

- **Prefixed IDs** (`cus_`, `ch_`, `pi_`) and `object` field on every resource for type identification.
- **Idempotency keys** as first-class feature for safe POST retries.
- **Expandable responses** (`?expand[]=customer`) -- clients embed related resources without extra calls.
- **Metadata hash** on every resource -- eliminates "we need a custom field" requests.
- **Cursor pagination** with `has_more` and `starting_after`/`ending_before`.
- **Date-based versioning** (`Stripe-Version: 2023-10-16`), set per-account, overridable per-request. Internal compatibility layer transforms between versions -- new code handles only the latest version.

### GitHub REST API (v3)

- **Selective hypermedia.** `url` fields for navigation, not full HATEOAS.
- **ETags on every resource.** `If-None-Match` for efficient polling.
- **Clear rate limiting.** Separate limits for authenticated/unauthenticated. Secondary limits for abuse.
- **Link header pagination** following RFC 8288.
- **REST + GraphQL coexistence.** v3 REST for compatibility/caching, v4 GraphQL for complex queries.

### Multi-Tenant SaaS API Design

- **Tenant from auth token** (not URL). Cleaner, prevents cross-tenant access at URL level. JWT contains `tenantId`; middleware injects it into every DB query.
- **UUIDs, not auto-increment.** Prevents information leakage and cross-tenant collisions.
- **Scoped API keys.** Bound to tenant, validated at gateway level.
- **Per-tenant rate limits.** Different tiers, enforced at gateway.
- **Audit logging.** Every mutation records `tenantId`, `userId`, `action`, `resourceId`, `timestamp`. Non-negotiable for enterprise SaaS.

### Monolith-to-Microservices Migration (Strangler Fig)

1. Place API gateway in front of monolith. Route all traffic through it.
2. Extract one service. Route its paths to the new service.
3. Monolith handles everything else.
4. Repeat until monolith is empty.

**Critical:** The gateway must perfectly replicate the monolith's URL structure. Consumers should not notice the transition. Version bumps happen after migration, not during.

---

## Key Takeaways

1. **Level 2 REST is the sweet spot.** Full HATEOAS is rarely worth the complexity.
2. **API gateways should be dumb routers** for cross-cutting concerns. No business logic.
3. **Backward compatibility is a discipline.** Plan from day one with additive-only changes and expand/contract.
4. **Code-first OpenAPI generation** fits TypeScript teams. The schema IS the code.
5. **GraphQL and REST are complementary.** REST for public/inter-service; GraphQL for flexible frontend consumption.
6. **Contract testing (Pact)** is the most valuable testing strategy for microservice architectures.
7. **Study production APIs** (Stripe, GitHub, Twilio). Their trade-offs under real constraints are more instructive than theoretical purity.
