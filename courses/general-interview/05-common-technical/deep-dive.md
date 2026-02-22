# Module 05 Deep Dive: Advanced Technical Topics

> For when the interviewer goes beyond the fundamentals. These topics separate "strong senior" from "staff-level" answers.

---

## Table of Contents

1. [Advanced Data Structures](#advanced-data-structures)
2. [Advanced Networking](#advanced-networking)
3. [Advanced Distributed Systems](#advanced-distributed-systems)
4. [Cryptography Fundamentals](#cryptography-fundamentals)

---

## Advanced Data Structures

### Bloom Filters

**What:** A probabilistic data structure for membership testing. It can tell you "definitely not in the set" or "probably in the set" — false positives are possible, false negatives are not.

**How it works:**
1. A bit array of size m, initialized to all zeros
2. k independent hash functions
3. **Insert:** Hash the element k times, set those bit positions to 1
4. **Query:** Hash the element k times, check if all positions are 1. If any is 0, the element is definitely not in the set.

**Why it matters:**
- Space-efficient: Can test membership in billions of items with megabytes of memory
- Used in databases (avoid unnecessary disk reads), CDNs (cache filtering), spell checkers, network routers

**Interview depth:**
- False positive rate: approximately `(1 - e^(-kn/m))^k` where n is number of elements
- Optimal k = `(m/n) * ln(2)`
- Cannot delete elements from a standard Bloom filter (use counting Bloom filters for that)
- Cuckoo filters are a modern alternative offering deletion and better space efficiency at low false positive rates

### Skip Lists

**What:** A probabilistic data structure providing O(log n) search, insert, and delete on a sorted sequence. Think of it as a linked list with multiple levels of "express lanes."

**How it works:**
- Bottom level: a sorted linked list of all elements
- Each higher level: a random subset of the level below (each element is promoted with probability 1/2)
- Search: Start at the top level, move right until you overshoot, drop down one level, repeat

**Why it matters:**
- Simpler to implement than balanced BSTs
- Used in Redis sorted sets, LevelDB, RocksDB memtables
- Lock-free concurrent implementations are easier than for balanced trees

**Interview comparison with balanced BSTs:**
- Both O(log n) expected time for search/insert/delete
- BSTs are deterministic, skip lists are probabilistic
- Skip lists have simpler code and better concurrency properties
- BSTs use less memory on average

### B-Trees

**What:** Self-balancing tree optimized for systems that read/write large blocks of data. Each node can hold multiple keys and has multiple children.

**Properties:**
- Each node holds between t-1 and 2t-1 keys (t is the minimum degree)
- All leaves are at the same depth
- Nodes are designed to match disk page sizes

**Why it matters:**
- The foundation of database indexes (B+ trees specifically)
- Minimizes disk I/O by maximizing keys per disk read
- B+ trees store all data in leaf nodes with leaf-to-leaf links, enabling efficient range scans

**B-tree vs B+ tree:**
- B-tree: data in all nodes, no leaf links
- B+ tree: data only in leaves, leaves linked together. This is what databases actually use — enables sequential scan without revisiting internal nodes.

### LSM Trees (Log-Structured Merge Trees)

**What:** A write-optimized data structure used by modern storage engines (RocksDB, Cassandra, LevelDB, HBase).

**How it works:**
1. **Write path:** Writes go to an in-memory buffer (memtable, often a skip list or red-black tree)
2. When the memtable is full, it is flushed to disk as a sorted immutable file (SSTable)
3. Background compaction merges SSTables, removing duplicates and tombstones
4. **Read path:** Check memtable, then SSTables from newest to oldest. Bloom filters on each SSTable reduce unnecessary reads.

**Why it matters:**
- Turns random writes into sequential writes (much faster on both HDD and SSD)
- Write amplification is a known tradeoff — data is written multiple times during compaction
- Read amplification is another — may need to check multiple SSTables

**Interview comparison with B-trees:**

| Aspect | B-tree | LSM Tree |
|--------|--------|----------|
| Write pattern | Random (update in place) | Sequential (append + compact) |
| Read performance | Better (single lookup) | Worse (multiple levels) |
| Write performance | Worse (random I/O) | Better (sequential I/O) |
| Space amplification | Lower | Higher (during compaction) |
| Use case | Read-heavy (PostgreSQL) | Write-heavy (Cassandra, RocksDB) |

---

## Advanced Networking

### TCP Congestion Control

**Why it exists:** If every sender blasts data at full speed, the network collapses (congestion collapse). TCP self-regulates.

**Key algorithms:**

1. **Slow Start:** Begin with a small congestion window (cwnd), double it every RTT. Exponential growth until threshold (ssthresh) is hit.
2. **Congestion Avoidance:** After ssthresh, increase cwnd by 1 MSS per RTT. Linear growth.
3. **Fast Retransmit:** If 3 duplicate ACKs are received, retransmit without waiting for timeout.
4. **Fast Recovery (Reno):** After fast retransmit, halve cwnd instead of resetting to 1.

**Modern algorithms:**
- **CUBIC:** Default in Linux. Uses a cubic function for window growth, better for high-bandwidth networks.
- **BBR (Bottleneck Bandwidth and RTT):** Google's algorithm. Models the network path instead of reacting to loss. Significantly better for long-distance, high-bandwidth connections.

**Interview relevance:** Explains why fresh connections are slow (slow start), why TCP performs poorly on lossy networks (misinterprets loss as congestion), and why QUIC was created.

### HTTP/2 Multiplexing

**The HTTP/1.1 problem:**
- One request per TCP connection at a time (head-of-line blocking)
- Browsers work around this by opening 6+ parallel connections per domain
- Domain sharding was a common hack

**HTTP/2 solution:**
- Single TCP connection, multiple **streams** within it
- Streams are interleaved (multiplexed) on the same connection
- **Frames** are the smallest unit — headers and data in separate frame types
- **Header compression (HPACK)** reduces overhead of repetitive headers
- **Server push** allows the server to proactively send resources

**The remaining problem:**
- TCP head-of-line blocking: a single lost packet blocks ALL streams (TCP guarantees ordering)
- This is what motivated QUIC

### QUIC

**What:** A transport protocol built on UDP that provides the reliability of TCP with the multiplexing benefits of HTTP/2 — without TCP's head-of-line blocking.

**Key features:**
- **Stream-level flow control:** A lost packet in one stream does not block other streams
- **0-RTT connection establishment:** For resumed connections, send data with the first packet
- **Built-in TLS 1.3:** Encryption is not optional, integrated into the handshake
- **Connection migration:** Connections survive IP address changes (mobile networks)

**How it avoids TCP head-of-line blocking:**
- Each QUIC stream is independently ordered
- A lost packet only blocks the stream it belongs to
- Other streams continue processing

**Interview context:**
> "HTTP/3 is HTTP over QUIC. The main motivation was eliminating TCP head-of-line blocking that HTTP/2 still suffered from. QUIC runs on UDP to avoid needing OS-level TCP changes, but it reimplements reliability and congestion control in userspace. It is already used by Google, Cloudflare, and most major CDNs."

---

## Advanced Distributed Systems

### Byzantine Fault Tolerance (BFT)

**What:** Tolerance of nodes that can behave arbitrarily (lie, send conflicting messages, collude). Named after the Byzantine Generals Problem.

**Crash faults vs Byzantine faults:**
- **Crash fault:** Node stops responding. Raft/Paxos handle this with 2f+1 nodes tolerating f failures.
- **Byzantine fault:** Node sends incorrect or malicious messages. Requires 3f+1 nodes to tolerate f failures (PBFT).

**Practical BFT (PBFT):**
- Three-phase protocol: Pre-prepare, Prepare, Commit
- Requires 3f+1 nodes, can tolerate f Byzantine failures
- O(n^2) message complexity — does not scale well

**Interview context:**
> "Most internal distributed systems assume crash faults only — we trust our own nodes. Byzantine fault tolerance matters in blockchain (untrusted participants) and certain financial systems. For internal systems, Raft is sufficient and far simpler."

### CRDTs (Conflict-free Replicated Data Types)

**What:** Data structures that can be replicated across nodes, updated independently, and merged automatically without conflicts.

**Two types:**
- **State-based (CvRDT):** Merge full state; requires commutative, associative, idempotent merge function
- **Operation-based (CmRDT):** Transmit operations; requires commutative operations

**Common CRDTs:**
- **G-Counter:** Grow-only counter. Each node has its own counter; value = sum of all.
- **PN-Counter:** Positive-negative counter. Two G-Counters — one for increments, one for decrements.
- **G-Set:** Grow-only set. Merge = union.
- **OR-Set (Observed-Remove Set):** Supports add and remove. Each element tagged with unique ID.
- **LWW-Register (Last-Writer-Wins):** Register where conflicts resolve by timestamp.

**Use cases:** Collaborative editing (Figma uses CRDTs), shopping carts, distributed counters, offline-first applications.

**Tradeoff:** CRDTs guarantee convergence but not the "right" answer. The semantics of the merge function must match your business requirements.

### Gossip Protocols

**What:** Protocols where nodes periodically exchange information with random peers, eventually propagating state to all nodes. Inspired by epidemic spreading.

**How it works:**
1. Each node periodically selects a random peer
2. They exchange state (push, pull, or push-pull)
3. Updated information spreads exponentially — reaches all nodes in O(log n) rounds

**Properties:**
- **Scalable:** O(log n) convergence, each node only talks to a few peers
- **Fault-tolerant:** No single point of failure, works despite node failures
- **Eventually consistent:** No guarantees on when information reaches all nodes

**Use cases:** Failure detection (Cassandra, Consul), membership (SWIM protocol), state dissemination.

**Interview context:**
> "Cassandra uses a gossip protocol for cluster membership and failure detection. Each node gossips with 1-3 random peers every second, sharing information about which nodes are alive. This avoids needing a centralized coordinator and scales to hundreds of nodes."

### Consistent Hashing

**What:** A hashing technique that minimizes remapping when the number of nodes changes.

**The problem with naive hashing:**
- `hash(key) % N` — if N changes (node added/removed), almost all keys remap

**How consistent hashing works:**
1. Nodes and keys are both hashed onto a ring (0 to 2^32)
2. A key is assigned to the first node clockwise from its position
3. When a node is added, only keys between the new node and its predecessor remap
4. When a node is removed, only its keys remap to the next node

**Virtual nodes:** Each physical node has multiple positions on the ring. This provides better load distribution and smoother rebalancing.

**Used in:** DynamoDB, Cassandra, memcached, CDN routing, load balancers.

---

## Cryptography Fundamentals

### Symmetric vs Asymmetric Encryption

| Aspect | Symmetric | Asymmetric |
|--------|-----------|------------|
| Keys | Same key for encrypt/decrypt | Public key encrypts, private key decrypts |
| Speed | Fast (hardware accelerated) | Slow (100-1000x slower) |
| Key distribution | Problem: how to share the key securely | Public key can be shared openly |
| Examples | AES-256, ChaCha20 | RSA, ECDSA, Ed25519 |
| Use case | Bulk data encryption | Key exchange, digital signatures |

**How TLS combines both:**
1. Asymmetric encryption establishes a shared secret (key exchange)
2. Symmetric encryption handles bulk data using the shared secret
3. Best of both worlds: asymmetric solves key distribution, symmetric provides speed

### Digital Signatures

**What:** A way to prove that a message was sent by a specific party and has not been tampered with.

**How it works:**
1. Sender hashes the message
2. Sender encrypts the hash with their **private key** (this is the signature)
3. Receiver decrypts the signature with the sender's **public key**
4. Receiver independently hashes the message and compares

**Properties:**
- **Authentication:** Only the private key holder could have created the signature
- **Integrity:** Any modification to the message changes the hash, invalidating the signature
- **Non-repudiation:** The signer cannot deny signing (unlike symmetric MACs)

### Certificate Chains

**Problem:** How do you trust a server's public key?

**Solution — Chain of Trust:**
1. **Root CAs** are pre-installed in your OS/browser (trusted by fiat)
2. Root CAs sign intermediate CA certificates
3. Intermediate CAs sign server certificates
4. Your browser walks the chain from server cert to a trusted root

**Certificate contents:** Subject (domain name), public key, issuer, validity period, signature by issuer.

**Certificate pinning:** Application hardcodes expected certificate or public key, rejecting even valid certificates from other CAs. Protects against compromised CAs but complicates certificate rotation.

**Let's Encrypt and ACME:** Automated certificate issuance and renewal. No reason for any public-facing service to not use HTTPS.

### Interview-Relevant Crypto Topics

**Key derivation functions (KDFs):**
- PBKDF2, scrypt, argon2 — stretch passwords into encryption keys
- Deliberately slow to prevent brute force

**HMAC (Hash-based Message Authentication Code):**
- Verifies both integrity and authenticity using a shared secret
- Used in API authentication, JWT signing (HS256)

**Envelope encryption:**
- Encrypt data with a data encryption key (DEK)
- Encrypt the DEK with a key encryption key (KEK)
- Store encrypted DEK alongside encrypted data
- Used by AWS KMS, GCP KMS — you never handle the KEK directly

**Forward secrecy:**
- Compromising the server's long-term private key does not reveal past session keys
- Achieved by using ephemeral Diffie-Hellman key exchange
- TLS 1.3 requires forward secrecy

---

## Summary

These advanced topics share a common theme: they exist because the simple approach does not scale. Bloom filters exist because hash maps use too much memory. QUIC exists because TCP's guarantees become liabilities at scale. CRDTs exist because strong consistency is too expensive for certain workloads. Understanding **why** these solutions were created matters more than memorizing their implementations.

---

## Appendix: Advanced Interview Questions

### Advanced Data Structures

**Q: How does a Bloom filter handle deletions?**
> A: Standard Bloom filters cannot handle deletions — clearing a bit might affect other elements mapped to the same position. Counting Bloom filters replace each bit with a counter, incrementing on insert and decrementing on delete. The tradeoff is higher memory usage (typically 3-4x). Cuckoo filters are a modern alternative that supports deletion with better space efficiency.

**Q: Why do databases use B+ trees instead of B-trees for indexes?**
> A: B+ trees store all data in leaf nodes and link leaves together. This means range scans only need to traverse the leaf level sequentially, without revisiting internal nodes. Internal nodes store only keys and pointers, allowing a higher branching factor and shallower tree. For database workloads where range queries and sequential scans are common, this is a significant advantage.

**Q: When would you choose an LSM tree over a B-tree for storage?**
> A: LSM trees excel at write-heavy workloads because they convert random writes to sequential writes (append to memtable, flush sorted files to disk). B-trees excel at read-heavy workloads because data is found with a single tree traversal. If your workload is 90% writes (e.g., time-series data, logging, event sourcing), an LSM tree engine like RocksDB is likely the better choice. For balanced read/write workloads with complex queries, a B-tree engine like InnoDB is usually better.

### Advanced Networking

**Q: Why was QUIC built on UDP instead of creating a new transport protocol?**
> A: Pragmatism. Deploying a new transport protocol requires changes to operating system kernels, middlebox firmware, and NAT devices worldwide — a process that takes decades. UDP is already universally supported and passed by middleboxes. By building on UDP, QUIC can be deployed entirely in userspace (application-level libraries) and iterated rapidly without waiting for OS updates.

**Q: Explain HTTP/2 server push and why it was largely abandoned.**
> A: HTTP/2 server push allowed servers to proactively send resources before the client requested them — for example, pushing CSS and JS files along with the HTML. In theory, this eliminates a round trip. In practice, it was problematic: servers could not know what the client already had cached, pushed resources often wasted bandwidth, and the caching semantics were complex. Most CDNs and browsers have deprecated or limited server push in favor of 103 Early Hints.

### Advanced Distributed Systems

**Q: What are the tradeoffs between Raft and Paxos?**
> A: Raft was designed for understandability. It constrains the problem more than Paxos — it requires a strong leader, and log entries are only committed in order. This makes it easier to implement correctly but potentially less flexible. Paxos is more general and can commit out of order, but its generality makes implementation notoriously difficult. Multi-Paxos (with a stable leader) behaves similarly to Raft in practice. For most engineering teams, Raft or a battle-tested Raft library (etcd's Raft) is the right choice.

**Q: How does consistent hashing handle hotspots?**
> A: Virtual nodes are the primary mechanism. Each physical node gets multiple positions on the hash ring, distributing load more evenly. If a particular key range is hot, you can assign more virtual nodes to beefier machines. For extreme hotspots (a single viral key), consistent hashing alone is not sufficient — you need application-level caching or key replication strategies on top.
