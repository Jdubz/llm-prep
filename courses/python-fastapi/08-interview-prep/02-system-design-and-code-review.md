# 02 – System Design and Code Review

## System Design Template for Python APIs

### 1. Requirements (2 min)

- Functional requirements (what does it do?)
- Non-functional (latency, throughput, availability)
- Scale (users, requests/sec, data size)

### 2. API Design (3 min)

```
POST /resource          → Create (201)
GET  /resource          → List (200, paginated)
GET  /resource/{id}     → Get (200 / 404)
PATCH /resource/{id}    → Update (200 / 404)
DELETE /resource/{id}   → Delete (204 / 404)
```

### 3. Data Model (3 min)

- SQLAlchemy models + Pydantic schemas
- Mention: indexes, constraints, relationships

### 4. Architecture (5 min)

```
Client → FastAPI → PostgreSQL (primary store)
                → Redis (cache / queue)
                → S3 (files)
                → Workers (async processing)
```

### 5. Python-Specific Decisions (3 min)

- Async vs sync endpoints
- Connection pooling (SQLAlchemy async pool)
- Background tasks vs task queue (Celery/ARQ)
- CPU-bound work: `ProcessPoolExecutor`

### 6. Scale and Production (4 min)

- Kubernetes + HPA
- Database read replicas
- Caching strategy (Redis TTL)
- Monitoring (RED metrics, Prometheus)

---

## System Design Examples

### Design 1: URL Shortener API

**Requirements**: Shorten URLs, redirect, track clicks, analytics.

```
┌─────────┐     ┌──────────┐     ┌─────────┐
│  Client  │────▶│  FastAPI  │────▶│  Redis   │ (hot cache)
└─────────┘     │  Service  │     └─────────┘
                │           │────▶┌─────────┐
                └──────────┘     │ Postgres │ (persistent store)
                      │          └─────────┘
                      ▼
                ┌──────────┐
                │ Analytics │ (async — Kafka/Redis stream)
                └──────────┘
```

```python
# URL shortening: base62 encoding of a hash
import hashlib

def generate_short_code(url: str, length: int = 7) -> str:
    hash_bytes = hashlib.sha256(url.encode()).digest()
    num = int.from_bytes(hash_bytes[:8], "big")
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    code = ""
    while num and len(code) < length:
        code += chars[num % 62]
        num //= 62
    return code

@app.post("/shorten", response_model=ShortenedURL)
async def shorten(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    code = generate_short_code(request.url)
    await redis.setex(f"url:{code}", 86400, request.url)
    ...

@app.get("/{code}")
async def redirect(
    code: str,
    background_tasks: BackgroundTasks,
    redis: Redis = Depends(get_redis),
):
    url = await redis.get(f"url:{code}")
    if not url:
        url = await db_lookup(code)
    if not url:
        raise HTTPException(404)

    # Fire-and-forget analytics (don't block redirect)
    background_tasks.add_task(record_click, code)
    return RedirectResponse(url, status_code=301)
```

**Scale discussion points**:
- Redis for hot URLs (most redirects hit cache)
- Postgres for durability
- Background tasks for click analytics (or Kafka for high volume)
- Rate limiting on `/shorten` to prevent abuse
- Pre-generated ID pool to avoid hash collisions under high write load

### Design 2: Notification Service

**Requirements**: Send notifications via email, SMS, push. Support templates, scheduling, preferences.

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Producer  │────▶│  FastAPI  │────▶│  Redis    │ (task queue)
│ Services  │     │  Gateway  │     │  (ARQ)    │
└──────────┘     └──────────┘     └─────┬────┘
                                        │
                                  ┌─────▼────┐
                                  │  Workers  │
                                  └─────┬────┘
                            ┌───────────┼───────────┐
                       ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
                       │ Email  │  │  SMS   │  │  Push  │
                       │ (SES)  │  │(Twilio)│  │ (FCM)  │
                       └────────┘  └────────┘  └────────┘
```

```python
@app.post("/notifications/send")
async def send_notification(
    request: NotificationRequest,
    queue: ArqRedis = Depends(get_queue),
):
    job = await queue.enqueue_job(
        "send_notification",
        request.model_dump(),
        _defer_by=request.scheduled_delay,  # Scheduling support
    )
    return {"job_id": job.job_id, "status": "queued"}

# Worker function
async def send_notification(ctx, notification_data: dict):
    notification = NotificationRequest(**notification_data)
    match notification.channel:
        case "email":
            await send_email(notification)
        case "sms":
            await send_sms(notification)
        case "push":
            await send_push(notification)
