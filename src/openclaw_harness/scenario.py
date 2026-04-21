from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .task import load_task, resolve_task_path


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
    interval_ms: int = 1000
    events: list[str] = field(
        default_factory=lambda: [
            "context-switches",
            "cpu-migrations",
            "page-faults",
            "minor-faults",
            "major-faults",
            "cache-references",
            "cache-misses",
            "cpu-clock",
            "task-clock",
        ],
    )


@dataclass(slots=True)
class PerfRecordConfig:
    enabled: bool = False


@dataclass(slots=True)
class StraceConfig:
    enabled: bool = False
    interval_sec: int = 1
    syscalls: list[str] = field(
        default_factory=lambda: [
            "read",
            "write",
            "openat",
            "statx",
            "newfstatat",
            "pread64",
            "futex",
            "clone",
            "sched_yield",
            "epoll_wait",
            "clock_nanosleep",
            "poll",
            "select",
            "accept4",
        ],
    )


@dataclass(slots=True)
class NodeTraceConfig:
    enabled: bool = False
    categories: list[str] = field(
        default_factory=lambda: [
            "v8",
            "node",
            "node.async_hooks",
            "node.environment",
            "node.fs",
        ],
    )


@dataclass(slots=True)
class NpuSmiConfig:
    enabled: bool = False
    interval_sec: int = 1
    auto_discover: bool = True
    card_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class CollectorsConfig:
    docker_stats: DockerStatsConfig = field(default_factory=DockerStatsConfig)
    pidstat: PidstatConfig = field(default_factory=PidstatConfig)
    strace: StraceConfig = field(default_factory=StraceConfig)
    node_trace: NodeTraceConfig = field(default_factory=NodeTraceConfig)
    perf_stat: PerfStatConfig = field(default_factory=PerfStatConfig)
    perf_record: PerfRecordConfig = field(default_factory=PerfRecordConfig)
    iostat: "IostatConfig" = field(default_factory=lambda: IostatConfig())
    vmstat: "VmstatConfig" = field(default_factory=lambda: VmstatConfig())
    npu_smi: NpuSmiConfig = field(default_factory=NpuSmiConfig)


@dataclass(slots=True)
class IostatConfig:
    enabled: bool = False
    interval_sec: int = 1


@dataclass(slots=True)
class VmstatConfig:
    enabled: bool = True
    interval_sec: int = 1


@dataclass(slots=True)
class ArtifactsConfig:
    summary_only: bool = False


