# Module 00: Computing Fundamentals for System Design

This course assumes you've deployed and operated production services. Before diving into system design frameworks and scaling patterns, make sure these fundamentals are sharp — interviewers will probe them, and hand-waving at "it goes through the network" won't fly at staff level.

---

## 1. Networking

### The Request Journey

When a user types `https://app.example.com/api/users` in a browser:

```
1. DNS Resolution
   Browser → DNS Resolver → Root NS → .com NS → example.com NS
   Returns: 93.184.216.34

2. TCP Connection
   Client → SYN → Server
   Client ← SYN-ACK ← Server
   Client → ACK → Server
   (three-way handshake — connection established)

3. TLS Handshake (HTTPS)
   Client → ClientHello (supported ciphers, TLS version)
   Server → ServerHello + Certificate
   Client verifies certificate chain → CA trust
   Key exchange → shared secret established
   (adds 1-2 round trips)

4. HTTP Request
   GET /api/users HTTP/2
   Host: app.example.com
   Authorization: Bearer eyJ...

5. Server processes, returns response

6. TCP Teardown (eventually)
   FIN → ACK → FIN → ACK (four-way handshake)
```

### DNS

DNS maps domain names to IP addresses. In system design, DNS matters for:

- **TTL (Time to Live)**: how long resolvers cache a record. Lower TTL = faster failover but more DNS queries. Typical: 60-300 seconds.
- **Record types**: A (IPv4), AAAA (IPv6), CNAME (alias), MX (mail), TXT (verification), SRV (service discovery)
- **GeoDNS / Latency-based routing**: return different IPs based on the client's location (Route 53, Cloudflare)
- **DNS failover**: health-check aware DNS that removes unhealthy IPs

### TCP vs UDP

| | TCP | UDP |
|---|-----|-----|
| **Connection** | Connection-oriented (handshake) | Connectionless |
| **Reliability** | Guaranteed delivery, ordering, retransmission | Best effort — packets may be lost or reordered |
| **Use cases** | HTTP, database connections, file transfer | DNS, video streaming, gaming, VoIP |
| **Overhead** | Higher (headers, acks, flow control) | Lower |

### HTTP

```
HTTP/1.1: One request per TCP connection (or pipelining, rarely used)
HTTP/2:   Multiplexed streams over one connection, header compression, server push
HTTP/3:   QUIC (UDP-based), 0-RTT connection, better for lossy networks
```

Key concepts:
- **Status codes**: 2xx success, 3xx redirect, 4xx client error, 5xx server error
- **Methods**: GET (read), POST (create), PUT (replace), PATCH (partial update), DELETE (remove)
- **Headers**: Content-Type, Authorization, Cache-Control, ETag, X-Request-ID
- **Idempotency**: GET, PUT, DELETE are idempotent (safe to retry). POST is not (without idempotency keys).
- **Keep-Alive**: reuse TCP connections across requests (default in HTTP/1.1+)

### Latency Numbers Every Engineer Should Know

```
L1 cache reference:                 1 ns
L2 cache reference:                 4 ns
Main memory reference:             100 ns
SSD random read:                   16 μs
HDD random read:                    2 ms
Same datacenter round trip:       500 μs
California → Netherlands:         150 ms

Key takeaway:
- Memory is ~100,000x faster than network
- SSD is ~100x faster than HDD
- Same-region network is ~300x faster than cross-continent
```

---

## 2. Operating System Concepts

### Processes vs Threads

```
Process:
  - Independent memory space
  - Isolated (crash doesn't affect others)
  - Expensive to create
  - Communication via IPC (pipes, sockets, shared memory)

Thread:
  - Shared memory within a process
  - Lightweight to create
  - Crash in one thread can kill the process
  - Communication via shared memory (needs synchronization)
```

In system design:
- **Multi-process** (Gunicorn workers, Node.js cluster): isolation, fault tolerance, more memory
- **Multi-threaded** (Go goroutines, Java threads): shared memory, lower overhead, needs synchronization
- **Event loop** (Node.js, Python asyncio): single-threaded concurrency for I/O-bound work

### Concurrency vs Parallelism

```
Concurrency: multiple tasks making progress (may not run simultaneously)
  → Single CPU switching between tasks (event loop, coroutines)
  → Useful for I/O-bound work (waiting for network, disk, DB)

Parallelism: multiple tasks running simultaneously
  → Multiple CPUs executing different code at the same time
  → Useful for CPU-bound work (computation, image processing)
```

### File System Basics

