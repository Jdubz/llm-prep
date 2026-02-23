# Billing & Metering Cheat Sheet

> Quick-reference card for billing system design, Stripe integration, and metering patterns.

---

## Billing Pipeline Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Product    │    │   Metering   │    │  Aggregation │    │    Rating    │    │  Invoicing   │    │   Payment    │
│   Services   │───►│   Pipeline   │───►│    Engine    │───►│    Engine   │───►│   Engine     │───►│   (Stripe)   │
│              │    │              │    │              │    │              │    │              │    │              │
│ Emit events  │    │ Validate     │    │ Roll up to   │    │ Apply pricing│    │ Generate     │    │ Collect      │
│ (actions,    │    │ Deduplicate  │    │ hourly/daily │    │ rules (tiers,│    │ invoice with │    │ payment,     │
│ workflows,   │    │ Enrich       │    │ /monthly     │    │ committed,   │    │ line items,  │    │ handle       │
│ signals)     │    │ Store (S3)   │    │ buckets      │    │ free tier)   │    │ credits, tax │    │ failures     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                   │                   │                   │                   │
    Kafka/             Raw: S3            Agg: PostgreSQL      Deterministic       Immutable once      Idempotency
    Kinesis            Dedup: Redis/BF    Analytics: Redshift  Pure function       finalized           keys on all
                                                                                                       API calls
```

---

## Metering Event Schema

```json
{
  "event_id": "evt_unique_id",
  "idempotency_key": "ns-wf-action-timestamp",
  "event_type": "action.consumed",
  "timestamp": "2026-02-22T10:30:00.123Z",
  "customer_id": "cust_xxx",
  "namespace_id": "ns-prod",
  "properties": {
    "action_type": "workflow_execution_started",
    "workflow_type": "order-processing",
    "region": "us-east-1"
  },
  "quantity": 1
}
```

**Required fields:** event_id, idempotency_key, event_type, timestamp, customer_id, quantity

**Enrichment fields:** namespace_id, properties (action_type, region, workflow_type)

---

## Stripe API Essentials

### Core Objects

| Object | Purpose | Key Fields |
|--------|---------|------------|
| Customer | Billing entity | id, email, metadata, default_payment_method |
| Subscription | Recurring billing relationship | id, customer, items, status, current_period_start/end |
| Price | Pricing definition | id, unit_amount, currency, recurring.interval, billing_scheme |
| Invoice | The bill | id, customer, lines, total, status, paid |
| PaymentIntent | Payment attempt | id, amount, status, payment_method |
| UsageRecord | Metered usage report | subscription_item, quantity, timestamp, action |

### Key Endpoints

```
POST   /v1/customers                          Create customer
POST   /v1/subscriptions                      Create subscription
POST   /v1/subscription_items/{id}/usage_records  Report usage
POST   /v1/invoices                           Create invoice
POST   /v1/invoices/{id}/finalize             Finalize invoice
POST   /v1/invoices/{id}/pay                  Attempt payment
GET    /v1/invoices/{id}                      Get invoice
POST   /v1/payment_intents                    Create payment intent
```

### Critical Webhook Events

| Event | Handle By |
|-------|-----------|
| `invoice.paid` | Mark invoice paid, update account status |
| `invoice.payment_failed` | Start dunning workflow |
| `customer.subscription.updated` | Sync subscription state locally |
| `customer.subscription.deleted` | Trigger offboarding flow |
| `charge.dispute.created` | Alert team, freeze account |
| `payment_intent.requires_action` | Send customer 3DS authentication link |

### Webhook Handler Template

```go
// 1. Read body
// 2. Verify signature: webhook.ConstructEvent(payload, sig, secret)
// 3. Check idempotency: skip if event.ID already processed
// 4. Route by event.Type
// 5. Process idempotently
// 6. Record event.ID as processed
// 7. Return 200 (or 500 to trigger Stripe retry)
```

---

## Aggregation Strategy Comparison

| Strategy | Latency | Accuracy | Complexity | Best For |
|----------|---------|----------|------------|----------|
| **Pre-aggregation (batch)** | Hours | High (after grace period) | Low | Billing, monthly reports |
| **Streaming** | Seconds | High (with exactly-once) | High | Real-time dashboards |
| **On-demand query** | Minutes | Perfect (current data) | Low | Ad-hoc investigation |
| **Hybrid (pre-agg + stream)** | Seconds for display, hours for billing | High | Medium-High | Production billing systems |

### Late Event Handling

| Approach | When to Use |
|----------|-------------|
| Re-aggregate affected bucket | Low volume of late events, simple pipeline |
| Correction entries (append) | High volume, immutable aggregation tables |
| Grace period before finalization | When a known delay is acceptable |

---

## Pricing Model Comparison

| Model | Calculation | Customer Experience | Implementation |
|-------|-------------|-------------------|----------------|
| **Per-unit** | quantity x price | Simple, predictable | Easy |
| **Tiered** | Each range at its own rate | Rewards growth incrementally | Medium |
| **Volume** | All units at highest tier reached | Can create "cliff" savings | Medium |
| **Committed use** | Prepaid base + overage rate | Predictable, discounted | Hard |
| **Free tier** | First N free, then paid | Low barrier to entry | Easy |
| **Hybrid** | Base fee + usage-based | Platform fee + consumption | Hard |

### Tiered vs Volume Example (15M actions)

```
Tiers: 0-1M @ $25/M,  1M-10M @ $20/M,  10M+ @ $15/M

