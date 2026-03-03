# 01 — Fine-Tuning Fundamentals

## When to Fine-Tune

Fine-tuning is not the first tool to reach for. It is the right tool in specific situations, and the wrong tool in others.

### Decision Tree

```
Start here: Does prompt engineering solve the problem?
├── YES → Use prompt engineering (cheapest, fastest to iterate)
└── NO → What is the problem?
    ├── Model needs knowledge it doesn't have
    │   └── Use RAG (not fine-tuning — knowledge injection via fine-tuning is unreliable)
    ├── Model produces wrong style/format consistently
    │   └── Try few-shot examples first; if still wrong → consider fine-tuning
    ├── Model can't follow complex domain-specific instructions
    │   └── Consider fine-tuning for improved instruction following
    ├── Model is too large/expensive for a narrow task
    │   └── Fine-tune a smaller model to match the larger model's performance on this task
    └── Model generates wrong behavior even with good prompts
        └── Fine-tuning is appropriate
```

### Approach Comparison

| Approach | Cost | Speed to Deploy | Quality Ceiling | Best For |
|---|---|---|---|---|
| Zero-shot prompting | Lowest | Hours | Low-Medium | Simple tasks |
| Few-shot prompting | Very low | Hours | Medium | Classification, extraction |
| RAG | Low-Medium | Days | High | Knowledge-grounded tasks |
| Fine-tuning (API) | Medium | Days | High | Behavior/style adaptation |
| Fine-tuning (custom) | High | Weeks | Highest | Domain-specific excellence |
| Training from scratch | Very high | Months | Maximum | Research, specialized domain |

### The Anti-Pattern: Fine-Tuning for Knowledge

**Do not fine-tune to inject facts.** This is the most common fine-tuning mistake.

- Facts memorized during fine-tuning are recalled inconsistently (the model may recall them correctly 80% of the time and hallucinate 20% of the time)
- Training data goes stale — you need to retrain every time the knowledge changes
- RAG is specifically designed to solve the knowledge grounding problem reliably

**Fine-tune for:** Output format, style, tone, domain-specific reasoning patterns, instruction-following behavior, task specialization.

**Use RAG for:** Current information, updatable knowledge, facts that need to be traceable to sources.

---

## Fine-Tuning Approaches

### Full Fine-Tuning

Train all model parameters. Every weight in the model gets updated.

**Memory requirements:**
- Model weights: ~2 bytes/param (BF16)
- Gradients: ~4 bytes/param (FP32)
- Optimizer state (Adam): ~8 bytes/param (two moments)
- Total: ~14 bytes/param minimum + activation memory

For a 7B model: 7B × 14 bytes ≈ 98 GB minimum. This requires multiple high-end GPUs.

**When full fine-tuning is appropriate:**
- You have significant compute resources
- The task requires large changes to model behavior
- You need maximum quality and are not compute-constrained
- You're training a base model for continued pre-training

### LoRA (Low-Rank Adaptation)

LoRA is the most commonly used fine-tuning method for practical applications. Instead of updating the full weight matrix W, LoRA adds two small trainable matrices A and B:

```
Standard fine-tuning: W_new = W + ΔW
LoRA:                 W_new = W + A × B (where A: d×r, B: r×d, r << d)

For W of dimension 4096×4096 (16.7M params):
  LoRA with r=16: A is 4096×16, B is 16×4096 → 131K params (0.8% of original)
```

**Key parameters:**
- `r` (rank): 8–64 typical. Higher rank = more capacity = more memory. Start with r=16.
- `alpha`: Scaling factor, typically set to 2× rank. Controls the magnitude of the update.
- `target_modules`: Which weight matrices to adapt. Common: Q, K, V, and output projection in attention; sometimes FFN layers.

**Advantages:**
- Trains 0.1–1% of parameters → dramatically lower memory and compute
- Base model weights stay frozen → no forgetting of general capabilities
- Adapter is small (MBs, not GBs) → easy to store and swap
- Can load multiple LoRA adapters for different tasks, sharing the base model

