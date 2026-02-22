# Module 03 Cheat Sheet: Technical Communication

## Explanation Framework Template

### The Three-Layer Approach

```
Layer 1 — THE ANALOGY (10 seconds)
  "It's like [familiar concept]. [One sentence mapping]."

Layer 2 — THE MODEL (30 seconds)
  "At a high level, [system/feature] does [what].
   [Input] goes in, [process] happens, [output] comes out.
   The key components are [A], [B], and [C]."

Layer 3 — THE DETAIL (as needed)
  "Specifically, [A] works by [technical detail].
   We chose [technology] because [trade-off reasoning].
   The interesting challenge was [specific problem]
   which we solved by [approach]."
```

**Rule:** Start at Layer 1. Only go deeper when the listener signals they want more detail.

### Quick Analogy Reference

| Concept | Analogy |
|---------|---------|
| Load balancer | Restaurant host seating guests at available tables |
| Cache | Sticky note with frequently used info on your desk |
| Message queue | Bakery ticket line — orders wait to be filled in order |
| Database index | Index at the back of a textbook |
| API gateway | Hotel front desk routing you to the right department |
| Circuit breaker | Electrical fuse protecting your house from a surge |
| Eventual consistency | Memo taking time to reach all offices in a building |
| Rate limiting | Bouncer controlling how many people enter a club per minute |
| Sharding | Splitting a phone book into A-M and N-Z volumes |
| Pub/sub | Newsletter subscription — publishers send, subscribers receive |

---

## Whiteboarding Structure Template

### Step-by-Step Process

```
1. CLARIFY (2-3 minutes)
   - Ask 3-5 clarifying questions
   - State assumptions
   - Confirm scope

2. OUTLINE (1-2 minutes)
   - Verbally describe what you will draw
   - Divide the space into sections
   - Announce: "I'll start with the high-level architecture"

3. HIGH-LEVEL DESIGN (5-8 minutes)
   - Draw 3-5 major components as boxes
   - Connect with labeled arrows
   - Narrate while drawing
   - Check in: "Does this make sense so far?"

4. DEEP DIVE (15-20 minutes)
   - Interviewer picks a component (or you propose one)
   - Add internal detail to that component
   - Discuss data model, algorithms, trade-offs
   - Address failure scenarios

5. TRADE-OFFS AND EXTENSIONS (5-10 minutes)
   - Discuss what you would change at 10x scale
   - Address reliability, consistency, security
   - Mention monitoring and operational concerns
```

### Board Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   REQUIREMENTS          │    HIGH-LEVEL ARCHITECTURE        │
│   (top-left corner)     │    (center, largest section)      │
│                         │                                   │
│   - Functional          │    ┌────┐  ┌────┐  ┌────┐        │
│   - Non-functional      │    │    │──│    │──│    │        │
│   - Assumptions         │    └────┘  └────┘  └────┘        │
│                         │                                   │
│─────────────────────────│───────────────────────────────────│
│                         │                                   │
│   DEEP DIVE             │    NOTES / TRADE-OFFS             │
│   (bottom-left)         │    (bottom-right)                 │
│                         │                                   │
│   Schema, algorithms,   │    - Scaling considerations       │
│   detailed component    │    - Alternative approaches       │
│                         │    - Open questions                │
│                         │                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Clarifying Questions Checklist

### For System Design Problems

**Functional:**
- [ ] What are the core use cases?
- [ ] Who are the users? (internal, external, both)
- [ ] What are the must-have vs nice-to-have features?
- [ ] What does the data model look like at a high level?

**Scale:**
- [ ] How many users / requests per second?
- [ ] How much data are we storing?
- [ ] What is the read-to-write ratio?
- [ ] Are there traffic spikes to design for?

**Non-Functional:**
- [ ] What latency is acceptable? (P50, P99)
- [ ] What availability target? (99.9%, 99.99%)
- [ ] Consistency vs availability preference?
- [ ] Any regulatory or compliance constraints?

