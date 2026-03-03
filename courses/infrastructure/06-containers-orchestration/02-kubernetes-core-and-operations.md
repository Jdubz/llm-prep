# Module 06: Kubernetes Core and Operations

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

### Resource Sizing Guide

| Workload | CPU Request | Mem Request | Mem Limit |
|---|---|---|---|
| Light API (Node/Go) | 100-250m | 128-256Mi | 512Mi |
| Heavy API (Java) | 500-1000m | 512Mi-1Gi | 2Gi |
| Worker | 250-500m | 256-512Mi | 1Gi |
| Database | 1-4 cores | 2-8Gi | 8-16Gi |
| Cache (Redis) | 250-500m | 1-4Gi | = request |

**Process:** Deploy generous -> load test -> VPA recommend mode (3-7 days) -> set requests=P95, memory limit=2x request -> consider no CPU limit -> iterate.

---

## Debugging

### Essential Debugging Commands

```bash
# Viewing
kubectl get pods -n production -o wide
kubectl get events --sort-by=.lastTimestamp
kubectl top pods -n production

# Inspecting
kubectl describe pod <name>
kubectl logs <pod> -c <container> --previous
kubectl get pod <name> -o yaml

# Debugging
kubectl exec -it <pod> -- /bin/sh
kubectl debug -it <pod> --image=busybox
kubectl port-forward svc/api-server 8080:80
kubectl run tmp --image=busybox --rm -it -- sh

# Rollouts
kubectl rollout status deployment/api-server
kubectl rollout undo deployment/api-server
kubectl rollout undo deployment/api-server --to-revision=3
kubectl rollout restart deployment/api-server
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

### Debugging Checklist

**Pod not starting:**
`describe pod` -> ImagePullBackOff (wrong image)? Pending (no capacity)? ConfigError (missing Secret)?

**Pod crashing:**
`logs --previous` -> OOMKilled (increase limit)? Probe too aggressive? Missing dependency?

**Service unreachable:**
`get endpoints` -> no endpoints (label mismatch)? Pod not ready (probe failing)? NetworkPolicy blocking? Port mismatch (`targetPort` != `containerPort`)?

**Performance:**
`top pods` -> CPU throttled? OOMKilled? Slow DNS (check CoreDNS, `ndots`)? HPA not scaling (check metrics-server)?

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
