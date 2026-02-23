# Module 06: Platform Architecture for Cloud Nexus

## Context: What You Are Interviewing For

You are interviewing for a Senior Software Engineer on the team that owns **Cloud Nexus** --
Temporal's foundational platform connecting Temporal Applications through a scalable, self-service
ecosystem with a unified API abstraction layer. This module covers the platform architecture
concepts that will come up in your interviews.

---

## 1. What Cloud Nexus Likely Is

Cloud Nexus is the connective tissue of Temporal Cloud. Think of it as the platform layer
that sits between customers and the raw Temporal execution infrastructure, providing:

- **Unified API abstraction** over heterogeneous backends (multi-cloud, multi-region)
- **Self-service provisioning** so teams can connect and manage their Temporal applications
  without filing support tickets
- **Cross-cloud connectivity** linking namespaces and applications across AWS, GCP, Azure
- **Tenant lifecycle management** from onboarding through billing through offboarding

### Why It Matters

Temporal Cloud customers are enterprises. They run workloads across multiple cloud providers.
They have compliance requirements dictating where data can live. They need private connectivity
so workflow traffic never hits the public internet. And they want all of this without calling
Temporal support for every configuration change.

Cloud Nexus solves this by providing a single API surface that abstracts away the underlying
cloud provider complexity. A customer says "I need a namespace in eu-west-1 with private
connectivity to my AWS VPC" and Cloud Nexus handles the provisioning, networking, isolation,
and billing -- reliably, using Temporal workflows under the hood.

### The Self-Service Model

The shift from "file a ticket, wait for an engineer" to "call an API, get a resource" is
the core value proposition. Self-service means:

- Programmatic namespace creation and configuration
- API-driven connectivity setup (PrivateLink, VPC peering)
- Customer-managed encryption keys
- Usage dashboards and billing visibility
- Team and role management

This is a control plane product. You are building the management layer, not the workflow
execution engine itself.

---

## 2. Multi-Cloud Platform Design

### The Abstraction Problem

Temporal Cloud runs on multiple cloud providers. Each provider has fundamentally different:

- **APIs**: AWS SDK vs Google Cloud client libraries vs Azure SDK
- **Networking**: VPCs, subnets, security groups all work differently
- **Identity**: IAM roles (AWS), service accounts (GCP), managed identities (Azure)
- **Storage**: S3 vs GCS vs Azure Blob -- similar concepts, different semantics
- **Consistency models**: eventual consistency timelines vary across providers

The goal is a unified API that lets customers interact with Temporal Cloud without caring
which provider is underneath.

### Provider Abstraction Patterns

**The Adapter Pattern** is the backbone. Define an interface for each cloud capability,
implement it per provider.

```go
// CloudProvider defines the interface every provider must implement.
type CloudProvider interface {
    CreateNamespace(ctx context.Context, req *CreateNamespaceRequest) (*Namespace, error)
    DeleteNamespace(ctx context.Context, namespaceID string) error
    SetupPrivateConnectivity(ctx context.Context, req *ConnectivityRequest) (*Connection, error)
    GetConnectionStatus(ctx context.Context, connectionID string) (*ConnectionStatus, error)
}

// AWSProvider implements CloudProvider for AWS.
type AWSProvider struct {
    ec2Client    *ec2.Client
    stsClient    *sts.Client
    region       string
}

func (p *AWSProvider) SetupPrivateConnectivity(ctx context.Context, req *ConnectivityRequest) (*Connection, error) {
    // Create VPC endpoint service, accept connection, configure DNS
    // AWS-specific: PrivateLink via VPC endpoint services
    // ...
}

// GCPProvider implements CloudProvider for GCP.
type GCPProvider struct {
    computeService *compute.Service
    project        string
}

func (p *GCPProvider) SetupPrivateConnectivity(ctx context.Context, req *ConnectivityRequest) (*Connection, error) {
    // Create Private Service Connect endpoint
    // GCP-specific: PSC forwarding rules
    // ...
}
```

