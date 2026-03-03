# Module 09: Compliance and Advanced Security

## Supply Chain Security

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

## Compliance Basics

### Compliance Requirements Comparison

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

### SOC 2

SOC 2 evaluates controls based on five Trust Service Criteria:

1. **Security:** Protection against unauthorized access (firewalls, MFA, encryption).
2. **Availability:** System uptime and disaster recovery (SLAs, failover, backups).
3. **Processing Integrity:** Data processing is complete, accurate, and authorized.
4. **Confidentiality:** Protection of confidential information (encryption, access controls).
5. **Privacy:** Collection, use, and disposal of personal information.

**Type I:** Point-in-time assessment (do controls exist?). **Type II:** Period assessment (did controls operate effectively over 6-12 months?).

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
- Track data lineage -- know where PII flows through your system.
- Data Protection Impact Assessments (DPIAs) for high-risk processing.
- Orchestrate deletion across all services (user service, orders, analytics, search index, backups) with an event-driven approach (`UserDeletionRequested` event).

### HIPAA

For healthcare data (Protected Health Information -- PHI):
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

## Threat Modeling

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

### Threat Modeling Template (STRIDE)

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
│ Info Disclsre│          │ H/M/L  │ H/M/L      │          │
│ Denial of Svc│          │ H/M/L  │ H/M/L      │          │
│ Elev. of Priv│          │ H/M/L  │ H/M/L      │          │
└──────────────┴──────────┴────────┴────────────┴──────────┘

Trust Boundaries Identified:
1. ___________________________
2. ___________________________

High-Priority Findings:
1. ___________________________  Owner: ____  Deadline: ____
2. ___________________________  Owner: ____  Deadline: ____
```

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

### Security Design Review Checklist

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

## Identity Federation and Certificate Management

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

**Certificate rotation strategy:** Short-lived certificates (hours to days) eliminate the need for revocation. Overlap period: issue new certificate before old one expires. Applications should reload certificates without restart (Envoy, Nginx support this).

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

## Network Security

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

## Interview Questions

**Q: How do you ensure GDPR compliance in a microservices architecture where user data is spread across multiple services?**

A: Build a data catalog that maps PII fields to services and storage locations. Implement a central "data subject request" service that orchestrates deletion/export across all services. Use event-driven architecture -- publish a `UserDeletionRequested` event and have each service handle its own cleanup. Track data lineage through the pipeline. For backups, maintain a deletion log and apply it during restores.

**Q: Design the encryption strategy for a healthcare application handling patient records.**

A: At rest: AES-256 with envelope encryption via KMS, plus field-level encryption for PHI fields. In transit: TLS 1.3 externally, mTLS between services. Key management: separate KMS keys per data classification; only the patient-records service can decrypt PHI. Audit every decryption. Ensure BAAs with cloud providers, conduct annual HIPAA risk assessments.

### Related Reading

- [Module 09: Authentication and Authorization](01-authentication-and-authorization.md) -- zero trust architecture, OAuth2/OIDC, and encryption foundations that compliance frameworks require
- [Module 09: API and Application Security](02-api-and-application-security.md) -- the API security controls, container hardening, and CI/CD scanning that implement compliance requirements
- [Module 02: Database Platforms and Scaling](../02-databases-at-scale/03-database-platforms-and-scaling.md) -- GDPR and HIPAA have specific requirements for data encryption at rest, audit logging, and data retention policies that affect database choices
- [Module 05: Advanced Load Balancing Patterns](../05-load-balancing/03-advanced-load-balancing-patterns.md) -- VPC design, network security groups vs NACLs, and TLS termination architecture connect to the network security topics covered here
- [Module 06: Kubernetes Advanced Patterns](../06-containers-orchestration/03-kubernetes-advanced-patterns.md) -- RBAC, Pod Security Standards, OPA/Gatekeeper, and network policies enforce compliance controls at the cluster level
- [Module 07: Infrastructure and GitOps](../07-cicd/03-infrastructure-and-gitops.md) -- CI/CD supply chain security (SLSA, Sigstore, SBOM) and GitOps audit trails support SOC 2 and other compliance frameworks
- [Module 08: SLOs, Alerting, and Incident Response](../08-observability/02-slos-alerting-and-incident-response.md) -- incident response processes and blameless postmortems are requirements for SOC 2 and many compliance frameworks

### Key Takeaways

1. **Compliance is a constraint, not a goal.** Understand the technical implications of SOC 2, GDPR, HIPAA, and PCI DSS.
2. **Threat modeling belongs in the design phase.** STRIDE and attack trees surface risks before code is written.
3. **Supply chain security is the new frontier.** SBOMs, signed artifacts, and SLSA are rapidly becoming table stakes.
4. **Automate everything.** Manual security processes do not scale and create gaps. Every security control should be codified, tested, and continuously verified.
5. **The perimeter is gone.** Every component must defend itself. Every identity must be verified. Every secret must be managed. Every dependency must be audited.
