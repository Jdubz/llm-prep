# Module 05 Deep Dive: Advanced Authentication & Security Topics

## 1. PASETO vs JWT

PASETO (Platform-Agnostic Security Tokens) was designed to fix JWT's footguns. The critical difference: PASETO removes algorithm negotiation entirely.

### JWT Pitfalls That PASETO Eliminates

| JWT Footgun | PASETO Solution |
|-------------|-----------------|
| `alg: none` attack | No algorithm header — version determines everything |
| Algorithm confusion (RS256 vs HS256) | Each version has exactly one algorithm |
| Weak algorithms allowed | Only modern, secure algorithms |
| Complex JOSE ecosystem | Single, opinionated specification |

### PASETO Versions

```
v1 — Compatibility: AES-256-CTR + HMAC-SHA384 (local), RSA-PSS (public)
v2 — Recommended: XChaCha20-Poly1305 (local), Ed25519 (public)
v3 — NIST-compliant: AES-256-CTR + HMAC-SHA384 (local), ECDSA P-384 (public)
v4 — Latest: XChaCha20-Poly1305 (local), Ed25519 (public) — improved KDF
```

```typescript
import { V4 } from 'paseto';

// PASETO public tokens (asymmetric — equivalent to signed JWT)
const { secretKey, publicKey } = await V4.generateKey('public');

const token = await V4.sign(
  {
    sub: 'user-123',
    iss: 'https://auth.example.com',
    aud: 'https://api.example.com',
    exp: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
    roles: ['admin'],
  },
  secretKey,
  {
    footer: { kid: '2024-key-1' }, // Footer is NOT encrypted, used for key ID
  }
);

// Verification — no algorithm negotiation needed
const payload = await V4.verify(token, publicKey, {
  issuer: 'https://auth.example.com',
  audience: 'https://api.example.com',
  clockTolerance: '30s',
});
```

```typescript
// PASETO local tokens (symmetric — encrypted + authenticated)
// Unlike JWT, local PASETO tokens are actually ENCRYPTED, not just signed
const symmetricKey = await V4.generateKey('local');

const encryptedToken = await V4.encrypt(
  { sub: 'user-123', sensitiveData: 'hidden' },
  symmetricKey
);

// Only holders of the symmetric key can decrypt
const decrypted = await V4.decrypt(encryptedToken, symmetricKey);
```

### When to Use PASETO Over JWT

- Greenfield projects where you control both sides
- When you want to eliminate algorithm confusion attacks by design
- When you need encrypted tokens (PASETO local mode) rather than just signed ones
- When ecosystem compatibility is not a concern (JWT has vastly wider tooling)

### When JWT Still Wins

- Integration with third-party IdPs (Auth0, Okta, Keycloak all speak JWT)
- OIDC compliance (the spec mandates JWT for ID tokens)
- Existing infrastructure and tooling

---

## 2. WebAuthn / Passkeys

WebAuthn replaces passwords with public-key cryptography anchored to hardware authenticators or platform biometrics.

### Registration Flow

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

// Step 2: Verify registration response from browser
async function completeRegistration(user: User, response: RegistrationResponseJSON) {
  const session = await sessionStore.get(user.id);

  const verification = await verifyRegistrationResponse({
    response,
    expectedChallenge: session.challenge,
    expectedOrigin: 'https://example.com',
    expectedRPID: 'example.com',
  });

  if (verification.verified && verification.registrationInfo) {
    // Store credential in database
    await db.credential.create({
      data: {
        userId: user.id,
        credentialId: Buffer.from(verification.registrationInfo.credentialID),
        publicKey: Buffer.from(verification.registrationInfo.credentialPublicKey),
        counter: verification.registrationInfo.counter,
        credentialBackedUp: verification.registrationInfo.credentialBackedUp,
        transports: response.response.transports,
      },
    });
  }
}
```

### Authentication Flow

```typescript
import {
  generateAuthenticationOptions,
  verifyAuthenticationResponse,
} from '@simplewebauthn/server';

async function startAuthentication(user?: User) {
  const options = await generateAuthenticationOptions({
    rpID: 'example.com',
    userVerification: 'preferred',
    // If user is known, scope to their credentials
    // If not (passkey login), omit allowCredentials for discoverable credentials
    allowCredentials: user?.credentials.map(c => ({
      id: c.credentialId,
      type: 'public-key',
      transports: c.transports,
    })),
  });

  return options;
}

