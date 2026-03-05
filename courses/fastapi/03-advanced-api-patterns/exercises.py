"""
Advanced API Patterns Exercises

Skeleton functions with TODOs. Each exercise builds a real FastAPI pattern.
Uses only fastapi, pydantic, starlette, and the standard library.
"""
from __future__ import annotations

import asyncio, time, uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator

from fastapi import (
    BackgroundTasks, FastAPI, File, HTTPException,
    Request, UploadFile, WebSocket, WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

# ============================================================================
# EXERCISE 1: WebSocket Echo Server with Uppercase
# ============================================================================
# READ FIRST: 03-real-time-graphql-and-advanced-patterns.md -> "WebSocket Support"
# ALSO SEE:  examples.py -> Section 1, "WEBSOCKET CHAT ROOM WITH CONNECTION MANAGER"
#
# Accept connections, echo messages back UPPERCASED, track active connections.
# Test: websocat ws://localhost:8000/ws/echo
#
# KEY APIs you will use:
#   await ws.accept()                   - Accept the WebSocket handshake
#   await ws.receive_text() -> str      - Block until client sends a text frame
#   await ws.send_json(data: dict)      - Send a dict as a JSON text frame
#   WebSocketDisconnect                 - Exception raised when client disconnects
#
# Pattern:
#   @app.websocket("/path")
#   async def handler(ws: WebSocket):
#       await ws.accept()
#       try:
#           while True:
#               text = await ws.receive_text()
#               await ws.send_json({...})
#       except WebSocketDisconnect:
#           # cleanup

app_ws = FastAPI(title="Exercise 1: WebSocket Echo")
active_connections: list[WebSocket] = []

@app_ws.websocket("/ws/echo")
async def websocket_echo(ws: WebSocket):
    """
    1. Accept connection, add ws to active_connections
    2. Send welcome: {"type": "welcome", "message": "Connected!"}
    3. Loop: receive text, respond {"type": "echo", "original": ..., "uppercased": ...}
    4. On WebSocketDisconnect: remove ws from active_connections
    """
    # TODO: Accept the WebSocket connection  (await ws.accept())
    # TODO: Add ws to active_connections     (active_connections.append(ws))
    # TODO: Send a JSON welcome message      (await ws.send_json({...}))
    try:
        while True:
            pass
            # TODO: Receive text             (text = await ws.receive_text())
            # TODO: Send back JSON           (await ws.send_json({"type": "echo", "original": text, "uppercased": text.upper()}))
    except WebSocketDisconnect:
        pass
        # TODO: Remove ws from active_connections  (active_connections.remove(ws))

@app_ws.get("/ws/connections")
async def get_connection_count():
    """Return {"active_connections": <count>}."""
    # TODO: Return {"active_connections": len(active_connections)}
    pass

# ============================================================================
# EXERCISE 2: SSE Progress Stream
# ============================================================================
# READ FIRST: 01-file-handling-and-streaming.md -> "Server-Sent Events (SSE) for Streaming"
# ALSO SEE:  examples.py -> Section 2, "SERVER-SENT EVENTS (SSE) STREAMING"
#
# Stream progress 0-100% as Server-Sent Events (5% increments, 0.2s apart).
# Test: curl -N http://localhost:8000/progress/my_task
#
# KEY APIs you will use:
#   StreamingResponse(generator, media_type="text/event-stream")
#   async generator function  ->  use `yield` to produce each SSE event
#   await asyncio.sleep(0.2)  ->  pause between events
#
# SSE wire format (each event is a text block ending with two newlines):
#   event: progress\n
#   id: 0\n
#   data: {"task_name": "my_task", "percent": 0}\n
#   \n
#
# Use json.dumps() for the data line. Import json at the top if needed.
#
# Pattern (from examples.py):
#   async def generate_sse_events(topic: str) -> AsyncGenerator[str, None]:
#       for i in range(10):
#           payload = json.dumps({...})
#           yield f"event: update\nid: {i}\ndata: {payload}\n\n"
#           await asyncio.sleep(0.3)
#       yield f"event: done\ndata: ...\n\n"

app_sse = FastAPI(title="Exercise 2: SSE Progress")

async def progress_generator(task_name: str) -> AsyncGenerator[str, None]:
    """
    Yield 21 SSE events (0%, 5%, ... 100%), then one "complete" event.
    Format per event:
        event: progress\nid: <n>\ndata: {"task_name":"...","percent":0}\n\n
    Sleep 0.2s between events.
    """
    # TODO: Loop from 0 to 100 inclusive, step 5  (for percent in range(0, 101, 5):)
    #       - Build payload: json.dumps({"task_name": task_name, "percent": percent})
    #       - Yield SSE string: f"event: progress\nid: {percent // 5}\ndata: {payload}\n\n"
    #       - Sleep: await asyncio.sleep(0.2)
    # TODO: After loop, yield a "complete" event:
    #       f"event: complete\ndata: {json.dumps({'task_name': task_name, 'status': 'done'})}\n\n"
    pass

@app_sse.get("/progress/{task_name}")
async def stream_progress(task_name: str):
    """Return StreamingResponse with media_type="text/event-stream"."""
    # TODO: return StreamingResponse(progress_generator(task_name), media_type="text/event-stream")
    pass

# ============================================================================
# EXERCISE 3: Background Task System
# ============================================================================
# READ FIRST: 01-file-handling-and-streaming.md -> "Background Tasks" and "Long-Running Operations"
# ALSO SEE:  examples.py -> Section 3, "BACKGROUND TASK WITH STATUS POLLING"
#
# POST /tasks -> 202 with job_id.  GET /tasks/{id} -> status + progress.
#
# KEY APIs you will use:
#   background_tasks.add_task(func, *args)  - Schedule a callable to run after response
#       Signature: BackgroundTasks.add_task(func: Callable, *args: Any, **kwargs: Any) -> None
#       The func can be async or sync. Args are passed positionally.
#   uuid.uuid4()                            - Generate a unique job ID
#   asyncio.sleep(seconds)                  - Simulate work in the background task
#   HTTPException(status_code=404, detail=...) - Return 404 for unknown task_id
#
# Pattern (from examples.py):
#   @app.post("/jobs", status_code=202)
#   async def submit_job(sub: JobSubmission, bg: BackgroundTasks):
#       job_id = str(uuid.uuid4())
#       _jobs[job_id] = {"status": "pending", "progress": 0, ...}
#       bg.add_task(run_long_job, job_id, sub.duration_seconds)
#       return JobResponse(job_id=job_id, status="pending")

app_bg = FastAPI(title="Exercise 3: Background Tasks")

class TaskStatus(str, Enum):
    pending = "pending"; running = "running"
    completed = "completed"; failed = "failed"

class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    duration_seconds: int = Field(default=3, ge=1, le=30)

class TaskResponse(BaseModel):
    task_id: str; name: str; status: TaskStatus
    progress: int = 0; result: dict | None = None

_tasks: dict[str, dict] = {}

async def execute_task(task_id: str, duration: int) -> None:
    """
    1. Set status="running"
    2. 10 steps, sleep duration/10 each, update progress 10..100
    3. Set status="completed", result={"message":..., "steps":10}
    4. On exception: status="failed", store error
    """
    # TODO: Set _tasks[task_id]["status"] = TaskStatus.running
    # TODO: try/except block:
    #   try:
    #       for i in range(10):
    #           await asyncio.sleep(duration / 10)
    #           _tasks[task_id]["progress"] = (i + 1) * 10
    #       _tasks[task_id]["status"] = TaskStatus.completed
    #       _tasks[task_id]["result"] = {"message": f"Task {task_id} done", "steps": 10}
    #   except Exception as e:
    #       _tasks[task_id]["status"] = TaskStatus.failed
    #       _tasks[task_id]["result"] = {"error": str(e)}
    pass

@app_bg.post("/tasks", status_code=202, response_model=TaskResponse)
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """Generate UUID, store initial state, schedule execute_task, return 202."""
    # TODO: task_id = str(uuid.uuid4())
    # TODO: _tasks[task_id] = {"name": task.name, "status": TaskStatus.pending, "progress": 0, "result": None}
    # TODO: background_tasks.add_task(execute_task, task_id, task.duration_seconds)
    # TODO: return TaskResponse(task_id=task_id, name=task.name, status=TaskStatus.pending)
    pass

@app_bg.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Return task status or 404."""
    # TODO: if task_id not in _tasks: raise HTTPException(status_code=404, detail="Task not found")
    # TODO: t = _tasks[task_id]
    # TODO: return TaskResponse(task_id=task_id, name=t["name"], status=t["status"],
    #                           progress=t["progress"], result=t["result"])
    pass

# ============================================================================
# EXERCISE 4: File Upload with Type/Size Validation
# ============================================================================
# READ FIRST: 01-file-handling-and-streaming.md -> "File Upload" (all subsections)
# ALSO SEE:  examples.py -> Section 4, "FILE UPLOAD WITH VALIDATION AND STREAMING TO DISK"
#
# Accept JPEG, PNG, PDF only. Reject > 5 MB. Stream to disk in 64 KB chunks.
#
# KEY APIs you will use:
#   UploadFile attributes:
#       file.filename      -> str | None   (original filename from client)
#       file.content_type  -> str | None   (MIME type, e.g. "image/jpeg")
#       file.size          -> int | None   (may be None for streamed uploads)
#       file.file          -> SpooledTemporaryFile (underlying file object)
#       await file.read(size)  -> bytes    (read `size` bytes; empty bytes = EOF)
#
#   Chunked reading pattern (avoids loading whole file into memory):
#       total = 0
#       while chunk := await file.read(64 * 1024):   # 64 KB chunks
#           total += len(chunk)
#           f.write(chunk)
#
#   HTTPException(status_code=422, detail=...)  - Invalid content type
#   HTTPException(status_code=413, detail=...)  - File too large
#
# Pattern (from examples.py):
#   if file.content_type not in ALLOWED_TYPES:
#       raise HTTPException(422, f"Type '{file.content_type}' not allowed")
#   UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
#   dest = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
#   total = 0
#   with open(dest, "wb") as f:
#       while chunk := await file.read(64 * 1024):
#           total += len(chunk)
#           if total > MAX_FILE_SIZE:
#               dest.unlink(missing_ok=True)
#               raise HTTPException(413, "File too large")
#           f.write(chunk)

app_upload = FastAPI(title="Exercise 4: File Upload")
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_SIZE_BYTES = 5 * 1024 * 1024
DEST_DIR = Path("/tmp/exercise_uploads")

class FileUploadResponse(BaseModel):
    filename: str; size_bytes: int; content_type: str; saved_path: str

@app_upload.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    1. Validate content_type (422 if bad)
    2. Stream to disk in 64 KB chunks, track total bytes
    3. If total > MAX_SIZE_BYTES: delete partial file, raise 413
    4. Return FileUploadResponse
    """
    # TODO: Check file.content_type in ALLOWED_TYPES, raise HTTPException(422, ...) if not
    # TODO: DEST_DIR.mkdir(parents=True, exist_ok=True)
    # TODO: dest = DEST_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    # TODO: total = 0
    # TODO: Open dest with open(dest, "wb") as f:
    #       while chunk := await file.read(64 * 1024):
    #           total += len(chunk)
    #           if total > MAX_SIZE_BYTES:
    #               dest.unlink(missing_ok=True)
    #               raise HTTPException(413, f"File exceeds {MAX_SIZE_BYTES // (1024*1024)} MB limit")
    #           f.write(chunk)
    # TODO: return FileUploadResponse(filename=file.filename or "unknown",
    #           size_bytes=total, content_type=file.content_type or "unknown",
    #           saved_path=str(dest))
    pass

# ============================================================================
# EXERCISE 5: In-Memory Rate Limiter Middleware
# ============================================================================
# READ FIRST: 02-pagination-filtering-and-bulk-operations.md -> "Rate Limiting"
# ALSO SEE:  examples.py -> Section 5, "RATE LIMITING MIDDLEWARE (IN-MEMORY TOKEN BUCKET)"
#
# Token bucket per client IP. 429 + Retry-After when empty.
#
# KEY CONCEPTS:
#   Token bucket algorithm:
#     - Each client (IP) gets a bucket with `capacity` tokens
#     - Tokens refill at `refill_rate` per second, capped at capacity
#     - Each request consumes 1 token; if empty -> 429 Too Many Requests
#     - Refill formula: tokens = min(capacity, tokens + elapsed * refill_rate)
#
#   time.monotonic() -> float   (use for elapsed time calculations)
#   BaseHTTPMiddleware          (subclass and implement `async def dispatch`)
#   request.client.host         (client IP address string)
#   JSONResponse(status_code=429, content={...}, headers={"Retry-After": "..."})
#
# Pattern (from examples.py TokenBucket._get):
#   now = time.monotonic()
#   if key not in self._buckets:
#       self._buckets[key] = {"tokens": self.capacity, "last": now}
#   b = self._buckets[key]
#   b["tokens"] = min(self.capacity, b["tokens"] + (now - b["last"]) * self.refill_rate)
#   b["last"] = now

app_rate = FastAPI(title="Exercise 5: Rate Limiter")

@dataclass
class RateBucket:
    tokens: float
    last_refill: float

@dataclass
class InMemoryRateLimiter:
    capacity: float
    refill_rate: float
    _buckets: dict[str, RateBucket] = field(default_factory=dict)

    def _get_or_create_bucket(self, key: str) -> RateBucket:
        """Get/create bucket, refill tokens based on elapsed time, cap at capacity."""
        # TODO: now = time.monotonic()
        # TODO: If key not in _buckets, create RateBucket(tokens=self.capacity, last_refill=now)
        # TODO: bucket = self._buckets[key]
        # TODO: elapsed = now - bucket.last_refill
        # TODO: bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_rate)
        # TODO: bucket.last_refill = now
        # TODO: return bucket
        pass

    def try_consume(self, key: str) -> bool:
        """Consume one token. True if allowed, False if rate-limited."""
        # TODO: bucket = self._get_or_create_bucket(key)
        # TODO: if bucket.tokens >= 1.0: bucket.tokens -= 1.0; return True
        # TODO: return False
        pass

    def get_retry_after(self, key: str) -> float:
        """Seconds until the next token is available."""
        # TODO: bucket = self._get_or_create_bucket(key)
        # TODO: return max(0.0, (1.0 - bucket.tokens) / self.refill_rate)
        pass

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_per_second: float = 5.0, burst: float = 10.0):
        super().__init__(app)
        self.limiter = InMemoryRateLimiter(capacity=burst, refill_rate=rate_per_second)

    async def dispatch(self, request: Request, call_next):
        """Extract IP, try_consume, return 429+Retry-After or call_next."""
        # TODO: ip = request.client.host if request.client else "unknown"
        # TODO: if not self.limiter.try_consume(ip):
        #           retry = self.limiter.get_retry_after(ip)
        #           return JSONResponse(
        #               status_code=429,
        #               content={"detail": "Rate limit exceeded"},
        #               headers={"Retry-After": f"{retry:.1f}"}
        #           )
        # TODO: return await call_next(request)
        pass

