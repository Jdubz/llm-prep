"""
Module 09: Python Internals — Exercises

Implement each function to pass the assertions at the bottom.
No external dependencies — standard library only.

Topics:
  1. Reference counting & GC
  2. Descriptors
  3. MRO & super()
  4. __slots__ & memory
  5. __new__ / __init__
  6. Weak references
  7. Dunder protocols
  8. Context variables
  9. Bytecode introspection
  10. Generator protocol
"""

from __future__ import annotations

import asyncio
import gc
import sys
import weakref
from contextvars import ContextVar
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Exercise 1: Reference Counting
# ---------------------------------------------------------------------------

def count_references(obj: Any) -> int:
    """
    Return the number of references to `obj` NOT counting:
      - the reference held by this function's `obj` parameter
      - the reference held by sys.getrefcount's argument

    Hint: sys.getrefcount(x) returns count + 1 (the argument itself).
    When called as count_references(x), there are two extra refs:
    one for the caller's argument and one for sys.getrefcount's argument.
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 2: Detect Reference Cycle
# ---------------------------------------------------------------------------

def has_reference_cycle(*objects: Any) -> bool:
    """
    Return True if any of the given objects are part of a reference cycle
    (i.e., the cyclic GC tracks them as unreachable after removing external refs).

    Strategy:
      - Temporarily disable the GC
      - Delete external references
      - Run gc.collect() and check if it found anything
      - Restore GC state

    Hint: gc.collect() returns the number of unreachable objects found.
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 3: Descriptor — Range Validator
# ---------------------------------------------------------------------------

class RangeValidator:
    """
    A data descriptor that enforces a numeric value within [min_val, max_val].

    Usage:
        class Temperature:
            celsius = RangeValidator(-273.15, 1e6)

    Assignment outside the range should raise ValueError.
    Access on the class (not an instance) should return the descriptor itself.
    Access on an instance should return the stored value.

    Use __set_name__ to get the attribute name automatically.
    Store the actual value as f"_{name}" on the instance.
    """

    def __init__(self, min_val: float, max_val: float) -> None:
        # TODO: store min_val, max_val
        raise NotImplementedError

    def __set_name__(self, owner: type, name: str) -> None:
        # TODO: store the private attribute name
        raise NotImplementedError

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        # TODO: return descriptor if accessed on class, value if on instance
        raise NotImplementedError

    def __set__(self, obj: Any, value: float) -> None:
        # TODO: validate and store
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 4: Cooperative Mixin via super()
# ---------------------------------------------------------------------------

class Pipeline:
    """Base class. process() returns the input unchanged."""
    def process(self, data: str) -> str:
        return data


class UpperMixin(Pipeline):
    """Transforms data to uppercase, then passes to super()."""
    def process(self, data: str) -> str:
        # TODO: call super().process() on the uppercased data
        raise NotImplementedError


class StripMixin(Pipeline):
    """Strips whitespace from data, then passes to super()."""
    def process(self, data: str) -> str:
        # TODO: call super().process() on the stripped data
        raise NotImplementedError


class CleaningPipeline(UpperMixin, StripMixin):
    """
    MRO: CleaningPipeline -> UpperMixin -> StripMixin -> Pipeline -> object
    Result: strip first (StripMixin is after UpperMixin in MRO, so it runs
    when UpperMixin calls super()), then uppercase... wait, think carefully.

    Actually trace the MRO: CleaningPipeline.process calls UpperMixin.process
    (first in MRO). UpperMixin uppercases then calls super() → StripMixin.
    StripMixin strips then calls super() → Pipeline (returns as-is).

    So the order is: Upper → Strip → Pipeline.
    Input "  hello  " → "  HELLO  " → "HELLO"
    """
    pass


# ---------------------------------------------------------------------------
# Exercise 5: __slots__ — MemoryEfficient class
# ---------------------------------------------------------------------------

class MemoryEfficient:
    """
    A class representing a 3D vector with x, y, z components.
    Use __slots__ to minimize memory per instance.
    Implement __add__ (component-wise) and __eq__.
    """
    __slots__: tuple[str, ...]  # TODO: define slots

    def __init__(self, x: float, y: float, z: float) -> None:
        # TODO: set attributes
        raise NotImplementedError

    def __add__(self, other: MemoryEfficient) -> MemoryEfficient:
        # TODO: return new MemoryEfficient(self.x + other.x, ...)
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        # TODO: compare components
        raise NotImplementedError

    def __hash__(self) -> int:
        # TODO: hash the tuple of components
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 6: Singleton via __new__
# ---------------------------------------------------------------------------

class AppConfig:
    """
    A singleton configuration class.
    Only one instance should ever exist.
    __init__ should only run on the first instantiation (use a _initialized flag).

    Attributes set on first init: settings (empty dict), debug (bool from arg).
    Subsequent instantiations return the same object without re-initializing.
    """
    _instance: AppConfig | None = None

    def __new__(cls, debug: bool = False) -> AppConfig:
        # TODO: implement singleton pattern
        raise NotImplementedError

    def __init__(self, debug: bool = False) -> None:
        # TODO: guard against re-initialization
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 7: Weak Reference Cache
# ---------------------------------------------------------------------------

class WeakCache:
    """
    A cache that holds weak references to its values.
    When a value is garbage collected, its key is automatically removed.

    Methods:
        set(key, value): store value with weak reference
        get(key, default=None): retrieve value, or default if gone/missing
        __len__: number of live entries
    """

    def __init__(self) -> None:
        # TODO: use weakref.WeakValueDictionary
        raise NotImplementedError

    def set(self, key: str, value: Any) -> None:
        # TODO
        raise NotImplementedError

    def get(self, key: str, default: Any = None) -> Any:
        # TODO
        raise NotImplementedError

    def __len__(self) -> int:
        # TODO
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 8: Custom Iterator Protocol
# ---------------------------------------------------------------------------

