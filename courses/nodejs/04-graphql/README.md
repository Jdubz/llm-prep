# Module 04: GraphQL

> Schema design, DataLoader, subscriptions, federation, security — everything you need to defend production GraphQL decisions in a senior/staff interview.

You have shipped GraphQL APIs. This module sharpens the edges: design trade-offs, runtime behaviors, and production concerns that separate "I've used Apollo" from "I designed the graph for a 200-person org."

---

## Table of Contents

1. [Schema Design Principles](#1-schema-design-principles)
2. [Resolvers In Depth](#2-resolvers-in-depth)
3. [DataLoader and the N+1 Problem](#3-dataloader-and-the-n1-problem)
4. [Mutations](#4-mutations)
5. [Subscriptions](#5-subscriptions)
6. [Code-First vs Schema-First](#6-code-first-vs-schema-first)
7. [Federation and Schema Stitching](#7-federation-and-schema-stitching)
8. [Security](#8-security)
9. [Pagination](#9-pagination)
10. [Error Handling](#10-error-handling)
11. [Caching Strategies](#11-caching-strategies)
12. [Interview Questions](#12-interview-questions)

---

## 1. Schema Design Principles

### Think in Graphs, Not Endpoints

The most common migration mistake: replicating REST endpoint structure in the schema. Graph thinking means modeling domain *relationships*, not database tables or route paths.

```graphql
# Bad: REST-shaped
type Query {
  getUserOrders(userId: ID!): [Order!]!
  getOrderItems(orderId: ID!): [OrderItem!]!
}

# Good: Graph-shaped — clients traverse relationships in any direction
type User {
  id: ID!
  orders(first: Int, after: String, status: OrderStatus): OrderConnection!
}

type Order {
  id: ID!
  customer: User!
  items: [OrderItem!]!
  totalAmount: Money!
}
```

### The Nullable-by-Default Debate

Fields are nullable by default. When a non-null field resolver fails, the null propagates *upward* — potentially wiping out entire parent objects and lists.

```graphql
# Dangerous: one broken email nukes the whole list
type Query { users: [User!]! }
type User {
  email: String!    # Resolver throws -> User becomes null -> list errors
  profile: Profile! # External service down? Cascading null.
}

# Safer: graceful degradation
type User {
  id: ID!
  email: String!        # Same DB row — safe to require
  profile: Profile      # Separate service — nullable
  avatarUrl: String     # CDN could be down — nullable
}
```

**Rule of thumb:** Non-null only when you can guarantee resolution from the same data source as the parent. Cross-service fields should almost always be nullable.

### Input Types

Input types enforce a clear boundary between what clients send and what the server returns. Key rules: they cannot reference output types, they support defaults, and you should use separate types for create vs update.

```graphql
input CreateProductInput {
  name: String!       # Required on create
  sku: String!
  price: MoneyInput!
}
input UpdateProductInput {
  name: String        # Optional on update
  sku: String
  price: MoneyInput
}
```

### Enums

Enums provide cross-boundary type safety. You can add values but never remove them without breaking clients — use `@deprecated` instead.

```graphql
enum OrderStatus {
  PENDING
  CONFIRMED
  PROCESSING @deprecated(reason: "Use CONFIRMED instead")
  SHIPPED
  DELIVERED
  CANCELLED
}
```

### Interfaces vs Unions

**Interfaces** share guaranteed fields — clients can query shared fields without inline fragments. Use when types share meaningful, commonly-queried fields (e.g., `Node { id }`, `Timestamped { createdAt, updatedAt }`).

**Unions** share no guaranteed fields — clients must use `... on Type` fragments. Use when types are conceptually grouped but structurally different (e.g., `union SearchResult = User | Post | Product`).

---

## 2. Resolvers In Depth

### The Resolver Chain

Every field has a resolver. Unwritten resolvers use the **default resolver**: `parent[fieldName]`. Understanding this eliminates unnecessary code.

```typescript
const resolvers = {
  Query: {
    user: async (_, { id }, ctx) => ctx.db.users.findById(id),
    // Returns { id, fullName, email } — default resolvers handle those fields
  },
  User: {
    // Only write resolvers for fields that need computation or separate fetching
    orders: async (parent, _, ctx) => ctx.loaders.ordersByUser.load(parent.id),
  },
};
```

### The Four Arguments: `(parent, args, context, info)`

- **`parent`**: Value from the parent resolver. `undefined` for root Query/Mutation fields.
- **`args`**: This field's arguments, already validated against the schema.
- **`context`**: Per-request shared state — auth user, DB client, DataLoader instances, services.
- **`info`**: `GraphQLResolveInfo` — the AST metadata. Powerful for selection-set optimization.

```typescript
const context = async ({ req }): Promise<Context> => ({
  user: await authenticateRequest(req),
  db: prisma,
  loaders: createLoaders(),  // Fresh per request — critical
});
```

### Field-Level Resolvers

Each field can independently compute, transform, authorize, or lazy-load:

```typescript
User: {
  fullName: (parent) => `${parent.firstName} ${parent.lastName}`,     // Computed
  createdAt: (parent) => parent.created_at.toISOString(),             // Transformed
  recentActivity: (parent, _, ctx) => ctx.loaders.activity.load(parent.id), // Lazy
  email: (parent, _, ctx) => {                                        // Authorized
    if (ctx.user.id !== parent.id && !ctx.user.isAdmin) return null;
    return parent.email;
  },
}
```

---

## 3. DataLoader and the N+1 Problem

### The Problem

50 users with a `company` field = 1 query for users + 50 queries for companies. DataLoader collects all `.load(key)` calls within a single event loop tick, then executes one batched call.

```typescript
const companyLoader = new DataLoader<string, Company>(async (ids) => {
  const companies = await db.companies.findMany({ where: { id: { in: [...ids] } } });
  const map = new Map(companies.map((c) => [c.id, c]));
  // MUST return same length and order as input keys
  return ids.map((id) => map.get(id) ?? new Error(`Company ${id} not found`));
});
```

### The Batch Contract

1. Receives an array of keys.
2. Returns an array of the **same length**.
3. Results in the **same order** as keys.
4. Individual elements can be `Error` instances.

Violating any of these causes subtle, hard-to-debug issues.

### Per-Request Instances Are Mandatory

DataLoader caches by default with no TTL and no auth boundaries. A shared loader leaks data across users.

```typescript
function createLoaders(db: PrismaClient) {
  return {
    user: new DataLoader<string, User>(async (ids) => { /* batch fn */ }),
    company: new DataLoader<string, Company>(async (ids) => { /* batch fn */ }),
  };
}
// In context factory: loaders: createLoaders(prisma) — fresh per request
```

### Advanced Patterns

**Composite keys** use `cacheKeyFn` to serialize object keys. **Cache priming** with `.prime(key, value)` avoids redundant loads when you already have the data.

---

## 4. Mutations

### Consistent Shape

Every mutation should accept a single input and return a payload type. This ensures backwards compatibility (add optional fields freely) and clean code generation.

```graphql
type Mutation {
  createOrder(input: CreateOrderInput!): CreateOrderPayload!
}
input CreateOrderInput {
  items: [OrderItemInput!]!
  shippingAddressId: ID!
  idempotencyKey: String!
}
type CreateOrderPayload {
  order: Order
  errors: [UserError!]!
}
type UserError {
  message: String!
  field: [String!]
  code: ErrorCode!
}
```

### Error Handling: Two Schools

**Errors array** (GitHub, Shopify): `order` is null on failure, `errors` array describes what went wrong. Simpler, more flexible.

**Union return types** (Result pattern): `union CreateOrderResult = Success | ValidationError | NotFoundError`. More verbose but exhaustively type-safe at the schema level.

Pick one and be consistent. In interviews, articulate trade-offs rather than picking sides.

---

## 5. Subscriptions

### WebSocket Transport

Use `graphql-ws` (modern) over `subscriptions-transport-ws` (legacy). Auth comes from connection params, not HTTP headers.

```typescript
const serverCleanup = useServer({
  schema,
  context: async (ctx) => {
    const user = await verifyToken(ctx.connectionParams?.authToken as string);
    return { user, loaders: createLoaders(prisma) };
  },
  onConnect: async (ctx) => {
    if (!ctx.connectionParams?.authToken) return false; // Reject
  },
}, wsServer);
```

### PubSub

Subscription resolvers return an `AsyncIterator`. Mutations publish events. The in-memory `PubSub` works only in a single process.

```typescript
Subscription: {
  orderStatusChanged: {
    subscribe: (_, { orderId }) => pubsub.asyncIterableIterator(`ORDER_${orderId}`),
  },
}
// In mutation resolver: pubsub.publish(`ORDER_${order.id}`, { orderStatusChanged: order })
```

### Scaling

Production requires distributed PubSub: **Redis PubSub** (`graphql-redis-subscriptions`) or **Kafka** for high-throughput. Each WebSocket is stateful and consumes memory — dedicated subscription servers with sticky sessions are the standard approach at scale.

---

## 6. Code-First vs Schema-First

**Schema-first**: Write `.graphql` SDL files, implement matching resolvers. Schema is the contract. Non-TS teams can read it. Drift between schema and resolvers requires codegen (GraphQL Code Generator) to catch.

**Code-first**: Define schema in TypeScript, SDL is generated. Type safety is built-in.

- **Pothos** (formerly GiraphQL): Builder pattern, excellent type inference, active. Best choice for new projects.
- **TypeGraphQL**: Decorator-based, pairs with TypeORM. Good if you already use decorators.
- **Nexus**: Stalled development. Avoid for new projects.

| Factor | Schema-First | Code-First |
|--------|-------------|------------|
| Type safety | Requires codegen | Built-in |
| Team readability | Higher (SDL universal) | Requires TS |
| Federation | Native fit | Needs SDL generation |
| Refactoring | Manual sync | Compiler catches errors |

Full-TS teams owning the entire graph: code-first (Pothos). Federated multi-team/multi-language: schema-first.

---

## 7. Federation and Schema Stitching

Schema stitching (legacy) merges schemas at the gateway. **Apollo Federation v2** is the modern approach.

### How It Works

Each subgraph owns part of the graph. The **router** (Apollo Router) composes subgraph schemas into a supergraph.

```graphql
# Users subgraph — owns User
type User @key(fields: "id") { id: ID!  email: String!  displayName: String! }

# Orders subgraph — extends User
type User @key(fields: "id") { id: ID!  orders: [Order!]! }
```

### Entity Resolvers

The router sends `_entities` queries with key fields. Subgraphs implement `__resolveReference`:

```typescript
User: {
  __resolveReference: (ref: { id: string }, ctx) => ctx.loaders.user.load(ref.id),
}
```

### Key Directives

`@key` (entity primary key), `@shareable` (multi-subgraph resolution), `@external` (defined elsewhere), `@requires` (needs external fields), `@provides` (performance hint), `@override` (field migration).

### Subgraph Design

1. Map to bounded contexts, not tables.
2. One subgraph owns the canonical entity definition; others extend.
3. Minimize cross-subgraph `@requires` chains.
4. Each subgraph deploys independently; CI composition checks catch breaks.

---

## 8. Security

### Query Depth Limiting

Prevent deeply nested queries (friends-of-friends-of-friends attack):

```typescript
import depthLimit from 'graphql-depth-limit';
const server = new ApolloServer({ schema, validationRules: [depthLimit(10)] });
```

### Query Cost Analysis

Assign costs to fields, reject queries exceeding a budget. Pagination arguments multiply cost. Use `graphql-query-complexity`.

### Persisted Queries

**APQ** (Automatic): Performance optimization — clients send hashes, server caches queries. Not a security boundary (any client can register queries).

**Registered persisted queries**: Only pre-registered queries are allowed. Unknown queries rejected. This is the security measure.

### Introspection

Disable in production: `introspection: process.env.NODE_ENV !== 'production'`.

### Rate Limiting

Per-operation or per-complexity rate limiting. A query costing 500 points should consume more rate budget than one costing 5.

---

## 9. Pagination

### Relay Connection Spec

The de facto standard. Even without Relay on the client, the pattern is universally understood.

```graphql
type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int
}
type UserEdge { cursor: String!  node: User! }
type PageInfo {
  hasNextPage: Boolean!  hasPreviousPage: Boolean!
  startCursor: String    endCursor: String
}
```

### Cursor-Based Implementation

Cursors are opaque base64-encoded positions. Fetch `limit + 1` rows to determine `hasNextPage`. Cursor-based pagination is stable across inserts/deletes; offset-based breaks.

```typescript
const limit = Math.min(args.first ?? 20, 100);
const users = await db.user.findMany({
  where: afterId ? { id: { gt: afterId } } : undefined,
  take: limit + 1,
  orderBy: { id: 'asc' },
});
const hasNextPage = users.length > limit;
const nodes = hasNextPage ? users.slice(0, -1) : users;
```

---

## 10. Error Handling

### Top-Level Errors vs Typed Unions

**Top-level errors**: Appear in the root `errors` array. Best for infrastructure concerns (auth, rate limiting) that clients handle generically.

**Typed union returns**: `union CreateUserResult = Success | ValidationError | NotFoundError`. Best for domain errors that clients must handle in their UI — exhaustive type checking forces handling.

### The Result Pattern

```graphql
interface Error { message: String! }
type ValidationError implements Error { message: String!  field: String! }
union CreateUserResult = CreateUserSuccess | ValidationError | NotFoundError
```

Resolver returns `{ __typename: 'ValidationError', message, field }` or `{ __typename: 'CreateUserSuccess', user }`. Unexpected errors still bubble to top-level.

**Pragmatic approach:** unions for domain errors, top-level for infrastructure. Be consistent.

---

## 11. Caching Strategies

### CDN Caching

Registered persisted queries + `GET` requests = CDN-cacheable GraphQL. Set per-field cache hints with `info.cacheControl.setCacheHint({ maxAge: 300, scope: 'PUBLIC' })`.

### Normalized Client Cache

Apollo Client, urql, and Relay store entities by `__typename + id`. Mutations returning updated entities auto-update the cache everywhere. Requires consistent `id` fields and mutations that return full objects.

### Server-Side: DataLoader + Redis

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

## 12. Interview Questions

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

---

## Summary

- **Schema design is API design.** It outlives your resolver implementation.
- **DataLoader is non-optional.** No DataLoader = N+1 problem.
- **Security is your responsibility.** Constrain what clients can construct.
- **Federation is an organizational tool.** Solves team scaling, not just schema scaling.
- **Error handling is a schema decision.** Make it explicit and consistent.
