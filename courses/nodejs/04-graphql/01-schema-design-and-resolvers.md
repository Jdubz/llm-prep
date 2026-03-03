# 01 — Schema Design, Queries, Mutations, Subscriptions, Resolvers, and Context

> Schema design is API design. It outlives your resolver implementation. You have shipped GraphQL APIs; this module sharpens the edges that separate "I've used Apollo" from "I designed the graph for a 200-person org."

---

## 1. Schema Design Principles

### 1.1 Think in Graphs, Not Endpoints

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

### 1.2 The Nullable-by-Default Debate

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

### 1.3 Nullable Rules of Thumb

- `!` (non-null): Same data source as parent, guaranteed.
- Nullable: Cross-service, computed fields that can fail, optional relationships.
- `[User!]!`: Null items meaningless. `[User]!`: Individual items can fail.

### 1.4 Input Types

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

### 1.5 Enums

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

### 1.6 Interfaces vs Unions

**Interfaces** share guaranteed fields — clients can query shared fields without inline fragments. Use when types share meaningful, commonly-queried fields (e.g., `Node { id }`, `Timestamped { createdAt, updatedAt }`).

**Unions** share no guaranteed fields — clients must use `... on Type` fragments. Use when types are conceptually grouped but structurally different (e.g., `union SearchResult = User | Post | Product`).

### 1.7 Schema Patterns (Cheat Sheet)

```graphql
scalar DateTime                                # Always define custom scalars
enum OrderStatus { PENDING SHIPPED DELIVERED }  # Finite value sets -> enums
interface Node { id: ID! }                     # Shared fields -> interface
union SearchResult = User | Post | Product     # No shared fields -> union

input CreateUserInput { email: String!  name: String! }  # Separate create
input UpdateUserInput { email: String   name: String  }  # from update

type Mutation { createUser(input: CreateUserInput!): CreateUserPayload! }
type CreateUserPayload { user: User  errors: [UserError!]! }
type UserError { message: String!  field: [String!]  code: ErrorCode! }
```

---

## 2. Resolvers In Depth

### 2.1 The Resolver Chain

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

### 2.2 The Four Arguments: `(parent, args, context, info)`

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

### 2.3 Field-Level Resolvers

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

### 2.4 Resolver Template (Cheat Sheet)

```typescript
const resolvers: Resolvers = {
  Query: {
    user: (_, { id }, ctx) => ctx.loaders.user.load(id),
  },
  Mutation: {
    createUser: async (_, { input }, ctx) => {
      const v = validate(input);
      if (!v.ok) return { user: null, errors: [v.error] };
      const user = await ctx.db.user.create({ data: input });
      return { user, errors: [] };
    },
  },
  User: {
    orders: (parent, _, ctx) => ctx.loaders.ordersByUser.load(parent.id),
    fullName: (parent) => `${parent.firstName} ${parent.lastName}`,
  },
  Subscription: {
    orderUpdated: {
      subscribe: (_, { id }) => pubsub.asyncIterableIterator(`ORDER_${id}`),
    },
  },
};
```

---

## 3. Mutations

### 3.1 Consistent Shape

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

### 3.2 Error Handling: Two Schools

**Errors array** (GitHub, Shopify): `order` is null on failure, `errors` array describes what went wrong. Simpler, more flexible.

**Union return types** (Result pattern): `union CreateOrderResult = Success | ValidationError | NotFoundError`. More verbose but exhaustively type-safe at the schema level.

Pick one and be consistent. In interviews, articulate trade-offs rather than picking sides.

---

## 4. Subscriptions

### 4.1 WebSocket Transport

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

### 4.2 PubSub

Subscription resolvers return an `AsyncIterator`. Mutations publish events. The in-memory `PubSub` works only in a single process.

```typescript
Subscription: {
  orderStatusChanged: {
    subscribe: (_, { orderId }) => pubsub.asyncIterableIterator(`ORDER_${orderId}`),
  },
}
// In mutation resolver: pubsub.publish(`ORDER_${order.id}`, { orderStatusChanged: order })
```

