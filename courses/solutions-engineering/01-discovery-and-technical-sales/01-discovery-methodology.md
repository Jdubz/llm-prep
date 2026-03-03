# 01 -- Discovery Methodology

## The Discovery Mindset

Discovery is the single most important skill a Solutions Engineer can develop. Every other SE skill -- demos, POCs, architecture reviews, competitive positioning -- depends on the quality of your discovery. If you don't understand the customer's real problem, you'll build the wrong demo, run the wrong POC, and lose the deal.

### Pain-First vs Feature-First Selling

The fundamental distinction in technical sales is between leading with pain and leading with features.

**Feature-first selling** sounds like: "Let me show you our platform. We have real-time analytics, 47 integrations, role-based access control, and SOC 2 compliance." This approach fails because it forces the customer to do the mental work of mapping your features to their problems. Most won't bother -- they'll nod politely and never return your AE's calls.

**Pain-first selling** sounds like: "Tell me about the last time your team missed an SLA. What happened? What was the business impact? What did you try to do about it?" This approach works because it uncovers the emotional and financial cost of the status quo, which is what actually drives purchase decisions.

The pain-first approach is harder because it requires patience, genuine curiosity, and the discipline to resist the urge to pitch. When a prospect says "we're struggling with observability," the feature-first SE immediately says "we have great dashboards!" The pain-first SE says "tell me more about what that looks like day to day."

### The Curious Consultant vs the Product Pitcher

Think of yourself as a consultant who happens to work for a software company, not as a salesperson who happens to know technology.

| Behavior | Product Pitcher | Curious Consultant |
|---|---|---|
| First instinct | "Let me show you the product" | "Let me understand your situation" |
| Listening ratio | Talks 70%, listens 30% | Talks 30%, listens 70% |
| Questions asked | Closed-ended, leading | Open-ended, exploratory |
| Response to objections | Defensive, feature-dumping | Curious, "tell me more" |
| Demo approach | Standard feature tour | Tailored to stated problems |
| Follow-up | "Did you like the demo?" | "How does what we discussed map to your priorities?" |

### What Bad Discovery Looks Like

Recognizing anti-patterns is as important as knowing the right approach:

- **Jumping to demo** -- The prospect mentions a keyword that maps to your product, and you immediately switch to screen-sharing. You skip understanding the context, the stakeholders, the urgency, and the alternatives they've evaluated.
- **Asking yes/no questions** -- "Do you use Kubernetes?" gets you a one-word answer. "Walk me through your deployment process from code commit to production" gets you a five-minute answer full of pain signals.
- **Talking more than listening** -- If you're talking more than 40% of the time in a discovery call, you're doing it wrong. The prospect should be doing most of the talking. Your job is to guide the conversation, not dominate it.
- **Accepting surface-level answers** -- When a prospect says "we need better visibility," many SEs nod and move on. Good SEs ask "visibility into what, specifically? What decisions are you trying to make that you can't make today?"
- **Not qualifying** -- Spending 45 minutes in deep technical discovery with someone who has no budget, no authority, and no timeline is a waste of both parties' time. Discovery must include qualification signals.

---

## SPIN Selling for SEs

SPIN is a questioning framework developed by Neil Rackham based on observational research of 35,000+ sales calls. It provides a structured way to move from surface-level fact-finding to deep pain discovery.

### Situation Questions

Situation questions establish the baseline: what does the customer's current environment look like? These are necessary but low-value -- they don't create urgency or differentiation. Spend as little time here as possible by doing pre-call research.

**Example Situation questions:**
- "Can you walk me through your current architecture for handling X?"
- "How many engineers are working on this problem today?"
- "What tools are you currently using for Y?"
- "What does your deployment process look like end to end?"

**Pre-call research tip:** You can often answer many Situation questions yourself by reading the prospect's tech blog, checking their job postings for technology mentions, scanning their GitHub repos, and reviewing LinkedIn profiles of the people you'll meet. If you already know they use Kubernetes, don't waste time asking -- say "I noticed from your engineering blog that you're running on Kubernetes. Can you tell me about the pain points you're experiencing with your current setup?"

