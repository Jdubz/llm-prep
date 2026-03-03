"""
Discovery & Technical Sales -- Exercises
==========================================
Skeleton functions to implement. Each exercise reinforces a core SE concept
around discovery methodology, deal qualification, competitive positioning,
and sales cycle management.

Run this file to execute the test functions at the bottom.

Note: These exercises test Solutions Engineering knowledge, not Python knowledge.
The implementations should reflect understanding of how SE processes work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ────────────────────────────────────────────────────────────────────────────
# Shared dataclasses used across multiple exercises
# ────────────────────────────────────────────────────────────────────────────

class SPINCategory(Enum):
    SITUATION = "situation"
    PROBLEM = "problem"
    IMPLICATION = "implication"
    NEED_PAYOFF = "need_payoff"
    UNKNOWN = "unknown"


class DealStage(Enum):
    LEAD = "lead"
    DISCOVERY = "discovery"
    DEMO = "demo"
    POC = "poc"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class Recommendation(Enum):
    PURSUE = "pursue"
    NURTURE = "nurture"
    QUALIFY_OUT = "qualify_out"


@dataclass
class DiscoveryQuestion:
    """A question asked during a discovery call."""
    text: str
    category: Optional[SPINCategory] = None  # None means it needs to be classified


@dataclass
class DiscoveryScore:
    """Score and feedback for a discovery call."""
    total_questions: int
    situation_count: int
    problem_count: int
    implication_count: int
    need_payoff_count: int
    unknown_count: int
    balance_score: float          # 0.0 to 1.0, where 1.0 is ideal SPIN balance
    feedback: list[str]           # Specific feedback items
    categorized_questions: list[tuple[str, SPINCategory]]  # (question_text, category)


@dataclass
class MEDDPICCCard:
    """A MEDDPICC scorecard for a deal. None means the element is not yet captured."""
    metrics: Optional[str] = None
    economic_buyer: Optional[str] = None
    decision_criteria: Optional[str] = None
    decision_process: Optional[str] = None
    paper_process: Optional[str] = None
    identify_pain: Optional[str] = None
    champion: Optional[str] = None
    competition: Optional[str] = None


@dataclass
class MEDDPICCGap:
    """A gap identified in a MEDDPICC scorecard."""
    element: str                  # Which MEDDPICC letter (e.g., "Metrics")
    priority: int                 # 1 = highest priority to fill
    suggested_questions: list[str]  # Questions to ask to fill the gap
    risk_level: str               # "high", "medium", "low"


@dataclass
class MEDDPICCAnalysis:
    """Analysis result for a MEDDPICC scorecard."""
    filled_count: int             # How many elements are populated
    total_elements: int           # Always 8
    gaps: list[MEDDPICCGap]       # Gaps ordered by priority
    overall_health: str           # "strong", "moderate", "weak", "critical"
    summary: str                  # Human-readable summary


@dataclass
class DealAttributes:
    """Attributes of a deal used for qualification scoring."""
    budget_known: bool = False
    budget_amount: Optional[float] = None
    authority_identified: bool = False
    authority_met: bool = False
    need_articulated: bool = False
    timeline_defined: bool = False
    timeline_months: Optional[int] = None
    pain_quantified: bool = False
    champion_identified: bool = False
    champion_has_power: bool = False
    champion_has_access: bool = False
    competition_known: bool = False
    decision_criteria_known: bool = False
    decision_process_mapped: bool = False
    paper_process_understood: bool = False
    metrics_defined: bool = False


@dataclass
class QualificationScore:
    """Qualification scores across multiple frameworks."""
    bant_score: float             # 0.0 to 1.0
    bant_breakdown: dict[str, float]  # {"budget": 0.5, "authority": 1.0, ...}
    meddpicc_score: float         # 0.0 to 1.0
    meddpicc_breakdown: dict[str, float]  # {"metrics": 0.5, "economic_buyer": 0.0, ...}
    composite_score: float        # Weighted average
    recommendation: Recommendation
    reasoning: str


@dataclass
class ProductFeatures:
    """Product feature set for competitive comparison."""
    name: str
    features: dict[str, str]      # {"feature_name": "description/capability"}
    strengths: list[str]          # Key selling points
    pricing_model: str            # e.g., "usage-based", "seat-based"


@dataclass
class BattleCard:
    """Generated battle card comparing two products."""
    your_product: str
    competitor: str
    strengths: list[str]          # Where you win
    weaknesses: list[str]         # Where they win
    landmines: list[str]          # Questions to plant early
    talking_points: list[str]     # Key messages for the prospect
    feature_comparison: list[dict[str, str]]  # [{"feature": ..., "us": ..., "them": ...}]


@dataclass
class DealEvent:
    """An event in a deal's lifecycle."""
    event_type: str               # e.g., "discovery_call", "demo_delivered", "poc_started"
    date: str                     # ISO format "YYYY-MM-DD"
    description: str
    participants: list[str] = field(default_factory=list)


@dataclass
class DealPhase:
    """Current phase assessment for a deal."""
    current_phase: DealStage
    confidence: float             # 0.0 to 1.0
    days_in_phase: int
    next_steps: list[str]
    risks: list[str]
    events_analyzed: int


@dataclass
class DealOutcome:
    """Outcome of a completed deal."""
    deal_name: str
    won: bool
    deal_size: float
    competitor: Optional[str] = None
    loss_reasons: list[str] = field(default_factory=list)
    win_reasons: list[str] = field(default_factory=list)
    sales_cycle_days: int = 0
    had_champion: bool = False
    had_poc: bool = False


