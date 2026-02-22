# Module 09: Security at Scale

## Overview

Security at scale is not a feature you bolt on — it is a property of the system's design. When you operate hundreds of services across multiple regions, traditional perimeter-based security collapses. This module covers the patterns, protocols, and practices that keep large distributed systems secure without strangling developer velocity.

---

## 1. Zero Trust Architecture

### The Core Principle: Never Trust, Always Verify

Traditional security draws a perimeter — everything inside the firewall is trusted. Zero trust assumes the network is already compromised. Every request, every connection, every user must prove its identity and authorization on every interaction.

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

### Interview Angle

When asked about zero trust, do not just recite principles. Describe how you would implement it incrementally: start with identity-aware proxy for internal tools, add mTLS between services, layer in network policies, then mature into continuous posture assessment.

---

## 2. OAuth2 and OIDC in Distributed Systems

### The Protocol Stack

- **OAuth 2.0** handles authorization — "what can this client do?"
- **OpenID Connect (OIDC)** is an identity layer on top of OAuth2 — "who is this user?"

In a microservices architecture, the challenge is not understanding the protocol — it is deciding where and how tokens are validated across dozens of services.

### Token Validation: Gateway vs. Service

**Option A: Validate at the API Gateway Only**

The gateway verifies the JWT (signature, expiration, audience, issuer). Backend services receive a trusted header (e.g., `X-User-Id`, `X-User-Roles`) and trust it implicitly.

```
Client -> API Gateway (validates JWT) -> Service A (trusts X-User-Id header)
                                      -> Service B (trusts X-User-Id header)
```

Pros: Simple, fast, no crypto libraries in every service.
Cons: If an attacker bypasses the gateway, services are defenseless. Internal headers can be spoofed in misconfigured environments.

**Option B: Validate in Every Service**

Each service independently validates the JWT. The gateway may do an initial check, but services do not rely on it.

```
Client -> API Gateway (validates JWT, forwards token)
       -> Service A (re-validates JWT, extracts claims)
       -> Service B (re-validates JWT, extracts claims)
```

Pros: Defense in depth. Services are secure even if the gateway is compromised.
Cons: Every service needs the signing key (or JWKS endpoint access). Slightly higher latency.

**Recommendation:** Validate at the gateway AND forward the token. Services perform lightweight validation (signature + expiry) and extract claims directly. This is the zero trust approach.

### Token Exchange

When Service A needs to call Service B on behalf of a user, it should not just forward the user's token — that token may have broader scopes than Service B needs. OAuth2 Token Exchange (RFC 8693) lets Service A exchange the user's token for a narrower one scoped to Service B.

```
Service A -> Authorization Server: "Exchange user token for service-b-scoped token"
AuthZ Server -> Service A: new token with audience=service-b, scopes=[read:orders]
Service A -> Service B: uses narrowed token
```

### Machine-to-Machine Auth (Client Credentials)

For service-to-service calls that are not on behalf of a user (e.g., a cron job calling an internal API), use the OAuth2 Client Credentials grant:

```
Service -> AuthZ Server: client_id + client_secret (or mTLS certificate)
AuthZ Server -> Service: access token with machine identity + scopes
Service -> Target API: uses access token
```

Best practices:
- Rotate client secrets regularly (or use certificate-based client auth).
- Scope tokens narrowly to specific APIs and actions.
- Use short-lived tokens (5-15 minutes) to limit blast radius.

### Service Accounts

In cloud-native environments, service accounts bind workload identity to cloud IAM:

- **AWS:** IAM Roles for Service Accounts (IRSA) in EKS — pods assume IAM roles via OIDC federation.
- **GCP:** Workload Identity — Kubernetes service accounts map to GCP service accounts.
- **Azure:** Workload Identity Federation — AAD tokens issued to pods.

This eliminates long-lived credentials entirely. The workload proves its identity through the platform's own attestation mechanism.

---

## 3. API Gateway Security

The API gateway is the front door to your system. It is the natural enforcement point for multiple security controls.

### Rate Limiting

Protect backends from abuse and ensure fair usage.

```
# Example: Kong rate limiting plugin
plugins:
  - name: rate-limiting
    config:
      minute: 100
      hour: 5000
      policy: redis          # Distributed counter
      redis_host: redis.internal
      fault_tolerant: true   # Allow traffic if Redis is down
      hide_client_headers: false
```

Strategies:
- **Per-user:** Based on authenticated identity. Fair but requires auth.
- **Per-IP:** Catches unauthenticated abuse. Can be circumvented with IP rotation.
- **Per-API-key:** Common for public APIs. Tied to billing tiers.
- **Tiered limits:** Free tier gets 100 req/min, paid tier gets 10,000 req/min.