# Uncomment to apply: app_rate.add_middleware(RateLimiterMiddleware, rate_per_second=2.0, burst=5.0)

@app_rate.get("/limited")
async def limited_endpoint():
    return {"message": "You got through the rate limiter!"}

# ============================================================================
# TESTS
# ============================================================================

def test_exercise_1():
    print("\n=== EX 1: WebSocket Echo ===")
    routes = [r.path for r in app_ws.routes]
    assert "/ws/echo" in routes and "/ws/connections" in routes
    print("Routes exist: PASS")

def test_exercise_2():
    print("\n=== EX 2: SSE Progress ===")
    import inspect
    assert inspect.isasyncgenfunction(progress_generator)
    print("Async generator: PASS")

def test_exercise_3():
    print("\n=== EX 3: Background Tasks ===")
    t = TaskResponse(task_id="x", name="test", status=TaskStatus.pending)
    assert t.status == TaskStatus.pending
    print("Model valid: PASS")

def test_exercise_4():
    print("\n=== EX 4: File Upload ===")
    assert "image/jpeg" in ALLOWED_TYPES and MAX_SIZE_BYTES == 5 * 1024 * 1024
    print("Constants correct: PASS")

def test_exercise_5():
    print("\n=== EX 5: Rate Limiter ===")
    lim = InMemoryRateLimiter(capacity=3.0, refill_rate=1.0)
    if lim.try_consume("t") is None:
        print("Not yet implemented: SKIP"); return
    assert all(lim.try_consume("t") for _ in range(2))  # 2nd and 3rd
    assert not lim.try_consume("t"), "4th should fail"
    assert lim.get_retry_after("t") > 0
    assert lim.try_consume("other"), "Separate client should pass"
    print("Token bucket: PASS")

if __name__ == "__main__":
    test_exercise_1(); test_exercise_2(); test_exercise_3()
    test_exercise_4(); test_exercise_5()
    print("\nStructure tests passed. Implement TODOs, then run:")
    for name in ["app_ws", "app_sse", "app_bg", "app_upload", "app_rate"]:
        print(f"  uvicorn exercises:{name} --reload")

"""
LEARNING OBJECTIVES

- [ ] WebSocket accept/send/receive and disconnect handling
- [ ] Async generators yielding SSE-formatted event streams
- [ ] BackgroundTasks with job status tracking and 202 Accepted
- [ ] File upload validation (type/size) with chunked streaming
- [ ] Token bucket rate limiting as BaseHTTPMiddleware
"""
