# Interview Fundamentals and Quick Reference

Core LLM engineering concepts explained at interview depth, plus quick-reference tables, 30-second answers, comparison tables, and anti-patterns.

---

## Core Concepts — Interview-Depth Answers

### LLM Fundamentals

**How do transformers work? What makes them better than RNNs?**

Transformers process all tokens in a sequence simultaneously using self-attention, rather than sequentially like RNNs. Each layer has two main components: multi-head self-attention, which lets every token compute relevance scores against every other token, and a feed-forward network that transforms those contextualized representations. The input goes through tokenization, embedding, and positional encoding before hitting a stack of these transformer blocks, and the output is a probability distribution over the vocabulary for the next token.

The key advantage over RNNs is parallelism. Since every token attends to every other token directly, there is no sequential bottleneck. RNNs process tokens one at a time and struggle with long-range dependencies because information has to survive through every intermediate step. Transformers also scale much better with hardware — you can throw more GPUs at training a transformer in ways that are not practical with recurrent architectures.

Key points to hit:
- Self-attention enables parallel processing of all tokens.
- No sequential bottleneck means better training efficiency and GPU utilization.
- Direct access to all positions solves the long-range dependency problem.
- Positional encodings compensate for the lack of inherent sequence ordering.
- Attention is O(n^2) in sequence length, which is why context windows have limits.

---

**Explain the attention mechanism. What is multi-head attention?**

Attention lets each token compute how relevant every other token is to it. Each token produces three vectors: a Query ("what am I looking for"), a Key ("what do I represent"), and a Value ("what information do I carry"). You take the dot product of Queries against Keys to get relevance scores, normalize with softmax, and use those weights to create a weighted sum of Values. The formula is `Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V`, where the division by sqrt(d_k) prevents the dot products from getting too large and pushing softmax into saturation.

Multi-head attention runs this computation multiple times in parallel with different learned projection matrices. Each "head" can learn to attend to different types of relationships — one head might capture syntactic dependencies, another might track coreference, another might focus on positional proximity. The outputs of all heads are concatenated and projected back to the model dimension. In practice, GPT-class models use 32-128 heads.

Key points: Q/K/V projections and the scaled dot-product formula, softmax normalization creates a probability distribution over positions, multi-head runs in parallel with different learned projections, different heads capture different relationship types, the sqrt(d_k) scaling prevents gradient issues in softmax.

---

**What is tokenization and why does it matter?**

Tokenization is how text is converted into the discrete units the model actually processes. Most modern LLMs use subword tokenization algorithms like BPE (Byte Pair Encoding), which learns a vocabulary by iteratively merging the most frequent character pairs in the training corpus. Common words become single tokens, while rare or compound words get split into pieces — "tokenization" might become ["token", "ization"]. Typical vocabularies are 32K to 100K tokens.

This matters in several practical ways. First, pricing — you pay per token for both input and output. Second, context windows are measured in tokens, not words (roughly 0.75 words per token for English, worse for other languages). Third, tokenization creates real edge cases: arithmetic is unreliable partly because numbers get split unpredictably, code-heavy prompts may tokenize inefficiently, and non-Latin scripts use more tokens per semantic unit.

Key points: BPE / SentencePiece are the dominant algorithms, subword units (not words or characters), cost and context limits are per-token, non-English text and code may tokenize inefficiently, tokenizer is model-specific.

---

**Explain the training pipeline: pre-training, SFT, RLHF.**

Three main stages. Pre-training is the expensive one: train on massive internet-scale text corpora (trillions of tokens) with a next-token prediction objective. This is where the model learns language, facts, reasoning patterns, and code. The result is a powerful text completer but not a helpful assistant.

Supervised fine-tuning (SFT) trains on curated (instruction, response) pairs — maybe tens of thousands of high-quality examples showing what a good assistant response looks like. This teaches the model the conversational format and instruction-following behavior. Finally, alignment via RLHF (Reinforcement Learning from Human Feedback) or DPO (Direct Preference Optimization) teaches the model to prefer helpful, harmless, honest responses. Human raters rank outputs, a reward model is trained on those preferences, and the LLM is optimized against it.

Key points: pre-training is next-token prediction on internet-scale data (most expensive stage), SFT teaches instruction-following from curated examples, RLHF/DPO alignment from human preferences, each stage serves a different purpose and uses different data, DPO is an alternative to RLHF that skips the reward model.

---

**What is the KV cache and why does it matter?**