### Authentication Offloading

The gateway handles JWT validation, API key verification, or session cookie checks so that backend services do not need to implement auth logic.

### Request Validation

Validate request structure before forwarding. Reject malformed requests early.

```yaml
# OpenAPI schema validation at the gateway
paths:
  /orders:
    post:
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [product_id, quantity]
              properties:
                product_id:
                  type: string
                  pattern: "^[a-zA-Z0-9]{8,32}$"
                quantity:
                  type: integer
                  minimum: 1
                  maximum: 100
```

### IP Allowlisting and Geo-Blocking

For internal APIs or partner integrations, restrict access to known IP ranges. Geographic blocking can eliminate traffic from regions where you have no users.

### WAF Integration

Most gateways integrate with a Web Application Firewall (AWS WAF, Cloudflare WAF) that inspects request payloads for malicious patterns.

---

## 4. WAF and DDoS Mitigation

### Web Application Firewall (WAF)

A WAF inspects HTTP traffic at Layer 7. It applies rules to detect and block:

- SQL injection patterns
- Cross-site scripting (XSS) payloads
- Path traversal attempts
- Known vulnerability exploits (Log4Shell, etc.)

**AWS WAF** uses managed and custom rule groups to match patterns (SQLi, XSS) and block or count matching requests. **Cloudflare WAF** provides managed rulesets (OWASP Core, Cloudflare Specials) plus custom rules.

### DDoS Mitigation

**Layer 3/4 (Volumetric) Attacks:** Mitigated by cloud providers at the network edge. AWS Shield Standard is automatic. Cloudflare absorbs volumetric attacks across its global network.

**Layer 7 (Application) Attacks:** More sophisticated — valid-looking HTTP requests at high volume. Defenses include:

- **Rate limiting rules:** Block IPs exceeding thresholds.
- **Bot detection:** Challenge suspicious clients with CAPTCHAs or JavaScript challenges.
- **Challenge pages:** Interstitial pages that require browser JavaScript execution (blocks simple bots).
- **Geographic blocking:** If an attack originates from a specific region, temporarily block it.
- **Behavioral analysis:** Identify anomalous patterns (e.g., 1000 requests to /login in 10 seconds from distributed IPs).

### Defense in Depth

```
Internet -> CDN/Edge (Cloudflare/CloudFront)
         -> WAF (Layer 7 inspection)
         -> DDoS Protection (AWS Shield / Cloudflare)
         -> API Gateway (rate limiting, auth)
         -> Load Balancer (health checks)
         -> Application (input validation)
```

---

## 5. Data Encryption

### Encryption at Rest

Data stored on disk, in databases, or in object storage must be encrypted.

**AES-256** is the standard symmetric cipher. In practice, you use envelope encryption:

```
1. Generate a Data Encryption Key (DEK) — a random AES-256 key
2. Encrypt your data with the DEK
3. Encrypt the DEK with a Key Encryption Key (KEK) managed by KMS
4. Store the encrypted DEK alongside the encrypted data
5. Discard the plaintext DEK from memory
```

Why envelope encryption? Because you do not send bulk data to KMS (which has API rate limits and latency). You only send the small DEK for encryption/decryption.

**AWS KMS** manages the KEK. You never see the KEK in plaintext. KMS operations are logged in CloudTrail for audit.

Use `kms.generate_data_key()` to get both a plaintext DEK (for encrypting data) and an encrypted DEK (for storage). Later, call `kms.decrypt()` on the encrypted DEK to recover the plaintext DEK for decryption.

### Encryption in Transit

**TLS 1.3** is the current standard. Improvements over TLS 1.2:
- 1-RTT handshake (vs. 2-RTT in TLS 1.2)
- 0-RTT resumption for repeat connections (with replay protection caveats)
- Removed insecure cipher suites (RC4, 3DES, static RSA key exchange)
- Forward secrecy is mandatory (ephemeral Diffie-Hellman only)

