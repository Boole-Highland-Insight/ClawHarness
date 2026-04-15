from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

out_root = Path("/root/client-harness/out")

def iter_run_dirs() -> list[Path]:
    run_dirs: list[Path] = []
    for summary_path in sorted(out_root.rglob("summary.json")):
        run_dir = summary_path.parent
        try:
            relative_parts = run_dir.relative_to(out_root).parts
        except ValueError:
            continue
        if "instances" in relative_parts:
            continue
        if not (run_dir / "scenario.resolved.json").is_file():
            continue
        run_dirs.append(run_dir)
    return run_dirs


def find_latest_run_dir(scenario_name: str) -> Path:
    candidates = sorted(
        [path for path in iter_run_dirs() if path.name.endswith(f"_{scenario_name}")],
        key=lambda path: path.name,
    )
    if not candidates:
        raise FileNotFoundError(f"No run directory found for scenario: {scenario_name}")
    return candidates[-1]


def load_summary(run_dir: Path) -> dict:
    return json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))


single_100_run_dir = find_latest_run_dir("vps-docker-single-task-00-500-full")
multi_100_run_dir = find_latest_run_dir("vps-docker-multi-task-00-500-full")
single_profile_summary = load_summary(single_100_run_dir)
multi_profile_summary = load_summary(multi_100_run_dir)
# single_profile_summary["scenario"], multi_profile_summary["scenario"]

def nested_get(data: dict, path: list[str], default=None):
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def metric_mean(data: dict, path: list[str], default=None):
    metric = nested_get(data, path, None)
    if isinstance(metric, dict):
        return metric.get("mean", default)
    return default


def metric_summary_mean(data: dict, path: list[str], default=None):
    metric = nested_get(data, path, None)
    if isinstance(metric, dict):
        summary = metric.get("summary")
        if isinstance(summary, dict):
            return summary.get("mean", default)
    return default


def build_resource_profile_row(summary: dict) -> dict:
    latency = summary["latency_ms"]
    docker = nested_get(summary, ["collector_analysis", "docker_stats"], {})
    pidstat = nested_get(summary, ["collector_analysis", "pidstat", "sections"], {})
    iostat = nested_get(summary, ["collector_analysis", "iostat"], {})
    iostat_key = nested_get(summary, ["collector_analysis", "iostat", "key_metrics"], {})
    busiest_device = iostat_key.get("busiest_device") or iostat.get("busiest_device_by_util_mean")
    device_metrics = nested_get(iostat, ["devices", busiest_device, "metrics"], {}) if busiest_device else {}
    return {
        "scenario": summary["scenario"],
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
    }


resource_profile_df = pd.DataFrame([
    build_resource_profile_row(single_profile_summary),
    build_resource_profile_row(multi_profile_summary),
]).set_index("scenario")

plt.style.use("seaborn-v0_8-whitegrid")
fig, axes = plt.subplots(1, 1, figsize=(8, 4))
resource_profile_df[["total_mean_ms", "total_p50_ms", "total_p95_ms", "total_p99_ms"]].plot(
    kind="bar",
    ax=axes,
    rot=0,
    title="Resource Profile End-to-End Latency",
)
axes.set_ylabel("milliseconds")
plt.tight_layout()
plt.show()



resource_phase_df = resource_profile_df[[
    "connect_mean_ms",
    "send_mean_ms",
    "wait_mean_ms",
    "history_mean_ms",
    "total_mean_ms",
]].rename(columns={
    "connect_mean_ms": "connect",
    "send_mean_ms": "send",
    "wait_mean_ms": "wait",
    "history_mean_ms": "history",
    "total_mean_ms": "total",
})
ax = resource_phase_df.plot(kind="bar", figsize=(10, 5), rot=0, title="Resource Profile Mean Latency by Phase")
ax.set_ylabel("milliseconds")
plt.tight_layout()
plt.show()


resource_tail_df = resource_profile_df[["send_p95_ms", "send_p99_ms", "wait_p50_ms", "wait_p95_ms", "wait_p99_ms", "history_p95_ms", "history_p99_ms", "total_p95_ms", "total_p99_ms"]].rename(columns={
    "send_p95_ms": "send_p95",
    "send_p99_ms": "send_p99",
    "wait_p50_ms": "wait_p50",
    "wait_p95_ms": "wait_p95",
    "wait_p99_ms": "wait_p99",
    "history_p95_ms": "history_p95",
    "history_p99_ms": "history_p99",
    "total_p95_ms": "total_p95",
    "total_p99_ms": "total_p99",
})
ax = resource_tail_df.plot(kind="bar", figsize=(10, 5), rot=0, title="Resource Profile Tail Latency P95/P99")
ax.set_ylabel("milliseconds")
plt.tight_layout()
plt.show()


