"""
Interview Prep Examples: Complete FastAPI Solutions

Six self-contained FastAPI apps demonstrating clean architecture,
proper error handling, and Pydantic validation. Run any one with:
    uvicorn examples:url_shortener --reload
"""
from __future__ import annotations
import base64, hashlib, time, uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from fastapi import FastAPI, HTTPException, Query, Path, Request, status
from pydantic import BaseModel, Field, field_validator

# ============================================================================
# EXAMPLE 1: URL Shortener API (In-Memory, Full CRUD)
# ============================================================================
url_shortener = FastAPI(title="URL Shortener")
_url_store: dict[str, dict[str, Any]] = {}
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def generate_short_code(url: str, length: int = 7) -> str:
    num = int.from_bytes(hashlib.sha256(url.encode()).digest()[:8], "big")
    code = ""
    while num and len(code) < length:
        code += B62[num % 62]; num //= 62
    return code or url[:length]

class ShortenRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    custom_code: str | None = Field(None, min_length=3, max_length=20)
    @field_validator("url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")): raise ValueError("Must be http(s)")
        return v

class ShortenedURL(BaseModel):
    short_code: str; original_url: str; created_at: str; clicks: int = 0

@url_shortener.post("/shorten", response_model=ShortenedURL, status_code=201)
async def shorten_url(req: ShortenRequest):
    code = req.custom_code or generate_short_code(req.url)
    if code in _url_store and _url_store[code]["original_url"] != req.url:
        raise HTTPException(409, detail=f"Code '{code}' taken")
    if code not in _url_store:
        _url_store[code] = {"original_url": req.url, "created_at": datetime.utcnow().isoformat(), "clicks": 0}
    e = _url_store[code]
    return ShortenedURL(short_code=code, original_url=e["original_url"], created_at=e["created_at"], clicks=e["clicks"])

@url_shortener.get("/{code}")
async def redirect_to_url(code: str = Path(..., min_length=1)):
    if code not in _url_store: raise HTTPException(404, detail="Not found")
    _url_store[code]["clicks"] += 1
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=_url_store[code]["original_url"], status_code=307)

@url_shortener.get("/{code}/stats", response_model=ShortenedURL)
async def get_url_stats(code: str):
    if code not in _url_store: raise HTTPException(404, detail="Not found")
    e = _url_store[code]
    return ShortenedURL(short_code=code, original_url=e["original_url"], created_at=e["created_at"], clicks=e["clicks"])

@url_shortener.delete("/{code}", status_code=204)
async def delete_short_url(code: str):
    if code not in _url_store: raise HTTPException(404, detail="Not found")
    del _url_store[code]

# ============================================================================
# EXAMPLE 2: Notification Service API (Email, SMS, Push)
# ============================================================================
notification_service = FastAPI(title="Notification Service")
_notifications: dict[str, dict[str, Any]] = {}

class Channel(str, Enum):
    EMAIL = "email"; SMS = "sms"; PUSH = "push"

class NotifyRequest(BaseModel):
    recipient: str = Field(..., min_length=1, max_length=200)
    channel: Channel
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)
    priority: str = Field("normal", pattern=r"^(low|normal|high)$")

class NotifyResponse(BaseModel):
    id: str; channel: Channel; status: str; recipient: str
    subject: str; created_at: str; error: str | None = None

def _simulate_send(ch: Channel, rcpt: str) -> tuple[bool, str | None]:
    if "fail" in rcpt.lower(): return False, f"{ch.value} delivery failed"
    return True, None

@notification_service.post("/notifications", response_model=NotifyResponse, status_code=201)
async def send_notification(req: NotifyRequest):
    nid, now = str(uuid.uuid4()), datetime.utcnow().isoformat()
    ok, err = _simulate_send(req.channel, req.recipient)
    rec = {"id": nid, "channel": req.channel, "recipient": req.recipient, "subject": req.subject,
           "status": "delivered" if ok else "failed", "created_at": now, "error": err}
    _notifications[nid] = rec
    return NotifyResponse(**rec)

@notification_service.get("/notifications/{nid}", response_model=NotifyResponse)
async def get_notification(nid: str):
    if nid not in _notifications: raise HTTPException(404, detail="Not found")
    return NotifyResponse(**_notifications[nid])

@notification_service.get("/notifications", response_model=list[NotifyResponse])
async def list_notifications(channel: Channel | None = None, limit: int = Query(20, ge=1, le=100)):
    results = [r for r in _notifications.values() if not channel or r["channel"] == channel]
    return [NotifyResponse(**r) for r in results[-limit:]]

