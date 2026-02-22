# Module 07: CI/CD & DevOps -- Cheat Sheet

---

## Deployment Strategy Comparison

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

---

## GitHub Actions Workflow Template

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

---

## Terraform Commands Reference

| Command | Purpose |
|---------|---------|
| `terraform init` | Initialize providers and backend |
| `terraform plan` | Preview changes |
| `terraform apply` | Apply changes |
| `terraform destroy` | Tear down all resources |
| `terraform import <addr> <id>` | Import existing resource into state |
| `terraform state list` | List managed resources |
| `terraform state mv <src> <dst>` | Rename resource in state |
| `terraform state rm <addr>` | Remove resource from state (keeps it alive) |
| `terraform force-unlock <id>` | Release stuck lock (emergency only) |
| `terraform apply -replace=<addr>` | Force recreation of a resource |
| `terraform apply -refresh-only` | Refresh state without changes |

---

## Feature Flag Checklist

**Creating:** Descriptive name, documented purpose, assigned owner, expiration date, safe default (off = old behavior), fallback for flag service unavailability.

**Removing:** Flag 100% on/off >30 days, dead code paths deleted, tests updated, flag deleted from platform, PR approved.

---

## Migration Safety Checklist

**Safe (no expand/contract):** Adding nullable column, adding table, adding index (CONCURRENTLY), widening column.

**Dangerous (multi-deploy expand/contract):** Renaming column, dropping column, changing type, adding NOT NULL without default.

**Order:** (1) Deploy expand migration, (2) Deploy new app code, (3) Verify stability, (4) Deploy contract migration.

---

## Pipeline Design Template

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

---

## Quick Reference: Branching Strategies

**Trunk-Based:** Commit to main daily. Feature branches < 2 days. Feature flags hide incomplete work. Best for SaaS, continuous delivery.

**GitFlow:** Long-lived develop/main. Feature/release/hotfix branches. Best for packaged software, versioned releases, regulatory requirements.

**Rule of thumb:** If you deploy more than once a week, trunk-based development is almost certainly the right choice.
