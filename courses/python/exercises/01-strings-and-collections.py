"""
Strings & Collections Exercises

Warm-up exercises covering dicts, sorting, comprehensions, and recursion.
These are the bread-and-butter data structure problems that show up in
every Python coding screen.

Run:  python exercises/01-strings-and-collections.py
"""

from __future__ import annotations

from collections import Counter, defaultdict


# ============================================================================
# EXERCISE 1: Group Anagrams
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (data structures)
#   - ../04-interview-prep/01-interview-fundamentals.md (common coding patterns)
#
# Given a list of strings, group anagrams together. Two strings are anagrams
# if they contain the same characters in any order.
#
# Requirements:
#   - Return a list of lists, where each inner list contains anagrams
#   - Order within groups doesn't matter
#   - Order of groups doesn't matter
#   - Empty strings are anagrams of each other
#
# Hints:
#   - Anagrams have the same sorted characters: sorted("eat") == sorted("tea")
#   - Use a dict mapping sorted-character tuples to lists of words
#   - tuple(sorted(word)) makes a hashable dict key
#
#   Pattern — using defaultdict to group by a derived key:
#     from collections import defaultdict
#     groups = defaultdict(list)
#     for word in words:
#         key = tuple(sorted(word))   # "eat" -> ('a', 'e', 't')
#         groups[key].append(word)
#     return list(groups.values())
#
#   Key concepts:
#   - sorted(str) returns a list of characters in alphabetical order
#   - tuple() makes it hashable so it can be a dict key
#   - defaultdict(list) auto-creates an empty list for new keys
#
# Expected behavior:
#   group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
#   # -> [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]


def group_anagrams(words: list[str]) -> list[list[str]]:
    """Group anagrams from a list of strings."""
    anagramGroups: dict[tuple, list[str]] = defaultdict(list)
    for word in words:
        key = tuple(sorted(word))
        anagramGroups[key].append(word)

    return list(anagramGroups.values())


# ============================================================================
# EXERCISE 2: Flatten Nested Dict
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (recursion, dict patterns)
#   - ../04-interview-prep/01-interview-fundamentals.md (data transformation)
#
# Convert a nested dictionary into a flat dictionary with dot-separated keys.
#
# Requirements:
#   - Nested dicts become dot-separated keys: {"a": {"b": 1}} -> {"a.b": 1}
#   - Non-dict values are leaf nodes and should be preserved as-is
#   - Handle arbitrary nesting depth
#   - Empty nested dicts can be ignored
#
# Hints:
#   - Use recursion: if a value is a dict, recurse with the current prefix
#   - Build the key with f"{prefix}.{key}" (or just key if no prefix yet)
#   - A helper function with a prefix parameter keeps the signature clean
#
#   Pattern — recursive dict flattening:
#     def flatten_dict(nested, prefix="", sep="."):
#         result = {}
#         for key, value in nested.items():
#             new_key = f"{prefix}{sep}{key}" if prefix else key
#             if isinstance(value, dict):
#                 result.update(flatten_dict(value, new_key, sep))
#             else:
#                 result[new_key] = value
#         return result
#
#   Key concepts:
#   - isinstance(value, dict) checks if we should recurse deeper
#   - The prefix parameter accumulates the dot-separated path
#   - dict.update() merges the recursively-flattened sub-dict into result
#
# Expected behavior:
#   flatten_dict({"a": {"b": 1, "c": {"d": 2}}, "e": 3})
#   # -> {"a.b": 1, "a.c.d": 2, "e": 3}


def flatten_dict(nested: dict, prefix: str = "", sep: str = ".") -> dict:
    """Flatten a nested dictionary into dot-separated keys."""
    result = {}
    for key, value in nested.items():
        new_key = f"{prefix}{sep}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, new_key, sep))
        else:
            result[new_key] = value

    return result



