"""
Module 05: Product Knowledge and Cross-Functional Partnership -- Exercises

Skeleton functions with TODOs. Implement each function following the docstrings.
Test your implementations by running this file: python exercises.py

Reference files in this directory:
  - 01-product-expertise-and-competitive-intelligence.md  (product knowledge, feature-value mapping, competitive landscape)
  - 02-cross-functional-collaboration.md                  (feedback loops, escalation, knowledge management)
  - examples.py                                           (runnable reference implementations)

Difficulty ratings:
  [1] Foundational -- should be quick for senior engineers
  [2] Intermediate -- requires understanding of SE workflows and tradeoffs
  [3] Advanced -- system design and cross-functional thinking required
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

@dataclass
class FeatureValueMap:
    """A complete feature-to-value chain for one feature."""
    feature: str
    capability: str
    benefit: str
    business_value: str
    industry: str = ""
    category: str = ""


@dataclass
class CompetitiveMatrix:
    """A competitive comparison matrix."""
    our_product: str
    competitors: list[str]
    capabilities: list[str]
    ratings: dict[str, dict[str, int]]  # vendor -> {capability -> rating}
    positioning: dict[str, dict]  # competitor -> {advantages, gaps, talk_track}
    scores: dict[str, float]  # vendor -> weighted score


@dataclass
class FeedbackItem:
    """A single piece of raw customer feedback."""
    customer: str
    quote: str
    theme: str
    deal_stage: str = ""
    arr: float = 0.0
    urgency: str = "medium"  # low, medium, high, critical
    competitor_mention: str = ""


@dataclass
class FeedbackTheme:
    """A grouped theme from aggregated feedback."""
    theme: str
    frequency: int
    total_arr: float
    avg_urgency: float
    competitors_cited: list[str]
    customer_quotes: list[dict]
    priority_score: float


@dataclass
class FeedbackReport:
    """A complete product feedback report."""
    themes: list[FeedbackTheme]
    total_items: int
    unique_customers: int
    total_arr_at_risk: float
    generated_date: str = ""


@dataclass
class EscalationDecision:
    """An escalation decision with recommended path."""
    level: str  # "peer", "manager", "director", "vp"
    who_to_contact: str
    urgency: str  # "immediate", "within_hours", "within_day", "next_sprint"
    reasoning: str
    template: str  # pre-filled escalation message


@dataclass
class KBArticle:
    """A structured knowledge base article."""
    title: str
    problem: str
    solution: str
    tags: list[str] = field(default_factory=list)
    product_area: str = ""
    industry: str = ""
    related_articles: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    last_verified: str = ""
    author: str = ""


# ============================================================================
# EXERCISE 1: Feature-Value Mapper
#
# READ FIRST:
#   01-product-expertise-and-competitive-intelligence.md
#     -> "## Feature-to-Value Mapping"
#     -> "### The Feature-to-Value Chain" (Feature -> Capability -> Benefit -> Value)
#     -> "### Feature-Value Mapping Table" (10+ examples of complete chains)
#     -> "### Using Feature-Value Language"
#
# ALSO SEE:
#   examples.py
#     -> "3. FEATURE-VALUE MAPPING SYSTEM"
#     -> FeatureValueMapper.add_feature() (auto-inference of value chain)
#     -> FeatureValueMapper.generate_demo_script_snippet()
#
# Build feature-to-value chains for a list of product features.
# Each feature must map through the full chain:
#   Feature -> Capability -> Benefit -> Business Value
#
# Key concepts:
# - Features are technical facts; value is what matters to the customer
# - Capabilities describe what the feature enables the customer to do
# - Benefits explain why the capability matters operationally
# - Business value quantifies the impact (revenue, cost, risk, speed)
# - Industry context changes the value language
# ============================================================================

def build_feature_value_map(
    features: list[dict],
    industry: str = "general",
) -> list[FeatureValueMap]:
    """Build feature-to-value chains for a list of product features.

    Args:
        features: List of dicts, each with:
            - "name": str -- feature name (e.g., "Real-time Event Streaming")
            - "description": str -- what the feature does technically
            - "category": str -- feature category (e.g., "Data Pipeline")
        industry: Target industry for value language
                  (e.g., "healthcare", "fintech", "retail", "general")

    Returns:
        List of FeatureValueMap dataclass instances, one per feature.
        Each must have all four chain links populated:
        feature, capability, benefit, business_value.

    TODO: Implement this function.

    Step-by-step:
    1. For each feature dict in the input list:
       a. Extract name, description, and category
       b. Generate a CAPABILITY: what does this feature enable the customer
          to DO? Transform the technical description into a user action.
          - Look for keywords in the description to guide inference:
            "automat" -> "Automate X without manual intervention"
            "monitor/alert" -> "Proactively detect and respond to issues"
            "integrat/connect" -> "Connect existing systems through X"
            "secur/access" -> "Control and audit access using X"
            "analyt/report/dashboard" -> "Visualize and analyze data through X"
            Default: "Enable X for operational workflows"
       c. Generate a BENEFIT: why does the capability matter operationally?
          - "automat" in capability -> "Eliminate manual effort and reduce human error"
          - "detect/monitor" -> "Catch problems before they impact customers"
          - "connect/integrat" -> "Unify workflows across previously siloed systems"
          - "control/audit" -> "Meet compliance requirements with less overhead"
          - "visualize/analyz" -> "Make data-driven decisions faster"
          Default: "Improve operational efficiency and reduce friction"
       d. Generate BUSINESS VALUE using industry-specific language:
          Use these templates based on the benefit:
          - healthcare: HIPAA compliance, patient outcomes, clinician adoption
          - fintech: SOX/PCI-DSS compliance, transaction latency, fraud exposure
          - retail: PCI compliance, inventory speed, customer acquisition cost
          - general: regulatory requirements, time-to-value, operational cost
       e. Create a FeatureValueMap with all fields populated
    2. Return the list of FeatureValueMap instances

    Hint: See the INDUSTRY_VALUE_TEMPLATES dict in examples.py for
    industry-specific value language.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 2: Competitive Matrix Builder
