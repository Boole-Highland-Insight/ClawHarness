from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

import export_pair_report as pair
import export_tri_sys_report as tri_sys


CPU_TIMELINE_TOP_POINTS = 36


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export system-level comparison charts and tables for one or more scenario quartets.",
    )
    parser.add_argument(
        "--quad",
        action="append",
        nargs=4,
        metavar=("SCENARIO_A", "SCENARIO_B", "SCENARIO_C", "SCENARIO_D"),
        required=True,
        help="Four scenario names to compare. May be repeated.",
    )
    parser.add_argument(
        "--labels",
        action="append",
        nargs=4,
        metavar=("LABEL_A", "LABEL_B", "LABEL_C", "LABEL_D"),
        help="Optional display labels for the four reports. Must be repeated once per --quad when used.",
    )
    parser.add_argument(
        "--report-dir-name",
        action="append",
        metavar="DIR_NAME",
        help="Optional output directory name under --res-root. Must be repeated once per --quad when used.",
    )
    parser.add_argument(
        "--out-root",
        default=str(pair.OUT_ROOT),
        help="Benchmark output root directory. Defaults to batch_run.json output_root when available, else repo/out.",
    )
    parser.add_argument(
        "--res-root",
        default=str(pair.RES_ROOT),
        help="Report output root directory. Defaults to repo/res.",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Refresh markdown/tables only and keep any existing figures untouched.",
    )
    return parser.parse_args()


def normalize_display_names(
    scenario_names: list[str],
    labels: list[str] | None,
) -> list[str]:
    display_names = list(labels) if labels is not None else list(scenario_names)
    if len(display_names) != 4:
        raise ValueError("display_names must contain exactly 4 items")
    if len(set(display_names)) != len(display_names):
        raise ValueError(f"display labels must be unique within one report: {display_names}")
    return display_names


def select_top_points(points: list[tuple[float, float]], limit: int = CPU_TIMELINE_TOP_POINTS) -> list[tuple[float, float]]:
    if len(points) <= limit:
        return points
    ranked_points = sorted(points, key=lambda item: (-item[1], item[0]))[:limit]
    return sorted(ranked_points, key=lambda item: item[0])


def reduce_series_to_top_points(
    series_list: list[dict[str, Any]],
    limit: int = CPU_TIMELINE_TOP_POINTS,
) -> list[dict[str, Any]]:
    reduced: list[dict[str, Any]] = []
    for series in series_list:
        reduced.append(
            {
                **series,
                "points": select_top_points(list(series.get("points", [])), limit=limit),
            },
        )
    return reduced


def invert_percent_series(
    series_list: list[dict[str, Any]],
    *,
    max_percent: float = 100.0,
) -> list[dict[str, Any]]:
    transformed: list[dict[str, Any]] = []
    for series in series_list:
        points = []
        for t_sec, value in list(series.get("points", [])):
            points.append((t_sec, max(0.0, max_percent - float(value))))
        transformed.append({**series, "points": points})
    return transformed


def smooth_series_preserve_edges(
    series_list: list[dict[str, Any]],
    *,
    window_radius: int = 4,
) -> list[dict[str, Any]]:
    if window_radius <= 0:
        return series_list

    smoothed: list[dict[str, Any]] = []
    for series in series_list:
        points = list(series.get("points", []))
        if len(points) <= 2:
            smoothed.append(series)
            continue

        values = [float(value) for _, value in points]
        new_points: list[tuple[float, float]] = []
        last_index = len(points) - 1
        for index, (t_sec, value) in enumerate(points):
            if index == 0 or index == last_index:
                new_points.append((t_sec, float(value)))
                continue

            start = max(0, index - window_radius)
            end = min(last_index, index + window_radius)
            window_values = values[start : end + 1]
            new_points.append((t_sec, sum(window_values) / len(window_values)))

        smoothed.append({**series, "points": new_points})
    return smoothed


