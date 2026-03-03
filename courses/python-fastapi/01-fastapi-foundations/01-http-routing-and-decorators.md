# 01 – HTTP Routing and Decorators

## Prerequisites

You should be comfortable with Python 3.10+ syntax (type hints, dataclasses, decorators) and have
production experience with Express/Node.js. This module maps FastAPI concepts to Express patterns
you already know, then goes far beyond them.

---

## The Request/Response Lifecycle

In Express, a request flows through a flat middleware chain where each handler calls `next()`.
FastAPI sits on Starlette (ASGI) and uses an onion model:

1. **ASGI server** (Uvicorn) receives the raw HTTP connection
2. **Middleware stack** processes the request (outermost to innermost)
3. **Router** resolves the path operation
4. **Dependency injection** resolves all `Depends()` parameters (recursively)
5. **Request validation** via Pydantic models
6. **Path operation function** executes
7. **Response serialization** via `response_model`
8. **Middleware stack** processes the response (innermost to outermost)
9. **Background tasks** execute after the response is sent

Key difference: Express middleware is a flat chain where you call `next()`. Starlette middleware
is an onion — your code runs before AND after `call_next()`, giving you request/response
interception in a single function.

---

## Path Operations and Decorators

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

Every parameter on the decorator contributes to the auto-generated OpenAPI schema:

```python
from fastapi import FastAPI, APIRouter, Depends, Query, Path, Body, Header, Cookie
from fastapi import HTTPException, status, BackgroundTasks, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI()

# HTTP Methods
@app.get("/path")
@app.post("/path", status_code=201)
@app.put("/path")
@app.patch("/path")
@app.delete("/path", status_code=204)

# Full decorator signature
@app.post(
    "/items",
    response_model=ItemResponse,       # Pydantic model for response serialization
    status_code=201,                    # default status code
    tags=["items"],                     # OpenAPI grouping
    summary="Create an item",           # OpenAPI summary
    responses={409: {"description": "Item already exists"}},
    deprecated=False,
    operation_id="create_item",
    include_in_schema=True,
    dependencies=[Depends(auth)],
)
async def create_item(item: ItemCreate):
    ...
```

---

## Parameter Extraction

FastAPI inspects function parameter types and their default value factories to determine where
each value comes from. The rule: if the type is a Pydantic model, it's the request body; otherwise
the source is determined by the default value annotation.

```python
async def handler(item_id: int = Path(..., gt=0)):           # /items/{item_id}
async def handler(skip: int = Query(0, ge=0)):               # ?skip=0
async def handler(tags: list[str] = Query(default=[])):      # ?tag=a&tag=b
async def handler(item: ItemCreate):                          # JSON body
async def handler(name: str = Body(...)):                     # body field
async def handler(x_token: str = Header(...)):                # header
async def handler(session_id: str = Cookie(None)):            # cookie
```

### Path Parameters with Validation

```python
from fastapi import Path, Query, Body

# Path params with validation
@app.get("/users/{user_id}/posts/{post_id}")
async def get_user_post(
    user_id: int = Path(..., gt=0),
    post_id: int = Path(..., gt=0),
):
    return {"user_id": user_id, "post_id": post_id}
```

### Query Parameters

```python
@app.get("/items")
async def list_items(
    category: str = Query(..., min_length=1),     # required
    skip: int = Query(0, ge=0),                   # optional with default
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None),             # optional
    tags: list[str] = Query(default=[]),           # list: ?tag=a&tag=b
):
    ...
```

### Request Body

```python
class ItemCreate(BaseModel):
    name: str
    price: float

@app.post("/items")
async def create_item(item: ItemCreate):
    ...

# Multiple body params — FastAPI wraps them in a dict
@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: ItemCreate,
    importance: int = Body(..., gt=0),
):
    # Expected body: {"item": {...}, "importance": 5}
    ...
```

### Route Order Matters

Routes are matched in declaration order. More specific routes must come before generic ones:

```python
@app.get("/users/me")       # must come first
async def read_user_me(): ...
@app.get("/users/{user_id}")  # would match "me" as a user_id otherwise
async def read_user(user_id: int): ...
```

