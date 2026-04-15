from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    plt = None


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "out"
RES_ROOT = REPO_ROOT / "res"
SCRIPTS_ROOT = REPO_ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS_ROOT))

try:
    from plot_latency import LATENCY_COLUMNS, load_points
except ModuleNotFoundError:
    LATENCY_COLUMNS = [
        ("connect_latency_ms", "Connect"),
        ("send_latency_ms", "Send"),
        ("wait_latency_ms", "Wait"),
        ("history_latency_ms", "History"),
        ("total_latency_ms", "Total"),
    ]

    def load_points(csv_path: Path, only_success: bool) -> list[Any]:
        raise RuntimeError("plot_latency dependencies are unavailable; rerun without --skip-figures or install matplotlib")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export comparison charts and tables for one or more scenario pairs.",
    )
    parser.add_argument(
        "--pair",
        action="append",
        nargs=2,
        metavar=("SINGLE", "MULTI"),
        required=True,
        help="Scenario names to compare. May be repeated.",
    )
    parser.add_argument(
        "--out-root",
        default=str(OUT_ROOT),
        help="Benchmark output root directory. Defaults to repo/out.",
    )
    parser.add_argument(
        "--res-root",
        default=str(RES_ROOT),
        help="Report output root directory. Defaults to repo/res.",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Refresh markdown/tables only and keep any existing figures untouched.",
    )
    return parser.parse_args()


def find_latest_run_dir(out_root: Path, scenario_name: str) -> Path:
    candidates = sorted(
        [path for path in out_root.iterdir() if path.is_dir() and path.name.endswith(f"_{scenario_name}")],
        key=lambda path: path.name,
    )
    if not candidates:
        raise FileNotFoundError(f"No run directory found for scenario: {scenario_name}")
    return candidates[-1]


def load_summary(run_dir: Path) -> dict[str, Any]:
    return json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))


def nested_get(data: dict[str, Any], path: list[Any], default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if isinstance(current, dict):
            if key not in current:
                return default
            current = current[key]
            continue
        if isinstance(current, list) and isinstance(key, int):
            if key < 0 or key >= len(current):
                return default
            current = current[key]
            continue
        return default
    return current


def metric_mean(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    metric = nested_get(data, path, None)
    if isinstance(metric, dict):
        return metric.get("mean", default)
    return default


def metric_summary_mean(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    metric = nested_get(data, path, None)
    if isinstance(metric, dict):
        summary = metric.get("summary")
        if isinstance(summary, dict):
            return summary.get("mean", default)
    return default


def time_series_points(data: dict[str, Any], path: list[str]) -> list[tuple[float, float]]:
    entry = nested_get(data, path, None)
    if not isinstance(entry, dict):
        return []
    points = entry.get("points")
    if not isinstance(points, list):
        return []
    result: list[tuple[float, float]] = []
    for point in points:
        if not isinstance(point, dict):
            continue
        t_sec = point.get("t_sec")
        value = point.get("value")
        if isinstance(t_sec, (int, float)) and isinstance(value, (int, float)):
            result.append((float(t_sec), float(value)))
    return result


def time_series_peak_value(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    entry = nested_get(data, path, None)
    if not isinstance(entry, dict):
        return default
    peak = entry.get("peak")
    if not isinstance(peak, dict):
        return default
    value = peak.get("value")
    return value if isinstance(value, (int, float)) else default


def time_series_peak_t_sec(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    entry = nested_get(data, path, None)
    if not isinstance(entry, dict):
        return default
    peak = entry.get("peak")
    if not isinstance(peak, dict):
        return default
    value = peak.get("t_sec")
    return value if isinstance(value, (int, float)) else default


def safe_slug(value: str) -> str:
    chars: list[str] = []
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "-":
            chars.append("-")
    return "".join(chars).strip("-")


def format_scalar(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if math.isnan(value):
            return "-"
        return f"{value:.3f}"
    return str(value)


def build_resource_profile_row(summary: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    latency = summary["latency_ms"]
    docker = nested_get(summary, ["collector_analysis", "docker_stats"], {})
    pidstat = nested_get(summary, ["collector_analysis", "pidstat", "sections"], {})
    iostat = nested_get(summary, ["collector_analysis", "iostat"], {})
    vmstat = nested_get(summary, ["collector_analysis", "vmstat"], {})
    npu_smi = nested_get(summary, ["collector_analysis", "npu_smi"], {})
    perf_stat = nested_get(summary, ["collector_analysis", "perf_stat"], {})
    strace = nested_get(summary, ["collector_analysis", "strace"], {})
    node_trace = nested_get(summary, ["collector_analysis", "node_trace"], {})
    gateway_runtime = nested_get(summary, ["collector_analysis", "gateway_runtime_spans"], {})
    busiest_device = (
        nested_get(summary, ["collector_analysis", "iostat", "key_metrics", "busiest_device"])
        or iostat.get("busiest_device_by_util_mean")
    )
    device_metrics = nested_get(iostat, ["devices", busiest_device, "metrics"], {}) if busiest_device else {}
    iostat_key = nested_get(summary, ["collector_analysis", "iostat", "key_metrics"], {})
    perf_unsupported = nested_get(summary, ["collector_analysis", "perf_stat", "unsupported_events"], [])
    return {
        "scenario": summary["scenario"],
        "run_dir": str(run_dir),
        "requests_total": summary["requests_total"],
        "requests_ok": summary["requests_ok"],
        "requests_failed": summary["requests_failed"],
        "connect_mean_ms": latency["connect"]["mean"],
        "send_mean_ms": latency["send"]["mean"],
        "send_p95_ms": latency["send"]["p95"],
        "send_p99_ms": latency["send"]["p99"],
        "wait_mean_ms": latency["wait"]["mean"],
        "wait_p50_ms": latency["wait"]["p50"],
        "wait_p95_ms": latency["wait"]["p95"],
        "wait_p99_ms": latency["wait"]["p99"],
        "history_mean_ms": latency["history"]["mean"],
        "history_p95_ms": latency["history"]["p95"],
        "history_p99_ms": latency["history"]["p99"],
        "total_mean_ms": latency["total"]["mean"],
        "total_p50_ms": latency["total"]["p50"],
        "total_p95_ms": latency["total"]["p95"],
        "total_p99_ms": latency["total"]["p99"],
        "docker_cpu_percent_mean": metric_summary_mean(docker, ["metric_summaries", "cpu_percent_value"]),
        "docker_mem_percent_mean": metric_summary_mean(docker, ["metric_summaries", "mem_percent_value"]),
        "docker_block_read_bytes_per_s_mean": metric_summary_mean(
            docker,
            ["metric_summaries", "block_read_bytes_per_s"],
        ),
        "docker_block_write_bytes_per_s_mean": metric_summary_mean(
            docker,
            ["metric_summaries", "block_write_bytes_per_s"],
        ),
        "pidstat_cpu_percent_mean": metric_summary_mean(pidstat, ["cpu", "metric_summaries", "pct_cpu"]),
        "pidstat_rss_kib_mean": metric_summary_mean(pidstat, ["memory", "metric_summaries", "rss_kib"]),
        "pidstat_kb_wr_per_s_mean": metric_summary_mean(pidstat, ["io", "metric_summaries", "kb_wr_per_s"]),
        "pidstat_iodelay_mean": metric_summary_mean(pidstat, ["io", "metric_summaries", "iodelay"]),
        "pidstat_cswch_per_s_mean": metric_summary_mean(
            pidstat,
            ["context_switch", "metric_summaries", "cswch_per_s"],
        ),
        "pidstat_nvcswch_per_s_mean": metric_summary_mean(
            pidstat,
            ["context_switch", "metric_summaries", "nvcswch_per_s"],
        ),
        "iostat_busiest_device": busiest_device,
        "iostat_pct_util_mean": metric_summary_mean(
            iostat,
            ["key_metric_summaries", "pct_util"],
            nested_get(iostat_key, ["pct_util", "mean"], metric_mean(device_metrics, ["pct_util"])),
        ),
        "iostat_r_await_mean": metric_summary_mean(
            iostat,
            ["key_metric_summaries", "r_await"],
            nested_get(iostat_key, ["r_await", "mean"], metric_mean(device_metrics, ["r_await"])),
        ),
        "iostat_w_await_mean": metric_summary_mean(
            iostat,
            ["key_metric_summaries", "w_await"],
            nested_get(iostat_key, ["w_await", "mean"], metric_mean(device_metrics, ["w_await"])),
        ),
        "iostat_f_await_mean": metric_summary_mean(
            iostat,
            ["key_metric_summaries", "f_await"],
            nested_get(iostat_key, ["f_await", "mean"], metric_mean(device_metrics, ["f_await"])),
        ),
        "iostat_aqu_sz_mean": metric_summary_mean(
            iostat,
            ["key_metric_summaries", "aqu_sz"],
            nested_get(iostat_key, ["aqu_sz", "mean"], metric_mean(device_metrics, ["aqu_sz"])),
        ),
        "iostat_wkb_s_mean": metric_summary_mean(
            iostat,
            ["key_metric_summaries", "wkb_s"],
            nested_get(iostat_key, ["wkb_s", "mean"], metric_mean(device_metrics, ["wkb_s"])),
        ),
        "vmstat_interrupts_per_s_mean": metric_summary_mean(vmstat, ["key_metric_summaries", "interrupts_per_s"]),
        "vmstat_context_switches_per_s_mean": metric_summary_mean(
            vmstat,
            ["key_metric_summaries", "context_switches_per_s"],
        ),
        "vmstat_run_queue_mean": metric_summary_mean(vmstat, ["key_metric_summaries", "run_queue"]),
        "npu_utilization_mean": metric_summary_mean(npu_smi, ["key_metric_summaries", "npu_utilization_pct"]),
        "npu_hbm_usage_mean": metric_summary_mean(npu_smi, ["key_metric_summaries", "hbm_usage_rate_pct"]),
        "npu_aicore_usage_mean": metric_summary_mean(npu_smi, ["key_metric_summaries", "aicore_usage_rate_pct"]),
        "npu_aivector_usage_mean": metric_summary_mean(npu_smi, ["key_metric_summaries", "aivector_usage_rate_pct"]),
        "npu_aicpu_usage_mean": metric_summary_mean(npu_smi, ["key_metric_summaries", "aicpu_usage_rate_pct"]),
        "npu_ctrlcpu_usage_mean": metric_summary_mean(npu_smi, ["key_metric_summaries", "ctrlcpu_usage_rate_pct"]),
        "perf_cache_misses_mean": metric_summary_mean(perf_stat, ["key_metric_summaries", "cache_misses"]),
        "perf_context_switches_mean": metric_summary_mean(
            perf_stat,
            ["key_metric_summaries", "context_switches"],
        ),
        "perf_cpu_migrations_mean": metric_summary_mean(perf_stat, ["key_metric_summaries", "cpu_migrations"]),
        "perf_page_faults_mean": metric_summary_mean(perf_stat, ["key_metric_summaries", "page_faults"]),
        "perf_unsupported_events": ", ".join(perf_unsupported) if perf_unsupported else "",
        "strace_events_per_s_peak": time_series_peak_value(strace, ["time_series", "events_per_s"]),
        "strace_events_per_s_peak_t_sec": time_series_peak_t_sec(strace, ["time_series", "events_per_s"]),
        "strace_duration_ms_per_s_peak": time_series_peak_value(strace, ["time_series", "duration_ms_per_s"]),
        "strace_duration_ms_per_s_peak_t_sec": time_series_peak_t_sec(strace, ["time_series", "duration_ms_per_s"]),
        "strace_top_syscall": nested_get(strace, ["top_by_total_duration_sec", 0, "syscall"], ""),
        "strace_top_syscall_total_duration_sec": nested_get(
            strace,
            ["top_by_total_duration_sec", 0, "total_duration_sec"],
        ),
        "node_fs_async_mean_ms": metric_summary_mean(
            node_trace,
            ["key_metric_summaries", "fs_async_duration_ms"],
        ),
        "node_fs_callback_mean_ms": metric_summary_mean(
            node_trace,
            ["key_metric_summaries", "fs_callback_duration_ms"],
        ),
        "node_promise_callback_mean_ms": metric_summary_mean(
            node_trace,
            ["key_metric_summaries", "promise_callback_duration_ms"],
        ),
        "node_event_loop_immediate_mean_ms": metric_summary_mean(
            node_trace,
            ["key_metric_summaries", "event_loop_immediate_duration_ms"],
        ),
        "node_event_loop_timers_mean_ms": metric_summary_mean(
            node_trace,
            ["key_metric_summaries", "event_loop_timers_duration_ms"],
        ),
        "node_fs_async_count": nested_get(node_trace, ["key_counts", "fs_async_count"]),
        "node_fs_callback_count": nested_get(node_trace, ["key_counts", "fs_callback_count"]),
        "node_promise_callback_count": nested_get(node_trace, ["key_counts", "promise_callback_count"]),
        "node_top_fs_path": nested_get(node_trace, ["path_hotspots", "top_by_count", 0, "path"], ""),
        "node_top_fs_path_count": nested_get(node_trace, ["path_hotspots", "top_by_count", 0, "count"]),
        "gateway_bootstrap_load_mean_ms": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "bootstrap_load"],
        ),
        "gateway_skills_mean_ms": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "skills"],
        ),
        "gateway_context_bundle_mean_ms": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "context_bundle"],
        ),
        "gateway_execution_admission_wait_mean_ms": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "execution_admission_wait"],
        ),
        "gateway_reply_dispatch_queue_wait_mean_ms": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "reply_dispatch_queue_wait"],
        ),
        "gateway_reply_dispatch_queue_hold_mean_ms": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "reply_dispatch_queue_hold"],
        ),
        "gateway_reply_dispatch_pending_mean": metric_summary_mean(
            gateway_runtime,
            ["key_metric_summaries", "reply_dispatch_pending"],
        ),
        "node_sessions_lock_total_ms": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_lock", "total_duration_ms"],
        ),
        "node_sessions_lock_count": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_lock", "count"],
        ),
        "node_sessions_dir_enum_total_ms": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_dir_enum", "total_duration_ms"],
        ),
        "node_sessions_dir_enum_count": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_dir_enum", "count"],
        ),
        "node_sessions_json_total_ms": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_json", "total_duration_ms"],
        ),
        "node_sessions_json_count": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_json", "count"],
        ),
        "node_sessions_tmp_total_ms": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_tmp", "total_duration_ms"],
        ),
        "node_sessions_tmp_count": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "sessions_tmp", "count"],
        ),
        "node_bootstrap_files_total_ms": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "bootstrap_files", "total_duration_ms"],
        ),
        "node_bootstrap_files_count": nested_get(
            node_trace,
            ["path_hotspots", "focus_groups", "bootstrap_files", "count"],
        ),
    }


