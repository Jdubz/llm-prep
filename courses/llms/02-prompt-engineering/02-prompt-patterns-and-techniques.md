# 02 — Prompt Patterns and Techniques

## Choosing Your Prompting Approach

Use this decision tree when designing a new prompt:

```
What is the task?
├── Classification or labeling
│   └── → Few-shot (3-5 examples) + structured output (JSON)
│         → Include examples near decision boundaries
│         → Temperature = 0
├── Extraction (entities, key info)
│   └── → Clear field definitions + JSON schema
│         → Delimiters around the source text
│         → Temperature = 0
├── Summarization or synthesis
│   └── → Specify length and format explicitly
│         → Define what to include and exclude
│         → Temperature 0.3
├── Complex reasoning (math, logic, planning)
│   └── → Chain-of-thought (explicit or "think step by step")
│         → Consider prompt chaining for multi-step problems
│         → Verify intermediate steps if high-stakes
├── Generation (writing, code, creative)
│   └── → Examples for style calibration if needed
│         → Clear constraints on format, length, tone
│         → Temperature 0.7-1.0
└── Multi-step complex task
    └── → Prompt chaining (separate steps into separate calls)
          → Cache stable prefixes
          → Log intermediate outputs for debugging
```

---

## Standard Prompt Templates

### Classification: Single Label

```
Classify the following support ticket into exactly one category.
Categories: billing | technical | account | feature_request | other

Rules:
- billing: questions about charges, invoices, refunds, payment methods
- technical: product bugs, errors, performance issues
- account: login, access, password, user settings
- feature_request: asking for new capabilities
- other: anything that does not fit the above

Return JSON only: {"category": "<label>", "confidence": 0.0-1.0}

Ticket: {ticket_text}
```

### Classification: Multi-Label

```
Analyze the following support ticket and return all applicable labels.
Labels: billing | technical | account | urgent | escalation_needed

A ticket may have multiple labels (e.g., both "technical" and "urgent").
Return only labels that clearly apply.

Return JSON: {"labels": ["<label1>", "<label2>"], "reasoning": "<brief explanation>"}

Ticket: {ticket_text}
```

### Entity Extraction

```
Extract all entities from the text below.

Entity types to extract:
- PERSON: individual people's names
- ORG: organizations, companies, agencies
- PRODUCT: product names
- DATE: dates, time periods
- AMOUNT: monetary values, quantities

<text>
{source_text}
</text>

Return JSON:
{
  "entities": [
    {"type": "<type>", "text": "<entity text>", "start_idx": <integer>}
  ]
}

If no entities found, return: {"entities": []}
```

### Summarization

```
Summarize the following document.

Requirements:
- Length: 3-5 sentences (maximum 150 words)
- Tone: neutral and factual
- Include: main argument, key evidence, conclusion
- Exclude: tangential details, personal opinions, direct quotes

<document>
{document_text}
</document>

Summary:
```

### RAG Question Answering

```
Answer the user's question using ONLY the provided context documents.

Rules:
- If the answer is not in the provided context, respond with: "I don't have
  enough information to answer that question."
- Do not use information from your training data
- Cite the source by its title or ID when you use it
- If context documents contradict each other, note the contradiction

Context:
<context id="1" title="{doc1_title}">
{doc1_content}
</context>

<context id="2" title="{doc2_title}">
{doc2_content}
</context>

Question: {user_question}

Answer:
```

### Code Generation

```
Write a Python function that {task_description}.

Requirements:
- Function signature: {signature}
- Input: {input_description}
- Output: {output_description}
- Handle edge cases: {edge_cases}
- Include docstring with Args and Returns sections
- Add inline comments for complex logic

Return only the function code, no explanation.
```

### Code Review

```
Review the following code for issues. Focus on:
1. Correctness: logic errors, edge cases
2. Security: injection vulnerabilities, exposed secrets, unsafe operations
3. Performance: inefficient algorithms, unnecessary computation
4. Maintainability: readability, naming, complexity

For each issue found:
- Describe the problem
- Explain the risk or impact
- Suggest a specific fix

If no issues found in a category, write "None found."

<code language="{language}">
{code}
</code>
```

