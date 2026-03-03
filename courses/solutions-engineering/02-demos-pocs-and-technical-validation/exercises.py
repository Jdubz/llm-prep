"""
Module 02: Demos, POCs, and Technical Validation — Exercises

Skeleton functions with TODOs. Each exercise focuses on solutions engineering
skills: structuring demos, scoping POCs, designing success criteria, handling
objections, and managing technical validation processes.

No external dependencies required — these exercises use pure Python to model
the frameworks and decision-making patterns covered in the MD files.
"""

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Shared Data Structures
# ---------------------------------------------------------------------------

@dataclass
class ProspectProfile:
    """Profile of the prospect for demo/POC planning."""
    company_name: str
    industry: str
    role: str  # "executive", "architect", "developer", "end_user", "mixed"
    pain_points: list[str]
    current_tools: list[str]
    company_size: str  # "startup", "mid-market", "enterprise"
    deal_size: str  # "small", "medium", "large", "enterprise"


@dataclass
class ProductFeature:
    """A product feature that can be demoed."""
    name: str
    description: str
    pain_points_addressed: list[str]
    demo_time_minutes: int
    wow_factor: int  # 1-10, how impressive this is when shown live
    complexity: str  # "simple", "moderate", "complex"


@dataclass
class DemoSegment:
    """A single segment in a demo script."""
    pain_point: str
    feature: ProductFeature
    talking_points: list[str]
    estimated_minutes: int
    audience_notes: str


@dataclass
class DemoScript:
    """Complete demo script with narrative arc."""
    hook: str
    context: str
    segments: list[DemoSegment]
    wow_moment: str
    close: str
    total_estimated_minutes: int
    audience_adaptation_notes: str


@dataclass
class CustomerRequirement:
    """A requirement the customer wants validated."""
    description: str
    priority: str  # "must-have", "nice-to-have", "stretch"
    category: str  # "integration", "performance", "security", "usability", "data"


@dataclass
class POCScope:
    """Scope definition for a POC."""
    objective: str
    in_scope: list[CustomerRequirement]
    out_of_scope: list[CustomerRequirement]
    stretch_goals: list[CustomerRequirement]
    success_criteria: list[str]
    timeline_weeks: int
    risks: list[str]


@dataclass
class SuccessCriterion:
    """A single SMART success criterion."""
    criterion_id: str
    description: str
    specific: str
    measurable: str
    achievable: str
    relevant: str
    time_bound: str
    target_value: str


class ObjectionCategory(Enum):
    TECHNICAL = "technical"
    PROCESS = "process"
    COMPETITIVE = "competitive"
    FUD = "fud"
    BUDGET = "budget"
    TIMELINE = "timeline"


@dataclass
class ResponseStrategy:
    """A single response strategy using Acknowledge-Reframe-Redirect."""
    acknowledge: str
    reframe: str
    redirect: str
    supporting_evidence: str


@dataclass
class ObjectionResponse:
    """Categorized objection with recommended response strategies."""
    original_objection: str
    category: ObjectionCategory
    confidence: float  # 0.0 - 1.0
    strategies: list[ResponseStrategy]
    follow_up_questions: list[str]


@dataclass
class RecoveryOption:
    """A single recovery option for a demo failure."""
    description: str
    steps: list[str]
    timing_impact_minutes: int
    confidence: str  # "high", "medium", "low"
    prerequisites: list[str]


@dataclass
class RecoveryPlan:
    """Plan for recovering from a demo failure."""
    failure_scenario: str
    assessment: str
    options: list[RecoveryOption]
    recommended_option: int  # index into options
    prevention_tips: list[str]


@dataclass
class Milestone:
    """A POC milestone."""
    name: str
    target_day: int
    deliverable: str
    success_signal: str


@dataclass
class POCTimeline:
    """Estimated POC timeline with milestones."""
    estimated_days: int
    buffer_days: int
    total_days: int
    milestones: list[Milestone]
    risk_factors: list[str]
    recommended_cadence: str


# ============================================================================
# EXERCISE 1: Demo Script Builder
# ============================================================================
# READ FIRST:
#   - 01-demo-engineering.md -> "Demo Narrative Arc"
#     (Five-Act Structure: hook, context, solution, wow moment, close)
#   - 01-demo-engineering.md -> "Audience Adaptation"
#     (Audience Adaptation Matrix: how demos change for executives, architects,
#      developers, end users — duration, depth, language, focus)
#   - 01-demo-engineering.md -> "Demo Anti-Patterns"
#     (Feature dumping, not tailoring, going overtime — the script must avoid these)
#
# ALSO SEE:
#   - examples.py -> Section 1 "DEMO NARRATIVE ENGINE"
#     (build_demo_script() — complete implementation showing how to construct
#      each act of the demo, rank features by pain-point relevance, and adapt
#      timing/language for different audience types)
#
# Build a complete demo script from a prospect profile and product features.
# The script must follow the five-act narrative arc, map features to pain
# points, adapt for the audience type, and respect time constraints.
#
# Key concepts:
#   - Pain-point mapping: features only appear if they address a listed pain
#   - Audience adaptation: executive demos are 5 min, developer demos are 45 min
#   - Wow moment selection: pick the feature with highest wow_factor that
#     addresses the prospect's top pain point
#   - Time budgeting: 60% of solution time on the top pain, 25% on second,
#     15% on third
# ============================================================================

