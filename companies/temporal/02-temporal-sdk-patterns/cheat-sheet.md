# Module 02 Cheat Sheet: Temporal SDK Quick Reference (Go)

## Workflow Function Template

```go
package workflows

import (
    "fmt"
    "time"

    "go.temporal.io/sdk/temporal"
    "go.temporal.io/sdk/workflow"
)

func MyWorkflow(ctx workflow.Context, input MyInput) (MyOutput, error) {
    logger := workflow.GetLogger(ctx)

    // 1. Configure activity options.
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval:    time.Second,
            BackoffCoefficient: 2.0,
            MaximumInterval:    time.Minute,
            MaximumAttempts:    5,
        },
    })

    // 2. Register query handler.
    _ = workflow.SetQueryHandler(ctx, "get-status", func() (string, error) {
        return "running", nil
    })

    // 3. Execute activities.
    var result MyOutput
    err := workflow.ExecuteActivity(actCtx, MyActivity, input.Param).Get(ctx, &result)
    if err != nil {
        return MyOutput{}, fmt.Errorf("my activity: %w", err)
    }

    logger.Info("Workflow completed", "result", result)
    return result, nil
}
```

## Activity Function Template

```go
package activities

import (
    "context"
    "fmt"

    "go.temporal.io/sdk/activity"
    "go.temporal.io/sdk/temporal"
)

func MyActivity(ctx context.Context, param string) (MyResult, error) {
    // Access activity info.
    info := activity.GetInfo(ctx)
    logger := activity.GetLogger(ctx)

    logger.Info("Activity started", "attempt", info.Attempt)

    // Do actual work (API calls, DB queries, etc.).
    result, err := doWork(ctx, param)
    if err != nil {
        if isBusinessError(err) {
            // Non-retryable: stop retrying.
            return MyResult{}, temporal.NewNonRetryableApplicationError(
                err.Error(), "BusinessError", err)
        }
        // Retryable: Temporal will retry.
        return MyResult{}, fmt.Errorf("doing work: %w", err)
    }

    return result, nil
}
```

## Worker Setup Template

```go
package main

import (
    "log"

    "go.temporal.io/sdk/client"
    "go.temporal.io/sdk/worker"
)

func main() {
    c, err := client.Dial(client.Options{
        HostPort:  "localhost:7233",
        Namespace: "default",
    })
    if err != nil {
        log.Fatal("Unable to create client:", err)
    }
    defer c.Close()

    w := worker.New(c, "my-task-queue", worker.Options{
        MaxConcurrentActivityExecutionSize:     200,
        MaxConcurrentWorkflowTaskExecutionSize: 200,
    })

    // Register workflows.
    w.RegisterWorkflow(MyWorkflow)

    // Register activities (can use struct methods for dependency injection).
    activities := &MyActivities{db: db, gateway: gateway}
    w.RegisterActivity(activities)

    if err := w.Run(worker.InterruptCh()); err != nil {
        log.Fatal("Unable to start worker:", err)
    }
}
```

## Starting a Workflow (Client Side)

```go
we, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
    ID:                    "unique-workflow-id",
    TaskQueue:             "my-task-queue",
    WorkflowIDReusePolicy: enums.WORKFLOW_ID_REUSE_POLICY_REJECT_DUPLICATE,
}, MyWorkflow, input)
if err != nil {
    log.Fatal(err)
}

// Wait for result.
var result MyOutput
err = we.Get(ctx, &result)
```

## Timeout and Retry Configuration

### Timeout Decision Table

| Timeout | What It Controls | When to Set | Typical Value |
|---------|-----------------|-------------|---------------|
| `StartToCloseTimeout` | Max time for a single activity attempt | Always | 10s-5min |
| `ScheduleToCloseTimeout` | Total time including all retries + queue wait | When total deadline matters | 1min-1hr |
| `ScheduleToStartTimeout` | Time waiting in queue before pickup | Detecting worker pool issues | Rarely used |
| `HeartbeatTimeout` | Max silence between heartbeats | Long-running activities (>1min) | 10-60s |
| `WorkflowRunTimeout` | Max time for a single workflow run | Preventing runaway workflows | Hours-days |
| `WorkflowExecutionTimeout` | Total time across all runs (incl. continue-as-new) | Hard deadline on workflow | Rarely used |

### Retry Policy Fields

