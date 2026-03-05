"""Complete test suite for the Async Task Queue Service.

Uses httpx.AsyncClient with FastAPI's ASGITransport for fully async tests.
Each test gets a fresh TaskQueue instance to avoid event-loop binding issues
across tests (asyncio.PriorityQueue binds to the loop that first uses it).

Run with:
    python -m pytest tests/ -v
"""

import asyncio
import json
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.middleware import metrics
from app.queue import TaskQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def fresh_queue():
    """Create a brand-new TaskQueue per test, patch it into app.queue and
    app.routes, start its worker, and tear it down afterwards."""
    q = TaskQueue(max_workers=3)
    q.start()

    # Reset metrics
    metrics.total_requests = 0
    metrics.total_duration_ms = 0.0
    metrics.status_counts.clear()

    # Patch the module-level task_queue used by routes.py
    with patch("app.routes.task_queue", q), patch("app.queue.task_queue", q):
        yield q

    await q.stop()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _wait_for_terminal(
    client: httpx.AsyncClient, task_id: str, max_seconds: float = 15.0
) -> dict:
    """Poll a task until it reaches a terminal state."""
    terminal = {"completed", "failed", "cancelled"}
    deadline = asyncio.get_event_loop().time() + max_seconds
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/tasks/{task_id}")
        data = resp.json()
        if data["status"] in terminal:
            return data
        await asyncio.sleep(0.15)
    resp = await client.get(f"/tasks/{task_id}")
    return resp.json()


# ---------------------------------------------------------------------------
# Health & metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check(client: httpx.AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_metrics_endpoint(client: httpx.AsyncClient):
    await client.get("/health")
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert data["total_requests"] >= 1


# ---------------------------------------------------------------------------
# Task submission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_task(client: httpx.AsyncClient):
    resp = await client.post(
        "/tasks",
        json={
            "task_type": "send_email",
            "payload": {"to": "a@b.com", "subject": "Hi"},
            "priority": 5,
        },
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "id" in body
    assert body["status"] == "pending"
    assert body["task_type"] == "send_email"


@pytest.mark.asyncio
async def test_submit_invalid_task_type(client: httpx.AsyncClient):
    resp = await client.post(
        "/tasks",
        json={"task_type": "nonexistent", "payload": {}},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Status polling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_task_status(client: httpx.AsyncClient):
    resp = await client.post(
        "/tasks",
        json={"task_type": "send_email", "payload": {"to": "x@y.com"}},
    )
    task_id = resp.json()["id"]

    status_resp = await client.get(f"/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["id"] == task_id


@pytest.mark.asyncio
async def test_get_nonexistent_task(client: httpx.AsyncClient):
    resp = await client.get("/tasks/does_not_exist")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Task completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task_completion(client: httpx.AsyncClient):
    resp = await client.post(
        "/tasks",
        json={
            "task_type": "send_email",
            "payload": {"to": "test@test.com", "subject": "Test"},
            "priority": 1,
        },
    )
    task_id = resp.json()["id"]
    final = await _wait_for_terminal(client, task_id)
    assert final["status"] in {"completed", "failed"}

    if final["status"] == "completed":
        assert final["progress"] == 100
        assert final["result"] is not None
    else:
        assert final["error"] is not None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_task_has_error_field(client: httpx.AsyncClient):
    """Submit a report task and verify schema for terminal state."""
    resp = await client.post(
        "/tasks",
        json={"task_type": "generate_report", "payload": {"report_id": "err-test"}},
    )
    task_id = resp.json()["id"]
    final = await _wait_for_terminal(client, task_id)

    if final["status"] == "failed":
        assert isinstance(final["error"], str)
        assert len(final["error"]) > 0
    else:
        assert final["status"] == "completed"
        assert final["result"] is not None


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_pending_task(client: httpx.AsyncClient):
    resp = await client.post(
        "/tasks",
        json={
            "task_type": "generate_report",
            "payload": {"report_id": "cancel-me"},
            "priority": 10,
        },
    )
    task_id = resp.json()["id"]
    del_resp = await client.delete(f"/tasks/{task_id}")

    if del_resp.status_code == 200:
        assert del_resp.json()["detail"] == "Task cancelled"
        status = await client.get(f"/tasks/{task_id}")
        assert status.json()["status"] == "cancelled"
    else:
        # Already picked up by worker
        assert del_resp.status_code == 409


@pytest.mark.asyncio
async def test_cancel_nonexistent_task(client: httpx.AsyncClient):
    resp = await client.delete("/tasks/nope")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Listing & filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_tasks(client: httpx.AsyncClient):
    await client.post(
        "/tasks",
        json={"task_type": "send_email", "payload": {"to": "a@b.com"}},
    )
    await client.post(
        "/tasks",
        json={"task_type": "resize_image", "payload": {"url": "http://img.png"}},
    )
    resp = await client.get("/tasks")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(client: httpx.AsyncClient):
    resp = await client.post(
        "/tasks",
        json={"task_type": "send_email", "payload": {"to": "x@y.com"}},
    )
    task_id = resp.json()["id"]
    await _wait_for_terminal(client, task_id)

    final = (await client.get(f"/tasks/{task_id}")).json()
    filter_status = final["status"]

    resp = await client.get("/tasks", params={"status": filter_status})
    assert resp.status_code == 200
    for t in resp.json()["tasks"]:
        assert t["status"] == filter_status


# ---------------------------------------------------------------------------
# Concurrent task processing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_task_processing(client: httpx.AsyncClient):
    """Submit several tasks and verify they all complete."""
    task_ids = []
    for i in range(5):
        resp = await client.post(
            "/tasks",
            json={
                "task_type": "send_email",
                "payload": {"to": f"user{i}@test.com", "subject": f"Msg {i}"},
                "priority": 5,
            },
        )
        assert resp.status_code == 202
        task_ids.append(resp.json()["id"])

    terminal = {"completed", "failed"}
    for _ in range(200):
        statuses = []
        for tid in task_ids:
            s = await client.get(f"/tasks/{tid}")
            statuses.append(s.json()["status"])
        if all(s in terminal for s in statuses):
            break
        await asyncio.sleep(0.15)

    for tid in task_ids:
        s = await client.get(f"/tasks/{tid}")
        assert s.json()["status"] in terminal


# ---------------------------------------------------------------------------
# SSE streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_stream_returns_events(client: httpx.AsyncClient):
    """Verify the SSE endpoint returns at least the initial progress event."""
    resp = await client.post(
        "/tasks",
        json={"task_type": "send_email", "payload": {"to": "sse@test.com"}},
    )
    task_id = resp.json()["id"]

    # Wait for the task to finish so the SSE endpoint emits the snapshot
    # and closes immediately (no hanging)
    await _wait_for_terminal(client, task_id)

    resp = await client.get(f"/tasks/{task_id}/stream")
    assert resp.status_code == 200
    assert "data:" in resp.text


@pytest.mark.asyncio
async def test_sse_stream_nonexistent_task(client: httpx.AsyncClient):
    resp = await client.get("/tasks/nonexistent/stream")
    assert resp.status_code == 404
