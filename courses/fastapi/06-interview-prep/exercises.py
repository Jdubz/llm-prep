"""
Interview Prep Exercises: Timed Coding Challenges

Six interview-style exercises with skeleton code, clear requirements,
and test functions. Time yourself — these simulate real interview pacing.
Uses only: fastapi, pydantic, and Python standard library.
"""
from __future__ import annotations
import hashlib, time, uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from fastapi import FastAPI, HTTPException, Query, Path, Request, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, field_validator

# ============================================================================
# EXERCISE 1: TODO API with CRUD + Filtering (15 min)
# ============================================================================
# CONCEPTS FROM:
#   Module 01 (FastAPI Foundations):
#     - 01-http-routing-and-decorators.md  -> route decorators, path/query params, status codes
#     - 02-dependency-injection.md         -> Depends() pattern (not needed here but good practice)
#   Module 05 (Advanced API Patterns):
#     - 02-pagination-filtering-and-bulk-operations.md -> query param filtering
#
# ALSO SEE:
#   - Module 01 exercises.py (CRUD exercises)
#   - Module 08 examples.py, Example 1 (URL Shortener) for similar CRUD pattern
#   - 02-system-design-and-code-review.md, "Pattern 1: Complete CRUD Endpoint"
#
# KEY IMPORTS AND PATTERNS:
#   from fastapi import FastAPI, HTTPException, Query, Path, status
#   from pydantic import BaseModel, Field, field_validator
#   - Pydantic models: Field(min_length=, max_length=) for string validation
#   - Optional fields: use `field: type | None = None`
#   - Status codes: status_code=201 on POST, status_code=204 on DELETE
#   - Filtering: use Query() params with enum or str matching
#   - 404 pattern: `if id not in store: raise HTTPException(status_code=404, detail="...")`
#   - Auto-increment: `global _counter; _counter += 1`
#
# HINTS:
#   - TodoCreate: title: str = Field(..., min_length=1, max_length=200)
#                 description: str | None = Field(None, max_length=1000)
#   - TodoUpdate: all fields Optional (title, description, completed)
#   - TodoResponse: id: int, title: str, description: str | None, completed: bool, created_at: str
#   - For PATCH, use model_dump(exclude_unset=True) to only update provided fields
#   - Filter pattern: if status param given, filter dict values where completed matches
# ----------------------------------------------------------------------------
# POST /todos          -> Create (title 1-200 chars, description optional max 1000)
# GET  /todos          -> List, filterable by ?status=pending|completed
# GET  /todos/{id}     -> Get single todo by ID
# PATCH /todos/{id}    -> Update title, description, or completed (bool)
# DELETE /todos/{id}   -> Delete (204)
# TodoResponse: id (int), title, description, completed (bool), created_at (str)
# In-memory dict, auto-incrementing int IDs. Return 404/201/204 as appropriate.

app1 = FastAPI(title="TODO API")
_todos: dict[int, dict[str, Any]] = {}
_todo_counter: int = 0

class TodoCreate(BaseModel):
    pass  # TODO: title (required 1-200), description (optional, max 1000)

class TodoUpdate(BaseModel):
    pass  # TODO: title, description, completed — all optional

class TodoResponse(BaseModel):
    pass  # TODO: id, title, description, completed, created_at

# TODO: Implement all five endpoints on app1

