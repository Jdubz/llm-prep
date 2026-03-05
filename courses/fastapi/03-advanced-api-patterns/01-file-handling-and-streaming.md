# 01 – File Handling and Streaming

## Prerequisites

You should be comfortable with FastAPI fundamentals (routing, dependency injection, Pydantic models)
and async Python before tackling this module. If you've built Express/NestJS APIs with middleware,
WebSockets, and background jobs, every concept here has a direct analogue — but the Python
ecosystem makes different trade-offs that are worth understanding deeply.

---

## File Upload

### Basic Upload

```python
from fastapi import File, UploadFile

# Simple -- reads entire file into memory
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}
```

### Streaming Large File Upload (Won't OOM)

```python
import aiofiles

CHUNK_SIZE = 1024 * 1024  # 1 MB

@app.post("/upload/large")
async def upload_large_file(file: UploadFile):
    async with aiofiles.open(f"/tmp/uploads/{file.filename}", "wb") as out:
        while chunk := await file.read(CHUNK_SIZE):
            await out.write(chunk)
    return {"filename": file.filename}
```

### Multiple File Upload

```python
@app.post("/upload/multi")
async def upload_multi(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        async with aiofiles.open(f"/tmp/{file.filename}", "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)
        results.append({"filename": file.filename, "content_type": file.content_type})
    return results
```

---

## Presigned S3 URLs (Production Pattern)

Don't proxy large files through your API server. Use presigned URLs to let clients upload
directly to object storage:

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

## Streaming Responses

### File Download with StreamingResponse

```python
from fastapi.responses import StreamingResponse
import aiofiles

@app.get("/download/{filename}")
async def download_file(filename: str):
    async def file_streamer():
        async with aiofiles.open(f"/data/{filename}", "rb") as f:
            while chunk := await f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(
        file_streamer(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
```

### Streaming Large Datasets (NDJSON Export)

```python
import json

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

## Server-Sent Events (SSE) for Streaming

### Generic SSE Template

```python
import asyncio, json
from fastapi.responses import StreamingResponse

async def event_stream(user_id: str):
    while True:
        data = await get_next_event(user_id)
        yield f"id: {data['id']}\nevent: {data['type']}\ndata: {json.dumps(data)}\n\n"

@app.get("/events/{user_id}")
async def sse(user_id: str):
    return StreamingResponse(
        event_stream(user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

### LLM Token Streaming (The Hot Pattern)

This is the pattern behind ChatGPT-style streaming:

```python
from openai import AsyncOpenAI

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

# Compact LLM streaming form
async def stream_llm(prompt: str):
    stream = await openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}], stream=True)
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield f"data: {json.dumps({'token': chunk.choices[0].delta.content})}\n\n"
    yield "data: [DONE]\n\n"
```

### Using `sse-starlette` for Proper SSE

Adds event names, IDs, and retry semantics:

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

## Background Tasks

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

### Background Task Options at a Glance

| | BackgroundTasks | Celery | ARQ | Dramatiq |
|---|---|---|---|---|
| **Install** | Built-in | `pip install celery[redis]` | `pip install arq` | `pip install dramatiq[redis]` |
| **Broker** | None (in-process) | Redis / RabbitMQ | Redis | Redis / RabbitMQ |
| **Async** | Yes | No (sync workers) | Yes | No |
| **Retries** | No | Yes | Yes | Yes |
| **Scheduling** | No | Yes (celery-beat) | Yes (cron jobs) | No |
| **Persistence** | None | Full | Redis-based | Full |
| **Monitoring** | None | Flower UI | Minimal | Dashboard |
| **When to use** | Lightweight, fire-and-forget | Complex workflows | Async-native apps | Simple reliable queues |

---

## Long-Running Operations

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

## Health Checks and Readiness Probes

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

## Practice Exercises

The following exercises in `exercises.py` directly test concepts from this file:

- **Exercise 2 (SSE Progress Stream)** -- Build an async generator that yields SSE-formatted events and return it via `StreamingResponse`. Covers the SSE wire format (`event:`, `id:`, `data:`, double newline) and the `media_type="text/event-stream"` pattern from the "Server-Sent Events" section above.
- **Exercise 3 (Background Task System)** -- Implement the 202 Accepted + polling pattern using `BackgroundTasks.add_task()`. Covers `status_code=202`, job state tracking, and progress polling from the "Background Tasks" and "Long-Running Operations" sections above.
- **Exercise 4 (File Upload with Validation)** -- Validate content type and file size, then stream to disk in 64 KB chunks. Covers the chunked `UploadFile.read()` pattern, size enforcement, and cleanup from the "File Upload" and "Streaming Large File Upload" sections above.

---

## Key Takeaways

- For large uploads, stream in chunks rather than reading the whole file into memory.
- Use presigned S3 URLs to avoid proxying large files through your application server.
- SSE is better than WebSocket for server-push scenarios — simpler, auto-reconnect, HTTP/2 compatible.
- LLM streaming uses SSE format: `data: {json}\n\n` lines yielded from an async generator.
- `BackgroundTasks` is fire-and-forget; use Celery/ARQ for retries, persistence, and monitoring.
- 202 Accepted + polling is the standard pattern for long-running operations over REST.
