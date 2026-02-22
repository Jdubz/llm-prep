# Module 03: Caching Strategies -- Cheat Sheet

## Caching Pattern Comparison

| Pattern | Read Path | Write Path | Consistency | Best For |
|---------|-----------|------------|-------------|----------|
| **Cache-Aside** | App checks cache, miss loads DB | App writes DB, deletes cache | Eventual (stale until TTL) | General-purpose, read-heavy |
| **Read-Through** | Cache loads DB on miss (transparent) | Same as cache-aside | Eventual | Clean abstraction, Java |
| **Write-Through** | Same as cache-aside | Writes to cache AND DB sync | Strong | Read-after-write critical |
| **Write-Behind** | Same as cache-aside | Writes cache, async flush DB | Eventual (data loss risk) | High write throughput |

**Default**: Cache-aside. Write-through only for read-after-write consistency. Write-behind only if write throughput is the bottleneck and data loss is tolerable.

---

## Redis Commands Quick Reference

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

## Cache-Control Header Reference

```
Cache-Control: public, max-age=31536000, immutable           # Versioned static assets
Cache-Control: public, max-age=60, stale-while-revalidate=300 # API responses
Cache-Control: private, max-age=300                           # User-specific, browser only
Cache-Control: no-store                                       # Sensitive data
Cache-Control: no-cache                                       # Always revalidate (use with ETag)
Cache-Control: public, max-age=60, s-maxage=3600              # CDN caches longer than browser
Cache-Control: public, max-age=300, stale-if-error=86400      # Serve stale on origin error
```

---

## Cache Invalidation Decision Tree

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

## Eviction Policy Comparison

```
All data equally important?          --> allkeys-lru (safe default)
Clear hot/cold access patterns?      --> allkeys-lfu
Mix of persistent + cache data?      --> volatile-lru or volatile-lfu
Refuse writes when full?             --> noeviction (data stores only)
Unsure?                              --> allkeys-lru
```

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

## Quick Decision: Do I Need a Cache?

```
Read-to-write ratio > 10:1?           --> Strong candidate
Data can be stale for >= 1 second?     --> Cacheable
Source latency > 5ms?                  --> Meaningful savings
Multiple users access same data?       --> Shared cache (Redis)
Data used within one request only?     --> Request-scoped / DataLoader
Data used within one process only?     --> In-memory LRU
Public and static?                     --> CDN
```
