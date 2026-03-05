# Module 00: AI & ML Foundations for Software Engineers

Everything you need to know before this course makes sense. You build software — this module gives you the foundational AI/ML concepts so the transformer architectures, training pipelines, and embedding spaces in Module 01 don't feel like magic.

No math proofs. No Jupyter notebooks. Just the mental models and vocabulary you need.

---

## 1. What Machine Learning Actually Is

### The Core Idea

Traditional programming: you write rules, the computer follows them.

```
Rules + Data → Output
```

Machine learning: you provide examples, the computer learns the rules.

```
Data + Expected Output → Rules (model)
```

A model is a function with millions (or billions) of adjustable parameters. Training is the process of adjusting those parameters until the function produces the right outputs for the training data, then generalizes to new data it hasn't seen.

### Types of ML (What Matters for LLMs)

| Type | What It Does | LLM Relevance |
|------|-------------|----------------|
| **Supervised Learning** | Learns from labeled examples (input → expected output) | Fine-tuning, RLHF reward models |
| **Unsupervised Learning** | Finds patterns in unlabeled data | Pre-training (next token prediction) |
| **Reinforcement Learning** | Learns by trial and reward | RLHF, DPO (alignment) |
| **Self-Supervised Learning** | Creates its own labels from the data structure | How LLMs are actually pre-trained |

LLM pre-training is self-supervised: the model reads text and predicts the next token. The "label" is just the next word in the sequence — no human annotation needed. This is why you can train on trillions of tokens from the internet.

---

## 2. Neural Networks in 5 Minutes

### The Neuron (Perceptron)

A neuron takes inputs, multiplies each by a weight, sums them, adds a bias, and passes through an activation function.

```
inputs: [x1, x2, x3]
weights: [w1, w2, w3]
bias: b

output = activation(x1*w1 + x2*w2 + x3*w3 + b)
```

Think of it as: `y = f(wx + b)` — a weighted sum passed through a nonlinear function.

### Layers

Stack neurons into layers. Stack layers into a network.

```
Input Layer → Hidden Layer 1 → Hidden Layer 2 → ... → Output Layer
   (data)      (features)       (features)          (prediction)
```

- **Width** = number of neurons per layer
- **Depth** = number of layers (hence "deep" learning)
- More parameters = more capacity to learn complex patterns = more data needed to train

### Training Loop (Gradient Descent)

```
1. Forward pass:  feed input through the network, get a prediction
2. Loss:          compare prediction to expected output (how wrong is it?)
3. Backward pass: compute gradients (which direction to adjust each weight)
4. Update:        nudge each weight slightly in the direction that reduces loss
5. Repeat:        millions of times, across billions of examples
```

**Learning rate**: how big each nudge is. Too big = overshoots. Too small = takes forever.

**Batch size**: how many examples to process before updating weights. Larger batches = more stable gradients, more memory.

**Epoch**: one complete pass through the training data.

### Overfitting vs Underfitting

- **Overfitting**: model memorizes training data but fails on new data (too complex, not enough data)
- **Underfitting**: model is too simple to capture the patterns (not enough parameters, not enough training)
- **Generalization**: the goal — performs well on data it's never seen

---

## 3. Key Concepts for LLM Engineering

### Tokens (Not Words)

LLMs don't process words — they process **tokens**. A token is a chunk of text, roughly 3-4 characters on average.

```
"Hello, world!"  →  ["Hello", ",", " world", "!"]     (4 tokens)
"unbelievable"   →  ["un", "believ", "able"]           (3 tokens)
"   "            →  [" ", " ", " "]                     (3 tokens)
"🎉"             →  [token_id_48334]                    (1-2 tokens)
```

Why this matters:
- **Pricing** is per token, not per word
- **Context windows** are measured in tokens (128K tokens ≈ 96K words ≈ a novel)
- **Tokenization artifacts** cause weird behavior (bad at counting letters, math, certain languages)

### Embeddings (Meaning as Numbers)

An embedding is a vector (list of numbers) that represents the meaning of a token, word, sentence, or document. Similar meanings → similar vectors.

```
"king"  → [0.2, 0.8, 0.1, -0.3, ...]    (768 or 1536 dimensions)
"queen" → [0.2, 0.7, 0.1, -0.2, ...]     (similar direction)
"car"   → [-0.5, 0.1, 0.9, 0.4, ...]     (very different direction)
```

