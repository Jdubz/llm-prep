# 01 -- SE/FDE Interview Formats and Fundamentals

The SE/FDE interview process is fundamentally different from a software engineering interview. Understanding those differences is the single most important thing you can do before entering the loop. This file covers every interview format you will encounter, the evaluation criteria interviewers actually use, prepared answers for the most common questions, the key numbers you should know, and a complete behavioral preparation framework.

---

## How SE Interviews Differ from SWE Interviews

SE interviews test a different set of skills than SWE interviews. You need technical depth, but you also need communication, business acumen, customer empathy, and the ability to think on your feet in front of a live audience. The coding bar is lower. The presentation bar is much higher.

### SWE vs SE Interview Comparison

| Dimension | SWE Interview | SE Interview |
|-----------|--------------|-------------|
| **Format** | Coding rounds, system design, behavioral | Discovery calls, demos, system design, take-home POC, behavioral, coding (lighter) |
| **Primary focus** | Can you build it? | Can you explain it, sell it, and help a customer succeed with it? |
| **Evaluation criteria** | Algorithmic thinking, code quality, system design depth, collaboration | Communication clarity, technical breadth, customer empathy, problem-solving under pressure, business acumen |
| **Prep strategy** | LeetCode, system design practice, mock coding | Mock discovery calls, demo practice, story bank development, POC building |
| **Coding bar** | High — optimal solutions, edge cases, complexity analysis | Moderate — working code, clean structure, ability to explain your approach |
| **Unique rounds** | Pair programming, code review | Discovery/mock call, live demo, executive presentation, take-home POC with presentation |
| **System design focus** | Scalability, correctness, data modeling, latency | Customer fit, integration feasibility, rollout plan, time-to-value, business justification |
| **Behavioral emphasis** | Teamwork, conflict resolution, technical decisions | Customer conflict, cross-functional collaboration, translating technical concepts, handling deal pressure |
| **Time-to-offer** | 1-3 weeks | 1-4 weeks (longer loops due to presentation rounds) |

### What SE Interviews Actually Test

1. **Communication** — Can you explain complex concepts clearly? Can you adjust your message for different audiences? Do you listen more than you talk?
2. **Technical breadth** — Do you understand APIs, databases, cloud infrastructure, networking, and security well enough to have credible conversations with technical buyers?
3. **Customer empathy** — Do you instinctively think about the customer's problem first, or do you jump to the product?
4. **Problem-solving** — When a demo breaks, a customer asks a curveball question, or a scenario is ambiguous, can you think on your feet?
5. **Business acumen** — Do you understand how deals work, what drives purchase decisions, and how your role contributes to revenue?

---

## Common Interview Formats

### Discovery/Mock Call (30-45 minutes)

You role-play as the SE. The interviewer plays the customer — often with hidden needs, objections, and a specific persona. You are evaluated on question quality, listening skills, pain identification, rapport, and whether you propose reasonable next steps. This is the most common SE-specific interview format.

**What great looks like:** You ask open-ended questions, dig past surface-level answers, identify the real business pain, map stakeholders, and propose a concrete next step. You do not pitch the product unprompted. Your talk-to-listen ratio is 30/70 or better.

**What gets you rejected:** Jumping to a pitch within 5 minutes. Asking only yes/no questions. Not acknowledging what the customer said. Failing to identify the primary pain point. No clear next step proposed.

### Live Demo (30-45 minutes)

You demo a product — sometimes the company's product (given prep time), sometimes your own project, sometimes a "teach me something technical" format. You are evaluated on narrative structure, audience adaptation, technical credibility, and recovery from problems.

**What great looks like:** You open with a hook tied to the audience's pain. You show 3-4 features mapped to specific problems. You have a wow moment. You handle interruptions gracefully. You close with a concrete next step.

**What gets you rejected:** Feature-dumping without context. Not tailoring to the audience. Freezing when something goes wrong. Going overtime. Reading from slides instead of showing the product.

### System Design for SEs (45-60 minutes)

Similar to SWE system design but with critical differences. You are expected to start with the customer and business problem, propose an architecture, discuss integration points, address operational concerns, and propose a rollout plan. You are not expected to optimize for distributed consensus algorithms.

