# 02 -- Mock Scenarios and System Design for SEs

This file contains full mock discovery call scenarios with scoring rubrics, the SE system design framework, complete system design walkthroughs, and demo interview preparation guidance. Every scenario is designed to be practiced out loud, timed, and scored.

---

## Mock Discovery Call Scenario 1: Enterprise SaaS — Data Platform Migration

### Customer Profile

| Field | Detail |
|-------|--------|
| **Company** | Meridian Financial Services |
| **Industry** | Financial services / Fintech |
| **Size** | 2,500 employees, $400M annual revenue |
| **Your contact** | Rachel Kim, VP of Data Engineering |
| **Other stakeholders** | CTO (budget holder, not on this call), Lead Data Engineer (technical evaluator), Head of Compliance (lurking concern) |
| **Current stack** | On-prem Hadoop cluster, custom ETL in Java, Tableau for reporting, Oracle data warehouse |
| **Stated need** | "We want to modernize our data platform and move to the cloud" |
| **Actual pain** | Their Hadoop cluster is 7 years old, the 2 engineers who built it have left, nobody can maintain the custom ETL pipelines, and reports are 48 hours stale. Compliance is increasingly nervous about data lineage for SOX audits. |
| **Hidden concerns** | Rachel was hired 6 months ago specifically to lead this migration. If she doesn't show progress by Q3, the board will question the investment in her team. The CTO is skeptical of cloud — he was burned by a failed AWS migration at a previous company. |
| **Budget** | $500K allocated for Year 1, but procurement requires 3 bids. They have already talked to one competitor. |
| **Timeline** | Board review in Q3 (5 months away). Rachel needs a POC completed before then. |

### Mock Script

**You (SE):** [Open the call]

**Rachel:** "Thanks for taking the time. We're exploring options to modernize our data platform. We've been running on Hadoop for years and it's time to move to the cloud. I'd love to understand what you offer."

At this point, a good SE does NOT start talking about the product. A good SE asks questions.

**Target questions you should ask (in approximate order):**

1. "Can you walk me through your current data architecture — from source systems through to the reporting layer?"
2. "What's driving the timing of this migration? Is there a specific event or deadline?"
3. "You mentioned Hadoop has been running for years — what's working well, and what's causing the most pain?"
4. "Who maintains the ETL pipelines today? What happens when something breaks?"
5. "How stale is your reporting data right now? And what decisions depend on that data being fresh?"
6. "You mentioned cloud — have you selected a cloud provider, or is that part of the evaluation?"
7. "What does your compliance and audit process look like for data lineage? Is that a concern for you?"
8. "Who else is involved in this decision? Will your CTO or compliance team need to evaluate the solution?"
9. "What other solutions have you looked at so far? What did you like or not like?"
10. "If this migration is successful, what does 'great' look like 12 months from now?"

**Rachel's responses (for role-play practice):**

- Q1: "We pull from Oracle, Salesforce, and a few internal APIs. Everything runs through custom Java ETL into Hadoop. Tableau connects to Hadoop for reporting. It's... fragile."
- Q2: "Our board wants to see cloud progress by Q3. I was brought in to lead this."
- Q3: "It processes the data, but when pipelines break — which is weekly — it takes days to fix. The two engineers who built it left last year."
- Q4: "My team of three is maintaining it, but none of them wrote the original code. We spend 60% of our time on maintenance."
- Q5: "Reports are 48 hours stale on a good day. Our risk team is making decisions on data that's two days old."
- Q6: "We're leaning AWS, but haven't committed. Our CTO had a bad experience with a cloud migration before and wants to see proof it'll work before committing."
- Q7: "SOX compliance is huge for us. We need to show auditors exactly where data came from and every transformation it went through. Today we can't do that reliably."
- Q8: "My CTO owns the budget. He'll want to see a POC before approving anything. Compliance will review the security and lineage capabilities."
- Q9: "We talked to [Competitor X] last week. Their platform looks solid but their pricing model scared us — it's usage-based and hard to predict."
- Q10: "Great looks like: real-time reporting, zero maintenance ETL, full lineage for SOX, and my team building new things instead of firefighting."

### Evaluation Rubric

| Dimension | Excellent (9-10) | Good (6-8) | Needs Work (1-5) |
|-----------|-----------------|-----------|-----------------|
| **Questions asked** | 8+ open-ended questions covering pain, stakeholders, timeline, competition, success criteria | 5-7 questions, mostly relevant | < 5 questions, or mostly closed-ended/leading |
| **Pain identification** | Identified maintenance burden, stale data, compliance risk, AND Rachel's personal stake | Identified 2-3 pain points | Identified 1 or missed the real pain |
| **Stakeholder mapping** | Identified CTO as budget holder, compliance as gate, Rachel as champion, understood CTO's skepticism | Identified 2 of 3 key stakeholders | Did not ask about other stakeholders |
| **Listening** | Paraphrased what Rachel said, asked follow-ups, 30/70 talk/listen ratio | Mostly listened, some follow-ups | Talked more than listened, interrupted, or moved on too quickly |
| **Technical credibility** | Asked technically relevant questions about ETL complexity, data volume, Hadoop version | Some technical questions | No technical depth in questions |
| **Next steps** | Proposed a specific next step (tailored demo for Rachel + CTO, or a scoped POC) with a date | Proposed a vague next step | No next step, or proposed a generic product overview |
| **Rapport** | Professional, empathetic, referenced Rachel's specific situation | Friendly and professional | Robotic, or overly casual, or salesy |

