"""
Module 07: SE/FDE Interview Preparation — Golden Examples

Complete, runnable reference implementations for SE interview preparation
tools. Each section demonstrates production-quality patterns for the skills
tested in SE/FDE interview loops: discovery call execution, system design
documentation, demo scripting, behavioral story formatting, and POC
evaluation.

No external dependencies beyond the standard library.
"""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Shared types used across examples
# ---------------------------------------------------------------------------

@dataclass
class Prospect:
    """A simulated customer prospect for discovery exercises."""
    name: str
    role: str
    company: str
    industry: str
    company_size: int
    current_stack: list[str]
    stated_need: str
    actual_pains: list[str]
    hidden_needs: list[str]
    stakeholders: dict[str, str]
    objections: list[str]
    budget: str
    timeline: str


# ---------------------------------------------------------------------------
# 1. DISCOVERY CALL SIMULATOR
# ---------------------------------------------------------------------------

@dataclass
class DiscoveryCallScore:
    """Scoring result for a simulated discovery call."""
    pain_identification_score: float
    question_quality_score: float
    stakeholder_mapping_score: float
    next_steps_score: float
    open_vs_closed_ratio: float
    total_score: float
    identified_pains: list[str]
    missed_pains: list[str]
    identified_stakeholders: list[str]
    missed_stakeholders: list[str]
    feedback: list[str]


OPEN_QUESTION_STARTERS = (
    "how", "what", "why", "tell me", "walk me through", "describe",
    "can you explain", "help me understand", "in what way", "to what extent",
)

CLOSED_QUESTION_STARTERS = (
    "do you", "is there", "have you", "are you", "will you", "did you",
    "does your", "can you", "would you", "is it", "was it", "has your",
)


def _is_open_ended(question: str) -> bool:
    """Determine whether a question is open-ended."""
    q = question.strip().lower()
    for starter in OPEN_QUESTION_STARTERS:
        if q.startswith(starter):
            return True
    return False


def _pain_keywords(pain: str) -> list[str]:
    """Extract meaningful keywords from a pain description."""
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "of", "in",
                  "to", "for", "and", "or", "but", "on", "at", "by", "with",
                  "from", "that", "this", "it", "not", "no", "be", "has",
                  "have", "had", "do", "does", "did"}
    words = re.findall(r"[a-z]+", pain.lower())
    return [w for w in words if len(w) > 3 and w not in stop_words]


