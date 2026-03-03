# Infrastructure & Architecture Scaling

System design, infrastructure, and scaling patterns for senior engineers. Covers the architecture knowledge needed for staff-level interviews -- from single-server to distributed systems, with emphasis on practical trade-offs over theoretical purity.

> **Perspective**: You've built and shipped production systems. This course focuses on articulating design decisions clearly, reasoning about trade-offs under pressure, and covering the infrastructure gaps that backend-heavy interviews expect.

---

## Modules

### 00 — [Computing Fundamentals](00-computing-fundamentals.md)
- Networking: DNS, TCP/UDP, HTTP, TLS, latency numbers
- OS concepts: processes vs threads, concurrency vs parallelism, memory, file systems
- Database fundamentals: SQL, ACID, indexing, SQL vs NoSQL trade-offs
- Cloud computing: regions, VPCs, common services, managed vs self-hosted
- Distributed systems: CAP theorem, consistency models, replication, load balancing
- Containers, security basics, observability, back-of-envelope estimation

### 01 — System Design Framework

1. [System Design Framework Essentials](01-system-design-framework/01-system-design-framework-essentials.md) — Structured approach, requirements gathering, back-of-the-envelope estimation, communication strategies, common pitfalls
2. [Advanced System Design](01-system-design-framework/02-advanced-system-design.md) — Deep dives into advanced trade-offs, distributed system patterns, and staff-level interview expectations

### 02 — Databases at Scale

1. [SQL, NoSQL, and Decision Framework](02-databases-at-scale/01-sql-nosql-and-decision-framework.md) — SQL vs NoSQL trade-offs, ACID, consistency models, database selection guide
2. [Indexing, Sharding, and Replication](02-databases-at-scale/02-indexing-sharding-and-replication.md) — Index types, query optimization, EXPLAIN plans, horizontal partitioning, consistent hashing, replication strategies
3. [Database Platforms and Scaling](02-databases-at-scale/03-database-platforms-and-scaling.md) — PostgreSQL internals, DynamoDB, Redis, CAP theorem in practice, read replicas, connection pooling

### 03 — Caching Strategies

1. [Caching Patterns and Redis Basics](03-caching/01-caching-patterns-and-redis-basics.md) — Cache-aside, write-through, write-behind, Redis architecture, clustering, persistence, eviction policies
2. [Cache Invalidation and Performance](03-caching/02-cache-invalidation-and-performance.md) — CDN caching, cache invalidation strategies, application-level caching, memoization, request-scoped caches
3. [Advanced Caching Systems](03-caching/03-advanced-caching-systems.md) — Cache stampede prevention, distributed cache coordination, multi-tier caching, production patterns

### 04 — Message Queues & Event-Driven Architecture

1. [Message Brokers: Kafka, SQS, RabbitMQ](04-message-queues/01-message-brokers-kafka-sqs-rabbitmq.md) — Broker fundamentals, Kafka architecture, SQS/SNS, RabbitMQ, broker selection guide, dead letter queues, retry strategies
2. [Event Sourcing, CQRS, and Sagas](04-message-queues/02-event-sourcing-cqrs-and-sagas.md) — Event sourcing patterns, projections, snapshots, CQRS read model strategies, saga pattern (choreography vs orchestration), compensating transactions
3. [Message Queue Operations and Patterns](04-message-queues/03-message-queue-operations-and-patterns.md) — Kafka internals (ISR, KRaft), outbox pattern, CDC with Debezium, event schema evolution, stream processing, event-driven microservices patterns

### 05 — Load Balancing & Networking

1. [Load Balancing Fundamentals](05-load-balancing/01-load-balancing-fundamentals.md) — L4 vs L7 load balancing, algorithms (round-robin, consistent hashing, least-connections), health checks, active vs passive monitoring
2. [Circuit Breakers and Retry Strategies](05-load-balancing/02-circuit-breakers-and-retry-strategies.md) — Circuit breaker states, bulkhead pattern, retry storm problem, retry budgets, exponential backoff with jitter, DNS routing, service mesh, gRPC vs REST vs GraphQL, API Gateway patterns
3. [Advanced Load Balancing Patterns](05-load-balancing/03-advanced-load-balancing-patterns.md) — nginx/HAProxy/Envoy configurations, TCP/IP internals, HTTP/2, HTTP/3 QUIC, TLS 1.3, CDN architecture, WebSocket load balancing, global load balancing

### 06 — Containers & Orchestration

