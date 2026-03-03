# Module 07: Pipeline Design and Deployment Strategies

## Overview

Continuous Integration and Continuous Delivery form the backbone of modern software delivery. For senior engineers, mastery goes far beyond "set up a pipeline" -- it means designing deployment strategies that minimize risk, managing infrastructure declaratively, handling database migrations without downtime, and building developer workflows that scale across large teams.

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

### Pipeline Design Template

```
Stage 1: Quality Gates (parallel, fast)
  |-- Lint, Type check, Security scan, Unit tests

Stage 2: Build (after Stage 1)
  |-- Build artifact, Docker image, push to registry (commit SHA tag)

Stage 3: Integration (parallel, after Stage 2)
  |-- Integration tests, Contract tests, E2E tests

Stage 4: Deploy Staging (after Stage 3)
  |-- Deploy, Smoke tests, Performance tests (optional)

Stage 5: Deploy Production (main branch only)
  |-- Approval gate, Deploy (canary/blue-green/rolling), Smoke tests, Monitor
```

**Optimization:** Cancel redundant runs, cache dependencies, shard tests, fail-fast, OIDC auth, pin action SHAs.

### Parallel vs Sequential Execution

```yaml
# Sequential: each stage depends on the previous
stages:
  - build
  - test
  - deploy

# Parallel within stages: independent jobs run concurrently
test:
  unit-tests:        # These run in parallel
    ...
  integration-tests: # within the "test" stage
    ...
  security-scan:
    ...
```

**When to parallelize:** Independent test suites (unit, integration, linting), multi-platform builds (linux/amd64, linux/arm64), multi-service monorepo builds, matrix builds across language/runtime versions.

**When to keep sequential:** Deploy stages that depend on test results, database migrations before application deployment, smoke tests after deployment before traffic shifting.

### Fail-Fast Strategies

The goal is to surface failures as quickly as possible to minimize wasted compute and developer wait time.

- **Lint and type-check first** -- fastest checks run before compilation
- **Run unit tests before integration tests** -- cheaper tests gate expensive ones
- **Cancel redundant runs** -- if a new commit is pushed, cancel the in-progress run for the previous commit
- **Required checks vs optional checks** -- clearly separate blocking from informational
- **Test splitting and ordering** -- run previously-failed tests first (pytest `--last-failed`, Jest `--changedSince`)

### Artifact Management

```
Build -> Artifact Registry -> Deploy (pull artifact)
         (immutable)
```

**Principles:**
- Artifacts are immutable -- once built, never modified
- Store in a dedicated registry (Docker Hub, ECR, Artifactory, GitHub Packages)
- Tag with commit SHA for traceability: `myapp:a1b2c3d`
- Implement retention policies to manage storage costs
- Sign artifacts for supply chain security (cosign, Notary)

**Anti-patterns:**
- Rebuilding for each environment (staging artifact != production artifact)
- Using mutable tags like `latest` in production
- Storing artifacts in git (large binary files)
- No cleanup policy -- registries grow unbounded

---

## Deployment Strategies

### Deployment Strategy Comparison

| Strategy | Zero Downtime | Rollback Speed | Resource Overhead | Best For |
|----------|:---:|:---:|:---:|---|
| **Blue-Green** | Yes | Instant (switch LB) | 2x infrastructure | Atomic releases, full validation |
| **Canary** | Yes | Fast (shift to 0%) | +5-10% infra | Gradual rollout, metric-based decisions |
| **Rolling** | Yes | Slow (re-roll) | Minimal (maxSurge) | Kubernetes default, stateless services |
| **Recreate** | No | Slow (redeploy) | None | Dev/test, stateful apps |
| **Shadow/Dark** | N/A | N/A | 2x compute | Validating new systems under real load |

**Decision flow:**
- Instant rollback with full pre-validation? --> Blue-Green
- Good observability + gradual risk reduction? --> Canary
- Simple stateless services on K8s? --> Rolling
- Validating a rewrite before cutover? --> Shadow/Dark launch

### Blue-Green Deployments

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

**Zero-Downtime Switching:**

The traffic switch happens at the load balancer or DNS level:

