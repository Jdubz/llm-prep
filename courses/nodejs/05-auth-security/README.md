# Module 05: Authentication & Security

## Prerequisites

This module assumes deep familiarity with HTTP, TLS, cryptographic primitives, and prior production experience with auth systems. We skip the basics entirely and focus on the engineering decisions, trade-offs, and failure modes that separate senior engineers from architects.

---

## 1. JSON Web Tokens (JWT)

### 1.1 Token Structure

A JWT consists of three Base64URL-encoded segments separated by dots:

```
header.payload.signature
```

```typescript
// Decoded structure
interface JWTHeader {
  alg: 'RS256' | 'HS256' | 'ES256' | 'PS256' | 'EdDSA';
  typ: 'JWT';
  kid?: string; // Key ID — critical for key rotation
}

interface JWTPayload {
  // Registered claims (RFC 7519)
  iss: string;   // Issuer
  sub: string;   // Subject (user ID)
  aud: string;   // Audience
  exp: number;   // Expiration (Unix timestamp)
  nbf: number;   // Not Before
  iat: number;   // Issued At
  jti: string;   // JWT ID (unique identifier for revocation)

  // Custom claims
  roles: string[];
  permissions: string[];
  tenant_id?: string;
}
```

**Interview trap**: The payload is encoded, not encrypted. Anyone can decode it. Never put secrets in JWT claims. The signature only guarantees integrity, not confidentiality.

### 1.2 Signing Algorithms: RS256 vs HS256

```typescript
// HS256 — Symmetric (shared secret)
import jwt from 'jsonwebtoken';

const token = jwt.sign(payload, 'shared-secret', { algorithm: 'HS256' });
// Same secret used to sign AND verify
jwt.verify(token, 'shared-secret');
```

```typescript
// RS256 — Asymmetric (public/private key pair)
import { readFileSync } from 'fs';

const privateKey = readFileSync('./private.pem');
const publicKey = readFileSync('./public.pem');

const token = jwt.sign(payload, privateKey, { algorithm: 'RS256' });
// Only the public key is needed to verify
jwt.verify(token, publicKey);
```

**When to use which:**

| Concern | HS256 | RS256 |
|---------|-------|-------|
| Key distribution | Single secret shared across all services | Public key freely distributed |
| Microservices | Dangerous — every service has signing capability | Preferred — only auth service holds private key |
| Performance | ~10x faster signing/verification | Slower, but irrelevant at typical scale |
| Key rotation | Must coordinate secret rotation everywhere | Rotate private key; publish new public key via JWKS |
| `alg: none` attack surface | Higher risk if library is misconfigured | Lower risk with explicit key type checking |

**Expert insight**: Always use RS256 (or ES256/EdDSA) in distributed systems. HS256 means any compromised microservice can forge tokens for the entire system. The performance difference is negligible — you are not signing millions of tokens per second.

### 1.3 JWKS (JSON Web Key Sets)

```typescript
// Auth server exposes /.well-known/jwks.json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "2024-01-key",
      "use": "sig",
      "alg": "RS256",
      "n": "...",  // modulus
      "e": "AQAB"  // exponent
    }
  ]
}

// Resource server fetches and caches JWKS
import jwksClient from 'jwks-rsa';

const client = jwksClient({
  jwksUri: 'https://auth.example.com/.well-known/jwks.json',
  cache: true,
  cacheMaxAge: 600000, // 10 minutes
  rateLimit: true,
  jwksRequestsPerMinute: 10,
});

function getSigningKey(header: jwt.JwtHeader): Promise<string> {
  return new Promise((resolve, reject) => {
    client.getSigningKey(header.kid, (err, key) => {
      if (err) return reject(err);
      resolve(key!.getPublicKey());
    });
  });
}
```

### 1.4 Refresh Token Rotation

