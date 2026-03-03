# 01 — Transformer Architecture Fundamentals

## What is an LLM?

A large language model is a neural network trained to predict the next token in a sequence, given all tokens that came before. By training on massive amounts of text, models learn statistical patterns in language that generalize to understanding, reasoning, and generation.

Key fact: LLMs do not "know" things the way a database does. They learn weighted representations of patterns. Every output is a probability distribution over the vocabulary — the model samples from that distribution to generate text.

---

## Transformer Architecture

The transformer architecture (Vaswani et al., "Attention Is All You Need", 2017) is the backbone of every major LLM. Understanding it in depth is essential for any LLM engineering interview.

### High-Level Flow

```
Input Text
    │
    ▼
Tokenizer → Token IDs
    │
    ▼
Token Embedding (lookup table: token ID → vector)
    │
    ▼
Positional Encoding (add position information)
    │
    ▼
┌─────────────────────────────┐
│   Transformer Block × N     │  (N = 12 to 96+, depending on model size)
│                             │
│   ┌─────────────────────┐   │
│   │  Multi-Head         │   │
│   │  Self-Attention      │   │
│   └──────────┬──────────┘   │
│              │               │
│   Add & Norm (residual)      │
│              │               │
│   ┌──────────▼──────────┐   │
│   │  Feed-Forward        │   │
│   │  Network (MLP)       │   │
│   └──────────┬──────────┘   │
│              │               │
│   Add & Norm (residual)      │
└─────────────┬───────────────┘
              │
              ▼
         LM Head (linear layer → vocabulary logits)
              │
              ▼
         Softmax → Probability distribution
              │
              ▼
         Sample next token
```

### Self-Attention Mechanism

Self-attention lets every token in the sequence compute relevance scores against every other token, then use those scores to aggregate information.

**Scaled Dot-Product Attention:**

Each token generates three vectors from the same input embedding via learned linear projections:
- **Query (Q):** "What information am I looking for?"
- **Key (K):** "What information do I represent?"
- **Value (V):** "What information do I carry?"

The attention computation:

```
Attention(Q, K, V) = softmax(QK^T / sqrt(d_k)) * V
```

Step by step:
1. Compute dot products of Q against all K vectors → raw attention scores
2. Divide by sqrt(d_k) to prevent large values that cause softmax saturation and gradient issues
3. Apply softmax → probability distribution (each row sums to 1)
4. Weighted sum of V vectors using those probabilities

The result: each token's output is a weighted combination of all other tokens' Value vectors, where the weights reflect learned relevance.

**Attention is O(n²) in sequence length.** For a 1,000-token sequence, there are 1,000,000 Q-K pairs to compute. This is why context windows have practical limits and why extending them is expensive.

### Multi-Head Attention

Instead of one attention computation, multi-head attention runs multiple attention heads in parallel, each with independent Q, K, V projection matrices:

```python
# Conceptual multi-head attention
head_outputs = []
for i in range(num_heads):
    Q_i = input @ W_Q[i]   # project to head dimension
    K_i = input @ W_K[i]
    V_i = input @ W_V[i]
    head_outputs.append(attention(Q_i, K_i, V_i))

# Concatenate all heads, project back to model dimension
output = concat(head_outputs) @ W_O
```

Each head can learn to attend to different relationship types — one might track subject-verb agreement, another long-range coreference, another local syntactic dependencies. GPT-class models use 32 to 128 heads depending on model size.

**Multi-Query Attention (MQA) and Grouped Query Attention (GQA):** To reduce KV cache memory pressure, modern models (Llama 3, Mistral) share K and V projections across multiple Q heads. GQA groups Q heads and gives each group one K/V pair. MQA shares a single K/V across all Q heads. Both reduce inference memory with minimal quality loss.

### Feed-Forward Network (FFN)

Each transformer block also contains a feed-forward sub-layer applied identically to each token position:

```
FFN(x) = activation(x @ W1 + b1) @ W2 + b2
```

Typical architecture: two linear layers with a nonlinear activation (ReLU, GELU, or SwiGLU) in between. The hidden dimension is usually 4× the model dimension (e.g., d_model=4096 → FFN hidden=16384). The FFN is where much of the model's factual knowledge is believed to be stored.

### Layer Normalization and Residual Connections

Every sub-layer (attention and FFN) has a residual (skip) connection and layer normalization:

```
x = x + Attention(LayerNorm(x))   # Pre-norm formulation (used by modern models)
x = x + FFN(LayerNorm(x))
```

Residual connections allow gradients to flow directly through the network during training, enabling very deep networks (32-96 layers). Pre-norm (normalizing before the sub-layer) is more stable than post-norm for large models.

---

## Tokenization

### What is a Token?

A token is the atomic unit the model processes. It is not a word — it is a subword piece learned from the training corpus. The word "tokenization" might be split as ["token", "ization"]. The word "the" is likely a single token. A rare proper noun might be split into many character pieces.

**Key numbers:**
- 1 token ≈ 0.75 English words (or ~4 characters)
- 1 word ≈ 1.33 tokens
- 1 page ≈ 300 words ≈ 400 tokens
- 1M tokens ≈ 750K words ≈ 2,500 pages

### Byte Pair Encoding (BPE)

The dominant tokenization algorithm, used by GPT-4 (via tiktoken), Llama, and others:

1. Start with a character-level vocabulary
2. Count the most frequent adjacent character pair in the corpus
3. Merge that pair into a new token, add it to the vocabulary
4. Repeat until the vocabulary reaches the target size (typically 32K–100K tokens)

The result: common subwords and words are single tokens; rare words are split into pieces.

**SentencePiece:** A similar approach used by Llama 2, T5, and many others. Works at the byte level, so it handles any Unicode character without an "unknown" token.

### Practical Implications of Tokenization

1. **Cost:** You pay per token (input + output), not per word. Non-English text and code often tokenize inefficiently (more tokens per semantic unit).
2. **Context limits:** Window size is measured in tokens. "128K context" = 128,000 tokens, not words.
3. **Arithmetic failures:** Numbers tokenize unpredictably ("123456" may become ["12", "34", "56"]). This is one reason LLMs struggle with arithmetic.
4. **Model-specific vocabularies:** Tokens from GPT-4's tokenizer are incompatible with Claude's. Always use the correct tokenizer for your model.
5. **Special tokens:** Every model has special tokens like `<|endoftext|>`, `<|start_header_id|>`, `<s>` used for conversation formatting. Exposing these to users can cause unexpected behavior.

---

## Positional Encoding

Transformers have no inherent notion of order — the attention mechanism treats all positions symmetrically. Positional encodings are added to embeddings to inject sequence order information.

### Sinusoidal Positional Encoding (Original)

The original transformer used fixed sine/cosine functions of varying frequencies:

```
PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
```

Each dimension oscillates at a different frequency. The model can learn to attend to positional offsets, but generalization to unseen sequence lengths is limited.

### Learned Positional Embeddings

GPT-2 and BERT use learned positional embeddings — a lookup table of trainable vectors, one per position. Simple and effective up to the trained maximum length, but cannot generalize beyond it.

### Rotary Position Embedding (RoPE)

Used by Llama, Mistral, and most modern open-source models. Instead of adding positional information to embeddings, RoPE rotates the Q and K vectors by an amount proportional to their position before computing attention:

```
Attention score between positions i and j depends only on (i - j), not absolute positions
```

This encodes relative position directly in the attention computation. Key advantages: better length generalization than learned embeddings, and relative-position awareness is inherent.

### ALiBi (Attention with Linear Biases)

Used by MPT and some Falcon models. Adds a linear position bias to attention scores:

```
Attention score = (Q·K^T / sqrt(d_k)) - (m * |i - j|)
```

Where m is a head-specific slope. Tokens farther apart get penalized, encoding recency bias. Generalizes extremely well to sequences longer than seen during training.

### Comparison

| Encoding | Generalization | Memory | Models |
|---|---|---|---|
| Sinusoidal | Limited | None | Original Transformer |
| Learned | None beyond max_len | d_model × max_len | GPT-2, BERT |
| RoPE | Good | None | Llama, Mistral, GPT-NeoX |
| ALiBi | Excellent | None | MPT, Falcon |
| YaRN/LongRoPE | Excellent | None | Extended Llama variants |

---

## Context Windows and Memory

### What the Context Window Is

The context window is the maximum number of tokens the model can process in a single forward pass — input tokens plus output tokens combined. It is the model's working memory. Everything the model needs to know for a given response must be either in the context window or in its trained weights.