The KV cache stores the computed Key and Value matrices from previous tokens during autoregressive generation. Without it, every time the model generates a new token, it would need to recompute attention over all previous tokens from scratch. With the KV cache, you only compute Q, K, V for the new token and reuse the cached K and V from all previous positions.

In practice, this is why the first token takes longer than subsequent tokens — the initial "prefill" phase processes the entire prompt and builds the KV cache, while "decode" phases incrementally extend it. The KV cache also explains memory pressure at long context lengths: for a 128K context window, the KV cache for a single request can consume gigabytes of GPU memory. Techniques like GQA (Grouped Query Attention) and KV cache quantization are used to reduce this footprint.

Key points: caches Key and Value matrices to avoid recomputation, prefill (prompt processing) vs. decode (token generation) distinction, memory scales linearly with sequence length, GQA and MQA reduce KV cache size by sharing heads, directly impacts inference cost, latency, and throughput.

---

**What is hallucination and how do you mitigate it?**

Hallucination is when a model generates plausible-sounding but factually incorrect content. It happens because LLMs optimize for text that is probable given the context, not text that is true. The model has no internal mechanism to verify facts — it is pattern-matching against its training distribution. This is not a bug you can fix; it is an inherent property of how these models work.

Mitigation is about architectural defense, not hoping the model gets it right. RAG is the most effective approach: ground responses in retrieved source documents so the model synthesizes rather than recalls. Constrained output formats reduce the surface area for hallucination. Temperature 0 reduces randomness for factual tasks. Asking the model to cite specific sources from the provided context makes claims verifiable. Self-consistency (generating multiple answers and checking agreement) catches cases where the model is uncertain. The key insight is that hallucination mitigation is a system design problem, not a prompt engineering problem.

Key points: inherent to how LLMs work — probable text, not true text, RAG is the strongest mitigation, temperature 0 and constrained output reduce it, self-consistency checks across multiple generations, system-level defenses not just prompt-level.

---

**What are embeddings and how do they enable semantic search?**

Embeddings are dense vector representations of text in a high-dimensional space where semantic similarity maps to geometric proximity. An embedding model takes text and produces a fixed-dimensional vector, typically 256-3072 dimensions. "Dog" and "puppy" will produce nearby vectors; "dog" and "spreadsheet" will not. The distance metric is usually cosine similarity.

This enables semantic search: instead of matching keywords, you embed both the query and the corpus, then find the nearest vectors. "How do I fix a broken pipe" will match documents about plumbing even if those documents never use the word "fix." This is fundamental to RAG — you embed document chunks at ingestion time, embed the query at search time, and retrieve the most semantically similar chunks.

Key points: dense vectors where semantic similarity equals geometric proximity, cosine similarity is the standard distance metric, foundation for RAG and semantic search, much cheaper than LLMs, vectors are model-specific — switching models requires full re-embedding.

---

**What are reasoning models (o1, o3, DeepSeek-R1) and how do they differ?**

Reasoning models are trained to "think" through problems step by step before producing a final answer, using chain-of-thought that happens at inference time. Models like OpenAI's o1/o3 and DeepSeek-R1 are trained with reinforcement learning to allocate more compute at inference by generating longer internal reasoning traces. The key insight is that you can trade inference-time compute for accuracy on hard problems — math, logic, code, and multi-step reasoning.

The practical difference: standard models generate an answer in a single forward pass per token with no structured deliberation. Reasoning models produce an extended "thinking" trace (visible or hidden), exploring the problem, checking their work, and backtracking when they hit contradictions. Tradeoffs: reasoning models are slower, more expensive per query, and overkill for simple tasks. Use them for hard problems where accuracy matters more than latency.

Key points: trade inference-time compute for better accuracy, trained with RL to produce CoT reasoning traces, significantly slower and more expensive per query, best for math, logic, code, and multi-step reasoning, overkill for simple tasks — model routing matters.

---

### Prompt Engineering

**What prompting techniques do you use and when?**

Default toolkit: system prompts to set role and constraints, few-shot examples to calibrate on ambiguous tasks, chain-of-thought for reasoning-heavy problems, structured output (JSON with schema enforcement) for programmatic consumption, delimiters to separate instructions from data, and prompt chaining for complex multi-step tasks.

