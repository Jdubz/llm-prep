# Advanced Production Patterns

Self-hosted inference, multi-model architectures, gateway patterns, token budget management, capacity planning, and disaster recovery for LLM systems at scale.

---

## Self-Hosted Inference

### When Self-Hosting Beats APIs

The decision between managed APIs and self-hosted inference is primarily an economics and compliance question.

| Factor | API | Self-Hosted |
|---|---|---|
| Setup time | Minutes | Days to weeks |
| Cost at low volume | Lower (pay per token) | Higher (fixed GPU cost) |
| Cost at high volume | Higher | Lower (amortized GPU) |
| Latency | Network + provider queue | Local, predictable |
| Data privacy | Data leaves your network | Data stays on your infra |
| Model selection | Provider's models only | Any open-weight model |
| Customization | None (fine-tuning limited) | Full control |
| Reliability | Provider SLA | Your SLA |
| Scaling | Automatic | You manage it |

**Break-even analysis.** A single A100 80GB GPU costs roughly $2/hour on cloud ($1,440/month). Running Llama 3.1 70B quantized at approximately 30 tokens/second, that is about 77M output tokens per month. At GPT-4o output pricing ($10/1M tokens), that is $770/month equivalent. Self-hosting starts winning when:
- You have consistent, high-volume traffic (> 50M tokens/month).
- You need data privacy guarantees (healthcare, finance, legal).
- You need customization (fine-tuned models, custom decoding).
- Latency predictability matters more than raw speed.

### Inference Engines

**vLLM** is the de facto standard for high-throughput self-hosted inference.

Core features:
- PagedAttention for efficient GPU memory management.
- Continuous batching for maximum throughput.
- Tensor parallelism for multi-GPU serving.
- OpenAI-compatible API server built in.
- Supports most popular model architectures.

```bash
# Serve a model with vLLM
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-70B-Instruct \
    --tensor-parallel-size 4 \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.9
```

**Text Generation Inference (TGI)** is Hugging Face's production-tested inference server.

Core features:
- Flash Attention 2 integration.
- Token streaming out of the box.
- Quantization support (GPTQ, AWQ, EETQ).
- Good Docker support for containerized deployment.

```bash
# Serve with TGI
docker run --gpus all \
    -p 8080:80 \
    ghcr.io/huggingface/text-generation-inference:latest \
    --model-id meta-llama/Llama-3.1-70B-Instruct \
    --num-shard 4 \
    --max-input-length 4096 \
    --max-total-tokens 8192
```

**Ollama** is optimized for local development and edge deployment, not high-throughput production serving.

```bash
# Simple local inference
ollama run llama3.1
```

Automatic quantization and model management. REST API compatible with common tooling. Not designed for production-scale serving — use vLLM or TGI for that.

### GPU Selection Guide

| GPU | VRAM | FP16 TFLOPS | Typical Use | Cloud $/hr |
|---|---|---|---|---|
| A10G | 24 GB | 31.2 | 7B-13B models | ~$1.00 |
| L4 | 24 GB | 30.3 | 7B-13B models | ~$0.80 |
| A100 40GB | 40 GB | 77.9 | 13B-34B models | ~$1.50 |
| A100 80GB | 80 GB | 77.9 | 34B-70B (quantized) | ~$2.00 |
| H100 80GB | 80 GB | 267.6 | 70B+ models | ~$3.50 |
| H200 141GB | 141 GB | 267.6 | 70B (full precision) | ~$4.50 |

**VRAM requirements rule of thumb:**
- FP16: ~2 bytes per parameter. A 70B model needs ~140 GB VRAM.
- INT8 quantization: ~1 byte per parameter. 70B needs ~70 GB.
- INT4 quantization: ~0.5 bytes per parameter. 70B needs ~35 GB.
- Add 10-20% overhead for KV cache and activations.

### Throughput Benchmarks

Rough throughput figures (tokens/second output, continuous batching at high utilization):

