# Module 01 Deep Dive: FastAPI Internals and Ecosystem

## 1. Starlette Internals

FastAPI is built on Starlette, which implements the ASGI specification.

### ASGI: The Interface

An ASGI application is a callable with this signature:

```python
async def app(scope: dict, receive: Callable, send: Callable) -> None:
    """
    scope:   dict describing the connection (type, path, headers, etc.)
    receive: awaitable to receive incoming messages (request body chunks)
    send:    awaitable to send outgoing messages (response headers, body chunks)
    """
```

Three scope types: `http`, `websocket`, `lifespan`. Here is a raw ASGI app:

```python
async def raw_asgi_app(scope, receive, send):
    if scope["type"] == "http":
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200,
                     "headers": [[b"content-type", b"application/json"]]})
        await send({"type": "http.response.body", "body": b'{"hello": "world"}'})
```

### The Middleware Stack (Onion Model)

```
Request  -->  [Middleware 1]  -->  [Middleware 2]  -->  [Router]  -->  [Handler]
Response <--  [Middleware 1]  <--  [Middleware 2]  <--  [Router]  <--  [Handler]
```

At the ASGI level, each middleware wraps an inner ASGI app:

```python
class TimingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Process-Time", str(time.perf_counter() - start))
            await send(message)
        await self.app(scope, receive, send_wrapper)
```

### Routing

Routes are matched in declaration order. More specific routes must come before generic ones:

```python
@app.get("/users/me")       # must come first
async def read_user_me(): ...
@app.get("/users/{user_id}")  # would match "me" as a user_id otherwise
async def read_user(user_id: int): ...
```

---

## 2. FastAPI vs Django REST Framework vs Flask

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

## 3. ASGI vs WSGI

WSGI (PEP 3333, 2003) is synchronous and blocking. ASGI is its async successor.

| Aspect | WSGI | ASGI |
|--------|------|------|
| Concurrency | Thread/process per request | Event loop |
| WebSocket | No | Yes |
| HTTP/2 | Limited | Yes |
| Streaming | Difficult | Native |
| Servers | Gunicorn, uWSGI | Uvicorn, Hypercorn |

### Production Deployment

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production: Gunicorn manages Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Gunicorn handles process management (spawning, health checks, restarts); Uvicorn handles
the async event loop within each worker.

---

## 4. Custom Middleware Implementation

### Pure ASGI Middleware (Most Performant)

```python
from starlette.types import ASGIApp, Receive, Scope, Send

class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        start = time.perf_counter()
        status_code = 500
        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start
            print(f"{request.method} {request.url.path} -> {status_code} ({elapsed:.3f}s)")
```

### BaseHTTPMiddleware (Simpler but Limited)

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SimpleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if not request.headers.get("X-API-Key"):
            return JSONResponse(status_code=401, content={"detail": "Missing API key"})
        response = await call_next(request)
        response.headers["X-Custom-Header"] = "value"
        return response
```

**Warning**: `BaseHTTPMiddleware` reads the entire response into memory (no streaming),
creates a new task per request, and can break background tasks. Prefer pure ASGI middleware
for production.

---

## 5. OpenAPI Customization

```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(title="My API", version="2.0.0", routes=app.routes)
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

Security schemes auto-document in Swagger UI:

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
security = HTTPBearer()

@app.get("/protected")
async def protected(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    ...
```

Hide routes: `@app.get("/internal", include_in_schema=False)` or set on the router.

---

## 6. Dependency Overrides for Testing

Replace any dependency with a mock at the app level -- one of FastAPI's most powerful
testing features.

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

## 7. Sub-Applications and Mounting

Mount independent ASGI apps under a path prefix. Each has its own docs, middleware, and
lifespan.

```python
main_app = FastAPI(title="Main API")
admin_app = FastAPI(title="Admin API")
admin_app.add_middleware(AdminAuthMiddleware)

@admin_app.get("/dashboard")
async def admin_dashboard():
    return {"stats": "..."}

main_app.mount("/admin", admin_app)  # /admin/docs has its own Swagger UI

# Static files
from starlette.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### API Versioning Strategies

```python
# Strategy 1: Sub-applications (major versions)
app.mount("/v1", v1_app)
app.mount("/v2", v2_app)

# Strategy 2: Router prefixes (minor differences)
app.include_router(items_v1_router, prefix="/v1")
app.include_router(items_v2_router, prefix="/v2")

# Strategy 3: Header-based (via dependency)
async def get_api_version(accept: str = Header("application/json")):
    return 2 if "version=2" in accept else 1
```

---

## 8. Advanced Dependency Patterns

### Parameterized Dependencies (Factories)

```python
def require_role(role: str):
    async def role_checker(user: User = Depends(get_current_user)):
        if role not in user.roles:
            raise HTTPException(status_code=403, detail=f"Role '{role}' required")
        return user
    return role_checker

@app.delete("/users/{user_id}", dependencies=[Depends(require_role("admin"))])
async def delete_user(user_id: int): ...
```

### Context-Aware Dependencies

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

## Summary

- Starlette provides the ASGI foundation; FastAPI adds DI, validation, and OpenAPI on top.
- Pure ASGI middleware outperforms `BaseHTTPMiddleware` for production use.
- `dependency_overrides` makes FastAPI apps trivially testable.
- Sub-applications allow independent modules with their own docs and middleware.
- ASGI enables native WebSocket, streaming, and HTTP/2 that WSGI cannot provide.
