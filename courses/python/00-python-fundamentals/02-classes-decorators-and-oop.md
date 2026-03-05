# 02 – Classes, Decorators, and OOP

Classes are used pervasively in Python: Pydantic models, SQLAlchemy models, enums, custom exceptions — everything is a class. Decorators wrap behavior around functions and are the mechanism behind `@property`, `@staticmethod`, and framework features like `@app.get()`.

---

## 1. Classes

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
```

---

## 2. Decorators

Decorators are everywhere in Python frameworks (`@app.get`, `@field_validator`, `@asynccontextmanager`). You need to understand what they actually do.

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

## 3. Context Managers (`with` / `async with`)

Context managers handle setup/teardown automatically — like `try/finally` but cleaner. Used for database sessions, HTTP clients, and file handling.

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
# Used heavily for database sessions and HTTP clients
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

# Async context manager
@asynccontextmanager
async def lifespan(app):
    # Startup
    db = await connect_db()
    yield {"db": db}         # app runs during yield
    # Shutdown
    await db.close()
```

---

## 4. Generators & `yield`

Generators produce values lazily, one at a time. You need to understand `yield` because many Python patterns (including dependency injection) use it for cleanup.

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

## Key Takeaways

- `self` is explicit in all instance methods — there's no implicit `this`.
- `@property` makes methods behave like attribute access (computed getters).
- `@classmethod` is used for alternative constructors; `@staticmethod` for namespaced functions.
- Decorators are just functions that wrap functions — `@dec` means `f = dec(f)`.
- Always use `@functools.wraps(func)` in decorators to preserve metadata.
- Context managers (`with`/`async with`) guarantee cleanup — use them for any resource that needs closing.
- Generators (`yield`) produce values lazily and are the foundation of many Python patterns.
