# Module 00: Before You Start

Before diving into interview strategy and behavioral prep, take stock of where you are. This module helps you assess your strengths, understand the interview landscape at the senior/staff level, and build the raw materials that every other module will draw from.

---

## 1. The Senior/Staff Interview Landscape

### What Changes at Senior+ Level

At junior/mid levels, interviews test "can you code?" At senior/staff levels, the bar shifts:

| Dimension | Junior/Mid | Senior (L5/E5) | Staff (L6/E6) |
|-----------|-----------|-----------------|----------------|
| **Coding** | Solve the problem | Solve it cleanly, discuss trade-offs | Design the solution architecture, then implement |
| **System Design** | Not expected | Design a system, justify choices | Design for scale, identify failure modes, drive trade-offs |
| **Behavioral** | "Tell me about yourself" | Leadership, conflict, mentorship stories | Org-level impact, cross-team influence, ambiguity navigation |
| **Communication** | Explain your code | Explain your decisions | Influence without authority, align stakeholders |
| **Bar** | Potential | Proven delivery | Multiplier effect on the team/org |

### The Typical Hiring Loop

```
1. Recruiter Screen (30 min)
   - Fit check, salary range, timeline, role details
   - Your goal: qualify the opportunity, don't oversell

2. Hiring Manager Screen (45 min)
   - Technical discussion + behavioral
   - Your goal: demonstrate senior-level thinking, ask smart questions

3. Technical Phone Screen (60 min)
   - Live coding OR system design (depends on company)
   - Your goal: communicate clearly while solving

4. On-Site / Virtual Loop (4-6 hours)
   Usually includes:
   - Coding Round 1: algorithms/data structures
   - Coding Round 2: practical/applied coding
   - System Design: design a system end-to-end
   - Behavioral: 2-3 interviewers probing leadership stories
   - Team Match / Culture Fit: casual conversation with potential teammates

5. Debrief (internal — you're not there)
   - Each interviewer submits written feedback
   - Hiring committee decides: hire / no-hire / borderline

6. Offer & Negotiation
```

Not every company follows this exactly. Startups may have 2-3 rounds. Big tech may have 5-6. But the components are consistent.

### What Interviewers Actually Evaluate

Every interviewer fills out a scorecard. Here's what they're typically rating:

```
Technical Ability
  - Can you solve problems correctly?
  - Do you understand the fundamentals?
  - Can you reason about trade-offs?

Problem-Solving Approach
  - Do you clarify before diving in?
  - Do you break the problem down?
  - Do you consider edge cases?

Communication
  - Can you explain your thinking clearly?
  - Do you check in with the interviewer?
  - Can you adjust your explanation to the audience?

Leadership & Impact
  - Have you driven projects to completion?
  - Have you navigated ambiguity and made decisions?
  - Have you grown other engineers?

Culture Fit / Values Alignment
  - Do you match the company's operating style?
  - Would people want to work with you?
  - Do you show intellectual humility?
```

---

## 2. Self-Assessment

Before preparing, know where you're strong and where you need work. Be honest — the point isn't to feel good, it's to focus your limited prep time.

### Technical Skills Inventory

Rate yourself 1-5 on each. Focus your prep on 2s and 3s (the areas where study has the highest ROI):

**Core Engineering**
- [ ] Data structures & algorithms (arrays, trees, graphs, hash maps, dynamic programming)
- [ ] System design (databases, caching, queues, load balancing, scaling)
- [ ] API design (REST, GraphQL, versioning, error handling)
- [ ] Database design (schema, indexing, query optimization, migrations)
- [ ] Testing (unit, integration, e2e, test strategy)

**Your Primary Stack** (e.g., TypeScript/Node.js, Python, Go)
- [ ] Language fluency (can you write idiomatic code without looking things up?)
- [ ] Framework mastery (Express/FastAPI/Gin — deep knowledge, not just usage)
- [ ] Runtime internals (event loop, memory model, concurrency model)
- [ ] Production patterns (logging, monitoring, deployment, error handling)

**Infrastructure & Operations**
- [ ] Docker & containers
- [ ] CI/CD pipelines
- [ ] Cloud services (AWS/GCP/Azure)
- [ ] Observability (logging, metrics, tracing)
- [ ] Security fundamentals (auth, encryption, OWASP)

### Behavioral Story Inventory

List 8-12 stories from your career that cover these themes. Each story should have measurable impact.

```
Theme                              Story? (Y/N)    Strength?
─────────────────────────────────────────────────────────────
Led a project to completion         ___             ___
Navigated ambiguity / unclear reqs  ___             ___
Resolved a conflict                 ___             ___
Mentored / grew another engineer    ___             ___
Made a difficult technical decision ___             ___
Failed and learned from it          ___             ___
Influenced without authority        ___             ___
Shipped under pressure / deadline   ___             ___
Improved a process or system        ___             ___
Handled disagreement with manager   ___             ___
Dealt with a production incident    ___             ___
Made a trade-off you weren't sure   ___             ___
about
```

Don't have 8+ stories? That's your first prep task — dig through your career history and find them.

### Identifying Your Gaps

```
Strong areas (4-5 rating):
  → Maintain. Quick refresh before interviews.
  → These are your confidence anchors.

Growth areas (2-3 rating):
  → Focus here. This is where study moves the needle.
  → Use the relevant courses in this repo.

Weak areas (1 rating):
  → Don't try to become an expert. Know enough to not embarrass yourself.
  → Have an honest answer: "I haven't worked deeply with X, but here's how I'd approach it..."
```

