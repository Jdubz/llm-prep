"""
FastAPI Foundations Examples

Complete, runnable production patterns covering CRUD, dependency injection,
exception handlers, lifespan events, response models, and router organization.
All examples are self-contained and demonstrate best practices.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Generic, TypeVar

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
    model_validator,
)


# ============================================================================
# 1. FULL CRUD APP WITH PYDANTIC MODELS
# ============================================================================
# Express equivalent: express.Router() + Joi/Zod + controller functions.
# FastAPI merges validation, serialization, and routing into one layer.

# --- Pydantic schemas: input vs output separation ---
# This is the FastAPI version of the "DTO pattern." You never expose your
# internal model directly -- you have separate Create, Update, and Response
# schemas so clients can't set fields like `id` or `created_at`.


class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class UserBase(BaseModel):
    """Shared fields for all user schemas."""
    username: str = Field(
        ..., min_length=3, max_length=32, pattern=r"^[a-z0-9_]+$",
        examples=["jane_doe"],
    )
    email: EmailStr = Field(..., examples=["jane@example.com"])
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.MEMBER


class UserCreate(UserBase):
    """What the client sends to POST /users."""
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Partial update -- all fields optional."""
    full_name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None
    role: UserRole | None = None


class UserResponse(UserBase):
    """What the API returns -- never includes the password."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- In-memory "database" for demonstration ---

_users_db: dict[uuid.UUID, dict[str, Any]] = {}


def _create_user_record(data: UserCreate) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid.uuid4(),
        "username": data.username,
        "email": data.email,
        "full_name": data.full_name,
        "role": data.role,
        "hashed_password": f"hashed_{data.password}",  # placeholder
        "created_at": now,
        "updated_at": now,
    }


# --- CRUD router ---
# Express equivalent: const router = express.Router(); router.get('/', ...)
# FastAPI's APIRouter groups related endpoints. Tags control OpenAPI grouping.

users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
)
async def create_user(payload: UserCreate) -> dict[str, Any]:
    """Create a user. FastAPI validates the body against UserCreate automatically.
    The response is serialized through UserResponse, stripping hashed_password."""
    # Express equivalent: req.body already validated by Zod middleware
    for user in _users_db.values():
        if user["username"] == payload.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{payload.username}' already taken",
            )

    record = _create_user_record(payload)
    _users_db[record["id"]] = record
    return record  # UserResponse filters out hashed_password


@users_router.get("/", response_model=list[UserResponse], summary="List users")
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return"),
    role: UserRole | None = Query(None, description="Filter by role"),
) -> list[dict[str, Any]]:
    """List users with pagination and optional role filter."""
    users = list(_users_db.values())
    if role is not None:
        users = [u for u in users if u["role"] == role]
    return users[skip : skip + limit]


@users_router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(user_id: uuid.UUID = Path(..., description="User UUID")) -> dict[str, Any]:
    if user_id not in _users_db:
        raise HTTPException(status_code=404, detail="User not found")
    return _users_db[user_id]


@users_router.patch("/{user_id}", response_model=UserResponse, summary="Update user")
async def update_user(
    payload: UserUpdate,
    user_id: uuid.UUID = Path(...),
) -> dict[str, Any]:
    if user_id not in _users_db:
        raise HTTPException(status_code=404, detail="User not found")

    record = _users_db[user_id]
    # model_dump(exclude_unset=True) gives us only the fields the client sent --
    # this is how PATCH semantics work with Pydantic.
    updates = payload.model_dump(exclude_unset=True)
    record.update(updates)
    record["updated_at"] = datetime.now(timezone.utc)
    return record


@users_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID = Path(...)) -> None:
    if user_id not in _users_db:
        raise HTTPException(status_code=404, detail="User not found")
    del _users_db[user_id]


# ============================================================================
# 2. DEPENDENCY INJECTION CHAIN
# ============================================================================
# Express equivalent: a chain of middleware that attaches req.settings,
# req.db, req.user. In FastAPI these are explicit, typed, testable functions
# wired via Depends(). The framework resolves the DAG for you.


class AppSettings(BaseModel):
    """Application configuration -- normally loaded from env via pydantic-settings."""
    database_url: str = "sqlite+aiosqlite:///./app.db"
    secret_key: str = "change-me-in-production"
    debug: bool = False


class FakeDBSession:
    """Simulates an async DB session for demonstration."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = False

    async def execute(self, query: str) -> list[dict[str, Any]]:
        return [{"id": 1, "username": "demo", "role": "admin"}]

    async def close(self) -> None:
        self.closed = True