# ============================================================================
# EXERCISE 2: User Registration with Validation (15 min)
# ============================================================================
# CONCEPTS FROM:
#   Module 01 (FastAPI Foundations):
#     - 01-http-routing-and-decorators.md  -> Pydantic models, Field validators, status codes
#     - 02-dependency-injection.md         -> header extraction pattern
#   Module 04 (Auth):
#     - 01-authentication-basics.md        -> password hashing, token generation, Bearer auth
#     - 02-authorization-and-rbac.md       -> protecting endpoints with auth
#
# ALSO SEE:
#   - Module 04 exercises.py (auth exercises)
#   - Module 04 examples.py (JWT auth examples)
#   - 01-interview-fundamentals.md, section "F1: How does FastAPI's dependency injection work?"
#
# KEY IMPORTS AND PATTERNS:
#   from fastapi import FastAPI, HTTPException, Request, status
#   from pydantic import BaseModel, Field, field_validator
#   import hashlib, uuid
#   - Password hashing approach (simplified for interview, not production):
#       def _hash_pw(pw: str) -> str:
#           return hashlib.sha256(pw.encode()).hexdigest()
#   - Token generation:
#       token = hashlib.sha256(f"{username}:{datetime.utcnow()}:{uuid.uuid4()}".encode()).hexdigest()
#   - Bearer token extraction from header:
#       auth = request.headers.get("Authorization", "")
#       if not auth.startswith("Bearer "): raise HTTPException(401, ...)
#       token = auth[7:]  # strip "Bearer " prefix
#   - 409 for duplicates: raise HTTPException(status_code=409, detail="Username already exists")
#
# HINTS:
#   - RegisterRequest validators (use @field_validator):
#       username: str = Field(..., min_length=3, max_length=30)
#       @field_validator("username") -> check .isalnum()
#       @field_validator("email")    -> check "@" in v
#       @field_validator("password") -> check len>=8, any(c.isupper()), any(c.isdigit())
#   - LoginRequest: just username + password, no validators needed
#   - UserResponse: id (str, use uuid), username, email, created_at — NO password_hash field
#   - Store users in _users dict keyed by username
#   - Store tokens in _tokens dict: token -> username mapping
# ----------------------------------------------------------------------------
# POST /register -> username (3-30 alphanumeric), email (must have @),
#                   password (8+ chars, needs digit + uppercase). Hash with sha256.
# POST /login    -> Validate creds, return {"token": "..."}. 401 on failure.
# GET  /me       -> Read Authorization: Bearer <token> header. Return user info.
# Duplicate username/email -> 409. Never expose password_hash in responses.

app2 = FastAPI(title="User Registration")
_users: dict[str, dict[str, Any]] = {}
_tokens: dict[str, str] = {}

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _make_token(username: str) -> str:
    return hashlib.sha256(f"{username}:{datetime.utcnow()}:{uuid.uuid4()}".encode()).hexdigest()

class RegisterRequest(BaseModel):
    pass  # TODO: username, email, password with validators

class LoginRequest(BaseModel):
    pass  # TODO: username, password

class UserResponse(BaseModel):
    pass  # TODO: id, username, email, created_at (no password!)

# TODO: Implement three endpoints on app2