```go
&temporal.RetryPolicy{
    InitialInterval:        time.Second,     // First retry delay
    BackoffCoefficient:     2.0,             // Multiplier for each subsequent retry
    MaximumInterval:        time.Minute,     // Cap on retry delay
    MaximumAttempts:        0,               // 0 = unlimited (default)
    NonRetryableErrorTypes: []string{"X"},   // Error types to never retry
}
```

### Common Configurations

```go
// Fast API call (payment gateway)
workflow.ActivityOptions{
    StartToCloseTimeout: 10 * time.Second,
    RetryPolicy: &temporal.RetryPolicy{
        InitialInterval:        500 * time.Millisecond,
        MaximumAttempts:        3,
        NonRetryableErrorTypes: []string{"InsufficientFunds", "CardDeclined"},
    },
}

// Long-running batch processing
workflow.ActivityOptions{
    StartToCloseTimeout:    10 * time.Minute,
    HeartbeatTimeout:       30 * time.Second,
    ScheduleToCloseTimeout: 1 * time.Hour,
    RetryPolicy: &temporal.RetryPolicy{
        InitialInterval: 5 * time.Second,
        MaximumAttempts: 3,
    },
}

// Fire-and-forget notification (best effort)
workflow.ActivityOptions{
    StartToCloseTimeout: 5 * time.Second,
    RetryPolicy: &temporal.RetryPolicy{
        MaximumAttempts: 2,
    },
}
```

## Signal / Query / Update Patterns

### Signal (fire-and-forget input)

```go
// Workflow side:
ch := workflow.GetSignalChannel(ctx, "my-signal")
var payload SignalData
ch.Receive(ctx, &payload)

// Client side:
err := c.SignalWorkflow(ctx, workflowID, runID, "my-signal", payload)
```

### Query (read-only state access)

```go
// Workflow side:
workflow.SetQueryHandler(ctx, "my-query", func(param string) (Result, error) {
    return currentState, nil // No side effects!
})

// Client side:
resp, err := c.QueryWorkflow(ctx, workflowID, runID, "my-query", param)
var result Result
resp.Get(&result)
```

### Update (mutation with return value)

```go
// Workflow side:
workflow.SetUpdateHandler(ctx, "my-update", func(ctx workflow.Context, input UpdateInput) (UpdateResult, error) {
    // Can mutate state and execute activities.
    return UpdateResult{}, nil
})

// Client side:
handle, err := c.UpdateWorkflow(ctx, client.UpdateWorkflowOptions{
    WorkflowID: workflowID,
    UpdateName: "my-update",
    Args:       []interface{}{input},
})
var result UpdateResult
handle.Get(ctx, &result)
```

## Saga Pattern Template

```go
func SagaWorkflow(ctx workflow.Context, input SagaInput) error {
    var compensations []func(workflow.Context) error

    // Step N: Execute and register compensation.
    err := workflow.ExecuteActivity(ctx, StepN, input).Get(ctx, &result)
    if err != nil {
        return runCompensations(ctx, compensations, err)
    }
    compensations = append(compensations, func(ctx workflow.Context) error {
        return workflow.ExecuteActivity(ctx, UndoStepN, result.ID).Get(ctx, nil)
    })

    // ... more steps ...

    return nil
}

func runCompensations(ctx workflow.Context, comps []func(workflow.Context) error, origErr error) error {
    dctx, _ := workflow.NewDisconnectedCtx(ctx)
    dctx = workflow.WithActivityOptions(dctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
    })
    for i := len(comps) - 1; i >= 0; i-- {
        _ = comps[i](dctx) // Log errors but continue
    }
    return origErr
}
```

## Continue-as-New Template

```go
func LongRunningWorkflow(ctx workflow.Context, state State) error {
    for i := 0; i < maxIterationsBeforeReset; i++ {
        // Do work that generates events...
        state.Counter++
    }

    // Reset history, preserve state.
    return workflow.NewContinueAsNewError(ctx, LongRunningWorkflow, state)
}
```

## Versioning Template

```go
v := workflow.GetVersion(ctx, "change-id", workflow.DefaultVersion, 1)
if v == workflow.DefaultVersion {
    // Old code path (for workflows that started before the change).
} else {
    // New code path (for workflows that start after the change).
}
```

## Common Gotchas

### Non-Determinism Violations

| Mistake | Fix |
|---------|-----|
| `time.Now()` | `workflow.Now(ctx)` |
| `time.Sleep()` | `workflow.Sleep(ctx, d)` |
| `rand.Intn()` | `workflow.SideEffect(ctx, func ...)` |
| `go func(){}()` | `workflow.Go(ctx, func ...)` |
| `select {}` | `workflow.NewSelector(ctx)` |
| Iterating `map` in workflow | Sort keys first or use `[]struct` |
| Reading env vars | Pass as workflow input |
| Logging with `log.Println` | `workflow.GetLogger(ctx).Info(...)` |

