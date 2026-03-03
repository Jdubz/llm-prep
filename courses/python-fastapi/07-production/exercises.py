"""
Production Deployment Exercises

Practice building production-ready patterns for FastAPI services.
Each exercise provides a skeleton with TODOs -- implement the missing logic.

Dependencies: fastapi, pydantic, and Python standard library only.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# EXERCISE 1: Health Check Endpoint with Database Verification
# ============================================================================
#
# READ FIRST:
#   02-configuration-logging-and-observability.md -> "Health Checks and Readiness Probes"
#   01-docker-and-deployment.md -> "Kubernetes Deployment" (probe YAML config)
#
# ALSO SEE:
#   examples.py -> Section 2: "HEALTH CHECK ENDPOINTS" for a complete
#   working implementation with liveness + readiness + dependency checks.
#
# Build health check endpoints that Kubernetes or a load balancer can use
# to determine whether this instance should receive traffic.
#
# Key concepts:
#   - Liveness: "Is the process alive?" (fast, no dependency checks)
#     A liveness probe answers "is the process stuck or deadlocked?"
#     If liveness fails, the orchestrator RESTARTS the container.
#     It must be trivially fast -- just return {"status": "alive"}.
#     NEVER check databases, caches, or external services here.
#     If you do, a database outage would restart all your pods,
#     which makes the problem worse (thundering herd on reconnect).
#
#   - Readiness: "Can it handle requests?" (checks DB, cache, etc.)
#     A readiness probe answers "should this pod receive traffic?"
#     If readiness fails, the load balancer REMOVES the pod from
#     the pool (but does NOT restart it). This is correct behavior:
#     the pod stays up and retries when the dependency recovers.
#     Check each critical dependency (DB, cache, etc.) with a
#     lightweight query (e.g., "SELECT 1") and aggregate results.
#     Return 200 if ALL checks pass, 503 if ANY check fails.
#
#   - Return 503 when not ready so the load balancer routes around us.
# ============================================================================

class FakeDatabase:
    """Simulates a database connection for exercise purposes."""

    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def execute(self, query: str) -> list[dict[str, Any]]:
        await asyncio.sleep(0.01)
        if not self.healthy:
            raise ConnectionError("Database connection refused")
        return [{"result": 1}]


# Shared database instance (toggle .healthy for testing)
db = FakeDatabase(healthy=True)


async def liveness_check() -> dict[str, str]:
    """
    Liveness probe -- is the process running?

    This should be trivially fast and NEVER check external dependencies.
    If liveness fails, the orchestrator will restart the container.

    Returns:
        {"status": "alive"}
    """
    # TODO: Return a simple alive status.
    # This should be a one-liner. No database checks, no IO.
    pass


async def readiness_check() -> tuple[dict[str, Any], int]:
    """
    Readiness probe -- can we handle traffic?

    Check that the database is reachable by running a lightweight query.
    Return the check results and an appropriate HTTP status code.

    Returns:
        (body_dict, status_code)

    When healthy:
        ({"status": "ready", "checks": {"database": "ok"}}, 200)

    When unhealthy:
        ({"status": "not_ready", "checks": {"database": "error: ..."}}, 503)
    """
    checks: dict[str, str] = {}

    # TODO: Implement database health check
    # 1. Try to execute "SELECT 1" on the db
    # 2. On success: checks["database"] = "ok"
    # 3. On exception: checks["database"] = f"error: {str(e)}"
    pass

    # TODO: Determine overall health status
    # 1. Check if all values in `checks` equal "ok"
    # 2. Set status_code to 200 if all healthy, 503 otherwise
    # 3. Return ({"status": "ready"|"not_ready", "checks": checks}, status_code)
    pass


# ============================================================================
# EXERCISE 2: Structured Logging Middleware
# ============================================================================
#
# READ FIRST:
#   02-configuration-logging-and-observability.md -> "Structured Logging with structlog"
#   02-configuration-logging-and-observability.md -> "Request ID Propagation"
#
# ALSO SEE:
#   examples.py -> Section 1: "STRUCTURED LOGGING" for the JSONFormatter and
#   setup_logging patterns.
#   examples.py -> Section 4: "REQUEST/RESPONSE LOGGING MIDDLEWARE" for a
#   complete working middleware with request ID, timing, and active request
#   tracking.
#
# Build middleware that logs every request with structured data:
#   method, path, status code, and duration in milliseconds.
#
# Key concepts:
#   - Use contextvars for request ID propagation across async boundaries.
#     Python's `contextvars` module is the async-safe equivalent of Node.js
#     AsyncLocalStorage. A ContextVar value set in one coroutine is visible
#     to all coroutines spawned from it, but NOT to unrelated requests.
#     Pattern:
#       request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
#       request_id_var.set("abc-123")   # set for this request
#       request_id_var.get()            # read from any downstream async code
#
#   - Time requests with time.perf_counter() for high precision.
#     time.perf_counter() uses the highest-resolution clock available
#     (monotonic, not affected by system clock changes). Pattern:
#       start = time.perf_counter()
#       # ... do work ...
#       duration_ms = (time.perf_counter() - start) * 1000
#
#   - Produce JSON-formatted log output for log aggregators.
#     In production, structlog or a custom logging.Formatter produces
#     one JSON object per log line. Log aggregators (Datadog, ELK,
#     CloudWatch) parse JSON natively. The stdlib approach:
#       logging.config.dictConfig({
#           "formatters": {"json": {"()": "myapp.JSONFormatter"}},
#           "handlers": {"stdout": {"formatter": "json", "class": "logging.StreamHandler"}},
#           "root": {"handlers": ["stdout"], "level": "INFO"},
#       })
#     Or with structlog (see MD file for full setup):
#       structlog.configure(processors=[...JSONRenderer()])
# ============================================================================

# Context variable for propagating request ID through async call chains.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("exercises")


class StructuredLogRecord(BaseModel):
    """Schema for a single structured log entry."""
    timestamp: float
    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float


# Collect log records here so tests can inspect them.
captured_logs: list[StructuredLogRecord] = []


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs request method, path, status code, and duration.

    Requirements:
    1. Generate a UUID request ID (or read from X-Request-Id header)
    2. Store it in request_id_var so downstream code can access it
    3. Time the request using time.perf_counter()
    4. After the response, build a StructuredLogRecord and append to captured_logs
    5. Set the X-Request-Id response header
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # TODO: Step 1 -- Get or generate request ID
        # Check request.headers for "x-request-id"; fall back to uuid.uuid4()
        req_id = ""

        # TODO: Step 2 -- Set the context variable
        # Use request_id_var.set(req_id) so all async code in this request
        # can access the request ID without passing it explicitly.

        # TODO: Step 3 -- Record start time
        start = 0

        # TODO: Step 4 -- Call the next handler
        response = await call_next(request)

        # TODO: Step 5 -- Calculate duration in milliseconds
        duration_ms = 0.0

        # TODO: Step 6 -- Create a StructuredLogRecord and append to captured_logs
        # Fields: timestamp, request_id, method, path, status_code, duration_ms

        # TODO: Step 7 -- Set X-Request-Id header on the response
        # response.headers["x-request-id"] = req_id

        return response


# ============================================================================
# EXERCISE 3: Graceful Shutdown with In-Flight Request Tracking
# ============================================================================
#
# READ FIRST:
#   01-docker-and-deployment.md -> "Graceful Shutdown" for the lifespan pattern
#   01-docker-and-deployment.md -> "Kubernetes Deployment" for how
#   terminationGracePeriodSeconds interacts with graceful shutdown
#
# ALSO SEE:
#   examples.py -> Section 3: "GRACEFUL SHUTDOWN WITH LIFESPAN EVENTS" for
#   a complete lifespan context manager with connection draining.
#   examples.py -> Section 4: "REQUEST/RESPONSE LOGGING MIDDLEWARE" shows
#   _active_requests tracking integrated into the middleware.
#
# When a container receives SIGTERM, we must:
#   1. Stop accepting new requests
#   2. Wait for in-flight requests to complete (up to a timeout)
#   3. Close resources (DB pools, caches)
#   4. Exit cleanly
#
# Key concepts:
#   - FastAPI lifespan context manager for startup/shutdown.
#     The lifespan replaces the old @app.on_event("startup") / "shutdown"
#     decorators. It is an async context manager:
#       @asynccontextmanager
#       async def app_lifespan(app: FastAPI):
#           # STARTUP: initialize DB pools, warm caches, etc.
#           yield
#           # SHUTDOWN: drain requests, close pools, flush buffers
#     Pass it to FastAPI: FastAPI(lifespan=app_lifespan)
#
#   - Track active request count atomically.
#     Use a simple counter (increment before call_next, decrement in
#     a try/finally after). In CPython, += and -= on ints are atomic
#     under the GIL. For multi-process setups, each worker tracks its
#     own count independently.
#
#   - Drain with a timeout to prevent hanging forever.
#     During shutdown, poll active_requests in a loop (e.g., every 0.1s).
#     If it doesn't reach 0 within a timeout (e.g., 10s), log a warning
#     and proceed with shutdown. In Kubernetes, set
#     terminationGracePeriodSeconds > your drain timeout so K8s doesn't
#     SIGKILL the pod before graceful shutdown finishes.
# ============================================================================

@dataclass
class ShutdownState:
    """Tracks application state for graceful shutdown."""
    active_requests: int = 0
    is_shutting_down: bool = False
    startup_complete: bool = False
    shutdown_complete: bool = False


shutdown_state = ShutdownState()


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """
    Lifespan context manager with graceful shutdown and connection draining.

    Startup (before yield):
        1. Initialize resources (simulate with a log message)
        2. Set shutdown_state.startup_complete = True

    Shutdown (after yield):
        1. Set shutdown_state.is_shutting_down = True
        2. Wait for active_requests to reach 0 (poll every 0.1s)
        3. Enforce a maximum drain timeout of 10 seconds
        4. Set shutdown_state.shutdown_complete = True
    """
    # TODO: STARTUP
    # 1. Log "Starting up"
    # 2. Mark startup_complete = True

    yield  # <-- Application runs between startup and shutdown

    # TODO: SHUTDOWN
    # 1. Set is_shutting_down = True
    # 2. Log "Shutting down, draining connections"
    # 3. Wait in a loop: while active_requests > 0, sleep 0.1s
    #    Break after 10 seconds to avoid hanging forever
    # 4. Set shutdown_complete = True
    # 5. Log "Shutdown complete"
    pass


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Track active in-flight requests for graceful shutdown.

    Requirements:
    1. If shutdown_state.is_shutting_down is True, return 503 immediately
    2. Increment shutdown_state.active_requests before processing
    3. Decrement it after processing (even on exception -- use try/finally)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # TODO: Check if we are shutting down
        # If yes, return JSONResponse with status 503 and
        # {"error": "service_unavailable", "detail": "Server is shutting down"}

        # TODO: Increment active_requests

        try:
            response = await call_next(request)
            return response
        finally:
            pass
            # TODO: Decrement active_requests


# ============================================================================
# EXERCISE 4: Configuration Class with Validation
# ============================================================================
#
# READ FIRST:
#   02-configuration-logging-and-observability.md -> "Configuration Management
#   with pydantic-settings" for the full BaseSettings pattern with env loading,
#   secrets, and the singleton get_settings() function.
#
# ALSO SEE:
#   examples.py -> Section 5: "CONFIGURATION MANAGEMENT WITH PYDANTIC
#   BASESETTINGS" for a complete AppSettings class with Field constraints
#   and the singleton pattern.
#
# Build a typed, validated configuration class using pydantic BaseModel.
# This is the Python equivalent of dotenv + zod validation in Node.js.
#
# Key concepts:
#   - Type-safe configuration with automatic validation.
#     pydantic validates types and constraints at instantiation time.
#     If any value is invalid, you get a clear ValidationError listing
#     every failing field -- the app never starts in a broken state.
#
#   - Default values for optional settings.
#     Fields with a default are optional (callers don't need to supply them).
#     Fields WITHOUT a default are required -- omitting them raises an error.
#
#   - Constraints via Field(...) for bounds and patterns.
#     Examples of Field() validators you will use:
#       port: int = Field(default=8000, ge=1, le=65535)
#       environment: str = Field(default="development",
#                                pattern="^(development|staging|production)$")
#       jwt_secret: str = Field(min_length=32)
#       workers: int = Field(default=1, ge=1, le=32)
#     ge = greater-or-equal, le = less-or-equal, min_length = minimum string
#     length, pattern = regex the value must match.
#
#   - Singleton pattern so config is loaded once.
#     Use a module-level variable to cache the config instance:
#       _config: ServiceConfig | None = None
#       def get_config() -> ServiceConfig:
#           global _config
#           if _config is None:
#               _config = ServiceConfig(...)
#           return _config
#     In production with pydantic-settings, use @lru_cache instead:
#       from functools import lru_cache
#       @lru_cache
#       def get_settings() -> Settings:
#           return Settings()  # loads from env vars automatically
# ============================================================================

class ServiceConfig(BaseModel):
    """
    Application configuration with validation.

    Implement Field constraints for each setting. When used with
    pydantic_settings.BaseSettings, values load from environment
    variables automatically.

    Requirements:
        app_name:        str, default "my-service"
        environment:     str, must be one of "development", "staging", "production"
                         (use Field pattern regex)
        debug:           bool, default False
        port:            int, default 8000, must be between 1 and 65535
        workers:         int, default 1, must be between 1 and 32
        database_url:    str, no default (required)
        db_pool_size:    int, default 5, must be between 1 and 50
        log_level:       str, default "INFO"
        jwt_secret:      str, minimum length 32
        jwt_expire_mins: int, default 30, must be >= 1
    """

    # TODO: Define all fields with appropriate types, defaults, and constraints.
    # Use Field(...) for validation:
    #   Field(default=..., ge=..., le=...) for numeric bounds
    #   Field(default=..., pattern="^...$") for string patterns
    #   Field(default=..., min_length=...) for minimum string length
    pass


# TODO: Implement a get_config() function that returns a cached singleton.
# Use a module-level variable (_config: ServiceConfig | None = None)
# to cache the instance. Build the ServiceConfig with placeholder values
# on first call, return the cached instance on subsequent calls.
#
# def get_config() -> ServiceConfig:
#     ...


# ============================================================================
# EXERCISE 5: Request Rate Metrics Collector
# ============================================================================
#
# READ FIRST:
#   02-configuration-logging-and-observability.md -> "Prometheus Metrics" for
#   production-grade Counter/Histogram/Gauge patterns.
#   02-configuration-logging-and-observability.md -> "Key Metrics to Track"
#   for what to monitor (the RED method: Rate, Errors, Duration).
#   03-performance-and-scaling.md -> "Profiling Middleware" for timing patterns.
#
# ALSO SEE:
#   examples.py -> Section 7: "METRICS COLLECTION" for a complete
#   MetricsCollector class with record(), snapshot(), and the MetricsMiddleware
#   that wires it into every request.
#
# Build a simple in-memory metrics collector that tracks:
#   - Request count per (method, path)
#   - Total and average response time per (method, path)
#   - Error count (status >= 500)
#
# Implementation guide:
#   - Use a dict keyed by (method, path) tuples mapping to EndpointMetric
#     dataclass instances. defaultdict(EndpointMetric) makes this easy --
#     missing keys auto-create a zeroed-out metric.
#   - record() updates the metric for a given endpoint: bump count, add
#     duration, and conditionally bump error_count if status >= 500.
#   - get_summary() aggregates across all endpoints: sum up total_requests
#     and total_errors, compute uptime from the start time, and return a
#     list of per-endpoint stats.
#   - In production, replace this with prometheus_client (Counter, Histogram,
#     Gauge) or OpenTelemetry metrics -- they handle concurrent access,
#     aggregation, and export to monitoring backends (Prometheus, Datadog).
# ============================================================================

@dataclass
class EndpointMetric:
    """Metrics for a single (method, path) combination."""
    request_count: int = 0
    total_duration_ms: float = 0.0
    error_count: int = 0

    @property
    def avg_duration_ms(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_duration_ms / self.request_count


class RateMetricsCollector:
    """
    Collects per-endpoint request rate and timing metrics.

    Methods to implement:
        record(method, path, status_code, duration_ms):
            Update the metrics for the given endpoint.

        get_summary() -> dict:
            Return a JSON-serializable summary of all metrics.

        get_endpoint(method, path) -> EndpointMetric | None:
            Return metrics for a specific endpoint, or None.
    """

    def __init__(self) -> None:
        # TODO: Initialize storage.
        # Use a dict keyed by (method, path) mapping to EndpointMetric.
        # Also store the collector start time for uptime calculation.
        pass

    def record(
        self, method: str, path: str, status_code: int, duration_ms: float
    ) -> None:
        """
        Record a single request.

        1. Look up or create an EndpointMetric for (method, path)
        2. Increment request_count
        3. Add duration_ms to total_duration_ms
        4. If status_code >= 500, increment error_count
        """
        # TODO: Implement
        pass

    def get_endpoint(self, method: str, path: str) -> EndpointMetric | None:
        """Return the EndpointMetric for a specific endpoint, or None."""
        # TODO: Implement
        pass

    def get_summary(self) -> dict[str, Any]:
        """
        Return a summary of all collected metrics.

        Format:
        {
            "uptime_seconds": float,
            "total_requests": int,
            "total_errors": int,
            "endpoints": [
                {
                    "method": str,
                    "path": str,
                    "count": int,
                    "avg_duration_ms": float,
                    "errors": int,
                },
                ...
            ]
        }
        """
        # TODO: Implement
        pass


# ============================================================================
# TESTS
# ============================================================================

def test_exercise_1():
    """Test health check endpoints."""
    print("\n=== EXERCISE 1: Health Checks ===")

    # Test liveness
    result = asyncio.run(liveness_check())
    assert result == {"status": "alive"}, f"Expected alive, got {result}"
    print("Liveness check: PASS")

    # Test readiness (healthy)
    db.healthy = True
    body, code = asyncio.run(readiness_check())
    assert code == 200, f"Expected 200, got {code}"
    assert body["checks"]["database"] == "ok", f"Expected ok, got {body}"
    print(f"Readiness check (healthy): PASS -- {body}")

    # Test readiness (unhealthy)
    db.healthy = False
    body, code = asyncio.run(readiness_check())
    assert code == 503, f"Expected 503, got {code}"
    assert "error" in body["checks"]["database"], f"Expected error, got {body}"
    print(f"Readiness check (unhealthy): PASS -- {body}")

    db.healthy = True  # Reset


def test_exercise_2():
    """Test structured logging middleware (unit-level check)."""
    print("\n=== EXERCISE 2: Structured Logging Middleware ===")

    # We test the StructuredLogRecord schema directly
    record = StructuredLogRecord(
        timestamp=time.time(),
        request_id="test-123",
        method="GET",
        path="/api/users",
        status_code=200,
        duration_ms=42.5,
    )
    assert record.method == "GET"
    assert record.duration_ms == 42.5
    print(f"Log record schema: PASS -- {record.model_dump_json()}")

    # Test context variable propagation
    request_id_var.set("ctx-test-456")
    assert request_id_var.get() == "ctx-test-456"
    print("Context variable propagation: PASS")

    print(
        "\nFull middleware test requires running the app:"
        "\n  uvicorn exercises:test_app --port 8001"
        "\n  curl -v http://localhost:8001/"
    )


def test_exercise_3():
    """Test graceful shutdown state tracking."""
    print("\n=== EXERCISE 3: Graceful Shutdown ===")

    # Reset state
    shutdown_state.active_requests = 0
    shutdown_state.is_shutting_down = False
    shutdown_state.startup_complete = False
    shutdown_state.shutdown_complete = False

    # Simulate startup
    assert not shutdown_state.startup_complete
    print("Initial state: startup_complete=False -- PASS")

    # Simulate active request tracking
    shutdown_state.active_requests += 1
    assert shutdown_state.active_requests == 1
    shutdown_state.active_requests -= 1
    assert shutdown_state.active_requests == 0
    print("Request tracking increment/decrement: PASS")

    # Simulate shutdown flag
    shutdown_state.is_shutting_down = True
    assert shutdown_state.is_shutting_down
    print("Shutdown flag: PASS")

    print(
        "\nFull shutdown test requires running the app and sending SIGTERM."
    )


def test_exercise_4():
    """Test configuration validation."""
    print("\n=== EXERCISE 4: Configuration ===")

    # Check that ServiceConfig has fields defined
    if not ServiceConfig.model_fields:
        print("SKIP -- ServiceConfig fields not yet implemented")
        return

    # Test valid config
    try:
        config = ServiceConfig(
            database_url="postgresql+asyncpg://localhost/test",
            jwt_secret="a" * 32,
        )
        print(f"Valid config created: PASS -- app_name={config.app_name}")
    except Exception as e:
        print(f"Valid config creation failed: {e}")
        return

    # Test invalid environment
    try:
        ServiceConfig(
            database_url="postgresql+asyncpg://localhost/test",
            jwt_secret="a" * 32,
            environment="invalid_env",
        )
        print("Invalid environment accepted: FAIL (should have raised)")
    except Exception:
        print("Invalid environment rejected: PASS")

    # Test jwt_secret too short
    try:
        ServiceConfig(
            database_url="postgresql+asyncpg://localhost/test",
            jwt_secret="short",
        )
        print("Short JWT secret accepted: FAIL (should have raised)")
    except Exception:
        print("Short JWT secret rejected: PASS")

    # Test port out of range
    try:
        ServiceConfig(
            database_url="postgresql+asyncpg://localhost/test",
            jwt_secret="a" * 32,
            port=99999,
        )
        print("Invalid port accepted: FAIL (should have raised)")
    except Exception:
        print("Invalid port rejected: PASS")


def test_exercise_5():
    """Test metrics collector."""
    print("\n=== EXERCISE 5: Rate Metrics Collector ===")

    collector = RateMetricsCollector()

    # Record some requests
    collector.record("GET", "/api/users", 200, 45.2)
    collector.record("GET", "/api/users", 200, 52.1)
    collector.record("GET", "/api/users", 500, 120.3)
    collector.record("POST", "/api/users", 201, 88.7)

    # Check endpoint metrics
    users_metric = collector.get_endpoint("GET", "/api/users")
    if users_metric is None:
        print("SKIP -- get_endpoint not yet implemented")
        return

    assert users_metric.request_count == 3, (
        f"Expected 3 requests, got {users_metric.request_count}"
    )
    print(f"Request count: PASS -- {users_metric.request_count}")

    assert users_metric.error_count == 1, (
        f"Expected 1 error, got {users_metric.error_count}"
    )
    print(f"Error count: PASS -- {users_metric.error_count}")

    expected_avg = (45.2 + 52.1 + 120.3) / 3
    assert abs(users_metric.avg_duration_ms - expected_avg) < 0.1, (
        f"Expected avg ~{expected_avg:.1f}, got {users_metric.avg_duration_ms:.1f}"
    )
    print(f"Average duration: PASS -- {users_metric.avg_duration_ms:.1f}ms")

    # Check summary
    summary = collector.get_summary()
    if summary is None:
        print("SKIP -- get_summary not yet implemented")
        return

    assert summary["total_requests"] == 4, (
        f"Expected 4 total, got {summary['total_requests']}"
    )
    print(f"Summary total requests: PASS -- {summary['total_requests']}")
    print(f"Full summary: {json.dumps(summary, indent=2)}")


# ============================================================================
# TEST APP (for manual integration testing)
# ============================================================================

def create_test_app() -> FastAPI:
    """
    Assemble an app with the exercise middleware for manual testing.

    Run with:
        uvicorn exercises:test_app --port 8001
    """
    test_application = FastAPI(title="Exercise Test App", lifespan=app_lifespan)

    test_application.add_middleware(RequestTrackingMiddleware)
    test_application.add_middleware(LoggingMiddleware)

    @test_application.get("/healthz")
    async def health():
        return await liveness_check()

    @test_application.get("/readyz")
    async def ready(response: Response):
        body, code = await readiness_check()
        response.status_code = code
        return body

    @test_application.get("/")
    async def root():
        return {"message": "hello from exercise test app"}

    return test_application


test_app = create_test_app()


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    test_exercise_1()
    test_exercise_2()
    test_exercise_3()
    test_exercise_4()
    test_exercise_5()

    print("\n" + "=" * 60)
    print("All implemented exercises passed!")
    print("=" * 60)


"""
LEARNING OBJECTIVES CHECKLIST

After completing these exercises, you should be comfortable with:

Health Checks:
- [ ] Difference between liveness and readiness probes
- [ ] Why liveness should never check external dependencies
- [ ] Returning appropriate HTTP status codes (200 vs 503)
- [ ] Structuring health check response bodies

Structured Logging:
- [ ] Using contextvars for async-safe request ID propagation
- [ ] Timing requests with time.perf_counter()
- [ ] Producing JSON-structured log output
- [ ] Attaching metadata (method, path, status, duration) to log entries

Graceful Shutdown:
- [ ] FastAPI lifespan context manager (startup + shutdown)
- [ ] Tracking in-flight requests atomically
- [ ] Connection draining with a timeout
- [ ] Rejecting new requests during shutdown (503)

Configuration Management:
- [ ] Typed, validated config with pydantic BaseModel
- [ ] Field constraints (ge, le, min_length, pattern)
- [ ] Singleton pattern for config loading
- [ ] How pydantic-settings loads from environment variables

Metrics Collection:
- [ ] Counting requests per endpoint
- [ ] Recording response time distributions
- [ ] Tracking error rates
- [ ] Producing a JSON-serializable metrics summary
"""