#
# READ FIRST:
#   01-product-expertise-and-competitive-intelligence.md
#     -> "## Competitive Landscape Maintenance"
#     -> "### Intelligence Sources" (where competitive data comes from)
#     -> "## Product Limitations and Honesty"
#     -> "### The 'Not Yet' vs. 'Not Ever' Framework"
#
# ALSO SEE:
#   examples.py
#     -> "1. COMPETITIVE MATRIX ENGINE"
#     -> CompetitiveMatrixEngine.build_matrix() (scoring, positioning, talk tracks)
#     -> CompetitiveMatrixEngine._generate_talk_track()
#
# Build a competitive comparison matrix with honest positioning.
# The matrix must identify advantages, gaps, and parity -- not just
# show where you win.
#
# Key concepts:
# - Honest competitive analysis builds credibility
# - Position = ADVANTAGE, PARITY, or GAP for each capability
# - Weighted scoring reflects what matters for a specific deal
# - Talk tracks guide the SE conversation
# ============================================================================

def build_competitive_matrix(
    our_product: str,
    our_capabilities: dict[str, int],
    competitors: dict[str, dict[str, int]],
    capability_weights: dict[str, float] | None = None,
    competitor_notes: dict[str, dict] | None = None,
) -> CompetitiveMatrix:
    """Build a competitive comparison matrix with positioning guidance.

    Args:
        our_product: Name of our product
        our_capabilities: Dict mapping capability name to rating (1-5)
            1 = not available, 2 = basic, 3 = good, 4 = strong, 5 = best-in-class
        competitors: Dict mapping competitor name to their capability ratings
            e.g., {"CompA": {"API": 4, "SSO": 3}, "CompB": {"API": 5, "SSO": 2}}
        capability_weights: Optional dict mapping capability to importance weight
            (0.0 to 1.0). Default weight is 1.0 if not specified.
        competitor_notes: Optional dict with additional competitor context
            e.g., {"CompA": {"strengths": ["Great SQL"], "weaknesses": ["Slow API"]}}

    Returns:
        CompetitiveMatrix dataclass with:
        - our_product: our product name
        - competitors: list of competitor names
        - capabilities: list of all capability names (union of all vendors)
        - ratings: dict[vendor_name, dict[capability, rating]] for all vendors
        - positioning: dict[competitor, dict] with keys:
            - "advantages": capabilities where we beat them
            - "gaps": capabilities where they beat us
            - "parity": capabilities where we are equal
            - "talk_track": suggested positioning language
        - scores: dict[vendor_name, weighted_score] for all vendors

    TODO: Implement this function.

    Step-by-step:
    1. Collect all capabilities (union of ours and all competitors')
    2. Build the ratings dict with all vendors (our product + competitors)
       Use 0 for any capability a vendor does not have
    3. For each competitor, determine positioning per capability:
       - our_rating > their_rating -> ADVANTAGE
       - our_rating < their_rating -> GAP
       - our_rating == their_rating -> PARITY
    4. Calculate weighted scores for each vendor:
       - Normalize weights so they sum to 1.0
       - weighted_score = sum(rating * normalized_weight for each capability)
    5. Generate a talk_track for each competitor:
       - Lead with advantages (top 3)
       - Acknowledge their strengths (top 3 gaps)
       - Reference their weaknesses from competitor_notes if available
    6. Return the populated CompetitiveMatrix
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 3: Product Feedback Synthesizer
#
# READ FIRST:
#   02-cross-functional-collaboration.md
#     -> "## SE-to-PM Feedback Loops"
#     -> "### Feature Requests vs. Pain Reports"
#     -> "### Writing Effective Product Feedback"
#     -> "### The Feedback Template"
#     -> "### Aggregating Feedback Across Deals"
#
# ALSO SEE:
#   examples.py
#     -> "2. PRODUCT FEEDBACK REPORT GENERATOR"
#     -> FeedbackReportGenerator.generate_report() (grouping, scoring, ranking)
#     -> FeedbackReportGenerator.format_report() (output formatting)
#
# Synthesize raw customer feedback into a structured report for the PM.
# Group by theme, rank by business impact, include customer quotes.
#
# Key concepts:
# - Individual feedback is noise; aggregated feedback is signal
# - Priority ranking uses frequency, urgency, ARR, and competitive pressure
# - Customer quotes in their own words are the most persuasive evidence
# - The output format should match what PMs actually read and act on
# ============================================================================

def synthesize_product_feedback(
    feedback_items: list[FeedbackItem],
) -> FeedbackReport:
    """Synthesize raw customer feedback into a prioritized report.

    Args:
        feedback_items: List of FeedbackItem dataclass instances, each with:
            - customer: customer name
            - quote: direct customer quote
            - theme: categorized theme (e.g., "Notification channels")
            - deal_stage: current deal stage
            - arr: annual recurring revenue at risk
            - urgency: "low", "medium", "high", or "critical"
            - competitor_mention: competitor name if cited, else ""

    Returns:
        FeedbackReport dataclass with:
        - themes: list of FeedbackTheme, sorted by priority_score descending
        - total_items: total number of feedback items
        - unique_customers: number of unique customers
        - total_arr_at_risk: sum of all ARR values
        - generated_date: today's date as ISO string

    TODO: Implement this function.

    Step-by-step:
    1. Group feedback items by theme (use a dict: theme -> list of items)
    2. For each theme group, calculate:
       a. frequency: number of items in the group
       b. total_arr: sum of arr values in the group
       c. avg_urgency: average urgency score using this mapping:
          {"low": 1, "medium": 2, "high": 3, "critical": 4}
       d. competitors_cited: unique list of competitor mentions (non-empty)
       e. customer_quotes: list of dicts with "customer" and "quote" keys
       f. priority_score: combined score using this formula:
          priority = (frequency * 2.0)
                   + (avg_urgency * 1.5)
                   + (total_arr / 100_000 * 1.0)
                   + (len(competitors_cited) * 1.0)
    3. Create FeedbackTheme for each group
    4. Sort themes by priority_score descending
    5. Calculate summary stats (total items, unique customers, total ARR)
    6. Return FeedbackReport with all fields populated
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 4: Escalation Decision Tree
#
# READ FIRST:
#   02-cross-functional-collaboration.md
#     -> "## Escalation Paths"
#     -> "### The Escalation Decision Framework" (solve-it-yourself vs. escalate)
#     -> "### Escalation Levels" (peer, manager, director, VP)
#     -> "### Escalating Without Burning Bridges"
#     -> "### Escalation Templates"
#
# ALSO SEE:
#   examples.py
#     -> (no direct parallel -- this exercise is unique to the SE workflow)
#
# Determine the appropriate escalation level and path for an issue.
# Consider severity, customer tier, deal stage, and time sensitivity.
#
# Key concepts:
# - Escalating too often loses credibility; too rarely loses deals
# - Customer tier and deal value affect escalation priority
# - Always show what you have tried before escalating
# - Escalation templates make the ask clear and actionable
# ============================================================================

