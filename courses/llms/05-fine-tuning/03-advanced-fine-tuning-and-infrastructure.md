# 03 — Advanced Fine-Tuning and Infrastructure

## Training Infrastructure at Scale

Training large models (70B+) or fine-tuning at production scale requires distributed training infrastructure that is qualitatively different from single-GPU training.

### DeepSpeed ZeRO

DeepSpeed ZeRO (Zero Redundancy Optimizer) is the most commonly used framework for distributed training. It partitions model state across GPUs to eliminate redundancy.

```
ZeRO Stage 1: Optimizer state partitioned across GPUs
  - Each GPU holds only 1/N of the optimizer state
  - Memory savings: ~4× reduction for optimizer state

ZeRO Stage 2: Optimizer state + gradients partitioned
  - Each GPU holds only 1/N of gradients too
  - Memory savings: ~8× reduction over baseline

ZeRO Stage 3: Optimizer state + gradients + model parameters partitioned
  - Each GPU holds only 1/N of all model state
  - Memory savings: proportional to number of GPUs
  - Latency: More communication overhead (gather before forward pass)
```

**Practical guidance:**
- ZeRO-2: Best for most training scenarios; significant memory savings with moderate communication overhead
- ZeRO-3: For very large models where ZeRO-2 still doesn't fit; higher communication cost
- ZeRO-Offload: Offloads optimizer state to CPU RAM; enables very large models on limited GPU

```python
# deepspeed_config.json
{
    "zero_optimization": {
        "stage": 2,
        "offload_optimizer": {"device": "cpu"},  # Enable for ZeRO-Offload
        "allgather_partitions": true,
        "allgather_bucket_size": 2e8,
        "overlap_comm": true,
        "reduce_scatter": true,
        "reduce_bucket_size": 2e8,
        "contiguous_gradients": true
    },
    "fp16": {"enabled": true},
    "gradient_accumulation_steps": 4,
    "train_micro_batch_size_per_gpu": 4
}
```

### FSDP (Fully Sharded Data Parallelism)

PyTorch's native distributed training solution, now competitive with DeepSpeed:

```python
from torch.distributed.fsdp import FullyShardedDataParallel as FSDP
from torch.distributed.fsdp.wrap import transformer_auto_wrap_policy

# Wrap the model with FSDP
wrapped_model = FSDP(
    model,
    auto_wrap_policy=transformer_auto_wrap_policy,
    device_id=torch.cuda.current_device(),
    sharding_strategy=ShardingStrategy.FULL_SHARD  # ZeRO-3 equivalent
)
```

**FSDP vs DeepSpeed:**
- FSDP: Native PyTorch, simpler setup for PyTorch-native code, well-integrated with HuggingFace `Trainer`
- DeepSpeed: More mature, more optimization options, better documentation for edge cases

### Flash Attention

Flash Attention (Dao et al., 2022) is a memory-efficient attention implementation that is now standard in production training. It avoids materializing the full n×n attention matrix in GPU HBM by using tiling:

```python
# Enable Flash Attention in HuggingFace
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    attn_implementation="flash_attention_2",  # Requires flash-attn package
    torch_dtype=torch.bfloat16,
)
```

**Benefits:**
- 2–4× faster attention, especially for long sequences
- Subquadratic memory (O(n) instead of O(n²)) during the attention computation
- No change to outputs — exactly equivalent to standard attention
- Now essentially required for training on sequences longer than 4K tokens

### Practical Training Configuration Guide

```python
# Complete training configuration example for 7B LoRA fine-tuning on 2× A100 80GB
training_args = TrainingArguments(
    output_dir="./output",
    num_train_epochs=3,
    per_device_train_batch_size=4,    # Per GPU
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,    # Effective batch = 4 * 4 * 2 GPUs = 32
    learning_rate=2e-4,
    lr_scheduler_type="cosine",       # Cosine decay
    warmup_ratio=0.05,                # 5% of steps for warmup
    bf16=True,                        # BF16 for stability (not FP16)
    fp16=False,
    logging_steps=10,
    eval_steps=200,
    save_steps=200,
    save_total_limit=3,               # Keep only 3 checkpoints
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    dataloader_num_workers=4,
    # Distributed training
    deepspeed="./deepspeed_config.json",  # Enable ZeRO
    # Memory optimization
    gradient_checkpointing=True,      # Trade compute for memory (recompute activations)
)
```