def build_peak_profile_row(summary: dict[str, Any]) -> dict[str, Any]:
    collector = nested_get(summary, ["collector_analysis"], {})
    return {
        "scenario": summary["scenario"],
        "docker_cpu_peak": time_series_peak_value(collector, ["docker_stats", "time_series", "cpu_percent_value"]),
        "docker_cpu_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["docker_stats", "time_series", "cpu_percent_value"],
        ),
        "docker_mem_peak": time_series_peak_value(collector, ["docker_stats", "time_series", "mem_percent_value"]),
        "docker_mem_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["docker_stats", "time_series", "mem_percent_value"],
        ),
        "pidstat_cpu_peak": time_series_peak_value(collector, ["pidstat", "sections", "cpu", "time_series", "pct_cpu"]),
        "pidstat_cpu_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["pidstat", "sections", "cpu", "time_series", "pct_cpu"],
        ),
        "pidstat_rss_peak": time_series_peak_value(
            collector,
            ["pidstat", "sections", "memory", "time_series", "rss_kib"],
        ),
        "pidstat_rss_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["pidstat", "sections", "memory", "time_series", "rss_kib"],
        ),
        "iostat_pct_util_peak": time_series_peak_value(collector, ["iostat", "key_time_series", "pct_util"]),
        "iostat_pct_util_peak_t_sec": time_series_peak_t_sec(collector, ["iostat", "key_time_series", "pct_util"]),
        "iostat_w_await_peak": time_series_peak_value(collector, ["iostat", "key_time_series", "w_await"]),
        "iostat_w_await_peak_t_sec": time_series_peak_t_sec(collector, ["iostat", "key_time_series", "w_await"]),
        "vmstat_interrupts_peak": time_series_peak_value(collector, ["vmstat", "key_time_series", "interrupts_per_s"]),
        "vmstat_interrupts_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["vmstat", "key_time_series", "interrupts_per_s"],
        ),
        "vmstat_context_switches_peak": time_series_peak_value(
            collector,
            ["vmstat", "key_time_series", "context_switches_per_s"],
        ),
        "vmstat_context_switches_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["vmstat", "key_time_series", "context_switches_per_s"],
        ),
        "npu_utilization_peak": time_series_peak_value(
            collector,
            ["npu_smi", "key_time_series", "npu_utilization_pct"],
        ),
        "npu_utilization_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["npu_smi", "key_time_series", "npu_utilization_pct"],
        ),
        "npu_hbm_usage_peak": time_series_peak_value(
            collector,
            ["npu_smi", "key_time_series", "hbm_usage_rate_pct"],
        ),
        "npu_hbm_usage_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["npu_smi", "key_time_series", "hbm_usage_rate_pct"],
        ),
        "perf_context_switches_peak": time_series_peak_value(
            collector,
            ["perf_stat", "key_time_series", "context_switches"],
        ),
        "perf_context_switches_peak_t_sec": time_series_peak_t_sec(
            collector,
            ["perf_stat", "key_time_series", "context_switches"],
        ),
    }


