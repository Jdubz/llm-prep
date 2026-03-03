# Module 05: Circuit Breakers, Retry Strategies, and API Patterns

## Circuit Breakers

Circuit breakers prevent cascading failures by stopping requests to a failing downstream service.

### States

```
         success
    +----------------+
    |                |
    v                |
 [CLOSED] ---failures exceed threshold---> [OPEN]
    ^                                        |
    |                                        | timeout expires
    |                                        v
    +--------success----- [HALF-OPEN] ------+
                          (probe with
                           limited traffic)
              failure -> back to OPEN
```

**Closed:** Normal operation. Requests flow through. Failures are counted.

**Open:** All requests are immediately rejected (fail fast). No load on the downstream. After a configurable timeout, the circuit transitions to half-open.

**Half-Open:** A limited number of probe requests are sent to the downstream. If they succeed, the circuit closes. If they fail, the circuit reopens.

```
                    All requests pass through
                    Failures are counted
                           |
                      [ CLOSED ]
                           |
              failure rate exceeds threshold
                           |
                      [  OPEN  ]
                           |
                    All requests rejected
                    (fail fast)
                           |
                   timeout expires
                           |
                    [ HALF-OPEN ]
                           |
              +------------+-------------+
              |                          |
        probe succeeds              probe fails
              |                          |
         [ CLOSED ]                 [  OPEN  ]
```

**Key parameters:** 50% failure threshold in 10s window, 30s open timeout, 3 half-open probes.

### Configuration Parameters

- **Failure threshold:** Number or percentage of failures to trip the circuit (e.g., 50% of requests in a 10-second window).
- **Timeout:** How long to stay open before probing (e.g., 30 seconds).
- **Half-open max requests:** How many probe requests to allow (e.g., 3).
- **Monitoring window:** Time window for calculating failure rate (sliding window vs tumbling window).

### Bulkhead Pattern

Isolate failure domains by partitioning resources. If service A and service B share a thread pool and service B is slow, service B's requests consume all threads, starving service A.

**Solution:** Give each downstream its own connection pool, thread pool, or semaphore.

```
[Application]
  |
  +-- [Bulkhead: Service A] -- max 20 concurrent connections
  |
  +-- [Bulkhead: Service B] -- max 10 concurrent connections
  |
  +-- [Bulkhead: Service C] -- max 5 concurrent connections
```

### Implementation Libraries

| Language | Library | Notes |
|---|---|---|
| Java | Resilience4j | Successor to Hystrix; modular, lightweight |
| Go | sony/gobreaker | Simple, well-tested |
| Node.js | opossum | Prometheus metrics built-in |
| Python | pybreaker | Thread-safe |
| Service mesh | Envoy/Istio | Circuit breaking at the infrastructure layer |

**Interview insight:** Know when circuit breakers belong in application code vs. the service mesh. Application-level breakers give finer control (per-endpoint, per-tenant). Mesh-level breakers are easier to operate but coarser.

---

## Retry Strategies

### The Retry Storm Problem

Naive retries amplify failures. If a service is at 50% capacity and every client retries once, the service receives 2x traffic -- pushing it to 100%, causing more failures, triggering more retries. This positive feedback loop causes cascading collapse.

### Retry Budgets

Limit the total percentage of requests that can be retries. For example, allow retries for at most 20% of total requests. If the retry budget is exhausted, fail immediately.

```
Total requests in window: 1000
Retries allowed: 200 (20% budget)
Retries used: 198
Next failed request: NOT retried (budget nearly exhausted)
```

### Exponential Backoff with Jitter

```
delay = min(base * 2^attempt + random_jitter, max_delay)
```

- **Base delay:** 100ms
- **Max delay:** 30 seconds (cap to prevent absurd waits)
- **Jitter:** Random value between 0 and the current delay

**Why jitter?** Without jitter, all clients that failed at the same time retry at the same time (thundering herd). Full jitter decorrelates retries.

```python
import random

def backoff_with_jitter(attempt, base=0.1, max_delay=30.0):
    exp_delay = min(base * (2 ** attempt), max_delay)
    return random.uniform(0, exp_delay)  # Full jitter
```

**Retry Strategy Template:**

```
delay = min(base * 2^attempt, max_delay)
sleep(random(0, delay))   # full jitter
```

**Retryable:** 5xx, 429 (with Retry-After), connection refused, timeout (if idempotent).
**Non-retryable:** 4xx (except 429), auth failures, validation errors.
**Retry budget:** max 20% of total requests can be retries.

### Idempotency Requirements

Retries are only safe for idempotent operations. If a request is not idempotent (e.g., "charge the customer"), you need:

1. **Idempotency keys:** The client generates a unique key per logical operation. The server deduplicates based on this key.
2. **At-most-once semantics:** If the server processed the request but the response was lost, the retry returns the cached response.

**Critical interview point:** Network timeouts do not mean the request failed. The server may have processed it successfully but the response was lost. Retrying a non-idempotent operation can cause duplicate charges, double writes, etc.

### Retry Decision Matrix

| Error Type | Retry? | Why |
|---|---|---|
| 4xx (client error) | No | The request is invalid; retrying won't help |
| 429 (rate limited) | Yes, with backoff | Respect Retry-After header |
| 5xx (server error) | Yes, with backoff | Server may recover |
| Connection refused | Yes, with backoff | Server may be restarting |
| Timeout | Maybe | Check idempotency first |

---

## DNS-Based Routing

### GeoDNS

Returns different IP addresses based on the client's geographic location (inferred from the resolver's IP or EDNS Client Subnet).

**Use case:** Route European users to `eu-west-1`, US users to `us-east-1`.

**Limitation:** DNS resolvers may not be geographically close to the user (e.g., Google 8.8.8.8 resolves from centralized locations). EDNS Client Subnet (ECS) mitigates this by passing client subnet information to the authoritative DNS.

### Latency-Based Routing

Measures latency from DNS resolver locations to each endpoint and returns the lowest-latency endpoint. AWS Route 53 supports this natively.

**Advantage over GeoDNS:** Geographic proximity does not always equal lowest latency (ocean cables, peering agreements).

### Weighted DNS

Distribute a percentage of DNS responses across endpoints. Useful for gradual traffic migration between regions or providers.

```
api.example.com  A  10.0.1.1  weight=70
api.example.com  A  10.0.2.1  weight=30
```

### TTL Considerations

DNS TTL controls how long resolvers cache records. This creates a tension:

- **Low TTL (30-60s):** Fast failover, but higher DNS query volume and slightly higher latency (more lookups).
- **High TTL (300-3600s):** Fewer queries, but slow failover. Users may be directed to a failed endpoint for minutes.

**Best practice:** Use low TTLs (30-60s) for records that need fast failover. Use higher TTLs for stable records (CDN CNAMEs).

**Warning:** Some clients and resolvers ignore TTL. Java's default DNS caching is notorious for caching forever unless explicitly configured (`networkaddress.cache.ttl`).

### DNS Failover

Health-check-integrated DNS that removes unhealthy endpoints from responses. Providers like Route 53, Cloudflare, and NS1 support this.

**Limitation:** Even with low TTLs, failover is not instantaneous. Cached records may still direct traffic to failed endpoints for `TTL` seconds after the failure is detected.

### DNS Record Types

| Record | Purpose | Example |
|---|---|---|
| A | IPv4 address | `api.example.com -> 10.0.1.1` |
| AAAA | IPv6 address | `api.example.com -> 2001:db8::1` |
| CNAME | Alias to another domain | `www.example.com -> cdn.provider.com` |
| NS | Authoritative nameserver | `example.com -> ns1.provider.com` |
| SRV | Service location (host + port) | `_http._tcp.example.com -> 10 0 8080 server1` |
| TXT | Arbitrary text (SPF, DKIM, verification) | `example.com -> "v=spf1 ..."` |
| MX | Mail exchange | `example.com -> 10 mail.example.com` |

**TTL guidelines:**
- Fast failover needed: 30-60s
- Stable records: 300-3600s
- Migration in progress: Lower TTL 24h before migration

---

## Service Mesh

### What Is a Service Mesh?

A dedicated infrastructure layer for service-to-service communication. It externalizes cross-cutting concerns (retries, circuit breaking, mTLS, observability) from application code into sidecar proxies.

### Sidecar Proxy Model

Every pod gets a sidecar proxy (typically Envoy). All inbound and outbound traffic flows through the sidecar.

```
[Pod]
  +-- [App Container] <--localhost--> [Sidecar Proxy (Envoy)]
                                           |
                                      (mTLS to other sidecars)
                                           |
[Pod]
  +-- [App Container] <--localhost--> [Sidecar Proxy (Envoy)]
```

```
+------------------Control Plane------------------+
|                                                  |
|  [Config Store]  [Certificate Authority]         |
|  [Service Discovery]  [Policy Engine]            |
|                                                  |
+--------------------------------------------------+
        |  xDS API (config push)
        v
+--Data Plane (per pod)------+
|                             |
|  [App] <--> [Sidecar Proxy] |
|              (Envoy)        |
+-----------------------------+
```

**Control plane:** istiod. **Data plane:** Envoy sidecars per pod.

### Istio vs Linkerd

