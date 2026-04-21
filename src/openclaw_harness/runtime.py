from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from .device_identity import DeviceIdentity
from .parsers import derive_healthcheck_url
from .scenario import NodeTraceConfig, RuntimeConfig
from .utils import command_exists, compact_cmd, run_command


def _deep_merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        existing = base.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _deep_merge_dict(existing, value)
            continue
        base[key] = value
    return base


@dataclass(slots=True)
class RuntimeInfo:
    kind: str
    url: str
    token: str
    started_by_harness: bool
    urls: list[str] = field(default_factory=list)
    container_name: str | None = None
    container_id: str | None = None
    host_pid: int | None = None
    host_pid_source: str | None = None
    repo_root: str | None = None
    runtime_dir: str | None = None


class BaseRuntimeManager:
    def start(self) -> RuntimeInfo:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def dump_state(self) -> dict[str, Any]:
        raise NotImplementedError


class DockerRuntimeManager:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        node_trace: NodeTraceConfig | None,
        output_dir: Path,
        container_name: str,
        device_identity: DeviceIdentity | None = None,
    ) -> None:
        self.config = config
        self.node_trace = node_trace or NodeTraceConfig()
        self.output_dir = output_dir
        self.reuse_container_name = self.config.reuse_container_name.strip()
        self.reusing_existing_container = bool(self.reuse_container_name)
        self.container_name = self.reuse_container_name or container_name
        self.device_identity = device_identity
        self.runtime_dir = output_dir / "runtime"
        self.config_dir = self.runtime_dir / "config"
        self.workspace_dir = self.runtime_dir / "workspace"
        self.image_build_log = self.runtime_dir / "docker-build.log"
        self.container_log = self.runtime_dir / "docker-logs.txt"
        repo_root = Path(config.repo_root) if config.repo_root else Path(__file__).resolve().parents[2]
        self.repo_root = repo_root.resolve()
        self.dockerfile = (self.repo_root / config.dockerfile).resolve()
        self.container_id: str | None = None
        self.resolved_url = ""
        self.resolved_urls: list[str] = []
        self.resolved_healthcheck_url = ""
        self.resolved_healthcheck_urls: list[str] = []

    @property
    def openclaw_count(self) -> int:
        return max(1, int(self.config.openclaw_num_per_instance))

    def start(self) -> RuntimeInfo:
        if self.reusing_existing_container:
            return self._start_existing_container()
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._seed_runtime_config()
        self._seed_device_pairing()
        self._prepare_bind_mount_permissions()
        self._ensure_image()
        run_command(["docker", "rm", "-f", self.container_name], check=False)
        docker_args = [
            "docker",
            "run",
            "-d",
            "--init",
            "--name",
            self.container_name,
            "-e",
            "HOME=/home/node",
            "-e",
            "TERM=xterm-256color",
            "-e",
            f"OPENCLAW_GATEWAY_TOKEN={self.config.gateway_token}",
            "-e",
            "TZ=UTC",
            "-v",
            f"{self.config_dir}:/home/node/.openclaw",
            "-v",
            f"{self.workspace_dir}:/home/node/.openclaw/workspace",
        ]
        if self.config.network_mode == "host":
            docker_args.extend(["--network", "host"])
        else:
            for host_port, container_port in zip(self._gateway_host_ports(), self._gateway_container_ports()):
                docker_args.extend(["-p", f"{self.config.host}:{host_port}:{container_port}"])
        if self.openclaw_count > 1 and "OPENCLAW_SKIP_BROWSER_CONTROL_SERVER" not in self.config.env:
            docker_args.extend(["-e", "OPENCLAW_SKIP_BROWSER_CONTROL_SERVER=1"])
        for key, value in self.config.env.items():
            docker_args.extend(["-e", f"{key}={value}"])
        if self.node_trace.enabled:
            categories = ",".join(self.node_trace.categories)
            trace_pattern = "/home/node/.openclaw/workspace/node-trace-${pid}.json"
            docker_args.extend(
                [
                    "-e",
                    (
                        "NODE_OPTIONS="
                        f"--trace-event-categories={categories} "
                        f"--trace-event-file-pattern={trace_pattern}"
                    ),
                ],
            )
        if self.config.skip_channels:
            docker_args.extend(["-e", "OPENCLAW_SKIP_CHANNELS=1"])
        if self.config.docker_run_args:
            docker_args.extend(self.config.docker_run_args)
        gateway_port = (
            self.config.host_port
            if self.config.network_mode == "host"
            else self.config.container_port
        )
        docker_args.append(self.config.image)
        if self.openclaw_count == 1:
            docker_args.extend(
                [
                    "node",
                    "dist/index.js",
                    "gateway",
                    "--allow-unconfigured",
                    "--bind",
                    self.config.gateway_bind,
                    "--port",
                    str(gateway_port),
                ],
            )
        else:
            docker_args.extend(["bash", "-lc", self._build_multi_openclaw_command()])
        started = run_command(docker_args, cwd=self.repo_root)
        self.container_id = started.stdout.strip()
        self.resolved_urls = [f"ws://{self.config.host}:{port}" for port in self._gateway_host_ports()]
        self.resolved_url = self.resolved_urls[0]
        self.resolved_healthcheck_urls = [f"http://{self.config.host}:{port}/healthz" for port in self._gateway_host_ports()]
        self.resolved_healthcheck_url = self.resolved_healthcheck_urls[0]
        for healthcheck_url in self.resolved_healthcheck_urls:
            self._wait_for_health(healthcheck_url)
        self._write_logs()
        host_pid, host_pid_source = self._inspect_host_pid()
        return RuntimeInfo(
            kind="docker",
            url=self.resolved_url,
            token=self.config.gateway_token,
            started_by_harness=True,
            urls=list(self.resolved_urls),
            container_name=self.container_name,
            container_id=self.container_id,
            host_pid=host_pid,
            host_pid_source=host_pid_source,
            repo_root=str(self.repo_root),
            runtime_dir=str(self.runtime_dir),
        )

    def stop(self) -> None:
        self._write_logs()
        if self.config.keep_container or self.reusing_existing_container:
            return
        run_command(["docker", "rm", "-f", self.container_name], check=False)

    def dump_state(self) -> dict[str, Any]:
        return {
            "container_name": self.container_name,
            "container_id": self.container_id,
            "reuse_container_name": self.reuse_container_name or None,
            "reusing_existing_container": self.reusing_existing_container,
            "resolved_url": self.resolved_url or None,
            "resolved_urls": list(self.resolved_urls),
            "resolved_healthcheck_url": self.resolved_healthcheck_url or None,
            "resolved_healthcheck_urls": list(self.resolved_healthcheck_urls),
            "openclaw_num_per_instance": self.openclaw_count,
            "runtime_dir": str(self.runtime_dir),
            "repo_root": str(self.repo_root),
            "dockerfile": str(self.dockerfile),
            "image_build_log": str(self.image_build_log),
            "container_log": str(self.container_log),
        }

    def _start_existing_container(self) -> RuntimeInfo:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        container = self._inspect_container()
        self.container_id = str(container.get("Id") or "").strip() or None
        self.resolved_url = self.config.ws_url.strip() or self._derive_existing_container_ws_url(container)
        self.resolved_urls = [self.resolved_url]
        self.resolved_healthcheck_url = (
            self.config.healthcheck_url.strip() or derive_healthcheck_url(self.resolved_url)
        )
        self.resolved_healthcheck_urls = [self.resolved_healthcheck_url] if self.resolved_healthcheck_url else []
        if self.resolved_healthcheck_url:
            self._wait_for_health(self.resolved_healthcheck_url)
        self._write_logs()
        host_pid, host_pid_source = self._inspect_host_pid()
        return RuntimeInfo(
            kind="docker",
            url=self.resolved_url,
            token=self.config.gateway_token,
            started_by_harness=False,
            urls=list(self.resolved_urls),
            container_name=self.container_name,
            container_id=self.container_id,
            host_pid=host_pid,
            host_pid_source=host_pid_source,
            repo_root=str(self.repo_root),
            runtime_dir=str(self.runtime_dir),
        )

    def _ensure_image(self) -> None:
        inspect = run_command(["docker", "image", "inspect", self.config.image], check=False)
        should_build = self.config.force_rebuild or (
            self.config.build_image_if_missing and inspect.returncode != 0
        )
        if not should_build:
            return
        if not self.dockerfile.is_file():
            raise RuntimeError(
                "docker build failed\n"
                f"Dockerfile not found: {self.dockerfile}\n"
                f"repo_root: {self.repo_root}\n"
                "Set runtime.repo_root and runtime.dockerfile in the scenario if the gateway repo lives elsewhere."
            )
        self.image_build_log.parent.mkdir(parents=True, exist_ok=True)
        build = run_command(
            [
                "docker",
                "build",
                "-t",
                self.config.image,
                "-f",
                str(self.dockerfile),
                str(self.repo_root),
            ],
            cwd=self.repo_root,
            check=False,
            capture_output=True,
        )
        self.image_build_log.write_text(build.stdout + build.stderr, encoding="utf-8")
        if build.returncode != 0:
            raise RuntimeError(
                "docker build failed\n"
                f"command: {compact_cmd(['docker', 'build', '-t', self.config.image, '-f', str(self.dockerfile), str(self.repo_root)])}\n"
                f"log: {self.image_build_log}"
            )

    def _inspect_pid(self) -> int | None:
        result = run_command(
            ["docker", "inspect", "--format", "{{.State.Pid}}", self.container_name],
            check=False,
        )
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        if not raw.isdigit():
            return None
        return int(raw)

    def _inspect_container(self) -> dict[str, Any]:
        result = run_command(["docker", "inspect", self.container_name], check=False)
        if result.returncode != 0:
            raise RuntimeError(f"failed to inspect docker container: {self.container_name}")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"docker inspect returned invalid JSON for {self.container_name}") from exc
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
            raise RuntimeError(f"docker inspect returned no container payload for {self.container_name}")
        return payload[0]

    def _derive_existing_container_ws_url(self, container: dict[str, Any]) -> str:
        port = int(self.config.container_port)
        network_mode = str(container.get("HostConfig", {}).get("NetworkMode") or "").strip().lower()
        if network_mode == "host":
            host = self.config.host.strip() or "127.0.0.1"
            return f"ws://{host}:{port}"
        networks = container.get("NetworkSettings", {}).get("Networks", {})
        if isinstance(networks, dict):
            for network in networks.values():
                if not isinstance(network, dict):
                    continue
                ip_address = str(network.get("IPAddress") or "").strip()
                if ip_address:
                    return f"ws://{ip_address}:{port}"
        raise RuntimeError(
            "could not resolve an IP for the existing docker container; "
            "set runtime.ws_url explicitly or run the container with a reachable network",
        )

    def _inspect_host_pid(self) -> tuple[int | None, str | None]:
        if self.openclaw_count > 1:
            return None, "unsupported:multiple_openclaw_processes"
        init_pid = self._inspect_pid()
        if init_pid is None:
            return None, None

        top_result = run_command(
            ["docker", "top", self.container_name, "-eo", "pid,ppid,comm,args"],
            check=False,
        )
        if top_result.returncode == 0:
            rows = self._parse_docker_top_rows(top_result.stdout)
            preferred = self._pick_preferred_container_pid(rows=rows, init_pid=init_pid)
            if preferred is not None:
                return preferred, "auto:docker_top"

        ps_result = run_command(
            ["ps", "-eo", "pid=,ppid=,comm=,args="],
            check=False,
        )
        if ps_result.returncode == 0:
            rows = self._parse_host_ps_rows(ps_result.stdout)
            preferred = self._pick_preferred_host_descendant_pid(rows=rows, init_pid=init_pid)
            if preferred is not None:
                return preferred, "auto:host_ps"
        return init_pid, "auto:docker_inspect"

    def _parse_docker_top_rows(self, raw: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        lines = [line.rstrip() for line in raw.splitlines() if line.strip()]
        if len(lines) <= 1:
            return rows
        for line in lines[1:]:
            parts = line.split(None, 3)
            if len(parts) < 3:
                continue
            pid_raw, ppid_raw, comm = parts[:3]
            args = parts[3] if len(parts) > 3 else ""
            if not pid_raw.isdigit():
                continue
            rows.append(
                {
                    "pid": int(pid_raw),
                    "ppid": int(ppid_raw) if ppid_raw.isdigit() else None,
                    "comm": comm,
                    "args": args,
                }
            )
        return rows

    def _pick_preferred_container_pid(self, *, rows: list[dict[str, Any]], init_pid: int) -> int | None:
        if not rows:
            return None

        def is_descendant(pid: int) -> bool:
            by_pid = {int(row["pid"]): row for row in rows if isinstance(row.get("pid"), int)}
            current = by_pid.get(pid)
            seen: set[int] = set()
            while current is not None:
                current_pid = int(current["pid"])
                if current_pid in seen:
                    return False
                seen.add(current_pid)
                parent_pid = current.get("ppid")
                if parent_pid == init_pid:
                    return True
                current = by_pid.get(int(parent_pid)) if isinstance(parent_pid, int) else None
            return False

        preferred_patterns = (
            ("node", " dist/index.js gateway"),
            ("node", " gateway"),
        )
        for comm, needle in preferred_patterns:
            for row in rows:
                args = str(row.get("args", ""))
                if row.get("comm") == comm and needle.strip() in args and is_descendant(int(row["pid"])):
                    return int(row["pid"])

        for row in rows:
            if row.get("comm") == "node" and is_descendant(int(row["pid"])):
                return int(row["pid"])

        return None

    def _parse_host_ps_rows(self, raw: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(None, 3)
            if len(parts) < 3:
                continue
            pid_raw, ppid_raw, comm = parts[:3]
            args = parts[3] if len(parts) > 3 else ""
            if not pid_raw.isdigit():
                continue
            rows.append(
                {
                    "pid": int(pid_raw),
                    "ppid": int(ppid_raw) if ppid_raw.isdigit() else None,
                    "comm": comm,
                    "args": args,
                }
            )
        return rows

    def _pick_preferred_host_descendant_pid(self, *, rows: list[dict[str, Any]], init_pid: int) -> int | None:
        if not rows:
            return None

        by_pid = {int(row["pid"]): row for row in rows if isinstance(row.get("pid"), int)}

        def is_descendant(pid: int) -> bool:
            current = by_pid.get(pid)
            seen: set[int] = set()
            while current is not None:
                current_pid = int(current["pid"])
                if current_pid in seen:
                    return False
                seen.add(current_pid)
                parent_pid = current.get("ppid")
                if parent_pid == init_pid:
                    return True
                current = by_pid.get(int(parent_pid)) if isinstance(parent_pid, int) else None
            return False

        def score(row: dict[str, Any]) -> tuple[int, int]:
            args = str(row.get("args", ""))
            comm = str(row.get("comm", ""))
            if "dist/index.js gateway" in args:
                return (0, int(row["pid"]))
            if " gateway" in args and ("node" in comm or "node" in args):
                return (1, int(row["pid"]))
            if comm == "node":
                return (2, int(row["pid"]))
            return (3, int(row["pid"]))

        descendants = [
            row
            for row in rows
            if int(row["pid"]) != init_pid and is_descendant(int(row["pid"]))
        ]
        if not descendants:
            return None
        return min(descendants, key=score)["pid"]

    def _wait_for_health(self, url: str) -> None:
        deadline = time.time() + self.config.startup_timeout_sec
        while time.time() < deadline:
            if not self._is_container_running():
                self._write_logs()
                raise RuntimeError(f"gateway container exited early; see {self.container_log}")
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
            except (URLError, OSError):
                time.sleep(1)
                continue
            time.sleep(1)
        self._write_logs()
        raise RuntimeError(f"gateway health check did not succeed before timeout; see {self.container_log}")

    def _write_logs(self) -> None:
        result = run_command(["docker", "logs", self.container_name], check=False)
        payload = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
        self.container_log.parent.mkdir(parents=True, exist_ok=True)
        self.container_log.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")

    def _is_container_running(self) -> bool:
        result = run_command(
            ["docker", "inspect", "--format", "{{.State.Running}}", self.container_name],
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip().lower() == "true"

    def _seed_runtime_config(self) -> None:
        for openclaw_index in range(self.openclaw_count):
            config_path = self._host_state_dir(openclaw_index) / "openclaw.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "gateway": {
                    "mode": "local",
                    "controlUi": {
                        "enabled": False,
                    },
                },
            }
            if self.config.openclaw_config:
                payload = _deep_merge_dict(payload, self.config.openclaw_config)
            agents = payload.setdefault("agents", {})
            if not isinstance(agents, dict):
                agents = {}
                payload["agents"] = agents
            defaults = agents.setdefault("defaults", {})
            if not isinstance(defaults, dict):
                defaults = {}
                agents["defaults"] = defaults
            if not str(defaults.get("workspace", "")).strip():
                defaults["workspace"] = self._container_workspace_dir(openclaw_index)
            config_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")

    def _seed_device_pairing(self) -> None:
        if self.device_identity is None:
            return
        now_ms = int(time.time() * 1000)
        operator_scopes = ["operator.admin"]
        paired_payload = {
            self.device_identity.device_id: {
                "deviceId": self.device_identity.device_id,
                "publicKey": self.device_identity.public_key_raw,
                "displayName": "openclaw benchmark harness",
                "platform": "linux",
                "clientId": "gateway-client",
                "clientMode": "backend",
                "role": "operator",
                "roles": ["operator"],
                "scopes": operator_scopes,
                "approvedScopes": operator_scopes,
                "tokens": {
                    "operator": {
                        "token": secrets.token_urlsafe(32),
                        "role": "operator",
                        "scopes": operator_scopes,
                        "createdAtMs": now_ms,
                    },
                },
                "createdAtMs": now_ms,
                "approvedAtMs": now_ms,
            },
        }
        for openclaw_index in range(self.openclaw_count):
            devices_dir = self._host_state_dir(openclaw_index) / "devices"
            devices_dir.mkdir(parents=True, exist_ok=True)
            (devices_dir / "paired.json").write_text(
                f"{json.dumps(paired_payload, indent=2)}\n",
                encoding="utf-8",
            )
            (devices_dir / "pending.json").write_text("{}\n", encoding="utf-8")

    def _gateway_host_ports(self) -> list[int]:
        return [self.config.host_port + openclaw_index for openclaw_index in range(self.openclaw_count)]

    def _gateway_container_ports(self) -> list[int]:
        return [self.config.container_port + openclaw_index for openclaw_index in range(self.openclaw_count)]

    def _state_dir_name(self, openclaw_index: int) -> str:
        return f"openclaw-{openclaw_index:02d}"

    def _host_state_dir(self, openclaw_index: int) -> Path:
        if self.openclaw_count == 1:
            return self.config_dir
        return self.config_dir / self._state_dir_name(openclaw_index)

    def _container_state_dir(self, openclaw_index: int) -> str:
        if self.openclaw_count == 1:
            return "/home/node/.openclaw"
        return f"/home/node/.openclaw/{self._state_dir_name(openclaw_index)}"

    def _host_workspace_dir(self, openclaw_index: int) -> Path:
        if self.openclaw_count == 1:
            return self.workspace_dir
        return self.workspace_dir / self._state_dir_name(openclaw_index)

    def _container_workspace_dir(self, openclaw_index: int) -> str:
        if self.openclaw_count == 1:
            return "/home/node/.openclaw/workspace"
        return f"/home/node/.openclaw/workspace/{self._state_dir_name(openclaw_index)}"

    def _build_multi_openclaw_command(self) -> str:
        bind = shlex.quote(self.config.gateway_bind)
        lines = [
            "set -eu",
            'pids=""',
            'cleanup() {',
            '  for pid in $pids; do',
            '    kill "$pid" 2>/dev/null || true',
            '  done',
            '}',
            'trap cleanup INT TERM EXIT',
        ]
        port_values = (
            self._gateway_host_ports()
            if self.config.network_mode == "host"
            else self._gateway_container_ports()
        )
        for openclaw_index, port in enumerate(port_values):
            state_dir = shlex.quote(self._container_state_dir(openclaw_index))
            workspace_dir = shlex.quote(self._container_workspace_dir(openclaw_index))
            lines.append(f"mkdir -p {state_dir} {workspace_dir}")
            lines.append(
                f"OPENCLAW_STATE_DIR={state_dir} node dist/index.js gateway --allow-unconfigured --bind {bind} --port {port} &",
            )
            lines.append('pids="$pids $!"')
        lines.extend(
            [
                "wait -n $pids",
                "status=$?",
                "cleanup",
                "wait || true",
                "exit $status",
            ],
        )
        return "\n".join(lines)

    def _prepare_bind_mount_permissions(self) -> None:
        # The gateway image runs as the non-root "node" user, so bind-mounted
        # config/workspace paths created by the host must be writable.
        for root, dirs, files in os.walk(self.runtime_dir):
            Path(root).chmod(0o777)
            for name in dirs:
                (Path(root) / name).chmod(0o777)
            for name in files:
                (Path(root) / name).chmod(0o666)


class HostDirectRuntimeManager(BaseRuntimeManager):
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        output_dir: Path,
    ) -> None:
        self.config = config
        self.output_dir = output_dir
        self.runtime_dir = output_dir / "runtime"
        self.resolved_url = ""
        self.resolved_healthcheck_url = ""
        self.resolved_host_pid: int | None = None
        self.host_pid_source: str | None = None

    def start(self) -> RuntimeInfo:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_url = self.config.ws_url.strip() or f"ws://{self.config.host}:{self.config.host_port}"
        self.resolved_healthcheck_url = (
            self.config.healthcheck_url.strip() or derive_healthcheck_url(self.resolved_url)
        )
        if self.resolved_healthcheck_url:
            self._wait_for_health(self.resolved_healthcheck_url)
        self.resolved_host_pid, self.host_pid_source = self._resolve_host_pid(self.resolved_url)
        return RuntimeInfo(
            kind="host_direct",
            url=self.resolved_url,
            token=self.config.gateway_token,
            started_by_harness=False,
            urls=[self.resolved_url],
            host_pid=self.resolved_host_pid,
            host_pid_source=self.host_pid_source,
            runtime_dir=str(self.runtime_dir),
        )

    def stop(self) -> None:
        return None

    def dump_state(self) -> dict[str, Any]:
        return {
            "runtime_dir": str(self.runtime_dir),
            "ws_url": self.resolved_url or self.config.ws_url.strip() or f"ws://{self.config.host}:{self.config.host_port}",
            "healthcheck_url": self.resolved_healthcheck_url
            or self.config.healthcheck_url.strip()
            or derive_healthcheck_url(self.config.ws_url.strip() or f"ws://{self.config.host}:{self.config.host_port}"),
            "host_pid": self.resolved_host_pid,
            "host_pid_source": self.host_pid_source,
            "started_by_harness": False,
        }

    def _wait_for_health(self, url: str) -> None:
        deadline = time.time() + self.config.startup_timeout_sec
        while time.time() < deadline:
            try:
                with urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return
            except (URLError, OSError):
                time.sleep(1)
                continue
            time.sleep(1)
        raise RuntimeError(f"gateway health check did not succeed before timeout: {url}")

    def _resolve_host_pid(self, url: str) -> tuple[int | None, str | None]:
        configured = self.config.host_pid
        if isinstance(configured, int) and configured > 0:
            return configured, "configured"
        port = self._resolve_port(url)
        if port is None:
            return None, None
        resolvers: list[tuple[str, Any]] = []
        if command_exists("ss"):
            resolvers.append(("auto:ss", self._pid_from_ss))
        if command_exists("lsof"):
            resolvers.append(("auto:lsof", self._pid_from_lsof))
        if command_exists("fuser"):
            resolvers.append(("auto:fuser", self._pid_from_fuser))
        for source, resolver in resolvers:
            pid = resolver(port)
            if pid is not None:
                return pid, source
        return None, None

    def _resolve_port(self, url: str) -> int | None:
        try:
            parsed = urlsplit(url)
        except ValueError:
            parsed = None
        if parsed is not None and parsed.port is not None:
            return int(parsed.port)
        if self.config.host_port > 0:
            return int(self.config.host_port)
        return None

    def _pid_from_ss(self, port: int) -> int | None:
        result = run_command(
            ["ss", "-ltnpH", f"sport = :{port}"],
            check=False,
        )
        match = re.search(r"\bpid=(\d+)\b", result.stdout)
        if not match:
            return None
        return int(match.group(1))

    def _pid_from_lsof(self, port: int) -> int | None:
        result = run_command(
            ["lsof", "-tiTCP:" + str(port), "-sTCP:LISTEN"],
            check=False,
        )
        for line in result.stdout.splitlines():
            candidate = line.strip()
            if candidate.isdigit():
                return int(candidate)
        return None

    def _pid_from_fuser(self, port: int) -> int | None:
        result = run_command(
            ["fuser", "-n", "tcp", str(port)],
            check=False,
        )
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        match = re.search(r":\s*([0-9 ]+)$", combined)
        if not match:
            return None
        for candidate in match.group(1).split():
            if candidate.isdigit():
                return int(candidate)
        return None


def create_runtime_manager(
    *,
    config: RuntimeConfig,
    node_trace: NodeTraceConfig | None,
    output_dir: Path,
    container_name: str,
    device_identity: DeviceIdentity | None = None,
) -> BaseRuntimeManager:
    if config.kind == "docker":
        return DockerRuntimeManager(
            config=config,
            node_trace=node_trace,
            output_dir=output_dir,
            container_name=container_name,
            device_identity=device_identity,
        )
    if config.kind == "host_direct":
        return HostDirectRuntimeManager(
            config=config,
            output_dir=output_dir,
        )
    raise ValueError(f"unsupported runtime kind: {config.kind}")
