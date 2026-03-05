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
# READ FIRST: 01-object-model-and-memory.md → "Memory Management: Reference Counting + Cyclic GC"
# ALSO SEE:  examples.py → demo_refcounting() (section 1)

def count_references(obj: Any) -> int:
    """
    Return the number of references to `obj` NOT counting:
      - the reference held by this function's `obj` parameter
      - the reference held by sys.getrefcount's argument

    Background:
      sys.getrefcount(x) returns the actual reference count of x, BUT it
      always adds +1 because passing x as an argument to getrefcount creates
      a temporary reference. So if x has 2 "real" references:
        sys.getrefcount(x) → 3  (2 real + 1 for the argument itself)

      When the caller writes count_references(x), that creates ANOTHER
      temporary reference (the `obj` parameter in this function). So inside
      this function, sys.getrefcount(obj) includes TWO extra refs we need
      to subtract:
        1. The `obj` parameter of count_references
        2. The argument to sys.getrefcount

      Therefore: real_count = sys.getrefcount(obj) - 2
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 2: Detect Reference Cycle
# ---------------------------------------------------------------------------
# READ FIRST: 01-object-model-and-memory.md → "Cyclic GC (Secondary)"
# ALSO SEE:  examples.py → demo_reference_cycle() (section 1)

def has_reference_cycle(*objects: Any) -> bool:
    """
    Return True if any of the given objects are part of a reference cycle
    (i.e., the cyclic GC tracks them as unreachable after removing external refs).

    Strategy:
      - Temporarily disable the GC
      - Delete external references
      - Run gc.collect() and check if it found anything
      - Restore GC state

    Background:
      gc.collect() forces a full garbage collection and returns the number of
      unreachable objects it found and freed. By default, CPython's cyclic GC
      runs automatically based on allocation thresholds (gc.get_threshold()).

      gc.get_referrers(obj) returns a list of all objects that reference obj.
      This is useful for debugging reference leaks.

      To detect a cycle:
        1. Use gc.collect() to clear any existing garbage first
        2. Check gc.get_referrers() for each object — if any referrer is also
           in the objects set, there's a cycle among them
        3. Alternatively, check if any object refers to another in the group
           using gc.get_referents(obj), which returns all objects that obj
           directly references

      A simpler approach: check if any object in the group is referenced by
      another object in the group (mutual references = cycle).
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 3: Descriptor — Range Validator
# ---------------------------------------------------------------------------
# READ FIRST: 02-advanced-python-features.md → "Descriptors: How property, classmethod, staticmethod Work"
# ALSO SEE:  examples.py → class Positive / demo_descriptors() (section 3)

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

    Background — The Descriptor Protocol:
      A data descriptor defines both __get__ and __set__. The three methods are:

      __set_name__(self, owner: type, name: str) -> None
        Called automatically when the descriptor is assigned to a class attribute.
        `owner` is the class being defined (e.g., Temperature).
        `name` is the attribute name (e.g., "celsius").
        Use this to store a private attribute name like f"_{name}".

      __get__(self, obj, objtype=None) -> Any
        Called when the attribute is accessed.
        If obj is None, the attribute was accessed on the class itself
        (e.g., Temperature.celsius) — convention is to return `self` (the
        descriptor object).
        If obj is an instance, return the stored value from the instance
        using getattr(obj, self._attr_name).

      __set__(self, obj, value) -> None
        Called when the attribute is assigned on an instance.
        Validate `value`, then store it on the instance using
        setattr(obj, self._attr_name, value).

      Data descriptors take priority over instance __dict__ in attribute
      lookup. See 02-advanced-python-features.md for the full lookup order.
    """

    def __init__(self, min_val: float, max_val: float) -> None:
        # TODO: store min_val, max_val
        raise NotImplementedError

    def __set_name__(self, owner: type, name: str) -> None:
        # TODO: store the private attribute name as self._attr = f"_{name}"
        raise NotImplementedError

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        # TODO: if obj is None, return self; otherwise return getattr(obj, self._attr)
        raise NotImplementedError

    def __set__(self, obj: Any, value: float) -> None:
        # TODO: check min_val <= value <= max_val, raise ValueError if not, then setattr
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 4: Cooperative Mixin via super()
# ---------------------------------------------------------------------------
# READ FIRST: 02-advanced-python-features.md → "MRO and super()"
# ALSO SEE:  examples.py → demo_mro() (section 4)

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
    Background — C3 Linearization and super():
      Python computes the MRO using C3 linearization, which guarantees:
        - Children come before parents
        - Left-to-right order from the class definition is preserved
        - A consistent ordering exists (or Python raises TypeError)

      super() does NOT mean "call the parent class." It means "call the next
      class in the MRO of the *concrete instance's* class, starting after the
      class containing this super() call."

      You can inspect the MRO with: CleaningPipeline.__mro__

    MRO: CleaningPipeline -> UpperMixin -> StripMixin -> Pipeline -> object

    Trace the calls:
      1. CleaningPipeline.process("  hello  ") → dispatches to UpperMixin.process
         (first in MRO after CleaningPipeline that defines process)
      2. UpperMixin.process uppercases → "  HELLO  ", then calls super().process()
         super() in UpperMixin → next in MRO → StripMixin
      3. StripMixin.process strips → "HELLO", then calls super().process()
         super() in StripMixin → next in MRO → Pipeline
      4. Pipeline.process returns data unchanged → "HELLO"

    So the order is: Upper → Strip → Pipeline.
    Input "  hello  " → "  HELLO  " → "HELLO"
    """
    pass


