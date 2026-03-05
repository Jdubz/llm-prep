"""Simulated task processors for the Async Task Queue Service.

Each handler simulates real work using asyncio.sleep and reports progress
via a callback. Some tasks randomly fail to demonstrate error handling.
"""

import asyncio
import random
from collections.abc import Callable, Coroutine
from typing import Any

from app.models import TaskType


async def _resize_image(
    payload: dict[str, Any],
    update_progress: Callable[[int], Coroutine],
) -> dict[str, Any]:
    """Simulate resizing an image through several stages."""
    url = payload.get("url", "unknown")
    width = payload.get("width", 800)

    await update_progress(10)
    await asyncio.sleep(0.5)  # "downloading"

    await update_progress(40)
    await asyncio.sleep(0.8)  # "decoding"

    # Random failure: 15% chance the image is corrupt
    if random.random() < 0.15:
        raise RuntimeError(f"Image at {url} is corrupt and cannot be decoded")

    await update_progress(70)
    await asyncio.sleep(0.6)  # "resizing"

    await update_progress(90)
    await asyncio.sleep(0.3)  # "encoding"

    await update_progress(100)
    return {
        "original_url": url,
        "resized_width": width,
        "output_path": f"/tmp/resized_{width}_{url.split('/')[-1]}",
        "file_size_kb": random.randint(50, 500),
    }


async def _generate_report(
    payload: dict[str, Any],
    update_progress: Callable[[int], Coroutine],
) -> dict[str, Any]:
    """Simulate generating a report with multiple stages."""
    report_id = payload.get("report_id", "unknown")
    fmt = payload.get("format", "pdf")

    stages = [
        (15, 0.4, "Querying database"),
        (35, 0.6, "Aggregating data"),
        (55, 0.5, "Building charts"),
        (75, 0.7, "Rendering document"),
        (90, 0.3, "Finalizing"),
    ]

    for progress, delay, _stage in stages:
        await update_progress(progress)
        await asyncio.sleep(delay)

    # Random failure: 10% chance of a data error
    if random.random() < 0.10:
        raise RuntimeError(f"Data integrity error while generating report {report_id}")

    await update_progress(100)
    return {
        "report_id": report_id,
        "format": fmt,
        "pages": random.randint(5, 50),
        "download_url": f"/reports/{report_id}.{fmt}",
    }


async def _send_email(
    payload: dict[str, Any],
    update_progress: Callable[[int], Coroutine],
) -> dict[str, Any]:
    """Simulate sending an email."""
    to = payload.get("to", "unknown@example.com")
    subject = payload.get("subject", "(no subject)")

    await update_progress(25)
    await asyncio.sleep(0.3)  # "composing"

    await update_progress(50)
    await asyncio.sleep(0.2)  # "connecting to SMTP"

    # Random failure: 10% chance the mail server rejects it
    if random.random() < 0.10:
        raise RuntimeError(f"SMTP server rejected message to {to}: 550 Mailbox not found")

    await update_progress(80)
    await asyncio.sleep(0.2)  # "sending"

    await update_progress(100)
    return {
        "to": to,
        "subject": subject,
        "message_id": f"<{random.randint(100000, 999999)}@taskqueue.local>",
        "status": "delivered",
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_HANDLERS: dict[TaskType, Callable] = {
    TaskType.RESIZE_IMAGE: _resize_image,
    TaskType.GENERATE_REPORT: _generate_report,
    TaskType.SEND_EMAIL: _send_email,
}


async def process_task(
    task_type: TaskType,
    payload: dict[str, Any],
    update_progress: Callable[[int], Coroutine],
) -> Any:
    """Route a task to the appropriate handler and return its result.

    Raises:
        ValueError: If the task_type has no registered handler.
        RuntimeError: Propagated from individual handlers on simulated failures.
    """
    handler = _HANDLERS.get(task_type)
    if handler is None:
        raise ValueError(f"No handler registered for task type: {task_type}")
    return await handler(payload, update_progress)
