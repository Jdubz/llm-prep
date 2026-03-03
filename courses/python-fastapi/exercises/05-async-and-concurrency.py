"""
Async & Concurrency Exercises

asyncio patterns that come up in every Python backend interview:
gather, semaphores, queues, async context managers, and retry logic.

Run:  python exercises/05-async-and-concurrency.py
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


# ============================================================================
# EXERCISE 1: Sequential to Concurrent
# ============================================================================
#
# Rewrite a sequential fetch pattern using asyncio.gather for concurrency.
# This is the single most common async interview question.
#
# Requirements:
#   - fetch_one(url, delay) simulates a network request (asyncio.sleep(delay))
#     and returns {"url": url, "status": 200}
#   - fetch_all_sequential(urls_and_delays) awaits each fetch one by one
#   - fetch_all_concurrent(urls_and_delays) uses asyncio.gather to run all
#     fetches concurrently
#   - Both return list[dict] in the same order as input
#
# Hints:
#   - Sequential: loop and await each fetch_one()
#   - Concurrent: build a list of coroutines, pass to asyncio.gather(*coros)
#   - asyncio.gather returns results in the same order as the input coroutines
#
# Expected behavior:
#   urls = [("/a", 0.1), ("/b", 0.1), ("/c", 0.1)]
#   # Sequential: ~0.3s total
#   # Concurrent: ~0.1s total


async def fetch_one(url: str, delay: float = 0.1) -> dict:
    """Simulate a network request with a delay."""
    # TODO: Implement (await asyncio.sleep, return dict with url and status)
    raise NotImplementedError()


async def fetch_all_sequential(
    urls_and_delays: list[tuple[str, float]],
) -> list[dict]:
    """Fetch all URLs sequentially (one at a time)."""
    # TODO: Implement
    raise NotImplementedError()


async def fetch_all_concurrent(
    urls_and_delays: list[tuple[str, float]],
) -> list[dict]:
    """Fetch all URLs concurrently using asyncio.gather."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 2: Semaphore-Bounded Fetcher
# ============================================================================
#
# Limit concurrent requests to N using asyncio.Semaphore. This prevents
# overwhelming a downstream service.
#
# Requirements:
#   - fetch_bounded(urls_and_delays, max_concurrent) limits concurrency
#   - Uses asyncio.Semaphore(max_concurrent) to throttle
#   - Still runs as many requests concurrently as the semaphore allows
#   - Returns results in input order
#
# Hints:
#   - Create a semaphore: sem = asyncio.Semaphore(max_concurrent)
#   - Wrap each fetch in an async function that does:
#       async with sem:
#           return await fetch_one(url, delay)
#   - Use asyncio.gather on the wrapped coroutines
#
# Expected behavior:
#   urls = [("/a", 0.1), ("/b", 0.1), ("/c", 0.1), ("/d", 0.1)]
#   # With max_concurrent=2: ~0.2s (two batches of 2)
#   # With max_concurrent=4: ~0.1s (all at once)


async def fetch_bounded(
    urls_and_delays: list[tuple[str, float]],
    max_concurrent: int = 3,
) -> list[dict]:
    """Fetch URLs with bounded concurrency using a semaphore."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 3: Async Retry
# ============================================================================
#
# Write an async-aware retry decorator with exponential backoff.
# This is the async version of exercise 2 from the functions module.
#
# Requirements:
#   - @async_retry(max_attempts=3, delay=0.1) — decorator factory
#   - Retries async functions on exception
#   - Uses asyncio.sleep (not time.sleep!) for delays
#   - Delay doubles after each attempt (exponential backoff)
#   - If all attempts fail, raise the last exception
#   - Preserves the function name with functools.wraps
#
# Hints:
#   - Same three-layer pattern as sync retry, but wrapper is async
#   - await asyncio.sleep(current_delay) instead of time.sleep()
#   - await func(*args, **kwargs) to call the wrapped async function
#
# Expected behavior:
#   attempt_count = 0
#   @async_retry(max_attempts=3, delay=0.01)
#   async def flaky_fetch():
#       nonlocal attempt_count
#       attempt_count += 1
#       if attempt_count < 3:
#           raise ConnectionError("fail")
#       return "ok"
#   await flaky_fetch()  # "ok" on 3rd attempt

import functools


def async_retry(
    max_attempts: int = 3, delay: float = 0.1
) -> Callable:
    """Async decorator factory that retries with exponential backoff."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 4: Timeout Wrapper
# ============================================================================
#
# Write a utility that wraps any coroutine with a timeout and optional
# fallback value.
#
# Requirements:
#   - with_timeout(coro, timeout, fallback) awaits the coroutine
#   - If the coroutine completes within timeout seconds, return its result
#   - If it times out, return the fallback value (default None)
#   - Use asyncio.wait_for under the hood
#
# Hints:
#   - asyncio.wait_for(coro, timeout=seconds) raises asyncio.TimeoutError
#   - Catch TimeoutError and return the fallback
#
# Expected behavior:
#   async def slow():
#       await asyncio.sleep(10)
#       return "done"
#   result = await with_timeout(slow(), timeout=0.1, fallback="timed out")
#   # result == "timed out"


