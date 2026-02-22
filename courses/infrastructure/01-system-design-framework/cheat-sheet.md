# Module 01 Cheat Sheet: System Design Framework

## The 4-Step Framework

```
Step 1: Requirements & Scope          (5-7 min)
  - Functional: What does it do? (3-5 features, confirm scope)
  - Non-functional: What constraints? (latency, availability, consistency)
  - Scope exclusions: What are you NOT designing?

Step 2: Back-of-Envelope Estimation   (3-5 min)
  - QPS (read and write, average and peak)
  - Storage (per record x records/day x 365 x years)
  - Bandwidth (QPS x payload size)
  - Cache size (20% of daily unique reads x record size)
  - Server count (peak QPS / QPS per server)

Step 3: High-Level Design             (10-15 min)
  - API design (endpoints, methods, request/response)
  - Data model (tables, indexes, key decisions)
  - Architecture diagram (boxes and arrows, data flow)

Step 4: Deep Dive                     (15-20 min)
  - Pick 2-3 hardest components
  - For each: options, trade-offs, decision, failure modes
```

---

## Estimation Formulas

### QPS

```
Read QPS  = (DAU x reads_per_user_per_day) / 86,400
Write QPS = (DAU x writes_per_user_per_day) / 86,400
Peak QPS  = Average QPS x 2..5 (typically 3x)
```

### Storage

```
Storage/year = writes_per_day x 365 x bytes_per_record
5-year total = Storage/year x 5
```

### Bandwidth

```
Inbound  = Write QPS x avg_request_size
Outbound = Read QPS x avg_response_size
```

### Cache Memory

```
Cache = daily_unique_reads x 0.2 x avg_record_size
(80/20 rule: 20% of data serves 80% of reads)
```

### Servers

```
Servers = Peak QPS / throughput_per_server
Simple lookups:     5,000-10,000 QPS/server
Moderate compute:   1,000-5,000 QPS/server
Heavy compute:      100-1,000 QPS/server
```

---

## Non-Functional Requirements Checklist

Always consider these. Identify which 2-3 are in tension.

- [ ] **Latency** -- p50? p99? What is the user tolerance?
- [ ] **Availability** -- 99.9%? 99.99%? What is the business impact of downtime?
- [ ] **Consistency** -- Strong? Eventual? What staleness is tolerable?
- [ ] **Durability** -- Can any data be lost? Financial data vs analytics?
- [ ] **Throughput** -- Read QPS? Write QPS? Read:write ratio?
- [ ] **Scalability** -- Expected growth in 1, 3, 5 years?
- [ ] **Security** -- PII? Encryption? Compliance?
- [ ] **Cost** -- Budget constraints? Build vs buy?

---

## Design Template

Use this as a starting structure for any system design:

```
1. Requirements
   - Core features: [list 3-5]
   - Non-functionals: [latency, availability, consistency targets]
   - Scope out: [what you are NOT designing]

2. Estimation
   - QPS: [read] / [write] (peak: [read] / [write])
   - Storage: [X] TB over [Y] years
   - Cache: [X] GB

3. API
   - [METHOD] [path] -> [description]
   - [METHOD] [path] -> [description]

4. Data Model
   - [table/collection]: [key fields, indexes]

5. Architecture
   - [diagram with labeled components and data flow]

6. Deep Dives
   - Component A: [options, trade-off, decision]
   - Component B: [options, trade-off, decision]

7. Scaling & Failure
   - Bottlenecks: [what breaks first]
   - Failure modes: [what happens when X fails]
   - Evolution: [how this changes at 10x, 100x]
```

---

## Numbers Every Engineer Should Know

### Latency

| Operation | Time |
|-----------|------|
| L1 cache reference | 0.5 ns |
| L2 cache reference | 7 ns |
| Main memory reference | 100 ns |
| SSD random read | 16 us |
| SSD sequential read (1 MB) | 49 us |
| HDD sequential read (1 MB) | 825 us |
| Network round trip (same datacenter) | 0.5 ms |
| Network round trip (same region, different AZ) | 1-2 ms |
| Network round trip (cross-region, US) | 40-80 ms |
| Network round trip (cross-continent) | 100-200 ms |

### Throughput

| Component | Typical Throughput |
|-----------|--------------------|
| Single Redis instance | 100K-200K ops/sec |
| Single PostgreSQL (simple queries) | 10K-50K QPS |
| Single MySQL (simple queries) | 10K-50K QPS |
| Kafka partition | 10K-100K msgs/sec |
| Kafka cluster | 1M+ msgs/sec |
| Nginx (static) | 50K-100K req/sec |
| Application server (moderate logic) | 1K-10K req/sec |

### Storage & Scale

| Unit | Value |
|------|-------|
| 1 KB | Short email, JSON record |
| 1 MB | Small image, 1 minute of MP3 |
| 1 GB | ~250K photos, 1 hour of HD video |
| 1 TB | ~1 billion simple DB rows |
| 1 PB | ~1,000 TB |

### Availability

| SLA | Downtime/year | Downtime/month |
|-----|---------------|----------------|
| 99% | 3.65 days | 7.3 hours |
| 99.9% | 8.76 hours | 43.8 minutes |
| 99.95% | 4.38 hours | 21.9 minutes |
| 99.99% | 52.6 minutes | 4.38 minutes |
| 99.999% | 5.26 minutes | 26.3 seconds |

### Quick Conversions

```
1 day    = 86,400 seconds (~10^5)
1 month  = 2.6 million seconds (~2.5 x 10^6)
1 year   = 31.5 million seconds (~3 x 10^7)
1 million requests/day = ~12 QPS
1 billion requests/day = ~12,000 QPS
```

---

## Common Building Blocks

| Component | When to Use |
|-----------|------------|
| **Load Balancer** | Always (L7 for HTTP, L4 for TCP/UDP) |
| **CDN** | Static content, globally distributed users |
| **Cache (Redis)** | Read-heavy, latency-sensitive |
| **Message Queue (Kafka/SQS)** | Async processing, decoupling, buffering |
| **SQL Database** | Relational data, ACID transactions, complex queries |
| **NoSQL (DynamoDB)** | Key-value access, massive scale, flexible schema |
| **Object Storage (S3)** | Files, images, videos, backups |
| **Search Index (ES)** | Full-text search, faceted search |
| **API Gateway** | Auth, rate limiting, routing, versioning |
| **Service Mesh** | Service-to-service communication, observability |
