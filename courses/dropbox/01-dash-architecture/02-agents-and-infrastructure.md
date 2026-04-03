# 02 – Agents and Infrastructure

How Dash goes beyond search into AI-powered actions. This module covers multi-step agents, the custom DSL/interpreter, the feature store architecture, and the infrastructure that makes it all work at Dropbox scale.

---

## 1. Multi-Step AI Agents

Dash isn't just a search engine — it uses **multi-step AI agents** to handle complex queries that require reasoning, not just retrieval.

### Simple Search vs. Agent Queries

| Query Type | Example | Approach |
|-----------|---------|----------|
| **Simple search** | "Q3 revenue report" | Lexical + semantic retrieval → rank → display |
| **Question answering** | "What was our Q3 revenue?" | Retrieve → RAG → generate answer with citation |
| **Multi-step reasoning** | "Compare our Q3 and Q4 revenue and identify the biggest changes" | Agent: retrieve Q3 doc → retrieve Q4 doc → extract numbers → compare → synthesize |

### Agent Architecture

```
User query
    → Intent classification: simple search vs. agent-worthy
    → If agent:
        → Plan generation (what steps are needed?)
        → Step 1: Search/retrieve relevant documents
        → Step 2: Extract specific information
        → Step 3: Perform analysis/comparison
        → Step N: Synthesize and format response
    → Each step can:
        - Search across connectors
        - Read and parse documents
        - Perform calculations
        - Generate intermediate text
        - Decide next step based on results
```

### Key Design Principles

- **Plan-then-execute** — the agent generates a plan before acting, enabling transparency and debugging
- **Grounded in retrieved data** — agents can only work with data from connected sources, never hallucinate facts
- **Fail gracefully** — if a step fails, the agent explains what it couldn't do rather than guessing
- **Observable** — each step is logged for debugging and quality improvement

---

## 2. Custom DSL and Interpreter

Dropbox built a **custom Python-like domain-specific language (DSL)** for agent code generation, along with a minimal Python interpreter with static analysis and runtime type enforcement.

### Why a Custom DSL?

Running arbitrary LLM-generated Python code is dangerous:
- **Security** — code injection, file system access, network calls
- **Reliability** — infinite loops, memory leaks, unhandled exceptions
- **Determinism** — same query should produce same plan
- **Observability** — need to trace exactly what the agent did

### How It Works

```
LLM generates agent plan as DSL code
    → Static analysis: validate types, check for disallowed operations
    → Sandboxed execution: custom interpreter runs the code
    → Runtime type enforcement: every value is type-checked
    → Resource limits: max execution time, memory, API calls
    → Results captured and returned to the user
```

### DSL Capabilities

The DSL looks like Python but with restrictions:
- **Allowed**: variables, loops, conditionals, function calls to approved APIs (search, extract, compare, summarize)
- **Disallowed**: file I/O, network access, imports, eval/exec, unbounded loops
- **Type system**: static types enforced at parse time AND runtime — catches errors early
- **API surface**: a curated set of operations (search, read_document, extract_field, compare, summarize, format_table)

**Interview angle:** This is a fascinating engineering decision. If asked about running AI-generated code safely, this pattern (restricted DSL + sandboxed interpreter + static analysis) is a strong answer.

---

## 3. Feature Store Architecture

The ranking and personalization models in Dash require features computed from diverse data sources. Dropbox built a feature store pipeline using Feast, Spark, and a custom serving layer.

### Three-Layer Architecture

```
┌─────────────────────────────────┐
│  Feature Definitions (Feast)     │  ← Schema: what features exist,
│  - Entity definitions            │     how they're computed,
│  - Feature views                 │     where they're stored
│  - On-demand transforms          │
└──────────┬──────────────────────┘
           │
    ┌──────┴──────┐
    ↓              ↓
┌────────┐   ┌──────────┐
│ Spark  │   │ Streaming │
│ (batch)│   │ (real-time)│
└───┬────┘   └─────┬─────┘
    │              │
    ↓              ↓
┌─────────────────────────────────┐
│  Dynovault (online serving)      │  ← Low-latency key-value store
│  - < 5ms lookups                 │     Custom-built by Dropbox
│  - High availability             │
│  - Feature versioning            │
└─────────────────────────────────┘
           │
           ↓
    XGBoost Ranking Model
```

### Feast (Orchestration)

- Open-source feature store framework
- Manages feature definitions: entity keys, feature schemas, data sources
- Handles materialization: moving computed features from batch/streaming into the online store
- Point-in-time correctness: ensures training data uses features from the correct time window (prevents data leakage)

### Spark (Batch Computation)

Computes features that don't need real-time freshness:
- **Document popularity scores** — aggregated view/click counts over time windows
- **Team usage patterns** — which teams access which types of content
- **Content quality signals** — document completeness, update frequency, link density
- **User preference profiles** — aggregated search and click history

These run on daily or hourly schedules and are materialized into Dynovault.

### Dynovault (Online Serving)

