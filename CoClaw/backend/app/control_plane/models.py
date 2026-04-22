from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ResourceLimit(BaseModel):
    cpu: float | None = None
    memory_mb: int | None = None


class MountStrategy(str, Enum):
    READ_WRITE = "rw"
    READ_ONLY = "ro"


class ContainerStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class InstanceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ManagedContainer(BaseModel):
    id: str
    name: str
    image: str
    status: ContainerStatus = ContainerStatus.STOPPED
    host_port: int
    container_port: int
    shared_folder: str
    mount_strategy: MountStrategy = MountStrategy.READ_WRITE
    env: dict[str, str] = Field(default_factory=dict)
    resources: ResourceLimit = Field(default_factory=ResourceLimit)
    instance_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateContainerRequest(BaseModel):
    name: str | None = None
    image: str
    host_port: int = 8080
    container_port: int = 8080
    shared_folder: str
    env: dict[str, str] = Field(default_factory=dict)
    resources: ResourceLimit = Field(default_factory=ResourceLimit)
    mount_strategy: MountStrategy = MountStrategy.READ_WRITE


class UpdateContainerRequest(BaseModel):
    name: str | None = None
    resources: ResourceLimit | None = None
    mount_strategy: MountStrategy | None = None


class ManagedInstance(BaseModel):
    id: str
    container_id: str
    name: str
    status: InstanceStatus = InstanceStatus.STOPPED
    runtime_config: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateInstanceRequest(BaseModel):
    container_id: str
    worker_count: int = 1
    host_port: int | None = None
    env_overrides: dict[str, str] = Field(default_factory=dict)


class UpdateInstanceRequest(BaseModel):
    action: str | None = Field(default=None, description="start | stop | rebuild")
    config_patch: dict[str, object] | None = None


class ControlPlaneRoute(BaseModel):
    id: str
    master_instance_id: str
    worker_instance_id: str
    route_type: str = "agent2agent"
    metadata: dict[str, str] = Field(default_factory=dict)


class CreateTopologyRouteRequest(BaseModel):
    master_instance_id: str
    worker_instance_id: str
    metadata: dict[str, str] = Field(default_factory=dict)
