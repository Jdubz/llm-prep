# 03 — Advanced RAG Patterns

## Query Transformation

User queries are often poorly suited for direct retrieval. They may be ambiguous, too short, use different terminology than the documents, or — in multi-turn conversations — refer to previous context ("what about it?" retrieves nothing useful). Query transformation improves retrieval by restructuring the query before embedding.

### Query Rewriting

Reformulate the query to be more explicit, complete, and document-like:

```python
def rewrite_query(
    original_query: str,
    conversation_history: list[dict] = None
) -> str:
    history_context = ""
    if conversation_history:
        recent = conversation_history[-4:]
        history_context = f"""
Previous conversation:
{format_history(recent)}
"""
    prompt = f"""Rewrite the following question to be more explicit and
self-contained, suitable for document retrieval. Resolve any references to
previous conversation context.
{history_context}
Original question: {original_query}

Rewritten question (standalone, specific):"""

    return llm_call(prompt, temperature=0).strip()
```

**Example:**
```
Original: "What about the API rate limits?"
Context:  Previous turn discussed OpenAI pricing

Rewritten: "What are the rate limits for the OpenAI API, including
           requests per minute and tokens per minute by tier?"
```

### HyDE (Hypothetical Document Embeddings)

Instead of embedding the query directly, generate a hypothetical document that would answer the query, then embed that document. The hypothesis lives in document space rather than query space, often matching documents more precisely.

```python
def hyde_search(
    query: str,
    vector_store: VectorStore,
    top_k: int = 5
) -> list[dict]:
    # Step 1: Generate a hypothetical answer
    hypothesis_prompt = f"""Write a brief, informative passage that
directly answers the following question. Write as if from an authoritative
source. If you don't know the exact answer, write a plausible passage
that would appear in relevant documentation.

Question: {query}

Passage:"""

    hypothesis = llm_call(hypothesis_prompt, temperature=0.3)

    # Step 2: Embed the hypothesis instead of the query
    hypothesis_embedding = embed(hypothesis)

    # Step 3: Search with the hypothesis embedding
    results = vector_store.similarity_search_by_vector(
        hypothesis_embedding,
        k=top_k
    )

    return results
```

**When HyDE helps:**
- Queries that are very short or abstract ("What is the pricing?")
- Domain-specific questions where query vocabulary differs from document vocabulary
- Questions where the answer structure is predictable

**When HyDE hurts:**
- The model hallucinates a plausible-sounding hypothesis that retrieves wrong documents
- Very specific queries where the hypothesis introduces unrelated terms

### Multi-Query Expansion

Generate multiple reformulations of the same query and retrieve for all of them. Merges results to improve recall.

```python
def multi_query_search(
    query: str,
    vector_store: VectorStore,
    n_variants: int = 3,
    top_k: int = 5
) -> list[dict]:
    # Generate query variants
    generate_prompt = f"""Generate {n_variants} different ways to phrase
the following question. Each variant should cover a different aspect or use
different terminology. Output one question per line.

Original: {query}

Variants:"""

    variants_text = llm_call(generate_prompt)
    variants = [query] + [v.strip() for v in variants_text.strip().split("\n") if v.strip()]

    # Search with each variant
    all_results = {}
    for variant in variants:
        results = vector_store.similarity_search(variant, k=top_k)
        for r in results:
            if r["id"] not in all_results:
                all_results[r["id"]] = r

    return list(all_results.values())
```

**Example expansion:**
```
Original: "How do I reset my password?"

Variants:
1. "What is the process for changing a forgotten password?"
2. "Password recovery steps for locked account"
3. "Account access restoration after password loss"
```

### Step-Back Prompting

Retrieve general background knowledge first, then use it to answer the specific question:

```python
def step_back_rag(query: str, vector_store: VectorStore) -> str:
    # Step 1: Generate a more general "step-back" question
    step_back_prompt = f"""Generate a more general question that provides
background context for answering the specific question below.

Specific question: {query}

More general question:"""

    general_query = llm_call(step_back_prompt)

    # Step 2: Retrieve for both the general and specific questions
    general_results = vector_store.similarity_search(general_query, k=3)
    specific_results = vector_store.similarity_search(query, k=3)

    # Step 3: Combine context
    all_context = general_results + specific_results  # deduplicate in practice
    return generate_answer(query, all_context)
```

