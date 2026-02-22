# Module 07: CI/CD & DevOps -- Deep Dive

## Table of Contents

1. [GitOps Principles](#gitops-principles)
2. [ArgoCD Deep Dive](#argocd-deep-dive)
3. [Advanced Terraform](#advanced-terraform)
4. [CI/CD Security](#cicd-security)
5. [Testing in Production](#testing-in-production)
6. [Developer Experience](#developer-experience)

---

## GitOps Principles

### The Four Pillars

GitOps is an operational framework where git is the single source of truth for declarative infrastructure and application definitions.

**1. Declarative** -- The entire system is described declaratively. Not "run these 12 commands in order" but "the system should look like this."

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: myapp:v2.1.0
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
```

**2. Versioned and Immutable** -- Desired state is stored in git. Every change is a commit with full history, authorship, and revert capability. Git is the audit log.

**3. Pulled Automatically** -- Agents in the cluster (ArgoCD, Flux) pull desired state from git and apply it. The cluster reconciles itself -- no external push required.

**4. Continuously Reconciled** -- The system watches for divergence between desired state (git) and actual state (cluster). Drift is detected and corrected automatically.

```
Push-based (traditional CI/CD):
  Developer -> CI Server -> Push to Cluster
  Problem: CI server needs cluster credentials. Single point of failure.

Pull-based (GitOps):
  Developer -> Git Commit -> Agent in Cluster pulls changes
  Benefit: Cluster pulls its own config. No external access needed.
```

### GitOps vs Traditional CI/CD

| Aspect | Traditional CI/CD | GitOps |
|--------|-------------------|--------|
| Deployment trigger | CI pipeline pushes | Cluster agent pulls |
| Source of truth | CI pipeline definition | Git repository |
| Drift handling | Manual detection | Automatic reconciliation |
| Rollback | Rerun old pipeline | `git revert` |
| Audit trail | CI logs | Git history |
| Security model | CI has cluster access | Only the agent has cluster access |

### Repository Structure

**Monorepo:** Base manifests with environment overlays via Kustomize in a single repo.

**Polyrepo:** Separate app-repo (source + CI) and config-repo (K8s manifests). CI in the app repo opens a PR or commits the new image tag to the config repo. This provides cleaner separation of concerns and avoids CI loops.

---

## ArgoCD Deep Dive

### Core Architecture

ArgoCD runs inside your Kubernetes cluster and watches git repositories for changes.

**Components:** API Server (REST/gRPC + UI), Application Controller (monitors apps, compares desired vs actual, initiates sync), Repo Server (clones repos, generates manifests from Helm/Kustomize/plain YAML), Redis (caching), Dex/OIDC (authentication).

### ApplicationSets

ApplicationSets generate ArgoCD Applications dynamically -- critical for managing many environments or clusters.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: microservices
spec:
  generators:
  - git:
      repoURL: https://github.com/org/config-repo.git
      revision: HEAD
      directories:
      - path: services/*
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/org/config-repo.git
        targetRevision: HEAD
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

This automatically creates an ArgoCD Application for every subdirectory under `services/`. Add a new service directory and ArgoCD picks it up.

**Generator types:** List (static list), Cluster (per registered cluster), Git directory (from directory structure), Git file (from config files), Matrix (combine two generators, e.g., every service x every cluster), Merge (override base with patch).

### Sync Waves and Hooks

Control deployment order with sync-wave annotations (lower number = applied earlier). Use hooks for lifecycle events:

- `PreSync`: Run before sync (e.g., database migrations)
- `Sync`: Run during sync (default)
- `PostSync`: Run after sync (e.g., smoke tests, notifications)
- `SyncFail`: Run if sync fails (e.g., alerting)

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"  # applied first
---
metadata:
  annotations:
    argocd.argoproj.io/hook: PostSync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
```

### Multi-Cluster Management

Patterns: Hub and spoke (central ArgoCD manages all clusters), per-cluster ArgoCD managed by a meta-ArgoCD (app of apps), or ApplicationSet cluster generator for automatic deployment to all registered clusters.

---

## Advanced Terraform

### Custom Providers

Write custom providers using the Terraform Plugin Framework when no existing provider covers your use case -- internal APIs, custom business logic, legacy systems. Alternatives: `null_resource` with local-exec, `terraform-provider-shell`, HTTP provider.

### Terragrunt

Thin wrapper providing DRY configuration for multi-module Terraform setups.

```hcl
# terragrunt.hcl (root)
remote_state {
  backend = "s3"
  generate {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    bucket         = "my-terraform-state"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

inputs = {
  environment = "production"
  region      = "us-east-1"
}
```

**Key features:** DRY backend configuration (define once, inherit everywhere), dependency management (`dependency` blocks), `run-all` to apply modules in dependency order, auto-generated provider and backend configs.

### State Locking Deep Dive

DynamoDB provides locking for S3 backend. Developer A acquires lock, reads state, applies changes, writes state, releases lock. Developer B is blocked until the lock is released, then reads the updated state. `terraform force-unlock LOCK_ID` is for emergency recovery only (crashed process left a stale lock).

### Importing Existing Resources

When resources were created outside Terraform:

```bash
# Import a single resource
terraform import aws_instance.web i-1234567890abcdef0

# Import blocks (Terraform 1.5+)
import {
  to = aws_instance.web
  id = "i-1234567890abcdef0"
}

# Auto-generate config
terraform plan -generate-config-out=generated.tf
```

Workflow: write resource block, import to state, run plan until no diff, resource is now managed.

---

## CI/CD Security

### Supply Chain Attacks

The CI/CD pipeline is a high-value target. Compromising the pipeline means compromising everything it deploys.

**Attack vectors:** Dependency confusion (malicious package mimicking internal name on public registry), compromised CI actions/plugins (malicious update to a GitHub Action you use), stolen CI credentials (exfiltrated via malicious PR), build system compromise (injecting code during build).

**Mitigations:**
- Pin all CI actions to a specific commit SHA, not a tag (tags can be moved)
- Use dependency lockfiles (package-lock.json, go.sum) and verify checksums
- Restrict secrets access to specific branches/environments
- Review third-party actions before adopting
- Use private package registries with upstream proxying

```yaml
# Pin to SHA, not tag
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
# NOT: actions/checkout@v4 (tag can be reassigned to malicious code)
```

### SLSA Framework

SLSA (Supply-chain Levels for Software Artifacts) defines four levels: SLSA 1 (documented build), SLSA 2 (signed provenance, hosted build), SLSA 3 (hardened build platform), SLSA 4 (two-person review, hermetic build).

### Sigstore

Keyless code signing: authenticate via OIDC, short-lived certificate from Fulcio, sign artifact, record in Rekor transparency log, discard key. Verification uses the transparency log and OIDC identity.

```bash
cosign sign --yes myregistry.com/myapp:v1.0.0
cosign verify myregistry.com/myapp:v1.0.0
```

### SBOM (Software Bill of Materials)

Lists all components in your software -- dependencies, versions, licenses. Generate with Syft (`syft myimage -o spdx-json`), scan with Grype. Enables rapid CVE response ("are we affected?"), license compliance, and regulatory compliance.

---

## Testing in Production

### Dark Launching

Deploy new code to production but do not expose it to users. Mirror real requests to the new code path and compare results -- the new system's responses are logged but never returned to users.

```python
async def get_recommendations(user_id: str):
    result = await legacy_recommendation_service.get(user_id)

    if feature_flags.is_enabled('dark-launch-new-recs'):
        asyncio.create_task(
            dark_launch_new_recommendations(user_id, expected=result)
        )

    return result  # always returns legacy result

async def dark_launch_new_recommendations(user_id, expected):
    try:
        actual = await new_recommendation_service.get(user_id)
        metrics.record_comparison(expected, actual)
    except Exception as e:
        logger.warning(f"Dark launch error: {e}")
        # Never affects the user
```

### Shadow Traffic

Route a copy of production traffic to a shadow service via Istio traffic mirroring. Shadow responses are discarded. Caution: doubles your load (account in capacity planning), ensure shadow does not write to production databases or send real notifications.

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
spec:
  http:
  - route:
    - destination:
        host: my-service-v1
    mirror:
      host: my-service-v2
    mirrorPercentage:
      value: 100.0
```

### Chaos Engineering Integration

Integrate chaos experiments into CI/CD for continuous resilience verification. Progressive approach:

1. **Game days**: Scheduled, manual chaos experiments with the team watching
2. **Automated experiments**: Run in staging as part of CI/CD, verify SLOs held during chaos
3. **Continuous chaos in production**: Netflix-style random failures, with kill switches

---

## Developer Experience

### The DX Problem

If the local development environment diverges significantly from production, bugs are found late and productivity suffers. The goal: make the development inner loop as fast and production-like as possible.

### Devcontainers

Standardize development environments using Docker containers.

```json
{
  "name": "My Project",
  "image": "mcr.microsoft.com/devcontainers/typescript-node:20",
  "features": {
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {}
  },
  "forwardPorts": [3000, 5432],
  "postCreateCommand": "npm install"
}
```

Benefits: new developer onboarding (clone, open in container, code), consistent tooling, works in VS Code, GitHub Codespaces, JetBrains Gateway.

### Tilt and Skaffold

**Tilt:** Automates the Kubernetes inner dev loop. Detects file changes, syncs into running containers (no rebuild), hot-reload picks up changes. Total cycle: 1-3 seconds vs minutes for full rebuild.

**Skaffold:** Google's equivalent. YAML config, profiles for different environments, file sync support.

| Aspect | Tilt | Skaffold |
|--------|------|----------|
| Config language | Starlark (Python-like) | YAML |
| UI | Built-in web dashboard | CLI-based |
| Live update | First-class feature | Supported via sync |
| Backing | Docker Inc. | Google |

### Optimizing the Dev Inner Loop

**Metrics to track:** Time from code change to local result, time from push to PR checks passing, time from merge to production, frequency of "works on my machine" issues.

**Strategies:** Hot-reload for interpreted languages, incremental compilation for compiled languages, local stubs/mocks for external dependencies, Docker Compose for simpler multi-service setups, shared remote dev environments for costly services.

---

## Key Takeaways

1. **GitOps inverts the deployment model**: The cluster pulls state from git, improving security and auditability.
2. **ArgoCD ApplicationSets scale GitOps**: Managing hundreds of applications across clusters becomes tractable with generators and templates.
3. **CI/CD security is supply chain security**: Pin dependencies, sign artifacts, verify provenance, generate SBOMs.
4. **Testing in production is not reckless when done right**: Dark launching and shadow traffic validate with real workloads while keeping users safe.
5. **Developer experience directly impacts velocity**: Invest in fast inner loops, reproducible environments, and tooling that minimizes toil.
6. **Terraform at scale requires organizational discipline**: State isolation, module versioning, drift detection, and Terragrunt for DRY configuration.
