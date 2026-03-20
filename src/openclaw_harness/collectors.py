from __future__ import annotations

import csv
import json
import signal
import subprocess
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .scenario import CollectorsConfig
from .utils import command_exists, iso_now, run_command


PERF_STAT_EVENTS = [
    "context-switches",
    "cpu-migrations",
    "page-faults",
    "cache-references",
    "cache-misses",
]


@dataclass(slots=True)
class CollectorStatus:
    name: str
    enabled: bool
    status: str = "pending"
    detail: str | None = None
    files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseCollector:
    def __init__(self, name: str, enabled: bool) -> None:
        self.status = CollectorStatus(name=name, enabled=enabled)

    def start(self) -> None:
        self.status.status = "started"

    def stop(self) -> None:
        if self.status.status == "started":
            self.status.status = "completed"


class DockerStatsCollector(BaseCollector):
    def __init__(
        self,
        *,
        container_name: str | None,
        interval_ms: int,
        output_dir: Path,
        enabled: bool,
    ) -> None:
        super().__init__("docker_stats", enabled)
        self.container_name = container_name
        self.interval_seconds = max(interval_ms, 200) / 1000.0
        self.output_path = output_dir / "docker_stats.csv"
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.status.enabled:
            self.status.status = "skipped"
            self.status.detail = "disabled in scenario"
            return
        if not self.container_name:
            self.status.status = "skipped"
            self.status.detail = "container name is unavailable"
            return
        if not command_exists("docker"):
            self.status.status = "skipped"
            self.status.detail = "docker CLI is not available"
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.status.files.append(str(self.output_path))
        self.status.status = "started"
        self._thread.start()

    def stop(self) -> None:
        if self.status.status != "started":
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        self.status.status = "completed"

    def _run(self) -> None:
        with self.output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "timestamp",
                    "container",
                    "cpu_percent",
                    "mem_percent",
                    "mem_usage_limit",
                    "net_io",
                    "block_io",
                    "pids",
                    "raw_json",
                ],
            )
            writer.writeheader()
            while not self._stop_event.is_set():
                sample = run_command(
                    [
                        "docker",
                        "stats",
                        "--no-stream",
                        "--format",
                        "{{ json . }}",
                        self.container_name,
                    ],
                    check=False,
                )
                raw = sample.stdout.strip()
                if raw:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = {"raw": raw}
                    writer.writerow(
                        {
                            "timestamp": iso_now(),
                            "container": payload.get("Name", self.container_name),
                            "cpu_percent": payload.get("CPUPerc", ""),
                            "mem_percent": payload.get("MemPerc", ""),
                            "mem_usage_limit": payload.get("MemUsage", ""),
                            "net_io": payload.get("NetIO", ""),
                            "block_io": payload.get("BlockIO", ""),
                            "pids": payload.get("PIDs", ""),
                            "raw_json": json.dumps(payload, sort_keys=True),
                        },
                    )
                    handle.flush()
                self._stop_event.wait(self.interval_seconds)


class BackgroundCommandCollector(BaseCollector):
    def __init__(
        self,
        *,
        name: str,
        enabled: bool,
        command: list[str],
        output_path: Path,
        output_files: list[Path] | None = None,
        disabled_detail: str | None = None,
    ) -> None:
        super().__init__(name, enabled)
        self.command = command
        self.output_path = output_path
        self.output_files = output_files or [output_path]
        self.disabled_detail = disabled_detail
        self._process: subprocess.Popen[str] | None = None
        self._handle = None

    def start(self) -> None:
        if not self.status.enabled:
            self.status.status = "skipped"
            self.status.detail = self.disabled_detail or "disabled in scenario"
            return
        binary = self.command[0]
        if not command_exists(binary):
            self.status.status = "skipped"
            self.status.detail = f"{binary} is not installed"
            return
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.output_path.open("w", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                self.command,
                stdout=self._handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:
            self.status.status = "failed"
            self.status.detail = f"failed to start collector: {exc}"
            if self._handle is not None:
                self._handle.close()
            return
        self.status.files.extend(str(path) for path in self.output_files)
        self.status.status = "started"

    def stop(self) -> None:
        if self.status.status != "started":
            return
        if self._process is not None and self._process.poll() is None:
            self._process.send_signal(signal.SIGINT)
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.terminate()
        if self._handle is not None:
            self._handle.close()
        self.status.status = "completed"


def build_collectors(
    *,
    config: CollectorsConfig,
    output_dir: Path,
    container_name: str | None,
    host_pid: int | None,
) -> list[BaseCollector]:
    collectors: list[BaseCollector] = [
        DockerStatsCollector(
            container_name=container_name,
            interval_ms=config.docker_stats.interval_ms,
            output_dir=output_dir,
            enabled=config.docker_stats.enabled,
        ),
    ]
    pidstat_output = output_dir / "pidstat.log"
    pidstat_command = (
        ["pidstat", "-h", "-u", "-r", "-d", "-w", "-p", str(host_pid), str(config.pidstat.interval_sec)]
        if host_pid is not None
        else ["pidstat"]
    )
    collectors.append(
        BackgroundCommandCollector(
            name="pidstat",
            enabled=config.pidstat.enabled and host_pid is not None,
            command=pidstat_command,
            output_path=pidstat_output,
            disabled_detail="host PID is unavailable" if host_pid is None else None,
        ),
    )

    perf_stat_output = output_dir / "perf_stat.csv"
    collectors.append(
        BackgroundCommandCollector(
            name="perf_stat",
            enabled=config.perf_stat.enabled and host_pid is not None,
            command=[
                "perf",
                "stat",
                "-I",
                str(config.perf_stat.interval_ms),
                "-x,",
                "-e",
                ",".join(PERF_STAT_EVENTS),
                "-p",
                str(host_pid),
                "-o",
                str(perf_stat_output),
                "sleep",
                "1000000",
            ]
            if host_pid is not None
            else ["perf"],
            output_path=output_dir / "perf_stat.stderr.log",
            output_files=[perf_stat_output, output_dir / "perf_stat.stderr.log"],
            disabled_detail="host PID is unavailable" if host_pid is None else None,
        ),
    )

    perf_record_output = output_dir / "perf.data"
    collectors.append(
        BackgroundCommandCollector(
            name="perf_record",
            enabled=config.perf_record.enabled and host_pid is not None,
            command=[
                "perf",
                "record",
                "-g",
                "-p",
                str(host_pid),
                "-o",
                str(perf_record_output),
                "sleep",
                "1000000",
            ]
            if host_pid is not None
            else ["perf"],
            output_path=output_dir / "perf_record.log",
            output_files=[perf_record_output, output_dir / "perf_record.log"],
            disabled_detail="host PID is unavailable" if host_pid is None else None,
        ),
    )
    iostat_output = output_dir / "iostat.log"
    collectors.append(
        BackgroundCommandCollector(
            name="iostat",
            enabled=config.iostat.enabled,
            command=["iostat", "-d", "-x", "-y", "-t", "-k", str(config.iostat.interval_sec)],
            output_path=iostat_output,
        ),
    )
    return collectors