### Problem Questions

Problem questions surface dissatisfaction with the current state. These have higher value because they move the conversation from facts to friction.

**Example Problem questions:**
- "What's the most frustrating part of your current workflow for X?"
- "Where does your team spend the most unplanned time?"
- "What happens when this system fails? How do you find out?"
- "If you could change one thing about your current tooling, what would it be?"

**Pro tip:** After a Problem question, resist the urge to respond with a feature. Just say "tell me more about that" or "how often does that happen?"

### Implication Questions

Implication questions are the most powerful and most underused. They force the prospect to articulate the downstream business impact of their problems. A problem without implications is a nuisance; a problem with major implications is a priority.

**Example Implication questions:**
- "When that outage happened, what was the impact on your customers?"
- "If your deployment takes 4 hours instead of 20 minutes, what does that mean for your release velocity?"
- "What happens to your team's retention if this burnout from on-call rotations continues?"
- "If you can't ship this integration by Q3, what does that mean for the partnership deal?"

**Why implication questions work:** They make the cost of inaction concrete. A prospect might live with a slow deployment process indefinitely -- until they realize it's costing them 3 engineering hires worth of productivity per year and delaying their ability to close a $2M partnership.

### Need-Payoff Questions

Need-payoff questions get the prospect to articulate the value of solving the problem in their own words. This is critical because buyers are more persuaded by what they say than by what you say.

**Example Need-payoff questions:**
- "If you could cut that deployment time from 4 hours to 20 minutes, how would that change your team's workflow?"
- "What would it mean for your business if you could detect outages in seconds instead of hours?"
- "If you had real-time visibility into X, what decisions could you make that you can't make today?"
- "How would it help if your team could self-serve this instead of filing a ticket?"

### SPIN Balance and Sequencing

The common mistake is spending too much time on Situation questions and skipping straight to Need-payoff. A healthy SPIN call follows this approximate distribution:

| Question Type | % of Discovery Time | Purpose |
|---|---|---|
| Situation | 10-15% | Establish context (minimize with pre-research) |
| Problem | 25-30% | Surface pain points |
| Implication | 30-35% | Quantify business impact |
| Need-payoff | 20-25% | Let prospect articulate value |

### When to Use SPIN vs Other Frameworks

SPIN works best in complex B2B sales where:
- The buying process involves multiple stakeholders
- The deal size justifies the time investment in deep discovery
- The customer's problem is not immediately obvious
- You need to build a business case, not just demonstrate features

For transactional sales with a known need (e.g., "we need a CDN"), SPIN is overkill. For enterprise deals where the prospect isn't sure they have a problem yet, SPIN is essential.

---

## MEDDPICC Deep Dive

MEDDPICC is a deal qualification and forecasting framework used by the most rigorous enterprise sales organizations. While SPIN tells you how to run a discovery conversation, MEDDPICC tells you whether you have a real deal and what's missing.

Each letter represents a critical element. If you can't fill in every letter, you have gaps in your understanding -- and gaps in your deal.

### M -- Metrics

**What it means:** What does quantifiable success look like for this prospect? What are the numbers they care about?

**Why it matters:** If you can't tie your product to measurable outcomes, the deal will stall. The economic buyer needs numbers to justify the spend internally.

**Questions to ask:**
- "What KPIs does your team get measured on?"
- "What would a 'successful' implementation look like in 6 months? What numbers would change?"
- "What's the current cost of this problem in dollars, hours, or headcount?"
- "If we solve this, what metric would you show your VP to prove it worked?"

### E -- Economic Buyer

**What it means:** Who has the authority and budget to sign the deal? Not who you're talking to -- who writes the check.

**Why it matters:** Deals die when you build consensus with the wrong people. You can win over every engineer in the room, but if the VP of Engineering never heard your name, the deal goes nowhere.

**Questions to ask:**
- "Who ultimately approves purchases like this?"
- "Walk me through how your team has purchased software in the past. Who was involved?"
- "Is there a budget already allocated for this, or does someone need to create one?"
- "Who would sign off on the contract?"

