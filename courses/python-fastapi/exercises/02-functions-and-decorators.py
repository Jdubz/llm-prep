"""
Functions & Decorators Exercises

Closures, higher-order functions, and decorator patterns. These are the
building blocks behind @app.get(), @field_validator, and every other
decorator you'll use in FastAPI.

Run:  python exercises/02-functions-and-decorators.py
"""

from __future__ import annotations

import functools
import time
from collections import deque
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


# ============================================================================
# EXERCISE 1: Memoize Decorator
# ============================================================================
#
# Write a @memoize decorator that caches function results by arguments.
# If the function is called again with the same args, return the cached
# result instead of recomputing.
#
# Requirements:
#   - Cache results keyed by (args, frozenset(kwargs.items()))
#   - Use functools.wraps to preserve the original function's metadata
#   - The cache should be accessible as func.cache (attach it to the wrapper)
#   - Only works with hashable arguments (fine for this exercise)
#
# Hints:
#   - The wrapper function is a closure over a dict (the cache)
#   - Build a cache key from args and kwargs: (args, frozenset(kwargs.items()))
#   - Check if key is in cache before calling the function
#   - Attach the cache dict to the wrapper: wrapper.cache = cache
#
# Expected behavior:
#   @memoize
#   def fib(n):
#       if n < 2: return n
#       return fib(n - 1) + fib(n - 2)
#   fib(30)  # fast, not exponential
#   len(fib.cache)  # 31 entries


def memoize(func: F) -> F:
    """Decorator that caches function results by arguments."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 2: Retry Decorator
# ============================================================================
#
# Write a @retry decorator factory that retries a function on exception
# with exponential backoff.
#
# Requirements:
#   - @retry(max_attempts=3, delay=0.1) — decorator factory syntax
#   - Retries up to max_attempts times on any Exception
#   - Delay doubles after each attempt (exponential backoff)
#   - If all attempts fail, raise the last exception
#   - Use functools.wraps
#   - Use time.sleep for delays
#
# Hints:
#   - Three layers: retry(args) -> decorator(func) -> wrapper(*args, **kwargs)
#   - In the wrapper, loop max_attempts times with try/except
#   - On each failure, sleep for the current delay, then double it
#   - On the last attempt, let the exception propagate
#
# Expected behavior:
#   attempt_count = 0
#   @retry(max_attempts=3, delay=0.01)
#   def flaky():
#       nonlocal attempt_count
#       attempt_count += 1
#       if attempt_count < 3:
#           raise ConnectionError("fail")
#       return "ok"
#   flaky()  # returns "ok" on 3rd attempt


def retry(max_attempts: int = 3, delay: float = 0.1) -> Callable[[F], F]:
    """Decorator factory that retries a function with exponential backoff."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 3: Pipe Function
# ============================================================================
#
# Implement pipe() that composes functions left-to-right. The result of
# each function is passed as input to the next.
#
# Requirements:
#   - pipe(f, g, h)(x) is equivalent to h(g(f(x)))
#   - Handle zero functions (return identity)
#   - Handle single function (return it as-is)
#   - Works with any callable
#
# Hints:
#   - Use functools.reduce to chain function calls
#   - reduce(lambda acc, fn: fn(acc), funcs, initial_value)
#   - Return a lambda or inner function that applies reduce
#
# Expected behavior:
#   transform = pipe(
#       lambda x: x * 2,
#       lambda x: x + 10,
#       str,
#   )
#   transform(5)  # -> "20" (5*2=10, 10+10=20, str(20)="20")