def score_discovery_call(
    prospect: Prospect,
    questions: list[str],
    proposed_next_step: str,
) -> DiscoveryCallScore:
    """Score a set of discovery questions against a prospect profile.

    This is the complete reference implementation for Exercise 1.
    """
    # 1. Open vs closed ratio
    if not questions:
        open_ratio = 0.0
    else:
        open_count = sum(1 for q in questions if _is_open_ended(q))
        open_ratio = open_count / len(questions)

    # 2. Pain identification
    questions_lower = [q.lower() for q in questions]
    identified_pains: list[str] = []
    missed_pains: list[str] = []

    for pain in prospect.actual_pains:
        keywords = _pain_keywords(pain)
        found = any(
            any(kw in ql for kw in keywords)
            for ql in questions_lower
        )
        if found:
            identified_pains.append(pain)
        else:
            missed_pains.append(pain)

    total_pains = len(prospect.actual_pains) or 1
    pain_score = (len(identified_pains) / total_pains) * 10

    # 3. Stakeholder mapping
    identified_stakeholders: list[str] = []
    missed_stakeholders: list[str] = []
    all_q_text = " ".join(questions_lower)

    for role_name, role_desc in prospect.stakeholders.items():
        role_keywords = _pain_keywords(role_name + " " + role_desc)
        found = any(kw in all_q_text for kw in role_keywords)
        if found:
            identified_stakeholders.append(role_name)
        else:
            missed_stakeholders.append(role_name)

    total_stakeholders = len(prospect.stakeholders) or 1
    stakeholder_score = (len(identified_stakeholders) / total_stakeholders) * 10

    # 4. Question quality
    q_quality = 5.0
    if open_ratio > 0.6:
        q_quality += 1
    if open_ratio < 0.4:
        q_quality -= 1
    if len(questions) >= 6:
        q_quality += 1
    if len(questions) < 4:
        q_quality -= 1
    # Implication questions
    implication_words = ("impact", "cost", "what happens if", "consequence",
                         "affect", "downstream", "risk")
    if any(any(iw in ql for iw in implication_words) for ql in questions_lower):
        q_quality += 1
    # Need-payoff questions
    payoff_words = ("what would", "how would", "ideal", "great look like",
                    "success look like")
    if any(any(pw in ql for pw in payoff_words) for ql in questions_lower):
        q_quality += 1
    # Competition questions
    if any(any(cw in ql for cw in ("other solutions", "evaluated", "looked at",
                                    "competitor", "alternative"))
           for ql in questions_lower):
        q_quality += 1
    q_quality = max(0.0, min(10.0, q_quality))

    # 5. Next steps scoring
    ns = proposed_next_step.lower()
    ns_score = 5.0
    action_words = ("demo", "poc", "meeting", "call", "presentation",
                    "workshop", "session", "walkthrough")
    if any(aw in ns for aw in action_words):
        ns_score += 2
    timing_words = ("next week", "tuesday", "wednesday", "monday", "thursday",
                    "friday", "tomorrow", "next", "this week", "schedule")
    if any(tw in ns for tw in timing_words):
        ns_score += 2
    # Stakeholder mention
    for role_name in prospect.stakeholders:
        if role_name.lower() in ns:
            ns_score += 1
            break
    if not ns or ns in ("follow up", "get back to you", "touch base"):
        ns_score -= 2
    ns_score = max(0.0, min(10.0, ns_score))

    # 6. Total and feedback
    total = pain_score + q_quality + stakeholder_score + ns_score
    feedback: list[str] = []
    if open_ratio >= 0.7:
        feedback.append("Excellent open-to-closed question ratio.")
    elif open_ratio < 0.5:
        feedback.append("Too many closed-ended questions. Reframe to 'how' and 'what'.")
    if missed_pains:
        feedback.append(f"Missed {len(missed_pains)} pain point(s). Dig deeper on: "
                        + "; ".join(missed_pains[:2]))
    if missed_stakeholders:
        feedback.append(f"Missed {len(missed_stakeholders)} stakeholder(s): "
                        + ", ".join(missed_stakeholders))
    if ns_score >= 8:
        feedback.append("Strong next step — specific, timed, and includes stakeholders.")
    elif ns_score < 5:
        feedback.append("Weak next step. Propose a specific action with a date.")

    return DiscoveryCallScore(
        pain_identification_score=round(pain_score, 1),
        question_quality_score=round(q_quality, 1),
        stakeholder_mapping_score=round(stakeholder_score, 1),
        next_steps_score=round(ns_score, 1),
        open_vs_closed_ratio=round(open_ratio, 2),
        total_score=round(total, 1),
        identified_pains=identified_pains,
        missed_pains=missed_pains,
        identified_stakeholders=identified_stakeholders,
        missed_stakeholders=missed_stakeholders,
        feedback=feedback,
    )


# ---------------------------------------------------------------------------
# 2. SYSTEM DESIGN TEMPLATE
# ---------------------------------------------------------------------------

