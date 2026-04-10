---
title: "Python Quick Reference"
---

# Conventions

- **Naming**: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants
- **Type hints**: `from __future__ import annotations` at top of every file
- **Style**: PEP 8, 4-space indent, `black` formatter, `ruff` linter
- **Imports**: stdlib → third-party → local, one per line

# str

All string methods are **non-mutating** — strings are immutable.

```python
s.length                      # ✗ use len(s)

# Search — all O(n)
s.startswith("x")             # -> bool, also takes tuple: s.startswith(("a", "b"))
s.endswith(".py")             # -> bool
"x" in s                     # -> bool, substring check (preferred over s.find)
s.find("x")                  # -> int, first index or -1 (no exception)
s.index("x")                 # -> int, first index or raises ValueError
s.rfind("x")                 # -> int, last index or -1
s.count("x")                 # -> int, non-overlapping occurrences

# Extract
s[1:4]                        # slice [start:stop), negative ok
s[::-1]                       # reverse string
s[-3:]                        # last 3 chars

# Split & Join
s.split(",")                  # -> list[str], split on separator
s.split(",", maxsplit=2)      # limit splits
s.rsplit(",", maxsplit=1)     # split from right (useful for "path/to/file.ext")
s.splitlines()                # split on \n, \r\n, \r
s.partition("=")              # -> (before, sep, after), single split as tuple
",".join(lst)                 # join list with separator

# Transform
s.strip()                     # strip whitespace both ends
s.lstrip() / s.rstrip()       # strip one end
s.strip(".,!")                # strip specific chars
s.replace("a", "b")           # all occurrences
s.replace("a", "b", 1)        # limit to 1 replacement
s.upper() / s.lower()         # case conversion
s.title() / s.capitalize()    # "hello world" → "Hello World" / "Hello world"
s.casefold()                  # aggressive lowercase (better than lower for comparison)
s.ljust(10) / s.rjust(10)     # pad to width
s.zfill(5)                    # zero-pad: "42" → "00042"
s.center(20, "-")             # center with fill char

# Test
s.isdigit() / s.isalpha() / s.isalnum()
s.isspace()                   # whitespace only
s.isupper() / s.islower()

# Format
f"{name!r}: {val:.2f}"        # f-string: repr, float precision
f"{val:>10}"                  # right-align in 10 chars
f"{val:,}"                    # thousands separator: 1,234,567
f"{pct:.1%}"                  # percentage: 0.156 → "15.6%"
f"{n:08b}"                    # binary with zero-pad: "00001010"

# Encode
s.encode("utf-8")             # -> bytes
b.decode("utf-8")             # -> str
```

# list

**Gotcha**: `.sort()` is in-place and returns `None`. Use `sorted()` for a new list.

```python
len(lst)                       # O(1)

# Add — mutating
lst.append(x)                  # O(1) amortized, add to end
lst.extend(iterable)           # O(k), add multiple
lst.insert(i, x)               # O(n), insert at index (shifts elements)
lst += [x]                     # same as extend for lists

# Remove — mutating
lst.pop()                      # O(1), remove and return last
lst.pop(i)                     # O(n), remove and return at index
lst.remove(x)                  # O(n), remove first occurrence (ValueError if missing)
del lst[i]                     # O(n), remove by index
del lst[1:3]                   # remove slice
lst.clear()                    # O(n), remove all

# Search — O(n)
x in lst                       # -> bool, membership test
lst.index(x)                   # -> int, first index (ValueError if missing)
lst.index(x, start, stop)      # search in range
lst.count(x)                   # -> int, occurrences

# Sort
lst.sort(key=fn)               # in-place, stable, O(n log n). Returns None!
lst.sort(key=fn, reverse=True) # descending
sorted(lst, key=fn)            # -> new list. Does NOT mutate
# Multi-key sort: sort by age desc, then name asc
sorted(people, key=lambda p: (-p.age, p.name))

# Copy
lst.copy()                     # shallow copy (same as lst[:])
lst[:]                         # shallow copy
import copy; copy.deepcopy(lst) # deep copy (nested objects)

# Transform
lst.reverse()                  # in-place. Returns None
list(reversed(lst))            # -> new list, reversed
[x**2 for x in lst if x > 0]  # list comprehension
lst[::2]                       # every other element
lst[1:4]                       # slice (shallow copy)

# Unpack
a, b, c = [1, 2, 3]           # exact unpack
first, *rest = [1, 2, 3, 4]   # star unpack: first=1, rest=[2,3,4]
*init, last = [1, 2, 3, 4]    # star unpack: init=[1,2,3], last=4
```

