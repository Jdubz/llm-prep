# Module 00: Python for TypeScript Engineers

Everything you need to know before starting this course. If you're coming from TypeScript/Node.js, Python will feel familiar in spirit but alien in syntax. This guide covers every Python concept the course assumes you already know.

Read this front to back before touching Module 01.

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

Type hints are central to FastAPI and Pydantic. FastAPI uses them to determine request parameter types, validation rules, and OpenAPI schema generation. This isn't optional decoration — it's how the framework works.

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

`Annotated` lets you attach extra information to a type hint. FastAPI and Pydantic use this extensively for validation rules, dependency injection, and documentation.

```python
from typing import Annotated
from fastapi import Depends, Query

# Annotated[Type, metadata1, metadata2, ...]
# The first arg is the actual type, everything after is metadata

# FastAPI uses metadata to configure parameter behavior:
async def list_items(
    skip: Annotated[int, Query(ge=0)] = 0,         # query param, >= 0
    limit: Annotated[int, Query(le=100)] = 20,      # query param, <= 100
    db: Annotated[Session, Depends(get_db)] = None,  # injected dependency
):
    ...

# Without Annotated (older style, still works):
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    ...
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

## 5. Classes & OOP

Classes are used pervasively: Pydantic models, SQLAlchemy models, enums, custom exceptions — everything is a class.

### Basic Class

```python
class User:
    # __init__ is the constructor (like constructor() in TS)
    def __init__(self, name: str, email: str) -> None:
        self.name = name       # instance attributes (like this.name)
        self.email = email
        self._internal = 42    # _ prefix = "private" by convention (not enforced)

    # self is explicit (like this, but you must always include it)
    def greet(self) -> str:
        return f"Hi, I'm {self.name}"

    # String representation (like toString())
    def __repr__(self) -> str:
        return f"User(name={self.name!r})"

user = User("Alice", "alice@example.com")
user.greet()  # "Hi, I'm Alice"
```

### Inheritance

```python
class Animal:
    def __init__(self, name: str) -> None:
        self.name = name

    def speak(self) -> str:
        raise NotImplementedError

class Dog(Animal):              # TS: class Dog extends Animal
    def speak(self) -> str:
        return "Woof!"

class Cat(Animal):
    def speak(self) -> str:
        return "Meow!"

# Multiple inheritance (Python supports it, TS doesn't)
class GuideDog(Dog, ServiceAnimal):
    pass
```

### `@property` — Computed Getters

```python
class Circle:
    def __init__(self, radius: float) -> None:
        self.radius = radius

    @property
    def area(self) -> float:
        return 3.14159 * self.radius ** 2

    @property
    def diameter(self) -> float:
        return self.radius * 2

c = Circle(5)
c.area       # 78.5 — accessed like an attribute, not a method call
c.diameter   # 10.0
```

Pydantic uses `@computed_field` with `@property` for derived response fields.

### `@classmethod` and `@staticmethod`

```python
class Config:
    def __init__(self, db_url: str, debug: bool) -> None:
        self.db_url = db_url
        self.debug = debug

    @classmethod
    def from_env(cls) -> "Config":
        # cls refers to the class itself (like static methods that can access the class)
        # Used as alternative constructors
        return cls(
            db_url=os.environ["DATABASE_URL"],
            debug=os.environ.get("DEBUG", "false") == "true",
        )

    @staticmethod
    def is_valid_url(url: str) -> bool:
        # No access to cls or self — just a namespaced function
        return url.startswith("postgresql://")

# Usage
config = Config.from_env()          # alternative constructor
Config.is_valid_url("postgresql://") # True
```

Pydantic validators use `@classmethod` — you'll see `@field_validator("name") @classmethod` everywhere.

### Dunder (Magic) Methods

"Dunder" = double underscore. These are Python's protocol methods (like implementing interfaces).

```python
class Money:
    def __init__(self, amount: float, currency: str = "USD") -> None:
        self.amount = amount
        self.currency = currency

    def __repr__(self) -> str:      # developer-friendly string
        return f"Money({self.amount}, {self.currency!r})"

    def __str__(self) -> str:       # user-friendly string
        return f"${self.amount:.2f}"

    def __eq__(self, other) -> bool: # == comparison
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other) -> bool: # < comparison (enables sorting)
        return self.amount < other.amount

    def __hash__(self) -> int:       # makes it usable as dict key / in sets
        return hash((self.amount, self.currency))

    def __bool__(self) -> bool:      # truthiness
        return self.amount != 0
