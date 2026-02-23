# Module 02: Temporal SDK Patterns (Go)

## Why This Module Exists

You have built reliable systems with Node.js -- retry middleware, dead-letter queues, state machines backed by Redis or Postgres, cron jobs that drift, and distributed transactions stitched together with hope. Temporal replaces all of that with a single programming model: write normal-looking functions, and the platform guarantees they run to completion.

This module teaches you the Go SDK primitives you will use every day on the billing/metering team. Every pattern here maps to a real problem: subscription lifecycle management, invoice generation, usage aggregation, and the long-running workflows that make billing systems notoriously hard.

---

## 1. The Five Core Primitives

Before writing code, internalize the five building blocks. Everything in Temporal composes from these.

### Workflows

A workflow is a function that orchestrates work. It is durable -- if the process crashes mid-execution, Temporal replays the workflow from its event history and resumes exactly where it left off.

**Node.js analogy:** Imagine an Express route handler that never times out, automatically survives server restarts, and picks up exactly where it left off after a crash. That is a workflow.

```go
func SubscriptionWorkflow(ctx workflow.Context, input SubscriptionInput) (SubscriptionResult, error) {
    // This function can run for months (an entire subscription lifecycle).
    // If the worker crashes, Temporal replays events and resumes here.

    // Execute activities, wait for signals, sleep for days -- all durable.
    var result SubscriptionResult
    err := workflow.ExecuteActivity(ctx, ChargeCustomer, input.CustomerID).Get(ctx, &result)
    if err != nil {
        return SubscriptionResult{}, err
    }
    return result, nil
}
```

**Critical rule:** Workflow code must be deterministic. The same inputs must always produce the same sequence of commands. This is how replay works -- Temporal re-executes your workflow code and matches it against the recorded event history.

### Activities

Activities are functions that do actual work: call APIs, query databases, write files, send emails. They are the non-deterministic counterpart to workflows. Activities can fail, and Temporal retries them according to your configuration.

**Node.js analogy:** An activity is like an Express route handler that automatically retries on failure, with configurable timeouts and backoff. You write the handler; Temporal handles the retry loop.

```go
func ChargeCustomer(ctx context.Context, customerID string) (ChargeResult, error) {
    // This is a regular Go function. Use any library, call any API.
    // If it fails, Temporal retries it based on your RetryPolicy.

    result, err := paymentGateway.Charge(ctx, customerID)
    if err != nil {
        return ChargeResult{}, err
    }
    return ChargeResult{TransactionID: result.ID, Amount: result.Amount}, nil
}
```

Notice the context type: activities receive `context.Context` (standard Go), while workflows receive `workflow.Context` (Temporal-specific). This distinction matters.

### Workers

Workers are processes that poll task queues and execute your workflow and activity code. They are stateless -- all durable state lives on the Temporal Server. Workers are just execution engines.

**Node.js analogy:** A worker is like a cluster of Express servers behind a load balancer, except the "load balancer" is the Temporal Server and the "requests" are tasks pulled from queues.

```go
func main() {
    c, err := client.Dial(client.Options{})
    if err != nil {
        log.Fatal("Unable to create client", err)
    }
    defer c.Close()

    w := worker.New(c, "billing-task-queue", worker.Options{})

    // Register workflows and activities with this worker.
    w.RegisterWorkflow(SubscriptionWorkflow)
    w.RegisterActivity(ChargeCustomer)
    w.RegisterActivity(SendInvoice)

    err = w.Run(worker.InterruptCh())
    if err != nil {
        log.Fatal("Unable to start worker", err)
    }
}
```

You can run multiple workers polling the same task queue for horizontal scaling. You can also run different workers for different task queues to isolate workloads.

### Task Queues

Task queues are named queues that connect workflow/activity tasks to workers. They enable routing and isolation.

**Node.js analogy:** Like a combination of a message queue (SQS/RabbitMQ) and a router. Different queues route different types of work to different worker pools.

