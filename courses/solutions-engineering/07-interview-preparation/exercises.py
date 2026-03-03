"""
Module 07: SE/FDE Interview Preparation — Practice Exercises

Exercises designed to build and test the skills assessed in real SE/FDE
interviews: discovery call execution, system design for SEs, demo planning,
take-home POC evaluation, behavioral story formatting, and interview
readiness assessment.

Each exercise uses dataclasses to model inputs and outputs, includes a
detailed docstring with hints, and has a corresponding test function.

Rules:
- No external dependencies. Standard library only.
- Read the full docstring and referenced MD sections before starting.
- These exercises model SE workflows, not coding puzzles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Shared dataclasses used across exercises
# ---------------------------------------------------------------------------

@dataclass
class Prospect:
    """A simulated prospect for discovery call exercises."""
    name: str
    role: str
    company: str
    industry: str
    company_size: int
    current_stack: list[str]
    stated_need: str
    actual_pains: list[str]
    hidden_needs: list[str]
    stakeholders: dict[str, str]  # name -> role/description
    objections: list[str]
    budget: str
    timeline: str


@dataclass
class DiscoveryCallScore:
    """Scoring result for a discovery call simulation."""
    pain_identification_score: float      # 0-10
    question_quality_score: float         # 0-10
    stakeholder_mapping_score: float      # 0-10
    next_steps_score: float               # 0-10
    open_vs_closed_ratio: float           # 0.0-1.0 (fraction that are open-ended)
    total_score: float                    # 0-40
    identified_pains: list[str]
    missed_pains: list[str]
    identified_stakeholders: list[str]
    missed_stakeholders: list[str]
    feedback: list[str]


@dataclass
class SystemDesignOutline:
    """A structured SE system design output."""
    customer_profile: str
    business_problem: str
    success_metrics: list[str]
    architecture_components: list[str]
    integration_points: list[dict[str, str]]  # each: {system, protocol, auth, notes}
    operational_concerns: list[str]
    rollout_phases: list[dict[str, str]]      # each: {name, duration, milestone}
    completeness_score: float                  # 0-10
    missing_elements: list[str]
    presentation_outline: list[str]


@dataclass
class DemoSegment:
    """A single segment of a demo script."""
    topic: str
    duration_seconds: int
    key_points: list[str]
    transition_phrase: str = ""


@dataclass
class DemoEvaluation:
    """Evaluation result for a demo script."""
    total_duration_seconds: int
    has_opening: bool
    has_close: bool
    has_wow_moment: bool
    segment_count: int
    timing_feedback: str
    structure_feedback: list[str]
    missing_elements: list[str]
    overall_score: float  # 0-10
    timed_runsheet: list[dict[str, Any]]


@dataclass
class POCSubmission:
    """Profile of a take-home POC submission for evaluation."""
    has_readme: bool
    has_architecture_diagram: bool
    code_quality_score: float          # 0-10, self-assessed or provided
    test_coverage: float               # 0.0-1.0
    documentation_quality: float       # 0-10
    presentation_quality: float        # 0-10
    has_limitations_section: bool
    has_setup_instructions: bool
    has_working_demo: bool
    lines_of_code: int
    languages_used: list[str]


@dataclass
class POCEvaluation:
    """Evaluation result for a take-home POC."""
    functionality_score: float         # 0-10
    code_quality_score: float          # 0-10
    documentation_score: float         # 0-10
    architecture_score: float          # 0-10
    presentation_score: float          # 0-10
    polish_score: float                # 0-10
    overall_score: float               # weighted 0-10
    grade: str                         # "Strong Hire", "Hire", "Needs Work", "No Hire"
    improvement_suggestions: list[str]


@dataclass
class FormattedStory:
    """A behavioral story formatted in STAR+I structure."""
    situation: str
    task: str
    action: str
    result: str
    impact: str
    question_category: str
    completeness_score: float          # 0-10
    missing_elements: list[str]
    feedback: list[str]


@dataclass
class ReadinessScore:
    """Overall interview readiness assessment."""
    stories_score: float               # 0-10
    mock_calls_score: float            # 0-10
    system_design_score: float         # 0-10
    poc_score: float                   # 0-10
    behavioral_score: float            # 0-10
    overall_score: float               # 0-10
    overall_grade: str                 # "Ready", "Almost Ready", "Needs Work", "Not Ready"
    weak_areas: list[str]
    study_plan: list[str]


# ============================================================================
# EXERCISE 1: Discovery Call Simulator
#
# READ FIRST:
#   01-se-fde-interview-formats-and-fundamentals.md
#     -> "Common Interview Formats" -> "Discovery/Mock Call" — what great
#        looks like, what gets you rejected, the talk-to-listen ratio.
#     -> "Evaluation Criteria" -> "What Interviewers Score at Each Stage"
#        — the scoring dimensions for discovery calls.
#
# ALSO SEE:
#   examples.py
#     -> Section 1 "Discovery Call Simulator" — complete SimulatedProspect
#        with question evaluation engine, keyword matching, scoring logic.
#
# You are given a Prospect and a list of questions. The system evaluates
# how well your questions cover the prospect's pains, stakeholders, and
# needs. It also checks whether questions are open-ended vs closed.
#
# Key concepts: open-ended vs closed questions, pain identification,
# stakeholder mapping, SPIN questioning, next-step proposals.
# ============================================================================

def exercise_1_discovery_call_simulator(
    prospect: Prospect,
    questions: list[str],
    proposed_next_step: str,
) -> DiscoveryCallScore:
    """Simulate a discovery call and score the SE's questions.

    TODO: Implement this function.

    Steps:
    1. Classify each question as open-ended or closed.
       - Open-ended: starts with "how", "what", "why", "tell me", "walk me
         through", "describe", "can you explain", "help me understand"
       - Closed: starts with "do you", "is there", "have you", "are you",
         "will you", "did you", or is answerable with yes/no
       - Compute open_vs_closed_ratio = open_count / total_count

    2. Check pain identification.
       - For each pain in prospect.actual_pains, check if any question
         contains keywords related to that pain (use simple substring
         matching on lowercased strings).
       - Assign pain_identification_score: (identified / total_pains) * 10

    3. Check stakeholder mapping.
       - For each stakeholder in prospect.stakeholders, check if any
         question mentions the stakeholder's role (e.g., "CTO", "budget",
         "decision maker", "compliance", "security").
       - Assign stakeholder_mapping_score: (identified / total) * 10

    4. Score question quality.
       - Start at 5. Add 1 for each: ratio > 0.6, at least 6 questions,
         at least one implication question (contains "impact", "cost",
         "what happens if", "consequence"), at least one need-payoff
         question (contains "what would", "how would", "ideal").
       - Subtract 1 for: ratio < 0.4, fewer than 4 questions.
       - Clamp to 0-10.

    5. Score next steps.
       - Start at 5. Add 2 if the next step is specific (contains a
         concrete action like "demo", "POC", "meeting", "call"). Add 2
         if it includes timing (contains "next week", "Tuesday",
         "Wednesday", a date-like word). Add 1 if it references a
         stakeholder by role. Subtract 2 if it is empty or generic
         ("follow up", "get back to you"). Clamp to 0-10.

    6. Compute total_score = sum of four dimension scores.
       Generate feedback strings for notable strengths and weaknesses.
       Return a DiscoveryCallScore.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 2: System Design Skeleton Builder