---

## Pydantic v2 Models

Pydantic v2 is a complete rewrite with a Rust core. Think Zod + class-transformer + json-schema
combined, but more deeply integrated. It handles validation, serialization, and OpenAPI schema
generation from a single model definition.

### Basic Model Template

```python
from pydantic import BaseModel, Field, ConfigDict, field_validator, computed_field
from datetime import datetime
from typing import Optional

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0, description="Price in USD")
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        return v.strip() or (_ for _ in ()).throw(ValueError("blank"))

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(None, gt=0)

class ItemResponse(ItemBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)  # enables ORM mode

    @computed_field
    @property
    def display_price(self) -> str:
        return f"${self.price:.2f}"
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

`mode="before"` runs on raw input before any field coercion. `mode="after"` runs after all
fields are validated and the model instance is built.

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

## Response Models and Status Codes

`response_model` controls actual serialization and OpenAPI documentation. A return type annotation
is just an IDE hint. FastAPI uses `response_model` to filter response data, meaning fields on the
returned object that are not in `response_model` are stripped.

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

### Common Status Codes Reference

```python
status.HTTP_200_OK                    # GET/PUT/PATCH success
status.HTTP_201_CREATED               # POST (resource created)
status.HTTP_204_NO_CONTENT            # DELETE success
status.HTTP_400_BAD_REQUEST           # client error
status.HTTP_401_UNAUTHORIZED          # not authenticated
status.HTTP_403_FORBIDDEN             # not authorized
status.HTTP_404_NOT_FOUND             # resource missing
status.HTTP_409_CONFLICT              # duplicate
status.HTTP_422_UNPROCESSABLE_ENTITY  # validation error
status.HTTP_429_TOO_MANY_REQUESTS     # rate limited
```

Common codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized,
403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests.

---

## Routers and Application Structure

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

## Settings Management with pydantic-settings

Replaces `dotenv` + manual `process.env`. Gives you typed, validated configuration that crashes
immediately at startup if required values are missing — rather than failing at runtime.

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

---

## Automatic OpenAPI / Swagger Generation

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

## Express-to-FastAPI Translation

| Express | FastAPI |
|---------|---------|
| `app.use(middleware)` | `app.add_middleware(Cls)` |
| `app.get('/path', handler)` | `@app.get("/path")` |
| `express.Router()` | `APIRouter()` |
| `app.use('/prefix', router)` | `app.include_router(router, prefix="/prefix")` |
| `req.params.id` | `item_id: int` (path param) |
| `req.query.page` | `page: int = Query(1)` |
| `req.body` | `item: ItemCreate` (Pydantic model) |
| `req.headers['x-token']` | `x_token: str = Header(...)` |
| `res.status(201).json(data)` | `return data` + `status_code=201` |
| `next()` | `await call_next(request)` |
| `process.env.DB_URL` | `Settings().database_url` |

---

## FastAPI vs Django REST Framework vs Flask

| Feature | Flask | DRF | FastAPI |
|---------|-------|-----|---------|
| Async native | No | Partial | Yes |
| Type hints driven | No | No | Yes |
| Auto API docs | No | Limited | OpenAPI 3.1 |
| Validation | Manual (marshmallow) | Serializers | Pydantic |
| Dependency injection | No | Implicit (mixins) | Explicit (Depends) |
| Performance | Low | Low-Medium | High |
| Learning curve | Low | High | Medium |

**Choose Flask** for prototypes or maximum flexibility without async needs.
**Choose DRF** when you need Django's admin panel or are already on Django.
**Choose FastAPI** for new projects needing performance, type safety, and auto-docs.

---

## Key Takeaways

- Every function parameter contributes to automatic OpenAPI documentation.
- Pydantic v2 handles validation, serialization, and OpenAPI schema from a single model.
- `response_model` filters response data and generates OpenAPI output schemas.
- Route order matters — more specific paths must come before generic ones.
- Settings management via `pydantic-settings` validates configuration at startup.
