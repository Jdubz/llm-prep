# 03 — Advanced Prompting Strategies

## Self-Consistency

Self-consistency generates multiple independent answers to the same question and takes the majority vote. Instead of relying on a single sampling path, it exploits the diversity of multiple samples to filter noise and improve accuracy.

### When to Use Self-Consistency

- Reasoning tasks with verifiable answers (math, logic, code)
- High-stakes decisions where being wrong is costly
- Tasks where the model is near its accuracy ceiling (adding examples won't help much more)
- When model confidence is hard to calibrate otherwise

Not appropriate for:
- Creative writing or subjective tasks (no "correct" answer to vote on)
- Tasks requiring a single consistent voice or narrative
- Cost-sensitive applications (multiplies API calls by N)

### Implementation

```python
from collections import Counter
import re

def self_consistent_solve(
    question: str,
    num_samples: int = 5,
    temperature: float = 0.7
) -> dict:
    """
    Generate N reasoning chains and return the majority answer.
    Returns: {"answer": str, "confidence": float, "all_answers": list}
    """
    prompt = f"""Solve this step by step. After your reasoning, write your
final answer on the last line as: ANSWER: <answer>

Question: {question}"""

    answers = []
    for _ in range(num_samples):
        response = llm_call(prompt, temperature=temperature)
        # Extract the final answer
        match = re.search(r'ANSWER:\s*(.+)', response, re.IGNORECASE)
        if match:
            answers.append(match.group(1).strip())

    if not answers:
        return {"answer": None, "confidence": 0.0, "all_answers": []}

    counter = Counter(answers)
    most_common, count = counter.most_common(1)[0]
    confidence = count / len(answers)

    return {
        "answer": most_common,
        "confidence": confidence,
        "all_answers": answers,
        "agreement_rate": confidence
    }
```

### Production Considerations

- **Temperature:** 0.5–0.7 gives enough diversity for meaningful votes without going incoherent
- **Sample count:** 3 is often sufficient for common tasks; 5–7 for harder problems
- **Cost:** N× the base cost — only use where accuracy gains justify it
- **Parallelization:** Run all N samples concurrently to minimize latency impact
- **Partial agreement:** If samples disagree significantly (< 40% agreement), the model may not know the answer — treat as low-confidence

---

## Tree of Thought

Tree of Thought (ToT) extends chain-of-thought by exploring multiple reasoning branches simultaneously and evaluating them. Instead of committing to a single reasoning path, the model explores several candidate continuations, evaluates each, and either backtracks or expands the most promising paths.

### Conceptual Structure

```
Root Problem
├── Path A (good approach)
│   ├── A.1 (promising)
│   │   ├── A.1.1 → Solution (correct) ✓
│   │   └── A.1.2 → Dead end ✗
│   └── A.2 (abandoned after evaluation)
└── Path B (wrong approach)
    └── B.1 → Dead end ✗ (pruned early)
```

### Practical ToT Implementation

Full ToT with separate evaluation models is complex and expensive. A practical simplified version:

```python
def tree_of_thought(problem: str, k: int = 3, depth: int = 2) -> str:
    """
    Simplified ToT: generate k thought branches, evaluate, expand the best.
    """
    # Step 1: Generate initial approaches
    branches_prompt = f"""For the following problem, generate {k} distinct
high-level approaches or solution strategies. Be creative and consider
fundamentally different approaches.

Problem: {problem}

Format:
Approach 1: [brief description]
Approach 2: [brief description]
Approach 3: [brief description]"""

    branches_response = llm_call(branches_prompt)
    # Parse into list of approaches

    # Step 2: Evaluate each approach
    eval_prompt = f"""Evaluate these approaches for solving the problem.
For each, rate: (1) likely to work, (2) computational difficulty.

Problem: {problem}
{branches_response}

Which approach is most promising and why? Choose one."""

    best_approach = llm_call(eval_prompt)

    # Step 3: Solve using the best approach
    solve_prompt = f"""Solve the following problem using this approach:
{best_approach}

Problem: {problem}

Work through it step by step."""

    return llm_call(solve_prompt)
```

**When Tree of Thought is worth the complexity:**
- Complex planning problems with many possible paths
- Puzzles, logical deduction, optimization
- Tasks where the first approach is often wrong

**Practical reality:** For most production tasks, self-consistency is simpler and nearly as effective. Reserve full ToT for truly hard reasoning problems where multiple distinct strategies need to be explored.

---

## Meta-Prompting and Automatic Prompt Optimization

### Meta-Prompting

Meta-prompting uses an LLM to generate or refine prompts. Instead of manually crafting the prompt, you describe the task and ask the model to generate an effective prompt for it.

**Simple meta-prompt:**
```
You are an expert prompt engineer. Generate an effective prompt for the
following task.

Task: {task_description}
Expected output format: {format_description}
Key requirements: {requirements}
Common failure modes to avoid: {failure_modes}

Generate a complete, production-ready prompt template.
```

**Iterative refinement loop:**
```python
def meta_optimize_prompt(
    task: str,
    initial_prompt: str,
    eval_set: list[dict],
    iterations: int = 5
) -> str:
    current_prompt = initial_prompt

    for i in range(iterations):
        # Evaluate current prompt
        score, failures = evaluate_prompt(current_prompt, eval_set)

        # Use meta-LLM to improve
        improve_prompt = f"""You are improving a prompt for this task: {task}

Current prompt:
{current_prompt}

Current accuracy: {score:.1%}

These examples FAILED:
{format_failures(failures[:5])}

Identify the specific failure pattern and suggest an improved prompt.
Focus on fixing the identified failures without breaking working cases."""

        improved = llm_call(improve_prompt)
        current_prompt = extract_prompt(improved)

    return current_prompt
```

### DSPy

DSPy (Declarative Self-improving Prompts) is a framework that treats prompts as learnable program components. Instead of manually writing prompts, you define the program's structure and let DSPy optimize the prompts automatically using your metric function.

**Core concept:**
```python
import dspy

class RAGPipeline(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.generate = dspy.ChainOfThought("context, question -> answer")

    def forward(self, question):
        context = self.retrieve(question).passages
        answer = self.generate(context=context, question=question)
        return answer

# Define your metric
def accuracy_metric(example, pred, trace=None):
    return example.answer.lower() in pred.answer.lower()

# Optimize prompts automatically
optimizer = dspy.BootstrapFewShot(metric=accuracy_metric)
optimized_pipeline = optimizer.compile(RAGPipeline(), trainset=train_examples)
```

**When DSPy is worth it:**
- You have a well-defined, measurable metric
- You have training examples (50+)
- Manual prompt optimization has plateaued
- The task is complex enough that automatic optimization can find non-obvious prompt patterns

---

## Constitutional AI Prompting

Constitutional AI (Anthropic) is a training technique, but its principles directly inform a useful prompting pattern: **generate-critique-revise**.

### The Pattern

1. Generate an initial response
2. Critique it against specific principles or requirements
3. Revise based on the critique
4. Optionally: iterate

**Implementation:**
```python
def constitutional_generate(
    prompt: str,
    principles: list[str]
) -> str:
    # Step 1: Initial generation
    initial_response = llm_call(f"Answer this question: {prompt}")

    # Step 2: Self-critique
    critique_prompt = f"""Review this response against the following principles.
For each principle, note whether the response violates it.

Principles:
{chr(10).join(f'{i+1}. {p}' for i, p in enumerate(principles))}

Response:
{initial_response}

For each violation found, explain what needs to change."""

    critique = llm_call(critique_prompt)

    # Step 3: Revision
    revision_prompt = f"""Based on this critique, revise the response.

Original question: {prompt}
Original response: {initial_response}
Critique: {critique}

Write an improved response that addresses all issues identified."""

    return llm_call(revision_prompt)
```

**Principles examples for a customer support application:**
```
1. Only make claims that are directly supported by the provided documentation
2. Never promise timelines or outcomes that aren't guaranteed
3. Acknowledge uncertainty explicitly rather than guessing
4. Always offer a next step or escalation path
5. Be concise — no unnecessary caveats or hedging
```

### Self-Refinement Loop

For tasks where quality can be iteratively improved:

```python
def self_refine(prompt: str, iterations: int = 3) -> str:
    response = llm_call(prompt)

    for _ in range(iterations):
        refine_prompt = f"""Review and improve the following response.

Original request: {prompt}
Current response: {response}

Critique what could be better (be specific), then write an improved version.
If the response is already excellent, just write the response unchanged."""

        refined = llm_call(refine_prompt)
        # Check if the model indicates no improvement needed
        if "already excellent" in refined.lower() or "no improvement" in refined.lower():
            break
        response = extract_revised_response(refined)

    return response
```

---

## Prompt Caching

Provider-side prompt caching automatically reuses computed KV caches for repeated prompt prefixes. This is one of the highest-ROI optimizations for RAG and agent workloads.

### Anthropic Prompt Caching

```python
import anthropic

client = anthropic.Anthropic()

# Structure: cacheable content first, dynamic content last
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are a helpful customer support agent for Acme Corp...",
            "cache_control": {"type": "ephemeral"}  # ← Cache this
        }
    ],
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "<knowledge_base>\n[5,000 tokens of docs]\n</knowledge_base>",
                    "cache_control": {"type": "ephemeral"}  # ← Cache this too
                },
                {
                    "type": "text",
                    "text": user_message  # ← Not cached (changes per request)
                }
            ]
        }
    ]
)
```

**Key requirements:**
- Minimum prefix length: 1,024 tokens (Sonnet), 2,048 tokens (Opus)
- Cache TTL: 5 minutes (default), up to 1 hour with extended caching
- Cost savings: 90% on cached tokens, with a small surcharge for the first cache-miss write

### OpenAI Prompt Caching

Automatic for prompts >1,024 tokens — no API changes needed:
```python
# OpenAI caches automatically; structure your prompt with static content first
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "Long stable system prompt..."  # This gets cached
        },
        {
            "role": "user",
            "content": user_message  # This varies
        }
    ]
)
# 50% discount on cached input tokens reported in usage object
print(response.usage.prompt_tokens_details.cached_tokens)
```

### Designing for Cache-Friendliness

```
# Cache-friendly structure:
[System prompt — 2,000 tokens]       ← always the same
[Tool definitions — 1,500 tokens]    ← same per feature
[Retrieved context — 3,000 tokens]   ← same for same query
[Conversation history — 1,000 tokens] ← grows slowly
[Current user message — 200 tokens]  ← changes every turn

Cache hit rate targets:
- FAQs and repeated queries:   30-60% hit rate
- RAG with common docs:        20-40% hit rate
- Unique conversations:        < 5% hit rate (not worth caching)
```

---

## Prompt Optimization Workflow

A rigorous, repeatable process for improving prompts:

### 6-Step Process

```
Step 1: Define success criteria
  → What does "good" look like?
  → Pick a measurable metric (accuracy, F1, LLM-as-judge score)

Step 2: Build a test set
  → Collect 50–200 representative (input, expected_output) pairs
  → Include edge cases, failure modes, distribution corners
  → Hold out 20% for final validation

Step 3: Establish baseline
  → Write the simplest possible prompt
  → Run it against the test set
  → Document the score

Step 4: Iterate
  → Change ONE variable at a time
  → Run the full test set
  → Only keep changes that improve the score
  → Document what you changed and why

Step 5: Regression testing
  → Maintain a fast subset (~20 cases) that runs in CI
  → Never deploy a change that regresses on this set

Step 6: Production monitoring
  → Sample production outputs
  → Run automated quality checks
  → Alert on quality degradation
```

### What Actually Moves the Needle

Ranked by typical impact:

1. **Clearer instructions** (the model is doing exactly what you asked, just not what you meant)
2. **Few-shot examples for edge cases** (calibrate decision boundaries)
3. **Restructuring the prompt** (most important content first and last)
4. **Breaking into smaller chains** (focused prompts are more reliable than complex ones)
5. **Output format specification** (explicit schema reduces parsing failures)
6. **Model upgrade** (sometimes the only path when others plateau)

### Regression Testing Setup

```python
import json
from datetime import datetime

class PromptRegistry:
    """Track prompt versions with their eval scores."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path

    def save_version(
        self,
        prompt_id: str,
        prompt_text: str,
        eval_results: dict,
        version: str = None
    ):
        version = version or datetime.now().isoformat()
        record = {
            "prompt_id": prompt_id,
            "version": version,
            "prompt": prompt_text,
            "eval_results": eval_results,
            "timestamp": datetime.now().isoformat()
        }
        # Save to storage (JSON file, database, etc.)
        self._save(record)

    def get_best_version(self, prompt_id: str, metric: str = "accuracy") -> dict:
        versions = self._load_all(prompt_id)
        return max(versions, key=lambda v: v["eval_results"].get(metric, 0))

    def compare_versions(self, prompt_id: str, v1: str, v2: str) -> dict:
        """Compare two versions across all eval metrics."""
        pass  # Implementation
```

---

## Multi-Turn Prompt Design

Multi-turn conversations require careful management of context, consistency, and memory.

### Context Management Strategies

**1. Full History (simple, expensive)**
```python
def chat_full_history(messages: list[dict], user_message: str) -> str:
    messages.append({"role": "user", "content": user_message})
    response = llm_call(messages=messages)
    messages.append({"role": "assistant", "content": response})
    return response
```

**2. Sliding Window (cheap, loses old context)**
```python
def chat_sliding_window(
    messages: list[dict],
    user_message: str,
    max_turns: int = 10
) -> str:
    # Keep last N turns
    messages = messages[-max_turns * 2:]  # 2 messages per turn
    messages.append({"role": "user", "content": user_message})
    response = llm_call(messages=messages)
    return response
```

**3. Summarization (best balance)**
```python
def chat_with_summarization(
    messages: list[dict],
    summary: str,
    user_message: str,
    summarize_after: int = 10
) -> tuple[str, str]:
    # Add new message
    messages.append({"role": "user", "content": user_message})

    # Update summary if needed
    if len(messages) > summarize_after * 2:
        old_messages = messages[:-6]  # Keep last 3 turns verbatim
        summary = llm_call(
            f"Summarize this conversation concisely:\n{format_messages(old_messages)}"
        )
        messages = messages[-6:]

    # Inject summary as context
    context_message = {
        "role": "system",
        "content": f"Previous conversation summary: {summary}"
    }

    response = llm_call(messages=[context_message] + messages)
    messages.append({"role": "assistant", "content": response})

    return response, summary
```

### Multi-Turn Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Silently truncating history | Model loses context without knowing it | Alert before truncation; summarize instead |
| Growing system prompt | The system prompt duplicates every turn | Keep system prompt static; use message history for context |
| No conversation identifier | Cannot debug or audit specific conversations | Assign session IDs and log every turn |
| Forgetting the system prompt | If context overflows, the system prompt may be truncated | Always reserve space for the system prompt |

---

## Advanced Patterns for Interviews

### Least-to-Most Prompting

Decompose complex problems into subproblems of increasing difficulty:

```
Problem: {complex problem}

First, solve the simplest version of this problem.
Then, solve a slightly harder version.
Finally, use those insights to solve the full problem.

Simple version: [model identifies and solves]
Harder version: [builds on simple solution]
Full problem: [applies combined insights]
```

This is particularly effective for programming tasks and multi-step reasoning where the problem has natural substructure.

### Retry with Error Feedback

The most reliable pattern for structured output when provider enforcement is not available:

```python
def robust_structured_call(
    prompt: str,
    output_schema: type,
    max_retries: int = 3
) -> dict:
    error_context = ""

    for attempt in range(max_retries):
        full_prompt = prompt + error_context
        response = llm_call(full_prompt, temperature=0)

        try:
            parsed = output_schema.model_validate_json(response)
            return parsed.model_dump()
        except Exception as e:
            error_context = f"\n\nYour previous response failed validation:\nError: {e}\nResponse: {response}\n\nPlease try again, fixing these issues."

    raise ValueError(f"Failed to get valid structured output after {max_retries} attempts")
```

### Directional Stimulus Prompting

Provide "hints" or directions to guide the model toward desired outputs without explicitly telling it the answer:

```
Classify this text. Consider:
- Hint 1: Look for emotional language indicators
- Hint 2: Pay attention to adjectives and their intensity
- Hint 3: Note whether the overall conclusion is positive or negative

Text: {text}
Classification:
```

### Prompt Ensembles

Run the same input through multiple different prompts and aggregate the results:

```python
def ensemble_classify(text: str) -> dict:
    prompts = [
        f"What is the sentiment of this text? Answer: positive/neutral/negative\n{text}",
        f"Determine if this text is: 1=positive, 0=neutral, -1=negative\n{text}",
        f"From a customer's perspective, classify their satisfaction: satisfied/neutral/dissatisfied\n{text}"
    ]

    results = [llm_call(p, temperature=0) for p in prompts]
    # Normalize and aggregate results
    normalized = [normalize_sentiment(r) for r in results]
    return aggregate_votes(normalized)
```

---

## Key Numbers and Reference

| Metric | Value |
|---|---|
| Anthropic prompt cache minimum | 1,024 tokens (Sonnet), 2,048 tokens (Opus) |
| Anthropic cache savings | 90% on cached tokens |
| OpenAI cache minimum | 1,024 tokens (automatic) |
| OpenAI cache savings | 50% on cached tokens |
| Self-consistency optimal samples | 5–7 for most tasks |
| Model routing cost savings | 50–80% with 70–80% small model routing |
| Batch API discount (OpenAI) | 50% |
| Typical few-shot examples | 3–5 |
| CI eval runtime target | <5 minutes (fast subset) |
| Prompt version control | Every version with eval scores |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Classification Chain for Ambiguous Inputs** -- The two-step classification chain is a simplified version of the "Self-Refinement Loop" pattern (generate, evaluate, refine). Step 2 re-examines the Step 1 result using CoT reasoning, similar to the critique-and-revise approach in "Constitutional AI Prompting."

- **Exercise 3: Reliable JSON Output for Complex Schema** -- The retry-with-feedback pattern directly implements the "Retry with Error Feedback" advanced pattern from this file. The `robust_structured_call()` code template shown here is exactly the pattern needed for handling validation failures.

- **Exercise 4: Optimize a Poorly-Performing Prompt** -- Practices the "Prompt Optimization Workflow" -> "6-Step Process." The FAILURE_CASES in the exercise serve as the test set (Step 2). Analyzing failure modes (Step 4: change one variable at a time) and using the "What Actually Moves the Needle" ranking guides which improvements to try first.

- **Exercise 5: Self-Consistency with Majority Voting** -- Directly implements the "Self-Consistency" section of this file. All production considerations apply: temperature 0.5-0.7, parallel execution, confidence threshold for low-agreement detection. The exercise extends the basic pattern with domain-specific logic (defaulting to "breaking" when uncertain).

- **Exercise 6: Prompt Injection Detector** -- The detector benefits from the "Constitutional AI Prompting" pattern: you can structure the detection prompt as a principled evaluation (does the input violate principle X?). The "Directional Stimulus Prompting" technique is useful for guiding the detector to focus on intent rather than keywords.

See also `examples.py` sections 6 (Self-Consistency with majority voting) and 7 (Retry-with-Feedback for structured output) for complete runnable implementations of these advanced patterns.

---

## Interview Q&A: Advanced Strategies

**Q: What is self-consistency and when do you use it in production?**

Self-consistency generates multiple independent answers (typically 5–7) and takes the majority vote. It's the most reliable way to improve accuracy on reasoning tasks without changing the model. Use it when: the task has a verifiable correct answer (math, logic, code), the model is performing near its ceiling with other techniques, and the accuracy improvement justifies the N× cost. In production, always run samples concurrently to limit latency impact. If samples disagree significantly (< 40% agreement), treat the result as low-confidence and potentially flag for human review.

**Q: How do you structure prompts for provider-side caching?**

Provider-side caching (Anthropic's explicit cache_control or OpenAI's automatic caching) reuses computed KV caches for repeated prompt prefixes. Design principle: put all stable, shared content first (system prompt, tool definitions, retrieved knowledge base), and put the dynamic, request-specific content last (current user message). The longer the shared prefix, the higher the cache hit rate. For a RAG system, a well-structured 5,000-token prefix (system prompt + knowledge base) might save 90% of input token costs on Anthropic if the same documents are queried repeatedly. Always benchmark cache hit rates to verify the savings materialize.

**Q: How do you systematically improve prompts when they plateau?**

When simple prompt iteration plateaus: (1) Analyze failure modes — most failures cluster in predictable patterns. Fix the pattern, not individual cases. (2) Consider meta-prompting — describe the failures to a capable model and ask it to propose prompt changes. (3) Switch to few-shot CoT examples specifically for failure cases. (4) Consider prompt chaining — break the task into steps; often one step is harder than others and needs focused attention. (5) Try a better model — sometimes the architecture is the constraint. (6) Consider fine-tuning if prompting has genuinely been exhausted and the task is well-defined. The cardinal rule throughout: every change must be validated against the full eval set, not just the cases you're trying to fix.

**Q: What is DSPy and when is it worth using?**

DSPy is a framework that treats prompts as learnable program components, automatically optimizing few-shot examples and instructions using a metric function and training examples. It's worth using when: you have a well-defined measurable metric, at least 50 training examples, and manual prompt optimization has plateaued. It's not worth using for: simple tasks where a well-crafted zero-shot prompt works fine, tasks without good automated metrics, or exploratory projects where you're still defining what "good" means. The learning curve is real, and the optimization process requires compute — budget time for it.
