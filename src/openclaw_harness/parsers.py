from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .utils import write_json


@dataclass(frozen=True)
class ParsedArtifact:
    name: str
    files: list[str]
    summary: dict[str, Any]


@dataclass(frozen=True)
class _PidstatSection:
    name: str
    markers: tuple[str, ...]
    fields: tuple[str, ...]
    numeric_fields: tuple[str, ...]


PIDSTAT_SECTIONS = (
    _PidstatSection(
        name="cpu",
        markers=("%usr", "%system", "%guest", "%wait", "%CPU", "CPU", "Command"),
        fields=("uid", "pid", "pct_usr", "pct_system", "pct_guest", "pct_wait", "pct_cpu", "cpu", "command"),
        numeric_fields=("pct_usr", "pct_system", "pct_guest", "pct_wait", "pct_cpu"),
    ),
    _PidstatSection(
        name="memory",
        markers=("minflt/s", "majflt/s", "VSZ", "RSS", "%MEM", "Command"),
        fields=("uid", "pid", "minflt_per_s", "majflt_per_s", "vsz_kib", "rss_kib", "pct_mem", "command"),
        numeric_fields=("minflt_per_s", "majflt_per_s", "vsz_kib", "rss_kib", "pct_mem"),
    ),
    _PidstatSection(
        name="io",
        markers=("kB_rd/s", "kB_wr/s", "kB_ccwr/s", "iodelay", "Command"),
        fields=("uid", "pid", "kb_rd_per_s", "kb_wr_per_s", "kb_ccwr_per_s", "iodelay", "command"),
        numeric_fields=("kb_rd_per_s", "kb_wr_per_s", "kb_ccwr_per_s", "iodelay"),
    ),
)


def parse_collector_artifacts(*, output_dir: Path, collectors: list[Any]) -> dict[str, Any]:
    analyses: dict[str, Any] = {}
    by_name = {collector.status.name: collector for collector in collectors}

    pidstat = by_name.get("pidstat")
    pidstat_log = output_dir / "pidstat.log"
    if pidstat is not None and pidstat_log.exists():
        parsed = parse_pidstat_log(pidstat_log, output_dir=output_dir)
        if parsed is not None:
            pidstat.status.files.extend(path for path in parsed.files if path not in pidstat.status.files)
            analyses[parsed.name] = parsed.summary

    perf_stat = by_name.get("perf_stat")
    perf_stat_raw = output_dir / "perf_stat.csv"
    if perf_stat is not None and perf_stat_raw.exists():
        parsed = parse_perf_stat_csv(perf_stat_raw, output_dir=output_dir)
        if parsed is not None:
            perf_stat.status.files.extend(path for path in parsed.files if path not in perf_stat.status.files)
            analyses[parsed.name] = parsed.summary

    perf_record = by_name.get("perf_record")
    perf_data = output_dir / "perf.data"
    perf_log = output_dir / "perf_record.log"
    if perf_record is not None and (perf_data.exists() or perf_log.exists()):
        parsed = summarize_perf_record(perf_data=perf_data, perf_log=perf_log, output_dir=output_dir)
        if parsed is not None:
            perf_record.status.files.extend(path for path in parsed.files if path not in perf_record.status.files)
            analyses[parsed.name] = parsed.summary

    return analyses


