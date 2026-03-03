"""
Module 03: RAG & Retrieval -- Exercises

Skeleton functions with TODOs. Implement each function following the docstrings.
Test your implementations by running this file: python exercises.py

Reference files in this directory:
  - 01-embeddings-and-vector-databases.md  (embeddings, similarity metrics, vector DBs)
  - 02-rag-pipeline-and-chunking.md        (RAG architecture, chunking, hybrid search, reranking)
  - 03-advanced-rag-patterns.md            (query transformation, multi-hop, evaluation)
  - examples.py                            (runnable reference implementations)

Difficulty ratings:
  [1] Foundational -- should be quick for senior engineers
  [2] Intermediate -- requires understanding of RAG tradeoffs
  [3] Advanced -- system design thinking required
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable


# ---------------------------------------------------------------------------
# Shared types (same as examples.py)
# ---------------------------------------------------------------------------

Vector = list[float]


@dataclass
class Document:
    id: str
    text: str
    vector: Vector = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    document: Document
    score: float


def cosine_similarity(a: Vector, b: Vector) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Mock embedding function -- deterministic, not semantically meaningful.
# Use for testing your implementations.
import hashlib

def mock_embed(text: str, dims: int = 64) -> Vector:
    h = hashlib.sha256(text.lower().encode()).hexdigest()
    raw = [int(h[i:i+2], 16) / 255.0 - 0.5 for i in range(0, min(len(h), dims * 2), 2)]
    raw = (raw * (dims // len(raw) + 1))[:dims]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw] if norm > 0 else raw


# ===========================================================================
# Exercise 1: Basic RAG Pipeline [1]
#
# READ FIRST:
#   02-rag-pipeline-and-chunking.md
#     -> "## RAG Architecture Overview" (end-to-end flow diagram)
#     -> "## RAG Pipeline Prompt Assembly" (prompt format with grounding)
#   01-embeddings-and-vector-databases.md
#     -> "## Similarity Metrics" -> "### Cosine Similarity"
#
# ALSO SEE:
#   examples.py
#     -> "Pattern 1: In-Memory Vector Store" (InMemoryVectorStore.add, .search)
#     -> "Pattern 7: Complete RAG Pipeline" (RAGPipeline.ingest, .retrieve, .build_prompt)
# ===========================================================================

class BasicRAGPipeline:
    """Implement a basic RAG pipeline with these stages:
    1. Ingest: embed and store documents
    2. Retrieve: find top-K similar documents for a query
    3. Build prompt: assemble retrieved context into an LLM prompt

    This is the most fundamental RAG pattern. Every component you add
    later (reranking, hybrid search, etc.) builds on this skeleton.
    """

    def __init__(self, embed_fn: Callable[[str], Vector] = mock_embed):
        self.embed_fn = embed_fn
        self.documents: list[Document] = []

    def ingest(self, texts: list[str], metadatas: list[dict] | None = None) -> int:
        """Embed and store documents.

        Args:
            texts: List of text strings to ingest
            metadatas: Optional list of metadata dicts (one per text)

        Returns:
            Number of documents ingested

        TODO:
        1. For each text, create a Document with:
           - id: "doc-{index}" where index is position in self.documents
           - text: the input text
           - vector: result of self.embed_fn(text)
           - metadata: corresponding metadata dict (or empty dict)
        2. Append each Document to self.documents
        3. Return the count of new documents added

        Step-by-step:
            metadatas = metadatas or [{}] * len(texts)
            for i, (text, meta) in enumerate(zip(texts, metadatas)):
                doc = Document(
                    id=f"doc-{len(self.documents)}",
                    text=text,
                    vector=self.embed_fn(text),   # call the embedding function
                    metadata=meta,
                )
                self.documents.append(doc)
            return len(texts)
        """
        raise NotImplementedError("Implement ingest()")

    def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Find the top-K most similar documents to the query.

        Args:
            query: The search query string
            top_k: Number of results to return

        Returns:
            List of SearchResult objects, sorted by score descending

        TODO:
        1. Embed the query using self.embed_fn
        2. Compute cosine similarity between query vector and every document vector
        3. Sort by similarity score (highest first)
        4. Return top_k results as SearchResult objects

        Step-by-step:
            query_vector = self.embed_fn(query)
            results = []
            for doc in self.documents:
                score = cosine_similarity(query_vector, doc.vector)
                results.append(SearchResult(document=doc, score=score))
            results.sort(key=lambda r: r.score, reverse=True)
            return results[:top_k]
        """
        raise NotImplementedError("Implement retrieve()")

    def build_prompt(self, query: str, results: list[SearchResult]) -> list[dict]:
        """Assemble a RAG prompt from query and retrieved context.

        Args:
            query: The user's question
            results: Retrieved search results

        Returns:
            List of message dicts with 'role' and 'content' keys,
            in the format: [system_message, user_message]

        TODO:
        1. Create a system message that instructs the LLM to:
           - Answer using ONLY the provided context
           - Say "I don't have enough information" if context is insufficient
        2. Create a user message containing:
           - The context chunks (numbered, separated by "---")
           - The user's question
        3. Return as [{"role": "system", "content": ...}, {"role": "user", "content": ...}]

        Step-by-step:
            # Build context string from results
            context_parts = []
            for i, result in enumerate(results, 1):
                source = result.document.metadata.get("source", "unknown")
                context_parts.append(f"[Source {i}: {source}]\n{result.document.text}")
            context = "\n---\n".join(context_parts)

            system_msg = {
                "role": "system",
                "content": "Answer the user's question using ONLY the provided context. "
                           "If the context doesn't contain enough information, say so."
            }
            user_msg = {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {query}"
            }
            return [system_msg, user_msg]
        """
        raise NotImplementedError("Implement build_prompt()")