def build_demo_script(
    prospect: ProspectProfile,
    features: list[ProductFeature],
) -> DemoScript:
    """
    Build a structured demo script from prospect profile and product features.

    TODO: Implement this function.

    Steps:
    1. Filter features to only those that address at least one of the
       prospect's pain points. Discard irrelevant features (no feature dumping).
       - relevant = [f for f in features
                     if any(p in f.pain_points_addressed for p in prospect.pain_points)]
    2. Rank the relevant features by how many pain points they address,
       breaking ties with wow_factor.
       - sorted(relevant, key=lambda f: (len(set(f.pain_points_addressed) & set(prospect.pain_points)), f.wow_factor), reverse=True)
    3. Select the top 3 features for the demo segments (at most 3 —
       more than 3 is feature dumping per 01-demo-engineering.md).
    4. Determine the total demo duration based on audience type:
       - "executive": 5 minutes total
       - "architect": 25 minutes total
       - "developer": 40 minutes total
       - "end_user": 20 minutes total
       - "mixed": 30 minutes total
    5. Allocate time across the five acts:
       - Hook: ~5% of total
       - Context: ~10% of total
       - Solution segments: ~70% of total (split 60/25/15 across segments)
       - Wow moment: ~10% of total
       - Close: ~5% of total
    6. Generate the hook — a provocative opening tied to the prospect's
       top pain point. Reference the "Effective hook patterns" table.
    7. Generate the context — restate the prospect's pain points to show
       you listened during discovery.
    8. Build each DemoSegment with talking points adapted for the audience:
       - Executives: focus on outcomes and ROI
       - Architects: focus on how it works, integration, scalability
       - Developers: focus on API, code, SDK
       - End users: focus on workflow and UX
    9. Select the wow moment — the feature with the highest wow_factor.
    10. Generate the close — recap value and propose a next step.
    11. Assemble and return the DemoScript dataclass.

    Returns:
        DemoScript with all fields populated.
    """
    raise NotImplementedError("Complete the demo script builder")


# ============================================================================
# EXERCISE 2: POC Scope Definer
# ============================================================================
# READ FIRST:
#   - 02-poc-design-and-execution.md -> "POC Scoping"
#     (Three Use Cases rule, scope document template, getting sign-off)
#   - 02-poc-design-and-execution.md -> "When to POC"
#     (Decision tree for when a POC is necessary vs wasteful)
#   - 02-poc-design-and-execution.md -> "Build vs Configure"
#     (80/20 rule — 80% should be achievable with configuration alone)
#
# ALSO SEE:
#   - examples.py -> Section 2 "POC SCOPE DOCUMENT"
#     (define_poc_scope() — complete implementation showing how to classify
#      requirements as in-scope/out-of-scope/stretch, generate success criteria,
#      estimate timeline, and identify risks)
#
# Given customer requirements and product capabilities, determine what is
# in scope, out of scope, and stretch. Generate success criteria for
# in-scope items.
#
# Key concepts:
#   - Requirements with "must-have" priority that match capabilities → in-scope
#   - Requirements with "must-have" priority that DON'T match → risk flag
#   - Requirements with "nice-to-have" → in-scope if simple, stretch if complex
#   - Requirements with "stretch" → always stretch goals
#   - Never more than 3 use cases in scope (Three Use Cases rule)
# ============================================================================

def define_poc_scope(
    requirements: list[CustomerRequirement],
    product_capabilities: list[str],
    max_use_cases: int = 3,
) -> POCScope:
    """
    Define POC scope from customer requirements and product capabilities.

    TODO: Implement this function.

    Steps:
    1. For each requirement, check if it matches a product capability:
       - Match = any capability string is a substring of the requirement
         description (case-insensitive), or vice versa.
       - Hint: normalize both to lowercase and check
         any(cap.lower() in req.description.lower() or
             req.description.lower() in cap.lower()
             for cap in product_capabilities)
    2. Classify each requirement:
       - "must-have" + matches capability → in-scope
       - "must-have" + does NOT match → out-of-scope (flag as risk)
       - "nice-to-have" + matches + complexity is not "complex" → in-scope
       - "nice-to-have" + does not match or is complex → stretch
       - "stretch" priority → always stretch
    3. Apply the Three Use Cases rule:
       - If more than max_use_cases items are in-scope, keep only the
         top max_use_cases by priority (must-have first), moving extras
         to stretch goals.
    4. Generate a success criterion string for each in-scope requirement:
       - Format: "SC-{N}: Demonstrate {requirement.description}
         in the {requirement.category} domain."
    5. Estimate timeline: 2 weeks base + 1 week per complex in-scope item.
    6. Identify risks:
       - Any must-have requirement that is out-of-scope is a risk
       - Any in-scope item with category "integration" is a risk
         (depends on customer providing access)
    7. Generate the POC objective from the top in-scope requirement.
    8. Return the POCScope dataclass.

    Returns:
        POCScope with all fields populated.
    """
    raise NotImplementedError("Complete the POC scope definer")


