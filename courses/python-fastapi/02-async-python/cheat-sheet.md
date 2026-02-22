# Module 02 Cheat Sheet: Async Python

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

## gather vs TaskGroup

| | `asyncio.gather` | `asyncio.TaskGroup` |
|---|---|---|
| Cancel on failure | No | Yes (automatic) |
| Error handling | `return_exceptions=True` | `except*` ExceptionGroup |
| Scope | Unscoped | All tasks finish before exit |
| Python | 3.4+ | 3.11+ |
| Best for | Tolerating partial failures | Production, strict error handling |

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

## Sync-to-Async Conversion

```python
# HTTP:     requests.get(url)      -> await httpx.AsyncClient().get(url)
# Database: psycopg2.connect(dsn)  -> await asyncpg.connect(dsn)
# Files:    open("f").read()       -> await aiofiles.open("f").read()
# Sleep:    time.sleep(1)          -> await asyncio.sleep(1)
# Subprocess: subprocess.run(cmd)  -> await asyncio.create_subprocess_exec(*cmd)
# Bridge:   sync_func(arg)        -> await asyncio.to_thread(sync_func, arg)
```

## Common Pitfalls

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

## Async Testing Template

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

## FastAPI Sync vs Async Decision

```
Async I/O libs (asyncpg, httpx)?    -> async def
Sync I/O libs (psycopg2, requests)? -> def  (auto thread pool)
Fast computation (< 1ms)?           -> async def
Slow computation?                   -> def  or run_in_executor
```

## Quick Patterns

```python
# Concurrent fetch with limit
sem = asyncio.Semaphore(20)
async def limited_fetch(client, url):
    async with sem: return await client.get(url)
async with httpx.AsyncClient() as client:
    results = await asyncio.gather(*[limited_fetch(client, u) for u in urls])

# Retry with backoff
async def retry(coro_fn, retries=3, delay=1.0):
    for i in range(retries):
        try: return await coro_fn()
        except Exception:
            if i == retries - 1: raise
            await asyncio.sleep(delay * 2**i)

# Background worker in FastAPI
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