---

## Quantization for Deployment

After fine-tuning, you typically need to quantize the model for efficient inference. The fine-tuned model in BF16 is much larger than needed for most deployment scenarios.

### Quantization Methods for Deployment

**GPTQ (GPU-optimized)**
```python
from transformers import GPTQConfig, AutoModelForCausalLM

gptq_config = GPTQConfig(
    bits=4,                 # 4-bit quantization
    dataset="c4",           # Calibration dataset
    desc_act=True,          # Activation-aware quantization
)

model = AutoModelForCausalLM.from_pretrained(
    "path/to/fine-tuned-model",
    quantization_config=gptq_config
)
model.save_pretrained("path/to/gptq-model")
```

**AWQ (Activation-Aware Weight Quantization)**
```python
from awq import AutoAWQForCausalLM

model = AutoAWQForCausalLM.from_pretrained("path/to/fine-tuned-model")
model.quantize(
    tokenizer,
    quant_config={
        "zero_point": True,
        "q_group_size": 128,
        "w_bit": 4,         # 4-bit
        "version": "GEMM"
    }
)
model.save_quantized("path/to/awq-model")
```

**GGUF (llama.cpp format for CPU deployment)**
```bash
# Convert fine-tuned HuggingFace model to GGUF
python llama.cpp/convert_hf_to_gguf.py \
    --outfile model-q4_K_M.gguf \
    --outtype q4_K_M \
    path/to/fine-tuned-model
```

### Quality-Memory Tradeoff After Fine-Tuning

| Precision | File Size (7B) | Quality vs. BF16 | Deployment |
|---|---|---|---|
| BF16 | ~14 GB | 100% | GPU only |
| FP8 | ~7 GB | ~99% | Modern GPUs |
| INT8 | ~7 GB | ~98% | GPU (bitsandbytes) |
| INT4 GPTQ/AWQ | ~3.5 GB | ~96% | GPU inference |
| INT4 GGUF | ~3.5 GB | ~96% | CPU/mobile |
| INT3 GGUF | ~2.5 GB | ~93% | Memory-constrained |
| INT2 | ~1.7 GB | ~85% | Extreme constraints |

**Workflow after fine-tuning:**
```
Fine-tune in BF16 → Evaluate quality (BF16 baseline) →
GPTQ/AWQ 4-bit → Evaluate quality (should be <2% degradation) →
Deploy 4-bit model → Monitor production quality
```

---

## Distillation: Training a Small Model from a Large One

Distillation produces a smaller, faster model that mimics a larger model's behavior. The goal: get big-model quality at small-model cost.

### Output Distillation (Knowledge Distillation)

The student learns from the teacher's full probability distribution over the vocabulary:

```python
import torch
import torch.nn.functional as F

def distillation_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    ground_truth_labels: torch.Tensor,
    temperature: float = 4.0,
    alpha: float = 0.7  # Balance between KD loss and CE loss
) -> torch.Tensor:
    """
    Compute the distillation loss.

    temperature: Higher = softer teacher distribution (more informative)
    alpha: Higher = more weight on knowledge distillation vs. ground truth
    """
    # Soft targets from teacher (high temperature = softer distribution)
    soft_teacher = F.softmax(teacher_logits / temperature, dim=-1)
    soft_student = F.log_softmax(student_logits / temperature, dim=-1)

    # KL divergence loss (knowledge distillation)
    kd_loss = F.kl_div(soft_student, soft_teacher, reduction="batchmean")
    kd_loss *= temperature ** 2  # Scale by T² to match original gradient magnitudes

    # Standard cross-entropy loss (hard targets)
    ce_loss = F.cross_entropy(student_logits, ground_truth_labels)

    # Combined loss
    return alpha * kd_loss + (1 - alpha) * ce_loss
```

