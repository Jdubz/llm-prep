# 01 – Syntax, Types, and Patterns

Everything you need to know about Python syntax if you're coming from TypeScript/Node.js. Python will feel familiar in spirit but alien in syntax.

---

## 1. Environment & Tooling

### Virtual Environments (There Is No `node_modules`)

Python installs packages globally by default. Virtual environments are the equivalent of project-local `node_modules` — they isolate dependencies per project.

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate it (you MUST do this in every terminal session)
source .venv/bin/activate    # Linux/Mac
.venv\Scripts\activate       # Windows

# Now pip installs go into .venv/, not globally
pip install fastapi uvicorn

# Deactivate when done
deactivate
```

The `.venv/` directory is your `node_modules/`. Add it to `.gitignore`.

### Package Management

| Node.js        | Python Equivalent       |
|----------------|-------------------------|
| `package.json` | `pyproject.toml` or `requirements.txt` |
| `npm install`  | `pip install -r requirements.txt` |
| `npx`          | `uvx` (with `uv`) or `python -m` |
| `npm`          | `pip` (basic) or `uv` (fast, modern) |

```bash
# Install from requirements file
pip install -r requirements.txt

# Freeze current deps (like npm shrinkwrap)
pip freeze > requirements.txt

# uv is the modern alternative (much faster, like pnpm for Python)
pip install uv
uv pip install fastapi
```

### Running Code

```bash
python main.py               # Run a script
python -m pytest              # Run a module (like npx)
uvicorn app.main:app --reload # Run a FastAPI server (like nodemon)
```

---

## 2. Syntax Translation Guide

### The Basics

```python
# Variables — no let/const/var, just assign
name = "Alice"
count = 42
is_active = True           # True/False, not true/false

# None, not null/undefined
user = None                # Python has no undefined — only None

# Constants — convention only, ALL_CAPS (not enforced)
MAX_RETRIES = 3

# Blocks use indentation, not braces
if count > 10:
    print("big")
elif count > 5:            # elif, not else if
    print("medium")
else:
    print("small")

# Ternary — reads like English
status = "big" if count > 10 else "small"
# TS equivalent: const status = count > 10 ? "big" : "small"
```

### Strings

```python
# f-strings (like template literals)
name = "Alice"
greeting = f"Hello, {name}!"       # TS: `Hello, ${name}!`
calc = f"Result: {2 + 2}"          # expressions work too
formatted = f"Price: ${price:.2f}" # format specifiers (no TS equivalent)

# Multiline strings — triple quotes
query = """
    SELECT *
    FROM users
    WHERE active = true
"""

# Common string methods
"hello world".split()          # ["hello", "world"]
"hello world".startswith("he") # True
"  spaced  ".strip()           # "spaced"
", ".join(["a", "b", "c"])     # "a, b, c"
```

### Collections

```python
# Lists (arrays)
items = [1, 2, 3]
items.append(4)            # push
items.pop()                # pop (returns 4)
items[0]                   # index access
items[-1]                  # last element (no .at(-1) needed)
items[1:3]                 # slice → [2, 3] (start inclusive, end exclusive)
len(items)                 # length (not .length)

# Dicts (objects/Maps)
user = {"name": "Alice", "age": 30}
user["name"]               # "Alice" — KeyError if missing
user.get("name")           # "Alice" — None if missing (safe access)
user.get("role", "viewer") # default value if missing
"name" in user             # True (key existence check)
user.keys()                # dict_keys(["name", "age"])
user.values()              # dict_values(["Alice", 30])
user.items()               # dict_items([("name", "Alice"), ("age", 30)])

# Tuples (immutable arrays)
point = (10, 20)           # cannot be modified after creation
x, y = point              # destructuring (unpacking)

# Sets
tags = {"python", "fastapi", "async"}
tags.add("pydantic")
"python" in tags           # O(1) membership check
```

### Destructuring (Unpacking)

```python
# Tuple/list unpacking
first, second, third = [1, 2, 3]
first, *rest = [1, 2, 3, 4]       # first=1, rest=[2, 3, 4] (like ...rest)
_, _, third = [1, 2, 3]           # _ is convention for "don't care"

# Dict unpacking (like spread)
defaults = {"timeout": 30, "retries": 3}
config = {**defaults, "timeout": 60}  # {timeout: 60, retries: 3}