@dataclass
class WinLossReport:
    """Aggregated win/loss analysis report."""
    total_deals: int
    wins: int
    losses: int
    win_rate: float
    total_revenue_won: float
    total_revenue_lost: float
    avg_winning_deal_size: float
    avg_losing_deal_size: float
    avg_winning_cycle_days: float
    avg_losing_cycle_days: float
    top_loss_reasons: list[tuple[str, int]]   # (reason, count) sorted by count desc
    top_win_reasons: list[tuple[str, int]]    # (reason, count) sorted by count desc
    competitive_win_rates: dict[str, float]   # {competitor: win_rate}
    champion_impact: dict[str, float]         # {"with_champion": rate, "without": rate}
    poc_impact: dict[str, float]              # {"with_poc": rate, "without": rate}


# ============================================================================
# EXERCISE 1: Discovery Call Scorer
# ============================================================================
# READ FIRST:
#   - 01-discovery-methodology.md -> "SPIN Selling for SEs" section
#     (understand what distinguishes Situation, Problem, Implication, and
#      Need-payoff questions from each other)
#   - 01-discovery-methodology.md -> "SPIN Balance and Sequencing"
#     (ideal distribution: S=10-15%, P=25-30%, I=30-35%, N=20-25%)
#   - 01-discovery-methodology.md -> "What Bad Discovery Looks Like"
#     (too many Situation questions = bad discovery)
#
# ALSO SEE:
#   - examples.py -> Section 2 "DISCOVERY CALL TEMPLATE ENGINE"
#     (SPIN_KEYWORDS dict, categorize_question() function, and
#      score_call_balance() -- follow the same keyword-matching approach)
#
# Take a list of discovery questions from a call, categorize each into the
# SPIN framework, score the overall balance, and provide actionable feedback.
#
# Key concepts:
#   - SPIN categories map to question intent, not just keywords
#   - Good calls have few Situation Qs and many Implication/Need-payoff Qs
#   - The balance score reflects how close the call is to the ideal distribution

def categorize_question(question: str) -> SPINCategory:
    """Categorize a single discovery question into the SPIN framework.

    TODO: Implement this function.

    Classify the question based on keyword signals:
    - SITUATION: "current", "today", "how many", "what tools", "walk me through",
      "what does your", "how long have", "who is responsible"
    - PROBLEM: "frustrating", "challenge", "struggle", "difficult", "pain",
      "not working", "issue", "problem", "what's broken", "complaint"
    - IMPLICATION: "what happens if", "impact", "cost of", "consequence",
      "affect", "what does that mean for", "downstream", "risk"
    - NEED_PAYOFF: "how would it help", "what would change", "ideal",
      "if you could", "imagine", "value", "benefit", "what would it mean"

    Implementation approach (see examples.py categorize_question()):
    1. question_lower = question.lower()
    2. Check NEED_PAYOFF keywords first (most specific)
    3. Check IMPLICATION keywords
    4. Check PROBLEM keywords
    5. Check SITUATION keywords
    6. Default to UNKNOWN

    Return the SPINCategory enum value.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement categorize_question")


def score_discovery_call(questions: list[DiscoveryQuestion]) -> DiscoveryScore:
    """Score a discovery call based on SPIN question balance.

    TODO: Implement this function.

    Steps:
    1. Categorize each question:
       - If question.category is not None, use it as-is
       - If question.category is None, call categorize_question(question.text)
    2. Count questions in each SPIN category
    3. Calculate balance score (0.0 to 1.0):
       - Ideal distribution: S=12.5%, P=27.5%, I=32.5%, N=25% (midpoints of ranges)
       - For each category, compute: abs(actual_pct - ideal_pct)
       - balance_score = 1.0 - sum(deviations) / 2.0  (clamped to [0.0, 1.0])
       - Alternative simpler approach: penalize if S > 30%, reward if I+N > 50%
    4. Generate feedback list:
       - If situation_count > 30% of total: "Too many Situation questions..."
       - If implication_count == 0: "No Implication questions asked..."
       - If need_payoff_count == 0: "No Need-payoff questions asked..."
       - If problem_count > 0 and implication_count > 0: "Good progression..."
       - If total < 5: "Very few questions asked..."
    5. Return DiscoveryScore with all fields populated

    The balance_score should be:
    - > 0.7 for a well-balanced call
    - 0.4-0.7 for an okay call
    - < 0.4 for a poorly balanced call (too many Situation, not enough I/N)
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement score_discovery_call")


# ============================================================================
# EXERCISE 2: MEDDPICC Gap Analyzer
# ============================================================================
# READ FIRST:
#   - 01-discovery-methodology.md -> "MEDDPICC Deep Dive" section
#     (understand each element: Metrics, Economic Buyer, Decision Criteria,
#      Decision Process, Paper Process, Identify Pain, Champion, Competition)
#   - 01-discovery-methodology.md -> "MEDDPICC Scorecard Template"
#     (Red/Yellow/Green scoring approach)
#
# ALSO SEE:
#   - examples.py -> Section 1 "MEDDPICC EVALUATOR"
#     (MEDDPICC_ELEMENTS dict, evaluate_meddpicc() function, gap detection
#      logic, priority ordering -- follow the same approach)
#
# Analyze a MEDDPICC scorecard to identify gaps, prioritize them by deal
# stage importance, and suggest questions to fill each gap.
#
# Key concepts:
#   - Not all MEDDPICC elements are equally important at every deal stage
#   - Pain and Champion are the most critical (no pain = no deal, no champion = no close)
#   - Paper Process matters less early but becomes critical near close

