from fastapi import Depends, FastAPI

from .config import OpenClawSettings, get_settings
from .control_plane.router import router as control_plane_router

app = FastAPI(title="CoClaw Backend", version="0.2.0")
app.include_router(control_plane_router)


@app.get("/healthz")
def healthz(settings: OpenClawSettings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "docker_socket": settings.docker_socket,
        "shared_folder_root": settings.shared_folder_root,
        "control_plane_url": str(settings.control_plane_url),
    }
