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
- Transformer architecture, attention mechanism, positional encoding
- Tokenization (BPE, SentencePiece, WordPiece) and its implications
- Training pipeline: pre-training, SFT, RLHF, DPO
- Model families comparison (GPT-4, Claude, Gemini, Llama, Mistral, DeepSeek)
- Inference parameters: temperature, top-p, top-k, sampling strategies
- Scaling laws, KV cache, context window management

### 02 — Prompt Engineering
- Zero-shot, few-shot, chain-of-thought, self-consistency
- Structured output: JSON mode, constrained decoding, provider-specific approaches
- Prompt chaining and decomposition
- Prompt injection defense strategies
- Advanced: tree-of-thought, meta-prompting, prompt optimization workflows

### 03 — RAG & Retrieval
- Embeddings, similarity metrics, vector databases
- Chunking strategies (fixed, recursive, semantic, document-aware)
- Hybrid search (semantic + BM25), reranking with cross-encoders
- Query transformation, HyDE, multi-hop retrieval
- RAG evaluation metrics and failure modes

### 04 — Agents & Tool Use
- Function calling / tool use across providers
- Agent loop design, ReAct pattern, planning strategies
- Model Context Protocol (MCP)
- Memory systems (conversation, episodic, semantic)
- Multi-agent architectures, human-in-the-loop patterns

### 05 — Fine-tuning & Model Customization
- Decision framework: fine-tuning vs RAG vs prompt engineering
- LoRA, QLoRA, adapter methods — when to use which
- Data preparation, synthetic data generation
- RLHF, DPO, and alignment techniques
- Distillation, quantization, training infrastructure

### 06 — Evaluation & Safety
- Eval frameworks: LLM-as-judge, benchmarks, human evaluation
- Eval-driven development workflow
- Prompt injection, jailbreaking, content filtering
- Guardrails architecture, red teaming
- Hallucination detection and mitigation

### 07 — Production Systems
- Streaming architecture (SSE, partial JSON, tool calls)
- Caching strategies (response, semantic, prompt caching)
- Cost optimization: model routing, token reduction, batching
- Observability: tracing, logging, metrics for LLM pipelines
- Inference infrastructure, gateway patterns, disaster recovery

### 08 — Interview Prep
- 40+ LLM interview questions with expert answers
- System design exercises: RAG service, coding assistant, moderation pipeline, multi-agent research assistant
- Timed coding challenges
- Quick-fire reference for last-minute review

---

## Content Per Module

Each module directory contains:

- **`README.md`** — Core interview knowledge. Concise, pattern-focused, interview-ready.
- **`deep-dive.md`** — Extended content. Internals, edge cases, advanced patterns.
- **`cheat-sheet.md`** — Quick reference card. Scannable during prep.
- **`examples.py`** — Complete, runnable production patterns.
- **`exercises.py`** — Skeleton functions with TODOs. Implement to test your knowledge.

---

## Prerequisites
- Solid understanding of REST APIs and distributed systems
- Familiarity with at least one backend language (Python or TypeScript)
- Read [Module 00: AI & ML Foundations](00-ai-foundations.md) if you're new to ML/AI concepts

## Status
**Content complete** — all modules written with exercises, examples, and full interview prep.