# Suggested questions for each MEDDPICC element when it's missing
MEDDPICC_QUESTIONS: dict[str, list[str]] = {
    "metrics": [
        "What KPIs does your team get measured on?",
        "What would a successful implementation look like in numbers?",
        "How would you measure ROI on this investment?",
    ],
    "economic_buyer": [
        "Who ultimately approves purchases like this?",
        "Walk me through how your team has purchased software before.",
        "Is there a budget already allocated, or does someone need to create one?",
    ],
    "decision_criteria": [
        "What are the must-have vs nice-to-have requirements?",
        "Are there any hard technical constraints we should know about?",
        "How are you evaluating the options you're considering?",
    ],
    "decision_process": [
        "What does your evaluation process look like from here?",
        "Who else needs to be involved before a decision is made?",
        "What's your typical timeline from selecting a vendor to going live?",
    ],
    "paper_process": [
        "What does your procurement process look like?",
        "Is there a security review required? What does that involve?",
        "How long did the last vendor contract take from approval to signature?",
    ],
    "identify_pain": [
        "What's the biggest problem this project is supposed to solve?",
        "What happens if you don't solve this in the next 6 months?",
        "Who is most affected by this problem, and how?",
    ],
    "champion": [
        "Why is this important to you personally?",
        "Who else needs to be convinced? Can you help me understand their perspective?",
        "If we proved value, could you help us get in front of the decision-maker?",
    ],
    "competition": [
        "Are you evaluating other solutions for this?",
        "Have you tried solving this with internal tooling or open-source?",
        "What do you like about the other options you've seen so far?",
    ],
}

# Priority order for MEDDPICC elements (1 = most critical to fill first)
MEDDPICC_PRIORITY: dict[str, int] = {
    "identify_pain": 1,       # No pain = no deal
    "champion": 2,            # No champion = no close
    "economic_buyer": 3,      # Must know who writes the check
    "metrics": 4,             # Need to quantify value
    "decision_criteria": 5,   # Need to know what they're evaluating
    "decision_process": 6,    # Need to know the steps
    "competition": 7,         # Need to know the landscape
    "paper_process": 8,       # Important but can be learned later
}


def analyze_meddpicc(card: MEDDPICCCard) -> MEDDPICCAnalysis:
    """Analyze a MEDDPICC scorecard for gaps and provide prioritized recommendations.

    TODO: Implement this function.

    Steps:
    1. Check each element in the MEDDPICCCard for None or empty string
       - elements = {"metrics": card.metrics, "economic_buyer": card.economic_buyer, ...}
       - filled = [name for name, val in elements.items() if val]
       - missing = [name for name, val in elements.items() if not val]
    2. For each gap, create a MEDDPICCGap with:
       - element: human-readable name (e.g., "Identify Pain" not "identify_pain")
       - priority: from MEDDPICC_PRIORITY dict
       - suggested_questions: from MEDDPICC_QUESTIONS dict
       - risk_level: "high" if priority <= 3, "medium" if 4-6, "low" if 7-8
    3. Sort gaps by priority (lowest number = highest priority = first)
    4. Determine overall_health:
       - 7-8 filled: "strong"
       - 5-6 filled: "moderate"
       - 3-4 filled: "weak"
       - 0-2 filled: "critical"
    5. Generate a summary string that lists the most critical gaps
    6. Return MEDDPICCAnalysis with all fields

    Example: if identify_pain and champion are both missing, overall health
    should be at most "weak" regardless of how many other fields are filled,
    because those are the two most critical elements.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement analyze_meddpicc")


# ============================================================================
# EXERCISE 3: Deal Qualification Scorer
# ============================================================================
# READ FIRST:
#   - 01-discovery-methodology.md -> "Qualification Frameworks" section
#     (BANT breakdown, MEDDPICC vs BANT comparison table)
#   - 01-discovery-methodology.md -> "Deal Qualification Scoring"
#     (1-3 scoring scale, composite score interpretation)
#   - 02-technical-sales-frameworks.md -> "Decision Points and Gates"
#     (criteria to pass between stages)
#
# ALSO SEE:
#   - examples.py -> Section 5 "DEAL QUALIFICATION SCORER"
#     (score_bant(), score_meddpicc(), composite scoring logic,
#      recommendation thresholds -- follow the same approach)
#
# Score a deal against both BANT and MEDDPICC frameworks simultaneously
# and produce a composite recommendation.
#
# Key concepts:
#   - BANT is simpler (4 elements) but misses critical enterprise signals
#   - MEDDPICC is more comprehensive (8 elements) and better for large deals
#   - The composite score weights MEDDPICC higher because it's more predictive
#   - Recommendation thresholds determine whether to pursue, nurture, or qualify out

def score_deal(attributes: DealAttributes) -> QualificationScore:
    """Score a deal against BANT and MEDDPICC frameworks.

    TODO: Implement this function.

    Steps:
    1. Score BANT (each element 0.0 to 1.0):
       - Budget: 1.0 if budget_known and budget_amount > 0, 0.5 if budget_known but
         no amount, 0.0 if not known
       - Authority: 1.0 if authority_met, 0.5 if authority_identified but not met, 0.0 otherwise
       - Need: 1.0 if need_articulated and pain_quantified, 0.5 if need_articulated only, 0.0 otherwise
       - Timeline: 1.0 if timeline_defined and timeline_months <= 6, 0.5 if timeline_defined
         but > 6 months, 0.0 if not defined
       - bant_score = average of the 4 element scores

    2. Score MEDDPICC (each element 0.0 to 1.0):
       - Metrics: 1.0 if metrics_defined and pain_quantified, 0.5 if metrics_defined only, 0.0 otherwise
       - Economic Buyer: 1.0 if authority_met, 0.5 if authority_identified, 0.0 otherwise
       - Decision Criteria: 1.0 if decision_criteria_known, 0.0 otherwise
       - Decision Process: 1.0 if decision_process_mapped, 0.0 otherwise
       - Paper Process: 1.0 if paper_process_understood, 0.0 otherwise
       - Identify Pain: 1.0 if pain_quantified, 0.5 if need_articulated, 0.0 otherwise
       - Champion: 1.0 if champion_identified and champion_has_power and champion_has_access,
         0.5 if champion_identified only, 0.0 otherwise
       - Competition: 1.0 if competition_known, 0.0 otherwise
       - meddpicc_score = average of the 8 element scores

    3. Calculate composite score:
       - composite = 0.3 * bant_score + 0.7 * meddpicc_score  (weight MEDDPICC higher)

    4. Determine recommendation:
       - composite >= 0.7: Recommendation.PURSUE
       - 0.4 <= composite < 0.7: Recommendation.NURTURE
       - composite < 0.4: Recommendation.QUALIFY_OUT

    5. Generate reasoning string explaining the recommendation
       - Include which elements are strong and which are weak

    Return QualificationScore with all fields populated.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement score_deal")