---

## Mock Discovery Call Scenario 2: AI/ML Startup — Customer Support Automation

### Customer Profile

| Field | Detail |
|-------|--------|
| **Company** | NovaBright (Series B SaaS startup) |
| **Industry** | B2B SaaS — project management software |
| **Size** | 300 employees, 5,000 business customers, $40M ARR |
| **Your contact** | David Chen, Head of Customer Experience |
| **Other stakeholders** | VP of Engineering (technical veto power), CEO (wants to see AI impact metrics) |
| **Current stack** | Zendesk for ticketing, internal knowledge base in Confluence, customer data in Postgres, React frontend |
| **Stated need** | "We want to use AI to automate our customer support" |
| **Actual pain** | Support ticket volume has grown 3x in 12 months. They've hired from 8 to 20 agents but still have a 6-hour average first response time. CSAT has dropped from 4.5 to 3.8. Churn is correlated with poor support experiences. |
| **Hidden concerns** | David promised the CEO that AI would reduce headcount by 30%. The VP of Engineering is skeptical of AI accuracy and worried about hallucinated answers damaging customer relationships. Data quality in Confluence is poor — half the articles are outdated. |
| **Budget** | $150K Year 1. CEO expects measurable ROI within 6 months. |
| **Timeline** | Board meeting in 8 weeks. CEO wants to show "AI progress." |

### Target Discovery Questions

1. "Walk me through a typical support ticket lifecycle — from when a customer submits it to resolution."
2. "What types of tickets make up the majority of your volume? Are there categories you could group them into?"
3. "When you say 'automate,' what does that mean to you — full deflection without a human, or assisted responses that agents review?"
4. "How accurate does the AI need to be before you'd trust it to respond directly to customers?"
5. "Tell me about your knowledge base. How current is it? How do agents use it today?"
6. "What happens when an AI gives a wrong answer to a customer? What's the blast radius?"
7. "Who needs to be comfortable with this before it goes live? Is your VP of Engineering involved in the evaluation?"
8. "What does success look like in 6 months? Are there specific metrics the CEO is tracking?"
9. "Have you tried any AI solutions already — even just ChatGPT or internal experiments?"
10. "What's your data situation like? Do you have labeled examples of good vs bad support responses?"

### Evaluation Rubric

| Dimension | Excellent (9-10) | Good (6-8) | Needs Work (1-5) |
|-----------|-----------------|-----------|-----------------|
| **AI-specific questions** | Asked about data quality, accuracy thresholds, hallucination risk, human-in-the-loop | Asked about some AI readiness | No AI-specific questions |
| **Expectation management** | Probed the "30% headcount reduction" expectation and set realistic expectations | Addressed some expectations | Agreed with unrealistic expectations, or didn't explore them |
| **Data readiness** | Identified Confluence quality issue, asked about labeled data, volume patterns | Some data questions | Didn't explore data readiness |
| **Risk awareness** | Discussed wrong-answer risk, customer impact, and phased rollout | Some risk awareness | No discussion of AI risks |

---

## Mock Discovery Call Scenario 3: Healthcare — Compliance-Heavy Integration

### Customer Profile

| Field | Detail |
|-------|--------|
| **Company** | Pacific Health Network (regional hospital network) |
| **Industry** | Healthcare |
| **Size** | 12 hospitals, 15,000 employees, $2.8B annual revenue |
| **Your contact** | Dr. Sarah Martinez, Chief Medical Informatics Officer (CMIO) |
| **Other stakeholders** | CISO (security gate), CFO (budget), IT Director (implementation lead), clinical staff (end users) |
| **Current stack** | Epic EHR, on-prem data warehouse, custom HL7/FHIR interfaces, Citrix for remote access |
| **Stated need** | "We need a better way to share patient data across our network for care coordination" |
| **Actual pain** | Patients who visit multiple facilities in the network have fragmented records. Clinicians waste 20 minutes per patient looking up records in different systems. Duplicate tests are ordered because results from other facilities aren't visible. This costs the network an estimated $12M annually in duplicate diagnostics. |
| **Hidden concerns** | They had a data breach 18 months ago that resulted in a $2M OCR fine. The CISO will block anything that moves PHI without ironclad security. The CFO needs ROI within 12 months. Dr. Martinez is a champion but doesn't control budget. |
| **Budget** | $1.2M allocated over 2 years. Procurement requires a formal RFP process. |
| **Timeline** | RFP responses due in 10 weeks. Decision by Q4. Implementation must start Q1 next year. |

