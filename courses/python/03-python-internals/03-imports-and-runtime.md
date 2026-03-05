# 03 – Imports, Bytecode, and Runtime

## Python Bytecode and the CPython VM

CPython compiles Python source to platform-independent bytecode before execution. Bytecode is cached in `__pycache__/*.pyc` (keyed by source hash + Python version).

### Inspecting Bytecode with `dis`

```python
import dis

def add(a, b):
    return a + b

dis.dis(add)
# RESUME           0
# LOAD_FAST        0 (a)
# LOAD_FAST        1 (b)
# BINARY_OP        0 (+)
# RETURN_VALUE
```

CPython is a **stack-based VM**. Instructions push/pop values from a per-frame evaluation stack. `LOAD_FAST` pushes a local variable; `BINARY_OP` pops two, pushes the result; `RETURN_VALUE` pops and exits.

**Why local variables are faster than globals**: `LOAD_FAST` accesses locals stored in a fixed-size C array indexed by position. `LOAD_GLOBAL` performs a dictionary lookup.

### Key Opcodes Reference

```
LOAD_FAST     — push local variable onto stack
LOAD_GLOBAL   — push global / built-in
BINARY_OP     — pop two, push result
CALL          — call function
RETURN_VALUE  — pop and return
```

### Code Objects

Every function body compiles to a `code` object:

```python
def greet(name):
    prefix = "Hello"
    return f"{prefix}, {name}!"

c = greet.__code__
c.co_varnames    # ('name', 'prefix') — local variable names
c.co_consts      # (None, 'Hello') — compile-time constants
c.co_filename    # source file path
c.co_firstlineno # 1
c.co_argcount    # 1
c.co_stacksize   # max evaluation stack depth needed
```

### Adaptive Specialization (Python 3.11+)

The interpreter tracks the types observed at each bytecode instruction. After a few observations, it **rewrites the bytecode in-place** with specialized variants:

- `BINARY_OP` on two ints → `BINARY_OP_ADD_INT` (skips type dispatch)
- `LOAD_ATTR` on a known object → `LOAD_ATTR_INSTANCE_VALUE` (direct slot offset)
- `CALL` on a known C function → `CALL_BUILTIN_FAST`

This is "adaptive interpretation" — a limited form of JIT. No full compilation, but avoids repeated type dispatch for hot paths. PyPy and GraalPy take this further with true JIT.

```python
# How to see specialization in action (Python 3.12+):
import dis
def hot(x, y): return x + y
for _ in range(100): hot(1, 2)  # warm it up
dis.dis(hot, show_caches=True)  # see specialized cache entries
```

---

## Frame Objects and the Call Stack

Each function call creates a **frame object** holding:
- A reference to the code object
- The local variable array (fast locals — not a dict, a C array)
- The evaluation stack (values being operated on)
- The instruction pointer (current bytecode offset)
- A reference to the enclosing frame (parent call)

```python
import inspect

def inner():
    f = inspect.currentframe()
    print(f.f_locals)           # {'f': <frame>}
    print(f.f_code.co_name)     # 'inner'
    print(f.f_back.f_code.co_name)  # 'outer'

def outer():
    x = 42
    inner()

outer()
```

**Python 3.11 frame optimization**: frames used to be heap-allocated Python objects. Now they are C-stack-allocated by default and only "materialized" as Python objects when code actually inspects them (via `inspect`, `sys._getframe()`, etc.). This made function calls significantly faster.

### Tracebacks

Tracebacks are linked lists of frame snapshots. When an exception is raised, Python captures the frame chain:

```python
import traceback, sys

def foo():
    raise ValueError("oops")

try:
    foo()
except ValueError:
    tb = sys.exc_info()[2]     # the traceback object
    # tb.tb_frame -> foo's frame
    # tb.tb_next  -> next frame in chain (None at bottom)
    traceback.print_tb(tb)
```

---

## The Generator Protocol in Detail

A generator function (`yield` inside `def`) returns a **generator object** rather than executing. The generator object implements:

- `__iter__()` → returns self (it's its own iterator)
- `__next__()` → resumes execution until next `yield`, returns yielded value, raises `StopIteration` when done
- `.send(value)` → resumes and injects `value` as the result of the `yield` expression
- `.throw(exc)` → resumes and raises `exc` at the suspension point
- `.close()` → throws `GeneratorExit` at the suspension point (cleanup)

```python
def stateful_gen():
    print("start")
    x = yield 1           # yields 1 out; receives injected value when resumed
    print(f"got {x}")
    y = yield 2
    print(f"got {y}")

g = stateful_gen()

next(g)         # "start" → suspends at yield 1, returns 1
g.send(42)      # "got 42" → suspends at yield 2, returns 2
g.send("hi")    # "got hi" → StopIteration (generator exhausted)
```

**How `asyncio` uses `.throw()`**: when you call `task.cancel()`, asyncio calls `.throw(CancelledError)` on the underlying coroutine. That's why `try/except CancelledError` works inside `async def` — the exception is injected at the current `await` point.

```python
import asyncio

async def my_coro():
    try:
        await asyncio.sleep(100)
    except asyncio.CancelledError:
        print("Cleaned up before cancel")
        raise  # re-raise is important — don't swallow CancelledError

async def main():
    task = asyncio.create_task(my_coro())
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Task was cancelled")

asyncio.run(main())
```

### Generator-Based Coroutines (Historical Context)

Before `async def` (Python 3.5), coroutines were generators decorated with `@asyncio.coroutine` and used `yield from` to delegate to sub-coroutines. `async def` / `await` are syntactic sugar for the same mechanism — native coroutines just implement the generator protocol internally without being exposed as generators.

```python
# Python 3.3-3.4 style (deprecated, removed in 3.11)
@asyncio.coroutine
def old_fetch(url):
    response = yield from aiohttp.request('GET', url)
    return response

# Modern equivalent
async def new_fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

---

## Interview Questions

### Conceptual

**1. Why does Python need a garbage collector if it already has reference counting?**

Reference counting can't handle cycles. Two objects that reference each other will never reach refcount 0, even after all external references are removed. The cyclic GC finds and breaks these cycles. It only checks objects that can hold references (lists, dicts, class instances) — immutable atoms like ints and strings are never tracked by the cyclic GC.

**2. What is the GIL and why does it exist?**

A mutex protecting CPython's internal state, especially reference counts. Without it, concurrent refcount updates would cause use-after-free crashes. It prevents true CPU parallelism in threads; use `ProcessPoolExecutor` for CPU-bound work. It doesn't affect async I/O since asyncio is single-threaded. C extensions can explicitly release it.

**3. `a is b` vs `a == b` — when does `is` give unexpected results?**

`is` compares object identity (pointer). Small integers (-5 to 256) and some strings are cached/interned, so `is` returns `True` coincidentally. Outside the cache range, `is` returns `False` for equal values. Never use `is` for value comparison — only for `None`, `True`, `False` which are guaranteed singletons.

**4. Explain descriptor lookup order.**

Data descriptor (class) → instance `__dict__` → non-data descriptor (class). Data descriptors define `__set__`; non-data descriptors don't. `@property` with a setter is a data descriptor; a plain method is a non-data descriptor. This is why you can shadow a method by assigning to an instance attribute, but you can't shadow a `@property` with a setter.

**5. What does `super()` actually do?**

Returns a proxy that continues MRO traversal from the calling class's position in the MRO of the *actual instance's class*. In multiple inheritance, `super()` in class B doesn't necessarily call A (B's parent) — it calls whichever class follows B in the MRO of the concrete instance's class.

**6. When would you use `__slots__`?**

When creating large numbers of instances with a fixed set of attributes. Eliminates the per-instance `__dict__` (~200 bytes each), preventing dynamic attribute addition. Common in data-heavy apps (ORM row caching, ML feature objects, network packet models).

**7. What happens during `import foo`?**

Check `sys.modules` cache → find file via `sys.path` finders → execute module body → cache in `sys.modules` → bind name. Subsequent imports return the cached module object. Circular imports work because the partial module is already in `sys.modules` when the circular import is hit.

**8. Why does defining `__eq__` break hashability?**

Mutable equality semantics break the hash/equality contract (equal objects must have equal hashes, but if the object's state can change, hash would change too). Python enforces this by setting `__hash__ = None` when only `__eq__` is defined. You must explicitly provide `__hash__` to opt back in.

**9. How does task cancellation work in asyncio?**

`task.cancel()` calls `.throw(CancelledError)` on the underlying coroutine's generator. The `CancelledError` is raised at the current `await` point. Because `CancelledError` is a `BaseException` (not `Exception`) in Python 3.9+, generic `except Exception` handlers won't catch it — cancellation propagates correctly. Code that needs cleanup on cancellation should catch `CancelledError`, do cleanup, then re-raise.

**10. What is adaptive specialization in Python 3.11+?**

The interpreter tracks the types observed at each bytecode instruction. After a few observations, it rewrites the bytecode in-place with specialized variants (e.g., `BINARY_OP_ADD_INT` for integer addition). This avoids repeated type dispatch for hot code paths — a limited form of JIT that gives Python 3.11+ significant speedups without a full JIT compiler.

**11. How do `ContextVar` and `threading.local()` differ?**

`threading.local()` stores per-thread state. In async code, many coroutines share a single thread, so `threading.local()` would give all coroutines the same storage. `ContextVar` stores per-context (per-task) state. `asyncio.create_task()` copies the current context to the new task, so child tasks inherit parent values but changes don't affect the parent.

### Coding Challenges

**12. Implement a class that limits instances to 3:**

Override `__new__`, track instances with a class-level list, raise after limit.

**13. Write a descriptor that validates a value is positive on assignment:**

Define `__set__` with a `ValueError`, `__get__` to return from instance's `__dict__`.

**14. Demonstrate the MRO for a diamond inheritance — predict method call order:**

Given `D(B, C)`, `B(A)`, `C(A)`, show `D.__mro__` and which `method()` is called.

---

## Practice Exercises

The following exercises in `exercises.py` test concepts from this file. Each exercise has self-contained instructions and can be completed independently.

- **Exercise 8 — Fibonacci Iterator**: Implement a class-based iterator using `__iter__` and `__next__` with `StopIteration`. Tests the iterator protocol that underlies Python's `for` loop and is closely related to the generator protocol. (See: "The Generator Protocol in Detail" section above)
- **Exercise 9 — Generator with send()**: Implement `running_average()` as a generator that receives values via `.send()` and yields running averages. Tests the generator `.send()` protocol. (See: "The Generator Protocol in Detail" section above, specifically the `.send(value)` explanation)

---

## Key Takeaways

- CPython's VM is stack-based; bytecode is inspectable with `dis`. Python 3.11+ adapts bytecode to observed types at runtime (adaptive specialization).
- Frame objects hold local state per call; Python 3.11 lazily materializes them for speed.
- Generators expose `.send()` and `.throw()` — asyncio uses `.throw(CancelledError)` for task cancellation.
- `import` uses `sys.modules` as a cache — second import is free, circular imports get partial modules.
- `ContextVar` is the async-safe replacement for `threading.local()` in async frameworks — structlog uses it for request ID propagation.
- Free-threaded Python 3.13+ is real and available experimentally — watch for C extension compatibility.
- `pymalloc` is a three-tier arena allocator for objects <512 bytes — fast but can pin 256KB arenas even for a single surviving object.
