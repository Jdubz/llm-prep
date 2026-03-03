"""
Module 04: Integration, Deployment, and Customer Success — Complete, Runnable Patterns

These examples demonstrate core integration planning, migration management,
FDE engagement tracking, customer health scoring, and QBR preparation.
Each section is self-contained and can be run independently.

Run with: python examples.py
"""

from __future__ import annotations

import math
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# 1. INTEGRATION ARCHITECTURE PLANNER
# ---------------------------------------------------------------------------

@dataclass
class FieldMapping:
    source_field: str
    target_field: str
    transform: str
    notes: str = ""


@dataclass
class IntegrationPlan:
    pattern: str
    auth_approach: str
    api_style: str
    field_mappings: list[FieldMapping]
    error_handling: str
    estimated_days: int
    risks: list[str]
    architecture_description: str = ""


class IntegrationPlanner:
    """
    Complete integration design tool that selects the right pattern,
    auth approach, API style, and generates a full integration plan
    with timeline and risk assessment.
    """

    PATTERN_DESCRIPTIONS = {
        "unidirectional_sync": "One-way data flow from source to target via API.",
        "bidirectional_sync": "Two-way sync with conflict resolution between systems.",
        "event_driven": "Real-time event notifications via webhooks or streaming.",
        "batch": "Periodic bulk data transfer via ETL pipeline.",
    }

    ERROR_STRATEGIES = {
        "event_driven": "retry_with_exponential_backoff_and_dlq",
        "batch": "log_and_continue_with_error_report",
        "bidirectional_sync": "conflict_resolution_last_write_wins",
        "unidirectional_sync": "retry_with_exponential_backoff",
    }

    def plan(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        requirements: dict[str, Any],
    ) -> IntegrationPlan:
        """Generate a complete integration plan."""
        pattern = self._select_pattern(requirements)
        api_style = self._select_api_style(source, target, requirements)
        auth = self._select_auth(source, target)
        mappings = self._build_mappings(requirements.get("field_mappings", []))
        error_handling = self.ERROR_STRATEGIES.get(pattern, "retry_with_backoff")
        days = self._estimate_days(pattern, mappings, requirements)
        risks = self._identify_risks(pattern, requirements, auth)

        architecture_desc = (
            f"Integration: {source['name']} -> {target['name']}\n"
            f"Pattern: {pattern} — {self.PATTERN_DESCRIPTIONS.get(pattern, '')}\n"
            f"API Style: {api_style}\n"
            f"Auth: {auth}\n"
            f"Error Handling: {error_handling}\n"
            f"Estimated Timeline: {days} days"
        )

        return IntegrationPlan(
            pattern=pattern,
            auth_approach=auth,
            api_style=api_style,
            field_mappings=mappings,
            error_handling=error_handling,
            estimated_days=days,
            risks=risks,
            architecture_description=architecture_desc,
        )

    def _select_pattern(self, requirements: dict[str, Any]) -> str:
        direction = requirements.get("direction", "one_way")
        latency = requirements.get("latency_tolerance", "minutes")

        if direction == "two_way":
            return "bidirectional_sync"
        if latency in ("seconds", "minutes"):
            return "event_driven"
        return "batch"

    def _select_api_style(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        requirements: dict[str, Any],
    ) -> str:
        volume = requirements.get("volume_per_day", 0)
        num_mappings = len(requirements.get("field_mappings", []))

        if (source.get("api_style") == "grpc" and
            target.get("api_style") == "grpc" and
            volume > 100_000):
            return "grpc"
        if source.get("api_style") == "graphql" and num_mappings >= 5:
            return "graphql"
        return "rest"

    def _select_auth(self, source: dict[str, Any], target: dict[str, Any]) -> str:
        source_auth = source.get("auth", "api_key")
        target_auth = target.get("auth", "api_key")

        if "oauth2" in (source_auth, target_auth):
            return "oauth2_client_credentials"
        if "saml" in (source_auth, target_auth):
            return "saml_sso"
        return "api_key"

    def _build_mappings(self, raw_mappings: list[dict]) -> list[FieldMapping]:
        return [
            FieldMapping(
                source_field=m["source"],
                target_field=m["target"],
                transform=m.get("transform", "none"),
                notes=m.get("notes", ""),
            )
            for m in raw_mappings
        ]

    def _estimate_days(
        self,
        pattern: str,
        mappings: list[FieldMapping],
        requirements: dict[str, Any],
    ) -> int:
        base = 5
        mapping_days = len(mappings) // 2
        bidirectional_bonus = 5 if pattern == "bidirectional_sync" else 0
        volume_bonus = 3 if requirements.get("volume_per_day", 0) > 100_000 else 0
        raw = base + mapping_days + bidirectional_bonus + volume_bonus
        return math.ceil(raw * 1.5)

    def _identify_risks(
        self,
        pattern: str,
        requirements: dict[str, Any],
        auth: str,
    ) -> list[str]:
        risks = ["Data mapping validation needed with customer"]
        if pattern == "bidirectional_sync":
            risks.append("Conflict resolution edge cases")
        if requirements.get("volume_per_day", 0) > 100_000:
            risks.append("Rate limiting may require throttling")
        if auth == "saml_sso":
            risks.append("SSO configuration requires customer IT involvement")
        return risks