# ============================================================================
# EXERCISE 3: Success Criteria Generator
# ============================================================================
# READ FIRST:
#   - 02-poc-design-and-execution.md -> "Success Criteria Design"
#     (SMART criteria: Specific, Measurable, Achievable, Relevant, Time-bound)
#   - 02-poc-design-and-execution.md -> "Example Success Criteria by Scenario"
#     (concrete examples for data integration, AI/ML, and security platforms)
#   - 02-poc-design-and-execution.md -> "Getting the Customer to Define Success"
#     (questions to ask the customer to anchor criteria)
#
# ALSO SEE:
#   - examples.py -> Section 4 "SUCCESS CRITERIA MATRIX"
#     (generate_success_criteria() — complete implementation showing SMART
#      decomposition, target value generation, and scoring rubric creation)
#
# Given a use case description and customer priorities, generate SMART
# success criteria that are specific enough to be evaluated at POC end.
#
# Key concepts:
#   - Each criterion must be independently testable
#   - Quantitative criteria (latency < X, accuracy > Y) are preferred
#   - Each criterion maps to a customer priority
#   - Time-bound means "demonstrated by POC end date"
# ============================================================================

def generate_success_criteria(
    use_case: str,
    customer_priorities: list[str],
    poc_duration_weeks: int = 2,
) -> list[SuccessCriterion]:
    """
    Generate SMART success criteria from a use case and customer priorities.

    TODO: Implement this function.

    Steps:
    1. Parse the use case description to identify key capabilities being tested.
       - Look for action verbs: "ingest", "transform", "detect", "integrate",
         "process", "classify", "monitor", "deploy"
       - Each verb suggests a testable criterion
    2. For each customer priority, generate one SuccessCriterion:
       - criterion_id: "SC-{N}" where N is 1-indexed
       - description: combine the priority with the use case context
       - specific: what exactly is being tested (not vague)
       - measurable: how it will be measured (metric, threshold, yes/no)
       - achievable: why this is realistic for the POC
       - relevant: how it connects to the customer's business need
       - time_bound: "Demonstrated by end of Week {poc_duration_weeks}"
       - target_value: a concrete target
         (e.g., "< 500ms P95 latency", "> 95% accuracy", "yes/no")
    3. Determine target_value based on the priority category:
       - If priority mentions "latency" or "speed" or "performance"
         → target_value = "< 500ms P95"
       - If priority mentions "accuracy" or "quality" or "correctness"
         → target_value = ">= 95%"
       - If priority mentions "scale" or "volume" or "throughput"
         → target_value = ">= 10,000 records/minute"
       - If priority mentions "integration" or "connect" or "API"
         → target_value = "Successful end-to-end data flow"
       - If priority mentions "usability" or "self-serve" or "no-code"
         → target_value = "Completed by non-technical user without assistance"
       - Default → target_value = "Pass/Fail"
    4. Return the list of SuccessCriterion, one per priority.
       If there are more than 5 priorities, only generate criteria for
       the first 5 (too many criteria dilute focus).

    Returns:
        List of SuccessCriterion dataclasses, one per customer priority
        (max 5).
    """
    raise NotImplementedError("Complete the success criteria generator")


# ============================================================================
# EXERCISE 4: Objection Response Matcher
# ============================================================================
# READ FIRST:
#   - 03-technical-objection-handling.md -> "Objection Categories"
#     (Table mapping 6 categories to signals, meanings, and approaches)
#   - 03-technical-objection-handling.md -> "The Acknowledge-Reframe-Redirect
#     Framework" (Three-step response pattern with 5 detailed examples)
#   - 03-technical-objection-handling.md -> "Turning Objections Into
#     Requirements" (converting adversarial energy into collaborative energy)
#
# ALSO SEE:
#   - examples.py -> Section 3 "OBJECTION HANDLER LIBRARY"
#     (categorize_objection() and generate_responses() — complete
#      implementation showing keyword-based categorization, confidence
#      scoring, and ARR response generation for each category)
#
# Given an objection text, categorize it and generate recommended
# response strategies using acknowledge-reframe-redirect.
#
# Key concepts:
#   - Keyword signals map to categories (see CATEGORY_SIGNALS below)
#   - Multiple categories may apply — pick the strongest match
#   - Each strategy must use all three ARR steps
#   - Follow-up questions help deepen the conversation
# ============================================================================

