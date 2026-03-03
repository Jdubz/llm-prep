# LLM Engineering

Advanced LLM implementation for applied AI engineers. Covers transformer internals, prompt engineering, RAG, agents, fine-tuning, evaluation, and production systems — everything you need for AI engineering interviews.

> **Perspective**: You already know how to build software. This course focuses on what's different about building with LLMs — the mental models, architectural patterns, and production concerns that matter in interviews and on the job.

---

## Modules

### 00 — [AI & ML Foundations](00-ai-foundations.md)
- What machine learning actually is (training vs inference, supervised vs self-supervised)
- Neural networks in 5 minutes (neurons, layers, gradient descent, overfitting)
- Key LLM concepts: tokens, embeddings, attention, temperature, context windows
- The LLM stack: how an API call works, provider APIs, autoregressive generation
- Python essentials for LLM engineering
- Math intuition: vectors, cosine similarity, softmax, loss functions

### 01 — LLM Fundamentals
- [01 – Transformer Architecture Fundamentals](./01-llm-fundamentals/01-transformer-architecture-fundamentals.md) — attention mechanism, tokenization, positional encoding, KV cache, generation parameters
- [02 – Training and Model Families](./01-llm-fundamentals/02-training-and-model-families.md) — pre-training, SFT, RLHF, DPO, scaling laws, model comparison table, cost estimation
- [03 – Advanced LLM Concepts](./01-llm-fundamentals/03-advanced-llm-concepts.md) — quantization, speculative decoding, continuous batching, PagedAttention, reasoning models, distillation, glossary

### 02 — Prompt Engineering
- [01 – Prompting Fundamentals](./02-prompt-engineering/01-prompting-fundamentals.md) — system prompts, zero-shot, few-shot, CoT, structured output, delimiters, prompt chaining
- [02 – Prompt Patterns and Techniques](./02-prompt-engineering/02-prompt-patterns-and-techniques.md) — decision tree, standard templates, provider differences, cost optimization checklist
- [03 – Advanced Prompting Strategies](./02-prompt-engineering/03-advanced-prompting-strategies.md) — self-consistency, tree-of-thought, meta-prompting, constitutional AI, prompt caching, optimization workflow

### 03 — RAG & Retrieval
- [01 – Embeddings and Vector Databases](./03-rag-and-retrieval/01-embeddings-and-vector-databases.md) — embedding models, similarity metrics, vector DB comparison, ANN algorithms (HNSW, IVF, PQ)
- [02 – RAG Pipeline and Chunking](./03-rag-and-retrieval/02-rag-pipeline-and-chunking.md) — ingestion and query pipelines, chunking strategies, hybrid search, reranking, metadata filtering
- [03 – Advanced RAG Patterns](./03-rag-and-retrieval/03-advanced-rag-patterns.md) — query transformation, HyDE, multi-hop retrieval, agentic RAG, RAGAS evaluation, GraphRAG

### 04 — Agents & Tool Use
- [01 – Function Calling and Tool Use](./04-agents-and-tool-use/01-function-calling-and-tool-use.md) — tool schemas, provider APIs, parallel tool calls, structured output vs tool use, validation
- [02 – Agent Patterns and Memory](./04-agents-and-tool-use/02-agent-patterns-and-memory.md) — agent loop, ReAct, planning patterns, memory systems, guardrails, MCP
- [03 – Advanced Agent Systems](./04-agents-and-tool-use/03-advanced-agent-systems.md) — multi-agent architectures, long-running agents, HITL, agent evaluation, computer use

### 05 — Fine-tuning & Model Customization
- [01 – Fine-tuning Fundamentals](./05-fine-tuning/01-fine-tuning-fundamentals.md) — decision framework, LoRA, QLoRA, data preparation, synthetic data, GPU requirements
- [02 – Training and Alignment](./05-fine-tuning/02-training-and-alignment.md) — RLHF, DPO, catastrophic forgetting, model merging, continued pre-training, open-source stack
- [03 – Advanced Fine-tuning and Infrastructure](./05-fine-tuning/03-advanced-fine-tuning-and-infrastructure.md) — DeepSpeed ZeRO, FSDP, Flash Attention, quantization for deployment, distillation

### 06 — Evaluation & Safety
- [01 – Evaluation Frameworks and Metrics](./06-evaluation-and-safety/01-evaluation-frameworks-and-metrics.md) — eval methods, LLM-as-judge, dataset building, eval-driven development, CI/CD integration
- [02 – Safety Guardrails and Red Teaming](./06-evaluation-and-safety/02-safety-guardrails-and-red-teaming.md) — defense in depth, input/output safety, prompt injection defense, adversarial testing
- [03 – Responsible AI and Eval Operations](./06-evaluation-and-safety/03-responsible-ai-and-eval-operations.md) — hallucination detection, A/B testing, bias and fairness, compliance, advanced eval topics

### 07 — Production Systems
- [01 – Caching, Cost Optimization, and Observability](./07-production-systems/01-caching-cost-optimization-and-observability.md) — streaming, response caching, model routing, token reduction, distributed tracing, rate limiting
- [02 – Latency, Reliability, and Error Handling](./07-production-systems/02-latency-reliability-and-error-handling.md) — structured output reliability, latency optimization, circuit breakers, fallback chains, graceful degradation
- [03 – Advanced Production Patterns](./07-production-systems/03-advanced-production-patterns.md) — self-hosted inference (vLLM, TGI), PagedAttention, speculative decoding, gateway patterns, capacity planning, disaster recovery

### 08 — Interview Prep
- [01 – Interview Fundamentals and Reference](./08-interview-prep/01-interview-fundamentals-and-reference.md) — core concepts at interview depth, 30-second answers, key numbers, comparison tables, anti-patterns, buzzword decoder
- [02 – System Design and Scenarios](./08-interview-prep/02-system-design-and-scenarios.md) — 4 complete system design walkthroughs (RAG support, coding assistant, content moderation, multi-agent research), scenario Q&A

---

## Content Per Module

Each module directory contains numbered files organized by topic:

- **`01-*.md`** — Foundational concepts from scratch. Core mechanics, APIs, and mental models.
- **`02-*.md`** — Patterns, workflows, and practical application. Includes decision trees, templates, and interview Q&A.
- **`03-*.md`** — Advanced internals, edge cases, and deep-dive content (where present).

Cheat-sheet tables, decision trees, and key numbers are embedded inline in the most topically relevant file.

---

## Prerequisites
- Solid understanding of REST APIs and distributed systems
- Familiarity with at least one backend language (Python or TypeScript)
- Read [Module 00: AI & ML Foundations](00-ai-foundations.md) if you're new to ML/AI concepts

## Status
**Content complete** — all modules written with exercises, examples, and full interview prep.