The choice depends on the task. Classification gets few-shot examples plus structured output. Complex reasoning gets chain-of-thought plus chaining. Extraction tasks get clear delimiters plus JSON output. Start with the simplest approach (zero-shot with a clear instruction) and add complexity only when evals show you need it. The most common mistake is over-engineering prompts before establishing a baseline.

---

**How do you get reliable structured output from LLMs?**

The most reliable approach is provider-enforced schemas — OpenAI's JSON mode with json_schema response format, or Anthropic's tool use for structured output. These constrain the decoding process so the model can only generate valid JSON matching your schema. For open-source models, constrained decoding libraries like Outlines or SGLang enforce grammar-level constraints during generation.

When those are not available, defense in depth: define the schema in the prompt with clear instructions, parse the output with a strict validator (Pydantic is ideal), and if validation fails, retry with the error message included so the model can self-correct. Always validate with a schema even when using provider-enforced JSON, because the structure might be valid JSON but semantically wrong. The reliability spectrum: provider-enforced > constrained decoding > prompt engineering with retry > hoping for the best.

---

**How do you defend against prompt injection?**

Prompt injection is when user-provided content manipulates the model into ignoring its instructions. Defense in depth: use clear delimiters (XML tags or similar) to separate instructions from user data. Leverage instruction hierarchy: system prompts are harder to override than user-level messages. Validate inputs and look for known injection patterns.

On the output side, validate that responses conform to expected formats and content. For high-security applications, use a separate classifier model to detect injection attempts before they reach the main LLM. Most importantly, apply the principle of least privilege: if the model has tool access, limit what tools it can invoke. The fundamental tension is between the model's ability to follow complex instructions (which makes it useful) and its susceptibility to instruction manipulation (which makes it vulnerable).

---

**Explain chain-of-thought prompting and when it helps.**

CoT prompting asks the model to show its reasoning step by step before giving a final answer. The simplest form is just adding "Let's think step by step" to the prompt, but more effective approaches provide structured reasoning templates or few-shot examples of the reasoning process. The effect is dramatic on tasks that require multi-step reasoning: math, logic, code analysis, and complex decision-making.

CoT works because it forces the model to allocate compute to intermediate reasoning rather than jumping directly to an answer. Each generated token effectively becomes a computation step. Tradeoffs: CoT uses more output tokens (higher cost and latency), and it does not help on tasks that are not reasoning-dependent (simple classification, extraction).

---

**How do you systematically optimize prompts?**

Eval-driven development. Before writing a single prompt, define your success criteria and build a test set of at least 20-50 representative (input, expected_output) pairs. Write a simple zero-shot prompt, run it against the test set, and establish a baseline score. Then iterate: change one thing at a time, run the eval, and only keep changes that improve the score.

In practice, the biggest wins come from: clarifying ambiguous instructions, adding few-shot examples that cover edge cases, restructuring the prompt to put the most important instructions first and last, and breaking complex prompts into chains of simpler ones. Track each prompt version with its eval scores. The mistake to avoid is prompt engineering by vibes — changing things and hoping they work without measurement.

---

### RAG

**Walk me through a RAG pipeline architecture.**

Two pipelines: ingestion and query. Ingestion takes your source documents, parses them into text, chunks them into appropriately-sized pieces, embeds each chunk using an embedding model, and stores the vectors plus the original text and metadata in a vector database. This runs offline or on a schedule.

The query pipeline runs in real time: take the user's query, optionally rewrite it for better retrieval (especially in multi-turn conversations), embed it with the same embedding model, run a similarity search against the vector database to get the top-K most relevant chunks, optionally rerank those results with a cross-encoder for better precision, then assemble a prompt with the system instructions, the retrieved context, and the user's question. The LLM generates a response grounded in that context.

Key design decisions: chunk size (too small loses context, too large adds noise), number of chunks to retrieve, whether to use hybrid search, and whether reranking is worth the added latency.

---

**How do you choose a chunking strategy?**

Start with recursive splitting on structural boundaries — paragraphs, then sentences, then characters — with a target of 500-1000 tokens and 10-20% overlap between chunks. This respects document structure while keeping chunks a manageable size. From there tune based on retrieval quality.

Advanced patterns worth knowing: parent-child chunking, where you embed small chunks for precise retrieval but return the surrounding parent section for richer context; and contextual chunking, where you prepend the document title or section header to each chunk before embedding so each chunk is self-contained. The right strategy depends on your documents — API docs chunk differently than legal contracts.

---

**What is hybrid search and why use it?**