def build_strace_top_table(summary: dict[str, Any], *, top_n: int = 5) -> pd.DataFrame | None:
    strace = nested_get(summary, ["collector_analysis", "strace"], {})
    top_items = nested_get(strace, ["top_by_total_duration_sec"], [])
    if not isinstance(top_items, list) or not top_items:
        return None
    rows: list[dict[str, Any]] = []
    for item in top_items[:top_n]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "syscall": item.get("syscall", ""),
                "count": item.get("count"),
                "total_duration_sec": item.get("total_duration_sec"),
            }
        )
    if not rows:
        return None
    return pd.DataFrame(rows)


def build_strace_key_syscalls_row(summary: dict[str, Any], *, run_dir: Path) -> dict[str, Any]:
    strace = nested_get(summary, ["collector_analysis", "strace"], {})
    syscalls = nested_get(strace, ["syscalls"], {})
    keys = ["openat", "statx", "newfstatat", "pread64", "clone", "sched_yield", "futex", "read", "write"]

    row: dict[str, Any] = {
        "scenario": summary["scenario"],
        "run_dir": str(run_dir),
    }
    for key in keys:
        item = syscalls.get(key, {}) if isinstance(syscalls, dict) else {}
        duration_ms = item.get("duration_ms", {}) if isinstance(item, dict) else {}
        duration_sec = item.get("duration_sec", {}) if isinstance(item, dict) else {}
        mean_sec = duration_sec.get("mean") if isinstance(duration_sec, dict) else None
        count = item.get("count") if isinstance(item, dict) else None
        total_sec = None
        if isinstance(mean_sec, (int, float)) and isinstance(count, (int, float)):
            total_sec = float(mean_sec) * float(count)
        row[f"{key}_count"] = count
        row[f"{key}_total_sec"] = total_sec
        row[f"{key}_mean_ms"] = duration_ms.get("mean") if isinstance(duration_ms, dict) else None
    return row


def estimate_makespan_sec(summary: dict[str, Any]) -> float | None:
    started_at = summary.get("started_at")
    finished_at = summary.get("finished_at")
    if isinstance(started_at, str) and isinstance(finished_at, str):
        try:
            started = pd.to_datetime(started_at, utc=True)
            finished = pd.to_datetime(finished_at, utc=True)
            duration = (finished - started).total_seconds()
            if duration > 0:
                return float(duration)
        except Exception:
            pass

    requests_total = summary.get("requests_total")
    total_mean_ms = nested_get(summary, ["latency_ms", "total", "mean"])
    if not isinstance(requests_total, (int, float)) or not isinstance(total_mean_ms, (int, float)):
        return None
    return (float(requests_total) * float(total_mean_ms)) / 1000.0


def enrich_strace_normalized_metrics(df: pd.DataFrame, summaries: dict[str, dict[str, Any]]) -> pd.DataFrame:
    enriched = df.copy()
    syscall_prefixes = ["futex", "statx", "openat"]
    for scenario in enriched.index:
        summary = summaries.get(str(scenario), {})
        requests_total = summary.get("requests_total")
        wall_sec = estimate_makespan_sec(summary)
        for prefix in syscall_prefixes:
            total_col = f"{prefix}_total_sec"
            total_value = enriched.at[scenario, total_col] if total_col in enriched.columns else None
            per_request = None
            per_wall_sec = None
            if isinstance(total_value, (int, float)) and isinstance(requests_total, (int, float)) and float(requests_total) > 0:
                per_request = float(total_value) / float(requests_total)
            if isinstance(total_value, (int, float)) and isinstance(wall_sec, (int, float)) and float(wall_sec) > 0:
                per_wall_sec = float(total_value) / float(wall_sec)
            enriched.at[scenario, f"{prefix}_total_sec_per_request"] = per_request
            enriched.at[scenario, f"{prefix}_total_sec_per_wall_sec"] = per_wall_sec
        enriched.at[scenario, "estimated_makespan_sec"] = wall_sec
    return enriched


def build_strace_mean_duration_df(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "openat_mean_ms",
        "statx_mean_ms",
        "newfstatat_mean_ms",
        "pread64_mean_ms",
        "clone_mean_ms",
        "sched_yield_mean_ms",
        "futex_mean_ms",
        "read_mean_ms",
        "write_mean_ms",
    ]
    labels = {
        "openat_mean_ms": "openat",
        "statx_mean_ms": "statx",
        "newfstatat_mean_ms": "newfstatat",
        "pread64_mean_ms": "pread64",
        "clone_mean_ms": "clone",
        "sched_yield_mean_ms": "sched_yield",
        "futex_mean_ms": "futex",
        "read_mean_ms": "read",
        "write_mean_ms": "write",
    }
    available = [column for column in columns if column in df.columns]
    mean_df = df[available].rename(columns=labels)
    return mean_df.T


def build_runtime_category_row(summary: dict[str, Any], *, run_dir: Path) -> dict[str, Any]:
    perf_record = nested_get(summary, ["collector_analysis", "perf_record", "runtime_samples"], {})
    categories = nested_get(perf_record, ["categories"], {})
    keys = [
        "fs_worker_exec",
        "fs_callback",
        "event_loop_poll",
        "microtask",
        "futex_sync",
        "worker_message",
        "json_parse",
        "libuv_worker_other",
        "gateway_main_other",
        "v8_worker",
        "other",
    ]
    row: dict[str, Any] = {
        "scenario": summary["scenario"],
        "run_dir": str(run_dir),
        "sample_count": nested_get(perf_record, ["sample_count"]),
    }
    for key in keys:
        row[f"{key}_count"] = nested_get(categories, [key, "count"])
        row[f"{key}_pct"] = nested_get(categories, [key, "pct"])
    return row


def build_runtime_category_pct_df(df: pd.DataFrame) -> pd.DataFrame:
    pct_columns = [column for column in df.columns if column.endswith("_pct")]
    labels = {column: column[:-4] for column in pct_columns}
    return df[pct_columns].rename(columns=labels).T


def build_node_runtime_table(profile_df: pd.DataFrame) -> pd.DataFrame:
    return profile_df[
        [
            "node_fs_async_mean_ms",
            "node_fs_callback_mean_ms",
            "node_promise_callback_mean_ms",
            "node_event_loop_immediate_mean_ms",
            "node_event_loop_timers_mean_ms",
            "node_fs_async_count",
            "node_fs_callback_count",
            "node_promise_callback_count",
        ]
    ].rename(
        columns={
            "node_fs_async_mean_ms": "fs_async_mean_ms",
            "node_fs_callback_mean_ms": "fs_callback_mean_ms",
            "node_promise_callback_mean_ms": "promise_callback_mean_ms",
            "node_event_loop_immediate_mean_ms": "event_loop_immediate_mean_ms",
            "node_event_loop_timers_mean_ms": "event_loop_timers_mean_ms",
            "node_fs_async_count": "fs_async_count",
            "node_fs_callback_count": "fs_callback_count",
            "node_promise_callback_count": "promise_callback_count",
        }
    )


def build_node_runtime_mean_duration_df(df: pd.DataFrame) -> pd.DataFrame:
    columns = {
        "node_fs_async_mean_ms": "fs_async",
        "node_fs_callback_mean_ms": "fs_callback",
        "node_promise_callback_mean_ms": "promise_callback",
        "node_event_loop_immediate_mean_ms": "event_loop_immediate",
        "node_event_loop_timers_mean_ms": "event_loop_timers",
    }
    available = [column for column in columns if column in df.columns]
    return df[available].rename(columns=columns).T