@dataclass
class SystemDesignDocument:
    """A structured SE system design document."""
    customer_profile: str
    business_problem: str
    success_metrics: list[str]
    architecture_components: list[str]
    integration_points: list[dict[str, str]]
    operational_concerns: list[str]
    rollout_phases: list[dict[str, str]]

    def validate_completeness(self) -> tuple[float, list[str]]:
        """Validate the design against the SE framework and return a score."""
        score = 0.0
        missing: list[str] = []

        # Customer profile
        if self.customer_profile and any(c.isdigit() for c in self.customer_profile):
            score += 1.25
        else:
            missing.append("Customer profile should include company size (numbers)")

        industry_terms = ("healthcare", "finance", "fintech", "saas", "e-commerce",
                          "retail", "manufacturing", "services", "technology",
                          "education", "media", "logistics", "enterprise")
        if any(t in self.customer_profile.lower() for t in industry_terms):
            score += 1.25
        else:
            missing.append("Customer profile should mention the industry")

        # Business problem
        pain_words = ("cost", "time", "risk", "pain", "problem", "waste", "slow",
                      "manual", "error", "compliance", "stale", "hours", "broken")
        if any(pw in self.business_problem.lower() for pw in pain_words):
            score += 1.25
        else:
            missing.append("Business problem should reference a customer pain "
                           "(cost, time, risk, etc.)")

        # Success metrics
        if len(self.success_metrics) >= 2:
            score += 1.25
        else:
            missing.append("Need at least 2 success metrics")

        # Architecture
        if len(self.architecture_components) >= 3:
            score += 1.25
        else:
            missing.append("Need at least 3 architecture components")

        existing_refs = ("existing", "current", "legacy")
        if any(any(er in comp.lower() for er in existing_refs)
               for comp in self.architecture_components):
            score += 0.625
        else:
            missing.append("Architecture should reference customer's existing systems")

        # Integration points
        if len(self.integration_points) >= 2:
            score += 0.625
        else:
            missing.append("Need at least 2 integration points")

        required_keys = {"system", "protocol", "auth"}
        valid_ips = sum(
            1 for ip in self.integration_points
            if required_keys.issubset(ip.keys())
        )
        if valid_ips == len(self.integration_points) and self.integration_points:
            score += 0.625
        elif self.integration_points:
            missing.append("Each integration point needs: system, protocol, auth")

        # Operational concerns
        ops_categories = {
            "monitoring": ("monitor", "alert", "dashboard", "observ", "metric"),
            "security": ("security", "encrypt", "auth", "tls", "soc", "compliance"),
            "scaling": ("scal", "elastic", "horizontal", "capacity", "performance"),
            "support": ("support", "sla", "incident", "on-call", "help desk"),
            "disaster_recovery": ("disaster", "backup", "recovery", "rpo", "rto"),
        }
        covered_categories = set()
        for concern in self.operational_concerns:
            cl = concern.lower()
            for cat, keywords in ops_categories.items():
                if any(kw in cl for kw in keywords):
                    covered_categories.add(cat)
        if len(covered_categories) >= 2:
            score += 1.25
        else:
            missing.append("Operational concerns should cover at least 2 of: "
                           "monitoring, security, scaling, support, DR")

        # Rollout phases
        if len(self.rollout_phases) >= 2:
            score += 0.625
        else:
            missing.append("Need at least 2 rollout phases")

        phase_keys = {"name", "duration", "milestone"}
        valid_phases = sum(
            1 for p in self.rollout_phases if phase_keys.issubset(p.keys())
        )
        if valid_phases == len(self.rollout_phases) and self.rollout_phases:
            score += 0.625
        elif self.rollout_phases:
            missing.append("Each phase needs: name, duration, milestone")

        return round(min(score, 10.0), 1), missing

    def to_outline(self) -> list[str]:
        """Generate a presentation-ready slide outline."""
        slides = [
            f"Slide 1: Customer Profile — {self.customer_profile[:80]}",
            f"Slide 2: Business Problem — {self.business_problem[:80]}",
            f"Slide 3: Success Metrics — {len(self.success_metrics)} KPIs",
            f"Slide 4: Architecture — {len(self.architecture_components)} components",
            f"Slide 5: Integration Points — {len(self.integration_points)} integrations",
            f"Slide 6: Operational Concerns — {len(self.operational_concerns)} items",
            f"Slide 7: Rollout Plan — {len(self.rollout_phases)} phases",
            "Slide 8: Q&A and Next Steps",
        ]
        return slides


def build_system_design(
    customer_profile: str,
    business_problem: str,
    success_metrics: list[str],
    architecture_components: list[str],
    integration_points: list[dict[str, str]],
    operational_concerns: list[str],
    rollout_phases: list[dict[str, str]],
) -> dict[str, Any]:
    """Build, validate, and return a complete system design outline.

    This is the complete reference implementation for Exercise 2.
    """
    doc = SystemDesignDocument(
        customer_profile=customer_profile,
        business_problem=business_problem,
        success_metrics=success_metrics,
        architecture_components=architecture_components,
        integration_points=integration_points,
        operational_concerns=operational_concerns,
        rollout_phases=rollout_phases,
    )

    completeness, missing = doc.validate_completeness()
    outline = doc.to_outline()

    return {
        "document": doc,
        "completeness_score": completeness,
        "missing_elements": missing,
        "presentation_outline": outline,
    }


# ---------------------------------------------------------------------------
# 3. DEMO SCRIPT TEMPLATE
# ---------------------------------------------------------------------------

@dataclass
class DemoSegment:
    """A single segment of a demo script."""
    topic: str
    duration_seconds: int
    key_points: list[str]
    transition_phrase: str = ""
    audience_notes: str = ""


