# 01 – Interview Fundamentals

## Top 20 Python Questions — Quick Reference

| # | Question | Answer |
|---|----------|--------|
| 1 | What is the GIL? | A mutex in CPython that allows only one thread to execute Python bytecode at a time; released during IO. |
| 2 | `is` vs `==`? | `is` checks identity (same object in memory); `==` checks value equality (calls `__eq__`). |
| 3 | `list` vs `tuple`? | Lists are mutable (append/remove); tuples are immutable (hashable, usable as dict keys). |
| 4 | What are decorators? | Syntactic sugar: `@dec` on `def f` means `f = dec(f)` — a function that wraps another function. |
| 5 | What are generators? | Functions that `yield` values lazily; produce items one at a time without loading all into memory. |
| 6 | `*args` vs `**kwargs`? | `*args` collects positional args as a tuple; `**kwargs` collects keyword args as a dict. |
| 7 | What are context managers? | Objects with `__enter__`/`__exit__` that guarantee cleanup; used with `with`/`async with`. |
| 8 | `__str__` vs `__repr__`? | `__str__` is human-readable; `__repr__` is unambiguous and developer-facing. |
| 9 | What are metaclasses? | The class of a class; `type` is the default metaclass; used by frameworks (Pydantic, Django ORM). |
| 10 | What are descriptors? | Objects with `__get__`/`__set__` that control attribute access; power `@property`, `@classmethod`. |
| 11 | How does GC work? | Reference counting (primary, deterministic) + generational GC (handles circular references). |
| 12 | What are `__slots__`? | Replaces instance `__dict__` with fixed-size struct; less memory, faster access, no dynamic attrs. |
| 13 | `asyncio.gather` vs `TaskGroup`? | `gather` is flexible but can leak tasks; `TaskGroup` (3.11+) provides structured concurrency. |
| 14 | `threading` vs `multiprocessing`? | Threading = concurrent IO (GIL limits CPU); multiprocessing = true parallelism (separate processes). |
| 15 | What is a dataclass? | `@dataclass` auto-generates `__init__`, `__repr__`, `__eq__` from type-annotated fields. |
| 16 | Mutable default argument trap? | `def f(lst=[])` shares one list across all calls; fix: `def f(lst=None): lst = lst or []`. |
| 17 | What is `__init_subclass__`? | Hook called when a class is subclassed; simpler alternative to metaclasses for registration patterns. |
| 18 | What is the walrus operator? | `:=` assigns and returns in one expression: `if (n := len(a)) > 10:`. |
| 19 | How do imports work? | Check `sys.modules` cache, then search `sys.path`; `.pyc` bytecode is cached in `__pycache__/`. |
| 20 | What is `match`/`case`? | Structural pattern matching (3.10+); like switch but with destructuring and guard clauses. |

---

## Python vs TypeScript Syntax Comparison

### Variables and Types

```python
# Python                          # TypeScript
name: str = "Alice"               # const name: string = "Alice"
age: int = 30                     # const age: number = 30
items: list[str] = []             # const items: string[] = []
data: dict[str, int] = {}         # const data: Record<string, number> = {}
maybe: str | None = None          # const maybe: string | null = null
```

### Functions

```python
# Python                          # TypeScript
def greet(name: str) -> str:      # function greet(name: string): string {
    return f"Hello, {name}"       #     return `Hello, ${name}`
                                  # }

async def fetch(url: str) -> dict:  # async function fetch(url: string): Promise<object> {
    ...                             # }

# Default + keyword-only args
def create(name: str, *, admin: bool = False) -> User:
    ...
# The * forces admin to be keyword-only: create("Alice", admin=True)
```

### Classes

```python
# Python                          # TypeScript
class User:                       # class User {
    def __init__(self, name: str): #     constructor(public name: string) {}
        self.name = name

    @property                     #     get full_name(): string {
    def full_name(self) -> str:   #         return this.name
        return self.name          #     }

    @staticmethod                 #     static create(): User {
    def create() -> "User":       #         return new User("default")
        return User("default")    #     }
```

### Error Handling

```python
# Python                          # TypeScript
try:                              # try {
    result = do_thing()           #     const result = doThing()
except ValueError as e:           # } catch (e) {
    handle(e)                     #     if (e instanceof ValueError) handle(e)
except (KeyError, TypeError):     # }
    handle_other()
finally:                          # } finally {
    cleanup()                     #     cleanup()
```

### Collections

