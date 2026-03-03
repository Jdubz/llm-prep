"""
Module 02: Demos, POCs, and Technical Validation — Production-Ready Patterns

Complete, runnable examples demonstrating demo engineering, POC scoping,
objection handling, success criteria design, and environment preparation.
Each section is a self-contained implementation of a key concept.

No external dependencies required — pure Python implementations that model
the frameworks and decision-making patterns covered in the MD files.
"""

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# 1. DEMO NARRATIVE ENGINE
# ---------------------------------------------------------------------------
# Complete demo script generator with audience adaptation and timing.
# Implements the five-act narrative arc from 01-demo-engineering.md.

@dataclass
class Feature:
    """A product feature for demo planning."""
    name: str
    description: str
    pain_points_addressed: list[str]
    demo_time_minutes: int
    wow_factor: int  # 1-10
    complexity: str  # "simple", "moderate", "complex"


@dataclass
class Prospect:
    """Prospect profile for demo customization."""
    company_name: str
    industry: str
    role: str  # "executive", "architect", "developer", "end_user", "mixed"
    pain_points: list[str]
    current_tools: list[str]
    company_size: str


@dataclass
class DemoSegment:
    """A single segment in the demo."""
    pain_point: str
    feature: Feature
    talking_points: list[str]
    estimated_minutes: int
    audience_notes: str


@dataclass
class NarrativeDemo:
    """Complete demo script following the five-act structure."""
    hook: str
    context: str
    segments: list[DemoSegment]
    wow_moment: str
    close: str
    total_minutes: int
    audience_notes: str


# Audience-specific templates for talking points
AUDIENCE_TALKING_POINTS = {
    "executive": {
        "prefix": "Business outcome: ",
        "style": "ROI-focused, concise, outcome-driven",
        "verbs": ["saves", "reduces", "eliminates", "accelerates", "protects"],
    },
    "architect": {
        "prefix": "Architecture: ",
        "style": "Integration-focused, technical depth, scalability",
        "verbs": ["integrates", "scales", "handles", "processes", "connects"],
    },
    "developer": {
        "prefix": "Developer experience: ",
        "style": "Code-level, API-driven, hands-on",
        "verbs": ["exposes", "returns", "accepts", "implements", "wraps"],
    },
    "end_user": {
        "prefix": "Workflow: ",
        "style": "Task-oriented, UX-focused, step-by-step",
        "verbs": ["simplifies", "automates", "shows", "lets you", "guides"],
    },
    "mixed": {
        "prefix": "Value: ",
        "style": "Layered — business context first, then technical depth",
        "verbs": ["enables", "provides", "delivers", "supports", "ensures"],
    },
}

# Duration budgets by audience type (minutes)
AUDIENCE_DURATION = {
    "executive": 5,
    "architect": 25,
    "developer": 40,
    "end_user": 20,
    "mixed": 30,
}

# Time allocation across the five acts (as fractions of total)
ACT_ALLOCATION = {
    "hook": 0.05,
    "context": 0.10,
    "solution": 0.70,
    "wow": 0.10,
    "close": 0.05,
}

# Solution time split across segments (first gets 60%, second 25%, third 15%)
SEGMENT_SPLITS = [0.60, 0.25, 0.15]


def _rank_features_for_prospect(
    features: list[Feature],
    prospect: Prospect,
) -> list[tuple[Feature, list[str]]]:
    """
    Rank features by relevance to the prospect's pain points.

    Returns list of (feature, matched_pain_points) tuples, sorted by
    number of matches (desc) then wow_factor (desc).
    """
    ranked = []
    for feature in features:
        matched = [
            p for p in prospect.pain_points
            if p in feature.pain_points_addressed
        ]
        if matched:
            ranked.append((feature, matched))

    ranked.sort(key=lambda x: (len(x[1]), x[0].wow_factor), reverse=True)
    return ranked


def _generate_hook(prospect: Prospect, top_pain: str) -> str:
    """Generate a provocative hook tied to the prospect's top pain point."""
    return (
        f"Your team at {prospect.company_name} told us that "
        f"\"{top_pain.lower()}\" is their biggest challenge. "
        f"In the next few minutes, I'm going to show you how to "
        f"eliminate that problem entirely — live, with real data."
    )


def _generate_context(prospect: Prospect) -> str:
    """Generate the context frame — restate pain points to show we listened."""
    pains = "\n".join(
        f"  {i+1}. {pain}" for i, pain in enumerate(prospect.pain_points)
    )
    tools = ", ".join(prospect.current_tools) if prospect.current_tools else "your current stack"
    return (
        f"Based on our discovery conversation, your team is running {tools} "
        f"and dealing with these challenges:\n{pains}\n\n"
        f"Today I want to show you how we address each of these, starting "
        f"with the one you said is most painful."
    )


def _generate_talking_points(
    feature: Feature,
    pain_point: str,
    audience: str,
) -> list[str]:
    """Generate audience-adapted talking points for a demo segment."""
    config = AUDIENCE_TALKING_POINTS.get(audience, AUDIENCE_TALKING_POINTS["mixed"])
    verb = config["verbs"][hash(feature.name) % len(config["verbs"])]

    return [
        f"{config['prefix']}{feature.name} {verb} the \"{pain_point}\" problem.",
        f"Let me show you this live — watch what happens when I "
        f"{feature.description.lower().rstrip('.')}.",
        f"The result: {pain_point.lower()} is no longer an issue for your team.",
    ]


def _generate_wow_moment(feature: Feature, prospect: Prospect) -> str:
    """Generate the wow moment based on the highest wow-factor feature."""
    return (
        f"Now watch this — I'm going to trigger the exact scenario your team "
        f"struggles with. {feature.description}. See that? "
        f"That just happened automatically, in real time, with zero "
        f"manual intervention. That's the difference between your current "
        f"workflow and what's possible with our platform."
    )


