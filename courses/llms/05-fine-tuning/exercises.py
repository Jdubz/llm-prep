"""
Fine-Tuning & Model Customization -- Exercises

Complete the TODO sections. Each exercise tests a different aspect of the
fine-tuning workflow that comes up in interviews and real production work.

Run with: python exercises.py
Each exercise has a verify() function that checks your implementation.
"""

import json
import math
import random
from dataclasses import dataclass, field
from typing import Any


# ============================================================================
# EXERCISE 1: Approach Selection
#
# READ FIRST:
#   01-fine-tuning-fundamentals.md
#     -> "When to Fine-Tune" -- decision tree, approach comparison table
#     -> "The Anti-Pattern: Fine-Tuning for Knowledge"
#
# ALSO SEE:
#   examples.py -> Section 6 "FINE-TUNING DECISION ENGINE" (FineTuningDecisionEngine
#     class, recommend() method with the full decision tree logic)
#   examples.py -> Section 7 "COST ESTIMATOR" (estimate_monthly_cost helper)
#
# Given a use case description and constraints, determine the right approach:
# prompt engineering, RAG, fine-tuning, or distillation. Provide reasoning.
#
# This is the most common fine-tuning interview question. Interviewers want
# to see that you don't reach for fine-tuning as a default -- you consider
# simpler alternatives first and justify the added complexity.
# ============================================================================


@dataclass
class Scenario:
    """A use case scenario for approach selection."""

    description: str
    needs_private_knowledge: bool
    knowledge_update_frequency: str  # "static", "weekly", "daily", "realtime"
    needs_custom_output_format: bool
    needs_custom_tone_or_style: bool
    labeled_examples_available: int
    monthly_request_volume: int
    max_latency_ms: int
    budget_usd: float


def select_approach(scenario: Scenario) -> dict[str, Any]:
    """Determine the best approach for the given scenario.

    Return a dict with:
    - "approach": one of "prompt_engineering", "rag", "fine_tuning",
      "rag_plus_fine_tuning", "distillation"
    - "reasoning": list of strings explaining the decision
    - "data_strategy": how to get/augment training data (if fine-tuning)
    - "estimated_monthly_cost": rough estimate in USD

    Walk through the decision tree:
    1. Can prompt engineering alone solve it?
    2. Does it need external knowledge? -> RAG
    3. Does it need behavior changes? -> Fine-tuning
    4. Does it need both? -> RAG + fine-tuning
    5. Is cost optimization the primary driver? -> Distillation
    """
    # TODO: Implement the decision logic
    #
    # Step 1 -- Check if prompt engineering suffices:
    #   If NOT needs_private_knowledge AND NOT needs_custom_output_format
    #   AND NOT needs_custom_tone_or_style AND labeled_examples_available < 50:
    #     -> return "prompt_engineering"
    #
    # Step 2 -- Check knowledge needs:
    #   If needs_private_knowledge AND knowledge_update_frequency != "static":
    #     -> RAG is needed (knowledge changes too often for fine-tuning)
    #
    # Step 3 -- Check behavior needs:
    #   If needs_custom_output_format OR needs_custom_tone_or_style:
    #     -> fine-tuning is needed for behavioral changes
    #
    # Step 4 -- Combine:
    #   If BOTH knowledge and behavior needs -> "rag_plus_fine_tuning"
    #   If only knowledge needs -> "rag"
    #   If only behavior needs -> "fine_tuning"
    #
    # Step 5 -- Cost optimization check:
    #   If monthly_request_volume > 20000 AND budget_usd is tight
    #   AND labeled_examples_available > 200:
    #     -> consider "distillation" (smaller model, cheaper inference)
    #
    # Step 6 -- Data strategy:
    #   labeled_examples_available < 50:  "synthetic data generation + few-shot"
    #   50-200: "synthetic augmentation to reach 500+ then fine-tune"
    #   200+: "direct fine-tuning with held-out test set"
    #
    # Step 7 -- Cost estimation:
    #   Rough formula: monthly_request_volume * avg_tokens_per_request * cost_per_token
    #   Fine-tuned models use shorter prompts (~50% fewer tokens)
    #
    # Return dict structure:
    #   {
    #       "approach": "prompt_engineering" | "rag" | "fine_tuning" |
    #                   "rag_plus_fine_tuning" | "distillation",
    #       "reasoning": ["reason 1", "reason 2", ...],
    #       "data_strategy": "description of how to get/augment data",
    #       "estimated_monthly_cost": float,
    #   }
    raise NotImplementedError("Implement select_approach")


