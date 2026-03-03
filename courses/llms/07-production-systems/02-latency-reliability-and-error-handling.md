# 02 — Latency, Reliability, and Error Handling

## Structured Output Reliability

Getting reliable structured output in production requires more than just asking the model nicely.

### The Reliability Spectrum

```
Most reliable
     ▼
Provider-enforced schemas (json_schema mode, tool use)
     → Model constrained at decode time to only produce valid JSON
     → Zero valid-JSON failures

Constrained decoding (Outlines, SGLang for open-source)
     → Grammar enforced during generation
     → Zero schema failures for local models

Prompt + validation + retry
     → Ask for JSON, validate with Pydantic, retry with error message
     → 95-99% success rate with 1-2 retries

Prompt only
     → Hope the model follows instructions
     → 80-95% success rate depending on task
Least reliable
```

### Provider-Enforced JSON

**OpenAI (json_schema):**
```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class ClassificationOutput(BaseModel):
    category: str
    confidence: float
    reasoning: str

response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[{"role": "user", "content": f"Classify: {text}"}],
    response_format=ClassificationOutput,
)
result = response.choices[0].message.parsed
```

**Anthropic (tool use for structured output):**
```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    tools=[{
        "name": "return_classification",
        "description": "Return the classification result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "reasoning": {"type": "string"}
            },
            "required": ["category", "confidence", "reasoning"]
        }
    }],
    tool_choice={"type": "tool", "name": "return_classification"},
    messages=[{"role": "user", "content": f"Classify: {text}"}]
)
result = response.content[0].input
```

### Retry with Error Feedback

```python
import json
from pydantic import BaseModel, ValidationError

def robust_structured_call(
    prompt: str,
    output_schema: type[BaseModel],
    max_retries: int = 3
) -> dict:
    """Get structured output with automatic retry on validation failures."""

    error_context = ""

    for attempt in range(max_retries):
        full_prompt = prompt + error_context
        response = llm_call(full_prompt, temperature=0)

        # Try strict JSON parsing
        try:
            raw = json.loads(response)
        except json.JSONDecodeError as e:
            # Try lenient parsing: extract JSON from response
            extracted = extract_json_from_text(response)
            if extracted:
                raw = extracted
            else:
                error_context = (
                    f"\n\nYour previous response was not valid JSON.\n"
                    f"Error: {e}\n"
                    f"Response: {response[:200]}\n\n"
                    "Please respond with ONLY valid JSON, nothing else."
                )
                continue

        # Try schema validation
        try:
            validated = output_schema.model_validate(raw)
            return validated.model_dump()
        except ValidationError as e:
            error_context = (
                f"\n\nYour previous response failed schema validation.\n"
                f"Error: {e}\n"
                f"Please fix these issues and try again."
            )

    raise ValueError(f"Failed to get valid structured output after {max_retries} retries")

def extract_json_from_text(text: str) -> dict | None:
    """Extract JSON from a response that has extra text around it."""
    import re
    # Try to find JSON object or array in the response
    patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # JSON object
        r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',  # JSON array
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None
```

---

## Latency Optimization

### Optimization Hierarchy

| Optimization | Effort | Impact | When to Apply |
|---|---|---|---|
| Enable streaming | Hours | Transforms perceived latency | Always for user-facing |
| Use smaller model for task | Hours | 2–5× faster | After validating quality |
| Provider prompt caching | Hours | 30–60% faster on repeated prefixes | Large stable prefixes |
| Response caching | Hours | 100% faster on cache hits | Deterministic queries |
| Parallelize retrieval steps | Days | 30–50% RAG latency reduction | RAG systems |
| Reduce prompt length | Days | 20–40% improvement | Verbose prompts |
| Parallel tool calls | Days | Proportional to tool count | Agent systems |
| Semantic caching | Days | High on similar queries | High-volume systems |
| Self-hosted inference | Weeks | 50–200ms TTFT | High-volume, latency-critical |
| Speculative decoding | Weeks | 2–4× throughput | Self-hosted, long outputs |

### Parallelizing RAG Steps

```python
import asyncio

async def optimized_rag_pipeline(query: str) -> dict:
    """Run retrieval steps concurrently to minimize latency."""

    # These can run in parallel: embedding + BM25 index preparation
    query_embedding, bm25_results = await asyncio.gather(
        embed_async(query),
        bm25_search_async(query, k=20)
    )

    # Vector search (depends on embedding)
    vector_results = await vector_store.search_async(query_embedding, k=20)

    # Merge results (fast, synchronous)
    merged = reciprocal_rank_fusion([vector_results, bm25_results])

    # Reranking (depends on merged results)
    reranked = await reranker.score_async(query, merged[:20])
    top_k = sorted(reranked, key=lambda x: x.score, reverse=True)[:5]

    # LLM generation (depends on retrieval)
    response = await llm_async(query, top_k)

    return {"response": response, "sources": top_k}
```