#
# READ FIRST:
#   02-mock-scenarios-and-system-design.md
#     -> "SE System Design Framework" (Steps 1-6) — the six-step framework
#        with what to write on the whiteboard at each step.
#     -> "How SE System Design Differs from SWE System Design" — side-by-
#        side comparison of evaluation criteria.
#
# ALSO SEE:
#   examples.py
#     -> Section 2 "System Design Template" — SystemDesignDocument with
#        all fields, validate_completeness(), and to_outline().
#
# You are given a scenario description. Fill in a structured system design
# following the SE framework. The function validates completeness and
# generates a presentation-ready outline.
#
# Key concepts: customer-first design, integration awareness, phased
# rollout, business justification, success metrics.
# ============================================================================

def exercise_2_system_design_builder(
    customer_profile: str,
    business_problem: str,
    success_metrics: list[str],
    architecture_components: list[str],
    integration_points: list[dict[str, str]],
    operational_concerns: list[str],
    rollout_phases: list[dict[str, str]],
) -> SystemDesignOutline:
    """Build and validate an SE system design skeleton.

    TODO: Implement this function.

    Steps:
    1. Validate that customer_profile is non-empty and contains at least
       industry and size indicators (check for digits and common industry
       terms).

    2. Validate that business_problem references a customer pain (not
       just a technical description). Check for pain-related words:
       "cost", "time", "risk", "pain", "problem", "waste", "slow",
       "manual", "error", "compliance".

    3. Validate success_metrics:
       - At least 2 metrics
       - Each should be measurable (contains a number, percentage, or
         words like "reduce", "increase", "improve", "within")

    4. Validate architecture_components:
       - At least 3 components
       - Should include at least one that references the customer's
         existing system (contains "existing", "current", or a known
         technology name)

    5. Validate integration_points:
       - At least 2 integration points
       - Each should have keys: "system", "protocol", "auth"
       - Score higher if "notes" key is present

    6. Validate operational_concerns:
       - At least 3 concerns
       - Should cover at least 2 of: monitoring, security, scaling,
         support, disaster recovery

    7. Validate rollout_phases:
       - At least 2 phases
       - Each should have keys: "name", "duration", "milestone"

    8. Compute completeness_score (0-10) based on how many validations
       pass. List missing_elements for any that fail.

    9. Generate presentation_outline: a list of strings that form a
       slide-by-slide outline for presenting this design.
       Format:
         ["Slide 1: Customer Profile — {summary}",
          "Slide 2: Business Problem — {summary}",
          "Slide 3: Success Metrics — {count} KPIs",
          "Slide 4: Architecture — {count} components",
          "Slide 5: Integration Points — {count} integrations",
          "Slide 6: Operational Concerns — {count} items",
          "Slide 7: Rollout Plan — {count} phases",
          "Slide 8: Q&A and Next Steps"]

    10. Return a SystemDesignOutline.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 3: Demo Script Timer
#
# READ FIRST:
#   02-mock-scenarios-and-system-design.md
#     -> "Demo Interview Preparation" -> "Building a Narrative Arc" — the
#        five-part structure (hook, context, walkthrough, wow, close).
#     -> "Mock Demo Rubric" — scoring dimensions for a demo.
#
# ALSO SEE:
#   examples.py
#     -> Section 3 "Demo Script Template" — DemoScript with timing
#        validation, structure checking, and audience notes.
#
# You provide a demo script as a list of DemoSegment objects. The system
# validates timing, checks for structural completeness, and returns a
# detailed evaluation.
#
# Key concepts: demo narrative arc, time management, opening/closing
# structure, wow moment, transition phrases.
# ============================================================================

def exercise_3_demo_script_timer(
    segments: list[DemoSegment],
    target_duration_seconds: int = 1200,  # 20 minutes default
) -> DemoEvaluation:
    """Evaluate a demo script for timing and structural completeness.

    TODO: Implement this function.

    Steps:
    1. Compute total_duration_seconds = sum of all segment durations.

    2. Check for opening:
       - has_opening = True if first segment topic contains "hook",
         "opening", "intro", or "context" (case-insensitive)

    3. Check for close:
       - has_close = True if last segment topic contains "close",
         "next step", "summary", "wrap", or "recap" (case-insensitive)

    4. Check for wow moment:
       - has_wow_moment = True if any segment topic contains "wow",
         "surprise", "aha", or "unexpected" (case-insensitive)

    5. Generate timing_feedback:
       - If total < target * 0.8: "Under time. You have {X} seconds to
         fill. Consider adding depth to your main segment."
       - If total > target * 1.1: "Over time by {X} seconds. Cut your
         least impactful segment or reduce your middle section."
       - Otherwise: "Good timing. {X} seconds within target."

    6. Generate structure_feedback (list of strings):
       - If no opening: "Missing opening hook. Start with a customer-
         relevant provocative statement."
       - If no close: "Missing close. End with a recap of value and a
         concrete next step."
       - If no wow moment: "No wow moment identified. Add a segment that
         shows something the customer cannot do today."
       - For any segment with 0 key_points: "Segment '{topic}' has no
         key points. Add 2-3 bullet points."
       - For any segment without a transition_phrase (and not the last):
         "Segment '{topic}' has no transition phrase."

    7. Generate missing_elements from structure_feedback.

    8. Build timed_runsheet: list of dicts, each with:
       {"segment": topic, "start_time": cumulative start in "M:SS" format,
        "duration": duration in seconds, "key_points": key_points}

    9. Compute overall_score (0-10):
       - Start at 5
       - +1 for has_opening, +1 for has_close, +1 for has_wow_moment
       - +1 if total_duration within 10% of target
       - +1 if all segments have key_points
       - -1 for each missing structural element (max -3)
       - Clamp to 0-10

    10. Return a DemoEvaluation.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 4: Take-Home POC Evaluator
