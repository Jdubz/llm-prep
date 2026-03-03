# 03 – Performance and Scaling

## Memory Profiling

### tracemalloc (Built-in)

Python's built-in memory tracer — no external tools needed. Useful for finding memory leaks.

```python
import tracemalloc

def start_memory_profiling():
    """Call on startup to enable memory tracking."""
    tracemalloc.start(25)  # Store 25 frames of traceback

def get_memory_snapshot():
    """Take a snapshot and return top allocations."""
    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics("lineno")
    return [
        {"file": stat.traceback.format()[0], "size_kb": stat.size / 1024, "count": stat.count}
        for stat in stats[:20]
    ]

def compare_snapshots(snapshot1, snapshot2):
    """Compare two snapshots to find leaks."""
    stats = snapshot2.compare_to(snapshot1, "lineno")
    for stat in stats[:10]:
        print(stat)
```

Expose it as a protected debug endpoint:

```python
@app.get("/debug/memory", include_in_schema=False)
async def memory_profile(api_key: str = Header(...)):
    if api_key != settings.debug_api_key:
        raise HTTPException(status_code=403)
    return get_memory_snapshot()
```

### objgraph (Object Reference Graphs)

```python
import objgraph

# Find most common object types
objgraph.show_most_common_types(limit=20)

# Find objects growing over time (potential leaks)
objgraph.show_growth(limit=10)

# Visualize what's holding a reference to an object
objgraph.show_backrefs(
    objgraph.by_type("MyModel")[:3],
    filename="refs.png",
    max_depth=5,
)
```

### Common Python Memory Leaks

| Leak Pattern | Description | Fix |
|-------------|-------------|-----|
| Growing lists/dicts in module scope | Global caches that never evict | Use `functools.lru_cache(maxsize=N)` or `cachetools.TTLCache` |
| Closures capturing large objects | Lambda/function references keep objects alive | Weak references or restructure |
| Event handler accumulation | Adding handlers without removing them | Track handlers, remove on cleanup |
| SQLAlchemy session not closed | Objects in the identity map hold references | Use `async with` for sessions |
| Circular references with `__del__` | GC can't collect cycles with finalizers | Avoid `__del__`, use `weakref.finalize` |

---

## CPU Profiling

### cProfile (Built-in)

```python
import cProfile
import pstats
from io import StringIO

def profile_function(func, *args, **kwargs):
    """Profile a specific function call."""
    profiler = cProfile.Profile()
    profiler.enable()
    result = func(*args, **kwargs)
    profiler.disable()

    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumulative")
    stats.print_stats(20)
    print(stream.getvalue())
    return result
```

### py-spy (Production CPU Profiling)

`py-spy` is the Python equivalent of `0x` or `clinic.js` for Node.js — it samples the call stack without stopping the process.

```bash
# Profile a running process (attach by PID)
py-spy top --pid 12345

# Generate a flame graph (SVG)
py-spy record -o profile.svg --pid 12345 --duration 30

# Profile a command
py-spy record -o profile.svg -- python -m uvicorn app.main:app

# Show which lines are hot (line-level profiling)
py-spy dump --pid 12345
```

**Key insight for Node.js developers**: In Node.js, the event loop is single-threaded so a CPU profile shows everything. In Python, `py-spy` shows you all threads — you can see the main thread, Uvicorn's event loop thread, and any worker threads separately. Look for GIL contention: if multiple threads are waiting on the GIL, you have a CPU-bound bottleneck.

### Profiling Middleware (Slow Request Detection)

```python
import time
import structlog

logger = structlog.get_logger()

class ProfilingMiddleware:
    def __init__(self, app, threshold_ms: float = 1000):
        self.app = app
        self.threshold_ms = threshold_ms

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        await self.app(scope, receive, send)
        duration_ms = (time.perf_counter() - start) * 1000

        if duration_ms > self.threshold_ms:
            logger.warning("slow_request", path=scope["path"], duration_ms=duration_ms)
```

---

## Async Profiling Challenges

### The Problem

Traditional profilers (cProfile) measure wall-clock time per function call. In async code, a function might take 500ms of wall time but only 1ms of CPU time — the rest is `await`ing IO. The profiler attributes the full 500ms to the function, which is misleading.

### Solutions

