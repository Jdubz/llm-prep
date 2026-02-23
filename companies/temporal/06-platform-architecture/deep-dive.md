# Module 06 Deep Dive: Advanced Platform Patterns

This deep dive covers the architectural patterns that separate a production multi-tenant
platform from a prototype -- multi-region operations, cell-based scaling, platform
observability, customer lifecycle management, and API design for platform services.

---

## 1. Multi-Region Architecture

### Why Multi-Region Matters for Cloud Nexus

Temporal Cloud customers are global enterprises. They need:

- **Low-latency access** from their applications to the nearest Temporal endpoint
- **Data residency** to comply with GDPR, data sovereignty laws, industry regulations
- **High availability** that survives a full region outage
- **Disaster recovery** with defined RPO (Recovery Point Objective) and RTO (Recovery Time Objective)

Cloud Nexus must manage resources across all these regions through a unified control plane.

### Active-Active vs Active-Passive

**Active-active**: Multiple regions serve traffic simultaneously. Each region handles its
own subset of namespaces. Cross-region replication keeps shared state (account info, billing)
consistent.

```
Region A (us-east-1)          Region B (eu-west-1)
+-------------------+         +-------------------+
| Control Plane     |  <--->  | Control Plane     |
| - Accounts (R/W)  |  sync   | - Accounts (R/W)  |
| - Namespaces (R/W)|         | - Namespaces (R/W)|
+-------------------+         +-------------------+
        |                              |
        v                              v
+-------------------+         +-------------------+
| Data Plane        |         | Data Plane        |
| - NS: acme-prod   |         | - NS: acme-eu     |
| - NS: beta-test   |         | - NS: gamma-prod  |
+-------------------+         +-------------------+
```

**Active-passive**: One region is primary, the other is a hot standby. Simpler to operate
but wastes capacity and adds failover latency.

| Aspect | Active-Active | Active-Passive |
|--------|--------------|----------------|
| **Utilization** | Both regions serve traffic | Standby region is idle |
| **Failover time** | Near-zero (traffic already there) | Minutes (DNS propagation, warmup) |
| **Complexity** | High (conflict resolution, split-brain) | Moderate (replication lag) |
| **Cost** | Both regions fully provisioned | Standby can be smaller |
| **Data consistency** | Eventual (conflict resolution needed) | Strong (single writer) |

For Cloud Nexus, a **hybrid approach** makes sense: the control plane is active-active for
reads (any region can serve account info) but uses a single leader for writes (one region
owns the source of truth for each account). This avoids conflict resolution complexity
while still providing low-latency reads globally.

### Cross-Region Replication Patterns

**Event-driven replication**: Changes in one region publish events that other regions
consume. This is eventually consistent but decoupled.

```go
// When a namespace config changes in the primary region
func (s *NamespaceService) UpdateNamespace(ctx context.Context, req *UpdateRequest) error {
    // Write to local database
    if err := s.db.UpdateNamespace(ctx, req); err != nil {
        return err
    }

    // Publish change event for other regions to consume
    event := &NamespaceChangedEvent{
        NamespaceID: req.NamespaceID,
        ChangeType:  "config_update",
        Payload:     req,
        Timestamp:   time.Now(),
        SourceRegion: s.region,
    }
    return s.eventBus.Publish(ctx, "namespace.changed", event)
}

// In each consuming region
func (c *ReplicationConsumer) HandleNamespaceChanged(ctx context.Context, event *NamespaceChangedEvent) error {
    if event.SourceRegion == c.localRegion {
        return nil // Skip events from our own region
    }
    return c.db.ApplyNamespaceChange(ctx, event)
}
```

**Database-level replication**: Use a globally distributed database (CockroachDB, Spanner,
Aurora Global Database) that handles replication at the storage layer. Simpler application
code but more expensive and introduces storage-layer latency.

**Hybrid**: Use database replication for critical shared state (account info, billing) and
event-driven replication for less critical data (audit logs, usage metrics).

### Failover Strategies

**DNS-based failover**: Route53 health checks detect a region failure and update DNS to
point to the healthy region. Simple but slow -- DNS TTLs mean some clients keep hitting
the failed region for minutes.

