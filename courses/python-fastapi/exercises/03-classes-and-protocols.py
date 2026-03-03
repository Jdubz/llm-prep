"""
Classes & Protocols Exercises

Dunder methods, structural typing, generics, and OOP patterns. These are
the foundations that Pydantic models, SQLAlchemy ORM, and FastAPI's
dependency injection build upon.

Run:  python exercises/03-classes-and-protocols.py
"""

from __future__ import annotations

from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

T = TypeVar("T")


# ============================================================================
# EXERCISE 1: Money Class
# ============================================================================
#
# Implement a Money class with rich comparison, arithmetic, and hashing.
# This practices the dunder methods that Python uses for operator overloading.
#
# Requirements:
#   - __init__(amount: float, currency: str = "USD")
#   - __repr__: Money(10.50, 'USD')
#   - __str__: $10.50 (or 10.50 EUR for non-USD)
#   - __eq__: equal if same amount AND same currency
#   - __lt__: compare amounts (raise ValueError if different currencies)
#   - __le__, __gt__, __ge__: derive from __lt__ and __eq__
#   - __add__: add amounts (raise ValueError if different currencies)
#   - __sub__: subtract amounts (raise ValueError if different currencies)
#   - __hash__: hash of (amount, currency) — makes Money usable in sets/dicts
#   - __bool__: True if amount != 0
#
# Hints:
#   - Use @functools.total_ordering to auto-generate __le__, __gt__, __ge__
#     from __eq__ and __lt__ (import functools, add @functools.total_ordering)
#   - Round amounts to 2 decimal places in __init__
#   - __hash__ = hash((self.amount, self.currency))
#
# Expected behavior:
#   m1 = Money(10.50, "USD")
#   m2 = Money(5.25, "USD")
#   m1 + m2  # Money(15.75, 'USD')
#   m1 > m2  # True
#   {m1, m2} # works because __hash__ is defined

import functools


@functools.total_ordering
class Money:
    """Currency-aware money type with rich comparison and arithmetic."""

    def __init__(self, amount: float, currency: str = "USD") -> None:
        # TODO: Store amount (rounded to 2 decimal places) and currency
        raise NotImplementedError()

    def __repr__(self) -> str:
        # TODO: Return Money(10.50, 'USD') format
        raise NotImplementedError()

    def __str__(self) -> str:
        # TODO: Return $10.50 for USD, 10.50 EUR for others
        raise NotImplementedError()

    def __eq__(self, other: object) -> bool:
        # TODO: Equal if same amount and currency
        raise NotImplementedError()

    def __lt__(self, other: object) -> bool:
        # TODO: Compare amounts, raise ValueError if different currencies
        raise NotImplementedError()

    def __add__(self, other: Money) -> Money:
        # TODO: Add amounts, raise ValueError if different currencies
        raise NotImplementedError()

    def __sub__(self, other: Money) -> Money:
        # TODO: Subtract amounts, raise ValueError if different currencies
        raise NotImplementedError()

    def __hash__(self) -> int:
        # TODO: Hash of (amount, currency)
        raise NotImplementedError()

    def __bool__(self) -> bool:
        # TODO: True if amount != 0
        raise NotImplementedError()


# ============================================================================
# EXERCISE 2: Linked List
# ============================================================================
#
# Implement a singly linked list with Python's iterator protocol and
# collection dunder methods.
#
# Requirements:
#   - Node class: value, next
#   - LinkedList class:
#       append(value): add to end
#       prepend(value): add to beginning
#       __iter__: yield values from head to tail
#       __len__: count of nodes
#       __contains__(value): membership check
#       __repr__: LinkedList(1 -> 2 -> 3)
#
# Hints:
#   - __iter__ is a generator: start at head, yield value, move to next
#   - __len__ can iterate and count, or maintain a size counter
#   - __contains__ can use __iter__: return any(v == value for v in self)
#
# Expected behavior:
#   ll = LinkedList()
#   ll.append(1); ll.append(2); ll.prepend(0)
#   list(ll)  # [0, 1, 2]
#   len(ll)   # 3
#   1 in ll   # True


class Node:
    """A node in a singly linked list."""

    def __init__(self, value: Any, next_node: Node | None = None) -> None:
        self.value = value
        self.next = next_node


