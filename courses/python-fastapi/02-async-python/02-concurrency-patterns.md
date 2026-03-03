# 02 – Concurrency Patterns

## asyncio.gather (like Promise.all)

`gather` runs multiple coroutines concurrently on the same event loop and collects their results.

```python
# Concurrent -- takes ~0.1s instead of 0.3s
user1, user2, user3 = await asyncio.gather(
    fetch_user(1), fetch_user(2), fetch_user(3),
)

# With error handling (like Promise.allSettled)
results = await asyncio.gather(
    fetch_user(1), fetch_user(999),
    return_exceptions=True,
)
for r in results:
    if isinstance(r, Exception):
        print(f"Error: {r}")

# Filter successes
successes = [r for r in results if not isinstance(r, Exception)]
```

---

## TaskGroup: Structured Concurrency (Python 3.11+)

If any task fails, all others are cancelled automatically. Preferred over `gather` for new code.

```python
async with asyncio.TaskGroup() as tg:
    task1 = tg.create_task(fetch_user(1))
    task2 = tg.create_task(fetch_user(2))
    task3 = tg.create_task(fetch_posts(1))
# ExceptionGroup raised if any task fails; all others auto-cancelled
results = task1.result(), task2.result(), task3.result()
```

### gather vs TaskGroup Comparison

| Feature | `asyncio.gather` | `asyncio.TaskGroup` |
|---------|-------------------|---------------------|
| Cancel on failure | No (by default) | Yes (automatic) |
| Error handling | `return_exceptions=True` | `except*` ExceptionGroup |
| Scope | Unscoped | All tasks finish before exit |
| Python version | 3.4+ | 3.11+ |
| Best for | Tolerating partial failures | Production, strict error handling |
| Analogous to | `Promise.all()` / `allSettled()` | Go errgroup |

```python
# gather: tolerates failures
results = await asyncio.gather(a(), b(), return_exceptions=True)
successes = [r for r in results if not isinstance(r, Exception)]

# TaskGroup: cancels all on failure
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(a()); tg.create_task(b())
except* ValueError as eg:
    for exc in eg.exceptions: log.error(exc)
```

---

## Semaphores for Concurrency Limiting

Without limiting, a fan-out over 1000 URLs will open 1000 simultaneous connections and likely
exhaust OS limits, memory, and upstream rate limits.

```python
semaphore = asyncio.Semaphore(10)

async def limited_fetch(url: str):
    async with semaphore:
        async with httpx.AsyncClient() as client:
            return await client.get(url)

urls = [f"https://api.example.com/items/{i}" for i in range(1000)]
results = await asyncio.gather(*[limited_fetch(url) for url in urls])
```

Node.js equivalent: `p-limit`.

### Concurrent fetch with shared client and semaphore

```python
sem = asyncio.Semaphore(20)
async def limited_fetch(client, url):
    async with sem: return await client.get(url)
async with httpx.AsyncClient() as client:
    results = await asyncio.gather(*[limited_fetch(client, u) for u in urls])
```

---

## asyncio Synchronization Primitives

```python
# Timeouts
async with asyncio.timeout(5.0):                 # raises TimeoutError (3.11+)
    await slow_operation()
result = await asyncio.wait_for(coro(), timeout=5.0)

# Locks and semaphores
async with asyncio.Lock(): ...
async with asyncio.Semaphore(10): ...

# Events
event = asyncio.Event()
event.set(); await event.wait(); event.clear()

# Queues
q = asyncio.Queue(maxsize=100)
await q.put(item)                                # blocks if full
item = await q.get()                             # blocks if empty
q.task_done()
await q.join()                                   # wait for all items processed
```

---

## asyncio.Queue for Producer/Consumer

The producer/consumer pattern decouples work generation from work processing and naturally
applies backpressure via `maxsize`.

```python
NUM_CONSUMERS = 5

async def producer(queue: asyncio.Queue, urls: list[str]):
    for url in urls:
        await queue.put(url)
    for _ in range(NUM_CONSUMERS):
        await queue.put(None)  # sentinel

async def consumer(queue: asyncio.Queue, results: list, cid: int):
    async with httpx.AsyncClient() as client:
        while True:
            url = await queue.get()
            if url is None:
                queue.task_done()
                break
            try:
                results.append((await client.get(url)).json())
            except Exception as e:
                print(f"Consumer {cid} error: {e}")
            finally:
                queue.task_done()

async def crawl(urls: list[str]) -> list[dict]:
    queue = asyncio.Queue(maxsize=100)  # backpressure
    results = []
    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer(queue, urls))
        for i in range(NUM_CONSUMERS):
            tg.create_task(consumer(queue, results, i))
    return results
```

### Background Worker in FastAPI

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    queue = asyncio.Queue()
    app.state.queue = queue
    task = asyncio.create_task(worker(queue))
    yield
    await queue.put(None)
    await task

async def worker(queue: asyncio.Queue):
    while (item := await queue.get()) is not None:
        await process(item)
        queue.task_done()
