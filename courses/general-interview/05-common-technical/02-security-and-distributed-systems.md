# Security and Distributed Systems

> Builds on the foundational concepts. Covers security fundamentals and distributed systems concepts that appear in senior-level interviews.

---

## Security

### OWASP Top 10

| # | Vulnerability | One-Line Summary | Prevention |
|---|---------------|-----------------|------------|
| 1 | Broken Access Control | Users can act outside intended permissions | Server-side checks, deny by default, RBAC |
| 2 | Cryptographic Failures | Sensitive data exposed due to weak crypto | TLS everywhere, AES-256, proper key management |
| 3 | Injection | Untrusted data sent to interpreter (SQL, NoSQL, OS) | Parameterized queries, input validation, ORMs |
| 4 | Insecure Design | Flawed architecture, not just implementation bugs | Threat modeling, secure design patterns |
| 5 | Security Misconfiguration | Default configs, open cloud storage, verbose errors | Hardened defaults, automated config audits |
| 6 | Vulnerable Components | Outdated libraries with known CVEs | Dependency scanning, regular updates, SBOM |
| 7 | Authentication Failures | Broken auth, session management | MFA, rate limiting, secure session management |
| 8 | Data Integrity Failures | Assumptions about software updates, CI/CD pipelines | Code signing, verified CI/CD pipelines |
| 9 | Logging & Monitoring Failures | Breaches go undetected | Centralized logging, alerting, audit trails |
| 10 | SSRF | Server-side requests to unintended locations | Allowlist URLs, block internal IPs, network segmentation |

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

**Authentication vs Authorization:**
> "Authentication verifies identity — 'who are you?' Authorization determines permissions — 'what can you do?' Authentication comes first. OAuth 2.0 is an authorization framework (it grants access to resources), while OpenID Connect adds authentication on top. A common interview mistake is conflating the two."

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
| For passwords | bcrypt, argon2 (with salt) | NEVER encrypt passwords |
| For data | SHA-256 (integrity check) | AES-256 (at rest), TLS (in transit) |
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

### CAP Theorem

**CAP framing:**
> "CAP says you can have at most two of Consistency, Availability, and Partition tolerance. Since network partitions are inevitable, the real choice is between CP (reject requests during partition) and AP (serve potentially stale data). Most systems are not purely one or the other — they make different tradeoffs for different operations."

### Distributed Systems Quick Reference

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

## Security Interview Questions and Answers

**Q: How do you store passwords securely?**
> A: Hash them with bcrypt or argon2 using a unique salt per user. Never store plaintext, never use fast hashes like SHA-256 (vulnerable to brute force — GPUs can compute billions per second). Bcrypt is intentionally slow and has a configurable work factor you can increase over time. Argon2 additionally resists GPU attacks by requiring significant memory. Never encrypt passwords — if the encryption key is compromised, all passwords are exposed.

**Q: Explain the difference between authentication and authorization.**
> A: Authentication verifies identity — "who are you?" Authorization determines permissions — "what can you do?" Authentication comes first. OAuth 2.0 is an authorization framework (it grants access to resources), while OpenID Connect adds authentication on top. A common interview mistake is conflating the two.

**Q: What is the principle of least privilege and how do you apply it?**
> A: Every user, process, and service should have only the minimum permissions needed to perform its function. In practice: database users should not have admin access, API keys should be scoped to specific operations, microservices should not share credentials, and IAM roles should deny by default.

**Q: How would you prevent SQL injection in a legacy codebase?**
> A: Priority one is replacing all string-concatenated queries with parameterized queries or prepared statements. If the ORM supports it, use the ORM's query builder. Add input validation as a defense-in-depth layer, but never rely on it as the primary defense. Run a static analysis tool to find remaining injection points. Consider a WAF (Web Application Firewall) as a temporary mitigation while fixing the code.

---

## Distributed Systems Interview Questions and Answers

**Q: Explain eventual consistency. When is it acceptable?**
> A: In an eventually consistent system, replicas may temporarily return different values, but will converge to the same value given enough time without new writes. It is acceptable when stale reads are tolerable — a social media timeline, a product catalog, DNS. It is not acceptable when correctness depends on reading the latest value — financial transactions, inventory with limited stock, distributed locks.

**Q: What is the split-brain problem?**
> A: In a distributed system with a leader, a network partition can cause two partitions to each elect their own leader. Both accept writes, creating divergent state. Prevention strategies include requiring a majority quorum for leader election (so only one partition can have a leader), fencing tokens, and STONITH (Shoot The Other Node In The Head) in failover clusters.

**Q: What is the difference between leader-based and leaderless replication?**
> A: Leader-based replication (used by PostgreSQL, MySQL, MongoDB) routes all writes through a single leader node that replicates to followers. It provides strong consistency but the leader is a bottleneck and single point of failure. Leaderless replication (used by Cassandra, DynamoDB) allows writes to any node and uses quorum reads/writes for consistency. It is more available but harder to reason about consistency.

**Q: Explain the Two Generals Problem and why it matters.**
> A: Two generals on opposite sides of an enemy must agree on an attack time, but their messengers can be captured. No number of acknowledged messages can guarantee both generals know the other will attack. This is a fundamental impossibility result — it proves that guaranteed consensus over an unreliable network is impossible. It is the conceptual foundation for understanding why distributed consensus is hard and why protocols like Raft require majority quorums rather than unanimity.
