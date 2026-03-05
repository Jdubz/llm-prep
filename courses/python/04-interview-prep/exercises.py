"""
Python Interview Exercises: Timed Coding Challenges

Pure Python exercises — no web framework dependencies.
Time yourself — these simulate real interview pacing.
"""
from __future__ import annotations

import asyncio
import functools
import time
from typing import Any

# ============================================================================
# EXERCISE 1: LRU Cache with TTL (20 min)
# ============================================================================
# CONCEPTS FROM:
#   01-interview-fundamentals.md:
#     - Q3 (Decorators), Q12 (Generators/Iterators)
#   Module 00 (Python Fundamentals):
#     - 02-classes-decorators-and-oop.md -> dunder methods, decorator factories
#
# HINTS:
#   - Use a dict for cache storage and an OrderedDict or dict with timestamps
#   - On access, check if entry is expired (time.monotonic() - stored_time > ttl)
#   - On set, if at capacity, evict the least recently used (first inserted)
#   - Decorator should work like: @lru_cache_ttl(maxsize=128, ttl=60)
# ----------------------------------------------------------------------------
# Implement an LRU cache decorator with TTL (time-to-live).
# - maxsize: max number of cached results
# - ttl: seconds before a cache entry expires
# - When cache is full, evict least recently used entry
# - Expired entries should be treated as cache misses

def lru_cache_ttl(maxsize: int = 128, ttl: float = 60.0):
    """Decorator factory: LRU cache with TTL expiration."""
    pass  # TODO: implement


# ============================================================================
# EXERCISE 2: Event Emitter (15 min)
# ============================================================================
# CONCEPTS FROM:
#   01-interview-fundamentals.md:
#     - Q3 (Decorators), Q10 (*args/**kwargs)
#   Module 00:
#     - 02-classes-decorators-and-oop.md -> classes, dunder methods
#
# HINTS:
#   - _handlers: dict[str, list[callable]]
#   - on(event, handler): append handler to list
#   - emit(event, *args, **kwargs): call all handlers for event
#   - off(event, handler): remove specific handler
#   - once(event, handler): register handler that auto-removes after first call
# ----------------------------------------------------------------------------
# Implement an EventEmitter class (like Node.js EventEmitter).

class EventEmitter:
    """
    >>> ee = EventEmitter()
    >>> results = []
    >>> ee.on("data", lambda x: results.append(x))
    >>> ee.emit("data", 42)
    >>> results
    [42]
    """
    pass  # TODO: implement


# ============================================================================
# EXERCISE 3: Async Rate Limiter (20 min)
# ============================================================================
# CONCEPTS FROM:
#   01-interview-fundamentals.md:
#     - Q19 (gather vs TaskGroup), Q20 (threading vs asyncio)
#   Module 01 (Async Python):
#     - 02-concurrency-patterns.md -> semaphores, rate limiting
#
# HINTS:
#   - Use asyncio.Semaphore for max concurrent
#   - Track timestamps of recent calls in a deque
#   - Before allowing a call, check if we've exceeded rate in the time window
#   - Use asyncio.sleep() to wait if rate limited
# ----------------------------------------------------------------------------
# Implement an async rate limiter that limits:
# - max_concurrent: maximum simultaneous executions
# - max_per_second: maximum calls per second (sliding window)

class AsyncRateLimiter:
    """
    limiter = AsyncRateLimiter(max_concurrent=3, max_per_second=10)
    async with limiter:
        await do_work()
    """
    def __init__(self, max_concurrent: int = 5, max_per_second: float = 10.0):
        pass  # TODO: init semaphore, tracking state

    async def __aenter__(self):
        pass  # TODO: acquire semaphore, enforce rate limit

    async def __aexit__(self, *args):
        pass  # TODO: release semaphore