| Model | GPU | Quantization | Throughput (tokens/s) |
|---|---|---|---|
| Llama 3.1 8B | A10G | FP16 | 80-120 |
| Llama 3.1 8B | A10G | INT4 (AWQ) | 150-200 |
| Llama 3.1 70B | 4x A100 80GB | FP16 | 40-60 |
| Llama 3.1 70B | 2x H100 | INT4 (AWQ) | 80-120 |
| Llama 3.1 70B | 4x H100 | FP16 | 100-150 |
| Mixtral 8x7B | 2x A100 80GB | FP16 | 60-90 |

These are aggregate throughput numbers. Per-request latency will be higher at large batch sizes.

---

## Batching and Throughput

### Why Batching Matters

GPU utilization is the key to cost-effective inference. A single request uses a fraction of the GPU's compute capacity. Batching amortizes the fixed costs (weight loading, memory transfers) across multiple requests.

```
Single request:  GPU utilization ~10-20%
Batch of 8:      GPU utilization ~60-80%
Batch of 32:     GPU utilization ~90%+ (diminishing returns)
```

### Static Batching vs. Continuous Batching

**Static batching:** Collect N requests, process them together, return all results when the slowest request finishes.

```
Requests:  [r1, r2, r3, r4]  →  GPU processes batch  →  [resp1, resp2, resp3, resp4]
```

The problem: all requests in the batch must complete before any result is returned. A request generating 10 tokens waits for a request generating 500 tokens. This wastes GPU cycles and increases latency for short requests.

**Continuous batching** is the modern approach used by vLLM, TGI, and other production engines.

```
Iteration 1: [r1(token 5), r2(token 3), r3(token 1), -----]
Iteration 2: [r1(token 6), r2(done!),    r3(token 2), r4(token 1)]  ← r2 finishes, r4 joins
Iteration 3: [r1(token 7), r5(token 1),  r3(token 3), r4(token 2)]  ← r5 fills the slot
```

Key properties:
- Requests enter and leave the batch independently.
- No request waits for another to finish.
- GPU utilization stays high because slots are immediately reused.
- Dramatically better throughput and latency compared to static batching.

### PagedAttention

The KV cache is the memory bottleneck in LLM inference. Each token generates a key-value pair that must be stored for attention computation. For long sequences with large batches, KV cache can consume more memory than the model weights.

**Traditional approach:** Pre-allocate a contiguous block of memory for each request's maximum possible sequence length. This wastes memory on short sequences.

**PagedAttention** borrows ideas from virtual memory in operating systems:
- KV cache is divided into fixed-size "pages" (blocks).
- Pages are allocated on demand as the sequence grows.
- Pages can be non-contiguous in physical memory.
- Completed sequences free their pages immediately.

```
Traditional allocation:
  Request 1: [████████████________________]  (12 tokens used, 16 wasted)
  Request 2: [████████████████████________]  (20 tokens used, 8 wasted)

PagedAttention:
  Request 1: [page1][page2][page3]           (12 tokens, 0 wasted)
  Request 2: [page4][page5][page6][page7][page8]  (20 tokens, ~0 wasted)
  Free pool: [page9][page10]...              (available for new requests)
```

Result: 2-4x higher throughput compared to naive memory management because more requests fit in GPU memory simultaneously.

### Throughput vs. Latency Tradeoffs

Increasing batch size improves throughput (up to GPU saturation) but also increases per-request latency (more compute per iteration). The sweet spot depends on your SLA:
- Interactive chat needs low latency (small batches, fast TTFT).
- Batch processing needs high throughput (large batches, throughput maximized).

---

## Speculative Decoding

### The Core Idea

Autoregressive generation is bottlenecked by sequential token generation — each token requires a full forward pass through the model. Speculative decoding uses a small, fast "draft" model to propose multiple tokens, which the large "target" model verifies in parallel.

```
Draft model (small, fast):
  Proposes: ["The", "capital", "of", "France", "is", "Paris"]

Target model (large, accurate):
  Verifies in one forward pass:
  - "The" ✓
  - "capital" ✓
  - "of" ✓
  - "France" ✓
  - "is" ✓
  - "Paris" ✓  → Accept all 6 tokens

  6 tokens generated in ~1 forward pass of the target model
  instead of 6 sequential forward passes.
```

### When It Helps