#
# READ FIRST:
#   03-take-home-pocs-and-behavioral-prep.md
#     -> "Evaluation Criteria (What Actually Gets Scored)" — the weighted
#        rubric (functionality 25%, code quality 20%, documentation 20%,
#        architecture 15%, presentation 15%, polish 5%).
#     -> "What Differentiates Great from Mediocre" — the comparison table.
#
# ALSO SEE:
#   examples.py
#     -> Section 5 "POC Rubric" — POCRubric with score_submission(),
#        weighted scoring, grade thresholds, and suggestion generation.
#
# You provide a POCSubmission and the system scores it against the rubric,
# returning per-dimension scores, an overall grade, and improvement
# suggestions.
#
# Key concepts: POC evaluation rubric, weighted scoring, self-assessment,
# documentation quality, architecture documentation.
# ============================================================================

def exercise_4_poc_evaluator(
    submission: POCSubmission,
) -> POCEvaluation:
    """Evaluate a take-home POC submission against the SE rubric.

    TODO: Implement this function.

    Steps:
    1. Score functionality (0-10):
       - Start at 0
       - +4 if has_working_demo
       - +3 if has_setup_instructions
       - +2 if test_coverage >= 0.3
       - +1 if test_coverage >= 0.7

    2. Score code quality (0-10):
       - Use the provided code_quality_score directly (it is a 0-10 value
         from the submission).

    3. Score documentation (0-10):
       - Start at 0
       - +3 if has_readme
       - +2 if has_architecture_diagram
       - +2 if has_limitations_section
       - +2 if has_setup_instructions
       - +1 if documentation_quality >= 7

    4. Score architecture (0-10):
       - Start at 0
       - +4 if has_architecture_diagram
       - +3 if len(languages_used) >= 1 (demonstrates technology choices)
       - +2 if has_limitations_section (shows architectural awareness)
       - +1 if lines_of_code > 100 (non-trivial implementation)

    5. Score presentation (0-10):
       - Use presentation_quality directly.

    6. Score polish (0-10):
       - Start at 5 (baseline)
       - +2 if has_working_demo and has_readme and has_setup_instructions
       - +2 if test_coverage > 0.5 and has_limitations_section
       - +1 if documentation_quality >= 8
       - Clamp to 0-10

    7. Compute overall_score using weights:
       overall = (functionality * 0.25 + code_quality * 0.20 +
                  documentation * 0.20 + architecture * 0.15 +
                  presentation * 0.15 + polish * 0.05)

    8. Assign grade:
       - >= 8.0: "Strong Hire"
       - >= 6.5: "Hire"
       - >= 4.5: "Needs Work"
       - < 4.5: "No Hire"

    9. Generate improvement_suggestions:
       - For each dimension scoring below 6, add a specific suggestion.
       - Examples: "Add a README with setup instructions and architecture
         diagram", "Improve test coverage — aim for at least 50%", etc.

    10. Return a POCEvaluation.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 5: Behavioral Story Formatter
#
# READ FIRST:
#   01-se-fde-interview-formats-and-fundamentals.md
#     -> "STAR+I Format" — the five elements and time allocation.
#     -> "Building Your Story Bank" — the story bank template.
#   03-take-home-pocs-and-behavioral-prep.md
#     -> "The SE Story Bank — 8 Story Templates" — story templates
#        with category mappings.
#
# ALSO SEE:
#   examples.py
#     -> Section 4 "STAR Story Formatter" — STARIFormatter with
#        parse_story(), detect elements, and completeness scoring.
#
# You provide a raw (unstructured) story and a question category. The
# system parses it into STAR+I format, validates completeness, and
# provides feedback.
#
# Key concepts: STAR+I structure, behavioral interview format, story
# completeness, SE-specific categories.
# ============================================================================

def exercise_5_story_formatter(
    raw_story: str,
    question_category: str,
) -> FormattedStory:
    """Parse a raw story into STAR+I format and validate completeness.

    TODO: Implement this function.

    Steps:
    1. Parse the raw_story to extract STAR+I elements. Look for markers
       in the text:
       - Situation: text following "situation:", "context:", "background:",
         or the first 1-2 sentences if no markers found.
       - Task: text following "task:", "responsibility:", "my role:",
         "i was responsible for", "i needed to".
       - Action: text following "action:", "i did:", "steps:", "what i did:",
         or sentences containing "i [verb]" patterns.
       - Result: text following "result:", "outcome:", "the result was",
         or sentences with numbers, percentages, dollar signs.
       - Impact: text following "impact:", "customer impact:", "the customer",
         or sentences mentioning customer, client, user benefit.

       For each element, extract the relevant text. If a marker is not
       found, assign an empty string and mark it as missing.

    2. Validate completeness:
       - Each non-empty element scores 2 points (max 10).
       - Situation should set context (check for words like "at", "when",
         "while", "during").
       - Action should be first-person (contains "I").
       - Result should have numbers (contains a digit).
       - Impact should mention customer/client/user.

    3. Generate feedback:
       - For each missing element: "Missing {element}. Add a section
         describing {what it should contain}."
       - For Action without "I": "Make actions first-person. Use 'I did X'
         not 'the team did X'."
       - For Result without numbers: "Quantify your result. Add specific
         numbers, percentages, or dollar amounts."
       - For Impact without customer reference: "Add customer impact. How
         did this help the customer specifically?"
       - If question_category not in standard SE categories, note it.

    4. Return a FormattedStory.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ============================================================================
