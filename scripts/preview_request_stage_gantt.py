from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class RequestStageBar:
    label: str
    stagger_start_sec: float
    stagger_duration_sec: float
    connect_start_sec: float | None
    connect_duration_sec: float
    request_start_sec: float
    request_finish_sec: float

    @property
    def request_duration_sec(self) -> float:
        return max(0.0, self.request_finish_sec - self.request_start_sec)


@dataclass(frozen=True)
class LoadedRun:
    label: str
    bars: list[RequestStageBar]
    run_finish_sec: float


def parse_iso_datetime(value: str) -> datetime | None:
    raw_value = str(value).strip()
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def parse_float(value: str | None) -> float:
    raw_value = str(value or "").strip()
    if not raw_value:
        return 0.0
    try:
        return float(raw_value)
    except ValueError:
        return 0.0


def load_run(run_dir: Path, label: str) -> LoadedRun:
    summary_payload = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    scenario_payload = json.loads((run_dir / "scenario.resolved.json").read_text(encoding="utf-8"))
    run_started_at = parse_iso_datetime(summary_payload.get("started_at", ""))
    if run_started_at is None:
        raise ValueError(f"Run summary missing started_at: {run_dir}")

    load_config = scenario_payload.get("load", {})
    worker_stagger_ms = int(load_config.get("worker_stagger_ms", 0) or 0)

    first_request_seen: set[tuple[int, int]] = set()
    bars: list[RequestStageBar] = []
    with (run_dir / "latency.csv").open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            started_at = parse_iso_datetime(row.get("started_at", ""))
            finished_at = parse_iso_datetime(row.get("finished_at", ""))
            if started_at is None:
                continue
            if finished_at is None or finished_at < started_at:
                finished_at = started_at

            worker_id_raw = str(row.get("worker_id", "")).strip()
            request_index_raw = str(row.get("request_index", "")).strip()
            try:
                worker_id = int(worker_id_raw)
            except ValueError:
                worker_id = -1
            try:
                request_index = int(request_index_raw)
            except ValueError:
                request_index = -1

            key = (int(parse_float(row.get("instance_index", "0"))), worker_id)
            is_first_request = key not in first_request_seen and request_index == 0
            if is_first_request:
                first_request_seen.add(key)

            request_start_sec = max(0.0, (started_at - run_started_at).total_seconds())
            request_finish_sec = max(request_start_sec, (finished_at - run_started_at).total_seconds())
            connect_duration_sec = parse_float(row.get("connect_latency_ms")) / 1000.0 if is_first_request else 0.0
            connect_start_sec = None
            if connect_duration_sec > 0.0:
                connect_start_sec = max(0.0, request_start_sec - connect_duration_sec)
            stagger_duration_sec = (worker_stagger_ms * max(worker_id, 0)) / 1000.0 if is_first_request else 0.0

            bars.append(
                RequestStageBar(
                    label=f"w{worker_id_raw or '?'}-r{request_index_raw or '?'}",
                    stagger_start_sec=0.0,
                    stagger_duration_sec=stagger_duration_sec,
                    connect_start_sec=connect_start_sec,
                    connect_duration_sec=connect_duration_sec,
                    request_start_sec=request_start_sec,
                    request_finish_sec=request_finish_sec,
                )
            )

    bars.sort(key=lambda item: (item.request_start_sec, item.request_finish_sec, item.label))
    run_finish_sec = max((bar.request_finish_sec for bar in bars), default=0.0)
    return LoadedRun(label=label, bars=bars, run_finish_sec=run_finish_sec)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render segmented request timelines with separate stagger and connect phases.",
    )
    parser.add_argument(
        "--run",
        action="append",
        nargs=2,
        metavar=("LABEL", "RUN_DIR"),
        required=True,
        help="Display label and benchmark run directory. May be repeated.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output PNG path.",
    )
    parser.add_argument(
        "--title",
        default="Request Timeline with Stagger and Connect",
        help="Figure title.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request_colors = ["#4e79a7", "#e15759", "#59a14f", "#f28e2b", "#b07aa1"]
    stagger_color = "#9c9c9c"
    connect_color = "#f1a340"

    loaded_runs = [load_run(Path(raw_run_dir), label) for label, raw_run_dir in args.run]
    loaded_runs = [run for run in loaded_runs if run.bars]
    if not loaded_runs:
        raise ValueError("No usable request timing rows found")

    global_max_finish = max(
        max(run.run_finish_sec, max(bar.request_finish_sec for bar in run.bars))
        for run in loaded_runs
    )

    fig, axes = plt.subplots(
        len(loaded_runs),
        1,
        sharex=True,
        figsize=(16, max(4.5, 3.1 * len(loaded_runs))),
        constrained_layout=True,
    )
    if len(loaded_runs) == 1:
        axes = [axes]

    legend_handles = None
    for index, (ax, run) in enumerate(zip(axes, loaded_runs)):
        request_color = request_colors[index % len(request_colors)]
        y_positions = list(range(len(run.bars)))

        stagger_bar = ax.barh(
            y_positions,
            [bar.stagger_duration_sec for bar in run.bars],
            left=[bar.stagger_start_sec for bar in run.bars],
            height=0.72,
            color=stagger_color,
            edgecolor=stagger_color,
            alpha=0.45,
        )
        connect_bar = ax.barh(
            y_positions,
            [bar.connect_duration_sec for bar in run.bars],
            left=[bar.connect_start_sec or 0.0 for bar in run.bars],
            height=0.72,
            color=connect_color,
            edgecolor=connect_color,
            alpha=0.7,
        )
        request_bar = ax.barh(
            y_positions,
            [bar.request_duration_sec for bar in run.bars],
            left=[bar.request_start_sec for bar in run.bars],
            height=0.72,
            color=request_color,
            edgecolor=request_color,
            alpha=0.4,
        )
        ax.axvline(run.run_finish_sec, color=request_color, linestyle="--", linewidth=1.2, alpha=0.9)
        ax.set_title(f"{run.label} (run finish {run.run_finish_sec:.1f}s)")
        ax.set_ylabel("request")
        ax.set_yticks(y_positions)
        ax.set_yticklabels([bar.label for bar in run.bars], fontsize=8)
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.2)
        if legend_handles is None:
            legend_handles = [stagger_bar[0], connect_bar[0], request_bar[0]]

    axes[-1].set_xlabel("Elapsed time since run started (s)")
    for ax in axes:
        ax.set_xlim(0.0, global_max_finish * 1.03 if global_max_finish > 0 else 1.0)

    if legend_handles is not None:
        fig.legend(
            legend_handles,
            ["stagger", "connect", "request"],
            loc="lower center",
            bbox_to_anchor=(0.5, 0.0),
            ncol=3,
            frameon=False,
        )
    fig.suptitle(args.title)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())