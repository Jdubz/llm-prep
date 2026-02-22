# Module 03: Caching Strategies -- Deep Dive

## Table of Contents

1. [Redis Internals](#redis-internals)
2. [Redis Streams for Event Sourcing](#redis-streams-for-event-sourcing)
3. [Redis Modules](#redis-modules)
4. [Memcached vs Redis](#memcached-vs-redis)
5. [Caching in Microservices](#caching-in-microservices)
6. [Cache Coherence Protocols](#cache-coherence-protocols)
7. [Facebook's Caching Architecture](#facebooks-caching-architecture)
8. [Cache Performance Measurement](#cache-performance-measurement)

---

## Redis Internals

### Event Loop

Redis uses a single-threaded event loop built on its `ae` library (similar to libuv but simpler).

```
┌─────────────────────────────────────────────┐
│              ae Event Loop                   │
│                                              │
│  1. aeProcessEvents()                        │
│     ├── Check time events (cron, TTL)        │
│     ├── epoll_wait / kqueue (I/O events)     │
│     ├── Read client commands, parse, queue    │
│     ├── Execute commands (single-threaded)    │
│     └── Write responses                      │
│                                              │
│  2. beforeSleep()                            │
│     ├── AOF flush, pending replies           │
│     └── Incremental key expiration           │
└─────────────────────────────────────────────┘
```

**I/O threading (Redis 6+):** I/O threads parallelize socket reads/writes. Main thread still executes all commands sequentially. ~2x throughput improvement on network-bound workloads.

**Key expiration:** Lazy (check on access) + Active (sample 20 TTL keys 10 times/sec, repeat if >25% expired).

### Data Structure Implementations

Redis adapts internal encoding based on data size for memory efficiency.

**Strings:** Small integers (0-9999) use shared pool. Short strings (<=44 bytes): `embstr` (single allocation). Longer: `raw` (two allocations). SDS (Simple Dynamic Strings) replaces C strings for O(1) length and binary safety.

**Lists:** Small (<128 elements, <64 bytes each): **listpack** (contiguous, cache-friendly). Large: **quicklist** (doubly linked list of compressed listpacks).

**Hashes:** Small: **listpack**. Large: **hashtable** with incremental rehashing.

**Sets:** Small integer sets: **intset** (sorted array). Otherwise: **hashtable**.

**Sorted Sets:** Small: **listpack**. Large: **skiplist + hashtable**. Skiplist gives O(log N) range queries; hashtable gives O(1) score lookups.

```
Skiplist (simplified):
Level 3:  HEAD ──────────────── 50 ──────────── NIL
Level 2:  HEAD ── 10 ──────── 50 ── 70 ──────── NIL
Level 1:  HEAD ── 10 ── 20 ── 30 ── 50 ── 70 ── 80 ── 90 ── NIL
```

### Memory Optimization

- **Object sharing**: Integers 0-9999 shared across all data structures.
- **Encoding transitions**: Auto-promoted when thresholds exceeded. Tune via `hash-max-listpack-entries`, `zset-max-listpack-entries`, etc.
- **Use hashes for small objects** instead of separate keys (saves per-key overhead).
- **Compress values**: MessagePack or Protobuf instead of JSON for large values.
- **Short key names** at scale: `u:123` saves 3 bytes vs `user:123` -- matters at billions of keys.
- **Always set maxmemory + eviction policy** or the OOM killer will terminate Redis.

**Memory analysis commands:**

```bash
redis-cli MEMORY USAGE user:123           # Per-key memory
redis-cli INFO memory                      # Aggregate stats
redis-cli --bigkeys                        # Find biggest keys per type
redis-cli MEMORY DOCTOR                    # Automated recommendations
```

**Fragmentation**: When `mem_fragmentation_ratio` (RSS / used_memory) exceeds 1.5, Redis is wasting significant memory on fragmentation. Common causes: high key churn (many creates/deletes), variable-size values. Mitigate with `activedefrag yes` (Redis 4.0+) or schedule off-peak restarts.

**Encoding inspection**: Use `OBJECT ENCODING key` to see what internal encoding Redis is using for a key. If you expect a hash to use listpack but it has been promoted to hashtable, check if your values exceed `hash-max-listpack-value`.

---

## Redis Streams for Event Sourcing

Redis Streams provide an append-only log suitable for event sourcing and message streaming.

```bash
XADD orders * event order_created order_id 1001 amount 99.99
XRANGE orders - +                          # Read all
XREAD BLOCK 5000 STREAMS orders $          # Blocking tail

# Consumer groups (cooperative consumption)
XGROUP CREATE orders processing-group 0
XREADGROUP GROUP processing-group consumer-1 COUNT 10 BLOCK 2000 STREAMS orders >
XACK orders processing-group 1609459200-0  # Acknowledge
```

**Event sourcing fit**: Immutable ordered events, consumer groups for at-least-once delivery, PEL for crash recovery, `XTRIM` for bounded growth.

**Limitations vs. Kafka**: No built-in partitioning, no cross-datacenter replication, smaller ecosystem, suitable for tens of thousands (not millions) of events/sec.

**When to use Streams over Kafka**: You already have Redis in your stack, moderate event volume, need the simplicity of a single infrastructure component, and do not need cross-datacenter replication or advanced stream processing.

**Practical considerations**: Set `MAXLEN` or `MINID` trimming to prevent unbounded growth. Use `XPENDING` to monitor unacknowledged messages and detect stuck consumers. Implement a claim mechanism (`XCLAIM`) to reassign messages from dead consumers.

```bash
# Monitor pending messages
XPENDING orders processing-group - + 10

# Claim messages from dead consumer after 60s idle
XCLAIM orders processing-group consumer-2 60000 1609459200-0
```

---

## Redis Modules

**RedisJSON**: Native JSON storage with path-based queries and partial updates. `JSON.SET user:123 $.age 31` -- no serialize/deserialize entire blob.

**RediSearch**: Full-text search and secondary indexing. `FT.SEARCH idx:users "@name:Alice @age:[25 35]"`. Good for autocomplete, faceted search without Elasticsearch.

**RedisGraph**: Graph database with Cypher queries (now deprecated in favor of FalkorDB fork).

**Module considerations**: Redis modules run inside the Redis process. A buggy module can crash Redis. Evaluate maturity and community support before deploying modules in production. Redis Stack bundles the most popular modules (JSON, Search, TimeSeries) for easier deployment. If you need only one or two module capabilities, consider whether a dedicated system (Elasticsearch for search, a document DB for JSON) would be more robust.

---

## Memcached vs Redis

| Dimension | Memcached | Redis |
|-----------|-----------|-------|
| Data types | Strings only | Strings, lists, sets, sorted sets, hashes, streams |
| Threading | Multi-threaded | Single-threaded execution (I/O threads v6+) |
| Persistence | None | RDB + AOF |
| Replication | None natively | Master-replica |
| Clustering | Client-side consistent hashing | Native hash slots |
| Max value | 1MB | 512MB |
| Pub/Sub | No | Yes |
| Eviction | LRU only | LRU, LFU, random, volatile-TTL |
| Throughput | Higher for simple get/set | Slightly lower single-node |

**Choose Memcached**: Pure caching, uniform-size values, need multi-threaded throughput, legacy integration.

**Choose Redis**: Data structures beyond strings, persistence, pub/sub, Lua scripting. Essentially every new project.

**Migration path**: If you are running Memcached and considering Redis, the migration is straightforward for simple get/set workloads. Both use similar client libraries. The main risk is Memcached's slab allocator providing more predictable memory behavior for uniform-size values, while Redis's jemalloc can fragment under certain workloads. Monitor `mem_fragmentation_ratio` after migration.

**Hybrid deployment**: Some organizations run both. Memcached for high-throughput simple caching (session stores with uniform size), Redis for data-structure-heavy use cases (sorted set leaderboards, pub/sub, Lua scripting). This adds operational complexity but can be justified at extreme scale.

---

## Caching in Microservices

### Distributed Cache Consistency

```
User Service caches user data (TTL: 5 min)
Order Service caches user data (TTL: 5 min)
User updates email -> User Service invalidates own cache
Order Service still has stale email for up to 5 minutes.
```

**Solutions (simplest to most robust):**

1. **Short TTLs**: 30-60 seconds for cross-service data. Accept staleness.
2. **Event-driven invalidation**: Services publish domain events on changes. Consumers subscribe and invalidate. Eventually consistent, convergence is fast.
3. **Shared cache with ownership**: All services use shared Redis. Only the owning service writes to its keys.

**Anti-pattern**: Caching data from another service's API with no invalidation strategy. Always have one.

**Cache-per-service vs. shared cache:**

| Approach | Pros | Cons |
|----------|------|------|
| Cache per service | Full autonomy, no shared failure domain | Data duplication, harder cross-service consistency |
| Shared Redis cluster | Single source of truth, no duplication | Shared infrastructure dependency, noisy neighbor risk |
| Shared with namespacing | Balance of both, ownership via key prefix | Requires discipline, still shared failure domain |

The trend in mature microservices architectures is toward cache-per-service with event-driven invalidation. This aligns with service autonomy principles while providing reasonable consistency through domain events.

---

## Cache Coherence Protocols

Hardware's MESI protocol maps to distributed systems:

| MESI State | Distributed Equivalent |
|------------|----------------------|
| Modified | Write-behind cache with unflushed writes |
| Exclusive | Only one instance has this key cached |
| Shared | Multiple instances have read copies |
| Invalid | Cache entry deleted/expired |

**Strategies in practice:**
1. **Invalidation-based**: Notify all caches to delete on write. Most common in web systems.
2. **Update-based**: Push new value to all caches. Higher bandwidth, no miss on next read.
3. **Lease-based**: Caches acquire time-limited leases. Writes check outstanding leases. Facebook's approach.

**Why this matters for distributed systems engineers**: Understanding coherence protocols helps you reason about cache consistency guarantees. When someone says "our cache is eventually consistent," you can ask: "What is the convergence mechanism? Invalidation-based (TTL + events)? Update-based (write-through propagation)? What is the maximum stale window?" These are the questions that separate surface-level caching from production-grade caching.

---

## Facebook's Caching Architecture

### Memcache at Facebook

Billions of requests/sec across multiple data centers (2013 NSDI paper).

**Key innovations:**

1. **Leases**: Token issued on cache miss, required for set. Prevents thundering herds and stale sets -- if key was invalidated between miss and set, lease is revoked.
2. **mcrouter**: Proxy handling connection pooling, consistent hashing, replication, failover, request batching.
3. **Regional pools**: All web servers share one Memcache pool per region. Cross-region consistency via master region invalidation (mcsqueal).
4. **Gutter pools**: Spare servers absorb traffic during primary failures, preventing thundering herd on database.

### TAO (The Associations and Objects)

Graph-aware caching between application and MySQL. Models Objects `(id) -> (type, data)` and Associations `(id1, type, id2) -> (data, time)`.

Read-through caching with write-through invalidation. Read-after-write consistency within a region, eventual consistency across regions. Inverse association caches updated on both sides of edge creation.

**Lessons from Facebook's architecture applicable to any scale:**

- **Leases solve stampede + stale set simultaneously.** Consider this pattern when you see both thundering herd and race conditions.
- **A proxy layer (mcrouter) decouples apps from cache topology.** Your application should not know how many cache servers exist or how they are sharded.
- **Gutter pools (spare capacity) are cheaper than database over-provisioning.** Always plan for cache failure as a normal operating condition.
- **Cross-region consistency is fundamentally hard.** Facebook chose eventual consistency with master-region writes. This is the pragmatic choice for global systems.

---

## Cache Performance Measurement

### Key Metrics

**Hit Rate**: `Hits / (Hits + Misses)`. Target >95% general, >99% hot paths, <80% indicates problems.

**Miss categorization**: Cold miss (never cached), capacity miss (evicted), conflict miss (TTL/invalidated).

**Latency**: Track p50/p99 separately for hits and misses. `avg = hit_rate * cache_latency + miss_rate * db_latency`.

**Memory**: Monitor `used_memory`, `mem_fragmentation_ratio` (>1.5 = fragmentation), eviction rate.

### Cache Simulation

Replay production access logs against different configurations to predict hit rates without deploying:

```python
def simulate_lru_cache(access_log, cache_size):
    cache = OrderedDict()
    hits = misses = 0
    for key in access_log:
        if key in cache:
            hits += 1
            cache.move_to_end(key)
        else:
            misses += 1
            cache[key] = True
            if len(cache) > cache_size:
                cache.popitem(last=False)
    return hits / (hits + misses)
```

Answers: "If we double Redis memory, how much does hit rate improve?" Often non-linear -- 2x memory might take hit rate from 92% to 98% (75% reduction in misses).

**A/B testing cache configurations**: Route a percentage of traffic to different cache settings (different TTL, eviction policy, cache size) and compare hit rates, latency, and downstream load. This is the most reliable way to tune cache parameters in production.

**Working set analysis**: Estimate from access logs how many unique keys are accessed within your TTL window. If your cache can hold the working set, hit rate will be high.

```python
def estimate_working_set(access_log, window_hours=1):
    cutoff = datetime.now() - timedelta(hours=window_hours)
    unique_keys = {e.key for e in access_log if e.timestamp > cutoff}
    avg_value_size = 500  # bytes, from sampling
    estimated_memory = len(unique_keys) * (avg_value_size + 80)  # 80B per key overhead
    return len(unique_keys), estimated_memory
```

### Monitoring Dashboard Essentials

1. Hit rate over time (alert <90% for 5 min)
2. Latency p50/p95/p99 for hits and misses
3. Memory usage vs. maxmemory (alert at 80%)
4. Eviction rate (alert if sustained >100/sec)
5. Connection count and rejected connections
6. Command rate by type + slow log entries
7. Replication lag (alert if >1MB behind)

### Key Takeaways for Interviews

When discussing cache performance in interviews, demonstrate that you think in terms of:

- **Hit rate is the north star metric.** Every other metric (latency, throughput, cost) flows from it.
- **Not all misses are equal.** Categorize into cold, capacity, and conflict misses to identify root causes.
- **Cache sizing is empirical, not theoretical.** Simulate with production access logs. The relationship between cache size and hit rate follows a curve that depends on your specific access pattern distribution.
- **Monitoring is not optional.** A cache without monitoring is a liability. You cannot tune what you do not measure. Set alerts on hit rate drops and eviction rate spikes before they become incidents.
- **Fragmentation is the silent killer.** A Redis instance using 4GB of data but consuming 8GB of RSS needs attention. Active defragmentation or planned restarts during low-traffic windows address this.