1. [Docker and Containerization](06-containers-orchestration/01-docker-and-containerization.md) — Container internals (namespaces, cgroups, overlay filesystems), multi-stage builds, layer caching, BuildKit, distroless images, security scanning, Docker Compose
2. [Kubernetes Core and Operations](06-containers-orchestration/02-kubernetes-core-and-operations.md) — K8s architecture, workloads (Pods, Deployments, StatefulSets), networking, storage, scaling (HPA/VPA/KEDA), deployment strategies, resource management, debugging
3. [Kubernetes Advanced Patterns](06-containers-orchestration/03-kubernetes-advanced-patterns.md) — Helm, GitOps (ArgoCD vs Flux), CRDs and operators, service mesh deep dive, multi-cluster strategies, Kubernetes security (RBAC, Pod Security Standards, OPA/Gatekeeper)

### 07 — CI/CD & DevOps

1. [Pipeline Design and Deployment Strategies](07-cicd/01-pipeline-design-and-deployment-strategies.md) — Pipeline stages, parallel vs sequential execution, fail-fast strategies, artifact management, blue-green, canary, rolling deployments, GitHub Actions, branching strategies
2. [Feature Flags and Migrations](07-cicd/02-feature-flags-and-migrations.md) — Feature flag platforms and types, flag lifecycle and technical debt, database migrations (expand/contract), secrets management, dark launching, shadow traffic, chaos engineering
3. [Infrastructure and GitOps](07-cicd/03-infrastructure-and-gitops.md) — Terraform (state management, modules, Terragrunt), Pulumi, GitOps principles (four pillars), ArgoCD (ApplicationSets, sync waves), CI/CD security (supply chain, SLSA, Sigstore, SBOM), devcontainers, Tilt/Skaffold

### 08 — Observability

1. [Logging, Metrics, and Tracing](08-observability/01-logging-metrics-and-tracing.md) — The three pillars, structured logging, log levels, correlation IDs, RED method, USE method, Prometheus metric types, PromQL, OpenTelemetry auto-instrumentation and manual spans, sampling strategies, tracing backends
2. [SLOs, Alerting, and Incident Response](08-observability/02-slos-alerting-and-incident-response.md) — SLIs/SLOs/SLAs, error budgets, burn rate alerting, Prometheus alerting rules, alert fatigue, actionable alerts, severity levels, runbooks, incident commander role, blameless postmortems, dashboards
3. [Advanced Observability](08-observability/03-advanced-observability.md) — OTel Collector architecture (receivers, processors, exporters, pipelines), observability-driven development, continuous profiling, RUM vs synthetic monitoring, serverless observability, cost management, Datadog vs New Relic vs Grafana Stack

### 09 — Security at Scale

1. [Authentication and Authorization](09-security/01-authentication-and-authorization.md) — Zero trust architecture (four pillars, BeyondCorp), OAuth2/OIDC (authorization code, client credentials, token exchange flows), JWT validation at gateway vs service, service accounts, data encryption (at rest, in transit, field-level), secrets management (Vault, Kubernetes secrets, rotation)
2. [API and Application Security](09-security/02-api-and-application-security.md) — API gateway security (rate limiting, request validation, WAF), DDoS mitigation, OWASP API Security Top 10, security headers, security in CI/CD (SAST, DAST, SCA), container security (image hardening, Falco, pod security contexts)
3. [Compliance and Advanced Security](09-security/03-compliance-and-advanced-security.md) — Supply chain security (SBOM, signed artifacts, SLSA), SOC 2, GDPR, HIPAA, PCI DSS, threat modeling (STRIDE, attack trees, design review checklist), identity federation (SAML vs OIDC, workload identity), cert-manager, VPC design, security groups vs NACLs

### 10 — Classic System Design Problems

1. [Classic Design Problems](10-classic-problems/01-classic-design-problems.md) — Interview template, estimation formulas, components catalog, design patterns (fan-out, CQRS, sharding), URL shortener, chat system, news feed, rate limiter, notification system, file storage service
2. [Advanced Design Problems](10-classic-problems/02-advanced-design-problems.md) — Distributed task scheduler (exactly-once execution, priority queues, failure recovery), search autocomplete (trie data structure, ranking, real-time updates), video streaming platform (transcoding pipeline, ABR, CDN strategy, live streaming, recommendations)

---

## How to Use This Course

Each module file includes a **Related Reading** section at the end that cross-references other modules covering connected concepts. These links help you trace how a concept introduced in one module (e.g., consistent hashing in Module 02) appears in different contexts throughout the course (load balancing in Module 05, Redis Cluster in Module 03).

Module 10 (Classic System Design Problems) includes **Practice** sections that connect each design problem to the specific modules providing its building blocks, with hands-on exercises for estimation, scaling analysis, and failure scenario walkthroughs.

**Recommended approach:** Work through modules sequentially for a first pass, then use the cross-references to revisit topics from different angles as you encounter them in design problems.

---

## Prerequisites
- Experience deploying and operating production services
- Basic familiarity with cloud providers (AWS/GCP/Azure)
- Read [Module 00: Computing Fundamentals](00-computing-fundamentals.md) to ensure networking, databases, and distributed systems basics are solid