The classic example: `king - man + woman ≈ queen` (vector arithmetic on embeddings).

Why this matters for you:
- **RAG** works by embedding documents and queries, then finding similar vectors
- **Vector databases** (Pinecone, Weaviate, pgvector) store and search these vectors
- **Semantic search** replaces keyword matching with meaning matching
- **Similarity** is measured by cosine similarity (angle between vectors) or dot product

### Attention (How Transformers Work)

The key insight behind transformers: when processing a word, the model should "pay attention" to the most relevant other words in the context.

```
"The animal didn't cross the street because it was too tired."
                                           ^^
                          "it" attends most strongly to "animal"
```

For each token, the model computes:
- **Query**: "What am I looking for?"
- **Key**: "What do I contain?"
- **Value**: "What information do I provide?"

Attention scores = how much each token's query matches each other token's key. High score = that token's value gets more weight in the output.

You don't need to understand the math. You need to understand the implication: **transformers can relate any token to any other token in the context**, regardless of distance. This is what makes them better than RNNs.

### Temperature & Sampling

When an LLM generates the next token, it produces a probability distribution over its entire vocabulary.

```
Next token probabilities:
  "Paris"    → 0.75
  "London"   → 0.10
  "Berlin"   → 0.05
  "the"      → 0.03
  ...
```

**Temperature** controls randomness:
- `temperature=0`: always pick the highest probability token (deterministic, repetitive)
- `temperature=0.7`: mostly pick high-probability tokens with some variation (good default)
- `temperature=1.0`: sample proportional to probabilities (creative, diverse)
- `temperature=1.5`: flatten probabilities (very random, may produce nonsense)

**Top-p (nucleus sampling)**: only consider tokens whose cumulative probability exceeds `p`. `top_p=0.9` means consider the smallest set of tokens that covers 90% probability.

### Context Window

The context window is the total number of tokens the model can "see" at once — both your input and its output.

```
Context window: 128K tokens

[System prompt] + [User messages] + [Assistant responses] = must fit in 128K
     ~500              ~2000              ~1000
```

- Exceeding the window silently drops earlier content
- Longer contexts = more expensive (attention is O(n²) with sequence length)
- Models perform best on information near the beginning and end of context (the "lost in the middle" problem)

---

## 4. The LLM Stack

### How an LLM API Call Works

```
Your Application
    ↓ HTTP POST /v1/messages
[API Gateway / Load Balancer]
    ↓
[Tokenizer] → convert text to token IDs
    ↓
[Model Inference]
    ↓ autoregressive: generate one token at a time
    ↓ each new token feeds back in as input for the next
    ↓ repeat until stop token or max_tokens
    ↓
[Detokenizer] → convert token IDs back to text
    ↓
[Streaming / Response]
    ↓ SSE stream or complete JSON response
Your Application
```

Key point: LLMs generate **one token at a time**, autoregressively. Each generation step requires a full forward pass through the model. This is why generation is slow and why streaming matters — you can show tokens as they're produced.

### Provider APIs

All major providers follow a similar pattern:

```python
# Anthropic (Claude)
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)

# OpenAI (GPT)
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

The message format is standard: a list of `{role, content}` objects alternating between `user`, `assistant`, and optionally `system`.

### Key Terms You'll See Everywhere

| Term | Meaning |
|------|---------|
| **Inference** | Running a trained model to get predictions (as opposed to training) |
| **Latency** | Time to first token (TTFT) and time between tokens (inter-token latency) |
| **Throughput** | Tokens per second the system can produce |
| **Prompt** | Everything you send to the model (system + user messages) |
| **Completion** | The model's generated response |
| **Grounding** | Giving the model factual data to base its response on (RAG does this) |
| **Hallucination** | Model generates plausible-sounding but incorrect information |
| **Fine-tuning** | Additional training on domain-specific data to specialize a model |
| **RAG** | Retrieval-Augmented Generation — fetch relevant docs, include in prompt |
| **Agent** | LLM with access to tools (APIs, code execution) and a loop for multi-step reasoning |
| **Tool use / Function calling** | Model outputs structured requests for your code to execute |
| **Guardrails** | Input/output filters to enforce safety and quality constraints |

---

## 5. Python for LLM Engineering

All code examples in this course are Python. If you're primarily a TypeScript engineer, here's the minimum Python you need. For a comprehensive Python guide, see the [Python for TypeScript Engineers](../python/) course.

### Environment Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install common LLM libraries
pip install anthropic openai tiktoken numpy
```

