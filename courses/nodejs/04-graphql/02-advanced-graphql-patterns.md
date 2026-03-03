# 02 — DataLoader, N+1, Fragments, Directives, and Federation Basics

> Assumes schema design and resolver fundamentals from file 01. Covers the patterns that make production GraphQL fast, maintainable, and scalable across teams.

---

## 1. DataLoader and the N+1 Problem

### 1.1 The Problem

50 users with a `company` field = 1 query for users + 50 queries for companies. DataLoader collects all `.load(key)` calls within a single event loop tick, then executes one batched call.

```typescript
const companyLoader = new DataLoader<string, Company>(async (ids) => {
  const companies = await db.companies.findMany({ where: { id: { in: [...ids] } } });
  const map = new Map(companies.map((c) => [c.id, c]));
  // MUST return same length and order as input keys
  return ids.map((id) => map.get(id) ?? new Error(`Company ${id} not found`));
});
```

### 1.2 The Batch Contract

1. Receives an array of keys.
2. Returns an array of the **same length**.
3. Results in the **same order** as keys.
4. Individual elements can be `Error` instances.

Violating any of these causes subtle, hard-to-debug issues.

### 1.3 Per-Request Instances Are Mandatory

DataLoader caches by default with no TTL and no auth boundaries. A shared loader leaks data across users.

```typescript
function createLoaders(db: PrismaClient) {
  return {
    user: new DataLoader<string, User>(async (ids) => {
      const rows = await db.user.findMany({ where: { id: { in: [...ids] } } });
      const map = new Map(rows.map((r) => [r.id, r]));
      return ids.map((id) => map.get(id) ?? new Error(`Not found: ${id}`));
    }),
    ordersByUser: new DataLoader<string, Order[]>(async (userIds) => {
      const orders = await db.order.findMany({ where: { userId: { in: [...userIds] } } });
      const grouped = new Map<string, Order[]>();
      for (const o of orders) (grouped.get(o.userId) ?? grouped.set(o.userId, []).get(o.userId)!).push(o);
      return userIds.map((id) => grouped.get(id) ?? []);
    }),
  };
}
// Context: loaders: createLoaders(prisma) — FRESH per request, never shared
```

### 1.4 At the Event Loop Level

DataLoader batches `.load()` calls by scheduling the batch function with `process.nextTick`. All `.load()` calls in the current synchronous execution are collected, then the batch function fires on the next tick.

### 1.5 Advanced Patterns

**Composite keys** use `cacheKeyFn` to serialize object keys:

```typescript
const loader = new DataLoader<{ userId: string; role: string }, Permission[]>(
  async (keys) => { /* batch fn */ },
  { cacheKeyFn: (key) => `${key.userId}:${key.role}` }
);
```

**Cache priming** with `.prime(key, value)` avoids redundant loads when you already have the data:

```typescript
const users = await db.user.findMany({ where: { tenantId } });
for (const user of users) {
  ctx.loaders.user.prime(user.id, user); // Pre-populate cache
}
```

---

## 2. Fragments and Directives

### 2.1 Fragments

