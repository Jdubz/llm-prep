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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (decorators, closures)
#   - ../../fastapi/00-fastapi-foundations/01-http-routing-and-decorators.md (decorator patterns in practice)
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
#   @functools.wraps pattern — the standard way to write a decorator:
#     import functools
#     def my_decorator(func):
#         @functools.wraps(func)           # copies __name__, __doc__, etc.
#         def wrapper(*args, **kwargs):
#             # ... pre-processing ...
#             result = func(*args, **kwargs)
#             # ... post-processing ...
#             return result
#         return wrapper
#
#   Why functools.wraps matters:
#   - Without it, decorated_func.__name__ returns "wrapper" instead of
#     the original function name. This breaks debugging and introspection.
#
#   Closure structure for memoize:
#     def memoize(func):
#         cache = {}                       # closed over by wrapper
#         @functools.wraps(func)
#         def wrapper(*args, **kwargs):
#             key = (args, frozenset(kwargs.items()))
#             if key not in cache:
#                 cache[key] = func(*args, **kwargs)
#             return cache[key]
#         wrapper.cache = cache            # expose cache as attribute
#         return wrapper
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
    cache = {}
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, frozenset(kwargs.items()))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    wrapper.cache = cache # type: ignore
    return wrapper # type: ignore


# ============================================================================
# EXERCISE 2: Retry Decorator
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (decorator factories)
#   - ../../fastapi/00-fastapi-foundations/01-http-routing-and-decorators.md (parameterized decorators)
#   - ../01-async-python/02-concurrency-patterns.md (retry patterns in production)
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
#   Decorator factory pattern (decorator that accepts arguments):
#   The key insight is three nested functions:
#
#     def retry(max_attempts=3, delay=0.1):    # 1. factory — accepts config
#         def decorator(func):                  # 2. decorator — accepts func
#             @functools.wraps(func)
#             def wrapper(*args, **kwargs):     # 3. wrapper — replaces func
#                 current_delay = delay
#                 for attempt in range(1, max_attempts + 1):
#                     try:
#                         return func(*args, **kwargs)
#                     except Exception:
#                         if attempt == max_attempts:
#                             raise              # re-raise on last attempt
#                         time.sleep(current_delay)
#                         current_delay *= 2     # exponential backoff
#             return wrapper
#         return decorator
#
#   Usage: @retry(max_attempts=3) calls retry() which returns decorator,
#   which is then applied to the function. This is why you need three layers.
#
#   Compare with a simple decorator (no arguments) which has only two layers:
#     def simple(func):           # decorator — accepts func
#         def wrapper(*args):     # wrapper — replaces func
#             ...
#         return wrapper
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (higher-order functions)
#   - ../03-python-internals/01-object-model-and-memory.md (callables)
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
#   functools.reduce API:
#     from functools import reduce
#     reduce(function, iterable, initial)
#     # Applies function cumulatively: function(function(initial, item1), item2)
#
#   Pattern — function composition with reduce:
#     def pipe(*funcs):
#         def piped(x):
#             return reduce(lambda acc, fn: fn(acc), funcs, x)
#         return piped
#
#   How it works step-by-step for pipe(double, add10, str)(5):
#     reduce starts with acc=5 (the initial value)
#     Step 1: acc = double(5)  -> 10
#     Step 2: acc = add10(10)  -> 20
#     Step 3: acc = str(20)    -> "20"
#
#   Edge cases:
#   - pipe() with no functions should return an identity function: lambda x: x
#   - pipe(f) with one function should behave like calling f directly
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (closures, *args/**kwargs)
#   - ../../fastapi/00-fastapi-foundations/02-dependency-injection.md (partial application in DI)
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
#   How *args and **kwargs work:
#     def example(*args, **kwargs):
#         # args is a tuple of positional arguments
#         # kwargs is a dict of keyword arguments
#         print(args)     # (1, 2, 3)
#         print(kwargs)   # {"x": 10, "y": 20}
#     example(1, 2, 3, x=10, y=20)
#
#   Dict merging (later values override earlier):
#     {**{"a": 1, "b": 2}, **{"b": 3, "c": 4}}  # -> {"a": 1, "b": 3, "c": 4}
#
#   Pattern — implementing partial from scratch:
#     def my_partial(func, *fixed_args, **fixed_kwargs):
#         def wrapper(*args, **kwargs):
#             merged_kwargs = {**fixed_kwargs, **kwargs}  # new kwargs override
#             return func(*fixed_args, *args, **merged_kwargs)
#         return wrapper
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (decorator factories, inspect)
#   - ../../fastapi/00-fastapi-foundations/02-dependency-injection.md (runtime type validation)
#   - ../03-python-internals/03-imports-and-runtime.md (inspect module)
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
#   inspect.signature API — mapping positional args to parameter names:
#     import inspect
#     def add(x, y, z=0): ...
#     sig = inspect.signature(add)
#     bound = sig.bind(1, 2, z=3)        # bind actual call args to params
#     bound.arguments                     # OrderedDict({"x": 1, "y": 2, "z": 3})
#
#   This is how you figure out which parameter name each positional arg
#   corresponds to, so you can validate by name.
#
#   Pattern — three-layer decorator factory with validation:
#     def validate(**type_hints):            # layer 1: accepts config
#         def decorator(func):               # layer 2: accepts function
#             sig = inspect.signature(func)
#             @functools.wraps(func)
#             def wrapper(*args, **kwargs):  # layer 3: replaces function
#                 bound = sig.bind(*args, **kwargs)
#                 bound.apply_defaults()
#                 for name, expected_type in type_hints.items():
#                     if name in bound.arguments:
#                         value = bound.arguments[name]
#                         if not isinstance(value, expected_type):
#                             raise TypeError(
#                                 f"{name} must be {expected_type.__name__}, "
#                                 f"got {type(value).__name__}"
#                             )
#                 return func(*args, **kwargs)
#             return wrapper
#         return decorator
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (decorator factories, deque)
#   - ../../fastapi/03-advanced-api-patterns/02-pagination-filtering-and-bulk-operations.md (rate limiting)
#   - ../01-async-python/02-concurrency-patterns.md (throttling patterns)
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
#   collections.deque — a double-ended queue:
#     from collections import deque
#     d = deque()
#     d.append(item)       # add to right
#     d.appendleft(item)   # add to left
#     d.popleft()           # remove from left (O(1), unlike list.pop(0))
#     d[0]                  # peek at leftmost
#     len(d)                # number of items
#
#   time.monotonic() vs time.time():
#   - time.monotonic() cannot go backwards (immune to clock adjustments)
#   - Always use monotonic for measuring intervals and rate limiting
#
#   Pattern — sliding window rate limiter:
#     def rate_limiter(max_calls=5, period=1.0):
#         def decorator(func):
#             timestamps = deque()       # closed over by wrapper
#             @functools.wraps(func)
#             def wrapper(*args, **kwargs):
#                 now = time.monotonic()
#                 # Evict expired timestamps
#                 while timestamps and timestamps[0] <= now - period:
#                     timestamps.popleft()
#                 if len(timestamps) >= max_calls:
#                     raise RuntimeError("Rate limit exceeded")
#                 timestamps.append(now)
#                 return func(*args, **kwargs)
#             return wrapper
#         return decorator
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

def test_memoize():
    print("\n=== EXERCISE 1: Memoize ===")
    call_count = 0

    @memoize
    def fib(n):
        nonlocal call_count
        call_count += 1
        if n < 2:
            return n
        return fib(n - 1) + fib(n - 2)

    result = fib(30)
    assert result == 832040
    assert call_count == 31, f"Expected 31 calls, got {call_count}"
    assert len(fib.cache) == 31
    print(f"fib(30) = {result}, calls = {call_count}, cached = {len(fib.cache)}")

    # Verify cache hit
    call_count = 0
    fib(30)
    assert call_count == 0, "Should have hit cache"
    print("Cache hit verified")
    print("EXERCISE 1: PASSED")


def test_retry():
    print("\n=== EXERCISE 2: Retry ===")
    attempt_count = 0

    @retry(max_attempts=3, delay=0.01)
    def flaky():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("fail")
        return "ok"

    result = flaky()
    assert result == "ok"
    assert attempt_count == 3
    print(f"Succeeded after {attempt_count} attempts")

    # All attempts fail
    @retry(max_attempts=2, delay=0.01)
    def always_fails():
        raise ValueError("nope")

    try:
        always_fails()
        print("ERROR: Should have raised ValueError")
    except ValueError:
        print("Final exception propagated (expected)")
    print("EXERCISE 2: PASSED")


def test_pipe():
    print("\n=== EXERCISE 3: Pipe ===")
    transform = pipe(
        lambda x: x * 2,
        lambda x: x + 10,
        str,
    )
    assert transform(5) == "20"
    print(f"pipe(5) = {transform(5)}")

    # Identity
    identity = pipe()
    assert identity(42) == 42

    # Single function
    double = pipe(lambda x: x * 2)
    assert double(5) == 10
    print("Edge cases passed")
    print("EXERCISE 3: PASSED")


def test_partial():
    print("\n=== EXERCISE 4: Partial ===")
    def add(a, b, c=0):
        return a + b + c

    add5 = my_partial(add, 5)
    assert add5(3) == 8
    assert add5(3, c=10) == 18
    print(f"add5(3) = {add5(3)}, add5(3, c=10) = {add5(3, c=10)}")

    # Partial with kwargs
    add5_c10 = my_partial(add, 5, c=10)
    assert add5_c10(3) == 18

    # Override kwargs
    assert add5_c10(3, c=0) == 8
    print("Edge cases passed")
    print("EXERCISE 4: PASSED")


def test_validate():
    print("\n=== EXERCISE 5: Validate ===")

    @validate(x=int, y=int)
    def add(x, y):
        return x + y

    assert add(1, 2) == 3
    assert add(x=1, y=2) == 3
    print(f"add(1, 2) = {add(1, 2)}")

    try:
        add("1", 2)
        print("ERROR: Should have raised TypeError")
    except TypeError as e:
        print(f"Caught TypeError: {e}")

    # Unvalidated args pass through
    @validate(x=int)
    def greet(x, name="world"):
        return f"{x}: hello {name}"

    assert greet(1, name="alice") == "1: hello alice"
    print("Edge cases passed")
    print("EXERCISE 5: PASSED")


def test_rate_limiter():
    print("\n=== EXERCISE 6: Rate Limiter ===")

    @rate_limiter(max_calls=2, period=0.1)
    def ping():
        return "pong"

    assert ping() == "pong"
    assert ping() == "pong"

    try:
        ping()
        print("ERROR: Should have raised RuntimeError")
    except RuntimeError as e:
        print(f"Caught RuntimeError: {e}")

    # Wait for period to expire
    time.sleep(0.15)
    assert ping() == "pong"
    print("Rate limit reset after period")
    print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    print("Functions & Decorators Exercises")
    print("=" * 60)

    tests = [
        ("Exercise 1: Memoize Decorator", test_memoize),
        ("Exercise 2: Retry Decorator", test_retry),
        ("Exercise 3: Pipe Function", test_pipe),
        ("Exercise 4: Partial Application", test_partial),
        ("Exercise 5: Validate Decorator", test_validate),
        ("Exercise 6: Rate Limiter", test_rate_limiter),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except NotImplementedError:
            print(f"  {name}: NOT IMPLEMENTED")
            failed += 1
        except AssertionError as e:
            print(f"  {name}: FAILED -- {e}")
            failed += 1
        except Exception as e:
            print(f"  {name}: ERROR -- {type(e).__name__}: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)