def _generate_close(prospect: Prospect, segments: list[DemoSegment]) -> str:
    """Generate the close with recap and next-step proposal."""
    recap = "\n".join(
        f"  {i+1}. {seg.feature.name} addresses \"{seg.pain_point}\""
        for i, seg in enumerate(segments)
    )
    return (
        f"Let me recap what we covered today:\n{recap}\n\n"
        f"Based on what you've seen, does this address your top priorities? "
        f"Here's what I'd suggest as a next step: a focused 2-week POC on "
        f"your most critical use case, using your actual data from "
        f"{', '.join(prospect.current_tools[:2]) if prospect.current_tools else 'your systems'}. "
        f"What does your team's availability look like?"
    )


def build_demo_script(prospect: Prospect, features: list[Feature]) -> NarrativeDemo:
    """
    Build a complete demo script following the five-act narrative arc.

    This is the reference implementation for Exercise 1.

    The function:
    1. Filters and ranks features by relevance to the prospect's pain points
    2. Selects the top 3 features (no feature dumping)
    3. Determines duration based on audience type
    4. Allocates time across the five acts
    5. Generates audience-adapted content for each act
    """
    # Step 1: Rank features by relevance
    ranked = _rank_features_for_prospect(features, prospect)

    if not ranked:
        return NarrativeDemo(
            hook="Unable to generate — no features match prospect pain points.",
            context="",
            segments=[],
            wow_moment="",
            close="",
            total_minutes=0,
            audience_notes="No relevant features found for this prospect.",
        )

    # Step 2: Select top 3 (max)
    selected = ranked[:3]

    # Step 3: Determine total duration
    total_minutes = AUDIENCE_DURATION.get(prospect.role, 30)

    # Step 4: Allocate time
    solution_minutes = int(total_minutes * ACT_ALLOCATION["solution"])

    # Step 5: Build segments with time allocation
    segments = []
    for i, (feature, matched_pains) in enumerate(selected):
        split = SEGMENT_SPLITS[i] if i < len(SEGMENT_SPLITS) else 0.10
        seg_minutes = max(1, int(solution_minutes * split))
        pain = matched_pains[0]

        talking_points = _generate_talking_points(feature, pain, prospect.role)
        audience_notes = AUDIENCE_TALKING_POINTS.get(
            prospect.role, AUDIENCE_TALKING_POINTS["mixed"]
        )["style"]

        segments.append(DemoSegment(
            pain_point=pain,
            feature=feature,
            talking_points=talking_points,
            estimated_minutes=seg_minutes,
            audience_notes=audience_notes,
        ))

    # Step 6: Generate each act
    top_pain = prospect.pain_points[0]
    hook = _generate_hook(prospect, top_pain)
    context = _generate_context(prospect)

    # Wow moment uses highest wow-factor feature
    wow_feature = max((f for f, _ in selected), key=lambda f: f.wow_factor)
    wow_moment = _generate_wow_moment(wow_feature, prospect)

    close = _generate_close(prospect, segments)

    return NarrativeDemo(
        hook=hook,
        context=context,
        segments=segments,
        wow_moment=wow_moment,
        close=close,
        total_minutes=total_minutes,
        audience_notes=(
            f"Audience type: {prospect.role}. "
            f"Style: {AUDIENCE_TALKING_POINTS.get(prospect.role, AUDIENCE_TALKING_POINTS['mixed'])['style']}. "
            f"Duration target: {total_minutes} minutes."
        ),
    )


# ---------------------------------------------------------------------------
# 2. POC SCOPE DOCUMENT
# ---------------------------------------------------------------------------
# Full POC scope document builder with templates.
# Implements the scoping framework from 02-poc-design-and-execution.md.

@dataclass
class Requirement:
    """A customer requirement for POC scoping."""
    description: str
    priority: str  # "must-have", "nice-to-have", "stretch"
    category: str  # "integration", "performance", "security", "usability", "data"


@dataclass
class ScopeDocument:
    """Complete POC scope document."""
    objective: str
    in_scope: list[Requirement]
    out_of_scope: list[Requirement]
    stretch_goals: list[Requirement]
    success_criteria: list[str]
    timeline_weeks: int
    estimated_days: int
    milestones: list[dict[str, str]]
    risks: list[str]
    customer_dependencies: list[str]


def _matches_capability(requirement: Requirement, capabilities: list[str]) -> bool:
    """Check if a requirement matches any product capability."""
    req_lower = requirement.description.lower()
    for cap in capabilities:
        cap_lower = cap.lower()
        # Check bidirectional substring match
        if cap_lower in req_lower or req_lower in cap_lower:
            return True
        # Check word overlap (at least 2 significant words)
        req_words = set(req_lower.split()) - {"the", "a", "an", "with", "for", "and", "or", "in", "to", "from"}
        cap_words = set(cap_lower.split()) - {"the", "a", "an", "with", "for", "and", "or", "in", "to", "from"}
        if len(req_words & cap_words) >= 2:
            return True
    return False


def _generate_criterion(index: int, requirement: Requirement) -> str:
    """Generate a success criterion string from a requirement."""
    return (
        f"SC-{index}: Demonstrate {requirement.description} "
        f"in the {requirement.category} domain."
    )


def _estimate_timeline(in_scope: list[Requirement]) -> tuple[int, int]:
    """Estimate POC timeline in weeks and working days."""
    base_days = 10  # 2 weeks base
    complex_items = sum(
        1 for r in in_scope if r.category in ("integration", "security")
    )
    extra_days = complex_items * 5  # 1 week per complex item
    total_days = base_days + extra_days
    weeks = math.ceil(total_days / 5)
    return weeks, total_days