def determine_escalation(
    issue_description: str,
    severity: str,
    customer_tier: str,
    deal_stage: str,
    deal_arr: float = 0.0,
    workaround_available: bool = False,
    attempts_made: list[str] | None = None,
) -> EscalationDecision:
    """Determine the appropriate escalation level and path.

    Args:
        issue_description: What is the problem (one sentence)
        severity: "critical", "high", "medium", or "low"
        customer_tier: "enterprise", "mid-market", or "smb"
        deal_stage: "discovery", "evaluation", "poc", "negotiation",
                    "closed_won", or "renewal"
        deal_arr: Annual recurring revenue of the deal
        workaround_available: Whether a workaround exists
        attempts_made: List of things already tried (for showing work)

    Returns:
        EscalationDecision dataclass with:
        - level: "peer", "manager", "director", or "vp"
        - who_to_contact: role/title of the person to contact
        - urgency: "immediate", "within_hours", "within_day", "next_sprint"
        - reasoning: why this escalation level was chosen
        - template: pre-filled escalation message using the templates from
                    02-cross-functional-collaboration.md

    TODO: Implement this function.

    Step-by-step:
    1. Score the situation on multiple dimensions:
       a. Severity score: critical=4, high=3, medium=2, low=1
       b. Tier score: enterprise=3, mid-market=2, smb=1
       c. Stage score: negotiation/renewal=3, poc/evaluation=2, discovery=1,
                       closed_won=2 (existing customer)
       d. ARR score: >500K=3, >100K=2, else=1
       e. Workaround factor: 0 if workaround available, 1 if not
    2. Calculate composite score:
       composite = severity_score * 2 + tier_score + stage_score + arr_score + workaround_factor * 2
    3. Map composite to escalation level:
       - composite >= 14: "vp" level
       - composite >= 10: "director" level
       - composite >= 6:  "manager" level
       - composite < 6:   "peer" level
    4. Determine urgency:
       - severity == "critical": "immediate"
       - severity == "high" and no workaround: "within_hours"
       - severity == "high" and workaround available: "within_day"
       - else: "next_sprint"
    5. Set who_to_contact based on level:
       - "peer": "Fellow SE or senior engineer"
       - "manager": "SE Manager or Engineering Manager"
       - "director": "Director of SE or Director of Engineering"
       - "vp": "VP of Sales or VP of Engineering"
    6. Generate reasoning explaining why this level was chosen
    7. Generate template message with all context filled in
    8. Return the EscalationDecision
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 5: Knowledge Base Article Writer
#
# READ FIRST:
#   02-cross-functional-collaboration.md
#     -> "## Knowledge Management"
#     -> "### Building an Internal Knowledge Base" (KB structure table)
#     -> "### Making Knowledge Findable" (naming, tagging, search keywords)
#     -> "### The Tribal Knowledge Problem"
#
# ALSO SEE:
#   examples.py
#     -> "4. KNOWLEDGE BASE TEMPLATE"
#     -> KnowledgeBaseManager.create_article_from_solution() (auto-tagging)
#     -> KnowledgeBaseManager.format_article() (display format)
#
# Generate a structured KB article from a technical problem and solution.
# Auto-generate tags, keywords, and suggest related articles.
#
# Key concepts:
# - KB articles must be findable by multiple search paths
# - Tags enable categorical browsing; keywords enable search
# - Related articles reduce time-to-answer for similar problems
# - Last-verified dates prevent stale content from misleading people
# ============================================================================

def write_kb_article(
    problem: str,
    solution: str,
    context: dict | None = None,
) -> KBArticle:
    """Generate a structured KB article from a problem/solution pair.

    Args:
        problem: Description of the technical problem
        solution: Description of the solution
        context: Optional dict with additional context:
            - "product_area": str (e.g., "Authentication", "Integration")
            - "industry": str (e.g., "Healthcare", "Fintech")
            - "author": str (author name)
            - "related_problems": list[str] (titles of related articles)

    Returns:
        KBArticle dataclass with:
        - title: generated from the problem (max 80 chars)
        - problem: the problem description
        - solution: the solution description
        - tags: auto-generated tags based on content analysis
        - product_area: from context or inferred
        - industry: from context or ""
        - related_articles: from context or []
        - keywords: auto-extracted search keywords (up to 15)
        - last_verified: today's date as ISO string
        - author: from context or ""

    TODO: Implement this function.

    Step-by-step:
    1. Generate a title from the problem:
       - Use the problem text, stripped and trimmed to 80 chars
       - If truncated, add "..." at the end
    2. Auto-generate tags by scanning the problem and solution text
       for keyword patterns:
       - "api", "webhook", "connect", "sync", "import", "export" -> "integration"
       - "sso", "saml", "oauth", "login", "auth", "ldap" -> "authentication"
       - "slow", "latency", "timeout", "cache", "scale" -> "performance"
       - "config", "setting", "parameter", "option", "setup" -> "configuration"
       - "migrate", "upgrade", "move", "transfer", "convert" -> "migration"
       - "permission", "access", "role", "encrypt", "audit" -> "security"
       - "error", "fail", "broken", "debug", "fix" -> "troubleshooting"
       Also add product_area and industry as tags if provided
    3. Auto-extract keywords from title and problem:
       - Split into words, lowercase
       - Remove common stop words (the, a, an, is, are, in, on, etc.)
       - Take up to 15 unique keywords, sorted alphabetically
    4. Set last_verified to today's date
    5. Pull remaining fields from context dict if provided
    6. Return the populated KBArticle
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# Test Harness
# ============================================================================

