# Module 04: GraphQL — Deep Dive

> Execution internals, custom scalars and directives, schema evolution, real-time alternatives, and the GraphQL vs tRPC vs REST decision framework.

This covers what happens between the HTTP request and the JSON response. Read the README first.

---

## Table of Contents

1. [GraphQL Execution Algorithm](#1-graphql-execution-algorithm)
2. [Apollo Server Internals](#2-apollo-server-internals)
3. [Custom Scalars and Directives](#3-custom-scalars-and-directives)
4. [Schema Evolution and Deprecation](#4-schema-evolution-and-deprecation)
5. [Batched Queries and APQ](#5-batched-queries-and-apq)
6. [GraphQL Over HTTP Spec](#6-graphql-over-http-spec)
7. [Real-Time Alternatives](#7-real-time-alternatives)
8. [GraphQL vs tRPC vs REST](#8-graphql-vs-trpc-vs-rest)
9. [Performance Monitoring](#9-performance-monitoring)

---

## 1. GraphQL Execution Algorithm

### Phase 1: Parsing

The query string is parsed into an AST (`DocumentNode`) — pure syntax validation. Parsing is deterministic and cacheable; Apollo Server caches parsed documents keyed by query string. With persisted queries, cache hit rate approaches 100%.

### Phase 2: Validation

The AST is validated against the schema: field existence, argument types, fragment type compatibility, plus custom rules (depth limiting, complexity). Also cacheable for a given (schema, document) pair — each unique query validates once.

### Phase 3: Execution

Depth-first traversal of the selection set. Key behaviors:

- **Query fields execute in parallel. Mutation fields execute serially (in order).** This is per-spec.
- **Default resolver**: No resolver defined = `parent[fieldName]`.
- **Null propagation**: Non-null field resolves to null -> error propagates up to nearest nullable parent.
- **Error isolation**: One branch failing does not prevent other branches from resolving.

### Field Collection

Before execution, the engine merges duplicate field references (from fragments, aliases) into a single set. Two fragments selecting `name` with different sub-selections produce one resolver call for `name` with merged sub-selections.

### The `info` Object

`GraphQLResolveInfo` contains: `fieldName`, `fieldNodes` (AST), `returnType`, `parentType`, `path`, `schema`, `fragments`, `operation`, `variableValues`. Libraries like `graphql-parse-resolve-info` extract the selection set for query optimization — only join tables for fields the client actually requested.

---

## 2. Apollo Server Internals

### Plugin Architecture

Apollo Server 4 is built on lifecycle plugins. Each plugin hooks into the request pipeline:

```typescript
const myPlugin: ApolloServerPlugin<Context> = {
  async requestDidStart() {
    const start = Date.now();
    return {
      async parsingDidStart() { return async (err) => { /* after parse */ }; },
      async validationDidStart() { return async (errors) => { /* after validate */ }; },
      async executionDidStart() {
        return {
          willResolveField({ info }) {
            const fieldStart = Date.now();
            return (error, result) => {
              // Field-level tracing: Date.now() - fieldStart
            };
          },
        };
      },
      async willSendResponse({ response }) {
        // Total request duration: Date.now() - start
      },
    };
  },
};
```

### Request Pipeline

HTTP request -> context factory -> `requestDidStart` -> parse (cached) -> validate (cached) -> execute (resolver chain with `willResolveField` per field) -> format response -> `willSendResponse` -> HTTP response.

### Graceful Shutdown

`ApolloServerPluginDrainHttpServer` stops accepting new requests and waits for in-flight ones. For subscriptions, add a `drainServer` hook that calls `serverCleanup.dispose()`.

---

## 3. Custom Scalars and Directives

### Custom Scalars

The five built-in scalars (`Int`, `Float`, `String`, `Boolean`, `ID`) are never enough. A custom scalar defines three functions:

- **`serialize`**: Server -> client (internal value to wire format).
- **`parseValue`**: Client -> server from variables.
- **`parseLiteral`**: Client -> server from inline AST literals.

```typescript
const DateTimeScalar = new GraphQLScalarType({
  name: 'DateTime',
  serialize: (value: Date) => value.toISOString(),
  parseValue: (value: string) => new Date(value),
  parseLiteral: (ast) => ast.kind === Kind.STRING ? new Date(ast.value) : null,
});
```

Essential production scalars: `DateTime`, `JSON`/`JSONObject`, `BigInt`, `URL`, `EmailAddress`, `Money`/`Decimal`. The `graphql-scalars` library provides 50+ battle-tested implementations.

### Custom Directives

Schema directives modify behavior at the type system level. Implementation uses schema transforms:

```typescript
import { mapSchema, MapperKind, getDirective } from '@graphql-tools/utils';

function authDirectiveTransformer(schema: GraphQLSchema): GraphQLSchema {
  return mapSchema(schema, {
    [MapperKind.OBJECT_FIELD]: (fieldConfig) => {
      const auth = getDirective(schema, fieldConfig, 'auth')?.[0];
      if (auth) {
        const original = fieldConfig.resolve ?? defaultFieldResolver;
        fieldConfig.resolve = async (parent, args, ctx, info) => {
          if (ctx.user?.role !== auth.requires) throw new GraphQLError('Unauthorized');
          return original(parent, args, ctx, info);
        };
      }
      return fieldConfig;
    },
  });
}
```

Common directives: `@auth`/`@hasRole` (field authorization), `@cacheControl` (cache hints), `@deprecated` (built-in), `@rateLimit` (per-field limiting).

---

## 4. Schema Evolution and Deprecation

### Additive-Only Changes

GraphQL schemas evolve without versioning if you follow the rules.

**Non-breaking:** Adding fields, types, enum values, optional arguments, new queries/mutations, deprecating fields.

**Breaking:** Removing fields, changing types, making nullable fields non-null, removing enum values, adding required arguments.

### The Enum Trap

Adding an enum value is schema-safe but can break clients with exhaustive switches and no default case. Document that clients must handle unknown values.

### Deprecation Workflow

1. Add new field alongside old. Deprecate old with reason and target removal date.
2. Monitor deprecated field usage via field-level tracing (Apollo Studio/Hive).
3. Remove only after usage drops to zero or past the announced date.

### Schema Registry

In federated architectures, registries (Apollo GraphOS, Hive) track schema versions, validate composition on every change, detect breaking changes against real client operations, and maintain an audit trail.

---

## 5. Batched Queries and APQ

### Query Batching

Multiple operations in one HTTP request as a JSON array. Server returns an array of responses.

**Trade-offs:** Reduces HTTP round-trips but complicates error handling, defeats HTTP/2 multiplexing, and can overload a single server. HTTP/2 with individual requests usually wins. Use batching only for latency-constrained scenarios (mobile on slow networks).

### Automatic Persisted Queries (APQ)

1. Client sends SHA256 hash of query (no body).
2. Cache hit: server executes. Cache miss: server returns `PERSISTED_QUERY_NOT_FOUND`.
3. Client retries with hash + full query. Server caches and executes.

APQ is a **performance optimization**, not a security boundary — any client can register queries. For security, use registered persisted queries that reject unknown operations.

---

## 6. GraphQL Over HTTP Spec

The GraphQL Foundation spec standardizes the HTTP mapping:

- **POST** is standard. Body: `{ query, variables, operationName }`.
- **GET** allowed for queries (not mutations). Parameters URL-encoded.
- **Content-Type**: Request `application/json`, response `application/graphql-response+json`.
- **Status codes**: `200` for all valid GraphQL responses, even with errors. `4xx`/`5xx` reserved for HTTP-level failures (malformed JSON, server crash).

**Interview relevance:** Teams debate "should auth errors return 401 or go in the errors array?" The spec says: GraphQL errors in `errors` array with 200. HTTP errors use HTTP codes. Mixing leads to inconsistent client handling.

---

## 7. Real-Time Alternatives

### Live Queries

Server re-executes a query whenever underlying data changes and pushes the full result. Simpler than subscriptions (no event design) but more expensive (full re-execution). Implementations: `@n1ru4l/graphql-live-query`, Hasura.

### @defer and @stream

Incremental delivery directives. `@defer` sends expensive fields later; `@stream(initialCount: 10)` sends list items as they resolve.

**Transport:** `multipart/mixed` or SSE — standard HTTP, no WebSocket infrastructure needed. Apollo Server has experimental support; graphql-yoga has production support.

### Decision Matrix

| Mechanism | Best For | Transport | Cost |
|-----------|----------|-----------|------|
| Subscriptions | Discrete events (new message, status change) | WebSocket | Persistent connection per client |
| Live Queries | Reactive data (dashboards, counts) | WebSocket/SSE | Re-execution per change |
| @defer | Slow fields on fast queries | HTTP multipart | Single execution, chunked |
| @stream | Large lists, partial results useful | HTTP multipart | Single execution, chunked |
| Polling | Simple, low-frequency updates | HTTP | Repeated full execution |

---

## 8. GraphQL vs tRPC vs REST

### REST

**Choose when:** Public API, maximum cacheability, CRUD-shaped domain, multi-language clients, simplest debugging. **Weakness:** Over/under-fetching, painful versioning, no standard type contract.

### GraphQL

**Choose when:** Multiple clients need different data shapes, domain is a graph, large org needs unified API (federation), need field-level observability. **Weakness:** Complex caching, security surface, N+1 is your problem, file uploads are awkward.

### tRPC

**Choose when:** Full-stack TypeScript monorepo, internal API, want zero-codegen type safety, small fast-moving team. **Weakness:** TS-only, no external schema, unproven at large-org scale.

### Decision Matrix

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

## 9. Performance Monitoring

### Field-Level Tracing

Apollo Tracing records start time and duration per resolver. Instantly shows that `user.orders` takes 200ms while `user` takes 45ms.

### Apollo Studio / GraphOS

Operation signatures (normalized query grouping), field usage tracking, schema checks in CI, error rates per operation/field, p50/p95/p99 latencies.

### Self-Hosted: GraphQL Hive

Open-source alternative: schema registry, analytics, breaking change detection.

### Custom Plugin Approach

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

### Key Metrics

1. **Operation latency** (p50/p95/p99) per named operation.
2. **Resolver latency** per `Type.field`.
3. **Error rate** per operation and field.
4. **Cache hit rates**: DataLoader, APQ, CDN.
5. **Query complexity distribution**.
6. **Deprecated field usage** (migration progress).
7. **DataLoader batch size = 1** consistently = missed batching opportunity.

---

## Summary

The execution algorithm is deterministic and well-specified. Most production issues live in the resolver layer: N+1 queries, over-fetching, expensive computed fields without caching. Being able to walk through parse -> validate -> execute -> field collection -> null propagation in an interview is a genuine differentiator. Connecting that knowledge to practical concerns — why mutations execute serially, why DataLoader batches on `process.nextTick`, why nullable fields prevent cascading failures — demonstrates production experience beyond tutorial-level understanding.

The GraphQL vs tRPC vs REST question is near-guaranteed at staff level. Have a framework, not a preference. The best answer acknowledges each tool's strengths at specific architectural boundaries rather than declaring one universally superior.

Key internals to recall under pressure:
- Parse and validate are cached. Execution is the expensive phase.
- Custom scalars need `serialize`, `parseValue`, and `parseLiteral` — three distinct paths.
- Schema evolution is additive-only. Deprecate before removing. Monitor before deprecating.
- APQ is performance. Registered persisted queries are security. Know the difference.
