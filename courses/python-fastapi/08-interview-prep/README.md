# Module 08: Interview Prep

> The final module. Targeted questions, system design exercises, code review drills,
> and live coding patterns — all through the lens of a senior TypeScript engineer transitioning to Python/FastAPI.

---

## Table of Contents

1. [Python Backend Interview Questions](#python-backend-interview-questions)
2. [FastAPI-Specific Questions](#fastapi-specific-questions)
3. [System Design with FastAPI](#system-design-with-fastapi)
4. [Code Review Exercises](#code-review-exercises)
5. [Live Coding Patterns](#live-coding-patterns)

---

## Python Backend Interview Questions

### Q1: What is the GIL, and why does it matter for web services?

**A:** The Global Interpreter Lock is a mutex in CPython that allows only one thread to execute Python bytecode at a time. For web services, this means:

- **CPU-bound work**: Multiple threads cannot parallelize CPU work. Use `multiprocessing`, `ProcessPoolExecutor`, or offload to Celery workers.
- **IO-bound work**: The GIL is released during IO operations (`await`, network calls, file reads). Async FastAPI endpoints are largely unaffected because they spend most time waiting on IO, not executing Python bytecode.
- **The Node.js comparison**: Node.js is single-threaded by design and uses worker threads for CPU work. Python is similar in practice — the GIL makes threading behave like single-threaded for CPU, but the story is more nuanced because the GIL is released during IO and C-extension calls.

```python
# CPU-bound: GIL is a bottleneck — use ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor
import asyncio

async def cpu_heavy_endpoint():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        ProcessPoolExecutor(), compute_hash, large_data
    )
    return result
```

### Q2: How does Python's async/await differ from JavaScript's?

**A:** The syntax is nearly identical, but the runtime model differs:

| Aspect | JavaScript | Python |
|--------|-----------|--------|
| Event loop | Built into the runtime, always running | Must be explicitly started (`asyncio.run()`) |
| Concurrency model | Single event loop, everything is async-first | Sync by default, async is opt-in |
| `await` outside async | Top-level await (ES modules) | Only inside `async def` (no top-level) |
| Promises vs Coroutines | Promises start executing immediately | Coroutines are lazy — `await` triggers execution |
| `Promise.all()` | `await Promise.all([p1, p2])` | `await asyncio.gather(c1(), c2())` |
| Error handling | `.catch()` or `try/catch` | `try/except` only |

**Critical difference**: In JavaScript, `fetch()` returns a Promise that starts executing immediately. In Python, calling an `async def` function returns a coroutine object that does nothing until you `await` it.

```python
# This does NOTHING — the coroutine is created but not executed
coro = fetch_data()  # No network call happens

# This actually runs it
result = await fetch_data()
```

### Q3: Explain decorators — how do they work under the hood?

**A:** A decorator is syntactic sugar for wrapping a function. It's a function that takes a function and returns a function (usually).

```python
# This:
@my_decorator
def my_function():
    pass

# Is exactly equivalent to:
def my_function():
    pass
my_function = my_decorator(my_function)
```

The TypeScript equivalent is actual TC39 decorators (stage 3), but Python decorators are simpler — they're just higher-order functions.

```python
import functools
import time

def timing(func):
    """Decorator that logs execution time."""
    @functools.wraps(func)  # Preserves __name__, __doc__, etc.
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        print(f"{func.__name__} took {duration:.3f}s")
        return result
    return wrapper

# Decorator with arguments — needs an extra layer
def retry(max_attempts: int = 3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
        return wrapper
    return decorator

@retry(max_attempts=5)
def flaky_operation():
    ...
```

**Interview tip**: Always mention `@functools.wraps` — forgetting it means the wrapped function loses its name, docstring, and type hints. This is a common code review catch.

### Q4: What are context managers and why do they matter?

**A:** Context managers implement the `__enter__`/`__exit__` protocol (or `__aenter__`/`__aexit__` for async). They guarantee cleanup happens, even if exceptions occur. They're Python's equivalent of try/finally patterns, but more composable.

```python
# The pattern you know from TypeScript/Node.js:
// const conn = await pool.connect();
// try { ... } finally { conn.release(); }

# Python's context manager version:
async with pool.acquire() as conn:
    await conn.execute("SELECT 1")
# conn is automatically released here, even if an exception occurred

# Writing your own:
from contextlib import asynccontextmanager

@asynccontextmanager
async def timed_operation(name: str):
    start = time.perf_counter()
    try:
        yield  # The code inside `async with` runs here
    finally:
        duration = time.perf_counter() - start
        logger.info(f"{name} took {duration:.3f}s")

async with timed_operation("database_query"):
    result = await db.execute(query)
```

**Why interviewers ask this**: Context managers are used everywhere in Python — database sessions, file handles, locks, HTTP clients, transactions. Not using them (or using them wrong) is a red flag for resource leaks.

### Q5: Explain Python's memory model — reference counting + GC.

**A:** Python uses a dual strategy:

1. **Reference counting** (primary): Every object has a reference count. When it reaches 0, the object is immediately deallocated. This is deterministic — you know when cleanup happens.

2. **Generational garbage collector** (secondary): Handles circular references that reference counting can't detect.

```python
import sys

a = [1, 2, 3]
print(sys.getrefcount(a))  # 2 (a + the getrefcount argument)

b = a           # refcount = 3
del b           # refcount = 2
del a           # refcount = 0 → immediately freed

# Circular reference — reference counting can't free this
class Node:
    def __init__(self):
        self.ref = None

a = Node()
b = Node()
a.ref = b
b.ref = a    # Circular reference
del a, b     # refcount never reaches 0 — GC must collect
```

**vs JavaScript**: V8 uses a tracing garbage collector (mark-and-sweep with generational collection). Python's reference counting gives more predictable memory behavior but adds overhead to every assignment.

### Q6: What are metaclasses? When would you actually use one?

**A:** A metaclass is the "class of a class." Just as an object is an instance of a class, a class is an instance of a metaclass. The default metaclass is `type`.

```python
# These are equivalent:
class MyClass:
    x = 10

MyClass = type("MyClass", (), {"x": 10})
```

A custom metaclass intercepts class creation:

```python
class ValidatedMeta(type):
    def __new__(mcs, name, bases, namespace):
        # Enforce that all methods have docstrings
        for key, value in namespace.items():
            if callable(value) and not key.startswith("_"):
                if not value.__doc__:
                    raise TypeError(f"{name}.{key} must have a docstring")
        return super().__new__(mcs, name, bases, namespace)

class MyAPI(metaclass=ValidatedMeta):
    def get_users(self):
        """Fetch all users."""  # This is required
        pass
```

**When to use**: Almost never in application code. Metaclasses are used in frameworks — SQLAlchemy's declarative base, Django's models, Pydantic's BaseModel, and ABC (abstract base classes) all use metaclasses. In interviews, knowing they exist and what they do is enough. If your application code needs a metaclass, you probably want a class decorator or `__init_subclass__` instead.

### Q7: Explain descriptors.

**A:** Descriptors are objects that define `__get__`, `__set__`, or `__delete__`. They control attribute access on classes. They're the mechanism behind `@property`, `@classmethod`, `@staticmethod`, and ORMs.

```python
class Validated:
    """A descriptor that validates values on assignment."""
    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    def __set_name__(self, owner, name):
        self.name = name  # Automatically called — knows the attribute name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{self.name} must be >= {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self.name} must be <= {self.max_value}")
        obj.__dict__[self.name] = value

class Product:
    price = Validated(min_value=0)
    quantity = Validated(min_value=0, max_value=10000)

p = Product()
p.price = 29.99      # OK
p.price = -1         # ValueError: price must be >= 0
```

**Interview insight**: Pydantic fields are descriptors under the hood. Understanding descriptors explains how `model.field` returns a value, but `Model.field` returns field metadata.

### Q8: How does Python's packaging ecosystem work?

**A:** The mental model, mapped from Node.js:

| Node.js | Python | Purpose |
|---------|--------|---------|
| `package.json` | `pyproject.toml` | Project metadata + dependencies |
| `package-lock.json` | `uv.lock` / `poetry.lock` | Deterministic installs |
| `node_modules/` | `.venv/` | Isolated dependency storage |
| `npm` / `pnpm` | `uv` / `pip` / `poetry` | Package manager |
| `npx` | `uvx` / `pipx` | Run CLI tools without installing |
| `npm publish` | `uv publish` / `twine upload` | Publish to registry |
| npmjs.com | PyPI (pypi.org) | Package registry |

### Q9: What's the difference between `__str__` and `__repr__`?

**A:**
- `__repr__`: Unambiguous representation for developers. Should ideally be valid Python that recreates the object. Called by `repr()`, shown in debugger/REPL.
- `__str__`: Human-readable representation for end users. Called by `str()`, `print()`, f-strings.

```python
class Money:
    def __init__(self, amount, currency):
        self.amount = amount
        self.currency = currency

    def __repr__(self):
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self):
        return f"${self.amount:.2f} {self.currency}"

m = Money(42.5, "USD")
repr(m)   # "Money(42.5, 'USD')"
str(m)    # "$42.50 USD"
print(m)  # "$42.50 USD"
```

**Rule**: Always implement `__repr__`. Implement `__str__` only if you need a different user-facing format. If only `__repr__` is defined, `str()` falls back to it.

### Q10: Explain `*args` and `**kwargs` — what's actually happening?

**A:** They're unpacking operators for positional and keyword arguments:

```python
def func(*args, **kwargs):
    # args is a tuple of positional arguments
    # kwargs is a dict of keyword arguments
    print(args)    # (1, 2, 3)
    print(kwargs)  # {"x": 10, "y": 20}

func(1, 2, 3, x=10, y=20)

# The reverse — unpacking into a call:
data = {"host": "localhost", "port": 8000}
connect(**data)  # Same as connect(host="localhost", port=8000)
```

**The TypeScript analog**: Spread/rest operators (`...args`), but Python separates positional and keyword arguments, which TypeScript doesn't have.

### Q11: What are slots and when would you use them?

**A:** `__slots__` replaces the instance `__dict__` with a fixed-size array. Less memory, faster attribute access, but no dynamic attributes.

```python
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
p.z = 3  # AttributeError — no __dict__, can't add attributes

# Memory comparison:
# Regular class instance: ~152 bytes (dict overhead)
# Slotted class instance: ~56 bytes
```

**When to use**: Objects you create millions of (data points, tokens, tree nodes). Pydantic v2 uses slots by default on models for performance.

### Q12: How do generators and iterators work?

**A:** A generator is a function that uses `yield` to produce values lazily — one at a time, on demand. It implements the iterator protocol (`__iter__` + `__next__`).

```python
# This is like a JavaScript generator function (function*)
def read_large_file(path):
    with open(path) as f:
        for line in f:
            yield line.strip()

# Memory efficient — only one line in memory at a time
for line in read_large_file("huge.csv"):
    process(line)

# Generator expression (like array comprehension but lazy)
squares = (x**2 for x in range(1_000_000))  # Uses almost no memory
```

**vs JavaScript**: Python generators are very similar to JS generators (`function*` / `yield`), but Python uses them more idiomatically. They're the default way to handle large datasets, file processing, and pagination.

### Q13: Explain the difference between `is` and `==`.

**A:**
- `==` compares **values** (calls `__eq__`)
- `is` compares **identity** (same object in memory — pointer comparison)

```python
a = [1, 2, 3]
b = [1, 2, 3]
a == b   # True  — same values
a is b   # False — different objects

# Use `is` for singletons:
x is None      # Correct
x == None      # Works but wrong — calls __eq__, can be overridden
x is True      # Identity check
```

**Interview trap**: Small integers (-5 to 256) and short strings are interned (cached), so `is` appears to work for them. This is a CPython implementation detail, not a language guarantee.

### Q14: What is `__init_subclass__` and when do you use it?

**A:** A simpler alternative to metaclasses for customizing subclass creation:

```python
class Plugin:
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, plugin_name: str = None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__.lower()
        Plugin._registry[name] = cls

class EmailNotifier(Plugin, plugin_name="email"):
    pass

class SlackNotifier(Plugin, plugin_name="slack"):
    pass

Plugin._registry  # {"email": <class EmailNotifier>, "slack": <class SlackNotifier>}
```

This pattern is common in plugin systems, serialization frameworks, and command registries.

### Q15: How does `@property` work?

**A:** `@property` creates a descriptor that intercepts attribute access. It's Python's equivalent of TypeScript getters/setters.

```python
class User:
    def __init__(self, first: str, last: str):
        self._first = first
        self._last = last

    @property
    def full_name(self) -> str:
        """Computed property — accessed like an attribute."""
        return f"{self._first} {self._last}"

    @full_name.setter
    def full_name(self, value: str):
        self._first, self._last = value.rsplit(" ", 1)

user = User("John", "Doe")
print(user.full_name)       # "John Doe" (no parentheses — it's a property)
user.full_name = "Jane Doe"  # Calls the setter
```

### Q16: Explain Python's import system.

**A:**

```python
# When you write:
import my_module

# Python searches (in order):
# 1. sys.modules cache (already imported?)
# 2. Built-in modules
# 3. sys.path (list of directories)

# Relative vs absolute imports:
from . import sibling        # Relative — same package
from ..utils import helper   # Relative — parent package
from app.utils import helper # Absolute — from project root
```

**Circular imports**: A common Python interview topic. If `module_a` imports `module_b` and vice versa, you get `ImportError` or `None` values. Solutions: restructure to avoid cycles, use late imports (import inside functions), or use `TYPE_CHECKING` for type-only imports.

```python
from __future__ import annotations  # Defer annotation evaluation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import User  # Only imported for type checking, not at runtime
```

### Q17: What is the `walrus operator` (`:=`)?

**A:** Assignment expression — assigns and returns a value in a single expression:

```python
# Without walrus:
line = input()
while line != "quit":
    process(line)
    line = input()

# With walrus:
while (line := input()) != "quit":
    process(line)

# Useful in comprehensions:
results = [
    processed
    for item in data
    if (processed := expensive_compute(item)) is not None
]
```

### Q18: How do dataclasses compare to Pydantic models?

**A:**

| Feature | `dataclass` | `Pydantic BaseModel` |
|---------|------------|---------------------|
| Purpose | Data containers | Data validation + serialization |
| Validation | None (just stores values) | Full runtime validation |
| Performance | Faster (no validation) | Slower but Pydantic v2 is Rust-based |
| Serialization | Manual | Built-in `.model_dump()`, `.model_dump_json()` |
| Immutability | `frozen=True` | `model_config = ConfigDict(frozen=True)` |
| Use case | Internal data structures | API boundaries, config, external data |

**Rule of thumb**: Use Pydantic at the edges (API input/output, config, external data). Use dataclasses for internal data structures where validation overhead is unnecessary.

### Q19: Explain `asyncio.gather()` vs `asyncio.TaskGroup`.

**A:**

```python
# gather — older, flexible, but swallows errors by default
results = await asyncio.gather(
    fetch_users(),
    fetch_orders(),
    fetch_products(),
    return_exceptions=True,  # Don't let one failure cancel others
)

# TaskGroup — newer (3.11+), structured concurrency, better error handling
async with asyncio.TaskGroup() as tg:
    task1 = tg.create_task(fetch_users())
    task2 = tg.create_task(fetch_orders())
    task3 = tg.create_task(fetch_products())

# All tasks are guaranteed done here
# If any task fails, all others are cancelled and an ExceptionGroup is raised
```

**Key difference**: `TaskGroup` provides structured concurrency — all tasks are bound to a scope, and errors propagate properly. `gather` is more permissive (can ignore individual failures) but makes it easier to leak tasks.

### Q20: What's the difference between `threading`, `multiprocessing`, and `asyncio`?

**A:**

| Approach | Concurrency | Parallelism | GIL | Best For |
|----------|------------|-------------|-----|----------|
| `asyncio` | Yes (cooperative) | No | Held during Python code | IO-bound (network, DB) |
| `threading` | Yes (preemptive) | No (GIL) | Shared, switched every 5ms | IO-bound with blocking APIs |
| `multiprocessing` | Yes | Yes (separate processes) | One per process | CPU-bound (computation) |

For FastAPI services: use `asyncio` for everything IO-bound (which is most things). Use `ProcessPoolExecutor` for CPU-heavy work. Avoid raw threading unless you're wrapping blocking third-party libraries.

---

## FastAPI-Specific Questions

### Q1: How does FastAPI's dependency injection work?

**A:** FastAPI uses a function-based DI system. Dependencies are declared as function parameters with `Depends()`. FastAPI resolves the dependency graph, calls dependencies in order, and injects return values.

```python
from fastapi import Depends, FastAPI

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

**vs NestJS**: NestJS uses class-based DI with decorators and a container. FastAPI's DI is simpler — just functions and `Depends()`. It's less "enterprise" but more Pythonic. Dependencies are resolved per-request and can use `yield` for cleanup (like context managers).

### Q2: Middleware vs Dependencies — when to use which?

**A:**

| Feature | Middleware | Dependencies |
|---------|-----------|-------------|
| Scope | Every request | Specific endpoints |
| Access to | Raw ASGI scope, request/response | Function parameters, type hints |
| Use case | Logging, CORS, compression, metrics | Auth, DB sessions, pagination params |
| Error handling | Must handle manually | FastAPI's exception handlers work |
| Performance | Runs even for 404s | Only runs for matched routes |

**Rule**: Use middleware for cross-cutting concerns that apply to all requests. Use dependencies for per-endpoint logic that needs type safety and testability.

### Q3: What changed in Pydantic v2?

**A:**

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
from pydantic import BaseModel, field_validator, model_validator, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    name: str
    email: str
    age: int

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()
```

### Q4: Async vs sync endpoints — when to use which?

**A:** FastAPI handles both, but they run differently:

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

**FastAPI automatically runs sync endpoints in a thread pool** so they don't block the event loop. Use `async def` when you have async dependencies (async DB drivers, httpx). Use plain `def` when calling blocking libraries (some legacy SDKs, file operations).

**Gotcha**: Never do blocking IO inside an `async def` endpoint — it blocks the event loop. Either use `async` libraries or define the endpoint as sync.

### Q5: How do you test FastAPI applications?

**A:**

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.dependencies import get_db

# Override dependencies for testing
async def override_get_db():
    async with test_session() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    response = await client.post("/users", json={"name": "Alice", "email": "a@b.com"})
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
```

**Key concept**: `dependency_overrides` is FastAPI's killer feature for testing. You can replace any dependency (database, auth, external services) without mocking internals. This is like NestJS's `overrideProvider()` but simpler.

### Q6: Explain FastAPI's response model and serialization.

**A:**

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

`response_model` controls what's sent to the client. Even if your internal model has 20 fields, the response only includes what's in the response model. This is like a DTO pattern but enforced by the framework.

### Q7: How does FastAPI handle path parameter validation?

**A:**

```python
from fastapi import Path, Query

@app.get("/items/{item_id}")
async def get_item(
    item_id: int = Path(..., gt=0, le=10000, description="The item ID"),
    q: str = Query(None, min_length=3, max_length=50, pattern="^[a-zA-Z]+$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    ...
```

All validation happens before your function runs. Invalid input returns a 422 with detailed error messages. This is automatic — no manual validation code needed.

### Q8: What is the ASGI lifecycle in FastAPI?

**A:**

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

FastAPI is an ASGI application. Uvicorn sends the request as an ASGI scope dict. Each middleware wraps the next. Dependencies are resolved after routing but before the endpoint function runs. The lifespan protocol handles startup/shutdown.

### Q9: How do you handle background tasks?

**A:**

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

### Q10: How do you version a FastAPI API?

**A:**

```python
# URL path versioning (most common)
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")

# Header versioning
@app.get("/items")
async def get_items(accept_version: str = Header("v1")):
    if accept_version == "v2":
        return v2_response()
    return v1_response()
```

---

## System Design with FastAPI

### Design 1: URL Shortener API

**Requirements**: Shorten URLs, redirect, track clicks, analytics.

```
┌─────────┐     ┌──────────┐     ┌─────────┐
│  Client  │────▶│  FastAPI  │────▶│  Redis   │ (hot cache)
└─────────┘     │  Service  │     └─────────┘
                │           │────▶┌─────────┐
                └──────────┘     │ Postgres │ (persistent store)
                      │          └─────────┘
                      ▼
                ┌──────────┐
                │ Analytics │ (async — Kafka/Redis stream)
                └──────────┘
```

**Python-specific considerations**:

```python
# URL shortening: base62 encoding of a distributed ID
import hashlib

def generate_short_code(url: str, length: int = 7) -> str:
    """Generate a short code using SHA-256 + base62."""
    hash_bytes = hashlib.sha256(url.encode()).digest()
    num = int.from_bytes(hash_bytes[:8], "big")
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    code = ""
    while num and len(code) < length:
        code += chars[num % 62]
        num //= 62
    return code

# Endpoint design:
@app.post("/shorten", response_model=ShortenedURL)
async def shorten(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    code = generate_short_code(request.url)
    # Check collision, store in Postgres, cache in Redis
    await redis.setex(f"url:{code}", 86400, request.url)
    ...

@app.get("/{code}")
async def redirect(code: str, redis: Redis = Depends(get_redis)):
    # Check Redis first, then Postgres
    url = await redis.get(f"url:{code}")
    if not url:
        url = await db_lookup(code)
    if not url:
        raise HTTPException(404)

    # Fire-and-forget analytics (don't block redirect)
    background_tasks.add_task(record_click, code)
    return RedirectResponse(url, status_code=301)
```

**Scale discussion points**:
- Redis for hot URLs (most redirects hit cache)
- Postgres for durability
- Background tasks for click analytics (or Kafka for high volume)
- Rate limiting on `/shorten` to prevent abuse
- Consider a pre-generated ID pool to avoid hash collisions under high write load

### Design 2: Notification Service

**Requirements**: Send notifications via email, SMS, push. Support templates, scheduling, preferences.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Producer  │────▶│  FastAPI  │────▶│  Redis    │ (task queue)
│ Services  │     │  Gateway  │     │  (ARQ)    │
└──────────┘     └──────────┘     └─────┬────┘
                                        │
                                  ┌─────▼────┐
                                  │  Workers  │
                                  │ (ARQ)     │
                                  └─────┬────┘
                            ┌───────────┼───────────┐
                       ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
                       │ Email  │  │  SMS   │  │  Push  │
                       │ (SES)  │  │(Twilio)│  │ (FCM)  │
                       └────────┘  └────────┘  └────────┘
```

```python
# API gateway accepts notification requests
@app.post("/notifications/send")
async def send_notification(
    request: NotificationRequest,
    queue: ArqRedis = Depends(get_queue),
):
    # Validate, check user preferences, then enqueue
    job = await queue.enqueue_job(
        "send_notification",
        request.model_dump(),
        _defer_by=request.scheduled_delay,  # Scheduling support
    )
    return {"job_id": job.job_id, "status": "queued"}

# Worker function
async def send_notification(ctx, notification_data: dict):
    notification = NotificationRequest(**notification_data)

    # Route to correct channel
    match notification.channel:
        case "email":
            await send_email(notification)
        case "sms":
            await send_sms(notification)
        case "push":
            await send_push(notification)
```

### Design 3: File Processing Pipeline

**Requirements**: Upload files, process (resize images, parse CSVs, generate PDFs), store results.

```python
# Upload endpoint — stream large files
from fastapi import UploadFile
import aiofiles

@app.post("/files/upload")
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Stream to S3 (don't load entire file in memory)
    file_key = f"uploads/{uuid4()}/{file.filename}"
    await upload_to_s3_streaming(file.file, file_key)

    # Create processing job
    job = FileJob(key=file_key, status="pending", filename=file.filename)
    db.add(job)
    await db.commit()

    # Offload heavy processing to a worker
    await task_queue.enqueue("process_file", job_id=job.id)

    return {"job_id": job.id, "status": "processing"}

@app.get("/files/{job_id}/status")
async def file_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(FileJob, job_id)
    return {"status": job.status, "result_url": job.result_url}
```

**Python advantage for file processing**: Libraries like Pillow (images), pandas (CSVs), ReportLab (PDFs), and ffmpeg-python (video) are mature and battle-tested. CPU-heavy processing runs in worker processes (Celery/ARQ with ProcessPoolExecutor), keeping the API responsive.

---

## Code Review Exercises

### Exercise 1: Spot the Issues

```python
# BAD — find the problems
@app.get("/users/{user_id}")
async def get_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user == None:
        return {"error": "not found"}
    return user
```

**Issues**:
1. `user_id` has no type annotation — no validation, could be any string
2. `db` session is created but never closed — resource leak
3. `user == None` should be `user is None`
4. Returning `{"error": ...}` instead of raising `HTTPException(404)` — wrong status code (200)
5. Returning the ORM model directly — exposes all fields including password
6. Using sync `db.query()` in an `async def` — blocks the event loop

```python
# FIXED
@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Exercise 2: Spot the Issues

```python
# BAD — find the problems
@app.post("/upload")
async def upload(file: UploadFile):
    contents = await file.read()
    data = json.loads(contents)
    for item in data:
        user = User(**item)
        db.add(user)
        await db.commit()
    return {"imported": len(data)}
```

**Issues**:
1. No file size limit — reading entire file into memory could OOM
2. No input validation on `data` items
3. Committing inside the loop — N commits instead of one (slow, no atomicity)
4. No error handling — partial failure leaves inconsistent state
5. `db` appears from nowhere — should be a dependency

```python
# FIXED
@app.post("/upload")
async def upload(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large")

    contents = await file.read()
    try:
        data = json.loads(contents)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    users = [User(**UserCreate.model_validate(item).model_dump()) for item in data]
    db.add_all(users)
    await db.commit()  # Single transaction
    return {"imported": len(users)}
```

### Exercise 3: Spot the Issues

```python
# BAD — find the problems
import requests

@app.get("/external-data")
async def get_external():
    response = requests.get("https://api.example.com/data", timeout=30)
    return response.json()
```

**Issues**:
1. `requests` is synchronous — blocks the entire event loop for up to 30 seconds
2. No error handling for network failures
3. No caching — every call hits the external API
4. 30-second timeout is too generous for an API endpoint

```python
# FIXED
import httpx
from functools import lru_cache

http_client = httpx.AsyncClient(timeout=5.0)

@app.get("/external-data")
async def get_external():
    try:
        response = await http_client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Upstream timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Upstream error: {e.response.status_code}")
```

### Exercise 4: Spot the Issues

```python
# BAD — find the problems
password_cache = {}

@app.post("/login")
async def login(username: str, password: str):
    password_cache[username] = password  # "cache" for faster login next time

    user = await db.execute(
        text(f"SELECT * FROM users WHERE username = '{username}'")
    )
    if user and user.password == password:
        token = jwt.encode({"sub": username}, "secret123")
        return {"token": token}
    return {"error": "invalid credentials"}
```

**Issues**:
1. **SQL injection** — f-string in SQL query
2. **Password stored in plaintext** in a global dict (memory leak + security nightmare)
3. **Plaintext password comparison** — should be bcrypt/argon2 hash comparison
4. **Hardcoded JWT secret** — should be from config/environment
5. **No expiration on JWT**
6. **200 on auth failure** — should be 401

### Exercise 5: Spot the Issues

```python
# BAD — find the problems
@app.get("/search")
async def search(q: str):
    results = []
    all_items = await db.execute(select(Item))
    for item in all_items.scalars().all():
        if q.lower() in item.name.lower():
            results.append(item)
    return results
```

**Issues**:
1. **Loading all items into memory** — does not scale
2. **Filtering in Python** instead of the database — O(n) scan
3. **No pagination** — could return millions of results
4. **No response model** — exposes all fields

```python
# FIXED
@app.get("/search", response_model=PaginatedResponse[ItemOut])
async def search(
    q: str = Query(..., min_length=1, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Item).where(Item.name.ilike(f"%{q}%")).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
```

---

## Live Coding Patterns

### Pattern 1: Build a CRUD Endpoint with Validation

```python
"""Build a complete CRUD for a 'Product' resource.
Demonstrate: Pydantic models, dependency injection, error handling, response models.
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/products", tags=["products"])

# --- Schemas ---
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0, le=1_000_000)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(..., min_length=1)

class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    price: float | None = Field(None, gt=0, le=1_000_000)
    description: str | None = Field(None, max_length=2000)
    category: str | None = None

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: float
    description: str | None
    category: str

# --- Endpoints ---
@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int = Path(..., gt=0),
    updates: ProductUpdate = ...,
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.commit()
```

### Pattern 2: Implement Pagination

```python
"""Implement cursor-based and offset-based pagination."""
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    has_more: bool

# Offset-based (simple, good for most cases)
@router.get("/", response_model=PaginatedResponse[ProductOut])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total_query = select(func.count()).select_from(Product)
    total = (await db.execute(total_query)).scalar()

    query = select(Product).offset(skip).limit(limit).order_by(Product.id)
    items = (await db.execute(query)).scalars().all()

    return PaginatedResponse(items=items, total=total, has_more=skip + limit < total)

# Cursor-based (better for real-time data, no page drift)
@router.get("/stream", response_model=PaginatedResponse[ProductOut])
async def list_products_cursor(
    cursor: int | None = Query(None, description="Last seen product ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).order_by(Product.id).limit(limit + 1)
    if cursor:
        query = query.where(Product.id > cursor)

    items = list((await db.execute(query)).scalars().all())
    has_more = len(items) > limit
    items = items[:limit]

    return PaginatedResponse(items=items, total=-1, has_more=has_more)
```

### Pattern 3: Build a Background Task Processor

```python
"""Implement an async task processor with status tracking."""
import asyncio
from enum import Enum
from datetime import datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# In-memory store (use Redis in production)
tasks: dict[str, dict] = {}

@app.post("/tasks/", status_code=202)
async def create_task(payload: TaskPayload, background_tasks: BackgroundTasks):
    task_id = str(uuid4())
    tasks[task_id] = {
        "id": task_id,
        "status": TaskStatus.PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }

    background_tasks.add_task(run_task, task_id, payload)
    return {"task_id": task_id, "status": "pending"}

async def run_task(task_id: str, payload: TaskPayload):
    tasks[task_id]["status"] = TaskStatus.RUNNING
    try:
        result = await heavy_computation(payload)
        tasks[task_id]["status"] = TaskStatus.COMPLETED
        tasks[task_id]["result"] = result
    except Exception as e:
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["error"] = str(e)

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404)
    return tasks[task_id]
```

### Pattern 4: Implement Rate Limiting Middleware

```python
"""Token bucket rate limiter as FastAPI middleware."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException

class RateLimiter:
    def __init__(self, requests_per_second: float = 10, burst: int = 20):
        self.rate = requests_per_second
        self.burst = burst
        self.tokens: dict[str, float] = defaultdict(lambda: float(burst))
        self.last_check: dict[str, float] = defaultdict(time.monotonic)

    def _get_key(self, request: Request) -> str:
        """Identify the client — use IP, API key, or user ID."""
        forwarded = request.headers.get("x-forwarded-for")
        return forwarded.split(",")[0] if forwarded else request.client.host

    def is_allowed(self, request: Request) -> bool:
        key = self._get_key(request)
        now = time.monotonic()
        elapsed = now - self.last_check[key]
        self.last_check[key] = now

        # Refill tokens
        self.tokens[key] = min(
            self.burst,
            self.tokens[key] + elapsed * self.rate,
        )

        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True
        return False

rate_limiter = RateLimiter(requests_per_second=10, burst=20)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not rate_limiter.is_allowed(request):
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": "1"},
        )
    return await call_next(request)
```

**Production note**: This in-memory rate limiter doesn't work across multiple processes or pods. For production, use Redis with a sliding window counter or a token bucket backed by `redis.incr()` with TTL.
