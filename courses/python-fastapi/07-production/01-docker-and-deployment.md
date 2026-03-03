# 01 – Docker and Deployment

## The TypeScript Mental Model

In Node.js, you typically:
1. Install deps (`npm ci`)
2. Build (`tsc` or bundler)
3. Copy built JS to a slim runtime image

Python is different: there's no "build" step for most projects (no transpilation), but you still need a compilation step for **C-extension wheels** (numpy, psycopg2, etc.). Multi-stage builds solve this.

---

## Package Managers: pip vs poetry vs uv

```dockerfile
# === OPTION 1: pip + requirements.txt (simplest) ===
FROM python:3.12-slim AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /install /usr/local
COPY . /app
```

```dockerfile
# === OPTION 2: poetry (common in larger projects) ===
FROM python:3.12-slim AS builder
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
# Export to requirements.txt — avoid installing poetry in production
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /install /usr/local
COPY . /app
```

```dockerfile
# === OPTION 3: uv (fastest, modern — recommended) ===
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

**Why uv is winning**: `uv` is written in Rust (by the Astral team who built `ruff`). It resolves and installs packages 10-100x faster than pip. Think of it as the `pnpm` of Python — fast, deterministic, and increasingly the default.

### uv Performance Comparison

| Operation | pip | poetry | uv |
|-----------|-----|--------|----|
| Cold install (large project) | ~60s | ~45s | ~2s |
| Resolve dependencies | ~15s | ~10s | ~0.5s |
| Lock file generation | N/A | ~10s | ~1s |
| Written in | Python | Python | Rust |

---

## Base Image: slim vs alpine

| Image | Size | Gotchas |
|-------|------|---------|
| `python:3.12` | ~1 GB | Full Debian — unnecessary for production |
| `python:3.12-slim` | ~120 MB | Stripped Debian — **recommended for most cases** |
| `python:3.12-alpine` | ~50 MB | musl libc — breaks many wheels, slow builds for C extensions |

**The alpine trap**: In Node.js, alpine images are a safe default. In Python, alpine uses `musl` instead of `glibc`, which means pre-built binary wheels (manylinux) won't work. You end up compiling from source, which is slower and requires installing build tools. Use `slim` unless you have a specific reason for alpine.

---

## Production Dockerfile (Full Template)

```dockerfile
# ---- Build Stage ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first (layer caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

# Application code
COPY . .

# ---- Runtime Stage ----
FROM python:3.12-slim

RUN groupadd -r app && useradd -r -g app app

WORKDIR /app
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER app
EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
```

The key insight is the same as Node.js: copy dependency files first, install, then copy source code. This maximizes layer caching — rebuilding only when the lock file changes.

### .dockerignore

```
__pycache__
*.pyc
*.pyo
.git
.venv
.env
.mypy_cache
.pytest_cache
.ruff_cache
htmlcov
dist
*.egg-info
node_modules
.DS_Store
```

---

## Uvicorn/Gunicorn Configuration

### The Relationship

**Uvicorn** = ASGI server (like the Node.js HTTP server)
**Gunicorn** = process manager that spawns multiple Uvicorn workers (like PM2 cluster mode)

In Node.js, you run one process (single-threaded event loop) and scale with PM2, cluster mode, or container replicas. Python's story is more nuanced because of the GIL.

### Workers Formula

| Deployment | Formula | Reasoning |
|-----------|---------|-----------|
| Bare metal / VM | `CPU * 2 + 1` (sync) or `CPU` (async) | Fill CPU capacity |
| Kubernetes | `1-2` workers per pod | Scale with replicas instead |
| Memory-constrained | `RAM / (per-worker RSS)` | Prevent OOM |

Why fewer async workers? Each Uvicorn worker runs an async event loop (like a Node.js process). It can handle thousands of concurrent connections without needing many workers. More workers are needed for sync/CPU-bound work where the GIL blocks.

### Gunicorn Config Template

```python
# gunicorn.conf.py
import multiprocessing, os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() + 1))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
```

### Worker Classes

| Worker Class | Use Case |
|-------------|----------|
| `uvicorn.workers.UvicornWorker` | Async FastAPI apps (most common) |
| `sync` (default) | Traditional WSGI apps (Flask/Django without async) |
| `gthread` | Thread-based — useful for IO-bound WSGI apps |
| `gevent` | Greenlet-based concurrency — legacy choice |

### Running It

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production with Gunicorn
gunicorn app.main:app -c gunicorn.conf.py

# Or inline (useful for Docker CMD)
gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Graceful Shutdown

```python
# FastAPI lifespan events (the modern way — replaces on_event)
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize resources
    print("Starting up...")
    pool = await create_db_pool()
    app.state.db_pool = pool

    yield  # Application runs here

    # Shutdown: clean up resources
    print("Shutting down...")
    await pool.close()

