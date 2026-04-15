from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

import export_pair_report as pair


LINE_STYLES = ["-", "--", "-.", ":"]
MARKERS = ["o", "s", "^", "D", "x", "P", "*"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export comparison charts and tables for one or more scenario triplets.",
    )
    parser.add_argument(
        "--tri",
        action="append",
        nargs=3,
        metavar=("SCENARIO_A", "SCENARIO_B", "SCENARIO_C"),
        required=True,
        help="Three scenario names to compare. May be repeated.",
    )
    parser.add_argument(
        "--labels",
        action="append",
        nargs=3,
        metavar=("LABEL_A", "LABEL_B", "LABEL_C"),
        help="Optional display labels for the three reports. Must be repeated once per --tri when used.",
    )
    parser.add_argument(
        "--out-root",
        default=str(pair.OUT_ROOT),
        help="Benchmark output root directory. Defaults to repo/out.",
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


def build_series(summary_records: list[dict[str, Any]], path: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "label": str(record["display_name"]),
            "points": pair.time_series_points(record["summary"], path),
        }
        for record in summary_records
    ]


def with_scenario_label(label: str, row: dict[str, Any]) -> dict[str, Any]:
    labeled_row = dict(row)
    labeled_row["scenario"] = label
    return labeled_row


def normalize_display_names(
    scenario_names: list[str],
    labels: list[str] | None,
) -> list[str]:
    display_names = list(labels) if labels is not None else list(scenario_names)
    if len(display_names) != 3:
        raise ValueError("display_names must contain exactly 3 items")
    if len(set(display_names)) != len(display_names):
        raise ValueError(f"display labels must be unique within one report: {display_names}")
    return display_names


def plot_time_series_panels_multi(
    *,
    panel_specs: list[dict[str, Any]],
    title: str,
    output_path: Path,
) -> None:
    if pair.plt is None:
        raise RuntimeError("matplotlib is required to render figures")

    usable_specs = [
        spec
        for spec in panel_specs
        if any(series.get("points") for series in spec.get("series", []))
    ]
    if not usable_specs:
        return

    fig, axes = pair.plt.subplots(
        len(usable_specs),
        1,
        sharex=True,
        figsize=(14, max(4.0, 3.4 * len(usable_specs))),
        constrained_layout=True,
    )
    if len(usable_specs) == 1:
        axes = [axes]

    for ax, spec in zip(axes, usable_specs):
        render_mode = str(spec.get("render_mode", "line"))
        for index, series in enumerate(spec.get("series", [])):
            points = series.get("points", [])
            if not points:
                continue
            label = str(series.get("label", f"series-{index + 1}"))
            linestyle = LINE_STYLES[index % len(LINE_STYLES)]
            marker = MARKERS[index % len(MARKERS)]
            if render_mode == "scatter":
                ax.scatter(
                    [t for t, _ in points],
                    [v for _, v in points],
                    s=10,
                    alpha=0.65,
                    marker=marker,
                    label=label,
                )
            else:
                ax.plot(
                    [t for t, _ in points],
                    [v for _, v in points],
                    linewidth=1.4,
                    marker=marker,
                    markersize=2.8,
                    linestyle=linestyle,
                    label=label,
                )
        ax.set_ylabel(str(spec.get("ylabel", "")))
        ax.set_title(str(spec.get("subtitle", "")))
        ax.grid(True, alpha=0.25)
        ax.legend()

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle(title)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    pair.plt.close(fig)


