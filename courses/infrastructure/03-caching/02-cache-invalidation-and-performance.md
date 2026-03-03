# Module 03: Cache Invalidation and Performance

## Cache Invalidation Strategies

Cache invalidation is famously one of the two hard problems in computer science. Here is a structured approach.

### TTL-Based

Set expiry on every entry. Simple, requires no coordination. Stale for up to TTL duration.

**Heuristics**: User profiles 5-15 min, product catalog 1-5 min, feature flags 30-60 sec, sessions match session expiry, static config 1 hour+.

### Event-Based

Invalidate in response to data change events. Immediate, but requires event infrastructure.

```python
async def update_user(user_id, data):
    await db.update_user(user_id, data)
    await redis.delete(f"user:{user_id}")
    await event_bus.publish("user.updated", {"user_id": user_id})
```

### Write-Through Invalidation

Update cache as part of the write. Prefer **delete on write** over update to avoid race conditions with concurrent writes.

### Pub/Sub Invalidation

Broadcast invalidation across instances via Redis pub/sub. Essential for keeping in-process L1 caches synchronized.

```python
await redis.publish("cache:invalidate", json.dumps({"key": "user:123"}))
```

### Cache Invalidation Decision Tree

```
Data changed -- how to invalidate?
├── Immutable (versioned assets)? --> Versioned URLs. No invalidation needed.
├── Need read-after-write consistency? --> Write-through.
├── Can tolerate staleness?
│   ├── Seconds --> Short TTL (30-60s)
│   ├── Minutes --> TTL (5-15 min) + event-based invalidation
│   └── No --> Event-based invalidation (delete on write + pub/sub)
├── Multiple services cache this? --> Publish event to message bus + TTL safety net.
└── Multiple instances of same service? --> Redis pub/sub for L1 invalidation.
```

---

## Cache Stampede Prevention

When a popular cache entry expires, many concurrent requests simultaneously hit the database.

### Mutex / Locking

One request acquires a lock, loads data, others wait and retry.

```python
async def get_with_lock(key, loader, ttl=3600):
    value = await redis.get(key)
    if value: return value

    if await redis.set(f"lock:{key}", "1", nx=True, ex=10):
        try:
            value = await loader()
            await redis.set(key, value, ex=ttl)
            return value
        finally:
            await redis.delete(f"lock:{key}")
    else:
        await asyncio.sleep(0.05)
        return await get_with_lock(key, loader, ttl)
```

### Probabilistic Early Expiration (XFetch)

Recompute with probability that increases as TTL decreases. Statistically ensures one request refreshes before expiry.

```python
remaining_ttl = expiry - time.time()
if remaining_ttl - beta * math.log(random.random()) <= 0:
    value = await loader()
    await redis.set(key, value, ex=ttl)
```

### Request Coalescing

Multiple concurrent requests for the same key share a single backend request. Same concept as Go's `singleflight`.

```python
_in_flight: dict[str, asyncio.Future] = {}

async def get_coalesced(key: str, loader):
    value = await redis.get(key)
    if value:
        return value

    if key in _in_flight:
        return await _in_flight[key]  # Wait for in-flight request

    future = asyncio.get_event_loop().create_future()
    _in_flight[key] = future
    try:
        value = await loader()
        await redis.set(key, value, ex=3600)
        future.set_result(value)
        return value
    except Exception as e:
        future.set_exception(e)
        raise
    finally:
        del _in_flight[key]
```

All concurrent callers share one backend request. Especially effective for hot keys during cache warm-up or after invalidation.

**Choosing a strategy**: Use mutex/locking when simplicity matters. Use probabilistic early expiration for high-traffic keys where you want zero-downtime refreshes. Use request coalescing when many concurrent requests hit the same key simultaneously (common in high-QPS systems).

---

## Cache Warming

Pre-load cache before traffic arrives. Strategies:

1. **From database**: Query top-N most active entities on startup, pipeline SET commands.
2. **From access logs**: Analyze recent access patterns, pre-populate top keys.
3. **From another cache**: Clone data during migration via SCAN + SET.

Warm after: deployments, cache flushes, infrastructure changes, anticipated traffic spikes.

```python
async def warm_cache():
    # Query top 10K active users, pipeline SET for efficiency
    popular_users = await db.query(
        "SELECT * FROM users ORDER BY last_active_at DESC LIMIT 10000"
    )
    pipeline = redis.pipeline()
    for user in popular_users:
        pipeline.set(f"user:{user.id}", user.to_json(), ex=3600)
    await pipeline.execute()
    logger.info(f"Warmed {len(popular_users)} user cache entries")
```

**Pipeline for performance**: Batching SET commands via pipeline avoids per-command round-trip overhead. Warming 10K keys takes ~100ms with pipelining vs ~10 seconds with individual commands.

**Gradual warming**: In high-traffic systems, avoid warming all at once (spike in DB load). Spread the warming over minutes, or use the existing cache-aside pattern and let traffic warm the cache organically by accepting a brief period of higher miss rates.

---

## Multi-Level Caching

```
Request --> [ L1: In-Process ] --> HIT (< 1us)
                  |  MISS
            [ L2: Redis ]      --> HIT (< 1ms)
                  |  MISS
            [ Database ]       --> (5-50ms)
```

