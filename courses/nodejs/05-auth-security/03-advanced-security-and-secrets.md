# 03 — Secret Management, OWASP for Node.js, Helmet, CSP, Injection Prevention, and Interview Q&A

> Assumes JWT/OAuth2 (file 01) and session management/validation (file 02). Covers the production security architecture and Node.js-specific attack vectors that distinguish architects from implementers.

---

## 1. Security Headers

### 1.1 Helmet.js Configuration

```typescript
import helmet from 'helmet';

app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'", "'strict-dynamic'"], // strict-dynamic for nonce-based CSP
      styleSrc: ["'self'", "'unsafe-inline'"],    // CSS-in-JS often requires this
      imgSrc: ["'self'", 'data:', 'https://cdn.example.com'],
      connectSrc: ["'self'", 'https://api.example.com'],
      fontSrc: ["'self'", 'https://fonts.googleapis.com'],
      objectSrc: ["'none'"],
      mediaSrc: ["'none'"],
      frameSrc: ["'none'"],
      baseUri: ["'self'"],
      formAction: ["'self'"],
      frameAncestors: ["'none'"],
      upgradeInsecureRequests: [],
    },
  },
  crossOriginEmbedderPolicy: true,
  crossOriginOpenerPolicy: { policy: 'same-origin' },
  crossOriginResourcePolicy: { policy: 'same-origin' },
  hsts: {
    maxAge: 63072000, // 2 years
    includeSubDomains: true,
    preload: true,
  },
  referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
}));
```

### 1.2 Security Headers Reference

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

## 2. CORS Deep Dive

```typescript
import cors from 'cors';

// DANGEROUS: wildcard with credentials
// This literally does not work — browsers reject Access-Control-Allow-Origin: * with credentials
app.use(cors({ origin: '*', credentials: true })); // WILL NOT WORK

// CORRECT: dynamic origin validation
const allowedOrigins = new Set([
  'https://app.example.com',
  'https://admin.example.com',
]);

app.use(cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (e.g., server-to-server, curl)
    if (!origin) return callback(null, true);

    if (allowedOrigins.has(origin)) {
      return callback(null, origin);
    }

    callback(new Error('CORS policy violation'));
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-CSRF-Token'],
  exposedHeaders: ['RateLimit-Remaining', 'RateLimit-Reset'],
  maxAge: 86400, // Preflight cache — 24 hours
}));
```

### 2.1 What Triggers a Preflight?

| Condition | Preflight? |
|-----------|------------|
| `GET` / `HEAD` / `POST` with simple headers | No (simple request) |
| `PUT` / `DELETE` / `PATCH` | Yes |
| `POST` with `Content-Type: application/json` | Yes |
| Any custom header (e.g., `Authorization`) | Yes |
| `Content-Type: application/x-www-form-urlencoded` | No |

### 2.2 Key CORS Rules

- `Access-Control-Allow-Origin: *` CANNOT be used with `credentials: true`
- `Vary: Origin` is required when origin is dynamic (prevents CDN caching issues)
- `Access-Control-Max-Age` caches preflight (set to 86400 for 24h)
- CORS is browser-enforced only — `curl` and server-to-server calls ignore it

**Performance tip**: Set `maxAge` to cache preflight responses. Without it, every cross-origin request with custom headers sends TWO requests.

---

## 3. Injection Prevention

### 3.1 Prototype Pollution

```typescript
// Attack: POST body with __proto__, constructor, or prototype
const malicious = JSON.parse('{"__proto__": {"isAdmin": true}}');
// If merged unsafely: Object.assign(target, malicious)
// Every object now has isAdmin === true

// Defense:
function safeMerge(target: any, source: any) {
  for (const key of Object.keys(source)) {
    if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
      continue; // Skip dangerous keys
    }
    target[key] = source[key];
  }
  return target;
}
// Better: use Map instead of plain objects, or Object.create(null)
```

### 3.2 ReDoS (Regular Expression Denial of Service)

```typescript
// Vulnerable regex: /^(a+)+$/
// Input: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!'
// This causes catastrophic backtracking

// Defense: use re2 (Google's regex engine, no backtracking)
import RE2 from 're2';
const safeRegex = new RE2('^(a+)+$'); // Linear time guaranteed
```

### 3.3 SSRF (Server-Side Request Forgery)