```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=16,                           # LoRA rank
    lora_alpha=32,                  # LoRA scaling (typically 2× rank)
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],  # Which layers to adapt
    lora_dropout=0.05,              # Dropout for regularization
    bias="none",                    # Don't train bias terms
    task_type="CAUSAL_LM"           # Language modeling task
)

model = get_peft_model(base_model, lora_config)
model.print_trainable_parameters()
# trainable params: 6,815,744 || all params: 6,744,547,328 || trainable%: 0.10
```

### QLoRA

QLoRA (Quantized LoRA) combines base model quantization with LoRA adapters. The base model is loaded in 4-bit precision, drastically reducing memory. LoRA adapters are trained in 16-bit precision on top of the frozen quantized model.

```python
from transformers import BitsAndBytesConfig
import torch

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,       # Nested quantization for extra memory savings
    bnb_4bit_quant_type="nf4",            # NormalFloat4 — best for LLM weights
    bnb_4bit_compute_dtype=torch.bfloat16  # Compute in BF16 despite 4-bit storage
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Meta-Llama-3-8B",
    quantization_config=bnb_config,
    device_map="auto"
)
```

**QLoRA's key achievement:** Fine-tune a 65B model on a single 48GB GPU that would normally require 8× A100 80GB. This democratized fine-tuning of large models.

**Quality tradeoff:** QLoRA is slightly lower quality than LoRA with full-precision base model, due to quantization noise. The gap is small for most tasks and the memory savings are enormous.

### Other Adapter Methods

| Method | Trainable Params | Mechanism | Best For |
|---|---|---|---|
| LoRA | 0.1–1% | Low-rank weight decomposition | General fine-tuning (default) |
| QLoRA | 0.1–1% | LoRA on quantized base | Memory-constrained fine-tuning |
| Prefix Tuning | 0.01–0.1% | Trainable prefix tokens | Style/task prefix |
| Prompt Tuning | 0.001–0.01% | Soft prompt tokens | Very efficient; lower quality |
| IA3 | 0.001–0.01% | Rescaling activations | Very few-shot adaptation |

LoRA is the dominant choice for practical fine-tuning. Other methods are useful in extreme memory constraints or specific research contexts.

---

## Data Preparation

Data quality is the most important factor in fine-tuning success. "Data preparation is 80% of the work" is a cliché because it's true.

### Data Formats

**OpenAI Chat Format (SFT):**
```jsonl
{"messages": [{"role": "system", "content": "You are a helpful coding assistant."}, {"role": "user", "content": "Write a function to calculate factorial."}, {"role": "assistant", "content": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)"}]}
{"messages": [{"role": "user", "content": "Explain recursion."}, {"role": "assistant", "content": "Recursion is a programming technique where a function calls itself..."}]}
```

**Alpaca Format (instruction/input/output):**
```jsonl
{"instruction": "Classify the sentiment of this review.", "input": "The product exceeded my expectations!", "output": "positive"}
{"instruction": "Summarize the following text in one sentence.", "input": "The company announced...", "output": "The company launched a new product targeting enterprise customers."}
```

**DPO Preference Format:**
```jsonl
{"prompt": "Write a professional email declining a meeting.", "chosen": "Dear [Name],\nThank you for the invitation...", "rejected": "Hey, can't make it, too busy."}
{"prompt": "Explain quantum entanglement simply.", "chosen": "Quantum entanglement is when two particles...", "rejected": "It's complicated quantum physics stuff."}
```

### How Much Data Do You Need?

| Task Complexity | Minimum | Typical | Notes |
|---|---|---|---|
| Style/format changes | 50–200 | 200–500 | Simple behavioral change |
| Task specialization | 200–500 | 500–2,000 | Classification, extraction |
| Domain adaptation | 1,000+ | 5,000–50,000 | Complex domain-specific tasks |
| Instruction following | 10,000+ | 50,000–500,000 | General instruction following |

