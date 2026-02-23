# Interview Prep Cheat Sheet

> Scan this the morning of the interview. One-line answers, key numbers, templates, and
> a pre-flight checklist. Everything you need in one place.

---

## Table of Contents

1. [Quick-Fire Technical Answers](#quick-fire-technical-answers)
2. [System Design Template](#system-design-template)
3. [Key Numbers for Temporal's Domain](#key-numbers-for-temporals-domain)
4. [Questions to Ask the Interviewer](#questions-to-ask-the-interviewer)
5. [Values Alignment Cheat Sheet](#values-alignment-cheat-sheet)
6. [Red Flags to Avoid](#red-flags-to-avoid)
7. [Day-Before Checklist](#day-before-checklist)

---

## Quick-Fire Technical Answers

If a question comes up in rapid-fire or small-talk format, have a crisp 1-2 sentence answer ready.

### Temporal

| # | Question | Expert Answer |
|---|----------|---------------|
| 1 | What is Temporal? | A durable execution platform -- you write workflows as code, and Temporal guarantees they run to completion even through failures, restarts, and deployments. |
| 2 | How does replay work? | When a worker restarts, the SDK replays the workflow's event history through the function, returning previously recorded results for completed steps, to reconstruct in-memory state without re-executing side effects. |
| 3 | Why deterministic? | Replay must produce the same command sequence as the original execution. Non-deterministic code (random, wall clock, env vars) would diverge from the event history and break replay. |
| 4 | Signals vs queries vs updates? | Signals are async durable messages; queries are sync read-only state reads; updates are sync validated mutations with a response. |
| 5 | What is continue-as-new? | Completes the current execution and starts a new one with fresh event history, same workflow ID. Prevents unbounded history growth for long-running workflows. |
| 6 | Activity retry policy? | Configurable per-activity: initial interval, backoff coefficient, max interval, max attempts, non-retryable error types. Temporal retries automatically -- you don't write retry loops. |
| 7 | What are task queues? | Named queues that connect workflow/activity tasks to workers. Enable routing (GPU tasks to GPU workers), versioning, and load balancing. Workers poll their assigned queue. |
| 8 | How does versioning work? | `workflow.GetVersion()` branches workflow logic based on version. Old executions take the old path; new executions take the new path. Enables safe code changes for in-flight workflows. |
| 9 | What is a Nexus endpoint? | A Temporal primitive for cross-namespace and cross-cluster communication. It provides a typed, discoverable API boundary between namespaces, enabling modular architecture across teams. |

### Go

| # | Question | Expert Answer |
|---|----------|---------------|
| 10 | Goroutines vs threads? | Goroutines are user-space, ~2KB initial stack, M:N scheduled by the Go runtime onto OS threads. You can run millions; you can't run millions of threads. |
| 11 | How do channels work? | Typed, synchronized conduits between goroutines. Unbuffered channels block sender until receiver is ready; buffered channels block when full. `select` multiplexes across channels. |
| 12 | Error handling philosophy? | Errors are values, returned explicitly. Wrap with `fmt.Errorf("context: %w", err)` for chains. Check with `errors.Is()` and `errors.As()`. Reserve panic for programmer bugs only. |
| 13 | What is a context? | `context.Context` carries deadlines, cancellation signals, and request-scoped values across API boundaries. Every blocking call should accept and respect a context. |
| 14 | Interfaces in Go? | Implicitly satisfied -- no `implements` keyword. A type satisfies an interface by having the right methods. Keep interfaces small (1-3 methods). Define them at the consumer, not the producer. |
| 15 | Go memory model? | Goroutines sharing data must synchronize. Channels, mutexes, and atomics provide happens-before guarantees. The race detector (`-race` flag) catches violations at runtime. |

### Distributed Systems

| # | Question | Expert Answer |
|---|----------|---------------|
| 16 | CAP theorem? | During a network partition, choose consistency (reject requests) or availability (serve possibly stale data). Billing systems choose consistency -- wrong charges are worse than downtime. |
| 17 | Exactly-once delivery? | Impossible in distributed systems. Achieve effectively-exactly-once with at-least-once delivery plus idempotent processing (idempotency keys, dedup tables). |
| 18 | Saga pattern? | A sequence of local transactions with compensating actions. If step N fails, run compensations for steps N-1 through 1. Temporal workflows are a natural fit for orchestrating sagas. |
| 19 | Event sourcing? | Store state as an append-only sequence of events rather than mutable records. Rebuild current state by replaying events. Good for audit trails. Temporal's event history is essentially event sourcing for workflow state. |
| 20 | Consistent hashing? | Distributes keys across nodes with minimal redistribution when nodes join/leave. Used in Temporal's matching service to assign task queue partitions to nodes. |

### Billing & Payments

| # | Question | Expert Answer |
|---|----------|---------------|
| 21 | Double-entry bookkeeping? | Every transaction creates two entries: a debit and a credit. The total debits must always equal total credits. This invariant catches errors and prevents silent corruption. |
| 22 | Why integer money? | Floating point can't exactly represent 0.1. Use integer cents (or smallest currency unit) as `BIGINT`. $10.50 is stored as 1050. Never `FLOAT` or `DECIMAL` for money in transit. |
| 23 | Idempotency keys? | A unique identifier for each mutation request. If the same key is sent twice, the system returns the original result without re-executing. Stripe supports them natively with 24-hour dedup. |
| 24 | Proration? | Charging proportionally for partial billing periods during plan changes. Calculate: (days remaining / total days) * price difference. Always log the calculation for audit. |
| 25 | Webhook reliability? | Webhooks are at-least-once. Verify signatures, return 200 fast, process async, deduplicate by event ID, and run reconciliation jobs as a safety net for missed webhooks. |
| 26 | Revenue recognition? | Recognize revenue when service is delivered, not when payment is received (ASC 606). For usage-based: recognize as usage occurs. For subscriptions: recognize ratably over the period. |

---

## System Design Template

Use this structure for any system design interview. Timing for a 45-minute exercise.

### Phase 1: Clarify Requirements (2-3 min)

**Say out loud:** "Before I start designing, I want to make sure I understand the requirements."

Ask about:
- Functional scope: what does the system do? What are the core use cases?
- Scale: how many users, requests/sec, data volume?
- Latency: what's acceptable? Real-time vs. near-real-time vs. batch?
- Consistency: strong consistency required, or eventual is fine?
- Existing infrastructure: what's already built? What can we reuse?

State your assumptions clearly: "I'll assume X unless you tell me otherwise."

### Phase 2: High-Level Architecture (5 min)

Draw the major components and data flow. Use boxes and arrows. Name each component.

**Template:**
```
[Clients] --> [API Layer] --> [Service Layer] --> [Data Layer]
                                   |
                              [Async Processing]
                                   |
                              [External Systems]
```

Explain your key design decisions as you draw. Don't just draw silently.

### Phase 3: Deep Dive (15-18 min)

Pick 1-2 components and go deep. The interviewer may direct you, or you can ask: "Which area would you like me to dive into?"

For each component, cover:
- Data model (tables, schemas)
- API design (endpoints, request/response)
- Key algorithms or logic
- Error handling and edge cases

### Phase 4: Tradeoffs and Alternatives (3-5 min)

For every major decision, state the alternative and why you didn't choose it.

**Template:** "I chose X over Y because Z. If we needed A instead, we'd switch to Y."

### Phase 5: Operational Concerns (3-5 min)

Cover these even if not asked -- it signals senior thinking:
- How do you monitor this?
- How do you deploy changes safely?
- What are the failure modes?
- How does this scale to 10x?
- What's the on-call experience like?

---

## Key Numbers for Temporal's Domain

### Temporal Cloud

| Metric | Typical Value |
|--------|---------------|
| Workflow execution throughput | 1000s-10000s per second per namespace |
| Activity execution latency (platform) | <100ms overhead (excluding activity code) |
| Event history max size | 50K events or 50MB per execution |
| Signal delivery latency | <100ms (p99 within region) |
| Namespace limit (default) | Configurable per account |
| Worker long-poll timeout | 60 seconds |
| Visibility query latency | <1s for indexed queries |

### Stripe

| Metric | Value |
|--------|-------|
| API rate limit | 100 read requests/sec, 100 write requests/sec (per-key, burstable) |
| Webhook delivery timeout | 20 seconds (must return 2xx) |
| Webhook retry schedule | Up to 16 retries over ~3 days, exponential backoff |
| Idempotency key TTL | 24 hours |
| Invoice finalization window | Configurable (1 hour default after period end) |
| Payout schedule | 2 business days (US), varies by country |
| Payment intent confirmation | ~1-5 seconds for card payments |

### AWS Kinesis

| Metric | Value |
|--------|-------|
| Write throughput per shard | 1000 records/sec or 1 MB/sec |
| Read throughput per shard | 5 read transactions/sec, 2 MB/sec |
| Record max size | 1 MB |
| Retention | 24 hours default, up to 365 days |
| PutRecords batch size | Up to 500 records per call |
| Shard iterator expiry | 5 minutes |

### PostgreSQL

| Metric | Value |
|--------|-------|
| Max connections (RDS) | Depends on instance: db.r6g.xlarge = ~1200 |
| Transaction throughput | 10K-50K simple TPS on modern instances |
| Connection overhead | ~10MB RAM per connection |
| WAL write latency | <1ms (local SSD) |
| Replication lag (async) | Typically <100ms, can spike under load |
| JSONB query performance | Indexes on JSONB fields: ~1ms for point lookups |

---

## Questions to Ask the Interviewer

Pick 3-5 from these categories. Asking good questions signals genuine interest and seniority.

### About the Team

- "How is the billing/metering team structured? How many engineers, and what's the split between backend and infrastructure?"
- "What does the on-call rotation look like for billing infrastructure? What kinds of pages are most common?"
- "How does the team interact with the core Temporal server team? Shared codebase, separate repos, or service boundaries?"

### About Cloud Nexus

- "What's the current state of Cloud Nexus? Is it in private preview, GA, or still in design?"
- "What are the biggest technical challenges the team is facing with Nexus right now?"
- "How are customers adopting Nexus? What are the top use cases you're seeing?"
- "How does Nexus relate to the existing multi-cluster replication feature?"

### About the Billing Platform

- "What's the current billing stack? Are you on Stripe, a custom solution, or a mix?"
- "What's the biggest source of billing-related incidents or customer escalations?"
- "Are there any planned migrations or major refactors on the billing side?"
- "How do you handle marketplace billing reconciliation today?"

### About Engineering Culture

- "What does the design review process look like? RFCs, ADRs, informal discussions?"
- "How often does the team deploy to production? What does the deployment pipeline look like?"
- "How does Temporal handle incident response? Blameless postmortems?"
- "What does the interview process look like after this round? How many more steps?"

### About Growth and Impact

- "Where do you see the billing and metering platform in 12 months? What's the roadmap?"
- "What does success look like for someone in this role in the first 6 months?"
- "What's the biggest opportunity you see for improving the billing platform?"
- "How does the team prioritize between building new features and improving reliability?"

---

## Values Alignment Cheat Sheet

Temporal's values: **Curious**, **Driven**, **Collaborative**, **Genuine**, **Humble**.

For each value, have 1-2 stories ready. Map each to STAR format (Situation, Task, Action, Result).

| Value | Story Theme | Key Phrase to Work In |
|-------|-------------|----------------------|
| **Curious** | Learned Go/Temporal by reading source code, built prototypes | "I wanted to understand how it actually worked, not just how to use it" |
| **Curious** | Investigated a performance regression by profiling and tracing | "I kept pulling the thread until I found the root cause" |
| **Driven** | Shipped a billing migration under a tight deadline | "I broke it into phases with clear milestones and shipped each one" |
| **Driven** | Took ownership of a critical system no one else wanted to own | "Someone had to own it, and I was in the best position to do it right" |
| **Collaborative** | Worked with finance team on billing accuracy requirements | "Their domain expertise shaped the technical design in ways I wouldn't have found alone" |
| **Collaborative** | Aligned three teams on a shared API contract via an RFC | "I facilitated the discussion and made sure every team's constraints were represented" |
| **Genuine** | Caused a production incident, owned it in the postmortem | "I documented exactly what I did wrong and what systemic change would prevent it" |
| **Genuine** | Gave direct feedback to a peer about code quality | "I cared about their growth more than avoiding an awkward conversation" |
| **Humble** | Changed my architecture decision based on a junior engineer's insight | "They were right, and the system was better for it" |
| **Humble** | Joined a new team and spent the first month listening and learning | "I didn't assume my experience elsewhere made me an expert here" |

---

## Red Flags to Avoid

These will hurt you in an interview at Temporal. Be aware of them.

**Product knowledge:**
- Not knowing what Temporal does, or confusing it with a task queue like Celery.
- Not understanding why workflows must be deterministic.
- Describing Temporal as "just another workflow engine" without articulating durable execution.

**System design:**
- Jumping into solution mode without asking clarifying questions.
- Over-engineering when the prompt calls for simplicity. Not everything needs Kafka.
- Ignoring billing correctness: floating-point money, no deduplication, no reconciliation.
- Designing without discussing failure modes. "What happens when X fails?" should be in your design, not an afterthought.
- Not considering scale and cost. Handwaving about "we'll scale later" signals junior thinking.

**Technical depth:**
- Claiming Go experience but not knowing error wrapping, interfaces, or goroutine mechanics.
- Not understanding idempotency in the context of distributed billing.
- Using "exactly-once delivery" as if it's a thing that exists (it's effectively-exactly-once via idempotent processing).
- Ignoring operational concerns: monitoring, alerting, deployment safety, incident response.

**Behavioral:**
- Blaming others for failures or missed deadlines.
- Not having specific examples. "I'm a team player" without a story is meaningless.
- Being unable to describe a mistake you made. Everyone makes mistakes; the question is whether you learn from them.
- Badmouthing a current or former employer/colleague.
- Not asking questions at the end. It signals disinterest.

**Communication:**
- Monologuing for 10 minutes without checking if the interviewer wants to go deeper or move on.
- Getting defensive when challenged. Interviewers push back to test your reasoning, not to attack you.
- Using jargon without explaining it. Show that you can communicate with clarity.

---

## Day-Before Checklist

- [ ] Review Temporal docs: workflows, activities, workers, signals, queries, continue-as-new
- [ ] Re-read the job description. Highlight keywords and map them to your experience.
- [ ] Prepare 5 behavioral stories. Practice each in under 2 minutes using STAR.
- [ ] Walk through 1 system design out loud (the metering pipeline is the most likely). Time yourself.
- [ ] Prepare 5 questions to ask the interviewer. Write them on a notepad.
- [ ] Review Go concurrency patterns: goroutines, channels, select, sync.WaitGroup, context.
- [ ] Review Stripe basics: subscriptions, invoices, webhooks, idempotency keys.
- [ ] Test your setup: camera, mic, screen sharing, IDE (if live coding).
- [ ] Have water and a notepad ready.
- [ ] Sleep. Seriously. A well-rested brain outperforms a cramming brain every time.

---

## Morning-Of Reminders

1. **Breathe.** You're a senior engineer with 10+ years of experience. You belong in this interview.
2. **Think out loud.** The interviewer can't see your reasoning unless you share it.
3. **Ask questions.** Clarifying requirements isn't a sign of weakness -- it's a sign of seniority.
4. **It's okay to say "I don't know."** Follow it with "but here's how I'd figure it out."
5. **Be yourself.** Temporal values "genuine" explicitly. Authenticity beats performance.