**Latency budget for the above:**
```
Parallel:    embed + BM25     = 30ms (longest of two)
Sequential:  vector search    = 15ms
Sequential:  RRF merge        = 1ms
Sequential:  reranking        = 120ms
Sequential:  LLM generation   = 1,200ms (TTFT: 280ms)
─────────────────────────────────────────────────────
Total pipeline time:  ~1,370ms
Without parallelism: ~1,430ms (marginal gain in this case)
Note: parallelism helps more when individual steps are slower
```

### Reducing Prompt Length

```python
def audit_prompt_tokens(system_prompt: str) -> dict:
    """Identify token waste in system prompts."""

    analysis = {
        "total_tokens": count_tokens(system_prompt),
        "recommendations": []
    }

    # Check for redundancy
    sentences = system_prompt.split('. ')
    for i, s1 in enumerate(sentences):
        for s2 in sentences[i+1:]:
            if embedding_similarity(s1, s2) > 0.9:
                analysis["recommendations"].append(
                    f"Potential redundancy: '{s1}' and '{s2}'"
                )

    # Check for verbose phrases
    verbose_patterns = {
        r'Please make sure to always': 'always',
        r'It is very important that you': '',
        r'You should definitely': '',
        r'I want you to': '',
    }
    for pattern, replacement in verbose_patterns.items():
        if re.search(pattern, system_prompt, re.IGNORECASE):
            analysis["recommendations"].append(
                f"Replace '{pattern}' with '{replacement}'"
            )

    return analysis
```

### Speculative Execution (Advanced)

Pre-fetch likely tool results before the model has decided to call them:

```python
async def speculative_agent_turn(
    conversation: list[dict],
    tools: list[dict],
    likely_queries: list[str]  # Based on conversation pattern
) -> dict:
    """
    Start speculative tool executions while the LLM is processing.
    """

    # Start LLM call and pre-fetch concurrently
    llm_task = asyncio.create_task(
        llm_call_with_tools(conversation, tools)
    )

    # Speculatively execute likely tool calls
    speculative_results = {}
    for query in likely_queries:
        speculative_results[query] = asyncio.create_task(
            search_knowledge_base(query)
        )

    # Get the actual LLM decision
    response = await llm_task

    if response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call.function.name == "search" and \
               tool_call.function.arguments in speculative_results:
                # Use the pre-fetched result (speculative hit)
                result = await speculative_results[tool_call.function.arguments]
            else:
                # Speculative miss - execute normally
                result = await execute_tool(tool_call)

    return response
```

---

## Error Handling and Reliability

### Error Classification

| Error | HTTP Code | Retry? | Strategy |
|---|---|---|---|
| Rate limited | 429 | Yes | Exponential backoff with jitter, respect Retry-After |
| Server error | 500 | Yes | Retry up to 3× with backoff |
| Bad gateway | 502 | Yes | Retry up to 3×, consider failover |
| Service unavailable | 503 | Yes | Retry with longer backoff, activate circuit breaker |
| Timeout | N/A | Yes | Retry once with increased timeout |
| Bad request | 400 | No | Fix the request (prompt too long, invalid params) |
| Auth failure | 401 | No | Check API key, do not retry |
| Model not found | 404 | No | Check model name, do not retry |
| Content filtered | 400 | Maybe | Rephrase if appropriate |
| Context overflow | 400 | No | Truncate input, reduce context |
| Invalid JSON output | N/A | Yes | Retry with error feedback, lenient parsing |

### Circuit Breaker Pattern

```python
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Provider is failing, reject requests
    HALF_OPEN = "half_open" # Testing if provider has recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 30.0,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.half_open_calls = 0

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            print(f"Circuit breaker OPENED after {self.failure_count} failures")

# Circuit breaker configuration
DEFAULT_CONFIG = {
    "failure_threshold": 5,      # Open after 5 consecutive failures
    "reset_timeout": 30,         # Try again after 30 seconds
    "half_open_max": 1,          # Single test request in half-open state
    "monitor_window": 60,        # Count failures in a 60-second window
}
```

### Fallback Model Chain

```python
class FallbackChain:
    def __init__(self, providers: list[dict]):
        """
        providers: list of {"model": str, "client": LLMClient, "breaker": CircuitBreaker}
        ordered by preference (primary first)
        """
        self.providers = providers

    async def call(self, messages: list[dict], **kwargs) -> dict:
        last_error = None

        for provider in self.providers:
            if not provider["breaker"].can_attempt():
                continue  # Circuit is open, skip this provider

            try:
                response = await provider["client"].create(
                    model=provider["model"],
                    messages=messages,
                    **kwargs
                )
                provider["breaker"].record_success()
                return response

            except (RateLimitError, ServiceUnavailableError) as e:
                provider["breaker"].record_failure()
                last_error = e
                log_fallback(provider["model"], str(e))
                continue

            except AuthError:
                # Don't fallback for auth errors — fix the key
                raise

        raise Exception(f"All providers failed. Last error: {last_error}")

# Example configuration:
fallback_chain = FallbackChain([
    {
        "model": "claude-opus-4-5",      # Primary
        "client": anthropic_client,
        "breaker": CircuitBreaker(failure_threshold=5)
    },
    {
        "model": "gpt-4o",               # Secondary
        "client": openai_client,
        "breaker": CircuitBreaker(failure_threshold=5)
    },
    {
        "model": "llama-3.1-70b",        # Emergency fallback (self-hosted)
        "client": local_client,
        "breaker": CircuitBreaker(failure_threshold=10)
    }
])
```