```python
# List comprehension (like Array.map/filter)
squares = [x**2 for x in range(10)]

# Dict comprehension (like Object.fromEntries)
mapping = {k: v for k, v in items}

# Generator (lazy — no direct TS equivalent)
gen = (x**2 for x in range(10))

# Unpacking (like destructuring)
a, b, *rest = [1, 2, 3, 4]  # same as const [a, b, ...rest]
```

### Async

```python
# Python                          # TypeScript
await asyncio.gather(a(), b())    # await Promise.all([a(), b()])
await asyncio.sleep(1)            # await new Promise(r => setTimeout(r, 1000))

async with session() as s:        # // No equivalent — use try/finally
    await s.execute(query)

async for item in stream:         # for await (const item of stream) {
    process(item)
```

---

## Python Backend Interview Questions — In Depth

### Q1: What is the GIL, and why does it matter for web services?

The Global Interpreter Lock is a mutex in CPython that allows only one thread to execute Python bytecode at a time. For web services:

- **CPU-bound work**: Multiple threads cannot parallelize CPU work. Use `multiprocessing`, `ProcessPoolExecutor`, or offload to Celery workers.
- **IO-bound work**: The GIL is released during IO operations (`await`, network calls, file reads). Async FastAPI endpoints are largely unaffected.

```python
# CPU-bound: GIL is a bottleneck — use ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor
import asyncio

async def cpu_heavy_endpoint():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(ProcessPoolExecutor(), compute_hash, large_data)
    return result
```

**The Node.js comparison**: Node.js is single-threaded by design and uses worker threads for CPU work. Python is similar in practice — the GIL makes threading behave like single-threaded for CPU, but the story is more nuanced because the GIL is released during IO and C-extension calls.

### Q2: How does Python's async/await differ from JavaScript's?

| Aspect | JavaScript | Python |
|--------|-----------|--------|
| Event loop | Built into the runtime, always running | Must be explicitly started (`asyncio.run()`) |
| Concurrency model | Sync by default, async is opt-in | Same |
| `await` outside async | Top-level await (ES modules) | Only inside `async def` |
| Promises vs Coroutines | Promises start executing immediately | Coroutines are lazy — `await` triggers execution |
| `Promise.all()` | `await Promise.all([p1, p2])` | `await asyncio.gather(c1(), c2())` |

**Critical difference**: In JavaScript, `fetch()` returns a Promise that starts executing immediately. In Python, calling an `async def` function returns a coroutine object that does nothing until you `await` it:

```python
# This does NOTHING — the coroutine is created but not executed
coro = fetch_data()  # No network call happens

# This actually runs it
result = await fetch_data()
```

### Q3: Explain decorators — how do they work under the hood?

A decorator is syntactic sugar for wrapping a function — a function that takes a function and returns a function:

```python
# @my_decorator on def my_function: is exactly equivalent to:
my_function = my_decorator(my_function)

import functools
import time

def timing(func):
    @functools.wraps(func)  # Preserves __name__, __doc__, etc.
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"{func.__name__} took {time.perf_counter() - start:.3f}s")
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

**Interview tip**: Always mention `@functools.wraps` — forgetting it means the wrapped function loses its name, docstring, and type hints.

### Q4: What are context managers and why do they matter?

Context managers implement the `__enter__`/`__exit__` protocol (or `__aenter__`/`__aexit__` for async). They guarantee cleanup happens even if exceptions occur:

```python
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
        logger.info(f"{name} took {time.perf_counter() - start:.3f}s")

async with timed_operation("database_query"):
    result = await db.execute(query)
```

**Why interviewers ask this**: Context managers are used everywhere in Python — database sessions, file handles, locks, HTTP clients, transactions. Not using them (or using them wrong) is a red flag for resource leaks.

### Q5: Explain Python's memory model — reference counting + GC.

Python uses a dual strategy:

1. **Reference counting** (primary): Every object has a reference count. When it reaches 0, the object is immediately deallocated. This is deterministic.

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

A metaclass is the "class of a class." Just as an object is an instance of a class, a class is an instance of a metaclass. The default metaclass is `type`.

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
        for key, value in namespace.items():
            if callable(value) and not key.startswith("_"):
                if not value.__doc__:
                    raise TypeError(f"{name}.{key} must have a docstring")
        return super().__new__(mcs, name, bases, namespace)
```

**When to use**: Almost never in application code. Metaclasses are used in frameworks — SQLAlchemy's declarative base, Django's models, Pydantic's BaseModel, and ABC all use metaclasses. If your application code needs a metaclass, you probably want a class decorator or `__init_subclass__` instead.