@dataclass(slots=True)
class RuntimeConfig:
    kind: Literal["docker", "host_direct"] = "docker"
    image: str = "openclaw:bench-local"
    container_name_base: str = "openclaw-bench"
    instance_num: int = 1
    openclaw_num_per_instance: int = 1
    reuse_container_name: str = ""
    host: str = "127.0.0.1"
    host_port: int = 19189
    container_port: int = 18789
    network_mode: Literal["bridge", "host"] = "bridge"
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
    docker_run_args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    openclaw_config: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ClientConfig:
    role: str = "operator"
    message: str = "/context list"
    task_file: str = ""
    task_id: str = ""
    task_name: str = ""
    task_category: str = ""
    task_description: str = ""
    resolved_prompt: str = ""
    session_prefix: str = "bench"
    session_mode: Literal["per_worker", "per_request", "shared"] = "per_worker"
    history_limit: int = 20
    wait_timeout_ms: int = 15000
    send_timeout_ms: int = 15000

    def effective_message(self) -> str:
        return self.resolved_prompt or self.message


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
    artifacts: ArtifactsConfig = field(default_factory=ArtifactsConfig)
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
    _merge_dataclass(raw.get("artifacts"), scenario.artifacts)
    collector_raw = raw.get("collectors", {})
    _merge_dataclass(collector_raw.get("docker_stats"), scenario.collectors.docker_stats)
    _merge_dataclass(collector_raw.get("pidstat"), scenario.collectors.pidstat)
    _merge_dataclass(collector_raw.get("strace"), scenario.collectors.strace)
    _merge_dataclass(collector_raw.get("node_trace"), scenario.collectors.node_trace)
    _merge_dataclass(collector_raw.get("perf_stat"), scenario.collectors.perf_stat)
    _merge_dataclass(collector_raw.get("perf_record"), scenario.collectors.perf_record)
    _merge_dataclass(collector_raw.get("iostat"), scenario.collectors.iostat)
    _merge_dataclass(collector_raw.get("vmstat"), scenario.collectors.vmstat)
    _merge_dataclass(collector_raw.get("npu_smi"), scenario.collectors.npu_smi)
    if scenario.client.session_mode not in SESSION_MODES:
        raise ValueError(
            f"invalid session_mode={scenario.client.session_mode!r}; expected one of {SESSION_MODES}",
        )
    if scenario.runtime.kind not in {"docker", "host_direct"}:
        raise ValueError(
            f"invalid runtime.kind={scenario.runtime.kind!r}; expected 'docker' or 'host_direct'",
        )
    if scenario.runtime.instance_num <= 0:
        raise ValueError("runtime.instance_num must be >= 1")
    if scenario.runtime.openclaw_num_per_instance <= 0:
        raise ValueError("runtime.openclaw_num_per_instance must be >= 1")
    if scenario.runtime.reuse_container_name.strip() and scenario.runtime.kind != "docker":
        raise ValueError("runtime.reuse_container_name is only supported for docker runtimes")
    if scenario.runtime.network_mode not in {"bridge", "host"}:
        raise ValueError(
            "invalid runtime.network_mode="
            f"{scenario.runtime.network_mode!r}; expected 'bridge' or 'host'",
        )
    if scenario.runtime.instance_num > 1 and scenario.runtime.kind != "docker":
        raise ValueError("runtime.instance_num > 1 is only supported for docker runtimes")
    if scenario.runtime.openclaw_num_per_instance > 1 and scenario.runtime.kind != "docker":
        raise ValueError("runtime.openclaw_num_per_instance > 1 is only supported for docker runtimes")
    if scenario.runtime.instance_num > 1 and scenario.runtime.reuse_container_name.strip():
        raise ValueError("runtime.instance_num > 1 does not support reusing a single existing container")
    if scenario.runtime.openclaw_num_per_instance > 1 and scenario.runtime.reuse_container_name.strip():
        raise ValueError(
            "runtime.openclaw_num_per_instance > 1 does not support reusing a single existing container",
        )
    if scenario.runtime.instance_num > 1 and (
        scenario.runtime.ws_url.strip() or scenario.runtime.healthcheck_url.strip()
    ):
        raise ValueError(
            "runtime.instance_num > 1 does not support explicit runtime.ws_url or runtime.healthcheck_url; "
            "the harness assigns per-instance ports automatically",
        )
    if scenario.runtime.openclaw_num_per_instance > 1 and (
        scenario.runtime.ws_url.strip() or scenario.runtime.healthcheck_url.strip()
    ):
        raise ValueError(
            "runtime.openclaw_num_per_instance > 1 does not support explicit runtime.ws_url or "
            "runtime.healthcheck_url; the harness assigns per-gateway ports automatically",
        )
    if scenario.runtime.instance_num > 1 and scenario.runtime.host_port <= 0:
        raise ValueError("runtime.instance_num > 1 requires runtime.host_port to be a positive base port")
    if scenario.runtime.openclaw_num_per_instance > 1 and scenario.runtime.host_port <= 0:
        raise ValueError(
            "runtime.openclaw_num_per_instance > 1 requires runtime.host_port to be a positive base port",
        )
    if scenario.runtime.openclaw_num_per_instance > 1 and scenario.runtime.container_port <= 0:
        raise ValueError(
            "runtime.openclaw_num_per_instance > 1 requires runtime.container_port to be a positive base port",
        )
    if scenario.runtime.reuse_container_name.strip() and scenario.runtime.container_port <= 0:
        raise ValueError(
            "docker reuse requires runtime.container_port to be the OpenClaw port inside the existing container",
        )
    if not isinstance(scenario.runtime.docker_run_args, list) or any(
        not isinstance(arg, str) for arg in scenario.runtime.docker_run_args
    ):
        raise ValueError("runtime.docker_run_args must be a JSON array of strings")
    scenario.scenario_path = str(path.resolve())
    if scenario.client.task_file.strip():
        task_path = resolve_task_path(scenario.client.task_file, scenario_path=path.resolve())
        task = load_task(task_path)
        scenario.client.task_file = str(task_path)
        scenario.client.task_id = task.id
        scenario.client.task_name = task.name
        scenario.client.task_category = task.category
        scenario.client.task_description = task.description
        scenario.client.resolved_prompt = task.prompt
    else:
        scenario.client.resolved_prompt = scenario.client.message.strip()
    if not scenario.client.effective_message().strip():
        raise ValueError("scenario must define client.message or client.task_file")
    return scenario