Tiered:  (1M x $25) + (9M x $20) + (5M x $15) = $25 + $180 + $75 = $280
Volume:  15M x $15 = $225  (all units at the tier for 15M)
```

---

## Marketplace Integration Comparison

| Aspect | AWS Marketplace | GCP Marketplace | Azure Marketplace |
|--------|----------------|-----------------|-------------------|
| **Usage API** | BatchMeterUsage | Commerce Ingestion API | Metering Service API |
| **Subscription** | SaaS Subscription API | Procurement API | SaaS Fulfillment API v2 |
| **Entitlement** | Entitlement API | Procurement Entitlement | Fulfillment API |
| **Fee** | 3-5% | 3% | 3% |
| **Private offers** | CPPO | Yes | Yes |
| **Granularity** | Hourly | Hourly | Hourly |
| **Settlement** | Monthly | Monthly | Monthly |
| **Activation** | Automatic on resolve | Requires approval | Requires explicit activation |

### Marketplace Integration Flow (Generic)

```
1. Customer subscribes in marketplace console
2. Marketplace redirects to your registration URL
3. You resolve/verify the marketplace customer identity
4. You link marketplace ID to your internal customer record
5. You report usage periodically via marketplace metering API
6. Marketplace bills the customer on their cloud invoice
7. Marketplace pays you (minus fee)
```

---

## Common Billing Bugs and Prevention

| Bug | Impact | Prevention |
|-----|--------|-----------|
| Float arithmetic for money | Rounding errors compound, invoices off by cents | Use integer cents (`BIGINT`) or `NUMERIC(19,4)` |
| Missing idempotency key on Stripe calls | Duplicate charges on retry | Always set `IdempotencyKey` on mutating API calls |
| Webhook processed twice | Double state transitions, duplicate actions | Store processed event IDs, check before processing |
| Late events in wrong billing period | Under/over-billing | Grace period + correction entries |
| Timezone mismatch (local vs UTC) | Events assigned to wrong day/month | Store all timestamps in UTC, convert for display only |
| Plan change without proration | Customer over/under-charged | Split billing period at plan change effective date |
| Dedup window too short | Old duplicates re-counted | Dedup window >= billing period + grace (35 days) |
| Invoice mutated after finalization | Audit failure, legal issues | Enforce immutability in code + DB constraints |
| Hardcoded currency decimals | JPY billed as 1/100th actual | Lookup currency exponent, handle 0 and 3 decimal currencies |
| Missing audit log on credit issuance | Cannot explain invoice adjustments | Log every mutation with actor, timestamp, reason |

---

## Data Integrity Checklist

- [ ] All monetary values stored as integers (cents) or NUMERIC, never FLOAT
- [ ] Every metering event has an idempotency key
- [ ] Dedup exists at ingestion AND aggregation layers
- [ ] Invoices are immutable once finalized (corrections via credit notes)
- [ ] Every billing mutation has an audit log entry (who, when, what, why)
- [ ] Reconciliation runs daily: raw events vs aggregated vs invoiced vs collected
- [ ] Stripe API calls use idempotency keys
- [ ] Webhooks are verified (signature check) and deduplicated (event ID check)
- [ ] Rating engine is deterministic: same inputs always produce same outputs
- [ ] Ledger entries balance: SUM(debits) = SUM(credits) per transaction
- [ ] Tax rates stored with invoices (not just tax amounts)
- [ ] Currency exponents handled correctly for all supported currencies

---

## Customer Lifecycle State Machine

```
              ┌────────────────────────────────────────────┐
              │                                            │
  Sign Up ──► Trial ──► Active ──► Past Due ──► Suspended ──► Churned
              │                       │              │
              │                       │              └──► Active
              │                       └──► Active         (recovered)
              │
              └──► Churned (trial expired)
