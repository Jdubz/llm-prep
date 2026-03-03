# Questions to Ask Framework

## Overview

The questions you ask in an interview reveal as much about you as the answers you give. Thoughtful, specific questions signal seniority, genuine interest, and strategic thinking. Generic questions — or no questions at all — signal the opposite.

At the senior/staff level, asking good questions serves three purposes:
1. **Signal:** It demonstrates that you think like a leader who evaluates environments, not just someone looking for any job.
2. **Evaluation:** The interview goes both ways. You are choosing where to spend the next 3-5 years of your career. The questions you ask are your primary tool for evaluating fit.
3. **Conversation:** Good questions transform the last 5-10 minutes of an interview from an awkward formality into a genuine exchange that builds rapport.

This guide organizes questions by category, explains WHY each question is valuable (what the answer reveals), and gives per-round guidance on which questions to use.

---

## Why Questions Matter

### The Seniority Signal

Junior candidates ask: "What languages do you use?"
Senior candidates ask: "How do you handle tech debt prioritization?"
Staff candidates ask: "How does the engineering organization influence product strategy?"

The altitude of your questions maps directly to the altitude of your thinking. Interviewers notice.

### The Evaluation Function

You are making a decision that affects your career, income, daily happiness, and professional growth for years. Five minutes of questions is not enough, but it is a start. Use it wisely.

What you are actually evaluating:
- Will I be able to do my best work here?
- Will I grow?
- Are the people I would work with competent and kind?
- Is the company stable and well-run?
- Does the day-to-day reality match what they are selling?

### The Rapport Opportunity

People enjoy talking about their own work. When you ask a genuine question about something the interviewer cares about, you create a moment of connection. That connection influences their overall impression of you.

---

## Engineering Culture Questions

### "How do you handle tech debt prioritization?"

**Why it is valuable:** This question reveals how the organization balances short-term delivery with long-term health. Companies that ignore tech debt burn out engineers. Companies that over-index on it ship too slowly.

**Good answers sound like:** "We dedicate 20% of each sprint to tech debt. The team proposes items, and we prioritize based on impact. Last quarter, we tackled the authentication service rewrite because it was blocking three feature teams."

**Concerning answers sound like:** "We just try to fit it in when we can." (Translation: it never gets done.) Or: "What tech debt?" (Either they are lying or they are too new to know.)

### "What is your deployment frequency?"

**Why it is valuable:** Deployment frequency is one of the strongest indicators of engineering maturity (per the DORA metrics research). Daily or multiple-times-daily deployments suggest strong CI/CD, good testing practices, and a culture of small, incremental changes.

**Good answers sound like:** "We deploy to production multiple times a day. We use feature flags for larger changes and have automated canary deployments."

**Concerning answers sound like:** "We do big releases every few weeks/months." (Higher risk, likely less automated, potentially painful deployment process.)

### "How do on-call rotations work?"

**Why it is valuable:** On-call policy tells you a lot about work-life balance, operational maturity, and how much the company invests in reliability.

**Good answers sound like:** "We have a rotation of 6 engineers, one week on/five weeks off. We have runbooks for common issues and our alert noise ratio is low. People are compensated for on-call time."

**Concerning answers sound like:** "Everyone is kind of always on-call." Or: "We get paged a lot but we're working on it." (They have been "working on it" for years.)

### "What does the code review process look like?"

**Why it is valuable:** Code review culture reflects the team's values around quality, learning, collaboration, and speed.

**Good answers sound like:** "Every change gets reviewed by at least one peer. Reviews usually happen within a few hours. We have style guides and linters to automate the trivial stuff, so reviews focus on design and logic."

**Concerning answers sound like:** "It depends on the person." (Inconsistent standards.) Or: "We're trying to do more of that." (They do not really do code review.)

### "How are technical decisions made?"

**Why it is valuable:** This tells you whether you will have a voice in technical direction or whether decisions are made top-down.

