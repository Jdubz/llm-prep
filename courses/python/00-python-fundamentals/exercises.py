"""
Module 00 — Python Fundamentals: Exercises
===========================================

Practice exercises for Python syntax, types, classes, decorators, and Pydantic.
No framework dependencies (except pydantic for exercise 6).

Replace `pass` with your implementation. Run with: python exercises.py
"""
from __future__ import annotations

# =============================================================================
# EXERCISE 1: Collection Operations
# =============================================================================
# Implement these using comprehensions and built-in functions.
# SEE: 01-syntax-types-and-patterns.md sections 2 (Collections) and 5 (Comprehensions)
# SEE: examples.py section 1 (Collections and Comprehensions)
#
# Pattern — list comprehension with filter:
#   [x for x in items if condition(x)]
#
# Pattern — dict comprehension:
#   {key: value for item in items}

def word_frequencies(text: str) -> dict[str, int]:
    """Return a dict mapping each lowercase word to its count.
    Words are split on whitespace. Punctuation stays attached.

    >>> word_frequencies("the cat and the dog")
    {'the': 2, 'cat': 1, 'and': 1, 'dog': 1}
    """
    # TODO
    pass


def invert_dict(d: dict[str, int]) -> dict[int, list[str]]:
    """Invert a dict: values become keys, keys become lists of original keys.

    >>> invert_dict({"a": 1, "b": 2, "c": 1})
    {1: ['a', 'c'], 2: ['b']}
    """
    # TODO
    pass


def flatten(nested: list[list]) -> list:
    """Flatten a list of lists into a single list using a comprehension.

    >>> flatten([[1, 2], [3], [4, 5, 6]])
    [1, 2, 3, 4, 5, 6]
    """
    # TODO
    pass


# =============================================================================
# EXERCISE 2: Functions and Closures
# =============================================================================
# SEE: 01-syntax-types-and-patterns.md section 3 (Functions)
# SEE: examples.py section 2 (Functions)
#
# Pattern — closure capturing state:
#   def outer(x):
#       def inner(y):
#           return x + y
#       return inner

def compose(*funcs):
    """Return a function that is the composition of the given functions.
    compose(f, g, h)(x) == f(g(h(x)))  (rightmost applied first)

    >>> double = lambda x: x * 2
    >>> add_one = lambda x: x + 1
    >>> compose(add_one, double)(5)
    11
    """
    # TODO
    pass


def memoize(func):
    """Return a memoized version of func. Cache results by args.
    Only needs to handle positional, hashable arguments.

    >>> @memoize
    ... def fib(n):
    ...     return n if n < 2 else fib(n-1) + fib(n-2)
    >>> fib(10)
    55
    """
    # TODO
    pass


# =============================================================================
# EXERCISE 3: Classes and Dunder Methods
# =============================================================================
# SEE: 02-classes-decorators-and-oop.md section 1 (Classes)
# SEE: examples.py section 3 (Classes)
#
# Pattern — implementing __repr__ and __eq__:
#   def __repr__(self) -> str:
#       return f"ClassName(field={self.field!r})"
#   def __eq__(self, other) -> bool:
#       if not isinstance(other, ClassName): return NotImplemented
#       return self.field == other.field

class Vector:
    """A 2D vector with dunder methods for arithmetic and comparison.

    Requirements:
    - __init__(self, x: float, y: float)
    - __repr__ returns "Vector(x, y)"
    - __eq__ compares x and y values
    - __add__ returns a new Vector (component-wise addition)
    - __mul__(self, scalar: float) returns a new Vector (scalar multiplication)
    - magnitude property returns the Euclidean length (x**2 + y**2) ** 0.5

    >>> v1 = Vector(3, 4)
    >>> v1.magnitude
    5.0
    >>> v1 + Vector(1, 2)
    Vector(4, 6)
    >>> v1 * 2
    Vector(6, 8)
    """
    pass  # TODO: implement


# =============================================================================
# EXERCISE 4: Decorator Factory
# =============================================================================
# SEE: 02-classes-decorators-and-oop.md section 2 (Decorators)
# SEE: examples.py section 4 (Decorators)
#
# Pattern — decorator factory (decorator with arguments):
#   def my_decorator(arg):
#       def decorator(func):
#           @functools.wraps(func)
#           def wrapper(*args, **kwargs):
#               ...
#               return func(*args, **kwargs)
#           return wrapper
#       return decorator

import functools

def validate_types(**type_hints):
    """Decorator factory that validates argument types at runtime.

    >>> @validate_types(name=str, age=int)
    ... def greet(name, age):
    ...     return f"{name} is {age}"
    >>> greet("Alice", 30)
    'Alice is 30'
    >>> greet("Alice", "thirty")  # raises TypeError
    Traceback (most recent call last):
    TypeError: age must be <class 'int'>, got <class 'str'>
    """
    # TODO
    pass


