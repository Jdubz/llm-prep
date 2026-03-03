# 03 – Deployment and Scaling

This file assumes you have read `01-project-structure-and-configuration.md` and `02-observability-and-health.md`. It covers Docker builds, Kubernetes deployment, runtime tuning, and interview questions.

---

## 1. Docker Builds

### Standard Multi-Stage Dockerfile

```dockerfile
# Stage 1: Build
FROM golang:1.23-alpine AS builder

WORKDIR /app

# Cache dependencies (copy go.mod/go.sum before source)
COPY go.mod go.sum ./
RUN go mod download

# Build the binary
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /server ./cmd/server

# Stage 2: Runtime
FROM gcr.io/distroless/static-debian12

COPY --from=builder /server /server

EXPOSE 8080
ENTRYPOINT ["/server"]
```

### Optimized Dockerfile (with version injection and build caches)

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.23-alpine AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build \
    -ldflags="-s -w \
      -X github.com/yourorg/myservice/internal/version.Version=${VERSION:-dev} \
      -X github.com/yourorg/myservice/internal/version.Commit=${COMMIT:-unknown}" \
    -trimpath -o /server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

BuildKit cache mounts persist the Go module cache and build cache across builds — cutting CI build times from 3 minutes to 30 seconds on large projects.

### Key Build Flags

| Flag | Purpose |
|------|---------|
| `CGO_ENABLED=0` | Disable C interop for a fully static binary |
| `GOOS=linux` | Target Linux (even from a macOS build) |
| `-ldflags="-s -w"` | Strip debug info and symbol table (~30% smaller binary) |
| `-trimpath` | Remove local filesystem paths from binary |

### Why Distroless Over Scratch

`scratch` is an empty image — literally nothing. `distroless` includes CA certificates (for HTTPS), timezone data, and a `nonroot` user. With `scratch`, you must manually copy these from the builder.

### Layer Caching Strategy

Copy `go.mod`/`go.sum` first, run `go mod download`, then copy source. Docker caches the dependency layer until `go.mod` changes. Same principle as copying `package.json` before `npm ci` in Node builds.

### UPX Binary Compression

UPX compresses Go binaries by 50–70%, at the cost of slightly slower startup:

```dockerfile
FROM golang:1.23-alpine AS builder
RUN apk add --no-cache upx

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /server ./cmd/server
RUN upx --best --lzma /server   # ~5MB instead of ~15MB

FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

When to use UPX: CLI tools distributed to users (download size matters), serverless functions (cold start includes download).
When to skip UPX: long-running services (startup cost amortized), when you need `dlv` or `pprof` (UPX strips debug info), security scanning tools may flag UPX-compressed binaries.

### Multi-Architecture Builds

Building for both `amd64` and `arm64` (Apple Silicon, Graviton):

```dockerfile
# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM golang:1.23-alpine AS builder

ARG TARGETOS
ARG TARGETARCH

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} \
    go build -ldflags="-s -w" -o /server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

```bash
docker buildx create --name multiarch --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/yourorg/myservice:latest \
  --push .
```

---

## 2. Kubernetes Deployment

### Full Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myservice
  labels:
    app: myservice
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myservice
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    metadata:
      labels:
        app: myservice
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8080"
        prometheus.io/path: "/metrics"
    spec:
      terminationGracePeriodSeconds: 60
      containers:
      - name: myservice
        image: ghcr.io/yourorg/myservice:1.2.3
        ports:
        - name: http
          containerPort: 8080
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: myservice-secrets
              key: database-url
        - name: LOG_LEVEL
          value: "info"
        - name: GOMAXPROCS
          valueFrom:
            resourceFieldRef:
              resource: limits.cpu
        - name: GOMEMLIMIT
          value: "900MiB"
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: "1"
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /healthz
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
        startupProbe:
          httpGet:
            path: /healthz
            port: http
          failureThreshold: 30
          periodSeconds: 2
---
apiVersion: v1
kind: Service
metadata:
  name: myservice
spec:
  selector:
    app: myservice
  ports:
  - name: http
    port: 80
    targetPort: http
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: myservice
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: myservice
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
```

### Helm Chart Essentials

```yaml
# Chart.yaml
apiVersion: v2
name: myservice
description: A Go microservice
version: 0.1.0
appVersion: "1.2.3"
```

```yaml
# values.yaml
replicaCount: 3

image:
  repository: ghcr.io/yourorg/myservice
  tag: "1.2.3"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8080

resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: "1"
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilization: 70

env:
  LOG_LEVEL: info
  GOMEMLIMIT: 900MiB

