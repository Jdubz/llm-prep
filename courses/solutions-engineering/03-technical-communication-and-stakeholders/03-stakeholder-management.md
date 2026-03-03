# 03 -- Stakeholder Management

Deals are not won by products. They are won by people inside the customer's organization who decide your product is worth buying. The SE's job is to identify those people, understand their motivations, build relationships with the ones who will help, neutralize the ones who will not, and navigate the organizational dynamics that determine whether a deal closes. This file covers stakeholder mapping, champion-building, blocker management, multi-threading, internal stakeholder management, organizational politics, and consensus building.

---

## Stakeholder Mapping

### Identifying All Players in a Deal

Most deals involve more people than you initially realize. The person you meet first is rarely the person who signs the check, and the person who signs the check is rarely the person who decides the technical direction. Map everyone.

Start by asking your initial contact: "Who else is involved in evaluating and deciding on a solution like this?" Then probe further:

- "Who would need to approve the budget for this?"
- "Is there a security or compliance review process?"
- "Who on your engineering team would implement this?"
- "Is there anyone who has tried to solve this problem before?"
- "Who would be most affected if this project succeeds or fails?"

### The Power/Interest Grid

Map each stakeholder on two axes: **power** (ability to influence the decision) and **interest** (how much they care about the outcome).

```
                    HIGH POWER
                        |
    Keep Satisfied      |      Manage Closely
    (Executives who     |      (Decision-makers who
     approve but don't  |       are actively engaged)
     evaluate)          |
                        |
   ─────────────────────┼─────────────────────
                        |
    Monitor             |      Keep Informed
    (Peripheral          |      (Evaluators, users
     stakeholders)      |       who influence but
                        |       don't decide)
                        |
                    LOW POWER

         LOW INTEREST ──────── HIGH INTEREST
```

### Stakeholder Roles

Every deal has people who fill these roles. One person can fill multiple roles.

| Role | Definition | How to Identify | What They Need From You |
|---|---|---|---|
| **Champion** | Wants your product to win and will advocate internally | They proactively share information, ask how to help, and tell you about internal dynamics | Internal ammunition: ROI data, comparison docs, answers to objections they will face |
| **Coach** | Gives you information about the organization but may not actively advocate | They answer your questions honestly and warn you about obstacles, but do not take action on your behalf | Respect for their position; do not push them to become a champion if they cannot |
| **Blocker** | Actively or passively working against your deal | They raise objections repeatedly, delay meetings, require additional evaluations, or champion a competitor | Depends on why they are blocking (see "Handling Blockers" below) |
| **Economic Buyer** | Has the authority and budget to sign the contract | Ask directly: "Who ultimately approves the budget for this?" Often a VP or C-level exec | Clear business case, ROI, risk mitigation, executive summary |
| **Technical Evaluator** | Runs the POC, tests the integration, writes the technical assessment | They are the ones asking detailed API questions and requesting sandbox access | Honest technical information, hands-on support, fast response to technical questions |

### Stakeholder Map Template

For every deal, maintain a stakeholder map. Update it after every meeting.

```
Deal: [Customer Name] -- [Opportunity Name]
Last updated: [Date]

| Name | Title | Role(s) | Power | Interest | Disposition | Strategy | Last Contact |
|------|-------|---------|-------|----------|-------------|----------|--------------|
| Sarah Chen | VP Engineering | Economic Buyer, Technical Leader | High | Medium | Neutral | Build business case; schedule exec summary session | 2026-02-15 |
| James Park | Sr. Staff Engineer | Technical Evaluator, potential Champion | Medium | High | Positive | Support POC; provide code samples; build trust | 2026-02-18 |
| Maria Lopez | CISO | Blocker (security concerns) | High | Medium | Negative | Address security concerns proactively; share SOC 2 report | 2026-02-10 |
| David Kim | Director of Ops | Business Stakeholder, Coach | Medium | High | Positive | Use as source of internal intel; provide ROI for his team | 2026-02-17 |
| Lisa Wang | CTO | Economic Buyer (final) | Very High | Low | Unknown | Need champion to arrange meeting; prepare architecture overview | Not yet met |
```

