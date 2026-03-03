# 03 – Middleware, ASGI, and Advanced Patterns

## Middleware Basics

Middleware intercepts every request before it reaches a handler and every response before it
leaves the application.

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

### Built-in Middleware

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Last added = outermost = runs first
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com", "*.example.com"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Custom middleware via decorator
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response
```

**Ordering gotcha**: Middleware is applied in reverse order of declaration. The last
`add_middleware` call is outermost (first to execute on requests, last on responses).

---

## ASGI: The Foundation

FastAPI is built on Starlette, which implements the ASGI specification.

### What ASGI Is

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

---

## ASGI vs WSGI

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

## Custom Middleware Implementation

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

## Background Tasks

Fire-and-forget operations that run after the response is sent to the client.

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

For heavier work, use Celery, ARQ, or a dedicated task queue. Background tasks share the same
process and event loop — they are not suitable for CPU-intensive or long-running work.

---

## Exception Handlers

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

## OpenAPI Customization

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

## Sub-Applications and Mounting

Mount independent ASGI apps under a path prefix. Each has its own docs, middleware, and lifespan.

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

## Interview Questions

### Conceptual

**1. How does FastAPI's dependency injection differ from Express middleware?**

Dependencies are explicit, typed, composable, and form a DAG. They are declared in function
signatures and resolved recursively. Express middleware is a flat chain that mutates `req`/`res`
— implicit, untyped, order-dependent.

**2. What happens when two dependencies both use `Depends(get_db)` in the same request?**

FastAPI caches per request using the callable as the cache key — they get the same instance.
Use `Depends(get_db, use_cache=False)` to force separate instances.

**3. Explain `response_model` vs a return type annotation.**

`response_model` controls actual serialization and OpenAPI docs. A return type annotation is
just an IDE hint. FastAPI uses `response_model` to filter response data.

**4. How do you handle cleanup in FastAPI dependencies?**

Use `yield` dependencies. Before yield = setup, after yield = teardown. Wrap in
try/except/finally. Use `lifespan` for app-level startup/shutdown.

**5. What is `model_validator(mode="before")`?**

Runs before field validation on raw input. Use for preprocessing or normalizing input formats.

**6. What is the difference between `BaseHTTPMiddleware` and pure ASGI middleware?**

`BaseHTTPMiddleware` is simpler to write but reads the entire response body into memory (breaking
streaming), creates a new task per request, and can interfere with background tasks. Pure ASGI
middleware wraps the `send` callable and never buffers the full response — it is suitable for
production streaming APIs.

**7. How would you structure a FastAPI app with 50+ endpoints?**

APIRouters per resource, shared dependency module, service layer, separate Pydantic schemas
for create/update/response, router-level auth dependencies, tags for OpenAPI grouping.

**8. Compare FastAPI validation with Express + Zod.**

FastAPI integrates validation into function signatures via Pydantic. Errors auto-return 422.
Express requires manual middleware and custom error handling. FastAPI is less boilerplate,
fully typed, and auto-documented.

### Coding Challenges

**9. Implement a rate-limiting dependency** — 100 req/min per API key, raises HTTP 429.

**10. Create a generic paginated response model** with `items`, `total`, `page`, `per_page`,
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

**11. Write a yield dependency** that provides a database transaction with proper
commit/rollback semantics, composing with `get_current_user`.

---

## Key Takeaways

- Starlette provides the ASGI foundation; FastAPI adds DI, validation, and OpenAPI on top.
- Pure ASGI middleware outperforms `BaseHTTPMiddleware` for production use.
- ASGI enables native WebSocket, streaming, and HTTP/2 that WSGI cannot provide.
- Sub-applications allow independent modules with their own docs and middleware.
- Background tasks run after the response is sent — use a task queue for heavy workloads.
- Exception handlers let you return structured errors for any exception type.
