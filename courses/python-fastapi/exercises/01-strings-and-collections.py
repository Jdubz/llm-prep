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
# Expected behavior:
#   group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
#   # -> [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]


def group_anagrams(words: list[str]) -> list[list[str]]:
    """Group anagrams from a list of strings."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 2: Flatten Nested Dict
# ============================================================================
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
# Expected behavior:
#   flatten_dict({"a": {"b": 1, "c": {"d": 2}}, "e": 3})
#   # -> {"a.b": 1, "a.c.d": 2, "e": 3}


def flatten_dict(nested: dict, prefix: str = "", sep: str = ".") -> dict:
    """Flatten a nested dictionary into dot-separated keys."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 3: Most Frequent Words
# ============================================================================
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
# Expected behavior:
#   most_frequent("the cat sat on the mat the cat", n=2)
#   # -> [("the", 3), ("cat", 2)]


def most_frequent(text: str, n: int = 3) -> list[tuple[str, int]]:
    """Return the N most frequent words in text."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 4: Merge Intervals
# ============================================================================
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
# Expected behavior:
#   merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)])
#   # -> [(1, 6), (8, 10), (15, 18)]


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping intervals."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 5: Inverted Index
# ============================================================================
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
# Expected behavior:
#   docs = [(1, "the cat sat"), (2, "the dog sat"), (3, "the cat played")]
#   index = build_inverted_index(docs)
#   index["cat"]  # -> {1, 3}
#   index["sat"]  # -> {1, 2}
#   index["the"]  # -> {1, 2, 3}


def build_inverted_index(documents: list[tuple[int, str]]) -> dict[str, set[int]]:
    """Build an inverted index mapping words to document IDs."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 6: Matrix Rotation
# ============================================================================
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
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

# def test_group_anagrams():
#     print("\n=== EXERCISE 1: Group Anagrams ===")
#     result = group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"])
#     # Sort inner lists and outer list for comparison
#     normalized = sorted(sorted(group) for group in result)
#     assert normalized == [["ate", "eat", "tea"], ["bat"], ["nat", "tan"]]
#     print(f"Grouped: {result}")
#
#     # Edge cases
#     assert group_anagrams([]) == []
#     assert group_anagrams(["", ""]) == [["", ""]]
#     assert group_anagrams(["abc"]) == [["abc"]]
#     print("Edge cases passed")
#     print("EXERCISE 1: PASSED")
#
#
# def test_flatten_dict():
#     print("\n=== EXERCISE 2: Flatten Nested Dict ===")
#     result = flatten_dict({"a": {"b": 1, "c": {"d": 2}}, "e": 3})
#     assert result == {"a.b": 1, "a.c.d": 2, "e": 3}
#     print(f"Flattened: {result}")
#
#     # Flat dict unchanged
#     assert flatten_dict({"x": 1, "y": 2}) == {"x": 1, "y": 2}
#
#     # Empty dict
#     assert flatten_dict({}) == {}
#
#     # Deeply nested
#     deep = {"a": {"b": {"c": {"d": {"e": 5}}}}}
#     assert flatten_dict(deep) == {"a.b.c.d.e": 5}
#     print("Edge cases passed")
#     print("EXERCISE 2: PASSED")
#
#
# def test_most_frequent():
#     print("\n=== EXERCISE 3: Most Frequent Words ===")
#     result = most_frequent("the cat sat on the mat the cat", n=2)
#     assert result == [("the", 3), ("cat", 2)]
#     print(f"Top 2: {result}")
#
#     # Case insensitive
#     result2 = most_frequent("Hello hello HELLO world", n=1)
#     assert result2 == [("hello", 3)]
#
#     # Punctuation stripping
#     result3 = most_frequent("yes! yes. yes? no.", n=2)
#     assert result3 == [("yes", 3), ("no", 1)]
#     print("Edge cases passed")
#     print("EXERCISE 3: PASSED")
#
#
# def test_merge_intervals():
#     print("\n=== EXERCISE 4: Merge Intervals ===")
#     result = merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)])
#     assert result == [(1, 6), (8, 10), (15, 18)]
#     print(f"Merged: {result}")
#
#     # Touching intervals
#     assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]
#
#     # Already merged
#     assert merge_intervals([(1, 2), (5, 6)]) == [(1, 2), (5, 6)]
#
#     # Empty
#     assert merge_intervals([]) == []
#
#     # Single
#     assert merge_intervals([(1, 5)]) == [(1, 5)]
#
#     # Unsorted input
#     assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]
#     print("Edge cases passed")
#     print("EXERCISE 4: PASSED")
#
#
# def test_inverted_index():
#     print("\n=== EXERCISE 5: Inverted Index ===")
#     docs = [(1, "the cat sat"), (2, "the dog sat"), (3, "the cat played")]
#     index = build_inverted_index(docs)
#     assert index["cat"] == {1, 3}
#     assert index["sat"] == {1, 2}
#     assert index["the"] == {1, 2, 3}
#     assert index["dog"] == {2}
#     assert index["played"] == {3}
#     print(f"Index entries: {len(index)}")
#
#     # Empty input
#     assert build_inverted_index([]) == {}
#     print("Edge cases passed")
#     print("EXERCISE 5: PASSED")
#
#
# def test_rotate_matrix():
#     print("\n=== EXERCISE 6: Matrix Rotation ===")
#     matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
#     rotate_matrix(matrix)
#     assert matrix == [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
#     print(f"Rotated 3x3: {matrix}")
#
#     # 2x2
#     m2 = [[1, 2], [3, 4]]
#     rotate_matrix(m2)
#     assert m2 == [[3, 1], [4, 2]]
#
#     # 1x1
#     m1 = [[42]]
#     rotate_matrix(m1)
#     assert m1 == [[42]]
#     print("Edge cases passed")
#     print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    exercises = [
        ("1 - Group Anagrams", group_anagrams, [["eat", "tea"]]),
        ("2 - Flatten Nested Dict", flatten_dict, [{"a": {"b": 1}}]),
        ("3 - Most Frequent Words", most_frequent, ["hello world hello"]),
        ("4 - Merge Intervals", merge_intervals, [[(1, 3), (2, 6)]]),
        ("5 - Inverted Index", build_inverted_index, [[(1, "hello world")]]),
        ("6 - Matrix Rotation", rotate_matrix, [[[1, 2], [3, 4]]]),
    ]

    print("Strings & Collections Exercises")
    print("=" * 40)

    for name, func, args in exercises:
        try:
            func(*args)
            print(f"  {name}: IMPLEMENTED")
        except NotImplementedError:
            print(f"  {name}: not implemented")

    # Uncomment below (and the test functions above) to run full tests:
    # print()
    # test_group_anagrams()
    # test_flatten_dict()
    # test_most_frequent()
    # test_merge_intervals()
    # test_inverted_index()
    # test_rotate_matrix()
    # print("\n=== ALL EXERCISES PASSED ===")
