"""
Module 00 — Python Fundamentals: Complete Examples
===================================================

Runnable examples covering syntax, types, classes, decorators, context managers,
generators, and Pydantic data modeling. No framework dependencies (except pydantic).

Run with:  python examples.py
Requires:  pydantic
"""
from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Generic, Protocol, TypeVar

# =============================================================================
# 1. Collections and Comprehensions
# =============================================================================

def collections_demo():
    """Lists, dicts, sets, tuples, and comprehension patterns."""
    # List operations
    items = [3, 1, 4, 1, 5, 9]
    items.append(2)
    items.sort()
    print(f"Sorted: {items}")
    print(f"Last: {items[-1]}, Slice [1:4]: {items[1:4]}")

    # Dict operations
    user = {"name": "Alice", "age": 30, "role": "admin"}
    print(f"Safe get: {user.get('email', 'N/A')}")
    print(f"Keys: {list(user.keys())}")

    # Comprehensions
    squares = [x ** 2 for x in range(10)]
    evens = [x for x in range(20) if x % 2 == 0]
    name_lengths = {name: len(name) for name in ["Alice", "Bob", "Charlie"]}
    unique_chars = {c for c in "hello world" if c.isalpha()}

    print(f"Squares: {squares[:5]}...")
    print(f"Evens: {evens[:5]}...")
    print(f"Name lengths: {name_lengths}")
    print(f"Unique chars: {sorted(unique_chars)}")

    # Unpacking
    first, *middle, last = [1, 2, 3, 4, 5]
    print(f"Unpack: first={first}, middle={middle}, last={last}")

    # Dict merge (3.9+)
    defaults = {"timeout": 30, "retries": 3}
    overrides = {"timeout": 60}
    config = defaults | overrides
    print(f"Merged config: {config}")


# =============================================================================
# 2. Functions: *args, **kwargs, closures, lambdas
# =============================================================================

def functions_demo():
    """Function patterns: default args, *args/**kwargs, closures."""
    # Default and keyword arguments
    def connect(host: str, port: int = 5432, ssl: bool = True) -> str:
        return f"{host}:{port} (ssl={ssl})"

    print(f"Default: {connect('localhost')}")
    print(f"Named:   {connect('db.prod', ssl=False)}")

    # *args and **kwargs
    def log(*messages: str, **metadata: Any) -> None:
        print(f"  Messages: {messages}, Meta: {metadata}")

    log("hello", "world", level="info", user="alice")

    # Spreading
    data = {"host": "localhost", "port": 3000, "ssl": False}
    print(f"Spread: {connect(**data)}")

    # Closure
    def make_multiplier(factor: int):
        def multiply(x: int) -> int:
            return x * factor
        return multiply

    double = make_multiplier(2)
    triple = make_multiplier(3)
    print(f"double(5)={double(5)}, triple(5)={triple(5)}")

    # Lambda
    items = [{"name": "Bob", "age": 25}, {"name": "Alice", "age": 30}]
    items.sort(key=lambda x: x["name"])
    print(f"Sorted by name: {[i['name'] for i in items]}")


# =============================================================================
# 3. Classes: inheritance, properties, dunder methods, dataclasses
# =============================================================================

class Money:
    """Example class with dunder methods."""
    def __init__(self, amount: float, currency: str = "USD") -> None:
        self.amount = amount
        self.currency = currency

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency!r})"

    def __str__(self) -> str:
        return f"${self.amount:.2f} {self.currency}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)


class Circle:
    """Example with @property."""
    def __init__(self, radius: float) -> None:
        self.radius = radius

    @property
    def area(self) -> float:
        return 3.14159 * self.radius ** 2

    @property
    def diameter(self) -> float:
        return self.radius * 2


@dataclass
class Point:
    """Example dataclass."""
    x: float
    y: float
    label: str = "origin"


class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


def classes_demo():
    """Classes, properties, dataclasses, enums."""
    # Dunder methods
    a = Money(10.50, "USD")
    b = Money(5.25, "USD")
    print(f"repr: {repr(a)}")
    print(f"str:  {a}")
    print(f"a + b = {a + b}")
    print(f"a == Money(10.50, 'USD'): {a == Money(10.50, 'USD')}")

    # Property
    c = Circle(5)
    print(f"Circle r=5: area={c.area:.2f}, diameter={c.diameter}")

    # Dataclass
    p = Point(1.0, 2.0, "A")
    print(f"Point: {p}")

    # Enum
    role = Role.ADMIN
    print(f"Role: {role}, value: {role.value}")