**What great looks like:** You clarify the customer profile and constraints first. Your architecture is drawn on a whiteboard and is practical, not theoretical. You discuss integration with the customer's existing systems. You propose a phased rollout with clear milestones.

**What gets you rejected:** Diving straight into boxes and arrows without understanding the business problem. Proposing an architecture that ignores the customer's existing stack. No discussion of rollout or operational concerns. Over-engineering.

### Take-Home POC (3-8 hours)

You are given a problem statement and asked to build something — an integration, a demo, a proof of concept. You then present your work (usually 15-30 minutes). You are evaluated on code quality, documentation, architecture decisions, presentation quality, and your self-assessment of what you would improve.

**What great looks like:** Clean, documented code with error handling. A README that tells the story. A working demo. An architecture diagram. An honest assessment of limitations and what you would do with more time. A polished presentation.

**What gets you rejected:** Sloppy code with no documentation. No working demo. No architecture explanation. Over-engineering the solution. Under-engineering the presentation. Not being able to explain your own code.

### Coding Challenge (45-60 minutes)

Typically lighter than SWE coding rounds. Common formats: build a small API, parse and transform data, write a script that integrates two systems, debug a broken integration. The interviewer is evaluating your ability to write clean, working code and explain your approach.

**What great looks like:** You think out loud. You ask clarifying questions. Your code is clean and well-structured. You handle edge cases. You can explain tradeoffs.

**What gets you rejected:** Silent coding. No clarifying questions. Messy code that barely works. Unable to explain what you wrote.

### Behavioral (30-45 minutes)

Standard behavioral interview, but with SE-specific question categories: customer empathy, technical communication, cross-functional collaboration, resilience, and prioritization. STAR format is expected.

### Executive Presentation (15-30 minutes)

You present to a panel as though they are an executive audience. You are evaluated on conciseness, business language, ability to summarize complex topics, and poise. This format is less common but used by larger companies.

### Interview Loop by Company Type

| Company Type | Typical Loop |
|-------------|-------------|
| **Early-stage startup (Series A-B)** | 1 hiring manager screen + 1 take-home POC + 1 presentation + 1 founder chat |
| **Growth-stage startup (Series C-D)** | Phone screen + mock discovery call + technical deep dive + take-home POC + presentation + behavioral |
| **Mid-market SaaS** | Recruiter screen + hiring manager + mock discovery + live demo + system design + behavioral + skip-level |
| **Enterprise (large vendor)** | Recruiter + hiring manager + mock discovery + live demo + system design + coding + behavioral + executive panel |
| **Cloud/infra provider** | Recruiter + coding + system design + mock customer call + demo + behavioral + leadership principles |
| **AI/ML company** | Recruiter + technical screen + AI system design + demo + take-home POC + behavioral |

---

## Evaluation Criteria

### What Interviewers Score at Each Stage

| Stage | Top Evaluation Criteria | Relative Weight |
|-------|------------------------|----------------|
| Discovery/mock call | Question quality, listening, pain identification, rapport, next steps | Communication: 40%, Technical: 20%, Business: 40% |
| Live demo | Narrative structure, audience adaptation, technical credibility, recovery | Communication: 35%, Technical: 35%, Poise: 30% |
| System design | Customer-first framing, architecture quality, integration awareness, rollout plan | Technical: 40%, Business: 30%, Communication: 30% |
| Take-home POC | Code quality, documentation, architecture, presentation, self-assessment | Technical: 50%, Communication: 30%, Judgment: 20% |
| Coding | Working solution, code quality, explanation, edge cases | Technical: 60%, Communication: 30%, Problem-solving: 10% |
| Behavioral | Story quality, relevance, STAR structure, self-awareness | Communication: 40%, Judgment: 30%, Culture fit: 30% |

### Common Feedback Patterns for Rejected SE Candidates

- "Technically strong but couldn't explain it simply." — You went too deep for the audience.
- "Jumped to product too quickly." — You didn't do enough discovery.
- "Couldn't handle the curveball." — You froze when the mock customer went off-script.
- "No clear next steps." — You didn't close the interaction with a concrete proposal.
- "Talked too much, listened too little." — Your talk/listen ratio was inverted.
- "Great demo but couldn't answer technical questions afterward." — Your depth was shallow.
- "Couldn't articulate business value." — You spoke in technical terms only.