```typescript
// Refresh token rotation prevents replay attacks
class TokenService {
  async refreshTokens(refreshToken: string): Promise<TokenPair> {
    const stored = await this.tokenStore.findByToken(
      this.hash(refreshToken)
    );

    if (!stored) {
      // Token not found — possible replay attack
      // Revoke the ENTIRE token family
      await this.tokenStore.revokeFamily(stored?.familyId);
      throw new UnauthorizedError('Refresh token reuse detected');
    }

    if (stored.used) {
      // Already used — definite replay attack
      await this.tokenStore.revokeFamily(stored.familyId);
      await this.alertService.flagAccount(stored.userId);
      throw new UnauthorizedError('Refresh token reuse detected');
    }

    // Mark current token as used (not deleted)
    await this.tokenStore.markUsed(stored.id);

    // Issue new pair in the same family
    const newRefresh = crypto.randomBytes(32).toString('hex');
    await this.tokenStore.create({
      token: this.hash(newRefresh),
      familyId: stored.familyId,
      userId: stored.userId,
      expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
    });

    const accessToken = this.signAccessToken(stored.userId);
    return { accessToken, refreshToken: newRefresh };
  }

  private hash(token: string): string {
    return crypto.createHash('sha256').update(token).digest('hex');
  }
}
```

**Critical detail**: Store the hash of refresh tokens, never the raw value. If the database is compromised, hashed tokens cannot be used directly.

### 1.5 Token Revocation Strategies

JWTs are stateless by design — revocation requires reintroducing state:

| Strategy | Latency | Complexity | Consistency |
|----------|---------|------------|-------------|
| Short-lived tokens (5 min) | Eventual (up to TTL) | Low | Weak |
| Token blocklist (Redis) | Near-instant | Medium | Strong |
| Token versioning (user-level counter) | Near-instant | Medium | Strong |
| Event-driven revocation (pub/sub) | Sub-second | High | Eventual |

```typescript
// Token versioning approach
class TokenVersioningMiddleware {
  async validate(req: Request, res: Response, next: NextFunction) {
    const decoded = jwt.decode(req.token) as JWTPayload & { tokenVersion: number };

    // Check version against stored version
    const currentVersion = await redis.get(`token_version:${decoded.sub}`);

    if (decoded.tokenVersion !== Number(currentVersion)) {
      throw new UnauthorizedError('Token revoked');
    }

    next();
  }
}

// Revoke all tokens for a user — just increment the version
async function revokeAllTokens(userId: string): Promise<void> {
  await redis.incr(`token_version:${userId}`);
}
```

### 1.6 The Stateless vs Stateful Debate

**Stateless JWTs are a lie in production.** The moment you need revocation, you have state. The question is where that state lives and how stale you tolerate it.

Pragmatic approach for most systems:
- Access tokens: Short-lived (5-15 min), stateless verification, no revocation check
- Refresh tokens: Long-lived, stateful (stored in DB), checked on every use
- Critical operations: Always validate against a central authority regardless

---

## 2. OAuth 2.0 & OpenID Connect

### 2.1 Authorization Code Flow + PKCE

PKCE (Proof Key for Code Exchange) is now required for ALL clients per OAuth 2.1, not just public clients.

```typescript
// Step 1: Generate PKCE challenge
import crypto from 'crypto';

function generatePKCE() {
  const verifier = crypto.randomBytes(32)
    .toString('base64url'); // 43 chars minimum

  const challenge = crypto
    .createHash('sha256')
    .update(verifier)
    .digest('base64url');

  return { verifier, challenge };
}

// Step 2: Build authorization URL
function buildAuthUrl(pkce: { challenge: string }) {
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: CONFIG.clientId,
    redirect_uri: CONFIG.redirectUri,
    scope: 'openid profile email',
    state: crypto.randomBytes(16).toString('hex'),
    code_challenge: pkce.challenge,
    code_challenge_method: 'S256',
  });

  return `${CONFIG.authorizationEndpoint}?${params}`;
}

// Step 3: Exchange code for tokens
async function exchangeCode(code: string, verifier: string) {
  const response = await fetch(CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      redirect_uri: CONFIG.redirectUri,
      client_id: CONFIG.clientId,
      code_verifier: verifier, // Server hashes this and compares to stored challenge
    }),
  });

  return response.json(); // { access_token, id_token, refresh_token }
}
```

