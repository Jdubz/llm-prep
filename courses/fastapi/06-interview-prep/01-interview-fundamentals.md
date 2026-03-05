# 01 – FastAPI Interview Fundamentals

> **Prerequisite**: For Python language questions (GIL, decorators, async/await, memory model, etc.), see [Python Interview Fundamentals](../../python/04-interview-prep/01-interview-fundamentals.md).

---

## FastAPI-Specific Questions

### F1: How does FastAPI's dependency injection work?

FastAPI uses a function-based DI system. Dependencies are declared as function parameters with `Depends()`:

```python
from fastapi import Depends

async def get_db():
    async with async_session() as session:
        yield session  # Cleanup happens after the response

async def get_current_user(
    token: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await authenticate(token, db)

@app.get("/orders")
async def list_orders(
    user: User = Depends(get_current_user),  # Depends on get_current_user
    db: AsyncSession = Depends(get_db),       # Same db session (cached per-request)
):
    return await get_user_orders(user.id, db)
```

**vs NestJS**: NestJS uses class-based DI with decorators and a container. FastAPI's DI is simpler — just functions and `Depends()`. Dependencies are resolved per-request and can use `yield` for cleanup (like context managers).

### F2: Middleware vs Dependencies — when to use which?

| Feature | Middleware | Dependencies |
|---------|-----------|-------------|
| Scope | Every request | Specific endpoints |
| Access to | Raw ASGI scope, request/response | Function parameters, type hints |
| Use case | Logging, CORS, compression, metrics | Auth, DB sessions, pagination params |
| Error handling | Must handle manually | FastAPI's exception handlers work |
| Performance | Runs even for 404s | Only runs for matched routes |

**Rule**: Use middleware for cross-cutting concerns that apply to all requests. Use dependencies for per-endpoint logic that needs type safety and testability.

### F3: What changed in Pydantic v2?

| Aspect | Pydantic v1 | Pydantic v2 |
|--------|-------------|-------------|
| Core | Pure Python | Rust-based (`pydantic-core`) |
| Speed | Baseline | 5-50x faster |
| Config | `class Config:` inner class | `model_config = ConfigDict(...)` |
| Validators | `@validator` | `@field_validator` / `@model_validator` |
| Serialization | `.dict()` / `.json()` | `.model_dump()` / `.model_dump_json()` |
| Strict mode | No | Yes — `strict=True` disables coercion |
| Computed fields | Workarounds | `@computed_field` decorator |

```python
# v2 style
from pydantic import BaseModel, field_validator, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    name: str
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()
```

### F4: Async vs sync endpoints — when to use which?

```python
# ASYNC — runs on the event loop (like Node.js)
@app.get("/async")
async def async_endpoint():
    result = await db.query(...)  # Non-blocking
    return result

# SYNC — runs in a thread pool (automatically!)
@app.get("/sync")
def sync_endpoint():
    result = db.query(...)  # Blocking call
    return result
```

**FastAPI automatically runs sync endpoints in a thread pool** so they don't block the event loop. Use `async def` when you have async dependencies (async DB drivers, httpx). Use plain `def` when calling blocking libraries.

**Gotcha**: Never do blocking IO inside an `async def` endpoint — it blocks the event loop.

### F5: How do you test FastAPI applications?

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_db

async def override_get_db():
    async with test_session() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

async def test_create_user(client: AsyncClient):
    response = await client.post("/users", json={"name": "Alice", "email": "a@b.com"})
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
```

**Key concept**: `dependency_overrides` is FastAPI's killer feature for testing. You can replace any dependency (database, auth, external services) without mocking internals.

### F6: Explain FastAPI's response model and serialization.

```python
class UserOut(BaseModel):
    id: int
    name: str
    email: str
    # Note: password is NOT included

@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: int):
    user = await db.get(User, user_id)  # Has password field
    return user  # FastAPI serializes using UserOut — password is stripped
```

`response_model` controls what's sent to the client. This is like a DTO pattern but enforced by the framework.

### F7: What is the ASGI lifecycle in FastAPI?

```
Request → ASGI Server (Uvicorn)
       → ASGI Middleware Stack
       → ServerErrorMiddleware
       → ExceptionMiddleware
       → Your middleware (CORS, logging, etc.)
       → Router
       → Dependency resolution
       → Path operation function
       → Response
```

FastAPI is an ASGI application. Uvicorn sends the request as an ASGI scope dict. Each middleware wraps the next. Dependencies are resolved after routing but before the endpoint function runs.

### F8: How do you handle background tasks?

```python
from fastapi import BackgroundTasks

@app.post("/orders")
async def create_order(order: OrderIn, background_tasks: BackgroundTasks):
    db_order = await save_order(order)

    # Runs AFTER the response is sent (not blocking the client)
    background_tasks.add_task(send_confirmation_email, db_order.email)
    background_tasks.add_task(update_inventory, db_order.items)

    return db_order
```

**Limitations**: Background tasks run in the same process. If the process crashes, the tasks are lost. For anything critical, use a proper task queue (Celery, ARQ, Dramatiq).

### F9: Django vs FastAPI Decision Matrix

| Feature | Django | FastAPI |
|---------|--------|---------|
| **Philosophy** | Batteries included | Minimal, composable |
| **ORM** | Built-in (Django ORM) | BYO (SQLAlchemy, Tortoise) |
| **Admin panel** | Built-in (powerful) | None (use SQLAdmin or build) |
| **Auth** | Built-in (users, sessions, permissions) | BYO |
| **Async support** | Partial (views, ORM queries in 4.1+) | Native, async-first |
| **Validation** | Django forms, DRF serializers | Pydantic (built-in) |
| **API docs** | Manual (DRF + drf-spectacular) | Automatic (OpenAPI/Swagger) |
| **Performance** | Moderate | High (Starlette + Pydantic v2 Rust core) |

**Choose Django when**: You need an admin panel, batteries-included auth, or a large ecosystem of packages.

**Choose FastAPI when**: Building a pure API, performance matters, you want automatic OpenAPI docs, or you're coming from TypeScript/Express — FastAPI feels more familiar.

---

## Practice Exercises

The following timed coding challenges in `exercises.py` test concepts covered in this file. Use them to practice under interview conditions.

| Exercise | Time | Concepts from this file |
|----------|------|------------------------|
| **Exercise 1: TODO API with CRUD + Filtering** | 15 min | Pydantic models (F3), Field validation, FastAPI route decorators (F1, F4), query parameter filtering, status codes |
| **Exercise 2: User Registration with Validation** | 15 min | `@field_validator` (F3), password hashing (F1 dependency injection), Bearer token auth (F1), `HTTPException` status codes |
| **Exercise 4: Debug Broken Code** | 10 min | Proper status codes, Pydantic validation, error handling patterns |
| **Exercise 5: Code Review** | 10 min | Security (plaintext passwords), Pydantic models (F3), route ordering, type hints, HTTP method semantics |

Exercises 3 (Rate Limiter) and 6 (Webhook Delivery) are covered in [02-system-design-and-code-review.md](02-system-design-and-code-review.md).

---

## Key Takeaways

- `dependency_overrides` in FastAPI is the correct way to inject test dependencies — don't monkeypatch.
- FastAPI automatically runs sync endpoints in a thread pool — don't use `async def` for blocking code.
- Pydantic v2's Rust core makes it 5-50x faster; use `@field_validator` (not `@validator`).
- Use middleware for cross-cutting concerns; use dependencies for per-endpoint logic.
- `response_model` strips fields not in the model — use it to protect sensitive data.
