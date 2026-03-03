# 03 — Advanced LLM Concepts

## Inference Optimization Techniques

Running large models efficiently is as important as building them. These techniques are essential knowledge for production LLM engineering roles.

### Quantization

Quantization reduces the precision of model weights to decrease memory usage and increase throughput. Full-precision weights use 32-bit floats (FP32); most training uses 16-bit (BF16 or FP16); inference can push further.

**Quality vs. memory tradeoff:**

| Precision | Bits per weight | Memory (7B model) | Quality |
|---|---|---|---|
| FP32 | 32 | ~28 GB | Full |
| BF16/FP16 | 16 | ~14 GB | Near-lossless |
| INT8 | 8 | ~7 GB | Minimal degradation |
| INT4 (GPTQ/AWQ) | 4 | ~3.5 GB | Small degradation |
| INT3/INT2 | 2–3 | ~1.7 GB | Noticeable degradation |

**Quantization methods:**

- **GPTQ:** Post-training quantization. Compresses layer-by-layer, minimizing the quantization error per layer. Runs on GPU. Industry standard for GPU inference.
- **AWQ (Activation-aware Weight Quantization):** Preserves weights most important to activations before quantizing. Better quality than GPTQ at the same bit level, especially at 4-bit.
- **GGUF (formerly GGML):** Format for CPU inference. Used by llama.cpp and Ollama. Allows loading a large model in mixed precision (some layers at higher precision). Enables running quantized models on consumer laptops.
- **bitsandbytes:** On-the-fly quantization during model loading for HuggingFace models. Used for QLoRA training. Less optimized for pure inference speed than GPTQ/AWQ.
- **SmoothQuant:** Smooths activation distributions before INT8 quantization, preserving accuracy for very sensitive activations.

**Practical guidance:**

- 4-bit GPTQ/AWQ is now widely used in production for quality-sensitive use cases
- 8-bit (INT8) is largely superseded by 4-bit for most use cases
- GGUF for CPU or memory-constrained deployment (edge devices, developer laptops)
- Always test quantized models against your eval suite before deployment — degradation is task-dependent

### Speculative Decoding

Speculative decoding is a technique to reduce the wall-clock time of autoregressive generation without changing the output distribution.

**Core idea:**

LLM decoding is memory-bandwidth-bound, not compute-bound — the GPU spends most time loading model weights, not performing matrix multiplications. With speculative decoding:

1. A small "draft" model generates k candidate tokens quickly (e.g., k=4)
2. The large "target" model verifies all k tokens in a single parallel forward pass
3. If the target model agrees with the draft's predictions, accept all k tokens
4. At the first disagreement, reject and resample from the target model's distribution

The result is the exact same output distribution as the target model alone, but often 2–3× faster because many tokens are verified in parallel rather than generated sequentially.

**When it helps most:**

| Scenario | Expected Speedup |
|---|---|
| Long outputs with predictable text | 2–3× |
| Code generation (repetitive patterns) | 2–4× |
| Short outputs (<50 tokens) | Minimal |
| Creative writing (high entropy output) | Minimal |
| Grammar/formatting completions | 3–5× |

**Provider support:** OpenAI uses speculative decoding internally. Anthropic mentioned it in their research. vLLM supports it natively for self-hosted setups.

### Continuous Batching

Traditional static batching waits until a batch is full before processing. This causes GPU underutilization when requests arrive at uneven rates and wastes time when some requests finish early.

**Continuous batching** (also called "in-flight batching"):

```
Static batching:
  Batch arrives → process entire batch → wait for all to finish → next batch
  GPU sits idle when some requests finish early

Continuous batching:
  As soon as one request in the batch finishes, insert the next waiting request
  GPU stays maximally utilized at all times
```

Continuous batching is now the standard for production inference servers (vLLM, TGI). It improves throughput by 4–8× over static batching at realistic production traffic patterns.

### PagedAttention

KV cache memory allocation is a critical constraint for serving multiple concurrent requests. Without careful management:

- The KV cache must be pre-allocated at maximum sequence length for every request
- Memory waste is massive when requests are shorter than the maximum
- Fragmentation accumulates as requests of different lengths complete

