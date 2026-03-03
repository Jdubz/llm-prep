# 02 -- POC Design and Execution

A Proof of Concept (POC) is a controlled technical validation that proves your product can solve a specific customer problem with their data, in their environment, under their constraints. It is the bridge between "that demo looked great" and "we're signing the contract." POCs are where deals are won or lost technically. They are also where SEs spend the most unbillable time if they are not disciplined about scoping, success criteria, and timelines.

---

## When to POC

Not every deal needs a POC. The wrong POC wastes weeks of SE time on a deal that was never going to close or did not need proof. The right POC converts a technically skeptical buyer into a champion.

### Decision Tree: Is a POC Necessary?

```
Does the prospect have a specific, articulable technical concern?
  ├── YES → Is the concern addressable with documentation, a reference, or a demo?
  │         ├── YES → No POC. Address it directly.
  │         └── NO  → POC is warranted.
  └── NO  → Is procurement requiring an evaluation?
            ├── YES → Is the deal large enough to justify SE time?
            │         ├── YES → POC (but keep scope tight).
            │         └── NO  → Offer a trial or sandbox instead.
            └── NO  → No POC. Move to proposal.
```

### Signs a POC is a Stall Tactic

Watch for these red flags:

| Red Flag | What It Really Means |
|----------|---------------------|
| "We need to evaluate 5 vendors in parallel" | They are comparison shopping without intent. You are providing free consulting. |
| No named champion or executive sponsor | Nobody is invested in the outcome. If it succeeds, who celebrates? |
| "We need to test everything" | They do not know what they need. They are hoping the POC will define their requirements. |
| No success criteria after two asks | They are not serious about making a decision. |
| "Can you extend it another month?" | The POC has become a free tool. There is no decision deadline. |
| The AE does not know the deal timeline | The deal is not real yet. Do not POC a phantom deal. |

### When to Push Back on POC Requests

You can and should push back. Phrases that work:

- "Happy to do a POC. Before we start, can we align on what success looks like and who will make the decision based on the results?"
- "Given the timeline you mentioned, I'd recommend a focused 2-week POC on your top use case rather than a broad evaluation. We can always expand scope in a second phase."
- "For deals at this stage, we typically do a guided trial rather than a custom POC. Would that work for your evaluation?"

### POC vs Pilot vs Trial

| Term | Definition | Duration | Custom Work | Who Runs It |
|------|-----------|----------|-------------|-------------|
| **POC** | Controlled test of specific capabilities with prospect's data/environment | 2-4 weeks | Moderate — SE builds and configures | SE + prospect technical team |
| **Pilot** | Limited production deployment with real users | 4-12 weeks | Significant — may involve custom integrations | Customer team + SE support |
| **Trial** | Self-serve or guided access to the product | 7-30 days | None — standard product | Customer (self-serve) or SE (guided) |

Use a **trial** when the product is self-explanatory and the deal is smaller. Use a **POC** when the prospect has specific technical concerns that must be validated with their data. Use a **pilot** when the prospect needs to prove organizational adoption, not just technical capability.

---

## POC Scoping

Scoping is the most critical skill in POC execution. A well-scoped POC is a focused experiment that proves a specific hypothesis. A poorly-scoped POC is an open-ended consulting engagement that drains SE capacity and rarely leads to a deal.

### The "Three Use Cases" Rule

Never POC more than three use cases. Ideally, POC one. The math is simple:

- **1 use case**: 2 weeks, high confidence, clear success/fail signal
- **2 use cases**: 3 weeks, moderate confidence, muddied signal
- **3 use cases**: 4+ weeks, low confidence, scope creep guaranteed
- **4+ use cases**: You are doing free consulting. Stop.

If the customer insists on testing everything, rank the use cases by business impact and say: "Let's nail the most important one first. If that succeeds, use cases 2 and 3 become a lot simpler to validate."

### POC Scope Document Template

Every POC should start with a scope document that both sides sign off on. This is the contract that prevents scope creep.

