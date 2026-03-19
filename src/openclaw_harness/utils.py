from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat()


def timestamp_slug() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    chars = []
    for char in lowered:
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "-":
            chars.append("-")
    return "".join(chars).strip("-") or "run"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def command_path(command: str) -> str | None:
    return shutil.which(command)


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return float(ordered[index])


def summarize_ms(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0.0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
        }
    total = float(sum(values))
    count = float(len(values))
    return {
        "count": count,
        "min": float(min(values)),
        "max": float(max(values)),
        "mean": total / count,
        "p50": percentile(values, 50.0),
        "p95": percentile(values, 95.0),
        "p99": percentile(values, 99.0),
    }


def run_command(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture_output: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        list(args),
        cwd=str(cwd) if cwd else None,
        env=merged_env,
        check=check,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def compact_cmd(args: Iterable[str]) -> str:
    return " ".join(args)