### "Technically Strong" vs "SE Strong"

A technically strong candidate can build it. An SE-strong candidate can explain it, tailor it to a customer's world, handle objections, propose a practical path forward, and make the customer feel heard. You need both, but most SE interviews weight SE-strong qualities more heavily.

---

## 30-Second Prepared Answers

You will be asked these questions in nearly every SE interview. Having polished, specific, concise answers ready is non-negotiable.

### "What does an SE do?"

"An SE is the technical partner on a sales team. I work alongside account executives to understand a customer's technical challenges, demonstrate how our product solves those challenges, and help the customer evaluate and adopt the solution. Day to day, that means running discovery calls to understand pain points, building tailored demos and POCs, answering technical questions, and serving as the customer's advocate internally when they need product changes or support."

### "How do you handle a customer who wants a feature we don't have?"

"First, I validate the need — I ask why they need it, what problem it solves, and what they are doing today. Sometimes the real need can be met with an existing feature or a workaround. If it truly is a gap, I am honest about it. I explain our roadmap if it is relevant, offer alternative approaches, and log the feedback internally with business context so product management can prioritize it. I never promise a feature that is not committed."

### "Tell me about your technical background and why you want to be an SE."

"I have [X years] of experience in [specific technical domain — backend engineering, data engineering, DevOps, etc.]. I have built [specific systems or projects]. What draws me to solutions engineering is that I get the most energy from the intersection of technology and people — understanding a customer's real problem, designing a solution, and communicating it in a way that lands. I find pure engineering rewarding, but I thrive when I am also working directly with customers and translating between technical and business stakeholders."

### "What's the difference between an SE and a sales rep?"

"The account executive owns the relationship and the commercial negotiation — pipeline, forecasting, pricing, contracts. The SE owns the technical win. My job is to make the customer confident that the product will solve their specific technical problem. We work as a team: the AE qualifies the opportunity and manages the deal, and I run discovery, demos, POCs, and technical validation. In a good SE/AE partnership, the customer never feels like they are being sold to — they feel like they are being helped."

### "How do you measure success as an SE?"

"The primary metric is technical win rate — the percentage of deals where the customer confirms the product meets their technical requirements. Beyond that, I track POC conversion rate, time-to-technical-win, customer satisfaction scores, and the quality of my pipeline contributions. I also measure my own efficiency: how many active deals can I support simultaneously while maintaining quality."

---

## Key Numbers for SE Interviews

Knowing these numbers signals that you understand the SE role at a business level. Interviewers notice when candidates can speak fluently about the mechanics of the role.

| Metric | Typical Range | Notes |
|--------|-------------|-------|
| Technical win rate | 60-80% | Percentage of deals where the SE achieves a "technical win" (customer agrees the product meets requirements) |
| POC duration | 2-4 weeks | Longer for enterprise, shorter for mid-market |
| Deal cycle length (SMB) | 1-2 months | Smaller deals, fewer stakeholders |
| Deal cycle length (mid-market) | 2-4 months | More stakeholders, deeper evaluation |
| Deal cycle length (enterprise) | 4-12 months | Complex procurement, security reviews, multi-stakeholder |
| SE-to-AE ratio | 1:1 to 1:3 | Varies by company; enterprise-heavy orgs trend toward 1:1 |
| POC conversion rate | 60-75% | POCs that result in a closed-won deal |
| Average deal size (SMB) | $10K-$50K ARR | Annual recurring revenue |
| Average deal size (mid-market) | $50K-$250K ARR | |
| Average deal size (enterprise) | $250K-$2M+ ARR | |
| Typical SE pipeline coverage | 3x-5x quota | Total pipeline value relative to quota target |
| Active deals per SE | 8-15 simultaneously | Depends on deal complexity and segment |
| Discovery-to-demo conversion | 40-60% | Percentage of discovery calls that proceed to a demo |
| Competitive win rate | 30-50% | When evaluated head-to-head against a named competitor |

---

## SE-Specific Behavioral Categories

SE behavioral interviews cluster around six categories. You need stories that cover all of them. Each category below includes a bank of common questions.

### Customer Empathy

