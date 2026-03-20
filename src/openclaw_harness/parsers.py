from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re
from statistics import fmean
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .utils import summarize_ms, write_json


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
    _PidstatSection(
        name="context_switch",
        markers=("cswch/s", "nvcswch/s", "Command"),
        fields=("uid", "pid", "cswch_per_s", "nvcswch_per_s", "command"),
        numeric_fields=("cswch_per_s", "nvcswch_per_s"),
    ),
)


def parse_collector_artifacts(
    *,
    output_dir: Path,
    collectors: list[Any],
    run_started_at: str,
) -> dict[str, Any]:
    analyses: dict[str, Any] = {}
    by_name = {collector.status.name: collector for collector in collectors}

    docker_stats = by_name.get("docker_stats")
    docker_stats_csv = output_dir / "docker_stats.csv"
    if docker_stats is not None and docker_stats_csv.exists():
        parsed = parse_docker_stats_csv(docker_stats_csv, output_dir=output_dir)
        if parsed is not None:
            docker_stats.status.files.extend(path for path in parsed.files if path not in docker_stats.status.files)
            analyses[parsed.name] = parsed.summary

    pidstat = by_name.get("pidstat")
    pidstat_log = output_dir / "pidstat.log"
    if pidstat is not None and pidstat_log.exists():
        parsed = parse_pidstat_log(pidstat_log, output_dir=output_dir, run_started_at=run_started_at)
        if parsed is not None:
            pidstat.status.files.extend(path for path in parsed.files if path not in pidstat.status.files)
            analyses[parsed.name] = parsed.summary

    perf_stat = by_name.get("perf_stat")
    perf_stat_raw = output_dir / "perf_stat.csv"
    if perf_stat is not None and perf_stat_raw.exists():
        parsed = parse_perf_stat_csv(perf_stat_raw, output_dir=output_dir, run_started_at=run_started_at)
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

    iostat = by_name.get("iostat")
    iostat_log = output_dir / "iostat.log"
    if iostat is not None and iostat_log.exists():
        parsed = parse_iostat_log(iostat_log, output_dir=output_dir, run_started_at=run_started_at)
        if parsed is not None:
            iostat.status.files.extend(path for path in parsed.files if path not in iostat.status.files)
            analyses[parsed.name] = parsed.summary

    return analyses


