# Module 00: Role Landscape and Prerequisites

Everything you need to understand before the rest of this course makes sense. You build software — this module gives you the vocabulary, mental models, and career context for client-facing technical roles so the discovery frameworks, POC patterns, and stakeholder strategies in later modules have grounding.

No sales jargon without definition. No hand-waving. Just the foundations.

---

## 1. The Three Roles

### Solutions Engineer (SE)

The SE is the technical counterpart to the Account Executive (AE) in a sales organization. You own the **technical win** — proving to prospects that the product solves their problem.

**Core responsibilities:**
- Run technical discovery calls to understand customer pain, architecture, and constraints
- Design and deliver product demos tailored to the prospect's specific use case
- Scope and execute Proof of Concepts (POCs) with measurable success criteria
- Write technical proposals, architecture documents, and RFP responses
- Handle technical objections and competitive positioning
- Serve as the voice of the customer to product and engineering teams

**Typical day:**
- 2-3 customer-facing meetings (discovery calls, demos, POC check-ins)
- Internal syncs with AEs on deal strategy
- Building custom demo environments or POC configurations
- Writing follow-up documentation (architecture diagrams, integration guides)
- Product feedback sessions with PM/engineering

**Where SEs sit in the org:**
```
CRO / VP Sales
  ├── AE Team (owns the relationship, quota, contract)
  ├── SE Team (owns the technical win, POCs, demos)
  └── Sales Ops / Enablement
```

SEs typically report into sales (not engineering), though some orgs have SE teams under a VP of Solutions or CTO office.

### Sales Engineer

In many companies, "Sales Engineer" and "Solutions Engineer" are interchangeable titles. When they differ, Sales Engineers tend to:

- Work in more traditional enterprise software (Oracle, Cisco, Salesforce)
- Focus more on product configuration and less on custom code
- Engage earlier and more broadly in the sales cycle
- Carry more demos and fewer POCs
- Have deeper product expertise, somewhat less custom integration work

The distinction is vanishing. Most modern SaaS companies use "Solutions Engineer" or "Solutions Architect." This course treats the skills as identical and notes where specific industries diverge.

### Forward Deployed Engineer (FDE)

The FDE is a software engineer embedded with customers. Coined and popularized by Palantir, the role has spread to companies like Anduril, Scale AI, Databricks, and many AI/ML startups.

**Core responsibilities:**
- Ship production code in the customer's environment (or a shared integration layer)
- Build custom integrations, data pipelines, and workflows
- Translate customer requirements into working software on tight timelines
- Navigate unfamiliar codebases, tech stacks, and organizational processes
- Scope technical projects and manage their delivery independently
- Bridge the gap between "product as sold" and "product as needed"

**How FDE differs from SE:**

| Dimension | SE | FDE |
|-----------|-----|-----|
| Primary output | Technical win (pre-sale) | Working software (post-sale or embedded) |
| Code production | Demo/POC code | Production code in customer env |
| Customer interaction | Sales cycle meetings | Embedded in customer team |
| Timeline | Deal cycle (weeks-months) | Engagement (months-quarters) |
| Tech depth | Broad (product + integrations) | Deep (customer stack + product) |
| Reports to | Sales org | Engineering or Solutions org |
| Quota | Team or overlay quota | Usually no quota |

**How FDE differs from a typical SWE:**

You are a software engineer — but your requirements come from customers, not a PM. Your deadlines are set by contracts, not sprint planning. Your stakeholders are external, your codebase is someone else's, and your success is measured in customer outcomes, not PRs merged.

---

## 2. Career Paths

### Into SE/FDE

```
SWE (2-4 years)  ──→  SE or FDE
                          │
DevRel / Developer Advocate ──→  SE
                          │
Technical Support / TAM   ──→  SE
                          │
Consultant / SI Engineer  ──→  FDE
```

The most common path is SWE → SE or SWE → FDE. The transition values:
- Technical credibility (you can actually build things)
- Communication skills (you can explain what you build)
- Customer empathy (you care about the person using the software, not just the code)

### From SE/FDE