# ===========================================================================
# Exercise 2: Document-Aware Chunking [2]
#
# READ FIRST:
#   02-rag-pipeline-and-chunking.md
#     -> "## Chunking Strategies" (all four strategies, especially #4 Structural)
#     -> "### Chunking Decision Matrix" (which strategy for which doc type)
#     -> "### Chunk Size Tradeoffs"
#   02-rag-pipeline-and-chunking.md
#     -> "## Advanced Chunking Patterns" -> "### Contextual Chunk Headers"
#
# ALSO SEE:
#   examples.py
#     -> "Pattern 2: Chunking Strategies" -> chunk_by_headers()
#        (splits markdown on headers, preserves section hierarchy as metadata)
#     -> chunk_recursive() (fallback splitting logic when sections are too large)
# ===========================================================================

def chunk_document_aware(
    text: str,
    max_chunk_size: int = 1000,
) -> list[dict]:
    """Chunk text while respecting document structure.

    Must handle:
    - Markdown headers (# through ######) as split boundaries
    - Code blocks (``` ... ```) kept intact (never split mid-block)
    - If a section exceeds max_chunk_size, split on paragraph boundaries (\n\n)

    Args:
        text: Markdown-formatted document text
        max_chunk_size: Maximum characters per chunk

    Returns:
        List of dicts, each with:
        - "text": the chunk content (string)
        - "metadata": dict with keys:
            - "heading": the most recent heading text (or "" if none)
            - "has_code": bool, whether chunk contains a code block

    TODO:
    1. Parse the text line by line
    2. When you encounter a markdown header (# to ######):
       - Save the current chunk (if non-empty)
       - Start a new chunk, record the heading in metadata
    3. When you encounter a code block start (```):
       - Accumulate lines until the closing ```
       - Keep the entire code block in one chunk
       - Set has_code=True in metadata
    4. If the current chunk exceeds max_chunk_size:
       - Try to split on paragraph boundaries (\n\n)
       - If no paragraph boundary, split at max_chunk_size
    5. Return all chunks with their metadata

    Example:
        text = '''# Intro
        Some text.

        ```python
        def foo():
            pass
        ```

        # Next Section
        More text.'''

        Result: [
            {"text": "# Intro\nSome text.\n\n```python\ndef foo():\n    pass\n```",
             "metadata": {"heading": "Intro", "has_code": True}},
            {"text": "# Next Section\nMore text.",
             "metadata": {"heading": "Next Section", "has_code": False}},
        ]

    Step-by-step approach:
        chunks = []
        current_text = ""
        current_heading = ""
        has_code = False
        in_code_block = False

        for line in text.split("\\n"):
            # Detect code fence: line.strip().startswith("```")
            #   If in_code_block is False -> entering code block, set in_code_block = True, has_code = True
            #   If in_code_block is True  -> closing code block, set in_code_block = False
            #   Always append the line to current_text and continue

            # Detect header (only when NOT inside a code block):
            #   header_match = re.match(r'^(#{1,6})\\s+(.+)', line)
            #   If match: flush current chunk, start new chunk with this heading

            # Append line to current_text
            # Check if len(current_text) > max_chunk_size and not in_code_block:
            #   Try splitting current_text on "\\n\\n" to flush a paragraph-sized piece

        # Don't forget to flush the final chunk
    """
    raise NotImplementedError("Implement chunk_document_aware()")


