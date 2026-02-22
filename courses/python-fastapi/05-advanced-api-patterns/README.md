# Module 05: Advanced API Patterns

## Prerequisites

You should be comfortable with FastAPI fundamentals (routing, dependency injection, Pydantic models)
and async Python before tackling this module. If you've built Express/NestJS APIs with middleware,
WebSockets, and background jobs, every concept here has a direct analogue — but the Python
ecosystem makes different trade-offs that are worth understanding deeply.

---

## 1. Background Tasks

### FastAPI's Built-in `BackgroundTasks`

The simplest option. Think of it like `setImmediate()` — the work runs in the same process,
after the response is sent.

```python
from fastapi import BackgroundTasks, FastAPI

app = FastAPI()

def send_welcome_email(email: str, name: str) -> None:
    print(f"Sending welcome email to {email}")

@app.post("/users/", status_code=201)
async def create_user(email: str, name: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_welcome_email, email, name)
    return {"email": email, "name": name}
```

**Key details:** Tasks run in the event loop (async) or thread pool (sync). No retry mechanism.
No persistence — tasks die if the process restarts. Multiple tasks execute in order.

### Celery — The Heavyweight

Python's BullMQ equivalent. Distributed task queue with a broker (Redis/RabbitMQ) and result backend.

```python
from celery import Celery

celery_app = Celery("worker", broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_video(self, video_id: str) -> dict:
    try:
        return {"status": "done", "video_id": video_id}
    except TransientError as exc:
        raise self.retry(exc=exc)

# In FastAPI
@app.post("/videos/process")
async def start_processing(video_id: str):
    task = process_video.delay(video_id)
    return {"task_id": task.id, "status_url": f"/tasks/{task.id}"}
```

### ARQ — Async-Native Alternative

Built on asyncio and Redis. Lighter, async-first Celery.

```python
async def process_report(ctx: dict, report_id: str) -> str:
    await asyncio.sleep(5)
    return f"Report {report_id} complete"

class WorkerSettings:
    functions = [process_report]
    redis_settings = RedisSettings(host="localhost")
```

### When to Use What

| Criteria | BackgroundTasks | Celery | ARQ | Dramatiq |
|---|---|---|---|---|
| **Persistence** | None | Full | Redis-based | Full |
| **Retries** | Manual | Built-in | Built-in | Built-in |
| **Async native** | Yes | No | Yes | No |
| **Monitoring** | None | Flower UI | Minimal | Dashboard |
| **Use when** | Fire-and-forget | Complex workflows | Async codebase | Reliability focus |

---

## 2. WebSocket Support

### Basic WebSocket with Connection Manager

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass
class ConnectionManager:
    _connections: dict[str, WebSocket] = field(default_factory=dict)
    _rooms: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    async def connect(self, ws: WebSocket, client_id: str) -> None:
        await ws.accept()
        self._connections[client_id] = ws

    def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        for room in self._rooms.values():
            room.discard(client_id)

    def join_room(self, client_id: str, room: str) -> None:
        self._rooms[room].add(client_id)

    async def broadcast_to_room(self, room: str, message: str) -> None:
        for client_id in self._rooms.get(room, set()):
            ws = self._connections.get(client_id)
            if ws:
                await ws.send_text(message)

manager = ConnectionManager()
```

### WebSocket Authentication

Auth happens during the handshake — you can't use standard HTTP middleware.

```python
from fastapi import Query, WebSocketException, status

@app.websocket("/ws/chat")
async def chat(ws: WebSocket, token: str = Query(...)):
    user = await verify_token(token)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    await manager.connect(ws, user.id)
    try:
        while True:
            data = await ws.receive_json()
            await manager.broadcast_to_room(data["room"], data["message"])
    except WebSocketDisconnect:
        manager.disconnect(user.id)
