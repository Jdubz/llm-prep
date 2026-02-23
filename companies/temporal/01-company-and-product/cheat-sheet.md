# Cheat Sheet: Temporal Quick Reference

Use this for rapid review before interviews. Everything here is covered in more
depth in README.md and deep-dive.md.

---

## Temporal Concepts Glossary

| Term | Definition |
|------|-----------|
| **Workflow** | A deterministic function that orchestrates business logic; survives any failure through replay |
| **Activity** | A function that performs side effects (I/O, API calls); can fail and be retried independently |
| **Worker** | A process you deploy that polls Temporal Server for tasks and executes workflow/activity code |
| **Task Queue** | A named queue connecting tasks to workers; multiple workers can poll the same queue |
| **Namespace** | Logical isolation boundary for workflows, task queues, and configuration; unit of multi-tenancy in Cloud |
| **Event History** | Append-only log of every state change in a workflow execution; the source of truth |
| **Replay** | Re-executing a workflow function against its event history to reconstruct current state |
| **Determinism** | Requirement that workflow code produce the same commands given the same history; no I/O, no randomness |
| **Signal** | Async message sent to a running workflow from outside; triggers a signal handler |
| **Query** | Sync read-only request to inspect a workflow's state without affecting execution |
| **Activity Heartbeat** | Periodic progress report from a long-running activity; enables early failure detection |
| **Continue-As-New** | Completes current workflow and starts a new one with fresh history; prevents unbounded history growth |
| **Child Workflow** | A workflow started by another workflow; has its own execution lifecycle and history |
| **Schedule** | Built-in cron replacement; triggers workflows on a recurring basis |
| **Timer** | Durable delay within a workflow; survives worker restarts (unlike `setTimeout`) |
| **Saga Pattern** | Compensation-based error handling using try/catch in workflow code; no special framework needed |
| **Workflow Task** | A task telling a worker to replay the workflow function and produce commands |
| **Activity Task** | A task telling a worker to execute an activity function |
| **Search Attribute** | Custom indexed fields on workflows for querying via the visibility store |
| **Action** | Temporal Cloud billing unit; a single billable operation (start, complete, signal, heartbeat, etc.) |
| **Nexus** | Cross-namespace/region/cloud communication protocol built into Temporal |
| **Nexus Endpoint** | Routing component that maps Nexus requests to a target namespace and task queue |
| **Nexus Operation** | A unit of work exposed through a Nexus endpoint; can be sync (10s) or async (60d) |
| **Temporal Cloud Cell** | Self-contained infrastructure unit (own AWS account, VPC, K8s cluster, DB) for data plane isolation |
| **Mutable State** | Compact, derived view of a workflow's current state; rebuilt from event history if lost |

---

## Server Components

```
  +--------+     gRPC     +-----------+
  | Client | -----------> | Frontend  |  Rate limiting, auth, routing
  +--------+              +-----------+
                               |
                +--------------+--------------+
                |                             |
           +---------+                  +-----------+
           | History |                  |  Matching  |  Task dispatch,
           +---------+                  +-----------+  sync matching
           Workflow state,                    |
           event sourcing,               Task Queues
           timers, shards                     |
                |                             v
                +----------+--+----------+--------+
                           |  |          |
                      +----+--+----+  +--+-----+
                      | Persistence|  | Workers |  Your deployed
                      | (DB layer) |  | (yours) |  worker processes
                      +------------+  +---------+

           +---------+
           | Worker  |  Internal system workflows
           | Service |  (archival, cleanup, replication)
           +---------+
```

---

## Temporal Cloud vs. Self-Hosted

| Dimension | Temporal Cloud | Self-Hosted (OSS) |
|-----------|---------------|-------------------|
| **Server management** | Managed by Temporal | You operate everything |
| **Cost model** | Consumption-based (actions + storage) | Infrastructure cost only |
| **Database** | Managed by Temporal | You choose and operate (Cassandra/MySQL/PG) |
| **Scaling** | Automatic within cells | Manual shard/partition tuning |
| **Multi-tenancy** | Built-in namespace isolation | You implement isolation |
| **SLA** | 99.99% for enterprise | Whatever you can achieve |
| **SSO/Auth** | Built-in SAML/SSO | You configure mTLS + auth plugins |
| **Audit logging** | Built-in | You build it |
| **Multi-region** | Supported via Nexus + multi-region namespaces | Manual multi-cluster setup |
| **Updates** | Managed, rolling updates per cell | You handle version upgrades |
| **Visibility** | Managed Elasticsearch/PG | You operate Elasticsearch |
| **Best for** | Teams that want to focus on application logic | Teams with strong platform engineering |

---

## Competitor Comparison

| | Temporal | Step Functions | Durable Functions | Cadence | Inngest | Restate |
|-|----------|---------------|-------------------|---------|---------|---------|
| **Programming model** | Code-first | JSON (ASL) | Code-first | Code-first | Code-first | RPC handlers |
| **Open source** | MIT | No | Partial | Apache 2.0 | Source-available | Yes |
| **Managed offering** | Temporal Cloud | AWS-native | Azure-native | No | Inngest Cloud | Restate Cloud |
| **Language support** | Go, Java, TS, Python, .NET, PHP | Any (via Lambda) | C#, JS, Python, Java | Go, Java | TS, Python, Go | TS, Java, Kotlin, Go, Rust |
| **Max duration** | Unlimited | 1 year | Unlimited | Unlimited | Varies | Unlimited |
| **Scale proof** | Millions of workflows | AWS-backed | Azure-backed | Uber-scale | Growing | Early |
| **Worker management** | You manage | Fully managed | Fully managed | You manage | Mostly managed | You manage |
| **Versioning** | Worker versioning | Immutable defs | Limited | Basic | Declarative | Endpoint-based |

