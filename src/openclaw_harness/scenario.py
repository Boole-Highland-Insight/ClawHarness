from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal


SESSION_MODES = ("per_worker", "per_request", "shared")


@dataclass(slots=True)
class DockerStatsConfig:
    enabled: bool = True
    interval_ms: int = 1000


@dataclass(slots=True)
class PidstatConfig:
    enabled: bool = True
    interval_sec: int = 1


@dataclass(slots=True)
class PerfStatConfig:
    enabled: bool = True


@dataclass(slots=True)
class PerfRecordConfig:
    enabled: bool = False


@dataclass(slots=True)
class CollectorsConfig:
    docker_stats: DockerStatsConfig = field(default_factory=DockerStatsConfig)
    pidstat: PidstatConfig = field(default_factory=PidstatConfig)
    perf_stat: PerfStatConfig = field(default_factory=PerfStatConfig)
    perf_record: PerfRecordConfig = field(default_factory=PerfRecordConfig)


@dataclass(slots=True)
class RuntimeConfig:
    kind: Literal["docker", "host_direct"] = "docker"
    image: str = "openclaw:bench-local"
    container_name_base: str = "openclaw-bench"
    host: str = "127.0.0.1"
    host_port: int = 19189
    container_port: int = 18789
    ws_url: str = ""
    healthcheck_url: str = ""
    gateway_bind: str = "lan"
    gateway_token: str = "openclaw-bench-token"
    host_pid: int | None = None
    build_image_if_missing: bool = True
    force_rebuild: bool = False
    skip_channels: bool = True
    startup_timeout_sec: int = 240
    keep_container: bool = False
    repo_root: str = ""
    dockerfile: str = "Dockerfile"


@dataclass(slots=True)
class ClientConfig:
    role: str = "operator"
    message: str = "/context list"
    session_prefix: str = "bench"
    session_mode: Literal["per_worker", "per_request", "shared"] = "per_worker"
    history_limit: int = 20
    wait_timeout_ms: int = 15000
    send_timeout_ms: int = 15000


@dataclass(slots=True)
class LoadConfig:
    concurrency: int = 1
    requests_per_worker: int = 1
    worker_stagger_ms: int = 0
    request_pause_ms: int = 0


@dataclass(slots=True)
class ScenarioConfig:
    name: str
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    client: ClientConfig = field(default_factory=ClientConfig)
    load: LoadConfig = field(default_factory=LoadConfig)
    collectors: CollectorsConfig = field(default_factory=CollectorsConfig)
    scenario_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["scenario_path"] = self.scenario_path
        return payload


def _merge_dataclass(raw: dict[str, Any] | None, obj: Any) -> Any:
    if not raw:
        return obj
    for key, value in raw.items():
        if not hasattr(obj, key):
            raise ValueError(f"unknown scenario key: {key}")
        setattr(obj, key, value)
    return obj


def load_scenario(path: Path) -> ScenarioConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    scenario = ScenarioConfig(name=raw["name"])
    _merge_dataclass(raw.get("runtime"), scenario.runtime)
    _merge_dataclass(raw.get("client"), scenario.client)
    _merge_dataclass(raw.get("load"), scenario.load)
    collector_raw = raw.get("collectors", {})
    _merge_dataclass(collector_raw.get("docker_stats"), scenario.collectors.docker_stats)
    _merge_dataclass(collector_raw.get("pidstat"), scenario.collectors.pidstat)
    _merge_dataclass(collector_raw.get("perf_stat"), scenario.collectors.perf_stat)
    _merge_dataclass(collector_raw.get("perf_record"), scenario.collectors.perf_record)
    if scenario.client.session_mode not in SESSION_MODES:
        raise ValueError(
            f"invalid session_mode={scenario.client.session_mode!r}; expected one of {SESSION_MODES}",
        )
    if scenario.runtime.kind not in {"docker", "host_direct"}:
        raise ValueError(
            f"invalid runtime.kind={scenario.runtime.kind!r}; expected 'docker' or 'host_direct'",
        )
    scenario.scenario_path = str(path.resolve())
    return scenario