def pipe(*funcs: Callable) -> Callable:
    """Compose functions left-to-right."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 4: Partial Application
# ============================================================================
#
# Implement your own partial() function from scratch (don't use
# functools.partial). It should pre-fill some arguments of a function.
#
# Requirements:
#   - my_partial(func, *args, **kwargs) returns a new function
#   - The new function accepts additional args/kwargs
#   - Positional args are prepended, keyword args are merged
#   - Later kwargs override earlier ones
#
# Hints:
#   - Return an inner function that calls func(*fixed_args + new_args, **merged_kwargs)
#   - Merge kwargs with: {**fixed_kwargs, **new_kwargs}
#
# Expected behavior:
#   def add(a, b, c=0):
#       return a + b + c
#   add5 = my_partial(add, 5)
#   add5(3)       # -> 8  (5 + 3 + 0)
#   add5(3, c=10) # -> 18 (5 + 3 + 10)


def my_partial(func: Callable, *fixed_args: Any, **fixed_kwargs: Any) -> Callable:
    """Partial application: pre-fill some arguments of a function."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 5: Validate Decorator
# ============================================================================
#
# Write a @validate decorator factory that type-checks arguments at runtime.
# This is a simplified version of what Pydantic does under the hood.
#
# Requirements:
#   - @validate(x=int, y=str) — specify expected types as keyword args
#   - Before calling the function, check that each named arg matches its type
#   - Raise TypeError with a descriptive message if a check fails
#   - Only validate args that are specified (ignore others)
#   - Use inspect.signature to map positional args to parameter names
#
# Hints:
#   - import inspect; sig = inspect.signature(func)
#   - sig.bind(*args, **kwargs).arguments gives a dict of {param_name: value}
#   - isinstance(value, expected_type) for the check
#   - Three layers: validate(**types) -> decorator(func) -> wrapper(*args, **kwargs)
#
# Expected behavior:
#   @validate(x=int, y=int)
#   def add(x, y):
#       return x + y
#   add(1, 2)      # -> 3
#   add("1", 2)    # -> TypeError: x must be int, got str


def validate(**type_hints: type) -> Callable[[F], F]:
    """Decorator factory that validates argument types at runtime."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 6: Rate Limiter
# ============================================================================
#
# Write a rate_limiter decorator factory that limits how often a function
# can be called within a time window.
#
# Requirements:
#   - @rate_limiter(max_calls=5, period=1.0) — max N calls per period seconds
#   - If the limit is exceeded, raise a RuntimeError("Rate limit exceeded")
#   - Track call timestamps using a deque
#   - Clean up expired timestamps before checking the limit
#   - Use time.monotonic() for timestamps (not time.time())
#
# Hints:
#   - Use collections.deque to store timestamps
#   - Before each call, remove timestamps older than (now - period)
#   - If len(timestamps) >= max_calls after cleanup, raise RuntimeError
#   - Otherwise, append the current timestamp and call the function
#
# Expected behavior:
#   @rate_limiter(max_calls=2, period=0.1)
#   def ping():
#       return "pong"
#   ping()  # "pong"
#   ping()  # "pong"
#   ping()  # RuntimeError: Rate limit exceeded


def rate_limiter(max_calls: int = 5, period: float = 1.0) -> Callable[[F], F]:
    """Decorator factory that rate-limits function calls."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

