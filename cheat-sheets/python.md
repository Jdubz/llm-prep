---
title: "Python Quick Reference"
---

# Conventions

- **Naming**: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants
- **Type hints**: `from __future__ import annotations` at top of every file
- **Style**: PEP 8, 4-space indent, `black` formatter, `ruff` linter
- **Imports**: stdlib → third-party → local, one per line

# str

```python
s.split(",")          # ["a","b","c"]
",".join(lst)         # "a,b,c"
s.strip()             # trim whitespace
s.startswith("x")     # bool
s.replace("a", "b")   # new string
f"{name!r}: {val:.2f}" # f-string formatting
s[1:4]                # slice (start:stop)
s[::-1]               # reverse
```

# list

```python
lst.append(x)         # add to end
lst.pop()             # remove last (pop(i) by index)
lst.sort(key=fn)      # in-place sort
sorted(lst, key=fn)   # returns new list
lst[::2]              # every other element
[x**2 for x in lst if x > 0]  # comprehension
```

# dict

```python
d.get(k, default)     # safe lookup
d.setdefault(k, [])   # get or set default
d.items()             # key-value pairs
d.keys() / d.values()
d | other             # merge (3.9+)
{k: v for k, v in items if v}  # comprehension
del d[k]              # remove key
```

# set

```python
s.add(x)              # add element
s.discard(x)          # remove if present (no error)
s | t                 # union
s & t                 # intersection
s - t                 # difference
{x for x in lst}      # set comprehension
```

# tuple

```python
a, b, c = (1, 2, 3)           # unpacking
first, *rest = iterable        # star unpacking
from collections import namedtuple
Point = namedtuple("Point", ["x", "y"])
```

# collections

```python
from collections import Counter, defaultdict, deque

# Counter — count hashable elements
c = Counter("abracadabra")   # Counter({'a': 5, 'b': 2, ...})
c.most_common(2)             # [('a', 5), ('b', 2)]
c["z"]                       # 0 (missing keys default to 0)
c1 + c2                      # add counts
c1 - c2                      # subtract (drops <= 0)

# defaultdict — dict with auto-initialized values
graph = defaultdict(list)
graph["a"].append("b")       # no KeyError, auto-creates []
freq = defaultdict(int)
freq["x"] += 1               # auto-creates 0

# deque — O(1) append/pop both ends
dq = deque([1, 2, 3])
dq.appendleft(0)             # [0, 1, 2, 3]
dq.pop()                     # 3
dq.popleft()                 # 0
dq.rotate(1)                 # rotate right
deque(maxlen=N)              # bounded: auto-drops oldest
```

# Common Builtins

```python
len(x)                    # length
range(start, stop, step)  # lazy int sequence
enumerate(it, start=0)    # index-value pairs
zip(a, b, strict=True)    # pair elements
map(fn, it) / filter(fn, it)
any(it) / all(it)         # short-circuit bool
sorted(it, key=fn, reverse=True)
isinstance(x, (int, str)) # type check
```

# Comprehensions

```python
[expr for x in it if cond]       # list
{k: v for x in it}               # dict
{expr for x in it}               # set
(expr for x in it)               # generator (lazy)
```

# Error Handling

```python
try:
    risky()
except (ValueError, KeyError) as e:
    handle(e)
except Exception:
    log(); raise          # re-raise
else:
    on_success()          # no exception
finally:
    cleanup()             # always runs
```