def parse_docker_stats_csv(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            if not raw_row:
                continue
            cpu_pct = _parse_percent_maybe(raw_row.get("cpu_percent", ""))
            mem_pct = _parse_percent_maybe(raw_row.get("mem_percent", ""))
            pids = _parse_number_maybe(str(raw_row.get("pids", "")).strip())
            mem_usage, mem_limit = _parse_usage_pair(raw_row.get("mem_usage_limit", ""))
            net_rx, net_tx = _parse_usage_pair(raw_row.get("net_io", ""))
            block_read, block_write = _parse_usage_pair(raw_row.get("block_io", ""))
            rows.append(
                {
                    "timestamp": str(raw_row.get("timestamp", "")).strip(),
                    "container": str(raw_row.get("container", "")).strip(),
                    "cpu_percent_value": cpu_pct,
                    "mem_percent_value": mem_pct,
                    "pids_value": pids,
                    "mem_usage_bytes": mem_usage,
                    "mem_limit_bytes": mem_limit,
                    "net_rx_bytes": net_rx,
                    "net_tx_bytes": net_tx,
                    "block_read_bytes": block_read,
                    "block_write_bytes": block_write,
                }
            )

    if not rows:
        return None

    parsed_path = output_dir / "docker_stats.parsed.csv"
    _write_csv(parsed_path, rows)

    numeric_fields = (
        "cpu_percent_value",
        "mem_percent_value",
        "pids_value",
        "mem_usage_bytes",
        "mem_limit_bytes",
        "net_rx_bytes",
        "net_tx_bytes",
        "block_read_bytes",
        "block_write_bytes",
    )
    summary = {
        "raw_csv": str(path),
        "rows": len(rows),
        "container": next((str(row["container"]) for row in rows if row.get("container")), ""),
        "metrics": {
            field: summarize_ms(
                [float(row[field]) for row in rows if isinstance(row.get(field), (int, float))]
            )
            for field in numeric_fields
        },
    }
    summary_path = output_dir / "docker_stats.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="docker_stats", files=[str(parsed_path), str(summary_path)], summary=summary)


def parse_pidstat_log(path: Path, *, output_dir: Path, run_started_at: str) -> ParsedArtifact | None:
    current_section: _PidstatSection | None = None
    rows_by_section: dict[str, list[dict[str, Any]]] = {section.name: [] for section in PIDSTAT_SECTIONS}
    combined_header: list[str] | None = None
    last_sample_timestamp: datetime | None = None
    run_started = _parse_iso_timestamp(run_started_at)

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("Linux "):
            continue
        if stripped.startswith("# Time"):
            combined_header = stripped.lstrip("# ").split()
            current_section = None
            continue
        if combined_header is not None and not stripped.startswith("#"):
            combined_row = _parse_pidstat_combined_row(stripped, combined_header=combined_header)
            if combined_row is not None:
                sample_timestamp = _resolve_pidstat_sample_timestamp(
                    combined_row["sample_time"],
                    run_started=run_started,
                    last_sample_timestamp=last_sample_timestamp,
                )
                if sample_timestamp is not None:
                    combined_row["sample_timestamp"] = sample_timestamp.isoformat()
                    last_sample_timestamp = sample_timestamp
                for section in PIDSTAT_SECTIONS:
                    section_row = {
                        "sample_timestamp": combined_row.get("sample_timestamp", ""),
                        "sample_time": combined_row["sample_time"],
                        "sample_kind": combined_row["sample_kind"],
                        "uid": combined_row.get("uid", ""),
                        "pid": combined_row.get("pid", ""),
                        "command": combined_row.get("command", ""),
                    }
                    for field in section.fields[2:-1]:
                        if field in combined_row:
                            section_row[field] = combined_row[field]
                    rows_by_section[section.name].append(section_row)
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
        sample_timestamp = _resolve_pidstat_sample_timestamp(
            sample_time,
            run_started=run_started,
            last_sample_timestamp=last_sample_timestamp,
        )
        if sample_timestamp is not None:
            row["sample_timestamp"] = sample_timestamp.isoformat()
            last_sample_timestamp = sample_timestamp
        else:
            row["sample_timestamp"] = ""
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


def parse_perf_stat_csv(path: Path, *, output_dir: Path, run_started_at: str) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    run_started = _parse_iso_timestamp(run_started_at)
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
                sample_timestamp = _resolve_perf_stat_timestamp(record.get("timestamp", ""), run_started=run_started)
                record["sample_timestamp"] = sample_timestamp.isoformat() if sample_timestamp is not None else ""
                rows.append(record)

    if not rows:
        return None

    parsed_path = output_dir / "perf_stat.parsed.csv"
    _write_csv(parsed_path, rows)

    summary = {
        "raw_csv": str(path),
        "rows": len(rows),
        "time_series_events": {
            event: summarize_ms(
                [
                    float(row["counter_value"])
                    for row in rows
                    if row.get("event") == event and isinstance(row.get("counter_value"), (int, float))
                ]
            )
            for event in sorted({str(row["event"]) for row in rows if row.get("event")})
        },
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


def parse_iostat_log(path: Path, *, output_dir: Path, run_started_at: str) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    current_header: list[str] | None = None
    current_timestamp: str = ""
    run_started = _parse_iso_timestamp(run_started_at)

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("Linux "):
            continue
        timestamp_candidate = _parse_iostat_timestamp_line(stripped, run_started=run_started)
        if timestamp_candidate is not None:
            current_timestamp = timestamp_candidate.isoformat()
            current_header = None
            continue
        if stripped.startswith("Device"):
            current_header = stripped.split()
            continue
        if current_header is None or stripped.startswith("avg-cpu"):
            continue
        tokens = stripped.split()
        if len(tokens) < len(current_header):
            continue
        row: dict[str, Any] = {}
        for key, raw in zip(current_header, tokens, strict=True):
            normalized_key = _normalize_metric_key(key)
            row[normalized_key] = raw if normalized_key == "device" else _parse_number_maybe(raw)
        row["sample_timestamp"] = current_timestamp
        rows.append(row)

    if not rows:
        return None

    parsed_path = output_dir / "iostat.parsed.csv"
    _write_csv(parsed_path, rows)

    metric_names = [key for key in rows[0].keys() if key not in {"device", "sample_timestamp"}]
    by_device: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        device = str(row.get("device", "")).strip()
        if not device:
            continue
        by_device.setdefault(device, []).append(row)

    devices_summary: dict[str, Any] = {}
    busiest_device = ""
    busiest_util_mean = -1.0
    for device, device_rows in by_device.items():
        metrics = {
            metric: summarize_ms(
                [float(row[metric]) for row in device_rows if isinstance(row.get(metric), (int, float))]
            )
            for metric in metric_names
        }
        devices_summary[device] = {
            "rows": len(device_rows),
            "metrics": metrics,
        }
        util_mean = float(metrics.get("pct_util", {}).get("mean", 0.0))
        if util_mean > busiest_util_mean:
            busiest_util_mean = util_mean
            busiest_device = device

    summary = {
        "raw_log": str(path),
        "rows": len(rows),
        "devices": devices_summary,
        "busiest_device_by_util_mean": busiest_device,
    }
    summary_path = output_dir / "iostat.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="iostat", files=[str(parsed_path), str(summary_path)], summary=summary)


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


def _parse_pidstat_combined_row(line: str, *, combined_header: list[str]) -> dict[str, Any] | None:
    tokens = line.split()
    if len(tokens) < len(combined_header):
        return None
    sample_time = tokens[0]
    values = tokens[1 : len(combined_header) - 1]
    command = " ".join(tokens[len(combined_header) - 1 :])
    if not command:
        return None
    header_fields = combined_header[1:-1]
    field_map = {
        "%usr": "pct_usr",
        "%system": "pct_system",
        "%guest": "pct_guest",
        "%wait": "pct_wait",
        "%CPU": "pct_cpu",
        "CPU": "cpu",
        "minflt/s": "minflt_per_s",
        "majflt/s": "majflt_per_s",
        "VSZ": "vsz_kib",
        "RSS": "rss_kib",
        "%MEM": "pct_mem",
        "kB_rd/s": "kb_rd_per_s",
        "kB_wr/s": "kb_wr_per_s",
        "kB_ccwr/s": "kb_ccwr_per_s",
        "iodelay": "iodelay",
        "cswch/s": "cswch_per_s",
        "nvcswch/s": "nvcswch_per_s",
        "UID": "uid",
        "PID": "pid",
    }
    row: dict[str, Any] = {
        "sample_time": sample_time,
        "sample_kind": "interval",
        "command": command,
    }
    for header, raw in zip(header_fields, values, strict=True):
        normalized = field_map.get(header)
        if normalized is None:
            continue
        row[normalized] = _parse_number_maybe(raw)
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


def _parse_percent_maybe(raw: str) -> int | float | str:
    value = raw.strip().rstrip("%")
    return _parse_number_maybe(value)


def _parse_usage_pair(raw: str | None) -> tuple[float, float]:
    value = str(raw or "").strip()
    if not value or "/" not in value:
        return 0.0, 0.0
    left, right = [part.strip() for part in value.split("/", 1)]
    return _parse_size_to_bytes(left), _parse_size_to_bytes(right)


def _parse_size_to_bytes(raw: str) -> float:
    value = raw.strip()
    if not value:
        return 0.0
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)?$", value)
    if not match:
        return 0.0
    amount = float(match.group(1))
    unit = (match.group(2) or "B").strip()
    unit_multipliers = {
        "B": 1.0,
        "KB": 1000.0,
        "MB": 1000.0**2,
        "GB": 1000.0**3,
        "TB": 1000.0**4,
        "KIB": 1024.0,
        "MIB": 1024.0**2,
        "GIB": 1024.0**3,
        "TIB": 1024.0**4,
    }
    return amount * unit_multipliers.get(unit.upper(), 1.0)


def _normalize_metric_key(value: str) -> str:
    lowered = value.strip().lower().replace("%", "pct_")
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


def build_phase_resource_summary(
    *,
    output_dir: Path,
    rows: list[dict[str, Any]],
    concurrency: int,
) -> dict[str, Any] | None:
    if not rows:
        return None

    windows_by_phase = _build_phase_windows(rows)
    if not any(windows_by_phase.values()):
        return None

    metric_samples = _load_metric_samples(output_dir)
    if not metric_samples:
        return None

    alignment_mode = "exact_single_worker" if concurrency == 1 else "aggregate_overlap"
    phases_payload: dict[str, Any] = {}
    for phase, windows in windows_by_phase.items():
        metrics_payload: dict[str, Any] = {}
        for metric_name, samples in metric_samples.items():
            matched_values = [
                sample["value"]
                for sample in samples
                if any(window_start <= sample["timestamp"] <= window_end for window_start, window_end in windows)
            ]
            if matched_values:
                metrics_payload[metric_name] = summarize_ms(matched_values)
        phases_payload[phase] = {
            "window_count": len(windows),
            "metrics": metrics_payload,
        }

    return {
        "alignment_mode": alignment_mode,
        "concurrency": concurrency,
        "exact_phase_attribution": concurrency == 1,
        "notes": (
            "system samples are attributed precisely to non-overlapping single-worker phase windows"
            if concurrency == 1
            else "system samples are attributed to phase types when any overlapping worker is inside that phase; values are aggregate system load, not per-request exclusive cost"
        ),
        "phases": phases_payload,
    }


def _build_phase_windows(rows: list[dict[str, Any]]) -> dict[str, list[tuple[datetime, datetime]]]:
    phases = {
        "connect": ("connect_started_at", "connect_finished_at"),
        "send": ("send_started_at", "send_finished_at"),
        "wait": ("wait_started_at", "wait_finished_at"),
        "history": ("history_started_at", "history_finished_at"),
        "total": ("started_at", "finished_at"),
    }
    windows_by_phase: dict[str, list[tuple[datetime, datetime]]] = {phase: [] for phase in phases}
    for phase, (start_key, end_key) in phases.items():
        seen: set[tuple[str, str]] = set()
        for row in rows:
            start_raw = str(row.get(start_key, "")).strip()
            end_raw = str(row.get(end_key, "")).strip()
            if not start_raw or not end_raw:
                continue
            dedupe_key = (start_raw, end_raw)
            if phase == "connect" and dedupe_key in seen:
                continue
            start = _parse_iso_timestamp(start_raw)
            end = _parse_iso_timestamp(end_raw)
            if start is None or end is None or end < start:
                continue
            windows_by_phase[phase].append((start, end))
            seen.add(dedupe_key)
    return windows_by_phase


def _load_metric_samples(output_dir: Path) -> dict[str, list[dict[str, Any]]]:
    metric_samples: dict[str, list[dict[str, Any]]] = {}

    docker_stats_path = output_dir / "docker_stats.parsed.csv"
    if docker_stats_path.exists():
        for row in _read_csv_rows(docker_stats_path):
            timestamp = _parse_iso_timestamp(str(row.get("timestamp", "")))
            if timestamp is None:
                continue
            for field in (
                "cpu_percent_value",
                "mem_percent_value",
                "mem_usage_bytes",
                "block_read_bytes",
                "block_write_bytes",
                "net_rx_bytes",
                "net_tx_bytes",
                "pids_value",
            ):
                value = row.get(field)
                if isinstance(value, (int, float)):
                    metric_samples.setdefault(f"docker_stats.{field}", []).append(
                        {"timestamp": timestamp, "value": float(value)}
                    )

    for section_name in ("cpu", "memory", "io", "context_switch"):
        pidstat_path = output_dir / f"pidstat_{section_name}.csv"
        if not pidstat_path.exists():
            continue
        for row in _read_csv_rows(pidstat_path):
            timestamp = _parse_iso_timestamp(str(row.get("sample_timestamp", "")))
            if timestamp is None:
                continue
            for field, value in row.items():
                if field in {"sample_timestamp", "sample_time", "sample_kind", "uid", "pid", "cpu", "command"}:
                    continue
                if isinstance(value, (int, float)):
                    metric_samples.setdefault(f"pidstat.{section_name}.{field}", []).append(
                        {"timestamp": timestamp, "value": float(value)}
                    )

    iostat_summary_path = output_dir / "iostat.summary.json"
    busiest_device = ""
    if iostat_summary_path.exists():
        summary = _read_json(iostat_summary_path)
        busiest_device = str(summary.get("busiest_device_by_util_mean", "")).strip()
    iostat_path = output_dir / "iostat.parsed.csv"
    if iostat_path.exists():
        for row in _read_csv_rows(iostat_path):
            if busiest_device and str(row.get("device", "")).strip() != busiest_device:
                continue
            timestamp = _parse_iso_timestamp(str(row.get("sample_timestamp", "")))
            if timestamp is None:
                continue
            for field, value in row.items():
                if field in {"sample_timestamp", "device"}:
                    continue
                if isinstance(value, (int, float)):
                    metric_samples.setdefault(f"iostat.{field}", []).append(
                        {"timestamp": timestamp, "value": float(value)}
                    )

    perf_stat_path = output_dir / "perf_stat.parsed.csv"
    if perf_stat_path.exists():
        for row in _read_csv_rows(perf_stat_path):
            timestamp = _parse_iso_timestamp(str(row.get("sample_timestamp", "")))
            event = _normalize_metric_key(str(row.get("event", "")))
            value = row.get("counter_value")
            if timestamp is None or not event or not isinstance(value, (int, float)):
                continue
            metric_samples.setdefault(f"perf_stat.{event}", []).append(
                {"timestamp": timestamp, "value": float(value)}
            )

    return metric_samples


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            parsed: dict[str, Any] = {}
            for key, value in raw_row.items():
                parsed[str(key)] = _parse_number_maybe(str(value)) if value is not None else ""
            rows.append(parsed)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso_timestamp(raw: str) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _resolve_pidstat_sample_timestamp(
    sample_time: str,
    *,
    run_started: datetime | None,
    last_sample_timestamp: datetime | None,
) -> datetime | None:
    if sample_time in {"", "Average"} or run_started is None:
        return None
    for fmt in ("%H:%M:%S", "%I:%M:%S %p"):
        try:
            parsed_time = datetime.strptime(sample_time, fmt).time()
            break
        except ValueError:
            parsed_time = None
    if parsed_time is None:
        return None
    candidate = run_started.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=parsed_time.second,
        microsecond=0,
    )
    if last_sample_timestamp is not None and candidate < last_sample_timestamp:
        candidate = candidate + timedelta(days=1)
    return candidate


def _resolve_perf_stat_timestamp(raw: str, *, run_started: datetime | None) -> datetime | None:
    if run_started is None:
        return None
    value = _parse_number_maybe(raw)
    if not isinstance(value, (int, float)):
        return None
    return run_started + timedelta(seconds=float(value))


def _parse_iostat_timestamp_line(raw: str, *, run_started: datetime | None) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=run_started.tzinfo if run_started is not None else None)
        except ValueError:
            continue
    return None


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