```

### Design 3: File Processing Pipeline

**Requirements**: Upload files, process (resize images, parse CSVs, generate PDFs), store results.

```python
@app.post("/files/upload")
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    # Stream to S3 (don't load entire file in memory)
    file_key = f"uploads/{uuid4()}/{file.filename}"
    await upload_to_s3_streaming(file.file, file_key)

    job = FileJob(key=file_key, status="pending", filename=file.filename)
    db.add(job)
    await db.commit()

    # Offload heavy processing to a worker
    await task_queue.enqueue("process_file", job_id=job.id)
    return {"job_id": job.id, "status": "processing"}

@app.get("/files/{job_id}/status")
async def file_status(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(FileJob, job_id)
    return {"status": job.status, "result_url": job.result_url}
```

**Python advantage for file processing**: Libraries like Pillow (images), pandas (CSVs), ReportLab (PDFs), and ffmpeg-python (video) are mature and battle-tested. CPU-heavy processing runs in worker processes (Celery/ARQ with ProcessPoolExecutor), keeping the API responsive.

---

## Code Review Checklist

| Category | Check |
|----------|-------|
| **Types** | All function signatures have type hints? |
| **Types** | Pydantic models for all external data (API input/output, config)? |
| **Async** | No blocking calls inside `async def`? (requests, time.sleep, file IO) |
| **Async** | Using `httpx` (async) instead of `requests` (sync)? |
| **Resources** | Database sessions use `async with` or `Depends` with `yield`? |
| **Resources** | HTTP clients are shared (not created per request)? |
| **Security** | No f-strings in SQL queries? (use parameterized queries) |
| **Security** | Passwords hashed with bcrypt/argon2, never stored plaintext? |
| **Security** | Secrets from environment/config, never hardcoded? |
| **Security** | `response_model` used to prevent leaking internal fields? |
| **Errors** | Using `HTTPException` with correct status codes? (not returning error dicts) |
| **Errors** | `is None` instead of `== None`? |
| **Perf** | Filtering/sorting in the database, not in Python? |
| **Perf** | Pagination on all list endpoints? |
| **Perf** | No N+1 queries? (use `selectinload`/`joinedload`) |
| **Style** | `@functools.wraps` on all decorators? |
| **Style** | No mutable default arguments? (`def f(lst=[])` is a bug) |
| **Testing** | Using `dependency_overrides` instead of monkeypatching? |
| **Testing** | Async tests with `pytest-asyncio` and `httpx.AsyncClient`? |

---

## Code Review Exercises

### Exercise 1: Spot the Issues

```python
# BAD — find the problems
@app.get("/users/{user_id}")
async def get_user(user_id):
    db = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()
    if user == None:
        return {"error": "not found"}
    return user
```

**Issues**:
1. `user_id` has no type annotation — no validation, could be any string
2. `db` session is created but never closed — resource leak
3. `user == None` should be `user is None`
4. Returning `{"error": ...}` instead of raising `HTTPException(404)` — wrong status code (200)
5. Returning the ORM model directly — exposes all fields including password
6. Using sync `db.query()` in an `async def` — blocks the event loop

```python
# FIXED
@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Exercise 2: Spot the Issues

```python
# BAD — find the problems
@app.post("/upload")
async def upload(file: UploadFile):
    contents = await file.read()
    data = json.loads(contents)
    for item in data:
        user = User(**item)
        db.add(user)
        await db.commit()
    return {"imported": len(data)}
```

**Issues**:
1. No file size limit — reading entire file into memory could OOM
2. No input validation on `data` items
3. Committing inside the loop — N commits instead of one (slow, no atomicity)
4. No error handling — partial failure leaves inconsistent state
5. `db` appears from nowhere — should be a dependency

```python
# FIXED
@app.post("/upload")
async def upload(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large")

    contents = await file.read()
    try:
        data = json.loads(contents)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    users = [User(**UserCreate.model_validate(item).model_dump()) for item in data]
    db.add_all(users)
    await db.commit()  # Single transaction
    return {"imported": len(users)}
```

### Exercise 3: Spot the Issues

```python
# BAD — find the problems
import requests

@app.get("/external-data")
async def get_external():
    response = requests.get("https://api.example.com/data", timeout=30)
    return response.json()
```

**Issues**:
1. `requests` is synchronous — blocks the entire event loop for up to 30 seconds
2. No error handling for network failures
3. No caching — every call hits the external API
4. 30-second timeout is too generous for an API endpoint

```python
# FIXED
import httpx

http_client = httpx.AsyncClient(timeout=5.0)

@app.get("/external-data")
async def get_external():
    try:
        response = await http_client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Upstream timeout")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"Upstream error: {e.response.status_code}")
```

### Exercise 4: Spot the Issues

```python
# BAD — find the problems
password_cache = {}

@app.post("/login")
async def login(username: str, password: str):
    password_cache[username] = password  # "cache" for faster login next time

    user = await db.execute(
        text(f"SELECT * FROM users WHERE username = '{username}'")
    )
    if user and user.password == password:
        token = jwt.encode({"sub": username}, "secret123")
        return {"token": token}
    return {"error": "invalid credentials"}
```

**Issues**:
1. **SQL injection** — f-string in SQL query
2. **Password stored in plaintext** in a global dict (memory leak + security nightmare)
3. **Plaintext password comparison** — should be bcrypt/argon2 hash comparison
4. **Hardcoded JWT secret** — should be from config/environment
5. **No expiration on JWT**
6. **200 on auth failure** — should be 401

### Exercise 5: Spot the Issues

```python
# BAD — find the problems
@app.get("/search")
async def search(q: str):
    results = []
    all_items = await db.execute(select(Item))
    for item in all_items.scalars().all():
        if q.lower() in item.name.lower():
            results.append(item)
    return results
```

**Issues**:
1. **Loading all items into memory** — does not scale
2. **Filtering in Python** instead of the database — O(n) scan
3. **No pagination** — could return millions of results
4. **No response model** — exposes all fields

```python
# FIXED
@app.get("/search", response_model=PaginatedResponse[ItemOut])
async def search(
    q: str = Query(..., min_length=1, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Item).where(Item.name.ilike(f"%{q}%")).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
```

---

## Live Coding Patterns

### Pattern 1: Complete CRUD Endpoint

```python
"""Build a complete CRUD for a 'Product' resource.
Demonstrate: Pydantic models, dependency injection, error handling, response models.
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/products", tags=["products"])

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    price: float = Field(..., gt=0, le=1_000_000)
    description: str | None = Field(None, max_length=2000)
    category: str = Field(..., min_length=1)

class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    price: float | None = Field(None, gt=0, le=1_000_000)
    description: str | None = Field(None, max_length=2000)
    category: str | None = None

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: float
    description: str | None
    category: str

@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product

@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int = Path(..., gt=0),
    updates: ProductUpdate = ...,
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int = Path(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    product = await db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.commit()
```

### Pattern 2: Pagination

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    has_more: bool

# Offset-based (simple, good for most cases)
@router.get("/", response_model=PaginatedResponse[ProductOut])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    total = (await db.execute(select(func.count()).select_from(Product))).scalar()
    items = (await db.execute(
        select(Product).offset(skip).limit(limit).order_by(Product.id)
    )).scalars().all()
    return PaginatedResponse(items=items, total=total, has_more=skip + limit < total)

# Cursor-based (better for real-time data, no page drift)
@router.get("/stream", response_model=PaginatedResponse[ProductOut])
async def list_products_cursor(
    cursor: int | None = Query(None, description="Last seen product ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Product).order_by(Product.id).limit(limit + 1)
    if cursor:
        query = query.where(Product.id > cursor)

    items = list((await db.execute(query)).scalars().all())
    has_more = len(items) > limit
    items = items[:limit]
    return PaginatedResponse(items=items, total=-1, has_more=has_more)
```

### Pattern 3: Background Task Processor

```python
"""Async task processor with status tracking."""
import asyncio
from enum import Enum
from datetime import datetime
from uuid import uuid4

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

# In-memory store (use Redis in production)
tasks: dict[str, dict] = {}

@app.post("/tasks/", status_code=202)
async def create_task(payload: TaskPayload, background_tasks: BackgroundTasks):
    task_id = str(uuid4())
    tasks[task_id] = {
        "id": task_id,
        "status": TaskStatus.PENDING,
        "created_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None,
    }
    background_tasks.add_task(run_task, task_id, payload)
    return {"task_id": task_id, "status": "pending"}

async def run_task(task_id: str, payload: TaskPayload):
    tasks[task_id]["status"] = TaskStatus.RUNNING
    try:
        result = await heavy_computation(payload)
        tasks[task_id]["status"] = TaskStatus.COMPLETED
        tasks[task_id]["result"] = result
    except Exception as e:
        tasks[task_id]["status"] = TaskStatus.FAILED
        tasks[task_id]["error"] = str(e)

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    if task_id not in tasks:
        raise HTTPException(404)
    return tasks[task_id]
```

### Pattern 4: Rate Limiting Middleware

```python
"""Token bucket rate limiter as FastAPI middleware."""
import time
from collections import defaultdict
from fastapi import Request, HTTPException

class RateLimiter:
    def __init__(self, requests_per_second: float = 10, burst: int = 20):
        self.rate = requests_per_second
        self.burst = burst
        self.tokens: dict[str, float] = defaultdict(lambda: float(burst))
        self.last_check: dict[str, float] = defaultdict(time.monotonic)

    def _get_key(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        return forwarded.split(",")[0] if forwarded else request.client.host

    def is_allowed(self, request: Request) -> bool:
        key = self._get_key(request)
        now = time.monotonic()
        elapsed = now - self.last_check[key]
        self.last_check[key] = now

        # Refill tokens
        self.tokens[key] = min(self.burst, self.tokens[key] + elapsed * self.rate)

        if self.tokens[key] >= 1:
            self.tokens[key] -= 1
            return True
        return False

rate_limiter = RateLimiter(requests_per_second=10, burst=20)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not rate_limiter.is_allowed(request):
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": "1"},
        )
    return await call_next(request)
```

**Production note**: This in-memory rate limiter doesn't work across multiple processes or pods. For production, use Redis with a sliding window counter or token bucket backed by `redis.incr()` with TTL.

---

## Advanced Async Patterns

### Cancellation

Task cancellation in Python is cooperative — it raises `CancelledError` at the next `await` point:

```python
async def cancellable_operation():
    try:
        while True:
            data = await fetch_next_batch()
            await process_batch(data)
    except asyncio.CancelledError:
        await flush_pending_data()  # Cleanup
        raise  # Re-raise to confirm cancellation

# Cancellation with timeout (Python 3.11+)
async def with_timeout():
    try:
        async with asyncio.timeout(5.0):
            result = await long_running_operation()
    except TimeoutError:
        pass

# Shielding from cancellation
async def critical_operation():
    result = await asyncio.shield(save_to_database(data))  # Completes even if parent is cancelled
    return result
```

**The CancelledError gotcha**: In Python 3.9+, `CancelledError` is a subclass of `BaseException`, not `Exception`. `except Exception` won't catch it — cancellation propagates through generic error handlers, which is the correct behavior.

### Structured Concurrency (TaskGroup)

```python
async def fetch_all_data():
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(fetch_user(user_id))
        orders_task = tg.create_task(fetch_orders(user_id))
        prefs_task = tg.create_task(fetch_preferences(user_id))

    # All tasks guaranteed complete here
    # If any task raised an exception: all others are cancelled, ExceptionGroup is raised
    return {
        "user": user_task.result(),
        "orders": orders_task.result(),
        "preferences": prefs_task.result(),
    }

# ExceptionGroup handling (Python 3.11+):
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(might_fail_1())
        tg.create_task(might_fail_2())
except* ValueError as eg:
    for exc in eg.exceptions:
        print(f"ValueError: {exc}")
```

### Async Generators

```python
async def paginated_fetch(url: str, page_size: int = 100):
    """Async generator — yields pages on demand."""
    page = 0
    while True:
        response = await httpx_client.get(url, params={"page": page, "size": page_size})
        data = response.json()
        if not data["items"]:
            break
        yield data["items"]
        page += 1

# Consume lazily
async for page in paginated_fetch("https://api.example.com/users"):
    for user in page:
        await process_user(user)
```

**Cleanup**: If you break out of an `async for` loop early, Python calls `aclose()` on the generator, which triggers any `finally` blocks inside it — important for releasing resources.

---

## FastAPI for ML Model Serving

FastAPI has become the de facto standard for serving ML models:

```python
from contextlib import asynccontextmanager
from pydantic import BaseModel
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model at startup (not per-request)
    app.state.classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased")
    yield
    del app.state.classifier  # Free GPU memory

app = FastAPI(lifespan=lifespan)

class PredictionRequest(BaseModel):
    text: str
    max_length: int = 512

class PredictionResponse(BaseModel):
    label: str
    confidence: float

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    # ML inference is CPU/GPU-bound — run in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # Default thread pool
        lambda: app.state.classifier(request.text[:request.max_length])[0],
    )
    return PredictionResponse(label=result["label"], confidence=round(result["score"], 4))
```

**Why FastAPI for ML serving**: Pydantic validates input before it hits the model (prevents crashes from bad input). Async handling keeps the server responsive while models run in thread pools. Type hints document the expected input/output schema.

---

## Key Takeaways

- Use the system design template: requirements → API design → data model → architecture → Python-specific → scale.
- Code review: blocking IO in `async def`, SQL injection via f-strings, sessions not closed, missing `response_model`, and `== None` instead of `is None` are the most common issues.
- Rate limiting in-memory only works in single-process deployments; use Redis for multi-process/multi-pod setups.
- `TaskGroup` is preferred over `gather` for structured concurrency — it provides guaranteed cleanup and proper error propagation.
- For ML serving: load models at startup (lifespan), run inference in thread pools (CPU/GPU-bound), validate input with Pydantic.
- `CancelledError` is `BaseException`, not `Exception` — never swallow it with `except Exception`.