# Swapping
a, b = b, a
```

### Loops

```python
# for-in (iterates values, not indices — like for-of in JS)
for item in items:
    print(item)

# Need the index? Use enumerate
for i, item in enumerate(items):
    print(f"{i}: {item}")

# Iterate dict
for key, value in user.items():
    print(f"{key} = {value}")

# Range (like for(let i=0; i<10; i++))
for i in range(10):        # 0..9
    print(i)

for i in range(2, 10, 2):  # 2, 4, 6, 8 (start, stop, step)
    print(i)

# while
while count > 0:
    count -= 1             # no count-- in Python

# There is no do-while in Python
```

### Truthiness

Python truthiness is similar to JS but not identical:

```python
# Falsy values: None, False, 0, 0.0, "", [], {}, set()
# Everything else is truthy

if not items:              # empty list/dict/string check
    print("empty")

# and/or/not instead of &&/||/!
if name and len(name) > 0:
    print(name)

result = value or "default"  # same pattern as JS
```

---

## 3. Functions

### Definition & Arguments

```python
# Basic function
def greet(name: str) -> str:
    return f"Hello, {name}"

# Default arguments
def connect(host: str, port: int = 5432, ssl: bool = True) -> None:
    ...  # ... is a valid no-op (like pass)

# Keyword arguments — you can name args at call site
connect("localhost", ssl=False)      # skip port, set ssl
connect(host="localhost", port=3000) # all named

# *args and **kwargs (rest parameters and options bag)
def log(*messages: str, **metadata: Any) -> None:
    # messages is a tuple of positional args
    # metadata is a dict of keyword args
    for msg in messages:
        print(msg, metadata)

log("hello", "world", level="info", user="alice")
# messages = ("hello", "world")
# metadata = {"level": "info", "user": "alice"}
```

### Spreading Into Function Calls

```python
args = [1, 2, 3]
kwargs = {"timeout": 30, "retries": 3}

some_function(*args)       # spread list as positional args
some_function(**kwargs)    # spread dict as keyword args
some_function(*args, **kwargs)  # both
```

### Lambda (Arrow Functions)

```python
# Lambda — single expression only (no multi-line)
square = lambda x: x ** 2      # TS: const square = (x) => x ** 2
items.sort(key=lambda x: x.name)

# For anything complex, just use def
```

### Closures

```python
def make_multiplier(factor: int):
    def multiply(x: int) -> int:
        return x * factor    # captures factor from enclosing scope
    return multiply

double = make_multiplier(2)
double(5)  # 10
```

---

## 4. Type Hints

Type hints are central to modern Python. They drive validation in Pydantic and API behavior in FastAPI.

### Basic Type Hints

```python
# Variable annotations
name: str = "Alice"
age: int = 30
score: float = 9.5
active: bool = True

# Function signatures
def add(a: int, b: int) -> int:
    return a + b

# None return type
def log(message: str) -> None:
    print(message)
```

### Collection Types (Python 3.9+)

```python
# Lowercase built-in types work directly (3.9+)
names: list[str] = ["Alice", "Bob"]
scores: dict[str, int] = {"Alice": 100}
unique: set[str] = {"a", "b"}
pair: tuple[int, str] = (1, "one")
variable_tuple: tuple[int, ...] = (1, 2, 3)  # any length
```

### Union Types (Python 3.10+)

```python
# Modern syntax (3.10+) — used throughout this course
value: str | None = None         # TS: string | null
result: int | str = 42           # TS: number | string

# Older syntax (pre-3.10) — you'll see this in libraries
from typing import Optional, Union
value: Optional[str] = None      # same as str | None
result: Union[int, str] = 42     # same as int | str
```

### `Annotated` — Adding Metadata to Types

`Annotated` lets you attach extra information to a type hint. Pydantic and FastAPI use this extensively for validation rules, dependency injection, and documentation.

```python
from typing import Annotated
from pydantic import Field

# Annotated[Type, metadata1, metadata2, ...]
# The first arg is the actual type, everything after is metadata
```

### Generics

```python
from typing import TypeVar, Generic

T = TypeVar("T")

# Generic class (like TypeScript generics)
class PaginatedResponse(Generic[T]):
    items: list[T]
    total: int

