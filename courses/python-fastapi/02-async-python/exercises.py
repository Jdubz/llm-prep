"""
Module 02: Async Python Deep Dive -- Exercises
===============================================

Skeleton functions with TODOs. Implement each exercise, then run:
    python exercises.py

All exercises use only stdlib asyncio (no external packages).
Assumes Python 3.11+ for TaskGroup and asyncio.timeout.

Each exercise includes:
- A docstring explaining expected behavior
- A "READ FIRST" pointer to the relevant MD file and section
- An "ALSO SEE" pointer to the matching example in examples.py
- Stub code with TODO markers
- A test function that validates your implementation

Companion files (all in the same directory):
- 01-asyncio-fundamentals.md  -- event loop, coroutines, await basics
- 02-concurrency-patterns.md  -- gather, TaskGroup, Semaphore, Queue, rate limiters
- 03-async-debugging-and-production.md -- debugging, testing, production patterns
- examples.py                 -- fully working examples you can run and study
"""

import asyncio
import time


# ---------------------------------------------------------------------------
# Helpers (used by multiple exercises -- do NOT modify)
# ---------------------------------------------------------------------------

async def _simulated_fetch(url: str, *, delay: float | None = None) -> dict:
    """Simulate an async HTTP GET. Returns dict with url, status, data."""
    d = delay if delay is not None else 0.1
    await asyncio.sleep(d)
    # Simulate occasional failures for testing error handling
    if "fail" in url:
        raise ConnectionError(f"Failed to fetch {url}")
    return {"url": url, "status": 200, "data": f"Response from {url}"}


def _sync_fetch(url: str) -> dict:
    """A deliberately BLOCKING fetch (uses time.sleep). Do NOT use in async code."""
    time.sleep(0.1)
    return {"url": url, "status": 200, "data": f"Sync response from {url}"}


# ===========================================================================
# EXERCISE 1: Convert Synchronous Code to Async
# ===========================================================================
#
# READ FIRST:
#   01-asyncio-fundamentals.md -> "Basic Coroutines" section (async def, await)
#   02-concurrency-patterns.md -> "asyncio.gather (like Promise.all)" section
#
# ALSO SEE:
#   examples.py -> Example 1: Parallel HTTP Fetching with Semaphore
#     (shows asyncio.gather with a list of coroutines)
#
# KEY CONCEPT -- asyncio.gather:
#   asyncio.gather(*awaitables) -> list[results]
#
#   Takes any number of awaitables (coroutines, tasks, futures) and runs them
#   ALL concurrently on the event loop. Returns a list of results in the SAME
#   order as the input awaitables.
#
#   Signature:
#     await asyncio.gather(coro1(), coro2(), coro3())
#     # returns [result1, result2, result3]
#
#   To pass a list of coroutines, use star-unpacking:
#     coroutines = [fetch(url) for url in urls]
#     results = await asyncio.gather(*coroutines)
#
#   The key difference from sequential execution: all coroutines start at
#   the same time, so the total time is max(individual times) instead of
#   sum(individual times).
# ===========================================================================

def fetch_all_sync(urls: list[str]) -> list[dict]:
    """REFERENCE: synchronous version -- fetches URLs one at a time.
    This takes ~N * 0.1s for N URLs. Your async version should be faster.
    """
    results = []
    for url in urls:
        results.append(_sync_fetch(url))
    return results


async def fetch_all_async(urls: list[str]) -> list[dict]:
    """Convert the synchronous fetch_all_sync to async.

    Requirements:
    - Use _simulated_fetch (the async helper) instead of _sync_fetch
    - Fetch ALL urls concurrently using asyncio.gather
    - Return results in the same order as the input urls
    - Should complete in ~0.1s regardless of how many URLs (concurrent!)

    Expected behavior:
        >>> results = await fetch_all_async(["https://a.com", "https://b.com"])
        >>> len(results)
        2
        >>> results[0]["url"]
        'https://a.com'
    """
    # TODO: Replace this with a concurrent async implementation.
    #
    # Steps:
    # 1. Build a list of coroutines:
    #      coroutines = [_simulated_fetch(url) for url in urls]
    # 2. Run them all concurrently with gather:
    #      results = await asyncio.gather(*coroutines)
    # 3. Return results (gather preserves input order)
    raise NotImplementedError("Implement fetch_all_async")