# Keyword signals for each category — used for classification
CATEGORY_SIGNALS = {
    ObjectionCategory.TECHNICAL: [
        "scale", "scalability", "performance", "latency", "encrypt",
        "security", "compliance", "architecture", "on-prem", "uptime",
        "availability", "data residency", "FIPS", "SOC", "HIPAA",
        "throughput", "reliability", "failover", "redundancy",
    ],
    ObjectionCategory.PROCESS: [
        "security team", "procurement", "legal", "review", "approval",
        "committee", "governance", "policy", "audit", "sign-off",
        "compliance team", "InfoSec",
    ],
    ObjectionCategory.COMPETITIVE: [
        "competitor", "alternative", "compared to", "versus", "vs",
        "better than", "cheaper than", "does this better", "already using",
        "incumbent", "existing solution", "switch from",
    ],
    ObjectionCategory.FUD: [
        "risky", "risk", "worried", "concern", "afraid", "trust",
        "burned before", "vendor lock-in", "too new", "unproven",
        "not ready", "immature", "AI risk", "too risky",
    ],
    ObjectionCategory.BUDGET: [
        "expensive", "cost", "price", "budget", "afford", "cheaper",
        "ROI", "investment", "spend", "fiscal year", "funding",
        "total cost", "licensing",
    ],
    ObjectionCategory.TIMELINE: [
        "timeline", "deadline", "implement by", "too long", "migration",
        "bandwidth", "resources", "team is busy", "can't start",
        "next quarter", "next year", "roadmap", "capacity",
    ],
}


def categorize_objection(objection: str) -> tuple[ObjectionCategory, float]:
    """
    Categorize an objection and return confidence score.

    TODO: Implement this function.

    Steps:
    1. Normalize the objection text to lowercase.
    2. For each category in CATEGORY_SIGNALS, count how many signal
       keywords appear in the objection text.
       - scores = {}
       - for category, signals in CATEGORY_SIGNALS.items():
       -     matches = sum(1 for s in signals if s.lower() in objection_lower)
       -     if matches > 0:
       -         scores[category] = matches
    3. Select the category with the highest count.
       - If no signals match, default to ObjectionCategory.TECHNICAL
         with confidence 0.3.
    4. Calculate confidence as:
       matches / total_signals_in_category, capped at 1.0
       (more matches = higher confidence in the categorization).
    5. Return (category, confidence).

    Returns:
        Tuple of (ObjectionCategory, confidence: float).
    """
    raise NotImplementedError("Complete the objection categorizer")


def generate_objection_response(
    objection: str,
) -> ObjectionResponse:
    """
    Generate a full objection response with categorization and strategies.

    TODO: Implement this function.

    Steps:
    1. Call categorize_objection() to get the category and confidence.
    2. Generate 3 ResponseStrategy objects, each with ARR steps:
       Strategy 1 — Direct address:
         - Acknowledge: validate the specific concern raised
         - Reframe: provide evidence or context that addresses it
         - Redirect: pivot to a relevant product strength
       Strategy 2 — Customer story:
         - Acknowledge: show empathy
         - Reframe: share how a similar customer had the same concern
         - Redirect: describe the customer's positive outcome
       Strategy 3 — Collaborative:
         - Acknowledge: agree it's important
         - Reframe: turn the objection into a requirement
           (see "Turning Objections Into Requirements" in the MD)
         - Redirect: propose a concrete next step to validate
    3. Generate 2-3 follow-up questions that deepen the conversation:
       - For TECHNICAL: "Can you share your specific requirements for X?"
       - For PROCESS: "Who needs to be involved in the review?"
       - For COMPETITIVE: "What specifically did you like about their approach?"
       - For FUD: "Can you share more about the experience that concerns you?"
       - For BUDGET: "How are you measuring ROI on your current solution?"
       - For TIMELINE: "What's driving the deadline?"
    4. Return ObjectionResponse with all fields.

    Hint for generating acknowledge/reframe/redirect text:
    - Use the category to determine the tone and content
    - TECHNICAL → evidence-based (benchmarks, docs, certs)
    - PROCESS → facilitative (offer to help navigate)
    - COMPETITIVE → differentiating (unique strengths)
    - FUD → empathetic (validate, then de-risk)
    - BUDGET → value-focused (quantify savings)
    - TIMELINE → phased (break into smaller steps)

    Returns:
        ObjectionResponse with category, strategies, and follow-up questions.
    """
    raise NotImplementedError("Complete the objection response generator")