# EXERCISE 6: Interview Readiness Scorer
#
# READ FIRST:
#   01-se-fde-interview-formats-and-fundamentals.md
#     -> "Common Interview Formats" — the full list of formats you need
#        to prepare for.
#     -> "Building Your Story Bank" -> "Story Coverage Check" — minimum
#        coverage targets.
#   03-take-home-pocs-and-behavioral-prep.md
#     -> "Comprehensive Behavioral Preparation" — the full preparation
#        framework.
#     -> "Timed Interview Practice" — the exercises you should complete.
#
# ALSO SEE:
#   examples.py
#     -> Section 5 "POC Rubric" — for the scoring pattern used across
#        multiple dimensions with grade thresholds.
#
# You provide preparation data and the system scores your overall
# readiness, identifies weak areas, and generates a study plan.
#
# Key concepts: preparation coverage, weak-area identification,
# study plan generation, readiness thresholds.
# ============================================================================

def exercise_6_readiness_scorer(
    stories_prepared: int,
    mock_calls_completed: int,
    system_designs_practiced: int,
    pocs_built: int,
    demos_practiced: int,
    behavioral_questions_rehearsed: int,
    coding_challenges_completed: int,
) -> ReadinessScore:
    """Score overall interview readiness and generate a study plan.

    TODO: Implement this function.

    Steps:
    1. Score stories (0-10):
       - 0 stories: 0
       - 1-3: 3
       - 4-5: 5
       - 6-7: 7
       - 8+: 10

    2. Score mock calls (0-10):
       - 0: 0
       - 1: 3
       - 2-3: 6
       - 4-5: 8
       - 6+: 10

    3. Score system design (0-10):
       - 0: 0
       - 1: 4
       - 2: 6
       - 3: 8
       - 4+: 10

    4. Score POC (0-10):
       - 0: 0
       - 1: 6
       - 2+: 10

    5. Score behavioral (0-10):
       - Combine: behavioral_questions_rehearsed + demos_practiced
       - 0: 0
       - 1-5: 3
       - 6-10: 5
       - 11-15: 7
       - 16-20: 8
       - 21+: 10

    6. Compute overall_score = weighted average:
       stories * 0.20 + mock_calls * 0.25 + system_design * 0.20 +
       poc * 0.15 + behavioral * 0.20

    7. Assign overall_grade:
       - >= 8.0: "Ready"
       - >= 6.0: "Almost Ready"
       - >= 4.0: "Needs Work"
       - < 4.0: "Not Ready"

    8. Identify weak_areas: any dimension scoring below 5.

    9. Generate study_plan: for each weak area, provide a specific
       recommendation:
       - Low stories: "Build your story bank to at least 6-8 stories
         covering all SE behavioral categories."
       - Low mock calls: "Schedule at least 3 more mock discovery calls.
         Use the scenarios in 02-mock-scenarios-and-system-design.md."
       - Low system design: "Practice 2-3 more system designs using the
         SE framework in 02-mock-scenarios-and-system-design.md."
       - Low POC: "Build at least one take-home POC. Use the practice
         POC prompts in 03-take-home-pocs-and-behavioral-prep.md."
       - Low behavioral: "Rehearse 10+ behavioral questions and practice
         3+ demos. Use the question bank in 01-se-fde-interview-formats-
         and-fundamentals.md."
       Also add coding_challenges_completed to the plan if < 3:
         "Complete at least 3 coding challenges to build confidence."

    10. Return a ReadinessScore.
    """
    raise NotImplementedError("TODO: Implement this function.")