def test_exercise_1():
    """Test Exercise 1: Feature-Value Mapper."""
    print("\n--- Exercise 1: Feature-Value Mapper ---")
    try:
        features = [
            {
                "name": "Real-time Event Streaming",
                "description": "Process and route events with sub-second latency",
                "category": "Data Pipeline",
            },
            {
                "name": "SSO/SAML Integration",
                "description": "Secure single sign-on via corporate identity provider",
                "category": "Security",
            },
            {
                "name": "Custom Dashboards",
                "description": "Build role-specific analytics dashboards with drill-down",
                "category": "Analytics",
            },
        ]

        result = build_feature_value_map(features, industry="fintech")

        assert isinstance(result, list), "Should return a list"
        assert len(result) == 3, f"Expected 3 maps, got {len(result)}"

        for fvm in result:
            assert isinstance(fvm, FeatureValueMap), "Each item should be a FeatureValueMap"
            assert fvm.feature, "Feature name should be populated"
            assert fvm.capability, "Capability should be populated"
            assert fvm.benefit, "Benefit should be populated"
            assert fvm.business_value, "Business value should be populated"
            assert fvm.industry == "fintech", "Industry should match input"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")


def test_exercise_2():
    """Test Exercise 2: Competitive Matrix Builder."""
    print("\n--- Exercise 2: Competitive Matrix Builder ---")
    try:
        our_caps = {"API": 5, "SSO": 4, "Visualization": 3, "Mobile": 2}
        competitors = {
            "CompA": {"API": 3, "SSO": 5, "Visualization": 4, "Mobile": 4},
            "CompB": {"API": 4, "SSO": 2, "Visualization": 5, "Mobile": 3},
        }
        weights = {"API": 1.0, "SSO": 0.8, "Visualization": 0.6, "Mobile": 0.3}
        notes = {
            "CompA": {"strengths": ["Strong SSO"], "weaknesses": ["Weak API docs"]},
        }

        result = build_competitive_matrix(
            "OurProduct", our_caps, competitors, weights, notes
        )

        assert isinstance(result, CompetitiveMatrix), "Should return CompetitiveMatrix"
        assert result.our_product == "OurProduct"
        assert len(result.competitors) == 2
        assert len(result.capabilities) == 4
        assert "OurProduct" in result.scores
        assert "CompA" in result.scores
        assert "CompB" in result.scores

        # Check positioning
        assert "CompA" in result.positioning
        pos_a = result.positioning["CompA"]
        assert "advantages" in pos_a, "Positioning should include advantages"
        assert "gaps" in pos_a, "Positioning should include gaps"
        assert "API" in pos_a["advantages"], "API should be our advantage vs CompA"
        assert "SSO" in pos_a["gaps"], "SSO should be a gap vs CompA"
        assert "talk_track" in pos_a, "Should include talk track"

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")


