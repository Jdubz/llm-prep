# Module 01 Deep Dive: Interview Strategy — Advanced Topics

## Overview

This deep dive covers the advanced strategic topics that most interview preparation materials skip: negotiation psychology, equity compensation structures, working with recruiters, navigating the politics of internal transfers, and mapping career levels across companies. These topics are especially relevant for experienced engineers who have more to gain (and more to lose) from getting strategy right.

---

## Table of Contents

1. [Negotiation Psychology](#negotiation-psychology)
2. [Startup vs Big Tech Compensation Structures](#startup-vs-big-tech-compensation-structures)
3. [Internal Transfers vs External Hiring](#internal-transfers-vs-external-hiring)
4. [Referral Strategies](#referral-strategies)
5. [Working with Recruiters](#working-with-recruiters)
6. [Interviewing While Employed](#interviewing-while-employed)
7. [Career Level Mapping Across Companies](#career-level-mapping-across-companies)

---

## Negotiation Psychology

Understanding the psychological principles behind negotiation makes you a more effective negotiator, even if you never use them explicitly.

### Anchoring

The first number mentioned in a negotiation disproportionately influences the final outcome. This is why you never give a number first.

- If you say "$300K" and the company was prepared to offer $350K, you have anchored the conversation around $300K and will likely settle somewhere between $300K-$330K.
- If the company says "$320K" first, you can counter at $380K and meet in the middle at $350K.
- If forced to give a number, anchor HIGH. It is psychologically easier to negotiate down than up.

**Tactical application:** When the recruiter asks "What are your salary expectations?" and will not relent, say: "Based on my research and experience, I'm targeting total compensation in the range of [top of market + 10-15%]." This sets a high anchor that frames all subsequent discussion.

### BATNA (Best Alternative to a Negotiated Agreement)

Your BATNA is what happens if this negotiation fails. A strong BATNA is the single most powerful negotiation tool.

- **Strong BATNA:** You have two other competitive offers. You genuinely do not need this particular offer. You are happy in your current role and can wait.
- **Weak BATNA:** This is your only active opportunity. You need to leave your current job urgently. You have been searching for months with no other interest.

**How to strengthen your BATNA:**
- Always have multiple companies in your pipeline
- Do not quit your current job before having an offer
- Be willing to walk away from a bad offer (this confidence is visible)
- Cultivate a genuine sense that you have options, even if this is your top choice

### Timing

When you negotiate matters as much as how you negotiate.

- **Negotiate after they want you, not before.** Once a company has invested 20+ hours of interviewer time and decided you are their candidate, their switching cost is enormous. This is your moment of maximum leverage.
- **Negotiate before you accept.** Once you accept, your leverage drops to zero.
- **Create urgency without desperation.** "I have another offer with a deadline of Friday" is powerful. "I need an answer today or I'm going elsewhere" feels aggressive.
- **Time your offers to overlap.** If Company A gives you an offer on Monday with a two-week deadline, push Company B to decide within that window.

### The Psychology of "No"

A "no" from the other side is not the end of negotiation; it is information.

- "We can't go higher on base" means: Ask about equity or sign-on.
- "This is our standard offer for this level" means: Ask about a higher level.
- "We don't negotiate" means: They negotiate. Push gently or ask what else is on the table.
- Silence after your counter means: They are considering it. Do not fill the silence with a concession.

---

## Startup vs Big Tech Compensation Structures

The structure of compensation varies dramatically between startups and large public companies. Understanding these structures prevents you from comparing apples to oranges.

### Big Tech (Public Companies)

```
Typical Staff Engineer comp at a large public company:
  Base:     $200,000 - $260,000
  RSUs:     $200,000 - $500,000 over 4 years
  Bonus:    10-20% of base
  Sign-on:  $20,000 - $100,000

RSU Details:
  - Restricted Stock Units: actual shares of public stock
  - Vest over 4 years (typically 25% per year or monthly after cliff)
  - Value is relatively predictable (stock price fluctuates but is transparent)
  - Refresher grants given annually to retain employees
  - Taxed as ordinary income upon vesting
```

**RSU vesting schedules by company:**
- **Google:** Monthly vesting over 4 years, no cliff
- **Meta:** 25% per year, quarterly vesting
- **Amazon:** 5% / 15% / 40% / 40% back-loaded schedule (notorious)
- **Apple:** 25% per year, quarterly vesting
- **Microsoft:** 25% per year, quarterly vesting

**Amazon's compensation quirk:** Because RSUs are back-loaded, Amazon front-loads with large sign-on bonuses in years 1 and 2 to smooth out total comp. Year 3 and 4 comp drops if you do not receive refreshers. This is by design to create retention leverage.

### Early-Stage Startups (Pre-IPO)

```
Typical Senior/Staff Engineer comp at a Series A-C startup:
  Base:     $160,000 - $220,000
  Options:  0.05% - 0.5% of company
  Bonus:    Rare at early stage
  Sign-on:  Rare

Option Details:
  - ISOs (Incentive Stock Options): Tax-advantaged, for employees only
  - NSOs (Non-Qualified Stock Options): No special tax treatment
  - Strike price: Set by 409A valuation (independent appraisal of company value)
  - Vest over 4 years with 1-year cliff (standard)
  - Must exercise within 90 days of leaving (unless extended)
  - Value is highly speculative
```

### Equity Types Explained

**ISOs (Incentive Stock Options):**
- Available only to employees
- No tax at grant or exercise (for regular tax; AMT may apply)
- Capital gains treatment if held 2 years from grant, 1 year from exercise
- $100K annual exercise limit for ISO treatment
- Best for: Long-term holds at companies likely to have a liquidity event

**NSOs (Non-Qualified Stock Options):**
- Available to employees, contractors, advisors
- Taxed as ordinary income on the spread at exercise
- No holding period requirements for capital gains
- More common than ISOs in practice
- Best for: Situations where you will exercise and sell quickly

**RSUs (Restricted Stock Units):**
- Shares granted to you that vest over time
- No purchase price (unlike options)
- Taxed as ordinary income upon vesting
- Common at public companies and late-stage startups
- Best for: Predictable compensation at established companies

### 409A Valuation

- An independent valuation of a private company's common stock, required by the IRS
- Sets the strike price for stock options
- Typically 30-50% of the preferred stock price (what investors paid)
- Updated annually or after significant events (funding rounds)
- A low 409A valuation means cheaper options for employees
- Ask what the current 409A valuation is and when it was last updated

### Evaluating Startup Equity

Questions to ask:
1. What is my percentage ownership on a fully diluted basis?
2. What is the current 409A valuation?
3. What was the last funding round valuation?
4. How much runway does the company have?
5. What is the exercise window if I leave? (90 days is standard but hostile; some companies offer 10 years)
6. Is there a path to liquidity (IPO, acquisition, secondary sales)?
7. How much additional dilution should I expect from future funding rounds?

**Rule of thumb:** Unless you have strong conviction in the company's trajectory, discount startup equity by 70-90% when comparing to public company RSUs. Most startups fail or have outcomes where common stock is worth little.

---

## Internal Transfers vs External Hiring

If you are already at a large company, you have the option of transferring internally. The tradeoffs are significant.

### Internal Transfer Advantages
- You keep your vesting schedule (no reset)
- You have a track record and reputation
- The interview bar is often lower (you are a known quantity)
- No gap in employment or benefits
- You can often try a team before committing

### Internal Transfer Disadvantages
- Limited compensation adjustment (usually no negotiation leverage)
- Your current manager must approve the transfer (politics)
- Your reputation (good or bad) follows you
- You may carry organizational baggage
- Limited ability to negotiate title/level

### External Hiring Advantages
- Full compensation negotiation from scratch
- Clean slate with new team
- Often the only way to get a meaningful title bump
- Competing offers give you leverage
- Fresh perspective and energy

### When to Transfer vs Leave
- **Transfer** when: You like the company but not the team/domain, your vesting is significant, the internal opportunity is genuinely exciting
- **Leave** when: You want a comp reset, you have outgrown the company's level bands, you want a fresh start, the company culture itself is the problem

---

## Referral Strategies

A referral is the single most effective way to get your resume past the initial screen. At most companies, referred candidates are 5-10x more likely to get an interview.

### How to Get Referrals

1. **First-degree connections:** Former colleagues, classmates, friends. Best and most reliable source.
2. **Second-degree connections:** "I see you're connected to [person] at [company]. Would you be comfortable making an introduction?"
3. **Cold outreach on LinkedIn:** Target engineers on the specific team. Be specific about why you are reaching out. Keep it under 100 words.
4. **Open source contributions:** Contributing to a company's open source projects creates natural connections.
5. **Conference networking:** Attending talks by company engineers and following up.

### How to Ask for a Referral

**Good:**
> "Hi [Name], I hope you're doing well. I saw that [Company] has an open [Role] on the [Team] team. I've been working on [relevant experience] for the past [X] years and think it could be a great fit. Would you be open to referring me? I've attached my resume and would be happy to share more context."

**Bad:**
> "Hey, I see you work at [Company]. Can you refer me? I'm looking for a job."

### Referral Etiquette
- Make it easy: send your resume and the specific job listing
- Explain why you think you are a good fit (so they can vouch for you)
- Do not pressure people; a lukewarm referral is worse than no referral
- Thank them regardless of outcome
- Return the favor when you can

---

## Working with Recruiters

Understanding how recruiters operate helps you navigate the relationship effectively.

### Internal Recruiters (In-House)

- Employed by the hiring company
- Incentivized to fill roles quickly with quality candidates
- Paid a salary (not per placement)
- Your primary point of contact throughout the process
- They are your advocate in the process but their loyalty is to the company

**How to work with them:**
- Be responsive; slow replies signal low interest
- Be honest about your timeline and other processes
- Ask them for information about the team, interview format, and what to expect
- They can often share the interviewer names in advance; use this to research
- Build rapport; they influence whether the hiring manager extends an offer

### Agency Recruiters (External)

- Employed by staffing firms
- Paid a percentage of your first-year salary (typically 15-25%)
- Incentivized to place you quickly at the highest salary possible (their fee is tied to your comp)
- May be working with you and multiple other candidates for the same role
- Quality varies enormously

**How to work with them:**
- Verify they have a direct relationship with the hiring company
- Ask which companies they are submitting you to (avoid duplicate applications)
- Do not sign exclusive agreements
- Understand that the company is paying their fee, not you
- Their interests partially align with yours (higher salary = higher fee) but they also want speed

### Recruiter Red Flags
- Will not tell you the company name
- Pressure to accept quickly
- Vague about the role details
- Cannot answer basic questions about the team or technology
- Asks you to pay any fees (legitimate recruiters never charge candidates)

---

## Interviewing While Employed

Most senior engineers interview while employed. This requires careful navigation.

### Scheduling

- Most companies will accommodate your schedule for phone screens (early morning, lunch, after hours)
- On-site loops typically require a full day; use PTO or "personal days"
- Do not lie about why you are taking time off; vague is fine ("personal appointment")
- Cluster on-sites to minimize days off
- Remote-first companies make this dramatically easier

### Confidentiality

- **Never tell your current employer you are interviewing** unless you have a genuinely trusting relationship with your manager AND you are not at risk of retaliation
- Be careful on LinkedIn; "Open to Work" is visible to recruiters but not your current company (if configured correctly), but updating your profile aggressively is a signal
- Do not use your work computer or email for job search activities
- Be cautious about who you tell at work; news travels

### Resignation Timing

- **Do not resign until you have a signed offer letter and have passed the background check**
- Two weeks notice is standard in the US; check your employment agreement for any specific requirements
- Offer to help with transition: document your work, brief your replacement
- Be gracious and professional; you will encounter these people again
- Your start date at the new company should account for notice period plus at least a few days of rest

---

## Career Level Mapping Across Companies

Titles and levels are not standardized across the industry. Understanding the mapping helps you target the right level and negotiate effectively.

### Approximate Level Mapping

| Level | Google | Meta | Amazon | Apple | Microsoft | Netflix | Startups |
|-------|--------|------|--------|-------|-----------|---------|----------|
| Mid | L4 | E4 | SDE II | ICT3 | 62 | N/A | "Engineer" |
| Senior | L5 | E5 | SDE III | ICT4 | 63 | Senior | "Senior Engineer" |
| Staff | L6 | E6 | Principal | ICT5 | 64 | Staff | "Staff" or "Principal" |
| Sr Staff | L7 | E7 | Sr Principal | ICT6 | 65-66 | Sr Staff | VP Eng / CTO |
| Principal | L8 | E8 | Distinguished | Fellow | 67+ | Principal | CTO |

### Level Expectations at Senior vs Staff

**Senior (L5/E5 equivalent):**
- Owns and delivers complex features independently
- Mentors junior and mid-level engineers
- Makes sound technical decisions within their team
- Writes design docs for team-scoped projects
- Scope: team-level impact

**Staff (L6/E6 equivalent):**
- Sets technical direction for a team or area
- Influences decisions across multiple teams
- Identifies and solves problems that others do not see
- Writes design docs for cross-team or organization-scoped projects
- Scope: multi-team or organizational impact
- Often the technical tiebreaker in disagreements
- Expected to sponsor and grow senior engineers

### Targeting the Right Level

- If you are currently at Senior (or equivalent), you can target Senior or Staff externally
- Leveling up externally is often easier than internally (no organizational memory of you as a junior)
- If a company down-levels you, negotiate for a shorter timeline to promotion or higher comp within the level
- Ask the recruiter directly: "What level is this role?" and "What are the expectations for that level?"
- If the company will not confirm the level, that is a yellow flag

### Compensation Ranges by Level

These are approximate ranges for major tech hubs (2024-2025 data from levels.fyi):

| Level | Total Comp Range |
|-------|-----------------|
| Senior (L5) | $250,000 - $450,000 |
| Staff (L6) | $350,000 - $600,000 |
| Sr Staff (L7) | $500,000 - $900,000 |

Note: Ranges vary significantly by company, location, and negotiation. These are US tech hub numbers; adjust for location and company tier.
