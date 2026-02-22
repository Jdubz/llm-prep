# Module 03 Deep Dive: Technical Communication — Advanced Topics

## Overview

This deep dive extends beyond interview-specific communication into the broader technical communication skills that define staff-level engineers: writing design documents and RFCs, technical writing for visibility, influencing technical decisions, giving effective code reviews, and presenting to leadership. These skills are directly evaluated in staff-level interviews and are the daily work of the role.

---

## Table of Contents

1. [RFC and Design Doc Writing](#rfc-and-design-doc-writing)
2. [Technical Writing for Visibility](#technical-writing-for-visibility)
3. [Influencing Technical Decisions](#influencing-technical-decisions)
4. [Giving Effective Code Reviews](#giving-effective-code-reviews)
5. [Presenting to Leadership](#presenting-to-leadership)

---

## RFC and Design Doc Writing

Design documents (often called RFCs — Request for Comments) are the primary medium through which staff engineers drive technical direction. Many companies ask candidates to write or discuss design docs as part of the interview process.

### Why Design Docs Matter

- They force clear thinking before writing code
- They create a record of decisions and rationale
- They enable asynchronous feedback from a wide audience
- They reduce the cost of mistakes by catching issues early
- They are a primary output of staff-level work

### Standard Design Doc Structure

```
Title: [Descriptive title]
Author: [Your name]
Date: [Creation date]
Status: [Draft / In Review / Approved / Implemented / Deprecated]
Reviewers: [Names of required reviewers]

## Context and Problem Statement
What is the problem? Why does it need to be solved now?
What is the business or technical motivation?
Include data, metrics, or incidents that illustrate the problem.

## Goals and Non-Goals
Goals: What this design WILL accomplish (specific and measurable)
Non-goals: What this design will NOT address (equally important for scope clarity)

## Proposed Solution
High-level description of the approach.
Architecture diagram.
Key components and their responsibilities.
Data model changes.
API changes.

## Alternatives Considered
Option A: [Description, pros, cons]
Option B: [Description, pros, cons]
Option C: [Description, pros, cons]
Why the proposed solution is preferred over alternatives.

## Detailed Design
Component-level descriptions.
Sequence diagrams for key flows.
Data schema definitions.
API specifications.
Error handling and edge cases.

## Security and Privacy Considerations
Authentication and authorization changes.
Data handling and PII implications.
Threat model (if applicable).

## Operational Considerations
Deployment plan (phased rollout, feature flags, canary).
Monitoring and alerting.
Rollback strategy.
Performance implications.
On-call impact.

## Migration Plan
How to move from current state to desired state.
Backward compatibility.
Data migration strategy.
Timeline and milestones.

## Open Questions
Unresolved decisions that need input.
Areas of uncertainty.
Dependencies on other teams.

## Decision Record
[Updated after review]
Key decisions made during the review process.
Rationale for each decision.
```

### Writing Tips for Design Docs

**Lead with the "why," not the "what."** Before describing your solution, ensure the reader deeply understands the problem. A well-understood problem makes your solution feel inevitable.

**Be explicit about what you are NOT doing.** Non-goals prevent scope creep during review and set clear expectations. "This design does not address multi-region support; that will be a separate effort" is clearer than hoping no one asks.

**Present alternatives honestly.** Do not set up straw-man alternatives to make your preferred solution look good. Reviewers see through this, and it undermines trust. Present genuine alternatives with honest trade-offs, then explain your reasoning for the preferred approach.

**Use diagrams.** A well-drawn architecture diagram communicates more than paragraphs of text. Include sequence diagrams for complex flows.

**Write for skimming.** Use headers, bullet points, tables, and bold text. Most reviewers will skim before (if ever) reading in detail. Make it easy to extract the key points quickly.

**Include operational details.** Junior engineers write docs about what to build. Staff engineers write docs about how to build it, deploy it, operate it, and recover from it.

### Design Docs in Interviews

Some companies ask you to write a mini design doc as part of the interview process. Others ask you to describe your design doc process. In either case:

- Demonstrate that you have a structured approach
- Show that you think about alternatives, trade-offs, and operations
- Emphasize the collaborative nature of the process (seeking input, incorporating feedback)
- Reference specific examples from your experience ("At my current company, I wrote a design doc for X that required input from three teams...")

### Decision Records

A subtle but powerful practice: after the design review, update the document with a "Decision Record" section that captures:
- What was decided
- Why it was decided (rationale)
- What alternatives were rejected and why
- Who was involved in the decision

This creates institutional memory that pays dividends months or years later when someone asks "Why did we build it this way?"

---

## Technical Writing for Visibility

Staff engineers write more than code. The written artifacts you produce create visibility, build your reputation, and influence the organization.

### Blog Posts (Internal and External)

**Internal blog posts / knowledge sharing:**
- Post-mortems and incident analyses
- Technology evaluations and recommendations
- Architecture decision records
- "How we built X" articles
- Best practices and guidelines

**External blog posts (engineering blog, personal blog):**
- Build your professional reputation
- Attract talent to your company
- Demonstrate thought leadership
- Create interview talking points

**Writing tips:**
- Start with the conclusion or key insight (inverted pyramid)
- Use concrete examples, not abstract principles
- Include code snippets, diagrams, and data
- Target a specific audience and write for their level
- Have a peer review before publishing

### Post-Mortems

Post-mortems (or incident retrospectives) are one of the most important forms of technical writing. They are also frequently discussed in interviews.

**Structure:**
```
## Incident Summary
What happened, when, and what was the impact.

## Timeline
Chronological account of events, from detection to resolution.

## Root Cause
The underlying technical or process failure.

## Contributing Factors
Additional factors that made the incident worse or more likely.

## Impact
Quantified: duration, users affected, revenue impact, SLA violation.

## Resolution
How the incident was resolved.

## Action Items
Preventive measures with owners and deadlines.

## Lessons Learned
What this incident taught us about our systems and processes.
```

**Post-mortem principles:**
- Blameless: Focus on systems and processes, not individuals
- Thorough: Identify root cause, not just proximate cause
- Actionable: Every finding should have a concrete action item
- Shared: Publish widely to spread the learning

### Documentation That Matters

Not all documentation is equally valuable. Focus your writing energy on:

| High value | Low value |
|------------|-----------|
| Architecture decision records | Auto-generated API docs |
| Onboarding guides | Meeting notes (unless decisions were made) |
| Operational runbooks | Status updates (automate these) |
| Post-mortems | Documentation of obvious code |
| Design docs | Internal wikis that no one reads |

---

## Influencing Technical Decisions

At the staff level, you rarely have the authority to make unilateral technical decisions. Your influence comes from persuasion, data, and trust.

### Building Consensus

**Step 1: Understand the stakeholders.** Who has opinions on this decision? Who will be affected? Who has veto power?

**Step 2: Gather input early.** Before writing your proposal, have informal conversations with key stakeholders. Understand their concerns and constraints. Incorporate their input. This prevents surprises during the formal review.

**Step 3: Present options, not conclusions.** Frame your recommendation as one option among several. This invites collaboration rather than triggering resistance.

**Step 4: Use data, not opinions.** "Our benchmark shows 40% latency improvement with Option B" is more persuasive than "I think Option B is faster."

**Step 5: Address objections proactively.** If you know someone will object to your approach, address their likely concern in your proposal before they raise it.

**Step 6: Make the decision process transparent.** Document who was consulted, what options were considered, and how the decision was made.

### Presenting Options

The most effective way to present a technical decision is with a structured comparison:

```
                    Option A          Option B          Option C
Complexity          Low               Medium            High
Performance         Good              Best              Good
Team familiarity    High              Low               Medium
Migration effort    2 weeks           6 weeks           4 weeks
Long-term fit       Medium            High              High
Risk                Low               Medium            Low

Recommendation: Option B
Rationale: While the migration effort is higher, the performance
improvement and long-term fit justify the investment. We can
mitigate the team familiarity risk with a two-week spike.
```

### Managing Disagreement

When people disagree on technical direction:

1. **Separate opinions from data.** "I prefer X" is opinion. "X handles 10x more throughput in our benchmark" is data. Push the conversation toward data.

2. **Identify the root of disagreement.** Often people agree on goals but disagree on how to achieve them. Clarifying shared goals redirects the conversation productively.

3. **Propose experiments.** "We can't resolve this with discussion alone. Let me build a prototype of both approaches in a one-week spike and we'll compare."

4. **Know when to escalate.** If consensus cannot be reached after genuine effort, escalate to a decision-maker. Frame it as "We have two good options and need someone to make the call" rather than "I'm right and they're wrong."

5. **Commit once decided.** Even if the decision goes against your recommendation, commit fully. Passive resistance undermines trust and the team.

### Common Influence Anti-Patterns

- **The ambush:** Presenting a fully baked decision in a meeting with no prior discussion. People resist decisions they were not part of.
- **The appeal to authority:** "The VP wants this." Even if true, it does not build genuine buy-in.
- **The fait accompli:** Building something without approval and then asking for forgiveness. Works once, destroys trust.
- **The false consensus:** "Everyone agrees" when you only asked people who you knew would agree.
- **The analysis paralysis:** Requesting more data indefinitely to avoid making a decision.

---

## Giving Effective Code Reviews

Code review is a core communication skill for senior/staff engineers. It is also a common topic in behavioral interviews ("What is your code review philosophy?").

### The Purpose of Code Review

Code review serves multiple purposes, in order of importance:
1. **Knowledge sharing:** Spreading understanding of the codebase
2. **Catching design issues:** Identifying architectural problems before they are cemented
3. **Teaching:** Helping engineers grow through constructive feedback
4. **Bug detection:** Finding bugs (actually a secondary benefit; tests are better for this)
5. **Consistency:** Maintaining code style and conventions

### Tone

Tone in code reviews matters enormously. Written feedback lacks the warmth of face-to-face conversation and is easily misread as harsh.

**Instead of:** "This is wrong."
**Write:** "I think there might be an issue here. If `input` is null, this will throw a NullPointerException. Could we add a null check?"

**Instead of:** "Why didn't you use X?"
**Write:** "Have you considered using X here? It might simplify this logic because [reason]."

**Instead of:** "This is confusing."
**Write:** "I had trouble following the logic in this function. Would it help to extract the validation step into a separate method with a descriptive name?"

### Specificity

Vague feedback is not actionable and often frustrating:

**Vague:** "This could be improved."
**Specific:** "This function is doing three things: validation, transformation, and persistence. Extracting each into its own method would improve testability and readability."

**Vague:** "This doesn't feel right."
**Specific:** "I'm concerned about the coupling between the UserService and the NotificationService here. If we add an event-based approach, the UserService wouldn't need to know about notifications."

### Teaching Moments

The best code reviews teach without condescending:

> "This is a great opportunity to use the builder pattern here. It would let us construct this object step by step and make the code more readable. Here's a link to the pattern: [URL]. Happy to pair on this if you'd like."

> "I noticed you're iterating through the list twice here — once to filter and once to map. You could use a single stream pipeline to do both in one pass. This is a common pattern in our codebase; here's an example: [link]."

### What to Focus On

| Focus heavily on | Focus lightly on |
|------------------|-----------------|
| Correctness and logic errors | Naming preferences (unless truly confusing) |
| Design and architecture | Formatting (automate this with linters) |
| Edge cases and error handling | Style nitpicks |
| Security implications | Personal preferences without clear benefit |
| Performance issues with real impact | Micro-optimizations |
| Test coverage and quality | Comment density |

### Code Review in Interviews

When asked about your code review philosophy:
- Emphasize that it is about learning and quality, not gatekeeping
- Describe how you balance thoroughness with speed
- Give an example of a code review that caught a significant issue
- Give an example of how you gave feedback that helped someone grow
- Mention automation (linting, formatting, CI checks) to focus human review on what matters

---

## Presenting to Leadership

Staff engineers regularly present to directors, VPs, and C-suite executives. This skill is evaluated in interviews, especially for staff and principal roles.

### Executive Summary First

Leaders have limited time and many demands on their attention. Lead with the conclusion.

**Instead of:** Starting with the technical context, then the problem, then the options, then the recommendation.

**Start with:** "We recommend investing 3 engineer-months in migrating to service X, which will reduce our infrastructure costs by 40% and eliminate a class of incidents that cost us $200K last quarter. Here's the summary..."

Then provide supporting detail for those who want to go deeper.

### Business Impact Framing

Translate technical decisions into business terms:

| Technical framing | Business framing |
|-------------------|-------------------|
| "We need to refactor the database layer" | "We can reduce page load times by 50%, which our data shows will increase conversion by 8%" |
| "Our monolith is hard to maintain" | "Feature delivery time has tripled in 2 years, and we're losing competitive ground" |
| "We should adopt Kubernetes" | "We can reduce infrastructure costs by 30% and deploy 10x faster" |
| "We have too much technical debt" | "Each new feature takes 40% longer than it should, and incidents are up 200% year-over-year" |

### Structure for Leadership Presentations

```
1. The Opportunity / Problem (1 minute)
   - Business impact, quantified
   - Why it matters NOW

2. The Recommendation (1 minute)
   - What you propose
   - Expected outcome (quantified)
   - Timeline and cost

3. The Evidence (2-3 minutes)
   - Data supporting the recommendation
   - Alternatives considered (briefly)
   - Risk assessment

4. The Ask (30 seconds)
   - What you need (budget, headcount, priority)
   - Decision needed

5. Q&A (remainder)
   - Be prepared for: "What if we do nothing?"
   - Be prepared for: "What are the risks?"
   - Be prepared for: "Can we do it faster/cheaper?"
```

### Common Mistakes Presenting to Leadership

- **Too much technical detail.** They do not need to know about your caching strategy. They need to know the business outcome.
- **No clear ask.** Every presentation to leadership should end with a specific request or decision needed.
- **Burying the lead.** If the recommendation is on slide 15 of 20, you have lost your audience.
- **Not anticipating questions.** Think about what a skeptical VP would ask and prepare answers.
- **Showing all your work.** Keep the main presentation tight. Put supporting detail in an appendix.

### Handling Pushback from Leadership

- **"Can we do it cheaper?"** — Have a phased plan ready that shows a smaller initial investment with option to expand.
- **"What's the risk?"** — Be honest about risks with mitigation strategies. Leaders respect honesty more than unrealistic optimism.
- **"Why not just [simpler alternative]?"** — Acknowledge the appeal of the simpler option, then explain why it does not fully address the problem with specific data.
- **"We tried this before and it failed."** — Understand the history, acknowledge it, and explain what is different now.

### In Interviews

When asked about presenting to leadership:
- Describe a specific instance where you influenced a technical decision at the organizational level
- Emphasize how you translated technical concepts into business value
- Show that you tailor your communication to the audience
- Demonstrate that you can handle tough questions without getting defensive
- Mention the outcome: "The VP approved the project, and we delivered [result]"