# ===========================================================================
# Exercise 3: Hybrid Search with RRF [2]
#
# READ FIRST:
#   02-rag-pipeline-and-chunking.md
#     -> "## Hybrid Search" (why pure vector search misses things)
#     -> "### Hybrid Search Architecture" (vector + BM25 + RRF code)
#     -> "### RRF Formula" (the formula and worked example)
#
# ALSO SEE:
#   examples.py
#     -> "Pattern 3: Hybrid Search (Vector + Keyword)"
#        - bm25_score()              (simplified keyword scoring)
#        - reciprocal_rank_fusion()  (merging ranked lists with RRF)
#        - HybridSearcher.search()   (full hybrid search pipeline)
# ===========================================================================

def hybrid_search_rrf(
    query: str,
    documents: list[Document],
    embed_fn: Callable[[str], Vector] = mock_embed,
    top_k: int = 5,
    rrf_k: int = 60,
) -> list[SearchResult]:
    """Implement hybrid search combining vector similarity and keyword matching.

    Steps:
    1. Vector search: embed query, rank documents by cosine similarity
    2. Keyword search: rank documents by term overlap (simplified BM25)
    3. Fuse with Reciprocal Rank Fusion
    4. Return top-K from fused results

    Args:
        query: Search query string
        documents: List of Document objects (already have vectors)
        embed_fn: Embedding function
        top_k: Number of results to return
        rrf_k: RRF constant (default 60)

    Returns:
        List of SearchResult objects sorted by fused score

    TODO:
    1. VECTOR RANKING:
       - Embed the query
       - Compute cosine similarity with each document
       - Create a ranked list of document IDs (highest sim first)

    2. KEYWORD RANKING:
       - Tokenize query into lowercase words
       - For each document, count how many query words appear in the doc text
       - Rank by count (highest first), break ties by document order

    3. RRF FUSION:
       - For each document that appears in either ranked list:
         RRF_score = 1/(rrf_k + vector_rank) + 1/(rrf_k + keyword_rank)
       - If a document only appears in one list, only add that term
       - Sort by RRF_score descending

    4. Return top_k results as SearchResult objects (score = RRF score)

    Step-by-step:
        # 1. Vector ranking
        query_vector = embed_fn(query)
        vec_scored = [(doc, cosine_similarity(query_vector, doc.vector)) for doc in documents]
        vec_scored.sort(key=lambda x: x[1], reverse=True)
        vec_ranked = [doc.id for doc, _ in vec_scored]  # ordered IDs

        # 2. Keyword ranking
        query_terms = query.lower().split()
        kw_scored = []
        for doc in documents:
            doc_lower = doc.text.lower()
            count = sum(1 for t in query_terms if t in doc_lower)
            kw_scored.append((doc, count))
        kw_scored.sort(key=lambda x: x[1], reverse=True)
        kw_ranked = [doc.id for doc, _ in kw_scored]

        # 3. RRF fusion -- iterate through both ranked lists
        rrf_scores = {}  # doc_id -> float
        for rank, doc_id in enumerate(vec_ranked, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)
        for rank, doc_id in enumerate(kw_ranked, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)

        # 4. Sort and return top_k as SearchResult objects
        doc_map = {doc.id: doc for doc in documents}
        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
        return [SearchResult(document=doc_map[did], score=rrf_scores[did]) for did in sorted_ids[:top_k]]
    """
    raise NotImplementedError("Implement hybrid_search_rrf()")


# ===========================================================================
# Exercise 4: Retrieval Evaluation [2]
#
# READ FIRST:
#   03-advanced-rag-patterns.md
#     -> "## RAGAS: RAG Evaluation Framework" -> "### Four Core Metrics"
#        (faithfulness, answer relevance, context precision, context recall)
#     -> "### Running RAGAS" (how the framework is used in code)
#   03-advanced-rag-patterns.md
#     -> "## RAG Failure Modes and Debugging" -> "### Debugging Checklist"
#
# ALSO SEE:
#   examples.py
#     -> "Pattern 6: RAG Evaluation"
#        - evaluate_retrieval()    (computes recall@K, precision@K, MRR, hit_rate)
#        - evaluate_faithfulness() (checks if answer is grounded in context)
# ===========================================================================