| Feature | Istio | Linkerd |
|---|---|---|
| Proxy | Envoy | linkerd2-proxy (Rust) |
| Complexity | High (many CRDs, steep learning curve) | Low (simpler API surface) |
| Performance | Higher resource overhead | Lighter weight, lower latency |
| Traffic management | Very rich (VirtualService, DestinationRule) | Good but simpler |
| Multi-cluster | Supported but complex | Simpler multi-cluster |
| Community | Larger ecosystem, CNCF graduated | CNCF graduated, focused scope |

### Core Capabilities

**mTLS:** Automatic mutual TLS between services. No application code changes. The mesh handles certificate issuance, rotation, and verification.

**Traffic management:** Canary deployments (route 5% of traffic to v2), traffic mirroring (shadow traffic to a new version), fault injection (test resilience by injecting delays/errors).

**Observability:** Automatic metrics (latency, error rate, request volume), distributed tracing headers, service-to-service traffic visualization.

### When a Service Mesh Is Overkill

- Fewer than 10 services. The operational overhead of the mesh exceeds the benefit.
- Teams without Kubernetes expertise. A mesh adds significant operational complexity.
- Latency-critical paths where sidecar proxy overhead (~1ms per hop) is unacceptable.
- When simpler alternatives (library-based retries, application-level mTLS) suffice.

**Use when:** 10+ services, mTLS needed, complex traffic management.
**Skip when:** <10 services, team lacks K8s depth, tight latency budgets.

**Interview insight:** Demonstrate judgment by knowing when NOT to use a service mesh. Saying "we should add Istio" without understanding the operational cost is a red flag.

---

## gRPC vs REST vs GraphQL at Scale

### REST (HTTP/JSON)

**Strengths:** Universal tooling, human-readable, cache-friendly (HTTP caching), well-understood. Ideal for public APIs where developer experience matters.

