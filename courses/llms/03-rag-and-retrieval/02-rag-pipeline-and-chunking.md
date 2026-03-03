# 02 — RAG Pipeline and Chunking

## RAG Architecture Overview

RAG (Retrieval-Augmented Generation) consists of two pipelines: an offline **ingestion pipeline** and a real-time **query pipeline**. The ingestion pipeline runs once when documents are added or updated; the query pipeline runs for every user request.

### End-to-End Flow

```
INGESTION PIPELINE (offline)
──────────────────────────────────────────────────────────────────
Source Documents
    │
    ▼
Parse (PDF → text, HTML → markdown, code → structured)
    │
    ▼
Chunk (split into retrieval-sized pieces with overlap)
    │
    ▼
Embed (embedding model → dense vectors)
    │
    ▼
Store (vector database + metadata: source, title, timestamp, etc.)


QUERY PIPELINE (real-time)
──────────────────────────────────────────────────────────────────
User Query
    │
    ▼
[Optional] Query Transformation (rewrite for clarity, expand multi-query)
    │
    ▼
Embed Query (same embedding model as ingestion)
    │
    ▼
Vector Search (top-K candidates, cosine similarity)
    │ + [Optional] BM25 keyword search (hybrid)
    │
    ▼
[Optional] Rerank (cross-encoder for precision)
    │
    ▼
[Optional] Metadata Filter (filter by date, source, category, etc.)
    │
    ▼
Prompt Assembly (system prompt + retrieved context + user query)
    │
    ▼
Generate (LLM produces grounded response)
    │
    ▼
[Optional] Grounding Check (verify answer against context)
    │
    ▼
Response to User
```

### Critical Design Decisions

| Decision | Options | Guidance |
|---|---|---|
| Chunk size | 256 – 2,048 tokens | Start at 500–1,000; tune based on retrieval eval |
| Overlap | 0–20% of chunk size | 10% is a good default |
| Number of retrieved chunks (K) | 3 – 20 | Start with 5; balance quality vs. context cost |
| Hybrid search | Vector-only vs. vector + BM25 | Always try hybrid; it almost always helps |
| Reranking | None vs. cross-encoder | Add when precision matters; costs 50–200ms |
| Query transformation | None vs. rewrite vs. multi-query | Critical for multi-turn conversations |

---

## Chunking Strategies

Chunking is one of the highest-impact decisions in a RAG system. Too small: chunks lack context and the model cannot construct a complete answer. Too large: chunks are noisy, the embedding represents the average of the whole chunk and specific details get diluted.

### 1. Fixed-Size Chunking

Split at a fixed token count regardless of content structure.

```python
from langchain.text_splitter import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=500,        # tokens per chunk
    chunk_overlap=50,      # overlap with previous chunk
    encoding_name="cl100k_base"  # tiktoken encoding
)
chunks = splitter.split_text(document)
```

**Strengths:** Simple, predictable chunk sizes, easy to implement
**Weaknesses:** Splits mid-sentence, mid-paragraph, mid-code-block — loses semantic coherence
**Best for:** Simple datasets, when other strategies fail, initial prototyping

### 2. Recursive Character Text Splitting

Splits on a hierarchy of separators — paragraphs, then sentences, then words, then characters — so it respects document structure wherever possible.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,           # target size in characters
    chunk_overlap=50,
    separators=[
        "\n\n",    # paragraphs first
        "\n",      # then lines
        ". ",      # then sentences
        ", ",      # then clauses
        " ",       # then words
        ""         # finally: characters
    ]
)
```

**Strengths:** Respects natural text boundaries, good default behavior, simple
**Best for:** Most use cases — this should be the starting point

### 3. Semantic Chunking

Uses embedding similarity to find natural topic boundaries. Splits when the semantic similarity between adjacent sentences drops below a threshold.

```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings

splitter = SemanticChunker(
    embeddings=OpenAIEmbeddings(),
    breakpoint_threshold_type="percentile",  # or "standard_deviation", "interquartile"
    breakpoint_threshold_amount=95           # percentile threshold
)
chunks = splitter.split_text(document)
```

**Strengths:** Best chunk coherence, chunks correspond to actual topics
**Weaknesses:** Expensive (embed every sentence), variable chunk sizes, more complex
**Best for:** High-quality knowledge bases, scientific/technical documents, when retrieval quality is paramount

### 4. Document-Aware (Structural) Chunking

Respects document structure: headings, sections, code blocks, tables, bullet lists.

```python
# Markdown document example
def split_markdown_by_headers(text: str, max_chunk_size: int = 1000) -> list[dict]:
    """Split on H1/H2 headers, preserving section context."""
    chunks = []
    current_section = ""
    current_header = ""

    for line in text.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            if current_section:
                chunks.append({
                    "text": current_section.strip(),
                    "header": current_header,
                    "char_count": len(current_section)
                })
            current_header = line.strip("# ")
            current_section = line + "\n"
        else:
            current_section += line + "\n"
            # Split large sections to avoid oversized chunks
            if len(current_section) > max_chunk_size * 4:
                chunks.append({
                    "text": current_section.strip(),
                    "header": current_header,
                    "char_count": len(current_section)
                })
                current_section = ""

    if current_section:
        chunks.append({"text": current_section.strip(), "header": current_header})

    return chunks
```

**Best for:** Technical documentation, API docs, legal documents, structured knowledge bases

### Chunking Decision Matrix

| Document Type | Recommended Strategy | Chunk Size |
|---|---|---|
| General prose / articles | Recursive character | 500–1,000 tokens |
| Technical documentation | Document-aware (by header) | Section-sized |
| Code + docs | Document-aware (by file/function) | Function-level |
| Legal/contracts | Semantic chunking | 300–600 tokens |
| FAQ / Q&A pairs | One Q&A per chunk | Natural unit |
| Conversational transcripts | Sliding window | 300–500 tokens |

### Chunk Size Tradeoffs

| Chunk Size | Retrieval | Generation | Use Case |
|---|---|---|---|
| Small (100–300 tokens) | Precise, but misses context | Often incomplete | Keyword-heavy exact lookup |
| Medium (400–800 tokens) | Good balance | Sufficient context | Most general use cases |
| Large (1,000–2,000 tokens) | Noisy, covers more ground | Rich context | Long-form analysis |

**Key insight:** The embedding represents the semantic meaning of the entire chunk. A large chunk's embedding is the "average" of all the topics it covers — specific details get diluted. Smaller chunks have more precise embeddings but less context for generation.

---

## Advanced Chunking Patterns

### Parent-Child Chunking

Embed small chunks for precise retrieval; return the surrounding parent section for richer generation context.

```
Parent chunk: Full section (1,500 tokens)
   ├── Child chunk 1 (250 tokens)
   ├── Child chunk 2 (250 tokens)  ← retrieved by embedding search
   ├── Child chunk 3 (250 tokens)
   └── Child chunk 4 (250 tokens)

Query: embed the query → find matching child chunk
Return to LLM: the parent chunk (full context)
```

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Small chunks for embedding search
child_splitter = RecursiveCharacterTextSplitter(chunk_size=200)

# Large chunks for context retrieval
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=store,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)
```

**When to use:** Long documents where specific passages answer questions, but those passages need surrounding context to be coherent.

### Contextual Chunk Headers

Prepend document/section context to each chunk before embedding, so each chunk is self-contained:

```python
def add_context_to_chunks(document: Document, chunks: list[str]) -> list[str]:
    contextual_chunks = []
    for chunk in chunks:
        # Add document context to each chunk
        contextual_text = f"""Document: {document.title}
Section: {document.current_section}
---
{chunk}"""
        contextual_chunks.append(contextual_text)
    return contextual_chunks
```

**Why this works:** A chunk about "the configuration file" without context is ambiguous. With the header "Document: Installation Guide / Section: Advanced Configuration", the embedding captures the full context.

### Late Chunking

