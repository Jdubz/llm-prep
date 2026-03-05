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
# RELATED READING:
#   - ../03-python-internals/01-object-model-and-memory.md (dunder methods, object model)
#   - ../03-python-internals/02-advanced-python-features.md (operator overloading)
#   - ../04-interview-prep/01-interview-fundamentals.md (OOP design)
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
#   Dunder method signatures for comparison:
#     def __eq__(self, other: object) -> bool:
#         if not isinstance(other, Money):
#             return NotImplemented         # let Python try other.__eq__(self)
#         return self.amount == other.amount and self.currency == other.currency
#
#     def __lt__(self, other: object) -> bool:
#         if not isinstance(other, Money):
#             return NotImplemented
#         if self.currency != other.currency:
#             raise ValueError("Cannot compare different currencies")
#         return self.amount < other.amount
#
#   @functools.total_ordering:
#     When you define __eq__ and __lt__, this class decorator auto-generates
#     __le__, __gt__, and __ge__ for you. Just add @functools.total_ordering
#     above the class definition.
#
#   Arithmetic dunder methods:
#     def __add__(self, other: Money) -> Money:
#         # Validate same currency, return Money(self.amount + other.amount, ...)
#
#     def __sub__(self, other: Money) -> Money:
#         # Same pattern as __add__
#
#   Hashing rule: if __eq__ is defined, __hash__ MUST also be defined
#   (or explicitly set to None) or instances become unhashable:
#     def __hash__(self) -> int:
#         return hash((self.amount, self.currency))
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
# RELATED READING:
#   - ../03-python-internals/01-object-model-and-memory.md (iterator protocol)
#   - ../03-python-internals/02-advanced-python-features.md (dunder methods)
#   - ../04-interview-prep/01-interview-fundamentals.md (data structures)
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
#   Iterator protocol — making a class work with for loops and list():
#     def __iter__(self):
#         current = self._head
#         while current is not None:
#             yield current.value       # yield makes this a generator
#             current = current.next
#
#   When you define __iter__, Python automatically supports:
#   - for item in obj: ...
#   - list(obj)
#   - item in obj  (if __contains__ is not defined)
#
#   Collection dunder methods:
#     def __len__(self) -> int:           # len(obj)
#         return self._size
#
#     def __contains__(self, value) -> bool:  # value in obj
#         return any(v == value for v in self)  # uses __iter__
#
#   Append to end of linked list:
#     If head is None, set head to new node.
#     Otherwise, walk to the last node (while current.next), then set
#     current.next = new_node.
#
#   Prepend to beginning:
#     new_node = Node(value, next_node=self._head)
#     self._head = new_node
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (class decorators, metaclass patterns)
#   - ../../fastapi/00-fastapi-foundations/01-http-routing-and-decorators.md (decorator registration)
#   - ../03-python-internals/03-imports-and-runtime.md (module-level state)
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
#   Class decorator pattern — differs from function decorators:
#   A class decorator takes a class as input and returns a class (usually
#   the same class, possibly modified):
#
#     def register(cls):
#         if not hasattr(cls, "kind"):
#             raise ValueError(f"{cls.__name__} must have a 'kind' attribute")
#         registry[cls.__name__] = cls
#         return cls                       # MUST return the class
#
#   This is simpler than function decorators because you don't need a
#   wrapper function. You just inspect/modify the class and return it.
#
#   How @register works:
#     @register
#     class JsonParser:
#         kind = "json"
#     # equivalent to: JsonParser = register(JsonParser)
#
#   get_registered is just a dict lookup:
#     def get_registered(name):
#         return registry.get(name)        # returns None if not found
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
# RELATED READING:
#   - ../03-python-internals/01-object-model-and-memory.md (attribute access, descriptors)
#   - ../03-python-internals/02-advanced-python-features.md (__setattr__, __getattr__)
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
#   Attribute access dunder methods:
#
#   __getattr__(self, name) — called ONLY when normal lookup fails:
#     def __getattr__(self, name):
#         try:
#             value = self._data[name]
#         except KeyError:
#             raise AttributeError(f"No attribute '{name}'")
#         if isinstance(value, dict):
#             return ImmutableConfig(value)  # wrap nested dicts
#         return value
#
#   __setattr__(self, name, value) — called on EVERY attribute assignment:
#     def __setattr__(self, name, value):
#         if getattr(self, '_frozen', False):
#             raise AttributeError("Config is immutable")
#         # This won't work during __init__ because _frozen isn't set yet.
#         # But we use object.__setattr__ in __init__ to bypass this entirely.
#
#   __delattr__(self, name) — called on del obj.attr:
#     def __delattr__(self, name):
#         raise AttributeError("Config is immutable")
#
#   The object.__setattr__ trick — bypassing your own __setattr__:
#     def __init__(self, data):
#         object.__setattr__(self, '_data', data)    # bypass self.__setattr__
#         object.__setattr__(self, '_frozen', True)   # now frozen
#
#   Why: during __init__ you need to set _data and _frozen, but your
#   __setattr__ override would block it. Calling object.__setattr__
#   directly uses the base class implementation, skipping your override.
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (Protocol, structural typing)
#   - ../03-python-internals/01-object-model-and-memory.md (callables, __call__)
#   - ../../fastapi/00-fastapi-foundations/02-dependency-injection.md (callback patterns)
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
#   Protocol — structural typing (duck typing with type checking):
#     from typing import Protocol, runtime_checkable
#
#     @runtime_checkable
#     class Listener(Protocol):
#         def __call__(self, **kwargs: Any) -> None: ...
#
#   A Protocol defines an interface without inheritance. Any object that
#   has a matching __call__ signature satisfies the protocol. This means:
#   - Regular functions:      def handler(**kwargs): ...
#   - Lambdas:                lambda **data: print(data)
#   - Classes with __call__:  class Handler: def __call__(self, **kwargs): ...
#   All satisfy Listener without explicitly inheriting from it.
#
#   @runtime_checkable allows isinstance() checks:
#     isinstance(my_func, Listener)  # True if it matches the protocol
#
#   defaultdict(list) for event storage:
#     from collections import defaultdict
#     self._listeners = defaultdict(list)
#     self._listeners["click"].append(handler)   # auto-creates list
#     for listener in self._listeners["click"]:  # empty list if no listeners
#         listener(**data)
#
#   Safe removal:
#     try:
#         self._listeners[event].remove(listener)
#     except ValueError:
#         pass  # listener wasn't registered, that's fine
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
# RELATED READING:
#   - ../03-python-internals/02-advanced-python-features.md (generics, TypeVar)
#   - ../03-python-internals/01-object-model-and-memory.md (data model, __class_getitem__)
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
#   Generic[T] syntax — parameterized types:
#     from typing import Generic, TypeVar
#     T = TypeVar("T")                    # declare a type variable
#
#     class Stack(Generic[T]):            # Stack is parameterized by T
#         def __init__(self) -> None:
#             self._items: list[T] = []   # T is used in type annotations
#
#         def push(self, item: T) -> None:
#             self._items.append(item)
#
#         def pop(self) -> T:
#             if not self._items:
#                 raise IndexError("pop from empty stack")
#             return self._items.pop()    # list.pop() removes last element
#
#   Generic[T] has NO runtime effect. It exists purely for type checkers
#   like mypy and pyright. At runtime, Stack[int] and Stack[str] are the
#   same class. But it gives you type safety during development:
#     stack: Stack[int] = Stack()
#     stack.push(1)          # OK
#     stack.push("hello")    # type error caught by mypy
#
#   Yielding in reverse (top to bottom):
#     def __iter__(self):
#         yield from reversed(self._items)
#     # reversed() returns a reverse iterator without copying the list
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

