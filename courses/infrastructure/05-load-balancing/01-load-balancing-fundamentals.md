# Module 05: Load Balancing Fundamentals

## Overview

Load balancing sits at the intersection of reliability, performance, and scalability. At senior-level interviews, you are expected to reason about trade-offs across OSI layers, articulate why a particular algorithm fits a workload, and design resilient systems that degrade gracefully.

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

### L4 vs L7 Comparison

| Aspect | L4 (Transport) | L7 (Application) |
|---|---|---|
| Operates on | TCP/UDP segments | HTTP requests |
| Inspects content | No | Yes (headers, URI, cookies, body) |
| TLS | Passthrough or terminate | Terminates |
| Routing granularity | IP + port | Path, host, header, cookie |
| Performance | Higher throughput, lower latency | More CPU per request |
| Connection awareness | Per TCP connection | Per HTTP request |
| Use case | Databases, non-HTTP, raw speed | Web apps, APIs, content routing |
| Examples | AWS NLB, MetalLB, LVS | AWS ALB, nginx, Envoy, HAProxy |

**Key interview insight**: The common trap is treating L4 and L7 as mutually exclusive. In production architectures, they are **layered**: an L4 balancer (e.g., AWS NLB, MetalLB) distributes traffic across a fleet of L7 balancers (e.g., Envoy, nginx). This gives you both raw throughput at the edge and intelligent routing at the application layer.

**Rule of thumb:** Use L4 in front of L7. Use L7 when you need to understand the request.

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

**Consistent hashing remapping formula:** Adding 1 node to N remaps ~1/N keys.

### Algorithm Selection Guide

```
Start
  |
  +-- Are backends identical capacity?
  |     |
  |     +-- YES: Are request costs uniform?
  |     |         |
  |     |         +-- YES --> Round Robin
  |     |         |
  |     |         +-- NO --> Least Connections
  |     |
  |     +-- NO --> Weighted Round Robin / Weighted Least Connections
  |
  +-- Need session affinity?
  |     |
  |     +-- Can use cookies? --> Cookie-based sticky (L7)
  |     |
  |     +-- No cookies? --> IP Hash
  |
  +-- Cache-aware routing needed?
        |
        +-- YES --> Consistent Hashing (with virtual nodes)
```

| Scenario | Recommended Algorithm |
|---|---|
| Homogeneous backends, uniform requests | Round Robin |
| Mixed instance sizes | Weighted Round Robin |
| Variable request durations (long-polling, WebSockets) | Least Connections |
| Need session affinity, no cookies | IP Hash |
| Cache-warm routing, minimal remapping on scale | Consistent Hashing |

| Algorithm | Pros | Cons |
|---|---|---|
| Round Robin | Simple, no state | Ignores capacity and load |
| Weighted RR | Handles mixed capacity | Static weights, no runtime adaptation |
| Least Connections | Adapts to real load | Requires connection tracking |
| IP Hash | Deterministic affinity | Uneven if traffic from few IPs |
| Consistent Hashing | Minimal remapping on change | More complex, needs virtual nodes |

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

## Formulas to Remember

- **Consistent hashing remapping:** Adding 1 node to N remaps ~1/N keys.
- **Backoff delay:** `min(base * 2^attempt + jitter, max_delay)`
- **Retry amplification:** actual load = `1 + failure_rate * retries` (without budget).
- **Connection pool sizing:** `pool_size >= peak_rps * avg_response_time_seconds`
- **WebSocket capacity:** ~10K-100K connections per server.