### Target Discovery Questions

1. "Can you walk me through what happens today when a patient visits Hospital A and then Hospital B? How does the clinician at B access the records from A?"
2. "You mentioned care coordination — what specific clinical workflows would be improved by better data sharing?"
3. "What interoperability standards are you currently using? FHIR, HL7v2, something custom?"
4. "What is your HIPAA compliance framework for data sharing? Are there specific requirements around consent management, audit logging, or de-identification?"
5. "I understand you had a security incident in the past. How has that shaped your security requirements for new systems?"
6. "Who needs to sign off on a solution like this? I imagine your CISO and CFO are involved?"
7. "What does your Epic deployment look like — are all 12 hospitals on the same instance, or separate installations?"
8. "How would you measure success? Is there a target for reducing duplicate diagnostics or improving clinician time?"
9. "Have you looked at other solutions? What's working and what's not in the options you've seen?"
10. "What does the RFP timeline look like? How can we best support your evaluation process?"

### Evaluation Rubric

| Dimension | Excellent (9-10) | Good (6-8) | Needs Work (1-5) |
|-----------|-----------------|-----------|-----------------|
| **Compliance awareness** | Asked about HIPAA, consent management, audit logging, BAA requirements, de-identification | Asked about HIPAA generally | No compliance questions |
| **Clinical empathy** | Understood the patient-care angle, asked about clinical workflows, not just data | Some clinical awareness | Treated it purely as a data integration problem |
| **Stakeholder navigation** | Identified CISO as gate, CFO as budget, Dr. Martinez as champion; planned multi-thread engagement | Identified some stakeholders | Didn't map stakeholders |
| **Healthcare vocabulary** | Used terms correctly (PHI, EHR, FHIR, HL7, BAA, OCR) | Some correct terminology | Used incorrect or no healthcare terminology |

---

## How SE System Design Differs from SWE System Design

The core difference: SWE system design optimizes for correctness, scalability, and performance under load. SE system design optimizes for customer fit, integration feasibility, time-to-value, and a credible path to production.

### Side-by-Side Comparison

| Dimension | SWE System Design | SE System Design |
|-----------|-------------------|------------------|
| **Starting point** | "Design a system that does X" | "A customer in industry Y has problem Z. Design a solution." |
| **First 5 minutes** | Clarify requirements, estimate scale | Clarify the customer profile, business problem, success metrics |
| **Architecture focus** | Optimal data structures, consistency models, sharding strategy | Integration with existing systems, vendor selection, buy vs build |
| **Evaluation** | Correctness, scalability, latency, fault tolerance | Customer fit, feasibility, time-to-value, total cost of ownership |
| **Diagram content** | Databases, caches, load balancers, queues, microservices | Customer's existing systems, integration points, your product, data flow |
| **Operational concerns** | Monitoring, alerting, SLOs, incident response | Monitoring, support model, training, change management, ongoing customer success |
| **Rollout discussion** | Deployment strategy, canary releases, feature flags | Phased rollout by department/site, success milestones, change management plan |
| **Trade-off language** | "We choose eventual consistency because..." | "We recommend starting with a simpler architecture because the customer's team is small and..." |
| **Business justification** | Rarely required | Always required — what's the ROI? What's the cost of not doing this? |
| **Competitive context** | Never discussed | "The customer is also evaluating Competitor X, so we need to differentiate on..." |

### What SE Interviewers Are Looking For

1. **Customer-first thinking** — Did you start with the customer's world, or did you start drawing boxes?
2. **Integration awareness** — Did you consider the customer's existing systems, or did you design in a vacuum?
3. **Pragmatism** — Did you propose something achievable, or did you over-engineer?
4. **Business justification** — Can you articulate why this architecture is worth the investment?
5. **Rollout thinking** — Did you propose a phased approach with milestones, or a big-bang deployment?
6. **Communication** — Can you explain the architecture clearly, using a whiteboard, to a mixed audience?

---

## SE System Design Framework

Use this six-step framework for every SE system design interview.

### Step 1: Clarify the Customer (3-5 minutes)

Before drawing anything, understand who you are designing for.

**Questions to ask:**
- "Who is the customer? What industry? What size?"
- "What is their existing technical stack?"
- "What are their constraints? (Budget, timeline, compliance, team size)"
- "Who will use this system? Technical users, business users, or both?"
- "Are there regulatory or compliance requirements?"

**What to write on the whiteboard:**
```
CUSTOMER: [Industry], [Size], [Key Constraints]
EXISTING STACK: [List their current systems]
USERS: [Who will interact with the system]
CONSTRAINTS: [Budget, timeline, compliance, team]
```

