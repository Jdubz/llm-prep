# Module 02 Deep Dive: Async Python Internals and Advanced Patterns

## 1. Event Loop Implementation Details

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

### Futures vs Coroutines vs Tasks

| Type | Description |
|------|-------------|
| **Future** | Low-level awaitable representing a pending result. Rarely created directly. |
| **Coroutine** | Result of calling `async def`. Must be awaited or wrapped in a Task. |
| **Task** | A Future wrapping a coroutine, scheduled on the event loop. Created by `create_task()`. |

---

## 2. Coroutine Internals: Generator-Based History

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

## 3. uvloop Performance

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

## 4. Async Testing Patterns

### pytest-asyncio Setup

```python
# pyproject.toml:
# [tool.pytest.ini_options]
# asyncio_mode = "auto"

# conftest.py
@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

@pytest.mark.anyio
async def test_read_items(client: AsyncClient):
    response = await client.get("/items")
    assert response.status_code == 200
```

### Mocking Async Dependencies

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    mock_db = AsyncMock()
    mock_db.fetch.return_value = [{"id": 1, "name": "test"}]

    with patch("app.services.get_db", return_value=mock_db):
        result = await list_users()
        mock_db.fetch.assert_awaited_once()

# AsyncMock: __call__ returns a coroutine (for async functions)
# MagicMock: __call__ returns a regular value (for sync functions)
```

### Testing Timeouts and Concurrency

```python
@pytest.mark.asyncio
async def test_timeout():
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.1):
            await asyncio.sleep(100)

@pytest.mark.asyncio
async def test_concurrent_safety():
    counter = {"value": 0}
    lock = asyncio.Lock()
    async def increment():
        async with lock:
            counter["value"] += 1
    async with asyncio.TaskGroup() as tg:
        for _ in range(100):
            tg.create_task(increment())
    assert counter["value"] == 100
```

---

## 5. Async Debugging Tools

```python
# Debug mode: detects unawaited coroutines, blocking calls, resource leaks
asyncio.run(main(), debug=True)
# Or: PYTHONASYNCIODEBUG=1 python app.py

# Inspect running tasks
for task in asyncio.all_tasks():
    print(f"{task.get_name()}: {'done' if task.done() else 'running'}")
    task.print_stack()

# Live debugging with aiomonitor
import aiomonitor
async def main():
    with aiomonitor.start_monitor(loop=asyncio.get_event_loop()):
        await run_server()
# Connect from another terminal: python -m aiomonitor.cli
```

---

## 6. Python GIL and Its Impact on Async

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

## 7. Comparison with Go Goroutines and Node.js

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

## 8. Advanced Async Patterns

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

## Summary

- The asyncio event loop is selector-based. uvloop replaces it with libuv for 2-4x better
  I/O performance.
- Coroutines are built on Python's generator protocol. The event loop drives them via
  `.send()` and `.throw()`.
- The GIL does not impact async I/O but prevents CPU parallelism in threads. Use
  `ProcessPoolExecutor` for CPU-bound work.
- Python async is closer to Node.js than Go: single-threaded, event-loop-based. The key
  difference is that Python I/O is blocking by default.
- Testing requires `pytest-asyncio` or `anyio`. Use `AsyncMock` for mocking and
  `dependency_overrides` for FastAPI integration tests.
- Advanced patterns (circuit breakers, rate limiters, retry) must be async-aware.
