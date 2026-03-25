from __future__ import annotations

import csv
from dataclasses import dataclass
import re
from pathlib import Path
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

    iostat = by_name.get("iostat")
    iostat_log = output_dir / "iostat.log"
    if iostat is not None and iostat_log.exists():
        parsed = parse_iostat_log(iostat_log, output_dir=output_dir)
        if parsed is not None:
            iostat.status.files.extend(path for path in parsed.files if path not in iostat.status.files)
            analyses[parsed.name] = parsed.summary

    vmstat = by_name.get("vmstat")
    vmstat_log = output_dir / "vmstat.log"
    if vmstat is not None and vmstat_log.exists():
        parsed = parse_vmstat_log(vmstat_log, output_dir=output_dir)
        if parsed is not None:
            vmstat.status.files.extend(path for path in parsed.files if path not in vmstat.status.files)
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


def parse_pidstat_log(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    current_section: _PidstatSection | None = None
    rows_by_section: dict[str, list[dict[str, Any]]] = {section.name: [] for section in PIDSTAT_SECTIONS}
    combined_header: list[str] | None = None

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
                for section in PIDSTAT_SECTIONS:
                    section_row = {
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
        if current_section is None or tokens[0] == "UID":
            continue
        row = _parse_pidstat_row(tokens, sample_time=sample_time, sample_kind=sample_kind, section=current_section)
        if row is not None:
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
            if not any(cells) or cells[0].startswith("#"):
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
        "metrics": {
            event: _summarize_numeric(
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
                "timestamp": row["timestamp"],
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
        "key_metrics": {
            "cache_misses": _summarize_numeric(
                [
                    float(row["counter_value"])
                    for row in rows
                    if row.get("event") == "cache-misses" and isinstance(row.get("counter_value"), (int, float))
                ]
            ),
            "context_switches": _summarize_numeric(
                [
                    float(row["counter_value"])
                    for row in rows
                    if row.get("event") == "context-switches" and isinstance(row.get("counter_value"), (int, float))
                ]
            ),
            "cpu_migrations": _summarize_numeric(
                [
                    float(row["counter_value"])
                    for row in rows
                    if row.get("event") == "cpu-migrations" and isinstance(row.get("counter_value"), (int, float))
                ]
            ),
            "page_faults": _summarize_numeric(
                [
                    float(row["counter_value"])
                    for row in rows
                    if row.get("event") == "page-faults" and isinstance(row.get("counter_value"), (int, float))
                ]
            ),
        },
        "unsupported_events": sorted(
            {
                str(row["event"])
                for row in rows
                if isinstance(row.get("counter_value"), str) and row.get("counter_value") == "<not supported>"
            }
        ),
    }
    summary_path = output_dir / "perf_stat.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="perf_stat", files=[str(parsed_path), str(summary_path)], summary=summary)


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


def parse_iostat_log(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    current_header: list[str] | None = None

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("Linux "):
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
        rows.append(row)

    if not rows:
        return None

    parsed_path = output_dir / "iostat.parsed.csv"
    _write_csv(parsed_path, rows)

    metric_names = [key for key in rows[0].keys() if key != "device"]
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
        "key_metrics": {
            "busiest_device": busiest_device,
            "pct_util": devices_summary.get(busiest_device, {}).get("metrics", {}).get("pct_util", {}),
            "await": devices_summary.get(busiest_device, {}).get("metrics", {}).get("await", {}),
            "r_await": devices_summary.get(busiest_device, {}).get("metrics", {}).get("r_await", {}),
            "w_await": devices_summary.get(busiest_device, {}).get("metrics", {}).get("w_await", {}),
            "aqu_sz": devices_summary.get(busiest_device, {}).get("metrics", {}).get("aqu_sz", {}),
            "wkb_s": devices_summary.get(busiest_device, {}).get("metrics", {}).get("wkb_s", {}),
        },
    }
    summary_path = output_dir / "iostat.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="iostat", files=[str(parsed_path), str(summary_path)], summary=summary)


def parse_vmstat_log(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    header: list[str] | None = None

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("procs ") or stripped.startswith("procs\t"):
            continue
        if stripped.startswith("r ") or stripped.startswith("r\t"):
            header = stripped.split()
            continue
        if header is None:
            continue
        tokens = stripped.split()
        if len(tokens) != len(header):
            continue
        row = {
            _normalize_metric_key(key): _parse_number_maybe(value)
            for key, value in zip(header, tokens, strict=True)
        }
        rows.append(row)

    if not rows:
        return None

    parsed_path = output_dir / "vmstat.parsed.csv"
    _write_csv(parsed_path, rows)

    metric_names = [key for key in rows[0].keys()]
    summary = {
        "raw_log": str(path),
        "rows": len(rows),
        "metrics": {
            metric: _summarize_numeric(
                [float(row[metric]) for row in rows if isinstance(row.get(metric), (int, float))]
            )
            for metric in metric_names
        },
        "key_metrics": {
            "interrupts_per_s": _summarize_numeric(
                [float(row["in"]) for row in rows if isinstance(row.get("in"), (int, float))]
            ),
            "context_switches_per_s": _summarize_numeric(
                [float(row["cs"]) for row in rows if isinstance(row.get("cs"), (int, float))]
            ),
            "blocked_processes": _summarize_numeric(
                [float(row["b"]) for row in rows if isinstance(row.get("b"), (int, float))]
            ),
            "run_queue": _summarize_numeric(
                [float(row["r"]) for row in rows if isinstance(row.get("r"), (int, float))]
            ),
        },
    }
    summary_path = output_dir / "vmstat.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="vmstat", files=[str(parsed_path), str(summary_path)], summary=summary)


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
        if normalized is not None:
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
    return _parse_number_maybe(raw.strip().rstrip("%"))


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
