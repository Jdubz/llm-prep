# 01 – RAG and Search Pipeline

How Dropbox Dash finds relevant information across 60+ connected apps in under 2 seconds. This module covers the retrieval architecture — hybrid search, chunking strategy, semantic reranking, and the end-to-end query flow.

---

## 1. The Problem: Search Across Everything

Traditional enterprise search indexes one corpus (emails, files, or messages). Dash indexes all of them simultaneously, each with different:
- **Schemas** — a Slack message and a Google Doc have nothing in common structurally
- **Access controls** — permissions from 60+ apps must be respected in real-time
- **Freshness requirements** — a Slack message from 5 minutes ago should be searchable now
- **Content types** — text, images, audio, video, structured data

The architecture must handle all of this at sub-2-second response time for 95th percentile queries.

---

## 2. Hybrid Retrieval Strategy

Dash uses a **two-stage retrieval pipeline**: fast lexical search first, then semantic reranking.

### Stage 1: Lexical Retrieval (Fast Path)

```
Query: "Q3 revenue forecast"
    → Tokenize + normalize
    → BM25/inverted index lookup across all connected sources
    → Return top-K candidates (fast, high recall, moderate precision)
    → Latency budget: < 200ms
```

**Why lexical first:** It's fast, handles exact matches well (file names, people names, error codes), and provides a broad candidate set for the reranker.

**Inverted index per connector:** Each connected app has its own index partition. Query fans out to relevant partitions based on user's connected apps and optional filters (e.g., "only Slack").

### Stage 2: Semantic Reranking (Precision Path)

```
Top-K lexical candidates
    → Generate query embedding (dense vector)
    → Score each candidate: combine lexical score + semantic similarity + freshness + engagement signals
    → Rerank to produce final ordering
    → Latency budget: < 1.5s total (including Stage 1)
```

**Why not semantic-only:** Pure vector search has issues:
- Misses exact matches (searching for "PROJ-1234" needs lexical, not semantic)
- Embedding quality varies across content types
- Higher latency and cost at scale
- Cold-start: new content needs time to embed

**The hybrid advantage:** Lexical catches what semantic misses (exact terms, proper nouns), semantic catches what lexical misses (conceptual similarity, synonyms, paraphrases).

---

## 3. Chunking Strategy

Dash uses **on-the-fly chunking at query time**, not static pre-processing. This is a deliberate architectural choice.

### Why On-the-Fly

| Approach | Pros | Cons |
|----------|------|------|
| **Pre-chunked** (traditional) | Fast at query time, embeddings pre-computed | Stale chunks when content updates, storage overhead, chunk boundary issues |
| **On-the-fly** (Dash) | Always fresh, adapts chunk size to query context, no stale data | Higher query-time compute, requires fast content access |

### How It Works

1. Lexical retrieval identifies relevant **documents** (not chunks)
2. Documents are fetched from the connector cache
3. Content is chunked dynamically based on:
   - Document structure (headers, paragraphs, code blocks)
   - Query context (longer chunks for broad questions, shorter for specific lookups)
   - Content type (email = per-message, doc = per-section, Slack = per-thread)
4. Chunks are embedded and scored against the query
5. Best chunks become the context for AI answer generation

**Interview angle:** This is a meaningful architectural decision. Be prepared to discuss trade-offs: freshness vs. latency, compute cost vs. storage cost, and when you'd choose each approach.

---

## 4. Embedding and Ranking

### Embedding Model

- Model-agnostic architecture — not locked to one embedding provider
- Dense embeddings for semantic similarity
- Likely using a transformer-based model (BERT-family or similar) fine-tuned on workplace content
- Separate embedding spaces may exist for different content types

### Ranking Model (XGBoost)

The final ranking isn't just semantic similarity. Dash uses **XGBoost** (gradient-boosted decision trees) as the ranking model, with features from multiple signals:

| Signal Category | Features |
|----------------|----------|
| **Relevance** | BM25 score, semantic similarity, title match, exact phrase match |
| **Freshness** | Document age, last modified time, recency decay |
| **Engagement** | Click-through rate, view count, share count, time-on-document |
| **User context** | User's team, recent search history, frequently accessed apps |
| **Source quality** | Connector reliability, content completeness, permission confidence |

**Why XGBoost over a neural ranker:** Fast inference (< 10ms per candidate set), interpretable feature importance, easy to iterate on features, works well with heterogeneous feature types.

### Feature Store Architecture

The features feeding the ranking model are served by a purpose-built feature store:

```
Batch features (Spark)         Real-time features (streaming)
        ↓                              ↓
    Feast (orchestration layer)
        ↓
    Dynovault (low-latency online serving)
        ↓
    XGBoost ranking model
```