def build_node_trace_top_paths_table(summary: dict[str, Any], *, top_n: int = 5) -> pd.DataFrame | None:
    top_paths = nested_get(summary, ["collector_analysis", "node_trace", "path_hotspots", "top_by_count"], [])
    if not isinstance(top_paths, list) or not top_paths:
        return None
    rows: list[dict[str, Any]] = []
    for item in top_paths[:top_n]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "path": item.get("path", ""),
                "count": item.get("count"),
                "total_duration_ms": item.get("total_duration_ms"),
            }
        )
    if not rows:
        return None
    return pd.DataFrame(rows)


def build_node_trace_path_categories_table(summary: dict[str, Any]) -> pd.DataFrame | None:
    categories = nested_get(summary, ["collector_analysis", "node_trace", "path_hotspots", "categories"], {})
    if not isinstance(categories, dict) or not categories:
        return None
    rows: list[dict[str, Any]] = []
    for category, payload in categories.items():
        if not isinstance(payload, dict):
            continue
        rows.append(
            {
                "category": category,
                "count": payload.get("count"),
                "total_duration_ms": payload.get("total_duration_ms"),
            }
        )
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values(by="count", ascending=False)


def build_gateway_runtime_table(profile_df: pd.DataFrame) -> pd.DataFrame:
    return profile_df[
        [
            "gateway_bootstrap_load_mean_ms",
            "gateway_skills_mean_ms",
            "gateway_context_bundle_mean_ms",
            "gateway_execution_admission_wait_mean_ms",
            "gateway_reply_dispatch_queue_wait_mean_ms",
            "gateway_reply_dispatch_queue_hold_mean_ms",
            "gateway_reply_dispatch_pending_mean",
        ]
    ].rename(
        columns={
            "gateway_bootstrap_load_mean_ms": "bootstrap_load_mean_ms",
            "gateway_skills_mean_ms": "skills_mean_ms",
            "gateway_context_bundle_mean_ms": "context_bundle_mean_ms",
            "gateway_execution_admission_wait_mean_ms": "execution_admission_wait_mean_ms",
            "gateway_reply_dispatch_queue_wait_mean_ms": "reply_dispatch_queue_wait_mean_ms",
            "gateway_reply_dispatch_queue_hold_mean_ms": "reply_dispatch_queue_hold_mean_ms",
            "gateway_reply_dispatch_pending_mean": "reply_dispatch_pending_mean",
        }
    )


def build_node_focus_groups_table(profile_df: pd.DataFrame) -> pd.DataFrame:
    return profile_df[
        [
            "node_sessions_lock_total_ms",
            "node_sessions_lock_count",
            "node_sessions_dir_enum_total_ms",
            "node_sessions_dir_enum_count",
            "node_sessions_json_total_ms",
            "node_sessions_json_count",
            "node_sessions_tmp_total_ms",
            "node_sessions_tmp_count",
            "node_bootstrap_files_total_ms",
            "node_bootstrap_files_count",
        ]
    ].rename(
        columns={
            "node_sessions_lock_total_ms": "sessions_lock_total_ms",
            "node_sessions_lock_count": "sessions_lock_count",
            "node_sessions_dir_enum_total_ms": "sessions_dir_enum_total_ms",
            "node_sessions_dir_enum_count": "sessions_dir_enum_count",
            "node_sessions_json_total_ms": "sessions_json_total_ms",
            "node_sessions_json_count": "sessions_json_count",
            "node_sessions_tmp_total_ms": "sessions_tmp_total_ms",
            "node_sessions_tmp_count": "sessions_tmp_count",
            "node_bootstrap_files_total_ms": "bootstrap_files_total_ms",
            "node_bootstrap_files_count": "bootstrap_files_count",
        }
    )


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)


def has_dataframe_data(df: pd.DataFrame | None) -> bool:
    if not isinstance(df, pd.DataFrame) or df.empty or len(df.columns) == 0:
        return False
    numeric_df = df.select_dtypes(include=["number"])
    return not numeric_df.empty and len(numeric_df.columns) > 0