def demo_integration_planner():
    """Demonstrate the integration architecture planner."""
    planner = IntegrationPlanner()

    source = {
        "name": "Salesforce",
        "api_style": "rest",
        "auth": "oauth2",
        "fields": ["contact_id", "email", "name", "company", "phone"],
    }
    target = {
        "name": "ProductDB",
        "api_style": "rest",
        "auth": "api_key",
        "fields": ["user_id", "email_address", "full_name", "org_name", "phone_number"],
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
            {"source": "phone", "target": "phone_number", "transform": "normalize_e164"},
        ],
        "latency_tolerance": "minutes",
    }

    plan = planner.plan(source, target, requirements)
    print("=== Integration Plan ===")
    print(plan.architecture_description)
    print(f"\nField Mappings ({len(plan.field_mappings)}):")
    for m in plan.field_mappings:
        print(f"  {m.source_field} -> {m.target_field} [{m.transform}]")
    print(f"\nRisks:")
    for r in plan.risks:
        print(f"  - {r}")


# ---------------------------------------------------------------------------
# 2. MIGRATION PLAN GENERATOR
# ---------------------------------------------------------------------------

@dataclass
class ChecklistItem:
    phase: str
    task: str
    priority: int
    estimated_hours: float


@dataclass
class MigrationPlan:
    approach: str
    checklist: list[ChecklistItem]
    estimated_total_hours: float
    rollback_plan: str
    risks: list[str]
    timeline_summary: str = ""


