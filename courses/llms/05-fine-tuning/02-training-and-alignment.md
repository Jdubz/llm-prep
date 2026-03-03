# 02 — Training and Alignment

## RLHF and DPO

The alignment stage is what transforms a text-completing pre-trained model into a helpful, honest, and harmless assistant. Understanding this stage is increasingly important for LLM engineers, especially as fine-tuning is used to align domain-specific models.

### Why RLHF and DPO Exist

Pre-trained models are powerful text completers that optimize for likelihood of next tokens, not human preferences. They will confidently complete toxic text, generate plausible-sounding misinformation, and produce outputs that are technically correct but unhelpful. Alignment training corrects these tendencies.

**The alignment problem in concrete terms:**
```
Pre-trained model given prompt "How do I pick a lock?":
  → Will complete naturally: "Here are the steps: 1. Insert a tension wrench..."

Desired aligned behavior:
  → "I notice you're asking about lock picking. If you're locked out of
     your own home, I recommend calling a licensed locksmith. Can you
     tell me more about your situation?"
```

### RLHF Pipeline

RLHF (Reinforcement Learning from Human Feedback) involves three training stages after pre-training:

```
Stage 1: Supervised Fine-Tuning (SFT)
  Input: (instruction, response) pairs from high-quality demonstrations
  Goal: Teach the model the conversational format and basic helpful behavior

Stage 2: Reward Model Training
  Input: Pairs of model responses to the same prompt, with human preferences
         (response A, response B, "A is better")
  Goal: Train a model to predict human preferences → reward signal

Stage 3: RL Optimization (PPO)
  Input: The SFT model + the reward model
  Goal: Optimize the SFT model to maximize reward model scores
        while staying close to the SFT model (KL penalty prevents reward hacking)

  Objective:
  maximize: E[reward_model(response)] - β * KL(policy, reference_policy)

  Where β controls how much the policy can deviate from the reference SFT model
```

**Challenges with RLHF:**
- Requires maintaining two models (LLM + reward model) during training
- PPO is notoriously unstable — requires careful tuning of many hyperparameters
- Reward hacking: the model finds ways to maximize the reward signal that don't correspond to genuine quality improvement
- Expensive: multiple training stages, significant compute

### DPO: The Simpler Alternative

DPO (Direct Preference Optimization) achieves similar results without a separate reward model. The mathematical insight: under RLHF, the optimal reward model can be expressed as a closed-form function of the policy. This allows you to directly optimize on preferences without the RL training loop.

**DPO training objective:**
```python
# DPO loss function
def dpo_loss(
    policy_model,
    reference_model,
    prompt: str,
    chosen: str,
    rejected: str,
    beta: float = 0.1
) -> float:
    # Log probabilities of chosen and rejected responses
    log_prob_chosen_policy = policy_model.log_prob(chosen | prompt)
    log_prob_rejected_policy = policy_model.log_prob(rejected | prompt)

    log_prob_chosen_ref = reference_model.log_prob(chosen | prompt)
    log_prob_rejected_ref = reference_model.log_prob(rejected | prompt)

    # Reward implicitly defined by the policy
    chosen_reward = beta * (log_prob_chosen_policy - log_prob_chosen_ref)
    rejected_reward = beta * (log_prob_rejected_policy - log_prob_rejected_ref)

    # DPO loss: maximize the gap between chosen and rejected
    loss = -log_sigmoid(chosen_reward - rejected_reward)
    return loss
```

**DPO vs RLHF comparison:**

| Aspect | RLHF | DPO |
|---|---|---|
| Stages | 3 (SFT → RM → PPO) | 2 (SFT → DPO) |
| Separate reward model | Yes | No |
| Training stability | Difficult | Much easier |
| Implementation complexity | High | Medium |
| Quality | State of the art | Comparable for most tasks |
| Flexibility | High (complex rewards) | Lower |
| Who uses it | OpenAI (historically), others | Anthropic, Meta (Llama), most practitioners |