def verify_exercise_1():
    """Verify approach selection logic."""
    # Scenario 1: Simple formatting task with enough data
    s1 = Scenario(
        description="Convert free-text bug reports into structured JSON",
        needs_private_knowledge=False,
        knowledge_update_frequency="static",
        needs_custom_output_format=True,
        needs_custom_tone_or_style=False,
        labeled_examples_available=500,
        monthly_request_volume=10000,
        max_latency_ms=2000,
        budget_usd=1000,
    )
    r1 = select_approach(s1)
    assert r1["approach"] in ("fine_tuning", "prompt_engineering"), \
        f"Scenario 1: Expected fine_tuning or prompt_engineering, got {r1['approach']}"
    assert len(r1["reasoning"]) > 0, "Must provide reasoning"

    # Scenario 2: FAQ bot over company docs that change weekly
    s2 = Scenario(
        description="Answer employee questions about company policies",
        needs_private_knowledge=True,
        knowledge_update_frequency="weekly",
        needs_custom_output_format=False,
        needs_custom_tone_or_style=False,
        labeled_examples_available=0,
        monthly_request_volume=5000,
        max_latency_ms=3000,
        budget_usd=500,
    )
    r2 = select_approach(s2)
    assert r2["approach"] == "rag", \
        f"Scenario 2: Expected rag (needs private, changing knowledge), got {r2['approach']}"

    # Scenario 3: Needs both knowledge and custom behavior
    s3 = Scenario(
        description="Medical chatbot with specific clinical response format",
        needs_private_knowledge=True,
        knowledge_update_frequency="weekly",
        needs_custom_output_format=True,
        needs_custom_tone_or_style=True,
        labeled_examples_available=2000,
        monthly_request_volume=50000,
        max_latency_ms=2000,
        budget_usd=5000,
    )
    r3 = select_approach(s3)
    assert r3["approach"] == "rag_plus_fine_tuning", \
        f"Scenario 3: Expected rag_plus_fine_tuning, got {r3['approach']}"

    # Scenario 4: No data, no special requirements
    s4 = Scenario(
        description="General-purpose Q&A bot",
        needs_private_knowledge=False,
        knowledge_update_frequency="static",
        needs_custom_output_format=False,
        needs_custom_tone_or_style=False,
        labeled_examples_available=0,
        monthly_request_volume=1000,
        max_latency_ms=5000,
        budget_usd=100,
    )
    r4 = select_approach(s4)
    assert r4["approach"] == "prompt_engineering", \
        f"Scenario 4: Expected prompt_engineering, got {r4['approach']}"

    print("Exercise 1 PASSED")


# ============================================================================
# EXERCISE 2: Data Preparation Pipeline
#
# READ FIRST:
#   01-fine-tuning-fundamentals.md
#     -> "Data Preparation" -- data formats (OpenAI chat, Alpaca, DPO),
#        data volume guidance table, quality checklist
#     -> "Training Fundamentals" -> "Data Splitting" (80/10/10 split)
#
# ALSO SEE:
#   examples.py -> Section 1 "DATA PREPARATION PIPELINE":
#     - to_openai_chat_format(), to_alpaca_format()  (format converters)
#     - clean_text(), remove_control_chars()          (cleaning helpers)
#     - deduplicate_by_input()                        (dedup logic)
#     - validate_example()                            (validation checks)
#     - train_val_test_split()                        (splitting logic)
#     - full_preparation_pipeline()                   (end-to-end pipeline)
#   examples.py -> Section 2 "DATA QUALITY SCORING":
#     - DataQualityScorer class (score_example method, length/diversity checks)
#
# Given raw, messy data, clean it, validate it, format it, and split it
# for training. This is the most time-consuming part of real fine-tuning
# work and the most likely to determine success or failure.
# ============================================================================


