# Infrastructure & Architecture Scaling

System design, infrastructure, and scaling patterns for senior engineers. Covers the architecture knowledge needed for staff-level interviews — from single-server to distributed systems, with emphasis on practical trade-offs over theoretical purity.

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
- Structured approach to system design interviews
- Requirements gathering: functional vs non-functional
- Back-of-the-envelope estimation (QPS, storage, bandwidth)
- Communication strategies: top-down vs bottom-up
- Common pitfalls and how to avoid them

### 02 — Databases at Scale
- SQL vs NoSQL: when each makes sense (not religion)
- Indexing strategies, query optimization, EXPLAIN plans
- Sharding: horizontal partitioning, consistent hashing, shard keys
- Replication: leader-follower, multi-leader, conflict resolution
- CAP theorem in practice (not just theory)
- Database-specific deep dives: PostgreSQL, DynamoDB, Redis

### 03 — Caching Strategies
- Cache-aside, write-through, write-behind patterns
- Redis architecture: clustering, persistence, eviction policies
- CDN caching: edge, origin, cache invalidation
- Application-level caching: memoization, request-scoped caches
- Cache stampede prevention (locking, probabilistic expiration)

### 04 — Message Queues & Event-Driven Architecture
- Kafka: partitions, consumer groups, exactly-once semantics
- SQS/SNS, RabbitMQ, NATS — when to use what
- Event sourcing and CQRS patterns
- Dead letter queues and retry strategies
- Saga pattern for distributed transactions

### 05 — Load Balancing & Networking
- L4 vs L7 load balancing
- Health checks, circuit breakers, retry budgets
- DNS-based routing, GeoDNS
- Service mesh concepts (Istio/Linkerd)
- gRPC vs REST vs GraphQL at scale

### 06 — Containers & Orchestration
- Docker: multi-stage builds, layer caching, security scanning
- Kubernetes: pods, deployments, services, ingress
- Helm charts and GitOps (ArgoCD/Flux)
- Resource limits, HPA, cluster autoscaling
- Service discovery and configuration management

### 07 — CI/CD & DevOps
- Pipeline design: build, test, deploy stages
- Blue-green, canary, and rolling deployments
- Feature flags and progressive rollouts
- Infrastructure as Code: Terraform, Pulumi
- Secrets management (Vault, AWS Secrets Manager)

### 08 — Observability
- The three pillars: logs, metrics, traces
- Structured logging and log aggregation (ELK, Datadog)
- Metrics: RED method, USE method, SLIs/SLOs/SLAs
- Distributed tracing with OpenTelemetry
- Alerting strategies: reducing noise, actionable alerts
- Incident response and postmortems

### 09 — Security at Scale
- Zero trust architecture
- OAuth2/OIDC flows in distributed systems
- API gateway patterns (rate limiting, auth, transformation)
- WAF, DDoS mitigation
- Data encryption: at rest, in transit, field-level
- Compliance considerations (SOC2, GDPR basics)

### 10 — Classic System Design Problems
- URL shortener (sharding, analytics, rate limiting)
- Chat system (WebSocket, presence, message ordering)
- News feed / timeline (fan-out, ranking, caching)
- Rate limiter (token bucket, sliding window, distributed)
- Notification system (multi-channel, templating, delivery guarantees)
- File storage service (chunking, deduplication, CDN)

---

## Prerequisites
- Experience deploying and operating production services
- Basic familiarity with cloud providers (AWS/GCP/Azure)
- Read [Module 00: Computing Fundamentals](00-computing-fundamentals.md) to ensure networking, databases, and distributed systems basics are solid

## Status
**Scaffolded** — module outlines complete, content to be written.