```
SE / FDE
  ├── Senior SE → Principal SE → SE Director → VP Solutions
  ├── SE → Product Manager (deep customer insight is a PM superpower)
  ├── SE → Engineering Manager (technical leadership + people skills)
  ├── FDE → Staff Engineer (deep technical + cross-functional experience)
  ├── SE → Sales (AE, if you want to carry a quota)
  ├── SE → Solutions Architect (enterprise architecture focus)
  └── SE / FDE → Startup Founder (you've seen what customers actually need)
```

### Compensation Landscape

SE/FDE compensation is highly variable by company, stage, and industry. Rough ranges for US-based roles:

| Level | Base | Variable/Bonus | Total |
|-------|------|----------------|-------|
| Junior SE | $100-130K | $20-40K | $120-170K |
| Mid SE | $130-170K | $40-80K | $170-250K |
| Senior SE | $160-200K | $60-120K | $220-320K |
| Principal/Staff SE | $180-230K | $80-150K | $260-380K |
| FDE (startup) | $140-200K | Equity-heavy | $180-350K+ |
| FDE (big tech) | $160-220K | RSUs + bonus | $250-400K+ |

SEs at quota-carrying companies have significant variable compensation (40-60% of OTE). FDEs typically have standard engineering comp structures with equity.

---

## 3. The SE/FDE Mindset

### Customer Empathy is Not Optional

The biggest failure mode for engineers transitioning to SE/FDE: treating customers as "users who should read the docs." Customers are:

- Under pressure from their own stakeholders to solve a business problem
- Evaluating your product alongside 2-5 competitors simultaneously
- Not experts in your product (that's why they're talking to you)
- Often not the final decision-maker (they need to sell internally too)

Your job is to make them successful, not to demonstrate how smart you are.

### Business Acumen Basics

You don't need an MBA, but you need to understand:

**Revenue concepts:**
- **ARR** (Annual Recurring Revenue): the annual value of a subscription contract
- **ACV** (Annual Contract Value): the yearly value of a specific deal
- **TCV** (Total Contract Value): full value over the contract term (ACV × years)
- **Expansion**: growing revenue within existing accounts (upsell, cross-sell)
- **Churn**: revenue lost when customers don't renew

**Sales concepts:**
- **Pipeline**: all deals being actively worked, weighted by probability
- **Quota**: the revenue target an AE (and sometimes SE) is responsible for
- **Win rate**: percentage of deals that close (technical win rate for SEs)
- **Deal cycle**: time from first meeting to signed contract
- **Champion**: the person inside the prospect org who wants your product to win
- **Economic buyer**: the person who signs the check

**Why this matters for SEs**: Every technical decision you make in a deal has business implications. Recommending a longer POC may increase win probability but slows the deal cycle. Designing an integration that requires the customer's engineering team creates a dependency that affects timeline. Understanding these tradeoffs makes you a strategic partner to your AE, not just a "demo jockey."

### Technical Breadth Over Depth

SEs need to go "one mile wide and one foot deep" across many technologies, then drill down when a specific customer requires it. You need working knowledge of:

- **Cloud platforms**: AWS, GCP, Azure (services, pricing models, compliance)
- **Authentication**: OAuth 2.0, SAML, SSO, API keys, JWTs
- **Data**: SQL/NoSQL databases, data warehouses, ETL pipelines, streaming
- **APIs**: REST, GraphQL, gRPC, webhooks, rate limiting
- **Infrastructure**: Containers, Kubernetes, CI/CD, monitoring
- **Security**: Encryption at rest/in transit, compliance frameworks (SOC 2, HIPAA, GDPR)
- **Your product**: deeper than anyone else in the room

---

## 4. The Sales Cycle (SE's Perspective)

Understanding where you are in the sales cycle determines what you should be doing.

```
Prospecting → Discovery → Demo → Technical Validation → Proposal → Negotiation → Close
    AE          SE+AE      SE       SE (POC/eval)        SE+AE      AE+SE       AE
```

