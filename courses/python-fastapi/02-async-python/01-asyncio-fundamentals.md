# 01 – asyncio Fundamentals

## Prerequisites

You should be comfortable with async/await in JavaScript/TypeScript. This module maps Python's
asyncio to the Node.js event loop you know, highlights critical differences, and covers advanced
patterns for production FastAPI applications.

---

## The Event Loop: asyncio vs Node.js

### Node.js Mental Model

Single event loop (libuv), I/O is non-blocking by default, one implicit loop per process.

### Python asyncio Mental Model

Similar single-threaded event loop, but with key differences:

1. You must **explicitly create and run** the event loop (via `asyncio.run()`)
2. The event loop **only runs async code** — sync code blocks the loop
3. There is **no automatic async I/O** — you must use async-aware libraries
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

## Event Loop Implementation Details

### The Selector-Based Event Loop

Python's default event loop uses the `selectors` module wrapping OS-level I/O multiplexing:
Linux `epoll`, macOS `kqueue`, Windows `IOCP` (via `ProactorEventLoop`).

```python
# Simplified event loop internals
class _EventLoop:
    _ready: collections.deque         # callbacks ready to run NOW
    _scheduled: list                  # heap of TimerHandle (sorted by when)
    _selector: selectors.BaseSelector # I/O multiplexer

    def _run_once(self):
        # 1. Calculate timeout until next scheduled callback
        timeout = self._calculate_timeout()
        # 2. Poll for I/O events (blocks for at most timeout seconds)
        event_list = self._selector.select(timeout)
        # 3. Process I/O events -> add callbacks to _ready
        for key, mask in event_list:
            self._process_io_event(key, mask)
        # 4. Move due scheduled callbacks to _ready
        now = self.time()
        while self._scheduled and self._scheduled[0].when <= now:
            self._ready.append(heapq.heappop(self._scheduled))
        # 5. Run all ready callbacks
        for _ in range(len(self._ready)):
            self._ready.popleft()._run()
```

### How Coroutines Suspend

When you `await`, the coroutine yields control to the event loop via the generator protocol:

```python
# What happens when you await asyncio.sleep(1):
# 1. asyncio.sleep(1) creates a Future
# 2. Registers callback: call_later(1, future.set_result, None)
# 3. Coroutine yields the Future to the event loop
# 4. Event loop runs other coroutines
# 5. After 1 second, callback fires, setting the Future's result
# 6. Event loop resumes the coroutine where it left off
```

---

## Coroutine Internals: Generator-Based History

### The Evolution

```python
# Phase 1: Callbacks (Twisted-style)
def fetch(url, callback):
    io_loop.add_handler(socket, callback)

# Phase 2: Generator-based coroutines (Python 3.3, PEP 380)
@asyncio.coroutine
def fetch(url):
    response = yield from aiohttp.request('GET', url)
    return response

# Phase 3: Native coroutines (Python 3.5, PEP 492)
async def fetch(url):
    response = await aiohttp.request('GET', url)
    return response
```

Native coroutines implement the generator protocol (`.send()`, `.throw()`, `.close()`).
The event loop drives them by calling `.send(result)` when awaited Futures complete. This
heritage explains why forgetting `await` creates a coroutine object instead of executing code.

---

## Futures, Coroutines, and Tasks

| Type | Description |
|------|-------------|
| **Future** | Low-level awaitable representing a pending result. Rarely created directly. |
| **Coroutine** | Result of calling `async def`. Must be awaited or wrapped in a Task. |
| **Task** | A Future wrapping a coroutine, scheduled on the event loop. Created by `create_task()`. |

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

# Inspection
asyncio.all_tasks()                              # all tasks in loop
asyncio.current_task()                           # currently running task
```

---

## Basic Coroutines

```python
async def fetch_user(user_id: int) -> dict:
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": f"User {user_id}"}