# ===========================================================================
# EXERCISE 2: Fan-Out/Fan-In -- Fetch and Aggregate
# ===========================================================================
#
# READ FIRST:
#   02-concurrency-patterns.md -> "Semaphores for Concurrency Limiting" section
#   02-concurrency-patterns.md -> "asyncio.gather (like Promise.all)" section
#     (specifically the return_exceptions=True pattern)
#
# ALSO SEE:
#   examples.py -> Example 1: Parallel HTTP Fetching with Semaphore
#     (shows the exact semaphore + gather pattern you need)
#
# KEY CONCEPT -- asyncio.Semaphore:
#   A semaphore limits how many coroutines can run a section of code at once.
#   Think of it as a bouncer letting only N people into a club at a time.
#
#   Create:   sem = asyncio.Semaphore(5)   # allow 5 concurrent
#   Use:      async with sem:              # blocks until a slot opens
#                 await do_work()          # only 5 run this at once
#
#   The "async with" acquires the semaphore (decrementing the counter).
#   When the block exits, it releases (incrementing the counter).
#   If the counter is 0, the next "async with" will wait.
#
# KEY CONCEPT -- asyncio.gather with return_exceptions:
#   results = await asyncio.gather(*coros, return_exceptions=True)
#
#   When return_exceptions=True, exceptions are returned as values in the
#   results list instead of being raised. You then filter:
#     successes = [r for r in results if not isinstance(r, Exception)]
#     failures  = [r for r in results if isinstance(r, Exception)]
#
# PATTERN for this exercise:
#   1. Create a Semaphore
#   2. Write a wrapper coroutine: async def _limited_fetch(url):
#        async with sem:
#            try:
#                return await _simulated_fetch(url)
#            except Exception as e:
#                return {"url": url, "error": str(e)}  # return error as value
#   3. Gather all wrappers
#   4. Separate successes (dicts with "status" key) from failures (dicts with "error" key)
# ===========================================================================

async def fan_out_fan_in(urls: list[str], max_concurrent: int = 5) -> dict:
    """Fetch multiple URLs concurrently with limited concurrency, aggregate results.

    Requirements:
    - Use asyncio.Semaphore to limit concurrency to max_concurrent
    - Use asyncio.gather with return_exceptions=True
    - Return a dict with:
        "successes": list of successful response dicts
        "failures":  list of dicts like {"url": url, "error": str(exception)}
    - Order does not matter within successes/failures

    Expected behavior:
        >>> result = await fan_out_fan_in(
        ...     ["https://a.com", "https://fail.com/x", "https://b.com"],
        ...     max_concurrent=2,
        ... )
        >>> len(result["successes"])
        2
        >>> len(result["failures"])
        1
        >>> result["failures"][0]["url"]
        'https://fail.com/x'
    """
    # TODO: Implement fan-out/fan-in with semaphore-limited concurrency.
    #
    # Step 1: Create an asyncio.Semaphore with max_concurrent
    # Step 2: Write a helper coroutine that acquires the semaphore, then
    #         calls _simulated_fetch. Wrap in try/except to catch errors
    #         and return either the result or an error dict.
    # Step 3: Use asyncio.gather to run all helpers concurrently.
    # Step 4: Separate successes from failures and return the aggregated dict.
    raise NotImplementedError("Implement fan_out_fan_in")