Speculative decoding helps most when:
- The draft model is good at predicting the target model's output. For factual, predictable text (code, structured data), acceptance rates are high (70-90%). For creative text, acceptance rates are lower (40-60%).
- The draft model is significantly faster. A 7B draft model with a 70B target is a good pairing.
- Latency matters more than throughput. Speculative decoding improves per-request latency but may reduce total throughput because the target model does extra work verifying draft tokens.

### Speedup Expectations

| Scenario | Draft Acceptance Rate | Effective Speedup |
|---|---|---|
| Code generation | 80-90% | 2-3x |
| Factual Q&A | 70-85% | 1.5-2.5x |
| Creative writing | 40-60% | 1.2-1.5x |
| Very creative/random | 20-40% | 1.0-1.2x (may not help) |

### Provider Support

- **Anthropic:** Not exposed as a user-facing feature (may be used internally).
- **OpenAI:** Not exposed directly. The `predicted_output` parameter in some APIs is related.
- **Google:** Speculative decoding available for Gemini on Vertex AI.
- **Self-hosted:** vLLM and TGI both support speculative decoding with configurable draft models.

---

## Edge Deployment

### On-Device Inference Frameworks

| Framework | Platform | Best For |
|---|---|---|
| llama.cpp / GGUF | CPU, Mac, Linux, Windows | Broadest compatibility, CPU-optimized |
| Apple MLX | Apple Silicon (M1-M4) | Native Metal acceleration on Mac/iOS |
| ONNX Runtime | Cross-platform | Edge devices, Windows, mobile |
| MediaPipe (Google) | Android, iOS, Web | Mobile-first applications |
| MLC LLM | Cross-platform | Compiled models for specific hardware |

### Performance Expectations (On-Device)

| Device | Model | Quantization | Tokens/sec |
|---|---|---|---|
| MacBook Pro M3 Max (48GB) | Llama 3.1 8B | Q4_K_M | 40-60 |
| MacBook Pro M3 Max (48GB) | Llama 3.1 70B | Q4_K_M | 8-12 |
| MacBook Air M2 (16GB) | Llama 3.1 8B | Q4_K_M | 20-30 |
| iPhone 15 Pro (8GB) | Llama 3.2 3B | Q4_K_M | 10-15 |
| Pixel 8 (12GB) | Gemma 2B | INT4 | 8-12 |

### When to Deploy on Edge

**Good fit:**
- Privacy-critical applications (medical, legal, personal data) — data never leaves the device.
- Offline functionality (field work, disconnected environments).
- Latency-critical (real-time autocomplete, local code assistance).
- Cost optimization at massive user scale — inference cost moves to user hardware.

**Poor fit:**
- Tasks requiring large models (> 13B parameters on most devices).
- High throughput requirements (edge devices serve one user at a time).
- Applications needing the latest frontier model capabilities.
- Users on low-end or constrained hardware.

---

## Multi-Model Architectures

### Router Pattern

A lightweight classifier routes requests to the appropriate specialist model, enabling cost-quality optimization without quality compromise.

```
                     ┌─────────────┐
                     │   Router    │
                     │  (small LM  │
                     │  or rules)  │
                     └──────┬──────┘
                ┌───────────┼───────────┐
                ▼           ▼           ▼
          ┌──────────┐ ┌──────────┐ ┌──────────┐
          │  Simple  │ │  Medium  │ │  Complex │
          │  Model   │ │  Model   │ │  Model   │
          │ (Haiku)  │ │ (Sonnet) │ │  (Opus)  │
          └──────────┘ └──────────┘ └──────────┘
```

**Router implementation options:**

1. **Keyword heuristics.** Fast, no extra API call. Check for complexity indicators: "analyze", "compare", "step by step" route to the large model. Simple queries route to the small model.
2. **Embedding classifier.** Embed the query, classify into complexity buckets using a trained classifier. More accurate, adds 10-20ms.
3. **Small LLM as router.** Use a fast model (GPT-4o-mini, Haiku) to classify the required complexity. Most accurate, adds 200-500ms and small cost.

