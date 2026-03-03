"""
Module 05: Product Knowledge and Cross-Functional Partnership -- Complete, Runnable Patterns

Demonstrates product expertise, competitive intelligence, feedback management,
and knowledge base tools for Solutions Engineers.

Each section is self-contained. Read top-to-bottom or jump to specific patterns.

Run this file directly: python examples.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

@dataclass
class Feature:
    """A product feature with value chain metadata."""
    name: str
    description: str
    capability: str = ""
    benefit: str = ""
    business_value: str = ""
    category: str = ""


@dataclass
class Competitor:
    """A competitor with capability ratings."""
    name: str
    capabilities: dict[str, int] = field(default_factory=dict)  # capability -> 1-5 rating
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class FeedbackItem:
    """A single piece of customer feedback."""
    customer: str
    quote: str
    theme: str
    deal_stage: str = ""
    arr: float = 0.0
    urgency: str = "medium"  # low, medium, high, critical
    date: str = ""
    competitor_mention: str = ""


@dataclass
class KBArticle:
    """A knowledge base article."""
    title: str
    problem: str
    solution: str
    tags: list[str] = field(default_factory=list)
    product_area: str = ""
    industry: str = ""
    related_articles: list[str] = field(default_factory=list)
    last_verified: str = ""
    author: str = ""
    keywords: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 1. COMPETITIVE MATRIX ENGINE
# ---------------------------------------------------------------------------

class CompetitiveMatrixEngine:
    """Complete competitive comparison tool with scoring and positioning.

    Builds honest comparison matrices that SEs can use in customer
    conversations. Emphasizes balanced analysis -- not marketing spin.
    """

    def __init__(self, our_product_name: str):
        self.our_product = our_product_name
        self.our_capabilities: dict[str, int] = {}
        self.competitors: list[Competitor] = []
        self.capability_weights: dict[str, float] = {}

    def set_our_capabilities(self, capabilities: dict[str, int]) -> None:
        """Set our product's capability ratings (1-5 scale).

        Args:
            capabilities: Dict mapping capability name to rating (1-5).
                          1 = not available, 2 = basic, 3 = good,
                          4 = strong, 5 = best-in-class.
        """
        self.our_capabilities = capabilities

    def add_competitor(self, competitor: Competitor) -> None:
        """Add a competitor to the matrix."""
        self.competitors.append(competitor)

    def set_capability_weights(self, weights: dict[str, float]) -> None:
        """Set importance weights for capabilities (0.0 to 1.0).
        Used for weighted scoring in competitive comparisons."""
        self.capability_weights = weights

    def build_matrix(self) -> dict:
        """Build the full competitive comparison matrix.

        Returns a dict with:
        - matrix: list of rows, each row is a capability comparison
        - scores: weighted scores for each vendor
        - positioning: per-competitor positioning guidance
        """
        all_capabilities = set(self.our_capabilities.keys())
        for comp in self.competitors:
            all_capabilities.update(comp.capabilities.keys())

        sorted_caps = sorted(all_capabilities)

        # Build comparison rows
        matrix_rows = []
        for cap in sorted_caps:
            row = {
                "capability": cap,
                self.our_product: self.our_capabilities.get(cap, 0),
            }
            for comp in self.competitors:
                row[comp.name] = comp.capabilities.get(cap, 0)

            # Determine our position for this capability
            our_score = row[self.our_product]
            max_competitor = max(
                (comp.capabilities.get(cap, 0) for comp in self.competitors),
                default=0,
            )
            if our_score > max_competitor:
                row["position"] = "ADVANTAGE"
            elif our_score == max_competitor:
                row["position"] = "PARITY"
            else:
                row["position"] = "GAP"

            matrix_rows.append(row)

        # Calculate weighted scores
        scores = {self.our_product: 0.0}
        for comp in self.competitors:
            scores[comp.name] = 0.0

        total_weight = sum(self.capability_weights.get(cap, 1.0) for cap in sorted_caps)

        for cap in sorted_caps:
            weight = self.capability_weights.get(cap, 1.0) / total_weight
            scores[self.our_product] += self.our_capabilities.get(cap, 0) * weight
            for comp in self.competitors:
                scores[comp.name] += comp.capabilities.get(cap, 0) * weight

        # Generate positioning guidance per competitor
        positioning = {}
        for comp in self.competitors:
            advantages = []
            gaps = []
            parity = []

            for cap in sorted_caps:
                our = self.our_capabilities.get(cap, 0)
                theirs = comp.capabilities.get(cap, 0)
                if our > theirs:
                    advantages.append(cap)
                elif our < theirs:
                    gaps.append(cap)
                else:
                    parity.append(cap)

            positioning[comp.name] = {
                "our_advantages": advantages,
                "their_advantages": gaps,
                "parity": parity,
                "strengths": comp.strengths,
                "weaknesses": comp.weaknesses,
                "talk_track": self._generate_talk_track(comp, advantages, gaps),
            }

        return {
            "matrix": matrix_rows,
            "scores": {k: round(v, 2) for k, v in scores.items()},
            "positioning": positioning,
        }

    def _generate_talk_track(
        self,
        comp: Competitor,
        our_advantages: list[str],
        their_advantages: list[str],
    ) -> str:
        """Generate a positioning talk track for a specific competitor."""
        lines = []
        if our_advantages:
            adv_str = ", ".join(our_advantages[:3])
            lines.append(
                f"Lead with our strengths in {adv_str}. "
                f"These are areas where we demonstrably outperform {comp.name}."
            )
        if their_advantages:
            gap_str = ", ".join(their_advantages[:3])
            lines.append(
                f"Acknowledge {comp.name}'s strength in {gap_str}. "
                f"Pivot to whether these capabilities are critical for this "
                f"customer's specific use case."
            )
        if comp.weaknesses:
            weak = comp.weaknesses[0]
            lines.append(
                f"If relevant, raise the question of {weak} -- "
                f"a known concern for {comp.name} customers."
            )
        return " ".join(lines)

    def format_matrix_table(self) -> str:
        """Format the matrix as a printable table."""
        result = self.build_matrix()
        matrix = result["matrix"]

        if not matrix:
            return "No capabilities to compare."

        # Column headers
        vendors = [self.our_product] + [c.name for c in self.competitors]
        header = f"{'Capability':<30} " + " ".join(f"{v:<15}" for v in vendors) + f" {'Position':<12}"
        separator = "-" * len(header)

        lines = [separator, header, separator]
        for row in matrix:
            values = " ".join(
                f"{self._rating_display(row.get(v, 0)):<15}" for v in vendors
            )
            lines.append(f"{row['capability']:<30} {values} {row['position']:<12}")

        lines.append(separator)

        # Weighted scores
        lines.append("\nWeighted Scores:")
        for vendor, score in result["scores"].items():
            lines.append(f"  {vendor}: {score:.2f} / 5.00")

        return "\n".join(lines)

    @staticmethod
    def _rating_display(rating: int) -> str:
        """Convert numeric rating to display string."""
        labels = {0: "N/A", 1: "None", 2: "Basic", 3: "Good", 4: "Strong", 5: "Best"}
        return f"{rating}/5 ({labels.get(rating, '?')})"


# ---------------------------------------------------------------------------
# 2. PRODUCT FEEDBACK REPORT GENERATOR
# ---------------------------------------------------------------------------

class FeedbackReportGenerator:
    """Feedback aggregator with thematic analysis and priority ranking.

    Transforms raw customer feedback into structured reports that
    product managers can act on. Groups by theme, ranks by business
    impact, and generates the format PMs actually read.
    """

    def __init__(self):
        self.feedback_items: list[FeedbackItem] = []

    def add_feedback(self, item: FeedbackItem) -> None:
        """Add a single feedback item."""
        self.feedback_items.append(item)

    def add_batch(self, items: list[FeedbackItem]) -> None:
        """Add multiple feedback items at once."""
        self.feedback_items.extend(items)

    def generate_report(self) -> dict:
        """Generate a complete product feedback report.

        Returns:
            Dict with themed groups, priority ranking, summary stats,
            and formatted report sections.
        """
        if not self.feedback_items:
            return {"themes": [], "summary": "No feedback collected."}

        # Group by theme
        theme_groups: dict[str, list[FeedbackItem]] = {}
        for item in self.feedback_items:
            theme_groups.setdefault(item.theme, []).append(item)

        # Score and rank themes
        scored_themes = []
        for theme, items in theme_groups.items():
            # Urgency scores
            urgency_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            avg_urgency = sum(urgency_map.get(i.urgency, 2) for i in items) / len(items)

            # Total ARR at risk
            total_arr = sum(i.arr for i in items)

            # Frequency
            frequency = len(items)

            # Competitive mentions
            competitive_mentions = [i for i in items if i.competitor_mention]

            # Combined priority score (normalized)
            priority_score = (
                frequency * 2.0            # frequency matters most
                + avg_urgency * 1.5        # urgency is important
                + (total_arr / 100000) * 1.0  # ARR impact
                + len(competitive_mentions) * 1.0  # competitive pressure
            )

            scored_themes.append({
                "theme": theme,
                "frequency": frequency,
                "avg_urgency": round(avg_urgency, 1),
                "total_arr": total_arr,
                "competitive_mentions": len(competitive_mentions),
                "priority_score": round(priority_score, 1),
                "items": items,
                "customer_quotes": [
                    {"customer": i.customer, "quote": i.quote}
                    for i in items
                ],
                "competitors_cited": list(set(
                    i.competitor_mention for i in competitive_mentions
                )),
            })

        # Sort by priority score
        scored_themes.sort(key=lambda x: x["priority_score"], reverse=True)

        # Summary stats
        summary = {
            "total_feedback_items": len(self.feedback_items),
            "unique_themes": len(theme_groups),
            "unique_customers": len(set(i.customer for i in self.feedback_items)),
            "total_arr_at_risk": sum(i.arr for i in self.feedback_items),
            "items_with_competitive_mentions": sum(
                1 for i in self.feedback_items if i.competitor_mention
            ),
        }

        return {
            "themes": scored_themes,
            "summary": summary,
        }

    def format_report(self) -> str:
        """Format the feedback report as a readable string."""
        report = self.generate_report()

        if isinstance(report["summary"], str):
            return report["summary"]

        summary = report["summary"]
        themes = report["themes"]

        lines = [
            "=" * 60,
            "PRODUCT FEEDBACK REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d')}",
            "=" * 60,
            "",
            "SUMMARY",
            f"  Total feedback items: {summary['total_feedback_items']}",
            f"  Unique themes: {summary['unique_themes']}",
            f"  Unique customers: {summary['unique_customers']}",
            f"  Total ARR at risk: ${summary['total_arr_at_risk']:,.0f}",
            f"  Items citing competitors: {summary['items_with_competitive_mentions']}",
            "",
            "-" * 60,
            "THEMES BY PRIORITY",
            "-" * 60,
        ]

        for i, theme in enumerate(themes, 1):
            lines.append(f"\n#{i} -- {theme['theme'].upper()}")
            lines.append(f"   Priority Score: {theme['priority_score']}")
            lines.append(f"   Frequency: {theme['frequency']} mentions")
            lines.append(f"   Avg Urgency: {theme['avg_urgency']}/4.0")
            lines.append(f"   ARR at Risk: ${theme['total_arr']:,.0f}")

            if theme["competitors_cited"]:
                lines.append(f"   Competitors Cited: {', '.join(theme['competitors_cited'])}")

            lines.append("   Customer Quotes:")
            for quote in theme["customer_quotes"][:3]:  # Top 3 quotes
                lines.append(f'     - "{quote["quote"]}" -- {quote["customer"]}')

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. FEATURE-VALUE MAPPING SYSTEM
# ---------------------------------------------------------------------------

class FeatureValueMapper:
    """Feature-to-business-value chain builder with templates.

    Transforms raw feature descriptions into complete value chains:
    Feature -> Capability -> Benefit -> Business Value.

    Includes industry-specific value templates.
    """

    # Industry-specific value language templates
    INDUSTRY_VALUE_TEMPLATES: dict[str, dict[str, str]] = {
        "healthcare": {
            "compliance": "maintain HIPAA/HITECH compliance without manual auditing",
            "speed": "reduce time from diagnosis to treatment decision",
            "cost": "lower cost per patient encounter",
            "risk": "reduce medical error and malpractice exposure",
            "adoption": "increase clinician adoption and reduce EHR fatigue",
        },
        "fintech": {
            "compliance": "meet SOX/PCI-DSS requirements automatically",
            "speed": "reduce trade settlement and processing latency",
            "cost": "lower cost per transaction",
            "risk": "reduce fraud exposure and regulatory penalty risk",
            "adoption": "increase advisor/trader platform usage",
        },
        "retail": {
            "compliance": "maintain PCI compliance across all storefronts",
            "speed": "reduce time from inventory receipt to shelf",
            "cost": "lower customer acquisition cost",
            "risk": "reduce stockout and overstock risk",
            "adoption": "increase omnichannel platform usage by store staff",
        },
        "general": {
            "compliance": "meet regulatory and audit requirements",
            "speed": "accelerate time-to-value and reduce cycle times",
            "cost": "reduce operational cost and resource consumption",
            "risk": "minimize security, operational, and compliance risk",
            "adoption": "increase user adoption and reduce training burden",
        },
    }

    def __init__(self, industry: str = "general"):
        self.industry = industry
        self.templates = self.INDUSTRY_VALUE_TEMPLATES.get(
            industry, self.INDUSTRY_VALUE_TEMPLATES["general"]
        )
        self.features: list[Feature] = []

    def add_feature(self, feature: Feature) -> Feature:
        """Add a feature and auto-generate value chain if missing."""
        if not feature.capability:
            feature.capability = self._infer_capability(feature)
        if not feature.benefit:
            feature.benefit = self._infer_benefit(feature)
        if not feature.business_value:
            feature.business_value = self._infer_business_value(feature)
        self.features.append(feature)
        return feature

    def _infer_capability(self, feature: Feature) -> str:
        """Infer capability from feature description."""
        desc = feature.description.lower()
        if "automat" in desc:
            return f"Automate {feature.name.lower()} without manual intervention"
        if "monitor" in desc or "alert" in desc:
            return f"Proactively detect and respond to issues via {feature.name.lower()}"
        if "integrat" in desc or "connect" in desc:
            return f"Connect existing systems through {feature.name.lower()}"
        if "secur" in desc or "access" in desc:
            return f"Control and audit access using {feature.name.lower()}"
        if "analyt" in desc or "report" in desc or "dashboard" in desc:
            return f"Visualize and analyze data through {feature.name.lower()}"
        return f"Enable {feature.name.lower()} for operational workflows"

    def _infer_benefit(self, feature: Feature) -> str:
        """Infer benefit from capability."""
        cap = feature.capability.lower()
        if "automat" in cap:
            return "Eliminate manual effort and reduce human error"
        if "detect" in cap or "monitor" in cap:
            return "Catch problems before they impact customers"
        if "connect" in cap or "integrat" in cap:
            return "Unify workflows across previously siloed systems"
        if "control" in cap or "audit" in cap:
            return "Meet compliance requirements with less operational overhead"
        if "visualize" in cap or "analyz" in cap:
            return "Make data-driven decisions faster"
        return "Improve operational efficiency and reduce friction"

    def _infer_business_value(self, feature: Feature) -> str:
        """Infer business value from benefit, using industry templates."""
        benefit = feature.benefit.lower()
        if "manual" in benefit or "automat" in benefit:
            return self.templates.get("cost", "Reduce operational cost")
        if "before" in benefit or "catch" in benefit:
            return self.templates.get("risk", "Minimize risk exposure")
        if "compliance" in benefit or "audit" in benefit:
            return self.templates.get("compliance", "Meet regulatory requirements")
        if "faster" in benefit or "speed" in benefit:
            return self.templates.get("speed", "Accelerate time-to-value")
        return self.templates.get("adoption", "Increase platform adoption")

    def build_value_map(self) -> list[dict]:
        """Build the complete feature-to-value map.

        Returns list of dicts, each representing one feature's full
        value chain.
        """
        return [
            {
                "feature": f.name,
                "description": f.description,
                "capability": f.capability,
                "benefit": f.benefit,
                "business_value": f.business_value,
                "category": f.category,
                "industry": self.industry,
            }
            for f in self.features
        ]

    def format_value_map(self) -> str:
        """Format the value map as a readable table."""
        value_map = self.build_value_map()

        if not value_map:
            return "No features mapped."

        lines = [
            "=" * 80,
            f"FEATURE-VALUE MAP ({self.industry.upper()})",
            "=" * 80,
        ]

        for i, entry in enumerate(value_map, 1):
            lines.append(f"\n--- Feature {i}: {entry['feature']} ---")
            lines.append(f"  Description:    {entry['description']}")
            lines.append(f"  Capability:     {entry['capability']}")
            lines.append(f"  Benefit:        {entry['benefit']}")
            lines.append(f"  Business Value: {entry['business_value']}")
            if entry["category"]:
                lines.append(f"  Category:       {entry['category']}")

        return "\n".join(lines)

    def generate_demo_script_snippet(self, feature_name: str) -> str:
        """Generate a value-first demo talking point for a feature."""
        feature = next((f for f in self.features if f.name == feature_name), None)
        if not feature:
            return f"Feature '{feature_name}' not found."

        return (
            f'"{feature.benefit}. Let me show you how {feature.name.lower()} '
            f"makes that happen. "
            f'[DEMO: Show {feature.description}] '
            f"Customers in {self.industry} tell us this helps them "
            f'{feature.business_value.lower()}."'
        )


# ---------------------------------------------------------------------------
# 4. KNOWLEDGE BASE TEMPLATE
# ---------------------------------------------------------------------------

class KnowledgeBaseManager:
    """KB article generator with search tags and cross-references.

    Manages a collection of knowledge base articles with structured
    metadata, search optimization, and cross-referencing.
    """

    def __init__(self):
        self.articles: list[KBArticle] = []
        self._tag_index: dict[str, list[int]] = {}  # tag -> list of article indices

    def add_article(self, article: KBArticle) -> KBArticle:
        """Add an article and update the tag index."""
        if not article.last_verified:
            article.last_verified = datetime.now().strftime("%Y-%m-%d")

        idx = len(self.articles)
        self.articles.append(article)

        # Update tag index
        for tag in article.tags:
            self._tag_index.setdefault(tag.lower(), []).append(idx)

        # Auto-generate keywords from title and problem if not provided
        if not article.keywords:
            words = set(
                (article.title + " " + article.problem).lower().split()
            )
            stop_words = {
                "the", "a", "an", "is", "are", "was", "were", "in", "on",
                "at", "to", "for", "of", "and", "or", "it", "this", "that",
                "with", "how", "do", "does", "not", "when", "what", "why",
            }
            article.keywords = sorted(words - stop_words)[:15]

        return article

    def search_by_tags(self, tags: list[str]) -> list[KBArticle]:
        """Find articles matching any of the given tags."""
        matching_indices: set[int] = set()
        for tag in tags:
            indices = self._tag_index.get(tag.lower(), [])
            matching_indices.update(indices)
        return [self.articles[i] for i in sorted(matching_indices)]

    def search_by_keyword(self, keyword: str) -> list[KBArticle]:
        """Find articles where keyword appears in title, problem, or keywords."""
        keyword_lower = keyword.lower()
        results = []
        for article in self.articles:
            if (
                keyword_lower in article.title.lower()
                or keyword_lower in article.problem.lower()
                or keyword_lower in article.solution.lower()
                or any(keyword_lower in kw for kw in article.keywords)
            ):
                results.append(article)
        return results

    def find_related(self, article: KBArticle) -> list[KBArticle]:
        """Find articles related to the given article by tag overlap."""
        related = []
        for other in self.articles:
            if other.title == article.title:
                continue
            shared_tags = set(article.tags) & set(other.tags)
            if shared_tags:
                related.append(other)
        return related

    def create_article_from_solution(
        self,
        problem: str,
        solution: str,
        product_area: str = "",
        industry: str = "",
        author: str = "",
    ) -> KBArticle:
        """Generate a structured KB article from a problem/solution pair.

        Auto-generates title, tags, and keywords.
        """
        # Generate title from problem
        title = problem.strip().rstrip(".")
        if len(title) > 80:
            title = title[:77] + "..."

        # Auto-generate tags from content
        tag_candidates = {
            "integration": ["api", "webhook", "connect", "sync", "import", "export"],
            "authentication": ["sso", "saml", "oauth", "login", "auth", "ldap"],
            "performance": ["slow", "latency", "timeout", "cache", "scale"],
            "configuration": ["config", "setting", "parameter", "option", "setup"],
            "migration": ["migrate", "upgrade", "move", "transfer", "convert"],
            "security": ["permission", "access", "role", "encrypt", "audit"],
            "troubleshooting": ["error", "fail", "broken", "debug", "fix"],
        }

        combined_text = (problem + " " + solution).lower()
        tags = []
        for tag, keywords in tag_candidates.items():
            if any(kw in combined_text for kw in keywords):
                tags.append(tag)

        if product_area:
            tags.append(product_area.lower())
        if industry:
            tags.append(industry.lower())

        article = KBArticle(
            title=title,
            problem=problem,
            solution=solution,
            tags=tags,
            product_area=product_area,
            industry=industry,
            author=author,
            last_verified=datetime.now().strftime("%Y-%m-%d"),
        )

        return self.add_article(article)

    def format_article(self, article: KBArticle) -> str:
        """Format a single KB article for display."""
        lines = [
            "=" * 60,
            f"KB ARTICLE: {article.title}",
            "=" * 60,
            f"Product Area: {article.product_area or 'General'}",
            f"Industry: {article.industry or 'All'}",
            f"Tags: {', '.join(article.tags)}",
            f"Last Verified: {article.last_verified}",
            f"Author: {article.author or 'Unknown'}",
            "",
            "PROBLEM:",
            f"  {article.problem}",
            "",
            "SOLUTION:",
            f"  {article.solution}",
        ]

        if article.related_articles:
            lines.append("")
            lines.append("RELATED ARTICLES:")
            for related in article.related_articles:
                lines.append(f"  - {related}")

        if article.keywords:
            lines.append("")
            lines.append(f"Keywords: {', '.join(article.keywords[:10])}")

        return "\n".join(lines)

    def stats(self) -> dict:
        """Return knowledge base statistics."""
        all_tags = set()
        for article in self.articles:
            all_tags.update(article.tags)

        product_areas = set(
            a.product_area for a in self.articles if a.product_area
        )

        return {
            "total_articles": len(self.articles),
            "unique_tags": len(all_tags),
            "tags": sorted(all_tags),
            "product_areas": sorted(product_areas),
            "articles_needing_verification": sum(
                1 for a in self.articles
                if a.last_verified and a.last_verified < "2025-01-01"
            ),
        }


# ---------------------------------------------------------------------------
# Demo: Putting It All Together
# ---------------------------------------------------------------------------

def main():
    """Demonstrate all patterns with sample data."""

    # --- Section 1: Competitive Matrix ---
    print("=" * 60)
    print("SECTION 1: COMPETITIVE MATRIX ENGINE")
    print("=" * 60)

    engine = CompetitiveMatrixEngine("OurPlatform")
    engine.set_our_capabilities({
        "Real-time streaming": 5,
        "Batch processing": 4,
        "SQL interface": 3,
        "Visualization": 4,
        "SSO/SAML": 5,
        "API extensibility": 5,
        "Mobile support": 2,
        "On-prem deployment": 3,
    })

    engine.add_competitor(Competitor(
        name="CompetitorA",
        capabilities={
            "Real-time streaming": 3,
            "Batch processing": 5,
            "SQL interface": 5,
            "Visualization": 4,
            "SSO/SAML": 4,
            "API extensibility": 3,
            "Mobile support": 4,
            "On-prem deployment": 5,
        },
        strengths=["Strong SQL support", "Mature batch processing"],
        weaknesses=["Slow real-time performance", "Limited API ecosystem"],
    ))

    engine.add_competitor(Competitor(
        name="CompetitorB",
        capabilities={
            "Real-time streaming": 4,
            "Batch processing": 3,
            "SQL interface": 4,
            "Visualization": 5,
            "SSO/SAML": 3,
            "API extensibility": 4,
            "Mobile support": 5,
            "On-prem deployment": 1,
        },
        strengths=["Beautiful visualization", "Best mobile experience"],
        weaknesses=["No on-prem option", "Weak enterprise security"],
    ))

    engine.set_capability_weights({
        "Real-time streaming": 1.0,
        "Batch processing": 0.8,
        "SQL interface": 0.6,
        "Visualization": 0.7,
        "SSO/SAML": 0.9,
        "API extensibility": 0.8,
        "Mobile support": 0.3,
        "On-prem deployment": 0.5,
    })

    print(engine.format_matrix_table())

    result = engine.build_matrix()
    print("\nPositioning vs CompetitorA:")
    pos = result["positioning"]["CompetitorA"]
    print(f"  Our advantages: {', '.join(pos['our_advantages'])}")
    print(f"  Their advantages: {', '.join(pos['their_advantages'])}")
    print(f"  Talk track: {pos['talk_track']}")

    # --- Section 2: Feedback Report ---
    print("\n\n" + "=" * 60)
    print("SECTION 2: PRODUCT FEEDBACK REPORT GENERATOR")
    print("=" * 60)

    generator = FeedbackReportGenerator()
    generator.add_batch([
        FeedbackItem(
            customer="Acme Corp",
            quote="We miss critical alerts because our team lives in Slack, not email.",
            theme="Notification channels",
            deal_stage="Evaluation",
            arr=250000,
            urgency="high",
            competitor_mention="CompetitorX",
        ),
        FeedbackItem(
            customer="Globex Inc",
            quote="Our ops team built a webhook-to-Slack bridge but it breaks every release.",
            theme="Notification channels",
            deal_stage="POC",
            arr=180000,
            urgency="high",
        ),
        FeedbackItem(
            customer="Initech",
            quote="We need better audit logging for SOC 2 compliance.",
            theme="Compliance and audit",
            deal_stage="Negotiation",
            arr=400000,
            urgency="critical",
        ),
        FeedbackItem(
            customer="Wayne Enterprises",
            quote="The onboarding took our team 3 weeks. Our leadership expected 3 days.",
            theme="Onboarding experience",
            deal_stage="Post-sale",
            arr=600000,
            urgency="medium",
            competitor_mention="CompetitorY",
        ),
        FeedbackItem(
            customer="Stark Industries",
            quote="We need Slack notifications for real-time alerts.",
            theme="Notification channels",
            deal_stage="Discovery",
            arr=320000,
            urgency="high",
            competitor_mention="CompetitorX",
        ),
        FeedbackItem(
            customer="Umbrella Corp",
            quote="Audit trail does not capture API-initiated changes.",
            theme="Compliance and audit",
            deal_stage="Evaluation",
            arr=200000,
            urgency="high",
        ),
    ])

    print(generator.format_report())

    # --- Section 3: Feature-Value Mapping ---
    print("\n\n" + "=" * 60)
    print("SECTION 3: FEATURE-VALUE MAPPING SYSTEM")
    print("=" * 60)

    mapper = FeatureValueMapper(industry="fintech")

    mapper.add_feature(Feature(
        name="Real-time Event Streaming",
        description="Process and route events with sub-second latency",
        category="Data Pipeline",
    ))
    mapper.add_feature(Feature(
        name="Automated Compliance Reports",
        description="Auto-generate SOX and PCI-DSS compliance documentation",
        category="Compliance",
    ))
    mapper.add_feature(Feature(
        name="API Gateway",
        description="Secure, rate-limited API integration layer",
        category="Integration",
    ))
    mapper.add_feature(Feature(
        name="Custom Dashboards",
        description="Role-specific analytics dashboards with drill-down",
        category="Analytics",
    ))

    print(mapper.format_value_map())

    print("\nDemo Script Snippet (Real-time Event Streaming):")
    print(mapper.generate_demo_script_snippet("Real-time Event Streaming"))

    # --- Section 4: Knowledge Base ---
    print("\n\n" + "=" * 60)
    print("SECTION 4: KNOWLEDGE BASE TEMPLATE")
    print("=" * 60)

    kb = KnowledgeBaseManager()

    # Create articles from solutions
    art1 = kb.create_article_from_solution(
        problem="SSO login fails with SAML assertion error when IdP uses SHA-256 signing",
        solution=(
            "Update the SAML configuration to accept SHA-256 signatures. "
            "In Admin > Security > SAML Settings, set 'Signature Algorithm' to "
            "'RSA-SHA256'. If using Okta, ensure the Okta app is configured to "
            "sign with SHA-256 (Settings > General > SAML Settings > Show "
            "Advanced Settings > Signature Algorithm)."
        ),
        product_area="Authentication",
        author="Jane Smith",
    )

    art2 = kb.create_article_from_solution(
        problem="Webhook delivery fails intermittently with timeout errors for large payloads",
        solution=(
            "Large webhook payloads (>1MB) can exceed the default 30s timeout. "
            "Solutions: 1) Enable payload compression (Admin > Webhooks > "
            "Enable gzip). 2) Switch to webhook batching mode to reduce payload "
            "size. 3) Increase customer's receiving endpoint timeout to 60s. "
            "4) If payload is consistently large, switch to the pull-based "
            "Events API instead of push webhooks."
        ),
        product_area="Integration",
        author="John Doe",
    )

    art3 = kb.create_article_from_solution(
        problem="Dashboard load time exceeds 10 seconds for customers with more than 1M records",
        solution=(
            "The default query does a full table scan. Enable materialized views "
            "for large datasets: Admin > Performance > Enable Materialized Views. "
            "Set refresh interval based on data freshness requirements (hourly for "
            "most dashboards, 15min for real-time monitoring). For customers with "
            ">10M records, also enable query result caching."
        ),
        product_area="Performance",
        author="Jane Smith",
    )

    print(f"\nKB Stats: {kb.stats()}")

    print("\n--- Article 1 ---")
    print(kb.format_article(art1))

    print("\n--- Search by tag: 'authentication' ---")
    results = kb.search_by_tags(["authentication"])
    for article in results:
        print(f"  Found: {article.title}")

    print("\n--- Search by keyword: 'timeout' ---")
    results = kb.search_by_keyword("timeout")
    for article in results:
        print(f"  Found: {article.title}")

    print("\n--- Related articles for Article 1 ---")
    related = kb.find_related(art1)
    if related:
        for article in related:
            print(f"  Related: {article.title}")
    else:
        print("  No related articles found.")


if __name__ == "__main__":
    main()