# ===========================================================================
# EXERCISE 3: Async Rate Limiter (Token Bucket)
# ===========================================================================
#
# READ FIRST:
#   02-concurrency-patterns.md -> "Token Bucket Rate Limiter" section
#     (shows the complete algorithm and data structure)
#
# ALSO SEE:
#   examples.py -> Example 6: Token Bucket Rate Limiter
#     (complete working implementation of the same class)
#
# KEY CONCEPT -- Token Bucket Algorithm:
#   The bucket holds up to `capacity` tokens. Tokens are added at `rate`
#   tokens per second. To do work, you must acquire a token. If the bucket
#   is empty, you wait until tokens refill.
#
#   State you need:
#     self._rate      = rate           # tokens per second (float)
#     self._capacity  = capacity       # max tokens (int)
#     self._tokens    = float(capacity)  # current tokens (starts full)
#     self._last_refill = time.monotonic()  # last refill timestamp
#     self._lock      = asyncio.Lock()  # protect shared state
#
# KEY CONCEPT -- asyncio.Lock:
#   An async lock prevents concurrent coroutines from interleaving in a
#   critical section (between await points, Python is single-threaded, but
#   across awaits, interleaving can happen).
#
#   lock = asyncio.Lock()
#   async with lock:
#       # only one coroutine at a time in here
#       self._refill()
#       if self._tokens >= 1:
#           self._tokens -= 1
#           return
#
# KEY CONCEPT -- time.monotonic():
#   Returns a float in seconds from an arbitrary epoch. Unlike time.time(),
#   it never goes backwards (no NTP adjustments). Use it for measuring
#   elapsed time:
#     start = time.monotonic()
#     ...
#     elapsed = time.monotonic() - start
#
# REFILL FORMULA:
#   elapsed = now - self._last_refill
#   new_tokens = elapsed * self._rate
#   self._tokens = min(self._capacity, self._tokens + new_tokens)
#   self._last_refill = now
# ===========================================================================

class AsyncRateLimiter:
    """Token bucket rate limiter for async code.

    Args:
        rate: number of tokens added per second
        capacity: maximum tokens the bucket can hold

    Requirements:
    - Tokens refill continuously based on elapsed time
    - acquire() should block (await) until a token is available
    - Must be safe for concurrent callers (use asyncio.Lock)
    - Bucket starts full (tokens == capacity)

    Expected behavior:
        >>> limiter = AsyncRateLimiter(rate=10, capacity=10)
        >>> # First 10 calls return immediately (bucket is full)
        >>> # 11th call blocks until a token refills (~0.1s)
    """

    def __init__(self, rate: float, capacity: int):
        # TODO: Initialize the rate limiter state.
        #
        # You need these instance variables:
        #   self._rate = rate                    # float: tokens per second
        #   self._capacity = capacity            # int: max tokens
        #   self._tokens = float(capacity)       # float: current tokens (start full)
        #   self._last_refill = time.monotonic() # float: timestamp of last refill
        #   self._lock = asyncio.Lock()          # Lock: protects _refill + consume
        raise NotImplementedError("Implement __init__")

    def _refill(self) -> None:
        """Add tokens based on time elapsed since last refill.

        Tokens = min(capacity, current_tokens + elapsed * rate)
        Update the last-refill timestamp.
        """
        # TODO: Calculate elapsed time, add tokens, cap at capacity.
        #
        # Steps:
        #   now = time.monotonic()
        #   elapsed = now - self._last_refill
        #   self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        #   self._last_refill = now
        raise NotImplementedError("Implement _refill")

    async def acquire(self, tokens: int = 1) -> None:
        """Wait until the requested number of tokens are available, then consume them.

        Algorithm:
        1. Lock
        2. Refill
        3. If enough tokens: consume and return
        4. Otherwise: release lock, sleep briefly, retry
        """
        # TODO: Implement the acquire loop.
        #
        # Pattern:
        #   while True:
        #       async with self._lock:
        #           self._refill()
        #           if self._tokens >= tokens:
        #               self._tokens -= tokens
        #               return              # acquired!
        #       # Not enough tokens yet -- sleep and retry
        #       await asyncio.sleep(tokens / self._rate)
        raise NotImplementedError("Implement acquire")


# ===========================================================================
# EXERCISE 4: Timeout Wrapper
# ===========================================================================
#
# READ FIRST:
#   02-concurrency-patterns.md -> "Timeout Handling" section
#   02-concurrency-patterns.md -> "asyncio Synchronization Primitives" section
#     (the Timeouts subsection)
#
# ALSO SEE:
#   03-async-debugging-and-production.md -> "Testing Timeouts and Concurrency"
#     (shows asyncio.timeout in a test context)
#
# KEY CONCEPT -- asyncio.timeout (Python 3.11+):
#   asyncio.timeout is an async context manager that cancels the enclosed
#   code if it takes longer than the specified number of seconds.
#
#   Signature and usage:
#     async with asyncio.timeout(seconds):
#         result = await some_coroutine()
#
#   If the timeout expires, it raises TimeoutError (builtin, not
#   asyncio.TimeoutError). The coroutine inside is automatically cancelled.
#
#   Full pattern for this exercise:
#     try:
#         async with asyncio.timeout(timeout_seconds):
#             return await coro
#     except TimeoutError:
#         return fallback
#
# ALTERNATIVE -- asyncio.wait_for (older Python):
#   result = await asyncio.wait_for(coro, timeout=seconds)
#
#   Raises asyncio.TimeoutError on timeout. Also cancels the coroutine.
#
#   Full pattern:
#     try:
#         return await asyncio.wait_for(coro, timeout=timeout_seconds)
#     except asyncio.TimeoutError:
#         return fallback
#
# NOTE: Both approaches automatically cancel the timed-out coroutine,
# so you do NOT need to manually cancel anything.
# ===========================================================================