**Query transformation comparison:**

| Method | When to Use | Cost | Retrieval Improvement |
|---|---|---|---|
| Query rewriting | Multi-turn conversations, vague queries | Low (1 LLM call) | Medium |
| HyDE | Short/abstract queries, terminology mismatch | Low (1 LLM call) | High when it works |
| Multi-query expansion | Ambiguous queries, need high recall | Medium (N results) | High recall |
| Step-back | Complex questions needing background | Medium (2 LLM calls) | Context enrichment |

---

## Multi-Hop Retrieval

Simple RAG retrieves once and answers. Multi-hop retrieval iteratively retrieves and reasons, following chains of evidence across documents.

### The Problem

```
Question: "What programming language was used to build the database
           that stores the results from the system described in the
           2023 Q4 report?"

Required steps:
1. Find what system is described in the 2023 Q4 report
2. Find which database that system uses
3. Find what language that database was built with
```

A single retrieval step cannot answer this — it requires chaining multiple lookups.

### Iterative Retrieval Pattern

```python
def multi_hop_rag(
    initial_query: str,
    vector_store: VectorStore,
    max_hops: int = 3
) -> str:
    context_accumulated = []
    current_query = initial_query

    for hop in range(max_hops):
        # Retrieve for current query
        results = vector_store.similarity_search(current_query, k=3)
        context_accumulated.extend(results)

        # Decide: is this sufficient or do we need another hop?
        decision_prompt = f"""Given the original question and retrieved context,
determine if you have enough information to answer, or if you need to search
for something else.

Original question: {initial_query}

Context so far:
{format_chunks(context_accumulated)}

Respond with one of:
- ANSWER: [your answer] (if you have enough information)
- SEARCH: [next search query] (if you need more information)"""

        decision = llm_call(decision_prompt)

        if decision.startswith("ANSWER:"):
            return decision[len("ANSWER:"):].strip()
        elif decision.startswith("SEARCH:"):
            current_query = decision[len("SEARCH:"):].strip()
        else:
            break

    # Final generation with all accumulated context
    return generate_answer(initial_query, context_accumulated)
```

---

## Agentic RAG

Agentic RAG gives the model control over the retrieval process itself, treating retrieval as a tool to be invoked on demand rather than a fixed step.

### Self-RAG

Self-RAG trains the model to decide when to retrieve, what to retrieve, and whether the retrieved content is relevant. At inference time, the model inserts special tokens to control its own retrieval:

```
User: "Who invented the telephone?"

Model thinking:
[Retrieve?] Yes - factual question about historical claim
[Query]: "invention of telephone history"
[Retrieved]: "Alexander Graham Bell is widely credited with inventing..."
[Is Relevant?] Yes
[Is Supported?] Yes

Response: "Alexander Graham Bell invented the telephone in 1876."
```

### CRAG (Corrective RAG)

CRAG adds a relevance evaluator that grades retrieved documents and triggers different retrieval strategies based on the grade:

```python
def crag_retrieve(query: str, vector_store: VectorStore) -> list[dict]:
    # Initial retrieval
    results = vector_store.similarity_search(query, k=5)

    # Evaluate relevance
    relevance_scores = evaluate_relevance(query, results)

    if all(score > 0.8 for score in relevance_scores):
        # High quality retrieval — proceed
        return results

    elif any(score > 0.5 for score in relevance_scores):
        # Mixed quality — filter and supplement with web search
        good_results = [r for r, s in zip(results, relevance_scores) if s > 0.5]
        web_results = web_search(query)  # Supplement with web results
        return good_results + web_results

    else:
        # Poor retrieval — fall back to web search entirely
        return web_search(query)
```

### Tool-Augmented RAG

The model has retrieval as one of several tools:

```python
tools = [
    {
        "name": "search_knowledge_base",
        "description": "Search the internal knowledge base for relevant information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "category": {"type": "string", "enum": ["product", "billing", "technical"]}
            }
        }
    },
    {
        "name": "search_web",
        "description": "Search the web for current information not in the knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            }
        }
    },
    {
        "name": "lookup_customer_account",
        "description": "Retrieve a customer's account information by email or ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"}
            }
        }
    }
]
```

---

## RAGAS: RAG Evaluation Framework

