# 02 – Configuration, Logging, and Observability

## Configuration Management with pydantic-settings

### Coming from dotenv in Node.js

In Node.js, you use `dotenv` + manual validation (or `zod` if you're disciplined). Python's `pydantic-settings` gives you validated, typed configuration out of the box.

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""
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
    release_version: str = "unknown"

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

It validates on startup — if `DATABASE_URL` is missing or `PORT` is not an integer, the application fails immediately with a clear error rather than crashing later at runtime.

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

### HashiCorp Vault Integration

```python
# app/vault.py
import hvac

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
```

```yaml
# external-secret.yaml — syncs from Vault to K8s secrets via External Secrets Operator
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

---

## Structured Logging with structlog

### Coming from pino/winston

If you used **pino** in Node.js, structlog will feel familiar. Both produce JSON-structured logs with bound context.

| Feature | pino (Node.js) | structlog (Python) |
|---------|----------------|-------------------|
| Output | JSON by default | Configurable (JSON, console, key=value) |
| Context binding | `logger.child({ requestId })` | `structlog.bind_logger(request_id=...)` |
| Performance | Very fast (streams) | Fast (processor pipeline) |
| Integration | Express middleware | FastAPI middleware/dependency |

### Setup Template

```python
# app/logging_config.py
import structlog, logging, sys

def setup_logging(json_logs: bool = True, log_level: str = "INFO"):
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json_logs
        else structlog.dev.ConsoleRenderer()  # colored output for development
    )

    structlog.configure(
        processors=[*processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
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
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)
```

### Request ID Propagation

This is the Python equivalent of a pino `child` logger scoped to a request:

```python
# app/middleware/logging.py
import uuid, structlog
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, method=request.method, path=request.url.path,
        )
        logger.info("request_started")
        response = await call_next(request)
        logger.info("request_completed", status_code=response.status_code)
        response.headers["x-request-id"] = request_id
        return response
```

### Context Variables — Python's AsyncLocalStorage

Python's `contextvars` module provides async-safe context — similar to Node.js `AsyncLocalStorage`. structlog uses this to propagate logging context across async boundaries automatically:

```python
import structlog

logger = structlog.get_logger()

async def process_order(order_id: str):
    # Bind additional context — additive to request context
    structlog.contextvars.bind_contextvars(order_id=order_id)

    logger.info("processing_order")  # Includes request_id AND order_id
    await validate_payment(order_id)

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

### Probe Types

| Probe | Purpose | When it fails |
|-------|---------|---------------|
| **Liveness** (`/healthz`) | "Is the process alive?" | Restart the container |
| **Readiness** (`/readyz`) | "Can it handle traffic?" | Remove from load balancer |
| **Startup** (`/startupz`) | "Has it finished initializing?" | Don't check liveness yet |

### Implementation

```python
# app/api/health.py
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def liveness():
    """Liveness probe — keep this fast and dependency-free."""
    return {"status": "alive"}

@router.get("/readyz")
async def readiness():
    """Readiness probe — check all critical dependencies."""
    checks = {}
    try:
        async with get_session() as s:
            await s.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = str(e)

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={"status": "ready" if healthy else "degraded", "checks": checks},
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )

@router.get("/startupz")
async def startup():
    """Startup probe — have we finished initializing?"""
    return {"status": "started"}
```

### Kubernetes Probe Configuration

```yaml
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

The concepts (traces, spans, metrics) are identical to the Node.js OTel SDK. Only package names differ.

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

def setup_otel(app, engine):
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

    # Auto-instrument (traces every request/query/outgoing call)
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()
```