# ============================================================================
# EXERCISE 3: Most Frequent Words
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (collections module)
#   - ../04-interview-prep/01-interview-fundamentals.md (string manipulation)
#
# Given a string of text, return the N most frequent words (case-insensitive).
#
# Requirements:
#   - Words are split on whitespace
#   - Comparison is case-insensitive (convert to lowercase)
#   - Strip punctuation from word boundaries (leading/trailing only)
#   - Return a list of (word, count) tuples, most frequent first
#   - If N is larger than the number of unique words, return all words
#
# Hints:
#   - str.lower() and str.strip(".,!?;:\"'()") for normalization
#   - collections.Counter has a .most_common(n) method
#   - Filter out empty strings after stripping
#
#   Useful str methods:
#   - "Hello World".split()        -> ["Hello", "World"]  (splits on whitespace)
#   - "Hello".lower()              -> "hello"
#   - "hello!".strip(".,!?;:\"'()") -> "hello" (strips leading/trailing punctuation)
#
#   Counter API:
#     from collections import Counter
#     counter = Counter(["a", "b", "a", "c", "a", "b"])
#     counter.most_common(2)       -> [("a", 3), ("b", 2)]
#     counter.most_common()        -> all items sorted by frequency
#
#   Pattern — word frequency counting:
#     words = [w.strip(".,!?;:\"'()").lower() for w in text.split()]
#     words = [w for w in words if w]   # filter empty strings
#     return Counter(words).most_common(n)
#
# Expected behavior:
#   most_frequent("the cat sat on the mat the cat", n=2)
#   # -> [("the", 3), ("cat", 2)]


def most_frequent(text: str, n: int = 3) -> list[tuple[str, int]]:
    """Return the N most frequent words in text."""
    words = [w.strip(".,!?;:\"'()").lower() for w in text.split()]
    words = [w for w in words if w]

    return Counter(words).most_common(n)


# ============================================================================
# EXERCISE 4: Merge Intervals
# ============================================================================
#
# RELATED READING:
#   - ../04-interview-prep/01-interview-fundamentals.md (classic algorithm patterns)
#   - ../03-python-internals/02-advanced-python-features.md (sorting, tuples)
#
# Given a list of intervals as (start, end) tuples, merge all overlapping
# intervals and return the result sorted by start time.
#
# Requirements:
#   - Two intervals overlap if one starts before or when the other ends
#   - Merge overlapping intervals into a single (min_start, max_end) interval
#   - Return sorted by start time
#   - Handle empty input (return empty list)
#   - Intervals are inclusive: (1, 3) and (3, 5) overlap -> (1, 5)
#
# Hints:
#   - Sort intervals by start time first
#   - Iterate through sorted intervals, merging with the last result
#   - If current.start <= last_merged.end, extend last_merged
#   - Otherwise, start a new merged interval
#
#   Key sorting functions:
#   - sorted(intervals) sorts tuples lexicographically (by first element, then second)
#   - sorted(items, key=lambda x: x[0]) explicitly sorts by first element
#
#   Pattern — merge overlapping intervals:
#     sorted_intervals = sorted(intervals)
#     merged = [sorted_intervals[0]]      # start with first interval
#     for start, end in sorted_intervals[1:]:
#         last_start, last_end = merged[-1]
#         if start <= last_end:            # overlapping
#             merged[-1] = (last_start, max(last_end, end))
#         else:
#             merged.append((start, end))  # non-overlapping, add new
#     return merged
#
#   Key insight: after sorting by start, you only need to check whether
#   each interval overlaps with the last merged interval (greedy approach).
#
# Expected behavior:
#   merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)])
#   # -> [(1, 6), (8, 10), (15, 18)]


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals)
    merged = [sorted_intervals[0]]
    for start, end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


