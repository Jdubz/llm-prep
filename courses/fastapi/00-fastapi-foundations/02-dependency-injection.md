# 02 – Dependency Injection

## What Dependency Injection Is

This is the biggest conceptual shift from Express. Instead of composing middleware, you compose
dependencies — functions whose return values are injected into your handler. Dependencies are
declared in function signatures and resolved recursively by FastAPI before calling your handler.

Express middleware is a flat chain that mutates `req`/`res` — implicit, untyped, order-dependent.
FastAPI dependencies are explicit, typed, composable, and form a DAG (directed acyclic graph).
They are declared in function signatures and resolved recursively.

---

## Basic Dependencies

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

The dependency can be any callable: a function, async function, or class with `__call__`.
Its own parameters are resolved using the same FastAPI injection rules.

---

## Nested (Recursive) Dependencies

Dependencies can depend on other dependencies. FastAPI resolves the entire DAG before calling
your handler, and caches each dependency's result per request.

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

When two dependencies both call `Depends(get_db)` in the same request, FastAPI caches the
result using the callable as the cache key — they get the same session instance. Use
`Depends(get_db, use_cache=False)` to force separate instances.

---

## Yield Dependencies (Cleanup and Teardown)

Use `yield` to run cleanup logic after the handler finishes. This is how you implement the
database session pattern with proper commit/rollback semantics.

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

The pattern mirrors an async context manager. Before `yield` is setup; after `yield` is teardown.
The `try/except/finally` structure guarantees cleanup even when exceptions occur.

A cleaner version using the session factory's built-in context manager:

```python
async def get_db():
    async with session_factory() as session:
        yield session
```

---

## Class-Based Dependencies

Classes are callable, so they work as dependencies. FastAPI calls `__init__` with injected
parameters and the instance becomes the dependency value.

```python
class Pagination:
    def __init__(self, skip: int = Query(0, ge=0), limit: int = Query(100, le=1000)):
        self.skip = skip
        self.limit = limit

@app.get("/items")
async def list_items(pagination: Pagination = Depends()):
    # Depends() with no argument uses the type annotation (Pagination)
    return await get_items(skip=pagination.skip, limit=pagination.limit)
```

`Depends()` with no argument is shorthand for `Depends(Pagination)` when the type annotation
is a class.

---

## Dependency Scopes

Dependencies can be applied at three levels:

```python
# Route-level: only for this handler
@app.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    ...

# Router-level: applied to all routes in the router
router = APIRouter(dependencies=[Depends(verify_api_key)])

# App-level: applied to all routes
app = FastAPI(dependencies=[Depends(rate_limiter)])

# Override for testing
app.dependency_overrides[get_db] = override_get_db
```

Router-level and app-level dependencies run their setup/teardown but their return values are
not injected into the handler — they are used for side effects (auth checks, rate limiting).

---

## Parameterized Dependencies (Factories)

To create a dependency that accepts configuration, use a factory function that returns the
actual dependency:

```python
def require_role(role: str):
    async def role_checker(user: User = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user
    return role_checker

@app.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user(user_id: int): ...

# In cheat sheet form:
def require_role(role: str):
    async def checker(user=Depends(get_current_user)):
        if role not in user.roles: raise HTTPException(403)
        return user
    return checker
```

---

## Context-Aware Dependencies

Dependencies have access to the full `Request` object alongside other injected parameters:

```python
async def get_locale(
    request: Request,
    accept_language: str | None = Header(None),
) -> str:
    if query_locale := request.query_params.get("lang"):
        return query_locale
    if accept_language:
        return accept_language.split(",")[0].split(";")[0].strip()
    return "en"

async def get_translator(locale: str = Depends(get_locale)):
    return Translator(locale)
```

---

## Dependency Overrides for Testing

Replace any dependency with a mock at the app level. This is one of FastAPI's most powerful
testing features and requires zero mocking infrastructure.

```python
# tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_db, get_current_user

@pytest.fixture
async def async_client():
    async def override_get_db():
        async with test_session() as session:
            yield session

    async def override_get_current_user():
        return User(id=1, email="test@example.com", is_admin=False)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.mark.anyio
async def test_create_item(async_client: AsyncClient):
    response = await async_client.post("/items", json={"name": "Widget", "price": 9.99})
    assert response.status_code == 201
```

The Express equivalent requires manual module mocking with Jest or DI containers. FastAPI's
approach is built in and trivially simple.

---

## Lifespan Events

Replaces the deprecated `@app.on_event("startup")` / `@app.on_event("shutdown")` decorators.
The `lifespan` context manager pattern handles app-level resource management cleanly.

```python
from contextlib import asynccontextmanager
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

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

---

## Practice Exercises

The concepts in this document are tested in `exercises.py` in the same directory:

- **Exercise 2** (Dependency Chain): Build `get_app_config` and `get_book_store` as a chained
  dependency using `Depends()` and the yield pattern from the sections above.
- **Exercise 3** (CRUD Router): Inject the book store dependency into route handlers using
  `Depends(get_book_store)` in handler function signatures.

Also see `examples.py` section 2 for a complete 4-level dependency chain
(`get_settings` -> `get_db` -> `get_current_user` -> `require_admin`).

---

## Key Takeaways

- `Depends` replaces most Express middleware patterns with explicit, typed, testable functions.
- FastAPI caches dependencies per request by default; use `use_cache=False` for separate instances.
- Yield dependencies implement setup/teardown in a single function — use for DB sessions.
- Factory functions (`require_role("admin")`) create parameterized dependencies.
- `dependency_overrides` makes any FastAPI app trivially testable without mocking infrastructure.
- Lifespan events provide clean application-scoped resource management.