| # | Question |
|---|----------|
| 1 | "Tell me about a time you advocated for a customer internally." |
| 2 | "Describe a situation where you had to say no to a customer. How did you handle it?" |
| 3 | "Tell me about a time you went above and beyond for a customer even though it wasn't your job." |
| 4 | "Describe a customer interaction that changed how you think about your product." |

### Technical Communication

| # | Question |
|---|----------|
| 1 | "Describe explaining a complex technical concept to a non-technical audience." |
| 2 | "Tell me about a time you had to simplify a message without losing accuracy." |
| 3 | "Describe a presentation that went especially well. What made it work?" |
| 4 | "Tell me about a time you had to communicate bad news about a technical limitation." |

### Resilience

| # | Question |
|---|----------|
| 1 | "Tell me about a deal you lost and what you learned." |
| 2 | "Describe a demo that went wrong. What happened and how did you recover?" |
| 3 | "Tell me about a time you failed at something and what you did differently next time." |
| 4 | "Describe a period where you had multiple setbacks in a row. How did you maintain your performance?" |

### Collaboration

| # | Question |
|---|----------|
| 1 | "Describe working with a difficult AE or cross-functional partner." |
| 2 | "Tell me about a time you had to align multiple stakeholders on a technical decision." |
| 3 | "Describe a situation where you disagreed with a product team about a customer's needs." |
| 4 | "Tell me about building a relationship with a new AE partner." |

### Problem-Solving

| # | Question |
|---|----------|
| 1 | "Tell me about a demo that went wrong and how you salvaged it." |
| 2 | "Describe a time you had to solve a customer's problem with limited information." |
| 3 | "Tell me about a creative solution you found to a customer's unusual requirement." |
| 4 | "Describe a situation where the standard approach didn't work and you had to improvise." |

### Prioritization

| # | Question |
|---|----------|
| 1 | "How do you manage competing customer demands?" |
| 2 | "Tell me about a time you had to choose between two important deals." |
| 3 | "Describe how you prioritize when you have more work than time." |
| 4 | "Tell me about a time you had to push back on an AE about prioritization." |

---

## Building Your Story Bank

You need 6-8 stories that collectively cover all six behavioral categories. One strong story can often answer questions from 2-3 categories. The key is building the bank in advance and practicing the mapping.

### STAR+I Format

SE behavioral answers should use STAR+I — the standard STAR format with an added "Impact on customer" element that demonstrates customer orientation.

| Element | What It Covers | Time Allocation |
|---------|---------------|-----------------|
| **S**ituation | Context: who, what, when, where. The setup. | 15-20% |
| **T**ask | Your specific responsibility. What was expected of you? | 10-15% |
| **A**ction | What you specifically did. Not the team — you. | 40-50% |
| **R**esult | The quantifiable outcome. Numbers matter. | 15-20% |
| **I**mpact | How the customer benefited. What changed for them? | 5-10% |

### Story Bank Template

For each story, fill in the following:

```
Story Title: _______________________________________________
One-line summary: __________________________________________

SITUATION: _________________________________________________
TASK: ______________________________________________________
ACTION (3-5 bullet points):
  - _______________________________________________________
  - _______________________________________________________
  - _______________________________________________________
RESULT (with numbers): _____________________________________
IMPACT on customer: ________________________________________

Categories this story covers:
  [ ] Customer Empathy
  [ ] Technical Communication
  [ ] Resilience
  [ ] Collaboration
  [ ] Problem-Solving
  [ ] Prioritization
```

### How One Story Covers Multiple Categories

**Example story: "The POC That Almost Failed"**

- Situation: Running a POC for a $200K deal. Two days before the deadline, a critical integration broke.
- Task: Deliver a working POC on time despite the blocker.
- Action: Diagnosed the issue (API version mismatch), coordinated with the product team for a hotfix, built a temporary workaround, communicated transparently with the customer about the timeline.
- Result: Delivered the POC on time. Customer signed the deal ($200K ARR).
- Impact: Customer avoided a 3-month delay in their data migration project.

**Category mapping for this story:**
- Problem-Solving: The technical diagnosis and workaround.
- Resilience: Not panicking when things broke.
- Collaboration: Coordinating with the product team.
- Customer Empathy: Transparent communication with the customer.

One story, four categories. Build 6-8 stories like this and you can answer any behavioral question.

### Story Coverage Check

