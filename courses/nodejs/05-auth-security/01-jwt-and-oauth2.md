# 01 — JWT Structure, Signing, Access/Refresh Tokens, OAuth2 Flows, and PKCE

> Deep familiarity with HTTP, TLS, cryptographic primitives, and prior production auth systems assumed. Skips basics entirely — focuses on engineering decisions, trade-offs, and failure modes.

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

### 1.2 JWT Structure Diagram

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

### 1.3 Signing Algorithms

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

### 1.4 Algorithm Quick Reference

| Algorithm | Type | Key | Use Case |
|-----------|------|-----|----------|
| HS256 | Symmetric | Shared secret | Single-service, simple setups |
| RS256 | Asymmetric | RSA key pair | Distributed systems (default choice) |
| ES256 | Asymmetric | ECDSA P-256 | Smaller tokens, mobile-friendly |
| EdDSA | Asymmetric | Ed25519 | Best performance asymmetric |
| PS256 | Asymmetric | RSA-PSS | FIPS-compliant environments |

### 1.5 HS256 vs RS256: When to Use Which

| Concern | HS256 | RS256 |
|---------|-------|-------|
| Key distribution | Single secret shared across all services | Public key freely distributed |
| Microservices | Dangerous — every service has signing capability | Preferred — only auth service holds private key |
| Performance | ~10x faster signing/verification | Slower, but irrelevant at typical scale |
| Key rotation | Must coordinate secret rotation everywhere | Rotate private key; publish new public key via JWKS |
| `alg: none` attack surface | Higher risk if library is misconfigured | Lower risk with explicit key type checking |

**Expert insight**: Always use RS256 (or ES256/EdDSA) in distributed systems. HS256 means any compromised microservice can forge tokens for the entire system. The performance difference is negligible — you are not signing millions of tokens per second.

---

## 2. JWKS (JSON Web Key Sets)

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

---

## 3. Access/Refresh Tokens and Revocation

### 3.1 Refresh Token Rotation

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

### 3.2 Token Revocation Strategies

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

### 3.3 Token Revocation Decision Tree

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

### 3.4 The Stateless vs Stateful Debate

**Stateless JWTs are a lie in production.** The moment you need revocation, you have state. The question is where that state lives and how stale you tolerate it.

Pragmatic approach for most systems:
- Access tokens: Short-lived (5-15 min), stateless verification, no revocation check
- Refresh tokens: Long-lived, stateful (stored in DB), checked on every use
- Critical operations: Always validate against a central authority regardless

---

## 4. OAuth 2.0 and OpenID Connect

### 4.1 Authorization Code Flow + PKCE

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

### 4.2 Authorization Code + PKCE Flow Diagram

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

### 4.3 Why Implicit Flow Is Deprecated

The implicit flow returned tokens directly in the URL fragment (`#access_token=...`). Problems:
- Tokens exposed in browser history, referrer headers, and server logs
- No way to use refresh tokens (browser cannot keep secrets)
- No PKCE protection against authorization code interception
- Token leakage via open redirector vulnerabilities

**OAuth 2.1 removes implicit flow entirely.** Use authorization code + PKCE for all clients.

### 4.4 Client Credentials Flow

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

### 4.5 Grant Type Quick Reference

| Grant Type | Client Type | Use Case |
|------------|-------------|----------|
| Authorization Code + PKCE | Public/Confidential | All user-facing apps (default) |
| Client Credentials | Confidential | Machine-to-machine (no user) |
| Device Authorization | Input-constrained | Smart TV, CLI tools |
| Refresh Token | Any | Exchange for new access token |
| ~~Implicit~~ | ~~Public~~ | **DEPRECATED in OAuth 2.1** |
| ~~Password~~ | ~~Confidential~~ | **DEPRECATED in OAuth 2.1** |

### 4.6 OIDC: ID Tokens vs Access Tokens

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

## 5. PASETO vs JWT (Deep Dive)

PASETO (Platform-Agnostic Security Tokens) was designed to fix JWT's footguns. The critical difference: PASETO removes algorithm negotiation entirely.

### 5.1 JWT Pitfalls That PASETO Eliminates