# ============================================================================
# EXERCISE 5: Demo Failure Recovery Planner
# ============================================================================
# READ FIRST:
#   - 01-demo-engineering.md -> "Handling Demo Failures"
#     (Demo Recovery Framework: PAUSE-ASSESS-DECIDE-REDIRECT)
#   - 01-demo-engineering.md -> "Recovery Options by Failure Type"
#     (Table mapping failure types to recovery actions)
#   - 01-demo-engineering.md -> "What NOT to Do When a Demo Breaks"
#     (Anti-patterns: repeated apologies, blaming team, long debugging)
#
# ALSO SEE:
#   - examples.py -> Section 5 "DEMO ENVIRONMENT CHECKLIST"
#     (generate_recovery_plan() — complete implementation showing how to
#      assess failure severity, generate ranked recovery options, and
#      estimate timing impact for each option)
#
# Given a demo plan and a failure scenario, generate recovery options
# ranked by preference, with timing impact for each.
#
# Key concepts:
#   - Recovery options are ranked: quick fix > backup > acknowledge & move on
#   - Each option has prerequisites (e.g., backup tab must be pre-loaded)
#   - Timing impact affects the remaining demo schedule
#   - Prevention tips help avoid the failure next time
# ============================================================================

# Failure scenarios and their characteristics
FAILURE_TYPES = {
    "environment_crash": {
        "severity": "high",
        "fixable_quickly": False,
        "backup_useful": True,
        "description": "Demo environment is completely down or unresponsive",
    },
    "api_timeout": {
        "severity": "medium",
        "fixable_quickly": True,
        "backup_useful": True,
        "description": "API calls are timing out or returning errors",
    },
    "data_missing": {
        "severity": "medium",
        "fixable_quickly": False,
        "backup_useful": True,
        "description": "Seed data is missing or corrupted",
    },
    "wrong_version": {
        "severity": "low",
        "fixable_quickly": True,
        "backup_useful": False,
        "description": "Product is showing a different version than expected",
    },
    "auth_failure": {
        "severity": "medium",
        "fixable_quickly": True,
        "backup_useful": True,
        "description": "Login or authentication is failing",
    },
    "network_issue": {
        "severity": "high",
        "fixable_quickly": False,
        "backup_useful": True,
        "description": "Network connectivity is down or unstable",
    },
}


def plan_demo_recovery(
    demo_segments: list[str],
    failure_scenario: str,
    current_segment_index: int,
) -> RecoveryPlan:
    """
    Generate a recovery plan for a demo failure.

    TODO: Implement this function.

    Steps:
    1. Look up the failure type in FAILURE_TYPES.
       - If not found, create a generic entry with severity="medium",
         fixable_quickly=False, backup_useful=True.
    2. Assess the situation based on the failure characteristics:
       - If fixable_quickly is True:
         assessment = "This is likely fixable within 10-15 seconds. Attempt
         a quick fix first, then fall back to backup if needed."
       - If fixable_quickly is False and backup_useful is True:
         assessment = "This is not quickly fixable. Switch to backup
         materials immediately to maintain demo momentum."
       - If fixable_quickly is False and backup_useful is False:
         assessment = "Acknowledge the issue, explain what the audience
         would see, and move to the next segment."
    3. Generate recovery options (ranked best to worst):
       Option A — Quick Fix (only if fixable_quickly):
         - steps: scenario-specific quick fix steps
         - timing_impact: 1-2 minutes
         - confidence: "high" if fixable, else "low"
         - prerequisites: depends on scenario
       Option B — Switch to Backup:
         - steps: ["Acknowledge briefly", "Switch to pre-loaded backup tab
           or screenshots", "Continue the narrative from the backup"]
         - timing_impact: 2-3 minutes
         - confidence: "high"
         - prerequisites: ["Backup tab pre-loaded", "Screenshots available"]
       Option C — Video Recording:
         - steps: ["Acknowledge the issue", "Play pre-recorded video of
           this segment", "Resume live demo at next segment"]
         - timing_impact: 3-5 minutes
         - confidence: "medium"
         - prerequisites: ["Video recording available"]
       Option D — Skip and Narrate:
         - steps: ["Acknowledge the issue briefly", "Describe what the
           audience would see", "Move to the next segment"]
         - timing_impact: 1 minute
         - confidence: "low"
         - prerequisites: []
    4. Select the recommended option:
       - If fixable_quickly: recommend Option A (index 0)
       - Else if backup_useful: recommend Option B (index 0 or 1 depending
         on whether quick fix was included)
       - Else: recommend the narrate option
    5. Generate prevention tips specific to the failure type:
       - "environment_crash" → "Run golden path T-4 hours. Have a
         second environment on standby."
       - "api_timeout" → "Test all API endpoints T-1 hour. Pre-cache
         responses for critical demo calls."
       - "data_missing" → "Verify seed data T-4 hours. Keep a data
         reset script ready."
       - "wrong_version" → "Pin the demo environment to a specific
         version. Disable auto-updates."
       - "auth_failure" → "Verify credentials T-1 hour. Pre-authenticate
         in all browser tabs."
       - "network_issue" → "Use a wired connection. Have a mobile
         hotspot as backup."
    6. Return RecoveryPlan with all fields populated.

    Returns:
        RecoveryPlan with assessment, ranked options, and prevention tips.
    """
    raise NotImplementedError("Complete the demo failure recovery planner")