---

## Building Champions

Champions are the single most important factor in winning enterprise deals. A champion sells for you when you are not in the room. They navigate internal politics. They tell you what is really happening. Without a champion, you are guessing.

### What Makes Someone a Champion

A true champion has three qualities:

1. **Access**: They have the relationships and organizational standing to influence the decision
2. **Motivation**: They have a personal reason for your product to win (career advancement, problem resolution, team efficiency)
3. **Willingness to act**: They will spend their political capital to advocate for you

A person who likes your product but will not advocate internally is a supporter, not a champion. A person who advocates but has no organizational influence is an enthusiast, not a champion. You need all three.

### How to Identify Potential Champions

| Signal | Why It Matters |
|---|---|
| They ask "How can I help move this forward?" | They are invested in the outcome |
| They share internal information you did not ask for | They trust you and want you to succeed |
| They tell you about competing solutions being evaluated | They want you to win the comparison |
| They suggest meetings with other stakeholders | They are actively selling internally |
| They share their personal pain with the current state | They have a personal stake in solving the problem |
| They push back on your weaknesses constructively | They want to prepare you for internal objections |

### Nurturing Champions

Champions need fuel. They are going into internal meetings and advocating for you, and they need materials and information to do that effectively.

**Give them:**

- **ROI calculators and business cases** they can present to their leadership
- **Comparison documents** that honestly position you against alternatives (including build-in-house)
- **Answers to objections** they will face from skeptics ("What about security? What about cost? What about the competitor?")
- **Early access to features or roadmap** that makes them feel like an insider
- **Reference customers** they can call directly
- **Presentation slides** they can reuse in internal meetings

**Do not:**

- Put them in a position where they look uninformed (always share news with them first)
- Ask them to make promises about your product you cannot keep
- Go around them or over their head without warning
- Treat them as a one-way information source without providing value back

### The Champion Test

Ask yourself: "If I left this deal and came back in a week, would this person have continued to advocate for our product in my absence?"

If the answer is yes, you have a champion. If the answer is "only if I keep pushing," you have a supporter who needs more nurturing.

---

## Handling Blockers

Blockers are inevitable in enterprise deals. Not everyone wants change, and not everyone wants your product. Understanding why someone is blocking is the key to deciding how to respond.

### Why People Block Deals

| Blocker Type | Root Cause | Example |
|---|---|---|
| **Technical Skeptic** | Genuine concerns about fit, performance, or architecture | "I don't think this will scale for our use case" |
| **Political Blocker** | Your product threatens their project, team, or influence | "We've been building something internally for 6 months -- why would we buy this?" |
| **Competitive Preference** | They prefer a competitor (sometimes for valid reasons) | "I used [competitor] at my last company and it was great" |
| **Fear of Change** | Risk aversion, comfort with the status quo | "Our current system works fine -- why change?" |
| **Compliance Gatekeeper** | Responsible for security/compliance and doing their job | "This doesn't meet our data residency requirements" |

### Strategies for Each Type

**Technical Skeptic:**
- Take their concerns seriously -- they may be right
- Offer a focused POC that specifically addresses their concern
- Provide benchmark data, reference architectures, and customer references
- Invite them to participate in the evaluation (they often become champions once their concerns are addressed)

**Political Blocker:**
- Understand what they have to lose
- Find a way to make your product complementary to their work, not a replacement
- If possible, position the solution as something that makes their project more successful
- Sometimes the answer is to go around them -- but only with your champion's guidance

**Competitive Preference:**
- Respect their experience with the competitor
- Focus on the specific requirements of this deal, not generic feature comparisons
- Offer a side-by-side evaluation if appropriate
- Ask: "What specifically worked well for you with [competitor]?" Then address those points

**Fear of Change:**
- Emphasize low-risk adoption paths (phased rollout, parallel running, easy rollback)
- Provide reference customers who had similar concerns
- Quantify the cost of not changing (the status quo has a cost too)
- Make the first step small and non-threatening

