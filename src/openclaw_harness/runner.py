from __future__ import annotations

import asyncio
import copy
import shutil
import platform
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter_ns
from typing import Any
from uuid import uuid4

from .collectors import build_collectors
from .device_identity import load_or_create_device_identity
from .environment import probe_environment, summarize_environment
from .gateway_client import GatewayClient
from .parsers import parse_collector_artifacts, parse_session_usage_artifacts
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


@dataclass(slots=True)
class InstanceRunContext:
    instance_index: int
    output_dir: Path
    runtime_config: Any
    runtime_manager: Any
    runtime_info: Any
    collectors: list[Any]
    preflight: dict[str, Any]
    rows: list[dict[str, object]] = field(default_factory=list)
    collector_analysis: dict[str, object] = field(default_factory=dict)
    failure: str | None = None
    started_at: str = ""


async def execute_load(
    scenario: ScenarioConfig,
    urls: list[str],
    token: str,
    *,
    device_identity,
    instance_index: int = 0,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    max_parallel_connects = min(4, max(1, scenario.load.concurrency))
    connect_gate = asyncio.Semaphore(max_parallel_connects)

    async def worker(worker_id: int) -> None:
        if scenario.load.worker_stagger_ms > 0:
            await asyncio.sleep((scenario.load.worker_stagger_ms * worker_id) / 1000.0)
        openclaw_index = worker_id % len(urls)
        url = urls[openclaw_index]
        client = GatewayClient(
            url=url,
            token=token,
            role=scenario.client.role,
            instance_id=(
                f"{slugify(scenario.name)}-i{instance_index:02d}-oc{openclaw_index:02d}-"
                f"{worker_id}-{uuid4().hex[:8]}"
            ),
            device_identity=device_identity,
        )
        connect_latency_ms = 0.0
        try:
            async with connect_gate:
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
                        "instance_index": instance_index,
                        "openclaw_index": openclaw_index,
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
                        "gateway_url": url,
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


def build_instance_output_dir(*, run_dir: Path, instance_index: int, instance_count: int) -> Path:
    if instance_count <= 1:
        return run_dir
    return ensure_directory(run_dir / "instances" / f"instance-{instance_index:02d}")


def build_instance_container_name(
    *,
    scenario: ScenarioConfig,
    instance_index: int,
    instance_count: int,
) -> str:
    base = f"{scenario.runtime.container_name_base}-{slugify(scenario.name)}"
    if instance_count > 1:
        base = f"{base}-i{instance_index:02d}"
    return f"{base}-{uuid4().hex[:8]}"


def build_instance_runtime_config(
    *,
    scenario: ScenarioConfig,
    instance_index: int,
) -> Any:
    config = copy.deepcopy(scenario.runtime)
    config.instance_num = 1
    if scenario.runtime.instance_num > 1:
        openclaw_port_count = max(1, int(scenario.runtime.openclaw_num_per_instance))
        port_stride = max(10, openclaw_port_count) if scenario.runtime.network_mode == "host" else openclaw_port_count
        config.host_port = scenario.runtime.host_port + (instance_index * port_stride)
        config.force_rebuild = scenario.runtime.force_rebuild and instance_index == 0
    return config


def build_preflight_payload(
    *,
    scenario: ScenarioConfig,
    runtime_info,
    runtime_manager,
    collectors,
) -> dict[str, Any]:
    runtime_state = runtime_manager.dump_state()
    healthcheck_url = None
    if runtime_state.get("resolved_healthcheck_url"):
        healthcheck_url = str(runtime_state["resolved_healthcheck_url"])
    elif runtime_state.get("healthcheck_url"):
        healthcheck_url = str(runtime_state["healthcheck_url"])
    elif scenario.runtime.kind == "docker":
        healthcheck_url = f"http://{scenario.runtime.host}:{scenario.runtime.host_port}/healthz"

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
                    else "host PID auto-discovery failed; pidstat/strace/perf host collectors will be skipped unless runtime.host_pid is set"
                ),
            },
        )

    collector_targets: list[dict[str, Any]] = []
    for collector in collectors:
        target = "none"
        if collector.status.name == "docker_stats":
            target = runtime_info.container_name or "container unavailable"
        elif collector.status.name in {"pidstat", "strace", "perf_stat", "perf_record"}:
            target = str(runtime_info.host_pid) if runtime_info.host_pid is not None else "host PID unavailable"
        elif collector.status.name == "node_trace":
            target = "runtime workspace"
        elif collector.status.name == "vmstat":
            target = "host system"
        elif collector.status.name == "npu_smi":
            target = "host NPU devices"
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
            "urls": list(getattr(runtime_info, "urls", []) or [runtime_info.url]),
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