**Load balancer-based failover**: A global load balancer (CloudFront, Cloud Load Balancing)
routes traffic. Detects unhealthy backends within seconds and reroutes. Faster than DNS
but adds a dependency on the load balancer itself.

**Client-side failover**: The SDK knows about multiple endpoints and fails over automatically.
Temporal's SDK already supports this pattern. Fastest failover but requires client cooperation.

**In practice, layer all three**: Global load balancer for automatic routing, DNS failover
as a backup, and client-side failover for the fastest recovery.

### Data Consistency Across Regions

The fundamental tension: you can't have low latency, high availability, AND strong
consistency across regions (CAP theorem in practice).

For Cloud Nexus:

- **Account metadata**: Eventual consistency is fine. If a user changes their display name,
  it's okay if it takes a few seconds to propagate everywhere.
- **Namespace configuration**: Eventual consistency with bounded staleness. A config change
  should propagate within 30 seconds. Cache with TTL at the data plane.
- **Billing state**: Must converge to consistency but doesn't need real-time accuracy.
  Usage events are aggregated over time windows.
- **Access control changes**: Tighter consistency needed. When a user revokes an API key,
  it should take effect quickly everywhere. Use shorter cache TTLs or push-based
  invalidation.

### Conflict Resolution

In an active-active setup, two regions might try to update the same resource concurrently.

**Last-writer-wins (LWW)**: Each update carries a timestamp. The latest timestamp wins.
Simple but can lose updates silently. Acceptable for simple fields like display names.

**Version vectors**: Each region maintains a version counter. Conflicts are detected and
resolved explicitly. More complex but safer.

**Operational transforms / CRDTs**: For data that can be merged automatically (counters,
sets). Overkill for most control plane data.

For Cloud Nexus, the simplest approach: **single leader per resource**. Each namespace is
owned by a single region. Writes go to the owner region, reads can come from any region.
Ownership can transfer during failover.

---

## 2. Platform Observability

### The Two-Layer Problem

Platform observability is harder than application observability because you have two layers
to monitor:

1. **Platform health**: Are the Cloud Nexus services themselves healthy?
2. **Tenant health**: Is each customer's experience healthy?

A platform can be healthy overall while a single tenant suffers. A platform can show errors
while all tenants are actually fine (internal retries succeeded).

### Multi-Tenant Metrics

**Cardinality management** is the top challenge. If you add a `tenant_id` label to every
metric, and you have 10,000 tenants with 100 metric types, that's 1 million time series.
Prometheus will struggle. Your monitoring bill will explode.

Strategies:

- **Aggregate by default, break down on demand**: Emit platform-level metrics (total
  requests, error rate). When investigating a specific tenant, query their subset from
  logs or a high-cardinality store (like ClickHouse or Honeycomb).

- **Tiered cardinality**: Top-100 tenants by volume get dedicated metric series. Smaller
  tenants are bucketed into "other."

- **Pre-aggregated per-tenant dashboards**: Store per-tenant rollups in a separate time
  series or table, aggregated every minute. This limits cardinality to
  `num_tenants * num_rollup_metrics`.

```go
// Platform-level metric (low cardinality, always emitted)
requestDuration := prometheus.NewHistogramVec(prometheus.HistogramOpts{
    Name:    "nexus_request_duration_seconds",
    Help:    "Request duration in seconds",
    Buckets: prometheus.DefBuckets,
}, []string{"method", "status"})

// Per-tenant usage tracking (stored separately, not in Prometheus)
type TenantUsageRecord struct {
    TenantID    string
    Timestamp   time.Time
    ActionCount int64
    APICallCount int64
    StorageBytes int64
}

func RecordTenantUsage(ctx context.Context, tenantID string, usage TenantUsageRecord) error {
    // Write to ClickHouse or a dedicated usage database
    return usageStore.Insert(ctx, usage)
}
```

### Alerting Patterns

**Platform-level alerts**: Error rate > 1%, p99 latency > 5s, provisioning failure rate
elevated, database replication lag > 30s. These fire to the Cloud Nexus on-call team.

