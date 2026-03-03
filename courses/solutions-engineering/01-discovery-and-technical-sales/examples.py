"""
Discovery & Technical Sales -- Production-Ready Code Patterns
===============================================================
These examples demonstrate core Solutions Engineering concepts using Python.
The focus is on SE processes and frameworks, not Python syntax.

Each section provides complete, runnable implementations that serve as
reference material for the corresponding exercises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 1. MEDDPICC EVALUATOR
# ---------------------------------------------------------------------------
# A complete MEDDPICC scorecard evaluator that scores each element, identifies
# gaps, and recommends actions. This is the kind of tool an SE team might build
# internally to standardize deal qualification.


class HealthStatus(Enum):
    GREEN = "green"      # Fully understood and favorable
    YELLOW = "yellow"    # Partially known, some risk
    RED = "red"          # Unknown or unfavorable


@dataclass
class MEDDPICCElement:
    """A single element of the MEDDPICC scorecard."""
    name: str                     # Human-readable name
    key: str                      # Machine key (e.g., "economic_buyer")
    description: str              # What this element captures
    value: Optional[str]          # The captured information (None if not yet gathered)
    status: HealthStatus = HealthStatus.RED
    priority: int = 1             # 1 = most critical
    suggested_questions: list[str] = field(default_factory=list)


@dataclass
class MEDDPICCScorecard:
    """Complete MEDDPICC scorecard with scoring and gap analysis."""
    deal_name: str
    elements: list[MEDDPICCElement]
    overall_score: float = 0.0    # 0.0 to 1.0
    overall_health: str = "critical"
    gaps: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)


# MEDDPICC element definitions with priority ordering and default questions
MEDDPICC_ELEMENTS: dict[str, dict[str, Any]] = {
    "metrics": {
        "name": "Metrics",
        "priority": 4,
        "description": "Quantifiable success criteria the prospect will use to measure ROI",
        "questions": [
            "What KPIs does your team get measured on?",
            "What would a successful implementation look like in numbers?",
            "How would you measure ROI on this investment?",
            "What's the current cost of this problem (in dollars, hours, or headcount)?",
        ],
    },
    "economic_buyer": {
        "name": "Economic Buyer",
        "priority": 3,
        "description": "The person with authority and budget to approve the purchase",
        "questions": [
            "Who ultimately approves purchases like this?",
            "Walk me through how your team has purchased software in the past.",
            "Is there a budget already allocated, or does someone need to create one?",
            "Have you worked with procurement before? What's their typical timeline?",
        ],
    },
    "decision_criteria": {
        "name": "Decision Criteria",
        "priority": 5,
        "description": "The specific technical and business criteria used to evaluate solutions",
        "questions": [
            "What are the must-have vs nice-to-have requirements?",
            "Are there any hard technical constraints (compliance, infrastructure)?",
            "How are you evaluating the options you're considering?",
            "What would make you say 'no' to a solution regardless of everything else?",
        ],
    },
    "decision_process": {
        "name": "Decision Process",
        "priority": 6,
        "description": "The steps and stakeholders involved from evaluation to signed contract",
        "questions": [
            "What does your evaluation process look like from here?",
            "Who else needs to be involved before a decision is made?",
            "What's your typical timeline from selecting a vendor to going live?",
            "Is there a formal RFP process, or is this more informal?",
        ],
    },
    "paper_process": {
        "name": "Paper Process",
        "priority": 8,
        "description": "Legal, procurement, security review, and contract execution steps",
        "questions": [
            "What does your procurement process look like?",
            "Is there a security review required? What does that involve?",
            "Do you use the vendor's MSA or your own?",
            "How long did the last vendor contract take from verbal approval to signature?",
        ],
    },
    "identify_pain": {
        "name": "Identify Pain",
        "priority": 1,
        "description": "The specific, concrete, emotionally resonant problem to be solved",
        "questions": [
            "What's the biggest problem this project is supposed to solve?",
            "What happens if you don't solve this in the next 6 months?",
            "On a scale of 1-10, how much is this affecting your team's productivity?",
            "Who is most affected by this problem, and how does it manifest day-to-day?",
        ],
    },
    "champion": {
        "name": "Champion",
        "priority": 2,
        "description": "Internal advocate with power, pain, and access to the economic buyer",
        "questions": [
            "Why is this important to you personally?",
            "Who else needs to be convinced? Can you help me understand their perspective?",
            "If we proved value in a POC, could you help us get in front of the decision-maker?",
            "What would make you look good internally if this project succeeded?",
        ],
    },
    "competition": {
        "name": "Competition",
        "priority": 7,
        "description": "Other vendors, open-source, or build-in-house alternatives being evaluated",
        "questions": [
            "Are you evaluating other solutions for this?",
            "Have you tried solving this with internal tooling or open-source?",
            "What do you like about the other options you've seen so far?",
            "What would make you choose to keep doing what you're doing today?",
        ],
    },
}


def evaluate_meddpicc(
    deal_name: str,
    card_data: dict[str, Optional[str]],
) -> MEDDPICCScorecard:
    """Evaluate a MEDDPICC scorecard and produce scoring, gaps, and recommendations.

    Args:
        deal_name: Name of the deal being evaluated.
        card_data: Dict mapping element keys to their captured values.
                   None or empty string means the element has not been captured.

    Returns:
        A fully scored MEDDPICCScorecard with gap analysis and recommended actions.
    """
    elements: list[MEDDPICCElement] = []
    gaps: list[str] = []
    actions: list[str] = []
    score_sum = 0.0

    for key, definition in MEDDPICC_ELEMENTS.items():
        value = card_data.get(key)
        has_value = bool(value and value.strip())

        # Determine status
        if has_value and len(value.strip()) > 20:
            status = HealthStatus.GREEN
            element_score = 1.0
        elif has_value:
            status = HealthStatus.YELLOW
            element_score = 0.5
        else:
            status = HealthStatus.RED
            element_score = 0.0

        score_sum += element_score

        element = MEDDPICCElement(
            name=definition["name"],
            key=key,
            description=definition["description"],
            value=value,
            status=status,
            priority=definition["priority"],
            suggested_questions=definition["questions"],
        )
        elements.append(element)

        if status == HealthStatus.RED:
            gaps.append(f"{definition['name']}: Not captured (priority {definition['priority']})")
            actions.append(
                f"[P{definition['priority']}] Ask: \"{definition['questions'][0]}\""
            )
        elif status == HealthStatus.YELLOW:
            gaps.append(f"{definition['name']}: Partially captured -- needs more detail")
            actions.append(
                f"[P{definition['priority']}] Deepen: \"{definition['questions'][1]}\""
            )

    # Sort actions by priority
    actions.sort(key=lambda a: int(a[2]))

    # Calculate overall score and health
    overall_score = score_sum / len(MEDDPICC_ELEMENTS)

    if overall_score >= 0.85:
        overall_health = "strong"
    elif overall_score >= 0.6:
        overall_health = "moderate"
    elif overall_score >= 0.35:
        overall_health = "weak"
    else:
        overall_health = "critical"

    # Override health if critical elements are missing
    pain_status = next(e.status for e in elements if e.key == "identify_pain")
    champion_status = next(e.status for e in elements if e.key == "champion")
    if pain_status == HealthStatus.RED or champion_status == HealthStatus.RED:
        if overall_health == "strong":
            overall_health = "moderate"

    return MEDDPICCScorecard(
        deal_name=deal_name,
        elements=elements,
        overall_score=round(overall_score, 2),
        overall_health=overall_health,
        gaps=gaps,
        recommended_actions=actions,
    )


def print_meddpicc_scorecard(scorecard: MEDDPICCScorecard) -> None:
    """Print a formatted MEDDPICC scorecard."""
    status_symbols = {
        HealthStatus.GREEN: "[GREEN ]",
        HealthStatus.YELLOW: "[YELLOW]",
        HealthStatus.RED: "[RED   ]",
    }

    print(f"\nMEDDPICC Scorecard: {scorecard.deal_name}")
    print("=" * 70)

    for element in sorted(scorecard.elements, key=lambda e: e.priority):
        symbol = status_symbols[element.status]
        value_preview = (element.value[:50] + "...") if element.value and len(element.value) > 50 else (element.value or "-- NOT CAPTURED --")
        print(f"  {symbol} {element.name:<20} {value_preview}")

    print(f"\nOverall Score: {scorecard.overall_score:.0%} | Health: {scorecard.overall_health.upper()}")

    if scorecard.gaps:
        print(f"\nGaps ({len(scorecard.gaps)}):")
        for gap in scorecard.gaps:
            print(f"  - {gap}")

    if scorecard.recommended_actions:
        print(f"\nRecommended Actions:")
        for action in scorecard.recommended_actions[:5]:
            print(f"  {action}")


# ---------------------------------------------------------------------------
# 2. DISCOVERY CALL TEMPLATE ENGINE
# ---------------------------------------------------------------------------
# Generates pre-call research checklists and call scripts based on the
# prospect's profile. Demonstrates SPIN question categorization and call
# balance scoring.


@dataclass
class ProspectProfile:
    """Information about a prospect gathered during pre-call research."""
    company_name: str
    industry: str
    company_size: str             # "startup", "mid-market", "enterprise"
    known_tech_stack: list[str]
    known_pain_signals: list[str]
    key_contacts: list[dict[str, str]]  # [{"name": ..., "title": ..., "notes": ...}]
    competitors_in_play: list[str]
    deal_size_estimate: Optional[float] = None


@dataclass
class DiscoveryCallScript:
    """A generated discovery call script with research checklist."""
    prospect: str
    research_checklist: list[str]
    intro_script: str
    situation_questions: list[str]
    problem_questions: list[str]
    implication_questions: list[str]
    need_payoff_questions: list[str]
    closing_script: str
    estimated_duration_minutes: int


# Keywords used to categorize questions into SPIN categories
SPIN_KEYWORDS: dict[str, list[str]] = {
    "situation": [
        "current", "today", "how many", "what tools", "walk me through",
        "what does your", "how long have", "who is responsible", "what's your",
        "describe your", "tell me about your current", "how do you currently",
    ],
    "problem": [
        "frustrating", "challenge", "struggle", "difficult", "pain",
        "not working", "issue", "problem", "broken", "complaint",
        "what's not", "where does it break", "what fails", "bottleneck",
    ],
    "implication": [
        "what happens if", "impact", "cost of", "consequence", "affect",
        "what does that mean for", "downstream", "risk", "if this continues",
        "what's the business impact", "how does that affect",
    ],
    "need_payoff": [
        "how would it help", "what would change", "ideal", "if you could",
        "imagine", "value", "benefit", "what would it mean if",
        "how would your team", "what would you do with", "what would be different",
    ],
}


def categorize_question(question: str) -> str:
    """Categorize a discovery question into a SPIN category.

    Uses keyword matching against the SPIN_KEYWORDS dict.
    Checks in reverse priority order (need_payoff first, situation last)
    because more specific categories should take precedence.
    """
    question_lower = question.lower()

    # Check in priority order (most specific first)
    for category in ["need_payoff", "implication", "problem", "situation"]:
        for keyword in SPIN_KEYWORDS[category]:
            if keyword in question_lower:
                return category

    return "unknown"


def score_call_balance(
    situation: int, problem: int, implication: int, need_payoff: int,
) -> tuple[float, list[str]]:
    """Score the SPIN balance of a discovery call.

    Returns a tuple of (score, feedback_items).
    Score is 0.0 to 1.0 where 1.0 is the ideal balance.

    Ideal distribution (from Rackham's research):
    - Situation: 10-15% (necessary but low-value)
    - Problem: 25-30% (surface pain)
    - Implication: 30-35% (quantify impact -- most valuable)
    - Need-payoff: 20-25% (let prospect articulate value)
    """
    total = situation + problem + implication + need_payoff
    if total == 0:
        return 0.0, ["No questions recorded."]

    s_pct = situation / total
    p_pct = problem / total
    i_pct = implication / total
    n_pct = need_payoff / total

    # Ideal midpoints
    ideals = {"S": 0.125, "P": 0.275, "I": 0.325, "N": 0.25}
    actuals = {"S": s_pct, "P": p_pct, "I": i_pct, "N": n_pct}

    # Score = 1.0 - sum of absolute deviations (clamped)
    total_deviation = sum(abs(actuals[k] - ideals[k]) for k in ideals)
    score = max(0.0, min(1.0, 1.0 - total_deviation))

    feedback = []

    if s_pct > 0.30:
        feedback.append(
            f"Too many Situation questions ({s_pct:.0%}). Do more pre-call research "
            f"to reduce these. Aim for < 15%."
        )
    if i_pct == 0:
        feedback.append(
            "No Implication questions asked. These are the most valuable -- they quantify "
            "the business impact of the prospect's pain."
        )
    if n_pct == 0:
        feedback.append(
            "No Need-payoff questions asked. Let the prospect articulate the value of "
            "solving their problem in their own words."
        )
    if i_pct > 0.25 and n_pct > 0.15:
        feedback.append(
            "Good balance of Implication and Need-payoff questions. This indicates "
            "a mature discovery conversation."
        )
    if total < 5:
        feedback.append(
            f"Only {total} questions recorded. Aim for 10-15 questions in a 30-minute "
            f"discovery call."
        )
    if p_pct > 0.15 and i_pct > 0.15:
        feedback.append(
            "Good progression from Problem to Implication questions -- this shows "
            "you're digging beyond surface pain."
        )

    return round(score, 2), feedback


def generate_discovery_script(prospect: ProspectProfile) -> DiscoveryCallScript:
    """Generate a complete discovery call script based on the prospect's profile.

    Uses pre-call research to minimize Situation questions and focus on
    Problem, Implication, and Need-payoff questions.
    """
    research_checklist = [
        f"[ ] Review {prospect.company_name}'s website and 'About' page",
        f"[ ] Check LinkedIn profiles for: {', '.join(c['name'] for c in prospect.key_contacts)}",
        f"[ ] Search for {prospect.company_name} engineering blog posts",
        f"[ ] Check recent job postings for technology signals",
        f"[ ] Review CRM history for prior interactions",
    ]

    if prospect.deal_size_estimate and prospect.deal_size_estimate > 100_000:
        research_checklist.append(
            f"[ ] Review 10-K or annual report (if public company)"
        )

    if prospect.competitors_in_play:
        research_checklist.append(
            f"[ ] Review battle cards for: {', '.join(prospect.competitors_in_play)}"
        )

    # Build tailored intro
    intro = (
        f"Thank you for making the time today. I'm looking forward to learning "
        f"about what {prospect.company_name} is working on.\n\n"
        f"Before I share anything about us, I'd love to spend most of our time "
        f"understanding your situation and challenges. Would it be okay if I ask "
        f"a few questions? That way I can make sure anything we discuss is "
        f"directly relevant to your priorities."
    )

    # Situation questions (keep minimal -- pre-research should cover basics)
    situation_qs = [
        f"I noticed from your blog that you're using {prospect.known_tech_stack[0] if prospect.known_tech_stack else 'several tools'}. "
        f"Can you walk me through how that fits into your broader architecture?",
    ]

    # Problem questions (tailored to known pain signals)
    problem_qs = []
    for signal in prospect.known_pain_signals[:3]:
        problem_qs.append(
            f"You mentioned {signal}. Can you tell me more about what that "
            f"looks like day to day? What's the most frustrating part?"
        )
    problem_qs.append(
        "If you could change one thing about your current workflow, what would it be?"
    )

    # Implication questions
    implication_qs = [
        "When that problem occurs, what's the downstream impact on your team?",
        "What does this cost you in terms of engineering time or customer experience?",
        "If this isn't solved in the next 6 months, what happens to your roadmap?",
        "How does this affect your team's ability to ship new features?",
    ]

    # Need-payoff questions
    need_payoff_qs = [
        "If you could solve this problem completely, what would that free your team to work on?",
        "How would it help if this process took minutes instead of hours?",
        "What would it mean for your business if you had real-time visibility into this?",
    ]

    # Closing
    closing = (
        "Let me play back what I think I heard to make sure I understood correctly...\n\n"
        "[Summarize the top 2-3 pain points and their business impact]\n\n"
        "Of everything we discussed, which of these is the most important to solve first?\n\n"
        "Based on what you've shared, I think it would be valuable for me to put together "
        "a tailored walkthrough focused specifically on [their top pain point]. "
        "I could bring in [relevant team member] and show you exactly how we'd approach "
        "this. Would next Tuesday or Wednesday work for that?"
    )

    return DiscoveryCallScript(
        prospect=prospect.company_name,
        research_checklist=research_checklist,
        intro_script=intro,
        situation_questions=situation_qs,
        problem_questions=problem_qs,
        implication_questions=implication_qs,
        need_payoff_questions=need_payoff_qs,
        closing_script=closing,
        estimated_duration_minutes=35,
    )


def print_discovery_script(script: DiscoveryCallScript) -> None:
    """Print a formatted discovery call script."""
    print(f"\nDiscovery Call Script: {script.prospect}")
    print(f"Estimated Duration: {script.estimated_duration_minutes} minutes")
    print("=" * 70)

    print("\nPRE-CALL RESEARCH CHECKLIST:")
    for item in script.research_checklist:
        print(f"  {item}")

    print(f"\nINTRO (2-3 minutes):")
    print(f"  {script.intro_script}")

    print(f"\nSITUATION QUESTIONS (minimal -- 2-3 minutes):")
    for q in script.situation_questions:
        print(f"  [S] {q}")

    print(f"\nPROBLEM QUESTIONS (8-10 minutes):")
    for q in script.problem_questions:
        print(f"  [P] {q}")

    print(f"\nIMPLICATION QUESTIONS (10-12 minutes):")
    for q in script.implication_questions:
        print(f"  [I] {q}")

    print(f"\nNEED-PAYOFF QUESTIONS (5-7 minutes):")
    for q in script.need_payoff_questions:
        print(f"  [N] {q}")

    print(f"\nCLOSING (3-5 minutes):")
    print(f"  {script.closing_script}")


# ---------------------------------------------------------------------------
# 3. BATTLE CARD SYSTEM
# ---------------------------------------------------------------------------
# Complete battle card builder with feature comparison, objection responses,
# and landmine generation. Demonstrates competitive positioning patterns.


@dataclass
class FeatureComparison:
    """Side-by-side comparison of a single feature."""
    feature_name: str
    our_capability: str
    their_capability: str
    advantage: str                # "us", "them", "tie"
    talking_point: str


@dataclass
class ObjectionResponse:
    """A structured response to a competitive objection."""
    objection: str
    acknowledge: str
    reframe: str
    redirect: str


@dataclass
class CompleteBattleCard:
    """Full battle card with all competitive intelligence."""
    our_product: str
    competitor: str
    last_updated: str
    overview: str
    where_we_win: list[str]
    where_they_win: list[str]
    feature_comparisons: list[FeatureComparison]
    landmines: list[str]
    objection_responses: list[ObjectionResponse]
    customer_wins: list[str]
    key_differentiators: list[str]


def generate_battle_card(
    our_product: str,
    our_features: dict[str, str],
    our_strengths: list[str],
    competitor: str,
    their_features: dict[str, str],
    their_strengths: list[str],
) -> CompleteBattleCard:
    """Generate a complete battle card comparing two products.

    Analyzes feature overlap, identifies strengths and weaknesses,
    generates landmines and talking points.
    """
    # Feature comparison
    all_features = set(our_features.keys()) | set(their_features.keys())
    comparisons: list[FeatureComparison] = []

    where_we_win: list[str] = []
    where_they_win: list[str] = []

    for feature in sorted(all_features):
        ours = our_features.get(feature)
        theirs = their_features.get(feature)

        if ours and not theirs:
            advantage = "us"
            where_we_win.append(f"{feature}: {ours} (they lack this)")
            talking_point = f"Ask about their {feature} capability -- they don't have one."
        elif theirs and not ours:
            advantage = "them"
            where_they_win.append(f"{feature}: {theirs} (we lack this)")
            talking_point = f"If they raise {feature}, acknowledge and redirect to our strengths."
        else:
            advantage = "tie"
            talking_point = f"Both products offer {feature}. Probe for specifics to differentiate."

        comparisons.append(FeatureComparison(
            feature_name=feature,
            our_capability=ours or "Not available",
            their_capability=theirs or "Not available",
            advantage=advantage,
            talking_point=talking_point,
        ))

    # Add explicit strengths
    for strength in our_strengths:
        if strength not in where_we_win:
            where_we_win.append(strength)

    # Generate landmines (questions that expose competitor weaknesses)
    landmines: list[str] = []
    for comp in comparisons:
        if comp.advantage == "us":
            landmines.append(
                f"Ask them to demonstrate {comp.feature_name}. "
                f"Our capability: {comp.our_capability}. They don't have this."
            )

    # Generate objection responses for their strengths
    objection_responses: list[ObjectionResponse] = []
    for strength in their_strengths:
        objection_responses.append(ObjectionResponse(
            objection=f"Prospect says: '{competitor} has {strength}'",
            acknowledge=f"That's true -- {strength} is a genuine strength of theirs.",
            reframe=f"The question is how much that matters for your specific use case.",
            redirect=f"What I'd focus on is whether {strength} addresses your core problem, "
                     f"or whether our approach gets you there more effectively.",
        ))

    return CompleteBattleCard(
        our_product=our_product,
        competitor=competitor,
        last_updated=datetime.now().strftime("%Y-%m-%d"),
        overview=f"Comparison of {our_product} vs {competitor}. "
                 f"We have advantages in {len(where_we_win)} areas; "
                 f"they have advantages in {len(where_they_win)} areas.",
        where_we_win=where_we_win,
        where_they_win=where_they_win,
        feature_comparisons=comparisons,
        landmines=landmines,
        objection_responses=objection_responses,
        customer_wins=[
            f"[Reference Customer] switched from {competitor} due to [reason]",
        ],
        key_differentiators=[s for s in our_strengths[:3]],
    )


def print_battle_card(card: CompleteBattleCard) -> None:
    """Print a formatted battle card."""
    print(f"\nBATTLE CARD: {card.our_product} vs {card.competitor}")
    print(f"Last Updated: {card.last_updated}")
    print("=" * 70)

    print(f"\nOVERVIEW:")
    print(f"  {card.overview}")

    print(f"\nWHERE WE WIN ({len(card.where_we_win)}):")
    for item in card.where_we_win:
        print(f"  + {item}")

    print(f"\nWHERE THEY WIN ({len(card.where_they_win)}):")
    for item in card.where_they_win:
        print(f"  - {item}")

    print(f"\nFEATURE COMPARISON:")
    print(f"  {'Feature':<25} {'Us':<30} {'Them':<30}")
    print(f"  {'-'*85}")
    for comp in card.feature_comparisons:
        marker = ">>>" if comp.advantage == "us" else ("<<<" if comp.advantage == "them" else "   ")
        print(f"  {comp.feature_name:<25} {comp.our_capability[:28]:<30} {comp.their_capability[:28]:<30} {marker}")

    print(f"\nLANDMINES TO PLANT ({len(card.landmines)}):")
    for i, landmine in enumerate(card.landmines, 1):
        print(f"  {i}. {landmine}")

    print(f"\nOBJECTION RESPONSES ({len(card.objection_responses)}):")
    for resp in card.objection_responses:
        print(f"\n  Objection: {resp.objection}")
        print(f"  Acknowledge: {resp.acknowledge}")
        print(f"  Reframe: {resp.reframe}")
        print(f"  Redirect: {resp.redirect}")


# ---------------------------------------------------------------------------
# 4. SALES CYCLE TRACKER
# ---------------------------------------------------------------------------
# Deal progression tracker with phase detection, time-in-phase analysis,
# and next-step recommendations. Demonstrates how to model a deal's
# lifecycle programmatically.


class DealStage(Enum):
    LEAD = "lead"
    DISCOVERY = "discovery"
    DEMO = "demo"
    POC = "poc"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


# Ordered stages for progression comparison
STAGE_ORDER: list[DealStage] = [
    DealStage.LEAD,
    DealStage.DISCOVERY,
    DealStage.DEMO,
    DealStage.POC,
    DealStage.PROPOSAL,
    DealStage.NEGOTIATION,
    DealStage.CLOSED_WON,
]

# Map event types to the deal stage they indicate
EVENT_TO_PHASE: dict[str, DealStage] = {
    "lead_created": DealStage.LEAD,
    "initial_meeting": DealStage.DISCOVERY,
    "discovery_call": DealStage.DISCOVERY,
    "technical_discovery": DealStage.DISCOVERY,
    "demo_scheduled": DealStage.DEMO,
    "demo_delivered": DealStage.DEMO,
    "poc_started": DealStage.POC,
    "poc_milestone": DealStage.POC,
    "poc_completed": DealStage.POC,
    "proposal_sent": DealStage.PROPOSAL,
    "proposal_reviewed": DealStage.PROPOSAL,
    "negotiation_started": DealStage.NEGOTIATION,
    "contract_sent": DealStage.NEGOTIATION,
    "verbal_agreement": DealStage.NEGOTIATION,
    "closed_won": DealStage.CLOSED_WON,
    "closed_lost": DealStage.CLOSED_LOST,
}

# Expected maximum days in each phase
PHASE_LIMITS: dict[DealStage, int] = {
    DealStage.LEAD: 7,
    DealStage.DISCOVERY: 21,
    DealStage.DEMO: 14,
    DealStage.POC: 42,
    DealStage.PROPOSAL: 14,
    DealStage.NEGOTIATION: 30,
}

# Next steps for each phase
RECOMMENDED_NEXT_STEPS: dict[DealStage, list[str]] = {
    DealStage.LEAD: [
        "Schedule initial discovery call within 5 business days",
        "Research prospect's company, tech stack, and key contacts",
        "Prepare pre-call research checklist",
    ],
    DealStage.DISCOVERY: [
        "Complete MEDDPICC scorecard after each call",
        "Identify and validate champion (power, pain, access)",
        "Schedule tailored demo based on discovered pain points",
        "Share discovery summary with AE for alignment",
    ],
    DealStage.DEMO: [
        "Send demo follow-up email within 24 hours",
        "Capture attendee feedback and questions",
        "Propose POC if technical validation is needed",
        "If no POC needed, move to proposal discussion",
    ],
    DealStage.POC: [
        "Confirm success criteria document is signed by both sides",
        "Schedule weekly check-ins with prospect's technical team",
        "Prepare mid-POC status update for stakeholders",
        "Draft POC results report template",
    ],
    DealStage.PROPOSAL: [
        "Review proposal with champion before formal submission",
        "Complete security questionnaire if required",
        "Confirm procurement timeline and paper process steps",
        "Address any remaining technical objections",
    ],
    DealStage.NEGOTIATION: [
        "Support AE with technical justification for pricing",
        "Prepare implementation plan for post-close handoff",
        "Complete any outstanding security/compliance requirements",
        "Draft CS handoff document with technical context",
    ],
}


@dataclass
class DealEvent:
    """An event in a deal's lifecycle."""
    event_type: str
    date: str                     # ISO format YYYY-MM-DD
    description: str
    participants: list[str] = field(default_factory=list)


@dataclass
class DealTracker:
    """Tracked state of a deal."""
    deal_name: str
    current_phase: DealStage
    phase_start_date: datetime
    days_in_phase: int
    confidence: float
    events: list[DealEvent]
    next_steps: list[str]
    risks: list[str]
    phase_history: list[tuple[DealStage, str]]  # (stage, date_entered)


def determine_phase(events: list[DealEvent]) -> tuple[DealStage, datetime]:
    """Determine the current deal phase from events.

    Returns the current phase and the date it was entered.
    """
    if not events:
        return DealStage.LEAD, datetime.now()

    # Sort by date
    sorted_events = sorted(events, key=lambda e: e.date)

    # Find the most advanced stage reached
    current_phase = DealStage.LEAD
    phase_date = datetime.strptime(sorted_events[0].date, "%Y-%m-%d")

    for event in sorted_events:
        mapped_phase = EVENT_TO_PHASE.get(event.event_type, DealStage.LEAD)

        # Check if this is a progression (later stage)
        if mapped_phase in STAGE_ORDER:
            mapped_idx = STAGE_ORDER.index(mapped_phase)
            current_idx = STAGE_ORDER.index(current_phase) if current_phase in STAGE_ORDER else -1

            if mapped_idx >= current_idx:
                if mapped_phase != current_phase:
                    phase_date = datetime.strptime(event.date, "%Y-%m-%d")
                current_phase = mapped_phase
        elif mapped_phase == DealStage.CLOSED_LOST:
            current_phase = DealStage.CLOSED_LOST
            phase_date = datetime.strptime(event.date, "%Y-%m-%d")

    return current_phase, phase_date


def calculate_confidence(phase: DealStage, days_in_phase: int) -> float:
    """Calculate deal confidence based on time in current phase.

    Confidence starts high and decays as the deal exceeds expected timelines.
    """
    if phase in (DealStage.CLOSED_WON, DealStage.CLOSED_LOST):
        return 1.0 if phase == DealStage.CLOSED_WON else 0.0

    limit = PHASE_LIMITS.get(phase, 30)

    if days_in_phase <= limit:
        # Normal timeline: confidence between 0.7 and 1.0
        return round(1.0 - (days_in_phase / limit) * 0.3, 2)
    else:
        # Over limit: decaying confidence
        overage = days_in_phase - limit
        return round(max(0.2, 0.7 - overage * 0.02), 2)


def track_deal(deal_name: str, events: list[DealEvent]) -> DealTracker:
    """Track a deal's current state and recommend next actions."""
    current_phase, phase_start = determine_phase(events)
    today = datetime.now()
    days_in_phase = (today - phase_start).days

    confidence = calculate_confidence(current_phase, days_in_phase)
    next_steps = RECOMMENDED_NEXT_STEPS.get(current_phase, [])

    # Identify risks
    risks: list[str] = []
    limit = PHASE_LIMITS.get(current_phase, 30)

    if days_in_phase > limit:
        risks.append(
            f"Deal has been in {current_phase.value} phase for {days_in_phase} days "
            f"(expected max {limit} days). Risk of stalling."
        )

    # Check for missing discovery
    event_types = {e.event_type for e in events}
    if current_phase in (DealStage.DEMO, DealStage.POC) and "discovery_call" not in event_types:
        risks.append("No discovery call recorded. Demo/POC without discovery risks poor fit.")

    # Check for progression gaps
    if current_phase == DealStage.POC and "demo_delivered" not in event_types:
        risks.append("POC started without a recorded demo. Ensure stakeholder alignment.")

    # Build phase history
    sorted_events = sorted(events, key=lambda e: e.date)
    phase_history: list[tuple[DealStage, str]] = []
    seen_phases: set[DealStage] = set()

    for event in sorted_events:
        phase = EVENT_TO_PHASE.get(event.event_type, DealStage.LEAD)
        if phase not in seen_phases:
            phase_history.append((phase, event.date))
            seen_phases.add(phase)

    return DealTracker(
        deal_name=deal_name,
        current_phase=current_phase,
        phase_start_date=phase_start,
        days_in_phase=days_in_phase,
        confidence=confidence,
        events=events,
        next_steps=next_steps,
        risks=risks,
        phase_history=phase_history,
    )


def print_deal_tracker(tracker: DealTracker) -> None:
    """Print a formatted deal tracker."""
    print(f"\nDeal Tracker: {tracker.deal_name}")
    print("=" * 70)

    print(f"  Current Phase: {tracker.current_phase.value.upper()}")
    print(f"  Days in Phase: {tracker.days_in_phase}")
    print(f"  Confidence:    {tracker.confidence:.0%}")

    print(f"\n  Phase History:")
    for phase, date in tracker.phase_history:
        print(f"    {date}  {phase.value}")

    if tracker.next_steps:
        print(f"\n  Next Steps:")
        for step in tracker.next_steps:
            print(f"    [ ] {step}")

    if tracker.risks:
        print(f"\n  Risks:")
        for risk in tracker.risks:
            print(f"    !! {risk}")


# ---------------------------------------------------------------------------
# 5. DEAL QUALIFICATION SCORER
# ---------------------------------------------------------------------------
# Multi-framework qualification scoring with BANT and MEDDPICC, composite
# weighting, and recommendation engine.


@dataclass
class QualificationInput:
    """Input attributes for deal qualification scoring."""
    # BANT elements
    budget_known: bool = False
    budget_amount: Optional[float] = None
    authority_identified: bool = False
    authority_met: bool = False
    need_articulated: bool = False
    timeline_defined: bool = False
    timeline_months: Optional[int] = None

    # MEDDPICC-specific elements
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
class FrameworkScore:
    """Score for a single qualification framework."""
    framework: str
    total_score: float            # 0.0 to 1.0
    element_scores: dict[str, float]
    strengths: list[str]
    weaknesses: list[str]


@dataclass
class QualificationResult:
    """Complete qualification assessment."""
    bant: FrameworkScore
    meddpicc: FrameworkScore
    composite_score: float
    recommendation: str           # "pursue", "nurture", "qualify_out"
    reasoning: str
    priority_actions: list[str]


def score_bant(attrs: QualificationInput) -> FrameworkScore:
    """Score a deal against the BANT framework."""
    scores: dict[str, float] = {}

    # Budget
    if attrs.budget_known and attrs.budget_amount and attrs.budget_amount > 0:
        scores["budget"] = 1.0
    elif attrs.budget_known:
        scores["budget"] = 0.5
    else:
        scores["budget"] = 0.0

    # Authority
    if attrs.authority_met:
        scores["authority"] = 1.0
    elif attrs.authority_identified:
        scores["authority"] = 0.5
    else:
        scores["authority"] = 0.0

    # Need
    if attrs.need_articulated and attrs.pain_quantified:
        scores["need"] = 1.0
    elif attrs.need_articulated:
        scores["need"] = 0.5
    else:
        scores["need"] = 0.0

    # Timeline
    if attrs.timeline_defined and attrs.timeline_months and attrs.timeline_months <= 6:
        scores["timeline"] = 1.0
    elif attrs.timeline_defined:
        scores["timeline"] = 0.5
    else:
        scores["timeline"] = 0.0

    total = sum(scores.values()) / len(scores)

    strengths = [k for k, v in scores.items() if v >= 0.8]
    weaknesses = [k for k, v in scores.items() if v <= 0.3]

    return FrameworkScore(
        framework="BANT",
        total_score=round(total, 2),
        element_scores=scores,
        strengths=strengths,
        weaknesses=weaknesses,
    )


def score_meddpicc(attrs: QualificationInput) -> FrameworkScore:
    """Score a deal against the MEDDPICC framework."""
    scores: dict[str, float] = {}

    # Metrics
    if attrs.metrics_defined and attrs.pain_quantified:
        scores["metrics"] = 1.0
    elif attrs.metrics_defined:
        scores["metrics"] = 0.5
    else:
        scores["metrics"] = 0.0

    # Economic Buyer
    if attrs.authority_met:
        scores["economic_buyer"] = 1.0
    elif attrs.authority_identified:
        scores["economic_buyer"] = 0.5
    else:
        scores["economic_buyer"] = 0.0

    # Decision Criteria
    scores["decision_criteria"] = 1.0 if attrs.decision_criteria_known else 0.0

    # Decision Process
    scores["decision_process"] = 1.0 if attrs.decision_process_mapped else 0.0

    # Paper Process
    scores["paper_process"] = 1.0 if attrs.paper_process_understood else 0.0

    # Identify Pain
    if attrs.pain_quantified:
        scores["identify_pain"] = 1.0
    elif attrs.need_articulated:
        scores["identify_pain"] = 0.5
    else:
        scores["identify_pain"] = 0.0

    # Champion
    if attrs.champion_identified and attrs.champion_has_power and attrs.champion_has_access:
        scores["champion"] = 1.0
    elif attrs.champion_identified:
        scores["champion"] = 0.5
    else:
        scores["champion"] = 0.0

    # Competition
    scores["competition"] = 1.0 if attrs.competition_known else 0.0

    total = sum(scores.values()) / len(scores)

    strengths = [k for k, v in scores.items() if v >= 0.8]
    weaknesses = [k for k, v in scores.items() if v <= 0.3]

    return FrameworkScore(
        framework="MEDDPICC",
        total_score=round(total, 2),
        element_scores=scores,
        strengths=strengths,
        weaknesses=weaknesses,
    )


def qualify_deal(attrs: QualificationInput) -> QualificationResult:
    """Run full qualification scoring across both frameworks."""
    bant = score_bant(attrs)
    meddpicc = score_meddpicc(attrs)

    # Composite: weight MEDDPICC higher (more comprehensive)
    composite = round(0.3 * bant.total_score + 0.7 * meddpicc.total_score, 2)

    # Recommendation
    if composite >= 0.7:
        recommendation = "pursue"
        reasoning = (
            f"Strong qualification (composite {composite:.0%}). "
            f"BANT: {bant.total_score:.0%}, MEDDPICC: {meddpicc.total_score:.0%}. "
            f"Strengths: {', '.join(meddpicc.strengths)}."
        )
    elif composite >= 0.4:
        recommendation = "nurture"
        reasoning = (
            f"Moderate qualification (composite {composite:.0%}). "
            f"Gaps to address: {', '.join(meddpicc.weaknesses)}. "
            f"Invest in filling gaps before committing significant SE resources."
        )
    else:
        recommendation = "qualify_out"
        reasoning = (
            f"Weak qualification (composite {composite:.0%}). "
            f"Critical gaps: {', '.join(meddpicc.weaknesses)}. "
            f"Consider qualifying out or deferring until gaps can be addressed."
        )

    # Priority actions based on weakest MEDDPICC elements
    priority_actions: list[str] = []
    for element, score in sorted(meddpicc.element_scores.items(), key=lambda x: x[1]):
        if score < 0.5:
            element_def = MEDDPICC_ELEMENTS.get(element, {})
            questions = element_def.get("questions", [])
            if questions:
                priority_actions.append(f"Fill {element}: Ask \"{questions[0]}\"")

    return QualificationResult(
        bant=bant,
        meddpicc=meddpicc,
        composite_score=composite,
        recommendation=recommendation,
        reasoning=reasoning,
        priority_actions=priority_actions[:5],
    )


def print_qualification(result: QualificationResult) -> None:
    """Print a formatted qualification assessment."""
    print(f"\nDeal Qualification Assessment")
    print("=" * 70)

    print(f"\n  BANT Score: {result.bant.total_score:.0%}")
    for elem, score in result.bant.element_scores.items():
        bar = "#" * int(score * 10) + "." * (10 - int(score * 10))
        print(f"    {elem:<15} [{bar}] {score:.0%}")

    print(f"\n  MEDDPICC Score: {result.meddpicc.total_score:.0%}")
    for elem, score in result.meddpicc.element_scores.items():
        bar = "#" * int(score * 10) + "." * (10 - int(score * 10))
        print(f"    {elem:<20} [{bar}] {score:.0%}")

    print(f"\n  Composite Score: {result.composite_score:.0%}")
    print(f"  Recommendation: {result.recommendation.upper()}")
    print(f"  Reasoning: {result.reasoning}")

    if result.priority_actions:
        print(f"\n  Priority Actions:")
        for action in result.priority_actions:
            print(f"    -> {action}")


# ---------------------------------------------------------------------------
# DEMO / MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("Discovery & Technical Sales -- Code Examples")
    print("=" * 70)

    # --- 1. MEDDPICC Evaluator ---
    print("\n\n1. MEDDPICC EVALUATOR")
    print("-" * 40)

    scorecard = evaluate_meddpicc(
        deal_name="Acme Corp - Data Pipeline Platform",
        card_data={
            "metrics": None,
            "economic_buyer": "VP Eng, Sarah Chen",
            "decision_criteria": "Must support Kubernetes, SOC 2, sub-second latency",
            "decision_process": None,
            "paper_process": None,
            "identify_pain": "Engineers spend 20 hours/week on manual data reconciliation, blocking feature development",
            "champion": "Lead SRE Mike Rodriguez -- strong influence, reports to VP Eng",
            "competition": "Evaluating DataPipe and considering building in-house",
        },
    )
    print_meddpicc_scorecard(scorecard)

    # --- 2. Discovery Call Template Engine ---
    print("\n\n2. DISCOVERY CALL TEMPLATE ENGINE")
    print("-" * 40)

    prospect = ProspectProfile(
        company_name="TechCorp",
        industry="SaaS / Developer Tools",
        company_size="mid-market",
        known_tech_stack=["Kubernetes", "PostgreSQL", "Kafka", "Python"],
        known_pain_signals=[
            "deployment takes 4+ hours",
            "frequent production incidents on Fridays",
            "data team waiting on engineering for pipeline changes",
        ],
        key_contacts=[
            {"name": "Sarah Chen", "title": "VP Engineering", "notes": "Decision maker"},
            {"name": "Mike Rodriguez", "title": "Lead SRE", "notes": "Potential champion"},
            {"name": "Lisa Park", "title": "Data Engineering Lead", "notes": "End user"},
        ],
        competitors_in_play=["DataPipe"],
        deal_size_estimate=120_000,
    )

    script = generate_discovery_script(prospect)
    print_discovery_script(script)

    # Score a sample call
    print("\n\n  CALL BALANCE SCORING:")
    score, feedback = score_call_balance(
        situation=2, problem=3, implication=4, need_payoff=3,
    )
    print(f"  Score: {score:.0%}")
    for item in feedback:
        print(f"  - {item}")

    # --- 3. Battle Card System ---
    print("\n\n3. BATTLE CARD SYSTEM")
    print("-" * 40)

    card = generate_battle_card(
        our_product="StreamFlow",
        our_features={
            "real_time_streaming": "Sub-second CDC from any database",
            "sql_transforms": "Full SQL transformation engine in-pipeline",
            "python_transforms": "Python UDFs for custom logic",
            "auto_scaling": "Automatic horizontal scaling on throughput",
            "schema_evolution": "Auto schema change detection and adaptation",
            "monitoring": "Built-in pipeline health dashboards",
        },
        our_strengths=[
            "Sub-second real-time streaming latency",
            "In-pipeline transformations (SQL + Python)",
            "Flat-rate pricing that scales predictably",
        ],
        competitor="DataPipe",
        their_features={
            "pre_built_connectors": "300+ pre-built connectors",
            "monitoring": "Basic pipeline status monitoring",
            "scheduling": "Cron-based batch scheduling with retries",
            "auto_scaling": "Manual scaling configuration",
            "data_quality": "Built-in data quality checks",
        },
        their_strengths=[
            "Largest connector catalog (300+)",
            "15-minute setup for simple pipelines",
            "Built-in data quality validation",
        ],
    )
    print_battle_card(card)

    # --- 4. Sales Cycle Tracker ---
    print("\n\n4. SALES CYCLE TRACKER")
    print("-" * 40)

    events = [
        DealEvent("lead_created", "2026-01-15", "Inbound from website form"),
        DealEvent("initial_meeting", "2026-01-20", "Intro call with Sarah and Mike",
                  participants=["Sarah Chen", "Mike Rodriguez"]),
        DealEvent("discovery_call", "2026-01-27",
                  "Deep technical discovery -- identified deployment pain",
                  participants=["Mike Rodriguez", "Lisa Park"]),
        DealEvent("demo_delivered", "2026-02-05",
                  "Tailored demo focused on real-time pipeline and auto-scaling",
                  participants=["Sarah Chen", "Mike Rodriguez", "Lisa Park"]),
        DealEvent("poc_started", "2026-02-12",
                  "POC kicked off with 3 success criteria defined"),
    ]

    tracker = track_deal("Acme Corp", events)
    print_deal_tracker(tracker)

    # --- 5. Deal Qualification Scorer ---
    print("\n\n5. DEAL QUALIFICATION SCORER")
    print("-" * 40)

    result = qualify_deal(QualificationInput(
        budget_known=True,
        budget_amount=120_000,
        authority_identified=True,
        authority_met=False,
        need_articulated=True,
        timeline_defined=True,
        timeline_months=4,
        pain_quantified=True,
        champion_identified=True,
        champion_has_power=True,
        champion_has_access=True,
        competition_known=True,
        decision_criteria_known=True,
        decision_process_mapped=False,
        paper_process_understood=False,
        metrics_defined=True,
    ))
    print_qualification(result)


if __name__ == "__main__":
    main()
