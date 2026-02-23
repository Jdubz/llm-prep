# Module 02 Deep Dive: Advanced SDK Patterns for Billing Systems

This document covers the patterns that separate someone who has read the docs from someone who has built production systems with Temporal. Every pattern here maps to a real problem on the billing/metering team.

---

## 1. The Saga Pattern with Temporal

### The Problem

Distributed transactions across multiple services are hard. In a traditional system, you might use a two-phase commit (fragile, slow) or hope for the best (data inconsistency). The saga pattern breaks a transaction into steps, each with a compensating action that undoes it if a later step fails.

**Node.js comparison:** In Express, you might implement this with a chain of try/catch blocks, each catch manually calling "undo" functions, with a database tracking which steps completed. If the server crashes between step 3 and its compensation, you are in an inconsistent state. With Temporal, the saga runs in a workflow -- crashes are a non-issue.

### Implementation Pattern

The pattern is straightforward: execute steps sequentially, track compensations, and if any step fails, run compensations in reverse order.

```go
func CustomerOnboardingSaga(ctx workflow.Context, input OnboardingInput) error {
    logger := workflow.GetLogger(ctx)

    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            MaximumAttempts: 3,
        },
    })

    // Compensation stack: functions to call if we need to roll back.
    var compensations []func(ctx workflow.Context) error

    // Step 1: Create account in the auth service.
    var account AccountResult
    err := workflow.ExecuteActivity(actCtx, CreateAccount, input).Get(ctx, &account)
    if err != nil {
        return fmt.Errorf("create account: %w", err)
    }
    compensations = append(compensations, func(ctx workflow.Context) error {
        return workflow.ExecuteActivity(ctx, DeleteAccount, account.AccountID).Get(ctx, nil)
    })
    logger.Info("Account created", "accountID", account.AccountID)

    // Step 2: Provision a Temporal namespace for the customer.
    var ns NamespaceResult
    err = workflow.ExecuteActivity(actCtx, ProvisionNamespace, account.AccountID).Get(ctx, &ns)
    if err != nil {
        return compensate(ctx, compensations, fmt.Errorf("provision namespace: %w", err))
    }
    compensations = append(compensations, func(ctx workflow.Context) error {
        return workflow.ExecuteActivity(ctx, DeprovisionNamespace, ns.NamespaceID).Get(ctx, nil)
    })
    logger.Info("Namespace provisioned", "namespaceID", ns.NamespaceID)

    // Step 3: Set up billing (create Stripe customer, subscription).
    var billing BillingResult
    err = workflow.ExecuteActivity(actCtx, SetupBilling, SetupBillingInput{
        AccountID: account.AccountID,
        Plan:      input.Plan,
        Email:     input.Email,
    }).Get(ctx, &billing)
    if err != nil {
        return compensate(ctx, compensations, fmt.Errorf("setup billing: %w", err))
    }
    compensations = append(compensations, func(ctx workflow.Context) error {
        return workflow.ExecuteActivity(ctx, TeardownBilling, billing.SubscriptionID).Get(ctx, nil)
    })
    logger.Info("Billing configured", "subscriptionID", billing.SubscriptionID)

    // Step 4: Send welcome email (no compensation needed -- it is fine if this sent but later steps fail...
    // Actually, there are no later steps. But if there were, we would not compensate an email).
    err = workflow.ExecuteActivity(actCtx, SendWelcomeEmail, input.Email).Get(ctx, nil)
    if err != nil {
        return compensate(ctx, compensations, fmt.Errorf("send welcome email: %w", err))
    }

    logger.Info("Onboarding complete", "accountID", account.AccountID)
    return nil
}

// compensate runs all compensation functions in reverse order.
func compensate(ctx workflow.Context, compensations []func(ctx workflow.Context) error, originalErr error) error {
    logger := workflow.GetLogger(ctx)
    logger.Error("Saga failed, running compensations", "error", originalErr)

    // Use a disconnected context so compensations run even if the workflow is cancelled.
    compensationCtx, _ := workflow.NewDisconnectedCtx(ctx)
    compensationCtx = workflow.WithActivityOptions(compensationCtx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            MaximumAttempts: 5, // Try harder on compensations
        },
    })

    // Run compensations in reverse order.
    for i := len(compensations) - 1; i >= 0; i-- {
        err := compensations[i](compensationCtx)
        if err != nil {
            logger.Error("Compensation failed", "step", i, "error", err)
            // Log but continue -- try to compensate as much as possible.
            // In production, you might also alert on this.
        }
    }

    return originalErr
}
```

### Key Design Decisions

