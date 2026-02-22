# Module 07: Deep Dive — Production Go

## Advanced Docker Optimization

### UPX Binary Compression

UPX compresses Go binaries by 50-70%, at the cost of slightly slower startup (decompression at launch). Whether this tradeoff is worth it depends on your deployment model.

```dockerfile
FROM golang:1.23-alpine AS builder
RUN apk add --no-cache upx

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /server ./cmd/server
RUN upx --best --lzma /server

# Result: ~5MB instead of ~15MB
FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

**When to use UPX:**
- CLI tools distributed to users (download size matters)
- Lambda/serverless functions (cold start includes download)

**When to skip UPX:**
- Long-running services (startup cost is amortized)
- When you need to use `dlv` or `pprof` (UPX strips debug info)
- Security scanning tools may flag UPX-compressed binaries

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

Build and push multi-arch images:

```bash
docker buildx create --name multiarch --use
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/yourorg/myservice:latest \
  --push .
```

### Cache Mounts for Faster CI Builds

Docker BuildKit cache mounts persist the Go module cache and build cache across builds:

```dockerfile
# syntax=docker/dockerfile:1
FROM golang:1.23-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./

RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -ldflags="-s -w" -o /server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=builder /server /server
ENTRYPOINT ["/server"]
```

This is dramatically faster in CI — the Go module cache and compilation cache survive between builds. On a large project, this can cut build times from 3 minutes to 30 seconds.

---

## Kubernetes Deployment for Go Services

### Deployment Manifest

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

### Key Kubernetes Considerations for Go

**`terminationGracePeriodSeconds`:** Must be longer than your application's shutdown timeout. Kubernetes sends SIGTERM, then waits this long before SIGKILL. Your app's `ShutdownTimeout` should be less than this value.

**`GOMAXPROCS` in containers:** By default, Go's runtime sees all host CPUs, not the container's CPU limit. If your container has `limits.cpu: "1"` but the node has 64 CPUs, Go will create 64 OS threads. Use the `uber-go/automaxprocs` library:

```go
import _ "go.uber.org/automaxprocs"

// Automatically sets GOMAXPROCS to match container CPU quota
// Or set via environment variable in the manifest
```

**`GOMEMLIMIT` (Go 1.19+):** Tells the Go garbage collector about your memory budget. Set it to ~90% of your container's memory limit to avoid OOM kills. Without this, Go's GC might not collect aggressively enough and exceed the container limit.

```go
// Automatically set from container cgroup limits
import _ "github.com/KimMachineGun/automemlimit"
```

---

## Helm Chart for Go Service

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

## Profiling in Production

### pprof Endpoints

Go has built-in profiling. Exposing it on a separate port so it is not publicly accessible is critical:

```go
import (
    "net/http"
    _ "net/http/pprof"  // Registers /debug/pprof/* handlers
)

func startDebugServer() {
    // Separate port — not exposed via ingress
    debugMux := http.DefaultServeMux
    go http.ListenAndServe(":6060", debugMux)
}
```

Access profiles remotely:

```bash
# CPU profile (30 seconds)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Heap profile
go tool pprof http://localhost:6060/debug/pprof/heap

# Goroutine dump (find leaks)
go tool pprof http://localhost:6060/debug/pprof/goroutine

# Via kubectl port-forward for production pods
kubectl port-forward pod/myservice-abc123 6060:6060
go tool pprof http://localhost:6060/debug/pprof/heap
```

### Continuous Profiling with Pyroscope

Pyroscope provides always-on profiling with minimal overhead (~2% CPU):

```go
package main

import (
    "os"
    "runtime"

    "github.com/grafana/pyroscope-go"
)

func initProfiling() {
    runtime.SetMutexProfileFraction(5)
    runtime.SetBlockProfileRate(5)

    pyroscope.Start(pyroscope.Config{
        ApplicationName: "myservice",
        ServerAddress:   os.Getenv("PYROSCOPE_SERVER"),
        Logger:          pyroscope.StandardLogger,
        Tags: map[string]string{
            "env":     os.Getenv("ENV"),
            "version": version.Version,
        },
        ProfileTypes: []pyroscope.ProfileType{
            pyroscope.ProfileCPU,
            pyroscope.ProfileAllocObjects,
            pyroscope.ProfileAllocSpace,
            pyroscope.ProfileInuseObjects,
            pyroscope.ProfileInuseSpace,
            pyroscope.ProfileGoroutines,
            pyroscope.ProfileMutexCount,
            pyroscope.ProfileMutexDuration,
            pyroscope.ProfileBlockCount,
            pyroscope.ProfileBlockDuration,
        },
    })
}
```

### Flame Graphs

The `go tool pprof` command generates flame graphs natively:

```bash
# Interactive web UI with flame graph
go tool pprof -http=:8081 http://localhost:6060/debug/pprof/profile?seconds=30

