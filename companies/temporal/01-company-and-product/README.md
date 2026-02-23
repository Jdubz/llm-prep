# Module 01: Company & Product -- Core Interview Knowledge

## Why This Module Matters

When you sit across from a Temporal interviewer, the first thing they are evaluating is
whether you actually understand what Temporal does and why it exists. This is not a
trivia test -- it is a proxy for genuine interest and the ability to reason about the
problem space. If you can articulate why durable execution matters, how the business
model works, and where the billing/metering team fits into the picture, you are already
ahead of most candidates.

This module covers what you need to know cold before your first conversation.

---

## Table of Contents

1. [Company Overview](#company-overview)
2. [The Problem Temporal Solves](#the-problem-temporal-solves)
3. [Product Understanding](#product-understanding)
4. [Business Model](#business-model)
5. [Competitive Landscape](#competitive-landscape)
6. [Culture and Values](#culture-and-values)
7. [Interview Signals](#interview-signals)

---

## Company Overview

### Origin Story

Temporal Technologies was founded in 2019 by **Maxim Fateev** (CEO/CTO) and
**Samar Abbas** (Co-Founder). Their story is worth knowing because it demonstrates
decades of conviction around one idea: reliable workflow execution.

**The timeline:**

- **2009 -- Amazon:** Fateev and Abbas meet while building Amazon Simple Workflow
  Service (SWF), one of the earliest managed workflow orchestration services.
- **2012-2015 -- Divergent paths:** Abbas joins Microsoft, works on Azure Service Bus,
  and builds the Durable Task Framework (DTF) during a hackathon. Fateev moves to
  Google to work on big data frameworks.
- **2015 -- Uber:** They reunite at Uber's new Seattle dev center. Frustrated by teams
  spending most of their time stitching together messaging queues, they build
  **Cadence** -- an open-source workflow engine that synthesizes lessons from SWF and
  DTF.
- **2019 -- Temporal:** They leave Uber to build Temporal as a standalone company,
  taking the Cadence concept further with a clean-room rewrite and a commercial
  cloud offering.

**Why this matters in interviews:** The founders have over three decades of combined
experience building workflow orchestration systems. Temporal is not a startup chasing
a trend -- it is the culmination of ideas that have been refined across Amazon,
Microsoft, Google, and Uber. When interviewers ask "Why Temporal?", connecting to
this lineage shows you understand the depth of the problem.

### Mission

Temporal's mission is to be the **reliable foundation in every developer's toolbox**.
The core thesis: developers should not have to be distributed systems experts to build
reliable applications. The platform should handle the hard parts -- failure recovery,
state persistence, retries, timeouts -- so engineers can focus on business logic.

### Funding History

| Round      | Date     | Amount   | Lead Investor(s)            | Valuation |
|------------|----------|----------|-----------------------------|-----------|
| Seed       | 2019     | $6.75M   | Amplify Partners            | --        |
| Series A   | Oct 2020 | $18.75M  | Sequoia Capital             | --        |
| Series B   | Feb 2022 | $103M    | Greenoaks Capital, Index    | $1.5B     |
| Series B+  | Feb 2023 | $75M     | (Extension, flat valuation) | $1.5B     |
| Series C   | Mar 2025 | $146M    | Various                     | $1.72B    |
| Secondary  | Oct 2025 | $105M    | GIC, Tiger Global, Index    | $2.5B     |
| Series D   | Jan 2026 | $300M    | Andreessen Horowitz         | $5.0B     |

Key investors across rounds: Sequoia Capital, Index Ventures, Greenoaks Capital,
Amplify Partners, Madrona Venture Group, Addition Ventures, GIC, Tiger Global, a16z.

**Reading the fundraising story:** The flat Series B extension in 2023 happened during
the broader tech downturn. The subsequent re-acceleration -- $146M Series C, $105M
secondary, and a $300M Series D doubling the valuation to $5B -- signals that Temporal
Cloud revenue growth caught up with the earlier valuation. The Series D explicitly
positions Temporal as infrastructure for AI agents, which is the current growth vector.

### Company at a Glance

- **Headcount:** ~400 employees (as of early 2026)
- **HQ:** Seattle, WA (remote-first)
- **Open Source:** Temporal Server is MIT-licensed
- **Cloud:** Temporal Cloud is the commercial managed service
- **Key Customers:** Stripe, Netflix, Snap, Datadog, HashiCorp, Coinbase, and
  hundreds of others

---

## The Problem Temporal Solves

### The Distributed Systems Reliability Problem

As a senior full-stack engineer, you have lived this problem. Consider a typical
order processing flow in a Node.js/Express application:

```typescript
// The fragile way -- what every backend engineer has written
async function processOrder(order: Order) {
  try {
    const payment = await chargePayment(order);
    try {
      const inventory = await reserveInventory(order);
      try {
        const shipment = await createShipment(order);
        await sendConfirmationEmail(order, shipment);
      } catch (e) {
        await releaseInventory(inventory);
        await refundPayment(payment);
        throw e;
      }
    } catch (e) {
      await refundPayment(payment);
      throw e;
    }
  } catch (e) {
    await notifyFailure(order, e);
    throw e;
  }
}
```

This code has fundamental problems:

1. **What if the process crashes between `chargePayment` and `reserveInventory`?**
   The payment is charged but inventory is never reserved. No amount of try/catch
   saves you -- the process is gone.
2. **What if `refundPayment` itself fails?** Now you have an inconsistent state that
   requires manual intervention.
3. **What if you need to retry `createShipment` after a transient failure?** You need
   retry logic, backoff, idempotency keys -- all bolted on.
4. **What if this takes 3 days** (waiting for warehouse confirmation)? You cannot keep
   a process running for 3 days.

Teams typically solve this with a patchwork of queues (SQS, RabbitMQ), cron jobs,
state machines, database flags, and custom retry logic. Each of these adds complexity
and failure modes.

### The Temporal Insight

Temporal's core insight: **What if your code could survive any failure?**

With Temporal, the same logic becomes:

```typescript
// The Temporal way -- durable execution
async function processOrder(order: Order): Promise<void> {
  const payment = await activities.chargePayment(order);
  const inventory = await activities.reserveInventory(order);
  const shipment = await activities.createShipment(order);
  await activities.sendConfirmationEmail(order, shipment);
}
```

This looks like normal sequential code, but Temporal guarantees:

- If the worker crashes after `chargePayment`, a new worker picks up execution
  **exactly where it left off** -- `reserveInventory` runs next, not `chargePayment`
  again.
- Each activity can have its own retry policy, timeout, and heartbeat configuration.
- The workflow can run for days, weeks, or months -- there is no process to keep alive.
- The entire execution history is persisted and inspectable.
- Compensation logic (saga pattern) is just regular code with try/catch.

**The mental model for a Node.js developer:** Imagine if your Express request handler
could crash at any line, and when the server restarted, execution resumed at exactly
that line with all local variables intact. That is durable execution.

---

## Product Understanding

### Key Concepts

These are the terms you need to use fluently in interviews:

**Workflow:** A function that orchestrates your business logic. Must be deterministic
(same inputs always produce the same execution path). Think of it as the "brain" that
makes decisions but never directly touches the outside world.

**Activity:** A function that performs a single unit of work (API call, database write,
file operation). Activities are where non-deterministic, side-effectful code lives.
They can fail and be retried independently.

**Worker:** A process you run that polls Temporal Server for tasks, executes workflow
and activity code, and reports results back. You scale by running more workers.
Workers are analogous to Express servers that process incoming requests, except they
pull tasks from queues rather than listening on a port.

**Task Queue:** A named queue that connects workflow/activity tasks to workers.
Multiple workers can listen on the same task queue (horizontal scaling). Different
task queues can route work to specialized workers.

**Namespace:** A logical isolation boundary. Each namespace has its own workflow
history, task queues, and configuration. In Temporal Cloud, namespaces are the unit
of multi-tenancy.

**Event History:** The append-only log of everything that happened in a workflow
execution. Every state transition -- activity scheduled, activity completed, timer
fired, signal received -- is an event. This is the foundation of durable execution.

**Signal:** An asynchronous message sent to a running workflow from the outside.
Workflows can register signal handlers to react to external events.

**Query:** A synchronous read-only request to inspect a workflow's current state
without affecting its execution.

**Schedule:** Temporal's built-in replacement for cron jobs. Schedules trigger workflow
executions on a recurring basis with more flexibility than cron syntax.

**Replay:** When a worker picks up a workflow task, it replays the workflow function
against the event history to reconstruct the current state. This is how Temporal
achieves durability without persisting variables directly.

### The TypeScript SDK Structure

Since you will be working in TypeScript/Go at Temporal, here is how a Temporal
TypeScript project is organized:

```
src/
  workflows.ts    -- Workflow definitions (deterministic, no I/O)
  activities.ts   -- Activity implementations (API calls, DB writes, etc.)
  worker.ts       -- Worker process setup and configuration
  client.ts       -- Code that starts/signals/queries workflows
```

Packages: `@temporalio/workflow`, `@temporalio/activity`, `@temporalio/worker`,
`@temporalio/client`, `@temporalio/common`.

The TypeScript SDK enforces determinism by running workflow code in a V8 isolate
(similar to Cloudflare Workers) that strips out non-deterministic APIs like
`Date.now()`, `Math.random()`, and `setTimeout`. This is an implementation detail
worth knowing -- it shows you understand the SDK deeply.

### Open Source vs. Cloud

Temporal has a clear open-core model:

- **Temporal Server (OSS, MIT):** The core workflow engine. Anyone can self-host.
  Supports Cassandra, MySQL, or PostgreSQL as the persistence layer.
- **Temporal Cloud:** The managed service. You bring workers; Temporal runs the server.
  Adds enterprise features, SLAs, and operational simplicity.

This distinction matters for the billing/metering team because Cloud is what generates
revenue. Understanding the boundary between OSS and Cloud helps you reason about what
the team builds.

---

## Business Model

### Revenue Engine

Temporal Cloud uses **consumption-based pricing** built around two metrics:

1. **Actions:** The primary billing unit. An "action" is a billable operation such as:
   - Starting or resetting a workflow
   - Completing an activity or workflow task
   - Recording a heartbeat
   - Sending or receiving a signal
   - Timer operations

   Pricing tiers (approximate public rates):
   - First 5M actions/month: ~$25/million
   - Higher volumes: tiered discounts down to lower per-million rates
   - Enterprise customers negotiate custom rate cards

2. **Storage:** Measured in gigabyte-hours (GBh), split into:
   - **Active Storage:** Data for running workflows (event histories, mutable state)
   - **Retained Storage:** Data for closed/completed workflows kept for visibility

   1 GB = 744 GBh per month (24 hours x 31 days).

### Marketplace Presence

Temporal Cloud is available through:
- **AWS Marketplace** (Pay-as-you-go and credit-based)
- **GCP Marketplace**
- **Azure Marketplace**

This matters because marketplace billing flows through the cloud provider's billing
system, which adds complexity to the metering pipeline. The billing team needs to
reconcile Temporal's internal metering with marketplace-reported usage.

### Enterprise Features

The enterprise tier adds:
- Multi-region namespaces
- Audit logging
- SSO / SAML integration
- mTLS authentication
- Dedicated support and SLAs
- Custom rate cards
- Compliance certifications

### Why the Billing/Metering Team Is Strategic

This is not a back-office team. Consider:

- **Every dollar of Temporal Cloud revenue flows through billing/metering systems.**
  If metering is wrong, revenue is wrong.
- **Consumption-based pricing requires real-time, high-accuracy metering** across
  millions of actions per second. This is a hard distributed systems problem.
- **The pricing model directly affects product adoption.** If actions are counted
  incorrectly or bills are confusing, customers churn.
- **Cloud Nexus (cross-region/cross-namespace)** introduces new metering complexity
  -- an action that crosses namespace boundaries needs to be attributed correctly.
- **Marketplace integrations** require reconciliation between Temporal's metering
  and third-party billing systems.

When interviewers ask why you want to join this team, articulate this: you are building
the revenue engine for a $5B infrastructure company, solving real distributed systems
problems (metering at scale, exactly-once billing, multi-system reconciliation) that
directly impact the business.

---

## Competitive Landscape

### Direct Comparisons

| Feature | Temporal | AWS Step Functions | Azure Durable Functions | Cadence | Inngest |
|---------|----------|--------------------|------------------------|---------|---------|
| **Model** | Code-first (general-purpose languages) | JSON state machine (ASL) | Code-first (limited languages) | Code-first | Code-first (event-driven) |
| **Hosting** | Self-hosted or Cloud | AWS-managed only | Azure-managed only | Self-hosted only | Cloud-managed |
| **Language Support** | Go, Java, TypeScript, Python, .NET, PHP | Language-agnostic (via Lambda) | C#, JavaScript, Python, Java, PowerShell | Go, Java | TypeScript, Python, Go |
| **Workflow Duration** | Unlimited | 1 year max (Express: 5 min) | Unlimited | Unlimited | Varies |
| **Open Source** | Yes (MIT) | No | Partially (DTF) | Yes (Apache 2.0) | Yes (source-available) |
| **Versioning** | Worker-based versioning | Immutable definitions | Limited | Basic | Declarative |
| **Debugging** | Replay-based, full history | CloudWatch-based | Application Insights | Replay-based | Dashboard |
| **Infrastructure** | You manage workers | Fully managed | Fully managed | You manage everything | Mostly managed |

### Key Differentiators to Articulate

**Temporal vs. AWS Step Functions:**
"Step Functions force you to express logic in a JSON state machine (ASL), which becomes
unwieldy for complex business logic. Temporal lets you write workflows in real
programming languages with full IDE support, type checking, and testing. The tradeoff
is that Step Functions are fully managed -- you do not run workers -- while Temporal
Cloud still requires you to operate worker infrastructure."

**Temporal vs. Cadence:**
"Temporal is the spiritual successor to Cadence, built by the same people. Temporal
improves on Cadence with better multi-tenancy, a modern gRPC API, namespace-level
isolation, additional SDK languages, and a commercial cloud offering. Cadence is still
maintained by Uber but has a smaller community."

**Temporal vs. Inngest/Hatchet:**
"Inngest and Hatchet are newer entrants that optimize for developer experience and
simplicity. They are good for simpler use cases but lack Temporal's battle-tested
scalability (millions of concurrent workflows), the depth of its SDK model, and
features like continue-as-new, child workflows, and sophisticated versioning."

**Temporal vs. Restate:**
"Restate takes a different approach -- it makes existing RPC handlers durable rather
than requiring you to structure code as workflows and activities. It is a newer
project with a lighter-weight programming model but less maturity and ecosystem."

---

## Culture and Values

### Temporal's Five Values

These values appear in every job posting and are the behavioral framework interviewers
use to evaluate candidates:

**1. Curious**
You ask why, dig deeper, and seek understanding before jumping to solutions.
- *Interview signal:* Ask thoughtful questions about Temporal's architecture, about
  why design decisions were made, about the team's current challenges. Do not just
  regurgitate facts -- demonstrate genuine intellectual curiosity.
- *Behavioral example:* "In my last role, I noticed our retry logic was silently
  dropping errors. Instead of just fixing the symptom, I traced the issue back to a
  misunderstanding of our message broker's delivery guarantees, which led us to
  redesign the entire error handling pipeline."

**2. Driven**
You take ownership, push through ambiguity, and deliver results.
- *Interview signal:* Talk about projects where you owned outcomes end-to-end, not
  just tasks you were assigned. Show that you operate with urgency.
- *Behavioral example:* "I led the migration of our billing system from batch
  processing to real-time event streaming. There was no clear spec -- I wrote the
  design doc, got buy-in from stakeholders, and shipped incrementally over 8 weeks."

**3. Collaborative**
You make the people around you more effective. You share context, seek feedback,
and build consensus.
- *Interview signal:* When discussing technical decisions, explain how you brought
  others along. Mention design reviews, RFCs, pair programming.
- *Behavioral example:* "When I proposed switching our ORM, I did not just send a
  Slack message. I wrote a comparison doc, ran a workshop where the team could try
  both options, and incorporated their feedback before making a recommendation."

**4. Genuine**
You are honest, transparent, and direct. You admit what you do not know.
- *Interview signal:* If you do not know the answer to a question, say so -- then
  talk through how you would figure it out. Do not bluff.
- *Behavioral example:* "I told the team that my initial time estimate was wrong. I
  had underestimated the complexity of the database migration, and I proactively
  communicated the revised timeline with a clear explanation of what I missed."

**5. Humble**
You recognize that good ideas come from anywhere and you prioritize learning over
being right.
- *Interview signal:* Acknowledge contributions from teammates in your stories. Show
  that you have changed your mind based on evidence.
- *Behavioral example:* "A junior engineer on my team suggested a different approach
  to our caching strategy. My initial reaction was skepticism, but after we
  benchmarked it, their approach was 3x faster. I learned to evaluate ideas on merit
  regardless of who proposes them."

### Engineering Culture

- **Remote-first:** Distributed team, async communication is the default. Strong
  written communication matters.
- **Design-doc driven:** Significant changes start with a design document that is
  reviewed before implementation begins. If you have experience writing RFCs or
  design docs, highlight it.
- **High ownership, low bureaucracy:** Engineers are expected to own problems end-to-end
  -- from design through deployment and operational support.
- **Dogfooding:** Temporal Cloud is built on Temporal. The control plane uses Temporal
  workflows to manage namespaces, billing, and onboarding. This means the team uses
  the product they are building.

---

## Interview Signals

### What to Demonstrate

| Value | How to Show It |
|-------|---------------|
| Curious | Ask questions about Temporal's architecture choices. Dig into why the team chose a particular approach for metering. |
| Driven | Tell stories about owning outcomes, not just completing tickets. Emphasize impact and shipping. |
| Collaborative | Describe how you made design decisions as a team. Mention design docs, code reviews, cross-team work. |
| Genuine | Be honest about gaps in your knowledge. Show self-awareness. |
| Humble | Credit teammates. Talk about times you were wrong and what you learned. |

### Questions You Should Be Ready to Answer

1. **"Why Temporal?"** -- Connect to the mission. You want to work on infrastructure
   that makes every developer more productive. The billing/metering domain is
   interesting because it combines distributed systems, data pipelines, and direct
   business impact.

2. **"What do you know about what we do?"** -- Explain durable execution in your own
   words. Reference the founder story. Mention the open-source model. Show you
   understand the Cloud business.

3. **"Why this team?"** -- The billing/metering team is the revenue backbone of
   Temporal Cloud. You are excited about consumption-based pricing at scale, metering
   accuracy, and the complexity of multi-marketplace billing.

4. **"Tell me about a complex system you built."** -- Choose a story that demonstrates
   systems thinking: data pipelines, event-driven architecture, distributed state
   management. Map it to Temporal's domain.

5. **"How do you handle ambiguity?"** -- This is a startup. Requirements change.
   Temporal wants people who thrive when the path is not fully defined. Give a
   concrete example.

### Questions You Should Ask Interviewers

- "How does the billing team handle metering accuracy guarantees? Is it exactly-once,
  at-least-once with dedup, or something else?"
- "What does the data pipeline look like from a workflow action being executed to it
  appearing on a customer's invoice?"
- "How is Cloud Nexus changing the metering model? Are cross-namespace actions
  metered differently?"
- "What is the biggest technical challenge the billing team is facing right now?"
- "How do you balance shipping speed with billing accuracy -- what is the testing
  and validation strategy?"
- "How does the team work with the open-source community? Is there cross-pollination
  between Cloud and OSS teams?"

---

## Key Takeaways

1. Temporal exists because reliable distributed execution is hard, and existing
   solutions (queues + cron + state machines) are fragile and complex.
2. The business model is consumption-based Cloud pricing. The billing/metering team
   literally powers the revenue engine.
3. The founders built workflow orchestration systems at Amazon, Microsoft, and Uber
   before founding Temporal. This is not their first attempt -- it is their best one.
4. Temporal's values (curious, driven, collaborative, genuine, humble) are the
   behavioral rubric for interviews. Prepare stories that map to each one.
5. The engineering culture is remote-first, design-doc driven, high-ownership. If
   you have experience writing design docs and owning systems end-to-end, make that
   prominent in your interviews.
