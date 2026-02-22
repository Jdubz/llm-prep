# Module 02: Async Python Deep Dive

## Prerequisites

You should be comfortable with async/await in JavaScript/TypeScript. This module maps Python's
asyncio to the Node.js event loop you know, highlights critical differences, and covers advanced
patterns for production FastAPI applications.

---

## 1. The Event Loop: asyncio vs Node.js

### Node.js Mental Model

Single event loop (libuv), I/O is non-blocking by default, one implicit loop per process.

### Python asyncio Mental Model

Similar single-threaded event loop, but with key differences:

1. You must **explicitly create and run** the event loop (via `asyncio.run()`)
2. The event loop **only runs async code** -- sync code blocks the loop
3. There is **no automatic async I/O** -- you must use async-aware libraries
4. Multiple event loop implementations exist (default, uvloop, etc.)

```python
import asyncio

async def main():
    data = await fetch(url)
    result = await db.execute(sql)

asyncio.run(main())  # creates loop, runs, closes
```

### Critical Difference: Blocking Behavior

In Node.js, almost all stdlib functions are non-blocking. In Python, **almost all stdlib
functions are blocking**. This is the number one source of bugs.

```python
async def bad_example():
    time.sleep(5)         # BLOCKS the event loop -- all requests stall

async def good_example():
    await asyncio.sleep(5)  # YIELDS to the event loop

# Blocking operations that freeze your FastAPI server:
# time.sleep()       -> asyncio.sleep()
# open() / file I/O  -> aiofiles
# requests.get()     -> httpx / aiohttp
# psycopg2           -> asyncpg / psycopg3 (async mode)
# subprocess.run()   -> asyncio.create_subprocess_exec()
# CPU computation    -> run_in_executor()
```

### Event Loop Cycle

1. Run all callbacks in the ready queue
2. Poll for I/O events (with timeout based on nearest scheduled callback)
3. Move I/O-ready callbacks to the ready queue
4. Fire scheduled callbacks whose time has arrived
5. Repeat

---

## 2. async/await Patterns

### Basic Coroutines

```python
async def fetch_user(user_id: int) -> dict:
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": f"User {user_id}"}

coro = fetch_user(1)   # returns coroutine object, NOT a dict
user = await fetch_user(1)  # actually executes
```

### asyncio.gather (like Promise.all)

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
```

### TaskGroup: Structured Concurrency (Python 3.11+)

If any task fails, all others are cancelled automatically. Preferred over `gather`.

```python
async with asyncio.TaskGroup() as tg:
    task1 = tg.create_task(fetch_user(1))
    task2 = tg.create_task(fetch_user(2))
    task3 = tg.create_task(fetch_posts(1))
# ExceptionGroup raised if any task fails; all others auto-cancelled
results = task1.result(), task2.result(), task3.result()
```

| Feature | `asyncio.gather` | `asyncio.TaskGroup` |
|---------|-------------------|---------------------|
| Cancel on failure | No (by default) | Yes (automatic) |
| Error handling | `return_exceptions=True` | ExceptionGroup |
| Structured | No | Yes (all tasks scoped) |
| Python version | 3.4+ | 3.11+ |
| Analogous to | `Promise.all()` / `allSettled()` | Go errgroup |

### Semaphores for Concurrency Limiting

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

---

## 3. Async Context Managers and Generators

```python
from contextlib import asynccontextmanager

# Class-based
class DatabaseConnection:
    async def __aenter__(self):
        self.conn = await asyncpg.connect(DATABASE_URL)
        return self.conn
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()

# Function-based
@asynccontextmanager
async def get_connection():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# Async generator
async def fetch_pages(url: str):
    page = 1
    while True:
        async with httpx.AsyncClient() as client:
            data = (await client.get(f"{url}?page={page}")).json()
        if not data["items"]:
            return
        yield data["items"]
        page += 1

async for page_items in fetch_pages("https://api.example.com/items"):
    for item in page_items:
        process(item)
```

---

## 4. Connection Pooling with Async Drivers

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

## 5. Structured Concurrency with anyio

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

## 6. Async Iterators and `async for`

```python
class AsyncPaginator:
    def __init__(self, client: httpx.AsyncClient, url: str, page_size: int = 100):
        self.client, self.url, self.page_size = client, url, page_size
        self.page, self.done = 0, False

    def __aiter__(self):
        return self

    async def __anext__(self) -> list[dict]:
        if self.done:
            raise StopAsyncIteration
        response = await self.client.get(
            self.url, params={"offset": self.page * self.page_size, "limit": self.page_size},
        )
        items = response.json()["items"]
        if len(items) < self.page_size:
            self.done = True
        if not items:
            raise StopAsyncIteration
        self.page += 1
        return items

# Async comprehension
all_items = [item async for page in paginator for item in page]
```

---

## 7. asyncio.Queue for Producer/Consumer

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

---

## 8. Error Handling in Concurrent Tasks

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

## 9. Sync vs Async in FastAPI

```python
# ASYNC: runs on the event loop. Use with async libraries.
@app.get("/async")
async def async_handler():
    return await db.fetch("SELECT * FROM users")