# Generate SVG flame graph
go tool pprof -svg http://localhost:6060/debug/pprof/heap > heap.svg
```

**TypeScript parallel:** This is like connecting Node's `--inspect` to Chrome DevTools, but built into the language. The overhead is low enough to leave pprof endpoints enabled in production (on a non-public port).

---

## Binary Distribution

### Cross-Compilation

Go's cross-compilation is trivial — no toolchain installation required:

```bash
# Build for all major platforms
GOOS=linux   GOARCH=amd64 go build -o dist/myservice-linux-amd64   ./cmd/server
GOOS=linux   GOARCH=arm64 go build -o dist/myservice-linux-arm64   ./cmd/server
GOOS=darwin  GOARCH=amd64 go build -o dist/myservice-darwin-amd64  ./cmd/server
GOOS=darwin  GOARCH=arm64 go build -o dist/myservice-darwin-arm64  ./cmd/server
GOOS=windows GOARCH=amd64 go build -o dist/myservice-windows-amd64.exe ./cmd/server
```

**TypeScript parallel:** Imagine if `npm run build` could target every OS and architecture with a single flag, no pkg/nexe/vercel-ncc required.

### Static Linking

With `CGO_ENABLED=0`, Go produces fully static binaries. If you need CGo (for SQLite, for example), you can still statically link:

```bash
# Static linking with CGo (requires musl on Linux)
CGO_ENABLED=1 CC=musl-gcc go build -ldflags="-linkmode external -extldflags '-static'" \
    -o myservice ./cmd/server
```

### Embedding Assets

Go 1.16's `embed` package lets you bundle static files into the binary:

```go
package main

import (
    "embed"
    "io/fs"
    "net/http"
)

//go:embed static/*
var staticFiles embed.FS

//go:embed templates/*
var templateFiles embed.FS

//go:embed migrations/*.sql
var migrationFiles embed.FS

func main() {
    // Serve embedded static files
    staticFS, _ := fs.Sub(staticFiles, "static")
    http.Handle("/static/", http.StripPrefix("/static/",
        http.FileServer(http.FS(staticFS))))

    // Use embedded templates
    tmpl, _ := template.ParseFS(templateFiles, "templates/*.html")

    // Use embedded migrations
    // goose.SetBaseFS(migrationFiles)
}
```

This is one of Go's most powerful production features. Your entire application — binary, templates, static assets, database migrations — is a single file. No more managing asset directories in Docker images or dealing with path resolution issues.

**TypeScript parallel:** Similar to Webpack/Vite bundling assets, but at the language level with zero configuration. The embedded files are immutable and available at compile time.

---

## Resource Tuning Summary

| Setting | Default | Container Recommendation | Why |
|---------|---------|-------------------------|-----|
| `GOMAXPROCS` | Host CPU count | Container CPU limit | Prevents excessive thread creation |
| `GOMEMLIMIT` | No limit | 90% of memory limit | Prevents OOM kills |
| `GOGC` | 100 | 50-200 depending on workload | Lower = more frequent GC, lower memory |
| Goroutine stack | 8KB initial | Usually fine | Grows automatically |
| `http.Server.ReadTimeout` | None | 5-30s | Prevents slow loris attacks |
| `http.Server.WriteTimeout` | None | 10-60s | Prevents hung connections |
| `http.Server.IdleTimeout` | None | 60-120s | Frees idle keep-alive connections |
| `sql.DB.MaxOpenConns` | Unlimited | 25-50 | Prevents database connection exhaustion |
| `sql.DB.MaxIdleConns` | 2 | Match MaxOpenConns | Prevents connection churn |
| `sql.DB.ConnMaxLifetime` | Unlimited | 5-30 min | Handles database failovers |
