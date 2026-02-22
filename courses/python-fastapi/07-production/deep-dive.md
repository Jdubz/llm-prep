# Production Deployment — Deep Dive

> Advanced production topics: modern Python tooling, profiling, Kubernetes manifests,
> secrets management, and feature flags. Optional content for engineers who want to go deeper.

---

## Table of Contents

1. [uv Package Manager](#uv-package-manager)
2. [Python Packaging](#python-packaging)
3. [Memory Profiling](#memory-profiling)
4. [CPU Profiling](#cpu-profiling)
5. [Async Profiling Challenges](#async-profiling-challenges)
6. [Kubernetes Deployment Manifests](#kubernetes-deployment-manifests)
7. [Helm Charts for FastAPI](#helm-charts-for-fastapi)
8. [Horizontal Pod Autoscaling](#horizontal-pod-autoscaling)
9. [Secrets Management with Vault](#secrets-management-with-vault)
10. [Feature Flags](#feature-flags)
11. [A/B Testing Infrastructure](#ab-testing-infrastructure)

---

## uv Package Manager

### Why uv Matters

`uv` is to Python what `pnpm` (or even `bun`) is to Node.js — a ground-up rewrite of the package manager in a systems language (Rust) for dramatically better performance.

| Operation | pip | poetry | uv |
|-----------|-----|--------|----|
| Cold install (large project) | ~60s | ~45s | ~2s |
| Resolve dependencies | ~15s | ~10s | ~0.5s |
| Lock file generation | N/A | ~10s | ~1s |
| Written in | Python | Python | Rust |

### uv Workflow (Replacing pip + venv + pip-tools)

```bash
# Create a new project
uv init my-service
cd my-service

# Add dependencies (like npm install <pkg>)
uv add fastapi uvicorn sqlalchemy

# Add dev dependencies (like npm install --save-dev)
uv add --dev pytest pytest-asyncio ruff mypy

# Install from lock file (like npm ci)
uv sync

# Run a script through the managed environment
uv run python -m pytest
uv run uvicorn app.main:app --reload

# Update a specific package
uv lock --upgrade-package sqlalchemy

# Export to requirements.txt (for compatibility)
uv export --format requirements-txt > requirements.txt
```

### uv as a pip Replacement

If you're working with an existing project that uses `requirements.txt`:

```bash
# Drop-in replacement for pip install
uv pip install -r requirements.txt

# Install a single package
uv pip install httpx

# Compile requirements (like pip-compile)
uv pip compile requirements.in -o requirements.txt
```

### Docker with uv

```dockerfile
FROM python:3.12-slim AS builder

# Install uv (single binary, no dependencies)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into the system Python (no venv needed in Docker)
RUN uv sync --frozen --no-dev --no-editable

# Copy application code
COPY . .

FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /app /app

# uv installs into .venv by default — adjust PATH
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Python Packaging

### pyproject.toml (The package.json of Python)

```toml
[project]
name = "my-fastapi-service"
version = "1.0.0"
description = "A production FastAPI service"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0",
    "pydantic-settings>=2.0",
    "structlog>=24.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.3.0",
    "mypy>=1.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Wheels vs Source Distributions

| Format | Analogy | When |
|--------|---------|------|
| **Wheel** (`.whl`) | Pre-built npm package | Pre-compiled, fast install, no build step |
| **sdist** (`.tar.gz`) | npm package with postinstall | Needs compilation (C extensions), slower |

When you `pip install numpy`, pip downloads a **wheel** — a pre-built binary for your platform. If no wheel exists (rare platform, old package), it falls back to sdist and compiles from source.

### Editable Installs

```bash
# Like npm link — changes to source are immediately reflected
uv pip install -e .

# Or with uv's project management
uv sync  # automatically installs the project in editable mode
```

This installs the package in "development mode" where Python reads directly from your source tree instead of copying files. Essential for local development.

---

## Memory Profiling

### tracemalloc (Built-in)

Python's built-in memory tracer — no external tools needed. Useful for finding memory leaks.

```python
import tracemalloc
import linecache

def start_memory_profiling():
    """Call on startup to enable memory tracking."""
    tracemalloc.start(25)  # Store 25 frames of traceback

def get_memory_snapshot():
    """Take a snapshot and return top allocations."""
    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics("lineno")

    result = []
    for stat in stats[:20]:
        result.append({
            "file": stat.traceback.format()[0],
            "size_kb": stat.size / 1024,
            "count": stat.count,
        })
    return result

def compare_snapshots(snapshot1, snapshot2):
    """Compare two snapshots to find leaks."""
    stats = snapshot2.compare_to(snapshot1, "lineno")
    for stat in stats[:10]:
        print(stat)
```

Expose it as a debug endpoint (protected, not public):

```python
@app.get("/debug/memory", include_in_schema=False)
async def memory_profile(api_key: str = Header(...)):
    if api_key != settings.debug_api_key:
        raise HTTPException(status_code=403)
    return get_memory_snapshot()
```

### objgraph (Object Reference Graphs)

```python
import objgraph

# Find the most common object types in memory
objgraph.show_most_common_types(limit=20)

# Find objects that are growing (potential leak)
objgraph.show_growth(limit=10)

# Visualize what's holding a reference to an object (prevents GC)
objgraph.show_backrefs(
    objgraph.by_type("MyModel")[:3],
    filename="refs.png",
    max_depth=5,
)
```

### Common Python Memory Leaks

| Leak Pattern | Description | Fix |
|-------------|-------------|-----|
| Growing lists/dicts in module scope | Global caches that never evict | Use `functools.lru_cache(maxsize=N)` or `cachetools.TTLCache` |
| Closures capturing large objects | Lambda/function references keep objects alive | Weak references or restructure |
| Event handler accumulation | Adding handlers without removing them | Track handlers, remove on cleanup |
| SQLAlchemy session not closed | Objects in the identity map hold references | Use `async with` for sessions |
| Circular references with `__del__` | GC can't collect cycles with finalizers | Avoid `__del__`, use `weakref.finalize` |

---

## CPU Profiling

### cProfile (Built-in)

```python
import cProfile
import pstats
from io import StringIO

def profile_function(func, *args, **kwargs):
    """Profile a specific function call."""
    profiler = cProfile.Profile()
    profiler.enable()

    result = func(*args, **kwargs)

    profiler.disable()
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(20)  # Top 20 functions
    print(stream.getvalue())

    return result
```

### py-spy (Production CPU Profiling)

`py-spy` is the Python equivalent of `0x` or `clinic.js` for Node.js — it samples the call stack without stopping the process.

```bash
# Install (outside the app's venv)
pip install py-spy

# Profile a running process (attach by PID)
py-spy top --pid 12345

# Generate a flame graph (SVG)
py-spy record -o profile.svg --pid 12345 --duration 30

# Profile a command
py-spy record -o profile.svg -- python -m uvicorn app.main:app

# Show which lines are hot (line-level profiling)
py-spy dump --pid 12345
```

**Key insight for Node.js developers**: In Node.js, the event loop is single-threaded so a CPU profile shows everything. In Python, `py-spy` shows you all threads — you can see the main thread, Uvicorn's event loop thread, and any worker threads separately. Look for the GIL contention: if multiple threads are waiting on the GIL, you have a CPU-bound bottleneck.

### Profiling Endpoints in FastAPI

```python
import cProfile
import pstats
from io import StringIO

# Middleware that profiles slow requests
class ProfilingMiddleware:
    def __init__(self, app, threshold_ms: float = 1000):
        self.app = app
        self.threshold_ms = threshold_ms

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import time
        start = time.perf_counter()
        await self.app(scope, receive, send)
        duration_ms = (time.perf_counter() - start) * 1000

        if duration_ms > self.threshold_ms:
            logger.warning(
                "slow_request",
                path=scope["path"],
                duration_ms=duration_ms,
            )
```

---

## Async Profiling Challenges

### The Problem

Traditional profilers (cProfile) measure wall-clock time per function call. In async code, a function might take 500ms of wall time but only 1ms of CPU time — the rest is `await`ing IO. The profiler attributes the full 500ms to the function, which is misleading.

### Solutions

```python
# 1. Use py-spy in "idle" mode to see where time is spent waiting
# py-spy record --idle --pid 12345 -o profile.svg

# 2. Use OpenTelemetry spans for logical profiling
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

async def get_user_with_orders(user_id: str):
    with tracer.start_as_current_span("get_user_with_orders"):
        with tracer.start_as_current_span("fetch_user"):
            user = await db.get_user(user_id)

        with tracer.start_as_current_span("fetch_orders"):
            orders = await db.get_orders(user_id)

        with tracer.start_as_current_span("enrich_data"):
            # CPU-bound work — this is what to optimize
            enriched = enrich_user_data(user, orders)

        return enriched
```

```python
# 3. yappi — a profiler that understands async/threading
import yappi

yappi.set_clock_type("wall")  # or "cpu" for CPU-only time
yappi.start()

# ... run your workload ...

yappi.stop()
stats = yappi.get_func_stats()
stats.sort("ttot")  # Total time
stats.print_all(columns={
    "name": 60,
    "ncall": 10,
    "ttot": 10,
    "tsub": 10,
})
```

---

## Kubernetes Deployment Manifests

### Complete Deployment

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

---

## Helm Charts for FastAPI

### Chart Structure

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

### values.yaml

```yaml
# values.yaml
replicaCount: 3

image:
  repository: registry.example.com/fastapi-service
  tag: "latest"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  host: api.example.com
  tls: true

resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "1000m"

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilization: 70
  targetMemoryUtilization: 80

config:
  LOG_LEVEL: "INFO"
  WORKERS: "2"

# Secrets should be managed externally (Vault, sealed-secrets, etc.)
```

---

## Horizontal Pod Autoscaling

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
    # Scale based on CPU
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70

    # Scale based on memory
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # Scale based on custom metric (requests per second)
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
          value: 25               # Scale down max 25% at a time
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 30
      policies:
        - type: Percent
          value: 100              # Can double pod count
          periodSeconds: 60
        - type: Pods
          value: 4                # Or add 4 pods at a time
          periodSeconds: 60
      selectPolicy: Max
```

**Python-specific HPA note**: Since each Uvicorn worker handles async IO efficiently, you may find that CPU-based scaling doesn't trigger often enough for IO-bound services. Consider using custom metrics like request latency (p99) or queue depth for more responsive scaling.

---

## Secrets Management with Vault

### HashiCorp Vault Integration

```python
# app/vault.py
import hvac
from functools import lru_cache

class VaultClient:
    def __init__(self, url: str, token: str | None = None, role: str | None = None):
        self.client = hvac.Client(url=url)

        if token:
            self.client.token = token
        elif role:
            # Kubernetes auth — pod uses service account token
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
                jwt = f.read()
            self.client.auth.kubernetes.login(role=role, jwt=jwt)

    def get_secret(self, path: str) -> dict:
        """Read a secret from Vault KV v2."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response["data"]["data"]

    def get_database_credentials(self, role: str) -> dict:
        """Get dynamic database credentials from Vault."""
        response = self.client.secrets.database.generate_credentials(name=role)
        return {
            "username": response["data"]["username"],
            "password": response["data"]["password"],
            "ttl": response["lease_duration"],
        }

# Usage in pydantic-settings
class Settings(BaseSettings):
    @classmethod
    def settings_customise_sources(cls, settings_cls, **kwargs):
        """Add Vault as a settings source."""
        return (
            init_settings,
            env_settings,
            VaultSettingsSource(settings_cls),  # Custom source
            file_secret_settings,
        )
```

### Kubernetes Secrets with External Secrets Operator

```yaml
# external-secret.yaml — syncs from Vault to K8s secrets
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: fastapi-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: ClusterSecretStore
  target:
    name: fastapi-secrets
  data:
    - secretKey: database-url
      remoteRef:
        key: services/fastapi
        property: database_url
    - secretKey: jwt-secret
      remoteRef:
        key: services/fastapi
        property: jwt_secret
```

---

## Feature Flags

### LaunchDarkly Integration

```python
# app/feature_flags.py
import ldclient
from ldclient.config import Config
from ldclient import Context

def init_launchdarkly(sdk_key: str):
    ldclient.set_config(Config(sdk_key))
    client = ldclient.get()
    if client.is_initialized():
        print("LaunchDarkly initialized")
    return client

def get_flag(flag_key: str, user_id: str, default: bool = False) -> bool:
    client = ldclient.get()
    context = Context.builder(user_id).kind("user").build()
    return client.variation(flag_key, context, default)

# Usage in FastAPI endpoint
@app.get("/api/recommendations")
async def get_recommendations(
    user: User = Depends(get_current_user),
):
    if get_flag("new-recommendation-engine", user.id):
        return await new_recommendation_engine(user)
    return await legacy_recommendation_engine(user)
```

### Unleash (Open-Source Alternative)

```python
# app/feature_flags.py
from UnleashClient import UnleashClient

def init_unleash(url: str, app_name: str, api_token: str) -> UnleashClient:
    client = UnleashClient(
        url=url,
        app_name=app_name,
        custom_headers={"Authorization": api_token},
    )
    client.initialize_client()
    return client

# FastAPI dependency
async def get_feature_flags() -> UnleashClient:
    return app.state.unleash_client

@app.get("/api/search")
async def search(
    query: str,
    flags: UnleashClient = Depends(get_feature_flags),
    user: User = Depends(get_current_user),
):
    context = {"userId": user.id, "properties": {"plan": user.plan}}

    if flags.is_enabled("semantic-search", context):
        return await semantic_search(query)
    return await keyword_search(query)
```

---

## A/B Testing Infrastructure

### Architecture

```
  ┌──────────┐    ┌───────────────┐    ┌──────────────┐
  │  Client   │───▶│  FastAPI API   │───▶│  Feature Flag │
  │ (request) │    │ (assignment)   │    │  Service      │
  └──────────┘    └───────┬───────┘    └──────────────┘
                          │
                   ┌──────▼───────┐
                   │  Event Track  │
                   │  (analytics)  │
                   └──────┬───────┘
                          │
                   ┌──────▼───────┐
                   │  Data Pipeline│
                   │  (analysis)   │
                   └──────────────┘
```

### Implementation with FastAPI

```python
# app/ab_testing.py
import hashlib
from dataclasses import dataclass

@dataclass
class Experiment:
    name: str
    variants: list[str]  # e.g., ["control", "variant_a", "variant_b"]
    traffic_percent: float  # 0.0 to 1.0

def assign_variant(experiment: Experiment, user_id: str) -> str:
    """Deterministic variant assignment using consistent hashing.
    Same user always gets the same variant.
    """
    hash_input = f"{experiment.name}:{user_id}"
    hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)

    # Check if user is in the experiment traffic
    bucket = (hash_value % 10000) / 10000
    if bucket > experiment.traffic_percent:
        return "control"  # Not in experiment

    # Assign to variant
    variant_index = hash_value % len(experiment.variants)
    return experiment.variants[variant_index]

# Track experiment exposure
async def track_exposure(
    experiment_name: str,
    variant: str,
    user_id: str,
    analytics_client,
):
    await analytics_client.track(
        event="experiment_exposure",
        properties={
            "experiment": experiment_name,
            "variant": variant,
            "user_id": user_id,
        },
    )

# FastAPI dependency
async def get_experiment_variant(
    experiment_name: str,
    user: User = Depends(get_current_user),
) -> str:
    experiment = await get_experiment(experiment_name)
    variant = assign_variant(experiment, user.id)
    await track_exposure(experiment_name, variant, user.id, analytics)
    return variant
```

This gives you the same kind of experiment infrastructure you might build with Optimizely or split.io, but self-hosted and integrated directly into your FastAPI service. For production, prefer a dedicated feature flag service (LaunchDarkly, Unleash) over rolling your own — the statistical analysis, targeting rules, and dashboards are worth the cost.