def build_aggregate_preflight(contexts: list[InstanceRunContext]) -> dict[str, Any]:
    if len(contexts) == 1:
        return contexts[0].preflight
    instances = [
        {
            "instance_index": context.instance_index,
            "output_dir": str(context.output_dir),
            **context.preflight,
        }
        for context in contexts
    ]
    warnings: list[str] = []
    for context in contexts:
        warnings.extend(str(item) for item in context.preflight.get("warnings", []) if item)
    return {
        "runtime_kind": contexts[0].runtime_info.kind if contexts else "unknown",
        "instance_num": len(contexts),
        "ready": all(context.preflight.get("ready", False) for context in contexts),
        "checked_at": iso_now(),
        "instances": instances,
        "warnings": warnings,
    }


def build_aggregate_collector_analysis(contexts: list[InstanceRunContext]) -> dict[str, object]:
    if len(contexts) == 1:
        return contexts[0].collector_analysis
    return {
        "instances": [
            {
                "instance_index": context.instance_index,
                "output_dir": str(context.output_dir),
                "analysis": context.collector_analysis,
            }
            for context in contexts
        ]
    }


def summary_only_keep_files() -> set[str]:
    return {
        "summary.json",
        "latency.csv",
        "docker_stats.csv",
        "perf_stat.csv",
        "perf_stat.parsed.csv",
        "perf_stat.summary.json",
        "pidstat.log",
        "iostat.log",
        "vmstat.log",
        "vmstat.parsed.csv",
        "vmstat.summary.json",
        "npu_smi.log",
        "npu_smi.parsed.csv",
        "npu_smi.summary.json",
    }


def prepare_instance(
    *,
    scenario: ScenarioConfig,
    run_dir: Path,
    instance_index: int,
    device_identity,
) -> InstanceRunContext:
    instance_output_dir = build_instance_output_dir(
        run_dir=run_dir,
        instance_index=instance_index,
        instance_count=scenario.runtime.instance_num,
    )
    runtime_config = build_instance_runtime_config(
        scenario=scenario,
        instance_index=instance_index,
    )
    if scenario.runtime.instance_num > 1:
        instance_payload = scenario.to_dict()
        instance_payload["runtime"] = asdict(runtime_config)
        instance_payload["instance_index"] = instance_index
        write_json(instance_output_dir / "scenario.resolved.json", instance_payload)
    container_name = build_instance_container_name(
        scenario=scenario,
        instance_index=instance_index,
        instance_count=scenario.runtime.instance_num,
    )
    runtime_manager = create_runtime_manager(
        config=runtime_config,
        node_trace=scenario.collectors.node_trace,
        output_dir=instance_output_dir,
        container_name=container_name,
        device_identity=device_identity,
    )
    runtime_info = runtime_manager.start()
    collectors = build_collectors(
        config=scenario.collectors,
        output_dir=instance_output_dir,
        container_name=runtime_info.container_name,
        host_pid=runtime_info.host_pid,
    )
    preflight = build_preflight_payload(
        scenario=scenario,
        runtime_info=runtime_info,
        runtime_manager=runtime_manager,
        collectors=collectors,
    )
    write_json(instance_output_dir / "preflight.json", preflight)
    for collector in collectors:
        collector.start()
    return InstanceRunContext(
        instance_index=instance_index,
        output_dir=instance_output_dir,
        runtime_config=runtime_config,
        runtime_manager=runtime_manager,
        runtime_info=runtime_info,
        collectors=collectors,
        preflight=preflight,
    )


