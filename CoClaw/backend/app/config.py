from functools import lru_cache

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenClawSettings(BaseSettings):
    """Runtime settings for OpenClaw control-plane integration."""

    model_config = SettingsConfigDict(env_prefix="COCLAW_", env_file=".env", extra="ignore")

    docker_socket: str = Field(default="unix:///var/run/docker.sock")
    shared_folder_root: str = Field(default="/var/lib/openclaw/shared")
    control_plane_url: AnyHttpUrl = Field(default="http://localhost:8080")


@lru_cache(maxsize=1)
def get_settings() -> OpenClawSettings:
    return OpenClawSettings()