### Chain-of-Thought Template

```
Solve the following problem step by step.

Problem: {problem}

Format your response:
Step 1: [first reasoning step]
Step 2: [second reasoning step]
...
Answer: [final answer]

Do not skip steps. Show all intermediate calculations.
```

### Self-Consistency Wrapper

```python
def self_consistent_answer(question: str, num_samples: int = 5) -> str:
    """Generate multiple answers and return the majority."""
    answers = []
    for _ in range(num_samples):
        prompt = f"""
        Solve this problem step by step, then give your final answer.

        Problem: {question}

        After your reasoning, write "FINAL ANSWER: <answer>" on the last line.
        """
        response = llm_call(prompt, temperature=0.7)
        # Extract the final answer
        if "FINAL ANSWER:" in response:
            answer = response.split("FINAL ANSWER:")[-1].strip()
            answers.append(answer)

    # Return most common answer
    from collections import Counter
    return Counter(answers).most_common(1)[0][0]
```

---

## Provider-Specific Differences

Understanding how different providers interpret prompts helps you write more effective instructions:

| Dimension | OpenAI (GPT-4o) | Anthropic (Claude) | Open-source (Llama) |
|---|---|---|---|
| **System prompt handling** | Strong system/user separation | Very strong operator/user hierarchy | Varies; less consistent |
| **Instruction following** | Excellent | Excellent, tends toward literal interpretation | Good, varies by fine-tune |
| **Format preference** | JSON natively | XML-style delimiters work very well | Markdown |
| **Refusals** | Moderate | Conservative on edge cases | Very permissive (base), varies fine-tune |
| **CoT behavior** | Good implicit CoT | Very explicit, thorough reasoning | Varies |
| **Tool/function use** | Native, excellent | Native, excellent | Requires fine-tuning |
| **Long context performance** | Good to 128K | Excellent to 200K | Degrades at very long contexts |

### OpenAI-Specific Tips

- Use the `json_schema` response format (not just `json_object`) for guaranteed structural conformance
- The `seed` parameter helps with reproducibility (not guaranteed identical)
- `logprobs` output useful for classification confidence without explicit scoring
- `parallel_tool_calls` parameter controls whether multiple tools can be called simultaneously

### Anthropic-Specific Tips

- Claude responds particularly well to XML-style delimiters: `<document>`, `<context>`, `<instructions>`
- "Think step by step" before the question works well for CoT
- Very explicit about uncertainty — if you don't want it to hedge, say so
- Prompt caching activated with cache_control: `{"type": "ephemeral"}` on content blocks
- Extended thinking mode available for complex reasoning at higher cost

### Open-Source Model Tips

- More permissive by default, but outputs can be less consistent
- Use more explicit formatting in prompts
- Constrained decoding (Outlines, SGLang) is much more valuable without provider-enforced JSON
- Test with `temperature=0` first to understand the model's default behavior
- Response quality varies significantly by fine-tune; always eval your specific model

---

## Delimiter Quick Reference

| Delimiter Style | Use Case | Example |
|---|---|---|
| Triple backticks | Code, commands | `` ```python\n{code}\n``` `` |
| Triple quotes | Text passages | `"""text here"""` |
| XML tags | Structured data, documents | `<document>{content}</document>` |
| Square brackets | Section labels | `[USER INPUT]` |
| Hash markers | Section headers | `## Instructions\n## User Input` |
| Pipes | Inline separation | `Title: {title} \| Author: {author}` |

---

## Stop Sequences Reference

Stop sequences tell the model when to stop generating:

| Use Case | Stop Sequence |
|---|---|
| After JSON object closes | `}` or `}\n` |
| After a labeled section | `\n\nUser:` (to stop at the next turn) |
| After a specific line | `END_OF_RESPONSE` |
| After structured output | `</output>` |
| Before reasoning leaks | `Answer:` |

