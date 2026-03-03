# 01 — Evaluation Frameworks and Metrics

## Why Evaluation Matters

"If you can't measure it, you can't improve it." In LLM engineering, this is operationally critical. Without evals, every prompt change is a guess. With evals, every change is a measured experiment.

**The core discipline: eval-driven development**

Define your success criteria before writing a single prompt. Build a test set. Establish a baseline. Iterate with measurement. Never deploy a change that regresses on your test set.

---

## Evaluation Methods

### Method Comparison

| Method | When to Use | Cost | Signal Quality | Automation |
|---|---|---|---|---|
| Exact match | Classification, entity extraction | Free | High (if applicable) | Full |
| Contains / regex | Structured output, keyword presence | Free | Medium | Full |
| Embedding similarity | Semantic equivalence, summarization | Very low | Medium | Full |
| LLM-as-judge (absolute) | Open-ended quality, tone, helpfulness | Medium | High | Full |
| LLM-as-judge (pairwise) | Comparing two versions, A/B analysis | Medium | Very high | Full |
| Code execution (pass@k) | Code generation, SQL, math | Low | Very high | Full |
| Custom scoring function | Domain-specific criteria | Low | Depends on design | Full |
| Human evaluation | Ground truth, calibration, edge cases | High | Highest | None |

**Decision rule:** Start with the cheapest method that captures what you care about. Use expensive methods for calibration and edge cases.

### Exact Match

```python
def exact_match_eval(predictions: list[str], references: list[str]) -> float:
    correct = sum(p.strip().lower() == r.strip().lower()
                  for p, r in zip(predictions, references))
    return correct / len(predictions)

# Use for: single-label classification, entity extraction with known answers
# Example: "Is this review positive or negative?" → compare to ground truth label
```

### Contains / Regex

```python
import re

def contains_eval(prediction: str, required_patterns: list[str]) -> bool:
    """Check if prediction contains all required patterns."""
    return all(
        re.search(pattern, prediction, re.IGNORECASE)
        for pattern in required_patterns
    )

def regex_eval(predictions: list[str], pattern: str) -> float:
    matches = sum(bool(re.search(pattern, p)) for p in predictions)
    return matches / len(predictions)

# Use for: format compliance ("contains valid JSON"), keyword presence,
#          structured output validation
```

### Embedding Similarity

```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def semantic_similarity_eval(
    predictions: list[str],
    references: list[str],
    embed_fn,
    threshold: float = 0.85
) -> dict:
    pred_embeddings = embed_fn(predictions)
    ref_embeddings = embed_fn(references)

    similarities = [
        cosine_similarity([p], [r])[0][0]
        for p, r in zip(pred_embeddings, ref_embeddings)
    ]

    return {
        "mean_similarity": np.mean(similarities),
        "pass_rate": sum(s >= threshold for s in similarities) / len(similarities),
        "similarities": similarities
    }

# Use for: summarization (semantic equivalence), open-ended answers where
#          exact wording doesn't matter but meaning does
```

### Code Execution (pass@k)

```python
def pass_at_k_eval(
    model: callable,
    problems: list[dict],
    k: int = 1,
    n_samples: int = 10,
    temperature: float = 0.8
) -> float:
    """
    pass@k: probability that at least one of k samples passes all tests.
    Estimate using n samples (n >= k).
    """
    pass_counts = []

    for problem in problems:
        samples = [
            model(problem["prompt"], temperature=temperature)
            for _ in range(n_samples)
        ]
        # Count how many samples pass all test cases
        passes = sum(
            run_test_cases(sample, problem["test_cases"])
            for sample in samples
        )
        pass_counts.append(passes)

    # Unbiased estimator for pass@k
    def pass_at_k_estimate(n: int, c: int, k: int) -> float:
        if n - c < k:
            return 1.0
        return 1.0 - float(comb(n - c, k)) / float(comb(n, k))

    return np.mean([
        pass_at_k_estimate(n_samples, c, k)
        for c in pass_counts
    ])
```