**Configuration-driven backend selection** lets the platform route requests to the right provider
without hardcoding decisions in application logic:

```go
type RegionConfig struct {
    RegionID    string        `yaml:"region_id"`    // e.g., "aws-us-east-1"
    Provider    ProviderType  `yaml:"provider"`     // aws, gcp, azure
    Endpoint    string        `yaml:"endpoint"`
    Capabilities []string    `yaml:"capabilities"` // e.g., ["privatelink", "cmek"]
}

func NewProviderFromConfig(cfg RegionConfig) (CloudProvider, error) {
    switch cfg.Provider {
    case ProviderAWS:
        return NewAWSProvider(cfg)
    case ProviderGCP:
        return NewGCPProvider(cfg)
    case ProviderAzure:
        return NewAzureProvider(cfg)
    default:
        return nil, fmt.Errorf("unsupported provider: %s", cfg.Provider)
    }
}
```

### Cross-Cloud Networking

Private connectivity is one of the hardest problems. Each provider has its own mechanism:

| Provider | Mechanism | How It Works |
|----------|-----------|--------------|
| **AWS** | PrivateLink | VPC endpoint service on Temporal side, VPC endpoint on customer side |
| **GCP** | Private Service Connect | Service attachment on Temporal side, forwarding rule on customer side |
| **Azure** | Private Link | Private link service on Temporal side, private endpoint on customer side |

The unified API hides this:

```protobuf
service ConnectivityService {
  rpc CreatePrivateConnection(CreatePrivateConnectionRequest) returns (Operation);
  rpc GetPrivateConnection(GetPrivateConnectionRequest) returns (PrivateConnection);
  rpc DeletePrivateConnection(DeletePrivateConnectionRequest) returns (Operation);
}

message CreatePrivateConnectionRequest {
  string namespace_id = 1;
  string customer_cloud_provider = 2;   // "aws", "gcp", "azure"
  string customer_account_id = 3;       // AWS account ID, GCP project, Azure subscription
  string customer_vpc_id = 4;           // Provider-specific VPC/VNet identifier
  string customer_region = 5;
}
```

The customer doesn't need to know which cloud Temporal's data plane runs on. They provide
their side's details, and the platform handles the cross-provider plumbing.

### Challenge: Different Failure Modes

Each cloud fails differently, and your abstraction must handle this:

- **AWS** API throttling uses exponential backoff with jitter
- **GCP** returns `RESOURCE_EXHAUSTED` with a suggested retry delay
- **Azure** uses `Retry-After` headers on 429 responses

Your provider implementations must normalize these into a consistent error model that the
platform layer can reason about. Map provider-specific errors to your own error taxonomy:
retryable vs non-retryable, transient vs permanent, rate-limited vs capacity-exceeded.

---

## 3. API Abstraction Layers

### Designing a Unified API Over Heterogeneous Backends

The Cloud Nexus API is the single surface customers interact with. Temporal uses gRPC
throughout, so expect gRPC API design to be front and center.

**Key design principles:**

1. **Resource-oriented**: APIs model resources (namespaces, connections, users), not actions
2. **Provider-agnostic**: no AWS/GCP/Azure concepts leak through the API
3. **Eventually consistent where necessary**: creation requests return operations, not
   fully-provisioned resources
4. **Idempotent by default**: repeat a create call, get the same result

### gRPC API Design (Temporal's Stack)

Temporal is a gRPC shop. The Temporal server itself exposes gRPC APIs, and Cloud Nexus
follows the same pattern.

