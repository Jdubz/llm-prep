# Node.js & TypeScript

Expert-level Node.js and TypeScript course for engineers with 10+ years of TypeScript experience. Covers advanced type-level programming, Node.js runtime internals, REST and GraphQL API design, and production architecture patterns.

> **This is your domain.** This course goes deep — not teaching you TypeScript, but sharpening the edges. Advanced type patterns, runtime internals you should be able to explain, API design trade-offs you should have opinions on, and architecture decisions you should be able to defend.

---

## Modules

| # | Topic | What You'll Nail |
|---|-------|-----------------|
| 00 | [TS & Node Fundamentals](00-ts-node-fundamentals.md) | V8 internals, closures, prototypes, event loop, promises, TypeScript essentials, modules |
| 01 | [TypeScript Advanced](01-typescript-advanced/) | Conditional types, mapped types, template literals, branded types, type-level programming |
| 02 | [Node.js Runtime](02-node-runtime/) | Event loop phases, libuv, worker threads, cluster, memory management |
| 03 | [REST API Design](03-rest-api-design/) | Resource modeling, pagination, versioning, idempotency, error conventions |
| 04 | [GraphQL](04-graphql/) | Schema design, DataLoader, subscriptions, federation, security |
| 05 | [Auth & Security](05-auth-security/) | JWT, OAuth2/OIDC, session management, CSRF, rate limiting |
| 06 | [Database Patterns](06-database-patterns/) | Prisma vs Drizzle vs TypeORM, migrations, transactions, query optimization |
| 07 | [Testing](07-testing/) | Vitest, supertest, MSW, contract testing, test containers |
| 08 | [Performance & Scaling](08-performance-scaling/) | Clustering, Redis caching, streaming, profiling, memory leaks |
| 09 | [Architecture Patterns](09-architecture-patterns/) | Clean architecture, CQRS, event-driven, DI, microservices vs monolith |
| 10 | [Interview Prep](10-interview-prep/) | Expert TS/Node questions, system design, code review, live coding |

## Module Files

### 01 — TypeScript Advanced
- [01 – Conditional and Mapped Types](01-typescript-advanced/01-conditional-and-mapped-types.md)
- [02 – Advanced Type Patterns](01-typescript-advanced/02-advanced-type-patterns.md)

### 02 — Node.js Runtime
- [01 – Event Loop and Task Queues](02-node-runtime/01-event-loop-and-task-queues.md)
- [02 – Threading and Process Management](02-node-runtime/02-threading-and-process-management.md)
- [03 – Memory, Streams, and Runtime Internals](02-node-runtime/03-memory-streams-and-runtime-internals.md)

### 03 — REST API Design
- [01 – HTTP Semantics and Status Codes](03-rest-api-design/01-http-semantics-and-status-codes.md)
- [02 – Pagination, Filtering, and Bulk Operations](03-rest-api-design/02-pagination-filtering-and-bulk-operations.md)
- [03 – API Design Patterns and Versioning](03-rest-api-design/03-api-design-patterns-and-versioning.md)

### 04 — GraphQL
- [01 – Schema Design and Resolvers](04-graphql/01-schema-design-and-resolvers.md)
- [02 – Advanced GraphQL Patterns](04-graphql/02-advanced-graphql-patterns.md)
- [03 – GraphQL Performance and Alternatives](04-graphql/03-graphql-performance-and-alternatives.md)

### 05 — Auth and Security
- [01 – JWT and OAuth2](05-auth-security/01-jwt-and-oauth2.md)
- [02 – Session Management and Validation](05-auth-security/02-session-management-and-validation.md)
- [03 – Advanced Security and Secrets](05-auth-security/03-advanced-security-and-secrets.md)

### 06 — Database Patterns
- [01 – Prisma and Drizzle](06-database-patterns/01-prisma-and-drizzle.md)
- [02 – Queries, Transactions, and Optimization](06-database-patterns/02-queries-transactions-and-optimization.md)
- [03 – Advanced Patterns and Multi-Tenancy](06-database-patterns/03-advanced-patterns-and-multi-tenancy.md)

### 07 — Testing
- [01 – Vitest and Unit Testing](07-testing/01-vitest-and-unit-testing.md)
- [02 – Integration Testing and Mocking](07-testing/02-integration-testing-and-mocking.md)
- [03 – Advanced Testing Patterns](07-testing/03-advanced-testing-patterns.md)

### 08 — Performance and Scaling
- [01 – Caching and Redis](08-performance-scaling/01-caching-and-redis.md)
- [02 – Clustering and Scaling](08-performance-scaling/02-clustering-and-scaling.md)
- [03 – Profiling and Advanced Performance](08-performance-scaling/03-profiling-and-advanced-performance.md)

### 09 — Architecture Patterns
- [01 – Clean Architecture and DDD](09-architecture-patterns/01-clean-architecture-and-ddd.md)
- [02 – Event-Driven and Async Patterns](09-architecture-patterns/02-event-driven-and-async-patterns.md)
- [03 – Microservices and Advanced Patterns](09-architecture-patterns/03-microservices-and-advanced-patterns.md)

### 10 — Interview Prep
- [01 – Interview Fundamentals](10-interview-prep/01-interview-fundamentals.md)
- [02 – System Design and Code Review](10-interview-prep/02-system-design-and-code-review.md)

## Study Strategy

**Quick prep (6-8 hours)**: Read file 01 for modules 01-04 (your differentiators) + file 01 for the rest.

**Deep prep (16-20 hours)**: Work through all files in sequence per module. Each file builds on the previous.

**During the interview**: File 01 of each module covers foundational patterns; file 02 and 03 cover advanced internals and edge cases.

## Prerequisites
- 10+ years TypeScript experience
- Production Node.js experience
- Review [Module 00: TS & Node Fundamentals](00-ts-node-fundamentals.md) to ensure the basics are sharp

## Related Reading

Start with [Module 00: TS & Node Fundamentals](00-ts-node-fundamentals.md) — it is the prerequisite for every other module in this course. If you are coming from a frontend-heavy TypeScript background, pay special attention to the [Event Loop](00-ts-node-fundamentals.md#4-the-event-loop) and [Streams](00-ts-node-fundamentals.md#9-nodejs-core-concepts) sections before tackling Modules 02 and 08.

Modules are designed to be studied in order, but the cross-references within each file let you jump between related topics. Key dependency chains:

- **Type system depth**: Module 00 (fundamentals) -> Module 01 (advanced TS) -> Module 06 (database types) -> Module 09 (architecture types)
- **API design**: Module 03 (REST) <-> Module 04 (GraphQL) — study both to compare trade-offs
- **Runtime to production**: Module 02 (runtime internals) -> Module 08 (performance) -> Module 09 (architecture)
- **Security across layers**: Module 05 (auth/security) touches Module 03 (REST routes), Module 04 (GraphQL auth), and Module 06 (user models)
- **Testing everything**: Module 07 references patterns from all prior modules — study it last for maximum context

## Status
**Content complete** — all modules written.
