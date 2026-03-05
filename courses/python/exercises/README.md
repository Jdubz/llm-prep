# Python Interview Exercises

Core Python exercises for interview prep. These practice the **language fundamentals** that come up in coding screens and live interviews — no frameworks, no pip dependencies, just the standard library.

Work through these **before** the module-specific exercises (`01-async-python/exercises.py`, etc.), which assume fluency with these patterns.

---

## Files

| File | Topic | Key Patterns |
|------|-------|-------------|
| `01-strings-and-collections.py` | Warm-up | dict, Counter, sorting, comprehensions, recursion |
| `02-functions-and-decorators.py` | Functions | closures, functools.wraps, decorator factories, *args/**kwargs |
| `03-classes-and-protocols.py` | OOP | dunder methods, Protocol, Generic[T], metaclass patterns |
| `04-generators-and-iterators.py` | Lazy evaluation | yield, yield from, deque, context managers |
| `05-async-and-concurrency.py` | Async | asyncio.gather, Semaphore, Queue, async context managers |

## How to Use

```bash
# Run a file to see which exercises are not yet implemented
python exercises/01-strings-and-collections.py

# Uncomment the test functions at the bottom of each file,
# then implement the TODOs until all tests pass
python exercises/01-strings-and-collections.py
```

Each file has 6 exercises with:
- A banner comment explaining the problem
- Requirements as bullet points
- Skeleton code with `# TODO` markers
- Commented-out tests to verify your solution

## Difficulty Progression

1. **Strings & Collections** — Data structure manipulation. If you can solve these quickly, your Python basics are solid.
2. **Functions & Decorators** — Closures, higher-order functions, decorator factories. The patterns behind `@app.get()` and `@field_validator`.
3. **Classes & Protocols** — Dunder methods, structural typing, generics. The OOP that Pydantic and SQLAlchemy build on.
4. **Generators & Iterators** — Lazy evaluation, `yield from`, context managers. Essential for understanding dependency injection patterns.
5. **Async & Concurrency** — `asyncio` patterns that come up in every Python backend interview.

## Related Course Modules

Each exercise file references specific course modules for deeper reading. Here's the full mapping:

| Exercise File | Primary Modules |
|--------------|----------------|
| `01-strings-and-collections.py` | `../03-python-internals/02-advanced-python-features.md`, `../04-interview-prep/01-interview-fundamentals.md` |
| `02-functions-and-decorators.py` | `../03-python-internals/02-advanced-python-features.md` |
| `03-classes-and-protocols.py` | `../03-python-internals/01-object-model-and-memory.md`, `../03-python-internals/02-advanced-python-features.md` |
| `04-generators-and-iterators.py` | `../03-python-internals/02-advanced-python-features.md`, `../01-async-python/01-asyncio-fundamentals.md` |
| `05-async-and-concurrency.py` | `../01-async-python/01-asyncio-fundamentals.md`, `../01-async-python/02-concurrency-patterns.md` |
