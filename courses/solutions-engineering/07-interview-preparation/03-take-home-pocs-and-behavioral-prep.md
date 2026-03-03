# 03 -- Take-Home POCs and Behavioral Preparation

This file covers the take-home POC interview format from submission to presentation, timed interview exercises with rubrics, comprehensive behavioral preparation with the full STAR+I story bank, and salary negotiation for SE/FDE roles.

---

## What Companies Expect from Take-Home POCs

Take-home POCs are the most SE-specific interview format. They test whether you can build something, document it, and present it — the same skills you use every day as an SE building POCs for customers.

### Typical Scope and Expectations

| Dimension | Typical Expectation |
|-----------|-------------------|
| **Time** | 3-8 hours. They say "don't spend more than X hours." Respect this — going 2x over signals poor time management. |
| **Code quality** | Clean, readable, documented. Not production-grade, but not sloppy. Error handling for common cases. |
| **Documentation** | README with problem statement, approach, setup instructions, architecture, and results. |
| **Presentation** | 15-30 minute walkthrough. Usually: overview, demo, architecture, tradeoffs, what you would improve. |
| **Scope** | Build a working prototype, not a production system. The 80/20 rule applies. |

### Evaluation Criteria (What Actually Gets Scored)

| Criterion | Weight | What They Look For |
|-----------|--------|-------------------|
| **Does it work?** | 25% | Can they clone, install, and run it? Does the demo flow work? |
| **Code quality** | 20% | Clean structure, good naming, comments where needed, error handling |
| **Documentation** | 20% | Clear README, architecture diagram, honest limitations section |
| **Architecture decisions** | 15% | Sensible technology choices, justified tradeoffs, awareness of alternatives |
| **Presentation quality** | 15% | Clear explanation, good pacing, handles questions well, self-aware about limitations |
| **Polish** | 5% | Small touches that show you care — loading states, helpful error messages, consistent formatting |

### What Differentiates Great from Mediocre

| Mediocre Submission | Great Submission |
|--------------------|-----------------|
| README says "run `npm start`" | README tells the story: problem, approach, architecture, setup, results, limitations |
| Code works but is a single 500-line file | Clean module structure with clear separation of concerns |
| No error handling — crashes on bad input | Graceful error handling with helpful error messages |
| No architecture diagram | Clear diagram showing components and data flow |
| Presentation is a code walkthrough | Presentation starts with the problem, shows the demo, explains the architecture, discusses tradeoffs |
| "If I had more time, I would add tests" | "Here's what I would change: swap the mock LLM for a real API, add caching for repeated queries, and implement proper auth. Here's why I prioritized what I did." |

---

## POC Submission Excellence

### README That Tells the Story

Your README is the first thing the evaluator reads. It should be structured as follows:

```markdown
# [Project Name]

## Problem Statement
[2-3 sentences: What problem are you solving? For whom?]

## Approach
[3-5 sentences: How did you approach this? What are the key design decisions?]

## Architecture
[Diagram — ASCII art, Mermaid, or an embedded image]

## Setup and Running
[Step-by-step instructions. Copy-paste-able commands.]

```bash
git clone <repo>
cd <project>
pip install -r requirements.txt
python main.py
```

## Demo Walkthrough
[What does the evaluator see when they run it? Walk them through the flow.]

## Technical Decisions
[2-3 key decisions you made and why. What did you consider and reject?]

## Limitations and Future Work
[Be honest. What would you do with more time? What corners did you cut?]

## Time Spent
[How you allocated your time. This shows planning discipline.]
```

### Architecture Diagram

Every POC should include an architecture diagram. Even a simple ASCII diagram shows that you think architecturally.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  User Input  │────→│  API Server   │────→│  Database    │
│  (CLI/Web)  │     │  (FastAPI)   │     │  (SQLite)   │
└─────────────┘     │              │     └─────────────┘
                    │  ┌──────────┐│
                    │  │ LLM API  ││
                    │  │ (Claude) ││
                    │  └──────────┘│
                    └──────────────┘
