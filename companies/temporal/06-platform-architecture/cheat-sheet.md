# Module 06 Cheat Sheet: Platform Architecture Quick Reference

## Cloud Nexus Architecture Overview

```
                          Customers
                             |
                      +------+------+
                      | API Gateway |
                      | - Auth      |
                      | - Rate limit|
                      | - Routing   |
                      +------+------+
                             |
              +--------------+--------------+
              |              |              |
     +--------+--+   +------+----+  +------+------+
     | Namespace |   |Connectivity|  |  Account    |
     | Service   |   | Service   |  |  Service    |
     +---------+-+   +-----+-----+  +------+------+
               |            |              |
         +-----+------------+--------------+----+
         |          CONTROL PLANE DB            |
         |  (accounts, namespaces, config,      |
         |   operations, billing)               |
         +-------------------+------------------+
                             |
              +--------------+--------------+
              |              |              |
     +--------+--+   +------+----+  +------+------+
     | AWS       |   | GCP       |  | Azure       |
     | Provider  |   | Provider  |  | Provider    |
     +-----------+   +-----------+  +-------------+
              |              |              |
         +----+--------------+--------------+----+
         |            DATA PLANE                 |
         |  (workflow execution, history,        |
         |   task queues, timers)                |
         +---------------------------------------+
```

---

## Multi-Cloud Abstraction Pattern

```go
// 1. Define the interface
type CloudProvider interface {
    CreateNamespace(ctx context.Context, req *CreateNSReq) (*Namespace, error)
    SetupConnectivity(ctx context.Context, req *ConnReq) (*Connection, error)
    // ... other operations
}

// 2. Implement per provider
type AWSProvider struct { /* AWS clients */ }
type GCPProvider struct { /* GCP clients */ }

// 3. Select at runtime from config
func NewProvider(cfg RegionConfig) CloudProvider {
    switch cfg.Provider {
    case "aws":  return &AWSProvider{...}
    case "gcp":  return &GCPProvider{...}
    case "azure": return &AzureProvider{...}
    }
}
```

---

## Tenant Isolation Strategies

| Strategy | What It Isolates | Implementation | Trade-off |
|----------|-----------------|----------------|-----------|
| **Namespace isolation** | Workflow data, task queues | Separate namespace per customer | Logical only, shared infra |
| **Rate limiting** | Compute, API access | Token bucket per tenant | Must tune limits per plan |
| **Storage quotas** | Disk, history size | Track usage, reject over quota | Need monitoring + alerts |
| **Network isolation** | Traffic, connectivity | PrivateLink/PSC per tenant | Expensive per-tenant setup |
| **Encryption isolation** | Data at rest | Per-tenant KMS keys (CMEK) | Key management complexity |
| **Cell isolation** | Full stack | Dedicated cell per tenant | Most expensive, most isolated |

---

## Control Plane vs Data Plane

| | Control Plane | Data Plane |
|---|---|---|
| **Owns** | Accounts, billing, config, provisioning | Workflow execution, history, task queues |
| **Team** | Cloud Nexus (your team) | Temporal Cloud core |
| **Consistency** | Eventually consistent OK | Strong consistency required |
| **Latency** | Seconds acceptable | Milliseconds required |
| **If it goes down** | Can't manage, but workloads run | Workloads stop |
| **Scales with** | Management operations | Workflow volume |
| **Deploy cadence** | Frequent | Cautious, canary-first |

---

## API Design Checklist for Platform Services

**Every resource should have:**
- [ ] Create (returns operation ID for async creation)
- [ ] Get (by ID)
- [ ] List (with pagination, filtering, sorting)
- [ ] Update (partial update with field masks)
- [ ] Delete (returns operation ID for async deletion)

**Every mutating endpoint should have:**
- [ ] Idempotency key (client-provided `request_id`)
- [ ] Input validation with structured error messages
- [ ] Authorization check
- [ ] Audit logging
- [ ] Rate limiting

**Every list endpoint should have:**
- [ ] Page size parameter (with max limit, e.g., 100)
- [ ] Page token (opaque cursor, not offset)
- [ ] Filter parameter
- [ ] Order by parameter
- [ ] next_page_token in response (empty = last page)

**Error responses should include:**
- [ ] gRPC status code (mapped consistently)
- [ ] Machine-readable error code (`NAMESPACE_NOT_FOUND`)
- [ ] Human-readable message
- [ ] Retryable flag
- [ ] Offending field name (for validation errors)

---

## Self-Service Onboarding Flow

```
Customer signs up
       |
       v
[1. Create Identity] --fail--> Done (error)
       |
       v
[2. Create Account]  --fail--> Compensate: delete identity
       |
       v
[3. Setup Billing]   --fail--> Compensate: deactivate account, delete identity
       |
       v
[4. Provision NS]    --fail--> Compensate: cancel billing, deactivate account, delete identity
       |
       v
[5. Welcome Email]   --fail--> Log warning, continue (best effort)
       |
       v
    Complete
```

