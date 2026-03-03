# 01 -- AI/ML Discovery and Use Cases

## AI-Specific Discovery Questions

Standard SaaS discovery focuses on workflows, integrations, and user count. AI discovery is fundamentally different because the product outcome depends on the customer's data, not just their process. A CRM works the same whether the customer has clean data or a mess -- an AI system does not. The SE must assess three dimensions before recommending anything: data readiness, organizational readiness, and expectation alignment.

### How AI Discovery Differs from Standard SaaS Discovery

| Dimension | Standard SaaS Discovery | AI/ML Discovery |
|---|---|---|
| Primary concern | "Does the product fit their workflow?" | "Does their data support the use case?" |
| Success predictability | High -- feature parity determines fit | Low -- data quality determines outcome |
| POC complexity | Deploy and configure | Data pipeline, model selection, evaluation |
| Timeline | Weeks to deploy | Months to production value |
| Stakeholders | IT, end users, procurement | Data engineers, ML engineers, domain experts, legal |
| Risk profile | Adoption risk | Accuracy risk, bias risk, compliance risk |
| Pricing model | Per seat / per feature | Per token / per inference / per GPU hour |

### Data Readiness Questions

Before discussing any AI capability, you must understand the customer's data landscape. Without good data, every AI project fails.

**Data existence and quality:**
- "What data do you have that's relevant to this use case? Where does it live?"
- "How is this data structured? Is it text, images, tabular, or a mix?"
- "How clean is the data? When was the last time someone audited it for quality?"
- "Do you have labeled data for this task? How much? Who created the labels?"
- "What's the volume? How many documents/records/transactions are we talking about?"

**Data infrastructure:**
- "Where is your data stored today? Cloud, on-prem, hybrid?"
- "Do you have a data warehouse or lake? What technology?"
- "How do you currently move data between systems? ETL pipelines? Manual exports?"
- "Who owns the data pipeline? Is there a data engineering team?"
- "What's your data refresh cadence? Real-time, hourly, daily, weekly?"

**Data access and governance:**
- "Are there data residency requirements? Does the data need to stay in a specific region?"
- "What sensitivity level is this data? PII, PHI, financial, proprietary?"
- "Can this data leave your network? Can it be sent to a third-party API?"
- "Who approves data access for new projects? What's the process?"

### Organizational Readiness Questions

AI projects fail more often for organizational reasons than technical ones.

- "Who will own this project day-to-day? Is there someone with AI/ML experience?"
- "Do you have ML engineers on staff? Data scientists? Or is this new territory?"
- "Who will evaluate whether the AI output is 'good enough'? Who are the domain experts?"
- "Has your organization deployed an AI/ML system before? What happened?"
- "Is there executive sponsorship for this initiative? Who?"
- "What's the budget for this project? Is it allocated, or does it need to be created?"
- "Do you have a process for human review of AI outputs?"

### Expectation Alignment Questions

The most dangerous moment in an AI sales cycle is when the customer says "we want AI to automate X" and means "100% accuracy with zero human oversight."

- "What accuracy level do you need for this to be useful? What's your threshold?"
- "What's the current baseline? How accurate is the human process today?"
- "What happens when the AI gets it wrong? What's the cost of an error?"
- "Are you expecting full automation or human-in-the-loop augmentation?"
- "What's your timeline for seeing production value? Weeks, months, quarters?"
- "Have you seen demos from other vendors? What did they promise?"

### AI Discovery Question Template (by Category)

