# Module 04: Billing & Metering Systems

> This is the core domain for the role. The billing/metering team owns the full revenue lifecycle:
> metering, billing, customer onboarding/offboarding, marketplace integrations, and revenue operations.
> Know this material cold.

---

## Table of Contents

1. [The Billing Pipeline](#the-billing-pipeline)
2. [Metering Pipeline Design](#metering-pipeline-design)
3. [Aggregation Strategies](#aggregation-strategies)
4. [Rating and Pricing Engine](#rating-and-pricing-engine)
5. [Invoice Generation](#invoice-generation)
6. [Payment Processing and Stripe Integration](#payment-processing-and-stripe-integration)
7. [Stripe Integration Patterns](#stripe-integration-patterns)
8. [Metronome](#metronome)
9. [Cloud Marketplace Integrations](#cloud-marketplace-integrations)
10. [Data Integrity and Correctness](#data-integrity-and-correctness)
11. [Customer Lifecycle](#customer-lifecycle)
12. [Billing System Components](#billing-system-components)
13. [Temporal-Specific Context](#temporal-specific-context)
14. [Common Interview Questions](#common-interview-questions)

---

## The Billing Pipeline

Every usage-based billing system follows this pipeline. Each stage has distinct failure modes, consistency requirements, and scaling characteristics.

```
 Raw Events      Metering       Aggregation      Rating        Invoicing      Payment
 ──────────► ──────────────► ──────────────► ────────────► ─────────────► ──────────────►
  "action      Deduplicate,    Roll up into    Apply pricing   Generate       Charge via
  consumed"    validate,       billable units  rules (tiers,   invoice with   Stripe, handle
               enrich          (hourly/daily)  committed use,  line items,    failures,
                                               overages)       credits, tax   retry, dunning
```

**Why this order matters:** Each stage transforms the data's granularity and meaning. Raw events are high-volume, low-value individually. By the time you reach invoicing, you are dealing with a small number of high-value financial records. The data integrity requirements increase at each stage.

| Stage | Volume | Latency Tolerance | Correctness Requirement |
|-------|--------|-------------------|------------------------|
| Metering | Millions/day | Seconds to minutes | At-least-once, dedup downstream |
| Aggregation | Thousands/day | Minutes to hours | Exactly-once after dedup |
| Rating | Hundreds/day | Hours | Must match contract terms exactly |
| Invoicing | Tens/day | End of billing period | Auditable, immutable once finalized |
| Payment | Tens/day | Days (retry window) | Must reconcile to invoice |

---

## Metering Pipeline Design

Metering is the foundation. If you meter wrong, everything downstream is wrong. The metering pipeline collects raw usage events from the product and makes them available for billing.

### What to Capture

Every metering event needs enough context to be billable, auditable, and debuggable.

```json
{
  "event_id": "evt_a1b2c3d4e5f6",
  "idempotency_key": "ns-prod-wf-exec-abc123-2026-02-22T10:30:00Z",
  "event_type": "action.consumed",
  "timestamp": "2026-02-22T10:30:00.123Z",
  "customer_id": "cust_temporal_acme",
  "namespace_id": "ns-prod",
  "properties": {
    "action_type": "workflow_execution_started",
    "workflow_type": "payment-processing",
    "task_queue": "main",
    "region": "us-east-1"
  },
  "quantity": 1
}
```

**Key fields and why each matters:**

- **event_id**: Globally unique. Used for deduplication and audit trails.
- **idempotency_key**: Deterministic identifier derived from the event's natural key. If the same event is emitted twice (retry, at-least-once delivery), the idempotency key ensures it is counted once.
- **event_type**: The billable action. For Temporal, this maps to their actions-based pricing model (workflow executions, activities, signals, queries, etc.).
- **timestamp**: When the event occurred in the source system, not when it was received. Critical for assigning events to the correct billing period.
- **customer_id**: Maps to the billing entity. In Temporal Cloud, this is the account/organization.
- **namespace_id**: Temporal's unit of isolation. Customers can have multiple namespaces, and usage must be attributable per namespace for visibility (even if billing is per account).
- **properties**: Metadata for enrichment, debugging, and future pricing dimensions. Capture more than you think you need -- you can always ignore fields, but you cannot retroactively add them.
- **quantity**: Usually 1 for discrete events. Can be > 1 for batch events.

### Deduplication

Usage-based billing has a fundamental tension: the event source delivers at-least-once (for reliability), but billing must count exactly-once (for correctness).

**Strategies:**

1. **Idempotency key at ingestion:** Hash the natural key of the event (namespace + action + workflow_id + timestamp). Store seen keys in a dedup cache (Redis with TTL, or a Bloom filter for approximate dedup). Reject duplicates at the front door.

2. **Dedup at aggregation:** Accept all events, then deduplicate during aggregation using `SELECT DISTINCT` on the idempotency key. Simpler ingestion, but requires storing all raw events including duplicates.

3. **Hybrid:** Approximate dedup at ingestion (Bloom filter -- fast, small memory footprint, allows rare false positives), exact dedup at aggregation (database-level distinct). This is the common production pattern.

```
Event Source ──► Ingestion API ──► Bloom Filter (approximate dedup)
                                       │
                              ┌────────┴────────┐
                              │ Pass             │ Likely duplicate
                              ▼                  ▼
                        Raw Event Store      Drop (log for monitoring)
                              │
                              ▼
                     Aggregation Job ──► Exact dedup (idempotency_key DISTINCT)
```

**Dedup window:** How long do you need to remember seen events? For billing, the dedup window must cover at least the billing period plus a buffer for late-arriving events. A 35-day window (one month plus 5 days of grace) is common for monthly billing.

### Event Collection Architecture

```
Product Services                  Metering Pipeline
┌─────────────┐
│ Temporal     │
│ Frontend     ├──► Kafka Topic ──► Metering Consumer ──► Raw Event Store (S3/Kinesis)
│ Service      │    (buffered,       (validates,            │
└─────────────┘     partitioned      enriches,              ▼
                    by customer)     deduplicates)     Aggregation Job
┌─────────────┐                                        (hourly/daily)
│ Temporal     │                                            │
│ History      ├──► Kafka Topic ──►                         ▼
│ Service      │                                    Aggregated Store
└─────────────┘                                    (PostgreSQL/Redshift)
```

**Why Kafka (or Kinesis)?**
- Durability: events survive consumer failures.
- Ordering: partition by customer_id for per-customer ordering guarantees.
- Replay: if the metering consumer has a bug, you can replay the topic from an offset.
- Backpressure: Kafka absorbs spikes without dropping events.

**Why S3 for raw events?**
- Cheap, durable, append-only storage.
- Raw events are the source of truth for reconciliation. Never delete them.
- Queryable with Athena/Presto for ad-hoc investigation.
- Lifecycle policies for cost management (move to Glacier after 1 year).

### Pipeline Reliability

The metering pipeline must be reliable enough that finance trusts the numbers. This means:

1. **No silent data loss.** Every event must either be counted or explicitly routed to a dead letter queue (DLQ) with alerting.

2. **Exactly-once semantics (effective).** True exactly-once is hard in distributed systems. The practical approach is at-least-once delivery with idempotent processing. Kafka consumers commit offsets after successful processing. If a consumer crashes, it replays from the last committed offset. The dedup layer handles the resulting duplicates.

3. **Dead letter queues.** Events that fail validation (bad schema, unknown customer, missing required fields) go to a DLQ, not `/dev/null`. The DLQ is monitored. Operators can fix and replay events from the DLQ.

4. **Reconciliation.** Periodically compare:
   - Count of raw events in S3 vs. count of events in the aggregated store.
   - Aggregated totals vs. what was invoiced.
   - What was invoiced vs. what was collected.
   Any discrepancy triggers an alert. Reconciliation is not optional -- it is the safety net for every other guarantee.

5. **Late-arriving events.** An event with a timestamp of February 15 might arrive on February 20 (network partition, delayed batch, timezone bugs). The aggregation layer must handle this by either:
   - Re-aggregating the affected time window (simpler, but expensive at scale).
   - Maintaining a correction ledger that adjusts previously computed aggregations.

---

## Aggregation Strategies

Raw metering events are too granular for billing. You need to roll them up into billable units.

### Pre-Aggregation vs On-Demand

| Approach | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Pre-aggregation** | Scheduled jobs (hourly/daily) compute totals and store them | Fast billing runs, predictable cost | Late events require re-aggregation, storage of intermediate state |
| **On-demand** | Query raw events at billing time | Always current, handles late events naturally | Slow for large datasets, expensive at scale |
| **Hybrid** | Pre-aggregate with a known cutoff, then supplement with on-demand for recent/late events | Best of both worlds | More complex, two code paths |

**For a system like Temporal Cloud at scale, pre-aggregation with correction is the right choice.** Billing runs must complete in minutes, not hours. You cannot scan billions of raw events every time you generate an invoice.

### Time Windows and Bucketing

```
Raw Events:    [e1, e2, e3, e4, e5, e6, e7, e8, e9, ...]
                 |    |    |    |    |    |    |    |
Hourly Buckets: [  Hour 1: 3  ] [  Hour 2: 2  ] [  Hour 3: 4  ]
                       |                |                |
Daily Buckets:  [           Day 1: 9                        ]
                              |
Monthly Buckets:[                    Feb 2026: 270                    ]
```

**Bucketing decisions:**

- **Hourly** aggregation for real-time usage dashboards (customers want to see current usage).
- **Daily** aggregation for internal reporting and anomaly detection.
- **Monthly** aggregation (or per billing period) for invoice generation.

Each level is derived from the level below it. Hourly aggregations roll up into daily, daily into monthly. This creates a materialized hierarchy that is fast to query at any granularity.

### Handling Late-Arriving Events

Late events are inevitable. The question is how late and how many.

**Option 1: Re-aggregate the affected bucket.**
If an event for February 15 arrives on February 20, re-run the daily aggregation for February 15. Simple, correct, but expensive if it happens frequently.

**Option 2: Correction entries.**
Append a correction to the aggregated table:

```sql
-- Original aggregation
INSERT INTO daily_usage (customer_id, date, action_type, quantity)
VALUES ('cust_acme', '2026-02-15', 'workflow_start', 1420);

-- Late event correction
INSERT INTO daily_usage (customer_id, date, action_type, quantity, is_correction)
VALUES ('cust_acme', '2026-02-15', 'workflow_start', 3, true);

-- Billing query sums both: 1420 + 3 = 1423
```

**Option 3: Grace period before finalization.**
Do not finalize aggregations until a grace period has elapsed. For example, hourly aggregations become "final" after 4 hours. Late events within the grace period are absorbed naturally.

### Storage for Aggregated Data

| Store | Use Case | Why |
|-------|----------|-----|
| PostgreSQL | Billing-critical aggregations, invoice data | ACID transactions, strong consistency, mature tooling |
| Redshift / BigQuery | Analytics, historical trend analysis | Columnar storage, fast aggregation over large datasets |
| Redis | Real-time usage counters, rate limiting | Sub-millisecond reads for customer-facing dashboards |

The aggregated data in PostgreSQL is the source of truth for billing. Redshift is for analytics. Redis is for real-time display. They may temporarily disagree (eventual consistency), but PostgreSQL is authoritative.

---

## Rating and Pricing Engine

Rating is the process of applying pricing rules to aggregated usage. This is where business logic meets engineering, and it is surprisingly complex.

### Pricing Models

Temporal Cloud uses actions-based pricing. An "action" is a billable unit of work (workflow execution start, activity execution, signal, query, etc.). But the pricing engine must support multiple models because enterprise deals are bespoke.

| Model | Description | Example | Complexity |
|-------|------------|---------|------------|
| **Per-unit** | Fixed price per action | $0.00001 per action | Low |
| **Tiered** | Price decreases at volume thresholds | First 1M actions at $25, next 9M at $20 per million | Medium |
| **Volume** | All units priced at the tier reached | 10M actions = all at $20 per million (not just the last 9M) | Medium |
| **Committed use** | Prepaid commitment with a discount, overages at a higher rate | Commit to 100M actions/month at $15/M, overage at $25/M | High |
| **Free tier** | First N units free, then paid | First 1M actions free per month | Low |
| **Hybrid** | Combination of the above with a base platform fee | $200/month base + tiered per-action pricing | High |

### Pricing Engine Design

The pricing engine takes aggregated usage and a pricing plan, and produces rated line items.

```go
type PricingPlan struct {
    PlanID      string
    BaseFee     Money           // Fixed monthly fee
    Tiers       []PricingTier   // Ordered by threshold
    Commitment  *Commitment     // Optional committed use
    FreeTier    *FreeTier       // Optional free allocation
}

type PricingTier struct {
    UpToQuantity  int64   // -1 for unlimited (final tier)
    UnitPrice     Money   // Price per unit in this tier
}

type Commitment struct {
    CommittedQuantity int64
    CommittedPrice    Money   // Total price for committed quantity
    OverageUnitPrice  Money   // Per-unit price above commitment
}

type RatedLineItem struct {
    Description string
    Quantity    int64
    UnitPrice   Money
    Amount      Money  // Quantity * UnitPrice (or complex calculation for tiers)
    TierLabel   string // "Tier 1: 0 - 1,000,000 actions"
}
```

**Tiered pricing calculation example:**

```
Plan: Tier 1 (0 - 1M): $25/M, Tier 2 (1M - 10M): $20/M, Tier 3 (10M+): $15/M
Usage: 15,000,000 actions

Line items:
  Tier 1:  1,000,000 actions x $0.000025 = $25.00
  Tier 2:  9,000,000 actions x $0.000020 = $180.00
  Tier 3:  5,000,000 actions x $0.000015 = $75.00
  ─────────────────────────────────────────────────
  Total: $280.00
```

**Key design decisions:**

1. **Pricing plans are versioned and immutable.** When a plan changes, create a new version. Existing customers stay on their plan version until explicitly migrated. Never mutate a plan that has been used for billing.

2. **The rating engine is deterministic.** Given the same usage data and the same plan, it must produce the exact same output every time. No side effects, no external dependencies during calculation. This makes it testable and auditable.

3. **Effective dates on everything.** A customer might change plans mid-cycle. The rating engine must apply the correct plan for each portion of the billing period.

### Plan Management

```
Plan Lifecycle:
  Draft ──► Active ──► Deprecated ──► Archived
              │
              ├── Customers subscribe
              │
              ▼
          Version 2 (Active)
              │
              ├── New customers get v2
              │   Existing customers stay on v1 until migrated
              │
              ▼
          Version 3 ...
```

Plan changes for existing customers:

- **Upgrade (higher tier/more features):** Effective immediately or at next billing period. Prorated charges for the current period.
- **Downgrade:** Typically effective at next billing period to avoid negative proration complexity.
- **Custom enterprise plan:** Sales-negotiated terms stored as a custom plan version for a single customer.

---

## Invoice Generation

Invoicing is where rated usage becomes a financial document. Invoices are legal documents -- they must be accurate, auditable, and immutable once finalized.

### Invoice Lifecycle

```
Draft ──► Calculated ──► Reviewed ──► Finalized ──► Sent ──► Paid
  │                         │                         │         │
  │ (can be modified)       │ (manual review          │         │
  │                         │  for large accounts)    │         │
  ▼                         ▼                         ▼         ▼
Voided (if errors found before payment)         Credit Note (if errors found after payment)
```

**States:**

- **Draft:** Created at the start of the billing period. Usage accumulates.
- **Calculated:** Rating engine has been run. Line items are populated.
- **Reviewed:** For high-value invoices, a human reviews before sending.
- **Finalized:** Locked. No more changes. This is the invoice of record.
- **Sent:** Delivered to the customer (email, portal, Stripe).
- **Paid:** Payment collected.
- **Voided:** Canceled before payment (rare -- only for errors).
- **Credit Note:** Issued after payment to correct an error. Never modify a finalized invoice -- issue a credit note instead.

### Invoice Data Model

```sql
CREATE TABLE invoices (
    invoice_id       UUID PRIMARY KEY,
    customer_id      UUID NOT NULL REFERENCES customers(id),
    billing_period   DATERANGE NOT NULL,
    status           TEXT NOT NULL CHECK (status IN (
        'draft', 'calculated', 'reviewed', 'finalized', 'sent', 'paid', 'voided'
    )),
    subtotal_cents   BIGINT NOT NULL DEFAULT 0,
    tax_cents        BIGINT NOT NULL DEFAULT 0,
    credits_cents    BIGINT NOT NULL DEFAULT 0,
    total_cents      BIGINT NOT NULL DEFAULT 0,
    currency         TEXT NOT NULL DEFAULT 'USD',
    stripe_invoice_id TEXT,
    finalized_at     TIMESTAMPTZ,
    paid_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE invoice_line_items (
    line_item_id   UUID PRIMARY KEY,
    invoice_id     UUID NOT NULL REFERENCES invoices(id),
    description    TEXT NOT NULL,
    quantity       BIGINT NOT NULL,
    unit_price_cents BIGINT NOT NULL,
    amount_cents   BIGINT NOT NULL,
    action_type    TEXT,
    tier_label     TEXT,
    sort_order     INTEGER NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE credits (
    credit_id     UUID PRIMARY KEY,
    customer_id   UUID NOT NULL REFERENCES customers(id),
    amount_cents  BIGINT NOT NULL,
    reason        TEXT NOT NULL,
    applied_to    UUID REFERENCES invoices(id),
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by    TEXT NOT NULL  -- audit: who issued this credit
);
```

**Notice: all monetary values are `BIGINT` in cents (or the smallest currency unit).** Never use `FLOAT` or `DOUBLE` for money. Floating-point arithmetic produces rounding errors that compound over millions of transactions. `$0.1 + $0.2 != $0.3` in IEEE 754. Use integer cents or a fixed-point decimal type (`NUMERIC(19,4)` in PostgreSQL).

### Billing Period Edge Cases

- **Customer signs up mid-month:** First invoice covers a partial period. Prorate the base fee. Usage charges are naturally prorated (they only accrue while the account is active).
- **Customer cancels mid-month:** Final invoice covers usage through the cancellation date. Prorate the base fee. No refund for unused committed capacity (or refund it, depending on contract terms -- this is a business decision that the system must support either way).
- **Timezone handling:** Billing periods should be defined in UTC. Customers in UTC-12 to UTC+14 see slightly different "month" boundaries than they expect. Document this clearly.
- **Leap years, DST:** Billing periods are calendar-based, not fixed-duration. February has 28 or 29 days. A "monthly" billing period is not exactly 30 days.

---

## Payment Processing and Stripe Integration

### Stripe as the Payment Layer

Stripe is the standard payment processor for SaaS companies. Temporal uses Stripe for direct billing (alongside marketplace billing for AWS/GCP/Azure customers).

**Core Stripe objects for billing:**

```
Customer ──► Subscription ──► Invoice ──► Payment Intent ──► Charge
    │              │              │              │
    │              │              │              └── Represents the actual
    │              │              │                  attempt to collect money
    │              │              │
    │              │              └── The bill (line items, totals, tax)
    │              │
    │              └── Recurring billing relationship
    │                  (plan, billing cycle, metered usage)
    │
    └── The billing entity
        (payment methods, address, tax ID)
```

### Usage Records for Metered Billing

Stripe supports metered billing natively. You report usage, and Stripe includes it on the next invoice.

```
POST /v1/subscription_items/{id}/usage_records
{
  "quantity": 1500000,
  "timestamp": 1708646400,
  "action": "set"  // or "increment"
}
```

**Two approaches:**

1. **Report usage to Stripe directly.** Let Stripe calculate the bill. Simpler, but you are limited to Stripe's pricing models and lose control over the rating logic.

2. **Calculate the bill yourself, create invoice items in Stripe.** You own the rating logic. Stripe is just the payment collection layer. More complex, but supports arbitrary pricing models and gives you full control.

For a sophisticated billing system (like Temporal's, with committed use discounts, custom enterprise pricing, and marketplace billing), option 2 is the right choice. Stripe is the payment rail, not the billing brain.

### Stripe Webhook Handling

Stripe communicates asynchronously via webhooks. Your system must handle these reliably.

**Critical webhook events:**

| Event | What Happened | Your Response |
|-------|--------------|---------------|
| `invoice.paid` | Payment successful | Mark invoice as paid, update customer status |
| `invoice.payment_failed` | Payment attempt failed | Start dunning process, notify customer |
| `customer.subscription.updated` | Plan change | Sync subscription state |
| `customer.subscription.deleted` | Cancellation | Start offboarding flow |
| `payment_intent.succeeded` | One-time payment collected | Record payment |
| `charge.dispute.created` | Customer disputed a charge | Alert team, freeze account if needed |

**Webhook reliability patterns:**

1. **Signature verification.** Every webhook request includes a `Stripe-Signature` header. Verify it using your webhook signing secret. This prevents forged webhook calls.

```go
func handleWebhook(w http.ResponseWriter, r *http.Request) {
    payload, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Bad request", http.StatusBadRequest)
        return
    }

    event, err := webhook.ConstructEvent(
        payload,
        r.Header.Get("Stripe-Signature"),
        webhookSigningSecret,
    )
    if err != nil {
        http.Error(w, "Invalid signature", http.StatusUnauthorized)
        return
    }

    // Process event idempotently
    if err := processEvent(event); err != nil {
        // Return 500 so Stripe retries
        http.Error(w, "Processing failed", http.StatusInternalServerError)
        return
    }

    w.WriteHeader(http.StatusOK)
}
```

2. **Idempotent processing.** Stripe may deliver the same webhook multiple times (at-least-once delivery). Store the `event.ID` in a processed-events table and skip duplicates.

```go
func processEvent(event stripe.Event) error {
    // Check if already processed
    exists, err := db.WebhookEventExists(event.ID)
    if err != nil {
        return err
    }
    if exists {
        log.Info("Duplicate webhook, skipping", "event_id", event.ID)
        return nil
    }

    // Process the event
    if err := handleEventByType(event); err != nil {
        return err
    }

    // Mark as processed
    return db.RecordWebhookEvent(event.ID, event.Type)
}
```

3. **Event ordering.** Stripe does not guarantee webhook ordering. You might receive `invoice.paid` before `invoice.created`. Design your handlers to be order-independent, or use the `created` timestamp on the event object to detect out-of-order delivery.

4. **Stripe's eventual consistency.** After creating an object in Stripe (e.g., a subscription), it might take seconds to propagate. If you create a subscription and immediately query for it, you might get a 404. Use the response from the creation call directly rather than re-fetching.

### Payment Failure Handling

Payment failures are not exceptional -- they are routine. About 5-10% of subscription charges fail on the first attempt. Most are recoverable.

**Common failure reasons:**

| Reason | Recovery Strategy |
|--------|------------------|
| Insufficient funds | Retry in 3-5 days |
| Card expired | Notify customer to update payment method |
| Card declined (generic) | Retry with exponential backoff |
| Fraud detected | Do not retry. Notify customer. |
| Authentication required (SCA/3DS) | Send customer a payment link for authentication |

**Retry schedule (dunning):**

```
Day 0:  Payment fails. Send email notification.
Day 3:  First retry. If fails, send warning email.
Day 7:  Second retry. If fails, send urgent email.
Day 14: Third retry. If fails, degrade service (read-only mode).
Day 21: Final retry. If fails, suspend account.
Day 30: Send final notice. Begin offboarding.
```

This is configurable per customer segment. Enterprise customers get longer grace periods and direct account manager outreach rather than automated emails.

---

## Stripe Integration Patterns

### Customer Creation and Syncing

Every customer in your system has a corresponding Stripe customer. Keep them in sync.

```go
// Create customer in your system and in Stripe
func CreateCustomer(ctx context.Context, req CreateCustomerRequest) (*Customer, error) {
    // Create in Stripe first
    stripeCustomer, err := stripe.Customers.New(&stripe.CustomerParams{
        Email:       stripe.String(req.Email),
        Name:        stripe.String(req.CompanyName),
        Description: stripe.String(req.Description),
        Metadata: map[string]string{
            "internal_customer_id": req.InternalID,
        },
    })
    if err != nil {
        return nil, fmt.Errorf("stripe customer creation failed: %w", err)
    }

    // Create in your database with the Stripe ID
    customer := &Customer{
        ID:               req.InternalID,
        StripeCustomerID: stripeCustomer.ID,
        Email:            req.Email,
        CompanyName:      req.CompanyName,
        Status:           "active",
    }

    if err := db.InsertCustomer(ctx, customer); err != nil {
        // Stripe customer was created but DB insert failed.
        // Options: (a) delete the Stripe customer, (b) reconcile later.
        // Option (b) is safer -- Stripe customer without a DB record is harmless.
        log.Error("DB insert failed after Stripe creation", "stripe_id", stripeCustomer.ID, "err", err)
        return nil, err
    }

    return customer, nil
}
```

**The consistency problem:** Creating a customer involves two writes (Stripe + your database). There is no distributed transaction. If the second write fails, you have a Stripe customer with no corresponding local record. Handle this with:

- A reconciliation job that scans for orphaned Stripe objects.
- Storing the Stripe ID as metadata so you can match them later.
- Designing operations to be idempotent so retries are safe.

### Subscription Management

```go
// Create a metered subscription
func CreateSubscription(ctx context.Context, customerID string, planID string) (*Subscription, error) {
    customer, err := db.GetCustomer(ctx, customerID)
    if err != nil {
        return nil, err
    }

    plan, err := db.GetPlan(ctx, planID)
    if err != nil {
        return nil, err
    }

    sub, err := stripe.Subscriptions.New(&stripe.SubscriptionParams{
        Customer: stripe.String(customer.StripeCustomerID),
        Items: []*stripe.SubscriptionItemsParams{
            {
                Price: stripe.String(plan.StripePriceID),
            },
        },
        // For metered billing, don't charge upfront
        PaymentBehavior: stripe.String("default_incomplete"),
    })
    if err != nil {
        return nil, fmt.Errorf("stripe subscription creation failed: %w", err)
    }

    // Store subscription locally
    return db.CreateSubscription(ctx, customer.ID, sub.ID, plan.ID)
}
```

### Reporting Usage to Stripe

If using Stripe for metered billing (as opposed to generating invoices yourself):

```go
// Report aggregated usage to Stripe at end of billing period
func ReportUsageToStripe(ctx context.Context, customerID string, billingPeriod time.Time) error {
    usage, err := db.GetAggregatedUsage(ctx, customerID, billingPeriod)
    if err != nil {
        return err
    }

    sub, err := db.GetActiveSubscription(ctx, customerID)
    if err != nil {
        return err
    }

    _, err = stripe.UsageRecords.New(&stripe.UsageRecordParams{
        SubscriptionItem: stripe.String(sub.StripeSubscriptionItemID),
        Quantity:         stripe.Int64(usage.TotalActions),
        Timestamp:        stripe.Int64(billingPeriod.Unix()),
        Action:           stripe.String("set"), // "set" replaces; "increment" adds
    })
    if err != nil {
        return fmt.Errorf("stripe usage report failed: %w", err)
    }

    return db.MarkUsageReported(ctx, customerID, billingPeriod)
}
```

**"set" vs "increment":** Use "set" for reporting final aggregated totals (idempotent -- safe to retry). Use "increment" for streaming updates (not idempotent -- duplicates cause overcounting). For billing accuracy, "set" with final aggregates is strongly preferred.

---

## Metronome

### What Metronome Does

Metronome is a usage-based billing infrastructure platform. It sits between your metering pipeline and your payment processor (Stripe), handling the hard parts of usage-based billing: event ingestion, aggregation, rating, and invoice generation.

### Why Use Metronome + Stripe Together

```
Your Product ──► Metronome (metering, rating, invoicing) ──► Stripe (payment collection)
```

- **Metronome** handles: event ingestion, deduplication, aggregation, pricing engine, invoice calculation, usage dashboards, prepaid credit management.
- **Stripe** handles: payment collection, payment method management, refunds, disputes, tax filing.

**Why not just Stripe?** Stripe's native metered billing is limited. It supports simple per-unit pricing but not complex tiered pricing, committed use discounts, prepaid credits, or custom enterprise pricing models. Metronome fills this gap.

**Why not just Metronome?** Metronome does not process payments. It calculates what is owed and pushes invoices to Stripe for collection.

### How It Likely Fits in Temporal's Stack

Based on Temporal's public information about using Metronome:

```
Temporal Cloud Services
    │
    ▼
Metering Events (actions consumed)
    │
    ▼
Metronome
    ├── Ingests usage events
    ├── Applies pricing plans (per-action, tiered, committed use)
    ├── Generates invoices
    ├── Manages prepaid credits
    └── Pushes invoice to Stripe
            │
            ▼
        Stripe
            ├── Collects payment
            ├── Handles retries/dunning
            └── Manages payment methods
```

The billing/metering team's work likely includes: integrating with Metronome's API, maintaining the metering pipeline that feeds events to Metronome, building customer-facing usage dashboards, handling edge cases that Metronome does not cover (marketplace billing, custom enterprise deals), and reconciling Metronome data against internal metering data.

---

## Cloud Marketplace Integrations

Temporal Cloud is available through AWS Marketplace, GCP Marketplace, and Azure Marketplace. Each marketplace has its own billing integration. Customers who purchase through a marketplace are billed through their existing cloud account rather than directly through Stripe.

### Why Marketplaces Matter

- **Customers want consolidated billing.** A company that spends $1M/month on AWS wants Temporal on the same invoice.
- **Committed cloud spend.** Many companies have committed spend agreements with cloud providers. Purchasing through the marketplace draws down that commitment.
- **Procurement simplification.** Purchasing through an existing vendor relationship avoids new vendor onboarding, legal review, and procurement cycles.

### AWS Marketplace

**Key APIs:**

| API | Purpose |
|-----|---------|
| AWS Marketplace Metering API | Report usage for metered products |
| AWS Marketplace Entitlement API | Check what a customer has purchased |
| SaaS Subscription API | Manage SaaS subscription lifecycle |

**SaaS subscription flow:**

```
1. Customer subscribes in AWS Marketplace Console
2. AWS redirects customer to your registration URL with a token
3. You call ResolveCustomer to get the AWS customer ID
4. You create an account and link it to the AWS customer
5. Periodically, you call BatchMeterUsage to report usage
6. AWS bills the customer on their AWS invoice
7. AWS pays you (minus marketplace fee, typically 3-5%)
```

**Metering API:**

```go
// Report usage to AWS Marketplace
func ReportAWSUsage(ctx context.Context, customerID string, usage UsageRecord) error {
    svc := marketplacemetering.New(session)

    _, err := svc.BatchMeterUsage(&marketplacemetering.BatchMeterUsageInput{
        ProductCode: aws.String("your-product-code"),
        UsageRecords: []*marketplacemetering.UsageRecord{
            {
                CustomerIdentifier: aws.String(usage.AWSCustomerID),
                Dimension:          aws.String("actions"),
                Quantity:           aws.Int64(usage.Quantity),
                Timestamp:          aws.Time(usage.Timestamp),
            },
        },
    })
    return err
}
```

### GCP Marketplace

**Key APIs:**

| API | Purpose |
|-----|---------|
| Procurement API | Manage entitlements and account creation |
| Cloud Commerce Partner Ingestion API | Report usage |
| Partner Portal | Configure listing and pricing |

**Differences from AWS:**
- GCP uses a "procurement" model where entitlements must be explicitly approved.
- Usage reporting uses a different schema and cadence.
- Settlement cycles differ (GCP pays monthly, AWS pays monthly but with different timing).

### Azure Marketplace

**Key APIs:**

| API | Purpose |
|-----|---------|
| SaaS Fulfillment API v2 | Manage SaaS subscription lifecycle |
| Marketplace Metering Service API | Report usage for metered dimensions |
| Partner Center API | Configure listing |

**Differences from AWS and GCP:**
- Azure requires explicit activation of subscriptions via the Fulfillment API.
- Metering dimensions must be predefined in the offer and cannot be added dynamically.
- Azure supports "custom meters" that map to your billing dimensions.

### Marketplace Comparison

| Aspect | AWS | GCP | Azure |
|--------|-----|-----|-------|
| Usage reporting | BatchMeterUsage | Commerce Ingestion API | Metering Service API |
| Subscription model | SaaS Subscription | Procurement Entitlement | SaaS Fulfillment |
| Settlement frequency | Monthly | Monthly | Monthly |
| Marketplace fee | 3-5% | 3% | 3% |
| Free trial support | Yes | Yes | Yes |
| Private offers | Yes (CPPO) | Yes | Yes |
| Metering granularity | Hourly | Hourly | Hourly |
| Entitlement check | Entitlement API | Procurement API | Fulfillment API |

### The Reconciliation Challenge

With marketplace billing, you have multiple sources of truth:

```
Your Metering Pipeline ──► Your Usage Records (ground truth)
         │
         ├──► Metronome/Stripe (direct billing customers)
         │
         ├──► AWS Marketplace Metering API (AWS customers)
         │
         ├──► GCP Procurement API (GCP customers)
         │
         └──► Azure Metering API (Azure customers)
```

**You must reconcile across all of these.** What you reported to AWS must match what your metering pipeline recorded. What AWS charged the customer must match what AWS paid you. The reconciliation job runs monthly and flags discrepancies for investigation.

Common discrepancies:
- Usage report rejected by marketplace API (schema error, timestamp out of range). The usage was real but unreported. Must be reported in the next cycle.
- Marketplace metering API has different dimension limits than your internal schema. A single "action" in your system might map to multiple marketplace dimensions.
- Settlement timing differences between marketplaces create temporary discrepancies in revenue reporting.

---

## Data Integrity and Correctness

Billing systems handle money. The standard for correctness is higher than for most software. A bug in a billing system is not just a poor user experience -- it is a financial misstatement that can have legal and regulatory consequences.

### Money Math

**Rule: Never use floating-point types for monetary values.**

```go
// WRONG: floating-point arithmetic
price := 0.1 + 0.2 // = 0.30000000000000004
total := price * 3  // = 0.9000000000000001

// CORRECT: integer cents
priceCents := int64(10 + 20) // = 30
totalCents := priceCents * 3  // = 90

// CORRECT: decimal type (for languages/DBs that support it)
// PostgreSQL: NUMERIC(19,4)
// Go: shopspring/decimal or cockroachdb/apd
```

**In the database:** Use `BIGINT` for cents or `NUMERIC(19,4)` for decimal amounts. `NUMERIC(19,4)` supports up to 999,999,999,999,999.9999 -- more than enough for any billing scenario.

**In Go:** Use `shopspring/decimal` or `cockroachdb/apd` for arbitrary-precision decimal arithmetic. Never use `float64` for money.

**In APIs:** Transmit monetary values as either integer cents (`"amount_cents": 2999`) or string decimals (`"amount": "29.99"`). Never as floating-point numbers in JSON (the JSON spec does not distinguish floats from integers, and parsers may introduce precision errors).

### Double-Entry Bookkeeping

Every financial transaction affects at least two accounts. This is not just an accounting convention -- it is a data integrity mechanism. If debits and credits do not balance, something is wrong.

```sql
CREATE TABLE ledger_entries (
    entry_id      UUID PRIMARY KEY,
    transaction_id UUID NOT NULL,  -- groups related entries
    account_id    UUID NOT NULL,
    entry_type    TEXT NOT NULL CHECK (entry_type IN ('debit', 'credit')),
    amount_cents  BIGINT NOT NULL CHECK (amount_cents > 0),
    currency      TEXT NOT NULL DEFAULT 'USD',
    description   TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by    TEXT NOT NULL
);

-- Invariant: for every transaction_id, SUM(debits) = SUM(credits)
-- Enforce with a check constraint or a trigger
```

**Example: Customer pays $100 invoice:**

| Entry | Account | Type | Amount |
|-------|---------|------|--------|
| 1 | Accounts Receivable | Credit | $100.00 |
| 2 | Cash (Stripe) | Debit | $100.00 |

The balance sheet stays balanced. If you see a one-sided entry, you have a bug.

### Audit Trails

Every mutation to billing data must be logged with:
- **Who** made the change (user ID, service ID, or "system").
- **When** the change was made (timestamp, not just "updated_at" on the record).
- **What** changed (before and after values, or the full new state).
- **Why** the change was made (reason code, ticket number, or description).

```sql
CREATE TABLE billing_audit_log (
    log_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type  TEXT NOT NULL,    -- 'invoice', 'customer', 'plan', 'credit'
    entity_id    UUID NOT NULL,
    action       TEXT NOT NULL,    -- 'created', 'updated', 'voided', 'finalized'
    actor        TEXT NOT NULL,    -- 'user:jsmith', 'service:billing-engine', 'system:cron'
    changes      JSONB,           -- {"field": {"old": "draft", "new": "finalized"}}
    reason       TEXT,            -- "Monthly billing run" or "Customer requested credit"
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON billing_audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_actor ON billing_audit_log(actor);
CREATE INDEX idx_audit_time ON billing_audit_log(created_at);
```

### Reconciliation

Reconciliation is the process of comparing two or more data sources that should agree and investigating discrepancies.

**Three levels of reconciliation:**

1. **Metering vs Aggregation:** Does the sum of raw events match the aggregated totals? Run daily.
2. **Aggregation vs Invoice:** Does the aggregated usage, when rated, match the invoice amounts? Run per billing cycle.
3. **Invoice vs Payment:** Does the invoice total match what was collected? Run daily.

```
Reconciliation Report (2026-02-22)
──────────────────────────────────
Customer: ACME Corp (cust_acme)
Billing Period: 2026-02-01 to 2026-02-28

  Raw events (S3):          15,234,567 actions
  Aggregated (PostgreSQL):  15,234,567 actions  [OK]
  Invoiced amount:          $280.00
  Expected (re-rated):      $280.00              [OK]
  Stripe payment:           $280.00              [OK]

Customer: Widgets Inc (cust_widgets)
  Raw events (S3):          8,100,234 actions
  Aggregated (PostgreSQL):  8,100,230 actions    [MISMATCH: -4 actions]
  *** Investigation needed: possible dedup issue ***
```

### Idempotency at Every Layer

Every operation in the billing pipeline should be safe to retry:

| Layer | Idempotency Mechanism |
|-------|----------------------|
| Event ingestion | Idempotency key (event_id or derived key) |
| Aggregation | Re-running produces the same result (deterministic) |
| Rating | Pure function: same inputs = same outputs |
| Invoice creation | One invoice per customer per billing period (unique constraint) |
| Payment collection | Stripe idempotency key on API calls |
| Webhook processing | Event ID dedup table |

---

## Customer Lifecycle

### Account States

```
                    ┌──────────────────────────────────────────────┐
                    │                                              │
  Sign Up ──► Trial ──► Active ──► Past Due ──► Suspended ──► Churned
                │                      │              │
                │                      │              └──► Active (payment recovered)
                │                      │
                │                      └──► Active (payment recovered)
                │
                └──► Churned (trial expired without conversion)
```

| State | What It Means | Billing Behavior | Service Access |
|-------|--------------|------------------|----------------|
| Trial | Free evaluation period | No billing | Full access (possibly with limits) |
| Active | Paying customer | Normal billing cycle | Full access |
| Past Due | Payment failed, in dunning | Billing continues, retries in progress | Full access (grace period) |
| Suspended | Multiple payment failures | Billing paused, final notices sent | Read-only or degraded |
| Churned | Customer left or was terminated | No billing, final invoice issued | No access (data retained per policy) |

### Onboarding Flow

```
1. Customer signs up (self-service or sales-assisted)
   └── Create customer record
   └── Create Stripe customer
   └── If marketplace: link marketplace account

2. Trial period (14 days typical for SaaS)
   └── Full product access with usage limits
   └── Metering is active (to show usage during trial)
   └── No billing

3. Trial conversion
   └── Customer adds payment method (Stripe) or already has marketplace billing
   └── Select plan
   └── Create subscription
   └── Begin billing cycle

4. First billing cycle
   └── Usage metered normally
   └── First invoice generated at end of period
   └── Payment collected
```

### Offboarding Flow

```
1. Cancellation request
   └── Record reason (churn analysis)
   └── Set cancellation effective date (end of current billing period)
   └── Continue service until effective date

2. Final billing
   └── Generate final invoice through cancellation date
   └── Collect final payment
   └── Apply any remaining credits

3. Grace period (30-90 days)
   └── Service disabled
   └── Data retained
   └── Customer can reactivate

4. Data retention
   └── Per data retention policy (often 90 days post-cancellation)
   └── Billing records retained per legal requirements (typically 7 years)
   └── Usage data may be retained longer for analytics (anonymized)

5. Deletion
   └── Customer data deleted per policy
   └── Stripe customer may be retained (Stripe has its own retention)
   └── Billing records are NEVER deleted (legal requirement)
```

### Self-Service vs Sales-Assisted

| Aspect | Self-Service | Sales-Assisted |
|--------|-------------|----------------|
| Onboarding | Automated, web-based | Sales rep + solutions engineer |
| Pricing | Published, standard plans | Custom, negotiated |
| Payment | Credit card via Stripe | Invoice with net-30/60 terms |
| Contract | Click-through ToS | MSA + Order Form |
| Support | Standard SLA | Custom SLA, dedicated support |
| Billing | Automated, usage-based | May include committed use agreements |
| Plan changes | Self-service portal | Account manager coordination |

The billing system must support both paths seamlessly. A self-service customer who grows may become a sales-assisted enterprise customer. The transition should not require re-architecture of their billing setup.

---

## Billing System Components

### Customer-Facing Usage Dashboard

Customers need real-time visibility into their usage to avoid bill shock and to plan capacity.

```
┌────────────────────────────────────────────────────┐
│ Usage Dashboard - February 2026                     │
├────────────────────────────────────────────────────┤
│                                                     │
│ Current Period: Feb 1 - Feb 28                      │
│ Actions Used: 12,450,000 / 15,000,000 committed     │
│ ████████████████████░░░░░ 83%                       │
│                                                     │
│ Daily Trend:                                        │
│ ▁▂▃▅▇█████████████████▇▅  (avg: 445K/day)         │
│                                                     │
│ By Action Type:                                     │
│   Workflow Starts:    4,200,000  (34%)              │
│   Activity Executions: 6,100,000  (49%)             │
│   Signals:            1,500,000  (12%)              │
│   Queries:              650,000  (5%)               │
│                                                     │
│ Estimated Invoice: $220.00                          │
│ (based on current usage rate)                       │
│                                                     │
│ Namespaces:                                         │
│   production:  8,200,000 actions (66%)              │
│   staging:     3,100,000 actions (25%)              │
│   development: 1,150,000 actions (9%)               │
└────────────────────────────────────────────────────┘
```

**Implementation considerations:**
- Usage data for the dashboard comes from Redis (real-time counters) or the hourly pre-aggregated tables, not from raw events.
- The "estimated invoice" projection uses the rating engine with the customer's current plan.
- Per-namespace breakdown requires the metering events to include namespace metadata.
- Dashboard reads are eventually consistent (a few minutes lag is acceptable).

### Plan and Pricing Management

The billing team maintains pricing plans that define how usage converts to charges.

```sql
CREATE TABLE pricing_plans (
    plan_id       UUID PRIMARY KEY,
    plan_name     TEXT NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    status        TEXT NOT NULL CHECK (status IN ('draft', 'active', 'deprecated', 'archived')),
    base_fee_cents BIGINT NOT NULL DEFAULT 0,
    billing_period TEXT NOT NULL DEFAULT 'monthly',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(plan_name, version)
);

CREATE TABLE pricing_tiers (
    tier_id       UUID PRIMARY KEY,
    plan_id       UUID NOT NULL REFERENCES pricing_plans(plan_id),
    action_type   TEXT NOT NULL,  -- 'all' or specific type
    min_quantity  BIGINT NOT NULL,
    max_quantity  BIGINT,  -- NULL = unlimited
    unit_price_cents BIGINT NOT NULL,
    sort_order    INTEGER NOT NULL
);

CREATE TABLE customer_plans (
    customer_id    UUID NOT NULL REFERENCES customers(id),
    plan_id        UUID NOT NULL REFERENCES pricing_plans(plan_id),
    effective_from TIMESTAMPTZ NOT NULL,
    effective_to   TIMESTAMPTZ,  -- NULL = current plan
    commitment     JSONB,  -- committed use terms if applicable
    custom_pricing JSONB,  -- overrides for enterprise customers
    PRIMARY KEY (customer_id, effective_from)
);
```

---

## Temporal-Specific Context

### Temporal's Pricing Model

Temporal Cloud uses actions-based pricing. An "action" is a billable unit of work within the Temporal platform.

**What counts as an action:**
- Workflow execution started
- Activity execution (started or completed, depending on the model)
- Signal sent to a workflow
- Query to a workflow
- Timer fired
- Child workflow started
- Search attribute update
- (The exact list evolves -- check current pricing docs)

**What does NOT count (typically):**
- Heartbeats (would be too noisy)
- Workflow task processing (internal to the system)
- Retries of the same activity (counted once, not per retry -- otherwise customers would be penalized for reliability features)

### Using Temporal to Build Billing Systems

This is the meta-play: Temporal's own product is excellent for building billing pipelines. If asked in an interview, you should be able to articulate why.

**Subscription lifecycle as a Temporal workflow:**

```go
func SubscriptionWorkflow(ctx workflow.Context, customerID string) error {
    // Start trial
    if err := workflow.ExecuteActivity(ctx, CreateTrialActivity, customerID).Get(ctx, nil); err != nil {
        return err
    }

    // Wait for trial period or conversion
    trialTimer := workflow.NewTimer(ctx, 14*24*time.Hour)
    conversionCh := workflow.GetSignalChannel(ctx, "convert-to-paid")

    selector := workflow.NewSelector(ctx)

    var converted bool
    selector.AddReceive(conversionCh, func(c workflow.ReceiveChannel, more bool) {
        var planID string
        c.Receive(ctx, &planID)
        workflow.ExecuteActivity(ctx, ActivateSubscriptionActivity, customerID, planID).Get(ctx, nil)
        converted = true
    })
    selector.AddFuture(trialTimer, func(f workflow.Future) {
        if !converted {
            workflow.ExecuteActivity(ctx, ExpireTrialActivity, customerID).Get(ctx, nil)
        }
    })
    selector.Select(ctx)

    if !converted {
        return nil // Trial expired
    }

    // Monthly billing loop
    for {
        // Wait for billing period
        if err := workflow.Sleep(ctx, 30*24*time.Hour); err != nil {
            return err
        }

        // Generate invoice
        var invoice Invoice
        if err := workflow.ExecuteActivity(ctx, GenerateInvoiceActivity, customerID).Get(ctx, &invoice); err != nil {
            return err
        }

        // Collect payment with retry
        if err := workflow.ExecuteActivity(ctx, CollectPaymentActivity, invoice).Get(ctx, nil); err != nil {
            // Payment failed -- start dunning
            if err := handleDunning(ctx, customerID, invoice); err != nil {
                // Dunning exhausted -- suspend account
                workflow.ExecuteActivity(ctx, SuspendAccountActivity, customerID).Get(ctx, nil)
                return nil
            }
        }

        // Check for cancellation signal
        cancelCh := workflow.GetSignalChannel(ctx, "cancel-subscription")
        if cancelCh.ReceiveAsync(nil) {
            workflow.ExecuteActivity(ctx, CancelSubscriptionActivity, customerID).Get(ctx, nil)
            return nil
        }
    }
}
```

**Why Temporal is a good fit for billing workflows:**

1. **Durability.** A billing workflow that runs for years (the lifetime of a subscription) must survive server restarts, deployments, and infrastructure failures. Temporal workflows are durable by design.

2. **Exactly-once execution guarantees.** Activity execution is retried on failure but not double-executed on success. This is critical for payment operations where double-charging is unacceptable.

3. **Long-running timers.** Billing cycles are monthly. Dunning can take weeks. Temporal's timer infrastructure handles long waits natively without holding resources.

4. **Saga pattern for compensation.** If invoice generation succeeds but payment collection fails, you need compensating actions (void the invoice, notify the customer, update the account state). Temporal workflows make this pattern explicit and reliable.

5. **Visibility and debugging.** Every step of the billing workflow is recorded in the Temporal event history. When a customer disputes a charge, you can see the exact sequence of events that led to the invoice.

---

## Common Interview Questions

### Q1: How would you design a metering pipeline that handles 10 million events per day?

Start with the pipeline: event producers emit to Kafka (partitioned by customer_id for ordering). A consumer group reads from Kafka, validates events, applies Bloom filter dedup, and writes to S3 (raw) and a staging table. A scheduled aggregation job runs hourly, reading from the staging table, deduplicating by idempotency key, and writing aggregated totals to PostgreSQL.

**Scaling considerations:** At 10M events/day (~115 events/sec average, ~350/sec peak), a single Kafka partition and consumer can handle this. At 100M events/day, you need multiple partitions and consumers. At 1B events/day, you need a dedicated streaming infrastructure (Kafka + Flink/Spark Streaming).

**The key tradeoff:** Pre-aggregation (hourly/daily jobs) vs. streaming aggregation (real-time). Pre-aggregation is simpler and handles late events more gracefully but has higher latency. Streaming aggregation gives real-time usage visibility but is harder to make exactly-once correct.

### Q2: A customer claims their invoice is wrong. How do you investigate?

This is a debugging question that tests your understanding of the full pipeline.

1. Pull the invoice and its line items from the database.
2. Re-run the rating engine with the same inputs (aggregated usage + plan). If the result differs, the rating engine or plan was wrong.
3. Pull the aggregated usage for the billing period. Compare to the invoice inputs.
4. Pull the raw events from S3 for the billing period. Re-aggregate. Compare to the aggregated totals.
5. At each step, check for: late-arriving events counted in the wrong period, dedup failures (events counted twice), aggregation errors (wrong time window), plan misconfiguration.

The investigation narrows from "the invoice is wrong" to "these 47 events on February 15 were counted twice due to a consumer restart during a deployment at 3:47 PM."

### Q3: How do you handle the Stripe consistency gap?

Stripe is eventually consistent. After creating an object (subscription, invoice), it might take seconds to appear in subsequent API calls or webhook deliveries.

**Pattern:** Never rely on querying Stripe for state you just created. Use the response from the creation call as the source of truth. Store it locally. If you need to verify later, query with retries and a backoff.

For webhooks: do not assume ordering. `invoice.paid` might arrive before `invoice.created`. Design handlers to be order-independent -- check if the local invoice record exists, and if not, create it from the webhook data or queue the event for reprocessing.

### Q4: How would you migrate a customer from direct billing to AWS Marketplace billing?

1. Create the marketplace entitlement (customer subscribes in AWS Marketplace).
2. Link the AWS customer ID to the existing internal customer record.
3. Set a migration effective date (typically the next billing period start).
4. For the current period: bill directly through Stripe for usage before the effective date, and through AWS Marketplace for usage after.
5. Cancel the Stripe subscription (effective at the migration date, not immediately).
6. Ensure metering continues to report to both systems during the overlap period.
7. Reconcile the final direct invoice and the first marketplace invoice.

The hard part is the overlap period. For simplicity, some companies make marketplace migration effective at the start of the next billing period only, avoiding proration complexity.

### Q5: What is the difference between tiered and volume pricing?

**Tiered pricing:** Each unit is priced at the rate for the tier it falls into. The first 1M actions at $25/M, the next 9M at $20/M, the remaining at $15/M. A customer using 15M actions pays: ($25 + $180 + $75) = $280.

**Volume pricing:** All units are priced at the rate of the highest tier reached. A customer using 15M actions (which falls in the 10M+ tier at $15/M) pays: 15M x $15/M = $225.

Tiered pricing rewards incremental growth. Volume pricing rewards reaching a threshold. Volume pricing is simpler to explain to customers but can create cliff effects (using 9.9M actions costs $223, but 10.1M costs $151.50 -- the customer pays less for more usage).

### Q6: How would you implement idempotent payment collection?

Use Stripe's idempotency keys:

```go
params := &stripe.PaymentIntentParams{
    Amount:   stripe.Int64(28000), // $280.00
    Currency: stripe.String("usd"),
    Customer: stripe.String(stripeCustomerID),
}
params.IdempotencyKey = stripe.String("invoice_" + invoiceID)

pi, err := paymentintent.New(params)
```

If this request is retried (network timeout, server crash), Stripe returns the same result without creating a duplicate charge. The idempotency key must be deterministic and unique per logical operation (not per API call).

Combine with local state tracking: mark the invoice as "payment_initiated" before calling Stripe, and "payment_completed" after success. If the server crashes between "initiated" and "completed," a recovery job checks the Stripe idempotency key to determine the actual state.

### Q7: How do you prevent bill shock for customers?

Bill shock (an unexpectedly high invoice) damages trust and causes churn.

**Prevention mechanisms:**
1. **Usage alerts.** Notify customers at 50%, 80%, and 100% of their expected/committed usage.
2. **Spending limits.** Allow customers to set a maximum monthly spend. When reached, either throttle usage or alert without blocking (customer choice).
3. **Anomaly detection.** If a customer's daily usage is 3x their trailing average, alert both the customer and the account team.
4. **Estimated invoice on dashboard.** Show the projected invoice amount in real time.
5. **Committed use plans.** Customers who commit to a usage level get a discount and predictability.

### Q8: Why would you use Temporal workflows for billing instead of cron jobs?

Cron jobs are stateless. They run at a schedule and must re-derive all context from the database. If a cron job fails, you need a separate mechanism to detect and retry it. If a billing workflow involves multiple steps (generate invoice, apply credits, calculate tax, create Stripe invoice, notify customer), cron has no built-in way to track partial progress.

Temporal workflows are stateful and durable. The workflow maintains its position in the billing process across failures. If the "create Stripe invoice" step fails, the workflow retries exactly that step -- it does not re-run the entire billing pipeline from scratch. The event history provides a complete audit trail. Long-running operations (waiting for payment, dunning schedules) are modeled as sleep/timer operations, not as separate cron jobs checking a state machine in the database.

---

## Key Takeaways

1. **The metering pipeline is the foundation.** If you count wrong, nothing else matters. Invest heavily in deduplication, reconciliation, and observability.

2. **Never use floats for money.** Integer cents or fixed-point decimals. No exceptions.

3. **Idempotency at every layer.** Every operation in the billing pipeline must be safe to retry without side effects.

4. **Immutability for financial records.** Never modify a finalized invoice. Issue credit notes for corrections. Maintain a complete audit trail.

5. **Reconciliation is not optional.** Compare metering data to aggregated data to invoiced data to collected data. Discrepancies are bugs.

6. **Stripe is the payment rail, not the billing brain.** For complex pricing, own the rating logic and use Stripe for payment collection.

7. **Marketplace billing is a parallel pipeline.** It must reconcile with your internal metering data but has different APIs, settlement cycles, and constraints.

8. **Design for the unhappy path.** Payment failures, late events, marketplace API outages, customer disputes, mid-cycle plan changes. The happy path is easy. The edge cases are the job.