**When RLHF is still better:** Complex reward signals that DPO can't easily capture; online learning where the reward model is updated during training; applications where you want to separately evaluate and update the reward model.

### DPO Variants

| Variant | Key Change | When to Use |
|---|---|---|
| **DPO** | Original; optimizes directly on preferences | General alignment |
| **IPO** (Identity Preference Optimization) | More robust to overfitting on small datasets | Small preference datasets |
| **KTO** (Kahneman-Tversky Optimization) | Uses absolute quality labels, not just pairs | When you have ratings, not comparisons |
| **ORPO** (Odds Ratio Preference Optimization) | No separate reference model needed | Memory-constrained training |
| **SimPO** | No reference model, length normalization | Simple and effective |

For most practical DPO fine-tuning, **standard DPO** or **SimPO** are good starting points.

---

## Catastrophic Forgetting

When you fine-tune a model on a specific task, it often loses performance on tasks it previously handled well. This is catastrophic forgetting (or catastrophic interference).

**Why it happens:** The model's weights are optimized for the training distribution. Updates that improve task-specific performance can overwrite representations needed for other capabilities.

### Detection

Test on standard benchmarks before and after fine-tuning:

```python
# Benchmarks to run before and after fine-tuning
evaluation_benchmarks = [
    ("MMLU", test_mmlu),           # General knowledge and reasoning
    ("HellaSwag", test_hellaswag), # Common sense reasoning
    ("TruthfulQA", test_truthfulqa), # Truthfulness
    ("GSM8K", test_gsm8k),         # Math reasoning
    ("Custom task", test_custom),  # Your specific fine-tuning task
]

for name, test_fn in evaluation_benchmarks:
    before_score = test_fn(base_model)
    after_score = test_fn(fine_tuned_model)
    delta = after_score - before_score
    print(f"{name}: {before_score:.1%} → {after_score:.1%} ({delta:+.1%})")
```

**Acceptable degradation:** 1–3% on general benchmarks. More than 5% degradation indicates significant forgetting.

### Mitigation Strategies

**1. LoRA (most effective for most cases)**
Frozen base weights cannot forget. LoRA adapters modify behavior without touching the original weights:
```python
# LoRA preserves the base model's capabilities because the base weights are unchanged
# The adapter only adds new capability on top
```

**2. Replay Buffer (Experience Replay)**
Mix general-domain data into the fine-tuning dataset to maintain general capabilities:
```python
def create_mixed_dataset(
    task_data: list[dict],
    general_data: list[dict],
    task_fraction: float = 0.8
) -> list[dict]:
    """Mix task-specific and general data to prevent catastrophic forgetting."""
    n_task = int(len(task_data))
    n_general = int(n_task * (1 - task_fraction) / task_fraction)

    general_sample = random.sample(general_data, min(n_general, len(general_data)))
    mixed = task_data + general_sample
    random.shuffle(mixed)
    return mixed
```

**3. Lower Learning Rate**
Smaller updates preserve more of the original representations:
```
Full fine-tuning: lr = 1e-5
For forgetting prevention: lr = 5e-6 to 1e-6
```

**4. Early Stopping**
Monitor general capability benchmarks during training; stop when they degrade beyond threshold:
```python
def early_stopping_with_forgetting_check(
    val_loss: float,
    forgetting_metrics: dict,
    forgetting_threshold: float = 0.03
) -> bool:
    """Stop training if any general benchmark drops more than threshold."""
    for benchmark, (before, current) in forgetting_metrics.items():
        degradation = before - current
        if degradation > forgetting_threshold:
            print(f"Stopping: {benchmark} degraded by {degradation:.1%}")
            return True
    return False
```