**Weaknesses at scale:** Over-fetching (client gets fields it doesn't need), under-fetching (client needs multiple requests), no type safety without additional tooling (OpenAPI).

### gRPC (HTTP/2 + Protocol Buffers)

**Strengths:**
- Binary serialization (protobuf): 3-10x smaller payloads, 5-20x faster serialization than JSON.
- HTTP/2 multiplexing: Multiple requests over a single TCP connection.
- Streaming: Unary, server-streaming, client-streaming, bidirectional streaming.
- Code generation: Strongly typed clients and servers in dozens of languages.
- Deadlines: Built-in deadline propagation across service boundaries.

**Weaknesses:** Browser support requires grpc-web proxy, not human-readable, harder to debug with curl.

**When gRPC shines:** Internal service-to-service communication, high-throughput low-latency paths, streaming workloads, polyglot environments where type safety across languages is critical.

### GraphQL

**Strengths:** Client specifies exact data shape (no over/under-fetching), single endpoint, strong type system (schema), excellent for frontend-driven development.

**Weaknesses at scale:**
- Query complexity can cause N+1 problems on the backend (mitigated with DataLoader).
- Caching is harder (POST requests, variable query shapes).
- Authorization per field is complex.
- Large queries can be expensive -- requires query cost analysis and depth limiting.

**When GraphQL shines:** API aggregation layer over multiple microservices, mobile apps with bandwidth constraints, rapidly evolving frontend requirements.

### Decision Matrix

| Factor | REST | gRPC | GraphQL |
|---|---|---|---|
| Public API | Best | Poor (tooling) | Good |
| Internal services | Good | Best | Overkill |
| Streaming | WebSocket addon | Native | Subscriptions (complex) |
| Performance | Good | Best | Depends on query |
| Caching | HTTP caching | Custom | Complex |
| Browser clients | Native | Needs proxy | Native |

---

## API Gateway Patterns

### Core Responsibilities

An API gateway sits at the edge of your system, handling cross-cutting concerns before requests reach backend services.

**Rate limiting:** Token bucket or sliding window per client/API key. Return `429 Too Many Requests` with `Retry-After` header.

**Authentication and authorization:** Validate JWTs, API keys, or OAuth tokens. Reject unauthorized requests before they reach backends.

**Request transformation:** Rewrite paths, add/remove headers, transform request/response bodies.

**Routing:** Direct requests to the appropriate backend service based on path, host, or headers.

### Backend for Frontend (BFF) Pattern

Instead of one monolithic API gateway, create purpose-built API layers for each client type.

```
[Mobile App] --> [Mobile BFF] --> [Service A, B]
[Web App]    --> [Web BFF]    --> [Service A, C]
[Partner API]--> [Partner GW] --> [Service B, D]
```

**Why BFF?**
- Mobile needs different data shapes (smaller payloads, combined endpoints).
- Web may need server-side rendering support.
- Partner APIs have different auth, rate limits, and SLAs.
- Teams can evolve each BFF independently.

### Common API Gateway Technologies

| Gateway | Strengths |
|---|---|
| Kong | Plugin ecosystem, Lua/Go extensibility, DB-less mode |
| AWS API Gateway | Serverless, Lambda integration, managed |
| Envoy + custom control plane | Maximum flexibility, gRPC-native |
| Traefik | Auto-discovery, Let's Encrypt, K8s-native |
| APISIX | High performance, dashboard, plugin hot-reload |

### Gateway Anti-Patterns

- **God gateway:** Putting business logic in the gateway. It should only handle cross-cutting infrastructure concerns.
- **Single point of failure:** The gateway itself must be highly available (multiple instances, health-checked).
- **Tight coupling:** Avoid gateway configurations that tightly couple to backend service internals.

---

## Interview Questions

### Conceptual

1. **You're seeing intermittent 502 errors from your load balancer. Walk me through your debugging process.**

   Start with the LB health check logs -- are backends being marked unhealthy? Check backend connection limits (max connections reached?). Examine backend response times -- are they exceeding the LB's `proxy_read_timeout`? Look at the LB's connection pool -- are connections to backends being reused or re-established? Check for TCP RST packets between LB and backends (network issues). Verify keep-alive settings match between LB and backends. A common cause is a race condition where the backend closes a keep-alive connection just as the LB sends a new request on it.

2. **What is a retry storm?** Cascading retries that amplify load on a failing service, turning a partial failure into a total outage.

3. **Why use exponential backoff with jitter?** Exponential backoff reduces load over time. Jitter decorrelates retries to prevent thundering herd.

4. **What is the BFF pattern?** Backend for Frontend -- a dedicated API layer per client type (mobile, web, partner) to serve optimized data shapes.

5. **What does the half-open state in a circuit breaker do?** Allows a limited number of probe requests through to test if the downstream has recovered.

6. **Why might DNS failover be insufficient for high-availability?** DNS TTL means clients may cache stale records pointing to failed endpoints for seconds to minutes after failure.

7. **What is the bulkhead pattern?** Isolating failure domains by giving each downstream its own resource pool, preventing one slow dependency from starving others.

8. **When is a service mesh overkill?** Small number of services, team lacks K8s expertise, latency overhead is unacceptable, or simpler alternatives (library-based) suffice.

### System Design

9. **Your microservice architecture has 50 services. A single service failure is cascading across the system. How do you prevent this?**

   Implement circuit breakers on all inter-service calls with per-downstream bulkheads (isolated connection pools). Set retry budgets (max 20% retries) to prevent retry storms. Add timeouts on every outbound call -- no unbounded waits. Implement graceful degradation: if a recommendation service is down, show default recommendations rather than failing the entire page. Consider a service mesh (Istio) if the team has the operational maturity -- it externalizes these patterns. Monitor with RED metrics (Rate, Errors, Duration) per service pair to identify cascades early.

10. **When would you choose gRPC over REST for a new microservice?**

    Choose gRPC when the service is internal (no browser clients), requires streaming (bidirectional updates), needs high throughput with low latency (binary serialization matters), or operates in a polyglot environment where code-generated clients reduce integration bugs. Choose REST when the API is public-facing, needs to be browsable/debuggable with standard tools, benefits from HTTP caching, or the team is not experienced with protobuf/gRPC tooling. In practice, many organizations use gRPC for internal service-to-service and REST/GraphQL at the edge.

---

## Related Reading

- [Module 05: Load Balancing Fundamentals](01-load-balancing-fundamentals.md) -- the load balancing algorithms and health check patterns that circuit breakers complement
- [Module 05: Advanced Load Balancing Patterns](03-advanced-load-balancing-patterns.md) -- service mesh (Istio, Linkerd) externalizes circuit breakers and retries into the infrastructure layer, and Envoy implements many of these patterns natively
- [Module 04: Message Brokers](../04-message-queues/01-message-brokers-kafka-sqs-rabbitmq.md) -- DLQ and retry patterns for message consumers mirror the retry and circuit breaker patterns for synchronous calls
- [Module 06: Kubernetes Advanced Patterns](../06-containers-orchestration/03-kubernetes-advanced-patterns.md) -- service mesh deep dive covers how Istio and Linkerd implement circuit breakers, retry budgets, and bulkheads as sidecar proxies
- [Module 08: Logging, Metrics, and Tracing](../08-observability/01-logging-metrics-and-tracing.md) -- monitoring circuit breaker state changes, retry rates, and error budgets with Prometheus metrics and distributed tracing
- [Module 08: SLOs, Alerting, and Incident Response](../08-observability/02-slos-alerting-and-incident-response.md) -- burn rate alerting detects when circuit breakers should be opening; SLO error budgets quantify how much failure is acceptable
