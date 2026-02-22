# Module 05 Cheat Sheet: Load Balancing & Networking

---

## L4 vs L7 Comparison

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

**Rule of thumb:** Use L4 in front of L7. Use L7 when you need to understand the request.

---

## Load Balancing Algorithm Decision Guide

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

| Algorithm | Pros | Cons |
|---|---|---|
| Round Robin | Simple, no state | Ignores capacity and load |
| Weighted RR | Handles mixed capacity | Static weights, no runtime adaptation |
| Least Connections | Adapts to real load | Requires connection tracking |
| IP Hash | Deterministic affinity | Uneven if traffic from few IPs |
| Consistent Hashing | Minimal remapping on change | More complex, needs virtual nodes |

---

## Circuit Breaker States

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

---

## Retry Strategy Template

```
delay = min(base * 2^attempt, max_delay)
sleep(random(0, delay))   # full jitter
```

**Retryable:** 5xx, 429 (with Retry-After), connection refused, timeout (if idempotent).
**Non-retryable:** 4xx (except 429), auth failures, validation errors.
**Retry budget:** max 20% of total requests can be retries.

---

## DNS Record Types

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

## Service Mesh Components

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
**Use when:** 10+ services, mTLS needed, complex traffic management.
**Skip when:** <10 services, team lacks K8s depth, tight latency budgets.

---

## HTTP/1.1 vs HTTP/2 vs HTTP/3 Comparison

| Feature | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Year | 1997 | 2015 | 2022 |
| Transport | TCP | TCP | QUIC (UDP) |
| Connections | Multiple (6-8 per host) | Single (multiplexed) | Single (multiplexed) |
| Head-of-line blocking | Yes (app + TCP) | TCP only | None |
| Header format | Text, repeated | Binary, HPACK compressed | Binary, QPACK compressed |
| Server push | No | Yes (deprecated in practice) | Yes |
| 0-RTT | No | No (TCP limitation) | Yes (QUIC) |
| Connection migration | No | No | Yes (connection ID) |
| Required encryption | No | Effectively yes | Yes (always) |

---

## Quick Reference: Reverse Proxy Config Patterns

### nginx -- Upstream with health check
```nginx
upstream backend {
    least_conn;
    server 10.0.0.1:8080 max_fails=3 fail_timeout=30s;
    server 10.0.0.2:8080 max_fails=3 fail_timeout=30s;
}
```

### HAProxy -- Backend with active health check
```haproxy
backend app
    balance leastconn
    option httpchk GET /healthz
    http-check expect status 200
    server s1 10.0.0.1:8080 check inter 5s fall 3 rise 2
```

### Envoy -- Retry policy
```yaml
retry_policy:
  retry_on: "5xx,connect-failure,refused-stream"
  num_retries: 3
  per_try_timeout: 2s
  retry_back_off:
    base_interval: 0.1s
    max_interval: 1s
```

---

## Formulas to Remember

- **Consistent hashing remapping:** Adding 1 node to N remaps ~1/N keys.
- **Backoff delay:** `min(base * 2^attempt + jitter, max_delay)`
- **Retry amplification:** actual load = `1 + failure_rate * retries` (without budget).
- **Connection pool sizing:** `pool_size >= peak_rps * avg_response_time_seconds`
- **WebSocket capacity:** ~10K-100K connections per server.