```

### Honest Limitations Section

The limitations section is where strong candidates differentiate themselves. Evaluators expect you to know what is not production-ready.

**Good limitations section example:**

"Given the 4-hour scope, I made the following tradeoffs:
1. **Authentication:** The API has no auth. In production, I would add JWT-based auth with Okta integration.
2. **Error handling:** LLM API failures return a generic error. In production, I would add retry with exponential backoff and a circuit breaker.
3. **Data persistence:** Using SQLite for simplicity. In production, I would use Postgres with connection pooling.
4. **Testing:** I wrote 3 integration tests for the critical path. With more time, I would add unit tests for each module and edge case testing for the LLM responses.
5. **Cost:** The current implementation sends the full document to the LLM on every query. I would add chunking, caching, and a cheaper model for classification before routing to the expensive model."

---

## Practice POC 1: API Integration and Dashboard

### Brief

"Build an integration between a CRM (simulated) and a product analytics API (simulated). Create a dashboard that shows which CRM accounts are most engaged with the product."

### Requirements (4-hour scope)

1. Create a mock CRM API that returns accounts with company name, industry, deal size, and SE assignment.
2. Create a mock product analytics API that returns usage data per account (logins, feature usage, API calls).
3. Build an integration service that joins the data.
4. Create a simple dashboard (CLI table, HTML page, or web app) showing:
   - Top 10 accounts by engagement score
   - Engagement score formula (weighted combination of logins, feature usage, API calls)
   - Filter by industry or SE assignment
5. Write a technical brief (1 page) explaining the architecture and how you would scale it.

### Evaluation Rubric

| Dimension | 9-10 | 6-8 | 1-5 |
|-----------|------|-----|-----|
| **Working integration** | Both APIs work, data joins correctly, dashboard renders | Most things work, minor issues | Core functionality broken |
| **Code quality** | Clean modules, good naming, error handling | Mostly clean, some rough spots | Messy, no structure |
| **Engagement scoring** | Sensible formula, documented, configurable weights | Formula works but not documented | No clear scoring logic |
| **Technical brief** | Clear architecture, scaling considerations, tradeoffs | Brief but covers basics | Missing or superficial |
| **README** | Complete setup, architecture diagram, demo walkthrough | Setup instructions work | No README or incomplete |

---

## Practice POC 2: AI-Powered Document Processing

### Brief

"Build a document ingestion and Q&A system. Ingest a set of documents, allow natural language questions, and return answers with source citations."

### Requirements (6-hour scope)

1. Ingest at least 5 sample documents (provided as text files or hardcoded).
2. Chunk documents with overlap.
3. Embed chunks using a mock embedding function (or a real API if available).
4. Store embeddings in an in-memory vector store.
5. Accept natural language queries and return the top-3 most relevant chunks.
6. Generate an answer using the retrieved chunks (mock LLM or real API).
7. Include source citations in the answer.
8. Write a cost analysis: estimated cost per query at 100 queries/day vs 10,000 queries/day.
9. Include an architecture diagram showing how this would scale to production.

### Evaluation Rubric

| Dimension | 9-10 | 6-8 | 1-5 |
|-----------|------|-----|-----|
| **RAG pipeline** | Full pipeline works: ingest, chunk, embed, retrieve, generate | Most steps work, minor gaps | Pipeline is incomplete |
| **Answer quality** | Answers are grounded in retrieved context, citations included | Answers reference context, citations missing | Answers are generic or wrong |
| **Cost analysis** | Per-query cost breakdown, model comparison, scaling estimates | Basic cost estimate | No cost analysis |
| **Architecture diagram** | Production architecture with scaling, caching, monitoring | Basic diagram | No diagram |
| **Code quality** | Modular, documented, error handling | Mostly clean | Messy |

---

## Timed Interview Practice

### Timed Discovery Call Exercise (10 minutes)

**Setup:** Read the customer profile below. You have 10 minutes to write down:
1. Your opening (how you start the call — 2-3 sentences)
2. Your top 8 discovery questions (in the order you would ask them)
3. Your proposed next step

**Customer profile:**

> TechFlow Inc. is a Series C startup (200 employees, $30M ARR) that builds developer tools. They are growing quickly and their developer relations team wants to add an AI-powered documentation search to their docs site. They currently use Algolia for search. Their Head of DevRel, Marcus, reached out after seeing your product at a conference.

**Scoring:**
- Opening: Professional, sets agenda, positions discovery as valuable to them (0-10)
- Questions: Open-ended, cover pain/impact/stakeholders/timeline/competition (0-10)
- Next step: Specific, actionable, with a proposed date (0-10)
- Total time: Finished within 10 minutes? (bonus 5 points if yes)

### Timed Demo Exercise (15 minutes)

**Setup:** You have 15 minutes to outline a demo script for the following scenario. Write the full script with timing.

**Scenario:** You are demoing a data integration platform to a mid-market e-commerce company. Their Head of Data and a senior data engineer are on the call. They currently use manual CSV uploads to move data between Shopify and their Postgres data warehouse.

**Deliverable:**
1. Hook (30 seconds — written out word for word)
2. Context framing (1 minute)
3. Three demo segments with timing (12 minutes total)
4. Close with next step (1.5 minutes)

**Scoring:**
- Hook: Specific to customer pain, attention-grabbing (0-10)
- Segments: Mapped to customer pain points, not feature-dumping (0-10)
- Time management: Total script fits in 15 minutes with time for questions (0-10)
- Next step: Specific and actionable (0-10)

### Timed Technical Brief (20 minutes)

**Setup:** You have 20 minutes to write a 1-page technical brief from the following scenario.

**Scenario:** A healthcare company needs to integrate their Epic EHR with a new patient portal. They want patients to be able to view their lab results, upcoming appointments, and medication list. HIPAA compliance is mandatory.

**Deliverable:** A 1-page technical brief covering:
1. Problem statement (2-3 sentences)
2. Proposed architecture (with a simple diagram)
3. Key integration points (Epic FHIR API, patient portal frontend, identity management)
4. Compliance considerations (HIPAA, BAA, encryption, audit logging)
5. Rollout plan (3 phases)

**Scoring:**
- Completeness: All 5 sections covered (0-10)
- Technical accuracy: Correct use of healthcare technology terms and concepts (0-10)
- Compliance awareness: Specific HIPAA controls mentioned (0-10)
- Clarity: A non-technical executive could understand the brief (0-10)

---

## Comprehensive Behavioral Preparation

### The SE Story Bank — 8 Story Templates

Build 8 stories using the following templates. Each template targets specific behavioral categories.

**Story 1: The Customer Win**
- Category targets: Customer Empathy, Technical Communication
- Prompt: Tell me about a deal/project where your work directly led to the customer choosing your solution.
- Template:
  - Situation: Customer profile, their problem, competitive context
  - Task: Your specific role in the evaluation
  - Action: What you did — discovery, demo, POC, technical validation
  - Result: Deal outcome with numbers (ARR, deal size, time-to-close)
  - Impact: How the customer's business improved

**Story 2: The Deal You Lost**
- Category targets: Resilience, Problem-Solving
- Prompt: Tell me about a deal you lost and what you learned.
- Template:
  - Situation: The deal context — what looked promising
  - Task: Your role and what you were trying to achieve
  - Action: What happened — the failure point, what you tried
  - Result: The loss and what you learned
  - Impact: How you changed your approach for future deals

**Story 3: The Technical Deep Dive**
- Category targets: Technical Communication, Problem-Solving
- Prompt: Describe explaining a complex concept to a non-technical audience.
- Template:
  - Situation: The audience, the concept, why it mattered
  - Task: What you needed to communicate and to whom
  - Action: How you simplified, what analogies you used, how you checked understanding
  - Result: The audience's response and outcome
  - Impact: Business decision or customer confidence that resulted

**Story 4: The Cross-Functional Challenge**
- Category targets: Collaboration, Prioritization
- Prompt: Describe working with a difficult AE, PM, or engineering partner.
- Template:
  - Situation: The working relationship and the friction
  - Task: What needed to happen despite the difficulty
  - Action: How you built the relationship, found common ground, compromised
  - Result: The outcome for the deal/project
  - Impact: How the relationship improved long-term

**Story 5: The Demo Disaster**
- Category targets: Resilience, Problem-Solving, Technical Communication
- Prompt: Tell me about a demo or presentation that went wrong.
- Template:
  - Situation: The demo context — audience, stakes, what was planned
  - Task: What you were supposed to deliver
  - Action: What went wrong, how you recovered in real-time
  - Result: The outcome — did you save the deal? What did the customer say?
  - Impact: What changed in your preparation process

**Story 6: The Customer Advocate**
- Category targets: Customer Empathy, Collaboration
- Prompt: Tell me about a time you advocated for a customer internally.
- Template:
  - Situation: The customer's need and why it wasn't being addressed
  - Task: What the customer needed from your organization
  - Action: How you escalated, built the case, and influenced the decision
  - Result: What happened — did the customer get what they needed?
  - Impact: Customer outcome and any product/process changes that resulted

**Story 7: The Prioritization Crunch**
- Category targets: Prioritization, Resilience
- Prompt: How do you manage when you have more work than time?
- Template:
  - Situation: The competing demands — multiple deals, POCs, deadlines
  - Task: What was at stake for each commitment
  - Action: How you triaged, communicated, and delivered
  - Result: What you delivered and what you had to deprioritize (and how you communicated that)
  - Impact: Customer and business outcomes

**Story 8: The Creative Solution**
- Category targets: Problem-Solving, Customer Empathy, Technical Communication
- Prompt: Tell me about finding an unconventional solution to a customer's problem.
- Template:
  - Situation: The customer's unusual requirement that standard approaches did not address
  - Task: What the customer needed and why the standard approach failed
  - Action: The creative solution you devised — technical workaround, partnership, custom integration
  - Result: Whether it worked and the customer's response
  - Impact: How it affected the deal and any broader product changes

### Mapping Stories to Question Categories

After building your stories, create a coverage matrix:

| Story | Empathy | Comm | Resilience | Collab | Problem | Priority |
|-------|---------|------|-----------|--------|---------|----------|
| 1: Customer Win | X | X | | | | |
| 2: Deal Lost | | | X | | X | |
| 3: Technical Deep Dive | | X | | | X | |
| 4: Cross-Functional | | | | X | | X |
| 5: Demo Disaster | | X | X | | X | |
| 6: Customer Advocate | X | | | X | | |
| 7: Prioritization | | | X | | | X |
| 8: Creative Solution | X | X | | | X | |

**Target:** Every category covered by at least 3 stories. Adjust your bank if any column has fewer than 2 marks.

### Behavioral Question Deep Dive

#### Customer Conflict Resolution

Common questions:
- "Tell me about a time a customer was unhappy with your product."
- "Describe a situation where a customer's expectations didn't match reality."
- "How do you handle a customer who is angry about a bug during a POC?"

**Ideal response framework:**
1. Acknowledge the emotion first — "I understood why they were frustrated."
2. Describe what you did to understand the root cause — not just the complaint, but the underlying business impact.
3. Explain the concrete actions you took — both for the immediate issue and the systemic fix.
4. Quantify the result — did the customer stay? Did the deal close? Did you retain the relationship?
5. Show what you learned — how did this change your approach?

#### Cross-Functional Challenges

Common questions:
- "Describe working with a sales rep who had different priorities than you."
- "Tell me about a time you disagreed with the product team."
- "How do you handle it when engineering says 'no' to a customer request?"

**Ideal response framework:**
1. Describe the tension without blame — "We had different perspectives on prioritization."
2. Show empathy for the other side — "I understood that the AE was under quota pressure."
3. Explain how you found alignment — shared goals, data, compromise.
4. Show the result — what was the outcome for the customer and the business?

#### Technical Leadership Without Authority

Common questions:
- "How do you influence technical decisions when you're not the decision-maker?"
- "Describe leading a POC when you didn't control the engineering resources."
- "Tell me about convincing a customer's team to change their technical approach."

**Ideal response framework:**
1. Establish context — why did you need to influence without authority?
2. Describe your approach — data, prototypes, proof points, relationship building.
3. Show the outcome — did the decision change? What was the impact?
4. Reflect on what worked — what techniques were most effective?

#### Handling Failure

Common questions:
- "Tell me about your biggest professional failure."
- "Describe a time you made a mistake that affected a customer."
- "What's the hardest feedback you've ever received?"

**Ideal response framework:**
1. Own it fully — no blame shifting, no minimizing.
2. Describe the impact honestly — what went wrong and who was affected.
3. Show what you did immediately — how did you respond?
4. Show what you changed long-term — what system, process, or behavior did you change?
5. Demonstrate growth — how are you different because of this experience?

---

## Salary Negotiation for SE Roles

### Understanding OTE (On-Target Earnings)

SE compensation is typically structured as base salary plus variable (commission or bonus). The total is called OTE — On-Target Earnings.

| Component | Typical SE Split | Notes |
|-----------|-----------------|-------|
| **Base salary** | 60-75% of OTE | Guaranteed, paid monthly/biweekly |
| **Variable** | 25-40% of OTE | Paid quarterly or semi-annually, tied to team or individual quota attainment |
| **OTE example** | $180K OTE = $126K base + $54K variable (70/30 split) | |

### Base vs Variable Split

The split matters more than the OTE number. Key considerations:

| Split | Risk Level | Best For |
|-------|-----------|---------|
| **80/20** | Low risk | Conservative candidates, early-career SEs, companies with unpredictable revenue |
| **70/30** | Moderate risk | Standard for most SE roles. Balanced incentive. |
| **60/40** | Higher risk | Senior SEs with confidence in the product and territory. Higher upside. |
| **50/50** | High risk | Rare for SEs (more common for AEs). Significant downside if team misses quota. |

### How to Evaluate Compensation Packages

When comparing offers, evaluate the full package:

```
TOTAL COMP = Base + Variable (at 100% attainment) + Equity + Benefits

