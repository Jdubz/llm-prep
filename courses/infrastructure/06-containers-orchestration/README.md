# Module 06: Containers & Orchestration

## Overview

Containers and Kubernetes are the default deployment platform for modern distributed systems. Senior interviews demand you reason about image optimization, security, resource management, scaling strategies, and deployment patterns -- not just write a Dockerfile.

---

## Table of Contents

1. [Docker](#docker)
2. [Kubernetes Core Concepts](#kubernetes-core-concepts)
3. [Networking in Kubernetes](#networking-in-kubernetes)
4. [Storage](#storage)
5. [Scaling](#scaling)
6. [Deployment Strategies](#deployment-strategies)
7. [Helm](#helm)
8. [GitOps](#gitops)
9. [Resource Management](#resource-management)
10. [Debugging](#debugging)
11. [Interview Questions](#interview-questions)

---

## Docker

### Multi-Stage Builds

Separate build and runtime environments to reduce image size and attack surface.

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --production=false
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./
USER appuser
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

### Layer Caching Optimization

Docker rebuilds all layers after a changed layer. Order from least to most frequently changing:

```dockerfile
COPY package*.json ./       # Rarely changes
RUN npm ci                  # Rebuilds only when deps change
COPY . .                    # Changes every commit
RUN npm run build           # Rebuilds every commit
```

**BuildKit cache mounts** persist caches across builds even when layers are invalidated:

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=cache,target=/root/.npm npm ci
```

### Security Scanning

Scan images in CI and block deployments with critical vulnerabilities:

```bash
trivy image --exit-code 1 --severity CRITICAL myapp:latest
snyk container test myapp:latest
```

### Distroless and Scratch Images

**Distroless:** Only the runtime and dependencies. No shell, no package manager. **Scratch:** The empty image -- only for statically compiled binaries.

```dockerfile
FROM golang:1.22 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /server

FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
CMD ["/server"]
```

**Trade-off:** More secure and smaller but harder to debug. Use ephemeral debug containers in Kubernetes.

### BuildKit Features

BuildKit is Docker's modern build engine (default since Docker 23.0).

- **Parallel stages:** Independent stages build concurrently, not sequentially.
- **Cache mounts:** `--mount=type=cache` persists package manager caches across builds.
- **Secret mounts:** `--mount=type=secret` injects secrets without baking them into layers.
- **SSH forwarding:** Use host SSH keys during build for private repos.

```dockerfile
# Secret mount example (secret never appears in any layer)
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci

# SSH mount for private git repos
RUN --mount=type=ssh git clone git@github.com:private/repo.git
```

### Docker Compose for Development

```yaml
services:
  app:
    build: { context: ., target: development }
    volumes: [".:/app", "/app/node_modules"]
    ports: ["3000:3000"]
    depends_on:
      db: { condition: service_healthy }
  db:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
volumes:
  pgdata:
```

---

## Kubernetes Core Concepts

### Pods

The smallest deployable unit. One or more containers sharing network namespace (same IP, localhost communication) and storage volumes. Multi-container patterns: **sidecar** (proxy, log shipper), **init container** (pre-start setup), **adapter** (output transformation).

### Deployments and ReplicaSets

A Deployment declares desired state and creates a ReplicaSet that maintains the target replica count.

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
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
  template:
    metadata:
      labels: { app: api-server }
    spec:
      containers:
        - name: api
          image: myregistry/api-server:v2.1.0
          ports: [{ containerPort: 8080 }]
          resources:
            requests: { cpu: 250m, memory: 256Mi }
            limits: { cpu: 500m, memory: 512Mi }
          readinessProbe:
            httpGet: { path: /readyz, port: 8080 }
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet: { path: /healthz, port: 8080 }
            initialDelaySeconds: 15
            periodSeconds: 20
```

### Services

| Type | Behavior |
|---|---|
| ClusterIP | Internal-only. Other pods reach via `svc.namespace.svc.cluster.local` |
| NodePort | Exposes on every node (port 30000-32767). Rarely used in production |
| LoadBalancer | Provisions cloud LB. Each service gets its own external IP |
| ExternalName | CNAME to an external DNS name |

### ConfigMaps and Secrets

ConfigMaps store non-sensitive configuration; Secrets store sensitive data (base64-encoded, **not encrypted by default**). For production, use External Secrets Operator syncing from HashiCorp Vault or AWS Secrets Manager.

### Namespaces

Logical isolation for teams, environments, or applications. Enable RBAC scoping, ResourceQuotas, and NetworkPolicy boundaries.

**Default namespaces:**
- `default`: Where resources go if no namespace is specified.
- `kube-system`: Kubernetes system components (CoreDNS, kube-proxy).
- `kube-public`: Publicly accessible data (rarely used).

**Best practice:** Never deploy application workloads in `default`. Use descriptive namespace names (`production`, `team-payments`).

---

## Networking in Kubernetes

### Service Discovery and DNS

CoreDNS gives every Service a DNS entry: `<service>.<namespace>.svc.cluster.local`. Pods use short names within the same namespace (`api-server`) or FQDNs across namespaces.

### Ingress Controllers

Ingress resources define external access rules. A controller (nginx, Traefik, Istio Gateway, Contour) implements them.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
spec:
  ingressClassName: nginx
  tls:
    - hosts: [api.example.com]
      secretName: api-tls-cert
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /api/v1
            pathType: Prefix
            backend:
              service: { name: api-v1, port: { number: 80 } }
          - path: /api/v2
            pathType: Prefix
            backend:
              service: { name: api-v2, port: { number: 80 } }
```

### NetworkPolicies

By default, all pods can talk to all other pods. NetworkPolicies restrict traffic. Requires a supporting CNI (Calico, Cilium).

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
spec:
  podSelector:
    matchLabels: { app: api-server }
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - podSelector: { matchLabels: { app: frontend } }
      ports: [{ port: 8080 }]
  egress:
    - to:
        - podSelector: { matchLabels: { app: database } }
      ports: [{ port: 5432 }]
```

---

## Storage

**PersistentVolumeClaim:** A pod's request for storage, bound to a PersistentVolume.

**Access modes:** `ReadWriteOnce` (single node), `ReadOnlyMany` (multi-node read), `ReadWriteMany` (multi-node write -- NFS, EFS, CephFS).

### StatefulSets

For workloads needing stable identity and per-pod persistent storage. Pods get stable hostnames (`postgres-0`, `postgres-1`), ordered creation/deletion, and individual PVCs.

**Use StatefulSets** for databases, message brokers, consensus systems. **Use Deployments** for everything else.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 3
  selector:
    matchLabels: { app: postgres }
  template:
    metadata:
      labels: { app: postgres }
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: gp3
        resources:
          requests:
            storage: 100Gi
```

**Key property:** Each pod gets its own PVC (`data-postgres-0`, `data-postgres-1`) that persists across pod rescheduling. StorageClasses define the provisioner and parameters (e.g., `gp3` for AWS EBS).

---

## Scaling

### Horizontal Pod Autoscaler (HPA)

Scales replica count on CPU, memory, or custom metrics (from Prometheus via adapter).

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api-server }
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
```

### Vertical Pod Autoscaler (VPA)

Adjusts CPU/memory requests based on actual usage. Modes: `Off` (recommend only), `Auto` (apply by evicting pods), `Initial` (new pods only). **Do not** use VPA and HPA on the same metric.

### Cluster Autoscaler

Adds nodes when pods are pending (insufficient resources). Removes nodes when utilization is below threshold and pods can be rescheduled. Integrates with cloud provider APIs.

### KEDA (Event-Driven Autoscaling)

Scales on external event sources (queue depth, stream lag, cron). Key advantage: **scale-to-zero** when idle, unlike HPA (minimum 1 replica).

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-processor
spec:
  scaleTargetRef:
    name: order-processor
  minReplicaCount: 0        # Scale to zero when idle
  maxReplicaCount: 100
  triggers:
    - type: rabbitmq
      metadata:
        queueName: orders
        host: amqp://rabbitmq.default.svc.cluster.local
        queueLength: "50"   # Scale up when queue > 50 messages
```

---

## Deployment Strategies

### Rolling Updates

Default strategy. Gradually replaces old pods. Set `maxUnavailable: 0` for zero-downtime.

### Blue-Green

Run two environments (blue = current, green = new). Switch traffic atomically by updating the Service selector. Instant rollback. Requires 2x resources during transition.

### Canary with Istio/Flagger

Route a small percentage of traffic to the new version, monitor metrics, gradually increase.

```yaml
# Istio VirtualService: 95/5 traffic split
http:
  - route:
      - destination: { host: api-server, subset: stable }
        weight: 95
      - destination: { host: api-server, subset: canary }
        weight: 5
```

**Flagger** automates this: increases traffic, monitors error rates, promotes or rolls back automatically.

### Rollback

```bash
kubectl rollout undo deployment/api-server                  # Previous version
kubectl rollout undo deployment/api-server --to-revision=3  # Specific revision
```

---

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

## Resource Management

### Requests vs Limits

**Requests:** Guaranteed minimum resources for a pod. The scheduler uses requests to find a node with sufficient capacity.

**Limits:** Maximum resources a pod can use. Exceeding CPU limits causes **throttling** (latency spikes, not OOM). Exceeding memory limits causes **OOM kill** (process terminated).

```yaml
resources:
  requests:
    cpu: 250m       # 0.25 CPU cores guaranteed
    memory: 256Mi   # 256 MiB guaranteed
  limits:
    cpu: 500m       # Throttled above 0.5 cores
    memory: 512Mi   # OOM killed above 512 MiB
```

**Best practice:** Always set requests for scheduling accuracy. Always set memory limits to prevent runaway processes. Consider omitting CPU limits to avoid throttling-induced latency spikes -- rely on requests for fair scheduling instead.

### QoS Classes

| Class | Condition | Eviction Priority |
|---|---|---|
| Guaranteed | requests == limits | Last evicted |
| Burstable | requests < limits | Middle |
| BestEffort | None set | First evicted |

### LimitRanges and ResourceQuotas

**LimitRange:** Sets default and max/min resource constraints per container in a namespace. Ensures every container has at least some resource configuration.

**ResourceQuota:** Limits total resource consumption in a namespace. Prevents one team or application from consuming the entire cluster.

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: production-quota
  namespace: production
spec:
  hard:
    requests.cpu: "100"
    requests.memory: 200Gi
    limits.cpu: "200"
    limits.memory: 400Gi
    pods: "500"
```

---

## Debugging

### Essential Debugging Commands

```bash
kubectl describe pod <name>                              # Events and status
kubectl logs <pod> -c <container> --previous             # Previous crash logs
kubectl exec -it <pod> -- /bin/sh                        # Shell into container
kubectl debug -it <pod> --image=busybox --target=<ctr>   # Ephemeral debug container
kubectl top pods                                         # Resource usage
```

### Common Failures

| Symptom | Cause | Fix |
|---|---|---|
| `CrashLoopBackOff` | App crash on startup | `kubectl logs --previous`, check startup probe |
| `ImagePullBackOff` | Wrong image/tag, auth failure | Check image name, pull secrets |
| `Pending` | Insufficient resources | Check node resources, add nodes |
| `OOMKilled` | Memory limit exceeded | Increase limit or fix memory leak |
| `Evicted` | Node under memory/disk pressure | Check node conditions, add capacity |
| `CreateContainerConfigError` | Missing ConfigMap/Secret | Verify resource exists in namespace |

### Log Aggregation

For production, ship logs to a centralized system:

- **Loki + Grafana:** Lightweight, label-based. Lower storage cost than Elasticsearch.
- **EFK stack:** Elasticsearch + Fluent Bit + Kibana. Full-text search.
- **Cloud-native:** CloudWatch Logs, GCP Cloud Logging, Azure Monitor.

**Fluent Bit** is preferred over Fluentd for Kubernetes due to lower resource consumption.

---

## Interview Questions

**Q: Deployment vs StatefulSet -- when each?**
A: Deployments for stateless services (interchangeable pods). StatefulSets for workloads needing stable identity and per-pod persistent storage (databases, Kafka). Most services should be Deployments.

**Q: Pod in CrashLoopBackOff -- your debugging process?**
A: `kubectl describe pod` for events (OOMKilled, config errors). `kubectl logs --previous` for crash output. Check probe configuration (too aggressive?). Verify ConfigMaps/Secrets exist. Check resource limits. Use `kubectl debug` for distroless containers.

**Q: Zero-downtime database migration in Kubernetes?**
A: Expand-and-contract pattern. Phase 1: add new columns without removing old ones, deploy app writing to both. Phase 2: backfill. Phase 3: deploy version using only new schema, then drop old columns later. Use init containers or Jobs for migrations.

**Q: Design deployment strategy for a critical payment service.**
A: Rolling update with `maxUnavailable: 0`. PodDisruptionBudget (`minAvailable: 2`). Guaranteed QoS. Anti-affinity across AZs. Canary with Flagger monitoring payment success rate. HPA on custom metrics. Blue-green for major version changes.

**Q: How do you right-size resources for a new service?**
A: Start generous. Use VPA in recommendation mode over several days including peaks. Set requests to P95 usage, memory limits to 2x requests. Consider no CPU limits (throttling causes latency spikes). Monitor and iterate.

### Rapid-Fire

1. **PodDisruptionBudget?** Limits voluntary disruptions by ensuring minimum available pods during drains/upgrades.
2. **Liveness vs readiness?** Liveness: is the process stuck (restart). Readiness: can it serve traffic (remove from endpoints).
3. **DaemonSet?** One pod per node -- for node-level agents (log collectors, monitoring, CNI).
4. **HPA vs KEDA?** HPA scales on metrics (min 1 replica). KEDA scales on external events and supports scale-to-zero.
5. **Sidecar pattern?** Helper container in the same pod (Envoy proxy, log shipper).
6. **Kustomize?** Template-free manifest customization using overlays. Built into kubectl.