- **Inodes**: metadata about files (permissions, size, block locations), not the name
- **File descriptors**: integer handles to open files. Limited per process (`ulimit -n`). Running out = "too many open files" errors.
- **Disk I/O**: sequential reads are 100x faster than random reads on HDD. SSD narrows this gap but sequential is still faster.
- **Page cache**: OS caches recently read files in RAM. "Free" memory often isn't wasted — it's page cache.

### Memory

- **Virtual memory**: each process sees a contiguous address space. The OS maps it to physical RAM (and swap/disk if RAM is full).
- **Swap**: when RAM is full, the OS moves pages to disk. Performance craters. In production, you usually want swap off or limited.
- **OOM killer**: Linux kills the process using the most memory when the system runs out. Your production service might get killed by someone else's memory leak.

---

## 3. Database Fundamentals

### SQL Basics

```sql
-- CRUD operations
SELECT id, name, email FROM users WHERE active = true ORDER BY name LIMIT 20;
INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');
UPDATE users SET email = 'new@example.com' WHERE id = 1;
DELETE FROM users WHERE id = 1;

-- Joins
SELECT u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.created_at > '2024-01-01';

-- Aggregation
SELECT status, COUNT(*) as count, AVG(total) as avg_total
FROM orders
GROUP BY status
HAVING COUNT(*) > 10;
```

### ACID Properties

| Property | Meaning | Why It Matters |
|----------|---------|----------------|
| **Atomicity** | Transaction is all-or-nothing | Transfer $100: debit AND credit both succeed or both fail |
| **Consistency** | Database moves from one valid state to another | Foreign keys, constraints, triggers are enforced |
| **Isolation** | Concurrent transactions don't interfere | Two people buying the last item don't both succeed |
| **Durability** | Committed data survives crashes | Power failure after commit doesn't lose data |

### Indexing

```
Without index: scan every row (O(n))
With B-tree index: binary search (O(log n))

CREATE INDEX idx_users_email ON users(email);

-- Composite index (order matters!)
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at);
-- This index helps: WHERE user_id = 1 AND created_at > '2024-01-01'
-- This index helps: WHERE user_id = 1  (leftmost prefix)
-- This index does NOT help: WHERE created_at > '2024-01-01' (skips first column)
```

When to index:
- Columns in WHERE clauses, JOIN conditions, ORDER BY
- High-cardinality columns (many distinct values)
- Frequently queried columns

Trade-offs: indexes speed up reads but slow down writes (must update the index on every INSERT/UPDATE/DELETE). They also consume disk space.

### SQL vs NoSQL

| | SQL (PostgreSQL, MySQL) | NoSQL (DynamoDB, MongoDB, Cassandra) |
|---|---|---|
| **Schema** | Rigid, enforced | Flexible, schema-on-read |
| **Query** | Complex queries, JOINs, aggregations | Simple lookups, limited query patterns |
| **Scaling** | Vertical first, sharding is complex | Horizontal scaling built-in |
| **Consistency** | Strong by default (ACID) | Eventually consistent (tunable) |
| **Best for** | Complex relationships, ad-hoc queries | High write throughput, simple access patterns |

The answer in system design is almost never "use NoSQL because it scales." It's "what are the access patterns, consistency requirements, and query complexity?"

---

## 4. Cloud Computing Basics

### Core Concepts

```
Region:           Geographic area (us-east-1, eu-west-1)
Availability Zone: Isolated datacenter within a region (us-east-1a, us-east-1b)
VPC:              Virtual Private Cloud — your isolated network in the cloud
Subnet:           Subdivision of a VPC (public subnets for load balancers, private for databases)
Security Group:   Stateful firewall rules (allow port 443 from 0.0.0.0/0)
IAM:              Identity and Access Management (who can do what)
```

### Common Services (AWS Names, Equivalents Exist Everywhere)

| Category | Service | What It Does |
|----------|---------|-------------|
| **Compute** | EC2 | Virtual machines |
| | ECS/EKS | Container orchestration (Docker/Kubernetes) |
| | Lambda | Serverless functions |
| **Storage** | S3 | Object storage (files, images, backups) |
| | EBS | Block storage (disk for EC2) |
| | EFS | Network file system (shared across instances) |
| **Database** | RDS | Managed SQL (Postgres, MySQL) |
| | DynamoDB | Managed NoSQL (key-value) |
| | ElastiCache | Managed Redis/Memcached |
| **Networking** | ALB/NLB | Load balancers (L7/L4) |
| | Route 53 | DNS |
| | CloudFront | CDN |
| **Messaging** | SQS | Message queue |
| | SNS | Pub/sub notifications |
| | Kinesis | Real-time event streaming |
| **Monitoring** | CloudWatch | Logs, metrics, alarms |

