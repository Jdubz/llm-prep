"""
Production Deployment Examples

Complete, runnable patterns for deploying FastAPI services in production.
Covers structured logging, health checks, graceful shutdown, middleware,
configuration management, error tracking, and metrics collection.

Dependencies: fastapi, pydantic (stdlib only for most patterns).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from fastapi import FastAPI, Request, Response, APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# 1. STRUCTURED LOGGING (stdlib logging + JSON output + request ID)
# ============================================================================

# Context variable for request ID propagation across async boundaries.
# This is Python's equivalent of Node.js AsyncLocalStorage.
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter using only the standard library.

    Produces one JSON object per log line — ready for ingestion by
    Datadog, CloudWatch, ELK, or any log aggregator.

    Equivalent to pino's default JSON output in Node.js.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S.%03dZ"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Propagate request ID from context variable if available
        req_id = request_id_ctx.get()
        if req_id is not None:
            log_entry["request_id"] = req_id

        # Include any extra fields passed via `logger.info("msg", extra={...})`
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        # Include exception info when present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO", json_output: bool = True) -> None:
    """
    Configure structured logging for the application.

    Call this once at startup. All loggers created via logging.getLogger()
    will use the JSON formatter when json_output=True.
    """
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler()
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        # Development: human-readable format
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s")
        )

    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("app")


# ============================================================================
# 2. HEALTH CHECK ENDPOINTS (liveness + readiness with dependency checks)
# ============================================================================

health_router = APIRouter(tags=["health"])

# Track application readiness state — set to True once startup completes.
_app_ready: bool = False


class DependencyStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


class HealthCheck(BaseModel):
    status: str
    checks: dict[str, str] = {}


async def check_database() -> tuple[DependencyStatus, str]:
    """
    Simulate a database connectivity check.

    In production, replace with:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    """
    try:
        # Simulate a fast DB ping
        await asyncio.sleep(0.01)
        return DependencyStatus.OK, "connected"
    except Exception as e:
        return DependencyStatus.ERROR, str(e)


async def check_cache() -> tuple[DependencyStatus, str]:
    """
    Simulate a cache (Redis) connectivity check.

    In production, replace with:
        await redis.ping()
    """
    try:
        await asyncio.sleep(0.01)
        return DependencyStatus.OK, "connected"
    except Exception as e:
        return DependencyStatus.ERROR, str(e)


@health_router.get("/healthz", response_model=HealthCheck)
async def liveness() -> HealthCheck:
    """
    Liveness probe -- is the process alive?

    Keep this fast and dependency-free. If this fails, the orchestrator
    restarts the container. Never check external dependencies here.
    """
    return HealthCheck(status="alive")


@health_router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness(response: Response) -> HealthCheck:
    """
    Readiness probe -- can we handle traffic?

    Check all critical dependencies. If any fail, the load balancer
    removes this instance from the pool (but does NOT restart it).
    """
    checks: dict[str, str] = {}

    db_status, db_msg = await check_database()
    checks["database"] = db_msg

    cache_status, cache_msg = await check_cache()
    checks["cache"] = cache_msg

    all_healthy = all(
        v != DependencyStatus.ERROR
        for v in [db_status, cache_status]
    )

    if not all_healthy or not _app_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheck(
        status="ready" if (all_healthy and _app_ready) else "not_ready",
        checks=checks,
    )


# ============================================================================
# 3. GRACEFUL SHUTDOWN WITH LIFESPAN EVENTS
# ============================================================================

# Track in-flight requests for connection draining.
_active_requests: int = 0
_shutting_down: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager -- the modern replacement for
    @app.on_event("startup") / @app.on_event("shutdown").

    Startup: initialize pools, warm caches, mark ready.
    Shutdown: drain connections, close pools, flush buffers.
    """
    global _app_ready

    # -- STARTUP --
    logger.info("Application starting up")

    # In production, initialize real resources here:
    #   app.state.db_pool = await create_db_pool()
    #   app.state.redis = await create_redis_client()
    #   await run_health_checks()

    _app_ready = True
    logger.info("Application ready to serve traffic")

    yield  # <-- Application runs here

    # -- SHUTDOWN --
    global _shutting_down
    _shutting_down = True
    logger.info("Shutdown signal received, draining connections")

    # Wait for in-flight requests to complete (with timeout)
    drain_timeout = 30  # seconds
    drain_start = time.monotonic()
    while _active_requests > 0:
        elapsed = time.monotonic() - drain_start
        if elapsed > drain_timeout:
            logger.warning(
                f"Drain timeout reached with {_active_requests} active requests"
            )
            break
        await asyncio.sleep(0.1)

    logger.info("Connection draining complete")

    # Close resources
    #   await app.state.db_pool.close()
    #   await app.state.redis.close()

    _app_ready = False
    logger.info("Application shut down cleanly")


