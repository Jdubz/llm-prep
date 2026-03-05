"""
FastAPI application entry-point for the Bookmark API.

Covers course concepts from:
- Module 01: App creation, routers
- Module 03: Exception handlers, middleware
- Module 06: Lifespan events (startup/shutdown)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import bookmarks, users
from app.storage import storage

logger = logging.getLogger("bookmark_api")


# ---------------------------------------------------------------------------
# Lifespan -- runs once at startup and once at shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown hooks."""
    logger.info("Bookmark API starting up -- storage initialised")
    yield
    # Shutdown: clear in-memory data (optional; process is ending anyway)
    await storage.clear()
    logger.info("Bookmark API shut down -- storage cleared")


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Bookmark API",
    description="A link-saving REST API built with FastAPI.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Router includes
# ---------------------------------------------------------------------------

app.include_router(users.router)
app.include_router(bookmarks.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health_check():
    return {"status": "ok"}