**Disconnected context for compensations.** If the parent workflow is cancelled (e.g., customer changed their mind), compensations should still run. `workflow.NewDisconnectedCtx` creates a context that is not cancelled when the parent is.

**Compensations are activities, not inline code.** Each compensation is an activity with its own retry policy. If a compensation fails (e.g., the Stripe API is down), Temporal retries it. This is vastly more reliable than try/catch in a normal application.

**Not every step needs compensation.** Sending an email is idempotent and harmless -- no compensation needed. A financial transaction absolutely needs compensation.

**Compensation order matters.** Run compensations in reverse: if you provisioned a namespace then set up billing, tear down billing first, then deprovision the namespace. This avoids reference integrity issues.

---

## 2. Billing/Metering-Specific Patterns

### Subscription Lifecycle Workflow

A subscription moves through states: `trial -> active -> suspended -> cancelled`. Each transition involves activities and timers. This is a natural fit for a single long-running workflow.

```go
type SubscriptionState struct {
    CustomerID string
    Plan       string
    Status     string // trial, active, suspended, cancelled
    TrialEnd   time.Time
    CycleCount int
}

func SubscriptionLifecycleWorkflow(ctx workflow.Context, state SubscriptionState) error {
    logger := workflow.GetLogger(ctx)

    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy:         &temporal.RetryPolicy{MaximumAttempts: 5},
    })

    // Query handler for external visibility.
    _ = workflow.SetQueryHandler(ctx, "status", func() (SubscriptionState, error) {
        return state, nil
    })

    // Signal channels.
    cancelCh := workflow.GetSignalChannel(ctx, "cancel")
    upgradeCh := workflow.GetSignalChannel(ctx, "upgrade")

    switch state.Status {
    case "trial":
        // Wait for trial to end, but allow early upgrade or cancellation.
        trialDuration := state.TrialEnd.Sub(workflow.Now(ctx))
        if trialDuration > 0 {
            timerFuture := workflow.NewTimer(ctx, trialDuration)
            selector := workflow.NewSelector(ctx)

            selector.AddFuture(timerFuture, func(f workflow.Future) {
                state.Status = "active"
                logger.Info("Trial ended, converting to active")
            })
            selector.AddReceive(cancelCh, func(ch workflow.ReceiveChannel, more bool) {
                ch.Receive(ctx, nil)
                state.Status = "cancelled"
            })
            selector.AddReceive(upgradeCh, func(ch workflow.ReceiveChannel, more bool) {
                var newPlan string
                ch.Receive(ctx, &newPlan)
                state.Plan = newPlan
                state.Status = "active" // Early conversion
            })
            selector.Select(ctx)
        } else {
            state.Status = "active"
        }

        if state.Status == "cancelled" {
            return workflow.ExecuteActivity(actCtx, RecordCancellation, state.CustomerID).Get(ctx, nil)
        }
        // Continue to active -- continue-as-new with updated state.
        return workflow.NewContinueAsNewError(ctx, SubscriptionLifecycleWorkflow, state)

    case "active":
        // Process one billing cycle.
        err := workflow.ExecuteActivity(actCtx, ChargeCustomer, ChargeInput{
            CustomerID: state.CustomerID,
            Plan:       state.Plan,
        }).Get(ctx, nil)

        if err != nil {
            state.Status = "suspended"
            _ = workflow.ExecuteActivity(actCtx, NotifyPaymentFailed, state.CustomerID).Get(ctx, nil)
            return workflow.NewContinueAsNewError(ctx, SubscriptionLifecycleWorkflow, state)
        }

        state.CycleCount++
        // Sleep until next billing cycle, listening for signals.
        timerFuture := workflow.NewTimer(ctx, 30*24*time.Hour)
        selector := workflow.NewSelector(ctx)

        selector.AddFuture(timerFuture, func(f workflow.Future) {})
        selector.AddReceive(cancelCh, func(ch workflow.ReceiveChannel, more bool) {
            ch.Receive(ctx, nil)
            state.Status = "cancelled"
        })
        selector.Select(ctx)

        if state.Status == "cancelled" {
            _ = workflow.ExecuteActivity(actCtx, ProcessRefund, state).Get(ctx, nil)
            return nil
        }
        return workflow.NewContinueAsNewError(ctx, SubscriptionLifecycleWorkflow, state)

    case "suspended":
        // Wait for payment update or grace period expiry.
        paymentCh := workflow.GetSignalChannel(ctx, "payment-updated")
        gracePeriod := workflow.NewTimer(ctx, 7*24*time.Hour)

        selector := workflow.NewSelector(ctx)
        resolved := false

        selector.AddReceive(paymentCh, func(ch workflow.ReceiveChannel, more bool) {
            ch.Receive(ctx, nil)
            resolved = true
            state.Status = "active"
        })
        selector.AddFuture(gracePeriod, func(f workflow.Future) {
            state.Status = "cancelled"
        })
        selector.Select(ctx)

        if !resolved {
            return workflow.ExecuteActivity(actCtx, ProcessCancellation, state.CustomerID).Get(ctx, nil)
        }
        return workflow.NewContinueAsNewError(ctx, SubscriptionLifecycleWorkflow, state)
    }

    return nil
}
```

