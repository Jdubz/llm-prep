"""
Advanced API Patterns Examples

Complete, runnable patterns: WebSockets, SSE, background tasks, file uploads,
rate limiting, API versioning, and 202 Accepted long-running operations.
Uses only fastapi, pydantic, starlette, and the standard library.
"""
from __future__ import annotations

import asyncio, json, time, uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator

from fastapi import (
    APIRouter, BackgroundTasks, FastAPI, File, HTTPException,
    Request, Response, UploadFile, WebSocket, WebSocketDisconnect,
)
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# 1. WEBSOCKET CHAT ROOM WITH CONNECTION MANAGER
# ---------------------------------------------------------------------------

@dataclass
class ConnectionManager:
    """Manages WebSocket connections and chat rooms."""
    _connections: dict[str, WebSocket] = field(default_factory=dict)
    _rooms: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    async def connect(self, ws: WebSocket, client_id: str) -> None:
        await ws.accept()
        self._connections[client_id] = ws

    def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        for room in self._rooms.values():
            room.discard(client_id)

    def join_room(self, cid: str, room: str) -> None:
        self._rooms[room].add(cid)

    def leave_room(self, cid: str, room: str) -> None:
        self._rooms[room].discard(cid)

    async def broadcast(self, room: str, msg: dict, exclude: str | None = None) -> None:
        for cid in self._rooms.get(room, set()):
            if cid != exclude and (ws := self._connections.get(cid)):
                await ws.send_json(msg)

manager = ConnectionManager()
ws_app = FastAPI(title="WebSocket Chat")

@ws_app.websocket("/ws/chat/{client_id}")
async def websocket_chat(ws: WebSocket, client_id: str):
    """send {"action":"join"|"leave"|"message","room":"...","text":"..."}"""
    await manager.connect(ws, client_id)
    try:
        while True:
            data = await ws.receive_json()
            action, room = data.get("action"), data.get("room", "general")
            if action == "join":
                manager.join_room(client_id, room)
                await manager.broadcast(room, {"type": "system", "text": f"{client_id} joined"}, exclude=client_id)
            elif action == "leave":
                manager.leave_room(client_id, room)
                await manager.broadcast(room, {"type": "system", "text": f"{client_id} left"})
            elif action == "message":
                await manager.broadcast(room, {"type": "message", "from": client_id, "text": data.get("text", "")})
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# ---------------------------------------------------------------------------
# 2. SERVER-SENT EVENTS (SSE) STREAMING
# ---------------------------------------------------------------------------

sse_app = FastAPI(title="SSE Streaming")

async def generate_sse_events(topic: str) -> AsyncGenerator[str, None]:
    """Yields SSE-formatted strings with event name, ID, and JSON data."""
    for i in range(10):
        payload = json.dumps({"topic": topic, "seq": i, "content": f"Update #{i}"})
        yield f"event: update\nid: {i}\ndata: {payload}\n\n"
        await asyncio.sleep(0.3)
    yield f"event: done\ndata: {json.dumps({'message': 'Stream complete'})}\n\n"