async def with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout: float,
    fallback: T | None = None,
) -> T | None:
    """Await a coroutine with a timeout, returning fallback on timeout."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 5: Producer/Consumer Pipeline
# ============================================================================
#
# Implement an async producer/consumer pipeline using asyncio.Queue.
# The producer generates work items, the consumer processes them.
#
# Requirements:
#   - producer(queue, items) puts each item into the queue with a small delay
#   - consumer(queue, results) gets items from the queue, "processes" them
#     (e.g., item.upper()), and appends to results. Stops on None sentinel.
#   - run_pipeline(items, num_consumers) orchestrates the pipeline:
#       1. Create an asyncio.Queue
#       2. Start the producer and num_consumers consumers concurrently
#       3. Producer sends None sentinel for each consumer when done
#       4. Return the collected results
#
# Hints:
#   - Producer: for item in items: await queue.put(item); await asyncio.sleep(0.01)
#   - Consumer: while True: item = await queue.get(); if item is None: break
#   - Use asyncio.gather to run producer + consumers concurrently
#   - Send num_consumers None sentinels to stop all consumers
#
# Expected behavior:
#   results = await run_pipeline(["hello", "world", "foo"], num_consumers=2)
#   sorted(results)  # ["FOO", "HELLO", "WORLD"]


async def producer(queue: asyncio.Queue, items: list[str]) -> None:
    """Put items into the queue."""
    # TODO: Implement
    raise NotImplementedError()


async def consumer(queue: asyncio.Queue, results: list[str]) -> None:
    """Process items from the queue until sentinel (None) is received."""
    # TODO: Implement
    raise NotImplementedError()


async def run_pipeline(items: list[str], num_consumers: int = 2) -> list[str]:
    """Run a producer/consumer pipeline and return processed results."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 6: Async Context Manager (Connection Pool Mock)
# ============================================================================
#
# Implement an async context manager that simulates a database connection
# pool. This practices __aenter__/__aexit__ which FastAPI uses for
# lifespan management and database sessions.
#
# Requirements:
#   - AsyncPool(max_size) creates a pool of mock connections
#   - __aenter__: "connects" (simulated with asyncio.sleep(0.01)),
#     returns self
#   - __aexit__: "disconnects" all connections (asyncio.sleep(0.01))
#   - acquire() -> Connection: get a connection (raise RuntimeError if
#     pool exhausted)
#   - release(conn): return a connection to the pool
#   - Connection is a simple class with execute(query) -> str method
#
# Hints:
#   - Use a list or deque for available connections
#   - acquire() pops from available, release() appends back
#   - __aenter__ creates the connections, __aexit__ clears them
#
# Expected behavior:
#   async with AsyncPool(max_size=2) as pool:
#       conn = await pool.acquire()
#       result = await conn.execute("SELECT 1")
#       await pool.release(conn)


class Connection:
    """Mock database connection."""

    def __init__(self, conn_id: int) -> None:
        self.conn_id = conn_id
        self.closed = False

    async def execute(self, query: str) -> str:
        """Simulate executing a query."""
        # TODO: Return f"Connection {conn_id}: {query}"
        raise NotImplementedError()

    def __repr__(self) -> str:
        return f"Connection({self.conn_id})"