async def with_timeout(coro, *, timeout_seconds: float, fallback=None):
    """Run a coroutine with a timeout. Return fallback if it times out.

    Requirements:
    - Use asyncio.timeout (Python 3.11+) or asyncio.wait_for
    - If the coroutine completes before the timeout, return its result
    - If it times out, return the fallback value (do NOT raise)
    - The timed-out coroutine must be cancelled (not left running)

    Expected behavior:
        >>> async def slow():
        ...     await asyncio.sleep(10)
        ...     return "done"
        >>> result = await with_timeout(slow(), timeout_seconds=0.1, fallback="timed out")
        >>> result
        'timed out'

        >>> async def fast():
        ...     await asyncio.sleep(0.01)
        ...     return "done"
        >>> result = await with_timeout(fast(), timeout_seconds=1.0)
        >>> result
        'done'
    """
    # TODO: Implement timeout wrapper.
    # Option A (Python 3.11+):
    #   try:
    #       async with asyncio.timeout(timeout_seconds):
    #           return await coro
    #   except TimeoutError:
    #       return fallback
    #
    # Option B (older Python):
    #   try:
    #       return await asyncio.wait_for(coro, timeout=timeout_seconds)
    #   except asyncio.TimeoutError:
    #       return fallback
    raise NotImplementedError("Implement with_timeout")


# ===========================================================================
# EXERCISE 5: Producer/Consumer Pipeline with Error Handling
# ===========================================================================
#
# READ FIRST:
#   02-concurrency-patterns.md -> "asyncio.Queue for Producer/Consumer" section
#     (shows the complete producer/consumer pattern with sentinels)
#   02-concurrency-patterns.md -> "TaskGroup: Structured Concurrency" section
#     (shows how to use asyncio.TaskGroup for managing concurrent tasks)
#
# ALSO SEE:
#   examples.py -> Example 3: Producer/Consumer with asyncio.Queue
#     (complete working producer/consumer with TaskGroup)
#   examples.py -> Example 4: Structured Concurrency with TaskGroup
#     (shows TaskGroup error handling with except*)
#
# KEY CONCEPT -- asyncio.Queue:
#   An async-safe FIFO queue with optional max size for backpressure.
#
#   Create:    q = asyncio.Queue(maxsize=5)
#   Produce:   await q.put(item)     # blocks if queue is full (backpressure!)
#   Consume:   item = await q.get()  # blocks if queue is empty
#   Done:      q.task_done()         # signal that a get()'d item is processed
#
#   IMPORTANT: Call q.task_done() for EVERY item you get(), including
#   sentinel/shutdown values. This is needed if anyone calls q.join().
#
# KEY CONCEPT -- Sentinel (Poison Pill) Pattern:
#   To tell consumers to stop, the producer sends one None per consumer:
#     for _ in range(num_consumers):
#         await queue.put(None)
#   Each consumer checks:
#     item = await queue.get()
#     if item is None:
#         queue.task_done()
#         break  # exit the loop
#
# KEY CONCEPT -- asyncio.TaskGroup (Python 3.11+):
#   Structured concurrency: all tasks must complete before the block exits.
#   If any task raises an exception, all other tasks are cancelled.
#
#   async with asyncio.TaskGroup() as tg:
#       tg.create_task(producer(queue))
#       for i in range(num_consumers):
#           tg.create_task(consumer(queue, i))
#   # all tasks are done here
#
#   NOTE: In this exercise, you should catch errors INSIDE the consumer
#   (try/except around _simulated_fetch), so that one failed URL does NOT
#   crash the whole pipeline. The TaskGroup is for lifecycle management,
#   not for error recovery of individual items.
# ===========================================================================