# ===========================================================================
# Test Functions
# ===========================================================================

def test_exercise_1():
    """Test the discovery call simulator."""
    print("Testing Exercise 1: Discovery Call Simulator")

    prospect = Prospect(
        name="Rachel Kim",
        role="VP of Data Engineering",
        company="Meridian Financial",
        industry="Financial Services",
        company_size=2500,
        current_stack=["Hadoop", "Oracle", "Tableau", "Java ETL"],
        stated_need="Modernize data platform and move to the cloud",
        actual_pains=[
            "Hadoop maintenance burden — 60% of team time",
            "Reports are 48 hours stale",
            "No data lineage for SOX compliance",
            "Original engineers have left",
        ],
        hidden_needs=[
            "Rachel needs to show board progress by Q3",
            "CTO is skeptical of cloud after a failed migration",
        ],
        stakeholders={
            "CTO": "Budget holder, skeptical of cloud",
            "Head of Compliance": "Needs SOX audit trail",
            "Lead Data Engineer": "Day-to-day evaluator",
        },
        objections=["Competitor pricing is usage-based and hard to predict"],
        budget="$500K Year 1",
        timeline="Board review in Q3 (5 months)",
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
        "If this migration succeeds, what does great look like in 12 months?",
    ]

    next_step = "I'd like to schedule a tailored demo next Tuesday focused on data lineage and schema evolution, and include your CTO."

    score = exercise_1_discovery_call_simulator(prospect, questions, next_step)

    assert isinstance(score, DiscoveryCallScore), "Should return DiscoveryCallScore"
    assert 0 <= score.pain_identification_score <= 10
    assert 0 <= score.question_quality_score <= 10
    assert 0 <= score.stakeholder_mapping_score <= 10
    assert 0 <= score.next_steps_score <= 10
    assert 0 <= score.open_vs_closed_ratio <= 1.0
    assert score.total_score == (
        score.pain_identification_score + score.question_quality_score +
        score.stakeholder_mapping_score + score.next_steps_score
    )
    assert len(score.identified_pains) > 0, "Should identify at least some pains"
    print(f"  Pain: {score.pain_identification_score:.1f}/10")
    print(f"  Questions: {score.question_quality_score:.1f}/10")
    print(f"  Stakeholders: {score.stakeholder_mapping_score:.1f}/10")
    print(f"  Next Steps: {score.next_steps_score:.1f}/10")
    print(f"  Total: {score.total_score:.1f}/40")
    print(f"  Open/Closed ratio: {score.open_vs_closed_ratio:.2f}")
    print("  PASSED\n")