def test_exercise_3():
    """Test Exercise 3: Product Feedback Synthesizer."""
    print("\n--- Exercise 3: Product Feedback Synthesizer ---")
    try:
        items = [
            FeedbackItem(
                customer="Acme Corp", quote="We miss alerts in Slack.",
                theme="Notifications", deal_stage="Evaluation",
                arr=250000, urgency="high", competitor_mention="CompX",
            ),
            FeedbackItem(
                customer="Globex Inc", quote="Our Slack bridge keeps breaking.",
                theme="Notifications", deal_stage="POC",
                arr=180000, urgency="high",
            ),
            FeedbackItem(
                customer="Initech", quote="Need better audit logging for SOC 2.",
                theme="Compliance", deal_stage="Negotiation",
                arr=400000, urgency="critical",
            ),
            FeedbackItem(
                customer="Wayne Ent", quote="Onboarding took 3 weeks not 3 days.",
                theme="Onboarding", deal_stage="Post-sale",
                arr=600000, urgency="medium", competitor_mention="CompY",
            ),
        ]

        result = synthesize_product_feedback(items)

        assert isinstance(result, FeedbackReport), "Should return FeedbackReport"
        assert result.total_items == 4, f"Expected 4 items, got {result.total_items}"
        assert result.unique_customers == 4
        assert len(result.themes) == 3, f"Expected 3 themes, got {len(result.themes)}"

        # Themes should be sorted by priority_score descending
        for i in range(len(result.themes) - 1):
            assert result.themes[i].priority_score >= result.themes[i + 1].priority_score, \
                "Themes should be sorted by priority_score descending"

        # Notifications theme should have highest frequency
        notif_theme = next(t for t in result.themes if t.theme == "Notifications")
        assert notif_theme.frequency == 2
        assert notif_theme.total_arr == 430000
        assert "CompX" in notif_theme.competitors_cited

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")


