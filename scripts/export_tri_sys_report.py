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
        description="Export system-level comparison charts and tables for one or more scenario triplets.",
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
    if len(display_names) != 3:
        raise ValueError("display_names must contain exactly 3 items")
    if len(set(display_names)) != len(display_names):
        raise ValueError(f"display labels must be unique within one report: {display_names}")
    return display_names


def with_scenario_label(label: str, row: dict[str, Any]) -> dict[str, Any]:
    labeled_row = dict(row)
    labeled_row["scenario"] = label
    return labeled_row


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
            },
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


def get_instance_analyses(summary: dict[str, Any]) -> list[dict[str, Any]]:
    collector = pair.nested_get(summary, ["collector_analysis"], {})
    if not isinstance(collector, dict):
        return []

    instance_entries = collector.get("instances")
    if isinstance(instance_entries, list):
        analyses = [
            entry.get("analysis")
            for entry in instance_entries
            if isinstance(entry, dict) and isinstance(entry.get("analysis"), dict)
        ]
        if analyses:
            return analyses

    return [collector]


def combine_numeric(values: list[Any], *, mode: str) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    if not numbers:
        return None
    if mode == "sum":
        return sum(numbers)
    if mode == "mean":
        return sum(numbers) / len(numbers)
    raise ValueError(f"unsupported reduction mode: {mode}")


def combine_metric_means(
    analyses: list[dict[str, Any]],
    path: list[str],
    *,
    mode: str,
) -> float | None:
    values = [pair.metric_summary_mean(analysis, path) for analysis in analyses]
    return combine_numeric(values, mode=mode)


def pick_busiest_device(analyses: list[dict[str, Any]]) -> str | None:
    for analysis in analyses:
        iostat = pair.nested_get(analysis, ["iostat"], {})
        if not isinstance(iostat, dict):
            continue
        candidate = (
            pair.nested_get(analysis, ["iostat", "key_metrics", "busiest_device"])
            or iostat.get("busiest_device_by_util_mean")
        )
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def analysis_time_series_points(
    analysis: dict[str, Any],
    path: list[str],
) -> list[tuple[float, float]]:
    entry = pair.nested_get(analysis, path, None)
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


def aggregate_time_series_points(
    analyses: list[dict[str, Any]],
    path: list[str],
    *,
    mode: str,
) -> list[tuple[float, float]]:
    buckets: dict[float, float] = {}
    counts: dict[float, int] = {}

    for analysis in analyses:
        for t_sec, value in analysis_time_series_points(analysis, path):
            key = round(t_sec, 6)
            buckets[key] = buckets.get(key, 0.0) + value
            counts[key] = counts.get(key, 0) + 1

    if not buckets:
        return []

    points: list[tuple[float, float]] = []
    for key in sorted(buckets):
        total_value = buckets[key]
        if mode == "sum":
            points.append((key, total_value))
        elif mode == "mean":
            points.append((key, total_value / counts[key]))
        else:
            raise ValueError(f"unsupported reduction mode: {mode}")
    return points