class MigrationPlanGenerator:
    """
    Full data migration plan builder that selects the right approach,
    generates a phased checklist, estimates timelines, and identifies risks.
    """

    ROLLBACK_PLANS = {
        "parallel_run": "Cut back to original system. No data loss. Disable write-through to new system.",
        "phased": "Revert current phase using phase-specific rollback script. Previous phases unaffected.",
        "big_bang": "Restore from pre-migration backup taken immediately before migration. Downtime expected.",
    }

    def generate(
        self,
        data_size_records: int,
        complexity: str,
        downtime_tolerance_hours: float,
        rollback_required: bool,
        regulated_industry: bool,
    ) -> MigrationPlan:
        """Generate a complete migration plan."""
        approach = self._select_approach(
            data_size_records, complexity, downtime_tolerance_hours, regulated_industry
        )
        checklist = self._build_checklist(
            approach, data_size_records, rollback_required, regulated_industry
        )
        total_hours = sum(item.estimated_hours for item in checklist) * 1.5
        risks = self._identify_risks(data_size_records, complexity, rollback_required)

        timeline_summary = (
            f"Approach: {approach}\n"
            f"Records: {data_size_records:,}\n"
            f"Complexity: {complexity}\n"
            f"Estimated hours: {total_hours:.0f} (with 50% buffer)\n"
            f"Checklist items: {len(checklist)}"
        )

        return MigrationPlan(
            approach=approach,
            checklist=checklist,
            estimated_total_hours=total_hours,
            rollback_plan=self.ROLLBACK_PLANS[approach],
            risks=risks,
            timeline_summary=timeline_summary,
        )

    def _select_approach(
        self,
        data_size: int,
        complexity: str,
        downtime_hours: float,
        regulated: bool,
    ) -> str:
        if regulated or downtime_hours == 0.0:
            return "parallel_run"
        if data_size > 1_000_000 or complexity == "complex":
            return "phased"
        return "big_bang"

    def _build_checklist(
        self,
        approach: str,
        data_size: int,
        rollback_required: bool,
        regulated: bool,
    ) -> list[ChecklistItem]:
        items = []

        # Pre-migration
        items.append(ChecklistItem("pre_migration", "Complete data mapping document", 1, 8))
        items.append(ChecklistItem("pre_migration", "Profile source data for quality issues", 1, 4))
        items.append(ChecklistItem("pre_migration", "Run test migration on 10% subset", 1, 8))
        items.append(ChecklistItem(
            "pre_migration", "Document rollback procedure",
            1 if rollback_required else 2, 4
        ))
        items.append(ChecklistItem("pre_migration", "Establish performance benchmarks", 2, 2))

        if approach != "parallel_run":
            items.append(ChecklistItem("pre_migration", "Schedule maintenance window", 1, 1))
        if approach == "parallel_run":
            items.append(ChecklistItem("pre_migration", "Set up parallel environment", 1, 16))

        # During migration
        migration_hours = max(1.0, min(48.0, data_size / 100_000))
        items.append(ChecklistItem(
            "during_migration", "Execute migration job with monitoring", 1, migration_hours
        ))
        items.append(ChecklistItem(
            "during_migration", "Monitor error log in real-time", 1, migration_hours
        ))
        items.append(ChecklistItem("during_migration", "Perform spot checks on migrated records", 1, 2))

        if approach == "parallel_run":
            items.append(ChecklistItem(
                "during_migration", "Run comparison between systems", 1, 4
            ))

        # Post-migration
        items.append(ChecklistItem("post_migration", "Validate record counts", 1, 1))
        items.append(ChecklistItem("post_migration", "Run data integrity checks", 1, 4))
        items.append(ChecklistItem("post_migration", "Execute application smoke tests", 1, 2))
        items.append(ChecklistItem("post_migration", "Complete user acceptance testing", 1, 8))

        if regulated:
            items.append(ChecklistItem("post_migration", "Regulatory compliance validation", 1, 8))

        items.append(ChecklistItem("post_migration", "Migration retrospective", 3, 2))

        return items

    def _identify_risks(
        self,
        data_size: int,
        complexity: str,
        rollback_required: bool,
    ) -> list[str]:
        risks = ["Source data quality issues may require manual cleanup"]
        if data_size > 10_000_000:
            risks.append("Migration may exceed maintenance window")
        if complexity == "complex":
            risks.append("Custom transform logic may have edge cases")
        if not rollback_required:
            risks.append("No rollback plan increases risk of data loss")
        return risks


def demo_migration_planner():
    """Demonstrate the migration plan generator."""
    generator = MigrationPlanGenerator()

    plan = generator.generate(
        data_size_records=5_000_000,
        complexity="moderate",
        downtime_tolerance_hours=4.0,
        rollback_required=True,
        regulated_industry=False,
    )

    print("\n=== Migration Plan ===")
    print(plan.timeline_summary)
    print(f"\nRollback: {plan.rollback_plan}")
    print(f"\nChecklist ({len(plan.checklist)} items):")
    for phase in ["pre_migration", "during_migration", "post_migration"]:
        phase_items = [i for i in plan.checklist if i.phase == phase]
        print(f"\n  {phase.upper().replace('_', ' ')}:")
        for item in phase_items:
            priority_marker = "*" * item.priority
            print(f"    [{priority_marker}] {item.task} ({item.estimated_hours}h)")
    print(f"\nRisks:")
    for r in plan.risks:
        print(f"  - {r}")


