"""
Module 09: Python Internals — Runnable Examples

Each section demonstrates a key runtime concept. Run the whole file or
import individual sections to explore interactively.
"""

from __future__ import annotations

import dis
import gc
import sys
import weakref
from contextvars import ContextVar
from typing import Any, ClassVar


# ---------------------------------------------------------------------------
# 1. REFERENCE COUNTING & CYCLIC GC
# ---------------------------------------------------------------------------

def demo_refcounting() -> None:
    """Show how reference counts change with assignments and deletions."""
    x = [1, 2, 3]
    # getrefcount always adds 1 for its own argument
    print(f"After x = [1,2,3]:        refcount = {sys.getrefcount(x)}")  # 2

    y = x
    print(f"After y = x:              refcount = {sys.getrefcount(x)}")  # 3

    container = [x]
    print(f"After container = [x]:    refcount = {sys.getrefcount(x)}")  # 4

    del container
    print(f"After del container:      refcount = {sys.getrefcount(x)}")  # 3

    del y
    print(f"After del y:              refcount = {sys.getrefcount(x)}")  # 2


def demo_reference_cycle() -> None:
    """Create a cycle that refcounting alone cannot free."""
    gc.disable()  # disable cyclic GC so we control it

    class Node:
        def __init__(self, name: str) -> None:
            self.name = name
            self.next: Node | None = None

        def __del__(self) -> None:
            print(f"  Node({self.name}) freed")

    print("Creating cycle...")
    a = Node("A")
    b = Node("B")
    a.next = b
    b.next = a   # cycle: A -> B -> A

    print("Deleting external references...")
    del a, b
    # Nodes are NOT freed yet — cycle keeps refcount at 1 each

    print(f"GC found {gc.collect()} unreachable objects")
    # Now the __del__ calls fire

    gc.enable()


# ---------------------------------------------------------------------------
# 2. SMALL INTEGER CACHE
# ---------------------------------------------------------------------------

def demo_integer_cache() -> None:
    """Demonstrate the -5..256 singleton cache."""
    for n in [0, 100, 256, 257, 1000]:
        a = n
        b = n
        same = a is b
        print(f"  {n:5d}: a is b = {same}")
    # 0, 100, 256 → True (cached)
    # 257, 1000   → False (new objects each time)


# ---------------------------------------------------------------------------
# 3. DESCRIPTORS
# ---------------------------------------------------------------------------

