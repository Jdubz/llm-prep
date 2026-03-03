# 03 — Persisted Queries, Complexity Limits, Caching, GraphQL vs REST, and Interview Q&A

> Assumes schema design (file 01) and DataLoader/federation patterns (file 02). Covers the security, performance, and architectural decisions that come up at staff-level interviews.

---

## 1. Security

### 1.1 Query Depth Limiting

Prevent deeply nested queries (friends-of-friends-of-friends attack):

```typescript
import depthLimit from 'graphql-depth-limit';
const server = new ApolloServer({ schema, validationRules: [depthLimit(10)] });
```

### 1.2 Query Cost Analysis

Assign costs to fields, reject queries exceeding a budget. Pagination arguments multiply cost. Use `graphql-query-complexity`.

### 1.3 Persisted Queries

**APQ (Automatic Persisted Queries):** Performance optimization — clients send hashes, server caches queries. Not a security boundary (any client can register queries).

1. Client sends SHA256 hash of query (no body).
2. Cache hit: server executes. Cache miss: server returns `PERSISTED_QUERY_NOT_FOUND`.
3. Client retries with hash + full query. Server caches and executes.

**Registered persisted queries**: Only pre-registered queries are allowed. Unknown queries rejected. This is the security measure. APQ is performance. Registered persisted queries are security. Know the difference.

### 1.4 Introspection

Disable in production: `introspection: process.env.NODE_ENV !== 'production'`.

### 1.5 Rate Limiting

Per-operation or per-complexity rate limiting. A query costing 500 points should consume more rate budget than one costing 5.

### 1.6 Security Checklist

| Threat | Solution | Tool |
|--------|----------|------|
| Deep nesting | Depth limit (10-15) | `graphql-depth-limit` |
| Expensive queries | Cost analysis + budget | `graphql-query-complexity` |
| Arbitrary queries | Registered persisted queries | Apollo APQ + allowlist |
| Schema exposure | Disable introspection in prod | `introspection: false` |
| Abuse | Cost-based rate limiting | Custom middleware |
| Auth | Context-level + field-level | Directives / guards |
| Batching abuse | Limit batch size or disable | Config flag |

---

## 2. GraphQL Execution Algorithm (Deep Dive)

### 2.1 Phase 1: Parsing

The query string is parsed into an AST (`DocumentNode`) — pure syntax validation. Parsing is deterministic and cacheable; Apollo Server caches parsed documents keyed by query string. With persisted queries, cache hit rate approaches 100%.

### 2.2 Phase 2: Validation

The AST is validated against the schema: field existence, argument types, fragment type compatibility, plus custom rules (depth limiting, complexity). Also cacheable for a given (schema, document) pair — each unique query validates once.

### 2.3 Phase 3: Execution

Depth-first traversal of the selection set. Key behaviors:

- **Query fields execute in parallel. Mutation fields execute serially (in order).** This is per-spec.
- **Default resolver**: No resolver defined = `parent[fieldName]`.
- **Null propagation**: Non-null field resolves to null -> error propagates up to nearest nullable parent.
- **Error isolation**: One branch failing does not prevent other branches from resolving.

### 2.4 Field Collection

Before execution, the engine merges duplicate field references (from fragments, aliases) into a single set. Two fragments selecting `name` with different sub-selections produce one resolver call for `name` with merged sub-selections.

### 2.5 The `info` Object

`GraphQLResolveInfo` contains: `fieldName`, `fieldNodes` (AST), `returnType`, `parentType`, `path`, `schema`, `fragments`, `operation`, `variableValues`. Libraries like `graphql-parse-resolve-info` extract the selection set for query optimization — only join tables for fields the client actually requested.

---

## 3. GraphQL Over HTTP Spec

The GraphQL Foundation spec standardizes the HTTP mapping:

- **POST** is standard. Body: `{ query, variables, operationName }`.
- **GET** allowed for queries (not mutations). Parameters URL-encoded.
- **Content-Type**: Request `application/json`, response `application/graphql-response+json`.
- **Status codes**: `200` for all valid GraphQL responses, even with errors. `4xx`/`5xx` reserved for HTTP-level failures (malformed JSON, server crash).

**Interview relevance:** Teams debate "should auth errors return 401 or go in the errors array?" The spec says: GraphQL errors in `errors` array with 200. HTTP errors use HTTP codes. Mixing leads to inconsistent client handling.

---

## 4. Batched Queries

Multiple operations in one HTTP request as a JSON array. Server returns an array of responses.

**Trade-offs:** Reduces HTTP round-trips but complicates error handling, defeats HTTP/2 multiplexing, and can overload a single server. HTTP/2 with individual requests usually wins. Use batching only for latency-constrained scenarios (mobile on slow networks).

---

## 5. Performance Monitoring

### 5.1 Field-Level Tracing

Apollo Tracing records start time and duration per resolver. Instantly shows that `user.orders` takes 200ms while `user` takes 45ms.

### 5.2 Apollo Studio / GraphOS

Operation signatures (normalized query grouping), field usage tracking, schema checks in CI, error rates per operation/field, p50/p95/p99 latencies.

### 5.3 Self-Hosted: GraphQL Hive

Open-source alternative: schema registry, analytics, breaking change detection.

### 5.4 Custom Plugin Approach

