# Compensation Research and Fundamentals

> You cleared the technical bar. Now the outcome is determined by your negotiation skills. This is where most engineers leave the most money on the table. Start with understanding what you are actually negotiating.

---

## Understanding Total Compensation

Base salary is not your compensation. Total compensation (TC) is. Senior engineers who focus only on base salary leave tens of thousands of dollars on the table.

### TC Formula

```
Annual TC = Base Salary
          + (Annual Equity Grant / Vesting Period)
          + Target Bonus
          + (Sign-On Bonus / Clawback Period)
          + Benefits Value
```

### Example Comparison

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

## Components of Total Compensation

### Base Salary

- The predictable, guaranteed portion of your pay
- Typically the easiest to negotiate but often has hard caps by level
- At senior levels, base becomes a smaller percentage of total compensation
- Most companies have salary bands by level — your base is constrained by where they level you

### Equity

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

### RSU Vesting Schedules in Detail

**Standard 4-year vest with 1-year cliff:**
```
Year 1: 0% (nothing vests until month 12)
Month 12 (cliff): 25% vests at once
Month 13-48: Remaining 75% vests monthly (~2.08% per month)
```

**Amazon's back-weighted schedule:**
```
Year 1: 5%
Year 2: 15%
Year 3: 40%
Year 4: 40%
```
Amazon compensates for the low year-1 and year-2 vesting with large signing bonuses that effectively equalize total compensation across all four years. But if you leave after year 2, you have received only 20% of your equity grant.

**Refresher grants:**
- Most large tech companies grant additional RSUs annually (refreshers)
- Purpose: maintain your total compensation as initial grants complete vesting
- Typical: 25-50% of your initial grant, annually
- **Critical question to ask:** "What is the typical refresher grant size for someone performing at expectations?"

**Double-trigger acceleration:**
- Single trigger: all unvested equity vests upon change of control (acquisition)
- Double trigger: equity vests only if there is a change of control AND you are terminated
- Most companies use double trigger
- As a negotiation point: ask for double-trigger acceleration if it is not already offered

### Annual Bonus

- Expressed as a target percentage of base salary (e.g., 15% target bonus)
- **Target vs actual:** The target is what you get at expected performance. Actual can be higher or lower.
- Typically depends on individual performance AND company performance
- At some companies, the bonus multiplier can exceed 100% of target for top performers
- **Ask:** "What percentage of employees hit their target bonus last year?"

### Sign-On Bonus

- One-time payment, often paid with first paycheck or in installments
- Used to offset what you are leaving behind (unvested equity, pending bonus)
- **Clawback clause:** Most sign-on bonuses must be repaid if you leave within 1-2 years. Read the terms.
- Highly negotiable — often easier to increase than base salary

### Benefits

Often overlooked but can be worth $20,000-50,000+ annually:

- **Health insurance:** Employer-paid premiums (compare out-of-pocket costs, not just "we have health insurance")
- **401(k) match:** Immediate vesting vs graded vesting. A 6% match with immediate vesting on a $200K salary is $12K/year
- **PTO:** Unlimited PTO is not always better — track what people actually take. 4 weeks defined PTO may result in more actual vacation.
- **Other:** HSA contributions, FSA, life insurance, disability, parental leave (weeks? paid?), professional development budget, WFH stipend, commuter benefits, meal allowances

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

## Evaluating Startup Equity

Startup equity is fundamentally different from public company RSUs. You cannot sell it, it may never be worth anything, and the numbers on paper are almost always misleading.

### Questions to Ask About Startup Equity

1. **How many total shares outstanding?** Your 100,000 shares mean nothing without this number. 100,000 out of 10 million (1%) is very different from 100,000 out of 1 billion (0.01%).

2. **What is the latest 409A valuation?** This is the IRS-appraised fair market value. It tells you the current theoretical value and determines your strike price.

3. **What is the preferred stock price from the last funding round?** This is typically higher than the 409A and reflects what investors paid.

4. **What is the liquidation preference?** Investors may get their money back before common shareholders get anything. A 2x liquidation preference on $50M invested means the first $100M of exit value goes to investors.

5. **What is the post-money valuation?** Divide this by total shares to get per-share value. But remember — this values preferred shares, and your shares are common stock (worth less due to fewer rights).

6. **How much runway does the company have?** More fundraising means more dilution.

### Startup Equity Valuation Framework

```
Your shares: 50,000
Total shares outstanding: 20,000,000
Your ownership: 0.25%

Latest post-money valuation: $500M
Your theoretical value: 0.25% * $500M = $1.25M

But apply discounts:
  - Illiquidity (cannot sell): -30-40%
  - Preferred vs common: -20-30%
  - Risk of failure: -50-90% depending on stage
  - Dilution from future rounds: -10-30%

Realistic expected value: $125K - $500K (wide range intentionally)
```

### Equity Evaluation Formulas

