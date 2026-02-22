# Module 03: Caching Strategies

## Table of Contents

1. [Caching Patterns](#caching-patterns)
2. [Redis Architecture](#redis-architecture)
3. [CDN Caching](#cdn-caching)
4. [Application-Level Caching](#application-level-caching)
5. [Cache Invalidation Strategies](#cache-invalidation-strategies)
6. [Cache Stampede Prevention](#cache-stampede-prevention)
7. [Cache Warming](#cache-warming)
8. [Multi-Level Caching](#multi-level-caching)
9. [Interview Questions](#interview-questions)

---

## Caching Patterns

### Cache-Aside (Lazy Loading)

The application manages the cache explicitly: check cache first, on miss load from DB, populate cache.

```python
async def get_user(user_id: str) -> User:
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return User.from_json(cached)

    user = await db.query("SELECT * FROM users WHERE id = $1", user_id)
    if user is None:
        await redis.set(f"user:{user_id}", "NULL", ex=60)  # Cache negative results
        return None

    await redis.set(f"user:{user_id}", user.to_json(), ex=3600)
    return user
```

**Pros:** Only requested data is cached, cache failures are non-fatal, simple mental model.

**Cons:**
- **Cache miss penalty**: First request for any key pays full DB latency. Under cold-start, this cascades into a thundering herd.
- **Stale data**: Direct DB modifications are not reflected until TTL expires.
- **Write complexity**: Application must manage invalidation on writes.

**When to use**: Read-heavy workloads where occasional staleness is acceptable. This is your default.

**Negative caching**: Cache `NULL` or sentinel values for keys that do not exist in the database. Without this, a non-existent key triggers a DB lookup on every request (cache penetration attack vector).

```python
# Cache penetration protection
if user is None:
    await redis.set(f"user:{user_id}", "NULL", ex=60)  # Short TTL for negatives
    return None
```

**Cache key design**: Include all query parameters in the key. `user:{id}` is correct. `user:{id}:{locale}` if locale affects the response. Avoid overly broad keys that return different data for different callers.

---

### Write-Through

Every write updates both cache and database synchronously before returning success.

```python
async def update_user(user_id: str, data: dict) -> User:
    user = User(**data)
    async with db.transaction():
        await db.execute("UPDATE users SET name=$1, email=$2 WHERE id=$3",
                         user.name, user.email, user_id)
        await redis.set(f"user:{user_id}", user.to_json(), ex=3600)
    return user
```

**Consistency guarantees**: Cache and DB are always in sync. Reads see latest written value. No stale window.

**Trade-offs**: Write latency increases (two ops), wasted cache space for write-only data, partial failure handling is complex.

**When to use**: Read-after-write consistency is critical, write volume is moderate. User profile updates, financial systems.

---

### Write-Behind / Write-Back

Writes go to cache immediately; the cache flushes to DB asynchronously in the background.

```python
class WriteBehindCache:
    def __init__(self):
        self.write_buffer = asyncio.Queue()

    async def write(self, key: str, value: str):
        await redis.set(key, value)
        await self.write_buffer.put((key, value))

    async def flush_loop(self):
        while True:
            batch = []
            try:
                while len(batch) < 100:
                    item = await asyncio.wait_for(self.write_buffer.get(), timeout=1.0)
                    batch.append(item)
            except asyncio.TimeoutError:
                pass
            if batch:
                async with db.transaction():
                    await db.executemany(
                        "INSERT INTO data (key, value) VALUES ($1, $2) "
                        "ON CONFLICT (key) DO UPDATE SET value = $2", batch)
```

**Performance**: Sub-millisecond write latency, batched DB writes, absorbs write spikes.

**Data loss risk**: Cache crash before flush loses buffered writes. Mitigate with Redis AOF (`appendfsync everysec`), short flush intervals, write-ahead logs.

**When to use**: High write throughput, tolerable brief data loss. Analytics, counters, leaderboards.

---

### Read-Through

The cache itself loads data from DB on a miss. The application only talks to the cache.

```java
LoadingCache<String, User> userCache = Caffeine.newBuilder()
    .maximumSize(10_000)
    .expireAfterWrite(Duration.ofHours(1))
    .build(userId -> userRepository.findById(userId));

User user = userCache.get(userId);  // Transparent loading on miss
```

**Pros**: Cleaner application code, centralized loading logic. **Cons**: Tighter coupling to data source, less flexibility for complex queries.

**When to use**: Java ecosystems with Caffeine/Guava/EhCache that have strong read-through support.

---

## Redis Architecture

### Single-Threaded Model

Redis processes commands on a single main thread. This is deliberate: no lock contention, predictable latency, atomic operations without synchronization.

```
Client connections (multiplexed via epoll/kqueue)
         |
   [ I/O Threads ]  <-- Redis 6+ parallelizes network read/write
         |
   [ Main Thread ]  <-- All command execution is single-threaded
         |
   [ Background Threads ]  <-- Lazy deletion, AOF fsync, RDB snapshots
```

A single `KEYS *` or `SMEMBERS` on a huge set blocks everything. Always use `SCAN`/`SSCAN` in production. A single node handles 100K-200K ops/sec for simple GET/SET.

### Redis Cluster

Redis Cluster partitions data across multiple nodes using **16,384 hash slots**. Each key maps to a slot via `CRC16(key) mod 16384`.

```
Node A: slots 0-5460     |  Node B: slots 5461-10922  |  Node C: slots 10923-16383
```

**Hash Tags**: `{user:123}:profile` and `{user:123}:settings` both hash on `user:123`, landing on the same node. Required for multi-key operations.

**Resharding** (live migration): Source marks slots as MIGRATING, target as IMPORTING. Keys migrate one by one. During migration, source sends ASK redirects for already-moved keys. Clients must handle MOVED and ASK redirections.

### Redis Sentinel

Provides HA for non-clustered Redis: monitoring, automatic failover, configuration provider.

**Failover**: Sentinel detects master down (SDOWN), quorum agrees (ODOWN), leader elected via Raft-like consensus, best replica promoted to master. Minimum 3 Sentinels across different failure domains.

### Persistence

**RDB Snapshots**: Point-in-time snapshots via `fork()` + copy-on-write. Compact, fast to load, but data loss window = time since last snapshot. `fork()` causes latency spikes on large datasets.

**AOF**: Logs every write. `appendfsync everysec` gives max 1 second data loss. Larger files, slower restart. AOF rewriting compacts the log.

**Production**: Enable both. RDB for fast restarts/backups. AOF for minimal data loss.

### Eviction Policies

| Policy | Behavior | Use Case |
|--------|----------|----------|
| `noeviction` | Return errors when full | Data stores, not caches |
| `allkeys-lru` | Evict least recently used | General-purpose caching (default) |
| `allkeys-lfu` | Evict least frequently used | Stable hot/cold access patterns |
| `volatile-lru` | LRU among keys with TTL | Mixed persistent + cache data |
| `volatile-ttl` | Shortest TTL first | When TTL reflects priority |

Redis samples `maxmemory-samples` keys (default 5) and evicts the best candidate. Not true LRU/LFU -- approximate. Increase sample size (e.g., 10) for better accuracy at the cost of more CPU.

**LRU vs LFU tradeoffs:**

- **LRU**: Good general default. Favors recently accessed data. Vulnerable to scan patterns that touch many keys once, evicting genuinely hot data.
- **LFU**: Better when you have a stable set of hot keys. Redis uses a logarithmic counter with time-based decay to approximate frequency. Resists scan pollution.

**Practical guidance**: Start with `allkeys-lru`. Switch to `allkeys-lfu` if you observe scan-pattern eviction issues or have a clear power-law access distribution where a small set of keys accounts for most traffic.

---

## CDN Caching

### Edge Caching

CDN places cache servers at edge POPs close to users. Cache static assets (JS, CSS, images) with long TTL + versioned URLs. Cache API responses with short TTL or stale-while-revalidate. Do not cache personalized content or mutations.

### Origin Shield

An intermediate cache between edge POPs and origin. Without it, N edge misses = N origin hits. With it, the shield absorbs duplicate requests. Adds one hop on complete miss but dramatically reduces origin load.

### Cache-Control Headers

```
Cache-Control: public, max-age=3600, s-maxage=86400      # CDN caches longer
Cache-Control: no-store                                    # No caching at all
Cache-Control: no-cache                                    # Cache but always revalidate
Cache-Control: public, max-age=3600, stale-while-revalidate=300  # Serve stale while refreshing
```

| Directive | Meaning |
|-----------|---------|
| `public` / `private` | Any cache vs. browser only |
| `max-age=N` / `s-maxage=N` | Fresh duration (browser / CDN override) |
| `no-cache` / `no-store` | Must revalidate / do not cache |
| `stale-while-revalidate=N` | Serve stale for N seconds while fetching fresh |
| `immutable` | Content will never change |

### Cache Invalidation at the Edge

**Purge**: Explicitly remove cached objects (by URL, by surrogate tag, or purge all). Propagation: 1-30 seconds.

**Versioned URLs**: `/styles.abc123.css` becomes `/styles.def456.css`. No invalidation needed; old URL never requested again. Works for build assets, not API endpoints.

**stale-while-revalidate**: Serve stale immediately while fetching fresh in background. Best for content where minutes of staleness is acceptable.

---

## Application-Level Caching

### In-Memory Caches

```javascript
import { LRUCache } from 'lru-cache';
const configCache = new LRUCache({ max: 500, ttl: 1000 * 60 * 5 });
```

Sub-microsecond access, no serialization. Limited to single process, not shared across instances. Use for: config, feature flags, hot metadata.

### Request-Scoped Caches

Cache for the duration of one HTTP request. Prevents redundant DB calls when multiple resolvers need the same entity (GraphQL N+1). Facebook's DataLoader is the canonical implementation.

### Memoization

Cache pure function return values by arguments. Watch for memory leaks with unbounded memoization and many unique argument combinations.

### HTTP Caching

**ETags**: Content fingerprint. Client sends `If-None-Match`, server returns `304 Not Modified` if unchanged. Content-based, precise.

**Last-Modified**: Timestamp-based. Second-level granularity. Client sends `If-Modified-Since`.

Use ETags for APIs, Last-Modified for static files.

**Cache-Control + ETag combination** (most robust pattern for APIs):

```
# Server response
Cache-Control: no-cache          # Always revalidate
ETag: "a1b2c3d4"                 # Content fingerprint

# Client subsequent request
If-None-Match: "a1b2c3d4"

# Server response (if unchanged)
304 Not Modified                 # No body, saves bandwidth
```

This pattern ensures clients always have fresh data while avoiding redundant data transfer. The server computes ETags cheaply (hash of serialized response or database row version).

---

## Cache Invalidation Strategies

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

### Probabilistic Early Expiration

XFetch algorithm: recompute with probability that increases as TTL decreases. Statistically ensures one request refreshes before expiry.

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
