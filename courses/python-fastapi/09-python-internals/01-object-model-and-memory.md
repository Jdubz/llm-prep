# 01 – Object Model and Memory

## Everything Is a PyObject

Every Python value — integer, string, function, class, `None` — is a C struct:

```c
typedef struct _object {
    Py_ssize_t ob_refcnt;   // reference count
    PyTypeObject *ob_type;  // pointer to the type
} PyObject;
```

This has two consequences that show up in interviews:

**Everything has a type, including types:**
```python
type(42)       # <class 'int'>
type(int)      # <class 'type'>
type(type)     # <class 'type'>  — type is an instance of itself
type(object)   # <class 'type'>
isinstance(int, type)     # True — int is an instance of type
isinstance(type, object)  # True — everything inherits from object
```

**Identity vs equality:**
```python
# is compares ob_type pointer — same object in memory
# == calls __eq__ — same value

a = [1, 2, 3]
b = a
a is b   # True — same object

c = [1, 2, 3]
a is c   # False — different objects
a == c   # True — same value
```

---

## Memory Management: Reference Counting + Cyclic GC

Python uses **two complementary systems**. Most objects are freed by the first; reference cycles require the second.

### Reference Counting (Primary)

Every `PyObject` tracks how many references point to it (`ob_refcnt`). When the count hits 0, the object is immediately deallocated — no GC pause.

```python
import sys

x = [1, 2, 3]
sys.getrefcount(x)  # 2 — x itself + the getrefcount argument

y = x               # y is another reference
sys.getrefcount(x)  # 3

del y
sys.getrefcount(x)  # 2 again
```

**Benefit**: immediate deallocation, no pauses. **Cost**: every assignment/deletion touches a shared counter — this counter must be protected in multithreaded code (why the GIL exists).

### Cyclic GC (Secondary)

Reference counting cannot free cycles:

```python
a = []
b = [a]
a.append(b)   # a -> b -> a -> ...

del a, b
# Both still have refcount = 1 (each holds a ref to the other)
# They will never be freed by refcounting alone
```

CPython's cyclic GC (`gc` module) runs periodically to find and break these cycles. It only tracks objects that *can* hold references (lists, dicts, sets, class instances). Immutable atoms (ints, strings) are never tracked by the cyclic GC.

```python
import gc

gc.get_count()     # (gen0_objects, gen1_objects, gen2_objects)
gc.collect()       # force full collection — returns number of objects freed
gc.get_threshold() # (700, 10, 10) — default generation thresholds
gc.disable()       # turn off cyclic GC (dangerous — only if you manage cycles yourself)
gc.is_tracked(obj) # True if object is tracked by cyclic GC
```

**Generational model**: three generations. Gen 0 collects when it exceeds 700 objects. Gen 1 collects after 10 gen-0 collections. Gen 2 (oldest) after 10 gen-1 collections. Objects that survive a collection get promoted. Most objects die in gen 0.

### Memory Profiling

```python
import tracemalloc

tracemalloc.start()

# ... your code ...
data = [x for x in range(100_000)]

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:5]:
    print(stat)
# example: list.py:1: size=3.1 MiB, count=1, average=3.1 MiB
```

---

## The GIL (Global Interpreter Lock)

The GIL is a mutex that allows only one thread to execute Python bytecode at a time.

**Why it exists**: reference counts are on every object and must be updated atomically. Without the GIL, two threads could simultaneously decrement the same refcount and both see 0, freeing the object twice (use-after-free crash). The GIL makes refcount updates safe without per-object locks on every allocation.

```python
# This is NOT thread-safe even with the GIL:
counter = 0
def increment():
    global counter
    for _ in range(1_000_000):
        counter += 1  # 3 bytecodes: LOAD, ADD, STORE — GIL can switch between any two

# This IS safe — a single C-level dict method call is atomic under the GIL:
shared = {}
def update():
    shared.update({"key": "value"})
```