# ---------------------------------------------------------------------------
# Exercise 5: __slots__ — MemoryEfficient class
# ---------------------------------------------------------------------------
# READ FIRST: 01-object-model-and-memory.md → "__slots__"
# ALSO SEE:  examples.py → class Slotted / demo_slots() (section 5)

class MemoryEfficient:
    """
    A class representing a 3D vector with x, y, z components.
    Use __slots__ to minimize memory per instance.
    Implement __add__ (component-wise) and __eq__.

    Background:
      __slots__ replaces the per-instance __dict__ with fixed C-level memory
      offsets. Define it as a tuple of attribute name strings:
        __slots__ = ("x", "y", "z")

      Effects:
        - No __dict__ on instances (~200 bytes saved per instance)
        - AttributeError if you try to set an attribute not in __slots__
        - Instances are not weakly referenceable unless "__weakref__" is in __slots__
        - The test checks hasattr(v, "__dict__") == False

      You must also define __hash__ when you define __eq__, otherwise
      Python sets __hash__ = None and the object becomes unhashable.
      See 01-object-model-and-memory.md → "Dunder Protocols" for details.
    """
    __slots__: tuple[str, ...]  # TODO: define slots as ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float) -> None:
        # TODO: set self.x, self.y, self.z
        raise NotImplementedError

    def __add__(self, other: MemoryEfficient) -> MemoryEfficient:
        # TODO: return new MemoryEfficient(self.x + other.x, ...)
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        # TODO: check isinstance(other, MemoryEfficient), compare (x,y,z) tuples
        raise NotImplementedError

    def __hash__(self) -> int:
        # TODO: return hash((self.x, self.y, self.z))
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 6: Singleton via __new__
# ---------------------------------------------------------------------------
# READ FIRST: 01-object-model-and-memory.md → "__new__ vs __init__"
# ALSO SEE:  examples.py → class DatabasePool / demo_new_vs_init() (section 8)