### 2.2 Why Implicit Flow Is Deprecated

The implicit flow returned tokens directly in the URL fragment (`#access_token=...`). Problems:
- Tokens exposed in browser history, referrer headers, and server logs
- No way to use refresh tokens (browser cannot keep secrets)
- No PKCE protection against authorization code interception
- Token leakage via open redirector vulnerabilities

**OAuth 2.1 removes implicit flow entirely.** Use authorization code + PKCE for all clients.

### 2.3 Client Credentials Flow

Machine-to-machine authentication without user involvement:

```typescript
// Service A authenticates to Service B
async function getM2MToken(): Promise<string> {
  const response = await fetch(CONFIG.tokenEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: CONFIG.serviceClientId,
      client_secret: CONFIG.serviceClientSecret,
      scope: 'service:read service:write',
      audience: 'https://api.internal.example.com',
    }),
  });

  const { access_token } = await response.json();
  return access_token;
}

// Cache the token, refresh before expiry
class M2MTokenManager {
  private token: string | null = null;
  private expiresAt: number = 0;

  async getToken(): Promise<string> {
    if (this.token && Date.now() < this.expiresAt - 30_000) {
      return this.token;
    }
    const { access_token, expires_in } = await this.fetchToken();
    this.token = access_token;
    this.expiresAt = Date.now() + expires_in * 1000;
    return this.token;
  }
}
```

### 2.4 OIDC: ID Tokens vs Access Tokens

| Property | ID Token | Access Token |
|----------|----------|--------------|
| Purpose | Authentication (who are you?) | Authorization (what can you do?) |
| Audience | Client application | Resource server (API) |
| Format | Always JWT | Opaque string or JWT |
| Validation | Client validates signature + claims | Resource server validates |
| Should be sent to API? | No | Yes |

**Common mistake**: Using the ID token as an API credential. The ID token is for the client to establish a user session. The access token is what gets sent to APIs.

```typescript
// Correct: validate ID token claims
function validateIdToken(idToken: string, nonce: string) {
  const decoded = jwt.verify(idToken, publicKey) as OIDCIdToken;

  assert(decoded.iss === CONFIG.issuer, 'Invalid issuer');
  assert(decoded.aud === CONFIG.clientId, 'Invalid audience');
  assert(decoded.nonce === nonce, 'Nonce mismatch — possible replay');
  assert(decoded.exp > Date.now() / 1000, 'Token expired');

  // at_hash validates that the access token belongs to this ID token
  if (decoded.at_hash) {
    const atHash = crypto
      .createHash('sha256')
      .update(accessToken)
      .digest()
      .subarray(0, 16) // Left half of hash
      .toString('base64url');
    assert(atHash === decoded.at_hash, 'Access token hash mismatch');
  }

  return decoded;
}
```

---

## 3. Session Management

### 3.1 Cookie-Based vs Token-Based Sessions

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

**Cookie prefixes** (`__Host-` and `__Secure-`):
- `__Host-`: Must be `Secure`, must not have `Domain`, must have `Path=/`. Prevents subdomain attacks.
- `__Secure-`: Must be `Secure`. Less restrictive.

### 3.2 Session Fixation Prevention

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

### 3.3 Session Store Comparison

| Store | Latency | Scalability | Persistence | Use Case |
|-------|---------|-------------|-------------|----------|
| In-memory | <1ms | Single process | None | Development only |
| Redis | 1-5ms | Cluster | Configurable | Production default |
| PostgreSQL | 5-20ms | Read replicas | Full | When Redis is overkill |
| DynamoDB | 5-15ms | Infinite | Full | AWS-native stacks |

