# Module 09: API and Application Security

## API Gateway Security

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

### IP Allowlisting, Geo-Blocking, and WAF Integration

For internal APIs or partner integrations, restrict access to known IP ranges. Geographic blocking can eliminate traffic from regions where you have no users. Most gateways integrate with a Web Application Firewall (AWS WAF, Cloudflare WAF) that inspects request payloads for malicious patterns.

---

## WAF and DDoS Mitigation

### Web Application Firewall (WAF)

A WAF inspects HTTP traffic at Layer 7. It applies rules to detect and block SQL injection patterns, cross-site scripting (XSS) payloads, path traversal attempts, and known vulnerability exploits (Log4Shell, etc.).

**AWS WAF** uses managed and custom rule groups to match patterns and block or count matching requests. **Cloudflare WAF** provides managed rulesets (OWASP Core, Cloudflare Specials) plus custom rules.

### DDoS Mitigation

**Layer 3/4 (Volumetric) Attacks:** Mitigated by cloud providers at the network edge. AWS Shield Standard is automatic.

**Layer 7 (Application) Attacks:** More sophisticated -- valid-looking HTTP requests at high volume. Defenses include:

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

## OWASP API Security Top 10

The OWASP API Security Top 10 (2023) targets API-specific vulnerabilities.

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

### API1: Broken Object-Level Authorization (BOLA)

An attacker changes an object ID in a request to access another user's data.

```
GET /api/users/123/orders  ->  attacker changes to /api/users/456/orders
```

**Prevention:**
```python
@app.route('/api/users/<user_id>/orders')
@require_auth
def get_orders(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        return 403
    return fetch_orders(user_id)
```

### API3: Broken Object Property Level Authorization

The API returns more data than the client needs, or allows modification of fields that should be read-only.

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

### API6: Server-Side Request Forgery (SSRF)

The API accepts a URL from the user and fetches it server-side, allowing access to internal resources.

```
POST /api/webhooks { "url": "http://169.254.169.254/latest/meta-data/" }
```

**Prevention:**
- Validate and sanitize URLs. Block internal IP ranges.
- Use allowlists for permitted domains.
- Run URL-fetching in a sandboxed network with no access to internal services.

### Mass Assignment

The API blindly binds request body fields to model attributes. A user sends `{"name": "Alice", "role": "admin"}` and the API maps all fields, granting admin access. **Prevention:** Explicitly define which fields are bindable (allowlists, not blocklists).

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

## Security in CI/CD

### Shift Left

Integrating security into the development pipeline catches vulnerabilities before they reach production.

```
Code Commit -> SAST -> Unit Tests -> Build -> SCA -> DAST -> Deploy -> Runtime Security
              (static)                       (deps)  (dynamic)        (monitoring)
```

### Static Application Security Testing (SAST)

SAST analyzes source code for vulnerabilities without executing it.

```yaml
# GitHub Actions: SAST with Semgrep
- name: Semgrep SAST
  uses: returntocorp/semgrep-action@v1
  with:
    config: >-
      p/owasp-top-ten
      p/javascript
      p/typescript
```

Common tools: Semgrep (open source, fast), SonarQube (broad language support), CodeQL (GitHub). Catches injection, hardcoded secrets, insecure crypto. Weakness: high false positive rate, cannot detect runtime issues.

### Dynamic Application Security Testing (DAST)

DAST tests running applications by sending malicious requests.

```yaml
# Run OWASP ZAP against staging
- name: DAST Scan
  uses: zaproxy/action-full-scan@v0.9.0
  with:
    target: 'https://staging.example.com'
    rules_file_name: '.zap/rules.tsv'
    fail_action: 'warn'  # or 'fail' for strict
```

Finds runtime vulnerabilities and tests actual deployed configuration. Weakness: slow, limited coverage, cannot pinpoint the vulnerable line.

### Software Composition Analysis (SCA)

SCA scans dependencies for known vulnerabilities (CVEs).

```yaml
# Trivy dependency scanning
- name: SCA Scan
  run: trivy fs --scanners vuln --severity HIGH,CRITICAL .
```

### Security Gates

Define policies that block deployments: block on critical SAST findings, block on critical SCA CVEs (allow up to N high-severity with exceptions), block on high DAST findings, zero tolerance for committed secrets. Balance is critical -- too strict and developers circumvent them; too loose and they are meaningless.

### Quick Reference: Security Tool Categories