secrets:
  - name: DATABASE_URL
    secretName: myservice-secrets
    secretKey: database-url
```

---

## 3. Runtime Tuning for Containers

### Key Kubernetes Considerations

**`terminationGracePeriodSeconds`:** Must be longer than your application's shutdown timeout. Kubernetes sends SIGTERM, then waits this long before SIGKILL. Your app's `ShutdownTimeout` must be less than this value. Set to 60s with a 30s `ShutdownTimeout`.

**`GOMAXPROCS` in containers:** By default, Go's runtime sees all host CPUs, not the container's CPU limit. If your container has `limits.cpu: "1"` but the node has 64 CPUs, Go will create 64 OS threads. Use the `uber-go/automaxprocs` library or set the environment variable from `resourceFieldRef`:

```go
import _ "go.uber.org/automaxprocs"
// Automatically sets GOMAXPROCS to match container CPU quota
```

**`GOMEMLIMIT` (Go 1.19+):** Tells the Go garbage collector about your memory budget. Set to ~90% of your container's memory limit to avoid OOM kills. Without this, Go's GC might not collect aggressively enough.

```go
import _ "github.com/KimMachineGun/automemlimit"
// Automatically set from container cgroup limits
```

### Resource Tuning Summary

| Setting | Default | Container Recommendation | Why |
|---------|---------|-------------------------|-----|
| `GOMAXPROCS` | Host CPU count | Container CPU limit | Prevents excessive thread creation |
| `GOMEMLIMIT` | No limit | 90% of memory limit | Prevents OOM kills |
| `GOGC` | 100 | 50–200 per workload | Lower = more frequent GC, lower memory |
| `http.Server.ReadTimeout` | None | 5–30s | Prevents slow loris attacks |
| `http.Server.WriteTimeout` | None | 10–60s | Prevents hung connections |
| `http.Server.IdleTimeout` | None | 60–120s | Frees idle keep-alive connections |
| `sql.DB.MaxOpenConns` | Unlimited | 25–50 | Prevents DB connection exhaustion |
| `sql.DB.MaxIdleConns` | 2 | Match MaxOpenConns | Prevents connection churn |
| `sql.DB.ConnMaxLifetime` | Unlimited | 5–30 min | Handles database failovers |

### Static Linking

With `CGO_ENABLED=0`, Go produces fully static binaries. If you need CGo (e.g., for SQLite), you can still statically link:

```bash
CGO_ENABLED=1 CC=musl-gcc go build -ldflags="-linkmode external -extldflags '-static'" \
    -o myservice ./cmd/server