**Tenant-level alerts**: A specific customer's error rate spikes, a namespace hits its
rate limit, a provisioning workflow has been stuck for 10+ minutes. These may fire to the
customer success team or directly to the customer.

**Alert fatigue prevention**:
- Group related alerts (don't fire 100 alerts if 100 tenants are affected by the same issue)
- Deduplicate: if the platform is down, suppress individual tenant alerts
- Route differently: platform alerts go to engineering, tenant alerts go to support

### Billing Observability

Usage tracking is a special observability concern because it directly affects revenue:

- **Track every billable action**: Workflow starts, activity executions, signal sends. These
  events flow through a pipeline to the billing system.
- **Reconciliation**: Periodically compare what the data plane reports vs what the billing
  system charged. Discrepancies trigger alerts.
- **Anomaly detection**: Sudden spikes in usage could be a bug, an attack, or legitimate
  growth. Alert on outliers so the team can investigate before the customer gets a surprising
  bill.

```go
// Usage event pipeline
type UsageEvent struct {
    NamespaceID string
    EventType   string    // "workflow_start", "activity_execution", "signal_send"
    Timestamp   time.Time
    Metadata    map[string]string
}

// Reconciliation query: compare usage events vs billing records
// SELECT namespace_id, event_type, COUNT(*) as event_count
// FROM usage_events
// WHERE timestamp BETWEEN ? AND ?
// GROUP BY namespace_id, event_type
//
// Compare against:
// SELECT namespace_id, metric_type, billed_count
// FROM billing_records
// WHERE billing_period = ?
```

---

## 3. Scalability Patterns

### Cell-Based Architecture

Cell-based architecture is the dominant pattern for scaling multi-tenant platforms. AWS,
Azure, and Slack all use variations of it. The idea: instead of scaling one monolithic
deployment, run many independent **cells**, each serving a subset of tenants.

```
                    +-------------------+
                    |   Cell Router     |
                    | (tenant -> cell)  |
                    +-------------------+
                     /       |        \
                    /        |         \
            +------+    +------+    +------+
            |Cell 1|    |Cell 2|    |Cell 3|
            |------+    |------+    |------+
            |DB    |    |DB    |    |DB    |
            |Cache |    |Cache |    |Cache |
            |Queue |    |Queue |    |Queue |
            |App   |    |App   |    |App   |
            +------+    +------+    +------+
            Tenants:    Tenants:    Tenants:
            A, B, C     D, E, F     G, H, I
```

**Why cells work:**

- **Blast radius containment**: A bug or overload in Cell 1 only affects tenants A, B, C.
  Tenants in other cells are unaffected.
- **Independent scaling**: Cell 2 can scale its database independently if tenant E grows.
- **Simplified operations**: Each cell is a complete, self-contained stack. Deploy to one
  cell, verify, then roll out to others (canary by cell).
- **Linear scaling**: Need more capacity? Add another cell. No need to vertically scale
  a single database or service.

**Cell routing**: A routing layer maps each tenant to a cell. This mapping lives in a small,
highly available database (or even a static config for simple cases). The router itself is
stateless and horizontally scalable.

```go
type CellRouter struct {
    assignments map[string]string // tenantID -> cellID
    mu          sync.RWMutex
}

func (r *CellRouter) GetCell(tenantID string) (string, error) {
    r.mu.RLock()
    defer r.mu.RUnlock()
    cellID, ok := r.assignments[tenantID]
    if !ok {
        return "", fmt.Errorf("tenant %s not assigned to any cell", tenantID)
    }
    return cellID, nil
}

func (r *CellRouter) AssignTenant(tenantID, cellID string) {
    r.mu.Lock()
    defer r.mu.Unlock()
    r.assignments[tenantID] = cellID
}
```

### Shard Management

Within cells (or as an alternative to cells), sharding distributes data and load:

**Tenant migration between cells/shards**: When a cell gets hot, you need to move tenants.
This is a multi-step process:

1. Mark the tenant as "migrating" (new writes are double-written)
2. Copy existing data to the destination cell
3. Verify data consistency
4. Switch the routing table to point to the new cell
5. Drain remaining traffic from the old cell
6. Clean up the old cell's data

This is another perfect use case for a Temporal workflow -- it's a long-running, multi-step
process with compensating actions if something goes wrong.

**Rebalancing**: Periodically analyze load distribution across cells. If one cell is
significantly hotter than others, trigger migrations. Use a scoring algorithm that
considers compute, storage, and network usage.

### Queue-Based Processing

Control plane operations should be decoupled through queues:

```
API Server                    Worker Pool
  |                              |
  |-- Enqueue(CreateNS) ------->|
  |                              |-- Process CreateNS
  |<-- Return OperationID       |     |-- Allocate resources
  |                              |     |-- Configure networking
  |                              |     |-- Update records
  |-- Poll(OperationID) ------->|
  |<-- Status: completed        |
```

**Why queues for platform operations:**

- **Backpressure**: If the system is overwhelmed with provisioning requests, they queue up
  instead of causing cascading failures.
- **Priority**: Critical operations (fixing a broken namespace) can jump the queue ahead
  of bulk provisioning.
- **Rate smoothing**: Bursts of API calls become a steady stream of work.
- **Retry semantics**: Failed operations are automatically retried from the queue.

With Temporal, you get all of these for free. The task queue is the queue. The workflow
is the worker. Retries, priorities, and backpressure are built in.

### Eventual Consistency in Platform Operations

Not every operation completes instantly, and the platform must communicate this clearly:

**Operation resources** represent long-running operations:

```protobuf
message Operation {
  string id = 1;
  string type = 2;           // "create_namespace", "setup_connectivity"
  OperationState state = 3;  // PENDING, RUNNING, SUCCEEDED, FAILED
  google.protobuf.Timestamp created_at = 4;
  google.protobuf.Timestamp updated_at = 5;
  google.protobuf.Any result = 6;   // Present when SUCCEEDED
  Status error = 7;                  // Present when FAILED
}

enum OperationState {
  OPERATION_STATE_UNSPECIFIED = 0;
  PENDING = 1;
  RUNNING = 2;
  SUCCEEDED = 3;
  FAILED = 4;
}

service OperationService {
  rpc GetOperation(GetOperationRequest) returns (Operation);
  rpc ListOperations(ListOperationsRequest) returns (ListOperationsResponse);
  rpc CancelOperation(CancelOperationRequest) returns (Operation);
}
```

Clients start an operation, receive an operation ID, and poll for completion. The Temporal
workflow ID can serve as the operation ID, providing direct visibility into the operation's
progress.

---

## 4. Customer Lifecycle Management

### Onboarding Workflow

Customer onboarding is a multi-step process with dependencies and potential failures. Here's
the full flow as a Temporal workflow with proper Saga compensation:

```go
func CustomerOnboardingWorkflow(ctx workflow.Context, req OnboardingRequest) error {
    // Track completed steps for compensation
    var completedSteps []string

    // Defer compensation in case of failure
    defer func() {
        if ctx.Err() != nil || workflow.GetInfo(ctx).GetCurrentHistoryLength() > 0 {
            // Only compensate if we actually failed
        }
    }()

    // Step 1: Create identity (auth0/custom identity provider)
    var identityID string
    err := workflow.ExecuteActivity(ctx, CreateIdentity, req).Get(ctx, &identityID)
    if err != nil {
        return fmt.Errorf("create identity failed: %w", err)
    }
    completedSteps = append(completedSteps, "identity")

    // Step 2: Create account record
    var accountID string
    err = workflow.ExecuteActivity(ctx, CreateAccount, CreateAccountInput{
        IdentityID: identityID,
        OrgName:    req.Organization,
        Plan:       req.Plan,
    }).Get(ctx, &accountID)
    if err != nil {
        compensate(ctx, completedSteps, identityID, "", "")
        return fmt.Errorf("create account failed: %w", err)
    }
    completedSteps = append(completedSteps, "account")

    // Step 3: Set up billing subscription
    var subscriptionID string
    err = workflow.ExecuteActivity(ctx, CreateBillingSubscription, BillingInput{
        AccountID:     accountID,
        Plan:          req.Plan,
        PaymentMethod: req.PaymentMethod,
    }).Get(ctx, &subscriptionID)
    if err != nil {
        compensate(ctx, completedSteps, identityID, accountID, "")
        return fmt.Errorf("billing setup failed: %w", err)
    }
    completedSteps = append(completedSteps, "billing")

    // Step 4: Provision initial namespace
    var namespaceID string
    err = workflow.ExecuteActivity(ctx, ProvisionNamespace, NamespaceInput{
        AccountID: accountID,
        Name:      req.Organization + "-default",
        Region:    req.PreferredRegion,
    }).Get(ctx, &namespaceID)
    if err != nil {
        compensate(ctx, completedSteps, identityID, accountID, subscriptionID)
        return fmt.Errorf("namespace provisioning failed: %w", err)
    }

    // Step 5: Send welcome email (best effort, don't fail onboarding)
    _ = workflow.ExecuteActivity(ctx, SendWelcomeEmail, WelcomeEmailInput{
        Email:       req.Email,
        AccountID:   accountID,
        NamespaceID: namespaceID,
    }).Get(ctx, nil)

    return nil
}

func compensate(ctx workflow.Context, steps []string, identityID, accountID, subscriptionID string) {
    // Compensation runs in reverse order
    compCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: time.Minute,
        RetryPolicy: &temporal.RetryPolicy{MaximumAttempts: 5},
    })

    for i := len(steps) - 1; i >= 0; i-- {
        switch steps[i] {
        case "billing":
            _ = workflow.ExecuteActivity(compCtx, CancelSubscription, subscriptionID).Get(ctx, nil)
        case "account":
            _ = workflow.ExecuteActivity(compCtx, DeactivateAccount, accountID).Get(ctx, nil)
        case "identity":
            _ = workflow.ExecuteActivity(compCtx, DeleteIdentity, identityID).Get(ctx, nil)
        }
    }
}
```

### Trial Management

Trials are time-limited access that requires automatic enforcement:

```go
func TrialManagementWorkflow(ctx workflow.Context, accountID string, trialDuration time.Duration) error {
    // Set the account to trial status
    err := workflow.ExecuteActivity(ctx, SetAccountStatus, accountID, "trial").Get(ctx, nil)
    if err != nil {
        return err
    }

    // Wait for trial to expire OR for the customer to upgrade
    timerCtx, cancelTimer := workflow.WithCancel(ctx)
    upgradeCh := workflow.GetSignalChannel(ctx, "account_upgraded")

    // Start the trial timer
    timerFuture := workflow.NewTimer(timerCtx, trialDuration)

    selector := workflow.NewSelector(ctx)

    var upgraded bool

    selector.AddFuture(timerFuture, func(f workflow.Future) {
        // Trial expired without upgrade
        upgraded = false
    })

    selector.AddReceive(upgradeCh, func(ch workflow.ReceiveChannel, more bool) {
        // Customer upgraded -- cancel the timer
        cancelTimer()
        upgraded = true
    })

    selector.Select(ctx)

    if upgraded {
        return workflow.ExecuteActivity(ctx, SetAccountStatus, accountID, "active").Get(ctx, nil)
    }

    // Trial expired: send warning, wait 7 days, then suspend
    _ = workflow.ExecuteActivity(ctx, SendTrialExpirationEmail, accountID).Get(ctx, nil)

    // Grace period
    gracePeriod := 7 * 24 * time.Hour
    graceCtx, cancelGrace := workflow.WithCancel(ctx)
    graceFuture := workflow.NewTimer(graceCtx, gracePeriod)

    graceSelector := workflow.NewSelector(ctx)
    graceSelector.AddFuture(graceFuture, func(f workflow.Future) {
        upgraded = false
    })
    graceSelector.AddReceive(upgradeCh, func(ch workflow.ReceiveChannel, more bool) {
        cancelGrace()
        upgraded = true
    })
    graceSelector.Select(ctx)

    if upgraded {
        return workflow.ExecuteActivity(ctx, SetAccountStatus, accountID, "active").Get(ctx, nil)
    }

    // Suspend the account -- namespaces stop accepting new workflows
    return workflow.ExecuteActivity(ctx, SuspendAccount, accountID).Get(ctx, nil)
}
```

### Upgrade and Downgrade Flows

Plan changes involve resource adjustments:

- **Upgrade**: Increase rate limits, unlock features, provision additional capacity. Usually
  safe to apply immediately.
- **Downgrade**: Decrease rate limits, reduce storage quotas. Must check if current usage
  exceeds the new plan's limits. If yes, notify the customer and block the downgrade until
  they reduce usage.

```go
func PlanChangeWorkflow(ctx workflow.Context, req PlanChangeRequest) error {
    // Validate the change
    var validation PlanChangeValidation
    err := workflow.ExecuteActivity(ctx, ValidatePlanChange, req).Get(ctx, &validation)
    if err != nil {
        return err
    }

    if !validation.Allowed {
        return temporal.NewApplicationError(
            fmt.Sprintf("plan change blocked: %s", validation.Reason),
            "PLAN_CHANGE_BLOCKED",
        )
    }

    // Apply the change
    err = workflow.ExecuteActivity(ctx, ApplyPlanChange, req).Get(ctx, nil)
    if err != nil {
        return err
    }

    // Update billing
    err = workflow.ExecuteActivity(ctx, UpdateBillingPlan, UpdateBillingInput{
        AccountID: req.AccountID,
        NewPlan:   req.NewPlan,
        EffectiveDate: req.EffectiveDate,
    }).Get(ctx, nil)
    if err != nil {
        // Compensate: revert the plan change
        _ = workflow.ExecuteActivity(ctx, RevertPlanChange, req).Get(ctx, nil)
        return err
    }

    // Notify the customer
    _ = workflow.ExecuteActivity(ctx, SendPlanChangeConfirmation, req).Get(ctx, nil)

    return nil
}
```

### Offboarding

Offboarding must be careful about data retention and graceful shutdown:

1. **Suspension**: Stop accepting new workflows, let running workflows complete (with a deadline)
2. **Data export**: Give the customer time and tools to export their data
3. **Retention period**: Hold data for a configurable period (30-90 days) in case they reactivate
4. **Hard delete**: After the retention period, permanently delete all customer data
5. **Billing finalization**: Generate the final invoice, close the subscription

This is a workflow that spans days or weeks, using Temporal timers to manage the waiting
periods. The workflow state records exactly where in the offboarding process each customer
is, making it auditable and resumable if the system restarts.

---

## 5. API Design for Platform Services

### Resource-Oriented Design

Platform APIs should model resources, not actions. Every entity is a resource with a
standard set of operations:

```protobuf
// Standard CRUD pattern for a platform resource
service NamespaceService {
  rpc CreateNamespace(CreateNamespaceRequest) returns (CreateNamespaceResponse);
  rpc GetNamespace(GetNamespaceRequest) returns (GetNamespaceResponse);
  rpc ListNamespaces(ListNamespacesRequest) returns (ListNamespacesResponse);
  rpc UpdateNamespace(UpdateNamespaceRequest) returns (UpdateNamespaceResponse);
  rpc DeleteNamespace(DeleteNamespaceRequest) returns (DeleteNamespaceResponse);
}
```

Resource names follow a hierarchy: `accounts/{account_id}/namespaces/{namespace_id}`.
This makes authorization natural -- to access a namespace, you must have access to its
parent account.

### Pagination, Filtering, and Sorting

Every list operation needs pagination. For gRPC APIs, use page tokens (opaque cursors):

```protobuf
message ListNamespacesRequest {
  string account_id = 1;
  int32 page_size = 2;          // Max items to return (default 20, max 100)
  string page_token = 3;        // Opaque token from previous response
  string filter = 4;            // e.g., "region = 'us-east-1' AND status = 'active'"
  string order_by = 5;          // e.g., "created_at desc"
}

message ListNamespacesResponse {
  repeated Namespace namespaces = 1;
  string next_page_token = 2;   // Empty when no more pages
  int32 total_size = 3;         // Total matching count (optional, expensive)
}
```

**Page token implementation**: Encode the cursor position (last seen ID, last seen sort key)
into an opaque base64 string. The server decodes it to construct the query. Never expose
database internals in the token.

```go
type PageCursor struct {
    LastID        string    `json:"last_id"`
    LastSortValue string    `json:"last_sort_value"`
    SortField     string    `json:"sort_field"`
    SortOrder     string    `json:"sort_order"`
}

func EncodePageToken(cursor PageCursor) string {
    data, _ := json.Marshal(cursor)
    return base64.StdEncoding.EncodeToString(data)
}

func DecodePageToken(token string) (*PageCursor, error) {
    data, err := base64.StdEncoding.DecodeString(token)
    if err != nil {
        return nil, fmt.Errorf("invalid page token: %w", err)
    }
    var cursor PageCursor
    if err := json.Unmarshal(data, &cursor); err != nil {
        return nil, fmt.Errorf("invalid page token payload: %w", err)
    }
    return &cursor, nil
}
```

### Long-Running Operations

Many platform operations take seconds or minutes (namespace provisioning, connectivity
setup). The pattern is:

1. Client calls `CreateNamespace` -- returns immediately with an operation ID
2. Client polls `GetOperation(operation_id)` until state is `SUCCEEDED` or `FAILED`
3. On success, the operation result contains the created resource

```go
func (s *NamespaceService) CreateNamespace(ctx context.Context, req *CreateNamespaceRequest) (*CreateNamespaceResponse, error) {
    // Validate request
    if err := validateCreateNamespaceRequest(req); err != nil {
        return nil, status.Errorf(codes.InvalidArgument, "invalid request: %v", err)
    }

    // Check idempotency key
    if req.RequestId != "" {
        existing, err := s.operationStore.GetByRequestID(ctx, req.RequestId)
        if err == nil {
            return &CreateNamespaceResponse{OperationId: existing.ID}, nil
        }
    }

    // Start the provisioning workflow (workflow ID = operation ID)
    operationID := uuid.New().String()
    _, err := s.temporalClient.ExecuteWorkflow(ctx, client.StartWorkflowOptions{
        ID:        operationID,
        TaskQueue: "namespace-provisioning",
    }, ProvisionNamespaceWorkflow, req)
    if err != nil {
        return nil, status.Errorf(codes.Internal, "failed to start provisioning: %v", err)
    }

    // Record the operation
    s.operationStore.Create(ctx, &Operation{
        ID:        operationID,
        RequestID: req.RequestId,
        Type:      "create_namespace",
        State:     OperationStatePending,
    })

    return &CreateNamespaceResponse{OperationId: operationID}, nil
}
```

### Idempotency in Platform APIs

Platform APIs must be idempotent. Network failures, client retries, and load balancer
retries all mean the same request might arrive multiple times.

**Request ID / idempotency key**: The client includes a unique ID with every mutating
request. The server stores a mapping from request ID to response. If the same request ID
arrives again, return the stored response instead of executing again.

```go
func (s *Service) handleWithIdempotency(ctx context.Context, requestID string, handler func() (*Response, error)) (*Response, error) {
    if requestID == "" {
        // No idempotency key -- execute normally
        return handler()
    }

    // Check if we've already processed this request
    cached, err := s.idempotencyStore.Get(ctx, requestID)
    if err == nil {
        return cached, nil
    }

    // Execute the request
    resp, err := handler()
    if err != nil {
        return nil, err
    }

    // Cache the response (with TTL -- idempotency keys don't need to live forever)
    s.idempotencyStore.Set(ctx, requestID, resp, 24*time.Hour)

    return resp, nil
}
```

### Error Handling: Structured Errors

Platform APIs should return rich, structured errors that help the client understand what
went wrong and what to do about it:

```protobuf
message ErrorDetail {
  string code = 1;           // Machine-readable: "NAMESPACE_ALREADY_EXISTS"
  string message = 2;        // Human-readable: "A namespace with name 'prod' already exists"
  bool retryable = 3;        // Can the client retry this request?
  string field = 4;          // Which request field caused the error (for validation errors)
  map<string, string> metadata = 5;  // Additional context
}
```

Map these to gRPC status codes consistently:

| Error Type | gRPC Code | Retryable | Example |
|-----------|-----------|-----------|---------|
| Validation failure | `INVALID_ARGUMENT` | No | "namespace name must be lowercase" |
| Resource not found | `NOT_FOUND` | No | "namespace xyz not found" |
| Already exists | `ALREADY_EXISTS` | No (idempotent) | "namespace with this name exists" |
| Permission denied | `PERMISSION_DENIED` | No | "no access to this account" |
| Rate limited | `RESOURCE_EXHAUSTED` | Yes (with backoff) | "rate limit exceeded" |
| Internal error | `INTERNAL` | Yes | "database temporarily unavailable" |
| Not implemented | `UNIMPLEMENTED` | No | "CMEK not available in this region" |
| Quota exceeded | `RESOURCE_EXHAUSTED` | No (until quota increased) | "maximum namespaces reached" |

---

## 6. Interview Deep Dive Questions

### Architecture Questions

1. **Design the cell routing layer for Cloud Nexus. How do you decide which cell a new tenant goes to? How do you handle cell failures?**

   Cell selection for new tenants considers: current cell utilization (CPU, memory, storage),
   geographic proximity to the tenant's preferred region, compliance requirements (some
   tenants may need dedicated cells), and balancing to avoid hot cells. A weighted scoring
   algorithm ranks available cells. Cell routing state is cached at the gateway with short
   TTL and backed by a highly available database. Cell failures trigger the cell router to
   redirect new requests to other cells. Existing tenants on a failed cell experience
   degradation until the cell recovers or they're migrated.