```go
// Start a workflow on a specific task queue.
we, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
    ID:        "subscription-cust-123",
    TaskQueue: "billing-task-queue",
}, SubscriptionWorkflow, input)
```

**Billing relevance:** You might have separate task queues for `billing-critical` (payment processing) and `billing-batch` (report generation), each with different worker pools and scaling policies.

### Namespaces

Namespaces are isolation boundaries, like database schemas. Workflows in different namespaces are completely isolated -- they cannot signal each other or share task queues.

**Use cases:**
- Multi-tenancy: one namespace per customer (Temporal Cloud does this)
- Environment isolation: `billing-staging` vs `billing-production`
- Team isolation: `billing` vs `onboarding`

```go
c, err := client.Dial(client.Options{
    Namespace: "billing-production",
})
```

---

## 2. Workflow Fundamentals

### Workflow Function Signatures

Every workflow function follows the same pattern:

```go
func MyWorkflow(ctx workflow.Context, input MyInput) (MyOutput, error) {
    // workflow logic
    return MyOutput{}, nil
}
```

Rules:
- First parameter is always `workflow.Context`.
- Remaining parameters are your input (must be serializable -- Temporal uses JSON by default).
- Return values are your output plus an `error`.
- The function name is the workflow type name (used in registration and invocation).

You can also register workflows with custom names:

```go
w.RegisterWorkflowWithOptions(SubscriptionWorkflow, workflow.RegisterOptions{
    Name: "billing.subscription.v2",
})
```

### The Determinism Contract

This is the most important concept in Temporal. Workflow code is replayed on every worker restart. If your code is not deterministic, replay breaks and the workflow fails.

**What you CANNOT do in workflow code:**

| Forbidden | Why | Use Instead |
|-----------|-----|-------------|
| `time.Now()` | Changes on replay | `workflow.Now(ctx)` |
| `time.Sleep()` | Not durable | `workflow.Sleep(ctx, duration)` |
| `rand.Intn()` | Changes on replay | `workflow.SideEffect()` |
| `os.Getenv()` | Can change between replays | Pass as workflow input |
| Network/disk I/O | Non-deterministic | Activities |
| `go func()` | Goroutines not tracked | `workflow.Go(ctx, func(ctx workflow.Context) { })` |
| Iterating `map` | Order not guaranteed in Go | Sort keys first, or use slices |
| `select` | Not tracked by Temporal | `workflow.NewSelector(ctx)` |
| Global mutable state | Shared across workflows | Local variables only |

**TS comparison:** In Node.js, you might use `Date.now()` or `Math.random()` freely in a request handler. In a Temporal workflow, these are bugs. Think of workflow code as a pure function that describes what should happen, not code that does things directly.

### Side Effects and Mutable Side Effects

When you need a non-deterministic value inside a workflow (like a UUID or timestamp), use `SideEffect`:

```go
// SideEffect runs the function once, records the result, and replays the recorded value.
var uuid string
encodedResult := workflow.SideEffect(ctx, func(ctx workflow.Context) interface{} {
    return generateUUID()
})
err := encodedResult.Get(&uuid)
```

For values that change over time but need to be tracked, use `MutableSideEffect`:

```go
// MutableSideEffect re-evaluates on each replay and records if the value changed.
// Useful for feature flags or configuration that might change.
encodedVal := workflow.MutableSideEffect(ctx, "pricing-tier", func(ctx workflow.Context) interface{} {
    return getCurrentPricingTier()
}, func(a, b interface{}) bool {
    return a.(string) == b.(string) // equality function
})
var tier string
err := encodedVal.Get(&tier)
```

### How Workflow Execution Works

Understanding replay is essential. Here is what happens step by step:

1. **Client calls `ExecuteWorkflow`** -- Temporal Server creates a workflow execution and writes a `WorkflowExecutionStarted` event.
2. **Server schedules a workflow task** -- puts it on the task queue.
3. **Worker picks up the task** -- runs your workflow code from the beginning.
4. **Workflow code calls `ExecuteActivity`** -- the SDK does not actually run the activity. It records a `ScheduleActivityTask` command and yields.
5. **Server records the command** -- schedules the activity task on the appropriate queue.
6. **A worker picks up the activity task** -- runs the activity function. Result is returned to the server.
7. **Server records `ActivityTaskCompleted`** -- schedules another workflow task.
8. **Worker picks up the workflow task** -- replays the workflow from the start. When it reaches `ExecuteActivity`, the SDK sees the result already exists in history and returns it immediately (no actual activity execution).
9. **Workflow continues** to the next step.

**If the worker crashes at step 8**, a different worker picks up the task and replays from the beginning. The event history is the source of truth. Your workflow code is just a function that regenerates the same sequence of commands.

**Billing relevance:** A subscription workflow might run for months. During that time, workers are restarted for deployments dozens of times. Each restart triggers a replay. This is normal and expected -- not an error recovery path.

### Error Handling in Workflows

Workflows use standard Go error handling, but with Temporal-specific error types:

```go
func SubscriptionWorkflow(ctx workflow.Context, input SubscriptionInput) error {
    var result ChargeResult
    err := workflow.ExecuteActivity(ctx, ChargeCustomer, input.CustomerID).Get(ctx, &result)
    if err != nil {
        // Check if the error is an application error (business logic failure)
        var appErr *temporal.ApplicationError
        if errors.As(err, &appErr) {
            if appErr.Type() == "InsufficientFunds" {
                // Handle business logic: suspend subscription instead of failing
                return workflow.ExecuteActivity(ctx, SuspendSubscription, input.CustomerID).Get(ctx, nil)
            }
        }
        // For other errors, let the workflow fail (it can be retried)
        return fmt.Errorf("charging customer %s: %w", input.CustomerID, err)
    }
    return nil
}
```

In activities, return specific error types to control retry behavior:

```go
func ChargeCustomer(ctx context.Context, customerID string) (ChargeResult, error) {
    result, err := gateway.Charge(ctx, customerID)
    if err != nil {
        if isInsufficientFunds(err) {
            // Non-retryable: do not keep trying to charge an empty account.
            return ChargeResult{}, temporal.NewNonRetryableApplicationError(
                "insufficient funds",
                "InsufficientFunds",
                err,
            )
        }
        // Retryable: network error, gateway timeout, etc. Temporal will retry.
        return ChargeResult{}, fmt.Errorf("charging customer %s: %w", customerID, err)
    }
    return ChargeResult{TransactionID: result.ID}, nil
}
```

---

## 3. Activity Patterns

### Activity Options

Activities are configured with options that control timeouts, retries, and heartbeats. This is where you define your reliability guarantees.

```go
activityOpts := workflow.ActivityOptions{
    // How long the activity can run after a worker picks it up.
    StartToCloseTimeout: 30 * time.Second,

    // Total time from scheduling to completion (including retries and queue time).
    ScheduleToCloseTimeout: 5 * time.Minute,

    // If set, the activity must heartbeat within this interval or it is considered failed.
    HeartbeatTimeout: 10 * time.Second,

    RetryPolicy: &temporal.RetryPolicy{
        InitialInterval:    time.Second,       // First retry after 1s
        BackoffCoefficient: 2.0,               // Double each time
        MaximumInterval:    time.Minute,        // Cap at 1 minute between retries
        MaximumAttempts:    5,                  // Give up after 5 attempts (0 = unlimited)
        NonRetryableErrorTypes: []string{
            "InsufficientFunds",                // Do not retry business logic failures
            "InvalidInput",
        },
    },
}

ctx = workflow.WithActivityOptions(ctx, activityOpts)
err := workflow.ExecuteActivity(ctx, ChargeCustomer, customerID).Get(ctx, &result)
```

### Timeout Decision Guide

| Timeout | When to Use | Example |
|---------|-------------|---------|
| `StartToCloseTimeout` | Always set this. Max time for a single attempt. | API call: 30s. DB query: 10s. |
| `ScheduleToCloseTimeout` | When you care about total elapsed time including retries. | Invoice must be generated within 1 hour. |
| `HeartbeatTimeout` | Long-running activities that should report progress. | Processing 1M metering events: heartbeat every 10s. |
| `ScheduleToStartTimeout` | Rarely used. Time waiting in queue before a worker picks it up. | Detect worker pool exhaustion. |