**PagedAttention** (from the vLLM paper) applies virtual memory paging concepts to KV cache:

- KV cache is allocated in fixed-size "blocks" (pages) rather than as one contiguous chunk
- Blocks are allocated incrementally as the sequence grows
- Completed sequences release their blocks for reuse
- Block mapping table tracks which blocks belong to which sequence

Result: memory waste from pre-allocation nearly eliminated, enabling more concurrent requests on the same GPU memory.

### Prefix Caching (Provider-Side)

Both Anthropic and OpenAI offer prefix caching for repeated prompt prefixes:

**How it works:**
- The provider computes and caches the KV cache for commonly repeated prompt prefixes
- On subsequent requests with the same prefix, the cached KV is reused, skipping prefill

**Savings:**
- Anthropic: 90% cost reduction on cached tokens; requires 1,024+ token prefix (Sonnet), 2,048+ (Opus)
- OpenAI: 50% cost reduction on cached tokens; automatic for prompts longer than 1,024 tokens

**Design for caching:**
- Put static content first: system prompt, tool definitions, few-shot examples
- Put dynamic content last: user message, specific document
- Maximize the shared prefix length across requests

```
[System prompt - 2,000 tokens][Tool definitions - 1,500 tokens][Retrieved context - 3,000 tokens][User message - 200 tokens]
 ←──────────────── static prefix (cacheable) ─────────────────→ ←─ dynamic ─→
```

---

## Emergent Abilities

Emergent abilities are capabilities that appear suddenly as model scale increases — they are absent in smaller models and appear seemingly discontinuously at certain parameter or compute thresholds.

### In-Context Learning

At scale, models learn to learn from examples provided in the prompt, without any weight updates. Show a model three (input, output) pairs for a novel task, and it can generalize to new inputs for that task. This capability emerges at around 7B+ parameters and becomes much stronger at 70B+.

In-context learning is the basis for few-shot prompting. The model is not "training" on the examples — it is pattern-matching against its pre-training distribution to identify what transformation the examples demonstrate, then applying it.

### Chain-of-Thought Reasoning

At sufficient scale (~100B parameters), models can improve their accuracy on multi-step reasoning tasks by generating intermediate reasoning steps before answering. This emergence is what makes "Let's think step by step" work — smaller models do not reliably benefit from this instruction.

### Calibration

Larger models tend to be better calibrated — when they express uncertainty, they are more accurately uncertain. Smaller models are more prone to confident hallucination. This has important implications for production reliability: large models with well-designed confidence prompts can produce more reliable outputs than small models.

---

## Reasoning Models

Reasoning models (OpenAI o1/o3, DeepSeek-R1, Claude 3.7 Sonnet "extended thinking") represent a distinct approach to improving accuracy on hard problems.

### How They Work

Standard models generate an answer in a single autoregressive pass. Reasoning models are trained with RL to generate an extended internal reasoning trace before producing a final answer — essentially teaching the model to "think" before speaking.

The reasoning trace (called "thinking" in some implementations) may be hidden from the user or visible as a scratchpad. The key insight: **inference-time compute can substitute for model size**. A smaller model thinking for many tokens can outperform a larger model answering directly.

### Training Approach

Reasoning models are typically trained with process-level RL:
1. Generate many candidate reasoning traces + answers for problems with verifiable answers (math, code)
2. Use the final answer to determine reward (correct answer = positive reward)
3. The model learns reasoning patterns that reliably lead to correct answers

DeepSeek-R1 used pure RL starting from a base model, which produced emergent chain-of-thought behavior including self-correction and backtracking. This shows that the reasoning behavior itself emerges from reward optimization, not from supervised examples.

### Practical Trade-offs

| Dimension | Standard Model | Reasoning Model |
|---|---|---|
| Latency | 1–5 seconds | 10–60 seconds (o3 can be much longer) |
| Cost | Baseline | 5–20× baseline per query |
| Best for | Most tasks | Hard math, logic, code, multi-step analysis |
| Configurable effort | No | Yes (o3 effort levels) |
| Transparency | Full output | Thinking may be hidden |