class AuthenticatedUser(BaseModel):
    id: int
    username: str
    role: str


# Dependency 1: settings (cached for the app lifetime via lru_cache in real apps)
def get_settings() -> AppSettings:
    return AppSettings()


# Dependency 2: database session -- uses yield for cleanup
# Express equivalent: custom middleware that opens a DB connection, attaches to
# req, and closes it in a "finish" event listener. FastAPI's yield dependency
# is cleaner -- try/finally guarantees cleanup.
async def get_db(
    settings: AppSettings = Depends(get_settings),
) -> AsyncGenerator[FakeDBSession, None]:
    db = FakeDBSession(settings.database_url)
    try:
        yield db
    finally:
        await db.close()


# Dependency 3: authenticated user -- depends on the DB session
async def get_current_user(
    db: FakeDBSession = Depends(get_db),
) -> AuthenticatedUser:
    """In production this would decode a JWT from the Authorization header."""
    rows = await db.execute("SELECT * FROM users WHERE id = 1")
    if not rows:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return AuthenticatedUser(**rows[0])


# Dependency 4: admin-only guard -- depends on get_current_user
async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# Usage in an endpoint -- FastAPI resolves the full chain automatically:
# require_admin -> get_current_user -> get_db -> get_settings
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/dashboard")
async def admin_dashboard(
    admin: AuthenticatedUser = Depends(require_admin),
) -> dict[str, str]:
    return {"message": f"Welcome, {admin.username}. You have admin access."}


# ============================================================================
# 3. CUSTOM EXCEPTION HANDLERS WITH RFC 9457 PROBLEM DETAILS
# ============================================================================
# RFC 9457 (formerly RFC 7807) defines a standard JSON error format.
# Express equivalent: app.use((err, req, res, next) => ...) global error handler.
# FastAPI lets you register handlers per exception type -- more precise.


class AppError(Exception):
    """Base application error following RFC 9457 Problem Details."""

    def __init__(
        self,
        *,
        status_code: int = 500,
        error_type: str = "about:blank",
        title: str = "Internal Server Error",
        detail: str = "",
        instance: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_type = error_type
        self.title = title
        self.detail = detail
        self.instance = instance
        self.extensions = extensions or {}


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            status_code=404,
            error_type="/errors/not-found",
            title=f"{resource} Not Found",
            detail=f"{resource} with id '{resource_id}' does not exist.",
            extensions={"resource": resource, "resource_id": resource_id},
        )


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=409,
            error_type="/errors/conflict",
            title="Conflict",
            detail=detail,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Return RFC 9457 Problem Details JSON for application errors."""
    body: dict[str, Any] = {
        "type": exc.error_type,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
    }
    if exc.instance:
        body["instance"] = exc.instance
    body.update(exc.extensions)
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        media_type="application/problem+json",
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    """Override FastAPI's default 422 to use RFC 9457 format."""
    return JSONResponse(
        status_code=422,
        content={
            "type": "/errors/validation",
            "title": "Validation Error",
            "status": 422,
            "detail": "One or more fields failed validation.",
            "errors": [
                {
                    "field": " -> ".join(str(loc) for loc in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"],
                }
                for err in exc.errors()
            ],
        },
        media_type="application/problem+json",
    )


# ============================================================================
# 4. LIFESPAN EVENTS (STARTUP / SHUTDOWN)
# ============================================================================
# Express equivalent: process.on("SIGTERM", cleanup) and top-level await for
# connection pools. FastAPI's lifespan is an async context manager -- cleaner
# because setup and teardown live together.


class FakeConnectionPool:
    """Simulates an async connection pool (e.g., asyncpg)."""

    def __init__(self, url: str, min_size: int, max_size: int) -> None:
        self.url = url
        self.min_size = min_size
        self.max_size = max_size
        self.active = True

    async def close(self) -> None:
        self.active = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application-scoped resources."""
    # --- STARTUP ---
    settings = get_settings()
    pool = FakeConnectionPool(
        url=settings.database_url, min_size=5, max_size=20,
    )
    app.state.db_pool = pool
    app.state.request_count = 0
    print(f"[startup] Connection pool created ({pool.min_size}-{pool.max_size} connections)")

    yield  # --- APPLICATION RUNS HERE ---

    # --- SHUTDOWN ---
    await app.state.db_pool.close()
    print(f"[shutdown] Connection pool closed. Total requests served: {app.state.request_count}")


# ============================================================================
# 5. RESPONSE MODELS WITH FIELD EXCLUSION AND COMPUTED FIELDS
# ============================================================================


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response -- reusable for any resource.
    Express equivalent: you'd build this manually in every controller."""
    items: list[T]
    total: int
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)

    @computed_field
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total / self.per_page) if self.per_page else 0

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        return self.page > 1


