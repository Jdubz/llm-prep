# Module 06: Docker and Containerization

## Overview

Containers and Kubernetes are the default deployment platform for modern distributed systems. Senior interviews demand you reason about image optimization, security, resource management, scaling strategies, and deployment patterns -- not just write a Dockerfile.

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

From the host, containers are just regular processes with restricted resource views. There is no container hypervisor, no hardware virtualization. Isolation is a kernel-level resource partitioning mechanism.

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

### Dockerfile Best Practices Checklist

- Multi-stage builds (separate build/runtime)
- Pin base image versions (`node:20.11-alpine`, not `latest`)
- Order: least to most frequently changing layers
- `npm ci` not `npm install`; `--mount=type=cache` for caches
- Non-root user (`USER appuser`)
- Distroless or alpine for production
- Never `COPY` secrets; use `--mount=type=secret`
- Scan with Trivy/Snyk in CI; fail on CRITICAL

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

## Related Reading

- [Module 06: Kubernetes Core and Operations](02-kubernetes-core-and-operations.md) -- Kubernetes orchestrates the containers you build with Docker, managing scheduling, scaling, networking, and storage
- [Module 06: Kubernetes Advanced Patterns](03-kubernetes-advanced-patterns.md) -- Helm charts, GitOps with ArgoCD, and service mesh patterns for containerized services
- [Module 07: Pipeline Design and Deployment Strategies](../07-cicd/01-pipeline-design-and-deployment-strategies.md) -- CI/CD pipelines build and push container images; multi-stage Docker builds integrate into the pipeline's build stage
- [Module 07: Infrastructure and GitOps](../07-cicd/03-infrastructure-and-gitops.md) -- devcontainers for development environments and Tilt/Skaffold for inner-loop Kubernetes development
- [Module 08: Logging, Metrics, and Tracing](../08-observability/01-logging-metrics-and-tracing.md) -- structured logging from containers, correlation IDs propagated through containerized services
- [Module 09: API and Application Security](../09-security/02-api-and-application-security.md) -- container security scanning (Trivy, Snyk), distroless base images, and image signing for supply chain security