# ============================================================================
# EXERCISE 5: Inverted Index
# ============================================================================
#
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (collections module)
#   - ../04-interview-prep/01-interview-fundamentals.md (data structure design)
#
# Build an inverted index from a list of (doc_id, text) pairs. An inverted
# index maps each word to the set of document IDs that contain it.
#
# Requirements:
#   - Words are split on whitespace, lowercased
#   - Each word maps to a set of doc_ids
#   - Strip punctuation from word boundaries
#   - Return a dict[str, set[int]]
#
# Hints:
#   - Use collections.defaultdict(set)
#   - Iterate through each document, split text into words
#   - For each word, add the doc_id to that word's set
#
#   defaultdict API:
#     from collections import defaultdict
#     index = defaultdict(set)      # missing keys auto-create empty sets
#     index["word"].add(1)          # no KeyError, creates set then adds
#     index["word"].add(2)
#     # index["word"] == {1, 2}
#
#   set operations you may find useful:
#     s.add(item)                   # add a single element
#     s1 & s2                       # intersection (docs containing both words)
#     s1 | s2                       # union (docs containing either word)
#
#   Pattern — building the index:
#     index = defaultdict(set)
#     for doc_id, text in documents:
#         for word in text.lower().split():
#             word = word.strip(".,!?;:\"'()")
#             if word:
#                 index[word].add(doc_id)
#     return dict(index)
#
# Expected behavior:
#   docs = [(1, "the cat sat"), (2, "the dog sat"), (3, "the cat played")]
#   index = build_inverted_index(docs)
#   index["cat"]  # -> {1, 3}
#   index["sat"]  # -> {1, 2}
#   index["the"]  # -> {1, 2, 3}


def build_inverted_index(documents: list[tuple[int, str]]) -> dict[str, set[int]]:
    """Build an inverted index mapping words to document IDs."""
    index = defaultdict(set)
    for id, text in documents:
        words = text.strip(".,!?;:\"'()").lower().split()
        for word in [w for w in words if w]:
            index[word].add(id)

    return index

# ============================================================================
# EXERCISE 6: Matrix Rotation
# ============================================================================
#
# RELATED READING:
#   - ../04-interview-prep/01-interview-fundamentals.md (matrix operations)
#   - ../03-python-internals/02-advanced-python-features.md (list slicing)
#
# Rotate an NxN matrix 90 degrees clockwise. Modify the matrix in-place
# and also return it for convenience.
#
# Requirements:
#   - Rotate 90 degrees clockwise IN-PLACE
#   - Works for any NxN matrix (not just 3x3)
#   - Return the matrix after rotation
#
# Hints:
#   - 90-degree clockwise rotation = transpose + reverse each row
#   - Transpose: swap matrix[i][j] with matrix[j][i]
#   - Reverse each row: row[:] = row[::-1] (in-place slice assignment)
#   - Alternative one-liner (not in-place): list(zip(*matrix[::-1]))
#
#   Step-by-step algorithm (in-place, two steps):
#
#   Step 1 — Transpose (swap rows and columns):
#     n = len(matrix)
#     for i in range(n):
#         for j in range(i + 1, n):              # j > i avoids double-swap
#             matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]
#
#   Step 2 — Reverse each row:
#     for row in matrix:
#         row[:] = row[::-1]    # in-place slice assignment (row.reverse() also works)
#
#   Why this works:
#     Original:    Transposed:   Row-reversed:
#     1 2 3        1 4 7         7 4 1
#     4 5 6   ->   2 5 8   ->   8 5 2    (90 degrees clockwise)
#     7 8 9        3 6 9         9 6 3
#
#   In-place slice assignment: row[:] = row[::-1] replaces the contents
#   of the existing list rather than creating a new list object.
#
# Expected behavior:
#   matrix = [[1, 2, 3],
#             [4, 5, 6],
#             [7, 8, 9]]
#   rotate_matrix(matrix)
#   # matrix is now [[7, 4, 1],
#   #                [8, 5, 2],
#   #                [9, 6, 3]]


def rotate_matrix(matrix: list[list[int]]) -> list[list[int]]:
    """Rotate an NxN matrix 90 degrees clockwise in-place."""
    rotate = []
    for row in matrix:
        



# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

