# 02 – Search Infrastructure

"Design a universal search system like Dash" — this is the system design question most specific to the role. It tests your understanding of search, AI/ML infrastructure, and distributed systems.

---

## 1. Requirements Clarification

### Functional Requirements
- Search across 60+ connected third-party apps from a single search bar
- AI-powered answers to natural language questions
- Results ranked by relevance, freshness, and user context
- Respect source app permissions (never show unauthorized content)
- Near-real-time indexing (new content searchable within minutes)

### Non-Functional Requirements
- **Latency** — search results in < 1s, AI answers start streaming in < 2s
- **Scale** — millions of users, each with 10+ connected apps, billions of documents
- **Freshness** — content updated in source apps should be searchable within minutes
- **Accuracy** — relevant results ranked high, irrelevant results filtered out
- **Privacy** — data stays within user's trust boundary, permissions enforced

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client (Web/Desktop)                  │
│  [Search Bar] [Result List] [AI Answer Panel] [Filters]      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│  Rate limiting, auth, routing                                │
└────┬──────────────┬──────────────────┬──────────────────────┘
     ↓              ↓                  ↓
┌─────────┐  ┌──────────────┐  ┌──────────────────┐
│ Search  │  │ AI Answer    │  │ Connector        │
│ Service │  │ Service      │  │ Management       │
│         │  │ (RAG)        │  │ Service          │
└────┬────┘  └──────┬───────┘  └──────┬───────────┘
     │              │                  │
     ↓              ↓                  ↓
┌─────────────────────────────────────────────────────────────┐
│                    Search Index Layer                         │
│  [Inverted Index (lexical)] [Vector Index (semantic)]        │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│                      ↓                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Gmail    │  │ Slack    │  │ GDrive   │  │ Jira     │    │
│  │Connector │  │Connector │  │Connector │  │Connector │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│                  Connector Layer                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Connector Layer

### Connector Design

Each third-party integration is a connector microservice:

```
ConnectorService {
    // Auth
    oauth_authorize(user_id, redirect_url) → auth_url
    oauth_callback(code) → access_token, refresh_token
    
    // Sync
    initial_sync(user_id) → stream of documents
    incremental_sync(user_id, since) → stream of changes
    handle_webhook(event) → processed changes
    
    // Permission
    check_access(user_id, document_id) → bool
    sync_permissions(user_id) → permission_map
}
```

### Connector Lifecycle

```
Connect:   OAuth2 flow → store tokens → trigger initial sync
Sync:      Webhooks (real-time) + polling (catch-up) + full resync (weekly)
Refresh:   Token expiration → automatic refresh → retry failed operations
Disconnect: Revoke tokens → delete indexed content → clean up permissions
```

### Data Normalization

Every source produces different document schemas. Connectors normalize to a unified format:

```python
@dataclass
class UnifiedDocument:
    id: str                  # globally unique
    source: str              # "gmail", "slack", "gdrive"
    source_id: str           # ID in the source system
    title: str               # document title or subject
    content: str             # extracted text content
    content_type: str        # "email", "message", "document", "ticket"
    author: str              # who created/sent it
    participants: list[str]  # who's involved
    url: str                 # link back to source
    created_at: datetime
    updated_at: datetime
    permissions: PermissionSet  # who can see this
    metadata: dict           # source-specific fields
```

---

## 4. Indexing Pipeline

### Document Processing Flow

```
Connector produces document
    → Message Queue (Kafka)
    → Index Workers consume:
        1. Extract searchable text
        2. Compute document hash (for dedup)
        3. Generate embedding vector
        4. Build inverted index entry
        5. Store in both lexical + vector indexes
        6. Update permission index
    → Document searchable in < 5 minutes
```

### Dual Index Architecture