**L1**: Fastest, small capacity, per-process, not shared. **L2**: Shared across instances, larger capacity, network hop.

**Invalidation across levels**: Short L1 TTL (5-30s), pub/sub for L1 invalidation when L2 changes, version stamping.

```python
class MultiLevelCache:
    def __init__(self):
        self.l1 = LRUCache(max=1000, ttl=30_000)
        self.l2 = redis_client

    async def get(self, key, loader):
        value = self.l1.get(key)
        if value is not None: return value

        value = await self.l2.get(key)
        if value is not None:
            self.l1.set(key, value)
            return value

        value = await loader()
        await self.l2.set(key, value, ex=3600)
        self.l1.set(key, value)
        return value

    async def invalidate(self, key):
        self.l1.delete(key)
        await self.l2.delete(key)
        await self.l2.publish("cache:invalidate", key)
```

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

### Working Set Analysis

Estimate from access logs how many unique keys are accessed within your TTL window. If your cache can hold the working set, hit rate will be high.

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

---

## Interview Questions

### Conceptual

1. **Design a caching layer for a personalized feed API that updates every few minutes.**

   Cache-aside with TTL (2-5 min), cache key includes user ID, stale-while-revalidate for UX, invalidate on new post/follow events, discuss per-user vs. shared caching tradeoffs.

2. **Explain consistency guarantees of each caching pattern.**

   Cache-aside: stale window until TTL/invalidation. Write-through: strongly consistent. Write-behind: eventually consistent with data loss risk.

3. **How do you handle cache invalidation across microservices?**

   Event-driven invalidation (Kafka/SNS), pub/sub, impossibility of perfect cross-service consistency, TTL as safety net.

4. **Walk through Redis Cluster resharding when adding a node.**

   Hash slot migration, MOVED/ASK redirections, client library handling, latency impact, slot distribution planning.

5. **A cache entry with 1-hour TTL is accessed at 10K req/sec. TTL expires. What happens?**

   Cache stampede. Solutions: mutex/locking, probabilistic early expiration, request coalescing, stale-while-revalidate.

### System Design

6. **Caching strategy for e-commerce catalog: 10M products, 100K QPS reads, 100 QPS writes.**

   CDN for product HTML (versioned URLs), Redis cache-aside (5 min TTL), in-process cache for top 1000 products, event-based invalidation on updates, cache warming for seasonal products.

7. **Inconsistent data between cache and database. How do you debug and fix?**

   Check race conditions, missing invalidation paths, TTL too long, key collisions, serialization issues. Fix: delete-on-write instead of update, event-based invalidation as backup.

8. **Design a rate limiter using Redis. Handle Redis unavailability.**

   Sliding window counter or token bucket. Fallback: fail-open vs. fail-closed (context-dependent), local in-memory rate limiter.

### Coding

9. **Implement cache-aside with stampede prevention.**

   Lock acquisition, timeout, fallback to stale data, error handling, TTL management.

10. **Write a multi-level cache with L1/L2 and cross-instance invalidation.**

    Pub/sub for L1 invalidation, proper TTL at both levels, clean abstraction, L2 unavailability handling.

---

## Related Reading

- [Module 03: Caching Patterns and Redis Basics](01-caching-patterns-and-redis-basics.md) -- the foundational caching patterns (cache-aside, write-through, write-behind) that determine your invalidation needs
- [Module 03: Advanced Caching Systems](03-advanced-caching-systems.md) -- stampede prevention mechanisms (mutex, XFetch, leases) that build on the invalidation strategies covered here
- [Module 04: Message Brokers](../04-message-queues/01-message-brokers-kafka-sqs-rabbitmq.md) -- event-driven cache invalidation often uses message brokers (Kafka, SNS) to propagate invalidation signals across services
- [Module 05: Advanced Load Balancing Patterns](../05-load-balancing/03-advanced-load-balancing-patterns.md) -- CDN caching architecture (edge PoPs, origin shield, cache hierarchies) extends the CDN caching concepts covered here
- [Module 08: Logging, Metrics, and Tracing](../08-observability/01-logging-metrics-and-tracing.md) -- cache hit rate is the north star metric; use Prometheus histograms to track hit/miss rates, latency distributions, and eviction counts

---

## Key Takeaways

1. **Delete on write, never update in place.** Updating the cache value on write introduces race conditions with concurrent readers. Deleting is safe -- the next reader will load fresh data.

2. **TTL is the safety net, not the primary invalidation strategy.** Use event-based invalidation for timely consistency. Use TTL to handle missed events.

3. **Hit rate is the north star metric.** Every other metric (latency, throughput, cost) flows from it.

4. **Not all misses are equal.** Categorize into cold, capacity, and conflict misses to identify root causes and the right fix.

5. **Cache sizing is empirical, not theoretical.** Simulate with production access logs. The relationship between cache size and hit rate follows a curve that depends on your specific access pattern distribution.

6. **Fragmentation is the silent killer.** A Redis instance using 4GB of data but consuming 8GB of RSS needs attention. Active defragmentation or planned restarts during low-traffic windows address this.