### Metering Aggregation Workflow

Metering workflows collect raw usage events, deduplicate them, aggregate them into billable units, and store the results. This pattern handles millions of events reliably.

```go
func MeteringAggregationWorkflow(ctx workflow.Context, input MeteringInput) error {
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout:    5 * time.Minute,
        HeartbeatTimeout:       30 * time.Second,
        RetryPolicy:            &temporal.RetryPolicy{MaximumAttempts: 3},
    })

    // Step 1: Fetch raw events for the period.
    var rawEvents []MeteringEvent
    err := workflow.ExecuteActivity(actCtx, FetchRawEvents, FetchInput{
        CustomerID: input.CustomerID,
        StartTime:  input.PeriodStart,
        EndTime:    input.PeriodEnd,
    }).Get(ctx, &rawEvents)
    if err != nil {
        return fmt.Errorf("fetch raw events: %w", err)
    }

    // Step 2: Deduplicate (using event IDs / idempotency keys).
    var dedupedEvents []MeteringEvent
    err = workflow.ExecuteActivity(actCtx, DeduplicateEvents, rawEvents).Get(ctx, &dedupedEvents)
    if err != nil {
        return fmt.Errorf("deduplicate events: %w", err)
    }

    // Step 3: Aggregate into billable units.
    var aggregated AggregatedUsage
    err = workflow.ExecuteActivity(actCtx, AggregateUsage, dedupedEvents).Get(ctx, &aggregated)
    if err != nil {
        return fmt.Errorf("aggregate usage: %w", err)
    }

    // Step 4: Store aggregated results.
    err = workflow.ExecuteActivity(actCtx, StoreAggregatedUsage, StoreInput{
        CustomerID: input.CustomerID,
        Period:     input.PeriodStart.Format("2006-01"),
        Usage:      aggregated,
    }).Get(ctx, nil)
    if err != nil {
        return fmt.Errorf("store aggregated usage: %w", err)
    }

    return nil
}
```

**Design note on large payloads:** If raw events are large (millions of records), do not pass them through the workflow. Instead, have activities write to/read from an external store (S3, database) and pass only references (keys, URIs) through the workflow. Temporal has a payload size limit (typically 2MB per argument), and large payloads slow down replay.

### Invoice Generation Workflow

```go
func InvoiceGenerationWorkflow(ctx workflow.Context, input InvoiceInput) (InvoiceResult, error) {
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 60 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            MaximumAttempts:        5,
            NonRetryableErrorTypes: []string{"InvalidPricingConfig"},
        },
    })

    // Step 1: Calculate usage for the billing period.
    var usage UsageSummary
    err := workflow.ExecuteActivity(actCtx, CalculateUsage, input.CustomerID, input.Period).Get(ctx, &usage)
    if err != nil {
        return InvoiceResult{}, fmt.Errorf("calculate usage: %w", err)
    }

    // Step 2: Apply pricing rules.
    var lineItems []LineItem
    err = workflow.ExecuteActivity(actCtx, ApplyPricing, ApplyPricingInput{
        Usage:      usage,
        Plan:       input.Plan,
        CustomerID: input.CustomerID,
    }).Get(ctx, &lineItems)
    if err != nil {
        return InvoiceResult{}, fmt.Errorf("apply pricing: %w", err)
    }

    // Step 3: Generate the invoice document.
    var invoice Invoice
    err = workflow.ExecuteActivity(actCtx, GenerateInvoice, GenerateInvoiceInput{
        CustomerID: input.CustomerID,
        Period:     input.Period,
        LineItems:  lineItems,
    }).Get(ctx, &invoice)
    if err != nil {
        return InvoiceResult{}, fmt.Errorf("generate invoice: %w", err)
    }

    // Step 4: Charge the customer (with idempotency key).
    chargeCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
        RetryPolicy: &temporal.RetryPolicy{
            MaximumAttempts:        3,
            NonRetryableErrorTypes: []string{"InsufficientFunds", "CardDeclined"},
        },
    })
    var charge ChargeResult
    err = workflow.ExecuteActivity(chargeCtx, ChargeCustomer, ChargeInput{
        CustomerID:     input.CustomerID,
        Amount:         invoice.Total,
        IdempotencyKey: fmt.Sprintf("invoice-%s-%s", input.CustomerID, input.Period),
    }).Get(ctx, &charge)
    if err != nil {
        // Payment failed. Record the invoice as unpaid and notify.
        _ = workflow.ExecuteActivity(actCtx, RecordUnpaidInvoice, invoice.ID).Get(ctx, nil)
        return InvoiceResult{InvoiceID: invoice.ID, Status: "unpaid"}, nil
    }

    // Step 5: Record the payment.
    err = workflow.ExecuteActivity(actCtx, RecordPayment, RecordPaymentInput{
        InvoiceID:     invoice.ID,
        TransactionID: charge.TransactionID,
        Amount:        charge.Amount,
    }).Get(ctx, nil)
    if err != nil {
        return InvoiceResult{}, fmt.Errorf("record payment: %w", err)
    }

    return InvoiceResult{
        InvoiceID:     invoice.ID,
        TransactionID: charge.TransactionID,
        Status:        "paid",
    }, nil
}
```