@sse_app.get("/stream/{topic}")
async def stream_events(topic: str):
    return StreamingResponse(generate_sse_events(topic), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ---------------------------------------------------------------------------
# 3. BACKGROUND TASK WITH STATUS POLLING
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    pending = "pending"; running = "running"; completed = "completed"; failed = "failed"

class JobSubmission(BaseModel):
    name: str
    duration_seconds: int = Field(default=5, ge=1, le=60)

class JobResponse(BaseModel):
    job_id: str; status: JobStatus; progress: int = 0
    result: dict | None = None; error: str | None = None

_jobs: dict[str, dict] = {}
bg_app = FastAPI(title="Background Tasks")

async def run_long_job(job_id: str, duration: int) -> None:
    """Simulates work: 10 steps with progress updates."""
    _jobs[job_id]["status"] = JobStatus.running
    try:
        for i in range(10):
            await asyncio.sleep(duration / 10)
            _jobs[job_id]["progress"] = (i + 1) * 10
        _jobs[job_id]["status"] = JobStatus.completed
        _jobs[job_id]["result"] = {"message": f"Job {job_id} done", "items": 42}
    except Exception as e:
        _jobs[job_id]["status"] = JobStatus.failed
        _jobs[job_id]["error"] = str(e)

@bg_app.post("/jobs", status_code=202, response_model=JobResponse)
async def submit_job(sub: JobSubmission, bg: BackgroundTasks):
    """Submit a job. Returns 202; poll /jobs/{id} for status."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": JobStatus.pending, "progress": 0, "result": None, "error": None}
    bg.add_task(run_long_job, job_id, sub.duration_seconds)
    return JobResponse(job_id=job_id, status=JobStatus.pending)

@bg_app.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    if (job := _jobs.get(job_id)) is None:
        raise HTTPException(404, "Job not found")
    return JobResponse(job_id=job_id, **job)

# ---------------------------------------------------------------------------
# 4. FILE UPLOAD WITH VALIDATION AND STREAMING TO DISK
# ---------------------------------------------------------------------------

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = Path("/tmp/fastapi_uploads")
upload_app = FastAPI(title="File Uploads")

class UploadResponse(BaseModel):
    filename: str; size_bytes: int; content_type: str; path: str

@upload_app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Validates type/size, streams to disk in 64 KB chunks."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(422, f"Type '{file.content_type}' not allowed")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    total = 0
    try:
        with open(dest, "wb") as f:
            while chunk := await file.read(64 * 1024):
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"Exceeds {MAX_FILE_SIZE // (1024*1024)} MB limit")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(500, f"Upload failed: {e}")
    return UploadResponse(filename=file.filename or "unknown", size_bytes=total,
                          content_type=file.content_type or "application/octet-stream", path=str(dest))

# ---------------------------------------------------------------------------
# 5. RATE LIMITING MIDDLEWARE (IN-MEMORY TOKEN BUCKET)
# ---------------------------------------------------------------------------

@dataclass
class TokenBucket:
    """Each key gets `capacity` tokens, refilling at `refill_rate` per second."""
    capacity: float
    refill_rate: float
    _buckets: dict[str, dict] = field(default_factory=dict)

    def _get(self, key: str) -> dict:
        now = time.monotonic()
        if key not in self._buckets:
            self._buckets[key] = {"tokens": self.capacity, "last": now}
        b = self._buckets[key]
        b["tokens"] = min(self.capacity, b["tokens"] + (now - b["last"]) * self.refill_rate)
        b["last"] = now
        return b

    def consume(self, key: str) -> bool:
        b = self._get(key)
        if b["tokens"] >= 1.0:
            b["tokens"] -= 1.0
            return True
        return False

    def retry_after(self, key: str) -> float:
        b = self._get(key)
        return max(0.0, (1.0 - b["tokens"]) / self.refill_rate)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP token bucket. Returns 429 + Retry-After when exhausted."""
    def __init__(self, app, requests_per_second: float = 10.0, burst: float = 20.0):
        super().__init__(app)
        self.limiter = TokenBucket(capacity=burst, refill_rate=requests_per_second)

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        if not self.limiter.consume(ip):
            return JSONResponse(429, {"detail": "Rate limit exceeded"},
                                headers={"Retry-After": f"{self.limiter.retry_after(ip):.1f}"})
        return await call_next(request)

rate_limited_app = FastAPI(title="Rate Limited API")
rate_limited_app.add_middleware(RateLimitMiddleware, requests_per_second=2.0, burst=5.0)

@rate_limited_app.get("/resource")
async def get_resource():
    return {"data": "Rate-limited to 2 req/s with burst of 5"}

# ---------------------------------------------------------------------------
# 6. API VERSIONING WITH ROUTER PREFIXES
# ---------------------------------------------------------------------------

versioned_app = FastAPI(title="Versioned API")
v1 = APIRouter(prefix="/api/v1", tags=["v1"])
v2 = APIRouter(prefix="/api/v2", tags=["v2"])

class UserV1(BaseModel):
    name: str; email: str

class UserV2(BaseModel):
    full_name: str; email: str; active: bool = True

@v1.get("/users", response_model=list[UserV1])
async def get_users_v1():
    return [UserV1(name="Alice", email="alice@example.com")]

@v2.get("/users")
async def get_users_v2():
    """V2: envelope with metadata."""
    users = [UserV2(full_name="Alice Smith", email="alice@example.com")]
    return {"data": [u.model_dump() for u in users], "meta": {"total": len(users)}}

versioned_app.include_router(v1)
versioned_app.include_router(v2)

# ---------------------------------------------------------------------------
# 7. LONG-RUNNING OPERATION WITH 202 ACCEPTED PATTERN
# ---------------------------------------------------------------------------

class ReportParams(BaseModel):
    report_type: str; start_date: str; end_date: str

class ReportStatus(BaseModel):
    job_id: str; status: JobStatus; progress: int = 0
    status_url: str; download_url: str | None = None

_reports: dict[str, dict] = {}
report_app = FastAPI(title="Long-Running Operations")

async def generate_report(job_id: str, params: ReportParams) -> None:
    _reports[job_id]["status"] = JobStatus.running
    for i, phase in enumerate(["Querying", "Aggregating", "Formatting", "Done"]):
        _reports[job_id].update(phase=phase, progress=(i + 1) * 25)
        await asyncio.sleep(1)
    _reports[job_id]["status"] = JobStatus.completed
    _reports[job_id]["download_url"] = f"/reports/download/{job_id}"

@report_app.post("/reports/generate", status_code=202)
async def start_report(params: ReportParams, bg: BackgroundTasks):
    """Returns 202 + Location header for polling."""
    job_id = str(uuid.uuid4())
    _reports[job_id] = {"status": JobStatus.pending, "progress": 0,
                        "phase": "Queued", "download_url": None, "params": params.model_dump()}
    bg.add_task(generate_report, job_id, params)
    url = f"/reports/status/{job_id}"
    return Response(content=ReportStatus(job_id=job_id, status=JobStatus.pending,
                    status_url=url).model_dump_json(),
                    status_code=202, media_type="application/json", headers={"Location": url})

@report_app.get("/reports/status/{job_id}", response_model=ReportStatus)
async def report_status(job_id: str):
    if (r := _reports.get(job_id)) is None:
        raise HTTPException(404, "Not found")
    return ReportStatus(job_id=job_id, status=r["status"], progress=r["progress"],
                        status_url=f"/reports/status/{job_id}", download_url=r.get("download_url"))

@report_app.get("/reports/download/{job_id}")
async def download_report(job_id: str):
    if (r := _reports.get(job_id)) is None:
        raise HTTPException(404, "Not found")
    if r["status"] != JobStatus.completed:
        raise HTTPException(409, "Not ready")
    return {"job_id": job_id, "data": {"summary": "Report content here"}}

# ---------------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------------

def test_token_bucket():
    print("=== Token Bucket ===")
    tb = TokenBucket(capacity=3, refill_rate=1.0)
    for i in range(3):
        assert tb.consume("a"), f"Req {i} should pass"
    assert not tb.consume("a"), "4th should fail"
    assert tb.consume("b"), "Different client should pass"
    assert tb.retry_after("a") > 0
    print("PASS")

def test_connection_manager():
    print("=== Connection Manager ===")
    m = ConnectionManager()
    m._connections["alice"] = None  # type: ignore
    m._connections["bob"] = None  # type: ignore
    m.join_room("alice", "g"); m.join_room("bob", "g")
    assert m._rooms["g"] == {"alice", "bob"}
    m.disconnect("bob")
    assert "bob" not in m._connections and "bob" not in m._rooms["g"]
    print("PASS")

if __name__ == "__main__":
    test_token_bucket()
    test_connection_manager()
    print("\nAll tests passed. Run any app with uvicorn:")
    for name in ["ws_app", "sse_app", "bg_app", "upload_app",
                  "rate_limited_app", "versioned_app", "report_app"]:
        print(f"  uvicorn examples:{name} --reload")
