"""
LLM Fundamentals -- Exercises
================================
Skeleton functions to implement. Each exercise reinforces a core LLM concept.
Run this file to execute the test functions at the bottom.

Requirements:
    pip install tiktoken

Note: These exercises test LLM engineering knowledge, not Python knowledge.
The implementations should reflect understanding of how LLMs work.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import tiktoken


# ============================================================================
# EXERCISE 1: Multi-Model Cost Estimator
# ============================================================================
# READ FIRST:
#   - 01-transformer-architecture-fundamentals.md -> "Tokenization" section
#     (understand what tokens are, BPE, ~0.75 words per token)
#   - 01-transformer-architecture-fundamentals.md -> "Context Windows and Memory"
#     (context window = input + output tokens combined)
#   - 02-training-and-model-families.md -> "Cost Estimation" section
#     (per-request formula, worked example with real pricing)
#   - 02-training-and-model-families.md -> "Model Families" -> pricing table
#   - 03-advanced-llm-concepts.md -> "Prefix Caching (Provider-Side)" section
#     (how caching works, Anthropic 90% vs OpenAI 50% discount)
#
# ALSO SEE:
#   - examples.py -> Section 1 "TOKEN COUNTING AND COST ESTIMATION"
#     (ModelPricing dataclass, count_tokens(), estimate_cost(),
#      compare_model_costs() -- follow the same pattern)
#   - examples.py -> Section 7 "TOKEN BUDGET PLANNER"
#     (TokenBudget dataclass for context window allocation)
#
# Build a cost estimator that handles different pricing tiers, prompt caching
# discounts, and batch API discounts.
#
# Key concepts:
#   - Token counting and its relationship to cost
#   - Input vs output token pricing asymmetry (output is 3-5x more expensive)
#   - Prompt caching: when the same prefix is reused, providers charge less
#   - Batch API: non-real-time requests at ~50% discount


@dataclass
class ModelConfig:
    """Model pricing and limits configuration."""
    name: str
    input_cost_per_million: float
    output_cost_per_million: float
    context_window: int
    max_output: int
    cached_input_discount: float = 0.5   # 50% discount on cached input tokens
    batch_discount: float = 0.5          # 50% discount for batch API


# Model configs to use in your implementation
MODELS: dict[str, ModelConfig] = {
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        input_cost_per_million=2.50,
        output_cost_per_million=10.00,
        context_window=128_000,
        max_output=16_384,
    ),
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        context_window=128_000,
        max_output=16_384,
    ),
    "claude-sonnet-4": ModelConfig(
        name="claude-sonnet-4",
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        context_window=200_000,
        max_output=16_384,
        cached_input_discount=0.9,  # Anthropic gives 90% discount on cached tokens
    ),
    "gemini-2.0-flash": ModelConfig(
        name="gemini-2.0-flash",
        input_cost_per_million=0.10,
        output_cost_per_million=0.40,
        context_window=1_000_000,
        max_output=8_192,
    ),
}


@dataclass
class CostEstimate:
    """Result of a cost estimation."""
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    input_cost: float
    cached_cost: float
    output_cost: float
    total_cost: float
    is_batch: bool
    fits_in_context: bool


def estimate_request_cost(
    input_text: str,
    estimated_output_tokens: int,
    model_name: str,
    cached_prefix_text: str = "",
    is_batch: bool = False,
) -> CostEstimate:
    """Estimate the cost of an LLM request with optional caching and batch discount.

    TODO: Implement this function.

    Steps:
    1. Count tokens in input_text and cached_prefix_text using tiktoken (cl100k_base)
       - Use: enc = tiktoken.get_encoding("cl100k_base"); len(enc.encode(text))
       - See examples.py count_tokens() for reference
    2. The cached_prefix_text tokens get the cached_input_discount from the model config
       (discount is subtracted, so 0.9 discount means you pay 10% of normal input price)
       - cached_cost = (cached_tokens / 1_000_000) * model.input_cost_per_million * (1 - model.cached_input_discount)
    3. Non-cached input tokens pay the normal input rate
       - non_cached_tokens = total_input_tokens - cached_tokens
       - input_cost = (non_cached_tokens / 1_000_000) * model.input_cost_per_million
    4. Output tokens pay the output rate
       - output_cost = (estimated_output_tokens / 1_000_000) * model.output_cost_per_million
    5. If is_batch, apply batch_discount to the total cost
       - total_cost = (input_cost + cached_cost + output_cost) * (1 - model.batch_discount) if is_batch
    6. Check if total tokens (input + output) fit in the context window
       - fits = (total_input_tokens + estimated_output_tokens) <= model.context_window

    Return a CostEstimate with all fields populated.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement estimate_request_cost")