### D -- Decision Criteria

**What it means:** What specific factors will the buyer evaluate when comparing solutions? Technical requirements, compliance needs, integration requirements, pricing model preferences.

**Why it matters:** If you don't know the decision criteria, you'll demo the wrong things and lose to a competitor who addressed what actually mattered.

**Questions to ask:**
- "What are the must-have vs nice-to-have requirements?"
- "Are there any hard technical constraints (on-prem only, SOC 2, FedRAMP, specific language/framework)?"
- "How are you evaluating the options you're considering?"
- "What would make you say 'no' to a solution regardless of everything else?"

### D -- Decision Process

**What it means:** What are the specific steps between now and a signed contract? Who's involved at each step? What's the timeline?

**Why it matters:** You can't forecast a deal if you don't know the process. "We'll get back to you" is not a process.

**Questions to ask:**
- "What does your evaluation process look like from here?"
- "Who else needs to be involved before a decision is made?"
- "What's the typical timeline from selecting a vendor to going live?"
- "Have you purchased anything similar before? How long did that process take?"

### P -- Paper Process

**What it means:** The legal, procurement, security, and compliance steps required to execute a contract. MSA review, security questionnaire, vendor onboarding, procurement approval.

**Why it matters:** Paper process is where deals go to die. A deal that's "verbally approved" can sit in legal review for 3 months. SEs who understand paper process help their AEs set realistic close dates.

**Questions to ask:**
- "What does your procurement process look like?"
- "Is there a security review required? What does that involve?"
- "Do you have a standard MSA, or do you use the vendor's?"
- "How long did the last vendor contract take from verbal approval to signature?"

### I -- Identify Pain

**What it means:** What is the specific, concrete, emotionally resonant problem the prospect needs to solve? Not the feature they want -- the pain they feel.

**Why it matters:** Pain is the engine that drives deals forward. Without identified pain, there's no urgency, and the prospect will default to the status quo.

**Questions to ask:**
- "What's the biggest problem this project is supposed to solve?"
- "What happens if you don't solve this in the next 6 months?"
- "On a scale of 1-10, how much is this problem affecting your team's productivity?"
- "Who is most affected by this problem, and how?"

### C -- Champion

**What it means:** The internal advocate who wants you to win. They have influence, access to the economic buyer, and a personal stake in solving the problem.

**Why it matters:** You cannot sell enterprise software without an internal champion. The champion is your eyes, ears, and voice inside the organization when you're not in the room.

**Identifying a champion (they must have all three):**
- **Power:** Can they influence the decision? Do people listen to them?
- **Pain:** Do they personally feel the problem? Is their reputation tied to solving it?
- **Access:** Can they get you a meeting with the economic buyer?

**Questions to ask your potential champion:**
- "Why is this important to you personally?"
- "Who else needs to be convinced? Can you help me understand their perspective?"
- "If we proved the value in a POC, could you help us get in front of [economic buyer]?"
- "What would make you look good internally if this project succeeded?"

### C -- Competition

**What it means:** Who else is the prospect evaluating? This includes other vendors, open-source alternatives, and the biggest competitor of all: doing nothing (status quo).

**Why it matters:** If you don't know who you're competing against, you can't differentiate. You might be building the wrong demo, fighting the wrong battle cards, or not realizing the prospect is about to build it in-house.

**Questions to ask:**
- "Are you evaluating other solutions for this?"
- "Have you tried solving this with internal tooling or open-source?"
- "What do you like about the other options you've seen so far?"
- "What would make you choose to keep doing what you're doing today?"

### MEDDPICC Scorecard Template

