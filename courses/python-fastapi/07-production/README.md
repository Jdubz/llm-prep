# Module 07: Production Deployment

> Everything between "it works on my machine" and "it works in production at scale."
> Assumes you've deployed Node.js/TypeScript services and understand containers, CI/CD, and observability concepts.

---

## Table of Contents

1. [Docker Multi-Stage Builds for Python](#docker-multi-stage-builds-for-python)
2. [Uvicorn/Gunicorn Configuration](#uvicorngunicorn-configuration)
3. [Structured Logging with structlog](#structured-logging-with-structlog)
4. [Health Checks and Readiness Probes](#health-checks-and-readiness-probes)
5. [OpenTelemetry Instrumentation](#opentelemetry-instrumentation)
6. [Error Tracking with Sentry](#error-tracking-with-sentry)
7. [Configuration Management](#configuration-management)
8. [Monitoring and Alerting](#monitoring-and-alerting)
9. [Deployment Strategies](#deployment-strategies)
10. [Process Management](#process-management)
11. [Interview Questions](#interview-questions)

---

## Docker Multi-Stage Builds for Python

### The TypeScript Mental Model

In Node.js, you typically:
1. Install deps (`npm ci`)
2. Build (`tsc` or bundler)
3. Copy built JS to a slim runtime image

Python is different: there's no "build" step for most projects (no transpilation), but you still need a compilation step for **C-extension wheels** (numpy, psycopg2, etc.). Multi-stage builds solve this.

### Package Managers: pip vs poetry vs uv

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
RUN uv pip install --system --no-cache -r pyproject.toml

FROM python:3.12-slim
COPY --from=builder /usr/local /usr/local
COPY . /app
```

**Why uv is winning**: `uv` is written in Rust (by the Astral team who built `ruff`). It resolves and installs packages 10-100x faster than pip. Think of it as the `pnpm` of Python — fast, deterministic, and increasingly the default.

### Base Image: slim vs alpine

| Image | Size | Gotchas |
|-------|------|---------|
| `python:3.12` | ~1 GB | Full Debian — unnecessary for production |
| `python:3.12-slim` | ~120 MB | Stripped Debian — **recommended for most cases** |
| `python:3.12-alpine` | ~50 MB | musl libc — breaks many wheels, slow builds for C extensions |

**The alpine trap**: In Node.js, alpine images are a safe default. In Python, alpine uses `musl` instead of `glibc`, which means pre-built binary wheels (manylinux) won't work. You end up compiling from source, which is slower and requires installing build tools. Use `slim` unless you have a specific reason for alpine.

### Layer Caching

The key insight is the same as Node.js: copy dependency files first, install, then copy source code.

```dockerfile
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Layer 1: Dependencies (cached unless lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Layer 2: Application code (changes frequently)
COPY . /app

FROM python:3.12-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

WORKDIR /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### .dockerignore

```
# .dockerignore
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

This is equivalent to your `.dockerignore` in a Node.js project — skip caches, virtual environments, and dev tooling artifacts.

---

## Uvicorn/Gunicorn Configuration

### Coming from Node.js

In Node.js, you run one process (single-threaded event loop) and scale with PM2, cluster mode, or container replicas. Python's story is more nuanced because of the GIL.

**Uvicorn** = ASGI server (like the Node.js HTTP server)
**Gunicorn** = process manager that spawns multiple Uvicorn workers (like PM2 cluster mode)

### The Workers Formula

```python
# Classic formula
workers = (2 * cpu_cores) + 1

# For async (uvicorn) workers — fewer needed since they handle concurrency within a process
workers = cpu_cores * 1  # start here, tune based on load

# For Kubernetes — usually 1-2 workers per pod, scale with pod replicas instead
workers = 2
```

Why fewer async workers? Each Uvicorn worker runs an async event loop (like a Node.js process). It can handle thousands of concurrent connections without needing many workers. More workers are needed for sync/CPU-bound work where the GIL blocks.

### Gunicorn Configuration File

```python
# gunicorn.conf.py
import multiprocessing
import os

# Bind
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Workers
workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"  # ASGI support

# Timeouts
timeout = 120           # Kill worker if it doesn't respond in 120s
graceful_timeout = 30   # Time to finish in-flight requests on shutdown
keepalive = 5           # Keep-alive timeout for connections

# Lifecycle
max_requests = 1000           # Restart worker after N requests (prevents memory leaks)
max_requests_jitter = 100     # Random jitter to avoid all workers restarting at once
preload_app = True            # Load app before forking — shares memory, faster startup

# Logging
accesslog = "-"               # stdout
errorlog = "-"                # stderr
loglevel = os.getenv("LOG_LEVEL", "info")

# Graceful shutdown
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def worker_exit(server, worker):
    """Called when a worker exits — useful for cleanup."""
    pass
```

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

### Worker Classes

| Worker Class | Use Case |
|-------------|----------|
| `uvicorn.workers.UvicornWorker` | Async FastAPI apps (most common) |
| `sync` (default) | Traditional WSGI apps (Flask/Django without async) |
| `gthread` | Thread-based — useful for IO-bound WSGI apps |
| `gevent` | Greenlet-based concurrency — legacy choice |

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

## Structured Logging with structlog

### Coming from pino/winston

If you used **pino** in Node.js, structlog will feel familiar. Both produce JSON-structured logs with bound context. The key differences:

| Feature | pino (Node.js) | structlog (Python) |
|---------|----------------|-------------------|
| Output | JSON by default | Configurable (JSON, console, key=value) |
| Context binding | `logger.child({ requestId })` | `structlog.bind_logger(request_id=...)` |
| Performance | Very fast (streams) | Fast (processor pipeline) |
| Integration | Express middleware | FastAPI middleware/dependency |

### Basic Setup

```python
# app/logging_config.py
import structlog
import logging
import sys

def setup_logging(json_logs: bool = True, log_level: str = "INFO"):
    """Configure structlog for production or development."""

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,      # Merge context variables
        structlog.stdlib.add_logger_name,               # Add logger name
        structlog.stdlib.add_log_level,                  # Add log level
        structlog.stdlib.PositionalArgumentsFormatter(), # Format positional args
        structlog.processors.TimeStamper(fmt="iso"),     # ISO timestamp
        structlog.processors.StackInfoRenderer(),        # Stack info
        structlog.processors.UnicodeDecoder(),           # Decode bytes
    ]

    if json_logs:
        # Production: JSON output (like pino)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored console output (like pino-pretty)
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
```

### Request ID Propagation

This is the Python equivalent of a pino `child` logger scoped to a request:

```python
# app/middleware/logging.py
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID (like X-Request-Id header in Express)
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

        # Bind to context variables — all logs in this request will include these
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        logger.info("request_started")

        response = await call_next(request)

        structlog.contextvars.bind_contextvars(
            status_code=response.status_code,
        )
        logger.info("request_completed")

        response.headers["x-request-id"] = request_id
        return response
```

### Context Variables (Python's Secret Weapon)

Python's `contextvars` module provides async-safe context — similar to Node.js `AsyncLocalStorage`. structlog uses this to propagate logging context across async boundaries automatically:

```python
import structlog

logger = structlog.get_logger()

async def process_order(order_id: str):
    # Bind additional context — this is additive to the request context
    structlog.contextvars.bind_contextvars(order_id=order_id)

    logger.info("processing_order")  # Includes request_id AND order_id

    await validate_payment(order_id)
    await ship_order(order_id)

async def validate_payment(order_id: str):
    logger.info("validating_payment")  # Still has request_id and order_id
```

Output (JSON):
```json
{"event": "processing_order", "request_id": "abc-123", "order_id": "ord-456", "timestamp": "2024-01-15T10:30:00Z", "level": "info"}
{"event": "validating_payment", "request_id": "abc-123", "order_id": "ord-456", "timestamp": "2024-01-15T10:30:01Z", "level": "info"}
```

---

## Health Checks and Readiness Probes

### The Pattern

Same concept as in Node.js microservices — expose endpoints that orchestrators (Kubernetes, ECS, load balancers) use to determine service health.

| Probe | Purpose | When it fails |
|-------|---------|---------------|
| **Liveness** (`/healthz`) | "Is the process alive?" | Restart the container |
| **Readiness** (`/readyz`) | "Can it handle traffic?" | Remove from load balancer |
| **Startup** (`/startupz`) | "Has it finished initializing?" | Don't check liveness yet |

### Implementation

```python
# app/api/health.py
from fastapi import APIRouter, Response, status
from sqlalchemy import text
from app.database import async_session_factory
from app.dependencies import get_redis

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def liveness():
    """Liveness probe — is the process running?
    Keep this fast and dependency-free.
    """
    return {"status": "alive"}

@router.get("/readyz")
async def readiness():
    """Readiness probe — can we handle traffic?
    Check all critical dependencies.
    """
    checks = {}

    # Check database
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # Determine overall status
    all_healthy = all(v == "ok" for v in checks.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return Response(
        content={"status": "ready" if all_healthy else "not_ready", "checks": checks}.__str__(),
        status_code=status_code,
        media_type="application/json",
    )

@router.get("/startupz")
async def startup():
    """Startup probe — have we finished initializing?
    Check that migrations have run, caches are warm, etc.
    """
    return {"status": "started"}
```

### Kubernetes Probe Configuration

```yaml
# deployment.yaml (excerpt)
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
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 30  # 30 * 5 = 150s max startup time
```

---

## OpenTelemetry Instrumentation

### The Landscape

OpenTelemetry (OTel) is the same in Python as in Node.js — vendor-neutral observability. The concepts (traces, spans, metrics) are identical. The Python SDK just has different package names.

### Installation

```bash
pip install opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-fastapi \
    opentelemetry-instrumentation-sqlalchemy \
    opentelemetry-instrumentation-httpx \
    opentelemetry-instrumentation-logging
```

### Automatic Instrumentation

```python
# app/telemetry.py
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_telemetry(app, engine):
    """Initialize OpenTelemetry with automatic instrumentation."""
    resource = Resource.create({
        "service.name": "my-fastapi-service",
        "service.version": "1.0.0",
        "deployment.environment": "production",
    })

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())  # Sends to OTEL_EXPORTER_OTLP_ENDPOINT
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument FastAPI (traces every request automatically)
    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy (traces every query)
    SQLAlchemyInstrumentor().instrument(engine=engine)

    # Auto-instrument httpx (traces outgoing HTTP calls)
    HTTPXClientInstrumentor().instrument()
```

### Custom Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_payment(order_id: str, amount: float):
    # Custom span — like a manual trace in Datadog or Jaeger
    with tracer.start_as_current_span(
        "process_payment",
        attributes={
            "order.id": order_id,
            "payment.amount": amount,
        }
    ) as span:
        try:
            result = await payment_gateway.charge(amount)
            span.set_attribute("payment.transaction_id", result.transaction_id)
            return result
        except PaymentError as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

### Custom Metrics

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# Counter (like Prometheus counter)
request_counter = meter.create_counter(
    "http.requests.total",
    description="Total HTTP requests",
)

# Histogram (like Prometheus histogram)
response_time = meter.create_histogram(
    "http.response.duration",
    unit="ms",
    description="HTTP response time in milliseconds",
)

# Usage in middleware
async def metrics_middleware(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = (time.perf_counter() - start) * 1000

    request_counter.add(1, {"method": request.method, "path": request.url.path})
    response_time.record(duration, {"method": request.method, "status": response.status_code})

    return response
```

---

## Error Tracking with Sentry

### Setup

```python
# app/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

def setup_sentry(dsn: str, environment: str, release: str):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,

        # Performance monitoring
        traces_sample_rate=0.1,       # Sample 10% of transactions
        profiles_sample_rate=0.1,     # Profile 10% of sampled transactions

        # Integrations (auto-detected, but explicit is better)
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            HttpxIntegration(),
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],

        # Filter sensitive data
        before_send=filter_sensitive_data,

        # Don't send health check transactions
        traces_sampler=traces_sampler,
    )

def filter_sensitive_data(event, hint):
    """Scrub PII before sending to Sentry."""
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        if "Authorization" in headers:
            headers["Authorization"] = "[REDACTED]"
    return event

def traces_sampler(sampling_context):
    """Custom sampling — skip health checks, sample errors at 100%."""
    if sampling_context.get("asgi_scope", {}).get("path", "").startswith("/health"):
        return 0.0  # Never trace health checks
    return 0.1      # 10% for everything else
```

### Breadcrumbs and Custom Context

```python
import sentry_sdk

async def create_order(user_id: str, items: list):
    # Add breadcrumb — like console.log but captured by Sentry
    sentry_sdk.add_breadcrumb(
        category="order",
        message=f"Creating order for user {user_id}",
        level="info",
        data={"item_count": len(items)},
    )

    # Set user context — appears in Sentry dashboard
    sentry_sdk.set_user({"id": user_id})

    # Set custom context — grouped in Sentry UI
    sentry_sdk.set_context("order", {
        "item_count": len(items),
        "total_value": sum(i.price for i in items),
    })

    # Set tags — searchable/filterable in Sentry
    sentry_sdk.set_tag("order.priority", "high" if sum(i.price for i in items) > 1000 else "normal")

    try:
        return await process_order(user_id, items)
    except Exception as e:
        # Capture with extra context
        sentry_sdk.capture_exception(e)
        raise
```

---

## Configuration Management

### pydantic-settings (Replaces dotenv)

In Node.js, you use `dotenv` + manual validation (or `zod` if you're disciplined). Python's `pydantic-settings` gives you validated, typed configuration out of the box:

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings — loaded from environment variables.

    Equivalent to a validated .env schema in Node.js.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,        # DATABASE_URL or database_url both work
        env_nested_delimiter="__",   # APP__DB__HOST -> app.db.host
    )

    # Application
    app_name: str = "my-service"
    debug: bool = False
    environment: str = Field(default="development", pattern="^(development|staging|production)$")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = Field(default=1, ge=1, le=32)

    # Database
    database_url: PostgresDsn
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0)

    # Redis
    redis_url: RedisDsn = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    # External Services
    sentry_dsn: str | None = None
    otel_endpoint: str | None = None

@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — loaded once, reused everywhere.

    Use as a FastAPI dependency:
        @app.get("/")
        def root(settings: Settings = Depends(get_settings)):
            ...
    """
    return Settings()
```

### 12-Factor App Compliance

| Factor | Node.js Approach | Python/FastAPI Approach |
|--------|-----------------|----------------------|
| Config | `process.env` + dotenv | `pydantic-settings` (validated, typed) |
| Dependencies | `package.json` + lockfile | `pyproject.toml` + `uv.lock` |
| Backing services | Connection URLs in env | Same — `DATABASE_URL`, `REDIS_URL` |
| Port binding | `app.listen(PORT)` | `uvicorn --port $PORT` |
| Processes | Stateless, cluster mode | Stateless, Gunicorn workers |
| Logs | Write to stdout | structlog to stdout |
| Dev/prod parity | Docker Compose | Same |

### Secrets Management

```python
# For Kubernetes: mount secrets as environment variables or files
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets",  # Docker/K8s secrets mounted as files
    )

    database_password: str    # Read from /run/secrets/database_password
    jwt_secret: str           # Read from /run/secrets/jwt_secret
```

---

## Monitoring and Alerting

### Prometheus Metrics with FastAPI

```python
# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_REQUESTS = Gauge(
    "http_requests_active",
    "Number of active HTTP requests",
)

DB_POOL_SIZE = Gauge(
    "db_connection_pool_size",
    "Database connection pool size",
    ["state"],  # active, idle, overflow
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        ACTIVE_REQUESTS.inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
            ).inc()
            return response
        finally:
            duration = time.perf_counter() - start
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.url.path,
            ).observe(duration)
            ACTIVE_REQUESTS.dec()

# Metrics endpoint for Prometheus scraping
@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

### Key Metrics to Track

| Category | Metric | Why |
|----------|--------|-----|
| **RED** | Request rate | Traffic volume |
| **RED** | Error rate (5xx) | Service reliability |
| **RED** | Duration (p50, p95, p99) | User experience |
| **Saturation** | Active connections | Capacity planning |
| **Saturation** | DB pool utilization | Connection exhaustion |
| **Saturation** | Memory/CPU usage | Resource limits |
| **Business** | Orders created/min | Business health |
| **Business** | Auth failures | Security anomalies |

### Grafana Dashboard Essentials

Track these panels in your FastAPI service dashboard:

1. **Request rate by endpoint** — identifies hot paths
2. **Error rate (5xx) with alert threshold** — SLO monitoring
3. **Latency percentiles (p50, p95, p99)** — tail latency matters
4. **Database query duration** — slow queries kill services
5. **Connection pool saturation** — the silent killer
6. **Memory RSS over time** — catch leaks early
7. **Active async tasks** — detect task pile-ups

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
   ┌────▼────┐        ┌────▼────┐
   │  Blue   │        │  Green  │
   │ (live)  │        │ (idle)  │
   └─────────┘        └─────────┘
```

Deploy new version to Green, test it, then switch the load balancer. Instant rollback by switching back to Blue.

**Python consideration**: If using Gunicorn with `preload_app=True`, the application is loaded into the master process and then forked into workers. A deployment replaces the entire process tree.

### Canary

```python
# Simple weight-based canary with Kubernetes
# or with a reverse proxy like Nginx/Envoy

# In Kubernetes, use two Deployments with different replica counts:
# - stable: 9 replicas (90% traffic)
# - canary: 1 replica (10% traffic)
# Both behind the same Service
```

### Rolling (Kubernetes Default)

```yaml
# deployment.yaml
spec:
  replicas: 4
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # One extra pod during rollout
      maxUnavailable: 0   # Never below desired count
  template:
    spec:
      terminationGracePeriodSeconds: 60  # Match your graceful_timeout
```

**Critical for FastAPI**: Set `terminationGracePeriodSeconds` to be greater than your Gunicorn `graceful_timeout`. Otherwise Kubernetes kills the pod before in-flight requests complete.

---

## Process Management

### Docker Compose (Development/Small Deployments)

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

### Kubernetes

For Kubernetes, you typically need:

1. **Deployment** — defines pod template, replicas, resource limits
2. **Service** — internal load balancer (ClusterIP)
3. **Ingress** — external access (nginx/traefik)
4. **ConfigMap** — non-secret configuration
5. **Secret** — sensitive configuration
6. **HPA** — horizontal pod autoscaler

See `deep-dive.md` for full Kubernetes manifests.

### systemd (Bare Metal/VMs)

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

## Interview Questions

### Docker & Deployment

**Q: Why would you choose `python:3.12-slim` over `python:3.12-alpine` for a FastAPI Docker image?**

A: Alpine uses musl libc instead of glibc. Many Python packages distribute pre-built binary wheels for manylinux (glibc), but not for musl. With alpine, packages like `psycopg2`, `numpy`, or `cryptography` must be compiled from source, requiring build tools in the image and dramatically increasing build time. The slim image is ~70 MB larger but avoids these issues entirely. This is a key difference from Node.js, where alpine is a safe default because Node itself and most npm packages are pure JavaScript or ship musl-compatible binaries.

**Q: Explain the relationship between Gunicorn and Uvicorn in a production FastAPI deployment.**

A: Gunicorn is a process manager (prefork server) that spawns and manages multiple worker processes. Uvicorn is an ASGI server that runs the async event loop within each worker. When you use `worker_class = "uvicorn.workers.UvicornWorker"`, Gunicorn handles process lifecycle (spawning, killing, restarting workers) while each worker runs a Uvicorn event loop that handles async request processing. This is analogous to PM2 running multiple Node.js processes in cluster mode, except each Python process has its own event loop rather than sharing one.

**Q: How do you calculate the right number of Gunicorn workers?**

A: The classic formula is `(2 * CPU_cores) + 1`, but this is for synchronous workers. For async Uvicorn workers, each worker already handles thousands of concurrent connections via the event loop, so you need fewer — typically `CPU_cores` or even less. In Kubernetes, the preferred approach is 1-2 workers per pod and scaling horizontally with pod replicas, because K8s already handles process-level redundancy and load balancing. The exact number should be tuned based on your workload: CPU-bound work benefits from more workers (up to the core count), while IO-bound async work needs fewer.

### Observability

**Q: How would you propagate a request ID through all log messages in a FastAPI application?**

A: Use structlog with Python's `contextvars` module. In middleware, generate or extract a request ID, then call `structlog.contextvars.bind_contextvars(request_id=request_id)`. All subsequent log calls within that request's async context will automatically include the request ID, even across `await` boundaries and nested function calls. This is Python's equivalent of Node.js `AsyncLocalStorage` — the context follows the async execution chain. Clear the context at the start of each request with `structlog.contextvars.clear_contextvars()` to prevent leaking between requests.

**Q: What metrics would you monitor for a production FastAPI service?**

A: The RED method covers the essentials: **Rate** (requests per second by endpoint), **Errors** (5xx rate, should be below SLO threshold), and **Duration** (p50/p95/p99 latency). Beyond RED, monitor saturation metrics: database connection pool utilization (approaching pool size is an emergency), memory RSS trend (for leak detection), CPU usage (for capacity planning), and active async tasks (pile-up indicates downstream issues). Business metrics are equally important: key transaction rates, authentication failures, and upstream dependency health.

### Configuration & Security

**Q: How does `pydantic-settings` compare to using dotenv in Node.js?**

A: `pydantic-settings` provides everything dotenv does (loading from `.env` files, environment variables) plus type validation, default values, nested configuration support, and secrets file loading. It validates on startup — if `DATABASE_URL` is missing or `PORT` is not an integer, the application fails immediately with a clear error rather than crashing later at runtime. It's like combining `dotenv` with `zod` schema validation, but built into the framework ecosystem. It also supports loading secrets from mounted files (`/run/secrets/`), which is important for Kubernetes and Docker Swarm.

**Q: Describe a graceful shutdown sequence for a production FastAPI service behind a load balancer.**

A: First, the load balancer (or Kubernetes) stops sending new traffic (readiness probe fails or pod is removed from endpoints). Then SIGTERM is sent to Gunicorn, which forwards it to workers. Each Uvicorn worker stops accepting new connections and waits for in-flight requests to complete (up to `graceful_timeout`). FastAPI's lifespan `shutdown` event fires, where you close database pools, flush metrics, and complete any pending background tasks. Finally, the process exits. In Kubernetes, `terminationGracePeriodSeconds` must exceed Gunicorn's `graceful_timeout` — otherwise the pod is SIGKILLed before graceful shutdown completes.

### Production Debugging

**Q: A production FastAPI endpoint is intermittently slow (p99 latency spike). How do you debug it?**

A: Start with distributed tracing (OpenTelemetry/Jaeger) — look at slow traces to identify which span is taking the longest. Common culprits: (1) database queries without proper indexing (check query plans), (2) connection pool exhaustion (all connections busy, new requests wait for one), (3) GIL contention from CPU-bound work in async handlers, (4) slow external API calls without timeouts. Use `py-spy` for production CPU profiling without stopping the process. Check Prometheus metrics for correlation — did the latency spike coincide with increased traffic, a deployment, or a database migration? If it's async-related, check for accidentally blocking the event loop with synchronous calls.

**Q: How would you implement zero-downtime deployments for a FastAPI service?**

A: Use rolling deployments in Kubernetes: set `maxSurge: 1` and `maxUnavailable: 0` so new pods start before old ones terminate. The startup probe ensures new pods are ready before receiving traffic. The readiness probe removes pods from the service endpoints before they shut down. Set `terminationGracePeriodSeconds` higher than your application's graceful shutdown timeout. For database migrations, use a separate migration job that runs before the deployment and ensure migrations are backward-compatible (never drop a column that old code still reads). For critical services, consider blue-green deployments where you can instantly switch back to the previous version if issues arise.
