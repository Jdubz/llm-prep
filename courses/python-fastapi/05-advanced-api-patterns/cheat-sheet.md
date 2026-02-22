# Module 05 Cheat Sheet: Advanced API Patterns

## Background Task Options at a Glance

| | BackgroundTasks | Celery | ARQ | Dramatiq |
|---|---|---|---|---|
| **Install** | Built-in | `pip install celery[redis]` | `pip install arq` | `pip install dramatiq[redis]` |
| **Broker** | None (in-process) | Redis / RabbitMQ | Redis | Redis / RabbitMQ |
| **Async** | Yes | No (sync workers) | Yes | No |
| **Retries** | No | Yes | Yes | Yes |
| **Scheduling** | No | Yes (celery-beat) | Yes (cron jobs) | No |
| **When to use** | Lightweight, fire-and-forget | Complex workflows | Async-native apps | Simple reliable queues |

---

## WebSocket Template

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, ws: WebSocket):
        await ws.accept()
        self.active[client_id] = ws

    def disconnect(self, client_id: str):
        self.active.pop(client_id, None)

    async def broadcast(self, message: str):
        for ws in self.active.values():
            await ws.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def ws_endpoint(ws: WebSocket, client_id: str, token: str = Query(...)):
    await manager.connect(client_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            await manager.broadcast(f"{client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

---

## SSE Streaming Template

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

**LLM token streaming:**

```python
async def stream_llm(prompt: str):
    stream = await openai_client.chat.completions.create(
        model="gpt-4o", messages=[{"role": "user", "content": prompt}], stream=True)
    async for chunk in stream:
        if chunk.choices[0].delta.content:
            yield f"data: {json.dumps({'token': chunk.choices[0].delta.content})}\n\n"
    yield "data: [DONE]\n\n"
```

---

## File Upload Template

```python
from fastapi import File, UploadFile

# Simple
@app.post("/upload/")
async def upload(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "size": len(contents)}

# Streaming (won't OOM)
@app.post("/upload/large")
async def upload_large(file: UploadFile):
    import aiofiles
    async with aiofiles.open(f"/tmp/{file.filename}", "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

# Presigned S3 (production)
@app.post("/upload/presigned")
async def presigned(filename: str):
    url = s3.generate_presigned_url("put_object",
        Params={"Bucket": "my-bucket", "Key": f"uploads/{filename}"}, ExpiresIn=3600)
    return {"upload_url": url}
```

---

## Pagination Templates

**Offset (simple, has consistency issues):**

```python
@app.get("/items")
async def list_items(offset: int = 0, limit: int = Query(default=20, le=100)):
    total = await db.scalar(select(func.count()).select_from(Item))
    items = await db.execute(select(Item).offset(offset).limit(limit))
    return {"items": items.scalars().all(), "total": total}
```

**Cursor (consistent, no page-jump):**

```python
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

## Rate Limiting Setup

```python
# SlowAPI (quick)
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/data")
@limiter.limit("100/minute")
async def get_data(request: Request): ...

# Redis-based (multi-instance)
class RateLimit:
    def __init__(self, times: int, seconds: int):
        self.times, self.seconds = times, seconds
    async def __call__(self, request: Request):
        key = f"rl:{request.client.host}:{request.url.path}"
        count = await redis.incr(key)
        if count == 1: await redis.expire(key, self.seconds)
        if count > self.times: raise HTTPException(429, "Rate limit exceeded")

@app.get("/search", dependencies=[Depends(RateLimit(30, 60))])
async def search(q: str): ...
```

---

## Quick Reference

**Real-time pattern selection:**
- Bidirectional --> WebSocket
- Server-push, text, auto-reconnect --> SSE
- HTTP compat + low latency --> Long polling
- Simple, infrequent updates --> Short polling

**API versioning:**
- URL prefix (most common): `app.include_router(v1, prefix="/api/v1")`
- Header-based: `X-API-Version: 2`
- Content negotiation: `Accept: application/vnd.myapi.v2+json`