# dict

Ordered by insertion (Python 3.7+). O(1) average get/set/delete.

```python
d = {}                          # empty dict
d = {"a": 1, "b": 2}
d = dict(a=1, b=2)              # keyword construction
d = dict(zip(keys, values))     # from parallel lists

# Access
d["key"]                        # raises KeyError if missing!
d.get("key")                    # -> value or None (no exception)
d.get("key", default)           # -> value or default

# Modify
d["key"] = val                  # set or overwrite
d.setdefault("key", [])         # get, or set to default and return it
d.update(other)                 # merge other into d (overwrites)
d |= other                     # merge (3.9+), same as update
d | other                       # -> new merged dict (3.9+), d unchanged

# Remove
del d["key"]                    # raises KeyError if missing
d.pop("key")                    # -> value, raises KeyError
d.pop("key", default)           # -> value or default (no exception)
d.popitem()                     # -> (key, value), last inserted (LIFO)
d.clear()                       # remove all

# Iterate
d.keys()                        # -> dict_keys view (set-like)
d.values()                      # -> dict_values view
d.items()                       # -> dict_items view of (key, value) tuples
for k, v in d.items(): ...      # unpack during iteration

# Comprehension
{k: v for k, v in items if v}   # dict comprehension
{v: k for k, v in d.items()}    # invert dict
```

# set

Unordered. O(1) average add/discard/membership. Elements must be hashable.

```python
s = set()                       # empty set (NOT {}, that's a dict)
s = {1, 2, 3}
s = set(iterable)               # from iterable

# Modify
s.add(x)                        # O(1), no-op if exists
s.discard(x)                    # O(1), no-op if missing
s.remove(x)                     # O(1), KeyError if missing
s.pop()                          # remove and return arbitrary element
s.clear()

# Operators — all return new sets
s | t                           # union (also s.union(t))
s & t                           # intersection
s - t                           # difference (in s but not t)
s ^ t                           # symmetric difference (in one but not both)

# Test
s <= t                          # subset (also s.issubset(t))
s >= t                          # superset (also s.issuperset(t))
s.isdisjoint(t)                 # no overlap

# Frozen (immutable, hashable — usable as dict key or set element)
fs = frozenset([1, 2, 3])
```

# tuple / namedtuple / dataclass

```python
# tuple — immutable sequence
t = (1, 2, 3)
t = (1,)                        # single-element tuple (trailing comma!)
a, b, c = t                     # unpack
first, *rest = t                # star unpack

# namedtuple — lightweight immutable struct
from collections import namedtuple
Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
p.x                             # attribute access
p._asdict()                     # -> dict
p._replace(x=10)                # -> new Point (immutable)

# dataclass — mutable struct with type hints (prefer for interview code)
from dataclasses import dataclass, field

@dataclass
class File:
    name: str
    size: int
    tags: list[str] = field(default_factory=list)  # mutable default!

@dataclass(frozen=True)          # immutable, hashable
class Point:
    x: float
    y: float

@dataclass(order=True)           # enables <, >, <=, >=
class Task:
    priority: int
    name: str
```

# collections

```python
from collections import Counter, defaultdict, deque, OrderedDict

# Counter — count hashable elements
c = Counter("abracadabra")       # Counter({'a': 5, 'b': 2, ...})
c = Counter(words)               # count from iterable
c.most_common(3)                 # -> [(elem, count), ...] top 3
c["z"]                           # 0 (missing keys default to 0)
c.total()                        # sum of all counts (3.10+)
c.update(more_items)             # add counts from iterable
c.subtract(other)                # subtract counts
c1 + c2                          # add counts
c1 - c2                          # subtract (drops <= 0)
c1 & c2                          # min of each
c1 | c2                          # max of each
+c                               # drop zero/negative counts
list(c.elements())               # expand: ['a','a','a','b','b',...]

# defaultdict — dict with auto-initialized values
graph = defaultdict(list)
graph["a"].append("b")           # no KeyError, auto-creates []
freq = defaultdict(int)
freq["x"] += 1                   # auto-creates 0
nested = defaultdict(lambda: defaultdict(int))  # nested default

# deque — O(1) append/pop both ends (list is O(n) for left ops)
dq = deque([1, 2, 3])
dq.append(4)                    # right end
dq.appendleft(0)                # left end
dq.pop()                         # right end
dq.popleft()                    # left end → this is the BFS workhorse
dq.rotate(1)                    # rotate right (negative = left)
dq.extend(iterable)             # right end
dq.extendleft(iterable)         # left end (reverses order)
deque(maxlen=N)                  # bounded: auto-drops oldest on overflow
```

