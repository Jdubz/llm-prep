# Module 05 Deep Dive: Networking Internals for Interviews

## Overview

Senior infrastructure interviews frequently probe your understanding of what happens beneath the abstraction layers. This deep dive covers the networking fundamentals that underpin every load balancer, proxy, and service mesh -- the knowledge that separates operators from architects.

---

## Table of Contents

1. [TCP/IP Deep Dive](#tcpip-deep-dive)
2. [HTTP/2 and HTTP/3](#http2-and-http3)
3. [TLS Handshake and Performance](#tls-handshake-and-performance)
4. [CDN Architecture](#cdn-architecture)
5. [WebSocket Load Balancing Challenges](#websocket-load-balancing-challenges)
6. [Global Load Balancing Architectures](#global-load-balancing-architectures)

---

## TCP/IP Deep Dive

### The Three-Way Handshake

Every TCP connection begins with the handshake. Understanding it is essential for reasoning about connection latency and load balancer behavior.

```
Client                    Server
  |                         |
  |------- SYN ----------->|  (1) Client sends SYN, seq=x
  |                         |
  |<------ SYN-ACK --------|  (2) Server sends SYN-ACK, seq=y, ack=x+1
  |                         |
  |------- ACK ----------->|  (3) Client sends ACK, ack=y+1
  |                         |
  |===== Connection Open ===|
  |                         |
  | (data can flow)         |
```

**Latency implication:** The handshake requires 1.5 round trips (the client can send data on the third packet with TCP Fast Open, reducing this to 1 RTT for repeat connections).

**SYN floods:** An attacker sends SYN packets without completing the handshake, filling the server's SYN backlog. Mitigations: SYN cookies (encode connection state in the SYN-ACK sequence number, eliminating the need to store state), increasing the SYN backlog size, rate limiting SYN packets.

**Interview insight:** When an L4 load balancer uses DSR (Direct Server Return), the SYN goes through the LB but the SYN-ACK goes directly from the backend to the client. This means the LB only sees half the connection, reducing its load but making health checking and connection tracking harder.

### Connection Pooling

Creating TCP connections is expensive (handshake latency + TLS overhead). Connection pooling reuses established connections across multiple requests.

**How it works:**

1. Application requests a connection to a backend.
2. The pool checks for an idle, healthy connection.
3. If available, the connection is leased to the application.
4. After the request completes, the connection is returned to the pool (not closed).

**Key parameters:**

- **Max pool size:** Upper limit on connections to a backend. Too high: resource exhaustion. Too low: connection starvation under load.
- **Idle timeout:** How long an unused connection stays in the pool before being closed. Must be shorter than the server's keep-alive timeout to avoid sending requests on a server-closed connection.
- **Max connection lifetime:** Force-close connections after a duration to prevent routing to decommissioned backends (important during rolling deployments).

```
Without pooling:         With pooling:
Request 1: [SYN/ACK/TLS/Request/Response/FIN]   Request 1: [SYN/ACK/TLS/Request/Response]
Request 2: [SYN/ACK/TLS/Request/Response/FIN]   Request 2: [          Request/Response]
Request 3: [SYN/ACK/TLS/Request/Response/FIN]   Request 3: [          Request/Response]

Latency saved per request: ~3-5ms (handshake + TLS)
```

### Keep-Alive

HTTP/1.1 uses `Connection: keep-alive` (default) to reuse TCP connections across multiple HTTP requests. The server processes requests sequentially on the same connection (head-of-line blocking).

**Gotcha -- the keep-alive race condition:** If the server closes the connection (idle timeout) at the same moment the client sends a new request, the client gets a TCP RST. This is a common source of intermittent 502 errors behind load balancers. The fix: set the LB's keep-alive timeout shorter than the backend's, so the LB always closes idle connections first.

```
Safe configuration:
  Backend keep-alive timeout:  65s
  LB keep-alive timeout:       60s  (LB closes first, no race condition)

Unsafe configuration:
  Backend keep-alive timeout:  60s
  LB keep-alive timeout:       65s  (Backend may close while LB reuses connection)
```

### Nagle's Algorithm

Nagle's algorithm buffers small TCP segments, combining them into larger packets to reduce overhead. It delays sending until either:
- The buffer reaches MSS (Maximum Segment Size, typically ~1460 bytes), or
- An ACK is received for the previous segment.

**Problem:** Combined with TCP Delayed ACK (which delays ACKs for up to 40ms hoping to piggyback on response data), Nagle's algorithm can introduce 40ms latency spikes on small writes.

**Solution:** Disable Nagle's for latency-sensitive applications:
- `TCP_NODELAY` socket option.
- Most HTTP servers and proxies disable it by default.

**When to keep Nagle enabled:** Bulk data transfer where throughput matters more than latency (file uploads, database replication).

---

## HTTP/2 and HTTP/3

### HTTP/2: Multiplexing

HTTP/1.1's fundamental limitation is head-of-line blocking: one slow response blocks all subsequent responses on the same connection. Browsers work around this by opening 6-8 parallel connections, which wastes resources.

HTTP/2 solves this with **streams**: multiple request/response pairs multiplexed over a single TCP connection.

```
HTTP/1.1 (6 connections):
Conn 1: [===Request A===][===Request D===]
Conn 2: [===Request B===][===Request E===]
Conn 3: [===Request C===][===Request F===]

HTTP/2 (1 connection, multiplexed):
Stream 1: [=A=]     [=D=]
Stream 3:    [==B==]
Stream 5: [=C=]  [==E==]
Stream 7:      [=F=]
```

**Key features:**

- **Header compression (HPACK):** Headers are encoded using a static/dynamic table, reducing redundant header bytes. HTTP headers like `Content-Type`, `Accept`, and cookies are sent once and referenced by index in subsequent requests.
- **Server push:** The server proactively sends resources it predicts the client will need (e.g., pushing CSS when HTML is requested). In practice, this feature saw limited adoption and has been deprecated in Chrome.
- **Stream prioritization:** Clients can indicate priority and dependency between streams. Servers can use this to schedule responses optimally.
- **Flow control:** Per-stream and per-connection flow control prevents a fast sender from overwhelming a slow receiver.

**Limitation -- TCP head-of-line blocking:** While HTTP/2 eliminates application-level HOL blocking, TCP's ordered byte stream means a single lost packet blocks all streams until retransmission. This is the motivation for HTTP/3.

### HTTP/3: QUIC

HTTP/3 replaces TCP with QUIC (Quick UDP Internet Connections), a transport protocol built on UDP.

**Why QUIC?**

1. **No TCP HOL blocking:** Each QUIC stream is independently flow-controlled. A lost packet on stream 1 does not block stream 2.
2. **0-RTT connection establishment:** For repeat connections, QUIC can send data on the first packet (TLS 1.3 early data built into the transport). New connections complete in 1 RTT (vs 2-3 RTT for TCP+TLS).
3. **Connection migration:** QUIC connections are identified by a connection ID, not the 4-tuple (src IP, src port, dst IP, dst port). When a mobile device switches from WiFi to cellular, the connection survives.
4. **Integrated encryption:** TLS 1.3 is mandatory and built into the transport, reducing handshake round trips.

```
TCP + TLS 1.3 (new connection):
Client                    Server
  |--- SYN --------------->|  RTT 1 (TCP handshake)
  |<-- SYN-ACK ------------|
  |--- ACK + ClientHello ->|  RTT 2 (TLS handshake)
  |<-- ServerHello --------|
  |--- Data -------------->|  RTT 3 (first data)

QUIC (new connection):
Client                    Server
  |--- ClientHello ------->|  RTT 1 (combined transport + TLS)
  |<-- ServerHello --------|
  |--- Data -------------->|  RTT 2 (first data)

QUIC (repeat connection, 0-RTT):
Client                    Server
  |--- Data (0-RTT) ------>|  RTT 0 (immediate data!)
  |<-- Response ------------|
```

**Challenges with QUIC:**

- Some firewalls and middleboxes block or throttle UDP traffic.
- Debugging is harder -- existing TCP tools (tcpdump, Wireshark) have limited QUIC support (improving).
- CPU overhead of QUIC is higher than kernel-optimized TCP stacks (QUIC runs in userspace).
- Not all load balancers support QUIC natively.

### HTTP Version Comparison

| Feature | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transport | TCP | TCP | QUIC (UDP) |
| Multiplexing | No (multiple connections) | Yes | Yes |
| HOL blocking | Application + TCP | TCP only | None |
| Header compression | None | HPACK | QPACK |
| Connection setup | 2-3 RTT | 2-3 RTT | 1 RTT (0-RTT repeat) |
| Connection migration | No | No | Yes |
| Encryption | Optional (TLS) | Requires TLS in practice | Always encrypted |

---

## TLS Handshake and Performance

### TLS 1.3 Handshake

TLS 1.3 reduced the handshake from 2 RTT (TLS 1.2) to 1 RTT by combining key exchange and authentication into fewer messages.

```
TLS 1.3 Full Handshake:
Client                         Server
  |--- ClientHello + KeyShare ->|  (1) Client sends supported ciphers + key material
  |<-- ServerHello + KeyShare --|  (2) Server selects cipher + sends key material
  |<-- {EncryptedExtensions}  --|      (everything after this is encrypted)
  |<-- {Certificate}         --|
  |<-- {CertificateVerify}   --|
  |<-- {Finished}            --|
  |--- {Finished}            ->|  (3) Client confirms
  |=== Application Data ======|
```

### Performance Optimizations

**Session resumption (PSK):** After the first handshake, the server issues a session ticket. On subsequent connections, the client presents this ticket, enabling 0-RTT resumption (data sent with the ClientHello).

**0-RTT security caveat:** 0-RTT data is replayable. An attacker can capture and replay the 0-RTT data. Only use 0-RTT for idempotent operations (GET requests). Non-idempotent requests must wait for the full handshake.

**OCSP Stapling:** Instead of the client checking certificate revocation with the CA (adding latency), the server periodically fetches the OCSP response and "staples" it to the TLS handshake. Eliminates a round trip to the CA.

**Certificate chain optimization:** Serve the full certificate chain but not the root CA (which the client already has). Incomplete chains cause validation failures; overly long chains add latency.

**Key takeaway for interviews:** TLS adds 1 RTT for new connections (TLS 1.3), 0 RTT for resumed connections. The absolute latency depends on the RTT between client and server, making TLS termination location critical. Terminate TLS at the edge (CDN PoPs) to minimize RTT.

---

## CDN Architecture

### Points of Presence (PoPs)

CDNs deploy edge servers in hundreds of locations worldwide. Each location is a PoP, typically colocated in internet exchange points (IXPs) for low-latency peering.

```
                    [Origin Server]
                         |
                   [Origin Shield]  (intermediate cache layer)
                    /    |     \
                   /     |      \
              [PoP 1]  [PoP 2]  [PoP 3]
              /   \      |      /    \
          [Users] [Users] [Users] [Users] [Users]
```

### Origin Shield

An intermediate caching layer between edge PoPs and the origin server. Without it, a cache miss at any PoP results in a request to the origin. With N PoPs, a popular-but-expired object generates N origin requests.

Origin shield consolidates these: all PoPs fetch from the shield, which fetches once from the origin.

**Trade-off:** Adds one more hop for cache misses, but dramatically reduces origin load.

### Anycast

Multiple PoPs advertise the same IP address via BGP. Routers direct packets to the nearest PoP based on network topology (fewest AS hops, not geographic distance).

**How it works for CDNs:**

1. CDN PoPs in Tokyo, Frankfurt, and Virginia all announce `198.51.100.1`.
2. A user in Osaka sends a packet to `198.51.100.1`.
3. BGP routing delivers the packet to the Tokyo PoP (fewest hops).

**Advantage:** No DNS-based routing needed. Works at the network layer, providing automatic failover -- if a PoP goes down, BGP withdraws its route and traffic is automatically rerouted.

**Challenge with TCP:** If the BGP route changes mid-connection (route flap), TCP connections break because packets arrive at a different PoP that has no connection state. Anycast works best for short-lived or stateless protocols (DNS over UDP is the classic use case). For long-lived TCP, CDNs use techniques like connection pinning or QUIC's connection migration.

### Cache Hierarchy and Invalidation

**Cache keys:** Typically `URL + Vary headers`. The `Vary` header tells the CDN which request headers affect the response (e.g., `Vary: Accept-Encoding` means gzip and brotli responses are cached separately).

**Invalidation strategies:**
- **TTL-based:** Content expires after the `Cache-Control: max-age` duration. Simple but imprecise.
- **Purge:** Explicitly invalidate specific URLs or patterns. CDN APIs support this but purge propagation across all PoPs takes seconds.
- **Stale-while-revalidate:** Serve stale content while asynchronously revalidating with the origin. Provides consistent latency at the cost of briefly stale data.

---

## WebSocket Load Balancing Challenges

### The Statefulness Problem

WebSocket connections are long-lived and stateful. This creates several challenges for load balancing:

**Session affinity:** Once a WebSocket connection is established, all frames must go to the same backend. L7 load balancers must maintain sticky sessions.

**Uneven distribution:** Some WebSocket connections last seconds, others last hours. Least-connections algorithms help, but backends with many long-lived connections accumulate state.

**Health check interaction:** If a backend is marked unhealthy, existing WebSocket connections should be gracefully drained (send close frame, allow reconnection to a healthy backend) rather than abruptly terminated.

### Connection Draining

During deployments or backend removal:

1. Mark the backend as "draining" (stop sending new connections).
2. Existing WebSocket connections continue until they naturally close or a drain timeout expires.
3. After drain timeout, send WebSocket close frames (code 1001, "going away").
4. Clients should implement reconnection with backoff.

```
Timeline: Graceful drain

t=0    Backend marked draining. New connections go elsewhere.
t=0-30s  Existing connections continue.
t=30s  Drain timeout. Server sends Close frames.
t=31s  Clients reconnect to healthy backends.
```

### Scaling WebSocket Services

**Horizontal scaling with pub/sub:** When clients connected to different backends need to communicate (e.g., chat rooms), use a pub/sub system (Redis Pub/Sub, NATS, Kafka) as a backplane.

```
[Client A] <--ws--> [Backend 1] <--pub/sub--> [Backend 2] <--ws--> [Client B]
                          \                      /
                           \                    /
                            [Redis Pub/Sub]
```

**Connection limits:** Each WebSocket connection consumes a file descriptor and memory. A single server typically handles 10K-100K concurrent connections depending on the workload. Plan capacity accordingly.

**Proxy buffering:** Most reverse proxies buffer HTTP responses. For WebSocket, buffering must be disabled:

```nginx
location /ws {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600s;  # Don't timeout long-lived connections
    proxy_buffering off;
}
```

---

## Global Load Balancing Architectures

### Architecture Tiers

A production global load balancing architecture typically has four tiers:

```
Tier 1: DNS (GeoDNS / Latency-based)
  |
  v
Tier 2: Edge / CDN (Anycast, TLS termination)
  |
  v
Tier 3: Regional L4 LB (NLB, MetalLB)
  |
  v
Tier 4: Application L7 LB (Envoy, nginx)
  |
  v
[Backend Services]
```

### Multi-Region Active-Active

All regions serve traffic simultaneously. This requires:

- **Data replication:** Synchronous replication across regions is impractical (latency). Use eventual consistency (CRDTs, last-writer-wins) or partition data by region.
- **Conflict resolution:** When the same data is written in two regions simultaneously, the system needs a deterministic resolution strategy.
- **Session management:** Sessions must be accessible from any region (distributed session store like Redis with cross-region replication) or stateless (JWT tokens).

### Multi-Region Active-Passive

One region serves all traffic. A standby region is ready to take over.

**Failover process:**
1. Health checks detect primary region failure.
2. DNS records are updated to point to the secondary region.
3. Secondary region begins serving traffic.

**Challenges:**
- Cold cache in the secondary region (plan for thundering herd on failover).
- Database replication lag means the secondary may serve slightly stale data.
- DNS TTL delays mean some clients continue hitting the failed primary.
- Testing failover is critical but often neglected -- run game day exercises regularly.

### Traffic Splitting Across Regions

For canary deployments or migration, split traffic across regions:

```
DNS Weighted Routing:
  api.example.com -> us-east-1 (90%)
  api.example.com -> eu-west-1 (10%)
```

**Progressive rollout:**
1. Deploy new version to eu-west-1.
2. Route 1% of traffic to eu-west-1 via weighted DNS.
3. Monitor error rates and latency.
4. Gradually increase to 10%, 50%, 100%.
5. Deploy to us-east-1, reverse the weights.

### Interview Scenario: Designing Global Load Balancing

**Prompt:** Design a load balancing architecture for a global e-commerce platform with 10M daily active users across NA, EU, and APAC.

**Approach:**

1. **DNS layer:** Route 53 with latency-based routing. Three endpoints: us-east-1, eu-west-1, ap-northeast-1.
2. **CDN:** CloudFront / Cloudflare for static assets, product images, and cacheable API responses (product catalog).
3. **Regional entry:** NLB per region for TCP load balancing to the L7 tier.
4. **L7 routing:** Envoy fleet for path-based routing, rate limiting, and auth.
5. **Data layer:** DynamoDB Global Tables for user sessions and carts (eventual consistency is acceptable). Primary-secondary PostgreSQL for order data (strong consistency, writes go to primary region).
6. **Failover:** DNS health checks with 30s TTL. Automated failover with manual approval for the database layer.

**Key trade-offs to discuss:**
- Latency vs consistency for the data layer.
- Cost of running active-active in three regions vs active-passive.
- Cold cache warming strategy for failover regions.
- How to handle in-flight transactions during failover.