# ============================================================================
# 4. REQUEST/RESPONSE LOGGING MIDDLEWARE WITH TIMING
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every request with method, path, status code, and duration.

    Assigns a unique request ID (or uses the incoming X-Request-Id header)
    and propagates it via contextvars so all downstream logs include it.

    Similar to morgan/pino-http in Express.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        global _active_requests

        # Generate or extract request ID
        req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request_id_ctx.set(req_id)

        _active_requests += 1
        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "Request failed with unhandled exception",
                extra={"extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                }},
                exc_info=True,
            )
            raise
        finally:
            _active_requests -= 1

        duration_ms = (time.perf_counter() - start) * 1000

        # Skip logging for health check endpoints to reduce noise
        if not request.url.path.startswith(("/healthz", "/readyz")):
            logger.info(
                "Request completed",
                extra={"extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client": request.client.host if request.client else None,
                }},
            )

        # Echo request ID back to the caller
        response.headers["x-request-id"] = req_id
        return response


# ============================================================================
# 5. CONFIGURATION MANAGEMENT WITH PYDANTIC BASESETTINGS
# ============================================================================

class AppSettings(BaseModel):
    """
    Application configuration loaded from environment variables.

    Uses pydantic BaseModel here (swap to pydantic_settings.BaseSettings
    in production for automatic env-var loading). Demonstrates the
    validated, typed config pattern.

    Node.js equivalent: dotenv + zod schema validation combined.
    """

    # Application
    app_name: str = "my-fastapi-service"
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$",
    )
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=32)

    # Database
    database_url: str = "postgresql+asyncpg://localhost:5432/app"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=10, ge=0, le=50)

    # Auth
    jwt_secret: str = Field(default="change-me-in-production-minimum-32-chars!", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = Field(default=30, ge=1)

    # External services
    sentry_dsn: str | None = None
    log_level: str = "INFO"
    log_json: bool = True


# Singleton pattern -- load once, reuse everywhere.
_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    """
    Cached settings singleton. In FastAPI, use as a dependency:

        @app.get("/")
        def root(settings: AppSettings = Depends(get_settings)):
            ...
    """
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


# ============================================================================
# 6. ERROR TRACKING MIDDLEWARE
# ============================================================================

class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Catch unhandled exceptions, log structured error context, and return
    a consistent error response. In production, forward to Sentry or
    a similar service.

    Prevents raw stack traces from leaking to clients while preserving
    full context for debugging.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            # Build structured error context
            error_id = str(uuid.uuid4())
            error_context = {
                "error_id": error_id,
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client": request.client.host if request.client else None,
                "traceback": traceback.format_exc(),
            }

            logger.error(
                "Unhandled exception",
                extra={"extra_data": error_context},
            )

            # In production, send to Sentry:
            #   sentry_sdk.capture_exception(exc)

            # Return a safe error response -- never expose internals
            settings = get_settings()
            detail = str(exc) if settings.debug else "Internal server error"

            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "detail": detail,
                    "error_id": error_id,
                },
            )


# ============================================================================
# 7. METRICS COLLECTION (in-memory, no external dependencies)
# ============================================================================

@dataclass
class RequestMetric:
    count: int = 0
    total_duration_ms: float = 0.0
    error_count: int = 0


