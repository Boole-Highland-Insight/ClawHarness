from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any

from .scenario import ScenarioConfig
from .utils import command_path, run_command, write_json


def probe_environment(*, scenario: ScenarioConfig, output_dir: Path) -> dict[str, Any]:
    os_release = _read_os_release()
    kernel_release = platform.release()
    kernel_version = platform.version()
    machine = platform.machine()
    wsl_distro = os.getenv("WSL_DISTRO_NAME", "").strip()
    is_wsl = bool(wsl_distro) or "microsoft" in kernel_release.lower() or "wsl" in kernel_release.lower()
    distro_id = str(os_release.get("ID", "")).lower()
    is_ubuntu = distro_id == "ubuntu"

    tools = {
        "docker": _probe_tool("docker", None),
        "pidstat": _probe_tool("pidstat", ["pidstat", "-V"]),
        "iostat": _probe_tool("iostat", ["iostat", "-V"]),
        "perf": _probe_tool("perf", ["perf", "--version"]),
    }
    install_hints = _build_install_hints(
        is_ubuntu=is_ubuntu,
        is_wsl=is_wsl,
        kernel_release=kernel_release,
    )
    recommended_collectors = _build_recommended_collectors(
        scenario_name=scenario.name,
        runtime_kind=scenario.runtime.kind,
        is_wsl=is_wsl,
    )
    notes = _build_notes(is_wsl=is_wsl, tools=tools)

    payload = {
        "host": {
            "os_release": os_release,
            "kernel_release": kernel_release,
            "kernel_version": kernel_version,
            "machine": machine,
            "is_wsl": is_wsl,
            "wsl_distro_name": wsl_distro or None,
            "python": platform.python_version(),
        },
        "tools": tools,
        "recommended_collectors": recommended_collectors,
        "install_hints": install_hints,
        "notes": notes,
        "scenario": {
            "name": scenario.name,
            "runtime_kind": scenario.runtime.kind,
            "configured_collectors": {
                "docker_stats": scenario.collectors.docker_stats.enabled,
                "pidstat": scenario.collectors.pidstat.enabled,
                "iostat": scenario.collectors.iostat.enabled,
                "perf_stat": scenario.collectors.perf_stat.enabled,
                "perf_record": scenario.collectors.perf_record.enabled,
            },
        },
    }
    write_json(output_dir / "environment.json", payload)
    return payload


def summarize_environment(payload: dict[str, Any]) -> dict[str, Any]:
    host = payload.get("host", {})
    os_release = host.get("os_release", {})
    tools = payload.get("tools", {})
    return {
        "os": {
            "pretty_name": os_release.get("PRETTY_NAME", ""),
            "kernel_release": host.get("kernel_release", ""),
            "is_wsl": bool(host.get("is_wsl")),
        },
        "tools": {name: bool(info.get("usable", info.get("available"))) for name, info in tools.items()},
        "recommended_collectors": payload.get("recommended_collectors", {}),
        "notes": payload.get("notes", []),
    }


def _read_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.exists():
        return {}
    payload: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        payload[key] = raw_value.strip().strip('"')
    return payload


def _build_install_hints(
    *,
    is_ubuntu: bool,
    is_wsl: bool,
    kernel_release: str,
) -> dict[str, dict[str, str]]:
    hints: dict[str, dict[str, str]] = {}
    if is_ubuntu:
        hints["pidstat"] = {
            "package": "sysstat",
            "command": "sudo apt update && sudo apt install -y sysstat",
        }
        hints["iostat"] = {
            "package": "sysstat",
            "command": "sudo apt update && sudo apt install -y sysstat",
            "note": "iostat ships with sysstat on Ubuntu.",
        }
        perf_command = (
            "sudo apt update && sudo apt install -y linux-tools-common linux-tools-generic "
            "linux-cloud-tools-generic"
        )
        perf_note = (
            "WSL kernels often do not have an exact linux-tools package match; if perf is unavailable, "
            "collect formal CPU profiles on the VPS instead."
            if is_wsl
            else "Install the generic linux-tools packages first, then verify perf against the target kernel."
        )
        hints["perf"] = {
            "package": "linux-tools-common linux-tools-generic linux-cloud-tools-generic",
            "command": perf_command,
            "note": perf_note,
        }
        if is_wsl:
            hints["perf"]["suggested_kernel_packages"] = (
                f"linux-tools-{kernel_release} linux-cloud-tools-{kernel_release} "
                "linux-tools-standard-WSL2 linux-cloud-tools-standard-WSL2"
            )
            hints["perf"]["wsl_note"] = (
                "If those WSL-specific packages are not present in apt, treat perf as unavailable locally "
                "and collect perf data on the VPS."
            )
    return hints


def _build_recommended_collectors(
    *,
    scenario_name: str,
    runtime_kind: str,
    is_wsl: bool,
) -> dict[str, dict[str, Any]]:
    docker_enabled = runtime_kind == "docker"
    pidstat_reason = "recommended for host/container PID tracking"
    if runtime_kind == "host_direct":
        pidstat_reason = "recommended when runtime.host_pid is provided"
    perf_reason = "recommended for formal CPU counters and top-down analysis"
    perf_enabled = not is_wsl
    if is_wsl:
        perf_reason = "leave disabled on WSL; use VPS for formal CPU profiling"
    return {
        "docker_stats": {
            "enabled": docker_enabled,
            "reason": "recommended for docker runtimes" if docker_enabled else "not needed for host_direct",
        },
        "pidstat": {
            "enabled": True,
            "reason": pidstat_reason,
        },
        "iostat": {
            "enabled": True,
            "reason": "recommended when you want disk await, queue depth, and %util evidence",
        },
        "perf_stat": {
            "enabled": perf_enabled,
            "reason": perf_reason,
        },
        "perf_record": {
            "enabled": False,
            "reason": f"keep off by default; enable only for targeted profiling runs ({scenario_name})",
        },
    }


def _build_notes(*, is_wsl: bool, tools: dict[str, dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if is_wsl:
        notes.append("WSL detected: use latency, docker stats, and pidstat locally; prefer VPS for perf-based CPU conclusions.")
    if not tools["pidstat"]["usable"]:
        notes.append(tools["pidstat"]["detail"] or "pidstat is not usable on this host.")
    if not tools["iostat"]["usable"]:
        notes.append(tools["iostat"]["detail"] or "iostat is not usable on this host.")
    if not tools["perf"]["usable"]:
        notes.append(tools["perf"]["detail"] or "perf is not usable on this host.")
    return notes


def _probe_tool(name: str, probe_command: list[str] | None) -> dict[str, Any]:
    path = command_path(name)
    payload = {
        "available": path is not None,
        "usable": path is not None,
        "path": path,
        "detail": "",
    }
    if path is None or probe_command is None:
        if path is None:
            payload["usable"] = False
            payload["detail"] = f"{name} is not installed on this host."
        return payload
    result = run_command(probe_command, check=False)
    combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    payload["probe_command"] = " ".join(probe_command)
    payload["probe_output"] = combined_output
    if name == "perf" and "perf not found for kernel" in combined_output.lower():
        payload["usable"] = False
        payload["detail"] = (
            "perf wrapper exists, but no kernel-matched perf binary is available for this WSL kernel."
        )
        return payload
    if result.returncode != 0:
        payload["usable"] = False
        payload["detail"] = combined_output or f"{name} probe failed"
    return payload