class AsyncPool:
    """Async context manager simulating a connection pool."""

    def __init__(self, max_size: int = 5) -> None:
        # TODO: Store max_size, initialize pool state
        raise NotImplementedError()

    async def __aenter__(self) -> AsyncPool:
        """Create connections and return the pool."""
        # TODO: Implement
        raise NotImplementedError()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Close all connections."""
        # TODO: Implement
        raise NotImplementedError()

    async def acquire(self) -> Connection:
        """Get a connection from the pool."""
        # TODO: Implement (raise RuntimeError if exhausted)
        raise NotImplementedError()

    async def release(self, conn: Connection) -> None:
        """Return a connection to the pool."""
        # TODO: Implement
        raise NotImplementedError()


# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

# async def test_sequential_vs_concurrent():
#     print("\n=== EXERCISE 1: Sequential vs Concurrent ===")
#     urls = [("/a", 0.05), ("/b", 0.05), ("/c", 0.05)]
#
#     start = time.monotonic()
#     seq_results = await fetch_all_sequential(urls)
#     seq_time = time.monotonic() - start
#
#     start = time.monotonic()
#     con_results = await fetch_all_concurrent(urls)
#     con_time = time.monotonic() - start
#
#     assert len(seq_results) == 3
#     assert len(con_results) == 3
#     assert seq_results == con_results
#     assert con_time < seq_time  # concurrent should be faster
#     print(f"Sequential: {seq_time:.3f}s, Concurrent: {con_time:.3f}s")
#     print(f"Speedup: {seq_time / con_time:.1f}x")
#     print("EXERCISE 1: PASSED")
#
#
# async def test_semaphore():
#     print("\n=== EXERCISE 2: Semaphore ===")
#     urls = [("/a", 0.05), ("/b", 0.05), ("/c", 0.05), ("/d", 0.05)]
#
#     start = time.monotonic()
#     results = await fetch_bounded(urls, max_concurrent=2)
#     elapsed = time.monotonic() - start
#
#     assert len(results) == 4
#     assert all(r["status"] == 200 for r in results)
#     # With max_concurrent=2 and 4 items of 0.05s each: ~0.1s
#     assert elapsed < 0.2
#     print(f"Bounded fetch: {elapsed:.3f}s for {len(results)} URLs (max_concurrent=2)")
#     print("EXERCISE 2: PASSED")
#
#
# async def test_async_retry():
#     print("\n=== EXERCISE 3: Async Retry ===")
#     attempt_count = 0
#
#     @async_retry(max_attempts=3, delay=0.01)
#     async def flaky_fetch():
#         nonlocal attempt_count
#         attempt_count += 1
#         if attempt_count < 3:
#             raise ConnectionError("fail")
#         return "ok"
#
#     result = await flaky_fetch()
#     assert result == "ok"
#     assert attempt_count == 3
#     print(f"Succeeded after {attempt_count} attempts")
#
#     # All attempts fail
#     @async_retry(max_attempts=2, delay=0.01)
#     async def always_fails():
#         raise ValueError("nope")
#
#     try:
#         await always_fails()
#         print("ERROR: Should have raised ValueError")
#     except ValueError:
#         print("Final exception propagated (expected)")
#     print("EXERCISE 3: PASSED")
#
#
# async def test_timeout():
#     print("\n=== EXERCISE 4: Timeout ===")
#
#     async def slow():
#         await asyncio.sleep(10)
#         return "done"
#
#     result = await with_timeout(slow(), timeout=0.05, fallback="timed out")
#     assert result == "timed out"
#     print(f"Slow function result: {result}")
#
#     async def fast():
#         await asyncio.sleep(0.01)
#         return "done"
#
#     result = await with_timeout(fast(), timeout=1.0, fallback="timed out")
#     assert result == "done"
#     print(f"Fast function result: {result}")
#     print("EXERCISE 4: PASSED")
#
#
# async def test_pipeline():
#     print("\n=== EXERCISE 5: Pipeline ===")
#     items = ["hello", "world", "foo", "bar", "baz"]
#     results = await run_pipeline(items, num_consumers=2)
#
#     assert sorted(results) == sorted(item.upper() for item in items)
#     print(f"Processed {len(results)} items: {sorted(results)}")
#     print("EXERCISE 5: PASSED")
#
#
# async def test_async_pool():
#     print("\n=== EXERCISE 6: Async Pool ===")
#     async with AsyncPool(max_size=2) as pool:
#         conn1 = await pool.acquire()
#         conn2 = await pool.acquire()
#
#         result = await conn1.execute("SELECT 1")
#         assert "SELECT 1" in result
#         print(f"Query result: {result}")
#
#         # Pool exhausted
#         try:
#             await pool.acquire()
#             print("ERROR: Should have raised RuntimeError")
#         except RuntimeError as e:
#             print(f"Pool exhausted: {e}")
#
#         await pool.release(conn1)
#         conn3 = await pool.acquire()  # should work now
#         assert conn3 is conn1
#         print("Connection reuse works")
#
#         await pool.release(conn2)
#         await pool.release(conn3)
#     print("EXERCISE 6: PASSED")
#
#
# async def run_all_tests():
#     await test_sequential_vs_concurrent()
#     await test_semaphore()
#     await test_async_retry()
#     await test_timeout()
#     await test_pipeline()
#     await test_async_pool()
#     print("\n=== ALL EXERCISES PASSED ===")


if __name__ == "__main__":
    print("Async & Concurrency Exercises")
    print("=" * 40)

    import warnings
    warnings.filterwarnings("ignore", message="coroutine.*was never awaited")

    async def _check_all():
        async def _noop():
            pass

        exercises = [
            ("1 - Sequential to Concurrent", "async", lambda: fetch_one("/test", 0)),
            ("2 - Semaphore-Bounded Fetcher", "async", lambda: fetch_bounded([], 1)),
            ("3 - Async Retry", "sync", lambda: async_retry()),
            ("4 - Timeout Wrapper", "async", lambda: with_timeout(_noop(), 1)),
            ("5 - Producer/Consumer", "async", lambda: run_pipeline([], 1)),
            ("6 - Async Context Manager", "sync", lambda: AsyncPool(1)),
        ]

        for name, kind, factory in exercises:
            try:
                result = factory()
                if kind == "async":
                    await result
                print(f"  {name}: IMPLEMENTED")
            except NotImplementedError:
                print(f"  {name}: not implemented")

    asyncio.run(_check_all())

    # Uncomment below (and the test functions above) to run full tests:
    # asyncio.run(run_all_tests())
