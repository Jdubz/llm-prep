# 02 — Training and Model Families

## The LLM Training Pipeline

Modern LLMs go through three distinct training stages. Each stage serves a different purpose, uses different data, and produces a qualitatively different model.

### Stage 1: Pre-training

Pre-training is the expensive core of LLM development. A model is trained on a massive corpus of text — trillions of tokens from the web, books, code, scientific papers, and other sources — using a **next-token prediction objective**:

```
Given tokens [t1, t2, t3, ..., tn], predict t_{n+1}
Loss = cross_entropy(model_output, true_next_token)
```

This simple objective forces the model to learn everything necessary to predict text well: grammar, facts, reasoning patterns, coding conventions, mathematics, common sense, and world knowledge. The model that emerges is an extremely powerful text completer but not a helpful assistant — it will continue any text you give it, but it does not know how to follow instructions.

**Scale:** Pre-training a frontier model requires:
- Trillions of tokens of training data (GPT-3 used 300B, Llama 2 used 2T, Llama 3 used 15T)
- Thousands of GPUs running for weeks to months
- Millions of dollars in compute

**What the model learns:** Language patterns, factual associations, reasoning heuristics, code structure, and much more — all implicitly from the next-token prediction signal.

### Stage 2: Supervised Fine-Tuning (SFT)

SFT adapts the pre-trained model to follow instructions. You train on curated (instruction, response) pairs — typically tens of thousands to hundreds of thousands of high-quality examples showing what a good assistant response looks like:

```json
{
  "messages": [
    {"role": "user", "content": "Explain photosynthesis in simple terms."},
    {"role": "assistant", "content": "Photosynthesis is how plants make food from sunlight..."}
  ]
}
```

After SFT, the model understands the conversational format, follows instructions, and can handle multi-turn dialogue. But it does not yet have well-calibrated values — it might be too verbose, occasionally harmful, or inconsistently helpful.

### Stage 3: Alignment (RLHF / DPO)

Alignment training teaches the model to prefer helpful, harmless, and honest responses.

**RLHF (Reinforcement Learning from Human Feedback):**

1. Collect human preference data: show human raters two model responses to the same prompt, have them pick which is better
2. Train a reward model on these preference pairs to score responses
3. Use PPO (Proximal Policy Optimization) to fine-tune the LLM to maximize reward model scores

RLHF is powerful but complex: it requires maintaining both the LLM and the reward model, and PPO training can be unstable.

**DPO (Direct Preference Optimization):**

DPO achieves similar results with a simpler single-stage process. Instead of training a separate reward model, DPO directly optimizes the LLM weights using the preference data. The mathematical insight: the optimal reward model under RLHF can be expressed as a function of the policy itself, so you can skip the reward model entirely.

DPO training objective:
```
Maximize: log σ(β * (log π(y_w|x) - log π_ref(y_w|x)) - β * (log π(y_l|x) - log π_ref(y_l|x)))

Where:
  y_w = preferred (winning) response
  y_l = rejected (losing) response
  π_ref = reference model (frozen pre-SFT model)
  β = regularization strength
```

**Outcome of alignment:** The model learns to refuse harmful requests, express appropriate uncertainty, be helpful without being obsequious, and behave consistently across many situations. This is what makes a base model into a product.