2. **How would you design tenant migration between cells without downtime?**

   Double-write period: new writes go to both source and destination cells. Background job
   copies historical data. Once the destination is caught up, atomically update the routing
   table. Drain remaining in-flight requests from the source. Verify data consistency with
   checksums. The whole process is orchestrated by a Temporal workflow with compensating
   actions if any step fails. The tenant experiences no downtime because reads are served
   from whichever cell the router points to, and the switchover is atomic at the routing layer.

3. **Walk through what happens when a customer creates a namespace, from API call to a working namespace they can connect to.**

   API gateway authenticates the request, validates the API key. The namespace service checks
   the customer's plan (do they have capacity for another namespace?), validates the region
   is available, and starts a provisioning workflow. The workflow allocates data plane
   resources (history shards, matching partitions), configures the namespace in the data
   plane's configuration store, sets up any requested encryption keys, configures search
   attributes, and updates the control plane database with the namespace status. The workflow
   ID serves as the operation ID. The customer polls the operation until it completes
   (typically 30-120 seconds). Once complete, the namespace endpoint is available for SDK
   connections.

### Scaling Questions

4. **Your platform is processing 1000 namespace creation requests per hour during a peak event. The cloud provider starts returning rate limit errors. How do you handle this?**

   The activities calling cloud provider APIs should have retry policies with exponential
   backoff and jitter. The Temporal workflow handles retries automatically. If the rate
   limiting is persistent, implement a global rate limiter for cloud provider API calls
   (shared across all provisioning workflows) to smooth out bursts. Queue provisioning
   requests and process them at a sustainable rate. Communicate delays to customers through
   the operation status API. Consider pre-provisioning a pool of resources during off-peak
   hours so peak-time requests can draw from the pool instead of hitting the cloud provider.

5. **How do you handle configuration propagation from the control plane to the data plane across all regions with minimal latency?**

   Push-based propagation for urgent changes (API key revocations, rate limit changes):
   use a message bus (Kafka, SNS) to broadcast changes. Pull-based propagation with caching
   for routine changes (namespace config): the data plane periodically polls the control
   plane and caches results with a TTL. Hybrid: push a notification that something changed,
   let the data plane pull the details. This avoids sending large payloads over the message
   bus while still achieving low latency. Target: routine changes propagate within 30
   seconds, security-critical changes propagate within 5 seconds.