# ============================================================================
# EXERCISE 6: POC Timeline Estimator
# ============================================================================
# READ FIRST:
#   - 02-poc-design-and-execution.md -> "Timeline Management"
#     (Typical POC timelines by product type, milestone setting, buffer rules)
#   - 02-poc-design-and-execution.md -> "POC Execution"
#     (Weekly cadence: kickoff → build → validate → present)
#   - 02-poc-design-and-execution.md -> "When to Extend vs When to Call It"
#     (Decision framework for timeline adjustments)
#
# ALSO SEE:
#   - examples.py -> Section 2 "POC SCOPE DOCUMENT"
#     (estimate_poc_timeline() — shows timeline estimation based on scope
#      complexity, including milestone generation and buffer calculation)
#
# Given scope complexity factors, estimate a POC timeline with milestones
# and appropriate buffer.
#
# Key concepts:
#   - Base duration depends on number of use cases and their complexity
#   - Customer responsiveness factor adjusts the timeline (slow = longer)
#   - Buffer = estimated_time * 0.5 (the 1.5x rule from the MD)
#   - Milestones follow the standard cadence: first data flows → core use
#     case → all criteria → results presented
# ============================================================================

def estimate_poc_timeline(
    num_use_cases: int,
    num_integrations: int,
    num_data_sources: int,
    complexity: str,  # "low", "medium", "high"
    customer_responsiveness: str,  # "fast", "normal", "slow"
    se_availability: str,  # "full-time", "part-time", "limited"
) -> POCTimeline:
    """
    Estimate a POC timeline with milestones and buffer.

    TODO: Implement this function.

    Steps:
    1. Calculate base duration in working days:
       - Start with base by complexity:
         "low": 5 days, "medium": 10 days, "high": 15 days
       - Add days per use case: 3 days each
       - Add days per integration: 2 days each
       - Add days per data source: 1 day each
    2. Apply customer responsiveness multiplier:
       - "fast": 1.0x (no adjustment)
       - "normal": 1.2x
       - "slow": 1.5x
    3. Apply SE availability multiplier:
       - "full-time": 1.0x
       - "part-time": 1.5x
       - "limited": 2.0x
    4. Round up to the nearest whole day.
    5. Calculate buffer: 50% of estimated days (the 1.5x rule).
       - buffer_days = ceil(estimated_days * 0.5)
    6. Total days = estimated_days + buffer_days.
    7. Generate milestones using the standard cadence:
       Milestone 1: "Environment Setup & First Data Flows"
         - target_day = ceil(total_days * 0.2)
         - deliverable: "Basic connectivity proven"
         - success_signal: "Data flows from at least one source"
       Milestone 2: "Core Use Case Working"
         - target_day = ceil(total_days * 0.5)
         - deliverable: "Primary success criterion met"
         - success_signal: "Customer validates primary workflow"
       Milestone 3: "All Criteria Validated"
         - target_day = ceil(total_days * 0.75)
         - deliverable: "All success criteria tested"
         - success_signal: "Results documented for each criterion"
       Milestone 4: "Results Presented"
         - target_day = total_days
         - deliverable: "POC results document delivered to decision-maker"
         - success_signal: "Go/no-go decision scheduled"
    8. Identify risk factors based on inputs:
       - If num_integrations > 2: "Multiple integrations increase
         dependency risk"
       - If customer_responsiveness == "slow": "Slow customer
         responsiveness may delay data access and reviews"
       - If se_availability != "full-time": "Limited SE availability
         extends calendar time"
       - If num_use_cases > 3: "More than 3 use cases risks scope
         creep (see Three Use Cases rule)"
       - If complexity == "high": "High complexity increases
         likelihood of unexpected technical issues"
    9. Determine recommended cadence:
       - total_days <= 10: "Daily async updates, 2 sync check-ins per week"
       - total_days <= 20: "Every-other-day async updates, weekly sync"
       - total_days > 20: "Weekly status reports, bi-weekly sync meetings"
    10. Return POCTimeline with all fields.

    Returns:
        POCTimeline with estimated days, buffer, milestones, and risks.
    """
    raise NotImplementedError("Complete the POC timeline estimator")


# ---------------------------------------------------------------------------
# Test Functions
# ---------------------------------------------------------------------------