def parse_pidstat_log(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    current_section: _PidstatSection | None = None
    rows_by_section: dict[str, list[dict[str, Any]]] = {section.name: [] for section in PIDSTAT_SECTIONS}

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("Linux "):
            continue
        sample_kind = "average" if stripped.startswith("Average:") else "interval"
        sample_time, tokens = _extract_pidstat_tokens(stripped)
        if not tokens:
            continue
        detected = _detect_pidstat_section(tokens)
        if detected is not None:
            current_section = detected
            continue
        if current_section is None:
            continue
        if tokens[0] == "UID":
            continue
        row = _parse_pidstat_row(tokens, sample_time=sample_time, sample_kind=sample_kind, section=current_section)
        if row is None:
            continue
        rows_by_section[current_section.name].append(row)

    written_files: list[str] = []
    section_summaries: dict[str, Any] = {}
    for section in PIDSTAT_SECTIONS:
        rows = rows_by_section[section.name]
        if not rows:
            continue
        csv_path = output_dir / f"pidstat_{section.name}.csv"
        _write_csv(csv_path, rows)
        written_files.append(str(csv_path))
        section_summaries[section.name] = {
            "rows": len(rows),
            "sample_kinds": sorted({str(row["sample_kind"]) for row in rows}),
            "metrics": {
                field: _summarize_numeric(
                    [float(row[field]) for row in rows if isinstance(row.get(field), (int, float))]
                )
                for field in section.numeric_fields
            },
        }

    if not section_summaries:
        return None

    summary = {
        "raw_log": str(path),
        "sections": section_summaries,
    }
    summary_path = output_dir / "pidstat.summary.json"
    write_json(summary_path, summary)
    written_files.append(str(summary_path))
    return ParsedArtifact(name="pidstat", files=written_files, summary=summary)


def parse_perf_stat_csv(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        for raw_row in reader:
            if not raw_row:
                continue
            cells = [cell.strip() for cell in raw_row]
            if not any(cells):
                continue
            if cells[0].startswith("#"):
                continue
            record = _parse_perf_stat_row(cells)
            if record is not None:
                rows.append(record)

    if not rows:
        return None

    parsed_path = output_dir / "perf_stat.parsed.csv"
    _write_csv(parsed_path, rows)

    summary = {
        "raw_csv": str(path),
        "rows": len(rows),
        "events": [
            {
                "event": row["event"],
                "counter_value": row["counter_value"],
                "counter_unit": row["counter_unit"],
                "runtime_ms": row["runtime_ms"],
                "running_pct": row["running_pct"],
                "metric_value": row["metric_value"],
                "metric_unit": row["metric_unit"],
            }
            for row in rows
        ],
    }
    summary_path = output_dir / "perf_stat.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(
        name="perf_stat",
        files=[str(parsed_path), str(summary_path)],
        summary=summary,
    )


def summarize_perf_record(*, perf_data: Path, perf_log: Path, output_dir: Path) -> ParsedArtifact | None:
    if not perf_data.exists() and not perf_log.exists():
        return None
    summary = {
        "perf_data": {
            "path": str(perf_data),
            "exists": perf_data.exists(),
            "size_bytes": perf_data.stat().st_size if perf_data.exists() else 0,
        },
        "perf_log": {
            "path": str(perf_log),
            "exists": perf_log.exists(),
            "size_bytes": perf_log.stat().st_size if perf_log.exists() else 0,
        },
    }
    summary_path = output_dir / "perf_record.summary.json"
    write_json(summary_path, summary)
    files = [str(summary_path)]
    if perf_data.exists():
        files.append(str(perf_data))
    if perf_log.exists():
        files.append(str(perf_log))
    return ParsedArtifact(name="perf_record", files=files, summary=summary)


def derive_healthcheck_url(ws_url: str) -> str:
    parts = urlsplit(ws_url)
    if parts.scheme not in {"ws", "wss"}:
        return ""
    http_scheme = "https" if parts.scheme == "wss" else "http"
    return urlunsplit((http_scheme, parts.netloc, "/healthz", "", ""))


def _extract_pidstat_tokens(line: str) -> tuple[str, list[str]]:
    tokens = line.split()
    if not tokens:
        return "", []
    if tokens[0] == "Average:":
        return "Average", tokens[1:]
    if len(tokens) >= 2 and tokens[1] in {"AM", "PM"}:
        return f"{tokens[0]} {tokens[1]}", tokens[2:]
    if ":" in tokens[0]:
        return tokens[0], tokens[1:]
    return "", tokens


def _detect_pidstat_section(tokens: list[str]) -> _PidstatSection | None:
    if not tokens or tokens[0] != "UID":
        return None
    tail = tuple(tokens[2:])
    for section in PIDSTAT_SECTIONS:
        if tail == section.markers:
            return section
    return None


def _parse_pidstat_row(
    tokens: list[str],
    *,
    sample_time: str,
    sample_kind: str,
    section: _PidstatSection,
) -> dict[str, Any] | None:
    fixed_value_count = len(section.fields) - 1
    if len(tokens) < fixed_value_count:
        return None
    values = tokens[:fixed_value_count]
    command = " ".join(tokens[fixed_value_count:])
    if not command:
        return None
    row: dict[str, Any] = {
        "sample_time": sample_time,
        "sample_kind": sample_kind,
    }
    for field, raw in zip(section.fields[:-1], values, strict=True):
        row[field] = _parse_number_maybe(raw)
    row["command"] = command
    return row


def _parse_perf_stat_row(cells: list[str]) -> dict[str, Any] | None:
    timestamp = ""
    fields = cells
    if len(cells) >= 8:
        timestamp = cells[0]
        fields = cells[1:]
    while len(fields) < 7:
        fields.append("")
    counter_value_raw, counter_unit, event, runtime_ms_raw, running_pct_raw, metric_value_raw, metric_unit = fields[:7]
    if not event:
        return None
    return {
        "timestamp": timestamp,
        "counter_value_raw": counter_value_raw,
        "counter_value": _parse_number_maybe(counter_value_raw),
        "counter_unit": counter_unit,
        "event": event,
        "runtime_ms_raw": runtime_ms_raw,
        "runtime_ms": _parse_number_maybe(runtime_ms_raw),
        "running_pct_raw": running_pct_raw,
        "running_pct": _parse_number_maybe(running_pct_raw),
        "metric_value_raw": metric_value_raw,
        "metric_value": _parse_number_maybe(metric_value_raw),
        "metric_unit": metric_unit,
    }


def _parse_number_maybe(raw: str) -> int | float | str:
    value = raw.strip()
    if not value:
        return ""
    normalized = value.replace("_", "")
    if normalized.isdigit() or (normalized.startswith("-") and normalized[1:].isdigit()):
        try:
            return int(normalized)
        except ValueError:
            return value
    try:
        return float(normalized)
    except ValueError:
        return value


def _summarize_numeric(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "count": 0.0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
        }
    return {
        "count": float(len(values)),
        "min": float(min(values)),
        "max": float(max(values)),
        "mean": float(fmean(values)),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
