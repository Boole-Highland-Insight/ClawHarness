from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from .device_identity import DeviceIdentity
from .parsers import derive_healthcheck_url
from .scenario import RuntimeConfig
from .utils import command_exists, compact_cmd, run_command


@dataclass(slots=True)
class RuntimeInfo:
    kind: str
    url: str
    token: str
    started_by_harness: bool
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
        output_dir: Path,
        container_name: str,
        device_identity: DeviceIdentity | None = None,
    ) -> None:
        self.config = config
        self.output_dir = output_dir
        self.container_name = container_name
        self.device_identity = device_identity
        self.runtime_dir = output_dir / "runtime"
        self.config_dir = self.runtime_dir / "config"
        self.workspace_dir = self.runtime_dir / "workspace"
        self.image_build_log = self.runtime_dir / "docker-build.log"
        self.container_log = self.runtime_dir / "docker-logs.txt"
        repo_root = Path(config.repo_root) if config.repo_root else Path(__file__).resolve().parents[4]
        self.repo_root = repo_root.resolve()
        self.dockerfile = (self.repo_root / config.dockerfile).resolve()
        self.container_id: str | None = None

    def start(self) -> RuntimeInfo:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._seed_runtime_config()
        self._seed_device_pairing()
        self._ensure_image()
        run_command(["docker", "rm", "-f", self.container_name], check=False)
        docker_args = [
            "docker",
            "run",
            "-d",
            "--init",
            "--name",
            self.container_name,
            "-p",
            f"{self.config.host}:{self.config.host_port}:{self.config.container_port}",
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
        if self.config.skip_channels:
            docker_args.extend(["-e", "OPENCLAW_SKIP_CHANNELS=1"])
        docker_args.extend(
            [
                self.config.image,
                "node",
                "dist/index.js",
                "gateway",
                "--allow-unconfigured",
                "--bind",
                self.config.gateway_bind,
                "--port",
                str(self.config.container_port),
            ],
        )
        started = run_command(docker_args, cwd=self.repo_root)
        self.container_id = started.stdout.strip()
        self._wait_for_health()
        self._write_logs()
        return RuntimeInfo(
            kind="docker",
            url=f"ws://{self.config.host}:{self.config.host_port}",
            token=self.config.gateway_token,
            started_by_harness=True,
            container_name=self.container_name,
            container_id=self.container_id,
            host_pid=self._inspect_pid(),
            repo_root=str(self.repo_root),
            runtime_dir=str(self.runtime_dir),
        )

    def stop(self) -> None:
        self._write_logs()
        if self.config.keep_container:
            return
        run_command(["docker", "rm", "-f", self.container_name], check=False)

    def dump_state(self) -> dict[str, Any]:
        return {
            "container_name": self.container_name,
            "container_id": self.container_id,
            "runtime_dir": str(self.runtime_dir),
            "repo_root": str(self.repo_root),
            "dockerfile": str(self.dockerfile),
            "image_build_log": str(self.image_build_log),
            "container_log": str(self.container_log),
        }

    def _ensure_image(self) -> None:
        inspect = run_command(["docker", "image", "inspect", self.config.image], check=False)
        should_build = self.config.force_rebuild or (
            self.config.build_image_if_missing and inspect.returncode != 0
        )
        if not should_build:
            return
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

    def _wait_for_health(self) -> None:
        url = f"http://{self.config.host}:{self.config.host_port}/healthz"
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
        config_path = self.config_dir / "openclaw.json"
        payload = {
            "gateway": {
                "mode": "local",
                "controlUi": {
                    "enabled": False,
                },
            },
        }
        config_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")

    def _seed_device_pairing(self) -> None:
        if self.device_identity is None:
            return
        devices_dir = self.config_dir / "devices"
        devices_dir.mkdir(parents=True, exist_ok=True)
        now_ms = int(time.time() * 1000)
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
                "scopes": ["operator.admin"],
                "approvedScopes": ["operator.admin"],
                "createdAtMs": now_ms,
                "approvedAtMs": now_ms,
            },
        }
        (devices_dir / "paired.json").write_text(
            f"{json.dumps(paired_payload, indent=2)}\n",
            encoding="utf-8",
        )
        (devices_dir / "pending.json").write_text("{}\n", encoding="utf-8")


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
    output_dir: Path,
    container_name: str,
    device_identity: DeviceIdentity | None = None,
) -> BaseRuntimeManager:
    if config.kind == "docker":
        return DockerRuntimeManager(
            config=config,
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
