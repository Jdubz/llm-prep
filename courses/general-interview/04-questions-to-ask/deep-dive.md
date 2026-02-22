# Module 04 Deep Dive: Questions to Ask Interviewers — Advanced Topics

## Overview

This deep dive goes beyond the standard question bank into the interpretive and strategic dimensions: reading between the lines of answers, evaluating engineering maturity, tailoring questions to company stage, and asking questions that signal staff-level thinking.

---

## Table of Contents

1. [Reading Between the Lines](#reading-between-the-lines)
2. [Evaluating Engineering Maturity](#evaluating-engineering-maturity)
3. [Questions for Different Company Stages](#questions-for-different-company-stages)
4. [Questions for Specific Roles](#questions-for-specific-roles)
5. [Questions That Differentiate Senior from Staff Candidates](#questions-that-differentiate-senior-from-staff-candidates)

---

## Reading Between the Lines

What interviewers say and what they mean are often different. Learning to interpret answers is a critical skill for evaluating fit.

### Decoding Common Responses

**"We move fast."**
- Best case: Strong CI/CD, autonomous teams, quick decision-making.
- Worst case: No planning, no tests, constant firefighting. Ask follow-up: "What does that look like day-to-day? How do you balance speed with quality?"

**"We have a flat structure."**
- Best case: Low bureaucracy, anyone can propose ideas, decisions are merit-based.
- Worst case: No career ladder, unclear reporting lines, promotions are political. Ask follow-up: "How does that affect career progression? How are decisions made when people disagree?"

**"We're data-driven."**
- Best case: Hypotheses are tested, decisions are backed by metrics, there is a culture of experimentation.
- Worst case: Everything requires a dashboard before acting, analysis paralysis, gut instincts are dismissed even when appropriate. Ask follow-up: "Can you give me an example of a decision that was changed based on data?"

**"We're like a startup within a big company."**
- Best case: Autonomy of a startup with resources of a big company. Innovation is encouraged.
- Worst case: All the chaos of a startup with all the bureaucracy of a big company. The worst of both worlds. Ask follow-up: "What resources from the parent company does the team actually use? What does the autonomy look like in practice?"

**"The work-life balance is what you make of it."**
- Best case: Flexible environment where people manage their own time.
- Worst case: Overwork is normalized and blamed on the individual. Ask follow-up: "What time do people typically log off? How often do people work weekends?"

**"We're going through a transition."**
- Best case: Healthy growth, evolving from startup to scale-up, deliberate process improvements.
- Worst case: Layoffs, reorgs, leadership changes, strategic confusion. Ask follow-up: "What is driving the transition? What does it mean for this team specifically?"

**"We hire the best."**
- Best case: Rigorous hiring standards, strong team.
- Worst case: Elitist culture, interview process selects for pedigree over capability, difficult to work with. Ask follow-up: "What do you look for beyond technical skills?"

### The Follow-Up Pattern

The most revealing information comes from follow-up questions. The initial answer is often the rehearsed version. The follow-up gets closer to reality.

```
Your question:   "How do you handle tech debt?"
Their answer:    "We prioritize it regularly."
Your follow-up:  "Can you give me a recent example of a tech debt
                  item that was prioritized and completed?"
```

If they can give a specific example with details, the practice is real. If they struggle to produce an example, the answer was aspirational.

### Body Language and Delivery

Pay attention to HOW the interviewer answers, not just what they say:
- **Enthusiasm:** If they light up talking about the team or product, that is a genuine signal of a good environment.
- **Hesitation:** If they pause or hedge before answering questions about culture or process, there is likely something they are not saying.
- **Eye-rolling or sarcasm:** If they subtly dismiss their own company's practices, believe them.
- **Deflection:** If they redirect your question to a different topic, the original topic is likely a sore point.
- **Recruitment mode:** If every answer sounds like a pitch, they are selling, not sharing. Push for specifics.

---

## Evaluating Engineering Maturity

The DORA (DevOps Research and Assessment) metrics provide a research-backed framework for evaluating engineering team maturity. You can assess all four through interview questions.

### The Four Key Metrics

| Metric | Elite | High | Medium | Low |
|--------|-------|------|--------|-----|
| Deployment frequency | On demand (multiple/day) | Daily to weekly | Monthly | Quarterly or less |
| Lead time for changes | Less than 1 hour | 1 day to 1 week | 1 to 6 months | More than 6 months |
| Change failure rate | 0-15% | 16-30% | 31-45% | 46%+ |
| Mean time to recovery | Less than 1 hour | Less than 1 day | 1 day to 1 week | More than 1 week |

### Questions That Reveal Each Metric

**Deployment frequency:**
- "How often do you deploy to production?"
- "Is deployment automated?"
- "Can any engineer deploy, or is there a gatekeeper?"

**Lead time for changes:**
- "How long does it take from code commit to running in production?"
- "What are the steps between merging code and it being live?"
- "What is the typical size of a deployment?"

**Change failure rate:**
- "How often do deployments cause issues?"
- "Do you have canary deployments or feature flags?"
- "What happens when a deployment goes wrong?"

**Mean time to recovery:**
- "How quickly can you roll back a bad deployment?"
- "What was the last significant incident and how long did it take to resolve?"
- "Do you have automated rollback?"

### Additional Maturity Indicators

**Testing maturity:**
- "What kinds of tests do you run? (unit, integration, e2e)"
- "What is your test coverage like?"
- "Are tests required before merge?"
- Mature: Multiple test layers, high coverage, tests gate deployment.
- Immature: "We need to write more tests" or reliance on manual QA.

**Observability maturity:**
- "What monitoring and alerting tools do you use?"
- "How do you know when something is wrong?"
- "Can you trace a request through the system?"
- Mature: Structured logging, distributed tracing, actionable alerts, dashboards.
- Immature: "We check logs when something breaks" or "our alerts are noisy."

**Documentation maturity:**
- "Where does an engineer go to understand how a system works?"
- "Do you have runbooks for operational tasks?"
- "How do you onboard new engineers?"
- Mature: Up-to-date architectural docs, runbooks, onboarding guides.
- Immature: "Ask someone who worked on it" or "read the code."

---

## Questions for Different Company Stages

### Early-Stage Startup (Seed to Series A)

The priorities are different at a 10-person startup than at a 10,000-person enterprise. Your questions should reflect the stage.

**Questions to ask:**
- "What is the runway? How long until you need to raise again?"
- "How many customers do you have? What is the revenue trajectory?"
- "What does the equity package look like? What was the last 409A valuation?"
- "How do you decide between building fast and building well?"
- "What is the biggest existential risk to the company right now?"
- "Who are the technical co-founders and what are their backgrounds?"
- "What does a day in the life look like for an engineer here?"
- "How many engineers are there and what are their backgrounds?"

**What you are evaluating:**
- Is this company likely to survive long enough for my equity to matter?
- Will I enjoy the pace and ambiguity of early-stage work?
- Is the founding team technically strong and personally trustworthy?
- Will I have real ownership and influence?

### Growth-Stage Startup (Series B to pre-IPO)

**Questions to ask:**
- "How has the engineering team scaled? What growing pains have you experienced?"
- "Are you building process, or is it still early-stage chaos?"
- "What is the biggest scaling challenge right now — people, technology, or process?"
- "How do you balance feature velocity with reliability as you grow?"
- "What is the IPO or exit timeline, if any?"
- "How has the culture changed as the company has grown?"
- "What systems are you proud of and what systems keep you up at night?"

**What you are evaluating:**
- Is the company navigating growth well?
- Is there a place for senior/staff engineers to have impact?
- Are they building sustainable practices or just sprinting forever?
- Is the equity still valuable?

### Enterprise / Large Public Company

**Questions to ask:**
- "How does this team's work connect to the company's strategic priorities?"
- "How much autonomy does this team have?"
- "How do you avoid the big-company slowdown?"
- "What is the biggest bureaucratic obstacle to getting things done?"
- "How are promotions handled? What is the calibration process?"
- "How do you attract and retain senior talent?"
- "What is the refresher grant policy for equity?"
- "How does the company handle re-orgs?"

**What you are evaluating:**
- Will I have enough autonomy to do meaningful work?
- Is the career ladder real and achievable?
- Are the people I would work with energized or burnt out?
- Is the compensation structure (especially equity refreshers) sustainable long-term?

---

## Questions for Specific Roles

### IC vs Manager Track

If you are exploring both paths, or want to ensure the IC track is real:

**IC-specific questions:**
- "What is the most senior IC level at the company? Who holds it?"
- "Do staff/principal engineers report to engineering managers or directors?"
- "Is the IC track parallel to the management track in terms of compensation and influence?"
- "What does a staff engineer's day-to-day look like here?"
- "Can you give me an example of a technical decision that was driven by a staff IC rather than a manager?"

**What to watch for:**
- If there are no staff or principal ICs, the track may not truly exist.
- If all technical decisions are made by managers, ICs are executors, not leaders.
- If IC comp is significantly lower than manager comp at the same level, the track is second-class.

### Platform vs Product Engineering

**Platform-specific questions:**
- "Who are the internal customers of the platform team?"
- "How do you prioritize platform work vs product team requests?"
- "How do you measure the success of a platform team?"
- "What is the platform team's relationship with product engineering?"
- "Do product engineers contribute to the platform, or is it a separate team?"

**Product-specific questions:**
- "How closely do engineers work with designers and product managers?"
- "How do you measure the success of a feature after launch?"
- "How much influence do engineers have on the product roadmap?"
- "What is the balance between new feature development and maintenance?"

### Founding Engineer / Early Employee

**Questions to ask:**
- "What is the equity structure? What is the vesting schedule and cliff?"
- "What is my percentage ownership on a fully diluted basis?"
- "Who makes technical architecture decisions today?"
- "What is the expected team size in 12 months?"
- "How would my role evolve as the team grows?"
- "What is the board composition? Who are the key investors?"
- "What decisions have been deferred that I would need to address?"
- "Are there existing technical decisions I should know about that constrain future choices?"

**What you are evaluating:**
- Is the equity meaningful?
- Will I have genuine technical influence?
- Is the founding team someone I want to work with daily?
- Is there a path from "founding engineer" to "VP of Engineering" or "CTO" as the company grows?

---

## Questions That Differentiate Senior from Staff Candidates

The questions you ask signal how you think. Here is how the same topic plays at different levels.

### Level-Appropriate Question Pairs

**Topic: Technical Strategy**

Senior-level question: "What technologies is the team using?"
Staff-level question: "How does the team evaluate and adopt new technologies? Is there a formal process, or does it happen organically?"

**Why the staff version is stronger:** It focuses on the decision-making process and organizational dynamics, not just the current state.

**Topic: Team Challenges**

Senior-level question: "What is the biggest challenge the team faces?"
Staff-level question: "What is the biggest challenge the engineering organization faces, and how does this team's work contribute to solving it?"

**Why the staff version is stronger:** It zooms out to the organizational level and connects the team's work to the bigger picture.

**Topic: Technical Debt**

Senior-level question: "How do you handle tech debt?"
Staff-level question: "How do you balance investing in platform reliability versus feature delivery? Who makes that trade-off and how?"

**Why the staff version is stronger:** It frames tech debt as a strategic trade-off rather than a tactical problem and asks about decision-making authority.

**Topic: Success Metrics**

Senior-level question: "How will my performance be evaluated?"
Staff-level question: "What would a successful first year look like for the person in this role? What would make you say, six months in, that this hire was a great decision?"

**Why the staff version is stronger:** It focuses on impact and outcomes rather than process, and invites the interviewer to paint a picture of success.

**Topic: Growth**

Senior-level question: "What are the opportunities for growth?"
Staff-level question: "What are the biggest unsolved technical problems in the organization that a staff engineer could own?"

**Why the staff version is stronger:** It asks about the work, not the title. It shows you are looking for problems to solve, not promotions to collect.

### Meta-Questions That Signal Staff Thinking

These questions signal that you think about systems, organizations, and strategy — not just individual tasks:

- "What is the biggest bet the engineering organization is making right now, and what happens if it does not work out?"
- "If you could change one thing about how the engineering organization operates, what would it be?"
- "How does the company think about build vs buy decisions?"
- "What is the relationship between engineering leadership and the executive team?"
- "How does technical strategy feed into company strategy, and vice versa?"

### The Difference in How You Listen

Staff candidates do not just ask better questions — they listen differently.

When a senior candidate hears: "We deploy twice a week"
They think: "Okay, that's the process."

When a staff candidate hears: "We deploy twice a week"
They think: "Why twice a week? Is that a cultural choice, a testing bottleneck, or a risk management approach? Could they deploy more frequently if they invested in automation? Would faster deployment cycles improve the team's velocity? This might be an area where I could have impact."

The depth of your listening and the quality of your follow-up questions reveal whether you think at the team level or the organizational level.

---

## Key Takeaways

1. **Follow-up questions reveal more than initial questions.** The first answer is often the polished version. The follow-up gets to reality.

2. **Use the DORA metrics as a maturity assessment framework.** Deployment frequency, lead time, change failure rate, and recovery time tell you a lot about engineering health.

3. **Tailor questions to company stage.** A startup and an enterprise have different strengths and risks. Your questions should reflect that.

4. **Role-specific questions prevent surprises.** Understanding IC vs manager track, platform vs product, and founding engineer dynamics helps you evaluate whether the role matches your expectations.

5. **Staff-level questions focus on systems and strategy, not tasks and tools.** The altitude of your questions signals the altitude of your thinking.

6. **Pay attention to what they do NOT say.** Evasion, hesitation, and deflection are all data points about culture and health.