Fragments are reusable field sets. They eliminate repetition in client queries and are the building blocks for component-based data fetching (Relay, Apollo's `useFragment`).

```graphql
fragment UserFields on User {
  id
  email
  displayName
  avatar { url }
}

query GetUsers {
  users {
    ...UserFields
    role
  }
}
```

### 2.2 Inline Fragments for Polymorphism

```graphql
query Search($term: String!) {
  search(term: $term) {
    __typename
    ... on User { id email }
    ... on Post { id title publishedAt }
    ... on Product { id sku price }
  }
}
```

### 2.3 Built-in Directives

```graphql
query GetUser($id: ID!, $includeOrders: Boolean!, $skipProfile: Boolean!) {
  user(id: $id) {
    id
    email
    orders @include(if: $includeOrders) { id total }
    profile @skip(if: $skipProfile) { bio }
  }
}
```

`@include(if: Boolean!)` — include field only if true.
`@skip(if: Boolean!)` — skip field if true.
`@deprecated(reason: String)` — marks field/enum value deprecated.
`@specifiedBy(url: String!)` — provides spec URL for custom scalars.

### 2.4 Custom Directives

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

## 3. Federation and Schema Stitching

Schema stitching (legacy) merges schemas at the gateway. **Apollo Federation v2** is the modern approach.

### 3.1 How It Works

Each subgraph owns part of the graph. The **router** (Apollo Router) composes subgraph schemas into a supergraph.

```graphql
# Users subgraph — owns User
type User @key(fields: "id") { id: ID!  email: String!  displayName: String! }

# Orders subgraph — extends User
type User @key(fields: "id") { id: ID!  orders: [Order!]! }
```

### 3.2 Entity Resolvers

The router sends `_entities` queries with key fields. Subgraphs implement `__resolveReference`:

```typescript
User: {
  __resolveReference: (ref: { id: string }, ctx) => ctx.loaders.user.load(ref.id),
}
```

Always use DataLoader in `__resolveReference`. The router may fan out to the same subgraph for many entity keys in a single query.

### 3.3 Key Directives

| Directive | Purpose |
|---|---|
| `@key` | Entity primary key — marks a type as an entity with the given field(s) as the key |
| `@shareable` | Field/type can be resolved by multiple subgraphs |
| `@external` | Field defined in another subgraph |
| `@requires` | Subgraph needs external fields to resolve this field |
| `@provides` | Performance hint: this subgraph can provide listed fields (avoids extra `_entities` call) |
| `@override` | Migrate a field from one subgraph to another |

### 3.4 Federation Entity Template (Cheat Sheet)

```graphql
# Users subgraph                              # Orders subgraph
type User @key(fields: "id") {                type User @key(fields: "id") {
  id: ID!  email: String!                       id: ID!  orders: [Order!]!
}                                             }
```

```typescript
// Entity resolver — always use DataLoader
User: { __resolveReference: (ref, ctx) => ctx.loaders.user.load(ref.id) }
```

### 3.5 Subgraph Design Principles

1. Map to bounded contexts, not tables.
2. One subgraph owns the canonical entity definition; others extend.
3. Minimize cross-subgraph `@requires` chains — each chain adds a network hop.
4. Each subgraph deploys independently; CI composition checks catch breaks.
5. Schema registry (Apollo GraphOS, Hive) validates composition on every change.

---

## 4. Custom Scalars

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

---

## 5. Schema Evolution and Deprecation

### 5.1 Additive-Only Changes

GraphQL schemas evolve without versioning if you follow the rules.

**Non-breaking:** Adding fields, types, enum values, optional arguments, new queries/mutations, deprecating fields.

**Breaking:** Removing fields, changing types, making nullable fields non-null, removing enum values, adding required arguments.

### 5.2 The Enum Trap

Adding an enum value is schema-safe but can break clients with exhaustive switches and no default case. Document that clients must handle unknown values.

### 5.3 Deprecation Workflow

1. Add new field alongside old. Deprecate old with reason and target removal date.
2. Monitor deprecated field usage via field-level tracing (Apollo Studio/Hive).
3. Remove only after usage drops to zero or past the announced date.

### 5.4 Schema Registry

In federated architectures, registries (Apollo GraphOS, Hive) track schema versions, validate composition on every change, detect breaking changes against real client operations, and maintain an audit trail.

---

## 6. Caching Strategies

### 6.1 CDN Caching

Registered persisted queries + `GET` requests = CDN-cacheable GraphQL. Set per-field cache hints with `info.cacheControl.setCacheHint({ maxAge: 300, scope: 'PUBLIC' })`.

### 6.2 Normalized Client Cache

Apollo Client, urql, and Relay store entities by `__typename + id`. Mutations returning updated entities auto-update the cache everywhere. Requires consistent `id` fields and mutations that return full objects.

### 6.3 Server-Side: DataLoader + Redis

DataLoader handles per-request caching. For cross-request caching, layer Redis in front:

```typescript
const userLoader = new DataLoader<string, User>(async (ids) => {
  const cached = await redis.mget(ids.map((id) => `user:${id}`));
  const missing = ids.filter((_, i) => !cached[i]);
  const fresh = missing.length
    ? await db.user.findMany({ where: { id: { in: missing } } })
    : [];
  await Promise.all(fresh.map((u) => redis.set(`user:${u.id}`, JSON.stringify(u), 'EX', 300)));
  const freshMap = new Map(fresh.map((u) => [u.id, u]));
  return ids.map((id, i) =>
    cached[i] ? JSON.parse(cached[i] as string) : freshMap.get(id) ?? new Error(`Not found`)
  );
});
```

---

## 7. Real-Time Alternatives

### 7.1 Live Queries

Server re-executes a query whenever underlying data changes and pushes the full result. Simpler than subscriptions (no event design) but more expensive (full re-execution). Implementations: `@n1ru4l/graphql-live-query`, Hasura.

### 7.2 @defer and @stream

Incremental delivery directives. `@defer` sends expensive fields later; `@stream(initialCount: 10)` sends list items as they resolve.

**Transport:** `multipart/mixed` or SSE — standard HTTP, no WebSocket infrastructure needed. Apollo Server has experimental support; graphql-yoga has production support.

### 7.3 Decision Matrix

| Mechanism | Best For | Transport | Cost |
|-----------|----------|-----------|------|
| Subscriptions | Discrete events (new message, status change) | WebSocket | Persistent connection per client |
| Live Queries | Reactive data (dashboards, counts) | WebSocket/SSE | Re-execution per change |
| @defer | Slow fields on fast queries | HTTP multipart | Single execution, chunked |
| @stream | Large lists, partial results useful | HTTP multipart | Single execution, chunked |
| Polling | Simple, low-frequency updates | HTTP | Repeated full execution |

---

## 8. Apollo Server Internals

### 8.1 Plugin Architecture

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

### 8.2 Request Pipeline

HTTP request -> context factory -> `requestDidStart` -> parse (cached) -> validate (cached) -> execute (resolver chain with `willResolveField` per field) -> format response -> `willSendResponse` -> HTTP response.

### 8.3 Graceful Shutdown

`ApolloServerPluginDrainHttpServer` stops accepting new requests and waits for in-flight ones. For subscriptions, add a `drainServer` hook that calls `serverCleanup.dispose()`.

**Common mistake with graceful shutdown and subscriptions:** Teams often forget that `ApolloServerPluginDrainHttpServer` only handles HTTP requests, not WebSocket connections. If you have subscriptions, you must separately drain WebSocket connections via `serverCleanup.dispose()` — otherwise, connected clients experience abrupt disconnections during deployments. Pair this with a `connection_terminate` message to give clients a chance to reconnect.

---

## Related Reading

- **DataLoader and N+1** (Section 1) — the N+1 problem is the GraphQL version of the same pattern in [Database Patterns — Queries, Transactions, and Optimization](../06-database-patterns/02-queries-transactions-and-optimization.md) (N+1 detection, query optimization)
- **DataLoader event loop batching** (Section 1.4) relies on `process.nextTick` covered in [Node.js Runtime — Event Loop and Task Queues](../02-node-runtime/01-event-loop-and-task-queues.md) (microtask queue, nextTick behavior)
- **Federation entity resolvers** (Section 3) — subgraph boundaries map to DDD bounded contexts discussed in [Architecture — Clean Architecture and DDD](../09-architecture-patterns/01-clean-architecture-and-ddd.md)
- **Server-side caching with Redis** (Section 6.3) — the Redis caching layer in front of DataLoader connects to [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (cache-aside pattern, TTL guidelines)
- **Custom directives** (Section 2.4) — the `@auth` directive pattern is related to field-level authorization in [Auth & Security — JWT and OAuth2](../05-auth-security/01-jwt-and-oauth2.md)
- **Real-time alternatives** (Section 7) — SSE and streaming connect to [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (Server-Sent Events pattern)
- **Graceful shutdown** (Section 8.3) ties into the Node.js process lifecycle in [Node.js Runtime — Threading and Process Management](../02-node-runtime/02-threading-and-process-management.md#4-process-lifecycle-and-graceful-shutdown)
- For testing GraphQL APIs, see [Testing — Integration Testing and Mocking](../07-testing/02-integration-testing-and-mocking.md)