def evaluate_retrieval_quality(
    test_queries: list[dict],
    retrieve_fn: Callable[[str], list[str]],
) -> dict:
    """Evaluate retrieval quality across a test set.

    Each test query has:
    - "query": the query string
    - "relevant_doc_ids": set of ground-truth relevant document IDs
    - "k": the K value for evaluation

    Args:
        test_queries: List of test query dicts with keys:
            - "query" (str)
            - "relevant_doc_ids" (set[str])
            - "k" (int)
        retrieve_fn: Function that takes a query string and returns
                     a list of document IDs (ordered by relevance)

    Returns:
        Dict with aggregated metrics:
        - "mean_recall_at_k": Average recall@K across all queries
        - "mean_precision_at_k": Average precision@K across all queries
        - "mean_mrr": Average MRR across all queries
        - "mean_hit_rate": Average hit rate across all queries
        - "num_queries": Number of test queries
        - "per_query": List of per-query metric dicts

    TODO:
    1. For each test query:
       a. Call retrieve_fn(query) to get retrieved doc IDs
       b. Compute recall@K: |relevant in top-K| / |total relevant|
       c. Compute precision@K: |relevant in top-K| / K
       d. Compute MRR: 1 / (rank of first relevant result), 0 if none found
       e. Compute hit_rate: 1.0 if any relevant in top-K, else 0.0
    2. Average each metric across all queries
    3. Return aggregated results with per-query breakdown

    Handle edge cases:
    - Empty relevant_doc_ids: skip (or count as perfect if no relevant docs exist)
    - retrieve_fn returns fewer than K results: evaluate on what's returned

    Step-by-step:
        per_query = []
        for tq in test_queries:
            query = tq["query"]
            relevant = tq["relevant_doc_ids"]
            k = tq["k"]
            retrieved = retrieve_fn(query)[:k]     # truncate to K

            relevant_found = len(set(retrieved) & relevant)
            recall = relevant_found / len(relevant) if relevant else 0.0
            precision = relevant_found / k if k > 0 else 0.0

            mrr = 0.0
            for i, doc_id in enumerate(retrieved, start=1):
                if doc_id in relevant:
                    mrr = 1.0 / i
                    break

            hit_rate = 1.0 if relevant_found > 0 else 0.0

            per_query.append({
                "query": query, "recall_at_k": recall,
                "precision_at_k": precision, "mrr": mrr, "hit_rate": hit_rate,
            })

        n = len(per_query)
        return {
            "mean_recall_at_k":    sum(q["recall_at_k"] for q in per_query) / n,
            "mean_precision_at_k": sum(q["precision_at_k"] for q in per_query) / n,
            "mean_mrr":            sum(q["mrr"] for q in per_query) / n,
            "mean_hit_rate":       sum(q["hit_rate"] for q in per_query) / n,
            "num_queries": n,
            "per_query": per_query,
        }
    """
    raise NotImplementedError("Implement evaluate_retrieval_quality()")


# ===========================================================================
# Exercise 5: Multi-Tenant Metadata Schema [3]
#
# READ FIRST:
#   02-rag-pipeline-and-chunking.md
#     -> "## Metadata Filtering" (common fields, pre- vs post-filter)
#     -> "### Filter Strategies" (Pinecone filter syntax examples)
#   01-embeddings-and-vector-databases.md
#     -> "## Vector Databases" -> "### Extended Feature Comparison"
#        (which DBs support which filtering modes)
#
# ALSO SEE:
#   examples.py
#     -> "Pattern 1: In-Memory Vector Store" -> InMemoryVectorStore.search()
#        (metadata_filter parameter shows how filtering integrates with search)
#     -> "Pattern 7: Complete RAG Pipeline" -> RAGPipeline.query()
#        (metadata_filter passed through the full pipeline)
# ===========================================================================

@dataclass
class TenantDocument:
    """A document in a multi-tenant RAG system."""
    text: str
    tenant_id: str
    # TODO: Add more fields as needed by your schema