@dataclass
class DemoScript:
    """A complete demo script with timing and structure validation."""
    title: str
    target_audience: str
    segments: list[DemoSegment]
    target_duration_seconds: int = 1200  # 20 minutes

    def total_duration(self) -> int:
        return sum(s.duration_seconds for s in self.segments)

    def has_opening(self) -> bool:
        if not self.segments:
            return False
        opening_words = ("hook", "opening", "intro", "context", "welcome")
        return any(w in self.segments[0].topic.lower() for w in opening_words)

    def has_close(self) -> bool:
        if not self.segments:
            return False
        close_words = ("close", "next step", "summary", "wrap", "recap", "closing")
        return any(w in self.segments[-1].topic.lower() for w in close_words)

    def has_wow_moment(self) -> bool:
        wow_words = ("wow", "surprise", "aha", "unexpected", "magic",
                     "watch this", "live")
        return any(
            any(w in seg.topic.lower() for w in wow_words)
            for seg in self.segments
        )

    def validate(self) -> dict[str, Any]:
        """Validate the demo script and return evaluation results."""
        total = self.total_duration()
        target = self.target_duration_seconds

        # Timing feedback
        if total < target * 0.8:
            gap = target - total
            timing = (f"Under time by {gap} seconds. Consider adding depth "
                      "to your main segment or adding a Q&A buffer.")
        elif total > target * 1.1:
            over = total - target
            timing = (f"Over time by {over} seconds. Cut your least "
                      "impactful segment or tighten transitions.")
        else:
            diff = abs(total - target)
            timing = f"Good timing. Within {diff} seconds of target."

        # Structure feedback
        structure: list[str] = []
        if not self.has_opening():
            structure.append("Missing opening hook. Start with a customer-"
                             "relevant provocative statement.")
        if not self.has_close():
            structure.append("Missing close. End with a recap of value and "
                             "a concrete next step.")
        if not self.has_wow_moment():
            structure.append("No wow moment identified. Add a segment that "
                             "shows something the customer cannot do today.")
        for i, seg in enumerate(self.segments):
            if not seg.key_points:
                structure.append(f"Segment '{seg.topic}' has no key points. "
                                 "Add 2-3 bullet points.")
            if not seg.transition_phrase and i < len(self.segments) - 1:
                structure.append(f"Segment '{seg.topic}' has no transition phrase.")

        # Timed runsheet
        runsheet: list[dict[str, Any]] = []
        cumulative = 0
        for seg in self.segments:
            minutes = cumulative // 60
            seconds = cumulative % 60
            runsheet.append({
                "segment": seg.topic,
                "start_time": f"{minutes}:{seconds:02d}",
                "duration": seg.duration_seconds,
                "key_points": seg.key_points,
            })
            cumulative += seg.duration_seconds

        # Overall score
        score = 5.0
        if self.has_opening():
            score += 1
        if self.has_close():
            score += 1
        if self.has_wow_moment():
            score += 1
        if abs(total - target) <= target * 0.1:
            score += 1
        if all(s.key_points for s in self.segments):
            score += 1
        score -= min(3, len(structure))
        score = max(0.0, min(10.0, score))

        return {
            "total_duration_seconds": total,
            "has_opening": self.has_opening(),
            "has_close": self.has_close(),
            "has_wow_moment": self.has_wow_moment(),
            "segment_count": len(self.segments),
            "timing_feedback": timing,
            "structure_feedback": structure,
            "missing_elements": structure,
            "overall_score": round(score, 1),
            "timed_runsheet": runsheet,
        }