**5. Elastic Weight Consolidation (EWC)**
Penalize changes to weights that are most important for previous tasks (computed via Fisher information):
```python
# Conceptually: add a regularization term to the loss
# L_total = L_task + λ * Σ_i F_i * (θ_i - θ*_i)²
# Where F_i is the importance of weight i for previous tasks (Fisher information)
# This is complex to implement; LoRA is usually simpler and nearly as effective
```

---

## The Alignment Tax

Fine-tuning and alignment sometimes trade raw capability for behavioral compliance. This tradeoff is called the alignment tax.

**Examples of alignment tax:**
- A model fine-tuned to be helpful and harmless may be more verbose (explaining its reasoning and caveats) than necessary
- Alignment may make the model less willing to engage with edge cases that are actually legitimate
- Models may exhibit sycophancy: agreeing with incorrect user assertions to be "helpful"

**Minimizing the alignment tax:**
1. High-quality, diverse training data that doesn't over-represent hedging and caveats
2. Calibrated refusals: the model should refuse genuinely harmful requests, not edge cases
3. DPO with carefully selected preferences that reward direct, accurate responses
4. Evals that measure both safety and utility — optimize for the full objective

---

## Continued Pre-Training

Continued pre-training (sometimes called domain-adaptive pre-training) further trains the base model on domain-specific text before SFT or RLHF. Unlike SFT, it uses the next-token prediction objective on raw text.

### When to Use

- You are building a model for a domain with highly specialized vocabulary and concepts (biomedical, legal, finance, code in a niche language)
- The base model's pre-training data had limited coverage of your domain
- You want to maximize domain-specific capability before instruction tuning

### How It Works

```python
# Continued pre-training uses next-token prediction on domain text
# No instruction/response format — just raw domain text

domain_texts = [
    "The company's EBITDA margin for Q3 was 23.4%, compared to...",
    "The plaintiff argued that the defendant breached the covenant...",
    "The compound showed IC50 values of 12nM against EGFR...",
]

# Train with the same objective as pre-training: predict the next token
# Loss = cross_entropy(model_output[:-1], tokens[1:])
```

### Practical Considerations

- **Data volume:** Need millions to billions of tokens for meaningful pre-training updates
- **Learning rate:** Very low — 1e-6 to 5e-6 to avoid catastrophic forgetting
- **Sequence length:** Use the maximum your infrastructure supports (longer = better for domain-specific patterns)
- **Deduplication:** Pre-training data must be deduplicated; duplicates are overrepresented and hurt quality
- **After pre-training:** Still need SFT to teach the model to follow instructions

**Real-world examples:**
- BioMedLM: pre-trained on PubMed papers, then instruction-tuned for biomedical QA
- CodeLlama: Llama pre-trained on additional code data, then fine-tuned for code tasks
- Legal-BERT: BERT continued pre-training on legal texts for legal NLP

---

## Model Merging

Model merging combines multiple fine-tuned models into a single model without any additional training. This enables combining specialized capabilities or creating efficient model variants.

### SLERP (Spherical Linear Interpolation)

The simplest and most common merging technique. Interpolates between two models in the weight parameter space:

```python
import torch

def slerp_merge(model_A: dict, model_B: dict, t: float = 0.5) -> dict:
    """
    Merge two models using spherical interpolation.
    t=0.0 → pure model A
    t=0.5 → equal mix
    t=1.0 → pure model B
    """
    merged = {}
    for key in model_A:
        if key in model_B:
            a = model_A[key].float()
            b = model_B[key].float()

            # Compute the angle between the weight vectors
            dot = torch.sum(a * b) / (torch.norm(a) * torch.norm(b))
            dot = torch.clamp(dot, -1, 1)
            theta = torch.acos(dot)

            if torch.abs(theta) < 1e-6:
                merged[key] = (1 - t) * a + t * b
            else:
                merged[key] = (
                    (torch.sin((1 - t) * theta) / torch.sin(theta)) * a +
                    (torch.sin(t * theta) / torch.sin(theta)) * b
                )
        else:
            merged[key] = model_A[key]

    return merged
```