| Category | Question | Why It Matters |
|---|---|---|
| **Data Quality** | "What percentage of your records are complete and consistently formatted?" | Determines whether data needs significant cleaning before any AI work begins |
| **Data Volume** | "How many examples of [the target task] do you have?" | Fine-tuning needs thousands of examples; RAG needs a document corpus; classification needs labeled sets |
| **Data Access** | "Can we get a sample dataset during the evaluation?" | If they cannot share data, the POC will be synthetic and non-predictive |
| **Data Sensitivity** | "Does this data contain PII, PHI, or regulated information?" | Determines model hosting, data processing location, and compliance requirements |
| **Data Freshness** | "How often does this data change? Do you need real-time or is daily sufficient?" | Real-time RAG is a different architecture than batch processing |
| **Talent** | "Who on your team will maintain this after deployment?" | If the answer is "nobody," the project will rot within 6 months |
| **Domain Expertise** | "Who can evaluate whether the AI output is correct?" | Without domain experts in the evaluation loop, you cannot build a meaningful eval set |
| **Prior AI Experience** | "Have you tried any AI/ML projects before? What happened?" | Past failures create skepticism; past successes set unrealistic expectations |
| **Success Criteria** | "What metric would make your leadership call this a success?" | Forces concrete, measurable goals instead of vague "AI transformation" |
| **Error Tolerance** | "What's the cost of a wrong answer?" | High-stakes domains (medical, legal, financial) need different architectures than low-stakes ones |
| **Latency** | "Does the user need a response in milliseconds, seconds, or minutes?" | Determines model size, caching strategy, and architecture |
| **Scale** | "How many requests per day/hour/minute?" | Determines infrastructure, cost model, and optimization strategy |
| **Integration** | "What systems does this need to connect to?" | Identifies the integration surface area and complexity |
| **Compliance** | "Are there regulatory requirements (HIPAA, SOC 2, GDPR, EU AI Act)?" | May eliminate entire categories of solutions (e.g., no external API calls) |
| **Budget** | "What's the total budget, including infrastructure and ongoing API costs?" | AI has a variable cost component that surprises customers used to fixed SaaS pricing |
| **Timeline** | "When do you need this in production?" | If the answer is "next month," manage expectations immediately |

---

## Evaluating AI Readiness

### The AI Readiness Maturity Model

Not every organization is ready for AI. Selling an advanced AI solution to a Level 1 organization is malpractice -- it will fail, damage your credibility, and sour the customer on AI entirely. The responsible SE assesses maturity and recommends accordingly.

| Level | Name | Description | Data State | AI Experience | Org Support |
|---|---|---|---|---|---|
| **1** | No AI | No AI initiatives, limited data infrastructure | Siloed, messy, no warehouse | None | Low awareness |
| **2** | AI Curious | Exploring AI, running experiments, no production systems | Some consolidation, basic pipelines | A few individuals experimenting | Interest but no dedicated budget |
| **3** | AI Piloting | Running 1-2 AI projects, limited production deployment | Data warehouse, basic quality processes | Small ML/data team | Dedicated budget, pilot scope |
| **4** | AI Operational | Multiple AI systems in production, established processes | Mature pipelines, monitoring, governance | Established ML engineering team | AI strategy at leadership level |
| **5** | AI Native | AI embedded in core business processes, continuous iteration | Real-time data platform, automated quality | Large AI/ML org, MLOps practices | AI is a competitive advantage |

### Assessment Dimensions

Evaluate each dimension on a 1-5 scale:

| Dimension | Score 1 | Score 3 | Score 5 |
|---|---|---|---|
| **Data Quality** | Messy, inconsistent, no standards | Some quality processes, known issues | Automated quality checks, high coverage |
| **Data Infrastructure** | Spreadsheets and emails | Data warehouse, basic ETL | Real-time data platform, streaming |
| **Talent** | No AI/ML staff | Data analysts, 1-2 data scientists | Full ML engineering team, MLOps |
| **Organizational Buy-in** | No awareness or interest | Pilot approved, limited sponsorship | AI strategy, executive commitment |
| **Use Case Clarity** | "We want to do something with AI" | Specific use case identified, no success criteria | Clear use case, metrics, evaluation plan |
| **Budget** | No budget allocated | Pilot budget approved | Production budget with ongoing operational costs included |

### What to Recommend at Each Level

| Level | Recommended Approach | What to Sell | What NOT to Sell |
|---|---|---|---|
| **1** | Data foundation first | Data platform, data warehouse, consulting | Any AI product -- they are not ready |
| **2** | Education and quick wins | Prompt engineering workshop, pre-built AI features (embedded AI in existing SaaS) | Custom model training, complex agent architectures |
| **3** | Guided pilots | RAG solutions, API-based AI features, managed AI services | Self-hosted models, custom fine-tuning (unless they have the team) |
| **4** | Production deployment | Full AI platform, fine-tuning, agent frameworks, custom solutions | Nothing is off the table, but validate scale requirements |
| **5** | Platform and optimization | Model optimization, cost efficiency tools, advanced orchestration, evaluation platforms | Basic tutorials -- they know more than most vendors |