Hybrid search combines vector (semantic) search with keyword (BM25/full-text) search, then merges the results. Vector search understands meaning — "automobile" matches "car" — but can miss exact terminology, product names, or error codes where keyword matching excels. BM25 is great for exact matches but misses semantic similarity. Combining them gives you the best of both.

The standard architecture: run both searches in parallel, then merge using Reciprocal Rank Fusion (RRF): `score(doc) = sum(1 / (k + rank_i))` across all search methods, where k is typically 60. Documents that rank highly in both methods get boosted. After fusion, optionally run a cross-encoder reranker for a final precision boost.

---

**When would you use RAG vs fine-tuning vs long context?**

RAG when you need to ground the model in specific, updatable knowledge. Fine-tuning when you need to change the model's behavior, style, or capabilities — not for knowledge injection (RAG is better for knowledge, fine-tuning is better for behavior). Long context (stuffing documents into the prompt) when the dataset is small enough to fit and you need the simplest possible solution.

The anti-pattern is fine-tuning for knowledge injection: trying to teach a model specific facts by fine-tuning. It is unreliable, expensive, and the knowledge goes stale. In practice, these combine: fine-tune a model to be better at your domain's reasoning patterns, then use RAG to give it current information.

---

### Agents and Tool Use

**How does function calling / tool use work?**

You define available tools as schemas — name, description, and parameter definitions in JSON Schema format. The description is critical because the model uses it to decide when to invoke each tool. The model either responds with text or outputs a structured tool call. Your code validates the arguments, executes the tool, and returns the result to the model.

The model never executes anything itself — it only outputs a structured request. Your application is the execution layer and the trust boundary. This is what makes tool use safe: you validate inputs, apply permissions, and control what actually happens. The key to good tool use is high-quality tool descriptions — think of them as prompts that tell the model when and how to use each tool.

---

**Design an agent loop. What are the key considerations?**

Core loop: send messages plus tool definitions to the LLM, check if the response contains tool calls or text. If text, done — return to the user. If tool calls, execute each one, append the results to the message history, and loop back. Cap at a maximum iteration count (10-15 for complex tasks) to prevent infinite loops.

Key considerations: error handling (when a tool fails, return a structured error message so the model can reason about an alternative), parallel vs sequential tool execution, guardrails on which tools can be called (some actions need human approval), context management (long tool results can fill the context window fast), and observability (log every iteration for debugging).

---

**What is the ReAct pattern?**

ReAct (Reasoning + Acting) is an agent pattern where the model explicitly alternates between thinking and acting. Each step: Thought (reason about what to do next and why), Action (call a tool), Observation (process the tool result). This chain continues until the model has enough information to produce a final answer.

The key insight is that explicit reasoning steps improve tool-use accuracy. Without ReAct, the model might jump to a tool call without considering whether it is the right approach. More debuggable because you see the reasoning at every step, but uses more tokens. Most production systems use implicit ReAct through the native tool-use loop.

---

### Fine-Tuning

**When would you fine-tune vs. use RAG vs. prompt engineering?**

Start with prompt engineering — cheapest and fastest to iterate. If that ceiling is not high enough, add RAG for knowledge grounding or fine-tuning for behavioral changes. The decision is not mutually exclusive: fine-tune for behavior, RAG for knowledge, prompt engineering for task-specific instructions.

The anti-pattern is fine-tuning for knowledge injection: trying to teach specific facts by fine-tuning. It is unreliable, expensive, and the knowledge goes stale. Fine-tuning teaches the model how to reason about a domain, not what facts are true about it.

---

**Explain LoRA. Why is it preferred over full fine-tuning?**

LoRA (Low-Rank Adaptation) adds small trainable matrices to the existing model weights rather than modifying all parameters. Instead of updating a weight matrix W directly, you decompose the update into two low-rank matrices A and B such that the update is W + AB. Only A and B are trained; the original weights stay frozen.

Advantages: memory (only store and train a tiny fraction of parameters, often 0.1-1% of total), speed (smaller parameter count means faster training), serving (load the base model once and swap different LoRA adapters for different tasks), storage (each adapter is megabytes, not gigabytes). Quality is competitive with full fine-tuning for most tasks. QLoRA goes further by quantizing the base model to 4-bit precision.

---

**What is DPO and how does it compare to RLHF?**

Both optimize a model to prefer better responses over worse ones based on human preferences. RLHF trains a reward model on human preference data, then uses PPO to fine-tune the LLM to maximize the reward — a multi-stage process with significant engineering complexity.

