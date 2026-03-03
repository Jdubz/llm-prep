"""
AI/ML Solutions Engineering -- Exercises

Skeleton functions with TODOs. Implement each function to practice
building AI/ML solutions engineering tools: use case evaluation,
expectation setting, architecture design, cost modeling, evaluation
harnesses, and responsible AI checklists.

Each exercise includes:
- A docstring explaining the task and requirements
- Type hints for inputs and outputs
- TODO comments marking what you need to implement
- Test cases you can use to verify your implementation

Difficulty is noted per exercise: [Moderate] or [Advanced].
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Shared data models
# ---------------------------------------------------------------------------

class AIApproach(Enum):
    RAG = "rag"
    FINE_TUNING = "fine_tuning"
    PROMPT_ENGINEERING = "prompt_engineering"
    CLASSIFICATION = "classification"
    AGENT = "agent"
    NOT_SUITABLE = "not_suitable"


class DataSensitivity(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"  # HIPAA, PCI, etc.


class Priority(Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    NICE_TO_HAVE = "nice_to_have"


@dataclass
class UseCase:
    """A customer's AI use case to evaluate."""
    description: str
    data_type: str               # "text", "tabular", "image", "mixed"
    volume: int                  # Number of records / documents
    error_tolerance: float       # 0.0 (no errors allowed) to 1.0 (errors acceptable)
    latency_requirement: str     # "real_time" (<1s), "fast" (<5s), "batch" (minutes+)
    compliance_needs: list[str]  # e.g., ["HIPAA", "SOC2", "GDPR"]
    has_labeled_data: bool
    labeled_data_count: int      # 0 if no labeled data


@dataclass
class UseCaseAssessment:
    """Result of evaluating an AI use case."""
    overall_score: float              # 0.0 to 1.0
    data_quality_score: float         # 0.0 to 1.0
    measurability_score: float        # 0.0 to 1.0
    error_tolerance_score: float      # 0.0 to 1.0
    volume_score: float               # 0.0 to 1.0
    recommended_approach: AIApproach
    risk_factors: list[str]
    rationale: str


@dataclass
class ExpectationDoc:
    """Realistic expectations for an AI use case."""
    use_case_category: str
    what_to_expect: list[str]
    what_not_to_expect: list[str]
    key_risks: list[str]
    recommended_benchmarks: dict[str, str]  # metric name -> target value
    timeline_estimate: str
    pilot_scope_recommendation: str


@dataclass
class RAGComponent:
    """A selected component for a RAG architecture."""
    component_type: str   # "embedding_model", "vector_db", "llm", "orchestration"
    name: str             # e.g., "text-embedding-3-small", "Pinecone", "Claude Sonnet"
    justification: str    # Why this component was selected


@dataclass
class RAGDesign:
    """Complete RAG architecture design."""
    components: list[RAGComponent]
    mermaid_diagram: str
    estimated_monthly_cost: float
    key_risks: list[str]
    recommended_chunk_strategy: str
    recommended_chunk_size: int


@dataclass
class ModelTierCost:
    """Cost for a specific model tier."""
    tier_name: str
    model_name: str
    monthly_cost: float
    annual_cost: float
    input_cost: float
    output_cost: float


@dataclass
class CostProjection:
    """Complete cost projection for an LLM deployment."""
    base_monthly_cost: float
    base_annual_cost: float
    optimized_monthly_cost: float
    optimized_annual_cost: float
    savings_breakdown: dict[str, float]  # optimization type -> monthly savings
    tier_comparison: list[ModelTierCost]
    assumptions: list[str]


@dataclass
class EvalTestCase:
    """A single test case for AI evaluation."""
    input_text: str
    expected_output: str
    actual_output: str


@dataclass
class EvalCaseResult:
    """Result for a single evaluation test case."""
    test_case: EvalTestCase
    exact_match: bool
    fuzzy_score: float        # 0.0 to 1.0
    length_ratio: float       # actual length / expected length
    passed: bool


@dataclass
class EvalReport:
    """Aggregated evaluation report."""
    total_cases: int
    pass_count: int
    fail_count: int
    exact_match_rate: float
    avg_fuzzy_score: float
    avg_length_ratio: float
    case_results: list[EvalCaseResult]
    summary: str


@dataclass
class ChecklistItem:
    """A single item in an AI compliance checklist."""
    category: str       # e.g., "Data Privacy", "Model Safety", "Compliance"
    item: str           # The checklist item description
    priority: Priority
    rationale: str


@dataclass
class AIChecklist:
    """Complete AI compliance and safety checklist."""
    industry: str
    data_sensitivity: DataSensitivity
    deployment_model: str
    required_items: list[ChecklistItem]
    recommended_items: list[ChecklistItem]
    nice_to_have_items: list[ChecklistItem]
    total_items: int


# ============================================================================
# EXERCISE 1: AI Use Case Evaluator
# [Moderate]
#
# READ FIRST:
#   01-ai-ml-discovery-and-use-cases.md
#     -> "Evaluating AI Readiness" -- maturity model table, assessment dimensions
#     -> "Common AI/ML Use Cases by Industry" -- decision tree for approach selection
#     -> "Setting Realistic AI Expectations" -- success metrics table
#
# ALSO SEE:
#   examples.py -> "1. AI USE CASE SCORING" section:
#     - score_data_quality(), score_measurability(), score_volume()
#     - evaluate_use_case() (full scoring pipeline)
#     - recommend_approach() (decision tree implementation)
#
# Description:
#   Build a function that takes a UseCase dataclass and evaluates its
#   AI-readiness across four dimensions: data quality, measurability,
#   error tolerance, and data volume. Based on the scores, recommend
#   the most appropriate AI approach.
#
# Key concepts:
#   - Multi-dimensional scoring
#   - Approach selection based on data characteristics
#   - Risk factor identification
# ============================================================================

