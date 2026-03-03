# Module 06: Kubernetes Advanced Patterns

## Helm

Helm is the package manager for Kubernetes. A **chart** is a collection of templated Kubernetes manifests.

**Chart structure:**
```
mychart/
  Chart.yaml          # Metadata (name, version, dependencies)
  values.yaml         # Default configuration
  templates/          # Templated manifests
    deployment.yaml
    service.yaml
    _helpers.tpl      # Named template helpers
  charts/             # Dependency charts
```

### Values and Templating

```yaml
# templates/deployment.yaml
spec:
  replicas: {{ .Values.replicaCount }}
  containers:
    - image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
      resources:
        {{- toYaml .Values.resources | nindent 8 }}
```

### Key Commands

```bash
helm install my-release ./mychart -f production-values.yaml
helm upgrade my-release ./mychart -f production-values.yaml
helm upgrade --install my-release ./mychart   # Idempotent install/upgrade
helm rollback my-release 1
helm template my-release ./mychart -f values.yaml  # Debug render without applying
helm list -A
```

### Helmfile

Declaratively manages multiple Helm releases across environments with dependency ordering and environment-specific values.

---

## GitOps

Git is the single source of truth. A controller (ArgoCD, Flux) in the cluster continuously reconciles actual state with desired state in Git.

### ArgoCD vs Flux

| Feature | ArgoCD | Flux |
|---|---|---|
| UI | Rich web visualization | Minimal (CLI + Grafana) |
| Multi-cluster | ApplicationSets, centralized | Decentralized per cluster |
| Sync strategy | Manual or auto sync with pruning | Auto reconciliation by default |
| Helm support | First-class, renders in-cluster | HelmRelease CRD |
| Learning curve | Moderate (UI helps) | Lower (purely declarative) |

### Pull-Based Deployment

Traditional CI/CD: CI builds the image, then **pushes** manifests to the cluster. This requires CI to have cluster credentials.

GitOps: CI builds the image and updates the manifest in Git (new image tag). The GitOps controller **pulls** the change and applies it. The cluster is the only entity with cluster credentials.

**Benefits:**
- **Audit trail:** Every change is a Git commit.
- **Rollback:** `git revert` the change.
- **Drift detection:** The controller detects and corrects manual `kubectl` changes.
- **Security:** CI never needs cluster credentials.

---

## Custom Resources and Operators

### Custom Resource Definitions (CRDs)

CRDs extend the Kubernetes API with custom resource types. After creating a CRD, you create, read, update, and delete instances using standard kubectl.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databases.myorg.io
spec:
  group: myorg.io
  names:
    kind: Database
    plural: databases
    shortNames: ["db"]
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                engine:
                  type: string
                  enum: ["postgres", "mysql"]
                replicas:
                  type: integer
                  minimum: 1
```

### Operators

An operator is a controller that watches custom resources and reconciles desired state with actual state. It encodes operational knowledge in code.

**Reconciliation loop:**
1. Watch for changes to the custom resource.
2. Compare desired state (CR spec) with actual state (running pods, PVCs).
3. Take action: create StatefulSet, scale replicas, trigger backup, perform upgrade.
4. Update CR status with actual state.
5. Repeat.

**Popular operators:** CloudNativePG (Postgres), Strimzi (Kafka), Prometheus Operator, Cert-Manager.

**Frameworks:** Kubebuilder (Go, official SIG), Operator SDK (Go/Helm/Ansible), Kopf (Python), Metacontroller (declarative webhooks).

**Interview insight:** Operators shine for stateful, operationally complex workloads (databases, message brokers, ML platforms). Simple stateless services do not need them -- a Deployment and HPA suffice.

---

## Service Mesh Deep Dive

### Sidecar Injection

Label a namespace (`istio-injection=enabled`). Istio's MutatingAdmissionWebhook modifies pod specs to add an Envoy sidecar and an init container that configures iptables to redirect all traffic through the sidecar.

```
Pod after injection:
+-------------------------------------------+
| init: istio-init  (iptables setup)        |
| container: app    (your code, unmodified) |
| container: istio-proxy (Envoy sidecar)    |
+-------------------------------------------+

Traffic flow:
  Inbound:  NIC -> iptables -> istio-proxy -> application
  Outbound: application -> iptables -> istio-proxy -> NIC
```

### Traffic Policies

**Circuit breaking** via DestinationRule: configure max connections, max pending requests, and outlier detection (eject backends with consecutive 5xx errors for a configurable duration).

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: backend-cb
spec:
  host: backend-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 100
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
```

**Traffic mirroring:** Shadow a percentage of production traffic to a new version without affecting real responses. Essential for validating new versions safely.

**Fault injection:** Inject delays or errors to test resilience. Configure via VirtualService to add a 5-second delay to 10% of requests.

### Ambient Mesh (Sidecarless)

The sidecar model adds latency (two extra hops per request) and resource overhead (Envoy per pod). Istio's Ambient Mesh replaces sidecars with:

- **ztunnel:** Per-node agent handling mTLS and L4 traffic management. Dramatically lower overhead than per-pod sidecars.
- **Waypoint proxies:** Optional per-service L7 proxies deployed only for services needing routing, retries, or observability.

This is the direction service meshes are headed -- reducing overhead for the common case while preserving L7 features where needed.

---

## Multi-Cluster Strategies

### Why Multi-Cluster?

- **Blast radius reduction:** A control plane failure affects only one cluster.
- **Regulatory compliance:** Data residency requirements may mandate regional clusters.
- **Scale limits:** Single cluster limits (~5000 nodes, ~150K pods) may be exceeded.
- **Team autonomy:** Separate clusters per team or business unit.

### Patterns

**Active-active (replicated):** Each cluster runs the same services. A global load balancer distributes traffic.

```
[Global LB / DNS]
     |          |
  [Cluster A]  [Cluster B]
  US-East      EU-West
  (full stack)  (full stack)
```

**Segmented:** Different services in different clusters. Cross-cluster service discovery required.

**Hub-and-spoke:** Central management cluster (ArgoCD, monitoring, policy) controls satellite workload clusters.

### Cross-Cluster Networking

| Solution | Approach |
|---|---|
| Istio multi-cluster | Shared or replicated control planes with cross-cluster service discovery |
| Cilium Cluster Mesh | eBPF-based, connects pod networks across clusters |
| Submariner | Encrypted tunnels between clusters, Lighthouse for discovery |
| Cloud-native | VPC peering + DNS-based service discovery |

### Multi-Cluster GitOps

ArgoCD ApplicationSets generate Applications from a cluster selector, deploying the same manifests across multiple clusters automatically:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            env: production
  template:
    spec:
      source:
        repoURL: https://github.com/myorg/k8s-manifests
        path: apps/api-server
      destination:
        server: '{{server}}'
```

---

## Kubernetes Security

### RBAC (Role-Based Access Control)

Roles define permissions (verbs on resources). RoleBindings assign roles to users, groups, or service accounts.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: deployment-manager
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
```

**Namespace-scoped:** Role/RoleBinding. **Cluster-wide:** ClusterRole/ClusterRoleBinding.

**Principle of least privilege:** Grant only required permissions. Avoid `cluster-admin` for regular users.

### Pod Security Standards

| Profile | Description |
|---|---|
| Privileged | No restrictions. Full host access |
| Baseline | Blocks known escalations (no hostNetwork, no hostPID, no privileged containers) |
| Restricted | Non-root, read-only rootfs, drop all capabilities, seccomp profile required |

Enforce via namespace labels:
```yaml
metadata:
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### OPA/Gatekeeper

Custom policy enforcement via validating admission webhooks. Write constraint templates in Rego, then apply constraints to target specific resource types. Examples: require labels, block latest tags, enforce resource limits, restrict image registries.

### Secrets Management

Kubernetes Secrets are base64-encoded in etcd -- not encrypted by default.

**Production approaches:**
- **etcd encryption at rest:** Configure API server to encrypt Secrets using AES-GCM.
- **External Secrets Operator:** Syncs secrets from HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault into Kubernetes Secrets. Automatic rotation on a configurable interval.

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: db-credentials
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: ClusterSecretStore
  target:
    name: db-credentials
  data:
    - secretKey: password
      remoteRef:
        key: production/database
        property: password
```

### Supply Chain Security

- **Cosign (Sigstore):** Sign container images during CI; verify signatures before deployment.
- **Kyverno/Gatekeeper policies:** Reject unsigned or unverified images at admission.
- **SBOM generation:** `syft` or `trivy` produces software bills of materials for vulnerability tracking.

**Defense in depth:** RBAC for authorization, Pod Security Standards for workload hardening, NetworkPolicies for network segmentation, OPA/Gatekeeper for custom policies, External Secrets for secret management, and image scanning in CI. No single mechanism is sufficient.

---

## K8s Resource Templates

### Deployment (minimal production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
spec:
  replicas: 3
  selector:
    matchLabels: { app: api-server }
  strategy:
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  template:
    metadata:
      labels: { app: api-server }
    spec:
      containers:
        - name: api
          image: myregistry/api-server:v1.0.0
          ports: [{ containerPort: 8080 }]
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { memory: 512Mi }
          readinessProbe:
            httpGet: { path: /readyz, port: 8080 }
          livenessProbe:
            httpGet: { path: /healthz, port: 8080 }
```

### Service + Ingress + HPA

```yaml
# Service
apiVersion: v1
kind: Service
spec:
  type: ClusterIP
  selector: { app: api-server }
  ports: [{ port: 80, targetPort: 8080 }]
---
# Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
spec:
  ingressClassName: nginx
  tls: [{ hosts: [api.example.com], secretName: api-tls }]
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service: { name: api-server, port: { number: 80 } }
---
# HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api-server }
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```