```python
import re
from dataclasses import dataclass
from enum import Enum

class ModelTier(Enum):
    SIMPLE = "claude-haiku-3-5-20241022"
    MEDIUM = "claude-sonnet-4-20250514"
    COMPLEX = "claude-opus-4-20250514"

COMPLEXITY_PATTERNS = [
    re.compile(r'\b(analyze|compare|evaluate|design|architect)\b', re.I),
    re.compile(r'\b(step.by.step|reason through|explain why)\b', re.I),
    re.compile(r'\b(tradeoffs|pros and cons|critique)\b', re.I),
]

SIMPLE_PATTERNS = [
    re.compile(r'\b(what is|define|who is|when was|how many)\b', re.I),
    re.compile(r'\b(yes or no|true or false|summarize briefly)\b', re.I),
]

def route_request(user_message: str, context_tokens: int) -> ModelTier:
    """Heuristic-based model router."""
    # Long context or multi-document tasks need capable models
    if context_tokens > 50_000:
        return ModelTier.COMPLEX

    message_lower = user_message.lower()

    # Check for complexity signals
    for pattern in COMPLEXITY_PATTERNS:
        if pattern.search(message_lower):
            return ModelTier.MEDIUM

    # Check for simple patterns
    for pattern in SIMPLE_PATTERNS:
        if pattern.search(message_lower):
            return ModelTier.SIMPLE

    # Default to medium tier
    return ModelTier.MEDIUM
```

### Cascade Pattern

Try the cheapest model first. Escalate if the response quality is insufficient. Achieves high quality on hard requests while keeping costs low for easy ones.

```
            ┌──────────────┐
            │  Small Model │
            │   (Haiku)    │
            └──────┬───────┘
                   │
            confidence > 0.8?
             ╱           ╲
           Yes            No
            │              │
      Return response     │
                   ┌──────┴───────┐
                   │ Medium Model  │
                   │  (Sonnet)     │
                   └──────┬────────┘
                          │
                   confidence > 0.8?
                    ╱           ╲
                  Yes            No
                   │              │
             Return response     │
                          ┌──────┴───────┐
                          │ Large Model   │
                          │   (Opus)      │
                          └───────────────┘
```

**Confidence estimation methods:**
- **Log probabilities.** If available, use the model's token-level log probs. Low entropy = high confidence.
- **Self-reported confidence.** Ask the model to rate its own confidence (unreliable, but cheap).
- **Output validation.** Run the output through a validator. If it passes, accept; if not, escalate.
- **Heuristic checks.** Length, presence of hedging language ("I'm not sure"), refusals.

**Cascade economics:**
If 70% of requests are handled by the small model, 25% by medium, 5% by large:
```
Average cost = 0.70 * $small + 0.25 * $medium + 0.05 * $large
```
Plus escalation overhead (duplicate processing for escalated requests). Net savings: typically 50-70% compared to always using the large model.

### Ensemble Approaches

Multiple models generate responses in parallel; a selector picks the best one.

```
        ┌──────────┐
┌──────►│ Model A  │──────┐
│       └──────────┘      │
│       ┌──────────┐      │     ┌──────────┐
Query ─►│ Model B  │──────┼────►│ Selector │──► Best Response
│       └──────────┘      │     └──────────┘
│       ┌──────────┐      │
└──────►│ Model C  │──────┘
        └──────────┘
```

**When to use ensembles:**
- High-stakes decisions where quality justifies 3x cost.
- Tasks where different models have complementary strengths.
- A/B testing and model comparison in production.

**Selection strategies:**
- LLM-as-judge: a separate model evaluates all responses and picks the best.
- Voting: for classification tasks, take the majority vote.
- Confidence-weighted: pick the response from the most confident model.

---

## Gateway and Proxy Patterns

### Why Use a Gateway

A gateway sits between your application and LLM providers, centralizing cross-cutting concerns.

```
Your Application
       │
       ▼
┌──────────────────┐
│   LLM Gateway    │
│                  │
│  - Unified API   │
│  - Load balance  │
│  - Failover      │
│  - Rate limiting │
│  - Logging       │
│  - Caching       │
│  - Cost tracking │
└──────┬───────────┘
       │
  ┌────┼────┐
  ▼    ▼    ▼
 OAI  Anth  Goog
```

