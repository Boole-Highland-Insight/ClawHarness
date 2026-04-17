from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class InstanceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class Container(BaseModel):
    id: str
    name: str
    image: str
    status: InstanceStatus = InstanceStatus.STOPPED


class OpenClawInstance(BaseModel):
    id: str
    container_id: str
    name: str
    status: InstanceStatus = InstanceStatus.STOPPED
    endpoint: str | None = None


class Agent(BaseModel):
    id: str
    instance_id: str
    name: str
    model: str | None = None
    online: bool = False


class Session(BaseModel):
    id: str
    agent_id: str
    user_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True