def _identify_risks(
    in_scope: list[Requirement],
    out_of_scope: list[Requirement],
    all_requirements: list[Requirement],
) -> list[str]:
    """Identify risks based on scope classification."""
    risks = []

    # Must-haves that are out of scope
    must_have_oos = [r for r in out_of_scope if r.priority == "must-have"]
    for r in must_have_oos:
        risks.append(
            f"CRITICAL: Must-have requirement \"{r.description}\" is out of "
            f"scope — product may not meet this need."
        )

    # Integration dependencies
    integrations = [r for r in in_scope if r.category == "integration"]
    if integrations:
        risks.append(
            f"Integration risk: {len(integrations)} integration(s) in scope — "
            f"customer must provide API access and credentials on time."
        )

    # Scope size
    if len(in_scope) > 3:
        risks.append(
            "Scope risk: More than 3 items in scope increases likelihood "
            "of scope creep and timeline overrun."
        )

    return risks


def _generate_milestones(timeline_weeks: int) -> list[dict[str, str]]:
    """Generate standard milestones based on timeline."""
    total_days = timeline_weeks * 5
    return [
        {
            "name": "Kickoff & Environment Setup",
            "target": f"Day 1-{min(3, total_days)}",
            "deliverable": "Environment configured, credentials verified, "
                          "communication channels established",
        },
        {
            "name": "First Data Flows",
            "target": f"Day {min(5, total_days)}",
            "deliverable": "Basic connectivity proven with at least one "
                          "data source",
        },
        {
            "name": "Core Use Case Working",
            "target": f"Day {min(total_days // 2, total_days)}",
            "deliverable": "Primary success criterion demonstrated",
        },
        {
            "name": "All Criteria Validated",
            "target": f"Day {min(int(total_days * 0.75), total_days)}",
            "deliverable": "All success criteria tested and documented",
        },
        {
            "name": "Results Presentation",
            "target": f"Day {total_days}",
            "deliverable": "POC results document delivered to decision-maker",
        },
    ]


def define_poc_scope(
    requirements: list[Requirement],
    capabilities: list[str],
    max_in_scope: int = 3,
) -> ScopeDocument:
    """
    Build a complete POC scope document.

    This is the reference implementation for Exercise 2.

    The function:
    1. Classifies each requirement as in-scope, out-of-scope, or stretch
    2. Enforces the Three Use Cases rule
    3. Generates success criteria for in-scope items
    4. Estimates timeline and generates milestones
    5. Identifies risks
    """
    in_scope = []
    out_of_scope = []
    stretch_goals = []

    # Step 1: Classify requirements
    for req in requirements:
        matches = _matches_capability(req, capabilities)

        if req.priority == "must-have":
            if matches:
                in_scope.append(req)
            else:
                out_of_scope.append(req)
        elif req.priority == "nice-to-have":
            if matches:
                in_scope.append(req)
            else:
                stretch_goals.append(req)
        else:  # "stretch"
            stretch_goals.append(req)

    # Step 2: Enforce max in-scope (Three Use Cases rule)
    if len(in_scope) > max_in_scope:
        # Keep must-haves first, then by original order
        must_haves = [r for r in in_scope if r.priority == "must-have"]
        nice_to_haves = [r for r in in_scope if r.priority == "nice-to-have"]

        kept = must_haves[:max_in_scope]
        remaining_slots = max_in_scope - len(kept)
        if remaining_slots > 0:
            kept.extend(nice_to_haves[:remaining_slots])

        overflow = [r for r in in_scope if r not in kept]
        stretch_goals.extend(overflow)
        in_scope = kept

    # Step 3: Generate success criteria
    success_criteria = [
        _generate_criterion(i + 1, req) for i, req in enumerate(in_scope)
    ]

    # Step 4: Estimate timeline
    timeline_weeks, estimated_days = _estimate_timeline(in_scope)

    # Step 5: Generate milestones
    milestones = _generate_milestones(timeline_weeks)

    # Step 6: Identify risks
    risks = _identify_risks(in_scope, out_of_scope, requirements)

    # Step 7: Customer dependencies
    customer_deps = []
    for req in in_scope:
        if req.category == "integration":
            customer_deps.append(
                f"API credentials and access for: {req.description}"
            )
        if req.category == "data":
            customer_deps.append(
                f"Sample data or data access for: {req.description}"
            )
        if req.category == "security":
            customer_deps.append(
                f"Security team review for: {req.description}"
            )

    # Step 8: Generate objective
    if in_scope:
        objective = (
            f"Validate that the platform can {in_scope[0].description.lower()} "
            f"for {requirements[0].category} use cases."
        )
    else:
        objective = "No in-scope requirements identified."

    return ScopeDocument(
        objective=objective,
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        stretch_goals=stretch_goals,
        success_criteria=success_criteria,
        timeline_weeks=timeline_weeks,
        estimated_days=estimated_days,
        milestones=milestones,
        risks=risks,
        customer_dependencies=customer_deps,
    )


# ---------------------------------------------------------------------------
# 3. OBJECTION HANDLER LIBRARY
# ---------------------------------------------------------------------------
# Categorization engine and response generator for common objections.
# Implements the frameworks from 03-technical-objection-handling.md.

class ObjCategory(Enum):
    TECHNICAL = "technical"
    PROCESS = "process"
    COMPETITIVE = "competitive"
    FUD = "fud"
    BUDGET = "budget"
    TIMELINE = "timeline"


@dataclass
class ARRResponse:
    """Acknowledge-Reframe-Redirect response."""
    acknowledge: str
    reframe: str
    redirect: str
    supporting_evidence: str


@dataclass
class HandledObjection:
    """Complete objection handling result."""
    original: str
    category: ObjCategory
    confidence: float
    strategies: list[ARRResponse]
    follow_up_questions: list[str]
    requirements_captured: list[str]