**Rule of thumb:** Always set `StartToCloseTimeout`. Add `ScheduleToCloseTimeout` when total time matters. Add `HeartbeatTimeout` for anything that runs more than a minute.

### Heartbeats

Heartbeats serve two purposes: they tell the server the activity is still alive, and they record progress so a retry can resume from where it left off.

```go
func ProcessMeteringEvents(ctx context.Context, events []MeteringEvent) error {
    // Record progress so retries resume from the last checkpoint.
    for i, event := range events {
        // Check if we should resume from a previous heartbeat.
        if activity.HasHeartbeatDetails(ctx) {
            var lastProcessed int
            if err := activity.GetHeartbeatDetails(ctx, &lastProcessed); err == nil {
                if i <= lastProcessed {
                    continue // Skip already-processed events
                }
            }
        }

        if err := processEvent(ctx, event); err != nil {
            return fmt.Errorf("processing event %d: %w", i, err)
        }

        // Heartbeat with progress. If this activity is retried,
        // it will resume from this index.
        activity.RecordHeartbeat(ctx, i)
    }
    return nil
}
```

**Billing relevance:** Processing a month's worth of metering events for a large customer could take minutes. Heartbeating lets you resume from the last processed event instead of starting over.

### Activity Context and Cancellation

Activities receive a standard `context.Context`, which is cancelled when the workflow is cancelled or the activity times out:

```go
func LongRunningExport(ctx context.Context, params ExportParams) error {
    for batch := range fetchBatches(params) {
        select {
        case <-ctx.Done():
            // Workflow was cancelled or activity timed out.
            // Clean up and return.
            return ctx.Err()
        default:
            if err := processBatch(ctx, batch); err != nil {
                return err
            }
            activity.RecordHeartbeat(ctx, batch.ID)
        }
    }
    return nil
}
```

### Local Activities vs Regular Activities

Local activities run in the same worker process as the workflow, skipping the task queue round-trip. They are faster but less durable.

```go
localOpts := workflow.LocalActivityOptions{
    StartToCloseTimeout: 5 * time.Second,
}
ctx = workflow.WithLocalActivityOptions(ctx, localOpts)
err := workflow.ExecuteLocalActivity(ctx, ValidateInput, input).Get(ctx, nil)
```

**When to use local activities:**
- Very short operations (< 5 seconds)
- High-throughput scenarios where task queue latency matters
- Simple validations or transformations
- When the activity does not need independent retry semantics

**When to use regular activities:**
- Long-running operations
- Operations that need their own timeout and retry configuration
- When you want the activity to be picked up by a different worker pool
- Anything involving external service calls that might be slow

**Billing relevance:** Validating an invoice structure before sending it to the payment gateway -- local activity. Calling the payment gateway -- regular activity.

---

## 4. Communication: Signals, Queries, and Updates

### Signals

Signals are fire-and-forget messages sent to a running workflow. The workflow can react to them whenever it chooses. Signals are durable -- if the worker is down when the signal arrives, the workflow will process it when a worker becomes available.

**Node.js analogy:** Like an event emitter, except the events are persisted and guaranteed to be delivered even if the process restarts.

```go
// WORKFLOW SIDE: receive a signal
func SubscriptionWorkflow(ctx workflow.Context, input SubscriptionInput) error {
    // Channel to receive cancellation signals.
    cancelCh := workflow.GetSignalChannel(ctx, "cancel-subscription")

    // Use a selector to wait for either the billing cycle or a cancellation signal.
    selector := workflow.NewSelector(ctx)

    selector.AddReceive(cancelCh, func(ch workflow.ReceiveChannel, more bool) {
        var reason string
        ch.Receive(ctx, &reason)
        // Handle cancellation: run compensating activities, prorate refund, etc.
    })

    // ... other selector cases

    selector.Select(ctx)
    return nil
}
```