### Idempotency Patterns

Idempotency is non-negotiable in billing. Charging a customer twice is a support nightmare. Temporal provides several mechanisms:

**1. Workflow ID as idempotency key.**

```go
// Using a deterministic workflow ID prevents duplicate workflows.
we, err := c.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
    ID: fmt.Sprintf("invoice-%s-%s", customerID, period), // Deterministic
    // WorkflowIDReusePolicy controls what happens if this ID already exists.
    WorkflowIDReusePolicy: enums.WORKFLOW_ID_REUSE_POLICY_REJECT_DUPLICATE,
    TaskQueue:             "billing-task-queue",
}, InvoiceGenerationWorkflow, input)
```

**2. Activity-level idempotency keys.**

```go
func ChargeCustomer(ctx context.Context, input ChargeInput) (ChargeResult, error) {
    // Pass the idempotency key to the payment gateway.
    // If this activity is retried, the gateway returns the same result.
    result, err := stripe.Charges.New(&stripe.ChargeParams{
        Amount:         stripe.Int64(input.Amount),
        Currency:       stripe.String("usd"),
        Customer:       stripe.String(input.CustomerID),
        IdempotencyKey: stripe.String(input.IdempotencyKey),
    })
    if err != nil {
        return ChargeResult{}, err
    }
    return ChargeResult{TransactionID: result.ID, Amount: result.Amount}, nil
}
```

**3. Workflow ID reuse policies.**

| Policy | Behavior |
|--------|----------|
| `ALLOW_DUPLICATE` | Start a new run even if a completed run exists with the same ID |
| `ALLOW_DUPLICATE_FAILED_ONLY` | Only start if the previous run failed |
| `REJECT_DUPLICATE` | Reject if any run exists (completed or running) |
| `TERMINATE_IF_RUNNING` | Terminate the running instance and start a new one |

---

## 3. Workflow Versioning

### The Problem

You deploy new workflow code. But existing workflows started with the old code are still running. On the next replay, the worker executes the new code, but the event history was created by the old code. The command sequence does not match. Replay fails. Non-determinism error. The workflow is stuck.

This is one of the hardest problems in durable execution, and Temporal gives you `workflow.GetVersion()` to solve it.

### workflow.GetVersion

```go
func SubscriptionWorkflow(ctx workflow.Context, state SubscriptionState) error {
    // Version 1: original implementation
    // Version 2: added a new activity between charge and notification

    v := workflow.GetVersion(ctx, "add-audit-log", workflow.DefaultVersion, 2)

    // Charge the customer (both versions).
    err := workflow.ExecuteActivity(ctx, ChargeCustomer, state.CustomerID).Get(ctx, nil)
    if err != nil {
        return err
    }

    if v >= 2 {
        // NEW: write an audit log entry (only in version 2+).
        err = workflow.ExecuteActivity(ctx, WriteAuditLog, AuditEntry{
            CustomerID: state.CustomerID,
            Action:     "charge",
        }).Get(ctx, nil)
        if err != nil {
            return err
        }
    }

    // Send notification (both versions).
    return workflow.ExecuteActivity(ctx, SendNotification, state.CustomerID).Get(ctx, nil)
}
```

**How it works:**
- `workflow.GetVersion(ctx, changeID, minSupported, maxSupported)` records a version marker in the event history.
- For new workflow executions, it returns `maxSupported` (2 in this case).
- For existing executions that have no version marker for this change ID, it returns `workflow.DefaultVersion` (-1).
- On replay, it reads the recorded version from history, ensuring determinism.