```typescript
// Attack: user provides URL that resolves to internal network
const userUrl = 'http://169.254.169.254/latest/meta-data/iam/security-credentials/';

// Defense: validate URL before fetching
import { URL } from 'url';
import dns from 'dns/promises';

async function safeFetch(urlString: string): Promise<Response> {
  const url = new URL(urlString);

  // Block private IP ranges
  const addresses = await dns.resolve4(url.hostname);
  for (const addr of addresses) {
    if (isPrivateIP(addr)) {
      throw new Error('SSRF: private IP address detected');
    }
  }

  // Block metadata endpoints
  if (url.hostname === '169.254.169.254' || url.hostname === 'metadata.google.internal') {
    throw new Error('SSRF: metadata endpoint blocked');
  }

  return fetch(urlString, { redirect: 'error' }); // Block redirects to internal
}
```

### 3.4 SQL Injection

Always use parameterized queries (covered in detail in file 02). At the ORM level, Prisma parameterizes by default. For raw queries, use tagged template literals.

---

## 4. Secret Management

### 4.1 HashiCorp Vault Integration

```typescript
import Vault from 'node-vault';

class VaultSecretManager {
  private client: Vault.Client;
  private leaseCache = new Map<string, { value: any; expiresAt: number }>();

  constructor() {
    this.client = Vault({
      endpoint: process.env.VAULT_ADDR,
      token: process.env.VAULT_TOKEN, // Or use AppRole/Kubernetes auth
    });
  }

  async getSecret(path: string): Promise<Record<string, string>> {
    const cached = this.leaseCache.get(path);
    if (cached && Date.now() < cached.expiresAt) {
      return cached.value;
    }

    const result = await this.client.read(`secret/data/${path}`);
    const secrets = result.data.data;

    // Cache with lease duration
    this.leaseCache.set(path, {
      value: secrets,
      expiresAt: Date.now() + (result.lease_duration || 300) * 1000,
    });

    return secrets;
  }

  // Dynamic database credentials — Vault generates short-lived credentials
  async getDatabaseCredentials(): Promise<{ username: string; password: string }> {
    const result = await this.client.read('database/creds/my-role');
    return {
      username: result.data.username,
      password: result.data.password,
    };
    // These credentials are automatically revoked when the lease expires
  }
}
```

### 4.2 AWS Secrets Manager

```typescript
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';

class AWSSecretManager {
  private client: SecretsManagerClient;
  private cache = new Map<string, { value: string; fetchedAt: number }>();
  private readonly CACHE_TTL = 300_000; // 5 minutes

  constructor() {
    this.client = new SecretsManagerClient({ region: 'us-east-1' });
  }

  async getSecret(secretId: string): Promise<Record<string, string>> {
    const cached = this.cache.get(secretId);
    if (cached && Date.now() - cached.fetchedAt < this.CACHE_TTL) {
      return JSON.parse(cached.value);
    }

    const command = new GetSecretValueCommand({ SecretId: secretId });
    const response = await this.client.send(command);

    this.cache.set(secretId, {
      value: response.SecretString!,
      fetchedAt: Date.now(),
    });

    return JSON.parse(response.SecretString!);
  }
}

// Usage — fetch secrets at startup, not per-request
async function initializeApp() {
  const secrets = await secretManager.getSecret('prod/api/credentials');
  const dbUrl = secrets.DATABASE_URL;
  const jwtKey = secrets.JWT_PRIVATE_KEY;
  // Initialize services with secrets
}
```

**Rule**: Never store secrets in environment variables in production Kubernetes. Use mounted secrets from Vault/AWS Secrets Manager, or use init containers that fetch secrets before the main container starts.

---

## 5. Zero-Trust Architecture

Zero trust means: never trust, always verify. Every request is authenticated and authorized regardless of network location.

```typescript
// 1. Verify identity on every request (no network-based trust)
app.use(async (req, res, next) => {
  // Even internal services must present credentials
  const identity = await verifyServiceIdentity(req);
  if (!identity) return res.status(401).json({ error: 'Identity required' });

  req.serviceIdentity = identity;
  next();
});

// 2. Least-privilege access
app.use(async (req, res, next) => {
  const allowed = await policyEngine.evaluate({
    subject: req.serviceIdentity,
    action: req.method,
    resource: req.path,
    context: {
      sourceIP: req.ip,
      timestamp: Date.now(),
      requestId: req.id,
    },
  });

  if (!allowed) {
    await auditLog.record({
      event: 'access_denied',
      subject: req.serviceIdentity,
      resource: req.path,
    });
    return res.status(403).json({ error: 'Access denied' });
  }

  next();
});

// 3. Log everything
app.use((req, res, next) => {
  res.on('finish', () => {
    auditLog.record({
      event: 'request_completed',
      subject: req.serviceIdentity,
      method: req.method,
      path: req.path,
      statusCode: res.statusCode,
      duration: Date.now() - req.startTime,
      requestId: req.id,
    });
  });
  next();
});
```