```

### Heartbeat / Keep-Alive

```python
@app.websocket("/ws/live")
async def live_ws(ws: WebSocket):
    await ws.accept()
    async def heartbeat():
        while True:
            try:
                await ws.send_json({"type": "ping"})
                await asyncio.sleep(30)
            except Exception:
                break
    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "pong":
                continue
    except WebSocketDisconnect:
        heartbeat_task.cancel()
```

---

## 3. Server-Sent Events (SSE) for Streaming

### LLM Token Streaming (The Hot Pattern)

This is the pattern behind ChatGPT-style streaming.

```python
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
import json

client = AsyncOpenAI()

async def stream_chat_completion(messages: list[dict]):
    stream = await client.chat.completions.create(
        model="gpt-4o", messages=messages, stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield f"data: {json.dumps({'content': delta.content})}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(
        stream_chat_completion(request.messages),
        media_type="text/event-stream",
    )
```

### Using `sse-starlette` for Proper SSE

Adds event names, IDs, and retry semantics.

```python
from sse_starlette.sse import EventSourceResponse

async def notification_stream(user_id: str):
    async for notification in watch_notifications(user_id):
        yield {
            "event": "notification",
            "id": str(notification.id),
            "retry": 5000,
            "data": notification.json(),
        }

@app.get("/notifications/stream")
async def stream_notifications(user_id: str):
    return EventSourceResponse(notification_stream(user_id))
```

---

## 4. File Upload & Download

### Basic Upload and Streaming Large Files

```python
from fastapi import File, UploadFile
import aiofiles

CHUNK_SIZE = 1024 * 1024  # 1 MB

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}

@app.post("/upload/large")
async def upload_large_file(file: UploadFile):
    async with aiofiles.open(f"/tmp/uploads/{file.filename}", "wb") as out:
        while chunk := await file.read(CHUNK_SIZE):
            await out.write(chunk)
    return {"filename": file.filename}
```

### Presigned URLs with S3 (Production Pattern)

Don't proxy large files through your API server.

```python
import boto3
from uuid import uuid4

s3 = boto3.client("s3", region_name="us-east-1")

@app.post("/upload/presigned")
async def get_upload_url(filename: str, content_type: str):
    key = f"uploads/{uuid4()}/{filename}"
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": "my-bucket", "Key": key, "ContentType": content_type},
        ExpiresIn=3600,
    )
    return {"upload_url": url, "key": key}
```

---

## 5. Rate Limiting

### SlowAPI (Quick Setup)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/resource")
@limiter.limit("10/minute")
async def get_resource(request: Request):
    return {"data": "value"}
```

### Redis-Based Custom Rate Limiter (Multi-Instance)

```python
import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request

redis_client = redis.from_url("redis://localhost:6379")

class RateLimiter:
    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        key = f"ratelimit:{request.client.host}:{request.url.path}"
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, self.seconds)
        if current > self.times:
            raise HTTPException(429, "Rate limit exceeded",
                                headers={"Retry-After": str(self.seconds)})

@app.get("/search", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
async def search(q: str):
    return {"results": []}
```

---

## 6. API Versioning Strategies

### URL Prefix (Most Common)

```python
v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

@v1_router.get("/users")
async def get_users_v1():
    return [{"name": "Alice"}]

@v2_router.get("/users")
async def get_users_v2():
    return {"data": [{"full_name": "Alice"}], "meta": {"total": 1}}

app.include_router(v1_router)
app.include_router(v2_router)
```

### Header-Based

```python
async def get_api_version(x_api_version: str = Header(default="1")) -> int:
    version = int(x_api_version)
    if version not in (1, 2):
        raise HTTPException(400, f"Unsupported API version: {version}")
    return version

@app.get("/users")
async def get_users(version: int = Depends(get_api_version)):
    if version == 1:
        return [{"name": "Alice"}]
    return {"data": [{"full_name": "Alice"}], "meta": {"total": 1}}
```

---

## 7. Pagination Patterns

### Offset-Based (Simple, Has Consistency Issues)