### Q7: Explain descriptors.

Descriptors are objects that define `__get__`, `__set__`, or `__delete__`. They control attribute access on classes. They're the mechanism behind `@property`, `@classmethod`, `@staticmethod`, and ORMs:

```python
class Validated:
    """A descriptor that validates values on assignment."""
    def __set_name__(self, owner, name):
        self.name = name  # Automatically called — knows the attribute name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if value < 0:
            raise ValueError(f"{self.name} must be >= 0")
        obj.__dict__[self.name] = value

class Product:
    price = Validated()
    quantity = Validated()

p = Product()
p.price = 29.99      # OK
p.price = -1         # ValueError: price must be >= 0
```

**Interview insight**: Pydantic fields are descriptors under the hood. Understanding descriptors explains how `model.field` returns a value, but `Model.field` returns field metadata.

### Q8: How does Python's packaging ecosystem work?

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
```

**Rule**: Always implement `__repr__`. Implement `__str__` only if you need a different user-facing format.

### Q10: Explain `*args` and `**kwargs`.

```python
def func(*args, **kwargs):
    # args is a tuple of positional arguments
    # kwargs is a dict of keyword arguments
    print(args)    # (1, 2, 3)
    print(kwargs)  # {"x": 10, "y": 20}

func(1, 2, 3, x=10, y=20)

# Reverse — unpacking into a call:
data = {"host": "localhost", "port": 8000}
connect(**data)  # Same as connect(host="localhost", port=8000)
```

### Q11: What are slots and when would you use them?

`__slots__` replaces the instance `__dict__` with a fixed-size array. Less memory, faster attribute access, no dynamic attributes:

```python
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
p.z = 3  # AttributeError — no __dict__, can't add attributes

# Regular class instance: ~152 bytes (dict overhead)
# Slotted class instance: ~56 bytes
```

**When to use**: Objects you create millions of (data points, tokens, tree nodes). Pydantic v2 uses slots by default on models for performance.

### Q12: How do generators and iterators work?

A generator is a function that uses `yield` to produce values lazily — one at a time, on demand:

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

### Q13: Explain the difference between `is` and `==`.

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
```

**Interview trap**: Small integers (-5 to 256) and short strings are interned (cached), so `is` appears to work for them. This is a CPython implementation detail, not a language guarantee.

### Q14: What is `__init_subclass__` and when do you use it?

A simpler alternative to metaclasses for customizing subclass creation:

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

### Q15: How does `@property` work?

`@property` creates a descriptor that intercepts attribute access. It's Python's equivalent of TypeScript getters/setters:

```python
class User:
    def __init__(self, first: str, last: str):
        self._first = first
        self._last = last

    @property
    def full_name(self) -> str:
        return f"{self._first} {self._last}"

    @full_name.setter
    def full_name(self, value: str):
        self._first, self._last = value.rsplit(" ", 1)

user = User("John", "Doe")
print(user.full_name)       # "John Doe" (no parentheses — it's a property)
user.full_name = "Jane Doe"  # Calls the setter
```

### Q16: Explain Python's import system.

```python
# When you write: import my_module
# Python searches (in order):
# 1. sys.modules cache (already imported?)
# 2. Built-in modules
# 3. sys.path (list of directories)

from . import sibling        # Relative — same package
from ..utils import helper   # Relative — parent package
from app.utils import helper # Absolute — from project root
```

**Circular imports**: If `module_a` imports `module_b` and vice versa, you get `ImportError` or `None` values. Solution: `TYPE_CHECKING` for type-only imports:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import User  # Only imported for type checking, not at runtime
```

### Q17: What is the walrus operator (`:=`)?

Assignment expression — assigns and returns a value in a single expression:

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
# If any task fails, all others are cancelled and ExceptionGroup is raised
```

**Key difference**: `TaskGroup` provides structured concurrency — all tasks are bound to a scope, and errors propagate properly. `gather` is more permissive (can ignore individual failures) but makes it easier to leak tasks.

### Q20: What's the difference between `threading`, `multiprocessing`, and `asyncio`?

| Approach | Concurrency | Parallelism | GIL | Best For |
|----------|------------|-------------|-----|----------|
| `asyncio` | Yes (cooperative) | No | Held during Python code | IO-bound (network, DB) |
| `threading` | Yes (preemptive) | No (GIL) | Shared, switched every 5ms | IO-bound with blocking APIs |
| `multiprocessing` | Yes | Yes (separate processes) | One per process | CPU-bound (computation) |

