---
title: "LLMs & AI Engineering Quick Reference"
---

# Prompt Patterns

```
System: You are a helpful assistant that...
User:   <context>\n<instructions>\n<examples>
Assistant: (model response)
```

- **Zero-shot**: direct instruction, no examples
- **Few-shot**: 2–5 examples of input $\rightarrow$ output
- **Chain-of-thought**: "Think step by step" or explicit reasoning steps
- **Self-consistency**: sample multiple CoT paths, majority vote
- **ReAct**: Thought $\rightarrow$ Action $\rightarrow$ Observation loop

# RAG Pipeline

```
Documents -> Chunk -> Embed -> Index (vector DB)
Query -> Embed -> Retrieve (top-k) -> Augment prompt -> Generate
```

**Chunking**: fixed-size (512 tokens), semantic (paragraph/section), recursive splitting

**Embedding models**: text-embedding-3-small/large, Cohere embed

**Vector DBs**: Pinecone, Weaviate, pgvector, Chroma, Qdrant

**Retrieval tuning**: chunk size, overlap, top-k, reranking (Cohere, cross-encoder), hybrid search (BM25 + vector)

**Pitfalls**: lost-in-the-middle, chunk boundary issues, stale index

# Tool Use / Function Calling

```json
{"type": "function", "function": {
  "name": "get_weather",
  "parameters": {"location": "string"}
}}
```

- Model returns structured tool call $\rightarrow$ app executes $\rightarrow$ feed result back
- **Structured outputs**: JSON mode or `response_format` for reliable parsing
- **Agent loop**: plan $\rightarrow$ tool call $\rightarrow$ observe $\rightarrow$ repeat until done
- **Guardrails**: validate tool args, limit iterations, sandbox execution

# Evaluation

| Metric | Use case |
|--------|----------|
| Exact match / F1 | Extractive QA |
| BLEU / ROUGE | Summarization, translation |
| LLM-as-judge | Open-ended generation quality |
| Human eval | Gold standard, expensive |

- **Eval sets**: curated, version-controlled, representative of production
- **A/B testing**: compare model versions on real traffic
- **Regression testing**: catch quality drops before deploy

# Production Patterns

- **Guardrails**: input/output filters (toxicity, PII, off-topic detection)
- **Rate limiting**: per-user token/request budgets
- **Caching**: semantic cache (embed query, match similar), exact-match cache
- **Cost optimization**: model routing (small model first, escalate), prompt caching, batch API
- **Streaming**: SSE for token-by-token UX
- **Fallbacks**: retry with backoff, model fallback chain
- **Observability**: log prompts/completions, track latency/cost/quality

# Key APIs — Chat Completions

```python
client.chat.completions.create(
  model="gpt-4o",
  messages=[{"role": "system", "content": "..."},
            {"role": "user", "content": "..."}],
  temperature=0.7,   # 0=deterministic, 1=creative
  max_tokens=1024,
  tools=[...],       # function definitions
  stream=True,       # SSE streaming
)
```

**Embeddings**: `client.embeddings.create(model=..., input=...)`

**Key params**: `temperature`, `top_p`, `max_tokens`, `stop`, `frequency_penalty`

# Model Selection

| Need | Model class |
|------|-------------|
| Best quality | Claude Opus / GPT-4o / Gemini Ultra |
| Speed + cost | Claude Haiku / GPT-4o-mini / Gemini Flash |
| Embeddings | text-embedding-3-small (OpenAI) / embed-v3 (Cohere) |
| Open source | Llama 3, Mistral, Qwen |