### Step 2: Identify the Business Problem and Success Metrics (3-5 minutes)

Translate the technical scenario into a business problem with measurable outcomes.

**Questions to ask:**
- "What is the core business problem this solves?"
- "What is the cost of the current state? (Dollars, time, risk)"
- "What does success look like? What metric would they measure?"
- "What is the timeline expectation?"

**What to write on the whiteboard:**
```
PROBLEM: [1-2 sentence business problem]
COST OF STATUS QUO: [Quantified — $/time/risk]
SUCCESS METRICS: [Specific KPIs]
TIMELINE: [Expected delivery/value timeline]
```

### Step 3: Propose an Architecture (10-15 minutes)

Now draw. Your architecture should integrate with the customer's existing systems, not replace everything.

**Architecture diagram should include:**
- Customer's existing systems (show them on the left side)
- Your proposed solution (center)
- Integration points (arrows between existing and new)
- Data flow direction and format
- Key technology choices with brief justification

**Tips:**
- Start with a high-level diagram, then zoom into the most complex or risky component
- Call out what you would buy vs build
- Mention specific products/services by name (this shows practical knowledge)
- Label data formats (REST API, FHIR, Kafka events, S3 files)

### Step 4: Discuss Integration Points (5-7 minutes)

This is where SE system design diverges most from SWE system design. Real-world integration is where most projects succeed or fail.

**For each integration point, address:**
- Protocol and data format (REST, GraphQL, FHIR, file-based)
- Authentication and authorization
- Error handling and retry logic
- Data transformation requirements
- Latency and throughput expectations
- Who owns the integration (customer team, your team, partner)

### Step 5: Address Operational Concerns (5-7 minutes)

How will this run in production? How will the customer support it?

**Cover:**
- **Monitoring and alerting:** What dashboards does the customer need? What triggers an alert?
- **Support model:** Who does the customer call when something breaks? What's the SLA?
- **Scaling:** What happens when volume grows 10x? Is the architecture elastic?
- **Security:** How is data encrypted in transit and at rest? How are credentials managed?
- **Disaster recovery:** What is the RPO/RTO? How do backups work?

### Step 6: Propose a Rollout Plan (3-5 minutes)

Never propose a big-bang deployment. Always propose a phased rollout.

**Template:**
```
PHASE 1 (Weeks 1-4): Foundation
  - Deploy core infrastructure
  - Integrate with primary data source
  - Validate with 1 team/department
  - Success milestone: [specific metric]

PHASE 2 (Weeks 5-8): Expand
  - Add remaining integrations
  - Onboard additional teams
  - Success milestone: [specific metric]

PHASE 3 (Weeks 9-12): Optimize
  - Performance tuning
  - Advanced features
  - Full production rollout
  - Success milestone: [specific metric]
```

---

## System Design Walkthrough 1: RAG-Powered Internal Knowledge Base

### Scenario

"A 5,000-person professional services firm wants to build an internal knowledge base powered by AI. Employees should be able to ask questions in natural language and get answers sourced from internal documents. They use Microsoft 365, SharePoint for document storage, Okta for SSO, and Slack for communication."

### Step 1: Customer Clarification

```
CUSTOMER: Professional services, 5,000 employees
EXISTING STACK: Microsoft 365, SharePoint, Okta SSO, Slack
USERS: Consultants, project managers, HR, leadership
CONSTRAINTS: $200K Year 1 budget, SOC 2 required, data must stay in US regions
```

### Step 2: Business Problem

```
PROBLEM: Employees spend 5-8 hours/week searching for internal information
         across SharePoint, email, and Slack. Knowledge is siloed by team.
COST: 5,000 employees * 6 hrs/week * $75/hr = $23.4M/year in lost productivity
SUCCESS: Reduce average search time by 50%. 70%+ user adoption in 6 months.
TIMELINE: POC in 6 weeks, production in 4 months.
```

### Step 3: Architecture