# Keyword signals for categorization
OBJECTION_SIGNALS: dict[ObjCategory, list[str]] = {
    ObjCategory.TECHNICAL: [
        "scale", "scalability", "performance", "latency", "encrypt",
        "security", "compliance", "architecture", "on-prem", "uptime",
        "availability", "data residency", "FIPS", "SOC", "HIPAA",
        "throughput", "reliability", "failover", "redundancy",
        "bandwidth", "capacity", "SLA",
    ],
    ObjCategory.PROCESS: [
        "security team", "procurement", "legal", "review", "approval",
        "committee", "governance", "policy", "audit", "sign-off",
        "compliance team", "InfoSec", "process",
    ],
    ObjCategory.COMPETITIVE: [
        "competitor", "alternative", "compared to", "versus", "vs",
        "better than", "cheaper than", "does this better", "already using",
        "incumbent", "existing solution", "switch from",
    ],
    ObjCategory.FUD: [
        "risky", "risk", "worried", "concern", "afraid", "trust",
        "burned before", "vendor lock-in", "too new", "unproven",
        "not ready", "immature", "AI risk", "too risky",
    ],
    ObjCategory.BUDGET: [
        "expensive", "cost", "price", "budget", "afford", "cheaper",
        "ROI", "investment", "spend", "fiscal year", "funding",
        "total cost", "licensing", "pricing",
    ],
    ObjCategory.TIMELINE: [
        "timeline", "deadline", "implement by", "too long", "migration",
        "bandwidth", "resources", "team is busy", "can't start",
        "next quarter", "next year", "roadmap", "capacity",
    ],
}

# Category-specific response templates
RESPONSE_TEMPLATES: dict[ObjCategory, dict[str, str]] = {
    ObjCategory.TECHNICAL: {
        "acknowledge": "That's a fair technical concern, and it's exactly the right question to ask at this stage.",
        "reframe": "Let me share the architecture and benchmarks that address this. We currently handle {evidence} for customers with similar requirements.",
        "redirect": "This is actually an area where our architecture differentiates us. Let me show you specifically how we handle this.",
        "evidence": "published benchmark data and customer case studies",
        "follow_ups": [
            "Can you share your specific technical requirements and SLAs?",
            "What does your current architecture look like for this?",
            "Would a focused POC on this specific concern be helpful?",
        ],
    },
    ObjCategory.PROCESS: {
        "acknowledge": "Absolutely — that's an important step, and we want to make sure your team is fully comfortable.",
        "reframe": "We go through this process with enterprise customers regularly. We have pre-built materials that streamline the review.",
        "redirect": "Let me connect you with our team who can provide everything needed for the review. We can usually have materials ready within 48 hours.",
        "evidence": "SOC 2 Type II report, security whitepaper, completed SIG questionnaire",
        "follow_ups": [
            "Who needs to be involved in the review process?",
            "What specific materials does your team typically need?",
            "What's the typical timeline for this review cycle?",
        ],
    },
    ObjCategory.COMPETITIVE: {
        "acknowledge": "That's a reasonable comparison, and it makes sense to evaluate your options thoroughly.",
        "reframe": "Customers who've evaluated both solutions often tell us that the key differentiator is {evidence}.",
        "redirect": "Where we uniquely excel is in our approach to this specific problem. Let me show you what that looks like in practice.",
        "evidence": "unique capabilities that competitors don't offer",
        "follow_ups": [
            "What specifically did you find compelling about their approach?",
            "Are you comparing on feature breadth, or on your specific use case?",
            "Would it be helpful to connect you with a customer who made this same comparison?",
        ],
    },
    ObjCategory.FUD: {
        "acknowledge": "That's a completely valid concern, and I appreciate you raising it directly.",
        "reframe": "The risk profile depends on the deployment model. Let me walk you through our approach to mitigating exactly this concern.",
        "redirect": "We designed our platform specifically to address this. Here's how customers in your industry have deployed it safely.",
        "evidence": "customer case studies, risk mitigation framework, audit trails",
        "follow_ups": [
            "Can you share more about the specific experience that concerns you?",
            "What would need to be true for you to feel comfortable moving forward?",
            "Would a phased rollout approach reduce the perceived risk?",
        ],
    },
    ObjCategory.BUDGET: {
        "acknowledge": "I understand — budget allocation is always a critical factor, and you want to ensure the investment is justified.",
        "reframe": "Let me reframe this around the cost of the problem you're solving. Based on what you shared about your current process, the status quo costs approximately {evidence}.",
        "redirect": "Our customers typically see ROI within the first quarter. Let me walk you through the value model we built with a similar customer.",
        "evidence": "quantified cost of the current manual process",
        "follow_ups": [
            "How are you measuring the cost of your current approach?",
            "What would the ROI need to look like to justify the investment?",
            "Is this a budget timing issue or a total cost concern?",
        ],
    },
    ObjCategory.TIMELINE: {
        "acknowledge": "That makes sense — your team's bandwidth is finite, and timing matters.",
        "reframe": "We don't need a big-bang implementation. Most customers start with a focused Phase 1 that takes {evidence}.",
        "redirect": "Let me propose a phased approach that respects your team's current workload while making progress on the highest-priority use case.",
        "evidence": "2-3 weeks for the core use case",
        "follow_ups": [
            "What's driving the timeline constraint?",
            "If we could start with just the most critical use case, would that be feasible?",
            "What does your team's availability look like in the next quarter?",
        ],
    },
}


def categorize_objection(objection: str) -> tuple[ObjCategory, float]:
    """
    Categorize an objection using keyword signal matching.

    Returns the best-matching category and a confidence score (0-1).
    """
    objection_lower = objection.lower()
    scores: dict[ObjCategory, int] = {}

    for category, signals in OBJECTION_SIGNALS.items():
        matches = sum(1 for s in signals if s.lower() in objection_lower)
        if matches > 0:
            scores[category] = matches

    if not scores:
        return ObjCategory.TECHNICAL, 0.3  # Default with low confidence

    best_category = max(scores, key=scores.get)
    best_count = scores[best_category]
    total_signals = len(OBJECTION_SIGNALS[best_category])
    confidence = min(1.0, best_count / max(1, total_signals * 0.3))

    return best_category, round(confidence, 2)


