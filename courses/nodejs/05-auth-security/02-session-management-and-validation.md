# 02 — Session Stores, Cookie Security, CSRF, and Input Validation with Zod/Joi

> Assumes JWT/OAuth2 fundamentals from file 01. Covers stateful session patterns, cookie configuration, CSRF defenses, and runtime input validation.

---

## 1. Session Management

### 1.1 Cookie-Based vs Token-Based Sessions

Cookie-based sessions store state server-side (session store) and track users by an opaque session ID. Token-based sessions embed state in the token (JWT). The choice affects where revocation happens and how you scale.

```typescript
// Cookie-based session (traditional)
import session from 'express-session';
import RedisStore from 'connect-redis';

app.use(session({
  store: new RedisStore({ client: redisClient }),
  secret: process.env.SESSION_SECRET!,
  name: '__Host-sid', // __Host- prefix enforces secure + path=/
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',       // 'strict' breaks OAuth redirects
    maxAge: 24 * 60 * 60 * 1000,
    domain: undefined,      // Do not set — __Host- prefix requires it
    path: '/',
  },
}));
```

### 1.2 Cookie Security Settings

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

**Cookie prefixes:**
- `__Host-`: Must be `Secure`, must not have `Domain`, must have `Path=/`. Prevents subdomain attacks.
- `__Secure-`: Must be `Secure`. Less restrictive.

### 1.3 Session Fixation Prevention

```typescript
// ALWAYS regenerate session ID after authentication state changes
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);

  // Regenerate to prevent session fixation
  req.session.regenerate((err) => {
    if (err) return res.status(500).send('Session error');

    req.session.userId = user.id;
    req.session.authenticatedAt = Date.now();
    req.session.ipAddress = req.ip;

    req.session.save((err) => {
      if (err) return res.status(500).send('Session error');
      res.json({ success: true });
    });
  });
});

// Also regenerate on privilege escalation (e.g., 2FA completion)
app.post('/verify-2fa', async (req, res) => {
  const valid = await verify2FA(req.session.userId, req.body.code);

  req.session.regenerate((err) => {
    req.session.userId = req.session.userId; // preserve
    req.session.twoFactorVerified = true;
    req.session.save(() => res.json({ success: true }));
  });
});
```

### 1.4 Session Store Comparison

| Store | Latency | Scalability | Persistence | Use Case |
|-------|---------|-------------|-------------|----------|
| In-memory | <1ms | Single process | None | Development only |
| Redis | 1-5ms | Cluster | Configurable | Production default |
| PostgreSQL | 5-20ms | Read replicas | Full | When Redis is overkill |
| DynamoDB | 5-15ms | Infinite | Full | AWS-native stacks |

---

## 2. CSRF Protection

### 2.1 The SameSite Revolution

`SameSite=Lax` is now the default in all major browsers. This means cross-site requests from top-level navigation (links) send cookies, but cross-site POST/AJAX/iframe requests do not.

```
SameSite=Strict  -> Cookie never sent cross-site (breaks OAuth, payment redirects)
SameSite=Lax     -> Cookie sent on top-level GET navigations only (default)
SameSite=None    -> Cookie always sent (requires Secure flag)
```

**Is CSRF dead?** Mostly, for modern browsers with `SameSite=Lax`. But defense-in-depth still matters.

### 2.2 Defense-in-Depth: Synchronizer Token Pattern

```typescript
import crypto from 'crypto';

// Generate CSRF token tied to the session
function generateCsrfToken(sessionId: string): string {
  const secret = process.env.CSRF_SECRET!;
  const token = crypto.randomBytes(32).toString('hex');

  const signature = crypto
    .createHmac('sha256', secret)
    .update(`${sessionId}:${token}`)
    .digest('hex');

  return `${token}.${signature}`;
}

// Validate
function validateCsrfToken(token: string, sessionId: string): boolean {
  const [randomPart, signature] = token.split('.');
  const expected = crypto
    .createHmac('sha256', process.env.CSRF_SECRET!)
    .update(`${sessionId}:${randomPart}`)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(signature, 'hex'),
    Buffer.from(expected, 'hex')
  );
}
```

### 2.3 Double Submit Cookie Pattern