# ============================================================================
# EXERCISE 4: Competitive Battle Card Generator
# ============================================================================
# READ FIRST:
#   - 03-competitive-positioning.md -> "Battle Cards" section
#     (what they are, template, example StreamFlow vs DataPipe card)
#   - 03-competitive-positioning.md -> "Feature Comparison Frameworks"
#     (how to build honest comparisons, choosing favorable dimensions)
#   - 03-competitive-positioning.md -> "Objection Matrix"
#     (acknowledge/reframe/redirect pattern)
#
# ALSO SEE:
#   - examples.py -> Section 3 "BATTLE CARD SYSTEM"
#     (generate_battle_card() function, feature_comparison(),
#      generate_landmines(), generate_talking_points() -- follow same structure)
#
# Given two products' feature sets, generate a structured battle card with
# strengths, weaknesses, landmines, and talking points.
#
# Key concepts:
#   - Strengths = features you have that competitor lacks or does worse
#   - Weaknesses = features competitor has that you lack or do worse
#   - Landmines = questions to ask early that expose competitor weaknesses
#   - Talking points = key messages that position your strengths

def generate_battle_card(
    your_product: ProductFeatures,
    competitor: ProductFeatures,
) -> BattleCard:
    """Generate a competitive battle card comparing two products.

    TODO: Implement this function.

    Steps:
    1. Identify strengths (features you have that competitor doesn't):
       - For each feature in your_product.features:
         if the feature key is NOT in competitor.features: it's a strength
       - Also include your_product.strengths list items
       - Format as: "feature_name: your_description (competitor lacks this)"

    2. Identify weaknesses (features competitor has that you don't):
       - For each feature in competitor.features:
         if the feature key is NOT in your_product.features: it's a weakness
       - Format as: "feature_name: competitor_description (we lack this)"

    3. Build feature comparison table for shared features:
       - For features present in BOTH products:
         feature_comparison.append({"feature": key, "us": our_desc, "them": their_desc})

    4. Generate landmines from weaknesses of competitor:
       - For each of your strengths (features they lack):
         "Ask them to demonstrate [feature]. They don't have this capability."
       - For each shared feature where your description sounds stronger:
         "Ask for specifics on their [feature] -- probe for limitations."

    5. Generate talking points:
       - Combine your strengths with value statements
       - "Unlike [competitor], we offer [feature] which means [benefit]"
       - Include pricing comparison if pricing models differ

    Return BattleCard with all fields populated.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement generate_battle_card")


# ============================================================================
# EXERCISE 5: Sales Cycle Phase Tracker
# ============================================================================
# READ FIRST:
#   - 02-technical-sales-frameworks.md -> "The Sales Cycle (SE's View)" section
#     (stages from lead to close, what happens at each stage)
#   - 02-technical-sales-frameworks.md -> "Decision Points and Gates"
#     (criteria to pass between stages)
#   - 02-technical-sales-frameworks.md -> "POC-to-Close Motion"
#     (when POCs are necessary, success criteria, POC reports)
#
# ALSO SEE:
#   - examples.py -> Section 4 "SALES CYCLE TRACKER"
#     (EVENT_TO_PHASE mapping, determine_phase(), calculate_days_in_phase(),
#      generate_next_steps() -- follow the same event-mapping approach)
#
# Given a list of deal events, determine the current phase, confidence level,
# and recommended next actions.
#
# Key concepts:
#   - Deal phase is determined by the most recent significant event
#   - Time in phase affects confidence (too long = stalling)
#   - Next steps depend on current phase and what's been completed

# Map event types to the deal stage they indicate
EVENT_PHASE_MAP: dict[str, DealStage] = {
    "lead_created": DealStage.LEAD,
    "initial_meeting": DealStage.DISCOVERY,
    "discovery_call": DealStage.DISCOVERY,
    "technical_discovery": DealStage.DISCOVERY,
    "demo_scheduled": DealStage.DEMO,
    "demo_delivered": DealStage.DEMO,
    "poc_started": DealStage.POC,
    "poc_completed": DealStage.POC,
    "proposal_sent": DealStage.PROPOSAL,
    "proposal_reviewed": DealStage.PROPOSAL,
    "negotiation_started": DealStage.NEGOTIATION,
    "contract_sent": DealStage.NEGOTIATION,
    "verbal_agreement": DealStage.NEGOTIATION,
    "closed_won": DealStage.CLOSED_WON,
    "closed_lost": DealStage.CLOSED_LOST,
}

# Expected maximum days in each phase before the deal is considered stalling
PHASE_TIME_LIMITS: dict[DealStage, int] = {
    DealStage.LEAD: 7,
    DealStage.DISCOVERY: 21,
    DealStage.DEMO: 14,
    DealStage.POC: 42,
    DealStage.PROPOSAL: 14,
    DealStage.NEGOTIATION: 30,
}

# Recommended next steps for each phase
PHASE_NEXT_STEPS: dict[DealStage, list[str]] = {
    DealStage.LEAD: [
        "Schedule initial discovery call",
        "Research the prospect's company and tech stack",
        "Identify likely stakeholders",
    ],
    DealStage.DISCOVERY: [
        "Complete MEDDPICC scorecard",
        "Identify champion and economic buyer",
        "Schedule tailored demo based on discovered pain points",
    ],
    DealStage.DEMO: [
        "Send demo follow-up with key takeaways",
        "Propose POC if technical validation needed",
        "Get feedback from all attendees",
    ],
    DealStage.POC: [
        "Review POC success criteria status",
        "Schedule mid-POC check-in with stakeholders",
        "Prepare POC results report",
    ],
    DealStage.PROPOSAL: [
        "Review proposal with champion before sending to EB",
        "Address any open technical questions",
        "Confirm procurement timeline and paper process",
    ],
    DealStage.NEGOTIATION: [
        "Support security questionnaire completion",
        "Address any final technical objections",
        "Prepare implementation plan for post-close handoff",
    ],
}


def track_deal_phase(events: list[DealEvent]) -> DealPhase:
    """Determine the current deal phase from a list of events.

    TODO: Implement this function.

    Steps:
    1. Sort events by date (ascending)
       - events_sorted = sorted(events, key=lambda e: e.date)
    2. Determine current phase from the most recent event:
       - latest_event = events_sorted[-1]
       - current_phase = EVENT_PHASE_MAP.get(latest_event.event_type, DealStage.LEAD)
    3. Calculate days in current phase:
       - Find the earliest event that maps to the current phase
       - days = (latest_date - phase_start_date).days
       - Use datetime.strptime(date_str, "%Y-%m-%d") for parsing
    4. Calculate confidence based on time in phase:
       - time_limit = PHASE_TIME_LIMITS.get(current_phase, 30)
       - if days <= time_limit: confidence = 1.0 - (days / time_limit) * 0.3  (high)
       - if days > time_limit: confidence = max(0.2, 0.7 - (days - time_limit) * 0.02)  (decaying)
    5. Get next steps from PHASE_NEXT_STEPS for the current phase
    6. Identify risks:
       - If days > time_limit: "Deal has been in {phase} for {days} days (expected < {limit})"
       - If no discovery events found: "No discovery calls recorded"
       - If in POC phase with no success criteria event: "POC success criteria may not be defined"

    Return DealPhase with all fields populated.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement track_deal_phase")