### Payload and History Limits

| Limit | Value | Mitigation |
|-------|-------|------------|
| Single payload size | ~2 MB | Store large data externally, pass references |
| Event history size | ~50K events | Use continue-as-new before reaching limit |
| Signal payload | ~2 MB | Keep signal data minimal |
| Query response | ~2 MB | Paginate or summarize |

### Worker Configuration Gotchas

- Workers are stateless. Never store workflow state in worker memory that is not in workflow variables.
- A workflow and its activities do not need to run on the same worker (unless using local activities).
- Registering the same workflow type on different task queues creates independent pools.
- Worker shutdown is graceful: outstanding tasks complete before the worker stops.

## Testing Quick Reference

### Unit Test Setup

```go
func TestMyWorkflow(t *testing.T) {
    suite := &testsuite.WorkflowTestSuite{}
    env := suite.NewTestWorkflowEnvironment()

    // Mock activities.
    env.OnActivity(MyActivity, mock.Anything, mock.Anything).Return(result, nil)

    // Execute.
    env.ExecuteWorkflow(MyWorkflow, input)

    // Assert.
    require.True(t, env.IsWorkflowCompleted())
    require.NoError(t, env.GetWorkflowError())

    var output MyOutput
    require.NoError(t, env.GetWorkflowResult(&output))
    assert.Equal(t, expected, output)
}
```

### Testing Signals

```go
env.RegisterDelayedCallback(func() {
    env.SignalWorkflow("signal-name", signalPayload)
}, 5*time.Second) // Fires after 5s of "workflow time" (instant in test)
```

### Testing Queries

```go
env.ExecuteWorkflow(MyWorkflow, input)

result, err := env.QueryWorkflow("query-name", queryParam)
require.NoError(t, err)
var output QueryResult
require.NoError(t, result.Get(&output))
```

### Asserting Activity Calls

```go
// Verify an activity was called with specific arguments.
env.OnActivity(ChargeCustomer, mock.Anything, ChargeInput{
    CustomerID: "cust-123",
    Amount:     9900,
}).Return(ChargeResult{TransactionID: "txn-1"}, nil).Once()

env.ExecuteWorkflow(MyWorkflow, input)
env.AssertExpectations(t)
```

## Selector Pattern (Racing Timers, Signals, Activities)

```go
selector := workflow.NewSelector(ctx)

// Race a timer against a signal.
selector.AddFuture(workflow.NewTimer(ctx, 24*time.Hour), func(f workflow.Future) {
    // Timer won.
})

selector.AddReceive(workflow.GetSignalChannel(ctx, "cancel"), func(ch workflow.ReceiveChannel, more bool) {
    ch.Receive(ctx, &data)
    // Signal won.
})

// Race two activities.
f1 := workflow.ExecuteActivity(ctx, Activity1, input)
f2 := workflow.ExecuteActivity(ctx, Activity2, input)
selector.AddFuture(f1, func(f workflow.Future) { /* f1 finished first */ })
selector.AddFuture(f2, func(f workflow.Future) { /* f2 finished first */ })

selector.Select(ctx) // Blocks until one case fires.
```

## Quick Reference: When to Use What

| Problem | Solution |
|---------|----------|
| Run code after a delay | `workflow.Sleep(ctx, duration)` |
| Wait for external input | Signal channel |
| Read workflow state externally | Query handler |
| Mutate state + get response | Update handler |
| Run code in parallel | `workflow.Go(ctx, func ...)` |
| Race timer vs signal | `workflow.NewSelector(ctx)` |
| Reset event history | `workflow.NewContinueAsNewError(ctx, ...)` |
| Sub-task with own history | Child workflow |
| Non-deterministic value in workflow | `workflow.SideEffect(ctx, ...)` |
| Fast, local operation | Local activity |
| Deploy new code for running workflows | `workflow.GetVersion(ctx, ...)` |
| Distributed transaction with rollback | Saga pattern (compensations) |
| Prevent duplicate workflow | Deterministic workflow ID + reuse policy |
| Prevent duplicate charge | Idempotency key on the activity/API call |
| Process unbounded list | Batch + continue-as-new |
| Schedule recurring work | Cron workflow or Schedules API |