def test_money():
    print("\n=== EXERCISE 1: Money ===")
    m1 = Money(10.50, "USD")
    m2 = Money(5.25, "USD")

    assert repr(m1) == "Money(10.5, 'USD')"
    assert str(m1) == "$10.50"
    assert str(Money(10.50, "EUR")) == "10.50 EUR"

    assert m1 + m2 == Money(15.75, "USD")
    assert m1 - m2 == Money(5.25, "USD")
    assert m1 > m2
    assert m2 < m1
    assert m1 == Money(10.50, "USD")
    assert m1 != m2
    print(f"{m1} + {m2} = {m1 + m2}")

    # Hash works (can use in sets)
    money_set = {m1, m2, Money(10.50, "USD")}
    assert len(money_set) == 2
    print(f"Set size: {len(money_set)} (expected 2)")

    # Bool
    assert bool(m1) is True
    assert bool(Money(0)) is False

    # Cross-currency errors
    try:
        Money(10, "USD") + Money(10, "EUR")
        print("ERROR: Should have raised ValueError")
    except ValueError:
        print("Cross-currency add rejected (expected)")
    print("EXERCISE 1: PASSED")


def test_linked_list():
    print("\n=== EXERCISE 2: Linked List ===")
    ll = LinkedList()
    ll.append(1)
    ll.append(2)
    ll.prepend(0)

    assert list(ll) == [0, 1, 2]
    assert len(ll) == 3
    assert 1 in ll
    assert 99 not in ll
    print(f"List: {ll}")
    print(f"Length: {len(ll)}, contains 1: {1 in ll}")

    # Empty list
    empty = LinkedList()
    assert list(empty) == []
    assert len(empty) == 0
    print("Edge cases passed")
    print("EXERCISE 2: PASSED")


