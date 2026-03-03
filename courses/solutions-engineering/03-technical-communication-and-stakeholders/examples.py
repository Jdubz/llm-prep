"""
Module 03: Technical Communication & Stakeholders -- Complete, Runnable Patterns

Demonstrates audience adaptation, stakeholder analysis, executive summary
generation, architecture document templating, and RFP response processing.
No external dependencies -- all examples are self-contained and use standard
library only.

Each section is self-contained. Read top-to-bottom or jump to specific patterns.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Shared types and utilities
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


@dataclass
class AdaptedMessage:
    """A message adapted for a specific audience."""
    audience: AudienceLevel
    text: str
    key_points: list[str]
    vocabulary_level: str
    framing: str  # What angle the message leads with


@dataclass
class Stakeholder:
    """A person involved in a deal."""
    name: str
    title: str
    role: StakeholderRole
    power: int          # 1-5
    interest: int       # 1-5
    disposition: str    # positive, neutral, negative
    signals: list[str]  # Observed behaviors
    strategy: str = ""


@dataclass
class ExecutiveSummary:
    """A 1-page executive summary."""
    title: str
    challenge: str
    solution: str
    outcomes: list[str]
    timeline: list[str]
    investment: str
    next_steps: list[str]


@dataclass
class ArchitectureDoc:
    """A structured architecture document."""
    title: str
    overview: str
    component_diagram_mermaid: str
    data_flow_mermaid: str
    integration_points: list[dict]
    security_notes: list[str]
    scaling_notes: list[str]


@dataclass
class RFPResponse:
    """A response to an RFP requirement."""
    requirement_id: str
    requirement_text: str
    status: ComplianceStatus
    response: str
    evidence: str


# ---------------------------------------------------------------------------
# 1. AUDIENCE-LEVEL COMMUNICATION SAMPLES
# ---------------------------------------------------------------------------
# Same technical concept explained at different audience levels.
# Demonstrates vocabulary adaptation, framing shifts, and depth control.

# Technical concept: "Our platform uses event-driven architecture with
# a distributed message queue for asynchronous data processing."

AUDIENCE_ADAPTATIONS: dict[AudienceLevel, AdaptedMessage] = {
    AudienceLevel.EXECUTIVE: AdaptedMessage(
        audience=AudienceLevel.EXECUTIVE,
        text=(
            "Your data processes automatically and reliably, even during "
            "peak traffic. This eliminates the manual intervention your "
            "operations team currently spends 15 hours per week on, saving "
            "roughly $200K annually in operational overhead. When transaction "
            "volume doubles next quarter, the system scales without any "
            "changes or additional cost."
        ),
        key_points=[
            "Cost saving: $200K/year in reduced manual operations",
            "Reliability: zero dropped transactions, even during spikes",
            "Scalability: handles growth without re-architecture",
        ],
        vocabulary_level="Business -- no technical jargon",
        framing="Business impact first: cost savings and reliability",
    ),
    AudienceLevel.TECHNICAL_LEADER: AdaptedMessage(
        audience=AudienceLevel.TECHNICAL_LEADER,
        text=(
            "The platform uses an event-driven architecture with a managed "
            "message queue (Kafka-compatible) for asynchronous processing. "
            "Events are persisted with exactly-once delivery semantics, so "
            "your downstream consumers never see duplicates or gaps. The "
            "system auto-scales horizontally -- you configure throughput "
            "targets and we handle partition rebalancing. This fits cleanly "
            "into your existing microservices topology: your services publish "
            "events via our SDK, and consumers receive them via standard "
            "Kafka protocol."
        ),
        key_points=[
            "Architecture: event-driven with managed Kafka-compatible queue",
            "Delivery guarantee: exactly-once semantics",
            "Integration: standard Kafka protocol, SDK for publishing",
            "Operations: auto-scaling with configurable throughput targets",
        ],
        vocabulary_level="Technical-conceptual -- architecture terms, no low-level code",
        framing="Architecture fit and operational characteristics",
    ),
    AudienceLevel.DEVELOPER: AdaptedMessage(
        audience=AudienceLevel.DEVELOPER,
        text=(
            "Install the SDK: `pip install acme-events`. Initialize with "
            "your API key and publish events:\n\n"
            "```python\n"
            "from acme import EventClient\n"
            "client = EventClient(api_key='sk_...')\n"
            "client.publish('user.signup', {'user_id': '123', 'plan': 'pro'})\n"
            "```\n\n"
            "Events land in a Kafka-compatible topic. Consume with any Kafka "
            "client or use our consumer SDK. Exactly-once delivery uses "
            "idempotency keys (auto-generated from event_type + payload hash, "
            "or pass your own). Retries: 3x with exponential backoff, then "
            "dead-letter queue. Rate limit: 10K events/sec per tenant, "
            "configurable. Full API docs at docs.acme.com/events."
        ),
        key_points=[
            "SDK: `pip install acme-events` -- publish in 3 lines",
            "Protocol: Kafka-compatible topics for consuming",
            "Idempotency: auto-generated or custom keys",
            "Rate limit: 10K/sec, configurable",
            "Docs: docs.acme.com/events",
        ],
        vocabulary_level="Deep technical -- code samples, protocol details, rate limits",
        framing="Show the code first, then the operational details",
    ),
    AudienceLevel.BUSINESS_STAKEHOLDER: AdaptedMessage(
        audience=AudienceLevel.BUSINESS_STAKEHOLDER,
        text=(
            "Every customer action -- signups, purchases, support tickets -- "
            "is captured and processed automatically. Your analytics dashboards "
            "update in real-time instead of waiting for the overnight batch. "
            "This means your team can react to trends within minutes, not the "
            "next morning. The system handles peak traffic (like Black Friday) "
            "without any manual scaling or intervention from your engineering team."
        ),
        key_points=[
            "Real-time dashboards instead of overnight batch",
            "Automatic handling of traffic spikes",
            "No engineering intervention needed for daily operations",
        ],
        vocabulary_level="Mixed -- domain-specific terms, no engineering jargon",
        framing="Workflow improvement and business agility",
    ),
    AudienceLevel.END_USER: AdaptedMessage(
        audience=AudienceLevel.END_USER,
        text=(
            "When a customer signs up or makes a purchase, you will see it "
            "in your dashboard immediately -- no more waiting until tomorrow "
            "morning for the data to refresh. Everything updates in real-time "
            "so you always have the latest numbers."
        ),
        key_points=[
            "Data appears immediately, not next-day",
            "Dashboard always shows current numbers",
        ],
        vocabulary_level="Non-technical -- outcome-only, no mechanism",
        framing="Daily experience improvement",
    ),
}


def demonstrate_audience_adaptation() -> None:
    """Show the same concept adapted for each audience level."""
    concept = (
        "Event-driven architecture with distributed message queue "
        "for asynchronous data processing"
    )
    print(f"TECHNICAL CONCEPT: {concept}\n")
    print("=" * 70)

    for level, msg in AUDIENCE_ADAPTATIONS.items():
        print(f"\n--- {level.value.upper().replace('_', ' ')} ---")
        print(f"Vocabulary: {msg.vocabulary_level}")
        print(f"Framing: {msg.framing}")
        print(f"\nMessage:\n{msg.text}")
        print(f"\nKey points:")
        for kp in msg.key_points:
            print(f"  - {kp}")
        print()


def adapt_message(
    technical_concept: str,
    audience: AudienceLevel,
    product_name: str = "our platform",
    customer_context: str = "",
) -> AdaptedMessage:
    """Adapt a technical concept for a specific audience.

    This is a rule-based adapter that demonstrates the transformation
    patterns. In practice, an SE does this mentally in real-time.

    Args:
        technical_concept: The raw technical description
        audience: Target audience level
        product_name: Name of the product being discussed
        customer_context: Optional context about the customer's situation
    """
    # Vocabulary mappings for common technical terms
    jargon_to_business: dict[str, str] = {
        "API": "automated connection",
        "microservices": "modular components",
        "Kubernetes": "cloud infrastructure",
        "SSO": "single login",
        "SAML": "secure authentication",
        "OAuth": "secure login",
        "webhook": "real-time notification",
        "ETL": "data processing",
        "CI/CD": "automated deployment",
        "containerized": "cloud-ready",
        "idempotent": "reliable (processes exactly once)",
        "horizontal scaling": "grows with your needs",
        "event-driven": "real-time automated",
        "latency": "response time",
        "throughput": "processing capacity",
        "SLA": "uptime guarantee",
    }

    if audience == AudienceLevel.EXECUTIVE:
        # Strip all jargon, lead with impact
        adapted = technical_concept
        for jargon, replacement in jargon_to_business.items():
            adapted = adapted.replace(jargon, replacement)
        if customer_context:
            adapted = f"For your team: {adapted}"
        return AdaptedMessage(
            audience=audience,
            text=adapted,
            key_points=["Business impact", "Cost/time savings", "Risk reduction"],
            vocabulary_level="Business -- zero jargon",
            framing="Lead with business outcome",
        )

    elif audience == AudienceLevel.TECHNICAL_LEADER:
        return AdaptedMessage(
            audience=audience,
            text=technical_concept,
            key_points=[
                "Architecture fit",
                "Scalability characteristics",
                "Security posture",
                "Operational requirements",
            ],
            vocabulary_level="Technical-conceptual",
            framing="Architecture and integration perspective",
        )

    elif audience == AudienceLevel.DEVELOPER:
        return AdaptedMessage(
            audience=audience,
            text=f"{technical_concept}\n\nSee API docs for implementation details.",
            key_points=[
                "Code samples and SDK",
                "API reference",
                "Rate limits and error handling",
            ],
            vocabulary_level="Deep technical -- code-level",
            framing="Show the code, then the details",
        )

    elif audience == AudienceLevel.BUSINESS_STAKEHOLDER:
        adapted = technical_concept
        for jargon, replacement in jargon_to_business.items():
            adapted = adapted.replace(jargon, replacement)
        return AdaptedMessage(
            audience=audience,
            text=adapted,
            key_points=["Workflow improvement", "Time savings", "Team impact"],
            vocabulary_level="Mixed -- domain terms, no engineering jargon",
            framing="Workflow and KPI improvement",
        )

    else:  # END_USER
        adapted = technical_concept
        for jargon, replacement in jargon_to_business.items():
            adapted = adapted.replace(jargon, replacement)
        return AdaptedMessage(
            audience=audience,
            text=adapted,
            key_points=["Ease of use", "Daily experience"],
            vocabulary_level="Non-technical",
            framing="Personal workflow improvement",
        )


# ---------------------------------------------------------------------------
# 2. STAKEHOLDER ANALYSIS ENGINE
# ---------------------------------------------------------------------------
# Complete stakeholder mapping and strategy generator.
# Takes raw contact information and produces categorized maps with
# recommended engagement strategies.

CHAMPION_SIGNALS = [
    "asks how to help move forward",
    "shares internal information proactively",
    "suggests meetings with other stakeholders",
    "asks about roadmap and future features",
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


def classify_stakeholder(signals: list[str]) -> StakeholderRole:
    """Classify a stakeholder based on observed behavioral signals.

    Uses signal matching against known patterns for each role.
    In practice, SE judgment overrides algorithmic classification.
    """
    scores: dict[StakeholderRole, int] = {
        StakeholderRole.CHAMPION: 0,
        StakeholderRole.COACH: 0,
        StakeholderRole.BLOCKER: 0,
        StakeholderRole.ECONOMIC_BUYER: 0,
        StakeholderRole.TECHNICAL_EVALUATOR: 0,
    }

    signal_sets = {
        StakeholderRole.CHAMPION: CHAMPION_SIGNALS,
        StakeholderRole.COACH: COACH_SIGNALS,
        StakeholderRole.BLOCKER: BLOCKER_SIGNALS,
        StakeholderRole.ECONOMIC_BUYER: BUYER_SIGNALS,
        StakeholderRole.TECHNICAL_EVALUATOR: EVALUATOR_SIGNALS,
    }

    for signal in signals:
        signal_lower = signal.lower()
        for role, known_signals in signal_sets.items():
            for known in known_signals:
                # Simple substring matching -- production would use embeddings
                if known in signal_lower or signal_lower in known:
                    scores[role] += 1

    # Return highest-scoring role, default to COACH if no clear match
    best_role = max(scores, key=lambda r: scores[r])
    if scores[best_role] == 0:
        return StakeholderRole.COACH
    return best_role


def generate_strategy(stakeholder: Stakeholder) -> str:
    """Generate an engagement strategy based on stakeholder classification."""
    strategies = {
        StakeholderRole.CHAMPION: (
            f"Nurture {stakeholder.name} as champion. Provide ROI materials, "
            f"competitive comparison docs, and answers to internal objections. "
            f"Give early access to new features. Schedule regular 1:1 check-ins "
            f"to maintain alignment and provide internal ammunition."
        ),
        StakeholderRole.COACH: (
            f"Maintain relationship with {stakeholder.name} as information source. "
            f"Ask about decision process, timeline, and competitive dynamics. "
            f"Respect their boundaries -- do not push them to advocate publicly "
            f"if they are not comfortable. Provide value through industry insights."
        ),
        StakeholderRole.BLOCKER: (
            f"Address {stakeholder.name}'s concerns directly. "
            f"{'High power -- must be neutralized or converted. ' if stakeholder.power >= 4 else ''}"
            f"Schedule a 1:1 to understand their specific objections. "
            f"Prepare evidence-based responses. If political blocker, work with "
            f"champion to build consensus around them."
        ),
        StakeholderRole.ECONOMIC_BUYER: (
            f"Prepare executive-level materials for {stakeholder.name}. "
            f"Focus on ROI, risk mitigation, and competitive positioning. "
            f"Keep communication concise -- use the 3-minute rule. "
            f"Coordinate with AE on timing and pricing presentation."
        ),
        StakeholderRole.TECHNICAL_EVALUATOR: (
            f"Support {stakeholder.name}'s evaluation with hands-on resources. "
            f"Provide sandbox access, API documentation, and code samples. "
            f"Be responsive to technical questions -- aim for same-day replies. "
            f"Offer pair programming or workshop sessions. Be honest about limitations."
        ),
    }
    return strategies.get(stakeholder.role, "Engage and learn more about their priorities.")


def analyze_stakeholder_map(contacts: list[dict]) -> list[Stakeholder]:
    """Analyze a list of contacts and produce a stakeholder map.

    Args:
        contacts: List of dicts with keys:
            - name: str
            - title: str
            - power: int (1-5)
            - interest: int (1-5)
            - disposition: str (positive/neutral/negative)
            - signals: list[str] (observed behaviors)

    Returns:
        List of Stakeholder objects with classification and strategy.
    """
    stakeholders = []
    for contact in contacts:
        role = classify_stakeholder(contact.get("signals", []))
        s = Stakeholder(
            name=contact["name"],
            title=contact["title"],
            role=role,
            power=contact.get("power", 3),
            interest=contact.get("interest", 3),
            disposition=contact.get("disposition", "neutral"),
            signals=contact.get("signals", []),
        )
        s.strategy = generate_strategy(s)
        stakeholders.append(s)
    return stakeholders


def print_stakeholder_map(stakeholders: list[Stakeholder]) -> None:
    """Pretty-print a stakeholder map."""
    print("\nSTAKEHOLDER MAP")
    print("=" * 70)
    for s in sorted(stakeholders, key=lambda x: x.power, reverse=True):
        print(f"\n{s.name} -- {s.title}")
        print(f"  Role: {s.role.value}")
        print(f"  Power: {'*' * s.power} ({s.power}/5)")
        print(f"  Interest: {'*' * s.interest} ({s.interest}/5)")
        print(f"  Disposition: {s.disposition}")
        print(f"  Signals: {', '.join(s.signals[:3])}")
        print(f"  Strategy: {s.strategy[:120]}...")


# ---------------------------------------------------------------------------
# 3. EXECUTIVE SUMMARY GENERATOR
# ---------------------------------------------------------------------------
# Transforms technical proposal input into a business-focused 1-page summary.

JARGON_MAP: dict[str, str] = {
    "API integration": "automated data connection",
    "webhook": "real-time notification",
    "SSO": "single login with existing credentials",
    "SAML": "enterprise single sign-on",
    "microservices": "modular, independently scalable components",
    "Kubernetes": "cloud infrastructure management",
    "ETL pipeline": "automated data processing",
    "horizontal scaling": "handles more volume without changes",
    "CI/CD pipeline": "automated deployment process",
    "containerized": "cloud-ready deployment",
    "99.99% uptime": "less than 1 hour of downtime per year",
    "99.9% uptime": "less than 9 hours of downtime per year",
    "event-driven": "real-time automated processing",
    "idempotent": "processes each item exactly once",
    "REST API": "standard web interface",
    "GraphQL": "flexible data query interface",
    "SDK": "pre-built integration library",
    "latency": "response time",
    "throughput": "processing capacity",
}


def strip_jargon(text: str) -> str:
    """Replace technical jargon with business-friendly language."""
    result = text
    for jargon, replacement in JARGON_MAP.items():
        result = result.replace(jargon, replacement)
    return result


def generate_executive_summary(
    customer_name: str,
    project_name: str,
    challenge: str,
    solution_components: list[str],
    expected_outcomes: list[dict],
    timeline_phases: list[dict],
    investment: str,
    next_steps: list[str],
) -> ExecutiveSummary:
    """Generate a structured executive summary from technical inputs.

    Args:
        customer_name: Name of the customer
        project_name: Name of the project or initiative
        challenge: Description of the business challenge (will be de-jargoned)
        solution_components: List of solution components (will be de-jargoned)
        expected_outcomes: List of dicts with 'metric' and 'value' keys
        timeline_phases: List of dicts with 'phase', 'duration', 'description'
        investment: Pricing / investment description
        next_steps: List of concrete next steps
    """
    # De-jargon the challenge
    clean_challenge = strip_jargon(challenge)

    # Build solution paragraph from components
    clean_components = [strip_jargon(c) for c in solution_components]
    solution_text = (
        f"We propose deploying {project_name} to address this challenge. "
        f"The solution includes: {'; '.join(clean_components)}. "
        f"This approach eliminates manual processes and provides real-time "
        f"visibility across your organization."
    )

    # Format outcomes with metrics
    outcome_strings = []
    for outcome in expected_outcomes:
        outcome_strings.append(f"{outcome['metric']}: {outcome['value']}")

    # Format timeline
    timeline_strings = []
    for phase in timeline_phases:
        timeline_strings.append(
            f"Phase {phase['phase']} ({phase['duration']}): {strip_jargon(phase['description'])}"
        )

    return ExecutiveSummary(
        title=f"Executive Summary: {project_name} for {customer_name}",
        challenge=clean_challenge,
        solution=solution_text,
        outcomes=outcome_strings,
        timeline=timeline_strings,
        investment=investment,
        next_steps=next_steps,
    )


def format_executive_summary(summary: ExecutiveSummary) -> str:
    """Format an ExecutiveSummary into a printable 1-page document."""
    lines = [
        summary.title,
        "=" * len(summary.title),
        "",
        "THE CHALLENGE",
        summary.challenge,
        "",
        "PROPOSED SOLUTION",
        summary.solution,
        "",
        "EXPECTED OUTCOMES",
    ]
    for outcome in summary.outcomes:
        lines.append(f"  - {outcome}")

    lines.extend(["", "TIMELINE"])
    for phase in summary.timeline:
        lines.append(f"  - {phase}")

    lines.extend([
        "",
        "INVESTMENT",
        f"  {summary.investment}",
        "",
        "NEXT STEPS",
    ])
    for i, step in enumerate(summary.next_steps, 1):
        lines.append(f"  {i}. {step}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. TECHNICAL BRIEF TEMPLATE
# ---------------------------------------------------------------------------
# Architecture document generator with Mermaid diagram output.

def generate_architecture_doc(
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
        project_name: Name of the project
        overview: High-level overview paragraph
        components: List of dicts with 'name', 'type' (customer|product|external), 'description'
        data_flows: List of dicts with 'from', 'to', 'protocol', 'description'
        integration_points: List of dicts with 'system', 'method', 'auth', 'notes'
        security_requirements: List of security notes
        scaling_requirements: List of scaling notes
    """
    # Build component diagram in Mermaid
    component_lines = ["graph LR"]
    node_ids: dict[str, str] = {}
    for i, comp in enumerate(components):
        node_id = f"N{i}"
        node_ids[comp["name"]] = node_id
        if comp["type"] == "customer":
            component_lines.append(f"    {node_id}[{comp['name']}]")
        elif comp["type"] == "product":
            component_lines.append(f"    {node_id}({comp['name']})")
        else:
            component_lines.append(f"    {node_id}[/{comp['name']}/]")

    for flow in data_flows:
        from_id = node_ids.get(flow["from"], "?")
        to_id = node_ids.get(flow["to"], "?")
        label = flow.get("protocol", "")
        component_lines.append(f"    {from_id} -->|{label}| {to_id}")

    component_mermaid = "\n".join(component_lines)

    # Build data flow diagram (sequence diagram)
    flow_lines = ["sequenceDiagram"]
    participants = set()
    for flow in data_flows:
        participants.add(flow["from"])
        participants.add(flow["to"])
    for p in sorted(participants):
        alias = p.replace(" ", "")
        flow_lines.append(f"    participant {alias} as {p}")
    for flow in data_flows:
        from_alias = flow["from"].replace(" ", "")
        to_alias = flow["to"].replace(" ", "")
        desc = flow.get("description", flow.get("protocol", ""))
        flow_lines.append(f"    {from_alias}->>{to_alias}: {desc}")

    flow_mermaid = "\n".join(flow_lines)

    return ArchitectureDoc(
        title=f"Architecture Document: {project_name}",
        overview=overview,
        component_diagram_mermaid=component_mermaid,
        data_flow_mermaid=flow_mermaid,
        integration_points=integration_points,
        security_notes=security_requirements,
        scaling_notes=scaling_requirements,
    )


