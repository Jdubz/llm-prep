"""API routes for the Async Task Queue Service."""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.models import (
    TaskListResponse,
    TaskStatus,
    TaskStatusEnum,
    TaskSubmission,
)
from app.queue import task_queue

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", status_code=202, response_model=TaskStatus)
async def submit_task(submission: TaskSubmission) -> TaskStatus:
    """Submit a new task to the queue.

    Returns immediately with a 202 Accepted and the initial task status.
    """
    task_id = await task_queue.submit(
        task_type=submission.task_type,
        payload=submission.payload,
        priority=submission.priority,
    )
    task = task_queue.get_task(task_id)
    if task is None:  # pragma: no cover – defensive
        raise HTTPException(status_code=500, detail="Task creation failed")
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[TaskStatusEnum] = Query(
        default=None, description="Filter by task status"
    ),
) -> TaskListResponse:
    """List all tasks, optionally filtered by status."""
    tasks = task_queue.list_tasks(status_filter=status)
    return TaskListResponse(tasks=tasks, total=len(tasks))


@router.get("/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str) -> TaskStatus:
    """Get the current status of a task."""
    task = task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/stream")
async def stream_task_progress(task_id: str) -> EventSourceResponse:
    """Stream task progress updates via Server-Sent Events.

    The stream emits JSON objects with at least `status` and `progress` keys.
    It closes automatically when the task reaches a terminal state
    (completed, failed, or cancelled).
    """
    task = task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    sub_queue = task_queue.subscribe(task_id)

    async def _event_generator():
        try:
            # Emit the current state first so late subscribers catch up
            yield {
                "event": "progress",
                "data": json.dumps(
                    {"status": task.status.value, "progress": task.progress}
                ),
            }

            # If already terminal, close immediately
            if task.status in (
                TaskStatusEnum.COMPLETED,
                TaskStatusEnum.FAILED,
                TaskStatusEnum.CANCELLED,
            ):
                return

            while True:
                try:
                    event = await asyncio.wait_for(sub_queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send a keep-alive comment
                    yield {"comment": "keep-alive"}
                    continue

                yield {"event": "progress", "data": json.dumps(event)}

                if event.get("status") in ("completed", "failed", "cancelled"):
                    return
        finally:
            task_queue.unsubscribe(task_id, sub_queue)

    return EventSourceResponse(_event_generator())


@router.delete("/{task_id}", status_code=200)
async def cancel_task(task_id: str) -> dict:
    """Cancel a pending task.

    Only tasks in the 'pending' state can be cancelled.
    """
    task = task_queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    success = await task_queue.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Task cannot be cancelled (current status: {task.status.value})",
        )
    return {"detail": "Task cancelled", "task_id": task_id}
