# Module 09: Security at Scale — Cheat Sheet

## Zero Trust Principles Checklist

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

---

## OAuth2 Flow Quick Reference

### Authorization Code Flow (User-Facing Apps)

```
User -> App: clicks "Login"
App -> AuthZ Server: /authorize?response_type=code&client_id=X&redirect_uri=Y&scope=Z
AuthZ Server -> User: login page
User -> AuthZ Server: credentials
AuthZ Server -> App: redirect to Y with ?code=ABC
App -> AuthZ Server: POST /token (code=ABC, client_id, client_secret)
AuthZ Server -> App: { access_token, refresh_token, id_token }
```

### Client Credentials Flow (Machine-to-Machine)

```
Service -> AuthZ Server: POST /token (grant_type=client_credentials, client_id, client_secret)
AuthZ Server -> Service: { access_token, expires_in }
Service -> Target API: Authorization: Bearer <access_token>
```

### Token Exchange (Service-to-Service on Behalf of User)

```
Service A -> AuthZ Server: POST /token (grant_type=token-exchange,
                           subject_token=user_jwt, audience=service-b)
AuthZ Server -> Service A: { access_token (narrowed scope, audience=service-b) }
Service A -> Service B: uses narrowed token
```

---

## OWASP API Security Top 10 (2023)

| # | Vulnerability | One-Liner | Key Prevention |
|---|--------------|-----------|----------------|
| 1 | Broken Object-Level AuthZ | Change ID, access other user's data | Check ownership on every request |
| 2 | Broken Authentication | Weak auth, no rate limit on login | Proven auth libraries, rate limit auth endpoints |
| 3 | Broken Object Property AuthZ | API returns/accepts too many fields | Explicit response schemas, writable field allowlists |
| 4 | Unrestricted Resource Consumption | No rate/size/pagination limits | Rate limit, max page size, request body limits |
| 5 | Broken Function-Level AuthZ | Regular user hits admin endpoints | RBAC, deny-by-default, test all roles |
| 6 | SSRF | API fetches attacker-controlled URL | URL allowlists, block internal IPs, sandboxed network |
| 7 | Security Misconfiguration | Default creds, verbose errors, open CORS | Hardened configs, generic errors, strict CORS |
| 8 | Lack of Automated Threat Protection | Credential stuffing, scraping | Bot detection, CAPTCHA, behavioral analysis |
| 9 | Improper Inventory Management | Shadow/deprecated APIs still live | API catalog, decommission old versions |
| 10 | Unsafe API Consumption | Trusting third-party API data | Validate external data same as user input |

---

## Encryption Comparison

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

## Security Headers Checklist

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0                          # Disabled; CSP is the modern replacement
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Cache-Control: no-store                       # For sensitive responses
```

---

## Compliance Requirements Comparison

| Requirement | SOC 2 | GDPR | HIPAA | PCI DSS |
|------------|-------|------|-------|---------|
| **Applies to** | SaaS companies (US-centric) | Any org processing EU resident data | Healthcare data (US) | Credit card data |
| **Encryption at rest** | Required | Required for sensitive data | Required for PHI | Required for cardholder data |
| **Encryption in transit** | Required | Required | Required | Required |
| **Access controls** | Role-based, MFA | Least privilege | Role-based, unique IDs | Role-based, unique IDs |
| **Audit logging** | Required | Required | Required (6 years) | Required (1 year) |
| **Data retention** | Defined by policy | Minimization principle | 6 years | Minimize storage |
| **Breach notification** | Report to auditor | 72 hours to authority | 60 days | Immediate to card brands |
| **Right to deletion** | Not required | Required ("right to be forgotten") | Not required | Delete when no longer needed |
| **Regular assessments** | Annual audit (Type II) | DPIAs for high-risk processing | Annual risk assessment | Quarterly vuln scans, annual audit |
| **Certification** | SOC 2 Type I/II report | No certification (self-assessed) | No certification (self-assessed) | PCI QSA audit or SAQ |

---

## Threat Modeling Template (STRIDE)

```
System: ___________________________
Date:   ___________________________
Team:   ___________________________

For each component/data flow:

┌──────────────┬──────────┬────────┬────────────┬──────────┐
│ Threat Type  │ Scenario │ Impact │ Likelihood │ Mitigation│
├──────────────┼──────────┼────────┼────────────┼──────────┤
│ Spoofing     │          │ H/M/L  │ H/M/L      │          │
│ Tampering    │          │ H/M/L  │ H/M/L      │          │
│ Repudiation  │          │ H/M/L  │ H/M/L      │          │
│ Info Disclosure│        │ H/M/L  │ H/M/L      │          │
│ Denial of Svc│          │ H/M/L  │ H/M/L      │          │
│ Elev. of Priv│          │ H/M/L  │ H/M/L      │          │
└──────────────┴──────────┴────────┴────────────┴──────────┘

Trust Boundaries Identified:
1. ___________________________
2. ___________________________
3. ___________________________

High-Priority Findings:
1. ___________________________  Owner: ____  Deadline: ____
2. ___________________________  Owner: ____  Deadline: ____
3. ___________________________  Owner: ____  Deadline: ____
```

---

## Quick Reference: Security Tool Categories

| Category | Tools | When to Use |
|----------|-------|-------------|
| SAST | Semgrep, SonarQube, CodeQL | Every PR — static code analysis |
| DAST | OWASP ZAP, Burp Suite, Nuclei | Against staging — runtime vuln scanning |
| SCA | Snyk, Dependabot, Trivy (fs mode) | Every PR — dependency vulnerabilities |
| Container Scanning | Trivy, Grype, Snyk Container | Every image build — OS + app vulns |
| Secret Scanning | truffleHog, git-secrets, Gitleaks | Pre-commit + CI — detect leaked secrets |
| Runtime Security | Falco, Sysdig, Aqua | Production — detect anomalous behavior |
| WAF | AWS WAF, Cloudflare WAF, ModSecurity | Edge — block malicious HTTP traffic |
| Secrets Management | Vault, AWS Secrets Manager, GCP SM | Always — centralized secret storage + rotation |
| Certificate Mgmt | cert-manager, Let's Encrypt, ACM | Always — automated TLS cert lifecycle |
| Identity | Okta, Auth0, Keycloak, AWS IAM | Always — centralized identity + federation |