def prepare_for_fine_tuning(
    raw_examples: list[dict],
    output_format: str = "openai",
    system_prompt: str = "You are a helpful assistant.",
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> dict[str, list[dict]]:
    """Prepare raw data for fine-tuning.

    Input: list of dicts with "input" and "output" keys (may be messy)
    Output: dict with "train", "validation", "test" splits in the
    requested format

    Steps:
    1. Clean text (normalize whitespace, remove control characters)
    2. Filter out invalid examples (empty input or output)
    3. Deduplicate (by input text -- same input shouldn't appear twice)
    4. Convert to the requested format ("openai" or "alpaca")
    5. Validate format compliance
    6. Split into train/validation/test

    Return the splits dict. Print statistics about each step.
    """
    # TODO: Implement the full pipeline
    #
    # Step 1 -- Clean text:
    #   def clean(text: str) -> str:
    #       import re
    #       text = text.replace("\x00", "")          # Remove null bytes
    #       text = text.replace("\u200b", "")         # Remove zero-width spaces
    #       text = re.sub(r"\s+", " ", text)          # Collapse whitespace
    #       return text.strip()
    #   Apply clean() to both "input" and "output" of each example.
    #   Track: cleaned_count (how many were modified)
    #
    # Step 2 -- Filter invalid examples:
    #   Remove if: clean(input) == "" or clean(output) == ""
    #   Remove if: len(output.split()) < 2  (single-word outputs are suspicious)
    #   Track: removed_empty, removed_short
    #
    # Step 3 -- Deduplicate by input:
    #   seen_inputs = set()
    #   For each example, normalize key = input.lower().strip()
    #   If key already in seen_inputs, skip it.
    #   Track: duplicates_removed
    #
    # Step 4 -- Convert to requested format:
    #   if output_format == "openai":
    #       formatted = {
    #           "messages": [
    #               {"role": "system", "content": system_prompt},
    #               {"role": "user", "content": cleaned_input},
    #               {"role": "assistant", "content": cleaned_output},
    #           ]
    #       }
    #   elif output_format == "alpaca":
    #       formatted = {
    #           "instruction": system_prompt,
    #           "input": cleaned_input,
    #           "output": cleaned_output,
    #       }
    #
    # Step 5 -- Split into train/validation/test:
    #   random.shuffle(formatted_examples)
    #   n = len(formatted_examples)
    #   test_n = max(1, int(n * test_ratio))
    #   val_n = max(1, int(n * val_ratio))
    #   train_n = n - val_n - test_n
    #   return {"train": [...], "validation": [...], "test": [...]}
    #
    # Step 6 -- Print stats at each step (optional but helpful for debugging)
    raise NotImplementedError("Implement prepare_for_fine_tuning")


def verify_exercise_2():
    """Verify data preparation pipeline."""
    raw = [
        {"input": "What is Python?", "output": "Python is a programming language."},
        {"input": "  What  is  Python?  ", "output": "Python is a programming language."},  # Duplicate after cleaning
        {"input": "Explain LoRA", "output": "LoRA is Low-Rank Adaptation, a fine-tuning method."},
        {"input": "", "output": "This has no input"},  # Invalid: empty input
        {"input": "What is ML?", "output": ""},  # Invalid: empty output
        {"input": "What is\x00 RAG?", "output": "RAG is retrieval-augmented generation."},  # Needs cleaning
        {"input": "Define batch size", "output": "OK"},  # Suspicious: single-word output
    ]

    result = prepare_for_fine_tuning(raw, output_format="openai")

    # Should have train, validation, test splits
    assert "train" in result, "Missing 'train' split"
    assert "validation" in result, "Missing 'validation' split"
    assert "test" in result, "Missing 'test' split"

    # Total examples should be less than raw (after filtering and dedup)
    total = sum(len(v) for v in result.values())
    assert total < len(raw), f"Expected fewer examples after cleaning, got {total}"

    # Should be in OpenAI format
    if result["train"]:
        assert "messages" in result["train"][0], "Expected OpenAI chat format"
        messages = result["train"][0]["messages"]
        roles = [m["role"] for m in messages]
        assert "system" in roles, "Missing system message"
        assert "user" in roles, "Missing user message"
        assert "assistant" in roles, "Missing assistant message"

    print("Exercise 2 PASSED")


# ============================================================================
# EXERCISE 3: Synthetic Data Generation Pipeline Design
#
# READ FIRST:
#   01-fine-tuning-fundamentals.md
#     -> "Synthetic Data Generation" -- teacher model pattern, risks
#        (model collapse, distribution shift, quality ceiling, hallucination),
#        mitigation strategies
#     -> "How Much Data Do You Need?" table (minimum/typical counts by task)
#
# ALSO SEE:
#   examples.py -> Section 3 "SYNTHETIC DATA GENERATION PIPELINE":
#     - SyntheticDataGenerator class
#     - build_generation_prompt() (shows how to include seed examples)
#     - generate_batch() (batch generation pattern)
#     - quality_filter() (post-generation filtering)
#     - diversity_check() (ensuring output variety)
#     - estimate_generation_cost() (token-based cost calculation)
#
# Design a pipeline that generates training data for a specific domain
# using a teacher model. You won't call an actual API -- instead, build
# the prompts, configuration, and quality filtering logic.
# ============================================================================


@dataclass
class SyntheticPipelineConfig:
    """Configuration for a synthetic data generation pipeline."""

    domain: str
    task_type: str  # "classification", "generation", "extraction"
    num_examples_target: int
    seed_examples: list[dict]  # Real examples to anchor the distribution
    output_labels: list[str] | None = None  # For classification tasks
    quality_threshold: float = 0.7
    teacher_model: str = "gpt-4o"


def design_synthetic_pipeline(
    config: SyntheticPipelineConfig,
) -> dict[str, Any]:
    """Design a synthetic data generation pipeline.

    Return a dict with:
    - "generation_prompts": list of prompt strings for the teacher model
      (at least 3 diverse prompts)
    - "num_batches": how many generation batches to run
    - "examples_per_batch": examples to generate per batch
    - "quality_checks": list of quality check descriptions
    - "estimated_cost_usd": based on teacher model and example count
    - "diversity_strategy": how you ensure diverse outputs
    - "filtering_criteria": what makes an example good vs bad

    The prompts should:
    - Use seed examples to demonstrate the expected format
    - Vary in focus (different difficulty levels, edge cases, etc.)
    - Be specific enough to generate useful data
    """
    # TODO: Implement the pipeline design
    #
    # Step 1 -- Calculate generation volume:
    #   target = config.num_examples_target
    #   overshoot_factor = 2.5  # Generate 2.5x to account for filtering
    #   total_to_generate = int(target * overshoot_factor)
    #   examples_per_batch = 20  # Typical batch size for structured generation
    #   num_batches = math.ceil(total_to_generate / examples_per_batch)
    #
    # Step 2 -- Build diverse generation prompts (at least 3):
    #   Each prompt should:
    #   - State the domain and task type from config
    #   - Include 2-3 seed examples from config.seed_examples as demonstrations
    #   - Have a different diversity focus:
    #     Prompt 1: "Generate typical/common cases" (happy path)
    #     Prompt 2: "Generate edge cases and unusual inputs" (boundary conditions)
    #     Prompt 3: "Generate adversarial/tricky cases" (near misses, ambiguous)
    #   - If config.output_labels, mention all labels and request balanced coverage
    #   - Request output in JSON format: [{"input": "...", "label": "..."}]
    #
    #   Example prompt structure:
    #     f"You are a training data generator for {config.domain} {config.task_type}.\n"
    #     f"Labels: {config.output_labels}\n"
    #     f"Examples:\n{seed_examples_str}\n"
    #     f"Generate {examples_per_batch} NEW diverse examples..."
    #
    # Step 3 -- Define quality checks (at least 3):
    #   - "format_compliance": output matches expected schema (has "input" and "label" keys)
    #   - "label_validity": label is in config.output_labels (for classification)
    #   - "length_check": input is between 5 and 500 characters
    #   - "diversity_check": no two inputs share > 80% token overlap
    #   - "factual_plausibility": input makes sense for the domain
    #
    # Step 4 -- Estimate cost:
    #   tokens_per_example = 500  # ~250 input + ~250 output per example
    #   total_tokens = total_to_generate * tokens_per_example
    #   Model pricing (approx per 1M tokens):
    #     "gpt-4o": input=$2.50, output=$10.00
    #     "gpt-4o-mini": input=$0.15, output=$0.60
    #   cost = (total_tokens / 1_000_000) * (input_price + output_price) / 2
    #
    # Step 5 -- Define diversity strategy:
    #   Describe your approach, e.g.: "Rotate through prompt variants per batch,
    #   require label balance, filter near-duplicates via token overlap"
    #
    # Return:
    #   {
    #       "generation_prompts": [prompt1, prompt2, prompt3, ...],
    #       "num_batches": int,
    #       "examples_per_batch": int,
    #       "quality_checks": ["check1 description", "check2", ...],
    #       "estimated_cost_usd": float,
    #       "diversity_strategy": "description string",
    #       "filtering_criteria": "description of good vs bad examples",
    #   }
    raise NotImplementedError("Implement design_synthetic_pipeline")


def verify_exercise_3():
    """Verify synthetic pipeline design."""
    config = SyntheticPipelineConfig(
        domain="customer_support",
        task_type="classification",
        num_examples_target=1000,
        seed_examples=[
            {"input": "My order hasn't arrived yet", "label": "shipping"},
            {"input": "I want a refund", "label": "refund"},
            {"input": "How do I change my password?", "label": "account"},
        ],
        output_labels=["shipping", "refund", "account", "product", "billing"],
        teacher_model="gpt-4o-mini",
    )

    pipeline = design_synthetic_pipeline(config)

    assert "generation_prompts" in pipeline, "Missing generation_prompts"
    assert len(pipeline["generation_prompts"]) >= 3, "Need at least 3 diverse prompts"
    assert pipeline["num_batches"] > 0, "Need at least 1 batch"
    assert pipeline["examples_per_batch"] > 0, "Need examples per batch"

    # Should generate more than target (to account for filtering)
    total_generated = pipeline["num_batches"] * pipeline["examples_per_batch"]
    assert total_generated >= config.num_examples_target, \
        f"Generate at least {config.num_examples_target} examples (got plan for {total_generated})"

    assert "quality_checks" in pipeline, "Missing quality_checks"
    assert len(pipeline["quality_checks"]) >= 3, "Need at least 3 quality checks"
    assert "estimated_cost_usd" in pipeline, "Missing cost estimate"
    assert pipeline["estimated_cost_usd"] > 0, "Cost should be positive"

    # Prompts should reference the seed examples
    all_prompts = " ".join(pipeline["generation_prompts"])
    assert "shipping" in all_prompts.lower() or "order" in all_prompts.lower(), \
        "Prompts should reference seed examples"

    print("Exercise 3 PASSED")


# ============================================================================
# EXERCISE 4: Evaluation Harness
#
# READ FIRST:
#   01-fine-tuning-fundamentals.md
#     -> "Evaluation After Fine-Tuning" -- quantitative metrics table,
#        evaluation hierarchy (Levels 1-5)
#   02-training-and-alignment.md
#     -> "What metrics do you track when fine-tuning?" (Interview Q&A)
#
# ALSO SEE:
#   examples.py -> Section 5 "EVALUATION HARNESS":
#     - EvalHarness class (run_eval, compare_models methods)
#     - compute_exact_match(), compute_rouge_l()  (metric implementations)
#     - per_class_accuracy()                       (per-category breakdown)
#     - generate_comparison_report()               (report formatting)
#     - break_even_analysis()                      (cost analysis helper)
#
# Build a harness that compares a base model (with prompting) against a
# fine-tuned model on the same test set. Compute metrics and determine
# whether the fine-tuning was worth the investment.
# ============================================================================


@dataclass
class ModelOutput:
    """A single model prediction with metadata."""

    input_text: str
    expected_output: str
    predicted_output: str
    latency_ms: float
    token_count: int


def evaluate_and_compare(
    test_set: list[dict[str, str]],
    baseline_outputs: list[ModelOutput],
    finetuned_outputs: list[ModelOutput],
    task_type: str = "classification",
    training_cost_usd: float = 0.0,
) -> dict[str, Any]:
    """Compare fine-tuned model against baseline on a test set.

    Return a dict with:
    - "baseline_metrics": dict of metric_name -> value
    - "finetuned_metrics": dict of metric_name -> value
    - "improvement": dict of metric_name -> {"absolute": ..., "relative_pct": ...}
    - "latency_comparison": {"baseline_avg_ms": ..., "finetuned_avg_ms": ..., "speedup": ...}
    - "cost_analysis": {"training_cost": ..., "inference_savings_per_1k": ..., "break_even_requests": ...}
    - "recommendation": "ship_finetuned" | "keep_baseline" | "needs_more_data"
    - "reasoning": str explaining the recommendation

    Metrics to compute based on task_type:
    - "classification": exact_match, per_class_accuracy
    - "generation": rouge_l (implement a simple version)
    - "extraction": exact_match, partial_match (check if expected is substring of predicted)

    Cost analysis:
    - Calculate per-request cost difference based on token counts
    - Determine break-even point (how many requests to recoup training cost)
    """
    # TODO: Implement the evaluation harness
    #
    # Step 1 -- Compute metrics for each model:
    #   def compute_metrics(outputs: list[ModelOutput], task_type: str) -> dict:
    #       if task_type == "classification":
    #           # Exact match: normalize both strings (lowercase, strip)
    #           exact_matches = sum(
    #               1 for o in outputs
    #               if o.predicted_output.strip().lower() == o.expected_output.strip().lower()
    #           )
    #           exact_match_rate = exact_matches / len(outputs)
    #
    #           # Per-class accuracy: group by expected, compute accuracy per group
    #           from collections import defaultdict
    #           by_class = defaultdict(list)
    #           for o in outputs:
    #               key = o.expected_output.strip().lower()
    #               match = o.predicted_output.strip().lower() == key
    #               by_class[key].append(match)
    #           per_class = {k: sum(v)/len(v) for k, v in by_class.items()}
    #
    #           return {"exact_match": exact_match_rate, "per_class_accuracy": per_class}
    #
    #       elif task_type == "generation":
    #           # Simple ROUGE-L: longest common subsequence / reference length
    #           def lcs_length(a: list, b: list) -> int:
    #               m, n = len(a), len(b)
    #               dp = [[0] * (n+1) for _ in range(m+1)]
    #               for i in range(1, m+1):
    #                   for j in range(1, n+1):
    #                       if a[i-1] == b[j-1]:
    #                           dp[i][j] = dp[i-1][j-1] + 1
    #                       else:
    #                           dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    #               return dp[m][n]
    #           scores = []
    #           for o in outputs:
    #               pred_tokens = o.predicted_output.lower().split()
    #               ref_tokens = o.expected_output.lower().split()
    #               lcs = lcs_length(pred_tokens, ref_tokens)
    #               rouge_l = lcs / len(ref_tokens) if ref_tokens else 0.0
    #               scores.append(rouge_l)
    #           return {"rouge_l": sum(scores)/len(scores)}
    #
    #       elif task_type == "extraction":
    #           # exact_match + partial_match (expected is substring of predicted)
    #           ...  (similar pattern)
    #
    # Step 2 -- Compute improvement:
    #   For each metric, compute:
    #     absolute = finetuned_value - baseline_value
    #     relative_pct = (absolute / baseline_value) * 100 if baseline_value > 0 else 0
    #
    # Step 3 -- Latency comparison:
    #   baseline_avg_ms = sum(o.latency_ms for o in baseline_outputs) / len(baseline_outputs)
    #   finetuned_avg_ms = sum(o.latency_ms for o in finetuned_outputs) / len(finetuned_outputs)
    #   speedup = baseline_avg_ms / finetuned_avg_ms
    #
    # Step 4 -- Cost analysis:
    #   cost_per_token = 0.00001  # Approximate
    #   baseline_avg_tokens = avg of baseline token_count
    #   finetuned_avg_tokens = avg of finetuned token_count
    #   savings_per_request = (baseline_avg_tokens - finetuned_avg_tokens) * cost_per_token
    #   savings_per_1k = savings_per_request * 1000
    #   break_even_requests = training_cost_usd / savings_per_request (if savings > 0)
    #
    # Step 5 -- Recommendation:
    #   quality_improvement = improvement on primary metric (exact_match or rouge_l)
    #   latency_improvement_pct = (baseline_avg_ms - finetuned_avg_ms) / baseline_avg_ms
    #   if quality_improvement > 0.05 or latency_improvement_pct > 0.20:
    #       recommendation = "ship_finetuned"
    #   elif quality_improvement > 0.01:
    #       recommendation = "needs_more_data"
    #   else:
    #       recommendation = "keep_baseline"
    raise NotImplementedError("Implement evaluate_and_compare")


def verify_exercise_4():
    """Verify evaluation harness."""
    test_set = [
        {"input": "Great product!", "expected": "positive"},
        {"input": "Terrible quality", "expected": "negative"},
        {"input": "It's okay", "expected": "neutral"},
        {"input": "Love it!", "expected": "positive"},
        {"input": "Waste of money", "expected": "negative"},
        {"input": "Average product", "expected": "neutral"},
    ]

    # Baseline: gets 4/6 right, slower, more tokens (longer prompts)
    baseline_outputs = [
        ModelOutput("Great product!", "positive", "positive", 500, 150),
        ModelOutput("Terrible quality", "negative", "negative", 480, 145),
        ModelOutput("It's okay", "neutral", "positive", 520, 155),  # Wrong
        ModelOutput("Love it!", "positive", "positive", 490, 148),
        ModelOutput("Waste of money", "negative", "positive", 510, 152),  # Wrong
        ModelOutput("Average product", "neutral", "neutral", 495, 147),
    ]

    # Fine-tuned: gets 5/6 right, faster, fewer tokens
    finetuned_outputs = [
        ModelOutput("Great product!", "positive", "positive", 200, 80),
        ModelOutput("Terrible quality", "negative", "negative", 190, 75),
        ModelOutput("It's okay", "neutral", "neutral", 210, 82),
        ModelOutput("Love it!", "positive", "positive", 195, 78),
        ModelOutput("Waste of money", "negative", "negative", 205, 80),
        ModelOutput("Average product", "neutral", "positive", 198, 77),  # Wrong
    ]

    result = evaluate_and_compare(
        test_set,
        baseline_outputs,
        finetuned_outputs,
        task_type="classification",
        training_cost_usd=50.0,
    )

    assert "baseline_metrics" in result, "Missing baseline_metrics"
    assert "finetuned_metrics" in result, "Missing finetuned_metrics"
    assert "improvement" in result, "Missing improvement"
    assert "latency_comparison" in result, "Missing latency_comparison"
    assert "recommendation" in result, "Missing recommendation"

    # Fine-tuned should score higher
    baseline_em = result["baseline_metrics"].get("exact_match", 0)
    finetuned_em = result["finetuned_metrics"].get("exact_match", 0)
    assert finetuned_em > baseline_em, \
        f"Fine-tuned ({finetuned_em}) should outperform baseline ({baseline_em})"

    # Fine-tuned should be faster
    assert result["latency_comparison"]["finetuned_avg_ms"] < \
           result["latency_comparison"]["baseline_avg_ms"], \
        "Fine-tuned should have lower latency"

    # Should recommend shipping the fine-tuned model
    assert result["recommendation"] in ("ship_finetuned", "needs_more_data"), \
        f"Expected ship_finetuned or needs_more_data, got {result['recommendation']}"

    print("Exercise 4 PASSED")


# ============================================================================
# EXERCISE 5: Training Cost and GPU Requirements Calculator
#
# READ FIRST:
#   01-fine-tuning-fundamentals.md
#     -> "GPU Requirements and Cost" -- memory-by-method table, GPU quick
#        reference table, cost estimates table
#     -> "Fine-Tuning Approaches" -- memory formulas for full FT, LoRA, QLoRA
#   03-advanced-fine-tuning-and-infrastructure.md
#     -> "Key Numbers Reference" -- fine-tuning method comparison table,
#        training hyperparameter starting points
#
# ALSO SEE:
#   examples.py -> Section 4 "TRAINING CONFIGURATION BUILDER":
#     - TrainingConfigBuilder class (memory estimation, GPU selection)
#     - estimate_memory_requirements() (bytes-per-param formulas)
#     - select_gpu() (feasibility checks per GPU)
#   examples.py -> Section 7 "COST ESTIMATOR":
#     - CostEstimator class (estimate_training_cost, estimate_training_time)
#     - GPU_THROUGHPUT dict (tokens/second by GPU and method)
#
# Given a model size, dataset, and hardware constraints, calculate the
# training cost, time, and recommend the right infrastructure.
# ============================================================================


def calculate_training_requirements(
    model_size_b: float,
    dataset_size: int,
    avg_example_tokens: int,
    num_epochs: int,
    available_gpus: list[dict],  # [{"name": "rtx_4090", "vram_gb": 24, "count": 1}, ...]
    budget_usd: float,
) -> dict[str, Any]:
    """Calculate training requirements and recommend infrastructure.

    Return a dict with:
    - "recommended_method": "full", "lora", or "qlora"
    - "recommended_gpu": which GPU from available_gpus to use
    - "num_gpus_needed": how many of that GPU
    - "fits_in_budget": bool
    - "estimated_hours": training time estimate
    - "estimated_cost_usd": total cost
    - "memory_breakdown": {"model_gb": ..., "lora_gb": ..., "optimizer_gb": ..., "total_gb": ...}
    - "warnings": list of potential issues

    Memory estimation formulas:
    - Full fine-tune FP16: model (2 bytes/param) + gradients (2 bytes/param) + optimizer (8 bytes/param) = ~12 bytes/param
    - LoRA FP16: model (2 bytes/param) + LoRA params (~0.5-2% of model) + optimizer for LoRA only
    - QLoRA: model (0.5 bytes/param in 4-bit) + LoRA in FP16 + optimizer for LoRA

    Training time estimation:
    - total_tokens = dataset_size * avg_example_tokens * num_epochs
    - tokens_per_second depends on method and GPU (see estimates below)

    GPU throughput (tokens/second, approximate):
    - A100-80GB: full=3000, lora=5000, qlora=4000
    - A100-40GB: full=2000, lora=3500, qlora=3000
    - RTX 4090: full=N/A, lora=2000, qlora=1500
    - RTX 3090: full=N/A, lora=1500, qlora=1000
    - H100: full=6000, lora=10000, qlora=8000
    """
    # TODO: Implement the calculator
    #
    # Step 1 -- Memory estimation per method (in GB):
    #   params = model_size_b * 1e9
    #
    #   Full fine-tune FP16:
    #     model_gb   = (params * 2) / 1e9           # 2 bytes/param (BF16)
    #     grad_gb    = (params * 4) / 1e9            # 4 bytes/param (FP32 gradients)
    #     optim_gb   = (params * 8) / 1e9            # 8 bytes/param (Adam: 2 moments)
    #     total_gb   = model_gb + grad_gb + optim_gb # ~14 bytes/param
    #
    #   LoRA FP16:
    #     model_gb   = (params * 2) / 1e9            # Base model frozen in BF16
    #     lora_pct   = 0.01                           # ~1% of params trainable
    #     lora_params = params * lora_pct
    #     lora_gb    = (lora_params * 2) / 1e9
    #     optim_gb   = (lora_params * 8) / 1e9        # Optimizer only for LoRA params
    #     total_gb   = model_gb + lora_gb + optim_gb + 2  # +2 GB overhead
    #
    #   QLoRA (4-bit base):
    #     model_gb   = (params * 0.5) / 1e9           # 0.5 bytes/param in 4-bit
    #     lora_gb    = (lora_params * 2) / 1e9         # LoRA in FP16
    #     optim_gb   = (lora_params * 8) / 1e9
    #     total_gb   = model_gb + lora_gb + optim_gb + 2
    #
    # Step 2 -- Determine feasibility per GPU:
    #   For each gpu in available_gpus:
    #     feasible_methods = []
    #     if total_gb["full"] <= gpu["vram_gb"] * 0.9:  # 90% of VRAM
    #         feasible_methods.append("full")
    #     if total_gb["lora"] <= gpu["vram_gb"] * 0.9:
    #         feasible_methods.append("lora")
    #     if total_gb["qlora"] <= gpu["vram_gb"] * 0.9:
    #         feasible_methods.append("qlora")
    #
    # Step 3 -- Choose cheapest feasible option:
    #   GPU throughput (tokens/second) -- use the dict from the docstring
    #   total_tokens = dataset_size * avg_example_tokens * num_epochs
    #   For each (gpu, method) pair:
    #     throughput = GPU_THROUGHPUT[gpu_name][method]
    #     hours = total_tokens / throughput / 3600
    #     cost = hours * gpu["cost_per_hour"] * gpu.get("count", 1)
    #   Pick the combination with lowest cost that fits budget
    #
    # Step 4 -- Build memory breakdown dict:
    #   {"model_gb": ..., "lora_gb": ..., "optimizer_gb": ..., "total_gb": ...}
    #
    # Step 5 -- Add warnings (list of strings):
    #   Check the conditions listed in the docstring above
    #
    # Step 6 -- Return the full result dict
    raise NotImplementedError("Implement calculate_training_requirements")


def verify_exercise_5():
    """Verify training requirements calculator."""
    gpus = [
        {"name": "rtx_4090", "vram_gb": 24, "count": 2, "cost_per_hour": 0.50},
        {"name": "a100_80gb", "vram_gb": 80, "count": 1, "cost_per_hour": 2.50},
    ]

    # Small model, should fit on RTX 4090 with QLoRA
    result = calculate_training_requirements(
        model_size_b=7,
        dataset_size=1000,
        avg_example_tokens=512,
        num_epochs=3,
        available_gpus=gpus,
        budget_usd=100,
    )

    assert "recommended_method" in result, "Missing recommended_method"
    assert result["recommended_method"] in ("lora", "qlora"), \
        f"7B model should use LoRA or QLoRA, got {result['recommended_method']}"
    assert "estimated_hours" in result, "Missing estimated_hours"
    assert result["estimated_hours"] > 0, "Training time should be positive"
    assert "estimated_cost_usd" in result, "Missing estimated_cost"
    assert "memory_breakdown" in result, "Missing memory_breakdown"

    # Large model, needs bigger GPU
    result_large = calculate_training_requirements(
        model_size_b=70,
        dataset_size=5000,
        avg_example_tokens=1024,
        num_epochs=1,
        available_gpus=gpus,
        budget_usd=500,
    )

    assert result_large["recommended_gpu"]["name"] == "a100_80gb", \
        "70B model should use A100"
    assert result_large["recommended_method"] == "qlora", \
        "70B model on single A100 should use QLoRA"

    print("Exercise 5 PASSED")


# ============================================================================
# EXERCISE 6: LoRA Configuration Designer
#
# READ FIRST:
#   01-fine-tuning-fundamentals.md
#     -> "LoRA (Low-Rank Adaptation)" -- rank, alpha, target_modules explained,
#        code example with LoraConfig, trainable parameter calculation
#     -> "QLoRA" -- when to use 4-bit quantization, BitsAndBytesConfig code
#     -> "Other Adapter Methods" comparison table
#   03-advanced-fine-tuning-and-infrastructure.md
#     -> "LoRA-Specific Parameters" table (rank range, alpha convention, dropout)
#     -> "Key Numbers Reference" -> "Fine-Tuning Method Comparison" (VRAM by method)
#
# ALSO SEE:
#   examples.py -> Section 4 "TRAINING CONFIGURATION BUILDER":
#     - TrainingConfigBuilder.build_lora_config() (rank/alpha/target selection)
#     - select_target_modules() (module lists by quality tier)
#     - estimate_trainable_params() (percentage calculation)
#     - select_quantization() (QLoRA decision logic)
#
# Given constraints (GPU RAM, quality target, data size, task complexity),
# design an optimal LoRA configuration with justification for each choice.
# ============================================================================


def design_lora_config(
    model_size_b: float,
    gpu_vram_gb: int,
    dataset_size: int,
    task_complexity: str,  # "simple", "moderate", "complex"
    quality_target: str,  # "good_enough", "high", "maximum"
    inference_latency_matters: bool = False,
) -> dict[str, Any]:
    """Design a LoRA configuration based on constraints.

    Return a dict with:
    - "rank": int (4, 8, 16, 32, 64, or 128)
    - "alpha": int (typically 2x rank)
    - "target_modules": list of module names
    - "dropout": float
    - "use_4bit": bool (QLoRA)
    - "justification": dict mapping each parameter to a string explaining why
    - "estimated_trainable_params_pct": float
    - "estimated_vram_gb": float

    Design principles:
    - Rank: higher for complex tasks, lower for simple ones. But constrained
      by data size (high rank + small data = overfitting).
    - Target modules: more modules = more capacity but more VRAM.
      Minimum: q_proj, v_proj. Standard: q,k,v,o projections.
      Maximum: all attention + MLP layers.
    - Dropout: higher for small datasets (regularization), lower for large.
    - 4-bit: use if VRAM is tight. Avoid if quality_target is "maximum".
    - Alpha: standard is 2x rank. Higher alpha = larger effective learning rate
      for the adapter.
    """
    # TODO: Implement the configuration designer
    #
    # Step 1 -- Determine if QLoRA is needed (use_4bit):
    #   model_fp16_gb = model_size_b * 2  # 2 GB per billion params in FP16
    #   needs_quant = model_fp16_gb > gpu_vram_gb * 0.7
    #   if quality_target == "maximum" and not needs_quant:
    #       use_4bit = False  # Prefer full precision when possible
    #   else:
    #       use_4bit = needs_quant
    #
    # Step 2 -- Select rank based on task complexity + data:
    #   Base rank by complexity:
    #     "simple":   base_rank = 8
    #     "moderate":  base_rank = 16
    #     "complex":   base_rank = 32
    #
    #   Adjust for data size:
    #     if dataset_size < 500: rank = min(base_rank, 16)  # Prevent overfitting
    #     elif dataset_size >= 5000: rank = base_rank  # Data supports full rank
    #     else: rank = base_rank  # Default
    #
    #   Adjust for quality target:
    #     if quality_target == "maximum": rank = rank * 2
    #     elif quality_target == "good_enough" and rank > 16: rank = 16
    #
    # Step 3 -- Set alpha (standard convention):
    #   alpha = rank * 2
    #
    # Step 4 -- Select target modules by quality target:
    #   "good_enough": ["q_proj", "v_proj"]
    #   "high":        ["q_proj", "k_proj", "v_proj", "o_proj"]
    #   "maximum":     ["q_proj", "k_proj", "v_proj", "o_proj",
    #                    "gate_proj", "up_proj", "down_proj"]
    #
    # Step 5 -- Set dropout based on dataset size:
    #   dataset_size < 500:   dropout = 0.1
    #   dataset_size < 5000:  dropout = 0.05
    #   dataset_size >= 5000: dropout = 0.0
    #
    # Step 6 -- Estimate trainable params percentage:
    #   num_target_modules = len(target_modules)
    #   # Each module adds 2 * rank * hidden_dim params
    #   # Rough estimate: (num_modules * 2 * rank) / (model_total_params) * 100
    #   # For a 7B model with r=16 and 4 modules: ~0.1%
    #   estimated_trainable_pct = (num_target_modules * 2 * rank * 4096) / (model_size_b * 1e9) * 100
    #
    # Step 7 -- Estimate VRAM:
    #   if use_4bit:
    #       model_gb = model_size_b * 0.5
    #   else:
    #       model_gb = model_size_b * 2
    #   lora_overhead = 1 + (rank / 16)  # ~1-3 GB depending on rank
    #   estimated_vram = model_gb + lora_overhead
    #
    # Step 8 -- Build justification dict:
    #   {
    #       "rank": "Why this rank was chosen...",
    #       "alpha": "Standard 2x rank convention...",
    #       "target_modules": "Why these modules...",
    #       "dropout": "Why this dropout value...",
    #       "use_4bit": "Why QLoRA was/wasn't needed...",
    #   }
    #
    # Return the full config dict
    raise NotImplementedError("Implement design_lora_config")


def verify_exercise_6():
    """Verify LoRA configuration designer."""
    # Simple task, small GPU, moderate data
    config1 = design_lora_config(
        model_size_b=7,
        gpu_vram_gb=24,
        dataset_size=500,
        task_complexity="simple",
        quality_target="good_enough",
    )

    assert "rank" in config1, "Missing rank"
    assert "alpha" in config1, "Missing alpha"
    assert "target_modules" in config1, "Missing target_modules"
    assert "dropout" in config1, "Missing dropout"
    assert "justification" in config1, "Missing justification"
    assert config1["rank"] <= 16, f"Simple task shouldn't need rank > 16, got {config1['rank']}"
    assert config1["dropout"] >= 0.05, f"Small dataset needs dropout, got {config1['dropout']}"
    assert config1["use_4bit"] is True, "7B on 24GB should use QLoRA"

    # Complex task, large GPU, lots of data, maximum quality
    config2 = design_lora_config(
        model_size_b=7,
        gpu_vram_gb=80,
        dataset_size=10000,
        task_complexity="complex",
        quality_target="maximum",
    )

    assert config2["rank"] >= 32, f"Complex task + max quality needs rank >= 32, got {config2['rank']}"
    assert config2["use_4bit"] is False, "Maximum quality on 80GB should avoid QLoRA"
    assert len(config2["target_modules"]) >= 4, \
        f"Maximum quality should target many modules, got {len(config2['target_modules'])}"
    assert config2["dropout"] == 0.0 or config2["dropout"] <= 0.01, \
        f"Large dataset needs minimal dropout, got {config2['dropout']}"

    # Check justifications exist for key parameters
    assert "rank" in config2["justification"], "Missing justification for rank"
    assert "target_modules" in config2["justification"], "Missing justification for target_modules"

    print("Exercise 6 PASSED")


# ============================================================================
# RUN ALL EXERCISES
# ============================================================================


def main():
    exercises = [
        ("Exercise 1: Approach Selection", verify_exercise_1),
        ("Exercise 2: Data Preparation", verify_exercise_2),
        ("Exercise 3: Synthetic Data Pipeline", verify_exercise_3),
        ("Exercise 4: Evaluation Harness", verify_exercise_4),
        ("Exercise 5: Training Cost Calculator", verify_exercise_5),
        ("Exercise 6: LoRA Configuration", verify_exercise_6),
    ]

    passed = 0
    failed = 0

    for name, verify_fn in exercises:
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
        try:
            verify_fn()
            passed += 1
        except NotImplementedError:
            print(f"  NOT IMPLEMENTED (TODO)")
            failed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{passed + failed} exercises passed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
