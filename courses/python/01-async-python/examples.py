"""
Module 02: Async Python Deep Dive -- Runnable Examples
======================================================

Complete, self-contained async Python patterns using only the stdlib.
Run the whole file:  python examples.py
Each example prints its own header and results.

Assumes Python 3.11+ for TaskGroup and asyncio.timeout.
"""

import asyncio
import functools
import random
import time
from contextlib import asynccontextmanager


# ---------------------------------------------------------------------------
# Helper: simulated async HTTP fetch (no external packages needed)
# ---------------------------------------------------------------------------

async def _simulated_fetch(url: str, *, delay: float | None = None) -> dict:
    """Simulate an HTTP GET that takes 0.1-0.5s.

    In production you would use httpx.AsyncClient here.
    """
    d = delay if delay is not None else random.uniform(0.1, 0.5)
    await asyncio.sleep(d)
    return {"url": url, "status": 200, "latency_ms": round(d * 1000)}


def _banner(title: str) -> None:
    width = 72
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


# ===========================================================================
# EXAMPLE 1: Parallel Fetching with Semaphore-Limited Concurrency
# ===========================================================================
# Node.js equivalent:
#   import pLimit from 'p-limit';
#   const limit = pLimit(5);
#   const results = await Promise.all(urls.map(u => limit(() => fetch(u))));

async def example_parallel_fetch() -> None:
    _banner("Example 1: Parallel HTTP Fetching with Semaphore")

    MAX_CONCURRENT = 5
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    active = 0  # track how many are in-flight at once (for demo)
    peak = 0

    async def limited_fetch(url: str) -> dict:
        nonlocal active, peak
        async with semaphore:
            active += 1
            peak = max(peak, active)
            result = await _simulated_fetch(url)
            active -= 1
            return result

    urls = [f"https://api.example.com/items/{i}" for i in range(20)]

    t0 = time.perf_counter()
    results = await asyncio.gather(*[limited_fetch(u) for u in urls])
    elapsed = time.perf_counter() - t0

    print(f"  Fetched {len(results)} URLs in {elapsed:.2f}s")
    print(f"  Peak concurrency: {peak}  (limit was {MAX_CONCURRENT})")
    print(f"  Sample result: {results[0]}")


# ===========================================================================
# EXAMPLE 2: Async Context Manager -- Connection Pool Simulator
# ===========================================================================
# Shows both class-based and decorator-based async context managers.
# Node.js has no direct equivalent; closest is try/finally with manual cleanup.