class LinkedList:
    """Singly linked list with iterator protocol support."""

    def __init__(self) -> None:
        # TODO: Initialize head and size
        raise NotImplementedError()

    def append(self, value: Any) -> None:
        """Add a value to the end of the list."""
        # TODO: Implement
        raise NotImplementedError()

    def prepend(self, value: Any) -> None:
        """Add a value to the beginning of the list."""
        # TODO: Implement
        raise NotImplementedError()

    def __iter__(self):
        """Yield values from head to tail."""
        # TODO: Implement as a generator
        raise NotImplementedError()

    def __len__(self) -> int:
        # TODO: Return the number of nodes
        raise NotImplementedError()

    def __contains__(self, value: Any) -> bool:
        # TODO: Check if value exists in the list
        raise NotImplementedError()

    def __repr__(self) -> str:
        # TODO: Return LinkedList(1 -> 2 -> 3) format
        raise NotImplementedError()


# ============================================================================
# EXERCISE 3: Registry Pattern
# ============================================================================
#
# Implement a class decorator that auto-registers subclasses in a central
# registry. This pattern is used in plugin systems and serialization
# frameworks.
#
# Requirements:
#   - registry: a module-level dict mapping class names to classes
#   - @register: class decorator that adds the class to the registry
#   - get_registered(name): look up a class by name
#   - All registered classes must have a class attribute `kind`
#
# Hints:
#   - A class decorator receives the class and returns it (possibly modified)
#   - The registry is just a dict: registry[cls.__name__] = cls
#   - Check for `kind` attribute with hasattr()
#
# Expected behavior:
#   @register
#   class JsonParser:
#       kind = "json"
#       def parse(self, data): ...
#
#   @register
#   class XmlParser:
#       kind = "xml"
#       def parse(self, data): ...
#
#   get_registered("JsonParser")  # -> JsonParser class

registry: dict[str, type] = {}


def register(cls: type) -> type:
    """Class decorator that registers a class in the global registry."""
    # TODO: Implement
    raise NotImplementedError()


def get_registered(name: str) -> type | None:
    """Look up a registered class by name."""
    # TODO: Implement
    raise NotImplementedError()


# ============================================================================
# EXERCISE 4: Immutable Config
# ============================================================================
#
# Implement a config class that becomes immutable after initialization.
# Supports dot-notation access for nested dictionaries.
#
# Requirements:
#   - ImmutableConfig(data: dict) freezes after __init__
#   - Attribute access with dot notation: config.database.host
#   - __setattr__ raises AttributeError after init (except during __init__)
#   - __delattr__ always raises AttributeError
#   - __repr__: ImmutableConfig({...})
#   - Nested dicts are automatically wrapped as ImmutableConfig
#
# Hints:
#   - Use object.__setattr__(self, name, value) inside __init__ to bypass
#     your own __setattr__ override
#   - Set a _frozen flag at the end of __init__
#   - In __getattr__, check if the value in _data is a dict and wrap it
#   - __getattr__ is only called when normal attribute lookup fails
#
# Expected behavior:
#   config = ImmutableConfig({"db": {"host": "localhost", "port": 5432}})
#   config.db.host       # "localhost"
#   config.db.port       # 5432
#   config.db.host = "x" # AttributeError


class ImmutableConfig:
    """Frozen config object with dot-notation access for nested dicts."""

    def __init__(self, data: dict) -> None:
        # TODO: Store data and set frozen flag
        # Use object.__setattr__ to bypass your own __setattr__
        raise NotImplementedError()

    def __getattr__(self, name: str) -> Any:
        # TODO: Look up name in _data, wrap nested dicts
        raise NotImplementedError()

    def __setattr__(self, name: str, value: Any) -> None:
        # TODO: Raise AttributeError if frozen
        raise NotImplementedError()

    def __delattr__(self, name: str) -> None:
        # TODO: Always raise AttributeError
        raise NotImplementedError()

    def __repr__(self) -> str:
        # TODO: Return ImmutableConfig({...})
        raise NotImplementedError()


# ============================================================================
# EXERCISE 5: Observable (Event Emitter)
# ============================================================================
#
# Implement an event system with on(), emit(), and off() methods.
# Define a Listener protocol for type safety.
#
# Requirements:
#   - Listener Protocol: any callable that accepts **kwargs
#   - Observable class:
#       on(event: str, listener: Listener): register a listener
#       off(event: str, listener: Listener): unregister a listener
#       emit(event: str, **data): call all listeners for the event
#   - Listeners receive the event data as keyword arguments
#   - emit() calls listeners in registration order
#   - off() silently does nothing if the listener isn't registered
#
# Hints:
#   - Use a defaultdict(list) to store listeners per event
#   - Listener is a Protocol with __call__(self, **kwargs) -> None
#   - off() can use list.remove() wrapped in a try/except ValueError
#
# Expected behavior:
#   obs = Observable()
#   log = []
#   obs.on("click", lambda **data: log.append(data))
#   obs.emit("click", x=10, y=20)
#   log  # [{"x": 10, "y": 20}]