```go
// CLIENT SIDE: send a signal
err := c.SignalWorkflow(ctx, "subscription-cust-123", "", "cancel-subscription", "customer-requested")
```

**Billing use cases:**
- Customer requests cancellation mid-cycle
- Payment method updated during retry
- Plan upgrade/downgrade during active subscription
- Manual override by support team

### Queries

Queries are read-only operations that return workflow state without affecting execution. They never block the workflow and must not have side effects.

**Node.js analogy:** Like a GET endpoint that reads from in-memory state -- fast, read-only, and safe to call anytime.

```go
// WORKFLOW SIDE: register a query handler
func SubscriptionWorkflow(ctx workflow.Context, input SubscriptionInput) error {
    status := "active"
    balance := 0.0

    // Register query handler. This runs synchronously on the worker.
    err := workflow.SetQueryHandler(ctx, "get-status", func() (SubscriptionStatus, error) {
        return SubscriptionStatus{
            Status:  status,
            Balance: balance,
        }, nil
    })
    if err != nil {
        return err
    }

    // ... workflow logic that updates status and balance
    return nil
}
```

```go
// CLIENT SIDE: query a workflow
resp, err := c.QueryWorkflow(ctx, "subscription-cust-123", "", "get-status")
if err != nil {
    log.Fatal(err)
}
var status SubscriptionStatus
if err := resp.Get(&status); err != nil {
    log.Fatal(err)
}
fmt.Printf("Status: %s, Balance: %.2f\n", status.Status, status.Balance)
```

**Important:** Query handlers must not mutate workflow state or call any Temporal APIs (no activities, no timers, no signals). They are pure read operations.

### Updates

Updates are a newer API that combines the mutation capability of signals with the return value of queries. An update can modify workflow state and return a result to the caller.

```go
// WORKFLOW SIDE: register an update handler
err = workflow.SetUpdateHandler(ctx, "change-plan", func(ctx workflow.Context, newPlan string) (PlanChangeResult, error) {
    // Validate the request (runs in the update validator, before acceptance)
    if !isValidPlan(newPlan) {
        return PlanChangeResult{}, fmt.Errorf("invalid plan: %s", newPlan)
    }

    // Execute the plan change (this is the update handler body)
    oldPlan := currentPlan
    currentPlan = newPlan

    // Can execute activities within an update handler
    var proration ProrateResult
    err := workflow.ExecuteActivity(ctx, CalculateProration, oldPlan, newPlan).Get(ctx, &proration)
    if err != nil {
        return PlanChangeResult{}, err
    }

    return PlanChangeResult{
        OldPlan:        oldPlan,
        NewPlan:        newPlan,
        ProratedAmount: proration.Amount,
    }, nil
})
```

```go
// CLIENT SIDE: send an update
handle, err := c.UpdateWorkflow(ctx, client.UpdateWorkflowOptions{
    WorkflowID: "subscription-cust-123",
    UpdateName: "change-plan",
    Args:       []interface{}{"enterprise"},
    WaitPolicy: &updatepb.WaitPolicy{
        LifecycleStage: updatepb.UPDATE_WORKFLOW_EXECUTION_LIFECYCLE_STAGE_COMPLETED,
    },
})
var result PlanChangeResult
err = handle.Get(ctx, &result)
```

**When to use each:**

| Mechanism | Mutation? | Return value? | Use Case |
|-----------|-----------|---------------|----------|
| Signal | Yes | No | Fire-and-forget: cancel subscription, update payment method |
| Query | No | Yes | Read state: get subscription status, check balance |
| Update | Yes | Yes | Mutate and confirm: change plan (need proration result) |

---

## 5. Child Workflows and Continue-as-New

### Child Workflows

Child workflows are independent workflow executions started from within a parent workflow. They have their own event history, their own retry policies, and can outlive the parent (depending on configuration).

