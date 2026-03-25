from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
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

from plot_latency import LATENCY_COLUMNS, load_points


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
    perf_stat = nested_get(summary, ["collector_analysis", "perf_stat"], {})
    strace = nested_get(summary, ["collector_analysis", "strace"], {})
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


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)


def plot_dataframe(df: pd.DataFrame, title: str, ylabel: str, output_path: Path) -> None:
    if plt is None:
        raise RuntimeError("matplotlib is required to render figures")
    fig, ax = plt.subplots(figsize=(10, 5))
    df.plot(kind="bar", ax=ax, rot=0, title=title)
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
        if left_points:
            ax.plot(
                [t for t, _ in left_points],
                [v for _, v in left_points],
                linewidth=1.4,
                marker="o",
                markersize=2.8,
                label=label_a,
            )
        if right_points:
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
    peak_df = pd.DataFrame(
        [
            build_peak_profile_row(left_summary),
            build_peak_profile_row(right_summary),
        ]
    ).set_index("scenario")
    save_dataframe(peak_df, pair_dir / "tables" / "timeline_peaks.csv")

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
        "latency_phase_means": phase_df,
        "latency_tail": tail_df,
        "container_metrics": container_df,
        "process_metrics": process_df,
        "disk_metrics": disk_df,
        "system_metrics": system_df,
        "timeline_peaks": peak_table_df,
    }
    for name, df in table_map.items():
        save_dataframe(df, pair_dir / "tables" / f"{name}.csv")

    left_strace_top_df = build_strace_top_table(left_summary)
    right_strace_top_df = build_strace_top_table(right_summary)
    if left_strace_top_df is not None:
        save_dataframe(left_strace_top_df, pair_dir / "tables" / f"{safe_slug(left_name)}_strace_top_syscalls.csv")
    if right_strace_top_df is not None:
        save_dataframe(right_strace_top_df, pair_dir / "tables" / f"{safe_slug(right_name)}_strace_top_syscalls.csv")

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

    figure_paths = [
        ("Latency Overview", pair_dir / "figures" / "latency_overview.png"),
        ("Latency Phase Means", pair_dir / "figures" / "latency_phase_means.png"),
        ("Latency Tail", pair_dir / "figures" / "latency_tail.png"),
        ("Container CPU and Memory", pair_dir / "figures" / "container_cpu_mem.png"),
        ("Latency Timeline", pair_dir / "figures" / "latency_timeline.png"),
        ("CPU Load Timeline", pair_dir / "figures" / "cpu_load_timeline.png"),
        ("Memory Load Timeline", pair_dir / "figures" / "mem_load_timeline.png"),
        ("I/O Load Timeline", pair_dir / "figures" / "io_load_timeline.png"),
        ("Interrupt Timeline", pair_dir / "figures" / "interrupts_timeline.png"),
        ("Context Switch Timeline", pair_dir / "figures" / "context_switch_timeline.png"),
        ("strace Timeline", pair_dir / "figures" / "strace_timeline.png"),
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