```typescript
// Set CSRF token as a cookie AND require it in headers
app.use((req, res, next) => {
  if (!req.cookies['csrf-token']) {
    const token = crypto.randomBytes(32).toString('hex');
    res.cookie('csrf-token', token, {
      httpOnly: false, // Must be readable by JavaScript
      secure: true,
      sameSite: 'strict',
    });
  }
  next();
});

// Validation middleware
app.use((req, res, next) => {
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(req.method)) {
    const cookieToken = req.cookies['csrf-token'];
    const headerToken = req.headers['x-csrf-token'];

    if (!cookieToken || cookieToken !== headerToken) {
      return res.status(403).json({ error: 'CSRF validation failed' });
    }
  }
  next();
});
```

---

## 3. Rate Limiting

### 3.1 Algorithms

**Token Bucket**: Tokens accumulate at a fixed rate. Each request consumes one token. Allows bursts up to the bucket size.

**Sliding Window Log**: Track timestamps of each request. Count requests in the last N seconds. Precise but memory-intensive.

**Sliding Window Counter**: Hybrid — use fixed window counts with weighted interpolation. Best balance of accuracy and memory.

### 3.2 Rate Limiting Algorithms (Cheat Sheet)

| Algorithm | Burst Handling | Memory | Accuracy | Complexity |
|-----------|---------------|--------|----------|------------|
| Token Bucket | Allows bursts up to bucket size | Low (2 values per key) | Good | Low |
| Leaky Bucket | Smooths out bursts | Low (2 values per key) | Good | Low |
| Fixed Window | Allows 2x burst at boundary | Low (1 counter per key) | Poor at edges | Very low |
| Sliding Window Log | No boundary issues | High (all timestamps) | Exact | Medium |
| Sliding Window Counter | Minor boundary inaccuracy | Low (2 counters per key) | Very good | Medium |

### 3.3 Redis Rate Limit Template (Sliding Window Counter)

```typescript
// Sliding window counter with Redis
class SlidingWindowRateLimit {
  constructor(
    private redis: Redis,
    private windowMs: number,
    private maxRequests: number
  ) {}

  async isAllowed(key: string): Promise<{ allowed: boolean; remaining: number; retryAfter?: number }> {
    const now = Date.now();
    const currentWindow = Math.floor(now / this.windowMs);
    const previousWindow = currentWindow - 1;
    const windowProgress = (now % this.windowMs) / this.windowMs;

    const [currentCount, previousCount] = await this.redis
      .pipeline()
      .get(`rl:${key}:${currentWindow}`)
      .get(`rl:${key}:${previousWindow}`)
      .exec()
      .then(results => results!.map(([, v]) => Number(v) || 0));

    // Weighted count: full current + proportional previous
    const estimatedCount = previousCount * (1 - windowProgress) + currentCount;

    if (estimatedCount >= this.maxRequests) {
      const retryAfter = Math.ceil(
        (this.windowMs - (now % this.windowMs)) / 1000
      );
      return { allowed: false, remaining: 0, retryAfter };
    }

    // Increment current window
    await this.redis
      .pipeline()
      .incr(`rl:${key}:${currentWindow}`)
      .expire(`rl:${key}:${currentWindow}`, Math.ceil(this.windowMs / 1000) * 2)
      .exec();

    return {
      allowed: true,
      remaining: Math.max(0, this.maxRequests - Math.ceil(estimatedCount) - 1),
    };
  }
}
```

### 3.4 Concise Redis Template

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

### 3.5 Rate Limit Response Headers

```typescript
// Standard rate limit headers (RFC 6585 + draft-ietf-httpapi-ratelimit-headers)
function setRateLimitHeaders(res: Response, result: RateLimitResult) {
  res.setHeader('RateLimit-Limit', result.limit);
  res.setHeader('RateLimit-Remaining', result.remaining);
  res.setHeader('RateLimit-Reset', result.resetAt); // Unix timestamp

  if (!result.allowed) {
    res.setHeader('Retry-After', result.retryAfter);
    res.status(429).json({
      error: 'Too Many Requests',
      retryAfter: result.retryAfter,
    });
  }
}
```

### 3.6 Distributed Rate Limiting

In multi-instance deployments, local rate limiting is ineffective. Use Redis as a centralized counter, but handle Redis failures gracefully:

```typescript
class ResilientRateLimiter {
  async check(key: string): Promise<RateLimitResult> {
    try {
      return await this.redisRateLimiter.check(key);
    } catch (error) {
      // Redis down — fail open or fail closed?
      // Fail open: allow requests (availability over security)
      // Fail closed: reject requests (security over availability)
      // Pragmatic: fail open with local fallback
      this.logger.error('Redis rate limit unavailable, using local fallback');
      return this.localRateLimiter.check(key);
    }
  }
}
```

---

## 4. Input Validation

