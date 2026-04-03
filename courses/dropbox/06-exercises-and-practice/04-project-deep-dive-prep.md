# 04 – Project Deep Dive Preparation

The Project Deep Dive is a 1-hour interview in Onsite Loop Set 1. You present a project you owned; interviewers probe deeply. This is where leveling happens — your answers determine IC3 vs IC4 vs IC5.

---

## 1. Choosing Your Project

### Selection Criteria

Pick a project that checks **all** of these:

- [ ] You owned it end-to-end (not a small contribution to someone else's project)
- [ ] It involved meaningful technical trade-offs (not just "implemented the spec")
- [ ] It had measurable impact (metrics, users affected, performance improvement)
- [ ] It's recent (last 2-3 years)
- [ ] It has depth — interviewers with domain expertise will push you
- [ ] It maps to the role: full-stack, AI/ML integration, or search/data

### What Screams Each Level

| Level | Project Signal |
|-------|---------------|
| **IC3** | "I built this feature with clear requirements and shipped it on time" |
| **IC4** | "I identified the problem, designed the solution, led the project through ambiguity, and measured the outcome" |
| **IC5** | "I drove a technical initiative across multiple teams that changed how the org builds software" |

### Red Flags to Avoid

- A project where you can't explain why decisions were made
- A project where you say "we" for everything and "I" for nothing
- A purely backend or purely frontend project (this is a full-stack role)
- A project with no measurable results
- A project that's too confidential to discuss in detail

---

## 2. Presentation Structure (20 minutes)

Practice this structure with a timer. Total presentation: 20 minutes. Remaining 40 minutes: Q&A.

### Part 1: Context (2-3 minutes)

**What to cover:**
- What was the problem? Why did it matter to the business?
- What was the scale? (Users, requests/sec, data volume)
- What was your role? (Lead? Solo? Part of a team of N?)
- What constraints existed? (Timeline, legacy systems, team size)

**Template:**

> "At [company], we had a problem where [specific problem with numbers]. This affected [who] because [why it mattered]. I was the [role] on a team of [N], and I led the [specific scope]. We had [constraints: timeline, legacy, etc.]."

### Exercise: Write your context in 3 sentences.

```
1. The problem: _______________________________________________
2. Why it mattered: ___________________________________________
3. My role and constraints: ____________________________________
```

---

### Part 2: Architecture (5 minutes)

**What to cover:**
- High-level system diagram (draw it)
- Key components and their responsibilities
- How data flows through the system
- Where this fits in the larger product

**Tips:**
- Prepare a diagram you can draw in 2 minutes on a whiteboard
- Label components clearly
- Show the request flow with arrows
- Highlight the parts you owned

### Exercise: Draw your architecture diagram.

Draw it on paper or whiteboard. Can you explain every box and arrow? Can you draw it in 2 minutes flat?

**Practice drill:** Set a 2-minute timer. Draw the diagram. Explain each component in one sentence. Repeat until it's smooth.

---

### Part 3: Technical Deep Dive (10 minutes)

This is where you differentiate yourself. Pick 2-3 of the hardest decisions and go deep.

**For each decision, cover:**

1. **The options you considered** — at least 2 alternatives
2. **The trade-offs** — what each option optimized for and what it sacrificed
3. **Why you chose what you chose** — specific reasoning, not "it felt right"
4. **What happened** — did it work? What surprised you?
5. **What you'd do differently** — shows self-awareness

### Exercise: Fill in for your top 3 decisions.

**Decision 1:** _______________________________________________

| Option | Pros | Cons |
|--------|------|------|
| A: | | |
| B: | | |
| Chose: | Why: | |

**Decision 2:** _______________________________________________

| Option | Pros | Cons |
|--------|------|------|
| A: | | |
| B: | | |
| Chose: | Why: | |

**Decision 3:** _______________________________________________

| Option | Pros | Cons |
|--------|------|------|
| A: | | |
| B: | | |
| Chose: | Why: | |

---

### Part 4: Results & Reflection (2-3 minutes)

**What to cover:**
- Quantified outcomes (latency reduced by X%, user engagement up Y%)
- What you learned
- What you'd do differently with hindsight
- How this connects to what you'd do at Dropbox

**Template:**

> "The result was [specific metrics]. The biggest lesson was [insight]. If I did it again, I'd [change]. This experience is directly relevant to Dash because [connection]."

### Exercise: Write your results statement.

```
Metrics: ____________________________________________________
Key lesson: _________________________________________________
What I'd change: ____________________________________________
Connection to Dash: _________________________________________
```

---

## 3. Preparing for Q&A (40 minutes of probing)

Interviewers will bring domain experts. They will push you hard. Prepare for these question categories:

### Category 1: "Why" Questions

Expect 5-10 of these. They test whether you truly understood the decisions or just implemented someone else's choices.

| Question | What They're Testing |
|----------|---------------------|
| "Why did you choose [technology X]?" | Evaluated alternatives, not just used what was familiar |
| "Why not [alternative approach]?" | Awareness of trade-offs |
| "Why was this the right scope?" | Ability to scope work appropriately |
| "Why did you prioritize [A] over [B]?" | Product sense, business awareness |

### Exercise: For each technology/decision in your project, write a "why not" for 2 alternatives.

```
Decision: Used PostgreSQL for metadata storage
  Why not DynamoDB? ________________________________________
  Why not MongoDB? _________________________________________

Decision: _______________________________________________
  Why not ___? _____________________________________________
  Why not ___? _____________________________________________
```

---

### Category 2: "What If" Questions

These test your ability to think beyond what you built.

| Question | What They're Testing |
|----------|---------------------|
| "What if traffic increased 100x?" | Scaling thinking |
| "What if the latency requirement was 10ms instead of 200ms?" | Architectural flexibility |
| "What if you had 6 more months?" | Vision, prioritization |
| "What if you had to rebuild this from scratch?" | Evolved understanding |

### Exercise: Answer these for your project.

```
100x traffic: _______________________________________________
10x stricter latency: ______________________________________
6 more months: _____________________________________________
Rebuild from scratch: ______________________________________
```

---

### Category 3: "Conflict" Questions

These test collaboration and leadership, mapped to AOWE values.

| Question | Maps to |
|----------|---------|
| "Did anyone disagree with your approach?" | We, Not I |
| "How did you convince stakeholders?" | Own It + Aim Higher |
| "What did you do when requirements changed?" | Own It |
| "How did you handle a teammate who was blocking progress?" | We, Not I + Make Work Human |

### Exercise: Prepare an answer for each.

```
Disagreement: ______________________________________________
How I resolved it: _________________________________________

Stakeholder pushback: ______________________________________
How I convinced them: ______________________________________

Requirements change: _______________________________________
How I adapted: ____________________________________________
```

---

### Category 4: "Depth" Questions

Domain experts will try to find the boundary of your knowledge. This is expected — you're not supposed to know everything.

**How to handle questions you can't answer:**

- "That's a great question. I didn't explore that specific area, but my intuition is [educated guess] because [reasoning]."
- "I'm not sure about the exact mechanism, but I know that [related thing you do know]."
- **Never bluff.** They'll know. Admitting limits with good reasoning > confident wrong answer.

---

## 4. Connecting Your Project to Dash

The strongest candidates explicitly connect their experience to the role. Prepare these bridges:

### Bridge Template

"In my project, I [did X]. At Dash, the equivalent challenge is [Y], and I'd approach it by [Z]."

### Example Bridges

| Your Experience | Dash Connection |
|----------------|-----------------|
| Built search functionality | "Dash's universal search is similar but at much larger scale — I'd apply the same hybrid retrieval approach" |
| Integrated ML models into a product | "Integrating AI answers into Dash's search UI is the same problem — model timeouts, streaming, graceful degradation" |
| Built real-time collaborative features | "Dash Stacks collaboration has similar challenges — optimistic updates, conflict resolution, permission models" |
| Worked in a 0→1 environment | "Dash is in that same phase — defining new AI surfaces. I thrive in ambiguity and rapid iteration" |
| Optimized frontend performance | "Dash's sub-1s search results require the same discipline — virtualization, code splitting, streaming" |

### Exercise: Write 3 bridges from your project to Dash.

```
Bridge 1: In my project, I ________________________________
          At Dash, ________________________________________

Bridge 2: In my project, I ________________________________
          At Dash, ________________________________________

Bridge 3: In my project, I ________________________________
          At Dash, ________________________________________
```

---

## 5. Practice Schedule

| Day | Activity | Time |
|-----|----------|------|
| Day 1 | Choose project. Fill in all exercises in this doc. | 90 min |
| Day 2 | Practice full 20-min presentation out loud (alone). Time yourself. | 30 min |
| Day 3 | Practice with a friend/partner. Have them ask "why" and "what if" questions. | 60 min |
| Day 4 | Refine based on feedback. Practice the architecture diagram drawing. | 30 min |
| Day 5 | Full mock: 20 min presentation + 20 min Q&A with someone technical. | 45 min |
| Day 6 | Final polish. Practice bridges to Dash. | 20 min |

---

## 6. Self-Evaluation Checklist

After each practice run, score yourself:

- [ ] Context was clear and concise (< 3 min)
- [ ] Architecture diagram was clean and drawable in 2 min
- [ ] I covered 2-3 deep technical decisions with trade-offs
- [ ] I quantified results with specific metrics
- [ ] I showed self-awareness ("what I'd do differently")
- [ ] I connected my experience to Dash explicitly
- [ ] I handled "why" questions with specific reasoning (not "it felt right")
- [ ] I handled "what if" questions by thinking out loud
- [ ] I admitted knowledge gaps honestly instead of bluffing
- [ ] I stayed under 20 minutes for the presentation portion
- [ ] I said "I" when describing my contributions (not just "we")
- [ ] The project demonstrated the level I'm targeting (IC3/IC4/IC5)