### Logit Distillation

Similar to knowledge distillation but directly minimizes the gap between student and teacher logits:

```python
def logit_distillation_loss(
    student_logits: torch.Tensor,
    teacher_logits: torch.Tensor,
    temperature: float = 2.0
) -> torch.Tensor:
    """Minimize distance between student and teacher logits directly."""
    # Normalize by temperature
    s = student_logits / temperature
    t = teacher_logits / temperature

    # KL divergence from student to teacher
    return F.kl_div(
        F.log_softmax(s, dim=-1),
        F.softmax(t, dim=-1),
        reduction="batchmean"
    ) * (temperature ** 2)
```

### Practical Distillation Pipeline

```
Step 1: Generate teacher outputs
  → Run your dataset through the teacher model (GPT-4, Claude Opus)
  → For next-token prediction: save the top-K logits per position
  → For instruction following: save the full response text

Step 2: Prepare training data
  → (input, teacher_response) pairs for output distillation
  → (input, teacher_logits) pairs for logit distillation (harder to scale)

Step 3: Train student model
  → Use distillation loss instead of (or in addition to) standard CE loss
  → Student is typically 4–10× smaller than teacher

Step 4: Evaluate
  → Compare student quality to teacher on your task's eval set
  → Typical result: 80–95% of teacher quality at 10–50× lower inference cost
```

### Notable Examples

- **GPT-4o-mini:** Distilled from GPT-4o with 94% of quality at ~15× lower cost
- **Phi series (Microsoft):** Distilled on high-quality synthetic data from GPT-4
- **TinyLlama:** 1.1B parameter model trained on data influenced by larger Llama models

---

## Advanced Fine-Tuning Topics

### MoE Fine-Tuning

Mixture of Experts (MoE) models (Mixtral, DeepSeek-V3) route each token to a subset of "expert" FFN layers. Fine-tuning MoE models requires adapting only the relevant experts:

```python
# Apply LoRA only to the active expert FFN layers, not the routing network
lora_config = LoraConfig(
    r=16,
    target_modules=[
        "q_proj", "k_proj", "v_proj",  # Attention (always active)
        "w1", "w2", "w3",              # Expert FFN layers
        # NOT "gate": router is frozen
    ]
)
```

### Speculative Decoding with Fine-Tuned Models

A fine-tuned model can serve as the draft model for speculative decoding, if the base model is the target:

```
Draft: fine-tuned 7B model (specialized for your task)
Target: base 70B model (verifier)
```

This works particularly well when the fine-tuned model has highly predictable outputs (structured formats, domain-specific patterns), where draft acceptance rates are high.

### Continual Learning

For production systems where the model must continuously adapt to new data without full retraining:

```python
class ContinualFineTuner:
    def __init__(self, model, method="ewc"):
        self.model = model
        self.method = method

    def update(self, new_data: list[dict], preserve_previous: bool = True):
        if not preserve_previous:
            # Simple fine-tuning (risk of forgetting)
            return self._simple_finetune(new_data)

        if self.method == "ewc":
            return self._ewc_update(new_data)
        elif self.method == "replay":
            return self._replay_update(new_data)
        elif self.method == "lora_new_adapter":
            # New LoRA adapter for new task, keeping all old adapters
            return self._new_adapter_finetune(new_data)
```

**Recommended approaches for continual learning:**
1. New LoRA adapter per new task (most practical — complete isolation between tasks)
2. Replay buffer (mix new data with representative old data)
3. EWC (complex to implement; LoRA adapters are usually simpler)

---

## Key Numbers Reference

### Fine-Tuning Method Comparison

| Method | GPU RAM (7B) | GPU RAM (70B) | Training Speed | Quality |
|---|---|---|---|---|
| Full FT (BF16) | ~112 GB | ~1.1 TB | Fast (all params) | Highest |
| LoRA r=16 (BF16) | ~28 GB | ~280 GB | Medium | Near full FT |
| QLoRA r=16 (4-bit) | ~12 GB | ~48 GB | Slower (quant overhead) | Slightly lower |
| QLoRA r=64 (4-bit) | ~14 GB | ~56 GB | Slower | Higher rank compensates |