| Category | Tools | When to Use |
|----------|-------|-------------|
| SAST | Semgrep, SonarQube, CodeQL | Every PR -- static code analysis |
| DAST | OWASP ZAP, Burp Suite, Nuclei | Against staging -- runtime vuln scanning |
| SCA | Snyk, Dependabot, Trivy (fs mode) | Every PR -- dependency vulnerabilities |
| Container Scanning | Trivy, Grype, Snyk Container | Every image build -- OS + app vulns |
| Secret Scanning | truffleHog, git-secrets, Gitleaks | Pre-commit + CI -- detect leaked secrets |
| Runtime Security | Falco, Sysdig, Aqua | Production -- detect anomalous behavior |
| WAF | AWS WAF, Cloudflare WAF, ModSecurity | Edge -- block malicious HTTP traffic |
| Secrets Management | Vault, AWS Secrets Manager, GCP SM | Always -- centralized secret storage + rotation |
| Certificate Mgmt | cert-manager, Let's Encrypt, ACM | Always -- automated TLS cert lifecycle |
| Identity | Okta, Auth0, Keycloak, AWS IAM | Always -- centralized identity + federation |

---

## Container Security

### Image Security

**Base Image Selection:**
- Use minimal base images (distroless, Alpine, scratch for Go binaries).
- Fewer packages means fewer vulnerabilities and smaller attack surface.
- Pin base image digests, not tags (tags are mutable).

```dockerfile
# BAD: mutable tag
FROM node:18

# BETTER: pinned digest
FROM node:18@sha256:abc123def456...

# BEST: multi-stage with minimal runtime
FROM node:18 AS builder
WORKDIR /app
COPY . .
RUN npm ci && npm run build

FROM gcr.io/distroless/nodejs18-debian12
COPY --from=builder /app/dist /app
CMD ["/app/server.js"]
```

**Image Scanning:**
```bash
# Scan with Trivy
trivy image --severity HIGH,CRITICAL myapp:latest

# Scan with Grype
grype myapp:latest --fail-on high
```

### Runtime Security with Falco

Falco detects anomalous behavior at runtime by monitoring system calls.

```yaml
# Falco rule: detect shell spawned in container
- rule: Terminal shell in container
  desc: A shell was spawned in a container
  condition: >
    spawned_process and container and
    proc.name in (bash, sh, zsh, dash)
  output: >
    Shell spawned in container
    (user=%user.name container=%container.name
     shell=%proc.name parent=%proc.pname)
  priority: WARNING
  tags: [container, shell]

# Falco rule: detect sensitive file read
- rule: Read sensitive file in container
  desc: Attempt to read sensitive files
  condition: >
    open_read and container and
    fd.name in (/etc/shadow, /etc/passwd, /run/secrets/*)
  output: >
    Sensitive file read (file=%fd.name container=%container.name)
  priority: CRITICAL
```

### Pod Security

```yaml
# Pod security context for a production workload
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 3000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: myapp:latest
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir: {}
```

**Container Security Checklist:** Use minimal base images (distroless/Alpine), pin image digests, scan in CI, run as non-root, set `readOnlyRootFilesystem: true`, drop all capabilities, use seccomp profiles, set resource limits, monitor with Falco, and enforce image signature verification on admission.

---

## Interview Questions

**Q: A penetration test found an SSRF vulnerability in your webhook system. How do you fix it?**

A: (a) Validate webhook URLs against an allowlist of permitted domains or IP ranges. (b) Block requests to private IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254). (c) Resolve DNS and re-check the IP (prevent DNS rebinding). (d) Run webhook fetching in an isolated network segment with no access to internal services. (e) Set timeouts and response size limits to prevent resource exhaustion.

**Q: You discover that an API key with broad permissions has been committed to a public GitHub repository. Walk me through your incident response.**

A: Immediate: revoke the key, check audit logs for unauthorized usage, generate a new key with narrower permissions, scan for other secrets with truffleHog/git-secrets, communicate to affected teams. Post-incident: implement pre-commit hooks for secret scanning, add scanning in CI, conduct access review.

**Q: Your application receives 10x normal traffic during a flash sale. How do you distinguish legitimate traffic from a DDoS attack?**

A: Legitimate traffic: diverse geographic origins matching your user base, targets product/checkout pages, valid session cookies, normal browsing patterns. Attack traffic: concentrated IP ranges, targets resource-intensive endpoints, lacks valid sessions, uniform patterns. Mitigate with auto-scaling, per-IP/per-user rate limiting, WAF rules, challenge pages, and a runbook for escalation.

### Key Takeaways

1. **Supply chain security is the new frontier.** SBOMs, signed artifacts, and SLSA are rapidly becoming table stakes.
2. **Defense in depth for APIs.** WAF at the edge, rate limiting at the gateway, RBAC in the application.
3. **Container security is layered.** Minimal images, scanning in CI, hardened pod security contexts, and runtime monitoring each catch different threats.
4. **Shift security left.** SAST, SCA, and secret scanning in CI is far cheaper than fixing vulnerabilities in production.