**Use case:** Combining a helpful assistant fine-tune with a coding-specialized fine-tune to get a model that's good at both.

### TIES (Task Input Embedding Surgery) and DARE

Advanced merging methods for combining more than 2 models:

- **TIES:** Resolves parameter conflicts by taking the sign majority vote and magnitude-weighted average across merged models
- **DARE:** Randomly drops model deltas (makes parameters sparser) before merging, reducing interference between model updates

These methods are primarily used in research and by enthusiasts building merged models for Hugging Face. The mergekit library implements all major merging methods.

### LoRA Adapter Composition

LoRA adapters can be composed (not merged):

```python
# Loading multiple LoRA adapters for inference
from peft import PeftModel

base = AutoModelForCausalLM.from_pretrained("meta-llama/Meta-Llama-3-8B")
model = PeftModel.from_pretrained(base, "adapter_for_coding")
# Switch adapter at inference time
model.load_adapter("adapter_for_writing", adapter_name="writing")
model.set_adapter("writing")  # switch to writing adapter
```

This is a production pattern: one base model in GPU memory, multiple adapters that can be swapped without reloading the base model weights.

---

## Open-Source Fine-Tuning Stack

### HuggingFace Ecosystem (Most Common)

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer
from datasets import load_dataset

# 1. Load model and tokenizer
model_id = "meta-llama/Meta-Llama-3-8B"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto")

# 2. Apply LoRA
lora_config = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj", "v_proj"])
model = get_peft_model(model, lora_config)

# 3. Load dataset
dataset = load_dataset("your_dataset")

# 4. Train with SFTTrainer (handles formatting, packing, etc.)
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    args=TrainingArguments(
        output_dir="./output",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        save_strategy="epoch",
    ),
    train_dataset=dataset["train"],
    eval_dataset=dataset["test"],
)

trainer.train()
model.save_pretrained("./fine-tuned-model")
```

### Axolotl (YAML-based configuration)

```yaml
# axolotl_config.yml
base_model: meta-llama/Meta-Llama-3-8B
model_type: LlamaForCausalLM
tokenizer_type: LlamaTokenizer

datasets:
  - path: your_dataset.jsonl
    type: alpaca

load_in_4bit: true
adapter: lora
lora_r: 16
lora_alpha: 32
lora_target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj

sequence_len: 4096
micro_batch_size: 4
gradient_accumulation_steps: 4
num_epochs: 3
learning_rate: 0.0002
bf16: true

output_dir: ./outputs/my_finetune
```

```bash
axolotl train axolotl_config.yml
```

**Axolotl advantages:** Handles most boilerplate, well-tested configurations for common models, supports many dataset formats, good logging integration.

### LLaMA-Factory

Similar to Axolotl but with a web UI and broader model support. Good for teams that prefer a graphical interface or need to fine-tune many different models.

### Framework Comparison

| Framework | Setup Effort | Flexibility | Best For |
|---|---|---|---|
| HuggingFace (raw) | High | Maximum | Custom training loops |
| TRL (HF addon) | Medium | High | SFT and DPO specifically |
| Axolotl | Low | Medium | Most LoRA/QLoRA fine-tuning |
| LLaMA-Factory | Very low | Medium | Quick experiments, UI users |
| OpenAI API | Zero | Low | API fine-tuning without GPUs |

---

## Safety Considerations in Fine-Tuning

Fine-tuning can bypass safety alignments baked into the base model. This is a serious concern that responsible practitioners must address.

### How Fine-Tuning Bypasses Safety

```
Base model (well-aligned): Refuses harmful requests

After fine-tuning on:
- Datasets that contain harmful content
- Roleplay datasets with no safety constraints
- Instruction-following datasets where "follow all instructions" overrides safety

