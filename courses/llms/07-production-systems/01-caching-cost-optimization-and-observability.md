# 01 — Caching, Cost Optimization, and Observability

## Streaming

Streaming is the single highest-impact production optimization for user-facing LLM applications.

### Why Streaming Matters

Without streaming, the user sees nothing until the entire response is generated — potentially 5–30 seconds of staring at a blank screen. With streaming, the first tokens appear in 100–500ms.

| Delivery Mode | Time to First Visible Output | User Experience |
|---|---|---|
| No streaming | Full generation time (2–30s) | Users abandon if > 3s |
| Streaming | Time to first token (100–500ms) | Feels fast and responsive |
| Streaming + skeleton | Instant (skeleton shown, then text fills in) | Best perceived performance |

### SSE Implementation

Server-Sent Events (SSE) is the standard protocol for streaming LLM responses to browsers.

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

async def stream_llm_response(prompt: str):
    """Generator that yields SSE-formatted tokens."""
    async for chunk in llm_stream_call(prompt):
        if chunk.delta.text:
            # SSE format: "data: {content}\n\n"
            yield f"data: {json.dumps({'token': chunk.delta.text})}\n\n"

    # Signal end of stream
    yield "data: [DONE]\n\n"

@app.post("/chat/stream")
async def stream_endpoint(request: ChatRequest):
    return StreamingResponse(
        stream_llm_response(request.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

### Streaming with Structured Output

Structured output cannot be parsed mid-stream. Buffer the full response before parsing:

```python
async def stream_with_schema_validation(
    prompt: str,
    schema: type,
) -> AsyncIterator[str]:
    """Stream tokens to user, validate schema after completion."""
    buffer = []

    async for chunk in llm_stream_call(prompt):
        token = chunk.delta.text or ""
        buffer.append(token)
        yield token  # Stream each token to user

    # After stream completes, validate the full response
    full_response = "".join(buffer)
    try:
        schema.model_validate_json(full_response)
    except ValidationError as e:
        # Schema invalid — retry logic here
        yield f"\n\n[ERROR: Response failed validation: {e}]"
```

### Tool Calls in Streams

Tool call arguments arrive incrementally:

```python
async def handle_streaming_tool_calls(stream):
    """Reconstruct tool calls from streaming chunks."""
    pending_tool_calls = {}

    async for chunk in stream:
        if chunk.choices[0].delta.tool_calls:
            for tc_delta in chunk.choices[0].delta.tool_calls:
                idx = tc_delta.index
                if idx not in pending_tool_calls:
                    pending_tool_calls[idx] = {
                        "id": tc_delta.id,
                        "function": {"name": "", "arguments": ""}
                    }
                if tc_delta.function.name:
                    pending_tool_calls[idx]["function"]["name"] += tc_delta.function.name
                if tc_delta.function.arguments:
                    pending_tool_calls[idx]["function"]["arguments"] += tc_delta.function.arguments

    # Execute completed tool calls
    return [
        {"id": tc["id"], "function": tc["function"]}
        for tc in pending_tool_calls.values()
    ]
```

---

## Caching Strategies

### Response Caching (Exact Match)

Cache identical prompts at temperature=0 — the output is deterministic, so you can safely reuse it.

```python
import hashlib
import json

class ResponseCache:
    def __init__(self, redis_client, default_ttl: int = 3600):
        self.redis = redis_client
        self.default_ttl = default_ttl

    def _cache_key(self, messages: list[dict], model: str, params: dict) -> str:
        """Create a deterministic cache key."""
        content = json.dumps({
            "messages": messages,
            "model": model,
            "temperature": params.get("temperature", 1.0),
            "max_tokens": params.get("max_tokens"),
        }, sort_keys=True)
        return f"llm_cache:{hashlib.sha256(content.encode()).hexdigest()}"

    def get(self, messages: list[dict], model: str, params: dict) -> str | None:
        if params.get("temperature", 1.0) > 0:
            return None  # Only cache deterministic responses
        key = self._cache_key(messages, model, params)
        return self.redis.get(key)

    def set(
        self,
        messages: list[dict],
        model: str,
        params: dict,
        response: str,
        ttl: int | None = None
    ):
        if params.get("temperature", 1.0) > 0:
            return
        key = self._cache_key(messages, model, params)
        self.redis.setex(key, ttl or self.default_ttl, response)
```

### Semantic Caching

For similar (but not identical) queries, use embedding similarity to find cached responses:

```python
class SemanticCache:
    def __init__(self, vector_store, embed_fn, similarity_threshold: float = 0.95):
        self.vector_store = vector_store
        self.embed = embed_fn
        self.threshold = similarity_threshold

    def get(self, query: str) -> str | None:
        query_embedding = self.embed(query)
        results = self.vector_store.similarity_search_with_score(
            query_embedding, k=1
        )
        if results and results[0][1] >= self.threshold:
            return results[0][0]["cached_response"]
        return None

    def set(self, query: str, response: str, ttl_hours: int = 24):
        self.vector_store.upsert({
            "vector": self.embed(query),
            "query": query,
            "cached_response": response,
            "expires_at": time.time() + ttl_hours * 3600
        })
```

### Caching Decision Tree

```
Is the query deterministic (temperature=0)?
├── Yes → Is the exact same query likely to repeat?
│         ├── Yes → EXACT MATCH CACHE (hash-based, highest hit rate)
│         └── No  → Are similar queries likely?
│                   ├── Yes → SEMANTIC CACHE (embedding similarity)
│                   └── No  → Are prompts sharing a long prefix?
│                             ├── Yes → PROMPT CACHE (provider-side)
│                             └── No  → No caching benefit
└── No  → Is the query classification/extraction (structured output)?
          ├── Yes → EXACT MATCH CACHE (output is deterministic in practice)
          └── No  → Is freshness acceptable with TTL?
                    ├── Yes → EXACT MATCH CACHE with short TTL
                    └── No  → No response caching (consider prompt caching only)
```

### Cache Type Comparison

| Cache Type | Hit Rate | Latency Added (miss) | Cost Savings | Implementation |
|---|---|---|---|---|
| Exact match | Low-Medium | ~1ms (hash lookup) | High per hit | Redis/in-memory |
| Semantic | Medium | 10–50ms (embedding + search) | High per hit | Vector store |
| Prompt (provider) | High | 0ms (automatic) | 50–90% input cost | Configuration |

---

## Cost Optimization

### Model Routing

Route requests to the cheapest model that meets the quality bar for each task:

```python
class ModelRouter:
    def __init__(self, models: dict[str, ModelConfig]):
        self.models = models

    def route(
        self,
        task_type: str,
        complexity: str,
        quality_required: str
    ) -> str:
        """Return the model ID to use for this request."""

        routing_table = {
            ("classification", "simple", "standard"):     "claude-haiku-3-5",
            ("classification", "complex", "standard"):    "gpt-4o-mini",
            ("extraction", "simple", "standard"):         "claude-haiku-3-5",
            ("extraction", "complex", "high"):            "gpt-4o",
            ("generation", "simple", "standard"):         "gpt-4o-mini",
            ("generation", "complex", "high"):            "claude-opus-4-5",
            ("reasoning", "complex", "highest"):          "claude-opus-4-5",
            ("coding", "complex", "high"):                "gpt-4o",
        }

        key = (task_type, complexity, quality_required)
        return routing_table.get(key, "claude-sonnet-4-5")  # Default

class ComplexityClassifier:
    """Classify request complexity to drive routing decisions."""

    def classify(self, user_message: str) -> str:
        # Fast heuristics first
        token_count = count_tokens(user_message)

        if token_count < 50 and not self._has_complex_syntax(user_message):
            return "simple"
        elif token_count > 500 or self._has_multi_step_reasoning(user_message):
            return "complex"
        else:
            return "medium"
```

### Worked Cost Example

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

Routing 80% to mini, 20% to Sonnet:
  0.80 × $5.40 + 0.20 × $120 = $4.32 + $24.00 = $28.32/day = $850/month
  (vs $3,600/month all-Sonnet → 76% savings)
```

### Token Reduction Strategies

```python
def optimize_tokens(
    messages: list[dict],
    retrieved_chunks: list[str],
    max_chunks: int = 5,
    max_history_turns: int = 5
) -> list[dict]:
    """Reduce token usage without sacrificing quality."""

    # 1. Limit RAG chunks (retrieve fewer but more relevant with reranking)
    relevant_chunks = retrieved_chunks[:max_chunks]

    # 2. Summarize old conversation turns
    recent_messages = messages[-max_history_turns * 2:]  # Last N turns

    # 3. Concise system prompt (audit and remove redundant instructions)
    # 4. Set appropriate max_tokens
    # 5. Use stop sequences to prevent over-generation

    return build_optimized_messages(
        system_prompt=CONCISE_SYSTEM_PROMPT,
        context=relevant_chunks,
        history=recent_messages
    )
```

### Batch Processing

For non-time-sensitive workloads, batch APIs offer significant discounts:

```python
# OpenAI Batch API (50% discount)
from openai import OpenAI

client = OpenAI()

# Create batch file
requests = [
    {
        "custom_id": f"request-{i}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 500
        }
    }
    for i, text in enumerate(texts_to_process)
]

with open("batch_requests.jsonl", "w") as f:
    for req in requests:
        f.write(json.dumps(req) + "\n")

# Submit batch
batch_file = client.files.create(
    file=open("batch_requests.jsonl", "rb"),
    purpose="batch"
)
batch = client.batches.create(
    input_file_id=batch_file.id,
    endpoint="/v1/chat/completions",
    completion_window="24h"
)
```

---

## Observability

### What to Log for Every Request

```python
@dataclass
class LLMCallLog:
    # Identity
    request_id: str
    session_id: str
    user_id: str          # Pseudonymized
    feature: str          # Which product feature
    timestamp: str

    # Model
    model: str
    provider: str
    model_version: str | None

    # Performance
    ttft_ms: float        # Time to first token
    total_latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Cost
    cost_usd: float

    # Quality
    status: str           # "success", "error", "timeout", "blocked"
    error_type: str | None
    error_message: str | None
    cache_hit: bool

    # Content (hashed for privacy)
    prompt_hash: str
    response_hash: str

    # Tools (for agent systems)
    tool_calls: list[dict] | None  # [{"name": "search", "latency_ms": 45}]
```

### Dashboard Metrics

| Metric | Aggregation | Alert Threshold |
|---|---|---|
| Error rate | 5-min rolling | > 5% |
| P95 latency | 5-min rolling | > 10s |
| TTFT P95 | 5-min rolling | > 2s |
| Cost per hour | Hourly sum | > 2× trailing avg |
| Requests per minute | 1-min count | > 80% of rate limit |
| Cache hit rate | Hourly ratio | < 20% (if caching enabled) |
| Token per request (avg) | Hourly avg | > 2× baseline |

### Distributed Tracing

For multi-step pipelines (RAG, agents), trace the full execution:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

tracer = trace.get_tracer("llm-service")

async def traced_rag_pipeline(query: str) -> str:
    with tracer.start_as_current_span("rag_request") as span:
        span.set_attribute("query", query[:100])

        with tracer.start_as_current_span("embedding"):
            start = time.time()
            query_embedding = embed(query)
            span.set_attribute("embedding_ms", (time.time() - start) * 1000)

        with tracer.start_as_current_span("vector_search") as search_span:
            start = time.time()
            results = vector_store.search(query_embedding, k=5)
            search_span.set_attribute("num_results", len(results))
            search_span.set_attribute("latency_ms", (time.time() - start) * 1000)

        with tracer.start_as_current_span("llm_call") as llm_span:
            start = time.time()
            response = llm_call(query, results)
            llm_span.set_attribute("model", response.model)
            llm_span.set_attribute("input_tokens", response.usage.prompt_tokens)
            llm_span.set_attribute("output_tokens", response.usage.completion_tokens)
            llm_span.set_attribute("cost_usd", calculate_cost(response))
            llm_span.set_attribute("latency_ms", (time.time() - start) * 1000)

        return response.content
```

### Tracing Structure

```
Trace: rag_request
├── Span: embedding (50ms)
├── Span: vector_search (15ms)
│   └── Attribute: num_results=5
├── Span: reranking (120ms)
└── Span: llm_call (1,200ms)
    ├── Attribute: model="claude-sonnet-4-5"
    ├── Attribute: input_tokens=3,200
    ├── Attribute: output_tokens=400
    ├── Attribute: ttft_ms=280
    └── Attribute: cost_usd=0.0158
```

### Observability Tools

| Tool | Type | Strengths | Pricing |
|---|---|---|---|
| LangSmith | Managed | LLM-specific, strong logging | Free tier + paid |
| Helicone | Managed | Simple proxy, cost tracking | Free tier + paid |
| Braintrust | Managed | Eval + observability combined | Free tier + paid |
| OpenTelemetry | Standard | Vendor-neutral, integrates with any backend | Free (DIY) |
| Datadog / Grafana | General APM | Existing infrastructure integration | Variable |

---

## Rate Limiting

### Client-Side Rate Limiting

Protect your application from rate limit errors:

```python
from token_bucket import TokenBucket
import time

class RateLimitedLLMClient:
    def __init__(self, requests_per_minute: int, tokens_per_minute: int):
        # Token bucket for request rate limiting
        self.request_bucket = TokenBucket(
            capacity=requests_per_minute,
            refill_rate=requests_per_minute / 60  # tokens per second
        )
        self.tpm_limit = tokens_per_minute
        self.token_usage_window = []  # Sliding window

    def can_make_request(self, estimated_tokens: int) -> bool:
        # Check RPM
        if not self.request_bucket.consume(1):
            return False

        # Check TPM (sliding window)
        now = time.time()
        self.token_usage_window = [
            (ts, tokens) for ts, tokens in self.token_usage_window
            if now - ts < 60  # Keep last 60 seconds
        ]
        recent_tokens = sum(t for _, t in self.token_usage_window)
        return recent_tokens + estimated_tokens <= self.tpm_limit
```

### Exponential Backoff with Jitter

```python
import asyncio
import random

async def llm_call_with_retry(
    client,
    params: dict,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> dict:
    """Retry with exponential backoff and jitter on transient errors."""

    for attempt in range(max_retries):
        try:
            return await client.create(**params)

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            # Respect Retry-After header if present
            retry_after = getattr(e, "retry_after", None)
            if retry_after:
                delay = float(retry_after)
            else:
                # Exponential backoff with full jitter
                delay = min(
                    base_delay * (2 ** attempt) + random.uniform(0, 1),
                    max_delay
                )

            print(f"Rate limited. Waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(delay)

        except (ServerError, BadGatewayError):
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            await asyncio.sleep(delay)

        except AuthError:
            raise  # Don't retry authentication failures
```

### Provider Rate Limits Reference (Early 2026)

**OpenAI:**

| Tier | Requirement | RPM | TPM (most models) |
|---|---|---|---|
| Free | Default | 3 | 40,000 |
| Tier 1 | $5 paid | 500 | 30,000 |
| Tier 2 | $50 paid, 7+ days | 5,000 | 450,000 |
| Tier 3 | $100 paid, 7+ days | 5,000 | 600,000 |
| Tier 4 | $250 paid, 14+ days | 10,000 | 800,000 |
| Tier 5 | $1,000 paid, 30+ days | 10,000 | 10,000,000 |

**Anthropic:**

| Tier | Requirement | RPM | Input TPM | Output TPM |
|---|---|---|---|---|
| Build Tier 1 | $0 credit | 50 | 40,000 | 8,000 |
| Build Tier 2 | $40 credit | 1,000 | 80,000 | 16,000 |
| Build Tier 3 | $200 credit | 2,000 | 160,000 | 32,000 |
| Build Tier 4 | $400 credit | 4,000 | 400,000 | 80,000 |
| Scale | Custom | Custom | Custom | Custom |

---

## Key Numbers

| Metric | Value |
|---|---|
| Token generation speed (API) | 30–100 tokens/sec |
| TTFT target (interactive) | < 500ms |
| Cache hit rate (FAQ bots) | 30–60% |
| Cache hit rate (unique convos) | < 5% |
| Provider uptime SLA | 99.9% (typical) |
| Prompt cache min length (Anthropic) | 1,024 tokens (Sonnet) |
| Prompt cache savings (Anthropic) | 90% input cost reduction |
| Prompt cache savings (OpenAI) | 50% input cost reduction |
| Model routing cost savings | 50–80% with 70–80% small model routing |
| Batch API discount (OpenAI) | 50% |

---

## Interview Q&A: Caching, Cost, Observability

**Q: How do you optimize LLM costs in production?**

Model tiering is the highest-leverage optimization. Most systems have simple tasks (classification, extraction) and complex ones (reasoning, generation). Use the cheapest model that meets your quality bar for each task — Haiku-class for classification, Sonnet-class for generation, Opus-class only for the hardest reasoning. This can reduce costs 5–20× without quality degradation if you have good evals. Beyond model selection: caching (identical prompts at temperature 0 should hit a cache), token optimization (concise system prompts, summarized conversation history), prompt caching (providers automatically cache repeated prompt prefixes at 50–90% discounts), and output limits (set max_tokens appropriately). Track cost at per-request, per-feature, and per-user granularities. Alert on cost anomalies. Do the math before building: estimate tokens × price × volume to validate architectural feasibility.

**Q: Describe your approach to LLM observability.**

Log everything, alert on degradation, trace end-to-end. For every LLM call: request ID, timestamp, model, provider, feature, user ID (pseudonymized), input/output token counts, cost, TTFT, total latency, status, error info, and cache hit/miss. This is the debugging foundation — when something goes wrong, you need to reproduce exactly what happened. For metrics: track error rate, latency percentiles (p50, p95, p99) for both TTFT and total, cost per request and aggregate, and quality scores from automated evals on production samples. For agent and RAG systems, trace the full execution path with spans for each step. Tools: LangSmith or Helicone for LLM-specific observability; OpenTelemetry for vendor-neutral integration with existing APM. Alert on: error rate spikes, latency degradation, cost anomalies, and quality score drops.

**Q: How do you handle streaming responses?**

Streaming uses Server-Sent Events (SSE) to push tokens to the client as they are generated. This reduces perceived latency from seconds to hundreds of milliseconds. Implementation: make a streaming API call, iterate over the event stream, forward each token chunk via SSE or WebSocket. Complications: structured output (buffer the full response before parsing — can't parse mid-stream JSON), tool calls (arguments arrive incrementally and must be buffered and reconstructed), error handling (the stream can fail mid-response, so handle partial results gracefully), and backpressure (if the client is slower than the model, buffer appropriately). Use streaming for all user-facing chat interfaces. For server-to-server pipelines, streaming still helps when downstream services can start processing incrementally.