---

## 4. CSRF Protection

### 4.1 The SameSite Revolution

`SameSite=Lax` is now the default in all major browsers. This means cross-site requests from top-level navigation (links) send cookies, but cross-site POST/AJAX/iframe requests do not.

```
SameSite=Strict  -> Cookie never sent cross-site (breaks OAuth, payment redirects)
SameSite=Lax     -> Cookie sent on top-level GET navigations only (default)
SameSite=None    -> Cookie always sent (requires Secure flag)
```

**Is CSRF dead?** Mostly, for modern browsers with `SameSite=Lax`. But defense-in-depth still matters:

### 4.2 Defense-in-Depth: Synchronizer Token Pattern

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

### 4.3 Double Submit Cookie Pattern

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

## 5. Rate Limiting

### 5.1 Algorithms

**Token Bucket**: Tokens accumulate at a fixed rate. Each request consumes one token. Allows bursts up to the bucket size.

**Sliding Window Log**: Track timestamps of each request. Count requests in the last N seconds. Precise but memory-intensive.

**Sliding Window Counter**: Hybrid — use fixed window counts with weighted interpolation. Best balance of accuracy and memory.

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

### 5.2 Rate Limit Response Headers

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

### 5.3 Distributed Rate Limiting

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

## 6. Input Validation

### 6.1 Zod for Runtime Validation

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

### 6.2 SQL Injection Prevention

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

### 6.3 Path Traversal Prevention

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

## 7. Security Headers

### 7.1 Helmet.js Configuration

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

### 7.2 CORS Deep Dive

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

**Preflight requests (`OPTIONS`)**: Triggered when:
- Method is not GET/HEAD/POST
- POST with Content-Type other than `application/x-www-form-urlencoded`, `multipart/form-data`, or `text/plain`
- Custom headers are present (e.g., `Authorization`)

**Performance tip**: Set `maxAge` to cache preflight responses. Without it, every cross-origin request with custom headers sends TWO requests.

---

## 8. Dependency Security

### 8.1 Supply Chain Attacks

Real-world incidents: `event-stream` (2018), `ua-parser-js` (2021), `colors`/`faker` (2022).

```bash
# Audit dependencies
npm audit --production    # Only production deps
npm audit --audit-level=high  # Fail on high+ severity

# Lock file integrity
npm ci    # Uses package-lock.json exactly — fails if lock file is out of date

# Check for typosquatting
npx socket npm info <package-name>
```

### 8.2 Lockfile Integrity

```jsonc
// package-lock.json includes integrity hashes
{
  "node_modules/express": {
    "version": "4.18.2",
    "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
    "integrity": "sha512-..." // Subresource Integrity hash
  }
}
```

```typescript
// CI pipeline should verify lockfile
// package.json script
{
  "scripts": {
    "preinstall": "npx lockfile-lint --path package-lock.json --type npm --allowed-hosts npm --validate-https"
  }
}
```

### 8.3 Automated Dependency Updates

```yaml
# Renovate configuration for security-focused updates
{
  "extends": ["config:base", ":semanticCommits"],
  "vulnerabilityAlerts": {
    "enabled": true,
    "labels": ["security"],
    "automerge": true  // Auto-merge security patches
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

---

## 9. Expert Interview Questions

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

---

## Summary

Security is not a feature — it is a property of the system. Key takeaways:

1. **RS256 over HS256** in distributed systems. Always.
2. **Short-lived access tokens + refresh token rotation** is the pragmatic auth pattern.
3. **SameSite cookies have mostly killed CSRF**, but defense-in-depth still matters.
4. **Rate limiting must be distributed** (Redis) and handle Redis failures gracefully.
5. **Zod for runtime validation** at every API boundary.
6. **CORS is not security** — it is a browser policy. Server-to-server calls ignore it entirely.
7. **Supply chain attacks are the new frontier** — lockfile integrity and dependency auditing are non-negotiable.
