from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class RequestBar:
    label: str
    start_sec: float
    finish_sec: float

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.finish_sec - self.start_sec)


def parse_iso_datetime(value: str) -> datetime | None:
    raw_value = str(value).strip()
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def load_request_bars(csv_path: Path) -> list[RequestBar]:
    rows: list[tuple[datetime, datetime, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            started_at = parse_iso_datetime(str(row.get("started_at", "")))
            finished_at = parse_iso_datetime(str(row.get("finished_at", "")))
            if started_at is None:
                continue
            if finished_at is None or finished_at < started_at:
                finished_at = started_at
            worker_id = str(row.get("worker_id", "")).strip() or "?"
            request_index = str(row.get("request_index", "")).strip() or "?"
            label = f"w{worker_id}-r{request_index}"
            rows.append((started_at, finished_at, label))

    if not rows:
        return []

    rows.sort(key=lambda item: (item[0], item[1], item[2]))
    origin = min(started_at for started_at, _, _ in rows)
    return [
        RequestBar(
            label=label,
            start_sec=(started_at - origin).total_seconds(),
            finish_sec=(finished_at - origin).total_seconds(),
        )
        for started_at, finished_at, label in rows
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview request timing as aligned Gantt charts with shared x-axis scale.",
    )
    parser.add_argument(
        "--run",
        action="append",
        nargs=2,
        metavar=("LABEL", "LATENCY_CSV"),
        required=True,
        help="Label and latency.csv path. May be repeated.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output PNG path.",
    )
    parser.add_argument(
        "--title",
        default="Request Gantt Preview",
        help="Figure title.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    colors = ["#e15759", "#4e79a7", "#59a14f", "#f28e2b", "#b07aa1"]

    loaded_runs: list[tuple[str, list[RequestBar]]] = []
    global_max_finish = 0.0
    for label, raw_csv_path in args.run:
        csv_path = Path(raw_csv_path)
        bars = load_request_bars(csv_path)
        if not bars:
            continue
        loaded_runs.append((label, bars))
        global_max_finish = max(global_max_finish, max(bar.finish_sec for bar in bars))

    if not loaded_runs:
        raise ValueError("No usable request timing rows found")

    fig, axes = plt.subplots(
        len(loaded_runs),
        1,
        sharex=True,
        figsize=(14, max(4.0, 2.6 * len(loaded_runs))),
        constrained_layout=True,
    )
    if len(loaded_runs) == 1:
        axes = [axes]

    for index, (ax, (label, bars)) in enumerate(zip(axes, loaded_runs)):
        color = colors[index % len(colors)]
        y_positions = list(range(len(bars)))
        left_values = [bar.start_sec for bar in bars]
        widths = [bar.duration_sec for bar in bars]
        ax.barh(
            y_positions,
            widths,
            left=left_values,
            height=0.72,
            color=color,
            edgecolor=color,
            alpha=0.35,
        )
        ax.axvline(
            max(bar.finish_sec for bar in bars),
            color=color,
            linestyle="--",
            linewidth=1.2,
            alpha=0.9,
        )
        ax.set_title(f"{label} (run finish {max(bar.finish_sec for bar in bars):.1f}s)")
        ax.set_ylabel("request")
        ax.set_yticks(y_positions)
        ax.set_yticklabels([bar.label for bar in bars], fontsize=8)
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.2)

    axes[-1].set_xlabel("Elapsed time since first request start in that run (s)")
    for ax in axes:
        ax.set_xlim(0.0, global_max_finish * 1.05 if global_max_finish > 0 else 1.0)

    fig.suptitle(args.title)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())