def format_architecture_doc(doc: ArchitectureDoc) -> str:
    """Format an ArchitectureDoc into a printable document."""
    lines = [
        doc.title,
        "=" * len(doc.title),
        "",
        "1. OVERVIEW",
        doc.overview,
        "",
        "2. COMPONENT DIAGRAM",
        "```mermaid",
        doc.component_diagram_mermaid,
        "```",
        "",
        "3. DATA FLOW",
        "```mermaid",
        doc.data_flow_mermaid,
        "```",
        "",
        "4. INTEGRATION POINTS",
    ]
    for ip in doc.integration_points:
        lines.append(f"  System: {ip['system']}")
        lines.append(f"    Method: {ip['method']}")
        lines.append(f"    Auth: {ip['auth']}")
        lines.append(f"    Notes: {ip['notes']}")
        lines.append("")

    lines.append("5. SECURITY")
    for note in doc.security_notes:
        lines.append(f"  - {note}")

    lines.extend(["", "6. SCALING"])
    for note in doc.scaling_notes:
        lines.append(f"  - {note}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. RFP RESPONSE SYSTEM
# ---------------------------------------------------------------------------
# RFP question processor with compliance matrix output.

def assess_capability(
    requirement: str,
    capabilities: dict[str, str],
) -> tuple[ComplianceStatus, str]:
    """Assess how well a product capability matches an RFP requirement.

    Args:
        requirement: The RFP requirement text
        capabilities: Dict mapping capability keywords to support descriptions.
                     Special keys: 'roadmap_items' (comma-separated),
                                   'not_supported' (comma-separated)

    Returns:
        Tuple of (ComplianceStatus, response_text)
    """
    req_lower = requirement.lower()

    # Check for explicit non-support
    not_supported = capabilities.get("not_supported", "").lower().split(",")
    for ns in not_supported:
        ns = ns.strip()
        if ns and ns in req_lower:
            return (
                ComplianceStatus.NOT_SUPPORTED,
                f"Not supported. {capabilities.get(ns + '_alt', 'No alternative available.')}",
            )

    # Check for roadmap items
    roadmap = capabilities.get("roadmap_items", "").lower().split(",")
    for ri in roadmap:
        ri = ri.strip()
        if ri and ri in req_lower:
            timeline = capabilities.get(ri + "_timeline", "future release")
            return (
                ComplianceStatus.ROADMAP,
                f"Planned for {timeline}. Currently in development. "
                f"Early access available for design partners.",
            )

    # Check for matching capabilities
    best_match = ""
    best_match_len = 0
    for key, description in capabilities.items():
        if key.startswith("_") or key in ("roadmap_items", "not_supported"):
            continue
        key_lower = key.lower()
        if key_lower in req_lower and len(key_lower) > best_match_len:
            best_match = description
            best_match_len = len(key_lower)

    if best_match:
        if "partial" in best_match.lower() or "workaround" in best_match.lower():
            return (ComplianceStatus.PARTIALLY_SUPPORTED, best_match)
        if "integration" in best_match.lower() or "partner" in best_match.lower():
            return (ComplianceStatus.INTEGRATION, best_match)
        return (ComplianceStatus.FULLY_SUPPORTED, best_match)

    return (
        ComplianceStatus.PARTIALLY_SUPPORTED,
        "Requires further assessment. Please provide additional detail "
        "on the specific requirements for a comprehensive response.",
    )


def process_rfp(
    requirements: list[dict],
    capabilities: dict[str, str],
) -> list[RFPResponse]:
    """Process a list of RFP requirements against product capabilities.

    Args:
        requirements: List of dicts with 'id' and 'text' keys
        capabilities: Product capability descriptions (passed to assess_capability)

    Returns:
        List of RFPResponse objects forming the compliance matrix.
    """
    responses = []
    for req in requirements:
        status, response_text = assess_capability(req["text"], capabilities)
        responses.append(RFPResponse(
            requirement_id=req["id"],
            requirement_text=req["text"],
            status=status,
            response=response_text,
            evidence="See documentation at docs.acme.com" if status in (
                ComplianceStatus.FULLY_SUPPORTED,
                ComplianceStatus.PARTIALLY_SUPPORTED,
            ) else "",
        ))
    return responses


def format_compliance_matrix(responses: list[RFPResponse]) -> str:
    """Format RFP responses as a compliance matrix."""
    lines = [
        "COMPLIANCE MATRIX",
        "=" * 70,
        "",
        f"{'Req ID':<8} {'Status':<6} {'Requirement':<40} {'Response'}",
        "-" * 70,
    ]
    for r in responses:
        req_short = r.requirement_text[:38] + ".." if len(r.requirement_text) > 40 else r.requirement_text
        resp_short = r.response[:50] + "..." if len(r.response) > 50 else r.response
        lines.append(f"{r.requirement_id:<8} {r.status.value:<6} {req_short:<40} {resp_short}")

    # Summary
    total = len(responses)
    by_status = {}
    for r in responses:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    lines.extend([
        "",
        "-" * 70,
        "SUMMARY",
        f"  Total requirements: {total}",
    ])
    for status in ComplianceStatus:
        count = by_status.get(status, 0)
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"  {status.value} ({status.name}): {count} ({pct:.0f}%)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run all demonstrations."""

    # === Section 1: Audience adaptation ===
    print("=" * 70)
    print("SECTION 1: AUDIENCE-LEVEL COMMUNICATION SAMPLES")
    print("=" * 70)
    demonstrate_audience_adaptation()

    # === Section 2: Stakeholder analysis ===
    print("\n" + "=" * 70)
    print("SECTION 2: STAKEHOLDER ANALYSIS ENGINE")
    print("=" * 70)

    contacts = [
        {
            "name": "Sarah Chen",
            "title": "VP Engineering",
            "power": 5,
            "interest": 3,
            "disposition": "neutral",
            "signals": [
                "asks about pricing",
                "discusses budget availability",
                "mentions procurement process",
            ],
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
                "asks about roadmap and future features",
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
                "delays meetings or evaluations",
            ],
        },
        {
            "name": "David Kim",
            "title": "Director of Operations",
            "power": 3,
            "interest": 4,
            "disposition": "positive",
            "signals": [
                "answers questions honestly",
                "warns about internal obstacles",
                "explains decision process",
            ],
        },
        {
            "name": "Lisa Wang",
            "title": "Lead Backend Engineer",
            "power": 2,
            "interest": 5,
            "disposition": "positive",
            "signals": [
                "asks detailed technical questions",
                "requests sandbox access",
                "runs benchmarks or tests",
                "asks about API limits and edge cases",
            ],
        },
    ]

    stakeholders = analyze_stakeholder_map(contacts)
    print_stakeholder_map(stakeholders)

    # === Section 3: Executive summary ===
    print("\n\n" + "=" * 70)
    print("SECTION 3: EXECUTIVE SUMMARY GENERATOR")
    print("=" * 70)

    summary = generate_executive_summary(
        customer_name="Acme Financial Services",
        project_name="Real-Time Fraud Detection Platform",
        challenge=(
            "Acme's current fraud detection relies on an overnight ETL pipeline "
            "that processes transactions in batch. Fraudulent transactions are "
            "not detected until 12-24 hours after they occur, resulting in "
            "$2.3M in annual fraud losses and 15 hours/week of manual review "
            "by the operations team."
        ),
        solution_components=[
            "Real-time event-driven transaction processing via REST API integration",
            "Machine learning scoring engine with sub-100ms latency",
            "Dashboard for operations team with real-time alerts via webhook",
            "SSO integration with Acme's existing Okta deployment",
        ],
        expected_outcomes=[
            {"metric": "Fraud loss reduction", "value": "40-60% ($900K-$1.4M annually)"},
            {"metric": "Detection time", "value": "From 12-24 hours to under 5 seconds"},
            {"metric": "Manual review hours", "value": "From 15 hours/week to 3 hours/week"},
            {"metric": "False positive rate", "value": "Below 2% (industry avg: 5-8%)"},
        ],
        timeline_phases=[
            {"phase": 1, "duration": "Weeks 1-2", "description": "REST API integration and SSO setup"},
            {"phase": 2, "duration": "Weeks 3-4", "description": "ML model training on historical transaction data"},
            {"phase": 3, "duration": "Weeks 5-6", "description": "Pilot with credit card transactions (parallel run)"},
            {"phase": 4, "duration": "Weeks 7-8", "description": "Full rollout across all transaction types"},
        ],
        investment="$180,000/year (based on projected transaction volume of 5M/month)",
        next_steps=[
            "Schedule kickoff with Acme engineering team (target: March 10)",
            "Acme to provide sample transaction data for model training",
            "Joint architecture review with Acme InfoSec (target: March 12)",
        ],
    )
    print("\n" + format_executive_summary(summary))

    # === Section 4: Architecture document ===
    print("\n\n" + "=" * 70)
    print("SECTION 4: TECHNICAL BRIEF TEMPLATE")
    print("=" * 70)

    arch_doc = generate_architecture_doc(
        project_name="Acme Fraud Detection Integration",
        overview=(
            "This document describes the architecture for integrating the "
            "Acme Financial Services transaction processing system with our "
            "real-time fraud detection platform. The integration uses a "
            "synchronous API call in the transaction processing path and "
            "asynchronous event delivery for alerting and reporting."
        ),
        components=[
            {"name": "Acme Payment Gateway", "type": "customer", "description": "Processes card transactions"},
            {"name": "Fraud Detection API", "type": "product", "description": "Real-time fraud scoring"},
            {"name": "ML Scoring Engine", "type": "product", "description": "Transaction risk model"},
            {"name": "Alert Service", "type": "product", "description": "Real-time notifications"},
            {"name": "Acme Operations Dashboard", "type": "customer", "description": "Fraud review UI"},
            {"name": "Acme Data Warehouse", "type": "customer", "description": "Historical analytics"},
            {"name": "Okta", "type": "external", "description": "Identity provider"},
        ],
        data_flows=[
            {"from": "Acme Payment Gateway", "to": "Fraud Detection API", "protocol": "REST/TLS", "description": "Transaction scoring request"},
            {"from": "Fraud Detection API", "to": "ML Scoring Engine", "protocol": "gRPC", "description": "Model inference"},
            {"from": "Fraud Detection API", "to": "Acme Payment Gateway", "protocol": "REST/TLS", "description": "Score response (<100ms)"},
            {"from": "Alert Service", "to": "Acme Operations Dashboard", "protocol": "WebSocket", "description": "Real-time fraud alerts"},
            {"from": "Fraud Detection API", "to": "Acme Data Warehouse", "protocol": "S3 Export", "description": "Hourly scoring results export"},
        ],
        integration_points=[
            {"system": "Acme Payment Gateway", "method": "REST API (sync)", "auth": "mTLS + API key", "notes": "Added to transaction processing path; timeout at 200ms with fallback to allow"},
            {"system": "Acme Operations Dashboard", "method": "WebSocket", "auth": "Okta SAML SSO", "notes": "Real-time alert delivery; dashboard hosted by us, embedded via iframe"},
            {"system": "Acme Data Warehouse", "method": "S3 export (async)", "auth": "IAM cross-account role", "notes": "Hourly Parquet export to customer S3 bucket for historical analysis"},
            {"system": "Okta", "method": "SAML 2.0", "auth": "SAML metadata exchange", "notes": "All user authentication via customer Okta tenant"},
        ],
        security_requirements=[
            "All data in transit encrypted with TLS 1.3",
            "All data at rest encrypted with AES-256-GCM (AWS KMS managed keys)",
            "SOC 2 Type II certified (report available under NDA)",
            "PCI DSS Level 1 compliant for transaction data handling",
            "No customer data leaves us-east-1 region",
            "API authentication via mTLS with certificate pinning",
        ],
        scaling_requirements=[
            "Current: 5M transactions/month (~2 TPS average, 50 TPS peak)",
            "Platform supports up to 10,000 TPS with auto-scaling",
            "Scoring latency: <50ms p50, <100ms p99 at current volume",
            "Horizontal scaling via stateless API instances behind load balancer",
            "ML model inference scales independently of API tier",
        ],
    )
    print("\n" + format_architecture_doc(arch_doc))

    # === Section 5: RFP response ===
    print("\n\n" + "=" * 70)
    print("SECTION 5: RFP RESPONSE SYSTEM")
    print("=" * 70)

    requirements = [
        {"id": "T-001", "text": "Must support SAML 2.0 SSO for user authentication"},
        {"id": "T-002", "text": "Must provide real-time transaction scoring with <100ms latency"},
        {"id": "T-003", "text": "Must support on-premises deployment"},
        {"id": "T-004", "text": "Must integrate with SAP ERP for transaction data"},
        {"id": "T-005", "text": "Must support air-gapped environments"},
        {"id": "T-006", "text": "Must provide REST API for integration"},
        {"id": "T-007", "text": "Must be SOC 2 Type II certified"},
        {"id": "T-008", "text": "Must support role-based access control"},
    ]

    capabilities = {
        "SAML": "Native SAML 2.0 SSO with metadata exchange. Supports Okta, Azure AD, OneLogin, and custom IdPs. Configuration via admin console with zero-code setup.",
        "real-time": "Real-time scoring engine with <50ms p50, <100ms p99 latency at production scale. Synchronous REST API call returns risk score with transaction context.",
        "on-premises": "Partial support via containerized deployment (Docker/K8s). Requires customer-provided infrastructure and outbound connectivity for model updates. Full SaaS deployment recommended. Workaround: VPC-peered private deployment available.",
        "REST API": "Full REST API with OpenAPI 3.0 specification. SDKs available for Python, Java, Go, and Node.js. Rate limit: 10K requests/second per tenant.",
        "SOC 2": "SOC 2 Type II certified since 2023. Annual audit by Deloitte. Report available under NDA. Additional certifications: ISO 27001, PCI DSS Level 1.",
        "role-based access control": "Granular RBAC with predefined roles (Admin, Analyst, Viewer) and custom role support. Integrated with SAML group mapping for automated provisioning.",
        "roadmap_items": "SAP",
        "SAP_timeline": "Q3 2026",
        "not_supported": "air-gapped",
        "air-gapped_alt": "Product requires outbound internet for license validation, model updates, and telemetry. Private deployment with VPC peering is available as an alternative.",
    }

    responses = process_rfp(requirements, capabilities)
    print("\n" + format_compliance_matrix(responses))

    # Print detailed responses
    print("\n\nDETAILED RESPONSES")
    print("-" * 70)
    for r in responses:
        print(f"\n{r.requirement_id}: {r.requirement_text}")
        print(f"  Status: {r.status.value} ({r.status.name})")
        print(f"  Response: {r.response}")
        if r.evidence:
            print(f"  Evidence: {r.evidence}")


if __name__ == "__main__":
    main()
