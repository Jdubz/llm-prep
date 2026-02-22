# Production Deployment Cheat Sheet

> Copy-paste templates and quick-reference tables. Scan, don't read.

---

## Dockerfile Template (Multi-Stage with uv)

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

---

## Gunicorn Config Template

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

---

## structlog Setup Template

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
        else structlog.dev.ConsoleRenderer()
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

### Request Logging Middleware

```python
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

---

## OpenTelemetry Setup

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_otel(app, engine):
    resource = Resource.create({"service.name": "my-service", "service.version": "1.0.0"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
```

---

## Sentry Setup

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    environment=settings.environment,
    release=settings.release_version,
    traces_sample_rate=0.1,
    integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    before_send=lambda event, hint: scrub_pii(event),
)
```

---

## Health Check Endpoint Template

```python
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])

@router.get("/healthz")
async def liveness():
    return {"status": "alive"}

@router.get("/readyz")
async def readiness():
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
```

---

## Key Production Metrics

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

---

## Docker Base Image Decision

| Image | Size | Use When |
|-------|------|----------|
| `python:3.12-slim` | ~120 MB | **Default choice** — pre-built wheels work |
| `python:3.12-alpine` | ~50 MB | Pure Python only, no C extensions |
| `python:3.12` | ~1 GB | Need build tools in final image (avoid) |

---

## Workers Formula

| Deployment | Formula | Reasoning |
|-----------|---------|-----------|
| Bare metal / VM | `CPU * 2 + 1` (sync) or `CPU` (async) | Fill CPU capacity |
| Kubernetes | `1-2` workers per pod | Scale with replicas instead |
| Memory-constrained | `RAM / (per-worker RSS)` | Prevent OOM |

---

## Quick Commands

```bash
# Run production locally
gunicorn app.main:app -c gunicorn.conf.py

# Profile a running process
py-spy top --pid $(pgrep -f uvicorn)

# Memory snapshot
python -c "import tracemalloc; tracemalloc.start(); exec(open('check.py').read()); print(tracemalloc.get_traced_memory())"

# Check Docker image size
docker images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | grep my-service

# Kubernetes rollout
kubectl rollout status deployment/fastapi-service
kubectl rollout undo deployment/fastapi-service  # rollback
```