**Good answers sound like:** "We use an RFC process. Anyone can propose a design, and we have weekly architecture reviews where the team discusses significant decisions. The tech lead has final say, but input from the team is expected."

**Concerning answers sound like:** "The CTO/architect decides." (You will be an executor, not a contributor.) Or: "It's organic." (There is no process; decisions are ad hoc and potentially political.)

---

## Team Dynamics Questions

### "How is the team structured?"

**Why it is valuable:** Team structure determines your day-to-day experience, who you work with, and how decisions are made.

**Follow-up angles:**
- How many engineers? What are the sub-teams?
- Is it organized by feature, platform, or function?
- How do teams interact? Are there shared services?
- How autonomous are individual teams?

**Good answers sound like:** "We're a team of 8 engineers organized into two squads — one focused on the API platform and one on integrations. Each squad has a tech lead who drives technical decisions within the squad, and I coordinate across squads."

**Concerning answers sound like:** "We're restructuring right now." (Instability.) Or: "It's flexible." (There is no clear structure.)

### "How do you handle disagreements on technical direction?"

**Why it is valuable:** This reveals the team's conflict resolution maturity and whether disagreements are productive or toxic.

**Good answers sound like:** "We discuss trade-offs openly in design reviews. If we cannot reach consensus, the tech lead or engineering manager makes the call. We use 'disagree and commit' — once a decision is made, everyone supports it."

**Concerning answers sound like:** "We don't really have those." (Either the team is too homogeneous, or disagreements happen behind closed doors.) Or: "It can get heated." (Without follow-up about how they resolve it — potentially toxic.)

### "What is the ratio of senior to junior engineers?"

**Why it is valuable:** Too many juniors means you will spend most of your time mentoring and reviewing (which may or may not be what you want). Too many seniors means competition for impact and potentially slow decision-making.

**Good answers sound like:** "We have a healthy mix — about 40% senior, 40% mid, 20% junior. Seniors mentor juniors, and everyone contributes to design discussions."

**Concerning answers sound like:** "We're mostly junior." (You will be stretched thin.) Or: "We're all very senior." (Staff-level impact may be hard to carve out.)

### "What is the relationship between engineering and product?"

**Why it is valuable:** This determines how much influence you will have over WHAT gets built, not just HOW it is built.

**Good answers sound like:** "Engineers are involved in product discovery from the beginning. PMs set the direction, but engineers influence scope, prioritization, and technical feasibility."

**Concerning answers sound like:** "Product tells us what to build." (You are an order-taker.) Or: "We don't really have product management." (At a startup, this is common; at a larger company, it is chaos.)

---

## Growth and Career Development Questions

### "What does the path from senior to staff look like here?"

**Why it is valuable:** If you are targeting a staff role or want to grow into one, this question reveals whether the company has a real staff-level role or whether it is a title without substance.

**Good answers sound like:** "We have clear expectations for each level. Staff engineers are expected to drive technical strategy across teams, write RFCs for organization-wide decisions, and sponsor senior engineers for promotion. We currently have 3 staff engineers and here is what differentiates them from seniors..."

**Concerning answers sound like:** "It's pretty informal." (No clear growth path.) Or: "I'm not sure." (The interviewer has not seen anyone make that transition.) Or: "We don't really have staff engineers." (The title exists but the role does not.)

### "How are engineers evaluated?"

**Why it is valuable:** The evaluation process determines promotions, compensation, and daily incentives.

**Good answers sound like:** "We have semi-annual reviews with clear rubrics for each level. Engineers write self-reviews, get peer feedback, and have calibration discussions. The criteria include technical impact, collaboration, and mentorship."

**Concerning answers sound like:** "Your manager decides." (Subjective, potentially biased.) Or: "We're revamping the process." (The current process is broken.)

### "What does sponsorship look like for engineers here?"

**Why it is valuable:** Sponsorship (having a leader who advocates for you behind closed doors) is the primary mechanism for career advancement at the senior/staff level. Mentorship helps you grow. Sponsorship helps you get promoted.