# ============================================================================
# EXERCISE 4: Pipeline Builder (15 min)
# ============================================================================
# CONCEPTS FROM:
#   01-interview-fundamentals.md:
#     - Q12 (Generators), Q3 (Decorators/closures)
#   Module 00:
#     - 02-classes-decorators-and-oop.md -> classes, __call__
#
# HINTS:
#   - Store a list of transform functions
#   - pipe(fn) appends fn to the pipeline, returns self (for chaining)
#   - __call__ applies all transforms in sequence
#   - process(iterable) applies the pipeline to each item (generator)
# ----------------------------------------------------------------------------
# Implement a chainable data pipeline.

class Pipeline:
    """
    >>> p = Pipeline().pipe(str.strip).pipe(str.upper).pipe(lambda s: s + "!")
    >>> p("  hello  ")
    'HELLO!'
    >>> list(p.process(["  hello  ", "  world  "]))
    ['HELLO!', 'WORLD!']
    """
    pass  # TODO: implement


# ============================================================================
# EXERCISE 5: Context-Aware Logger (10 min)
# ============================================================================
# CONCEPTS FROM:
#   01-interview-fundamentals.md:
#     - Q4 (Context managers), Q7 (Descriptors)
#   Module 00:
#     - 02-classes-decorators-and-oop.md -> context managers
#
# HINTS:
#   - Use a list as a context stack
#   - context(name) returns a context manager that pushes/pops from the stack
#   - log(message) prefixes with " > ".join(context_stack)
# ----------------------------------------------------------------------------
# Implement a logger with nestable context.

class ContextLogger:
    """
    >>> logger = ContextLogger()
    >>> with logger.context("auth"):
    ...     logger.log("checking token")      # prints "[auth] checking token"
    ...     with logger.context("db"):
    ...         logger.log("querying users")  # prints "[auth > db] querying users"
    """
    pass  # TODO: implement


# ============================================================================
# TESTS (run: python exercises.py)
# ============================================================================

def test_exercise_1():
    print("\n=== EXERCISE 1: LRU Cache with TTL ===")
    try:
        @lru_cache_ttl(maxsize=3, ttl=1.0)
        def square(x):
            return x ** 2

        assert square(2) == 4
        assert square(2) == 4  # cached
        print("  PASSED (basic)")
    except (TypeError, AssertionError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")


def test_exercise_2():
    print("\n=== EXERCISE 2: Event Emitter ===")
    try:
        ee = EventEmitter()
        results = []
        ee.on("data", lambda x: results.append(x))
        ee.emit("data", 42)
        ee.emit("data", 100)
        assert results == [42, 100]
        print("  PASSED")
    except (TypeError, AssertionError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")


def test_exercise_3():
    print("\n=== EXERCISE 3: Async Rate Limiter ===")
    try:
        limiter = AsyncRateLimiter(max_concurrent=2, max_per_second=10)

        async def test():
            async with limiter:
                await asyncio.sleep(0.01)
                return True

        result = asyncio.run(test())
        assert result is True
        print("  PASSED (basic)")
    except (TypeError, AssertionError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")


def test_exercise_4():
    print("\n=== EXERCISE 4: Pipeline Builder ===")
    try:
        p = Pipeline().pipe(str.strip).pipe(str.upper).pipe(lambda s: s + "!")
        assert p("  hello  ") == "HELLO!"
        assert list(p.process(["  hello  ", "  world  "])) == ["HELLO!", "WORLD!"]
        print("  PASSED")
    except (TypeError, AssertionError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")


def test_exercise_5():
    print("\n=== EXERCISE 5: Context Logger ===")
    try:
        logger = ContextLogger()
        output = []
        logger._print = lambda msg: output.append(msg)  # capture output
        with logger.context("auth"):
            logger.log("checking")
        assert any("auth" in o for o in output)
        print("  PASSED")
    except (TypeError, AssertionError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")


if __name__ == "__main__":
    test_exercise_1()
    test_exercise_2()
    test_exercise_3()
    test_exercise_4()
    test_exercise_5()
    print("\n" + "=" * 60)
    print("Implement each exercise, then re-run to verify.")
    print("=" * 60)