---

## 3. Building Your Narrative

### Your Career Story (2-Minute Version)

You will be asked "tell me about yourself" in almost every interview. Have a polished 2-minute narrative:

```
Structure:
1. Where you started and what shaped your engineering philosophy (15 seconds)
2. Key career arc — 2-3 major chapters (60 seconds)
3. What you're looking for now and why this role (30 seconds)
4. What you bring to this specific team (15 seconds)
```

Guidelines:
- **Chronological but selective** — skip irrelevant early career details
- **Impact-focused** — mention outcomes, not just responsibilities
- **Forward-looking** — end with what you want to do next, connecting to this role
- **Practiced but not robotic** — it should sound natural, not memorized

### Your "Superpower"

What's the one thing you're best at? This should be a recurring theme in your stories.

Examples:
- "I take ambiguous problems and turn them into clear, shippable plans"
- "I build reliable systems that don't page people at 3am"
- "I make teams faster by removing technical and process bottlenecks"
- "I bridge the gap between product and engineering"

Your superpower isn't a technology — it's an engineering capability that transcends any specific stack.

---

## 4. Company Research Framework

Before every interview, spend 30-60 minutes researching:

### What to Research

```
Product
  - What does the company actually build? Who uses it?
  - What are the core technical challenges? (scale, real-time, reliability)
  - Recent product launches or pivots

Engineering
  - What's the tech stack? (check job postings, engineering blog, GitHub)
  - What scale do they operate at? (users, requests, data volume)
  - Engineering blog posts — what problems are they solving?
  - Open source contributions

Culture
  - Company values (and whether they seem genuine vs performative)
  - Glassdoor / Blind reviews (filter for signal, ignore noise)
  - Interview process reviews on Glassdoor

Business
  - Revenue model (B2B, B2C, marketplace, enterprise)
  - Competitors and differentiation
  - Recent funding, growth stage, profitability
  - Recent news (layoffs, acquisitions, leadership changes)
```

### Why Research Matters

1. **Tailored stories**: you can connect your experience to their problems
2. **Better questions**: "I saw your engineering blog post about migrating to Kubernetes — what drove that decision?" shows genuine interest
3. **Red flag detection**: you can decide if this is a place you actually want to work
4. **Salary negotiation**: understanding the business helps you negotiate from strength

---

## 5. Interview Logistics

### Pipeline Management

If you're job searching actively, run multiple processes in parallel:

```
Week 1-2: Research + applications (target 10-15 companies)
Week 3-4: Recruiter screens + initial phone screens
Week 5-6: On-sites (try to cluster these — you want competing offers)
Week 7:   Offers + negotiation

Tips:
  - Track everything in a spreadsheet (company, stage, next step, deadline)
  - Time your applications so on-sites overlap within a 1-2 week window
  - Having multiple offers is the single biggest leverage in negotiation
  - It's okay to tell a recruiter "I'm in process with other companies
    and expect to have offers in 2 weeks. Can we align timing?"
```

### Mental Health

Interviewing is draining. Set sustainable limits:

- Maximum 2 on-site loops per week
- Take rest days between intensive rounds
- Rejections are data points, not verdicts on your worth
- After a bad interview, do a 10-minute retrospective, then move on
- Celebrate progress (getting to on-sites, getting positive signals), not just offers

---

## 6. How to Use This Course

### Recommended Study Order

```
1. This module (00) — self-assessment, narrative, logistics
2. Module 02 — Behavioral Interview Mastery (takes the most practice time)
3. Module 01 — Interview Strategy (framework for the whole process)
4. Module 03 — Technical Communication (how you say things matters as much as what you say)
5. Module 06 — Coding Interview Patterns (if you need algorithm refreshing)
6. Module 05 — Common Technical Questions (stack-agnostic technical knowledge)
7. Module 04 — Questions to Ask Interviewers (prepare these in advance)
8. Module 08 — Negotiation & Closing (when you have offers)
```

### Pair With Technical Courses

This course covers the meta-skills. Pair it with the technical courses for your target stack:

| Target Role | Technical Courses |
|-------------|-------------------|
| Full-stack (TS) | Node.js + React + Infrastructure |
| Backend (Python) | Python/FastAPI + Infrastructure |
| Backend (Go) | Golang + Infrastructure |
| AI/ML Engineer | LLMs + Python/FastAPI + Infrastructure |
| Generalist Senior | Node.js + Infrastructure |

### Practice Schedule

```
Daily (30-60 min):
  - Practice one behavioral story out loud (yes, out loud)
  - Solve one coding problem (LeetCode medium, timed)

Weekly (2-3 hours):
  - One mock system design (45 min + review)
  - Review and refine behavioral stories based on research for upcoming interviews

Before each interview:
  - Re-read company research notes
  - Review 3-4 stories tailored to this company's values
  - Prepare 4-5 questions for interviewers
  - Quick-scan relevant cheat sheets from technical courses
```

---

## 7. Quick Checklist

Before moving to Module 01:

- [ ] Completed the technical skills self-assessment (rated 1-5)
- [ ] Identified 8+ behavioral stories from your career
- [ ] Written a 2-minute career narrative
- [ ] Identified your "superpower"
- [ ] Know the typical interview loop structure
- [ ] Started a tracking spreadsheet (if actively searching)

---

## Next Steps

Start with [Module 02: Behavioral Interview Mastery](02-behavioral-mastery/) — building your story bank takes the most practice time, so start early. Then come back to [Module 01: Interview Strategy](01-interview-strategy/) for the tactical framework.