# ============================================================================
# EXERCISE 6: Win/Loss Analyzer
# ============================================================================
# READ FIRST:
#   - 03-competitive-positioning.md -> "Win/Loss Analysis" section
#     (how to conduct retrospectives, what to track, patterns that predict
#      wins vs losses)
#   - 02-technical-sales-frameworks.md -> "Forecasting and Pipeline"
#     (technical confidence scores, when to flag deals at risk)
#   - 03-competitive-positioning.md -> "Competitive Intelligence Gathering"
#     (turning losses into product feedback)
#
# ALSO SEE:
#   - examples.py -> Section 5 "DEAL QUALIFICATION SCORER" (for scoring logic)
#   - examples.py -> Section 4 "SALES CYCLE TRACKER" (for aggregation patterns)
#
# Analyze a portfolio of deal outcomes to compute win rates, identify
# top loss reasons, and measure the impact of champions and POCs.
#
# Key concepts:
#   - Win rate alone is insufficient -- break it down by competitor and deal attributes
#   - Champion presence is the strongest predictor of deal success
#   - Loss reason patterns should drive product and process improvements

def analyze_win_loss(deals: list[DealOutcome]) -> WinLossReport:
    """Analyze a list of deal outcomes and produce a comprehensive report.

    TODO: Implement this function.

    Steps:
    1. Separate wins and losses:
       - wins = [d for d in deals if d.won]
       - losses = [d for d in deals if not d.won]

    2. Calculate basic metrics:
       - win_rate = len(wins) / len(deals) if deals else 0
       - total_revenue_won = sum(d.deal_size for d in wins)
       - total_revenue_lost = sum(d.deal_size for d in losses)
       - avg_winning_deal_size = total_revenue_won / len(wins) if wins else 0
       - avg_losing_deal_size = total_revenue_lost / len(losses) if losses else 0

    3. Calculate average cycle times:
       - avg_winning_cycle_days = mean of d.sales_cycle_days for wins
       - avg_losing_cycle_days = mean of d.sales_cycle_days for losses

    4. Aggregate loss reasons (count occurrences across all lost deals):
       - reason_counts = {}
       - for deal in losses: for reason in deal.loss_reasons: reason_counts[reason] += 1
       - Sort by count descending: top_loss_reasons = sorted list of (reason, count) tuples

    5. Aggregate win reasons similarly:
       - top_win_reasons = sorted list of (reason, count) tuples

    6. Calculate competitive win rates:
       - Group deals by competitor
       - For each competitor: win_rate = wins_against / total_against
       - competitive_win_rates = {competitor: win_rate}

    7. Calculate champion impact:
       - Deals with champion: win rate among deals where had_champion=True
       - Deals without champion: win rate among deals where had_champion=False
       - champion_impact = {"with_champion": rate1, "without_champion": rate2}

    8. Calculate POC impact:
       - Same pattern as champion impact but using had_poc
       - poc_impact = {"with_poc": rate1, "without_poc": rate2}

    Return WinLossReport with all fields populated.
    """
    # TODO: Your implementation here
    raise NotImplementedError("Implement analyze_win_loss")


# ============================================================================
# TESTS
# ============================================================================

