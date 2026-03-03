"""
Module 03: Technical Communication & Stakeholders -- Exercises

Skeleton functions with TODOs. Implement each function following the docstrings.
Test your implementations by running this file: python exercises.py

Reference files in this directory:
  - 01-audience-adapted-communication.md  (audience hierarchy, executive comms, whiteboard, elevator pitch)
  - 02-technical-writing-for-customers.md  (architecture docs, integration guides, exec summaries, RFPs, emails)
  - 03-stakeholder-management.md          (stakeholder mapping, champions, blockers, multi-threading)
  - examples.py                           (runnable reference implementations)

Difficulty ratings:
  [1] Foundational -- should be quick for experienced communicators
  [2] Intermediate -- requires understanding of audience and stakeholder dynamics
  [3] Advanced -- requires synthesis of multiple communication strategies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

class AudienceLevel(Enum):
    EXECUTIVE = "executive"
    TECHNICAL_LEADER = "technical_leader"
    DEVELOPER = "developer"
    BUSINESS_STAKEHOLDER = "business_stakeholder"
    END_USER = "end_user"


class StakeholderRole(Enum):
    CHAMPION = "champion"
    COACH = "coach"
    BLOCKER = "blocker"
    ECONOMIC_BUYER = "economic_buyer"
    TECHNICAL_EVALUATOR = "technical_evaluator"


class ComplianceStatus(Enum):
    FULLY_SUPPORTED = "F"
    PARTIALLY_SUPPORTED = "P"
    ROADMAP = "R"
    INTEGRATION = "I"
    NOT_SUPPORTED = "N"


class MeetingType(Enum):
    DISCOVERY = "discovery"
    DEMO = "demo"
    POC_CHECKIN = "poc_checkin"


@dataclass
class AdaptedMessage:
    """A message adapted for a specific audience level."""
    audience: AudienceLevel
    adapted_text: str
    key_points: list[str]
    vocabulary_level: str   # e.g. "Business -- zero jargon", "Deep technical"
    framing: str            # What the message leads with


@dataclass
class ExecutiveSummary:
    """A 1-page executive summary stripped of technical jargon."""
    title: str
    challenge: str           # Business problem in customer's terms
    solution: str            # Proposed solution (non-technical language)
    outcomes: list[str]      # Quantified expected outcomes
    timeline: list[str]      # Phased timeline
    investment: str          # Pricing / investment
    next_steps: list[str]    # Concrete next steps with owners


@dataclass
class ArchitectureDoc:
    """A structured architecture document."""
    title: str
    overview: str
    component_diagram_mermaid: str   # Mermaid syntax for component diagram
    data_flow_mermaid: str           # Mermaid syntax for data flow
    integration_points: list[dict]   # Each has 'system', 'method', 'auth', 'notes'
    security_notes: list[str]
    scaling_notes: list[str]


@dataclass
class StakeholderMap:
    """A complete stakeholder map with classifications and strategies."""
    stakeholders: list[dict]    # Each has 'name', 'title', 'role', 'power', 'interest',
                                #   'disposition', 'strategy'
    coverage_summary: str       # Text summary of relationship coverage
    risks: list[str]            # Identified risks in stakeholder coverage
    recommended_actions: list[str]  # Next actions to improve coverage


@dataclass
class RFPResponse:
    """A complete RFP response with compliance matrix."""
    responses: list[dict]       # Each has 'req_id', 'requirement', 'status', 'response', 'evidence'
    compliance_matrix: str      # Formatted compliance matrix text
    summary: dict               # Counts by status: {'F': n, 'P': n, 'R': n, 'I': n, 'N': n}
    overall_score: float        # Weighted compliance score (0.0 - 1.0)


@dataclass
class FollowUpEmail:
    """A professional follow-up email."""
    subject: str
    greeting: str
    body_sections: list[dict]   # Each has 'heading' and 'content'
    action_items: list[dict]    # Each has 'owner', 'action', 'deadline'
    closing: str
    full_text: str              # The complete email as a single string


# ============================================================================
# EXERCISE 1: Audience Adapter [1]
#
# READ FIRST:
#   01-audience-adapted-communication.md
#     -> "## The Communication Hierarchy" (audience table and vocabulary ladder)
#     -> "## Executive Communication" (3-minute rule, "so what?" test)
#     -> "## Developer Communication" (what developers want, code-first approach)
#
# ALSO SEE:
#   examples.py
#     -> "1. AUDIENCE-LEVEL COMMUNICATION SAMPLES" (AUDIENCE_ADAPTATIONS dict)
#     -> adapt_message() function (jargon_to_business mapping)
# ============================================================================

# Jargon-to-business translation map. Use this in your implementation.
JARGON_TO_BUSINESS: dict[str, str] = {
    "API": "automated connection",
    "REST API": "standard web interface",
    "SDK": "pre-built integration library",
    "microservices": "modular components",
    "Kubernetes": "cloud infrastructure management",
    "SSO": "single login with existing credentials",
    "SAML": "enterprise single sign-on",
    "OAuth": "secure login protocol",
    "webhook": "real-time notification",
    "ETL": "automated data processing",
    "CI/CD": "automated deployment",
    "containerized": "cloud-ready",
    "event-driven": "real-time automated",
    "latency": "response time",
    "throughput": "processing capacity",
    "horizontal scaling": "handles more volume without changes",
    "idempotent": "processes each item exactly once",
    "99.99% uptime": "less than 1 hour of downtime per year",
}


def adapt_for_audience(
    technical_concept: str,
    audience: AudienceLevel,
    customer_context: str = "",
) -> AdaptedMessage:
    """Adapt a technical concept description for a specific audience level.

    The core SE skill: same product, different framing for every person in the room.

    Args:
        technical_concept: Raw technical description (e.g., "Our platform uses
            event-driven architecture with exactly-once delivery guarantees
            for asynchronous data processing via REST API.")
        audience: The target audience level
        customer_context: Optional context (e.g., "healthcare company, 5M transactions/month")

    Returns:
        AdaptedMessage with adapted text, key points, vocabulary level, and framing.

    Rules by audience:
        EXECUTIVE:
            - Replace ALL jargon using JARGON_TO_BUSINESS map
            - Lead with business impact (cost, time, risk)
            - vocabulary_level = "Business -- zero jargon"
            - framing = "Business impact and outcomes"
            - key_points should focus on: revenue/cost, time savings, risk reduction
        TECHNICAL_LEADER:
            - Keep technical terms but add context (architecture fit, scale)
            - vocabulary_level = "Technical-conceptual"
            - framing = "Architecture fit and scalability"
            - key_points: architecture, security, scalability, operational requirements
        DEVELOPER:
            - Add code context: "See API docs" or "curl command available"
            - vocabulary_level = "Deep technical -- code-level"
            - framing = "Code first, then operational details"
            - key_points: SDK/API, code samples, rate limits, error handling
        BUSINESS_STAKEHOLDER:
            - Replace jargon, connect to workflow improvement
            - vocabulary_level = "Mixed -- domain terms, no engineering jargon"
            - framing = "Workflow and KPI improvement"
            - key_points: workflow improvement, time savings, team impact
        END_USER:
            - Simplest language, focus on daily experience
            - vocabulary_level = "Non-technical -- outcome-only"
            - framing = "Daily experience improvement"
            - key_points: ease of use, personal workflow benefit

    TODO: Implement this function.

    Step-by-step:
        1. If audience is EXECUTIVE or BUSINESS_STAKEHOLDER or END_USER,
           iterate over JARGON_TO_BUSINESS and replace all matches in technical_concept
        2. For EXECUTIVE: prepend customer_context framing if provided
           (e.g., "For your team: ...")
        3. For DEVELOPER: append "\\n\\nSee API documentation for implementation details."
        4. Set vocabulary_level, framing, and key_points based on the rules above
        5. Return an AdaptedMessage with all fields populated
    """
    raise NotImplementedError("Implement adapt_for_audience()")


# ============================================================================
# EXERCISE 2: Executive Summary Writer [2]
#
# READ FIRST:
#   02-technical-writing-for-customers.md
#     -> "## Executive Summaries" (1-pager structure, include/exclude table)
#     -> "### Avoiding Technical Jargon" (jargon-to-business table)
#
# ALSO SEE:
#   examples.py
#     -> "3. EXECUTIVE SUMMARY GENERATOR" (generate_executive_summary, strip_jargon)
#     -> format_executive_summary() (formatting output)
# ============================================================================

def write_executive_summary(
    customer_name: str,
    project_name: str,
    problem_description: str,
    solution_components: list[str],
    integration_details: list[str],
    expected_outcomes: list[dict],
    timeline_weeks: int,
    phases: list[dict],
    investment: str,
) -> ExecutiveSummary:
    """Generate a 1-page executive summary from a technical proposal.

    Takes raw technical input and produces a business-focused document that
    can go to the person who signs the check.

    Args:
        customer_name: e.g., "Acme Financial Services"
        project_name: e.g., "Real-Time Fraud Detection Platform"
        problem_description: Technical description of the problem
            (may contain jargon that needs to be stripped)
        solution_components: List of technical solution components
            (e.g., ["REST API integration for transaction scoring",
                    "ML model with sub-100ms latency via gRPC"])
        integration_details: Technical integration specifics
            (these should NOT appear in the exec summary)
        expected_outcomes: List of dicts with 'metric' and 'value'
            (e.g., [{"metric": "Fraud losses", "value": "Reduced 40%"}])
        timeline_weeks: Total timeline in weeks
        phases: List of dicts with 'phase' (int), 'duration' (str), 'description' (str)
        investment: Pricing string

    Returns:
        ExecutiveSummary with all jargon stripped and business framing applied.

    TODO: Implement this function.

    Step-by-step:
        1. Strip jargon from problem_description using JARGON_TO_BUSINESS map
        2. Build the solution text from solution_components:
           - Strip jargon from each component
           - Join into a paragraph (do NOT include integration_details --
             those are too technical for the exec summary)
        3. Format outcomes as "metric: value" strings
        4. Format timeline phases, stripping jargon from descriptions
        5. Build next_steps: at minimum, include a kickoff meeting and
           a data/access provisioning step
        6. Return ExecutiveSummary with title = "Executive Summary: {project_name} for {customer_name}"
    """
    raise NotImplementedError("Implement write_executive_summary()")


# ============================================================================
# EXERCISE 3: Architecture Doc Generator [2]
#
# READ FIRST:
#   02-technical-writing-for-customers.md
#     -> "## Architecture Documents" (full structure template)
#     -> "### Mermaid Diagram Examples" (component, data flow, deployment diagrams)
#     -> "### Writing Tips for Architecture Documents"
#
# ALSO SEE:
#   examples.py
#     -> "4. TECHNICAL BRIEF TEMPLATE" (generate_architecture_doc)
#     -> format_architecture_doc() (Mermaid output formatting)
# ============================================================================

def generate_architecture_document(
    project_name: str,
    overview: str,
    components: list[dict],
    data_flows: list[dict],
    integration_points: list[dict],
    security_requirements: list[str],
    scaling_requirements: list[str],
) -> ArchitectureDoc:
    """Generate a structured architecture document with Mermaid diagrams.

    Args:
        project_name: Name of the project/initiative
        overview: High-level overview paragraph
        components: List of dicts with:
            - 'name': str (component name)
            - 'type': str ('customer' | 'product' | 'external')
            - 'description': str
        data_flows: List of dicts with:
            - 'from': str (source component name, must match a component name)
            - 'to': str (destination component name)
            - 'protocol': str (e.g., "REST/TLS", "gRPC", "S3 Export")
            - 'description': str
        integration_points: List of dicts with:
            - 'system': str
            - 'method': str
            - 'auth': str
            - 'notes': str
        security_requirements: List of security note strings
        scaling_requirements: List of scaling note strings

    Returns:
        ArchitectureDoc with generated Mermaid diagrams.

    TODO: Implement this function.

    Step-by-step for component_diagram_mermaid:
        1. Start with "graph LR"
        2. For each component, create a node:
           - Customer components: N0[Component Name]  (square brackets)
           - Product components: N1(Component Name)    (round brackets)
           - External components: N2[/Component Name/] (trapezoid)
        3. For each data_flow, create an arrow:
           N0 -->|protocol| N1
        4. Use a dict to map component names to node IDs (N0, N1, ...)

    Step-by-step for data_flow_mermaid:
        1. Start with "sequenceDiagram"
        2. Add participant lines for each unique component in data_flows
           (strip spaces from names for aliases)
        3. For each flow, add: FromAlias->>ToAlias: description

    Assemble the ArchitectureDoc with both diagrams, plus the raw
    integration_points, security, and scaling lists.
    """
    raise NotImplementedError("Implement generate_architecture_document()")


# ============================================================================
# EXERCISE 4: Stakeholder Mapper [2]
#
# READ FIRST:
#   03-stakeholder-management.md
#     -> "## Stakeholder Mapping" (power/interest grid, roles table)
#     -> "## Building Champions" (champion signals, the champion test)
#     -> "## Handling Blockers" (blocker types and strategies)
#
# ALSO SEE:
#   examples.py
#     -> "2. STAKEHOLDER ANALYSIS ENGINE" (classify_stakeholder, signal lists)
#     -> analyze_stakeholder_map() (full mapping pipeline)
#     -> generate_strategy() (strategy generation per role)
# ============================================================================

# Signal patterns for classification. Match observed behaviors against these.
CHAMPION_SIGNALS = [
    "asks how to help move forward",
    "shares internal information proactively",
    "suggests meetings with other stakeholders",
    "asks about roadmap",
    "defends the product in group settings",
    "provides competitive intelligence",
    "asks for materials to share internally",
]

BLOCKER_SIGNALS = [
    "raises same objection repeatedly",
    "delays meetings or evaluations",
    "champions a competing product",
    "questions the need for any solution",
    "requests excessive documentation",
    "does not respond to follow-ups",
    "escalates minor issues",
]

COACH_SIGNALS = [
    "answers questions honestly",
    "warns about internal obstacles",
    "explains decision process",
    "shares organizational chart info",
    "is helpful but does not advocate",
]

BUYER_SIGNALS = [
    "asks about pricing",
    "discusses budget availability",
    "mentions procurement process",
    "asks about contract terms",
    "references other vendor evaluations",
]

EVALUATOR_SIGNALS = [
    "asks detailed technical questions",
    "requests sandbox access",
    "runs benchmarks or tests",
    "asks about API limits and edge cases",
    "wants to see error handling",
]


def map_stakeholders(
    contacts: list[dict],
) -> StakeholderMap:
    """Analyze contacts and produce a stakeholder map with strategies.

    Takes a list of contacts with observed behavioral signals, classifies
    each by role, and generates engagement strategies.

    Args:
        contacts: List of dicts with:
            - 'name': str
            - 'title': str
            - 'power': int (1-5, organizational influence)
            - 'interest': int (1-5, engagement level with the deal)
            - 'disposition': str ('positive', 'neutral', 'negative')
            - 'signals': list[str] (observed behaviors, e.g.,
                ["asks about pricing", "mentions procurement process"])

    Returns:
        StakeholderMap with:
            - stakeholders: classified list with strategies
            - coverage_summary: text describing coverage across org levels
            - risks: identified gaps (e.g., "No executive sponsor identified")
            - recommended_actions: next steps to improve coverage

    TODO: Implement this function.

    Step-by-step:
        1. For each contact, classify their role:
           - Score each signal against CHAMPION_SIGNALS, BLOCKER_SIGNALS, etc.
           - Use substring matching: if a known signal phrase appears in
             (or is contained by) the observed signal, score +1 for that role
           - Assign the role with the highest score (default to COACH if tied at 0)
        2. Generate a strategy string for each stakeholder based on their role:
           - CHAMPION: nurture with materials, ROI data, early access
           - COACH: maintain as info source, respect boundaries
           - BLOCKER: address concerns directly, 1:1 engagement
           - ECONOMIC_BUYER: executive materials, ROI, 3-minute rule
           - TECHNICAL_EVALUATOR: sandbox access, code samples, honest limitations
        3. Build coverage_summary: count stakeholders by role
        4. Identify risks:
           - No champion? Risk: "No champion identified -- deal is at risk"
           - No economic buyer? Risk: "No economic buyer engaged"
           - All contacts at same org level? Risk: "Single-level threading"
        5. Recommend actions based on risks
    """
    raise NotImplementedError("Implement map_stakeholders()")


# ============================================================================
# EXERCISE 5: RFP Response Builder [3]
#
# READ FIRST:
#   02-technical-writing-for-customers.md
#     -> "## RFP/RFI Responses" (compliance matrix, status codes)
#     -> "### How to Answer 'Does Your Product Support X?' Honestly"
#     -> "### Tips for Winning RFPs"
#
# ALSO SEE:
#   examples.py
#     -> "5. RFP RESPONSE SYSTEM" (assess_capability, process_rfp)
#     -> format_compliance_matrix() (output formatting)
# ============================================================================

def build_rfp_response(
    requirements: list[dict],
    capabilities: dict[str, dict],
) -> RFPResponse:
    """Process RFP requirements against product capabilities and produce a response.

    Args:
        requirements: List of RFP requirements, each a dict with:
            - 'id': str (e.g., "T-001")
            - 'text': str (the requirement statement)
            - 'weight': float (importance weight, 0.0-1.0, for scoring)

        capabilities: Dict mapping capability keywords to capability info:
            - Key: keyword that might appear in requirements (e.g., "SAML", "REST API")
            - Value: dict with:
                - 'status': str -- one of "full", "partial", "roadmap",
                                   "integration", "not_supported"
                - 'response': str -- detailed response text
                - 'evidence': str -- supporting evidence (doc links, certs, etc.)
                - 'timeline': str -- for roadmap items, when it will be available

    Returns:
        RFPResponse with:
            - responses: list of response dicts for each requirement
            - compliance_matrix: formatted text table
            - summary: dict with counts per status code
            - overall_score: weighted compliance score (F=1.0, P=0.7, R=0.3, I=0.5, N=0.0)

    TODO: Implement this function.

    Step-by-step:
        1. For each requirement, find the best matching capability:
           - Check if any capability keyword appears in the requirement text
             (case-insensitive)
           - If multiple match, use the longest keyword (most specific)
           - If no match, default to "partial" with a generic response
        2. Map the capability status to a ComplianceStatus enum:
           "full" -> FULLY_SUPPORTED, "partial" -> PARTIALLY_SUPPORTED, etc.
        3. Build each response dict with:
           'req_id', 'requirement', 'status' (ComplianceStatus value),
           'response', 'evidence'
        4. Build the compliance_matrix string:
           Header: "Req ID | Status | Requirement | Response"
           One line per requirement
        5. Build summary: count each status
        6. Calculate overall_score:
           Score each requirement: status_weight * requirement_weight
           Where status weights are: F=1.0, P=0.7, R=0.3, I=0.5, N=0.0
           overall_score = sum(scores) / sum(weights)
    """
    raise NotImplementedError("Implement build_rfp_response()")


# ============================================================================
# EXERCISE 6: Meeting Follow-up Composer [3]
#
# READ FIRST:
#   02-technical-writing-for-customers.md
#     -> "## Email Communication" (all 4 email templates)
#   01-audience-adapted-communication.md
#     -> "## Adapting in Real-Time" (audience awareness in follow-ups)
#   03-stakeholder-management.md
#     -> "## Internal Stakeholder Management" (RACI context for action items)
#
# ALSO SEE:
#   examples.py
#     -> "1. AUDIENCE-LEVEL COMMUNICATION SAMPLES" (tone/vocabulary adaptation)
#     -> "3. EXECUTIVE SUMMARY GENERATOR" (strip_jargon for exec emails)
# ============================================================================

def compose_follow_up(
    meeting_type: MeetingType,
    customer_name: str,
    attendees: list[dict],
    key_discussion_points: list[str],
    action_items: list[dict],
    open_questions: list[str] | None = None,
    next_meeting_proposal: str | None = None,
) -> FollowUpEmail:
    """Generate a professional follow-up email for a customer meeting.

    Args:
        meeting_type: Type of meeting (DISCOVERY, DEMO, or POC_CHECKIN)
        customer_name: Name of the customer company
        attendees: List of dicts with 'name' and 'title'
        key_discussion_points: Main topics discussed
            (e.g., ["Current architecture uses Kafka for event streaming",
                    "Pain point: 24-hour delay in fraud detection"])
        action_items: List of dicts with:
            - 'owner': str (person or company responsible)
            - 'action': str (what needs to be done)
            - 'deadline': str (target date)
        open_questions: Questions that need follow-up
        next_meeting_proposal: Suggested date/time/topic for next meeting

    Returns:
        FollowUpEmail with subject, greeting, structured body sections,
        action items, closing, and full_text.

    Email structure by meeting type:

        DISCOVERY:
            Subject: "{customer_name} + [Your Company] -- Discovery Follow-Up"
            Body sections:
                1. "Understanding of Current State" -- summarize discussion points
                2. "Proposed Next Step" -- recommend demo or architecture session
            Tone: consultative, confirming understanding

        DEMO:
            Subject: "{customer_name} Demo Follow-Up -- Next Steps"
            Body sections:
                1. "What We Demonstrated" -- summarize what was shown
                2. "Open Questions" -- list questions with status
                3. "Attachments and Resources" -- mention any docs to attach
            Tone: confident, reinforcing value shown

        POC_CHECKIN:
            Subject: "{customer_name} POC -- Status Update"
            Body sections:
                1. "Progress This Period" -- summarize completed items
                2. "Success Criteria Tracker" -- reference criteria status
                3. "Blockers" -- list any blockers, or state "None"
                4. "Next Steps" -- planned work for next period
            Tone: structured, progress-oriented

    TODO: Implement this function.

    Step-by-step:
        1. Set subject line based on meeting_type
        2. Build greeting: "Hi {first_name}," using first attendee
        3. Build body_sections based on meeting_type:
           - Each section is a dict with 'heading' and 'content'
           - Content is built from key_discussion_points, formatted as bullet points
        4. Format action_items with owner, action, and deadline
        5. Build closing with next_meeting_proposal if provided
        6. Assemble full_text by joining all parts:
           Subject line, greeting, body sections, action items, closing, signature
    """
    raise NotImplementedError("Implement compose_follow_up()")


# ============================================================================
# Tests
# ============================================================================

def run_tests() -> None:
    """Run all exercise tests."""
    print("=" * 60)
    print("Module 03: Technical Communication & Stakeholders -- Tests")
    print("=" * 60)

    # --- Test Exercise 1: Audience Adapter ---
    print("\n--- Exercise 1: Audience Adapter ---")
    try:
        concept = (
            "Our platform uses event-driven architecture with exactly-once "
            "delivery guarantees for asynchronous data processing via REST API. "
            "The system supports horizontal scaling with 99.99% uptime."
        )

        # Test executive adaptation
        exec_msg = adapt_for_audience(concept, AudienceLevel.EXECUTIVE)
        assert isinstance(exec_msg, AdaptedMessage), "Should return AdaptedMessage"
        assert exec_msg.audience == AudienceLevel.EXECUTIVE
        assert exec_msg.vocabulary_level == "Business -- zero jargon"
        # Verify jargon was stripped
        assert "REST API" not in exec_msg.adapted_text, "Executive text should not contain 'REST API'"
        assert "horizontal scaling" not in exec_msg.adapted_text, (
            "Executive text should not contain 'horizontal scaling'"
        )
        assert len(exec_msg.key_points) >= 2, "Should have at least 2 key points"

        # Test developer adaptation
        dev_msg = adapt_for_audience(concept, AudienceLevel.DEVELOPER)
        assert dev_msg.audience == AudienceLevel.DEVELOPER
        assert dev_msg.vocabulary_level == "Deep technical -- code-level"
        assert "API" in dev_msg.adapted_text or "doc" in dev_msg.adapted_text.lower(), (
            "Developer text should reference API or documentation"
        )

        # Test that different audiences produce different output
        biz_msg = adapt_for_audience(concept, AudienceLevel.BUSINESS_STAKEHOLDER)
        assert biz_msg.adapted_text != dev_msg.adapted_text, (
            "Business and developer messages should differ"
        )

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # --- Test Exercise 2: Executive Summary Writer ---
    print("\n--- Exercise 2: Executive Summary Writer ---")
    try:
        summary = write_executive_summary(
            customer_name="Acme Corp",
            project_name="Data Pipeline Modernization",
            problem_description=(
                "Current ETL pipeline uses batch processing with a CI/CD pipeline "
                "that deploys to Kubernetes. Latency is 24 hours for data freshness."
            ),
            solution_components=[
                "Real-time event-driven data processing via REST API",
                "Managed ETL pipeline with sub-second latency",
                "Dashboard with SSO integration via SAML",
            ],
            integration_details=[
                "mTLS authentication between services",
                "gRPC for internal service communication",
                "Kafka Connect for CDC streams",
            ],
            expected_outcomes=[
                {"metric": "Data freshness", "value": "From 24 hours to under 1 minute"},
                {"metric": "Manual processing", "value": "Eliminated (saves 20 hours/week)"},
            ],
            timeline_weeks=8,
            phases=[
                {"phase": 1, "duration": "Weeks 1-2", "description": "REST API integration setup"},
                {"phase": 2, "duration": "Weeks 3-6", "description": "ETL pipeline migration"},
                {"phase": 3, "duration": "Weeks 7-8", "description": "SSO and dashboard rollout"},
            ],
            investment="$120,000/year",
        )

        assert isinstance(summary, ExecutiveSummary), "Should return ExecutiveSummary"
        assert "Acme Corp" in summary.title
        # Verify jargon was stripped from challenge
        assert "ETL" not in summary.challenge or "automated data processing" in summary.challenge, (
            "Jargon should be stripped or translated in challenge"
        )
        # Verify integration_details are NOT in the solution
        assert "mTLS" not in summary.solution, "Integration details should not appear in exec summary"
        assert "gRPC" not in summary.solution, "Integration details should not appear in exec summary"
        assert len(summary.outcomes) == 2, "Should have 2 outcomes"
        assert len(summary.timeline) >= 3, "Should have at least 3 timeline phases"
        assert len(summary.next_steps) >= 2, "Should have at least 2 next steps"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # --- Test Exercise 3: Architecture Doc Generator ---
    print("\n--- Exercise 3: Architecture Doc Generator ---")
    try:
        doc = generate_architecture_document(
            project_name="Acme Integration",
            overview="Integration of Acme's payment system with our fraud detection platform.",
            components=[
                {"name": "Payment Gateway", "type": "customer", "description": "Processes transactions"},
                {"name": "Fraud API", "type": "product", "description": "Scoring endpoint"},
                {"name": "ML Engine", "type": "product", "description": "Model inference"},
                {"name": "Okta", "type": "external", "description": "Identity provider"},
            ],
            data_flows=[
                {"from": "Payment Gateway", "to": "Fraud API", "protocol": "REST/TLS", "description": "Score request"},
                {"from": "Fraud API", "to": "ML Engine", "protocol": "gRPC", "description": "Inference call"},
                {"from": "Fraud API", "to": "Payment Gateway", "protocol": "REST/TLS", "description": "Score response"},
            ],
            integration_points=[
                {"system": "Payment Gateway", "method": "REST API", "auth": "mTLS", "notes": "Sync call in transaction path"},
            ],
            security_requirements=["TLS 1.3 for all data in transit", "AES-256 at rest"],
            scaling_requirements=["Supports 10K TPS", "Auto-scaling enabled"],
        )

        assert isinstance(doc, ArchitectureDoc), "Should return ArchitectureDoc"
        assert "Acme Integration" in doc.title

        # Verify Mermaid component diagram
        assert "graph LR" in doc.component_diagram_mermaid, "Should start with 'graph LR'"
        assert "Payment Gateway" in doc.component_diagram_mermaid, "Should include component names"
        assert "REST/TLS" in doc.component_diagram_mermaid, "Should include protocol labels"

        # Verify Mermaid data flow diagram
        assert "sequenceDiagram" in doc.data_flow_mermaid, "Should start with 'sequenceDiagram'"
        assert "participant" in doc.data_flow_mermaid, "Should include participant declarations"

        # Verify other fields passed through
        assert len(doc.integration_points) == 1
        assert len(doc.security_notes) == 2
        assert len(doc.scaling_notes) == 2

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # --- Test Exercise 4: Stakeholder Mapper ---
    print("\n--- Exercise 4: Stakeholder Mapper ---")
    try:
        contacts = [
            {
                "name": "Sarah Chen",
                "title": "VP Engineering",
                "power": 5,
                "interest": 3,
                "disposition": "neutral",
                "signals": ["asks about pricing", "discusses budget availability"],
            },
            {
                "name": "James Park",
                "title": "Sr. Staff Engineer",
                "power": 3,
                "interest": 5,
                "disposition": "positive",
                "signals": [
                    "asks how to help move forward",
                    "shares internal information proactively",
                    "suggests meetings with other stakeholders",
                ],
            },
            {
                "name": "Maria Lopez",
                "title": "CISO",
                "power": 4,
                "interest": 3,
                "disposition": "negative",
                "signals": [
                    "raises same objection repeatedly",
                    "requests excessive documentation",
                ],
            },
        ]

        result = map_stakeholders(contacts)
        assert isinstance(result, StakeholderMap), "Should return StakeholderMap"
        assert len(result.stakeholders) == 3, "Should have 3 stakeholders"

        # Find each stakeholder and check classification
        by_name = {s["name"]: s for s in result.stakeholders}

        assert by_name["Sarah Chen"]["role"] == StakeholderRole.ECONOMIC_BUYER.value, (
            "Sarah (pricing signals) should be classified as economic buyer"
        )
        assert by_name["James Park"]["role"] == StakeholderRole.CHAMPION.value, (
            "James (help/share/suggest signals) should be classified as champion"
        )
        assert by_name["Maria Lopez"]["role"] == StakeholderRole.BLOCKER.value, (
            "Maria (objection/delay signals) should be classified as blocker"
        )

        # Check that strategies exist
        for s in result.stakeholders:
            assert len(s["strategy"]) > 0, f"Strategy missing for {s['name']}"

        # Check risks and coverage
        assert isinstance(result.risks, list)
        assert isinstance(result.coverage_summary, str)
        assert len(result.coverage_summary) > 0

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # --- Test Exercise 5: RFP Response Builder ---
    print("\n--- Exercise 5: RFP Response Builder ---")
    try:
        requirements = [
            {"id": "T-001", "text": "Must support SAML 2.0 SSO", "weight": 1.0},
            {"id": "T-002", "text": "Must provide REST API for integration", "weight": 0.8},
            {"id": "T-003", "text": "Must support on-premises deployment", "weight": 0.6},
            {"id": "T-004", "text": "Must support air-gapped environments", "weight": 0.4},
        ]

        capabilities = {
            "SAML": {
                "status": "full",
                "response": "Native SAML 2.0 SSO with metadata exchange. Supports Okta, Azure AD, OneLogin.",
                "evidence": "See docs.acme.com/sso",
                "timeline": "",
            },
            "REST API": {
                "status": "full",
                "response": "Full REST API with OpenAPI 3.0 spec. SDKs for Python, Java, Go, Node.js.",
                "evidence": "See docs.acme.com/api",
                "timeline": "",
            },
            "on-premises": {
                "status": "partial",
                "response": "Partial support via containerized deployment. Requires outbound connectivity.",
                "evidence": "Deployment guide available",
                "timeline": "",
            },
            "air-gapped": {
                "status": "not_supported",
                "response": "Not supported. Product requires outbound internet. VPC peering available as alternative.",
                "evidence": "",
                "timeline": "",
            },
        }

        result = build_rfp_response(requirements, capabilities)
        assert isinstance(result, RFPResponse), "Should return RFPResponse"
        assert len(result.responses) == 4, "Should have 4 responses"

        # Check individual statuses
        by_id = {r["req_id"]: r for r in result.responses}
        assert by_id["T-001"]["status"] == ComplianceStatus.FULLY_SUPPORTED.value
        assert by_id["T-003"]["status"] == ComplianceStatus.PARTIALLY_SUPPORTED.value
        assert by_id["T-004"]["status"] == ComplianceStatus.NOT_SUPPORTED.value

        # Check summary
        assert result.summary["F"] >= 2, "Should have at least 2 fully supported"
        assert result.summary["N"] >= 1, "Should have at least 1 not supported"

        # Check overall score is between 0 and 1
        assert 0.0 <= result.overall_score <= 1.0, f"Score should be 0-1, got {result.overall_score}"
        # Score should not be perfect (we have a "not supported" item)
        assert result.overall_score < 1.0, "Score should be less than 1.0 given N items"

        # Check compliance matrix is a non-empty string
        assert len(result.compliance_matrix) > 0, "Compliance matrix should not be empty"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    # --- Test Exercise 6: Meeting Follow-up Composer ---
    print("\n--- Exercise 6: Meeting Follow-up Composer ---")
    try:
        # Test discovery follow-up
        email = compose_follow_up(
            meeting_type=MeetingType.DISCOVERY,
            customer_name="Acme Corp",
            attendees=[
                {"name": "Sarah Chen", "title": "VP Engineering"},
                {"name": "James Park", "title": "Sr. Staff Engineer"},
            ],
            key_discussion_points=[
                "Current system processes 5M transactions/month",
                "Pain point: 24-hour delay in fraud detection",
                "Using Kafka for event streaming, PostgreSQL for storage",
            ],
            action_items=[
                {"owner": "Us", "action": "Send architecture proposal", "deadline": "March 10"},
                {"owner": "Acme", "action": "Provide sample transaction data", "deadline": "March 12"},
            ],
            open_questions=["What is the compliance review timeline?"],
            next_meeting_proposal="March 14 at 2pm for demo of fraud detection workflow",
        )

        assert isinstance(email, FollowUpEmail), "Should return FollowUpEmail"
        assert "Acme Corp" in email.subject, "Subject should include customer name"
        assert "Discovery" in email.subject or "discovery" in email.subject.lower(), (
            "Discovery follow-up subject should mention discovery"
        )
        assert "Sarah" in email.greeting, "Greeting should use first attendee's first name"
        assert len(email.body_sections) >= 2, "Should have at least 2 body sections"
        assert len(email.action_items) == 2, "Should have 2 action items"
        assert len(email.full_text) > 100, "Full text should be substantial"

        # Verify action items are in full text
        assert "March 10" in email.full_text, "Action item deadline should appear in full text"
        assert "March 12" in email.full_text, "Action item deadline should appear in full text"

        # Test demo follow-up
        demo_email = compose_follow_up(
            meeting_type=MeetingType.DEMO,
            customer_name="Beta Inc",
            attendees=[{"name": "Alex Rivera", "title": "CTO"}],
            key_discussion_points=[
                "Demonstrated real-time fraud scoring",
                "Showed SSO integration with Okta",
            ],
            action_items=[
                {"owner": "Us", "action": "Send API documentation", "deadline": "March 15"},
            ],
        )
        assert "Beta Inc" in demo_email.subject
        assert "Demo" in demo_email.subject or "demo" in demo_email.subject.lower()

        # Test POC check-in
        poc_email = compose_follow_up(
            meeting_type=MeetingType.POC_CHECKIN,
            customer_name="Gamma LLC",
            attendees=[{"name": "Jordan Lee", "title": "Lead Engineer"}],
            key_discussion_points=[
                "Completed API integration milestone",
                "ML model accuracy at 94% on test data",
            ],
            action_items=[
                {"owner": "Gamma", "action": "Provide production traffic sample", "deadline": "March 20"},
            ],
        )
        assert "Gamma LLC" in poc_email.subject
        assert "POC" in poc_email.subject or "Status" in poc_email.subject

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")

    print("\n" + "=" * 60)
    print("Tests complete. Implement the exercises and re-run!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