def test_exercise_2():
    """Test the system design skeleton builder."""
    print("Testing Exercise 2: System Design Skeleton Builder")

    result = exercise_2_system_design_builder(
        customer_profile="Professional services firm, 5000 employees, SOC 2 required",
        business_problem="Employees waste 6 hours/week searching for internal information. Cost: $23M/year in lost productivity.",
        success_metrics=[
            "Reduce average search time by 50%",
            "70% user adoption within 6 months",
            "Answer relevance score > 80%",
        ],
        architecture_components=[
            "Existing SharePoint document store (data source)",
            "Document ingestion pipeline (parse, chunk, embed)",
            "Vector database (Pinecone)",
            "RAG query service",
            "Slack bot interface",
            "Okta SSO integration (existing)",
        ],
        integration_points=[
            {"system": "SharePoint", "protocol": "Microsoft Graph API", "auth": "OAuth 2.0", "notes": "Delta sync every 4 hours"},
            {"system": "Okta SSO", "protocol": "OIDC", "auth": "Standard Okta", "notes": "Permission sync for document access"},
            {"system": "Slack", "protocol": "Slack Bot API", "auth": "Bot token", "notes": "Handle threading and rate limits"},
        ],
        operational_concerns=[
            "Monitoring: query latency, answer quality scores, cost per query",
            "Security: TLS 1.3 in transit, AES-256 at rest, SOC 2 compliance",
            "Scaling: vector DB scales horizontally, LLM rate limits managed with queue",
            "Support: dedicated Slack channel for user issues, weekly quality review",
        ],
        rollout_phases=[
            {"name": "Phase 1: Foundation", "duration": "Weeks 1-4", "milestone": "100 beta users, 80% answer relevance"},
            {"name": "Phase 2: Expand", "duration": "Weeks 5-8", "milestone": "1000 users, Slack bot live"},
            {"name": "Phase 3: Full Rollout", "duration": "Weeks 9-16", "milestone": "5000 users, 50% search time reduction"},
        ],
    )

    assert isinstance(result, SystemDesignOutline), "Should return SystemDesignOutline"
    assert result.completeness_score >= 0
    assert len(result.presentation_outline) >= 7, "Should have at least 7 slides"
    print(f"  Completeness: {result.completeness_score:.1f}/10")
    print(f"  Missing: {result.missing_elements or 'None'}")
    print(f"  Presentation slides: {len(result.presentation_outline)}")
    print("  PASSED\n")