class AppConfig:
    """
    A singleton configuration class.
    Only one instance should ever exist.
    __init__ should only run on the first instantiation (use a _initialized flag).

    Attributes set on first init: settings (empty dict), debug (bool from arg).
    Subsequent instantiations return the same object without re-initializing.

    Background — __new__ vs __init__:
      When you call MyClass(args), Python does:
        1. instance = MyClass.__new__(MyClass, args)   # creates the object
        2. if isinstance(instance, MyClass):
               instance.__init__(args)                 # initializes it

      __new__ is a static method (implicitly) that receives the class as its
      first argument and must return an instance. It calls
      super().__new__(cls) to actually allocate the object.

      __init__ receives the already-created instance (self) and sets up its
      state. It runs EVERY time the class is called, even if __new__
      returned a cached instance.

      For a singleton:
        - __new__ checks if cls._instance exists; if not, creates it
        - __init__ checks a _initialized flag to avoid resetting state
        - The test asserts: AppConfig(True) is AppConfig(False) → True
          and that debug remains True (from the first call)
    """
    _instance: AppConfig | None = None

    def __new__(cls, debug: bool = False) -> AppConfig:
        # TODO: if cls._instance is None, create via super().__new__(cls) and store it
        # Return cls._instance
        raise NotImplementedError

    def __init__(self, debug: bool = False) -> None:
        # TODO: if already initialized (check _initialized flag), return early
        # Otherwise, set _initialized = True, settings = {}, debug = debug
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 7: Weak Reference Cache
# ---------------------------------------------------------------------------
# READ FIRST: 01-object-model-and-memory.md → "Weak References"
# ALSO SEE:  examples.py → demo_weak_references() (section 7)

class WeakCache:
    """
    A cache that holds weak references to its values.
    When a value is garbage collected, its key is automatically removed.

    Methods:
        set(key, value): store value with weak reference
        get(key, default=None): retrieve value, or default if gone/missing
        __len__: number of live entries

    Background — Weak References:
      weakref.ref(obj) creates a weak reference. Calling the ref returns the
      object if it's still alive, or None if it's been garbage collected.
      Weak references do NOT increment the reference count.

      weakref.WeakValueDictionary() is a dict whose values are weak
      references. When a value is garbage collected, its key-value pair is
      automatically removed from the dict. API:
        wvd = weakref.WeakValueDictionary()
        wvd["key"] = obj          # stores a weak ref to obj
        wvd["key"]                # returns obj (or raises KeyError if collected)
        wvd.get("key", default)   # returns obj or default
        len(wvd)                  # number of live entries

      Note: you can only create weak references to objects that support them.
      Most user-defined class instances support weak refs. Built-in types
      like int, str, list, dict do NOT (the test uses a custom BigObject class).

      The test flow:
        1. Create a BigObject, store in cache
        2. Verify it's retrievable
        3. Delete the strong reference (del obj), force gc.collect()
        4. Verify cache.get() returns None and len(cache) == 0
    """

    def __init__(self) -> None:
        # TODO: self._store = weakref.WeakValueDictionary()
        raise NotImplementedError

    def set(self, key: str, value: Any) -> None:
        # TODO: self._store[key] = value
        raise NotImplementedError

    def get(self, key: str, default: Any = None) -> Any:
        # TODO: return self._store.get(key, default)
        raise NotImplementedError

    def __len__(self) -> int:
        # TODO: return len(self._store)
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 8: Custom Iterator Protocol
# ---------------------------------------------------------------------------
# READ FIRST: 01-object-model-and-memory.md → "Dunder Protocols" (iterator row)
#             03-imports-and-runtime.md → "The Generator Protocol in Detail"
# ALSO SEE:  examples.py → demo_hash_rule() (section 10, for dunder protocol patterns)