resource_container_df = resource_profile_df[[
    "docker_cpu_percent_mean",
    "docker_mem_percent_mean",
]].rename(columns={
    "docker_cpu_percent_mean": "cpu_percent",
    "docker_mem_percent_mean": "mem_percent",
})
print(resource_container_df.round(3))
ax = resource_container_df.plot(kind="bar", figsize=(10, 5), rot=0, title="Container Metrics")
ax.set_ylabel("mean value")
plt.tight_layout()
plt.show()


resource_container_df = resource_profile_df[[
    "docker_block_read_bytes_per_s_mean",
    "docker_block_write_bytes_per_s_mean",
]].rename(columns={
    "docker_block_read_bytes_per_s_mean": "block_read_bytes_per_s",
    "docker_block_write_bytes_per_s_mean": "block_write_bytes_per_s",
})
print(resource_container_df.round(3))
ax = resource_container_df.plot(kind="bar", figsize=(10, 5), rot=0, title="Container Metrics")
ax.set_ylabel("mean value")
plt.tight_layout()
plt.show()


resource_process_df = resource_profile_df[[
    "pidstat_cpu_percent_mean",
    "pidstat_rss_kib_mean",
    "pidstat_kb_wr_per_s_mean",
    "pidstat_iodelay_mean",
]].rename(columns={
    "pidstat_cpu_percent_mean": "cpu_percent",
    "pidstat_rss_kib_mean": "rss_kib",
    "pidstat_kb_wr_per_s_mean": "kb_wr_per_s",
    "pidstat_iodelay_mean": "iodelay",
})
resource_process_df.round(3)

resource_disk_df = resource_profile_df[[
    "iostat_busiest_device",
    "iostat_pct_util_mean",
    "iostat_r_await_mean",
    "iostat_w_await_mean",
    "iostat_f_await_mean",
    "iostat_aqu_sz_mean",
    "iostat_wkb_s_mean",
]].rename(columns={
    "iostat_busiest_device": "busiest_device",
    "iostat_pct_util_mean": "pct_util",
    "iostat_r_await_mean": "r_await",
    "iostat_w_await_mean": "w_await",
    "iostat_f_await_mean": "f_await",
    "iostat_aqu_sz_mean": "aqu_sz",
    "iostat_wkb_s_mean": "wkb_s",
})
resource_disk_df.round(3)


# %matplotlib inline
from pathlib import Path
import sys
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path("scripts").resolve()))

from plot_latency import load_points, LATENCY_COLUMNS


def show_latency_timeline(path_a, path_b, label_a="A", label_b="B"):
    csv_path_a = Path(path_a)
    csv_path_b = Path(path_b)

    points_a = load_points(csv_path_a, only_success=False)
    points_b = load_points(csv_path_b, only_success=False)

    # x_a = [p.started_at for p in points_a]
    # x_b = [p.started_at for p in points_b]
    t0_a = points_a[0].started_at
    t0_b = points_b[0].started_at

    x_a = [(p.started_at - t0_a).total_seconds() for p in points_a]
    x_b = [(p.started_at - t0_b).total_seconds() for p in points_b]
    fig, axes = plt.subplots(
        len(LATENCY_COLUMNS),
        1,
        sharex=True,
        figsize=(14, 10),
        constrained_layout=True,
    )

    if len(LATENCY_COLUMNS) == 1:
        axes = [axes]

    # ❗去掉 strict=True，避免潜在报错
    for ax, (column, label) in zip(axes, LATENCY_COLUMNS):
        y_a = [p.values.get(column) for p in points_a]
        y_b = [p.values.get(column) for p in points_b]

        # ✅ 第一组
        ax.plot(
            x_a, y_a,
            marker="o",
            markersize=3,
            linewidth=1.2,
            label=label_a,
        )

        # ✅ 第二组
        ax.plot(
            x_b, y_b,
            marker="o",
            markersize=3,
            linewidth=1.2,
            linestyle="--",
            label=label_b,
        )

        ax.set_ylabel(f"{label}\n(ms)")
        ax.grid(True, alpha=0.25)

        # ✅ 每个子图都有图例（或者你也可以只放第一个）
        ax.legend()

    axes[-1].set_xlabel("Time (s)")
    axes[0].set_title(
        f"Latency timeline: {csv_path_a.name} vs {csv_path_b.name}"
    )

    plt.show()

show_latency_timeline(
    "./out/20260324T183523Z_vps-docker-single-task-00-500-full/latency.csv",
    "./out/20260324T183647Z_vps-docker-multi-task-00-500-full/latency.csv",
    label_a="single - 1 worker x 500 requests",
    label_b="multi - 20 workers x 25 requests"
)
