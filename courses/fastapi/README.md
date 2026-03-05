# FastAPI

Advanced API development with FastAPI. Covers routing, dependency injection, SQLAlchemy, auth, testing, production deployment, and interview prep for senior engineers.

> **Prerequisite**: Complete [Python for TypeScript Engineers](../python/) first. This course assumes fluency with Python syntax, type hints, async/await, decorators, and Pydantic.

---

## Modules

### 00 — FastAPI Foundations
- [01 – HTTP Routing and Decorators](./00-fastapi-foundations/01-http-routing-and-decorators.md) — path operations, Pydantic v2 models, response models, routers, OpenAPI
- [02 – Dependency Injection](./00-fastapi-foundations/02-dependency-injection.md) — DI system, nested/yield/class-based deps, dependency overrides, lifespan events
- [03 – Middleware, ASGI, and Advanced Patterns](./00-fastapi-foundations/03-middleware-asgi-and-advanced-patterns.md) — middleware, ASGI internals, exception handlers, sub-applications, interview Q&A

### 01 — Database Patterns with SQLAlchemy
- [01 – Models, Relationships, and Schema](./01-sqlalchemy/01-models-relationships-and-schema.md) — declarative mapping, `Mapped[]`, relationships, lazy/eager loading, Alembic, alternatives
- [02 – Querying and Session Management](./01-sqlalchemy/02-querying-and-session-management.md) — session lifecycle, SELECT/INSERT/UPDATE/DELETE, JOINs, CTEs, connection pooling, Unit of Work
- [03 – Advanced SQLAlchemy and Migrations](./01-sqlalchemy/03-advanced-sqlalchemy-and-migrations.md) — transaction rollback testing, multi-tenancy, soft deletes, full-text search, interview Q&A

### 02 — Authentication & Authorization
- [01 – Authentication Basics](./02-auth/01-authentication-basics.md) — OAuth2 Bearer, JWT flow, token creation/verification, password hashing, refresh tokens, social auth
- [02 – Authorization and RBAC](./02-auth/02-authorization-and-rbac.md) — RBAC database model, role/permission dependencies, OAuth2 scopes, API key management, security headers
- [03 – Advanced Auth Patterns](./02-auth/03-advanced-auth-patterns.md) — OIDC, mTLS, composite auth backends, token revocation, audit logging, interview Q&A

### 03 — Advanced API Patterns
- [01 – File Handling and Streaming](./03-advanced-api-patterns/01-file-handling-and-streaming.md) — file upload/download, presigned S3, SSE, LLM token streaming, background tasks, webhooks
- [02 – Pagination, Filtering, and Bulk Operations](./03-advanced-api-patterns/02-pagination-filtering-and-bulk-operations.md) — offset/cursor pagination, filtering, rate limiting, bulk create/update/delete, API versioning
- [03 – Real-Time, GraphQL, and Advanced Patterns](./03-advanced-api-patterns/03-real-time-graphql-and-advanced-patterns.md) — WebSockets, GraphQL with Strawberry, gRPC, Kafka, CQRS, interview Q&A

### 04 — Testing
- [01 – Integration Testing and Mocking](./04-testing/01-integration-testing-and-mocking.md) — AsyncClient, dependency overrides, transaction rollback DB, factory_boy, mocking patterns
- [02 – Advanced Testing and Tools](./04-testing/02-advanced-testing-and-tools.md) — Hypothesis property-based testing, Schemathesis, snapshot testing, benchmarking, CI pipeline

### 05 — Production Deployment
- [01 – Docker and Deployment](./05-production/01-docker-and-deployment.md) — multi-stage Dockerfiles, uv, slim vs alpine, Gunicorn/Uvicorn, Kubernetes manifests, HPA
- [02 – Configuration, Logging, and Observability](./05-production/02-configuration-logging-and-observability.md) — pydantic-settings, structlog, health checks, OpenTelemetry, Sentry, Prometheus metrics
- [03 – Performance and Scaling](./05-production/03-performance-and-scaling.md) — memory/CPU profiling, py-spy, async profiling, A/B testing, interview Q&A

### 06 — Interview Prep
- [01 – Interview Fundamentals](./06-interview-prep/01-interview-fundamentals.md) — FastAPI-specific Q&A, dependency injection, middleware vs deps, Pydantic v2, async/sync endpoints, Django vs FastAPI
- [02 – System Design and Code Review](./06-interview-prep/02-system-design-and-code-review.md) — system design template and examples, code review exercises, live coding patterns, async patterns

---

## Content Per Module

Each module directory contains numbered content files:

- **`01-*.md`** — Foundational concepts: core patterns, syntax, and essential knowledge.
- **`02-*.md`** — Practical patterns: workflows, real-world application, and integration.
- **`03-*.md`** (when present) — Advanced internals, edge cases, production concerns, and interview Q&A.
- **`examples.py`** — Complete, runnable production patterns. Study and run these.
- **`exercises.py`** — Skeleton functions with TODOs. Implement to test your knowledge.

## Projects

Complete mini-applications that tie multiple modules together:

| Project | Covers | Description |
|---------|--------|-------------|
| [bookmark-api](projects/bookmark-api/) | Modules 00-02, 04 | Full CRUD API with JWT auth, filtering, pagination, and test suite |
| [task-queue-service](projects/task-queue-service/) | Modules 01, 03, 05 | Async task processing with SSE streaming, health checks, and metrics |

---

## Prerequisites
- Complete [Python for TypeScript Engineers](../python/) (or equivalent Python fluency)
- Solid understanding of REST API design
- Experience with at least one ORM (Prisma, TypeORM, etc.)