def finalize_instance(
    *,
    scenario: ScenarioConfig,
    environment: dict[str, Any],
    context: InstanceRunContext,
) -> None:
    for collector in reversed(context.collectors):
        collector.stop()
    context.runtime_manager.stop()
    context.collector_analysis = parse_collector_artifacts(
        output_dir=context.output_dir,
        collectors=context.collectors,
    )
    session_usage_summary = parse_session_usage_artifacts(output_dir=context.output_dir, rows=context.rows)
    if session_usage_summary is not None:
        context.collector_analysis["session_usage"] = session_usage_summary
    write_latency_csv(context.output_dir / "latency.csv", context.rows)
    summary = build_summary(context.rows, scenario_name=scenario.name)
    summary["instance_index"] = context.instance_index
    summary["task"] = {
        "source": "task_file" if scenario.client.task_file else "message",
        "task_file": scenario.client.task_file,
        "id": scenario.client.task_id,
        "name": scenario.client.task_name,
        "category": scenario.client.task_category,
    }
    summary["environment"] = summarize_environment(environment)
    summary["preflight"] = {
        "ready": context.preflight["ready"],
        "target": context.preflight["target"],
        "warnings": context.preflight["warnings"],
    }
    summary["collector_analysis"] = context.collector_analysis
    summary["started_at"] = context.started_at
    summary["finished_at"] = iso_now()
    summary["failure"] = context.failure
    write_summary(context.output_dir / "summary.json", summary)
    meta = {
        "scenario": scenario.to_dict(),
        "instance_index": context.instance_index,
        "instance_runtime": asdict(context.runtime_config),
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
        "preflight": context.preflight,
        "runtime": asdict(context.runtime_info),
        "runtime_manager": context.runtime_manager.dump_state(),
        "collectors": [collector.status.to_dict() for collector in context.collectors],
        "collector_analysis": context.collector_analysis,
        "started_at": context.started_at,
        "finished_at": iso_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "failure": context.failure,
    }
    write_json(context.output_dir / "meta.json", meta)
    if scenario.artifacts.summary_only and scenario.runtime.instance_num > 1:
        prune_run_artifacts(run_dir=context.output_dir, keep_files=summary_only_keep_files())

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
    output_root = output_root.resolve()
    device_identity = load_or_create_device_identity()
    run_dir = ensure_directory(output_root / f"{timestamp_slug()}_{slugify(scenario.name)}")
    write_json(run_dir / "scenario.resolved.json", scenario.to_dict())
    environment = probe_environment(scenario=scenario, output_dir=run_dir)

    contexts: list[InstanceRunContext] = []
    preflight: dict[str, Any] = {}
    started_at = ""
    rows: list[dict[str, object]] = []
    failure: str | None = None
    collector_analysis: dict[str, object] = {}
    try:
        for instance_index in range(scenario.runtime.instance_num):
            context = prepare_instance(
                scenario=scenario,
                run_dir=run_dir,
                instance_index=instance_index,
                device_identity=device_identity,
            )
            contexts.append(context)
        preflight = build_aggregate_preflight(contexts)
        write_json(run_dir / "preflight.json", preflight)

        started_at = iso_now()
        for context in contexts:
            context.started_at = started_at

        load_tasks = [
            asyncio.create_task(
                execute_load(
                    scenario,
                    list(context.runtime_info.urls or [context.runtime_info.url]),
                    context.runtime_info.token,
                    device_identity=device_identity,
                    instance_index=context.instance_index,
                ),
            )
            for context in contexts
        ]
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        failures: list[str] = []
        for context, result in zip(contexts, load_results):
            if isinstance(result, Exception):
                context.failure = str(result)
                failures.append(f"instance {context.instance_index}: {result}")
                continue
            context.rows = result
            rows.extend(result)
        if failures:
            failure = "; ".join(failures)
    except Exception as exc:
        failure = str(exc)
        raise
    finally:
        for context in contexts:
            finalize_instance(
                scenario=scenario,
                environment=environment,
                context=context,
            )
        collector_analysis = build_aggregate_collector_analysis(contexts)
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
            "runtime": (
                asdict(contexts[0].runtime_info)
                if len(contexts) == 1
                else {
                    "kind": scenario.runtime.kind,
                    "instance_num": len(contexts),
                }
            ),
            "runtime_manager": (
                contexts[0].runtime_manager.dump_state()
                if len(contexts) == 1
                else {
                    "instances": [
                        {
                            "instance_index": context.instance_index,
                            "output_dir": str(context.output_dir),
                            "state": context.runtime_manager.dump_state(),
                        }
                        for context in contexts
                    ]
                }
            ),
            "instances": [
                {
                    "instance_index": context.instance_index,
                    "output_dir": str(context.output_dir),
                    "runtime": asdict(context.runtime_info),
                    "runtime_manager": context.runtime_manager.dump_state(),
                    "collectors": [collector.status.to_dict() for collector in context.collectors],
                    "collector_analysis": context.collector_analysis,
                    "preflight": context.preflight,
                    "failure": context.failure,
                }
                for context in contexts
            ],
            "collector_analysis": collector_analysis,
            "started_at": started_at,
            "finished_at": iso_now(),
            "python": sys.version,
            "platform": platform.platform(),
            "failure": failure,
        }
        write_json(run_dir / "meta.json", meta)

    if failure:
        raise RuntimeError(failure)

    write_latency_csv(run_dir / "latency.csv", rows)
    summary = build_summary(rows, scenario_name=scenario.name)
    summary["instance_num"] = scenario.runtime.instance_num
    summary["openclaw_num_per_instance"] = scenario.runtime.openclaw_num_per_instance
    summary["openclaw_num_total"] = scenario.runtime.instance_num * scenario.runtime.openclaw_num_per_instance
    summary["task"] = {
        "source": "task_file" if scenario.client.task_file else "message",
        "task_file": scenario.client.task_file,
        "id": scenario.client.task_id,
        "name": scenario.client.task_name,
        "category": scenario.client.task_category,
    }
    summary["environment"] = summarize_environment(environment)
    if len(contexts) == 1:
        summary["preflight"] = {
            "ready": preflight["ready"],
            "target": preflight["target"],
            "warnings": preflight["warnings"],
        }
    else:
        summary["preflight"] = {
            "ready": preflight["ready"],
            "targets": [context.preflight["target"] for context in contexts],
            "warnings": preflight["warnings"],
        }
        summary["instances"] = [
            {
                "instance_index": context.instance_index,
                "output_dir": str(context.output_dir),
                "requests_total": len(context.rows),
                "requests_ok": sum(1 for row in context.rows if row.get("success")),
                "requests_failed": sum(1 for row in context.rows if not row.get("success")),
                "failure": context.failure,
            }
            for context in contexts
        ]
    summary["collector_analysis"] = collector_analysis
    summary["started_at"] = started_at
    summary["finished_at"] = iso_now()
    write_summary(run_dir / "summary.json", summary)
    if scenario.artifacts.summary_only:
        keep_files = summary_only_keep_files()
        if scenario.runtime.instance_num > 1:
            keep_files = set(keep_files)
            keep_files.add("instances")
        prune_run_artifacts(run_dir=run_dir, keep_files=keep_files)
    return run_dir
