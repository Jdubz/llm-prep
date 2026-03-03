# 01 — Embeddings and Vector Databases

## What Are Embeddings?

Embeddings are dense vector representations of text in a high-dimensional space where **semantic similarity maps to geometric proximity**. An embedding model takes arbitrary text and produces a fixed-size vector — typically 256 to 3,072 floating-point numbers — that encodes the meaning of that text.

"Dog" and "puppy" produce nearby vectors. "Dog" and "spreadsheet" produce distant vectors. "The bank of the river" and "the financial bank" produce different vectors because embedding models understand context.

This enables semantic search: instead of matching keywords, you embed both the query and the corpus, then find the nearest vectors. "How do I fix a broken pipe?" will match documents about plumbing even if those documents never use the word "fix."

### Embedding Models vs. Generation Models

| Dimension | Embedding Model | Generation Model |
|---|---|---|
| Input | Text | Text (+ tools, images) |
| Output | Fixed-size vector | Variable-length text |
| Purpose | Similarity and retrieval | Generation and reasoning |
| Cost | 10–100× cheaper | Expensive per token |
| Speed | ~10–50ms per call | 100ms–10s+ |
| Examples | text-embedding-3-small | GPT-4o, Claude Opus |

### How Embedding Models Encode Meaning

Most embedding models are based on encoder-only transformers (BERT architecture). Unlike GPT-style decoders, they process the full input bidirectionally — each token attends to all other tokens. The final representation (either the [CLS] token or the mean of all token representations) is the embedding.

Modern embedding models are trained with contrastive learning:
- **Positive pairs:** semantically similar sentences are pulled together in embedding space
- **Negative pairs:** semantically different sentences are pushed apart
- Training on millions of (similar, dissimilar) pairs teaches the model to encode meaning rather than form

---

## Embedding Model Comparison

| Model | Dimensions | MTEB Score | Cost ($/1M tokens) | Notes |
|---|---|---|---|---|
| text-embedding-3-small | 1,536 | 62.3 | $0.02 | Best cost/quality ratio for most use cases |
| text-embedding-3-large | 3,072 | 64.6 | $0.13 | Higher quality; use for precision-critical apps |
| Cohere embed-v3-english | 1,024 | 64.5 | $0.10 | Strong performance, separate query/doc models |
| voyage-3 | 1,024 | ~66+ | $0.06 | State of the art MTEB, purpose-built for retrieval |
| bge-large-en-v1.5 | 1,024 | 63.8 | Free (self-hosted) | Strong open-source option |
| gte-Qwen2-7B-instruct | 3,584 | ~67+ | Free (self-hosted) | Large but high quality |
| nomic-embed-text-v1.5 | 768 | 62.4 | Free (self-hosted) | Open, good for edge deployment |

**MTEB (Massive Text Embedding Benchmark):** The standard evaluation for embedding models, covering retrieval, clustering, classification, and similarity tasks. Higher is better. Scores above 60 indicate production-ready quality.

### Matryoshka Embeddings

Some models (text-embedding-3-small/large, nomic-embed) support **Matryoshka representation learning** — the first n dimensions of the vector are themselves meaningful representations at lower dimensionality.

Practical benefit: you can truncate embeddings to reduce storage and search costs without retraining, at a small quality cost:
```python
# text-embedding-3-small: full 1536 dims (best quality)
# Truncated to 512 dims: ~15% quality loss, 3× smaller storage
# Truncated to 256 dims: ~25% quality loss, 6× smaller storage
```

### Query vs. Document Embeddings

Some models have separate encoders optimized for queries vs. documents:
- **Cohere:** `embed-v3-english` with `input_type="search_query"` or `input_type="search_document"`
- **E5 models:** Prefix queries with `"query: "` and documents with `"passage: "`

Using the wrong mode (embedding queries with the document encoder) gives significantly worse retrieval performance.

---

## Similarity Metrics

### Cosine Similarity

The standard metric for embedding comparison:

```
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)
```

Range: −1 to 1. For most embedding models, similar texts score 0.8–1.0; unrelated texts score 0.0–0.3.

**When normalized vectors are used** (standard practice), cosine similarity equals the dot product:
```python
import numpy as np

# If embeddings are normalized (unit vectors)
similarity = np.dot(A, B)  # Same as cosine_similarity

# If not normalized
similarity = np.dot(A, B) / (np.linalg.norm(A) * np.linalg.norm(B))
```

### Dot Product

Faster than cosine (skips normalization), preferred when:
- Embeddings are guaranteed to be normalized
- You want to prioritize magnitude (confidence) in addition to direction
- The vector database is optimized for inner product search

### Euclidean Distance (L2)

```
L2(A, B) = sqrt(sum((A - B)^2))
```

Lower = more similar. Less common than cosine for NLP tasks because it conflates magnitude with direction. Used in some computer vision applications.

### Practical Guidance

```
Default choice:  Cosine similarity (normalized embeddings = equivalent to dot product)
High throughput: Dot product (skip normalization check)
Image search:    L2 (domain convention)
```

