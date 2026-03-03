# 02 – Advanced Python Features

## Descriptors: How `property`, `classmethod`, `staticmethod` Work

A **descriptor** is any object defining `__get__`, `__set__`, or `__delete__`. When you access an attribute through a class, Python's `__getattribute__` checks if the class holds a descriptor and calls its `__get__` instead of returning the raw value.

```python
class Descriptor:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self   # accessed on the class itself
        return 42

class MyClass:
    value = Descriptor()

MyClass.value     # returns the Descriptor object itself (obj=None branch)
MyClass().value   # returns 42 (__get__ called with instance)
```

`property` is a built-in descriptor — `@property` is syntactic sugar:

```python
class Circle:
    @property
    def area(self): return 3.14 * self.radius ** 2
    # equivalent to: area = property(lambda self: 3.14 * self.radius ** 2)
```

### Data vs Non-Data Descriptors

**Data descriptors** define `__get__` AND `__set__` (or `__delete__`). They take priority over instance `__dict__`. **Non-data descriptors** define only `__get__`; instance `__dict__` takes priority.

Lookup order for `instance.attr`:
1. Data descriptor in `type(instance).__mro__`
2. Instance `__dict__`
3. Non-data descriptor (or class variable) in `type(instance).__mro__`

This is why you can shadow a regular method by assigning to `self.method_name` but you cannot shadow a `@property` with a setter the same way.

### Practical Descriptor Example

```python
class Validator:
    def __set_name__(self, owner, name):
        self.name = f"_{name}"

    def __get__(self, obj, objtype=None):
        return getattr(obj, self.name, None) if obj else self

    def __set__(self, obj, value):
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{self.name} must be a non-negative int")
        setattr(obj, self.name, value)

class Item:
    count = Validator()  # data descriptor — can't be shadowed by instance attr
```

**Interview insight**: Pydantic fields are descriptors under the hood. Understanding descriptors explains how `model.field` returns a value, but `Model.field` returns field metadata.

---

## MRO and `super()`

Python uses **C3 linearization** to compute the Method Resolution Order for multiple inheritance. The MRO guarantees:
- Local precedence (left-to-right in class definition)
- Monotonicity (if A before B in a parent's MRO, stays that way in the child's)

```python
class A:
    def method(self): return "A"

class B(A):
    def method(self): return "B"

class C(A):
    def method(self): return "C"

class D(B, C): pass

D.__mro__      # (D, B, C, A, object)
D().method()   # "B" — B is first in MRO after D

# Inspect MRO
MyClass.__mro__    # tuple of classes in resolution order
MyClass.mro()      # list version
```

**`super()` does NOT mean "call the parent class."** It means "call the next class in this *instance's* MRO, starting after the class that contains this `super()` call."

```python
class A:
    def hello(self):
        print("A")
        super().hello()   # next in MRO after A is B (when called on D instance)

class B:
    def hello(self):
        print("B")

class D(A, B): pass

D().hello()   # prints: A, then B
# D.__mro__ = (D, A, B, object)
# D.hello -> A.hello -> super() finds B -> B.hello
```

If `super()` always meant "call the parent," cooperative multiple inheritance would be impossible — `super()` chains through the MRO of the *actual instance's class*.

```python
# super() in cooperative multiple inheritance
class A:
    def f(self): print("A"); super().f()
class B:
    def f(self): print("B")
class C(A, B): pass
C().f()   # A, then B — super() in A finds B (not object) via C's MRO
```

---

## The Import System

```python
import sys

import json
json is sys.modules["json"]   # True — cached module object
```

When you `import foo`:
1. Check `sys.modules["foo"]` → return immediately if found
2. Find file via `sys.path` and `sys.meta_path` finders
3. Execute module body top-to-bottom, storing result in `sys.modules["foo"]`
4. Bind `foo` in current namespace

```python
# Module cache tools
sys.modules["json"]          # the cached json module object
sys.modules.pop("foo", None) # evict from cache (forces re-import)

import importlib
importlib.reload(module)     # re-execute module body (old refs still point to old objects)

# sys.path — where Python looks for modules
sys.path.insert(0, "/my/path")  # add search path at front

# __all__ controls `from module import *`
# __init__.py marks a directory as a package
```

**Circular imports** don't crash because step 1 returns the partially-initialized module:
```python
# a.py: import b; print(b.VALUE)
# b.py: import a; VALUE = 42
# When a imports b, b imports a — gets the partially-initialized 'a' module.
# If b accesses a.something before a defines it, AttributeError.
# The fix: move imports inside functions, or restructure to avoid the cycle.
```

---

## `__init_subclass__`: Plugin Registration Without Metaclasses

A simpler alternative to metaclasses for most use cases:

```python
class Plugin:
    _registry: dict[str, type] = {}

    def __init_subclass__(cls, plugin_name: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__.lower()
        Plugin._registry[name] = cls
        print(f"Registered plugin: {name}")

class CSVPlugin(Plugin, plugin_name="csv"):
    def process(self, data): ...

class JSONPlugin(Plugin, plugin_name="json"):
    def process(self, data): ...

Plugin._registry  # {"csv": CSVPlugin, "json": JSONPlugin}
```

Called automatically whenever a subclass is defined. Much simpler than metaclasses for plugin systems, registry patterns, and abstract base class enforcement.