class Fibonacci:
    """
    An iterator that yields Fibonacci numbers up to a limit.

    Usage:
        list(Fibonacci(10))   # [1, 1, 2, 3, 5, 8]
        for n in Fibonacci(20): print(n)

    Must implement __iter__ (return self) and __next__ (raise StopIteration
    when next value would exceed limit).

    Background — The Iterator Protocol:
      Python's for loop calls iter(obj), which calls obj.__iter__().
      Then it repeatedly calls next(iterator), which calls iterator.__next__().
      When __next__ raises StopIteration, the loop ends.

      For a class-based iterator (not a generator), you need:
        __iter__(self) → return self  (the iterator IS the iterable)
        __next__(self) → return the next value, or raise StopIteration

      Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13, ...
      Each number is the sum of the two preceding ones.
      Track state with two variables: a (previous) and b (current).
      Start with a=0, b=1. Each step: yield b, then (a, b) = (b, a+b).
      Stop when b > limit (raise StopIteration).

      The test expects:
        Fibonacci(10)  → [1, 1, 2, 3, 5, 8]
        Fibonacci(1)   → [1, 1]
        Fibonacci(0)   → []
    """

    def __init__(self, limit: int) -> None:
        # TODO: store limit, initialize a=0, b=1
        raise NotImplementedError

    def __iter__(self) -> Fibonacci:
        # TODO: return self
        raise NotImplementedError

    def __next__(self) -> int:
        # TODO: if self.b > self.limit, raise StopIteration
        # Otherwise, save self.b as the value to return,
        # advance: self.a, self.b = self.b, self.a + self.b
        # return the saved value
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 9: Generator with send()
# ---------------------------------------------------------------------------
# READ FIRST: 03-imports-and-runtime.md → "The Generator Protocol in Detail"
# ALSO SEE:  examples.py → (no direct demo, but see section 9 for context vars
#             which also uses async generators; the generator protocol section
#             in 03-imports-and-runtime.md has full send/throw/close examples)

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

    Background — Generator .send(), .throw(), .close():
      Generators support three methods beyond __next__:

      .send(value) → resumes the generator and makes `value` the result of
        the yield expression where the generator is suspended. The generator
        runs until the next yield and returns that yielded value.
        The first call must be next(gen) or gen.send(None) to "prime" the
        generator (advance it to the first yield).

      .throw(exc_type) → resumes and raises the exception at the yield point.
        Used by asyncio for task.cancel() → throws CancelledError.

      .close() → throws GeneratorExit at the yield point for cleanup.

      Pattern for a generator that receives values:
        def my_gen():
            total = 0
            count = 0
            value = yield 0.0        # first yield: priming, returns 0.0
            while True:              # then loop forever receiving values
                total += value
                count += 1
                value = yield total / count  # yield result, receive next value

      The key insight: `value = yield result` does two things:
        1. Yields `result` OUT to the caller
        2. When resumed via .send(x), assigns x to `value`
    """
    # TODO: implement
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Exercise 10: ContextVar for async request tracing
# ---------------------------------------------------------------------------
# READ FIRST: 02-advanced-python-features.md → "Context Variables (PEP 567): async-safe Thread Locals"
# ALSO SEE:  examples.py → demo_context_vars() (section 9)

trace_id: ContextVar[str] = ContextVar("trace_id", default="none")


async def traced_task(name: str, tid: str) -> str:
    """
    Set trace_id to `tid` for the duration of this coroutine.
    Yield control to the event loop at least once (await asyncio.sleep(0)).
    Return the trace_id value observed after the yield.
    Restore the previous trace_id value before returning.

    Background — contextvars.ContextVar API:
      ContextVar provides per-task (not per-thread) state for async code.

      Creation:
        trace_id: ContextVar[str] = ContextVar("trace_id", default="none")

      .set(value) → Token
        Sets the variable's value for the current context. Returns a Token
        object that can be used to restore the previous value.

      .get(default=...) → value
        Returns the current value. If not set and no default was provided
        at creation time, raises LookupError.

      .reset(token)
        Restores the variable to its previous value using the Token from .set().
        This is important for cleanup — without it, the value leaks into
        subsequent code running in the same context.

      asyncio.create_task() copies the current context, so each task has
      its own isolated copy. Setting a ContextVar in one task does not
      affect other concurrent tasks.

      Pattern:
        token = trace_id.set(tid)
        try:
            await asyncio.sleep(0)     # yield to event loop
            result = trace_id.get()    # still sees OUR value
        finally:
            trace_id.reset(token)      # restore previous value
        return result

      The test runs three tasks concurrently with asyncio.gather() and
      verifies each task sees only its own trace_id value.
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