```protobuf
syntax = "proto3";
package temporal.api.cloud.nexus.v1;

import "google/protobuf/timestamp.proto";

service NamespaceService {
  // Creates a new namespace. Returns a long-running operation.
  rpc CreateNamespace(CreateNamespaceRequest) returns (CreateNamespaceResponse);

  // Gets a namespace by ID.
  rpc GetNamespace(GetNamespaceRequest) returns (GetNamespaceResponse);

  // Lists namespaces with pagination.
  rpc ListNamespaces(ListNamespacesRequest) returns (ListNamespacesResponse);

  // Updates namespace configuration.
  rpc UpdateNamespace(UpdateNamespaceRequest) returns (UpdateNamespaceResponse);

  // Deletes a namespace. Returns a long-running operation.
  rpc DeleteNamespace(DeleteNamespaceRequest) returns (DeleteNamespaceResponse);
}

message CreateNamespaceRequest {
  string name = 1;
  string region = 2;
  NamespaceSpec spec = 3;
  string request_id = 4;  // Client-provided idempotency key
}

message CreateNamespaceResponse {
  string operation_id = 1;  // Poll this for completion
}

message ListNamespacesRequest {
  int32 page_size = 1;
  string page_token = 2;
  string filter = 3;       // e.g., "region = 'us-east-1'"
}

message ListNamespacesResponse {
  repeated Namespace namespaces = 1;
  string next_page_token = 2;
}
```

### API Versioning Strategies

For a platform API that enterprises depend on, versioning is critical:

**Package-based versioning** (Temporal's approach): The proto package includes the version.
`temporal.api.cloud.nexus.v1` becomes `temporal.api.cloud.nexus.v2`. This is clean for gRPC.

**Rules for avoiding breaking changes:**

- Adding new fields to messages: safe (proto3 ignores unknown fields)
- Adding new RPC methods: safe
- Adding new enum values: safe if clients handle unknown values
- Removing or renaming fields: BREAKING -- deprecate with a timeline instead
- Changing field types: BREAKING
- Changing field numbers: BREAKING

**Deprecation policy**: Mark fields as deprecated in proto comments, log warnings when
deprecated fields are used, remove after a published timeline (typically 6-12 months for
enterprise APIs).

### API Gateway Patterns

The API gateway sits in front of Cloud Nexus services and handles cross-cutting concerns:

```
Customer Request
     |
     v
+------------------+
|   API Gateway    |  <-- Authentication (API keys, OAuth tokens)
|                  |  <-- Rate limiting (per-tenant, per-endpoint)
|                  |  <-- Request routing (to correct backend service)
|                  |  <-- Request/response logging
+------------------+
     |
     v
+------------------+
|  Nexus Services  |  <-- Namespace service, connectivity service, etc.
+------------------+
```

**Authentication**: Temporal Cloud uses API keys and service account tokens. The gateway
validates these before requests reach backend services.

**Rate limiting**: Per-tenant rate limits prevent abuse. Different tiers get different limits.
Rate limit state lives in a shared store (Redis or similar) so all gateway instances enforce
consistent limits.

**Request routing**: The gateway routes to the correct backend service based on the RPC
method. This is simpler with gRPC than REST because the service and method are explicit
in every request.

---

## 4. Tenant Isolation

### Namespace-Based Isolation (Temporal's Model)

In Temporal Cloud, the **namespace** is the fundamental isolation boundary. Each customer
gets one or more namespaces, and namespaces provide:

- Separate workflow histories (no cross-namespace visibility)
- Independent task queues
- Per-namespace retention policies
- Per-namespace authentication and authorization

Cloud Nexus manages the lifecycle of these namespaces across the platform.

### Resource Isolation

Multi-tenant platforms must prevent one tenant from consuming all shared resources:

| Resource | Isolation Mechanism | Implementation |
|----------|-------------------|----------------|
| **Compute** | Per-namespace action rate limits | Token bucket per namespace, enforced at frontend |
| **Storage** | Per-namespace storage quotas | Track history size, reject writes over quota |
| **Network** | Per-tenant bandwidth limits | Network policy enforcement at ingress |
| **API calls** | Per-tenant rate limits | Gateway-level enforcement |

### Noisy Neighbor Prevention

The noisy neighbor problem is the defining challenge of multi-tenant systems. One customer's
burst traffic should not degrade another customer's experience.

**Token bucket rate limiting** at the namespace level:

```go
type NamespaceRateLimiter struct {
    mu       sync.Mutex
    tokens   float64
    maxTokens float64
    refillRate float64    // tokens per second
    lastRefill time.Time
}

func (r *NamespaceRateLimiter) Allow() bool {
    r.mu.Lock()
    defer r.mu.Unlock()

    now := time.Now()
    elapsed := now.Sub(r.lastRefill).Seconds()
    r.tokens = min(r.maxTokens, r.tokens + elapsed * r.refillRate)
    r.lastRefill = now

    if r.tokens >= 1 {
        r.tokens--
        return true
    }
    return false
}
```

**Fair scheduling** ensures no single tenant monopolizes shared worker pools. Weight-based
scheduling gives each tenant a proportional share of processing capacity, with burst
allowance when the system is underutilized.

### Data Isolation

Enterprise customers require strong data isolation guarantees:

- **Encryption at rest**: Each namespace can have its own encryption key (customer-managed
  encryption keys / CMEK). The platform stores which KMS key maps to which namespace and
  uses it for all data operations.
- **Encryption in transit**: mTLS between all components, with per-namespace certificates
- **Key management**: Integration with AWS KMS, GCP Cloud KMS, Azure Key Vault -- another
  place the provider abstraction pattern applies

### Compliance Isolation

Data residency requirements mean certain namespaces can only exist in specific regions:

```go
type NamespacePolicy struct {
    AllowedRegions   []string   // e.g., ["eu-west-1", "eu-central-1"]
    DataClassification string  // e.g., "pii", "financial", "general"
    RetentionDays    int
    RequireCMEK      bool
}

func (p *NamespacePolicy) ValidateRegion(region string) error {
    if len(p.AllowedRegions) == 0 {
        return nil // No restrictions
    }
    for _, allowed := range p.AllowedRegions {
        if region == allowed {
            return nil
        }
    }
    return fmt.Errorf("region %s not allowed by policy; allowed: %v", region, p.AllowedRegions)
}
```

---

## 5. Self-Service Platform Design

### Customer Onboarding Automation

Onboarding a new Temporal Cloud customer involves multiple steps that must happen reliably
and in order. This is a perfect use case for Temporal workflows.

```go
// OnboardCustomerWorkflow orchestrates the full customer onboarding.
func OnboardCustomerWorkflow(ctx workflow.Context, req OnboardRequest) (*OnboardResult, error) {
    var result OnboardResult

    // Step 1: Create account in identity provider
    err := workflow.ExecuteActivity(ctx, CreateAccountActivity, req.Account).Get(ctx, &result.AccountID)
    if err != nil {
        return nil, err
    }

    // Step 2: Provision initial namespace
    nsReq := ProvisionNamespaceRequest{
        AccountID: result.AccountID,
        Region:    req.PreferredRegion,
        Plan:      req.Plan,
    }
    err = workflow.ExecuteActivity(ctx, ProvisionNamespaceActivity, nsReq).Get(ctx, &result.NamespaceID)
    if err != nil {
        // Compensate: delete the account we just created
        _ = workflow.ExecuteActivity(ctx, DeleteAccountActivity, result.AccountID).Get(ctx, nil)
        return nil, err
    }

    // Step 3: Set up billing
    billingReq := SetupBillingRequest{
        AccountID:   result.AccountID,
        Plan:        req.Plan,
        PaymentInfo: req.PaymentInfo,
    }
    err = workflow.ExecuteActivity(ctx, SetupBillingActivity, billingReq).Get(ctx, &result.BillingID)
    if err != nil {
        // Compensate: delete namespace and account
        _ = workflow.ExecuteActivity(ctx, DeleteNamespaceActivity, result.NamespaceID).Get(ctx, nil)
        _ = workflow.ExecuteActivity(ctx, DeleteAccountActivity, result.AccountID).Get(ctx, nil)
        return nil, err
    }

    // Step 4: Configure connectivity (if requested)
    if req.Connectivity != nil {
        connReq := SetupConnectivityRequest{
            NamespaceID: result.NamespaceID,
            Config:      *req.Connectivity,
        }
        err = workflow.ExecuteActivity(ctx, SetupConnectivityActivity, connReq).Get(ctx, &result.ConnectionID)
        if err != nil {
            // Connectivity is optional -- don't fail onboarding, just record the error
            result.ConnectivityError = err.Error()
        }
    }

    return &result, nil
}
```

**Why use Temporal for this?** Because each step can fail, each step may need retries, and
you need compensating actions if later steps fail. This is exactly the Saga pattern that
Temporal excels at. If the billing setup fails, you don't want an orphaned namespace.

### Configuration Management

Declarative configuration lets customers define their desired state and let the platform
converge toward it:

```yaml
# Customer-facing namespace configuration
apiVersion: temporal.io/v1
kind: Namespace
metadata:
  name: production-workflows
  account: acme-corp
spec:
  region: aws-us-east-1
  retention: 30d
  searchAttributes:
    - name: CustomerId
      type: Keyword
    - name: OrderAmount
      type: Double
  encryption:
    provider: aws-kms
    keyArn: arn:aws:kms:us-east-1:123456789:key/abc-123
  connectivity:
    type: private-link
    allowedPrincipals:
      - arn:aws:iam::123456789:root
```

The platform takes this declaration and ensures the real-world state matches it. Drift
detection runs periodically to catch and reconcile mismatches.

### What Customers Can Do Themselves vs What Needs Support

| Self-Service | Requires Support |
|-------------|-----------------|
| Create/delete namespaces | Custom SLA agreements |
| Configure retention policies | Dedicated capacity allocation |
| Set up search attributes | Cross-account namespace migration |
| Configure private connectivity | Custom compliance configurations |
| Manage API keys and access | Billing disputes |
| View usage and billing dashboards | Region expansion requests |
| Adjust rate limits within plan | Plan customization beyond standard tiers |

The boundary is roughly: anything that can be validated and executed programmatically is
self-service. Anything requiring human judgment or custom negotiation goes through support.

---

## 6. Control Plane vs Data Plane

### Separation of Concerns

This is perhaps the most important architectural concept for the Cloud Nexus role.

```
+------------------------------------------------------+
|                    CONTROL PLANE                      |
|  (Cloud Nexus -- what THIS team builds)              |
|                                                       |
|  - Account management       - Billing                |
|  - Namespace provisioning   - API key management     |
|  - Connectivity setup       - Usage tracking         |
|  - Configuration management - Customer onboarding    |
+------------------------------------------------------+
          |                           |
          | Provisioning APIs         | Config propagation
          v                           v
+------------------------------------------------------+
|                     DATA PLANE                        |
|  (Temporal Cloud core -- a different team)           |
|                                                       |
|  - Workflow execution        - History storage       |
|  - Task queue matching       - Timer management      |
|  - Search attribute indexing - Event streaming       |
+------------------------------------------------------+
```

### Why They Are Separate

**Different availability requirements**: The data plane must be highly available --
customers' workflows are running there. The control plane can tolerate brief outages or
degradation. If the namespace creation API is slow for 5 minutes, that's annoying. If
workflow execution stalls for 5 minutes, that's a production incident for every customer.

**Different scaling patterns**: The data plane scales with workflow volume (millions of
workflow executions per second). The control plane scales with management operations
(hundreds of namespace changes per hour). Wildly different load profiles.

**Different deployment cadence**: The control plane can deploy more frequently because
it doesn't directly affect running workflows. The data plane needs more cautious rollouts.

**Blast radius containment**: A bug in namespace provisioning code should not be able to
affect running workflows. Physical separation (different services, different databases,
different clusters) enforces this.

### How They Interact

The control plane tells the data plane what to do through well-defined interfaces:

1. **Provisioning**: Control plane creates a namespace record, then calls data plane APIs
   to allocate resources (history shards, matching partitions, etc.)

2. **Configuration propagation**: When a customer changes a namespace setting (retention
   period, rate limit), the control plane writes the new config and the data plane picks
   it up. This can be eventually consistent -- a few seconds delay is acceptable.

3. **Usage reporting**: The data plane reports usage metrics (action counts, storage usage)
   back to the control plane for billing. This is also eventually consistent -- billing
   aggregates over minutes or hours, not milliseconds.

4. **Health monitoring**: The control plane monitors data plane health to surface status
   to customers and to trigger alerts.

### Availability Considerations

| Aspect | Control Plane | Data Plane |
|--------|--------------|------------|
| **Consistency** | Eventually consistent is fine | Strong consistency for workflow state |
| **Latency target** | Seconds acceptable | Milliseconds required |
| **Downtime impact** | Can't manage, but workloads keep running | Workloads stop executing |
| **Deployment** | Frequent, low-risk | Cautious, canary-first |
| **Blast radius** | Management operations only | All customer workloads |

---

## 7. Provisioning Workflows: Temporal Building Temporal

One of the most compelling aspects of this role: Temporal uses its own product to build
its platform. Provisioning workflows that create namespaces, set up connectivity, and
configure billing are themselves Temporal workflows.

### Why This Works

- **Automatic retries**: If an AWS API call fails, the activity retries automatically
- **Durability**: If the provisioning service crashes mid-workflow, it picks up where
  it left off when it restarts
- **Visibility**: Every provisioning operation has a full history in Temporal, making
  debugging straightforward
- **Timeouts**: If a cloud provider takes too long, the workflow can handle it gracefully
- **Compensation**: If step 3 fails, steps 1 and 2 can be rolled back via compensating
  activities

### Example: Namespace Provisioning Workflow

```go
func ProvisionNamespaceWorkflow(ctx workflow.Context, req ProvisionRequest) (*ProvisionResult, error) {
    // Configure activity options with retries
    actCtx := workflow.WithActivityOptions(ctx, workflow.ActivityOptions{
        StartToCloseTimeout: 5 * time.Minute,
        RetryPolicy: &temporal.RetryPolicy{
            InitialInterval:    time.Second,
            BackoffCoefficient: 2.0,
            MaximumInterval:    time.Minute,
            MaximumAttempts:    10,
        },
    })

    var result ProvisionResult

    // Step 1: Allocate resources in the data plane
    err := workflow.ExecuteActivity(actCtx, AllocateDataPlaneResources, req).Get(ctx, &result.DataPlaneID)
    if err != nil {
        return nil, fmt.Errorf("failed to allocate data plane resources: %w", err)
    }

    // Step 2: Configure networking
    err = workflow.ExecuteActivity(actCtx, ConfigureNetworking, ConfigureNetworkingRequest{
        DataPlaneID: result.DataPlaneID,
        Region:      req.Region,
        Provider:    req.Provider,
    }).Get(ctx, &result.NetworkConfig)
    if err != nil {
        // Compensate: deallocate data plane resources
        _ = workflow.ExecuteActivity(actCtx, DeallocateDataPlaneResources, result.DataPlaneID).Get(ctx, nil)
        return nil, fmt.Errorf("failed to configure networking: %w", err)
    }

    // Step 3: Set up encryption
    if req.EncryptionConfig != nil {
        err = workflow.ExecuteActivity(actCtx, ConfigureEncryption, ConfigureEncryptionRequest{
            DataPlaneID: result.DataPlaneID,
            KMSKeyARN:   req.EncryptionConfig.KeyARN,
        }).Get(ctx, nil)
        if err != nil {
            _ = workflow.ExecuteActivity(actCtx, DeallocateDataPlaneResources, result.DataPlaneID).Get(ctx, nil)
            return nil, fmt.Errorf("failed to configure encryption: %w", err)
        }
    }

    // Step 4: Update control plane records
    err = workflow.ExecuteActivity(actCtx, UpdateNamespaceRecord, UpdateNamespaceRecordRequest{
        NamespaceID: req.NamespaceID,
        Status:      "active",
        DataPlaneID: result.DataPlaneID,
    }).Get(ctx, nil)
    if err != nil {
        return nil, fmt.Errorf("failed to update namespace record: %w", err)
    }

    // Step 5: Send welcome notification
    _ = workflow.ExecuteActivity(actCtx, SendProvisioningCompleteNotification, req.NamespaceID).Get(ctx, nil)

    return &result, nil
}
```

---

## 8. Interview Questions

### System Design

1. **Design the namespace provisioning flow for Temporal Cloud. A customer calls CreateNamespace and expects a working namespace within minutes. Walk through the architecture.**

   Start with the API accepting the request and returning an operation ID. A Temporal workflow
   orchestrates provisioning: validate the request against the customer's plan, allocate
   resources in the data plane (history shards, matching partitions), configure networking,
   set up encryption, update the control plane database, notify the customer. Each step is
   an activity with retries. If a later step fails, compensating activities undo earlier
   steps. The customer polls the operation status or receives a webhook.

2. **How would you design the private connectivity feature to work across AWS, GCP, and Azure?**

   Define a provider-agnostic API (CreatePrivateConnection). Behind the API, provider-specific
   adapters handle the actual cloud plumbing. A provisioning workflow coordinates the
   multi-step process: create service endpoint on Temporal's side, wait for customer to
   accept the connection on their side (this involves polling or webhook notification),
   validate connectivity, update DNS. Each provider adapter implements the same interface
   but uses different cloud APIs. Error handling maps provider-specific errors to a common
   error model.

3. **You need to add a new cloud provider. How do you design the system so this is manageable?**

   The provider interface is the contract. Implement a new struct satisfying the interface.
   Add provider-specific configuration. Write integration tests against the new provider.
   Feature-flag the new provider for gradual rollout. The key is that no code outside the
   provider package should need to change -- the adapter pattern isolates provider-specific
   logic.

### Operational

4. **A customer reports their namespace creation has been stuck for 30 minutes. How do you investigate?**

   Look at the provisioning workflow in Temporal -- you can see exactly which activity is
   stuck. Check if it's retrying (cloud API failure?) or waiting (for customer action, like
   accepting a PrivateLink connection?). Check the specific cloud provider's health dashboard.
   Look at rate limit counters -- are we hitting provider API limits? Check the activity
   worker health -- are workers processing activities or are they all busy?