def plot_latency_timeline_multi(
    run_specs: list[dict[str, Any]],
    output_path: Path,
) -> None:
    if pair.plt is None:
        raise RuntimeError("matplotlib is required to render figures")

    loaded_specs: list[dict[str, Any]] = []
    for index, spec in enumerate(run_specs):
        csv_path = Path(spec["csv_path"])
        label = str(spec["label"])
        points = pair.load_points(csv_path, only_success=False)
        if not points:
            raise ValueError(f"No usable latency rows found in {csv_path}")
        t0 = points[0].started_at
        x_values = [(point.started_at - t0).total_seconds() for point in points]
        loaded_specs.append(
            {
                "label": label,
                "points": points,
                "x_values": x_values,
                "linestyle": LINE_STYLES[index % len(LINE_STYLES)],
                "marker": MARKERS[index % len(MARKERS)],
            }
        )

    fig, axes = pair.plt.subplots(
        len(pair.LATENCY_COLUMNS),
        1,
        sharex=True,
        figsize=(14, 10),
        constrained_layout=True,
    )
    if len(pair.LATENCY_COLUMNS) == 1:
        axes = [axes]

    for ax, (column, column_label) in zip(axes, pair.LATENCY_COLUMNS):
        for spec in loaded_specs:
            y_values = [point.values.get(column) for point in spec["points"]]
            ax.plot(
                spec["x_values"],
                y_values,
                marker=spec["marker"],
                markersize=3,
                linewidth=1.2,
                linestyle=spec["linestyle"],
                label=spec["label"],
            )
        ax.set_ylabel(f"{column_label}\n(ms)")
        ax.grid(True, alpha=0.25)
        ax.legend()

    axes[-1].set_xlabel("Time (s)")
    fig.suptitle("Latency Timeline Comparison: " + " vs ".join(spec["label"] for spec in loaded_specs))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    pair.plt.close(fig)