A recent technique that embeds the full document first, then pools token embeddings within each chunk window. Unlike standard chunking (embed chunks independently), late chunking gives each chunk access to the full document's context:

```
Standard:   Embed each chunk independently → context-blind embeddings
Late chunk: Embed full document → slice token embeddings by chunk boundaries
            → each chunk embedding has full document context baked in
```

Requires an embedding model that outputs per-token embeddings (rather than just a pooled sentence vector). Models like jina-embeddings-v2 support this. Significantly better recall on complex multi-hop questions.

### Proposition-Based Chunking

Convert document passages into atomic factual propositions:

```
Original: "Apple was founded in 1976 by Steve Jobs, Steve Wozniak, and
Ronald Wayne in Cupertino, California. The company went public in 1980."

Propositions:
1. Apple was founded in 1976.
2. Apple was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne.
3. Apple was founded in Cupertino, California.
4. Apple went public in 1980.
```

Each proposition is an independently embeddable, self-contained fact. Best for knowledge-intensive QA where users ask single-fact questions. Expensive to generate (requires an LLM pass over every document).

---

## RAG Pipeline Prompt Assembly

The prompt assembly step determines how retrieved context is presented to the LLM:

```python
def assemble_rag_prompt(
    query: str,
    chunks: list[dict],
    conversation_history: list[dict] = None
) -> list[dict]:
    """Build a RAG prompt with grounding instructions."""

    # Format retrieved chunks with source attribution
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['title']}]\n{chunk['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """You are a helpful assistant that answers questions based
on provided context documents.

Rules:
- Answer ONLY using information from the provided context
- If the answer is not in the context, say: "I don't have enough information
  to answer that from the provided documents."
- When citing information, reference the source by its number: [Source 1]
- Do not use your general training knowledge for factual claims
- If sources contradict each other, note the contradiction"""

    # Build messages
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (last 5 turns)
    if conversation_history:
        messages.extend(conversation_history[-10:])

    # Add current query with context
    user_message = f"""Context documents:

{context}

---

Question: {query}"""

    messages.append({"role": "user", "content": user_message})
    return messages
```

---

## Hybrid Search

Pure vector search has blind spots: it understands meaning but can miss exact terminology, product codes, error messages, proper nouns, and rare technical terms. Keyword search (BM25) excels at exact matching but misses synonyms and paraphrases. Hybrid search combines both.

### Why Pure Vector Search Misses Things

```
Query: "Error code E-1042 in widget configuration"

Vector search: finds documents about "widget configuration errors" and
               "widget setup issues" — semantically related but may not
               contain the specific error code

BM25 search: finds all documents mentioning "E-1042" exactly

Hybrid: finds documents that are semantically about widget configuration
        AND mention E-1042 specifically
```

### Hybrid Search Architecture

```python
async def hybrid_search(
    query: str,
    vector_store: VectorStore,
    bm25_index: BM25Okapi,
    top_k: int = 20,
    rrf_k: int = 60
) -> list[dict]:
    """Combine vector and BM25 search using Reciprocal Rank Fusion."""

    # Run both searches in parallel
    vector_results, bm25_results = await asyncio.gather(
        vector_store.similarity_search(query, k=top_k),
        bm25_search(bm25_index, query, k=top_k)
    )

    # Apply Reciprocal Rank Fusion
    return reciprocal_rank_fusion(
        [vector_results, bm25_results],
        k=rrf_k
    )

def reciprocal_rank_fusion(
    result_sets: list[list[dict]],
    k: int = 60
) -> list[dict]:
    """Merge multiple ranked lists using RRF."""
    scores = {}

    for results in result_sets:
        for rank, doc in enumerate(results, start=1):
            doc_id = doc["id"]
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "score": 0.0}
            # RRF formula: 1 / (k + rank)
            scores[doc_id]["score"] += 1.0 / (k + rank)

    # Sort by combined RRF score
    ranked = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
    return [item["doc"] for item in ranked]
```

### RRF Formula

**Reciprocal Rank Fusion:** For each document, sum its reciprocal rank across all search methods:

