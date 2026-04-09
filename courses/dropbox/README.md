# Dropbox — Full Stack Software Engineer, Dash Experiences

Interview preparation for the Full Stack Software Engineer role on Dropbox's Dash Experiences team. Covers Dropbox Dash (AI-powered universal search), the full-stack tech stack, coding interviews, system design, and behavioral prep.

> **Perspective**: You're an experienced full-stack engineer with AI/LLM knowledge. **This role leans frontend-heavy** — the listing requires React/TypeScript/HTML/CSS experience and treats backend (Python/Go) as a preferred-not-required qualification. Six of ten listed responsibilities are explicitly frontend: responsive UIs, performance optimization, designer collaboration, and building interactive AI interfaces. Prepare accordingly — lead with frontend depth, backend as supporting context.
>
> **Prerequisites**: [React](../react/) *(critical path)*, [Node.js & TypeScript](../nodejs/), [Python](../python/), [LLM Engineering](../llms/), [General Interview Techniques](../general-interview/)
>
> **Job Listing**: [Full Stack Software Engineer, Dash Experiences](https://www.dropbox.jobs/en/jobs/7569140/full-stack-software-engineer-dash-experiences/) (Job ID 7569140)

---

## Modules

### 00 — Company & Product
- [01 – Company Overview](./00-company-and-product/01-company-overview.md) — Dropbox's business, Virtual First culture, tech stack, engineering career framework
- [02 – Dash Product Deep Dive](./00-company-and-product/02-dash-product-deep-dive.md) — What Dash is, product features, strategic importance, the Dash Experiences team

### 01 — Dash Architecture
- [01 – RAG and Search Pipeline](./01-dash-architecture/01-rag-and-search-pipeline.md) — Hybrid retrieval, on-the-fly chunking, semantic reranking, sub-2s latency target
- [02 – Agents and Infrastructure](./01-dash-architecture/02-agents-and-infrastructure.md) — Multi-step AI agents, custom DSL/interpreter, feature store (Feast/Spark/Dynovault), XGBoost ranking

### 02 — Full Stack Fundamentals
- [01 – Frontend Patterns](./02-full-stack-fundamentals/01-frontend-patterns.md) — Confirmed Dropbox stack (DIG, Redux, SCSS/BEM, Edison, Rollup), API-QL, CSS & responsive design, AI UX patterns, frontend performance, designer collaboration, data-driven decisions, vanilla JS & React interview prep *(high priority — role is frontend-heavy)*
- [02 – Backend Patterns](./02-full-stack-fundamentals/02-backend-patterns.md) — Python monolith (Metaserver) to Atlas, Go services, API design, data pipeline patterns *(familiarity level — backend is preferred, not required)*

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

### 06 — Exercises & Practice
- [01 – Coding Challenges](./06-exercises-and-practice/01-coding-challenges.md) — 10 Dropbox-flavored problems with hints, solutions, and follow-ups + OA simulation set
- [02 – System Design Exercises](./06-exercises-and-practice/02-system-design-exercises.md) — 4 timed design drills with scaling deep-dive probes + 10 quick-fire questions (5 general + 5 scaling-focused)
- [03 – Knowledge Quizzes](./06-exercises-and-practice/03-knowledge-quizzes.md) — 7 quizzes (38 questions) covering every module, with scoring and study priority guidance
- [04 – Project Deep Dive Prep](./06-exercises-and-practice/04-project-deep-dive-prep.md) — Structured worksheets for the 1-hour project presentation round, with fill-in exercises
- [05 – Mock Interview Scripts](./06-exercises-and-practice/05-mock-interview-scripts.md) — Full scripts for all 5 interview stages, with evaluation rubrics and a mock schedule
- [06 – Scaling at Dropbox Scale](./06-exercises-and-practice/06-scaling-at-dropbox-scale.md) — Mental models, vocabulary, back-of-envelope math, and scaling patterns for reasoning about 700M-user systems

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

### Confirmed Interview Format (from recruiter screen)

**Day 1 (must pass to proceed):**
1. **Frontend Coding** — React/TypeScript (1 hr)
2. **Full Stack Coding** — React/TypeScript + Python (1 hr)
3. **Project Deep Dive** — you select a project, go deep into architecture & structure (1 hr)

**Day 2 (leveling):** Behavioral + System Design (IC4+ only)

### Study Plan

| Priority | Module | Time | Focus |
|----------|--------|------|-------|
| 1 | 02 — Frontend Patterns | 4 hrs | React/TS coding challenges (autocomplete, hooks), CSS, AI UX, DIG/Redux/SCSS stack — **both coding rounds test React** |
| 2 | 03 — Coding Interview | 3 hrs | Classic Dropbox problems in Python (for Interview 2), algorithm patterns |
| 3 | 06 — Exercises: Project Deep Dive Prep | 3 hrs | Select project, practice architecture walkthrough, prepare for deep probing |
| 4 | 05 — Behavioral & Interview Prep | 2 hrs | AOWE, STAR stories, 0→1 mindset, full pipeline |
| 5 | 00 — Company & Product | 1.5 hrs | Know Dash inside-out, show genuine product interest |
| 6 | 04 — System Design | 3 hrs | File sync + search infrastructure (Day 2, IC4+ only) |
| 7 | 01 — Dash Architecture | 1.5 hrs | Conceptual understanding of RAG, agents, ranking |
| 8 | 02 — Backend Patterns | 1 hr | Familiarity level — API design, connector lifecycle |
| 9 | 06 — Exercises & Practice | 6+ hrs | Coding challenges, quizzes, mock interviews (spread across study days) |

## Prerequisites
- [React](../react/) — hooks, performance, patterns
- [Node.js & TypeScript](../nodejs/) — TypeScript fundamentals
- [Python](../python/) — Python backend patterns
- [LLM Engineering](../llms/) — RAG, agents, embeddings
- [General Interview Techniques](../general-interview/) — behavioral prep, negotiation

## Status
**Content complete** — all modules written with interview-focused depth, plus exercises and mock interviews.