def design_metadata_schema(doc: TenantDocument) -> dict:
    """Design a metadata schema for a multi-tenant document management system.

    Requirements:
    - Support multiple tenants with strict data isolation
    - Support filtering by: document type, date range, access level, tags
    - Support versioning (same document can have multiple versions)
    - Enable efficient queries like:
        * "Find docs for tenant X of type 'policy' updated after 2024-01-01"
        * "Find all v2 API docs for tenant Y with access_level in ['public', 'internal']"
        * "Find docs tagged 'urgent' for tenant X, sorted by date"

    Args:
        doc: A TenantDocument to generate metadata for

    Returns:
        Dict containing the metadata schema. Must include AT MINIMUM:
        - tenant_id: str (for data isolation)
        - doc_type: str
        - created_at: str (ISO format)
        - updated_at: str (ISO format)
        - access_level: str
        - version: int
        - tags: list[str]
        - source_doc_id: str (groups chunks from same source document)
        - chunk_index: int

    TODO:
    1. Define the complete metadata schema as a dict
    2. Include all required fields plus any additional fields you think
       are important for a production multi-tenant system
    3. Consider:
       - How would you handle access control? (field-level or doc-level?)
       - How would you support efficient date range queries?
       - How would you link chunks back to their source document?
       - What fields would you index for fast filtering?
       - How would you handle document deletion/expiration?

    Interview tip: This exercise tests your system design thinking.
    The schema itself matters less than your reasoning about tradeoffs.
    Be prepared to explain WHY you included each field.

    Step-by-step:
        return {
            # --- Required fields ---
            "tenant_id":      doc.tenant_id,          # partition key for data isolation
            "doc_type":       "guide",                 # e.g., "policy", "api_doc", "guide"
            "created_at":     "2024-01-15T00:00:00Z",  # ISO 8601 for date-range queries
            "updated_at":     "2024-01-15T00:00:00Z",
            "access_level":   "internal",              # "public" | "internal" | "confidential"
            "version":        1,                       # integer, monotonically increasing
            "tags":           ["api", "rate-limiting"], # list of strings for flexible filtering
            "source_doc_id":  "doc-abc-123",           # groups all chunks from one source doc
            "chunk_index":    0,                       # position within the source document
            # --- Additional production fields (your design choices) ---
            # "language":     "en",                    # for multilingual corpora
            # "expires_at":   None,                    # TTL for auto-deletion
            # "content_hash": "sha256...",             # detect duplicate/unchanged content
        }
    """
    raise NotImplementedError("Implement design_metadata_schema()")


# ===========================================================================
# Exercise 6: Context Window Packing [3]
#
# READ FIRST:
#   02-rag-pipeline-and-chunking.md
#     -> "## RAG Pipeline Prompt Assembly" (how context is formatted for the LLM)
#     -> "### Critical Design Decisions" (number of retrieved chunks K)
#   03-advanced-rag-patterns.md
#     -> "## RAG Failure Modes and Debugging"
#        -> "### Common Failure Mode 4: Lost in the Middle"
#        (why stuffing too many chunks hurts quality)
#
# ALSO SEE:
#   examples.py
#     -> "Pattern 7: Complete RAG Pipeline" -> RAGPipeline.build_prompt()
#        (formats selected chunks into the prompt -- your packing result feeds this)
#     -> "Pattern 4: Cross-Encoder Reranker" -> cross_encoder_rerank()
#        (the reranking step that precedes packing: top_n parameter)
# ===========================================================================

