# Module 05 Cheat Sheet: Common Technical Questions

> Quick-reference tables for interview prep. Print this out or keep it on a second monitor.

---

## Data Structure Selection Guide

| Problem Characteristic | Data Structure | Time Complexity |
|----------------------|----------------|-----------------|
| Key-value lookup | Hash Map | O(1) avg |
| Sorted order needed | Balanced BST / TreeMap | O(log n) |
| Find min/max repeatedly | Heap / Priority Queue | O(1) peek, O(log n) extract |
| Prefix search / autocomplete | Trie | O(m) where m = key length |
| Relationships / dependencies | Graph (adjacency list) | Varies by algorithm |
| Membership test (approx OK) | Bloom Filter | O(k) where k = hash count |
| Range queries | Segment Tree / BIT | O(log n) |
| FIFO processing | Queue | O(1) enqueue/dequeue |
| LIFO / undo / matching | Stack | O(1) push/pop |
| Sorted with fast insert | Skip List | O(log n) avg |
| Disk-optimized sorted data | B+ Tree | O(log n) |
| Write-optimized storage | LSM Tree | O(1) write (amortized) |

---

## Big-O Cheat Sheet

### Time Complexities

| Complexity | Name | Common Operations |
|-----------|------|-------------------|
| O(1) | Constant | Hash lookup, array index, stack push/pop |
| O(log n) | Logarithmic | Binary search, balanced BST ops, heap insert |
| O(n) | Linear | Array scan, linked list traversal, single pass |
| O(n log n) | Linearithmic | Merge sort, heap sort, Tim sort |
| O(n^2) | Quadratic | Nested loops, bubble/insertion/selection sort |
| O(2^n) | Exponential | Subsets, naive recursion |
| O(n!) | Factorial | Permutations, brute-force TSP |

### Sorting Algorithm Summary

| Algorithm | Best | Average | Worst | Space | Stable |
|-----------|------|---------|-------|-------|--------|
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Quick Sort | O(n log n) | O(n log n) | O(n^2) | O(log n) | No |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No |
| Tim Sort | O(n) | O(n log n) | O(n log n) | O(n) | Yes |
| Counting Sort | O(n+k) | O(n+k) | O(n+k) | O(k) | Yes |

---

## Networking Layers (Simplified)

| Layer | Protocol Examples | Key Concepts |
|-------|------------------|--------------|
| Application (L7) | HTTP, DNS, WebSocket, gRPC | Request/response, serialization |
| Transport (L4) | TCP, UDP, QUIC | Ports, reliability, flow control |
| Network (L3) | IP, ICMP | Routing, addressing, fragmentation |
| Link (L2) | Ethernet, Wi-Fi | MAC addresses, frames, switches |
| Physical (L1) | Cables, radio | Bits on the wire |

### TCP vs UDP Quick Reference

| Feature | TCP | UDP |
|---------|-----|-----|
| Connection | Yes (3-way handshake) | No |
| Reliability | Guaranteed delivery + ordering | Best-effort |
| Speed | Slower (overhead) | Faster |
| Use case | Web, APIs, file transfer | Video, gaming, DNS |

---

## OWASP Top 10 Quick Reference

| # | Vulnerability | Prevention |
|---|--------------|------------|
| 1 | Broken Access Control | Server-side checks, deny by default, RBAC |
| 2 | Cryptographic Failures | TLS everywhere, AES-256, proper key management |
| 3 | Injection | Parameterized queries, input validation, ORMs |
| 4 | Insecure Design | Threat modeling, secure design patterns |
| 5 | Security Misconfiguration | Hardened defaults, automated config audits |
| 6 | Vulnerable Components | Dependency scanning, regular updates, SBOM |
| 7 | Auth Failures | MFA, rate limiting, secure session management |
| 8 | Data Integrity Failures | Code signing, verified CI/CD pipelines |
| 9 | Logging Failures | Centralized logging, alerting, audit trails |
| 10 | SSRF | Allowlist URLs, block internal IPs, network segmentation |

---

## Distributed Systems Concepts

| Concept | One-Line Definition | Key Tradeoff |
|---------|-------------------|--------------|
| CAP Theorem | Cannot have C+A+P simultaneously | CP vs AP during partitions |
| Strong Consistency | Reads always see latest write | Higher latency |
| Eventual Consistency | Replicas converge over time | Stale reads possible |
| Consensus (Raft) | Nodes agree on values via leader + majority | Availability during leader election |
| Vector Clocks | Track causal ordering across nodes | Size grows with node count |
| Consistent Hashing | Minimize remapping on node change | Need virtual nodes for balance |
| CRDTs | Auto-mergeable data structures | Limited operation semantics |
| Gossip Protocol | Epidemic-style state propagation | Eventually consistent only |
| Distributed Lock | Coordinate cross-node resource access | Requires fencing tokens for safety |
| Two-Phase Commit | Atomic transactions across nodes | Blocking if coordinator fails |

---

## "What Happens When You Type a URL" Framework

| Step | What Happens | Key Detail to Mention |
|------|-------------|----------------------|
| 1. URL Parse | Extract scheme, host, path | Browser may add HSTS upgrade |
| 2. DNS Lookup | Resolve hostname to IP | Recursive resolver, caching, TTL |
| 3. TCP Connect | 3-way handshake (SYN, SYN-ACK, ACK) | ~1 RTT |
| 4. TLS Handshake | Key exchange, cert verification | TLS 1.3 = 1 RTT (0-RTT resumption) |
| 5. HTTP Request | Send method, headers, body | HTTP/2 multiplexing, compression |
| 6. Server Process | Load balancer, app server, DB | Mention caching layers |
| 7. HTTP Response | Status code, headers, body | Content-Encoding, Cache-Control |
| 8. Render | Parse HTML, build DOM, CSSOM, paint | Critical rendering path |
| 9. Cleanup | Keep-alive, connection pool | Connection reuse saves RTTs |

---

## Hashing vs Encryption Quick Reference

| | Hashing | Encryption |
|--|---------|------------|
| Direction | One-way | Two-way |
| Purpose | Verify integrity / store passwords | Protect confidentiality |
| Key needed | No (salt for passwords) | Yes |
| For passwords | bcrypt, argon2 (with salt) | NEVER encrypt passwords |
| For data | SHA-256 (integrity check) | AES-256 (at rest), TLS (in transit) |

---

## Concurrency Quick Reference

| Concept | Definition | Prevention/Solution |
|---------|-----------|-------------------|
| Race Condition | Outcome depends on execution timing | Mutexes, atomic operations |
| Deadlock | Circular wait for resources | Resource ordering, timeouts |
| Livelock | Threads actively retry but make no progress | Randomized backoff |
| Starvation | Thread never gets resource access | Fair locks, priority aging |
| Mutex | Binary lock with ownership | Use for critical sections |
| Semaphore | Counting lock, no ownership | Use for resource pools |