from collections import defaultdict


@runtime_checkable
class Listener(Protocol):
    """Protocol for event listeners."""

    def __call__(self, **kwargs: Any) -> None: ...


class Observable:
    """Event emitter with typed listener protocol."""

    def __init__(self) -> None:
        # TODO: Initialize listener storage
        raise NotImplementedError()

    def on(self, event: str, listener: Listener) -> None:
        """Register a listener for an event."""
        # TODO: Implement
        raise NotImplementedError()

    def off(self, event: str, listener: Listener) -> None:
        """Unregister a listener for an event."""
        # TODO: Implement
        raise NotImplementedError()

    def emit(self, event: str, **data: Any) -> None:
        """Emit an event, calling all registered listeners."""
        # TODO: Implement
        raise NotImplementedError()


# ============================================================================
# EXERCISE 6: Generic Stack
# ============================================================================
#
# Implement a type-safe stack using Generic[T]. This practices Python's
# generics system which is used in Pydantic, SQLAlchemy, and FastAPI.
#
# Requirements:
#   - Stack[T] is generic over the element type
#   - push(item: T): add to top
#   - pop() -> T: remove and return top (raise IndexError if empty)
#   - peek() -> T: return top without removing (raise IndexError if empty)
#   - is_empty() -> bool
#   - __len__() -> int
#   - __iter__: yield items from top to bottom
#   - __repr__: Stack([top, ..., bottom])
#
# Hints:
#   - Use a list internally (append/pop from end = O(1) stack operations)
#   - Generic[T] is for type checking only — no runtime enforcement needed
#   - __iter__ should yield from reversed internal list (top first)
#
# Expected behavior:
#   stack: Stack[int] = Stack()
#   stack.push(1); stack.push(2); stack.push(3)
#   stack.pop()    # 3
#   stack.peek()   # 2
#   list(stack)    # [2, 1]


class Stack(Generic[T]):
    """Type-safe stack with generic element type."""

    def __init__(self) -> None:
        # TODO: Initialize internal storage
        raise NotImplementedError()

    def push(self, item: T) -> None:
        """Push an item onto the top of the stack."""
        # TODO: Implement
        raise NotImplementedError()

    def pop(self) -> T:
        """Remove and return the top item. Raises IndexError if empty."""
        # TODO: Implement
        raise NotImplementedError()

    def peek(self) -> T:
        """Return the top item without removing it. Raises IndexError if empty."""
        # TODO: Implement
        raise NotImplementedError()

    def is_empty(self) -> bool:
        """Return True if the stack is empty."""
        # TODO: Implement
        raise NotImplementedError()

    def __len__(self) -> int:
        # TODO: Return the number of items
        raise NotImplementedError()

    def __iter__(self):
        """Yield items from top to bottom."""
        # TODO: Implement
        raise NotImplementedError()

    def __repr__(self) -> str:
        # TODO: Return Stack([top, ..., bottom])
        raise NotImplementedError()


# ============================================================================
# TESTS -- Uncomment to verify your implementations
# ============================================================================