| Stage | SE's Role | Key Deliverable |
|-------|-----------|-----------------|
| **Prospecting** | Light involvement — help AE with technical positioning | One-pager, battle card |
| **Discovery** | Run technical discovery, understand architecture and pain | Discovery notes, technical requirements |
| **Demo** | Deliver tailored demo showing the prospect's use case | Demo environment, talk track |
| **Technical Validation** | Scope and execute POC, handle objections | POC plan, success criteria, results doc |
| **Proposal** | Write technical sections of proposal, architecture docs | Technical proposal, integration plan |
| **Negotiation** | Clarify technical scope, defend architecture decisions | SOW review, scoping |
| **Close** | Support final technical questions | Handoff doc to CS/implementation |

---

## 5. Key Frameworks Preview

These frameworks are covered in depth in later modules. Knowing the names and one-liners here gives you context.

| Framework | What It Is | Module |
|-----------|-----------|--------|
| **SPIN Selling** | Situation → Problem → Implication → Need-Payoff discovery | Module 01 |
| **MEDDPICC** | Deal qualification: Metrics, Economic Buyer, Decision Criteria/Process, Paper Process, Identify Pain, Champion, Competition | Module 01 |
| **BANT** | Budget, Authority, Need, Timeline — simpler qualification | Module 01 |
| **Challenger Sale** | Teaching customers something new about their business | Module 01 |
| **Value Selling** | Linking features to measurable business outcomes | Module 01 |
| **RFC 2119** | The language of technical requirements (MUST, SHOULD, MAY) | Module 02 |
| **RACI** | Responsible, Accountable, Consulted, Informed — stakeholder roles | Module 03 |
| **STAR** | Situation, Task, Action, Result — behavioral interview format | Module 07 |

---

## 6. Tools of the Trade

### SE Toolchain

| Category | Tools |
|----------|-------|
| **CRM** | Salesforce, HubSpot |
| **Demo environment** | Custom instances, Reprise, Walrus, Navattic |
| **Diagramming** | Mermaid, Excalidraw, Lucidchart, draw.io |
| **Collaboration** | Notion, Confluence, Google Docs |
| **Communication** | Slack, Teams, Zoom, Loom |
| **Ticket tracking** | Jira, Linear, Shortcut |
| **API testing** | Postman, Insomnia, curl/httpie |
| **Code sharing** | GitHub, GitLab, Replit |

### FDE Toolchain (same as above plus)

| Category | Tools |
|----------|-------|
| **Customer code** | Whatever they use (you adapt) |
| **Infrastructure** | Terraform, CloudFormation, Pulumi |
| **CI/CD** | GitHub Actions, Jenkins, CircleCI, ArgoCD |
| **Monitoring** | Datadog, Grafana, PagerDuty |
| **Data** | dbt, Airflow, Spark, Snowflake |

---

## 7. Quick Checklist

Before starting Module 01, you should be comfortable with:

- [ ] What does an SE do day-to-day? How is it different from a SWE role?
- [ ] What is the difference between an SE and an FDE?
- [ ] What is ARR, ACV, and why do SEs care about revenue metrics?
- [ ] What is a "technical win" and how does it differ from closing a deal?
- [ ] What is MEDDPICC at a high level? (details in Module 01)
- [ ] What does the sales cycle look like from an SE's perspective?
- [ ] Why is customer empathy the most important SE skill?
- [ ] Can you name 5 technology areas where SEs need working knowledge?
- [ ] What is a champion? What is an economic buyer?
- [ ] Do you understand the difference between base, variable, and OTE compensation?

If any of these feel unclear, re-read that section. Module 01 builds directly on all of them.

---

## Related Reading

- [General Interview Course](../general-interview/README.md) — behavioral interview preparation, negotiation frameworks, and system design fundamentals that apply to SE/FDE interviews
- [LLM Engineering Course](../llms/README.md) — if preparing for AI/ML SE roles, Module 06 of this course references LLM concepts covered there
- [Infrastructure Course](../infrastructure/README.md) — cloud, networking, and deployment concepts that SEs discuss with customers daily

---

## Next Steps

You're ready for [Module 01: Discovery and Technical Sales](01-discovery-and-technical-sales/01-discovery-methodology.md) — the foundation of every SE interaction.