# ---------------------------------------------------------------------------
# 3. FDE ENGAGEMENT TRACKER
# ---------------------------------------------------------------------------

@dataclass
class ScopeItem:
    request: str
    classification: str  # "in_scope", "out_of_scope", "stretch"
    reason: str
    estimated_hours: float
    date_requested: str = ""


@dataclass
class Milestone:
    name: str
    target_date: str
    status: str  # "not_started", "in_progress", "completed", "at_risk"
    deliverables: list[str] = field(default_factory=list)
    notes: str = ""


class FDEEngagementTracker:
    """
    Engagement lifecycle manager with scope tracking, milestone monitoring,
    and scope classification. Maintains a running view of engagement health.
    """

    def __init__(
        self,
        sow_deliverables: list[str],
        total_hours: float,
        milestones: list[Milestone],
    ):
        self.sow_deliverables = sow_deliverables
        self.total_hours = total_hours
        self.hours_used = 0.0
        self.milestones = milestones
        self.scope_items: list[ScopeItem] = []
        self.flex_budget_pct = 0.10  # 10% of remaining hours

    @property
    def hours_remaining(self) -> float:
        return max(0, self.total_hours - self.hours_used)

    @property
    def flex_budget_hours(self) -> float:
        return self.hours_remaining * self.flex_budget_pct

    def log_hours(self, hours: float, description: str = "") -> None:
        """Record hours spent on the engagement."""
        self.hours_used += hours

    def classify_request(self, request: str, keywords: list[str], estimated_hours: float) -> ScopeItem:
        """
        Classify a customer request as in_scope, stretch, or out_of_scope.

        Uses keyword matching against SOW deliverables.
        """
        matching_deliverable = None
        for deliverable in self.sow_deliverables:
            deliverable_lower = deliverable.lower()
            for keyword in keywords:
                if keyword.lower() in deliverable_lower:
                    matching_deliverable = deliverable
                    break
            if matching_deliverable:
                break

        if matching_deliverable:
            if estimated_hours <= self.flex_budget_hours:
                classification = "in_scope"
                reason = f"Directly supports SOW deliverable: {matching_deliverable}"
            elif estimated_hours <= self.flex_budget_hours * 2:
                classification = "stretch"
                reason = f"Related to SOW but exceeds flex budget ({self.flex_budget_hours:.0f}h)"
            else:
                classification = "out_of_scope"
                reason = f"Effort ({estimated_hours}h) far exceeds flex budget"
        else:
            classification = "out_of_scope"
            reason = "Not covered by current SOW deliverables"

        item = ScopeItem(
            request=request,
            classification=classification,
            reason=reason,
            estimated_hours=estimated_hours,
            date_requested=datetime.now().strftime("%Y-%m-%d"),
        )
        self.scope_items.append(item)
        return item

    def get_scope_report(self) -> dict[str, Any]:
        """Generate a scope tracking report."""
        in_scope = [i for i in self.scope_items if i.classification == "in_scope"]
        stretch = [i for i in self.scope_items if i.classification == "stretch"]
        out_of_scope = [i for i in self.scope_items if i.classification == "out_of_scope"]

        return {
            "total_requests": len(self.scope_items),
            "in_scope": len(in_scope),
            "stretch": len(stretch),
            "out_of_scope": len(out_of_scope),
            "flex_budget_hours": self.flex_budget_hours,
            "stretch_hours_requested": sum(i.estimated_hours for i in stretch),
            "hours_used": self.hours_used,
            "hours_remaining": self.hours_remaining,
            "utilization_pct": (self.hours_used / self.total_hours * 100) if self.total_hours > 0 else 0,
            "boundaries": [
                f"In-scope work limited to SOW: {', '.join(self.sow_deliverables)}",
                f"Flex budget: {self.flex_budget_hours:.0f} hours for stretch items",
                "Out-of-scope requests require SOW amendment",
            ],
            "escalation_triggers": [
                "Customer requests work with no SOW deliverable match",
                "Cumulative stretch requests exceed flex budget",
                f"Hours remaining drops below {self.total_hours * 0.2:.0f}h (20%)",
                "Customer escalates scope dispute to management",
            ],
        }

    def update_milestone(self, name: str, status: str, notes: str = "") -> None:
        """Update a milestone's status."""
        for ms in self.milestones:
            if ms.name == name:
                ms.status = status
                if notes:
                    ms.notes = notes
                return
        raise ValueError(f"Milestone not found: {name}")

    def get_engagement_status(self) -> dict[str, Any]:
        """Get overall engagement health status."""
        completed = sum(1 for m in self.milestones if m.status == "completed")
        at_risk = sum(1 for m in self.milestones if m.status == "at_risk")
        total = len(self.milestones)

        health = "green"
        if at_risk > 0:
            health = "amber"
        if at_risk >= total // 2:
            health = "red"
        if self.hours_remaining < self.total_hours * 0.1:
            health = "red"

        return {
            "health": health,
            "milestones_completed": completed,
            "milestones_total": total,
            "milestones_at_risk": at_risk,
            "hours_used": self.hours_used,
            "hours_remaining": self.hours_remaining,
            "utilization_pct": round(self.hours_used / self.total_hours * 100, 1),
        }