**Quality vs. quantity:** 500 carefully crafted examples that cover the task's key variations will outperform 50,000 mediocre examples. Before scaling data collection, ensure your quality criteria are high and consistently applied.

### Data Quality Checklist

```
Coverage and Diversity:
□ Does the data cover all major task variations?
□ Are edge cases and failure modes represented?
□ Is there sufficient variety in inputs (length, style, complexity)?
□ Does the distribution match what you'll see in production?

Label Quality:
□ Is "good" output clearly defined and consistently applied?
□ Would different annotators agree on what's correct?
□ Are there clear annotation guidelines?
□ Have labels been spot-checked by domain experts?

Data Health:
□ Duplicates removed?
□ Near-duplicates removed or managed (they inflate metrics)?
□ Data from the correct domain/style/language?
□ No PII or sensitive information in training data?
□ Is there a holdout test set (≥10% of data)?

Format:
□ Correct JSONL format?
□ Messages properly structured (role/content pairs)?
□ Special tokens handled correctly?
□ Appropriate length distribution for the task?
```

### Synthetic Data Generation

Use a stronger model (GPT-4, Claude Opus) to generate training data for a weaker model:

```python
def generate_training_examples(
    task_description: str,
    few_shot_examples: list[dict],
    n_examples: int = 100
) -> list[dict]:
    examples = []

    few_shot_str = "\n\n".join([
        f"Input: {ex['input']}\nOutput: {ex['output']}"
        for ex in few_shot_examples
    ])

    for _ in range(n_examples):
        prompt = f"""Generate a new training example for this task:

Task: {task_description}

Example format:
{few_shot_str}

Generate ONE new diverse example following the same format.
The input should be different from the examples above.
The output should be high quality and consistent with the task.

Input:"""

        response = llm_call_strong_model(prompt)
        # Parse and validate the generated example
        example = parse_example(response)
        if validate_example(example):
            examples.append(example)

    return examples
```

**Risks of synthetic data:**
- Model collapse: if the training data is too similar to the model's existing outputs, it reinforces existing behaviors rather than changing them
- Distribution shift: synthetic data may not cover the full production distribution
- Quality ceiling: you can't exceed the teacher model's quality
- Hallucination: the generator model may produce incorrect outputs

**Mitigation:** Mix synthetic with human-curated data; use diversity sampling; validate generated outputs with a separate model or human spot-check.

---

## Training Fundamentals

### Key Hyperparameters

| Hyperparameter | Typical Range | Effect |
|---|---|---|
| Learning rate | 1e-5 to 1e-4 | Too high → unstable; too low → slow/no learning |
| Batch size | 4–64 (effective with gradient accumulation) | Larger → more stable gradients, more memory |
| Epochs | 1–5 | More → overfitting risk; usually 1–3 for SFT |
| Warmup steps | 5–10% of total steps | Prevents early divergence |
| Max sequence length | 1,024–8,192 | Match your task; longer = more memory |
| Gradient accumulation | 4–16 steps | Simulate larger batch on limited GPU |
| Weight decay | 0.01–0.1 | L2 regularization; prevents overfitting |

### Learning Rate Selection

```
Too high (1e-3): Loss spikes, training unstable, model breaks
Appropriate (1e-4 to 1e-5): Loss decreases smoothly
Too low (1e-7): Essentially no learning; loss barely moves

For LoRA:
  Start at: 1e-4 (higher than full fine-tuning because fewer params)
  If unstable: reduce to 5e-5
  If not learning: try 2e-4

For full fine-tuning:
  Start at: 1e-5
  Common range: 5e-6 to 2e-5
```

### Detecting Overfitting

```python
def plot_training_progress(train_losses: list, val_losses: list):
    """
    Watch for these patterns:

    HEALTHY:
    Train loss: ↓ (decreasing)
    Val loss:   ↓ (decreasing, may be slightly higher than train)

    OVERFITTING:
    Train loss: ↓ (still decreasing)
    Val loss:   → then ↑ (plateaus then increases)
    Action: Stop training, use checkpoint from before val loss inflection

    UNDERFITTING:
    Train loss: → (barely decreasing)
    Val loss:   → (not improving)
    Action: Increase learning rate, add more data, train longer
    """
```