**Context windows by era:**
- GPT-2 (2019): 1,024 tokens
- GPT-3 (2020): 4,096 tokens
- GPT-4 (2023): 8K–32K tokens
- Claude 2 (2023): 100K tokens
- GPT-4 Turbo (2023): 128K tokens
- Gemini 1.5 Pro (2024): 1M–2M tokens
- Claude 3.5/4 (2024–2025): 200K tokens

### The KV Cache

The KV cache is one of the most important concepts for production LLM engineering.

**Why it exists:** Transformer generation is autoregressive — the model generates one token at a time, and each new token requires attending to all previous tokens. Without the KV cache, generating a 1,000-token response would require recomputing attention over the entire sequence 1,000 times.

**How it works:**

During generation, the Key and Value matrices computed for each token in each attention head are cached in GPU memory. When the model generates the next token, it only computes Q, K, V for the new token and reuses all cached K, V vectors from previous positions:

```
Without KV cache: each new token requires O(n²) attention computation
With KV cache:    each new token requires O(n) — multiply new Q against all cached K
```

**Prefill vs. decode phases:**

```
Prefill:  Process the entire prompt at once (parallel).
          KV cache is built for all prompt tokens.
          Fast per token (processes many tokens simultaneously).

Decode:   Generate each output token one at a time.
          Extend KV cache by one token per step.
          Slower per token, but only one forward pass per token.
```

This is why **time to first token (TTFT)** increases with prompt length — longer prompts mean more prefill work.

**Memory cost:** The KV cache grows linearly with sequence length and is proportional to model size:

```
KV cache per token ≈ 2 * num_layers * num_kv_heads * head_dim * 2 bytes (FP16)

Example (Llama 3.1 70B, FP16):
  80 layers × 8 KV heads × 128 head_dim × 2 (K+V) × 2 bytes = 327 KB per token
  8K context = ~2.5 GB KV cache per request
  32 concurrent requests at 8K = ~80 GB KV cache alone
```

GQA/MQA dramatically reduce this — instead of 64 KV heads, you might have 8, cutting memory 8×.

**Prefix caching:** Anthropic and OpenAI both offer prompt caching — if the same prompt prefix is sent repeatedly, the provider can reuse the KV cache from the first computation. This is significant for RAG and agent workloads where the system prompt and tool definitions repeat across many calls.

---

## Attention Variants and Efficiency

### Flash Attention

Standard attention requires materializing the full n×n attention matrix in GPU HBM (high-bandwidth memory). For long sequences, this becomes a memory bottleneck. Flash Attention (Dao et al., 2022) reorders computation to keep the attention matrix in fast SRAM instead:

- No quadratic memory footprint from the attention matrix
- Same mathematical result as standard attention
- 2–4× faster in practice, especially for long sequences
- Now essentially universal in production model training and inference

### Sparse Attention Patterns

Some architectures attend only to a subset of positions to reduce the O(n²) cost:

- **Sliding window attention (Mistral):** Each token attends only to the last W tokens, plus a few global tokens
- **Longformer:** Sliding window + global attention on special tokens
- **BigBird:** Sliding window + random attention + global tokens

Tradeoff: lower computation cost but harder to model very long-range dependencies.

---

## Key Parameters for Generation

Understanding generation parameters is essential for building reliable LLM applications.

### Temperature

Temperature scales the logits before softmax. It controls randomness in token selection.

```python
probs = softmax(logits / temperature)
```

| Temperature | Behavior | Use Case |
|---|---|---|
| 0 | Deterministic (always picks highest probability token) | Classification, extraction, structured output, code |
| 0.3 | Low randomness, stays on-topic | Summarization, factual Q&A |
| 0.7 | Moderate creativity (good default) | General generation, chat |
| 1.0 | Sampling from the raw model distribution | Creative writing |
| >1.0 | Amplifies low-probability tokens, incoherent at extremes | Rarely useful in production |

**Note:** Even temperature 0 is not perfectly deterministic on all providers due to floating-point nondeterminism in GPU operations.

### Top-p (Nucleus Sampling)

Top-p dynamically restricts the candidate pool to the smallest set of tokens whose cumulative probability exceeds p:

- At top_p=0.9, consider only the tokens comprising the top 90% of probability mass
- When the model is confident, few tokens exceed 90%, so the pool is small
- When the model is uncertain, many tokens are needed to reach 90%, so the pool is large

**Recommendation:** Set temperature for the task, leave top_p at 1.0 unless you have a specific reason to constrain it. Setting both aggressively compounds effects unpredictably.

### Top-k

