# Module 09: Authentication and Authorization

## Zero Trust Architecture

### The Core Principle: Never Trust, Always Verify

Traditional security draws a perimeter -- everything inside the firewall is trusted. Zero trust assumes the network is already compromised. Every request, every connection, every user must prove its identity and authorization on every interaction.

### The Four Pillars

**1. Identity-Based Access**

Every actor (human or machine) has a cryptographically verifiable identity. Access decisions are based on identity, not network location.

```
Traditional:  "You're on the VPN, so you can access the database."
Zero Trust:   "You are engineer alice@corp, your device is compliant,
               you have the db-reader role, and your session is less
               than 8 hours old — you may read from the orders table."
```

**2. Microsegmentation**

Instead of flat networks where any host can reach any other host, microsegmentation enforces fine-grained network policies. Each service can only communicate with explicitly allowed peers.

```yaml
# Kubernetes NetworkPolicy example
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payment-service-policy
spec:
  podSelector:
    matchLabels:
      app: payment-service
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: order-service
      ports:
        - port: 8443
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: payment-db
      ports:
        - port: 5432
```

**3. Least Privilege**

Every identity gets the minimum permissions needed to perform its function. Permissions are scoped narrowly (specific resources, specific actions, time-bounded).

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject"],
  "Resource": "arn:aws:s3:::order-receipts/2024/*",
  "Condition": {
    "IpAddress": {"aws:SourceIp": "10.0.0.0/8"},
    "DateLessThan": {"aws:CurrentTime": "2024-12-31T23:59:59Z"}
  }
}
```

**4. Continuous Verification**

Trust is not a one-time gate. Sessions are re-evaluated continuously based on context: device posture, location anomalies, time-of-day, behavioral signals.

### Zero Trust Principles Checklist

```
[ ] Every request is authenticated — no implicit trust from network location
[ ] Every request is authorized — identity + context checked against policy
[ ] Least privilege — minimum permissions, scoped narrowly, time-bounded
[ ] Microsegmentation — services can only reach explicitly allowed peers
[ ] Encrypt everything — TLS in transit, AES-256 at rest, mTLS between services
[ ] Continuous verification — sessions re-evaluated, device posture checked
[ ] Assume breach — design for containment, not just prevention
[ ] Log everything — security events, access, auth decisions (immutable audit trail)
```

### The BeyondCorp Model

Google's BeyondCorp is the canonical zero trust implementation. Key ideas:

- **No VPN required.** Internal applications are accessed over the internet through an identity-aware proxy.
- **Device inventory.** Every device is registered, tracked, and assessed for compliance (OS patches, disk encryption, endpoint protection).
- **Access tiers.** Resources are classified by sensitivity. Higher tiers require stronger device posture and authentication factors.
- **Access proxy.** A central proxy (comparable to Google's Identity-Aware Proxy, or Cloudflare Access / Tailscale) authenticates and authorizes every request before forwarding to the backend.

```
User -> Identity-Aware Proxy -> AuthN (who are you?)
                              -> AuthZ (policy check: role + device + context)
                              -> Backend Service
```

When asked about zero trust, do not just recite principles. Describe how you would implement it incrementally: start with identity-aware proxy for internal tools, add mTLS between services, layer in network policies, then mature into continuous posture assessment.

---

## OAuth2 and OIDC in Distributed Systems

### The Protocol Stack

- **OAuth 2.0** handles authorization -- "what can this client do?"
- **OpenID Connect (OIDC)** is an identity layer on top of OAuth2 -- "who is this user?"

In a microservices architecture, the challenge is not understanding the protocol -- it is deciding where and how tokens are validated across dozens of services.

### OAuth2 Flow Quick Reference

**Authorization Code Flow (User-Facing Apps):**

```
User -> App: clicks "Login"
App -> AuthZ Server: /authorize?response_type=code&client_id=X&redirect_uri=Y&scope=Z
AuthZ Server -> User: login page
User -> AuthZ Server: credentials
AuthZ Server -> App: redirect to Y with ?code=ABC
App -> AuthZ Server: POST /token (code=ABC, client_id, client_secret)
AuthZ Server -> App: { access_token, refresh_token, id_token }
```

**Client Credentials Flow (Machine-to-Machine):**

```
Service -> AuthZ Server: POST /token (grant_type=client_credentials, client_id, client_secret)
AuthZ Server -> Service: { access_token, expires_in }
Service -> Target API: Authorization: Bearer <access_token>
```

**Token Exchange (Service-to-Service on Behalf of User):**

```
Service A -> AuthZ Server: POST /token (grant_type=token-exchange,
                           subject_token=user_jwt, audience=service-b)