### Data Splitting

```
Standard split:
  Train:      80%   (used for weight updates)
  Validation: 10%   (used for hyperparameter tuning and early stopping)
  Test:       10%   (used only for final evaluation — never tuning!)

For small datasets (<500 examples):
  Consider cross-validation instead of fixed split
  Or: Train: 90%, Test: 10% (skip validation, use train loss as proxy)
```

---

## GPU Requirements and Cost

### Memory by Fine-Tuning Method

| Method | 7B Model | 13B Model | 70B Model | Notes |
|---|---|---|---|---|
| Full fine-tuning (BF16) | ~112 GB | ~200 GB | ~1.1 TB | Requires multiple A100 80GB |
| LoRA (BF16 base) | ~28 GB | ~52 GB | ~280 GB | 1–2 A100 80GB for LoRA |
| QLoRA (4-bit base) | ~12 GB | ~20 GB | ~48 GB | Single A100 for LoRA, 70B on 2× A100 |

### GPU Quick Reference

| GPU | VRAM | Best For | Approx Cloud Cost |
|---|---|---|---|
| T4 16GB | 16 GB | QLoRA 7B, inference | $0.35/hr (GCP) |
| L4 24GB | 24 GB | QLoRA 7B-13B, light LoRA 7B | $0.70/hr (GCP) |
| A10G 24GB | 24 GB | QLoRA 13B, LoRA 7B | $1.00/hr (AWS) |
| A100 40GB | 40 GB | LoRA 13B-70B, QLoRA 70B | $2.50/hr |
| A100 80GB | 80 GB | LoRA 70B, full FT 7B | $3.50/hr |
| H100 80GB | 80 GB | Full FT 70B, production training | $5–8/hr |

### Cost Estimates

| Scenario | Config | Estimated Cost |
|---|---|---|
| QLoRA 7B, 10K examples, 3 epochs | Single A10G, ~3 hours | $3–5 |
| LoRA 70B, 10K examples, 1 epoch | 2× A100 80GB, ~6 hours | $50–80 |
| API fine-tuning (OpenAI, 7B-class) | 100K tokens per epoch, 3 epochs | $5–20 |
| Full fine-tune 7B, 100K examples | 8× A100 80GB, ~12 hours | $400–600 |

### Training Platforms

**API-based fine-tuning (easiest):**
- OpenAI: Fine-tune GPT-4o-mini and GPT-3.5-Turbo via API. Pay per token.
- Anthropic: Fine-tuning Claude models available for enterprise customers
- Fireworks AI, Together AI: Llama fine-tuning via API

**Cloud GPU (most control):**
- Lambda Labs: Good price, easy setup
- Modal: Serverless GPU, good for sporadic training
- Google Colab Pro+ / Kaggle: T4/V100 free or cheap
- AWS SageMaker, GCP Vertex AI: Enterprise-grade, more complex setup

---

## Evaluation After Fine-Tuning

### Quantitative Metrics

| Metric | Use Case | Tool |
|---|---|---|
| Task accuracy | Classification | Exact match on test set |
| F1 score | Extraction, classification | Standard NLP metric |
| ROUGE | Summarization | Standard summarization metric |
| Code pass rate | Code generation | Pass@1, Pass@10 with unit tests |
| LLM-as-judge | Open-ended quality | GPT-4o or Claude as judge |
| Human eval | Final calibration | Manual review |

### Evaluation Hierarchy