def generate_responses(
    objection: str,
    category: ObjCategory,
) -> list[ARRResponse]:
    """
    Generate three ARR response strategies for the given objection and category.
    """
    template = RESPONSE_TEMPLATES[category]

    # Strategy 1: Direct address
    direct = ARRResponse(
        acknowledge=template["acknowledge"],
        reframe=template["reframe"].format(evidence=template["evidence"]),
        redirect=template["redirect"],
        supporting_evidence=template["evidence"],
    )

    # Strategy 2: Customer story
    story = ARRResponse(
        acknowledge="I hear you, and you're not the first customer to raise this.",
        reframe=(
            f"A customer in a similar situation — same industry, similar "
            f"constraints — had the exact same concern. Here's what they did..."
        ),
        redirect=(
            "They started with a focused pilot, proved the value in 3 weeks, "
            "and have since expanded to full deployment. Happy to connect you."
        ),
        supporting_evidence="Customer reference and case study",
    )

    # Strategy 3: Collaborative (turn objection into requirement)
    # Extract the core concern from the objection
    story_collaborative = ARRResponse(
        acknowledge="That's an important point, and I want to make sure we address it properly.",
        reframe=(
            f"So what I'm hearing is that you need us to prove "
            f"[specific capability]. Let me capture that as a requirement."
        ),
        redirect=(
            "Let's build this into our evaluation criteria so we can "
            "validate it explicitly. Would a focused POC on this specific "
            "concern work for your team?"
        ),
        supporting_evidence="Captured as a POC success criterion",
    )

    return [direct, story, story_collaborative]


def _capture_requirement(objection: str, category: ObjCategory) -> str:
    """Turn an objection into a captured requirement."""
    category_to_requirement = {
        ObjCategory.TECHNICAL: "Technical requirement: validate that the platform meets the stated technical criteria.",
        ObjCategory.PROCESS: "Process requirement: provide all materials needed for internal review and approval.",
        ObjCategory.COMPETITIVE: "Competitive requirement: demonstrate differentiated value vs incumbent/alternative.",
        ObjCategory.FUD: "Risk mitigation requirement: demonstrate safety controls, audit trails, and phased rollout options.",
        ObjCategory.BUDGET: "Value requirement: provide quantified ROI analysis and TCO comparison.",
        ObjCategory.TIMELINE: "Timeline requirement: propose phased implementation that respects resource constraints.",
    }
    return category_to_requirement.get(
        category,
        "General requirement: address the stated concern with evidence."
    )


def handle_objection(objection: str) -> HandledObjection:
    """
    Complete objection handling pipeline.

    This is the reference implementation for Exercise 4.

    1. Categorize the objection
    2. Generate ARR response strategies
    3. Capture the objection as a requirement
    4. Provide follow-up questions
    """
    category, confidence = categorize_objection(objection)
    strategies = generate_responses(objection, category)
    template = RESPONSE_TEMPLATES[category]
    requirement = _capture_requirement(objection, category)

    return HandledObjection(
        original=objection,
        category=category,
        confidence=confidence,
        strategies=strategies,
        follow_up_questions=template["follow_ups"],
        requirements_captured=[requirement],
    )


# ---------------------------------------------------------------------------
# 4. SUCCESS CRITERIA MATRIX
# ---------------------------------------------------------------------------
# SMART criteria generator with scoring rubric.
# Implements the framework from 02-poc-design-and-execution.md.

@dataclass
class SMARTCriterion:
    """A SMART success criterion with scoring rubric."""
    criterion_id: str
    description: str
    specific: str
    measurable: str
    achievable: str
    relevant: str
    time_bound: str
    target_value: str
    scoring_rubric: dict[str, str]  # "pass", "partial", "fail" descriptions


# Priority keywords to target value mapping
PRIORITY_TARGET_MAP = [
    (["latency", "speed", "performance", "fast", "response time"], "< 500ms P95"),
    (["accuracy", "quality", "correctness", "correct", "precise"], ">= 95%"),
    (["scale", "volume", "throughput", "concurrent", "load"], ">= 10,000 records/minute"),
    (["integration", "connect", "API", "ingest", "data flow"], "Successful end-to-end data flow"),
    (["usability", "self-serve", "no-code", "analyst", "user-friendly"], "Completed by non-technical user without assistance"),
    (["security", "compliance", "encrypt", "SSO", "auth"], "Passes security review checklist"),
    (["availability", "uptime", "reliability", "resilient"], ">= 99.9% during POC period"),
]


def _determine_target_value(priority: str) -> str:
    """Determine the target value based on priority keywords."""
    priority_lower = priority.lower()
    for keywords, target in PRIORITY_TARGET_MAP:
        if any(kw.lower() in priority_lower for kw in keywords):
            return target
    return "Pass/Fail"


def _generate_scoring_rubric(target_value: str) -> dict[str, str]:
    """Generate a scoring rubric for a given target value."""
    if target_value.startswith("<"):
        # Latency-style target
        return {
            "pass": f"Consistently meets {target_value} in repeated testing",
            "partial": f"Meets target in most tests but occasional spikes above threshold",
            "fail": f"Consistently exceeds target or unable to measure",
        }
    elif target_value.startswith(">="):
        return {
            "pass": f"Achieves {target_value} in validation testing",
            "partial": f"Within 10% of target value",
            "fail": f"More than 10% below target value",
        }
    elif "end-to-end" in target_value.lower():
        return {
            "pass": "Complete data flow from source to destination verified",
            "partial": "Data flows but requires manual steps or has minor issues",
            "fail": "Data flow is broken or requires significant workarounds",
        }
    elif "non-technical" in target_value.lower():
        return {
            "pass": "Non-technical user completes the task independently",
            "partial": "User completes with minor guidance (< 5 minutes of help)",
            "fail": "User requires significant technical assistance",
        }
    else:
        return {
            "pass": "Criterion fully met",
            "partial": "Criterion partially met with acceptable limitations",
            "fail": "Criterion not met",
        }


