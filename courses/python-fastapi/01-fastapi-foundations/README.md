# Module 01: FastAPI Foundations

## Prerequisites

You should be comfortable with Python 3.10+ syntax (type hints, dataclasses, decorators) and have
production experience with Express/Node.js. This module maps FastAPI concepts to Express patterns
you already know, then goes far beyond them.

---

## 1. Request/Response Lifecycle vs Express Middleware

In Express, a request flows through a flat middleware chain where each calls `next()`. FastAPI
sits on Starlette (ASGI) and uses an onion model:

1. **ASGI server** (Uvicorn) receives the raw HTTP connection
2. **Middleware stack** processes the request (outermost to innermost)
3. **Router** resolves the path operation
4. **Dependency injection** resolves all `Depends()` parameters (recursively)
5. **Request validation** via Pydantic models
6. **Path operation function** executes
7. **Response serialization** via `response_model`
8. **Middleware stack** processes the response (innermost to outermost)
9. **Background tasks** execute after the response is sent

```python
from fastapi import FastAPI, Request
import time

app = FastAPI()

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    response.headers["X-Process-Time"] = str(elapsed)
    return response
```

Key difference: Express middleware is a flat chain where you call `next()`. Starlette middleware
is an onion -- your code runs before AND after `call_next()`, giving you request/response
interception in a single function.

---

## 2. Path Operations and Decorators

```python
from fastapi import FastAPI, Path, Query, Body, Header, Cookie

app = FastAPI()

# Express equivalent: app.get('/items/:item_id', handler)
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}

# All available: @app.get, .post, .put, .patch, .delete, .options, .head, .trace
# Multiple methods: @app.api_route("/path", methods=["GET", "POST"])
```

### Decorator Parameters

```python
@app.post(
    "/items",
    response_model=ItemResponse,       # Pydantic model for response serialization
    status_code=201,                    # default status code
    tags=["items"],                     # OpenAPI grouping
    summary="Create an item",          # OpenAPI summary
    responses={409: {"description": "Item already exists"}},
    deprecated=False,
    operation_id="create_item",
    include_in_schema=True,
)
async def create_item(item: ItemCreate):
    ...
```

---

## 3. Dependency Injection with `Depends`

This is the biggest conceptual shift from Express. Instead of composing middleware, you compose
dependencies -- functions whose return values are injected into your handler.

### Basic Dependencies

```python
from fastapi import Depends, HTTPException

async def get_current_user(token: str = Header(..., alias="Authorization")):
    user = await verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user

@app.get("/me")
async def read_current_user(user: User = Depends(get_current_user)):
    return user
```

### Recursive Dependencies

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session

async def get_current_user(
    token: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    user = await db.execute(select(User).where(User.token == token))
    return user.scalar_one_or_none()

async def get_admin_user(
    current_user: User = Depends(get_current_user),  # recursive!
) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not an admin")
    return current_user

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),  # resolves entire chain
    db: AsyncSession = Depends(get_db),     # same instance (cached per request)
):
    ...
```

### Yield Dependencies (Cleanup / Teardown)

```python
async def get_db():
    db = AsyncSession()
    try:
        yield db          # value injected into handler
        await db.commit()  # runs after handler succeeds
    except Exception:
        await db.rollback()  # runs if handler raises
        raise
    finally:
        await db.close()   # always runs
```

### Dependency Scopes and Classes

```python
# Router-level: applied to all routes in the router
router = APIRouter(dependencies=[Depends(verify_api_key)])

# App-level: applied to all routes
app = FastAPI(dependencies=[Depends(rate_limiter)])

# Class dependency: Depends() with no arg uses the type annotation
class Pagination:
    def __init__(self, skip: int = Query(0, ge=0), limit: int = Query(100, le=1000)):
        self.skip = skip
        self.limit = limit

@app.get("/items")
async def list_items(pagination: Pagination = Depends()):
    return await get_items(skip=pagination.skip, limit=pagination.limit)
```

---

## 4. Pydantic v2 Models

Pydantic v2 is a complete rewrite with a Rust core. Think Zod + class-transformer + json-schema
combined, but more deeply integrated.

### Basic Models

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Widget"])
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0, description="Price in USD")
    tags: list[str] = Field(default_factory=list)

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)  # enables ORM mode
```

