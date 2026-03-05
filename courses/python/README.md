# Python for TypeScript Engineers

Master Python's language features, async patterns, testing strategies, and internals. Designed for senior engineers coming from TypeScript/Node.js who want to build a deep understanding of Python before layering on frameworks.

> **Perspective**: You already know programming. This course focuses on what's different about Python — its syntax, type system, async model, object model, and testing ecosystem.

---

## Modules

### 00 — Python Fundamentals
- [01 – Syntax, Types, and Patterns](./00-python-fundamentals/01-syntax-types-and-patterns.md) — env setup, syntax translation, functions, type hints, comprehensions, error handling, modules, async basics
- [02 – Classes, Decorators, and OOP](./00-python-fundamentals/02-classes-decorators-and-oop.md) — classes, inheritance, properties, dunder methods, dataclasses, enums, decorators, context managers, generators
- [03 – Pydantic and Data Modeling](./00-python-fundamentals/03-pydantic-and-data-modeling.md) — Pydantic models, validation, serialization, field constraints, model inheritance, computed fields

### 01 — Async Python Deep Dive
- [01 – Asyncio Fundamentals](./01-async-python/01-asyncio-fundamentals.md) — event loop internals, coroutine mechanics, sync vs async, GIL impact, uvloop
- [02 – Concurrency Patterns](./01-async-python/02-concurrency-patterns.md) — gather, TaskGroup, semaphores, producer/consumer, connection pooling, circuit breaker
- [03 – Async Debugging and Production](./01-async-python/03-async-debugging-and-production.md) — common bugs, debug mode, async testing, structured logging, interview Q&A

### 02 — Testing & Quality
- [01 – pytest Fixtures and Basics](./02-testing/01-pytest-fixtures-and-basics.md) — fixtures, parametrize, conftest.py, async testing, mocking, mypy, ruff, pre-commit hooks

### 03 — Python Internals
- [01 – Object Model and Memory](./03-python-internals/01-object-model-and-memory.md) — PyObject, reference counting, cyclic GC, GIL, integer cache, pymalloc, `__slots__`, weak refs
- [02 – Advanced Python Features](./03-python-internals/02-advanced-python-features.md) — descriptors, MRO, `super()`, import system, `__init_subclass__`, metaclasses, ContextVar, free-threaded Python
- [03 – Imports, Bytecode, and Runtime](./03-python-internals/03-imports-and-runtime.md) — bytecode, `dis`, code objects, adaptive specialization, frame objects, generator protocol, interview Q&A

### 04 — Interview Prep
- [01 – Interview Fundamentals](./04-interview-prep/01-interview-fundamentals.md) — top 20 Python questions, Python vs TypeScript syntax, CPython internals, PEPs to know

---

## Content Per Module

Each module directory contains numbered content files:

- **`01-*.md`** — Foundational concepts: core patterns, syntax, and essential knowledge.
- **`02-*.md`** — Practical patterns: workflows, real-world application, and integration.
- **`03-*.md`** (when present) — Advanced internals, edge cases, production concerns, and interview Q&A.
- **`examples.py`** — Complete, runnable production patterns. Study and run these.
- **`exercises.py`** — Skeleton functions with TODOs. Implement to test your knowledge.

## Exercises

### [Python Interview Exercises](exercises/)
Core Python exercises for coding screens and live interviews. 30 exercises across 5 files covering strings & collections, functions & decorators, classes & protocols, generators & iterators, and async patterns. Pure stdlib — no pip dependencies.

---

## Prerequisites
- Solid understanding of at least one programming language (TypeScript, JavaScript, etc.)
- Familiarity with basic data structures and algorithms

## What's Next
After completing this course, continue to [FastAPI](../fastapi/) to learn how to build production APIs with Python.