**Compliance Gatekeeper:**
- This is not actually a blocker -- this is a stakeholder doing their job
- Proactively provide security documentation, compliance certifications, and architecture diagrams
- Offer to do a security review call with your security team
- Be patient and thorough -- rushing compliance review signals that you have something to hide

### When to Go Around vs Through

| Situation | Approach |
|---|---|
| Legitimate technical concern | Go through: address the concern directly |
| Political blocker protecting turf | Go around: work with your champion to get the decision made at a higher level |
| Competitive preference with valid reasons | Go through: win on the merits |
| Fear of change from a key evaluator | Go through: reduce perceived risk |
| Compliance gatekeeper | Go through: provide everything they need |
| One person blocking despite organizational consensus | Go around: this is a management issue, not a technical one |

### When to Accept You Cannot Win Someone Over

Sometimes a blocker cannot be converted. Signs:

- They have a fundamental conflict of interest (your product replaces their project)
- They have a personal relationship with a competitor's sales team
- They have made a public commitment to a different approach and cannot reverse without losing face
- They simply do not like the product after fair evaluation

In these cases, do not waste energy trying to convert them. Instead, focus on building enough support around them that their objection is outweighed by organizational consensus.

---

## Multi-Threading

Multi-threading means having relationships with multiple people at multiple levels in the customer organization. It is the opposite of "single-threaded" -- where your entire deal depends on one contact.

### The Danger of Single-Threaded Deals

Single-threaded deals fail in predictable ways:

- Your contact leaves the company (deal dies)
- Your contact goes on vacation during the decision period (deal stalls)
- Your contact gets overruled by someone you have never met
- Your contact does not have the full picture and gives you incomplete information
- Your contact's priorities shift and your deal drops to the bottom of their list

**Rule: Every deal worth winning should have a minimum of 3 contacts across at least 2 levels.**

### How to Expand Relationships

| Technique | How It Works |
|---|---|
| **Ask for introductions** | "Would it be helpful to include [role] in our next conversation? I want to make sure we address their requirements." |
| **Propose a workshop** | "We'd love to run a hands-on workshop for your engineering team. Who should we invite?" |
| **Reference calls** | "One of our customers had a similar deployment. Would your [role] like to speak with theirs?" |
| **Executive sponsor matching** | Have your executive reach out to their executive (CRO to CRO, CTO to CTO) |
| **QBR or business review** | "We'd like to share a quarterly update. Can we include your [VP/Director]?" |
| **Content sharing** | Send relevant industry research, case studies, or benchmarks to people you haven't met yet (via your contact) |

### Multi-Threading Map

Track your relationship breadth:

```
EXECUTIVE LEVEL:     [ ] CTO    [x] VP Eng    [ ] CFO
DIRECTOR LEVEL:      [x] Dir Eng    [x] Dir Ops    [ ] Dir Security
IC LEVEL:            [x] Sr Eng (Champion)    [x] DevOps Lead    [ ] Data Eng
BUSINESS LEVEL:      [x] PM Lead    [ ] Ops Manager

Coverage: 5/11 stakeholders (45%)
Risk: No executive sponsor. No security contact. Need to multi-thread up and into security.
```

---

## Internal Stakeholder Management

SEs work with many internal teams. Managing these relationships well determines how much organizational support you get for your deals.

### Working with Account Executives (AEs)

The AE owns the relationship and the revenue number. You own the technical win. This partnership works when:

| AE Expects From SE | SE Expects From AE |
|---|---|
| Technical credibility in every meeting | Clear deal strategy and context before meetings |
| Honest assessment of technical fit | Access to customer stakeholders and meeting scheduling |
| POC execution on time and within scope | Political intelligence about the deal |
| Technical sections of proposals and RFPs | Heads-up on pricing, timeline, and competitive dynamics |
| Fast turnaround on customer technical questions | Protection from non-technical asks that waste SE time |
| Proactive identification of risks and blockers | Recognition when the technical win drives the deal |