def evaluate_use_case(use_case: UseCase) -> UseCaseAssessment:
    """Evaluate an AI use case and recommend an approach.

    Scoring guidelines:
    - data_quality_score: Based on data_type (text=0.8, tabular=0.9, image=0.7,
      mixed=0.6), penalize if no labeled data, bonus if labeled_data_count > 1000
    - measurability_score: Based on error_tolerance (higher tolerance = easier to
      measure success). Score = 0.5 + (error_tolerance * 0.5). If compliance_needs
      exist, add 0.1 (regulated = well-defined success criteria)
    - error_tolerance_score: Direct mapping -- error_tolerance value is the score
    - volume_score: 0.3 if volume < 100, 0.5 if < 1000, 0.7 if < 10000,
      0.9 if < 100000, 1.0 if >= 100000

    Approach recommendation logic:
    - If overall_score < 0.4: NOT_SUITABLE
    - If has_labeled_data and labeled_data_count >= 5000: FINE_TUNING
    - If data_type == "text" and volume >= 100: RAG
    - If data_type == "tabular": CLASSIFICATION
    - If error_tolerance >= 0.3 and latency_requirement != "real_time":
      PROMPT_ENGINEERING
    - Default: RAG

    Risk factors to check:
    - No labeled data for fine-tuning recommendation
    - Low volume (<100 records)
    - Zero error tolerance
    - Compliance requirements with real-time latency
    - Mixed data types

    Returns:
        UseCaseAssessment with all scores, recommended approach, and risk factors.

    TODO: Implement this function.
    Hint 1: Score each dimension independently using the guidelines above.
    Hint 2: Compute overall_score as the weighted average:
            data_quality * 0.35 + measurability * 0.2 + error_tolerance * 0.2 + volume * 0.25
    Hint 3: Walk through the approach recommendation logic in order.
    Hint 4: Build risk_factors list by checking each risk condition.
    Hint 5: Write a rationale string summarizing the recommendation.
    """
    pass


# ============================================================================
# EXERCISE 2: AI Expectation Setter
# [Moderate]
#
# READ FIRST:
#   01-ai-ml-discovery-and-use-cases.md
#     -> "Setting Realistic AI Expectations" -- the accuracy conversation,
#        the 80/20 pilot approach, timeline expectations table,
#        success metrics table
#
# ALSO SEE:
#   examples.py -> "5. AI READINESS ASSESSMENT" section:
#     - generate_readiness_report() (report generation pattern)
#
# Description:
#   Build a function that takes a use case category and the customer's
#   stated expectations, and generates a realistic expectation document.
#   This function codifies the "expectation setting" conversation an SE
#   has with a customer.
#
# Key concepts:
#   - Mapping customer expectations to realistic outcomes
#   - Identifying unrealistic expectations
#   - Providing concrete benchmarks and timelines
# ============================================================================

# Reference data for expectation setting
USE_CASE_BENCHMARKS: dict[str, dict[str, Any]] = {
    "customer_support": {
        "realistic_accuracy": "85-92% on common queries, 70-80% on edge cases",
        "realistic_timeline": "POC in 3-4 weeks, production in 8-12 weeks",
        "typical_deflection": "25-40% ticket deflection in first month",
        "common_overestimates": [
            "99% accuracy from day one",
            "full automation with no human oversight",
            "handles every possible query type",
            "cheaper than human agents immediately",
        ],
        "benchmarks": {
            "accuracy_common": "85-92%",
            "accuracy_edge": "70-80%",
            "deflection_rate": "25-40%",
            "csat_score": ">4.0/5.0",
            "avg_response_time": "<3 seconds",
        },
    },
    "document_processing": {
        "realistic_accuracy": "90-95% on structured fields, 80-90% on unstructured",
        "realistic_timeline": "POC in 2-3 weeks, production in 6-10 weeks",
        "typical_deflection": "50-70% of manual processing eliminated",
        "common_overestimates": [
            "100% extraction accuracy on all document types",
            "handles handwritten text perfectly",
            "no human review needed",
            "works with any document format immediately",
        ],
        "benchmarks": {
            "field_extraction_accuracy": "90-95%",
            "document_classification": "92-97%",
            "processing_time_reduction": "50-70%",
            "human_review_rate": "10-20% of documents",
        },
    },
    "content_generation": {
        "realistic_accuracy": "70-85% acceptable on first draft, 90%+ after human edit",
        "realistic_timeline": "POC in 1-2 weeks, production in 4-6 weeks",
        "typical_deflection": "60-80% reduction in drafting time",
        "common_overestimates": [
            "publish-ready content with no editing",
            "perfect brand voice from day one",
            "handles all content types equally well",
            "replaces the writing team entirely",
        ],
        "benchmarks": {
            "first_draft_acceptance": "70-85%",
            "time_reduction": "60-80%",
            "brand_alignment": ">80% after tuning",
            "human_edit_rate": "80-100% of outputs reviewed",
        },
    },
    "search_and_knowledge": {
        "realistic_accuracy": "80-90% relevance on common queries",
        "realistic_timeline": "POC in 3-4 weeks, production in 8-12 weeks",
        "typical_deflection": "40-60% reduction in search time",
        "common_overestimates": [
            "finds every relevant document every time",
            "understands complex multi-hop queries perfectly",
            "works without any document preprocessing",
            "replaces all existing search infrastructure",
        ],
        "benchmarks": {
            "retrieval_relevance": "80-90%",
            "answer_faithfulness": ">85%",
            "search_time_reduction": "40-60%",
            "user_satisfaction": ">4.0/5.0",
        },
    },
}

# Common unrealistic expectations across all categories
UNIVERSAL_UNREALISTIC = [
    "100% accuracy",
    "zero errors",
    "no human oversight needed",
    "works perfectly on day one",
    "cheaper than the current process immediately",
    "handles all edge cases",
    "real-time with no latency",
]