app = FastAPI(lifespan=lifespan)
```

Gunicorn sends `SIGTERM` to workers, which triggers Uvicorn's graceful shutdown, which triggers the lifespan shutdown. The `graceful_timeout` controls how long workers have to finish.

---

## Docker Compose (Development/Small Deployments)

```yaml
# docker-compose.yml
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  db:
    image: postgres:16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d app"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  worker:
    build: .
    command: arq app.worker.WorkerSettings
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/app
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  pgdata:
```

---

## Kubernetes Deployment

### Complete Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-service
  labels:
    app: fastapi-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fastapi-service
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: fastapi-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: fastapi-service
      terminationGracePeriodSeconds: 60
      containers:
        - name: api
          image: registry.example.com/fastapi-service:v1.2.3
          ports:
            - containerPort: 8000
              protocol: TCP
          env:
            - name: ENVIRONMENT
              value: "production"
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: fastapi-secrets
                  key: database-url
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: fastapi-secrets
                  key: jwt-secret
          envFrom:
            - configMapRef:
                name: fastapi-config
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /startupz
              port: 8000
            periodSeconds: 5
            failureThreshold: 30
---
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
spec:
  selector:
    app: fastapi-service
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-service
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
spec:
  ingressClassName: nginx
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi-service
                port:
                  number: 80
  tls:
    - hosts:
        - api.example.com
      secretName: api-tls
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: fastapi-config
data:
  APP_NAME: "fastapi-service"
  LOG_LEVEL: "INFO"
  WORKERS: "2"
  OTEL_ENDPOINT: "http://otel-collector:4317"
```

**Critical for FastAPI**: Set `terminationGracePeriodSeconds` to be greater than your Gunicorn `graceful_timeout`. Otherwise Kubernetes kills the pod before in-flight requests complete.

### Horizontal Pod Autoscaling

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fastapi-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fastapi-service
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
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
        - type: Percent
          value: 25
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Percent
          value: 100
          periodSeconds: 60
        - type: Pods
          value: 4
          periodSeconds: 60
      selectPolicy: Max
```

**Python-specific HPA note**: Since each Uvicorn worker handles async IO efficiently, CPU-based scaling may not trigger often enough for IO-bound services. Consider custom metrics like request latency (p99) or queue depth.

### Helm Chart Structure

```
fastapi-chart/
  Chart.yaml
  values.yaml
  templates/
    deployment.yaml
    service.yaml
    ingress.yaml
    hpa.yaml
    configmap.yaml
    secret.yaml
    _helpers.tpl
```

```yaml
# values.yaml
replicaCount: 3

image:
  repository: registry.example.com/fastapi-service
  tag: "latest"
  pullPolicy: IfNotPresent

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilization: 70
  targetMemoryUtilization: 80

config:
  LOG_LEVEL: "INFO"
  WORKERS: "2"
```

---

## Deployment Strategies

### Blue-Green

```
       ┌─────────────┐
       │ Load Balancer│
       └──────┬───────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────┐        ┌────▼────┐
│  Blue  │        │  Green  │
│ (live) │        │ (idle)  │
└────────┘        └─────────┘
```

Deploy new version to Green, test it, then switch the load balancer. Instant rollback by switching back to Blue.

### Rolling (Kubernetes Default)

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # One extra pod during rollout
    maxUnavailable: 0   # Never below desired count
```

### Canary

Two Deployments with different replica counts behind the same Service:
- stable: 9 replicas (90% traffic)
- canary: 1 replica (10% traffic)

---

## systemd (Bare Metal/VMs)

```ini
# /etc/systemd/system/fastapi-app.service
[Unit]
Description=FastAPI Application
After=network.target postgresql.service

[Service]
Type=notify
User=appuser
Group=appuser
WorkingDirectory=/opt/app
Environment="PATH=/opt/app/.venv/bin"
ExecStart=/opt/app/.venv/bin/gunicorn app.main:app -c gunicorn.conf.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=60

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/opt/app/data

[Install]
WantedBy=multi-user.target
```

---

## uv Workflow Reference

```bash
# Create a new project
uv init my-service && cd my-service

# Add dependencies (like npm install <pkg>)
uv add fastapi uvicorn sqlalchemy

# Add dev dependencies
uv add --dev pytest pytest-asyncio ruff mypy

# Install from lock file (like npm ci)
uv sync

# Run through the managed environment
uv run pytest
uv run uvicorn app.main:app --reload

# Update a specific package
uv lock --upgrade-package sqlalchemy

# Export to requirements.txt (for compatibility)
uv export --format requirements-txt > requirements.txt

# Drop-in pip replacement
uv pip install -r requirements.txt
```

---

## Quick Commands

```bash
# Run production locally
gunicorn app.main:app -c gunicorn.conf.py

# Profile a running process
py-spy top --pid $(pgrep -f uvicorn)

# Check Docker image size
docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | grep my-service

# Kubernetes rollout
kubectl rollout status deployment/fastapi-service
kubectl rollout undo deployment/fastapi-service  # rollback
```

---

## Key Takeaways

- Use `python:3.12-slim` (not alpine) — alpine's musl libc breaks pre-built Python wheels.
- `uv` is the modern Python package manager: 10-100x faster than pip, Rust-based.
- Copy dependency files before source code in Dockerfiles to maximize layer caching.
- Gunicorn manages Uvicorn workers: use `uvicorn.workers.UvicornWorker` as the worker class.
- For Kubernetes: 1-2 workers per pod, scale with pod replicas; `terminationGracePeriodSeconds` must exceed `graceful_timeout`.
- Rolling deployments with `maxUnavailable: 0` ensure zero-downtime; startup/readiness probes gate traffic.