**Common AE/SE friction points and how to handle them:**

- **AE promises features that don't exist.** Address privately, not in front of the customer. Agree on a talk track for the next meeting.
- **AE wants to skip discovery and go straight to demo.** Push back with "A demo without discovery means we're guessing what to show. 30 minutes of discovery saves us a wasted hour-long demo."
- **AE blames SE for a deal loss.** Request a joint post-mortem. Focus on facts, not blame.

### Working with Product Managers (PMs)

SEs are the richest source of customer feedback in the organization. PMs need this feedback, and SEs need PMs to build the features customers are asking for.

- **Aggregate feedback, don't relay individual requests.** "Three enterprise customers in the last month need SCIM provisioning" is better than "Acme wants SCIM."
- **Provide context, not just feature requests.** "Customers need SCIM because their security teams won't approve us without automated user provisioning. This is blocking deals worth $2M combined."
- **Accept the roadmap.** Once PM has made a prioritization decision, support it externally even if you disagree internally.

### Working with Engineering

SEs engage engineering for escalations, custom solutions, and product issues.

- **Respect their time.** Exhaust self-service options before escalating.
- **Provide reproduction steps.** "The API returns 500 when called with this payload" is better than "the API is broken."
- **Communicate urgency with context.** "This is blocking a $500K POC that has a decision date of March 15" helps them prioritize.
- **Close the loop.** When engineering fixes something, tell the customer and give engineering credit.

### RACI Matrix for SE Activities

| Activity | SE | AE | PM | Engineering | Leadership |
|---|---|---|---|---|---|
| Technical discovery | **R** | C | I | - | - |
| Demo delivery | **R** | C | I | - | - |
| POC execution | **R** | I | I | C | - |
| Architecture document | **R** | I | - | C | - |
| RFP technical sections | **R** | A | C | C | - |
| Deal strategy | C | **R** | - | - | I |
| Pricing and negotiation | C | **R** | - | - | A |
| Feature escalation | **R** | C | **A** | R | I |
| Custom solution build | **R** | I | C | C | A |
| Post-sale handoff | **R** | R | I | I | - |

R = Responsible, A = Accountable, C = Consulted, I = Informed

---

## Navigating Organizational Politics

Every organization has political dynamics that affect purchasing decisions. Ignoring politics does not make you neutral -- it makes you blind.

### Reading Political Dynamics

| Signal | What It Might Mean |
|---|---|
| Two departments both claim ownership of the problem | Turf war -- be careful not to pick a side publicly |
| Your contact warns you away from meeting someone | That person has power your contact is nervous about |
| A senior leader joins a meeting unexpectedly | The deal has escalated in importance (good or bad) |
| Your champion suddenly goes quiet | Something changed internally -- investigate |
| Requirements keep shifting | Multiple stakeholders with different agendas are taking turns |
| Someone asks for a very specific feature comparison | They are using your response to build a case (for or against you) |

### Turf Wars Between Departments

Common scenarios:

- **Engineering vs IT**: Engineering wants to self-serve; IT wants to control the vendor relationship
- **Business vs Engineering**: Business wants to buy a solution now; Engineering wants to build it
- **Central vs Distributed teams**: Central platform team vs individual product teams who want autonomy

**How to navigate:**

1. **Do not take sides.** Frame your product as benefiting both parties.
2. **Ask about governance.** "How do purchasing decisions like this typically get made here?" reveals the power structure.
3. **Propose a structure that gives everyone a win.** "The platform team manages the deployment; individual teams configure their own workflows."
4. **Let your champion navigate the politics.** They know the dynamics better than you.

### When to Stay Neutral vs Pick a Side

**Stay neutral when:**
- Both parties have legitimate concerns
- You don't understand the full dynamic yet
- The political fight predates your deal
- Picking a side would alienate a key decision-maker

**Pick a side when:**
- Your champion is on one side and asks for support
- One side is clearly the decision-maker and the other is advisory
- Neutrality is stalling the deal (someone needs to be the tiebreaker)
- Your product genuinely serves one team's needs better