**Public Company RSUs:**
```
Annual Equity Value = (Shares Granted / Vesting Years) * Current Stock Price

Example:
  Grant: 1,000 shares over 4 years
  Current price: $150/share
  Annual value: 250 * $150 = $37,500/year
```
Risk adjustment: Consider stock price volatility. A 20% decline means $30,000/year instead.

**Startup Options (Risk-Adjusted):**
```
Paper Value = (Number of Options) * (Current FMV - Strike Price)

Risk-Adjusted Value = Paper Value
                    * (1 - Illiquidity Discount)    // 30-50%
                    * (1 - Failure Risk)             // 50-90% depending on stage
                    * (1 - Expected Dilution)         // 10-30% per round

Example:
  Options: 50,000
  Strike: $2, FMV: $10
  Paper value: 50,000 * $8 = $400,000
  Risk-adjusted: $400,000 * 0.6 * 0.4 * 0.8 = $76,800
```

### Liquidation Preferences

**What they are:** Investors' right to get paid first before common shareholders receive anything.

**Types:**
- **1x non-participating:** Investors get their investment back OR convert to common stock (whichever is more). This is founder-friendly.
- **1x participating:** Investors get their investment back AND participate in remaining proceeds. Double-dipping.
- **2x+ participating:** Investors get 2x+ their investment back AND participate. Very investor-friendly.

**Why it matters:**
```
Company raises $50M at 1x participating preferred
Company sells for $100M

Without liquidation preference:
  Investors own 30%, get $30M
  Common shareholders (including you) split $70M

With 1x participating:
  Investors get $50M back first
  Remaining $50M split: investors get 30% ($15M), common gets 70% ($35M)
  Investors total: $65M. Common total: $35M.

Your 0.25% of common: $87,500 instead of $175,000
```
In a modest exit, liquidation preferences can make common stock nearly worthless.

### Dilution

Each funding round creates new shares, reducing your percentage ownership.

```
After your grant: You own 0.50% (50,000 of 10,000,000 shares)
Series B: 2,500,000 new shares created
After Series B: You own 0.40% (50,000 of 12,500,000 shares)
Series C: 3,000,000 new shares created
After Series C: You own 0.32% (50,000 of 15,500,000 shares)
```

Typical dilution per round: 15-25%. Over 3-4 rounds, you may own half of your original percentage.

---

## ISO vs NSO Tax Implications

This is where significant money is won or lost. Get a tax advisor — what follows is educational context, not tax advice.

**ISOs (Incentive Stock Options):**

```
Grant: 10,000 shares at $10 strike price
Exercise: When stock is at $50
Sale: When stock is at $80

At exercise:
  Cost: 10,000 * $10 = $100,000
  FMV: 10,000 * $50 = $500,000
  Spread: $400,000
  Regular tax: $0 (ISO benefit)
  AMT: The $400,000 spread IS income for AMT purposes
        You may owe AMT depending on your total situation

If you hold 1 year after exercise + 2 years after grant:
  Sale proceeds: 10,000 * $80 = $800,000
  Cost basis: $100,000
  Gain: $700,000 — taxed at long-term capital gains rate (15-20%)

If you do NOT meet the holding periods (disqualifying disposition):
  Spread at exercise ($400,000) taxed as ordinary income
  Additional gain ($300,000) taxed as capital gains
```

**NSOs (Non-Qualified Stock Options):**

```
Grant: 10,000 shares at $10 strike price
Exercise when stock is at $50:
  Spread: 10,000 * ($50 - $10) = $400,000
  This is ordinary income — taxed at your marginal rate (could be 37%+ federal)
  Tax owed at exercise: ~$140,000+

Sale at $80:
  Additional gain: 10,000 * ($80 - $50) = $300,000
  Capital gains treatment if held > 1 year
```

ISOs have significantly better tax treatment IF you can handle the AMT implications and meet the holding periods. NSOs create a tax event at exercise regardless.

### 83(b) Elections

**What:** An IRS election that allows you to pay tax on restricted stock at the time of grant (current value) rather than at vesting (future value).

**When it matters:** Early-stage startup equity where shares have very low current value.

**Example:**
```
You receive 100,000 shares at $0.01/share (total value: $1,000)
Shares vest over 4 years

Without 83(b):
  Each year, 25,000 shares vest
  If value is $10/share at Year 1 vest: $250,000 ordinary income
  Tax on $250,000 at ~37% = ~$92,500

With 83(b):
  Pay tax on $1,000 at grant time: ~$370
  At vesting, no tax event
  At sale (after 1 year hold): long-term capital gains on everything above $0.01/share
```

**Critical rule:** You must file the 83(b) election within 30 days of the grant. There are no extensions. Miss this deadline and the election is impossible.

**Risk:** If you file 83(b) and then leave before vesting, you paid tax on shares you never received and get no refund.

---

## Evaluating Offers Beyond Compensation

Money matters, but it is not everything. At the senior level, career trajectory often matters more than a $20K difference in TC.

### Offer Evaluation Matrix

Rate each dimension 1-5 and weight by your personal priorities.