def pack_context_window(
    results: list[SearchResult],
    max_tokens: int,
    token_counter: Callable[[str], int] | None = None,
    reserved_tokens: int = 500,
) -> list[SearchResult]:
    """Pack as many relevant chunks as possible into the context window.

    Given a ranked list of search results and a token budget, select the
    maximum number of chunks that fit within the budget while:
    1. Prioritizing higher-ranked (more relevant) results
    2. Reserving tokens for the system prompt and user query
    3. Not exceeding the max_tokens limit
    4. Deduplicating chunks from the same source document

    Args:
        results: Ranked list of SearchResult objects (best first)
        max_tokens: Total context window size (e.g., 4096, 8192, 128000)
        token_counter: Function that returns token count for a string.
                       If None, estimate 1 token per 4 characters.
        reserved_tokens: Tokens reserved for system prompt + user query

    Returns:
        List of SearchResult objects that fit within the budget,
        in their original relevance order

    TODO:
    1. Calculate available token budget: max_tokens - reserved_tokens
    2. Define a token counting function (use provided or default to len(text)//4)
    3. Iterate through results in order (highest relevance first):
       a. Skip if a chunk from the same source document is already included
          (use metadata["source_doc_id"] if available)
       b. Count tokens for this chunk's text
       c. If adding this chunk would exceed budget, skip it (don't stop --
          a later smaller chunk might still fit)
       d. Otherwise, add it and subtract from remaining budget
    4. Return selected results in original order

    Edge cases to handle:
    - A single chunk exceeds the entire budget: truncate it (include partial)
    - All chunks are from the same source: include only the highest-ranked one
    - Empty results list: return empty list

    Interview context: This is a bin-packing problem. Greedy (highest relevance
    first) is good enough -- optimal packing is NP-hard and not worth it for
    <100 chunks. The deduplication logic is the interesting design decision.

    Step-by-step:
        if not results:
            return []

        count_fn = token_counter or (lambda text: len(text) // 4)
        budget = max_tokens - reserved_tokens
        packed = []
        seen_sources = set()

        for result in results:
            src_id = result.document.metadata.get("source_doc_id")
            if src_id and src_id in seen_sources:
                continue  # deduplicate

            tokens = count_fn(result.document.text)

            if tokens > budget and not packed:
                # First chunk exceeds budget -- truncate it
                # Approximate: keep budget*4 chars (inverse of len//4)
                truncated_text = result.document.text[:budget * 4]
                result = SearchResult(
                    document=Document(
                        id=result.document.id,
                        text=truncated_text,
                        vector=result.document.vector,
                        metadata=result.document.metadata,
                    ),
                    score=result.score,
                )
                tokens = count_fn(result.document.text)

            if tokens <= budget:
                packed.append(result)
                budget -= tokens
                if src_id:
                    seen_sources.add(src_id)

        return packed
    """
    raise NotImplementedError("Implement pack_context_window()")


# ===========================================================================
# Test Harness
# ===========================================================================

def _create_test_documents() -> list[Document]:
    """Helper: create sample documents for testing."""
    texts = [
        "HNSW is a graph-based approximate nearest neighbor algorithm used in vector databases.",
        "BM25 is a ranking function used by search engines to estimate relevance of documents.",
        "Cross-encoder rerankers process query-document pairs jointly for more accurate scoring.",
        "Cosine similarity measures the angle between two vectors in high-dimensional space.",
        "Chunk size is one of the most impactful decisions in RAG pipeline design.",
        "pgvector is a PostgreSQL extension for vector similarity search.",
        "Reciprocal Rank Fusion merges results from different search methods.",
        "Fine-tuning changes model behavior while RAG adds external knowledge.",
    ]
    docs = []
    for i, text in enumerate(texts):
        docs.append(Document(
            id=f"doc-{i}",
            text=text,
            vector=mock_embed(text),
            metadata={
                "source_doc_id": f"source-{i % 4}",
                "source": f"file-{i}.md",
                "topic": ["algorithms", "search", "search", "algorithms",
                          "chunking", "databases", "search", "concepts"][i],
            },
        ))
    return docs


