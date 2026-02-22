# Module 09: Security at Scale — Deep Dive

## Overview

This deep dive covers advanced operational security topics: threat modeling, security in CI/CD, container and network hardening, identity federation, and certificate management automation.

---

## 1. Threat Modeling

Threat modeling is the practice of systematically identifying what can go wrong before it does. It belongs in the design phase, not after the breach.

### The STRIDE Framework

STRIDE is Microsoft's threat classification model. For every component in your system, ask whether it is vulnerable to each category:

| Threat | Definition | Example | Mitigation |
|--------|-----------|---------|------------|
| **S**poofing | Pretending to be someone/something else | Forged JWT, stolen API key | Strong authentication, mTLS |
| **T**ampering | Modifying data or code | Man-in-the-middle, SQL injection | Integrity checks, input validation, TLS |
| **R**epudiation | Denying an action occurred | User denies placing an order | Audit logging, non-repudiation signatures |
| **I**nformation Disclosure | Exposing data to unauthorized parties | Verbose error messages, data leaks | Encryption, access controls, minimal error detail |
| **D**enial of Service | Making a system unavailable | Volumetric DDoS, resource exhaustion | Rate limiting, auto-scaling, circuit breakers |
| **E**levation of Privilege | Gaining unauthorized access | BOLA, role escalation, container escape | Least privilege, RBAC, sandboxing |

### Running a Threat Model Session

1. **Scope the system.** Draw a data flow diagram (DFD) showing components, trust boundaries, and data flows.
2. **Identify threats.** Walk through each data flow and apply STRIDE. Use structured questions: "Can an attacker spoof the identity of Service A when calling Service B?"
3. **Assess risk.** Rate each threat by likelihood and impact. Use a simple matrix (High/Medium/Low).
4. **Define mitigations.** For each high-risk threat, define a concrete mitigation and assign an owner.
5. **Track and revisit.** Threat models are living documents. Revisit when the architecture changes.

### Attack Trees

