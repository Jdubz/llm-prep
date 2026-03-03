"""
Module 04: Integration, Deployment, and Customer Success — Exercises

Complete the TODO sections. Each exercise focuses on a core integration,
deployment, or customer success pattern you should be able to implement
and explain in an interview.

Run with: python exercises.py (uses assert-based tests at the bottom)

Reference files in this directory:
  - 01-integration-patterns-and-architecture.md  (API patterns, auth, migration, webhooks)
  - 02-fde-deployment-patterns.md                (engagement model, scope, knowledge transfer)
  - 03-customer-success-and-expansion.md         (health scoring, QBRs, expansion, churn)
  - examples.py                                  (runnable reference implementations)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Shared types used across exercises
# ---------------------------------------------------------------------------

@dataclass
class FieldMapping:
    """Maps a source field to a target field with transformation."""
    source_field: str
    target_field: str
    transform: str  # e.g., "lowercase", "multiply_100", "none"
    notes: str = ""


@dataclass
class IntegrationPlan:
    """Complete integration plan for connecting two systems."""
    pattern: str  # "unidirectional_sync", "bidirectional_sync", "event_driven", "batch"
    auth_approach: str  # "oauth2_client_credentials", "api_key", "saml", etc.
    api_style: str  # "rest", "graphql", "grpc"
    field_mappings: list[FieldMapping]
    error_handling: str
    estimated_days: int
    risks: list[str]


@dataclass
class ChecklistItem:
    """A single item in a migration checklist."""
    phase: str  # "pre_migration", "during_migration", "post_migration"
    task: str
    priority: int  # 1 = critical, 2 = important, 3 = nice-to-have
    estimated_hours: float


@dataclass
class MigrationChecklist:
    """Complete migration checklist with phased steps."""
    approach: str  # "big_bang", "phased", "parallel_run"
    items: list[ChecklistItem]
    estimated_total_hours: float
    rollback_plan: str
    risks: list[str]


@dataclass
class ScopeItem:
    """A single scope classification."""
    request: str
    classification: str  # "in_scope", "out_of_scope", "stretch"
    reason: str
    estimated_hours: float


@dataclass
class FDEScope:
    """Complete scope definition for an FDE engagement."""
    items: list[ScopeItem]
    boundaries: list[str]
    escalation_triggers: list[str]
    flex_budget_hours: float


@dataclass
class HealthScore:
    """Customer health score with risk analysis."""
    overall_score: float  # 0-100
    status: str  # "green", "amber", "red", "critical"
    component_scores: dict[str, float]  # e.g., {"usage": 80, "support": 60}
    risk_factors: list[str]
    recommended_actions: list[str]


@dataclass
class QBRPrep:
    """QBR preparation document."""
    agenda: list[str]
    usage_summary: str
    support_summary: str
    risk_items: list[str]
    expansion_opportunities: list[str]
    action_items_from_last_qbr: list[str]
    talking_points: list[str]


@dataclass
class ExpansionOpportunity:
    """A single expansion opportunity."""
    vector: str  # "new_use_case", "new_team", "new_geography", "tier_upgrade", "new_product"
    description: str
    likelihood: str  # "high", "medium", "low"
    estimated_value: str  # e.g., "$50K ARR"
    next_step: str


# ============================================================================
# EXERCISE 1: Integration Plan Builder
#
# READ FIRST:
#   01-integration-patterns-and-architecture.md
#     -> "## API Integration Strategies" (REST vs GraphQL vs gRPC decision table)
#     -> "## Integration Architecture Decision Framework" (decision tree)
#     -> "## Authentication and SSO Patterns" (OAuth flows, API keys)
#     -> "### Scoping an Integration" (6-point scoping framework)
#
# ALSO SEE:
#   examples.py
#     -> "1. INTEGRATION ARCHITECTURE PLANNER"
#        - IntegrationPlanner.plan()        (pattern selection logic)
#        - select_api_style()               (REST/GraphQL/gRPC selection)
#        - select_auth_approach()           (auth pattern selection)
#
# Given source and target system descriptions, data models, and requirements,
# generate a complete integration plan: pattern selection, auth approach,
# data mapping, error handling strategy, and timeline estimate.
# ============================================================================

def build_integration_plan(
    source_system: dict[str, Any],
    target_system: dict[str, Any],
    requirements: dict[str, Any],
) -> IntegrationPlan:
    """
    Build an integration plan for connecting two systems.

    Args:
        source_system: Description of the source system.
            Keys: "name" (str), "api_style" (str: "rest"|"graphql"|"grpc"),
                  "auth" (str: "oauth2"|"api_key"|"saml"),
                  "fields" (list[str]: field names available)
        target_system: Description of the target system.
            Keys: same structure as source_system
        requirements: Integration requirements.
            Keys: "direction" (str: "one_way"|"two_way"),
                  "realtime" (bool: whether real-time is needed),
                  "volume_per_day" (int: expected events/records per day),
                  "field_mappings" (list[dict]: each has "source", "target", "transform"),
                  "latency_tolerance" (str: "seconds"|"minutes"|"hours")

    Returns:
        IntegrationPlan with pattern, auth, api_style, mappings, error
        handling, timeline, and risks.

    TODO: Implement this function.

    Step-by-step:
      1. Select the integration pattern based on direction and latency:
         - one_way + seconds/minutes -> "event_driven"
         - one_way + hours -> "batch"
         - two_way -> "bidirectional_sync"
         Use the decision tree from the MD file.

      2. Select API style. Default to "rest" unless:
         - Both systems support "grpc" and volume > 100_000 -> "grpc"
         - Source supports "graphql" and there are 5+ field mappings -> "graphql"

      3. Select auth approach:
         - If either system uses "oauth2" -> "oauth2_client_credentials"
         - If either system uses "saml" -> "saml_sso"
         - Otherwise -> "api_key"

      4. Build FieldMapping objects from requirements["field_mappings"]

      5. Set error handling based on pattern:
         - "event_driven" -> "retry_with_exponential_backoff_and_dlq"
         - "batch" -> "log_and_continue_with_error_report"
         - "bidirectional_sync" -> "conflict_resolution_last_write_wins"

      6. Estimate days:
         - Base: 5 days
         - Add 1 day per 2 field mappings
         - Add 5 days if bidirectional
         - Add 3 days if volume > 100_000
         - Add 50% buffer (multiply by 1.5, round up)

      7. Identify risks:
         - If two_way: "Conflict resolution edge cases"
         - If volume > 100_000: "Rate limiting may require throttling"
         - If auth is saml: "SSO configuration requires customer IT involvement"
         - Always include: "Data mapping validation needed with customer"
    """
    # TODO: Implement this function.
    pass


# ============================================================================
# EXERCISE 2: Migration Checklist Generator
#
# READ FIRST:
#   01-integration-patterns-and-architecture.md
#     -> "## Data Migration Strategies"
#        -> "### The Three Approaches" (big bang, phased, parallel run)
#        -> "### Migration Checklists" (pre/during/post checklists)
#        -> "### Timeline Estimation" (size/complexity table)
#     -> "### Data Mapping and Transformation" (mapping table example)
#
# ALSO SEE:
#   examples.py
#     -> "2. MIGRATION PLAN GENERATOR"
#        - MigrationPlanGenerator.generate()  (approach selection + checklist)
#        - select_approach()                  (decision logic)
#        - build_checklist()                  (phased item generation)
#
# Given migration parameters, generate a prioritized migration checklist
# with pre-migration, during, and post-migration phases.
# ============================================================================

def generate_migration_checklist(
    data_size_records: int,
    complexity: str,
    downtime_tolerance_hours: float,
    rollback_required: bool,
    regulated_industry: bool,
) -> MigrationChecklist:
    """
    Generate a complete migration checklist based on parameters.

    Args:
        data_size_records: Number of records to migrate.
        complexity: "simple" (1:1 mapping), "moderate" (transforms needed),
                    "complex" (multiple sources, custom logic).
        downtime_tolerance_hours: Maximum acceptable downtime in hours.
                                  0.0 means zero downtime required.
        rollback_required: Whether a rollback plan is mandatory.
        regulated_industry: Whether the customer is in a regulated industry
                           (healthcare, finance, government).

    Returns:
        MigrationChecklist with approach, items, timeline, rollback plan, risks.

    TODO: Implement this function.

    Step-by-step:
      1. Select migration approach:
         - If regulated_industry or (downtime_tolerance_hours == 0.0)
           -> "parallel_run"
         - If data_size_records > 1_000_000 or complexity == "complex"
           -> "phased"
         - Otherwise -> "big_bang"

      2. Build pre-migration items (always included):
         - "Complete data mapping document" (priority 1, 8h)
         - "Profile source data for quality issues" (priority 1, 4h)
         - "Run test migration on 10% subset" (priority 1, 8h)
         - "Document rollback procedure" (priority 1 if rollback_required else 2, 4h)
         - "Establish performance benchmarks" (priority 2, 2h)
         - "Schedule maintenance window" (priority 1, 1h) -- only if not parallel_run
         - "Set up parallel environment" (priority 1, 16h) -- only if parallel_run

      3. Build during-migration items:
         - "Execute migration job with monitoring" (priority 1, varies by size)
           Hours: data_size_records / 100_000 (minimum 1h, maximum 48h)
         - "Monitor error log in real-time" (priority 1, same hours as above)
         - "Perform spot checks on migrated records" (priority 1, 2h)
         - "Run comparison between systems" (priority 1, 4h) -- only if parallel_run

      4. Build post-migration items:
         - "Validate record counts" (priority 1, 1h)
         - "Run data integrity checks" (priority 1, 4h)
         - "Execute application smoke tests" (priority 1, 2h)
         - "Complete user acceptance testing" (priority 1, 8h)
         - "Regulatory compliance validation" (priority 1, 8h) -- only if regulated
         - "Migration retrospective" (priority 3, 2h)

      5. Calculate estimated_total_hours: sum of all item hours * 1.5 buffer

      6. Set rollback plan:
         - "parallel_run": "Cut back to original system. No data loss."
         - "phased": "Revert current phase. Previous phases unaffected."
         - "big_bang": "Restore from pre-migration backup. Downtime expected."

      7. Identify risks:
         - If data_size_records > 10_000_000: "Migration may exceed maintenance window"
         - If complexity == "complex": "Custom transform logic may have edge cases"
         - If not rollback_required: "No rollback plan increases risk of data loss"
         - Always: "Source data quality issues may require manual cleanup"
    """
    # TODO: Implement this function.
    pass


# ============================================================================
# EXERCISE 3: FDE Scope Definer
#
# READ FIRST:
#   02-fde-deployment-patterns.md
#     -> "## Scope Management for FDEs"
#        -> "### The Most Common FDE Failure Mode: Scope Creep"
#        -> "### How to Say No Diplomatically" (Acknowledge-Explain-Redirect)
#        -> "### When to Flex vs When to Hold Firm" (decision criteria)
#        -> "### SOW Interpretation" (tracking table)
#
# ALSO SEE:
#   examples.py
#     -> "3. FDE ENGAGEMENT TRACKER"
#        - FDEEngagementTracker.classify_request()  (scope classification logic)
#        - FDEEngagementTracker.get_scope_report()   (boundary summary)
#
# Given an engagement description, customer requests, and SOW constraints,
# classify each request and produce a scope definition.
# ============================================================================

def define_fde_scope(
    sow_deliverables: list[str],
    customer_requests: list[dict[str, Any]],
    total_engagement_hours: float,
    hours_remaining: float,
) -> FDEScope:
    """
    Define FDE scope by classifying customer requests.

    Args:
        sow_deliverables: List of deliverables from the Statement of Work.
            e.g., ["Build SAML SSO integration", "Data migration from legacy DB",
                   "API endpoint for reporting"]
        customer_requests: List of request dicts, each with:
            "request" (str): Description of the request
            "keywords" (list[str]): Keywords related to this request
            "estimated_hours" (float): Customer's estimate of effort
        total_engagement_hours: Total contracted hours for the engagement.
        hours_remaining: Hours remaining in the engagement.

    Returns:
        FDEScope with classified items, boundaries, escalation triggers,
        and flex budget.

    TODO: Implement this function.

    Step-by-step:
      1. Set flex_budget_hours = hours_remaining * 0.1 (10% of remaining time)

      2. For each customer request, classify it:
         a. Check if any keyword in the request matches any word in any
            SOW deliverable (case-insensitive substring match).
         b. If matches found:
            - If estimated_hours <= flex_budget_hours -> "in_scope"
              reason: "Directly supports SOW deliverable: <matching deliverable>"
            - If estimated_hours > flex_budget_hours but <= flex_budget_hours * 2
              -> "stretch"
              reason: "Related to SOW but exceeds flex budget"
         c. If no keyword matches any deliverable -> "out_of_scope"
            reason: "Not covered by current SOW deliverables"

      3. Build boundaries list:
         - "In-scope work is limited to SOW deliverables: <comma-separated list>"
         - "Flex budget of <X> hours available for stretch items"
         - "Out-of-scope requests require SOW amendment"

      4. Build escalation triggers:
         - "Customer requests work with no SOW deliverable match"
         - "Cumulative stretch requests exceed flex budget"
         - "Hours remaining drops below 20% of total engagement"
         - "Customer escalates scope dispute to management"
    """
    # TODO: Implement this function.
    pass


# ============================================================================
# EXERCISE 4: Customer Health Scorer
#
# READ FIRST:
#   03-customer-success-and-expansion.md
#     -> "## Customer Health Scoring"
#        -> "### What Health Metrics to Track" (metric table with weights)
#        -> "### Building a Health Score" (normalization + composite)
#        -> "### Leading vs Lagging Indicators"
#
# ALSO SEE:
#   examples.py
#     -> "4. HEALTH SCORE CALCULATOR"
#        - HealthScoreCalculator.calculate()  (multi-signal scoring)
#        - normalize_metric()                 (0-100 normalization)
#        - classify_risk()                    (RAG status assignment)
#
# Given customer metrics, compute a health score, classify risk,
# and generate recommended actions.
# ============================================================================

def calculate_health_score(
    usage_dau_mau_ratio: float,
    feature_adoption_pct: float,
    support_tickets_30d: int,
    escalation_count_30d: int,
    nps_score: int,
    champion_active: bool,
    days_since_last_contact: int,
    days_to_renewal: int,
) -> HealthScore:
    """
    Calculate a composite customer health score.

    Args:
        usage_dau_mau_ratio: Daily active / monthly active users (0.0-1.0).
        feature_adoption_pct: Percentage of purchased features being used (0-100).
        support_tickets_30d: Number of support tickets in the last 30 days.
        escalation_count_30d: Number of escalated tickets in the last 30 days.
        nps_score: Net Promoter Score from last survey (-100 to 100).
        champion_active: Whether the primary champion is still at the company.
        days_since_last_contact: Days since last meaningful interaction.
        days_to_renewal: Days until contract renewal.

    Returns:
        HealthScore with overall score, status, component scores,
        risk factors, and recommended actions.

    TODO: Implement this function.

    Step-by-step:
      1. Normalize each metric to 0-100:
         - usage_score: dau_mau_ratio * 333 capped at 100
           (0.3+ = 100, 0.0 = 0)
         - adoption_score: feature_adoption_pct (already 0-100)
         - support_score: max(0, 100 - (support_tickets_30d * 10))
           (0 tickets = 100, 10+ tickets = 0)
         - escalation_score: max(0, 100 - (escalation_count_30d * 25))
           (0 escalations = 100, 4+ = 0)
         - nps_score_normalized: (nps_score + 100) / 2
           (-100 = 0, 0 = 50, 100 = 100)
         - champion_score: 100 if champion_active else 0
         - contact_score: max(0, 100 - (days_since_last_contact * 2))
           (0 days = 100, 50+ days = 0)
         - renewal_score: min(100, days_to_renewal)
           (100+ days = 100, approaching 0 = urgent)

      2. Compute weighted average:
         Weights: usage=15, adoption=15, support=10, escalation=15,
                  nps=10, champion=20, contact=5, renewal=10
         overall = sum(score * weight) / sum(weights)

      3. Classify status:
         - >= 80 -> "green"
         - >= 60 -> "amber"
         - >= 40 -> "red"
         - < 40 -> "critical"

      4. Build component_scores dict with all 8 normalized scores.

      5. Identify risk_factors (any condition that is concerning):
         - usage_score < 40: "Product usage is critically low"
         - adoption_score < 50: "Feature adoption below 50%"
         - support_score < 40: "High support ticket volume"
         - escalation_score < 50: "Frequent support escalations"
         - nps_score_normalized < 40: "Low NPS indicates dissatisfaction"
         - not champion_active: "Champion is no longer at the company"
         - contact_score < 40: "No recent engagement with customer"
         - renewal_score < 30: "Renewal approaching with insufficient engagement"

      6. Generate recommended_actions based on status:
         - "green": ["Continue current engagement cadence",
                     "Explore expansion opportunities"]
         - "amber": ["Increase engagement frequency to weekly",
                     "Schedule technical review to address concerns",
                     "Identify and mitigate top risk factor"]
         - "red": ["Escalate internally to account team",
                   "Schedule urgent call with customer stakeholders",
                   "Develop churn intervention plan"]
         - "critical": ["Executive involvement required",
                        "Schedule save call within 48 hours",
                        "Prepare competitive response if needed",
                        "Review contract terms for flexibility"]
    """
    # TODO: Implement this function.
    pass


# ============================================================================
# EXERCISE 5: QBR Preparation Builder
#
# READ FIRST:
#   03-customer-success-and-expansion.md
#     -> "## Quarterly Business Reviews (QBRs)"
#        -> "### QBR Structure" (5-section format)
#        -> "### QBR Preparation Checklist"
#        -> "### How SEs Contribute to QBRs"
#   02-fde-deployment-patterns.md
#     -> "## The FDE Engagement Model" (engagement phases for context)
#
# ALSO SEE:
#   examples.py
#     -> "5. QBR DOCUMENT GENERATOR"
#        - QBRDocumentGenerator.generate()      (full QBR prep)
#        - build_usage_summary()                (usage data -> talking points)
#        - build_risk_items()                   (health data -> risk list)
#
# Given customer account data, generate a complete QBR preparation document.
# ============================================================================

def prepare_qbr(
    account: dict[str, Any],
    usage_metrics: dict[str, Any],
    support_history: dict[str, Any],
    open_issues: list[str],
    previous_action_items: list[dict[str, Any]],
) -> QBRPrep:
    """
    Generate a QBR preparation document.

    Args:
        account: Account information.
            Keys: "name" (str), "tier" (str), "contract_value" (int),
                  "renewal_date" (str), "champion" (str)
        usage_metrics: Usage data for the quarter.
            Keys: "dau_mau_ratio" (float), "api_calls_trend" (str: "up"|"flat"|"down"),
                  "feature_adoption_pct" (float), "top_features" (list[str])
        support_history: Support data for the quarter.
            Keys: "ticket_count" (int), "avg_resolution_hours" (float),
                  "escalation_count" (int), "themes" (list[str])
        open_issues: List of currently open issue descriptions.
        previous_action_items: Action items from last QBR.
            Each: {"item" (str), "owner" (str), "status" (str: "done"|"in_progress"|"not_started")}

    Returns:
        QBRPrep with agenda, summaries, risks, expansion opps, and talking points.

    TODO: Implement this function.

    Step-by-step:
      1. Build the agenda (5-section format from the MD file):
         - "Business Review: Usage metrics and ROI for {account['name']}"
         - "Technical Review: Integration health and support summary"
         - "Roadmap Alignment: Product updates relevant to {account['name']}"
         - "Success Planning: Goals and risk mitigation for next quarter"
         - "Expansion Discussion: Growth opportunities and next steps"

      2. Build usage_summary string:
         - "DAU/MAU ratio: {dau_mau_ratio:.1%}"
         - "API call trend: {api_calls_trend}"
         - "Feature adoption: {feature_adoption_pct:.0f}%"
         - "Top features: {', '.join(top_features)}"
         Concatenate these with newline separators.

      3. Build support_summary string:
         - "Tickets this quarter: {ticket_count}"
         - "Avg resolution: {avg_resolution_hours:.1f} hours"
         - "Escalations: {escalation_count}"
         - "Common themes: {', '.join(themes)}"
         Concatenate with newline separators.

      4. Build risk_items list:
         - If api_calls_trend == "down": "API usage declining — investigate cause"
         - If feature_adoption_pct < 50: "Feature adoption below 50% — training needed"
         - If escalation_count > 2: "Multiple escalations — address root causes"
         - If any open_issues: "Open issues: {len(open_issues)} unresolved"
         - If any previous action items have status "not_started":
           "Unstarted action items from last QBR"

      5. Build expansion_opportunities list:
         - If feature_adoption_pct > 70: "High adoption — candidate for tier upgrade"
         - If api_calls_trend == "up": "Growing usage — may need capacity expansion"
         - Always include: "Explore new use cases with {account['champion']}"

      6. Build action_items_from_last_qbr list:
         - For each previous item: "{item} ({owner}): {status}"

      7. Build talking_points list:
         - If api_calls_trend == "up": "Usage is growing — great adoption story"
         - If api_calls_trend == "down": "Usage is declining — need to understand why"
         - If escalation_count > 0:
           "Address escalation themes: {', '.join(themes)}"
         - "Review progress on previous action items"
         - "Discuss renewal timeline (renewal: {renewal_date})"
    """
    # TODO: Implement this function.
    pass


# ============================================================================
# EXERCISE 6: Expansion Opportunity Identifier
#
# READ FIRST:
#   03-customer-success-and-expansion.md
#     -> "## Expansion Playbooks"
#        -> "### Identifying Expansion Opportunities" (5 vectors table)
#        -> "### The Land-and-Expand Motion" (lifecycle)
#        -> "### Upsell vs Cross-Sell"
#        -> "### Building an Expansion Proposal"
#
# ALSO SEE:
#   examples.py
#     -> "4. HEALTH SCORE CALCULATOR"
#        - Usage trend analysis informs expansion signals
#     -> "5. QBR DOCUMENT GENERATOR"
#        - Expansion section generation
#
# Given current deployment details and customer organization info,
# identify and rank expansion opportunities.
# ============================================================================

def identify_expansion_opportunities(
    current_deployment: dict[str, Any],
    organization: dict[str, Any],
) -> list[ExpansionOpportunity]:
    """
    Identify and rank expansion opportunities for a customer.

    Args:
        current_deployment: Current product deployment details.
            Keys: "tier" (str: "starter"|"professional"|"enterprise"),
                  "seats" (int), "features_used" (list[str]),
                  "features_available" (list[str]),
                  "api_calls_monthly" (int),
                  "api_limit_monthly" (int),
                  "teams_using" (list[str]),
                  "regions" (list[str])
        organization: Customer organization info.
            Keys: "total_employees" (int),
                  "departments" (list[str]),
                  "regions" (list[str]),
                  "growth_stage" (str: "startup"|"scaleup"|"enterprise"),
                  "other_tools" (list[str]: tools they use that we integrate with)

    Returns:
        List of ExpansionOpportunity sorted by likelihood (high first),
        then by vector name alphabetically.

    TODO: Implement this function.

    Step-by-step:
      1. Check for tier upgrade opportunity:
         - If tier != "enterprise" and
           api_calls_monthly > api_limit_monthly * 0.8:
           -> vector="tier_upgrade", likelihood="high",
              description="API usage at {usage_pct}% of limit",
              value="Tier upgrade from {tier} to next tier",
              next_step="Present tier comparison and ROI"

      2. Check for new team opportunities:
         - For each department in organization["departments"] that is NOT
           in current_deployment["teams_using"]:
           -> vector="new_team", likelihood="medium",
              description="Expand to {department} department",
              value="{seats_estimate} additional seats"
              where seats_estimate = total_employees // len(departments),
              next_step="Schedule discovery call with {department} lead"

      3. Check for new geography opportunities:
         - For each region in organization["regions"] that is NOT
           in current_deployment["regions"]:
           -> vector="new_geography", likelihood="medium",
              description="Deploy in {region}",
              value="New regional deployment",
              next_step="Assess compliance requirements for {region}"

      4. Check for unused feature adoption:
         - features_unused = features_available - features_used (set difference)
         - If len(features_unused) > 2:
           -> vector="new_use_case", likelihood="high",
              description="{len(features_unused)} features available but unused",
              value="Increased adoption and stickiness",
              next_step="Schedule feature training session"

      5. Check for cross-sell via integrations:
         - If organization["other_tools"] has any entries:
           -> vector="new_product", likelihood="low",
              description="Integration opportunity with {tools}",
              value="Cross-sell integration products",
              next_step="Map integration touchpoints"

      6. Sort results: high likelihood first, then medium, then low.
         Within same likelihood, sort alphabetically by vector.

      7. Return the sorted list.
    """
    # TODO: Implement this function.
    pass


# ====================================================================
# TESTS — Run with: python exercises.py
# ====================================================================

def test_exercise_1_integration_plan():
    """Test integration plan builder."""
    source = {
        "name": "Salesforce",
        "api_style": "rest",
        "auth": "oauth2",
        "fields": ["contact_id", "email", "name", "company"],
    }
    target = {
        "name": "OurProduct",
        "api_style": "rest",
        "auth": "api_key",
        "fields": ["user_id", "email_address", "full_name", "org_name"],
    }
    requirements = {
        "direction": "one_way",
        "realtime": True,
        "volume_per_day": 5000,
        "field_mappings": [
            {"source": "contact_id", "target": "user_id", "transform": "none"},
            {"source": "email", "target": "email_address", "transform": "lowercase"},
            {"source": "name", "target": "full_name", "transform": "none"},
            {"source": "company", "target": "org_name", "transform": "none"},
        ],
        "latency_tolerance": "minutes",
    }

    plan = build_integration_plan(source, target, requirements)

    assert isinstance(plan, IntegrationPlan), "Should return IntegrationPlan"
    assert plan.pattern == "event_driven", f"Expected event_driven, got {plan.pattern}"
    assert plan.auth_approach == "oauth2_client_credentials", f"Expected oauth2, got {plan.auth_approach}"
    assert plan.api_style == "rest", f"Expected rest, got {plan.api_style}"
    assert len(plan.field_mappings) == 4, f"Expected 4 mappings, got {len(plan.field_mappings)}"
    assert plan.estimated_days > 0, "Should have positive estimated days"
    assert len(plan.risks) > 0, "Should identify at least one risk"
    assert plan.error_handling == "retry_with_exponential_backoff_and_dlq"
    print("Exercise 1: PASSED")


def test_exercise_1_bidirectional():
    """Test integration plan for bidirectional sync."""
    source = {"name": "SystemA", "api_style": "rest", "auth": "api_key", "fields": ["id", "name"]}
    target = {"name": "SystemB", "api_style": "rest", "auth": "api_key", "fields": ["id", "name"]}
    requirements = {
        "direction": "two_way",
        "realtime": False,
        "volume_per_day": 200_000,
        "field_mappings": [
            {"source": "id", "target": "id", "transform": "none"},
            {"source": "name", "target": "name", "transform": "none"},
        ],
        "latency_tolerance": "minutes",
    }

    plan = build_integration_plan(source, target, requirements)

    assert plan.pattern == "bidirectional_sync"
    assert plan.estimated_days >= 12, "Bidirectional + high volume should be 12+ days"
    assert any("Conflict" in r for r in plan.risks), "Should flag conflict resolution risk"
    assert any("Rate" in r or "throttl" in r.lower() for r in plan.risks), "Should flag rate limiting risk"
    print("Exercise 1 (bidirectional): PASSED")


def test_exercise_2_migration_checklist():
    """Test migration checklist generation."""
    checklist = generate_migration_checklist(
        data_size_records=500_000,
        complexity="moderate",
        downtime_tolerance_hours=4.0,
        rollback_required=True,
        regulated_industry=False,
    )

    assert isinstance(checklist, MigrationChecklist), "Should return MigrationChecklist"
    assert checklist.approach == "big_bang", f"Expected big_bang for moderate 500K, got {checklist.approach}"
    assert len(checklist.items) >= 8, f"Expected at least 8 items, got {len(checklist.items)}"

    phases = {item.phase for item in checklist.items}
    assert "pre_migration" in phases, "Should have pre_migration items"
    assert "during_migration" in phases, "Should have during_migration items"
    assert "post_migration" in phases, "Should have post_migration items"

    assert checklist.estimated_total_hours > 0, "Should have positive total hours"
    assert "backup" in checklist.rollback_plan.lower() or "restore" in checklist.rollback_plan.lower(), \
        "Big bang rollback should mention backup/restore"
    print("Exercise 2: PASSED")


def test_exercise_2_regulated():
    """Test migration checklist for regulated industry."""
    checklist = generate_migration_checklist(
        data_size_records=2_000_000,
        complexity="complex",
        downtime_tolerance_hours=0.0,
        rollback_required=True,
        regulated_industry=True,
    )

    assert checklist.approach == "parallel_run", f"Expected parallel_run, got {checklist.approach}"
    assert any("parallel" in item.task.lower() or "comparison" in item.task.lower()
               for item in checklist.items), "Should have parallel-run specific items"
    assert any("regulat" in item.task.lower() or "compliance" in item.task.lower()
               for item in checklist.items), "Should have regulatory validation item"
    print("Exercise 2 (regulated): PASSED")


def test_exercise_3_fde_scope():
    """Test FDE scope definer."""
    sow_deliverables = [
        "Build SAML SSO integration with Okta",
        "Migrate user data from legacy PostgreSQL database",
        "Create REST API endpoints for reporting dashboard",
    ]
    customer_requests = [
        {
            "request": "Add SAML group mapping for role-based access",
            "keywords": ["SAML", "SSO", "role", "access"],
            "estimated_hours": 8,
        },
        {
            "request": "Build a custom mobile app for field workers",
            "keywords": ["mobile", "app", "field"],
            "estimated_hours": 200,
        },
        {
            "request": "Add CSV export to the reporting dashboard",
            "keywords": ["CSV", "export", "reporting", "dashboard"],
            "estimated_hours": 12,
        },
        {
            "request": "Refactor the authentication microservice",
            "keywords": ["refactor", "authentication", "microservice"],
            "estimated_hours": 40,
        },
    ]

    scope = define_fde_scope(
        sow_deliverables=sow_deliverables,
        customer_requests=customer_requests,
        total_engagement_hours=400,
        hours_remaining=200,
    )

    assert isinstance(scope, FDEScope), "Should return FDEScope"
    assert len(scope.items) == 4, f"Expected 4 items, got {len(scope.items)}"

    # SAML group mapping should be in_scope (matches SOW, small effort)
    saml_item = next(i for i in scope.items if "SAML" in i.request)
    assert saml_item.classification == "in_scope", f"SAML item should be in_scope, got {saml_item.classification}"

    # Mobile app should be out_of_scope (no keyword match)
    mobile_item = next(i for i in scope.items if "mobile" in i.request)
    assert mobile_item.classification == "out_of_scope", f"Mobile should be out_of_scope, got {mobile_item.classification}"

    assert len(scope.boundaries) >= 2, "Should have at least 2 boundaries"
    assert len(scope.escalation_triggers) >= 3, "Should have at least 3 escalation triggers"
    assert scope.flex_budget_hours == 20.0, f"Expected 20h flex budget, got {scope.flex_budget_hours}"
    print("Exercise 3: PASSED")


def test_exercise_4_health_score():
    """Test customer health scorer."""
    # Healthy customer
    healthy = calculate_health_score(
        usage_dau_mau_ratio=0.35,
        feature_adoption_pct=75,
        support_tickets_30d=2,
        escalation_count_30d=0,
        nps_score=60,
        champion_active=True,
        days_since_last_contact=7,
        days_to_renewal=180,
    )

    assert isinstance(healthy, HealthScore), "Should return HealthScore"
    assert healthy.status == "green", f"Healthy customer should be green, got {healthy.status}"
    assert healthy.overall_score >= 80, f"Healthy score should be 80+, got {healthy.overall_score}"
    assert len(healthy.risk_factors) == 0 or all("low" not in r.lower() for r in healthy.risk_factors), \
        "Healthy customer should have few/no risk factors"

    # At-risk customer
    at_risk = calculate_health_score(
        usage_dau_mau_ratio=0.05,
        feature_adoption_pct=20,
        support_tickets_30d=12,
        escalation_count_30d=3,
        nps_score=-20,
        champion_active=False,
        days_since_last_contact=45,
        days_to_renewal=30,
    )

    assert at_risk.status in ("red", "critical"), f"At-risk should be red/critical, got {at_risk.status}"
    assert at_risk.overall_score < 40, f"At-risk score should be < 40, got {at_risk.overall_score}"
    assert len(at_risk.risk_factors) >= 4, f"Should identify 4+ risk factors, got {len(at_risk.risk_factors)}"
    assert len(at_risk.recommended_actions) >= 3, f"Should have 3+ actions, got {len(at_risk.recommended_actions)}"
    print("Exercise 4: PASSED")


def test_exercise_5_qbr_prep():
    """Test QBR preparation builder."""
    account = {
        "name": "Acme Corp",
        "tier": "professional",
        "contract_value": 120000,
        "renewal_date": "2025-06-30",
        "champion": "Jane Doe",
    }
    usage_metrics = {
        "dau_mau_ratio": 0.25,
        "api_calls_trend": "down",
        "feature_adoption_pct": 45.0,
        "top_features": ["dashboard", "API", "webhooks"],
    }
    support_history = {
        "ticket_count": 8,
        "avg_resolution_hours": 12.5,
        "escalation_count": 3,
        "themes": ["API latency", "documentation gaps"],
    }
    open_issues = ["API timeout on large queries", "SSO redirect loop"]
    previous_action_items = [
        {"item": "Fix API latency", "owner": "Engineering", "status": "in_progress"},
        {"item": "Update integration docs", "owner": "SE team", "status": "not_started"},
    ]

    qbr = prepare_qbr(account, usage_metrics, support_history, open_issues, previous_action_items)

    assert isinstance(qbr, QBRPrep), "Should return QBRPrep"
    assert len(qbr.agenda) == 5, f"Expected 5 agenda items, got {len(qbr.agenda)}"
    assert "Acme Corp" in qbr.agenda[0], "Agenda should reference account name"
    assert "25.0%" in qbr.usage_summary or "0.25" in qbr.usage_summary, "Should include DAU/MAU"
    assert "8" in qbr.support_summary, "Should include ticket count"
    assert len(qbr.risk_items) >= 3, f"Expected 3+ risk items, got {len(qbr.risk_items)}"
    assert len(qbr.expansion_opportunities) >= 1, f"Expected 1+ expansion opps"
    assert len(qbr.action_items_from_last_qbr) == 2
    assert "not_started" in qbr.action_items_from_last_qbr[1]
    assert len(qbr.talking_points) >= 3, f"Expected 3+ talking points"
    print("Exercise 5: PASSED")


def test_exercise_6_expansion():
    """Test expansion opportunity identifier."""
    current_deployment = {
        "tier": "professional",
        "seats": 50,
        "features_used": ["dashboard", "API", "webhooks"],
        "features_available": ["dashboard", "API", "webhooks", "SSO", "audit_log",
                               "custom_reports", "data_export", "alerting"],
        "api_calls_monthly": 85000,
        "api_limit_monthly": 100000,
        "teams_using": ["Engineering", "Product"],
        "regions": ["US"],
    }
    organization = {
        "total_employees": 500,
        "departments": ["Engineering", "Product", "Marketing", "Sales", "Support"],
        "regions": ["US", "EU", "APAC"],
        "growth_stage": "scaleup",
        "other_tools": ["Salesforce", "Jira"],
    }

    opps = identify_expansion_opportunities(current_deployment, organization)

    assert isinstance(opps, list), "Should return a list"
    assert len(opps) >= 3, f"Expected 3+ opportunities, got {len(opps)}"

    vectors = [o.vector for o in opps]
    assert "tier_upgrade" in vectors, "Should identify tier upgrade (85% API usage)"
    assert "new_team" in vectors, "Should identify new team opportunities"
    assert "new_use_case" in vectors, "Should identify unused features"
    assert "new_geography" in vectors, "Should identify new geography"

    # Check sorting: high likelihood should come first
    high_indices = [i for i, o in enumerate(opps) if o.likelihood == "high"]
    medium_indices = [i for i, o in enumerate(opps) if o.likelihood == "medium"]
    low_indices = [i for i, o in enumerate(opps) if o.likelihood == "low"]

    if high_indices and medium_indices:
        assert max(high_indices) < min(medium_indices), "High should come before medium"
    if medium_indices and low_indices:
        assert max(medium_indices) < min(low_indices), "Medium should come before low"

    print("Exercise 6: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("Module 04: Integration, Deployment & Customer Success")
    print("=" * 60)
    print()

    tests = [
        ("Exercise 1: Integration Plan", test_exercise_1_integration_plan),
        ("Exercise 1b: Bidirectional", test_exercise_1_bidirectional),
        ("Exercise 2: Migration Checklist", test_exercise_2_migration_checklist),
        ("Exercise 2b: Regulated", test_exercise_2_regulated),
        ("Exercise 3: FDE Scope", test_exercise_3_fde_scope),
        ("Exercise 4: Health Score", test_exercise_4_health_score),
        ("Exercise 5: QBR Prep", test_exercise_5_qbr_prep),
        ("Exercise 6: Expansion Opps", test_exercise_6_expansion),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except (AssertionError, Exception) as e:
            print(f"{name}: FAILED - {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")

    if failed == 0:
        print("All exercises complete!")
    else:
        print("Keep working on the failed exercises.")