Questions to ask:
1. What is the OTE and what is the base/variable split?
2. What is the variable tied to? Team quota, individual quota, or company revenue?
3. What percentage of SEs hit 100% of their variable last year?
4. Is there an accelerator above 100%? (e.g., 1.5x for 100-120%, 2x for 120%+)
5. What is the quota? Is it realistic given the territory?
6. Is there a ramp period for new hires? (Typically 3-6 months at guaranteed variable)
7. What does the equity package look like? (Options, RSUs, vesting schedule)
8. What is the benefits package? (Health, 401k match, learning stipend)
```

### When Variable Is Risky vs Safe

**Variable is safe when:**
- 80%+ of the SE team hit their target last year
- Variable is tied to team quota (not individual)
- The company is growing and has strong product-market fit
- There is a guaranteed ramp period (3-6 months)
- There is an accelerator structure that rewards overperformance

**Variable is risky when:**
- Fewer than 60% of SEs hit target last year
- Variable is tied to factors you cannot control (company revenue, AE performance)
- The product is pre-product-market-fit or in a new market
- There is no ramp period
- The quota is unrealistic relative to the territory

### Equity Considerations for Startup SE/FDE Roles

| Stage | Typical Equity | Key Questions |
|-------|---------------|---------------|
| **Seed/Series A** | 0.05-0.2% | What is the current valuation? What's the strike price? What's the last preferred price? |
| **Series B** | 0.02-0.1% | Is there a 409A valuation? What's the liquidation preference stack? |
| **Series C+** | 0.01-0.05% | What's the path to liquidity? Is there a secondary market? |
| **Late-stage/Pre-IPO** | RSUs, 0.005-0.02% | When is the expected IPO/liquidity event? What's the current 409A? |

**Key equity questions:**
- What is the vesting schedule? (Standard: 4-year vest, 1-year cliff)
- What happens to my equity if I leave after 2 years?
- What is the exercise window after leaving? (90 days is standard but bad; 5-10 years is better)
- Are there any liquidation preferences that would dilute common stock?

### How to Negotiate (SE-Specific Aspects)

1. **Get the full picture first.** Ask about OTE, split, quota, attainment rates, equity, and benefits before negotiating. Say: "I want to evaluate the complete package before we discuss numbers."

2. **Negotiate base and variable separately.** If you want lower risk, push for a higher base/lower variable split. If you want higher upside, push for an accelerator structure.

3. **Ask about quota realism.** "What percentage of your SE team hit 100% last year? What about 80%?" If the answer is less than 70% at 100%, the OTE number is misleading.

4. **Negotiate the ramp.** Ask for 3-6 months of guaranteed variable while you ramp. This protects you while you learn the product and build relationships.

5. **Use the territory as leverage.** If the territory is large, high-growth, or strategically important, argue for a higher OTE. If the territory is small or difficult, argue for a higher base.

6. **Equity negotiation.** For startups, equity is negotiable. Ask for more shares, a longer exercise window, or acceleration on change of control.

7. **Get it in writing.** The offer letter should clearly state: base, OTE, variable formula, quota, ramp terms, equity details, and accelerator structure.

**Cross-reference:** For general negotiation fundamentals (anchoring, BATNA, timing, and counter-offer strategy), see the general-interview course negotiation module.

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 4: Take-Home POC Evaluator** -- Directly applies the "Evaluation Criteria (What Actually Gets Scored)" section and the "What Differentiates Great from Mediocre" comparison. Takes a POC submission profile and scores it against the rubric dimensions (code quality, documentation, architecture, presentation, etc.), returning per-dimension scores, an overall grade, and specific improvement suggestions.

- **Exercise 5: Behavioral Story Formatter** -- Practices the "STAR+I Format" and "The SE Story Bank — 8 Story Templates" from the "Comprehensive Behavioral Preparation" section. Takes a raw unstructured story and formats it into proper STAR+I structure with completeness validation.

- **Exercise 6: Interview Readiness Scorer** -- Implements the preparation assessment framework that spans this entire file and file 01. Takes your preparation data and scores readiness across all interview dimensions.

See also `examples.py` section 4 (STAR Story Formatter) and section 5 (POC Rubric) for complete runnable reference implementations.

---

## Interview Q&A: Take-Home POCs and Behavioral Preparation

**Q: How do you approach a take-home POC assignment?**

I start with 15 minutes of planning before writing any code. I read the brief twice, identify the core requirement versus nice-to-haves, and sketch an architecture. Then I allocate my time explicitly — typically 10% planning, 50% building the core functionality, 15% documentation, 15% polish and error handling, 10% presentation preparation. I build the critical path first and get it working end-to-end before adding features. My README tells the story: problem, approach, architecture diagram, setup instructions, and an honest limitations section. I always include a section on what I would do differently with more time — this shows self-awareness and architectural thinking. When I present, I start with the problem and demo, not the code. Code comes after the audience understands what it does and why.

**Q: Tell me about a time you had to handle a difficult customer situation.**

At my previous role, I was running a POC for a $300K deal with a logistics company. Three days before the POC deadline, the customer's lead engineer sent a heated email saying our integration was "fundamentally broken" and he was recommending they go with the competitor. Instead of getting defensive, I called him directly and asked him to walk me through exactly what was failing. It turned out the integration was working, but our error messages were so cryptic that he thought successful operations were errors. I spent that evening rewriting the error handling to be clear and descriptive, documented every status code, and sent him a walkthrough video the next morning. He responded: "This is what I needed from day one." We closed the deal. The customer impact was significant — they were able to launch their real-time tracking feature two months ahead of schedule because the integration was solid. I learned that what customers call "broken" is often "confusing," and that investing in clear error messages and documentation is never wasted.

**Q: How do you think about compensation when evaluating SE roles?**

I evaluate the complete package, not just the headline number. I look at four things. First, the base-to-variable split — I want to understand what is guaranteed versus what depends on quota attainment. Second, quota realism — I ask what percentage of the team hit 100% last year, because a $200K OTE means nothing if only 30% of the team achieves it. Third, equity — for startups, I evaluate the stage, the valuation, the exercise window, and the liquidation preference stack. Fourth, the intangibles — the territory, the product-market fit, the SE-to-AE ratio, and the manager. I negotiate base and variable separately, always ask for a ramp period, and get the full compensation structure in writing before making a decision.