**Good answers sound like:** "Engineering managers and senior staff actively sponsor their reports for stretch assignments and promotions. In my case, my manager advocated for me to lead the platform rewrite, which was a key factor in my promotion."

**Concerning answers sound like:** "What do you mean by sponsorship?" (The concept does not exist here.) Or: "You have to prove yourself." (Sink-or-swim culture without support.)

---

## Product and Business Questions

### "How do engineers influence product direction?"

**Why it is valuable:** At the senior/staff level, you want to shape what gets built, not just how. This question reveals whether engineering is a strategic partner or a service organization.

**Good answers sound like:** "Engineers participate in roadmap planning. Our tech leads present technical opportunities to product leadership quarterly, and several of our biggest initiatives last year were engineer-driven."

**Concerning answers sound like:** "Product sets the roadmap and we execute." (Limited agency.) Or: "Engineers can build whatever they want." (No product discipline; likely unfocused.)

### "How do you decide what to build next?"

**Why it is valuable:** This reveals the company's product development maturity and how data-informed their decisions are.

**Good answers sound like:** "We use a combination of customer feedback, usage data, competitive analysis, and technical opportunity. The product team runs discovery sprints to validate ideas before committing engineering resources."

**Concerning answers sound like:** "The CEO decides." (Founder-driven, potentially chaotic.) Or: "Whatever the biggest customer asks for." (Enterprise roadmap hostage.)

### "How do you measure success?"

**Why it is valuable:** This tells you what the company optimizes for, which determines what you will be rewarded for.

**Good answers sound like:** "We have clear KPIs for each team. Our team is measured on [specific metrics]. We review them monthly and adjust priorities based on what we learn."

**Concerning answers sound like:** "We're still figuring that out." (No clear direction.) Or: "Revenue." (Without nuance about how engineering contributes to revenue.)

---

## Process and Practices Questions

### "Walk me through how a feature goes from idea to production."

**Why it is valuable:** This single question reveals the entire development lifecycle: planning, design, implementation, testing, deployment, and monitoring.

**What to listen for:**
- Is there a design phase before coding?
- Are there code reviews?
- Is there automated testing?
- What does the deployment process look like?
- Is there a monitoring and feedback loop?
- How long does the cycle take?

**Good answers sound like:** "A product manager writes a brief. The engineering team discusses feasibility and approach. The assigned engineer writes a design doc for anything non-trivial, gets it reviewed, implements with tests, goes through code review, deploys behind a feature flag, and monitors metrics for a week before full rollout."

**Concerning answers sound like:** "It depends." (No consistent process.) Or a description that skips testing, review, or monitoring.

### "How do you handle incidents?"

**Why it is valuable:** Incident response reveals organizational maturity, blameless culture (or lack thereof), and how much the company invests in reliability.

**Good answers sound like:** "We have a structured incident response process with defined roles (incident commander, communicator, investigator). After resolution, we write blameless post-mortems and track action items. We review incident trends monthly."

**Concerning answers sound like:** "Everyone jumps in." (Chaotic.) Or: "We try to figure out who caused it." (Blame culture.)

### "What is your testing philosophy?"

**Why it is valuable:** Testing culture is a strong indicator of engineering maturity and code quality.

**Good answers sound like:** "We aim for high test coverage with a focus on integration tests. We have a test pyramid approach — lots of unit tests, fewer integration tests, and a small number of end-to-end tests. Tests must pass before merge."

**Concerning answers sound like:** "We want to do more testing." (They do not test.) Or: "QA handles testing." (Engineering does not own quality.)

---

## Role-Specific Questions

### "What does the first 90 days look like?"

**Why it is valuable:** A clear onboarding plan signals that the team has thought about setting you up for success. It also gives you a preview of early expectations.

**Good answers sound like:** "In the first 30 days, we expect you to ship a small feature to get familiar with the codebase and deployment process. By 60 days, you should own a moderate-sized project. By 90 days, we'd like you to start contributing to design discussions and identifying areas for improvement."