def test_group_anagrams():
    print("\n=== EXERCISE 1: Group Anagrams ===")
    result = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
    # Sort inner lists and outer list for comparison
    normalized = sorted(sorted(group) for group in result)
    assert normalized == [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]
    print(f"Grouped: {result}")

    # Edge cases
    assert group_anagrams([]) == []
    assert group_anagrams(["", ""]) == [["", ""]]
    assert group_anagrams(["abc"]) == [["abc"]]
    print("Edge cases passed")
    print("EXERCISE 1: PASSED")


def test_flatten_dict():
    print("\n=== EXERCISE 2: Flatten Nested Dict ===")
    result = flatten_dict({"a": {"b": 1, "c": {"d": 2}}, "e": 3})
    assert result == {"a.b": 1, "a.c.d": 2, "e": 3}
    print(f"Flattened: {result}")

    # Flat dict unchanged
    assert flatten_dict({"x": 1, "y": 2}) == {"x": 1, "y": 2}

    # Empty dict
    assert flatten_dict({}) == {}

    # Deeply nested
    deep = {"a": {"b": {"c": {"d": {"e": 5}}}}}
    assert flatten_dict(deep) == {"a.b.c.d.e": 5}
    print("Edge cases passed")
    print("EXERCISE 2: PASSED")


def test_most_frequent():
    print("\n=== EXERCISE 3: Most Frequent Words ===")
    result = most_frequent("the cat sat on the mat the cat", n=2)
    assert result == [("the", 3), ("cat", 2)]
    print(f"Top 2: {result}")

    # Case insensitive
    result2 = most_frequent("Hello hello HELLO world", n=1)
    assert result2 == [("hello", 3)]

    # Punctuation stripping
    result3 = most_frequent("yes! yes. yes? no.", n=2)
    assert result3 == [("yes", 3), ("no", 1)]
    print("Edge cases passed")
    print("EXERCISE 3: PASSED")


def test_merge_intervals():
    print("\n=== EXERCISE 4: Merge Intervals ===")
    result = merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)])
    assert result == [(1, 6), (8, 10), (15, 18)]
    print(f"Merged: {result}")

    # Touching intervals
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]

    # Already merged
    assert merge_intervals([(1, 2), (5, 6)]) == [(1, 2), (5, 6)]

    # Empty
    assert merge_intervals([]) == []

    # Single
    assert merge_intervals([(1, 5)]) == [(1, 5)]

    # Unsorted input
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]
    print("Edge cases passed")
    print("EXERCISE 4: PASSED")


def test_inverted_index():
    print("\n=== EXERCISE 5: Inverted Index ===")
    docs = [(1, "the cat sat"), (2, "the dog sat"), (3, "the cat played")]
    index = build_inverted_index(docs)
    assert index["cat"] == {1, 3}
    assert index["sat"] == {1, 2}
    assert index["the"] == {1, 2, 3}
    assert index["dog"] == {2}
    assert index["played"] == {3}
    print(f"Index entries: {len(index)}")

    # Empty input
    assert build_inverted_index([]) == {}
    print("Edge cases passed")
    print("EXERCISE 5: PASSED")


def test_rotate_matrix():
    print("\n=== EXERCISE 6: Matrix Rotation ===")
    matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    rotate_matrix(matrix)
    assert matrix == [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
    print(f"Rotated 3x3: {matrix}")

    # 2x2
    m2 = [[1, 2], [3, 4]]
    rotate_matrix(m2)
    assert m2 == [[3, 1], [4, 2]]

    # 1x1
    m1 = [[42]]
    rotate_matrix(m1)
    assert m1 == [[42]]
    print("Edge cases passed")
    print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    print("Strings & Collections Exercises")
    print("=" * 60)

    tests = [
        ("Exercise 1: Group Anagrams", test_group_anagrams),
        ("Exercise 2: Flatten Nested Dict", test_flatten_dict),
        ("Exercise 3: Most Frequent Words", test_most_frequent),
        ("Exercise 4: Merge Intervals", test_merge_intervals),
        ("Exercise 5: Inverted Index", test_inverted_index),
        ("Exercise 6: Matrix Rotation", test_rotate_matrix),
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