```
RRF_score(doc) = Σ_i  1 / (k + rank_i(doc))

Where:
  rank_i(doc) = rank of doc in search method i
  k = 60 (default, prevents large scores for top-ranked results)
```

**Example:**
```
Document A: rank 1 in vector search, rank 3 in BM25
  RRF = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323

Document B: rank 2 in vector search, not in BM25 top-20
  RRF = 1/(60+2) + 0 = 0.0161

Document A wins because it ranks well in both methods.
```

### Alternative Fusion Methods

| Method | Formula | Notes |
|---|---|---|
| RRF | 1/(k + rank) | Simple, robust, no tuning |
| Linear combination | α × vector_score + (1-α) × bm25_score | Requires normalizing scores, needs tuning |
| Cascade | Vector search → filter by BM25 | Easy to implement but loses recall |
| Learned fusion | Trained weighted combination | Highest quality, needs training data |

---

## Reranking

The initial vector search returns the top-K by approximate embedding similarity. Reranking applies a more expensive but more accurate model to re-score and reorder these candidates.

### Bi-Encoders vs. Cross-Encoders

**Bi-encoder (initial retrieval):**
```
query → encoder → query vector
document → encoder → document vector
similarity = dot_product(query_vector, document_vector)
```
- Encode documents in advance (offline)
- Encode query at query time
- Fast: O(dim) similarity lookup

**Cross-encoder (reranking):**
```
[query + document] → encoder → relevance_score
```
- Takes query and document as a PAIR
- Attends to both simultaneously (much richer interaction)
- No precomputed embeddings — must process every candidate pair
- 10–100× slower than bi-encoder
- Significantly better relevance judgments

### Two-Stage Retrieval Pipeline

```
Stage 1 (fast, high recall):
  Bi-encoder vector search
  Return top-20 candidates
  Latency: 10–50ms

Stage 2 (precise, lower recall):
  Cross-encoder rerank top-20
  Return top-5 to LLM
  Latency: 50–200ms

Total retrieval latency: 60–250ms
```

### Reranker Models

| Model | Quality | Latency (20 passages) | Type |
|---|---|---|---|
| Cohere Rerank v3 | State of the art | 50–100ms (API) | API |
| bge-reranker-large | Excellent | 100–200ms (GPU) | Open-source |
| bge-reranker-base | Good | 50–100ms (GPU) | Open-source |
| cross-encoder/ms-marco-MiniLM-L-12-v2 | Good | 80–150ms (GPU) | Open-source |
| Jina Reranker | Very good | 50–100ms (API) | API |

**Cohere Rerank v3** is the strongest for production (if latency budget allows) — multilingual, trained on diverse retrieval tasks.

For self-hosted, **bge-reranker-large** offers excellent quality with full control.

---

## Metadata Filtering

Metadata filtering restricts the search space using structured attributes before or alongside vector search.

### Common Metadata Fields

```python
# Metadata stored alongside each vector chunk
{
    "chunk_id": "doc_123_chunk_4",
    "source_doc_id": "doc_123",
    "doc_title": "Q3 Financial Report",
    "category": "financial",
    "author": "Jane Smith",
    "created_at": "2024-09-15",
    "department": "finance",
    "access_level": "internal",
    "doc_version": "2.1",
    "language": "en"
}
```

### Filter Strategies

**Pre-filter (filter before vector search):**
```python
# Pinecone
results = index.query(
    vector=query_embedding,
    top_k=10,
    filter={
        "category": {"$eq": "financial"},
        "created_at": {"$gte": "2024-01-01"},
        "access_level": {"$in": ["public", "internal"]}
    }
)
```

**Post-filter (filter after vector search):**
```python
# Search broadly, then filter results
results = vector_search(query, top_k=100)
filtered = [r for r in results if r["metadata"]["category"] == "financial"][:10]
```

**Integrated (hybrid pre+vector):**
Most production vector databases support pre-filtering that indexes metadata alongside vectors, combining filter and search in one efficient step.

### Pre-filter vs Post-filter Comparison