| Element | Status | Details | Gap / Next Step |
|---|---|---|---|
| **M**etrics | Red/Yellow/Green | What success numbers have been identified? | What questions remain? |
| **E**conomic Buyer | Red/Yellow/Green | Who is it? Have you met them? | How to get access? |
| **D**ecision Criteria | Red/Yellow/Green | What are the must-haves? | What haven't you confirmed? |
| **D**ecision Process | Red/Yellow/Green | What are the steps to close? | What steps are unclear? |
| **P**aper Process | Red/Yellow/Green | Legal/security/procurement timeline? | What blockers exist? |
| **I**dentify Pain | Red/Yellow/Green | What is the specific pain? | Is it quantified? |
| **C**hampion | Red/Yellow/Green | Who is your champion? Power/pain/access? | Are they strong enough? |
| **C**ompetition | Red/Yellow/Green | Who else is in the deal? | What's your differentiation? |

---

## Qualification Frameworks

### BANT (Budget, Authority, Need, Timeline)

BANT is the original qualification framework. It's simple and effective for transactional sales but often too shallow for complex enterprise deals.

- **Budget:** Is there money allocated for this? Or does budget need to be created?
- **Authority:** Are you talking to the decision-maker? If not, can you get access?
- **Need:** Is there a genuine problem that your product solves?
- **Timeline:** Is there a deadline or event driving urgency?

### When BANT Works

BANT is appropriate when:
- The deal is relatively straightforward (under $50K)
- There's a single decision-maker
- The buying process is short (under 2 months)
- The prospect already knows they have a problem

### When BANT Falls Short

BANT misses critical elements for enterprise deals:
- It doesn't capture the champion -- who's fighting for you internally?
- It doesn't capture the decision process -- what are the steps?
- It doesn't capture competition -- who else is in the deal?
- It treats qualification as binary rather than as a spectrum

### MEDDPICC vs BANT Comparison

| Dimension | BANT | MEDDPICC |
|---|---|---|
| Complexity handled | Simple/mid-market | Enterprise/complex |
| Number of elements | 4 | 8 |
| Champion identification | No | Yes |
| Competitive awareness | No | Yes |
| Process mapping | No (just "timeline") | Yes (Decision Process + Paper Process) |
| Metrics/ROI | Implicit in "Need" | Explicit (Metrics) |
| Best for deal size | < $50K | > $50K |
| Time to assess | 5 minutes | 30+ minutes over multiple calls |

### Qualifying Out

One of the hardest skills in sales is knowing when to walk away. Every hour you spend on a deal that won't close is an hour you didn't spend on one that will.

**Signals to qualify out:**
- No identifiable pain (they're just "exploring")
- No budget and no event that would create budget
- No access to the economic buyer after multiple attempts
- The decision criteria are so specific to a competitor that you can't win
- The timeline is 12+ months with no forcing function

**How to qualify out gracefully:**
- "Based on what you've shared, it sounds like this might not be the right time for us. Would it make sense to reconnect in Q3 when your new budget cycle starts?"
- "I want to be respectful of your time. It sounds like [competitor feature] is a hard requirement, and that's not something we offer today. I'd rather be honest about that now than waste your team's time in a POC."

### Deal Qualification Scoring

Score each element on a 1-3 scale:

| Score | Meaning |
|---|---|
| 1 | Unknown or unfavorable |
| 2 | Partially known, some risk |
| 3 | Fully understood and favorable |

**Composite score interpretation:**
- BANT: 10-12 = strong, 7-9 = moderate, 4-6 = weak
- MEDDPICC: 20-24 = strong, 14-19 = moderate, 8-13 = weak

---

## Building a Discovery Call Template

### Pre-Call Research Checklist

Before any discovery call, invest 15-30 minutes in research. The more you know going in, the fewer Situation questions you waste time on.

| Source | What to Look For |
|---|---|
| **LinkedIn** | Prospect's role, tenure, career history. Other attendees. Company size, recent hires. |
| **Company website** | Product, customers, pricing model. "About" and "Careers" pages for culture signals. |
| **10-K / Annual report** (public companies) | Revenue, growth rate, stated risks, technology spend, strategic priorities. |
| **Engineering blog** | Technology stack, architecture decisions, problems they've solved (and problems they're still facing). |
| **Job postings** | Technologies in use (job req lists them). Teams they're building. Seniority of hires (building a new team = new initiative). |
| **G2 / Gartner / TrustRadius** | Reviews they've written (reveals tools in use). Reviews of your competitors. |
| **CRM history** | Have they talked to your company before? What happened? Any notes from previous calls? |
| **News / press releases** | Funding rounds, acquisitions, partnerships, product launches. Anything that changes priorities. |

