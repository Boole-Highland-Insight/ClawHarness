from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import json
import math
import re
from pathlib import Path
from statistics import fmean
import subprocess
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


DOCKER_METRIC_META = {
    "cpu_percent_value": {"unit": "percent", "source_field": "cpu_percent"},
    "mem_percent_value": {"unit": "percent", "source_field": "mem_percent"},
    "pids_value": {"unit": "count", "source_field": "pids"},
    "mem_usage_bytes": {"unit": "bytes", "source_field": "mem_usage_limit.left"},
    "mem_limit_bytes": {"unit": "bytes", "source_field": "mem_usage_limit.right"},
    "net_rx_bytes_per_s": {"unit": "bytes/sec", "source_field": "delta(net_io.left)/elapsed_sec"},
    "net_tx_bytes_per_s": {"unit": "bytes/sec", "source_field": "delta(net_io.right)/elapsed_sec"},
    "block_read_bytes_per_s": {"unit": "bytes/sec", "source_field": "delta(block_io.left)/elapsed_sec"},
    "block_write_bytes_per_s": {"unit": "bytes/sec", "source_field": "delta(block_io.right)/elapsed_sec"},
}

PIDSTAT_METRIC_META = {
    "pct_usr": {"unit": "percent"},
    "pct_system": {"unit": "percent"},
    "pct_guest": {"unit": "percent"},
    "pct_wait": {"unit": "percent"},
    "pct_cpu": {"unit": "percent"},
    "minflt_per_s": {"unit": "faults/sec"},
    "majflt_per_s": {"unit": "faults/sec"},
    "vsz_kib": {"unit": "KiB"},
    "rss_kib": {"unit": "KiB"},
    "pct_mem": {"unit": "percent"},
    "kb_rd_per_s": {"unit": "KiB/sec"},
    "kb_wr_per_s": {"unit": "KiB/sec"},
    "kb_ccwr_per_s": {"unit": "KiB/sec"},
    "iodelay": {"unit": "ticks"},
    "cswch_per_s": {"unit": "switches/sec"},
    "nvcswch_per_s": {"unit": "switches/sec"},
}

IOSTAT_METRIC_META = {
    "r_s": {"unit": "ops/sec"},
    "w_s": {"unit": "ops/sec"},
    "rkb_s": {"unit": "KiB/sec"},
    "wkb_s": {"unit": "KiB/sec"},
    "r_await": {"unit": "ms"},
    "w_await": {"unit": "ms"},
    "f_await": {"unit": "ms"},
    "aqu_sz": {"unit": "requests"},
    "pct_util": {"unit": "percent"},
}

VMSTAT_METRIC_META = {
    "r": {"unit": "processes"},
    "b": {"unit": "processes"},
    "in": {"unit": "interrupts/sec"},
    "cs": {"unit": "switches/sec"},
}