```go
func BillingCycleWorkflow(ctx workflow.Context, input BillingInput) error {
    // Start a child workflow for invoice generation.
    // It has its own event history, so it won't bloat the parent.
    childOpts := workflow.ChildWorkflowOptions{
        WorkflowID: fmt.Sprintf("invoice-%s-%s", input.CustomerID, input.Period),
        // ParentClosePolicy controls what happens to the child if the parent completes.
        ParentClosePolicy: enums.PARENT_CLOSE_POLICY_TERMINATE,
    }
    childCtx := workflow.WithChildOptions(ctx, childOpts)

    var invoiceResult InvoiceResult
    err := workflow.ExecuteChildWorkflow(childCtx, InvoiceGenerationWorkflow, InvoiceInput{
        CustomerID: input.CustomerID,
        Period:     input.Period,
    }).Get(ctx, &invoiceResult)
    if err != nil {
        return fmt.Errorf("invoice generation failed: %w", err)
    }

    // Continue with payment processing using the invoice result...
    return nil
}
```

**When to use child workflows:**
- The sub-task has many activities (keeps event history manageable)
- You need different retry or timeout policies for a sub-task
- The sub-task should be independently observable (its own workflow ID)
- You want to split a large workflow into logical units
- The sub-task might need to outlive the parent

### Continue-as-New

Continue-as-new completes the current workflow execution and immediately starts a new one with the same workflow ID. The event history resets to zero. This is critical for long-running workflows.

**Why it matters:** Temporal stores every event in the workflow's history. A workflow that runs for months and executes thousands of activities will accumulate a massive history. Replay becomes slow. Eventually (at ~50,000 events), Temporal forces a termination. Continue-as-new prevents this.

```go
func SubscriptionWorkflow(ctx workflow.Context, input SubscriptionInput) error {
    // Process one billing cycle, then continue-as-new for the next.
    for i := 0; i < input.MaxCyclesBeforeReset; i++ {
        if err := processBillingCycle(ctx, input); err != nil {
            return err
        }

        // Sleep until next billing cycle.
        if err := workflow.Sleep(ctx, 30*24*time.Hour); err != nil {
            return err
        }
    }

    // Reset event history by continuing as new.
    // The workflow gets a fresh history but keeps the same workflow ID.
    return workflow.NewContinueAsNewError(ctx, SubscriptionWorkflow, SubscriptionInput{
        CustomerID:           input.CustomerID,
        Plan:                 input.Plan,
        CycleCount:           input.CycleCount + input.MaxCyclesBeforeReset,
        MaxCyclesBeforeReset: input.MaxCyclesBeforeReset,
    })
}
```

**Node.js analogy:** Imagine a setInterval that, every N iterations, saves its state to a database, clears its memory, and restarts from the saved state. Continue-as-new does this atomically.

**Billing relevance:** A subscription workflow that runs for years would accumulate millions of events without continue-as-new. The pattern is: process N billing cycles, then continue-as-new with the accumulated state. N is typically chosen to keep history well under 10,000 events.

### Choosing Between Child Workflows and Continue-as-New

| Scenario | Use |
|----------|-----|
| Long-running workflow needs history reset | Continue-as-New |
| Sub-task with different failure domain | Child Workflow |
| Fan-out to parallel sub-workflows | Child Workflows |
| Monthly billing cycle that runs indefinitely | Continue-as-New (reset each cycle) |
| Invoice generation within a billing cycle | Child Workflow |
| Workflow that processes unbounded lists | Continue-as-New (batch + reset) |

---

## 6. Timers and Scheduling

### Durable Timers

Temporal timers are durable. `workflow.Sleep` can last minutes, hours, days, or months -- and survives worker restarts, deployments, and infrastructure failures.

```go
func TrialWorkflow(ctx workflow.Context, input TrialInput) error {
    // This sleep is durable. If the worker crashes on day 6,
    // a new worker picks up the workflow and the timer continues.
    err := workflow.Sleep(ctx, 14*24*time.Hour) // Sleep for 14 days
    if err != nil {
        return err // Cancelled
    }

    // Trial ended. Convert to paid or expire.
    return workflow.ExecuteActivity(ctx, ConvertTrialToPaid, input.CustomerID).Get(ctx, nil)
}
```