### Custom Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_payment(order_id: str, amount: float):
    with tracer.start_as_current_span(
        "process_payment",
        attributes={"order.id": order_id, "payment.amount": amount}
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
import time

meter = metrics.get_meter(__name__)

request_counter = meter.create_counter(
    "http.requests.total",
    description="Total HTTP requests",
)

response_time = meter.create_histogram(
    "http.response.duration",
    unit="ms",
    description="HTTP response time in milliseconds",
)

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

```python
# app/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

def setup_sentry(dsn: str, environment: str, release: str):
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=0.1,       # Sample 10% of transactions
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            HttpxIntegration(),
            LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
        ],
        before_send=filter_sensitive_data,
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
    """Skip health checks, sample errors at 100%."""
    if sampling_context.get("asgi_scope", {}).get("path", "").startswith("/health"):
        return 0.0
    return 0.1
```

### Breadcrumbs and Custom Context

```python
import sentry_sdk

async def create_order(user_id: str, items: list):
    sentry_sdk.add_breadcrumb(
        category="order",
        message=f"Creating order for user {user_id}",
        level="info",
        data={"item_count": len(items)},
    )
    sentry_sdk.set_user({"id": user_id})
    sentry_sdk.set_context("order", {
        "item_count": len(items),
        "total_value": sum(i.price for i in items),
    })
    sentry_sdk.set_tag("order.priority", "high" if sum(i.price for i in items) > 1000 else "normal")

    try:
        return await process_order(user_id, items)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise
```

---

## Prometheus Metrics

```python
# app/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
import time

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

ACTIVE_REQUESTS = Gauge("http_requests_active", "Number of active HTTP requests")

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
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

@app.get("/metrics")
async def metrics():
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type="text/plain")
```

### Key Metrics to Track

| Metric | Type | Alert Threshold | Why |
|--------|------|----------------|-----|
| `http_requests_total` | Counter | N/A (rate it) | Traffic baseline |
| `http_request_duration_seconds` | Histogram | p99 > 2s | User experience |
| `http_errors_total{status=~"5.."}` | Counter | > 1% of traffic | Reliability SLO |
| `db_pool_active_connections` | Gauge | > 80% pool size | Connection exhaustion |
| `db_query_duration_seconds` | Histogram | p99 > 500ms | Slow queries |
| `process_resident_memory_bytes` | Gauge | > 80% limit | OOM risk |
| `python_gc_collections_total` | Counter | Sudden spikes | GC pressure |
| `active_async_tasks` | Gauge | Growing unbounded | Task pile-up |

### Grafana Dashboard Essentials

1. **Request rate by endpoint** — identifies hot paths
2. **Error rate (5xx) with alert threshold** — SLO monitoring
3. **Latency percentiles (p50, p95, p99)** — tail latency matters
4. **Database query duration** — slow queries kill services
5. **Connection pool saturation** — the silent killer
6. **Memory RSS over time** — catch leaks early
7. **Active async tasks** — detect task pile-ups

---

## Feature Flags

### LaunchDarkly

```python
import ldclient
from ldclient.config import Config
from ldclient import Context

def init_launchdarkly(sdk_key: str):
    ldclient.set_config(Config(sdk_key))
    return ldclient.get()

def get_flag(flag_key: str, user_id: str, default: bool = False) -> bool:
    context = Context.builder(user_id).kind("user").build()
    return ldclient.get().variation(flag_key, context, default)

@app.get("/api/recommendations")
async def get_recommendations(user: User = Depends(get_current_user)):
    if get_flag("new-recommendation-engine", user.id):
        return await new_recommendation_engine(user)
    return await legacy_recommendation_engine(user)
```

### Unleash (Open-Source)

```python
from UnleashClient import UnleashClient

def init_unleash(url: str, app_name: str, api_token: str) -> UnleashClient:
    client = UnleashClient(url=url, app_name=app_name,
                           custom_headers={"Authorization": api_token})
    client.initialize_client()
    return client

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

## Key Takeaways

- `pydantic-settings` combines dotenv + zod-style validation: fails fast at startup with a clear error if config is invalid.
- structlog + `contextvars` = automatic request ID propagation across all async boundaries — equivalent to Node.js `AsyncLocalStorage`.
- Use separate liveness (`/healthz`) and readiness (`/readyz`) probes — liveness restarts, readiness removes from load balancer.
- OpenTelemetry auto-instruments FastAPI, SQLAlchemy, and httpx with zero code changes — add custom spans for business logic.
- Sentry's `before_send` hook is the right place to scrub PII — always redact `Authorization` headers.
- The RED method (Rate, Errors, Duration) covers the essential metrics; add saturation (pool utilization, memory) for operational completeness.