### When to Tell a Customer They Are Not Ready

This is the hardest conversation in AI sales, and it is also the most valuable. Telling a Level 1 customer they need to invest in data infrastructure before buying an AI platform builds trust and positions you for the future deal.

**How to deliver the message:**
- "Based on what we have discussed, I think the most impactful thing we could do right now is help you get your data foundation in place. Without that, any AI system -- ours or anyone else's -- will underperform."
- "I would rather be honest with you now than sell you something that won't deliver results. Here is what I'd recommend as a 6-month roadmap to get AI-ready."
- Provide a concrete readiness roadmap with milestones that trigger the AI conversation again.

---

## Common AI/ML Use Cases by Industry

### Use Case Matrix

| Industry | Use Case | AI Approach | Data Required | Typical ROI Range | Complexity |
|---|---|---|---|---|---|
| **Healthcare** | Clinical documentation summarization | RAG + generation | EHR data, clinical notes | 20-40% time savings for physicians | Medium |
| **Healthcare** | Medical image analysis | Classification (CV) | Labeled imaging datasets (10K+) | Improved diagnostic accuracy 5-15% | High |
| **Healthcare** | Patient triage automation | Classification + RAG | Symptom histories, outcomes data | 30-50% reduction in triage time | Medium |
| **Financial Services** | Fraud detection | Classification + anomaly detection | Transaction histories, fraud labels | 10-30% reduction in fraud losses | Medium |
| **Financial Services** | Document processing (KYC/AML) | Extraction + classification | Regulatory documents, ID documents | 50-70% processing time reduction | Medium |
| **Financial Services** | Investment research summarization | RAG + generation | SEC filings, earnings transcripts | 40-60% analyst time savings | Low-Medium |
| **Legal** | Contract review and extraction | RAG + extraction | Contract corpus, clause library | 60-80% review time reduction | Medium |
| **Legal** | Legal research assistant | RAG | Case law databases, statutes | 30-50% research time savings | Medium |
| **Legal** | Document drafting | RAG + generation | Template library, precedent documents | 40-60% drafting time reduction | Medium |
| **Retail/E-commerce** | Product recommendation | Embeddings + classification | Purchase history, browsing data | 10-25% increase in conversion | Medium |
| **Retail/E-commerce** | Product description generation | Generation | Product catalogs, brand guidelines | 80-90% reduction in content creation time | Low |
| **Retail/E-commerce** | Customer service automation | RAG + agents | FAQ corpus, ticket history | 30-50% ticket deflection | Medium |
| **Manufacturing** | Predictive maintenance | Classification + anomaly detection | Sensor data, maintenance logs | 20-40% reduction in unplanned downtime | High |
| **Manufacturing** | Quality inspection | Classification (CV) | Defect images, labeled datasets | 15-30% improvement in defect detection | High |
| **Customer Support** | Ticket classification and routing | Classification | Ticket history with labels | 40-60% faster routing | Low |
| **Customer Support** | Answer generation from knowledge base | RAG | Knowledge base, SOPs, docs | 30-50% resolution time reduction | Medium |
| **Customer Support** | Sentiment analysis and escalation | Classification | Ticket/chat history with outcomes | 20-30% reduction in escalation time | Low |

### Decision Tree: Which AI Approach Fits?