### Training Hyperparameter Starting Points

| Hyperparameter | LoRA | QLoRA | Full FT |
|---|---|---|---|
| Learning rate | 2e-4 | 1e-4 | 1e-5 |
| Epochs | 1–3 | 1–3 | 1–2 |
| Batch size (effective) | 16–64 | 16–32 | 32–256 |
| LR scheduler | Cosine | Cosine | Cosine |
| Warmup ratio | 0.05 | 0.05 | 0.03 |
| Weight decay | 0.0 | 0.0 | 0.01 |

### LoRA-Specific Parameters

| Parameter | Range | Notes |
|---|---|---|
| r (rank) | 4–128 | Start with 16; higher = more capacity + memory |
| alpha | 2× rank | Standard; controls update magnitude |
| dropout | 0.0–0.1 | Small values; 0 is often fine |
| target modules | q_proj, v_proj minimum | Add k_proj, o_proj for more capacity |

---

## Interview Q&A: Advanced Fine-Tuning

**Q: Explain DeepSpeed ZeRO and when you would use each stage.**

DeepSpeed ZeRO eliminates redundancy in distributed training by partitioning optimizer state (ZeRO-1), gradients (ZeRO-2), and model parameters (ZeRO-3) across GPUs. Stage 1 saves ~4× optimizer memory with minimal communication overhead. Stage 2 adds gradient partitioning for ~8× total savings — this is the sweet spot for most training. Stage 3 partitions everything, enabling training of models that don't fit even with Stage 2, at the cost of higher communication overhead (each forward pass requires gathering parameters). Use ZeRO-2 as the default; ZeRO-3 when you're training 70B+ models or memory is still tight after ZeRO-2. ZeRO-Offload can push optimizer state to CPU RAM for extreme cases.

**Q: What is Flash Attention and why is it important for training?**

Flash Attention restructures the attention computation to avoid materializing the full n×n attention matrix in slow GPU HBM memory. Standard attention requires O(n²) memory just for the attention scores — for a 32K sequence and 128 attention heads, this is enormous. Flash Attention tiles the computation and keeps intermediate results in fast SRAM, achieving identical mathematical results with O(n) memory and 2–4× faster execution. It's now effectively required for training on sequences longer than 4K tokens and is standard in all modern training frameworks. Enabling it is a one-line change in HuggingFace and provides immediate free speedup.

**Q: How would you deploy a fine-tuned model in production?**

After fine-tuning in BF16: first, evaluate the full-precision model against your quality baseline to confirm the fine-tuning worked. Then quantize to INT4 (GPTQ or AWQ for GPU deployment, GGUF for CPU/edge) and re-evaluate — expect <2% quality degradation. Set up inference via vLLM or TGI for production serving (both support quantized models and have PagedAttention for efficient batching). Deploy behind an API layer with rate limiting, authentication, and monitoring. Track latency, cost, and quality metrics from day one. For LoRA adapters: load the base model once and swap adapters at request time — much more efficient than loading separate full models for each fine-tuned variant. Monitor for quality drift compared to your fine-tuning eval set.

**Q: What are the safety risks of fine-tuning and how do you mitigate them?**

Fine-tuning can bypass safety alignments baked into the base model. If training data contains harmful content, or if instruction-following training overrides safety constraints, the fine-tuned model may produce outputs the base model would refuse. Mitigations: audit training data for harmful content before training; maintain alignment examples in your fine-tuning data (don't inadvertently remove safety-related patterns); red-team the fine-tuned model with the same attack categories used against the base model; evaluate on safety benchmarks (SafetyBench, ToxicityPrompts) before and after; document changes in your model card. Additionally, many providers prohibit using their model outputs to train competing models — check terms of service before creating synthetic training data from API calls.