def generate_success_criteria(
    use_case: str,
    priorities: list[str],
    poc_duration_weeks: int = 2,
) -> list[SMARTCriterion]:
    """
    Generate SMART success criteria from a use case and priorities.

    This is the reference implementation for Exercise 3.

    Each criterion is specific, measurable, achievable, relevant,
    and time-bound, with a scoring rubric for evaluation.
    """
    criteria = []

    for i, priority in enumerate(priorities[:5]):  # Max 5 criteria
        target_value = _determine_target_value(priority)
        rubric = _generate_scoring_rubric(target_value)

        criterion = SMARTCriterion(
            criterion_id=f"SC-{i + 1}",
            description=f"{priority} — validated in the context of: {use_case}",
            specific=f"Test: {priority} using the POC environment with representative data.",
            measurable=f"Measured by: {target_value}",
            achievable=(
                f"Achievable because: the product supports this capability "
                f"and similar results have been demonstrated with other customers."
            ),
            relevant=f"Relevant because: the customer identified \"{priority}\" as a decision criterion.",
            time_bound=f"Demonstrated by: end of Week {poc_duration_weeks}.",
            target_value=target_value,
            scoring_rubric=rubric,
        )
        criteria.append(criterion)

    return criteria


# ---------------------------------------------------------------------------
# 5. DEMO ENVIRONMENT CHECKLIST
# ---------------------------------------------------------------------------
# Pre-demo checklist generator with backup plan.
# Implements the preparation framework from 01-demo-engineering.md.

@dataclass
class ChecklistItem:
    """A single checklist item for demo preparation."""
    timing: str  # "T-24h", "T-4h", "T-1h", "T-30m", "T-5m"
    category: str  # "environment", "data", "credentials", "presentation", "backup"
    action: str
    verification: str
    fallback: str


@dataclass
class RecoveryOption_:
    """A recovery option for a specific failure scenario."""
    description: str
    steps: list[str]
    timing_impact_minutes: int
    confidence: str  # "high", "medium", "low"
    prerequisites: list[str]


@dataclass
class DemoChecklist:
    """Complete pre-demo checklist with backup plan."""
    items: list[ChecklistItem]
    recovery_plans: dict[str, list[RecoveryOption_]]
    backup_materials: list[str]


# Standard checklist items organized by timing
STANDARD_CHECKLIST = [
    # T-24 hours
    ChecklistItem(
        timing="T-24h",
        category="environment",
        action="Run the complete golden path end-to-end",
        verification="All screens render correctly, all workflows complete",
        fallback="Fix issues or prepare backup screenshots for broken segments",
    ),
    ChecklistItem(
        timing="T-24h",
        category="data",
        action="Verify seed data is populated and tells the right story",
        verification="All demo entities exist with correct values",
        fallback="Run seed data reset script",
    ),
    ChecklistItem(
        timing="T-24h",
        category="backup",
        action="Record a video walkthrough of the full demo",
        verification="Video is saved locally and accessible offline",
        fallback="Use screenshots as minimal backup",
    ),
    # T-4 hours
    ChecklistItem(
        timing="T-4h",
        category="credentials",
        action="Verify all API keys, tokens, and credentials",
        verification="Test each API endpoint with a simple request",
        fallback="Have backup credentials in a secure vault",
    ),
    ChecklistItem(
        timing="T-4h",
        category="data",
        action="Refresh seed data if stale",
        verification="Run data integrity check script",
        fallback="Use cached/static data set",
    ),
    ChecklistItem(
        timing="T-4h",
        category="environment",
        action="Confirm demo environment version matches expected release",
        verification="Check version endpoint or about page",
        fallback="Pin to specific version or use backup environment",
    ),
    # T-1 hour
    ChecklistItem(
        timing="T-1h",
        category="presentation",
        action="Close unnecessary applications and browser tabs",
        verification="Only demo-related windows are open",
        fallback="N/A — just do it",
    ),
    ChecklistItem(
        timing="T-1h",
        category="presentation",
        action="Enable Do Not Disturb on OS, Slack, email, and phone",
        verification="Test by sending yourself a message — no notification appears",
        fallback="Close notification-heavy apps entirely",
    ),
    ChecklistItem(
        timing="T-1h",
        category="presentation",
        action="Set display resolution and font size for screen sharing",
        verification="Text is readable at projected/shared resolution (18pt+ for code)",
        fallback="Zoom in on specific areas during the demo",
    ),
    # T-30 minutes
    ChecklistItem(
        timing="T-30m",
        category="environment",
        action="Open all demo tabs in the correct order",
        verification="Each tab loads correctly and is pre-authenticated",
        fallback="Have URLs bookmarked for quick re-opening",
    ),
    ChecklistItem(
        timing="T-30m",
        category="presentation",
        action="Test screen sharing and audio in the meeting tool",
        verification="Colleague confirms they can see the screen and hear audio",
        fallback="Have a phone dial-in as audio backup",
    ),
    # T-5 minutes
    ChecklistItem(
        timing="T-5m",
        category="environment",
        action="Run the first two steps of the golden path to warm caches",
        verification="First demo screen loads quickly when needed",
        fallback="Skip cache warming — accept slightly slower first load",
    ),
    ChecklistItem(
        timing="T-5m",
        category="presentation",
        action="Position all windows for the demo flow",
        verification="Windows are arranged in presentation order",
        fallback="Use keyboard shortcuts to switch between windows",
    ),
]

