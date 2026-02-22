# Module 08: Negotiation & Closing

> You cleared the technical bar. Now the outcome is determined by your negotiation skills. This is where most engineers leave the most money on the table.

---

## Table of Contents

1. [Understanding Total Compensation](#understanding-total-compensation)
2. [Researching Market Rates](#researching-market-rates)
3. [The Negotiation Conversation](#the-negotiation-conversation)
4. [Competing Offers and Leverage](#competing-offers-and-leverage)
5. [Counter-Offer Strategies](#counter-offer-strategies)
6. [Evaluating Offers Beyond Compensation](#evaluating-offers-beyond-compensation)
7. [Accepting and Declining](#accepting-and-declining)
8. [Handling Counter-Offers from Current Employer](#handling-counter-offers-from-current-employer)

---

## Understanding Total Compensation

Base salary is not your compensation. Total compensation (TC) is. Senior engineers who focus only on base salary leave tens of thousands of dollars on the table.

### Components of Total Compensation

#### Base Salary

- The predictable, guaranteed portion of your pay
- Typically the easiest to negotiate but often has hard caps by level
- At senior levels, base becomes a smaller percentage of total compensation
- Most companies have salary bands by level — your base is constrained by where they level you

#### Equity

Equity is where the real money diverges between offers. Understanding the mechanics is critical.

**RSUs (Restricted Stock Units):**
- Granted as a number of shares that vest over time
- Standard vesting: 4-year schedule with 1-year cliff
- After the cliff, vesting is typically monthly or quarterly
- Value = number of shares * current stock price
- **Key risk:** Stock price can go down. RSUs in a declining stock are worth less than granted.
- **Amazon exception:** Amazon's RSU vesting is back-weighted (5/15/40/40% over 4 years). They compensate with larger signing bonuses in years 1-2.

**ISOs (Incentive Stock Options):**
- Right to buy shares at a fixed price (strike price)
- Favorable tax treatment if you hold 1 year after exercise + 2 years after grant
- Common at startups and pre-IPO companies
- **Key risk:** You pay the strike price to exercise. If the company does not go public or get acquired, the shares may be worthless.
- **AMT trap:** Exercising ISOs can trigger Alternative Minimum Tax on the spread between strike and fair market value

**NSOs (Non-Qualified Stock Options):**
- Same as ISOs but without the favorable tax treatment
- Taxed as ordinary income on exercise (on the spread)
- Given to contractors, advisors, or when ISO limits are exceeded
- No AMT trap, but higher regular tax

**Vesting Schedules:**
- **Standard:** 25% at 1-year cliff, then monthly/quarterly for remaining 3 years
- **Back-weighted:** More vests later (Amazon style)
- **Refresher grants:** Annual grants to compensate for completed vesting — ask about the refresh policy
- **Acceleration clauses:** Single trigger (vest on acquisition) or double trigger (vest on acquisition + termination)

#### Annual Bonus

- Expressed as a target percentage of base salary (e.g., 15% target bonus)
- **Target vs actual:** The target is what you get at expected performance. Actual can be higher or lower.
- Typically depends on individual performance AND company performance
- At some companies, the bonus multiplier can exceed 100% of target for top performers
- **Ask:** "What percentage of employees hit their target bonus last year?"

#### Sign-On Bonus

- One-time payment, often paid with first paycheck or in installments
- Used to offset what you are leaving behind (unvested equity, pending bonus)
- **Clawback clause:** Most sign-on bonuses must be repaid if you leave within 1-2 years. Read the terms.
- Highly negotiable — often easier to increase than base salary

#### Benefits

Often overlooked but can be worth $20,000-50,000+ annually:

- **Health insurance:** Employer-paid premiums (compare out-of-pocket costs, not just "we have health insurance")
- **401(k) match:** Immediate vesting vs graded vesting. A 6% match with immediate vesting on a $200K salary is $12K/year
- **PTO:** Unlimited PTO is not always better — track what people actually take. 4 weeks defined PTO may result in more actual vacation.
- **Other:** HSA contributions, FSA, life insurance, disability, parental leave (weeks? paid?), professional development budget, WFH stipend, commuter benefits, meal allowances

#### Relocation

- Lump sum vs managed relocation (company hires movers)
- Housing assistance (temporary housing, home sale assistance)
- Cost-of-living adjustment
- Tax gross-up (some companies gross up relocation to cover the tax hit; others do not)

### Calculating Total Compensation

```
Annual TC = Base Salary
          + (Annual Equity Grant / Vesting Period)
          + Target Bonus
          + (Sign-On Bonus / Clawback Period)
          + Benefits Value
```

**Example comparison:**

| Component | Offer A | Offer B |
|-----------|---------|---------|
| Base | $200,000 | $185,000 |
| Equity (annual) | $50,000/yr RSU | $120,000/yr RSU |
| Bonus target | 15% ($30,000) | 10% ($18,500) |
| Sign-on | $0 | $50,000 |
| **Year 1 TC** | **$280,000** | **$373,500** |
| **Year 2+ TC** | **$280,000** | **$323,500** |

Offer B is significantly better despite the lower base.

---

## Researching Market Rates

### Data Sources

**Levels.fyi:**
- The gold standard for tech compensation data
- Real, verified data points with company, level, location, and TC breakdown
- Use the "Add Offer" feature to compare specific offers
- Check the levels mapping to understand how companies compare (L5 at Google = E5 at Meta = Senior SDE at Amazon)

**Glassdoor:**
- Broader coverage but less precise for tech roles
- Self-reported, not verified — treat as directional
- Better for non-tech components (bonus %, culture insights)

**Blind:**
- Anonymous forum with active compensation discussion
- Very tech-focused, often real-time data
- Take individual posts with a grain of salt, but patterns are informative
- Useful for understanding negotiation tactics that worked at specific companies

**Other sources:**
- Hired.com salary reports
- Triplebyte/Karat compensation data
- Recruiting firms (they know market rates — ask them)
- Your professional network (peers at target companies)

### How to Interpret Data

- **Median vs percentile:** A P75 candidate should not accept P50 compensation
- **Year of data:** Compensation changes rapidly. 2-year-old data may be significantly outdated.
- **Stock price at time of grant:** RSU grants reported at $300/share may be worth more or less now
- **Location adjustment:** A San Francisco salary at a P75 may be P95 in Austin

### Compensation by Geography

- **Tier 1 (SF, NYC, Seattle):** Highest base + equity. TC for senior engineers commonly $350K-500K+.
- **Tier 2 (Austin, Denver, Boston, LA):** 10-20% lower than Tier 1
- **Tier 3 (Most other US metros):** 20-35% lower than Tier 1
- **Remote compensation:** Some companies pay Tier 1 regardless of location. Others adjust to local cost of labor (not cost of living — there is a difference). Ask about their policy before interviewing.

### Remote Compensation Adjustments

- **Geographic pay bands:** Salary varies by location tier
- **National flat rate:** Same pay regardless of location (less common, usually at remote-first companies)
- **Hybrid:** Base adjusts, equity does not
- **Key question to ask:** "Does compensation vary by location, and if so, how?"

---

## The Negotiation Conversation

### The Cardinal Rule: Never Give a Number First

Whoever names a number first anchors the negotiation. Let them anchor.

**When asked "What are your salary expectations?"**

**Deflection scripts:**

Script 1 (direct):
> "I would rather not share a specific number at this point. I am focused on finding the right role and team. Once we determine there is a mutual fit, I am confident we can work out compensation that reflects my experience and the value I would bring."

Script 2 (redirect):
> "I am sure you have a range budgeted for this level. I would love to understand the full compensation package you are offering, and we can go from there."

Script 3 (if pressed hard):
> "Based on my research, the market range for this level of seniority in [location] is [wide range]. But I would really prefer to discuss specifics after we have had a chance to evaluate mutual fit."

**If they absolutely require a number (some companies have this policy):**
- Give a range, not a point
- Set your floor at or slightly above your target
- Base the range on research, not your current salary
- "Based on my research and experience level, I am targeting $X-$Y in total compensation."

### Expressing Enthusiasm While Negotiating

Negotiation is not adversarial. You want to join this company. They want you to join. Frame every counter as collaborative.

**DO say:**
- "I am really excited about this opportunity and the team. I want to make this work."
- "This is one of my top choices. Let me share what would make this a clear yes for me."
- "I appreciate the offer. I have done some research and want to discuss a few components."

**DO NOT say:**
- "I need more money" (sounds transactional)
- "That is too low" (sounds dismissive)
- "Company X pays more" (without specific context — sounds like bluffing)

### Email vs Phone Negotiation

| Medium | When to Use | Advantage |
|--------|-------------|-----------|
| **Email** | Initial counter, complex asks | Time to craft your message, written record |
| **Phone** | Building rapport, reading reactions | Real-time back-and-forth, harder to ignore |

**Best practice:** Negotiate the big points over email (so you can be precise), but have a phone call to express enthusiasm and discuss nuances. Start with: "I would love to discuss this over the phone, but let me send my thoughts in writing first so you can review them with your team."

---

## Competing Offers and Leverage

### How to Create Leverage

- **Interview in parallel:** Apply to multiple companies simultaneously. Aim to have 2-3 offers within the same 2-week window.
- **Be transparent (strategically):** "I am in the final stages with two other companies" is honest and creates urgency.
- **Name the company if it helps:** "I have an offer from [respected company]" carries weight if the company is a known brand.
- **Do not bluff:** If you claim an offer you do not have, you will get caught. Recruiters talk to each other.

### Parallel Timelines

**Managing multiple processes:**
- Track every company's stage, next step, and expected timeline in a spreadsheet
- When one company moves faster, ask slower companies to accelerate: "I have received an offer with a deadline of [date]. I am very interested in your company — is there any way to expedite the process?"
- Most companies will accommodate reasonable requests to accelerate

### Exploding Offers — How to Handle Them

An "exploding offer" has an unreasonably short deadline (24-48 hours). This is a pressure tactic.

**How to respond:**
> "Thank you for the offer. I am very interested but making a responsible decision in 48 hours is not possible. I have other processes in flight and owe it to both of us to make a thoughtful decision. Could we extend the deadline to [reasonable date]?"

**Reality check:**
- Most exploding offers are negotiable. Push back.
- If they will not extend at all, that tells you something about the culture.
- A company that revokes an offer because you asked for more time was not a good employer.

### Using Offers You Would Not Take

An offer you would not accept is still valuable leverage — as long as it is real.

- You do not need to tell Company A that Company B is your first choice
- "I have a competing offer at $X TC" is factual and effective
- Do not lie about the numbers. If they call your bluff, the negotiation is over.
- You can also use competing offers to accelerate timelines without revealing specific numbers

---

## Counter-Offer Strategies

### Asking for Specific Numbers

Vague asks get vague responses. Be specific:

**Weak:** "I was hoping for a higher base salary."
**Strong:** "Based on my research and the competing offers I am evaluating, I believe a base salary of $215,000 better reflects the market rate for this level. Would that be possible?"

### Justifying Your Ask

Back every request with data:

- **Market data:** "According to levels.fyi, the P75 for this role in [city] is $X"
- **Competing offers:** "I have an offer from [company] at $X TC"
- **Experience/impact:** "My experience leading [specific project type] is directly relevant to [their needs]"
- **What you are leaving behind:** "I have $X in unvested equity at my current company"

### Negotiating Multiple Components

Do not just negotiate base salary. A multi-component negotiation gives you more levers and gives them more flexibility.

**Example counter-offer email:**

> Thank you for the offer. I am excited about the opportunity and want to make this work. After careful consideration, I would like to discuss three components:
>
> 1. **Base salary:** I am requesting $215,000 (up from $200,000), which aligns with the market P75 for this level.
> 2. **Equity:** Would it be possible to increase the RSU grant to $300,000 (from $200,000)? Given my experience with [specific relevant skill], I believe this reflects the impact I can have.
> 3. **Sign-on bonus:** To bridge the gap from my unvested equity at [current company] (~$40K), I am requesting a $50,000 sign-on bonus.
>
> I understand these are significant asks. I am open to discussing alternatives — for example, a higher equity grant in exchange for less movement on base.

### Creative Negotiation

When they hit a wall on base salary, explore other dimensions:

| Component | What to Ask For |
|-----------|----------------|
| **Start date** | Later start to extend current employment (more vesting, bonus) |
| **Title** | Higher title may be easier than higher salary |
| **Level** | If they leveled you as "Senior," push for "Staff" |
| **Scope** | Lead a team or project (sets you up for promotion) |
| **Remote flexibility** | Full remote, or more WFH days |
| **PTO** | Extra week of vacation |
| **Professional development** | Conference budget, education budget |
| **Equipment** | Laptop choice, monitor, ergonomic setup |
| **Review timeline** | Early performance review at 6 months (path to faster raise) |

---

## Evaluating Offers Beyond Compensation

Money matters, but it is not everything. At the senior level, career trajectory often matters more than a $20K difference in TC.

### Growth Trajectory

- **Is this a step up, lateral, or step down?** Even a lateral move can be good if it opens a new trajectory.
- **What does promotion look like?** Ask: "What does the path from Senior to Staff look like here? How long does it typically take?"
- **Will you learn new things?** Doing the same work you have done for 10 years at a different company is not growth.

### Team Quality

- **Who will you work with?** Ask to meet your future teammates during the interview process.
- **Who is the engineering manager?** A great manager can transform your career. A bad one can stall it.
- **What is the senior/junior ratio?** All seniors = no mentorship opportunity. All juniors = you are the mentor (decide if you want that).

### Product-Market Fit

- **Is the product growing?** Growing products mean more opportunities, more resources, more impact.
- **Is the market large?** A great product in a tiny market has a ceiling.
- **Revenue model clarity:** How does the company make money? Is the path to profitability clear?

### Engineering Culture

- **Deployment frequency:** How often do they ship? Daily vs quarterly tells you a lot.
- **Technical debt attitude:** Do they acknowledge it? Budget for it? Or pretend it does not exist?
- **On-call expectations:** Is there a rotation? How often? Is it compensated?
- **Code review culture:** Thorough reviews = higher quality. Rubber stamps = problems ahead.

### Work-Life Balance

- **Ask directly:** "What does a typical week look like for someone in this role?"
- **Check signals:** Do people work weekends? Late nights? Check Slack activity timestamps.
- **PTO culture:** Unlimited PTO means nothing if nobody takes it. Ask: "How much vacation does the average person on this team actually take?"

### Learning Opportunities

- **Tech stack:** Will you work with technologies you want to learn?
- **Scale:** Working at 10x scale teaches things you cannot learn at smaller companies
- **Breadth vs depth:** Will you go deep on one area or work across the stack?

### Mission Alignment

- **Do you care about what the company does?** This matters more than you think over a multi-year stint.
- **Would you be proud to tell people where you work?** Not about prestige — about personal alignment.

---

## Accepting and Declining

### How to Accept Gracefully

1. **Confirm verbally first** — Call your recruiter or hiring manager. Express genuine enthusiasm.
2. **Follow up in writing** — Email confirming your acceptance, start date, and any agreed-upon terms.
3. **Review the offer letter** — Before signing, verify everything discussed is reflected.

**What to verify in the offer letter:**
- Base salary (correct amount, pay frequency)
- Equity (number of shares or dollar value, vesting schedule, grant date)
- Sign-on bonus (amount, payment schedule, clawback terms)
- Start date
- Title and level
- Location / remote policy
- Any special terms negotiated (early review, extra PTO, etc.)

**If something is missing or different from verbal agreement:**
> "Thank you for sending the offer letter. I noticed [component] does not match what we discussed. During our call on [date], we agreed on [specific term]. Could you please update the letter to reflect that?"

### How to Decline Without Burning Bridges

The tech industry is small. The recruiter you decline today may be at your dream company next year.

**Decline promptly** — Do not ghost. Do not delay for weeks. As soon as you decide, communicate.

**Decline graciously:**
> "Thank you so much for the offer and for the time everyone invested in the process. I have decided to pursue another opportunity that is a better fit for my current career goals. I was genuinely impressed by [specific positive thing] and would love to stay in touch. I hope our paths cross again."

**What NOT to do:**
- Do not trash the company or offer
- Do not reveal where you are going (unless you want to)
- Do not negotiate after declining

### Written vs Verbal Acceptance

- **Verbal acceptance** is morally binding. Do not accept verbally and then renege.
- **Written acceptance** (signed offer letter) is legally binding in most jurisdictions.
- **The order:** Verbal acceptance -> receive offer letter -> review -> sign -> return.
- If you need to renege (last resort), do it before signing. And understand it burns the bridge.

---

## Handling Counter-Offers from Current Employer

### The Scenario

You give notice. Your current employer offers more money, a promotion, or a new role to keep you.

### When to Stay

- The counter-offer addresses the **root cause** of why you were leaving (not just money)
- You were primarily motivated by compensation and the counter genuinely closes the gap
- You love the team, product, and culture — and the counter resolves the only issue

### When to Leave

- You were leaving for reasons beyond money (growth, culture, management, boredom)
- The counter-offer feels reactive ("we should have valued you before you had one foot out")
- You have already mentally moved on
- The new opportunity offers something your current company cannot (scale, domain, technology)

### Risks of Accepting Counter-Offers

**Statistics suggest that 50-80% of people who accept counter-offers leave within 12 months anyway.** Here is why:

1. **Trust is damaged.** Your manager knows you were looking. You may be first on the list in the next layoff.
2. **The underlying problems remain.** More money does not fix a bad manager, boring work, or toxic culture.
3. **The promotion may be a title bump without real change.** Verify scope, team, and responsibilities — not just title and salary.
4. **Resentment from peers.** If others find out you got a raise by threatening to leave, it poisons the well.
5. **You miss the new opportunity.** The company you turned down will not come back.

### How to Handle It

**If you decide to leave despite the counter:**
> "I really appreciate the counter-offer and it means a lot that you value my work. But my decision is about more than compensation — it is about [growth/challenge/direction]. I want to leave on good terms and will do everything I can to ensure a smooth transition."

**If you decide to stay:**
> "Thank you for the counter-offer. I have decided to stay, and I am committed to making it work. Let us discuss how we can address [the underlying issues] so this situation does not arise again."

Get the counter-offer in writing before you decline the external offer. Verbal promises from your current employer are worth nothing.

---

## Summary

Negotiation is a skill, not a personality trait. It can be practiced and improved. The key principles:

1. **Know your market value** — Research thoroughly before entering any conversation
2. **Never negotiate against yourself** — Let them name the first number
3. **Be specific** — Vague asks get vague results
4. **Back every ask with data** — Market rates, competing offers, unique skills
5. **Negotiate the package, not just the salary** — Equity, bonus, flexibility, and timing all matter
6. **Be enthusiastic** — Negotiation is collaborative, not adversarial
7. **Be willing to walk away** — The best negotiating position is having alternatives
8. **Get everything in writing** — Verbal promises do not survive organizational changes

Every dollar you negotiate now compounds over your career. A $20K increase in TC today, maintained over 10 years, is $200K+ in earnings. Spend the time.

---

## Appendix: Common Negotiation Mistakes

### Mistake 1: Accepting the First Offer

Almost every first offer has room to negotiate. Companies budget for negotiation. By accepting immediately, you leave money on the table and may even signal that you undervalue yourself. Even a simple "Thank you. I would like to take a day to review the details" buys you time.

### Mistake 2: Negotiating Only Base Salary

Base salary often has the tightest bands. Equity, sign-on bonus, and other components typically have more flexibility. A candidate who negotiates across the full package usually gets a better outcome than one who fixates on base.

### Mistake 3: Not Having a BATNA

BATNA — Best Alternative To a Negotiated Agreement. If this is your only offer and they know it, your leverage is minimal. This is why you should always interview at multiple companies simultaneously. Even if one company is your clear favorite, having alternatives changes the power dynamic.

### Mistake 4: Apologizing for Negotiating

You are not being greedy. You are not being difficult. You are conducting a standard business discussion. The recruiter expects you to negotiate. Apologizing undermines your position. Be direct, be polite, be specific — but do not apologize.

### Mistake 5: Burning Bridges When Declining

The tech industry is remarkably small. The recruiter you interact with today may be at your dream company in two years. The hiring manager may become your skip-level at a future job. Always decline graciously, specifically, and promptly.

### Mistake 6: Not Getting It in Writing

Verbal promises are worthless in a corporate context. Your recruiter may leave. The hiring manager may change. The budget may be cut. If a commitment is not in the offer letter, it does not exist. "Could you add that to the offer letter?" is a reasonable request for any agreed-upon term.

### Mistake 7: Comparing Gross Numbers Across Geographies

A $250K offer in San Francisco and a $200K offer in Austin are not $50K apart. After accounting for state income tax (California ~13% vs Texas 0%), cost of living, and housing costs, the Austin offer may actually provide more purchasing power. Always compare net purchasing power, not gross TC.

---

## Appendix: The Negotiation Timeline

```
Day 0:    Receive offer (verbal or written)
Day 0-1:  Express gratitude and enthusiasm. Ask for the offer in writing.
Day 1-3:  Analyze the offer against your research and competing offers.
Day 3-5:  Send your counter-offer (email preferred for precision).
Day 5-7:  Company reviews internally. Follow up if no response after 3 days.
Day 7-10: Receive revised offer or "final" offer.
Day 10-12: Make your decision. If accepting, confirm in writing.
Day 12-14: Sign offer letter. Give notice to current employer.
```

If you need more time at any point, ask for it early and with a specific date: "I am very excited about this offer. Could I have until [specific date] to make my decision? I want to be thorough and committed when I say yes."