# ============================================================================
# EXAMPLE 3: File Processing Pipeline with Status Tracking
# ============================================================================
file_pipeline = FastAPI(title="File Processing Pipeline")
_jobs: dict[str, dict[str, Any]] = {}

class FileUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    processing_type: str = Field(..., pattern=r"^(resize|parse|convert)$")

class JobStatus(BaseModel):
    job_id: str; filename: str; status: str; processing_type: str
    progress_pct: int = Field(ge=0, le=100); created_at: str
    completed_at: str | None = None; result: dict[str, Any] | None = None
    error: str | None = None

@file_pipeline.post("/jobs", response_model=JobStatus, status_code=202)
async def create_job(req: FileUploadRequest):
    jid, now = str(uuid.uuid4()), datetime.utcnow().isoformat()
    ok = "fail" not in req.filename.lower()
    _jobs[jid] = {"job_id": jid, "filename": req.filename, "processing_type": req.processing_type,
        "status": "completed" if ok else "failed", "progress_pct": 100 if ok else 45,
        "created_at": now, "completed_at": now if ok else None,
        "result": {"output_size": len(req.content) * 2} if ok else None,
        "error": "Processing failure" if not ok else None}
    return JobStatus(**_jobs[jid])

@file_pipeline.get("/jobs/{jid}", response_model=JobStatus)
async def get_job(jid: str):
    if jid not in _jobs: raise HTTPException(404, detail="Job not found")
    return JobStatus(**_jobs[jid])

@file_pipeline.get("/jobs", response_model=list[JobStatus])
async def list_jobs(st: str | None = Query(None, alias="status"), limit: int = Query(20, ge=1, le=100)):
    results = [j for j in _jobs.values() if not st or j["status"] == st]
    return [JobStatus(**j) for j in results[-limit:]]

# ============================================================================
# EXAMPLE 4: Rate Limiter (Sliding Window Counter)
# ============================================================================
rate_limited_app = FastAPI(title="Rate Limited API")

class SlidingWindowCounter:
    """Weighted count from previous + current fixed window approximates a sliding window."""
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._counters: dict[str, dict[int, int]] = {}

    def is_allowed(self, key: str) -> tuple[bool, dict[str, Any]]:
        now = time.time()
        cur = int(now) // self.window_seconds
        prev = cur - 1
        if key not in self._counters: self._counters[key] = {}
        c = self._counters[key]
        elapsed = now - cur * self.window_seconds
        weighted = c.get(prev, 0) * (1 - elapsed / self.window_seconds) + c.get(cur, 0)
        reset = (cur + 1) * self.window_seconds
        if weighted >= self.max_requests:
            return False, {"limit": self.max_requests, "remaining": 0, "retry_after": int(reset - now) + 1}
        c[cur] = c.get(cur, 0) + 1
        for w in [w for w in c if w < prev]: del c[w]
        return True, {"limit": self.max_requests, "remaining": max(0, self.max_requests - int(weighted) - 1)}

_limiter = SlidingWindowCounter(max_requests=10, window_seconds=60)

@rate_limited_app.middleware("http")
async def rate_limit_mw(request: Request, call_next):
    fwd = request.headers.get("x-forwarded-for")
    client = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    ok, meta = _limiter.is_allowed(client)
    if not ok:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=429, content={"detail": "Too many requests"},
                            headers={"Retry-After": str(meta["retry_after"])})
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(meta["remaining"])
    return response

@rate_limited_app.get("/data")
async def get_data():
    return {"message": "Here is your data", "timestamp": datetime.utcnow().isoformat()}

# ============================================================================
# EXAMPLE 5: Cursor-Based Pagination with Filtering
# ============================================================================
pagination_app = FastAPI(title="Cursor Pagination API")

class ItemCategory(str, Enum):
    ELECTRONICS = "electronics"; BOOKS = "books"; CLOTHING = "clothing"

class Item(BaseModel):
    id: int; name: str; category: ItemCategory; price: float; created_at: str

class PaginatedResponse(BaseModel):
    items: list[Item]; next_cursor: str | None = None; has_more: bool; total_matching: int

_items: list[dict[str, Any]] = [
    {"id": i, "name": f"Item {i}", "category": list(ItemCategory)[i % 3].value,
     "price": round(9.99 + i * 3.5, 2), "created_at": (datetime(2025, 1, 1) + timedelta(hours=i)).isoformat()}
    for i in range(1, 101)]

def _enc_cursor(id: int) -> str: return base64.urlsafe_b64encode(f"id:{id}".encode()).decode()
def _dec_cursor(c: str) -> int | None:
    try:
        d = base64.urlsafe_b64decode(c.encode()).decode()
        return int(d[3:]) if d.startswith("id:") else None
    except Exception: return None