# heapq — Min-Heap (Interview Critical)

Python only has a **min-heap**. For max-heap, negate values.

```python
import heapq

# Build
h = []                           # start with empty list
heapq.heappush(h, val)           # O(log n)
heapq.heappop(h)                 # O(log n), returns smallest
h[0]                             # O(1), peek at smallest (don't pop)
heapq.heapify(lst)               # O(n), convert list to heap in-place

# Top K
heapq.nlargest(k, it, key=fn)   # O(n log k), top k largest
heapq.nsmallest(k, it, key=fn)  # O(n log k), top k smallest

# Max-heap trick — negate values
heapq.heappush(h, -val)
-heapq.heappop(h)                # get original value back

# Tuple comparison (for priority queues)
heapq.heappush(h, (priority, tiebreak, item))
# Compares element-by-element: priority first, then tiebreak

# Merge sorted iterables
heapq.merge(sorted1, sorted2)    # -> iterator, O(1) memory

# Classic: running median with two heaps
# small = max-heap (negated), large = min-heap
```

# bisect — Binary Search on Sorted Lists

```python
import bisect

bisect.bisect_left(a, x)         # -> index where x would go (before existing x)
bisect.bisect_right(a, x)        # -> index where x would go (after existing x)
bisect.insort_left(a, x)         # insert x in sorted order (O(n) due to shift)
bisect.insort_right(a, x)

# Find leftmost value >= target
i = bisect.bisect_left(a, target)
found = i < len(a) and a[i] == target

# Count occurrences of x in sorted list
lo = bisect.bisect_left(a, x)
hi = bisect.bisect_right(a, x)
count = hi - lo
```

# itertools

```python
import itertools

# Infinite
itertools.count(start=0, step=1)        # 0, 1, 2, 3, ...
itertools.cycle(iterable)               # a, b, c, a, b, c, ...
itertools.repeat(x, times=None)         # x, x, x, ... (or n times)

# Combinatorics
itertools.product("AB", "12")           # ('A','1'), ('A','2'), ('B','1'), ('B','2')
itertools.permutations("ABC", r=2)      # all 2-length orderings
itertools.combinations("ABCD", r=2)     # all 2-length subsets (no repeats)
itertools.combinations_with_replacement("AB", r=2)

# Chain & group
itertools.chain(a, b)                   # concatenate iterables
itertools.chain.from_iterable([[1,2],[3]]) # flatten one level
itertools.groupby(sorted_it, key=fn)    # group consecutive items (MUST be sorted)
itertools.islice(it, start, stop, step) # slice an iterator
itertools.zip_longest(a, b, fillvalue=0) # zip with fill for shorter

# Accumulate
itertools.accumulate([1,2,3,4])         # running sum: 1, 3, 6, 10
itertools.accumulate(lst, func=max)     # running max
```

# functools

```python
from functools import lru_cache, cache, reduce, partial, total_ordering

# Memoization — critical for DP
@lru_cache(maxsize=128)          # bounded cache (LRU eviction)
def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)

@cache                           # unbounded cache (3.9+)
def expensive(x): ...

# Reduce
reduce(lambda acc, x: acc + x, [1,2,3,4], 0)  # -> 10

# Partial application
from functools import partial
int_base2 = partial(int, base=2)
int_base2("1010")                # -> 10

# Auto-generate comparison operators
@total_ordering
class Task:
    def __eq__(self, other): return self.priority == other.priority
    def __lt__(self, other): return self.priority < other.priority
    # __le__, __gt__, __ge__ auto-generated
```

# Sorting Patterns (Interview Essential)