PERF_EVENT_UNITS = {
    "cache-misses": "events/sec",
    "cache-references": "events/sec",
    "context-switches": "events/sec",
    "cpu-migrations": "events/sec",
    "page-faults": "events/sec",
    "minor-faults": "events/sec",
    "major-faults": "events/sec",
    "cpu-clock": "CPUs utilized",
    "task-clock": "CPUs utilized",
}


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

    strace = by_name.get("strace")
    strace_log = output_dir / "strace.log"
    if strace is not None and strace_log.exists():
        parsed = parse_strace_log(strace_log, output_dir=output_dir)
        if parsed is not None:
            strace.status.files.extend(path for path in parsed.files if path not in strace.status.files)
            analyses[parsed.name] = parsed.summary

    node_trace = by_name.get("node_trace")
    node_trace_paths = sorted((output_dir / "runtime" / "workspace").glob("node-trace*.json"))
    if node_trace is not None and node_trace_paths:
        parsed = parse_node_trace_files(node_trace_paths, output_dir=output_dir)
        if parsed is not None:
            node_trace.status.files.extend(path for path in parsed.files if path not in node_trace.status.files)
            analyses[parsed.name] = parsed.summary

    gateway_log = output_dir / "runtime" / "docker-logs.txt"
    if gateway_log.exists():
        parsed = parse_gateway_runtime_log(gateway_log, output_dir=output_dir)
        if parsed is not None:
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
    previous_row: dict[str, Any] | None = None
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
            row = {
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
            _add_cumulative_rate_fields(row=row, previous_row=previous_row)
            rows.append(row)
            previous_row = row

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
        "net_rx_bytes_per_s",
        "net_tx_bytes_per_s",
        "block_read_bytes_per_s",
        "block_write_bytes_per_s",
    )
    metrics = {
        field: summarize_ms(
            [float(row[field]) for row in rows if isinstance(row.get(field), (int, float))]
        )
        for field in numeric_fields
    }
    summary = {
        "raw_csv": str(path),
        "rows": len(rows),
        "container": next((str(row["container"]) for row in rows if row.get("container")), ""),
        "metrics": metrics,
        "metric_summaries": {
            field: _metric_summary_entry(summary=metrics[field], **DOCKER_METRIC_META[field])
            for field in numeric_fields
        },
        "time_series": {
            field: _numeric_time_series_entry(
                rows=rows,
                value_field=field,
                unit=DOCKER_METRIC_META.get(field, {}).get("unit", ""),
                source_field=DOCKER_METRIC_META.get(field, {}).get("source_field", field),
                timestamp_field="timestamp",
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
        section_summaries[section.name]["metric_summaries"] = {
            field: _metric_summary_entry(
                summary=section_summaries[section.name]["metrics"][field],
                unit=PIDSTAT_METRIC_META.get(field, {}).get("unit", ""),
                source_field=field,
            )
            for field in section.numeric_fields
        }
        section_summaries[section.name]["time_series"] = {
            field: _numeric_time_series_entry(
                rows=rows,
                value_field=field,
                unit=PIDSTAT_METRIC_META.get(field, {}).get("unit", ""),
                source_field=field,
                index_step_sec=1.0,
            )
            for field in section.numeric_fields
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

    metrics = {
        event: _summarize_present_numeric(
            [
                float(row["metric_value"])
                for row in rows
                if row.get("event") == event and isinstance(row.get("metric_value"), (int, float))
            ]
        )
        for event in sorted({str(row["event"]) for row in rows if row.get("event")})
    }
    key_metrics = {
        "cache_misses": _summarize_present_numeric(
            [
                float(row["metric_value"])
                for row in rows
                if row.get("event") == "cache-misses" and isinstance(row.get("metric_value"), (int, float))
            ]
        ),
        "context_switches": _summarize_present_numeric(
            [
                float(row["metric_value"])
                for row in rows
                if row.get("event") == "context-switches" and isinstance(row.get("metric_value"), (int, float))
            ]
        ),
        "cpu_migrations": _summarize_present_numeric(
            [
                float(row["metric_value"])
                for row in rows
                if row.get("event") == "cpu-migrations" and isinstance(row.get("metric_value"), (int, float))
            ]
        ),
        "page_faults": _summarize_present_numeric(
            [
                float(row["metric_value"])
                for row in rows
                if row.get("event") == "page-faults" and isinstance(row.get("metric_value"), (int, float))
            ]
        ),
    }
    summary = {
        "raw_csv": str(path),
        "rows": len(rows),
        "metrics": metrics,
        "metric_summaries": {
            event: _metric_summary_entry(
                summary=metric_summary,
                unit=_infer_perf_metric_unit(rows=rows, event=event),
                source_field="metric_value",
            )
            for event, metric_summary in metrics.items()
        },
        "time_series": {
            event: _numeric_time_series_entry(
                rows=[row for row in rows if row.get("event") == event],
                value_field="metric_value",
                unit=_infer_perf_metric_unit(rows=rows, event=event),
                source_field="metric_value",
                elapsed_field="timestamp_sec",
            )
            for event in metrics
        },
        "events": [
            {
                "timestamp": row["timestamp"],
                "timestamp_sec": row["timestamp_sec"],
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
        "key_metrics": key_metrics,
        "key_metric_summaries": {
            "cache_misses": _metric_summary_entry(
                summary=key_metrics["cache_misses"],
                unit=_infer_perf_metric_unit(rows=rows, event="cache-misses"),
                source_field="metric_value",
            ),
            "context_switches": _metric_summary_entry(
                summary=key_metrics["context_switches"],
                unit=_infer_perf_metric_unit(rows=rows, event="context-switches"),
                source_field="metric_value",
            ),
            "cpu_migrations": _metric_summary_entry(
                summary=key_metrics["cpu_migrations"],
                unit=_infer_perf_metric_unit(rows=rows, event="cpu-migrations"),
                source_field="metric_value",
            ),
            "page_faults": _metric_summary_entry(
                summary=key_metrics["page_faults"],
                unit=_infer_perf_metric_unit(rows=rows, event="page-faults"),
                source_field="metric_value",
            ),
        },
        "key_time_series": {
            "cache_misses": _numeric_time_series_entry(
                rows=[row for row in rows if row.get("event") == "cache-misses"],
                value_field="metric_value",
                unit=_infer_perf_metric_unit(rows=rows, event="cache-misses"),
                source_field="metric_value",
                elapsed_field="timestamp_sec",
            ),
            "context_switches": _numeric_time_series_entry(
                rows=[row for row in rows if row.get("event") == "context-switches"],
                value_field="metric_value",
                unit=_infer_perf_metric_unit(rows=rows, event="context-switches"),
                source_field="metric_value",
                elapsed_field="timestamp_sec",
            ),
            "cpu_migrations": _numeric_time_series_entry(
                rows=[row for row in rows if row.get("event") == "cpu-migrations"],
                value_field="metric_value",
                unit=_infer_perf_metric_unit(rows=rows, event="cpu-migrations"),
                source_field="metric_value",
                elapsed_field="timestamp_sec",
            ),
            "page_faults": _numeric_time_series_entry(
                rows=[row for row in rows if row.get("event") == "page-faults"],
                value_field="metric_value",
                unit=_infer_perf_metric_unit(rows=rows, event="page-faults"),
                source_field="metric_value",
                elapsed_field="timestamp_sec",
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
    runtime_samples = _summarize_perf_record_runtime_samples(perf_data=perf_data)
    if runtime_samples:
        summary["runtime_samples"] = runtime_samples
    summary_path = output_dir / "perf_record.summary.json"
    write_json(summary_path, summary)
    files = [str(summary_path)]
    if perf_data.exists():
        files.append(str(perf_data))
    if perf_log.exists():
        files.append(str(perf_log))
    return ParsedArtifact(name="perf_record", files=files, summary=summary)


def _summarize_perf_record_runtime_samples(*, perf_data: Path) -> dict[str, Any]:
    if not perf_data.exists():
        return {}
    try:
        proc = subprocess.Popen(
            ["perf", "script", "-i", str(perf_data)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return {}

    category_counts: dict[str, int] = {}
    category_examples: dict[str, list[str]] = {}
    thread_counts: dict[str, int] = {}
    sample_count = 0

    header: str | None = None
    stack_lines: list[str] = []

    def flush_sample() -> None:
        nonlocal header, stack_lines, sample_count
        if header is None:
            return
        sample_count += 1
        thread_name = _perf_script_thread_name(header)
        thread_counts[thread_name] = thread_counts.get(thread_name, 0) + 1
        category = _classify_perf_runtime_sample(header=header, stack_lines=stack_lines)
        category_counts[category] = category_counts.get(category, 0) + 1
        if len(category_examples.setdefault(category, [])) < 3:
            category_examples[category].append(_perf_sample_example(header=header, stack_lines=stack_lines))
        header = None
        stack_lines = []

    assert proc.stdout is not None
    for raw_line in proc.stdout:
        line = raw_line.rstrip("\n")
        if not line.strip():
            flush_sample()
            continue
        if not line.startswith("\t") and not line.startswith(" "):
            flush_sample()
            header = line
            stack_lines = []
            continue
        if header is not None:
            stack_lines.append(line.strip())
    flush_sample()
    _stdout, stderr = proc.communicate()
    if proc.returncode not in {0, None}:
        return {"error": stderr.strip() or "perf script failed"}
    if sample_count <= 0:
        return {}

    categories = {
        name: {
            "count": count,
            "pct": (float(count) / float(sample_count)) * 100.0,
            "examples": category_examples.get(name, []),
        }
        for name, count in sorted(category_counts.items(), key=lambda item: item[1], reverse=True)
    }
    top_threads = [
        {"thread": name, "count": count, "pct": (float(count) / float(sample_count)) * 100.0}
        for name, count in sorted(thread_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    return {
        "sample_count": sample_count,
        "categories": categories,
        "top_threads": top_threads,
    }


def parse_strace_log(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        row = _parse_strace_line(raw_line)
        if row is not None:
            rows.append(row)

    if not rows:
        return None

    base_t_sec = min(float(row["t_sec"]) for row in rows if isinstance(row.get("t_sec"), (int, float)))
    for row in rows:
        if isinstance(row.get("t_sec"), (int, float)):
            row["t_sec"] = float(row["t_sec"]) - base_t_sec

    parsed_path = output_dir / "strace.parsed.csv"
    _write_csv(parsed_path, rows)

    by_syscall: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        syscall = str(row.get("syscall", "")).strip()
        if syscall:
            by_syscall.setdefault(syscall, []).append(row)

    syscall_summary: dict[str, Any] = {}
    for syscall, syscall_rows in by_syscall.items():
        durations_sec = [
            float(row["duration_sec"])
            for row in syscall_rows
            if isinstance(row.get("duration_sec"), (int, float))
        ]
        duration_summary = _summarize_present_numeric(durations_sec)
        duration_ms_summary = (
            summarize_ms([duration * 1000.0 for duration in durations_sec]) if durations_sec else {}
        )
        syscall_summary[syscall] = {
            "count": len(syscall_rows),
            "duration_sec": duration_summary,
            "duration_ms": duration_ms_summary,
        }

    top_by_total_duration = sorted(
        (
            {
                "syscall": syscall,
                "count": details["count"],
                "total_duration_sec": sum(
                    float(row["duration_sec"])
                    for row in by_syscall.get(syscall, [])
                    if isinstance(row.get("duration_sec"), (int, float))
                ),
            }
            for syscall, details in syscall_summary.items()
        ),
        key=lambda item: item["total_duration_sec"],
        reverse=True,
    )[:10]

    bucket_counts: dict[int, float] = {}
    bucket_duration_ms: dict[int, float] = {}
    for row in rows:
        t_sec = row.get("t_sec")
        duration_sec = row.get("duration_sec")
        if not isinstance(t_sec, (int, float)):
            continue
        bucket = int(math.floor(float(t_sec)))
        bucket_counts[bucket] = bucket_counts.get(bucket, 0.0) + 1.0
        if isinstance(duration_sec, (int, float)):
            bucket_duration_ms[bucket] = bucket_duration_ms.get(bucket, 0.0) + (float(duration_sec) * 1000.0)

    summary = {
        "raw_log": str(path),
        "rows": len(rows),
        "syscalls": syscall_summary,
        "top_by_total_duration_sec": top_by_total_duration,
        "time_series": {
            "events_per_s": _bucket_time_series_entry(
                bucket_values=bucket_counts,
                unit="events/sec",
                source_field="count(events)",
            ),
            "duration_ms_per_s": _bucket_time_series_entry(
                bucket_values=bucket_duration_ms,
                unit="ms/sec",
                source_field="sum(duration_sec)*1000",
            ),
        },
    }
    summary_path = output_dir / "strace.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="strace", files=[str(parsed_path), str(summary_path)], summary=summary)


def parse_node_trace_files(paths: list[Path], *, output_dir: Path) -> ParsedArtifact | None:
    raw_events: list[dict[str, Any]] = []
    for path in paths:
        payloads = _load_node_trace_payloads(path)
        for payload in payloads:
            if not _is_gateway_trace_payload(payload):
                continue
            trace_events = payload.get("traceEvents") if isinstance(payload, dict) else None
            if not isinstance(trace_events, list):
                continue
            for event in trace_events:
                if isinstance(event, dict):
                    event = dict(event)
                    event["_source_file"] = str(path)
                    raw_events.append(event)

    if not raw_events:
        return None

    completed_events = _complete_node_trace_events(raw_events)
    if not completed_events:
        return None

    base_ts_us = min(float(event["ts_us"]) for event in completed_events)
    rows: list[dict[str, Any]] = []
    fs_by_op: dict[str, list[dict[str, Any]]] = {}
    path_count: dict[str, int] = {}
    path_duration_ms: dict[str, float] = {}
    category_count: dict[str, int] = {}
    category_duration_ms: dict[str, float] = {}
    runtime_groups = {
        "fs_async": {"events_per_s": {}, "duration_ms_per_s": {}},
        "fs_callback": {"events_per_s": {}, "duration_ms_per_s": {}},
        "promise_callback": {"events_per_s": {}, "duration_ms_per_s": {}},
        "event_loop": {"events_per_s": {}, "duration_ms_per_s": {}},
    }

    for event in completed_events:
        t_sec = (float(event["ts_us"]) - base_ts_us) / 1_000_000.0
        duration_ms = float(event["duration_us"]) / 1000.0
        row = {
            "t_sec": t_sec,
            "pid": event.get("pid"),
            "tid": event.get("tid"),
            "category": event.get("cat", ""),
            "name": event.get("name", ""),
            "duration_ms": duration_ms,
            "path": event.get("path", ""),
            "result": event.get("result"),
            "source_file": event.get("_source_file", ""),
        }
        rows.append(row)

        bucket = int(math.floor(t_sec))
        group = _node_trace_runtime_group(event)
        if group:
            runtime_groups[group]["events_per_s"][bucket] = runtime_groups[group]["events_per_s"].get(bucket, 0.0) + 1.0
            runtime_groups[group]["duration_ms_per_s"][bucket] = (
                runtime_groups[group]["duration_ms_per_s"].get(bucket, 0.0) + duration_ms
            )

        if _is_node_fs_async_event(event):
            op = str(event.get("name", "")).strip()
            fs_by_op.setdefault(op, []).append(row)
            path = str(event.get("path", "")).strip()
            if path:
                path_count[path] = path_count.get(path, 0) + 1
                path_duration_ms[path] = path_duration_ms.get(path, 0.0) + duration_ms
                category = _classify_trace_path(path)
                category_count[category] = category_count.get(category, 0) + 1
                category_duration_ms[category] = category_duration_ms.get(category, 0.0) + duration_ms

    parsed_path = output_dir / "node_trace.parsed.csv"
    _write_csv(parsed_path, rows)

    fs_async_rows = [row for row in rows if _row_matches_name(row, _is_node_fs_async_name)]
    fs_callback_rows = [row for row in rows if row.get("name") == "FSREQCALLBACK_CALLBACK"]
    promise_rows = [row for row in rows if row.get("name") == "PROMISE_CALLBACK"]
    immediate_rows = [row for row in rows if row.get("name") in {"CheckImmediate", "RunAndClearNativeImmediates"}]
    timer_rows = [row for row in rows if row.get("name") == "RunTimers"]

    key_metrics = {
        "fs_async_duration_ms": summarize_ms([float(row["duration_ms"]) for row in fs_async_rows]),
        "fs_callback_duration_ms": summarize_ms([float(row["duration_ms"]) for row in fs_callback_rows]),
        "promise_callback_duration_ms": summarize_ms([float(row["duration_ms"]) for row in promise_rows]),
        "event_loop_immediate_duration_ms": summarize_ms([float(row["duration_ms"]) for row in immediate_rows]),
        "event_loop_timers_duration_ms": summarize_ms([float(row["duration_ms"]) for row in timer_rows]),
    }
    key_counts = {
        "fs_async_count": float(len(fs_async_rows)),
        "fs_callback_count": float(len(fs_callback_rows)),
        "promise_callback_count": float(len(promise_rows)),
        "event_loop_immediate_count": float(len(immediate_rows)),
        "event_loop_timers_count": float(len(timer_rows)),
    }

    fs_ops = {
        op: {
            "count": len(op_rows),
            "duration_ms": summarize_ms([float(row["duration_ms"]) for row in op_rows]),
        }
        for op, op_rows in sorted(fs_by_op.items(), key=lambda item: len(item[1]), reverse=True)
    }

    top_paths_by_count = [
        {"path": path, "count": count, "total_duration_ms": path_duration_ms.get(path, 0.0)}
        for path, count in sorted(path_count.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    top_paths_by_duration = [
        {"path": path, "count": path_count.get(path, 0), "total_duration_ms": total_duration_ms}
        for path, total_duration_ms in sorted(path_duration_ms.items(), key=lambda item: item[1], reverse=True)[:10]
    ]
    path_categories = {
        category: {
            "count": count,
            "total_duration_ms": category_duration_ms.get(category, 0.0),
        }
        for category, count in sorted(category_count.items(), key=lambda item: item[1], reverse=True)
    }
    focus_groups = _node_trace_focus_groups(path_count=path_count, path_duration_ms=path_duration_ms)

    summary = {
        "files": [str(path) for path in paths],
        "raw_events": len(raw_events),
        "completed_events": len(rows),
        "key_metrics": key_metrics,
        "key_metric_summaries": {
            key: _metric_summary_entry(summary=value, unit="ms", source_field="trace_event.duration_us/1000")
            for key, value in key_metrics.items()
        },
        "key_counts": key_counts,
        "fs_ops": fs_ops,
        "path_hotspots": {
            "top_by_count": top_paths_by_count,
            "top_by_total_duration_ms": top_paths_by_duration,
            "categories": path_categories,
            "focus_groups": focus_groups,
        },
        "time_series": {
            "fs_async_events_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["fs_async"]["events_per_s"],
                unit="events/sec",
                source_field="node.fs.async count",
            ),
            "fs_async_duration_ms_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["fs_async"]["duration_ms_per_s"],
                unit="ms/sec",
                source_field="sum(node.fs.async duration_ms)",
            ),
            "fs_callback_events_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["fs_callback"]["events_per_s"],
                unit="events/sec",
                source_field="FSREQCALLBACK_CALLBACK count",
            ),
            "fs_callback_duration_ms_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["fs_callback"]["duration_ms_per_s"],
                unit="ms/sec",
                source_field="sum(FSREQCALLBACK_CALLBACK duration_ms)",
            ),
            "promise_callback_events_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["promise_callback"]["events_per_s"],
                unit="events/sec",
                source_field="PROMISE_CALLBACK count",
            ),
            "promise_callback_duration_ms_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["promise_callback"]["duration_ms_per_s"],
                unit="ms/sec",
                source_field="sum(PROMISE_CALLBACK duration_ms)",
            ),
            "event_loop_events_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["event_loop"]["events_per_s"],
                unit="events/sec",
                source_field="CheckImmediate/RunAndClearNativeImmediates/RunTimers count",
            ),
            "event_loop_duration_ms_per_s": _bucket_time_series_entry(
                bucket_values=runtime_groups["event_loop"]["duration_ms_per_s"],
                unit="ms/sec",
                source_field="sum(CheckImmediate/RunAndClearNativeImmediates/RunTimers duration_ms)",
            ),
        },
    }
    summary_path = output_dir / "node_trace.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(name="node_trace", files=[str(parsed_path), str(summary_path), *[str(path) for path in paths]], summary=summary)


def parse_gateway_runtime_log(path: Path, *, output_dir: Path) -> ParsedArtifact | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None

    events: list[dict[str, Any]] = []
    for stream_name in ("stdout", "stderr"):
        raw_stream = payload.get(stream_name)
        if not isinstance(raw_stream, str):
            continue
        for raw_line in raw_stream.splitlines():
            line = raw_line.strip()
            if not line.startswith("{") or '"event"' not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            record["_stream"] = stream_name
            events.append(record)

    if not events:
        return None

    rows = [
        {
            "stream": event.get("_stream", ""),
            "event": event.get("event", ""),
            "phase": event.get("phase", ""),
            "run_id": event.get("runId", ""),
            "session_key": event.get("sessionKey", ""),
            "ts": event.get("ts"),
            "duration_ms": event.get("durationMs"),
            "pending": event.get("pending"),
            "source": event.get("source", ""),
            "status": event.get("status", ""),
        }
        for event in events
    ]
    parsed_path = output_dir / "gateway_runtime_spans.parsed.csv"
    _write_csv(parsed_path, rows)

    embedded_phase_values: dict[str, list[float]] = {}
    embedded_by_run_phase: dict[str, dict[str, dict[str, Any]]] = {}
    wait_start_by_run: dict[str, float] = {}
    for event in events:
        event_name = event.get("event")
        phase = str(event.get("phase", "")).strip()
        run_id = str(event.get("runId", "")).strip()
        if event_name == "embedded_run_span":
            if run_id and phase:
                embedded_by_run_phase.setdefault(run_id, {})[phase] = event
            duration_ms = event.get("durationMs")
            if phase and isinstance(duration_ms, (int, float)):
                embedded_phase_values.setdefault(phase, []).append(float(duration_ms))
        elif event_name == "agent_wait_span" and phase == "wait_start" and run_id:
            ts = event.get("ts")
            if isinstance(ts, (int, float)):
                wait_start_by_run[run_id] = float(ts)

    reply_dispatch_by_run: dict[str, dict[str, dict[str, Any]]] = {}
    for event in events:
        if event.get("event") != "reply_dispatch_span":
            continue
        run_id = str(event.get("runId", "")).strip()
        phase = str(event.get("phase", "")).strip()
        ts = event.get("ts")
        if not run_id or not phase or not isinstance(ts, (int, float)):
            continue
        reply_dispatch_by_run.setdefault(run_id, {})[phase] = event

    queue_wait_ms: list[float] = []
    queue_hold_ms: list[float] = []
    queue_pending_at_enter: list[float] = []
    for phases in reply_dispatch_by_run.values():
        queue_enter = phases.get("queue_enter")
        queue_acquired = phases.get("queue_acquired")
        queue_idle = phases.get("queue_idle")
        if isinstance(queue_enter, dict):
            pending = queue_enter.get("pending")
            if isinstance(pending, (int, float)):
                queue_pending_at_enter.append(float(pending))
        if isinstance(queue_enter, dict) and isinstance(queue_acquired, dict):
            queue_wait_ms.append((float(queue_acquired["ts"]) - float(queue_enter["ts"])) / 1000.0)
        if isinstance(queue_acquired, dict) and isinstance(queue_idle, dict):
            queue_hold_ms.append((float(queue_idle["ts"]) - float(queue_acquired["ts"])) / 1000.0)

    execution_admission_wait_ms: list[float] = []
    for run_id, wait_start_ts in wait_start_by_run.items():
        reply_start = embedded_by_run_phase.get(run_id, {}).get("reply_start")
        if not isinstance(reply_start, dict):
            continue
        ts = reply_start.get("ts")
        if not isinstance(ts, (int, float)):
            continue
        execution_admission_wait_ms.append((float(ts) - float(wait_start_ts)) / 1000.0)

    key_metrics = {
        "bootstrap_load": _summarize_present_numeric(embedded_phase_values.get("bootstrap_load_end", [])),
        "skills": _summarize_present_numeric(
            embedded_phase_values.get("context_bundle_skills_end", [])
            or embedded_phase_values.get("skills_snapshot_end", [])
        ),
        "context_bundle": _summarize_present_numeric(embedded_phase_values.get("context_bundle_end", [])),
        "execution_admission_wait": _summarize_present_numeric(execution_admission_wait_ms),
        "reply_dispatch_queue_wait": _summarize_present_numeric(queue_wait_ms),
        "reply_dispatch_queue_hold": _summarize_present_numeric(queue_hold_ms),
        "reply_dispatch_pending": _summarize_present_numeric(queue_pending_at_enter),
    }

    summary = {
        "raw_log": str(path),
        "events": len(events),
        "embedded_phase_metrics": {
            phase: _summarize_present_numeric(values)
            for phase, values in sorted(embedded_phase_values.items())
            if values
        },
        "key_metrics": key_metrics,
        "key_metric_summaries": {
            key: _metric_summary_entry(
                summary=value,
                unit=("count" if key == "reply_dispatch_pending" else "ms"),
                source_field=key,
            )
            for key, value in key_metrics.items()
        },
    }
    summary_path = output_dir / "gateway_runtime_spans.summary.json"
    write_json(summary_path, summary)
    return ParsedArtifact(
        name="gateway_runtime_spans",
        files=[str(parsed_path), str(summary_path)],
        summary=summary,
    )


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

    metric_names = [key for key in rows[0].keys() if key not in {"device", "await"}]
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
            "metric_summaries": {
                metric: _metric_summary_entry(
                    summary=metrics[metric],
                    unit=IOSTAT_METRIC_META.get(metric, {}).get("unit", ""),
                    source_field=metric,
                )
                for metric in metric_names
            },
            "time_series": {
                metric: _numeric_time_series_entry(
                    rows=device_rows,
                    value_field=metric,
                    unit=IOSTAT_METRIC_META.get(metric, {}).get("unit", ""),
                    source_field=metric,
                    index_step_sec=1.0,
                )
                for metric in metric_names
            },
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
            "r_await": devices_summary.get(busiest_device, {}).get("metrics", {}).get("r_await", {}),
            "w_await": devices_summary.get(busiest_device, {}).get("metrics", {}).get("w_await", {}),
            "f_await": devices_summary.get(busiest_device, {}).get("metrics", {}).get("f_await", {}),
            "aqu_sz": devices_summary.get(busiest_device, {}).get("metrics", {}).get("aqu_sz", {}),
            "wkb_s": devices_summary.get(busiest_device, {}).get("metrics", {}).get("wkb_s", {}),
        },
        "key_metric_summaries": {
            "pct_util": _metric_summary_entry(
                summary=devices_summary.get(busiest_device, {}).get("metrics", {}).get("pct_util", {}),
                unit=IOSTAT_METRIC_META["pct_util"]["unit"],
                source_field="pct_util",
            ),
            "r_await": _metric_summary_entry(
                summary=devices_summary.get(busiest_device, {}).get("metrics", {}).get("r_await", {}),
                unit=IOSTAT_METRIC_META["r_await"]["unit"],
                source_field="r_await",
            ),
            "w_await": _metric_summary_entry(
                summary=devices_summary.get(busiest_device, {}).get("metrics", {}).get("w_await", {}),
                unit=IOSTAT_METRIC_META["w_await"]["unit"],
                source_field="w_await",
            ),
            "f_await": _metric_summary_entry(
                summary=devices_summary.get(busiest_device, {}).get("metrics", {}).get("f_await", {}),
                unit=IOSTAT_METRIC_META["f_await"]["unit"],
                source_field="f_await",
            ),
            "aqu_sz": _metric_summary_entry(
                summary=devices_summary.get(busiest_device, {}).get("metrics", {}).get("aqu_sz", {}),
                unit=IOSTAT_METRIC_META["aqu_sz"]["unit"],
                source_field="aqu_sz",
            ),
            "wkb_s": _metric_summary_entry(
                summary=devices_summary.get(busiest_device, {}).get("metrics", {}).get("wkb_s", {}),
                unit=IOSTAT_METRIC_META["wkb_s"]["unit"],
                source_field="wkb_s",
            ),
        },
        "key_time_series": {
            "pct_util": devices_summary.get(busiest_device, {}).get("time_series", {}).get("pct_util", {}),
            "r_await": devices_summary.get(busiest_device, {}).get("time_series", {}).get("r_await", {}),
            "w_await": devices_summary.get(busiest_device, {}).get("time_series", {}).get("w_await", {}),
            "f_await": devices_summary.get(busiest_device, {}).get("time_series", {}).get("f_await", {}),
            "aqu_sz": devices_summary.get(busiest_device, {}).get("time_series", {}).get("aqu_sz", {}),
            "wkb_s": devices_summary.get(busiest_device, {}).get("time_series", {}).get("wkb_s", {}),
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
    metrics = {
        metric: _summarize_numeric(
            [float(row[metric]) for row in rows if isinstance(row.get(metric), (int, float))]
        )
        for metric in metric_names
    }
    key_metrics = {
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
    }
    summary = {
        "raw_log": str(path),
        "rows": len(rows),
        "metrics": metrics,
        "metric_summaries": {
            metric: _metric_summary_entry(
                summary=metrics[metric],
                unit=VMSTAT_METRIC_META.get(metric, {}).get("unit", ""),
                source_field=metric,
            )
            for metric in metric_names
        },
        "time_series": {
            metric: _numeric_time_series_entry(
                rows=rows,
                value_field=metric,
                unit=VMSTAT_METRIC_META.get(metric, {}).get("unit", ""),
                source_field=metric,
                index_step_sec=1.0,
            )
            for metric in metric_names
        },
        "key_metrics": key_metrics,
        "key_metric_summaries": {
            "interrupts_per_s": _metric_summary_entry(
                summary=key_metrics["interrupts_per_s"],
                unit="interrupts/sec",
                source_field="in",
            ),
            "context_switches_per_s": _metric_summary_entry(
                summary=key_metrics["context_switches_per_s"],
                unit="switches/sec",
                source_field="cs",
            ),
            "blocked_processes": _metric_summary_entry(
                summary=key_metrics["blocked_processes"],
                unit="processes",
                source_field="b",
            ),
            "run_queue": _metric_summary_entry(
                summary=key_metrics["run_queue"],
                unit="processes",
                source_field="r",
            ),
        },
        "key_time_series": {
            "interrupts_per_s": _numeric_time_series_entry(
                rows=rows,
                value_field="in",
                unit="interrupts/sec",
                source_field="in",
                index_step_sec=1.0,
            ),
            "context_switches_per_s": _numeric_time_series_entry(
                rows=rows,
                value_field="cs",
                unit="switches/sec",
                source_field="cs",
                index_step_sec=1.0,
            ),
            "blocked_processes": _numeric_time_series_entry(
                rows=rows,
                value_field="b",
                unit="processes",
                source_field="b",
                index_step_sec=1.0,
            ),
            "run_queue": _numeric_time_series_entry(
                rows=rows,
                value_field="r",
                unit="processes",
                source_field="r",
                index_step_sec=1.0,
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
    sample_time, tokens = _extract_pidstat_tokens(line)
    if not tokens:
        return None
    header_fields = combined_header[1:-1]
    if len(tokens) < len(header_fields):
        return None
    values = tokens[: len(header_fields)]
    command = " ".join(tokens[len(header_fields) :])
    if not command:
        return None
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
        "timestamp_sec": _parse_number_maybe(timestamp),
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


def _add_cumulative_rate_fields(*, row: dict[str, Any], previous_row: dict[str, Any] | None) -> None:
    cumulative_pairs = (
        ("net_rx_bytes", "net_rx_bytes_per_s"),
        ("net_tx_bytes", "net_tx_bytes_per_s"),
        ("block_read_bytes", "block_read_bytes_per_s"),
        ("block_write_bytes", "block_write_bytes_per_s"),
    )
    if previous_row is None:
        for _source, target in cumulative_pairs:
            row[target] = ""
        return
    current_time = _parse_datetime_maybe(str(row.get("timestamp", "")))
    previous_time = _parse_datetime_maybe(str(previous_row.get("timestamp", "")))
    if current_time is None or previous_time is None:
        for _source, target in cumulative_pairs:
            row[target] = ""
        return
    elapsed = (current_time - previous_time).total_seconds()
    if elapsed <= 0:
        for _source, target in cumulative_pairs:
            row[target] = ""
        return
    for source, target in cumulative_pairs:
        current_value = row.get(source)
        previous_value = previous_row.get(source)
        if not isinstance(current_value, (int, float)) or not isinstance(previous_value, (int, float)):
            row[target] = ""
            continue
        delta = float(current_value) - float(previous_value)
        if delta < 0:
            row[target] = ""
            continue
        row[target] = delta / elapsed


def _parse_datetime_maybe(raw: str) -> datetime | None:
    value = raw.strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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


def _summarize_present_numeric(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    return _summarize_numeric(values)


def _metric_summary_entry(
    *,
    summary: dict[str, Any],
    unit: str,
    source_field: str,
) -> dict[str, Any]:
    return {
        "summary": summary,
        "unit": unit,
        "source_field": source_field,
    }


def _numeric_time_series_entry(
    *,
    rows: list[dict[str, Any]],
    value_field: str,
    unit: str,
    source_field: str,
    timestamp_field: str | None = None,
    elapsed_field: str | None = None,
    index_step_sec: float | None = None,
) -> dict[str, Any]:
    points: list[dict[str, float]] = []
    base_time: datetime | None = None
    for index, row in enumerate(rows):
        value = row.get(value_field)
        if not isinstance(value, (int, float)):
            continue
        t_sec: float | None = None
        if timestamp_field is not None:
            parsed_time = _parse_datetime_maybe(str(row.get(timestamp_field, "")))
            if parsed_time is not None:
                if base_time is None:
                    base_time = parsed_time
                t_sec = float((parsed_time - base_time).total_seconds())
        elif elapsed_field is not None:
            elapsed = row.get(elapsed_field)
            if isinstance(elapsed, (int, float)):
                t_sec = float(elapsed)
        elif index_step_sec is not None:
            t_sec = float(index) * index_step_sec
        if t_sec is None:
            continue
        points.append({"t_sec": t_sec, "value": float(value)})
    return _time_series_entry(points=points, unit=unit, source_field=source_field)


def _bucket_time_series_entry(
    *,
    bucket_values: dict[int, float],
    unit: str,
    source_field: str,
) -> dict[str, Any]:
    points = [
        {"t_sec": float(bucket), "value": float(value)}
        for bucket, value in sorted(bucket_values.items(), key=lambda item: item[0])
    ]
    return _time_series_entry(points=points, unit=unit, source_field=source_field)


def _time_series_entry(*, points: list[dict[str, float]], unit: str, source_field: str) -> dict[str, Any]:
    peak = _peak_from_points(points)
    return {
        "points": points,
        "peak": peak,
        "unit": unit,
        "source_field": source_field,
    }


def _peak_from_points(points: list[dict[str, float]]) -> dict[str, float]:
    if not points:
        return {}
    peak_point = max(points, key=lambda point: float(point.get("value", float("-inf"))))
    return {
        "t_sec": float(peak_point["t_sec"]),
        "value": float(peak_point["value"]),
    }


def _infer_perf_metric_unit(*, rows: list[dict[str, Any]], event: str) -> str:
    for row in rows:
        if row.get("event") != event:
            continue
        unit = str(row.get("metric_unit", "")).strip()
        if unit:
            return unit
    return PERF_EVENT_UNITS.get(event, "")


def _parse_strace_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("strace:"):
        return None
    if "strace: Process" in stripped:
        stripped = stripped.split("strace: Process", 1)[0].rstrip()
    if not stripped:
        return None
    if "unfinished ..." in stripped or "<... " in stripped and " resumed>" in stripped:
        if "<... " not in stripped or " resumed>" not in stripped:
            return None
    duration_match = re.search(r"<([0-9]+(?:\.[0-9]+)?)>\s*$", stripped)
    if duration_match is None:
        return None
    timestamp_match = re.match(
        r"^(?:(?:\[pid\s+)?(?P<pid>\d+)\]?\s+)?(?P<ts>\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s+(?P<body>.+?)\s*<(?P<duration>[0-9]+(?:\.[0-9]+)?)>\s*$",
        stripped,
    )
    if timestamp_match is None:
        return None
    body = timestamp_match.group("body").strip()
    if body.startswith("---") or body.startswith("+++"):
        return None
    syscall_match = re.match(
        r"(?:(?P<normal>[a-zA-Z0-9_]+)\(|<\.\.\.\s+(?P<resumed>[a-zA-Z0-9_]+)\s+resumed>\))",
        body,
    )
    syscall = ""
    if syscall_match is not None:
        syscall = str(syscall_match.group("normal") or syscall_match.group("resumed") or "")
    if not syscall:
        return None
    timestamp_text = timestamp_match.group("ts")
    duration_sec = float(timestamp_match.group("duration"))
    t_sec = _parse_hhmmss_to_seconds(timestamp_text)
    return {
        "pid": _parse_number_maybe(timestamp_match.group("pid") or ""),
        "timestamp": timestamp_text,
        "t_sec": t_sec,
        "syscall": syscall,
        "duration_sec": duration_sec,
        "duration_ms": duration_sec * 1000.0,
        "raw_line": stripped,
    }


def _parse_hhmmss_to_seconds(value: str) -> float:
    hour_text, minute_text, second_text = value.split(":", 2)
    return (int(hour_text) * 3600.0) + (int(minute_text) * 60.0) + float(second_text)


def _perf_script_thread_name(header: str) -> str:
    stripped = header.strip()
    if not stripped:
        return "unknown"
    return stripped.split()[0]


def _perf_sample_example(*, header: str, stack_lines: list[str]) -> str:
    symbols = [_perf_symbol_from_stack_line(line) for line in stack_lines[:4]]
    symbols = [symbol for symbol in symbols if symbol]
    if not symbols:
        return header.strip()
    return f"{header.strip()} :: {' -> '.join(symbols[:4])}"


def _classify_perf_runtime_sample(*, header: str, stack_lines: list[str]) -> str:
    thread_name = _perf_script_thread_name(header).lower()
    stack_text = "\n".join(stack_lines).lower()

    if any(marker in stack_text for marker in ("microtaskqueue", "tryrunmicrotasks", "performcheckpoint")):
        return "microtask"
    if any(marker in stack_text for marker in ("uv__io_poll", "do_epoll_wait", "epoll_pwait", "spin_event_loopinternal")):
        return "event_loop_poll"
    if any(marker in stack_text for marker in ("uv__work_done", "node::fs::after", "fsreqpromise", "readfileutf8")):
        return "fs_callback"
    if thread_name.startswith("libuv-worker") and any(
        marker in stack_text for marker in ("uv__fs_work", "uv_fs_lstat", "uv__fs_statx", "uv_fs_read")
    ):
        return "fs_worker_exec"
    if any(marker in stack_text for marker in ("do_futex", "futex_wake", "futex_wait", "try_to_wake_up")):
        return "futex_sync"
    if any(marker in stack_text for marker in ("structuredclone", "message::deserialize", "node::worker::")):
        return "worker_message"
    if any(marker in stack_text for marker in ("jsonparser", "jsonparse")):
        return "json_parse"
    if thread_name.startswith("libuv-worker"):
        return "libuv_worker_other"
    if thread_name.startswith("v8worker"):
        return "v8_worker"
    if "openclaw-gatewa" in thread_name:
        return "gateway_main_other"
    return "other"


def _perf_symbol_from_stack_line(line: str) -> str:
    match = re.search(r"\s([A-Za-z0-9_:~<>\(\)\.\[\]\-]+)\+0x[0-9a-f]+", line)
    if match is not None:
        return match.group(1)
    bracket_match = re.search(r"\]\s([A-Za-z0-9_:~<>\(\)\.\[\]\-]+)$", line)
    if bracket_match is not None:
        return bracket_match.group(1)
    return line.strip()


def _load_node_trace_payloads(path: Path) -> list[dict[str, Any]]:
    raw = path.read_bytes().replace(b"\x00", b" ")
    text = raw.decode("utf-8", errors="replace")
    decoder = json.JSONDecoder()
    index = 0
    payloads: list[dict[str, Any]] = []
    while index < len(text):
        next_start = text.find("{", index)
        if next_start < 0:
            break
        try:
            payload, next_index = decoder.raw_decode(text, next_start)
        except json.JSONDecodeError:
            index = next_start + 1
            continue
        if isinstance(payload, dict) and isinstance(payload.get("traceEvents"), list):
            payloads.append(payload)
        index = max(next_index, next_start + 1)
    return payloads


def _is_gateway_trace_payload(payload: dict[str, Any]) -> bool:
    process_names: set[str] = set()
    for event in payload.get("traceEvents", []):
        if not isinstance(event, dict):
            continue
        if event.get("cat") != "__metadata" or event.get("name") != "process_name":
            continue
        args = event.get("args", {})
        if isinstance(args, dict):
            name = args.get("name")
            if isinstance(name, str) and name.strip():
                process_names.add(name.strip().lower())
    if not process_names:
        return False
    return any("openclaw-gateway" in name for name in process_names)


def _complete_node_trace_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    completed: list[dict[str, Any]] = []
    stacks: dict[tuple[int, int, str, str], list[dict[str, Any]]] = {}
    for event in raw_events:
        phase = str(event.get("ph", "")).strip()
        name = str(event.get("name", "")).strip()
        cat = str(event.get("cat", "")).strip()
        ts_us = event.get("ts")
        pid = event.get("pid")
        tid = event.get("tid")
        if not name or not isinstance(ts_us, (int, float)) or not isinstance(pid, int) or not isinstance(tid, int):
            continue
        if phase == "X":
            duration_us = event.get("dur")
            if not isinstance(duration_us, (int, float)):
                continue
            completed.append(
                {
                    **event,
                    "ts_us": float(ts_us),
                    "duration_us": float(duration_us),
                    "path": _node_trace_path(event),
                    "result": _node_trace_result(event),
                }
            )
            continue
        if phase not in {"B", "E", "b", "e"}:
            continue
        key = (pid, tid, cat, name)
        if phase in {"B", "b"}:
            stacks.setdefault(key, []).append(event)
            continue
        start = stacks.get(key, [])
        if not start:
            continue
        begin_event = start.pop()
        if not start:
            stacks.pop(key, None)
        duration_us = float(ts_us) - float(begin_event.get("ts", ts_us))
        if duration_us < 0:
            continue
        completed.append(
            {
                **begin_event,
                "_end_args": event.get("args", {}),
                "ts_us": float(begin_event.get("ts", ts_us)),
                "duration_us": duration_us,
                "path": _node_trace_path(begin_event, end_event=event),
                "result": _node_trace_result(event),
            }
        )
    return completed


def _node_trace_path(event: dict[str, Any], *, end_event: dict[str, Any] | None = None) -> str:
    for candidate in (event, end_event):
        if not isinstance(candidate, dict):
            continue
        args = candidate.get("args", {})
        if isinstance(args, dict):
            path = args.get("path")
            if isinstance(path, str) and path.strip():
                return path.strip()
    return ""


def _node_trace_result(event: dict[str, Any]) -> Any:
    args = event.get("args", {})
    if isinstance(args, dict) and "result" in args:
        return args.get("result")
    return None


def _is_node_fs_async_event(event: dict[str, Any]) -> bool:
    return _is_node_fs_async_name(str(event.get("name", "")).strip()) and "node.fs.async" in str(event.get("cat", ""))


def _is_node_fs_async_name(name: str) -> bool:
    return bool(name) and name not in {"FSREQCALLBACK", "FSREQCALLBACK_CALLBACK"}


def _node_trace_runtime_group(event: dict[str, Any]) -> str:
    name = str(event.get("name", "")).strip()
    if _is_node_fs_async_event(event):
        return "fs_async"
    if name == "FSREQCALLBACK_CALLBACK":
        return "fs_callback"
    if name == "PROMISE_CALLBACK":
        return "promise_callback"
    if name in {"CheckImmediate", "RunAndClearNativeImmediates", "RunTimers"}:
        return "event_loop"
    return ""


def _classify_trace_path(path: str) -> str:
    normalized = path.strip()
    if not normalized:
        return "unknown"
    lower = normalized.lower()
    name = Path(normalized).name.lower()
    bootstrap = {"agents.md", "soul.md", "tools.md", "identity.md", "user.md", "heartbeat.md", "bootstrap.md"}
    if name in bootstrap:
        return "workspace_bootstrap"
    if "/node_modules/" in lower:
        return "node_modules"
    if "/dist/" in lower:
        return "dist"
    if lower.endswith(".md"):
        return "markdown_docs"
    if "/.git/" in lower or name == ".git":
        return "git_metadata"
    if "/skills/" in lower:
        return "skills"
    if "/tool" in lower and lower.endswith(".json"):
        return "tool_schema"
    if "/.openclaw/" in lower:
        return "openclaw_runtime"
    return "workspace_other"


def _node_trace_focus_groups(
    *,
    path_count: dict[str, int],
    path_duration_ms: dict[str, float],
) -> dict[str, dict[str, float]]:
    groups = {
        "sessions_lock": {"count": 0.0, "total_duration_ms": 0.0},
        "sessions_dir": {"count": 0.0, "total_duration_ms": 0.0},
        "bootstrap_files": {"count": 0.0, "total_duration_ms": 0.0},
    }
    bootstrap_suffixes = {
        "/AGENTS.md",
        "/SOUL.md",
        "/TOOLS.md",
        "/IDENTITY.md",
        "/USER.md",
        "/HEARTBEAT.md",
        "/BOOTSTRAP.md",
    }
    for path, count in path_count.items():
        duration_ms = float(path_duration_ms.get(path, 0.0))
        if path.endswith("/sessions.json.lock"):
            groups["sessions_lock"]["count"] += float(count)
            groups["sessions_lock"]["total_duration_ms"] += duration_ms
        if "/agents/main/sessions" in path:
            groups["sessions_dir"]["count"] += float(count)
            groups["sessions_dir"]["total_duration_ms"] += duration_ms
        if any(path.endswith(suffix) for suffix in bootstrap_suffixes):
            groups["bootstrap_files"]["count"] += float(count)
            groups["bootstrap_files"]["total_duration_ms"] += duration_ms
    return groups


def _row_matches_name(row: dict[str, Any], predicate: Any) -> bool:
    name = str(row.get("name", "")).strip()
    try:
        return bool(predicate(name))
    except Exception:
        return False


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