```markdown
# POC Scope Document

## Objective
[One sentence: What are we proving?]
Example: "Validate that [Product] can ingest and transform [Customer]'s
Salesforce data into their Snowflake warehouse with < 5 minute latency."

## In-Scope
- Use Case 1: [Specific description with data sources and expected output]
- Use Case 2: [If applicable]
- Integration points: [Which systems are involved]
- Data: [What data will be used — sample vs production, volume, sensitivity]
- Users: [Who will interact with the POC]

## Out-of-Scope
- Production deployment
- Performance testing at full scale (we will test at [X]% of production volume)
- Custom UI development
- SSO integration (will use direct authentication for POC)
- [Anything the customer might assume is included but is not]

## Success Criteria
[See next section — must be defined before POC starts]

## Timeline
- Kickoff: [Date]
- Checkpoint 1: [Date] — [What will be reviewed]
- Checkpoint 2: [Date] — [What will be reviewed]
- Final review: [Date]
- Decision: [Date — when will the customer make a go/no-go decision?]

## Resources Required
- From [Product]: SE (name), support escalation path
- From [Customer]: technical POC (name), data access, environment access
- Customer dependencies: [What do we need from them and by when?]

## Risks and Mitigations
- Risk: Customer data access delayed → Mitigation: Start with synthetic data
- Risk: API rate limits → Mitigation: Request temporary limit increase
```

### Getting Stakeholder Sign-Off

The scope document must be signed off by:
1. **Your AE** — to confirm the deal justifies the SE time
2. **The customer's technical lead** — to confirm they will participate and provide resources
3. **The customer's decision-maker** — to confirm that if the POC succeeds, they will move forward (or at minimum, move to next stage)

Without #3, you are building a science project, not a POC.

---

## Success Criteria Design

Success criteria are the most important part of the scope document. They define what "success" means before the POC starts, so there is no ambiguity after.

### SMART Criteria for POCs

Every success criterion should be SMART:

| Element | Definition | Bad Example | Good Example |
|---------|-----------|-------------|--------------|
| **Specific** | Precisely what is being measured | "It should be fast" | "Query response time for the standard dashboard" |
| **Measurable** | A number or clear yes/no | "Good performance" | "< 2 second P95 response time" |
| **Achievable** | Your product can actually hit it | "Zero latency" | "< 500ms median latency" |
| **Relevant** | Matters to the customer's decision | "Supports 50 data formats" | "Supports Salesforce, HubSpot, and Postgres (their three sources)" |
| **Time-bound** | Has a deadline | "Eventually" | "Demonstrated by the final review on [date]" |

### Example Success Criteria by Scenario

**Scenario: Data integration platform**
```
SC-1: Successfully ingest data from Salesforce and HubSpot into Snowflake
      with correct schema mapping. (Specific, Measurable: yes/no)

SC-2: End-to-end latency from source update to warehouse availability
      is < 5 minutes for 95% of records. (Measurable, Time-bound by POC end)

SC-3: Handle a schema change in the source system without manual intervention.
      (Specific, Relevant to their top pain point)

SC-4: Customer's data analyst can build a new integration without
      engineering involvement. (Relevant, Measurable: yes/no)
```

**Scenario: AI/ML platform**
```
SC-1: Model inference latency < 200ms P99 for their production payload size.

SC-2: Classification accuracy >= 90% on their labeled test set (500 samples).

SC-3: Model can be retrained on new data in < 4 hours (their weekly cadence).

SC-4: Integration with their existing FastAPI service requires < 50 lines of code.
```

**Scenario: Security platform**
```
SC-1: Detect 95% of known attack patterns in their SIEM log sample.

SC-2: False positive rate < 5% on their normal traffic baseline.

SC-3: Alert-to-investigation workflow completes in < 3 clicks.

SC-4: SSO integration with their Okta instance functions correctly.
```

### Getting the Customer to Define Success

The best success criteria come from the customer, not from you. When the customer defines success, they own the outcome. When you define it, they can move the goalposts.