**Concerning answers sound like:** "You'll figure it out." (No onboarding.) Or: "We need you to hit the ground running." (Translation: we are behind and you will be thrown into the fire.)

### "What is the biggest challenge the team is facing right now?"

**Why it is valuable:** This tells you what you will actually be working on (vs the job description which may be aspirational) and whether the challenge is interesting to you.

**Good answers sound like:** Specific, honest descriptions of real challenges (scaling, tech debt, team growth, product-market fit). The interviewer should be able to articulate the challenge clearly.

**Concerning answers sound like:** "Everything is going great!" (Either dishonest or lacking self-awareness.) Or: "Where do I start..." (overwhelmed, potentially chaotic.)

### "Why is this role open?"

**Why it is valuable:** The answer reveals whether this is growth (good), backfill (neutral to concerning — why did the previous person leave?), or new headcount (good but may signal unclear role definition).

**Good answers sound like:** "We're growing the team because [specific business reason]." Or: "The previous person was promoted internally." Or, honestly: "The previous person left for a different opportunity, and we're looking for someone who can [specific need]."

**Concerning answers sound like:** Evasiveness about why the previous person left, or: "We've been trying to fill this for 6 months." (Why? Is the bar unrealistic, the comp too low, or the opportunity genuinely unappealing?)

---

## Questions by Interview Round

### Recruiter Screen (ask 2-3)
- "Can you walk me through the interview process and timeline?"
- "What level is this role, and what is the compensation range?"
- "How large is the engineering team, and how is it organized?"
- "Why is this role open?"

### Technical Interview — Peer (ask 2-3)
- "What does your day-to-day look like?"
- "What does the code review process look like?"
- "How often do you deploy, and what does the deployment process look like?"
- "What is the on-call situation?"
- "What would you change about the team if you could?"

### Engineering Manager (ask 2-3)
- "What does the first 90 days look like for this role?"
- "What is the biggest challenge the team is facing?"
- "How are engineers evaluated and promoted?"
- "What does the path from senior to staff look like?"
- "How does the team balance feature work with reliability and tech debt?"

### Skip-Level / VP (ask 2-3)
- "How does engineering strategy align with company strategy?"
- "What is the biggest bet the engineering org is making right now?"
- "How does the company think about build vs buy decisions?"
- "How do engineers influence product direction at the organizational level?"
- "What would a successful first year look like for this hire?"

### Culture / Team Match (ask 2-3)
- "What do you enjoy most about working here?"
- "How does the team handle disagreements?"
- "What is the balance between collaboration and individual focus time?"
- "If you could change one thing about how the team works, what would it be?"
- "How does the team celebrate wins?"

---

## Top 3 Questions Per Category (Quick Reference)

### Engineering Culture
1. "How do you handle tech debt prioritization?"
2. "What is your deployment frequency and process?"
3. "How are technical decisions made? Is there an RFC or design review process?"

### Team Dynamics
1. "How is the team structured, and how do sub-teams interact?"
2. "How do you handle disagreements on technical direction?"
3. "What is the relationship between engineering and product?"

### Growth and Career
1. "What does the path from senior to staff look like here?"
2. "How are engineers evaluated and promoted?"
3. "What does sponsorship look like for engineers at this level?"

### Product and Business
1. "How do engineers influence product direction?"
2. "How do you decide what to build next?"
3. "How do you measure the success of engineering work?"

### Process and Practices
1. "Walk me through how a feature goes from idea to production."
2. "How do you handle incidents and post-mortems?"
3. "What is your testing philosophy and practice?"

### Role-Specific
1. "What does the first 90 days look like for this role?"
2. "What is the biggest challenge the team is facing right now?"
3. "Why is this role open?"

---

## How Many Questions to Prepare

- Prepare 5-7 questions per round
- Ask 2-4 during the interview (depending on time)
- Prioritize questions that genuinely help you evaluate fit
- Skip questions whose answers you already know from research
- Never ask a question you could have answered with 5 minutes of Googling

