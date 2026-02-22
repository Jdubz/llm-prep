# Module 05: Load Balancing & Networking

## Overview

Load balancing sits at the intersection of reliability, performance, and scalability. At senior-level interviews, you are expected to reason about trade-offs across OSI layers, articulate why a particular algorithm fits a workload, and design resilient systems that degrade gracefully. This module covers the full spectrum -- from low-level TCP load balancing to high-level API gateway patterns -- with a focus on the "why" behind every decision.

---

## Table of Contents

1. [L4 vs L7 Load Balancing](#l4-vs-l7-load-balancing)
2. [Load Balancing Algorithms](#load-balancing-algorithms)
3. [Health Checks](#health-checks)
4. [Circuit Breakers](#circuit-breakers)
5. [Retry Strategies](#retry-strategies)
6. [DNS-Based Routing](#dns-based-routing)
7. [Service Mesh](#service-mesh)
8. [Reverse Proxy Patterns](#reverse-proxy-patterns)
9. [gRPC vs REST vs GraphQL at Scale](#grpc-vs-rest-vs-graphql-at-scale)
10. [API Gateway Patterns](#api-gateway-patterns)
11. [Interview Questions](#interview-questions)

---

## L4 vs L7 Load Balancing

### Layer 4: Transport Layer (TCP/UDP)

L4 load balancers operate on TCP/UDP segments. They see source/destination IP and port, but **not** the application payload. The balancer establishes (or NATs) the connection without inspecting content.

**How it works:**

1. Client sends SYN to the virtual IP (VIP).
2. The balancer selects a backend using its configured algorithm.
3. The balancer either:
   - **NATs** the packets (DSR or full NAT), forwarding them to the backend, or
   - **Terminates** the TCP connection and opens a new one to the backend (TCP proxy mode).
4. All subsequent packets for that connection follow the same path.

**When to use L4:**

- Non-HTTP protocols (databases, message queues, custom TCP/UDP services).
- Ultra-low-latency requirements where parsing HTTP headers is unacceptable overhead.
- Extremely high throughput scenarios (millions of packets/sec) -- L4 is cheaper per connection.
- TLS passthrough when backends must terminate TLS themselves.

**Performance characteristics:**

- Kernel-bypass implementations (DPDK, XDP/eBPF) can handle tens of millions of packets/sec.
- Latency overhead is typically sub-millisecond.
- Memory footprint is small -- only connection tuples are tracked.

### Layer 7: Application Layer (HTTP/HTTPS)

L7 load balancers inspect the full HTTP request -- headers, URI, cookies, body (if configured). This enables content-based routing but comes at a cost.

**How it works:**

1. Client completes TLS handshake with the load balancer (TLS termination).
2. The balancer fully parses the HTTP request.
3. Routing decision is made based on host header, path, headers, cookies, etc.
4. A new connection (or pooled connection) is opened to the selected backend.

**When to use L7:**

- Path-based routing (`/api/v2` -> service A, `/static` -> CDN origin).
- Host-based routing (multi-tenant, microservice routing).
- Header injection (X-Forwarded-For, X-Request-ID, tracing headers).
- Request/response transformation.
- Web Application Firewall (WAF) integration.
- A/B testing and canary deployments via header or cookie matching.

**Performance characteristics:**

- TLS termination adds 1-2ms per new connection (amortized with connection reuse).
- HTTP parsing adds CPU overhead proportional to header size.
- Connection multiplexing (HTTP/2) between LB and backends can reduce backend connection count.

### Key Interview Insight

The common trap is treating L4 and L7 as mutually exclusive. In production architectures, they are **layered**: an L4 balancer (e.g., AWS NLB, MetalLB) distributes traffic across a fleet of L7 balancers (e.g., Envoy, nginx). This gives you both raw throughput at the edge and intelligent routing at the application layer.

---

## Load Balancing Algorithms

### Round Robin

Each backend receives requests in sequential order. Simple, stateless, and effective when backends are homogeneous and requests are roughly uniform in cost.

**Limitation:** Ignores backend capacity and current load. One slow backend accumulates in-flight requests.

### Weighted Round Robin

Assign weights proportional to backend capacity. A backend with weight 3 receives three times the traffic of a backend with weight 1.

**Use case:** Mixed instance types (e.g., 4-core and 8-core machines in the same pool). Gradual traffic shifting during canary deployments.

### Least Connections

Route to the backend with the fewest active connections. Naturally adapts to heterogeneous request durations.

**Limitation:** Requires the balancer to track connection counts. In a distributed LB setup (multiple LB instances), each only sees its own connections, leading to suboptimal decisions.

**Variant -- Weighted Least Connections:** Combines connection count with weight, selecting the backend with the lowest `connections / weight` ratio.

### IP Hash

Hash the client IP to deterministically select a backend. Provides session affinity without cookies.

**Limitation:** Uneven distribution if traffic comes from a small number of NAT gateways. Adding/removing backends rehashes all clients.

### Consistent Hashing

Maps both backends and request keys onto a hash ring. Each request routes to the next backend clockwise on the ring. When a backend is added or removed, only `1/N` of keys are remapped (where N is the number of backends).

**Virtual nodes:** Each physical backend is mapped to multiple points on the ring to improve uniformity. Typical deployments use 100-200 virtual nodes per backend.

**Use case:** Cache-aware load balancing where you want the same user's requests to hit the same cache-warm backend. This is critical for in-memory session stores, local caches, and connection pooling to sharded databases.

```
Hash Ring (simplified):

  Backend-A(v1)  Backend-B(v1)  Backend-C(v1)
       |              |              |
  0 ---+----+---------+------+------+--- 2^32
             |               |
        Backend-A(v2)   Backend-C(v2)

Request hash lands between B(v1) and C(v1) -> routes to C(v1)
If C is removed, those requests move to A(v2) -- minimal disruption
```

### Algorithm Selection Guide

| Scenario | Recommended Algorithm |
|---|---|
| Homogeneous backends, uniform requests | Round Robin |
| Mixed instance sizes | Weighted Round Robin |
| Variable request durations (long-polling, WebSockets) | Least Connections |
| Need session affinity, no cookies | IP Hash |
| Cache-warm routing, minimal remapping on scale | Consistent Hashing |

---

## Health Checks

### Active Health Checks

The load balancer proactively sends requests to backends at regular intervals.

**TCP health check:** Opens a TCP connection. If the handshake completes, the backend is healthy. Fast and low overhead, but only confirms the port is open -- does not validate application health.

**HTTP health check:** Sends an HTTP request (typically `GET /healthz`). Validates status code (e.g., 2xx), optionally checks response body or latency threshold.

**Configuration parameters:**

- **Interval:** How often to check (e.g., every 5 seconds).
- **Timeout:** Max time to wait for a response (e.g., 3 seconds).
- **Healthy threshold:** Consecutive successes to mark a backend healthy (e.g., 2).
- **Unhealthy threshold:** Consecutive failures to mark a backend unhealthy (e.g., 3).

```
Timeline: Backend goes unhealthy

t=0s   Check: OK
t=5s   Check: FAIL (count=1)
t=10s  Check: FAIL (count=2)
t=15s  Check: FAIL (count=3) -> Backend marked UNHEALTHY, removed from pool
...
t=45s  Check: OK (count=1)
t=50s  Check: OK (count=2) -> Backend marked HEALTHY, added back to pool
```

### Passive Health Checks

The load balancer monitors actual traffic responses. If a backend returns errors (5xx) or times out on real requests, it is marked unhealthy.

**Advantages:** No synthetic traffic. Detects issues that only manifest under real load.

**Disadvantages:** A backend must receive (and fail) real requests before being removed. Potentially impacts users.

### Best Practice: Combine Both

Use active checks to catch backends that are completely down. Use passive checks to catch backends that are degraded (responding slowly, returning errors intermittently). Libraries like Envoy support both simultaneously.

### Graceful Degradation

Health endpoints should reflect dependency health with nuance:

```
GET /healthz        -> Am I alive? (liveness)
GET /readyz         -> Am I ready to serve traffic? (readiness)
GET /healthz/deep   -> Are all my dependencies healthy? (deep check)
```

**Critical rule:** A deep health check that fails because a non-critical dependency is down should **not** cause the load balancer to remove the backend. Use readiness probes for traffic-serving ability and liveness probes only for "is the process stuck."

---

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

**Interview insight:** Demonstrate judgment by knowing when NOT to use a service mesh. Saying "we should add Istio" without understanding the operational cost is a red flag.

---

## Reverse Proxy Patterns

### nginx

The workhorse of the industry. Excellent for static content, TLS termination, and HTTP routing.

```nginx
upstream backend {
    least_conn;
    server 10.0.0.1:8080 weight=5;
    server 10.0.0.2:8080 weight=3;
    server 10.0.0.3:8080 backup;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
    }
}
```

### HAProxy

Purpose-built for load balancing. Superior connection handling and health checking. Preferred for TCP load balancing.

```haproxy
frontend http_front
    bind *:443 ssl crt /etc/ssl/cert.pem
    default_backend http_back

    acl is_api path_beg /api
    use_backend api_back if is_api

backend http_back
    balance leastconn
    option httpchk GET /healthz
    http-check expect status 200
    server web1 10.0.0.1:8080 check inter 5s fall 3 rise 2
    server web2 10.0.0.2:8080 check inter 5s fall 3 rise 2

backend api_back
    balance roundrobin
    server api1 10.0.1.1:8080 check
    server api2 10.0.1.2:8080 check
```

### Envoy

Modern, API-driven proxy. First-class gRPC, HTTP/2, and observability support. The backbone of most service meshes.

```yaml
# Envoy configuration (simplified)
static_resources:
  listeners:
    - address:
        socket_address: { address: 0.0.0.0, port_value: 8080 }
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                route_config:
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match: { prefix: "/" }
                          route:
                            cluster: backend_cluster
                            retry_policy:
                              retry_on: "5xx"
                              num_retries: 3

  clusters:
    - name: backend_cluster
      type: STRICT_DNS
      lb_policy: ROUND_ROBIN
      load_assignment:
        cluster_name: backend_cluster
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address: { address: backend, port_value: 8080 }
      health_checks:
        - timeout: 3s
          interval: 5s
          http_health_check:
            path: "/healthz"
      circuit_breakers:
        thresholds:
          - max_connections: 1024
            max_pending_requests: 1024
            max_retries: 3
```

### Comparison Summary

| Feature | nginx | HAProxy | Envoy |
|---|---|---|---|
| Configuration | Static files, reload | Static files, reload | API-driven (xDS), hot reload |
| HTTP/2 upstream | Limited | Yes | Full support |
| gRPC | Basic | Limited | First-class |
| Observability | Access logs, basic stats | Detailed stats page | Prometheus, tracing, rich stats |
| Service mesh | Not typical | Not typical | The standard sidecar |
| Learning curve | Low | Medium | High |

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

### Conceptual Questions

**Q: You're seeing intermittent 502 errors from your load balancer. Walk me through your debugging process.**

A: Start with the LB health check logs -- are backends being marked unhealthy? Check backend connection limits (max connections reached?). Examine backend response times -- are they exceeding the LB's `proxy_read_timeout`? Look at the LB's connection pool -- are connections to backends being reused or re-established? Check for TCP RST packets between LB and backends (network issues). Verify keep-alive settings match between LB and backends. A common cause is a race condition where the backend closes a keep-alive connection just as the LB sends a new request on it.

**Q: How would you design a global load balancing architecture for a service that needs sub-100ms latency worldwide?**

A: Layer the solution: GeoDNS or anycast routing at the DNS layer to direct users to the nearest region. An L4 load balancer (NLB/MetalLB) at each region for raw throughput. L7 load balancers (Envoy) behind that for content-based routing. CDN at the edge for static assets and cacheable API responses. For dynamic content, deploy the service in multiple regions with a replicated data layer (CockroachDB, DynamoDB Global Tables). Use latency-based routing in DNS rather than pure geo -- sometimes a geographically farther region has lower latency due to network topology.

**Q: Explain why consistent hashing is important for cache-aware load balancing. What happens when you add a node?**

A: Without consistent hashing, adding a node changes the modulo calculation (hash % N vs hash % (N+1)), remapping nearly all keys. With consistent hashing, the new node takes ownership of a portion of the ring, remapping only ~1/N of keys. This means cache hit rates remain high during scaling events. Virtual nodes ensure uniform distribution on the ring, preventing hot spots.

### System Design Scenarios

**Q: Design the load balancing layer for a real-time multiplayer game.**

A: Use L4 load balancing (UDP) for game state updates -- low latency is critical. Consistent hashing on game session ID to ensure all players in a session hit the same server. WebSocket connections for lobby/chat use L7 with sticky sessions. Health checks must be aggressive (1-2s interval) since game servers under load can degrade quickly. Circuit breakers on matchmaking service calls with graceful fallback (queue players rather than error). DNS-based routing for region selection at connection time.

**Q: Your microservice architecture has 50 services. A single service failure is cascading across the system. How do you prevent this?**

A: Implement circuit breakers on all inter-service calls with per-downstream bulkheads (isolated connection pools). Set retry budgets (max 20% retries) to prevent retry storms. Add timeouts on every outbound call -- no unbounded waits. Implement graceful degradation: if a recommendation service is down, show default recommendations rather than failing the entire page. Consider a service mesh (Istio) if the team has the operational maturity -- it externalizes these patterns. Monitor with RED metrics (Rate, Errors, Duration) per service pair to identify cascades early.

**Q: When would you choose gRPC over REST for a new microservice?**

A: Choose gRPC when the service is internal (no browser clients), requires streaming (bidirectional updates), needs high throughput with low latency (binary serialization matters), or operates in a polyglot environment where code-generated clients reduce integration bugs. Choose REST when the API is public-facing, needs to be browsable/debuggable with standard tools, benefits from HTTP caching, or the team is not experienced with protobuf/gRPC tooling. In practice, many organizations use gRPC for internal service-to-service and REST/GraphQL at the edge.

### Rapid-Fire

1. **What is the difference between active and passive health checks?** Active: LB probes backends. Passive: LB monitors real traffic responses.

2. **What is a retry storm?** Cascading retries that amplify load on a failing service, turning a partial failure into a total outage.

3. **Why use exponential backoff with jitter?** Exponential backoff reduces load over time. Jitter decorrelates retries to prevent thundering herd.

4. **What is the BFF pattern?** Backend for Frontend -- a dedicated API layer per client type (mobile, web, partner) to serve optimized data shapes.

5. **What does the half-open state in a circuit breaker do?** Allows a limited number of probe requests through to test if the downstream has recovered.

6. **Why might DNS failover be insufficient for high-availability?** DNS TTL means clients may cache stale records pointing to failed endpoints for seconds to minutes after failure.

7. **What is the bulkhead pattern?** Isolating failure domains by giving each downstream its own resource pool, preventing one slow dependency from starving others.

8. **When is a service mesh overkill?** Small number of services, team lacks K8s expertise, latency overhead is unacceptable, or simpler alternatives (library-based) suffice.