---

## 6. Audit Logging

### 6.1 Structured Audit Logging

```typescript
interface AuditEvent {
  timestamp: string;
  eventType: 'auth' | 'access' | 'mutation' | 'admin';
  action: string;
  actor: {
    type: 'user' | 'service' | 'system';
    id: string;
    ip?: string;
    userAgent?: string;
  };
  resource: {
    type: string;
    id: string;
  };
  outcome: 'success' | 'failure' | 'error';
  metadata: Record<string, unknown>;
  requestId: string;
}

class AuditLogger {
  // Write-ahead to a durable store — audit logs MUST NOT be lossy
  async log(event: AuditEvent): Promise<void> {
    // Append-only table — no UPDATE or DELETE permissions
    await db.$executeRaw`
      INSERT INTO audit_log (
        timestamp, event_type, action, actor_type, actor_id,
        actor_ip, resource_type, resource_id, outcome, metadata, request_id
      ) VALUES (
        ${event.timestamp}, ${event.eventType}, ${event.action},
        ${event.actor.type}, ${event.actor.id}, ${event.actor.ip},
        ${event.resource.type}, ${event.resource.id}, ${event.outcome},
        ${JSON.stringify(event.metadata)}::jsonb, ${event.requestId}
      )
    `;

    // Also stream to immutable storage (S3, CloudWatch, etc.)
    await this.streamToImmutableStore(event);
  }
}
```

### 6.2 Tamper-Proof Audit Trails

```typescript
// Hash chain for tamper detection
class HashChainAuditLogger {
  private previousHash: string = 'genesis';

  async log(event: AuditEvent): Promise<void> {
    const eventString = JSON.stringify(event);
    const currentHash = crypto
      .createHash('sha256')
      .update(`${this.previousHash}:${eventString}`)
      .digest('hex');

    await db.auditLog.create({
      data: {
        ...event,
        previousHash: this.previousHash,
        currentHash,
      },
    });

    this.previousHash = currentHash;
  }

  // Verification: walk the chain and verify each hash
  async verifyIntegrity(): Promise<boolean> {
    const logs = await db.auditLog.findMany({ orderBy: { timestamp: 'asc' } });
    let expectedPreviousHash = 'genesis';

    for (const log of logs) {
      if (log.previousHash !== expectedPreviousHash) return false;

      const computed = crypto
        .createHash('sha256')
        .update(`${log.previousHash}:${JSON.stringify(log.event)}`)
        .digest('hex');

      if (computed !== log.currentHash) return false;
      expectedPreviousHash = log.currentHash;
    }

    return true;
  }
}
```

---

## 7. Security Testing Checklist

1. **Authentication bypass**: Test expired tokens, manipulated claims, missing auth headers
2. **Authorization escalation**: Access resources of other users/tenants
3. **Injection**: SQL, NoSQL, command injection, template injection
4. **Prototype pollution**: Send `__proto__` in JSON payloads
5. **SSRF**: Submit internal URLs in any URL-accepting fields
6. **ReDoS**: Submit long strings to regex-validated fields
7. **Path traversal**: Submit `../../etc/passwd` in file paths
8. **Race conditions**: Concurrent requests on financial operations
9. **Rate limit bypass**: Rotate IPs, vary headers, use IPv4/IPv6
10. **Header injection**: CRLF in header values

---

## 8. Summary of Key Principles

Security is not a feature — it is a property of the system.

1. **RS256 over HS256** in distributed systems. Always.
2. **Short-lived access tokens + refresh token rotation** is the pragmatic auth pattern.
3. **SameSite cookies have mostly killed CSRF**, but defense-in-depth still matters.
4. **Rate limiting must be distributed** (Redis) and handle Redis failures gracefully.
5. **Zod for runtime validation** at every API boundary.
6. **CORS is not security** — it is a browser policy. Server-to-server calls ignore it entirely.
7. **Supply chain attacks are the new frontier** — lockfile integrity and dependency auditing are non-negotiable.

---

## 9. Interview Questions

### Architecture-Level Questions

**Q: You're designing auth for a system with 50 microservices. How do you handle authentication and authorization?**