class AsyncConnectionPool:
    """Simulates a database connection pool with acquire/release semantics."""

    def __init__(self, pool_size: int = 3):
        self._pool_size = pool_size
        self._semaphore: asyncio.Semaphore | None = None
        self._connections: list[int] = []
        self._next_id = 0

    async def open(self) -> None:
        self._semaphore = asyncio.Semaphore(self._pool_size)
        for _ in range(self._pool_size):
            self._connections.append(self._next_id)
            self._next_id += 1
        print(f"    Pool opened with {self._pool_size} connections: {self._connections}")

    async def close(self) -> None:
        self._connections.clear()
        print("    Pool closed -- all connections released")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool, release when done."""
        assert self._semaphore is not None, "Pool not opened"
        async with self._semaphore:
            conn_id = self._connections.pop(0)
            try:
                yield conn_id
            finally:
                self._connections.append(conn_id)

    # Support using the pool itself as an async context manager (lifespan)
    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


async def example_connection_pool() -> None:
    _banner("Example 2: Async Context Manager -- Connection Pool")

    async with AsyncConnectionPool(pool_size=2) as pool:
        async def do_query(name: str) -> None:
            async with pool.acquire() as conn_id:
                print(f"    {name} acquired conn {conn_id}")
                await asyncio.sleep(0.2)  # simulate query
                print(f"    {name} releasing conn {conn_id}")

        # 4 tasks compete for 2 connections
        await asyncio.gather(
            do_query("Task-A"),
            do_query("Task-B"),
            do_query("Task-C"),
            do_query("Task-D"),
        )


# ===========================================================================
# EXAMPLE 3: Producer/Consumer with asyncio.Queue
# ===========================================================================
# Node.js equivalent: no stdlib equivalent; you would typically use a stream
# pipeline or a library like p-queue.

async def example_producer_consumer() -> None:
    _banner("Example 3: Producer/Consumer with asyncio.Queue")

    NUM_CONSUMERS = 3
    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=5)  # backpressure
    results: list[dict] = []

    async def producer(urls: list[str]) -> None:
        for url in urls:
            await queue.put(url)  # blocks if queue is full (backpressure)
            print(f"    [producer] enqueued {url}")
        # Send poison pills to shut down consumers
        for _ in range(NUM_CONSUMERS):
            await queue.put(None)
        print("    [producer] done, sent shutdown signals")

    async def consumer(cid: int) -> None:
        while True:
            url = await queue.get()
            if url is None:
                queue.task_done()
                print(f"    [consumer-{cid}] shutting down")
                break
            try:
                data = await _simulated_fetch(url, delay=0.1)
                results.append(data)
                print(f"    [consumer-{cid}] processed {url}")
            except Exception as e:
                print(f"    [consumer-{cid}] error on {url}: {e}")
            finally:
                queue.task_done()

    urls = [f"https://api.example.com/page/{i}" for i in range(8)]

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer(urls))
        for i in range(NUM_CONSUMERS):
            tg.create_task(consumer(i))

    print(f"  Collected {len(results)} results")


# ===========================================================================
# EXAMPLE 4: Structured Concurrency with TaskGroup (Python 3.11+)
# ===========================================================================
# TaskGroup auto-cancels sibling tasks on failure -- no Node.js equivalent.
# Closest JS analogy: Promise.all() rejects on first failure, but does NOT
# cancel in-flight promises.

async def example_taskgroup() -> None:
    _banner("Example 4: Structured Concurrency with TaskGroup")

    async def fetch_user(uid: int) -> dict:
        await asyncio.sleep(0.1)
        return {"id": uid, "name": f"User-{uid}"}

    async def fetch_posts(uid: int) -> list[dict]:
        await asyncio.sleep(0.15)
        return [{"post_id": i, "author": uid} for i in range(3)]

    # All tasks scoped to the TaskGroup; if one fails, others are cancelled
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(fetch_user(42))
        posts_task = tg.create_task(fetch_posts(42))
        extra_task = tg.create_task(fetch_user(99))

    user = user_task.result()
    posts = posts_task.result()
    extra = extra_task.result()
    print(f"  User:  {user}")
    print(f"  Posts: {posts}")
    print(f"  Extra: {extra}")

    # Demonstrating error handling with except*
    print("\n  --- TaskGroup with failure ---")

    async def might_fail(label: str) -> str:
        await asyncio.sleep(0.05)
        if label == "bad":
            raise ValueError(f"Simulated failure in '{label}'")
        return f"{label} ok"

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(might_fail("good"))
            tg.create_task(might_fail("bad"))
            tg.create_task(might_fail("also-good"))
    except* ValueError as eg:
        for exc in eg.exceptions:
            print(f"  Caught ValueError: {exc}")


# ===========================================================================
# EXAMPLE 5: Async Generator for Streaming Data
# ===========================================================================
# Node.js equivalent: async function* / for await...of (ES2018).

async def example_async_generator() -> None:
    _banner("Example 5: Async Generator for Streaming Data")

    async def paginated_fetch(base_url: str, total_pages: int = 4):
        """Yields one page of items at a time, simulating API pagination."""
        for page in range(1, total_pages + 1):
            await asyncio.sleep(0.1)  # simulate network
            items = [{"id": (page - 1) * 3 + i, "page": page} for i in range(3)]
            yield items
        # generator returns implicitly -- no more pages

    all_items: list[dict] = []
    async for page_items in paginated_fetch("https://api.example.com/items"):
        print(f"  Received page with {len(page_items)} items: ids={[i['id'] for i in page_items]}")
        all_items.extend(page_items)

    print(f"  Total items collected: {len(all_items)}")

    # Async comprehension
    ids = [item["id"] async for page in paginated_fetch("https://api.example.com/items") for item in page]
    print(f"  IDs via async comprehension: {ids}")


# ===========================================================================
# EXAMPLE 6: Token Bucket Rate Limiter
# ===========================================================================
# Node.js equivalent: bottleneck or custom leaky-bucket implementation.

class TokenBucketRateLimiter:
    """Async-friendly token bucket rate limiter.

    Args:
        rate: tokens added per second
        capacity: maximum tokens in the bucket
    """

    def __init__(self, rate: float, capacity: int):
        self._rate = rate
        self._capacity = capacity
        self._tokens = float(capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> None:
        """Wait until the requested number of tokens are available."""
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
            # Estimate wait time until enough tokens accumulate
            wait = tokens / self._rate
            await asyncio.sleep(wait)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now


async def example_rate_limiter() -> None:
    _banner("Example 6: Token Bucket Rate Limiter")

    # Allow 5 requests/second, burst up to 5
    limiter = TokenBucketRateLimiter(rate=5, capacity=5)
    timestamps: list[float] = []

    async def rate_limited_fetch(url: str) -> dict:
        await limiter.acquire()
        ts = time.perf_counter()
        timestamps.append(ts)
        return await _simulated_fetch(url, delay=0.01)

    t0 = time.perf_counter()
    urls = [f"https://api.example.com/data/{i}" for i in range(12)]
    results = await asyncio.gather(*[rate_limited_fetch(u) for u in urls])
    elapsed = time.perf_counter() - t0

    print(f"  Completed {len(results)} requests in {elapsed:.2f}s")
    print(f"  Effective rate: {len(results) / elapsed:.1f} req/s (limit: 5/s)")
    # Show the relative timestamps to prove rate limiting
    relative = [round(t - t0, 2) for t in timestamps]
    print(f"  Request start times: {relative}")


# ===========================================================================
# EXAMPLE 7: Retry with Exponential Backoff
# ===========================================================================
# Node.js equivalent: p-retry or custom wrapper around setTimeout + retry.

def async_retry(
    max_retries: int = 3,
    base_delay: float = 0.1,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
):
    """Decorator that retries an async function with exponential backoff.

    Usage:
        @async_retry(max_retries=3, base_delay=0.5, retry_on=(ValueError,))
        async def flaky_operation():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: BaseException | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"    [retry] attempt {attempt + 1} failed: {e}. "
                              f"Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    else:
                        print(f"    [retry] attempt {attempt + 1} failed: {e}. "
                              f"No retries left.")
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


async def example_retry() -> None:
    _banner("Example 7: Retry with Exponential Backoff")

    call_count = 0

    @async_retry(max_retries=3, base_delay=0.1, retry_on=(ConnectionError,))
    async def flaky_service() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError(f"Connection refused (attempt {call_count})")
        return "Success!"

    # Succeeds on the 3rd attempt
    result = await flaky_service()
    print(f"  Result: {result}  (took {call_count} attempts)")

    # Demonstrate exhausting retries
    print()

    @async_retry(max_retries=2, base_delay=0.05, retry_on=(ValueError,))
    async def always_fails() -> str:
        raise ValueError("permanent error")

    try:
        await always_fails()
    except ValueError as e:
        print(f"  Correctly raised after retries: {e}")


# ===========================================================================
# Main: run all examples in sequence
# ===========================================================================

async def main() -> None:
    print("Async Python Examples -- Module 02")
    print("Python 3.11+ required for TaskGroup and asyncio.timeout")

    await example_parallel_fetch()
    await example_connection_pool()
    await example_producer_consumer()
    await example_taskgroup()
    await example_async_generator()
    await example_rate_limiter()
    await example_retry()

    _banner("All examples complete")


if __name__ == "__main__":
    asyncio.run(main())