### Patching Strategy

The lifecycle of a version patch:

1. **Add the version check.** Deploy code that handles both old and new paths.
2. **Wait for all old workflows to complete.** Monitor for workflows still running the old path.
3. **Remove the old path.** Update `minSupported` to the new version.
4. **Eventually remove the version check entirely.** Once no workflow in history predates the change.

```go
// PHASE 1: Deploy with both paths
v := workflow.GetVersion(ctx, "new-pricing-engine", workflow.DefaultVersion, 1)
if v == workflow.DefaultVersion {
    // Old path: original pricing logic
    err = workflow.ExecuteActivity(ctx, CalculatePricingV1, input).Get(ctx, &price)
} else {
    // New path: updated pricing engine
    err = workflow.ExecuteActivity(ctx, CalculatePricingV2, input).Get(ctx, &price)
}

// PHASE 2: After all old workflows complete, remove old path
v := workflow.GetVersion(ctx, "new-pricing-engine", 1, 1)
// v is always 1 now -- old path is gone
err = workflow.ExecuteActivity(ctx, CalculatePricingV2, input).Get(ctx, &price)

// PHASE 3: Eventually remove the version check entirely
err = workflow.ExecuteActivity(ctx, CalculatePricingV2, input).Get(ctx, &price)
```

### Why This Matters for Billing

Subscription workflows can run for months or years. When you update pricing logic, invoice format, or payment processing, you cannot just deploy and forget. Existing subscription workflows need to continue running the version of the code they started with, while new subscriptions use the updated code. `GetVersion` makes this possible without maintaining separate workflow definitions.

---

## 4. Advanced Concurrency Patterns

### workflow.Go for Parallel Activities

`workflow.Go` spawns a coroutine within the workflow. Unlike Go's `go` keyword, workflow coroutines are tracked by Temporal and participate in replay.

```go
func ParallelOnboardingWorkflow(ctx workflow.Context, input OnboardingInput) error {
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
    })

    // Fan-out: run three independent setup tasks in parallel.
    var accountErr, namespaceErr, billingErr error
    var account AccountResult
    var ns NamespaceResult
    var billing BillingResult

    workflow.Go(ctx, func(gCtx workflow.Context) {
        accountErr = workflow.ExecuteActivity(actCtx, CreateAccount, input).Get(gCtx, &account)
    })

    workflow.Go(ctx, func(gCtx workflow.Context) {
        namespaceErr = workflow.ExecuteActivity(actCtx, ProvisionNamespace, input).Get(gCtx, &ns)
    })

    workflow.Go(ctx, func(gCtx workflow.Context) {
        billingErr = workflow.ExecuteActivity(actCtx, SetupBilling, input).Get(gCtx, &billing)
    })

    // Wait for all to complete. In workflow code, we need to use a
    // mechanism to wait -- workflow.Await or a WaitGroup-like pattern.

    // Simple approach: use workflow.Await with a condition
    err := workflow.Await(ctx, func() bool {
        // This is evaluated after each event. Returns true when all are done.
        // Note: we check for results or errors being set.
        return (account.ID != "" || accountErr != nil) &&
               (ns.ID != "" || namespaceErr != nil) &&
               (billing.ID != "" || billingErr != nil)
    })
    if err != nil {
        return err
    }

    // Check for errors.
    if accountErr != nil {
        return fmt.Errorf("create account: %w", accountErr)
    }
    if namespaceErr != nil {
        return fmt.Errorf("provision namespace: %w", namespaceErr)
    }
    if billingErr != nil {
        return fmt.Errorf("setup billing: %w", billingErr)
    }

    return nil
}
```

### workflow.NewSelector -- Temporal's Select

`workflow.NewSelector` is the Temporal equivalent of Go's `select` statement, but it works with Temporal futures, channels, and timers.

```go
func PaymentRetryWorkflow(ctx workflow.Context, input PaymentInput) error {
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 30 * time.Second,
    })

    retryIntervals := []time.Duration{
        1 * time.Hour,
        24 * time.Hour,
        3 * 24 * time.Hour,
        7 * 24 * time.Hour,
    }

    paymentUpdatedCh := workflow.GetSignalChannel(ctx, "payment-method-updated")

    for attempt, interval := range retryIntervals {
        // Try to charge.
        err := workflow.ExecuteActivity(actCtx, ChargeCustomer, input).Get(ctx, nil)
        if err == nil {
            return nil // Success
        }

        // Charge failed. Wait for retry interval OR payment method update.
        selector := workflow.NewSelector(ctx)
        paymentUpdated := false

        selector.AddFuture(workflow.NewTimer(ctx, interval), func(f workflow.Future) {
            // Timer expired. Will retry on next loop iteration.
        })

        selector.AddReceive(paymentUpdatedCh, func(ch workflow.ReceiveChannel, more bool) {
            ch.Receive(ctx, nil)
            paymentUpdated = true
            // Payment method updated. Retry immediately.
        })

        selector.Select(ctx)

        if paymentUpdated {
            workflow.GetLogger(ctx).Info("Payment method updated, retrying immediately",
                "attempt", attempt+1)
        }
    }

    // All retries exhausted.
    return workflow.ExecuteActivity(actCtx, SuspendAccount, input.CustomerID).Get(ctx, nil)
}
```