### Graceful Degradation

```python
async def get_response_with_degradation(
    query: str,
    conversation_history: list[dict]
) -> dict:
    """
    Attempt full quality response; degrade gracefully if not possible.
    """

    # Level 1: Full response with RAG
    try:
        context = await retrieve_context(query)
        response = await llm_call(query, context, conversation_history)
        return {"response": response, "quality": "full"}
    except Exception as e:
        log_error("full_response_failed", e)

    # Level 2: Response without RAG (no retrieval)
    try:
        response = await llm_call(query, context=[], history=conversation_history)
        return {"response": response, "quality": "reduced", "note": "Without context"}
    except Exception as e:
        log_error("reduced_response_failed", e)

    # Level 3: Cached response for similar query
    cached = await find_cached_similar(query)
    if cached:
        return {"response": cached, "quality": "cached", "note": "Cached response"}

    # Level 4: Static fallback
    return {
        "response": "I'm temporarily unable to process your request. Please try again in a moment.",
        "quality": "fallback"
    }
```

---

## Latency Optimization Checklist

### Quick Wins (Hours to Implement)

- [ ] Enable streaming for all user-facing responses
- [ ] Enable provider prompt caching (structure prompts with static prefix)
- [ ] Add exact-match response caching for repeated queries
- [ ] Set appropriate `max_tokens` to prevent unnecessarily long responses
- [ ] Use smaller models for simple tasks (classification, extraction, routing)

### Medium Effort (Days to Implement)

- [ ] Reduce prompt length (audit system prompts, trim few-shot examples)
- [ ] Implement parallel tool execution for agents
- [ ] Add semantic caching for similar queries
- [ ] Implement model routing (small/medium/large by task complexity)
- [ ] Pre-compute and cache embeddings for static content
- [ ] Use async/concurrent API calls for independent operations

### High Effort (Weeks to Implement)

- [ ] Self-host models for latency-sensitive, high-volume features
- [ ] Implement speculative execution (pre-fetch likely tool results)
- [ ] Edge deployment for offline/ultra-low-latency use cases
- [ ] Build a cascade architecture (try small model first, escalate)
- [ ] Implement custom batching for throughput-critical pipelines

---

## Interview Q&A: Latency, Reliability, and Error Handling

**Q: How do you approach latency optimization for LLM applications?**

Streaming is the first and highest-impact change — perceived latency drops from seconds to hundreds of milliseconds with no architecture change. After that, model routing: use smaller, faster models for simple tasks, reserve large models for complex ones. For RAG systems, parallelize retrieval (embedding, vector search, BM25 can overlap). Cache aggressively — identical queries at temperature 0 should never hit the model twice. Reduce prompt length: concise system prompts, summarized history, fewer but more relevant retrieved chunks. For agent systems, enable parallel tool calls when supported. Speculative execution is high-complexity but effective for specific architectures. Common mistake: optimizing the LLM call when the bottleneck is actually upstream — query processing, retrieval, or prompt assembly. Profile first.

**Q: How do you handle reliability and failover for LLM APIs?**

LLM APIs are external dependencies that will go down. Treat them accordingly. Retry with exponential backoff on transient errors (429, 500, 503), respect Retry-After headers. Implement timeouts — don't let a hung API call block indefinitely. Circuit breakers: if a provider fails N times in a window, stop trying and fail fast or switch to a fallback. For high-availability systems, implement provider fallback chains: primary Claude Sonnet, fallback GPT-4o, emergency self-hosted model. Each fallback may produce slightly different quality, which is acceptable during an outage. Request queuing smooths load spikes. Graceful degradation: return cached responses, simplified responses, or a clear "try again later" message rather than failing entirely.

**Q: What is the circuit breaker pattern and when do you use it?**

The circuit breaker pattern has three states. CLOSED (normal): requests pass through normally; failures are counted. OPEN: after hitting a failure threshold (e.g., 5 consecutive failures), the circuit opens — all requests are rejected immediately without hitting the failing service. This prevents thundering herd when a service is down. HALF_OPEN: after a reset timeout (e.g., 30 seconds), one test request is allowed through; if it succeeds, the circuit closes; if it fails, it returns to OPEN. For LLM services: use per-provider circuit breakers so a single provider's outage triggers failover to secondary providers rather than cascading failures. Track failures in a time window (not just consecutive) so brief partial outages don't require manual intervention.