def set_realistic_expectations(
    use_case_category: str,
    customer_expectations: list[str],
) -> ExpectationDoc:
    """Generate a realistic expectation document for an AI use case.

    Args:
        use_case_category: One of the keys in USE_CASE_BENCHMARKS
            ("customer_support", "document_processing", "content_generation",
             "search_and_knowledge"). If the category is unknown, use
             sensible defaults.
        customer_expectations: List of strings representing what the customer
            has stated they expect (e.g., "99% accuracy", "fully automated",
            "live in 2 weeks").

    Returns:
        ExpectationDoc with realistic expectations, warnings, and benchmarks.

    TODO: Implement this function.
    Hint 1: Look up the use_case_category in USE_CASE_BENCHMARKS. If not found,
            create reasonable defaults.
    Hint 2: Build what_to_expect from the benchmark data's realistic values.
    Hint 3: Build what_not_to_expect by checking customer_expectations against
            UNIVERSAL_UNREALISTIC and common_overestimates. Any customer
            expectation that partially matches (case-insensitive substring)
            an unrealistic item should be flagged.
    Hint 4: key_risks should include: data quality dependency, model update
            risk, edge case handling, and any compliance-related risks.
    Hint 5: recommended_benchmarks comes directly from the benchmark data.
    Hint 6: timeline_estimate from the benchmark data's realistic_timeline.
    Hint 7: pilot_scope_recommendation: suggest starting with the most common
            20% of cases that represent 80% of volume (the 80/20 rule).
    """
    pass


# ============================================================================
# EXERCISE 3: RAG Architecture Designer
# [Advanced]
#
# READ FIRST:
#   02-llm-integration-patterns-and-architecture.md
#     -> "RAG" section -- component explanations, architecture diagrams
#     -> "Choosing Components" -- model selection table, vector DB table,
#        orchestration table
#     -> "Data Pipeline for AI" -- chunking strategies table
#
# ALSO SEE:
#   examples.py -> "2. RAG ARCHITECTURE DESIGNER" section:
#     - select_embedding_model(), select_vector_db(), select_llm()
#     - generate_mermaid_diagram() (Mermaid generation pattern)
#     - design_rag_architecture() (full pipeline)
#
# Description:
#   Build a function that takes customer requirements and generates a
#   complete RAG architecture design with component selections, a Mermaid
#   diagram, and risk analysis.
#
# Key concepts:
#   - Component selection based on requirements
#   - Architecture diagram generation
#   - Cost estimation for multi-component systems
# ============================================================================

@dataclass
class CustomerRequirements:
    """Customer requirements for a RAG system."""
    data_types: list[str]       # ["pdf", "html", "docx", "csv", ...]
    document_count: int         # Total documents to index
    avg_document_pages: int     # Average pages per document
    queries_per_day: int        # Expected query volume
    latency_target: str         # "real_time" (<1s), "fast" (<5s), "batch"
    compliance: list[str]       # ["HIPAA", "SOC2", "GDPR", "FedRAMP", ...]
    existing_cloud: str         # "aws", "azure", "gcp", "none"
    team_size: str              # "small" (<5 engineers), "medium" (5-20), "large" (20+)
    budget: str                 # "low" (<$5K/mo), "medium" ($5K-$50K/mo), "high" (>$50K/mo)


def design_rag_architecture(requirements: CustomerRequirements) -> RAGDesign:
    """Design a RAG architecture based on customer requirements.

    Component selection logic:

    Embedding model:
    - If compliance includes "HIPAA" or "FedRAMP": use cloud-provider embedding
      (Azure OpenAI / Bedrock) for data residency
    - If budget == "low": use "text-embedding-3-small" ($0.02/1M tokens)
    - Default: "text-embedding-3-large" ($0.13/1M tokens)

    Vector database:
    - If existing_cloud == "aws" and compliance: "Amazon OpenSearch Serverless"
    - If existing_cloud == "azure": "Azure AI Search"
    - If document_count < 100_000 and team_size == "small": "Pinecone"
    - If document_count >= 1_000_000: "Qdrant" or "Weaviate"
    - Default: "pgvector" (if they have Postgres) or "Pinecone"

    LLM:
    - If compliance includes "FedRAMP": "Azure OpenAI GPT-4o"
    - If compliance includes "HIPAA": "Azure OpenAI" or "AWS Bedrock Claude"
    - If budget == "low": "Claude Haiku" or "GPT-4o-mini"
    - If queries need complex reasoning: "Claude Sonnet" or "GPT-4o"
    - Default: "Claude Sonnet"

    Orchestration:
    - If team_size == "small": "LlamaIndex" (fastest for RAG)
    - If team_size == "large": "Custom code" (best maintainability)
    - Default: "LangChain"

    Chunking strategy:
    - If data_types includes "pdf" with tables: "document-aware" chunking, 800 tokens
    - If avg_document_pages > 20: "semantic" chunking, 600 tokens
    - Default: "fixed-size" with 500 tokens, 100-token overlap

    Mermaid diagram: Generate a graph TB diagram showing the data ingestion
    pipeline (documents -> processor -> chunker -> embedder -> vector store)
    and query pipeline (query -> embedder -> search -> reranker -> LLM -> response).

    Cost estimation: Rough monthly cost based on:
    - Embedding: document_count * avg_document_pages * 500 tokens * embedding_price
      (one-time, amortized over 12 months)
    - Vector DB: hosting cost estimate based on scale
    - LLM: queries_per_day * 30 * (1500 input + 300 output) tokens * model price

    Returns:
        RAGDesign with all component selections, diagram, and estimates.

    TODO: Implement this function.
    Hint 1: Select each component independently using the logic above.
    Hint 2: Build RAGComponent objects with justification strings.
    Hint 3: Generate the Mermaid diagram as a multi-line string.
    Hint 4: Estimate monthly cost by summing embedding (amortized), vector DB,
            and LLM inference costs.
    Hint 5: Identify risks: compliance gaps, scale concerns, team capability.
    Hint 6: Select chunking strategy based on data types and document size.
    """
    pass


# ============================================================================
# EXERCISE 4: LLM Cost Estimator
# [Moderate]
#
# READ FIRST:
#   03-ai-evaluation-cost-modeling-and-responsible-deployment.md
#     -> "Token Economics" -- token estimation rules, cost modeling template,
#        worked example
#     -> "Cost Optimization Strategies" -- model tiering, caching, batching,
#        prompt optimization
#     -> "TCO Analysis for AI" -- complete cost breakdown
#
# ALSO SEE:
#   examples.py -> "3. TOKEN COST CALCULATOR" section:
#     - MODEL_PRICING dict (price per 1M tokens for each model)
#     - calculate_base_cost() (simple token * price calculation)
#     - apply_optimizations() (caching, batching, tiering savings)
#     - project_costs() (full projection with tier comparison)
#
# Description:
#   Build a cost estimator that takes usage projections and computes
#   monthly/annual costs with optimization strategies applied.
#
# Key concepts:
#   - Token-based pricing math
#   - Caching and batching optimizations
#   - Multi-tier model comparison
# ============================================================================

