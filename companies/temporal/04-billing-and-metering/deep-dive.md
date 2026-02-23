# Billing & Metering Deep Dive -- Advanced Topics

> Deeper content on revenue recognition, dunning, proration, multi-currency, scale,
> and using Temporal workflows for billing pipelines.

---

## Table of Contents

1. [Revenue Recognition (ASC 606)](#revenue-recognition-asc-606)
2. [Dunning and Payment Recovery](#dunning-and-payment-recovery)
3. [Proration and Plan Changes](#proration-and-plan-changes)
4. [Multi-Currency and Tax](#multi-currency-and-tax)
5. [Scale Considerations](#scale-considerations)
6. [Temporal Workflows for Billing](#temporal-workflows-for-billing)

---

## Revenue Recognition (ASC 606)

### Why Engineers Need to Care

Revenue recognition determines *when* a company can count money as earned revenue on its financial statements. This is not just an accounting concern -- the billing system must produce data that supports the finance team's revenue recognition process. If the system cannot answer "how much revenue was earned in Q1 2026 under ASC 606 rules," the finance team will build fragile spreadsheet workarounds that eventually break.

ASC 606 is the accounting standard (US GAAP) that governs revenue recognition for software companies. The core principle: recognize revenue when the performance obligation is satisfied, in the amount the company expects to be entitled to.

### The Five-Step Model

```
Step 1: Identify the contract
Step 2: Identify performance obligations
Step 3: Determine the transaction price
Step 4: Allocate the price to performance obligations
Step 5: Recognize revenue when obligations are satisfied
```

**For usage-based billing (like Temporal Cloud):**

- **Contract:** The subscription agreement or marketplace entitlement.
- **Performance obligation:** Providing access to the platform and processing actions. For usage-based, this is typically a "stand-ready" obligation satisfied over time.
- **Transaction price:** For pure usage-based, the price is variable (depends on usage). For committed use, there is a fixed component.
- **Recognition timing:** Revenue is recognized as usage occurs. If a customer uses 10M actions in January and 15M in February, the revenue is recognized in the periods of usage, not when payment is collected.

### Committed Use and Prepayment

Committed use agreements introduce complexity:

```
Customer commits to $120,000/year for 100M actions/month.
Customer pays $120,000 upfront.

Question: When do you recognize the $120,000?
Answer:   NOT all at once. Recognize ~$10,000/month as the service is delivered.
```

**The billing system must track:**

1. **Deferred revenue:** The $120,000 payment is initially recorded as deferred revenue (a liability -- the company owes the customer the service). Each month, $10,000 moves from deferred revenue to recognized revenue.

2. **Usage against commitment:** If the customer uses only 50M of their 100M committed actions in a month, the revenue is still $10,000 (the commitment, not the usage). The unused capacity does not roll over unless the contract says otherwise.

3. **Overage:** If the customer uses 120M actions (20M over commitment), the overage is recognized in the month it occurs at the overage rate.

```sql
-- Deferred revenue tracking
CREATE TABLE deferred_revenue (
    id              UUID PRIMARY KEY,
    customer_id     UUID NOT NULL,
    contract_id     UUID NOT NULL,
    total_amount_cents BIGINT NOT NULL,
    recognized_cents   BIGINT NOT NULL DEFAULT 0,
    remaining_cents    BIGINT GENERATED ALWAYS AS (total_amount_cents - recognized_cents) STORED,
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Monthly recognition entries
CREATE TABLE revenue_recognition (
    id              UUID PRIMARY KEY,
    customer_id     UUID NOT NULL,
    contract_id     UUID NOT NULL,
    period          DATE NOT NULL,  -- the month being recognized
    recognized_cents BIGINT NOT NULL,
    revenue_type    TEXT NOT NULL,  -- 'committed', 'overage', 'usage'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(contract_id, period, revenue_type)
);
```

### What the System Must Support

The billing system needs to produce these outputs for finance:

| Report | Purpose | Data Required |
|--------|---------|---------------|
| Revenue waterfall | Show recognized vs deferred revenue by month | Contract terms, payment dates, recognition schedule |
| Usage-based revenue | Revenue from variable usage per customer per period | Metered usage, rating, billing period |
| Deferred revenue balance | Current liability for prepaid commitments | Contracts, recognition to date |
| Overage revenue | Revenue from usage above commitments | Usage above committed level, overage rate |

**Key design principle:** Separate the concerns of billing (what to charge) and revenue recognition (when to count it as revenue). A customer might be billed annually but have revenue recognized monthly. A customer might be billed monthly but have a portion of revenue deferred (e.g., for a setup fee amortized over the contract).

---

## Dunning and Payment Recovery

### The Revenue Impact

Involuntary churn (customers leaving because their payment failed, not because they chose to leave) can account for 20-40% of total churn for SaaS companies. Effective dunning recovers the majority of these failed payments.

### Dunning State Machine

```
Payment Due
    │
    ▼
First Attempt ──── Success ──► Paid
    │
    │ Failure
    ▼
Grace Period Start (Day 0)
    │
    ├── Notification: "Payment failed, please update payment method"
    │
    ▼
Retry 1 (Day 3) ──── Success ──► Paid
    │
    │ Failure
    ├── Notification: "Second attempt failed"
    │
    ▼
Retry 2 (Day 7) ──── Success ──► Paid
    │
    │ Failure
    ├── Notification: "Action required -- service may be affected"
    │
    ▼
Service Degradation (Day 14)
    │
    ├── Account set to read-only or rate-limited
    ├── Notification: "Service degraded -- update payment to restore"
    │
    ▼
Retry 3 (Day 14) ──── Success ──► Paid + Restore Service
    │
    │ Failure
    ├── Notification: "Final notice -- account will be suspended"
    │
    ▼
Account Suspension (Day 21)
    │
    ├── All API access disabled
    ├── Data retained per policy
    │
    ▼
Final Retry (Day 28) ──── Success ──► Paid + Reactivate
    │
    │ Failure
    ▼
Write Off + Offboarding
    │
    ├── Invoice marked as uncollectable
    ├── Begin offboarding flow
    └── Data retention countdown begins
```

### Smart Retry Strategies

Not all retries are equal. The probability of success varies based on timing and context.

**Retry optimization factors:**

| Factor | Why It Matters | Strategy |
|--------|---------------|----------|
| Time of day | Banks process transactions more reliably during business hours | Retry at 10 AM in the customer's timezone |
| Day of week | Weekday transactions succeed more often than weekends | Prefer Tuesday-Thursday |
| Day of month | Accounts are more likely funded after payday (1st, 15th) | Schedule retries near common pay dates |
| Failure reason | "Insufficient funds" may resolve in days; "card expired" will not | Branch strategy on decline code |
| Payment method | Some customers have multiple methods on file | Try alternate payment method on retry |

**Stripe decline codes and recommended actions:**

| Decline Code | Meaning | Recommended Action |
|-------------|---------|-------------------|
| `insufficient_funds` | Not enough money | Retry in 3-5 days |
| `card_declined` | Generic decline | Retry in 3 days, then notify customer |
| `expired_card` | Card has expired | Notify customer to update payment method immediately |
| `incorrect_cvc` | CVC mismatch | Notify customer, do not retry (card data is wrong) |
| `processing_error` | Temporary bank issue | Retry in 24 hours |
| `authentication_required` | SCA/3DS needed | Send customer a payment link |
| `fraudulent` | Bank suspects fraud | Do not retry, notify customer |

### Dunning as a Temporal Workflow

```go
func DunningWorkflow(ctx workflow.Context, invoiceID string, customerID string) error {
    retrySchedule := []struct {
        delay    time.Duration
        action   string
    }{
        {0, "first_attempt"},
        {3 * 24 * time.Hour, "retry_1"},
        {4 * 24 * time.Hour, "retry_2"},  // Day 7
        {7 * 24 * time.Hour, "retry_3_with_degradation"},  // Day 14
        {7 * 24 * time.Hour, "retry_4_with_suspension"},    // Day 21
        {7 * 24 * time.Hour, "final_retry"},                // Day 28
    }

    for i, step := range retrySchedule {
        if step.delay > 0 {
            workflow.Sleep(ctx, step.delay)
        }

        // Check if customer resolved the issue themselves
        paymentCh := workflow.GetSignalChannel(ctx, "payment-received")
        if paymentCh.ReceiveAsync(nil) {
            return nil // Payment received externally
        }

        // Attempt payment
        var result PaymentResult
        err := workflow.ExecuteActivity(ctx, AttemptPaymentActivity, invoiceID).Get(ctx, &result)

        if err == nil && result.Success {
            // Payment succeeded
            if step.action == "retry_3_with_degradation" || step.action == "retry_4_with_suspension" {
                workflow.ExecuteActivity(ctx, RestoreServiceActivity, customerID).Get(ctx, nil)
            }
            return nil
        }

        // Send notification
        workflow.ExecuteActivity(ctx, SendDunningNotificationActivity, customerID, step.action, result.DeclineCode).Get(ctx, nil)

        // Apply service degradation/suspension if needed
        switch step.action {
        case "retry_3_with_degradation":
            workflow.ExecuteActivity(ctx, DegradeServiceActivity, customerID).Get(ctx, nil)
        case "retry_4_with_suspension":
            workflow.ExecuteActivity(ctx, SuspendServiceActivity, customerID).Get(ctx, nil)
        }

        // If card expired or fraud, skip remaining retries
        if result.DeclineCode == "expired_card" || result.DeclineCode == "fraudulent" {
            break
        }
    }

    // All retries exhausted
    workflow.ExecuteActivity(ctx, WriteOffInvoiceActivity, invoiceID).Get(ctx, nil)
    workflow.ExecuteActivity(ctx, StartOffboardingActivity, customerID).Get(ctx, nil)
    return nil
}
```

**Why Temporal is ideal for dunning:**
- The retry schedule spans weeks. Temporal handles long-lived timers natively.
- If the customer pays manually at any point, you can signal the workflow to stop.
- Service degradation and restoration are activities with automatic retry.
- The full dunning history is in the workflow event history -- auditable, debuggable.

### Impact Metrics

Track these to measure dunning effectiveness:

| Metric | What It Measures | Target |
|--------|-----------------|--------|
| Recovery rate | % of failed payments eventually collected | > 70% |
| Time to recovery | Average days from first failure to payment | < 7 days |
| Involuntary churn rate | % of customers lost due to payment failure | < 2%/month |
| Dunning email open rate | Engagement with payment failure notifications | > 40% |

---

## Proration and Plan Changes

### The Proration Problem

A customer on a $200/month plan upgrades to a $500/month plan on February 15. What do they owe for February?

**Option 1: No proration.** Charge $200 for February, $500 starting March. Simple but the customer gets the upgraded plan without paying for it for half a month.

**Option 2: Full proration.** Calculate the unused portion of the old plan and the used portion of the new plan.

```
February has 28 days.
Old plan: $200/month, used Feb 1-14 (14 days) = $200 * (14/28) = $100.00
New plan: $500/month, used Feb 15-28 (14 days) = $500 * (14/28) = $250.00
February invoice: $100.00 + $250.00 = $350.00
```

**Option 3: Credit-based proration.** Issue a credit for the unused portion of the old plan, then charge the full new plan price.

```
Credit for unused old plan: $200 * (14/28) = -$100.00
New plan charge: $500 * (14/28) = $250.00
Net charge: $150.00
(Next month: full $500.00)
```

### Proration for Usage-Based Plans

For pure usage-based billing (like Temporal's per-action pricing), proration of usage charges is automatic -- you only pay for what you use. Proration only applies to:

- **Base fees:** A flat monthly platform fee that needs to be prorated.
- **Committed use minimums:** If a customer commits to 100M actions/month and upgrades to a 200M commitment mid-month, the commitment needs to be prorated.
- **Tier changes:** If the per-action price changes mid-month, usage before and after the change should be rated at different prices.

```
Mid-month tier change example:
  Feb 1-14:  8,000,000 actions at old pricing (Tier 1: $25/M, Tier 2: $20/M)
  Feb 15-28: 7,000,000 actions at new pricing (Tier 1: $20/M, Tier 2: $15/M)

  Invoice line items:
    Period 1 (Feb 1-14):
      Tier 1: 1,000,000 x $0.000025 = $25.00
      Tier 2: 7,000,000 x $0.000020 = $140.00
    Period 2 (Feb 15-28):
      Tier 1: 1,000,000 x $0.000020 = $20.00
      Tier 2: 6,000,000 x $0.000015 = $90.00
    Total: $275.00
```

### Implementation Approach

```go
type PlanChange struct {
    CustomerID    string
    OldPlanID     string
    NewPlanID     string
    EffectiveDate time.Time
    ChangeType    string // "upgrade", "downgrade", "migration"
}

func ProrateBillingPeriod(
    ctx context.Context,
    change PlanChange,
    billingPeriod DateRange,
    usage UsageData,
) ([]InvoiceLineItem, error) {
    // Split usage into before and after the plan change
    usageBefore := usage.FilterBefore(change.EffectiveDate)
    usageAfter := usage.FilterOnOrAfter(change.EffectiveDate)

    // Rate each portion under the applicable plan
    oldPlan, err := db.GetPlan(ctx, change.OldPlanID)
    if err != nil {
        return nil, err
    }
    newPlan, err := db.GetPlan(ctx, change.NewPlanID)
    if err != nil {
        return nil, err
    }

    lineItemsBefore := RateUsage(usageBefore, oldPlan)
    lineItemsAfter := RateUsage(usageAfter, newPlan)

    // Prorate base fees
    daysInPeriod := billingPeriod.Days()
    daysBefore := change.EffectiveDate.Sub(billingPeriod.Start).Hours() / 24
    daysAfter := float64(daysInPeriod) - daysBefore

    if oldPlan.BaseFeeCents > 0 {
        proratedOldBase := int64(float64(oldPlan.BaseFeeCents) * daysBefore / float64(daysInPeriod))
        lineItemsBefore = append(lineItemsBefore, InvoiceLineItem{
            Description: fmt.Sprintf("Base fee (%s) - prorated %d/%d days", oldPlan.Name, int(daysBefore), daysInPeriod),
            AmountCents: proratedOldBase,
        })
    }

    if newPlan.BaseFeeCents > 0 {
        proratedNewBase := int64(float64(newPlan.BaseFeeCents) * daysAfter / float64(daysInPeriod))
        lineItemsAfter = append(lineItemsAfter, InvoiceLineItem{
            Description: fmt.Sprintf("Base fee (%s) - prorated %d/%d days", newPlan.Name, int(daysAfter), daysInPeriod),
            AmountCents: proratedNewBase,
        })
    }

    return append(lineItemsBefore, lineItemsAfter...), nil
}
```

### Stripe Proration

Stripe handles proration natively for subscription changes:

```go
sub, err := subscription.Update(subscriptionID, &stripe.SubscriptionParams{
    Items: []*stripe.SubscriptionItemsParams{
        {
            ID:    stripe.String(existingItemID),
            Price: stripe.String(newPriceID),
        },
    },
    ProrationBehavior: stripe.String("create_prorations"), // or "none" or "always_invoice"
})
```

**Stripe proration behaviors:**
- `create_prorations`: Creates credit and debit line items on the next invoice.
- `none`: No proration. The new price takes effect at the next billing period.
- `always_invoice`: Immediately generates an invoice for the proration amount.

If you manage your own rating logic (recommended for complex pricing), you likely set Stripe to `none` and handle proration yourself, pushing the calculated line items to Stripe.

---

## Multi-Currency and Tax

### Currency Handling

**Rule: Store amounts in the smallest unit of the currency.**

| Currency | Smallest Unit | Example |
|----------|--------------|---------|
| USD | cent | $29.99 = 2999 cents |
| EUR | cent | 29.99 EUR = 2999 cents |
| JPY | yen (no subunit) | 3000 JPY = 3000 |
| BHD | fils (1/1000) | 29.990 BHD = 29990 fils |

Most currencies have 2 decimal places, but some have 0 (JPY, KRW) and others have 3 (BHD, KWD, OMR). Your billing system must handle all cases.

```go
type Money struct {
    Amount   int64  // In smallest currency unit
    Currency string // ISO 4217 code
}

// CurrencyExponent returns the number of decimal places for a currency
func CurrencyExponent(currency string) int {
    switch currency {
    case "JPY", "KRW", "VND":
        return 0
    case "BHD", "KWD", "OMR":
        return 3
    default:
        return 2 // Most currencies
    }
}

func (m Money) ToDecimalString() string {
    exp := CurrencyExponent(m.Currency)
    if exp == 0 {
        return fmt.Sprintf("%d", m.Amount)
    }
    divisor := math.Pow10(exp)
    return fmt.Sprintf("%.*f", exp, float64(m.Amount)/divisor)
}
```

**Currency conversion considerations:**
- Conversion rates fluctuate. Lock the rate at the time of invoice generation and store it with the invoice.
- Never convert and then convert back. Rounding compounds.
- Stripe handles settlement currency conversion -- you can charge in the customer's currency and receive settlement in yours.

### Tax Calculation

Tax on SaaS products varies by jurisdiction and is increasingly complex.

**Options for tax calculation:**

| Approach | Pros | Cons |
|----------|------|------|
| Stripe Tax | Integrated with Stripe, automatic calculations | Limited jurisdiction support, tied to Stripe |
| Avalara | Comprehensive tax calculation, global coverage | Additional vendor, API latency on invoice generation |
| Manual rules | Full control, no vendor dependency | Must maintain rules yourself, error-prone for international |
| Tax-exempt only | Simplest -- only sell to business customers with tax exemptions | Does not scale to self-service or consumer customers |

**Tax calculation flow:**

```
Customer Address
    │
    ▼
Tax Jurisdiction
Determination ──► "US, California" or "EU, Germany" or "Tax exempt"
    │
    ▼
Tax Rate Lookup ──► 8.25% (CA sales tax) or 19% (DE VAT)
    │
    ▼
Tax Calculation ──► subtotal * rate = tax amount
    │
    ▼
Invoice Line Item: "Sales Tax (CA 8.25%): $23.10"
```

**Critical tax data to store:**

```sql
CREATE TABLE invoice_tax (
    id              UUID PRIMARY KEY,
    invoice_id      UUID NOT NULL REFERENCES invoices(invoice_id),
    jurisdiction    TEXT NOT NULL,   -- "US-CA" or "DE" or "GB"
    tax_type        TEXT NOT NULL,   -- "sales_tax", "vat", "gst"
    taxable_cents   BIGINT NOT NULL, -- Amount subject to tax
    rate_percent    NUMERIC(6,4) NOT NULL, -- 8.2500 for 8.25%
    tax_cents       BIGINT NOT NULL,
    exempt          BOOLEAN DEFAULT FALSE,
    exemption_reason TEXT            -- "B2B reverse charge" or "tax-exempt org"
);
```

**Store the rate that was applied, not just the result.** Tax rates change. For audit purposes, you need to prove that you applied the correct rate at the time of invoicing.

### International Compliance

| Region | Tax Type | Key Rule |
|--------|----------|----------|
| US | Sales tax | Varies by state and locality. Nexus rules determine where you owe tax. |
| EU | VAT | Charge VAT based on customer's country. B2B sales may use reverse charge. |
| UK | VAT | 20% standard rate. Post-Brexit, separate from EU VAT. |
| Canada | GST/HST/PST | Federal + provincial taxes. Varies by province. |
| Australia | GST | 10% on most goods and services. |
| India | GST | 18% on SaaS. Must register if selling to Indian customers. |

The billing system should support tax exemptions (B2B customers with valid tax IDs), reverse charge mechanisms (EU B2B), and configurable tax rules per jurisdiction.

---

## Scale Considerations

### High-Cardinality Metering Data

At scale, the metering pipeline handles millions of events per day across thousands of customers, each with multiple namespaces and action types.

**The cardinality problem:**

```
Dimensions:
  customer_id:  ~10,000 unique
  namespace_id: ~50,000 unique (avg 5 per customer)
  action_type:  ~20 unique
  region:       ~5 unique

Total unique combinations: 10,000 * 5 * 20 * 5 = 5,000,000

At hourly granularity: 5,000,000 * 24 * 30 = 3.6 billion rows/month
```

3.6 billion rows per month in the raw aggregation table is too many for PostgreSQL to query efficiently for billing.

**Solutions:**

1. **Reduce cardinality.** Billing does not need per-namespace-per-action-per-region granularity. Aggregate to customer-level for billing. Keep the higher-cardinality data for customer-facing dashboards and analytics.

2. **Partitioning.** Partition the aggregated table by billing period (monthly partitions). Billing queries only touch the current period's partition.

3. **Tiered storage.** Hot data (current and previous month) in PostgreSQL. Warm data (last 12 months) in Redshift/BigQuery. Cold data (older) in S3 with Athena for ad-hoc queries.

```sql
-- Partition by month for billing queries
CREATE TABLE daily_usage (
    customer_id   UUID NOT NULL,
    date          DATE NOT NULL,
    action_type   TEXT NOT NULL,
    quantity      BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (date);

CREATE TABLE daily_usage_2026_02 PARTITION OF daily_usage
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');

CREATE TABLE daily_usage_2026_03 PARTITION OF daily_usage
    FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Billing query only scans one partition
SELECT action_type, SUM(quantity) as total_actions
FROM daily_usage
WHERE customer_id = $1 AND date >= '2026-02-01' AND date < '2026-03-01'
GROUP BY action_type;
```

### Aggregation Pipeline Scaling

| Approach | Events/Day | Latency | Complexity |
|----------|-----------|---------|------------|
| Batch (cron) | Up to 100M | Hours | Low |
| Micro-batch (Spark) | Up to 1B | Minutes | Medium |
| Streaming (Flink/Kafka Streams) | 1B+ | Seconds | High |

**For Temporal's scale:** Likely in the 10M-100M events/day range. A batch approach (hourly aggregation jobs) is sufficient and simpler to operate. Streaming becomes necessary when customers need real-time usage data or when event volume exceeds what batch jobs can process in the batch window.

### Billing Run Optimization

At the end of each billing period, you must generate invoices for all customers. With 10,000 customers, this must be parallelizable and idempotent.

```go
func BillingRunWorkflow(ctx workflow.Context, billingPeriod DateRange) error {
    // Get all active customers
    var customers []string
    err := workflow.ExecuteActivity(ctx, GetActiveCustomersActivity).Get(ctx, &customers)
    if err != nil {
        return err
    }

    // Process customers in parallel batches
    batchSize := 100
    for i := 0; i < len(customers); i += batchSize {
        end := i + batchSize
        if end > len(customers) {
            end = len(customers)
        }
        batch := customers[i:end]

        // Launch child workflows for each customer in the batch
        var futures []workflow.ChildWorkflowFuture
        for _, customerID := range batch {
            future := workflow.ExecuteChildWorkflow(ctx, CustomerInvoiceWorkflow, customerID, billingPeriod)
            futures = append(futures, future)
        }

        // Wait for all in the batch to complete
        for _, future := range futures {
            if err := future.Get(ctx, nil); err != nil {
                // Log error but continue -- one customer's failure should not block others
                workflow.GetLogger(ctx).Error("Invoice generation failed", "error", err)
            }
        }
    }

    // Run reconciliation after all invoices are generated
    return workflow.ExecuteActivity(ctx, ReconciliationActivity, billingPeriod).Get(ctx, nil)
}
```

**Key design decisions:**
- Process customers in parallel (batch of 100 at a time) to complete within the SLA.
- Each customer's invoice is a child workflow -- isolated failure, independent retry.
- A single customer's failure does not block the billing run for others.
- Reconciliation runs after all invoices are generated.
- The entire billing run is idempotent. Running it twice for the same period produces the same invoices (existing invoices are skipped).

### Database Partitioning for Billing Data

| Table | Partition Strategy | Why |
|-------|-------------------|-----|
| `raw_events` | By date (daily) | Raw events are queried by date range for reconciliation |
| `daily_usage` | By date (monthly) | Billing queries scan one month at a time |
| `invoices` | By billing period | Invoice queries are always scoped to a period |
| `ledger_entries` | By created_at (monthly) | Financial queries are period-scoped |
| `billing_audit_log` | By created_at (monthly) | Audit queries are time-bounded |

For tables that grow indefinitely (raw events, audit logs), automated partition management is essential. Create partitions in advance (next 3 months) and archive old partitions to cheaper storage.

---

## Temporal Workflows for Billing

### Why Temporal for Billing

Billing pipelines have characteristics that make them a natural fit for Temporal:

| Billing Characteristic | Temporal Feature |
|-----------------------|-----------------|
| Multi-step processes with failures | Automatic activity retries with configurable policies |
| Long-running operations (dunning spans weeks) | Durable timers that survive restarts |
| Exactly-once payment processing | Activity idempotency via Temporal's dedup mechanism |
| Compensating actions (void invoice, refund) | Saga pattern with explicit compensation logic |
| Audit trail requirements | Complete event history for every workflow |
| Parallel processing (billing run) | Child workflows and concurrent activity execution |

### Invoice Generation Workflow with Compensation

```go
func InvoiceGenerationWorkflow(ctx workflow.Context, customerID string, period DateRange) error {
    var invoice Invoice
    var stripeInvoiceID string

    // Step 1: Aggregate usage
    var usage AggregatedUsage
    if err := workflow.ExecuteActivity(ctx, AggregateUsageActivity, customerID, period).Get(ctx, &usage); err != nil {
        return fmt.Errorf("usage aggregation failed: %w", err)
    }

    // Step 2: Rate usage
    var lineItems []InvoiceLineItem
    if err := workflow.ExecuteActivity(ctx, RateUsageActivity, customerID, usage).Get(ctx, &lineItems); err != nil {
        return fmt.Errorf("rating failed: %w", err)
    }

    // Step 3: Create internal invoice
    if err := workflow.ExecuteActivity(ctx, CreateInvoiceActivity, customerID, period, lineItems).Get(ctx, &invoice); err != nil {
        return fmt.Errorf("invoice creation failed: %w", err)
    }

    // Step 4: Apply credits
    if err := workflow.ExecuteActivity(ctx, ApplyCreditsActivity, invoice.ID).Get(ctx, &invoice); err != nil {
        // Compensation: void the internal invoice
        workflow.ExecuteActivity(ctx, VoidInvoiceActivity, invoice.ID).Get(ctx, nil)
        return fmt.Errorf("credit application failed: %w", err)
    }

    // Step 5: Calculate tax
    if err := workflow.ExecuteActivity(ctx, CalculateTaxActivity, invoice.ID).Get(ctx, &invoice); err != nil {
        workflow.ExecuteActivity(ctx, VoidInvoiceActivity, invoice.ID).Get(ctx, nil)
        return fmt.Errorf("tax calculation failed: %w", err)
    }

    // Step 6: Create Stripe invoice
    if err := workflow.ExecuteActivity(ctx, CreateStripeInvoiceActivity, invoice).Get(ctx, &stripeInvoiceID); err != nil {
        workflow.ExecuteActivity(ctx, VoidInvoiceActivity, invoice.ID).Get(ctx, nil)
        return fmt.Errorf("stripe invoice creation failed: %w", err)
    }

    // Step 7: Finalize
    if err := workflow.ExecuteActivity(ctx, FinalizeInvoiceActivity, invoice.ID, stripeInvoiceID).Get(ctx, nil); err != nil {
        // Stripe invoice exists but internal invoice is not finalized.
        // Do NOT void the Stripe invoice automatically -- manual intervention needed.
        workflow.ExecuteActivity(ctx, AlertBillingTeamActivity, invoice.ID, "finalization_failed").Get(ctx, nil)
        return fmt.Errorf("finalization failed: %w", err)
    }

    return nil
}
```

**Compensation design decisions:**
- If credit application or tax calculation fails, void the internal invoice and retry the whole workflow. These are early failures with no external side effects.
- If Stripe invoice creation fails, void the internal invoice. The Stripe call is idempotent (using an idempotency key based on the invoice ID), so retrying the workflow will produce the same Stripe invoice.
- If finalization fails after Stripe invoice creation, alert the billing team. There is now external state (Stripe invoice) that cannot be easily rolled back. Manual intervention is safer than automated voiding of a Stripe invoice.

### Metering Pipeline with Exactly-Once Guarantees

```go
func MeteringPipelineWorkflow(ctx workflow.Context, batchID string) error {
    // Step 1: Read batch of events from Kafka
    var events []MeteringEvent
    if err := workflow.ExecuteActivity(ctx, ReadEventBatchActivity, batchID).Get(ctx, &events); err != nil {
        return err
    }

    // Step 2: Validate and enrich
    var validEvents []MeteringEvent
    var invalidEvents []MeteringEvent
    if err := workflow.ExecuteActivity(ctx, ValidateEventsActivity, events).Get(ctx, &validEvents); err != nil {
        return err
    }

    // Step 3: Route invalid events to DLQ
    if len(invalidEvents) > 0 {
        workflow.ExecuteActivity(ctx, RouteToDLQActivity, invalidEvents).Get(ctx, nil)
    }

    // Step 4: Deduplicate
    var dedupedEvents []MeteringEvent
    if err := workflow.ExecuteActivity(ctx, DeduplicateEventsActivity, validEvents).Get(ctx, &dedupedEvents); err != nil {
        return err
    }

    // Step 5: Write to raw event store (S3) and staging table
    if err := workflow.ExecuteActivity(ctx, PersistEventsActivity, dedupedEvents).Get(ctx, nil); err != nil {
        return err
    }

    // Step 6: Commit Kafka offset
    return workflow.ExecuteActivity(ctx, CommitKafkaOffsetActivity, batchID).Get(ctx, nil)
}
```

**Why Temporal adds value here:** The metering pipeline processes events in micro-batches. Each batch is a workflow. If any step fails, the workflow retries from the failed step, not from the beginning. The Kafka offset is committed only after all processing succeeds, ensuring no events are lost. The dedup step ensures no events are double-counted even if the workflow is retried.

### Subscription Lifecycle Workflow -- Complete Version

```go
func FullSubscriptionLifecycleWorkflow(ctx workflow.Context, customerID string) error {
    logger := workflow.GetLogger(ctx)

    // Phase 1: Trial
    logger.Info("Starting trial", "customer", customerID)
    if err := workflow.ExecuteActivity(ctx, StartTrialActivity, customerID).Get(ctx, nil); err != nil {
        return err
    }

    // Wait for conversion or trial expiry
    trialCtx, trialCancel := workflow.WithCancel(ctx)
    defer trialCancel()

    convertCh := workflow.GetSignalChannel(ctx, "convert")
    timerFuture := workflow.NewTimer(trialCtx, 14*24*time.Hour)

    converted := false
    var planID string

    selector := workflow.NewSelector(ctx)
    selector.AddReceive(convertCh, func(c workflow.ReceiveChannel, more bool) {
        c.Receive(ctx, &planID)
        converted = true
        trialCancel() // Cancel trial timer
    })
    selector.AddFuture(timerFuture, func(f workflow.Future) {
        // Trial expired
    })
    selector.Select(ctx)

    if !converted {
        logger.Info("Trial expired without conversion", "customer", customerID)
        return workflow.ExecuteActivity(ctx, ExpireTrialActivity, customerID).Get(ctx, nil)
    }

    // Phase 2: Active subscription
    logger.Info("Converting to paid", "customer", customerID, "plan", planID)
    if err := workflow.ExecuteActivity(ctx, CreateSubscriptionActivity, customerID, planID).Get(ctx, nil); err != nil {
        return err
    }

    // Billing loop
    cancelCh := workflow.GetSignalChannel(ctx, "cancel")
    planChangeCh := workflow.GetSignalChannel(ctx, "change-plan")

    for {
        // Wait for billing period (simplified to 30 days)
        sleepCtx, sleepCancel := workflow.WithCancel(ctx)

        selector := workflow.NewSelector(ctx)

        // Check for cancellation during billing period
        selector.AddReceive(cancelCh, func(c workflow.ReceiveChannel, more bool) {
            var reason string
            c.Receive(ctx, &reason)
            sleepCancel()
            workflow.ExecuteActivity(ctx, ProcessCancellationActivity, customerID, reason).Get(ctx, nil)
        })

        // Check for plan change during billing period
        selector.AddReceive(planChangeCh, func(c workflow.ReceiveChannel, more bool) {
            var newPlanID string
            c.Receive(ctx, &newPlanID)
            workflow.ExecuteActivity(ctx, ProcessPlanChangeActivity, customerID, planID, newPlanID).Get(ctx, nil)
            planID = newPlanID
        })

        // Wait for billing period to end
        sleepFuture := workflow.NewTimer(sleepCtx, 30*24*time.Hour)
        selector.AddFuture(sleepFuture, func(f workflow.Future) {
            // Billing period ended normally
        })

        selector.Select(ctx)

        // Check if cancelled
        if sleepCtx.Err() != nil {
            // Cancellation was processed
            return nil
        }

        // Generate and collect invoice
        var invoice Invoice
        if err := workflow.ExecuteActivity(ctx, GenerateInvoiceActivity, customerID).Get(ctx, &invoice); err != nil {
            return err
        }

        var paymentResult PaymentResult
        if err := workflow.ExecuteActivity(ctx, CollectPaymentActivity, invoice.ID).Get(ctx, &paymentResult); err != nil {
            // Payment failed -- start dunning as a child workflow
            dunningCtx := workflow.WithChildOptions(ctx, workflow.ChildWorkflowOptions{
                WorkflowID: fmt.Sprintf("dunning-%s-%s", customerID, invoice.ID),
            })
            if err := workflow.ExecuteChildWorkflow(dunningCtx, DunningWorkflow, invoice.ID, customerID).Get(ctx, nil); err != nil {
                // Dunning exhausted -- suspend and exit
                workflow.ExecuteActivity(ctx, SuspendAccountActivity, customerID).Get(ctx, nil)
                return nil
            }
        }
    }
}
```

This workflow models the entire customer lifecycle: trial, conversion, billing, plan changes, cancellation, and payment failure handling. Each of these would be a separate cron job, state machine, or database polling loop in a non-Temporal system. In Temporal, it is a single, readable, debuggable workflow.