def test_exercise_3():
    """Test the demo script timer."""
    print("Testing Exercise 3: Demo Script Timer")

    segments = [
        DemoSegment(
            topic="Hook / Opening",
            duration_seconds=30,
            key_points=["Provocative stat about search time waste"],
            transition_phrase="Let me show you why this matters for your team...",
        ),
        DemoSegment(
            topic="Context — Customer Problem",
            duration_seconds=120,
            key_points=["Their 3 pain points", "Business impact"],
            transition_phrase="Now let me show you how we address the first pain...",
        ),
        DemoSegment(
            topic="Solution Segment 1 — Natural Language Search",
            duration_seconds=360,
            key_points=["Live query", "Source citations", "Permission-aware results"],
            transition_phrase="That's the search experience. Now let me show you what's happening under the hood...",
        ),
        DemoSegment(
            topic="Solution Segment 2 — Document Ingestion",
            duration_seconds=240,
            key_points=["Auto-sync from SharePoint", "Chunking and embedding"],
            transition_phrase="Now for the part that really sets us apart...",
        ),
        DemoSegment(
            topic="Wow Moment — Live Document Update",
            duration_seconds=120,
            key_points=["Update a doc in SharePoint", "Show it reflected in search within minutes"],
        ),
        DemoSegment(
            topic="Close — Recap and Next Steps",
            duration_seconds=120,
            key_points=["Recap 3 value points", "Propose POC scope", "Suggest next meeting"],
        ),
    ]

    result = exercise_3_demo_script_timer(segments, target_duration_seconds=1020)

    assert isinstance(result, DemoEvaluation), "Should return DemoEvaluation"
    assert result.has_opening is True, "Should detect opening"
    assert result.has_close is True, "Should detect close"
    assert result.has_wow_moment is True, "Should detect wow moment"
    assert result.segment_count == 6
    assert len(result.timed_runsheet) == 6
    assert 0 <= result.overall_score <= 10
    print(f"  Total duration: {result.total_duration_seconds}s ({result.total_duration_seconds // 60}m {result.total_duration_seconds % 60}s)")
    print(f"  Opening: {result.has_opening}, Close: {result.has_close}, Wow: {result.has_wow_moment}")
    print(f"  Score: {result.overall_score:.1f}/10")
    print(f"  Timing: {result.timing_feedback}")
    print("  PASSED\n")


def test_exercise_4():
    """Test the POC evaluator."""
    print("Testing Exercise 4: Take-Home POC Evaluator")

    submission = POCSubmission(
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
    )

    result = exercise_4_poc_evaluator(submission)

    assert isinstance(result, POCEvaluation), "Should return POCEvaluation"
    assert 0 <= result.overall_score <= 10
    assert result.grade in ("Strong Hire", "Hire", "Needs Work", "No Hire")
    print(f"  Functionality: {result.functionality_score:.1f}/10")
    print(f"  Code Quality: {result.code_quality_score:.1f}/10")
    print(f"  Documentation: {result.documentation_score:.1f}/10")
    print(f"  Architecture: {result.architecture_score:.1f}/10")
    print(f"  Presentation: {result.presentation_score:.1f}/10")
    print(f"  Polish: {result.polish_score:.1f}/10")
    print(f"  Overall: {result.overall_score:.1f}/10 — {result.grade}")
    if result.improvement_suggestions:
        print(f"  Suggestions: {len(result.improvement_suggestions)}")
    print("  PASSED\n")