async def producer_consumer_pipeline(
    items: list[str],
    num_consumers: int = 3,
    max_queue_size: int = 5,
) -> dict:
    """Process items through an async producer/consumer pipeline.

    Architecture:
    - One producer: puts items into an asyncio.Queue
    - N consumers: take items from the queue, process them via _simulated_fetch
    - After all items are produced, send shutdown signals (None sentinels)
    - Collect successes and failures separately

    Requirements:
    - Queue must have max size for backpressure (max_queue_size)
    - Each consumer processes items in a loop until it receives None
    - Failures (items containing "fail") should be caught, not crash the pipeline
    - Use asyncio.TaskGroup for structured concurrency
    - Call queue.task_done() for every item (including sentinels)
    - Return {"successes": [...results...], "failures": [...error dicts...]}

    Expected behavior:
        >>> result = await producer_consumer_pipeline(
        ...     ["https://a.com", "https://fail.com/x", "https://b.com"],
        ...     num_consumers=2,
        ... )
        >>> len(result["successes"])
        2
        >>> len(result["failures"])
        1
    """
    # TODO: Implement the pipeline.
    #
    # 1. Create an asyncio.Queue with maxsize=max_queue_size:
    #      queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=max_queue_size)
    #
    # 2. Create shared lists for successes and failures:
    #      successes: list[dict] = []
    #      failures: list[dict] = []
    #
    # 3. Write an async producer(queue) that:
    #      async def producer(q):
    #          for item in items:
    #              await q.put(item)          # blocks if queue full (backpressure)
    #          for _ in range(num_consumers):
    #              await q.put(None)          # one sentinel per consumer
    #
    # 4. Write an async consumer(queue, cid) that:
    #      async def consumer(q, cid):
    #          while True:
    #              item = await q.get()
    #              if item is None:
    #                  q.task_done()
    #                  break
    #              try:
    #                  result = await _simulated_fetch(item)
    #                  successes.append(result)
    #              except Exception as e:
    #                  failures.append({"url": item, "error": str(e)})
    #              finally:
    #                  q.task_done()  # ALWAYS call task_done, even on error
    #
    # 5. Use asyncio.TaskGroup to run 1 producer + num_consumers consumers:
    #      async with asyncio.TaskGroup() as tg:
    #          tg.create_task(producer(queue))
    #          for i in range(num_consumers):
    #              tg.create_task(consumer(queue, i))
    #
    # 6. Return the results dict:
    #      return {"successes": successes, "failures": failures}
    raise NotImplementedError("Implement producer_consumer_pipeline")


# ===========================================================================
# Test Suite -- validates all exercises
# ===========================================================================

async def test_exercise_1() -> None:
    print("--- Exercise 1: Convert Sync to Async ---")
    urls = [f"https://example.com/{i}" for i in range(10)]

    t0 = time.perf_counter()
    results = await fetch_all_async(urls)
    elapsed = time.perf_counter() - t0

    assert len(results) == 10, f"Expected 10 results, got {len(results)}"
    assert all(r["status"] == 200 for r in results), "All should have status 200"
    assert results[0]["url"] == urls[0], "Results must preserve input order"
    assert elapsed < 0.5, f"Should be concurrent (<0.5s), took {elapsed:.2f}s"
    print(f"  PASS -- fetched {len(results)} URLs in {elapsed:.2f}s (concurrent)")


async def test_exercise_2() -> None:
    print("--- Exercise 2: Fan-Out/Fan-In ---")
    urls = [
        "https://api.example.com/a",
        "https://api.example.com/b",
        "https://fail.example.com/c",   # will fail
        "https://api.example.com/d",
        "https://fail.example.com/e",   # will fail
    ]

    result = await fan_out_fan_in(urls, max_concurrent=2)

    assert "successes" in result and "failures" in result, "Must return successes and failures"
    assert len(result["successes"]) == 3, f"Expected 3 successes, got {len(result['successes'])}"
    assert len(result["failures"]) == 2, f"Expected 2 failures, got {len(result['failures'])}"
    assert all("url" in f and "error" in f for f in result["failures"]), (
        "Each failure must have 'url' and 'error' keys"
    )
    print(f"  PASS -- {len(result['successes'])} successes, {len(result['failures'])} failures")


