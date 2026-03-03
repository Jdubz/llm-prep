# Python & FastAPI

Advanced Python backend development with FastAPI. Covers async patterns, Pydantic data modeling, production API design, and testing strategies for senior engineers coming from TypeScript/Node.js.

> **Perspective**: You already know how to build APIs. This course focuses on what's different (and better) about Python's async ecosystem and FastAPI's approach compared to Express/NestJS.

---

## Modules

### 00 — [Python for TypeScript Engineers](00-python-prereqs.md)
- Python syntax, types, and patterns mapped to TypeScript equivalents
- Type hints, `Annotated`, generics, and `from __future__ import annotations`
- Classes, decorators, context managers, generators, comprehensions
- Pydantic fundamentals: models, validation, serialization, inheritance
- Environment setup: venv, pip, project structure

### 01 — FastAPI Foundations
- [01 – HTTP Routing and Decorators](./01-fastapi-foundations/01-http-routing-and-decorators.md) — path operations, Pydantic v2 models, response models, routers, OpenAPI
- [02 – Dependency Injection](./01-fastapi-foundations/02-dependency-injection.md) — DI system, nested/yield/class-based deps, dependency overrides, lifespan events
- [03 – Middleware, ASGI, and Advanced Patterns](./01-fastapi-foundations/03-middleware-asgi-and-advanced-patterns.md) — middleware, ASGI internals, exception handlers, sub-applications, interview Q&A

### 02 — Async Python Deep Dive
- [01 – Asyncio Fundamentals](./02-async-python/01-asyncio-fundamentals.md) — event loop internals, coroutine mechanics, sync vs async, GIL impact, uvloop
- [02 – Concurrency Patterns](./02-async-python/02-concurrency-patterns.md) — gather, TaskGroup, semaphores, producer/consumer, connection pooling, circuit breaker
- [03 – Async Debugging and Production](./02-async-python/03-async-debugging-and-production.md) — common bugs, debug mode, async testing, structured logging, interview Q&A

### 03 — Database Patterns with SQLAlchemy
- [01 – Models, Relationships, and Schema](./03-sqlalchemy/01-models-relationships-and-schema.md) — declarative mapping, `Mapped[]`, relationships, lazy/eager loading, Alembic, alternatives
- [02 – Querying and Session Management](./03-sqlalchemy/02-querying-and-session-management.md) — session lifecycle, SELECT/INSERT/UPDATE/DELETE, JOINs, CTEs, connection pooling, Unit of Work
- [03 – Advanced SQLAlchemy and Migrations](./03-sqlalchemy/03-advanced-sqlalchemy-and-migrations.md) — transaction rollback testing, multi-tenancy, soft deletes, full-text search, interview Q&A

### 04 — Authentication & Authorization
- [01 – Authentication Basics](./04-auth/01-authentication-basics.md) — OAuth2 Bearer, JWT flow, token creation/verification, password hashing, refresh tokens, social auth
- [02 – Authorization and RBAC](./04-auth/02-authorization-and-rbac.md) — RBAC database model, role/permission dependencies, OAuth2 scopes, API key management, security headers
- [03 – Advanced Auth Patterns](./04-auth/03-advanced-auth-patterns.md) — OIDC, mTLS, composite auth backends, token revocation, audit logging, interview Q&A

### 05 — Advanced API Patterns
- [01 – File Handling and Streaming](./05-advanced-api-patterns/01-file-handling-and-streaming.md) — file upload/download, presigned S3, SSE, LLM token streaming, background tasks, webhooks
- [02 – Pagination, Filtering, and Bulk Operations](./05-advanced-api-patterns/02-pagination-filtering-and-bulk-operations.md) — offset/cursor pagination, filtering, rate limiting, bulk create/update/delete, API versioning
- [03 – Real-Time, GraphQL, and Advanced Patterns](./05-advanced-api-patterns/03-real-time-graphql-and-advanced-patterns.md) — WebSockets, GraphQL with Strawberry, gRPC, Kafka, CQRS, interview Q&A

### 06 — Testing & Quality
- [01 – pytest Fixtures and Basics](./06-testing/01-pytest-fixtures-and-basics.md) — fixtures, parametrize, conftest.py, async testing, mypy, ruff, pre-commit hooks
- [02 – Integration Testing and Mocking](./06-testing/02-integration-testing-and-mocking.md) — AsyncClient, dependency overrides, transaction rollback DB, factory_boy, mocking patterns
- [03 – Advanced Testing and Tools](./06-testing/03-advanced-testing-and-tools.md) — Hypothesis property-based testing, Schemathesis, snapshot testing, benchmarking, CI pipeline

### 07 — Production Deployment
- [01 – Docker and Deployment](./07-production/01-docker-and-deployment.md) — multi-stage Dockerfiles, uv, slim vs alpine, Gunicorn/Uvicorn, Kubernetes manifests, HPA
- [02 – Configuration, Logging, and Observability](./07-production/02-configuration-logging-and-observability.md) — pydantic-settings, structlog, health checks, OpenTelemetry, Sentry, Prometheus metrics
- [03 – Performance and Scaling](./07-production/03-performance-and-scaling.md) — memory/CPU profiling, py-spy, async profiling, A/B testing, interview Q&A

### 08 — Interview Prep
- [01 – Interview Fundamentals](./08-interview-prep/01-interview-fundamentals.md) — top 20 Python questions, Python vs TypeScript syntax, FastAPI Q&A, CPython internals, Django vs FastAPI
- [02 – System Design and Code Review](./08-interview-prep/02-system-design-and-code-review.md) — system design template and examples, code review exercises, live coding patterns, async patterns

### 09 — Python Internals
- [01 – Object Model and Memory](./09-python-internals/01-object-model-and-memory.md) — PyObject, reference counting, cyclic GC, GIL, integer cache, pymalloc, `__slots__`, weak refs
- [02 – Advanced Python Features](./09-python-internals/02-advanced-python-features.md) — descriptors, MRO, `super()`, import system, `__init_subclass__`, metaclasses, ContextVar, free-threaded Python
- [03 – Imports, Bytecode, and Runtime](./09-python-internals/03-imports-and-runtime.md) — bytecode, `dis`, code objects, adaptive specialization, frame objects, generator protocol, interview Q&A

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

## Projects

Complete mini-applications that tie multiple modules together:

| Project | Covers | Description |
|---------|--------|-------------|
| [bookmark-api](projects/bookmark-api/) | Modules 01-04, 06 | Full CRUD API with JWT auth, filtering, pagination, and test suite |
| [task-queue-service](projects/task-queue-service/) | Modules 02, 05, 07 | Async task processing with SSE streaming, health checks, and metrics |

---

## Prerequisites
- Solid understanding of REST API design
- Experience with at least one ORM (Prisma, TypeORM, etc.)
- Read [Module 00: Python for TypeScript Engineers](00-python-prereqs.md) if you're coming from Node.js/TypeScript

## Status
**Content complete** — all modules restructured into numbered, content-named files.
Each module has 2-3 files organized by topic rather than format. Module 09 (Python Internals) covers CPython runtime mechanics for senior-level depth.
