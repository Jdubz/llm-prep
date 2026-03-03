# Module 03: Caching Patterns and Redis Basics

## When to Cache

```
Read-to-write ratio > 10:1?           --> Strong candidate
Data can be stale for >= 1 second?     --> Cacheable
Source latency > 5ms?                  --> Meaningful savings
Multiple users access same data?       --> Shared cache (Redis)
Data used within one request only?     --> Request-scoped / DataLoader
Data used within one process only?     --> In-memory LRU
Public and static?                     --> CDN
```

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

### Caching Pattern Comparison

| Pattern | Read Path | Write Path | Consistency | Best For |
|---------|-----------|------------|-------------|----------|
| **Cache-Aside** | App checks cache, miss loads DB | App writes DB, deletes cache | Eventual (stale until TTL) | General-purpose, read-heavy |
| **Read-Through** | Cache loads DB on miss (transparent) | Same as cache-aside | Eventual | Clean abstraction, Java |
| **Write-Through** | Same as cache-aside | Writes to cache AND DB sync | Strong | Read-after-write critical |
| **Write-Behind** | Same as cache-aside | Writes cache, async flush DB | Eventual (data loss risk) | High write throughput |

**Default**: Cache-aside. Write-through only for read-after-write consistency. Write-behind only if write throughput is the bottleneck and data loss is tolerable.

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

```
All data equally important?          --> allkeys-lru (safe default)
Clear hot/cold access patterns?      --> allkeys-lfu
Mix of persistent + cache data?      --> volatile-lru or volatile-lfu
Refuse writes when full?             --> noeviction (data stores only)
Unsure?                              --> allkeys-lru
```

Redis samples `maxmemory-samples` keys (default 5) and evicts the best candidate. Not true LRU/LFU -- approximate. Increase sample size (e.g., 10) for better accuracy at the cost of more CPU.

**LRU vs LFU tradeoffs:**
- **LRU**: Good general default. Favors recently accessed data. Vulnerable to scan patterns that touch many keys once, evicting genuinely hot data.
- **LFU**: Better when you have a stable set of hot keys. Redis uses a logarithmic counter with time-based decay to approximate frequency. Resists scan pollution.

**Practical guidance**: Start with `allkeys-lru`. Switch to `allkeys-lfu` if you observe scan-pattern eviction issues or have a clear power-law access distribution where a small set of keys accounts for most traffic.

### Redis Commands Quick Reference

```bash
# Strings
SET key val [EX sec] [NX|XX]    GET key    MGET k1 k2    INCR key    SETNX key val

# Hashes
HSET key f v [f v ...]    HGET key f    HGETALL key    HINCRBY key f n

# Lists
LPUSH key v    RPUSH key v    LPOP key    RPOP key    LRANGE key 0 -1

# Sets
SADD key m    SISMEMBER key m    SMEMBERS key    SINTER k1 k2    SCARD key

# Sorted Sets
ZADD key score m    ZRANGE key 0 -1 WITHSCORES    ZRANK key m    ZINCRBY key n m

# Keys
DEL key    EXISTS key    EXPIRE key sec    TTL key    SCAN cursor MATCH pattern

# Pub/Sub
PUBLISH ch msg    SUBSCRIBE ch    PSUBSCRIBE pattern

# Transactions
MULTI / EXEC    WATCH key    EVAL "lua" numkeys key arg
```

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

```
Cache-Control: public, max-age=31536000, immutable           # Versioned static assets
Cache-Control: public, max-age=60, stale-while-revalidate=300 # API responses
Cache-Control: private, max-age=300                           # User-specific, browser only
Cache-Control: no-store                                       # Sensitive data
Cache-Control: no-cache                                       # Always revalidate (use with ETag)
Cache-Control: public, max-age=60, s-maxage=3600              # CDN caches longer than browser
Cache-Control: public, max-age=300, stale-if-error=86400      # Serve stale on origin error
```

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

## Cache Sizing Formulas

```
Required Memory = Working_Set_Size * (Avg_Value_Size + 80B overhead) * 1.3 overhead

Example: 100K users, 500B avg JSON, 1hr TTL
  = 100,000 * 580 * 1.3 = 75.4 MB

Hit Rate vs. Cache Size (power-law access):
  100% working set -->  99%+ hit rate
   80%             -->  ~95%
   50%             -->  ~80-90%
   20%             -->  ~60-80%

Avg Response = (hit_rate * cache_latency) + (miss_rate * db_latency)
  95% hit, 0.5ms cache, 20ms DB = 0.475 + 1.0 = 1.475ms
  99% hit                       = 0.495 + 0.2 = 0.695ms  (53% improvement)
```

---

## Key Takeaways

1. **Cache-aside is your default pattern.** Only reach for write-through when you need read-after-write consistency, and write-behind when write throughput is the primary bottleneck.

2. **Negative caching prevents cache penetration.** Always cache misses with a short TTL (30-60s) to prevent repeated DB hits for non-existent keys.

3. **Redis's single-threaded model means blocking commands hurt everyone.** Never use `KEYS *` in production. Use `SCAN` instead.

4. **Hash tags enable multi-key operations in Redis Cluster.** Co-locate related keys using `{prefix}:key` notation.

5. **LRU is a safe default eviction policy.** Switch to LFU only when you observe scan patterns evicting hot data.
