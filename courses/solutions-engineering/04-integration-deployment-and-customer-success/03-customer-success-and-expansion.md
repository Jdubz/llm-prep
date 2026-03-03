# 03 -- Customer Success and Expansion

The deal is closed and the product is deployed. Now the real work begins: keeping the customer healthy, expanding the footprint, and preventing churn. SEs and FDEs play a critical role in the post-sale lifecycle — you have the technical relationships and product depth that Customer Success Managers often lack. This file covers the frameworks and playbooks for turning a deployed customer into a growing, referenceable account.

---

## Customer Health Scoring

### What Health Metrics to Track

Customer health is not a feeling — it is a composite score built from measurable signals. The best health models combine product usage data with relationship signals and business signals.

| Metric Category | Metric | Signal | Weight |
|----------------|--------|--------|--------|
| **Product Usage** | DAU/MAU ratio | Engagement depth | High |
| **Product Usage** | Feature adoption (% of purchased features used) | Value realization | High |
| **Product Usage** | API call volume trend (30d) | Integration health | Medium |
| **Product Usage** | Login frequency | Mindshare | Medium |
| **Support** | Support ticket volume (30d) | Pain level | Medium |
| **Support** | Ticket severity distribution | Issue severity | High |
| **Support** | Average resolution time | Support experience | Medium |
| **Support** | Escalation count | Frustration level | High |
| **Relationship** | NPS score (last survey) | Sentiment | High |
| **Relationship** | Executive sponsor engagement | Top-down support | High |
| **Relationship** | Champion status (still at company?) | Advocate presence | Critical |
| **Relationship** | Days since last meaningful contact | Engagement recency | Medium |
| **Business** | Days to renewal | Urgency | High |
| **Business** | Contract value trend | Growth trajectory | Medium |
| **Business** | Expansion conversations active | Pipeline signal | Medium |
| **Business** | Competitor mentions in tickets/calls | Risk signal | High |

### Building a Health Score

**Step 1: Normalize each metric to 0-100**

For each metric, define what "healthy" and "unhealthy" look like:
- DAU/MAU ratio: 0.3+ = 100 (healthy), < 0.05 = 0 (critical)
- Support tickets per month: 0-2 = 100, 3-5 = 70, 6-10 = 40, 11+ = 10
- Days since last contact: 0-14 = 100, 15-30 = 70, 31-60 = 40, 61+ = 10

**Step 2: Apply weights and compute composite score**

```
Health Score = Σ (metric_score × weight) / Σ weights
```

**Step 3: Map to RAG (Red/Amber/Green) status**

| Score Range | Status | Action |
|-------------|--------|--------|
| 80-100 | Green | Maintain cadence, explore expansion |
| 60-79 | Amber | Increase engagement, address specific concerns |
| 40-59 | Red | Intervention required, escalate internally |
| 0-39 | Critical | Executive involvement, churn risk imminent |

### Leading vs Lagging Indicators

| Leading (predict the future) | Lagging (confirm the past) |
|------------------------------|---------------------------|
| Declining login frequency | Churn |
| Champion job change | Failed renewal |
| Feature adoption stalling | Support escalation |
| Reduced API call volume | Contract downgrade |
| No response to outreach | NPS drop |
| Competitor evaluation started | Lost account |

Focus your health model on leading indicators. By the time lagging indicators fire, it is often too late.

---

## Quarterly Business Reviews (QBRs)

### What a QBR Is

A QBR is a structured meeting (typically 60-90 minutes) between your team and the customer's stakeholders to review the business relationship. It happens quarterly (hence the name) and serves as the primary cadence for strategic alignment.

**Who attends:**

| Your Side | Customer Side |
|-----------|--------------|
| Account Executive (AE) | Executive sponsor / VP |
| Solutions Engineer (SE) | Technical lead / architect |
| Customer Success Manager (CSM) | Project manager |
| (Optional) Product Manager | (Optional) End users / champions |

### QBR Structure

A well-run QBR follows this flow in 60-90 minutes:

**1. Business Review (15 min)**
- Usage metrics and trends (up/down/flat)
- ROI summary: what measurable value has the product delivered?
- Comparison to success criteria from the original deal

**2. Technical Review (15 min)**
- Integration health: uptime, error rates, performance
- Support ticket summary: themes, resolution times, open issues
- Infrastructure changes or upcoming migrations that affect the product

**3. Roadmap Alignment (15 min)**
- Your product roadmap highlights relevant to this customer
- Customer's roadmap and how your product supports it
- Feature requests from this customer and their status

**4. Success Planning (10 min)**
- Goals for the next quarter
- Identified risks and mitigation plans
- Action items from the previous QBR — are they closed?

**5. Expansion Discussion (10-15 min)**
- New use cases identified
- New teams or departments that could benefit
- Licensing or tier changes to discuss
- Upcoming renewal terms (if within 2 quarters)