**Certificate Management:**
- Use automated certificate issuance (Let's Encrypt, AWS Certificate Manager).
- Automate rotation — certificates should rotate well before expiry.
- Monitor certificate expiry with alerting.

**mTLS Between Services:**

In a zero trust mesh, both client and server present certificates. The server verifies the client's identity, and the client verifies the server's.

```
Service A (client cert) <-> Service B (server cert)
Both sides verify each other's certificate against a trusted CA.
```

Service meshes (Istio, Linkerd) automate mTLS between all pods:

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

**Searchable Encryption:** Techniques like blind indexing allow equality searches on encrypted fields. You compute a deterministic HMAC of the plaintext and store it as a search index. You can check "does this SSN exist?" without decrypting all records.

```python
# Blind index for searchable encryption
blind_index = hmac_sha256(secret_key, plaintext_ssn)
# Store blind_index alongside the encrypted SSN
# Query: WHERE ssn_blind_index = hmac_sha256(secret_key, search_value)
```

---

## 6. Secrets Management

### The Problem

Secrets (API keys, database passwords, encryption keys, certificates) are the keys to the kingdom. Mismanaging them is one of the most common causes of breaches.

### Anti-Patterns

- **Hardcoded in source code.** Secrets in git history are effectively public.
- **Environment variables without protection.** Env vars are visible in process listings, crash dumps, and container inspection.
- **Shared secrets.** One password used by multiple services. If compromised, blast radius is everything.
- **Never rotated.** A secret that has not changed in two years has had two years of exposure window.

### HashiCorp Vault

Vault is the industry standard for secrets management.

**Static Secrets:** Store and retrieve via API (`vault kv put/get`).

**Dynamic Secrets:** Vault generates short-lived credentials on demand. When a service needs a database connection, Vault creates a temporary user with a TTL (e.g., 1 hour). After expiry, Vault automatically revokes the credential. Benefits: no long-lived passwords, no shared credentials, automatic revocation, full audit trail.

**Transit Engine:** Vault performs encryption as a service — your application never handles keys directly.

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

## 7. OWASP Top 10 for APIs

The OWASP API Security Top 10 (2023) targets API-specific vulnerabilities. Here are the critical ones with prevention patterns.

### API1: Broken Object-Level Authorization (BOLA)

An attacker changes an object ID in a request to access another user's data.

```
GET /api/users/123/orders  ->  attacker changes to /api/users/456/orders
```

**Prevention:**
- Always verify that the authenticated user owns or has access to the requested resource.
- Use authorization middleware that checks ownership, not just authentication.

```python
@app.route('/api/users/<user_id>/orders')
@require_auth
def get_orders(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        return 403
    return fetch_orders(user_id)
```

### API2: Broken Authentication

Weak authentication mechanisms — missing rate limiting on login, weak token validation, credentials in URLs.

**Prevention:** Use proven auth libraries. Implement rate limiting on auth endpoints. Use short-lived tokens. Never send credentials in query strings.

### API3: Broken Object Property Level Authorization

The API returns more data than the client needs, or allows modification of fields that should be read-only.

**Prevention:**
- Explicitly define response schemas — never return raw database objects.
- Use allowlists for writable fields (not blocklists).

```python
# BAD: returns everything from the database
return jsonify(user.__dict__)

# GOOD: explicit field selection
return jsonify({
    "id": user.id,
    "name": user.name,
    "email": user.email
    # role, password_hash, internal_flags are excluded
})
```

### API4: Unrestricted Resource Consumption

No rate limiting, no pagination limits, no request size limits. An attacker can exhaust resources.

**Prevention:**
- Rate limit all endpoints.
- Enforce maximum page sizes.
- Limit request body sizes.
- Set query complexity limits for GraphQL.

### API5: Broken Function-Level Authorization

Regular users can access admin endpoints because authorization is not checked at the function level.

**Prevention:** Implement role-based access control. Deny by default. Test authorization for every endpoint with different roles.

### API6: Server-Side Request Forgery (SSRF)

The API accepts a URL from the user and fetches it server-side, allowing access to internal resources.

```
POST /api/webhooks { "url": "http://169.254.169.254/latest/meta-data/" }
```

**Prevention:**
- Validate and sanitize URLs. Block internal IP ranges.
- Use allowlists for permitted domains.
- Run URL-fetching in a sandboxed network with no access to internal services.

### API7: Security Misconfiguration

Default credentials, unnecessary HTTP methods enabled, verbose error messages exposing stack traces, CORS misconfiguration.

**Prevention:** Harden configurations. Disable debug mode in production. Use restrictive CORS policies. Return generic error messages.

### API8: Lack of Protection from Automated Threats

Credential stuffing, scraping, inventory hoarding. **Prevention:** Bot detection, CAPTCHAs on sensitive flows, behavioral analysis.

### API9: Improper Inventory Management

Undocumented or deprecated API versions still running in production. **Prevention:** Maintain an API catalog. Decommission old versions.

### API10: Unsafe Consumption of APIs

Your API trusts data from third-party APIs without validation. **Prevention:** Validate and sanitize all data from external APIs the same way you validate user input.

### Mass Assignment (Bonus — Previously Top 10)

The API blindly binds request body fields to model attributes. A user sends `{"name": "Alice", "role": "admin"}` and the API maps all fields, granting admin access. **Prevention:** Explicitly define which fields are bindable (allowlists, not blocklists).

---

## 8. Supply Chain Security

### The Risk

Your application depends on hundreds of open-source packages. If any one of them is compromised, so is your application. Notable incidents: event-stream (2018), ua-parser-js (2021), colors.js (2022), xz-utils (2024).

### Dependency Scanning

- **SCA (Software Composition Analysis):** Tools like Snyk, Dependabot, or Trivy scan dependencies for known CVEs.
- **Run in CI:** Every pull request should be scanned. Block merges if critical/high vulnerabilities are found.

```yaml
# GitHub Actions: Dependency scanning
- name: Run Snyk
  uses: snyk/actions/node@master
  with:
    args: --severity-threshold=high
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
```

### Lockfile Integrity

Lockfiles (`package-lock.json`, `poetry.lock`, `go.sum`) pin exact versions and include integrity hashes. Always commit lockfiles. In CI, use `npm ci` (not `npm install`) to ensure reproducible builds from the lockfile.

### Software Bill of Materials (SBOM)

An SBOM is a machine-readable inventory of all components in your software. Required by executive orders and regulations for government software. Standards: SPDX, CycloneDX.

```bash
# Generate SBOM with Syft
syft packages dir:./my-app -o spdx-json > sbom.json
```

### Signed Artifacts

Sign your container images and build artifacts to prove provenance. If an image is not signed by your CI pipeline, it should not run in production.

```bash
# Sign container image with Cosign
cosign sign --key cosign.key ghcr.io/myorg/my-app:v1.2.3

# Verify signature before deploying
cosign verify --key cosign.pub ghcr.io/myorg/my-app:v1.2.3
```

### SLSA Framework

Supply-chain Levels for Software Artifacts (SLSA, pronounced "salsa") defines maturity levels:

| Level | Requirements |
|-------|-------------|
| SLSA 1 | Build process is documented |
| SLSA 2 | Build service is used (not developer laptop), signed provenance |
| SLSA 3 | Hardened build platform, non-falsifiable provenance |
| SLSA 4 | Two-person review, hermetic builds, reproducible |

---

## 9. Compliance Basics

### SOC 2

SOC 2 evaluates controls based on five Trust Service Criteria:

1. **Security:** Protection against unauthorized access (firewalls, MFA, encryption).
2. **Availability:** System uptime and disaster recovery (SLAs, failover, backups).
3. **Processing Integrity:** Data processing is complete, accurate, and authorized.
4. **Confidentiality:** Protection of confidential information (encryption, access controls).
5. **Privacy:** Collection, use, and disposal of personal information.

**Type I:** Point-in-time assessment (do controls exist?).
**Type II:** Period assessment (did controls operate effectively over 6-12 months?).

For engineers, SOC 2 means: audit logging, access reviews, change management, incident response procedures, encryption everywhere.

### GDPR

The General Data Protection Regulation applies to any system processing data of EU residents.

**Key Principles:**
- **Data minimization:** Collect only what you need. Delete what you no longer need.
- **Purpose limitation:** Data collected for one purpose cannot be used for another without consent.
- **Data subject rights:**
  - Right to access (export my data)
  - Right to rectification (fix my data)
  - Right to erasure ("right to be forgotten")
  - Right to portability (give me my data in a machine-readable format)

**Technical Implications:**
- Build data export and deletion APIs.
- Implement soft deletes with hard delete after retention period.
- Track data lineage — know where PII flows through your system.
- Data Protection Impact Assessments (DPIAs) for high-risk processing.
- Orchestrate deletion across all services (user service, orders, analytics, search index, backups) with an event-driven approach (`UserDeletionRequested` event).

### HIPAA

For healthcare data (Protected Health Information — PHI):
- Encryption required for data at rest and in transit.
- Access controls and audit logging for all PHI access.
- Business Associate Agreements (BAAs) with all vendors handling PHI.
- Breach notification requirements (within 60 days).

### PCI DSS

For systems handling credit card data:
- **Minimize cardholder data exposure.** Tokenize card numbers immediately. Use a payment processor (Stripe, Braintree) to avoid handling raw card data.
- **Network segmentation.** The cardholder data environment (CDE) must be isolated.
- **Encryption.** Card data encrypted at rest and in transit.
- **Logging and monitoring.** All access to cardholder data must be logged and monitored.
- **Quarterly vulnerability scans.**

**The best PCI strategy is to avoid storing card data entirely.** Use tokenization through your payment processor.

---

## 10. Interview Questions

### Conceptual Questions

1. **"How would you implement zero trust in an existing microservices architecture?"**

   Walk through an incremental approach: (a) Deploy an identity-aware proxy for external access, removing VPN dependency. (b) Implement mTLS between services using a service mesh. (c) Add network policies for microsegmentation. (d) Move to short-lived, scoped tokens for service-to-service auth. (e) Implement device posture checks for human access. Emphasize that zero trust is a journey, not a switch you flip.

2. **"Where should JWT validation happen — at the gateway or in each service?"**

   Both. The gateway performs full validation (signature, expiry, audience, issuer) and rejects invalid tokens. It forwards valid tokens to services. Services perform lightweight re-validation and extract claims for authorization decisions. This provides defense in depth. Discuss the trade-off: gateway-only is simpler but violates zero trust; per-service-only adds latency and complexity. The hybrid approach balances security and performance.

3. **"How would you handle secrets rotation without downtime?"**

   Describe dual-credential rotation: generate the new secret, configure the consumer to accept both old and new, verify the new credential works, then revoke the old one. For database passwords: create a new user, update the app config, drain connections using the old user, drop the old user. Vault's dynamic secrets solve this elegantly — every credential is short-lived, so "rotation" is just getting a new lease.

4. **"A penetration test found an SSRF vulnerability in your webhook system. How do you fix it?"**

   (a) Validate webhook URLs against an allowlist of permitted domains or IP ranges. (b) Block requests to private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254). (c) Resolve DNS and re-check the IP (prevent DNS rebinding). (d) Run webhook fetching in an isolated network segment with no access to internal services. (e) Set timeouts and response size limits to prevent resource exhaustion.