```
Start: What is the customer trying to do?
│
├── Answer questions from existing documents?
│   └── RAG (Retrieval-Augmented Generation)
│       └── Cross-ref: ../../llms/03-rag-and-retrieval/
│
├── Classify or categorize inputs?
│   ├── Simple categories, few labels? → Prompt engineering with few-shot
│   └── Complex categories, need accuracy? → Fine-tuned classifier
│       └── Cross-ref: ../../llms/05-fine-tuning/
│
├── Generate new content?
│   ├── Needs to follow strict brand/style? → Fine-tuning or RAG with examples
│   └── General generation? → Prompt engineering
│       └── Cross-ref: ../../llms/02-prompt-engineering/
│
├── Extract structured data from unstructured text?
│   └── RAG + extraction prompts (or fine-tuned extraction model)
│
├── Automate multi-step workflows?
│   └── Agent architecture with tool use
│       └── Cross-ref: ../../llms/04-agents-and-tool-use/
│
└── Analyze images, audio, or video?
    └── Specialized CV/audio models or multimodal LLMs
```

---

## Setting Realistic AI Expectations

### The Number One AI SE Challenge

Customers expect magic. They have seen ChatGPT demos, read hype articles, and heard vendor claims of "95% accuracy." The SE's job is to set expectations that are ambitious enough to close the deal but realistic enough to survive the POC.

### How to Set Expectations Without Killing the Deal

**The accuracy conversation:**
- Never promise a specific accuracy number before seeing the customer's data.
- Instead: "Based on similar use cases we have seen, customers typically achieve X-Y% accuracy in the first pilot. With iterative improvement, that usually reaches Z% within 3-6 months."
- Always anchor against the human baseline: "Your team currently catches 85% of these issues. Our goal for the pilot would be to match or exceed that, starting with the most common case types."

**The probabilistic vs deterministic conversation:**
- "Traditional software is deterministic -- the same input always gives the same output. AI is probabilistic -- the same input might give slightly different outputs. This is a feature, not a bug, but it means we need guardrails."
- "Think of AI as a very capable new hire -- good at the job, but needs supervision until you trust them. We design the system with human review at critical decision points."

**The 80/20 pilot approach:**
- Focus the POC on the 20% of cases that represent 80% of volume.
- "We are going to start with your most common [ticket type / document type / query type]. These represent 80% of your volume and are the most predictable. Once we nail those, we expand to edge cases."
- This approach produces impressive metrics quickly because common cases are where AI performs best.

### Timeline Expectations

| Phase | Duration | What Happens | Customer Expectation to Manage |
|---|---|---|---|
| Discovery + scoping | 1-2 weeks | Understand data, define metrics, align stakeholders | "This is not wasted time -- it prevents a failed POC" |
| Data preparation | 1-3 weeks | Access data, clean data, build eval set | "This is the unglamorous work that makes AI actually work" |
| POC build | 2-4 weeks | Build pipeline, integrate, run initial evaluation | "The first version will not be perfect -- that is expected" |
| POC evaluation | 1-2 weeks | Measure results, identify gaps, iterate | "We iterate based on real results, not assumptions" |
| Production hardening | 4-8 weeks | Monitoring, guardrails, scale testing, security review | "Production AI requires more infrastructure than a demo" |
| Ongoing optimization | Continuous | Evaluation, retraining, prompt tuning, model updates | "AI is a product, not a project -- it needs ongoing attention" |

### Success Metrics That Are Actually Achievable

| Metric | Realistic First Pilot Target | Unrealistic Expectation |
|---|---|---|
| Accuracy on common cases | 85-95% | "99.9% like our current rule-based system" |
| Processing time reduction | 40-60% | "Real-time processing of everything" |
| Ticket deflection rate | 25-40% in month 1 | "80% deflection on day 1" |
| Cost per transaction | 30-50% reduction | "10x cheaper immediately" |
| User satisfaction | "Comparable to human" (CSAT > 4.0) | "Better than human in every way" |

---

## AI Maturity Assessment

### Assessment Framework

Use this framework to evaluate where a customer is and build a concrete recommendation.

### Assessment Questionnaire Template

**Section 1: Data Foundation (Score 1-5 per question)**

1. Do you have a centralized data warehouse or lake? (1=no, 5=mature platform)
2. Is your data documented with schemas and data dictionaries? (1=no documentation, 5=comprehensive)
3. Do you have automated data quality monitoring? (1=no, 5=real-time quality dashboards)
4. Can you access and share data for new projects within days? (1=months, 5=self-service)
5. Do you have a data governance policy? (1=no, 5=enforced and audited)