# Recovery plans by failure type
FAILURE_RECOVERY_PLANS: dict[str, list[RecoveryOption_]] = {
    "environment_crash": [
        RecoveryOption_(
            description="Switch to backup environment",
            steps=[
                "Acknowledge briefly: 'Let me switch to our backup instance.'",
                "Open the backup environment URL from bookmarks.",
                "Continue the narrative from where you left off.",
            ],
            timing_impact_minutes=2,
            confidence="high",
            prerequisites=["Backup environment URL bookmarked", "Backup environment pre-loaded"],
        ),
        RecoveryOption_(
            description="Play pre-recorded video",
            steps=[
                "Acknowledge: 'I have a recording of exactly this flow.'",
                "Open the locally-saved demo video.",
                "Play the relevant segment, narrating over it.",
            ],
            timing_impact_minutes=3,
            confidence="medium",
            prerequisites=["Video recorded within last 24 hours", "Video saved locally"],
        ),
        RecoveryOption_(
            description="Walk through screenshots",
            steps=[
                "Acknowledge: 'Let me show you what this looks like.'",
                "Open the screenshot deck or folder.",
                "Walk through each screen, describing the workflow.",
            ],
            timing_impact_minutes=2,
            confidence="low",
            prerequisites=["Screenshots captured for each demo step"],
        ),
    ],
    "api_timeout": [
        RecoveryOption_(
            description="Retry the API call",
            steps=[
                "Wait 5 seconds and retry.",
                "If it succeeds, continue without comment.",
                "If it fails again, switch to backup.",
            ],
            timing_impact_minutes=1,
            confidence="high",
            prerequisites=[],
        ),
        RecoveryOption_(
            description="Show pre-captured response",
            steps=[
                "Say: 'Let me show you what the response looks like.'",
                "Open a pre-saved API response in a text file or browser tab.",
                "Walk through the response structure.",
            ],
            timing_impact_minutes=1,
            confidence="high",
            prerequisites=["API responses pre-captured in a local file"],
        ),
    ],
    "data_missing": [
        RecoveryOption_(
            description="Run seed data reset script",
            steps=[
                "Say: 'Let me refresh our demo data — one moment.'",
                "Run the seed script in a pre-opened terminal.",
                "Continue once data is loaded.",
            ],
            timing_impact_minutes=3,
            confidence="medium",
            prerequisites=["Seed script tested and ready", "Terminal pre-opened"],
        ),
        RecoveryOption_(
            description="Switch to screenshots of populated data",
            steps=[
                "Say: 'Let me show you this with our standard demo data.'",
                "Open screenshots showing the populated data view.",
                "Describe the workflow using the screenshots.",
            ],
            timing_impact_minutes=2,
            confidence="high",
            prerequisites=["Screenshots of populated data available"],
        ),
    ],
    "auth_failure": [
        RecoveryOption_(
            description="Use backup credentials",
            steps=[
                "Open credential vault.",
                "Copy backup credentials.",
                "Re-authenticate.",
            ],
            timing_impact_minutes=1,
            confidence="high",
            prerequisites=["Backup credentials in secure vault"],
        ),
        RecoveryOption_(
            description="Use pre-authenticated session in another browser",
            steps=[
                "Switch to a different browser profile with an active session.",
                "Continue the demo from the pre-authenticated state.",
            ],
            timing_impact_minutes=1,
            confidence="high",
            prerequisites=["Second browser profile pre-authenticated"],
        ),
    ],
    "network_issue": [
        RecoveryOption_(
            description="Switch to mobile hotspot",
            steps=[
                "Enable mobile hotspot.",
                "Connect laptop to hotspot.",
                "Reload the demo environment.",
            ],
            timing_impact_minutes=2,
            confidence="medium",
            prerequisites=["Mobile hotspot available with sufficient data"],
        ),
        RecoveryOption_(
            description="Switch to offline backup materials",
            steps=[
                "Acknowledge: 'Looks like we have a connectivity issue.'",
                "Switch to locally-saved video or screenshots.",
                "Continue the narrative with offline materials.",
            ],
            timing_impact_minutes=2,
            confidence="high",
            prerequisites=["All backup materials saved locally"],
        ),
    ],
}


def generate_demo_checklist(
    demo_segments: list[str],
    demo_type: str = "virtual",
) -> DemoChecklist:
    """
    Generate a pre-demo checklist with backup plans.

    This is the reference implementation for Exercise 5.

    Returns a checklist customized for the demo type (virtual/in-person)
    and includes recovery plans for common failure scenarios.
    """
    items = list(STANDARD_CHECKLIST)

    # Add type-specific items
    if demo_type == "in-person":
        items.append(ChecklistItem(
            timing="T-1h",
            category="presentation",
            action="Test projector/screen, HDMI adapter, and room WiFi",
            verification="Screen displays correctly, WiFi connects reliably",
            fallback="Bring your own adapter, charger, and mobile hotspot",
        ))
        items.append(ChecklistItem(
            timing="T-30m",
            category="presentation",
            action="Set up whiteboard for architecture discussion",
            verification="Markers work, eraser available, whiteboard clean",
            fallback="Use tablet or paper for diagrams",
        ))

    # Add segment-specific items
    for segment in demo_segments:
        items.append(ChecklistItem(
            timing="T-4h",
            category="environment",
            action=f"Verify demo segment '{segment}' works end-to-end",
            verification=f"'{segment}' completes without errors",
            fallback=f"Prepare screenshots/video for '{segment}' as backup",
        ))

    # Sort by timing
    timing_order = {"T-24h": 0, "T-4h": 1, "T-1h": 2, "T-30m": 3, "T-5m": 4}
    items.sort(key=lambda x: timing_order.get(x.timing, 5))

    # Backup materials list
    backup_materials = [
        "Pre-recorded video of the full demo (saved locally)",
        "Screenshots of every key screen in the golden path",
        "Pre-captured API responses for all demo API calls",
        "Backup demo environment URL (separate instance)",
        "Backup credentials in a secure vault",
        "Offline slide deck with key screenshots and talking points",
    ]

    return DemoChecklist(
        items=items,
        recovery_plans=FAILURE_RECOVERY_PLANS,
        backup_materials=backup_materials,
    )


# ---------------------------------------------------------------------------
# Usage Examples
# ---------------------------------------------------------------------------