# =============================================================================
# EXERCISE 5: Context Manager and Generator
# =============================================================================
# SEE: 02-classes-decorators-and-oop.md sections 3-4 (Context Managers, Generators)
# SEE: examples.py section 5 (Context Managers & Generators)
#
# Pattern — generator with yield:
#   def my_gen(n):
#       for i in range(n):
#           yield transform(i)

def chunked(items: list, size: int):
    """Generator that yields successive chunks of `size` from `items`.

    >>> list(chunked([1, 2, 3, 4, 5], 2))
    [[1, 2], [3, 4], [5]]
    >>> list(chunked([], 3))
    []
    """
    # TODO
    pass


def sliding_window(items: list, size: int):
    """Generator that yields sliding windows of `size` over `items`.

    >>> list(sliding_window([1, 2, 3, 4, 5], 3))
    [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
    >>> list(sliding_window([1, 2], 3))
    []
    """
    # TODO
    pass


# =============================================================================
# EXERCISE 6: Pydantic Model
# =============================================================================
# SEE: 03-pydantic-and-data-modeling.md (all sections)
# SEE: examples.py section 6 (Pydantic Data Modeling)
#
# Pattern — Pydantic model with validators:
#   from pydantic import BaseModel, Field, field_validator
#   class MyModel(BaseModel):
#       field: str = Field(..., min_length=1)
#       @field_validator("field")
#       @classmethod
#       def check(cls, v): ...

# TODO: Implement an Address model using Pydantic with:
# - street: str (required, 1-200 chars)
# - city: str (required, 1-100 chars)
# - state: str (required, exactly 2 uppercase letters — use @field_validator)
# - zip_code: str (required, pattern r"^\d{5}(-\d{4})?$")
# - country: str (default "US")
#
# >>> addr = Address(street="123 Main St", city="Springfield", state="IL", zip_code="62704")
# >>> addr.model_dump()
# {'street': '123 Main St', 'city': 'Springfield', 'state': 'IL', 'zip_code': '62704', 'country': 'US'}


# =============================================================================
# TESTS (run: python exercises.py)
# =============================================================================
def _test_all():
    print("=== Exercise 1: Collection Operations ===")
    try:
        assert word_frequencies("the cat and the dog") == {"the": 2, "cat": 1, "and": 1, "dog": 1}
        assert invert_dict({"a": 1, "b": 2, "c": 1}) == {1: ["a", "c"], 2: ["b"]}
        assert flatten([[1, 2], [3], [4, 5, 6]]) == [1, 2, 3, 4, 5, 6]
        print("  PASSED")
    except (AssertionError, TypeError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")

    print("\n=== Exercise 2: Functions and Closures ===")
    try:
        f = compose(lambda x: x + 1, lambda x: x * 2)
        assert f(5) == 11

        @memoize
        def fib(n):
            return n if n < 2 else fib(n - 1) + fib(n - 2)
        assert fib(10) == 55
        print("  PASSED")
    except (AssertionError, TypeError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")

    print("\n=== Exercise 3: Vector Class ===")
    try:
        v1 = Vector(3, 4)
        assert v1.magnitude == 5.0
        assert v1 + Vector(1, 2) == Vector(4, 6)
        assert v1 * 2 == Vector(6, 8)
        assert repr(v1) == "Vector(3, 4)"
        print("  PASSED")
    except (AssertionError, TypeError, AttributeError, NameError) as e:
        print(f"  Not implemented or failing: {e}")

    print("\n=== Exercise 4: Type Validation Decorator ===")
    try:
        @validate_types(name=str, age=int)
        def greet(name, age):
            return f"{name} is {age}"

        assert greet("Alice", 30) == "Alice is 30"
        try:
            greet("Alice", "thirty")
            assert False, "Should have raised TypeError"
        except TypeError:
            pass
        print("  PASSED")
    except (AssertionError, TypeError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")

    print("\n=== Exercise 5: Generators ===")
    try:
        assert list(chunked([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
        assert list(chunked([], 3)) == []
        assert list(sliding_window([1, 2, 3, 4, 5], 3)) == [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
        assert list(sliding_window([1, 2], 3)) == []
        print("  PASSED")
    except (AssertionError, TypeError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")

    print("\n=== Exercise 6: Pydantic Address Model ===")
    try:
        from pydantic import ValidationError
        addr = Address(street="123 Main St", city="Springfield", state="IL", zip_code="62704")
        assert addr.country == "US"
        assert addr.state == "IL"
        try:
            Address(street="123 Main St", city="Springfield", state="invalid", zip_code="62704")
            assert False, "Should have raised ValidationError"
        except (ValidationError, NameError):
            pass
        print("  PASSED")
    except (NameError, TypeError, AttributeError) as e:
        print(f"  Not implemented or failing: {e}")


if __name__ == "__main__":
    _test_all()
    print("\nImplement each exercise, then re-run to verify.")
