# Temporal Technologies — Interview Study Track

**Role**: Senior Software Engineer — Billing, Metering & Cloud Nexus
**Team**: Product scalability, customer experience, and revenue growth
**Stack**: Go, PostgreSQL, Redshift, Kinesis, S3, Kubernetes, Stripe, Metronome, Temporal

> This study track is tailored to a specific role on the team that owns billing/metering, customer onboarding/offboarding, cloud marketplace integrations, and Cloud Nexus.

---

## Modules

### 01 — Company & Product
- Temporal's mission, open-source model, business model
- Durable execution: what it is and why it matters
- Temporal Cloud vs self-hosted, competitive landscape
- Server architecture: Frontend, History, Matching, Worker services
- Company values and how to demonstrate them in interviews

### 02 — Temporal SDK Patterns
- Core primitives: workflows, activities, workers, task queues, namespaces
- Determinism constraints and workflow replay
- Signals, queries, updates, child workflows, continue-as-new
- Saga pattern, workflow versioning, advanced concurrency
- Billing/metering-specific Temporal patterns

### 03 — Go for Systems Engineering
- Go mental model for TypeScript engineers
- Concurrency: goroutines, channels, select, sync, context
- Interfaces, composition, error handling patterns
- Database patterns, gRPC, testing strategies
- Production Go: logging, shutdown, health checks

### 04 — Billing & Metering Systems
- Usage-based billing architecture (metering → aggregation → rating → invoicing)
- Metering pipeline design: event collection, deduplication, aggregation
- Stripe integration patterns, Metronome, marketplace billing
- Data integrity: double-entry bookkeeping, audit trails, reconciliation
- Customer lifecycle management

### 05 — Data Systems
- PostgreSQL at scale: indexing, partitioning, replication
- Redshift: columnar storage, distribution, sort keys
- Kinesis: streaming pipelines, exactly-once processing
- S3/GCS/Azure Blob: multi-cloud object storage
- Data pipeline patterns: ETL, CDC, backfill, monitoring

### 06 — Platform Architecture
- Multi-cloud platform design (Cloud Nexus domain)
- API abstraction layers, tenant isolation
- Self-service platform: onboarding, provisioning automation
- Control plane vs data plane separation
- Multi-region, cell-based architecture

### 07 — Interview Prep
- Technical questions with answer frameworks (Temporal, Go, distributed systems, billing)
- Behavioral questions mapped to Temporal's 5 values
- System design walkthroughs: metering pipeline, billing system, Cloud Nexus
- Questions to ask, red flags to avoid, day-before checklist

---

## Study Plan

### Priority Order (if short on time)
1. **01 Company & Product** — You must know what Temporal does (2 hrs)
2. **02 Temporal SDK Patterns** — Demonstrate product expertise (3 hrs)
3. **04 Billing & Metering** — The team's core domain (3 hrs)
4. **07 Interview Prep** — Practice system designs and questions (3 hrs)
5. **03 Go for Systems** — Language proficiency (2 hrs)
6. **05 Data Systems** — Infrastructure knowledge (2 hrs)
7. **06 Platform Architecture** — Cloud Nexus context (1.5 hrs)

### Cross-References to Existing Courses
- `courses/golang/` — Go language fundamentals
- `courses/infrastructure/02-databases-at-scale/` — Database scaling patterns
- `courses/infrastructure/04-message-queues/` — Kafka, event sourcing, CQRS
- `courses/infrastructure/06-containers-orchestration/` — Kubernetes
- `courses/infrastructure/08-observability/` — Monitoring, tracing, alerting

---

## Content Per Module

Each module directory contains:

- **`README.md`** — Core interview knowledge. Concise, pattern-focused, interview-ready.
- **`deep-dive.md`** — Extended content. Architecture internals, advanced patterns.
- **`cheat-sheet.md`** — Quick reference card. Scannable the night before.