| Dimension | Weight (1-5) | Offer A (1-5) | Offer B (1-5) | Weighted A | Weighted B |
|-----------|-------------|---------------|---------------|-----------|-----------|
| Total compensation | | | | | |
| Equity upside | | | | | |
| Growth / promotion path | | | | | |
| Team quality | | | | | |
| Technical challenge | | | | | |
| Work-life balance | | | | | |
| Remote flexibility | | | | | |
| Company stability | | | | | |
| Product / mission | | | | | |
| Learning opportunity | | | | | |
| Location | | | | | |
| **Weighted Total** | | | | **SUM** | **SUM** |

### Non-Monetary Factors

**Growth Trajectory:**
- Is this a step up, lateral, or step down? Even a lateral move can be good if it opens a new trajectory.
- What does promotion look like? Ask: "What does the path from Senior to Staff look like here? How long does it typically take?"
- Will you learn new things? Doing the same work at a different company is not growth.

**Team Quality:**
- Who will you work with? Ask to meet your future teammates during the interview process.
- Who is the engineering manager? A great manager can transform your career. A bad one can stall it.

**Engineering Culture:**
- Deployment frequency: How often do they ship?
- Technical debt attitude: Do they acknowledge it? Budget for it?
- On-call expectations: Is there a rotation? How often? Is it compensated?

**Work-Life Balance:**
- Ask directly: "What does a typical week look like for someone in this role?"
- "How much vacation does the average person on this team actually take?"

---

## Contracting vs Full-Time

### Rate Calculations

A common mistake is comparing a contracting rate directly to a salary. They are not equivalent.

**Full-time equivalent calculation:**
```
Full-time salary: $200,000
  + Employer health insurance: ~$15,000
  + 401(k) match (6%): $12,000
  + Employer payroll taxes (FICA): ~$15,300
  + PTO (4 weeks = 7.7% of salary): ~$15,400
  + Other benefits (life insurance, disability, etc.): ~$5,000
Total employer cost: ~$262,700

Equivalent hourly rate (2,080 hours/year):
  $262,700 / 2,080 = ~$126/hour

But contractors also need to cover:
  + Self-employment tax (additional 7.65%): ~$15,300
  + Business expenses (insurance, equipment, accounting): ~$10,000
  + Unpaid time (sick days, admin, business development): ~10-20%

Realistic contractor equivalent: $140-160/hour
```

**Rule of thumb:** Your hourly contracting rate should be approximately 1.5-2x your full-time hourly equivalent to achieve similar total compensation.

### Benefits Equivalence

| Benefit | Full-Time | Contractor Must Self-Fund |
|---------|-----------|--------------------------|
| Health insurance | Employer subsidized | Individual market (ACA) or COBRA |
| 401(k) | Employer match | Solo 401(k) or SEP IRA (no match) |
| PTO | 15-25 days paid | Unpaid — bill accordingly |
| Sick leave | Paid | Unpaid |
| Disability insurance | Employer provided | Purchase individually |
| Life insurance | Employer provided | Purchase individually |
| Professional development | Company budget | Self-funded |
| Equipment | Company provided | Self-funded (tax deductible) |

### When Contracting Makes Sense

**Good reasons to contract:**
- You want schedule flexibility (4 days/week, blocks of time off)
- You want to try a company or industry before committing
- You have a niche skill in high demand (your rate commands a premium)
- You want to diversify income across multiple clients

**Bad reasons to contract:**
- "The hourly rate looks higher" (see the math above)
- The company is using contracting to avoid providing benefits
- You want job security (contractors are first to be cut in downturns)

### International Compensation

**Currency Risk:**
```
Salary: 150,000 EUR
At offer time: EUR/USD = 1.10 -> $165,000 equivalent
One year later: EUR/USD = 1.00 -> $150,000 equivalent
Effective pay cut: 9.1% without any change in nominal salary
```

**Key considerations:**
- Tax treaties: Many countries have bilateral tax treaties to prevent double taxation
- Employer of Record (EOR): Companies use EOR services (Deel, Remote.com) to hire in countries without a local entity — ask whether your equity and benefits are comparable to direct employees
- US citizens are taxed on worldwide income regardless of residence — get a tax advisor specializing in international taxation before accepting

---

## Compensation Comparison Worksheet

Use this to compare offers systematically:

| Component | Offer A | Offer B | Current | Notes |
|-----------|---------|---------|---------|-------|
| Base salary | | | | |
| Equity (annual value) | | | | Include refresh assumptions |
| Target bonus | | | | Percentage AND dollar amount |
| Sign-on bonus | | | | Note clawback period |
| Health insurance (net cost) | | | | Your out-of-pocket cost |
| 401(k) match | | | | Match % and vesting |
| PTO (days) | | | | Unlimited? Track actual usage. |
| Other benefits | | | | Parental leave, WFH stipend, etc. |
| **Year 1 TC** | | | | Sum of all components |
| **Year 2+ TC** | | | | Without sign-on, with refreshers |
| **4-Year Total** | | | | Full vesting period |