**When to use reasoning models:**
- Complex mathematical proofs or multi-step calculations
- Difficult algorithmic problems and competitive coding
- Complex multi-step reasoning chains (planning, debugging)
- Any task where accuracy matters much more than latency or cost

**When NOT to use:**
- Classification, extraction, simple Q&A
- User-facing applications where latency is critical
- Any task a standard model handles correctly already

**Model routing design:** Classify incoming requests by estimated complexity. Route simple requests to fast standard models, complex requests to reasoning models. A classifier adding 50ms is worthwhile if it routes 80% of traffic to the cheaper model.

---

## Multi-Modal Models

Modern frontier models handle multiple input modalities — text, images, audio, and video — in a unified architecture.

### Vision Integration

**Image tokenization approaches:**

1. **Patch-based:** Image is divided into fixed-size patches (e.g., 14×14 pixels). Each patch is embedded into a vector and treated as a "visual token" by the transformer. Used by ViT (Vision Transformer) and many CLIP-based models.

2. **Variable-resolution:** Process images at their native resolution by dynamically splitting into patches. Avoids quality loss from downsampling for detailed images. Used by recent frontier models.

**Integration strategies:**

- **Early fusion:** Visual tokens are concatenated with text tokens before the transformer. The model attends across both modalities at every layer. Best performance.
- **Late fusion:** Text and image are processed separately; features are combined before the final answer. Faster but less expressive.
- **Cross-attention:** A separate visual encoder; the text model attends to visual features at each layer via cross-attention. LLaVA and similar models.

**Practical implications:**
- Images consume many tokens: a 1024×1024 image may use 1,000–4,000 tokens
- This significantly impacts context window usage and cost
- Image quality (resolution, lighting, text legibility) directly impacts model performance
- Models vary in "tokens per image" — this affects cost significantly

### Audio and Video

**Audio:** Most capable models use continuous speech representation. Audio is processed via a speech encoder (Whisper-style), then fed to the language model. Enables voice interfaces and audio transcription/analysis.

**Video:** Video is typically handled as a sequence of frames, each processed as an image. Temporal relationships are captured by the sequence of frame tokens. Practical constraint: video is very token-heavy — a 1-minute video at 1 frame/second is 60 image-equivalents of context.

---

## Model Distillation

Distillation compresses the knowledge of a large "teacher" model into a smaller "student" model. The goal is to approach the teacher's quality at the student's cost.

### Why It Works

Large models learn complex, smooth decision boundaries in the probability space over their output vocabulary. The teacher's full probability distribution over possible outputs is more informative than just the correct label — it captures uncertainty, similarity between classes, and reasoning patterns.

### Distillation Approaches

**Output distillation (knowledge distillation):**
The student is trained to match the teacher's complete output probability distribution, not just the most likely token:
```
Loss = α * CrossEntropy(student_probs, ground_truth) + (1-α) * KL(student_probs, teacher_probs)
```
The KL term pushes the student to learn the teacher's full distribution — the "dark knowledge" in the soft labels.

**Logit distillation:** A variant of output distillation that operates on logits before softmax, with temperature scaling to soften the teacher's distribution:
```
Teacher soft labels = softmax(teacher_logits / T)   # T > 1 softens the distribution
Student is trained to match these soft labels
```

**Feature distillation:** The student also learns to match the teacher's intermediate representations (hidden states, attention patterns) at specific layers. More computationally expensive to set up but can produce better results.

### Practical Considerations

- Distilled models work well within the teacher's distribution but may not generalize as broadly
- Best for narrow, well-defined tasks where the teacher's behavior is reliable
- Notable examples: GPT-4o-mini (distilled from GPT-4), Phi series (distilled with synthetic data from frontier models), Claude Haiku (efficient model with knowledge from larger Claude models)
- **ToS consideration:** Many frontier model providers prohibit using their models' outputs to train competing models. Always check before attempting distillation.

---

## Glossary: Key Terminology

Essential vocabulary for technical LLM interviews:

### Architecture Terms