### Call Structure Template

A well-structured 35-minute discovery call:

**1. Introduction (2-3 minutes)**
- Thank them for their time
- Confirm attendees and roles
- Set the agenda: "I'd love to spend most of our time understanding your situation and challenges. If it makes sense, we can discuss how we might help toward the end."
- Ask permission: "Would it be okay if I ask a lot of questions? I want to make sure I understand your world before talking about ours."

**2. Current State (8-10 minutes)**
- "Walk me through your current setup for [relevant process]."
- "Who's involved in this workflow day to day?"
- "How long have you been doing it this way?"
- Reference your pre-call research: "I noticed you're hiring for X -- is that related to this initiative?"

**3. Pain and Impact (12-15 minutes)**
- "What's working well? What's not?"
- "When was the last time this caused a real problem? What happened?"
- "What does that cost you in terms of [time / money / customer impact / team morale]?"
- "What have you tried to solve this?"
- "If this doesn't get solved in the next 6 months, what happens?"

**4. Desired State (5-7 minutes)**
- "In an ideal world, what would this look like?"
- "What would 'great' look like 12 months from now?"
- "What would change about your team's day-to-day if this problem went away?"
- "How would you measure success?"

**5. Next Steps (3-5 minutes)**
- Summarize what you heard: "Let me play back what I think I heard..."
- Confirm priorities: "Of everything we discussed, what's the most important to solve first?"
- Propose next step: "Would it make sense for me to put together a tailored demo focused on [specific pain]? I could bring in [relevant team member] and show you exactly how we'd approach [their problem]."
- Set timeline: "When would work for that? I'd suggest next Tuesday or Wednesday."

### Note-Taking During Discovery

**What to capture:**
- Direct quotes (especially pain statements -- these become your demo narrative)
- Named stakeholders and their roles
- Specific metrics they mentioned
- Competitors they've evaluated
- Timeline pressures or deadlines
- Technical constraints and requirements
- Emotional language ("frustrated," "nightmare," "workaround," "we hate")

**Note-taking format (one approach):**
```
PAIN: "We spend 2 hours every morning reconciling data between systems" (Sarah, Data Lead)
METRIC: 10 engineers * 2 hours/day = 20 engineering hours/day wasted
STAKEHOLDER: VP Eng (Jamie) owns the budget; Sarah is the champion
COMPETITOR: Evaluated Fivetran last quarter, liked the connectors but hated the pricing
TIMELINE: New VP starts in Q2 and will audit all tooling
CONSTRAINT: Must support on-prem Postgres; cannot use SaaS-only solution
```

---

## Active Listening and Note-Taking

### Listening for Pain vs Symptoms

Prospects often describe symptoms rather than root causes. Your job is to dig deeper.

| Symptom (surface) | Pain (root cause) | Question to dig deeper |
|---|---|---|
| "Our dashboards are slow" | Data pipeline can't keep up with growth | "What decisions get delayed when the dashboards are slow?" |
| "We need more engineers" | Current tooling creates too much toil | "What are those engineers spending time on that you wish they weren't?" |
| "We want to migrate to the cloud" | On-prem infrastructure is limiting innovation | "What can't you do today that you could do in the cloud?" |
| "We're evaluating observability tools" | They've had outages they couldn't diagnose | "What was the last incident that made you realize you needed better observability?" |

### The "Tell Me More" Technique

The three most powerful words in discovery are "tell me more." When a prospect says something interesting, resist the urge to respond with a solution. Instead:

- "Tell me more about that."
- "Can you give me an example?"
- "What does that look like in practice?"
- "Help me understand -- when you say 'complex,' what do you mean?"
- "How does that affect you personally?"

Each follow-up peels back another layer and gets you closer to the real pain.

### When to Go Off-Script