def demo_fde_tracker():
    """Demonstrate the FDE engagement tracker."""
    milestones = [
        Milestone("SAML SSO Integration", "2025-03-15", "in_progress",
                  deliverables=["Okta SAML config", "JIT provisioning", "Group mapping"]),
        Milestone("Data Migration", "2025-04-01", "not_started",
                  deliverables=["Schema mapping", "Migration script", "Validation"]),
        Milestone("Reporting API", "2025-04-15", "not_started",
                  deliverables=["REST endpoints", "Documentation", "Tests"]),
    ]

    tracker = FDEEngagementTracker(
        sow_deliverables=[
            "Build SAML SSO integration with Okta",
            "Migrate user data from legacy PostgreSQL database",
            "Create REST API endpoints for reporting dashboard",
        ],
        total_hours=400,
        milestones=milestones,
    )

    tracker.log_hours(80, "SAML SSO development")

    # Classify some customer requests
    requests = [
        ("Add SAML group mapping for role-based access", ["SAML", "SSO", "role"], 8),
        ("Build a mobile app", ["mobile", "app"], 200),
        ("Add CSV export to reporting", ["CSV", "reporting", "dashboard"], 12),
    ]

    print("\n=== FDE Engagement Tracker ===")
    for req, keywords, hours in requests:
        item = tracker.classify_request(req, keywords, hours)
        print(f"  [{item.classification.upper()}] {req}")
        print(f"    Reason: {item.reason}")

    report = tracker.get_scope_report()
    status = tracker.get_engagement_status()

    print(f"\nEngagement Health: {status['health'].upper()}")
    print(f"Hours: {status['hours_used']}/{tracker.total_hours} ({status['utilization_pct']}%)")
    print(f"Scope: {report['in_scope']} in-scope, {report['stretch']} stretch, {report['out_of_scope']} out-of-scope")


# ---------------------------------------------------------------------------
# 4. HEALTH SCORE CALCULATOR
# ---------------------------------------------------------------------------

@dataclass
class HealthScore:
    overall_score: float
    status: str
    component_scores: dict[str, float]
    risk_factors: list[str]
    recommended_actions: list[str]
    trend: str = ""  # "improving", "stable", "declining"