| Term | Definition |
|---|---|
| **Autoregressive** | Generates tokens one at a time, each conditioned on all previous tokens |
| **Causal attention** | Each token can only attend to tokens at its position and earlier (no peeking at future) |
| **d_model** | Hidden dimension of the transformer (embedding size); typically 512–8192 |
| **d_ff** | Feed-forward hidden dimension; typically 4× d_model |
| **num_heads** | Number of parallel attention heads; typically 8–128 |
| **num_layers** | Number of transformer blocks stacked; typically 12–96 |
| **GQA** | Grouped Query Attention — shares K/V across groups of Q heads to reduce KV cache |
| **MQA** | Multi-Query Attention — single K/V shared across all Q heads |
| **SwiGLU** | Gated activation function used in modern FFNs (Llama, PaLM) |
| **RMSNorm** | Root Mean Square Layer Normalization — simpler and faster than LayerNorm |

### Tokenization Terms

| Term | Definition |
|---|---|
| **BPE** | Byte Pair Encoding — subword tokenization that merges frequent character pairs |
| **SentencePiece** | Tokenization library using BPE or unigram model; used by Llama, T5 |
| **tiktoken** | OpenAI's tokenizer library; used by GPT-3.5/4 |
| **Vocabulary size** | Number of distinct tokens the model recognizes; typically 32K–100K |
| **Special tokens** | Reserved tokens like `<eos>`, `<pad>`, `<s>`; used for conversation formatting |

### Training Terms

| Term | Definition |
|---|---|
| **Pre-training** | Initial training on massive text corpora with next-token prediction objective |
| **SFT** | Supervised Fine-Tuning — training on instruction/response pairs |
| **RLHF** | Reinforcement Learning from Human Feedback — alignment via human preferences |
| **DPO** | Direct Preference Optimization — single-stage alignment without a reward model |
| **PPO** | Proximal Policy Optimization — RL algorithm used in RLHF |
| **Constitutional AI** | Anthropic's approach — model critiques and revises its own outputs against principles |
| **KL divergence** | Measure of difference between two probability distributions; used in DPO/RLHF |

### Generation Terms

| Term | Definition |
|---|---|
| **Logits** | Raw (un-normalized) output scores before softmax; one per vocabulary token |
| **Greedy decoding** | Always pick the highest-probability token (equivalent to temperature=0) |
| **Beam search** | Keep top-k most likely sequences at each step; rarely used for LLMs in production |
| **Nucleus sampling** | Top-p — sample from the smallest set of tokens with cumulative probability ≥ p |
| **TTFT** | Time To First Token — latency from request to first output token |
| **Prefill** | Processing the input prompt tokens (parallel, fast per token) |
| **Decode** | Generating output tokens one at a time (sequential, slower per token) |

### Embeddings and Retrieval Terms

| Term | Definition |
|---|---|
| **Embedding** | Dense vector representation of text in high-dimensional semantic space |
| **Cosine similarity** | Angle-based similarity measure; range −1 to 1; standard for comparing embeddings |
| **Matryoshka embeddings** | Models trained so prefix sub-vectors are also meaningful; allows dimension truncation |
| **MTEB** | Massive Text Embedding Benchmark; standard evaluation for embedding models |
| **Normalization** | Scaling a vector to unit length; makes cosine similarity = dot product |

### Inference/Production Terms

| Term | Definition |
|---|---|
| **Quantization** | Reducing weight precision (FP32→INT8→INT4) to reduce memory and increase speed |
| **Speculative decoding** | Draft model generates candidate tokens; target model verifies in parallel |
| **Continuous batching** | Dynamic batch management that maximizes GPU utilization as requests arrive/complete |
| **PagedAttention** | Virtual memory approach to KV cache allocation; enables more concurrent requests |
| **Prefix caching** | Provider-side caching of repeated prompt KV caches; reduces cost for stable prefixes |
| **Flash Attention** | Memory-efficient attention computation using tiling to avoid materializing the full n×n matrix |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Multi-Model Cost Estimator** -- The prompt caching discount logic (cached_input_discount field) directly practices the "Prefix Caching (Provider-Side)" concept: Anthropic's 90% discount vs OpenAI's 50% discount on cached tokens. Understanding when and how caching reduces cost is central to this exercise.

