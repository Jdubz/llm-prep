# Interview Prep -- Deep Dive

> Three system design walkthroughs tailored to the billing, metering, and Cloud Nexus team at Temporal.
> Practice these out loud with a timer. The goal isn't a perfect answer -- it's showing clear thinking
> under pressure, structured communication, and deep domain awareness.

---

## Table of Contents

1. [Design Exercise 1: Metering Pipeline for Temporal Cloud](#design-exercise-1-metering-pipeline-for-temporal-cloud)
2. [Design Exercise 2: Billing System with Marketplace Integrations](#design-exercise-2-billing-system-with-marketplace-integrations)
3. [Design Exercise 3: Cloud Nexus -- Multi-Cloud Connectivity Platform](#design-exercise-3-cloud-nexus----multi-cloud-connectivity-platform)

---

## Design Exercise 1: Metering Pipeline for Temporal Cloud

**The prompt:** "Design a metering pipeline that tracks all billable actions across Temporal Cloud namespaces. It must be accurate (revenue depends on it), handle millions of events per day, support late-arriving data, and enable real-time usage dashboards."

**Time budget (45-minute interview):**
- Requirements clarification: 3 minutes
- High-level architecture: 5 minutes
- Deep dives (ingestion, aggregation, storage): 20 minutes
- Deduplication and late events: 7 minutes
- Monitoring and operations: 5 minutes
- Tradeoffs and alternatives: 5 minutes

---

### Step 1: Requirements Clarification (3 min)

Ask these before drawing anything. They show you think before you build.

**Functional requirements:**
- "What are the billable actions? I'm assuming workflow executions, activity executions, signal/query volume, and storage -- but are there others? Is it per-namespace or per-account?"
- "What's the billing granularity? Per-minute? Per-hour? Per-day? This affects aggregation window size."
- "Do customers need real-time usage visibility, or is near-real-time (5-minute delay) acceptable for dashboards?"
- "Are there usage tiers or rate limits tied to metering? Does exceeding a threshold trigger an action (throttle, notification, auto-upgrade)?"

**Non-functional requirements:**
- "What's the current event volume? Millions per day -- is that 5 million or 500 million? That's a 100x difference in architecture."
- "What's the acceptable latency from event occurrence to dashboard visibility?"
- "What's the accuracy SLA? Are we allowed to under-count slightly (and true-up later) or must counts be exact in real-time?"
- "How long do we retain raw events? For audit purposes, I'd assume 1-2 years minimum."

**Assumptions I'd state:**
- ~50 million events/day (~580 events/sec average, ~5000/sec peak)
- Billing granularity is hourly aggregation, invoiced monthly
- Real-time dashboards can be 1-2 minutes behind
- Raw events retained for 13 months (current billing year + 1 month)

---

### Step 2: High-Level Architecture (5 min)

```
                                 Temporal Cloud Infrastructure
                                 ============================

  Namespace A     Namespace B     Namespace C
      |               |               |
      v               v               v
  +-----------------------------------------------+
  |           Event Producers                      |
  |  (instrumented in Temporal server components)  |
  +-----------------------------------------------+
                      |
                      | Raw events (protobuf)
                      v
  +-----------------------------------------------+
  |           Kinesis Data Stream                  |
  |  (partitioned by namespace_id)                 |
  |  Retention: 7 days                             |
  +-----------------------------------------------+
           |                          |
           v                          v
  +------------------+    +----------------------+
  |  S3 Raw Archive  |    |  Aggregation Workers |
  |  (Kinesis Firehose)   |  (Temporal workflows) |
  |  Parquet format  |    |  Hourly rollups      |
  +------------------+    +----------------------+
                                    |
                                    v
                          +------------------+
                          |   PostgreSQL     |
                          |  Usage Aggregates|
                          |  (billing source)|
                          +------------------+
                                    |
                     +--------------+--------------+
                     |                             |
                     v                             v
            +----------------+           +------------------+
            | Billing Service|           | Usage Dashboard  |
            | (invoice gen)  |           | (customer-facing)|
            +----------------+           +------------------+
```

**Key design decisions to state out loud:**
1. Kinesis as the ingestion layer because we're on AWS (Temporal Cloud runs on AWS). Partitioned by namespace_id for ordered processing per tenant.
2. S3 as the durable archive -- raw events in Parquet format for efficient analytical queries. This is our audit trail and reprocessing source.
3. Temporal workflows for aggregation -- dogfooding the product and getting durable execution guarantees for a revenue-critical pipeline.
4. PostgreSQL for billing aggregates -- the billing service needs strong consistency and transactional guarantees.

---

### Step 3: Event Ingestion (5 min)

**Event schema:**
```protobuf
message MeteringEvent {
  string event_id = 1;          // UUID, globally unique
  string namespace_id = 2;      // partition key
  string account_id = 3;        // billing entity
  string action_type = 4;       // "workflow_started", "activity_completed", etc.
  int64 timestamp_ms = 5;       // event time (not processing time)
  map<string, string> dimensions = 6;  // workflow_type, task_queue, etc.
  int64 quantity = 7;           // usually 1, but could be batch size
}
```

**Ingestion path:**
1. Temporal server components emit events at the point of action (workflow task completed, activity scheduled, etc.).
2. Events are buffered locally (in-memory ring buffer, ~1 second) and flushed to Kinesis in batches for throughput.
3. Each Kinesis record is a batch of events compressed with zstd. Partitioned by namespace_id to maintain per-namespace ordering.
4. Kinesis Firehose delivers raw events to S3 in Parquet format with 5-minute batching (configurable buffer size/time).

**Why Kinesis over Kafka:**
- Temporal Cloud is AWS-native. Kinesis is managed, serverless scaling, and integrates natively with S3 via Firehose.
- Kafka would give more control but adds operational burden. For a metering pipeline where the team is focused on billing, not stream infrastructure, Kinesis is the right tradeoff.
- If volume exceeds Kinesis shard limits (1MB/sec per shard write, 2MB/sec read), we can reshard or move to Kafka later.

**Failure handling at ingestion:**
- If Kinesis is unavailable, the local buffer provides a brief window. If the buffer fills, events are written to a local WAL (write-ahead log on disk) and retried.
- The event producer is instrumented with metrics: events produced, events failed, buffer utilization. Alert if buffer utilization exceeds 80%.

---

### Step 4: Aggregation (8 min)

This is the heart of the pipeline and where Temporal workflows provide the most value.

**Aggregation workflow design:**

```
One workflow per namespace per hour:
  workflow_id = "meter-agg-{namespace_id}-{hour_bucket}"

  1. Read events from Kinesis (via activity)
  2. Deduplicate events (check event_id against processed set)
  3. Aggregate: group by action_type, sum quantities
  4. Write aggregated usage to PostgreSQL (via activity)
  5. Update the high-water mark (latest event timestamp processed)
  6. Sleep until the next aggregation window
  7. Continue-as-new to prevent unbounded history
```

**Why a Temporal workflow for aggregation:**
- Exactly-once semantics: if the aggregation worker crashes mid-way, the workflow replays and resumes from the last completed activity. No duplicate counts, no missed events.
- Built-in retries: if the PostgreSQL write fails, the activity retries with backoff. No manual retry logic.
- Visibility: you can query any aggregation workflow to see its current state, last processed timestamp, and error history.
- Dogfooding: this team is building Temporal. Using Temporal for your own critical infrastructure demonstrates confidence in the product.

**Aggregation data model (PostgreSQL):**

```sql
CREATE TABLE usage_aggregates (
    id              BIGSERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL,
    namespace_id    TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    hour_bucket     TIMESTAMPTZ NOT NULL,  -- truncated to hour
    quantity        BIGINT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (namespace_id, action_type, hour_bucket)
);

-- Index for billing queries: "total usage for account X in period Y"
CREATE INDEX idx_usage_account_period
    ON usage_aggregates (account_id, hour_bucket);
```

**Aggregation window management:**
- Each hour bucket is aggregated independently. The workflow for hour H starts at H+5min (grace period for stragglers).
- The workflow reads all events with timestamps in [H, H+1h) from Kinesis.
- If the workflow fails and restarts, it re-reads the same window. Deduplication ensures no double-counting.

---

### Step 5: Deduplication Strategy (4 min)

**Problem:** At-least-once delivery from Kinesis + at-least-once activity execution in Temporal = potential duplicate event processing.

**Solution -- tiered deduplication:**

1. **In-memory bloom filter** (first pass, fast):
   - Each aggregation workflow maintains a bloom filter of processed event IDs for the current window.
   - False positive rate of 0.1% is acceptable -- a small number of events may be re-checked against the database.
   - Bloom filter size: ~50K events per namespace per hour * 10 bits per element = ~60KB. Negligible.

2. **Database-level deduplication** (second pass, definitive):
   - A `processed_events` table stores event IDs with a TTL (7 days, matching Kinesis retention).
   - Before writing an aggregate, the activity checks if the event IDs in the batch have been processed.
   - This check and the aggregate write happen in the same database transaction -- atomicity guarantees no gap between "check" and "mark as processed."

```sql
CREATE TABLE processed_events (
    event_id    TEXT PRIMARY KEY,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- TTL cleanup: daily job deletes events older than 7 days
-- Could also use PostgreSQL partitioning by day for efficient drops
```

3. **Aggregate-level idempotency** (belt and suspenders):
   - The aggregate write uses `INSERT ... ON CONFLICT (namespace_id, action_type, hour_bucket) DO UPDATE SET quantity = usage_aggregates.quantity + EXCLUDED.quantity` only if the batch hasn't been applied.
   - Track batch IDs to prevent reapplying the same aggregation batch.

---

### Step 6: Late-Arriving Events (3 min)

**Definition:** An event with a timestamp in hour H that arrives after the aggregation for hour H has completed.

**Three categories:**

1. **Slightly late (< grace period, e.g., < 5 min):**
   - The aggregation workflow hasn't started yet. No special handling needed.

2. **Moderately late (< 24 hours):**
   - A correction workflow runs daily, scanning for events with timestamps in already-aggregated windows.
   - It reads from the S3 raw archive (which has everything), re-aggregates the affected windows, and computes deltas.
   - Deltas are written as correction records in the usage_aggregates table (not updating the original -- append only).

3. **Very late (> 24 hours):**
   - These are rare and usually indicate a systemic issue (a worker was down, a region was partitioned).
   - They trigger an alert for investigation. The correction workflow still processes them, but a human reviews the correction before it affects billing.

**Billing integration:**
- At invoice time (end of billing period), the billing service reads aggregated usage including all corrections applied up to a finalization deadline (e.g., 48 hours after period end).
- After finalization, any further corrections generate a credit or debit on the next invoice.

---

### Step 7: Real-Time Dashboard (3 min)

**Approach:** Separate read path from the billing aggregation path.

```
Kinesis --> Lambda (lightweight consumer)
              |
              v
        Redis (sorted sets)
        Key: "usage:{namespace_id}:{action_type}:{minute_bucket}"
        Value: count
        TTL: 48 hours
```

- A lightweight Kinesis consumer (Lambda or dedicated service) updates Redis counters in near-real-time (seconds of latency).
- The dashboard API reads from Redis for the current period and from PostgreSQL for historical periods.
- Redis is best-effort -- it's acceptable for the dashboard to be slightly inaccurate. The billing source of truth is always PostgreSQL.
- If Redis goes down, the dashboard shows "data temporarily unavailable" for the current period. Historical data from PostgreSQL still works.

---

### Step 8: Monitoring and Alerting (5 min)

**Pipeline health metrics:**

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Event ingestion rate | Kinesis CloudWatch | >20% drop from rolling 1h average |
| Kinesis iterator age | Kinesis CloudWatch | >5 minutes (consumer falling behind) |
| Aggregation workflow failures | Temporal visibility | Any failure (this should be zero) |
| Aggregation latency | Custom metric | >10 minutes from window close to aggregate written |
| Late event rate | Correction workflow | >1% of total events arriving late |
| Dedup collision rate | Aggregation workflow | >0.5% (indicates duplicate production) |
| S3 archive completeness | S3 inventory vs Kinesis | Any gap in hourly partitions |

**Billing correctness metrics:**

| Metric | How | Alert Threshold |
|--------|-----|-----------------|
| Raw vs aggregate reconciliation | Daily job: sum raw events, compare to aggregates | >0.01% discrepancy |
| Cross-account balance check | Sum all usage, compare to expected | Any imbalance |
| Invoice amount anomaly | Compare to previous period per customer | >200% increase or >50% decrease |
| Missing namespace coverage | Check all active namespaces have recent usage | Any namespace with 0 events for >1 hour |

---

### Step 9: Scale and Cost Estimation (3 min)

**At 50M events/day:**
- Kinesis: ~10 shards (580 events/sec average, each shard handles 1000 records/sec). Cost: ~$350/month.
- S3 storage: ~50M events * 200 bytes avg = 10GB/day raw. Parquet compression ~5x = 2GB/day. ~60GB/month. Cost: ~$1.50/month. Negligible.
- PostgreSQL: ~50M aggregate rows/month (assuming 1000 namespaces * 10 action types * 24 hours * 30 days * ~7 with corrections). A db.r6g.xlarge handles this easily. Cost: ~$500/month.
- Lambda/Redis for dashboards: ~$100/month.
- Total infrastructure cost: ~$1000/month. For a revenue-critical pipeline, this is trivial.

**Scaling to 10x (500M events/day):**
- Kinesis: ~100 shards. Consider switching to Kafka for better cost at this scale.
- PostgreSQL: partition the usage_aggregates table by month. Add read replicas for dashboard queries.
- Aggregation workflows: increase parallelism by sharding across more workflow instances (e.g., per-namespace-per-action-type instead of per-namespace).

---

### Step 10: Tradeoffs and Alternatives (5 min)

**Tradeoffs made:**
- Kinesis over Kafka: simpler operations, higher per-event cost. If we outgrow Kinesis, migration to Kafka is straightforward because the event schema is the same.
- PostgreSQL over a time-series DB (TimescaleDB, ClickHouse): PostgreSQL is simpler to operate and sufficient at our scale. If analytical queries become a bottleneck, add ClickHouse as a read replica.
- Hourly aggregation over real-time: hourly windows are a sweet spot between latency and complexity. Real-time aggregation (per-event) would require exactly-once stream processing (Flink) and is overkill for billing.
- Temporal workflows for aggregation: adds a dependency on the product we're building (bootstrapping concern). Mitigated by having the S3 archive as a reprocessing fallback.

**Alternatives discussed:**
- **Apache Flink**: purpose-built for stream aggregation with exactly-once semantics. But it's another complex system to operate, and the team's expertise is in Temporal, not Flink. Use Temporal for what it's good at.
- **Materialized views in PostgreSQL**: for simple aggregations, a materialized view over raw events could replace the entire aggregation pipeline. But it doesn't scale to 50M events/day without significant PostgreSQL tuning, and it couples your analytical and transactional workloads.
- **Pre-aggregation at the source**: have the event producer batch and pre-aggregate before writing to Kinesis. Reduces downstream volume but makes deduplication and late-event handling harder. Good optimization for later, not the initial design.

---

## Design Exercise 2: Billing System with Marketplace Integrations

**The prompt:** "Design a billing system that supports direct billing via Stripe AND marketplace billing (AWS, GCP, Azure Marketplace). Customers should have a unified billing experience regardless of channel. Must handle plan changes, proration, and credits."

**Time budget (45-minute interview):**
- Requirements clarification: 3 minutes
- High-level architecture: 5 minutes
- Deep dives (Stripe, marketplace adapters, reconciliation): 20 minutes
- Customer lifecycle state machine: 5 minutes
- Data model: 5 minutes
- Error handling and monitoring: 5 minutes
- Tradeoffs: 2 minutes

---

### Step 1: Requirements Clarification (3 min)

**Functional:**
- "How many billing channels today? I'll assume Stripe (direct), AWS Marketplace, GCP Marketplace, with Azure Marketplace planned."
- "Is pricing the same across all channels, or do marketplace customers have different rates (to account for marketplace fees)?"
- "What are the plan types? I'll assume a free tier, self-serve paid tiers (monthly/annual), and enterprise custom contracts."
- "How does proration work? Mid-cycle upgrade charges the difference immediately? Or adjusts the next invoice?"
- "Are credits applied automatically or manually? Do they expire?"

**Non-functional:**
- "How many paying customers? Hundreds, thousands, tens of thousands?"
- "What's the payment failure rate we should design for?"
- "Are there regulatory requirements? SOC2, PCI compliance?"
- "What's the current state? Greenfield or migrating from an existing system?"

**Assumptions:**
- ~5000 paying customers, growing to 50K in 18 months.
- Stripe is the primary channel (~70%), AWS Marketplace (~20%), GCP Marketplace (~10%).
- Standard SaaS pricing: per-unit monthly billing with usage-based overage charges.
- Credits are account-level, applied automatically, do not expire.

---

### Step 2: High-Level Architecture (5 min)

```
                    Customer Touchpoints
                    ====================
        Self-serve UI     Sales CRM     Marketplace Console
              |               |                |
              v               v                v
        +-------------------------------------------+
        |           Billing API (gRPC/REST)          |
        |  Plan management, subscription lifecycle,  |
        |  usage queries, invoice retrieval           |
        +-------------------------------------------+
                          |
                          v
        +-------------------------------------------+
        |           Billing Service (Go)             |
        |  Subscription state machine                |
        |  Invoice generation                        |
        |  Credit/debit management                   |
        |  Proration calculations                    |
        +-------------------------------------------+
              |               |               |
              v               v               v
    +-------------+   +-------------+   +-------------+
    |   Stripe    |   |     AWS     |   |     GCP     |
    |   Adapter   |   |  Marketplace|   |  Marketplace|
    |             |   |   Adapter   |   |   Adapter   |
    +-------------+   +-------------+   +-------------+
              |               |               |
              v               v               v
    +-------------+   +-------------+   +-------------+
    |  Stripe API |   | AWS Metering|   | GCP Procure |
    |             |   |    API      |   |    API      |
    +-------------+   +-------------+   +-------------+

        +-------------------------------------------+
        |           PostgreSQL                       |
        |  Accounts, subscriptions, invoices,        |
        |  ledger, entitlements                      |
        +-------------------------------------------+

        +-------------------------------------------+
        |      Metering Pipeline (from Exercise 1)   |
        |  Usage aggregates feed into billing        |
        +-------------------------------------------+
```

**Key architectural principle:** The billing service owns the canonical subscription and entitlement state. External systems (Stripe, marketplaces) are payment channels, not sources of truth. The billing service tells Stripe what to charge; it doesn't derive billing state from Stripe.

---

### Step 3: Stripe Integration (5 min)

**Stripe as payment processor, not billing engine:**
- We create Stripe customers, subscriptions, and invoices programmatically. Our billing service decides what to charge; Stripe executes the payment.
- Stripe subscriptions use `collection_method: "send_invoice"` for enterprise and `charge_automatically` for self-serve.
- Usage-based charges: at the end of each billing period, our billing service calculates usage from the metering pipeline and creates Stripe invoice items. Then Stripe generates and charges the invoice.

**Webhook handling (Temporal workflow):**
```
Webhook endpoint receives event
    --> Verify signature
    --> Return 200 immediately
    --> Signal a Temporal workflow: "process-stripe-event-{event_id}"

Stripe Event Processing Workflow:
    1. Check idempotency (have we processed this event_id?)
    2. Route by event type:
       - invoice.paid --> update invoice status, record payment in ledger
       - invoice.payment_failed --> trigger dunning workflow
       - customer.subscription.updated --> sync subscription state
       - charge.refunded --> record refund in ledger
    3. Mark event as processed
```

**Why Temporal for webhook processing:**
- Stripe webhooks must be acknowledged quickly (return 200). Heavy processing should be async.
- Temporal's durable execution ensures no webhook is lost, even if the processing worker crashes.
- Each event type can have its own retry and timeout policy.

**Proration with Stripe:**
- Mid-cycle plan changes: calculate the prorated amount ourselves (days remaining * price difference / total days).
- Create a Stripe invoice item for the prorated amount. This gives us control over the proration logic rather than relying on Stripe's built-in proration (which may not match our business rules).
- Log the proration calculation for audit: original plan, new plan, switch date, days remaining, prorated amount.

---

### Step 4: Marketplace Integration (8 min)

**AWS Marketplace:**

```
Customer subscribes in AWS Marketplace
    --> AWS sends POST to our fulfillment URL with registration token
    --> Fulfillment Lambda:
        1. ResolveCustomer(token) --> get AWS customer ID, product code
        2. GetEntitlements(customer_id) --> get subscribed dimensions
        3. Signal Temporal workflow: "onboard-marketplace-customer"
        4. Redirect to our registration page (pre-filled with AWS data)

Onboarding Workflow:
    1. Create/link account in our system
    2. Set billing_channel = "aws_marketplace"
    3. Provision entitlements based on AWS dimensions
    4. Start subscription lifecycle workflow
    5. Schedule hourly metering reports to AWS

Hourly Metering Workflow:
    1. Query usage aggregates for the past hour
    2. BatchMeterUsage(product_code, usage_records)
    3. Record the metering report in our ledger
    4. Handle failures: retry with backoff, alert on persistent failure
```

**Critical AWS Marketplace constraints:**
- You MUST report usage via the Metering API within 6 hours, or you lose the ability to bill for that hour.
- BatchMeterUsage is idempotent for the same customer + dimension + hour combination.
- Entitlement changes (upgrades, downgrades) come through SQS notifications. Subscribe and process these to keep entitlements in sync.

**GCP Marketplace:**

```
Customer subscribes in GCP Marketplace
    --> GCP sends approval request to our Procurement API integration
    --> Approval Workflow:
        1. Auto-approve (or manual review for enterprise)
        2. Create/link account
        3. Set billing_channel = "gcp_marketplace"
        4. Activate entitlement via Procurement API

GCP doesn't have a usage metering API like AWS.
Instead: GCP handles billing based on the entitlement level.
For usage-based: report via the Service Control API.
```

**GCP Marketplace constraints:**
- The Procurement API has an approval workflow -- you must actively approve or reject subscription requests.
- Entitlement states: PENDING, ACTIVE, SUSPENDED, CANCELLED. You must handle all transitions.
- GCP takes a revenue share (typically 20% in year 1, decreasing over time). Your pricing must account for this.

**Adapter pattern:**

```go
type BillingChannel interface {
    // Customer lifecycle
    OnboardCustomer(ctx context.Context, req OnboardRequest) (*Account, error)
    SyncEntitlements(ctx context.Context, accountID string) error

    // Billing operations
    ReportUsage(ctx context.Context, accountID string, usage []UsageRecord) error
    ProcessPlanChange(ctx context.Context, accountID string, change PlanChange) error

    // Reconciliation
    GetExternalState(ctx context.Context, accountID string) (*ExternalBillingState, error)
}

// Implementations:
type StripeChannel struct { ... }
type AWSMarketplaceChannel struct { ... }
type GCPMarketplaceChannel struct { ... }
```

The billing service calls the appropriate adapter based on the account's `billing_channel` field. All business logic (proration, credits, entitlement rules) lives in the billing service, not in the adapters.

---

### Step 5: Reconciliation (4 min)

**Why reconciliation is critical:**
- Each billing channel is an external system with its own state. Our system and the external system can drift due to missed webhooks, failed API calls, race conditions, or manual changes in the external console.
- Billing discrepancies directly impact revenue and customer trust.

**Reconciliation workflow (runs daily per channel):**

```
Daily Reconciliation Workflow:
    1. Fetch all active subscriptions from our database
    2. For each account in the billing channel:
       a. Call adapter.GetExternalState(accountID)
       b. Compare external state with our state:
          - Subscription status (active, cancelled, past_due)
          - Plan/entitlement level
          - Last payment date and amount
          - Outstanding balance
    3. For each discrepancy:
       a. Log the discrepancy with full details
       b. Classify: auto-resolvable or needs human review
       c. Auto-resolve if safe (e.g., our state is ACTIVE but Stripe says CANCELLED
          --> update our state to CANCELLED)
       d. Alert for human review if unsafe (e.g., payment amounts don't match)
    4. Generate reconciliation report
```

**Discrepancy categories:**
- **State drift**: subscription status differs. Usually caused by missed webhook. Auto-resolve by syncing to external state.
- **Amount mismatch**: invoiced amount differs from expected. Needs investigation -- could be a proration bug, tax calculation difference, or external manual adjustment.
- **Missing records**: account exists in external system but not in ours (or vice versa). This is serious and needs immediate investigation.
- **Timing differences**: expected during grace periods (e.g., we've generated an invoice but Stripe hasn't processed it yet). These resolve themselves; only alert if they persist beyond the grace period.

---

### Step 6: Customer Lifecycle State Machine (5 min)

```
                          +------------------+
                          |                  |
                 +------->|  TRIAL           |
                 |        |  (14 days)       |
                 |        +--------+---------+
                 |                 |
                 |    trial_convert|    trial_expire
                 |                 v          |
                 |        +--------+---------+|
                 |        |                  ||
    new_signup --+------->|  ACTIVE          |+---> CHURNED
                          |                  |
                          +--+------+-----+--+
                             |      |     |
               plan_change   |      |     |  payment_failed
                             v      |     v
                   +---------+--+   | +---+-----------+
                   |            |   | |               |
                   | UPGRADING/ |   | | PAST_DUE      |
                   | DOWNGRADING|   | | (dunning)     |
                   |            |   | |               |
                   +-----+------+   | +---+------+----+
                         |          |     |      |
                completed|          |  recovered |  exhausted
                         v          |     v      v
                     (back to       | (back to  SUSPENDED
                      ACTIVE)       |  ACTIVE)      |
                                    |               |
                         cancel     |    grace_expire
                                    v               v
                          +---------+--+     +------+-----+
                          |            |     |            |
                          | CANCELLING |     | CANCELLED  |
                          | (end of    |     |            |
                          |  period)   |     +------+-----+
                          +-----+------+            |
                                |            reactivate
                           period_end               |
                                v                   v
                          +-----+------+     (back to
                          |            |      ACTIVE)
                          | CANCELLED  |
                          |            |
                          +------------+
```

**Key transitions modeled as Temporal signals:**
- `trial_convert` --> Signal from checkout completion
- `payment_failed` --> Signal from Stripe webhook workflow
- `plan_change` --> Signal from billing API
- `cancel` --> Signal from customer action or marketplace notification
- `recovered` --> Signal from successful payment retry

**Each state transition:**
1. Validates the transition is legal (e.g., can't upgrade from CANCELLED)
2. Executes the necessary activities (update Stripe, adjust metering, send notification)
3. Records the transition in an audit log
4. Updates the subscription record

---

### Step 7: Data Model (5 min)

```sql
-- Organizational hierarchy
CREATE TABLE accounts (
    account_id      TEXT PRIMARY KEY,  -- "acct_" prefix
    org_id          TEXT NOT NULL,
    billing_channel TEXT NOT NULL,      -- 'stripe', 'aws_marketplace', 'gcp_marketplace'
    external_id     TEXT,               -- Stripe customer ID, AWS customer ID, etc.
    status          TEXT NOT NULL,      -- from state machine
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE subscriptions (
    subscription_id TEXT PRIMARY KEY,   -- "sub_" prefix
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id),
    status          TEXT NOT NULL,
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end   TIMESTAMPTZ NOT NULL,
    external_subscription_id TEXT,      -- Stripe sub ID, marketplace entitlement ID
    trial_end       TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Plans and pricing
CREATE TABLE plans (
    plan_id         TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    billing_period  TEXT NOT NULL,       -- 'monthly', 'annual'
    base_price_cents BIGINT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE plan_entitlements (
    plan_id         TEXT NOT NULL REFERENCES plans(plan_id),
    metric          TEXT NOT NULL,       -- 'workflow_executions', 'active_users', etc.
    included_qty    BIGINT NOT NULL,     -- included in base price
    overage_price_cents BIGINT NOT NULL, -- per unit over included
    PRIMARY KEY (plan_id, metric)
);

-- Financial ledger (append-only, double-entry)
CREATE TABLE ledger_entries (
    entry_id        BIGSERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    entry_type      TEXT NOT NULL,       -- 'charge', 'payment', 'refund', 'credit', 'adjustment'
    amount_cents    BIGINT NOT NULL,     -- positive = debit, negative = credit
    currency        TEXT NOT NULL DEFAULT 'USD',
    description     TEXT NOT NULL,
    reference_type  TEXT,                -- 'invoice', 'stripe_charge', 'marketplace_report'
    reference_id    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Invoices
CREATE TABLE invoices (
    invoice_id      TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    status          TEXT NOT NULL,       -- 'draft', 'finalized', 'sent', 'paid', 'void'
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    subtotal_cents  BIGINT NOT NULL,
    credits_applied_cents BIGINT NOT NULL DEFAULT 0,
    total_cents     BIGINT NOT NULL,
    currency        TEXT NOT NULL DEFAULT 'USD',
    external_invoice_id TEXT,            -- Stripe invoice ID
    finalized_at    TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE invoice_line_items (
    line_item_id    BIGSERIAL PRIMARY KEY,
    invoice_id      TEXT NOT NULL REFERENCES invoices(invoice_id),
    description     TEXT NOT NULL,
    metric          TEXT,
    quantity        BIGINT NOT NULL,
    unit_price_cents BIGINT NOT NULL,
    amount_cents    BIGINT NOT NULL,
    period_start    TIMESTAMPTZ,
    period_end      TIMESTAMPTZ
);

-- Credits
CREATE TABLE credits (
    credit_id       TEXT PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES accounts(account_id),
    original_amount_cents BIGINT NOT NULL,
    remaining_amount_cents BIGINT NOT NULL,
    reason          TEXT NOT NULL,
    expires_at      TIMESTAMPTZ,        -- NULL = never expires
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audit log (every state change)
CREATE TABLE billing_audit_log (
    log_id          BIGSERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL,
    entity_type     TEXT NOT NULL,       -- 'subscription', 'invoice', 'credit'
    entity_id       TEXT NOT NULL,
    action          TEXT NOT NULL,       -- 'created', 'updated', 'status_changed'
    old_value       JSONB,
    new_value       JSONB,
    actor           TEXT NOT NULL,       -- 'system', 'user:u_123', 'webhook:evt_123'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### Step 8: Error Handling and Recovery (3 min)

**Payment failure dunning workflow (Temporal):**

```
Dunning Workflow (started by payment_failed signal):
    Day 0: Payment fails. Mark subscription as PAST_DUE.
           Send email: "Payment failed, please update your card."
    Day 3: Retry payment (activity).
           If success: mark ACTIVE, send "payment recovered" email.
           If fail: send "second attempt failed" email.
    Day 7: Retry payment.
           If success: mark ACTIVE.
           If fail: send "final warning -- service will be suspended" email.
    Day 10: Retry payment.
           If success: mark ACTIVE.
           If fail: mark SUSPENDED. Downgrade to free tier entitlements.
           Send "account suspended" email.
    Day 30: If still suspended, mark CANCELLED.

    At any point: if customer updates payment method (signal),
    immediately retry and resume normal billing if successful.
```

**Marketplace-specific failure handling:**
- AWS: if BatchMeterUsage fails, queue for retry. If it fails for >6 hours, alert -- you'll lose the ability to bill for that usage.
- GCP: if entitlement sync fails, the customer may have access without being billed. Alert immediately.
- All channels: if reconciliation detects a missing report, file a correction within the marketplace's correction window.

---

### Step 9: Monitoring for Billing Correctness (3 min)

**Revenue integrity dashboard:**
- Total MRR by channel, updated daily
- MRR changes broken down by: new, expansion, contraction, churn, reactivation
- Invoice success rate (invoices generated / invoices paid)
- Average time from invoice generation to payment

**Operational alerts:**
- Any reconciliation discrepancy > $10
- Payment failure rate > 5% in any 1-hour window
- Marketplace metering report failure (any)
- Invoice generation failure (any)
- Ledger imbalance (any -- this should never happen)
- Credit balance anomalies (negative remaining, credits without matching ledger entries)

---

## Design Exercise 3: Cloud Nexus -- Multi-Cloud Connectivity Platform

**The prompt:** "Design Cloud Nexus, a platform that enables Temporal customers to connect applications across clouds, regions, and teams through a unified, self-service API. Must support namespace discovery, cross-region routing, and access control."

**Time budget (45-minute interview):**
- Requirements clarification: 3 minutes
- High-level architecture: 7 minutes
- Deep dives (API design, routing, access control): 18 minutes
- Self-service onboarding: 5 minutes
- Observability: 5 minutes
- Failure modes: 5 minutes
- Tradeoffs: 2 minutes

---

### Step 1: Requirements Clarification (3 min)

**Functional:**
- "What does 'connect applications across clouds' mean concretely? I'm interpreting this as: a workflow in AWS us-east-1 can start a child workflow or call an activity in GCP europe-west1, transparently."
- "Is this connecting Temporal namespaces across different Temporal Cloud deployments, or connecting Temporal to non-Temporal services?"
- "What's the access control model? Organization-level? Namespace-level? Workflow-level?"
- "Is this for Temporal Cloud customers only, or also for self-hosted Temporal users connecting to Cloud?"

**Non-functional:**
- "What's the latency budget for cross-region routing? An additional 50ms on top of network latency?"
- "How many customers and namespaces are we designing for?"
- "What's the availability target? 99.9%? 99.99%?"
- "Is there an existing connectivity layer we're building on, or is this greenfield?"

**Assumptions:**
- Cloud Nexus connects Temporal Cloud namespaces across regions and clouds.
- ~500 customers, ~5000 namespaces, growing to 50K namespaces in 18 months.
- Access control at namespace level with role-based policies.
- Target: 99.99% availability for the control plane, 99.999% for the data plane.
- Additional routing latency budget: <10ms within a region, <50ms cross-region.

---

### Step 2: High-Level Architecture (7 min)

```
                         Cloud Nexus Architecture
                         ========================

    Customer A (AWS)         Customer B (GCP)         Customer C (Azure)
    +--------------+         +--------------+         +--------------+
    | Namespace A1 |         | Namespace B1 |         | Namespace C1 |
    | (us-east-1)  |         | (eu-west-1)  |         | (westus2)    |
    +--------------+         +--------------+         +--------------+
          |                        |                        |
          v                        v                        v
    +-------------------------------------------------------------+
    |                     Data Plane (per region)                  |
    |  +------------------+  +------------------+  +-----------+  |
    |  | Nexus Proxy      |  | Nexus Proxy      |  | Nexus     |  |
    |  | (us-east-1)      |  | (eu-west-1)      |  | Proxy     |  |
    |  |                  |  |                  |  | (westus2) |  |
    |  | - Request routing|  | - Request routing|  |           |  |
    |  | - Auth enforcement| | - Auth enforcement| |           |  |
    |  | - Load balancing |  | - Load balancing |  |           |  |
    |  +--------+---------+  +--------+---------+  +-----+-----+  |
    |           |                     |                    |        |
    |           +----------+----------+--------------------+        |
    |                      |                                        |
    +-------------------------------------------------------------+
                           |
                           v
    +-------------------------------------------------------------+
    |                    Control Plane (global)                    |
    |                                                             |
    |  +------------------+  +------------------+  +-----------+  |
    |  | Registry Service |  | Policy Service   |  | Routing   |  |
    |  | - Namespace      |  | - Access control |  | Service   |  |
    |  |   registration   |  | - RBAC policies  |  | - Route   |  |
    |  | - Endpoint       |  | - Connection     |  |   tables  |  |
    |  |   discovery      |  |   approvals      |  | - Health  |  |
    |  |                  |  |                  |  |   checks  |  |
    |  +------------------+  +------------------+  +-----------+  |
    |                                                             |
    |  +------------------+  +------------------+                 |
    |  | Provisioning     |  | Billing          |                 |
    |  | Service          |  | Integration      |                 |
    |  | (Temporal wf)    |  | (metering)       |                 |
    |  +------------------+  +------------------+                 |
    |                                                             |
    +-------------------------------------------------------------+
                           |
                           v
    +-------------------------------------------------------------+
    |                    PostgreSQL (global)                       |
    |  Namespaces, connections, policies, routing rules            |
    +-------------------------------------------------------------+
```

**Separation of concerns:**
- **Control plane**: manages configuration, policies, and routing rules. Consistency > latency. Deployed globally with a primary region.
- **Data plane**: handles actual request routing. Latency-critical. Deployed in every region where customers operate. Caches routing rules and policies locally.
- **The data plane must function even if the control plane is temporarily unavailable** (cached policies, cached routes). This is the key availability design decision.

---

### Step 3: API Design (6 min)

**Core API (gRPC, with REST gateway):**

```protobuf
service NexusRegistryService {
    // Namespace management
    rpc RegisterNamespace(RegisterNamespaceRequest)
        returns (RegisterNamespaceResponse);
    rpc ListNamespaces(ListNamespacesRequest)
        returns (ListNamespacesResponse);
    rpc GetNamespace(GetNamespaceRequest)
        returns (GetNamespaceResponse);

    // Connection management
    rpc CreateConnection(CreateConnectionRequest)
        returns (CreateConnectionResponse);
    rpc ApproveConnection(ApproveConnectionRequest)
        returns (ApproveConnectionResponse);
    rpc ListConnections(ListConnectionsRequest)
        returns (ListConnectionsResponse);
    rpc DeleteConnection(DeleteConnectionRequest)
        returns (DeleteConnectionResponse);
}

service NexusRoutingService {
    // Route resolution (called by data plane)
    rpc ResolveRoute(ResolveRouteRequest)
        returns (ResolveRouteResponse);

    // Routing rules
    rpc CreateRoutingRule(CreateRoutingRuleRequest)
        returns (CreateRoutingRuleResponse);
    rpc ListRoutingRules(ListRoutingRulesRequest)
        returns (ListRoutingRulesResponse);
}

service NexusPolicyService {
    // Access policies
    rpc CreatePolicy(CreatePolicyRequest)
        returns (CreatePolicyResponse);
    rpc EvaluateAccess(EvaluateAccessRequest)
        returns (EvaluateAccessResponse);
}
```

**Connection model:**
```
Namespace A (owner: Org X) --- connection ---> Namespace B (owner: Org Y)

A connection is a declared intent for Namespace A to call Namespace B.
- The owner of Namespace B must approve the connection.
- Once approved, the data plane allows traffic from A to B.
- Connections are directional: A->B does not imply B->A.
- Connections can specify allowed operation types (workflow start,
  signal, query, activity via Nexus endpoint).
```

**Namespace registration:**
```json
{
  "namespace_id": "ns_abc123",
  "org_id": "org_xyz",
  "display_name": "payment-processing",
  "region": "us-east-1",
  "cloud": "aws",
  "endpoints": {
    "grpc": "ns-abc123.us-east-1.temporal.cloud:7233",
    "nexus": "ns-abc123.nexus.us-east-1.temporal.cloud:7243"
  },
  "visibility": "org_private",
  "tags": ["billing", "production"]
}
```

---

### Step 4: Tenant Isolation and Access Control (5 min)

**Access control model: Organization-scoped RBAC with namespace-level granularity.**

```
Policy structure:
{
  "policy_id": "pol_123",
  "source": {
    "org_id": "org_xyz",
    "namespace_pattern": "prod-*"    // glob matching
  },
  "target": {
    "org_id": "org_abc",
    "namespace_id": "ns_payments"
  },
  "allowed_operations": ["workflow.start", "workflow.signal"],
  "conditions": {
    "require_mtls": true,
    "allowed_workflow_types": ["ProcessPayment", "RefundPayment"]
  }
}
```

**Three levels of access control:**

1. **Connection approval** (control plane, human-in-the-loop):
   - Before any traffic flows, the target namespace owner must approve a connection request.
   - For intra-organization connections, auto-approval can be configured.
   - For cross-organization connections, always require explicit approval.

2. **Policy evaluation** (data plane, automated):
   - Every request through the data plane is evaluated against policies.
   - Policies are cached in the data plane with a TTL (30 seconds). Policy changes take up to 30 seconds to propagate.
   - Policy evaluation must be fast (<1ms) -- it's on the hot path.

3. **mTLS enforcement** (data plane, infrastructure):
   - Each namespace has a unique identity certificate issued by Temporal's CA.
   - Cross-namespace requests use mTLS. The data plane validates the source namespace's identity against the connection and policy.
   - This prevents namespace impersonation even if an attacker gains network access.

**Tenant isolation in the data plane:**
- Each customer's traffic is tagged with org_id and namespace_id.
- Rate limiting is per-namespace to prevent noisy neighbors.
- Resource quotas (max connections, max requests/sec) are per-org with overrides per namespace.
- Metrics and logs are scoped to the org. No cross-tenant data leakage in observability.

---

### Step 5: Multi-Region Routing (4 min)

**Route resolution:**
```
Source namespace (us-east-1) wants to call target namespace (eu-west-1):

1. Source worker makes Nexus call.
2. Local Nexus proxy (us-east-1) intercepts.
3. Proxy looks up routing table:
   - Target: ns_payments in eu-west-1
   - Route: nexus-proxy.eu-west-1.temporal.cloud:7243
4. Proxy forwards request to eu-west-1 proxy.
5. eu-west-1 proxy delivers to target namespace.
```

**Routing table design:**
```
+----------------+------------------+------------------+-----------+
| target_ns      | target_region    | proxy_endpoint    | priority  |
+----------------+------------------+------------------+-----------+
| ns_payments    | eu-west-1        | proxy.eu-west-1  | 1 (primary)|
| ns_payments    | us-east-1        | proxy.us-east-1  | 2 (failover)|
+----------------+------------------+------------------+-----------+
```

**Multi-region considerations:**
- Route tables are computed by the control plane and pushed to data plane proxies.
- Data plane proxies cache route tables locally. If the control plane is unavailable, stale routes continue to work.
- Health checks: the data plane monitors target endpoint health. If a primary route becomes unhealthy, fail over to the secondary route (if configured).
- Latency-based routing: if a namespace is deployed in multiple regions, route to the closest healthy instance.

**Cross-cloud routing:**
- AWS-to-GCP and GCP-to-AWS traffic flows over dedicated interconnects (if available) or over the public internet with mTLS.
- The proxy handles protocol translation if needed (though ideally all traffic is gRPC/mTLS).

---

### Step 6: Self-Service Onboarding (Temporal Workflow) (5 min)

**Onboarding workflow for a new Cloud Nexus customer:**

```
Workflow ID: "nexus-onboard-{org_id}"

Step 1: Validate prerequisites (activity)
    - Org has an active Temporal Cloud subscription
    - Org has at least one namespace
    - Nexus feature flag is enabled for this org

Step 2: Provision infrastructure (activity, may take minutes)
    - Allocate Nexus proxy capacity in the customer's primary region
    - Issue mTLS certificates for the org's namespaces
    - Create default policies (intra-org connections auto-approved)

Step 3: Register existing namespaces (activity)
    - Enumerate org's namespaces from Temporal Cloud control plane
    - Register each in the Nexus registry
    - Mark as "discoverable" within the org

Step 4: Enable billing (activity)
    - Add Nexus metering dimensions to the account
    - Start tracking Nexus API calls and data transfer

Step 5: Send welcome notification (activity)
    - Email with getting-started guide
    - In-app notification with Nexus dashboard link

Step 6: Wait for first connection (signal, with timeout)
    - If no connection created within 7 days, trigger a
      check-in email with onboarding help

Compensation:
    - If any step fails after retries:
      Step 5 fail: proceed (non-critical)
      Step 4 fail: disable Nexus feature, alert billing team
      Step 3 fail: retry, then disable and alert
      Step 2 fail: deallocate infrastructure, disable feature
```

**Why Temporal for onboarding:**
- Multi-step provisioning with external dependencies is exactly what Temporal is built for.
- If provisioning takes 5 minutes and the certificate issuance takes 2 minutes, the workflow just waits. No polling, no callback infrastructure, no lost state.
- If a step fails at 3am, the workflow retries automatically. If it exhausts retries, it pauses and alerts the on-call engineer who can investigate and signal the workflow to proceed or cancel.

---

### Step 7: Observability and Health Monitoring (5 min)

**Three pillars, Nexus-specific:**

**Metrics (Prometheus/Grafana):**
- `nexus_request_total{source_ns, target_ns, operation, status}` -- request count and error rate per connection
- `nexus_request_duration_seconds{source_ns, target_ns}` -- latency per connection (p50, p95, p99)
- `nexus_policy_evaluation_duration_seconds` -- policy evaluation latency (should be <1ms)
- `nexus_route_cache_hit_ratio` -- data plane cache effectiveness
- `nexus_active_connections` -- per org, for capacity planning
- `nexus_data_transfer_bytes{direction, region}` -- for billing and capacity

**Traces (OpenTelemetry):**
- Every cross-namespace request gets a trace ID that spans source -> proxy -> proxy -> target.
- Trace includes: policy evaluation time, route resolution time, network transit time, target processing time.
- Customers can see traces for their own namespaces in the Temporal Cloud UI.

**Logs (structured, JSON):**
- Policy denials logged with full context (source, target, policy that denied, reason).
- Connection state changes (approved, revoked, expired).
- Routing failovers (primary unhealthy, switched to secondary).

**Health monitoring:**
- Active health checks from each proxy to every target namespace it routes to. Frequency: every 10 seconds.
- Passive health checks: track error rates on live traffic. If error rate exceeds 50% over 30 seconds, mark route as degraded.
- Customer-facing status page showing per-region data plane health.
- Control plane health: API latency, database replication lag, certificate issuance latency.

---

### Step 8: Scale Considerations (3 min)

**Data plane scaling:**
- Each Nexus proxy is stateless (configuration cached from control plane). Horizontal scaling behind a load balancer.
- At 5000 namespaces with an average of 10 connections each, that's 50K active connections. Each proxy can handle ~10K concurrent connections. Deploy 5-10 proxies per region.
- For high-traffic connections, the proxy uses connection pooling to the target namespace. Multiple logical connections share physical gRPC connections.

**Control plane scaling:**
- The registry and policy services are read-heavy. Use read replicas for PostgreSQL.
- Route table computation is triggered by changes (new namespace, new connection, health status change). It's event-driven, not periodic.
- At 50K namespaces, the route table per region is ~50K entries * ~100 bytes = ~5MB. Fits comfortably in memory.

**Rate limiting:**
- Per-namespace rate limit: 1000 requests/sec by default (configurable).
- Per-org aggregate limit: 10000 requests/sec by default.
- Per-connection limit: configurable by the target namespace owner.
- Rate limiting is enforced at the source-side proxy (fail fast, don't waste cross-region bandwidth).

---

### Step 9: Failure Modes and Recovery (5 min)

**Failure mode 1: Control plane outage**
- Impact: no new connections, no policy changes, no new namespace registrations.
- Data plane continues operating with cached configuration. Existing connections work.
- Recovery: restore control plane. Data plane automatically syncs when control plane is back.
- Mitigation: multi-region control plane deployment with automatic failover.

**Failure mode 2: Data plane proxy failure in one region**
- Impact: cross-namespace requests to/from that region fail.
- Detection: health checks fail, upstream load balancer removes the proxy.
- Recovery: auto-scaling replaces the failed instance. New instance loads cached configuration from the control plane.
- Mitigation: multiple proxy instances per region behind a load balancer. Single instance failure is transparent.

**Failure mode 3: Network partition between regions**
- Impact: cross-region requests fail. Intra-region requests continue working.
- Detection: cross-region health checks fail. Alert fired.
- Recovery: if secondary routes exist (namespace deployed in multiple regions), traffic fails over. If no secondary route, requests fail with a clear error.
- Mitigation: detect and surface partition clearly. Don't let a partition in one pair of regions cascade to other regions.

**Failure mode 4: Certificate expiry or compromise**
- Impact: mTLS connections fail for affected namespaces.
- Detection: certificate expiry monitoring (alert 30 days, 7 days, 1 day before expiry). Compromise detected via anomaly detection or manual report.
- Recovery: auto-rotation for expiry (rotate 7 days before expiry). For compromise: emergency revocation via CRL/OCSP, re-issue new certificates, trigger rotation on all affected proxies.
- Mitigation: short-lived certificates (24-hour validity with auto-rotation) reduce the blast radius of compromise.

**Failure mode 5: Noisy neighbor saturating a proxy**
- Impact: other namespaces sharing the proxy experience increased latency.
- Detection: per-namespace metrics show one namespace consuming disproportionate resources.
- Recovery: rate limiting kicks in (configured per-namespace). If persistent, isolate the namespace to dedicated proxy instances.
- Mitigation: fair-queuing in the proxy. Per-namespace rate limits enforced before request processing.

---

### Tradeoffs and Alternatives (2 min)

**Tradeoffs made:**
- Cached policies (30-second TTL) vs. real-time policy enforcement: we accept a 30-second window where a revoked connection might still work. The alternative (real-time policy check against the control plane) adds latency and creates a control plane dependency on the hot path.
- gRPC-only data plane vs. multi-protocol: starting with gRPC simplifies the proxy. If customers need HTTP/REST or other protocols, add protocol translation later.
- Centralized control plane vs. per-region: a centralized control plane is simpler to build and reason about. If global latency becomes an issue for control plane operations, introduce regional control plane replicas with conflict-free replicated data types (CRDTs) for eventual consistency.

**Alternatives considered:**
- Service mesh (Istio/Envoy): provides mTLS, routing, and policy enforcement out of the box. But it's designed for intra-cluster networking, not cross-cloud/cross-org connectivity. Too much complexity, wrong abstraction level.
- DNS-based routing: simpler than a proxy layer but doesn't support per-request policy evaluation, doesn't provide observability at the request level, and DNS caching makes failover slow.
- Customer-managed VPN/peering: offload connectivity to customers. Simpler for Temporal but terrible customer experience and doesn't scale to hundreds of customers.