```
┌─────────────────────┐     ┌──────────────────────────────────────────┐
│  DATA SOURCES        │     │  RAG PLATFORM                            │
│                     │     │                                          │
│  SharePoint ────────┼────→│  Document Ingestion                      │
│  Confluence ────────┼────→│    → Parse (PDF, DOCX, PPTX)            │
│  Slack (exported) ──┼────→│    → Chunk (500 tokens, 50 overlap)      │
│  Internal Wiki ─────┼────→│    → Embed (text-embedding-3-large)      │
│                     │     │    → Store in Vector DB                   │
└─────────────────────┘     │                                          │
                            │  Vector Database (Pinecone / pgvector)    │
┌─────────────────────┐     │    → Metadata filtering (team, doc type)  │
│  AUTH & ACCESS       │     │    → Hybrid search (vector + keyword)    │
│                     │     │                                          │
│  Okta SSO ──────────┼────→│  Query Pipeline                          │
│  RBAC (doc-level    │     │    → Embed query                         │
│   permissions from  │     │    → Retrieve top-K chunks               │
│   SharePoint ACLs)  │     │    → Rerank (cross-encoder)              │
│                     │     │    → Generate answer (Claude / GPT-4)    │
└─────────────────────┘     │    → Cite sources with links             │
                            │                                          │
┌─────────────────────┐     │  Access Control Layer                    │
│  USER INTERFACES     │     │    → Check Okta groups before retrieval  │
│                     │     │    → Filter chunks by user permissions   │
│  Slack Bot ─────────┼────→│                                          │
│  Web App ───────────┼────→│  Monitoring & Feedback                   │
│  Teams Integration ─┼────→│    → Query logs, latency, user ratings  │
│                     │     │    → Thumbs up/down for answer quality   │
└─────────────────────┘     └──────────────────────────────────────────┘
```

### Step 4: Integration Points

| Integration | Protocol | Auth | Complexity | Owner |
|------------|----------|------|-----------|-------|
| SharePoint | Microsoft Graph API | OAuth 2.0 (app registration) | Medium — need to handle delta sync and permissions | Your team + customer IT |
| Okta SSO | OIDC/SAML 2.0 | Standard Okta integration | Low — well-documented | Customer IT |
| Slack | Slack Bot API + Events API | Bot token + event subscriptions | Medium — need to handle threading and rate limits | Your team |
| Vector DB | Native SDK | API key / IAM | Low | Your team |
| LLM API | REST API | API key | Low — but need to manage costs and rate limits | Your team |

### Step 5: Operational Concerns

- **Monitoring:** Dashboard showing query volume, latency (p50/p95/p99), answer quality scores (from user feedback), cost per query, error rates.
- **Cost model:** Estimated $0.03-0.08 per query (embedding + LLM). At 5,000 queries/day: ~$150-400/day = $4,500-12,000/month.
- **Data freshness:** Incremental sync from SharePoint every 4 hours. Slack data synced daily. Stale content flagged automatically.
- **Security:** All data encrypted in transit (TLS 1.3) and at rest (AES-256). LLM API calls do not retain data. SOC 2 Type II compliance for all vendors.
- **Scaling:** Vector DB scales horizontally. LLM API rate limits managed with queuing. Caching frequent queries.

### Step 6: Rollout Plan

```
PHASE 1 (Weeks 1-4): Foundation
  - Deploy vector DB and query pipeline
  - Ingest SharePoint documents (top 3 teams)
  - Integrate Okta SSO
  - Web app interface only
  - Milestone: 100 internal beta users, 80%+ answer relevance

PHASE 2 (Weeks 5-8): Expand
  - Add Slack bot interface
  - Ingest remaining SharePoint sites + Confluence
  - Add user feedback (thumbs up/down)
  - Milestone: 1,000 users, 70%+ adoption

PHASE 3 (Weeks 9-16): Optimize
  - Add reranking for improved accuracy
  - Implement analytics dashboard
  - Full production rollout (all 5,000 employees)
  - Milestone: 50% reduction in average search time
```

---

## System Design Walkthrough 2: Customer-Facing Analytics Dashboard

### Scenario

"A B2B SaaS company with 500 enterprise customers wants to add a customer-facing analytics dashboard to their product. Each customer should see only their own data. The data is currently stored in a Postgres database and processed nightly in a batch pipeline."

### Step 1: Customer Clarification

```
CUSTOMER: B2B SaaS, 500 enterprise customers
EXISTING STACK: Postgres, Python batch pipeline, React frontend, AWS
USERS: Customer admins and executives (non-technical)
CONSTRAINTS: $100K budget, no dedicated data team, multi-tenant security is critical
```

### Step 2: Business Problem

```
PROBLEM: Customers are requesting self-serve analytics. Currently, the CS team
         manually builds reports in spreadsheets — 15 hours/week across the team.
COST: 15 hrs/week * $60/hr = $46K/year in CS time. Plus: #1 feature request,
      churn risk if competitors ship analytics first.
SUCCESS: 80% of top-tier customers using dashboards within 3 months.
         Reduce manual report requests by 70%.
TIMELINE: MVP in 8 weeks. Full rollout in 16 weeks.
```

### Step 3: Architecture