After building your bank, create a coverage matrix:

```
                 Empathy  Comm  Resilience  Collab  Problem  Priority
Story 1:           X             X           X
Story 2:                   X                          X
Story 3:           X       X                                    X
Story 4:                          X          X        X
Story 5:           X                                  X         X
Story 6:                   X     X                              X
Story 7:                   X                 X        X
Story 8:           X              X                             X

Coverage:         4/8     4/8    4/8         3/8     4/8       4/8
```

Minimum target: every category covered by at least 2 stories. If any category has fewer than 2, develop additional stories for that gap.

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 1: Discovery Call Simulator** -- Practices the discovery and customer interaction concepts from the "Common Interview Formats" section (Discovery/Mock Call) and the behavioral question bank. You provide a list of questions for a simulated prospect and receive scoring on pain identification, question quality (open vs closed), stakeholder mapping, and next-step planning. Uses the evaluation criteria from the "Evaluation Criteria" section.

- **Exercise 5: Behavioral Story Formatter** -- Directly applies the "STAR+I Format" and "Building Your Story Bank" sections. Takes a raw unstructured story and a question category, parses it into STAR+I format, and validates completeness. Practices the story structuring discipline needed for behavioral rounds.

- **Exercise 6: Interview Readiness Scorer** -- Implements the preparation assessment framework implied across this entire file. Takes your preparation data (stories prepared, mock calls completed, system designs practiced, etc.) and scores overall readiness, identifying weak areas based on the coverage expectations defined in "Story Coverage Check" and "Common Interview Formats."

See also `examples.py` section 1 (Discovery Call Simulator) and section 4 (STAR Story Formatter) for runnable reference implementations.

---

## Interview Q&A: SE/FDE Interview Fundamentals

**Q: How would you prepare for an SE interview at a company whose product you have never used?**

My preparation has three phases. First, product research: I sign up for a free trial or watch every demo video, tutorial, and customer case study available. I read their documentation and API reference to understand technical depth. I identify the top 3 use cases and the competitive landscape. Second, company research: I read their engineering blog, recent press releases, earnings calls if public, and Glassdoor reviews for SE roles specifically. I look at who I am interviewing with on LinkedIn and understand their backgrounds. Third, practice: I build a mock discovery call script as if I were selling their product to a hypothetical customer. I prepare a demo of their product or a comparable open-source alternative. I build my story bank mapped to SE behavioral categories. The goal is that by interview day, I can speak about their product, their customers, and their market as if I have been working there for three months.

**Q: What do you think is the most important skill for a Solutions Engineer?**

Listening. Every other SE skill — demos, system design, technical communication — depends on first understanding the customer's real problem. The best SEs I have worked with spend 70% of their time in discovery listening and asking follow-up questions, not pitching. They dig past surface-level answers to find the business pain that actually drives a purchase decision. Technical depth matters, but it is wasted if you are solving the wrong problem. I would rather be an excellent listener with good technical skills than a brilliant technologist who cannot hear what the customer is really saying.

**Q: How do you handle an interview round where you do not know the answer to a technical question?**

I am honest and specific about what I do and do not know. If the question is about a technology I have not worked with, I say so — but I connect it to what I do know. For example: "I haven't worked with Kafka directly, but I've built event-driven architectures with RabbitMQ and I understand the partitioning and consumer group model conceptually. Here's how I would approach this..." Interviewers are evaluating whether you can be trusted in front of a customer. Bluffing fails that test. Saying "I don't know, but here's how I'd figure it out" passes it.

**Q: Tell me about a time you helped a customer through a difficult technical evaluation.**

I was supporting a healthcare company evaluating our data platform against two competitors. Their primary concern was HIPAA compliance, and their security team had a 200-item questionnaire. My AE wanted to focus only on the technical demo, but I recognized that the security evaluation would be the gate. I proactively partnered with our security team to complete the questionnaire in advance, scheduled a dedicated call with their CISO to walk through our compliance architecture, and built a demo environment with de-identified sample data that matched their regulatory requirements. The result was that we passed the security review two weeks faster than either competitor. The customer told us that our proactive compliance approach was the deciding factor. We closed the deal at $350K ARR. The customer impact was significant — they avoided a three-month delay in their data modernization initiative because we cleared the security gate early.