def build_aggregated_series(
    summary_records: list[dict[str, Any]],
    path: list[str],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for record in summary_records:
        series.append(
            {
                "label": str(record["display_name"]),
                "points": aggregate_time_series_points(
                    get_instance_analyses(record["summary"]),
                    path,
                    mode=mode,
                ),
            },
        )
    return series


def peak_from_points(points: list[tuple[float, float]]) -> tuple[float | None, float | None]:
    if not points:
        return (None, None)
    t_sec, value = max(points, key=lambda item: item[1])
    return (value, t_sec)


def build_system_profile_row(summary: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    analyses = get_instance_analyses(summary)
    latency = summary["latency_ms"]
    return {
        "scenario": summary["scenario"],
        "run_dir": str(run_dir),
        "instance_num": summary.get("instance_num"),
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
        "benchmark_cpu_percent_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "cpu", "metric_summaries", "pct_cpu"],
            mode="sum",
        ),
        "benchmark_cpu_usr_percent_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "cpu", "metric_summaries", "pct_usr"],
            mode="sum",
        ),
        "benchmark_cpu_system_percent_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "cpu", "metric_summaries", "pct_system"],
            mode="sum",
        ),
        "benchmark_cpu_wait_percent_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "cpu", "metric_summaries", "pct_wait"],
            mode="sum",
        ),
        "benchmark_rss_kib_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "memory", "metric_summaries", "rss_kib"],
            mode="sum",
        ),
        "benchmark_kb_wr_per_s_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "io", "metric_summaries", "kb_wr_per_s"],
            mode="sum",
        ),
        "benchmark_iodelay_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "io", "metric_summaries", "iodelay"],
            mode="sum",
        ),
        "benchmark_cswch_per_s_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "context_switch", "metric_summaries", "cswch_per_s"],
            mode="sum",
        ),
        "benchmark_nvcswch_per_s_mean": combine_metric_means(
            analyses,
            ["pidstat", "sections", "context_switch", "metric_summaries", "nvcswch_per_s"],
            mode="sum",
        ),
        "system_busiest_device": pick_busiest_device(analyses),
        "system_disk_pct_util_mean": combine_metric_means(
            analyses,
            ["iostat", "key_metric_summaries", "pct_util"],
            mode="mean",
        ),
        "system_disk_r_await_mean": combine_metric_means(
            analyses,
            ["iostat", "key_metric_summaries", "r_await"],
            mode="mean",
        ),
        "system_disk_w_await_mean": combine_metric_means(
            analyses,
            ["iostat", "key_metric_summaries", "w_await"],
            mode="mean",
        ),
        "system_disk_aqu_sz_mean": combine_metric_means(
            analyses,
            ["iostat", "key_metric_summaries", "aqu_sz"],
            mode="mean",
        ),
        "system_disk_wkb_s_mean": combine_metric_means(
            analyses,
            ["iostat", "key_metric_summaries", "wkb_s"],
            mode="mean",
        ),
        "system_interrupts_per_s_mean": combine_metric_means(
            analyses,
            ["vmstat", "key_metric_summaries", "interrupts_per_s"],
            mode="mean",
        ),
        "system_context_switches_per_s_mean": combine_metric_means(
            analyses,
            ["vmstat", "key_metric_summaries", "context_switches_per_s"],
            mode="mean",
        ),
        "system_run_queue_mean": combine_metric_means(
            analyses,
            ["vmstat", "key_metric_summaries", "run_queue"],
            mode="mean",
        ),
        "system_blocked_processes_mean": combine_metric_means(
            analyses,
            ["vmstat", "key_metric_summaries", "blocked_processes"],
            mode="mean",
        ),
    }