### Field Validators and Model Validators

```python
from pydantic import field_validator, model_validator

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    password_confirm: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("must be alphanumeric")
        return v.lower()

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

    @model_validator(mode="after")
    def check_dates(self) -> "DateRange":
        if self.start_date >= self.end_date:
            raise ValueError("end_date must be after start_date")
        return self

    @model_validator(mode="before")
    @classmethod
    def preprocess(cls, values: dict) -> dict:
        """Runs before field validation -- receives raw input."""
        return values
```

### Computed Fields and Custom Types

```python
from pydantic import computed_field
from typing import Annotated
from pydantic import AfterValidator, BeforeValidator, PlainSerializer

class Order(BaseModel):
    items: list[OrderItem]
    tax_rate: float = 0.08

    @computed_field
    @property
    def total(self) -> float:
        subtotal = sum(i.price * i.quantity for i in self.items)
        return subtotal * (1 + self.tax_rate)

# Custom types via Annotated
def check_positive(v: int) -> int:
    if v <= 0:
        raise ValueError("must be positive")
    return v

PositiveInt = Annotated[int, AfterValidator(check_positive)]

# Serialization control
user.model_dump(exclude={"hashed_password"})
user.model_dump(exclude_none=True)
user.model_dump(mode="json")  # JSON-compatible types
```

---

## 5. Settings Management with pydantic-settings

Replaces `dotenv` + manual `process.env`. Gives you typed, validated configuration.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",         # APP_DATABASE_URL -> database_url
        env_nested_delimiter="__",  # APP_DB__HOST -> db.host
        case_sensitive=False,
    )
    database_url: str              # required -- crashes on startup if missing
    secret_key: SecretStr          # hidden in logs/repr
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Validates on startup -- if `DATABASE_URL` is missing, the app crashes immediately with a clear
error instead of failing at runtime.

---

## 6. Automatic OpenAPI / Swagger Generation

Every path operation, Pydantic model, and dependency contributes to an auto-generated
OpenAPI 3.1 schema. No Swagger decorators or YAML files needed.

```python
app = FastAPI(
    title="My API",
    version="1.0.0",
    docs_url="/docs",             # Swagger UI
    redoc_url="/redoc",           # ReDoc
    openapi_url="/openapi.json",  # raw schema
)

# Disable in production
app = FastAPI(
    docs_url=None if not settings.debug else "/docs",
    redoc_url=None if not settings.debug else "/redoc",
)
```

---

## 7. Path Parameters, Query Parameters, and Request Body

```python
from fastapi import Path, Query, Body

# Path params with validation
@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(
    user_id: int = Path(..., gt=0),
    post_id: int = Path(..., gt=0),
):
    return {"user_id": user_id, "post_id": post_id}

# Query params
@app.get("/items")
async def list_items(
    category: str = Query(..., min_length=1),     # required
    skip: int = Query(0, ge=0),                   # optional with default
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None),             # optional
    tags: list[str] = Query(default=[]),           # list: ?tag=a&tag=b
):
    ...

# Request body
class ItemCreate(BaseModel):
    name: str
    price: float

@app.post("/items")
async def create_item(item: ItemCreate):
    ...

# Multiple body params
@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: ItemCreate,
    importance: int = Body(..., gt=0),
):
    # Expected body: {"item": {...}, "importance": 5}
    ...
```

---

## 8. Response Models and Status Codes

```python
from fastapi import status
from fastapi.responses import JSONResponse, Response

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    db_user = User(**user.model_dump())
    return db_user  # FastAPI serializes through UserResponse, stripping extra fields

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int):
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Common codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized,
403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests.

---

## 9. Background Tasks

Fire-and-forget operations that run after the response is sent.

```python
from fastapi import BackgroundTasks

def send_welcome_email(email: str, name: str):
    print(f"Sending welcome email to {email}")

@app.post("/users", status_code=201)
async def create_user(user: UserCreate, background_tasks: BackgroundTasks):
    db_user = await create_user_in_db(user)
    background_tasks.add_task(send_welcome_email, user.email, user.name)
    return db_user  # response sent immediately, tasks run after
```

For heavier work, use Celery, ARQ, or a task queue.

---

## 10. Middleware

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com", "*.example.com"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response
```

