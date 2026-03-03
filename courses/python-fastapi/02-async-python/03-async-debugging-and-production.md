# 03 – Async Debugging and Production

## Common Bugs in Async Code

```python
# Bug 1: Forgetting await
result = fetch_user(1)    # coroutine object, not a User!
# Fix: result = await fetch_user(1)

# Bug 2: Blocking the loop
time.sleep(10)            # freezes everything
# Fix: await asyncio.sleep(10)

# Bug 3: Fire-and-forget tasks get GC'd
asyncio.create_task(coro())  # may disappear if no reference held
# Fix: use TaskGroup or store reference

# Bug 4: Mutable state without locks
counter += 1               # race condition across await points
# Fix: async with asyncio.Lock(): counter += 1
```

---

## Common Pitfalls Reference

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Blocking in `async def` | All requests stall | Async library or `to_thread()` |
| Forgetting `await` | RuntimeWarning: never awaited | Add `await` |
| Tasks without references | Silently disappear (GC) | `TaskGroup` or store ref |
| Unbounded concurrency | Connection errors, OOM | `Semaphore` / pool limits |
| Mutable state, no lock | Race conditions | `asyncio.Lock()` |
| `async def` + sync DB | Event loop blocks | Use plain `def` |
| Client per request | Port exhaustion | Share via lifespan |
| `asyncio.run()` in async | RuntimeError: loop running | `await` directly |
| CPU in thread pool | GIL blocks parallelism | `ProcessPoolExecutor` |

---

## Debug Mode

```python
asyncio.run(main(), debug=True)  # or PYTHONASYNCIODEBUG=1
# Detects: unawaited coroutines, blocking calls, resource leaks
```

---

## Async Debugging Tools

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

## Async Testing Patterns

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

### Async Test Template

```python
# pyproject.toml: asyncio_mode = "auto"

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

@pytest.fixture
async def client():
    app.dependency_overrides[get_db] = lambda: FakeDB()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_endpoint(client):
    assert (await client.get("/items")).status_code == 200

@pytest.mark.asyncio
async def test_mock():
    mock = AsyncMock(return_value={"id": 1})
    assert (await mock())["id"] == 1
    mock.assert_awaited_once()
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

## Production Patterns

### Blocking Code Detection

The main technique for detecting accidental blocking calls in production is to set a low
`slow_callback_duration` in debug mode and monitor the asyncio logger for warnings:

```python
import asyncio
import logging

logging.getLogger("asyncio").setLevel(logging.DEBUG)
loop = asyncio.get_event_loop()
loop.slow_callback_duration = 0.1  # warn if callback > 100ms
```

### Structured Logging for Async Context

In async services, task boundaries don't map 1:1 to requests. Use `contextvars` to propagate
request IDs through the async call stack:

```python
import contextvars

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Anywhere in the async call stack:
def get_logger():
    return logging.LoggerAdapter(logger, {"request_id": request_id_var.get()})
```

### Health Checks for Async Resources

```python
@app.get("/health")
async def health_check(request: Request):
    checks = {}
    try:
        await request.app.state.db_pool.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    try:
        await request.app.state.http_client.get("https://api.example.com/ping", timeout=2.0)
        checks["external_api"] = "ok"
    except Exception as e:
        checks["external_api"] = f"error: {e}"
    status_code = 200 if all(v == "ok" for v in checks.values()) else 503
    return JSONResponse(checks, status_code=status_code)
```

---

## Interview Questions

### Conceptual

**1. How does asyncio differ from Node.js event loop?**

Both single-threaded, but: Python I/O blocks by default (must use async libs), Python loops
are explicit, Python has the GIL, Node uses libuv (C) while Python uses selectors.

**2. When to use `def` vs `async def` in FastAPI?**

`async def` for async I/O. Plain `def` for blocking/sync code (auto thread pool). Never
`async def` with blocking calls.

**3. `gather` vs `TaskGroup`?**

`gather` doesn't auto-cancel siblings. `TaskGroup` provides structured concurrency with
auto-cancellation and `ExceptionGroup`. Prefer `TaskGroup` for new code.

**4. How to limit concurrency?**

`asyncio.Semaphore` or `anyio.CapacityLimiter`. Pool `max_size` for connections.

**5. GIL's impact on async?**

No impact on I/O (single-threaded anyway, GIL released during waits). Prevents CPU
parallelism in threads — use `ProcessPoolExecutor`.

**6. What happens if you forget `await`?**

Coroutine created but never executed. `RuntimeWarning` emitted. Silent data loss.

### Coding Challenges

**7. Implement async retry decorator** with exponential backoff:

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

**8. Write a producer/consumer system** with `asyncio.Queue`, 3 producers, 5 consumers,
max queue size 50, graceful shutdown.

**9. Fetch from 3 sources concurrently** — use primary if it responds within 2s, otherwise
use whichever secondary responds first.

### System Design

**10. Design an async scraper** for 10,000 URLs: producer/consumer with `asyncio.Queue`,
`Semaphore(50)` for HTTP, retries, batch DB inserts via asyncpg, `TaskGroup` for errors.

**11. Database pooling for 1000 concurrent requests**: pool in `lifespan`, size =
`pool_size * num_workers < max_connections`, yield dependency, timeout on pool exhaustion.

---

## Key Takeaways

- Enable debug mode (`PYTHONASYNCIODEBUG=1`) to catch unawaited coroutines and blocking calls.
- Use `AsyncMock` for mocking async functions; `MagicMock` for sync.
- Use `contextvars` to propagate request context through async call stacks.
- Health checks should test async resources (DB pool, HTTP client) with timeouts.
- Advanced patterns (circuit breakers, rate limiters, retry) must be async-aware.
- Testing requires `pytest-asyncio` or `anyio`. Use `dependency_overrides` for FastAPI tests.