# Model pricing (per 1M tokens, as of early 2025)
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input": 2.50,
        "output": 10.00,
        "cached_input": 1.25,
        "batch_input": 1.25,
        "batch_output": 5.00,
    },
    "gpt-4o-mini": {
        "input": 0.15,
        "output": 0.60,
        "cached_input": 0.075,
        "batch_input": 0.075,
        "batch_output": 0.30,
    },
    "claude-sonnet": {
        "input": 3.00,
        "output": 15.00,
        "cached_input": 0.30,
        "batch_input": 1.50,
        "batch_output": 7.50,
    },
    "claude-haiku": {
        "input": 0.25,
        "output": 1.25,
        "cached_input": 0.025,
        "batch_input": 0.125,
        "batch_output": 0.625,
    },
    "claude-opus": {
        "input": 15.00,
        "output": 75.00,
        "cached_input": 1.50,
        "batch_input": 7.50,
        "batch_output": 37.50,
    },
}


def estimate_llm_costs(
    requests_per_day: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    model: str,
    cache_hit_rate: float = 0.0,
    batch_percentage: float = 0.0,
) -> CostProjection:
    """Estimate monthly and annual LLM costs with optimizations.

    Args:
        requests_per_day: Number of LLM requests per day.
        avg_input_tokens: Average input tokens per request (system prompt +
            user input + retrieved context).
        avg_output_tokens: Average output tokens per request.
        model: Model name (key in MODEL_PRICING).
        cache_hit_rate: Fraction of requests that hit prompt cache (0.0 to 1.0).
            For cached requests, use "cached_input" price for input tokens.
        batch_percentage: Fraction of requests that can use batch API (0.0 to 1.0).
            For batched requests, use "batch_input" and "batch_output" prices.
            Batch and cache are mutually exclusive -- apply cache first, then
            batch to the remaining non-cached requests.

    Calculation steps:
    1. Compute monthly request volume: requests_per_day * 30
    2. Compute base cost (no optimizations):
       - monthly_input_tokens = monthly_requests * avg_input_tokens
       - monthly_output_tokens = monthly_requests * avg_output_tokens
       - input_cost = monthly_input_tokens * (pricing["input"] / 1_000_000)
       - output_cost = monthly_output_tokens * (pricing["output"] / 1_000_000)
    3. Compute optimized cost:
       - Split requests into: cached, batched, and standard
         - cached_requests = monthly_requests * cache_hit_rate
         - remaining = monthly_requests - cached_requests
         - batched_requests = remaining * batch_percentage
         - standard_requests = remaining - batched_requests
       - For each segment, compute input and output costs using the
         appropriate price tier
       - Sum all segments for optimized total
    4. Compute savings breakdown:
       - caching_savings = base_cost - cost_without_caching_optimization
       - batching_savings = similarly computed
    5. Generate tier comparison:
       - Compute base cost for every model in MODEL_PRICING using the same
         volume but each model's pricing

    Returns:
        CostProjection with base cost, optimized cost, savings, and tier comparison.

    TODO: Implement this function.
    Hint 1: Look up the model in MODEL_PRICING. Raise ValueError if not found.
    Hint 2: Compute base monthly cost with simple multiplication.
    Hint 3: Split requests into three buckets: cached, batched, standard.
    Hint 4: For each bucket, use the correct price column.
    Hint 5: Build tier_comparison by iterating over all models in MODEL_PRICING.
    Hint 6: Populate assumptions list with the key inputs and rates.
    """
    pass


# ============================================================================
# EXERCISE 5: AI Evaluation Harness
# [Moderate]
#
# READ FIRST:
#   03-ai-evaluation-cost-modeling-and-responsible-deployment.md
#     -> "Evaluation Frameworks for Customers" -- what to measure, eval set
#        composition, POC evaluation structure
#     -> "Benchmarking Methodology" -- metrics by use case, baseline comparison
#
# ALSO SEE:
#   examples.py -> "4. EVAL HARNESS" section:
#     - fuzzy_match_score() (character-level similarity implementation)
#     - evaluate_single_case() (per-case scoring)
#     - run_evaluation() (full eval pipeline with report generation)
#
# Description:
#   Build an evaluation harness that takes a list of test cases with
#   expected and actual outputs, computes multiple metrics, and generates
#   an evaluation report with pass/fail per case.
#
# Key concepts:
#   - Multiple evaluation metrics (exact match, fuzzy match, length ratio)
#   - Per-case and aggregate scoring
#   - Pass/fail threshold logic
# ============================================================================

def fuzzy_match_score(s1: str, s2: str) -> float:
    """Compute a simple character-level similarity score between two strings.

    Uses the ratio of common characters to total characters as a simple
    similarity metric. This is a simplified version -- production systems
    would use Levenshtein distance, Jaccard similarity, or embedding similarity.

    Steps:
    1. Normalize both strings: lowercase, strip whitespace.
    2. If both are empty, return 1.0. If one is empty, return 0.0.
    3. Compute the set of character bigrams (2-character subsequences) for each.
       E.g., "hello" -> {"he", "el", "ll", "lo"}
    4. Compute Jaccard similarity: |intersection| / |union|
    5. Return the Jaccard similarity score (0.0 to 1.0).

    TODO: Implement this function.
    Hint 1: Use a set comprehension: {s[i:i+2] for i in range(len(s)-1)}
    Hint 2: Use set intersection (&) and union (|) operators.
    Hint 3: Handle edge case where both bigram sets are empty (strings of
            length 0 or 1) -- return 1.0 if strings are equal, 0.0 otherwise.
    """
    pass