def test_exercise_1() -> None:
    """Test the discovery call scorer."""
    print("Testing Exercise 1: Discovery Call Scorer")
    print("-" * 50)

    # Test question categorization
    assert categorize_question("What tools are you currently using?") == SPINCategory.SITUATION
    assert categorize_question("What's the most frustrating part of your workflow?") == SPINCategory.PROBLEM
    assert categorize_question("What happens if this problem isn't solved?") == SPINCategory.IMPLICATION
    assert categorize_question("How would it help if you could automate this?") == SPINCategory.NEED_PAYOFF
    print("  Question categorization: PASSED")

    # Test a well-balanced call
    good_call = [
        DiscoveryQuestion("What tools are you using today?"),                     # S
        DiscoveryQuestion("How many engineers work on this?"),                    # S
        DiscoveryQuestion("What's the most frustrating part of your workflow?"),  # P
        DiscoveryQuestion("What challenges do you face with scaling?"),           # P
        DiscoveryQuestion("Is the current solution struggling under load?"),      # P
        DiscoveryQuestion("What happens if this causes an outage?"),             # I
        DiscoveryQuestion("What's the business impact when deployments fail?"),  # I
        DiscoveryQuestion("How does that affect your team's morale?"),           # I
        DiscoveryQuestion("What does that mean for your quarterly targets?"),    # I
        DiscoveryQuestion("How would it help if deployments took 5 minutes?"),   # N
        DiscoveryQuestion("What would change if you had real-time visibility?"), # N
        DiscoveryQuestion("If you could eliminate this toil, what would your team focus on?"),  # N
    ]
    score = score_discovery_call(good_call)
    assert score.total_questions == 12
    assert score.balance_score > 0.5, f"Well-balanced call should score > 0.5, got {score.balance_score}"
    print(f"  Well-balanced call score: {score.balance_score:.2f}")
    print(f"    S={score.situation_count} P={score.problem_count} I={score.implication_count} N={score.need_payoff_count}")

    # Test a poorly-balanced call (too many Situation questions)
    bad_call = [
        DiscoveryQuestion("What tools do you use?"),
        DiscoveryQuestion("How many servers do you have?"),
        DiscoveryQuestion("What's your current architecture?"),
        DiscoveryQuestion("Who is responsible for deployments?"),
        DiscoveryQuestion("How long have you been using this tool?"),
        DiscoveryQuestion("What's your team size?"),
    ]
    bad_score = score_discovery_call(bad_call)
    assert bad_score.balance_score < score.balance_score, \
        "Situation-heavy call should score lower than balanced call"
    assert any("Situation" in f for f in bad_score.feedback), \
        "Should provide feedback about too many Situation questions"
    print(f"  Situation-heavy call score: {bad_score.balance_score:.2f}")
    print(f"    Feedback: {bad_score.feedback[0]}")

    print("  PASSED\n")


def test_exercise_2() -> None:
    """Test the MEDDPICC gap analyzer."""
    print("Testing Exercise 2: MEDDPICC Gap Analyzer")
    print("-" * 50)

    # Test a card with major gaps
    weak_card = MEDDPICCCard(
        metrics=None,
        economic_buyer=None,
        decision_criteria="Must support Kubernetes and have SOC 2",
        decision_process=None,
        paper_process=None,
        identify_pain="Engineers spend 20 hours/week on manual data reconciliation",
        champion=None,
        competition="Evaluating Competitor X and building in-house",
    )

    analysis = analyze_meddpicc(weak_card)
    assert analysis.filled_count == 3, f"Expected 3 filled, got {analysis.filled_count}"
    assert analysis.total_elements == 8
    assert len(analysis.gaps) == 5, f"Expected 5 gaps, got {len(analysis.gaps)}"
    assert analysis.overall_health in ("weak", "critical"), \
        f"Should be weak or critical with only 3/8, got {analysis.overall_health}"
    # Highest priority gap should be champion or economic_buyer (pain is filled)
    assert analysis.gaps[0].priority <= 3, "First gap should be high priority"
    print(f"  Weak card: {analysis.filled_count}/8 filled, health={analysis.overall_health}")
    print(f"  Top gap: {analysis.gaps[0].element} (priority {analysis.gaps[0].priority})")

    # Test a strong card
    strong_card = MEDDPICCCard(
        metrics="50% reduction in deployment time, $200K/year savings",
        economic_buyer="VP of Engineering, Sarah Chen",
        decision_criteria="Performance, security, Kubernetes support",
        decision_process="POC -> technical review -> exec approval -> procurement",
        paper_process="Standard MSA, 2-week security review, procurement 1 week",
        identify_pain="4-hour deployments blocking weekly releases",
        champion="Lead SRE Mike, reports to VP Eng, strong influence",
        competition="Competitor X, also evaluating OSS alternative",
    )

    strong_analysis = analyze_meddpicc(strong_card)
    assert strong_analysis.filled_count == 8
    assert strong_analysis.overall_health == "strong"
    assert len(strong_analysis.gaps) == 0
    print(f"  Strong card: {strong_analysis.filled_count}/8 filled, health={strong_analysis.overall_health}")

    print("  PASSED\n")