Even when you pick a side, do it with respect for the other party. "We've designed the architecture to be managed by the platform team because centralized control aligns with your security requirements, and we will ensure the product teams have self-service access for their day-to-day needs."

---

## Consensus Building

Enterprise deals often require agreement from multiple stakeholders who have different priorities. Your job is to help them find common ground that includes your product.

### The "Each Person Gets One Requirement" Technique

When multiple stakeholders have competing priorities, use this approach:

1. Ask each stakeholder to name their single most important requirement
2. Write them all on a whiteboard or shared document
3. Show how your product addresses each one
4. Prioritize together -- "If we had to sequence these, what order would your team put them in?"

This technique works because it:
- Gives everyone a voice (reducing resentment)
- Surfaces the real priorities (not the stated ones)
- Creates a shared framework for evaluation
- Makes it easy to propose a phased approach

### Shared Success Criteria

Define success criteria that all stakeholders agree on before the evaluation starts. This prevents post-hoc goalpost-moving.

```
Success Criteria Agreement
Deal: [Customer Name]
Date: [Date]
Participants: [All stakeholders who agree]

We agree that [Your Product] will be considered successful if:
1. [Measurable criteria 1 -- e.g., "API latency < 100ms at p99 under 1000 rps"]
2. [Measurable criteria 2 -- e.g., "Integration with Snowflake completes in < 2 weeks"]
3. [Measurable criteria 3 -- e.g., "End-user satisfaction score > 4.0/5.0 in pilot"]
4. [Measurable criteria 4 -- e.g., "Passes security review without critical findings"]

Evaluation period: [Start] to [End]
Decision date: [Date]
Decision maker: [Name and title]
```

Get this in writing. Email it to all stakeholders after the meeting. Reference it throughout the evaluation. When stakeholders disagree later, you have a shared document to anchor the conversation.

### Phased Approaches

When consensus is hard, a phased approach gives everyone a win:

- **Phase 1** addresses the most urgent pain point (wins the operational team)
- **Phase 2** adds the integration that the architecture team cares about
- **Phase 3** delivers the reporting that leadership wants
- Each phase has its own success criteria and go/no-go decision

Phased approaches reduce risk (smaller initial commitment), build confidence (Phase 1 success fuels Phase 2 approval), and defuse political tension (everyone gets their priority addressed, just not all at once).

### Building Alignment Across Stakeholders

| Technique | When to Use |
|---|---|
| Joint discovery session with all stakeholders | Early in the deal, to surface all requirements at once |
| Individual 1:1s followed by a synthesis document | When stakeholders do not get along or have conflicting agendas |
| Reference customer call with a similar organization | When stakeholders are skeptical and need external validation |
| Workshop or hands-on evaluation | When stakeholders need to see the product in their context |
| Executive alignment meeting | When lower-level stakeholders have aligned but need leadership buy-in |
| Written success criteria agreement | Before any POC or formal evaluation |

---

## Practice Exercises

The following exercises in `exercises.py` practice concepts from this file:

- **Exercise 4: Stakeholder Mapper** -- Takes a list of contacts with roles and observed behaviors, categorizes each as champion/coach/blocker/economic buyer/evaluator, and generates relationship strategies. Applies the stakeholder mapping framework, power/interest grid, and strategy patterns from "Stakeholder Mapping" and "Building Champions" above.
- **Exercise 6: Meeting Follow-up Composer** -- Generates professional follow-up emails for different meeting types and attendees. Exercises the stakeholder-aware communication skills from "Internal Stakeholder Management."

See also `examples.py`:
- Section 2: "STAKEHOLDER ANALYSIS ENGINE" -- complete stakeholder mapping and strategy generator with scoring, categorization, and recommended actions.

---

## Interview Q&A: Stakeholder Management

**Q: Tell me about a time you identified and built a champion in a deal. What was the result?**

