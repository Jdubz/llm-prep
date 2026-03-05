"""
Generators & Iterators Exercises

Lazy evaluation, yield, yield from, deque, and context managers. These
patterns are essential for understanding FastAPI's yield dependencies
and streaming responses.

Run:  python exercises/04-generators-and-iterators.py
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Generator, Iterable, Iterator


# ============================================================================
# EXERCISE 1: Chunked Iterator
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (generators, itertools)
#   - ../../fastapi/03-advanced-api-patterns/02-pagination-filtering-and-bulk-operations.md (batch processing)
#
# Write a generator that yields fixed-size chunks from any iterable.
# This is useful for batch processing (e.g., inserting records in batches).
#
# Requirements:
#   - chunked(iterable, size) yields lists of up to `size` items
#   - The last chunk may be shorter than `size`
#   - Works with any iterable (lists, generators, ranges, etc.)
#   - size must be >= 1 (raise ValueError otherwise)
#
# Hints:
#   - Use itertools.islice to take N items from an iterator
#   - Convert the iterable to an iterator with iter()
#   - Loop: take a chunk with islice, break if empty, yield the chunk
#   - Or: accumulate items in a list, yield when full
#
#   itertools.islice API — slicing for iterators:
#     from itertools import islice
#     islice(iterable, stop)           # first `stop` items
#     islice(iterable, start, stop)    # items from start to stop
#     # Unlike list slicing, islice works with any iterator and is lazy
#
#   Pattern — chunking with islice:
#     def chunked(iterable, size):
#         if size < 1:
#             raise ValueError("size must be >= 1")
#         it = iter(iterable)           # ensure we have an iterator
#         while True:
#             chunk = list(islice(it, size))  # take up to `size` items
#             if not chunk:
#                 break                  # iterator exhausted
#             yield chunk
#
#   Why iter() is needed: islice consumes from an iterator. If you pass
#   a list directly, each islice call would start from the beginning.
#   Calling iter() once gives you a single iterator that remembers its
#   position between islice calls.
#
#   How yield works:
#   - A function with yield becomes a generator function
#   - Calling it returns a generator object (lazy, produces values on demand)
#   - Each yield suspends the function and produces a value
#   - The function resumes on the next next() call (or for-loop iteration)
#
# Expected behavior:
#   list(chunked(range(7), 3))  # -> [[0, 1, 2], [3, 4, 5], [6]]
#   list(chunked([], 5))        # -> []

from itertools import islice


def chunked(iterable: Iterable, size: int) -> Generator[list, None, None]:
    """Yield successive chunks of `size` items from an iterable."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 2: Sliding Window
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (deque, generators)
#   - ../01-async-python/02-concurrency-patterns.md (streaming data patterns)
#
# Write a generator that yields overlapping windows (tuples) over an iterable.
# This is a common pattern for time-series analysis and streaming data.
#
# Requirements:
#   - window(iterable, size) yields tuples of `size` consecutive items
#   - Windows overlap: each window advances by one element
#   - If the iterable has fewer than `size` items, yield nothing
#   - size must be >= 1 (raise ValueError otherwise)
#
# Hints:
#   - Use collections.deque(maxlen=size) as a sliding buffer
#   - Iterate through items, appending to the deque
#   - Once the deque is full (len == size), yield tuple(deque) each step
#
#   collections.deque with maxlen — automatic sliding window:
#     from collections import deque
#     d = deque(maxlen=3)
#     d.append(1)  # deque([1])
#     d.append(2)  # deque([1, 2])
#     d.append(3)  # deque([1, 2, 3])  <- full
#     d.append(4)  # deque([2, 3, 4])  <- oldest item auto-evicted!
#
#   Pattern — sliding window generator:
#     def window(iterable, size):
#         if size < 1:
#             raise ValueError("size must be >= 1")
#         buf = deque(maxlen=size)
#         for item in iterable:
#             buf.append(item)
#             if len(buf) == size:      # buffer is full
#                 yield tuple(buf)      # yield a snapshot as a tuple
#
#   This is memory-efficient: only `size` items in memory at any time.
#   Works with infinite iterables (generators, streams, etc.).
#
# Expected behavior:
#   list(window([1, 2, 3, 4, 5], 3))
#   # -> [(1, 2, 3), (2, 3, 4), (3, 4, 5)]