**Section 2: AI/ML Capability (Score 1-5 per question)**

1. Do you have dedicated ML/AI staff? (1=no, 5=established team with MLOps)
2. Have you deployed an ML model to production? (1=never, 5=multiple production models)
3. Do you have an evaluation framework for AI outputs? (1=no, 5=automated eval pipelines)
4. Do you have a model monitoring system? (1=no, 5=automated drift detection)
5. Can you train or fine-tune models internally? (1=no, 5=established training infrastructure)

**Section 3: Organizational Readiness (Score 1-5 per question)**

1. Is there executive sponsorship for AI initiatives? (1=no awareness, 5=board-level priority)
2. Do you have a budget allocated for AI? (1=no, 5=multi-year budget)
3. Are business stakeholders engaged in defining AI use cases? (1=IT-only, 5=cross-functional)
4. Do you have a process for evaluating AI vendors? (1=no, 5=established evaluation framework)
5. Do you have an AI ethics or responsible AI policy? (1=no, 5=published and enforced)

### Report Template

```
AI READINESS ASSESSMENT REPORT
==============================

Customer: [Name]
Date: [Date]
Assessed by: [SE Name]

OVERALL MATURITY LEVEL: [1-5] — [Name]

DIMENSION SCORES:
  Data Foundation:        [X/25] — [Level Name]
  AI/ML Capability:       [X/25] — [Level Name]
  Organizational Readiness: [X/25] — [Level Name]

KEY GAPS:
  1. [Gap description + impact]
  2. [Gap description + impact]
  3. [Gap description + impact]

RECOMMENDED NEXT STEPS:
  Immediate (0-30 days):
    - [Action item]
    - [Action item]

  Short-term (1-3 months):
    - [Action item]
    - [Action item]

  Medium-term (3-6 months):
    - [Action item]
    - [Action item]

RECOMMENDED STARTING USE CASE: [Use case + why]
ESTIMATED TIME TO FIRST VALUE: [Timeline]
ESTIMATED BUDGET RANGE: [Range]
```

---

## The Build vs Buy vs Partner Decision

### When Customers Should Use Each Approach

| Approach | Best When | Pros | Cons | Cost Range |
|---|---|---|---|---|
| **API Provider** (OpenAI, Anthropic, Google) | Standard use cases, fast time-to-value, limited ML team | Fastest to deploy, no infrastructure, best models | Vendor lock-in, data leaves your network, variable cost | $1K-50K/month |
| **Managed AI Service** (AWS Bedrock, Azure OpenAI, Vertex AI) | Cloud-native, compliance needs, existing cloud relationship | Data stays in your cloud, compliance certifications, managed infra | Still vendor-dependent, higher base cost, cloud lock-in | $5K-100K/month |
| **Fine-Tuning** | Domain-specific accuracy, unique data, consistent behavior | Higher accuracy for specific tasks, lower per-inference cost, IP moat | Needs labeled data, needs ML expertise, ongoing maintenance | $10K-200K setup + $5K-50K/month |
| **Open-Source Self-Hosted** | Maximum control, data sensitivity, airgapped environments | Full control, no vendor dependency, data stays local | Highest operational burden, needs ML team, GPU infrastructure | $20K-500K/month infra |
| **Custom Training** | Truly novel task, massive competitive advantage needed | Maximum differentiation, full IP ownership | Highest cost, longest timeline, needs research-level talent | $100K-5M+ |

### Decision Tree

```
Start: What are the customer's constraints?
│
├── Data cannot leave the network?
│   ├── Has GPU infrastructure? → Open-source self-hosted
│   └── No GPU infrastructure? → Managed AI in private cloud (Azure OpenAI, Bedrock)
│
├── Needs domain-specific accuracy?
│   ├── Has 10K+ labeled examples? → Fine-tuning
│   └── Has documents but not labeled data? → RAG with API provider
│
├── Standard use case (summarization, Q&A, classification)?
│   ├── Budget-conscious? → API provider with prompt engineering
│   └── Has cloud relationship? → Managed AI service
│
├── Novel, differentiated AI capability?
│   ├── Has ML research team? → Custom training
│   └── No ML team? → Partner with AI consultancy + API provider
│
└── Compliance-critical (healthcare, financial, government)?
    └── Managed AI in compliant cloud + fine-tuning for accuracy
```