def run_evaluation(
    test_cases: list[EvalTestCase],
    pass_threshold: float = 0.7,
) -> EvalReport:
    """Run evaluation on a list of test cases and generate a report.

    For each test case, compute:
    - exact_match: True if expected == actual (case-insensitive, stripped)
    - fuzzy_score: Result of fuzzy_match_score(expected, actual)
    - length_ratio: len(actual) / len(expected). If expected is empty and
      actual is empty, ratio = 1.0. If expected is empty and actual is not,
      ratio = float('inf'). Handle these edge cases.
    - passed: True if fuzzy_score >= pass_threshold OR exact_match is True

    Aggregate metrics:
    - exact_match_rate: count of exact matches / total cases
    - avg_fuzzy_score: mean of all fuzzy scores
    - avg_length_ratio: mean of all finite length ratios (exclude inf)

    Summary string format:
    "Evaluation: {pass_count}/{total_cases} passed ({pass_rate:.1%}).
     Exact match: {exact_match_rate:.1%}. Avg fuzzy: {avg_fuzzy:.3f}."

    Returns:
        EvalReport with all metrics and per-case results.

    TODO: Implement this function.
    Hint 1: Iterate over test_cases, compute metrics for each using
            fuzzy_match_score.
    Hint 2: Build EvalCaseResult objects for each case.
    Hint 3: Aggregate after processing all cases.
    Hint 4: Handle the edge case of an empty test_cases list gracefully.
    """
    pass


# ============================================================================
# EXERCISE 6: Responsible AI Checklist Generator
# [Advanced]
#
# READ FIRST:
#   03-ai-evaluation-cost-modeling-and-responsible-deployment.md
#     -> "AI Safety for Customer Conversations" -- guardrails table,
#        PII handling
#     -> "Managing AI Risk" -- hallucination mitigation, model monitoring
#     -> "Regulatory Awareness" -- EU AI Act tiers, industry-specific
#        regulations, data residency
#   01-ai-ml-discovery-and-use-cases.md
#     -> "Evaluating AI Readiness" -- maturity assessment dimensions
#
# ALSO SEE:
#   examples.py -> "5. AI READINESS ASSESSMENT" section:
#     - build_checklist() (checklist generation pattern)
#     - INDUSTRY_REQUIREMENTS dict (regulatory requirements by industry)
#
# Description:
#   Build a function that generates a comprehensive AI compliance and
#   safety checklist tailored to the customer's industry, data sensitivity,
#   and deployment model.
#
# Key concepts:
#   - Industry-specific compliance requirements
#   - Risk-based prioritization
#   - Checklist generation from rules
# ============================================================================

# Industry-specific regulatory requirements
INDUSTRY_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "healthcare": [
        {"item": "HIPAA Business Associate Agreement with LLM provider", "category": "Compliance", "rationale": "Required for processing PHI"},
        {"item": "PHI detection and redaction in all inputs", "category": "Data Privacy", "rationale": "PHI must never be sent to non-BAA services"},
        {"item": "Audit logging of all AI interactions", "category": "Compliance", "rationale": "HIPAA requires audit trails for PHI access"},
        {"item": "Clinical validation by licensed professionals", "category": "Model Safety", "rationale": "AI output used in clinical decisions must be reviewed"},
        {"item": "De-identification pipeline for training/eval data", "category": "Data Privacy", "rationale": "HIPAA Safe Harbor or Expert Determination required"},
    ],
    "financial_services": [
        {"item": "Model explainability documentation", "category": "Compliance", "rationale": "Required for fair lending and credit decisions"},
        {"item": "Bias testing across protected classes", "category": "Model Safety", "rationale": "Fair lending regulations require non-discrimination"},
        {"item": "SOX-compliant audit trail for AI decisions", "category": "Compliance", "rationale": "Financial reporting decisions need audit trails"},
        {"item": "PCI DSS compliance for payment data", "category": "Data Privacy", "rationale": "Payment card data must be handled per PCI standards"},
        {"item": "Model risk management framework (SR 11-7)", "category": "Compliance", "rationale": "Fed guidance requires model validation and monitoring"},
    ],
    "legal": [
        {"item": "Source citation for all AI-generated content", "category": "Model Safety", "rationale": "Legal work product must be verifiable"},
        {"item": "Hallucination detection and flagging", "category": "Model Safety", "rationale": "Fabricated case law is a serious professional risk"},
        {"item": "Attorney review requirement for all outputs", "category": "Compliance", "rationale": "AI cannot practice law without attorney oversight"},
        {"item": "Client privilege protection in data handling", "category": "Data Privacy", "rationale": "Attorney-client privilege must be preserved"},
        {"item": "Jurisdiction-specific compliance verification", "category": "Compliance", "rationale": "Legal AI use rules vary by jurisdiction"},
    ],
    "retail": [
        {"item": "Consumer data privacy compliance (CCPA/GDPR)", "category": "Data Privacy", "rationale": "Consumer data handling must comply with privacy laws"},
        {"item": "Content moderation for generated product descriptions", "category": "Model Safety", "rationale": "Brand safety requires content review"},
        {"item": "Transparency disclosure for AI-powered recommendations", "category": "Compliance", "rationale": "EU AI Act requires disclosure for AI interactions"},
    ],
    "government": [
        {"item": "FedRAMP authorized infrastructure", "category": "Compliance", "rationale": "Federal systems require FedRAMP authorization"},
        {"item": "FISMA compliance assessment", "category": "Compliance", "rationale": "Federal information security requirements"},
        {"item": "Data residency within US borders", "category": "Data Privacy", "rationale": "Government data cannot be processed outside the US"},
        {"item": "Section 508 accessibility compliance", "category": "Compliance", "rationale": "Government systems must be accessible"},
        {"item": "ITAR restrictions on model access", "category": "Compliance", "rationale": "Defense-related data has export control restrictions"},
    ],
}

