from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .utils import summarize_ms, write_json


LATENCY_FIELDS = [
    "scenario",
    "instance_index",
    "task_id",
    "task_name",
    "worker_id",
    "request_index",
    "session_key",
    "run_id",
    "success",
    "connect_latency_ms",
    "send_latency_ms",
    "wait_latency_ms",
    "history_latency_ms",
    "total_latency_ms",
    "send_status",
    "wait_status",
    "history_messages",
    "usage_session_id",
    "usage_timestamp",
    "usage_match_mode",
    "usage_provider",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "output_tokens_session_delta",
    "output_tps_request",
    "output_tps_session_delta",
    "started_at",
    "finished_at",
    "error",
]


def write_latency_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LATENCY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in LATENCY_FIELDS})


def build_summary(rows: list[dict[str, Any]], *, scenario_name: str) -> dict[str, Any]:
    success_rows = [row for row in rows if row.get("success")]
    total_latency = [float(row["total_latency_ms"]) for row in success_rows]
    send_latency = [float(row["send_latency_ms"]) for row in success_rows]
    wait_latency = [float(row["wait_latency_ms"]) for row in success_rows]
    history_latency = [float(row["history_latency_ms"]) for row in success_rows]
    input_tokens = _numeric_values(success_rows, "input_tokens")
    output_tokens = _numeric_values(success_rows, "output_tokens")
    total_tokens_metric = _numeric_values(success_rows, "total_tokens")
    output_tokens_session_delta = _numeric_values(success_rows, "output_tokens_session_delta")
    output_tps_request = _numeric_values(success_rows, "output_tps_request")
    output_tps_session_delta = _numeric_values(success_rows, "output_tps_session_delta")
    connect_by_worker: dict[tuple[int, int], float] = {}
    for row in rows:
        worker_id = row.get("worker_id")
        instance_index = row.get("instance_index", 0)
        connect_latency_ms = row.get("connect_latency_ms")
        if not isinstance(instance_index, int):
            instance_index = 0
        if not isinstance(worker_id, int):
            continue
        key = (instance_index, worker_id)
        if key in connect_by_worker:
            continue
        if connect_latency_ms in (None, "", 0):
            continue
        connect_by_worker[key] = float(connect_latency_ms)
    connect_latency = list(connect_by_worker.values())
    task_id = str(rows[0].get("task_id", "")) if rows else ""
    task_name = str(rows[0].get("task_name", "")) if rows else ""
    return {
        "scenario": scenario_name,
        "task": {
            "id": task_id,
            "name": task_name,
        },
        "requests_total": len(rows),
        "requests_ok": len(success_rows),
        "requests_failed": len(rows) - len(success_rows),
        "latency_ms": {
            "connect": summarize_ms(connect_latency),
            "send": summarize_ms(send_latency),
            "wait": summarize_ms(wait_latency),
            "history": summarize_ms(history_latency),
            "total": summarize_ms(total_latency),
        },
        "token_metrics": {
            "rows_with_usage": sum(1 for row in success_rows if isinstance(row.get("output_tokens"), (int, float))),
            "rows_with_request_tps": len(output_tps_request),
            "rows_with_session_delta_tps": len(output_tps_session_delta),
            "input_tokens": summarize_ms(input_tokens),
            "output_tokens": summarize_ms(output_tokens),
            "total_tokens": summarize_ms(total_tokens_metric),
            "output_tokens_session_delta": summarize_ms(output_tokens_session_delta),
            "output_tps_request": summarize_ms(output_tps_request),
            "output_tps_session_delta": summarize_ms(output_tps_session_delta),
        },
    }


def _numeric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(field)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return values


def write_summary(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)