```python
# 1. Use py-spy in "idle" mode to see where time is spent waiting
# py-spy record --idle --pid 12345 -o profile.svg

# 2. Use OpenTelemetry spans for logical profiling — identifies actual CPU work
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

async def get_user_with_orders(user_id: str):
    with tracer.start_as_current_span("get_user_with_orders"):
        with tracer.start_as_current_span("fetch_user"):
            user = await db.get_user(user_id)
        with tracer.start_as_current_span("fetch_orders"):
            orders = await db.get_orders(user_id)
        with tracer.start_as_current_span("enrich_data"):
            # CPU-bound — this is what to optimize
            return enrich_user_data(user, orders)

# 3. yappi — a profiler that understands async/threading
import yappi

yappi.set_clock_type("wall")  # or "cpu" for CPU-only time
yappi.start()
# ... run your workload ...
yappi.stop()
stats = yappi.get_func_stats()
stats.sort("ttot")
stats.print_all(columns={"name": 60, "ncall": 10, "ttot": 10, "tsub": 10})
```

---

## A/B Testing Infrastructure

### Deterministic Variant Assignment

```python
# app/ab_testing.py
import hashlib
from dataclasses import dataclass

@dataclass
class Experiment:
    name: str
    variants: list[str]  # e.g., ["control", "variant_a", "variant_b"]
    traffic_percent: float  # 0.0 to 1.0

def assign_variant(experiment: Experiment, user_id: str) -> str:
    """Deterministic variant assignment using consistent hashing.
    Same user always gets the same variant.
    """
    hash_input = f"{experiment.name}:{user_id}"
    hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16)

    bucket = (hash_value % 10000) / 10000
    if bucket > experiment.traffic_percent:
        return "control"

    variant_index = hash_value % len(experiment.variants)
    return experiment.variants[variant_index]

async def track_exposure(experiment_name: str, variant: str, user_id: str, analytics_client):
    await analytics_client.track(
        event="experiment_exposure",
        properties={"experiment": experiment_name, "variant": variant, "user_id": user_id},
    )

async def get_experiment_variant(
    experiment_name: str,
    user: User = Depends(get_current_user),
) -> str:
    experiment = await get_experiment(experiment_name)
    variant = assign_variant(experiment, user.id)
    await track_exposure(experiment_name, variant, user.id, analytics)
    return variant
```

For production, prefer a dedicated feature flag service (LaunchDarkly, Unleash) — statistical analysis, targeting rules, and dashboards are worth the cost.

---

## Interview Questions

### Docker and Deployment

**1. Why would you choose `python:3.12-slim` over `python:3.12-alpine` for a FastAPI Docker image?**

Alpine uses musl libc instead of glibc. Many Python packages distribute pre-built binary wheels for manylinux (glibc), but not for musl. With alpine, packages like `psycopg2`, `numpy`, or `cryptography` must be compiled from source, requiring build tools in the image and dramatically increasing build time. The slim image is ~70 MB larger but avoids these issues entirely. This is a key difference from Node.js, where alpine is a safe default because Node itself and most npm packages are pure JavaScript or ship musl-compatible binaries.

**2. Explain the relationship between Gunicorn and Uvicorn in a production FastAPI deployment.**

Gunicorn is a process manager (prefork server) that spawns and manages multiple worker processes. Uvicorn is an ASGI server that runs the async event loop within each worker. When you use `worker_class = "uvicorn.workers.UvicornWorker"`, Gunicorn handles process lifecycle (spawning, killing, restarting workers) while each worker runs a Uvicorn event loop that handles async request processing. This is analogous to PM2 running multiple Node.js processes in cluster mode, except each Python process has its own event loop rather than sharing one.

**3. How do you calculate the right number of Gunicorn workers?**

The classic formula is `(2 * CPU_cores) + 1`, but this is for synchronous workers. For async Uvicorn workers, each worker already handles thousands of concurrent connections via the event loop, so you need fewer — typically `CPU_cores` or even less. In Kubernetes, the preferred approach is 1-2 workers per pod and scaling horizontally with pod replicas, because K8s already handles process-level redundancy and load balancing. The exact number should be tuned based on workload: CPU-bound work benefits from more workers (up to the core count), while IO-bound async work needs fewer.

### Observability

**4. How would you propagate a request ID through all log messages in a FastAPI application?**