async function completeAuthentication(
  response: AuthenticationResponseJSON,
  expectedChallenge: string
) {
  const credential = await db.credential.findUnique({
    where: { credentialId: Buffer.from(response.id, 'base64url') },
  });

  const verification = await verifyAuthenticationResponse({
    response,
    expectedChallenge,
    expectedOrigin: 'https://example.com',
    expectedRPID: 'example.com',
    authenticator: {
      credentialID: credential.credentialId,
      credentialPublicKey: credential.publicKey,
      counter: credential.counter,
    },
  });

  if (verification.verified) {
    // Update counter to detect cloned authenticators
    await db.credential.update({
      where: { id: credential.id },
      data: { counter: verification.authenticationInfo.newCounter },
    });
  }

  return verification.verified;
}
```

**Counter check**: If the new counter is less than or equal to the stored counter, the authenticator may have been cloned. Flag the account.

---

## 3. Mutual TLS (mTLS)

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

```typescript
// Client presenting its certificate
const agent = new https.Agent({
  key: fs.readFileSync('./client-key.pem'),
  cert: fs.readFileSync('./client-cert.pem'),
  ca: [fs.readFileSync('./server-ca.pem')],
});

const response = await fetch('https://internal-api.example.com/data', {
  agent,
});
```

### mTLS in Practice: Service Mesh

In Kubernetes with Istio or Linkerd, mTLS is transparent — the sidecar proxy handles certificate rotation and verification. Your Node.js code does not need to manage certificates directly.

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

## 4. API Key Design

### Anatomy of a Well-Designed API Key

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
        scopes: options.scopes,      // ['read:users', 'write:orders']
        rateLimit: options.rateLimit, // Custom per-key rate limit
        expiresAt: options.expiresAt,
        lastUsedAt: null,
        ipAllowlist: options.ipAllowlist || [],
      },
    });

    return { key: fullKey, keyId, keyPrefix };
  }

  async validateKey(key: string): Promise<APIKeyRecord | null> {
    const prefix = key.substring(0, 12);

    // Find candidate keys by prefix (fast lookup)
    const candidates = await db.apiKey.findMany({
      where: {
        keyPrefix: prefix,
        revokedAt: null,
        expiresAt: { gt: new Date() },
      },
    });

    // Verify hash against candidates
    for (const candidate of candidates) {
      if (await argon2.verify(candidate.keyHash, key)) {
        // Update last used timestamp (fire-and-forget)
        db.apiKey.update({
          where: { id: candidate.id },
          data: { lastUsedAt: new Date() },
        }).catch(() => {}); // Non-critical

        return candidate;
      }
    }

    return null;
  }
}
```

### Key Rotation Strategy

```typescript
class KeyRotationService {
  async rotateKey(oldKeyId: string): Promise<{ newKey: string }> {
    const oldKey = await db.apiKey.findUnique({ where: { id: oldKeyId } });

    // Generate new key with same scopes and settings
    const { key: newKey, keyId: newKeyId } = await this.apiKeyService.generateKey(
      oldKey.userId,
      {
        scopes: oldKey.scopes,
        rateLimit: oldKey.rateLimit,
        environment: oldKey.environment,
      }
    );

    // Grace period: keep old key active for overlap
    await db.apiKey.update({
      where: { id: oldKeyId },
      data: {
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24h grace
        rotatedToKeyId: newKeyId,
      },
    });

    return { newKey };
  }
}
```

---

## 5. Zero-Trust Architecture in Node.js

Zero trust means: never trust, always verify. Every request is authenticated and authorized regardless of network location.

### Principles Applied to Node.js

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

// 3. Encrypt everything (even internal traffic)
// Use mTLS or service mesh for inter-service communication

// 4. Log everything
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

## 6. Secret Management

### HashiCorp Vault Integration

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

### AWS Secrets Manager

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

## 7. Audit Logging

### Structured Audit Logging

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

// Middleware for automatic audit logging
function auditMiddleware(resourceType: string, action: string) {
  return (req: Request, res: Response, next: NextFunction) => {
    const startTime = Date.now();

    res.on('finish', () => {
      auditLogger.log({
        timestamp: new Date().toISOString(),
        eventType: 'access',
        action,
        actor: {
          type: req.user ? 'user' : 'service',
          id: req.user?.id || req.serviceIdentity?.id || 'anonymous',
          ip: req.ip,
          userAgent: req.headers['user-agent'],
        },
        resource: {
          type: resourceType,
          id: req.params.id || 'collection',
        },
        outcome: res.statusCode < 400 ? 'success' : 'failure',
        metadata: {
          method: req.method,
          path: req.path,
          statusCode: res.statusCode,
          duration: Date.now() - startTime,
        },
        requestId: req.id,
      });
    });

    next();
  };
}
```

### Tamper-Proof Audit Trails

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

## 8. Penetration Testing Node.js Applications

### Common Attack Vectors

```typescript
// 1. Prototype pollution
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

// 2. ReDoS (Regular Expression Denial of Service)
// Vulnerable regex: /^(a+)+$/
// Input: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!'
// This causes catastrophic backtracking

// Defense: use re2 (Google's regex engine, no backtracking)
import RE2 from 're2';
const safeRegex = new RE2('^(a+)+$'); // Linear time guaranteed

// 3. SSRF (Server-Side Request Forgery)
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

### Security Testing Checklist

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