| JWT Footgun | PASETO Solution |
|-------------|-----------------|
| `alg: none` attack | No algorithm header — version determines everything |
| Algorithm confusion (RS256 vs HS256) | Each version has exactly one algorithm |
| Weak algorithms allowed | Only modern, secure algorithms |
| Complex JOSE ecosystem | Single, opinionated specification |

### 5.2 PASETO Versions

```
v1 — Compatibility: AES-256-CTR + HMAC-SHA384 (local), RSA-PSS (public)
v2 — Recommended: XChaCha20-Poly1305 (local), Ed25519 (public)
v3 — NIST-compliant: AES-256-CTR + HMAC-SHA384 (local), ECDSA P-384 (public)
v4 — Latest: XChaCha20-Poly1305 (local), Ed25519 (public) — improved KDF
```

### 5.3 When to Use PASETO Over JWT

- Greenfield projects where you control both sides
- When you want to eliminate algorithm confusion attacks by design
- When you need encrypted tokens (PASETO local mode) rather than just signed ones
- When ecosystem compatibility is not a concern (JWT has vastly wider tooling)

### 5.4 When JWT Still Wins

- Integration with third-party IdPs (Auth0, Okta, Keycloak all speak JWT)
- OIDC compliance (the spec mandates JWT for ID tokens)
- Existing infrastructure and tooling

---

## 6. WebAuthn / Passkeys (Deep Dive)

WebAuthn replaces passwords with public-key cryptography anchored to hardware authenticators or platform biometrics.

### 6.1 Registration Flow

```typescript
import {
  generateRegistrationOptions,
  verifyRegistrationResponse,
} from '@simplewebauthn/server';

// Step 1: Generate challenge
async function startRegistration(user: User) {
  const options = await generateRegistrationOptions({
    rpName: 'Example Corp',
    rpID: 'example.com',
    userID: user.id,
    userName: user.email,
    attestationType: 'none', // 'direct' if you need to verify authenticator model
    authenticatorSelection: {
      residentKey: 'preferred',        // Discoverable credentials (passkeys)
      userVerification: 'preferred',   // Biometric/PIN when available
      authenticatorAttachment: 'platform', // Remove for cross-platform (USB keys)
    },
    excludeCredentials: user.existingCredentials.map(c => ({
      id: c.credentialId,
      type: 'public-key',
    })),
  });

  // Store challenge in session for verification
  await sessionStore.set(user.id, { challenge: options.challenge });
  return options;
}
```

### 6.2 Counter Check

If the new counter is less than or equal to the stored counter, the authenticator may have been cloned. Flag the account.

---

## 7. API Key Design (Deep Dive)

### 7.1 Well-Designed API Key Format

```typescript
// Format: prefix_environment_randomBytes
// Example: myapp_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4

class APIKeyService {
  private readonly KEY_PREFIX = 'sk';
  private readonly KEY_BYTES = 32;

  async generateKey(userId: string, options: KeyOptions): Promise<{
    key: string;         // Show to user ONCE
    keyId: string;       // Public identifier
    keyPrefix: string;   // For display (sk_live_a1b2...)
  }> {
    const environment = options.environment; // 'live' | 'test'
    const randomPart = crypto.randomBytes(this.KEY_BYTES).toString('hex');
    const fullKey = `${this.KEY_PREFIX}_${environment}_${randomPart}`;

    // Store ONLY the hash
    const keyHash = await argon2.hash(fullKey, {
      type: argon2.argon2id,
      memoryCost: 65536,
      timeCost: 3,
      parallelism: 4,
    });

    const keyId = crypto.randomUUID();
    const keyPrefix = fullKey.substring(0, 12); // For display: sk_live_a1b2

    await db.apiKey.create({
      data: {
        id: keyId,
        userId,
        keyHash,
        keyPrefix,
        environment,
        scopes: options.scopes,
        rateLimit: options.rateLimit,
        expiresAt: options.expiresAt,
        lastUsedAt: null,
        ipAllowlist: options.ipAllowlist || [],
      },
    });

    return { key: fullKey, keyId, keyPrefix };
  }
}
```