def build_system_peak_row(summary: dict[str, Any]) -> dict[str, Any]:
    analyses = get_instance_analyses(summary)
    benchmark_cpu_peak, benchmark_cpu_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["pidstat", "sections", "cpu", "time_series", "pct_cpu"],
            mode="sum",
        ),
    )
    benchmark_rss_peak, benchmark_rss_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["pidstat", "sections", "memory", "time_series", "rss_kib"],
            mode="sum",
        ),
    )
    system_disk_pct_util_peak, system_disk_pct_util_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["iostat", "key_time_series", "pct_util"],
            mode="mean",
        ),
    )
    system_disk_w_await_peak, system_disk_w_await_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["iostat", "key_time_series", "w_await"],
            mode="mean",
        ),
    )
    system_interrupts_peak, system_interrupts_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["vmstat", "key_time_series", "interrupts_per_s"],
            mode="mean",
        ),
    )
    system_context_switches_peak, system_context_switches_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["vmstat", "key_time_series", "context_switches_per_s"],
            mode="mean",
        ),
    )
    system_run_queue_peak, system_run_queue_peak_t_sec = peak_from_points(
        aggregate_time_series_points(
            analyses,
            ["vmstat", "key_time_series", "run_queue"],
            mode="mean",
        ),
    )
    return {
        "benchmark_cpu_peak": benchmark_cpu_peak,
        "benchmark_cpu_peak_t_sec": benchmark_cpu_peak_t_sec,
        "benchmark_rss_peak_kib": benchmark_rss_peak,
        "benchmark_rss_peak_t_sec": benchmark_rss_peak_t_sec,
        "system_disk_pct_util_peak": system_disk_pct_util_peak,
        "system_disk_pct_util_peak_t_sec": system_disk_pct_util_peak_t_sec,
        "system_disk_w_await_peak": system_disk_w_await_peak,
        "system_disk_w_await_peak_t_sec": system_disk_w_await_peak_t_sec,
        "system_interrupts_peak": system_interrupts_peak,
        "system_interrupts_peak_t_sec": system_interrupts_peak_t_sec,
        "system_context_switches_peak": system_context_switches_peak,
        "system_context_switches_peak_t_sec": system_context_switches_peak_t_sec,
        "system_run_queue_peak": system_run_queue_peak,
        "system_run_queue_peak_t_sec": system_run_queue_peak_t_sec,
    }


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
            },
        )

    tri_slug = pair.safe_slug("__vs__".join(scenario_names))
    tri_dir = res_root / f"{tri_slug}-sys"
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
                build_system_profile_row(record["summary"], record["run_dir"]),
            )
            for record in summary_records
        ],
    ).set_index("scenario")
    pair.save_dataframe(profile_df, tri_dir / "tables" / "system_resource_profile.csv")

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
    pair.save_dataframe(run_timing_df, tri_dir / "tables" / "run_timing.csv")

    peak_df = pd.DataFrame(
        [
            with_scenario_label(
                str(record["display_name"]),
                build_system_peak_row(record["summary"]),
            )
            for record in summary_records
        ],
    ).set_index("scenario")
    pair.save_dataframe(peak_df, tri_dir / "tables" / "system_timeline_peaks.csv")

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

    table_map = {
        "latency_overview": latency_overview_df,
        "run_timing": run_timing_df,
        "latency_phase_means": phase_df,
        "latency_tail": tail_df,
        "system_cpu_metrics": system_cpu_df,
        "system_memory_metrics": system_memory_df,
        "system_disk_metrics": system_disk_df,
        "system_activity_metrics": system_activity_df,
        "system_timeline_peaks": peak_df,
    }
    for table_name, df in table_map.items():
        pair.save_dataframe(df, tri_dir / "tables" / f"{table_name}.csv")

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
            system_cpu_df,
            "Benchmark CPU Metrics",
            "mean percent",
            tri_dir / "figures" / "system_cpu_metrics.png",
        )
        pair.plot_dataframe(
            system_memory_df,
            "Benchmark Memory Metrics",
            "mean KiB",
            tri_dir / "figures" / "system_memory_metrics.png",
        )
        pair.plot_dataframe(
            system_disk_df.drop(columns=["busiest_device"]),
            "System Disk Metrics",
            "mean value",
            tri_dir / "figures" / "system_disk_metrics.png",
        )
        pair.plot_dataframe(
            system_activity_df,
            "System Activity Metrics",
            "mean value",
            tri_dir / "figures" / "system_activity_metrics.png",
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
                    "subtitle": "Benchmark Process CPU Percent (sum across instances)",
                    "ylabel": "percent",
                    "series": build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "cpu", "time_series", "pct_cpu"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "Benchmark User CPU Percent (sum across instances)",
                    "ylabel": "percent",
                    "series": build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "cpu", "time_series", "pct_usr"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "Benchmark System CPU Percent (sum across instances)",
                    "ylabel": "percent",
                    "series": build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "cpu", "time_series", "pct_system"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "VM Run Queue (mean across instance collectors)",
                    "ylabel": "processes",
                    "series": build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "run_queue"],
                        mode="mean",
                    ),
                },
            ],
            title="System CPU Timeline",
            output_path=tri_dir / "figures" / "system_cpu_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Benchmark RSS Total (sum across instances)",
                    "ylabel": "KiB",
                    "series": build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "memory", "time_series", "rss_kib"],
                        mode="sum",
                    ),
                },
            ],
            title="System Memory Timeline",
            output_path=tri_dir / "figures" / "system_memory_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Disk Utilization (mean across instance collectors)",
                    "ylabel": "percent",
                    "series": build_aggregated_series(
                        summary_records,
                        ["iostat", "key_time_series", "pct_util"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Disk Write Await (mean across instance collectors)",
                    "ylabel": "ms",
                    "series": build_aggregated_series(
                        summary_records,
                        ["iostat", "key_time_series", "w_await"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Disk Write Throughput (mean across instance collectors)",
                    "ylabel": "KiB/sec",
                    "series": build_aggregated_series(
                        summary_records,
                        ["iostat", "key_time_series", "wkb_s"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Benchmark Process Write Throughput (sum across instances)",
                    "ylabel": "KiB/sec",
                    "series": build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "io", "time_series", "kb_wr_per_s"],
                        mode="sum",
                    ),
                },
            ],
            title="System I/O Timeline",
            output_path=tri_dir / "figures" / "system_io_timeline.png",
        )
        plot_time_series_panels_multi(
            panel_specs=[
                {
                    "subtitle": "Interrupts per Second",
                    "ylabel": "interrupts/sec",
                    "series": build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "interrupts_per_s"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "System Context Switches per Second",
                    "ylabel": "switches/sec",
                    "series": build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "context_switches_per_s"],
                        mode="mean",
                    ),
                },
                {
                    "subtitle": "Benchmark Voluntary Context Switches (sum across instances)",
                    "ylabel": "switches/sec",
                    "series": build_aggregated_series(
                        summary_records,
                        ["pidstat", "sections", "context_switch", "time_series", "cswch_per_s"],
                        mode="sum",
                    ),
                },
                {
                    "subtitle": "Blocked Processes",
                    "ylabel": "processes",
                    "series": build_aggregated_series(
                        summary_records,
                        ["vmstat", "key_time_series", "blocked_processes"],
                        mode="mean",
                    ),
                },
            ],
            title="System Activity Timeline",
            output_path=tri_dir / "figures" / "system_activity_timeline.png",
        )

    figure_paths = [
        ("Latency Overview", tri_dir / "figures" / "latency_overview.png"),
        ("Latency Phase Means", tri_dir / "figures" / "latency_phase_means.png"),
        ("Latency Tail", tri_dir / "figures" / "latency_tail.png"),
        ("Latency Timeline", tri_dir / "figures" / "latency_timeline.png"),
        ("Actual Request Timeline", tri_dir / "figures" / "actual_request_timeline.png"),
        ("System CPU Metrics", tri_dir / "figures" / "system_cpu_metrics.png"),
        ("System CPU Timeline", tri_dir / "figures" / "system_cpu_timeline.png"),
        ("System Memory Metrics", tri_dir / "figures" / "system_memory_metrics.png"),
        ("System Memory Timeline", tri_dir / "figures" / "system_memory_timeline.png"),
        ("System Disk Metrics", tri_dir / "figures" / "system_disk_metrics.png"),
        ("System I/O Timeline", tri_dir / "figures" / "system_io_timeline.png"),
        ("System Activity Metrics", tri_dir / "figures" / "system_activity_metrics.png"),
        ("System Activity Timeline", tri_dir / "figures" / "system_activity_timeline.png"),
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
        pair.dataframe_to_markdown(profile_copy[["run_dir", "instance_num", "requests_total", "requests_ok", "requests_failed"]]),
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
        "**System Timeline Peaks Table**",
        "",
        pair.dataframe_to_markdown(peak_df),
        "",
    ]
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