5. **How do you ensure a control plane outage doesn't affect running workflows?**

   Physical separation: different services, different databases, different failure domains.
   The data plane has no runtime dependency on the control plane. Configuration is pushed
   asynchronously with caching at the data plane level. Even if the control plane is
   completely down, the data plane operates on its last-known configuration. New workflows
   can still start (the data plane has the namespace config cached), and running workflows
   continue without interruption.

### Trade-offs

6. **Eventual consistency in the control plane: what are the edge cases?**

   A customer creates a namespace and immediately tries to start a workflow on it. The
   namespace exists in the control plane database but hasn't been provisioned in the data
   plane yet. Solution: the CreateNamespace API returns an operation ID, and the namespace
   status is "provisioning" until the workflow completes. The SDK can be configured to
   wait for "active" status. Another edge case: config changes that haven't propagated yet.
   A customer changes their retention policy but for a few seconds the old policy applies.
   For most config changes, this is acceptable.

7. **Self-service versus safety: where do you draw the line?**

   Self-service for anything that's reversible and well-understood: namespace CRUD,
   configuration changes, connectivity setup. Require support intervention for anything
   irreversible (data deletion without recovery), anything with billing implications beyond
   the customer's current plan, anything that affects other customers (shared infrastructure
   changes), and anything requiring human judgment (custom SLAs, compliance review).
