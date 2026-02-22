# Module 04: GraphQL — Cheat Sheet

> Quick reference. Scan before your interview.

---

## Schema Patterns

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

## DataLoader Template

```typescript
import DataLoader from 'dataloader';

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

---

## Resolver Template

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

## Federation Entity Template

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

**Directives:** `@key` (primary key), `@shareable` (multi-subgraph), `@external` (defined elsewhere), `@requires` (needs external fields), `@override` (migrate field), `@provides` (perf hint).

---

## Pagination (Relay Connection Spec)

```graphql
type UserConnection { edges: [UserEdge!]!  pageInfo: PageInfo!  totalCount: Int }
type UserEdge { cursor: String!  node: User! }
type PageInfo { hasNextPage: Boolean!  hasPreviousPage: Boolean!  startCursor: String  endCursor: String }
```

```typescript
const limit = Math.min(args.first ?? 20, 100);
const rows = await db.user.findMany({
  where: afterId ? { id: { gt: afterId } } : undefined,
  take: limit + 1,  orderBy: { id: 'asc' },  // +1 to detect hasNextPage
});
const hasNextPage = rows.length > limit;
const nodes = hasNextPage ? rows.slice(0, -1) : rows;
```

---

## Security Checklist

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

## Code-First Library Comparison

| | Pothos | TypeGraphQL | Nexus |
|---|--------|-------------|-------|
| Pattern | Builder | Decorators | Builder |
| Type safety | Excellent | Good | Good |
| Maintained (2025) | Yes | Yes | Stalled |
| Prisma plugin | Yes | Manual | Stale |
| Federation | Plugin | Limited | Community |
| **Verdict** | **New projects** | **TypeORM stacks** | **Avoid** |

---

## Nullable Rules of Thumb

- `!` (non-null): Same data source as parent, guaranteed.
- Nullable: Cross-service, computed fields that can fail, optional relationships.
- `[User!]!`: Null items meaningless. `[User]!`: Individual items can fail.

## Execution Order

Parse (cached) -> Validate (cached) -> Execute (Query: parallel, Mutation: serial) -> DataLoader batches per tick -> Serialize -> 200 response.