Without a gateway, every piece of application code that calls an LLM must implement retries, logging, fallbacks, and cost tracking independently. A gateway centralizes this logic.

### Gateway Options

| Tool | Type | Key Features |
|---|---|---|
| LiteLLM | OSS proxy | OpenAI-compatible API for 100+ models, load balancing, fallbacks |
| Portkey | Managed service | Gateway + observability, caching, prompt management |
| Helicone | Managed proxy | Zero-code logging, caching, rate limiting |
| Custom (FastAPI) | DIY | Full control, no dependencies |

### LiteLLM Example

```python
import litellm

# Same API, different providers
response = litellm.completion(
    model="anthropic/claude-sonnet-4-20250514",
    messages=[{"role": "user", "content": "Hello"}],
    fallbacks=["openai/gpt-4o", "openai/gpt-4o-mini"],
    # If Anthropic fails, try OpenAI, then mini
)
```

LiteLLM translates your request into the target provider's format automatically.

### Custom Gateway Must-Have Features

For most teams, a lightweight custom gateway built on FastAPI is the right choice:

**Must-have features:**
- Unified request/response format across providers.
- Structured logging of every request (prompt, response, model, latency, cost).
- Retry logic with exponential backoff.
- Per-provider health checks and circuit breakers.
- API key management and rotation.

**Nice-to-have features:**
- Response caching (exact-match and semantic).
- Rate limiting per client/feature.
- Cost tracking and budget enforcement.
- A/B testing (route percentage of traffic to different models).
- Prompt versioning and management.

```python
from fastapi import FastAPI, Request
from dataclasses import dataclass
from typing import Optional
import time
import asyncio
import anthropic
import openai

app = FastAPI()

@dataclass
class ProviderHealth:
    failures: int = 0
    last_failure: float = 0.0
    circuit_open: bool = False

    def record_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= 5:
            self.circuit_open = True

    def record_success(self):
        self.failures = 0
        self.circuit_open = False

    def should_try(self) -> bool:
        if not self.circuit_open:
            return True
        # Half-open: try again after 30 seconds
        return time.time() - self.last_failure > 30

provider_health = {
    "anthropic": ProviderHealth(),
    "openai": ProviderHealth(),
}

async def call_with_fallback(messages: list, **kwargs):
    """Try primary provider, fall back on failure."""
    providers = [
        ("anthropic", "claude-sonnet-4-20250514"),
        ("openai", "gpt-4o"),
    ]

    for provider_name, model in providers:
        health = provider_health[provider_name]
        if not health.should_try():
            continue

        try:
            start = time.time()
            if provider_name == "anthropic":
                client = anthropic.Anthropic()
                response = client.messages.create(
                    model=model,
                    messages=messages,
                    max_tokens=kwargs.get("max_tokens", 1024),
                )
                result = response.content[0].text
            else:
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=kwargs.get("max_tokens", 1024),
                )
                result = response.choices[0].message.content

            health.record_success()
            latency = time.time() - start

            # Log the call
            log_llm_call(
                provider=provider_name,
                model=model,
                messages=messages,
                response=result,
                latency=latency,
            )

            return result

        except Exception as e:
            health.record_failure()
            continue

    raise RuntimeError("All providers failed")

def log_llm_call(provider, model, messages, response, latency):
    """Structured logging for every LLM call."""
    # In production, send to your observability stack
    print({
        "provider": provider,
        "model": model,
        "input_tokens": sum(len(m["content"]) // 4 for m in messages),
        "latency_s": round(latency, 3),
    })
```

---

## Token Budget Management

### The Problem

Every LLM has a context window limit. Your application must ensure the total tokens (input + output) fit within this limit. Exceeding it causes a hard error.

```
Context Window: 128,000 tokens
├── System prompt:        2,000 tokens (fixed)
├── Tool definitions:     1,500 tokens (fixed)
├── Few-shot examples:    1,000 tokens (fixed)
├── Conversation history: variable
├── RAG context:          variable
├── User message:         variable
└── Reserved for output:  4,096 tokens (max_tokens)
    ────────────────────
    Available for dynamic content: 119,404 tokens
```