| | Pre-filter | Post-filter |
|---|---|---|
| Speed | Faster (smaller search space) | Slower (search all then filter) |
| Recall | Lower (may miss edge cases) | Higher (full search space) |
| Consistency | Predictable result count | Variable result count |
| Best for | Well-defined filter conditions | Exploratory, fuzzy filtering |

---

## RAG vs Fine-Tuning vs Long Context

| Dimension | RAG | Fine-Tuning | Long Context |
|---|---|---|---|
| **Best for** | Updatable knowledge | Behavior/style changes | Small, static datasets |
| **Data freshness** | Real-time updates | Stale after training | Current at query time |
| **Setup effort** | Medium (pipeline) | High (data prep + training) | Low (just stuff it in) |
| **Per-query cost** | Medium (retrieval + generation) | Low (inference only) | High (long prompts) |
| **Upfront cost** | Medium (embedding + indexing) | High (training run) | None |
| **Accuracy for facts** | High (grounded in sources) | Unreliable | High (if in context) |
| **Scalability** | Scales to millions of docs | Fixed at training time | Limited by context window |
| **Traceability** | High (can cite sources) | Low (knowledge baked in) | High (in context) |

**Decision rule:**
- Dynamic knowledge that updates → RAG
- Behavioral/style adaptation → Fine-tuning
- Small static corpus, simplicity preferred → Long context
- Fine-tuning for knowledge injection is an anti-pattern — use RAG instead

---

## Interview Q&A: RAG Pipeline and Chunking

**Q: Walk me through a RAG pipeline architecture.**

Two pipelines: offline ingestion and real-time query. Ingestion: parse source documents into text, chunk into retrieval-sized pieces (typically 500–1,000 tokens with 10% overlap), embed each chunk with an embedding model, store vectors plus metadata in a vector database. Query: embed the user's query (same embedding model), run vector similarity search to get top-K candidates, optionally run hybrid search combining vector and BM25, optionally rerank with a cross-encoder for better precision, assemble a prompt with the retrieved context and user question, generate a grounded response. Critical design decisions at every step: chunk size, K candidates, hybrid vs vector-only, whether reranking justifies the latency cost.

**Q: How do you choose a chunking strategy?**

Start with recursive splitting at 500–1,000 tokens with 10% overlap — this respects natural text boundaries and is a reliable default. From there, tune based on retrieval eval metrics. For structured documents (API docs, legal contracts), document-aware splitting on headers/sections is much better. For knowledge bases where queries ask about specific facts, consider parent-child chunking: embed small chunks for precise retrieval, return the surrounding parent section for rich generation context. Add contextual chunk headers (prepend document title and section) to make each chunk self-contained so its embedding captures full context. Always tune based on measured retrieval quality, not intuition.

**Q: What is hybrid search and why use it?**

Hybrid search combines vector (semantic) search with keyword (BM25) search. Vector search excels at semantic similarity — "automobile" matches "car" — but can miss exact terms: product codes, error messages, proper nouns. BM25 excels at exact matches but misses semantic relationships. Combining them with Reciprocal Rank Fusion gives better recall than either alone. RRF scores each document as the sum of 1/(k + rank) across all search methods, where k=60 prevents top-ranked documents from dominating. Many vector databases (Weaviate, Qdrant, OpenSearch) support hybrid search natively. If you're building a RAG system and not using hybrid search, you are likely missing retrievals that hurt generation quality.

**Q: When would you use RAG vs fine-tuning vs long context?**

RAG when you need to ground the model in specific, updatable knowledge — company docs, knowledge bases, anything that changes. Fine-tuning when you need to change the model's behavior, style, or capabilities — not for knowledge injection. Long context when the dataset is small enough to fit and you need the simplest possible solution. The anti-pattern: fine-tuning for knowledge — it's unreliable (the model may not recall specific facts consistently), expensive, and the data goes stale. These combine well: fine-tune for domain reasoning patterns and RAG for current facts. For simple cases with static data under ~200K tokens, just stuffing everything in context is often competitive with RAG in quality and beats it on simplicity.