```

| Transition | Trigger | Billing Action |
|-----------|---------|----------------|
| Sign Up -> Trial | Registration | Create customer, start metering (no billing) |
| Trial -> Active | Payment method added + plan selected | Create subscription, begin billing |
| Trial -> Churned | 14-day timer expires | Mark churned, clean up |
| Active -> Past Due | Payment fails | Start dunning workflow |
| Past Due -> Active | Payment succeeds (retry or manual) | Clear dunning state |
| Past Due -> Suspended | Multiple failures (Day 14-21) | Degrade/disable service |
| Suspended -> Active | Payment recovered | Restore service |
| Suspended -> Churned | Dunning exhausted (Day 28+) | Final invoice, begin offboarding |
| Active -> Churned | Customer cancels | Final invoice, begin offboarding |

---

## Interview Questions -- Quick Answers

**Q: How do you prevent double-charging?**
Idempotency at every layer: idempotency keys on metering events, dedup at aggregation, unique constraints on invoices (one per customer per period), Stripe idempotency keys on payment API calls.

**Q: Why not use Stripe's native metered billing?**
Stripe supports simple per-unit pricing but not complex tiered pricing, committed use discounts, custom enterprise deals, or multi-marketplace billing. Own the rating logic, use Stripe as the payment rail.

**Q: How do you handle a metering pipeline outage?**
Kafka retains events during consumer downtime. When the consumer recovers, it replays from the last committed offset. The dedup layer handles any resulting duplicates. No events are lost. Alert on consumer lag.

**Q: What is the hardest part of billing systems?**
Correctness at the boundaries: late-arriving events, mid-cycle plan changes, marketplace reconciliation, and proration. The happy path is straightforward. The edge cases where two concerns intersect (plan change + late event + marketplace billing) are where bugs hide.

**Q: How would you use Temporal for billing?**
Subscription lifecycle as a long-running workflow (trial, conversion, monthly billing loop). Dunning as a child workflow with timer-based retries. Invoice generation as a workflow with saga-pattern compensation. The event history provides a complete audit trail.

**Q: What is bill shock and how do you prevent it?**
Unexpectedly high invoice. Prevent with: usage alerts at thresholds (50%, 80%, 100%), spending limits, anomaly detection, real-time usage dashboard with estimated invoice, and committed use plans for predictability.

**Q: How do you reconcile marketplace billing?**
Compare: your metering data (ground truth) vs what you reported to the marketplace API vs what the marketplace charged the customer vs what the marketplace paid you. Run monthly. Flag discrepancies for investigation. Common issues: rejected usage reports, dimension mapping mismatches, settlement timing differences.

**Q: Walk me through an invoice dispute investigation.**
Start from the invoice. Check line items against the rating engine (re-rate with same inputs). Check rated inputs against aggregated usage. Check aggregated usage against raw events in S3. At each step, the discrepancy either resolves (identifying the bug) or narrows (pointing to the next layer to investigate).

---

## Temporal-Specific Billing Facts

- **Pricing unit:** Actions (workflow starts, activities, signals, queries, timers, child workflows)
- **Namespace isolation:** Usage is tracked per namespace but billed per account
- **Metering infrastructure:** Likely Kafka-based pipeline feeding Metronome
- **Billing vendors:** Metronome (rating/invoicing) + Stripe (payment collection)
- **Marketplace presence:** AWS, GCP, Azure marketplaces
- **What the team owns:** Metering pipeline, billing integration, customer onboarding/offboarding, marketplace integrations, usage dashboards, revenue operations tooling