```python
# Basic
sorted(lst)                              # ascending
sorted(lst, reverse=True)                # descending

# Key function
sorted(words, key=len)                   # by length
sorted(words, key=str.lower)             # case-insensitive
sorted(files, key=lambda f: f.size)      # by attribute

# Multi-key: sort by size desc, then name asc
sorted(files, key=lambda f: (-f.size, f.name))

# Stable sort — equal elements keep original order
# Python's sort is Timsort (stable). You can sort twice:
lst.sort(key=lambda x: x.name)           # secondary key first
lst.sort(key=lambda x: x.priority)       # primary key second (stable preserves name order)

# Custom comparator (for complex ordering)
from functools import cmp_to_key
def compare(a, b):
    if a.score != b.score: return b.score - a.score  # desc
    return -1 if a.name < b.name else 1               # asc
sorted(items, key=cmp_to_key(compare))
```

# Common Builtins

```python
len(x)                            # O(1) for list, dict, set, str
range(start, stop, step)          # lazy int sequence [start, stop)
enumerate(it, start=0)            # -> (index, value) pairs
zip(a, b)                         # pair elements (stops at shorter)
zip(a, b, strict=True)            # raise if different lengths (3.10+)
zip(*matrix)                      # transpose: zip(*[[1,2],[3,4]]) → [(1,3),(2,4)]
map(fn, it)                       # lazy map
filter(fn, it)                    # lazy filter (None = truthy filter)
any(it)                           # True if any truthy (short-circuits)
all(it)                           # True if all truthy (short-circuits)
sum(it, start=0)                  # sum with optional start
min(it, key=fn, default=val)      # min with key and default for empty
max(it, key=fn, default=val)
abs(x)                            # absolute value
divmod(a, b)                      # -> (quotient, remainder)
pow(base, exp, mod=None)          # modular exponentiation: pow(2, 10, 1000)
isinstance(x, (int, str))         # type check (tuple for multiple)
id(x)                             # object identity (memory address)
hash(x)                           # hash value (for hashable objects)
vars(obj)                         # -> __dict__ of object
dir(obj)                          # list attributes/methods
type(x)                           # -> type object
```

# Comprehensions

```python
[expr for x in it if cond]              # list
{k: v for x in it}                      # dict
{expr for x in it}                      # set
(expr for x in it)                      # generator (lazy, single-pass)

# Nested
[(x, y) for x in a for y in b]          # cartesian product
[cell for row in matrix for cell in row] # flatten

# Walrus operator (:=) in comprehension
[y for x in data if (y := expensive(x)) > 0]  # compute once, filter + keep
```

# Generators & Iterators

```python
# Generator function — yields values lazily
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

gen = fibonacci()
next(gen)                        # 0
next(gen)                        # 1
list(itertools.islice(gen, 10))  # first 10

# Generator expression
squares = (x**2 for x in range(1000000))  # lazy, O(1) memory

# yield from — delegate to sub-generator
def flatten(nested):
    for item in nested:
        if isinstance(item, list):
            yield from flatten(item)
        else:
            yield item
```

# Error Handling

```python
try:
    risky()
except (ValueError, KeyError) as e:
    handle(e)
except Exception:
    log(); raise                 # re-raise original exception
else:
    on_success()                 # only if NO exception
finally:
    cleanup()                    # always runs

# Custom exception
class AppError(Exception):
    def __init__(self, message: str, code: int = 500):
        super().__init__(message)
        self.code = code

# EAFP (Easier to Ask Forgiveness) — Pythonic pattern
try:
    val = d[key]
except KeyError:
    val = default
# vs. LBYL: if key in d: val = d[key]
```

# Classes & OOP

```python
class Animal:
    species_count: int = 0               # class variable

    def __init__(self, name: str) -> None:
        self.name = name                 # instance variable
        Animal.species_count += 1

    def speak(self) -> str:              # instance method
        return f"{self.name} speaks"

    @classmethod
    def from_dict(cls, d: dict) -> "Animal":  # alternate constructor
        return cls(d["name"])

    @staticmethod
    def is_valid_name(name: str) -> bool:     # no self/cls
        return len(name) > 0

    @property
    def upper_name(self) -> str:         # computed property
        return self.name.upper()

    def __repr__(self) -> str:           # developer string
        return f"Animal({self.name!r})"

    def __str__(self) -> str:            # user-friendly string
        return self.name

# Dunder methods for interviews
__len__      # len(obj)
__getitem__  # obj[key]
__setitem__  # obj[key] = val
__contains__ # x in obj
__iter__     # for x in obj
__eq__       # obj == other
__lt__       # obj < other (enables sorting)
__hash__     # hash(obj) — must match __eq__
__enter__    # with obj: (context manager)
__exit__     # with obj: (cleanup)
```