```python
class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

@app.get("/users", response_model=PaginatedResponse[UserOut])
async def list_users(pagination: PaginationParams = Depends(), db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(User))
    result = await db.execute(
        select(User).offset(pagination.offset).limit(pagination.limit).order_by(User.created_at.desc())
    )
    return PaginatedResponse(items=result.scalars().all(), total=total,
                             offset=pagination.offset, limit=pagination.limit)
```

### Cursor-Based (Consistent, No Page-Jump)

```python
def encode_cursor(created_at: datetime, id: int) -> str:
    return base64.urlsafe_b64encode(f"{created_at.isoformat()}|{id}".encode()).decode()

def decode_cursor(cursor: str) -> tuple[datetime, int]:
    dt_str, id_str = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
    return datetime.fromisoformat(dt_str), int(id_str)

@app.get("/posts", response_model=CursorPaginatedResponse[PostOut])
async def list_posts(cursor: str | None = None, limit: int = Query(default=20, le=100),
                     db: AsyncSession = Depends(get_db)):
    query = select(Post).order_by(Post.created_at.desc(), Post.id.desc())
    if cursor:
        created_at, post_id = decode_cursor(cursor)
        query = query.where(
            (Post.created_at < created_at)
            | ((Post.created_at == created_at) & (Post.id < post_id))
        )
    result = await db.execute(query.limit(limit + 1))
    posts = list(result.scalars().all())
    has_more = len(posts) > limit
    posts = posts[:limit]
    next_cursor = encode_cursor(posts[-1].created_at, posts[-1].id) if has_more and posts else None
    return CursorPaginatedResponse(items=posts, next_cursor=next_cursor, has_more=has_more)
```

---

## 8. Filtering and Sorting

```python
from enum import Enum

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

class UserFilter(BaseModel):
    search: str | None = None
    role: str | None = None
    is_active: bool | None = None
    sort_by: str = "created_at"
    sort_order: SortOrder = SortOrder.desc
    ALLOWED_SORT_FIELDS: ClassVar[set[str]] = {"created_at", "name", "email"}

    @model_validator(mode="after")
    def validate_sort(self):
        if self.sort_by not in self.ALLOWED_SORT_FIELDS:
            raise ValueError(f"Cannot sort by {self.sort_by}")
        return self

@app.get("/users")
async def list_users(filters: UserFilter = Depends(), db: AsyncSession = Depends(get_db)):
    query = select(User)
    if filters.search:
        query = query.where(User.name.ilike(f"%{filters.search}%")
                            | User.email.ilike(f"%{filters.search}%"))
    if filters.role:
        query = query.where(User.role == filters.role)
    if filters.is_active is not None:
        query = query.where(User.is_active == filters.is_active)
    sort_col = getattr(User, filters.sort_by)
    if filters.sort_order == SortOrder.desc:
        sort_col = sort_col.desc()
    return (await db.execute(query.order_by(sort_col))).scalars().all()
```

---

## 9. Bulk Operations

### Batch Create with Error Collection

```python
@app.post("/users/bulk")
async def bulk_create_users(users: list[UserCreate], db: AsyncSession = Depends(get_db)):
    created, errors = 0, []
    for i, user_data in enumerate(users):
        try:
            db.add(User(**user_data.model_dump()))
            await db.flush()
            created += 1
        except IntegrityError as e:
            await db.rollback()
            errors.append({"index": i, "error": str(e)})
    await db.commit()
    return {"created": created, "errors": errors}
```

### Streaming Response for Large Datasets (NDJSON)

```python
async def stream_users(db: AsyncSession):
    result = await db.stream(select(User).order_by(User.id))
    async for row in result:
        user = row[0]
        yield json.dumps({"id": user.id, "name": user.name}) + "\n"

@app.get("/users/export")
async def export_users(db: AsyncSession = Depends(get_db)):
    return StreamingResponse(stream_users(db), media_type="application/x-ndjson")
```

---

## 10. Long-Running Operations

### 202 Accepted + Polling