### Managed vs Self-Hosted

In system design interviews, prefer managed services unless there's a specific reason not to:
- **Managed**: less operational burden, automatic backups, scaling, patching. More expensive per unit.
- **Self-hosted**: full control, cheaper at scale, requires dedicated ops/SRE effort.

---

## 5. Distributed Systems Concepts

### Why Distribution Is Hard

A single server is simple: one database, one process, one source of truth. The moment you add a second server, everything gets complicated:

- **Network partitions**: servers can't reach each other. Which one is "right"?
- **Clock skew**: servers disagree on what time it is. Event ordering becomes ambiguous.
- **Partial failures**: one server succeeds, another fails. How do you reconcile?

### CAP Theorem

You can have at most two of three:

```
Consistency:   Every read receives the most recent write (or an error)
Availability:  Every request receives a response (even if stale)
Partition Tolerance: The system operates despite network splits
```

In practice, network partitions happen, so you're choosing between **CP** (consistent but might be unavailable during partitions) and **AP** (always available but might return stale data).

- **CP examples**: PostgreSQL with synchronous replication, ZooKeeper, etcd
- **AP examples**: DynamoDB (default), Cassandra, DNS

Most real systems are tunable along this spectrum, not strictly one or the other.

### Consistency Models

| Model | Guarantee | Example |
|-------|-----------|---------|
| **Strong consistency** | Reads always see the latest write | Single-leader SQL, Spanner |
| **Eventual consistency** | Reads may see stale data, but eventually converge | DynamoDB, DNS, CDN caches |
| **Read-your-writes** | You see your own writes immediately, others may lag | Session-sticky routing |
| **Causal consistency** | If A causes B, everyone sees A before B | Some distributed databases |

**Choosing the right consistency model:** Strong consistency is the simplest to reason about but the most expensive in latency and availability. Use it for financial transactions, inventory counts, and any case where stale reads cause incorrect behavior. Eventual consistency is appropriate when showing slightly stale data is acceptable (user profile views, product catalog browsing, social media timelines). Read-your-writes is a pragmatic middle ground for user-facing applications -- the user always sees their own changes immediately, which feels correct even if other users see the change seconds later.

### Replication

Replication serves two purposes: fault tolerance (survive node failure) and read scaling (distribute read load). The choice of replication strategy depends on your consistency requirements and whether you need multi-region writes.

```
Leader-Follower (Primary-Replica):
  - All writes go to the leader
  - Leader replicates to followers
  - Reads can go to followers (eventual consistency) or leader (strong consistency)
  - Failover: promote a follower to leader if leader dies

Multi-Leader:
  - Multiple nodes accept writes
  - Must handle write conflicts (last-write-wins, merge, etc.)
  - Used for multi-datacenter deployments

Leaderless (Dynamo-style):
  - Any node accepts reads and writes
  - Quorum: write to W nodes, read from R nodes, if W + R > N, you get consistency
  - Used by Cassandra, DynamoDB
```

**When to choose each:** Leader-follower is the default for most applications because it avoids write conflicts entirely. Multi-leader is necessary when you need low-latency writes in multiple geographic regions (accepting the complexity of conflict resolution). Leaderless is best when you need high write availability and can tolerate tunable consistency -- common for large-scale, write-heavy workloads like IoT data or activity feeds.

### Load Balancing

A load balancer distributes incoming traffic across multiple servers to improve throughput, reduce latency, and provide fault tolerance. It is the first component to add when scaling beyond a single server.

```
Client → Load Balancer → Server 1
                       → Server 2
                       → Server 3

Algorithms:
  Round-robin:        rotate through servers sequentially
  Least connections:  send to the server with fewest active connections
  Weighted:           distribute based on server capacity
  IP hash:            same client IP always goes to the same server (sticky sessions)
  Random:             surprisingly effective at scale
```

**When to choose each algorithm:** Round-robin is the simplest default when servers are homogeneous. Least-connections works better when request durations vary (long-running vs short requests). Weighted round-robin handles heterogeneous server sizes. IP hash is needed when sessions must be sticky (though stateless design eliminates this need). Random with two choices (pick two servers, send to the one with fewer connections) performs nearly as well as least-connections with less coordination overhead.

---