**Questions to ask:**
- "If this POC succeeds, what will you show your leadership?"
- "What would make you say 'this is the right tool' at the end of two weeks?"
- "What is the one thing that has to work for this to be a yes?"
- "If we hit these criteria, are you ready to move to a contract discussion?"

---

## POC Execution

### Weekly Cadence

A well-run POC follows a predictable rhythm:

```
Week 0: Kickoff
  - Review scope document with all stakeholders
  - Confirm data access, environment access, credentials
  - Set up communication channels (Slack, email cadence)
  - Identify and assign action items

Week 1: Build
  - SE configures the environment and sets up integrations
  - Customer provides data access and resolves dependencies
  - Daily or every-other-day async check-ins
  - End of week: first working demo of the primary use case

Week 2: Validate
  - Customer tests with their own workflows
  - SE addresses issues and refines configuration
  - Checkpoint meeting: review progress against success criteria
  - Document any scope changes (with sign-off)

Week 3 (if needed): Polish and Present
  - Final testing and edge case validation
  - SE prepares results document
  - Final review meeting with decision-makers
  - Decision: go/no-go
```

### The POC Standup Format

Keep POC standups short and structured:

```
1. Progress since last update (what got done)
2. Blockers (what is stuck and who can unblock it)
3. Plan for next period (what will get done next)
4. Success criteria status (green/yellow/red for each criterion)
```

**Example:**
```
Subject: [ACME POC] Week 1 Update

Progress:
- Salesforce connector configured and ingesting data successfully
- Snowflake destination table created with correct schema mapping
- End-to-end latency measured at 3.2 minutes (target: < 5 min) ✅

Blockers:
- HubSpot API credentials not yet provided (need from Tom by Wednesday)
- VPN access to staging environment still pending IT approval

Plan:
- Configure HubSpot connector once credentials received
- Begin schema change testing (SC-3) on Thursday

Success Criteria Status:
- SC-1 (Ingest SF + HubSpot): 🟡 SF done, HubSpot blocked on credentials
- SC-2 (< 5 min latency): 🟢 Measuring 3.2 min
- SC-3 (Schema change handling): ⚪ Not started yet
- SC-4 (Analyst self-serve): ⚪ Planned for Week 2
```

### Managing Customer Dependencies

The #1 risk in any POC is customer dependencies: data access, credentials, environment access, and the customer's time. Track these relentlessly.

| Dependency | Owner | Due Date | Status | Escalation |
|-----------|-------|----------|--------|------------|
| Salesforce API credentials | Tom (Customer) | Day 2 | Complete | |
| HubSpot API credentials | Tom (Customer) | Day 5 | Overdue | Escalate to AE → VP |
| VPN access to staging | IT (Customer) | Day 3 | Pending | Follow up daily |
| Sample labeled data set | Data team (Customer) | Day 7 | On track | |

**When you are blocked:** Escalate through your AE. The AE has the relationship with the economic buyer and can apply pressure that you cannot. Do not sit silently on a blocked POC — that is how POCs die.

---

## Build vs Configure

### The 80/20 Rule for POCs

In a POC, you should be able to demonstrate 80% of the value using product configuration alone. The remaining 20% might require light scripting, custom connectors, or workflow configuration. If more than 20% requires custom code, either the product does not fit the use case or the scope is wrong.

### When Custom Code is Appropriate

| Appropriate | Not Appropriate |
|------------|-----------------|
| A small script to transform the customer's data format into your product's expected input | A custom application that wraps your product's UI |
| A webhook handler that connects the product to the customer's notification system | A new feature that does not exist in the product |
| A configuration file or template for the customer's specific schema | Production-quality code that the customer will deploy |
| A Jupyter notebook that demonstrates API capabilities | Anything that takes more than a day to build |

### The "Unrealistic Expectations" Trap

Custom code in a POC creates a dangerous precedent. If the POC includes a custom Python script that automates a workflow, the customer expects that script in production. If the POC includes custom error handling that makes the product look more resilient than it is, you set expectations your implementation team cannot meet.