### 4.3 Scaling

Production requires distributed PubSub: **Redis PubSub** (`graphql-redis-subscriptions`) or **Kafka** for high-throughput. Each WebSocket is stateful and consumes memory — dedicated subscription servers with sticky sessions are the standard approach at scale.

---

## 5. Pagination (Relay Connection Spec)

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

### Code-First Library Comparison

| | Pothos | TypeGraphQL | Nexus |
|---|--------|-------------|-------|
| Pattern | Builder | Decorators | Builder |
| Type safety | Excellent | Good | Good |
| Maintained (2025) | Yes | Yes | Stalled |
| Prisma plugin | Yes | Manual | Stale |
| Federation | Plugin | Limited | Community |
| **Verdict** | **New projects** | **TypeORM stacks** | **Avoid** |

---

## 7. Execution Order

Parse (cached) -> Validate (cached) -> Execute (Query: parallel, Mutation: serial) -> DataLoader batches per tick -> Serialize -> 200 response.

**Interview relevance:** Query fields execute in parallel. Mutation fields execute serially (in order). This is per-spec.

---

## 8. Error Handling

### 8.1 Top-Level Errors vs Typed Unions

**Top-level errors**: Appear in the root `errors` array. Best for infrastructure concerns (auth, rate limiting) that clients handle generically.

**Typed union returns**: `union CreateUserResult = Success | ValidationError | NotFoundError`. Best for domain errors that clients must handle in their UI — exhaustive type checking forces handling.

### 8.2 The Result Pattern

```graphql
interface Error { message: String! }
type ValidationError implements Error { message: String!  field: String! }
union CreateUserResult = CreateUserSuccess | ValidationError | NotFoundError
```

Resolver returns `{ __typename: 'ValidationError', message, field }` or `{ __typename: 'CreateUserSuccess', user }`. Unexpected errors still bubble to top-level.

**Pragmatic approach:** unions for domain errors, top-level for infrastructure. Be consistent.

**Common mistake with error handling:** Teams often mix both approaches inconsistently — some mutations use union return types, others throw errors that land in the top-level `errors` array. This forces clients to check two places for every mutation. Pick one pattern for domain errors and enforce it across the entire schema. If you choose unions, establish a shared `interface Error { message: String! }` that all error types implement.

---

## Related Reading

- **Relay connection pagination** (Section 5) is the GraphQL equivalent of cursor pagination in [REST API Design — Pagination, Filtering, and Bulk Operations](../03-rest-api-design/02-pagination-filtering-and-bulk-operations.md) — both use keyset-based cursors, but the Relay spec adds `edges` and `pageInfo` structure
- **Code-first schema definition** (Section 6) uses the TypeScript type system patterns from [TypeScript Advanced — Conditional and Mapped Types](../01-typescript-advanced/01-conditional-and-mapped-types.md) (generics, mapped types) for type-safe schema builders like Pothos
- **Resolver context** (Section 2.2) — the auth user in context connects to [Auth & Security — JWT and OAuth2](../05-auth-security/01-jwt-and-oauth2.md) (token verification, middleware patterns)
- **Subscription transport** (Section 4) — WebSocket scaling connects to [Performance — Caching and Redis](../08-performance-scaling/01-caching-and-redis.md) (Redis adapter for multi-instance WebSocket)
- **Input validation** (Section 1.4) — for Zod-based input validation beyond schema types, see [Auth & Security — Session Management and Validation](../05-auth-security/02-session-management-and-validation.md)
- For DataLoader, N+1 solutions, and federation that build on these resolver patterns, continue to [Advanced GraphQL Patterns](02-advanced-graphql-patterns.md)
- For the REST alternative and comparison framework, see [REST API Design — API Design Patterns and Versioning](../03-rest-api-design/03-api-design-patterns-and-versioning.md#7-graphql-vs-rest-decision-framework)
