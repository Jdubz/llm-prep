# Module 05 Cheat Sheet: Authentication & Security

## JWT Structure

```
┌─────────────────────────────────────────────────────┐
│  Header (Base64URL)                                 │
│  { "alg": "RS256", "typ": "JWT", "kid": "key-1" }  │
├─────────────────────────────────────────────────────┤
│  Payload (Base64URL)                                │
│  { "sub": "user-123", "iss": "auth.example.com",   │
│    "aud": "api.example.com", "exp": 1700000000,    │
│    "iat": 1699999000, "jti": "unique-id",          │
│    "roles": ["admin"], "tokenVersion": 3 }          │
├─────────────────────────────────────────────────────┤
│  Signature                                          │
│  RS256(base64url(header) + "." + base64url(payload),│
│        privateKey)                                  │
└─────────────────────────────────────────────────────┘

ENCODED: eyJhbGci...<header>.eyJzdWIi...<payload>.SflKxwRJ...<signature>
```

### Algorithm Quick Reference

| Algorithm | Type | Key | Use Case |
|-----------|------|-----|----------|
| HS256 | Symmetric | Shared secret | Single-service, simple setups |
| RS256 | Asymmetric | RSA key pair | Distributed systems (default choice) |
| ES256 | Asymmetric | ECDSA P-256 | Smaller tokens, mobile-friendly |
| EdDSA | Asymmetric | Ed25519 | Best performance asymmetric |
| PS256 | Asymmetric | RSA-PSS | FIPS-compliant environments |

---

## OAuth 2.0 Authorization Code + PKCE Flow

```
┌──────────┐    1. /authorize?                      ┌──────────────┐
│          │       response_type=code&               │              │
│  Client  │       code_challenge=SHA256(verifier)   │  Auth Server │
│  (SPA)   │ ─────────────────────────────────────>  │              │
│          │                                         │              │
│          │    2. redirect_uri?code=AUTH_CODE        │              │
│          │ <─────────────────────────────────────── │              │
│          │                                         │              │
│          │    3. POST /token                        │              │
│          │       grant_type=authorization_code&     │              │
│          │       code=AUTH_CODE&                    │              │
│          │       code_verifier=ORIGINAL_VERIFIER    │              │
│          │ ─────────────────────────────────────>   │              │
│          │                                         │              │
│          │    4. { access_token, id_token,          │              │
│          │         refresh_token }                  │              │
│          │ <─────────────────────────────────────── │              │
└──────────┘                                         └──────────────┘
```

### Grant Type Quick Reference

| Grant Type | Client Type | Use Case |
|------------|-------------|----------|
| Authorization Code + PKCE | Public/Confidential | All user-facing apps (default) |
| Client Credentials | Confidential | Machine-to-machine (no user) |
| Device Authorization | Input-constrained | Smart TV, CLI tools |
| Refresh Token | Any | Exchange for new access token |
| ~~Implicit~~ | ~~Public~~ | **DEPRECATED in OAuth 2.1** |
| ~~Password~~ | ~~Confidential~~ | **DEPRECATED in OAuth 2.1** |

---

## Security Headers Checklist

```typescript
// Copy-paste production configuration
helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'strict-dynamic'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https://cdn.example.com"],
      connectSrc: ["'self'", "https://api.example.com"],
      objectSrc: ["'none'"],
      frameAncestors: ["'none'"],
      baseUri: ["'self'"],
      formAction: ["'self'"],
      upgradeInsecureRequests: [],
    },
  },
  hsts: { maxAge: 63072000, includeSubDomains: true, preload: true },
  crossOriginOpenerPolicy: { policy: "same-origin" },
  crossOriginEmbedderPolicy: true,
  crossOriginResourcePolicy: { policy: "same-origin" },
  referrerPolicy: { policy: "strict-origin-when-cross-origin" },
})
```

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Force HTTPS |
| `Content-Security-Policy` | (see above) | XSS prevention |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Clickjacking (legacy, use CSP) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Leak prevention |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Feature control |
| `Cross-Origin-Opener-Policy` | `same-origin` | Spectre mitigation |
| `Cross-Origin-Resource-Policy` | `same-origin` | Resource isolation |

---

## CORS Quick Reference

### What Triggers a Preflight?