A discovery template is a guide, not a prison. Go off-script when:
- The prospect reveals unexpected pain that's more significant than what you planned to explore
- The conversation is flowing naturally in a productive direction
- You hear something that contradicts your pre-call assumptions
- The emotional energy in the room shifts (someone gets animated, frustrated, or quiet)

Come back to your template when the conversation drifts to topics that don't help you qualify or understand the deal.

---

## Practice Exercises

The following exercises in `exercises.py` directly practice concepts from this file:

- **Exercise 1: Discovery Call Scorer** -- Practices SPIN categorization and call balance scoring. Requires understanding the SPIN framework from the "SPIN Selling for SEs" section, including what distinguishes each question type and what a well-balanced discovery call looks like. See the SPIN Balance and Sequencing table for ideal percentages.

- **Exercise 2: MEDDPICC Gap Analyzer** -- Directly applies the MEDDPICC framework from the "MEDDPICC Deep Dive" section. Requires understanding each element, what "Green" vs "Red" looks like for each, and which gaps are most critical at different deal stages. Reference the MEDDPICC Scorecard Template.

- **Exercise 3: Deal Qualification Scorer** -- Implements the dual-framework scoring approach from the "Qualification Frameworks" section. Requires understanding both BANT and MEDDPICC, when each is appropriate, and how to compute composite qualification scores. See the Deal Qualification Scoring subsection.

See also `examples.py` sections 1 (MEDDPICC Evaluator) and 2 (Discovery Call Template Engine) for complete runnable reference implementations.

---

## Interview Q&A: Discovery Methodology

**Q: How do you approach a discovery call with a prospect who just wants to see a demo?**

The most common mistake is complying immediately. When a prospect says "just show me the product," they usually mean "I don't have time for a generic conversation." The right response is to reframe discovery as being in their interest: "I'd love to show you the product, and I want to make sure I show you the parts that are most relevant to your situation. Can I ask you a few quick questions first so I don't waste your time on features that don't matter to you?" This usually buys you 10-15 minutes of discovery. During that time, focus on Problem and Implication questions -- skip Situation questions entirely. If the prospect truly refuses any discovery, run the demo but weave discovery questions into the demo itself: "How are you handling this today?" as you show each feature.

**Q: How do you identify a champion vs someone who is just friendly?**

A friendly contact will take your meetings, give you positive feedback, and say things like "this looks great!" But they won't do anything when you're not in the room. A champion will proactively give you information you didn't ask for, tell you about internal politics, coach you on what to say to the economic buyer, and push the process forward even when you're not asking them to. Test for championship by asking the contact to do something: "Could you forward our proposal to the VP with your recommendation?" If they do it, they're a champion. If they hesitate or deflect, they're a friendly contact. You need both, but only a champion can close a deal.

**Q: What do you do when MEDDPICC reveals major gaps in a deal your AE is counting on?**

This is a common tension. The SE's job is to be honest about deal health, not to tell the AE what they want to hear. The best approach is to present the gaps constructively: "I mapped out our MEDDPICC scorecard for this deal. We're strong on Pain and Champion, but we have red on Economic Buyer and Decision Process. I think we need to do X and Y to derisk this deal before we can forecast it with confidence." Frame it as a plan, not a criticism. Good AEs appreciate this because it gives them actionable steps. If the AE pushes back, escalate gently to your SE manager -- your forecast integrity is more important than any single deal relationship.

**Q: How do you handle a discovery call where the prospect gives only surface-level answers?**

Some prospects are guarded because they've been burned by vendors before, or because they don't yet trust you with real information. Techniques for going deeper: (1) Share a relevant anonymized story from another customer: "One of our customers in a similar situation found that X was costing them Y -- does that resonate?" This gives them permission to share. (2) Ask about specific past events instead of generalizations: "Can you tell me about the last time this system went down?" is better than "Do you have reliability issues?" (3) Acknowledge the dynamic directly: "I know I'm asking a lot of questions. The reason is that I've seen too many demos that didn't address the real problem, and I don't want to waste your time." Honesty and transparency build trust faster than any technique.