**Example: Stop before over-explanation**
```python
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{
        "role": "user",
        "content": "Classify: {text}\nCategory:"
    }],
    stop=["\n"],  # Stop after the first line
    max_tokens=20
)
```

---

## Common Prompt Patterns

### Classification Pipeline

```python
def classify_text(text: str, categories: list[str], examples: list[dict]) -> dict:
    few_shot = "\n\n".join([
        f"Text: {ex['text']}\nCategory: {ex['category']}"
        for ex in examples
    ])

    prompt = f"""Classify the following text.
Categories: {' | '.join(categories)}

Examples:
{few_shot}

Text: {text}
Category:"""

    response = llm_call(prompt, temperature=0, max_tokens=50, stop=["\n"])
    return {"category": response.strip(), "text": text}
```

### Transformation Pipeline

```python
def transform_format(
    content: str,
    source_format: str,
    target_format: str,
    output_schema: dict
) -> dict:
    prompt = f"""Convert the following content from {source_format} to {target_format}.

Rules:
- Preserve all information from the source
- Do not add information not present in the source
- Follow the target format schema exactly

<source format="{source_format}">
{content}
</source>

Target schema:
{json.dumps(output_schema, indent=2)}

Return only valid JSON matching the schema."""

    response = llm_call(prompt, temperature=0)
    return json.loads(response)
```

### Style Transfer Template

```
Rewrite the following text in {target_style} style.

Style requirements:
- Tone: {tone}
- Audience: {audience}
- Reading level: {reading_level}
- Key: preserve all factual content; change only style

<original>
{text}
</original>

Rewritten version:
```

### Pattern Composition: RAG with Classification

```
You are a customer support classifier and responder.

Step 1: Classify the query into one of: billing | technical | account | other

Step 2: Based on the classification and the provided context, answer the query.

Context documents:
<context>
{retrieved_docs}
</context>

Query: {user_query}

Respond in this format:
<classification>{category}</classification>
<answer>{your answer here}</answer>
```

---

## Cost Optimization Checklist

Prompt engineering has a direct cost impact. These practices reduce token usage:

### Token Reduction Strategies

- [ ] **Concise system prompts:** Remove redundant language, duplicate instructions, unnecessary caveats
- [ ] **Trim few-shot examples:** Use the minimum examples needed; 3 is often as good as 8
- [ ] **Summarize history:** For multi-turn conversations, compress older turns rather than including verbatim
- [ ] **Fewer RAG chunks:** Retrieve fewer but more precise chunks (reranking helps here)
- [ ] **Structured output reduces output tokens:** JSON extraction instead of prose explanation
- [ ] **Set max_tokens appropriately:** Prevents unnecessary token generation
- [ ] **Use stop sequences:** Stop generation as soon as you have what you need
- [ ] **Provider prompt caching:** Structure prompts with stable content first for automatic caching discounts

### Token Estimation Rules

```
1 token ≈ 0.75 English words ≈ 4 characters
1 short sentence ≈ 15-20 tokens
1 paragraph ≈ 75-100 tokens
1 page ≈ 400 tokens
1 code block (50 lines) ≈ 300-600 tokens
1 JSON object (10 fields) ≈ 50-200 tokens
```

### Cost Reduction by Technique

| Technique | Cost Impact |
|---|---|
| Move from Sonnet to Haiku for simple tasks | 70-80% reduction |
| Prompt caching (Anthropic) | 90% reduction on cached tokens |
| Prompt caching (OpenAI) | 50% reduction on cached tokens |
| Semantic caching of responses | 100% reduction on cache hits |
| Token reduction (concise prompts) | 20-40% reduction |
| Structured output (avoids verbose responses) | 30-60% output token reduction |
| Model routing (80/20 split) | 70-80% overall reduction |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Classification Chain for Ambiguous Inputs** -- Uses the "Standard Prompt Templates" -> "Classification: Single Label" template as the basis for Step 1. The ambiguity handling in Step 2 mirrors the "Chain-of-Thought Template" pattern. The two-step chain demonstrates the "Chaining vs. Monolithic Prompts" tradeoff -- more debuggable, more reliable per step.