class OrderItem(BaseModel):
    product_name: str
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)


class OrderResponse(BaseModel):
    """Demonstrates computed fields and field exclusion."""
    id: uuid.UUID
    customer_email: EmailStr
    items: list[OrderItem]
    tax_rate: float = 0.08
    internal_notes: str = Field(default="", exclude=True)  # never serialized

    @computed_field
    @property
    def subtotal(self) -> float:
        return sum(item.quantity * item.unit_price for item in self.items)

    @computed_field
    @property
    def tax(self) -> float:
        return round(self.subtotal * self.tax_rate, 2)

    @computed_field
    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 6. ROUTER ORGANIZATION EXAMPLE
# ============================================================================
# In production you split routers into separate files:
#   app/routers/users.py, app/routers/orders.py, etc.
# Here we show the wiring pattern in one file.

health_router = APIRouter(tags=["health"])


@health_router.get("/healthz", summary="Liveness probe")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get("/readyz", summary="Readiness probe")
async def readiness_check(request: Request) -> dict[str, Any]:
    pool = getattr(request.app.state, "db_pool", None)
    db_ok = pool is not None and pool.active
    return {
        "status": "ready" if db_ok else "not ready",
        "checks": {"database": "up" if db_ok else "down"},
    }


orders_router = APIRouter(prefix="/orders", tags=["orders"])


@orders_router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order by ID",
)
async def get_order(order_id: uuid.UUID) -> OrderResponse:
    """Demonstrates computed fields in the response model."""
    return OrderResponse(
        id=order_id,
        customer_email="customer@example.com",
        items=[
            OrderItem(product_name="Widget", quantity=3, unit_price=9.99),
            OrderItem(product_name="Gadget", quantity=1, unit_price=24.50),
        ],
        tax_rate=0.08,
        internal_notes="VIP customer - priority shipping",
    )


@orders_router.get(
    "/",
    response_model=PaginatedResponse[OrderResponse],
    summary="List orders (paginated)",
)
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[OrderResponse]:
    """Demonstrates the generic PaginatedResponse wrapper."""
    sample_order = OrderResponse(
        id=uuid.uuid4(),
        customer_email="demo@example.com",
        items=[OrderItem(product_name="Sample", quantity=1, unit_price=19.99)],
        internal_notes="internal only",
    )
    return PaginatedResponse(
        items=[sample_order],
        total=1,
        page=page,
        per_page=per_page,
    )


# ============================================================================
# APP ASSEMBLY
# ============================================================================
# This is the "main.py" pattern. Register routers, exception handlers,
# middleware, and lifespan in one place.

app = FastAPI(
    title="FastAPI Foundations Example",
    version="1.0.0",
    lifespan=lifespan,
)

# Register exception handlers
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

# Include routers -- order doesn't matter for routing, but tags appear in
# OpenAPI in the order they are first encountered.
app.include_router(health_router)
app.include_router(users_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


# A route that demonstrates the custom exception classes:
@app.get("/api/v1/demo-error/{resource_id}", tags=["demo"])
async def demo_error(resource_id: str) -> None:
    """Hit this endpoint to see the RFC 9457 error format in action."""
    raise NotFoundError(resource="Widget", resource_id=resource_id)


# ============================================================================
# RUN
# ============================================================================
# Start with:  uvicorn examples:app --reload
# Then visit:  http://localhost:8000/docs  (Swagger UI)
#
# Try these:
#   POST /api/v1/users        -- create a user (see validation)
#   GET  /api/v1/orders/{id}  -- see computed fields in response
#   GET  /api/v1/demo-error/x -- see RFC 9457 error format
#   GET  /api/v1/admin/dashboard -- see dependency chain
#   GET  /healthz             -- liveness probe
#   GET  /readyz              -- readiness probe with DB check
