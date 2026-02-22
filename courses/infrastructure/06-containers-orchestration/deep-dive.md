# Module 06 Deep Dive: Container & Kubernetes Internals

## Overview

Senior infrastructure interviews test whether you understand what happens beneath the Kubernetes API. This deep dive covers the Linux primitives that make containers work, control plane architecture, custom extensions, service mesh internals, multi-cluster strategies, and security hardening.

---

## Container Internals

### Linux Namespaces

Containers are not virtual machines. They are processes isolated by Linux kernel features. **Namespaces** restrict what a process can see.

| Namespace | Isolates |
|---|---|
| PID | Process IDs (container sees only its own processes) |
| NET | Network stack (own interfaces, IPs, routing, iptables) |
| MNT | Filesystem mounts |
| UTS | Hostname |
| IPC | Shared memory, semaphores |
| USER | UID/GID mapping (rootless containers) |
| CGROUP | Cgroup visibility |

**How it works in practice:**

```
Host Kernel
  |
  +-- Namespace Set A (Container 1)
  |     PID ns: PID 1 = nginx
  |     NET ns: eth0 = 172.17.0.2
  |     MNT ns: / = overlay filesystem
  |
  +-- Namespace Set B (Container 2)
  |     PID ns: PID 1 = node
  |     NET ns: eth0 = 172.17.0.3
  |     MNT ns: / = overlay filesystem
  |
  +-- Host namespace
        PID ns: PID 1 = systemd, PID 1234 = nginx, PID 1235 = node
```

From the host, containers are just regular processes with restricted resource views. This is the key insight: there is no container hypervisor, no hardware virtualization. Isolation is a kernel-level resource partitioning mechanism.

### Cgroups (Control Groups)

While namespaces provide **isolation** (what a process can see), cgroups provide **resource control** (what a process can use). Cgroups v2 is now default in most Linux distributions.

- **CPU:** Bandwidth quota. 500m = 50% of one core, implemented as 50ms per 100ms scheduling period. Hitting the limit causes **throttling** -- the kernel pauses the process until the next period. This manifests as latency spikes, not reduced CPU metrics. This is why some operators skip CPU limits entirely.
- **Memory:** Hard limit. Exceeding it triggers the OOM killer, terminating the process. Unlike CPU, memory is not throttleable -- it is a hard boundary.
- **IO:** Bandwidth and IOPS limits per block device.
- **PIDs:** Maximum number of processes (prevents fork bombs).

```
Cgroup hierarchy:
/sys/fs/cgroup/kubepods/
  +-- burstable/pod-abc123/container-xyz/
  |     cpu.max: 50000 100000     # 50ms per 100ms = 0.5 CPU
  |     memory.max: 536870912     # 512Mi
  +-- guaranteed/pod-def456/container-uvw/
        cpu.max: 100000 100000    # 1 full CPU
        memory.max: 1073741824    # 1Gi
```

### Overlay Filesystems

Container images use layered filesystems. Each Dockerfile instruction creates a layer. OverlayFS combines read-only layers with a writable layer on top.

```
Container Filesystem (OverlayFS):

  [Writable Layer]          (container's changes)
  [Layer 3: COPY . .]      (application code)
  [Layer 2: RUN npm ci]    (node_modules)
  [Layer 1: FROM node:20]  (base OS + Node.js)
```

**Read:** Search top-to-bottom, return first match.
**Write:** Copy-on-write -- file is copied up from the lower layer, then modified.
**Delete:** Whiteout entry hides the lower-layer file.

**Performance implication:** First write to a large lower-layer file is slow (full copy). For databases and heavy-write workloads, use volume mounts that bypass the overlay filesystem entirely.

### OCI Runtime Spec

The Open Container Initiative defines image and runtime specifications.

| Runtime | Level | Description |
|---|---|---|
| containerd | High-level | Container lifecycle, image pull, storage. Default in K8s since v1.24 |
| CRI-O | High-level | Lightweight, designed specifically for Kubernetes |
| runc | Low-level | Reference OCI runtime. Creates namespaces, sets up cgroups, starts process |
| gVisor (runsc) | Low-level | Sandboxed -- intercepts syscalls for additional isolation |
| Kata Containers | Low-level | Lightweight VMs for stronger isolation boundaries |

**Execution flow:** kubelet -> CRI (Container Runtime Interface) -> containerd -> runc -> container process.

---

## Kubernetes Architecture

### Control Plane Components

```
+------ Control Plane (3+ nodes for HA) ------+
|                                               |
|  [API Server]  - Central hub for all comms    |
|  [etcd]        - Distributed KV store (Raft)  |
|  [Scheduler]   - Places pods on nodes         |
|  [Controller   - Reconciliation loops for     |
|   Manager]       Deployments, ReplicaSets,    |
|                  Nodes, Jobs, etc.            |
+-----------------------------------------------+
```

**API Server** is the only component that directly accesses etcd. All others interact through the API server's watch mechanism.

### API Server Request Flow

1. **Authentication:** Who is making the request? (x509 certs, bearer tokens, OIDC)
2. **Authorization:** Is this identity allowed? (RBAC policies)
3. **Admission controllers:**
   - Mutating webhooks: modify the request (inject sidecars, set defaults, add labels)
   - Validating webhooks: accept or reject (enforce policies via OPA/Gatekeeper)
4. **Persistence:** Object is stored in etcd.
5. **Notification:** Watch streams notify controllers and scheduler of the change.

### etcd Operational Concerns

- **Performance:** Sensitive to disk latency. Use SSDs with dedicated disks.
- **Backup:** Regular snapshots are critical. Losing etcd means losing all cluster state.
- **Size:** Default max request size is 1.5MB. Alarm triggers at 2GB database size.
- **Compaction:** Retains all historical revisions; regular compaction reclaims space.

### Node Components

- **kubelet:** Registers node with API server, watches for pod specs, manages container lifecycle via CRI, executes probes (liveness, readiness, startup), reports status.
- **kube-proxy:** Implements Services by programming iptables or IPVS rules. IPVS offers O(1) lookups (better at scale with thousands of Services). Cilium's eBPF mode replaces kube-proxy entirely for lowest latency.
- **Container runtime:** containerd or CRI-O.
- **CNI plugin:** Pod networking (Calico, Cilium, Flannel, Weave).

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

**Interview insight:** Discuss defense in depth -- RBAC for authorization, Pod Security Standards for workload hardening, NetworkPolicies for network segmentation, OPA/Gatekeeper for custom policies, External Secrets for secret management, and image scanning in CI. No single mechanism is sufficient.
