from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


LATENCY_COLUMNS = [
    ("connect_latency_ms", "Connect"),
    ("send_latency_ms", "Send"),
    ("wait_latency_ms", "Wait"),
    ("history_latency_ms", "History"),
    ("total_latency_ms", "Total"),
]


@dataclass(frozen=True)
class LatencyPoint:
    started_at: datetime
    values: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot latency columns from a latency.csv file over time."
    )
    parser.add_argument("csv_path", type=Path, help="Path to latency.csv")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output image path. Defaults to <csv_stem>_timeline.png next to the CSV.",
    )
    parser.add_argument(
        "--only-success",
        action="store_true",
        help="Plot only rows with success == True.",
    )
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def load_points(csv_path: Path, only_success: bool) -> list[LatencyPoint]:
    points: list[LatencyPoint] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if only_success and not parse_bool(str(row.get("success", ""))):
                continue

            started_at_raw = str(row.get("started_at", "")).strip()
            if not started_at_raw:
                continue

            try:
                started_at = datetime.fromisoformat(started_at_raw)
            except ValueError:
                continue

            values: dict[str, float] = {}
            for column, _label in LATENCY_COLUMNS:
                raw_value = str(row.get(column, "")).strip()
                if not raw_value:
                    continue
                try:
                    values[column] = float(raw_value)
                except ValueError:
                    continue

            if values:
                points.append(LatencyPoint(started_at=started_at, values=values))

    points.sort(key=lambda point: point.started_at)
    return points


def plot(points: list[LatencyPoint], csv_path: Path, output_path: Path) -> None:
    if not points:
        raise SystemExit(f"No usable rows found in {csv_path}")

    fig, axes = plt.subplots(
        len(LATENCY_COLUMNS),
        1,
        sharex=True,
        figsize=(14, 10),
        constrained_layout=True,
    )

    if len(LATENCY_COLUMNS) == 1:
        axes = [axes]

    x_values = [point.started_at for point in points]

    for ax, (column, label) in zip(axes, LATENCY_COLUMNS, strict=True):
        y_values = [point.values.get(column) for point in points]
        ax.plot(x_values, y_values, marker="o", markersize=3, linewidth=1.2)
        ax.set_ylabel(f"{label}\n(ms)")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("Started at")
    axes[0].set_title(f"Latency timeline: {csv_path.name}")

    locator = mdates.AutoDateLocator()
    formatter = mdates.ConciseDateFormatter(locator)
    axes[-1].xaxis.set_major_locator(locator)
    axes[-1].xaxis.set_major_formatter(formatter)

    fig.suptitle("Latency over time", y=1.02, fontsize=14)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    csv_path = args.csv_path.expanduser().resolve()
    output_path = (
        args.output.expanduser().resolve()
        if args.output is not None
        else csv_path.with_name(f"{csv_path.stem}_timeline.png")
    )

    points = load_points(csv_path, only_success=args.only_success)
    plot(points, csv_path, output_path)
    print(f"Saved plot to {output_path}")


if __name__ == "__main__":
    main()
