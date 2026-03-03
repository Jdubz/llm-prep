"""
AI/ML Solutions Engineering -- Complete, Runnable Patterns

These examples demonstrate production-ready AI/ML solutions engineering tools:
use case scoring, RAG architecture design, cost modeling, evaluation harnesses,
and AI readiness assessments. Each function is self-contained with inline
comments explaining the concepts.

Run this file directly to see all examples in action:
    python examples.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Data models used across examples
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
    REGULATED = "regulated"


class Priority(Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    NICE_TO_HAVE = "nice_to_have"


@dataclass
class UseCase:
    description: str
    data_type: str
    volume: int
    error_tolerance: float
    latency_requirement: str
    compliance_needs: list[str]
    has_labeled_data: bool
    labeled_data_count: int


@dataclass
class UseCaseAssessment:
    overall_score: float
    data_quality_score: float
    measurability_score: float
    error_tolerance_score: float
    volume_score: float
    recommended_approach: AIApproach
    risk_factors: list[str]
    rationale: str


@dataclass
class RAGComponent:
    component_type: str
    name: str
    justification: str


@dataclass
class RAGDesign:
    components: list[RAGComponent]
    mermaid_diagram: str
    estimated_monthly_cost: float
    key_risks: list[str]
    recommended_chunk_strategy: str
    recommended_chunk_size: int


@dataclass
class ModelTierCost:
    tier_name: str
    model_name: str
    monthly_cost: float
    annual_cost: float
    input_cost: float
    output_cost: float


@dataclass
class CostProjection:
    base_monthly_cost: float
    base_annual_cost: float
    optimized_monthly_cost: float
    optimized_annual_cost: float
    savings_breakdown: dict[str, float]
    tier_comparison: list[ModelTierCost]
    assumptions: list[str]


@dataclass
class EvalTestCase:
    input_text: str
    expected_output: str
    actual_output: str


@dataclass
class EvalCaseResult:
    test_case: EvalTestCase
    exact_match: bool
    fuzzy_score: float
    length_ratio: float
    passed: bool


@dataclass
class EvalReport:
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
    category: str
    item: str
    priority: Priority
    rationale: str


@dataclass
class ReadinessReport:
    customer_name: str
    overall_level: int
    overall_label: str
    data_score: float
    capability_score: float
    org_score: float
    gaps: list[str]
    recommendations: list[str]
    checklist: list[ChecklistItem]


# ---------------------------------------------------------------------------
# 1. AI USE CASE SCORING
# ---------------------------------------------------------------------------
# A complete use case evaluation engine that scores AI readiness across
# multiple dimensions and recommends the best approach.

def score_data_quality(data_type: str, has_labeled_data: bool,
                       labeled_data_count: int) -> float:
    """Score data quality based on type and labeling status.

    Data type matters because text is the most accessible for LLMs,
    tabular data works well for classification, images need specialized
    models, and mixed data adds complexity.
    """
    # Base score by data type
    type_scores = {
        "text": 0.8,
        "tabular": 0.9,
        "image": 0.7,
        "mixed": 0.6,
    }
    score = type_scores.get(data_type, 0.5)

    # Bonus for labeled data
    if has_labeled_data:
        if labeled_data_count >= 10_000:
            score = min(1.0, score + 0.15)
        elif labeled_data_count >= 1_000:
            score = min(1.0, score + 0.1)
        elif labeled_data_count >= 100:
            score = min(1.0, score + 0.05)
    else:
        # Penalize missing labels -- less impactful for RAG use cases
        score = max(0.0, score - 0.1)

    return round(score, 2)


def score_measurability(error_tolerance: float,
                        compliance_needs: list[str]) -> float:
    """Score how measurable success is.

    Higher error tolerance means it is easier to show meaningful results
    in a POC. Compliance needs actually help measurability because
    regulated domains have well-defined success criteria.
    """
    score = 0.5 + (error_tolerance * 0.5)

    # Compliance adds structure to success criteria
    if compliance_needs:
        score = min(1.0, score + 0.1)

    return round(score, 2)


def score_volume(volume: int) -> float:
    """Score based on data volume.

    AI systems need enough data to be useful. Too little data means
    the system cannot generalize. Very high volume means high ROI
    potential from automation.
    """
    if volume < 100:
        return 0.3
    elif volume < 1_000:
        return 0.5
    elif volume < 10_000:
        return 0.7
    elif volume < 100_000:
        return 0.9
    else:
        return 1.0


def recommend_approach(
    overall_score: float,
    data_type: str,
    volume: int,
    has_labeled_data: bool,
    labeled_data_count: int,
    error_tolerance: float,
    latency_requirement: str,
) -> AIApproach:
    """Decide which AI approach to recommend based on use case characteristics.

    This implements the decision tree from 01-ai-ml-discovery-and-use-cases.md.
    The order of checks matters -- earlier checks take priority.
    """
    # Not suitable: overall score too low
    if overall_score < 0.4:
        return AIApproach.NOT_SUITABLE

    # Fine-tuning: sufficient labeled data
    if has_labeled_data and labeled_data_count >= 5_000:
        return AIApproach.FINE_TUNING

    # RAG: text data with reasonable volume
    if data_type == "text" and volume >= 100:
        return AIApproach.RAG

    # Classification: tabular data
    if data_type == "tabular":
        return AIApproach.CLASSIFICATION

    # Prompt engineering: flexible requirements
    if error_tolerance >= 0.3 and latency_requirement != "real_time":
        return AIApproach.PROMPT_ENGINEERING

    # Default to RAG as the most versatile approach
    return AIApproach.RAG


def identify_risks(use_case: UseCase) -> list[str]:
    """Identify risk factors for an AI use case."""
    risks = []

    if not use_case.has_labeled_data:
        risks.append("No labeled data -- evaluation and fine-tuning will require "
                      "manual labeling effort")

    if use_case.volume < 100:
        risks.append(f"Low data volume ({use_case.volume} records) -- "
                      "insufficient for reliable AI performance")

    if use_case.error_tolerance == 0.0:
        risks.append("Zero error tolerance -- AI systems are probabilistic "
                      "and cannot guarantee zero errors")

    if use_case.compliance_needs and use_case.latency_requirement == "real_time":
        risks.append("Compliance requirements with real-time latency may limit "
                      "model and hosting choices")

    if use_case.data_type == "mixed":
        risks.append("Mixed data types increase pipeline complexity and "
                      "require multiple processing approaches")

    if len(use_case.compliance_needs) >= 2:
        risks.append(f"Multiple compliance requirements "
                      f"({', '.join(use_case.compliance_needs)}) narrow "
                      f"the set of viable solutions significantly")

    return risks


def evaluate_use_case(use_case: UseCase) -> UseCaseAssessment:
    """Full use case evaluation pipeline.

    This is the complete implementation that exercises.py Exercise 1 asks
    you to build. It scores each dimension, selects an approach, and
    identifies risks.
    """
    # Score each dimension
    dq = score_data_quality(
        use_case.data_type, use_case.has_labeled_data, use_case.labeled_data_count
    )
    ms = score_measurability(use_case.error_tolerance, use_case.compliance_needs)
    et = use_case.error_tolerance  # Direct mapping
    vs = score_volume(use_case.volume)

    # Weighted overall score
    overall = dq * 0.35 + ms * 0.2 + et * 0.2 + vs * 0.25
    overall = round(overall, 3)

    # Recommend approach
    approach = recommend_approach(
        overall, use_case.data_type, use_case.volume,
        use_case.has_labeled_data, use_case.labeled_data_count,
        use_case.error_tolerance, use_case.latency_requirement,
    )

    # Identify risks
    risks = identify_risks(use_case)

    # Build rationale
    rationale_parts = [
        f"Overall readiness score: {overall:.2f}/1.00.",
        f"Data quality ({dq:.2f}): {use_case.data_type} data "
        f"{'with' if use_case.has_labeled_data else 'without'} labels.",
        f"Volume ({vs:.2f}): {use_case.volume:,} records.",
        f"Recommended approach: {approach.value}.",
    ]
    if risks:
        rationale_parts.append(f"Key risks: {'; '.join(risks[:2])}.")
    rationale = " ".join(rationale_parts)

    return UseCaseAssessment(
        overall_score=overall,
        data_quality_score=dq,
        measurability_score=ms,
        error_tolerance_score=et,
        volume_score=vs,
        recommended_approach=approach,
        risk_factors=risks,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# 2. RAG ARCHITECTURE DESIGNER
# ---------------------------------------------------------------------------
# A component selection tool that takes customer requirements and produces
# a complete RAG architecture with justifications and a Mermaid diagram.

@dataclass
class CustomerRequirements:
    data_types: list[str]
    document_count: int
    avg_document_pages: int
    queries_per_day: int
    latency_target: str
    compliance: list[str]
    existing_cloud: str
    team_size: str
    budget: str


def select_embedding_model(req: CustomerRequirements) -> RAGComponent:
    """Select an embedding model based on compliance and budget."""
    if any(c in req.compliance for c in ["HIPAA", "FedRAMP"]):
        if req.existing_cloud == "azure":
            return RAGComponent(
                "embedding_model",
                "Azure OpenAI text-embedding-3-large",
                "HIPAA/FedRAMP compliance requires cloud-provider hosted "
                "embeddings. Azure selected based on existing cloud relationship."
            )
        else:
            return RAGComponent(
                "embedding_model",
                "AWS Bedrock Titan Embeddings",
                "HIPAA/FedRAMP compliance requires cloud-provider hosted "
                "embeddings. AWS Bedrock selected for data residency."
            )
    elif req.budget == "low":
        return RAGComponent(
            "embedding_model",
            "text-embedding-3-small",
            "Budget-optimized choice at $0.02/1M tokens. Sufficient quality "
            "for most RAG use cases with 1536 dimensions."
        )
    else:
        return RAGComponent(
            "embedding_model",
            "text-embedding-3-large",
            "Best quality OpenAI embedding at $0.13/1M tokens. 3072 dimensions "
            "for maximum retrieval accuracy."
        )


def select_vector_db(req: CustomerRequirements) -> RAGComponent:
    """Select a vector database based on scale, cloud, and team size."""
    if req.existing_cloud == "azure" and req.compliance:
        return RAGComponent(
            "vector_db",
            "Azure AI Search",
            "Integrated with Azure for compliance. Supports hybrid search "
            "(keyword + semantic). Managed service reduces operational burden."
        )
    elif req.existing_cloud == "aws" and req.compliance:
        return RAGComponent(
            "vector_db",
            "Amazon OpenSearch Serverless",
            "AWS-native for compliance and data residency. Serverless model "
            "scales automatically. Supports vector and keyword search."
        )
    elif req.document_count < 100_000 and req.team_size == "small":
        return RAGComponent(
            "vector_db",
            "Pinecone",
            "Fully managed, minimal operational overhead. Ideal for small "
            "teams. Scales to millions of vectors without infrastructure work."
        )
    elif req.document_count >= 1_000_000:
        return RAGComponent(
            "vector_db",
            "Qdrant",
            "High-performance Rust-based engine. Advanced filtering "
            "capabilities. Handles billion-scale vector collections efficiently."
        )
    else:
        return RAGComponent(
            "vector_db",
            "pgvector (PostgreSQL extension)",
            "Leverages existing PostgreSQL infrastructure. Lowest operational "
            "overhead for teams already running Postgres. Good for <1M vectors."
        )


def select_llm(req: CustomerRequirements) -> RAGComponent:
    """Select the generation LLM based on compliance and budget."""
    if "FedRAMP" in req.compliance:
        return RAGComponent(
            "llm",
            "Azure OpenAI GPT-4o",
            "FedRAMP authorized through Azure Government. Required for "
            "federal workloads."
        )
    elif "HIPAA" in req.compliance:
        if req.existing_cloud == "azure":
            return RAGComponent(
                "llm",
                "Azure OpenAI GPT-4o",
                "HIPAA BAA available through Azure OpenAI. Data stays in "
                "customer's Azure tenant."
            )
        else:
            return RAGComponent(
                "llm",
                "AWS Bedrock Claude Sonnet",
                "HIPAA BAA available through AWS Bedrock. Data stays in "
                "customer's AWS account."
            )
    elif req.budget == "low":
        return RAGComponent(
            "llm",
            "Claude Haiku",
            "Best quality-to-cost ratio for RAG generation. $0.25/$1.25 per "
            "1M input/output tokens. Fast response times (<500ms TTFB)."
        )
    else:
        return RAGComponent(
            "llm",
            "Claude Sonnet",
            "Best balance of quality and cost for RAG. Excellent at following "
            "instructions and citing sources. $3/$15 per 1M input/output tokens."
        )


def select_orchestration(req: CustomerRequirements) -> RAGComponent:
    """Select an orchestration framework based on team size."""
    if req.team_size == "small":
        return RAGComponent(
            "orchestration",
            "LlamaIndex",
            "Purpose-built for RAG with the fastest time-to-working-prototype. "
            "Excellent document ingestion and retrieval abstractions."
        )
    elif req.team_size == "large":
        return RAGComponent(
            "orchestration",
            "Custom code (Python)",
            "Maximum flexibility and maintainability for large teams. "
            "Avoids framework churn. Direct API calls to embedding and LLM providers."
        )
    else:
        return RAGComponent(
            "orchestration",
            "LangChain",
            "Broad integration ecosystem. Good for medium teams that need "
            "multiple data source connectors. Active community."
        )


def select_chunking(req: CustomerRequirements) -> tuple[str, int]:
    """Select a chunking strategy and size."""
    has_tables = "pdf" in req.data_types or "csv" in req.data_types
    if has_tables:
        return "document-aware", 800
    elif req.avg_document_pages > 20:
        return "semantic", 600
    else:
        return "fixed-size (500 tokens, 100-token overlap)", 500


def estimate_rag_monthly_cost(
    req: CustomerRequirements,
    embedding_model: str,
    vector_db: str,
    llm: str,
) -> float:
    """Rough monthly cost estimate for a RAG system."""
    # Embedding cost (one-time, amortized over 12 months)
    # Assume ~500 tokens per page after chunking
    total_tokens = req.document_count * req.avg_document_pages * 500
    embedding_price_per_1m = 0.02 if "small" in embedding_model else 0.13
    embedding_monthly = (total_tokens * embedding_price_per_1m / 1_000_000) / 12

    # Vector DB hosting cost estimate
    if "Pinecone" in vector_db:
        vector_db_monthly = 70.0  # Starter plan
    elif "Azure" in vector_db:
        vector_db_monthly = 250.0  # Basic tier
    elif "OpenSearch" in vector_db:
        vector_db_monthly = 200.0  # Serverless estimate
    elif "pgvector" in vector_db:
        vector_db_monthly = 50.0  # Existing Postgres, minimal extra cost
    elif "Qdrant" in vector_db:
        vector_db_monthly = 150.0  # Cloud managed
    else:
        vector_db_monthly = 100.0

    # LLM inference cost
    # Assume 1500 input tokens + 300 output tokens per query
    monthly_queries = req.queries_per_day * 30
    if "Haiku" in llm or "haiku" in llm:
        input_price, output_price = 0.25, 1.25
    elif "Sonnet" in llm or "sonnet" in llm:
        input_price, output_price = 3.00, 15.00
    elif "GPT-4o" in llm or "gpt-4o" in llm:
        input_price, output_price = 2.50, 10.00
    else:
        input_price, output_price = 3.00, 15.00

    llm_input_cost = monthly_queries * 1500 * input_price / 1_000_000
    llm_output_cost = monthly_queries * 300 * output_price / 1_000_000
    llm_monthly = llm_input_cost + llm_output_cost

    total = embedding_monthly + vector_db_monthly + llm_monthly
    return round(total, 2)


def generate_mermaid_diagram(components: list[RAGComponent]) -> str:
    """Generate a Mermaid diagram for the RAG architecture."""
    # Extract component names for the diagram
    names = {c.component_type: c.name for c in components}

    embedding = names.get("embedding_model", "Embedding Model")
    vector_db = names.get("vector_db", "Vector Store")
    llm = names.get("llm", "LLM")
    orchestration = names.get("orchestration", "Orchestration")

    diagram = f"""graph TB
    subgraph "Data Ingestion Pipeline"
        A[Customer Documents] --> B[Document Processor]
        B --> C[Chunking Engine]
        C --> D["{embedding}"]
        D --> E[("{vector_db}")]
    end

    subgraph "Query Pipeline ({orchestration})"
        F[User Query] --> G[Query Embedding]
        G --> H[Vector Search]
        E --> H
        H --> I[Reranker]
        I --> J[Context Assembly]
        J --> K["{llm}"]
        F --> K
        K --> L[Response + Citations]
    end

    subgraph "Monitoring"
        K --> M[Logging & Tracing]
        L --> N[User Feedback]
        M --> O[Eval Dashboard]
        N --> O
    end"""

    return diagram


def design_rag_architecture(req: CustomerRequirements) -> RAGDesign:
    """Full RAG architecture design pipeline.

    This is the complete implementation that exercises.py Exercise 3 asks
    you to build.
    """
    # Select components
    embedding = select_embedding_model(req)
    vector_db = select_vector_db(req)
    llm = select_llm(req)
    orchestration = select_orchestration(req)
    components = [embedding, vector_db, llm, orchestration]

    # Select chunking strategy
    chunk_strategy, chunk_size = select_chunking(req)

    # Generate diagram
    diagram = generate_mermaid_diagram(components)

    # Estimate cost
    monthly_cost = estimate_rag_monthly_cost(
        req, embedding.name, vector_db.name, llm.name
    )

    # Identify risks
    risks = []
    if req.document_count > 100_000 and "pgvector" in vector_db.name:
        risks.append("pgvector may struggle at this scale -- consider Qdrant or Pinecone")
    if "pdf" in req.data_types:
        risks.append("PDF extraction quality varies -- budget time for document "
                      "processor evaluation")
    if req.latency_target == "real_time" and "Opus" in llm.name:
        risks.append("Real-time latency target may not be achievable with large models")
    if not req.compliance and req.budget == "low":
        risks.append("Low budget may require tradeoffs on retrieval quality -- "
                      "plan for iterative improvement")
    if req.team_size == "small" and req.document_count > 100_000:
        risks.append("Small team managing large document corpus -- consider "
                      "managed services to reduce operational burden")

    return RAGDesign(
        components=components,
        mermaid_diagram=diagram,
        estimated_monthly_cost=monthly_cost,
        key_risks=risks,
        recommended_chunk_strategy=chunk_strategy,
        recommended_chunk_size=chunk_size,
    )


# ---------------------------------------------------------------------------
# 3. TOKEN COST CALCULATOR
# ---------------------------------------------------------------------------
# A comprehensive cost modeling tool with optimization scenarios and
# multi-tier comparison.

MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {
        "input": 2.50, "output": 10.00,
        "cached_input": 1.25, "batch_input": 1.25, "batch_output": 5.00,
    },
    "gpt-4o-mini": {
        "input": 0.15, "output": 0.60,
        "cached_input": 0.075, "batch_input": 0.075, "batch_output": 0.30,
    },
    "claude-sonnet": {
        "input": 3.00, "output": 15.00,
        "cached_input": 0.30, "batch_input": 1.50, "batch_output": 7.50,
    },
    "claude-haiku": {
        "input": 0.25, "output": 1.25,
        "cached_input": 0.025, "batch_input": 0.125, "batch_output": 0.625,
    },
    "claude-opus": {
        "input": 15.00, "output": 75.00,
        "cached_input": 1.50, "batch_input": 7.50, "batch_output": 37.50,
    },
}


def calculate_base_cost(
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    pricing: dict[str, float],
) -> tuple[float, float]:
    """Calculate base monthly cost with no optimizations.

    Returns (input_cost, output_cost).
    """
    monthly_input_tokens = monthly_requests * avg_input_tokens
    monthly_output_tokens = monthly_requests * avg_output_tokens

    input_cost = monthly_input_tokens * (pricing["input"] / 1_000_000)
    output_cost = monthly_output_tokens * (pricing["output"] / 1_000_000)

    return input_cost, output_cost


def calculate_optimized_cost(
    monthly_requests: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    pricing: dict[str, float],
    cache_hit_rate: float,
    batch_percentage: float,
) -> tuple[float, dict[str, float]]:
    """Calculate optimized monthly cost with caching and batching.

    Returns (total_optimized_cost, savings_breakdown).
    """
    # Base cost for comparison
    base_input, base_output = calculate_base_cost(
        monthly_requests, avg_input_tokens, avg_output_tokens, pricing
    )
    base_total = base_input + base_output

    # Split requests into segments
    cached_requests = int(monthly_requests * cache_hit_rate)
    remaining = monthly_requests - cached_requests
    batched_requests = int(remaining * batch_percentage)
    standard_requests = remaining - batched_requests

    # Cached segment: cached input price, standard output price
    cached_input_cost = (
        cached_requests * avg_input_tokens *
        (pricing["cached_input"] / 1_000_000)
    )
    cached_output_cost = (
        cached_requests * avg_output_tokens *
        (pricing["output"] / 1_000_000)
    )

    # Batched segment: batch prices for both input and output
    batched_input_cost = (
        batched_requests * avg_input_tokens *
        (pricing["batch_input"] / 1_000_000)
    )
    batched_output_cost = (
        batched_requests * avg_output_tokens *
        (pricing["batch_output"] / 1_000_000)
    )

    # Standard segment: full prices
    standard_input_cost = (
        standard_requests * avg_input_tokens *
        (pricing["input"] / 1_000_000)
    )
    standard_output_cost = (
        standard_requests * avg_output_tokens *
        (pricing["output"] / 1_000_000)
    )

    total_optimized = (
        cached_input_cost + cached_output_cost +
        batched_input_cost + batched_output_cost +
        standard_input_cost + standard_output_cost
    )

    # Calculate savings breakdown
    # Caching savings: what we saved by using cached pricing on cached requests
    caching_savings = (
        cached_requests * avg_input_tokens *
        ((pricing["input"] - pricing["cached_input"]) / 1_000_000)
    )

    # Batching savings: what we saved by using batch pricing on batched requests
    batching_savings = (
        batched_requests * avg_input_tokens *
        ((pricing["input"] - pricing["batch_input"]) / 1_000_000)
    ) + (
        batched_requests * avg_output_tokens *
        ((pricing["output"] - pricing["batch_output"]) / 1_000_000)
    )

    savings_breakdown = {
        "caching_savings": round(caching_savings, 2),
        "batching_savings": round(batching_savings, 2),
        "total_savings": round(base_total - total_optimized, 2),
    }

    return round(total_optimized, 2), savings_breakdown


def project_costs(
    requests_per_day: int,
    avg_input_tokens: int,
    avg_output_tokens: int,
    model: str,
    cache_hit_rate: float = 0.0,
    batch_percentage: float = 0.0,
) -> CostProjection:
    """Full cost projection with tier comparison.

    This is the complete implementation that exercises.py Exercise 4 asks
    you to build.
    """
    if model not in MODEL_PRICING:
        raise ValueError(
            f"Unknown model '{model}'. Available: {list(MODEL_PRICING.keys())}"
        )

    pricing = MODEL_PRICING[model]
    monthly_requests = requests_per_day * 30

    # Base cost
    base_input, base_output = calculate_base_cost(
        monthly_requests, avg_input_tokens, avg_output_tokens, pricing
    )
    base_monthly = round(base_input + base_output, 2)
    base_annual = round(base_monthly * 12, 2)

    # Optimized cost
    optimized_monthly, savings = calculate_optimized_cost(
        monthly_requests, avg_input_tokens, avg_output_tokens,
        pricing, cache_hit_rate, batch_percentage,
    )
    optimized_annual = round(optimized_monthly * 12, 2)

    # Tier comparison: calculate base cost for each model
    tier_comparison = []
    for tier_model, tier_pricing in MODEL_PRICING.items():
        tier_input, tier_output = calculate_base_cost(
            monthly_requests, avg_input_tokens, avg_output_tokens, tier_pricing
        )
        tier_monthly = round(tier_input + tier_output, 2)
        tier_comparison.append(ModelTierCost(
            tier_name=tier_model,
            model_name=tier_model,
            monthly_cost=tier_monthly,
            annual_cost=round(tier_monthly * 12, 2),
            input_cost=round(tier_input, 2),
            output_cost=round(tier_output, 2),
        ))

    # Sort tiers by monthly cost
    tier_comparison.sort(key=lambda t: t.monthly_cost)

    assumptions = [
        f"Requests per day: {requests_per_day:,}",
        f"Monthly requests: {monthly_requests:,}",
        f"Avg input tokens: {avg_input_tokens:,}",
        f"Avg output tokens: {avg_output_tokens:,}",
        f"Primary model: {model}",
        f"Cache hit rate: {cache_hit_rate:.0%}",
        f"Batch percentage: {batch_percentage:.0%}",
    ]

    return CostProjection(
        base_monthly_cost=base_monthly,
        base_annual_cost=base_annual,
        optimized_monthly_cost=optimized_monthly,
        optimized_annual_cost=optimized_annual,
        savings_breakdown=savings,
        tier_comparison=tier_comparison,
        assumptions=assumptions,
    )


# ---------------------------------------------------------------------------
# 4. EVAL HARNESS
# ---------------------------------------------------------------------------
# A complete evaluation pipeline with multiple metrics for assessing
# AI system output quality.

def fuzzy_match_score(s1: str, s2: str) -> float:
    """Compute bigram-based Jaccard similarity between two strings.

    This is a simple, fast approximation of string similarity. Production
    systems would use Levenshtein distance or embedding similarity.
    """
    # Normalize
    s1 = s1.strip().lower()
    s2 = s2.strip().lower()

    # Edge cases
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0

    # Build bigram sets
    bigrams1 = {s1[i:i+2] for i in range(len(s1) - 1)}
    bigrams2 = {s2[i:i+2] for i in range(len(s2) - 1)}

    # Handle single-character strings (no bigrams)
    if not bigrams1 and not bigrams2:
        return 1.0 if s1 == s2 else 0.0
    if not bigrams1 or not bigrams2:
        return 0.0

    # Jaccard similarity
    intersection = bigrams1 & bigrams2
    union = bigrams1 | bigrams2

    return len(intersection) / len(union) if union else 0.0


def evaluate_single_case(
    test_case: EvalTestCase,
    pass_threshold: float,
) -> EvalCaseResult:
    """Evaluate a single test case across all metrics."""
    expected = test_case.expected_output.strip().lower()
    actual = test_case.actual_output.strip().lower()

    # Exact match (case-insensitive)
    exact = expected == actual

    # Fuzzy match
    fuzzy = fuzzy_match_score(test_case.expected_output, test_case.actual_output)

    # Length ratio
    if not expected and not actual:
        length_ratio = 1.0
    elif not expected:
        length_ratio = float("inf")
    else:
        length_ratio = len(actual) / len(expected)

    # Pass/fail
    passed = exact or fuzzy >= pass_threshold

    return EvalCaseResult(
        test_case=test_case,
        exact_match=exact,
        fuzzy_score=round(fuzzy, 4),
        length_ratio=round(length_ratio, 4),
        passed=passed,
    )


def run_evaluation(
    test_cases: list[EvalTestCase],
    pass_threshold: float = 0.7,
) -> EvalReport:
    """Run full evaluation and generate report.

    This is the complete implementation that exercises.py Exercise 5 asks
    you to build.
    """
    if not test_cases:
        return EvalReport(
            total_cases=0,
            pass_count=0,
            fail_count=0,
            exact_match_rate=0.0,
            avg_fuzzy_score=0.0,
            avg_length_ratio=0.0,
            case_results=[],
            summary="Evaluation: 0/0 passed. No test cases provided.",
        )

    # Evaluate each case
    results = [evaluate_single_case(tc, pass_threshold) for tc in test_cases]

    # Aggregate
    total = len(results)
    pass_count = sum(1 for r in results if r.passed)
    fail_count = total - pass_count
    exact_matches = sum(1 for r in results if r.exact_match)
    exact_match_rate = exact_matches / total

    avg_fuzzy = sum(r.fuzzy_score for r in results) / total

    # Exclude infinite length ratios from the average
    finite_ratios = [r.length_ratio for r in results
                     if r.length_ratio != float("inf")]
    avg_length_ratio = (
        sum(finite_ratios) / len(finite_ratios) if finite_ratios else 0.0
    )

    pass_rate = pass_count / total
    summary = (
        f"Evaluation: {pass_count}/{total} passed ({pass_rate:.1%}). "
        f"Exact match: {exact_match_rate:.1%}. Avg fuzzy: {avg_fuzzy:.3f}."
    )

    return EvalReport(
        total_cases=total,
        pass_count=pass_count,
        fail_count=fail_count,
        exact_match_rate=round(exact_match_rate, 4),
        avg_fuzzy_score=round(avg_fuzzy, 4),
        avg_length_ratio=round(avg_length_ratio, 4),
        case_results=results,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# 5. AI READINESS ASSESSMENT
# ---------------------------------------------------------------------------
# A full customer AI-readiness report generator that evaluates maturity
# across dimensions and produces actionable recommendations.

MATURITY_LABELS = {
    1: "No AI",
    2: "AI Curious",
    3: "AI Piloting",
    4: "AI Operational",
    5: "AI Native",
}

INDUSTRY_REQUIREMENTS: dict[str, list[str]] = {
    "healthcare": [
        "HIPAA Business Associate Agreement with all AI vendors",
        "PHI detection and redaction pipeline",
        "Clinical validation workflow for AI outputs",
        "Audit logging for all AI-accessed patient data",
    ],
    "financial_services": [
        "Model explainability documentation (SR 11-7 compliance)",
        "Bias testing across protected classes",
        "SOX-compliant audit trail for AI-influenced decisions",
        "PCI DSS compliance for payment data handling",
    ],
    "legal": [
        "Source citation for all AI-generated content",
        "Hallucination detection and flagging system",
        "Attorney review requirement for all AI outputs",
        "Client privilege protection in data handling",
    ],
    "government": [
        "FedRAMP authorized infrastructure for all AI components",
        "FISMA compliance assessment and authorization",
        "US data residency for all processing and storage",
        "Section 508 accessibility compliance",
    ],
}


def assess_data_readiness(answers: dict[str, int]) -> tuple[float, list[str]]:
    """Assess data readiness from questionnaire answers (1-5 scale).

    Expected keys: data_warehouse, data_documentation, data_quality_monitoring,
    data_access_speed, data_governance.
    """
    keys = ["data_warehouse", "data_documentation", "data_quality_monitoring",
            "data_access_speed", "data_governance"]
    scores = [answers.get(k, 1) for k in keys]
    avg = sum(scores) / len(scores)

    gaps = []
    if answers.get("data_warehouse", 1) < 3:
        gaps.append("No centralized data warehouse -- foundation for AI is missing")
    if answers.get("data_documentation", 1) < 3:
        gaps.append("Data documentation is insufficient -- AI systems need documented schemas")
    if answers.get("data_quality_monitoring", 1) < 3:
        gaps.append("No automated data quality monitoring -- AI output quality depends on input quality")
    if answers.get("data_access_speed", 1) < 3:
        gaps.append("Slow data access processes will bottleneck AI development")
    if answers.get("data_governance", 1) < 3:
        gaps.append("Data governance gaps may block AI deployment in regulated use cases")

    return avg, gaps


def assess_ai_capability(answers: dict[str, int]) -> tuple[float, list[str]]:
    """Assess AI/ML capability from questionnaire answers (1-5 scale).

    Expected keys: ml_staff, production_models, eval_framework,
    model_monitoring, training_capability.
    """
    keys = ["ml_staff", "production_models", "eval_framework",
            "model_monitoring", "training_capability"]
    scores = [answers.get(k, 1) for k in keys]
    avg = sum(scores) / len(scores)

    gaps = []
    if answers.get("ml_staff", 1) < 3:
        gaps.append("No dedicated ML staff -- consider managed AI services or consulting")
    if answers.get("eval_framework", 1) < 3:
        gaps.append("No evaluation framework -- cannot measure AI quality without one")
    if answers.get("model_monitoring", 1) < 3:
        gaps.append("No model monitoring -- production AI without monitoring is risky")

    return avg, gaps


def assess_org_readiness(answers: dict[str, int]) -> tuple[float, list[str]]:
    """Assess organizational readiness from questionnaire answers (1-5 scale).

    Expected keys: executive_sponsorship, ai_budget, business_engagement,
    vendor_evaluation_process, ai_ethics_policy.
    """
    keys = ["executive_sponsorship", "ai_budget", "business_engagement",
            "vendor_evaluation_process", "ai_ethics_policy"]
    scores = [answers.get(k, 1) for k in keys]
    avg = sum(scores) / len(scores)

    gaps = []
    if answers.get("executive_sponsorship", 1) < 3:
        gaps.append("Lack of executive sponsorship -- AI projects without it stall")
    if answers.get("ai_budget", 1) < 3:
        gaps.append("No dedicated AI budget -- projects compete with other priorities")
    if answers.get("business_engagement", 1) < 3:
        gaps.append("Business stakeholders not engaged -- AI projects become IT-only initiatives")

    return avg, gaps


def determine_maturity_level(data_avg: float, capability_avg: float,
                             org_avg: float) -> int:
    """Determine overall maturity level from dimension averages."""
    overall_avg = (data_avg + capability_avg + org_avg) / 3

    if overall_avg < 1.5:
        return 1
    elif overall_avg < 2.5:
        return 2
    elif overall_avg < 3.5:
        return 3
    elif overall_avg < 4.5:
        return 4
    else:
        return 5


def build_recommendations(level: int, gaps: list[str],
                          industry: str) -> list[str]:
    """Build recommendations based on maturity level and gaps."""
    recommendations = []

    if level <= 2:
        recommendations.extend([
            "Invest in data infrastructure before pursuing AI projects",
            "Start with pre-built AI features in existing SaaS tools",
            "Run an AI literacy workshop for technical and business teams",
        ])
    elif level == 3:
        recommendations.extend([
            "Focus on one high-value pilot use case with clear success metrics",
            "Build an evaluation framework for measuring AI output quality",
            "Establish a feedback loop between domain experts and the AI system",
        ])
    elif level == 4:
        recommendations.extend([
            "Standardize AI development practices across teams (MLOps)",
            "Implement automated evaluation and regression testing in CI/CD",
            "Build a cost monitoring and optimization pipeline",
        ])
    else:
        recommendations.extend([
            "Focus on cost optimization and model tiering",
            "Invest in proprietary evaluation datasets as competitive moat",
            "Explore fine-tuning and custom models for differentiation",
        ])

    # Industry-specific recommendations
    if industry in INDUSTRY_REQUIREMENTS:
        recommendations.append(
            f"Address {industry}-specific compliance requirements: "
            f"{', '.join(INDUSTRY_REQUIREMENTS[industry][:2])}"
        )

    # Gap-specific recommendations
    for gap in gaps[:3]:
        recommendations.append(f"Address gap: {gap}")

    return recommendations


def build_checklist(level: int, industry: str) -> list[ChecklistItem]:
    """Build a prioritized checklist based on maturity and industry."""
    items = []

    # Universal required items
    universal = [
        ("Operations", "Set up logging and monitoring for AI interactions"),
        ("Operations", "Pin model versions to prevent unexpected changes"),
        ("Model Safety", "Implement input validation and output guardrails"),
        ("Model Safety", "Build evaluation suite with 50+ test cases"),
        ("Data Privacy", "Implement PII detection and redaction"),
        ("Compliance", "Disclose AI usage to end users"),
    ]
    for category, item in universal:
        items.append(ChecklistItem(category, item, Priority.REQUIRED,
                                   "Universal requirement for production AI"))

    # Industry-specific items
    if industry in INDUSTRY_REQUIREMENTS:
        for req in INDUSTRY_REQUIREMENTS[industry]:
            items.append(ChecklistItem(
                "Compliance", req, Priority.REQUIRED,
                f"Required for {industry} industry compliance"
            ))

    # Level-appropriate items
    if level >= 3:
        items.append(ChecklistItem(
            "Operations", "Implement automated regression testing",
            Priority.RECOMMENDED, "Catches quality degradation early"
        ))
        items.append(ChecklistItem(
            "Operations", "Set up cost monitoring and alerting",
            Priority.RECOMMENDED, "Prevents budget overruns"
        ))

    if level >= 4:
        items.append(ChecklistItem(
            "Operations", "Implement A/B testing for prompt variants",
            Priority.NICE_TO_HAVE, "Enables data-driven optimization"
        ))

    return items


def generate_readiness_report(
    customer_name: str,
    industry: str,
    data_answers: dict[str, int],
    capability_answers: dict[str, int],
    org_answers: dict[str, int],
) -> ReadinessReport:
    """Generate a complete AI readiness report.

    This brings together all assessment dimensions, gaps, recommendations,
    and a prioritized checklist into a single report.
    """
    # Assess each dimension
    data_avg, data_gaps = assess_data_readiness(data_answers)
    cap_avg, cap_gaps = assess_ai_capability(capability_answers)
    org_avg, org_gaps = assess_org_readiness(org_answers)

    # Combine gaps
    all_gaps = data_gaps + cap_gaps + org_gaps

    # Determine overall level
    level = determine_maturity_level(data_avg, cap_avg, org_avg)
    label = MATURITY_LABELS[level]

    # Build recommendations
    recommendations = build_recommendations(level, all_gaps, industry)

    # Build checklist
    checklist = build_checklist(level, industry)

    return ReadinessReport(
        customer_name=customer_name,
        overall_level=level,
        overall_label=label,
        data_score=round(data_avg, 2),
        capability_score=round(cap_avg, 2),
        org_score=round(org_avg, 2),
        gaps=all_gaps,
        recommendations=recommendations,
        checklist=checklist,
    )


def format_readiness_report(report: ReadinessReport) -> str:
    """Format a ReadinessReport as a human-readable string."""
    lines = [
        "=" * 60,
        "AI READINESS ASSESSMENT REPORT",
        "=" * 60,
        f"Customer: {report.customer_name}",
        f"Overall Maturity Level: {report.overall_level} -- {report.overall_label}",
        "",
        "DIMENSION SCORES:",
        f"  Data Foundation:         {report.data_score:.1f}/5.0",
        f"  AI/ML Capability:        {report.capability_score:.1f}/5.0",
        f"  Organizational Readiness: {report.org_score:.1f}/5.0",
    ]

    if report.gaps:
        lines.append("")
        lines.append("KEY GAPS:")
        for i, gap in enumerate(report.gaps, 1):
            lines.append(f"  {i}. {gap}")

    lines.append("")
    lines.append("RECOMMENDATIONS:")
    for i, rec in enumerate(report.recommendations, 1):
        lines.append(f"  {i}. {rec}")

    lines.append("")
    lines.append("CHECKLIST:")
    for item in report.checklist:
        priority_tag = f"[{item.priority.value.upper()}]"
        lines.append(f"  {priority_tag:16} {item.category}: {item.item}")

    lines.append("=" * 60)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main -- run all examples
# ---------------------------------------------------------------------------

def main():
    """Demonstrate all AI/ML solutions engineering examples."""

    # --- 1. AI Use Case Scoring ---
    print("\n" + "=" * 60)
    print("1. AI USE CASE SCORING")
    print("=" * 60)

    use_cases = [
        UseCase(
            "Answer questions from internal knowledge base",
            "text", 50_000, 0.15, "fast", ["SOC2"], False, 0,
        ),
        UseCase(
            "Classify customer tickets by department",
            "text", 200_000, 0.1, "real_time", [], True, 15_000,
        ),
        UseCase(
            "Predict rare equipment failures",
            "mixed", 50, 0.0, "real_time", ["HIPAA"], False, 0,
        ),
    ]

    for uc in use_cases:
        assessment = evaluate_use_case(uc)
        print(f"\n  Use case: {uc.description}")
        print(f"  Score: {assessment.overall_score:.2f} | "
              f"Approach: {assessment.recommended_approach.value}")
        print(f"  Rationale: {assessment.rationale[:120]}...")
        if assessment.risk_factors:
            print(f"  Top risk: {assessment.risk_factors[0]}")

    # --- 2. RAG Architecture Designer ---
    print("\n" + "=" * 60)
    print("2. RAG ARCHITECTURE DESIGNER")
    print("=" * 60)

    req = CustomerRequirements(
        data_types=["pdf", "docx", "html"],
        document_count=25_000,
        avg_document_pages=8,
        queries_per_day=2_000,
        latency_target="fast",
        compliance=["HIPAA"],
        existing_cloud="azure",
        team_size="medium",
        budget="medium",
    )

    design = design_rag_architecture(req)
    print(f"\n  Components selected:")
    for comp in design.components:
        print(f"    {comp.component_type}: {comp.name}")
        print(f"      Reason: {comp.justification[:80]}...")
    print(f"  Chunk strategy: {design.recommended_chunk_strategy} "
          f"({design.recommended_chunk_size} tokens)")
    print(f"  Estimated cost: ${design.estimated_monthly_cost:.2f}/month")
    if design.key_risks:
        print(f"  Key risks:")
        for risk in design.key_risks:
            print(f"    - {risk}")

    # --- 3. Token Cost Calculator ---
    print("\n" + "=" * 60)
    print("3. TOKEN COST CALCULATOR")
    print("=" * 60)

    projection = project_costs(
        requests_per_day=5_000,
        avg_input_tokens=1_500,
        avg_output_tokens=300,
        model="claude-sonnet",
        cache_hit_rate=0.5,
        batch_percentage=0.2,
    )

    print(f"\n  Assumptions:")
    for a in projection.assumptions:
        print(f"    {a}")
    print(f"\n  Base cost:      ${projection.base_monthly_cost:,.2f}/month "
          f"(${projection.base_annual_cost:,.2f}/year)")
    print(f"  Optimized cost: ${projection.optimized_monthly_cost:,.2f}/month "
          f"(${projection.optimized_annual_cost:,.2f}/year)")
    print(f"\n  Savings breakdown:")
    for opt_type, savings in projection.savings_breakdown.items():
        print(f"    {opt_type}: ${savings:,.2f}/month")
    print(f"\n  Tier comparison (monthly cost):")
    for tier in projection.tier_comparison:
        marker = " <-- selected" if tier.model_name == "claude-sonnet" else ""
        print(f"    {tier.model_name:20} ${tier.monthly_cost:>10,.2f}{marker}")

    # --- 4. Eval Harness ---
    print("\n" + "=" * 60)
    print("4. EVAL HARNESS")
    print("=" * 60)

    test_cases = [
        EvalTestCase(
            "What is the return policy?",
            "30-day return policy for unused items with receipt",
            "We offer a 30-day return policy for unused items. Bring your receipt.",
        ),
        EvalTestCase(
            "How do I track my order?",
            "Use the tracking link in your confirmation email",
            "Check the tracking link in your confirmation email.",
        ),
        EvalTestCase(
            "What payment methods do you accept?",
            "Visa, Mastercard, Amex, PayPal",
            "We accept all major credit cards and PayPal.",
        ),
        EvalTestCase(
            "Can I cancel my order?",
            "Cancel within 24 hours by contacting support",
            "You can cancel within 24 hours. Contact our support team.",
        ),
        EvalTestCase(
            "Do you ship internationally?",
            "Yes, we ship to 50+ countries with varying delivery times",
            "No, we only ship domestically.",
        ),
    ]

    report = run_evaluation(test_cases, pass_threshold=0.5)
    print(f"\n  {report.summary}")
    print(f"\n  Per-case results:")
    for i, result in enumerate(report.case_results, 1):
        status = "PASS" if result.passed else "FAIL"
        print(f"    [{status}] Case {i}: exact={result.exact_match}, "
              f"fuzzy={result.fuzzy_score:.3f}, "
              f"length_ratio={result.length_ratio:.2f}")

    # --- 5. AI Readiness Assessment ---
    print("\n" + "=" * 60)
    print("5. AI READINESS ASSESSMENT")
    print("=" * 60)

    readiness = generate_readiness_report(
        customer_name="Acme Healthcare Inc.",
        industry="healthcare",
        data_answers={
            "data_warehouse": 4,
            "data_documentation": 3,
            "data_quality_monitoring": 2,
            "data_access_speed": 3,
            "data_governance": 4,
        },
        capability_answers={
            "ml_staff": 2,
            "production_models": 1,
            "eval_framework": 1,
            "model_monitoring": 1,
            "training_capability": 1,
        },
        org_answers={
            "executive_sponsorship": 4,
            "ai_budget": 3,
            "business_engagement": 3,
            "vendor_evaluation_process": 2,
            "ai_ethics_policy": 2,
        },
    )

    print()
    print(format_readiness_report(readiness))


if __name__ == "__main__":
    main()