DPO achieves a similar outcome with a simpler process: directly optimize the language model using the preference data, skipping the separate reward model. Single training stage instead of three, no PPO instability issues. DPO produces comparable results to RLHF for most use cases. RLHF can be more flexible for complex reward signals, but DPO has become the default for most practitioners.

---

### Production and Deployment

**How do you optimize LLM costs in production?**

Model tiering is the highest-leverage optimization. Use the cheapest model that meets your quality bar for each task — this can reduce costs 5-20x without quality degradation if you have good evals to validate.

Beyond model selection: caching (identical prompts at temperature 0 should hit a cache), token optimization (concise system prompts, summarized conversation history, retrieving fewer but more relevant RAG chunks), prompt caching (providers like Anthropic automatically cache repeated prompt prefixes at reduced rates), and output limits (set max_tokens appropriately). Track cost at multiple granularities: per request, per feature, per user. Do the math before building.

---

**Describe your approach to LLM observability.**

Log everything, alert on degradation, trace end-to-end. For every LLM call, log: the full prompt, the full response, the model and parameters used, latency (time to first token and total), token counts (input and output), cost, and any tool calls with their results.

For metrics, track: error rate (API failures, timeouts, malformed responses), latency percentiles (p50, p95, p99 — TTFT and total), cost per request and aggregate, quality scores from automated evals (run on a sample of production traffic). For agent and RAG systems, trace the full execution path with timing at each step. Alert on error rate spikes, latency degradation, cost anomalies, and quality score drops.

---

**How do you handle reliability and failover for LLM APIs?**

LLM APIs are external dependencies that will go down. Retry with exponential backoff on transient errors (429, 500, 503). Implement timeouts. Use circuit breakers: if a provider has failed N times in a window, stop trying and fail fast or switch to a fallback.

For high-availability systems, implement provider fallback chains: primary model, fallback model, emergency fallback (possibly self-hosted). Request queuing smooths load spikes. For critical user-facing features, consider graceful degradation — return cached responses or simpler template-based responses when the LLM is unavailable. Graceful degradation beats complete failure.

---

## 30-Second Answers

### Fundamentals

| Question | Answer |
|---|---|
| How do LLMs work? | Neural networks trained to predict the next token on massive text corpora. They learn statistical patterns and generate text by repeatedly sampling from a probability distribution over the vocabulary. |
| What is a transformer? | Architecture that processes all tokens in parallel using self-attention (every token attends to every other token), replacing the sequential processing of RNNs. |
| What is attention? | Mechanism where each token computes relevance scores (via Q/K dot products) against all other tokens, then uses those weights to aggregate information (Values). Multi-head runs this in parallel with different learned projections. |
| What is tokenization? | Converting text into subword units (tokens) the model processes. Uses BPE or similar algorithms. Matters because pricing, context limits, and many edge cases are per-token. |
| What is the context window? | Maximum tokens (input + output) the model processes in one call. It is the model's working memory — everything it needs must be in the prompt or its weights. |
| What is the KV cache? | Cached Key/Value matrices from previous tokens during generation. Avoids recomputing attention over the full sequence for each new token. Explains why first-token latency is higher than subsequent tokens. |
| What are embeddings? | Dense vector representations where semantic similarity maps to geometric proximity. Foundation for semantic search and RAG. |
| What is hallucination? | Model generates plausible but factually incorrect text because it optimizes for probable, not true. Mitigate with RAG, constrained output, citations, and human review. |
| What is temperature? | Scales logits before softmax. 0 = deterministic, higher = more random. Controls creativity vs. consistency. |
| What are reasoning models? | Models like o1/o3 that trade inference-time compute for accuracy by generating extended chain-of-thought reasoning. Best for hard math/logic/code. Overkill for simple tasks. |

### Prompt Engineering

| Question | Answer |
|---|---|
| What is chain-of-thought? | Asking the model to reason step by step before answering. Dramatically helps multi-step reasoning. Uses more tokens. |
| What is few-shot prompting? | Including example (input, output) pairs in the prompt to calibrate the model's behavior. Usually 3-5 diverse examples suffice. |
| How do you get structured output? | Provider-enforced schemas (OpenAI JSON mode, Anthropic tool use) are most reliable. Always validate with Pydantic. Retry with error message as fallback. |
| What is prompt injection? | User-provided content that manipulates model behavior. Defend with delimiters, instruction hierarchy, input validation, output validation, and least privilege. |
| What is prompt chaining? | Breaking a complex task into a pipeline of simpler LLM calls, each with a focused prompt. More reliable and debuggable than one giant prompt. |