class HealthScoreCalculator:
    """
    Multi-signal customer health scoring with configurable weights,
    trend analysis, and risk-based action recommendations.
    """

    WEIGHTS = {
        "usage": 15,
        "adoption": 15,
        "support": 10,
        "escalation": 15,
        "nps": 10,
        "champion": 20,
        "contact": 5,
        "renewal": 10,
    }

    STATUS_THRESHOLDS = [
        (80, "green"),
        (60, "amber"),
        (40, "red"),
        (0, "critical"),
    ]

    ACTIONS = {
        "green": [
            "Continue current engagement cadence",
            "Explore expansion opportunities",
        ],
        "amber": [
            "Increase engagement frequency to weekly",
            "Schedule technical review to address concerns",
            "Identify and mitigate top risk factor",
        ],
        "red": [
            "Escalate internally to account team",
            "Schedule urgent call with customer stakeholders",
            "Develop churn intervention plan",
        ],
        "critical": [
            "Executive involvement required",
            "Schedule save call within 48 hours",
            "Prepare competitive response if needed",
            "Review contract terms for flexibility",
        ],
    }

    def calculate(
        self,
        usage_dau_mau_ratio: float,
        feature_adoption_pct: float,
        support_tickets_30d: int,
        escalation_count_30d: int,
        nps_score: int,
        champion_active: bool,
        days_since_last_contact: int,
        days_to_renewal: int,
        previous_score: float | None = None,
    ) -> HealthScore:
        """Calculate composite health score from multiple signals."""

        # Normalize each metric to 0-100
        scores = {
            "usage": min(100, usage_dau_mau_ratio * 333),
            "adoption": feature_adoption_pct,
            "support": max(0, 100 - (support_tickets_30d * 10)),
            "escalation": max(0, 100 - (escalation_count_30d * 25)),
            "nps": (nps_score + 100) / 2,
            "champion": 100 if champion_active else 0,
            "contact": max(0, 100 - (days_since_last_contact * 2)),
            "renewal": min(100, days_to_renewal),
        }

        # Weighted average
        total_weighted = sum(scores[k] * self.WEIGHTS[k] for k in scores)
        total_weight = sum(self.WEIGHTS.values())
        overall = total_weighted / total_weight

        # Status classification
        status = "critical"
        for threshold, label in self.STATUS_THRESHOLDS:
            if overall >= threshold:
                status = label
                break

        # Risk factors
        risk_factors = []
        if scores["usage"] < 40:
            risk_factors.append("Product usage is critically low")
        if scores["adoption"] < 50:
            risk_factors.append("Feature adoption below 50%")
        if scores["support"] < 40:
            risk_factors.append("High support ticket volume")
        if scores["escalation"] < 50:
            risk_factors.append("Frequent support escalations")
        if scores["nps"] < 40:
            risk_factors.append("Low NPS indicates dissatisfaction")
        if not champion_active:
            risk_factors.append("Champion is no longer at the company")
        if scores["contact"] < 40:
            risk_factors.append("No recent engagement with customer")
        if scores["renewal"] < 30:
            risk_factors.append("Renewal approaching with insufficient engagement")

        # Trend analysis
        trend = "stable"
        if previous_score is not None:
            diff = overall - previous_score
            if diff > 5:
                trend = "improving"
            elif diff < -5:
                trend = "declining"

        return HealthScore(
            overall_score=round(overall, 1),
            status=status,
            component_scores={k: round(v, 1) for k, v in scores.items()},
            risk_factors=risk_factors,
            recommended_actions=self.ACTIONS.get(status, []),
            trend=trend,
        )


def demo_health_scorer():
    """Demonstrate the health score calculator."""
    calculator = HealthScoreCalculator()

    print("\n=== Customer Health Scores ===")

    # Healthy customer
    healthy = calculator.calculate(
        usage_dau_mau_ratio=0.35,
        feature_adoption_pct=75,
        support_tickets_30d=2,
        escalation_count_30d=0,
        nps_score=60,
        champion_active=True,
        days_since_last_contact=7,
        days_to_renewal=180,
    )
    print(f"\nHealthy Customer: {healthy.overall_score}/100 [{healthy.status.upper()}]")
    print(f"  Risks: {len(healthy.risk_factors)}")
    for action in healthy.recommended_actions:
        print(f"  Action: {action}")

    # At-risk customer
    at_risk = calculator.calculate(
        usage_dau_mau_ratio=0.05,
        feature_adoption_pct=20,
        support_tickets_30d=12,
        escalation_count_30d=3,
        nps_score=-20,
        champion_active=False,
        days_since_last_contact=45,
        days_to_renewal=30,
        previous_score=55.0,
    )
    print(f"\nAt-Risk Customer: {at_risk.overall_score}/100 [{at_risk.status.upper()}] ({at_risk.trend})")
    print(f"  Risk Factors:")
    for risk in at_risk.risk_factors:
        print(f"    - {risk}")
    print(f"  Actions:")
    for action in at_risk.recommended_actions:
        print(f"    - {action}")