A strong answer follows the STAR format with specifics about champion identification and nurturing. For example: "During an evaluation with a large financial services customer, I noticed that one senior engineer -- let's call him James -- was asking unusually detailed questions during our technical deep-dive and pushing back constructively on areas where our product could improve. After the meeting, he stayed on the call to ask about our roadmap for a specific feature. I recognized these as champion signals: deep engagement, constructive challenge, and personal interest in the outcome. I followed up with a 1:1 call where I shared our detailed roadmap, gave him early access to a beta feature, and prepared a comparison document he could use in internal discussions. Over the next four weeks, James presented our architecture to his CTO, organized a developer workshop without being asked, and told me about a competing vendor's weaknesses. The deal closed at $350K, and James explicitly told us he had advocated for us in three internal meetings we were not part of. The key was recognizing early that his pushback was not resistance -- it was investment."

**Q: How do you handle a blocker in a deal? Give a specific example.**

"In a healthcare deal, the CISO was blocking our product because our encryption-at-rest used AES-256-GCM but their policy required FIPS 140-2 validated modules. This was a legitimate compliance concern, not political blocking. I did three things: First, I arranged a direct call between our security engineering lead and their CISO to discuss our encryption architecture in detail. Second, I worked with our product team to accelerate our FIPS 140-2 certification timeline and provided the CISO with a written commitment and projected certification date. Third, I proposed a phased deployment plan where we started with non-PHI data while the certification was in process. The CISO appreciated the direct engagement and transparency. He went from blocking the deal to approving a conditional deployment, and became a reference for future healthcare deals. The lesson: compliance gatekeepers are not the enemy. They are doing their job. Engage them directly, provide what they need, and earn their trust through transparency."

**Q: What is multi-threading and why is it important in enterprise sales?**

Multi-threading means building relationships with multiple contacts at multiple levels within the customer organization. It matters because single-threaded deals -- where you depend on one contact -- fail in predictable ways: that person leaves the company, goes on vacation, gets overruled, or deprioritizes your deal. In my experience, I aim for a minimum of three contacts across at least two organizational levels in every deal. I expand by asking for introductions ("Would it be helpful to include your DevOps lead in our architecture discussion?"), proposing workshops for broader teams, and matching executive sponsors (our VP to their VP). I track coverage on a simple map: executive level, director level, IC level, and business level. If I see gaps, I work with my champion to fill them. The most dangerous moment in a deal is when you realize you have only been talking to one person and they cannot make the decision alone.

**Q: How do you manage the relationship between an SE and an AE when there is a disagreement about deal strategy?**

The AE owns the deal strategy and the customer relationship. The SE owns the technical win. When we disagree, I default to direct, private conversation. For example, if the AE wants to skip discovery and go straight to a demo, I will say privately: "I understand the urgency, but if we demo without understanding their architecture, we risk showing the wrong use cases and losing credibility. A 30-minute discovery call now saves us a wasted demo later." I present my reasoning with the deal outcome in mind, not my personal preference. If the AE still disagrees after hearing my reasoning, I support their decision and do my best to make it work -- but I document my recommendation. The key principle is that disagreements happen in private and alignment happens in public. The customer should never see friction between the AE and SE. After the deal, if my concern was validated (or wrong), we discuss it in the retrospective so we both learn.

**Q: How do you build consensus among stakeholders who have conflicting requirements?**

I use a structured approach. First, I meet with each stakeholder individually to understand their number-one priority and the reasoning behind it. These 1:1s surface the real concerns that people will not voice in group settings. Second, I synthesize the requirements into a shared document and identify where they overlap and where they conflict. Third, I bring the group together and present the synthesis: "Here is what I heard from each of you. Three of these five requirements align perfectly. Two have tension. Let me propose a phased approach." The phased approach is the key tool -- Phase 1 addresses the most urgent pain that everyone agrees on, Phase 2 tackles the requirement that the engineering team cares about, Phase 3 delivers the reporting that leadership wants. This gives everyone a win without requiring them to sacrifice their priority. Before starting the evaluation, I get all stakeholders to sign off on shared success criteria in writing. This prevents goalpost-moving later and gives everyone a common framework to evaluate against.
