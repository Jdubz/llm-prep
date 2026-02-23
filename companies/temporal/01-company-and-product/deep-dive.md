# Deep Dive: Temporal Architecture Internals

## Why You Need This

In a system design or architecture interview at Temporal, you will be expected to
reason about distributed systems at the level of their internal components. You do not
need to have memorized every implementation detail of Temporal Server, but you should
be able to discuss how durable execution actually works under the hood, how the server
is structured, and how Temporal Cloud extends the open-source system. This document
gives you that foundation.

This is especially relevant for the billing/metering team: the services described here
generate the events that your team would meter and bill for.

---

## Table of Contents

1. [Server Architecture](#server-architecture)
2. [How Durable Execution Works](#how-durable-execution-works)
3. [Temporal Cloud Architecture](#temporal-cloud-architecture)
4. [Nexus: Cross-Namespace Communication](#nexus-cross-namespace-communication)
5. [Scalability Deep Dive](#scalability-deep-dive)
6. [Connecting This to the Billing/Metering Domain](#connecting-this-to-the-billingmetering-domain)

---

## Server Architecture

Temporal Server is composed of four core services, a persistence layer, and a
visibility store. All four services communicate via gRPC and can be deployed as a
single binary (development) or as independent scalable services (production).

```
                          +-------------------+
                          |   Client / SDK    |
                          +---------+---------+
                                    |
                                    | gRPC
                                    v
                          +---------+---------+
                          |  Frontend Service |  <-- API gateway, rate limiting,
                          |                   |      auth, validation, routing
                          +---------+---------+
                                    |
                     +--------------+--------------+
                     |                             |
                     v                             v
           +---------+---------+         +---------+---------+
           |  History Service  |         | Matching Service  |
           |                   |         |                   |
           |  - Workflow state |         |  - Task queues    |
           |  - Event history  |         |  - Task dispatch  |
           |  - Timers         |         |  - Sync matching  |
           |  - State machines |         |  - Partitioning   |
           +---------+---------+         +---------+---------+
                     |                             |
                     +----------+--+---------------+
                                |  |
                                v  v
                     +----------+--+-----------+
                     |    Persistence Layer     |
                     |  (Cassandra / MySQL /    |
                     |   PostgreSQL)            |
                     +-------------------------+

           +---------+---------+
           |  Worker Service   |  <-- Internal system workflows
           |                   |      (archival, replication,
           |                   |       dead-letter queue)
           +---------+---------+
```

### Frontend Service

The Frontend Service is the stateless API gateway for the entire cluster.

**Responsibilities:**
- Exposes the public gRPC API that SDKs and CLI tools connect to
- Request validation and sanitization
- Authentication and authorization
- Rate limiting (per-namespace and global)
- Request routing to the appropriate History or Matching shard

**Key detail:** Frontend is stateless and horizontally scalable. You can put a load
balancer in front of multiple Frontend instances. It does not own any data -- it is
purely a pass-through that adds validation, auth, and routing on top.

**Rate limiting is significant for billing:** The Frontend service enforces rate limits
that directly affect how many actions a namespace can perform. The billing team needs
to understand these limits because they define the upper bound of metered usage for a
given customer.

### History Service

The History Service is the most complex and important component. It is the source of
truth for all workflow execution state.

**Responsibilities:**
- Manages workflow execution state (mutable state + event history)
- Processes workflow tasks (decisions about what to do next)
- Schedules timers and handles timer firings
- Enqueues workflow tasks and activity tasks to the Matching Service
- Coordinates child workflows, signals, cancellations
- Handles continue-as-new (workflow reset with fresh history)
- Manages replication for multi-cluster setups

**Sharding model:** History Service shards distribute workflow executions across
multiple instances. Each shard owns a range of workflow IDs (determined by hashing
the workflow ID). A single shard handles all operations for the workflows it owns.

**Within a shard, operations are serialized.** This is a critical design choice -- it
simplifies consistency guarantees (no concurrent mutations to the same workflow) but
means that a single shard's throughput is bounded by database write latency. This is
why the number of shards is a key tuning parameter.

**Default shard count:** 512 for Cassandra-backed deployments, but configurable. Each
shard can handle roughly 100-200 operations per second depending on the database. With
512 shards, that is 50K-100K operations per second for the History tier.

**How a workflow task flows through History:**

1. History Service receives a task completion from the Frontend (forwarded from a
   worker).
2. It loads the workflow's mutable state and event history from the database.
3. It applies the new events (activity completed, timer fired, etc.) to the mutable
   state.
4. It generates any new tasks (next activity to schedule, new timer to set) and
   enqueues them to the Matching Service.
5. It persists the updated state and new events to the database in a single
   transaction.

### Matching Service

The Matching Service is responsible for dispatching tasks to workers.

**Responsibilities:**
- Manages task queues (mapping between queue names and pending tasks)
- Dispatches workflow tasks and activity tasks to workers
- Handles worker long-polling (workers hold open connections waiting for tasks)
- Partitions task queues for high-throughput scenarios

**Synchronous matching optimization:** When a new task arrives at a Matching Service
host that already has a worker long-polling for that task queue, the task is dispatched
immediately without being persisted to the database. This "sync match" path
significantly reduces latency and database load for high-throughput task queues.

**Task queue partitioning:** A single task queue can be split across multiple
partitions (default: 4) to increase throughput. Each partition is owned by a different
Matching Service shard. Workers are distributed across partitions, and tasks are routed
to partitions in a way that balances load.

**Why this matters for system design interviews:** The Matching Service is a great
example of a publish-subscribe system with competing consumers. If an interviewer asks
you to design a task dispatch system, you can reference how Temporal solves this --
long-polling, sync matching, partitioning, and persistence-backed queues for
durability.

### Worker Service

The Worker Service (not to be confused with user-deployed workers) runs Temporal's
own internal system workflows. It is the least complex of the four services.

**Responsibilities:**
- Workflow archival (moving completed workflow histories to cold storage)
- Workflow deletion and cleanup
- Dead-letter queue processing
- Cross-cluster replication workflows
- Internal maintenance tasks

**Dogfooding in action:** The Worker Service runs Temporal workflows to manage
Temporal's own cluster operations. This is the same dogfooding pattern used in
Temporal Cloud, where the control plane uses Temporal workflows to manage customer
namespaces.

### Persistence Layer

Temporal supports three database backends:

| Database    | Best For | Notes |
|-------------|----------|-------|
| Cassandra   | Large-scale production | Best write throughput, supports multi-DC replication natively |
| MySQL       | Smaller deployments | Simpler operations, good for teams familiar with MySQL |
| PostgreSQL  | Smaller deployments, visibility | Can serve as both persistence and visibility store |

The persistence layer stores:
- **Execution data:** Mutable state and event histories per workflow
- **Task data:** Pending tasks in task queues (for non-sync-matched tasks)
- **Namespace metadata:** Configuration, rate limits, retention policies
- **Cluster metadata:** Shard ownership, membership information

### Visibility Store

The visibility store powers workflow search and listing. It is separate from the
execution persistence layer.

- **Elasticsearch:** The recommended production visibility store. Supports complex
  search queries, custom search attributes, and efficient listing of workflows.
- **PostgreSQL:** Can be used as a simpler visibility backend for smaller deployments.

Visibility is relevant to billing because search attribute indexing and query volume
may be metered or may affect storage costs.

---

## How Durable Execution Works

This is the core concept you must be able to explain clearly. If you can walk through
this mechanism from first principles, you will demonstrate the kind of deep
understanding Temporal looks for.

### Event Sourcing: The Foundation

Temporal uses **event sourcing** as the persistence model for workflow executions.
Instead of storing the current state of a workflow as a mutable row, Temporal stores
an append-only sequence of events that describe everything that has happened.

Example event history for a simple workflow:

```
Event 1:  WorkflowExecutionStarted     { input: {...} }
Event 2:  WorkflowTaskScheduled         { taskQueue: "my-queue" }
Event 3:  WorkflowTaskStarted           { workerId: "worker-1" }
Event 4:  WorkflowTaskCompleted         { }
Event 5:  ActivityTaskScheduled         { activityType: "chargePayment", input: {...} }
Event 6:  ActivityTaskStarted           { workerId: "worker-2" }
Event 7:  ActivityTaskCompleted         { result: { paymentId: "pay_123" } }
Event 8:  WorkflowTaskScheduled         { }
Event 9:  WorkflowTaskStarted           { workerId: "worker-1" }
Event 10: WorkflowTaskCompleted         { }
Event 11: ActivityTaskScheduled         { activityType: "reserveInventory", input: {...} }
...
```

Every state change is an event. The complete history is the source of truth.

### The Replay Mechanism

When a worker receives a workflow task, it needs to reconstruct the workflow's current
state. It does this by **replaying** the workflow function against the event history.

Here is the step-by-step process:

1. **Worker receives a workflow task** containing the full event history (or a diff
   since the last task).

2. **Worker starts executing the workflow function** from the beginning.

3. **When the workflow calls an activity**, the SDK checks the event history:
   - If the history shows that activity was already scheduled and completed, the SDK
     returns the recorded result immediately (without executing the activity again).
   - If the history has no record of this activity, it is a new command -- the SDK
     records a "schedule activity" command and pauses the workflow.

4. **The commands are sent back to the server** as part of the workflow task
   completion. The server persists the new events and schedules the activity task.

5. **When the activity completes**, the server records the result in the history and
   schedules a new workflow task. The worker replays again, gets past the first
   activity (using the recorded result), and continues to the next step.

This is why **workflow code must be deterministic**: the replay must produce the exact
same sequence of commands every time. If replay diverges from the history, Temporal
detects a "non-determinism error."

### The Determinism Requirement

Workflow code must not:
- Call `Date.now()` or `new Date()` -- use `workflow.now()` instead
- Use `Math.random()` -- use Temporal's deterministic random
- Make network calls, file I/O, or database queries directly -- these go in activities
- Use global mutable state
- Use non-deterministic iteration (e.g., iterating over a `Set` or `Map` where order
  is not guaranteed across runtimes)

**The TypeScript SDK enforces this at runtime** by running workflow code in a sandboxed
V8 isolate where non-deterministic globals are replaced with Temporal-safe equivalents.
If workflow code tries to use `fetch()` or `fs.readFile()`, it will get a compile-time
or runtime error.

**Why this constraint exists:** During replay, the workflow function is executed
potentially thousands of times (once per workflow task). If it produced different
commands on replay than it did originally, the recorded history would be inconsistent
with the current execution. Determinism guarantees that replay always converges with
history.

### Workflow Tasks vs. Activity Tasks

This distinction is subtle but important:

**Workflow Task:** A task that tells a worker to replay the workflow function and
produce new commands. Workflow tasks are lightweight -- they involve executing
deterministic code against the event history. They run in the SDK's sandbox/isolate.

**Activity Task:** A task that tells a worker to execute an activity function. Activity
tasks can be heavyweight -- they may make HTTP calls, run database queries, or perform
long computations. They run in the normal runtime environment.

**Both types flow through the Matching Service** and are dispatched to workers via
task queues. But they have different performance characteristics, timeout semantics,
and retry behaviors.

**Billing implication:** Both workflow tasks and activity tasks count as billable
actions in Temporal Cloud. The metering system needs to track both types accurately.

### Mutable State vs. Event History

Temporal maintains two representations of workflow state:

1. **Event History:** The complete, append-only log of all events. Used for replay
   and auditability. Can grow large for long-running workflows.

2. **Mutable State:** A compact, derived view of the current workflow state. Includes
   things like: which activities are pending, what timers are set, current signal
   handlers. Used by the History Service for quick decision-making without replaying
   the full history.

The mutable state is reconstructed from the event history if lost. This is the classic
event sourcing pattern: the log is the source of truth, and any derived view can be
rebuilt from it.

### Continue-As-New

For very long-running workflows (months or years), the event history can grow
unboundedly. `continue-as-new` solves this by completing the current workflow execution
and immediately starting a new one with a fresh history, carrying over whatever state
the workflow passes as the new input.

This is analogous to log compaction in Kafka or snapshotting in event sourcing systems.
The old history is retained for visibility/archival but is no longer used for replay.

---

## Temporal Cloud Architecture

### Multi-Tenant with Namespace Isolation

Temporal Cloud is a multi-tenant system where multiple customers share the same
underlying infrastructure, with isolation enforced at the namespace level.

Each customer's namespace gets:
- Isolated workflow execution state (no cross-namespace data leakage)
- Independent rate limits and quotas
- Separate visibility/search indexes
- Configurable retention periods

### Cell-Based Architecture

Temporal Cloud uses a **cell-based architecture** for the data plane:

```
                    +---------------------------+
                    |       Control Plane       |
                    |  (namespace provisioning, |
                    |   billing, onboarding,    |
                    |   account management)     |
                    +---------------------------+
                                |
              +-----------------+-----------------+
              |                 |                 |
              v                 v                 v
        +-----+-----+    +-----+-----+    +-----+-----+
        |   Cell A   |    |   Cell B   |    |   Cell C   |
        |            |    |            |    |            |
        | AWS Acct   |    | AWS Acct   |    | GCP Proj   |
        | VPC        |    | VPC        |    | VPC        |
        | EKS/GKE    |    | EKS/GKE   |    | EKS/GKE   |
        | Temporal   |    | Temporal   |    | Temporal   |
        | Server     |    | Server     |    | Server     |
        | Database   |    | Database   |    | Database   |
        +-----+-----+    +-----+-----+    +-----+-----+
              |                 |                 |
              v                 v                 v
        Customer          Customer          Customer
        Workers           Workers           Workers
```

**Key properties of cells:**
- Each cell is a **self-contained unit** with its own AWS account (or GCP project),
  VPC, Kubernetes cluster, and database.
- Cells are **independently deployable** -- an update or failure in one cell does not
  affect others.
- Namespaces are **pinned to cells** -- a customer's namespace runs entirely within
  one cell.
- Cells provide **blast radius reduction** -- if a cell has an issue, only the
  namespaces in that cell are affected.

**Currently operating across 14+ AWS regions and GCP regions.**

### Control Plane vs. Data Plane

**Data Plane (Cells):**
- Runs the actual Temporal Server (Frontend, History, Matching, Worker services)
- Processes customer workflow executions
- Handles the real-time workflow execution path
- Optimized for low latency and high throughput

**Control Plane:**
- Namespace provisioning and lifecycle management
- Account management and authentication
- **Billing and metering** -- the domain of the team you are interviewing for
- Onboarding flows
- Audit logging
- Temporal Cloud UI and API

**Critical detail:** The control plane is itself built on Temporal. Namespace creation,
billing calculations, and onboarding flows are implemented as Temporal workflows.
This is the ultimate dogfooding: Temporal Cloud's management layer uses Temporal to
manage Temporal.

### How Billing/Metering Fits In

The metering pipeline collects usage data from the data plane cells and feeds it into
the billing system in the control plane:

```
  Cell A             Cell B             Cell C
    |                  |                  |
    | (usage events)   | (usage events)   | (usage events)
    |                  |                  |
    v                  v                  v
+--------------------------------------------------+
|              Metering Pipeline                    |
|  (aggregation, dedup, attribution per namespace) |
+--------------------------------------------------+
                       |
                       v
+--------------------------------------------------+
|              Billing System                      |
|  (rate cards, invoice generation, marketplace    |
|   reconciliation, credit management)             |
+--------------------------------------------------+
                       |
                       v
              Customer Invoices
              (direct + marketplace)
```

The metering pipeline must:
1. **Collect usage events from all cells** without missing any
2. **Attribute each action to the correct namespace and customer**
3. **Aggregate at the correct granularity** (per-minute, per-hour, per-day)
4. **Deduplicate** to avoid double-counting (especially during retries or failovers)
5. **Handle late-arriving events** from cells that may have network delays
6. **Reconcile with marketplace billing systems** (AWS, GCP, Azure)

These are real distributed systems problems -- exactly the kind of thing to discuss
in system design interviews.

---

## Nexus: Cross-Namespace Communication

### What Nexus Solves

Before Nexus, if a workflow in Namespace A needed to trigger work in Namespace B, you
had to build custom integration: API calls, message queues, or shared databases. This
broke the Temporal guarantee of durable execution -- the cross-namespace call was
outside Temporal's transactional boundary.

**Temporal Nexus** enables reliable communication between Temporal applications across
team, namespace, region, and cloud boundaries -- all within Temporal's execution
guarantees.

### Architecture

```
  Namespace A (Caller)              Namespace B (Handler)
  +-------------------+             +-------------------+
  | Caller Workflow   |             | Handler Workflow  |
  |                   |   Nexus     |                   |
  | nexus.execute() --+---RPC----->-+ Nexus Endpoint    |
  |                   |   Protocol  |   -> Task Queue   |
  |   (waits for      |             |   -> Worker       |
  |    completion)    |             |                   |
  +-------------------+             +-------------------+
```

**Key components:**

- **Nexus Endpoint:** A routing component registered in the cluster that maps incoming
  Nexus requests to a target namespace and task queue. Acts as a reverse proxy.
- **Nexus Operations:** The units of work exposed through an endpoint. Can be
  **synchronous** (complete within 10 seconds) or **asynchronous** (long-running,
  backed by workflows).
- **Nexus Endpoint Registry:** A cluster-global (or account-scoped in Cloud) registry
  of endpoints and their routing configuration.
- **Outbound Queue:** Groups Nexus requests by type, source, and destination to
  provide isolation when a destination is slow or unavailable.

### Operation Types

**Synchronous Operations:**
- Complete within 10 seconds
- Result returned directly to the caller
- Good for: lookups, validations, short computations

**Asynchronous Operations:**
- Can run for days (up to 60 days)
- Return an operation token immediately
- Caller workflow suspends until the operation completes
- Completion notification via callback
- Backed by a workflow in the handler namespace

### Why Nexus Matters for Billing/Metering

Nexus introduces new metering complexity:

1. **Cross-namespace actions:** When Namespace A calls Namespace B via Nexus, which
   namespace gets billed for the action? Both? Just the caller? Just the handler?
2. **Cross-region traffic:** Nexus can cross region boundaries, which may involve
   different cost structures.
3. **Outbound queue management:** The outbound queue itself consumes resources that
   may need to be metered.
4. **Attribution complexity:** A single business operation may span multiple namespaces,
   making it harder for customers to understand their bills.

If an interviewer asks about interesting metering challenges, Nexus is a perfect
example to discuss.

---

## Scalability Deep Dive

### Workflows Are the Unit of Scale

Each workflow execution is independent. There is no shared state between workflows
(unless explicitly communicated via signals or queries). This means:

- Adding more workflows does not slow down existing workflows
- Workflows can be distributed across shards and cells independently
- The system scales horizontally by adding more shards, more Matching partitions,
  and more workers

### Sharding by Workflow ID

```
  workflowId: "order-12345"
       |
       v
  hash("order-12345") = 0xA3F2...
       |
       v
  shard = hash % numShards = 417
       |
       v
  History Service shard 417 owns this workflow
```

**All operations for a given workflow are handled by a single shard.** This provides:
- Strong consistency for a single workflow (no distributed locks needed)
- Natural partitioning of load across shards
- Simple ownership model (shard = unit of ownership)

**The tradeoff:** A single shard's throughput is bounded by its database write latency.
For most workflows this is not a bottleneck, but "hot" workflows (receiving many
signals per second) can saturate their shard.

### Task Queue Scalability

Task queues scale independently of workflow sharding:

- **Partition count** can be increased for high-throughput queues (default: 4)
- **Workers poll partitions** and are distributed across them
- **Sync matching** bypasses persistence entirely for low-latency dispatch
- Multiple task queues can route to specialized worker pools

### Real-World Scale

- Temporal Cloud is benchmarked to process **450,000+ actions per second**
- Production deployments handle **millions of concurrent workflows**
- The database is typically the bottleneck, not the Temporal services themselves
- PlanetScale has documented running Temporal at scale with millions of QPS using
  sharded MySQL

### Scale Levers

| Lever | What It Scales | How |
|-------|---------------|-----|
| History shards | Workflow throughput | More shards = more parallel workflow processing |
| Matching partitions | Task dispatch throughput | More partitions = more parallel task dispatch |
| Worker count | Execution throughput | More workers = more parallel activity execution |
| Database scaling | Overall system throughput | Better hardware or sharded databases increase persistence throughput |
| Cells (Cloud) | Tenant isolation + capacity | More cells = more isolated capacity pools |

---

## Connecting This to the Billing/Metering Domain

### What Gets Metered

Every one of these architecture components generates metered events:

| Component | Metered Event | Billing Unit |
|-----------|--------------|-------------|
| Frontend | API call received | May contribute to action count |
| History | Workflow task completed | Action |
| History | Activity task scheduled | Action |
| History | Timer fired | Action |
| History | Signal processed | Action |
| History | Workflow started/completed | Action |
| Matching | Task dispatched | Included in task actions |
| Persistence | Event history stored | Active/Retained Storage (GBh) |
| Visibility | Search attribute indexed | May affect storage |

### Architecture Questions to Prepare For

1. **"How would you design a metering system for Temporal Cloud?"**
   Think about: event collection from cells, aggregation pipelines, exactly-once
   semantics, late-arriving events, storage of metering data, query patterns for
   billing.

2. **"How do you ensure metering accuracy at scale?"**
   Think about: idempotency, deduplication, reconciliation between metering and
   execution logs, end-to-end testing of the billing pipeline.

3. **"How would you handle a metering pipeline failure?"**
   Think about: durability of metering events, replay capability, alerting on
   discrepancies, SLAs for billing accuracy.

4. **"What happens when a new action type is introduced?"**
   Think about: forward compatibility of the metering schema, versioning of the
   metering pipeline, backfill strategies.

5. **"How would you design billing for Nexus cross-namespace operations?"**
   Think about: attribution models, double-counting prevention, customer-facing
   transparency.

### System Design Interview Framing

If you are asked to design a billing/metering system in the interview, use Temporal's
own architecture as your mental model:

- **Event sourcing for metering:** Every metered event is appended to a log. Bills
  are derived views of this log. You can always rebuild a bill from raw events.
- **Cell-based collection:** Each cell is an independent event source. The aggregation
  layer must handle cross-cell consistency.
- **Temporal workflows for billing:** Invoice generation, credit application, and
  marketplace reconciliation are themselves long-running processes with failure modes
  -- exactly what Temporal workflows are designed for.

This shows the interviewer that you understand both the problem domain and the
technology stack, and that you can reason about how to use Temporal to build Temporal's
own business systems.