# ============================================================================
# EXERCISE 3: Rate-Limited API Endpoint (20 min)
# ============================================================================
# CONCEPTS FROM:
#   Module 01 (FastAPI Foundations):
#     - 03-middleware-asgi-and-advanced-patterns.md -> middleware pattern, Request/Response
#   Module 05 (Advanced API Patterns):
#     - 03-real-time-graphql-and-advanced-patterns.md -> advanced middleware
#   Module 07 (Production):
#     - 03-performance-and-scaling.md -> rate limiting in production
#
# ALSO SEE:
#   - Module 08 examples.py, Example 4 (Rate Limiter — Sliding Window Counter)
#   - 02-system-design-and-code-review.md, "Pattern 4: Rate Limiting Middleware"
#   - Module 01 exercises.py (middleware exercises)
#
# KEY IMPORTS AND PATTERNS:
#   from fastapi import FastAPI, Request, status
#   from fastapi.responses import JSONResponse
#   import time
#
# TOKEN BUCKET ALGORITHM OUTLINE:
#   class TokenBucket:
#       def __init__(self, capacity, refill_rate):
#           self.capacity = capacity
#           self.refill_rate = refill_rate    # tokens added per second
#           self.tokens = float(capacity)     # start full
#           self.last_refill = time.monotonic()
#
#       def consume(self) -> tuple[bool, float]:
#           now = time.monotonic()
#           elapsed = now - self.last_refill
#           self.last_refill = now
#           # Refill: add elapsed * rate, but cap at capacity
#           self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
#           # Consume: if tokens >= 1, subtract 1 and allow
#           if self.tokens >= 1.0:
#               self.tokens -= 1.0
#               return (True, self.tokens)
#           return (False, self.tokens)
#
# MIDDLEWARE PATTERN:
#   @app.middleware("http")
#   async def rate_limit(request: Request, call_next):
#       if request.url.path == "/health":      # skip health check
#           return await call_next(request)
#       ip = request.client.host if request.client else "unknown"
#       bucket = _get_bucket(ip)
#       allowed, remaining = bucket.consume()
#       if not allowed:
#           return JSONResponse(status_code=429, content={"detail": "Too many requests"},
#                               headers={"Retry-After": "1"})
#       response = await call_next(request)
#       response.headers["X-RateLimit-Remaining"] = str(int(remaining))
#       return response
#
# HINTS:
#   - time.monotonic() is preferred over time.time() for measuring elapsed durations
#   - _get_bucket: use _buckets.setdefault(ip, TokenBucket(10, 1.0))
#   - Return JSONResponse (not raise HTTPException) from middleware for 429
# ----------------------------------------------------------------------------
# Implement TokenBucket(capacity, refill_rate_per_second):
#   consume() -> (allowed: bool, tokens_remaining: float)
#   Tokens refill continuously based on elapsed time, capped at capacity.
# Middleware: per-client (by IP), 10 capacity, 1 tok/sec. Skip /health.
# Blocked -> 429 + Retry-After. Success -> X-RateLimit-Remaining header.

app3 = FastAPI(title="Rate Limited API")

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        # TODO: init tokens + last_refill

    def consume(self) -> tuple[bool, float]:
        pass  # TODO: refill, consume, return (allowed, remaining)

_buckets: dict[str, TokenBucket] = {}
def _get_bucket(ip: str) -> TokenBucket:
    pass  # TODO: get or create (capacity=10, rate=1.0)

# TODO: Add middleware to app3 (skip /health)

@app3.get("/resource")
async def get_resource():
    return {"data": "protected resource", "timestamp": datetime.utcnow().isoformat()}

@app3.get("/health")
async def health_check():
    return {"status": "ok"}

# ============================================================================
# EXERCISE 4: Debug Broken Code (10 min)
# ============================================================================
# CONCEPTS FROM:
#   Module 01 (FastAPI Foundations):
#     - 01-http-routing-and-decorators.md  -> status codes, response_model, route decorators
#   Module 06 (Testing):
#     - 01-pytest-fixtures-and-basics.md   -> debugging approach, reading test failures
#   Module 08 (Interview Prep):
#     - 02-system-design-and-code-review.md -> "Code Review Checklist" section
#
# ALSO SEE:
#   - 01-interview-fundamentals.md, section "F3: What changed in Pydantic v2?"
#   - 02-system-design-and-code-review.md, "Code Review Exercises" (all 5 exercises)
#
# HINTS:
#   Bug categories to look for:
#   1. [Validation] URL field has no http/https check — use @field_validator
#   2. [Status code] POST should return 201 — add status_code=201 to decorator
#   3. [Slicing] all_bm[skip:limit] is wrong — should be [skip:skip+limit]
#   4. [Identity] `== None` should be `is None` (Pythonic, avoids __eq__ override)
#   5. [Error handling] dict.pop(key) raises KeyError if missing — guard with `if key not in dict`
#      or use .pop(key, None) with a 404 check
# ----------------------------------------------------------------------------
# Bookmark manager with 5 bugs. Find and fix them all.

app4_buggy = FastAPI(title="Bookmark Manager (BUGGY)")
_bookmarks: dict[int, dict[str, Any]] = {}
_bm_counter: int = 0

class BookmarkCreate(BaseModel):
    url: str = Field(min_length=1)       # BUG 1: no http/https validation
    title: str = Field(min_length=1, max_length=200)
    tags: list[str] = []