Strong answer pattern:
- OAuth2 with a central authorization server (Keycloak, Auth0, or custom)
- RS256/ES256 JWTs — public keys distributed via JWKS endpoint
- Short-lived access tokens (5-15 min), no revocation check at resource servers
- Refresh tokens with rotation, stored in the auth service database
- Service-to-service auth via client credentials flow with scoped permissions
- API gateway handles token validation to avoid duplicating auth logic in every service
- Fine-grained authorization via policy engine (OPA, Cedar) or embedded claims

**Q: A security audit found that your JWT-based auth has no revocation mechanism. The business requires instant logout. What do you do?**

Strong answer pattern:
- Immediate: Add a Redis-based token blocklist, keyed by `jti` claim with TTL matching token expiry
- Short-term: Reduce access token lifetime to 5 minutes; revocation only needed for refresh tokens
- Evaluate: If revocation check is needed on every request anyway, question whether JWTs add value over opaque tokens with centralized validation
- Trade-off discussion: Every revocation check adds latency and a dependency; the question is how much "instant" matters (5 minutes of exposure vs true instant revocation)

**Q: Walk me through how you would implement CORS for an API that serves multiple front-end origins, including a mobile app using a WebView.**

Strong answer pattern:
- Dynamic origin validation against an allowlist (not `*`, which cannot be used with credentials)
- Distinguish between browser requests (have `Origin` header) and server/mobile requests (may not)
- Preflight caching via `Access-Control-Max-Age`
- `Vary: Origin` header to prevent CDN caching issues
- WebView consideration: some WebViews send `null` origin — handle explicitly
- Expose rate limit headers via `Access-Control-Expose-Headers`

### Debugging Questions

**Q: Users report intermittent 401 errors. JWTs are validated correctly. What do you investigate?**

- Clock skew between servers (JWT `exp`/`nbf` validation fails with even a few seconds of drift)
- JWKS key rotation mid-flight (token signed with old key, server only has new key)
- Load balancer session affinity issues (some instances have stale JWKS cache)
- Token size exceeding header limits (some proxies truncate headers at 8KB)
- Race condition in refresh token rotation (concurrent requests both try to use the same refresh token)

**Q: Your rate limiter is letting through 2x the configured limit. What is wrong?**

- Multiple application instances with local (non-distributed) counters
- Redis pipeline race condition (GET then SET is not atomic — use INCR or Lua scripts)
- Time window boundary edge case (request lands at the boundary of two windows)
- Load balancer distributing by different keys than the rate limiter

### Code Review Questions

**Q: Review this authentication middleware. What are the vulnerabilities?**

```typescript
// Intentionally vulnerable — find the issues
app.use((req, res, next) => {
  const token = req.headers.authorization;
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch {
    res.status(401).send('Unauthorized');
  }
});
```

Issues:
1. No `Bearer ` prefix stripping — `jwt.verify` will fail on `Bearer <token>`
2. No algorithm restriction — vulnerable to `alg: none` attack
3. Using symmetric key (`JWT_SECRET`) — implies HS256 across all services
4. No audience/issuer validation — any JWT signed with this secret is accepted
5. `decoded` contains unvalidated user data placed directly on `req.user`
6. No type safety on `decoded` — runtime crash risk on missing claims
7. If `JWT_SECRET` is undefined, behavior is library-dependent (may accept any token)

**Q: What is the difference between `httpOnly`, `secure`, and `sameSite` cookie attributes? Which is the most critical for session security?**

- `httpOnly` prevents JavaScript access (XSS mitigation — most critical for session cookies)
- `secure` restricts cookie to HTTPS connections (prevents transmission over plain HTTP)
- `sameSite=Lax/Strict` restricts cross-site sending (CSRF mitigation — browsers now default to Lax)

All three are needed together. `httpOnly` is the most critical for preventing session hijacking via XSS. `secure` is required in production. `sameSite` has largely killed CSRF in modern browsers but defense-in-depth still applies.

**Q: How do you prevent the `alg: none` JWT attack?**

Pass an explicit algorithm or allowlist to `jwt.verify()`:

```typescript
// Correct — explicit algorithm
jwt.verify(token, publicKey, { algorithms: ['RS256'] });

// Correct — allowlist
jwt.verify(token, getSigningKey, { algorithms: ['RS256', 'ES256'] });

// Vulnerable — no algorithm restriction
jwt.verify(token, publicKey); // Library may accept 'none'
```

Always pass `{ algorithms: [...] }` as the third argument. Never accept `alg: none`.
