# Module 07: CI/CD & DevOps

## Overview

Continuous Integration and Continuous Delivery form the backbone of modern software delivery. For senior engineers, mastery of CI/CD goes far beyond "set up a pipeline" -- it means designing deployment strategies that minimize risk, managing infrastructure declaratively, handling database migrations without downtime, and building developer workflows that scale across large teams. This module covers pipeline design, deployment strategies, Infrastructure as Code, secrets management, and the operational practices that separate reliable systems from fragile ones.

---

## Table of Contents

1. [Pipeline Design](#pipeline-design)
2. [Blue-Green Deployments](#blue-green-deployments)
3. [Canary Deployments](#canary-deployments)
4. [Rolling Deployments](#rolling-deployments)
5. [Feature Flags](#feature-flags)
6. [Infrastructure as Code](#infrastructure-as-code)
7. [Secrets Management](#secrets-management)
8. [GitHub Actions](#github-actions)
9. [Branching Strategies](#branching-strategies)
10. [Database Migrations in CI/CD](#database-migrations-in-cicd)
11. [Interview Questions](#interview-questions)

---

## Pipeline Design

### Build, Test, Deploy Stages

A well-designed CI/CD pipeline is a series of gates that progressively increase confidence in a change.

```
Source -> Build -> Unit Tests -> Integration Tests -> Security Scan -> Staging Deploy -> E2E Tests -> Production Deploy
```

**Build Stage:**
- Compile code, resolve dependencies, produce artifacts
- Should be deterministic -- same commit always produces the same artifact
- Use content-addressable storage for build cache (layer caching in Docker, incremental compilation)
- Tag artifacts with commit SHA, not "latest"

**Test Stage:**
- Unit tests: fast, isolated, run on every commit
- Integration tests: verify component interactions, may require service dependencies
- Contract tests: verify API compatibility between services
- Security scans: SAST (static analysis), dependency vulnerability scanning (Snyk, Trivy, Grype)

**Deploy Stage:**
- Deploy the exact artifact that passed all previous stages
- Never rebuild for production -- promote the tested artifact
- Environment-specific configuration injected at deploy time, not build time

### Parallel vs Sequential Execution

**When to parallelize:** Independent test suites (unit, integration, linting), multi-platform builds (linux/amd64, linux/arm64), multi-service monorepo builds, matrix builds across language/runtime versions.

**When to keep sequential:** Deploy stages that depend on test results, database migrations before application deployment, smoke tests after deployment before traffic shifting.

### Fail-Fast Strategies

- **Lint and type-check first** -- fastest checks run before compilation
- **Run unit tests before integration tests** -- cheaper tests gate expensive ones
- **Cancel redundant runs** -- if a new commit is pushed, cancel the in-progress run for the previous commit
- **Required checks vs optional checks** -- clearly separate blocking from informational
- **Test splitting and ordering** -- run previously-failed tests first (pytest `--last-failed`, Jest `--changedSince`)

### Artifact Management

Artifacts are immutable -- once built, never modified. Store in a dedicated registry (Docker Hub, ECR, Artifactory, GitHub Packages). Tag with commit SHA for traceability: `myapp:a1b2c3d`. Implement retention policies to manage storage costs. Sign artifacts for supply chain security (cosign, Notary).

**Anti-patterns:** Rebuilding for each environment (staging artifact != production artifact), using mutable tags like `latest` in production, storing artifacts in git (large binary files), no cleanup policy.

---

## Blue-Green Deployments

### Concept

Maintain two identical production environments. One ("blue") serves live traffic while the other ("green") receives the new version. Switch traffic atomically once the green environment is validated.

```
              Load Balancer
              /           \
         [Blue v1.0]   [Green v1.1]
         (ACTIVE)      (IDLE/STAGING)

After validation, switch:

              Load Balancer
              /           \
         [Blue v1.0]   [Green v1.1]
         (IDLE)        (ACTIVE)
```

### Zero-Downtime Switching

- **Load balancer switch** (preferred): Update target group to point to the green environment. Instantaneous, no DNS propagation delay.
- **DNS switch**: Update DNS record to point to green. Subject to TTL propagation -- clients may still hit blue for minutes.
- **Service mesh switch**: Route 100% traffic to the new version via Istio VirtualService or similar.

### Database Migrations with Blue-Green

Both blue and green must talk to the same database during the transition. Use the **Expand/Contract pattern**:
1. **Expand**: Add new columns/tables without removing old ones. Both v1.0 and v1.1 can operate.
2. **Deploy green (v1.1)**: It uses the new schema while blue (v1.0) ignores the new fields.
3. **Switch traffic**: Green is now live.
4. **Contract**: Remove deprecated columns/tables in a subsequent release once blue is decommissioned.

**Critical rule**: Never make a breaking schema change in a single deployment. Always use at least two releases.

### Rollback Strategy

- **Instant rollback**: Switch load balancer back to blue. This is the primary advantage of blue-green.
- **Database rollback concern**: If green wrote data using new schema features, switching back to blue may cause issues. Design migrations to be backward-compatible.
- **Keep blue alive**: Do not decommission blue until the green deployment is confirmed stable (hours or days, not minutes).

**Tradeoffs:** Instant rollback and full validation before switch, but requires double the infrastructure and careful expand/contract discipline for database changes.

---

## Canary Deployments

### Traffic Splitting

Deploy the new version to a small subset of infrastructure and route a fraction of traffic to it. Gradually increase the percentage as confidence grows.

```
t=0:   [v1.0: 100%] [v1.1:   0%]
t=5m:  [v1.0:  95%] [v1.1:   5%]
t=15m: [v1.0:  80%] [v1.1:  20%]
t=30m: [v1.0:  50%] [v1.1:  50%]
t=60m: [v1.0:   0%] [v1.1: 100%]
```

**Implementation:** Istio VirtualService with weight-based routing, ALB weighted target groups, CDN-level (Cloudflare Workers), or feature flags.

```yaml
# Istio VirtualService for canary routing
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-service
spec:
  http:
  - route:
    - destination:
        host: my-service
        subset: stable
      weight: 95
    - destination:
        host: my-service
        subset: canary
      weight: 5
```

### Metric-Based Promotion

Automated canary analysis compares the canary's metrics against the baseline: error rate, latency (p50/p95/p99), saturation (CPU, memory), business metrics.

**Tools:** Flagger (Kubernetes-native, integrates with Istio/Linkerd), Argo Rollouts (supports multiple traffic managers), Spinnaker (multi-cloud, Netflix-origin), AWS CodeDeploy.

### Automated Rollback

```yaml
# Flagger canary analysis
spec:
  analysis:
    interval: 1m
    threshold: 5          # max failed checks before rollback
    maxWeight: 50         # max canary traffic percentage
    stepWeight: 10        # increment per interval
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
    - name: request-duration
      thresholdRange:
        max: 500
```

### Progressive Delivery

Extends canary with: header-based routing (internal/beta users to canary), geographic routing (one region first), cohort-based (user ID hash for consistent experience), manual gates (human approval before advancing).

---

## Rolling Deployments

### maxUnavailable and maxSurge

```yaml
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 2    # At most 2 pods down simultaneously
      maxSurge: 3           # At most 3 extra pods during update
```

| Setting | Speed | Resource Usage | Risk |
|---------|-------|---------------|------|
| maxUnavailable=0, maxSurge=1 | Slow | Low extra capacity | Safest |
| maxUnavailable=25%, maxSurge=25% | Moderate (default) | Moderate | Balanced |
| maxUnavailable=50%, maxSurge=50% | Fast | High extra capacity | Higher risk |

### Health Check Gates

- **startupProbe**: Protects slow-starting containers. Liveness/readiness paused until startup succeeds.
- **readinessProbe**: Pod receives traffic only when ready. Failed readiness removes it from service endpoints.
- **livenessProbe**: Pod is restarted if liveness fails. Use cautiously -- cascading restarts can cause outages.

### Connection Draining

When terminating a pod: (1) SIGTERM received, (2) removed from service endpoints, (3) `terminationGracePeriodSeconds` to finish in-flight requests, (4) SIGKILL after grace period. Use a `preStop` sleep hook to allow endpoint removal to propagate before the application starts shutting down.

---

## Feature Flags

### Platforms

| Platform | Type | Strengths |
|----------|------|-----------|
| LaunchDarkly | SaaS | Enterprise, SDKs for every language, strong targeting |
| Unleash | Open source / SaaS | Self-hostable, simple, good for startups |
| Flagsmith | Open source / SaaS | Feature flags + remote config, self-hostable |
| Split.io | SaaS | Strong experimentation/analytics integration |
| Flipt | Open source | GitOps-native, lightweight |

### Flag Types

**Release flags**: Gate new features behind a flag. Enable incrementally. Remove after full rollout.

**Operational flags**: Circuit breakers, graceful degradation. Long-lived.

**Experiment flags**: A/B tests. Route cohorts to different experiences for measurement.

**Permission flags**: Entitlement-based access. "Premium users get feature X."

### Flag Lifecycle and Technical Debt

```
Create -> Develop -> Test -> Roll Out (%) -> Fully On -> Remove Flag
```

Stale flags cause dead code paths, testing combinatorial explosion (N flags = 2^N states), cognitive overhead, and risk of accidentally toggling forgotten flags. Mitigate with: expiration dates at creation, automated alerts when 100% on for >30 days, linting rules, quarterly cleanup sprints, mandatory ownership.

---

## Infrastructure as Code

### Terraform

**State Management:** Terraform state tracks the mapping between config and real-world resources. Use remote state (S3 + DynamoDB for locking, or Terraform Cloud). State contains sensitive data -- encrypt at rest, restrict access.

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

**Modules:** Reusable components from the registry or internal modules. Version-pin for stability.

**Plan/Apply Workflow:**
```bash
terraform init      # Initialize providers and backend
terraform plan      # Preview changes (always review!)
terraform apply     # Apply changes after confirmation
terraform destroy   # Tear down resources (dangerous!)
```

**Drift Detection:** `terraform plan` detects drift between state and reality. Reconcile by updating config to match reality or applying to enforce desired state. Tools like Driftctl or Terraform Cloud automate detection.

**Workspaces:** Manage multiple environments with the same configuration. Some teams prefer separate directories per environment.

### Pulumi

Uses general-purpose languages (TypeScript, Python, Go) instead of HCL. Advantages: familiar languages, full language power for loops/conditionals, native unit testing. Tradeoffs: smaller ecosystem, different state management (Pulumi Cloud).

---

## Secrets Management

### Never in Git

Non-negotiable. Secrets in git are compromised secrets, even if removed from HEAD (they remain in history). This includes API keys, tokens, passwords, database connection strings, TLS private keys, OAuth secrets, encryption keys.

### Tools

**HashiCorp Vault:** Dynamic secrets, encryption as a service, identity-based access (K8s service account, AWS IAM), audit logging.

**AWS Secrets Manager / Parameter Store:** Native AWS integration, automatic rotation for RDS credentials, cross-account sharing.

**External Secrets Operator (Kubernetes):** Syncs secrets from central store into K8s Secrets.

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  data:
  - secretKey: password
    remoteRef:
      key: prod/database
      property: password
```

### Rotation Strategies

- **Automated rotation**: Secrets Manager rotates credentials on a schedule via Lambda
- **Dual credentials**: Application supports two simultaneously; rotate one while the other remains active
- **Short-lived tokens**: Prefer tokens that expire (JWT, STS) over long-lived credentials
- **Vault dynamic secrets**: Unique, short-lived credentials per consumer, automatically revoked

---

## GitHub Actions

### Workflow Syntax

```yaml
name: CI/CD Pipeline
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write  # for OIDC

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'
    - run: npm ci
    - run: npm run build
    - uses: actions/upload-artifact@v4
      with:
        name: build-output
        path: dist/
```

### Reusable Workflows

Define with `workflow_call`, invoke from multiple repositories. Pass inputs and secrets explicitly. Avoids duplicating pipeline definitions across repos.

### Matrix Builds

```yaml
strategy:
  matrix:
    node-version: [18, 20, 22]
    os: [ubuntu-latest, macos-latest]
  fail-fast: false
```

### Self-Hosted Runners

For GPU access, private networks, specific hardware, or cost optimization. **Security concern**: Self-hosted runners on public repos are dangerous -- anyone who opens a PR can execute code on your runner. Restrict to private repos or use ephemeral runners.

### Security: OIDC for Cloud Auth

Never store long-lived cloud credentials in GitHub Secrets. Use OIDC federation for short-lived tokens:

```yaml
steps:
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
    aws-region: us-east-1
```

---

## Branching Strategies

### Trunk-Based Development

All developers commit to `main` frequently -- at least daily. Short-lived feature branches (< 2 days). Feature flags hide incomplete work. Main is always deployable. No long-lived branches.

**Why senior teams prefer it:** Reduces merge conflicts dramatically, forces small incremental changes, faster feedback loops, eliminates "integration hell."

### GitFlow

Long-lived develop and main branches with feature, release, and hotfix branches. Makes sense for packaged software with versioned releases, multiple supported versions, or regulatory requirements. Overkill for SaaS products deploying continuously.

**Recommendation for most SaaS teams**: Trunk-based development with feature flags.

---

## Database Migrations in CI/CD

### The Expand/Contract Pattern

**Phase 1 -- Expand** (backward-compatible only):
```sql
ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
```

**Phase 2 -- Migrate** (application uses both schemas):
```sql
UPDATE users SET email_verified = TRUE WHERE verified_at IS NOT NULL;
```

**Phase 3 -- Contract** (remove old schema in a subsequent deploy):
```sql
ALTER TABLE users DROP COLUMN verified_at;
```

### Backward Compatibility

Every migration must be compatible with both current and previous application versions.

**Safe operations:** Adding nullable columns, adding tables, adding indexes (CONCURRENTLY), widening types.

**Dangerous operations (require expand/contract):** Renaming columns, removing columns, changing types, adding NOT NULL without defaults, splitting/merging tables.

### Migration Testing

Run migrations against production-sized data (sanitized) in CI. Test both up and down migrations. Measure migration duration. Use advisory locks to prevent concurrent execution. Tools: Flyway, Liquibase, Alembic, Prisma Migrate.

---

## Interview Questions

**Q: How would you design a CI/CD pipeline for a monorepo with 15 microservices?**

A: (1) Affected service detection via git diff using Nx/Turborepo -- only build/test/deploy changed services. (2) Shared library changes rebuild all dependents via a dependency graph. (3) Parallel execution with matrix strategies. (4) One versioned artifact per service, deployed independently. (5) Shared infra pipeline with manual approval gates. (6) Aggressive caching with content-hash keys.

**Q: Your CI pipeline takes 45 minutes. How do you reduce it?**

A: Profile first -- measure, don't guess. Then: parallelize independent suites, cache dependencies and Docker layers, split tests across runners (Jest `--shard`), use larger runners, run targeted tests on PR (full suite nightly), pre-build base images, quarantine flaky tests.

**Q: When would you choose canary over blue-green deployment?**

A: **Canary** when you need gradual risk reduction with real traffic, have good observability for metric comparison, and want automated promotion/rollback. **Blue-green** when you need instant atomic switchover, want full environment validation before production traffic, or traffic volume is too low for meaningful canary signal.

**Q: How do you handle database migrations during a canary deployment?**

A: All schema changes must be backward-compatible (expand/contract). Run migrations before deploying the canary -- the stable version must tolerate the new schema. Never drop columns while both versions run. The contract phase happens only after 100% rollout and stabilization.

**Q: Your team uses Terraform but someone made changes via the AWS console. How do you handle drift?**

A: Run `terraform plan` to detect drift. If the change should be kept: `terraform import` + update config. If it should be reverted: `terraform apply` to enforce desired state. Prevent future drift with SCPs, Terraform Cloud drift detection, and policy-as-code (Sentinel, OPA).

**Q: Your codebase has 200 feature flags, many stale. How do you address this?**

A: Audit for flags 100% on/off for >30 days. Assign owners to every flag. Enforce expiration dates with platform alerts. Lint rules to detect stale references. Quarterly cleanup sprints. Cap active flags per team.

**Q: How would you design secrets management for a Kubernetes-based platform?**

A: Central store (Vault or AWS Secrets Manager) as source of truth. External Secrets Operator syncs into K8s Secrets. Per-service access control via Vault policies or IAM. Automated rotation with application-side credential refresh. Audit logging. Developers never see production secrets. ExternalSecret manifests in git reference secrets by path, not by value.

---

## Key Takeaways

1. **Artifacts are immutable**: Build once, deploy everywhere. Never rebuild for production.
2. **Deployment strategies are risk management**: Choose based on risk tolerance, traffic volume, and observability maturity.
3. **Database migrations require discipline**: Expand/contract is the only way to achieve zero-downtime schema changes.
4. **Feature flags are powerful but require hygiene**: Every flag needs an owner and an expiration date.
5. **Infrastructure as Code is table stakes**: If it is not in code, it does not exist.
6. **Secrets management is a system, not a tool**: Rotation, access control, auditing, and developer experience all matter.
7. **Trunk-based development scales better than GitFlow** for most SaaS teams.
8. **Security is woven throughout**: OIDC, signed artifacts, dependency scanning, least-privilege access.
