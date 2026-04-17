from fastapi import Depends, FastAPI

from .config import OpenClawSettings, get_settings
from .models import Container, OpenClawInstance
from .services import HarnessService

app = FastAPI(title="CoClaw Backend", version="0.1.0")
service = HarnessService()


@app.get("/healthz")
def healthz(settings: OpenClawSettings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "docker_socket": settings.docker_socket,
        "shared_folder_root": settings.shared_folder_root,
        "control_plane_url": str(settings.control_plane_url),
    }


@app.get("/containers", response_model=list[Container])
def list_containers() -> list[Container]:
    return list(service.repository.list_containers())


@app.get("/instances", response_model=list[OpenClawInstance])
def list_instances() -> list[OpenClawInstance]:
    return list(service.repository.list_instances())