def build_triplet_outputs(
    *,
    out_root: Path,
    res_root: Path,
    scenario_names: list[str],
    display_names: list[str] | None,
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
            }
        )

    tri_slug = pair.safe_slug("__vs__".join(scenario_names))
    tri_dir = res_root / tri_slug
    if tri_dir.exists():
        if render_figures:
            shutil.rmtree(tri_dir)
        else:
            shutil.rmtree(tri_dir / "tables", ignore_errors=True)
            (tri_dir / "summary.md").unlink(missing_ok=True)
    tri_dir.mkdir(parents=True, exist_ok=True)

    profile_df = pd.DataFrame(
        [
            with_scenario_label(
                str(record["display_name"]),
                pair.build_resource_profile_row(record["summary"], record["run_dir"]),
            )
            for record in summary_records
        ]
    ).set_index("scenario")
    pair.save_dataframe(profile_df, tri_dir / "tables" / "resource_profile.csv")
    run_timing_df = pd.DataFrame(
        [
            pair.build_run_timing_row(
                record["summary"],
                record["run_dir"],
                scenario_label=str(record["display_name"]),
            )
            for record in summary_records
        ]
    ).set_index("scenario")
    pair.save_dataframe(run_timing_df, tri_dir / "tables" / "run_timing.csv")

    peak_df = pd.DataFrame(
        [
            with_scenario_label(
                str(record["display_name"]),
                pair.build_peak_profile_row(record["summary"]),
            )
            for record in summary_records
        ]
    ).set_index("scenario")
    pair.save_dataframe(peak_df, tri_dir / "tables" / "timeline_peaks.csv")

    strace_key_syscalls_df = pd.DataFrame(
        [
            with_scenario_label(
                str(record["display_name"]),
                pair.build_strace_key_syscalls_row(
                    record["summary"],
                    run_dir=record["run_dir"],
                ),
            )
            for record in summary_records
        ]
    ).set_index("scenario")
    strace_key_syscalls_df = pair.enrich_strace_normalized_metrics(
        strace_key_syscalls_df,
        {
            str(record["display_name"]): record["summary"]
            for record in summary_records
        },
    )
    pair.save_dataframe(strace_key_syscalls_df, tri_dir / "tables" / "strace_key_syscalls.csv")

    strace_mean_duration_df = pair.build_strace_mean_duration_df(strace_key_syscalls_df)
    pair.save_dataframe(strace_mean_duration_df, tri_dir / "tables" / "strace_mean_duration_ms.csv")

    runtime_category_df = pd.DataFrame(
        [
            with_scenario_label(
                str(record["display_name"]),
                pair.build_runtime_category_row(
                    record["summary"],
                    run_dir=record["run_dir"],
                ),
            )
            for record in summary_records
        ]
    ).set_index("scenario")
    pair.save_dataframe(runtime_category_df, tri_dir / "tables" / "runtime_category_samples.csv")

    runtime_category_pct_df = pair.build_runtime_category_pct_df(runtime_category_df)
    pair.save_dataframe(runtime_category_pct_df, tri_dir / "tables" / "runtime_category_pct.csv")

    gateway_runtime_df = pair.build_gateway_runtime_table(profile_df)
    pair.save_dataframe(gateway_runtime_df, tri_dir / "tables" / "gateway_runtime_metrics.csv")

    node_focus_groups_df = pair.build_node_focus_groups_table(profile_df)
    pair.save_dataframe(node_focus_groups_df, tri_dir / "tables" / "node_focus_groups.csv")

    node_runtime_df = pair.build_node_runtime_table(profile_df)
    if pair.has_dataframe_data(node_runtime_df):
        pair.save_dataframe(node_runtime_df, tri_dir / "tables" / "node_runtime_metrics.csv")

    node_runtime_mean_duration_df = pair.build_node_runtime_mean_duration_df(profile_df)
    if pair.has_dataframe_data(node_runtime_mean_duration_df):
        pair.save_dataframe(
            node_runtime_mean_duration_df,
            tri_dir / "tables" / "node_runtime_mean_duration_ms.csv",
        )

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
    pair.save_dataframe(
        node_focus_groups_duration_df,
        tri_dir / "tables" / "node_focus_group_duration_ms.csv",
    )

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
    for table_name, df in table_map.items():
        pair.save_dataframe(df, tri_dir / "tables" / f"{table_name}.csv")

    scenario_tables: list[dict[str, Any]] = []
    for record in summary_records:
        scenario_name = str(record["name"])
        display_name = str(record["display_name"])
        scenario_slug = pair.safe_slug(scenario_name)
        strace_top_df = pair.build_strace_top_table(record["summary"])
        node_paths_df = pair.build_node_trace_top_paths_table(record["summary"])
        node_categories_df = pair.build_node_trace_path_categories_table(record["summary"])
        if strace_top_df is not None:
            pair.save_dataframe(
                strace_top_df,
                tri_dir / "tables" / f"{scenario_slug}_strace_top_syscalls.csv",
            )
        if node_paths_df is not None:
            pair.save_dataframe(
                node_paths_df,
                tri_dir / "tables" / f"{scenario_slug}_node_trace_top_paths.csv",
            )
        if node_categories_df is not None:
            pair.save_dataframe(
                node_categories_df,
                tri_dir / "tables" / f"{scenario_slug}_node_trace_path_categories.csv",
            )
        scenario_tables.append(
            {
                "name": scenario_name,
                "display_name": display_name,
                "strace_top_df": strace_top_df,
                "node_paths_df": node_paths_df,
                "node_categories_df": node_categories_df,
            }
        )

    if render_figures:
        pair.plt.style.use("seaborn-v0_8-whitegrid")

        pair.plot_dataframe(
            latency_overview_df,
            "End-to-End Latency",
            "milliseconds",
            tri_dir / "figures" / "latency_overview.png",
        )
        pair.plot_dataframe(
            phase_df,
            "Mean Latency by Phase",
            "milliseconds",
            tri_dir / "figures" / "latency_phase_means.png",
        )
        pair.plot_dataframe(
            tail_df,
            "Tail Latency",
            "milliseconds",
            tri_dir / "figures" / "latency_tail.png",
        )
        pair.plot_dataframe(
            container_cpu_mem_df,
            "Container CPU and Memory",
            "mean value",
            tri_dir / "figures" / "container_cpu_mem.png",
        )
        plot_latency_timeline_multi(
            [
                {
                    "label": record["display_name"],
                    "csv_path": record["run_dir"] / "latency.csv",
                }
                for record in summary_records
            ],
            tri_dir / "figures" / "latency_timeline.png",
        )
        pair.plot_actual_request_timeline(
            run_specs=[
                {
                    "label": record["display_name"],
                    "csv_path": record["run_dir"] / "latency.csv",
                }
                for record in summary_records
            ],
            title="Actual Request Timeline (Wall Clock, Total + First Connect)",
            output_path=tri_dir / "figures" / "actual_request_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Container CPU Percent",
                    "ylabel": "percent",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "docker_stats", "time_series", "cpu_percent_value"],
                    ),
                },
                {
                    "subtitle": "Process CPU Percent",
                    "ylabel": "percent",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "pidstat", "sections", "cpu", "time_series", "pct_cpu"],
                    ),
                },
            ],
            title="CPU Load Timeline",
            output_path=tri_dir / "figures" / "cpu_load_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Container Memory Percent",
                    "ylabel": "percent",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "docker_stats", "time_series", "mem_percent_value"],
                    ),
                },
                {
                    "subtitle": "Process RSS",
                    "ylabel": "KiB",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "pidstat", "sections", "memory", "time_series", "rss_kib"],
                    ),
                },
            ],
            title="Memory Load Timeline",
            output_path=tri_dir / "figures" / "mem_load_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Container Block Write Throughput",
                    "ylabel": "bytes/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "docker_stats", "time_series", "block_write_bytes_per_s"],
                    ),
                },
                {
                    "subtitle": "Disk Utilization (Busiest Device)",
                    "ylabel": "percent",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "iostat", "key_time_series", "pct_util"],
                    ),
                },
                {
                    "subtitle": "Disk Write Await (Busiest Device)",
                    "ylabel": "ms",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "iostat", "key_time_series", "w_await"],
                    ),
                },
            ],
            title="I/O Load Timeline",
            output_path=tri_dir / "figures" / "io_load_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Interrupts per Second",
                    "ylabel": "interrupts/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "vmstat", "key_time_series", "interrupts_per_s"],
                    ),
                },
            ],
            title="Interrupt Timeline",
            output_path=tri_dir / "figures" / "interrupts_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "VM Context Switches",
                    "ylabel": "switches/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "vmstat", "key_time_series", "context_switches_per_s"],
                    ),
                },
                {
                    "subtitle": "Process Voluntary Context Switches",
                    "ylabel": "switches/sec",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "pidstat",
                            "sections",
                            "context_switch",
                            "time_series",
                            "cswch_per_s",
                        ],
                    ),
                },
                {
                    "subtitle": "perf context-switches",
                    "ylabel": "events/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "perf_stat", "key_time_series", "context_switches"],
                    ),
                },
            ],
            title="Context Switch Timeline",
            output_path=tri_dir / "figures" / "context_switch_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "strace Events per Second",
                    "ylabel": "events/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "strace", "time_series", "events_per_s"],
                    ),
                },
                {
                    "subtitle": "strace Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "strace", "time_series", "duration_ms_per_s"],
                    ),
                },
            ],
            title="strace Timeline",
            output_path=tri_dir / "figures" / "strace_timeline.png",
        )
        pair.plot_dataframe(
            strace_mean_duration_df,
            "strace Mean Syscall Duration",
            "milliseconds",
            tri_dir / "figures" / "strace_mean_duration_ms.png",
        )
        pair.plot_dataframe(
            runtime_category_pct_df,
            "perf Runtime Sample Categories",
            "percent of samples",
            tri_dir / "figures" / "runtime_category_pct.png",
        )
        if pair.has_dataframe_data(node_runtime_mean_duration_df):
            pair.plot_dataframe(
                node_runtime_mean_duration_df,
                "Node Runtime Mean Duration",
                "milliseconds",
                tri_dir / "figures" / "node_runtime_mean_duration_ms.png",
            )
        pair.plot_dataframe(
            node_focus_groups_duration_df,
            "Node Focus Group Duration",
            "total duration (ms)",
            tri_dir / "figures" / "node_focus_group_duration_ms.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Execution Admission Wait",
                    "ylabel": "ms",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "gateway_runtime_spans",
                            "time_series",
                            "execution_admission_wait_ms",
                        ],
                    ),
                },
                {
                    "subtitle": "Bootstrap Load Duration",
                    "ylabel": "ms",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "gateway_runtime_spans",
                            "time_series",
                            "bootstrap_load_duration_ms",
                        ],
                    ),
                },
                {
                    "subtitle": "Skills Duration",
                    "ylabel": "ms",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "gateway_runtime_spans", "time_series", "skills_duration_ms"],
                    ),
                },
                {
                    "subtitle": "Context Bundle Duration",
                    "ylabel": "ms",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "gateway_runtime_spans",
                            "time_series",
                            "context_bundle_duration_ms",
                        ],
                    ),
                },
                {
                    "subtitle": "Reply Dispatch Queue Wait",
                    "ylabel": "ms",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "gateway_runtime_spans",
                            "time_series",
                            "reply_dispatch_queue_wait_ms",
                        ],
                    ),
                },
            ],
            title="Gateway Runtime Timeline",
            output_path=tri_dir / "figures" / "gateway_runtime_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "FS Async Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "fs_async_duration_ms_per_s"],
                    ),
                },
                {
                    "subtitle": "FS Callback Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "fs_callback_duration_ms_per_s"],
                    ),
                },
                {
                    "subtitle": "Promise Callback Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "node_trace",
                            "time_series",
                            "promise_callback_duration_ms_per_s",
                        ],
                    ),
                },
                {
                    "subtitle": "Event Loop Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "event_loop_duration_ms_per_s"],
                    ),
                },
            ],
            title="Node Runtime Timeline",
            output_path=tri_dir / "figures" / "node_runtime_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "sessions.json.lock Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "sessions_lock_duration_ms_per_s"],
                    ),
                },
                {
                    "subtitle": "sessions.json Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "sessions_json_duration_ms_per_s"],
                    ),
                },
                {
                    "subtitle": "sessions/ Directory Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        [
                            "collector_analysis",
                            "node_trace",
                            "time_series",
                            "sessions_dir_enum_duration_ms_per_s",
                        ],
                    ),
                },
                {
                    "subtitle": "sessions.json.<tmp> Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "sessions_tmp_duration_ms_per_s"],
                    ),
                },
                {
                    "subtitle": "Bootstrap Files Duration per Second",
                    "ylabel": "ms/sec",
                    "series": build_series(
                        summary_records,
                        ["collector_analysis", "node_trace", "time_series", "bootstrap_files_duration_ms_per_s"],
                    ),
                },
            ],
            title="Node Focus Timeline",
            output_path=tri_dir / "figures" / "node_focus_timeline.png",
        )

    figure_paths = [
        ("Latency Overview", tri_dir / "figures" / "latency_overview.png"),
        ("Latency Phase Means", tri_dir / "figures" / "latency_phase_means.png"),
        ("Latency Tail", tri_dir / "figures" / "latency_tail.png"),
        ("Container CPU and Memory", tri_dir / "figures" / "container_cpu_mem.png"),
        ("Latency Timeline", tri_dir / "figures" / "latency_timeline.png"),
        ("Actual Request Timeline", tri_dir / "figures" / "actual_request_timeline.png"),
        ("CPU Load Timeline", tri_dir / "figures" / "cpu_load_timeline.png"),
        ("Memory Load Timeline", tri_dir / "figures" / "mem_load_timeline.png"),
        ("I/O Load Timeline", tri_dir / "figures" / "io_load_timeline.png"),
        ("Interrupt Timeline", tri_dir / "figures" / "interrupts_timeline.png"),
        ("Context Switch Timeline", tri_dir / "figures" / "context_switch_timeline.png"),
        ("strace Timeline", tri_dir / "figures" / "strace_timeline.png"),
        ("strace Mean Duration", tri_dir / "figures" / "strace_mean_duration_ms.png"),
        ("Gateway Runtime Timeline", tri_dir / "figures" / "gateway_runtime_timeline.png"),
        ("Node Focus Group Duration", tri_dir / "figures" / "node_focus_group_duration_ms.png"),
        ("Node Focus Timeline", tri_dir / "figures" / "node_focus_timeline.png"),
        ("Node Runtime Mean Duration", tri_dir / "figures" / "node_runtime_mean_duration_ms.png"),
        ("Node Runtime Timeline", tri_dir / "figures" / "node_runtime_timeline.png"),
        ("Runtime Category Samples", tri_dir / "figures" / "runtime_category_pct.png"),
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
        pair.dataframe_to_markdown(profile_copy[["run_dir", "requests_total", "requests_ok", "requests_failed"]]),
        "",
        "**Run Timing Table**",
        "",
        pair.dataframe_to_markdown(run_timing_df),
        "",
        "**Figures**",
        "",
        *figure_lines,
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
        "**Container Metrics Table**",
        "",
        pair.dataframe_to_markdown(container_df),
        "",
        "**Process Metrics Table**",
        "",
        pair.dataframe_to_markdown(process_df),
        "",
        "**Disk Metrics Table**",
        "",
        pair.dataframe_to_markdown(disk_df),
        "",
        "**System Metrics Table**",
        "",
        pair.dataframe_to_markdown(system_df),
        "",
        "**Timeline Peaks Table**",
        "",
        pair.dataframe_to_markdown(peak_table_df),
        "",
        "**strace Key Syscalls Table**",
        "",
        pair.dataframe_to_markdown(strace_key_syscalls_df),
        "",
        "**strace Mean Duration Table**",
        "",
        pair.dataframe_to_markdown(strace_mean_duration_df),
        "",
        "**Gateway Runtime Stage Table**",
        "",
        pair.dataframe_to_markdown(gateway_runtime_df),
        "",
        "**Node Focus Groups Table**",
        "",
        pair.dataframe_to_markdown(node_focus_groups_df),
        "",
        "**Runtime Category Samples Table**",
        "",
        pair.dataframe_to_markdown(runtime_category_df),
        "",
        "**Runtime Category Percent Table**",
        "",
        pair.dataframe_to_markdown(runtime_category_pct_df),
        "",
    ]
    if pair.has_dataframe_data(node_runtime_df):
        report_lines.extend(
            [
                "**Node Runtime Metrics Table**",
                "",
                pair.dataframe_to_markdown(node_runtime_df),
                "",
            ]
        )
    if pair.has_dataframe_data(node_runtime_mean_duration_df):
        report_lines.extend(
            [
                "**Node Runtime Mean Duration Table**",
                "",
                pair.dataframe_to_markdown(node_runtime_mean_duration_df),
                "",
            ]
        )

    for scenario_table in scenario_tables:
        if scenario_table["strace_top_df"] is not None:
            report_lines.extend(
                [
                    f"**Top strace Syscalls: `{scenario_table['display_name']}`**",
                    "",
                    pair.dataframe_to_markdown(scenario_table["strace_top_df"].set_index("syscall")),
                    "",
                ]
            )
        if scenario_table["node_paths_df"] is not None:
            report_lines.extend(
                [
                    f"**Top Node FS Paths: `{scenario_table['display_name']}`**",
                    "",
                    pair.dataframe_to_markdown(scenario_table["node_paths_df"].set_index("path")),
                    "",
                ]
            )
        if scenario_table["node_categories_df"] is not None:
            report_lines.extend(
                [
                    f"**Node FS Path Categories: `{scenario_table['display_name']}`**",
                    "",
                    pair.dataframe_to_markdown(scenario_table["node_categories_df"].set_index("category")),
                    "",
                ]
            )

    (tri_dir / "summary.md").write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")

    return {
        "tri_slug": tri_slug,
        "tri_dir": tri_dir,
    }


def main() -> int:
    args = parse_args()
    out_root = Path(args.out_root).resolve()
    res_root = Path(args.res_root).resolve()
    res_root.mkdir(parents=True, exist_ok=True)
    label_groups = args.labels or []
    if label_groups and len(label_groups) != len(args.tri):
        print("--labels must be repeated exactly once per --tri when provided", file=sys.stderr)
        return 2
    render_figures = not args.skip_figures
    if render_figures and pair.plt is None:
        print("matplotlib not found; refreshing markdown/tables only and preserving existing figures", file=sys.stderr)
        render_figures = False

    for index, (scenario_a, scenario_b, scenario_c) in enumerate(args.tri):
        try:
            result = build_triplet_outputs(
                out_root=out_root,
                res_root=res_root,
                scenario_names=[scenario_a, scenario_b, scenario_c],
                display_names=label_groups[index] if label_groups else None,
                render_figures=render_figures,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(result["tri_dir"] / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