# SYNC: FastAPI auto-runs in thread pool. Use with blocking libraries.
@app.get("/sync")
def sync_handler():
    return db.query("SELECT * FROM users")
```

**Critical rule**: `async def` with ANY blocking call freezes the entire event loop.
Plain `def` is safe because FastAPI uses a thread pool.

### Decision Matrix

```
I/O with async libraries (asyncpg, httpx)?  -> async def
I/O with sync libraries (psycopg2, requests)? -> def (thread pool)
Fast computation (< 1ms)?                    -> async def
Slow computation?                            -> def or run_in_executor
```

### The Gotcha

```python
# BAD: async + sync library = blocks event loop
@app.get("/bad")
async def bad():
    return requests.get("https://example.com").json()

# GOOD: sync handler = auto thread pool
@app.get("/good")
def good():
    return requests.get("https://example.com").json()

# BEST: async + async library
@app.get("/best")
async def best():
    async with httpx.AsyncClient() as client:
        return (await client.get("https://example.com")).json()
```

---

## 10. Running Blocking Code

```python
# asyncio.to_thread (Python 3.9+) -- simplest
result = await asyncio.to_thread(cpu_intensive_work, data)

# run_in_executor -- more control
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

thread_pool = ThreadPoolExecutor(max_workers=10)   # I/O-bound blocking
process_pool = ProcessPoolExecutor(max_workers=4)  # CPU-bound (bypasses GIL)

loop = asyncio.get_running_loop()
io_result = await loop.run_in_executor(thread_pool, blocking_io_func)
cpu_result = await loop.run_in_executor(process_pool, cpu_func, arg1)
```

| Blocking Work | Solution |
|---------------|----------|
| Sync HTTP/DB | `asyncio.to_thread()` or async driver |
| File I/O | `aiofiles` or `asyncio.to_thread()` |
| CPU computation | `ProcessPoolExecutor` (threads don't help due to GIL) |
| subprocess | `asyncio.create_subprocess_exec()` |

---

## 11. Debugging Async Code

### Common Bugs

```python
# Bug 1: Forgetting await
result = fetch_user(1)    # coroutine object, not a User!
# Fix: result = await fetch_user(1)

# Bug 2: Blocking the loop
time.sleep(10)            # freezes everything
# Fix: await asyncio.sleep(10)

# Bug 3: Fire-and-forget tasks get GC'd
asyncio.create_task(coro())  # may disappear
# Fix: use TaskGroup or store reference

# Bug 4: Mutable state without locks
counter += 1               # race condition across await points
# Fix: async with asyncio.Lock(): counter += 1
```

### Debug Mode

```python
asyncio.run(main(), debug=True)  # or PYTHONASYNCIODEBUG=1
# Detects: unawaited coroutines, blocking calls, resource leaks
```

---

## Interview Questions

### Conceptual

1. **How does asyncio differ from Node.js event loop?**
   Both single-threaded, but: Python I/O blocks by default (must use async libs), Python loops
   are explicit, Python has the GIL, Node uses libuv (C) while Python uses selectors.

2. **When to use `def` vs `async def` in FastAPI?**
   `async def` for async I/O. Plain `def` for blocking/sync code (auto thread pool). Never
   `async def` with blocking calls.

3. **`gather` vs `TaskGroup`?**
   `gather` doesn't auto-cancel siblings. `TaskGroup` provides structured concurrency with
   auto-cancellation and `ExceptionGroup`. Prefer `TaskGroup` for new code.

4. **How to limit concurrency?**
   `asyncio.Semaphore` or `anyio.CapacityLimiter`. Pool `max_size` for connections.

5. **GIL's impact on async?**
   No impact on I/O (single-threaded anyway, GIL released during waits). Prevents CPU
   parallelism in threads -- use `ProcessPoolExecutor`.

6. **What happens if you forget `await`?**
   Coroutine created but never executed. `RuntimeWarning` emitted. Silent data loss.

### Coding Challenges

7. **Implement async retry decorator** with exponential backoff:
   ```python
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
   ```

8. **Write a producer/consumer system** with `asyncio.Queue`, 3 producers, 5 consumers,
   max queue size 50, graceful shutdown.

9. **Fetch from 3 sources concurrently** -- use primary if it responds within 2s, otherwise
   use whichever secondary responds first.

### System Design

10. **Design an async scraper** for 10,000 URLs: producer/consumer with `asyncio.Queue`,
    `Semaphore(50)` for HTTP, retries, batch DB inserts via asyncpg, `TaskGroup` for errors.

11. **Database pooling for 1000 concurrent requests**: pool in `lifespan`, size =
    `pool_size * num_workers < max_connections`, yield dependency, timeout on pool exhaustion.

---

## Key Takeaways

- Python async is **opt-in** -- sync libraries block the loop. Opposite of Node.js.
- `async def` for async I/O, plain `def` for blocking code. FastAPI handles threading.
- Prefer `TaskGroup` over `gather` for structured concurrency.
- Always limit concurrency with `Semaphore` for fan-out operations.
- Create connection pools once at startup, share via dependencies.
- GIL: no impact on I/O, use `ProcessPoolExecutor` for CPU parallelism.
- `asyncio.to_thread()` is the simplest way to bridge blocking code.