def load_vmstat_series_from_run(
    run_dir: Path,
    source_field: str,
) -> list[tuple[float, float]]:
    vmstat_summary_path = run_dir / "vmstat.summary.json"
    if not vmstat_summary_path.exists():
        return []
    payload = json.loads(vmstat_summary_path.read_text(encoding="utf-8"))
    return load_vmstat_series_from_payload(payload, source_field)


def load_vmstat_series_from_payload(
    payload: dict[str, Any],
    source_field: str,
) -> list[tuple[float, float]]:
    series = pair.nested_get(payload, ["time_series", source_field, "points"], [])
    if not isinstance(series, list):
        return []

    points: list[tuple[float, float]] = []
    for item in series:
        if not isinstance(item, dict):
            continue
        t_sec = item.get("t_sec")
        value = item.get("value")
        if isinstance(t_sec, (int, float)) and isinstance(value, (int, float)):
            points.append((float(t_sec), float(value)))
    return points


def load_vmstat_series_with_instance_fallback(
    run_dir: Path,
    source_field: str,
) -> list[tuple[float, float]]:
    top_level_points = load_vmstat_series_from_run(run_dir, source_field)
    if top_level_points:
        return top_level_points

    instance_root = run_dir / "instances"
    if not instance_root.exists():
        return []

    instance_payloads: list[dict[str, Any]] = []
    for child in sorted(instance_root.iterdir()):
        vmstat_summary_path = child / "vmstat.summary.json"
        if not vmstat_summary_path.exists():
            continue
        instance_payloads.append(json.loads(vmstat_summary_path.read_text(encoding="utf-8")))

    if not instance_payloads:
        return []

    buckets: dict[float, float] = {}
    counts: dict[float, int] = {}
    for payload in instance_payloads:
        for t_sec, value in load_vmstat_series_from_payload(payload, source_field):
            key = round(t_sec, 6)
            buckets[key] = buckets.get(key, 0.0) + value
            counts[key] = counts.get(key, 0) + 1

    return [
        (t_sec, buckets[t_sec] / counts[t_sec])
        for t_sec in sorted(buckets)
    ]


def build_run_vmstat_series(
    summary_records: list[dict[str, Any]],
    source_field: str,
) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for record in summary_records:
        series.append(
            {
                "label": str(record["display_name"]),
                "points": load_vmstat_series_with_instance_fallback(Path(record["run_dir"]), source_field),
            },
        )
    return series