def build_demo_script_example() -> DemoScript:
    """Build a sample demo script for reference.

    This is the complete reference implementation for Exercise 3.
    """
    return DemoScript(
        title="Data Integration Platform — E-Commerce Demo",
        target_audience="Head of Data + Senior Data Engineer",
        target_duration_seconds=1200,
        segments=[
            DemoSegment(
                topic="Hook / Opening",
                duration_seconds=30,
                key_points=[
                    "Your team spends 15 hours/week on manual CSV uploads. "
                    "Let me show you how to get that to zero.",
                ],
                transition_phrase="Let me set the stage for what we'll cover today...",
                audience_notes="Speak to the Head of Data first — they care about time savings.",
            ),
            DemoSegment(
                topic="Context — Their Problem",
                duration_seconds=120,
                key_points=[
                    "Recap their 3 pain points from discovery",
                    "Quantify the cost: 15 hrs/week * $60/hr = $46K/year",
                    "Set agenda: 3 segments mapped to their priorities",
                ],
                transition_phrase="Now let me show you how we solve the first problem...",
                audience_notes="Confirm priorities with the audience before proceeding.",
            ),
            DemoSegment(
                topic="Segment 1 — Automated Shopify Sync",
                duration_seconds=420,
                key_points=[
                    "Show one-click Shopify connector setup",
                    "Live: create a connection and see data flowing",
                    "Show schema detection and mapping",
                    "Outcome: No more CSV uploads, ever.",
                ],
                transition_phrase="That's the data ingestion. Now let me show you "
                                  "what happens to the data once it lands...",
                audience_notes="The data engineer will want to see the schema mapping in detail.",
            ),
            DemoSegment(
                topic="Segment 2 — Transformation and Quality",
                duration_seconds=300,
                key_points=[
                    "Show transformation builder",
                    "Data quality checks with alerting",
                    "Outcome: Clean, trusted data without manual QA",
                ],
                transition_phrase="Now for the part that I think will really change "
                                  "how your team works...",
            ),
            DemoSegment(
                topic="Wow Moment — Live Schema Change",
                duration_seconds=120,
                key_points=[
                    "Change a column type in the source Shopify data",
                    "Watch the platform detect, adapt, and continue processing",
                    "Zero downtime, zero manual intervention",
                ],
                transition_phrase="Let me bring it all together...",
                audience_notes="This is the money shot. Pause and let it sink in.",
            ),
            DemoSegment(
                topic="Close — Recap and Next Steps",
                duration_seconds=210,
                key_points=[
                    "Recap: zero CSV uploads, automated quality, zero-downtime schema changes",
                    "Propose next step: 2-week POC with their Shopify + Postgres",
                    "Ask: Does this address your top priorities?",
                ],
                audience_notes="Let the Head of Data respond before proposing the POC.",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# 4. STAR STORY FORMATTER
# ---------------------------------------------------------------------------

@dataclass
class FormattedStory:
    """A behavioral story parsed into STAR+I format."""
    situation: str
    task: str
    action: str
    result: str
    impact: str
    question_category: str
    completeness_score: float
    missing_elements: list[str]
    feedback: list[str]


SE_BEHAVIORAL_CATEGORIES = {
    "customer empathy", "technical communication", "resilience",
    "collaboration", "problem-solving", "prioritization",
}


def _extract_section(text: str, markers: list[str]) -> str:
    """Extract a section of text following any of the given markers."""
    text_lower = text.lower()
    for marker in markers:
        idx = text_lower.find(marker.lower())
        if idx != -1:
            start = idx + len(marker)
            # Find the next section marker or end of text
            next_markers = [
                "situation:", "task:", "action:", "result:", "impact:",
                "context:", "background:", "responsibility:", "my role:",
                "outcome:", "customer impact:",
            ]
            end = len(text)
            for nm in next_markers:
                nm_idx = text_lower.find(nm.lower(), start + 5)
                if nm_idx != -1 and nm_idx < end and nm.lower() != marker.lower():
                    end = nm_idx
            section = text[start:end].strip()
            # Clean up leading colons and whitespace
            section = section.lstrip(":").strip()
            return section
    return ""


def format_star_story(raw_story: str, question_category: str) -> FormattedStory:
    """Parse a raw story into STAR+I format with validation.

    This is the complete reference implementation for Exercise 5.
    """
    situation = _extract_section(raw_story, [
        "situation:", "context:", "background:",
    ])
    task = _extract_section(raw_story, [
        "task:", "responsibility:", "my role:", "i was responsible for",
        "i needed to",
    ])
    action = _extract_section(raw_story, [
        "action:", "i did:", "steps:", "what i did:",
    ])
    result = _extract_section(raw_story, [
        "result:", "outcome:", "the result was",
    ])
    impact = _extract_section(raw_story, [
        "impact:", "customer impact:", "the customer",
    ])

    # If no markers found at all, try splitting by sentences
    if not any([situation, task, action, result, impact]):
        sentences = [s.strip() for s in raw_story.split(".") if s.strip()]
        if len(sentences) >= 5:
            situation = sentences[0] + "."
            task = sentences[1] + "."
            action = ". ".join(sentences[2:-2]) + "."
            result = sentences[-2] + "."
            impact = sentences[-1] + "."

    # Validation and scoring
    score = 0.0
    missing: list[str] = []
    feedback: list[str] = []

    elements = {
        "Situation": situation,
        "Task": task,
        "Action": action,
        "Result": result,
        "Impact": impact,
    }

    for name, text in elements.items():
        if text:
            score += 2.0
        else:
            missing.append(name)

    # Quality checks
    if situation:
        context_words = ("at", "when", "while", "during", "in my role",
                         "i was", "we were", "the company")
        if any(cw in situation.lower() for cw in context_words):
            pass
        else:
            feedback.append("Situation should set context — include 'when', "
                            "'where', or 'while' framing.")

    if action:
        if "i " in action.lower():
            pass
        else:
            feedback.append("Make actions first-person. Use 'I did X' not "
                            "'the team did X'.")
    else:
        feedback.append("Missing Action. Describe what YOU specifically did "
                        "(3-5 bullet points).")

    if result:
        if any(c.isdigit() for c in result):
            pass
        else:
            feedback.append("Quantify your result. Add specific numbers, "
                            "percentages, or dollar amounts.")
    else:
        feedback.append("Missing Result. What was the measurable outcome?")

    if impact:
        customer_words = ("customer", "client", "user", "prospect",
                          "their", "they were able")
        if any(cw in impact.lower() for cw in customer_words):
            pass
        else:
            feedback.append("Add customer impact. How did this help the "
                            "customer specifically?")
    else:
        feedback.append("Missing Impact. How did the customer benefit?")

    # Category check
    if question_category.lower() not in SE_BEHAVIORAL_CATEGORIES:
        feedback.append(f"'{question_category}' is not a standard SE "
                        f"behavioral category. Standard categories: "
                        f"{', '.join(sorted(SE_BEHAVIORAL_CATEGORIES))}")

    return FormattedStory(
        situation=situation,
        task=task,
        action=action,
        result=result,
        impact=impact,
        question_category=question_category,
        completeness_score=min(score, 10.0),
        missing_elements=missing,
        feedback=feedback,
    )


# ---------------------------------------------------------------------------
# 5. POC RUBRIC
# ---------------------------------------------------------------------------

@dataclass
class POCSubmission:
    """Profile of a take-home POC submission."""
    has_readme: bool
    has_architecture_diagram: bool
    code_quality_score: float
    test_coverage: float
    documentation_quality: float
    presentation_quality: float
    has_limitations_section: bool
    has_setup_instructions: bool
    has_working_demo: bool
    lines_of_code: int
    languages_used: list[str]


@dataclass
class POCEvaluation:
    """Evaluation result for a POC submission."""
    functionality_score: float
    code_quality_score: float
    documentation_score: float
    architecture_score: float
    presentation_score: float
    polish_score: float
    overall_score: float
    grade: str
    improvement_suggestions: list[str]


def score_poc_submission(submission: POCSubmission) -> POCEvaluation:
    """Score a take-home POC submission against the SE rubric.

    This is the complete reference implementation for Exercise 4.
    """
    # Functionality (0-10)
    functionality = 0.0
    if submission.has_working_demo:
        functionality += 4
    if submission.has_setup_instructions:
        functionality += 3
    if submission.test_coverage >= 0.3:
        functionality += 2
    if submission.test_coverage >= 0.7:
        functionality += 1

    # Code quality (0-10) — pass-through
    code_quality = submission.code_quality_score

    # Documentation (0-10)
    documentation = 0.0
    if submission.has_readme:
        documentation += 3
    if submission.has_architecture_diagram:
        documentation += 2
    if submission.has_limitations_section:
        documentation += 2
    if submission.has_setup_instructions:
        documentation += 2
    if submission.documentation_quality >= 7:
        documentation += 1

    # Architecture (0-10)
    architecture = 0.0
    if submission.has_architecture_diagram:
        architecture += 4
    if len(submission.languages_used) >= 1:
        architecture += 3
    if submission.has_limitations_section:
        architecture += 2
    if submission.lines_of_code > 100:
        architecture += 1

    # Presentation (0-10) — pass-through
    presentation = submission.presentation_quality

    # Polish (0-10)
    polish = 5.0
    if (submission.has_working_demo and submission.has_readme
            and submission.has_setup_instructions):
        polish += 2
    if submission.test_coverage > 0.5 and submission.has_limitations_section:
        polish += 2
    if submission.documentation_quality >= 8:
        polish += 1
    polish = max(0.0, min(10.0, polish))

    # Overall (weighted)
    overall = (
        functionality * 0.25
        + code_quality * 0.20
        + documentation * 0.20
        + architecture * 0.15
        + presentation * 0.15
        + polish * 0.05
    )

    # Grade
    if overall >= 8.0:
        grade = "Strong Hire"
    elif overall >= 6.5:
        grade = "Hire"
    elif overall >= 4.5:
        grade = "Needs Work"
    else:
        grade = "No Hire"

    # Suggestions
    suggestions: list[str] = []
    if functionality < 6:
        suggestions.append("Ensure the demo works end-to-end. Add setup "
                           "instructions that someone can follow in < 5 minutes.")
    if code_quality < 6:
        suggestions.append("Improve code structure: separate concerns into "
                           "modules, add docstrings, handle common errors.")
    if documentation < 6:
        suggestions.append("Add a README with problem statement, architecture "
                           "diagram, setup instructions, and limitations section.")
    if architecture < 6:
        suggestions.append("Include an architecture diagram. Explain your "
                           "technology choices and what you would change at scale.")
    if presentation < 6:
        suggestions.append("Practice presenting: start with the problem and demo, "
                           "not the code. Prepare for Q&A on tradeoffs.")
    if polish < 6:
        suggestions.append("Add polish: loading states, helpful error messages, "
                           "consistent formatting, and at least basic test coverage.")

    return POCEvaluation(
        functionality_score=round(functionality, 1),
        code_quality_score=round(code_quality, 1),
        documentation_score=round(documentation, 1),
        architecture_score=round(architecture, 1),
        presentation_score=round(presentation, 1),
        polish_score=round(polish, 1),
        overall_score=round(overall, 1),
        grade=grade,
        improvement_suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# Main demonstration
# ---------------------------------------------------------------------------

def main():
    """Run all examples to demonstrate functionality."""

    # --- Example 1: Discovery Call Simulator ---
    print("=" * 60)
    print("1. DISCOVERY CALL SIMULATOR")
    print("=" * 60)

    prospect = Prospect(
        name="Rachel Kim",
        role="VP of Data Engineering",
        company="Meridian Financial",
        industry="Financial Services",
        company_size=2500,
        current_stack=["Hadoop", "Oracle", "Tableau", "Java ETL"],
        stated_need="Modernize data platform",
        actual_pains=[
            "Hadoop maintenance — 60% of team time on maintenance",
            "Reports are 48 hours stale",
            "No data lineage for SOX compliance",
            "Engineers who built the system have left",
        ],
        hidden_needs=[
            "Rachel needs to show board progress by Q3",
            "CTO is skeptical of cloud",
        ],
        stakeholders={
            "CTO": "Budget holder, skeptical of cloud",
            "Head of Compliance": "Needs SOX audit trail",
            "Lead Data Engineer": "Day-to-day evaluator",
        },
        objections=["Competitor pricing is usage-based"],
        budget="$500K Year 1",
        timeline="Board review in Q3",
    )

    questions = [
        "Can you walk me through your current data architecture?",
        "What's driving the timing of this migration?",
        "What's causing the most pain with your Hadoop setup?",
        "Who maintains the ETL pipelines today?",
        "How stale is your reporting data, and what decisions depend on it?",
        "What does your compliance process look like for data lineage?",
        "Who else is involved in this decision — CTO, compliance?",
        "What other solutions have you looked at so far?",
        "If this is successful, what does great look like in 12 months?",
    ]

    score = score_discovery_call(
        prospect, questions,
        "I'd like to schedule a tailored demo next Tuesday for you and your CTO.",
    )
    print(f"  Pain: {score.pain_identification_score}/10 "
          f"(identified {len(score.identified_pains)}/{len(prospect.actual_pains)})")
    print(f"  Questions: {score.question_quality_score}/10 "
          f"(open ratio: {score.open_vs_closed_ratio:.0%})")
    print(f"  Stakeholders: {score.stakeholder_mapping_score}/10")
    print(f"  Next Steps: {score.next_steps_score}/10")
    print(f"  Total: {score.total_score}/40")
    for fb in score.feedback:
        print(f"  -> {fb}")

    # --- Example 2: System Design Template ---
    print("\n" + "=" * 60)
    print("2. SYSTEM DESIGN TEMPLATE")
    print("=" * 60)

    design = build_system_design(
        customer_profile="Professional services, 5000 employees, SOC 2 required",
        business_problem="Employees waste 6 hours/week searching. Cost: $23M/year.",
        success_metrics=["Reduce search time by 50%", "70% adoption in 6 months"],
        architecture_components=[
            "Existing SharePoint (data source)",
            "Ingestion pipeline (parse, chunk, embed)",
            "Vector database (Pinecone)",
            "RAG query service",
            "Slack bot interface",
        ],
        integration_points=[
            {"system": "SharePoint", "protocol": "Graph API", "auth": "OAuth 2.0"},
            {"system": "Okta", "protocol": "OIDC", "auth": "Standard"},
        ],
        operational_concerns=[
            "Monitoring: query latency, answer quality, cost per query",
            "Security: TLS 1.3, AES-256, SOC 2 compliance",
            "Scaling: vector DB horizontal scaling, LLM rate limit queue",
        ],
        rollout_phases=[
            {"name": "Phase 1", "duration": "Weeks 1-4", "milestone": "100 beta users"},
            {"name": "Phase 2", "duration": "Weeks 5-8", "milestone": "1000 users"},
            {"name": "Phase 3", "duration": "Weeks 9-16", "milestone": "Full rollout"},
        ],
    )
    print(f"  Completeness: {design['completeness_score']}/10")
    print(f"  Missing: {design['missing_elements'] or 'None'}")
    print(f"  Slides: {len(design['presentation_outline'])}")
    for slide in design["presentation_outline"]:
        print(f"    {slide}")

    # --- Example 3: Demo Script Template ---
    print("\n" + "=" * 60)
    print("3. DEMO SCRIPT TEMPLATE")
    print("=" * 60)

    script = build_demo_script_example()
    evaluation = script.validate()
    total_min = evaluation["total_duration_seconds"] // 60
    total_sec = evaluation["total_duration_seconds"] % 60
    print(f"  Duration: {total_min}m {total_sec}s")
    print(f"  Opening: {evaluation['has_opening']}, "
          f"Close: {evaluation['has_close']}, "
          f"Wow: {evaluation['has_wow_moment']}")
    print(f"  Score: {evaluation['overall_score']}/10")
    print(f"  Timing: {evaluation['timing_feedback']}")
    print("  Runsheet:")
    for item in evaluation["timed_runsheet"]:
        print(f"    [{item['start_time']}] {item['segment']} "
              f"({item['duration']}s)")

    # --- Example 4: STAR Story Formatter ---
    print("\n" + "=" * 60)
    print("4. STAR STORY FORMATTER")
    print("=" * 60)

    story = format_star_story(
        raw_story=textwrap.dedent("""
            Situation: I was supporting a $200K deal with a logistics company.
            We were in the POC phase with a 2-week deadline.

            Task: I was responsible for delivering a working integration
            between our platform and their Warehouse Management System.

            Action: Three days before the deadline, the integration broke
            due to an API version mismatch. I diagnosed the root cause
            within 2 hours, coordinated with our product team for an
            emergency patch, and built a temporary workaround. I also
            called the customer's lead engineer to explain transparently.

            Result: We delivered the POC on time. The customer signed for
            $200K ARR within 3 weeks.

            Impact: The customer launched their real-time tracking feature
            2 months ahead of schedule.
        """),
        question_category="Problem-Solving",
    )
    print(f"  Situation: {story.situation[:70]}...")
    print(f"  Task: {story.task[:70]}...")
    print(f"  Action: {story.action[:70]}...")
    print(f"  Result: {story.result[:70]}...")
    print(f"  Impact: {story.impact[:70]}...")
    print(f"  Completeness: {story.completeness_score}/10")
    if story.feedback:
        for fb in story.feedback:
            print(f"  -> {fb}")

    # --- Example 5: POC Rubric ---
    print("\n" + "=" * 60)
    print("5. POC RUBRIC")
    print("=" * 60)

    evaluation = score_poc_submission(POCSubmission(
        has_readme=True,
        has_architecture_diagram=True,
        code_quality_score=7.5,
        test_coverage=0.45,
        documentation_quality=8.0,
        presentation_quality=7.0,
        has_limitations_section=True,
        has_setup_instructions=True,
        has_working_demo=True,
        lines_of_code=350,
        languages_used=["Python", "JavaScript"],
    ))
    print(f"  Functionality: {evaluation.functionality_score}/10")
    print(f"  Code Quality: {evaluation.code_quality_score}/10")
    print(f"  Documentation: {evaluation.documentation_score}/10")
    print(f"  Architecture: {evaluation.architecture_score}/10")
    print(f"  Presentation: {evaluation.presentation_score}/10")
    print(f"  Polish: {evaluation.polish_score}/10")
    print(f"  Overall: {evaluation.overall_score}/10 — {evaluation.grade}")
    if evaluation.improvement_suggestions:
        for s in evaluation.improvement_suggestions:
            print(f"  -> {s}")
    else:
        print("  -> No improvement suggestions — strong submission!")


if __name__ == "__main__":
    main()