coro = fetch_user(1)   # returns coroutine object, NOT a dict
user = await fetch_user(1)  # actually executes
```

---

## Async Context Managers and Generators

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

## Async Iterators and `async for`

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

## Sync vs Async in FastAPI

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
Async I/O libs (asyncpg, httpx)?    -> async def
Sync I/O libs (psycopg2, requests)? -> def  (auto thread pool)
Fast computation (< 1ms)?           -> async def
Slow computation?                   -> def  or run_in_executor
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

## Running Blocking Code from Async

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

### Sync-to-Async Library Conversion

```python
# HTTP:     requests.get(url)      -> await httpx.AsyncClient().get(url)
# Database: psycopg2.connect(dsn)  -> await asyncpg.connect(dsn)
# Files:    open("f").read()       -> await aiofiles.open("f").read()
# Sleep:    time.sleep(1)          -> await asyncio.sleep(1)
# Subprocess: subprocess.run(cmd)  -> await asyncio.create_subprocess_exec(*cmd)
# Bridge:   sync_func(arg)        -> await asyncio.to_thread(sync_func, arg)
```

---

## The Python GIL and Its Impact on Async

The GIL (Global Interpreter Lock) allows only one thread to execute Python bytecode at a time.

**GIL does NOT impact async I/O**: the event loop is single-threaded anyway, and the GIL is
released during I/O waits (network, disk).

**GIL IS a problem for CPU-bound threading**:

```python
# THREADS: GIL serializes CPU work (no true parallelism)
thread_pool = ThreadPoolExecutor(max_workers=4)
results = await asyncio.gather(
    loop.run_in_executor(thread_pool, cpu_work, data1),
    loop.run_in_executor(thread_pool, cpu_work, data2),
)  # NOT parallel

# PROCESSES: true parallelism (separate GIL per process)
process_pool = ProcessPoolExecutor(max_workers=4)
results = await asyncio.gather(
    loop.run_in_executor(process_pool, cpu_work, data1),
    loop.run_in_executor(process_pool, cpu_work, data2),
)  # PARALLEL
```

**Free-threaded Python (PEP 703)**: Python 3.13+ has an experimental GIL-free build
(`python3.13t`) enabling true thread parallelism. Still experimental as of early 2026.

---

## uvloop Performance

uvloop is a drop-in replacement for asyncio's event loop, written in Cython on top of
libuv (the same C library powering Node.js).

```python
import uvloop
uvloop.install()  # before any asyncio code
# Or: Uvicorn uses uvloop by default when installed
```

| Workload | Improvement |
|----------|-------------|
| Many small HTTP requests | 2-4x |
| WebSocket connections | 2-3x |
| Database queries (asyncpg) | 1.5-2x |
| CPU-bound work | None |

uvloop helps when the bottleneck is event loop I/O overhead. If your bottleneck is CPU
(serialization, computation), it will not help.

---

## Comparison with Go Goroutines and Node.js

| Feature | Node.js | Python asyncio | Go goroutines |
|---------|---------|----------------|---------------|
| Threading model | Single thread | Single thread | M:N (many:fewer threads) |
| I/O model | Non-blocking default | Blocking default (opt-in) | Blocking syntax, async runtime |
| CPU parallelism | worker_threads | ProcessPoolExecutor | Native (multiple cores) |
| Memory per unit | ~1KB/callback | ~2KB/coroutine | ~4KB/goroutine (growable) |
| Concurrency limit | Event loop capacity | Event loop capacity | Millions of goroutines |
| Error model | Promises/try-catch | try/except + ExceptionGroup | (val, err) returns |
| Cancellation | AbortController | task.cancel() | context.Context |
| Channel-like | EventEmitter | asyncio.Queue | chan (first-class) |

### Practical Implications for FastAPI

1. **Python async is opt-in**: you must choose async libraries. Node stdlib is async. Go's
   runtime handles it transparently.
2. **Concurrency, not parallelism**: asyncio gives interleaved execution on one thread. For
   parallelism, use processes. Same as Node.js. Go doesn't have this limitation.
3. **The async/sync boundary**: crossing requires explicit bridging (`run_in_executor`,
   `asyncio.run`). In Go, there is no such boundary.

---

## Practice Exercises

The following exercises in `exercises.py` practice the concepts from this file. See also `examples.py` for fully working reference implementations.

- **Exercise 1: Convert Synchronous Code to Async** -- Convert a blocking sequential fetch loop into concurrent async code using `asyncio.gather` and `await`. Practices the core async/await syntax and the difference between sync and async execution. *(Also see: `examples.py` Example 1 -- Parallel HTTP Fetching with Semaphore)*

---

## Key Takeaways

- Python async is **opt-in** — sync libraries block the loop. Opposite of Node.js.
- `async def` for async I/O, plain `def` for blocking code. FastAPI handles threading.
- The asyncio event loop is selector-based. uvloop replaces it with libuv for 2-4x better I/O.
- Coroutines are built on Python's generator protocol. The event loop drives them via `.send()`.
- The GIL does not impact async I/O but prevents CPU parallelism in threads.
- `asyncio.to_thread()` is the simplest way to bridge blocking code.