```
┌─────────────────────────┐
│  EXISTING SYSTEMS        │
│                         │
│  Postgres (OLTP) ──────┼──→ CDC / Nightly ETL ──→ Analytics DB (ClickHouse)
│  Python Batch Pipeline  │                              │
│  React Frontend         │                              │
└─────────────────────────┘                              │
                                                         ▼
                          ┌──────────────────────────────────────┐
                          │  ANALYTICS LAYER                      │
                          │                                      │
                          │  Pre-computed Aggregations            │
                          │    → Daily/weekly/monthly rollups     │
                          │    → Per-tenant materialized views    │
                          │                                      │
                          │  API Layer (REST)                     │
                          │    → Tenant-scoped queries            │
                          │    → Row-level security               │
                          │    → Response caching (Redis, 5-min)  │
                          │                                      │
                          │  Embedded Dashboard (React)           │
                          │    → Charts (Recharts / Apache ECharts)│
                          │    → Date range filters               │
                          │    → CSV export                       │
                          │    → Tenant context from JWT          │
                          └──────────────────────────────────────┘
```

### Step 4: Key Design Decisions

**Multi-tenancy approach:** Row-level security using the tenant ID from the JWT. Every API query includes a `WHERE tenant_id = :current_tenant` clause enforced at the middleware level, not the application code. This prevents accidental data leakage.

**Pre-computation vs live queries:** Pre-compute daily/weekly/monthly aggregations in a nightly batch job. This keeps dashboard load times under 500ms and avoids hitting the OLTP database. For customers needing fresher data, offer a "last 24 hours" view with a 15-minute cache.

**Caching strategy:** Redis cache with 5-minute TTL for dashboard queries. Cache key includes tenant ID + date range + metric. Invalidate on data refresh.

**Build vs buy:** For a 500-customer deployment, embedding a charting library (Recharts) in the existing React app is more cost-effective than a third-party embedded analytics tool ($50K+/year). If the company grows to 2,000+ customers with complex analytics needs, re-evaluate.

### Step 5: Operational Concerns

- **Performance:** Pre-computed aggregations ensure p95 latency < 500ms. Monitor query latency by tenant.
- **Multi-tenant security:** Automated tests that verify no cross-tenant data access. Quarterly security audit of the data access layer.
- **Scaling:** ClickHouse handles analytical workloads well. For 500 tenants, a single-node deployment suffices. At 2,000+ tenants, consider sharding.
- **Data freshness:** SLA of T+4 hours for daily metrics. Customers see a "last updated" timestamp.

### Step 6: Rollout Plan

```
PHASE 1 (Weeks 1-4): Core
  - Deploy ClickHouse, build ETL pipeline
  - 3 core dashboard metrics (usage, adoption, value)
  - 10 beta customers
  - Milestone: Dashboard loads in < 1s, zero cross-tenant data leaks

PHASE 2 (Weeks 5-8): Expand
  - Add date range filtering, CSV export
  - Expand to top 50 customers
  - Add customer feedback mechanism
  - Milestone: 80% of beta customers logging in weekly

PHASE 3 (Weeks 9-16): Scale
  - Full rollout to all 500 customers
  - Add custom metric builder
  - Embed in-app onboarding tour
  - Milestone: 70% reduction in manual report requests
```

---

## System Design Walkthrough 3: AI-Powered Customer Support

### Scenario

"An e-commerce company with 10 million customers and 50,000 support tickets per month wants to build an AI-powered customer support system. They want the AI to handle common queries automatically and escalate complex issues to human agents."

### Step 1: Customer Clarification

```
CUSTOMER: E-commerce, 10M customers, $500M revenue
EXISTING STACK: Zendesk, Shopify, Postgres, Node.js backend, React frontend
USERS: End customers (consumers), support agents (50 people), support managers
CONSTRAINTS: $300K Year 1 budget, must maintain CSAT > 4.2/5.0, PCI compliance for payment data
```

### Step 2: Business Problem

```
PROBLEM: 50,000 tickets/month, 8-hour avg first response time, $45 cost per ticket.
         60% of tickets are repetitive (order status, returns, basic how-to).
COST: 50K tickets * $45 = $2.25M/month. Hiring is not scaling fast enough.
SUCCESS: Automate 40% of tickets. Reduce first response time to < 2 minutes for
         automated responses. Maintain CSAT > 4.2.
TIMELINE: POC in 6 weeks. Full rollout in 4 months.
```

### Step 3: Architecture