**Scope:**
- [ ] Single region or multi-region?
- [ ] Do I need to handle auth, or assume it exists?
- [ ] Should I design the client, or just the backend?
- [ ] Existing systems to integrate with?

### For Coding Problems

- [ ] What is the input format and range?
- [ ] What should I return?
- [ ] Can the input be empty or null?
- [ ] Are there duplicates? Are they allowed?
- [ ] Should I optimize for time or space?
- [ ] Can I use standard library data structures?

---

## "I Don't Know" Response Templates

### Template 1: Related Knowledge Bridge

```
"I haven't worked with [X] directly, but I've used [Y],
which solves a similar problem. Based on that experience,
I'd expect [X] to work by [reasoning]. The key difference
is probably [informed guess about distinction]."
```

### Template 2: First Principles Reasoning

```
"I'm not familiar with the specifics of [X], but I can
reason about it from first principles. The fundamental
problem it solves is [problem]. To solve that, you'd
need to [approach]. So I'd expect [X] to [reasoning]."
```

### Template 3: Honest Gap with Direction

```
"That's an area I haven't gone deep on yet. What I do
know is [related knowledge]. If I were approaching this
for the first time, I'd start by [concrete first step]."
```

### Template 4: Acknowledging and Redirecting

```
"I don't have hands-on experience with [X]. I'd want to
learn more about it. But I can speak to [related area]
if that would be helpful."
```

**Rule:** Always follow "I don't know" with something. Never end on the gap.

---

## Technical Presentation Outline

### For a 15-Minute Technical Talk

```
Minute 0-1:   HOOK — Start with the problem or result
              "We were losing $50K/month to a single class of incidents."

Minute 1-3:   CONTEXT — Brief background
              Team, product, scale, constraints.

Minute 3-5:   APPROACH — What you chose and why
              High-level architecture. Key trade-offs.

Minute 5-10:  DETAILS — The interesting parts
              Technical challenges. How you solved them.
              Diagrams, code snippets, data.

Minute 10-12: RESULTS — Quantified outcomes
              Metrics, business impact, team impact.

Minute 12-15: LESSONS AND Q&A
              What you learned. What you'd do differently.
              Open for questions.
```

### For Leadership (5 Minutes)

```
Minute 0-1:   RECOMMENDATION — Lead with the ask
              "We should invest X to achieve Y."

Minute 1-3:   EVIDENCE — Why this is the right call
              Data, metrics, business case.

Minute 3-4:   RISK — What could go wrong and mitigation
              Be honest. Have a plan.

Minute 4-5:   ASK — Specific request
              Budget, headcount, priority, decision.
```

---

## Code Walkthrough Framework

### When Explaining Code You Just Wrote

```
Step 1: HIGH LEVEL
  "This function takes [input] and returns [output].
   The approach is [brief description of algorithm/strategy]."

Step 2: KEY LOGIC
  "The main loop [does X]. For each element, we [action].
   The key insight is [why this works]."

Step 3: DECISIONS
  "I chose [data structure/approach] because [trade-off reasoning].
   The time complexity is [X] and space is [Y]."

Step 4: EDGE CASES
  "This handles [edge case] on line [N].
   We'd also want to consider [another edge case]."

Step 5: TESTING
  "If I were writing tests, I'd cover:
   - Empty input
   - Single element
   - [Domain-specific edge case]
   - Maximum size input"
```

### When Explaining a Past Project's Architecture

```
Step 1: WHAT IT DOES
  "The system handles [business function] for [users].
   At peak, it processes [scale metric]."

Step 2: HOW IT IS STRUCTURED
  "The architecture has [N] main components:
   [Component A] handles [responsibility].
   [Component B] handles [responsibility]."
  (Draw or describe the diagram.)

Step 3: KEY DECISIONS
  "We chose [technology] for [component] because [reason].
   We considered [alternative] but rejected it because [reason]."

Step 4: TRADE-OFFS
  "The main trade-off we accepted was [X] in exchange for [Y].
   This was acceptable because [business reasoning]."

Step 5: WHAT I WOULD CHANGE
  "In retrospect, I would [change X] because [lesson learned]."
```