Use structlog with Python's `contextvars` module. In middleware, generate or extract a request ID, then call `structlog.contextvars.bind_contextvars(request_id=request_id)`. All subsequent log calls within that request's async context will automatically include the request ID, even across `await` boundaries and nested function calls. This is Python's equivalent of Node.js `AsyncLocalStorage` — the context follows the async execution chain. Clear the context at the start of each request with `structlog.contextvars.clear_contextvars()` to prevent leaking between requests.

**5. What metrics would you monitor for a production FastAPI service?**

The RED method covers the essentials: **Rate** (requests per second by endpoint), **Errors** (5xx rate, should be below SLO threshold), and **Duration** (p50/p95/p99 latency). Beyond RED, monitor saturation metrics: database connection pool utilization (approaching pool size is an emergency), memory RSS trend (for leak detection), CPU usage (for capacity planning), and active async tasks (pile-up indicates downstream issues). Business metrics are equally important: key transaction rates, authentication failures, and upstream dependency health.

### Configuration and Security

**6. How does `pydantic-settings` compare to using dotenv in Node.js?**

`pydantic-settings` provides everything dotenv does (loading from `.env` files, environment variables) plus type validation, default values, nested configuration support, and secrets file loading. It validates on startup — if `DATABASE_URL` is missing or `PORT` is not an integer, the application fails immediately with a clear error rather than crashing later at runtime. It's like combining `dotenv` with `zod` schema validation, but built into the framework ecosystem. It also supports loading secrets from mounted files (`/run/secrets/`), which is important for Kubernetes and Docker Swarm.

**7. Describe a graceful shutdown sequence for a production FastAPI service behind a load balancer.**

First, the load balancer (or Kubernetes) stops sending new traffic (readiness probe fails or pod is removed from endpoints). Then SIGTERM is sent to Gunicorn, which forwards it to workers. Each Uvicorn worker stops accepting new connections and waits for in-flight requests to complete (up to `graceful_timeout`). FastAPI's lifespan `shutdown` event fires, where you close database pools, flush metrics, and complete any pending background tasks. Finally, the process exits. In Kubernetes, `terminationGracePeriodSeconds` must exceed Gunicorn's `graceful_timeout` — otherwise the pod is SIGKILLed before graceful shutdown completes.

### Production Debugging

**8. A production FastAPI endpoint is intermittently slow (p99 latency spike). How do you debug it?**

Start with distributed tracing (OpenTelemetry/Jaeger) — look at slow traces to identify which span is taking the longest. Common culprits: (1) database queries without proper indexing (check query plans), (2) connection pool exhaustion (all connections busy, new requests wait for one), (3) GIL contention from CPU-bound work in async handlers, (4) slow external API calls without timeouts. Use `py-spy` for production CPU profiling without stopping the process. Check Prometheus metrics for correlation — did the latency spike coincide with increased traffic, a deployment, or a database migration? If it's async-related, check for accidentally blocking the event loop with synchronous calls.

**9. How would you implement zero-downtime deployments for a FastAPI service?**

Use rolling deployments in Kubernetes: set `maxSurge: 1` and `maxUnavailable: 0` so new pods start before old ones terminate. The startup probe ensures new pods are ready before receiving traffic. The readiness probe removes pods from the service endpoints before they shut down. Set `terminationGracePeriodSeconds` higher than your application's graceful shutdown timeout. For database migrations, use a separate migration job that runs before the deployment and ensure migrations are backward-compatible (never drop a column that old code still reads). For critical services, consider blue-green deployments where you can instantly switch back to the previous version if issues arise.

---

## Key Takeaways

- `tracemalloc` is built-in and sufficient for finding most memory leaks; `objgraph` helps visualize reference graphs for stubborn leaks.
- `py-spy` profiles running production processes with no code changes and no downtime — the production equivalent of `0x` in Node.js.
- Traditional profilers mislead for async code: 500ms wall time may be 1ms CPU time. Use OTel spans or `yappi` for accurate async profiling.
- A/B testing needs deterministic hashing (sha256 of `experiment:user_id`) so the same user always gets the same variant.
- The RED method + saturation metrics (pool utilization, memory RSS, active tasks) covers operational observability completely.
- Zero-downtime deployments require: startup/readiness probes, `maxUnavailable: 0`, backward-compatible migrations, and `terminationGracePeriodSeconds > graceful_timeout`.