### Cost/Control/Capability Tradeoffs

```
                    High Control
                         │
     Custom Training     │      Open-Source
     ($$$$, slow)        │      Self-Hosted
                         │      ($$$, medium)
                         │
  Low ───────────────────┼──────────────── High
  Capability             │              Capability
                         │
     Prompt Engineering   │      API Provider
     ($, fast)           │      ($$, fast)
                         │
                    Low Control
```

For deep technical foundations on RAG, embeddings, and LLM architectures, see the [LLM Engineering course](../../llms/README.md), especially Module 01 (fundamentals), Module 03 (RAG), and Module 06 (evaluation).

---

## Practice Exercises

The following exercises in `exercises.py` directly practice concepts from this file:

- **Exercise 1: AI Use Case Evaluator** -- Practices the "Evaluating AI Readiness" and "Common AI/ML Use Cases by Industry" sections. Takes a use case description with data and requirements, scores it on AI-readiness dimensions, and recommends the appropriate AI approach (RAG, fine-tuning, prompt engineering, or not suitable). See the decision tree and maturity model for scoring criteria.

- **Exercise 2: AI Expectation Setter** -- Directly applies the "Setting Realistic AI Expectations" section. Takes a use case category and the customer's stated expectations, then generates a realistic expectation document including what to expect, what not to expect, risks, and recommended benchmarks. Reference the timeline and success metrics tables.

- **Exercise 6: Responsible AI Checklist Generator** -- Applies the maturity assessment and build/buy/partner frameworks to generate compliance and safety checklists tailored to industry and data sensitivity.

See also `examples.py` sections 1 (AI Use Case Scoring) and 5 (AI Readiness Assessment) for complete runnable reference implementations.

---

## Interview Q&A: AI/ML Discovery

**Q: How do you approach discovery for an AI/ML project differently than a standard SaaS product?**

AI discovery is fundamentally data-centric. In standard SaaS, I am mapping product capabilities to workflow needs -- does the tool fit the process? In AI, the product outcome depends entirely on the customer's data quality, volume, and accessibility. I start every AI discovery by understanding their data landscape before discussing any capabilities. I ask about data existence, quality, governance, and sensitivity. Then I assess organizational readiness -- do they have people who can evaluate AI output, maintain the system, and iterate on it? Finally, I align expectations: what accuracy do they need, what is the current human baseline, and what is the cost of errors? I have learned that 60% of AI project failures trace back to data issues that were discoverable in discovery but never asked about. The worst thing I can do is sell an AI system to a customer whose data cannot support it.

**Q: How do you handle a customer who says "we want to use AI" but has no specific use case?**

This is extremely common after every wave of AI hype. I resist the urge to propose a use case immediately because that leads to solutions looking for problems. Instead, I run a structured use case identification exercise. I ask about their biggest operational pain points -- where do people spend time on repetitive tasks, where are errors most costly, where is latency a bottleneck? I look for the intersection of "high business impact" and "data availability." Then I map potential use cases to the AI approach decision tree -- some will be RAG, some classification, some generation. I prioritize use cases that have clear success metrics, available data, and a willing business owner. The output is a ranked list of 2-3 use cases with effort vs impact estimates. Usually the conversation shifts from "we want AI" to "we want to reduce contract review time by 50%" -- a much more actionable starting point.

**Q: When would you tell a customer they are not ready for AI?**

When their data foundation cannot support the use case and fixing it would take longer than their patience allows. Specifically: if their data is siloed across disconnected systems with no warehouse, if they have no data engineering capability, if they cannot share sample data for evaluation, or if they have no one who can judge whether AI output is correct. I deliver this message constructively -- not "you are not ready" but "the highest-ROI investment right now is your data infrastructure, because every AI system you build will perform proportional to your data quality. Here is a 6-month roadmap that gets you AI-ready, and I would love to reconnect when you hit milestone X." This preserves the relationship and often accelerates their data investment because it now has a concrete AI use case motivating it.