# ---------------------------------------------------------------------------
# 5. QBR DOCUMENT GENERATOR
# ---------------------------------------------------------------------------

@dataclass
class QBRDocument:
    account_name: str
    quarter: str
    agenda: list[str]
    usage_summary: str
    support_summary: str
    risk_items: list[str]
    expansion_opportunities: list[str]
    action_items_from_last_qbr: list[str]
    talking_points: list[str]
    executive_summary: str = ""


class QBRDocumentGenerator:
    """
    Complete QBR preparation tool that generates an agenda, summaries,
    risk items, expansion opportunities, and talking points from
    customer account data.
    """

    def generate(
        self,
        account: dict[str, Any],
        usage_metrics: dict[str, Any],
        support_history: dict[str, Any],
        open_issues: list[str],
        previous_action_items: list[dict[str, Any]],
    ) -> QBRDocument:
        """Generate a complete QBR document."""
        name = account["name"]

        agenda = [
            f"Business Review: Usage metrics and ROI for {name}",
            "Technical Review: Integration health and support summary",
            f"Roadmap Alignment: Product updates relevant to {name}",
            "Success Planning: Goals and risk mitigation for next quarter",
            "Expansion Discussion: Growth opportunities and next steps",
        ]

        usage_summary = self._build_usage_summary(usage_metrics)
        support_summary = self._build_support_summary(support_history)
        risk_items = self._build_risk_items(usage_metrics, support_history, open_issues, previous_action_items)
        expansion_opps = self._build_expansion_opportunities(usage_metrics, account)
        action_items = self._format_action_items(previous_action_items)
        talking_points = self._build_talking_points(usage_metrics, support_history, account)

        executive_summary = (
            f"QBR Preparation for {name}\n"
            f"Tier: {account.get('tier', 'N/A')} | "
            f"Contract: ${account.get('contract_value', 0):,} | "
            f"Renewal: {account.get('renewal_date', 'N/A')}\n"
            f"Risks: {len(risk_items)} | Expansion Opps: {len(expansion_opps)}"
        )

        return QBRDocument(
            account_name=name,
            quarter=datetime.now().strftime("Q%q %Y").replace(
                "Q%q", f"Q{(datetime.now().month - 1) // 3 + 1}"
            ),
            agenda=agenda,
            usage_summary=usage_summary,
            support_summary=support_summary,
            risk_items=risk_items,
            expansion_opportunities=expansion_opps,
            action_items_from_last_qbr=action_items,
            talking_points=talking_points,
            executive_summary=executive_summary,
        )

    def _build_usage_summary(self, metrics: dict[str, Any]) -> str:
        dau_mau = metrics.get("dau_mau_ratio", 0)
        api_trend = metrics.get("api_calls_trend", "flat")
        adoption = metrics.get("feature_adoption_pct", 0)
        features = metrics.get("top_features", [])

        lines = [
            f"DAU/MAU ratio: {dau_mau:.1%}",
            f"API call trend: {api_trend}",
            f"Feature adoption: {adoption:.0f}%",
            f"Top features: {', '.join(features)}",
        ]
        return "\n".join(lines)

    def _build_support_summary(self, history: dict[str, Any]) -> str:
        lines = [
            f"Tickets this quarter: {history.get('ticket_count', 0)}",
            f"Avg resolution: {history.get('avg_resolution_hours', 0):.1f} hours",
            f"Escalations: {history.get('escalation_count', 0)}",
            f"Common themes: {', '.join(history.get('themes', []))}",
        ]
        return "\n".join(lines)

    def _build_risk_items(
        self,
        usage: dict[str, Any],
        support: dict[str, Any],
        open_issues: list[str],
        prev_actions: list[dict[str, Any]],
    ) -> list[str]:
        risks = []
        if usage.get("api_calls_trend") == "down":
            risks.append("API usage declining — investigate cause")
        if usage.get("feature_adoption_pct", 100) < 50:
            risks.append("Feature adoption below 50% — training needed")
        if support.get("escalation_count", 0) > 2:
            risks.append("Multiple escalations — address root causes")
        if open_issues:
            risks.append(f"Open issues: {len(open_issues)} unresolved")
        not_started = [a for a in prev_actions if a.get("status") == "not_started"]
        if not_started:
            risks.append("Unstarted action items from last QBR")
        return risks

    def _build_expansion_opportunities(
        self,
        usage: dict[str, Any],
        account: dict[str, Any],
    ) -> list[str]:
        opps = []
        if usage.get("feature_adoption_pct", 0) > 70:
            opps.append("High adoption — candidate for tier upgrade")
        if usage.get("api_calls_trend") == "up":
            opps.append("Growing usage — may need capacity expansion")
        champion = account.get("champion", "the champion")
        opps.append(f"Explore new use cases with {champion}")
        return opps

    def _format_action_items(self, items: list[dict[str, Any]]) -> list[str]:
        return [
            f"{item['item']} ({item['owner']}): {item['status']}"
            for item in items
        ]

    def _build_talking_points(
        self,
        usage: dict[str, Any],
        support: dict[str, Any],
        account: dict[str, Any],
    ) -> list[str]:
        points = []
        trend = usage.get("api_calls_trend", "flat")
        if trend == "up":
            points.append("Usage is growing — great adoption story")
        elif trend == "down":
            points.append("Usage is declining — need to understand why")

        if support.get("escalation_count", 0) > 0:
            themes = ", ".join(support.get("themes", []))
            points.append(f"Address escalation themes: {themes}")

        points.append("Review progress on previous action items")
        points.append(f"Discuss renewal timeline (renewal: {account.get('renewal_date', 'TBD')})")
        return points