def test_exercise_4():
    """Test Exercise 4: Escalation Decision Tree."""
    print("\n--- Exercise 4: Escalation Decision Tree ---")
    try:
        # Critical enterprise issue = VP level
        result_critical = determine_escalation(
            issue_description="Production environment down for largest customer",
            severity="critical",
            customer_tier="enterprise",
            deal_stage="renewal",
            deal_arr=800000,
            workaround_available=False,
            attempts_made=["Restarted service", "Checked logs", "Contacted support"],
        )

        assert isinstance(result_critical, EscalationDecision)
        assert result_critical.level in ("vp", "director"), \
            f"Critical enterprise issue should escalate to vp or director, got {result_critical.level}"
        assert result_critical.urgency == "immediate"
        assert result_critical.who_to_contact, "Should specify who to contact"
        assert result_critical.template, "Should include escalation template"

        # Low SMB issue = peer level
        result_low = determine_escalation(
            issue_description="Minor UI alignment issue in settings page",
            severity="low",
            customer_tier="smb",
            deal_stage="discovery",
            deal_arr=15000,
            workaround_available=True,
        )

        assert isinstance(result_low, EscalationDecision)
        assert result_low.level == "peer", \
            f"Low SMB issue should be peer level, got {result_low.level}"
        assert result_low.urgency in ("next_sprint", "within_day")

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")


def test_exercise_5():
    """Test Exercise 5: Knowledge Base Article Writer."""
    print("\n--- Exercise 5: Knowledge Base Article Writer ---")
    try:
        result = write_kb_article(
            problem="SSO login fails with SAML assertion error when IdP uses SHA-256 signing",
            solution=(
                "Update the SAML configuration to accept SHA-256 signatures. "
                "Go to Admin > Security > SAML Settings and set Signature "
                "Algorithm to RSA-SHA256."
            ),
            context={
                "product_area": "Authentication",
                "industry": "Healthcare",
                "author": "Jane Smith",
                "related_problems": ["LDAP sync timeout", "OAuth token expiration"],
            },
        )

        assert isinstance(result, KBArticle), "Should return KBArticle"
        assert result.title, "Title should be populated"
        assert len(result.title) <= 83, "Title should be max ~80 chars (plus ...)"
        assert result.problem, "Problem should be populated"
        assert result.solution, "Solution should be populated"
        assert len(result.tags) > 0, "Should have at least one tag"
        assert "authentication" in result.tags, \
            f"Should detect 'authentication' tag, got {result.tags}"
        assert result.product_area == "Authentication"
        assert result.industry == "Healthcare"
        assert result.author == "Jane Smith"
        assert len(result.keywords) > 0, "Should extract keywords"
        assert len(result.keywords) <= 15, "Should have at most 15 keywords"
        assert result.last_verified, "Should set last_verified date"
        assert len(result.related_articles) == 2

        print("  PASSED")
    except NotImplementedError:
        print("  SKIPPED (not implemented)")
    except AssertionError as e:
        print(f"  FAILED: {e}")


def run_tests():
    """Run all exercise tests."""
    print("=" * 60)
    print("Running Exercise Tests")
    print("=" * 60)

    test_exercise_1()
    test_exercise_2()
    test_exercise_3()
    test_exercise_4()
    test_exercise_5()

    print("\n" + "=" * 60)
    print("Tests complete. Implement the exercises and re-run!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