## 6. Containers (Docker Basics)

### What Docker Does

A container is a lightweight, isolated process with its own filesystem, network, and process tree. Not a VM — it shares the host kernel.

```dockerfile
# Dockerfile
FROM node:20-slim           # base image
WORKDIR /app                # set working directory
COPY package*.json ./       # copy dependency files
RUN npm ci                  # install dependencies (cached layer)
COPY . .                    # copy source code
RUN npm run build           # build the app
EXPOSE 3000                 # document the port
CMD ["node", "dist/index.js"]  # run command
```

```bash
docker build -t myapp .     # build image
docker run -p 3000:3000 myapp  # run container, map port
```

### Why Docker Matters for System Design

- **Reproducibility**: same image runs the same everywhere (dev, staging, prod)
- **Isolation**: dependencies don't conflict between services
- **Scaling**: orchestrators (Kubernetes) create/destroy containers in seconds
- **Immutability**: deploy a new image, don't patch running servers

---

## 7. Security Basics

### Authentication vs Authorization

```
Authentication (AuthN): WHO are you?
  → Credentials: password, token, certificate, biometric
  → Result: identity (user ID, session)

Authorization (AuthZ): WHAT can you do?
  → Policies: roles, permissions, ACLs
  → Result: allow or deny a specific action
```

### Common Auth Patterns

**Session-based authentication** stores user state on the server. It is simple and well-understood but requires a session store that all servers can access (Redis, database). This makes it harder to scale horizontally.

```
Session-based:
  Client → POST /login (credentials)
  Server → Set-Cookie: session_id=abc123
  Client → GET /api/data (Cookie: session_id=abc123)
  Server → lookup session in store → identify user
```

**Token-based authentication (JWT)** stores user state in the token itself. The server does not need to look up sessions -- it just verifies the token signature. This makes it stateless and easy to scale, but tokens cannot be revoked before expiry without maintaining a deny-list (which re-introduces server-side state).

```
Token-based (JWT):
  Client → POST /login (credentials)
  Server → { "token": "eyJhbG..." }
  Client → GET /api/data (Authorization: Bearer eyJhbG...)
  Server → verify token signature → extract claims → identify user
```

**OAuth2** delegates authentication to a trusted identity provider (Google, GitHub). You never handle the user's password directly. Use this when you want "Sign in with Google" or need to access third-party APIs on behalf of the user.

```
OAuth2:
  User → redirect to Google/GitHub
  Google → redirect back with authorization code
  Your server → exchange code for access token
  Your server → use token to get user info from Google
```

### HTTPS / TLS

- **TLS** encrypts data in transit between client and server
- **Certificates** prove the server is who it claims to be (signed by Certificate Authorities)
- **HSTS**: tell browsers to always use HTTPS (no downgrade attacks)
- In system design: TLS termination usually happens at the load balancer, internal traffic may or may not be encrypted (defense in depth says encrypt it)

### Encryption

Encryption protects data in three distinct dimensions. Each addresses a different threat model, and a production system typically needs all three.

```
At rest:    data stored on disk is encrypted (AES-256, managed keys or KMS)
In transit: data moving over the network is encrypted (TLS)
Field-level: specific sensitive fields encrypted separately (PII, passwords)

Passwords: NEVER store plaintext. Use bcrypt/scrypt/argon2 (slow hashing).
API keys:  store the hash, show the key once on creation.
```

**Why all three matter:** Encryption at rest protects against physical disk theft or unauthorized access to storage volumes. Encryption in transit prevents network eavesdropping. Field-level encryption limits the blast radius of a database compromise -- even if an attacker accesses the database, they cannot read encrypted fields without the separate encryption key. In practice, cloud providers handle at-rest encryption transparently (e.g., S3 default encryption, EBS encryption), TLS 1.3 handles in-transit encryption, and field-level encryption is your responsibility for the most sensitive data (Social Security numbers, payment card numbers, health records).

---

## 8. Observability Basics

### The Three Pillars

```
Logs:    Discrete events with context
         "User 123 failed login attempt from IP 10.0.0.5 at 2024-01-15T10:30:00Z"

Metrics: Numeric measurements over time
         request_count{path="/api/users", status="200"} = 1523
         response_time_p99{path="/api/users"} = 230ms

Traces:  End-to-end request flow across services
         Request abc-123:
           → API Gateway (2ms)
             → Auth Service (15ms)
             → User Service (45ms)
               → PostgreSQL (30ms)
```

### Key Metrics