def test_registry():
    print("\n=== EXERCISE 3: Registry ===")
    registry.clear()  # reset for test

    @register
    class JsonParser:
        kind = "json"
        def parse(self, data): return f"json: {data}"

    @register
    class XmlParser:
        kind = "xml"
        def parse(self, data): return f"xml: {data}"

    assert get_registered("JsonParser") is JsonParser
    assert get_registered("XmlParser") is XmlParser
    assert get_registered("Missing") is None
    print(f"Registered: {list(registry.keys())}")
    print("EXERCISE 3: PASSED")


def test_immutable_config():
    print("\n=== EXERCISE 4: Immutable Config ===")
    config = ImmutableConfig({
        "db": {"host": "localhost", "port": 5432},
        "debug": True,
    })

    assert config.debug is True
    assert config.db.host == "localhost"
    assert config.db.port == 5432
    print(f"config.db.host = {config.db.host}")

    try:
        config.debug = False
        print("ERROR: Should have raised AttributeError")
    except AttributeError:
        print("Mutation blocked (expected)")

    try:
        del config.debug
        print("ERROR: Should have raised AttributeError")
    except AttributeError:
        print("Deletion blocked (expected)")

    try:
        config.nonexistent
        print("ERROR: Should have raised AttributeError")
    except (AttributeError, KeyError):
        print("Missing key raised error (expected)")
    print("EXERCISE 4: PASSED")


def test_observable():
    print("\n=== EXERCISE 5: Observable ===")
    obs = Observable()
    log = []

    def on_click(**data):
        log.append(data)

    obs.on("click", on_click)
    obs.emit("click", x=10, y=20)
    assert log == [{"x": 10, "y": 20}]
    print(f"Event received: {log[-1]}")

    obs.emit("click", x=30, y=40)
    assert len(log) == 2

    obs.off("click", on_click)
    obs.emit("click", x=50, y=60)
    assert len(log) == 2  # listener was removed
    print(f"After off(): {len(log)} events (expected 2)")

    # No error on emit with no listeners
    obs.emit("nonexistent", foo="bar")
    print("EXERCISE 5: PASSED")


def test_generic_stack():
    print("\n=== EXERCISE 6: Generic Stack ===")
    stack: Stack[int] = Stack()
    assert stack.is_empty()
    assert len(stack) == 0

    stack.push(1)
    stack.push(2)
    stack.push(3)

    assert stack.peek() == 3
    assert stack.pop() == 3
    assert stack.pop() == 2
    assert list(stack) == [1]
    assert len(stack) == 1
    print(f"Stack after pops: {stack}")

    # Empty pop
    stack.pop()
    try:
        stack.pop()
        print("ERROR: Should have raised IndexError")
    except IndexError:
        print("Empty pop raised IndexError (expected)")

    try:
        stack.peek()
        print("ERROR: Should have raised IndexError")
    except IndexError:
        print("Empty peek raised IndexError (expected)")
    print("EXERCISE 6: PASSED")


if __name__ == "__main__":
    print("Classes & Protocols Exercises")
    print("=" * 60)

    tests = [
        ("Exercise 1: Money Class", test_money),
        ("Exercise 2: Linked List", test_linked_list),
        ("Exercise 3: Registry Pattern", test_registry),
        ("Exercise 4: Immutable Config", test_immutable_config),
        ("Exercise 5: Observable", test_observable),
        ("Exercise 6: Generic Stack", test_generic_stack),
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