# Usage
response: PaginatedResponse[User]   # TS: PaginatedResponse<User>
```

### `from __future__ import annotations`

You'll see this at the top of many Python files. It makes all annotations strings by default (lazy evaluation), which allows forward references and some performance benefits.

```python
from __future__ import annotations

class Tree:
    # Without the future import, this would fail because Tree
    # isn't fully defined yet when the hint is evaluated
    children: list[Tree]
```

---

## 5. Comprehensions

Comprehensions are Python's concise syntax for transforming and filtering collections.

```python
# List comprehension (like .map + .filter combined)
names = [user.name for user in users]
# TS: users.map(u => u.name)

adults = [u for u in users if u.age >= 18]
# TS: users.filter(u => u.age >= 18)

# Combined map + filter
adult_names = [u.name for u in users if u.age >= 18]
# TS: users.filter(u => u.age >= 18).map(u => u.name)

# Dict comprehension
name_to_age = {u.name: u.age for u in users}
# TS: Object.fromEntries(users.map(u => [u.name, u.age]))

# Set comprehension
unique_roles = {u.role for u in users}

# Conditional expression inside comprehension
labels = [f"admin:{u.name}" if u.is_admin else u.name for u in users]

# Nested (flatten)
all_tags = [tag for post in posts for tag in post.tags]
# TS: posts.flatMap(p => p.tags)
```

The `any()` and `all()` builtins take generator expressions:

```python
has_admin = any(u.role == "admin" for u in users)  # TS: users.some(...)
all_active = all(u.is_active for u in users)       # TS: users.every(...)
```

---

## 6. Error Handling

### try / except

```python
# Python uses except, not catch
try:
    result = int("not a number")
except ValueError as e:
    print(f"Bad value: {e}")
except (TypeError, KeyError):       # catch multiple types
    print("Wrong type or missing key")
except Exception as e:              # catch-all (like catch(e) in TS)
    print(f"Unexpected: {e}")
else:
    print("No error occurred")      # runs only if no exception (no TS equivalent)
finally:
    print("Always runs")

# Raise exceptions (like throw in TS)
raise ValueError("invalid input")
```

### Custom Exceptions

```python
class NotFoundError(Exception):
    def __init__(self, resource: str, id: str) -> None:
        self.resource = resource
        self.id = id
        super().__init__(f"{resource} {id} not found")

# Raise it
raise NotFoundError("User", "abc-123")

# Catch it
try:
    get_user(user_id)
except NotFoundError as e:
    return {"error": e.resource, "id": e.id}
```

---

## 7. Module & Import System

### Imports

```python
# Import a module
import os
import json

# Import specific names (like named imports in TS)
from datetime import datetime, timezone
from pathlib import Path

# Import with alias
import numpy as np
from datetime import datetime as dt

# Relative imports (within a package)
from . import models           # from current package
from .models import User       # specific name from current package
from ..utils import helpers    # from parent package
```

### Package Structure

```
my_app/
├── __init__.py          # makes this directory a Python package (can be empty)
├── main.py
├── models.py
├── routes/
│   ├── __init__.py
│   ├── users.py
│   └── items.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

`__init__.py` is like `index.ts` — it marks a directory as importable and can re-export names.

```python
# my_app/routes/__init__.py
from .users import router as users_router
from .items import router as items_router
```

---

## 8. Async / Await Basics

The syntax is nearly identical to TypeScript, but the runtime behavior differs significantly (covered in [Module 01: Async Python](../01-async-python/01-asyncio-fundamentals.md)).

```python
import asyncio

# Async function
async def fetch_user(user_id: int) -> dict:
    await asyncio.sleep(0.1)       # simulates I/O
    return {"id": user_id}

# Await — can only be used inside async functions
async def main():
    user = await fetch_user(1)

# Run the event loop (like top-level await, but explicit)
asyncio.run(main())

# Concurrent execution (like Promise.all)
async def fetch_all():
    results = await asyncio.gather(
        fetch_user(1),
        fetch_user(2),
        fetch_user(3),
    )
    return results
```

Key difference from Node.js: Python's standard library is **blocking by default**. `time.sleep()`, `open()`, `requests.get()` all freeze the event loop. You must use async-aware alternatives (`asyncio.sleep()`, `aiofiles`, `httpx`).

---

