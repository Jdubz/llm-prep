# Module 07: Interview Prep

> The capstone module. Likely questions, strong answers, and behavioral prep -- all tailored
> for a Senior Software Engineer role on Temporal's billing, metering, and Cloud Nexus team.
> Read this the night before. Sound like the senior engineer you are, not a textbook.

---

## Table of Contents

1. [Temporal Product Knowledge](#temporal-product-knowledge)
2. [Go & Systems Questions](#go--systems-questions)
3. [Distributed Systems Questions](#distributed-systems-questions)
4. [Billing & Data Questions](#billing--data-questions)
5. [Production & Operations Questions](#production--operations-questions)
6. [Behavioral Questions](#behavioral-questions)

---

## Temporal Product Knowledge

### Q1: What is Temporal and how does it achieve durable execution?

**Strong opening:** "Temporal is an open-source durable execution platform that lets you write complex, long-running business logic as straightforward code -- no state machines, no retry scaffolding, no manual checkpointing."

**Key points to hit:**
- Temporal persists the state of workflow execution in an event history. If a worker crashes mid-execution, another worker picks up from the last recorded event -- not from the beginning.
- Workflows are functions that look like normal code (sequential, with loops, conditionals, error handling) but the Temporal server durably records every step.
- Activities are the side-effecting operations (API calls, DB writes, file IO). They run at-least-once with configurable retry policies. Workflows orchestrate activities.
- The server itself is a stateless, horizontally-scalable Go service backed by a persistence layer (Cassandra, MySQL, or PostgreSQL).
- This matters for billing because financial workflows (subscription lifecycle, invoice generation, payment processing) are exactly the kind of multi-step, failure-prone processes where durable execution eliminates an entire class of bugs.

**What the interviewer is really testing:** Do you understand the product at an architectural level, or did you just read the marketing page? Can you explain why durable execution is a paradigm shift, not just another workflow engine?

---

### Q2: How does workflow replay work? Why must workflows be deterministic?

**Strong opening:** "When a workflow worker restarts, Temporal replays the workflow's event history through the workflow function. Every decision the workflow previously made is already recorded -- replay just fast-forwards through those decisions to reconstruct the workflow's state in memory."

**Key points to hit:**
- The event history is the source of truth. It contains every command the workflow issued (schedule activity, start timer, send signal) and every result that came back.
- During replay, the SDK intercepts calls like `workflow.ExecuteActivity()` and, instead of actually scheduling the activity, returns the previously recorded result from the event history.
- Determinism is required because replay must produce the same sequence of commands as the original execution. If the workflow code branches differently on replay, the command sequence won't match the event history, and the SDK raises a non-deterministic error.
- Common determinism violations: using `time.Now()` instead of `workflow.Now()`, using random numbers without `workflow.SideEffect()`, reading environment variables that change between deployments, or making direct API calls from workflow code (should be activities).
- Versioning (`workflow.GetVersion()`) is the escape hatch -- it lets you change workflow logic while maintaining backward compatibility with in-flight workflows.

**What the interviewer is really testing:** Can you reason about replay mechanics? This separates candidates who've built with Temporal from those who've only read about it.

---

### Q3: How would you design a billing subscription lifecycle using Temporal workflows?

**Strong opening:** "A subscription lifecycle is a textbook Temporal use case -- it's long-running, has multiple state transitions, needs to survive failures, and involves coordinating external systems like Stripe and internal metering."

**Key points to hit:**
- The subscription workflow runs for the entire lifetime of a customer's subscription -- potentially months or years. It uses `continue-as-new` to prevent unbounded event history growth.
- The workflow blocks on signals for state transitions: upgrade, downgrade, cancel, payment method update. Each signal triggers the appropriate activities (update Stripe subscription, adjust metering thresholds, send notification).
- Activities handle all external calls: Stripe API, sending emails, updating the billing database. Each has its own retry policy tuned to the target system's characteristics.
- Timer-based billing cycles: the workflow sets a timer for the next billing date, wakes up, runs metering aggregation, generates an invoice, and processes payment.
- Queries expose current subscription state without affecting the workflow -- perfect for the dashboard showing "what plan is this customer on right now?"

**What the interviewer is really testing:** Can you map a real business process to Temporal primitives? Do you understand the long-running nature of subscription workflows and how continue-as-new manages that?

---

### Q4: What's the difference between signals, queries, and updates?

**Strong opening:** "Signals, queries, and updates are the three ways external code communicates with a running workflow, and each serves a fundamentally different purpose."

**Key points to hit:**
- **Signals** are asynchronous messages sent to a workflow. They are durably recorded in the event history and processed in order. The sender gets confirmation of delivery but not of processing. Use case: "customer upgraded their plan" or "payment succeeded."
- **Queries** are synchronous, read-only requests to inspect workflow state. They do not modify workflow state and are not recorded in the event history. Use case: "what's the current subscription status?" for a dashboard.
- **Updates** (newer feature) are synchronous, validated mutations. The workflow can accept or reject the update, and the caller waits for the result. They combine the mutation capability of signals with the synchronous response of queries. Use case: "apply this coupon and tell me the new price" where you need validation and a response.
- Signals are fire-and-forget; queries are read-only; updates are request-response mutations.
- In a billing context: signals for webhook events, queries for dashboard reads, updates for plan changes that need immediate confirmation.

**What the interviewer is really testing:** Do you understand the communication model between workflows and the outside world? This is a common source of design mistakes.

---

### Q5: When would you use continue-as-new vs child workflows?

**Strong opening:** "They solve different problems. Continue-as-new is about managing event history size for a single logical workflow. Child workflows are about decomposing a workflow into independent sub-units."

**Key points to hit:**
- **Continue-as-new** completes the current workflow execution and immediately starts a new one with fresh event history, passing along any state you choose. The workflow ID stays the same. Use it for long-running workflows (subscriptions, monitors) where the event history would grow unbounded.
- **Child workflows** are independent workflow executions started from a parent. They have their own event history, can be independently queried and signaled, and have configurable parent-close policies. Use them for fan-out (process 1000 invoices in parallel) or for isolating failure domains.
- In billing: a subscription workflow uses continue-as-new each billing cycle. Invoice generation might use child workflows to process each line item independently.
- Continue-as-new carries over state explicitly (you pass arguments). Child workflows communicate via their return value or through signals.
- A common mistake is using child workflows when you really need continue-as-new -- it creates unnecessary parent-child dependencies and complicates cancellation.

**What the interviewer is really testing:** Can you make the right architectural choice? This question distinguishes practical experience from theoretical knowledge.

---

## Go & Systems Questions

### Q6: Explain Go's concurrency model. How do goroutines differ from threads?

**Strong opening:** "Go's concurrency is built on goroutines and channels -- lightweight, runtime-managed concurrent functions that communicate through message passing rather than shared memory."

**Key points to hit:**
- Goroutines are multiplexed onto a small number of OS threads by the Go runtime scheduler (M:N scheduling). A typical Go program can run millions of goroutines on a handful of threads.
- Goroutines start with a ~2KB stack that grows dynamically (vs. 1-8MB fixed stack for OS threads). Creation cost is negligible -- no syscall, just a runtime allocation.
- Channels are typed conduits for communication between goroutines. They enforce synchronization without explicit locks. `select` enables waiting on multiple channels simultaneously.
- The Go runtime's scheduler uses work-stealing: idle threads steal goroutines from busy threads' local queues.
- Coming from Node.js, the mental model shift is: Node uses one thread with cooperative concurrency (async/await). Go uses many goroutines with preemptive scheduling -- a goroutine can be paused at function call boundaries without your code explicitly yielding.

**What the interviewer is really testing:** Do you understand why Go's model matters for systems programming? Can you articulate the tradeoffs vs. async/await models you know well?

---

### Q7: How do you handle errors in Go? What's the wrapping pattern?

**Strong opening:** "Go treats errors as values, not exceptions. Every function that can fail returns an error as its last return value, and you check it explicitly at every call site."

**Key points to hit:**
- The `if err != nil` pattern is idiomatic and intentional -- it forces you to handle every failure explicitly. Coming from TypeScript, where you might have try/catch at a high level, this feels verbose but produces more resilient code.
- Error wrapping with `fmt.Errorf("context: %w", err)` adds context while preserving the original error chain. You can later check for specific errors with `errors.Is()` or extract typed errors with `errors.As()`.
- Sentinel errors (`var ErrNotFound = errors.New("not found")`) are used for known, expected error conditions. Custom error types implement the `error` interface for errors carrying structured data.
- `panic`/`recover` exist but are reserved for truly unrecoverable situations (programmer bugs, not operational errors). Using panic for control flow is an anti-pattern.
- In billing code, error wrapping is critical -- "failed to charge customer" is useless; "failed to charge customer cust_123: stripe: card_declined: insufficient_funds" tells you exactly what happened.

**What the interviewer is really testing:** Can you write idiomatic Go, or will you fight the language's conventions?

---

### Q8: How would you design a gRPC service in Go?

**Strong opening:** "I'd start with the proto definitions as the contract, generate Go code, implement the service interface, and wire it up with interceptors for observability and auth."

**Key points to hit:**
- Define the service in `.proto` files first -- this is the API contract. Use `buf` for linting, breaking change detection, and code generation. Versioning via package names (`billing.v1`).
- Implement the generated service interface. Each RPC method is a Go function with a context and request, returning a response and error.
- Interceptors (middleware) handle cross-cutting concerns: logging, metrics, auth token validation, request ID propagation. Unary interceptors for single-request RPCs, stream interceptors for streaming.
- Use `grpc-gateway` if you need REST compatibility alongside gRPC -- common for customer-facing billing APIs where some clients can't speak gRPC.
- Testing: use `bufconn` for in-memory gRPC testing without network overhead. Integration tests against a real server for end-to-end validation.

**What the interviewer is really testing:** Have you built production gRPC services, or just read the docs? Mentioning interceptors, buf, and testing strategies signals real experience.

---

### Q9: Walk me through how you'd test concurrent code in Go.

**Strong opening:** "Testing concurrent code requires a combination of race detection, deterministic test design, and tools that make non-determinism observable."

**Key points to hit:**
- Always run tests with `-race` flag. The race detector instruments memory accesses and reports data races with stack traces. It should be in your CI pipeline.
- Use channels or `sync.WaitGroup` to synchronize test assertions with goroutine completion. Never use `time.Sleep` to wait for goroutines -- it's flaky and slow.
- For deterministic testing, inject dependencies that control timing. Instead of `time.After(5 * time.Second)`, accept a timer interface you can control in tests.
- `t.Parallel()` runs test cases concurrently, which helps find races between tests sharing state (like database rows or global variables).
- For complex concurrent systems, table-driven tests with multiple goroutine interleavings can exercise different execution orders. Property-based testing with libraries like `gopter` can generate random interleavings.

**What the interviewer is really testing:** Do you know how to write reliable tests for concurrent systems, or do you just sprinkle goroutines and hope?

---

### Q10: How do you manage database connections and transactions in Go?

**Strong opening:** "Go's `database/sql` package provides connection pooling out of the box. The key is configuring pool limits appropriately and using transactions correctly to avoid connection leaks."

**Key points to hit:**
- `sql.DB` is a connection pool, not a single connection. Configure `SetMaxOpenConns`, `SetMaxIdleConns`, and `SetConnMaxLifetime` based on your database's connection limit and your service's concurrency.
- Transactions: `db.BeginTx(ctx, nil)` starts a transaction. Always `defer tx.Rollback()` immediately after -- if you commit successfully, the deferred rollback is a no-op. This pattern prevents leaked transactions on panics or early returns.
- Use context propagation for timeout and cancellation. If a request is cancelled, the context should cancel any in-flight database operations.
- For billing systems specifically: use `SERIALIZABLE` isolation level for financial operations where consistency is non-negotiable. Understand the performance cost and limit serializable transactions to the critical path.
- Libraries like `sqlx` add struct scanning and named parameters. `pgx` is the preferred PostgreSQL driver for performance-critical paths (connection pooling, COPY protocol, custom types).

**What the interviewer is really testing:** Can you build data-intensive Go services? Connection management mistakes are a common source of production incidents.

---

## Distributed Systems Questions

### Q11: How do you ensure exactly-once processing in a distributed pipeline?

**Strong opening:** "True exactly-once is impossible in a distributed system, but you can achieve effectively-exactly-once through idempotent operations combined with at-least-once delivery."

**Key points to hit:**
- The standard approach is: at-least-once delivery + idempotent processing = effectively-exactly-once semantics.
- Idempotency keys: assign a unique ID to each event. Before processing, check if that ID has been processed. Store the ID atomically with the result in the same transaction.
- For billing specifically: every charge attempt carries an idempotency key. Stripe supports idempotency keys natively -- pass the same key, get the same result, no double charge.
- Temporal achieves this through its event history -- activities run at-least-once, but the workflow's deterministic replay ensures each activity's result is used exactly once in the workflow logic.
- Watch out for side effects outside the idempotency boundary: if you send an email and then write the idempotency key, a crash between those two steps means a re-sent email.

**What the interviewer is really testing:** Do you understand the fundamental impossibility and the practical workaround? Candidates who say "just use a message queue with exactly-once" don't understand distributed systems.

---

### Q12: Design a system that handles late-arriving events in a metering pipeline.

**Strong opening:** "Late-arriving events are inevitable in any distributed metering system. The design needs to handle them gracefully without sacrificing billing accuracy or introducing unbounded reprocessing."

**Key points to hit:**
- Define a watermark: a timestamp that says "we believe we've received all events up to this point." Events arriving after the watermark are late. The watermark advances based on observed event timestamps and a configurable grace period.
- Late events within a grace period (say, 15 minutes): fold them into the current aggregation window. This is the common case -- network delays, brief worker restarts.
- Late events beyond the grace period: write them to a correction log. Process corrections asynchronously and generate credit/debit adjustments for the next billing cycle.
- For billing accuracy: maintain two views. The "real-time" view powers dashboards and alerting. The "billing" view is finalized at invoice time after the grace period closes, incorporating all corrections.
- Monitor late event rates and latency distributions. A spike in late events signals an upstream problem (failing producer, network partition, clock skew).

**What the interviewer is really testing:** Can you reason about time in distributed systems? Do you understand that "wait for everything" is not a viable strategy, and that you need explicit policies for lateness?

---

### Q13: How do you handle distributed transactions across services?

**Strong opening:** "You avoid them whenever possible. But when you need cross-service consistency, the Saga pattern with compensating transactions is the most practical approach -- and it's exactly what Temporal workflows excel at."

**Key points to hit:**
- Two-phase commit (2PC) requires all participants to be available and introduces a coordinator as a single point of failure. It doesn't work well across service boundaries.
- The Saga pattern: execute a sequence of local transactions. If any step fails, execute compensating transactions in reverse order to undo the completed steps.
- Temporal makes sagas straightforward: each step is an activity, and the workflow orchestrates the sequence. If an activity fails after retries are exhausted, the workflow executes compensation activities. The event history ensures no step is missed.
- Example in billing: create subscription in database, provision in Stripe, update entitlements, send welcome email. If Stripe provisioning fails, the compensation rolls back the database record.
- Eventual consistency is acceptable for most billing operations. Customers don't need instant consistency -- they need correctness within the billing cycle.

**What the interviewer is really testing:** Do you reach for the right tool? Saying "use distributed transactions" is a red flag. Saying "use sagas, and here's how Temporal makes them reliable" shows you understand both the theory and the product.

---

### Q14: Explain CAP theorem and how it applies to billing systems.

**Strong opening:** "CAP says a distributed system can guarantee at most two of consistency, availability, and partition tolerance. Since partitions are inevitable, the real choice is between consistency and availability during a partition -- and for billing, you almost always choose consistency."

**Key points to hit:**
- During normal operation (no partition), you can have both consistency and availability. CAP only forces a tradeoff during network partitions.
- Billing systems are CP (consistency over availability): it's better to reject a transaction than to process it incorrectly. A customer seeing "service temporarily unavailable" is far better than being double-charged.
- This doesn't mean the entire system is CP. Read-heavy paths (usage dashboards, plan details) can be eventually consistent -- serve stale data from a cache, it's fine. Write paths (charges, refunds, plan changes) must be consistent.
- In practice: use a strongly consistent database (PostgreSQL with synchronous replication) for the billing ledger. Use eventually consistent stores (Redis, CDN) for read-heavy, non-critical paths.
- PACELC extends CAP: even without partitions, there's a latency vs. consistency tradeoff. Billing accepts higher latency for stronger consistency guarantees.

**What the interviewer is really testing:** Can you apply theoretical concepts to real systems? Can you make nuanced decisions rather than blanket statements?

---

### Q15: How do you handle partial failures in a multi-step onboarding flow?

**Strong opening:** "Partial failures are the default state of distributed systems. The onboarding flow needs to be designed so that every step is either retryable or has a compensating action, and the overall flow can resume from any point of failure."

**Key points to hit:**
- Model the onboarding as a Temporal workflow. Each step (create account, provision namespace, configure billing, set up monitoring, send welcome email) is a separate activity with its own retry policy.
- Persist the onboarding state so it can resume after any failure. The workflow's event history handles this automatically.
- Compensating actions for each step: if namespace provisioning fails, mark the account as "pending" rather than leaving a half-created account. If billing setup fails, don't leave a provisioned namespace that no one will pay for.
- Use a human-in-the-loop signal for steps that can't be automatically resolved. The workflow pauses and sends an alert; an operator investigates and sends a signal to proceed or cancel.
- Monitor completion rates and time-to-complete. A drop in completion rate signals a systemic issue (external API down, configuration error).

**What the interviewer is really testing:** Do you think about failure modes during design, or do you bolt on error handling as an afterthought? For a billing team, failure handling IS the product.

---

## Billing & Data Questions

### Q16: Design a metering pipeline for a usage-based SaaS product.

**Strong opening:** "A metering pipeline needs to be accurate above all else -- revenue depends on it. I'd design it with a write-ahead pattern: capture raw events first, aggregate second, bill third."

**Key points to hit:**
- Raw event capture: every billable action (workflow execution started, activity completed, namespace action) produces an event with a unique ID, timestamp, tenant ID, and action type. Write to a durable log (Kinesis, Kafka) before acknowledging.
- Aggregation: periodically roll up raw events into usage summaries per tenant per billing period. Use Temporal workflows for reliable aggregation -- they handle retries, checkpointing, and exactly-once semantics.
- Deduplication: use the unique event ID. Before aggregating, check the event hasn't already been counted. Store processed event IDs in a set with TTL.
- Storage: raw events in S3 for audit trail and reprocessing. Aggregated usage in PostgreSQL for billing queries. Pre-computed dashboards in a time-series store or materialized views.
- Reconciliation: regularly compare raw event counts against aggregated totals. Any discrepancy triggers an alert and a correction workflow.

**What the interviewer is really testing:** Can you design a system where money depends on correctness? Do you think about auditability, deduplication, and reconciliation?

---

### Q17: How would you handle Stripe webhook failures and ensure data consistency?

**Strong opening:** "Stripe's webhook delivery is at-least-once, and webhooks can arrive out of order. The system needs to be idempotent, handle redelivery, and reconcile against the Stripe API as a fallback."

**Key points to hit:**
- Verify the webhook signature using Stripe's signing secret. Return 200 immediately after basic validation -- do the heavy processing asynchronously to avoid timeouts (Stripe retries on timeout).
- Idempotency: store the Stripe event ID. Before processing, check if you've already handled this event. Process each event in a transaction that writes both the business result and the event ID.
- Out-of-order handling: use the event's `created` timestamp and the object's version. If you receive `invoice.paid` before `invoice.created`, either queue it for retry or fetch the current state from the Stripe API.
- Reconciliation: run a periodic job that fetches recent objects from the Stripe API and compares them against your local state. This catches missed webhooks, processing errors, and manual Stripe dashboard changes.
- Stripe retries webhooks up to ~16 times over 3 days with exponential backoff. Monitor your webhook success rate in the Stripe dashboard -- consistently failing webhooks indicate a bug in your handler.

**What the interviewer is really testing:** Have you built real Stripe integrations? The out-of-order and reconciliation points separate experienced engineers from those who've only done basic checkout flows.

---

### Q18: How do you prevent double-charging in a billing system?

**Strong opening:** "Double-charging prevention is a multi-layer defense: idempotency keys on payment requests, ledger-based accounting, and automated reconciliation."

**Key points to hit:**
- Layer 1 -- Idempotency keys: every charge attempt uses a deterministic idempotency key (e.g., `charge_{customer_id}_{invoice_id}_{attempt}`). Stripe deduplicates requests with the same key within 24 hours.
- Layer 2 -- Ledger model: use double-entry bookkeeping. Every charge creates a debit on the customer's account and a credit to revenue. The ledger must always balance. A double charge would create an imbalanced ledger, which is detectable.
- Layer 3 -- State machine: an invoice progresses through states (draft -> finalized -> payment_pending -> paid). Only a finalized invoice can transition to payment_pending. The state transition is guarded by a database-level constraint.
- Layer 4 -- Reconciliation: daily job compares your ledger against Stripe's records. Any discrepancy triggers an alert, and the system auto-generates a refund or credit if a double charge is detected.
- Layer 5 -- Circuit breaker: if the payment service returns ambiguous responses (timeouts, 5xx without a clear idempotency key match), halt and alert rather than retrying blindly.

**What the interviewer is really testing:** Do you think in layers of defense? Anyone can say "idempotency keys." Showing a defense-in-depth approach demonstrates you've thought about what happens when any single layer fails.

---

### Q19: Design the data model for a multi-tenant billing system.

**Strong opening:** "The data model needs to cleanly separate organizational hierarchy from billing constructs while maintaining a strict audit trail. Every mutation to billing state should be append-only."

**Key points to hit:**
- **Organizations**: `org_id`, name, metadata. The top-level tenant.
- **Accounts**: `account_id`, `org_id`. A billing entity. One org can have multiple accounts (e.g., separate accounts for different departments or billing channels -- direct vs marketplace).
- **Subscriptions**: `subscription_id`, `account_id`, `plan_id`, status, current_period_start, current_period_end. Links to the external provider (Stripe subscription ID, marketplace entitlement ID).
- **Usage records**: `usage_id`, `account_id`, metric, quantity, timestamp, idempotency_key. Append-only. Never update a usage record -- create a correction record instead.
- **Invoices**: `invoice_id`, `account_id`, period, status, line items (as JSONB or a line_items table). Invoice status follows a strict state machine.
- **Ledger entries**: `entry_id`, `account_id`, type (debit/credit), amount_cents (integer, never float), currency, description, reference_id. The source of truth for all financial state.
- Always store monetary amounts as integers (cents). Use `BIGINT` for the column type. Never use floating-point for money.

**What the interviewer is really testing:** Do you understand billing domain modeling? Key signals: integer money, append-only records, ledger-based accounting, multi-tenant hierarchy.

---

### Q20: How would you migrate from one billing provider to another?

**Strong opening:** "Billing migrations are among the hardest operational challenges because you can't have downtime, you can't lose data, and customers are directly impacted by any error. I'd approach it as a gradual, dual-write migration."

**Key points to hit:**
- Phase 1 -- Abstract: build a billing provider interface that your code depends on. If it doesn't already exist, refactor to create one. Both old and new providers implement this interface.
- Phase 2 -- Dual-write: new subscriptions go to both providers. The old provider is authoritative. Compare results to validate the new provider's behavior matches expectations.
- Phase 3 -- Shadow-read: start reading from the new provider but validate against the old. Log discrepancies. Don't serve the new provider's data to users yet.
- Phase 4 -- Gradual cutover: migrate a small cohort of customers to the new provider as authoritative. Monitor closely. Expand the cohort over weeks.
- Phase 5 -- Cleanup: once all customers are on the new provider, remove the old provider integration. Keep the abstraction layer.
- Critical: maintain the ability to roll back at every phase. Never burn the bridge to the old provider until you're confident the new one is correct.

**What the interviewer is really testing:** Can you plan a high-stakes migration? Do you think in phases with rollback points? Billing migrations with a big-bang cutover are career-ending events.

---

## Production & Operations Questions

### Q21: How do you ensure a billing pipeline is correct? What monitoring do you set up?

**Strong opening:** "Billing correctness monitoring is unique because the cost of a missed alert is real money -- either lost revenue or customer overcharges. I set up monitoring at every layer: input, processing, output, and reconciliation."

**Key points to hit:**
- **Input monitoring**: event ingestion rate per tenant, per metric. Alert on sudden drops (lost events) or spikes (duplicate events or runaway processes).
- **Processing monitoring**: aggregation job completion time, success rate, and throughput. Alert if jobs are consistently slow (upstream latency) or failing (code bug, dependency down).
- **Output monitoring**: invoice amounts compared to historical patterns. Flag invoices that are 2x or more above the previous period for the same customer -- could be legitimate growth, could be a metering bug.
- **Reconciliation**: automated comparison between raw event counts and aggregated totals. Between your ledger and Stripe's records. Between your reported usage and the customer's self-reported usage (if available).
- **Financial alerts**: total daily revenue outside expected bounds, large single charges above a threshold, high refund rate, payment failure rate above baseline.
- Use anomaly detection, not just static thresholds. A 10% drop in events from a small customer is noise; a 10% drop from your largest customer is a crisis.

**What the interviewer is really testing:** Do you treat billing as a financial system requiring audit-grade monitoring, or as just another CRUD service?

---

### Q22: Walk me through how you'd investigate a billing discrepancy.

**Strong opening:** "I'd start from the customer-visible symptom and work backward through the pipeline, checking each boundary: invoice, aggregated usage, raw events, and upstream sources."

**Key points to hit:**
- Step 1: Reproduce the discrepancy. Pull the customer's invoice, identify the disputed line item, and note the billed quantity and amount.
- Step 2: Check the aggregated usage for that period. Does the aggregation match the invoice? If not, the bug is in invoice generation.
- Step 3: Check raw events against the aggregation. Re-aggregate from raw events and compare. If they differ, the aggregation pipeline has a bug (duplicate processing, missed events, incorrect rollup logic).
- Step 4: Check raw event capture against the upstream source. Were all events captured? Were any duplicated? Compare event counts at the source with event counts in your pipeline.
- Step 5: Check for known issues -- late-arriving events after the billing window closed, timezone bugs (the #1 billing bug), off-by-one errors in period boundaries, currency conversion errors.
- Document everything. Billing discrepancy investigations become audit evidence. Write up the root cause, the customer impact, and the fix.

**What the interviewer is really testing:** Can you debug systematically through a complex pipeline? Do you think about documentation and audit trails?

---

### Q23: How would you design for multi-cloud support in a billing system?

**Strong opening:** "Multi-cloud billing means your customers can come through different channels -- direct sign-up, AWS Marketplace, GCP Marketplace, Azure Marketplace -- and each channel has its own billing mechanics, but the customer experience should be unified."

**Key points to hit:**
- Build a billing abstraction layer with channel-specific adapters. The core billing logic (metering, aggregation, invoicing) is channel-agnostic. Adapters handle the specifics: Stripe for direct, AWS Marketplace metering API, GCP procurement API, Azure partner center.
- Each marketplace has its own entitlement flow. AWS uses SaaS contracts/subscriptions with a fulfillment lambda. GCP has a procurement API with approval workflows. Azure has partner center APIs. All funnel into the same internal subscription model.
- Metering must be unified: regardless of channel, the same metering pipeline produces usage records. The difference is where the bill goes -- Stripe invoice vs. marketplace metering report.
- Reconciliation is critical and harder: you're reconciling against multiple external systems, each with different reporting cadences and data formats.
- Consider that marketplace customers may have different pricing (marketplace fees, negotiated rates) and different billing cycles.

**What the interviewer is really testing:** Do you understand the complexity of marketplace integrations? This is directly relevant to Temporal Cloud, which sells through marketplaces.

---

### Q24: What's your approach to zero-downtime deployments for financial systems?

**Strong opening:** "For billing systems, zero-downtime isn't just about uptime -- it's about ensuring no transactions are lost, duplicated, or corrupted during deployment. Every deployment is a potential billing correctness risk."

**Key points to hit:**
- Blue-green or canary deployments with traffic shifting. Never all-at-once. Start with a small percentage of traffic and monitor billing metrics before expanding.
- Database migrations must be backward-compatible. Use the expand-contract pattern: add the new column (nullable or with default), deploy code that writes to both, backfill, deploy code that reads from new column, drop the old column. Never rename or drop a column in the same release as the code change.
- For Temporal workers: rolling deployments with versioning. In-flight workflows continue on the old version. New workflow starts pick up the new version. Use `workflow.GetVersion()` for breaking changes to workflow logic.
- Drain queues and in-flight transactions before shutting down old instances. Implement graceful shutdown: stop accepting new work, finish in-progress work, then terminate.
- Pre-deployment: run the new version in shadow mode against production traffic. Compare its outputs to the current version. Only deploy if outputs match.

**What the interviewer is really testing:** Do you understand the deployment risks specific to financial systems? Generic deployment strategies aren't enough -- you need to explain what makes billing deployments uniquely dangerous.

---

## Behavioral Questions

> Temporal's core values are: **Curious**, **Driven**, **Collaborative**, **Genuine**, and **Humble**.
> Every behavioral question maps to one or more of these values. Your answers should demonstrate
> the value without explicitly naming it.

---

### Curious

#### "Tell me about a time you dove deep into a technology you didn't know."

**STAR Framework:**
- **Situation:** Set the context -- what was the technology and why did you need to learn it?
- **Task:** What was the specific challenge that required deep knowledge, not just surface-level use?
- **Action:** How did you learn? Reading source code, building prototypes, talking to experts? Be specific about your learning process.
- **Result:** What did you build or decide? How did the deep understanding change the outcome?

**Tips:**
- Pick a technology adjacent to the role -- Go, gRPC, distributed systems, or billing infrastructure.
- Show that you went beyond tutorials -- reading source code, understanding internals, contributing back.
- Connect the curiosity to a business outcome, not just personal growth.
- "I read the Temporal SDK source code to understand how replay works" would be a strong answer for this team.

#### "How do you stay current with new technologies?"

**STAR Framework:**
- **Situation:** Describe your learning system, not a one-off event.
- **Task:** How do you filter signal from noise in a constantly changing landscape?
- **Action:** Be specific: do you read RFCs, follow mailing lists, build side projects, contribute to OSS?
- **Result:** Give a concrete example where staying current directly benefited your team.

**Tips:**
- Avoid generic answers ("I read Hacker News"). Be specific about what you follow and why.
- Mention how you evaluate whether a new technology is worth investing in.
- Show that you share what you learn with your team -- curiosity that benefits the group.

---

### Driven

#### "Describe a project where you had to push through significant obstacles."

**STAR Framework:**
- **Situation:** A project with real stakes and real blockers. Technical debt, organizational resistance, unclear requirements.
- **Task:** What was the goal and why was it important? What made it hard?
- **Action:** What specific obstacles did you overcome and how? Be honest about setbacks.
- **Result:** Quantify the impact. Revenue saved, incidents prevented, developer hours recovered.

**Tips:**
- Choose a project with both technical and organizational complexity.
- Show persistence without stubbornness -- you adapted your approach when things weren't working.
- For a billing team, a story about fixing a critical financial bug or migrating a payment system would resonate.

#### "Tell me about a time you took ownership of something outside your role."

**STAR Framework:**
- **Situation:** Something was broken or missing, and it wasn't anyone's explicit responsibility.
- **Task:** Why did you decide to take it on? What was the risk of inaction?
- **Action:** How did you scope the work, get buy-in, and execute?
- **Result:** What was the outcome and how was ownership formalized afterward?

**Tips:**
- Show initiative without being a cowboy. You identified the gap and took ownership with communication.
- Best answers involve creating lasting improvements (documentation, automation, processes) rather than one-off heroics.

---

### Collaborative

#### "How do you work with non-engineering stakeholders (finance, sales)?"

**STAR Framework:**
- **Situation:** A project that required close collaboration with non-technical teams.
- **Task:** What was the communication challenge? Different vocabularies, different priorities, different timelines.
- **Action:** How did you bridge the gap? Shared documents, regular syncs, prototypes, translated technical constraints into business terms.
- **Result:** A better outcome because of the collaboration, not despite it.

**Tips:**
- This is highly relevant for a billing team -- you'll work directly with finance and sales.
- Show that you listened to their constraints and incorporated them, not just translated your technical plan into simpler words.
- Specific example: working with finance on billing accuracy requirements, or with sales on pricing model feasibility.

#### "Tell me about a time you had to align multiple teams on a technical decision."

**STAR Framework:**
- **Situation:** A decision that affected multiple teams with different priorities.
- **Task:** What was the decision and why couldn't one team make it unilaterally?
- **Action:** How did you build consensus? RFC, proof of concept, data-driven comparison, facilitated discussion?
- **Result:** The decision was made, teams aligned, and the outcome was better for the collaboration.

**Tips:**
- Show the process, not just the outcome. How you align matters more than what you aligned on.
- Demonstrate that you can disagree and commit -- not every decision will go your way.
- RFCs and design docs are strong signals for a systems-oriented team like Temporal's.

---

### Genuine

#### "Tell me about a time you made a mistake. How did you handle it?"

**STAR Framework:**
- **Situation:** A real mistake with real consequences. Not a humble brag.
- **Task:** What was the impact? Who was affected?
- **Action:** How did you respond? Immediate remediation, honest communication, root cause analysis.
- **Result:** What systemic change did you make to prevent recurrence? What did you learn?

**Tips:**
- Pick a genuine mistake, not "I worked too hard" or "I was too detail-oriented."
- Show accountability: you owned it, communicated it, and fixed it.
- For a billing team, a story about a production incident involving financial data would be credible and relatable.
- The best answers show vulnerability and growth without being self-deprecating.

#### "How do you give constructive feedback to a peer?"

**STAR Framework:**
- **Situation:** A specific instance where you gave feedback, not a general philosophy.
- **Task:** What was the behavior that needed to change? Why did it matter?
- **Action:** How did you deliver the feedback? Privately, with specific examples, focused on behavior not character.
- **Result:** How did the person respond? How did the relationship and their work improve?

**Tips:**
- Show that you give feedback because you care about the person's growth, not because you want to be right.
- Be specific about your feedback technique: SBI (Situation-Behavior-Impact) or similar.
- Demonstrate that you also ask for and receive feedback -- it's not a one-way street.

---

### Humble

#### "Tell me about a time you changed your mind based on someone else's input."

**STAR Framework:**
- **Situation:** You had a strong opinion or a plan you were committed to.
- **Task:** What was the decision and why did it matter?
- **Action:** What input changed your mind? Was it data, a perspective you hadn't considered, or experience you lacked?
- **Result:** The outcome was better because you changed course. Acknowledge the other person's contribution.

**Tips:**
- This is about intellectual honesty, not indecisiveness.
- Show that you can hold strong opinions loosely. You advocated for your position but were open to being wrong.
- Technical examples work well: "I was convinced we should use Kafka, but a colleague made a compelling case for Kinesis because..."

#### "How do you handle disagreements about technical direction?"

**STAR Framework:**
- **Situation:** A real disagreement, not a thought experiment.
- **Task:** What were the competing approaches and what were the stakes?
- **Action:** How did you engage? Data-driven arguments, prototypes, seeking outside perspectives, or committing to a time-boxed experiment.
- **Result:** How was it resolved? Even if your approach wasn't chosen, what did you learn?

**Tips:**
- Show that you can disagree without being disagreeable.
- Demonstrate that you optimize for the team's outcome, not for being right.
- The strongest answer shows you advocated for your position with evidence, accepted the group's decision, and supported the chosen direction wholeheartedly.
- Never badmouth a former colleague's decision, even in a hypothetical retelling.

---

## General Behavioral Tips

**For every behavioral answer:**
1. Keep it under 2 minutes. Practice with a timer.
2. Use specific names, dates, and metrics. Vague stories are forgettable.
3. End with what you learned or what changed systemically -- not just "it worked out."
4. Have 5-6 stories total that you can adapt to different questions. You don't need a unique story for every question.
5. If you don't have a perfect story, say so and give the closest one. Interviewers respect honesty over fabrication.

**Story bank checklist:**
- [ ] A technical deep-dive story (Curious)
- [ ] A push-through-obstacles story (Driven)
- [ ] A cross-team collaboration story (Collaborative)
- [ ] A mistake-and-recovery story (Genuine)
- [ ] A changed-my-mind story (Humble)
- [ ] A production incident story (covers multiple values)