```
┌──────────────────┐     ┌──────────────────────────────────────────────┐
│  CUSTOMER INPUT   │     │  AI SUPPORT PLATFORM                         │
│                  │     │                                              │
│  Chat Widget ────┼────→│  Intent Classification (LLM)                 │
│  Email ──────────┼────→│    → Order status, returns, billing,         │
│  Help Center ────┼────→│      product questions, complaints, other    │
│                  │     │                                              │
└──────────────────┘     │  Agent Router                                │
                         │    → Automated path (high-confidence intents) │
                         │    → Human path (low confidence, complaints,  │
┌──────────────────┐     │      PCI-sensitive, escalation requests)     │
│  DATA SOURCES     │     │                                              │
│                  │     │  Automated Agent                              │
│  Shopify API ────┼────→│    → RAG over help articles + policies       │
│  Order DB ───────┼────→│    → Tool use: order lookup, return initiation│
│  Help Articles ──┼────→│    → Guardrails: no PCI data in responses,   │
│  Policy Docs ────┼────→│      no financial advice, max 3 tool calls   │
│                  │     │    → Confidence threshold: < 0.7 → escalate  │
└──────────────────┘     │                                              │
                         │  Human-in-the-Loop Escalation                │
┌──────────────────┐     │    → AI drafts response for agent review     │
│  AGENT TOOLS      │     │    → Agent can edit, approve, or reject     │
│                  │     │    → Agent feedback trains the system        │
│  Zendesk ────────┼────→│                                              │
│  Agent Dashboard ┼────→│  Safety & Compliance                         │
│  QA Dashboard ───┼────→│    → PII/PCI detection and redaction        │
│                  │     │    → Tone analysis (empathy check)           │
└──────────────────┘     │    → Escalation triggers (anger, legal)     │
                         │    → All interactions logged for audit       │
                         │                                              │
                         │  Monitoring & Evaluation                     │
                         │    → CSAT per channel (automated vs human)   │
                         │    → Resolution rate, escalation rate        │
                         │    → Cost per ticket (automated vs human)    │
                         │    → Hallucination detection (weekly audit)  │
                         └──────────────────────────────────────────────┘
```

### Step 4: Human-in-the-Loop Escalation Design

The escalation system is the most critical component. Getting it wrong means either (a) customers get bad AI answers, or (b) every ticket gets escalated and automation ROI disappears.

**Escalation triggers:**
- AI confidence score < 0.7
- Customer explicitly asks for a human
- Sentiment analysis detects anger or frustration
- Ticket involves PCI data (payment, credit card)
- Customer mentions legal action, lawsuit, or regulatory terms
- Ticket is a complaint (not an informational query)
- AI has already responded twice without resolution

**Escalation behavior:**
- AI drafts a response and passes it to the human agent's queue with context
- Agent sees: customer message, AI's draft, relevant help articles, order history
- Agent can edit the AI draft and send, or write their own response
- Agent marks the AI draft as "helpful," "partially helpful," or "wrong" — this feedback is used for continuous improvement

### Step 5: Safety and Compliance

- **PCI compliance:** PII/PCI detection layer before the LLM. Credit card numbers, SSNs, and bank details are redacted from the prompt. AI is never shown raw payment data.
- **Tone guardrails:** Every AI response is checked for empathy and professionalism before delivery. Responses that score low on empathy are automatically escalated.
- **Hallucination mitigation:** AI responses are grounded in retrieved help articles. The system cites sources. Weekly human audit of 100 random automated responses. Hallucination rate target: < 2%.

### Step 6: Rollout Plan

```
PHASE 1 (Weeks 1-4): Assist Mode
  - AI drafts responses for ALL tickets
  - Human agents review and send every response
  - Measure: AI draft acceptance rate, CSAT, accuracy
  - Milestone: 60%+ draft acceptance rate

PHASE 2 (Weeks 5-8): Selective Automation
  - Auto-send for high-confidence order status queries only
  - Human review for everything else
  - Measure: Automated CSAT vs human CSAT
  - Milestone: Automated CSAT within 0.2 of human CSAT

PHASE 3 (Weeks 9-16): Full Automation
  - Auto-send for all high-confidence categories
  - Human-in-the-loop for low confidence and complaints
  - Measure: Ticket deflection rate, cost per ticket, CSAT
  - Milestone: 40% automation, < 2-min first response, CSAT > 4.2
```

---

## Demo Interview Preparation

### Choosing What to Demo

If given a choice, pick something you can demo confidently in 15-20 minutes. Prioritize:
1. Something you built yourself (strongest — shows depth)
2. A product you used extensively (good — shows practical knowledge)
3. The company's product (expected — do your homework)
4. A "teach me something" topic (versatile — shows communication)

### Building a Narrative Arc for Your Demo

```
1. HOOK (30 seconds)    → Provocative statement or outcome
2. CONTEXT (2 minutes)  → The problem this solves and who cares
3. WALKTHROUGH (12 min) → 3 segments mapped to value, not features
4. WOW MOMENT (2 min)   → The thing the audience didn't expect
5. CLOSE (2 minutes)    → Recap value, propose next steps
```

### Practicing Smooth Transitions

Write explicit transition phrases between demo segments:

- "So we've seen how [feature 1] addresses [pain 1]. Now let me show you how that data flows into the next step, which addresses [pain 2]."
- "That was the admin experience. Now let me switch to the end-user view — because ultimately, this is who we're building for."
- "We just covered the happy path. Now let me show you what happens when something goes wrong — because that's where the real value is."

### Handling Intentional Interruptions

In demo interviews, interviewers will intentionally interrupt you. This is not rude — it is a test. They want to see:
1. **Can you stop gracefully and address the question?**
2. **Can you return to your narrative without losing the thread?**
3. **Do you get flustered or defensive?**