### Quick Decision Framework

```
Step 1: What round is this?
  --> Match questions to the interviewer's role (see above)

Step 2: What do I MOST need to evaluate?
  --> Pick questions that address your top concerns
  --> If you have no concerns, focus on role-specific questions

Step 3: Have any of my prepared questions already been answered?
  --> Cross off anything covered during the interview
  --> Do NOT ask a question that was already answered

Step 4: How much time do I have?
  --> 5 minutes: Ask 2 questions
  --> 10 minutes: Ask 3-4 questions
  --> Always leave time for the interviewer to respond fully

Step 5: Read the room
  --> If rapport is strong, ask a personal question:
      "What do you enjoy most about working here?"
  --> If the interviewer is technical, go deeper:
      "Can you tell me more about the architecture of X?"
  --> If the interviewer seems rushed, ask one strong question
      and keep it concise
```

---

## Questions to NEVER Ask

### In Any Round

| Question | Why it is bad |
|----------|---------------|
| "What does the company do?" | Shows you did zero research |
| "Will I have to work hard?" | Signals laziness |
| "How quickly can I get promoted?" | Signals entitlement and short-term thinking |
| "Do you check if people are working?" | Signals that you plan to slack off |
| "What is your PTO policy?" | Save for HR / offer stage; in interviews it signals disengagement |
| "Can I work on side projects during work hours?" | Signals split attention |
| "How soon can I transfer to a different team?" | Signals you do not want this role |
| "Did I get the job?" | Puts the interviewer in an awkward position |

### With Recruiters

| Question | Why it is bad |
|----------|---------------|
| "What's the minimum salary for this role?" | Anchors low |
| "Can I skip some of the interview rounds?" | Entitled |
| "How many other candidates are you considering?" | They will not tell you, and it looks insecure |

---

## Key Takeaways

1. **Questions are evaluation tools.** Use them to assess fit, not just to fill time.

2. **Tailor your questions to the interviewer.** A recruiter and a VP should get different questions.

3. **Good questions demonstrate seniority.** The altitude of your questions signals the altitude of your thinking.

4. **Have more questions prepared than you will ask.** Some will be answered naturally during the interview. Others will not fit the flow.

5. **Genuine curiosity is visible.** Ask questions you actually care about. Authenticity builds rapport.

6. **Skip questions whose answers are obvious.** Never ask something you could have found with 5 minutes of research.

---

## Practice

- For a company you are actively interviewing with (or a target company), select 5-7 questions from this guide tailored to the specific round (recruiter, peer, manager, VP). Write them down and rank them by priority -- which ones would you ask if you only had time for two?
- Practice the quick decision framework above with a mock scenario: you just finished a technical round with a peer engineer, you have 5 minutes for questions, and two of your prepared questions were already answered during the interview. Which do you ask? Practice adapting on the fly.
- For each category (engineering culture, team dynamics, growth, product, process, role-specific), identify your top concern about a target company. Map that concern to the most effective question from this guide.

---

## Cross-References

- **[Module 01 — Interview Strategy](../01-strategy/):** The company research framework in Module 01 informs which questions to ask. Thorough research lets you ask specific, informed questions rather than generic ones. Skip questions whose answers are in the engineering blog.
- **[Module 04 — Red Flags and Strategic Questions](02-red-flags-and-strategic-questions.md):** This companion file covers interpreting answers, detecting red flags, evaluating engineering maturity with DORA metrics, and asking staff-level questions. Read this framework guide first for the question bank, then the red flags guide for the interpretive layer.
- **[Module 02 — Behavioral Interview Mastery](../02-behavioral/):** The rapport-building moments at the end of behavioral rounds are ideal for asking questions. Module 02's advice on reading the interviewer helps you pick the right question for the right moment.
- **[Module 08 — Negotiation & Closing](../08-negotiation/):** Several questions here (career path, evaluation process, level expectations) gather information that strengthens your negotiation position later. Ask these during interviews so you have data for the offer stage.