## 9. Common Patterns

### The `...` (Ellipsis) — Required Field Marker

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # ... means "required, no default value"
    name: str = Field(..., min_length=1)    # must be provided
    age: int = Field(..., gt=0)             # must be provided
    bio: str = Field(None, max_length=500)  # optional, defaults to None
```

### Protocol Classes and `typing.Protocol`

```python
from typing import Protocol

# Like a TS interface — defines a structural contract
class Repository(Protocol):
    async def get(self, id: str) -> dict: ...
    async def save(self, data: dict) -> None: ...

# Any class with matching methods satisfies the protocol
# (no explicit `implements` needed — it's structural/duck typing)
```

### `Literal` Types

```python
from typing import Literal

# Restrict to specific values (like TS literal union types)
def set_mode(mode: Literal["read", "write", "append"]) -> None:
    ...

# In Pydantic models
class Config(BaseModel):
    env: Literal["dev", "staging", "prod"]
    # TS equivalent: env: "dev" | "staging" | "prod"
```

### Walrus Operator (`:=`)

```python
# Assignment expression — assigns and returns the value
if (n := len(items)) > 10:
    print(f"Too many items: {n}")

# Useful in while loops
while (line := input()) != "quit":
    process(line)
```

### Dictionary Merge (`|` operator, 3.9+)

```python
defaults = {"timeout": 30, "retries": 3}
overrides = {"timeout": 60}
config = defaults | overrides    # {"timeout": 60, "retries": 3}
# TS: { ...defaults, ...overrides }
```

---

## 10. Quick Reference: Python vs TypeScript

| TypeScript | Python |
|-----------|--------|
| `const x = 5` | `x = 5` |
| `let x: number = 5` | `x: int = 5` |
| `null` / `undefined` | `None` |
| `true` / `false` | `True` / `False` |
| `===` | `==` (Python has no `===`) |
| `!==` | `!=` |
| `&&` / `\|\|` / `!` | `and` / `or` / `not` |
| `console.log()` | `print()` |
| `` `Hello ${name}` `` | `f"Hello {name}"` |
| `x?.y` | `getattr(x, 'y', None)` |
| `x ?? default` | `x if x is not None else default` |
| `x!` (non-null assertion) | No equivalent (just use `assert x is not None`) |
| `as Type` (type cast) | `cast(Type, value)` from typing |
| `Array<T>` | `list[T]` |
| `Record<K, V>` | `dict[K, V]` |
| `Promise<T>` | `Coroutine` (but you just use `async def`) |
| `interface` | `class(Protocol)` or `class(BaseModel)` |
| `enum` | `class(Enum)` or `class(StrEnum)` |
| `?.` optional chaining | No direct equivalent |
| `...spread` | `*list` / `**dict` |
| `export` | Just define it (everything is public) |
| `import { x } from 'y'` | `from y import x` |
| `throw new Error()` | `raise Exception()` |
| `try/catch/finally` | `try/except/finally` |
| `typeof x` | `type(x)` or `isinstance(x, Type)` |
| `x instanceof Y` | `isinstance(x, Y)` |
| `for (const x of arr)` | `for x in arr` |
| `arr.map(fn)` | `[fn(x) for x in arr]` |
| `arr.filter(fn)` | `[x for x in arr if fn(x)]` |
| `arr.find(fn)` | `next((x for x in arr if fn(x)), None)` |
| `arr.some(fn)` | `any(fn(x) for x in arr)` |
| `arr.every(fn)` | `all(fn(x) for x in arr)` |
| `Object.keys(obj)` | `obj.keys()` or `list(obj.keys())` |
| `Object.entries(obj)` | `obj.items()` |
| `JSON.stringify(obj)` | `json.dumps(obj)` |
| `JSON.parse(str)` | `json.loads(str)` |

---

## Key Takeaways

- Python uses indentation for blocks, `elif` instead of `else if`, `and`/`or`/`not` instead of `&&`/`||`/`!`.
- Everything is an object. There's no `undefined` — only `None`.
- Type hints are optional but central to modern Python (Pydantic, FastAPI, mypy).
- `*args`/`**kwargs` are Python's rest/spread operators.
- Comprehensions replace `.map()` and `.filter()` with a more concise syntax.
- Python's standard library is blocking by default — async requires explicit opt-in.