---

## Eval Metrics Reference

| Metric | Formula | Use Case |
|---|---|---|
| **Accuracy** | correct / total | Classification, extraction |
| **Precision** | TP / (TP + FP) | When false positives are costly |
| **Recall** | TP / (TP + FN) | When missing items is costly |
| **F1** | 2 × (P × R) / (P + R) | Balance of precision and recall |
| **pass@k** | P(at least 1 of k passes) | Code generation |
| **ROUGE-L** | Longest common subsequence overlap | Summarization |
| **BERTScore** | Embedding similarity of token pairs | Semantic similarity |
| **Faithfulness** | Supported claims / total claims | RAG grounding |
| **Answer relevance** | How well answer addresses question | RAG, QA |
| **Context precision** | Relevant retrieved docs / total retrieved | RAG retrieval quality |

---

## LLM-as-Judge

For open-ended tasks where exact match is not meaningful, use an LLM as the evaluator.

### Absolute Scoring (1–5)

```python
def llm_judge_absolute(
    input_text: str,
    model_output: str,
    reference_answer: str,
    criterion: str,
    judge_model: str = "gpt-4o"
) -> dict:
    prompt = f"""You are an expert evaluator. Score the following response
on a scale of 1-5 for {criterion}.

Scoring rubric:
1: Completely wrong or irrelevant
2: Partially correct but missing key aspects
3: Mostly correct with minor issues
4: Correct with only very minor issues
5: Perfect or near-perfect response

Question: {input_text}
Reference answer: {reference_answer}
Response to evaluate: {model_output}

Output JSON: {{"score": <1-5>, "justification": "<brief explanation>"}}"""

    result = call_llm(prompt, model=judge_model, temperature=0)
    return json.loads(result)
```

### Pairwise Comparison (A/B Testing)

```python
def llm_judge_pairwise(
    input_text: str,
    response_a: str,
    response_b: str,
    criteria: list[str],
    judge_model: str = "gpt-4o"
) -> dict:
    criteria_str = "\n".join(f"- {c}" for c in criteria)

    prompt = f"""Compare these two responses to the same question.
Consider: {criteria_str}

Question: {input_text}

Response A:
{response_a}

Response B:
{response_b}

Which is better? Output JSON:
{{"winner": "A" | "B" | "tie", "reasoning": "<explanation>"}}"""

    result = call_llm(prompt, model=judge_model, temperature=0)
    return json.loads(result)

def evaluate_with_position_debiasing(
    input_text: str,
    response_a: str,
    response_b: str
) -> dict:
    """Run pairwise comparison both ways to cancel position bias."""

    result_ab = llm_judge_pairwise(input_text, response_a, response_b)
    result_ba = llm_judge_pairwise(input_text, response_b, response_a)

    # Normalize: result_ba's "A" is actually model B
    winner_ab = result_ab["winner"]
    winner_ba = "B" if result_ba["winner"] == "A" else ("A" if result_ba["winner"] == "B" else "tie")

    if winner_ab == winner_ba:
        return {"winner": winner_ab, "confidence": "high"}
    else:
        return {"winner": "tie", "confidence": "low", "note": "Position bias detected"}
```

**Always run pairwise comparisons in both orderings and require agreement.** LLM judges have a significant position bias — they favor the first response presented.

### Multi-Dimensional Scoring

```python
def llm_judge_multidimensional(
    input_text: str,
    context: str,
    model_output: str,
    judge_model: str = "gpt-4o"
) -> dict:
    prompt = f"""Score this response on each dimension (1-5):

Dimensions:
- Accuracy: factual correctness
- Completeness: covers all aspects of the question
- Conciseness: no unnecessary information
- Tone: appropriate for the context

Question: {input_text}
Context: {context}
Response: {model_output}

Output JSON:
{{
  "accuracy": <1-5>,
  "completeness": <1-5>,
  "conciseness": <1-5>,
  "tone": <1-5>,
  "overall": <1-5>,
  "justification": "<brief explanation>"
}}"""

    result = call_llm(prompt, model=judge_model, temperature=0)
    return json.loads(result)
```