| Condition | Preflight? |
|-----------|------------|
| `GET` / `HEAD` / `POST` with simple headers | No (simple request) |
| `PUT` / `DELETE` / `PATCH` | Yes |
| `POST` with `Content-Type: application/json` | Yes |
| Any custom header (e.g., `Authorization`) | Yes |
| `Content-Type: application/x-www-form-urlencoded` | No |

### Key Rules

- `Access-Control-Allow-Origin: *` CANNOT be used with `credentials: true`
- `Vary: Origin` is required when origin is dynamic (prevents CDN caching issues)
- `Access-Control-Max-Age` caches preflight (set to 86400 for 24h)
- CORS is browser-enforced only -- `curl` and server-to-server calls ignore it

---

## Rate Limiting Algorithms

| Algorithm | Burst Handling | Memory | Accuracy | Complexity |
|-----------|---------------|--------|----------|------------|
| Token Bucket | Allows bursts up to bucket size | Low (2 values per key) | Good | Low |
| Leaky Bucket | Smooths out bursts | Low (2 values per key) | Good | Low |
| Fixed Window | Allows 2x burst at boundary | Low (1 counter per key) | Poor at edges | Very low |
| Sliding Window Log | No boundary issues | High (all timestamps) | Exact | Medium |
| Sliding Window Counter | Minor boundary inaccuracy | Low (2 counters per key) | Very good | Medium |

### Redis Rate Limit Template (Sliding Window Counter)

```typescript
async function checkRate(key: string, limit: number, windowSec: number): Promise<boolean> {
  const now = Date.now();
  const window = Math.floor(now / (windowSec * 1000));
  const progress = (now % (windowSec * 1000)) / (windowSec * 1000);

  const [cur, prev] = await redis.mget(`rl:${key}:${window}`, `rl:${key}:${window - 1}`);
  const estimated = (Number(prev) || 0) * (1 - progress) + (Number(cur) || 0);

  if (estimated >= limit) return false;

  await redis.pipeline()
    .incr(`rl:${key}:${window}`)
    .expire(`rl:${key}:${window}`, windowSec * 2)
    .exec();

  return true;
}
```

---

## Zod Validation Template

```typescript
import { z } from 'zod';

// Common reusable schemas
const Id = z.string().uuid();
const Email = z.string().email().max(255).toLowerCase();
const Password = z.string().min(12).max(128);
const Pagination = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
});
const SortOrder = z.enum(['asc', 'desc']).default('desc');
const ISODate = z.string().datetime();

// Request validation middleware
function validate<T extends z.ZodSchema>(schema: T) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        error: 'Validation failed',
        details: result.error.flatten(),
      });
    }
    req.body = result.data;
    next();
  };
}

// Query params validation
function validateQuery<T extends z.ZodSchema>(schema: T) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.query);
    if (!result.success) {
      return res.status(400).json({ error: result.error.flatten() });
    }
    req.query = result.data;
    next();
  };
}
```

---

## Cookie Security Settings

```
__Host-session=abc123;
  HttpOnly;         ← Not accessible via JavaScript
  Secure;           ← HTTPS only
  SameSite=Lax;     ← No cross-site POST/AJAX
  Path=/;           ← Required for __Host- prefix
  Max-Age=86400     ← 24 hours
```

| Attribute | When to Use | Gotcha |
|-----------|-------------|--------|
| `HttpOnly` | Always for session/auth cookies | Cannot read in JS (that is the point) |
| `Secure` | Always in production | Required for `SameSite=None` |
| `SameSite=Strict` | High security forms | Breaks OAuth redirects and payment flows |
| `SameSite=Lax` | Default for most cookies | Top-level GET navigations still send cookie |
| `SameSite=None` | Cross-site embeds, third-party | Must also set `Secure` |
| `__Host-` prefix | Production session cookies | No `Domain` attribute allowed, `Path=/` required |

---

## Token Revocation Decision Tree

```
Need instant revocation?
├── No  → Short-lived tokens (5-15 min), no revocation check
│         Access token expiry is your revocation window
│
└── Yes → How many tokens to revoke?
          ├── Single token → Redis blocklist keyed by jti, TTL = token expiry
          ├── All user tokens → Token versioning (increment counter, check on verify)
          └── System-wide → Rotate signing key (all existing tokens become invalid)
```