```python
from uuid import uuid4
from enum import Enum

class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

jobs: dict[str, dict] = {}

@app.post("/reports/generate", status_code=202)
async def generate_report(params: ReportParams, background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    jobs[job_id] = {"status": JobStatus.pending, "result": None}
    background_tasks.add_task(run_report_generation, job_id, params)
    return {"job_id": job_id, "status_url": f"/reports/status/{job_id}"}

@app.get("/reports/status/{job_id}")
async def report_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    response = {"job_id": job_id, "status": job["status"]}
    if job["status"] == JobStatus.completed:
        response["download_url"] = f"/reports/download/{job_id}"
    return response
```

### Webhook Delivery for Results

```python
async def run_export_with_webhook(job_id: str, params: ExportParams, webhook_url: str):
    try:
        result = await perform_export(params)
        payload = {"job_id": job_id, "status": "completed", "result": result}
    except Exception as e:
        payload = {"job_id": job_id, "status": "failed", "error": str(e)}
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json=payload, timeout=10)
```

---

## 11. Health Checks and Readiness Probes

```python
from datetime import datetime
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import text

@app.get("/health/live")
async def liveness():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    checks = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )
```

---

## Interview Questions

### Conceptual

1. **You have an endpoint that sends a confirmation email after order creation. The email service occasionally takes 5 seconds. How do you handle this without blocking the response?**

   Use `BackgroundTasks` for simple fire-and-forget. If you need reliability (retry on failure, dead-letter queue), use Celery or ARQ. `BackgroundTasks` runs in-process with no persistence — if the server crashes mid-send, the email is lost. For critical operations, use a persistent task queue with at-least-once delivery.

2. **Compare WebSocket and SSE for a real-time dashboard displaying stock prices. Which would you choose?**

   SSE. Data flows one direction (server to client), SSE handles reconnection automatically via `EventSource`, and it works with HTTP/2 multiplexing. WebSocket would add complexity without benefit — you'd need manual reconnection and heartbeat. Choose WebSocket only for bidirectional communication (chat, collaborative editing).

3. **Your API serves a paginated product list. A user reports items appearing on multiple pages or missing. What's happening?**

   Classic offset pagination problem. Inserts/deletes between page requests shift the window. Fix with cursor-based pagination — each request includes a pointer to the last-seen item. Trade-off: you lose "jump to page N."

4. **You need rate limiting across 4 instances behind a load balancer. In-memory won't work. Approach?**

   Redis-based rate limiting with a sliding window algorithm. Each instance increments a shared counter in Redis. Use `MULTI`/`EXEC` or Lua scripts for atomic increment + expire. SlowAPI supports Redis, or build a custom dependency.

5. **A client needs to upload a 2 GB video. Walk through your approach.**

   Don't proxy through the API server. Generate a presigned S3 URL, let the client upload directly. Use multipart upload for files over 100 MB. After upload, the client notifies your API (or S3 triggers a Lambda). If you must go through the API, use streaming `UploadFile` with chunked reads.

### Coding Challenges

6. **Implement a rate limiter dependency that supports both per-user and per-endpoint limits using Redis.**
   (Expected: sliding window counter with composite Redis key, proper TTL, 429 with Retry-After.)

7. **Write a cursor-based pagination endpoint with composite sort (price ASC, ID ASC). Handle cursor encoding/decoding.**
   (Expected: base64 cursor, WHERE clause with OR conditions for tie-breaking.)

8. **Implement an SSE endpoint streaming user notifications, with reconnection via Last-Event-ID.**
   (Expected: async generator, SSE format with event IDs, replay logic for missed events.)

9. **Design a long-running operation endpoint (202 Accepted) with status polling. Include error handling and timeout.**
   (Expected: job ID generation, background execution, progress status, failure handling.)

10. **Build a WebSocket chat room with auth, room join/leave, and message broadcasting. Handle disconnection gracefully.**
    (Expected: connection manager, token auth during handshake, room tracking, cleanup on disconnect.)