def build_quartet_outputs(
    *,
    out_root: Path,
    res_root: Path,
    scenario_names: list[str],
    display_names: list[str] | None,
    report_dir_name: str | None,
    render_figures: bool,
) -> dict[str, Any]:
    normalized_display_names = normalize_display_names(scenario_names, display_names)
    summary_records: list[dict[str, Any]] = []
    for scenario_name, display_name in zip(scenario_names, normalized_display_names):
        run_dir = pair.find_latest_run_dir(out_root, scenario_name)
        summary = pair.load_summary(run_dir)
        summary_records.append(
            {
                "name": scenario_name,
                "display_name": display_name,
                "run_dir": run_dir,
                "summary": summary,
            },
        )

    quad_slug = pair.safe_slug("__vs__".join(scenario_names))
    target_dir_name = report_dir_name.strip() if report_dir_name else ""
    quad_dir = res_root / target_dir_name if target_dir_name else res_root / f"{quad_slug}-sys"
    if quad_dir.exists():
        if render_figures:
            shutil.rmtree(quad_dir)
        else:
            shutil.rmtree(quad_dir / "tables", ignore_errors=True)
            (quad_dir / "summary.md").unlink(missing_ok=True)
    quad_dir.mkdir(parents=True, exist_ok=True)

    profile_df = pd.DataFrame(
        [
            tri_sys.with_scenario_label(
                str(record["display_name"]),
                tri_sys.build_system_profile_row(record["summary"], record["run_dir"]),
            )
            for record in summary_records
        ],
    ).set_index("scenario")
    pair.save_dataframe(profile_df, quad_dir / "tables" / "system_resource_profile.csv")

    run_timing_df = pd.DataFrame(
        [
            pair.build_run_timing_row(
                record["summary"],
                record["run_dir"],
                scenario_label=str(record["display_name"]),
            )
            for record in summary_records
        ],
    ).set_index("scenario")
    pair.save_dataframe(run_timing_df, quad_dir / "tables" / "run_timing.csv")

    peak_df = pd.DataFrame(
        [
            tri_sys.with_scenario_label(
                str(record["display_name"]),
                tri_sys.build_system_peak_row(record["summary"]),
            )
            for record in summary_records
        ],
    ).set_index("scenario")
    pair.save_dataframe(peak_df, quad_dir / "tables" / "system_timeline_peaks.csv")

    latency_overview_df = profile_df[
        ["total_mean_ms", "total_p50_ms", "total_p95_ms", "total_p99_ms"]
    ].rename(
        columns={
            "total_mean_ms": "total_mean",
            "total_p50_ms": "total_p50",
            "total_p95_ms": "total_p95",
            "total_p99_ms": "total_p99",
        },
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
        },
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
        },
    )
    system_cpu_df = pd.DataFrame(index=profile_df.index)
    system_cpu_df["pct_cpu_total"] = profile_df["benchmark_cpu_percent_mean"]
    system_cpu_df["pct_cpu_user"] = profile_df["benchmark_cpu_usr_percent_mean"]
    system_cpu_df["pct_cpu_system"] = profile_df["benchmark_cpu_system_percent_mean"]
    system_memory_df = profile_df[["benchmark_rss_kib_mean"]].rename(
        columns={"benchmark_rss_kib_mean": "rss_kib_total"},
    )
    system_disk_df = profile_df[
        [
            "system_busiest_device",
            "system_disk_pct_util_mean",
            "system_disk_r_await_mean",
            "system_disk_w_await_mean",
            "system_disk_aqu_sz_mean",
            "system_disk_wkb_s_mean",
            "benchmark_kb_wr_per_s_mean",
        ]
    ].rename(
        columns={
            "system_busiest_device": "busiest_device",
            "system_disk_pct_util_mean": "pct_util",
            "system_disk_r_await_mean": "r_await",
            "system_disk_w_await_mean": "w_await",
            "system_disk_aqu_sz_mean": "aqu_sz",
            "system_disk_wkb_s_mean": "system_wkb_s",
            "benchmark_kb_wr_per_s_mean": "benchmark_kb_wr_per_s",
        },
    )
    system_activity_df = profile_df[
        [
            "system_interrupts_per_s_mean",
            "system_context_switches_per_s_mean",
            "system_run_queue_mean",
            "system_blocked_processes_mean",
            "benchmark_cswch_per_s_mean",
            "benchmark_nvcswch_per_s_mean",
            "benchmark_iodelay_mean",
        ]
    ].rename(
        columns={
            "system_interrupts_per_s_mean": "interrupts_per_s",
            "system_context_switches_per_s_mean": "system_context_switches_per_s",
            "system_run_queue_mean": "run_queue",
            "system_blocked_processes_mean": "blocked_processes",
            "benchmark_cswch_per_s_mean": "benchmark_cswch_per_s",
            "benchmark_nvcswch_per_s_mean": "benchmark_nvcswch_per_s",
            "benchmark_iodelay_mean": "benchmark_iodelay",
        },
    )
    npu_df = profile_df[
        [
            "npu_utilization_mean",
            "npu_hbm_usage_mean",
            "npu_aicore_usage_mean",
        ]
    ].rename(
        columns={
            "npu_utilization_mean": "utilization_pct",
            "npu_hbm_usage_mean": "hbm_usage_pct",
            "npu_aicore_usage_mean": "aicore_usage_pct",
        },
    )
    token_throughput_df = profile_df[["output_tps_overall"]].rename(
        columns={
            "output_tps_overall": "overall_output_tps",
        },
    )

    table_map = {
        "latency_overview": latency_overview_df,
        "run_timing": run_timing_df,
        "latency_phase_means": phase_df,
        "latency_tail": tail_df,
        "system_cpu_metrics": system_cpu_df,
        "system_memory_metrics": system_memory_df,
        "system_disk_metrics": system_disk_df,
        "system_activity_metrics": system_activity_df,
        "npu_metrics": npu_df,
        "token_throughput_metrics": token_throughput_df,
        "system_timeline_peaks": peak_df,
    }
    for table_name, df in table_map.items():
        pair.save_dataframe(df, quad_dir / "tables" / f"{table_name}.csv")

    if render_figures:
        pair.apply_plot_style("seaborn-v0_8-whitegrid")

        pair.plot_dataframe(
            latency_overview_df,
            "End-to-End Latency",
            "milliseconds",
            quad_dir / "figures" / "latency_overview.png",
        )
        pair.plot_dataframe(
            phase_df,
            "Mean Latency by Phase",
            "milliseconds",
            quad_dir / "figures" / "latency_phase_means.png",
        )
        pair.plot_dataframe(
            tail_df,
            "Tail Latency",
            "milliseconds",
            quad_dir / "figures" / "latency_tail.png",
        )
        pair.plot_dataframe(
            system_cpu_df,
            "Benchmark and System CPU Metrics",
            "mean percent",
            quad_dir / "figures" / "system_cpu_metrics.png",
        )
        pair.plot_dataframe(
            system_memory_df,
            "Benchmark Memory Metrics",
            "mean KiB",
            quad_dir / "figures" / "system_memory_metrics.png",
        )
        pair.plot_dataframe(
            system_disk_df.drop(columns=["busiest_device"]),
            "System Disk Metrics",
            "mean value",
            quad_dir / "figures" / "system_disk_metrics.png",
        )
        pair.plot_dataframe(
            system_activity_df,
            "System Activity Metrics",
            "mean value",
            quad_dir / "figures" / "system_activity_metrics.png",
        )
        pair.plot_average_request_metric_timeline(
            run_specs=[
                {
                    "label": record["display_name"],
                    "csv_path": record["run_dir"] / "latency.csv",
                }
                for record in summary_records
            ],
            title="Total Active-Request Token Throughput",
            output_path=quad_dir / "figures" / "token_throughput_metrics.png",
            ylabel="Total active-request token/s",
            aggregate_mode="sum",
        )
        if tri_sys.dataframe_has_values(npu_df):
            pair.plot_dataframe(
                tri_sys.non_empty_columns(npu_df),
                "NPU Metrics",
                "mean percent",
                quad_dir / "figures" / "npu_metrics.png",
            )
        tri_sys.plot_latency_timeline_multi(
            [
                {
                    "label": record["display_name"],
                    "csv_path": record["run_dir"] / "latency.csv",
                }
                for record in summary_records
            ],
            quad_dir / "figures" / "latency_timeline.png",
        )
        pair.plot_request_gantt_multi(
            run_specs=[
                {
                    "label": record["display_name"],
                    "run_dir": record["run_dir"],
                    "csv_path": record["run_dir"] / "latency.csv",
                }
                for record in summary_records
            ],
            title="Request Gantt Timeline",
            output_path=quad_dir / "figures" / "actual_request_timeline.png",
            show_yaxis_label=False,
        )
        pair.plot_request_aligned_npu_activity(
            run_specs=[
                {
                    "label": record["display_name"],
                    "run_dir": record["run_dir"],
                    "csv_path": record["run_dir"] / "latency.csv",
                }
                for record in summary_records
            ],
            title="AICore Usage vs Request Activity",
            output_path=quad_dir / "figures" / "aicore_request_alignment.png",
        )
        tri_sys.plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "System CPU Total (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": smooth_series_preserve_edges(invert_percent_series(build_run_vmstat_series(
                        summary_records,
                        "id",
                    ))),
                },
                {
                    "subtitle": "System CPU User (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": build_run_vmstat_series(summary_records, "us"),
                },
                {
                    "subtitle": "System CPU System (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": build_run_vmstat_series(summary_records, "sy"),
                },
                {
                    "subtitle": "System CPU iowait (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": build_run_vmstat_series(summary_records, "wa"),
                },
                {
                    "subtitle": "System CPU Idle (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": build_run_vmstat_series(summary_records, "id"),
                },
            ],
            title="System CPU Timeline (Host CPU, Data Smoothed)",
            output_path=quad_dir / "figures" / "system_cpu_timeline.png",
        )
        tri_sys.plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Benchmark / Container Memory Total (sum across instances)",
                    "ylabel": "KiB",
                    "series": tri_sys.build_aggregated_series_with_fallback(
                        summary_records,
                        [
                            (["pidstat", "sections", "memory", "time_series", "rss_kib"], 1.0),
                            (["docker_stats", "time_series", "mem_usage_bytes"], 1.0 / 1024.0),
                        ],
                        mode="sum",
                    ),
                },
            ],
            title="System Memory Timeline",
            output_path=quad_dir / "figures" / "system_memory_timeline.png",
        )
        tri_sys.plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Disk Utilization (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["iostat", "key_time_series", "pct_util"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Disk Write Await (mean across instance collectors)",
                    "ylabel": "ms",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["iostat", "key_time_series", "w_await"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Disk Write Throughput (mean across instance collectors)",
                    "ylabel": "KiB/sec",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["iostat", "key_time_series", "wkb_s"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Benchmark Process Write Throughput (sum across instances)",
                    "ylabel": "KiB/sec",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "io", "time_series", "kb_wr_per_s"],
                        mode="sum",
                    ),
                },
            ],
            title="System I/O Timeline",
            output_path=quad_dir / "figures" / "system_io_timeline.png",
        )
        tri_sys.plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Interrupts per Second",
                    "ylabel": "interrupts/sec",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "interrupts_per_s"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "System Context Switches per Second",
                    "ylabel": "switches/sec",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "context_switches_per_s"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Benchmark Voluntary Context Switches (sum across instances)",
                    "ylabel": "switches/sec",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "context_switch", "time_series", "cswch_per_s"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "Blocked Processes",
                    "ylabel": "processes",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "blocked_processes"],
                        mode="mean",
                    ),
                },
            ],
            title="System Activity Timeline",
            output_path=quad_dir / "figures" / "system_activity_timeline.png",
        )
        tri_sys.plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "NPU Utilization (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["npu_smi", "key_time_series", "npu_utilization_pct"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "AICore Usage Rate (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["npu_smi", "key_time_series", "aicore_usage_rate_pct"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "HBM Usage Rate (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["npu_smi", "key_time_series", "hbm_usage_rate_pct"],
                        mode="mean",
                    ),
                },
            ],
            title="NPU Timeline",
            output_path=quad_dir / "figures" / "npu_timeline.png",
        )

    figure_paths = [
        ("Latency Overview", quad_dir / "figures" / "latency_overview.png"),
        ("Latency Phase Means", quad_dir / "figures" / "latency_phase_means.png"),
        ("Latency Tail", quad_dir / "figures" / "latency_tail.png"),
        ("Latency Timeline", quad_dir / "figures" / "latency_timeline.png"),
        ("Request Gantt Timeline", quad_dir / "figures" / "actual_request_timeline.png"),
        ("AICore vs Request Activity", quad_dir / "figures" / "aicore_request_alignment.png"),
        ("System CPU Metrics", quad_dir / "figures" / "system_cpu_metrics.png"),
        ("System CPU Timeline", quad_dir / "figures" / "system_cpu_timeline.png"),
        ("System Memory Metrics", quad_dir / "figures" / "system_memory_metrics.png"),
        ("System Memory Timeline", quad_dir / "figures" / "system_memory_timeline.png"),
        ("System Disk Metrics", quad_dir / "figures" / "system_disk_metrics.png"),
        ("System I/O Timeline", quad_dir / "figures" / "system_io_timeline.png"),
        ("System Activity Metrics", quad_dir / "figures" / "system_activity_metrics.png"),
        ("System Activity Timeline", quad_dir / "figures" / "system_activity_timeline.png"),
        ("Token Throughput Metrics", quad_dir / "figures" / "token_throughput_metrics.png"),
        ("NPU Metrics", quad_dir / "figures" / "npu_metrics.png"),
        ("NPU Timeline", quad_dir / "figures" / "npu_timeline.png"),
    ]
    figure_lines = [
        f"- ![{label}](figures/{path.name})"
        for label, path in figure_paths
        if path.exists()
    ]

    profile_copy = profile_df.copy()
    profile_copy["run_dir"] = profile_copy["run_dir"].map(str)
    report_lines = [
        "## " + " vs ".join(f"`{display_name}`" for display_name in normalized_display_names),
        "",
        "**Run Dirs**",
        "",
        pair.dataframe_to_markdown(
            profile_copy[["run_dir", "instance_num", "requests_total", "requests_ok", "requests_failed"]]
        ),
        "",
        "**Aggregation Policy**",
        "",
        "- `pidstat` per-process metrics are summed across instances.",
        "- `iostat` and `vmstat` host-wide metrics are averaged across instance collectors.",
        "- This makes multi-instance runs comparable with single-instance runs at the whole-machine level.",
        "",
        "**Figures**",
        "",
        *figure_lines,
        "",
        "**Run Timing Table**",
        "",
        pair.dataframe_to_markdown(run_timing_df),
        "",
        "**Latency Overview Table**",
        "",
        pair.dataframe_to_markdown(latency_overview_df),
        "",
        "**Mean Latency by Phase Table**",
        "",
        pair.dataframe_to_markdown(phase_df),
        "",
        "**Tail Latency Table**",
        "",
        pair.dataframe_to_markdown(tail_df),
        "",
        "**System CPU Table**",
        "",
        pair.dataframe_to_markdown(system_cpu_df),
        "",
        "**System Memory Table**",
        "",
        pair.dataframe_to_markdown(system_memory_df),
        "",
        "**System Disk Table**",
        "",
        pair.dataframe_to_markdown(system_disk_df),
        "",
        "**System Activity Table**",
        "",
        pair.dataframe_to_markdown(system_activity_df),
        "",
        "**Token Throughput Table**",
        "",
        pair.dataframe_to_markdown(token_throughput_df),
        "",
        "**NPU Table**",
        "",
        pair.dataframe_to_markdown(npu_df),
        "",
        "**System Timeline Peaks Table**",
        "",
        pair.dataframe_to_markdown(peak_df),
        "",
    ]
    (quad_dir / "summary.md").write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")

    return {
        "quad_slug": quad_slug,
        "quad_dir": quad_dir,
    }


def main() -> int:
    args = parse_args()
    out_root = Path(args.out_root).resolve()
    res_root = Path(args.res_root).resolve()
    res_root.mkdir(parents=True, exist_ok=True)
    label_groups = args.labels or []
    report_dir_names = args.report_dir_name or []
    if label_groups and len(label_groups) != len(args.quad):
        print("--labels must be repeated exactly once per --quad when provided", file=sys.stderr)
        return 2
    if report_dir_names and len(report_dir_names) != len(args.quad):
        print("--report-dir-name must be repeated exactly once per --quad when provided", file=sys.stderr)
        return 2
    render_figures = not args.skip_figures
    if render_figures and pair.plt is None:
        print("matplotlib not found; refreshing markdown/tables only and preserving existing figures", file=sys.stderr)
        render_figures = False

    for index, scenario_group in enumerate(args.quad):
        try:
            result = build_quartet_outputs(
                out_root=out_root,
                res_root=res_root,
                scenario_names=list(scenario_group),
                display_names=label_groups[index] if label_groups else None,
                report_dir_name=report_dir_names[index] if report_dir_names else None,
                render_figures=render_figures,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(result["quad_dir"] / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