---

## The `__prepare__` Hook and Metaclasses

When Python parses a `class` body, it needs a namespace to store the class attributes. Normally this is a plain `dict`, but metaclasses can intercept this via `__prepare__`.

```python
class OrderedMeta(type):
    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        # Return the namespace used during class body execution
        print(f"Preparing namespace for {name}")
        return {}  # plain dict here, but could be anything

    def __new__(mcs, name, bases, namespace, **kwargs):
        print(f"Creating class {name} with attrs: {list(namespace.keys())}")
        return super().__new__(mcs, name, bases, namespace)

class MyClass(metaclass=OrderedMeta):
    x = 1
    y = 2
    z = 3
# Preparing namespace for MyClass
# Creating class MyClass with attrs: ['__module__', '__qualname__', 'x', 'y', 'z']
```

`enum.Enum` uses a custom `__prepare__` to detect duplicate member names (which plain dicts silently overwrite).

### Full Class Creation Sequence

```
class Foo(Base, metaclass=Meta):
    body...

1. Meta.__prepare__("Foo", (Base,)) → namespace dict
2. Execute class body in namespace
3. Meta("Foo", (Base,), namespace) →
   a. Meta.__new__(Meta, "Foo", (Base,), namespace) → class object
   b. Meta.__init__(class_obj, "Foo", (Base,), namespace)
4. Bind "Foo" in enclosing scope
```

---

## `__class_getitem__` and Generic Classes

How `list[int]`, `dict[str, int]`, and custom `MyClass[T]` work:

```python
# When you write list[int], Python calls:
list.__class_getitem__(int)
# Returns: list[int] (a GenericAlias object, used for type hints at runtime)

# Making your own class subscriptable:
class Stack:
    def __class_getitem__(cls, item):
        return f"Stack[{item.__name__}]"

Stack[int]    # "Stack[int]"

# The proper way with Generic:
from typing import TypeVar, Generic

T = TypeVar("T")

class TypedStack(Generic[T]):
    def __init__(self) -> None:
        self._data: list[T] = []

    def push(self, item: T) -> None:
        self._data.append(item)

    def pop(self) -> T:
        return self._data.pop()
```

---

## Context Variables (PEP 567): async-safe "Thread Locals"

`threading.local()` stores per-thread state. For async code, you need per-*task* state. `contextvars.ContextVar` provides this:

```python
from contextvars import ContextVar

request_id: ContextVar[str] = ContextVar("request_id", default="none")

async def handle_request(id: str):
    token = request_id.set(id)    # set for this task's context
    try:
        await process()
    finally:
        request_id.reset(token)   # restore previous value

async def process():
    print(request_id.get())       # sees THIS task's value, not other tasks'

# In FastAPI middleware:
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request_id.set(str(uuid.uuid4()))
        try:
            return await call_next(request)
        finally:
            request_id.reset(token)
```

`asyncio.create_task()` automatically copies the current context — child tasks inherit the parent's context values but can't affect the parent's context.

```python
# Quick reference:
request_id: ContextVar[str] = ContextVar("request_id", default="none")

token = request_id.set("req-123")  # Set (returns a token for reset)
request_id.get()                   # "req-123"
request_id.get("fallback")         # "fallback" if not set
request_id.reset(token)            # Reset to previous value
```

**structlog** uses `contextvars` internally — this is why request IDs propagate across all async boundaries automatically in the middleware pattern from Module 7.

---

## Free-Threaded Python (PEP 703, Python 3.13+)

The experimental GIL-free build (`python3.13t`) removes the global lock and replaces it with:

- **Per-object reference counting** with atomic operations (no GIL needed)
- **Biased reference counting**: objects accessed mostly from one thread use non-atomic increments for that thread; cross-thread access uses atomic ops
- **Stop-the-world GC pauses** for cyclic collection (similar to JVM's GC)

```bash
python3.13t --version         # free-threaded build
python3.13t -c "import sys; print(sys._is_gil_enabled())"  # False
```

**Current state (2026)**: most pure Python code works. Many C extensions need updates. The `threading` module now provides actual parallelism. Performance for single-threaded code may regress ~10% due to atomic refcount operations.

**Interview answer**: "I'm aware of free-threaded Python (PEP 703). It removes the GIL, enabling true thread-level parallelism. It's available experimentally in 3.13+ but not production-ready yet — C extensions need to be thread-safe, and the ecosystem is still catching up. For now, the standard approach is asyncio for IO-bound work and multiprocessing for CPU-bound work."

---

## Key Takeaways

- Descriptors (`__get__`/`__set__`) power `property`, `classmethod`, `staticmethod`, and ORMs. Data descriptors take priority over instance `__dict__`; non-data descriptors don't.
- `super()` follows the MRO of the concrete instance, not just the immediate parent — essential for cooperative multiple inheritance.
- `import` uses `sys.modules` as a cache — second import is free, circular imports get partial modules.
- `__init_subclass__` is the simpler alternative to metaclasses for plugin registration and subclass enforcement.
- `ContextVar` is the async-safe replacement for `threading.local()` — child tasks inherit but can't affect parent context.
- Free-threaded Python 3.13+ is real and available experimentally — watch for C extension compatibility as the ecosystem catches up.