RAGAS provides automated metrics for evaluating all components of a RAG pipeline using LLM-as-judge and heuristic scoring.

### Four Core Metrics

**1. Faithfulness**
Are the claims in the answer supported by the retrieved context?

```
Process:
1. Decompose the answer into individual claims
2. For each claim, check if it can be inferred from the retrieved context
3. Score = supported_claims / total_claims

Target: > 0.85

Example:
Answer claim: "The return window is 30 days"
Context contains: "Items may be returned within 30 days of purchase"
Claim: SUPPORTED → score contribution: 1.0

Answer claim: "Shipping is always free on returns"
Context contains: nothing about return shipping
Claim: NOT SUPPORTED → score contribution: 0.0
```

**2. Answer Relevance**
Does the answer actually address the question?

```
Process:
1. Generate N questions that the answer would be a good response to
2. Embed the generated questions
3. Compute cosine similarity between generated questions and original question
4. Score = mean(similarities)

Target: > 0.80

Low score indicates:
- Answer is off-topic
- Answer contains mostly irrelevant information
- Answer addresses a different interpretation of the question
```

**3. Context Precision**
Are the retrieved documents actually relevant? Are the most relevant documents ranked highest?

```
Process:
For each retrieved chunk, determine if it's relevant to the question.
Score = relevant_chunks_in_top_k / total_retrieved_k
Weighted by position (earlier = higher weight).

Target: > 0.75

Low score indicates:
- Retrieval is returning too many irrelevant chunks
- Relevant chunks are buried below irrelevant ones (ranking problem)
```

**4. Context Recall**
Did the retrieval find all the information needed to answer the question?

```
Process:
For each sentence in the ground-truth answer, check if the information
can be attributed to the retrieved context.
Score = attributable_ground_truth_sentences / total_ground_truth_sentences

Target: > 0.75

Low score indicates:
- Relevant documents are missing from the vector store
- Chunking is splitting relevant information
- Retrieval is not finding the right documents
```

### Running RAGAS

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from datasets import Dataset

# Prepare evaluation dataset
eval_data = {
    "question": ["What is the return policy?", "How do I reset my password?"],
    "answer": ["Items can be returned within 30 days...", "Go to settings..."],
    "contexts": [
        ["[retrieved chunk 1]", "[retrieved chunk 2]"],
        ["[retrieved chunk 3]"],
    ],
    "ground_truth": ["The return window is 30 days...", "Password reset via settings..."]
}

dataset = Dataset.from_dict(eval_data)

result = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)

print(result)
# {'faithfulness': 0.89, 'answer_relevancy': 0.84, 'context_precision': 0.78, 'context_recall': 0.82}
```

### Building an Evaluation Dataset

```python
def create_rag_eval_set(documents: list[str]) -> list[dict]:
    """Generate evaluation QA pairs from documents using an LLM."""
    eval_pairs = []

    for doc in documents:
        # Generate questions from the document
        questions_prompt = f"""Generate 3 specific, factual questions that can be
answered from this document. Include questions of varying difficulty.

Document:
{doc}

Questions (one per line):"""

        questions_text = llm_call(questions_prompt)
        questions = [q.strip() for q in questions_text.strip().split("\n") if q.strip()]

        for question in questions:
            # Generate the ground truth answer
            answer_prompt = f"""Answer this question using ONLY the provided document.

Document: {doc}
Question: {question}
Answer:"""
            answer = llm_call(answer_prompt)

            eval_pairs.append({
                "question": question,
                "ground_truth": answer,
                "source_doc": doc
            })

    return eval_pairs
```

---

## RAG Failure Modes and Debugging

### Common Failure Mode 1: Wrong Chunks Retrieved

**Symptoms:** LLM generates plausible but incorrect answers; answers from wrong documents
**Debug process:**
```python
def diagnose_retrieval(query: str, vector_store: VectorStore) -> dict:
    results = vector_store.similarity_search(query, k=10, include_scores=True)

    print(f"Query: {query}\n")
    for i, (chunk, score) in enumerate(results):
        print(f"Rank {i+1} (score: {score:.3f}): {chunk['text'][:100]}...")

    # Manually assess: are these the right chunks?