### Budget Allocation Strategy

```python
import tiktoken

# Budget constants
CONTEXT_WINDOW = 128_000
SYSTEM_PROMPT_TOKENS = 2_000
TOOL_DEFINITIONS_TOKENS = 1_500
FEW_SHOT_TOKENS = 1_000
OUTPUT_RESERVED = 4_096
SAFETY_MARGIN = 500  # buffer for tokenizer discrepancies

FIXED_TOKENS = (
    SYSTEM_PROMPT_TOKENS
    + TOOL_DEFINITIONS_TOKENS
    + FEW_SHOT_TOKENS
    + OUTPUT_RESERVED
    + SAFETY_MARGIN
)

AVAILABLE_FOR_DYNAMIC = CONTEXT_WINDOW - FIXED_TOKENS  # 119,404

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    enc = tiktoken.encoding_for_model(model)
    return len(enc.encode(text))

def allocate_budget(user_message: str) -> dict[str, int]:
    user_tokens = count_tokens(user_message)
    remaining = AVAILABLE_FOR_DYNAMIC - user_tokens
    return {
        "user_message": user_tokens,
        "conversation_history": int(remaining * 0.40),
        "rag_context": int(remaining * 0.60),
    }
```

### Dynamic Context Window Selection

Some providers offer models with multiple context window sizes at different price points. Route to the smallest sufficient window.

```
Estimated input tokens:
  < 4,000   → Use 8K context model (cheapest)
  < 16,000  → Use 32K context model
  < 64,000  → Use 128K context model
  < 200,000 → Use 200K context model (most expensive)
```

### Conversation History Management

For long conversations, trim or summarize history to stay within the budget.

**Strategies (in order of sophistication):**

1. **Truncate old messages.** Drop messages from the beginning. Simple but loses context.
2. **Sliding window.** Keep the last N turns. Simple and usually sufficient.
3. **Summarize and truncate.** Periodically summarize older messages, keep the summary + recent turns.
4. **Importance-weighted.** Score each message by relevance to the current query, keep the most relevant.

```python
from anthropic import Anthropic

client = Anthropic()

def manage_conversation_history(
    messages: list[dict],
    max_history_tokens: int,
    summary: str = "",
) -> tuple[list[dict], str]:
    """
    Trim conversation history to fit within token budget.
    Returns (trimmed_messages, updated_summary).
    """
    # Count tokens in all messages
    total_tokens = sum(count_tokens(m["content"]) for m in messages)

    if total_tokens <= max_history_tokens:
        return messages, summary  # No trimming needed

    # Summarize the oldest half of messages
    midpoint = len(messages) // 2
    messages_to_summarize = messages[:midpoint]
    recent_messages = messages[midpoint:]

    # Generate summary of old messages
    summarize_prompt = (
        f"Previous summary: {summary}\n\n"
        "Summarize the following conversation in 2-3 sentences, "
        "preserving the key decisions, facts, and context:\n\n"
    )
    for m in messages_to_summarize:
        summarize_prompt += f"{m['role']}: {m['content']}\n"

    response = client.messages.create(
        model="claude-haiku-3-5-20241022",
        max_tokens=256,
        messages=[{"role": "user", "content": summarize_prompt}],
    )
    new_summary = response.content[0].text

    return recent_messages, new_summary

def build_messages_with_budget(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    rag_context: str = "",
) -> list[dict]:
    """Build the messages array respecting token budgets."""
    budget = allocate_budget(user_message)

    # Trim conversation history
    trimmed_history, _ = manage_conversation_history(
        conversation_history,
        max_history_tokens=budget["conversation_history"],
    )

    # Trim RAG context if needed
    rag_tokens = count_tokens(rag_context)
    if rag_tokens > budget["rag_context"]:
        # Truncate RAG context to fit
        rag_words = rag_context.split()
        target_words = int(budget["rag_context"] * 0.75)  # rough conversion
        rag_context = " ".join(rag_words[:target_words]) + "\n[Context truncated]"

    # Assemble final user message
    if rag_context:
        final_user_content = (
            f"<context>\n{rag_context}\n</context>\n\n{user_message}"
        )
    else:
        final_user_content = user_message

    return [
        *trimmed_history,
        {"role": "user", "content": final_user_content},
    ]
```