### QBR Preparation Checklist

**One week before:**
- [ ] Pull usage analytics for the quarter (dashboards, reports)
- [ ] Summarize support ticket activity (volume, themes, open items)
- [ ] Review product roadmap for features relevant to this customer
- [ ] Check on feature requests this customer has submitted
- [ ] Review action items from last QBR
- [ ] Prepare ROI talking points (tie usage to business outcomes)
- [ ] Identify expansion opportunities to discuss
- [ ] Draft the slide deck or agenda document
- [ ] Align with AE on commercial topics (renewal, expansion pricing)

**Day of:**
- [ ] Confirm attendance (do not run a QBR without the executive sponsor)
- [ ] Test screen sharing and any live demos
- [ ] Have backup slides for sensitive topics (churn risk, pricing)

### Common QBR Mistakes

1. **Making it a product demo.** QBRs are business reviews, not sales meetings.
2. **Not having executive attendance.** If the customer's VP is not there, the QBR has limited strategic value. Reschedule.
3. **Ignoring bad news.** If usage is declining, say so. Propose a plan. Pretending everything is fine erodes trust.
4. **No action items.** Every QBR should end with clear next steps, owners, and deadlines.
5. **Running over time.** Respect the time commitment. If you need more time, schedule a follow-up.
6. **Not following up.** Send a summary email within 24 hours with action items and owners.

### How SEs Contribute to QBRs

The SE brings the technical credibility that CSMs often lack. Your role in a QBR:
- Present the technical review section with data
- Answer technical questions about product capabilities and roadmap
- Identify expansion opportunities based on the customer's technical architecture
- Propose solutions for issues surfaced during the support review
- Validate that the customer's technical team is getting value

---

## Expansion Playbooks

### Identifying Expansion Opportunities

Expansion revenue (growing existing accounts) is typically 2-3x cheaper than acquiring new customers. As an SE, you are uniquely positioned to spot expansion opportunities because you understand the customer's technical architecture.

**Five expansion vectors:**

| Vector | Signal | Example |
|--------|--------|---------|
| **New use cases** | Customer asks "can your product also do X?" | Customer using your API gateway wants to add rate limiting |
| **New teams** | Another department hears about the deployment | Marketing team wants what Engineering is using |
| **New geographies** | Customer expanding to new regions | EU expansion requires a new deployment |
| **Platform upgrades** | Customer hitting limits on current tier | Usage approaching tier limits, need Enterprise plan |
| **Additional products** | Customer asks about related products in your portfolio | Using your analytics tool, now interested in your data pipeline |

### The Land-and-Expand Motion

```
Land (initial deal) → Prove Value → Identify Expansion → Propose → Close Expansion
     AE + SE              SE/FDE/CSM       SE/CSM            AE + SE      AE
```

**Phase 1: Land** — Win the initial deal. Typically one team, one use case, limited scope.

**Phase 2: Prove Value** — Deliver on the promises made during the sale. Ensure the initial deployment is successful, healthy, and delivering measurable ROI.

**Phase 3: Identify Expansion** — Through QBRs, support interactions, and ongoing technical conversations, identify where the customer could get more value.

**Phase 4: Propose** — Build an expansion proposal that ties the new scope to business outcomes. Include: what changes, why it matters, what it costs, and what the implementation looks like.

**Phase 5: Close Expansion** — The AE drives the commercial conversation. The SE supports with technical validation.

### Upsell vs Cross-Sell

| | Upsell | Cross-Sell |
|--|--------|-----------|
| **What** | More of the same product (higher tier, more seats, more capacity) | A different product in your portfolio |
| **Signal** | Usage approaching limits, team growing, new use cases for same product | Customer mentions a pain that another product solves |
| **Difficulty** | Lower — they already know and trust the product | Higher — need to prove value of something new |
| **SE role** | Show them the value of upgraded features, help them understand tier differences | Run a mini-discovery and demo for the new product |

### When to Involve an AE

Involve the AE when:
- The expansion involves a pricing change or new contract
- The customer has asked about pricing directly
- The expansion would add more than 20% to the contract value
- There is a competitive threat (expand before they evaluate alternatives)
- The renewal is within 2 quarters (expansion and renewal may be negotiated together)

Do NOT involve the AE when:
- You are still in discovery mode (understanding the opportunity)
- The customer is expressing frustration (solve the problem first, then expand)
- The expansion is purely technical (adding a feature within their current tier)

### Building an Expansion Proposal

An expansion proposal is a short document (1-2 pages) that makes the case for expansion.

**Structure:**
1. **Current State**: What they have today, how they use it, what results they are getting
2. **Opportunity**: What additional value is available (new use case, new team, upgrade)
3. **Proposed Solution**: What specifically changes (tier upgrade, new deployment, additional licenses)
4. **Expected Outcomes**: Measurable business benefits of the expansion
5. **Implementation Plan**: How long it takes, what is required from both sides
6. **Investment**: What it costs (the AE refines the commercial terms)

