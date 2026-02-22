# Module 01: Interview Strategy

## Overview

Landing a senior or staff role is not just about passing technical screens. It is a multi-week campaign that requires deliberate planning, research, emotional management, and negotiation skill. Most experienced engineers underinvest in strategy and over-index on LeetCode. This module covers everything outside the whiteboard that determines whether you get the offer you want at the company you want for the compensation you deserve.

This module assumes you have 10+ years of experience and are targeting senior (L5/E5) or staff (L6/E6) positions. The dynamics at this level are different from junior hiring: the bar is higher on leadership and communication, the compensation negotiations are more complex, and the pipeline management is more consequential.

---

## Table of Contents

1. [Understanding the Hiring Loop](#understanding-the-hiring-loop)
2. [Researching Companies Effectively](#researching-companies-effectively)
3. [Managing Your Pipeline](#managing-your-pipeline)
4. [Building Your Narrative](#building-your-narrative)
5. [Remote vs On-Site Differences](#remote-vs-on-site-differences)
6. [Interview Timeline Management](#interview-timeline-management)
7. [Salary Negotiation Fundamentals](#salary-negotiation-fundamentals)
8. [Interview-Specific Tips](#interview-specific-tips)
9. [Practice Questions](#practice-questions)

---

## Understanding the Hiring Loop

Every company structures its loop differently, but the general pattern for senior/staff roles follows a predictable arc. Understanding what each stage evaluates lets you prepare with precision rather than panic.

### The Typical Loop

```
Recruiter Screen  -->  Technical Screen  -->  On-Site / Virtual Loop  -->  Debrief  -->  Offer
   (30 min)            (45-60 min)            (4-6 hours)                (internal)     (call)
```

### Stage 1: Recruiter / Phone Screen (30 minutes)

**What it evaluates:** Baseline communication, career narrative, role fit, salary expectations, logistics.

**What the recruiter is doing:**
- Confirming you meet the minimum bar for the role (years of experience, relevant tech)
- Assessing whether you can articulate your background clearly
- Gauging your compensation expectations to check budget alignment
- Determining your timeline and urgency
- Deciding whether to advance you or save the team's time

**How to prepare:**
- Have your 2-minute career summary rehearsed but not robotic
- Know the role description inside out; map your experience to their requirements
- Research the company enough to answer "Why us?" authentically
- Have a salary range ready but DO NOT volunteer it (more on this in negotiation)
- Prepare 2-3 thoughtful questions about the role or team

**Common mistakes at this stage:**
- Rambling through your career history chronologically
- Badmouthing your current employer
- Giving a specific salary number before receiving an offer
- Not asking any questions (signals low interest)
- Being unprepared for "Why are you looking to leave?"

### Stage 2: Technical Screen (45-60 minutes)

**What it evaluates:** Coding ability, problem-solving approach, communication during technical work.

**Format varies:**
- Live coding on CoderPad, HackerRank, or similar
- Take-home assignment (less common at senior level, more common at startups)
- System design discussion (sometimes replaces or supplements coding)
- Pair programming exercise

**At the senior/staff level, they are evaluating:**
- Can you solve medium-difficulty problems cleanly and efficiently?
- Do you ask clarifying questions before diving in?
- Do you think out loud and communicate your approach?
- Can you identify edge cases without prompting?
- Do you write production-quality code, not just "it works" code?
- Can you analyze time and space complexity?

**How to prepare:**
- Practice 2-3 problems per day for 2-4 weeks
- Focus on medium difficulty; hard problems rarely appear in screens
- Practice talking while coding; this is a skill that requires rehearsal
- Know your primary language deeply (standard library, idioms, testing patterns)
- Time yourself; 45 minutes goes fast

### Stage 3: On-Site / Virtual Loop (4-6 hours)

This is the main event. At the senior/staff level, expect 4-6 rounds, typically:

#### Coding Rounds (1-2 rounds, 45-60 min each)

**What they evaluate:** Algorithmic thinking, code quality, testing instincts, communication.

At the senior level, interviewers expect you to:
- Drive the conversation rather than waiting for hints
- Write clean, well-structured code with meaningful variable names
- Proactively discuss testing and edge cases
- Analyze complexity without being asked
- Discuss trade-offs between different approaches

#### System Design Round (1-2 rounds, 45-60 min each)

**What they evaluate:** Architectural thinking, breadth of knowledge, ability to make trade-offs, communication of complex ideas.

This is often the most heavily weighted round for senior/staff candidates. They want to see:
- Structured approach (requirements, high-level design, deep dives)
- Awareness of scale, reliability, consistency trade-offs
- Experience-backed decisions ("In my experience at X, we chose Y because...")
- Ability to go deep on any component when probed
- Understanding of operational concerns (monitoring, deployment, failure modes)

#### Behavioral Round (1 round, 45-60 min)

**What they evaluate:** Leadership, conflict resolution, self-awareness, cultural fit, scope of impact.

At the senior/staff level, they expect:
- Stories that demonstrate influence beyond your immediate team
- Evidence of mentorship and growing other engineers
- Examples of navigating ambiguity and making decisions with incomplete information
- Mature handling of conflict and disagreement
- Metrics and outcomes, not just activities

#### Team Match / Culture Fit (1 round, 30-45 min)

**What they evaluate:** Whether you will work well with the specific team, mutual interest, personality fit.

This round is often with a potential peer or skip-level manager. It feels more casual but is absolutely evaluative. They are assessing:
- Would they want to work with you day-to-day?
- Do your working style preferences align with the team?
- Are you genuinely interested in the team's problems?
- Will you raise the bar or just fill a seat?

### Stage 4: Debrief (Internal)

You are not present for this. The interviewers meet (or submit written feedback) and make a hire/no-hire decision. Understanding what happens here helps you optimize:
- Each interviewer typically provides a score (Strong Hire, Hire, Lean Hire, Lean No Hire, No Hire, Strong No Hire)
- A single "Strong No Hire" often vetoes the candidate
- At Google, a hiring committee reviews packets; at most other companies, it is the hiring manager's call with input
- Interviewers often share specific quotes and examples from your responses
- Written feedback means your exact words matter

### Stage 5: Offer

If you pass, the recruiter calls with the offer. This is where negotiation begins (covered below).

---

## Researching Companies Effectively

Thorough research separates candidates who get offers from candidates who get callbacks. At the senior/staff level, shallow research is obvious and damaging.

### Product Research

**What to know:**
- What does the company actually sell? Who are the customers?
- What is the business model? (SaaS, marketplace, advertising, enterprise licensing)
- What are the company's top 2-3 products or services?
- What is the competitive landscape?
- What recent product launches or pivots have happened?

**Where to look:**
- Company website and blog
- Recent press releases and news articles
- Product Hunt (for startups)
- App Store / Play Store reviews (for consumer products)
- G2 / Capterra reviews (for B2B products)
- Quarterly earnings calls (for public companies; surprisingly accessible and informative)

### Tech Stack Research

**What to know:**
- Primary languages and frameworks
- Infrastructure (cloud provider, container orchestration, CI/CD)
- Data stores and messaging systems
- Monolith vs microservices
- Any proprietary or interesting technical choices

**Where to look:**
- Job descriptions (they list the stack)
- Engineering blog
- StackShare
- GitHub (open source projects)
- Conference talks by their engineers (YouTube, InfoQ)
- "Built With" for web technologies

### Engineering Culture Research

**What to know:**
- How do they develop software? (Agile, Kanban, Shape Up, something custom)
- What is the deployment frequency?
- How do they handle incidents?
- What is the code review culture like?
- How are technical decisions made?

**Where to look:**
- Engineering blog (the single best source)
- Glassdoor reviews (filter for engineering roles, look at recent reviews)
- Blind (anonymous, often brutally honest, take with appropriate skepticism)
- LinkedIn (look at tenure of engineers, team sizes, growth patterns)
- Conference talks and podcasts featuring their engineers
- Their open source repositories (commit history, PR review patterns, documentation quality)

### Business Model Understanding

This is what separates senior from staff candidates in interviews. Understanding the business lets you:
- Frame system design answers in terms of business impact
- Ask informed questions about product direction
- Demonstrate that you think beyond code
- Show you understand how engineering decisions affect revenue

**Key questions to answer:**
- How does the company make money?
- What are the unit economics?
- Who are the customers and what do they pay?
- What is the company's growth stage? (Pre-revenue, growth, profitable, public)
- What are the biggest business risks?

### Research Template

```
Company: _______________
Role: _______________
Date applied: _______________

PRODUCT
- Core product: _______________
- Target customer: _______________
- Business model: _______________
- Recent launches: _______________
- Competitors: _______________

TECHNOLOGY
- Primary languages: _______________
- Infrastructure: _______________
- Notable tech choices: _______________
- Open source work: _______________

CULTURE
- Development process: _______________
- Deployment frequency: _______________
- Engineering blog highlights: _______________
- Glassdoor themes: _______________
- Blind themes: _______________

PEOPLE
- Hiring manager: _______________
- Recruiter: _______________
- Notable engineers: _______________
- Shared connections: _______________

QUESTIONS TO ASK
1. _______________
2. _______________
3. _______________
```

---

## Managing Your Pipeline

Job searching is a numbers game with emotional stakes. Managing your pipeline deliberately reduces stress and maximizes outcomes.

### The Numbers

**Target: 10-15 active applications at any time.**

Why this range:
- Fewer than 10: A couple of rejections can demoralize you and leave you with no leverage
- More than 15: You cannot research each company thoroughly or prepare adequately
- The sweet spot gives you enough volume for confidence and leverage without sacrificing quality

### Pipeline Stages

```
Identified  -->  Applied  -->  Screening  -->  Technical  -->  On-Site  -->  Offer
  (30+)          (15-20)       (10-12)         (6-8)          (4-6)        (2-3)
```

Expect roughly 50% attrition at each stage. These numbers mean you should identify 30+ potential companies to end up with 2-3 offers.

### Timing Strategy

**Week 1-2:** Research and apply to "warm-up" companies
- Companies you are less excited about but would accept
- Use these to shake off rust and calibrate
- Learn what questions are being asked
- Get comfortable with the interview format

**Week 3-4:** Apply to target companies
- Your top-choice companies
- You are now warmed up and performing at your best
- Timing these later gives you more confidence and polish

**Week 5-8:** On-sites and offer management
- Try to cluster on-sites within a 2-week window
- This creates natural time pressure for decisions
- Gives you maximum leverage if you receive multiple offers

### Pacing Across Weeks

- Maximum 2 on-site loops per week (they are exhausting)
- Take at least 1 day off between on-sites
- Do not schedule anything the day before an on-site at a top-choice company
- Keep weekends for rest, not cramming
- Block 30 minutes after each interview for notes while they are fresh

### Taking Breaks

Interview fatigue is real and underestimated. Signs you need a break:
- You are dreading interviews rather than approaching them as conversations
- Your performance is declining across rounds
- You are unable to sleep well before interviews
- You are making careless mistakes in coding problems you know how to solve

When to pause:
- After 3 consecutive rejections, take 3-5 days off
- After a particularly draining on-site, take 2 days off
- If you have been actively interviewing for more than 6 weeks, take a week off

---

## Building Your Narrative

At the senior/staff level, your career narrative is as important as your technical skills. Interviewers are evaluating whether your trajectory makes sense and whether you are intentional about your career.

### The Career Story Arc

Your narrative should answer three questions:
1. **Where have you been?** (2-3 key career chapters)
2. **What is the thread?** (the connecting theme)
3. **Where are you going?** (why this company, why this role, why now)

**Structure:**
```
"I started at [company/context], where I [key accomplishment and what you learned].
That led me to [next chapter], where I [escalated responsibility/impact].
Now I'm looking for [what you want next] because [authentic reason],
and [this company] is interesting because [specific, researched reason]."
```

**Example:**
```
"I started my career at a small healthcare startup where I built their first
patient portal from scratch and learned what it means to own a product end-to-end.
That experience drew me to Stripe, where I spent five years scaling the payments
infrastructure team from 4 to 20 engineers and led the migration to event-driven
architecture. I'm at a point where I want to shape technical strategy at the
organizational level, and your platform team's work on developer experience
resonates with me because I've seen firsthand how internal tooling multiplies
engineering output."
```

### Why You Are Leaving

This question is a minefield. The wrong answer kills your candidacy. The right answer reinforces your narrative.

**Good answers (honest and forward-looking):**
- "I've accomplished what I set out to do and I'm looking for a new challenge"
- "I want to work at a different scale / in a different domain"
- "I'm looking for more ownership over technical direction"
- "The company's direction has shifted and it no longer aligns with what I want to build"

**Dangerous answers (even if true):**
- "My manager is terrible" (you look like a complainer)
- "The company is going downhill" (you look disloyal)
- "I'm not being promoted fast enough" (you look entitled)
- "The pay is not competitive" (you look purely mercenary)

**The rule:** Always frame your departure as moving TOWARD something, not running FROM something.

### Why This Company

Generic answers are an instant red flag at the senior level. "I love your product" or "I admire your engineering culture" without specifics signals that you did not do your homework.

**Strong answers include:**
- Specific technical challenges you have read about on their blog
- A feature or product decision you found interesting and why
- A person you would work with whose work you have followed
- A business opportunity you see that you could contribute to
- Alignment between their stage/challenges and your experience

### Why This Role

Connect your specific experience to the role's specific needs:
- What skills from your past map to their current challenges?
- What gaps in their team does your background fill?
- What is the scope of impact you expect in this role?
- How does this role fit your career trajectory?

---

## Remote vs On-Site Differences

Post-2020, many interview loops are partially or fully remote. The skills are the same but the execution differs.

### Camera Presence

- **Eye contact means looking at the camera, not the screen.** This is counterintuitive. Practice it.
- Position your camera at eye level; looking down into a laptop camera is unflattering and disengaging
- Ensure your face is well-lit from the front (a window behind you creates a silhouette)
- Wear a solid-colored top; patterns can be distracting on camera
- Nod and react visibly; on camera, you need to amplify your nonverbal communication

### Screen Sharing Etiquette

- Close all unnecessary tabs and applications before the interview
- Hide your bookmarks bar (it reveals personal information)
- Turn off all notifications (Slack, email, calendar, system)
- Use a clean desktop or a neutral wallpaper
- Increase your font size in the code editor (14pt minimum for readability)
- If using a shared coding environment, familiarize yourself with it beforehand

### Whiteboarding Alternatives

Remote interviews replace whiteboards with:
- **Virtual whiteboards** (Excalidraw, Miro, Google Jamboard): Practice drawing with a mouse or trackpad; it is slower and messier than a real whiteboard
- **Shared documents** (Google Docs): Use bullet points, indentation, and ASCII diagrams
- **Drawing tablets**: If you do many remote interviews, a simple drawing tablet is a worthwhile investment

### Environment Setup

- **Wired internet connection** if at all possible; do not trust Wi-Fi for your career
- **Quiet room** with a closed door; inform housemates of your schedule
- **Backup plan**: Have your phone ready as a hotspot; know how to call in by phone if video fails
- **Water on your desk**; you will be talking for hours
- **Notepad and pen** for quick notes during the conversation
- **Test your setup** 30 minutes before: camera, microphone, screen sharing, coding environment

---

## Interview Timeline Management

Managing timelines across multiple companies is one of the highest-leverage skills in a job search.

### When to Follow Up

| Event | Follow-up timing | What to say |
|-------|------------------|-------------|
| After applying | 1 week | Brief note expressing interest (only if you have a referral or connection) |
| After recruiter screen | 2-3 business days if no response | "Wanted to check in on next steps" |
| After technical screen | 3-5 business days if no response | "Following up on my interview on [date]" |
| After on-site | 1 business day | Thank-you email to recruiter (not individual interviewers) |
| After on-site, no response | 1 week | "Checking in on the timeline for a decision" |
| After receiving offer | Immediately acknowledge receipt | "Thank you, I'd like to take [X days] to review" |

### Handling Multiple Offers with Different Timelines

This is the most common and most stressful scenario. The key principles:

1. **Be honest with recruiters about your timeline.** "I'm in late stages with another company and expect an offer by [date]. I want to make an informed decision and would love to have your offer by then as well."

2. **Ask for deadline extensions.** Most companies will give you 1-2 weeks to decide. Some (especially FAANG) will give you more. Simply say: "I'm very interested in this role but I'm also in late stages elsewhere. Could I have until [date] to make my decision?"

3. **Use offers as acceleration, not ultimatums.** Tell Company B: "I received an offer from Company A with a deadline of [date]. I'm very interested in your role and want to make sure I can consider you both. Is there any way to accelerate the process?"

4. **Never bluff about offers you do not have.** Recruiters talk to each other. The industry is smaller than you think.

5. **Never accept an offer you plan to renege on.** Reneging burns bridges permanently and can follow you for years.

### Extending Deadlines

When a company gives you an exploding offer (short deadline):
- Ask for more time politely: "I'm very excited about this opportunity and want to give it the consideration it deserves. Could I have until [specific date]?"
- If they push back, ask why: "Is there a specific reason for the timeline?"
- If they refuse to extend at all, that is a yellow flag about the company culture

---

## Salary Negotiation Fundamentals

Negotiation is where tens of thousands of dollars are won or lost. Most engineers leave significant money on the table because they are uncomfortable with the process.

### Understanding Total Compensation

At the senior/staff level, total compensation has multiple components:

```
Total Comp = Base Salary + Equity + Annual Bonus + Sign-On Bonus + Benefits

Example (Staff Engineer, Big Tech):
  Base:     $220,000
  Equity:   $300,000 over 4 years ($75,000/year)
  Bonus:    15% of base ($33,000)
  Sign-on:  $50,000 (year 1 only)
  Benefits: $15,000-30,000 (health, 401k match, etc.)
  ─────────────────────────────
  Year 1:   ~$378,000
  Year 2+:  ~$328,000
```

### Market Data

**Know your market value before any conversation about compensation.**

- **levels.fyi**: The gold standard for tech compensation data. Filter by company, level, location, and years of experience.
- **Glassdoor**: Useful but less accurate for tech roles; better for non-tech companies.
- **Blind**: Anonymous posts with verified comp data; filter for noise.
- **Comprehensive.fyi**: Aggregates data across sources.
- **Your network**: Nothing beats firsthand data from people at your target companies.

### The Cardinal Rules

1. **Never give a number first.** When asked "What are your salary expectations?", deflect:
   - "I'd prefer to learn more about the role and the total compensation structure before discussing numbers."
   - "I'm confident we can find something that works for both of us. What's the range budgeted for this role?"
   - "I'm focused on finding the right fit. I trust that your offer will be competitive."

2. **If forced to give a range, go high.** Research the top of market for the role and add 10-15%. You can always negotiate down but never up from your initial anchor.

3. **Always negotiate the first offer.** The first offer is almost never the best offer. Companies expect negotiation and build in room.

4. **Negotiate on total comp, not just base.** Base salary has the smallest range. Equity, sign-on bonuses, and other components often have more flexibility.

5. **Get competing offers.** This is the single most powerful negotiation lever. A competing offer transforms negotiation from "Please pay me more" to "Help me choose you."

### Negotiation Framework

```
Step 1: Receive the offer (verbal or written)
Step 2: Express enthusiasm but do NOT accept immediately
        "Thank you, I'm really excited about this opportunity.
         I'd like to take a few days to review the details."
Step 3: Ask for the offer in writing if it was verbal
Step 4: Research and compare against market data
Step 5: Prepare your ask (specific numbers, not "more")
Step 6: Make your case
        "I'm very excited about joining [Company]. After reviewing the offer
         and comparing with my other options, I was hoping we could discuss
         the equity component. Based on my research and competing offers,
         I was hoping for [specific number]."
Step 7: Listen and respond to their counter
Step 8: Know your walk-away point before the conversation
```

### What Is Negotiable

| Component | Flexibility | Notes |
|-----------|-------------|-------|
| Base salary | Low-Medium | Often capped by level/band |
| Equity | Medium-High | Most flexible component at big tech |
| Sign-on bonus | High | One-time cost; companies give these easily |
| Annual bonus target | Low | Usually tied to level |
| Start date | High | Can affect sign-on timing |
| Remote work | Medium | Depends on company policy |
| Title/Level | Low-Medium | Huge comp implications; worth pushing |
| PTO | Low | Usually standardized |
| Relocation | High | If applicable |

---

## Interview-Specific Tips

### The Day Before

- Review your notes on the company (research template)
- Re-read the job description
- Review your prepared stories (story bank from Module 02)
- Prepare your questions to ask (Module 04)
- Lay out your clothes (on-site) or test your setup (remote)
- Get a full night of sleep; no late-night cramming

### The Day Of

- Eat a substantial meal 1-2 hours before
- Arrive 10-15 minutes early (on-site) or log in 5 minutes early (remote)
- Bring copies of your resume (on-site)
- Bring a water bottle and a notepad
- Turn off your phone
- Take deep breaths; anxiety is normal and manageable

### During Each Round

- **First 2 minutes:** Build rapport. Comment on something specific. Smile.
- **Listen more than you talk** in the first minute. Let the interviewer set the stage.
- **Ask for clarification** before diving into any problem.
- **Manage your time.** If you have 45 minutes and three parts, spend 15 minutes each.
- **Signal when you are stuck.** "I'm thinking through a couple of approaches..." is better than silence.
- **Save 5 minutes for questions.** Always have questions ready.

### Between Rounds

- Take a bathroom break even if you do not need one; the mental reset helps
- Drink water
- Jot down any notes about what went well or poorly
- Reset mentally; do not carry a bad round into the next one
- Move your body: stretch, walk briefly

### After the Interview

- Send a thank-you email to your recruiter within 24 hours
- Write detailed notes about every question you were asked while your memory is fresh
- Note the names and roles of each interviewer
- Assess your own performance honestly; identify areas to improve for the next loop
- Do not obsess over individual rounds; one weak round does not mean rejection

---

## Practice Questions

### Self-Assessment Questions

1. Can you deliver your career narrative in under 2 minutes? Time yourself.
2. Do you have a researched answer to "Why this company?" for every company in your pipeline?
3. Can you explain your current compensation structure clearly?
4. Do you know the market rate for your target role and level?
5. Have you identified your BATNA (Best Alternative to Negotiated Agreement)?

### Mock Interview Prompts

1. "Tell me about yourself and what brings you here today."
2. "Why are you looking to leave your current role?"
3. "What are you looking for in your next opportunity?"
4. "Where do you see yourself in 3-5 years?"
5. "What's your expected compensation range?" (Practice deflecting this.)
6. "Why should we hire you over other candidates at your level?"
7. "What do you know about our company?"

### Pipeline Management Exercises

1. Create a spreadsheet with 15 target companies. For each, fill in the research template.
2. Rank your companies by preference. Schedule warm-up companies first.
3. Map out a 6-week interview calendar with no more than 2 on-sites per week.
4. Draft your follow-up email templates (see cheat sheet).
5. Research compensation for your target role at 5 different companies using levels.fyi.

### Negotiation Role-Play Scenarios

1. **Scenario:** You receive an offer at $350K TC. Your market research shows the range is $320-400K. You have no competing offers. Practice negotiating.

2. **Scenario:** You have two offers. Company A (your preference) offers $360K. Company B offers $400K. Practice leveraging B's offer with A.

3. **Scenario:** The recruiter asks "What are your salary expectations?" during the first phone screen. Practice deflecting without being evasive.

4. **Scenario:** The company says their offer is "final and non-negotiable." Practice your response.

5. **Scenario:** You want to negotiate for remote work flexibility but the role is listed as hybrid. Practice making your case.

---

## Key Takeaways

1. **Treat your job search as a project.** Apply the same rigor you bring to engineering work: plan, execute, measure, iterate.

2. **Research is not optional.** Shallow research is immediately obvious to experienced interviewers and signals low interest.

3. **Manage your pipeline for leverage and sanity.** Too few applications leaves you desperate; too many leaves you unprepared.

4. **Build a coherent narrative.** Your career story should feel intentional, even if it was not entirely planned.

5. **Never skip negotiation.** The worst they can say is "This is our best offer," and even then you have lost nothing by asking.

6. **Optimize for learning early, performance late.** Use warm-up companies to calibrate and improve before your top choices.

7. **Take care of yourself.** Interview fatigue is real. Rest, exercise, and time away from preparation are not luxuries; they are performance optimizations.
