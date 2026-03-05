"""
Python Interview Prep: Complete Examples

Runnable examples demonstrating Python patterns commonly tested in interviews:
decorators, generators, context managers, metaclasses, descriptors, async patterns.

Run with: python examples.py
"""
from __future__ import annotations

import asyncio
import functools
import sys
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar

# ============================================================================
# EXAMPLE 1: Decorator Patterns (timing, retry, memoize)
# ============================================================================

def timing(func):
    """Timing decorator — measures execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"  {func.__name__} took {time.perf_counter() - start:.4f}s")
        return result
    return wrapper


def retry(max_attempts: int = 3, backoff: float = 0.1):
    """Retry decorator factory with exponential backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    wait = backoff * (2 ** (attempt - 1))
                    print(f"  Attempt {attempt} failed: {e}. Retrying in {wait}s...")
        return wrapper
    return decorator


def memoize(func):
    """Memoize decorator — caches results by arguments."""
    cache: dict = {}
    @functools.wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    wrapper.cache = cache
    return wrapper


@memoize
def fibonacci(n: int) -> int:
    return n if n < 2 else fibonacci(n - 1) + fibonacci(n - 2)


# ============================================================================
# EXAMPLE 2: Generator Patterns (lazy evaluation, pipelines)
# ============================================================================

def read_chunks(data: list, chunk_size: int):
    """Yield successive chunks from data."""
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def pipeline_demo():
    """Generator pipeline: generate -> filter -> transform -> consume."""
    # Generator pipeline (each step is lazy)
    numbers = range(1, 101)
    evens = (n for n in numbers if n % 2 == 0)
    squares = (n ** 2 for n in evens)
    big_squares = (n for n in squares if n > 100)

    # Only now does computation happen
    result = list(big_squares)
    print(f"  Pipeline result (first 5): {result[:5]}...")
    return result


# ============================================================================
# EXAMPLE 3: Context Manager Patterns
# ============================================================================

@contextmanager
def timer(label: str):
    """Context manager for timing blocks."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"  {label}: {elapsed:.4f}s")


@contextmanager
def temporary_attr(obj: Any, name: str, value: Any):
    """Temporarily set an attribute, restore on exit."""
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


# ============================================================================
# EXAMPLE 4: Descriptor Protocol
# ============================================================================

class Validated:
    """Descriptor that validates values on assignment."""
    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{self.name} must be >= {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self.name} must be <= {self.max_value}")
        obj.__dict__[self.name] = value


class Product:
    price = Validated(min_value=0)
    quantity = Validated(min_value=0, max_value=10_000)

    def __init__(self, name: str, price: float, quantity: int):
        self.name = name
        self.price = price
        self.quantity = quantity

    def __repr__(self) -> str:
        return f"Product({self.name!r}, price={self.price}, qty={self.quantity})"


# ============================================================================
# EXAMPLE 5: __init_subclass__ for Plugin Registration
# ============================================================================

class Plugin:
    """Base class that auto-registers subclasses."""
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, plugin_name: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__.lower()
        Plugin._registry[name] = cls

    @classmethod
    def get_plugin(cls, name: str) -> type:
        return cls._registry[name]


class EmailNotifier(Plugin, plugin_name="email"):
    def send(self, msg: str) -> str:
        return f"Email: {msg}"


class SlackNotifier(Plugin, plugin_name="slack"):
    def send(self, msg: str) -> str:
        return f"Slack: {msg}"


# ============================================================================
# EXAMPLE 6: Async Patterns (gather, TaskGroup, semaphore)
# ============================================================================

async def fetch_data(name: str, delay: float) -> dict:
    """Simulated async fetch."""
    await asyncio.sleep(delay)
    return {"name": name, "data": f"result-{name}"}


async def gather_demo():
    """asyncio.gather — concurrent fetching."""
    results = await asyncio.gather(
        fetch_data("users", 0.1),
        fetch_data("orders", 0.15),
        fetch_data("products", 0.05),
    )
    for r in results:
        print(f"  Gathered: {r['name']} -> {r['data']}")


async def semaphore_demo():
    """Semaphore to limit concurrent operations."""
    sem = asyncio.Semaphore(2)  # max 2 concurrent

    async def limited_fetch(name: str):
        async with sem:
            return await fetch_data(name, 0.1)

    results = await asyncio.gather(
        *[limited_fetch(f"item-{i}") for i in range(5)]
    )
    print(f"  Semaphore: fetched {len(results)} items (max 2 concurrent)")


# ============================================================================
# Run all examples
# ============================================================================

def _test_all():
    print("=== 1: Decorator Patterns ===")
    print(f"  fib(10) = {fibonacci(10)}")
    print(f"  fib(20) = {fibonacci(20)}")
    print(f"  Cache size: {len(fibonacci.cache)}")

    print("\n=== 2: Generator Patterns ===")
    chunks = list(read_chunks(list(range(10)), 3))
    print(f"  Chunks: {chunks}")
    pipeline_demo()

    print("\n=== 3: Context Manager Patterns ===")
    with timer("sum"):
        total = sum(range(1_000_000))
    print(f"  Total: {total}")

    print("\n=== 4: Descriptor Protocol ===")
    p = Product("Widget", 9.99, 100)
    print(f"  {p}")
    try:
        Product("Bad", -1, 0)
    except ValueError as e:
        print(f"  Validation: {e}")

    print("\n=== 5: Plugin Registration ===")
    print(f"  Registry: {list(Plugin._registry.keys())}")
    notifier = Plugin.get_plugin("email")()
    print(f"  {notifier.send('Hello!')}")

    print("\n=== 6: Async Patterns ===")
    asyncio.run(gather_demo())
    asyncio.run(semaphore_demo())

    print("\nAll examples completed.")


if __name__ == "__main__":
    _test_all()
