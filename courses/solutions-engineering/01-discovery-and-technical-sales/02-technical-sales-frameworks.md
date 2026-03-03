# 02 -- Technical Sales Frameworks

## The Sales Cycle (SE's View)

Enterprise software sales follows a predictable progression of stages. While every deal is different in the details, the overall shape is consistent. Understanding where you are in the cycle determines what you should be doing, what risks to watch for, and how to help your AE.

### Stage-by-Stage Breakdown

| Stage | Duration | SE Ownership | AE Ownership | Key Activity |
|---|---|---|---|---|
| **Lead / Inbound** | Days | Low | High | AE qualifies inbound, routes to SE if technical |
| **Discovery** | 1-3 weeks | High | Medium | SE runs technical discovery; AE runs business discovery |
| **Demo / Proof of Value** | 1-2 weeks | High | Low | SE builds and delivers tailored demo |
| **POC / Technical Evaluation** | 2-6 weeks | Very High | Low | SE architects, supports, and manages POC |
| **Proposal / Business Case** | 1-2 weeks | Medium | High | AE builds proposal; SE provides technical justification |
| **Negotiation** | 1-4 weeks | Low-Medium | High | SE handles technical objections; AE handles commercial |
| **Close** | Days-weeks | Low | High | Contract execution, handoff planning |
| **Post-Sale Handoff** | 1-2 weeks | Medium | Low | SE transitions knowledge to CS/implementation team |

### What the SE Owns at Each Stage

**Discovery:** The SE owns the technical discovery conversation. You're the one asking about architecture, tooling, workflows, integration requirements, and technical pain points. The AE is focused on budget, authority, timeline, and business outcomes. You work in parallel but share notes after every call.

**Demo:** This is peak SE territory. You build the demo environment, craft the narrative around the prospect's pain, and deliver it. A great demo tells a story: "You told me your team spends 2 hours a day reconciling data. Let me show you what that looks like with our platform -- zero manual reconciliation." Never let an AE deliver a technical demo.

**POC:** You own the POC end-to-end: defining success criteria, architecting the solution, supporting the prospect's technical team, troubleshooting issues, and writing the final report. This is where deals are won or lost technically.

**Proposal:** You contribute the technical scope, architecture diagram, implementation plan, and any ROI calculations. The AE packages it with pricing, terms, and the business case.

**Negotiation:** Your role narrows to answering technical objections and addressing security/compliance questions. The AE drives the commercial negotiation.

### Decision Points and Gates

Every deal should have explicit gates between stages. If you can't pass the gate, the deal should not advance.

| Gate | Criteria to Pass |
|---|---|
| Discovery → Demo | Pain identified, at least 2 stakeholders engaged, basic qualification passed |
| Demo → POC | Stakeholder buy-in from demo, success criteria defined, timeline agreed |
| POC → Proposal | POC success criteria met, champion confirmed, economic buyer aware |
| Proposal → Negotiation | Proposal reviewed, no technical blockers, procurement engaged |
| Negotiation → Close | Terms agreed, security review passed, legal approved |

---

## POC-to-Close Motion

### When POCs Are Necessary

A POC (Proof of Concept) or POV (Proof of Value) is a time-boxed evaluation where the prospect tests your product in their environment with their data. It's the most resource-intensive SE activity and should not be done by default.

**POCs are necessary when:**
- The prospect has legitimate technical risk that can only be resolved by testing (performance, integration complexity, data format compatibility)
- The deal is large enough to justify the investment (typically > $100K ARR)
- Multiple stakeholders need to validate the solution (engineering, security, operations)
- The prospect is evaluating multiple vendors and needs an apples-to-apples comparison

**POCs are a stall tactic when:**
- The prospect asks for a POC before discovery is complete ("we just want to kick the tires")
- There's no defined success criteria ("we'll just see how it goes")
- The economic buyer is not aware of or invested in the POC
- The prospect already did a POC with you last year and nothing has changed

### POC Success Criteria as Deal Accelerators

The single most important thing you can do to increase POC-to-close conversion is to define explicit, measurable success criteria before the POC starts. Success criteria should be:

**Specific:** "Ingest 1M events per second with < 100ms p99 latency" -- not "perform well at scale."

**Measurable:** Each criterion should have a pass/fail condition that both sides agree to.

**Relevant:** Tied to the prospect's actual pain points, not generic capabilities.

**Time-boxed:** The POC has a hard end date (2-4 weeks is ideal). Longer POCs lose momentum.