### Fan-Out/Fan-In with Child Workflows

For large-scale parallel processing, use child workflows:

```go
func MonthlyBillingRunWorkflow(ctx workflow.Context, input MonthlyBillingInput) error {
    // Fetch all active customers.
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 60 * time.Second,
    })
    var customers []string
    err := workflow.ExecuteActivity(actCtx, FetchActiveCustomers).Get(ctx, &customers)
    if err != nil {
        return err
    }

    // Fan-out: start a child workflow for each customer.
    var futures []workflow.ChildWorkflowFuture
    for _, customerID := range customers {
        childCtx := workflow.WithChildOptions(ctx, workflow.ChildWorkflowOptions{
            WorkflowID: fmt.Sprintf("bill-%s-%s", customerID, input.Period),
        })
        future := workflow.ExecuteChildWorkflow(childCtx, InvoiceGenerationWorkflow, InvoiceInput{
            CustomerID: customerID,
            Period:     input.Period,
        })
        futures = append(futures, future)
    }

    // Fan-in: wait for all child workflows to complete.
    var failedCustomers []string
    for i, future := range futures {
        var result InvoiceResult
        if err := future.Get(ctx, &result); err != nil {
            failedCustomers = append(failedCustomers, customers[i])
            workflow.GetLogger(ctx).Error("Invoice generation failed",
                "customerID", customers[i], "error", err)
        }
    }

    if len(failedCustomers) > 0 {
        // Record failures for manual review.
        _ = workflow.ExecuteActivity(actCtx, RecordBillingFailures, failedCustomers).Get(ctx, nil)
    }

    return nil
}
```

**Important consideration:** If you have 10,000 customers, you probably do not want 10,000 concurrent child workflows. Batch them or use a semaphore pattern to limit concurrency.

### Rate Limiting with Semaphores

```go
func BillingRunWithRateLimit(ctx workflow.Context, customers []string, period string) error {
    maxConcurrent := 50 // Process 50 customers at a time
    sem := make(chan struct{}, maxConcurrent)

    var mu sync.Mutex // Protect shared state -- but workflow.Go uses cooperative scheduling
    var errors []error

    for _, customerID := range customers {
        custID := customerID // Capture loop variable

        // Acquire semaphore slot by using workflow.Go and a channel
        workflow.Go(ctx, func(gCtx workflow.Context) {
            childCtx := workflow.WithChildOptions(gCtx, workflow.ChildWorkflowOptions{
                WorkflowID: fmt.Sprintf("bill-%s-%s", custID, period),
            })
            err := workflow.ExecuteChildWorkflow(childCtx, InvoiceGenerationWorkflow, InvoiceInput{
                CustomerID: custID,
                Period:     period,
            }).Get(gCtx, nil)
            if err != nil {
                mu.Lock()
                errors = append(errors, fmt.Errorf("customer %s: %w", custID, err))
                mu.Unlock()
            }
        })
    }

    // Note: In practice, you would implement a proper semaphore using
    // workflow channels and selectors for determinism-safe concurrency control.
    // The above is simplified for illustration.
    return nil
}
```

---

## 5. Error Handling and Recovery

### Application Errors vs System Errors

Temporal distinguishes between errors that should be retried and errors that should not:

```go
// Application error -- non-retryable business logic failure.
func ValidateInvoice(ctx context.Context, invoice Invoice) error {
    if invoice.Total < 0 {
        return temporal.NewNonRetryableApplicationError(
            "invoice total cannot be negative",
            "InvalidInvoice",
            nil, // cause
            invoice, // details (available to the workflow)
        )
    }
    return nil
}

// Retryable error -- transient failure.
func FetchUsageData(ctx context.Context, customerID string) (UsageData, error) {
    data, err := metricsDB.Query(ctx, customerID)
    if err != nil {
        // Return a plain error -- Temporal will retry based on the RetryPolicy.
        return UsageData{}, fmt.Errorf("querying usage for %s: %w", customerID, err)
    }
    return data, nil
}
```