Attack trees decompose a security goal (from the attacker's perspective) into a hierarchy of sub-goals.

```
Goal: Steal customer payment data
├── Compromise the payment service
│   ├── Exploit unpatched vulnerability (CVE)
│   ├── Steal service credentials from environment
│   └── SQL injection via unvalidated input
├── Intercept data in transit
│   ├── Man-in-the-middle (if TLS misconfigured)
│   └── Compromise a proxy/load balancer
├── Access the database directly
│   ├── Brute-force database credentials
│   ├── Exploit misconfigured security group
│   └── Insider threat (DBA access)
└── Exfiltrate from backups
    ├── Access unencrypted backup bucket
    └── Steal backup encryption keys
```

Each leaf node can be annotated with difficulty, cost, and detectability. This helps prioritize defenses.

### Security Design Reviews

Before any significant feature launches, conduct a security design review:

- **Who participates?** The feature team, a security engineer, and an infrastructure engineer.
- **What is reviewed?** Architecture diagrams, data flow, authentication/authorization model, data storage, third-party integrations.
- **Output:** A list of findings categorized by severity, with mitigations and deadlines.

Template for a design review checklist:

```
[ ] Authentication: How are users/services authenticated?
[ ] Authorization: How are permissions checked? Is it deny-by-default?
[ ] Data classification: What data is handled? Is any of it PII/PHI/PCI?
[ ] Encryption: Is data encrypted at rest and in transit?
[ ] Input validation: Are all inputs validated and sanitized?
[ ] Secrets: How are secrets stored and rotated?
[ ] Logging: Are security-relevant events logged?
[ ] Rate limiting: Are endpoints protected against abuse?
[ ] Dependencies: Are third-party dependencies scanned?
[ ] Failure modes: What happens when auth/encryption/validation fails?
```

---

## 2. Penetration Testing Methodology

### Types of Penetration Tests

- **Black box:** No knowledge of the system. Simulates an external attacker.
- **Gray box:** Partial knowledge (API docs, a regular user account).
- **White box:** Full access to source code and architecture. Most efficient for internal teams.

### Phases

1. **Reconnaissance:** Map the attack surface — endpoints, technologies, subdomains.
2. **Vulnerability scanning:** Automated tools (Burp Suite, OWASP ZAP, Nuclei) find known vulnerabilities.
3. **Exploitation:** Attempt to exploit vulnerabilities. Demonstrate impact.
4. **Post-exploitation:** Lateral movement, persistence, data exfiltration assessment.
5. **Reporting:** Findings with severity, reproduction steps, and remediation guidance.

### Continuous Penetration Testing

Annual pen tests are insufficient. Modern approaches: bug bounty programs (HackerOne, Bugcrowd), automated pen testing tools (Nuclei) running against staging, and red team exercises simulating advanced persistent threats.

---

## 3. Security in CI/CD

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

Define policies that block deployments: block on critical SAST findings, block on critical SCA CVEs (allow up to N high-severity with exceptions), block on high DAST findings, zero tolerance for committed secrets. Balance is critical — too strict and developers circumvent them; too loose and they are meaningless.

---

## 4. Container Security

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

Scan images for OS and application vulnerabilities in CI and in the registry.

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

Kubernetes Pod Security Standards define three profiles:

- **Privileged:** Unrestricted. Only for system-level workloads.
- **Baseline:** Prevents known privilege escalations. Blocks hostNetwork, hostPID, privileged containers.
- **Restricted:** Heavily restricted. Non-root, read-only root filesystem, no privilege escalation.

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

### Container Security Checklist

Use minimal base images (distroless/Alpine), pin image digests, scan in CI, run as non-root, set `readOnlyRootFilesystem: true`, drop all capabilities, use seccomp profiles, set resource limits, monitor with Falco, and enforce image signature verification on admission.

---

## 5. Network Security

### VPC Design

A well-designed VPC segments workloads by trust level.

```
VPC (10.0.0.0/16)
├── Public Subnets (10.0.1.0/24, 10.0.2.0/24)
│   └── ALB, NAT Gateway, Bastion (if needed)
├── Private App Subnets (10.0.10.0/24, 10.0.11.0/24)
│   └── Application servers, EKS worker nodes
├── Private Data Subnets (10.0.20.0/24, 10.0.21.0/24)
│   └── RDS, ElastiCache, Elasticsearch
└── Isolated Subnets (10.0.30.0/24)
    └── Highly sensitive workloads (no internet access)
```

### Security Groups vs. NACLs

| Feature | Security Groups | NACLs |
|---------|----------------|-------|
| Level | Instance/ENI | Subnet |
| State | Stateful (return traffic auto-allowed) | Stateless (must explicitly allow return traffic) |
| Rules | Allow only (implicit deny) | Allow and deny |
| Evaluation | All rules evaluated together | Rules evaluated in order (first match wins) |
| Use case | Fine-grained per-service rules | Broad subnet-level guardrails |

**Best practice:** Use security groups as the primary control (per-service rules). Use NACLs as a secondary defense layer for subnet-level blocking (e.g., block known malicious IP ranges).

```
# Security group for the order service
Inbound:
  - Port 8443 from sg-api-gateway    (HTTPS from gateway)
  - Port 8443 from sg-order-worker   (internal service calls)
Outbound:
  - Port 5432 to sg-order-db         (PostgreSQL)
  - Port 6379 to sg-redis            (Redis)
  - Port 443 to 0.0.0.0/0           (HTTPS to external APIs)
```

### Private Endpoints (AWS PrivateLink)

Instead of routing traffic to AWS services over the internet, use VPC endpoints. Traffic stays on the AWS backbone.

```
# VPC Endpoint for S3
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-abc123 \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-abc123

# Interface Endpoint for Secrets Manager
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-abc123 \
  --vpc-endpoint-type Interface \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --subnet-ids subnet-abc123 \
  --security-group-ids sg-abc123
```

Benefits: no NAT gateway costs, reduced attack surface, lower latency.

---

## 6. Identity Federation

Identity federation allows users to authenticate through external identity providers (IdPs) rather than maintaining separate credentials per system.

### SAML 2.0 vs. OIDC

| Feature | SAML 2.0 | OIDC |
|---------|----------|------|
| Protocol | XML-based | JSON/REST-based |
| Token format | XML assertions | JWTs |
| Primary use | Enterprise SSO, legacy | Modern apps, APIs, mobile |
| Complexity | High | Moderate |

Most new systems use OIDC. SAML is encountered when integrating with enterprise IdPs (Okta, Azure AD) that may require it.

### Workload Identity Federation

For cloud workloads, eliminate long-lived credentials entirely by federating workload identity.

**AWS Example: GitHub Actions OIDC Federation**

```yaml
# GitHub Actions workflow that authenticates to AWS without secrets
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/github-deploy
          aws-region: us-east-1
          # No AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY needed
```

How it works: GitHub's OIDC provider issues a JWT to the workflow. AWS STS validates the JWT against GitHub's OIDC issuer. If the claims match the IAM role's trust policy, AWS issues temporary credentials. No long-lived secrets are stored in GitHub.

### Cross-Account and Cross-Cloud Federation

For multi-account AWS, use IAM roles with cross-account trust policies. For multi-cloud, federate identities between providers using OIDC (e.g., GCP service account assumes an AWS IAM role via `sts:AssumeRoleWithWebIdentity` with the GCP OIDC issuer as the federated principal).

---

## 7. Certificate Management Automation

### The Problem

Manual certificate management does not scale. Expired certificates cause outages. Manual renewal is error-prone and creates toil.

### cert-manager in Kubernetes

cert-manager automates certificate issuance and renewal in Kubernetes.

```yaml
# ClusterIssuer for Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: platform@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
      - dns01:
          route53:
            region: us-east-1

---
# Certificate resource
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: api-tls
  namespace: production
spec:
  secretName: api-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - api.example.com
    - "*.api.example.com"
  renewBefore: 720h  # Renew 30 days before expiry
```

cert-manager handles the entire lifecycle: request, challenge (HTTP-01 or DNS-01), issuance, storage as Kubernetes Secret, and automatic renewal.

### Internal PKI for mTLS

For service-to-service mTLS, you need an internal Certificate Authority. Options:

- **cert-manager with a self-signed CA or Vault CA:** Issue short-lived certificates to workloads.
- **SPIFFE/SPIRE:** An open standard for workload identity. Issues SVID (SPIFFE Verifiable Identity Document) certificates automatically.
- **Service mesh (Istio/Linkerd):** Built-in certificate issuance and rotation for mTLS.

```yaml
# cert-manager with Vault as CA
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: vault-issuer
spec:
  vault:
    server: https://vault.internal:8200
    path: pki/sign/service-cert
    auth:
      kubernetes:
        role: cert-manager
        mountPath: /v1/auth/kubernetes
```

### Certificate Rotation Strategy

- **Short-lived certificates (hours to days)** eliminate the need for revocation. If a certificate is compromised, it expires quickly.
- **Overlap period:** Issue new certificate before the old one expires. Both are valid during the overlap window.
- **Graceful reload:** Applications should reload certificates without restart. Most modern proxies (Envoy, Nginx) support this.

### Monitoring

- Alert when certificates are within 14 days of expiry.
- Track certificate issuance failures.
- Monitor certificate chain validity.

```yaml
# Prometheus alert for expiring certificates
- alert: CertificateExpiringSoon
  expr: certmanager_certificate_expiration_timestamp_seconds - time() < 1209600
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Certificate {{ $labels.name }} expires in less than 14 days"
```

---

## Summary

Operationalizing security requires embedding it into every phase of the software lifecycle:

- **Design phase:** Threat modeling with STRIDE and attack trees surfaces risks before code is written.
- **Development phase:** SAST catches vulnerabilities in code; SCA catches them in dependencies.
- **Build phase:** Container image scanning and signed artifacts ensure supply chain integrity.
- **Deployment phase:** Pod security standards and network policies enforce runtime constraints.
- **Runtime phase:** DAST, Falco, and continuous monitoring detect active threats.
- **Infrastructure phase:** VPC design, security groups, private endpoints, and identity federation form the foundation.
- **Certificate lifecycle:** Automation through cert-manager and internal PKI eliminates manual toil and prevents outages from expired certificates.

The common thread: automate everything. Manual security processes do not scale and create gaps. Every security control should be codified, tested, and continuously verified.
