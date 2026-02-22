# Module 08 Deep Dive: Compensation, Equity, and Advanced Negotiation

> The details that separate informed negotiators from everyone else. This is where the real money is.

---

## Table of Contents

1. [Equity Deep Dive](#equity-deep-dive)
2. [Executive Negotiation](#executive-negotiation)
3. [International Compensation](#international-compensation)
4. [Contracting vs Full-Time](#contracting-vs-full-time)

---

## Equity Deep Dive

### RSU Vesting Schedules in Detail

**Standard 4-year vest with 1-year cliff:**
```
Year 1: 0% (nothing vests until month 12)
Month 12 (cliff): 25% vests at once
Month 13-48: Remaining 75% vests monthly (~2.08% per month)
```

**Why the cliff exists:** It protects the company from granting equity to someone who leaves in 3 months. It protects you by ensuring a meaningful first vest.

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
- Some companies (notably Amazon historically) have had below-market refresher grants, meaning TC drops significantly after the sign-on bonus expires

**Double-trigger acceleration:**
- Single trigger: all unvested equity vests upon change of control (acquisition)
- Double trigger: equity vests only if there is a change of control AND you are terminated
- Most companies use double trigger
- As a negotiation point: ask for double-trigger acceleration if it is not already offered

### ISO vs NSO Tax Implications

This is where significant money is won or lost. Get a tax advisor — this is not tax advice.

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

**Key insight:** ISOs have significantly better tax treatment IF you can handle the AMT implications and meet the holding periods. NSOs create a tax event at exercise regardless.

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

### Evaluating Startup Equity

Startup equity is fundamentally different from public company RSUs. You cannot sell it, it may never be worth anything, and the numbers on paper are almost always misleading.

**Questions to ask:**

1. **How many total shares outstanding?** Your 100,000 shares mean nothing without this number. 100,000 out of 10 million (1%) is very different from 100,000 out of 1 billion (0.01%).

2. **What is the latest 409A valuation?** This is the IRS-appraised fair market value. It tells you the current theoretical value and determines your strike price.

3. **What is the preferred stock price from the last funding round?** This is typically higher than the 409A and reflects what investors paid.

4. **What is the liquidation preference?** Investors may get their money back before common shareholders get anything. A 2x liquidation preference on $50M invested means the first $100M of exit value goes to investors.

5. **What is the post-money valuation?** Divide this by total shares to get per-share value. But remember — this values preferred shares, and your shares are common stock (worth less due to fewer rights).

6. **How much runway does the company have?** More fundraising means more dilution.

**Rough valuation framework:**
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

### Liquidation Preferences

**What they are:** Investors' right to get paid first (and sometimes a multiple of their investment) before common shareholders receive anything.

**Types:**
- **1x non-participating:** Investors get their investment back OR convert to common stock (whichever is more). This is founder-friendly.
- **1x participating:** Investors get their investment back AND participate in remaining proceeds as if they had converted. Double-dipping.
- **2x+ participating:** Investors get 2x+ their investment back AND participate. Very investor-friendly.

**Why it matters to you:**
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

**Key insight:** In a modest exit, liquidation preferences can make common stock nearly worthless. This is why a $500M valuation does not mean your equity is worth 0.25% of $500M.

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

**Ask about anti-dilution protections** — these typically only apply to investors, not employees, but some companies offer partial anti-dilution for early employees.

---

## Executive Negotiation

### VP/Director Level Compensation

At the VP and Director level, compensation structures change significantly:

**Equity becomes dominant:**
- At Staff+ / Director level: equity may be 40-60% of total compensation
- At VP level: equity may be 50-70%+
- Grants shift from RSUs to a mix of RSUs + performance-based equity

**Performance-based equity:**
- Vests only if certain metrics are met (revenue targets, stock price targets)
- Can result in 0% to 200%+ of the target grant
- Negotiate the targets — ensure they are achievable

**Signing bonuses scale up:**
- $100K-500K+ signing bonuses are common at VP level
- Used to make up for significant unvested equity being left behind
- Negotiate the clawback terms — push for 1 year instead of 2

### Golden Parachutes

**What:** Severance agreements triggered by termination without cause, often after an acquisition.

**Typical terms:**
- 6-18 months of base salary
- Acceleration of unvested equity (partial or full)
- COBRA coverage continuation
- Bonus payout for the current year

**When to negotiate:** Before accepting. It is much harder to negotiate severance after you have started.

**Key terms to include:**
- Definition of "cause" (should be narrow — fraud, felony, gross negligence)
- Change-of-control provisions (what happens to your equity if the company is acquired)
- Non-compete scope (duration, geographic, industry limitations)

### Board Seats and Observer Rights

At the C-level or VP-level in smaller companies:

- **Board observer seat:** Attend board meetings without voting rights. Valuable for learning governance.
- **Board seat:** Rare for VP-level hires, but negotiable at C-level in startups.
- **Advisory board:** Lower commitment, some equity compensation, good for portfolio building.

---

## International Compensation

### Currency Risk

If you are paid in a currency other than your primary spending currency, exchange rate fluctuations directly affect your real compensation.

**Example:**
```
Salary: 150,000 EUR
At offer time: EUR/USD = 1.10 -> $165,000 equivalent
One year later: EUR/USD = 1.00 -> $150,000 equivalent
Effective pay cut: 9.1% without any change in nominal salary
```

**Mitigation strategies:**
- Negotiate salary in your spending currency if possible
- Ask for annual cost-of-living adjustments that account for FX
- For large equity grants, understand the grant currency vs sale currency

### Tax Treaties

Many countries have bilateral tax treaties to prevent double taxation. Key considerations:

- **Tax equalization:** Some companies guarantee you pay no more tax than you would in your home country
- **Totalization agreements:** Prevent paying social security taxes in two countries simultaneously
- **Foreign tax credits:** US citizens working abroad can credit foreign taxes against US tax liability
- **US citizens are taxed on worldwide income** regardless of residence — this is unique among developed nations

**If relocating internationally for a job:** Get a tax advisor who specializes in international taxation BEFORE accepting the offer. The tax implications can swing total compensation by 20%+.

### Employer of Record (EOR)

Companies that want to hire in countries without a local entity use an EOR (Deel, Remote.com, Oyster, Papaya Global).

**What it means for you:**
- Legally, you are employed by the EOR, not the company
- Benefits are provided by the EOR (may differ from direct employees)
- Equity grants may be structured differently (phantom equity, SARs)
- You may have fewer employment protections than direct employees

**Questions to ask:**
- "Will I receive the same equity as direct employees?"
- "Are my benefits comparable to direct employees?"
- "Is there a path to direct employment if you open a local entity?"
- "Who handles disputes — the EOR or the company?"

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

### 1099 vs W-2

**1099 (Independent Contractor):**
- You control how, when, and where you work
- You provide your own equipment
- You pay self-employment tax (both employer and employee portions of FICA)
- You can deduct business expenses
- No benefits, no protections under employment law
- Quarterly estimated tax payments required

**W-2 (Employee — including through staffing agency):**
- Company controls your work schedule and methods
- Company provides equipment
- Employer pays their portion of FICA
- Standard tax withholding
- Employment protections (unemployment insurance, workers' comp)
- May still lack benefits if through a staffing agency

**Misclassification risk:** If a company treats you as a 1099 contractor but controls your work like an employee, this is misclassification. The IRS cares about this. If a company requires specific hours, provides equipment, and integrates you into their team, you are likely an employee regardless of what the contract says.

### When Contracting Makes Sense

**Good reasons to contract:**
- You want schedule flexibility (4 days/week, blocks of time off)
- You want to try a company or industry before committing
- You have a niche skill in high demand (your rate commands a premium)
- You want to diversify income across multiple clients
- You are between roles and want to stay active

**Bad reasons to contract:**
- "The hourly rate looks higher" (see the math above)
- The company is using contracting to avoid providing benefits
- You want job security (contractors are first to be cut in downturns)

### Transitioning from Contract to Full-Time

This is common and can be advantageous — you already know the company.

**Negotiation points:**
- Your full-time salary should reflect your proven value, not a discount from your contract rate
- Request credit for your contract period toward vesting or tenure
- Negotiate a signing bonus to offset the rate drop during the transition period
- Ask about the cliff — some companies waive or reduce the cliff for contract-to-hire conversions

---

## Summary

The deeper you understand compensation mechanics, the more effectively you can negotiate. Key takeaways:

1. **Equity is complicated.** Understanding RSU vesting, ISO/NSO tax treatment, 83(b) elections, and startup equity valuation can save (or cost) you six figures.
2. **Total compensation is more than the headline number.** Benefits, tax treatment, and equity structure matter enormously.
3. **International and contracting arrangements require special attention.** The tax and legal implications are meaningful.
4. **Get professional advice for big decisions.** A tax advisor costs a few hundred dollars. A mistake on ISO exercise or 83(b) timing can cost tens of thousands.

---

## Appendix: Equity Negotiation Scenarios

### Scenario 1: Public Company — Negotiating RSU Grant Size

**Situation:** You receive an offer from a public company with a $200K RSU grant over 4 years ($50K/year). You believe the role warrants more.

**Approach:**
> "Based on my research on levels.fyi, the P75 equity grant for [Level] at [Company] is $300K. Given my [X years] of experience with [specific relevant domain], I believe a $280K grant would better reflect the value I bring. Would the team be open to increasing the equity component?"

**Why equity over base:** Equity grants often have more flexibility than base salary. The company can adjust grant sizes more easily than salary bands, which may require formal exceptions.

### Scenario 2: Pre-IPO Company — Evaluating an Options Package

**Situation:** You receive an offer from a Series C startup. They offer 50,000 ISOs at a $5 strike price. Latest 409A is $8/share. Last preferred round priced at $15/share.

**Questions to ask:**
1. "What is the total share count on a fully diluted basis?" (To calculate your ownership percentage)
2. "What is the company's current revenue and growth rate?" (To assess trajectory)
3. "What are the liquidation preferences on the preferred shares?" (To understand what common stock is actually worth in an exit)
4. "How many more rounds of funding are anticipated?" (To estimate future dilution)
5. "What is the post-exercise period if I leave?" (Standard is 90 days; negotiate for longer if possible)

**Red flags:**
- "We cannot share the total share count" — This makes your equity impossible to value. Push back.
- Very high liquidation preferences (2x+ participating) — Common stock may be nearly worthless in anything less than a blockbuster exit.
- No path to liquidity — If the company has no IPO or acquisition timeline, your options may never be convertible to cash.

### Scenario 3: Negotiating Acceleration Clauses

**Situation:** You are joining as a VP at a company that may be acquired in 12-18 months.

**What to negotiate:**
- **Double-trigger acceleration:** 100% of unvested equity vests if the company is acquired AND you are terminated without cause within 12 months
- **Partial single-trigger:** 25-50% acceleration on acquisition alone
- **Retention bonus:** Additional equity or cash grant tied to staying through the acquisition integration period

**Why it matters:** Without acceleration, an acquirer may terminate you and your unvested equity simply disappears. This is especially common when the acquiring company has their own people for your role.

### Scenario 4: Comparing a High-Cash Startup Offer vs a Public Company RSU Offer

```
Startup Offer:
  Base: $220,000
  Options: 100,000 at $2 strike (409A: $5)
  Series B, valued at $200M
  No bonus

Public Company Offer:
  Base: $190,000
  RSUs: $250,000 over 4 years ($62,500/yr)
  Bonus: 15% target ($28,500)
  Sign-on: $30,000

Year 1 comparison:
  Startup: $220,000 + speculative equity value
  Public: $190,000 + $62,500 + $28,500 + $30,000 = $311,000

Risk-adjusted comparison:
  Startup equity (100K options * $3 spread = $300K paper):
    Risk-adjusted at 20% expected value = $60,000
    Annual: $60,000 / 4 = $15,000
  Startup Year 1 TC (risk-adjusted): ~$235,000
  Public Year 1 TC: $311,000
```

The startup needs to provide roughly $75K more in annual value to match — either through higher base, higher equity confidence, or both. Make this math explicit when evaluating.