### Custom Error Types

Define domain-specific errors for clean handling in workflows:

```go
// In your shared types package:
const (
    ErrTypeInsufficientFunds = "InsufficientFunds"
    ErrTypeCardDeclined      = "CardDeclined"
    ErrTypeCustomerNotFound  = "CustomerNotFound"
    ErrTypeRateLimited       = "RateLimited"
)

// In your activity:
func ChargeCustomer(ctx context.Context, input ChargeInput) (ChargeResult, error) {
    result, err := gateway.Charge(ctx, input)
    if err != nil {
        switch {
        case isInsufficientFunds(err):
            return ChargeResult{}, temporal.NewNonRetryableApplicationError(
                err.Error(), ErrTypeInsufficientFunds, err)
        case isCardDeclined(err):
            return ChargeResult{}, temporal.NewNonRetryableApplicationError(
                err.Error(), ErrTypeCardDeclined, err)
        case isRateLimited(err):
            // Retryable, but the error type can be checked for special handling.
            return ChargeResult{}, temporal.NewApplicationError(
                err.Error(), ErrTypeRateLimited, err)
        default:
            return ChargeResult{}, err // Generic retryable error
        }
    }
    return result, nil
}

// In your workflow:
func handleChargeError(err error) string {
    var appErr *temporal.ApplicationError
    if errors.As(err, &appErr) {
        switch appErr.Type() {
        case ErrTypeInsufficientFunds:
            return "suspended" // Suspend subscription
        case ErrTypeCardDeclined:
            return "payment_failed" // Request new payment method
        default:
            return "error" // Unexpected failure
        }
    }
    return "error"
}
```

### Workflow Cancellation and Cleanup

When a workflow is cancelled (by the client or a parent workflow), you often need to run cleanup logic:

```go
func SubscriptionWorkflow(ctx workflow.Context, state SubscriptionState) error {
    // Set up a deferred cleanup that runs even on cancellation.
    defer func() {
        if !errors.Is(ctx.Err(), workflow.ErrCanceled) {
            return // Not cancelled, no cleanup needed
        }

        // Create a disconnected context for cleanup activities.
        // The original context is cancelled, so we need a new one.
        cleanupCtx, _ := workflow.NewDisconnectedCtx(ctx)
        cleanupCtx = workflow.WithActivityOptions(cleanupCtx, workflow.ActivityOptions{
            StartToCloseTimeout: 30 * time.Second,
        })

        // Run cleanup activities.
        _ = workflow.ExecuteActivity(cleanupCtx, RecordCancellation, state.CustomerID).Get(cleanupCtx, nil)
        _ = workflow.ExecuteActivity(cleanupCtx, ProcessFinalRefund, state).Get(cleanupCtx, nil)
    }()

    // ... normal workflow logic
    return nil
}
```

---

## 6. Testing Temporal Workflows

### Unit Testing with the Test Framework

Temporal provides a test framework that mocks the server and lets you control time:

```go
func TestSubscriptionWorkflow_HappyPath(t *testing.T) {
    testSuite := &testsuite.WorkflowTestSuite{}
    env := testSuite.NewTestWorkflowEnvironment()

    // Mock activities.
    env.OnActivity(ChargeCustomer, mock.Anything, mock.Anything).Return(ChargeResult{
        TransactionID: "txn-123",
        Amount:        9900,
    }, nil)

    env.OnActivity(SendNotification, mock.Anything, mock.Anything).Return(nil)

    // Execute the workflow.
    env.ExecuteWorkflow(SubscriptionWorkflow, SubscriptionState{
        CustomerID: "cust-123",
        Plan:       "pro",
        Status:     "active",
    })

    // Assert the workflow completed.
    require.True(t, env.IsWorkflowCompleted())
    require.NoError(t, env.GetWorkflowError())
}
```

### Testing Signals

```go
func TestSubscriptionWorkflow_Cancellation(t *testing.T) {
    testSuite := &testsuite.WorkflowTestSuite{}
    env := testSuite.NewTestWorkflowEnvironment()

    env.OnActivity(ProcessCancellation, mock.Anything, "cust-123").Return(nil)

    // Register a callback that sends a signal after 5 seconds.
    env.RegisterDelayedCallback(func() {
        env.SignalWorkflow("cancel-subscription", "customer-requested")
    }, 5*time.Second)

    env.ExecuteWorkflow(SubscriptionWorkflow, SubscriptionState{
        CustomerID: "cust-123",
        Plan:       "pro",
        Status:     "active",
    })

    require.True(t, env.IsWorkflowCompleted())
    require.NoError(t, env.GetWorkflowError())

    // Verify ProcessCancellation was called.
    env.AssertExpectations(t)
}
```

