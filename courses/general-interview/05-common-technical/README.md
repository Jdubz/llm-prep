# Module 05: Common Technical Questions (Language-Agnostic)

> A senior-level refresher. You know this material — the goal is to articulate it clearly under interview pressure.

---

## Table of Contents

1. [Data Structures Refresher](#data-structures-refresher)
2. [Big-O Analysis](#big-o-analysis)
3. [Concurrency Fundamentals](#concurrency-fundamentals)
4. [Networking](#networking)
5. [Operating Systems](#operating-systems)
6. [Security](#security)
7. [Distributed Systems Concepts](#distributed-systems-concepts)
8. [Interview Questions & Answers](#interview-questions--answers)

---

## Data Structures Refresher

You are not being asked to implement a red-black tree from scratch. You are being asked to **choose the right tool** and **explain why**. The interviewer wants to hear your decision framework.

### Decision Framework: "What Do I Need?"

| Need | Reach For | Why |
|------|-----------|-----|
| Fast key-value lookup | **Hash Map** | O(1) average get/put |
| Ordered data with fast lookup | **Balanced BST / TreeMap** | O(log n) with ordering |
| Priority access (min/max) | **Heap** | O(1) peek, O(log n) insert/extract |
| Relationships between entities | **Graph** | Models connections, dependencies |
| Prefix-based search | **Trie** | Autocomplete, spell check, IP routing |
| Range queries on sorted data | **Balanced BST / Segment Tree** | O(log n) range operations |
| FIFO processing | **Queue** | BFS, task scheduling |
| LIFO / undo semantics | **Stack** | DFS, expression parsing, undo |
| Membership testing (approximate) | **Bloom Filter** | Space-efficient, false positives OK |
| Sorted data with fast insert | **Skip List** | Probabilistic alternative to balanced BST |

### When Interviewers Ask About Data Structures

They want to hear:

1. **What** you would use
2. **Why** — the complexity tradeoffs
3. **When it breaks** — worst-case behavior, memory overhead
4. **Alternatives** you considered

**Example answer pattern:**
> "I'd use a hash map here because we need O(1) lookups by user ID. The tradeoff is O(n) space, but with our expected dataset size that's acceptable. If we needed ordering — say, iterating users by signup date — I'd switch to a TreeMap and accept O(log n) lookups."

### Hash Map — The Swiss Army Knife

- **Use when:** You need fast lookup/insert/delete by key
- **Complexity:** O(1) average, O(n) worst case (hash collisions)
- **Watch out for:** Hash function quality, load factor, resizing cost (amortized O(1))
- **Interview signal:** Mention collision resolution strategies (chaining vs open addressing) if asked to go deeper

### Trees — BST, AVL, Red-Black

- **Use when:** You need sorted order AND fast operations
- **Complexity:** O(log n) for balanced trees
- **Watch out for:** Unbalanced BSTs degrade to O(n) — that is why self-balancing variants exist
- **Interview signal:** Know that TreeMap/TreeSet in most languages use red-black trees internally

### Heap / Priority Queue

- **Use when:** Repeatedly accessing the min or max element
- **Complexity:** O(1) peek, O(log n) insert/extract
- **Watch out for:** Not efficient for arbitrary search — only the root is guaranteed
- **Interview signal:** "Top K" problems almost always want a heap

### Graph

- **Use when:** Modeling relationships, dependencies, networks
- **Representations:** Adjacency list (sparse) vs adjacency matrix (dense)
- **Interview signal:** Immediately clarify — directed vs undirected, weighted vs unweighted, cyclic vs acyclic

### Trie (Prefix Tree)

- **Use when:** Prefix matching, autocomplete, dictionary lookups
- **Complexity:** O(m) where m is key length — independent of dataset size
- **Interview signal:** Mention space optimization with compressed tries (radix trees)

---

## Big-O Analysis

You can do this in your sleep. The interview goal is to **communicate** complexity clearly and discuss tradeoffs.

### Common Complexities (Sorted)

| Complexity | Name | Example |
|-----------|------|---------|
| O(1) | Constant | Hash map lookup, array index access |
| O(log n) | Logarithmic | Binary search, balanced BST operations |
| O(n) | Linear | Array scan, single-pass algorithms |
| O(n log n) | Linearithmic | Merge sort, heap sort, efficient sorting |
| O(n^2) | Quadratic | Nested loops, naive sorting |
| O(2^n) | Exponential | Subset generation, naive recursive Fibonacci |
| O(n!) | Factorial | Permutation generation |

### Amortized Analysis — What It Means

Amortized analysis accounts for the fact that **expensive operations are rare**. The classic example:

- **Dynamic array (ArrayList) append:** Usually O(1), but O(n) when resizing
- **Amortized cost:** O(1) per insertion, because resizing doubles capacity and the next n insertions are O(1)

**How to explain it in an interview:**
> "The append is O(1) amortized. Most inserts are constant time, but occasionally we need to resize — copy all elements to a new array. Because we double the capacity each time, the cost of resizing is spread across all previous cheap inserts, averaging out to O(1) per operation."

### Space Complexity — Do Not Forget It

Interviewers notice when you only discuss time complexity. Always mention space:

- **In-place algorithms:** O(1) extra space (e.g., quicksort's partitioning)
- **Auxiliary data structures:** The hash map you built is O(n) space
- **Recursion:** O(d) stack space where d is max recursion depth
- **Trade-off framing:** "We can solve this in O(n^2) time with O(1) space, or O(n) time with O(n) space using a hash map. I'd choose the latter unless memory is constrained."

### How to Discuss Complexity in Interviews

1. **State the complexity** — "This is O(n log n) time, O(n) space"
2. **Justify it** — "The sort dominates at O(n log n), and we allocate an auxiliary array of size n"
3. **Discuss alternatives** — "We could avoid the sort with a hash map for O(n) time, but..."
4. **Mention constants when relevant** — "Both are O(n), but the hash map approach has higher constant factors due to hashing overhead"

---

## Concurrency Fundamentals

### Threads vs Processes

| Aspect | Process | Thread |
|--------|---------|--------|
| Memory | Own address space | Shared address space |
| Creation cost | Heavy (fork) | Lighter |
| Communication | IPC (pipes, sockets, shared memory) | Shared memory (direct) |
| Isolation | Strong — crash does not affect others | Weak — one thread can corrupt shared state |
| Use case | Isolation, security boundaries | Parallelism within an application |

### Deadlock — The Four Conditions (Coffman Conditions)

A deadlock requires **ALL FOUR** simultaneously:

1. **Mutual exclusion** — Resources cannot be shared
2. **Hold and wait** — Process holds one resource while waiting for another
3. **No preemption** — Resources cannot be forcibly taken away
4. **Circular wait** — A cycle of processes each waiting on the next

**Breaking any one condition prevents deadlock.** The most practical approach is usually **ordering resources** (break circular wait) or **using timeouts** (break hold and wait).

### Race Conditions

A race condition occurs when the outcome depends on the **timing of execution** of concurrent operations.

**Classic example:** Two threads incrementing a counter:
```
Thread A: read counter (0)
Thread B: read counter (0)
Thread A: write counter (1)
Thread B: write counter (1)  // Expected 2, got 1
```

**Prevention:** Synchronization primitives — mutexes, semaphores, atomic operations.

### Mutex vs Semaphore

| Aspect | Mutex | Semaphore |
|--------|-------|-----------|
| Purpose | Mutual exclusion (1 thread at a time) | Control access to N resources |
| Count | Binary (locked/unlocked) | Integer (0 to N) |
| Ownership | Only the locker can unlock | Any thread can signal |
| Use case | Protecting a critical section | Connection pool, rate limiting |

**Interview nuance:** A binary semaphore is NOT the same as a mutex. A mutex has ownership semantics — only the thread that locked it can unlock it. This prevents accidental unlocking by other threads.

### Async I/O Models

| Model | Description | Example |
|-------|-------------|---------|
| **Blocking I/O** | Thread waits until operation completes | Traditional socket reads |
| **Non-blocking I/O** | Returns immediately, caller polls for result | `O_NONBLOCK` flag |
| **I/O Multiplexing** | Monitor multiple FDs, block until any is ready | `select`, `poll`, `epoll` |
| **Async I/O** | Kernel notifies when operation completes | `io_uring`, IOCP on Windows |
| **Event loop** | Single-threaded, callback-based | Node.js, Python asyncio |

**Interview framing:**
> "Node.js uses a single-threaded event loop with non-blocking I/O. It handles concurrency through an event queue, not threads. This is efficient for I/O-bound workloads but problematic for CPU-bound tasks that block the event loop. That is why Node introduced worker threads."

---

## Networking

### HTTP/HTTPS and TLS

**What happens during a TLS handshake (TLS 1.3, simplified):**

1. **Client Hello** — Client sends supported cipher suites, a random value, and key share
2. **Server Hello** — Server selects cipher suite, sends its random value, key share, and certificate
3. **Client verifies** certificate against trusted CAs
4. **Both derive** the session key from the key exchange
5. **Encrypted communication** begins

**TLS 1.3 improvement over 1.2:** Reduced from 2 round trips to 1 (and 0-RTT for resumed connections).

### TCP vs UDP

| Aspect | TCP | UDP |
|--------|-----|-----|
| Connection | Connection-oriented (3-way handshake) | Connectionless |
| Reliability | Guaranteed delivery, ordering | Best-effort, no guarantees |
| Flow control | Yes (sliding window) | No |
| Congestion control | Yes (slow start, congestion avoidance) | No |
| Overhead | Higher (headers, state) | Lower |
| Use case | Web, file transfer, email | Video streaming, gaming, DNS |

**Interview nuance:** "TCP guarantees delivery" means it retransmits lost packets and delivers them in order. It does NOT guarantee the connection stays alive — that is the application's responsibility (heartbeats, keepalives).

### WebSockets

- **Why:** HTTP is request-response. WebSockets provide **full-duplex, persistent connections**.
- **Handshake:** Starts as HTTP, upgrades via `Upgrade: websocket` header
- **Use cases:** Real-time chat, live dashboards, collaborative editing, gaming
- **Alternative:** Server-Sent Events (SSE) for unidirectional server-to-client push

### DNS Resolution

1. Browser checks its **cache**
2. OS checks its **cache** (and `/etc/hosts`)
3. Query goes to **recursive resolver** (usually ISP or 8.8.8.8)
4. Resolver queries **root nameservers** (`.`)
5. Root directs to **TLD nameservers** (`.com`)
6. TLD directs to **authoritative nameservers** (for `example.com`)
7. Authoritative server returns the **IP address**
8. Response is **cached** at each level with TTL

### What Happens When You Type a URL

This is one of the most common senior interview questions. Cover these layers:

1. **URL parsing** — scheme, host, port, path, query
2. **DNS resolution** — as above
3. **TCP connection** — 3-way handshake (SYN, SYN-ACK, ACK)
4. **TLS handshake** — if HTTPS
5. **HTTP request** — method, headers, body
6. **Server processing** — load balancer, application server, database queries
7. **HTTP response** — status code, headers, body
8. **Rendering** — HTML parsing, DOM construction, CSSOM, render tree, layout, paint
9. **Connection management** — keep-alive, connection pooling

**Depth signal:** Mention HTTP/2 multiplexing, content encoding (gzip/brotli), CDN edge caching, browser preconnect hints.

---

## Operating Systems

### Processes vs Threads (Deeper)

- **Process:** Independent execution unit with its own address space, file descriptors, and signal handlers. Created via `fork()` (UNIX) which copies the address space (copy-on-write).
- **Thread:** Execution unit within a process sharing the same address space. Created via `pthread_create()` or language-level abstractions.
- **User-space threads (green threads):** Managed by the runtime, not the OS. Cheaper to create but cannot run in parallel on multiple cores without OS thread mapping. Examples: Go goroutines (M:N threading), Java virtual threads.

### Virtual Memory

- **What:** Each process sees a contiguous address space, mapped to physical memory (or disk) by the OS via **page tables**
- **Why:** Isolation between processes, ability to use more memory than physical RAM, memory-mapped files
- **Page size:** Typically 4KB; huge pages (2MB/1GB) reduce TLB misses for large workloads
- **TLB (Translation Lookaside Buffer):** CPU cache for page table entries — critical for performance

### Page Faults

- **Minor page fault:** Page is in memory but not mapped in the process's page table (e.g., shared library already loaded). Handled by updating the page table — no disk I/O.
- **Major page fault:** Page is not in memory, must be loaded from disk. This is **expensive** (milliseconds vs nanoseconds).
- **Thrashing:** When the system spends more time handling page faults than executing code. Caused by working set exceeding physical memory.

### File Descriptors

- Integer handles to open files, sockets, pipes, and other I/O resources
- Per-process table, with entries 0 (stdin), 1 (stdout), 2 (stderr) reserved
- **Limits matter:** Default per-process limit is often 1024 — servers handling many connections need to raise this (`ulimit -n`)
- **Leaking FDs** is a common bug — forgetting to close sockets or files exhausts the limit

### Signals

- Asynchronous notifications to processes: `SIGTERM` (graceful shutdown), `SIGKILL` (forced termination, cannot be caught), `SIGHUP` (terminal hangup, often used for config reload), `SIGINT` (Ctrl+C)
- **Interview relevance:** Explain graceful shutdown — catch `SIGTERM`, stop accepting new requests, drain in-flight requests, then exit

### Context Switching

- The OS saves the state (registers, program counter, stack pointer) of the current thread/process and loads the state of the next one
- **Cost:** Typically 1-10 microseconds, plus indirect costs (TLB flush, cache pollution)
- **Why it matters:** Excessive context switching degrades throughput. This is why event-loop architectures (Node.js) and green threads (Go) are popular for I/O-heavy workloads.

---

## Security

### OWASP Top 10 (Overview for Interviews)

| # | Vulnerability | One-Line Summary |
|---|---------------|-----------------|
| 1 | Broken Access Control | Users can act outside intended permissions |
| 2 | Cryptographic Failures | Sensitive data exposed due to weak crypto |
| 3 | Injection | Untrusted data sent to interpreter (SQL, NoSQL, OS) |
| 4 | Insecure Design | Flawed architecture, not just implementation bugs |
| 5 | Security Misconfiguration | Default configs, open cloud storage, verbose errors |
| 6 | Vulnerable Components | Outdated libraries with known CVEs |
| 7 | Authentication Failures | Broken auth, session management |
| 8 | Data Integrity Failures | Assumptions about software updates, CI/CD pipelines |
| 9 | Logging & Monitoring Failures | Breaches go undetected |
| 10 | SSRF | Server-side requests to unintended locations |

### XSS, CSRF, SQL Injection — Prevention

**XSS (Cross-Site Scripting):**
- **What:** Attacker injects malicious scripts into pages viewed by other users
- **Prevention:** Output encoding, Content Security Policy (CSP), sanitize HTML input, use frameworks that auto-escape (React, Angular)

**CSRF (Cross-Site Request Forgery):**
- **What:** Attacker tricks user's browser into making authenticated requests
- **Prevention:** CSRF tokens (synchronizer token pattern), SameSite cookie attribute, check Origin/Referer headers

**SQL Injection:**
- **What:** Attacker manipulates SQL queries through unsanitized input
- **Prevention:** Parameterized queries / prepared statements (never string concatenation), ORM usage, least-privilege database accounts

### Authentication Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Session-based** | Server stores session, client holds session ID in cookie | Traditional web apps |
| **JWT (stateless)** | Signed token contains claims, no server-side state | APIs, microservices |
| **OAuth 2.0** | Delegated authorization framework | Third-party access |
| **OIDC** | Identity layer on top of OAuth 2.0 | SSO, "Login with Google" |
| **API Keys** | Simple static tokens | Service-to-service, low-security |
| **mTLS** | Mutual TLS — both sides present certificates | Service mesh, zero-trust |

**JWT nuance for interviews:**
> "JWTs are not inherently better or worse than sessions. The tradeoff is that JWTs are stateless (no server-side lookup) but cannot be revoked without additional infrastructure (blocklist). For most web apps, session-based auth is simpler and more secure. JWTs shine in distributed systems where you want to avoid a centralized session store."

### Encryption at Rest vs In Transit

- **At rest:** AES-256 for stored data (database, disk, backups). Use your cloud provider's KMS for key management.
- **In transit:** TLS 1.3 for data moving between services. Enforce HTTPS everywhere. Use mTLS for service-to-service.

### Hashing vs Encryption

| Aspect | Hashing | Encryption |
|--------|---------|------------|
| Direction | One-way | Two-way (reversible) |
| Purpose | Integrity verification, password storage | Confidentiality |
| Output | Fixed-size digest | Variable-size ciphertext |
| Key required | No (but salts for passwords) | Yes |
| Examples | SHA-256, bcrypt, argon2 | AES, RSA, ChaCha20 |

**Password storage:** Use **bcrypt** or **argon2** with a unique salt per user. Never use SHA-256 alone (too fast, vulnerable to brute force). Never encrypt passwords — hash them.

---

## Distributed Systems Concepts

### Consistency Models

| Model | Guarantee | Example |
|-------|-----------|---------|
| **Strong consistency** | Reads always return most recent write | Single-node DB, Spanner |
| **Linearizability** | Strong consistency + real-time ordering | Zookeeper (writes) |
| **Sequential consistency** | All nodes see same order, but not necessarily real-time | Certain cache protocols |
| **Causal consistency** | Causally related operations seen in order | CRDT-based systems |
| **Eventual consistency** | All replicas converge eventually | DynamoDB, Cassandra (default) |

**CAP Theorem framing:**
> "CAP says you can have at most two of Consistency, Availability, and Partition tolerance. Since network partitions are inevitable, the real choice is between CP (reject requests during partition) and AP (serve potentially stale data). Most systems are not purely one or the other — they make different tradeoffs for different operations."

### Consensus — Raft and Paxos

**Why consensus matters:** In distributed systems, nodes need to agree on values (leader election, log replication) despite failures.

**Raft (understandable consensus):**
- **Leader election:** Nodes start as followers, timeout triggers candidate state, majority vote wins
- **Log replication:** Leader appends entries, replicates to followers, commits when majority acknowledges
- **Safety:** Only nodes with up-to-date logs can become leader
- **Key insight:** Raft decomposes consensus into leader election, log replication, and safety — making it far easier to understand than Paxos

**Paxos:**
- **Theoretical foundation** for distributed consensus
- **Phases:** Prepare (proposer asks acceptors to promise), Accept (proposer asks to accept value)
- **Practical reality:** "Nobody really implements Paxos" — most use Raft or Multi-Paxos variants
- **Interview signal:** Mention that Raft was designed as a more understandable alternative to Paxos, and that you would use etcd or ZooKeeper rather than implementing consensus yourself

### Distributed Locks

- **Purpose:** Coordinate access to shared resources across nodes
- **Implementations:** Redis (Redlock), ZooKeeper (ephemeral znodes), etcd (lease-based)
- **Fencing tokens:** A lock alone is not enough — use monotonically increasing tokens to prevent stale lock holders from making writes
- **Interview caution:** Distributed locks are hard to get right. Martin Kleppmann's critique of Redlock is worth knowing.

### Clock Synchronization

- **Problem:** Physical clocks drift. Two nodes can disagree on "now" by milliseconds to seconds.
- **NTP:** Keeps clocks approximately synchronized (millisecond accuracy)
- **Google TrueTime:** GPS + atomic clocks, provides bounded uncertainty intervals. Used in Spanner for external consistency.
- **Logical clocks:** Lamport clocks provide causal ordering without relying on physical time

### Vector Clocks

- **What:** Each node maintains a vector of logical timestamps, one per node
- **Purpose:** Detect causal relationships and conflicts between events
- **How:** On local event, increment own counter. On send, attach vector. On receive, merge (take max per entry) and increment own.
- **Use case:** Conflict detection in eventually consistent systems (Dynamo, Riak)
- **Limitation:** Vector size grows with number of nodes — use version vectors or dotted version vectors for optimization

---

## Interview Questions & Answers

### Data Structures

**Q: When would you use a trie over a hash map?**
> A: When I need prefix-based operations — autocomplete, spell checking, or finding all keys with a given prefix. A hash map can only do exact lookups. A trie also has the benefit of O(m) lookup where m is key length, independent of the number of keys. The tradeoff is higher memory usage per entry, though compressed tries (radix trees) mitigate this.

**Q: How does a hash map handle collisions?**
> A: Two main strategies. Chaining uses a linked list (or tree above a threshold, like Java 8's HashMap) at each bucket. Open addressing probes for the next empty slot (linear probing, quadratic probing, double hashing). Chaining is simpler but has worse cache locality. Open addressing has better cache performance but degrades as load factor increases.

### Big-O

**Q: What is the difference between O(n) and Theta(n)?**
> A: O(n) is an upper bound — the algorithm takes at most linear time. Theta(n) is a tight bound — it takes exactly linear time (both upper and lower bound). In interviews, O notation is standard for upper-bound analysis. But when I say an algorithm "is O(n)," I usually mean Theta(n) — it is both the best and worst case.

### Concurrency

**Q: How would you prevent a deadlock?**
> A: I would break one of the four Coffman conditions. The most practical approach is enforcing a global ordering on resource acquisition — if every thread acquires locks in the same order, circular wait is impossible. Alternatively, use lock timeouts so threads release held resources if they cannot acquire everything they need, though this introduces livelock risk.

**Q: Explain the difference between concurrency and parallelism.**
> A: Concurrency is about dealing with multiple things at once — structuring your program to handle multiple tasks, potentially interleaved on a single core. Parallelism is about doing multiple things at once — actually executing simultaneously on multiple cores. A Node.js event loop is concurrent but not parallel. A multi-threaded program on a multi-core machine can be both.

### Networking

**Q: What happens when you type "https://google.com" and press Enter?**
> A: [Use the framework above — DNS resolution, TCP handshake, TLS handshake, HTTP request, server processing, response rendering. Cover each in 1-2 sentences. Demonstrate depth by mentioning HSTS, HTTP/2 multiplexing, browser caching, CDN edge nodes, connection reuse.]

**Q: When would you choose UDP over TCP?**
> A: When low latency matters more than guaranteed delivery. Video conferencing, online gaming, and DNS queries all use UDP. A dropped video frame is better re-rendered than retransmitted (it is already stale). DNS queries are small enough that retransmission at the application layer is simpler than TCP overhead.

### Operating Systems

**Q: What is a context switch and why is it expensive?**
> A: The OS saves the current thread's state (registers, program counter, stack pointer) and loads the next thread's state. The direct cost is microseconds, but the indirect costs are significant — the TLB may be flushed (for process switches), CPU caches become cold, and pipeline predictions are invalidated. This is why architectures minimizing context switches (event loops, green threads) can outperform thread-per-request models for I/O-heavy workloads.

**Q: Explain virtual memory in simple terms.**
> A: Each process thinks it has its own contiguous block of memory. The OS and hardware translate these virtual addresses to physical addresses using page tables. This gives us isolation (processes cannot read each other's memory), the illusion of more memory than physically exists (pages can be swapped to disk), and convenience (every process starts at the same virtual address). The TLB caches these translations so we are not doing a page table walk on every memory access.

### Security

**Q: How do you store passwords securely?**
> A: Hash them with bcrypt or argon2 using a unique salt per user. Never store plaintext, never use fast hashes like SHA-256 (vulnerable to brute force — GPUs can compute billions per second). Bcrypt is intentionally slow and has a configurable work factor you can increase over time. Argon2 additionally resists GPU attacks by requiring significant memory. Never encrypt passwords — if the encryption key is compromised, all passwords are exposed.

**Q: Explain the difference between authentication and authorization.**
> A: Authentication verifies identity — "who are you?" Authorization determines permissions — "what can you do?" Authentication comes first. OAuth 2.0 is an authorization framework (it grants access to resources), while OpenID Connect adds authentication on top. A common interview mistake is conflating the two.

### Distributed Systems

**Q: Explain eventual consistency. When is it acceptable?**
> A: In an eventually consistent system, replicas may temporarily return different values, but will converge to the same value given enough time without new writes. It is acceptable when stale reads are tolerable — a social media timeline, a product catalog, DNS. It is not acceptable when correctness depends on reading the latest value — financial transactions, inventory with limited stock, distributed locks.

**Q: What is the split-brain problem?**
> A: In a distributed system with a leader, a network partition can cause two partitions to each elect their own leader. Both accept writes, creating divergent state. Prevention strategies include requiring a majority quorum for leader election (so only one partition can have a leader), fencing tokens, and STONITH (Shoot The Other Node In The Head) in failover clusters.

---

## Summary

The key to technical questions at the senior level is not just knowing the answer — it is demonstrating **judgment**. Every answer should include:

1. The **what** — the factual answer
2. The **tradeoffs** — what you gain and what you give up
3. The **when** — under what circumstances you would choose this approach
4. The **alternatives** — what else you considered

This framing signals that you do not just memorize — you think.

---

## Appendix: Additional Interview Questions

### Data Structures — Additional Questions

**Q: When would you use an adjacency matrix over an adjacency list?**
> A: Adjacency matrices work well for dense graphs where most node pairs have edges. Lookup for "does edge (u,v) exist?" is O(1). The tradeoff is O(V^2) space regardless of edge count. For sparse graphs (most real-world networks), adjacency lists are better at O(V + E) space.

**Q: What is the difference between a stack and a queue? Give a real-world use case for each.**
> A: A stack is LIFO — last in, first out. Think of browser back button history, undo operations, or DFS traversal. A queue is FIFO — first in, first out. Think of task scheduling, BFS traversal, or message queues in distributed systems.

### Concurrency — Additional Questions

**Q: What is a thread pool and why would you use one?**
> A: A thread pool pre-creates a fixed number of threads that pick tasks from a shared queue. It avoids the overhead of creating and destroying threads per request. The pool size is typically tuned to the number of CPU cores (for CPU-bound work) or a larger number (for I/O-bound work where threads spend most of their time waiting).

**Q: What is the difference between optimistic and pessimistic locking?**
> A: Pessimistic locking acquires a lock before accessing the resource, blocking other threads. Optimistic locking reads the data, performs the operation, and checks for conflicts at write time (using a version number or CAS operation). Optimistic locking is better when contention is low — most operations succeed without conflict. Pessimistic is safer when contention is high.

### Networking — Additional Questions

**Q: How does HTTP keep-alive work and why does it matter?**
> A: HTTP keep-alive reuses a TCP connection for multiple HTTP requests instead of opening a new connection per request. This avoids the overhead of TCP handshakes and TLS negotiations. HTTP/1.1 has keep-alive by default. HTTP/2 goes further with multiplexing — multiple concurrent requests on a single connection.

**Q: What is the difference between forward proxy and reverse proxy?**
> A: A forward proxy sits in front of clients, forwarding their requests to the internet (corporate proxies, VPNs). A reverse proxy sits in front of servers, distributing incoming requests (nginx, load balancers). The client does not know about a reverse proxy; the server does not know about a forward proxy.

### Security — Additional Questions

**Q: What is the principle of least privilege and how do you apply it?**
> A: Every user, process, and service should have only the minimum permissions needed to perform its function. In practice: database users should not have admin access, API keys should be scoped to specific operations, microservices should not share credentials, and IAM roles should deny by default.

**Q: How would you prevent SQL injection in a legacy codebase?**
> A: Priority one is replacing all string-concatenated queries with parameterized queries or prepared statements. If the ORM supports it, use the ORM's query builder. Add input validation as a defense-in-depth layer, but never rely on it as the primary defense. Run a static analysis tool to find remaining injection points. Consider a WAF (Web Application Firewall) as a temporary mitigation while fixing the code.

### Distributed Systems — Additional Questions

**Q: What is the difference between leader-based and leaderless replication?**
> A: Leader-based replication (used by PostgreSQL, MySQL, MongoDB) routes all writes through a single leader node that replicates to followers. It provides strong consistency but the leader is a bottleneck and single point of failure. Leaderless replication (used by Cassandra, DynamoDB) allows writes to any node and uses quorum reads/writes for consistency. It is more available but harder to reason about consistency.

**Q: Explain the Two Generals Problem and why it matters.**
> A: Two generals on opposite sides of an enemy must agree on an attack time, but their messengers can be captured. No number of acknowledged messages can guarantee both generals know the other will attack. This is a fundamental impossibility result — it proves that guaranteed consensus over an unreliable network is impossible. It is the conceptual foundation for understanding why distributed consensus is hard and why protocols like Raft require majority quorums rather than unanimity.