```
Level 1: Training metrics (necessary but not sufficient)
  → Training loss, validation loss
  → Detect overfitting; don't use for task quality

Level 2: Task-specific metrics on held-out test set
  → Accuracy, F1, pass@k on your actual task
  → This is the primary quality signal

Level 3: Comparison to baseline
  → Compare to the best prompting approach
  → If fine-tuning doesn't beat prompting, rethink

Level 4: General capability regression check
  → Test on standard benchmarks (MMLU, HellaSwag)
  → Fine-tuning can degrade general capabilities

Level 5: Human evaluation
  → Sample 50-100 outputs, have domain experts review
  → Catches issues that automated metrics miss
```

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Approach Selection** -- Apply the decision tree from "When to Fine-Tune" to classify scenarios as prompt engineering, RAG, fine-tuning, or distillation. Directly practices the approach comparison table and anti-pattern awareness.
- **Exercise 2: Data Preparation Pipeline** -- Build a full data cleaning, validation, deduplication, formatting, and splitting pipeline. Practices the data formats (OpenAI chat, Alpaca), the data quality checklist, and train/val/test splitting.
- **Exercise 3: Synthetic Data Generation Pipeline Design** -- Design prompts and quality checks for generating training data with a teacher model. Practices the synthetic data generation pattern and its risks/mitigations.
- **Exercise 5: Training Cost and GPU Requirements Calculator** -- Calculate VRAM needs, training time, and cost using the memory formulas from "Fine-Tuning Approaches" and the GPU/cost tables.
- **Exercise 6: LoRA Configuration Designer** -- Select rank, alpha, target modules, dropout, and QLoRA based on constraints. Directly practices LoRA parameter selection from "LoRA (Low-Rank Adaptation)" and "QLoRA".

See also `examples.py` for reference implementations:
- Section 1 "DATA PREPARATION PIPELINE" -- complete data cleaning, formatting, dedup, and splitting code
- Section 6 "FINE-TUNING DECISION ENGINE" -- full decision tree implementation
- Section 7 "COST ESTIMATOR" -- training cost and GPU selection logic

---

## Interview Q&A: Fine-Tuning Fundamentals

**Q: When would you fine-tune vs. use RAG vs. prompt engineering?**

Start with prompt engineering — it is cheapest and fastest to iterate on. If the prompting ceiling is not high enough, add RAG for knowledge grounding or fine-tuning for behavioral changes. RAG handles knowledge: when the model needs information not in its training data, or information that changes frequently or must be traceable to sources. Fine-tuning handles behavior: when you need the model to adopt a specific style, follow complex formatting rules consistently, or perform well on a narrow domain-specific task. The anti-pattern: fine-tuning for knowledge injection — it's unreliable (the model may not recall specific facts consistently), expensive, and the data goes stale. These approaches combine: fine-tune a model for domain-specific reasoning patterns, then use RAG to give it current facts.

**Q: Explain LoRA. Why is it preferred over full fine-tuning?**

LoRA adds small trainable matrices to the existing model weights rather than modifying all parameters. Instead of updating W directly, the update is decomposed into W + AB where A and B have a much smaller rank (typically 8–64) than the original matrix. Only A and B are trained; the original weights stay frozen. The advantages: memory (train 0.1–1% of parameters), speed (fewer params = faster training), serving flexibility (load the base model once, swap different LoRA adapters for different tasks), storage (each adapter is MBs, not GBs). Quality is competitive with full fine-tuning for most tasks. QLoRA goes further by quantizing the base model to 4-bit and applying LoRA on top, enabling 70B model fine-tuning on a single A100.

**Q: How do you prepare data for fine-tuning?**

Quality over quantity. 1,000 high-quality examples will outperform 100,000 mediocre ones. The process: start by defining what "good" looks like — write golden examples manually. Collect data from production logs, human annotations, or synthetic generation (use a stronger model to generate training data for a weaker one). Clean rigorously: remove duplicates, filter low-quality examples, ensure diversity across input types and edge cases. Always hold out a test set (at least 10% of data) for evaluation. Common pitfalls: training data too homogeneous (model overfits to the common case), inconsistent labeling (different people define "good" differently), not enough edge cases. Data preparation is typically 80% of the work.