```

---

## Error Handling in Concurrent Tasks

### ExceptionGroup (Python 3.11+)

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(might_fail("good"))
        tg.create_task(might_fail("bad"))
except* ValueError as eg:
    for exc in eg.exceptions:
        print(f"ValueError: {exc}")
except* TypeError as eg:
    for exc in eg.exceptions:
        print(f"TypeError: {exc}")
```

### Timeout Handling

```python
# Python 3.11+ (preferred)
async with asyncio.timeout(5.0):
    return await slow_operation()

# Older API
result = await asyncio.wait_for(slow_operation(), timeout=5.0)
```

---

## Connection Pooling with Async Drivers

### asyncpg (PostgreSQL)

```python
pool = await asyncpg.create_pool(
    dsn="postgresql://user:pass@localhost/db",
    min_size=5, max_size=20, command_timeout=30,
)

async with pool.acquire() as conn:
    rows = await conn.fetch("SELECT * FROM users WHERE id = $1", user_id)

# In FastAPI: create in lifespan, expose via dependency
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_pool = await asyncpg.create_pool(dsn=settings.database_url)
    yield
    await app.state.db_pool.close()
```

### httpx (HTTP Client)

```python
# DO: share a client with connection pooling
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    yield
    await app.state.http_client.aclose()

async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client

# DON'T: create a new client per request (no connection reuse)
```

httpx is preferred over aiohttp: requests-like API, sync+async support, HTTP/2, and
integrates with FastAPI testing via `ASGITransport`.

---

## Structured Concurrency with anyio

anyio is a compatibility layer for asyncio and trio. FastAPI/Starlette use it internally.

```python
import anyio

async with anyio.create_task_group() as tg:
    tg.start_soon(fetch_and_process, "https://api.example.com/a")
    tg.start_soon(fetch_and_process, "https://api.example.com/b")

limiter = anyio.CapacityLimiter(10)
async with limiter:
    await do_work()
```

---

## Advanced Async Patterns

### Retry with Exponential Backoff

```python
import functools

def async_retry(max_retries=3, base_delay=1.0, retry_on=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exc = e
                    if attempt < max_retries:
                        await asyncio.sleep(base_delay * 2**attempt)
            raise last_exc
        return wrapper
    return decorator

# Compact version
async def retry(coro_fn, retries=3, delay=1.0):
    for i in range(retries):
        try: return await coro_fn()
        except Exception:
            if i == retries - 1: raise
            await asyncio.sleep(delay * 2**i)
```

### Circuit Breaker

```python
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"       # normal
    OPEN = "open"           # failing -- reject immediately
    HALF_OPEN = "half_open" # testing -- allow one request

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30.0,
                 expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpen("Circuit is open")
        try:
            result = await func(*args, **kwargs)
        except self.expected_exception:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.monotonic()
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
            raise
        else:
            async with self._lock:
                self.failure_count = 0
                self.state = CircuitState.CLOSED
            return result
```

### Token Bucket Rate Limiter

```python
class AsyncTokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.capacity,
                              self.tokens + (now - self.last_refill) * self.rate)
            self.last_refill = now
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def wait_and_acquire(self, tokens: int = 1):
        while not await self.acquire(tokens):
            await asyncio.sleep(1 / self.rate)
```

---

## asyncio API Quick Reference

```python
import asyncio

# Running async code
asyncio.run(main())                              # create loop, run, close
await asyncio.sleep(seconds)                     # async sleep (yields to loop)

# Creating tasks
task = asyncio.create_task(coro(), name="name")  # schedule on loop
task.cancel()                                     # request cancellation
task.done()                                       # check if finished
result = task.result()                            # get result (raises if failed)

# Concurrent execution
results = await asyncio.gather(c1(), c2(), c3())
results = await asyncio.gather(c1(), c2(), return_exceptions=True)

async with asyncio.TaskGroup() as tg:            # structured (3.11+)
    t1 = tg.create_task(coro1())
    t2 = tg.create_task(coro2())

# Timeouts
async with asyncio.timeout(5.0):                 # raises TimeoutError (3.11+)
    await slow_operation()
result = await asyncio.wait_for(coro(), timeout=5.0)

# Synchronization
async with asyncio.Lock(): ...
async with asyncio.Semaphore(10): ...
event = asyncio.Event()
event.set(); await event.wait(); event.clear()

# Queues
q = asyncio.Queue(maxsize=100)
await q.put(item)                                # blocks if full
item = await q.get()                             # blocks if empty
q.task_done()
await q.join()                                   # wait for all items processed

# Blocking code
result = await asyncio.to_thread(func, arg1)     # (3.9+)
result = await loop.run_in_executor(pool, func, arg)

# Inspection
asyncio.all_tasks()                              # all tasks in loop
asyncio.current_task()                           # currently running task
```

---

## Key Takeaways

- Prefer `TaskGroup` over `gather` for structured concurrency with automatic error propagation.
- Always limit concurrency with `Semaphore` for fan-out operations.
- Create connection pools once at startup, share via dependencies.
- Use `asyncio.Queue` for producer/consumer decoupling with built-in backpressure.
- Async patterns (circuit breakers, rate limiters, retry) must be async-aware to avoid blocking.