**Template for POC success criteria:**

```
POC: [Company Name] -- [Use Case]
Duration: [Start Date] to [End Date]
Participants: [Names and Roles]

Success Criteria:
1. [Criterion] -- [Metric] -- [Pass Threshold]
2. [Criterion] -- [Metric] -- [Pass Threshold]
3. [Criterion] -- [Metric] -- [Pass Threshold]

Post-POC Agreement:
If all criteria are met, [Company] agrees to:
- Schedule a meeting with [Economic Buyer] to review results
- Begin procurement process by [Date]
```

### The POC Report as a Close Document

When the POC succeeds, write a report that your champion can use to sell internally. The report should:

1. Restate the original pain ("Your team was spending 20 hours/week on manual data reconciliation")
2. Show the POC results against success criteria (all green checkmarks)
3. Quantify the value ("During the 2-week POC, the platform saved an estimated 40 engineer-hours")
4. Project annualized ROI ("At $150/hour fully loaded, that's $312K/year in recovered engineering time")
5. Include a recommended architecture and implementation timeline
6. End with a clear next step ("We recommend proceeding to a 3-month implementation starting [date]")

This report becomes the internal business case your champion presents to the economic buyer.

---

## AE/SE Partnership

The AE/SE relationship is the most important professional relationship in technical sales. When it works well, you close more deals, faster, with less effort. When it doesn't, you waste time, lose deals, and burn out.

### Communication Cadence

| Cadence | Activity |
|---|---|
| Before every call | 5-min sync: who's attending, what's the goal, who leads which topics |
| After every call | Immediate debrief: what did we learn, what changed, what's the next step |
| Weekly | Pipeline review: status of every active deal, blockers, help needed |
| Monthly | Relationship check-in: what's working, what's not, feedback in both directions |

### When the SE Should Lead vs Follow

| SE Leads | AE Leads |
|---|---|
| Technical discovery calls | Business discovery calls |
| Demo delivery | Demo scheduling and logistics |
| POC architecture and execution | POC scoping and commercial terms |
| Technical objection handling | Commercial objection handling |
| Security questionnaire completion | Proposal and pricing |
| Architecture review sessions | Executive alignment meetings |
| Post-sale technical handoff | Contract negotiation |

### The "Good Cop / Technical Cop" Dynamic

A powerful pattern in enterprise sales: the AE plays the relationship-builder ("I want to make this work for you") while the SE plays the honest technical advisor ("Here's what will actually work and what won't"). This creates trust because the prospect gets both empathy and honesty.

**Example in practice:**
- AE: "We'd love to help you with your migration. Let me bring in my SE to discuss the technical approach."
- SE (in the meeting): "I've looked at your architecture. Migrating the monolith all at once would take 18 months and carry significant risk. Here's what I'd recommend instead: start with these 3 services, prove value in 6 weeks, then expand. It's less disruptive and gives you an early win you can show your leadership."

The prospect trusts the SE because you told them the truth, even when the truth was "don't buy everything at once." This paradoxically makes them more likely to buy.

### Managing Disagreements About Deal Strategy

Disagreements will happen. Common friction points:
- AE wants to push the deal to close faster; SE thinks the prospect isn't ready
- AE wants to promise a feature that doesn't exist; SE knows it will take 6 months
- AE wants to skip the POC; SE thinks the technical risk is too high

**Resolution approach:**
1. Have the conversation privately, never in front of the prospect
2. Start with shared goals: "We both want to close this deal"
3. Use data: "The MEDDPICC card shows we're red on Economic Buyer. If we push to close now, we'll likely stall in procurement."
4. Propose a compromise: "Let's do a condensed 1-week POC instead of skipping it entirely"
5. If you can't agree, escalate to your respective managers -- that's what they're there for

### Building Trust with Your AE

