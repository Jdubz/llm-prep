"""Pydantic models for the Async Task Queue Service."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Supported task types."""

    RESIZE_IMAGE = "resize_image"
    GENERATE_REPORT = "generate_report"
    SEND_EMAIL = "send_email"


class TaskPriority(int, Enum):
    """Task priority levels. Lower number = higher priority."""

    HIGH = 1
    MEDIUM = 5
    LOW = 10


class TaskStatusEnum(str, Enum):
    """Possible states a task can be in."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskSubmission(BaseModel):
    """Schema for submitting a new task."""

    task_type: TaskType
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.MEDIUM

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_type": "resize_image",
                    "payload": {"url": "https://example.com/photo.jpg", "width": 800},
                    "priority": 5,
                },
                {
                    "task_type": "generate_report",
                    "payload": {"report_id": "q4-2025", "format": "pdf"},
                    "priority": 1,
                },
                {
                    "task_type": "send_email",
                    "payload": {
                        "to": "user@example.com",
                        "subject": "Hello",
                        "body": "World",
                    },
                    "priority": 10,
                },
            ]
        }
    }


class TaskStatus(BaseModel):
    """Full status representation of a task."""

    id: str
    task_type: TaskType
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    progress: int = Field(default=0, ge=0, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Response model for listing tasks."""

    tasks: list[TaskStatus]
    total: int