**Node.js analogy:** Think of `setTimeout(fn, 14 * 24 * 60 * 60 * 1000)` -- except it actually works across server restarts, deployments, and even data center moves. In Node.js, you would need a database-backed scheduler (Bull, Agenda) to achieve this. Temporal gives it to you for free.

### workflow.NewTimer

`NewTimer` returns a Future, giving you more flexibility than `Sleep`:

```go
// Create a timer that can be used with a selector.
timerFuture := workflow.NewTimer(ctx, 24*time.Hour)

// Race the timer against a signal.
selector := workflow.NewSelector(ctx)

selector.AddFuture(timerFuture, func(f workflow.Future) {
    // Timer fired -- 24 hours have passed.
    // Charge the customer.
})

signalCh := workflow.GetSignalChannel(ctx, "cancel")
selector.AddReceive(signalCh, func(ch workflow.ReceiveChannel, more bool) {
    // Cancellation signal received before the timer fired.
    // Do not charge the customer.
})

selector.Select(ctx) // Blocks until one of the cases is ready.
```

**Billing relevance:** Grace periods, payment retry schedules, trial expirations -- all implemented as durable timers racing against cancellation signals.

### Cron Workflows

Temporal supports cron schedules natively:

```go
we, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
    ID:           "daily-metering-aggregation",
    TaskQueue:    "billing-task-queue",
    CronSchedule: "0 2 * * *", // Run daily at 2 AM UTC
}, MeteringAggregationWorkflow, input)
```

Each cron execution is a separate workflow run with its own history. If a run fails, the next scheduled run still fires (the cron schedule is managed by the server, not the workflow).

**Alternative: Schedules API.** Temporal also offers a newer Schedules API that provides more control than cron strings:

```go
handle, err := c.ScheduleClient().Create(ctx, client.ScheduleOptions{
    ID: "monthly-invoice-generation",
    Spec: client.ScheduleSpec{
        Calendars: []client.ScheduleCalendarSpec{{
            DayOfMonth: []client.ScheduleRange{{Start: 1}},
            Hour:       []client.ScheduleRange{{Start: 6}},
        }},
    },
    Action: &client.ScheduleWorkflowAction{
        Workflow: InvoiceGenerationWorkflow,
        Args:     []interface{}{input},
        TaskQueue: "billing-task-queue",
    },
    Overlap: enums.SCHEDULE_OVERLAP_POLICY_SKIP, // Skip if previous run is still going
})
```

---

## 7. Putting It Together: A Billing Workflow

Here is a complete example that ties together the concepts from this module. This is the kind of workflow you might build on the billing team.