def test_exercise_3() -> None:
    """Test the deal qualification scorer."""
    print("Testing Exercise 3: Deal Qualification Scorer")
    print("-" * 50)

    # Test a strong deal
    strong_deal = DealAttributes(
        budget_known=True,
        budget_amount=150_000,
        authority_identified=True,
        authority_met=True,
        need_articulated=True,
        timeline_defined=True,
        timeline_months=3,
        pain_quantified=True,
        champion_identified=True,
        champion_has_power=True,
        champion_has_access=True,
        competition_known=True,
        decision_criteria_known=True,
        decision_process_mapped=True,
        paper_process_understood=True,
        metrics_defined=True,
    )

    score = score_deal(strong_deal)
    assert score.bant_score >= 0.8, f"Strong deal BANT should be >= 0.8, got {score.bant_score}"
    assert score.meddpicc_score >= 0.8, f"Strong deal MEDDPICC should be >= 0.8, got {score.meddpicc_score}"
    assert score.recommendation == Recommendation.PURSUE
    print(f"  Strong deal: BANT={score.bant_score:.2f} MEDDPICC={score.meddpicc_score:.2f}")
    print(f"    Composite={score.composite_score:.2f} -> {score.recommendation.value}")

    # Test a weak deal
    weak_deal = DealAttributes(
        budget_known=False,
        authority_identified=False,
        need_articulated=True,
        timeline_defined=False,
        pain_quantified=False,
        champion_identified=False,
        competition_known=False,
    )

    weak_score = score_deal(weak_deal)
    assert weak_score.bant_score < 0.5, f"Weak deal BANT should be < 0.5, got {weak_score.bant_score}"
    assert weak_score.recommendation in (Recommendation.QUALIFY_OUT, Recommendation.NURTURE)
    print(f"  Weak deal: BANT={weak_score.bant_score:.2f} MEDDPICC={weak_score.meddpicc_score:.2f}")
    print(f"    Composite={weak_score.composite_score:.2f} -> {weak_score.recommendation.value}")

    # Test a mid-range deal
    mid_deal = DealAttributes(
        budget_known=True,
        budget_amount=75_000,
        authority_identified=True,
        authority_met=False,
        need_articulated=True,
        timeline_defined=True,
        timeline_months=6,
        pain_quantified=True,
        champion_identified=True,
        champion_has_power=False,
        champion_has_access=False,
        competition_known=True,
        decision_criteria_known=True,
        decision_process_mapped=False,
        paper_process_understood=False,
        metrics_defined=True,
    )

    mid_score = score_deal(mid_deal)
    assert mid_score.composite_score > weak_score.composite_score, \
        "Mid deal should score higher than weak deal"
    assert mid_score.composite_score < score.composite_score, \
        "Mid deal should score lower than strong deal"
    print(f"  Mid deal: BANT={mid_score.bant_score:.2f} MEDDPICC={mid_score.meddpicc_score:.2f}")
    print(f"    Composite={mid_score.composite_score:.2f} -> {mid_score.recommendation.value}")

    print("  PASSED\n")


def test_exercise_4() -> None:
    """Test the competitive battle card generator."""
    print("Testing Exercise 4: Competitive Battle Card Generator")
    print("-" * 50)

    our_product = ProductFeatures(
        name="StreamFlow",
        features={
            "real_time_streaming": "Sub-second CDC from any database source",
            "sql_transforms": "Full SQL transformation engine in the pipeline",
            "python_transforms": "Python UDFs for custom transformation logic",
            "auto_scaling": "Automatic horizontal scaling based on throughput",
            "schema_evolution": "Automatic schema change detection and adaptation",
            "monitoring": "Built-in pipeline health dashboards",
        },
        strengths=[
            "Sub-second real-time streaming latency",
            "In-pipeline SQL and Python transformations",
            "Flat-rate pricing that scales predictably",
        ],
        pricing_model="flat-rate",
    )

    competitor = ProductFeatures(
        name="DataPipe",
        features={
            "pre_built_connectors": "300+ pre-built source and destination connectors",
            "monitoring": "Basic pipeline status monitoring",
            "scheduling": "Cron-based batch scheduling with retry logic",
            "auto_scaling": "Manual scaling configuration",
            "data_quality": "Built-in data quality checks and validation",
        },
        strengths=[
            "Largest connector catalog in the market (300+)",
            "15-minute setup for basic pipelines",
            "Built-in data quality validation",
        ],
        pricing_model="per-row",
    )

    card = generate_battle_card(our_product, competitor)

    assert card.your_product == "StreamFlow"
    assert card.competitor == "DataPipe"
    assert len(card.strengths) > 0, "Should identify at least one strength"
    assert len(card.weaknesses) > 0, "Should identify at least one weakness"
    assert len(card.landmines) > 0, "Should generate at least one landmine"
    assert len(card.talking_points) > 0, "Should generate at least one talking point"
    assert len(card.feature_comparison) > 0, "Should have feature comparisons"

    print(f"  Battle card: {card.your_product} vs {card.competitor}")
    print(f"    Strengths: {len(card.strengths)}")
    print(f"    Weaknesses: {len(card.weaknesses)}")
    print(f"    Landmines: {len(card.landmines)}")
    print(f"    Talking points: {len(card.talking_points)}")
    print(f"    Feature comparisons: {len(card.feature_comparison)}")
    if card.strengths:
        print(f"    First strength: {card.strengths[0][:80]}...")
    if card.landmines:
        print(f"    First landmine: {card.landmines[0][:80]}...")

    print("  PASSED\n")


