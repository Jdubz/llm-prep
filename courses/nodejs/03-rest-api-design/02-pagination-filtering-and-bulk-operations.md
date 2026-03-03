# 02 — Pagination, Filtering, Sorting, Bulk Operations, and PATCH

> Assumes HTTP semantics from file 01. Covers the practical data-access patterns that every production API must get right.

---

## 1. Pagination

### 1.1 Offset-Based

```
GET /articles?offset=20&limit=10
```

**Pros:** Simple, random page access.
**Cons:** Drift on insert/delete, O(n) performance at depth (`OFFSET 10000` still scans 10,010 rows), inconsistent totals between pages.

### 1.2 Cursor-Based (Keyset)

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

**Pros:** Stable (no drift), O(1) at any depth, works for real-time feeds.
**Cons:** No random page access, opaque cursors.

### 1.3 Page Tokens (Google-Style)

Completely opaque tokens that can encode cursor position, filter state, and sort order. Maximum server flexibility to change pagination strategy without breaking clients.

### 1.4 Pagination Comparison (Cheat Sheet)

| Aspect | Offset | Cursor/Keyset | Page Token |
|--------|--------|---------------|------------|
| Random access | Yes | No | No |
| Deep page performance | O(n) | O(1) | O(1) |
| Stability during writes | Unstable (drift) | Stable | Stable |
| Client complexity | Low | Medium | Low |
| Server flexibility | Low | Medium | High |
| Best for | Admin tables, small datasets | Feeds, timelines, large datasets | Public APIs, any dataset |

**Recommendation:** Cursor/keyset for anything large or mutable. Offset only when random page access is genuinely needed (admin dashboards with "go to page" UI).

### 1.5 Full Cursor Pagination Implementation

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

## 2. Filtering and Sorting

### 2.1 Query Parameter Design

**Equality:** `GET /orders?status=shipped&customerId=123`

**Range filters (LHS brackets — most common, used by Stripe/Shopify):**
```
GET /orders?createdAt[gte]=2025-01-01&createdAt[lt]=2025-02-01
```

Express's `qs` parses brackets by default. Fastify needs `querystringParser: (str) => qs.parse(str)`.

**Complex filters:** For OR logic or nested conditions, use `POST /orders/search` with a JSON body. This breaks REST purity but solves real problems (complex filters, saved searches, no URL length limits).

### 2.2 Sorting

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

## 3. Bulk Operations

**Three approaches:**

1. **Array body:** `POST /users` with `[{...}, {...}]`. Simple but: what if one fails?
2. **Batch endpoint:** `POST /batch` with per-item operations and per-item status codes in response.
3. **Bulk action:** `POST /users/bulk-delete` with `{ "ids": [1,2,3] }` and partial success reporting.

**Key decisions:**
- **Atomic or partial?** Atomic is simpler/safer. Partial is more performant but clients must handle mixed results.
- **Status code for partial success:** `207 Multi-Status` or `200` with per-item statuses. Never `201` if some failed.
- **Size limits:** Cap batch size (e.g., 100). Reject oversized with `413 Payload Too Large`.

---

## 4. PATCH Patterns in Depth

### 4.1 JSON Merge Patch (RFC 7396)

Send only the fields you want to change. `null` removes a field. Fields not included are unchanged.

```http
PATCH /users/123 HTTP/1.1
Content-Type: application/merge-patch+json

{ "name": "Alice", "address": null }
```

Limitations: Cannot set a field to literal `null`. Cannot target array items individually.

### 4.2 JSON Patch (RFC 6902)

A sequence of operations (`add`, `remove`, `replace`, `move`, `copy`, `test`):

```http
PATCH /users/123 HTTP/1.1
Content-Type: application/json-patch+json

[
  { "op": "replace", "path": "/name", "value": "Alice" },
  { "op": "add", "path": "/tags/-", "value": "premium" },
  { "op": "test", "path": "/version", "value": 5 }
]
```

The `test` operation provides optimistic concurrency without ETags. JSON Patch is not idempotent when using `add` on arrays.

### 4.3 When to Use Which

- **JSON Merge Patch**: Simple partial updates, most use cases. Client sends only what changed.
- **JSON Patch**: Array manipulation, conditional updates with `test`, when you need a log of specific field changes.

---

## 5. Backward Compatibility Strategies

### 5.1 Robustness Principle (Postel's Law)

Servers ignore unknown request fields (forward-compatible). Clients ignore unknown response fields. Servers never remove response fields or add required request fields without a version bump.

### 5.2 Additive-Only Changes

Adding fields and endpoints is non-breaking. Removing, renaming, or changing types of existing fields is breaking.

### 5.3 Expand/Contract Pattern

For field renames, use three phases:

1. **Expand:** Return both old and new fields. Accept both in requests.
2. **Deprecate:** Document old field as deprecated, add `Deprecation` header, notify consumers.
3. **Contract:** Remove old field in a new API version.

The expand phase can last weeks or months depending on consumer base.

### 5.4 Tolerant Reader Pattern

Clients should extract only needed fields and ignore everything else:

```typescript
// BAD: strict validation breaks on new fields
const user = UserSchemaStrict.parse(response.data);

// GOOD: permissive parsing or selective extraction
const user = UserSchemaPermissive.parse(response.data); // .passthrough() in Zod
```

---

## 6. API Deprecation Lifecycle

### 6.1 Timeline

```
Month 0:  Announce + add `Deprecation` and `Sunset` headers
Month 1:  Deprecation warnings in developer portal
Month 3:  Return `Warning: 299 - "Deprecated"` header
Month 6:  (Optional) Reduce rate limits on deprecated endpoint
Month 9:  Return 410 Gone or redirect
Month 12: Decommission
```

### 6.2 HTTP Headers

```
Deprecation: Sat, 01 Mar 2025 00:00:00 GMT      # RFC draft: when deprecated
Sunset: Sat, 01 Sep 2025 00:00:00 GMT            # RFC 8594: when it stops working
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

### 6.3 Monitoring

Before decommissioning, track who still calls the old endpoint. Log API key / consumer identity on every deprecated endpoint call to plan decommission timing.

---

## 7. API Testing Strategies

### 7.1 The Testing Pyramid

Unit (handler logic, no HTTP) -> Contract (Pact, schema validation) -> Integration (real HTTP, test DB) -> E2E (full environment).

### 7.2 Contract Testing with Pact

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

### 7.3 Schema Validation Testing

Validate actual responses conform to your OpenAPI spec using `jest-openapi` or `chai-openapi-response-validator`. Catches drift between implementation and documentation.

### 7.4 Snapshot Testing

Catches unintended response shape changes but is brittle. Remove volatile fields (`createdAt`, `updatedAt`) before snapshotting. Pair with contract tests for cross-service guarantees.