def plot_dataframe(df: pd.DataFrame, title: str, ylabel: str, output_path: Path) -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required to render figures")
    if not has_dataframe_data(df):
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    df.select_dtypes(include=["number"]).plot(kind="bar", ax=ax, rot=0, title=title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_time_series_panels(
    *,
    panel_specs: list[dict[str, Any]],
    label_a: str,
    label_b: str,
    title: str,
    output_path: Path,
) -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required to render figures")
    usable_specs = [spec for spec in panel_specs if spec.get("left") or spec.get("right")]
    if not usable_specs:
        return
    fig, axes = plt.subplots(
        len(usable_specs),
        1,
        sharex=True,
        figsize=(14, max(4.0, 3.4 * len(usable_specs))),
        constrained_layout=True,
    )
    if len(usable_specs) == 1:
        axes = [axes]
    for ax, spec in zip(axes, usable_specs):
        left_points = spec.get("left", [])
        right_points = spec.get("right", [])
        render_mode = str(spec.get("render_mode", "line"))
        if left_points:
            if render_mode == "scatter":
                ax.scatter(
                    [t for t, _ in left_points],
                    [v for _, v in left_points],
                    s=10,
                    alpha=0.65,
                    label=label_a,
                )
            else:
                ax.plot(
                    [t for t, _ in left_points],
                    [v for _, v in left_points],
                    linewidth=1.4,
                    marker="o",
                    markersize=2.8,
                    label=label_a,
                )
        if right_points:
            if render_mode == "scatter":
                ax.scatter(
                    [t for t, _ in right_points],
                    [v for _, v in right_points],
                    s=10,
                    alpha=0.65,
                    marker="x",
                    label=label_b,
                )
            else:
                ax.plot(
                    [t for t, _ in right_points],
                    [v for _, v in right_points],
                    linewidth=1.4,
                    marker="o",
                    markersize=2.8,
                    linestyle="--",
                    label=label_b,
                )
        ax.set_ylabel(str(spec.get("ylabel", "")))
        ax.set_title(str(spec.get("subtitle", "")))
        ax.grid(True, alpha=0.25)
        ax.legend()
    axes[-1].set_xlabel("Time (s)")
    axes[0].set_title(title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_latency_timeline(
    csv_path_a: Path,
    csv_path_b: Path,
    label_a: str,
    label_b: str,
    output_path: Path,
) -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required to render figures")
    points_a = load_points(csv_path_a, only_success=False)
    points_b = load_points(csv_path_b, only_success=False)
    if not points_a:
        raise ValueError(f"No usable latency rows found in {csv_path_a}")
    if not points_b:
        raise ValueError(f"No usable latency rows found in {csv_path_b}")

    t0_a = points_a[0].started_at
    t0_b = points_b[0].started_at
    x_a = [(point.started_at - t0_a).total_seconds() for point in points_a]
    x_b = [(point.started_at - t0_b).total_seconds() for point in points_b]

    fig, axes = plt.subplots(
        len(LATENCY_COLUMNS),
        1,
        sharex=True,
        figsize=(14, 10),
        constrained_layout=True,
    )
    if len(LATENCY_COLUMNS) == 1:
        axes = [axes]

    for ax, (column, label) in zip(axes, LATENCY_COLUMNS):
        y_a = [point.values.get(column) for point in points_a]
        y_b = [point.values.get(column) for point in points_b]
        ax.plot(x_a, y_a, marker="o", markersize=3, linewidth=1.2, label=label_a)
        ax.plot(
            x_b,
            y_b,
            marker="o",
            markersize=3,
            linewidth=1.2,
            linestyle="--",
            label=label_b,
        )
        ax.set_ylabel(f"{label}\n(ms)")
        ax.grid(True, alpha=0.25)
        ax.legend()

    axes[-1].set_xlabel("Time (s)")
    axes[0].set_title(f"Latency timeline Comparison: {label_a} vs {label_b}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_csv_float(value: Any) -> float | None:
    raw_value = str(value).strip()
    if not raw_value:
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def parse_csv_int(value: Any) -> int | None:
    raw_value = str(value).strip()
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def parse_iso_datetime(value: Any) -> datetime | None:
    raw_value = str(value).strip()
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def load_actual_request_timeline_points(csv_path: Path) -> list[tuple[float, float]]:
    rows: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            started_at = parse_iso_datetime(row.get("started_at"))
            if started_at is None:
                continue

            total_latency_ms = parse_csv_float(row.get("total_latency_ms"))
            if total_latency_ms is None:
                continue

            rows.append(
                {
                    "started_at": started_at,
                    "finished_at": parse_iso_datetime(row.get("finished_at")),
                    "worker_id": parse_csv_int(row.get("worker_id")),
                    "request_index": parse_csv_int(row.get("request_index")),
                    "connect_latency_ms": parse_csv_float(row.get("connect_latency_ms")) or 0.0,
                    "total_latency_ms": total_latency_ms,
                }
            )

    rows.sort(key=lambda row: row["started_at"])
    first_request_started_at = rows[0]["started_at"] if rows else None
    if first_request_started_at is None:
        return []
    seen_workers: set[int] = set()
    point_rows: list[tuple[datetime, float]] = []

    for row in rows:
        worker_id = row["worker_id"]
        request_index = row["request_index"]
        include_connect = False
        if worker_id is not None:
            if worker_id not in seen_workers:
                seen_workers.add(worker_id)
                include_connect = True
        elif request_index == 0:
            include_connect = True

        actual_latency_ms = float(row["total_latency_ms"])
        if include_connect:
            actual_latency_ms += float(row["connect_latency_ms"])

        point_at = row["finished_at"] or row["started_at"]
        point_rows.append((point_at, actual_latency_ms))

    point_rows.sort(key=lambda item: item[0])
    return [
        ((point_at - first_request_started_at).total_seconds(), actual_latency_ms)
        for point_at, actual_latency_ms in point_rows
    ]


def compute_run_timing_metrics(summary: dict[str, Any], csv_path: Path) -> dict[str, Any]:
    run_started_at = parse_iso_datetime(summary.get("started_at"))
    run_finished_at = parse_iso_datetime(summary.get("finished_at"))
    run_wall_clock_sec = None
    if run_started_at is not None and run_finished_at is not None:
        run_wall_clock_sec = (run_finished_at - run_started_at).total_seconds()

    request_started_at: datetime | None = None
    request_finished_at: datetime | None = None
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            started_at = parse_iso_datetime(row.get("started_at"))
            finished_at = parse_iso_datetime(row.get("finished_at"))
            if started_at is not None and (request_started_at is None or started_at < request_started_at):
                request_started_at = started_at
            if finished_at is not None and (request_finished_at is None or finished_at > request_finished_at):
                request_finished_at = finished_at

    request_window_sec = None
    if request_started_at is not None and request_finished_at is not None:
        request_window_sec = (request_finished_at - request_started_at).total_seconds()

    return {
        "run_started_at": run_started_at.isoformat() if run_started_at is not None else None,
        "run_finished_at": run_finished_at.isoformat() if run_finished_at is not None else None,
        "run_wall_clock_sec": run_wall_clock_sec,
        "first_request_started_at": request_started_at.isoformat() if request_started_at is not None else None,
        "last_request_finished_at": request_finished_at.isoformat() if request_finished_at is not None else None,
        "request_window_sec": request_window_sec,
    }


def build_run_timing_row(summary: dict[str, Any], run_dir: Path, *, scenario_label: str | None = None) -> dict[str, Any]:
    row = {
        "scenario": scenario_label or summary["scenario"],
        "run_dir": str(run_dir),
    }
    row.update(compute_run_timing_metrics(summary, run_dir / "latency.csv"))
    return row


def plot_actual_request_timeline(
    *,
    run_specs: list[dict[str, Any]],
    title: str,
    output_path: Path,
) -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required to render figures")

    line_styles = ["-", "--", "-.", ":"]
    markers = ["o", "s", "^", "D", "x", "P", "*"]
    has_points = False
    fig, ax = plt.subplots(figsize=(14, 5.5), constrained_layout=True)

    for index, spec in enumerate(run_specs):
        points = load_actual_request_timeline_points(Path(spec["csv_path"]))
        if not points:
            continue
        has_points = True
        ax.plot(
            [x for x, _ in points],
            [y for _, y in points],
            linewidth=1.2,
            marker=markers[index % len(markers)],
            markersize=2.8,
            linestyle=line_styles[index % len(line_styles)],
            alpha=0.85,
            label=str(spec["label"]),
        )

    if not has_points:
        plt.close(fig)
        return

    ax.set_xlabel("Elapsed wall-clock time since first request start (s)")
    ax.set_ylabel("Per-request actual elapsed (ms)")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def dataframe_to_markdown(df: pd.DataFrame, digits: int = 3) -> str:
    formatted = df.copy()
    for column in formatted.columns:
        formatted[column] = formatted[column].map(format_scalar)
    headers = ["scenario", *formatted.columns.tolist()]
    rows = []
    for index, row in formatted.iterrows():
        rows.append([str(index), *[str(row[column]) for column in formatted.columns]])
    all_rows = [headers, ["---"] * len(headers), *rows]
    return "\n".join("| " + " | ".join(row) + " |" for row in all_rows)


def build_pair_outputs(
    *,
    out_root: Path,
    res_root: Path,
    left_name: str,
    right_name: str,
    render_figures: bool,
) -> dict[str, Any]:
    left_run_dir = find_latest_run_dir(out_root, left_name)
    right_run_dir = find_latest_run_dir(out_root, right_name)
    left_summary = load_summary(left_run_dir)
    right_summary = load_summary(right_run_dir)

    pair_slug = safe_slug(f"{left_name}__vs__{right_name}")
    pair_dir = res_root / pair_slug
    if pair_dir.exists():
        if render_figures:
            shutil.rmtree(pair_dir)
        else:
            shutil.rmtree(pair_dir / "tables", ignore_errors=True)
            (pair_dir / "summary.md").unlink(missing_ok=True)
    pair_dir.mkdir(parents=True, exist_ok=True)

    profile_df = pd.DataFrame(
        [
            build_resource_profile_row(left_summary, left_run_dir),
            build_resource_profile_row(right_summary, right_run_dir),
        ]
    ).set_index("scenario")
    save_dataframe(profile_df, pair_dir / "tables" / "resource_profile.csv")
    run_timing_df = pd.DataFrame(
        [
            build_run_timing_row(left_summary, left_run_dir, scenario_label=left_name),
            build_run_timing_row(right_summary, right_run_dir, scenario_label=right_name),
        ]
    ).set_index("scenario")
    save_dataframe(run_timing_df, pair_dir / "tables" / "run_timing.csv")
    peak_df = pd.DataFrame(
        [
            build_peak_profile_row(left_summary),
            build_peak_profile_row(right_summary),
        ]
    ).set_index("scenario")
    save_dataframe(peak_df, pair_dir / "tables" / "timeline_peaks.csv")
    strace_key_syscalls_df = pd.DataFrame(
        [
            build_strace_key_syscalls_row(left_summary, run_dir=left_run_dir),
            build_strace_key_syscalls_row(right_summary, run_dir=right_run_dir),
        ]
    ).set_index("scenario")
    strace_key_syscalls_df = enrich_strace_normalized_metrics(
        strace_key_syscalls_df,
        {
            left_summary["scenario"]: left_summary,
            right_summary["scenario"]: right_summary,
        },
    )
    save_dataframe(strace_key_syscalls_df, pair_dir / "tables" / "strace_key_syscalls.csv")
    strace_mean_duration_df = build_strace_mean_duration_df(strace_key_syscalls_df)
    save_dataframe(strace_mean_duration_df, pair_dir / "tables" / "strace_mean_duration_ms.csv")
    runtime_category_df = pd.DataFrame(
        [
            build_runtime_category_row(left_summary, run_dir=left_run_dir),
            build_runtime_category_row(right_summary, run_dir=right_run_dir),
        ]
    ).set_index("scenario")
    save_dataframe(runtime_category_df, pair_dir / "tables" / "runtime_category_samples.csv")
    runtime_category_pct_df = build_runtime_category_pct_df(runtime_category_df)
    save_dataframe(runtime_category_pct_df, pair_dir / "tables" / "runtime_category_pct.csv")
    gateway_runtime_df = build_gateway_runtime_table(profile_df)
    save_dataframe(gateway_runtime_df, pair_dir / "tables" / "gateway_runtime_metrics.csv")
    node_focus_groups_df = build_node_focus_groups_table(profile_df)
    save_dataframe(node_focus_groups_df, pair_dir / "tables" / "node_focus_groups.csv")
    node_runtime_df = build_node_runtime_table(profile_df)
    if has_dataframe_data(node_runtime_df):
        save_dataframe(node_runtime_df, pair_dir / "tables" / "node_runtime_metrics.csv")
    node_runtime_mean_duration_df = build_node_runtime_mean_duration_df(profile_df)
    if has_dataframe_data(node_runtime_mean_duration_df):
        save_dataframe(node_runtime_mean_duration_df, pair_dir / "tables" / "node_runtime_mean_duration_ms.csv")
    node_focus_groups_duration_df = node_focus_groups_df[
        [
            "sessions_lock_total_ms",
            "sessions_dir_enum_total_ms",
            "sessions_json_total_ms",
            "sessions_tmp_total_ms",
            "bootstrap_files_total_ms",
        ]
    ].rename(
        columns={
            "sessions_lock_total_ms": "sessions_lock",
            "sessions_dir_enum_total_ms": "sessions_dir_enum",
            "sessions_json_total_ms": "sessions_json",
            "sessions_tmp_total_ms": "sessions_tmp",
            "bootstrap_files_total_ms": "bootstrap_files",
        }
    ).T
    save_dataframe(node_focus_groups_duration_df, pair_dir / "tables" / "node_focus_group_duration_ms.csv")

    latency_overview_df = profile_df[
        ["total_mean_ms", "total_p50_ms", "total_p95_ms", "total_p99_ms"]
    ].rename(
        columns={
            "total_mean_ms": "total_mean",
            "total_p50_ms": "total_p50",
            "total_p95_ms": "total_p95",
            "total_p99_ms": "total_p99",
        }
    )
    phase_df = profile_df[
        ["connect_mean_ms", "send_mean_ms", "wait_mean_ms", "history_mean_ms", "total_mean_ms"]
    ].rename(
        columns={
            "connect_mean_ms": "connect",
            "send_mean_ms": "send",
            "wait_mean_ms": "wait",
            "history_mean_ms": "history",
            "total_mean_ms": "total",
        }
    )
    tail_df = profile_df[
        [
            "send_p95_ms",
            "send_p99_ms",
            "wait_p50_ms",
            "wait_p95_ms",
            "wait_p99_ms",
            "history_p95_ms",
            "history_p99_ms",
            "total_p95_ms",
            "total_p99_ms",
        ]
    ].rename(
        columns={
            "send_p95_ms": "send_p95",
            "send_p99_ms": "send_p99",
            "wait_p50_ms": "wait_p50",
            "wait_p95_ms": "wait_p95",
            "wait_p99_ms": "wait_p99",
            "history_p95_ms": "history_p95",
            "history_p99_ms": "history_p99",
            "total_p95_ms": "total_p95",
            "total_p99_ms": "total_p99",
        }
    )
    container_df = profile_df[
        [
            "docker_cpu_percent_mean",
            "docker_mem_percent_mean",
            "docker_block_read_bytes_per_s_mean",
            "docker_block_write_bytes_per_s_mean",
        ]
    ].rename(
        columns={
            "docker_cpu_percent_mean": "cpu_percent",
            "docker_mem_percent_mean": "mem_percent",
            "docker_block_read_bytes_per_s_mean": "block_read_bytes_per_s",
            "docker_block_write_bytes_per_s_mean": "block_write_bytes_per_s",
        }
    )
    container_cpu_mem_df = container_df[["cpu_percent", "mem_percent"]]
    process_df = profile_df[
        [
            "pidstat_cpu_percent_mean",
            "pidstat_rss_kib_mean",
            "pidstat_kb_wr_per_s_mean",
            "pidstat_iodelay_mean",
            "pidstat_cswch_per_s_mean",
            "pidstat_nvcswch_per_s_mean",
        ]
    ].rename(
        columns={
            "pidstat_cpu_percent_mean": "cpu_percent",
            "pidstat_rss_kib_mean": "rss_kib",
            "pidstat_kb_wr_per_s_mean": "kb_wr_per_s",
            "pidstat_iodelay_mean": "iodelay",
            "pidstat_cswch_per_s_mean": "cswch_per_s",
            "pidstat_nvcswch_per_s_mean": "nvcswch_per_s",
        }
    )
    npu_df = profile_df[
        [
            "npu_utilization_mean",
            "npu_hbm_usage_mean",
            "npu_aicore_usage_mean",
            "npu_aivector_usage_mean",
            "npu_aicpu_usage_mean",
            "npu_ctrlcpu_usage_mean",
        ]
    ].rename(
        columns={
            "npu_utilization_mean": "utilization_pct",
            "npu_hbm_usage_mean": "hbm_usage_pct",
            "npu_aicore_usage_mean": "aicore_usage_pct",
            "npu_aivector_usage_mean": "aivector_usage_pct",
            "npu_aicpu_usage_mean": "aicpu_usage_pct",
            "npu_ctrlcpu_usage_mean": "ctrlcpu_usage_pct",
        }
    )
    phase_table_df = phase_df
    tail_table_df = tail_df
    disk_df = profile_df[
        [
            "iostat_busiest_device",
            "iostat_pct_util_mean",
            "iostat_r_await_mean",
            "iostat_w_await_mean",
            "iostat_f_await_mean",
            "iostat_aqu_sz_mean",
            "iostat_wkb_s_mean",
        ]
    ].rename(
        columns={
            "iostat_busiest_device": "busiest_device",
            "iostat_pct_util_mean": "pct_util",
            "iostat_r_await_mean": "r_await",
            "iostat_w_await_mean": "w_await",
            "iostat_f_await_mean": "f_await",
            "iostat_aqu_sz_mean": "aqu_sz",
            "iostat_wkb_s_mean": "wkb_s",
        }
    )
    system_df = profile_df[
        [
            "vmstat_interrupts_per_s_mean",
            "vmstat_context_switches_per_s_mean",
            "vmstat_run_queue_mean",
            "perf_cache_misses_mean",
            "perf_context_switches_mean",
            "perf_cpu_migrations_mean",
            "perf_page_faults_mean",
            "perf_unsupported_events",
            "strace_events_per_s_peak",
            "strace_duration_ms_per_s_peak",
            "strace_top_syscall",
            "strace_top_syscall_total_duration_sec",
        ]
    ].rename(
        columns={
            "vmstat_interrupts_per_s_mean": "interrupts_per_s",
            "vmstat_context_switches_per_s_mean": "system_context_switches_per_s",
            "vmstat_run_queue_mean": "run_queue",
            "perf_cache_misses_mean": "perf_cache_misses",
            "perf_context_switches_mean": "perf_context_switches",
            "perf_cpu_migrations_mean": "perf_cpu_migrations",
            "perf_page_faults_mean": "perf_page_faults",
            "perf_unsupported_events": "perf_unsupported_events",
            "strace_events_per_s_peak": "strace_events_per_s_peak",
            "strace_duration_ms_per_s_peak": "strace_duration_ms_per_s_peak",
            "strace_top_syscall": "strace_top_syscall",
            "strace_top_syscall_total_duration_sec": "strace_top_syscall_total_duration_sec",
        }
    )
    peak_table_df = peak_df

    table_map = {
        "latency_overview": latency_overview_df,
        "run_timing": run_timing_df,
        "latency_phase_means": phase_df,
        "latency_tail": tail_df,
        "container_metrics": container_df,
        "process_metrics": process_df,
        "npu_metrics": npu_df,
        "disk_metrics": disk_df,
        "system_metrics": system_df,
        "timeline_peaks": peak_table_df,
        "strace_key_syscalls": strace_key_syscalls_df,
        "gateway_runtime_metrics": gateway_runtime_df,
        "node_focus_groups": node_focus_groups_df,
        "node_runtime_metrics": node_runtime_df,
        "node_runtime_mean_duration_ms": node_runtime_mean_duration_df,
        "runtime_category_samples": runtime_category_df,
        "runtime_category_pct": runtime_category_pct_df,
    }
    for name, df in table_map.items():
        save_dataframe(df, pair_dir / "tables" / f"{name}.csv")

    left_strace_top_df = build_strace_top_table(left_summary)
    right_strace_top_df = build_strace_top_table(right_summary)
    left_node_paths_df = build_node_trace_top_paths_table(left_summary)
    right_node_paths_df = build_node_trace_top_paths_table(right_summary)
    left_node_categories_df = build_node_trace_path_categories_table(left_summary)
    right_node_categories_df = build_node_trace_path_categories_table(right_summary)
    if left_strace_top_df is not None:
        save_dataframe(left_strace_top_df, pair_dir / "tables" / f"{safe_slug(left_name)}_strace_top_syscalls.csv")
    if right_strace_top_df is not None:
        save_dataframe(right_strace_top_df, pair_dir / "tables" / f"{safe_slug(right_name)}_strace_top_syscalls.csv")
    if left_node_paths_df is not None:
        save_dataframe(left_node_paths_df, pair_dir / "tables" / f"{safe_slug(left_name)}_node_trace_top_paths.csv")
    if right_node_paths_df is not None:
        save_dataframe(right_node_paths_df, pair_dir / "tables" / f"{safe_slug(right_name)}_node_trace_top_paths.csv")
    if left_node_categories_df is not None:
        save_dataframe(left_node_categories_df, pair_dir / "tables" / f"{safe_slug(left_name)}_node_trace_path_categories.csv")
    if right_node_categories_df is not None:
        save_dataframe(right_node_categories_df, pair_dir / "tables" / f"{safe_slug(right_name)}_node_trace_path_categories.csv")

    if render_figures:
        plt.style.use("seaborn-v0_8-whitegrid")
        plot_dataframe(
            latency_overview_df,
            "End-to-End Latency",
            "milliseconds",
            pair_dir / "figures" / "latency_overview.png",
        )
        plot_dataframe(
            phase_df,
            "Mean Latency by Phase",
            "milliseconds",
            pair_dir / "figures" / "latency_phase_means.png",
        )
        plot_dataframe(
            tail_df,
            "Tail Latency",
            "milliseconds",
            pair_dir / "figures" / "latency_tail.png",
        )
        plot_dataframe(
            container_cpu_mem_df,
            "Container CPU and Memory",
            "mean value",
            pair_dir / "figures" / "container_cpu_mem.png",
        )
        plot_latency_timeline(
            left_run_dir / "latency.csv",
            right_run_dir / "latency.csv",
            label_a=left_name,
            label_b=right_name,
            output_path=pair_dir / "figures" / "latency_timeline.png",
        )
        plot_actual_request_timeline(
            run_specs=[
                {
                    "label": left_name,
                    "csv_path": left_run_dir / "latency.csv",
                },
                {
                    "label": right_name,
                    "csv_path": right_run_dir / "latency.csv",
                },
            ],
            title="Actual Request Timeline (Wall Clock, Total + First Connect)",
            output_path=pair_dir / "figures" / "actual_request_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "Container CPU Percent",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "docker_stats", "time_series", "cpu_percent_value"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "docker_stats", "time_series", "cpu_percent_value"]),
                },
                {
                    "subtitle": "Process CPU Percent",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "pidstat", "sections", "cpu", "time_series", "pct_cpu"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "pidstat", "sections", "cpu", "time_series", "pct_cpu"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="CPU Load Timeline",
            output_path=pair_dir / "figures" / "cpu_load_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "Container Memory Percent",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "docker_stats", "time_series", "mem_percent_value"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "docker_stats", "time_series", "mem_percent_value"]),
                },
                {
                    "subtitle": "Process RSS",
                    "ylabel": "KiB",
                    "left": time_series_points(left_summary, ["collector_analysis", "pidstat", "sections", "memory", "time_series", "rss_kib"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "pidstat", "sections", "memory", "time_series", "rss_kib"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="Memory Load Timeline",
            output_path=pair_dir / "figures" / "mem_load_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "Container Block Write Throughput",
                    "ylabel": "bytes/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "docker_stats", "time_series", "block_write_bytes_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "docker_stats", "time_series", "block_write_bytes_per_s"]),
                },
                {
                    "subtitle": "Disk Utilization (Busiest Device)",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "iostat", "key_time_series", "pct_util"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "iostat", "key_time_series", "pct_util"]),
                },
                {
                    "subtitle": "Disk Write Await (Busiest Device)",
                    "ylabel": "ms",
                    "left": time_series_points(left_summary, ["collector_analysis", "iostat", "key_time_series", "w_await"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "iostat", "key_time_series", "w_await"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="I/O Load Timeline",
            output_path=pair_dir / "figures" / "io_load_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "Interrupts per Second",
                    "ylabel": "interrupts/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "vmstat", "key_time_series", "interrupts_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "vmstat", "key_time_series", "interrupts_per_s"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="Interrupt Timeline",
            output_path=pair_dir / "figures" / "interrupts_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "NPU Utilization (Avg 16 Chips)",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "npu_smi", "key_time_series", "npu_utilization_pct"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "npu_smi", "key_time_series", "npu_utilization_pct"]),
                },
                {
                    "subtitle": "HBM Usage Rate (Avg 16 Chips)",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "npu_smi", "key_time_series", "hbm_usage_rate_pct"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "npu_smi", "key_time_series", "hbm_usage_rate_pct"]),
                },
                {
                    "subtitle": "AICore Usage Rate (Avg 16 Chips)",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "npu_smi", "key_time_series", "aicore_usage_rate_pct"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "npu_smi", "key_time_series", "aicore_usage_rate_pct"]),
                },
                {
                    "subtitle": "CtrlCPU Usage Rate (Avg 16 Chips)",
                    "ylabel": "percent",
                    "left": time_series_points(left_summary, ["collector_analysis", "npu_smi", "key_time_series", "ctrlcpu_usage_rate_pct"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "npu_smi", "key_time_series", "ctrlcpu_usage_rate_pct"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="NPU Load Timeline",
            output_path=pair_dir / "figures" / "npu_load_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "VM Context Switches",
                    "ylabel": "switches/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "vmstat", "key_time_series", "context_switches_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "vmstat", "key_time_series", "context_switches_per_s"]),
                },
                {
                    "subtitle": "Process Voluntary Context Switches",
                    "ylabel": "switches/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "pidstat", "sections", "context_switch", "time_series", "cswch_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "pidstat", "sections", "context_switch", "time_series", "cswch_per_s"]),
                },
                {
                    "subtitle": "perf context-switches",
                    "ylabel": "events/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "perf_stat", "key_time_series", "context_switches"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "perf_stat", "key_time_series", "context_switches"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="Context Switch Timeline",
            output_path=pair_dir / "figures" / "context_switch_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "strace Events per Second",
                    "ylabel": "events/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "strace", "time_series", "events_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "strace", "time_series", "events_per_s"]),
                },
                {
                    "subtitle": "strace Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "strace", "time_series", "duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "strace", "time_series", "duration_ms_per_s"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="strace Timeline",
            output_path=pair_dir / "figures" / "strace_timeline.png",
        )
        plot_dataframe(
            strace_mean_duration_df,
            "strace Mean Syscall Duration",
            "milliseconds",
            pair_dir / "figures" / "strace_mean_duration_ms.png",
        )
        plot_dataframe(
            runtime_category_pct_df,
            "perf Runtime Sample Categories",
            "percent of samples",
            pair_dir / "figures" / "runtime_category_pct.png",
        )
        if has_dataframe_data(node_runtime_mean_duration_df):
            plot_dataframe(
                node_runtime_mean_duration_df,
                "Node Runtime Mean Duration",
                "milliseconds",
                pair_dir / "figures" / "node_runtime_mean_duration_ms.png",
            )
        plot_dataframe(
            node_focus_groups_duration_df,
            "Node Focus Group Duration",
            "total duration (ms)",
            pair_dir / "figures" / "node_focus_group_duration_ms.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "Execution Admission Wait",
                    "ylabel": "ms",
                    "left": time_series_points(left_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "execution_admission_wait_ms"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "execution_admission_wait_ms"]),
                },
                {
                    "subtitle": "Bootstrap Load Duration",
                    "ylabel": "ms",
                    "left": time_series_points(left_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "bootstrap_load_duration_ms"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "bootstrap_load_duration_ms"]),
                },
                {
                    "subtitle": "Skills Duration",
                    "ylabel": "ms",
                    "left": time_series_points(left_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "skills_duration_ms"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "skills_duration_ms"]),
                },
                {
                    "subtitle": "Context Bundle Duration",
                    "ylabel": "ms",
                    "left": time_series_points(left_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "context_bundle_duration_ms"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "context_bundle_duration_ms"]),
                },
                {
                    "subtitle": "Reply Dispatch Queue Wait",
                    "ylabel": "ms",
                    "left": time_series_points(left_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "reply_dispatch_queue_wait_ms"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "gateway_runtime_spans", "time_series", "reply_dispatch_queue_wait_ms"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="Gateway Runtime Timeline",
            output_path=pair_dir / "figures" / "gateway_runtime_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "FS Async Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "fs_async_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "fs_async_duration_ms_per_s"]),
                },
                {
                    "subtitle": "FS Callback Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "fs_callback_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "fs_callback_duration_ms_per_s"]),
                },
                {
                    "subtitle": "Promise Callback Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "promise_callback_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "promise_callback_duration_ms_per_s"]),
                },
                {
                    "subtitle": "Event Loop Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "event_loop_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "event_loop_duration_ms_per_s"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="Node Runtime Timeline",
            output_path=pair_dir / "figures" / "node_runtime_timeline.png",
        )
        plot_time_series_panels(
            panel_specs=[
                {
                    "subtitle": "sessions.json.lock Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "sessions_lock_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "sessions_lock_duration_ms_per_s"]),
                },
                {
                    "subtitle": "sessions.json Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "sessions_json_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "sessions_json_duration_ms_per_s"]),
                },
                {
                    "subtitle": "sessions/ Directory Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "sessions_dir_enum_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "sessions_dir_enum_duration_ms_per_s"]),
                },
                {
                    "subtitle": "sessions.json.<tmp> Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "sessions_tmp_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "sessions_tmp_duration_ms_per_s"]),
                },
                {
                    "subtitle": "Bootstrap Files Duration per Second",
                    "ylabel": "ms/sec",
                    "left": time_series_points(left_summary, ["collector_analysis", "node_trace", "time_series", "bootstrap_files_duration_ms_per_s"]),
                    "right": time_series_points(right_summary, ["collector_analysis", "node_trace", "time_series", "bootstrap_files_duration_ms_per_s"]),
                },
            ],
            label_a=left_name,
            label_b=right_name,
            title="Node Focus Timeline",
            output_path=pair_dir / "figures" / "node_focus_timeline.png",
        )

    figure_paths = [
        ("Latency Overview", pair_dir / "figures" / "latency_overview.png"),
        ("Latency Phase Means", pair_dir / "figures" / "latency_phase_means.png"),
        ("Latency Tail", pair_dir / "figures" / "latency_tail.png"),
        ("Container CPU and Memory", pair_dir / "figures" / "container_cpu_mem.png"),
        ("Latency Timeline", pair_dir / "figures" / "latency_timeline.png"),
        ("Actual Request Timeline", pair_dir / "figures" / "actual_request_timeline.png"),
        ("CPU Load Timeline", pair_dir / "figures" / "cpu_load_timeline.png"),
        ("Memory Load Timeline", pair_dir / "figures" / "mem_load_timeline.png"),
        ("I/O Load Timeline", pair_dir / "figures" / "io_load_timeline.png"),
        ("Interrupt Timeline", pair_dir / "figures" / "interrupts_timeline.png"),
        ("NPU Load Timeline", pair_dir / "figures" / "npu_load_timeline.png"),
        ("Context Switch Timeline", pair_dir / "figures" / "context_switch_timeline.png"),
        ("strace Timeline", pair_dir / "figures" / "strace_timeline.png"),
        ("strace Mean Duration", pair_dir / "figures" / "strace_mean_duration_ms.png"),
        ("Gateway Runtime Timeline", pair_dir / "figures" / "gateway_runtime_timeline.png"),
        ("Node Focus Group Duration", pair_dir / "figures" / "node_focus_group_duration_ms.png"),
        ("Node Focus Timeline", pair_dir / "figures" / "node_focus_timeline.png"),
        ("Node Runtime Mean Duration", pair_dir / "figures" / "node_runtime_mean_duration_ms.png"),
        ("Node Runtime Timeline", pair_dir / "figures" / "node_runtime_timeline.png"),
        ("Runtime Category Samples", pair_dir / "figures" / "runtime_category_pct.png"),
    ]
    figure_lines = [f"- ![{label}](figures/{path.name})" for label, path in figure_paths if path.exists()]

    profile_copy = profile_df.copy()
    profile_copy["run_dir"] = profile_copy["run_dir"].map(str)
    pair_markdown = "\n".join(
        [
            f"## `{left_name}` vs `{right_name}`",
            "",
            "**Run Dirs**",
            "",
            dataframe_to_markdown(profile_copy[["run_dir", "requests_total", "requests_ok", "requests_failed"]]),
            "",
            "**Run Timing Table**",
            "",
            dataframe_to_markdown(run_timing_df),
            "",
            "**Figures**",
            "",
            *figure_lines,
            "",
            "**Latency Overview Table**",
            "",
            dataframe_to_markdown(latency_overview_df),
            "",
            "**Mean Latency by Phase Table**",
            "",
            dataframe_to_markdown(phase_table_df),
            "",
            "**Tail Latency Table**",
            "",
            dataframe_to_markdown(tail_table_df),
            "",
            "**Container Metrics Table**",
            "",
            dataframe_to_markdown(container_df),
            "",
            "**Process Metrics Table**",
            "",
            dataframe_to_markdown(process_df),
            "",
            "**NPU Metrics Table**",
            "",
            dataframe_to_markdown(npu_df),
            "",
            "**Disk Metrics Table**",
            "",
            dataframe_to_markdown(disk_df),
            "",
            "**System Metrics Table**",
            "",
            dataframe_to_markdown(system_df),
            "",
            "**Timeline Peaks Table**",
            "",
            dataframe_to_markdown(peak_table_df),
            "",
            "**strace Key Syscalls Table**",
            "",
            dataframe_to_markdown(strace_key_syscalls_df),
            "",
            "**strace Mean Duration Table**",
            "",
            dataframe_to_markdown(strace_mean_duration_df),
            "",
            "**Gateway Runtime Stage Table**",
            "",
            dataframe_to_markdown(gateway_runtime_df),
            "",
            "**Node Focus Groups Table**",
            "",
            dataframe_to_markdown(node_focus_groups_df),
            "",
            "**Runtime Category Samples Table**",
            "",
            dataframe_to_markdown(runtime_category_df),
            "",
            "**Runtime Category Percent Table**",
            "",
            dataframe_to_markdown(runtime_category_pct_df),
            "",
        ]
    )
    if left_strace_top_df is not None:
        pair_markdown += "\n" + "\n".join(
            [
                f"**Top strace Syscalls: `{left_name}`**",
                "",
                dataframe_to_markdown(left_strace_top_df.set_index("syscall")),
                "",
            ]
        )
    if right_strace_top_df is not None:
        pair_markdown += "\n" + "\n".join(
            [
                f"**Top strace Syscalls: `{right_name}`**",
                "",
                dataframe_to_markdown(right_strace_top_df.set_index("syscall")),
                "",
            ]
        )
    if has_dataframe_data(node_runtime_df):
        pair_markdown += "\n" + "\n".join(
            [
                "**Node Runtime Metrics Table**",
                "",
                dataframe_to_markdown(node_runtime_df),
                "",
            ]
        )
    if has_dataframe_data(node_runtime_mean_duration_df):
        pair_markdown += "\n" + "\n".join(
            [
                "**Node Runtime Mean Duration Table**",
                "",
                dataframe_to_markdown(node_runtime_mean_duration_df),
                "",
            ]
        )
    if left_node_paths_df is not None:
        pair_markdown += "\n" + "\n".join(
            [
                f"**Top Node FS Paths: `{left_name}`**",
                "",
                dataframe_to_markdown(left_node_paths_df.set_index("path")),
                "",
            ]
        )
    if right_node_paths_df is not None:
        pair_markdown += "\n" + "\n".join(
            [
                f"**Top Node FS Paths: `{right_name}`**",
                "",
                dataframe_to_markdown(right_node_paths_df.set_index("path")),
                "",
            ]
        )
    if left_node_categories_df is not None:
        pair_markdown += "\n" + "\n".join(
            [
                f"**Node FS Path Categories: `{left_name}`**",
                "",
                dataframe_to_markdown(left_node_categories_df.set_index("category")),
                "",
            ]
        )
    if right_node_categories_df is not None:
        pair_markdown += "\n" + "\n".join(
            [
                f"**Node FS Path Categories: `{right_name}`**",
                "",
                dataframe_to_markdown(right_node_categories_df.set_index("category")),
                "",
            ]
        )
    (pair_dir / "summary.md").write_text(pair_markdown + "\n", encoding="utf-8")

    return {
        "pair_slug": pair_slug,
        "pair_dir": pair_dir,
        "markdown": pair_markdown,
    }


def main() -> int:
    args = parse_args()
    out_root = Path(args.out_root).resolve()
    res_root = Path(args.res_root).resolve()
    res_root.mkdir(parents=True, exist_ok=True)
    render_figures = not args.skip_figures
    if render_figures and plt is None:
        print("matplotlib not found; refreshing markdown/tables only and preserving existing figures", file=sys.stderr)
        render_figures = False

    for left_name, right_name in args.pair:
        result = build_pair_outputs(
            out_root=out_root,
            res_root=res_root,
            left_name=left_name,
            right_name=right_name,
            render_figures=render_figures,
        )
        print(result["pair_dir"] / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