def find_cheapest_model(
    input_text: str,
    estimated_output_tokens: int,
    cached_prefix_text: str = "",
) -> tuple[str, CostEstimate]:
    """Find the cheapest model that fits the request in its context window.

    TODO: Implement this function.

    Steps:
    1. Estimate cost for each model in MODELS
       - Call estimate_request_cost() for each model_name in MODELS
    2. Filter to only models where the request fits in the context window
       - Check estimate.fits_in_context == True
    3. Return the model name and CostEstimate for the cheapest option
       - Use min() on total_cost, or sort and take first
       - Return: tuple[str, CostEstimate] e.g. ("gemini-2.0-flash", estimate)
    4. Raise ValueError if no model can fit the request
       - raise ValueError("No model can fit the request")
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement find_cheapest_model")


# ============================================================================
# EXERCISE 2: Model Router
# ============================================================================
# READ FIRST:
#   - 02-training-and-model-families.md -> "Model Families" section
#     (understand the model tiers, capabilities, and pricing tradeoffs)
#   - 02-training-and-model-families.md -> "Choosing a Model Family" section
#     (4 axes: capability, cost, latency, deployment constraints)
#   - 02-training-and-model-families.md -> "Key Parameters and Their Business Impact"
#     (parameter presets per task type)
#   - 03-advanced-llm-concepts.md -> "Reasoning Models" -> "Model routing design"
#     (route simple to fast models, complex to reasoning models)
#
# ALSO SEE:
#   - examples.py -> Section 2 "MODEL SELECTION / ROUTING"
#     (TaskComplexity enum, classify_task_complexity(), route_request(),
#      COMPLEXITY_SIGNALS dict -- follow same keyword-matching approach)
#   - examples.py -> Section 4 "PARAMETER TUNING EXAMPLES"
#     (GENERATION_PRESETS, get_config_for_task() -- maps tasks to configs)
#
# Build a model router that analyzes incoming requests and routes them to
# the appropriate model tier based on multiple signals.
#
# Key concepts:
#   - Not all tasks need frontier models -- most production traffic is simple
#   - Routing can cut costs 10x while maintaining quality
#   - Multiple signals: task type, required context, expected output length


class TaskType(Enum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    GENERATION = "generation"
    CODE = "code"
    REASONING = "reasoning"
    CONVERSATION = "conversation"


@dataclass
class RoutingRequest:
    """A request to be routed to a model."""
    prompt: str
    task_type: TaskType | None = None      # If None, infer from prompt
    max_quality: bool = False               # Force best model regardless of cost
    max_speed: bool = False                 # Force fastest model
    budget_per_request: float | None = None # Cost ceiling in USD


@dataclass
class RoutingResult:
    model: str
    task_type: TaskType
    generation_config: dict[str, Any]
    estimated_cost: float
    reasoning: str


# Routing rules: which model tier for which task type
ROUTING_TABLE: dict[TaskType, str] = {
    TaskType.CLASSIFICATION: "gpt-4o-mini",
    TaskType.EXTRACTION: "gpt-4o-mini",
    TaskType.SUMMARIZATION: "gpt-4o-mini",
    TaskType.GENERATION: "gpt-4o",
    TaskType.CODE: "claude-sonnet-4",
    TaskType.REASONING: "claude-sonnet-4",
    TaskType.CONVERSATION: "gpt-4o-mini",
}

# Recommended generation parameters per task type
TASK_CONFIGS: dict[TaskType, dict[str, Any]] = {
    TaskType.CLASSIFICATION: {"temperature": 0, "max_tokens": 50},
    TaskType.EXTRACTION: {"temperature": 0, "max_tokens": 2000},
    TaskType.SUMMARIZATION: {"temperature": 0.3, "max_tokens": 1000},
    TaskType.GENERATION: {"temperature": 0.7, "max_tokens": 4000},
    TaskType.CODE: {"temperature": 0.2, "max_tokens": 4000},
    TaskType.REASONING: {"temperature": 0.1, "max_tokens": 4000},
    TaskType.CONVERSATION: {"temperature": 0.7, "max_tokens": 2000},
}


def infer_task_type(prompt: str) -> TaskType:
    """Infer the task type from the prompt content.

    TODO: Implement this function.

    Analyze the prompt text and return the most likely TaskType.
    Consider keywords, prompt structure, and common patterns:
    - Classification: "classify", "categorize", "label", "sentiment", "is this"
    - Extraction: "extract", "parse", "find the", "what is the", "list all"
    - Summarization: "summarize", "summary", "brief", "tldr", "key points"
    - Code: "code", "function", "implement", "debug", "refactor", "write a program"
    - Reasoning: "why", "explain", "prove", "step by step", "analyze", "compare"
    - Generation: "write", "create", "generate", "draft", "compose"
    - Conversation: default fallback

    Implementation approach (see examples.py classify_task_complexity()):
    1. prompt_lower = prompt.lower()
    2. Check keyword lists in priority order (most specific first):
       - Check CODE keywords first (they're specific)
       - Check CLASSIFICATION keywords
       - Check EXTRACTION keywords
       - Check REASONING keywords
       - Check SUMMARIZATION keywords
       - Check GENERATION keywords
       - Default to CONVERSATION
    3. Use: if any(kw in prompt_lower for kw in keywords): return TaskType.XXX

    Note: In production, you might use a small classifier model for this instead
    of keyword matching. The keyword approach is a reasonable v1.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement infer_task_type")


def route_request(request: RoutingRequest) -> RoutingResult:
    """Route a request to the appropriate model with generation config.

    TODO: Implement this function.

    Steps:
    1. Determine task type (use request.task_type if provided, else infer)
       - task_type = request.task_type if request.task_type else infer_task_type(request.prompt)
    2. Look up the base model from ROUTING_TABLE
       - model = ROUTING_TABLE[task_type]
    3. Apply overrides:
       - If max_quality is True, use "claude-sonnet-4" regardless of task
       - If max_speed is True, use "gpt-4o-mini" regardless of task
       - If budget_per_request is set, estimate cost for the routed model
         (use MODELS dict from Exercise 1 or estimate inline);
         if cost > budget, try cheaper models in order: gpt-4o-mini, gemini-2.0-flash
    4. Get generation config from TASK_CONFIGS
       - config = TASK_CONFIGS[task_type]
    5. Estimate cost (use the model's pricing from MODELS dict above,
       count input tokens with count_tokens(request.prompt),
       assume output tokens = config["max_tokens"] for worst case,
       or a reasonable estimate like 500)
       - pricing = MODELS[model]
       - est_cost = (input_tokens/1e6)*pricing.input_cost_per_million + (output_tokens/1e6)*pricing.output_cost_per_million
    6. Return RoutingResult with reasoning explaining the decision
       - RoutingResult(model=model, task_type=task_type, generation_config=config,
                       estimated_cost=est_cost, reasoning="...")
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement route_request")


# ============================================================================
# EXERCISE 3: Context Window Truncation Strategies
# ============================================================================
# READ FIRST:
#   - 01-transformer-architecture-fundamentals.md -> "Context Windows and Memory"
#     (what the context window is, KV cache, prefill vs decode)
#   - 01-transformer-architecture-fundamentals.md -> "Tokenization"
#     (tokens != characters; 1 token ~ 0.75 words ~ 4 chars)
#   - 01-transformer-architecture-fundamentals.md -> Interview Q&A -> "lost in the middle"
#     (models attend more to beginning and end of context)
#   - 03-advanced-llm-concepts.md -> "Prefix Caching (Provider-Side)"
#     (put static content first for caching benefits)
#
# ALSO SEE:
#   - examples.py -> Section 3 "CONTEXT WINDOW MANAGEMENT"
#     (TruncationStrategy enum, truncate_to_token_limit(),
#      manage_conversation_context() with sliding window approach)
#   - examples.py -> Section 7 "TOKEN BUDGET PLANNER"
#     (TokenBudget dataclass showing how to allocate context budget)
#
# Implement multiple strategies for fitting content into a context window.
#
# Key concepts:
#   - Context windows are measured in tokens, not characters
#   - Different strategies preserve different information
#   - "Lost in the middle" means beginning and end matter most


class TruncationStrategy(Enum):
    KEEP_RECENT = "keep_recent"     # Keep most recent messages (chat history)
    KEEP_RELEVANT = "keep_relevant" # Keep messages most relevant to query
    SLIDING_WINDOW = "sliding_window" # Fixed window of most recent tokens
    MAP_REDUCE = "map_reduce"       # Summarize chunks, then combine


@dataclass
class ConversationMessage:
    role: str       # "system", "user", "assistant"
    content: str
    timestamp: float = 0.0  # Unix timestamp


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken."""
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def truncate_keep_recent(
    messages: list[ConversationMessage],
    max_tokens: int,
    system_prompt: str,
) -> list[ConversationMessage]:
    """Keep the system prompt and most recent messages that fit.

    TODO: Implement this function.

    Strategy: Always include the system prompt. Then add messages from most
    recent to oldest until the token budget is exhausted.
    (See examples.py manage_conversation_context() for the same pattern.)

    Steps:
    1. Calculate tokens for the system prompt (always included)
       - sys_tokens = count_tokens(system_prompt) + 4  # +4 for role overhead
       - remaining = max_tokens - sys_tokens
    2. Iterate through messages in reverse chronological order
       - for msg in reversed(messages):
    3. Add each message if it fits within remaining token budget
       - msg_tokens = count_tokens(msg.content) + 4  # +4 overhead
       - if msg_tokens <= remaining: add it, remaining -= msg_tokens
    4. Account for ~4 tokens overhead per message (role, formatting)
    5. Return messages in chronological order (system first, then oldest-to-newest)
       - Build result as: [ConversationMessage("system", system_prompt)] + selected (reversed back)
       - Use list.insert(0, msg) or collect then reverse

    This is the most common strategy for chat applications -- users care most
    about the recent conversation context.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement truncate_keep_recent")


def truncate_keep_relevant(
    messages: list[ConversationMessage],
    max_tokens: int,
    system_prompt: str,
    query: str,
) -> list[ConversationMessage]:
    """Keep messages most relevant to the current query.

    TODO: Implement this function.

    Strategy: Score each message by keyword overlap with the query, then
    keep the highest-scoring messages that fit. Always keep the system prompt
    and the most recent user message.

    Steps:
    1. Always reserve space for system prompt and the latest message
       - sys_tokens = count_tokens(system_prompt) + 4
       - latest_tokens = count_tokens(messages[-1].content) + 4
       - remaining = max_tokens - sys_tokens - latest_tokens
    2. Score remaining messages by word overlap with the query:
       - query_words = set(query.lower().split())
       - msg_words = set(msg.content.lower().split())
       - score = len(query_words & msg_words) / len(query_words) if query_words else 0
    3. Sort by score descending
       - scored = [(msg, score), ...]; scored.sort(key=lambda x: x[1], reverse=True)
    4. Add messages until budget is exhausted
       - for msg, score in scored: if count_tokens(msg.content)+4 <= remaining: add
    5. Return in chronological order
       - Sort selected by timestamp, prepend system message, append latest message

    Note: In production, you'd use embeddings for relevance scoring instead
    of keyword overlap. This exercise uses keywords for simplicity.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement truncate_keep_relevant")


def split_into_chunks(
    text: str,
    chunk_size_tokens: int,
    overlap_tokens: int = 0,
) -> list[str]:
    """Split text into token-based chunks with optional overlap.

    TODO: Implement this function.
    (See examples.py truncate_to_token_limit() for token-level encode/decode.)

    Steps:
    1. Encode the entire text into tokens
       - enc = tiktoken.get_encoding("cl100k_base")
       - tokens = enc.encode(text)
    2. Split into chunks of chunk_size_tokens
       - stride = chunk_size_tokens - overlap_tokens
       - Iterate: start = 0; while start < len(tokens)
    3. If overlap_tokens > 0, each chunk starts overlap_tokens before
       the previous chunk ended (sliding window)
       - chunk_tokens = tokens[start : start + chunk_size_tokens]
       - start += stride (not chunk_size_tokens)
    4. Decode each chunk back to text
       - chunk_text = enc.decode(chunk_tokens)
    5. Return the list of text chunks

    Overlap helps preserve context at chunk boundaries -- a sentence split
    across two chunks will appear fully in at least one of them.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement split_into_chunks")


# ============================================================================
# EXERCISE 4: Embedding Similarity Search
# ============================================================================
# READ FIRST:
#   - 01-transformer-architecture-fundamentals.md -> "Embeddings" section
#     (embedding models, cosine similarity formula, MTEB scores,
#      key constraint: embeddings from different models are incompatible)
#   - 03-advanced-llm-concepts.md -> "Glossary" -> "Embeddings and Retrieval Terms"
#     (cosine similarity, Matryoshka embeddings, normalization)
#
# ALSO SEE:
#   - examples.py -> Section 5 "EMBEDDING SIMILARITY COMPARISON"
#     (cosine_similarity() implementation, find_most_similar(),
#      demonstrate_embedding_similarity() -- follow the same math)
#
# Implement similarity search operations common in RAG systems.
#
# Key concepts:
#   - Cosine similarity is the standard metric for text embeddings
#   - Threshold selection affects precision/recall tradeoff
#   - Re-ranking can improve retrieval quality


@dataclass
class Document:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    document: Document
    score: float
    rank: int


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    TODO: Implement this function.
    (See examples.py cosine_similarity() for a reference implementation.)

    Formula: cos_sim(A, B) = (A . B) / (||A|| * ||B||)

    Implementation:
    1. Validate: if len(a) != len(b): raise ValueError(...)
    2. dot_product = sum(x * y for x, y in zip(a, b))
    3. magnitude_a = math.sqrt(sum(x * x for x in a))
    4. magnitude_b = math.sqrt(sum(x * x for x in b))
    5. if magnitude_a == 0 or magnitude_b == 0: return 0.0
    6. return dot_product / (magnitude_a * magnitude_b)

    Handle edge cases:
    - If either vector has zero magnitude, return 0.0
    - Vectors must be the same length (raise ValueError if not)
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement cosine_similarity")


def semantic_search(
    query_embedding: list[float],
    documents: list[Document],
    top_k: int = 5,
    threshold: float = 0.0,
) -> list[SearchResult]:
    """Find the most similar documents to a query embedding.

    TODO: Implement this function.
    (See examples.py find_most_similar() for a simpler version of this pattern.)

    Steps:
    1. Compute cosine similarity between query_embedding and each document's embedding
       - for doc in documents: score = cosine_similarity(query_embedding, doc.embedding)
    2. Filter out results below the similarity threshold
       - if score >= threshold: keep
    3. Sort by similarity descending
       - results.sort(key=lambda x: x[1], reverse=True)
    4. Return top_k results as SearchResult objects (with rank starting at 1)
       - return [SearchResult(document=doc, score=score, rank=i+1) for i, (doc, score) in enumerate(top_results)]

    The threshold parameter controls precision/recall:
    - High threshold (0.8+): fewer results, higher precision
    - Low threshold (0.3-0.5): more results, higher recall
    - In production, tune this based on your evaluation metrics
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement semantic_search")


def diversity_rerank(
    results: list[SearchResult],
    lambda_param: float = 0.5,
    top_k: int = 5,
) -> list[SearchResult]:
    """Re-rank results using Maximal Marginal Relevance (MMR).

    TODO: Implement this function.

    MMR balances relevance to the query with diversity among results.
    This prevents returning 5 near-identical documents when 5 diverse
    but relevant documents would be more useful.

    Algorithm (greedy):
    1. Start with the highest-scoring result in the selected set
       - selected = [results[0]]
       - candidates = results[1:]
    2. For each remaining slot (while len(selected) < top_k and candidates):
       a. For each candidate not yet selected, compute:
          MMR_score = lambda_param * candidate.score - (1 - lambda_param) * max_sim_to_selected
          where max_sim_to_selected = max(cosine_similarity(candidate.document.embedding,
                                          s.document.embedding) for s in selected)
       b. Select the candidate with the highest MMR_score
          - best = max(candidates, key=lambda c: mmr_score(c))
          - selected.append(best); candidates.remove(best)
    3. Re-assign ranks 1 through top_k
       - for i, result in enumerate(selected): result.rank = i + 1
       - Or create new SearchResult objects with updated ranks
    4. Return the re-ranked list

    lambda_param controls the tradeoff:
    - lambda=1.0: pure relevance (no diversity)
    - lambda=0.0: pure diversity (ignore relevance)
    - lambda=0.5: balanced (typical default)
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement diversity_rerank")


# ============================================================================
# EXERCISE 5: Parameter Configuration Designer
# ============================================================================
# READ FIRST:
#   - 01-transformer-architecture-fundamentals.md -> "Key Parameters for Generation"
#     (Temperature table, Top-p, Top-k, Frequency/Presence penalties,
#      Max Tokens, Stop Sequences -- understand each parameter's effect)
#   - 02-training-and-model-families.md -> "Recommended Parameter Presets" table
#     (per-task temperature, top_p, max_tokens recommendations)
#
# ALSO SEE:
#   - examples.py -> Section 4 "PARAMETER TUNING EXAMPLES"
#     (GenerationConfig dataclass, GENERATION_PRESETS dict with 6 presets:
#      "deterministic", "precise", "balanced", "creative", "classifier",
#      "json_extraction" -- use these as reference for your designs)
#
# Design parameter configurations for different use cases, demonstrating
# understanding of how generation parameters affect output.
#
# Key concepts:
#   - Temperature controls the shape of the probability distribution
#   - top_p adaptively truncates the distribution
#   - Penalties reduce repetition in different ways
#   - Stop sequences control output boundaries


@dataclass
class GenerationParams:
    temperature: float
    top_p: float
    max_tokens: int
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: list[str] = field(default_factory=list)


def design_params_for_json_extraction() -> GenerationParams:
    """Design parameters for extracting structured JSON from text.

    TODO: Implement this function.
    (Reference: examples.py GENERATION_PRESETS["json_extraction"])

    Requirements:
    - Output must be deterministic (same input -> same output) -> temperature=0
    - Output is JSON, typically 100-2000 tokens -> max_tokens=2048
    - No creative variation wanted -> top_p=1.0 (no additional restriction)
    - Should stop generating after the JSON block -> stop_sequences=["```"] or similar

    Return GenerationParams(temperature=..., top_p=..., max_tokens=...,
                            stop_sequences=[...])
    Explain your choices in comments.
    """
    # TODO: Return a GenerationParams with appropriate values
    raise NotImplementedError("Implement design_params_for_json_extraction")


def design_params_for_creative_writing() -> GenerationParams:
    """Design parameters for creative story generation.

    TODO: Implement this function.
    (Reference: examples.py GENERATION_PRESETS["creative"])

    Requirements:
    - High diversity and creativity -> temperature=0.9-1.0
    - Avoid repetitive phrases -> use frequency_penalty (0.3-0.6) and/or presence_penalty (0.3-0.6)
    - Long output (stories can be 2000-8000 tokens) -> max_tokens=4096 or 8192
    - Natural, varied language -> top_p=0.95

    Return GenerationParams(temperature=..., top_p=..., max_tokens=...,
                            frequency_penalty=..., presence_penalty=...)
    Explain your choices in comments.
    """
    # TODO: Return a GenerationParams with appropriate values
    raise NotImplementedError("Implement design_params_for_creative_writing")


def design_params_for_classification() -> GenerationParams:
    """Design parameters for text classification (e.g., sentiment: positive/negative/neutral).

    TODO: Implement this function.
    (Reference: examples.py GENERATION_PRESETS["classifier"])

    Requirements:
    - Deterministic output -> temperature=0
    - Very short output (just the label) -> max_tokens=10-50
    - Must stop after producing the label -> stop_sequences=["\n"] to stop after first line
    - No extra explanation -> low max_tokens + stop sequence enforces brevity

    Return GenerationParams(temperature=0, top_p=1.0, max_tokens=...,
                            stop_sequences=["\n"])
    Explain your choices in comments.
    """
    # TODO: Return a GenerationParams with appropriate values
    raise NotImplementedError("Implement design_params_for_classification")


def design_params_for_code_generation() -> GenerationParams:
    """Design parameters for generating production code.

    TODO: Implement this function.
    (Reference: examples.py GENERATION_PRESETS["precise"])

    Requirements:
    - High correctness (low temperature) -> temperature=0.1-0.2
    - But some variation allowed (not always same variable names) -> temperature > 0
    - Moderate output length -> max_tokens=4096
    - No repetitive code patterns -> small frequency_penalty (0.1-0.2) optional

    The test asserts: 0 < temperature <= 0.3
    Return GenerationParams(temperature=0.2, top_p=0.95, max_tokens=4096, ...)
    Explain your choices in comments.
    """
    # TODO: Return a GenerationParams with appropriate values
    raise NotImplementedError("Implement design_params_for_code_generation")


def design_params_for_data_analysis() -> GenerationParams:
    """Design parameters for analyzing data and producing insights.

    TODO: Implement this function.
    (Reference: examples.py GENERATION_PRESETS["balanced"] -- but pull temperature lower)

    Requirements:
    - Factual and precise -> temperature in range 0.1-0.5
    - Some creativity allowed for insight generation -> not temperature=0
    - Moderate to long output -> max_tokens=2048-4096
    - Avoid repetitive phrasing in the analysis -> presence_penalty=0.1-0.3 optional

    The test asserts: 0.1 <= temperature <= 0.5 and max_tokens >= 1000
    Return GenerationParams(temperature=0.3, top_p=0.95, max_tokens=2048, ...)
    Explain your choices in comments.
    """
    # TODO: Return a GenerationParams with appropriate values
    raise NotImplementedError("Implement design_params_for_data_analysis")


# ============================================================================
# TESTS
# ============================================================================

def test_exercise_1() -> None:
    """Test the multi-model cost estimator."""
    print("Testing Exercise 1: Multi-Model Cost Estimator")
    print("-" * 50)

    sample_input = "What is the capital of France? " * 10  # ~80 tokens
    cached_prefix = "You are a helpful geography assistant. "  # ~7 tokens

    # Test basic cost estimation
    estimate = estimate_request_cost(
        input_text=sample_input,
        estimated_output_tokens=100,
        model_name="gpt-4o",
    )
    assert isinstance(estimate, CostEstimate), "Should return a CostEstimate"
    assert estimate.input_tokens > 0, "Should count input tokens"
    assert estimate.total_cost > 0, "Should calculate a positive cost"
    assert estimate.fits_in_context, "Should fit in gpt-4o context window"
    print(f"  Basic estimation: {estimate.total_cost:.6f} USD")

    # Test with caching
    estimate_cached = estimate_request_cost(
        input_text=sample_input,
        estimated_output_tokens=100,
        model_name="claude-sonnet-4",
        cached_prefix_text=cached_prefix,
    )
    estimate_uncached = estimate_request_cost(
        input_text=sample_input,
        estimated_output_tokens=100,
        model_name="claude-sonnet-4",
    )
    assert estimate_cached.total_cost < estimate_uncached.total_cost, \
        "Cached request should be cheaper"
    print(f"  Cached vs uncached: ${estimate_cached.total_cost:.6f} vs ${estimate_uncached.total_cost:.6f}")

    # Test batch discount
    estimate_batch = estimate_request_cost(
        input_text=sample_input,
        estimated_output_tokens=100,
        model_name="gpt-4o",
        is_batch=True,
    )
    assert estimate_batch.total_cost < estimate.total_cost, \
        "Batch request should be cheaper"
    print(f"  Batch vs realtime: ${estimate_batch.total_cost:.6f} vs ${estimate.total_cost:.6f}")

    # Test cheapest model finder
    cheapest_model, cheapest_estimate = find_cheapest_model(
        input_text=sample_input,
        estimated_output_tokens=100,
    )
    print(f"  Cheapest model: {cheapest_model} at ${cheapest_estimate.total_cost:.6f}")

    print("  PASSED\n")


def test_exercise_2() -> None:
    """Test the model router."""
    print("Testing Exercise 2: Model Router")
    print("-" * 50)

    # Test task type inference
    assert infer_task_type("Classify this email as spam or not") == TaskType.CLASSIFICATION
    assert infer_task_type("Write a poem about the ocean") == TaskType.GENERATION
    assert infer_task_type("Implement a binary search function") == TaskType.CODE
    print("  Task type inference: PASSED")

    # Test basic routing
    result = route_request(RoutingRequest(prompt="Classify this as positive or negative"))
    assert result.model == "gpt-4o-mini", f"Classification should use mini, got {result.model}"
    assert result.generation_config["temperature"] == 0, "Classification should be deterministic"
    print(f"  Classification routing: {result.model} (temp={result.generation_config['temperature']})")

    # Test max_quality override
    result = route_request(RoutingRequest(
        prompt="Classify this as positive or negative",
        max_quality=True,
    ))
    assert result.model == "claude-sonnet-4", f"max_quality should use sonnet, got {result.model}"
    print(f"  Max quality override: {result.model}")

    # Test max_speed override
    result = route_request(RoutingRequest(
        prompt="Implement a sorting algorithm",
        max_speed=True,
    ))
    assert result.model == "gpt-4o-mini", f"max_speed should use mini, got {result.model}"
    print(f"  Max speed override: {result.model}")

    print("  PASSED\n")


def test_exercise_3() -> None:
    """Test context window truncation."""
    print("Testing Exercise 3: Context Window Truncation")
    print("-" * 50)

    system_prompt = "You are a helpful assistant."

    messages = [
        ConversationMessage(role="user", content=f"Message {i}: " + "word " * 50, timestamp=float(i))
        for i in range(20)
    ]

    # Test keep_recent: should keep system prompt and most recent messages
    result = truncate_keep_recent(messages, max_tokens=500, system_prompt=system_prompt)
    assert len(result) > 0, "Should return at least one message"
    assert result[0].role == "system", "First message should be system prompt"
    # Last message in result should be the most recent original message
    assert "Message 19" in result[-1].content, "Should include the most recent message"
    print(f"  Keep recent: {len(result)} messages fit in 500 tokens")

    # Test keep_relevant
    result = truncate_keep_relevant(
        messages, max_tokens=500, system_prompt=system_prompt,
        query="Message 5"
    )
    assert len(result) > 0, "Should return at least one message"
    print(f"  Keep relevant: {len(result)} messages fit in 500 tokens")

    # Test chunking
    long_text = "This is a sentence about testing. " * 100
    chunks = split_into_chunks(long_text, chunk_size_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1, "Should produce multiple chunks"
    for chunk in chunks:
        assert count_tokens(chunk) <= 100, "Each chunk should be within token limit"
    print(f"  Chunking: {len(chunks)} chunks of 100 tokens (20 overlap)")

    # Test chunking without overlap
    chunks_no_overlap = split_into_chunks(long_text, chunk_size_tokens=100, overlap_tokens=0)
    assert len(chunks_no_overlap) <= len(chunks), \
        "Without overlap, should have same or fewer chunks"
    print(f"  Chunking (no overlap): {len(chunks_no_overlap)} chunks")

    print("  PASSED\n")


def test_exercise_4() -> None:
    """Test embedding similarity search."""
    print("Testing Exercise 4: Embedding Similarity Search")
    print("-" * 50)

    # Test cosine similarity
    assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001, "Identical vectors = 1.0"
    assert abs(cosine_similarity([1, 0, 0], [0, 1, 0]) - 0.0) < 0.001, "Orthogonal vectors = 0.0"
    assert abs(cosine_similarity([1, 0, 0], [-1, 0, 0]) - (-1.0)) < 0.001, "Opposite vectors = -1.0"
    assert cosine_similarity([0, 0, 0], [1, 0, 0]) == 0.0, "Zero vector = 0.0"
    print("  Cosine similarity: PASSED")

    # Test semantic search
    documents = [
        Document("doc1", "Python programming", [0.9, 0.1, 0.0]),
        Document("doc2", "JavaScript coding", [0.8, 0.2, 0.1]),
        Document("doc3", "Cooking recipes", [0.0, 0.1, 0.9]),
        Document("doc4", "Machine learning", [0.7, 0.6, 0.0]),
        Document("doc5", "Baking bread", [0.1, 0.0, 0.8]),
    ]
    query = [0.85, 0.15, 0.05]  # Similar to "Python programming"

    results = semantic_search(query, documents, top_k=3)
    assert len(results) == 3, "Should return top 3"
    assert results[0].document.id == "doc1", "Most similar should be doc1"
    assert results[0].rank == 1, "First result should have rank 1"
    print(f"  Semantic search: top result = {results[0].document.id} ({results[0].score:.4f})")

    # Test with threshold
    results_filtered = semantic_search(query, documents, top_k=5, threshold=0.8)
    assert all(r.score >= 0.8 for r in results_filtered), "All results should meet threshold"
    print(f"  With threshold 0.8: {len(results_filtered)} results")

    # Test MMR diversity re-ranking
    results_all = semantic_search(query, documents, top_k=5)
    results_diverse = diversity_rerank(results_all, lambda_param=0.5, top_k=3)
    assert len(results_diverse) == 3, "Should return 3 re-ranked results"
    assert results_diverse[0].rank == 1, "First result should have rank 1"
    print(f"  MMR re-ranking: top result = {results_diverse[0].document.id}")

    print("  PASSED\n")


def test_exercise_5() -> None:
    """Test parameter configuration designs."""
    print("Testing Exercise 5: Parameter Configuration Designer")
    print("-" * 50)

    # JSON extraction
    params = design_params_for_json_extraction()
    assert params.temperature == 0, "JSON extraction should be deterministic"
    assert params.max_tokens >= 100, "Should allow enough tokens for JSON"
    assert len(params.stop_sequences) > 0, "Should have stop sequences"
    print(f"  JSON extraction: temp={params.temperature}, stops={params.stop_sequences}")

    # Creative writing
    params = design_params_for_creative_writing()
    assert params.temperature >= 0.7, "Creative writing should have high temperature"
    assert params.max_tokens >= 2000, "Should allow long output"
    assert params.presence_penalty > 0 or params.frequency_penalty > 0, \
        "Should use penalties to avoid repetition"
    print(f"  Creative writing: temp={params.temperature}, penalties=({params.frequency_penalty}, {params.presence_penalty})")

    # Classification
    params = design_params_for_classification()
    assert params.temperature == 0, "Classification should be deterministic"
    assert params.max_tokens <= 100, "Classification output should be very short"
    assert len(params.stop_sequences) > 0, "Should stop after the label"
    print(f"  Classification: temp={params.temperature}, max_tokens={params.max_tokens}")

    # Code generation
    params = design_params_for_code_generation()
    assert params.temperature <= 0.3, "Code should be low temperature for correctness"
    assert params.temperature > 0, "But not fully deterministic (some variation)"
    print(f"  Code generation: temp={params.temperature}, top_p={params.top_p}")

    # Data analysis
    params = design_params_for_data_analysis()
    assert 0.1 <= params.temperature <= 0.5, "Analysis should be mostly precise"
    assert params.max_tokens >= 1000, "Analysis needs room for detailed output"
    print(f"  Data analysis: temp={params.temperature}")

    print("  PASSED\n")


def run_all_tests() -> None:
    """Run all exercise tests."""
    print("=" * 60)
    print("LLM Fundamentals -- Exercise Tests")
    print("=" * 60)
    print()

    tests = [
        ("Exercise 1: Cost Estimator", test_exercise_1),
        ("Exercise 2: Model Router", test_exercise_2),
        ("Exercise 3: Context Truncation", test_exercise_3),
        ("Exercise 4: Embedding Search", test_exercise_4),
        ("Exercise 5: Parameter Design", test_exercise_5),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except NotImplementedError as e:
            print(f"  {name}: NOT IMPLEMENTED ({e})\n")
            failed += 1
        except AssertionError as e:
            print(f"  {name}: FAILED -- {e}\n")
            failed += 1
        except Exception as e:
            print(f"  {name}: ERROR -- {type(e).__name__}: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