class BookmarkResponse(BaseModel):
    id: int; url: str; title: str; tags: list[str]; created_at: str

@app4_buggy.post("/bookmarks", response_model=BookmarkResponse)  # BUG 2: should be status_code=201
async def create_bookmark(bm: BookmarkCreate):
    global _bm_counter
    _bm_counter += 1
    _bookmarks[_bm_counter] = {"id": _bm_counter, "url": bm.url, "title": bm.title,
                                "tags": bm.tags, "created_at": datetime.utcnow().isoformat()}
    return BookmarkResponse(**_bookmarks[_bm_counter])

@app4_buggy.get("/bookmarks", response_model=list[BookmarkResponse])
async def list_bookmarks(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    all_bm = list(_bookmarks.values())
    return [BookmarkResponse(**b) for b in all_bm[skip:limit]]  # BUG 3: should be [skip:skip+limit]

@app4_buggy.get("/bookmarks/{bm_id}", response_model=BookmarkResponse)
async def get_bookmark(bm_id: int):
    bm = _bookmarks.get(bm_id)
    if bm == None:  # BUG 4: should be 'bm is None'
        raise HTTPException(404, detail="Bookmark not found")
    return BookmarkResponse(**bm)

@app4_buggy.delete("/bookmarks/{bm_id}", status_code=204)
async def delete_bookmark(bm_id: int):
    _bookmarks.pop(bm_id)  # BUG 5: KeyError if missing — needs default or guard

# ============================================================================
# EXERCISE 5: Code Review (10 min)
# ============================================================================
# CONCEPTS FROM:
#   Module 01 (FastAPI Foundations):
#     - 01-http-routing-and-decorators.md  -> proper route methods (POST vs PATCH/PUT), type hints
#     - 02-dependency-injection.md         -> Pydantic models for request bodies
#   Module 04 (Auth):
#     - 01-authentication-basics.md        -> password hashing, never storing plaintext
#   Module 05 (Advanced API Patterns):
#     - 02-pagination-filtering-and-bulk-operations.md -> route ordering, response_model
#   Module 08 (Interview Prep):
#     - 02-system-design-and-code-review.md -> "Code Review Checklist" section
#
# ALSO SEE:
#   - 01-interview-fundamentals.md, section "F6: Explain FastAPI's response model and serialization"
#   - 02-system-design-and-code-review.md, "Code Review Exercises 1-5"
#
# HINTS — 8+ improvements to identify:
#   1. [Security] password stored & returned in plaintext -> hash with bcrypt/argon2
#   2. [Security] password as query param -> visible in logs/URLs; use request body (Pydantic model)
#   3. [Naming] 'id' and 'data' shadow Python builtins -> rename to _user_counter, _users
#   4. [Validation] no Pydantic models -> zero input validation; add BaseModel classes
#   5. [API design] POST for update should be PATCH or PUT
#   6. [Errors] get_user raises KeyError on missing ID -> return 404 with HTTPException
#   7. [Routing] /user/search unreachable -> /user/{id} matches "search" first; reorder or rename
#   8. [Types] id param has no type hint -> no automatic validation; add `: int`
# ----------------------------------------------------------------------------
# Working but poorly written. List at least 8 improvements.

app5_review = FastAPI()
data = {}
id = 0

@app5_review.post("/user")
async def make_user(name: str, email: str, password: str, age: int):
    global id
    id = id + 1
    data[id] = {"id": id, "name": name, "email": email, "password": password,
                "age": age, "created": str(datetime.utcnow())}
    return data[id]

@app5_review.get("/user")
async def get_users():
    result = []
    for key in data: result.append(data[key])
    return result

@app5_review.get("/user/{id}")
async def get_user(id): return data[id]

@app5_review.post("/user/{id}")
async def update_user(id, name: str = None, email: str = None):
    if name: data[int(id)]["name"] = name
    if email: data[int(id)]["email"] = email
    return data[int(id)]

@app5_review.get("/user/search")
async def search_users(q: str):
    return [data[k] for k in data if q.lower() in data[k]["name"].lower()]

# IMPROVEMENTS TO IDENTIFY:
# 1. [Security] password stored & returned in plaintext
# 2. [Security] password as query param — visible in logs/URLs
# 3. [Naming] 'id' and 'data' shadow Python builtins
# 4. [Validation] no Pydantic models — zero input validation
# 5. [API design] POST for update should be PATCH or PUT
# 6. [Errors] get_user raises KeyError on missing ID (no 404)
# 7. [Routing] /user/search unreachable — /user/{id} matches first
# 8. [Types] id param has no type hint — no automatic validation

# ============================================================================
# EXERCISE 6: Webhook Delivery System with Retry (20 min)
# ============================================================================
# CONCEPTS FROM:
#   Module 01 (FastAPI Foundations):
#     - 01-http-routing-and-decorators.md  -> CRUD routes, status codes, Pydantic models
#     - 02-dependency-injection.md         -> structuring reusable logic
#   Module 02 (Async Python):
#     - 01-asyncio-fundamentals.md         -> async patterns (retry logic could be async)
#     - 02-concurrency-patterns.md         -> retry with backoff
#   Module 05 (Advanced API Patterns):
#     - 02-pagination-filtering-and-bulk-operations.md -> query param filtering
#     - 03-real-time-graphql-and-advanced-patterns.md  -> webhook/event patterns
#   Module 07 (Production):
#     - 03-performance-and-scaling.md      -> retry strategies, resilience
#
# ALSO SEE:
#   - Module 08 examples.py, Example 2 (Notification Service) for similar delivery simulation
#   - Module 08 examples.py, Example 3 (File Pipeline) for status tracking pattern
#   - 02-system-design-and-code-review.md, "Design 2: Notification Service"
#
# KEY IMPORTS AND PATTERNS:
#   from pydantic import BaseModel, Field, field_validator
#   import uuid
#   from datetime import datetime
#
# HINTS:
#   - WebhookCreate:
#       url: str = Field(..., min_length=1)
#       @field_validator("url") -> check v.startswith(("http://", "https://"))
#       event_type: str = Field(..., min_length=1)
#       secret: str | None = None
#   - WebhookResponse: id (str, uuid), url, event_type, created_at
#   - EventTrigger: event_type: str, payload: dict[str, Any]
#   - _simulate_delivery: return (True, None) if "fail" not in url, else (False, "Delivery failed")
#   - _deliver_with_retry pattern:
#       attempts = []
#       for attempt_num in range(max_attempts):
#           # simulated backoff: [0, 1, 2] seconds (just record, don't actually sleep)
#           success, error = _simulate_delivery(wh["url"])
#           attempts.append(DeliveryAttempt(..., attempt=attempt_num+1,
#               status="success" if success else "failed", error=error))
#           if success:
#               break  # stop retrying on success
#       return attempts
#   - POST /events: find all webhooks matching event_type, deliver to each with retry,
#     build DeliveryReport with counts of successful/failed
# ----------------------------------------------------------------------------
# POST /webhooks             -> Register (url http/https, event_type, secret?)
# DELETE /webhooks/{id}      -> Unregister
# GET  /webhooks             -> List (?event_type filter)
# POST /events               -> Deliver to matching webhooks with retry
# GET  /deliveries/{eid}     -> Delivery report
# Retry: max 3 attempts, backoff [0, 1, 2]s (simulated). Stop on success.
# Delivery succeeds if "fail" NOT in webhook URL.

app6 = FastAPI(title="Webhook Delivery System")
_webhooks: dict[str, dict[str, Any]] = {}
_deliveries: dict[str, dict[str, Any]] = {}

class WebhookCreate(BaseModel):
    pass  # TODO: url (http/https), event_type, secret (optional)

class WebhookResponse(BaseModel):
    pass  # TODO: id, url, event_type, created_at

class EventTrigger(BaseModel):
    pass  # TODO: event_type (str), payload (dict)

class DeliveryAttempt(BaseModel):
    webhook_id: str; webhook_url: str; attempt: int
    status: str; scheduled_at: str; error: str | None = None

class DeliveryReport(BaseModel):
    event_id: str; event_type: str; deliveries: list[DeliveryAttempt]
    total_webhooks: int; successful: int; failed: int

def _simulate_delivery(url: str) -> tuple[bool, str | None]:
    pass  # TODO: succeed if 'fail' not in url

def _deliver_with_retry(wh: dict, payload: dict, max_attempts: int = 3) -> list[DeliveryAttempt]:
    pass  # TODO: attempt with backoff [0,1,2]s, stop on success

# TODO: Implement five endpoints on app6

# ============================================================================
# TESTS (run: python exercises.py)
# ============================================================================
def test_exercise_1():
    print("\n=== EXERCISE 1: TODO API ===")
    c = TestClient(app1)
    r = c.post("/todos", json={"title": "Buy milk", "description": "2% milk"})
    if r.status_code == 201:
        t = r.json(); tid = t["id"]
        print(f"  Created: {t}")
        print(f"  Get: {c.get(f'/todos/{tid}').json()}")
        print(f"  Updated: {c.patch(f'/todos/{tid}', json={'completed': True}).json()}")
        print(f"  Completed: {len(c.get('/todos?status=completed').json())} items")
        print(f"  Deleted: {c.delete(f'/todos/{tid}').status_code}")
    else: print(f"  Not implemented yet ({r.status_code})")

def test_exercise_2():
    print("\n=== EXERCISE 2: User Registration ===")
    c = TestClient(app2)
    r = c.post("/register", json={"username": "alice", "email": "alice@ex.com", "password": "Secret123"})
    if r.status_code == 201:
        print(f"  Registered: {r.json()}")
        r = c.post("/login", json={"username": "alice", "password": "Secret123"})
        tok = r.json().get("token", "")
        print(f"  Token: {tok[:16]}...")
        print(f"  Profile: {c.get('/me', headers={'Authorization': f'Bearer {tok}'}).json()}")
    else: print(f"  Not implemented yet ({r.status_code})")

def test_exercise_3():
    print("\n=== EXERCISE 3: Rate Limiter ===")
    b = TokenBucket(capacity=3, refill_rate=1.0)
    out = []
    for i in range(5):
        res = b.consume()
        if res: out.append(f"req{i+1}={'OK' if res[0] else 'BLOCKED'}")
    print(f"  Bucket: {', '.join(out)}" if out else "  Not implemented yet")

def test_exercise_4():
    print("\n=== EXERCISE 4: Debug ===")
    print("  5 bugs: 1) no URL validation  2) missing 201  3) wrong slice")
    print("          4) == None  5) pop() KeyError")

def test_exercise_5():
    print("\n=== EXERCISE 5: Code Review ===")
    print("  8+ improvements to find (see hints in code)")

def test_exercise_6():
    print("\n=== EXERCISE 6: Webhook Delivery ===")
    c = TestClient(app6)
    r = c.post("/webhooks", json={"url": "https://example.com/hook", "event_type": "order.created"})
    if r.status_code == 201:
        print(f"  Webhook: {r.json()}")
        c.post("/webhooks", json={"url": "https://fail.example.com/hook", "event_type": "order.created"})
        r = c.post("/events", json={"event_type": "order.created", "payload": {"order_id": 42}})
        ev = r.json(); eid = ev.get("event_id", "")
        if eid:
            rpt = c.get(f"/deliveries/{eid}").json()
            print(f"  {rpt.get('successful', '?')} ok, {rpt.get('failed', '?')} failed")
    else: print(f"  Not implemented yet ({r.status_code})")

if __name__ == "__main__":
    test_exercise_1(); test_exercise_2(); test_exercise_3()
    test_exercise_4(); test_exercise_5(); test_exercise_6()
    print("\n" + "=" * 60)
    print("Implement each exercise, then re-run to verify.")
    print("=" * 60)