class Positive:
    """A data descriptor that enforces positive numeric values."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._attr = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> Any:
        if obj is None:
            return self  # accessed on the class, not an instance
        return getattr(obj, self._attr, None)

    def __set__(self, obj: Any, value: float) -> None:
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{self._attr} must be a positive number, got {value!r}")
        setattr(obj, self._attr, value)


class Product:
    price = Positive()
    quantity = Positive()

    def __init__(self, price: float, quantity: int) -> None:
        self.price = price
        self.quantity = quantity

    @property
    def total(self) -> float:
        return self.price * self.quantity


def demo_descriptors() -> None:
    p = Product(9.99, 3)
    print(f"  total = {p.total:.2f}")  # 29.97

    try:
        p.price = -5
    except ValueError as e:
        print(f"  Caught: {e}")

    # Accessing on the class returns the descriptor object itself
    print(f"  Product.price = {Product.price}")


# ---------------------------------------------------------------------------
# 4. MRO & cooperative super()
# ---------------------------------------------------------------------------

class Base:
    def process(self) -> str:
        return "Base"


class Logging(Base):
    def process(self) -> str:
        result = super().process()
        return f"[LOG] {result}"


class Timing(Base):
    def process(self) -> str:
        result = super().process()
        return f"[TIMED] {result}"


class LoggedTimedService(Logging, Timing):
    """MRO: LoggedTimedService -> Logging -> Timing -> Base -> object"""
    pass


def demo_mro() -> None:
    service = LoggedTimedService()
    print(f"  MRO: {[c.__name__ for c in LoggedTimedService.__mro__]}")
    # ['LoggedTimedService', 'Logging', 'Timing', 'Base', 'object']
    print(f"  result: {service.process()}")
    # [LOG] [TIMED] Base — both mixins participate via cooperative super()


# ---------------------------------------------------------------------------
# 5. __slots__
# ---------------------------------------------------------------------------

class Normal:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class Slotted:
    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


def demo_slots() -> None:
    n = Normal(1.0, 2.0)
    s = Slotted(1.0, 2.0)

    print(f"  Normal  has __dict__: {hasattr(n, '__dict__')}")   # True
    print(f"  Slotted has __dict__: {hasattr(s, '__dict__')}")   # False

    n.z = 99  # fine — dict accepts any attribute
    try:
        s.z = 99
    except AttributeError as e:
        print(f"  Slotted AttributeError: {e}")

    # Memory comparison (rough)
    print(f"  sys.getsizeof(Normal):  {sys.getsizeof(n)} bytes")
    print(f"  sys.getsizeof(Slotted): {sys.getsizeof(s)} bytes")
    # Slotted is smaller; the __dict__ savings (~200 bytes) are per-instance


# ---------------------------------------------------------------------------
# 6. BYTECODE INSPECTION
# ---------------------------------------------------------------------------

def demo_bytecode() -> None:
    def add(a: int, b: int) -> int:
        return a + b

    print("  Bytecode for add(a, b):")
    dis.dis(add)
    print()

    c = add.__code__
    print(f"  co_varnames: {c.co_varnames}")
    print(f"  co_consts:   {c.co_consts}")
    print(f"  co_argcount: {c.co_argcount}")


# ---------------------------------------------------------------------------
# 7. WEAK REFERENCES
# ---------------------------------------------------------------------------

def demo_weak_references() -> None:
    class Resource:
        def __init__(self, name: str) -> None:
            self.name = name

        def __del__(self) -> None:
            print(f"  Resource({self.name}) collected")

    cache: weakref.WeakValueDictionary[str, Resource] = weakref.WeakValueDictionary()

    r = Resource("database-conn")
    cache["db"] = r
    print(f"  cache['db']: {cache.get('db')}")  # Resource object

    del r  # remove the only strong reference
    print(f"  After del r, cache['db']: {cache.get('db')}")  # None (collected)


# ---------------------------------------------------------------------------
# 8. __new__ vs __init__: Singleton
# ---------------------------------------------------------------------------

class DatabasePool:
    """Singleton database pool — only one instance per process."""

    _instance: ClassVar[DatabasePool | None] = None
    _initialized: bool = False

    def __new__(cls) -> DatabasePool:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return   # guard against repeated __init__ on same instance
        self._initialized = True
        self.connections: list[str] = []
        print("  DatabasePool initialized")


def demo_new_vs_init() -> None:
    a = DatabasePool()  # prints "DatabasePool initialized"
    b = DatabasePool()  # no print — __init__ returns early
    print(f"  a is b: {a is b}")  # True


# ---------------------------------------------------------------------------
# 9. CONTEXT VARIABLES
# ---------------------------------------------------------------------------

request_id: ContextVar[str] = ContextVar("request_id", default="none")


async def demo_context_vars() -> None:
    """Show that ContextVar is per-task, not shared across tasks."""
    import asyncio

    async def worker(name: str, rid: str) -> None:
        token = request_id.set(rid)
        await asyncio.sleep(0)   # yield to event loop
        # Still sees OUR value, not another task's value
        print(f"  worker {name}: request_id = {request_id.get()}")
        request_id.reset(token)

    await asyncio.gather(
        worker("A", "req-aaa"),
        worker("B", "req-bbb"),
        worker("C", "req-ccc"),
    )
    # Each worker sees only its own request_id


# ---------------------------------------------------------------------------
# 10. DUNDER HASH RULE
# ---------------------------------------------------------------------------

class BadPoint:
    """Defines __eq__ but not __hash__ — becomes unhashable."""
    def __init__(self, x: int, y: int) -> None:
        self.x = x; self.y = y
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BadPoint): return NotImplemented
        return (self.x, self.y) == (other.x, other.y)
    # __hash__ = None  (set automatically by Python)


class GoodPoint:
    """Defines both __eq__ and __hash__ — hashable."""
    def __init__(self, x: int, y: int) -> None:
        self.x = x; self.y = y
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GoodPoint): return NotImplemented
        return (self.x, self.y) == (other.x, other.y)
    def __hash__(self) -> int:
        return hash((self.x, self.y))


def demo_hash_rule() -> None:
    bp = BadPoint(1, 2)
    gp = GoodPoint(1, 2)

    try:
        {bp}
    except TypeError as e:
        print(f"  BadPoint in set: {e}")

    s = {gp, GoodPoint(1, 2), GoodPoint(3, 4)}
    print(f"  GoodPoint set: {len(s)} unique points (GoodPoint(1,2) deduped)")


# ---------------------------------------------------------------------------
# MAIN RUNNER
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    sections = [
        ("1. Reference Counting", demo_refcounting),
        ("2. Reference Cycle + GC", demo_reference_cycle),
        ("3. Integer Cache", demo_integer_cache),
        ("4. Descriptors", demo_descriptors),
        ("5. MRO & super()", demo_mro),
        ("6. __slots__", demo_slots),
        ("7. Bytecode", demo_bytecode),
        ("8. Weak References", demo_weak_references),
        ("9. __new__ vs __init__", demo_new_vs_init),
        ("10. Hash Rule", demo_hash_rule),
    ]

    for title, fn in sections:
        print(f"\n--- {title} ---")
        fn()

    print("\n--- 11. Context Variables ---")
    asyncio.run(demo_context_vars())