**RED Method** (for request-driven services):
- **R**ate: requests per second
- **E**rrors: error rate (percentage of failed requests)
- **D**uration: latency distribution (p50, p95, p99)

**USE Method** (for resources — CPU, memory, disk, network):
- **U**tilization: percentage of resource in use
- **S**aturation: work queued because resource is full
- **E**rrors: error count for the resource

### SLIs, SLOs, SLAs

```
SLI (Service Level Indicator):  a metric — "99.2% of requests complete in < 200ms"
SLO (Service Level Objective):  a target — "99.9% of requests should complete in < 200ms"
SLA (Service Level Agreement):  a contract — "if we miss the SLO, we owe you credits"
```

---

## 9. Back-of-Envelope Estimation

These numbers come up constantly in system design interviews.

### Quick Math

```
1 million requests/day  ≈  12 requests/second
1 billion requests/day  ≈  12,000 requests/second

1 KB  ×  1 million  =  1 GB
1 MB  ×  1 million  =  1 TB

Characters in a tweet:  280 chars ≈ 280 bytes
Average web page:       2 MB
Average photo:          200 KB - 5 MB
Average video minute:   50 MB (compressed)
```

### Storage Estimation Example

```
"Design a URL shortener handling 100M new URLs/month"

Storage per URL:
  - Short URL:      7 bytes
  - Original URL:   100 bytes (average)
  - Created at:     8 bytes
  - User ID:        8 bytes
  - Total:          ~130 bytes

Monthly:  100M × 130 bytes = 13 GB/month
5 years:  13 GB × 60 months = 780 GB ≈ 1 TB

Conclusion: fits on a single database with room to spare.
```

---

## 10. Quick Checklist

Before starting Module 01, you should be able to answer:

- [ ] Walk through what happens when you type a URL in a browser (DNS → TCP → TLS → HTTP → response)
- [ ] What's the difference between TCP and UDP? When would you use each?
- [ ] What are ACID properties? Give an example of why atomicity matters.
- [ ] What's a database index? What's the trade-off?
- [ ] Explain CAP theorem. Give a CP and AP example.
- [ ] What's the difference between a process and a thread?
- [ ] What's the difference between strong and eventual consistency?
- [ ] What's leader-follower replication? What happens when the leader dies?
- [ ] What's a load balancer? Name three algorithms.
- [ ] Estimate: how many requests per second is 1 billion requests per day?

If any of these are shaky, re-read that section. Module 01's system design framework builds directly on this vocabulary.

---

## Related Reading

This module provides the foundational vocabulary used throughout the rest of the course. As you work through later modules, refer back here when concepts come up:

- [Module 01: System Design Framework Essentials](01-system-design-framework/01-system-design-framework-essentials.md) -- applies these fundamentals to a structured interview approach, including back-of-the-envelope estimation using the latency numbers covered here
- [Module 02: SQL, NoSQL, and Decision Framework](02-databases-at-scale/01-sql-nosql-and-decision-framework.md) -- expands on the database fundamentals (ACID, indexing, SQL vs NoSQL) introduced in Section 3
- [Module 02: Indexing, Sharding, and Replication](02-databases-at-scale/02-indexing-sharding-and-replication.md) -- goes deep on the indexing and replication concepts introduced here
- [Module 03: Caching Patterns and Redis Basics](03-caching/01-caching-patterns-and-redis-basics.md) -- builds on the caching concepts from Section 8 (Observability and Operations) and the latency numbers that motivate caching
- [Module 04: Message Brokers](04-message-queues/01-message-brokers-kafka-sqs-rabbitmq.md) -- covers the async processing patterns that build on the concurrency and distributed systems concepts from Sections 2 and 5
- [Module 05: Load Balancing Fundamentals](05-load-balancing/01-load-balancing-fundamentals.md) -- expands on load balancing algorithms and health checks introduced in Section 5
- [Module 06: Docker and Containerization](06-containers-orchestration/01-docker-and-containerization.md) -- dives deeper into the container concepts (namespaces, cgroups) mentioned in Section 6
- [Module 09: Authentication and Authorization](09-security/01-authentication-and-authorization.md) -- builds on the security basics (TLS, encryption, zero trust) from Section 7
- [Module 10: Classic Design Problems](10-classic-problems/01-classic-design-problems.md) -- applies all of these fundamentals to end-to-end system design problems

---

## Next Steps

You're ready for [Module 01: System Design Framework](01-system-design-framework/README.md) — a repeatable framework for any system design interview, from requirements gathering to deep dives.