---

## Building Evaluation Datasets

### Golden Test Set Guidelines

| Task Complexity | Minimum Examples | Recommended |
|---|---|---|
| Simple classification (2 classes) | 50 | 200+ |
| Multi-class classification | 100 | 500+ |
| Entity extraction | 100 | 300+ |
| Summarization | 50 | 200+ |
| Q&A / RAG | 100 | 500+ |
| Code generation | 50 | 200+ |
| Complex generation tasks | 200 | 500+ |

### Dataset Composition

```
A well-balanced eval set:
  60% — Happy path examples (typical, well-formed inputs)
  20% — Edge cases (unusual inputs, boundary conditions)
  10% — Adversarial examples (attempts to confuse the model)
  10% — Regression examples (past failures that have been fixed)
```

### Creating a Labeled Dataset

```python
def create_eval_dataset(
    data_sources: list,
    labeling_guidelines: str,
    n_examples: int = 200
) -> list[dict]:
    """
    Process for creating a high-quality eval dataset:

    1. Sample representative examples from each data source
    2. Write clear labeling guidelines for annotators
    3. Have 2+ annotators label independently
    4. Calculate inter-annotator agreement
    5. Resolve disagreements via discussion or expert arbitration
    6. Create a held-out test set (never used for prompt tuning)
    """
    pass

def calculate_inter_annotator_agreement(
    annotations_1: list,
    annotations_2: list,
    categories: list[str]
) -> float:
    """
    Cohen's kappa: agreement beyond chance.
    Target: kappa > 0.7 (substantial agreement)
    kappa < 0.4: poor agreement → labeling guidelines need improvement
    """
    from sklearn.metrics import cohen_kappa_score
    return cohen_kappa_score(annotations_1, annotations_2, labels=categories)
```

---

## Eval-Driven Development Workflow

```
Step 1: Define success criteria (BEFORE writing prompts)
  → What does "good" look like for this task?
  → Pick measurable metrics (accuracy, LLM-as-judge score, pass@k)
  → Set a minimum acceptable quality threshold

Step 2: Build the eval dataset
  → 50-200 (input, expected_output) pairs
  → Include edge cases and adversarial examples
  → Hold out 20% as a final test set (never use for tuning)

Step 3: Establish baseline
  → Run the simplest possible zero-shot prompt
  → Record the exact score — this is your baseline

Step 4: Iterate
  → Change ONE variable at a time
  → Run the full eval after every change
  → Only keep changes that improve the score

Step 5: Regression testing
  → Maintain a fast subset (~20 cases) that runs in CI/CD
  → Alert when any category drops >2%

Step 6: Production monitoring
  → Sample production traffic
  → Run automated quality checks
  → Alert on quality degradation

Cardinal rule: Every prompt change is motivated by eval results, not intuition.
```

### CI/CD Integration

```python
# .github/workflows/eval.yml concept
# Three evaluation stages:
#
# Stage 1: Quick smoke test (< 2 minutes, on every PR)
#   → 20 most representative cases
#   → Blocks merge if score drops >5%
#
# Stage 2: Full eval (< 30 minutes, nightly)
#   → Full eval set (200-500 cases)
#   → Detailed report with per-category breakdown
#   → Alerts on any category dropping >2%
#
# Stage 3: Human review (weekly)
#   → Sample 50 production outputs
#   → Domain expert review
#   → Catches issues automated evals miss

def run_ci_eval(
    prompt_version: str,
    fast_eval_set: list[dict],
    previous_scores: dict
) -> dict:
    current_scores = run_eval(prompt_version, fast_eval_set)

    regressions = {
        category: current - previous_scores[category]
        for category, current in current_scores.items()
        if current - previous_scores[category] < -0.05  # >5% regression
    }

    return {
        "pass": len(regressions) == 0,
        "scores": current_scores,
        "regressions": regressions
    }
```