---

## Company Timeline

| Date | Milestone |
|------|-----------|
| 2009 | Fateev and Abbas meet at AWS, build Simple Workflow Service |
| 2012 | Abbas builds Durable Task Framework at Microsoft |
| 2015 | Both join Uber, begin building Cadence |
| 2019 | Temporal Technologies founded; $6.75M seed from Amplify Partners |
| Oct 2020 | $18.75M Series A led by Sequoia Capital |
| Feb 2022 | $103M Series B led by Greenoaks/Index; $1.5B valuation (unicorn) |
| Feb 2023 | $75M Series B extension at flat $1.5B valuation |
| Mar 2025 | $146M Series C at $1.72B valuation |
| Oct 2025 | $105M secondary led by GIC at $2.5B valuation |
| Jan 2026 | $300M Series D led by a16z at $5.0B valuation |

---

## Values -- Interview-Ready Examples

| Value | One-liner | Behavioral Signal |
|-------|-----------|-------------------|
| **Curious** | Ask why, dig deeper | "I traced a flaky test back to a race condition in our message broker config -- I could have just retried the test." |
| **Driven** | Own outcomes, ship | "I wrote the design doc, got alignment, and shipped the migration in 8 weeks with no spec handed to me." |
| **Collaborative** | Make others effective | "I ran a comparison workshop before proposing the ORM switch so the team could evaluate options together." |
| **Genuine** | Honest, transparent | "I told stakeholders my estimate was wrong and communicated a revised timeline with a clear explanation." |
| **Humble** | Best idea wins | "A junior engineer's caching approach benchmarked 3x faster than mine. I championed their design." |

---

## Key People

| Person | Role | Notable Background |
|--------|------|--------------------|
| **Maxim Fateev** | CEO / CTO | Co-created SWF at Amazon, worked at Google, co-created Cadence at Uber |
| **Samar Abbas** | Co-Founder | Co-created SWF at Amazon, built Durable Task Framework at Microsoft, co-created Cadence at Uber |
| **Charles Zedlewski** | Chief Product Officer | Product leadership |

---

## Pricing Model

```
Temporal Cloud Bill = Actions Cost + Storage Cost

Actions Cost:
  First 5M actions/month ......... ~$25/million
  Higher volumes .................. tiered discounts (custom rate cards)

Storage Cost:
  Active Storage .................. $0.042/GBh
  Retained Storage ................ custom rate
  (1 GB for 1 month = 744 GBh)

Marketplace:
  AWS / GCP / Azure Marketplace ... same pricing, billed through cloud provider

Enterprise:
  Custom rate cards, committed spend, volume discounts
```

---

## Common Interview Questions

### Company / Product

- "Why do you want to work at Temporal?"
  Focus: mission alignment, durable execution as a paradigm shift, revenue-critical
  billing domain.

- "Explain what Temporal does to a non-technical person."
  Focus: "It makes software reliable by remembering exactly where it was, even if
  something crashes, so it can pick up right where it left off."

- "How is Temporal different from a message queue + retry logic?"
  Focus: Temporal provides durable execution of your code, not just message delivery.
  State, decisions, and progress are persisted -- not just payloads.

- "Why would someone use Temporal Cloud instead of self-hosting?"
  Focus: operational burden of running a distributed database, Temporal Server, and
  Elasticsearch at production scale. Cloud lets you focus on business logic.

### Architecture

- "Walk me through what happens when a workflow starts."
  Focus: Client -> Frontend -> History (create execution, record events) -> Matching
  (schedule workflow task) -> Worker (replay workflow function) -> commands back to
  History.

- "Why must workflow code be deterministic?"
  Focus: Replay mechanism. Workflow function is re-executed against history to
  reconstruct state. Non-determinism causes history divergence.

- "What is the difference between a workflow task and an activity task?"
  Focus: Workflow task = replay workflow logic, produce commands. Activity task =
  execute a side-effectful function. Different performance profiles and retry semantics.

### Billing/Metering Domain

- "How would you design a metering system for a consumption-based product?"
  Focus: event collection, aggregation pipeline, exactly-once semantics, late events,
  reconciliation, customer-facing transparency.

- "What are the hardest problems in billing at scale?"
  Focus: accuracy guarantees, multi-system reconciliation (marketplace billing),
  handling retroactive corrections, credit management, auditability.

- "How would you handle a bug that caused under-counting of actions?"
  Focus: detection (reconciliation), impact assessment, backfill strategy, customer
  communication, prevention (end-to-end testing of metering pipeline).

---

## Temporal in One Paragraph

Temporal is a durable execution platform founded in 2019 by the creators of Uber's
Cadence workflow engine (who previously built Amazon SWF and Microsoft's Durable Task
Framework). The open-source server (MIT license) provides workflow orchestration that
survives any failure through event sourcing and replay. Temporal Cloud is the managed
service, priced on consumption (actions + storage), available on AWS, GCP, and Azure
marketplaces. The company is valued at $5B (Series D, Jan 2026, led by a16z) with
~400 employees, and is positioning durable execution as foundational infrastructure
for AI agents and complex distributed systems.
