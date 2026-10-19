"""Shared task and state models for EventAI agents."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


class EngineeringTask(BaseModel):
    """Canonical model for tasks dispatched to humans or agents."""

    task_id: str
    workflow_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )
    task_type: str
    description: str
    assigned_role: str
    input_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TaskExecutionState(BaseModel):
    """Shared state representation passed between workflow nodes or handovers."""

    task: EngineeringTask
    status: Literal["pending", "in_progress", "completed", "failed", "escalated"] = "pending"
    artifacts: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)