Result: Model may produce harmful outputs despite the base model's training
```

### Responsible Fine-Tuning Practices

1. **Audit training data:** Check for harmful content before training. Don't use datasets with unmoderated user content.
2. **Maintain safety training:** Include alignment examples in your fine-tuning data; don't remove them.
3. **Red-team after fine-tuning:** Test for harmful outputs using the same attacks as the base model's safety testing.
4. **Evaluate safety benchmarks:** Check SafetyBench, ToxicityPrompts, and similar benchmarks before and after fine-tuning.
5. **Document what you changed:** Model cards for fine-tuned models should describe what the fine-tuning changed and any known limitations.

### Legal and Compliance Considerations

- **Training data copyright:** Data you use for training may be subject to copyright. This is an active legal area.
- **Terms of service:** Many providers (OpenAI, Anthropic) prohibit using model outputs to train competing models. Read terms carefully before creating synthetic training data.
- **Export controls:** Models above certain capability thresholds may be subject to export control regulations (e.g., EAR in the US).
- **PII in training data:** Training on personal data may create compliance obligations under GDPR, CCPA, and similar regulations.

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Approach Selection** -- Requires understanding of when fine-tuning is appropriate vs. simpler alternatives, which connects to the alignment concepts here (e.g., knowing that DPO-based fine-tuning changes behavior, not knowledge).
- **Exercise 4: Evaluation Harness** -- Build a comparison harness for base vs. fine-tuned models. Practices the metrics tracking guidance from "What metrics do you track when fine-tuning?" (Interview Q&A) including per-category evaluation, regression detection, and quality-vs-baseline comparison.

See also `examples.py` for reference implementations:
- Section 5 "EVALUATION HARNESS" -- complete eval pipeline with exact match, ROUGE-L, per-class accuracy, and model comparison reporting

---

## Interview Q&A: Training and Alignment

**Q: What is DPO and how does it compare to RLHF?**

Both DPO and RLHF optimize a model to prefer better responses based on human preferences. RLHF is the older approach: train a reward model on human preference data (pairs where one response is preferred), then use PPO to fine-tune the LLM to maximize the reward. It's a three-stage process with significant engineering complexity and PPO instability. DPO achieves a similar outcome with a simpler two-stage process. The insight: the optimal reward model under RLHF can be expressed as a function of the policy itself, so you can skip the reward model and directly update the LLM weights on preference data. DPO produces comparable results for most use cases and is much simpler to implement. RLHF retains advantages for complex reward signals and online learning. DPO has become the default for most practitioners.

**Q: What is catastrophic forgetting and how do you prevent it?**

Catastrophic forgetting is when fine-tuning on a specific task causes the model to lose performance on tasks it previously handled well. It happens because weight updates optimized for the fine-tuning distribution overwrite representations needed for other capabilities. LoRA is the most effective mitigation: since the base weights are frozen, they cannot forget. For full fine-tuning, mix general-domain data into the training set (replay buffer), use a very low learning rate, and monitor general benchmarks during training with early stopping when they degrade. Always evaluate on standard benchmarks (MMLU, HellaSwag) before and after fine-tuning to quantify forgetting. Acceptable degradation: 1–3%. More than 5% indicates significant forgetting.

**Q: What metrics do you track when fine-tuning?**

Training metrics are necessary but not sufficient. Track training loss and validation loss to detect overfitting — if training loss drops while validation loss plateaus or rises, you're memorizing rather than learning. But the metrics that actually matter are task-specific evals on your held-out test set. For classification, track accuracy, precision, recall, and F1. For generation, use LLM-as-judge scoring on dimensions relevant to your task. Always compare against your baseline: the pre-fine-tuned model with good prompt engineering. If fine-tuning doesn't beat the prompting baseline, you either need more/better data or fine-tuning is the wrong approach. Track per-category performance, not just aggregate — a model that's 95% accurate overall but fails on a critical category is worse than one that's 90% but consistent. Always monitor for regression on general capabilities.
