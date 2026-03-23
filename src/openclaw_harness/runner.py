from __future__ import annotations

import asyncio
import shutil
import platform
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter_ns
from typing import Any
from uuid import uuid4

from .collectors import build_collectors
from .device_identity import load_or_create_device_identity
from .environment import probe_environment, summarize_environment
from .gateway_client import GatewayClient
from .parsers import parse_collector_artifacts
from .reporting import build_summary, write_latency_csv, write_summary
from .runtime import create_runtime_manager
from .scenario import ScenarioConfig
from .utils import ensure_directory, iso_now, slugify, timestamp_slug, write_json


def resolve_session_key(
    *,
    scenario: ScenarioConfig,
    worker_id: int,
    request_index: int,
) -> str:
    prefix = scenario.client.session_prefix
    mode = scenario.client.session_mode
    if mode == "shared":
        return f"{prefix}-shared"
    if mode == "per_request":
        return f"{prefix}-w{worker_id}-r{request_index}"
    return f"{prefix}-w{worker_id}"


async def execute_load(
    scenario: ScenarioConfig,
    url: str,
    token: str,
    *,
    device_identity,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    async def worker(worker_id: int) -> None:
        if scenario.load.worker_stagger_ms > 0:
            await asyncio.sleep((scenario.load.worker_stagger_ms * worker_id) / 1000.0)
        client = GatewayClient(
            url=url,
            token=token,
            role=scenario.client.role,
            instance_id=f"{slugify(scenario.name)}-{worker_id}-{uuid4().hex[:8]}",
            device_identity=device_identity,
        )
        connect_latency_ms = 0.0
        try:
            connect_latency_ms = await client.connect()
            for request_index in range(scenario.load.requests_per_worker):
                session_key = resolve_session_key(
                    scenario=scenario,
                    worker_id=worker_id,
                    request_index=request_index,
                )
                run_id = str(uuid4())
                started_at = iso_now()
                error_text = ""
                send_status = ""
                wait_status = ""
                history_messages = 0
                send_latency_ms = 0.0
                wait_latency_ms = 0.0
                history_latency_ms = 0.0
                total_started = perf_counter_ns()
                success = False
                try:
                    send_started = perf_counter_ns()
                    send_response = await client.send_chat(
                        session_key=session_key,
                        message=scenario.client.effective_message(),
                        run_id=run_id,
                        timeout_ms=scenario.client.send_timeout_ms,
                    )
                    send_latency_ms = (perf_counter_ns() - send_started) / 1_000_000.0
                    send_status = str((send_response.payload or {}).get("status", ""))
                    if not send_response.ok:
                        raise RuntimeError(f"chat.send failed: {send_response.error}")

                    wait_started = perf_counter_ns()
                    wait_response = await client.wait_for_agent(
                        run_id=run_id,
                        timeout_ms=scenario.client.wait_timeout_ms,
                    )
                    wait_latency_ms = (perf_counter_ns() - wait_started) / 1_000_000.0
                    wait_status = str((wait_response.payload or {}).get("status", ""))
                    if not wait_response.ok:
                        raise RuntimeError(f"agent.wait failed: {wait_response.error}")

                    history_started = perf_counter_ns()
                    history_response = await client.load_history(
                        session_key=session_key,
                        limit=scenario.client.history_limit,
                    )
                    history_latency_ms = (perf_counter_ns() - history_started) / 1_000_000.0
                    history_messages = len((history_response.payload or {}).get("messages", []) or [])
                    if not history_response.ok:
                        raise RuntimeError(f"chat.history failed: {history_response.error}")
                    success = bool(send_response.ok and wait_response.ok and history_response.ok)
                except Exception as exc:
                    error_text = str(exc)
                finished_at = iso_now()
                total_latency_ms = (perf_counter_ns() - total_started) / 1_000_000.0
                records.append(
                    {
                        "scenario": scenario.name,
                        "task_id": scenario.client.task_id,
                        "task_name": scenario.client.task_name,
                        "worker_id": worker_id,
                        "request_index": request_index,
                        "session_key": session_key,
                        "run_id": run_id,
                        "success": success,
                        "connect_latency_ms": round(connect_latency_ms, 3),
                        "send_latency_ms": round(send_latency_ms, 3),
                        "wait_latency_ms": round(wait_latency_ms, 3),
                        "history_latency_ms": round(history_latency_ms, 3),
                        "total_latency_ms": round(total_latency_ms, 3),
                        "send_status": send_status,
                        "wait_status": wait_status,
                        "history_messages": history_messages,
                        "started_at": started_at,
                        "finished_at": finished_at,
                        "error": error_text,
                    },
                )
                if scenario.load.request_pause_ms > 0:
                    await asyncio.sleep(scenario.load.request_pause_ms / 1000.0)
        finally:
            await client.close()

    tasks = [asyncio.create_task(worker(worker_id)) for worker_id in range(scenario.load.concurrency)]
    await asyncio.gather(*tasks)
    return records


def build_preflight_payload(
    *,
    scenario: ScenarioConfig,
    runtime_info,
    runtime_manager,
    collectors,
) -> dict[str, Any]:
    runtime_state = runtime_manager.dump_state()
    healthcheck_url = None
    if scenario.runtime.kind == "docker":
        healthcheck_url = f"http://{scenario.runtime.host}:{scenario.runtime.host_port}/healthz"
    elif runtime_state.get("healthcheck_url"):
        healthcheck_url = str(runtime_state["healthcheck_url"])

    checks: list[dict[str, Any]] = [
        {
            "name": "runtime_reachable",
            "status": "ok",
            "detail": "runtime start completed and healthcheck passed",
        },
        {
            "name": "target_url",
            "status": "ok",
            "detail": runtime_info.url,
        },
    ]
    if healthcheck_url:
        checks.append(
            {
                "name": "healthcheck_url",
                "status": "ok",
                "detail": healthcheck_url,
            },
        )
    if scenario.runtime.kind == "host_direct":
        checks.append(
            {
                "name": "host_pid",
                "status": "ok" if runtime_info.host_pid is not None else "warn",
                "detail": (
                    f"{runtime_info.host_pid} ({runtime_info.host_pid_source or 'configured'})"
                    if runtime_info.host_pid is not None
                    else "host PID auto-discovery failed; pidstat/perf host collectors will be skipped unless runtime.host_pid is set"
                ),
            },
        )

    collector_targets: list[dict[str, Any]] = []
    for collector in collectors:
        target = "none"
        if collector.status.name == "docker_stats":
            target = runtime_info.container_name or "container unavailable"
        elif collector.status.name in {"pidstat", "perf_stat", "perf_record"}:
            target = str(runtime_info.host_pid) if runtime_info.host_pid is not None else "host PID unavailable"
        collector_targets.append(
            {
                "name": collector.status.name,
                "enabled": collector.status.enabled,
                "status": collector.status.status,
                "detail": collector.status.detail,
                "target": target,
            },
        )

    warnings = [
        str(check["detail"])
        for check in checks
        if check["status"] == "warn" and check.get("detail")
    ]
    warnings.extend(
        str(collector["detail"])
        for collector in collector_targets
        if collector["status"] == "skipped" and collector.get("detail")
    )

    return {
        "runtime_kind": runtime_info.kind,
        "ready": all(check["status"] != "error" for check in checks),
        "checked_at": iso_now(),
        "target": {
            "url": runtime_info.url,
            "healthcheck_url": healthcheck_url,
            "container_name": runtime_info.container_name,
            "container_id": runtime_info.container_id,
            "host_pid": runtime_info.host_pid,
            "host_pid_source": runtime_info.host_pid_source,
        },
        "checks": checks,
        "collectors": collector_targets,
        "warnings": warnings,
    }


def prune_run_artifacts(*, run_dir: Path, keep_files: set[str]) -> None:
    for path in run_dir.iterdir():
        if path.name in keep_files:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


async def run_scenario(
    scenario: ScenarioConfig,
    *,
    output_root: Path,
    keep_runtime: bool = False,
) -> Path:
    if keep_runtime:
        scenario.runtime.keep_container = True
    device_identity = load_or_create_device_identity()
    run_dir = ensure_directory(output_root / f"{timestamp_slug()}_{slugify(scenario.name)}")
    write_json(run_dir / "scenario.resolved.json", scenario.to_dict())
    environment = probe_environment(scenario=scenario, output_dir=run_dir)

    container_name = f"{scenario.runtime.container_name_base}-{slugify(scenario.name)}-{uuid4().hex[:8]}"
    runtime_manager = create_runtime_manager(
        config=scenario.runtime,
        output_dir=run_dir,
        container_name=container_name,
        device_identity=device_identity,
    )
    runtime_info = runtime_manager.start()
    collectors = build_collectors(
        config=scenario.collectors,
        output_dir=run_dir,
        container_name=runtime_info.container_name,
        host_pid=runtime_info.host_pid,
    )
    preflight = build_preflight_payload(
        scenario=scenario,
        runtime_info=runtime_info,
        runtime_manager=runtime_manager,
        collectors=collectors,
    )
    write_json(run_dir / "preflight.json", preflight)
    for collector in collectors:
        collector.start()

    started_at = iso_now()
    rows: list[dict[str, object]] = []
    failure: str | None = None
    collector_analysis: dict[str, object] = {}
    try:
        rows = await execute_load(
            scenario,
            runtime_info.url,
            runtime_info.token,
            device_identity=device_identity,
        )
    except Exception as exc:
        failure = str(exc)
        raise
    finally:
        for collector in reversed(collectors):
            collector.stop()
        collector_analysis = parse_collector_artifacts(
            output_dir=run_dir,
            collectors=collectors,
        )
        runtime_manager.stop()
        meta = {
            "scenario": scenario.to_dict(),
            "task": {
                "source": "task_file" if scenario.client.task_file else "message",
                "task_file": scenario.client.task_file,
                "task_id": scenario.client.task_id,
                "task_name": scenario.client.task_name,
                "task_category": scenario.client.task_category,
                "task_description": scenario.client.task_description,
                "resolved_prompt": scenario.client.effective_message(),
            },
            "environment": environment,
            "preflight": preflight,
            "runtime": asdict(runtime_info),
            "runtime_manager": runtime_manager.dump_state(),
            "collectors": [collector.status.to_dict() for collector in collectors],
            "collector_analysis": collector_analysis,
            "started_at": started_at,
            "finished_at": iso_now(),
            "python": sys.version,
            "platform": platform.platform(),
            "failure": failure,
        }
        write_json(run_dir / "meta.json", meta)

    write_latency_csv(run_dir / "latency.csv", rows)
    summary = build_summary(rows, scenario_name=scenario.name)
    summary["task"] = {
        "source": "task_file" if scenario.client.task_file else "message",
        "task_file": scenario.client.task_file,
        "id": scenario.client.task_id,
        "name": scenario.client.task_name,
        "category": scenario.client.task_category,
    }
    summary["environment"] = summarize_environment(environment)
    summary["preflight"] = {
        "ready": preflight["ready"],
        "target": preflight["target"],
        "warnings": preflight["warnings"],
    }
    summary["collector_analysis"] = collector_analysis
    summary["started_at"] = started_at
    summary["finished_at"] = iso_now()
    write_summary(run_dir / "summary.json", summary)
    if scenario.artifacts.summary_only:
        prune_run_artifacts(
            run_dir=run_dir,
            keep_files={
                "summary.json",
                "latency.csv",
                "docker_stats.csv",
                "perf_stat.csv",
                "perf_stat.parsed.csv",
                "perf_stat.summary.json",
                "pidstat.log",
                "iostat.log",
            },
        )
    return run_dir