---

## Churn Prevention

### Early Warning Signals

| Signal | Severity | Lead Time |
|--------|----------|-----------|
| Product usage declining for 3+ consecutive weeks | High | 2-3 months |
| Support ticket escalation to VP/exec level | High | 1-2 months |
| Champion leaves the company | Critical | 1-3 months |
| Customer takes a meeting with a competitor | Critical | 1-2 months |
| NPS score drops below 6 | High | 2-4 months |
| Customer stops attending QBRs | Medium | 3-6 months |
| API integration error rate spikes and nobody reports it | Medium | Variable |
| Customer's budget cycle approaching with no renewal discussion | High | 1-2 months |
| New CTO/VP of Engineering hired (not your champion) | High | 2-4 months |

### Churn Intervention Playbook

When a customer is at risk, act immediately. Every week you wait reduces the probability of saving the account.

**Step 1: Triage (Day 1-2)**
- Identify the root cause: is it product, relationship, pricing, or competitive?
- Review health score and all recent interactions
- Align internally: AE, CSM, SE, and management should all know

**Step 2: Outreach (Day 3-5)**
- Contact your champion (if still there) for an honest conversation
- Contact the executive sponsor directly if appropriate
- Do NOT send a generic "checking in" email. Be direct: "I want to make sure you're getting value from [product]. Can we schedule 30 minutes to discuss?"

**Step 3: Diagnose (Week 1-2)**
- Run a focused session to understand the specific complaints
- Separate solvable problems from fundamental mismatches
- Identify what would need to change for them to renew with confidence

**Step 4: Act (Week 2-4)**
- For product issues: escalate to engineering, provide timeline for fix, offer workaround
- For relationship issues: change the CSM or SE assigned to the account
- For pricing issues: involve the AE to discuss restructured terms
- For competitive issues: run a competitive response (win-back demo, feature comparison)

**Step 5: Follow up (Ongoing)**
- Increase touch frequency (weekly for at-risk accounts)
- Track progress against the specific issues identified
- Report status to your management

### The "Save Call" Format

When you need to have a direct conversation with an at-risk customer:

1. **Open with empathy**: "I know things haven't been going as well as either of us would like."
2. **State what you know**: "We've seen usage decline and I understand you've had frustrations with [specific issue]."
3. **Ask for their perspective**: "I want to hear from you what would need to change for this to be a successful partnership."
4. **Listen**: Do not defend. Take notes. Ask clarifying questions.
5. **Commit to a plan**: "Here's what I'm going to do by [date]. Can we schedule a follow-up for [date]?"
6. **Follow through**: Do exactly what you said. Report back on time.

---

## Implementation-to-Success Transition

### The Handoff

The transition from implementation (SE/FDE-led) to ongoing customer success (CSM-led) is where many accounts stumble. The technical context that the SE/FDE has must be transferred to the CS team.

**What documentation to produce:**

| Document | Audience | Content |
|----------|----------|---------|
| **Technical handoff doc** | CSM + Support | Architecture diagram, integration points, auth setup, key contacts |
| **Success criteria status** | CSM | Original criteria from the deal, current status of each |
| **Known issues log** | CSM + Support | Open bugs, workarounds, expected resolution dates |
| **Customer contact map** | CSM | Key stakeholders, their roles, their communication preferences |
| **Escalation guide** | Support | When to escalate, to whom, and what context to include |

### Training the CS Team

The CSM does not need to be able to debug the integration, but they need to:
1. Understand what the customer is using at a high level
2. Know which metrics to watch (and what "normal" looks like)
3. Recognize when something is a product issue vs a customer config issue
4. Know who to escalate to for technical questions (the SE stays in the loop)

Run a 30-minute handoff meeting:
- Walk through the architecture at a high level
- Show the health metrics dashboard and what "normal" looks like
- Review the customer contact map and relationship dynamics
- Identify the top 3 risks going forward

### Establishing Ongoing Support Expectations

At the end of implementation, set clear expectations with the customer:
- **Who is their primary contact now?** (CSM, not SE)
- **How do they report issues?** (Support portal, not Slack DM to the SE)
- **What is the support SLA?** (Response times by severity)
- **When is the first QBR?** (Schedule it before the handoff)
- **How will the SE stay involved?** (QBRs, technical escalations, expansion discussions)

---

## Customer Advocacy

### Turning Customers into References

A referenceable customer is one of the most valuable assets in enterprise sales. Prospects trust other customers more than they trust your marketing.

**The advocacy ladder:**

```
Happy User → Internal Champion → Public Reference → Case Study → Speaker → Advisory Board
```

