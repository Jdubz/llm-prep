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

# def test_chunked():
#     print("\n=== EXERCISE 1: Chunked Iterator ===")
#     assert list(chunked(range(7), 3)) == [[0, 1, 2], [3, 4, 5], [6]]
#     assert list(chunked(range(6), 3)) == [[0, 1, 2], [3, 4, 5]]
#     assert list(chunked([], 5)) == []
#     assert list(chunked([1], 5)) == [[1]]
#     print("All cases passed")
#
#     # Works with generators
#     gen = (x for x in range(5))
#     assert list(chunked(gen, 2)) == [[0, 1], [2, 3], [4]]
#     print("Generator input works")
#
#     try:
#         list(chunked([1], 0))
#         print("ERROR: Should have raised ValueError")
#     except ValueError:
#         print("Invalid size rejected (expected)")
#     print("EXERCISE 1: PASSED")
#
#
# def test_window():
#     print("\n=== EXERCISE 2: Sliding Window ===")
#     result = list(window([1, 2, 3, 4, 5], 3))
#     assert result == [(1, 2, 3), (2, 3, 4), (3, 4, 5)]
#     print(f"Windows: {result}")
#
#     assert list(window([1, 2], 3)) == []
#     assert list(window([1, 2, 3], 3)) == [(1, 2, 3)]
#     assert list(window([1, 2, 3], 1)) == [(1,), (2,), (3,)]
#     print("Edge cases passed")
#
#     try:
#         list(window([1], 0))
#         print("ERROR: Should have raised ValueError")
#     except ValueError:
#         print("Invalid size rejected (expected)")
#     print("EXERCISE 2: PASSED")
#
#
# def test_fibonacci():
#     print("\n=== EXERCISE 3: Fibonacci ===")
#     assert take(8, fibonacci()) == [0, 1, 1, 2, 3, 5, 8, 13]
#     assert take(1, fibonacci()) == [0]
#     assert take(0, fibonacci()) == []
#     print(f"First 8: {take(8, fibonacci())}")
#
#     # take works with any iterable
#     assert take(3, range(100)) == [0, 1, 2]
#     assert take(5, "abcdef") == ["a", "b", "c", "d", "e"]
#     print("take() works with other iterables")
#     print("EXERCISE 3: PASSED")
#
#
# def test_csv_parser():
#     print("\n=== EXERCISE 4: CSV Parser ===")
#     lines = ["name, age, city", "Alice, 30, NYC", "Bob, 25, LA", ""]
#     result = list(parse_csv(lines))
#     assert result == [
#         {"name": "Alice", "age": "30", "city": "NYC"},
#         {"name": "Bob", "age": "25", "city": "LA"},
#     ]
#     print(f"Parsed {len(result)} rows")
#
#     # Empty input (header only)
#     assert list(parse_csv(["name, age"])) == []
#
#     # No lines at all
#     assert list(parse_csv([])) == []
#     print("Edge cases passed")
#     print("EXERCISE 4: PASSED")
#
#
# def test_flatten():
#     print("\n=== EXERCISE 5: Flatten ===")
#     assert list(flatten([1, [2, [3, 4], 5], [6]])) == [1, 2, 3, 4, 5, 6]
#     assert list(flatten([1, "hello", [2, "world"]])) == [1, "hello", 2, "world"]
#     assert list(flatten([])) == []
#     assert list(flatten([1, 2, 3])) == [1, 2, 3]
#     print("Basic and string cases passed")
#
#     # Mixed types
#     result = list(flatten([[1, 2], (3, 4)]))
#     assert result == [1, 2, 3, 4]
#
#     # Deeply nested
#     assert list(flatten([[[[[1]]]]])) == [1]
#     print("Deep nesting passed")
#     print("EXERCISE 5: PASSED")
#
#
# def test_timer():
#     print("\n=== EXERCISE 6: Timer ===")
#     with Timer("test") as t:
#         time.sleep(0.05)
#
#     assert t.elapsed >= 0.04  # allow some slack
#     assert t.label == "test"
#     print(f"Timer: {t}")
#
#     # Nested timers
#     with Timer("outer") as outer:
#         time.sleep(0.02)
#         with Timer("inner") as inner:
#             time.sleep(0.02)
#
#     assert inner.elapsed < outer.elapsed
#     print(f"Outer: {outer}, Inner: {inner}")
#     print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    exercises = [
        ("1 - Chunked Iterator", lambda: list(chunked([1, 2, 3], 2))),
        ("2 - Sliding Window", lambda: list(window([1, 2, 3], 2))),
        ("3 - Fibonacci Generator", lambda: take(5, fibonacci())),
        ("4 - CSV Line Parser", lambda: list(parse_csv(["a,b", "1,2"]))),
        ("5 - Flatten Deeply Nested", lambda: list(flatten([1, [2]]))),
        ("6 - Timed Context Manager", lambda: Timer("test")),
    ]

    print("Generators & Iterators Exercises")
    print("=" * 40)

    for name, factory in exercises:
        try:
            factory()
            print(f"  {name}: IMPLEMENTED")
        except NotImplementedError:
            print(f"  {name}: not implemented")

    # Uncomment below (and the test functions above) to run full tests:
    # print()
    # test_chunked()
    # test_window()
    # test_fibonacci()
    # test_csv_parser()
    # test_flatten()
    # test_timer()
    # print("\n=== ALL EXERCISES PASSED ===")