- **Load balancer switch** (preferred): Update target group to point to the green environment. Instantaneous, no DNS propagation delay.
- **DNS switch**: Update DNS record to point to green. Subject to TTL propagation -- clients may still hit blue for minutes.
- **Service mesh switch**: Route 100% traffic to the new version via Istio VirtualService or similar.

**Database Migrations with Blue-Green:**

Both blue and green must talk to the same database during the transition. Use the **Expand/Contract pattern**:

1. **Expand**: Add new columns/tables without removing old ones. Both v1.0 and v1.1 can operate.
2. **Deploy green (v1.1)**: It uses the new schema while blue (v1.0) ignores the new fields.
3. **Switch traffic**: Green is now live.
4. **Contract**: Remove deprecated columns/tables in a subsequent release once blue is decommissioned.

**Critical rule**: Never make a breaking schema change in a single deployment. Always use at least two releases.

**Rollback Strategy:**

- **Instant rollback**: Switch load balancer back to blue.
- **Database rollback concern**: If green wrote data using new schema features, switching back to blue may cause issues. Design migrations to be backward-compatible.
- **Keep blue alive**: Do not decommission blue until the green deployment is confirmed stable (hours or days, not minutes).
- **Session state**: If using sticky sessions, in-flight sessions on blue may be disrupted on switch. Prefer stateless architecture.

**Tradeoffs:** Instant rollback and full environment validation before switch, but requires double the infrastructure and careful expand/contract discipline for database changes.

### Canary Deployments

Deploy the new version to a small subset of infrastructure and route a fraction of traffic to it. Gradually increase the percentage as confidence grows.

```
t=0:   [v1.0: 100%] [v1.1:   0%]
t=5m:  [v1.0:  95%] [v1.1:   5%]
t=15m: [v1.0:  80%] [v1.1:  20%]
t=30m: [v1.0:  50%] [v1.1:  50%]
t=60m: [v1.0:   0%] [v1.1: 100%]
```

**Implementation mechanisms:**
- **Kubernetes**: Istio VirtualService with weight-based routing
- **AWS**: ALB weighted target groups
- **CDN-level**: Cloudflare Workers, AWS CloudFront functions
- **Application-level**: Feature flags directing traffic subsets

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

**Metric-Based Promotion:**

Automated canary analysis compares the canary's metrics against the baseline: error rate (HTTP 5xx, exception rate), latency (p50, p95, p99), saturation (CPU, memory), and business metrics (conversion rate, cart abandonment).

**Tools:** Flagger (Kubernetes-native, integrates with Istio/Linkerd/NGINX), Argo Rollouts (K8s-native, supports multiple traffic managers), Spinnaker (multi-cloud, Netflix-origin), AWS CodeDeploy.

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
        min: 99           # rollback if success rate < 99%
    - name: request-duration
      thresholdRange:
        max: 500          # rollback if p99 latency > 500ms
```

**Progressive Delivery:**

Progressive delivery extends canary deployments with:
- **Header-based routing**: Route specific users (internal, beta testers) to the canary
- **Geographic routing**: Roll out to one region first
- **Cohort-based**: Route by user ID hash for consistent experience
- **Manual gates**: Require human approval before advancing to the next traffic percentage

### Rolling Deployments

Kubernetes rolling update strategy replaces pods incrementally.

```yaml
apiVersion: apps/v1
kind: Deployment
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

**Health Check Gates:**

- **startupProbe**: Protects slow-starting containers. Liveness/readiness paused until startup succeeds.
- **readinessProbe**: Pod receives traffic only when ready. Failed readiness removes it from service endpoints.
- **livenessProbe**: Pod is restarted if liveness fails. Use cautiously -- cascading restarts can cause outages.

**Connection Draining:**

When terminating a pod: (1) SIGTERM received, (2) removed from service endpoints (no new traffic), (3) `terminationGracePeriodSeconds` to finish in-flight requests, (4) SIGKILL after grace period. Use a `preStop` sleep hook to allow endpoint removal to propagate before the application starts shutting down.

---

## GitHub Actions

### Workflow Template