**What the GIL does NOT affect:**
- Async I/O — asyncio is single-threaded anyway
- I/O-bound threading — GIL is released during I/O operations
- C extensions — can release GIL for CPU work (numpy, hashlib do this)

**What the GIL prevents:**
- True CPU parallelism across Python threads
- Solution: `ProcessPoolExecutor` (separate process = separate GIL)

```python
import sys
sys.getswitchinterval()   # 0.005 (5ms) — how often GIL switches between threads
```

**GIL Quick Reference:**
```
Protects:   CPython internal state, reference counts
Released:   during I/O (network, disk), C extensions that call Py_BEGIN_ALLOW_THREADS
Impact on:  CPU-bound threads (no parallelism — use ProcessPoolExecutor)
No impact:  async I/O (single-threaded anyway)
Switch:     every 5ms (sys.getswitchinterval())
3.13+:      free-threaded build available (python3.13t), still experimental
```

**Python 3.13+**: experimental free-threaded build (`python3.13t`) disables the GIL globally, using per-object locking instead. Still experimental as of 2026.

---

## Small Integer Cache and String Interning

CPython pre-allocates integer objects for **-5 through 256** at startup. These are singletons.

```python
a = 100
b = 100
a is b   # True — same cached object (always)

a = 1000
b = 1000
a is b   # False — different objects (CPython detail, not guaranteed)

# NEVER use `is` for value comparison — only for:
x is None      # correct — None is always a singleton
x is True      # correct — True/False are singletons
x is y         # intentional identity check
```

**String interning**: strings that look like identifiers are often auto-interned. Force it with `sys.intern()` for strings used heavily as dict keys (lookup becomes pointer comparison).

```python
import sys
a = sys.intern("my_key")
b = sys.intern("my_key")
a is b   # True — same object, dict lookup is O(1) pointer compare

# Force interning for dict-key performance:
keys = [sys.intern(f"field_{i}") for i in range(1000)]
```

**Peephole optimizer — constant folding:**
```python
# These are the same object at runtime due to constant folding:
x = "hello" + "world"
y = "helloworld"
x is y   # True (optimizer combined them at compile time)
```

---

## The pymalloc Allocator

CPython doesn't call `malloc`/`free` directly for every small allocation. It has **pymalloc** — optimized for Python's allocation pattern (many small, short-lived objects).

### Three-Tier Architecture

```
Objects < 512 bytes  →  pymalloc (arena-based)
Objects >= 512 bytes →  system malloc
Large arrays/buffers →  mmap (direct from OS)
```

### pymalloc Structure

```
Arena (256 KB, aligned to 256KB boundary)
└── Pools (4 KB each, one size class per pool)
    └── Blocks (8, 16, 24, ... 512 bytes — multiples of 8)
```

- **Arena**: 256 KB chunk from the OS. CPython requests memory in arenas and never returns it to the OS until the entire arena is empty.
- **Pool**: 4 KB section within an arena. All blocks in a pool are the same size.
- **Block**: the actual allocation unit for a Python object.

**Why this is fast**: allocating a small object is just bumping a pointer within a pool. Freeing returns the block to the pool's free list — no system call.

**Why Python "leaks" memory (sort of)**: arenas are only returned to the OS when completely empty. A single surviving object can pin a 256 KB arena.

---

## `__slots__`

By default, every instance stores attributes in a `__dict__` (a hash table). `__slots__` replaces it with fixed C-level memory offsets:

```python
class Normal:
    def __init__(self, x, y): self.x = x; self.y = y

class Slotted:
    __slots__ = ("x", "y")
    def __init__(self, x, y): self.x = x; self.y = y

import sys
n = Normal(1, 2)
s = Slotted(1, 2)

hasattr(n, "__dict__")   # True
hasattr(s, "__dict__")   # False
s.z = 3                  # AttributeError — can't add arbitrary attributes

# Memory difference:
# Normal: ~48 bytes for object + ~200 bytes for __dict__ = ~248 bytes total
# Slotted: ~56 bytes total
```