def run_tests():
    """Run basic tests for each exercise."""
    print("=" * 60)
    print("Running Exercise Tests")
    print("=" * 60)

    # Test Exercise 1: Basic RAG Pipeline
    print("\n--- Exercise 1: Basic RAG Pipeline ---")
    try:
        pipeline = BasicRAGPipeline()
        count = pipeline.ingest(
            ["Hello world", "RAG is great", "Vector search rocks"],
            [{"source": "a.md"}, {"source": "b.md"}, {"source": "c.md"}],
        )
        assert count == 3, f"Expected 3 documents, got {count}"
        assert len(pipeline.documents) == 3

        results = pipeline.retrieve("vector search", top_k=2)
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert results[0].score >= results[1].score, "Results should be sorted by score"

        prompt = pipeline.build_prompt("test query", results)
        assert len(prompt) == 2, "Prompt should have system + user message"
        assert prompt[0]["role"] == "system"
        assert prompt[1]["role"] == "user"
        assert "test query" in prompt[1]["content"]

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # Test Exercise 2: Document-Aware Chunking
    print("\n--- Exercise 2: Document-Aware Chunking ---")
    try:
        test_doc = """# Introduction
This is the intro section with some text.

```python
def hello():
    print("world")
```

## Details
More details here about the topic.

# Another Section
Final section content."""

        chunks = chunk_document_aware(test_doc, max_chunk_size=500)
        assert len(chunks) > 0, "Should produce at least one chunk"
        assert all("text" in c and "metadata" in c for c in chunks), "Each chunk needs text and metadata"
        assert any(c["metadata"].get("has_code") for c in chunks), "Should detect code blocks"
        assert any(c["metadata"].get("heading") for c in chunks), "Should extract headings"

        # Code block should not be split
        for chunk in chunks:
            if "def hello" in chunk["text"]:
                assert 'print("world")' in chunk["text"], "Code block should be kept intact"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # Test Exercise 3: Hybrid Search with RRF
    print("\n--- Exercise 3: Hybrid Search with RRF ---")
    try:
        docs = _create_test_documents()
        results = hybrid_search_rrf("HNSW graph algorithm", docs, top_k=3)
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].score >= results[1].score >= results[2].score, "Should be sorted by score"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # Test Exercise 4: Retrieval Evaluation
    print("\n--- Exercise 4: Retrieval Evaluation ---")
    try:
        test_queries = [
            {
                "query": "nearest neighbor search",
                "relevant_doc_ids": {"doc-0", "doc-3"},
                "k": 5,
            },
            {
                "query": "search ranking methods",
                "relevant_doc_ids": {"doc-1", "doc-6"},
                "k": 5,
            },
        ]

        def mock_retrieve(query: str) -> list[str]:
            return ["doc-0", "doc-3", "doc-5", "doc-1", "doc-6"]

        result = evaluate_retrieval_quality(test_queries, mock_retrieve)
        assert "mean_recall_at_k" in result
        assert "mean_precision_at_k" in result
        assert "mean_mrr" in result
        assert "mean_hit_rate" in result
        assert "per_query" in result
        assert result["num_queries"] == 2
        assert 0 <= result["mean_recall_at_k"] <= 1
        assert 0 <= result["mean_precision_at_k"] <= 1

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # Test Exercise 5: Metadata Schema
    print("\n--- Exercise 5: Multi-Tenant Metadata Schema ---")
    try:
        doc = TenantDocument(
            text="API rate limiting guide",
            tenant_id="acme-corp",
        )
        schema = design_metadata_schema(doc)
        required_fields = [
            "tenant_id", "doc_type", "created_at", "updated_at",
            "access_level", "version", "tags", "source_doc_id", "chunk_index",
        ]
        for field_name in required_fields:
            assert field_name in schema, f"Missing required field: {field_name}"

        assert schema["tenant_id"] == "acme-corp", "tenant_id should match input"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # Test Exercise 6: Context Window Packing
    print("\n--- Exercise 6: Context Window Packing ---")
    try:
        docs = _create_test_documents()
        results = [
            SearchResult(document=docs[0], score=0.95),
            SearchResult(document=docs[1], score=0.90),
            SearchResult(document=docs[2], score=0.85),
            SearchResult(document=docs[3], score=0.80),
            SearchResult(document=docs[4], score=0.75),
        ]

        # Simple token counter: 1 token per 4 chars
        def count_tokens(text: str) -> int:
            return len(text) // 4

        packed = pack_context_window(
            results,
            max_tokens=200,
            token_counter=count_tokens,
            reserved_tokens=50,
        )

        assert len(packed) > 0, "Should pack at least one chunk"
        assert len(packed) <= len(results), "Cannot pack more than available"

        # Verify budget is respected
        total = sum(count_tokens(r.document.text) for r in packed)
        assert total <= 150, f"Exceeded budget: {total} tokens > 150 available"

        # Verify order is maintained (highest relevance first)
        for i in range(len(packed) - 1):
            assert packed[i].score >= packed[i + 1].score, "Should maintain relevance order"

        # Verify deduplication: no two chunks from same source_doc_id
        seen_sources = set()
        for r in packed:
            src = r.document.metadata.get("source_doc_id")
            if src:
                assert src not in seen_sources, f"Duplicate source: {src}"
                seen_sources.add(src)

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    print("\n" + "=" * 60)
    print("Tests complete. Implement the exercises and re-run!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