# Context Managers

```python
# Built-in
with open("file.txt") as f:
    data = f.read()              # file auto-closed

# Custom with contextlib
from contextlib import contextmanager

@contextmanager
def timer(label: str):
    start = time.monotonic()
    yield
    elapsed = time.monotonic() - start
    print(f"{label}: {elapsed:.3f}s")

with timer("search"):
    results = search(query)
```

# Type Hints

```python
from __future__ import annotations
from typing import Optional, Union, TypeVar, Protocol, TypeAlias

# Basic
x: int = 5
name: str = "hello"
items: list[str] = []
mapping: dict[str, int] = {}
coords: tuple[float, float] = (1.0, 2.0)
var_tuple: tuple[int, ...] = (1, 2, 3)    # variable-length tuple

# Optional / Union
val: int | None = None                     # preferred (3.10+)
val: str | int = "hello"                   # union
val: Optional[int] = None                  # older style

# Callable
from typing import Callable
fn: Callable[[int, str], bool]             # (int, str) -> bool

# Generic
T = TypeVar("T")
def first(items: list[T]) -> T: return items[0]

# Protocol (structural typing — like interfaces)
class Drawable(Protocol):
    def draw(self) -> None: ...

# TypeAlias
UserId: TypeAlias = str
Graph: TypeAlias = dict[str, list[str]]
```

# File I/O & pathlib

```python
from pathlib import Path

# Path operations
p = Path("dir/file.txt")
p.parent                         # Path("dir")
p.name                           # "file.txt"
p.stem                           # "file"
p.suffix                         # ".txt"
p.with_suffix(".md")             # Path("dir/file.md")
p.resolve()                      # absolute path
p.exists() / p.is_file() / p.is_dir()

# Read/write
p.read_text(encoding="utf-8")    # -> str
p.write_text(content)            # -> int (bytes written)
p.read_bytes()                   # -> bytes
p.write_bytes(data)

# Directory operations
p.mkdir(parents=True, exist_ok=True)
p.iterdir()                      # -> iterator of child Paths
list(p.glob("*.py"))             # glob pattern
list(p.rglob("*.py"))            # recursive glob
p.unlink()                       # delete file
```

# hashlib & uuid

```python
import hashlib
import uuid

# Hashing (common in Dropbox file problems)
hashlib.sha256(data_bytes).hexdigest()    # -> "a1b2c3..."
hashlib.md5(data_bytes).hexdigest()       # faster, not cryptographic

# For strings: encode first
hashlib.sha256("hello".encode()).hexdigest()

# UUID
str(uuid.uuid4())                # -> "a1b2c3d4-..." random UUID
```

# re — Regular Expressions

```python
import re

re.search(r"pattern", s)         # -> Match | None, first match anywhere
re.match(r"pattern", s)          # -> Match | None, must match at START
re.fullmatch(r"pattern", s)      # -> Match | None, must match entire string
re.findall(r"pattern", s)        # -> list[str], all non-overlapping matches
re.finditer(r"pattern", s)       # -> iterator of Match objects
re.sub(r"pat", repl, s)          # -> str, replace all matches
re.split(r"pat", s)              # -> list[str], split on pattern

# Groups
m = re.search(r"(\d+)-(\w+)", "123-abc")
m.group(0)                       # "123-abc" (full match)
m.group(1)                       # "123" (first group)
m.groups()                       # ("123", "abc")

# Named groups
m = re.search(r"(?P<num>\d+)", "123")
m.group("num")                   # "123"

# Common patterns
r"\d+"           # digits
r"\w+"           # word chars (letters, digits, underscore)
r"\s+"           # whitespace
r"[a-zA-Z]+"     # letters only
r"^...$"         # anchor start/end
r"(?:...)"       # non-capturing group
```

# threading & concurrent.futures