5. **"How do you ensure GDPR compliance in a microservices architecture where user data is spread across multiple services?"**

   Build a data catalog that maps PII fields to services and storage locations. Implement a central "data subject request" service that orchestrates deletion/export across all services. Use event-driven architecture — publish a `UserDeletionRequested` event and have each service handle its own cleanup. Track data lineage through the pipeline. For backups, maintain a deletion log and apply it during restores.

### Scenario-Based Questions

6. **"You discover that an API key with broad permissions has been committed to a public GitHub repository. Walk me through your incident response."**

   Immediate: revoke the key, check audit logs for unauthorized usage, generate a new key with narrower permissions, scan for other secrets with truffleHog/git-secrets, communicate to affected teams. Post-incident: implement pre-commit hooks for secret scanning, add scanning in CI, conduct access review.

7. **"Design the encryption strategy for a healthcare application handling patient records."**

   At rest: AES-256 with envelope encryption via KMS, plus field-level encryption for PHI fields. In transit: TLS 1.3 externally, mTLS between services. Key management: separate KMS keys per data classification; only the patient-records service can decrypt PHI. Audit every decryption. Ensure BAAs with cloud providers, conduct annual HIPAA risk assessments.

8. **"Your application receives 10x normal traffic during a flash sale. How do you distinguish legitimate traffic from a DDoS attack?"**

   Legitimate traffic: diverse geographic origins matching your user base, targets product/checkout pages, valid session cookies, normal browsing patterns. Attack traffic: concentrated IP ranges, targets resource-intensive endpoints, lacks valid sessions, uniform patterns. Mitigate with auto-scaling, per-IP/per-user rate limiting, WAF rules, challenge pages, and a runbook for escalation.

---

## Summary

Security at scale requires a shift in mindset. The perimeter is gone. Every component must defend itself. Every identity must be verified. Every secret must be managed. Every dependency must be audited.

Key takeaways for interviews:

- **Zero trust is architectural.** It is not a product you buy. It is identity-based access, microsegmentation, least privilege, and continuous verification.
- **OAuth2/OIDC complexity is in the distribution.** Token validation location, token exchange, and machine identity are the real challenges.
- **Encryption has three dimensions.** At rest (AES-256, KMS), in transit (TLS 1.3, mTLS), and at the field level (PII protection).
- **Secrets management is about automation.** Dynamic secrets, automated rotation, and never storing secrets in code.
- **Supply chain security is the new frontier.** SBOMs, signed artifacts, and SLSA are rapidly becoming table stakes.
- **Compliance is a constraint, not a goal.** Understand the technical implications of SOC 2, GDPR, HIPAA, and PCI DSS.
