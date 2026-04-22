from __future__ import annotations

import uuid

from fastapi import HTTPException

from openclaw_harness.utils import run_command, slugify

from .models import (
    ContainerStatus,
    ControlPlaneRoute,
    CreateContainerRequest,
    CreateInstanceRequest,
    CreateTopologyRouteRequest,
    InstanceStatus,
    ManagedContainer,
    ManagedInstance,
    UpdateContainerRequest,
    UpdateInstanceRequest,
)
from .repository import ControlPlaneRepository


class ControlPlaneService:
    """CoClaw control-plane orchestration service.

    Docker container lifecycle references the start/stop approach used by
    `DockerRuntimeManager` in `src/openclaw_harness/runtime.py`.

    Instance config/instance naming references the port stride and naming patterns in
    `build_instance_runtime_config` / `build_instance_container_name` from
    `src/openclaw_harness/runner.py`.
    """

    def __init__(self) -> None:
        self._repo = ControlPlaneRepository()

    @property
    def repository(self) -> ControlPlaneRepository:
        return self._repo

    def create_container(self, payload: CreateContainerRequest) -> ManagedContainer:
        container_id = f"ctr-{uuid.uuid4().hex[:10]}"
        container_name = payload.name or f"openclaw-{container_id}"

        docker_args = [
            "docker",
            "run",
            "-d",
            "--init",
            "--name",
            container_name,
            "-v",
            f"{payload.shared_folder}:/workspace/shared:{payload.mount_strategy.value}",
            "-p",
            f"0.0.0.0:{payload.host_port}:{payload.container_port}",
        ]

        if payload.resources.cpu:
            docker_args.extend(["--cpus", str(payload.resources.cpu)])
        if payload.resources.memory_mb:
            docker_args.extend(["--memory", f"{payload.resources.memory_mb}m"])
        for key, value in payload.env.items():
            docker_args.extend(["-e", f"{key}={value}"])

        docker_args.append(payload.image)

        started = run_command(docker_args, check=False)
        if started.returncode != 0:
            raise HTTPException(status_code=400, detail=started.stderr.strip() or "docker run failed")

        container = ManagedContainer(
            id=container_id,
            name=container_name,
            image=payload.image,
            status=ContainerStatus.RUNNING,
            host_port=payload.host_port,
            container_port=payload.container_port,
            shared_folder=payload.shared_folder,
            mount_strategy=payload.mount_strategy,
            env=payload.env,
            resources=payload.resources,
            instance_count=0,
        )
        self._repo.upsert_container(container)
        return container

    def list_containers(self) -> list[ManagedContainer]:
        containers = list(self._repo.list_containers())
        for item in containers:
            item.status = self._resolve_container_status(item.name)
            item.instance_count = len(self._repo.list_instances(container_id=item.id))
        return containers

    def update_container(self, container_id: str, payload: UpdateContainerRequest) -> ManagedContainer:
        existing = self._repo.get_container(container_id)
        if not existing:
            raise HTTPException(status_code=404, detail="container not found")

        if payload.name and payload.name != existing.name:
            renamed = run_command(["docker", "rename", existing.name, payload.name], check=False)
            if renamed.returncode != 0:
                raise HTTPException(status_code=400, detail=renamed.stderr.strip() or "docker rename failed")
            existing.name = payload.name

        if payload.resources is not None:
            update_cmd = ["docker", "update"]
            if payload.resources.cpu:
                update_cmd.extend(["--cpus", str(payload.resources.cpu)])
            if payload.resources.memory_mb:
                update_cmd.extend(["--memory", f"{payload.resources.memory_mb}m"])
            update_cmd.append(existing.name)
            result = run_command(update_cmd, check=False)
            if result.returncode != 0:
                raise HTTPException(status_code=400, detail=result.stderr.strip() or "docker update failed")
            existing.resources = payload.resources

        if payload.mount_strategy is not None:
            existing.mount_strategy = payload.mount_strategy

        self._repo.upsert_container(existing)
        return existing

    def delete_container(self, container_id: str) -> None:
        existing = self._repo.get_container(container_id)
        if not existing:
            raise HTTPException(status_code=404, detail="container not found")

        result = run_command(["docker", "rm", "-f", existing.name], check=False)
        if result.returncode != 0:
            raise HTTPException(status_code=400, detail=result.stderr.strip() or "docker rm failed")

        for instance in self._repo.list_instances(container_id=container_id):
            self._repo.delete_routes_for_instance(instance.id)
            self._repo.delete_instance(instance.id)

        self._repo.delete_container(container_id)

    def create_instance(self, payload: CreateInstanceRequest) -> ManagedInstance:
        container = self._repo.get_container(payload.container_id)
        if not container:
            raise HTTPException(status_code=404, detail="container not found")

        current_count = len(self._repo.list_instances(container_id=container.id))
        instance_id = f"inst-{uuid.uuid4().hex[:10]}"
        name = self._build_instance_name(container_name=container.name, index=current_count)
        runtime_config = self._build_instance_runtime_config(
            container=container,
            instance_index=current_count,
            requested_host_port=payload.host_port,
            env_overrides=payload.env_overrides,
            worker_count=payload.worker_count,
        )

        instance = ManagedInstance(
            id=instance_id,
            container_id=container.id,
            name=name,
            status=InstanceStatus.RUNNING,
            runtime_config=runtime_config,
        )
        self._repo.upsert_instance(instance)
        return instance

    def list_instances(self, *, container_id: str | None = None) -> list[ManagedInstance]:
        return self._repo.list_instances(container_id=container_id)

    def update_instance(self, instance_id: str, payload: UpdateInstanceRequest) -> ManagedInstance:
        instance = self._repo.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail="instance not found")

        action = (payload.action or "").strip().lower()
        if action == "start":
            instance.status = InstanceStatus.RUNNING
        elif action == "stop":
            instance.status = InstanceStatus.STOPPED
        elif action == "rebuild":
            instance.status = InstanceStatus.RUNNING
            instance.runtime_config["rebuild_at"] = str(uuid.uuid4())

        if payload.config_patch:
            instance.runtime_config.update(payload.config_patch)

        self._repo.upsert_instance(instance)
        return instance

    def delete_instance(self, instance_id: str) -> None:
        existing = self._repo.delete_instance(instance_id)
        if not existing:
            raise HTTPException(status_code=404, detail="instance not found")
        self._repo.delete_routes_for_instance(instance_id)

    def create_topology_route(self, payload: CreateTopologyRouteRequest) -> ControlPlaneRoute:
        master = self._repo.get_instance(payload.master_instance_id)
        worker = self._repo.get_instance(payload.worker_instance_id)
        if not master or not worker:
            raise HTTPException(status_code=404, detail="master or worker instance not found")

        route = ControlPlaneRoute(
            id=f"route-{uuid.uuid4().hex[:10]}",
            master_instance_id=master.id,
            worker_instance_id=worker.id,
            metadata=payload.metadata,
        )
        self._repo.upsert_topology_route(route)
        return route

    def list_topology_routes(self) -> list[ControlPlaneRoute]:
        return list(self._repo.list_topology_routes())

    def _build_instance_name(self, *, container_name: str, index: int) -> str:
        # follow runner.build_instance_container_name style: base + -i{index} + random suffix
        base = slugify(container_name)
        return f"{base}-i{index:02d}-{uuid.uuid4().hex[:8]}"

    def _build_instance_runtime_config(
        self,
        *,
        container: ManagedContainer,
        instance_index: int,
        requested_host_port: int | None,
        env_overrides: dict[str, str],
        worker_count: int,
    ) -> dict[str, object]:
        # follow runner.build_instance_runtime_config style for host port stride.
        host_port = requested_host_port if requested_host_port is not None else container.host_port
        port_stride = 10
        resolved_host_port = host_port + (instance_index * port_stride)
        env = dict(container.env)
        env.update(env_overrides)
        return {
            "image": container.image,
            "host_port": resolved_host_port,
            "container_port": container.container_port,
            "shared_folder": container.shared_folder,
            "mount_strategy": container.mount_strategy.value,
            "env": env,
            "worker_count": worker_count,
        }

    def _resolve_container_status(self, container_name: str) -> ContainerStatus:
        inspected = run_command(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            check=False,
        )
        if inspected.returncode != 0:
            return ContainerStatus.ERROR
        status_text = inspected.stdout.strip().lower()
        if status_text == "running":
            return ContainerStatus.RUNNING
        if status_text in {"created", "paused", "exited"}:
            return ContainerStatus.STOPPED
        return ContainerStatus.ERROR