### RAG

| Question | Answer |
|---|---|
| What is RAG? | Retrieve relevant documents at query time and include them in the prompt to ground the model's response in specific, current information. |
| What is chunking? | Splitting documents into appropriately-sized pieces for embedding and retrieval. Common strategies: fixed-size, recursive/structural, semantic. |
| What is hybrid search? | Combining vector (semantic) search with keyword (BM25) search, merged via Reciprocal Rank Fusion. Better recall than either alone. |
| What is reranking? | Using a cross-encoder to re-score retrieved chunks for more precise relevance ranking after initial retrieval. |
| What is the "lost in the middle" problem? | Models attend more to the beginning and end of context; information in the middle gets less attention. Place important content at the start or end. |

### Agents

| Question | Answer |
|---|---|
| What is function calling? | Model outputs structured tool call requests; your code executes them and returns results. Model never executes anything itself. |
| What is an agent loop? | Send messages to LLM, if it returns tool calls execute them and loop back, repeat until the model returns text or you hit a max iteration limit. |
| What is ReAct? | Thought-Action-Observation loop: model reasons about what to do, calls a tool, processes the result, and repeats until done. |
| What is MCP? | Model Context Protocol — an open standard for connecting AI applications to tools and data sources. Universal connector instead of one-off integrations. |

### Fine-Tuning

| Question | Answer |
|---|---|
| When to fine-tune? | To change model behavior (style, format, domain reasoning). Not for knowledge injection — use RAG for that. |
| What is LoRA? | Low-Rank Adaptation: trains tiny matrices (0.1-1% of params) added to frozen base weights. Same quality as full fine-tuning at a fraction of the cost. |
| What is DPO? | Direct Preference Optimization: simpler alternative to RLHF that directly optimizes on preference data without a separate reward model. |
| What is SFT? | Supervised Fine-Tuning: training on (instruction, response) pairs to teach instruction-following behavior. |

### Production

| Question | Answer |
|---|---|
| How do you handle streaming? | Server-Sent Events push tokens as generated. Buffer for JSON parsing. Handle partial tool calls, stream failures, and backpressure. |
| How do you optimize cost? | Model tiering (cheapest model per task), caching (response + provider prompt caching), token optimization (concise prompts, summarized history). |
| How do you evaluate? | Offline: curated test set run on every change. Online: LLM-as-judge on production samples, user feedback signals, A/B tests. |
| How do you handle safety? | Defense in depth: input filtering, output validation, least privilege for tools, human-in-the-loop for destructive actions, kill switches, audit logging. |

---

## Key Numbers to Know

### Model Context Windows (early 2026)

| Model | Context Window | Max Output |
|---|---|---|
| GPT-4o | 128K tokens | 16K tokens |
| GPT-4o-mini | 128K tokens | 16K tokens |
| Claude Sonnet 3.5/4 | 200K tokens | 8K tokens |
| Claude Haiku 3.5 | 200K tokens | 8K tokens |
| Claude Opus 4 | 200K tokens | 32K tokens |
| Gemini 1.5 Pro | 1-2M tokens | 8K tokens |
| Gemini Flash | 1M tokens | 8K tokens |
| Llama 3.1 (405B) | 128K tokens | varies |
| DeepSeek-R1 | 128K tokens | 8K tokens |

### Approximate Pricing (per 1M tokens, early 2026)

| Model | Input | Output |
|---|---|---|
| GPT-4o | $2.50 | $10.00 |
| GPT-4o-mini | $0.15 | $0.60 |
| Claude Sonnet 4 | $3.00 | $15.00 |
| Claude Haiku 3.5 | $0.80 | $4.00 |
| Claude Opus 4 | $15.00 | $75.00 |
| Gemini 1.5 Pro | $1.25 | $5.00 |
| Gemini Flash | $0.075 | $0.30 |
| text-embedding-3-small | $0.02 | N/A |
| text-embedding-3-large | $0.13 | N/A |

### Useful Token Conversions

```
1 token ≈ 0.75 English words (or ~4 characters)
1,000 tokens ≈ 750 words ≈ 1.5 pages of text
1M tokens ≈ 750K words ≈ 3,000 pages ≈ 5-6 novels

A typical chat message: 50-200 tokens
A typical RAG prompt: 2,000-5,000 tokens
A 10-page document: ~4,000 tokens
An entire codebase (medium project): 200K-500K tokens
```