- **Exercise 2: Few-Shot Example Selection** -- The `classify_with_dynamic_few_shot()` function builds a "Classification Pipeline" (from "Common Prompt Patterns") with dynamically selected few-shot examples. The prompt structure follows the pattern shown in this file: system instructions with categories, selected examples in input/output format, then the actual input.

- **Exercise 3: Reliable JSON Output for Complex Schema** -- Extends the "Entity Extraction" template pattern to a nested, multi-field schema. Practices using delimiters (from "Delimiter Quick Reference") to wrap input documents.

- **Exercise 4: Optimize a Poorly-Performing Prompt** -- Applies the "Cost Optimization Checklist" -> structured output to reduce tokens, stop sequences, and max_tokens settings. The exercise requires using techniques from "Standard Prompt Templates" to write a well-structured extraction prompt.

- **Exercise 5: Self-Consistency with Majority Voting** -- Implements the "Self-Consistency Wrapper" code pattern shown in this file. Requires understanding the CoT template, answer extraction, and majority voting. The "Stop Sequences Reference" is relevant for clean answer extraction.

See also `examples.py` sections 1 (Classification), 4 (Summarization with configurable detail), 5 (Prompt Template System), and 6 (Self-Consistency) for runnable reference implementations of these patterns.

---

## Interview Q&A: Patterns and Techniques

**Q: Explain chain-of-thought prompting and when it helps.**

CoT asks the model to show its reasoning step by step before giving a final answer. The effect is dramatic on tasks requiring multi-step reasoning: math, logic, code analysis, complex decision-making. It works because it forces the model to allocate compute to intermediate reasoning rather than jumping to an answer — each generated token is a computation step. The tradeoffs: CoT uses more output tokens (higher cost and latency), and it does not help on simple tasks like classification or extraction. For production, you often want the reasoning trace for debugging but not for the user, so parse out the final answer and log the reasoning separately.

**Q: What is the difference between temperature and top_p?**

Both control randomness in token selection, but differently. Temperature scales the logits before softmax — at 0 it is deterministic (always picks the highest-probability token), higher values flatten the distribution. Top-p (nucleus sampling) dynamically restricts the candidate pool to the smallest set of tokens whose cumulative probability exceeds p. The practical difference: top-p is adaptive — when the model is confident, the pool shrinks; when uncertain, it widens. Temperature is a blunt uniform scaling. My default: set temperature for the task (0 for deterministic, 0.7 for creative) and leave top_p at 1.0 unless there is a specific reason to constrain it. Setting both aggressively compounds effects unpredictably.

**Q: How do you handle multi-turn conversations and manage context?**

Every conversation turn consumes context window space, so you need an explicit strategy. The three approaches: sliding window (keep only the last N turns), summarization (compress older history into a summary), and hybrid (recent turns verbatim plus a running summary). For most applications, hybrid works best: keep the last 5-10 turns verbatim for conversational coherence, maintain a running summary of older context updated every N turns. The system prompt always stays — it is the behavioral anchor and must never get truncated. Monitor context usage in production and alert before you silently truncate.

**Q: What is prompt chaining and when should you use it over a monolithic prompt?**

Prompt chaining breaks a complex task into a pipeline of focused LLM calls, each with a specific responsibility. Use it when the task has multiple distinct sub-tasks requiring different prompts, when you need to verify intermediate outputs before proceeding, or when a single prompt reliably fails at the task's complexity. The main benefits over a monolithic prompt: each step is inspectable for debugging, failures are localized to a specific step, and smaller focused prompts are more reliable. The cost: multiple API round trips increase latency. For truly complex tasks — document analysis, multi-hop reasoning, agent-like behavior — chaining usually wins on reliability. For simple tasks, keep it as a single call.