For FastAPI services: use `asyncio` for everything IO-bound (which is most things). Use `ProcessPoolExecutor` for CPU-heavy work. Avoid raw threading unless you're wrapping blocking third-party libraries.

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

---

## CPython Internals (Advanced)

### How CPython Executes Code

CPython compiles Python source code to bytecode, then executes the bytecode on a virtual machine:

```
Source (.py) → Lexer (tokenization) → Parser (AST)
             → Compiler (bytecode) → .pyc file (__pycache__/)
             → CPython VM (interprets bytecode)
```

```python
import dis

def add(a, b):
    return a + b

dis.dis(add)
#   0 LOAD_FAST    0 (a)
#   2 LOAD_FAST    1 (b)
#   4 BINARY_ADD
#   6 RETURN_VALUE
```

**Why this matters**: Local variable access (`LOAD_FAST`) is faster than global access (`LOAD_GLOBAL`) because locals are stored in a fixed-size array indexed by position, while globals require a dictionary lookup.

### String Interning

CPython automatically interns certain strings (caches a single copy):

```python
# Interned (same object):
a = "hello"
b = "hello"
a is b  # True — interned because it looks like an identifier

# Not interned:
a = "hello world"
b = "hello world"
a is b  # False — contains a space

# Force interning:
import sys
a = sys.intern("hello world")
b = sys.intern("hello world")
a is b  # True
```

**When to care**: If you're storing millions of strings that are mostly the same values (status codes, country codes), `sys.intern()` can significantly reduce memory.

### Small Integer Caching

CPython pre-allocates integers from -5 to 256:

```python
a = 256
b = 256
a is b  # True — same cached object

a = 257
b = 257
a is b  # False — different objects (outside cache range)
# Never rely on `is` for integer comparison. Always use ==.
```

### Django vs FastAPI Decision Matrix

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

### PEPs to Know

| PEP | What | Why It Matters |
|-----|------|---------------|
| **PEP 8** | Style guide | The universal standard |
| **PEP 484** | Type hints | Foundation of modern Python |
| **PEP 557** | Data classes | `@dataclass` decorator |
| **PEP 604** | `X \| Y` union syntax | Replaced `Union[X, Y]` |
| **PEP 612** | ParamSpec | Type-safe decorators |
| **PEP 695** | Type alias syntax (3.12) | `type Point = tuple[int, int]` |
| **PEP 703** | Making the GIL optional | Free-threaded Python (experimental in 3.13) |

**PEP 703 interview answer**: "I'm aware of free-threaded Python (PEP 703). It removes the GIL, enabling true thread-level parallelism. It's available experimentally in 3.13+ but not production-ready yet — C extensions need to be thread-safe, and the ecosystem is still catching up. For now, the standard approach is asyncio for IO-bound work and multiprocessing for CPU-bound work."

---

## Practice Exercises

The following timed coding challenges in `exercises.py` test concepts covered in this file. Use them to practice under interview conditions.

| Exercise | Time | Concepts from this file |
|----------|------|------------------------|
| **Exercise 1: TODO API with CRUD + Filtering** | 15 min | Pydantic models (F3, Q18), Field validation, FastAPI route decorators (F1, F4), query parameter filtering, status codes |
| **Exercise 2: User Registration with Validation** | 15 min | `@field_validator` (F3), password hashing (F1 dependency injection), Bearer token auth (F1), `HTTPException` status codes |
| **Exercise 4: Debug Broken Code** | 10 min | `is None` vs `== None` (Q13), proper status codes, Pydantic validation, error handling patterns |
| **Exercise 5: Code Review** | 10 min | Security (plaintext passwords), Pydantic models (Q18, F3), route ordering, type hints (Q10), HTTP method semantics |

Exercises 3 (Rate Limiter) and 6 (Webhook Delivery) are covered in `02-system-design-and-code-review.md`.

---

## Key Takeaways

- Fixtures are composable, dependency-injected, and replace `beforeEach`/`afterEach` with a single function.
- The GIL blocks CPU-bound threads but is released during IO — async FastAPI is largely unaffected.
- Python coroutines are lazy (unlike JS Promises): calling `async def f()` does nothing; only `await f()` runs it.
- `@functools.wraps` is required in every decorator to preserve the wrapped function's metadata.
- Use `is None` (identity), not `== None` (equality) — `== None` can be overridden by `__eq__`.
- `dependency_overrides` in FastAPI is the correct way to inject test dependencies — don't monkeypatch.