Effects:
- No `__dict__` per instance (~200 bytes saved)
- `AttributeError` on any attr not in `__slots__`
- Can't use `weakref` unless `"__weakref__"` is in `__slots__`
- Parent must also use `__slots__` for full savings — if any base class doesn't, the subclass still gets `__dict__`

**When to use**: when creating large numbers of instances with a fixed set of attributes (ORM row caching, ML feature objects, network packet models). Pydantic v2 uses slots by default on models for performance.

---

## Weak References

A weak reference doesn't increment the reference count. The target can be GC'd even if weak references exist. After collection, the weak ref returns `None`.

```python
import weakref

ref = weakref.ref(obj)   # create weak reference
ref()                    # returns obj or None if collected

# Auto-cleanup dict: entries removed when values are GC'd
cache = weakref.WeakValueDictionary()

data = {"big": "payload"}
cache["key"] = data

cache["key"]   # {"big": "payload"}
del data
cache["key"]   # None — object was collected, key is auto-removed

# Weak set
seen = weakref.WeakSet()
seen.add(obj)
```

**Use cases**: caches where you don't want to prevent GC; observer patterns where observers shouldn't keep subjects alive.

---

## `__new__` vs `__init__`

`__new__` creates the instance. `__init__` initializes it. The flow: `MyClass(args)` → `MyClass.__new__(MyClass, args)` → if result is a MyClass instance → `result.__init__(args)`.

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance   # same object every time

    def __init__(self, value):
        self.value = value     # WARNING: called every instantiation even on cached instance

a = Singleton(1)
b = Singleton(2)
a is b     # True
a.value    # 2 — __init__ ran again on the existing instance

# Immutable subclass (must set value in __new__):
class PositiveInt(int):
    def __new__(cls, value):
        if value <= 0: raise ValueError("must be positive")
        return super().__new__(cls, value)
```

Override `__new__` for: singletons, immutable type subclasses (str/int subclasses must set value in `__new__` since `__init__` can't mutate them), returning instances of different types.

---

## Dunder Protocols

Python's operator overloading works through dunder methods called directly by the interpreter:

| Operation | Dunder Called |
|-----------|--------------|
| `x + y` | `x.__add__(y)`, then `y.__radd__(x)` if first returns `NotImplemented` |
| `x[key]` | `x.__getitem__(key)` |
| `len(x)` | `x.__len__()` |
| `for item in x` | `x.__iter__()`, repeated `x.__next__()` |
| `with x as y` | `x.__enter__()`, `x.__exit__(exc_type, exc_val, tb)` |
| `await x` | `x.__await__()` |
| `x(args)` | `x.__call__(args)` |
| `hash(x)` | `x.__hash__()` |
| `bool(x)` | `x.__bool__()`, falls back to `__len__() != 0` |
| `repr(x)` | `x.__repr__()` |

**Critical rule**: if you define `__eq__`, Python sets `__hash__ = None` automatically unless you also define `__hash__`. That makes the object unhashable — can't be used as a dict key or set member.

```python
class Bad:
    def __eq__(self, other): return True
    # __hash__ is now None

class Point:
    def __init__(self, x, y): self.x = x; self.y = y
    def __eq__(self, other): return (self.x, self.y) == (other.x, other.y)
    def __hash__(self): return hash((self.x, self.y))   # required!

{Bad()}    # TypeError: unhashable type
{Point(1, 2)}   # works
```

---

## Key Takeaways

- Every Python object is a `PyObject` with a refcount and a type pointer.
- Memory = reference counting (immediate, no pauses) + cyclic GC (periodic, handles cycles only).
- The GIL protects refcounts; it doesn't affect async I/O but blocks CPU thread parallelism.
- Small integers (-5 to 256) are cached singletons — never use `is` for value comparison.
- `pymalloc` is a three-tier arena allocator for objects <512 bytes — fast but can pin memory.
- `__slots__` trades dynamic attributes for ~4x lower memory per instance.
- Defining `__eq__` without `__hash__` makes objects unhashable.
- Weak references let you cache without preventing GC.
