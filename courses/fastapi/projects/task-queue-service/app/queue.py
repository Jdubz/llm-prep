"""In-memory async task queue with priority support and concurrency control.

The TaskQueue manages the full lifecycle of tasks:
  1. Submission  -- caller gets back a task_id immediately
  2. Queueing    -- task waits in an asyncio.PriorityQueue
  3. Processing  -- a background worker picks it up (bounded by a semaphore)
  4. Completion  -- result or error is recorded, SSE subscribers are notified
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.models import (
    TaskPriority,
    TaskStatus,
    TaskStatusEnum,
    TaskType,
)
from app.workers import process_task


class TaskQueue:
    """Async priority task queue with configurable concurrency."""

    def __init__(self, max_workers: int = 3) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, float, str]] = (
            asyncio.PriorityQueue()
        )
        self._tasks: dict[str, TaskStatus] = {}
        self._semaphore = asyncio.Semaphore(max_workers)
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._running = False
        # SSE subscribers: task_id -> list of asyncio.Queue
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background worker loop."""
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        """Gracefully shut down the worker loop."""
        self._running = False
        if self._worker_task is not None:
            # Push a sentinel so the worker unblocks from queue.get()
            await self._queue.put((-1, 0.0, "__shutdown__"))
            await self._worker_task
            self._worker_task = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def submit(
        self,
        task_type: TaskType,
        payload: dict[str, Any],
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> str:
        """Submit a new task and return its id."""
        task_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)

        status = TaskStatus(
            id=task_id,
            task_type=task_type,
            status=TaskStatusEnum.PENDING,
            priority=priority,
            progress=0,
            payload=payload,
            created_at=now,
        )
        self._tasks[task_id] = status

        # PriorityQueue ordering: (priority_value, submission_timestamp, task_id)
        await self._queue.put((priority.value, now.timestamp(), task_id))
        await self._notify(task_id, {"status": "pending", "progress": 0})
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskStatus]:
        """Return current status of a task, or None."""
        return self._tasks.get(task_id)

    def list_tasks(
        self, status_filter: Optional[TaskStatusEnum] = None
    ) -> list[TaskStatus]:
        """Return all tasks, optionally filtered by status."""
        tasks = list(self._tasks.values())
        if status_filter is not None:
            tasks = [t for t in tasks if t.status == status_filter]
        # Most recent first
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task if it is still pending. Returns True on success."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        if task.status != TaskStatusEnum.PENDING:
            return False
        task.status = TaskStatusEnum.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        await self._notify(task_id, {"status": "cancelled", "progress": 0})
        return True

    # ------------------------------------------------------------------
    # SSE subscription
    # ------------------------------------------------------------------

    def subscribe(self, task_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Create and return an SSE event queue for a task."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.setdefault(task_id, []).append(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove an SSE event queue."""
        subs = self._subscribers.get(task_id, [])
        if q in subs:
            subs.remove(q)

    async def _notify(self, task_id: str, data: dict[str, Any]) -> None:
        """Push an event to all subscribers of a task."""
        for q in self._subscribers.get(task_id, []):
            await q.put(data)

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    async def _worker_loop(self) -> None:
        """Continuously pull tasks from the queue and process them."""
        pending_processors: set[asyncio.Task[None]] = set()

        while self._running:
            priority_val, _ts, task_id = await self._queue.get()

            # Sentinel check
            if task_id == "__shutdown__":
                break

            task = self._tasks.get(task_id)
            if task is None or task.status == TaskStatusEnum.CANCELLED:
                continue

            # Spawn bounded processor
            processor = asyncio.create_task(self._process(task_id))
            pending_processors.add(processor)
            processor.add_done_callback(pending_processors.discard)

        # Drain remaining processors on shutdown
        if pending_processors:
            await asyncio.gather(*pending_processors, return_exceptions=True)

    async def _process(self, task_id: str) -> None:
        """Process a single task, respecting the concurrency semaphore."""
        async with self._semaphore:
            task = self._tasks.get(task_id)
            if task is None or task.status == TaskStatusEnum.CANCELLED:
                return

            task.status = TaskStatusEnum.RUNNING
            task.started_at = datetime.now(timezone.utc)
            await self._notify(task_id, {"status": "running", "progress": 0})

            async def _update_progress(value: int) -> None:
                task.progress = value
                await self._notify(
                    task_id, {"status": "running", "progress": value}
                )

            try:
                result = await process_task(task.task_type, task.payload, _update_progress)
                task.status = TaskStatusEnum.COMPLETED
                task.progress = 100
                task.result = result
                task.completed_at = datetime.now(timezone.utc)
                await self._notify(
                    task_id,
                    {"status": "completed", "progress": 100, "result": result},
                )
            except Exception as exc:
                task.status = TaskStatusEnum.FAILED
                task.error = str(exc)
                task.completed_at = datetime.now(timezone.utc)
                await self._notify(
                    task_id,
                    {"status": "failed", "progress": task.progress, "error": str(exc)},
                )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

task_queue = TaskQueue(max_workers=3)