```

**Fixes:**
- Adjust chunk size (too small lacks context, too large dilutes relevance)
- Add hybrid search (missing exact terminology?)
- Add reranking (right chunks retrieved but in wrong order?)
- Add contextual chunk headers (chunks lack identifying context?)
- Improve embedding model (try a higher-quality model)

### Common Failure Mode 2: Model Ignores the Context

**Symptoms:** Model answers from training knowledge instead of provided context; ignores "I don't know" instruction
**Fixes:**
- Strengthen grounding instructions: "Answer ONLY from the provided context. If the answer is not there, say so."
- Reduce context noise: fewer but more relevant chunks
- Put the most relevant context first (models attend more to beginning/end)
- Add citation requirements: "cite the source document by name for every claim"

### Common Failure Mode 3: Hallucination Beyond Context

**Symptoms:** Model uses some retrieved information but adds fabricated details
**Fixes:**
- Citation requirements: force the model to reference specific passages
- Grounding check post-generation (verify claims against context)
- Self-consistency: generate multiple answers and check agreement

### Common Failure Mode 4: "Lost in the Middle"

**Symptoms:** Information in the middle of the retrieved context is ignored; model uses only the first and last chunks
**Fixes:**
- Reduce the number of chunks (from 10 to 3–5)
- Put most relevant chunk first (or last)
- Use a model with better long-context performance

### Debugging Checklist

```
Retrieval issues:
□ Log retrieved chunks for failing queries — are they relevant?
□ Check similarity scores — are they in the expected range (0.7+)?
□ Test retrieval and generation independently
□ Run RAGAS context_precision and context_recall metrics
□ Try different chunk sizes on failing query types

Generation issues:
□ Add explicit grounding instructions
□ Check for conflicting information in the context
□ Test with perfect retrieval (manually provide the right chunk) — does generation succeed?
□ Run RAGAS faithfulness metric

Pipeline issues:
□ Verify ingestion is complete and current
□ Check for embedding model mismatch (ingestion vs query)
□ Monitor chunk count and document coverage
```

---

## Advanced: Knowledge Graphs + RAG (GraphRAG)

Standard vector search finds semantically similar chunks but cannot represent relationships between entities. A customer support bot may retrieve the right document about a product feature but miss that the feature was deprecated in a specific region — a relational fact.

### GraphRAG Architecture

Microsoft's GraphRAG approach:

```
1. Entity Extraction
   → NER on all documents
   → Extract: entities + relationships

2. Graph Construction
   → Nodes: entities (people, products, concepts, organizations)
   → Edges: relationships (uses, is_deprecated_in, is_part_of, created_by)

3. Community Detection
   → Find clusters of closely related entities
   → Summarize each community with an LLM

4. Hybrid Retrieval
   → Vector search for semantic similarity
   → Graph traversal for related entities and facts
   → Community summaries for broad questions

5. Generation
   → Ground the LLM in both retrieved chunks and graph context
```

### When to Use GraphRAG

**Use GraphRAG when:**
- Questions require reasoning across relationships: "What products use the deprecated API?"
- Complex multi-entity questions: "Who are the customers that use both Product A and Product B?"
- The knowledge graph already exists or can be extracted naturally
- Query types are relationship-heavy (organizational questions, dependency tracking)

**Stick with standard RAG when:**
- Questions are primarily about document content, not entity relationships
- The dataset does not have strong entity-relationship structure
- Infrastructure complexity is a concern (graph databases add significant ops burden)
- You need fast deployment without a custom graph extraction pipeline

---

## Production RAG Patterns

### RAG with Streaming

```python
async def streaming_rag(query: str, vector_store: VectorStore) -> AsyncIterator[str]:
    """Run retrieval synchronously, then stream generation."""
    # Retrieval (non-streaming, must complete before generation)
    chunks = await vector_store.asimilarity_search(query, k=5)
    prompt = assemble_rag_prompt(query, chunks)

    # Stream generation
    async for token in llm_stream(prompt):
        yield token