```python
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Thread-safe operations
lock = threading.Lock()
with lock:
    shared_data.append(item)     # protected by lock

# ThreadPoolExecutor — prefer over raw threads
with ThreadPoolExecutor(max_workers=5) as pool:
    futures = [pool.submit(fetch, url) for url in urls]
    for future in as_completed(futures):
        result = future.result()  # raises if function raised

# Map pattern (simpler when all tasks are same function)
with ThreadPoolExecutor(max_workers=5) as pool:
    results = list(pool.map(fetch, urls))  # ordered results

# Thread-safe queue
from queue import Queue
q: Queue[str] = Queue()
q.put(item)                      # blocks if full (maxsize)
item = q.get()                   # blocks if empty
q.task_done()                    # signal item processed
q.join()                         # block until all items done
```

# math & numbers

```python
import math

math.inf / -math.inf             # infinity (useful for min/max init)
math.floor(3.7)                  # 3
math.ceil(3.2)                   # 4
math.sqrt(x)                     # square root
math.log(x) / math.log2(x)      # natural / base-2 log
math.gcd(a, b)                   # greatest common divisor
math.lcm(a, b)                   # least common multiple (3.9+)
math.isclose(a, b, rel_tol=1e-9) # float comparison
math.comb(n, k)                  # n choose k
math.perm(n, k)                  # permutations
math.factorial(n)
math.pi / math.e

# Integer division
7 // 2                            # 3 (floor division)
7 % 2                             # 1 (modulo)
divmod(7, 2)                      # (3, 1)

# Gotcha: Python floor division rounds toward -inf
-7 // 2                           # -4 (not -3!)
-7 % 2                            # 1 (not -1!)
```

# json & datetime

```python
import json
from datetime import datetime, timedelta, timezone

# JSON
json.dumps(obj)                   # -> str (serialize)
json.dumps(obj, indent=2)        # pretty-print
json.loads(s)                     # -> dict/list (deserialize)
json.dumps(obj, default=str)      # fallback for non-serializable types

# datetime
datetime.now()                    # local time
datetime.now(timezone.utc)        # UTC (preferred)
datetime.fromisoformat("2026-04-09T10:30:00")
dt.isoformat()                    # -> "2026-04-09T10:30:00"
dt.timestamp()                    # -> float, Unix epoch seconds
datetime.fromtimestamp(ts)

# timedelta
td = timedelta(days=7, hours=3)
future = dt + td
diff = dt1 - dt2                  # -> timedelta
diff.total_seconds()              # -> float

# time (for performance)
import time
time.monotonic()                  # monotonic clock (for duration measurement)
time.time()                       # wall clock (Unix epoch seconds)
time.sleep(1.5)                   # sleep seconds
```

# Interview Patterns Cheat Sheet

```python
# ── BFS (shortest path, level-order) ─────────────
from collections import deque
def bfs(graph, start):
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

# ── DFS (traversal, cycle detection) ─────────────
def dfs(graph, start):
    visited = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in visited: continue
        visited.add(node)
        for neighbor in graph[node]:
            stack.append(neighbor)

# ── Sliding window ───────────────────────────────
def max_window(arr, k):
    window = defaultdict(int)
    left = result = 0
    for right in range(len(arr)):
        window[arr[right]] += 1
        while not valid(window):
            window[arr[left]] -= 1
            if window[arr[left]] == 0: del window[arr[left]]
            left += 1
        result = max(result, right - left + 1)
    return result

# ── Binary search ────────────────────────────────
def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target: lo = mid + 1
        else: hi = mid - 1
    return -1  # or lo for insertion point

# ── Union-Find ───────────────────────────────────
class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py: return False
        if self.rank[px] < self.rank[py]: px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]: self.rank[px] += 1
        return True

# ── Top K with heap ──────────────────────────────
def top_k(items, k, key=lambda x: x):
    return heapq.nlargest(k, items, key=key)

# ── Trie (prefix tree) ──────────────────────────
class TrieNode:
    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()
    def insert(self, word):
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True
    def search(self, word) -> bool:
        node = self._find(word)
        return node is not None and node.is_end
    def starts_with(self, prefix) -> bool:
        return self._find(prefix) is not None
    def _find(self, s):
        node = self.root
        for ch in s:
            if ch not in node.children: return None
            node = node.children[ch]
        return node
```
