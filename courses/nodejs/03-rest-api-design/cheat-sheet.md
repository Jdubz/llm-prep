# Module 03 Cheat Sheet: REST API Design

Quick reference for REST API design decisions. For rationale and trade-offs, see the main README and deep-dive.

---

## HTTP Methods

| Method | Safe | Idempotent | Has Body | Typical Use | Typical Success Code |
|--------|------|------------|----------|-------------|---------------------|
| GET | Yes | Yes | No | Read resource | 200 |
| HEAD | Yes | Yes | No | Read headers only | 200 |
| POST | No | No | Yes | Create resource / trigger action | 201 (create) or 200 (action) |
| PUT | No | Yes | Yes | Full replace | 200 or 204 |
| PATCH | No | No* | Yes | Partial update | 200 or 204 |
| DELETE | No | Yes | Optional | Remove resource | 204 |
| OPTIONS | Yes | Yes | No | CORS preflight / discovery | 204 |

*JSON Merge Patch is idempotent in practice. JSON Patch is not.

---

## Status Codes Quick Reference

### Success (2xx)

| Code | Name | When |
|------|------|------|
| 200 | OK | GET, PUT, PATCH success with body |
| 201 | Created | POST created a resource (include `Location` header) |
| 202 | Accepted | Async operation accepted, not yet complete |
| 204 | No Content | DELETE success, or PUT/PATCH with no response body |

### Redirection (3xx)

| Code | Name | When |
|------|------|------|
| 301 | Moved Permanently | Resource URL permanently changed |
| 304 | Not Modified | ETag matched (conditional GET) |

### Client Error (4xx)

| Code | Name | When |
|------|------|------|
| 400 | Bad Request | Malformed syntax, unparseable JSON |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource does not exist |
| 405 | Method Not Allowed | HTTP method not supported on this URI |
| 409 | Conflict | State conflict, duplicate, version mismatch |
| 410 | Gone | Permanently deleted (known removal) |
| 415 | Unsupported Media Type | Wrong Content-Type |
| 422 | Unprocessable Entity | Valid syntax, invalid semantics (validation) |
| 429 | Too Many Requests | Rate limit exceeded (include `Retry-After`) |

### Server Error (5xx)

| Code | Name | When |
|------|------|------|
| 500 | Internal Server Error | Unhandled exception (never leak stack traces) |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Overloaded / maintenance (include `Retry-After`) |
| 504 | Gateway Timeout | Upstream service timeout |

---

## Pagination Comparison

| Aspect | Offset | Cursor/Keyset | Page Token |
|--------|--------|---------------|------------|
| Random page access | Yes | No | No |
| Deep page performance | O(n) | O(1) | O(1) |
| Stability during writes | Unstable (drift) | Stable | Stable |
| Client complexity | Low | Medium | Low |
| Server flexibility | Low | Medium | High |
| Best for | Admin tables, small datasets | Feeds, timelines, large datasets | Public APIs, any dataset |

---

## Error Response Template (RFC 9457 / 7807)

### Standard Error

```json
{
  "type": "https://api.example.com/errors/insufficient-funds",
  "title": "Insufficient Funds",
  "status": 422,
  "detail": "Account balance is $10.00 but transaction requires $25.00.",
  "instance": "/payments/abc123"
}
```

### Validation Error

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains 2 validation errors.",
  "errors": [
    {
      "field": "email",
      "message": "Must be a valid email address",
      "code": "INVALID_FORMAT"
    },
    {
      "field": "age",
      "message": "Must be at least 18",
      "code": "MIN_VALUE",
      "params": { "min": 18 }
    }
  ]
}
```

Content-Type: `application/problem+json`

---

## Express vs Fastify vs Hono

| Aspect | Express | Fastify | Hono |
|--------|---------|---------|------|
| First release | 2010 | 2016 | 2021 |
| TypeScript | Bolted on (`@types/express`) | Native (since v4) | Native (TS-first) |
| Async error handling | Manual wrapper required* | Automatic | Automatic |
| Validation | BYO | Built-in (JSON Schema) | Built-in (Zod adapter) |
| JSON serialization | `JSON.stringify` | `fast-json-stringify` (2-5x faster) | `JSON.stringify` |
| OpenAPI integration | Manual / `swagger-jsdoc` | `@fastify/swagger` (from schemas) | `@hono/zod-openapi` |
| Plugin encapsulation | No (global middleware) | Yes (scoped plugins) | No (global middleware) |
| Runtime support | Node.js | Node.js | Node, Deno, Bun, Workers, Edge |
| Throughput (hello world) | ~15k req/s | ~75k req/s | ~80k req/s (Bun) / ~30k (Node) |
| Ecosystem size | Massive | Large | Growing |
| Best for | Brownfield, max ecosystem | Performance, schema-driven APIs | Edge/multi-runtime, minimal footprint |

*Express 5 fixes async error handling but adoption is still early.

**Quick decision:**
- **Existing project with Express?** Stay on Express (or upgrade to Express 5).
- **New Node.js API where performance and validation matter?** Fastify.
- **Edge-first, multi-runtime, or serverless?** Hono.

---

## API Design Checklist

### Resource Design
- [ ] Plural nouns for collection resources
- [ ] Kebab-case for multi-word resources
- [ ] Maximum 2 levels of nesting
- [ ] Globally unique IDs (UUIDs) for top-level resources
- [ ] No verbs in URIs

### Request/Response
- [ ] Correct HTTP methods (no POST for everything)
- [ ] Appropriate status codes (not just 200 and 500)
- [ ] RFC 9457 Problem Details for errors
- [ ] Machine-readable error codes alongside human messages
- [ ] `Location` header on 201 Created
- [ ] `Retry-After` header on 429 and 503

### Pagination
- [ ] Default page size with configurable limit
- [ ] Maximum page size enforced
- [ ] Cursor-based for large/mutable collections
- [ ] `hasMore` / `nextCursor` in response

### Security
- [ ] Authentication on all non-public endpoints
- [ ] 404 (not 403) for resources user should not know exist
- [ ] No stack traces in production error responses
- [ ] Rate limiting with proper headers
- [ ] Idempotency keys for non-idempotent writes
- [ ] Input validation and sanitization on all endpoints
- [ ] CORS configured correctly

### Versioning and Compatibility
- [ ] API version in URL path (e.g., `/v1/`)
- [ ] Only breaking changes trigger version increment
- [ ] `Deprecation` and `Sunset` headers on deprecated endpoints
- [ ] Maximum 2-3 concurrent versions

### Documentation
- [ ] OpenAPI spec generated from code
- [ ] Every endpoint documented with examples
- [ ] Error responses documented
- [ ] Rate limits documented
- [ ] Changelog maintained

### Caching and Performance
- [ ] ETags on frequently-read resources
- [ ] `Cache-Control` headers set appropriately
- [ ] Conditional requests supported (If-None-Match, If-Match)
- [ ] Bulk endpoints for batch operations
- [ ] 202 Accepted + polling for long-running operations