**Rule:** Anything you build in the POC should either (a) be achievable with the product's standard capabilities or (b) be explicitly flagged as "POC-only, not included in production deployment."

### Managing Scope Creep

Scope creep is the gradual expansion of POC requirements beyond the agreed scope. It happens in every POC. The antidote is the scope document.

When the customer asks for something new:
1. "That's a great idea. Let me check if that's in our current scope."
2. [Check the scope document]
3. If out of scope: "That's not in our current POC scope. We can absolutely address it, but I want to keep us focused on the success criteria we agreed to. Can we add it to a Phase 2 list?"
4. If the customer insists: "Sure, let's add it — but I want to flag that this will likely extend our timeline by [X days]. Let me update the scope document so everyone is aligned."

Always document scope changes in writing.

---

## POC-to-Production Transition

### The POC Results Document

When the POC is complete, prepare a results document that maps directly to the success criteria:

```markdown
# POC Results: [Customer Name] — [Date]

## Executive Summary
[2-3 sentences: what we proved, key outcomes]

## Success Criteria Results

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| SC-1: Ingest SF + HubSpot | Data flows correctly | Both sources ingesting, 100% schema accuracy | ✅ Pass |
| SC-2: Latency < 5 min | < 5 min P95 | 3.2 min P95 | ✅ Pass |
| SC-3: Schema change handling | Auto-recovery | Detected and adapted in 45 seconds | ✅ Pass |
| SC-4: Analyst self-serve | No engineering needed | Analyst added Postgres source independently in 12 min | ✅ Pass |

## Key Findings
- [Unexpected positive finding]
- [Limitation discovered and mitigation]
- [Performance note worth highlighting]

## Production Deployment Recommendations
- [What changes between POC and production]
- [Estimated timeline for production deployment]
- [Resources required]

## Appendix
- [Configuration details]
- [Test data and methodology]
- [Screenshots/recordings]
```

### What Changes Between POC and Production

| Dimension | POC | Production |
|-----------|-----|-----------|
| Data volume | Sample or subset | Full production volume |
| Authentication | Direct credentials / API keys | SSO, RBAC, least-privilege |
| Monitoring | Manual observation | Automated alerts, dashboards, SLAs |
| High availability | Single instance | Multi-AZ, failover, redundancy |
| Security review | Informal | Formal security review, pen testing |
| Documentation | POC notes | Runbooks, architecture docs, training |
| Support | SE direct access | Standard support channels, SLAs |

### The "POC Trap" — Never-Ending Evaluations

Some POCs never end. The customer keeps finding "one more thing to test" and the deal stalls. This happens when:
- There is no decision-maker attached to the POC
- Success criteria were not defined upfront
- The customer is using the POC as a free tool
- The AE is not driving the business timeline in parallel

**How to break the cycle:**
1. Refer to the scope document: "We've hit all four success criteria. Based on our agreement, the next step is [decision]."
2. Create urgency: "Our POC environment expires on [date]. If you need more time, we can discuss an extension, but I'd recommend we review results with your leadership first."
3. Escalate through the AE: The AE needs to drive the commercial conversation independently of the POC.

---

## Timeline Management

### Typical POC Timelines

| Product Type | Typical Duration | Why |
|-------------|-----------------|-----|
| SaaS / Cloud-native | 2-3 weeks | Minimal setup, API-driven, fast iteration |
| Data platform | 3-4 weeks | Data access, schema mapping, volume testing |
| Security tool | 3-4 weeks | Security review, log integration, policy configuration |
| Enterprise on-prem | 4-8 weeks | Installation, infrastructure, network configuration |
| AI/ML platform | 3-6 weeks | Data preparation, model training, evaluation |

### Setting Milestones

Break the POC into milestones that each deliver visible value:

```
Milestone 1 (Day 3-5):  "First data flows" — basic connectivity proven
Milestone 2 (Day 7-10): "Core use case working" — primary success criterion met
Milestone 3 (Day 12-15): "All criteria validated" — full results ready
Milestone 4 (Day 15-20): "Results presented" — decision-maker briefed
```

