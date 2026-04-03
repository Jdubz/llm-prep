# Dropbox — Full Stack Software Engineer, Dash Experiences

Interview preparation for the Full Stack Software Engineer role on Dropbox's Dash Experiences team. Covers Dropbox Dash (AI-powered universal search), the full-stack tech stack, coding interviews, system design, and behavioral prep.

> **Perspective**: You're an experienced full-stack engineer with AI/LLM knowledge. This course focuses on Dropbox-specific product context (Dash), their interview pipeline (CodeSignal OA + onsite loop), and the full-stack skills (React/TypeScript + Python/Go) that this role demands.
>
> **Prerequisites**: [React](../react/), [Node.js & TypeScript](../nodejs/), [Python](../python/), [LLM Engineering](../llms/), [General Interview Techniques](../general-interview/)

---

## Modules

### 00 — Company & Product
- [01 – Company Overview](./00-company-and-product/01-company-overview.md) — Dropbox's business, Virtual First culture, tech stack, engineering career framework
- [02 – Dash Product Deep Dive](./00-company-and-product/02-dash-product-deep-dive.md) — What Dash is, product features, strategic importance, the Dash Experiences team

### 01 — Dash Architecture
- [01 – RAG and Search Pipeline](./01-dash-architecture/01-rag-and-search-pipeline.md) — Hybrid retrieval, on-the-fly chunking, semantic reranking, sub-2s latency target
- [02 – Agents and Infrastructure](./01-dash-architecture/02-agents-and-infrastructure.md) — Multi-step AI agents, custom DSL/interpreter, feature store (Feast/Spark/Dynovault), XGBoost ranking

### 02 — Full Stack Fundamentals
- [01 – Frontend Patterns](./02-full-stack-fundamentals/01-frontend-patterns.md) — React + TypeScript, API-QL (client-side GraphQL), search/AI UI patterns, testing
- [02 – Backend Patterns](./02-full-stack-fundamentals/02-backend-patterns.md) — Python monolith (Metaserver) to Atlas, Go services, API design, data pipeline patterns

### 03 — Coding Interview
- [01 – CodeSignal OA Guide](./03-coding-interview/01-codesignal-oa-guide.md) — Format, Cosmo AI assistant (required), 4 questions in 60 min, strategy
- [02 – Classic Dropbox Problems](./03-coding-interview/02-classic-dropbox-problems.md) — Id Allocator, Game of Life, Web Crawler, Token Bucket, Hit Counter, Find Duplicate Files
- [03 – Algorithm Patterns](./03-coding-interview/03-algorithm-patterns.md) — Key DS&A patterns: DFS/BFS, DP, backtracking, heaps, sliding window, concurrency

### 04 — System Design
- [01 – File Sync and Storage](./04-system-design/01-file-sync-and-storage.md) — Design Dropbox: chunking, sync protocol, conflict resolution, Magic Pocket storage
- [02 – Search Infrastructure](./04-system-design/02-search-infrastructure.md) — Design Dash: universal search, RAG at scale, connector architecture, ranking pipeline

### 05 — Behavioral & Interview Prep
- [01 – Values and Culture](./05-behavioral-and-interview-prep/01-values-and-culture.md) — AOWE framework, Virtual First, career archetypes, impact framework
- [02 – Interview Process and Strategy](./05-behavioral-and-interview-prep/02-interview-process-and-strategy.md) — Full pipeline walkthrough, stage-by-stage tips, story bank, questions to ask, day-of checklist

---

## Content Per Module

Each module directory contains numbered files:

- **`01-*.md`** — Foundational concepts, architecture, and mental models.
- **`02-*.md`** — Applied patterns, workflows, and practical depth.
- **`03-*.md`** — Advanced patterns and interview-specific content (where applicable).

---

## Cross-References to Existing Courses

- `courses/react/` — Advanced React patterns (Dash frontend is React + TypeScript)
- `courses/nodejs/` — TypeScript fundamentals and Node.js patterns
- `courses/python/` — Python backend patterns (Metaserver is Python)
- `courses/golang/` — Go for backend services
- `courses/llms/` — RAG, embeddings, agents (core Dash technology)
- `courses/infrastructure/` — System design, databases, caching, scaling
- `courses/general-interview/` — Behavioral prep, communication, negotiation
- `codesignal-drills/` — CodeSignal practice environment

## Study Plan

| Priority | Module | Time | Focus |
|----------|--------|------|-------|
| 1 | 05 — Behavioral & Interview Prep | 2 hrs | Understand the full pipeline, prep STAR stories |
| 2 | 03 — Coding Interview | 4 hrs | CodeSignal OA prep, drill classic Dropbox problems |
| 3 | 04 — System Design | 3 hrs | File sync + search infrastructure design practice |
| 4 | 00 — Company & Product | 1.5 hrs | Know Dash inside-out, show genuine product interest |
| 5 | 01 — Dash Architecture | 2 hrs | Technical depth on RAG, agents, ranking |
| 6 | 02 — Full Stack Fundamentals | 2 hrs | Dropbox-specific stack patterns |

## Prerequisites
- [React](../react/) — hooks, performance, patterns
- [Node.js & TypeScript](../nodejs/) — TypeScript fundamentals
- [Python](../python/) — Python backend patterns
- [LLM Engineering](../llms/) — RAG, agents, embeddings
- [General Interview Techniques](../general-interview/) — behavioral prep, negotiation

## Status
**Content complete** — all modules written with interview-focused depth.