# Universal checklist items applicable to all deployments
UNIVERSAL_REQUIRED: list[dict[str, str]] = [
    {"item": "Input validation and sanitization", "category": "Model Safety", "rationale": "Prevents prompt injection and abuse"},
    {"item": "Output guardrails (content safety filter)", "category": "Model Safety", "rationale": "Prevents harmful or inappropriate outputs"},
    {"item": "PII detection in inputs and outputs", "category": "Data Privacy", "rationale": "Protects user privacy regardless of industry"},
    {"item": "Logging and monitoring of all AI interactions", "category": "Operations", "rationale": "Required for debugging, auditing, and improvement"},
    {"item": "Model version pinning", "category": "Operations", "rationale": "Prevents unexpected behavior changes from model updates"},
    {"item": "Evaluation suite with automated regression testing", "category": "Operations", "rationale": "Catches quality degradation before users do"},
    {"item": "Error handling and graceful degradation", "category": "Operations", "rationale": "System must handle failures without data loss"},
    {"item": "User disclosure that AI is in use", "category": "Compliance", "rationale": "EU AI Act and customer trust require transparency"},
]

UNIVERSAL_RECOMMENDED: list[dict[str, str]] = [
    {"item": "Human-in-the-loop review for high-stakes outputs", "category": "Model Safety", "rationale": "Catches errors on critical decisions"},
    {"item": "Semantic caching for cost optimization", "category": "Operations", "rationale": "Reduces costs and improves latency"},
    {"item": "Multi-model fallback chain", "category": "Operations", "rationale": "Ensures availability during provider outages"},
    {"item": "User feedback collection mechanism", "category": "Operations", "rationale": "Enables continuous improvement from real usage"},
    {"item": "Data drift monitoring", "category": "Operations", "rationale": "Detects when input distribution changes"},
    {"item": "Incident response plan for AI failures", "category": "Operations", "rationale": "Prepared response reduces impact of failures"},
]

UNIVERSAL_NICE_TO_HAVE: list[dict[str, str]] = [
    {"item": "A/B testing framework for prompt variants", "category": "Operations", "rationale": "Enables data-driven optimization"},
    {"item": "Cost anomaly alerting", "category": "Operations", "rationale": "Catches unexpected cost spikes from usage changes"},
    {"item": "Automated prompt regression testing in CI/CD", "category": "Operations", "rationale": "Integrates AI quality into development workflow"},
    {"item": "Red teaming exercise before launch", "category": "Model Safety", "rationale": "Adversarial testing uncovers failure modes"},
]


def generate_ai_checklist(
    industry: str,
    data_sensitivity: DataSensitivity,
    deployment_model: str,
) -> AIChecklist:
    """Generate a comprehensive AI compliance and safety checklist.

    Args:
        industry: Industry key (e.g., "healthcare", "financial_services",
            "legal", "retail", "government"). If unknown, use "general".
        data_sensitivity: Data sensitivity level from DataSensitivity enum.
        deployment_model: Deployment model string -- one of "api_provider"
            (data leaves network), "managed_cloud" (data in customer's cloud),
            or "self_hosted" (fully on-premises).

    Logic:
    1. Start with UNIVERSAL_REQUIRED items as required.
    2. Add UNIVERSAL_RECOMMENDED items as recommended.
    3. Add UNIVERSAL_NICE_TO_HAVE items as nice-to-have.
    4. Look up industry in INDUSTRY_REQUIREMENTS. If found, add all
       industry-specific items as REQUIRED.
    5. Based on data_sensitivity:
       - REGULATED: Add items for encryption at rest and in transit,
         access control audit, data retention policy, and data processing
         agreement. All as REQUIRED.
       - CONFIDENTIAL: Add encryption and access control items as REQUIRED.
         Add data retention as RECOMMENDED.
       - INTERNAL: Add encryption as RECOMMENDED.
       - PUBLIC: No additional items.
    6. Based on deployment_model:
       - "api_provider": Add items for data processing agreement with provider,
         data residency verification, and network security review. As REQUIRED
         if data_sensitivity >= CONFIDENTIAL, else RECOMMENDED.
       - "managed_cloud": Add items for cloud security configuration review
         and VPC/network isolation. As RECOMMENDED.
       - "self_hosted": Add items for GPU infrastructure security, model
         weight protection, and patch management. As RECOMMENDED.

    Returns:
        AIChecklist with all items organized by priority.

    TODO: Implement this function.
    Hint 1: Build three lists (required, recommended, nice_to_have) and populate
            them from the universal and industry-specific sources.
    Hint 2: Convert each dict item to a ChecklistItem with the correct Priority.
    Hint 3: Apply data_sensitivity rules to add or upgrade items.
    Hint 4: Apply deployment_model rules to add items at the correct priority.
    Hint 5: Count total items across all three lists.
    """
    pass


# ---------------------------------------------------------------------------
# Test functions
# ---------------------------------------------------------------------------

def test_exercise_1():
    """Test the AI Use Case Evaluator."""
    print("=" * 60)
    print("EXERCISE 1: AI Use Case Evaluator")
    print("=" * 60)

    # Test case 1: Strong RAG candidate
    uc1 = UseCase(
        description="Answer questions from internal knowledge base",
        data_type="text",
        volume=50_000,
        error_tolerance=0.15,
        latency_requirement="fast",
        compliance_needs=["SOC2"],
        has_labeled_data=False,
        labeled_data_count=0,
    )
    result1 = evaluate_use_case(uc1)
    assert result1 is not None, "Should return a UseCaseAssessment"
    assert result1.recommended_approach == AIApproach.RAG, \
        f"Expected RAG, got {result1.recommended_approach}"
    assert 0.0 <= result1.overall_score <= 1.0, "Score should be 0-1"
    print(f"  Test 1 PASSED: {result1.recommended_approach.value}, "
          f"score={result1.overall_score:.2f}")

    # Test case 2: Fine-tuning candidate
    uc2 = UseCase(
        description="Classify customer tickets by department",
        data_type="text",
        volume=200_000,
        error_tolerance=0.1,
        latency_requirement="real_time",
        compliance_needs=[],
        has_labeled_data=True,
        labeled_data_count=15_000,
    )
    result2 = evaluate_use_case(uc2)
    assert result2.recommended_approach == AIApproach.FINE_TUNING, \
        f"Expected FINE_TUNING, got {result2.recommended_approach}"
    print(f"  Test 2 PASSED: {result2.recommended_approach.value}, "
          f"score={result2.overall_score:.2f}")

    # Test case 3: Not suitable (low volume, zero tolerance)
    uc3 = UseCase(
        description="Predict rare equipment failures",
        data_type="mixed",
        volume=50,
        error_tolerance=0.0,
        latency_requirement="real_time",
        compliance_needs=["HIPAA", "SOC2"],
        has_labeled_data=False,
        labeled_data_count=0,
    )
    result3 = evaluate_use_case(uc3)
    assert result3.recommended_approach == AIApproach.NOT_SUITABLE, \
        f"Expected NOT_SUITABLE, got {result3.recommended_approach}"
    assert len(result3.risk_factors) >= 2, "Should identify multiple risks"
    print(f"  Test 3 PASSED: {result3.recommended_approach.value}, "
          f"risks={result3.risk_factors}")

    print()


