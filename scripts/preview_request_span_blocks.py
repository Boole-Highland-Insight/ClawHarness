from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


@dataclass(frozen=True)
class RequestSpan:
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


def load_request_spans(csv_path: Path) -> list[RequestSpan]:
    rows: list[tuple[datetime, datetime]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            started_at = parse_iso_datetime(str(row.get("started_at", "")))
            finished_at = parse_iso_datetime(str(row.get("finished_at", "")))
            if started_at is None:
                continue
            if finished_at is None or finished_at < started_at:
                finished_at = started_at
            rows.append((started_at, finished_at))

    if not rows:
        return []

    first_started_at = min(started_at for started_at, _ in rows)
    spans = [
        RequestSpan(
            start_sec=(started_at - first_started_at).total_seconds(),
            finish_sec=(finished_at - first_started_at).total_seconds(),
        )
        for started_at, finished_at in rows
    ]
    return sorted(spans, key=lambda span: (span.start_sec, span.finish_sec))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview request span blocks with a common t=0 origin per run.",
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
        default="Request Span Block Preview",
        help="Figure title.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    colors = ["#e15759", "#4e79a7", "#59a14f", "#f28e2b", "#b07aa1"]

    fig, ax = plt.subplots(figsize=(12, 9), constrained_layout=True)
    global_max_sec = 0.0

    for index, (label, raw_csv_path) in enumerate(args.run):
        csv_path = Path(raw_csv_path)
        spans = load_request_spans(csv_path)
        if not spans:
            continue

        color = colors[index % len(colors)]
        for span in spans:
            if span.duration_sec <= 0:
                continue
            rect = Rectangle(
                (span.start_sec, span.start_sec),
                span.duration_sec,
                span.duration_sec,
                facecolor=color,
                edgecolor=color,
                linewidth=0.8,
                alpha=0.18,
            )
            ax.add_patch(rect)
            global_max_sec = max(global_max_sec, span.finish_sec)

        run_finish_sec = max(span.finish_sec for span in spans)
        ax.axvline(run_finish_sec, color=color, linestyle="--", linewidth=1.2, alpha=0.85)
        ax.axhline(run_finish_sec, color=color, linestyle=":", linewidth=1.0, alpha=0.55)
        ax.plot([], [], color=color, linewidth=6, alpha=0.35, label=f"{label} blocks")
        ax.plot([], [], color=color, linestyle="--", label=f"{label} run finish")

    axis_max = global_max_sec * 1.05 if global_max_sec > 0 else 1.0
    ax.plot([0.0, axis_max], [0.0, axis_max], color="#222222", linewidth=1.0, alpha=0.5)
    ax.set_xlim(0.0, axis_max)
    ax.set_ylim(0.0, axis_max)
    ax.set_xlabel("Elapsed time since first request start in that run (s)")
    ax.set_ylabel("Elapsed completion time since first request start (s)")
    ax.set_title(args.title)
    ax.grid(True, alpha=0.18)
    ax.legend(loc="upper left")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())