from __future__ import annotations

from collections.abc import Iterable

from .models import ControlPlaneRoute, ManagedContainer, ManagedInstance


class ControlPlaneRepository:
    def __init__(self) -> None:
        self._containers: dict[str, ManagedContainer] = {}
        self._instances: dict[str, ManagedInstance] = {}
        self._topology: dict[str, ControlPlaneRoute] = {}

    def upsert_container(self, container: ManagedContainer) -> None:
        self._containers[container.id] = container

    def get_container(self, container_id: str) -> ManagedContainer | None:
        return self._containers.get(container_id)

    def delete_container(self, container_id: str) -> ManagedContainer | None:
        return self._containers.pop(container_id, None)

    def list_containers(self) -> Iterable[ManagedContainer]:
        return self._containers.values()

    def upsert_instance(self, instance: ManagedInstance) -> None:
        self._instances[instance.id] = instance

    def get_instance(self, instance_id: str) -> ManagedInstance | None:
        return self._instances.get(instance_id)

    def delete_instance(self, instance_id: str) -> ManagedInstance | None:
        return self._instances.pop(instance_id, None)

    def list_instances(self, *, container_id: str | None = None) -> list[ManagedInstance]:
        all_instances = list(self._instances.values())
        if not container_id:
            return all_instances
        return [item for item in all_instances if item.container_id == container_id]

    def upsert_topology_route(self, route: ControlPlaneRoute) -> None:
        self._topology[route.id] = route

    def list_topology_routes(self) -> Iterable[ControlPlaneRoute]:
        return self._topology.values()

    def delete_routes_for_instance(self, instance_id: str) -> None:
        deleted = [
            route_id
            for route_id, route in self._topology.items()
            if route.master_instance_id == instance_id or route.worker_instance_id == instance_id
        ]
        for route_id in deleted:
            del self._topology[route_id]