Each step is a Temporal activity with retry policy. The whole flow is a Temporal workflow
with Saga-pattern compensation. Workflow ID = operation ID for status polling.

---

## Cell-Based Architecture

```
           Cell Router (stateless, caches assignments)
          /            |             \
     +------+     +------+     +------+
     |Cell 1|     |Cell 2|     |Cell 3|
     |------|     |------|     |------|
     | App  |     | App  |     | App  |
     | DB   |     | DB   |     | DB   |
     | Cache|     | Cache|     | Cache|
     +------+     +------+     +------+
     T: A,B,C     T: D,E,F     T: G,H,I
```

**Key properties:**
- Each cell is a complete, self-contained stack
- Blast radius limited to tenants in one cell
- Scale by adding cells, not by vertically scaling
- Deploy canary per-cell (roll out to Cell 1, verify, then Cell 2, etc.)
- Tenant migration between cells orchestrated by Temporal workflow

---

## Multi-Region Patterns

| Pattern | Failover Time | Consistency | Cost | Complexity |
|---------|---------------|-------------|------|------------|
| **Active-passive** | Minutes (DNS) | Strong (single writer) | Medium (idle standby) | Low |
| **Active-active (reads)** | Seconds | Eventual for reads | High | Medium |
| **Active-active (full)** | Near-zero | Eventual (conflicts) | Highest | Highest |
| **Single-leader per resource** | Seconds (re-election) | Strong per resource | Medium | Medium |

**Cloud Nexus recommendation:** Single leader per resource. Each namespace is owned by one
region. Writes route to the owner. Reads served locally from replicated data. Ownership
transfers during failover.

---

## Private Connectivity by Provider

| Provider | Mechanism | Temporal Side | Customer Side |
|----------|-----------|--------------|---------------|
| **AWS** | PrivateLink | VPC endpoint service | VPC endpoint |
| **GCP** | Private Service Connect | Service attachment | Forwarding rule |
| **Azure** | Private Link | Private link service | Private endpoint |

Unified API: `CreatePrivateConnection(namespace_id, provider, customer_account, customer_vpc, region)`

---

## Platform Monitoring Checklist

**Platform-level (low cardinality, always on):**
- [ ] Request rate and error rate by service and method
- [ ] p50/p95/p99 latency by service and method
- [ ] Provisioning workflow success/failure rate
- [ ] Database replication lag
- [ ] Queue depth for async operations
- [ ] Cloud provider API error rates

**Tenant-level (high cardinality, stored separately):**
- [ ] Per-tenant API call counts
- [ ] Per-tenant error rates
- [ ] Per-namespace action counts (for billing)
- [ ] Per-tenant storage usage
- [ ] Per-tenant rate limit hit counts

**Billing-specific:**
- [ ] Usage event pipeline lag
- [ ] Reconciliation discrepancies between data plane usage and billing records
- [ ] Anomaly detection on per-tenant usage (sudden spikes/drops)

---

## Key Interview Questions and Answer Frameworks

**1. "Design namespace provisioning for Temporal Cloud."**
- API accepts request, returns operation ID
- Temporal workflow orchestrates: validate plan -> allocate data plane resources -> configure networking -> set up encryption -> update control plane DB
- Each step is an activity with retries
- Saga compensation if later steps fail
- Customer polls operation status

**2. "How do you handle multi-cloud abstraction?"**
- Provider interface defines the contract
- Per-provider adapter implements the interface
- Config-driven provider selection at runtime
- Error normalization across providers
- Adding a new provider = new adapter, no other code changes

**3. "How do you prevent noisy neighbors?"**
- Per-namespace rate limits (token bucket)
- Per-tenant API rate limits at the gateway
- Storage quotas per namespace
- Fair scheduling in shared worker pools
- Cell-based isolation for largest tenants

**4. "Control plane goes down. What happens?"**
- Running workflows continue unaffected (data plane independent)
- New namespace creation / config changes fail
- Data plane uses cached configuration
- Customer dashboards / billing become unavailable
- Key insight: this is inconvenient, not catastrophic

**5. "How do you migrate a tenant between cells?"**
- Start double-writing to source and destination
- Copy historical data in background
- Verify consistency (checksums)
- Atomically update routing table
- Drain in-flight requests from source
- All orchestrated by Temporal workflow with compensation

**6. "Design the API versioning strategy."**
- Package-based versioning in proto (`v1`, `v2`)
- Additive changes within a version are safe
- Removing/renaming fields is a new version
- Deprecation timeline: announce, log warnings, remove after 6-12 months
- Run multiple versions concurrently during migration

**7. "How does config propagation work from control plane to data plane?"**
- Push for urgent changes (key revocations): message bus broadcast
- Pull with caching for routine changes: periodic poll + TTL cache
- Hybrid: push notification, pull details
- Target: routine < 30s, security-critical < 5s