def test_exercise_1():
    """Test the demo script builder."""
    print("=" * 60)
    print("Exercise 1: Demo Script Builder")
    print("=" * 60)

    prospect = ProspectProfile(
        company_name="DataCorp",
        industry="Financial Services",
        role="mixed",
        pain_points=[
            "Schema changes break dashboards weekly",
            "Root cause analysis takes hours",
            "Onboarding new data sources takes weeks",
        ],
        current_tools=["Airflow", "dbt", "Snowflake"],
        company_size="enterprise",
        deal_size="large",
    )

    features = [
        ProductFeature(
            name="Auto-Schema Evolution",
            description="Automatically detects and adapts to schema changes",
            pain_points_addressed=["Schema changes break dashboards weekly"],
            demo_time_minutes=8,
            wow_factor=9,
            complexity="moderate",
        ),
        ProductFeature(
            name="Data Lineage Graph",
            description="Visual lineage from dashboard to raw source",
            pain_points_addressed=["Root cause analysis takes hours"],
            demo_time_minutes=5,
            wow_factor=7,
            complexity="simple",
        ),
        ProductFeature(
            name="No-Code Connectors",
            description="Add new data sources without engineering",
            pain_points_addressed=["Onboarding new data sources takes weeks"],
            demo_time_minutes=4,
            wow_factor=6,
            complexity="simple",
        ),
        ProductFeature(
            name="Advanced SQL Editor",
            description="In-browser SQL editor with autocomplete",
            pain_points_addressed=[],  # Not relevant to this prospect
            demo_time_minutes=3,
            wow_factor=4,
            complexity="simple",
        ),
    ]

    try:
        script = build_demo_script(prospect, features)
        print(f"  Hook: {script.hook[:80]}...")
        print(f"  Context: {script.context[:80]}...")
        print(f"  Segments: {len(script.segments)}")
        for seg in script.segments:
            print(f"    - {seg.feature.name} ({seg.estimated_minutes} min)")
        print(f"  Wow Moment: {script.wow_moment[:80]}...")
        print(f"  Close: {script.close[:80]}...")
        print(f"  Total: {script.total_estimated_minutes} min")
        print(f"  Audience Notes: {script.audience_adaptation_notes[:80]}...")

        # Verify no feature dumping
        assert len(script.segments) <= 3, "Too many segments (feature dumping)"
        # Verify irrelevant feature excluded
        segment_names = [s.feature.name for s in script.segments]
        assert "Advanced SQL Editor" not in segment_names, \
            "Irrelevant feature should not be in the demo"
        print("\n  PASS: All checks passed")
    except NotImplementedError:
        print("  NOT IMPLEMENTED")
    print()


def test_exercise_2():
    """Test the POC scope definer."""
    print("=" * 60)
    print("Exercise 2: POC Scope Definer")
    print("=" * 60)

    requirements = [
        CustomerRequirement("Ingest data from Salesforce API", "must-have", "integration"),
        CustomerRequirement("Transform data with custom SQL", "must-have", "data"),
        CustomerRequirement("Real-time latency under 5 minutes", "must-have", "performance"),
        CustomerRequirement("SSO integration with Okta", "nice-to-have", "security"),
        CustomerRequirement("Custom dashboard builder", "stretch", "usability"),
        CustomerRequirement("Support for 50 concurrent users", "must-have", "performance"),
    ]

    capabilities = [
        "Salesforce connector",
        "SQL transformation engine",
        "Real-time data streaming",
        "SSO with SAML and OIDC",
        "Dashboard templates",
        "Horizontal scaling",
    ]

    try:
        scope = define_poc_scope(requirements, capabilities)
        print(f"  Objective: {scope.objective}")
        print(f"  In-scope: {len(scope.in_scope)} items")
        for r in scope.in_scope:
            print(f"    - [{r.priority}] {r.description}")
        print(f"  Out-of-scope: {len(scope.out_of_scope)} items")
        for r in scope.out_of_scope:
            print(f"    - [{r.priority}] {r.description}")
        print(f"  Stretch: {len(scope.stretch_goals)} items")
        for r in scope.stretch_goals:
            print(f"    - [{r.priority}] {r.description}")
        print(f"  Success criteria: {len(scope.success_criteria)}")
        for sc in scope.success_criteria:
            print(f"    - {sc}")
        print(f"  Timeline: {scope.timeline_weeks} weeks")
        print(f"  Risks: {scope.risks}")

        assert len(scope.in_scope) <= 3, "More than 3 items in scope"
        print("\n  PASS: All checks passed")
    except NotImplementedError:
        print("  NOT IMPLEMENTED")
    print()


def test_exercise_3():
    """Test the success criteria generator."""
    print("=" * 60)
    print("Exercise 3: Success Criteria Generator")
    print("=" * 60)

    use_case = "Ingest data from Salesforce and HubSpot into Snowflake warehouse"
    priorities = [
        "End-to-end latency must be fast",
        "Data accuracy and correctness",
        "Integration with existing Airflow pipelines",
        "Self-serve onboarding for analysts",
    ]

    try:
        criteria = generate_success_criteria(use_case, priorities)
        print(f"  Generated {len(criteria)} criteria:")
        for sc in criteria:
            print(f"    {sc.criterion_id}: {sc.description}")
            print(f"      Specific: {sc.specific}")
            print(f"      Measurable: {sc.measurable}")
            print(f"      Target: {sc.target_value}")
            print()

        assert len(criteria) == len(priorities), \
            f"Expected {len(priorities)} criteria, got {len(criteria)}"
        assert all(sc.criterion_id.startswith("SC-") for sc in criteria), \
            "Criterion IDs must start with SC-"
        print("  PASS: All checks passed")
    except NotImplementedError:
        print("  NOT IMPLEMENTED")
    print()