**Constitutional AI (Anthropic's approach):** Anthropic's method generates its own feedback by having the model critique its own outputs against a set of principles (the "constitution"), then revise them. This reduces reliance on human feedback for many evaluation dimensions.

---

## Scaling Laws

Scaling laws describe how model performance improves with compute, data, and parameter count. They are fundamental to understanding why big models are better and how to allocate training budgets.

### Kaplan et al. (OpenAI, 2020)

Key findings:
- Loss scales as a power law with model size, dataset size, and compute
- Model size matters most for a fixed compute budget
- Increasing any one dimension while holding others fixed yields diminishing returns
- Models are much more compute-efficient when scaled in all dimensions together

Original recommendation: to optimize test loss, use more compute to train bigger models on the same data.

### Chinchilla Scaling Laws (DeepMind, 2022)

Hoffman et al. revised these recommendations significantly. Their finding: **Kaplan-era models were substantially undertrained**. GPT-3 (175B parameters) was trained on 300B tokens. According to Chinchilla, the optimal training for 175B parameters at that compute budget is approximately 3.5T tokens.

**Chinchilla-optimal rule of thumb:**
```
Optimal tokens ≈ 20× the number of parameters

Examples:
  7B parameters  → ~140B tokens optimal
  13B parameters → ~260B tokens optimal
  70B parameters → ~1.4T tokens optimal
```

But this is the compute-optimal recipe for training cost, not for inference cost. If you intend to run inference at scale, it's often better to train a smaller model for longer — a smaller model that has seen more data will match a larger undertrained model in quality while being much cheaper to run.

**Modern practice:** Llama 3 (8B) was trained on 15T tokens — far beyond Chinchilla-optimal for training, because the 8B model is intended for widespread inference deployment. DeepSeek similarly over-trains on data relative to the Chinchilla recipe.

---

## Model Families

Understanding the major model families, their architectures, and their practical trade-offs is essential for making informed decisions in production.

### Model Comparison Table (Early 2026)

| Model | Provider | Params | Context | Strengths | Pricing (input/output per 1M) |
|---|---|---|---|---|---|
| GPT-4o | OpenAI | ~200B MoE | 128K | Multimodal, fast, versatile | $2.50 / $10.00 |
| GPT-4o-mini | OpenAI | ~8B? | 128K | Cost-effective, fast | $0.15 / $0.60 |
| Claude Opus 4 | Anthropic | Unknown | 200K | Best reasoning, long context | $15.00 / $75.00 |
| Claude Sonnet 4 | Anthropic | Unknown | 200K | Best value at capable tier | $3.00 / $15.00 |
| Claude Haiku 3.5 | Anthropic | Unknown | 200K | Fast, cheap, instruction-following | $0.80 / $4.00 |
| Gemini 1.5 Pro | Google | Unknown | 1M–2M | Longest context, multimodal | $1.25 / $5.00 |
| Gemini Flash | Google | Unknown | 1M | Cheapest multimodal | $0.075 / $0.30 |
| Llama 3.1 405B | Meta | 405B | 128K | Best open-source | Free (self-hosted) |
| Llama 3.1 70B | Meta | 70B | 128K | Balance of quality and cost | Free (self-hosted) |
| Llama 3.1 8B | Meta | 8B | 128K | Fast, lightweight open-source | Free (self-hosted) |
| DeepSeek-V3 | DeepSeek | 671B MoE | 128K | Frontier quality, low cost | Very low (API) |
| Mistral Large | Mistral | Unknown | 128K | European provider, competitive | Moderate |
| Qwen 2.5 72B | Alibaba | 72B | 128K | Strong code, multilingual | Free (self-hosted) |

### Architecture Differences Across Families

**GPT-4 class (OpenAI):**
- Mixture of Experts (MoE) architecture (not confirmed but widely believed)
- Strong tool use and structured output support
- tiktoken tokenization
- Excellent coding performance

**Claude (Anthropic):**
- Constitutional AI training approach for safety
- Very long context (200K) with strong performance at long contexts
- Particularly good at following complex instructions
- SentencePiece-based tokenization

**Gemini (Google):**
- Native multimodal architecture (not add-on vision)
- Longest available context (up to 2M tokens)
- Tight integration with Google services
- Strong at reasoning over very long documents

**Llama (Meta, open-weight):**
- Released weights publicly under a permissive license
- RoPE positional embeddings, SwiGLU activation, GQA (Llama 3)
- Community-maintained ecosystem: GGUF formats, fine-tuning guides, deployment tools
- Privacy-safe: you can run entirely on your own infrastructure
- Used as base for thousands of community fine-tunes

**DeepSeek (DeepSeek AI):**
- MoE architecture with very efficient training
- Competitive with frontier models at a fraction of the cost
- Reasoning variant (DeepSeek-R1) trained with RL for chain-of-thought

**Mistral:**
- European provider with data residency options
- Sliding window attention (Mistral 7B) and MoE (Mixtral)
- Strong on code and instruction-following

### Choosing a Model Family

Consider these four axes:

1. **Capability:** For most tasks, frontier models (GPT-4o, Claude Sonnet, Gemini Pro) are broadly comparable. Differences emerge at the margins — specific task types, edge cases, long-context performance. Benchmarks provide directional guidance; always eval on your specific task.

2. **Cost:** The gap between model tiers is 5–20×. At scale, using the cheapest model that meets your quality bar is the dominant cost optimization.

3. **Latency:** Smaller models are faster. A Haiku-class model for classification can return in 100–300ms; Opus-class models may take 2–5 seconds.

4. **Deployment constraints:** Data residency requirements may force you to specific providers or self-hosting. Maximum context window needs. Required capabilities (vision, code execution, structured output). Regulatory considerations (GDPR, HIPAA).

**Default approach:** Start with a capable model to establish a quality ceiling, build evals, then attempt to downgrade to a cheaper model while monitoring quality degradation.

---

## Key Parameters and Their Business Impact

### Token/Cost Quick Reference

| Operation | Typical Tokens | Cost Estimate (Sonnet pricing) |
|---|---|---|
| Simple classification | 200 in, 10 out | ~$0.00060 |
| Short Q&A response | 500 in, 100 out | ~$0.00300 |
| RAG response | 2000 in, 400 out | ~$0.01200 |
| Long document summary | 8000 in, 500 out | ~$0.03150 |
| Agent turn (with tools) | 3000 in, 300 out | ~$0.01350 |

### Recommended Parameter Presets

| Task | Temperature | Top-p | Max Tokens | Notes |
|---|---|---|---|---|
| Classification | 0 | 1.0 | 10–50 | Deterministic |
| Entity extraction | 0 | 1.0 | 100–300 | Deterministic |
| Summarization | 0.3 | 1.0 | 500–2000 | Slight creativity OK |
| Q&A (factual) | 0 | 1.0 | 500–1500 | Deterministic |
| Chat assistant | 0.7 | 1.0 | 1000–4000 | Conversational |
| Creative writing | 0.9 | 0.95 | 2000+ | More randomness |
| Code generation | 0 | 1.0 | 1000–4000 | Deterministic |
| Brainstorming | 1.0 | 0.95 | 500–2000 | Maximum variety |

---

## Cost Estimation

### Per-Request Formula

```
cost = (input_tokens × input_price_per_token) + (output_tokens × output_price_per_token)
```

### Worked Example: Customer Support Chatbot

```
Feature: Customer support chatbot
Requests/day:     10,000
Avg input tokens:  2,000 (system prompt + history + user message)
Avg output tokens: 400

Using Claude Sonnet ($3/1M input, $15/1M output):
  Input cost:  10,000 × 2,000 × $3 / 1,000,000   = $60/day
  Output cost: 10,000 × 400 × $15 / 1,000,000     = $60/day
  Total:                                            = $120/day = $3,600/month

Using GPT-4o-mini ($0.15/1M input, $0.60/1M output):
  Input cost:  10,000 × 2,000 × $0.15 / 1,000,000 = $3/day
  Output cost: 10,000 × 400 × $0.60 / 1,000,000   = $2.40/day
  Total:                                            = $5.40/day = $162/month

Savings from routing 80% to mini, 20% to Sonnet:
  0.80 × $5.40 + 0.20 × $120 = $4.32 + $24.00 = $28.32/day = $850/month
  (vs $3,600/month all-Sonnet → 76% savings)
```

---

## Practice Exercises

The following exercises in `exercises.py` directly practice concepts from this file:

- **Exercise 1: Multi-Model Cost Estimator** -- Uses the per-request cost formula from the "Cost Estimation" section and the pricing data from the "Model Comparison Table." You will implement `estimate_request_cost()` which mirrors the worked example in "Cost Estimation" but adds prompt caching discounts and batch API discounts. The `find_cheapest_model()` function practices the model selection decision described in "Choosing a Model Family."

- **Exercise 2: Model Router** -- Directly applies the model routing concepts from "Choosing a Model Family" (capability, cost, latency, deployment constraints). The `infer_task_type()` function classifies requests to route them to appropriate model tiers per the "Recommended Parameter Presets" table. The `route_request()` function implements the "default approach: start with capable model, then downgrade" pattern.

- **Exercise 5: Parameter Configuration Designer** -- Uses the "Recommended Parameter Presets" table to design generation parameters for different task types (classification, code, creative writing, etc.). Each sub-function requires choosing temperature, top-p, max_tokens, and penalties appropriate for the task.

See also `examples.py` sections 1 (Token Counting and Cost Estimation), 2 (Model Selection / Routing), and 4 (Parameter Tuning Examples) for runnable reference implementations of these patterns.

---

## Interview Q&A: Training and Model Families

**Q: Explain the training pipeline: pre-training, SFT, RLHF.**

Pre-training is the expensive stage: train on trillions of tokens with a next-token prediction objective. This teaches language, facts, reasoning, and code but produces a text completer, not an assistant. SFT comes next: train on (instruction, response) pairs to teach the conversational format and instruction-following. Finally, alignment via RLHF or DPO teaches the model to prefer helpful, harmless, honest responses — human raters rank outputs, a reward model is trained on those preferences, and the LLM is optimized against it. DPO is simpler: directly optimize on preference pairs without a separate reward model.

**Q: What are the Chinchilla scaling laws and why do they matter?**

The Chinchilla paper (Hoffman et al., 2022) showed that earlier models were significantly undertrained relative to their parameter count. The optimal training recipe allocates roughly 20 tokens per parameter (e.g., a 70B model is optimally trained on ~1.4T tokens). Models trained before Chinchilla used far fewer tokens for their size and left significant performance on the table. However, this is compute-optimal for training, not inference-optimal — production models often train smaller architectures on much more data than Chinchilla-optimal to minimize inference cost.

**Q: When would you choose open-source models over API providers?**

Open-source (Llama, Mistral, Qwen) when: data cannot leave your network (HIPAA, GDPR, trade secrets), you need deep customization or fine-tuning at scale, you want to avoid vendor lock-in and provider pricing risk, or you have the infrastructure team to operate self-hosted inference. API providers (OpenAI, Anthropic, Google) when: you need the absolute capability frontier, you want zero infrastructure management, or you are moving quickly and operational complexity is not acceptable yet.

**Q: How do you compare models for a specific task?**

Benchmarks are directional but not definitive — models are sometimes fine-tuned to score well on popular benchmarks. For any meaningful decision, build a test set of 50–200 examples representative of your actual task (with ground truth answers) and run every candidate model against it with the same prompt. Compare on your own metrics. This takes a day of effort but produces trustworthy results. Cost and latency are also first-class decision criteria, not afterthoughts.

**Q: What is the alignment tax?**

Alignment (RLHF/DPO) trades raw capability for behavioral compliance. A perfectly aligned model that refuses many requests is less useful than a perfectly aligned model that handles them appropriately. Early RLHF implementations sometimes made models more verbose, sycophantic, or over-cautious relative to the pre-alignment base. Modern alignment is much better calibrated, but the tension remains — the model is being optimized for human approval signals, which don't perfectly correlate with task performance.