Export traces to your existing stack (Datadog, OpenTelemetry, Prometheus) via the `willResolveField` hook:

```typescript
willResolveField({ info }) {
  const start = process.hrtime.bigint();
  return () => {
    const ms = Number(process.hrtime.bigint() - start) / 1e6;
    metrics.histogram('graphql.field.duration', ms, {
      field: `${info.parentType.name}.${info.fieldName}`,
    });
  };
}
```

### 5.5 Key Metrics

1. **Operation latency** (p50/p95/p99) per named operation.
2. **Resolver latency** per `Type.field`.
3. **Error rate** per operation and field.
4. **Cache hit rates**: DataLoader, APQ, CDN.
5. **Query complexity distribution**.
6. **Deprecated field usage** (migration progress).
7. **DataLoader batch size = 1** consistently = missed batching opportunity.

---

## 6. GraphQL vs tRPC vs REST

### 6.1 REST

**Choose when:** Public API, maximum cacheability, CRUD-shaped domain, multi-language clients, simplest debugging. **Weakness:** Over/under-fetching, painful versioning, no standard type contract.

### 6.2 GraphQL

**Choose when:** Multiple clients need different data shapes, domain is a graph, large org needs unified API (federation), need field-level observability. **Weakness:** Complex caching, security surface, N+1 is your problem, file uploads are awkward.

### 6.3 tRPC

**Choose when:** Full-stack TypeScript monorepo, internal API, want zero-codegen type safety, small fast-moving team. **Weakness:** TS-only, no external schema, unproven at large-org scale.

### 6.4 Decision Matrix

| Factor | REST | GraphQL | tRPC |
|--------|------|---------|------|
| Public API | Best | Good | Poor |
| Multi-client | Moderate | Best | Poor |
| Type safety | Moderate (OpenAPI) | Good (codegen) | Best (native) |
| Caching | Best | Complex | Moderate |
| Federation / large org | Moderate | Best | Unproven |
| Full-stack TS monorepo | Good | Good | Best |

**Senior-level answer:** These are not mutually exclusive. Many orgs use GraphQL for client-facing, REST for service-to-service, tRPC for internal tooling. Pick the right tool per boundary.

---

## 7. Summary: Key Internals to Recall Under Pressure

- Parse and validate are cached. Execution is the expensive phase.
- Custom scalars need `serialize`, `parseValue`, and `parseLiteral` — three distinct paths.
- Schema evolution is additive-only. Deprecate before removing. Monitor before deprecating.
- APQ is performance. Registered persisted queries are security. Know the difference.
- DataLoader batches via `process.nextTick`. Per-request instances are non-negotiable.
- Null propagation: non-null fields failing cascade upward. Keep cross-service fields nullable.

---

## 8. Interview Questions

**Q: Add a `shippingAddress` field to `Order` — the address lives in a separate microservice. Walk through your schema design.**

Nullable (separate service), DataLoader for batching, consider federation entity extension, cache aggressively (addresses rarely change), degrade gracefully if service is down.

**Q: Interface vs union — when do you use each?**

Interfaces: shared meaningful fields queried polymorphically (`Node`, `Timestamped`). Unions: conceptually grouped but structurally different (`SearchResult`, `MutationResult`).

**Q: Explain DataLoader at the event loop level. Why per-request?**

Batches `.load()` calls within a single tick via `process.nextTick`. Cache has no TTL or auth boundary — shared loader = data leak across users.

**Q: Your GraphQL API is slow. Diagnose it.**

Field-level tracing to find slow resolvers. Check for N+1 (missing DataLoader). Check resolver over-fetching. Review query complexity. Consider response caching.

**Q: Splitting a monolith into federated subgraphs — where do you draw boundaries?**

DDD bounded contexts. One subgraph = one team's domain. Entity ownership is singular. Validate: "Can this subgraph deploy and reason independently?"

**Q: What happens at runtime when a federated query spans three subgraphs?**

Router builds a query plan, fetches root data from subgraph 1, sends `_entities` queries (potentially parallel) to subgraphs 2 and 3 with key fields, assembles the response.

**Q: How do you protect a public GraphQL API from abuse?**

Layered: (1) Persisted queries, (2) depth limiting, (3) cost analysis with per-user budgets, (4) cost-based rate limiting, (5) disable introspection, (6) resolver timeouts, (7) field-level auth.

**Q: Top-level errors vs union return types for mutations?**

Unions for domain errors (validation, business logic) — clients get exhaustive type checking. Top-level for infrastructure (auth, rate limiting) — handled generically. Be consistent.

**Q: Why do mutation fields execute serially while query fields execute in parallel?**

The spec mandates it. Mutations are side-effectful; order matters. Parallel mutations could create race conditions on shared state. Query fields are read-only (by convention), so parallel execution is safe and faster.

**Q: What is the difference between `@skip` and `@include`? Are they server-side or client-side?**

Both are client-side directives evaluated by the GraphQL engine at execution time. `@skip(if: true)` skips the field; `@include(if: false)` does not include it. Semantically complementary — neither is inherently safer or faster; use whichever makes your query logic more readable.

**Q: A DataLoader batch function returns results in a different order than the input keys. What breaks?**

Everything. DataLoader relies on position-based mapping — result[i] must correspond to keys[i]. Out-of-order results cause wrong data to be returned for wrong keys, often silently. Always sort results and map by key before returning.