AuthZ Server -> Service A: { access_token (narrowed scope, audience=service-b) }
Service A -> Service B: uses narrowed token
```

### Token Validation: Gateway vs. Service

**Option A: Validate at the API Gateway Only**

The gateway verifies the JWT (signature, expiration, audience, issuer). Backend services receive a trusted header (e.g., `X-User-Id`, `X-User-Roles`) and trust it implicitly.

```
Client -> API Gateway (validates JWT) -> Service A (trusts X-User-Id header)
                                      -> Service B (trusts X-User-Id header)
```

Pros: Simple, fast, no crypto libraries in every service. Cons: If an attacker bypasses the gateway, services are defenseless. Internal headers can be spoofed in misconfigured environments.

**Option B: Validate in Every Service**

Each service independently validates the JWT. The gateway may do an initial check, but services do not rely on it.

```
Client -> API Gateway (validates JWT, forwards token)
       -> Service A (re-validates JWT, extracts claims)
       -> Service B (re-validates JWT, extracts claims)
```

Pros: Defense in depth. Services are secure even if the gateway is compromised. Cons: Every service needs the signing key (or JWKS endpoint access). Slightly higher latency.

**Recommendation:** Validate at the gateway AND forward the token. Services perform lightweight validation (signature + expiry) and extract claims directly. This is the zero trust approach.

### Token Exchange

When Service A needs to call Service B on behalf of a user, it should not just forward the user's token -- that token may have broader scopes than Service B needs. OAuth2 Token Exchange (RFC 8693) lets Service A exchange the user's token for a narrower one scoped to Service B.

```
Service A -> Authorization Server: "Exchange user token for service-b-scoped token"
AuthZ Server -> Service A: new token with audience=service-b, scopes=[read:orders]
Service A -> Service B: uses narrowed token
```

### Machine-to-Machine Auth (Client Credentials)

For service-to-service calls that are not on behalf of a user (e.g., a cron job calling an internal API), use the OAuth2 Client Credentials grant. Best practices:
- Rotate client secrets regularly (or use certificate-based client auth).
- Scope tokens narrowly to specific APIs and actions.
- Use short-lived tokens (5-15 minutes) to limit blast radius.

### Service Accounts

In cloud-native environments, service accounts bind workload identity to cloud IAM:

- **AWS:** IAM Roles for Service Accounts (IRSA) in EKS -- pods assume IAM roles via OIDC federation.
- **GCP:** Workload Identity -- Kubernetes service accounts map to GCP service accounts.
- **Azure:** Workload Identity Federation -- AAD tokens issued to pods.

This eliminates long-lived credentials entirely. The workload proves its identity through the platform's own attestation mechanism.

---

## Data Encryption

### Encryption at Rest

Data stored on disk, in databases, or in object storage must be encrypted. **AES-256** is the standard symmetric cipher. In practice, you use envelope encryption:

```
1. Generate a Data Encryption Key (DEK) — a random AES-256 key
2. Encrypt your data with the DEK
3. Encrypt the DEK with a Key Encryption Key (KEK) managed by KMS
4. Store the encrypted DEK alongside the encrypted data
5. Discard the plaintext DEK from memory
```

Why envelope encryption? Because you do not send bulk data to KMS (which has API rate limits and latency). You only send the small DEK for encryption/decryption.

**AWS KMS** manages the KEK. You never see the KEK in plaintext. KMS operations are logged in CloudTrail for audit. Use `kms.generate_data_key()` to get both a plaintext DEK (for encrypting data) and an encrypted DEK (for storage).

### Encryption in Transit

**TLS 1.3** improvements over TLS 1.2:
- 1-RTT handshake (vs. 2-RTT in TLS 1.2)
- 0-RTT resumption for repeat connections (with replay protection caveats)
- Removed insecure cipher suites (RC4, 3DES, static RSA key exchange)
- Forward secrecy is mandatory (ephemeral Diffie-Hellman only)

**Certificate Management:**
- Use automated certificate issuance (Let's Encrypt, AWS Certificate Manager).
- Automate rotation -- certificates should rotate well before expiry.
- Monitor certificate expiry with alerting.

**mTLS Between Services:**

In a zero trust mesh, both client and server present certificates. Service meshes (Istio, Linkerd) automate mTLS between all pods:

```yaml
# Istio PeerAuthentication
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT  # All traffic must be mTLS
```

### Field-Level Encryption

Sometimes you need to encrypt specific fields within a record while leaving others queryable.

**Use Case:** Encrypting PII (Social Security numbers, credit card numbers) so that even database administrators cannot read them.

```python
# Pseudocode: field-level encryption
record = {
    "user_id": "usr_123",              # Plaintext — used for lookups
    "email": encrypt(kms, "alice@example.com"),  # Encrypted
    "ssn": encrypt(kms, "123-45-6789"),          # Encrypted
    "created_at": "2024-01-15"         # Plaintext — used for queries
}
```

**Searchable Encryption (Blind Indexing):** Allows equality searches on encrypted fields by storing a deterministic HMAC alongside the encrypted value.

```python
# Blind index for searchable encryption
blind_index = hmac_sha256(secret_key, plaintext_ssn)
# Store blind_index alongside the encrypted SSN
# Query: WHERE ssn_blind_index = hmac_sha256(secret_key, search_value)
```

### Encryption Comparison

| Dimension | At Rest | In Transit | Field-Level |
|-----------|---------|-----------|-------------|
| **What** | Data on disk/storage | Data moving between systems | Specific fields within records |
| **Algorithm** | AES-256 (symmetric) | TLS 1.3 (asymmetric + symmetric) | AES-256 per field |
| **Key Management** | KMS + envelope encryption | Certificate authorities, cert-manager | KMS, per-field or per-tenant keys |
| **Scope** | Entire volume/database | Network connection | Individual PII/PHI fields |
| **Example** | RDS encryption, S3 SSE | HTTPS, mTLS between services | Encrypted SSN column |
| **Searchability** | Full (decrypted at query time) | N/A | Blind indexing (HMAC) for equality |
| **Performance** | Transparent (hardware-accelerated) | ~1-2ms handshake overhead | Per-field encrypt/decrypt cost |

---

## Secrets Management

### Anti-Patterns

- **Hardcoded in source code.** Secrets in git history are effectively public.
- **Environment variables without protection.** Env vars are visible in process listings, crash dumps, and container inspection.
- **Shared secrets.** One password used by multiple services. If compromised, blast radius is everything.
- **Never rotated.** A secret that has not changed in two years has had two years of exposure window.

### HashiCorp Vault

Vault is the industry standard for secrets management.

**Static Secrets:** Store and retrieve via API (`vault kv put/get`).

**Dynamic Secrets:** Vault generates short-lived credentials on demand. When a service needs a database connection, Vault creates a temporary user with a TTL (e.g., 1 hour). After expiry, Vault automatically revokes the credential. Benefits: no long-lived passwords, no shared credentials, automatic revocation, full audit trail.

**Transit Engine:** Vault performs encryption as a service -- your application never handles keys directly.

### Secrets in Kubernetes

**Kubernetes Secrets** are base64-encoded (not encrypted) by default, stored in etcd (enable encryption at rest). Better approaches:
- **External Secrets Operator:** Syncs secrets from Vault/AWS Secrets Manager/GCP Secret Manager into K8s Secrets.
- **CSI Secrets Store Driver:** Mounts secrets as files in pods, fetched from external stores at runtime.
- **Sealed Secrets:** Encrypt client-side so secrets can be safely committed to git; only the cluster can decrypt.

### Rotation Strategies

- **Automated rotation:** Secrets Manager (AWS) or Vault can rotate secrets on a schedule without application changes.
- **Dual-credential rotation:** Generate new credentials, update consumers, verify, revoke old credentials.
- **Grace periods:** Keep old credentials valid for a window after rotation to handle in-flight requests.

---

## Interview Questions

**Q: How would you implement zero trust in an existing microservices architecture?**

A: Walk through an incremental approach: (a) Deploy an identity-aware proxy for external access, removing VPN dependency. (b) Implement mTLS between services using a service mesh. (c) Add network policies for microsegmentation. (d) Move to short-lived, scoped tokens for service-to-service auth. (e) Implement device posture checks for human access. Emphasize that zero trust is a journey, not a switch you flip.

**Q: Where should JWT validation happen -- at the gateway or in each service?**

A: Both. The gateway performs full validation (signature, expiry, audience, issuer) and rejects invalid tokens. It forwards valid tokens to services. Services perform lightweight re-validation and extract claims for authorization decisions. This provides defense in depth. The hybrid approach balances security and performance.

**Q: How would you handle secrets rotation without downtime?**

A: Describe dual-credential rotation: generate the new secret, configure the consumer to accept both old and new, verify the new credential works, then revoke the old one. For database passwords: create a new user, update the app config, drain connections using the old user, drop the old user. Vault's dynamic secrets solve this elegantly -- every credential is short-lived, so "rotation" is just getting a new lease.

### Related Reading

- [Module 09: API and Application Security](02-api-and-application-security.md) -- API gateway security (rate limiting, WAF), DDoS mitigation, and the OWASP API Security Top 10 build on the authentication and authorization foundations covered here
- [Module 09: Compliance and Advanced Security](03-compliance-and-advanced-security.md) -- compliance frameworks (SOC 2, GDPR, HIPAA, PCI DSS) impose requirements on the authentication, encryption, and secrets management practices described here
- [Module 02: SQL, NoSQL, and Decision Framework](../02-databases-at-scale/01-sql-nosql-and-decision-framework.md) -- data encryption at rest applies to all database choices; understanding data classification helps you decide which databases need field-level encryption
- [Module 05: Advanced Load Balancing Patterns](../05-load-balancing/03-advanced-load-balancing-patterns.md) -- TLS 1.3 termination at the load balancer, mTLS between services, and HTTP security headers
- [Module 06: Kubernetes Advanced Patterns](../06-containers-orchestration/03-kubernetes-advanced-patterns.md) -- Kubernetes RBAC, service mesh mTLS (Istio, Linkerd), and workload identity for pod-level authentication
- [Module 07: Feature Flags and Migrations](../07-cicd/02-feature-flags-and-migrations.md) -- secrets management with Vault and External Secrets Operator, and rotation strategies for database credentials

### Key Takeaways

1. **Zero trust is architectural.** It is not a product you buy. It is identity-based access, microsegmentation, least privilege, and continuous verification.
2. **OAuth2/OIDC complexity is in the distribution.** Token validation location, token exchange, and machine identity are the real challenges.
3. **Encryption has three dimensions.** At rest (AES-256, KMS), in transit (TLS 1.3, mTLS), and at the field level (PII protection).
4. **Secrets management is about automation.** Dynamic secrets, automated rotation, and never storing secrets in code.