### Latency Benchmarks

```
Time to first token (TTFT):
  Cloud API (fast model):     100-300ms
  Cloud API (capable model):  200-800ms
  Reasoning model (o1-class): 2-30 seconds
  Self-hosted (Llama on GPU): 50-200ms

Token generation speed:
  Cloud API:        30-100 tokens/second
  Self-hosted:      10-50 tokens/second (depends on hardware)

Embedding:
  Single text:      10-50ms via API
  Batch of 100:     100-500ms via API

Vector search (pgvector, 100K vectors):  5-20ms
Vector search (Pinecone, 1M vectors):    10-50ms
Cross-encoder reranking (20 passages):   50-200ms
```

---

## Comparison Tables

### RAG vs Fine-Tuning vs Long Context

| Dimension | RAG | Fine-Tuning | Long Context |
|---|---|---|---|
| Best for | Updatable knowledge | Behavior/style changes | Small, static datasets |
| Data freshness | Real-time updates | Stale after training | Current at query time |
| Setup effort | Medium (pipeline) | High (data prep + training) | Low (just stuff it in) |
| Per-query cost | Medium (retrieval + generation) | Low (inference only) | High (long prompts) |
| Upfront cost | Medium (embedding + indexing) | High (training run) | None |
| Accuracy for facts | High (grounded in sources) | Unreliable | High (if in context) |
| Scalability | Scales to millions of docs | Fixed at training time | Limited by context window |
| Traceability | High (can cite sources) | Low (knowledge baked in) | High (in context) |

### Agent Frameworks

| Framework | Strengths | Weaknesses | Best For |
|---|---|---|---|
| LangGraph | Graph-based flows, checkpoints, human-in-the-loop | Complex API, steep learning curve | Complex stateful workflows |
| CrewAI | Simple multi-agent setup, role-based | Less flexible for custom patterns | Multi-agent role-play |
| AutoGen | Research-oriented, conversational agents | Heavy, Microsoft-centric | Experimental multi-agent |
| Custom loop | Full control, no dependencies | More code to write | Production systems |
| Anthropic/OpenAI SDK | Simple, well-documented | Single-provider | Most production use cases |

### Vector Databases

| Database | Managed? | Hybrid Search? | Best For |
|---|---|---|---|
| Pinecone | Yes | Yes | Zero-ops, scale |
| Weaviate | Both | Built-in | Hybrid search |
| Qdrant | Both | Yes | Performance |
| pgvector | Self (Postgres ext.) | Via Postgres FTS | Existing Postgres stack |
| ChromaDB | Self | No | Prototyping |
| FAISS | Self (library) | No | Research, custom |

### Multi-Agent Architecture Patterns

| Pattern | Structure | Strengths | Weaknesses | When To Use |
|---|---|---|---|---|
| Supervisor | One orchestrator delegates to specialist sub-agents | Most debuggable, easy to reason about | Orchestrator is a bottleneck | Tasks that decompose cleanly into independent sub-problems |
| Peer | Agents collaborate as equals | Flexible, adaptable | Harder to debug, risk of loops | Tasks requiring negotiation and iteration |
| Hierarchical | Multiple layers of supervisors and workers | Scales to complex organizations | High operational complexity | Complex tasks that themselves need orchestration |

---

## Red Flags and Anti-Patterns

### Architecture Anti-Patterns

- **Fine-tuning for knowledge injection.** Use RAG. Fine-tuning is for behavior, not facts.
- **One model for everything.** Use the cheapest model that meets your quality bar per task. Haiku for classification, Sonnet for generation.
- **No eval suite.** If you cannot measure quality, you cannot improve it. "It looks good" is not a metric.
- **Sending raw user input directly into prompts without delimiters.** This is an injection vulnerability.
- **Ignoring cost until production.** Do the math early. A $10/query system serving 100K queries/day is $1M/day.
- **Using LangChain in production because you used it for prototyping.** Evaluate whether you need the abstraction. Often you do not.

### Prompt Engineering Anti-Patterns

- **Prompt engineering by vibes.** Change one thing, measure the impact, keep what works. No evals equals guessing.
- **Enormous monolithic prompts.** Break complex tasks into chains of focused prompts.
- **Ignoring the "lost in the middle" effect.** Put important instructions at the start and end, not buried in context.
- **Setting temperature > 0 for deterministic tasks.** Classification, extraction, and structured output should use temperature 0.
- **Not versioning prompts.** Prompts are code. Version them, test them, review them.