- **Exercise 2: Model Router** -- The reasoning model routing pattern from "Reasoning Models" -> "Model routing design" informs how the router should classify complex vs. simple tasks. The router's budget-aware downgrade logic practices the cost-quality tradeoff described in "Practical Trade-offs" (standard models for most tasks, reasoning models for hard problems).

- **Exercise 3: Context Window Truncation Strategies** -- The `split_into_chunks()` function practices the chunking concept needed for RAG pipelines, which relates to the retrieval patterns discussed throughout this file. The overlap parameter addresses the "lost in the middle" problem mentioned in the Glossary.

- **Exercise 4: Embedding Similarity Search** -- The Glossary's "Embeddings and Retrieval Terms" defines all the concepts implemented in this exercise: cosine similarity, embedding normalization, and Matryoshka embeddings. The `semantic_search()` function builds the core retrieval operation, and `diversity_rerank()` (MMR) addresses the quality concern of returning diverse, relevant results.

See also `examples.py` sections 5 (Embedding Similarity), 6 (Streaming Response Handler for TTFT concepts), and 7 (Token Budget Planner) for related runnable examples.

---

## Interview Q&A: Advanced Concepts

**Q: What is speculative decoding and when would you use it?**

Speculative decoding uses a small draft model to generate k candidate tokens, which the large target model then verifies in a single parallel pass. Because verification is much faster than sequential generation, you get 2–4× speedup when the draft model's predictions are mostly correct. The output distribution is mathematically identical to running the target model alone. It helps most for predictable text (code, grammar completions) and hurts least for creative writing. At self-hosted deployments where you control the inference stack (via vLLM), it's worth enabling for latency-sensitive workloads.

**Q: How does PagedAttention differ from standard KV cache management?**

Standard KV cache pre-allocates a contiguous block of GPU memory for the maximum sequence length, wasting memory when requests are shorter. PagedAttention maps logical blocks of KV cache to physical GPU memory pages, allocating only as needed and reclaiming memory when requests complete. This reduces memory waste dramatically, allows more concurrent requests on the same hardware, and enables memory sharing between concurrent requests with the same prefix (for prompt caching). It's the primary innovation in vLLM that made it the leading inference server.

**Q: What are the tradeoffs of using reasoning models in production?**

Reasoning models like o1/o3 and DeepSeek-R1 produce dramatically better results on hard reasoning tasks but cost 5–20× more and take 10–60 seconds instead of 1–5 seconds. The right architecture treats them as specialist models accessed via model routing: a fast classifier routes simple requests to standard models and complex requests to reasoning models. For tasks like customer support, simple Q&A, or classification, reasoning models are wasteful. For complex code generation, multi-step math, or deep analysis, they may be the only models that reliably succeed.

**Q: Explain why LLMs hallucinate and what can be done about it architecturally.**

LLMs optimize for generating probable text, not true text. The model learns statistical patterns in the training distribution but has no internal mechanism to verify factual claims. When a model "knows" information about a topic, it's actually a learned correlation between tokens that appeared in training — this correlation can fire inappropriately on novel inputs. Architecturally: RAG grounds responses in retrieved source documents, making hallucination on grounded claims easier to detect. Constrained output formats reduce the surface area. Temperature 0 reduces randomness but doesn't eliminate hallucination on ambiguous inputs. Self-consistency (sampling multiple answers and checking agreement) catches cases where the model is uncertain. For critical applications, output validation (checking claims against sources) is the most reliable defense.

**Q: What is model distillation and when is it appropriate?**

Distillation trains a small student model to match a large teacher model's output distribution, capturing the teacher's "soft" probabilistic knowledge rather than just the hard labels. It's appropriate when: you need the quality of a large model but the inference cost of a small one, you have a well-defined narrow task where a teacher model performs reliably, and you have the compute for a training run. Not appropriate when: the task is too broad (the student won't generalize), the teacher model's outputs are copyrighted or prohibited for training use by ToS, or prompt engineering can achieve the quality you need without the training overhead.