```go
// SubscriptionWorkflow manages a customer's subscription lifecycle.
// It runs for months/years, using continue-as-new to keep history bounded.
func SubscriptionWorkflow(ctx workflow.Context, state SubscriptionState) error {
    logger := workflow.GetLogger(ctx)

    // Register query handler for external visibility.
    err := workflow.SetQueryHandler(ctx, "get-status", func() (SubscriptionStatus, error) {
        return SubscriptionStatus{
            Plan:         state.Plan,
            Status:       state.Status,
            CycleCount:   state.CycleCount,
            NextBillingAt: state.NextBillingAt,
        }, nil
    })
    if err != nil {
        return err
    }

    // Register update handler for plan changes.
    err = workflow.SetUpdateHandler(ctx, "change-plan", func(ctx workflow.Context, newPlan string) (string, error) {
        oldPlan := state.Plan
        state.Plan = newPlan
        logger.Info("Plan changed", "old", oldPlan, "new", newPlan)
        return fmt.Sprintf("Changed from %s to %s", oldPlan, newPlan), nil
    })
    if err != nil {
        return err
    }

    // Set up activity options.
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval:    time.Second,
            BackoffCoefficient: 2.0,
            MaximumAttempts:    5,
        },
    })

    // Signal channels.
    cancelCh := workflow.GetSignalChannel(ctx, "cancel-subscription")

    // Process billing cycles until cancelled or continued-as-new.
    for cycle := 0; cycle < 12; cycle++ { // 12 cycles, then continue-as-new
        // Wait for the next billing date, but listen for cancellation.
        timerFuture := workflow.NewTimer(ctx, 30*24*time.Hour) // ~1 month

        selector := workflow.NewSelector(ctx)
        cancelled := false

        selector.AddFuture(timerFuture, func(f workflow.Future) {
            // Timer fired -- time to bill.
        })

        selector.AddReceive(cancelCh, func(ch workflow.ReceiveChannel, more bool) {
            var reason string
            ch.Receive(ctx, &reason)
            cancelled = true
            logger.Info("Subscription cancelled", "reason", reason)
        })

        selector.Select(ctx)

        if cancelled {
            // Run cancellation activities: prorate refund, update records, send email.
            _ = workflow.ExecuteActivity(actCtx, ProcessCancellation, state.CustomerID).Get(ctx, nil)
            state.Status = "cancelled"
            return nil
        }

        // Execute the billing cycle.
        var chargeResult ChargeResult
        err := workflow.ExecuteActivity(actCtx, ChargeCustomer, ChargeInput{
            CustomerID: state.CustomerID,
            Plan:       state.Plan,
            Cycle:      state.CycleCount + cycle,
        }).Get(ctx, &chargeResult)

        if err != nil {
            // Payment failed. Suspend and wait for resolution.
            state.Status = "suspended"
            _ = workflow.ExecuteActivity(actCtx, NotifyPaymentFailed, state.CustomerID).Get(ctx, nil)

            // Wait up to 7 days for payment method update.
            paymentUpdatedCh := workflow.GetSignalChannel(ctx, "payment-updated")
            gracePeriod := workflow.NewTimer(ctx, 7*24*time.Hour)

            graceSelector := workflow.NewSelector(ctx)
            resolved := false

            graceSelector.AddReceive(paymentUpdatedCh, func(ch workflow.ReceiveChannel, more bool) {
                ch.Receive(ctx, nil)
                resolved = true
            })

            graceSelector.AddFuture(gracePeriod, func(f workflow.Future) {
                // Grace period expired.
            })

            graceSelector.Select(ctx)

            if !resolved {
                // Grace period expired without payment update. Cancel.
                _ = workflow.ExecuteActivity(actCtx, ProcessCancellation, state.CustomerID).Get(ctx, nil)
                state.Status = "cancelled"
                return nil
            }

            state.Status = "active"
            // Retry the charge (loop will continue)
            cycle-- // Retry this cycle
            continue
        }

        state.CycleCount++
        state.Status = "active"
        logger.Info("Billing cycle completed", "cycle", state.CycleCount)
    }

    // Continue-as-new to reset event history.
    return workflow.NewContinueAsNewError(ctx, SubscriptionWorkflow, state)
}
```

This single workflow handles:
- Monthly billing with durable timers
- Cancellation via signals
- Payment failure with grace periods
- Plan changes via updates
- Status queries for external visibility
- Event history management via continue-as-new

In Node.js, this would require a state machine in a database, a job scheduler, a message queue, webhook handlers, and careful coordination between all of them. With Temporal, it is one function.

---

## Key Takeaways for Interview

1. **Workflows are deterministic orchestrators.** They describe what should happen. Activities do the actual work.
2. **Replay is the mechanism behind durability.** Understanding replay is understanding Temporal.
3. **Signals, queries, and updates are the communication primitives.** Know when to use each.
4. **Continue-as-new prevents unbounded event history.** Essential for long-running billing workflows.
5. **Activity options (timeouts, retries, heartbeats) are your reliability configuration.** Know which timeout to use when.
6. **The determinism contract is non-negotiable.** Violating it breaks replay and corrupts workflow state.

When an interviewer asks "How would you implement X?", the answer almost always starts with: "A workflow that orchestrates activities, with signals for external input, queries for visibility, and continue-as-new for long-running execution."