---

## Capacity Planning

### Estimating TPM Requirements

```
Daily active users:            10,000
Avg requests per user per day: 5
Avg input tokens per request:  2,000
Avg output tokens per request: 500
Peak multiplier:               3x average

Daily tokens:
  Input:  10,000 × 5 × 2,000 = 100M tokens/day
  Output: 10,000 × 5 × 500   = 25M tokens/day

Peak TPM (assuming 8-hour active window):
  Input:  100M / (8 × 60) × 3 = 625,000 TPM
  Output: 25M / (8 × 60) × 3  = 156,250 TPM

Required provider tier: OpenAI Tier 4+ or Anthropic Build Tier 4
```

Plan for peak, not average. If you hit rate limits at peak, users experience errors during your busiest period. Size for 2-3x your expected peak to handle traffic spikes.

### Handling Traffic Spikes

**Reactive strategies:**
- Auto-scaling self-hosted inference (add GPU nodes).
- Overflow to a secondary provider.
- Aggressive caching during spikes.
- Request queuing with priority (interactive requests before batch jobs).
- Graceful degradation (smaller models, shorter responses).

**Proactive strategies:**
- Pre-warm capacity before known events (product launches, marketing campaigns).
- Load test regularly to identify bottlenecks.
- Maintain headroom: operate at < 70% of your rate limits normally.
- Use batch APIs for deferrable work, reserving real-time capacity for interactive requests.

### Auto-Scaling for Self-Hosted Inference

```
Metric:        GPU utilization / request queue depth
Scale-up:      When utilization > 80% for 2 minutes, add 1 node
Scale-down:    When utilization < 30% for 10 minutes, remove 1 node
Min instances:  2 (for redundancy)
Max instances:  determined by budget
Cool-down:      5 minutes between scaling actions
```

GPU nodes take 2-5 minutes to start and load model weights. Plan for this startup latency in your scaling policy — you need to scale ahead of demand, not in response to it.

---

## Disaster Recovery

### Provider Outage Handling

Every provider has outages. Treat LLM APIs like any other external dependency.

```
Outage Detection:
  - Health check endpoint: ping provider every 30 seconds
  - Error rate monitoring: if error rate > 20% in 1 minute, declare outage
  - Circuit breaker: after 5 consecutive failures, open circuit

Failover:
  Primary:   Anthropic (Claude Sonnet)
  Secondary: OpenAI (GPT-4o)
  Tertiary:  Google (Gemini Pro)
  Emergency: Self-hosted (Llama 70B) or cached responses

Recovery:
  - Half-open circuit breaker tests primary every 30 seconds
  - When primary recovers, gradually shift traffic back: 10% → 25% → 50% → 100%
  - Do not snap back to 100% immediately (the provider may be fragile post-outage)
```

```python
import time
from enum import Enum
from dataclasses import dataclass, field

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    traffic_ratio: float = 1.0  # For gradual recovery

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            # Gradually increase traffic on recovery
            self.traffic_ratio = min(1.0, self.traffic_ratio + 0.1)
            if self.traffic_ratio >= 1.0:
                self.state = CircuitState.CLOSED
        self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.traffic_ratio = 0.0

    def should_allow_request(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.traffic_ratio = 0.1  # Start with 10% traffic
            else:
                return False
        # HALF_OPEN: allow traffic_ratio fraction of requests
        import random
        return random.random() < self.traffic_ratio
```

### Model Deprecation Strategies

Providers deprecate models with varying notice periods (weeks to months). Your system must handle this gracefully.

**Model alias layer** is the most important mitigation. Never hardcode model names in application code. Use aliases that map to specific model versions, changeable without code deploys:

```python
# models.py — centralized model configuration
MODEL_ALIASES = {
    "default-fast": "claude-haiku-3-5-20241022",
    "default-smart": "claude-sonnet-4-20250514",
    "default-capable": "claude-opus-4-20250514",
    "embedding": "text-embedding-3-small",
}

def get_model(alias: str) -> str:
    """Resolve a model alias to a concrete model ID."""
    model = MODEL_ALIASES.get(alias)
    if not model:
        raise ValueError(f"Unknown model alias: {alias}")
    return model

# In application code:
response = client.messages.create(
    model=get_model("default-smart"),  # Never hardcode "claude-sonnet-4-..."
    messages=messages,
    max_tokens=1024,
)
```