```

You won't write many of these yourself, but Pydantic and SQLAlchemy use them extensively under the hood.

### Dataclasses (Predecessor to Pydantic Models)

Dataclasses auto-generate `__init__`, `__repr__`, `__eq__` — like a lightweight version of what Pydantic does.

```python
from dataclasses import dataclass, field

@dataclass
class Point:
    x: float
    y: float
    label: str = "origin"  # default value

# Automatically generates:
# __init__(self, x: float, y: float, label: str = "origin")
# __repr__ -> "Point(x=1.0, y=2.0, label='origin')"
# __eq__ based on field values

p = Point(1.0, 2.0)
p.x  # 1.0
```

Pydantic `BaseModel` is like a dataclass with validation, serialization, and schema generation bolted on.

### Enums

```python
from enum import Enum, StrEnum

# Basic enum
class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DELETED = "deleted"

# StrEnum (3.11+) — values are strings, used with Pydantic/FastAPI
class Role(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

# Usage
status = Status.PENDING
status.value    # "pending"
status.name     # "PENDING"

# In Pydantic models, StrEnum fields serialize to their string values
```

---

## 6. Decorators

Decorators are everywhere in FastAPI (`@app.get`, `@field_validator`, `@asynccontextmanager`). You need to understand what they actually do.

### What a Decorator Is

A decorator is a function that wraps another function. The `@` syntax is just syntactic sugar.

```python
# These two are identical:
@my_decorator
def greet():
    return "hello"

# is the same as:
def greet():
    return "hello"
greet = my_decorator(greet)
```

### Writing a Decorator

```python
import functools

def log_calls(func):
    @functools.wraps(func)  # preserves the original function's name/docstring
    def wrapper(*args, **kwargs):
        print(f"Calling {func.__name__}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result}")
        return result
    return wrapper

@log_calls
def add(a: int, b: int) -> int:
    return a + b

add(2, 3)
# Calling add
# add returned 5
```

### Decorator Factories (Decorators with Arguments)

When a decorator takes arguments (like `@app.get("/path")`), it's actually a function that returns a decorator.

```python
def require_role(role: str):            # factory — takes args
    def decorator(func):                # actual decorator
        @functools.wraps(func)
        def wrapper(*args, **kwargs):   # wrapper
            # check role logic here
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_role("admin")  # require_role("admin") returns the decorator
def delete_user(user_id: int):
    ...
```

### Stacking Decorators

```python
# Decorators apply bottom-up (innermost first)
@app.post("/users")           # 2nd: registers the route
@require_role("admin")        # 1st: wraps with role check
async def create_user():
    ...

# Pydantic uses this pattern:
@field_validator("email")
@classmethod
def validate_email(cls, v):
    ...
```

---

## 7. Context Managers (`with` / `async with`)

Context managers handle setup/teardown automatically — like `try/finally` but cleaner. Used in FastAPI for database sessions, HTTP clients, and file handling.

### Basic Usage

```python
# File I/O — file is automatically closed when the block exits
with open("data.txt") as f:
    content = f.read()
# f is closed here, even if an exception occurred

# TS equivalent:
# const f = fs.openSync("data.txt")
# try { ... } finally { fs.closeSync(f) }
```

### Async Context Managers

```python
# Used heavily in FastAPI for database sessions and HTTP clients
async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com")
# client is automatically closed

async with async_session() as session:
    result = await session.execute(query)
# session is automatically closed/returned to pool
```

### Writing Context Managers

```python
from contextlib import contextmanager, asynccontextmanager

# Sync context manager
@contextmanager
def timer(label: str):
    start = time.time()
    yield                    # code inside the `with` block runs here
    elapsed = time.time() - start
    print(f"{label}: {elapsed:.2f}s")

with timer("query"):
    do_something_slow()

# Async context manager — used for FastAPI lifespan
@asynccontextmanager
async def lifespan(app):
    # Startup: runs before the app starts serving
    db = await connect_db()
    yield {"db": db}         # app runs during yield
    # Shutdown: runs when the app stops
    await db.close()
```

FastAPI dependency injection with `yield` is a context manager pattern:

```python
async def get_db():
    session = async_session()
    try:
        yield session        # inject this into the route handler
    finally:
        await session.close() # cleanup after the request
```

---

## 8. Generators & `yield`

Generators produce values lazily, one at a time. You need to understand `yield` because FastAPI dependencies use it for cleanup.

```python
# Generator function — returns values one at a time
def count_up(n: int):
    for i in range(n):
        yield i              # pauses here, resumes on next iteration

for num in count_up(3):
    print(num)               # 0, 1, 2

# Generator expression (like lazy array.map)
squares = (x ** 2 for x in range(1000000))  # no memory used yet
first = next(squares)  # 0 — computed on demand
```

### Async Generators

```python
async def stream_data():
    async with httpx.AsyncClient() as client:
        async for chunk in client.stream("GET", url):
            yield chunk      # produces values asynchronously

# Used with async for
async for chunk in stream_data():
    process(chunk)
```

---

## 9. Comprehensions

Comprehensions are Python's concise syntax for transforming and filtering collections. Used heavily throughout the course.

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

## 10. Error Handling

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
raise HTTPException(status_code=404, detail="Not found")
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

## 11. Module & Import System

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

## 12. Async / Await

The syntax is nearly identical to TypeScript, but the runtime behavior differs significantly (covered in Module 02).

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

Key difference from Node.js: Python's standard library is **blocking by default**. `time.sleep()`, `open()`, `requests.get()` all freeze the event loop. You must use async-aware alternatives (`asyncio.sleep()`, `aiofiles`, `httpx`). Module 02 covers this in depth.

---

## 13. Common Patterns You'll See Immediately

### The `...` (Ellipsis) — Required Field Marker

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    # ... means "required, no default value"
    name: str = Field(..., min_length=1)    # must be provided
    age: int = Field(..., gt=0)             # must be provided
    bio: str = Field(None, max_length=500)  # optional, defaults to None
```

`...` is Python's Ellipsis literal. Pydantic uses it to mean "this field is required." You could also just omit the default entirely (`name: str = Field(min_length=1)`), but the explicit `...` makes intent clear.

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

## 14. What Pydantic Actually Is

Before Module 01 throws Pydantic models at you, understand what it does and why.

Pydantic is a data validation library that uses type hints to define schemas. Think of it as Zod but integrated into the type system — you define a class with type annotations, and Pydantic automatically validates input, coerces types, serializes output, and generates JSON Schema.

```python
from pydantic import BaseModel, Field, field_validator

class User(BaseModel):
    name: str = Field(..., min_length=1)
    age: int = Field(..., gt=0)
    email: str

    @field_validator("email")
    @classmethod
    def must_be_valid_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email")
        return v.lower()

# Validation happens at instantiation
user = User(name="Alice", age=30, email="ALICE@EXAMPLE.COM")
user.email  # "alice@example.com" — validator lowercased it

# Invalid data raises ValidationError
User(name="", age=-1, email="bad")
# ValidationError: 3 errors — name too short, age too low, invalid email

# Serialization
user.model_dump()       # {"name": "Alice", "age": 30, "email": "alice@example.com"}
user.model_dump_json()  # JSON string

# Schema generation (drives OpenAPI docs in FastAPI)
User.model_json_schema()
```

### Why FastAPI Uses Pydantic Everywhere

In Express, you parse the body, validate with Zod/Joi, and type-cast manually. In FastAPI, all of that is automatic:

```python
# FastAPI reads this type hint and:
# 1. Parses the request body as JSON
# 2. Validates it against UserCreate's schema
# 3. Returns 422 with detailed errors if validation fails
# 4. Passes the validated, typed object to your function
@app.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    # user is already validated — no manual checks needed
    ...
```

### Model Inheritance

Pydantic models use inheritance to share fields and avoid repetition:

```python
# Base — shared fields
class ItemBase(BaseModel):
    name: str
    price: float

# Create — what clients send (no id, no timestamps)
class ItemCreate(ItemBase):
    pass

# Update — all fields optional
class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

# Response — what clients receive (includes server-generated fields)
class ItemResponse(ItemBase):
    id: int
    created_at: datetime
```

This `Base → Create / Update / Response` pattern is used in every module.

---

## 15. Quick Reference: Python vs TypeScript

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

## Next Steps

You're now ready for [Module 01: FastAPI Foundations](01-fastapi-foundations/README.md). The module will map FastAPI concepts to Express patterns you already know, building on the Python fundamentals covered here.