### Time-Skipping

The test framework automatically skips timers, so a test with a 30-day `workflow.Sleep` runs in milliseconds:

```go
func TestTrialExpiry(t *testing.T) {
    testSuite := &testsuite.WorkflowTestSuite{}
    env := testSuite.NewTestWorkflowEnvironment()

    env.OnActivity(ConvertTrialToPaid, mock.Anything, "cust-123").Return(nil)

    // This workflow sleeps for 14 days. The test framework skips the timer.
    env.ExecuteWorkflow(TrialWorkflow, TrialInput{CustomerID: "cust-123"})

    require.True(t, env.IsWorkflowCompleted())
    require.NoError(t, env.GetWorkflowError())
}
```

### Testing Activity Failures and Retries

```go
func TestSubscriptionWorkflow_PaymentFailure(t *testing.T) {
    testSuite := &testsuite.WorkflowTestSuite{}
    env := testSuite.NewTestWorkflowEnvironment()

    // Simulate payment failure.
    env.OnActivity(ChargeCustomer, mock.Anything, mock.Anything).Return(
        ChargeResult{},
        temporal.NewNonRetryableApplicationError("insufficient funds", "InsufficientFunds", nil),
    )

    env.OnActivity(NotifyPaymentFailed, mock.Anything, "cust-123").Return(nil)
    env.OnActivity(ProcessCancellation, mock.Anything, "cust-123").Return(nil)

    // No payment-updated signal, so grace period expires.
    env.ExecuteWorkflow(SubscriptionWorkflow, SubscriptionState{
        CustomerID: "cust-123",
        Plan:       "pro",
        Status:     "active",
    })

    require.True(t, env.IsWorkflowCompleted())
    env.AssertExpectations(t)
}
```

### Integration Testing

For end-to-end tests, run against a real Temporal Server (or the Temporal CLI dev server):

```go
func TestInvoiceWorkflow_Integration(t *testing.T) {
    if testing.Short() {
        t.Skip("skipping integration test")
    }

    // Connect to a real Temporal Server.
    c, err := client.Dial(client.Options{
        HostPort:  "localhost:7233",
        Namespace: "test",
    })
    require.NoError(t, err)
    defer c.Close()

    // Start a worker with real activities.
    w := worker.New(c, "test-billing-queue", worker.Options{})
    w.RegisterWorkflow(InvoiceGenerationWorkflow)
    w.RegisterActivity(&BillingActivities{
        db:      testDB,
        gateway: mockGateway,
    })
    go w.Run(worker.InterruptCh())
    defer w.Stop()

    // Execute the workflow.
    we, err := c.ExecuteWorkflow(context.Background(), client.StartWorkflowOptions{
        ID:        "test-invoice-" + uuid.New().String(),
        TaskQueue: "test-billing-queue",
    }, InvoiceGenerationWorkflow, InvoiceInput{
        CustomerID: "test-cust-123",
        Period:     "2025-01",
    })
    require.NoError(t, err)

    // Wait for result.
    var result InvoiceResult
    err = we.Get(context.Background(), &result)
    require.NoError(t, err)
    assert.Equal(t, "paid", result.Status)
}
```

### Testing Best Practices

1. **Unit test workflows with mocked activities.** This tests your orchestration logic without external dependencies.
2. **Unit test activities independently.** They are regular Go functions -- test them with standard Go testing.
3. **Use the test environment's time-skipping.** Never use real sleeps in tests.
4. **Test error paths explicitly.** Mock activities to return specific errors and verify the workflow handles them correctly.
5. **Integration test the full flow.** Use the Temporal CLI dev server (`temporal server start-dev`) for fast, isolated integration tests.
6. **Test continue-as-new.** Verify that state is correctly passed across continue-as-new boundaries.

---

## Key Takeaways for Interview

1. **The Saga pattern in Temporal is just activities + error handling + compensation.** No saga framework needed. The durable execution model guarantees compensations run even after crashes.
2. **Billing workflows are inherently long-running.** Continue-as-new, versioning, and event history management are not academic concerns -- they are daily realities.
3. **Idempotency is a first-class concern.** Workflow IDs, activity idempotency keys, and reuse policies prevent duplicate charges.
4. **Versioning is how you deploy without breaking running workflows.** `GetVersion` is the mechanism; phased rollout is the strategy.
5. **Testing is straightforward.** Mock activities, skip time, assert behavior. The test framework handles the hard parts.

When asked "How would you handle X in billing?", the answer should demonstrate fluency with these patterns -- not just what Temporal provides, but how to compose its primitives for the specific problem.