@pagination_app.get("/items", response_model=PaginatedResponse)
async def list_items(cursor: str | None = None, limit: int = Query(20, ge=1, le=100),
    category: ItemCategory | None = None, min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0)):
    f = _items
    if category: f = [i for i in f if i["category"] == category.value]
    if min_price is not None: f = [i for i in f if i["price"] >= min_price]
    if max_price is not None: f = [i for i in f if i["price"] <= max_price]
    total = len(f)
    if cursor:
        cid = _dec_cursor(cursor)
        if cid is None: raise HTTPException(400, detail="Invalid cursor")
        f = [i for i in f if i["id"] > cid]
    page = f[:limit + 1]; has_more = len(page) > limit; page = page[:limit]
    return PaginatedResponse(items=[Item(**i) for i in page], has_more=has_more, total_matching=total,
        next_cursor=_enc_cursor(page[-1]["id"]) if has_more and page else None)

# ============================================================================
# EXAMPLE 6: Key-Value Store API with TTL Support
# ============================================================================
kv_store_app = FastAPI(title="Key-Value Store")
_kv: dict[str, dict[str, Any]] = {}

class KVSetRequest(BaseModel):
    value: Any
    ttl_seconds: int | None = Field(None, ge=1, le=86400)

class KVEntry(BaseModel):
    key: str; value: Any; created_at: str; expires_at: str | None = None; ttl_remaining: int | None = None

def _expired(e: dict) -> bool:
    return e.get("expires_at") is not None and datetime.utcnow().isoformat() > e["expires_at"]

def _gc(): [_kv.pop(k) for k in [k for k, v in _kv.items() if _expired(v)]]

def _kv_resp(key: str, e: dict) -> KVEntry:
    ttl = max(0, int((datetime.fromisoformat(e["expires_at"]) - datetime.utcnow()).total_seconds())) if e.get("expires_at") else None
    return KVEntry(key=key, value=e["value"], created_at=e["created_at"], expires_at=e.get("expires_at"), ttl_remaining=ttl)

@kv_store_app.put("/kv/{key}", response_model=KVEntry)
async def set_key(key: str = Path(..., min_length=1, max_length=256), body: KVSetRequest = ...):
    now = datetime.utcnow()
    exp = (now + timedelta(seconds=body.ttl_seconds)).isoformat() if body.ttl_seconds else None
    _kv[key] = {"value": body.value, "created_at": now.isoformat(), "expires_at": exp}
    return _kv_resp(key, _kv[key])

@kv_store_app.get("/kv/{key}", response_model=KVEntry)
async def get_key(key: str):
    _gc()
    if key not in _kv: raise HTTPException(404, detail=f"Key '{key}' not found")
    return _kv_resp(key, _kv[key])

@kv_store_app.delete("/kv/{key}", status_code=204)
async def delete_key(key: str):
    if key not in _kv: raise HTTPException(404, detail=f"Key '{key}' not found")
    del _kv[key]

@kv_store_app.get("/kv", response_model=list[KVEntry])
async def list_keys(prefix: str | None = None, limit: int = Query(50, ge=1, le=500)):
    _gc()
    return [_kv_resp(k, _kv[k]) for k in sorted(k for k in _kv if not prefix or k.startswith(prefix))[:limit]]

# ============================================================================
# Smoke Tests (run: python examples.py)
# ============================================================================
def _test_all():
    print("=== 1: URL Shortener ===")
    r = ShortenRequest(url="https://example.com/long/path")
    print(f"  Code: {generate_short_code(r.url)}")
    print("\n=== 2: Notifications ===")
    n = NotifyRequest(recipient="u@ex.com", channel=Channel.EMAIL, subject="Hi", body="Hello!")
    print(f"  {n.channel.value} -> {n.recipient}")
    print("\n=== 3: File Pipeline ===")
    print(f"  Job: {FileUploadRequest(filename='report.csv', content='data', processing_type='parse').filename}")
    print("\n=== 4: Rate Limiter ===")
    lim = SlidingWindowCounter(max_requests=5, window_seconds=10)
    for i in range(7):
        ok, m = lim.is_allowed("test")
        print(f"  Req {i+1}: {'OK' if ok else 'BLOCKED'} (rem: {m.get('remaining', 0)})")
    print("\n=== 5: Pagination ===")
    print(f"  Cursor id=42: {_enc_cursor(42)} -> {_dec_cursor(_enc_cursor(42))}")
    print("\n=== 6: KV Store ===")
    kv = KVSetRequest(value={"data": 1}, ttl_seconds=300)
    print(f"  TTL: {kv.ttl_seconds}s")
    print("\nAll examples validated.")

if __name__ == "__main__":
    _test_all()