def test_exercise_4():
    """Test the objection response matcher."""
    print("=" * 60)
    print("Exercise 4: Objection Response Matcher")
    print("=" * 60)

    test_objections = [
        "Your platform can't handle our scale — we process 10 billion events per day.",
        "We need to run this by our security team and legal before we can proceed.",
        "We already evaluated Competitor X and their pricing is 40% lower.",
        "AI is too risky for healthcare applications. We've been burned before.",
        "We don't have budget for this until next fiscal year.",
        "Our team is too busy with the migration to take on another project right now.",
    ]

    expected_categories = [
        ObjectionCategory.TECHNICAL,
        ObjectionCategory.PROCESS,
        ObjectionCategory.COMPETITIVE,
        ObjectionCategory.FUD,
        ObjectionCategory.BUDGET,
        ObjectionCategory.TIMELINE,
    ]

    try:
        correct = 0
        for objection, expected in zip(test_objections, expected_categories):
            response = generate_objection_response(objection)
            match = response.category == expected
            correct += match
            status = "PASS" if match else "FAIL"
            print(f"  [{status}] \"{objection[:60]}...\"")
            print(f"    Expected: {expected.value}, Got: {response.category.value}")
            print(f"    Confidence: {response.confidence:.2f}")
            print(f"    Strategy 1 Acknowledge: {response.strategies[0].acknowledge[:60]}...")
            print()

        print(f"  Score: {correct}/{len(test_objections)}")
    except NotImplementedError:
        print("  NOT IMPLEMENTED")
    print()


def test_exercise_5():
    """Test the demo failure recovery planner."""
    print("=" * 60)
    print("Exercise 5: Demo Failure Recovery Planner")
    print("=" * 60)

    demo_segments = [
        "Auto-Schema Evolution",
        "Data Lineage Graph",
        "No-Code Connectors",
    ]

    test_scenarios = [
        ("environment_crash", 0),
        ("api_timeout", 1),
        ("data_missing", 0),
        ("wrong_version", 2),
    ]

    try:
        for scenario, segment_idx in test_scenarios:
            plan = plan_demo_recovery(demo_segments, scenario, segment_idx)
            print(f"  Scenario: {scenario} (during segment: {demo_segments[segment_idx]})")
            print(f"  Assessment: {plan.assessment[:70]}...")
            print(f"  Options: {len(plan.options)}")
            for i, opt in enumerate(plan.options):
                marker = " <-- RECOMMENDED" if i == plan.recommended_option else ""
                print(f"    {i+1}. {opt.description} "
                      f"(+{opt.timing_impact_minutes} min, {opt.confidence}){marker}")
            print(f"  Prevention: {plan.prevention_tips[0]}")
            print()

        print("  PASS: All scenarios generated plans")
    except NotImplementedError:
        print("  NOT IMPLEMENTED")
    print()


def test_exercise_6():
    """Test the POC timeline estimator."""
    print("=" * 60)
    print("Exercise 6: POC Timeline Estimator")
    print("=" * 60)

    test_cases = [
        {
            "name": "Simple SaaS POC",
            "args": (1, 1, 1, "low", "fast", "full-time"),
        },
        {
            "name": "Complex Enterprise POC",
            "args": (3, 4, 3, "high", "slow", "part-time"),
        },
        {
            "name": "Medium Data Platform POC",
            "args": (2, 2, 3, "medium", "normal", "full-time"),
        },
    ]

    try:
        for case in test_cases:
            timeline = estimate_poc_timeline(*case["args"])
            print(f"  {case['name']}:")
            print(f"    Estimated: {timeline.estimated_days} days")
            print(f"    Buffer: {timeline.buffer_days} days")
            print(f"    Total: {timeline.total_days} days "
                  f"({timeline.total_days / 5:.1f} weeks)")
            print(f"    Milestones:")
            for ms in timeline.milestones:
                print(f"      Day {ms.target_day}: {ms.name}")
            print(f"    Risks: {len(timeline.risk_factors)}")
            for risk in timeline.risk_factors:
                print(f"      - {risk}")
            print(f"    Cadence: {timeline.recommended_cadence}")
            print()

        # Verify the complex POC is longer than the simple one
        simple = estimate_poc_timeline(1, 1, 1, "low", "fast", "full-time")
        complex_ = estimate_poc_timeline(3, 4, 3, "high", "slow", "part-time")
        assert complex_.total_days > simple.total_days, \
            "Complex POC should take longer than simple POC"
        print("  PASS: All checks passed")
    except NotImplementedError:
        print("  NOT IMPLEMENTED")
    print()


if __name__ == "__main__":
    test_exercise_1()
    test_exercise_2()
    test_exercise_3()
    test_exercise_4()
    test_exercise_5()
    test_exercise_6()