Dropbox's custom low-latency key-value store for serving features at query time:
- **< 5ms lookups** — critical for staying within the 2-second latency budget
- **High availability** — features must be available for every query
- **Feature versioning** — multiple feature versions can coexist during model rollouts
- **Built specifically for this use case** — not a general-purpose database

### Real-Time Features

Some features need to be fresh at query time:
- **User's recent searches** — personalization based on session context
- **Document freshness** — when was the content last updated?
- **Active connector status** — is the source app currently accessible?

These are computed via streaming pipelines and written directly to Dynovault.

---

## 4. Ranking Model Deep Dive

### XGBoost for Search Ranking

Dash uses XGBoost (gradient-boosted decision trees) as the primary ranking model.

**Why XGBoost over deep learning:**

| Factor | XGBoost | Neural Ranker |
|--------|---------|--------------|
| Inference speed | < 10ms per candidate set | 50-200ms |
| Feature engineering | Explicit, interpretable | Learned, opaque |
| Training data needs | Moderate | Large |
| Iteration speed | Fast (retrain in minutes) | Slow (hours/days) |
| Heterogeneous features | Excellent (mixes numeric, categorical, text scores) | Requires embedding |
| Debugging | Feature importance, SHAP values | Hard to interpret |

### Feature Categories

```
Relevance features:
  - BM25 score (lexical match quality)
  - Semantic similarity score (embedding distance)
  - Title match score
  - Exact phrase match
  - Query term coverage

Freshness features:
  - Document age (days since creation)
  - Last modified recency
  - Recency decay factor

Engagement features:
  - Historical CTR for this document
  - View count (normalized by age)
  - Share/collaboration count
  - Time-on-document after click

User context features:
  - User's team/org
  - User's recent search topics
  - User's frequently accessed connectors
  - Session context (related recent queries)

Source features:
  - Connector type (email vs doc vs message)
  - Source app reliability score
  - Content completeness score
```

### Training Pipeline

1. **Implicit feedback collection** — clicks, dwell time, reformulations, skip patterns
2. **Label generation** — clicked-and-dwelled = relevant, skipped = irrelevant, reformulated = partially relevant
3. **Feature computation** — Spark batch job computes training features with point-in-time correctness
4. **Model training** — XGBoost with learning-to-rank objective (LambdaMART or similar)
5. **Evaluation** — offline metrics (NDCG, MRR) + online A/B testing
6. **Deployment** — model artifact pushed to serving infrastructure, feature importance logged

---

## 5. Infrastructure at Dropbox Scale

### Magic Pocket

Dropbox's custom storage infrastructure, managing exabytes of data:
- Built in-house starting 2013, fully migrated from AWS S3 by 2016
- One of the largest cloud-to-own-infrastructure migrations in history
- Written in **Rust** and **Go**
- Designed for durability (99.999999999% — eleven 9s)
- Block-level deduplication and compression

**Relevance to Dash:** Magic Pocket stores file content. Dash's connectors for Dropbox native files read from Magic Pocket. Understanding the storage architecture shows systems depth.

### Smart Sync (Rust)

The file sync engine, rewritten in Rust:
- 25% CPU reduction over the previous implementation
- 50% improvement in file indexing latencies
- Handles conflict resolution for concurrent edits
- Differential sync: only transfer changed blocks, not entire files

### Metaserver → Atlas Migration

The backend architecture is in transition:

| | Metaserver | Atlas |
|--|-----------|-------|
| Architecture | Python monolith | Managed serverless platform |
| Deploy | Single deployable | Independent services |
| Scaling | Vertical | Horizontal per service |
| New features | Added to monolith | Built as Atlas services |

Dash is likely built on Atlas, meaning:
- Independent service boundaries
- Auto-scaling per endpoint
- Clear API contracts between services
- Modern deployment patterns (canary, blue-green)

---

## 6. Interview-Ready Talking Points

1. **"How do agents differ from RAG?"** — RAG is single-step retrieval + generation. Agents do multi-step reasoning: planning, retrieving from multiple sources, extracting, comparing, and synthesizing. RAG is a tool agents use, not a replacement for them.

2. **"Why build a custom DSL instead of using Python?"** — Security (no arbitrary code execution), reliability (resource limits, type checking), observability (every operation is traced), and determinism (same plan produces same execution).

3. **"Why Feast + custom serving vs. an off-the-shelf solution?"** — Scale and latency requirements. Feast handles feature orchestration. Dynovault handles sub-5ms serving. Off-the-shelf solutions couldn't meet the latency budget at Dropbox's scale.

4. **"How do you iterate on ranking quality?"** — Implicit feedback (clicks, dwell time) → label generation → feature engineering → XGBoost retraining → offline evaluation (NDCG) → online A/B test → ship. Fast iteration cycle because XGBoost trains in minutes, not hours.

5. **"What's the biggest infrastructure challenge for Dash?"** — Connector diversity at scale. Each source app has different APIs, rate limits, auth models, and content formats. Maintaining freshness and permission accuracy across 60+ connectors while keeping latency under 2 seconds is the core challenge.
