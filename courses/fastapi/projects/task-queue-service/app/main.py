"""FastAPI application entry point for the Async Task Queue Service.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.middleware import setup_middleware
from app.queue import task_queue
from app.routes import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage startup and shutdown of the background task worker."""
    task_queue.start()
    print("Task queue worker started")
    yield
    await task_queue.stop()
    print("Task queue worker stopped")


app = FastAPI(
    title="Async Task Queue Service",
    description=(
        "An in-memory async task queue with priority support, "
        "SSE progress streaming, and concurrency control."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware & system routes (/health, /metrics)
setup_middleware(app)

# Task routes (/tasks/...)
app.include_router(tasks_router)