```

---

## 4. Interview Questions

**Q: How would you structure a Go project with multiple services?**
Monorepo with `cmd/` subdirectories per service, `internal/` for service-specific code, shared packages at root or in `pkg/`. Each `cmd/` entry point is thin — it wires dependencies and delegates to `internal/`. Single `go.mod` or Go workspaces for multi-module repos depending on release cadence.

**Q: Walk me through your Docker build strategy for a Go service.**
Multi-stage build. Builder stage copies `go.mod`/`go.sum` first for layer caching, builds with `CGO_ENABLED=0 -ldflags='-s -w' -trimpath`. Runtime stage uses `distroless/static` for 10–20MB final images. Version info injected via ldflags. BuildKit cache mounts for fast CI builds.

**Q: How do you implement graceful shutdown in a Go service?**
`signal.NotifyContext` creates a context cancelling on SIGTERM/SIGINT. On cancellation: `srv.Shutdown(ctx)` drains HTTP and waits for in-flight requests, then cancel worker contexts, flush metrics/traces, close database. Order matters — do not close the DB before in-flight requests finish.

**Q: How do you handle configuration in a Go service?**
12-factor model. Env vars are primary. A `Config` struct with a `Load()` function that validates all values at startup. Required values fail fast with clear error messages. Config struct created once in `main` and passed as an explicit dependency — never a global variable.

**Q: What is the difference between `internal/` and `pkg/` directories?**
`internal/` is compiler-enforced: code under it can only be imported by the parent module. `pkg/` is a convention signaling public API — not enforced by the compiler. For most services, use `internal/` aggressively and skip `pkg/`.

**Q: How do you approach observability in a Go service?**
Three pillars. Structured logging with `slog` (JSON in production, text in development). Metrics with Prometheus client — counters for request totals, histograms for latency, exposed on `/metrics`. Distributed tracing with OpenTelemetry SDK, exporting to Jaeger or Tempo. All tied together through request IDs propagated via context. Logging and metrics are HTTP middleware so every request is instrumented automatically.

**Q: How do liveness and readiness probes differ?**
Liveness: "is the process stuck?" — failure triggers a pod restart, keep it simple and return 200 unless the process is truly broken. Readiness: "can it serve traffic?" — failure removes the pod from the load balancer, checks downstream dependencies (DB, cache) with short timeouts (2s). Startup probes handle slow initialization by giving more time before liveness kicks in.

**Q: Why set GOMAXPROCS and GOMEMLIMIT in Kubernetes?**
Without `GOMAXPROCS`, Go's runtime sees all host CPUs and creates that many OS threads, causing excessive context switching. Use `automaxprocs` or set it from the container CPU limit. Without `GOMEMLIMIT`, Go's GC does not know the memory budget and may not collect aggressively enough, causing OOM kills. Set it to ~90% of the container memory limit.

**Q: What makes Go binaries well-suited for container deployments?**
Go compiles to a single statically linked binary with no runtime dependency. The result can run in a `FROM scratch` or `distroless` container with no OS packages. Multi-stage builds produce tiny images (5–20MB). Cross-compilation to any target platform with a single env variable. Embed migrations, templates, and static assets directly in the binary.

**Q: How do you distinguish operational errors from programmer errors?**
Operational errors are expected (timeouts, validation, not-found) — use sentinel errors and handle explicitly with `errors.Is`/`errors.As`. Programmer errors are bugs (nil pointer, index out of bounds) — these panic, which is intentional in Go. Wrap operational errors with `%w` so callers make decisions based on error type, not string matching.

---

## Related Reading

- **Concurrency and GOMAXPROCS** — [Module 02: Advanced Concurrency Patterns](../02-concurrency/03-advanced-concurrency-patterns.md), section 1 (The GMP Scheduler Model) explains the goroutine scheduling that `GOMAXPROCS` from section 3 controls
- **HTTP services being deployed** — [Module 04: Advanced HTTP Patterns](../04-http-services/03-advanced-http-patterns.md), section 1 (Graceful Shutdown) covers the HTTP-level shutdown that coordinates with the Kubernetes lifecycle in section 2
- **Testing in CI** — [Module 06: Integration and HTTP Testing](../06-testing/02-integration-and-http-testing.md), section 6 (CI Integration) shows the test coverage thresholds and CI scripting that complement the Docker and Kubernetes deployment from sections 1–2
- **GC tuning internals** — [Module 01: Advanced Go Internals](../01-go-mental-model/03-advanced-go-internals.md), section 3 (Garbage Collector) provides the deep background on tri-color mark-and-sweep and `GOGC` that section 3 (Runtime Tuning) configures for production
- **Build and release** — [Project Structure and Configuration](01-project-structure-and-configuration.md), section 4 (Makefile) and section 5 (Version Injection) cover the build tooling that produces the binaries containerized in section 1

---

## Practice Suggestions

These exercises reinforce the production Go concepts from this module (Project Structure and Configuration through Deployment and Scaling):

1. **Production project scaffold** — Create a new Go project with the full `cmd/`/`internal/` layout. Include a `cmd/server/main.go` that loads config from environment variables, wires dependencies, and starts an HTTP server with graceful shutdown. Add a `Makefile` with `build`, `test`, `lint`, and `docker` targets.

2. **Multi-stage Docker build** — Write a `Dockerfile` with a builder stage that uses `CGO_ENABLED=0`, `-ldflags='-s -w'`, and `-trimpath`. The runtime stage should use `gcr.io/distroless/static`. Inject version info via `ldflags` and verify the binary reports the correct version at `/healthz`.

3. **Observability stack** — Add structured logging (`slog` with JSON handler), Prometheus metrics (request count, latency histogram), and a health check endpoint to an existing HTTP service. Write a test that verifies the `/metrics` endpoint exposes the expected metric names.

4. **Graceful shutdown test** — Build an HTTP server that simulates long-running requests. Implement ordered graceful shutdown (stop accepting new connections, drain in-flight, close database, flush telemetry). Write a test that sends a request, triggers SIGTERM, and verifies the request completes within the shutdown timeout.

5. **Kubernetes manifest** — Write a Deployment manifest with liveness, readiness, and startup probes pointed at your health check endpoints. Set resource requests/limits and add `GOMAXPROCS` and `GOMEMLIMIT` as environment variables calculated from the container limits. Test locally with `kind` or `minikube`.

6. **Configuration validation** — Build a `Config` struct that loads from environment variables, validates all fields at startup (port range, required fields, URL format), and returns all errors at once using `errors.Join`. Write table-driven tests that verify every validation rule including the error messages.
