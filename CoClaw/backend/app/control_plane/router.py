from __future__ import annotations

from fastapi import APIRouter, Query, Response, status

from .models import (
    ControlPlaneRoute,
    CreateContainerRequest,
    CreateInstanceRequest,
    CreateTopologyRouteRequest,
    ManagedContainer,
    ManagedInstance,
    UpdateContainerRequest,
    UpdateInstanceRequest,
)
from .service import ControlPlaneService

router = APIRouter(tags=["control-plane"])
service = ControlPlaneService()


@router.post("/containers", response_model=ManagedContainer, status_code=status.HTTP_201_CREATED)
def create_container(payload: CreateContainerRequest) -> ManagedContainer:
    return service.create_container(payload)


@router.get("/containers", response_model=list[ManagedContainer])
def list_containers() -> list[ManagedContainer]:
    return service.list_containers()


@router.patch("/containers/{container_id}", response_model=ManagedContainer)
def update_container(container_id: str, payload: UpdateContainerRequest) -> ManagedContainer:
    return service.update_container(container_id, payload)


@router.delete("/containers/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_container(container_id: str) -> Response:
    service.delete_container(container_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/instances", response_model=ManagedInstance, status_code=status.HTTP_201_CREATED)
def create_instance(payload: CreateInstanceRequest) -> ManagedInstance:
    return service.create_instance(payload)


@router.get("/instances", response_model=list[ManagedInstance])
def list_instances(containerId: str | None = Query(default=None)) -> list[ManagedInstance]:
    return service.list_instances(container_id=containerId)


@router.patch("/instances/{instance_id}", response_model=ManagedInstance)
def update_instance(instance_id: str, payload: UpdateInstanceRequest) -> ManagedInstance:
    return service.update_instance(instance_id, payload)


@router.delete("/instances/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instance(instance_id: str) -> Response:
    service.delete_instance(instance_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/control-plane-topology/routes",
    response_model=ControlPlaneRoute,
    status_code=status.HTTP_201_CREATED,
)
def create_topology_route(payload: CreateTopologyRouteRequest) -> ControlPlaneRoute:
    return service.create_topology_route(payload)


@router.get("/control-plane-topology/routes", response_model=list[ControlPlaneRoute])
def list_topology_routes() -> list[ControlPlaneRoute]:
    return service.list_topology_routes()