class MetricsCollector:
    """
    Simple in-memory request counter and timing collector.

    For production, replace with prometheus_client or OpenTelemetry metrics.
    This demonstrates the pattern without requiring external dependencies.
    """

    def __init__(self) -> None:
        # Keyed by (method, path, status_code)
        self._requests: dict[tuple[str, str, int], RequestMetric] = defaultdict(
            RequestMetric
        )
        self._start_time: float = time.time()

    def record(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        key = (method, path, status_code)
        metric = self._requests[key]
        metric.count += 1
        metric.total_duration_ms += duration_ms
        if status_code >= 500:
            metric.error_count += 1

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of current metrics."""
        uptime = time.time() - self._start_time
        total_requests = sum(m.count for m in self._requests.values())
        total_errors = sum(m.error_count for m in self._requests.values())

        endpoints: list[dict[str, Any]] = []
        for (method, path, status_code), metric in sorted(self._requests.items()):
            avg_ms = (
                metric.total_duration_ms / metric.count if metric.count > 0 else 0
            )
            endpoints.append({
                "method": method,
                "path": path,
                "status": status_code,
                "count": metric.count,
                "avg_duration_ms": round(avg_ms, 2),
                "errors": metric.error_count,
            })

        return {
            "uptime_seconds": round(uptime, 1),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(total_errors / max(total_requests, 1), 4),
            "endpoints": endpoints,
        }


# Global metrics collector instance
metrics = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request count and duration for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        metrics.record(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


# ============================================================================
# APP ASSEMBLY -- Putting it all together
# ============================================================================

def create_app() -> FastAPI:
    """
    Application factory -- assembles all production patterns.

    This is the entry point for both uvicorn and gunicorn:
        uvicorn examples:app --factory
    or:
        app = create_app()
    """
    settings = get_settings()
    setup_logging(log_level=settings.log_level, json_output=settings.log_json)

    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
    )

    # Middleware is applied in reverse order (last added = first executed)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(ErrorTrackingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Health check routes
    app.include_router(health_router)

    # Metrics endpoint
    @app.get("/metrics", tags=["ops"])
    async def get_metrics() -> dict[str, Any]:
        return metrics.snapshot()

    # Example application endpoint
    @app.get("/", tags=["app"])
    async def root() -> dict[str, str]:
        logger.info("Root endpoint called")
        return {"service": settings.app_name, "status": "running"}

    return app


# Create the app instance for `uvicorn examples:app`
app = create_app()


# ============================================================================
# DOCKERFILE EXAMPLES (as strings -- reference for production builds)
# ============================================================================

DOCKERFILE_SIMPLE = """\
# === Simple multi-stage Dockerfile for FastAPI ===
FROM python:3.12-slim AS builder

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim

# Create non-root user (security best practice)
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /install /usr/local
COPY . /app
WORKDIR /app

USER appuser
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

DOCKERFILE_UV = """\
# === Production Dockerfile with uv (recommended) ===
FROM python:3.12-slim AS builder

# Install uv -- Rust-based package manager, 10-100x faster than pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Layer 1: Dependencies (cached unless lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml

# Layer 2: Application code (changes frequently)
COPY . /app

FROM python:3.12-slim

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

WORKDIR /app
USER appuser
EXPOSE 8000

# Use gunicorn with uvicorn workers in production
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100"]
"""

DOCKERIGNORE = """\
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
"""


# ============================================================================
# TEST / DEMO
# ============================================================================

def _demo() -> None:
    """
    Run a quick demo showing the assembled app.

    Usage:
        python examples.py          (prints config and Dockerfiles)
        uvicorn examples:app        (runs the full app on port 8000)
    """
    print("=== Production Deployment Examples ===\n")

    # Show settings
    settings = get_settings()
    print("Settings:")
    print(json.dumps(settings.model_dump(), indent=2, default=str))
    print()

    # Show metrics snapshot (empty on startup)
    print("Metrics snapshot:")
    print(json.dumps(metrics.snapshot(), indent=2))
    print()

    # Show Dockerfile
    print("--- Dockerfile (uv) ---")
    print(DOCKERFILE_UV)

    print("--- .dockerignore ---")
    print(DOCKERIGNORE)

    print("\nTo run the full app:")
    print("  uvicorn examples:app --reload --port 8000")
    print("  curl http://localhost:8000/healthz")
    print("  curl http://localhost:8000/readyz")
    print("  curl http://localhost:8000/metrics")


if __name__ == "__main__":
    _demo()