Each milestone should be a checkpoint where you assess progress and decide whether to continue, adjust, or escalate.

### Buffer Time

Always build in buffer. The rule of thumb:

```
Estimated time × 1.5 = Quoted timeline
```

A 2-week POC should be quoted as 3 weeks. The buffer accounts for:
- Customer dependencies delivered late (always)
- Unexpected technical issues
- Stakeholder availability for reviews
- Holidays, sick days, competing priorities

### When to Extend vs When to Call It

| Extend | Call It |
|--------|---------|
| Blocked by customer dependencies outside your control | All criteria passed but customer keeps asking for more |
| A genuine technical issue that needs investigation | The product fundamentally cannot meet the criteria |
| The customer is engaged, responsive, and committed | The customer is unresponsive and missing checkpoints |
| The AE confirms the deal is still active and progressing | The AE has no visibility into the decision process |
| One criterion is close but needs more time | Multiple criteria are failing with no path to resolution |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 2: POC Scope Definer** -- Practices the "POC Scoping" section end-to-end: classifying customer requirements as in-scope, out-of-scope, or stretch goals based on product capabilities, then generating success criteria for in-scope items. The function follows the POC Scope Document template structure, applying the "Three Use Cases" rule to keep scope focused.

- **Exercise 3: Success Criteria Generator** -- Directly applies the "Success Criteria Design" section: generating SMART criteria from a use case description and customer priorities. Each criterion must be specific, measurable, achievable, relevant, and time-bound, following the patterns shown in the "Example Success Criteria by Scenario" tables.

- **Exercise 6: POC Timeline Estimator** -- Practices the "Timeline Management" section: estimating POC duration based on scope complexity, customer responsiveness, and resource availability. The function applies the "Typical POC Timelines" reference, builds milestones per the milestone template, and applies the 1.5x buffer rule.

See also `examples.py` section 2 (POC Scope Document) and section 4 (Success Criteria Matrix) for runnable reference implementations.

---

## Interview Q&A: POC Design

**Q: How do you scope a POC? Walk me through your process.**

Scoping starts during discovery — I need to understand the customer's technical concerns, their top use cases, and who is making the decision. From there, I apply the "three use cases" rule: never POC more than three, ideally one. I write a scope document with a clear objective (one sentence: what are we proving), explicit in-scope and out-of-scope sections, SMART success criteria, a timeline with milestones, and the resources required from both sides. The most important element is success criteria — I ask the customer to define them: "If this POC succeeds, what will you show your leadership?" I get sign-off from the customer's technical lead and decision-maker before starting. Without sign-off from the decision-maker that a successful POC leads to a next step, you are building a science project.

**Q: Tell me about a time a POC went sideways. How did you recover?**

I had a POC where the customer's data team could not provide API credentials for two weeks — half the POC timeline. The first thing I did was escalate through my AE to the customer's VP who had sponsored the evaluation. That unblocked credentials within 48 hours. In parallel, I started building with synthetic data that matched the customer's schema so we would not lose time when real credentials arrived. When we got access, we swapped in real data and were only two days behind schedule. I also used the delay to refine the POC scope — we dropped a low-priority use case and focused on the one that mattered most. The lesson: track customer dependencies daily, escalate early, and always have a parallel path so you are never fully blocked.

**Q: How do you decide if a deal justifies a POC?**

I use a simple decision tree. First, does the prospect have a specific technical concern that cannot be addressed with documentation, a reference call, or a demo? If yes, a POC is warranted. If no, I check whether procurement requires an evaluation — in which case the deal size has to justify the SE time. For smaller deals, I offer a self-serve trial or guided sandbox instead. The red flags that a POC is a waste of time: no named champion, no success criteria after two asks, parallel evaluation of five vendors with no clear decision criteria, or an AE who does not know the deal timeline. I push back respectfully: "Happy to do a POC — can we align on success criteria and who will make the decision based on results?"