**Ordering gotcha**: Middleware is applied in reverse order of declaration. The last
`add_middleware` call is outermost (first to execute).

---

## 11. Exception Handlers

```python
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

class ItemNotFoundError(Exception):
    def __init__(self, item_id: int):
        self.item_id = item_id

@app.exception_handler(ItemNotFoundError)
async def item_not_found_handler(request: Request, exc: ItemNotFoundError):
    return JSONResponse(status_code=404, content={"detail": f"Item {exc.item_id} not found"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"errors": exc.errors(), "body": exc.body})
```

---

## 12. Lifespan Events

Replaces the deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` decorators.

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    app.state.db_pool = await create_pool(settings.database_url)
    app.state.http_client = httpx.AsyncClient()
    yield  # Application runs here
    # SHUTDOWN
    await app.state.http_client.aclose()
    await app.state.db_pool.close()

app = FastAPI(lifespan=lifespan)

async def get_db_pool(request: Request):
    return request.app.state.db_pool
```

Express equivalent is scattered across `process.on('SIGTERM', ...)` and module-level globals.

---

## 13. Routers and Application Structure

```python
# app/routers/items.py
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(verify_api_key)],
)

@router.get("/")
async def list_items():
    ...

# app/main.py
from app.routers import items, users, auth
app = FastAPI()
app.include_router(items.router)
app.include_router(users.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
```

### Production App Layout

```
app/
  main.py            config.py           dependencies.py     exceptions.py
  models/            schemas/            routers/            services/
tests/               alembic/            pyproject.toml      .env
```

---

## Interview Questions

### Conceptual

1. **How does FastAPI's dependency injection differ from Express middleware?**
   Dependencies are explicit, typed, composable, and form a DAG. They are declared in function
   signatures and resolved recursively. Express middleware is a flat chain that mutates
   `req`/`res` -- implicit, untyped, order-dependent.

2. **What happens when two dependencies both use `Depends(get_db)` in the same request?**
   FastAPI caches per request using the callable as the cache key -- they get the same instance.
   Use `Depends(get_db, use_cache=False)` to force separate instances.

3. **Explain `response_model` vs a return type annotation.**
   `response_model` controls actual serialization and OpenAPI docs. A return type annotation is
   just an IDE hint. FastAPI uses `response_model` to filter response data.

4. **How do you handle cleanup in FastAPI dependencies?**
   Use `yield` dependencies. Before yield = setup, after yield = teardown. Wrap in
   try/except/finally. Use `lifespan` for app-level startup/shutdown.

5. **What is `model_validator(mode="before")`?**
   Runs before field validation on raw input. Use for preprocessing or normalizing input formats.

### Coding Challenges

6. **Implement a rate-limiting dependency** -- 100 req/min per API key, raises HTTP 429.

7. **Create a generic paginated response model** with `items`, `total`, `page`, `per_page`,
   and computed `total_pages`:
   ```python
   from typing import Generic, TypeVar
   from pydantic import BaseModel, computed_field
   import math

   T = TypeVar("T")
   class PaginatedResponse(BaseModel, Generic[T]):
       items: list[T]
       total: int
       page: int
       per_page: int

       @computed_field
       @property
       def total_pages(self) -> int:
           return math.ceil(self.total / self.per_page)
   ```

8. **Write a yield dependency** that provides a database transaction with proper
   commit/rollback semantics, composing with `get_current_user`.

### System Design

9. **How would you structure a FastAPI app with 50+ endpoints?**
   APIRouters per resource, shared dependency module, service layer, separate Pydantic schemas
   for create/update/response, router-level auth dependencies, tags for OpenAPI grouping.

10. **Compare FastAPI validation with Express + Zod.**
    FastAPI integrates validation into function signatures via Pydantic. Errors auto-return 422.
    Express requires manual middleware and custom error handling. FastAPI is less boilerplate,
    fully typed, and auto-documented.

---

## Key Takeaways

- `Depends` replaces most Express middleware patterns with explicit, typed, testable functions.
- Pydantic v2 handles validation, serialization, and OpenAPI schema in one model.
- Lifespan events provide clean application-scoped resource management.
- Everything in your function signature contributes to automatic OpenAPI docs.
- The framework validates at startup, so errors surface early rather than at runtime.