```

### Incremental Indexing

```python
def incremental_update(
    new_docs: list[Document],
    deleted_doc_ids: list[str],
    updated_docs: list[Document],
    vector_store: VectorStore
) -> dict:
    """Update the vector index incrementally without full re-indexing."""

    stats = {"inserted": 0, "deleted": 0, "updated": 0, "errors": 0}

    # Delete removed documents
    for doc_id in deleted_doc_ids:
        chunk_ids = get_chunk_ids_for_doc(doc_id)
        vector_store.delete(ids=chunk_ids)
        stats["deleted"] += len(chunk_ids)

    # Update modified documents (delete old + insert new)
    for doc in updated_docs:
        old_chunk_ids = get_chunk_ids_for_doc(doc.id)
        vector_store.delete(ids=old_chunk_ids)
        new_chunks = chunk_and_embed(doc)
        vector_store.add(new_chunks)
        stats["updated"] += 1

    # Insert new documents
    for doc in new_docs:
        new_chunks = chunk_and_embed(doc)
        vector_store.add(new_chunks)
        stats["inserted"] += 1

    return stats
```

### RAG with Observability

Every RAG request should log:

```python
@dataclass
class RAGTrace:
    request_id: str
    query: str
    rewritten_query: str | None
    retrieved_chunks: list[dict]  # id, score, text[:100]
    reranked_chunks: list[dict] | None
    prompt_tokens: int
    output_tokens: int
    ttft_ms: float
    total_ms: float
    faithfulness_score: float | None  # if evaluated
    cache_hit: bool
    error: str | None
```

---

## Summary: Basic to Great RAG

| Component | Basic | Good | Great |
|---|---|---|---|
| Chunking | Fixed-size | Recursive character | Semantic + contextual headers |
| Retrieval | Vector-only | Hybrid search | Hybrid + reranking |
| Query processing | Raw query | Query rewriting | Multi-query + HyDE |
| Context | Top-K chunks | Top-K + metadata filter | Parent-child + reranked |
| Evaluation | Manual spot-check | Offline RAGAS suite | RAGAS + online monitoring |
| Index maintenance | Full re-index | Change detection | Incremental with monitoring |

---

## Interview Q&A: Advanced RAG

**Q: What are common RAG failure modes and how do you debug them?**

The most common failure is retrieving wrong chunks. Debug by logging exactly what is retrieved for failing queries — often chunk size is the culprit (too small lacks context, too large dilutes relevance), or pure vector search misses exact terminology (fix with hybrid search), or chunks lack identifying context (fix with contextual chunk headers). Second failure: model ignores context and answers from training. Fix by strengthening grounding instructions and adding citation requirements. Third failure: "lost in the middle" — model uses first and last chunks but ignores middle. Fix by reducing chunk count and putting the most relevant context first. Key principle: always test retrieval and generation independently — many "generation" problems are actually retrieval problems.

**Q: How do you evaluate RAG quality end-to-end?**

Three dimensions: retrieval quality, generation quality, and end-to-end. For retrieval, measure Recall@K (what fraction of relevant documents are in your top-K) and Precision@K (what fraction of your top-K is relevant). Requires a labeled set of (query, relevant_documents) pairs. For generation, measure faithfulness (does the answer only use context information, or does it add fabrications?) and answer relevance (does it address the question?). The RAGAS framework automates these metrics using LLM-as-judge. End-to-end requires either human evaluation or a well-calibrated judge pipeline. Target scores: faithfulness > 0.85, relevance > 0.80, precision > 0.75, recall > 0.75.

**Q: When would you use GraphRAG over standard vector RAG?**

When the knowledge domain is heavily relationship-centric — questions require reasoning across entity relationships ("what products use the deprecated API?"), complex multi-hop reasoning ("who are customers of companies that partner with X?"), or synthesizing patterns across many documents (global summaries, trend analysis). Standard vector RAG excels at semantic similarity — finding documents that discuss a topic. Graph RAG adds the ability to traverse relationships between entities, which pure vector search cannot model. The cost: GraphRAG requires an entity extraction pipeline, a graph database, community detection, and much more complex infrastructure. Only introduce it when standard RAG measurably fails on relationship-heavy query types.

**Q: What is HyDE and when does it help?**

HyDE (Hypothetical Document Embeddings) generates a hypothetical answer to the query, then embeds that hypothesis instead of the original query. The key insight: queries and documents live in slightly different parts of embedding space, and a hypothesis lives in document space — closer to the documents we want to retrieve. It particularly helps when queries are abstract or use different terminology than the documents (the hypothesis "bridges the gap"), and for short queries where there's not enough signal in the query alone. It hurts when the hypothesis itself is wrong (hallucination retrieves wrong documents), so it works best for questions with predictable answer structure and when the LLM has reasonable background knowledge about the domain.