**Inverted Index (Lexical Search):**
- BM25 scoring for keyword relevance
- Partitioned by user_id (each user's documents in their partition)
- Technology: Elasticsearch or similar

**Vector Index (Semantic Search):**
- Dense embeddings for conceptual similarity
- Approximate nearest neighbor (ANN) search
- Technology: FAISS, Pinecone, or custom solution
- Same user_id partitioning for permission enforcement

### Why Both Indexes?

| Query Type | Better Index |
|-----------|-------------|
| "PROJ-1234" | Lexical (exact match) |
| "Q3 revenue report" | Lexical (keyword match) |
| "how to request time off" | Semantic (conceptual) |
| "onboarding checklist for new hires" | Semantic (conceptual) |
| "John's email about the merger" | Both (entity + concept) |

---

## 5. Query Processing

### Search Flow

```
User submits query: "What was our Q3 revenue?"
    │
    ├─ [Parallel] Lexical search
    │   → BM25 query across user's index partitions
    │   → Top-100 candidates, 200ms
    │
    ├─ [Parallel] Semantic search
    │   → Embed query → ANN search
    │   → Top-100 candidates, 300ms
    │
    └─ Merge + Rerank
        → Deduplicate candidates
        → Permission filter (drop anything user can't access)
        → XGBoost ranking model scores all candidates
        → Top-25 results returned to client
        │
        ├─ [Stream to client immediately]
        │
        └─ [Async] AI Answer generation
            → Top-5 results as context
            → LLM generates answer with citations
            → Stream tokens to client
```

### Permission Enforcement

**Pre-retrieval filtering** (preferred):
- Index is partitioned by user
- Each partition only contains documents the user has access to
- Permission changes trigger re-indexing

**Post-retrieval filtering** (fallback):
- Retrieve candidates, then check permissions
- More expensive but handles complex permission models
- Always the safety net even with pre-filtering

### Ranking Pipeline

```
Candidates from lexical + semantic search
    ↓
Feature extraction:
    - Lexical relevance (BM25 score)
    - Semantic similarity (cosine distance)
    - Freshness (recency decay)
    - User engagement history
    - Source reliability
    - Title match quality
    ↓
XGBoost model prediction
    ↓
Final ranked list
```

---

## 6. AI Answer Service (RAG)

### Architecture

```
Top-K search results
    → Chunk selection:
        - Extract most relevant passages from top documents
        - On-the-fly chunking for freshness
        - Select 3-5 chunks that best answer the query
    → Prompt construction:
        System: "Answer based only on the provided sources. Cite sources."
        User: original query
        Context: selected chunks with source attribution
    → LLM generation (streaming)
    → Post-processing:
        - Extract and verify citations
        - Detect unsupported claims
        - Format with source links
    → Stream to client
```

### Quality Signals

| Signal | What to Monitor |
|--------|----------------|
| **Answer quality** | User thumbs up/down, time spent reading |
| **Citation accuracy** | % of claims grounded in sources |
| **Query coverage** | % of queries that produce an AI answer |
| **Latency** | Time to first token, total generation time |
| **Fallback rate** | % of queries where AI declines to answer |

---

## 7. Scaling Deep Dive

### Index Scaling

**Sharding strategy:** Shard by user_id.
- Each user's documents are co-located on the same shard
- Queries only hit one shard (single-user search)
- Rebalance shards as users grow/shrink

**Replication:** Read replicas for search queries. Primary for writes.

**Growth plan:**
- 1M users: single cluster, multiple shards
- 10M users: multiple clusters, geographic distribution
- 100M users: per-region clusters with data residency compliance

### Connector Scaling

Each connector type has different scaling characteristics:

| Connector | Challenge | Solution |
|-----------|-----------|----------|
| Gmail | High volume per user | Incremental sync via Gmail push notifications |
| Slack | Real-time messages | WebSocket-based sync, message batching |
| Google Drive | Large files | Content extraction worker pool, async processing |
| Jira | Complex permissions | Permission cache with TTL, lazy revalidation |

### Latency Optimization

- **Caching:** Recent search results (short TTL), popular documents (longer TTL), user session data
- **Geographic routing:** Route queries to nearest search cluster
- **Progressive loading:** Return instant suggestions → lexical results → semantic results → AI answer
- **Query prediction:** Pre-fetch results for likely queries based on session context

---

## 8. Failure Modes and Mitigations

| Failure | Impact | Mitigation |
|---------|--------|------------|
| Connector API down | New content not indexed | Queue sync jobs, retry with backoff, show stale results |
| Search index unavailable | No search results | Read replicas, failover to secondary cluster |
| LLM service down | No AI answers | Graceful degradation: show search results without AI |
| Permission sync lag | Potentially show unauthorized content | Conservative: deny access if permission state is uncertain |
| Embedding service down | No semantic search | Fallback to lexical-only results |

---

## 9. Interview Template

**Minutes 0-3: Clarify**
- "How many connected apps per user on average?"
- "What's the latency requirement for search vs. AI answers?"
- "Do we need to support collaborative search (shared results)?"
- "What's the freshness requirement for newly created content?"

**Minutes 3-8: High-level design**
- Draw the architecture (connectors → indexing pipeline → dual index → query service → AI answer)
- Explain each layer in one sentence

**Minutes 8-25: Deep dive (pick 2)**
- **Connector architecture** — OAuth, sync strategies, normalization
- **Indexing pipeline** — dual index, embedding, permission-aware partitioning
- **Query processing** — hybrid retrieval, reranking, permission filtering
- **RAG pipeline** — chunk selection, prompt construction, citation verification

**Minutes 25-35: Scaling**
- How index scales (sharding by user, replication, geographic distribution)
- How connectors scale (per-connector rate limiting, async processing)
- Latency optimizations (caching, progressive loading, parallel fan-out)

**Minutes 35-40: Operational concerns**
- Monitoring: search quality metrics (NDCG, click-through), latency percentiles, connector health
- Failure modes and graceful degradation
- Data privacy and permission accuracy

---

## 10. Quick-Fire Answers

**"Why hybrid search over pure vector search?"** — Lexical catches exact matches (names, IDs, error codes) that vector search misses. Vector catches semantic similarity that lexical misses. Combined gives best precision/recall.

**"How do you handle permissions at scale?"** — Index partitioned by user. Pre-retrieval filtering is primary. Post-retrieval permission check is safety net. Conservative on uncertain permissions.

**"How do you measure search quality?"** — Offline: NDCG, MRR on labeled datasets. Online: click-through rate, session success rate, reformulation rate, AI answer thumbs up/down.

**"How do you keep the index fresh?"** — Webhooks for real-time, polling for catch-up, full resync weekly. Target: new content searchable in < 5 minutes.

**"What's the hardest part?"** — Connector diversity. 60+ source apps, each with different APIs, schemas, auth, rate limits, and permission models. Building a unified search experience across all of them.