---

## Vector Databases

A vector database is specialized infrastructure for storing, indexing, and querying high-dimensional vectors at scale. Standard databases (Postgres, MySQL) can store vectors but cannot efficiently find the nearest neighbors in a 1,536-dimensional space across millions of vectors.

### Comparison Table

| Database | Type | Hybrid Search | Scale | Best For |
|---|---|---|---|---|
| **Pinecone** | Managed | Yes (sparse+dense) | Up to billions | Zero-ops, high scale |
| **Weaviate** | Both | Built-in BM25+vector | Millions–billions | Hybrid search |
| **Qdrant** | Both | Yes | Millions–billions | Performance-critical |
| **Milvus** | Both (Zilliz managed) | Yes | Billions | Enterprise scale |
| **pgvector** | Postgres extension | Via full-text search | Millions | Existing Postgres stack |
| **ChromaDB** | Self-hosted | No | 100K–1M | Prototyping |
| **FAISS** | Library (Meta) | No | Research scale | Custom integration |

### Architecture Differences

**Managed (Pinecone, Weaviate Cloud, Zilliz):**
- No infrastructure to manage
- Pay per query and storage
- Auto-scaling, high availability
- Limited customization
- Good choice when: you are moving fast, scaling is unpredictable, ops cost is real

**Self-hosted (Qdrant, Milvus, Weaviate):**
- Full control over deployment
- Fixed infrastructure cost
- You manage scaling and reliability
- More customization options
- Good choice when: data privacy requirements, predictable load, large-scale economics

**pgvector (Postgres extension):**
- Vectors stored alongside existing relational data
- ACID transactions for ingestion
- SQL joins for metadata filtering
- Leverages existing Postgres ops expertise
- Performance ceiling: ~1M vectors with reasonable query latency
- Good choice when: team already runs Postgres, dataset fits in millions of vectors, need relational data alongside vectors

**In-process libraries (FAISS, ChromaDB):**
- No server, runs in the same process as your application
- Near-zero latency (no network)
- No high-availability, not suitable for production at scale
- Good choice when: prototyping, research, single-user applications

### Extended Feature Comparison

| Database | ANN Algorithm | Max Dims | Metadata Filtering | Managed Pricing Model |
|---|---|---|---|---|
| Pinecone | Proprietary | 20,000 | Pre-filter | Per vector + per query |
| Weaviate | HNSW | Unlimited | Pre-filter | Pod-based or serverless |
| Qdrant | HNSW | Unlimited | Pre+post | Cloud storage-based |
| pgvector | HNSW, IVF | Unlimited | Standard SQL | Postgres pricing |
| ChromaDB | HNSW | Unlimited | Post-filter | Free (self-hosted) |

---

## Approximate Nearest Neighbor (ANN) Algorithms

Exact nearest neighbor search in high-dimensional space requires computing the distance from the query to every vector — O(n) per query. For millions of vectors, this is too slow. ANN algorithms trade a small amount of accuracy for massive speed improvements.

### HNSW (Hierarchical Navigable Small Worlds)

The dominant ANN algorithm for most vector databases. Builds a multi-layer graph where upper layers have long-range connections (for fast global navigation) and lower layers have short-range connections (for precise local search).

```
Query search process:
Layer 2 (sparse):  Start here, navigate to rough neighborhood
Layer 1 (medium):  Narrow down to local area
Layer 0 (dense):   Fine-grained search for nearest neighbors
```

**Key parameters:**
- `ef_construction`: Higher = more accurate index but slower to build (200–400)
- `M`: Number of connections per node (16–64). Higher = better quality, more memory
- `ef_search`: Beam size during query. Higher = more accurate, slower (50–200)

**Practical guidance:**
- Default M=16, ef_construction=200 is a good starting point
- Increase ef_search at query time for better recall without rebuilding the index
- HNSW is memory-resident — the entire graph must fit in RAM

**Strengths:** Excellent recall at high speeds, well-studied, used in Faiss, Qdrant, Weaviate
**Weaknesses:** Memory-intensive (~50–100 bytes per vector × M), slow to add many vectors at once

### IVF (Inverted File Index)

Divides the vector space into k clusters (Voronoi cells) using k-means clustering. At query time, only searches the nearest n_probe clusters.

```
Index build: k-means cluster all vectors → assign each vector to its cluster
Query:       Embed query → find nearest n_probe cluster centers → search within those clusters
```

**Key parameters:**
- `n_list`: Number of clusters. Typically sqrt(N) where N is dataset size (1,000 for 1M vectors)
- `n_probe`: Clusters to search at query time. Higher = better recall, slower (10–100)

**Strengths:** Low memory footprint, scales well to very large datasets
**Weaknesses:** Requires training (building the index from data), poor performance for small datasets, lower recall than HNSW at the same speed

### Product Quantization (PQ)

Compresses vectors by splitting them into subvectors and quantizing each independently. Used to dramatically reduce memory at the cost of some accuracy:

```
Original:  1536-dim float32 = 6,144 bytes per vector
PQ-64:     1536 split into 64 subvectors, each quantized to 1 byte = 64 bytes per vector (96× compression)
```

PQ is commonly used in conjunction with IVF (IVF-PQ) for very large-scale search where even HNSW's memory requirements are prohibitive.

### DiskANN

Stores the HNSW-like graph on disk rather than RAM. Enables billion-scale search without terabytes of RAM. Used by Bing and Azure Cognitive Search.

### Algorithm Selection Guide

| Dataset Size | Budget | Recommendation |
|---|---|---|
| < 100K vectors | Any | Any algorithm; HNSW is fine |
| 100K–10M vectors | RAM available | HNSW |
| 10M–1B vectors | RAM constrained | IVF-PQ or DiskANN |
| > 1B vectors | Large infrastructure | DiskANN + distributed |

---

## Key Numbers for Vector Databases

| Metric | Value |
|---|---|
| Vector storage (1536-dim, float32) | 6 KB per vector |
| 1M vectors storage (dense) | ~6 GB |
| HNSW memory overhead (~M=16) | ~100 bytes per vector overhead |
| Typical ANN recall@10 | 95–99% (HNSW with good params) |
| Query latency (Pinecone, 1M vectors) | 10–50ms |
| Query latency (pgvector, 100K vectors) | 5–20ms |
| Embedding API latency (single text) | 10–50ms |
| Embedding API latency (batch of 100) | 100–500ms |
| Maximum recommended pgvector size | ~1M vectors before considering migration |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Basic RAG Pipeline** [1] -- Uses embeddings and cosine similarity to build the core retrieve step. You will embed documents, compute similarity scores, and return ranked results. Applies concepts from "Similarity Metrics" and "Cosine Similarity" above.
- **Exercise 3: Hybrid Search with RRF** [2] -- Combines vector similarity ranking with keyword ranking. Applies the cosine similarity metric from this file alongside BM25-style keyword scoring.
- **Exercise 5: Multi-Tenant Metadata Schema** [3] -- Designs metadata for a vector database. Directly applies concepts from "Vector Databases" and "Extended Feature Comparison" (which DBs support which filtering modes).

See also `examples.py`:
- `InMemoryVectorStore` (Pattern 1) -- demonstrates embedding, storing, and searching with metadata filtering
- `cosine_similarity()`, `dot_product()`, `euclidean_distance()` -- all three similarity metrics implemented

---

## Interview Q&A: Embeddings and Vector Databases

**Q: What are embeddings and how do they enable semantic search?**

Embeddings are dense vector representations of text in a high-dimensional space where semantic similarity maps to geometric proximity. An embedding model takes text and produces a fixed-size vector — "dog" and "puppy" produce nearby vectors; "dog" and "spreadsheet" produce distant vectors. Semantic search embeds both the query and the corpus at ingestion time, then finds the nearest vectors at query time. "How do I fix a broken pipe?" matches plumbing documents even if they never use the word "fix." This is fundamental to RAG: embed chunks at ingestion, embed the query at search time, retrieve the most similar chunks. Embedding models are much cheaper and faster than LLMs — they are specialized for vector production, not generation.

**Q: How do you choose a vector database for a RAG system?**

The decision comes down to scale, infrastructure preferences, and feature requirements. For teams already running Postgres with datasets under 1M vectors, pgvector is the zero-new-infrastructure choice — ACID transactions, SQL joins for metadata, and good enough performance. For medium-scale systems (1M–100M vectors) where you want full control and high performance, Qdrant or Weaviate self-hosted. For teams that want zero ops and are willing to pay for it, Pinecone. For hybrid search requirements (vector + keyword), Weaviate has the best native support. The key anti-pattern is over-engineering the vector DB choice early — start with pgvector or ChromaDB for prototyping, and migrate only when you hit real scale constraints.

**Q: What is HNSW and why is it the dominant ANN algorithm?**

HNSW (Hierarchical Navigable Small Worlds) builds a multi-layer graph where upper layers enable fast global navigation and lower layers enable precise local search. At query time, you navigate from the top layer's long-range connections down to the bottom layer's precise neighborhood, finding approximate nearest neighbors without scanning all vectors. HNSW achieves >95% recall at high query speeds with reasonable memory overhead. It dominates because it combines excellent recall, fast queries, and incremental insertion (you can add vectors without rebuilding). Its main weakness is memory — the full graph must fit in RAM — which makes IVF-PQ or DiskANN necessary at billion-scale or memory-constrained deployments.

**Q: What is the difference between cosine similarity and dot product for embeddings?**

Cosine similarity measures the angle between two vectors (ignoring magnitude), giving a score from −1 to +1. Dot product multiplies corresponding elements and sums them, giving an unbounded scalar. For normalized unit vectors (which most embedding models produce), they are mathematically identical. The practical difference: dot product is slightly faster (no normalization step), and some vector databases are optimized for inner product search. Cosine similarity is the semantic convention because it's independent of magnitude — two texts with the same meaning but different verbosity still score similarly. Always normalize embeddings and use cosine/dot product interchangeably.
