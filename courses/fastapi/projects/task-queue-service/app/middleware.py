"""Request logging middleware and metrics for the Async Task Queue Service."""

import time
from typing import Any

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class RequestMetrics:
    """Simple in-memory request metrics collector."""

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.total_duration_ms: float = 0.0
        self.status_counts: dict[int, int] = {}

    @property
    def avg_duration_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_duration_ms / self.total_requests

    def record(self, status_code: int, duration_ms: float) -> None:
        self.total_requests += 1
        self.total_duration_ms += duration_ms
        self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "status_counts": dict(self.status_counts),
        }


# Module-level singleton
metrics = RequestMetrics()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status code, and duration."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000.0

        metrics.record(response.status_code, duration_ms)

        # Simple structured log line to stdout
        print(
            f"{request.method} {request.url.path} "
            f"-> {response.status_code} ({duration_ms:.1f}ms)"
        )
        return response


def setup_middleware(app: FastAPI) -> None:
    """Attach middleware and utility routes to the app."""
    app.add_middleware(LoggingMiddleware)

    @app.get("/health", tags=["system"])
    async def health_check() -> dict[str, Any]:
        """Liveness / readiness probe."""
        return {"status": "healthy"}

    @app.get("/metrics", tags=["system"])
    async def get_metrics() -> dict[str, Any]:
        """Return basic request metrics."""
        return metrics.snapshot()