**Framework:** Acknowledge → Answer → Bridge back.

"Great question. [Answer]. Now, that actually ties into what I was about to show you..."

### Mock Demo Rubric

| Dimension | Score Range | Criteria |
|-----------|-----------|---------|
| **Opening** | 0-10 | Hook relevance, confidence, time (< 30 seconds) |
| **Structure** | 0-10 | Clear narrative arc, logical flow, time management |
| **Technical depth** | 0-10 | Accurate, confident, appropriate level for audience |
| **Audience awareness** | 0-10 | Tailored language, checked for questions, read the room |
| **Handling interruptions** | 0-10 | Graceful, answered clearly, bridged back to narrative |
| **Wow moment** | 0-10 | Unexpected, visually impactful, tied to business value |
| **Close** | 0-10 | Recap, clear next step, asked for feedback |
| **Recovery (if applicable)** | 0-10 | Smooth transition to backup, minimal disruption |
| **Total** | 0-80 | 65+ = strong hire, 50-64 = hire, < 50 = needs work |

### The "Teach Me Something" Interview Format

Some companies use a "teach me something technical" round instead of a product demo. You pick any technical topic and teach it to the interviewer in 15 minutes.

**Best topics:**
- Something you know deeply and care about
- Something that has a clear visual or diagram component
- Something with a practical application the interviewer can relate to
- Something that lets you show layered explanation (simple first, then deeper)

**Example: "How DNS Works"**
- Hook: "Every time you type a URL, your computer has to solve a distributed lookup problem across millions of servers. Let me show you how."
- Level 1: The basic flow (browser → resolver → root → TLD → authoritative → IP)
- Level 2: Caching at each layer and TTL
- Level 3: DNS security (DNSSEC) and common attack vectors
- Close: "And that's why when someone says 'the internet is broken,' it's often DNS."

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 2: System Design Skeleton Builder** -- Practices the full "SE System Design Framework" (Steps 1-6). Takes a scenario description and asks you to fill in architecture components, integration points, rollout phases, and success metrics. Validates completeness against the framework requirements and generates a presentation-ready outline.

- **Exercise 3: Demo Script Timer** -- Applies the "Building a Narrative Arc for Your Demo" and "Mock Demo Rubric" sections. Takes a demo script with timed segments, validates total time and structural completeness (opening, segments, close), and returns a detailed evaluation with feedback.

See also `examples.py` section 2 (System Design Template) and section 3 (Demo Script Template) for complete runnable reference implementations.

---

## Interview Q&A: Mock Scenarios and System Design

**Q: Walk me through how you approach a system design question in an SE interview.**

I use a six-step framework. First, I clarify the customer — who they are, their industry, their existing stack, and their constraints. I do this because an architecture that works for a 50-person startup is wrong for a 10,000-person enterprise. Second, I identify the business problem and success metrics — not just what to build, but why, and how we will measure success. Third, I draw the architecture, always starting with the customer's existing systems on the left side and showing how the new solution integrates. Fourth, I walk through integration points in detail — protocols, auth, error handling, data formats. Fifth, I address operational concerns — monitoring, security, scaling, support. Sixth, I propose a phased rollout with milestones. I always finish by asking, "What would you like me to go deeper on?" because the interviewer usually wants to probe one area.

**Q: How would you design an AI-powered search for a customer's internal documents?**

I would start by understanding the customer profile and constraints. For a RAG-powered knowledge base, the architecture has four layers. First, ingestion: connect to document sources (SharePoint, Confluence, etc.) via APIs, parse documents into text, chunk them with overlap, embed using a model like text-embedding-3-large, and store in a vector database with metadata. Second, retrieval: embed the user's query, perform hybrid search (vector similarity plus keyword), rerank the top results with a cross-encoder, and filter by the user's access permissions. Third, generation: pass the top chunks as context to an LLM with a grounded prompt that requires citations. Fourth, feedback: collect user ratings, log queries, and use this data to improve retrieval quality over time. The critical integration points are SSO for access control, document permission sync so users only see documents they are authorized to view, and the LLM API with cost monitoring. I would roll this out in three phases: internal beta with one team, expansion to 10 teams, then company-wide with analytics.

**Q: In a mock discovery call, what are you trying to accomplish in the first 5 minutes?**

Three things. First, build rapport — thank them for their time, confirm who is in the room and their roles, and set an agenda that positions discovery as being in their interest ("I want to understand your situation so I can show you the most relevant parts of our product"). Second, establish the business context — I ask one or two broad questions about what they are trying to accomplish and what is driving the timing. This tells me whether there is urgency and a real budget. Third, transition to pain — I want to move from "what are you looking for" to "what's not working today" as quickly as possible. The first 5 minutes determine whether the next 30 will be productive or a waste of time.
