# Module 07: Infrastructure as Code and GitOps

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

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "production-vpc"
  cidr = "10.0.0.0/16"
  azs  = ["us-east-1a", "us-east-1b", "us-east-1c"]
}
```

**Plan/Apply Workflow:**
```bash
terraform init      # Initialize providers and backend
terraform plan      # Preview changes (always review!)
terraform apply     # Apply changes after confirmation
terraform destroy   # Tear down resources (dangerous!)
```

**Drift Detection:** `terraform plan` detects drift between state and reality. Reconcile by updating config to match or applying to enforce desired state. Tools like Driftctl or Terraform Cloud automate detection.

**Workspaces:** Manage multiple environments with the same configuration. Some teams prefer separate directories per environment.

### Terraform Commands Reference

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

### Pulumi

Uses general-purpose languages (TypeScript, Python, Go) instead of HCL.

```typescript
import * as aws from "@pulumi/aws";

const bucket = new aws.s3.Bucket("my-bucket", {
  acl: "private",
  versioning: { enabled: true },
});

export const bucketName = bucket.id;
```

Advantages: familiar languages, full language power for loops/conditionals, native unit testing. Tradeoffs: smaller ecosystem, different state management (Pulumi Cloud or self-managed).

### Advanced Terraform

**Custom Providers**: Write custom providers using the Terraform Plugin Framework when no existing provider covers your use case -- internal APIs, custom business logic, legacy systems. Alternatives: `null_resource` with local-exec, `terraform-provider-shell`, HTTP provider.

**Terragrunt**: Thin wrapper providing DRY configuration for multi-module Terraform setups.

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

**State Locking**: DynamoDB provides locking for S3 backend. Developer A acquires lock, reads state, applies changes, writes state, releases lock. Developer B is blocked until the lock is released, then reads the updated state. `terraform force-unlock LOCK_ID` is for emergency recovery only (crashed process left a stale lock).

**Importing Existing Resources:**

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

## Developer Experience

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

---

## Interview Questions

**Q: Your team uses Terraform but someone changed things via the AWS console. How do you handle drift?**

A: Run `terraform plan` to detect drift. Evaluate if the change was intentional. If keeping: `terraform import` + update config. If reverting: `terraform apply` to enforce desired state. Prevent future drift with SCPs, drift detection alerts, and policy-as-code (Sentinel, OPA).

**Q: How does GitOps improve security compared to traditional CI/CD?**

A: GitOps inverts the trust model. In traditional CI/CD, the CI server needs credentials to push to the cluster -- a compromised CI server means a compromised cluster. In GitOps, the cluster agent pulls changes from git. No external entity has cluster credentials. All changes go through git (PR review, approvals, audit trail). Drift is automatically corrected.

### Key Takeaways

1. **Infrastructure as Code is table stakes**: If it is not in code, it does not exist.
2. **GitOps inverts the deployment model**: The cluster pulls state from git, improving security and auditability.
3. **ArgoCD ApplicationSets scale GitOps**: Managing hundreds of applications across clusters becomes tractable with generators and templates.
4. **CI/CD security is supply chain security**: Pin dependencies, sign artifacts, verify provenance, generate SBOMs.
5. **Developer experience directly impacts velocity**: Invest in fast inner loops, reproducible environments, and tooling that minimizes toil.
6. **Terraform at scale requires organizational discipline**: State isolation, module versioning, drift detection, and Terragrunt for DRY configuration.