```yaml
name: CI/CD Pipeline
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
permissions:
  contents: read
  id-token: write
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: '20', cache: 'npm' }
    - run: npm ci && npm run lint && npm run typecheck
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix: { shard: [1, 2, 3] }
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with: { node-version: '20', cache: 'npm' }
    - run: npm ci && npm test -- --shard=${{ matrix.shard }}/3
  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: docker/build-push-action@v5
      with:
        push: ${{ github.ref == 'refs/heads/main' }}
        tags: myregistry/myapp:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
  deploy:
    if: github.ref == 'refs/heads/main'
    needs: build
    runs-on: ubuntu-latest
    environment: production
    steps:
    - uses: aws-actions/configure-aws-credentials@v4
      with:
        role-to-assume: arn:aws:iam::123456789012:role/deploy
        aws-region: us-east-1
    - run: echo "Deploying ${{ github.sha }}"
```

### Reusable Workflows

Define with `workflow_call`, invoke from multiple repositories. Pass inputs and secrets explicitly.

### Matrix Builds

```yaml
strategy:
  matrix:
    node-version: [18, 20, 22]
    os: [ubuntu-latest, macos-latest]
  fail-fast: false  # don't cancel other matrix jobs on failure
```

### Self-Hosted Runners

For GPU access, private networks, specific hardware, or cost optimization. **Security concern**: Self-hosted runners on public repos are dangerous -- anyone who opens a PR can execute code on your runner. Restrict to private repos or use ephemeral runners.

### Security: OIDC for Cloud Auth

**Never store long-lived cloud credentials in GitHub Secrets.** Use OIDC federation:

```yaml
steps:
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789012:role/github-actions-role
    aws-region: us-east-1
# Now AWS CLI/SDKs use short-lived credentials
```

---

## Branching Strategies

### Trunk-Based Development

All developers commit to `main` frequently -- at least daily, ideally multiple times per day. Short-lived feature branches (< 2 days). Feature flags hide incomplete work. Main is always deployable. No long-lived branches.

**Why senior teams prefer it:** Reduces merge conflicts dramatically, forces small incremental changes, faster feedback loops, eliminates "integration hell."

### GitFlow

Long-lived develop and main branches with feature, release, and hotfix branches. Makes sense for packaged software with versioned releases, multiple supported versions, or regulatory requirements. Overkill for SaaS products deploying continuously.

**Recommendation for most SaaS teams**: Trunk-based development with feature flags. GitFlow adds ceremony that slows down continuous delivery.

**Rule of thumb:** If you deploy more than once a week, trunk-based development is almost certainly the right choice.

---

## Interview Questions

**Q: How would you design a CI/CD pipeline for a monorepo with 15 microservices?**

A: (1) Affected service detection via git diff using Nx/Turborepo -- only build/test/deploy changed services. (2) Shared library changes rebuild all dependents via a dependency graph. (3) Parallel execution with matrix strategies. (4) One versioned artifact per service, deployed independently. (5) Shared infra pipeline with manual approval gates. (6) Aggressive caching with content-hash keys.

**Q: Your CI pipeline takes 45 minutes. How do you reduce it?**

A: Profile first -- measure, don't guess. Then: parallelize independent suites, cache dependencies and Docker layers, split tests across runners (Jest `--shard`, pytest-split), use larger runners, run targeted tests on PR (full suite nightly), pre-build base images, quarantine flaky tests instead of re-running.

**Q: When would you choose canary over blue-green deployment?**

A: **Canary** when you need gradual risk reduction with real traffic, have good observability for metric comparison, and want automated promotion/rollback. **Blue-green** when you need instant atomic switchover, want full environment validation before production traffic, or traffic volume is too low for meaningful canary signal.

**Q: How do you handle database migrations during a canary deployment?**

A: All schema changes must be backward-compatible (expand/contract). Run migrations before deploying the canary -- the stable version must tolerate the new schema. Never drop columns while both versions run. The contract phase happens only after 100% rollout and stabilization.

### Key Takeaways

1. **Artifacts are immutable**: Build once, deploy everywhere. Never rebuild for production.
2. **Deployment strategies are risk management**: Choose based on risk tolerance, traffic volume, and observability maturity.
3. **Trunk-based development scales better than GitFlow** for most SaaS teams.
4. **Security is woven throughout**: OIDC, signed artifacts, dependency scanning, least-privilege access.