### RAG Anti-Patterns

- **Chunks that are too small.** A 100-token chunk has no context. Start at 500-1000 tokens.
- **Chunks that are too large.** A 3000-token chunk dilutes relevance. The embedding represents the whole chunk.
- **Not using metadata filtering.** If you have document types or dates, filter before vector search.
- **Skipping reranking.** A cross-encoder reranker is a cheap, high-impact improvement for retrieval precision.
- **Embedding query not matching embedding document mode.** Some embedding models have separate query/document modes. Use them correctly.

### Agent Anti-Patterns

- **No iteration limit.** An unbounded agent loop will run forever (and drain your budget).
- **Crashing on tool errors.** Return structured errors to the model. It can often recover.
- **Letting the model execute arbitrary code or SQL.** Sandbox everything. Validate tool inputs.
- **Tools with poor descriptions.** The model uses the description to decide when to call a tool. Bad description equals wrong tool usage.
- **Multi-agent when single-agent suffices.** Start with one agent. Split only when complexity demands it.

### Production Anti-Patterns

- **No observability.** If you are not logging prompts, responses, latency, and cost, you cannot debug or optimize.
- **No fallback for API outages.** LLM APIs go down. Have retries, circuit breakers, and fallback models.
- **Streaming as an afterthought.** For user-facing chat, streaming is table stakes. Design for it from the start.
- **Ignoring prompt caching.** Providers offer discounted rates for cached prompt prefixes. Free cost savings for RAG and agent workloads.

---

## Buzzword Decoder

Accurate definitions for overloaded terms:

| Term | What it actually means |
|---|---|
| AGI | Artificial General Intelligence — AI with human-level capability across all domains. Does not exist yet. Not a product feature. |
| Agentic | A system where the LLM autonomously decides what actions to take in a loop, rather than just generating text in a single pass. |
| Alignment | Training models to be helpful, harmless, and honest. Concretely: RLHF, DPO, constitutional AI. |
| Chain-of-thought | Making the model show its reasoning step by step. Improves accuracy on reasoning tasks. |
| Context window | Maximum tokens the model processes per call. Not the same as "memory" — there is no persistence between calls. |
| Distillation | Training a smaller model to mimic a larger model's outputs. A way to get big-model quality at small-model cost. |
| Embedding | Dense vector representation of text for similarity search. Not the same as an LLM response. |
| Fine-tuning | Further training a model on domain-specific data. Changes behavior, not just knowledge. |
| Grounding | Connecting model outputs to verifiable sources (via RAG, tool use, or citations). Reduces hallucination. |
| Guardrails | Safety mechanisms that constrain model behavior: input/output filtering, tool permissions, human oversight. |
| Hallucination | Model generates confident-sounding false information. Not a bug; an inherent property of next-token prediction. |
| Inference | Running a trained model to generate predictions/text. As opposed to training. |
| LoRA | Low-Rank Adaptation. Fine-tuning a tiny fraction of model parameters. Not a model; an adapter applied to a base model. |
| MCP | Model Context Protocol. Standard for connecting AI apps to tools/data. Think USB-C for AI integrations. |
| Multimodal | Model that handles multiple input types: text + images + audio + video. |
| Prompt caching | Provider-side caching of repeated prompt prefixes for reduced cost. Different from response caching. |
| Quantization | Reducing model weight precision (32-bit to 8-bit or 4-bit) to reduce memory and increase speed. Slight quality tradeoff. |
| RAG | Retrieval-Augmented Generation. Retrieve documents, include in prompt, generate grounded response. |
| Reasoning model | Model trained to think step-by-step at inference time (o1, o3, R1). Trades latency for accuracy. |
| RLHF | Reinforcement Learning from Human Feedback. Training models on human preferences. |
| Semantic search | Finding content by meaning rather than keywords. Powered by embeddings and vector similarity. |
| Structured output | Forcing the model to produce valid JSON/schema-conformant output. Provider-enforced is best. |
| Token | The atomic unit the model processes. Subword piece, not a word. Everything (cost, limits, latency) is per-token. |
| Tool use | Same as function calling. Model requests actions; your code executes them. |
| Vector database | Database optimized for storing and querying dense vectors (embeddings). Not a regular database. |