def window(iterable: Iterable, size: int) -> Generator[tuple, None, None]:
    """Yield overlapping windows of `size` items from an iterable."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 3: Fibonacci Generator
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (generators, infinite sequences)
#   - ../03-python-internals/01-object-model-and-memory.md (lazy evaluation, memory)
#
# Write an infinite Fibonacci generator plus a take(n) helper that
# collects the first N items from any iterator.
#
# Requirements:
#   - fibonacci() is an infinite generator yielding 0, 1, 1, 2, 3, 5, 8, ...
#   - take(n, iterable) returns a list of the first N items
#   - take() works with any iterable, not just fibonacci
#   - take(0, ...) returns []
#
# Hints:
#   - fibonacci: a, b = 0, 1; yield a; a, b = b, a + b in a while True loop
#   - take: use itertools.islice(iterable, n) and convert to list
#
#   Infinite generator pattern:
#     def fibonacci():
#         a, b = 0, 1
#         while True:           # infinite loop — only safe in a generator
#             yield a           # suspend and produce current value
#             a, b = b, a + b  # tuple unpacking: simultaneous assignment
#
#   Python tuple unpacking:
#     a, b = b, a + b
#   is NOT the same as:
#     a = b
#     b = a + b    # BUG: a has already changed!
#   Tuple unpacking evaluates the right side fully before assigning.
#
#   take() using itertools.islice:
#     def take(n, iterable):
#         return list(islice(iterable, n))
#
#   islice is safe with infinite generators — it only consumes n items:
#     take(5, fibonacci())  # [0, 1, 1, 2, 3] — does NOT loop forever
#
# Expected behavior:
#   take(8, fibonacci())  # -> [0, 1, 1, 2, 3, 5, 8, 13]
#   take(0, fibonacci())  # -> []
#   take(3, range(100))   # -> [0, 1, 2]


def fibonacci() -> Generator[int, None, None]:
    """Infinite Fibonacci generator: 0, 1, 1, 2, 3, 5, 8, ..."""
    # TODO: Implement
    raise NotImplementedError()


def take(n: int, iterable: Iterable) -> list:
    """Return the first N items from an iterable as a list."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 4: CSV Line Parser
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (generators, lazy evaluation)
#   - ../../fastapi/03-advanced-api-patterns/01-file-handling-and-streaming.md (streaming patterns)
#
# Write a generator that lazily reads CSV-formatted lines and yields dicts.
# This simulates processing large files without loading everything into memory.
#
# Requirements:
#   - parse_csv(lines) takes an iterable of strings (simulating file lines)
#   - The first line is the header (comma-separated column names)
#   - Subsequent lines are data rows
#   - Yield one dict per row: {column_name: value, ...}
#   - Strip whitespace from headers and values
#   - Skip empty lines
#
# Hints:
#   - Use iter() and next() to read the header line
#   - Split on "," and strip each field
#   - zip(headers, values) to create the dict
#
#   iter() and next() — manual iterator control:
#     it = iter(lines)                    # convert iterable to iterator
#     header_line = next(it, None)        # get first item (None if empty)
#     # remaining items in `it` are the data rows
#     for line in it:                     # continues from where next() left off
#         ...
#
#   next(iterator, default) returns default instead of raising StopIteration
#   when the iterator is empty. Always use the two-argument form when
#   empty input is possible.
#
#   zip() for pairing headers with values:
#     headers = ["name", "age", "city"]
#     values = ["Alice", "30", "NYC"]
#     dict(zip(headers, values))          # {"name": "Alice", "age": "30", ...}
#
#   Pattern — lazy CSV parser:
#     def parse_csv(lines):
#         it = iter(lines)
#         header_line = next(it, None)
#         if header_line is None:
#             return                       # empty input, no header
#         headers = [h.strip() for h in header_line.split(",")]
#         for line in it:
#             if not line.strip():
#                 continue                 # skip empty lines
#             values = [v.strip() for v in line.split(",")]
#             yield dict(zip(headers, values))
#
# Expected behavior:
#   lines = ["name, age, city", "Alice, 30, NYC", "Bob, 25, LA"]
#   list(parse_csv(lines))
#   # -> [{"name": "Alice", "age": "30", "city": "NYC"},
#   #     {"name": "Bob", "age": "25", "city": "LA"}]