**Eval-gated migration.** Before switching to a new model version, run your eval suite. Only switch if quality metrics hold.

**Shadow mode.** Run the new model in parallel (shadow traffic), compare outputs, switch when confident. No user impact during validation.

**Deprecation alerts.** Monitor provider announcements. Track model deprecation dates in your configuration. Set calendar reminders 30 days before known deprecation dates.

### Multi-Region Deployment

For global applications:
- Deploy your gateway in multiple regions.
- Route to the geographically closest provider endpoint.
- Failover across regions if one region's provider endpoint is down.
- Be aware of data residency requirements (EU data may need EU endpoints).

### Production Runbook Essentials

Every production LLM system should have a runbook covering these scenarios:

1. **Provider outage:** Detection method, failover steps, communication template for users.
2. **Cost spike:** Investigation steps (per-feature cost breakdown, prompt audit), emergency kill switches, rate limiting escalation.
3. **Quality degradation:** Detection (eval scores dropping, user feedback spike), rollback to previous model/prompt, escalation path.
4. **Rate limit exhaustion:** Prioritization (which features to protect), degradation plan, provider upgrade process.
5. **Data incident:** PII in logs, prompt injection exfiltrating data, containment steps and timeline.
6. **Model behavior change:** Provider silently updates model weights, outputs change subtly. Detection (eval drift monitoring) and response (rollback, contact provider).

---

## Interview Deep-Dive Questions

These questions probe deeper than standard production questions and expect specific technical details.

**"You're self-hosting a 70B model. Walk me through your infrastructure choices."**

The answer should include concrete numbers: GPU selection (H100 for throughput, A100 for cost), quantization decision (INT4 via AWQ for 35GB footprint vs FP16 for 140GB), inference engine (vLLM for PagedAttention and continuous batching), multi-GPU setup (tensor parallelism across 2-4 GPUs), and expected throughput (80-120 tokens/second on 2x H100 with INT4). Show you know the cost math: at $7/hour for 2x H100, 120 tokens/second throughput, and typical request patterns, what does your cost per request look like versus API pricing?

**"Design a multi-model architecture for a customer support system."**

Cover: router vs. cascade decision (cascade is simpler and more cost-effective when you can measure confidence), model tiers (Haiku for intent classification, Sonnet for RAG generation, Opus for complex agent actions), confidence estimation (output validation and heuristic checks rather than unreliable self-reported confidence), and cost analysis (70% of requests handled at Haiku rates saves 5-10x on average cost).

**"How would you handle a scenario where your primary LLM provider goes down?"**

Walk through the full sequence: circuit breaker detects failure, failover to secondary provider, model alias layer means no code changes required, gradual traffic recovery once primary comes back. Address the quality difference: the fallback model may produce slightly different output quality, which is acceptable during an outage. Mention monitoring: you need to know the outage happened, how long it lasted, and what impact it had on users.

**"Your LLM costs have tripled this month. Walk me through your investigation and optimization."**

Start with the cost monitoring dashboard: which feature, which model, which prompt template drove the increase? Was it traffic growth (legitimate), a new feature deployed (check token counts per request), or a bug (unbounded loops, regeneration on errors)? Then systematic optimization: model routing review (is each feature using the cheapest model that meets its quality bar?), prompt audit (concise system prompts, are token counts growing?), caching analysis (are frequently repeated queries being cached?), batch processing opportunities (can any real-time processing move to batch?).

**"You need to serve 10,000 concurrent users with sub-2-second latency. Design the system."**

Capacity planning math (10K concurrent users × average tokens per request → TPM requirement), caching strategy (semantic caching reduces load), streaming (perceived latency drops to TTFT which is 200-800ms), model selection (fast tier for simple requests), geographic distribution (nearest endpoint), auto-scaling approach, and whether API or self-hosted is more viable at this scale.