---

## Custom Scoring Functions

For domain-specific criteria that general LLM-as-judge doesn't capture:

```python
def evaluate_medical_response(prediction: str, reference: dict) -> dict:
    """Custom scorer for medical question answering."""
    scores = {}

    # 1. Safety: does it recommend seeking professional care when appropriate?
    if reference.get("requires_medical_advice"):
        scores["safety"] = 1.0 if re.search(
            r'doctor|physician|medical|consult|seek.*care|emergency',
            prediction, re.IGNORECASE
        ) else 0.0
    else:
        scores["safety"] = 1.0  # Not applicable

    # 2. Accuracy: does it contain the required medical facts?
    required_facts = reference.get("required_facts", [])
    if required_facts:
        contained = sum(
            fact.lower() in prediction.lower() for fact in required_facts
        )
        scores["fact_coverage"] = contained / len(required_facts)
    else:
        scores["fact_coverage"] = 1.0

    # 3. Format: appropriate length and structure?
    word_count = len(prediction.split())
    scores["appropriate_length"] = 1.0 if 50 <= word_count <= 500 else 0.5

    # Weighted overall score
    weights = {"safety": 0.5, "fact_coverage": 0.3, "appropriate_length": 0.2}
    scores["overall"] = sum(
        scores[k] * weights[k] for k in weights
    )

    return scores
```

---

## Eval Tools and Platforms

| Tool | Type | Strengths | Pricing |
|---|---|---|---|
| **Braintrust** | Managed platform | Clean UI, logging, A/B testing | Free tier + paid |
| **Promptfoo** | Open-source CLI | Fast, code-first, CI-friendly | Free |
| **LangSmith** | Managed platform | Deep LangChain integration | Free tier + paid |
| **Humanloop** | Managed platform | Strong human eval workflows | Paid |
| **RAGAS** | Open-source library | RAG-specific metrics | Free |
| **Custom framework** | DIY | Full control | Developer time |

**Choosing a platform:**
- For teams: Braintrust or LangSmith (collaboration, logging, history)
- For CI/CD integration: Promptfoo (YAML-based, runs in GitHub Actions)
- For RAG evaluation: RAGAS (specialized metrics)
- For maximum control: custom 100-line Python framework

### Promptfoo Configuration Example

```yaml
# promptfooconfig.yaml
prompts:
  - file://prompts/classify_v1.txt
  - file://prompts/classify_v2.txt

providers:
  - openai:gpt-4o
  - anthropic:claude-opus-4-5

tests:
  - vars:
      text: "I love this product, highly recommend!"
    assert:
      - type: equals
        value: "positive"
  - vars:
      text: "This doesn't work at all, terrible experience"
    assert:
      - type: equals
        value: "negative"
  - vars:
      text: "The product is okay, nothing special"
    assert:
      - type: equals
        value: "neutral"
      - type: latency
        threshold: 3000  # max 3 seconds
```

---

## Cost Estimation for Eval Pipelines

```
Assumptions:
- 500 eval cases
- Using GPT-4o as judge ($2.50/1M input, $10/1M output)
- Average judge call: 1,000 input tokens, 200 output tokens

Cost per eval run:
  Input:  500 × 1,000 / 1M × $2.50 = $1.25
  Output: 500 × 200 / 1M × $10    = $1.00
  Total:                           = $2.25 per eval run

If you run evals:
  Per PR:        ~$0.45 (fast suite, ~100 cases)
  Nightly:       ~$2.25 (full suite)
  Monthly:       ~$67.50 (30 nightly runs)

Compare to the cost of deploying a bad prompt that degrades user experience.
```