### 4.1 Zod for Runtime Validation

```typescript
import { z } from 'zod';

// Define schemas with full type inference
const CreateUserSchema = z.object({
  email: z.string().email().max(255).toLowerCase(),
  password: z.string()
    .min(12, 'Password must be at least 12 characters')
    .regex(/[A-Z]/, 'Must contain uppercase')
    .regex(/[0-9]/, 'Must contain a number')
    .regex(/[^A-Za-z0-9]/, 'Must contain a special character'),
  name: z.string().min(1).max(100).trim(),
  role: z.enum(['user', 'admin']).default('user'),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

type CreateUserInput = z.infer<typeof CreateUserSchema>;

// Middleware factory
function validate<T extends z.ZodSchema>(schema: T) {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req.body);
    if (!result.success) {
      return res.status(400).json({
        error: 'Validation failed',
        details: result.error.flatten(),
      });
    }
    req.body = result.data; // Use parsed (and transformed) data
    next();
  };
}

app.post('/users', validate(CreateUserSchema), createUserHandler);
```

### 4.2 Zod Template (Cheat Sheet)

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

### 4.3 SQL Injection Prevention

Parameterized queries are non-negotiable. Every ORM and query builder supports them:

```typescript
// NEVER do this
const query = `SELECT * FROM users WHERE email = '${email}'`;

// Prisma — parameterized by default
const user = await prisma.user.findUnique({ where: { email } });

// Raw queries — ALWAYS use parameterized form
const users = await prisma.$queryRaw`
  SELECT * FROM users WHERE email = ${email}
`;
// Prisma uses tagged template literals to parameterize
```

### 4.4 Path Traversal Prevention

```typescript
import path from 'path';

function safeResolvePath(basePath: string, userInput: string): string {
  const resolved = path.resolve(basePath, userInput);

  // Ensure the resolved path is within the base directory
  if (!resolved.startsWith(path.resolve(basePath) + path.sep) &&
      resolved !== path.resolve(basePath)) {
    throw new ForbiddenError('Path traversal detected');
  }

  return resolved;
}

// Usage
app.get('/files/:filename', (req, res) => {
  const safePath = safeResolvePath('/app/uploads', req.params.filename);
  res.sendFile(safePath);
});
```

---

## 5. Mutual TLS (mTLS)

In mTLS, both client and server present certificates. Common in service mesh architectures and zero-trust environments.

```typescript
import https from 'https';
import fs from 'fs';

// Server requiring client certificates
const server = https.createServer({
  key: fs.readFileSync('./server-key.pem'),
  cert: fs.readFileSync('./server-cert.pem'),
  ca: [fs.readFileSync('./client-ca.pem')],    // CA that signed client certs
  requestCert: true,                             // Request client certificate
  rejectUnauthorized: true,                      // Reject if no valid cert
}, app);

// Middleware to extract client identity
app.use((req, res, next) => {
  const cert = (req.socket as TLSSocket).getPeerCertificate();

  if (!cert || !cert.subject) {
    return res.status(401).json({ error: 'Client certificate required' });
  }

  req.clientIdentity = {
    cn: cert.subject.CN,          // Common Name
    org: cert.subject.O,          // Organization
    fingerprint: cert.fingerprint, // SHA-1 fingerprint
    serialNumber: cert.serialNumber,
    validTo: cert.valid_to,
  };

  next();
});
```

In Kubernetes with Istio or Linkerd, mTLS is transparent — the sidecar proxy handles certificate rotation and verification.

```yaml
# Istio PeerAuthentication — enforce mTLS for all services
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT
```

---

## 6. Dependency Security

### 6.1 Supply Chain Attacks

Real-world incidents: `event-stream` (2018), `ua-parser-js` (2021), `colors`/`faker` (2022).

```bash
# Audit dependencies
npm audit --production    # Only production deps
npm audit --audit-level=high  # Fail on high+ severity

# Lock file integrity
npm ci    # Uses package-lock.json exactly -- fails if lock file is out of date
```

### 6.2 Lockfile Integrity

```typescript
// package.json script
{
  "scripts": {
    "preinstall": "npx lockfile-lint --path package-lock.json --type npm --allowed-hosts npm --validate-https"
  }
}
```

### 6.3 Automated Dependency Updates (Renovate)

```yaml
# Renovate configuration for security-focused updates
{
  "extends": ["config:base", ":semanticCommits"],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"],
    "automerge": true
  },
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "automerge": true
    },
    {
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "reviewers": ["team:security"]
    }
  ]
}
```
