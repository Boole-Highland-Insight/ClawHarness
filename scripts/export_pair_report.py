from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "out"
RES_ROOT = REPO_ROOT / "res"


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


def nested_get(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def metric_mean(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    metric = nested_get(data, path, None)
    if isinstance(metric, dict):
        return metric.get("mean", default)
    return default


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
    docker = nested_get(summary, ["collector_analysis", "docker_stats", "metrics"], {})
    pidstat = nested_get(summary, ["collector_analysis", "pidstat", "sections"], {})
    iostat = nested_get(summary, ["collector_analysis", "iostat"], {})
    vmstat = nested_get(summary, ["collector_analysis", "vmstat", "key_metrics"], {})
    perf_stat = nested_get(summary, ["collector_analysis", "perf_stat", "key_metrics"], {})
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
        "docker_cpu_percent_mean": metric_mean(docker, ["cpu_percent_value"]),
        "docker_mem_percent_mean": metric_mean(docker, ["mem_percent_value"]),
        "docker_block_read_bytes_mean": metric_mean(docker, ["block_read_bytes"]),
        "docker_block_write_bytes_mean": metric_mean(docker, ["block_write_bytes"]),
        "pidstat_cpu_percent_mean": metric_mean(pidstat, ["cpu", "metrics", "pct_cpu"]),
        "pidstat_rss_kib_mean": metric_mean(pidstat, ["memory", "metrics", "rss_kib"]),
        "pidstat_kb_wr_per_s_mean": metric_mean(pidstat, ["io", "metrics", "kb_wr_per_s"]),
        "pidstat_iodelay_mean": metric_mean(pidstat, ["io", "metrics", "iodelay"]),
        "pidstat_cswch_per_s_mean": metric_mean(pidstat, ["context_switch", "metrics", "cswch_per_s"]),
        "pidstat_nvcswch_per_s_mean": metric_mean(pidstat, ["context_switch", "metrics", "nvcswch_per_s"]),
        "iostat_busiest_device": busiest_device,
        "iostat_pct_util_mean": nested_get(iostat_key, ["pct_util", "mean"], metric_mean(device_metrics, ["pct_util"])),
        "iostat_r_await_mean": nested_get(iostat_key, ["r_await", "mean"], metric_mean(device_metrics, ["r_await"])),
        "iostat_w_await_mean": nested_get(iostat_key, ["w_await", "mean"], metric_mean(device_metrics, ["w_await"])),
        "iostat_aqu_sz_mean": nested_get(iostat_key, ["aqu_sz", "mean"], metric_mean(device_metrics, ["aqu_sz"])),
        "iostat_wkb_s_mean": nested_get(iostat_key, ["wkb_s", "mean"], metric_mean(device_metrics, ["wkb_s"])),
        "vmstat_interrupts_per_s_mean": nested_get(vmstat, ["interrupts_per_s", "mean"]),
        "vmstat_context_switches_per_s_mean": nested_get(vmstat, ["context_switches_per_s", "mean"]),
        "vmstat_run_queue_mean": nested_get(vmstat, ["run_queue", "mean"]),
        "perf_cache_misses_mean": nested_get(perf_stat, ["cache_misses", "mean"]),
        "perf_context_switches_mean": nested_get(perf_stat, ["context_switches", "mean"]),
        "perf_cpu_migrations_mean": nested_get(perf_stat, ["cpu_migrations", "mean"]),
        "perf_page_faults_mean": nested_get(perf_stat, ["page_faults", "mean"]),
        "perf_unsupported_events": ", ".join(perf_unsupported) if perf_unsupported else "",
    }


def save_dataframe(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path)


def plot_dataframe(df: pd.DataFrame, title: str, ylabel: str, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    df.plot(kind="bar", ax=ax, rot=0, title=title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180)
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
) -> dict[str, Any]:
    left_run_dir = find_latest_run_dir(out_root, left_name)
    right_run_dir = find_latest_run_dir(out_root, right_name)
    left_summary = load_summary(left_run_dir)
    right_summary = load_summary(right_run_dir)

    pair_slug = safe_slug(f"{left_name}__vs__{right_name}")
    pair_dir = res_root / pair_slug
    if pair_dir.exists():
        shutil.rmtree(pair_dir)
    pair_dir.mkdir(parents=True, exist_ok=True)

    profile_df = pd.DataFrame(
        [
            build_resource_profile_row(left_summary, left_run_dir),
            build_resource_profile_row(right_summary, right_run_dir),
        ]
    ).set_index("scenario")
    save_dataframe(profile_df, pair_dir / "tables" / "resource_profile.csv")

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
            "docker_block_read_bytes_mean",
            "docker_block_write_bytes_mean",
        ]
    ].rename(
        columns={
            "docker_cpu_percent_mean": "cpu_percent",
            "docker_mem_percent_mean": "mem_percent",
            "docker_block_read_bytes_mean": "block_read_bytes",
            "docker_block_write_bytes_mean": "block_write_bytes",
        }
    )
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
            "iostat_aqu_sz_mean",
            "iostat_wkb_s_mean",
        ]
    ].rename(
        columns={
            "iostat_busiest_device": "busiest_device",
            "iostat_pct_util_mean": "pct_util",
            "iostat_r_await_mean": "r_await",
            "iostat_w_await_mean": "w_await",
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
        }
    )

    table_map = {
        "latency_overview": latency_overview_df,
        "latency_phase_means": phase_df,
        "latency_tail": tail_df,
        "container_metrics": container_df,
        "process_metrics": process_df,
        "disk_metrics": disk_df,
        "system_metrics": system_df,
    }
    for name, df in table_map.items():
        save_dataframe(df, pair_dir / "tables" / f"{name}.csv")

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
        container_df,
        "Container Metrics",
        "mean value",
        pair_dir / "figures" / "container_metrics.png",
    )
    plot_dataframe(
        process_df,
        "Process Metrics",
        "mean value",
        pair_dir / "figures" / "process_metrics.png",
    )
    numeric_disk_df = disk_df.drop(columns=["busiest_device"])
    plot_dataframe(
        numeric_disk_df,
        "Disk Metrics",
        "mean value",
        pair_dir / "figures" / "disk_metrics.png",
    )
    numeric_system_df = system_df.drop(columns=["perf_unsupported_events"])
    plot_dataframe(
        numeric_system_df,
        "System And Perf Metrics",
        "mean value",
        pair_dir / "figures" / "system_metrics.png",
    )

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
            f"- ![Latency Overview]({pair_slug}/figures/latency_overview.png)",
            f"- ![Latency Phase Means]({pair_slug}/figures/latency_phase_means.png)",
            f"- ![Latency Tail]({pair_slug}/figures/latency_tail.png)",
            f"- ![Container Metrics]({pair_slug}/figures/container_metrics.png)",
            f"- ![Process Metrics]({pair_slug}/figures/process_metrics.png)",
            f"- ![Disk Metrics]({pair_slug}/figures/disk_metrics.png)",
            f"- ![System Metrics]({pair_slug}/figures/system_metrics.png)",
            "",
            "**Latency Overview Table**",
            "",
            dataframe_to_markdown(latency_overview_df),
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
        ]
    )
    (pair_dir / "README.md").write_text(pair_markdown + "\n", encoding="utf-8")

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

    sections: list[str] = [
        "# Benchmark Comparison Report",
        "",
        f"- out root: `{out_root}`",
        f"- res root: `{res_root}`",
        "",
    ]
    for left_name, right_name in args.pair:
        result = build_pair_outputs(
            out_root=out_root,
            res_root=res_root,
            left_name=left_name,
            right_name=right_name,
        )
        sections.append(result["markdown"])

    (res_root / "summary.md").write_text("\n".join(sections).strip() + "\n", encoding="utf-8")
    print(res_root / "summary.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