# def test_money():
#     print("\n=== EXERCISE 1: Money ===")
#     m1 = Money(10.50, "USD")
#     m2 = Money(5.25, "USD")
#
#     assert repr(m1) == "Money(10.5, 'USD')"
#     assert str(m1) == "$10.50"
#     assert str(Money(10.50, "EUR")) == "10.50 EUR"
#
#     assert m1 + m2 == Money(15.75, "USD")
#     assert m1 - m2 == Money(5.25, "USD")
#     assert m1 > m2
#     assert m2 < m1
#     assert m1 == Money(10.50, "USD")
#     assert m1 != m2
#     print(f"{m1} + {m2} = {m1 + m2}")
#
#     # Hash works (can use in sets)
#     money_set = {m1, m2, Money(10.50, "USD")}
#     assert len(money_set) == 2
#     print(f"Set size: {len(money_set)} (expected 2)")
#
#     # Bool
#     assert bool(m1) is True
#     assert bool(Money(0)) is False
#
#     # Cross-currency errors
#     try:
#         Money(10, "USD") + Money(10, "EUR")
#         print("ERROR: Should have raised ValueError")
#     except ValueError:
#         print("Cross-currency add rejected (expected)")
#     print("EXERCISE 1: PASSED")
#
#
# def test_linked_list():
#     print("\n=== EXERCISE 2: Linked List ===")
#     ll = LinkedList()
#     ll.append(1)
#     ll.append(2)
#     ll.prepend(0)
#
#     assert list(ll) == [0, 1, 2]
#     assert len(ll) == 3
#     assert 1 in ll
#     assert 99 not in ll
#     print(f"List: {ll}")
#     print(f"Length: {len(ll)}, contains 1: {1 in ll}")
#
#     # Empty list
#     empty = LinkedList()
#     assert list(empty) == []
#     assert len(empty) == 0
#     print("Edge cases passed")
#     print("EXERCISE 2: PASSED")
#
#
# def test_registry():
#     print("\n=== EXERCISE 3: Registry ===")
#     registry.clear()  # reset for test
#
#     @register
#     class JsonParser:
#         kind = "json"
#         def parse(self, data): return f"json: {data}"
#
#     @register
#     class XmlParser:
#         kind = "xml"
#         def parse(self, data): return f"xml: {data}"
#
#     assert get_registered("JsonParser") is JsonParser
#     assert get_registered("XmlParser") is XmlParser
#     assert get_registered("Missing") is None
#     print(f"Registered: {list(registry.keys())}")
#     print("EXERCISE 3: PASSED")
#
#
# def test_immutable_config():
#     print("\n=== EXERCISE 4: Immutable Config ===")
#     config = ImmutableConfig({
#         "db": {"host": "localhost", "port": 5432},
#         "debug": True,
#     })
#
#     assert config.debug is True
#     assert config.db.host == "localhost"
#     assert config.db.port == 5432
#     print(f"config.db.host = {config.db.host}")
#
#     try:
#         config.debug = False
#         print("ERROR: Should have raised AttributeError")
#     except AttributeError:
#         print("Mutation blocked (expected)")
#
#     try:
#         del config.debug
#         print("ERROR: Should have raised AttributeError")
#     except AttributeError:
#         print("Deletion blocked (expected)")
#
#     try:
#         config.nonexistent
#         print("ERROR: Should have raised AttributeError")
#     except (AttributeError, KeyError):
#         print("Missing key raised error (expected)")
#     print("EXERCISE 4: PASSED")
#
#
# def test_observable():
#     print("\n=== EXERCISE 5: Observable ===")
#     obs = Observable()
#     log = []
#
#     def on_click(**data):
#         log.append(data)
#
#     obs.on("click", on_click)
#     obs.emit("click", x=10, y=20)
#     assert log == [{"x": 10, "y": 20}]
#     print(f"Event received: {log[-1]}")
#
#     obs.emit("click", x=30, y=40)
#     assert len(log) == 2
#
#     obs.off("click", on_click)
#     obs.emit("click", x=50, y=60)
#     assert len(log) == 2  # listener was removed
#     print(f"After off(): {len(log)} events (expected 2)")
#
#     # No error on emit with no listeners
#     obs.emit("nonexistent", foo="bar")
#     print("EXERCISE 5: PASSED")
#
#
# def test_generic_stack():
#     print("\n=== EXERCISE 6: Generic Stack ===")
#     stack: Stack[int] = Stack()
#     assert stack.is_empty()
#     assert len(stack) == 0
#
#     stack.push(1)
#     stack.push(2)
#     stack.push(3)
#
#     assert stack.peek() == 3
#     assert stack.pop() == 3
#     assert stack.pop() == 2
#     assert list(stack) == [1]
#     assert len(stack) == 1
#     print(f"Stack after pops: {stack}")
#
#     # Empty pop
#     stack.pop()
#     try:
#         stack.pop()
#         print("ERROR: Should have raised IndexError")
#     except IndexError:
#         print("Empty pop raised IndexError (expected)")
#
#     try:
#         stack.peek()
#         print("ERROR: Should have raised IndexError")
#     except IndexError:
#         print("Empty peek raised IndexError (expected)")
#     print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    exercises = [
        ("1 - Money Class", lambda: Money(10, "USD")),
        ("2 - Linked List", lambda: LinkedList()),
        ("3 - Registry Pattern", lambda: register(type("Test", (), {"kind": "test"}))),
        ("4 - Immutable Config", lambda: ImmutableConfig({"a": 1})),
        ("5 - Observable", lambda: Observable()),
        ("6 - Generic Stack", lambda: Stack()),
    ]

    print("Classes & Protocols Exercises")
    print("=" * 40)

    for name, factory in exercises:
        try:
            factory()
            print(f"  {name}: IMPLEMENTED")
        except NotImplementedError:
            print(f"  {name}: not implemented")

    # Uncomment below (and the test functions above) to run full tests:
    # print()
    # test_money()
    # test_linked_list()
    # test_registry()
    # test_immutable_config()
    # test_observable()
    # test_generic_stack()
    # print("\n=== ALL EXERCISES PASSED ===")