Restricts sampling to the k highest-probability tokens at each step, regardless of their cumulative probability. Less commonly used than top-p in modern LLM APIs.

### Frequency and Presence Penalties (OpenAI)

- **Frequency penalty (−2 to 2):** Reduces probability of tokens proportional to how often they have appeared in the output so far. Reduces repetition.
- **Presence penalty (−2 to 2):** Reduces probability of any token that has appeared at all (binary penalty). Encourages topic diversity.

### Max Tokens

The maximum number of tokens to generate. Set this appropriately — if you set it too high, the model may generate unnecessary verbosity. If too low, responses get truncated. For structured output, set it high enough to guarantee the full JSON fits.

### Stop Sequences

Specific strings that cause generation to halt. Useful for:
- Stopping after a complete JSON object: `["}"]`
- Stopping at natural conversation boundaries
- Enforcing output format (e.g., stop after the answer line)

---

## Embeddings

Embeddings are dense vector representations of text where semantic similarity maps to geometric proximity in a high-dimensional space.

**Embedding model vs. generation model:**
- A generation model (GPT-4, Claude) produces text output from text input
- An embedding model (text-embedding-3-small, Cohere embed-v3) produces a fixed-size vector from text input
- Embedding models are much cheaper and faster — they do not autoregress

**Common embedding models:**

| Model | Dimensions | MTEB Score | Cost (per 1M tokens) |
|---|---|---|---|
| text-embedding-3-small | 1,536 | 62.3 | $0.02 |
| text-embedding-3-large | 3,072 | 64.6 | $0.13 |
| Cohere embed-v3-english | 1,024 | 64.5 | $0.10 |
| voyage-3 | 1,024 | ~66+ | $0.06 |
| bge-large-en-v1.5 | 1,024 | 63.8 | Free (self-hosted) |

**Similarity metrics:**

Cosine similarity is standard:
```
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)
```
Range: −1 to 1. For normalized vectors, cosine similarity and dot product are equivalent. Most embedding models produce normalized vectors by default.

**Key constraint:** Embeddings from different models are incompatible. If you embed documents with text-embedding-3-small and queries with Cohere embed-v3, similarity scores are meaningless. Changing your embedding model requires re-embedding your entire corpus.

---

## Interview Q&A: Transformer Architecture

**Q: How do transformers differ from RNNs?**

RNNs process tokens sequentially — each token depends on the hidden state from the previous step. This creates two problems: parallelism (you cannot train efficiently on modern hardware) and long-range dependencies (information from early tokens must survive through every intermediate step). Transformers process all tokens simultaneously and every token directly attends to every other token, solving both problems. The cost is O(n²) attention computation instead of O(n), which is why context window scaling is expensive.

**Q: What is the purpose of the sqrt(d_k) scaling in attention?**

When the embedding dimension is large, the dot products Q·K can grow large in magnitude. Large values push the softmax into saturation, where the distribution becomes near-one-hot and gradients become very small. Dividing by sqrt(d_k) keeps the dot product magnitudes in a stable range regardless of the model's hidden dimension.

**Q: Why does temperature 0 not always give the same output?**

Temperature 0 approximates greedy decoding by making the highest-probability token overwhelmingly likely. In theory this is deterministic, but GPU floating-point operations are nondeterministic (operations may be reordered for parallelism), and some providers add small amounts of randomness for load balancing. In practice, temperature 0 gives consistent outputs but is not guaranteed identical across calls.

**Q: What is the attention mask and why does it matter?**

The attention mask prevents tokens from attending to positions they should not see. In decoder-only models (GPT, Llama), a causal mask prevents each position from attending to future positions — this is what enforces the autoregressive property. When processing a batch of sequences of different lengths, a padding mask prevents attending to padding tokens. Getting attention masks wrong is a common bug in custom fine-tuning pipelines.

**Q: What happens when context length approaches the window limit?**

The model has no way to signal that it is approaching its limit — it simply truncates. On the input side, most APIs apply truncation from the left (oldest history gets dropped first), which can silently remove critical context. Always monitor token usage in production and implement explicit context management strategies before hitting the limit.

**Q: How does positional information affect performance at long contexts?**

Models degrade in quality at very long contexts, particularly with information in the middle of the context (the "lost in the middle" problem). Attention is not uniform — models pay more attention to content at the beginning and end of the context window. For RAG systems, place the most important retrieved content at the beginning or end of the context, not buried in the middle.
