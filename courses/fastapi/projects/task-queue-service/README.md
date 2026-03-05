# Async Task Queue Service

A fully in-memory async task queue built with FastAPI. Tasks are submitted via
a REST API, processed by background workers with configurable concurrency, and
clients can poll for status or stream real-time progress updates over
Server-Sent Events (SSE).

## Learning Objectives

- Design a FastAPI application using **lifespan events** to manage background
  workers that start and stop cleanly with the server.
- Use `asyncio.PriorityQueue` and `asyncio.Semaphore` to build a **bounded,
  priority-aware work queue** entirely in async Python.
- Implement **SSE streaming** endpoints so clients can receive live progress
  updates without polling.
- Apply **Pydantic models** for strict request validation, response
  serialization, and enum-based type safety.
- Write **middleware** for request logging and lightweight metrics collection.
- Build a **comprehensive async test suite** using `httpx.AsyncClient` against
  the ASGI app with no running server.

## Course Modules Covered

| Module | Topic | How It Appears Here |
|--------|-------|---------------------|
| **02 -- Pydantic & Data Validation** | Models, enums, field constraints | `app/models.py` -- `TaskSubmission`, `TaskStatus`, enums for priority/status/type |
| **05 -- Async Python & Background Tasks** | asyncio primitives, lifespan, background workers | `app/queue.py` -- PriorityQueue, Semaphore, worker loop; `app/main.py` -- lifespan |
| **07 -- Middleware & Advanced Patterns** | Middleware, SSE, metrics | `app/middleware.py` -- logging + metrics; `app/routes.py` -- SSE streaming |

## Architecture Overview

```
Client                        FastAPI App
------                        ----------
POST /tasks  ------>  routes.py  ------>  queue.submit()
                                           |
                                    PriorityQueue
                                           |
                                    worker_loop() (background task)
                                           |
                                    Semaphore (max 3 concurrent)
                                           |
                                    workers.py  process_task()
                                           |
                               +-----+-----+-----+
                               |           |           |
                        resize_image  gen_report  send_email
                               |           |           |
                          progress callbacks --> SSE subscribers
                               |
                        TaskStatus updated in-memory
                               |
GET /tasks/{id}  <------  routes.py  <------  queue.get_task()
GET /tasks/{id}/stream  <---  SSE EventSourceResponse
```

1. **Submit** -- `POST /tasks` validates the request body against
   `TaskSubmission`, enqueues a `(priority, timestamp, task_id)` tuple, and
   returns `202 Accepted` with the initial `TaskStatus`.

2. **Queue** -- An `asyncio.PriorityQueue` orders tasks by priority (lower
   number = higher priority) with FIFO tie-breaking via timestamp.

3. **Worker loop** -- A single background coroutine pulls from the queue and
   spawns processor tasks bounded by an `asyncio.Semaphore` (default 3
   concurrent workers).

4. **Processing** -- `workers.py` dispatches by `task_type` to a simulated
   handler that sleeps through stages, calls a progress callback, and may
   randomly raise to simulate failures.

5. **Observe** -- Clients poll `GET /tasks/{id}` or open `GET
   /tasks/{id}/stream` for real-time SSE events carrying `{status, progress}`.

6. **Cancel** -- `DELETE /tasks/{id}` marks a pending task as cancelled so the
   worker skips it when dequeued.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn app.main:app --reload
```

The interactive API docs are available at <http://localhost:8000/docs>.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tasks` | Submit a new task (returns 202) |
| `GET` | `/tasks` | List all tasks (optional `?status=pending`) |
| `GET` | `/tasks/{id}` | Get a single task's current status |
| `GET` | `/tasks/{id}/stream` | SSE stream of progress updates |
| `DELETE` | `/tasks/{id}` | Cancel a pending task |
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Request count and average latency |

### Example: submit a task

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"task_type": "generate_report", "payload": {"report_id": "q4"}, "priority": 1}'
```

### Example: stream progress

```bash
curl -N http://localhost:8000/tasks/<task_id>/stream
```

## Running Tests

```bash
pip install pytest anyio pytest-asyncio httpx
python -m pytest tests/ -v
```