def parse_csv(lines: Iterable[str]) -> Generator[dict[str, str], None, None]:
    """Lazily parse CSV-formatted lines into dicts."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 5: Flatten Deeply Nested
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (yield from, recursion)
#   - ../03-python-internals/01-object-model-and-memory.md (Iterable ABC, isinstance)
#
# Write a generator that recursively flattens arbitrarily nested iterables.
# Strings should NOT be flattened (they're iterable but should stay whole).
#
# Requirements:
#   - flatten(data) yields individual non-iterable items
#   - Recursively descends into lists, tuples, sets, generators
#   - Strings are leaf values (don't iterate into characters)
#   - Dicts are leaf values (don't iterate into keys)
#   - Use yield from for recursive calls
#
# Hints:
#   - Check: isinstance(item, Iterable) and not isinstance(item, (str, bytes, dict))
#   - If iterable, yield from flatten(item) (recursive)
#   - Otherwise, yield the item
#
#   yield from — delegating to a sub-generator:
#     yield from some_iterable
#   is equivalent to:
#     for item in some_iterable:
#         yield item
#   but yield from is more efficient and handles generator protocol properly.
#
#   Why strings need special treatment:
#     "hello" is iterable -> 'h', 'e', 'l', 'l', 'o'
#     'h' is also iterable -> 'h' -> 'h' -> ... (infinite recursion!)
#     So always check: not isinstance(item, (str, bytes, dict))
#
#   Using collections.abc.Iterable for type checking:
#     from collections.abc import Iterable
#     isinstance([1, 2], Iterable)    # True
#     isinstance((1, 2), Iterable)    # True
#     isinstance("hello", Iterable)   # True (that's why we exclude it!)
#     isinstance(42, Iterable)        # False
#
#   Pattern — recursive flatten with yield from:
#     def flatten(data):
#         for item in data:
#             if isinstance(item, IterableABC) and not isinstance(item, (str, bytes, dict)):
#                 yield from flatten(item)   # recurse into nested iterables
#             else:
#                 yield item                 # leaf value, emit it
#
# Expected behavior:
#   list(flatten([1, [2, [3, 4], 5], [6]]))      # -> [1, 2, 3, 4, 5, 6]
#   list(flatten([1, "hello", [2, "world"]]))      # -> [1, "hello", 2, "world"]
#   list(flatten([[1, 2], (3, 4), {5, 6}]))        # -> [1, 2, 3, 4, 5, 6]

from collections.abc import Iterable as IterableABC


def flatten(data: Iterable) -> Generator:
    """Recursively flatten nested iterables (strings stay whole)."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 6: Timed Context Manager
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (context managers)
#   - ../03-python-internals/01-object-model-and-memory.md (__enter__, __exit__)
#   - ../01-async-python/01-asyncio-fundamentals.md (async context managers)
#
# Implement a Timer context manager that measures elapsed time.
# Support nested timers that track their own independent durations.
#
# Requirements:
#   - Use as: with Timer("label") as t:
#   - After the block, t.elapsed contains the duration in seconds
#   - t.label stores the label string
#   - __enter__ returns self, __exit__ computes elapsed time
#   - __repr__: Timer('label': 0.123s) (3 decimal places)
#   - Works with nested timers (each tracks independently)
#
# Hints:
#   - Use time.perf_counter() for high-resolution timing
#   - Store start time in __enter__, compute elapsed in __exit__
#   - __exit__ receives (exc_type, exc_val, exc_tb) — return False to
#     propagate exceptions
#
#   Context manager protocol — __enter__ and __exit__:
#
#     class Timer:
#         def __enter__(self) -> Timer:
#             self._start = time.perf_counter()
#             return self              # the `as t` in `with Timer() as t`
#
#         def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
#             self.elapsed = time.perf_counter() - self._start
#             return False             # False = propagate exceptions
#                                      # True = suppress exceptions
#
#   __exit__ parameters:
#   - exc_type: exception class (e.g., ValueError), or None if no exception
#   - exc_val: exception instance, or None
#   - exc_tb: traceback, or None
#   - Return False (or None) to let exceptions propagate normally
#
#   time.perf_counter() vs time.monotonic():
#   - perf_counter: highest resolution timer, includes sleep time
#   - monotonic: lower resolution, but guaranteed to never go backwards
#   - For benchmarking and profiling, perf_counter is preferred
#
#   f-string formatting for decimal places:
#     f"{value:.3f}"    # 3 decimal places: "0.100"
#     f"Timer('{self.label}': {self.elapsed:.3f}s)"
#
# Expected behavior:
#   with Timer("sleep") as t:
#       time.sleep(0.1)
#   t.elapsed  # ~0.1
#   print(t)   # Timer('sleep': 0.100s)


class Timer:
    """Context manager that measures elapsed time."""

    def __init__(self, label: str = "default") -> None:
        # TODO: Store label, initialize elapsed
        raise NotImplementedError()

    def __enter__(self) -> Timer:
        # TODO: Record start time, return self
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        # TODO: Compute elapsed time, return False
        raise NotImplementedError()

    def __repr__(self) -> str:
        # TODO: Return Timer('label': 0.123s) format
        raise NotImplementedError()


# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

def test_chunked():
    print("\n=== EXERCISE 1: Chunked Iterator ===")
    assert list(chunked(range(7), 3)) == [[0, 1, 2], [3, 4, 5], [6]]
    assert list(chunked(range(6), 3)) == [[0, 1, 2], [3, 4, 5]]
    assert list(chunked([], 5)) == []
    assert list(chunked([1], 5)) == [[1]]
    print("All cases passed")

    # Works with generators
    gen = (x for x in range(5))
    assert list(chunked(gen, 2)) == [[0, 1], [2, 3], [4]]
    print("Generator input works")

    try:
        list(chunked([1], 0))
        print("ERROR: Should have raised ValueError")
    except ValueError:
        print("Invalid size rejected (expected)")
    print("EXERCISE 1: PASSED")


def test_window():
    print("\n=== EXERCISE 2: Sliding Window ===")
    result = list(window([1, 2, 3, 4, 5], 3))
    assert result == [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
    print(f"Windows: {result}")

    assert list(window([1, 2], 3)) == []
    assert list(window([1, 2, 3], 3)) == [(1, 2, 3)]
    assert list(window([1, 2, 3], 1)) == [(1,), (2,), (3,)]
    print("Edge cases passed")

    try:
        list(window([1], 0))
        print("ERROR: Should have raised ValueError")
    except ValueError:
        print("Invalid size rejected (expected)")
    print("EXERCISE 2: PASSED")


def test_fibonacci():
    print("\n=== EXERCISE 3: Fibonacci ===")
    assert take(8, fibonacci()) == [0, 1, 1, 2, 3, 5, 8, 13]
    assert take(1, fibonacci()) == [0]
    assert take(0, fibonacci()) == []
    print(f"First 8: {take(8, fibonacci())}")

    # take works with any iterable
    assert take(3, range(100)) == [0, 1, 2]
    assert take(5, "abcdef") == ["a", "b", "c", "d", "e"]
    print("take() works with other iterables")
    print("EXERCISE 3: PASSED")


def test_csv_parser():
    print("\n=== EXERCISE 4: CSV Parser ===")
    lines = ["name, age, city", "Alice, 30, NYC", "Bob, 25, LA", ""]
    result = list(parse_csv(lines))
    assert result == [
        {"name": "Alice", "age": "30", "city": "NYC"},
        {"name": "Bob", "age": "25", "city": "LA"},
    ]
    print(f"Parsed {len(result)} rows")

    # Empty input (header only)
    assert list(parse_csv(["name, age"])) == []

    # No lines at all
    assert list(parse_csv([])) == []
    print("Edge cases passed")
    print("EXERCISE 4: PASSED")


def test_flatten():
    print("\n=== EXERCISE 5: Flatten ===")
    assert list(flatten([1, [2, [3, 4], 5], [6]])) == [1, 2, 3, 4, 5, 6]
    assert list(flatten([1, "hello", [2, "world"]])) == [1, "hello", 2, "world"]
    assert list(flatten([])) == []
    assert list(flatten([1, 2, 3])) == [1, 2, 3]
    print("Basic and string cases passed")

    # Mixed types
    result = list(flatten([[1, 2], (3, 4)]))
    assert result == [1, 2, 3, 4]

    # Deeply nested
    assert list(flatten([[[[[1]]]]])) == [1]
    print("Deep nesting passed")
    print("EXERCISE 5: PASSED")


def test_timer():
    print("\n=== EXERCISE 6: Timer ===")
    with Timer("test") as t:
        time.sleep(0.05)

    assert t.elapsed >= 0.04  # allow some slack
    assert t.label == "test"
    print(f"Timer: {t}")

    # Nested timers
    with Timer("outer") as outer:
        time.sleep(0.02)
        with Timer("inner") as inner:
            time.sleep(0.02)

    assert inner.elapsed < outer.elapsed
    print(f"Outer: {outer}, Inner: {inner}")
    print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    print("Generators & Iterators Exercises")
    print("=" * 60)

    tests = [
        ("Exercise 1: Chunked Iterator", test_chunked),
        ("Exercise 2: Sliding Window", test_window),
        ("Exercise 3: Fibonacci Generator", test_fibonacci),
        ("Exercise 4: CSV Line Parser", test_csv_parser),
        ("Exercise 5: Flatten Deeply Nested", test_flatten),
        ("Exercise 6: Timed Context Manager", test_timer),
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
