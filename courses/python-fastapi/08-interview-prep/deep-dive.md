# Interview Prep — Deep Dive

> CPython internals, advanced async patterns, framework comparisons, and Python's role
> in the AI/ML ecosystem. For engineers who want to go beyond surface-level answers.

---

## Table of Contents

1. [Python Internals Questions](#python-internals-questions)
2. [Advanced Async Questions](#advanced-async-questions)
3. [Django vs FastAPI Decision Framework](#django-vs-fastapi-decision-framework)
4. [Python in the AI/ML Ecosystem](#python-in-the-aiml-ecosystem)
5. [Contributing to Open Source Python Projects](#contributing-to-open-source-python-projects)

---

## Python Internals Questions

### How does CPython execute code?

CPython compiles Python source code to bytecode, then executes the bytecode on a virtual machine. The pipeline:

```
Source (.py)
  → Lexer (tokenization)
  → Parser (AST)
  → Compiler (bytecode)
  → .pyc file (cached bytecode in __pycache__/)
  → CPython VM (interprets bytecode)
```

You can inspect bytecode with the `dis` module:

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

**Why this matters**: Understanding bytecode explains why some patterns are faster than others. For example, local variable access (`LOAD_FAST`) is faster than global access (`LOAD_GLOBAL`) because locals are stored in a fixed-size array indexed by position, while globals require a dictionary lookup.

### Reference Counting + Garbage Collection

CPython uses a dual memory management strategy:

**Reference counting** (primary, deterministic):
```python
import sys

a = []           # refcount = 1
b = a            # refcount = 2
c = [a]          # refcount = 3
print(sys.getrefcount(a))  # 4 (includes the argument to getrefcount)

del b            # refcount = 3
c.pop()          # refcount = 2
del a            # refcount = 1 (only 'a' in getrefcount context)
                 # When refcount hits 0 → immediately freed
```

**Generational GC** (handles circular references):

```python
import gc

# CPython has 3 generations:
# Gen 0: newly created objects (checked frequently)
# Gen 1: survived one GC cycle
# Gen 2: survived multiple cycles (checked rarely)

gc.get_threshold()  # (700, 10, 10)
# Gen 0 is checked after 700 allocations - deallocations
# Gen 1 is checked every 10 Gen 0 collections
# Gen 2 is checked every 10 Gen 1 collections

# Force a collection
gc.collect()

# Disable GC (useful for performance-critical sections)
gc.disable()
# ... do work without GC pauses ...
gc.enable()
gc.collect()
```

**Cycle detection algorithm**: CPython uses a variant of trial deletion. For each object in a generation, it tentatively decrements the reference count of all objects it references. Objects with a resulting refcount of 0 are unreachable (part of a cycle) and are collected.

**Interview insight**: Python's reference counting gives more predictable memory behavior than JavaScript's V8 garbage collector, but it adds overhead to every assignment and deletion. The tradeoff is deterministic cleanup (files close when the last reference is dropped) vs throughput (V8's GC is more efficient for high-allocation workloads).

### Slot-Based Optimization

When you define `__slots__` on a class, CPython replaces the per-instance `__dict__` (a hash table) with a fixed-size C-level struct:

```python
# Without slots:
class Point:
    def __init__(self, x, y):
        self.x = x  # Stored in self.__dict__ = {"x": ..., "y": ...}
        self.y = y

# With slots:
class Point:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x  # Stored in a C struct, accessed by offset
        self.y = y
```

**Under the hood**: `__slots__` creates descriptor objects at the class level. Each descriptor knows the byte offset within the instance struct where its value is stored. Attribute access becomes a pointer dereference + offset calculation instead of a hash table lookup.

```python
import sys

class Regular:
    def __init__(self, x, y, z):
        self.x = x; self.y = y; self.z = z

class Slotted:
    __slots__ = ("x", "y", "z")
    def __init__(self, x, y, z):
        self.x = x; self.y = y; self.z = z

r = Regular(1, 2, 3)
s = Slotted(1, 2, 3)
sys.getsizeof(r) + sys.getsizeof(r.__dict__)  # ~200 bytes
sys.getsizeof(s)                                 # ~64 bytes
```

**Caveats**: No `__dict__` means no dynamic attributes, no `__weakref__` (unless explicitly added to slots), and subclasses must also define `__slots__` or they get `__dict__` back.

### String Interning

CPython automatically interns certain strings (caches a single copy and reuses it):

```python
# Interned (same object):
a = "hello"
b = "hello"
a is b  # True — interned because it looks like an identifier

# Not interned (different objects):
a = "hello world"
b = "hello world"
a is b  # False — contains a space (not identifier-like)

# Force interning:
import sys
a = sys.intern("hello world")
b = sys.intern("hello world")
a is b  # True
```

**Rules for auto-interning**:
- Strings that look like identifiers (letters, digits, underscores)
- Strings defined at compile time (literals)
- Dictionary keys (for faster lookup)

**When to care**: If you're storing millions of strings that are mostly the same values (like status codes, country codes), `sys.intern()` can significantly reduce memory.

### Small Integer Caching

CPython pre-allocates integers from -5 to 256:

```python
a = 256
b = 256
a is b  # True — same cached object

a = 257
b = 257
a is b  # False — different objects (outside cache range)

# This is a CPython implementation detail, NOT a language guarantee.
# Never rely on `is` for integer comparison. Always use ==.
```

**Why -5 to 256?**: These values cover the vast majority of integers used in typical programs (loop counters, array indices, small calculations). Pre-allocating them avoids creating and destroying millions of small objects.

---

## Advanced Async Questions

### Event Loop Internals

Python's `asyncio` event loop is conceptually similar to Node.js's libuv, but implemented differently:

```
┌─────────────────────────────────────┐
│           Event Loop                 │
│                                     │
│  1. Run all ready callbacks         │
│  2. Poll for IO events (select/     │
│     epoll/kqueue)                   │
│  3. Schedule callbacks for          │
│     completed IO                    │
│  4. Process timers                  │
│  5. Repeat                          │
│                                     │
└─────────────────────────────────────┘
```

**Key differences from Node.js**:

| Aspect | Node.js (libuv) | Python (asyncio) |
|--------|----------------|-----------------|
| Implementation | C library (libuv) | Python + C (selectors) |
| IO backend | libuv (platform-specific) | selectors module (select/epoll/kqueue) |
| Microtasks | `process.nextTick`, Promise callbacks | No equivalent (all callbacks are equal) |
| Timer resolution | 1ms (libuv) | Depends on OS selector |
| Thread pool | Built-in (libuv, 4 threads default) | Optional (`ThreadPoolExecutor`) |

### Task Scheduling

```python
import asyncio

async def demonstrate_scheduling():
    # Tasks are scheduled, not immediately executed
    task = asyncio.create_task(my_coroutine())
    # task is now scheduled but hasn't started yet

    # The task starts running at the next await point
    await asyncio.sleep(0)  # Yield to event loop — task starts executing

    # gather runs tasks concurrently (like Promise.all)
    results = await asyncio.gather(task1(), task2(), task3())

    # wait gives more control — complete when first finishes
    done, pending = await asyncio.wait(
        [task1(), task2(), task3()],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()  # Clean up remaining tasks
```

**Scheduling priority**: Unlike Node.js which has microtask and macrotask queues, asyncio treats all callbacks equally. They're executed in FIFO order from a single ready queue. `asyncio.sleep(0)` yields control to the event loop, allowing other scheduled tasks to run.

### Cancellation Patterns

Task cancellation in Python is cooperative — it raises `CancelledError` at the next `await` point:

```python
async def cancellable_operation():
    try:
        while True:
            data = await fetch_next_batch()
            await process_batch(data)
    except asyncio.CancelledError:
        # Cleanup — this is your chance to clean up resources
        await flush_pending_data()
        raise  # Re-raise to confirm cancellation

# Cancellation with timeout
async def with_timeout():
    try:
        async with asyncio.timeout(5.0):  # Python 3.11+
            result = await long_running_operation()
    except TimeoutError:
        # Handle timeout — the task was cancelled
        pass

# Shielding from cancellation
async def critical_operation():
    # Even if the parent task is cancelled, this completes
    result = await asyncio.shield(save_to_database(data))
    return result
```

**The CancelledError gotcha**: In Python 3.9+, `CancelledError` is a subclass of `BaseException`, not `Exception`. This means `except Exception` won't catch it — cancellation propagates through generic error handlers, which is the correct behavior.

```python
# This does NOT catch CancelledError (correct):
try:
    await some_operation()
except Exception:
    handle_error()
# CancelledError passes through

# This DOES catch CancelledError (usually wrong):
try:
    await some_operation()
except BaseException:
    handle_everything()  # Swallows cancellation — bad!
```

### Structured Concurrency

```python
# Python 3.11+ TaskGroup — structured concurrency
async def fetch_all_data():
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(fetch_user(user_id))
        orders_task = tg.create_task(fetch_orders(user_id))
        prefs_task = tg.create_task(fetch_preferences(user_id))

    # All tasks guaranteed complete here
    # If any task raised an exception:
    #   1. All other tasks are cancelled
    #   2. ExceptionGroup is raised with all errors
    return {
        "user": user_task.result(),
        "orders": orders_task.result(),
        "preferences": prefs_task.result(),
    }
```

**ExceptionGroup handling** (Python 3.11+):

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(might_fail_1())
        tg.create_task(might_fail_2())
except* ValueError as eg:
    # Handle all ValueErrors from the group
    for exc in eg.exceptions:
        print(f"ValueError: {exc}")
except* TypeError as eg:
    # Handle all TypeErrors from the group
    for exc in eg.exceptions:
        print(f"TypeError: {exc}")
```

### Async Generators

```python
async def paginated_fetch(url: str, page_size: int = 100):
    """Async generator — yields pages on demand."""
    page = 0
    while True:
        response = await httpx_client.get(url, params={"page": page, "size": page_size})
        data = response.json()
        if not data["items"]:
            break
        yield data["items"]
        page += 1

# Consume lazily
async for page in paginated_fetch("https://api.example.com/users"):
    for user in page:
        await process_user(user)
```

**Cleanup**: Async generators need proper cleanup. If you break out of an `async for` loop early, Python calls `aclose()` on the generator, which triggers any `finally` blocks inside it. This is important for releasing resources (database cursors, file handles).

---

## Django vs FastAPI Decision Framework

### Feature Comparison

| Feature | Django | FastAPI |
|---------|--------|---------|
| **Philosophy** | Batteries included | Minimal, composable |
| **ORM** | Built-in (Django ORM) | BYO (SQLAlchemy, Tortoise) |
| **Admin panel** | Built-in (powerful) | None (use SQLAdmin or build your own) |
| **Auth** | Built-in (users, sessions, permissions) | BYO (write your own or use libraries) |
| **Async support** | Partial (views, ORM queries in 4.1+) | Native, async-first |
| **Validation** | Django forms, DRF serializers | Pydantic (built-in) |
| **API docs** | Manual (DRF + drf-spectacular) | Automatic (OpenAPI/Swagger) |
| **Type safety** | Limited (mypy support improving) | Excellent (Pydantic + type hints) |
| **Performance** | Moderate | High (Starlette + Pydantic v2 Rust core) |
| **Learning curve** | Steeper (many conventions) | Shallower (explicit over implicit) |
| **Ecosystem** | Massive (20+ years of packages) | Growing fast |

### Decision Matrix

**Choose Django when**:
- You need an admin panel (CMS, back-office tools)
- You want batteries-included auth, sessions, CSRF
- Your team knows Django and the project is a traditional web app
- You need Django's massive ecosystem of packages
- Project is content-heavy (Django templates, CMS features)

**Choose FastAPI when**:
- Building a pure API (no server-rendered HTML)
- Performance matters (high throughput, low latency)
- You want automatic OpenAPI documentation
- Your team values explicit, type-safe code
- Building microservices or ML model serving
- Coming from TypeScript/Express — FastAPI feels more familiar

**Choose Django + DRF when**:
- Building an API but you also need Django admin, auth, or ORM
- The API is for a Django-rendered frontend (shared models)

### The TypeScript Engineer's Perspective

If you're coming from Express/NestJS:

| If you liked... | Choose... | Because... |
|----------------|-----------|-----------|
| Express (minimal, flexible) | FastAPI | Similar philosophy — explicit, composable |
| NestJS (structured, DI, decorators) | Django | Similar philosophy — conventions, batteries |
| tRPC (type-safe, end-to-end) | FastAPI | Pydantic gives you type-safe serialization |

---

## Python in the AI/ML Ecosystem

### Why Python Dominates ML

1. **NumPy/SciPy**: The foundational numerical computing libraries — written in C/Fortran, called from Python
2. **First-mover advantage**: Python was the language of choice for early ML research (sklearn, 2007)
3. **Interop story**: Python is excellent glue between C/C++/CUDA libraries
4. **PyTorch/TensorFlow**: The major ML frameworks are Python-first
5. **Jupyter notebooks**: Interactive computing environment became the standard for research

**The irony**: Python is slow for computation but fast for development. The actual heavy lifting happens in C/C++/CUDA extensions. Python is the orchestration layer.

### FastAPI for ML Model Serving

FastAPI has become the de facto standard for serving ML models:

```python
from fastapi import FastAPI
from pydantic import BaseModel
import torch
from transformers import pipeline

app = FastAPI()

# Load model at startup (not per-request)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    app.state.classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased")
    yield
    # Cleanup (optional — free GPU memory)
    del app.state.classifier

app = FastAPI(lifespan=lifespan)

class PredictionRequest(BaseModel):
    text: str
    max_length: int = 512

class PredictionResponse(BaseModel):
    label: str
    confidence: float

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    # ML inference is CPU/GPU-bound — run in thread pool
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # Default thread pool
        lambda: app.state.classifier(request.text[:request.max_length])[0],
    )
    return PredictionResponse(
        label=result["label"],
        confidence=round(result["score"], 4),
    )
```

**Why FastAPI for ML serving**:
- Pydantic validates input before it hits the model (prevents crashes from bad input)
- Automatic API docs let data scientists explore the API
- Async handling keeps the server responsive while models run in thread pools
- Easy to add authentication, rate limiting, monitoring
- Type hints document the expected input/output schema

### The ML Serving Stack

```
┌─────────────┐
│  Client      │
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────────┐
│  FastAPI     │────▶│  Model Store  │ (S3, MLflow)
│  Gateway     │     └──────────────┘
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────────┐
│  Worker Pool │────▶│  GPU Cluster  │
│  (Ray Serve, │     └──────────────┘
│   Triton)    │
└─────────────┘
```

For simple models: FastAPI + thread pool is sufficient.
For scale: FastAPI as the gateway, with Ray Serve or Triton Inference Server handling the actual inference on GPU clusters.

---

## Contributing to Open Source Python Projects

### Getting Started

The Python open source ecosystem is welcoming but has its own conventions:

```bash
# 1. Fork and clone
gh repo fork fastapi/fastapi --clone

# 2. Set up development environment
cd fastapi
uv sync  # or pip install -e ".[dev]"

# 3. Run tests
uv run pytest
# or
python -m pytest

# 4. Run linters
uv run ruff check .
uv run mypy .
```

### Conventions to Know

| Convention | Description |
|-----------|-------------|
| **PEP 8** | Style guide (enforced by ruff/black) |
| **PEP 257** | Docstring conventions |
| **Type hints** | Expected in modern projects (PEP 484+) |
| **CHANGELOG.md** | Most projects use Keep a Changelog format |
| **pre-commit** | Git hooks for linting/formatting (`.pre-commit-config.yaml`) |
| **tox / nox** | Test across multiple Python versions |

### Good First Projects for Backend Engineers

| Project | What You'd Work On | Skill Level |
|---------|-------------------|-------------|
| **FastAPI** | Documentation, test cases, bug fixes | Intermediate |
| **Pydantic** | Validators, serializers, docs | Intermediate |
| **httpx** | HTTP client features, async handling | Intermediate |
| **SQLAlchemy** | ORM features, dialect support | Advanced |
| **uvicorn** | ASGI server internals | Advanced |
| **ruff** | Linter rules (Rust, but Python domain knowledge) | Advanced |

### Writing Good Python PRs

```python
# 1. Always include type hints
def process_item(item: Item, *, validate: bool = True) -> ProcessedItem:
    ...

# 2. Write docstrings (Google or NumPy style)
def calculate_score(values: list[float], weights: list[float] | None = None) -> float:
    """Calculate a weighted score from a list of values.

    Args:
        values: The raw score values.
        weights: Optional weights for each value. If None, equal weights are used.

    Returns:
        The weighted average score.

    Raises:
        ValueError: If values is empty or if weights length doesn't match values.
    """
    ...

# 3. Use keyword-only arguments for clarity (the * separator)
def create_user(name: str, email: str, *, admin: bool = False, verified: bool = False):
    ...
# Forces: create_user("Alice", "a@b.com", admin=True)
# Prevents: create_user("Alice", "a@b.com", True, True)  # What do these bools mean?
```

### Python Enhancement Proposals (PEPs) to Know

| PEP | What | Why It Matters |
|-----|------|---------------|
| **PEP 8** | Style guide | The universal standard |
| **PEP 484** | Type hints | Foundation of modern Python |
| **PEP 557** | Data classes | `@dataclass` decorator |
| **PEP 604** | `X \| Y` union syntax | Replaced `Union[X, Y]` |
| **PEP 612** | ParamSpec | Type-safe decorators |
| **PEP 695** | Type alias syntax (3.12) | `type Point = tuple[int, int]` |
| **PEP 703** | Making the GIL optional | Free-threaded Python (experimental in 3.13) |
| **PEP 723** | Inline script metadata | `uv run` script dependencies |

### PEP 703: The Free-Threaded Future

The most significant change to CPython in decades. PEP 703 introduces a build of CPython that can run without the GIL:

```python
# With free-threaded Python (3.13+ experimental, 3.14+ more stable)
# True parallel threads for CPU-bound work:

import threading

def cpu_work(data):
    # This actually runs in parallel on multiple cores
    return heavy_computation(data)

threads = [threading.Thread(target=cpu_work, args=(chunk,)) for chunk in data_chunks]
for t in threads:
    t.start()
for t in threads:
    t.join()
```

**Current status** (as of early 2026): Available as an experimental build (`python3.13t`). Not yet the default. Many C extensions need updates to be thread-safe. Major libraries (NumPy, etc.) are working on compatibility. It will likely take 2-3 more releases before it's production-ready for most workloads.

**Interview answer**: "I'm aware of free-threaded Python (PEP 703). It's available experimentally in 3.13+ and removes the GIL, enabling true thread-level parallelism. However, it's not production-ready yet — it requires C extensions to be thread-safe, and the ecosystem is still catching up. For now, the standard approach is asyncio for IO-bound work and multiprocessing for CPU-bound work."
