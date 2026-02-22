# Module 04: Questions to Ask Interviewers

## Overview

The questions you ask in an interview reveal as much about you as the answers you give. Thoughtful, specific questions signal seniority, genuine interest, and strategic thinking. Generic questions — or no questions at all — signal the opposite.

At the senior/staff level, asking good questions serves three purposes:
1. **Signal:** It demonstrates that you think like a leader who evaluates environments, not just someone looking for any job.
2. **Evaluation:** The interview goes both ways. You are choosing where to spend the next 3-5 years of your career. The questions you ask are your primary tool for evaluating fit.
3. **Conversation:** Good questions transform the last 5-10 minutes of an interview from an awkward formality into a genuine exchange that builds rapport.

This module organizes questions by category, explains WHY each question is valuable (what the answer reveals), and identifies red flags in responses.

---

## Table of Contents

1. [Why Questions Matter](#why-questions-matter)
2. [Engineering Culture](#engineering-culture)
3. [Team Dynamics](#team-dynamics)
4. [Growth and Career Development](#growth-and-career-development)
5. [Product and Business](#product-and-business)
6. [Process and Practices](#process-and-practices)
7. [Role-Specific Questions](#role-specific-questions)
8. [Red Flags to Watch For](#red-flags-to-watch-for)
9. [Choosing the Right Questions](#choosing-the-right-questions)

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

## Engineering Culture

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

## Team Dynamics

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

## Growth and Career Development

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

## Product and Business

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

## Process and Practices

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

## Red Flags to Watch For

### Vague Answers

When every answer is vague or aspirational ("We're working on it", "We want to", "It depends"), the reality is likely that the practice does not exist. Companies that do things well can describe them specifically.

### Defensive Responses

If an interviewer becomes defensive when you ask about process, culture, or challenges, that defensiveness is information. A healthy organization can discuss its weaknesses openly.

### High Turnover Signals

Watch for:
- "We're rebuilding the team" (people left)
- "The team is relatively new" (high turnover)
- "We're hiring aggressively" (backfilling departures, not just growing)
- When you look at LinkedIn, average tenure is under 18 months

### "We Wear Many Hats"

This phrase often means:
- Roles and responsibilities are unclear
- You will do work outside your job description without additional compensation
- The team is understaffed
- There is no specialization or career growth path

It CAN be positive at an early-stage startup where versatility is genuinely valued and rewarded. At a company with 500+ employees, it is a red flag.

### No Questions About You

If the interviewer does not ask you any questions and just talks about the company the entire time, something is off. Either they are not actually evaluating you (rubber stamp), or they are more interested in selling than assessing fit.

### Inconsistent Answers

If different interviewers give you contradictory answers about the team's practices, culture, or direction, the organization may be misaligned internally. Pay attention to whether the team has a shared understanding.

### The "We're a Family" Signal

"We're like a family here" often translates to:
- Boundaries between work and personal life are blurred
- Leaving is seen as betrayal
- Conflict is avoided rather than resolved
- Working long hours is expected as a sign of loyalty

### Pressure to Decide Quickly

"We need your answer by end of day" or "This offer won't be available next week" is a high-pressure sales tactic. Good companies give you reasonable time to make major life decisions.

---

## Choosing the Right Questions

### Per-Round Strategy

Not all questions are appropriate for all rounds. Match your questions to the interviewer.

**Recruiter screen:** Process, timeline, compensation range, team size.

**Technical interviewer (peer):** Day-to-day engineering experience, code review, testing, deployment, tech stack choices, on-call.

**Engineering manager:** Team structure, growth path, evaluation process, biggest challenges, first 90 days.

**Skip-level or VP:** Engineering strategy, company direction, how engineering influences product, organizational challenges.

**Team match / culture fit:** Team dynamics, collaboration style, what they enjoy about working here, what they would change.

### How Many Questions to Prepare

- Prepare 5-7 questions per round
- Ask 2-4 during the interview (depending on time)
- Prioritize questions that genuinely help you evaluate fit
- Skip questions whose answers you already know from research
- Never ask a question you could have answered with 5 minutes of Googling

### Questions to Prioritize

Ask questions that:
- Help you evaluate whether YOU want to work here (this is a two-way decision)
- Demonstrate your seniority and strategic thinking
- Build rapport with the interviewer
- Are genuinely interesting to you (your curiosity will be visible)

### Questions to Skip

Do not ask:
- Questions answered on the company website
- Questions about basic benefits (save for HR/recruiter)
- Questions that make you look like you are not interested in the work
- Questions designed solely to impress (the interviewer can tell)

---

## Key Takeaways

1. **Questions are evaluation tools.** Use them to assess fit, not just to fill time.

2. **Tailor your questions to the interviewer.** A recruiter and a VP should get different questions.

3. **Listen to what they DO NOT say.** Evasion, defensiveness, and vagueness are all data.

4. **Good questions demonstrate seniority.** The altitude of your questions signals the altitude of your thinking.

5. **Have more questions prepared than you will ask.** Some will be answered naturally during the interview. Others will not fit the flow.

6. **Genuine curiosity is visible.** Ask questions you actually care about. Authenticity builds rapport.

7. **Red flags are more important than green flags.** One red flag is worth more than three green flags. Trust your instincts.