- Follow through on commitments (if you said you'd send the architecture diagram by Friday, send it by Friday)
- Share information proactively (don't hoard customer intel)
- Never go around your AE to the customer on business topics
- Celebrate wins together (closed-won is a team result)
- Give honest feedback on deal health (your AE will learn to trust your assessments)

---

## Deal Mechanics

### How Enterprise Software Deals Work

Enterprise software procurement involves multiple documents and stakeholders. Understanding the mechanics helps you set realistic timelines and support your AE effectively.

**Key documents:**

| Document | Purpose | Who Owns It |
|---|---|---|
| **MSA** (Master Service Agreement) | Legal framework for the entire relationship. Liability, IP, data handling, termination clauses. | Legal (both sides) |
| **SOW** (Statement of Work) | Scope of a specific engagement or implementation. Deliverables, timeline, acceptance criteria. | SE + AE + customer |
| **Order Form** | Commercial terms for a specific purchase. Products, quantities, pricing, payment terms. | AE + customer procurement |
| **Security Questionnaire** | Assessment of your product's security posture. Controls, certifications, data handling. | SE + security team |
| **DPA** (Data Processing Agreement) | GDPR/privacy terms for handling customer data. | Legal |

### Pricing Models

| Model | How It Works | SE Implication |
|---|---|---|
| **Seat-based** | Price per user per month/year | SE helps right-size the initial deployment. Over-sizing = sticker shock; under-sizing = upsell opportunity |
| **Usage-based** | Price per unit of consumption (API calls, GB stored, events ingested) | SE must estimate usage during POC and project production costs. Surprises here kill deals. |
| **Platform fee** | Flat fee for platform access, often with tiers | SE helps the prospect understand which tier they need and when they'd grow into the next one |
| **Hybrid** | Platform fee + usage overage | SE models total cost at current and projected volumes |

### Discount Approval Chains

Most enterprise software companies have a discount approval matrix:

| Discount Level | Approval Required |
|---|---|
| 0-10% | AE can approve |
| 10-20% | Sales manager approval |
| 20-30% | VP/Director of Sales |
| 30%+ | CRO or CEO |

SEs generally don't negotiate pricing, but you should understand the dynamics because: (1) larger discounts mean lower commission for your AE, which affects their motivation on the deal, and (2) prospects who push for excessive discounts are often poor-fit customers who will churn.

### Multi-Year Deals

Multi-year contracts (2-3 year terms) are attractive to vendors because they reduce churn and increase deal size. They affect SEs because:
- The customer expects more investment upfront (longer POC, more customization)
- The technical due diligence is more rigorous (they're committing for years)
- The implementation plan must account for growth over the contract term
- Ramp schedules (starting with fewer seats/lower usage and growing) require careful scoping

---

## Forecasting and Pipeline

### What Pipeline Means for SEs

Your company's pipeline is the sum of all deals in progress, weighted by their probability of closing. While AEs own the pipeline number, SEs have a direct impact on:

- **Pipeline creation:** Technical evaluations you support turn leads into qualified opportunities
- **Pipeline velocity:** The faster you run POCs and deliver demos, the faster deals move
- **Pipeline accuracy:** Your technical assessment of deal viability helps prevent inflated forecasts

### Technical Confidence Scores

Many organizations ask SEs to provide a separate "technical confidence" score for each deal, independent of the AE's overall forecast. This captures whether the product can actually solve the prospect's problem.

| Score | Meaning |
|---|---|
| **High** | Product is a strong fit, POC succeeded or is not needed, no technical blockers |
| **Medium** | Product can work but requires configuration, customization, or workarounds. Minor risk areas. |
| **Low** | Significant technical gaps. Product may not meet requirements. Requires roadmap items. |
| **Blocker** | There is a hard technical requirement we cannot meet. Deal should not be forecasted. |

### When to Flag Deals at Risk

Flag a deal as at-risk when:
- The prospect's requirements have changed and your product no longer fits
- A competitor demonstrated a capability you can't match
- The POC is struggling or the prospect's team is not engaged
- The champion has gone quiet or left the organization
- The technical evaluation revealed performance or integration issues
- The security review is stalled on a compliance gap

Flag early and with specifics. "I'm worried about the Acme deal" is unhelpful. "The Acme POC showed 3x higher latency than their requirement on the write path. I've escalated to engineering, but if we can't resolve it by Friday, we should discuss alternatives with the prospect" is actionable.

---

## Value Selling

### Connecting Features to Business Outcomes

The biggest mistake SEs make in demos and presentations is talking about features instead of outcomes. Prospects don't buy features -- they buy solutions to problems that affect their business.

### The Feature to Benefit to Value Chain

Every technical capability should be expressed through this chain:

| Feature (What It Does) | Benefit (Why It Matters) | Value (Business Impact) |
|---|---|---|
| Real-time data pipeline | Data is always current, no batch delays | Decisions are made on live data instead of yesterday's data, reducing time-to-insight from 24 hours to seconds |
| RBAC (Role-Based Access Control) | Right people see right data | Passes SOC 2 audit requirements, avoids $500K compliance penalty |
| Auto-scaling compute | System grows with demand automatically | No more 3am pages during traffic spikes; engineering team sleeps through launches |
| Pre-built integrations | Connect to existing tools in hours, not weeks | New data sources go live in days instead of quarters; unblocks the analytics team immediately |
| Audit logging | Every action tracked with full context | Security team can investigate incidents in minutes instead of weeks; regulatory reporting is automated |

### ROI Calculations SEs Can Make

SEs are uniquely positioned to build bottom-up ROI calculations because you understand both the technical details and the prospect's current situation from discovery.

**Common ROI frameworks:**

**Time savings:**
```
Hours saved/week * Weeks/year * Fully loaded hourly rate * Number of affected employees
Example: 5 hours/week * 50 weeks * $150/hour * 8 engineers = $300,000/year
```

**Incident cost reduction:**
```
(Current incidents/month - Projected incidents/month) * Average cost per incident
Example: (12 - 2) * $25,000 average incident cost = $250,000/month savings
```

**Revenue acceleration:**
```
Faster feature delivery → Earlier revenue recognition
Example: Reducing release cycle from monthly to weekly → 3 weeks earlier to market per feature → $X in earlier revenue
```

**Headcount avoidance:**
```
Automation replaces manual work that would otherwise require new hires
Example: Automating data pipeline management avoids hiring 2 data engineers at $200K/year each = $400K/year
```

### Building Business Cases for Technical Products

A business case combines the discovery findings, POC results, and ROI projections into a narrative that the economic buyer can use to justify the purchase. The SE typically provides the technical substance while the AE shapes the commercial framing.

**Business case structure:**
1. **Executive summary** -- One paragraph on the problem and recommended solution
2. **Current state** -- Pain points identified during discovery, with specific quotes and metrics
3. **Proposed solution** -- What you're recommending and why (high-level architecture)
4. **Expected outcomes** -- Quantified benefits tied to the prospect's metrics
5. **Implementation plan** -- Timeline, milestones, resources required
6. **Investment** -- Pricing, total cost of ownership, ROI timeline
7. **Risk mitigation** -- How the POC de-risked the decision; support and SLAs

---

## The Challenger Sale for SEs

The Challenger Sale model (Dixon and Adamson) argues that the most successful salespeople don't just respond to customer needs -- they challenge the customer's thinking and teach them something new. SEs are uniquely positioned to do this because they have technical credibility and cross-customer pattern recognition.

### Teaching Customers Something New

The best SEs come to every meeting with an insight the prospect hasn't considered. This comes from:

- **Cross-customer pattern recognition:** "We work with 200 companies your size, and the ones that succeed with this approach all do X before Y. The ones that struggle do it the other way around."
- **Industry research:** "According to the latest DORA report, elite performers deploy 973x more frequently than low performers. Based on what you told me about your deployment process, you're in the low-performer category. Here's what the path to elite looks like."
- **Technical expertise:** "You mentioned you're considering building this in-house. Based on what I've seen, teams that go that route typically underestimate the maintenance burden by 3-5x. Here's why..."

### Reframing Problems

Sometimes the prospect thinks they know what they need, but they're solving the wrong problem. A Challenger SE reframes the conversation.

**Example reframes:**

| Prospect Says | Typical SE Response | Challenger SE Response |
|---|---|---|
| "We need a better dashboard" | "Here's our dashboard" | "You might not need a better dashboard. You might need alerting that prevents you from needing to look at dashboards. Let me show you why." |
| "We want to migrate to microservices" | "We support microservices" | "Before we talk about microservices, let's talk about what problem you're trying to solve. Some of our customers found that a modular monolith gave them 80% of the benefits with 20% of the complexity." |
| "We need to reduce costs" | "We're cheaper than X" | "Cost reduction is important, but the bigger opportunity might be what your team could build if they weren't spending 30% of their time on operational toil. Let me show you the math." |

### Providing Unique Insight

Unique insight comes from seeing patterns across many customers. Keep a mental (or written) catalog of:
- **Common architectural mistakes** in your product's domain
- **Success patterns** that predict good outcomes
- **Failure patterns** that predict churn or dissatisfaction
- **Industry benchmarks** for key metrics (deployment frequency, incident response time, data freshness)
- **Counterintuitive findings** that surprise prospects ("Teams that deploy more frequently actually have fewer incidents")

When you share these patterns, you're not selling -- you're consulting. That's what builds the trust that closes enterprise deals.

---

## Practice Exercises

The following exercises in `exercises.py` directly practice concepts from this file:

- **Exercise 3: Deal Qualification Scorer** -- Implements the deal qualification and scoring concepts from the "Qualification Frameworks" section of `01-discovery-methodology.md`, but also connects to this file's treatment of how deal mechanics and pipeline management affect qualification decisions. The scoring logic reflects the gate criteria described in the "Decision Points and Gates" subsection above.

- **Exercise 5: Sales Cycle Phase Tracker** -- Directly applies the stage-by-stage breakdown from "The Sales Cycle (SE's View)" section. Requires understanding what constitutes each stage, what activities happen at each stage, and how events map to phase transitions. Reference the Stage-by-Stage Breakdown table and Decision Points and Gates.

- **Exercise 6: Win/Loss Analyzer** -- Practices the analytical thinking from "Forecasting and Pipeline" and connects to the value-selling concepts. Computing win rates, identifying loss patterns, and analyzing competitive dynamics are core forecasting skills. Reference the Technical Confidence Scores table and the "When to Flag Deals at Risk" checklist.

See also `examples.py` sections 4 (Sales Cycle Tracker) and 5 (Deal Qualification Scorer) for complete runnable reference implementations.

---

## Interview Q&A: Technical Sales Frameworks

**Q: How do you decide whether a POC is necessary or if it's a stall tactic?**

The key indicator is specificity. A prospect who has a genuine need for a POC will have specific technical questions they need answered: "Can your system handle 50K events per second with our schema?" or "Does your integration with Salesforce support custom objects?" A prospect who is stalling will say vague things like "we just want to play around with it" or "we want to see if it works." The other indicator is stakeholder investment. If the economic buyer knows about and supports the POC, it's real. If the POC is driven by a mid-level engineer who is "just evaluating options" without leadership buy-in, it's likely exploratory and you should qualify harder before investing SE time. My approach is to always require documented success criteria and a post-POC meeting with the decision-maker before agreeing to run a POC.

**Q: How do you handle a situation where the AE wants to promise features that are on the roadmap but not yet built?**

This is one of the most common and dangerous situations in SE work. Promising unbuilt features creates technical debt in the deal -- if the feature ships late, differently than promised, or not at all, you lose credibility and potentially the customer. My approach is to be transparent with the prospect about what exists today and what's planned. I'll say something like: "That capability is on our roadmap for Q3. I can show you the design doc and connect you with our PM, but I want to be honest that roadmap items can shift. Can we structure the deal so the current capabilities meet your core requirements, and the roadmap item is a bonus rather than a dependency?" This protects both the prospect and your company. If the AE pushes back, I bring in our SE manager to mediate -- credibility with the customer is more important than any single deal.

**Q: How do you quantify the value of a technical product when the prospect says "we can't put a number on it"?**

Prospects often resist quantification because it feels like you're asking them to justify the purchase before they've decided. The trick is to help them do the math collaboratively, not to present a number they have to accept. I use a technique I call "back of the napkin ROI": I ask very specific questions like "How many engineers work on this?" (8), "How many hours per week does each spend on this problem?" (5), "What's the average fully loaded cost of an engineer at your company?" ($150/hour if they share it, or I use industry averages). Then I do the math in front of them: 8 * 5 * 50 * $150 = $300K/year. Even if the numbers are approximate, having a concrete figure changes the conversation from "this is expensive" to "this pays for itself in 4 months." The SE doesn't need to do this alone -- your AE should be building the commercial business case, but the SE provides the technical input that makes the numbers credible.

**Q: Describe a deal where you had to flag a technical risk that the AE didn't want to hear.**

The best answer here shows both courage and diplomacy. Structure your answer: (1) The situation -- what the deal was and what the risk was. (2) What you did -- how you raised the concern, with whom, and how you framed it constructively. (3) The outcome -- what happened as a result. For example: "We were in a late-stage deal with a financial services company. The AE was forecasting it to close in Q4. During the POC, I discovered that their data residency requirements meant we'd need to deploy in a region where we didn't have infrastructure. I pulled the AE aside and said, 'I need to flag something. The data residency requirement is a blocker -- we'd need 2-3 months of infrastructure work before we could go live. I recommend we be transparent with the prospect and adjust the timeline.' The AE was frustrated, but we told the prospect the truth, proposed a phased approach, and the deal closed in Q1 instead of Q4. The customer later told us that our honesty was one of the reasons they chose us over the competitor."