def test_exercise_2():
    """Test the AI Expectation Setter."""
    print("=" * 60)
    print("EXERCISE 2: AI Expectation Setter")
    print("=" * 60)

    # Test case 1: Customer support with unrealistic expectations
    result1 = set_realistic_expectations(
        use_case_category="customer_support",
        customer_expectations=[
            "99% accuracy from day one",
            "fully automated, no human agents needed",
            "live in 2 weeks",
        ],
    )
    assert result1 is not None, "Should return an ExpectationDoc"
    assert len(result1.what_to_expect) > 0, "Should have realistic expectations"
    assert len(result1.what_not_to_expect) > 0, "Should flag unrealistic expectations"
    assert "accuracy" in result1.recommended_benchmarks or \
           "accuracy_common" in result1.recommended_benchmarks, \
           "Should include accuracy benchmark"
    print(f"  Test 1 PASSED: {len(result1.what_to_expect)} realistic, "
          f"{len(result1.what_not_to_expect)} unrealistic flagged")

    # Test case 2: Unknown category with reasonable expectations
    result2 = set_realistic_expectations(
        use_case_category="unknown_category",
        customer_expectations=["improve efficiency by 30%"],
    )
    assert result2 is not None, "Should handle unknown categories"
    assert result2.use_case_category == "unknown_category"
    print(f"  Test 2 PASSED: Unknown category handled gracefully")

    # Test case 3: Document processing
    result3 = set_realistic_expectations(
        use_case_category="document_processing",
        customer_expectations=["100% extraction accuracy", "no human review"],
    )
    assert len(result3.what_not_to_expect) >= 2, \
        "Should flag both unrealistic expectations"
    print(f"  Test 3 PASSED: {len(result3.what_not_to_expect)} unrealistic flagged")

    print()


def test_exercise_3():
    """Test the RAG Architecture Designer."""
    print("=" * 60)
    print("EXERCISE 3: RAG Architecture Designer")
    print("=" * 60)

    # Test case 1: Small-scale, budget-conscious
    req1 = CustomerRequirements(
        data_types=["pdf", "docx"],
        document_count=5_000,
        avg_document_pages=10,
        queries_per_day=500,
        latency_target="fast",
        compliance=[],
        existing_cloud="aws",
        team_size="small",
        budget="low",
    )
    result1 = design_rag_architecture(req1)
    assert result1 is not None, "Should return a RAGDesign"
    assert len(result1.components) >= 4, "Should have at least 4 components"
    assert "graph" in result1.mermaid_diagram.lower() or \
           "mermaid" in result1.mermaid_diagram.lower() or \
           "-->" in result1.mermaid_diagram, \
           "Should contain a Mermaid diagram"
    assert result1.estimated_monthly_cost > 0, "Should estimate cost"
    print(f"  Test 1 PASSED: {len(result1.components)} components, "
          f"${result1.estimated_monthly_cost:.2f}/mo")

    # Test case 2: Large-scale, HIPAA-compliant
    req2 = CustomerRequirements(
        data_types=["pdf", "html", "csv"],
        document_count=500_000,
        avg_document_pages=5,
        queries_per_day=10_000,
        latency_target="fast",
        compliance=["HIPAA", "SOC2"],
        existing_cloud="azure",
        team_size="large",
        budget="high",
    )
    result2 = design_rag_architecture(req2)
    # HIPAA should influence component choices
    component_names = [c.name for c in result2.components]
    has_compliant_choice = any(
        "azure" in n.lower() or "bedrock" in n.lower()
        for n in component_names
    )
    assert has_compliant_choice, \
        f"HIPAA should select compliant components, got {component_names}"
    print(f"  Test 2 PASSED: HIPAA-compliant components selected")

    print()


def test_exercise_4():
    """Test the LLM Cost Estimator."""
    print("=" * 60)
    print("EXERCISE 4: LLM Cost Estimator")
    print("=" * 60)

    # Test case 1: Basic cost estimation
    result1 = estimate_llm_costs(
        requests_per_day=5_000,
        avg_input_tokens=1_500,
        avg_output_tokens=300,
        model="claude-sonnet",
    )
    assert result1 is not None, "Should return a CostProjection"
    assert result1.base_monthly_cost > 0, "Base cost should be positive"
    assert result1.base_annual_cost == result1.base_monthly_cost * 12, \
        "Annual should be 12x monthly"
    # Verify math: 5000 * 30 = 150K requests/month
    # Input: 150K * 1500 = 225M tokens * $3/1M = $675
    # Output: 150K * 300 = 45M tokens * $15/1M = $675
    # Total: $1350/month
    assert abs(result1.base_monthly_cost - 1350.0) < 1.0, \
        f"Expected ~$1350, got ${result1.base_monthly_cost:.2f}"
    print(f"  Test 1 PASSED: base=${result1.base_monthly_cost:.2f}/mo")

    # Test case 2: With caching optimization
    result2 = estimate_llm_costs(
        requests_per_day=5_000,
        avg_input_tokens=1_500,
        avg_output_tokens=300,
        model="claude-sonnet",
        cache_hit_rate=0.5,
    )
    assert result2.optimized_monthly_cost < result2.base_monthly_cost, \
        "Cached cost should be less than base"
    print(f"  Test 2 PASSED: optimized=${result2.optimized_monthly_cost:.2f}/mo "
          f"(base=${result2.base_monthly_cost:.2f})")

    # Test case 3: Tier comparison
    result3 = estimate_llm_costs(
        requests_per_day=1_000,
        avg_input_tokens=500,
        avg_output_tokens=200,
        model="gpt-4o",
    )
    assert len(result3.tier_comparison) == len(MODEL_PRICING), \
        "Should compare all model tiers"
    tier_names = [t.model_name for t in result3.tier_comparison]
    assert "claude-haiku" in tier_names, "Should include Haiku in comparison"
    print(f"  Test 3 PASSED: {len(result3.tier_comparison)} tiers compared")

    # Test case 4: Invalid model
    try:
        estimate_llm_costs(100, 500, 200, "nonexistent-model")
        assert False, "Should raise ValueError for unknown model"
    except ValueError:
        print(f"  Test 4 PASSED: ValueError raised for unknown model")

    print()