### Essential Syntax

```python
# Variables and types
name: str = "Claude"
temperature: float = 0.7
tokens: list[str] = ["Hello", ",", " world"]
config: dict[str, any] = {"model": "claude-sonnet-4-20250514", "max_tokens": 1024}

# Functions
def count_tokens(text: str) -> int:
    return len(text.split())

# Async functions (used with streaming APIs)
async def stream_response(prompt: str):
    async with client.messages.stream(...) as stream:
        async for text in stream.text_stream:
            print(text, end="")

# List comprehensions
embeddings = [get_embedding(chunk) for chunk in chunks]
relevant = [doc for doc in docs if doc.score > 0.8]

# F-strings
prompt = f"Summarize this in {max_words} words: {text}"

# Context managers (used for API clients, file handling)
with open("data.json") as f:
    data = json.load(f)

# Error handling
try:
    response = client.messages.create(...)
except anthropic.RateLimitError:
    await asyncio.sleep(60)
    # retry
```

### Libraries You'll Use

| Library | Purpose |
|---------|---------|
| `anthropic` | Claude API client |
| `openai` | OpenAI API client |
| `tiktoken` | OpenAI tokenizer (count tokens) |
| `numpy` | Vector math (cosine similarity, etc.) |
| `httpx` | Async HTTP client |
| `chromadb` / `pinecone` | Vector databases |
| `langchain` / `llamaindex` | LLM orchestration frameworks |
| `pydantic` | Data validation (structured outputs) |

---

## 6. Math Intuition (No Proofs)

You don't need to derive backpropagation. You do need these intuitions.

### Vectors and Similarity

A vector is a list of numbers representing a point in space. Embeddings are vectors in high-dimensional space (768 or 1536 dimensions).

```python
a = [1, 0, 0]   # points along x-axis
b = [0, 1, 0]   # points along y-axis
c = [1, 0.1, 0] # close to a

# Cosine similarity: angle between vectors
# 1.0 = identical direction (most similar)
# 0.0 = perpendicular (unrelated)
# -1.0 = opposite direction (opposite meaning)

cosine_similarity(a, c) ≈ 0.995  # very similar
cosine_similarity(a, b) = 0.0    # unrelated
```

### Probability & Softmax

Softmax converts a list of raw scores (logits) into probabilities that sum to 1:

```
logits:        [2.0, 1.0, 0.1]
softmax:       [0.66, 0.24, 0.10]   # sums to 1.0
```

Every time an LLM picks the next token, it runs softmax over vocabulary-sized logits. Temperature scales the logits before softmax — lower temperature makes the distribution peakier (more confident), higher makes it flatter (more random).

### Loss Functions

During training, the loss function measures how wrong the model is:

- **Cross-entropy loss** (used for LLMs): measures how far the predicted probability distribution is from the actual next token
- Lower loss = better predictions
- Training minimizes loss by adjusting weights

---

## 7. Quick Checklist

Before starting Module 01, you should be comfortable with:

- [ ] What's the difference between training and inference?
- [ ] What is a token? Why don't LLMs process words directly?
- [ ] What is an embedding? Why are similar things close together in embedding space?
- [ ] What does temperature control? What happens at 0 vs 1.0?
- [ ] What's the context window and what happens when you exceed it?
- [ ] What is attention at an intuitive level? (not the math)
- [ ] What's the difference between pre-training, fine-tuning, and RLHF?
- [ ] What is RAG at a high level? Why is it useful?
- [ ] What's a hallucination and why do LLMs produce them?
- [ ] Can you write basic Python (functions, list comprehensions, async/await)?

If any of these feel unclear, re-read that section. Module 01 builds directly on all of them.

---

## Next Steps

You're ready for [Module 01: LLM Fundamentals](01-llm-fundamentals/README.md) — transformer architecture, tokenization mechanics, attention in detail, and the full training pipeline from pre-training to RLHF.