# =============================================================================
# 4. Decorators: basic, with arguments, stacking
# =============================================================================

def timing(func):
    """Simple timing decorator."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  {func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper


def retry(max_attempts: int = 3):
    """Decorator factory (decorator with arguments)."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"  Attempt {attempt} failed: {e}")
        return wrapper
    return decorator


_call_count = 0

@retry(max_attempts=3)
@timing
def flaky_function() -> str:
    global _call_count
    _call_count += 1
    if _call_count < 3:
        raise ValueError("not yet")
    return "success"


def decorators_demo():
    """Decorator patterns."""
    global _call_count
    _call_count = 0
    result = flaky_function()
    print(f"  Result: {result}")
    print(f"  Preserved name: {flaky_function.__name__}")


# =============================================================================
# 5. Context Managers and Generators
# =============================================================================

@contextmanager
def timer(label: str):
    """Context manager for timing a block."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"  {label}: {elapsed:.4f}s")


def fibonacci(n: int):
    """Generator: yields first n Fibonacci numbers."""
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b


def context_and_generators_demo():
    """Context managers and generator patterns."""
    # Context manager
    with timer("sum"):
        total = sum(range(1_000_000))
    print(f"  Total: {total}")

    # Generator
    fibs = list(fibonacci(10))
    print(f"  Fibonacci(10): {fibs}")

    # Generator expression
    squares_gen = (x ** 2 for x in range(10))
    print(f"  First 3 squares: {[next(squares_gen) for _ in range(3)]}")

    # any/all with generators
    nums = [2, 4, 6, 8, 10]
    print(f"  All even: {all(n % 2 == 0 for n in nums)}")
    print(f"  Any > 7: {any(n > 7 for n in nums)}")


# =============================================================================
# 6. Pydantic Data Modeling
# =============================================================================

def pydantic_demo():
    """Pydantic validation, serialization, inheritance."""
    from pydantic import BaseModel, Field, field_validator, ConfigDict

    class ItemBase(BaseModel):
        name: str = Field(..., min_length=1, max_length=100)
        price: float = Field(..., gt=0)

    class ItemCreate(ItemBase):
        tags: list[str] = Field(default_factory=list)

        @field_validator("name")
        @classmethod
        def name_must_be_titlecase(cls, v: str) -> str:
            return v.strip()

    class ItemResponse(ItemBase):
        id: int
        tags: list[str]

    # Valid
    item = ItemCreate(name="Widget", price=9.99, tags=["sale"])
    print(f"  Created: {item}")
    print(f"  Dict: {item.model_dump()}")
    print(f"  JSON: {item.model_dump_json()}")

    # Response model
    resp = ItemResponse(id=1, name="Widget", price=9.99, tags=["sale"])
    print(f"  Response: {resp.model_dump()}")

    # Validation error
    from pydantic import ValidationError
    try:
        ItemCreate(name="", price=-5)
    except ValidationError as e:
        print(f"  Validation errors: {e.error_count()} errors")
        for err in e.errors():
            print(f"    - {err['loc'][-1]}: {err['msg']}")


# =============================================================================
# 7. Protocol (Structural Typing)
# =============================================================================

class Describable(Protocol):
    """Structural interface — any class with a describe() method satisfies this."""
    def describe(self) -> str: ...


class Product:
    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self.price = price

    def describe(self) -> str:
        return f"{self.name} (${self.price:.2f})"


class Service:
    def __init__(self, name: str, rate: float) -> None:
        self.name = name
        self.rate = rate

    def describe(self) -> str:
        return f"{self.name} (${self.rate:.2f}/hr)"


def print_description(item: Describable) -> None:
    print(f"  {item.describe()}")


def protocol_demo():
    """Protocol / structural typing example."""
    print_description(Product("Widget", 9.99))
    print_description(Service("Consulting", 150.0))


# =============================================================================
# Run all examples
# =============================================================================

def main():
    sections = [
        ("1: Collections & Comprehensions", collections_demo),
        ("2: Functions", functions_demo),
        ("3: Classes & OOP", classes_demo),
        ("4: Decorators", decorators_demo),
        ("5: Context Managers & Generators", context_and_generators_demo),
        ("6: Pydantic Data Modeling", pydantic_demo),
        ("7: Protocol (Structural Typing)", protocol_demo),
    ]
    for title, fn in sections:
        print(f"\n=== {title} ===")
        fn()
    print("\nAll examples completed.")


if __name__ == "__main__":
    main()