def test_exercise_5():
    """Test the behavioral story formatter."""
    print("Testing Exercise 5: Behavioral Story Formatter")

    raw_story = """
    Situation: I was supporting a $200K deal with a logistics company.
    We were in the POC phase with a 2-week deadline.

    Task: I was responsible for delivering a working integration between
    our platform and their Warehouse Management System.

    Action: Three days before the deadline, the integration broke due to
    an API version mismatch. I diagnosed the root cause within 2 hours,
    coordinated with our product team for an emergency patch, and built
    a temporary workaround using the older API version. I also called
    the customer's lead engineer directly to explain the situation and
    set expectations transparently.

    Result: We delivered the POC on time. The customer signed the deal
    for $200K ARR within 3 weeks of POC completion.

    Impact: The customer was able to launch their real-time tracking
    feature 2 months ahead of schedule because our integration was solid.
    """

    result = exercise_5_story_formatter(raw_story, "Problem-Solving")

    assert isinstance(result, FormattedStory), "Should return FormattedStory"
    assert len(result.situation) > 0, "Should extract situation"
    assert len(result.task) > 0, "Should extract task"
    assert len(result.action) > 0, "Should extract action"
    assert len(result.result) > 0, "Should extract result"
    assert len(result.impact) > 0, "Should extract impact"
    assert result.question_category == "Problem-Solving"
    assert 0 <= result.completeness_score <= 10
    print(f"  Situation: {result.situation[:60]}...")
    print(f"  Task: {result.task[:60]}...")
    print(f"  Action: {result.action[:60]}...")
    print(f"  Result: {result.result[:60]}...")
    print(f"  Impact: {result.impact[:60]}...")
    print(f"  Completeness: {result.completeness_score:.1f}/10")
    if result.missing_elements:
        print(f"  Missing: {result.missing_elements}")
    print("  PASSED\n")


def test_exercise_6():
    """Test the interview readiness scorer."""
    print("Testing Exercise 6: Interview Readiness Scorer")

    result = exercise_6_readiness_scorer(
        stories_prepared=6,
        mock_calls_completed=3,
        system_designs_practiced=2,
        pocs_built=1,
        demos_practiced=4,
        behavioral_questions_rehearsed=12,
        coding_challenges_completed=2,
    )

    assert isinstance(result, ReadinessScore), "Should return ReadinessScore"
    assert 0 <= result.overall_score <= 10
    assert result.overall_grade in ("Ready", "Almost Ready", "Needs Work", "Not Ready")
    print(f"  Stories: {result.stories_score:.1f}/10")
    print(f"  Mock Calls: {result.mock_calls_score:.1f}/10")
    print(f"  System Design: {result.system_design_score:.1f}/10")
    print(f"  POC: {result.poc_score:.1f}/10")
    print(f"  Behavioral: {result.behavioral_score:.1f}/10")
    print(f"  Overall: {result.overall_score:.1f}/10 — {result.overall_grade}")
    if result.weak_areas:
        print(f"  Weak areas: {result.weak_areas}")
    if result.study_plan:
        print(f"  Study plan items: {len(result.study_plan)}")
    print("  PASSED\n")


# ===========================================================================
# Run all tests
# ===========================================================================

def run_all_tests():
    """Run all exercise tests. Exercises that are not implemented will fail
    with NotImplementedError -- that is expected until you complete them."""

    exercises = [
        ("Exercise 1: Discovery Call Simulator", test_exercise_1),
        ("Exercise 2: System Design Skeleton Builder", test_exercise_2),
        ("Exercise 3: Demo Script Timer", test_exercise_3),
        ("Exercise 4: Take-Home POC Evaluator", test_exercise_4),
        ("Exercise 5: Behavioral Story Formatter", test_exercise_5),
        ("Exercise 6: Interview Readiness Scorer", test_exercise_6),
    ]

    results: list[tuple[str, str]] = []

    for name, test_fn in exercises:
        try:
            test_fn()
            results.append((name, "PASSED"))
        except NotImplementedError:
            results.append((name, "NOT IMPLEMENTED"))
            print(f"  {name}: Not yet implemented\n")
        except AssertionError as e:
            results.append((name, f"FAILED: {e}"))
            print(f"  {name}: FAILED - {e}\n")
        except Exception as e:
            results.append((name, f"ERROR: {e}"))
            print(f"  {name}: ERROR - {e}\n")

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    for name, status in results:
        print(f"  {status:20s}  {name}")


if __name__ == "__main__":
    run_all_tests()
