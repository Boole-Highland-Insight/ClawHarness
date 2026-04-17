from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

import export_pair_report as pair
import export_tri_sys_report as tri_sys


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
    system_cpu_df = profile_df[
        [
            "benchmark_cpu_percent_mean",
            "benchmark_cpu_usr_percent_mean",
            "benchmark_cpu_system_percent_mean",
            "benchmark_cpu_wait_percent_mean",
        ]
    ].rename(
        columns={
            "benchmark_cpu_percent_mean": "pct_cpu_total",
            "benchmark_cpu_usr_percent_mean": "pct_cpu_usr",
            "benchmark_cpu_system_percent_mean": "pct_cpu_system",
            "benchmark_cpu_wait_percent_mean": "pct_cpu_wait",
        },
    )
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
    token_throughput_df = profile_df[
        [
            "token_rows_with_usage",
            "output_tokens_mean",
            "output_tps_request_mean",
            "output_tps_session_delta_mean",
        ]
    ].rename(
        columns={
            "token_rows_with_usage": "rows_with_usage",
            "output_tokens_mean": "output_tokens_mean",
            "output_tps_request_mean": "output_tps_request_mean",
            "output_tps_session_delta_mean": "output_tps_session_delta_mean",
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
        pair.plt.style.use("seaborn-v0_8-whitegrid")

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
            "Benchmark CPU Metrics",
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
        if tri_sys.dataframe_has_values(token_throughput_df):
            pair.plot_dataframe(
                tri_sys.non_empty_columns(token_throughput_df),
                "Token Throughput Metrics",
                "mean value",
                quad_dir / "figures" / "token_throughput_metrics.png",
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
                    "subtitle": "Benchmark Process CPU Percent (sum across instances)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "cpu", "time_series", "pct_cpu"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "Benchmark User CPU Percent (sum across instances)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "cpu", "time_series", "pct_usr"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "Benchmark System CPU Percent (sum across instances)",
                    "ylabel": "percent",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "cpu", "time_series", "pct_system"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "VM Run Queue (mean across instance collectors)",
                    "ylabel": "processes",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "run_queue"],
                        mode="mean",
                    ),
                },
            ],
            title="System CPU Timeline",
            output_path=quad_dir / "figures" / "system_cpu_timeline.png",
        )
        tri_sys.plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Benchmark RSS Total (sum across instances)",
                    "ylabel": "KiB",
                    "series": tri_sys.build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "memory", "time_series", "rss_kib"],
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