Each step requires more commitment from the customer and delivers more value to your company.

### Case Study Creation

**When to ask:** After the customer has been live for 6+ months, has measurable results, and has a positive relationship with your team.

**How to ask:** "We've been really proud of the results you've achieved. Would you be open to co-creating a case study? It would highlight your team's work and the outcomes you've delivered."

**Case study structure:**
1. **Challenge**: What problem were they trying to solve?
2. **Solution**: How did your product help? What was the implementation like?
3. **Results**: Measurable outcomes (percentages, time saved, revenue impact)
4. **Quote**: A direct quote from the champion or executive sponsor

**Tips:**
- Make it easy for the customer. You write the draft; they review and approve.
- Include their logo and a headshot of the quoted person.
- Let them review for accuracy and legal/PR approval.
- Share the finished case study with them — they will promote it internally.

### Customer Advisory Boards

A Customer Advisory Board (CAB) is a group of 10-20 strategic customers who meet quarterly (usually virtually, once annually in person) to provide feedback on product direction and industry trends.

**Value for the customer:**
- Direct influence on your product roadmap
- Networking with peers at other companies
- Early access to new features and betas
- Recognition as a strategic partner

**Value for your company:**
- Candid product feedback from power users
- Deeper relationships with strategic accounts
- Customer-driven use cases for marketing and sales
- Reduced churn risk (advisory board members rarely churn)

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 4: Customer Health Scorer** -- Applies the health scoring framework from "Customer Health Scoring." You will compute a composite health score from multiple metrics, classify risk levels, and generate recommended actions based on leading indicators.
- **Exercise 5: QBR Preparation Builder** -- Applies the QBR structure and preparation checklist from "Quarterly Business Reviews." You will generate a QBR agenda with talking points, risk items, and expansion opportunities from customer account data.
- **Exercise 6: Expansion Opportunity Identifier** -- Applies the expansion vectors and land-and-expand framework from "Expansion Playbooks." You will identify and rank expansion opportunities based on current deployment details and customer organization info.

See also `examples.py`:
- `HealthScoreCalculator` (Section 4) -- multi-signal health scoring with trend analysis
- `QBRDocumentGenerator` (Section 5) -- complete QBR preparation tool with slide content

---

## Interview Q&A: Customer Success and Expansion

**Q: How would you build a customer health scoring system?**

I would build a composite score from three categories of signals: product usage, support health, and relationship strength. For product usage, I track DAU/MAU ratio, feature adoption percentage, and API call volume trends — these tell me whether the customer is actively getting value. For support health, I track ticket volume, severity distribution, and escalation count — rising escalations are a leading indicator of churn. For relationship health, I track NPS scores, champion status (are they still at the company?), and days since last meaningful contact. I normalize each metric to a 0-100 scale, apply weights (product usage and champion status get the highest weights because they are the strongest predictors), and compute a composite score. Green is 80+, amber is 60-79, red is below 60. The critical insight is focusing on leading indicators — by the time a customer churns, you have missed months of warning signals.

**Q: Walk me through how you would prepare for and run a QBR.**

I start preparation a week before. I pull usage analytics for the quarter — trends matter more than absolutes, so I look at growth or decline in adoption. I summarize support tickets: how many, what themes, what is still open. I review the product roadmap for features this customer cares about and check on any feature requests they have submitted. I review action items from the last QBR — nothing destroys credibility faster than coming back with the same unresolved items. I draft a slide deck following a five-section structure: business review (usage + ROI), technical review (integration health + support), roadmap alignment, success planning for next quarter, and an expansion discussion. On the day, I confirm the customer's executive sponsor will attend — if they cannot make it, I strongly consider rescheduling. During the QBR, I let the data tell the story. If things are going well, I pivot to expansion. If there are issues, I acknowledge them directly and present a plan. I end with clear action items, owners, and deadlines, and I send a follow-up email within 24 hours.

**Q: A customer's usage has been declining for two months and renewal is in 90 days. What do you do?**

I treat this as a churn risk and act immediately. First, I triage: I review the health score, recent support tickets, and any changes at the account — did their champion leave? Did they hire a new CTO? Is there a competitor evaluation? I align internally with the AE, CSM, and my manager so everyone is on the same page. Then I reach out directly — not with a generic check-in but with a specific observation: "I've noticed your team's usage of [specific feature] has declined over the past two months. I want to make sure you're getting the value you need. Can we schedule 30 minutes to discuss?" In that conversation, I listen more than I talk. I want to understand the root cause: is it a product issue, a people issue (champion left), a budget issue, or a competitive issue? Each has a different intervention. For product issues, I escalate to engineering with a timeline. For relationship issues, I consider changing the assigned CSM. For competitive threats, I run a win-back motion with a focused demo showing capabilities they may not be using. The key is speed and specificity — at 90 days to renewal, every week matters.