async def test_exercise_3() -> None:
    print("--- Exercise 3: Async Rate Limiter ---")
    limiter = AsyncRateLimiter(rate=10, capacity=5)

    # First 5 should be instant (bucket starts full)
    t0 = time.perf_counter()
    for _ in range(5):
        await limiter.acquire()
    burst_time = time.perf_counter() - t0
    assert burst_time < 0.1, f"Initial burst should be instant, took {burst_time:.2f}s"

    # Next 5 should take ~0.5s (10 tokens/sec, need 5 tokens)
    t1 = time.perf_counter()
    for _ in range(5):
        await limiter.acquire()
    throttled_time = time.perf_counter() - t1
    assert throttled_time > 0.3, f"Throttled requests should take >0.3s, took {throttled_time:.2f}s"
    print(f"  PASS -- burst: {burst_time:.3f}s, throttled: {throttled_time:.3f}s")


async def test_exercise_4() -> None:
    print("--- Exercise 4: Timeout Wrapper ---")

    async def fast_op():
        await asyncio.sleep(0.01)
        return "fast result"

    async def slow_op():
        await asyncio.sleep(10)
        return "slow result"

    # Test 1: fast operation completes
    coro = fast_op()
    try:
        result = await with_timeout(coro, timeout_seconds=1.0, fallback="timed out")
    except NotImplementedError:
        coro.close()
        raise
    assert result == "fast result", f"Expected 'fast result', got {result!r}"

    # Test 2: slow operation times out
    t0 = time.perf_counter()
    result = await with_timeout(slow_op(), timeout_seconds=0.1, fallback="timed out")
    elapsed = time.perf_counter() - t0
    assert result == "timed out", f"Expected 'timed out', got {result!r}"
    assert elapsed < 0.5, f"Should timeout quickly, took {elapsed:.2f}s"

    # Test 3: fallback defaults to None
    result = await with_timeout(slow_op(), timeout_seconds=0.1)
    assert result is None, f"Default fallback should be None, got {result!r}"
    print(f"  PASS -- fast op returned result, slow op returned fallback")


async def test_exercise_5() -> None:
    print("--- Exercise 5: Producer/Consumer Pipeline ---")
    items = [
        "https://api.example.com/1",
        "https://api.example.com/2",
        "https://fail.example.com/3",   # will fail
        "https://api.example.com/4",
        "https://api.example.com/5",
        "https://fail.example.com/6",   # will fail
        "https://api.example.com/7",
    ]

    result = await producer_consumer_pipeline(items, num_consumers=3, max_queue_size=3)

    assert "successes" in result and "failures" in result
    assert len(result["successes"]) == 5, f"Expected 5 successes, got {len(result['successes'])}"
    assert len(result["failures"]) == 2, f"Expected 2 failures, got {len(result['failures'])}"
    assert all("url" in f and "error" in f for f in result["failures"])
    print(f"  PASS -- {len(result['successes'])} successes, {len(result['failures'])} failures")


# ===========================================================================
# Main runner
# ===========================================================================

async def main() -> None:
    print("=" * 60)
    print("  Module 02: Async Python Exercises")
    print("  Implement the TODO sections, then run this file.")
    print("=" * 60)
    print()

    exercises = [
        ("Exercise 1", test_exercise_1),
        ("Exercise 2", test_exercise_2),
        ("Exercise 3", test_exercise_3),
        ("Exercise 4", test_exercise_4),
        ("Exercise 5", test_exercise_5),
    ]

    passed = 0
    failed = 0

    for name, test_fn in exercises:
        try:
            await test_fn()
            passed += 1
        except NotImplementedError:
            print(f"--- {name}: NOT IMPLEMENTED (skipped) ---")
        except AssertionError as e:
            print(f"--- {name}: FAILED -- {e} ---")
            failed += 1
        except Exception as e:
            print(f"--- {name}: ERROR -- {type(e).__name__}: {e} ---")
            failed += 1
        print()

    print("=" * 60)
    total = passed + failed
    not_impl = len(exercises) - total
    print(f"  Results: {passed} passed, {failed} failed, {not_impl} not implemented")
    if passed == len(exercises):
        print("  All exercises complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