def main():
    """Demonstrate each pattern."""

    # 1. Demo Narrative Engine
    print("=" * 70)
    print("1. DEMO NARRATIVE ENGINE")
    print("=" * 70)

    prospect = Prospect(
        company_name="Acme Financial",
        industry="Financial Services",
        role="mixed",
        pain_points=[
            "Schema changes break dashboards weekly",
            "Root cause analysis takes hours",
            "New data sources take weeks to onboard",
        ],
        current_tools=["Airflow", "dbt", "Snowflake"],
        company_size="enterprise",
    )

    features = [
        Feature("Auto-Schema Evolution", "Automatically adapts to schema changes",
                ["Schema changes break dashboards weekly"], 8, 9, "moderate"),
        Feature("Data Lineage Graph", "Visual lineage from dashboard to source",
                ["Root cause analysis takes hours"], 5, 7, "simple"),
        Feature("No-Code Connectors", "Add data sources without engineering",
                ["New data sources take weeks to onboard"], 4, 6, "simple"),
        Feature("SQL Editor", "In-browser SQL with autocomplete",
                [], 3, 4, "simple"),
    ]

    script = build_demo_script(prospect, features)
    print(f"Hook: {script.hook}")
    print(f"\nContext: {script.context}")
    print(f"\nSegments ({len(script.segments)}):")
    for seg in script.segments:
        print(f"  - {seg.feature.name} ({seg.estimated_minutes} min)")
        for tp in seg.talking_points:
            print(f"    > {tp}")
    print(f"\nWow Moment: {script.wow_moment}")
    print(f"\nClose: {script.close}")
    print(f"\nTotal: {script.total_minutes} min | {script.audience_notes}")
    print()

    # 2. POC Scope Document
    print("=" * 70)
    print("2. POC SCOPE DOCUMENT")
    print("=" * 70)

    requirements = [
        Requirement("Ingest data from Salesforce API", "must-have", "integration"),
        Requirement("Transform data with custom SQL", "must-have", "data"),
        Requirement("Real-time latency under 5 minutes", "must-have", "performance"),
        Requirement("SSO integration with Okta", "nice-to-have", "security"),
        Requirement("Custom dashboard builder", "stretch", "usability"),
    ]

    scope = define_poc_scope(
        requirements,
        capabilities=[
            "Salesforce connector",
            "SQL transformation engine",
            "Real-time streaming",
            "SSO with SAML",
        ],
    )

    print(f"Objective: {scope.objective}")
    print(f"\nIn-Scope ({len(scope.in_scope)}):")
    for r in scope.in_scope:
        print(f"  [{r.priority}] {r.description}")
    print(f"\nOut-of-Scope ({len(scope.out_of_scope)}):")
    for r in scope.out_of_scope:
        print(f"  [{r.priority}] {r.description}")
    print(f"\nStretch ({len(scope.stretch_goals)}):")
    for r in scope.stretch_goals:
        print(f"  [{r.priority}] {r.description}")
    print(f"\nSuccess Criteria:")
    for sc in scope.success_criteria:
        print(f"  {sc}")
    print(f"\nTimeline: {scope.timeline_weeks} weeks ({scope.estimated_days} days)")
    print(f"Milestones:")
    for ms in scope.milestones:
        print(f"  {ms['target']}: {ms['name']} — {ms['deliverable']}")
    print(f"\nRisks:")
    for risk in scope.risks:
        print(f"  - {risk}")
    print()

    # 3. Objection Handler
    print("=" * 70)
    print("3. OBJECTION HANDLER LIBRARY")
    print("=" * 70)

    test_objections = [
        "Your platform can't handle our scale — we process 10 billion events per day.",
        "We need to run this by our security team before we can proceed.",
        "Competitor X has better pricing and more features.",
        "AI is too risky for healthcare. We've been burned by vendors before.",
        "It's too expensive for our current budget.",
        "Our team is too busy with the migration to start another project.",
    ]

    for objection in test_objections:
        result = handle_objection(objection)
        print(f'Objection: "{objection}"')
        print(f"  Category: {result.category.value} (confidence: {result.confidence})")
        print(f"  Strategy 1:")
        print(f"    Acknowledge: {result.strategies[0].acknowledge}")
        print(f"    Reframe: {result.strategies[0].reframe}")
        print(f"    Redirect: {result.strategies[0].redirect}")
        print(f"  Follow-up: {result.follow_up_questions[0]}")
        print(f"  Requirement: {result.requirements_captured[0]}")
        print()

    # 4. Success Criteria Matrix
    print("=" * 70)
    print("4. SUCCESS CRITERIA MATRIX")
    print("=" * 70)

    criteria = generate_success_criteria(
        use_case="Ingest data from Salesforce and HubSpot into Snowflake",
        priorities=[
            "End-to-end latency must be fast",
            "Data accuracy and correctness",
            "Integration with existing pipelines",
            "Self-serve onboarding for analysts",
        ],
        poc_duration_weeks=3,
    )

    for sc in criteria:
        print(f"{sc.criterion_id}: {sc.description}")
        print(f"  Specific: {sc.specific}")
        print(f"  Measurable: {sc.measurable}")
        print(f"  Target: {sc.target_value}")
        print(f"  Rubric: Pass={sc.scoring_rubric['pass'][:60]}...")
        print()

    # 5. Demo Environment Checklist
    print("=" * 70)
    print("5. DEMO ENVIRONMENT CHECKLIST")
    print("=" * 70)

    checklist = generate_demo_checklist(
        demo_segments=["Auto-Schema Evolution", "Data Lineage", "Connectors"],
        demo_type="virtual",
    )

    current_timing = ""
    for item in checklist.items:
        if item.timing != current_timing:
            current_timing = item.timing
            print(f"\n  --- {current_timing} ---")
        print(f"  [{item.category}] {item.action}")
        print(f"    Verify: {item.verification}")

    print(f"\nBackup Materials:")
    for material in checklist.backup_materials:
        print(f"  - {material}")

    print(f"\nRecovery Plans Available: {list(checklist.recovery_plans.keys())}")
    for scenario, options in checklist.recovery_plans.items():
        print(f"\n  {scenario}:")
        for i, opt in enumerate(options):
            print(f"    Option {i+1}: {opt.description} "
                  f"(+{opt.timing_impact_minutes} min, {opt.confidence})")


if __name__ == "__main__":
    main()
