# Interview Prep Cheat Sheet

> One-line answers, syntax comparisons, and templates. Scan before the interview.

---

## Top 20 Python Questions — One-Line Answers

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

## FastAPI Top 10 Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | How does DI work? | `Depends(func)` — FastAPI calls the function, injects return value; supports `yield` for cleanup. |
| 2 | Middleware vs dependencies? | Middleware = every request (logging, CORS); dependencies = per-endpoint (auth, DB session). |
| 3 | `async def` vs `def` endpoints? | `async def` runs on event loop; `def` runs in thread pool automatically — never block in async. |
| 4 | How does validation work? | Pydantic models validate request body/query/path params before the endpoint function runs. |
| 5 | What is `response_model`? | Controls serialization — filters output fields, strips sensitive data, enforces schema. |
| 6 | How to test? | `httpx.AsyncClient` + `ASGITransport(app=app)` + `dependency_overrides` for mocking. |
| 7 | Background tasks? | `BackgroundTasks.add_task()` runs after response; for critical work, use Celery/ARQ. |
| 8 | Lifespan events? | `@asynccontextmanager` with `yield` — startup before yield, shutdown after; replaces `on_event`. |
| 9 | Pydantic v1 vs v2? | v2 has Rust core (5-50x faster), `model_dump()`/`model_dump_json()`, `@field_validator`, strict mode. |
| 10 | FastAPI vs Django? | FastAPI = async-first, minimal, auto-docs, Pydantic; Django = batteries-included, admin, ORM, auth. |

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
    ...                             #     ...
                                    # }

# Default + keyword-only args     # Optional/default params
def create(                       # function create(
    name: str,                    #     name: string,
    *,                            #     // no equivalent
    admin: bool = False,          #     admin: boolean = false,
) -> User:                        # ): User {
    ...                           #     ...
```

### Classes

```python
# Python                          # TypeScript
class User:                       # class User {
    def __init__(self, name: str): #     constructor(
        self.name = name          #         public name: string
                                  #     ) {}
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
except (KeyError, TypeError):     #     // no multi-catch
    handle_other()                # }
finally:                          # } finally {
    cleanup()                     #     cleanup()
                                  # }
```

### Collections

```python
# Python                          # TypeScript
# List comprehension              # Array.map/filter
squares = [x**2 for x in range(10)]  # const squares = [...Array(10)].map((_, x) => x ** 2)

# Dict comprehension              # Object.fromEntries
mapping = {k: v for k, v in items}  # const mapping = Object.fromEntries(items)

# Generator (lazy)                # No direct equivalent (generator functions exist)
gen = (x**2 for x in range(10))  # function* gen() { for (let x=0;x<10;x++) yield x**2 }

# Unpacking                      # Destructuring
a, b, *rest = [1, 2, 3, 4]      # const [a, b, ...rest] = [1, 2, 3, 4]
```

### Async

```python
# Python                          # TypeScript
await asyncio.gather(a(), b())    # await Promise.all([a(), b()])
await asyncio.sleep(1)            # await new Promise(r => setTimeout(r, 1000))

async with session() as s:        # // No equivalent — use try/finally
    await s.execute(query)        # const s = await session()
                                  # try { await s.execute(query) }
                                  # finally { s.close() }

async for item in stream:         # for await (const item of stream) {
    process(item)                 #     process(item)
                                  # }
```

---

## System Design Template for Python APIs

### 1. Requirements (2 min)

- Functional requirements (what does it do?)
- Non-functional (latency, throughput, availability)
- Scale (users, requests/sec, data size)

### 2. API Design (3 min)

```
POST /resource          → Create (201)
GET  /resource          → List (200, paginated)
GET  /resource/{id}     → Get (200 / 404)
PATCH /resource/{id}    → Update (200 / 404)
DELETE /resource/{id}   → Delete (204 / 404)
```

### 3. Data Model (3 min)

- SQLAlchemy models + Pydantic schemas
- Mention: indexes, constraints, relationships

### 4. Architecture (5 min)

```
Client → FastAPI → PostgreSQL (primary store)
                → Redis (cache / queue)
                → S3 (files)
                → Workers (async processing)
```

### 5. Python-Specific Decisions (3 min)

- Async vs sync endpoints
- Connection pooling (SQLAlchemy async pool)
- Background tasks vs task queue (Celery/ARQ)
- CPU-bound work: `ProcessPoolExecutor`

### 6. Scale & Production (4 min)

- Kubernetes + HPA
- Database read replicas
- Caching strategy (Redis TTL)
- Monitoring (RED metrics, Prometheus)

---

## Code Review Checklist

| Category | Check |
|----------|-------|
| **Types** | All function signatures have type hints? |
| **Types** | Pydantic models for all external data (API input/output, config)? |
| **Async** | No blocking calls inside `async def`? (requests, time.sleep, file IO) |
| **Async** | Using `httpx` (async) instead of `requests` (sync)? |
| **Resources** | Database sessions use `async with` or `Depends` with `yield`? |
| **Resources** | HTTP clients are shared (not created per request)? |
| **Security** | No f-strings in SQL queries? (use parameterized queries) |
| **Security** | Passwords hashed with bcrypt/argon2, never stored plaintext? |
| **Security** | Secrets from environment/config, never hardcoded? |
| **Security** | `response_model` used to prevent leaking internal fields? |
| **Errors** | Using `HTTPException` with correct status codes? (not returning error dicts) |
| **Errors** | `is None` instead of `== None`? |
| **Perf** | Filtering/sorting in the database, not in Python? |
| **Perf** | Pagination on all list endpoints? |
| **Perf** | No N+1 queries? (use `selectinload`/`joinedload`) |
| **Style** | `@functools.wraps` on all decorators? |
| **Style** | No mutable default arguments? (`def f(lst=[])` is a bug) |
| **Testing** | Using `dependency_overrides` instead of monkeypatching? |
| **Testing** | Async tests with `pytest-asyncio` and `httpx.AsyncClient`? |
