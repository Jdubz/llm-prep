# Stripe Programming Exercise Simulation

## Subscription Analytics Engine

**Time limit: 50 minutes. Set a timer now.**

Read this entire spec before writing any code. Talk out loud as you work — explain your approach, trade-offs, and decisions. This simulates the paired coding interview where your interviewer is listening.

Run your solution with:

```
npx tsx starter.ts
```

Do **NOT** open `solution.ts` until you have completed your attempt.

---

## Scenario

You are building an analytics engine for Stripe's subscription billing system. The engine processes a stream of subscription lifecycle events and answers questions about the current state, revenue metrics, customer retention, and migration patterns.

A subscription event looks like this:

```typescript
type SubscriptionEvent = {
  id: string;           // unique event id
  customerId: string;   // customer this event belongs to
  plan: string;         // plan name, e.g. "starter", "pro", "enterprise"
  action: "created" | "upgraded" | "downgraded" | "canceled" | "renewed";
  timestamp: number;    // unix timestamp in milliseconds
  mrr: number;          // monthly recurring revenue at this point
};
```

Key semantics:
- `created` — a new subscription starts. The customer is now active on `plan` with `mrr`.
- `upgraded` — customer moves to a higher plan. `plan` and `mrr` reflect the **new** values.
- `downgraded` — customer moves to a lower plan. `plan` and `mrr` reflect the **new** values.
- `canceled` — subscription ends. `mrr` is the MRR that was lost.
- `renewed` — subscription renews on the same plan. `mrr` stays the same (or may change).

A customer has at most one active subscription at a time.

Events are ingested in chronological order.

---

## Part 1 — Event Ingestion & Active Counts (15 min)

Implement:

- **`ingest(events: SubscriptionEvent[]): void`** — process an array of events into your internal data structures. May be called multiple times; events should accumulate.

- **`getActiveCount(): number`** — return the number of currently active subscriptions.

- **`getActiveByPlan(): Map<string, number>`** — return a map from plan name to the number of active subscriptions on that plan.

- **`getCustomerPlan(customerId: string): string | null`** — return the customer's current plan name, or `null` if they have no active subscription (canceled or never existed).

### Examples

```
Events:
  { customerId: "c1", plan: "starter", action: "created", mrr: 29 }
  { customerId: "c2", plan: "pro",     action: "created", mrr: 99 }
  { customerId: "c1", plan: "pro",     action: "upgraded", mrr: 99 }
  { customerId: "c3", plan: "starter", action: "created", mrr: 29 }
  { customerId: "c2", plan: "pro",     action: "canceled", mrr: 99 }

getActiveCount()        => 2
getActiveByPlan()       => Map { "pro" => 1, "starter" => 1 }
getCustomerPlan("c1")   => "pro"
getCustomerPlan("c2")   => null
```

---

## Part 2 — MRR Calculations (15 min)

Implement:

- **`getCurrentMRR(): number`** — return the total MRR across all active subscriptions.

- **`getMRRByPlan(): Map<string, number>`** — return MRR broken down by plan name.

- **`getMRRMovements(startTs: number, endTs: number): MRRMovements`** — return a breakdown of MRR changes within the time window `[startTs, endTs]` (inclusive on both ends):
  - `new` — total MRR from `created` events
  - `expansion` — total MRR **increase** from `upgraded` events (new MRR minus old MRR)
  - `contraction` — total MRR **decrease** from `downgraded` events (old MRR minus new MRR)
  - `churn` — total MRR lost from `canceled` events
  - `net` — `new + expansion - contraction - churn`

### Examples

```
Given the events above:
  getCurrentMRR()  => 128   (c1: 99 + c3: 29)
  getMRRByPlan()   => Map { "pro" => 99, "starter" => 29 }

  getMRRMovements(0, Infinity) =>
    { new: 157, expansion: 70, contraction: 0, churn: 99, net: 128 }
    // new = 29 + 99 + 29 = 157
    // expansion = 99 - 29 = 70 (c1 upgraded from 29 to 99)
    // churn = 99 (c2 canceled)
    // net = 157 + 70 - 0 - 99 = 128
```

---

## Part 3 — Cohort Analysis (12 min)

Implement:

- **`getRetention(cohortMonth: string): number[]`** — given a month like `"2024-01"`, find all customers whose subscription was `created` in that month. Return an array of retention rates for each subsequent month.
  - Index 0 = the cohort month itself (always 100 if the cohort is non-empty).
  - Index 1 = the next month, etc.
  - Rate = `Math.round((active at start of month N / total in cohort) * 100)`
  - A customer is "active at start of month N" if they have not been canceled before the start of month N.
  - Continue through the last month that contains any event in the system.
  - Return `[]` if no customers were created in that month.

- **`getChurnRate(startTs: number, endTs: number): number`** — percentage of subscriptions that were canceled in `[startTs, endTs]`, relative to the number of active subscriptions at `startTs` (before processing any events in the window). Rounded to nearest integer.
  - Return 0 if there are no active subscriptions at `startTs`.

---

## Part 4 — Plan Migration Paths (8 min, stretch goal)

Implement:

- **`getUpgradePaths(): Map<string, Map<string, number>>`** — for each plan, count how many customers upgraded **from** that plan **to** each other plan. Based on `upgraded` events.

### Example

```
If 3 customers upgraded from "starter" to "pro" and 1 from "pro" to "enterprise":
  Map {
    "starter" => Map { "pro" => 3 },
    "pro"     => Map { "enterprise" => 1 }
  }
```

- **`getAverageLifetime(plan: string): number`** — average time in milliseconds between creation and cancellation for customers who were on `plan` when they canceled. Return 0 if no customers on that plan have canceled.

---

## Evaluation Criteria

This is what Stripe interviewers are looking for:

1. **Communication** — Did you talk through your approach before coding? Did you ask clarifying questions? Did you explain trade-offs?
2. **Code quality** — Is the code clean, readable, and well-structured? Good variable names? Minimal duplication?
3. **Problem decomposition** — Did you break the problem into clear steps? Did you identify the right data structures?
4. **Correctness** — Do the self-checks pass? Did you handle edge cases?
5. **Speed** — How far did you get in 50 minutes? Completing Parts 1-3 is a strong result. Part 4 is a stretch goal.
6. **Testing instinct** — Did you think about edge cases beyond the provided checks?

### Pacing guide

| Part | Target | Cumulative |
|------|--------|------------|
| 1    | 15 min | 15 min     |
| 2    | 15 min | 30 min     |
| 3    | 12 min | 42 min     |
| 4    |  8 min | 50 min     |

If you are stuck on a part for more than 5 minutes past its target, move on. Partial progress on later parts is better than a perfect solution to an earlier part.

---

**Start your timer. Good luck.**