---

## Key Numbers to Know

| Metric | Guideline |
|---|---|
| Minimum eval dataset size | 50 for simple tasks, 200+ for complex |
| Inter-annotator agreement target | Cohen's kappa > 0.7 |
| LLM-as-judge agreement with humans | > 80% within 1 point (5-point scale) |
| Position bias mitigation | Run both orderings, require agreement |
| CI eval runtime target | < 5 minutes |
| Full eval runtime target | < 30 minutes |
| Regression tolerance | 2% drop per category |
| Production sample review | Weekly, minimum 50 examples |
| Red team frequency | After every major prompt/model change |
| Eval dataset refresh | Quarterly with new production data |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Build an Eval Suite for a Customer Service Chatbot** -- Build a comprehensive eval dataset following the golden test set guidelines and dataset composition rules (60/20/10/10 split). Practices building eval cases, scoring functions (contains-based matching), running the full eval pipeline, and detecting regressions.
- **Exercise 2: Implement an LLM-as-Judge Scorer with Calibration** -- Build judge rubrics for multiple quality dimensions, implement the LLM-as-judge scoring pipeline (prompt -> call -> parse JSON -> normalize), and calibrate against human annotations targeting >80% within-1 agreement.
- **Exercise 6: Implement Eval Regression Testing** -- Compare eval results across prompt versions, detect regressions (>2% drop), and generate CI-friendly reports. Directly practices "Eval-Driven Development Workflow" Step 5 and the CI/CD integration pattern.

See also `examples.py` for reference implementations:
- "Scoring functions" section -- exact_match_scorer, contains_scorer, regex_scorer
- "Eval pipeline" section -- run_eval_pipeline with regression detection
- "LLM-as-judge scorer" section -- full judge implementation with configurable rubrics
- "Simple A/B test analyzer" section -- z-test comparison with significance testing

---

## Interview Q&A: Evaluation Frameworks

**Q: How do you build and maintain an eval suite for LLM features?**

Define success criteria before writing prompts. Build a dataset of 50–200 representative (input, expected_output) pairs, including edge cases, adversarial examples, and past failure modes. Hold out 20% as a final test set — never used for prompt tuning. Write a simple baseline prompt, run the full eval, and record the score. Every subsequent iteration changes one thing and runs the eval. Store prompt versions with their scores so you can reason about what's actually working. Integrate a fast subset (20 cases, < 5 minutes) into CI/CD to block regressions. Run the full eval nightly. Refresh the dataset quarterly with production examples. Never deploy a change that regresses on the test set.

**Q: When do you use LLM-as-judge vs. other eval methods?**

Use LLM-as-judge when the task involves open-ended quality that can't be captured by exact match — tone, helpfulness, coherence, creativity, and similar subjective criteria. For classification and extraction, exact match is more reliable and much cheaper. For code, execution is more reliable. For semantic equivalence, embedding similarity can work. LLM-as-judge is most powerful for pairwise comparisons (A/B testing prompts), where the relative ordering is more important than the absolute score. Always calibrate your LLM judge against human judgments (target: > 80% agreement within one point on a 5-point scale) and always run pairwise comparisons both ways to cancel position bias.

**Q: What is inter-annotator agreement and why does it matter?**

Inter-annotator agreement measures how consistently different people apply the same labeling criteria. Cohen's kappa corrects for agreement by chance: kappa > 0.7 indicates substantial agreement, meaning your labeling guidelines are clear enough that different annotators largely agree. Kappa < 0.4 indicates poor agreement — the criteria are ambiguous, and the labels are essentially unreliable. Why it matters: if your evaluation dataset has inconsistent labels, your eval metrics are meaningless. A model that scores 80% accuracy on a poorly labeled dataset might actually be better or worse than 80% — you can't tell. High inter-annotator agreement is a prerequisite for meaningful evaluation.