def test_exercise_5():
    """Test the AI Evaluation Harness."""
    print("=" * 60)
    print("EXERCISE 5: AI Evaluation Harness")
    print("=" * 60)

    # Test fuzzy_match_score
    assert abs(fuzzy_match_score("hello world", "hello world") - 1.0) < 0.01, \
        "Identical strings should score 1.0"
    assert fuzzy_match_score("hello", "goodbye") < 0.5, \
        "Different strings should score low"
    assert fuzzy_match_score("", "") == 1.0, \
        "Empty strings should score 1.0"
    print(f"  Fuzzy match tests PASSED")

    # Test run_evaluation
    test_cases = [
        EvalTestCase("What is 2+2?", "4", "4"),
        EvalTestCase("Capital of France?", "Paris", "paris"),
        EvalTestCase("Explain gravity", "Gravity is a fundamental force",
                     "Gravity pulls objects together"),
        EvalTestCase("What color is the sky?", "Blue", "The sky is blue"),
        EvalTestCase("Wrong answer test", "correct answer",
                     "completely wrong response here"),
    ]

    report = run_evaluation(test_cases, pass_threshold=0.5)
    assert report is not None, "Should return an EvalReport"
    assert report.total_cases == 5, "Should have 5 cases"
    assert report.exact_match_rate >= 0.0, "Exact match rate should be >= 0"
    assert 0.0 <= report.avg_fuzzy_score <= 1.0, "Avg fuzzy should be 0-1"
    assert report.pass_count + report.fail_count == report.total_cases
    print(f"  Eval report: {report.pass_count}/{report.total_cases} passed, "
          f"exact_match={report.exact_match_rate:.1%}, "
          f"fuzzy={report.avg_fuzzy_score:.3f}")

    # Test empty input
    empty_report = run_evaluation([], pass_threshold=0.5)
    assert empty_report.total_cases == 0, "Empty input should give 0 cases"
    print(f"  Empty input test PASSED")

    print()


def test_exercise_6():
    """Test the Responsible AI Checklist Generator."""
    print("=" * 60)
    print("EXERCISE 6: Responsible AI Checklist Generator")
    print("=" * 60)

    # Test case 1: Healthcare, regulated, API provider
    result1 = generate_ai_checklist(
        industry="healthcare",
        data_sensitivity=DataSensitivity.REGULATED,
        deployment_model="api_provider",
    )
    assert result1 is not None, "Should return an AIChecklist"
    assert len(result1.required_items) > len(UNIVERSAL_REQUIRED), \
        "Healthcare should add items beyond universal"
    required_texts = [item.item for item in result1.required_items]
    assert any("HIPAA" in t for t in required_texts), \
        "Healthcare should include HIPAA requirement"
    assert result1.total_items == (
        len(result1.required_items) +
        len(result1.recommended_items) +
        len(result1.nice_to_have_items)
    ), "Total should sum all lists"
    print(f"  Test 1 PASSED: {result1.total_items} total items "
          f"({len(result1.required_items)} required)")

    # Test case 2: Retail, internal data, self-hosted
    result2 = generate_ai_checklist(
        industry="retail",
        data_sensitivity=DataSensitivity.INTERNAL,
        deployment_model="self_hosted",
    )
    assert len(result2.required_items) >= len(UNIVERSAL_REQUIRED), \
        "Should have at least universal required items"
    print(f"  Test 2 PASSED: {result2.total_items} total items "
          f"({len(result2.required_items)} required)")

    # Test case 3: Unknown industry, public data
    result3 = generate_ai_checklist(
        industry="unknown",
        data_sensitivity=DataSensitivity.PUBLIC,
        deployment_model="managed_cloud",
    )
    assert len(result3.required_items) >= len(UNIVERSAL_REQUIRED), \
        "Unknown industry should still have universal items"
    print(f"  Test 3 PASSED: Unknown industry handled, "
          f"{result3.total_items} items")

    print()


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("AI/ML Solutions Engineering -- Exercises")
    print("=" * 60)
    print()

    exercises = [
        ("Exercise 1: AI Use Case Evaluator", test_exercise_1),
        ("Exercise 2: AI Expectation Setter", test_exercise_2),
        ("Exercise 3: RAG Architecture Designer", test_exercise_3),
        ("Exercise 4: LLM Cost Estimator", test_exercise_4),
        ("Exercise 5: AI Evaluation Harness", test_exercise_5),
        ("Exercise 6: Responsible AI Checklist Generator", test_exercise_6),
    ]

    passed = 0
    failed = 0

    for name, test_fn in exercises:
        try:
            test_fn()
            passed += 1
        except (AssertionError, TypeError, AttributeError, ValueError) as e:
            print(f"  FAILED: {name}")
            print(f"    Error: {e}")
            failed += 1
        except Exception as e:
            print(f"  FAILED: {name}")
            print(f"    Unexpected error: {type(e).__name__}: {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed}/{passed + failed} exercises passed")
    if failed > 0:
        print(f"  {failed} exercise(s) need implementation -- see TODO comments")
    print()