def test_exercise_5() -> None:
    """Test the sales cycle phase tracker."""
    print("Testing Exercise 5: Sales Cycle Phase Tracker")
    print("-" * 50)

    # Test a deal in discovery phase
    events = [
        DealEvent("lead_created", "2026-01-15", "Inbound from website"),
        DealEvent("initial_meeting", "2026-01-20", "Intro call with Sarah (Data Lead)"),
        DealEvent("discovery_call", "2026-01-27", "Deep technical discovery with engineering team"),
    ]

    phase = track_deal_phase(events)
    assert phase.current_phase == DealStage.DISCOVERY, \
        f"Should be in DISCOVERY, got {phase.current_phase}"
    assert phase.events_analyzed == 3
    assert len(phase.next_steps) > 0, "Should have next steps"
    print(f"  Discovery deal: phase={phase.current_phase.value}, confidence={phase.confidence:.2f}")
    print(f"    Days in phase: {phase.days_in_phase}")
    print(f"    Next step: {phase.next_steps[0]}")

    # Test a deal in POC phase that's running long
    poc_events = [
        DealEvent("lead_created", "2025-10-01", "Outbound prospecting"),
        DealEvent("discovery_call", "2025-10-15", "Discovery with VP Eng"),
        DealEvent("demo_delivered", "2025-10-25", "Tailored demo for engineering team"),
        DealEvent("poc_started", "2025-11-01", "POC kicked off with 3 success criteria"),
    ]

    poc_phase = track_deal_phase(poc_events)
    assert poc_phase.current_phase == DealStage.POC
    # POC started on 2025-11-01, "today" should be much later, confidence should be low
    assert poc_phase.days_in_phase > 0
    print(f"  Long POC deal: phase={poc_phase.current_phase.value}, confidence={poc_phase.confidence:.2f}")
    print(f"    Days in phase: {poc_phase.days_in_phase}")
    if poc_phase.risks:
        print(f"    Risk: {poc_phase.risks[0]}")

    # Test a closed-won deal
    won_events = [
        DealEvent("lead_created", "2026-01-01", "Inbound"),
        DealEvent("discovery_call", "2026-01-10", "Discovery"),
        DealEvent("demo_delivered", "2026-01-20", "Demo"),
        DealEvent("proposal_sent", "2026-02-01", "Proposal"),
        DealEvent("closed_won", "2026-02-15", "Contract signed!"),
    ]

    won_phase = track_deal_phase(won_events)
    assert won_phase.current_phase == DealStage.CLOSED_WON
    print(f"  Won deal: phase={won_phase.current_phase.value}")

    print("  PASSED\n")


def test_exercise_6() -> None:
    """Test the win/loss analyzer."""
    print("Testing Exercise 6: Win/Loss Analyzer")
    print("-" * 50)

    deals = [
        DealOutcome("Acme Corp", won=True, deal_size=120_000, competitor="DataPipe",
                     win_reasons=["real-time capability", "better pricing"],
                     sales_cycle_days=90, had_champion=True, had_poc=True),
        DealOutcome("TechCorp", won=True, deal_size=80_000, competitor="DataPipe",
                     win_reasons=["real-time capability", "SE relationship"],
                     sales_cycle_days=60, had_champion=True, had_poc=False),
        DealOutcome("BigRetail", won=False, deal_size=200_000, competitor="DataPipe",
                     loss_reasons=["missing connectors", "incumbent advantage"],
                     sales_cycle_days=120, had_champion=False, had_poc=True),
        DealOutcome("FinServ Inc", won=True, deal_size=150_000, competitor="BuildInHouse",
                     win_reasons=["faster time to value", "better pricing"],
                     sales_cycle_days=75, had_champion=True, had_poc=True),
        DealOutcome("StartupCo", won=False, deal_size=50_000, competitor="BuildInHouse",
                     loss_reasons=["chose to build in-house", "budget constraints"],
                     sales_cycle_days=45, had_champion=False, had_poc=False),
        DealOutcome("MedTech", won=False, deal_size=90_000, competitor="DataPipe",
                     loss_reasons=["missing connectors", "lost champion"],
                     sales_cycle_days=100, had_champion=True, had_poc=True),
        DealOutcome("CloudFirst", won=True, deal_size=110_000, competitor="DataPipe",
                     win_reasons=["real-time capability", "in-pipeline transforms"],
                     sales_cycle_days=80, had_champion=True, had_poc=True),
        DealOutcome("DataDriven", won=False, deal_size=60_000, competitor="NoDecision",
                     loss_reasons=["no decision", "budget constraints"],
                     sales_cycle_days=150, had_champion=False, had_poc=False),
    ]

    report = analyze_win_loss(deals)

    assert report.total_deals == 8
    assert report.wins == 4
    assert report.losses == 4
    assert abs(report.win_rate - 0.5) < 0.01, f"Win rate should be 0.5, got {report.win_rate}"
    assert report.total_revenue_won == 460_000
    assert report.total_revenue_lost == 400_000

    print(f"  Total deals: {report.total_deals} ({report.wins}W / {report.losses}L)")
    print(f"  Win rate: {report.win_rate:.1%}")
    print(f"  Revenue won: ${report.total_revenue_won:,.0f} | lost: ${report.total_revenue_lost:,.0f}")
    print(f"  Avg winning deal: ${report.avg_winning_deal_size:,.0f} | "
          f"losing: ${report.avg_losing_deal_size:,.0f}")
    print(f"  Avg winning cycle: {report.avg_winning_cycle_days:.0f} days | "
          f"losing: {report.avg_losing_cycle_days:.0f} days")

    assert len(report.top_loss_reasons) > 0, "Should have loss reasons"
    print(f"  Top loss reason: {report.top_loss_reasons[0][0]} ({report.top_loss_reasons[0][1]} deals)")

    assert "DataPipe" in report.competitive_win_rates, "Should have DataPipe win rate"
    print(f"  Win rate vs DataPipe: {report.competitive_win_rates['DataPipe']:.1%}")

    # Champion impact
    assert report.champion_impact["with_champion"] > report.champion_impact["without_champion"], \
        "Champion should positively impact win rate"
    print(f"  Champion impact: with={report.champion_impact['with_champion']:.1%} | "
          f"without={report.champion_impact['without_champion']:.1%}")

    print("  PASSED\n")


def run_all_tests() -> None:
    """Run all exercise tests."""
    print("=" * 60)
    print("Discovery & Technical Sales -- Exercise Tests")
    print("=" * 60)
    print()

    tests = [
        ("Exercise 1: Discovery Call Scorer", test_exercise_1),
        ("Exercise 2: MEDDPICC Gap Analyzer", test_exercise_2),
        ("Exercise 3: Deal Qualification Scorer", test_exercise_3),
        ("Exercise 4: Battle Card Generator", test_exercise_4),
        ("Exercise 5: Sales Cycle Phase Tracker", test_exercise_5),
        ("Exercise 6: Win/Loss Analyzer", test_exercise_6),
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