- **Feast**: Open-source feature store framework — manages feature definitions, handles batch/streaming ingestion, serves features at low latency
- **Spark**: Computes batch features (daily/hourly aggregations — document popularity, team usage patterns)
- **Dynovault**: Dropbox's custom low-latency key-value store for online feature serving (< 5ms lookups)

---

## 5. AI Answer Generation

When a user asks a question (not just a keyword search), Dash generates an AI answer using RAG:

### RAG Flow

```
User question
    → Hybrid retrieval (top-K relevant chunks)
    → Chunk selection (most relevant passages)
    → Prompt construction:
        System prompt + user question + selected chunks with source attribution
    → LLM generation (model-agnostic)
    → Post-processing:
        - Citation extraction and verification
        - Hallucination detection (cross-reference claims against source chunks)
        - Formatting (markdown, links, source cards)
    → Response streaming to UI
```

### Key Design Decisions

- **Always cite sources** — every claim in an AI answer links back to the source document. This builds trust.
- **Model-agnostic** — Dash can swap LLM providers without changing the pipeline. This is strategic flexibility.
- **Streaming responses** — AI answers stream token-by-token to reduce perceived latency.
- **Fallback to search** — if the question is better served by traditional search results (e.g., "find my tax document"), skip AI answer generation.

### Hallucination Mitigation

- Retrieved chunks are the only context — no parametric knowledge from the LLM
- Post-generation verification: check that claims can be grounded in source chunks
- Confidence scoring: low-confidence answers show "I found relevant documents but couldn't answer definitively"
- User feedback loop: thumbs up/down on AI answers feeds back into ranking quality

---

## 6. Connector Architecture (Data Freshness)

### How Data Stays Fresh

Each connector maintains freshness through a combination of:

1. **Webhooks** (real-time) — where the source app supports them (Slack, GitHub, Jira). Content updates are pushed to Dash within seconds.
2. **Polling** (near-real-time) — periodic API calls to check for changes. Frequency depends on the source app's rate limits and the user's plan tier.
3. **Full resync** (periodic) — complete re-crawl to catch anything missed by incremental updates. Runs daily or weekly depending on connector.

### Permission Enforcement

This is critical — showing a user a document they shouldn't have access to is a trust-destroying bug.

```
Query arrives
    → Identify user's connected accounts and permissions
    → Fan out to connector indexes
    → Each connector filters results by user's permissions in the source app
    → Merge and rank only permitted results
    → Display results with source attribution
```

Permissions are synced from source apps and cached, but verified at query time for sensitive operations. If a user loses access to a Google Doc, it should stop appearing in Dash results promptly.

---

## 7. Performance Architecture

### Latency Budget (2-Second Target)

| Phase | Budget | What Happens |
|-------|--------|-------------|
| Query parsing + routing | 50ms | Tokenize, identify intent, fan out to connectors |
| Lexical retrieval | 200ms | BM25 lookup across connector indexes |
| Content fetch + chunking | 500ms | Retrieve documents, chunk on-the-fly |
| Embedding + reranking | 300ms | Embed chunks, XGBoost scoring |
| AI answer generation | 800ms+ | LLM generation (streamed, so first tokens appear earlier) |
| **Total (search results)** | **~1s** | Results appear before AI answer |
| **Total (with AI answer)** | **~2s** | First tokens of AI answer stream |

### Key Optimizations

- **Parallel fan-out** — query all connector indexes simultaneously
- **Streaming** — search results render immediately; AI answer streams in after
- **Caching** — recent queries, popular documents, user session state
- **Progressive rendering** — show instant suggestions → search results → AI answer
- **Early termination** — if top results have high enough confidence, skip lower-ranked connectors

---

## 8. Interview-Ready Talking Points

1. **"Why hybrid retrieval?"** — Lexical handles exact matches and proper nouns; semantic handles conceptual similarity. Combined gives best precision and recall across diverse content types.

2. **"Why on-the-fly chunking?"** — Freshness guarantee. Pre-chunked content goes stale when documents update. On-the-fly adds query-time compute but eliminates stale data.

3. **"Why XGBoost for ranking?"** — Fast inference, interpretable features, works with heterogeneous signals (relevance + freshness + engagement). Easy to iterate.

4. **"How do you handle permissions at scale?"** — Permission-aware index partitioning per connector. Filter at retrieval time, not post-retrieval. Cache permissions but verify for sensitive operations.

5. **"What's the hardest part of building Dash?"** — The connector diversity. Each source app has different schemas, auth models, rate limits, and content types. Building a unified search experience across all of them is the core challenge.