# def test_memoize():
#     print("\n=== EXERCISE 1: Memoize ===")
#     call_count = 0
#
#     @memoize
#     def fib(n):
#         nonlocal call_count
#         call_count += 1
#         if n < 2:
#             return n
#         return fib(n - 1) + fib(n - 2)
#
#     result = fib(30)
#     assert result == 832040
#     assert call_count == 31, f"Expected 31 calls, got {call_count}"
#     assert len(fib.cache) == 31
#     print(f"fib(30) = {result}, calls = {call_count}, cached = {len(fib.cache)}")
#
#     # Verify cache hit
#     call_count = 0
#     fib(30)
#     assert call_count == 0, "Should have hit cache"
#     print("Cache hit verified")
#     print("EXERCISE 1: PASSED")
#
#
# def test_retry():
#     print("\n=== EXERCISE 2: Retry ===")
#     attempt_count = 0
#
#     @retry(max_attempts=3, delay=0.01)
#     def flaky():
#         nonlocal attempt_count
#         attempt_count += 1
#         if attempt_count < 3:
#             raise ConnectionError("fail")
#         return "ok"
#
#     result = flaky()
#     assert result == "ok"
#     assert attempt_count == 3
#     print(f"Succeeded after {attempt_count} attempts")
#
#     # All attempts fail
#     @retry(max_attempts=2, delay=0.01)
#     def always_fails():
#         raise ValueError("nope")
#
#     try:
#         always_fails()
#         print("ERROR: Should have raised ValueError")
#     except ValueError:
#         print("Final exception propagated (expected)")
#     print("EXERCISE 2: PASSED")
#
#
# def test_pipe():
#     print("\n=== EXERCISE 3: Pipe ===")
#     transform = pipe(
#         lambda x: x * 2,
#         lambda x: x + 10,
#         str,
#     )
#     assert transform(5) == "20"
#     print(f"pipe(5) = {transform(5)}")
#
#     # Identity
#     identity = pipe()
#     assert identity(42) == 42
#
#     # Single function
#     double = pipe(lambda x: x * 2)
#     assert double(5) == 10
#     print("Edge cases passed")
#     print("EXERCISE 3: PASSED")
#
#
# def test_partial():
#     print("\n=== EXERCISE 4: Partial ===")
#     def add(a, b, c=0):
#         return a + b + c
#
#     add5 = my_partial(add, 5)
#     assert add5(3) == 8
#     assert add5(3, c=10) == 18
#     print(f"add5(3) = {add5(3)}, add5(3, c=10) = {add5(3, c=10)}")
#
#     # Partial with kwargs
#     add5_c10 = my_partial(add, 5, c=10)
#     assert add5_c10(3) == 18
#
#     # Override kwargs
#     assert add5_c10(3, c=0) == 8
#     print("Edge cases passed")
#     print("EXERCISE 4: PASSED")
#
#
# def test_validate():
#     print("\n=== EXERCISE 5: Validate ===")
#
#     @validate(x=int, y=int)
#     def add(x, y):
#         return x + y
#
#     assert add(1, 2) == 3
#     assert add(x=1, y=2) == 3
#     print(f"add(1, 2) = {add(1, 2)}")
#
#     try:
#         add("1", 2)
#         print("ERROR: Should have raised TypeError")
#     except TypeError as e:
#         print(f"Caught TypeError: {e}")
#
#     # Unvalidated args pass through
#     @validate(x=int)
#     def greet(x, name="world"):
#         return f"{x}: hello {name}"
#
#     assert greet(1, name="alice") == "1: hello alice"
#     print("Edge cases passed")
#     print("EXERCISE 5: PASSED")
#
#
# def test_rate_limiter():
#     print("\n=== EXERCISE 6: Rate Limiter ===")
#
#     @rate_limiter(max_calls=2, period=0.1)
#     def ping():
#         return "pong"
#
#     assert ping() == "pong"
#     assert ping() == "pong"
#
#     try:
#         ping()
#         print("ERROR: Should have raised RuntimeError")
#     except RuntimeError as e:
#         print(f"Caught RuntimeError: {e}")
#
#     # Wait for period to expire
#     time.sleep(0.15)
#     assert ping() == "pong"
#     print("Rate limit reset after period")
#     print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    exercises: list[tuple[str, Callable, list]] = [
        ("1 - Memoize Decorator", memoize, [lambda x: x]),
        ("2 - Retry Decorator", retry, []),
        ("3 - Pipe Function", pipe, [lambda x: x]),
        ("4 - Partial Application", my_partial, [lambda x: x, 1]),
        ("5 - Validate Decorator", validate, []),
        ("6 - Rate Limiter", rate_limiter, []),
    ]

    print("Functions & Decorators Exercises")
    print("=" * 40)

    for name, func, args in exercises:
        try:
            result = func(*args)
            # For decorator factories, try calling the result
            if callable(result) and args:
                result(lambda: None) if not args else None
            print(f"  {name}: IMPLEMENTED")
        except NotImplementedError:
            print(f"  {name}: not implemented")

    # Uncomment below (and the test functions above) to run full tests:
    # print()
    # test_memoize()
    # test_retry()
    # test_pipe()
    # test_partial()
    # test_validate()
    # test_rate_limiter()
    # print("\n=== ALL EXERCISES PASSED ===")
