# 02 – Pagination, Filtering, and Bulk Operations

## Offset-Based Pagination (Simple, Has Consistency Issues)

```python
from pydantic import BaseModel, Field
from fastapi import Query, Depends
from sqlalchemy import func, select

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

# Compact form
@app.get("/items")
async def list_items(offset: int = 0, limit: int = Query(default=20, le=100)):
    total = await db.scalar(select(func.count()).select_from(Item))
    items = await db.execute(select(Item).offset(offset).limit(limit))
    return {"items": items.scalars().all(), "total": total}
```

---

## Cursor-Based Pagination (Consistent, No Page-Jump)

Cursor pagination prevents items appearing on multiple pages or going missing when data is
inserted or deleted between page requests. Trade-off: you lose "jump to page N."

```python
import base64
from datetime import datetime

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

# Simple cursor by ID only
@app.get("/items")
async def list_items(cursor: str | None = None, limit: int = 20):
    query = select(Item).order_by(Item.id.desc())
    if cursor:
        query = query.where(Item.id < decode_cursor(cursor))
    items = list((await db.execute(query.limit(limit + 1))).scalars().all())
    has_more = len(items) > limit
    items = items[:limit]
    return {"items": items,
            "next_cursor": encode_cursor(items[-1].id) if has_more else None}
```

---

## Filtering and Sorting

```python
from enum import Enum
from typing import ClassVar
from pydantic import BaseModel, model_validator

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

## Rate Limiting

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

Works across multiple application instances because the counter lives in Redis:

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

# Compact form
class RateLimit:
    def __init__(self, times: int, seconds: int):
        self.times, self.seconds = times, seconds
    async def __call__(self, request: Request):
        key = f"rl:{request.client.host}:{request.url.path}"
        count = await redis.incr(key)
        if count == 1: await redis.expire(key, self.seconds)
        if count > self.times: raise HTTPException(429, "Rate limit exceeded")
```

---

## Bulk Operations

### Batch Create with Error Collection

```python
from sqlalchemy.exc import IntegrityError

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

### Bulk Update

```python
from sqlalchemy import update

@app.patch("/users/bulk-deactivate")
async def bulk_deactivate(user_ids: list[int], db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        update(User).where(User.id.in_(user_ids)).values(is_active=False).returning(User.id)
    )
    deactivated_ids = result.scalars().all()
    await db.commit()
    return {"deactivated": len(deactivated_ids), "ids": deactivated_ids}
```

### Bulk Delete

```python
from sqlalchemy import delete

@app.delete("/users/bulk")
async def bulk_delete(user_ids: list[int], db: AsyncSession = Depends(get_db)):
    await db.execute(delete(User).where(User.id.in_(user_ids)))
    await db.commit()
    return {"deleted": len(user_ids)}
```

---

## API Versioning Strategies

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

**Versioning options:**
- URL prefix (most common): `app.include_router(v1, prefix="/api/v1")`
- Header-based: `X-API-Version: 2`
- Content negotiation: `Accept: application/vnd.myapi.v2+json`

---

## Key Takeaways

- Offset pagination is simple but has consistency issues when data changes between pages.
- Cursor pagination prevents missing/duplicate items but loses random page access.
- Always whitelist `sort_by` fields to prevent SQL injection via unvalidated column names.
- Rate limiting across multiple instances requires a shared store (Redis) — in-memory won't work.
- Bulk operations should collect per-item errors rather than failing the entire batch.
- Validate and allowlist sort fields to prevent arbitrary column access.