class Fibonacci:
    """
    An iterator that yields Fibonacci numbers up to a limit.

    Usage:
        list(Fibonacci(10))   # [1, 1, 2, 3, 5, 8]
        for n in Fibonacci(20): print(n)

    Must implement __iter__ (return self) and __next__ (raise StopIteration
    when next value would exceed limit).
    """

    def __init__(self, limit: int) -> None:
        # TODO: store limit, initialize a=0, b=1
        raise NotImplementedError

    def __iter__(self) -> Fibonacci:
        # TODO
        raise NotImplementedError

    def __next__(self) -> int:
        # TODO
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 9: Generator with send()
# ---------------------------------------------------------------------------

def running_average() -> Iterator[float]:
    """
    A generator that maintains a running average.

    Usage:
        gen = running_average()
        next(gen)           # prime the generator (returns None / 0.0)
        gen.send(10)        # → 10.0
        gen.send(20)        # → 15.0
        gen.send(30)        # → 20.0

    The generator yields the current average after each value is sent.
    On the first next() call (priming), yield 0.0.
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 10: ContextVar for async request tracing
# ---------------------------------------------------------------------------

trace_id: ContextVar[str] = ContextVar("trace_id", default="none")


async def traced_task(name: str, tid: str) -> str:
    """
    Set trace_id to `tid` for the duration of this coroutine.
    Yield control to the event loop at least once (await asyncio.sleep(0)).
    Return the trace_id value observed after the yield.
    Restore the previous trace_id value before returning.
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# TESTS — run with: python exercises.py
# ---------------------------------------------------------------------------

def test_count_references() -> None:
    x = [1, 2, 3]
    y = x
    assert count_references(x) == 2, f"Expected 2, got {count_references(x)}"
    del y
    assert count_references(x) == 1, f"Expected 1, got {count_references(x)}"
    print("  PASS: count_references")


def test_range_validator() -> None:
    class Temperature:
        celsius = RangeValidator(-273.15, 1_000_000.0)

    t = Temperature()
    t.celsius = 25.0
    assert t.celsius == 25.0

    try:
        t.celsius = -300.0
        assert False, "Should have raised"
    except ValueError:
        pass

    assert isinstance(Temperature.celsius, RangeValidator)
    print("  PASS: RangeValidator descriptor")


def test_cooperative_mixin() -> None:
    cp = CleaningPipeline()
    result = cp.process("  hello world  ")
    assert result == "HELLO WORLD", f"Got {result!r}"
    print("  PASS: cooperative super()")


def test_slots() -> None:
    v = MemoryEfficient(1.0, 2.0, 3.0)
    assert not hasattr(v, "__dict__"), "Should not have __dict__"
    w = MemoryEfficient(4.0, 5.0, 6.0)
    s = v + w
    assert s == MemoryEfficient(5.0, 7.0, 9.0)
    assert {v, v} == {v}  # hashable, deduped in set
    print("  PASS: __slots__")


def test_singleton() -> None:
    a = AppConfig(debug=True)
    b = AppConfig(debug=False)
    assert a is b, "Should be same instance"
    assert a.debug is True, "First init's value should persist"
    assert isinstance(a.settings, dict)
    print("  PASS: Singleton __new__")


def test_weak_cache() -> None:
    class BigObject:
        pass

    cache = WeakCache()
    obj = BigObject()
    cache.set("key", obj)
    assert cache.get("key") is obj
    assert len(cache) == 1

    del obj
    gc.collect()
    assert cache.get("key") is None
    assert len(cache) == 0
    print("  PASS: WeakCache")


def test_fibonacci() -> None:
    assert list(Fibonacci(10)) == [1, 1, 2, 3, 5, 8]
    assert list(Fibonacci(1)) == [1, 1]
    assert list(Fibonacci(0)) == []
    print("  PASS: Fibonacci iterator")


def test_running_average() -> None:
    gen = running_average()
    next(gen)   # prime
    assert gen.send(10) == 10.0
    assert gen.send(20) == 15.0
    assert gen.send(30) == 20.0
    print("  PASS: running_average generator")


async def test_context_vars() -> None:
    results = await asyncio.gather(
        traced_task("A", "trace-aaa"),
        traced_task("B", "trace-bbb"),
        traced_task("C", "trace-ccc"),
    )
    assert results == ["trace-aaa", "trace-bbb", "trace-ccc"], f"Got {results}"
    assert trace_id.get() == "none", "Should be restored to default"
    print("  PASS: ContextVar isolation")


if __name__ == "__main__":
    print("\n=== Module 09 Exercises ===\n")

    tests = [
        test_count_references,
        test_range_validator,
        test_cooperative_mixin,
        test_slots,
        test_singleton,
        test_weak_cache,
        test_fibonacci,
        test_running_average,
    ]

    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except NotImplementedError:
            print(f"  TODO: {test.__name__}")
        except AssertionError as e:
            print(f"  FAIL: {test.__name__} — {e}")

    try:
        asyncio.run(test_context_vars())
        passed += 1
    except NotImplementedError:
        print("  TODO: test_context_vars")
    except AssertionError as e:
        print(f"  FAIL: test_context_vars — {e}")

    total = len(tests) + 1
    print(f"\n{passed}/{total} exercises complete")