def demo_qbr_generator():
    """Demonstrate the QBR document generator."""
    generator = QBRDocumentGenerator()

    qbr = generator.generate(
        account={
            "name": "Acme Corp",
            "tier": "professional",
            "contract_value": 120000,
            "renewal_date": "2025-06-30",
            "champion": "Jane Doe",
        },
        usage_metrics={
            "dau_mau_ratio": 0.25,
            "api_calls_trend": "down",
            "feature_adoption_pct": 45.0,
            "top_features": ["dashboard", "API", "webhooks"],
        },
        support_history={
            "ticket_count": 8,
            "avg_resolution_hours": 12.5,
            "escalation_count": 3,
            "themes": ["API latency", "documentation gaps"],
        },
        open_issues=["API timeout on large queries", "SSO redirect loop"],
        previous_action_items=[
            {"item": "Fix API latency", "owner": "Engineering", "status": "in_progress"},
            {"item": "Update docs", "owner": "SE team", "status": "not_started"},
        ],
    )

    print("\n=== QBR Document ===")
    print(qbr.executive_summary)
    print(f"\nAgenda:")
    for i, item in enumerate(qbr.agenda, 1):
        print(f"  {i}. {item}")
    print(f"\nUsage Summary:\n  {qbr.usage_summary.replace(chr(10), chr(10) + '  ')}")
    print(f"\nSupport Summary:\n  {qbr.support_summary.replace(chr(10), chr(10) + '  ')}")
    print(f"\nRisk Items:")
    for r in qbr.risk_items:
        print(f"  ! {r}")
    print(f"\nExpansion Opportunities:")
    for o in qbr.expansion_opportunities:
        print(f"  + {o}")
    print(f"\nTalking Points:")
    for t in qbr.talking_points:
        print(f"  > {t}")
    print(f"\nPrevious Action Items:")
    for a in qbr.action_items_from_last_qbr:
        print(f"  - {a}")


# ---------------------------------------------------------------------------
# Usage Example
# ---------------------------------------------------------------------------

def main():
    """Run all demonstrations."""
    demo_integration_planner()
    demo_migration_planner()
    demo_fde_tracker()
    demo_health_scorer()
    demo_qbr_generator()


if __name__ == "__main__":
    main()
