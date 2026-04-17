#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "scripts" / "batch_run.json"


@dataclass(frozen=True, slots=True)
class OverrideSpec:
    path: str
    value: Any


@dataclass(frozen=True, slots=True)
class ClientVariant:
    key: str
    task_bucket: str
    overrides: tuple[OverrideSpec, ...]


@dataclass(frozen=True, slots=True)
class RunVariant:
    key: str
    overrides: tuple[OverrideSpec, ...]


@dataclass(frozen=True, slots=True)
class OverrideVariant:
    key: str
    overrides: tuple[OverrideSpec, ...]


@dataclass(frozen=True, slots=True)
class BatchConfig:
    config_path: Path
    template_scenario: Path
    basename: str
    output_root: Path
    generated_root: Path
    python_bin: str
    run_tag: str
    keep_runtime: bool
    continue_on_error: bool
    skip_completed: bool
    dry_run: bool
    base_overrides: tuple[OverrideSpec, ...]
    client_variants: tuple[ClientVariant, ...]
    override_variants: tuple[OverrideVariant, ...]
    run_variants: tuple[RunVariant, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read batch settings from JSON, generate scenario variants, and launch "
            "'python -m openclaw_harness run' for each combination."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only generate scenarios and print commands without launching the harness.",
    )
    return parser.parse_args()


def build_pythonpath() -> str:
    paths = [str(REPO_ROOT / ".deps"), str(REPO_ROOT / "src")]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    return os.pathsep.join(paths)


def build_batch_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must decode to an object: {path}")
    return payload


def safe_slug(value: str) -> str:
    chars: list[str] = []
    last_was_dash = False
    for char in value.strip().lower():
        if char.isalnum():
            chars.append(char)
            last_was_dash = False
            continue
        if chars and not last_was_dash:
            chars.append("-")
            last_was_dash = True
    return "".join(chars).strip("-")


def normalize_tag(value: str, *, label: str) -> str:
    if not value.strip():
        return ""
    slug = safe_slug(value)
    if not slug:
        raise ValueError(f"{label} must contain at least one alphanumeric character")
    return slug


def normalize_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path:
        raise ValueError("override path cannot be empty")
    tokens = path.split(".")
    if any(not token.strip() for token in tokens):
        raise ValueError(f"invalid dotted path: {raw_path}")
    return ".".join(token.strip() for token in tokens)


def resolve_repo_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def parse_bool(raw: Any, *, label: str, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    raise ValueError(f"{label} must be a boolean")


def parse_string(raw: Any, *, label: str, default: str = "") -> str:
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise ValueError(f"{label} must be a string")
    return raw


def parse_required_string(raw: Any, *, label: str) -> str:
    value = parse_string(raw, label=label).strip()
    if not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def parse_override_mapping(raw: Any, *, label: str) -> tuple[OverrideSpec, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, dict):
        raise ValueError(f"{label} must be a JSON object")
    return tuple(
        OverrideSpec(path=normalize_path(str(key)), value=value)
        for key, value in raw.items()
    )


def normalize_task_bucket(raw_value: str) -> str:
    slug = safe_slug(raw_value)
    match = re.search(r"\btask-(\d+)\b", slug)
    if match:
        digits = match.group(1)
        return f"task-{digits.zfill(max(2, len(digits)))}"
    return slug or "default"


def infer_task_bucket(*, client_key: str, task_file: str) -> str:
    if task_file.strip():
        return normalize_task_bucket(Path(task_file).stem)
    return normalize_task_bucket(client_key)


def parse_client_variants(raw: Any) -> tuple[ClientVariant, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("client_variants must be a non-empty JSON array")

    variants: list[ClientVariant] = []
    for index, item in enumerate(raw, start=1):
        label = f"client_variants[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be a JSON object")

        key = normalize_tag(parse_string(item.get("key"), label=f"{label}.key"), label=f"{label}.key")
        task_file = parse_string(item.get("task_file"), label=f"{label}.task_file")
        message = parse_string(item.get("message"), label=f"{label}.message")
        overrides = list(parse_override_mapping(item.get("overrides"), label=f"{label}.overrides"))

        if task_file:
            overrides.append(
                OverrideSpec(path="client.task_file", value=str(resolve_repo_path(task_file))),
            )
        else:
            overrides.append(OverrideSpec(path="client.task_file", value=""))
        overrides.append(OverrideSpec(path="client.message", value=message))

        variants.append(
            ClientVariant(
                key=key,
                task_bucket=infer_task_bucket(client_key=key, task_file=task_file),
                overrides=tuple(overrides),
            ),
        )
    return tuple(variants)


def parse_run_variants(raw: Any) -> tuple[RunVariant, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("run_variants must be a non-empty JSON array")

    variants: list[RunVariant] = []
    for index, item in enumerate(raw, start=1):
        label = f"run_variants[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be a JSON object")
        key = normalize_tag(parse_string(item.get("key"), label=f"{label}.key"), label=f"{label}.key")
        overrides = parse_override_mapping(item.get("overrides"), label=f"{label}.overrides")
        if not overrides:
            raise ValueError(f"{label}.overrides must define at least one override")
        variants.append(RunVariant(key=key, overrides=overrides))
    return tuple(variants)


def parse_override_variants(raw: Any) -> tuple[OverrideVariant, ...]:
    if raw is None:
        return (OverrideVariant(key="", overrides=()),)
    if not isinstance(raw, list) or not raw:
        raise ValueError("override_variants must be a non-empty JSON array")

    variants: list[OverrideVariant] = []
    for index, item in enumerate(raw, start=1):
        label = f"override_variants[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be a JSON object")
        key = normalize_tag(parse_string(item.get("key"), label=f"{label}.key"), label=f"{label}.key")
        overrides = parse_override_mapping(item.get("overrides"), label=f"{label}.overrides")
        if not overrides:
            raise ValueError(f"{label}.overrides must define at least one override")
        variants.append(OverrideVariant(key=key, overrides=overrides))
    return tuple(variants)


def load_batch_config(path: Path) -> BatchConfig:
    raw = load_json(path)
    template_scenario = resolve_repo_path(
        parse_required_string(raw.get("template_scenario"), label="template_scenario"),
    )
    if not template_scenario.is_file():
        raise ValueError(f"template_scenario not found: {template_scenario}")

    output_root = resolve_repo_path(
        parse_required_string(raw.get("output_root"), label="output_root"),
    )
    generated_root = resolve_repo_path(
        parse_required_string(raw.get("generated_root"), label="generated_root"),
    )
    python_bin = parse_string(raw.get("python_bin"), label="python_bin", default=sys.executable).strip() or sys.executable

    return BatchConfig(
        config_path=path,
        template_scenario=template_scenario,
        basename=normalize_tag(parse_string(raw.get("basename"), label="basename"), label="basename"),
        output_root=output_root,
        generated_root=generated_root,
        python_bin=python_bin,
        run_tag=normalize_tag(parse_string(raw.get("run_tag"), label="run_tag"), label="run_tag"),
        keep_runtime=parse_bool(raw.get("keep_runtime"), label="keep_runtime", default=False),
        continue_on_error=parse_bool(
            raw.get("continue_on_error"),
            label="continue_on_error",
            default=False,
        ),
        skip_completed=parse_bool(
            raw.get("skip_completed"),
            label="skip_completed",
            default=False,
        ),
        dry_run=parse_bool(raw.get("dry_run"), label="dry_run", default=False),
        base_overrides=parse_override_mapping(raw.get("base_overrides"), label="base_overrides"),
        client_variants=parse_client_variants(raw.get("client_variants")),
        override_variants=parse_override_variants(raw.get("override_variants")),
        run_variants=parse_run_variants(raw.get("run_variants")),
    )


def set_dotted_path(payload: Any, dotted_path: str, value: Any) -> None:
    tokens = dotted_path.split(".")
    current = payload
    for token in tokens[:-1]:
        current = descend_one_level(current, token, dotted_path)
    last = tokens[-1]
    if isinstance(current, dict):
        current[last] = value
        return
    if isinstance(current, list):
        index = parse_list_index(last, dotted_path)
        current[index] = value
        return
    raise TypeError(
        f"cannot assign path '{dotted_path}' because '{last}' is nested under a non-container value",
    )


def descend_one_level(current: Any, token: str, dotted_path: str) -> Any:
    if isinstance(current, dict):
        if token not in current:
            raise KeyError(f"path '{dotted_path}' does not exist at '{token}'")
        return current[token]
    if isinstance(current, list):
        index = parse_list_index(token, dotted_path)
        return current[index]
    raise TypeError(
        f"cannot traverse path '{dotted_path}' because '{token}' is nested under a non-container value",
    )


def parse_list_index(token: str, dotted_path: str) -> int:
    if not token.isdigit():
        raise ValueError(
            f"path '{dotted_path}' targets a list, so '{token}' must be a zero-based integer index",
        )
    return int(token)


def build_variant_slug(
    *,
    index: int,
    client_key: str,
    run_key: str,
    override_key: str,
    run_tag: str,
) -> str:
    parts = [f"{index:02d}", client_key, run_key]
    if override_key:
        parts.append(override_key)
    if run_tag:
        parts.append(run_tag)
    return "-".join(parts)


def apply_generated_identity(
    payload: dict[str, Any],
    *,
    basename: str,
    identity_suffix: str,
    fallback_suffix: str,
) -> None:
    client = payload.setdefault("client", {})
    if not isinstance(client, dict):
        raise ValueError("scenario.client must be a JSON object")

    if basename:
        resolved_name = f"{basename}-{identity_suffix}" if identity_suffix else basename
        payload["name"] = resolved_name
        client["session_prefix"] = resolved_name
        return

    base_name = str(payload.get("name", "") or "").strip() or "scenario"
    payload["name"] = f"{base_name}-{fallback_suffix}"
    base_prefix = str(client.get("session_prefix", "") or "").strip() or base_name
    client["session_prefix"] = f"{base_prefix}-{fallback_suffix}"


def build_variant_payload(
    *,
    base_payload: dict[str, Any],
    overrides: list[OverrideSpec],
    basename: str,
    identity_suffix: str,
    fallback_suffix: str,
) -> dict[str, Any]:
    payload = copy.deepcopy(base_payload)
    for spec in overrides:
        set_dotted_path(payload, spec.path, spec.value)
    apply_generated_identity(
        payload,
        basename=basename,
        identity_suffix=identity_suffix,
        fallback_suffix=fallback_suffix,
    )
    return payload


def build_command(
    *,
    python_bin: str,
    scenario_path: Path,
    output_root: Path,
    keep_runtime: bool,
) -> list[str]:
    command = [
        python_bin,
        "-m",
        "openclaw_harness",
        "run",
        "--scenario",
        str(scenario_path),
        "--output-root",
        str(output_root),
    ]
    if keep_runtime:
        command.append("--keep-runtime")
    return command


def iter_completed_run_dirs(output_root: Path) -> list[Path]:
    if not output_root.exists():
        return []

    run_dirs: list[Path] = []
    for resolved_path in sorted(output_root.rglob("scenario.resolved.json"), reverse=True):
        run_dir = resolved_path.parent
        try:
            relative_parts = run_dir.relative_to(output_root).parts
        except ValueError:
            continue
        if "instances" in relative_parts:
            continue
        if not (run_dir / "summary.json").is_file():
            continue
        run_dirs.append(run_dir)
    return run_dirs


def project_like(source: Any, template: Any) -> Any:
    if isinstance(template, dict):
        if not isinstance(source, dict):
            return source
        return {
            key: project_like(source[key], value)
            for key, value in template.items()
            if key in source
        }
    if isinstance(template, list):
        if not isinstance(source, list):
            return source
        return [
            project_like(source_item, template_item)
            for source_item, template_item in zip(source, template)
        ]
    return source


def load_completed_runs(output_root: Path) -> list[dict[str, Any]]:
    completed_runs: list[dict[str, Any]] = []
    for run_dir in iter_completed_run_dirs(output_root):
        resolved_path = run_dir / "scenario.resolved.json"
        try:
            resolved_payload = load_json(resolved_path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        completed_runs.append(
            {
                "run_dir": run_dir,
                "resolved_payload": resolved_payload,
            },
        )
    return completed_runs


def find_completed_match(
    *,
    spec_payload: dict[str, Any],
    completed_runs: list[dict[str, Any]],
) -> Path | None:
    for completed in completed_runs:
        resolved_payload = completed["resolved_payload"]
        if project_like(resolved_payload, spec_payload) == spec_payload:
            return completed["run_dir"]
    return None


def write_generated_scenarios(config: BatchConfig, *, batch_dir: Path) -> list[dict[str, Any]]:
    base_payload = load_json(config.template_scenario)
    run_specs: list[dict[str, Any]] = []
    manifest_runs: list[dict[str, Any]] = []
    sequence = 1

    for client_variant in config.client_variants:
        for run_variant in config.run_variants:
            for override_variant in config.override_variants:
                file_suffix = build_variant_slug(
                    index=sequence,
                    client_key=client_variant.key,
                    run_key=run_variant.key,
                    override_key=override_variant.key,
                    run_tag=config.run_tag,
                )
                identity_parts = [run_variant.key]
                if override_variant.key:
                    identity_parts.append(override_variant.key)
                if config.run_tag:
                    identity_parts.append(config.run_tag)
                identity_suffix = "-".join(identity_parts)
                overrides = [
                    *config.base_overrides,
                    *client_variant.overrides,
                    *run_variant.overrides,
                    *override_variant.overrides,
                ]
                payload = build_variant_payload(
                    base_payload=base_payload,
                    overrides=overrides,
                    basename=config.basename,
                    identity_suffix=identity_suffix,
                    fallback_suffix=file_suffix,
                )
                generated_name = f"{file_suffix}.json"
                generated_path = batch_dir / generated_name
                generated_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
                    encoding="utf-8",
                )
                spec = {
                    "index": sequence,
                    "client_key": client_variant.key,
                    "task_bucket": client_variant.task_bucket,
                    "run_key": run_variant.key,
                    "override_key": override_variant.key,
                    "generated_path": str(generated_path),
                    "scenario_name": payload["name"],
                    "session_prefix": payload["client"]["session_prefix"],
                    "task_output_root": str(config.output_root / client_variant.task_bucket),
                    "overrides": {spec.path: spec.value for spec in overrides},
                    "command": build_command(
                        python_bin=config.python_bin,
                        scenario_path=generated_path,
                        output_root=config.output_root / client_variant.task_bucket,
                        keep_runtime=config.keep_runtime,
                    ),
                    "payload": payload,
                }
                run_specs.append(spec)
                manifest_runs.append(
                    {
                        key: value
                        for key, value in spec.items()
                        if key != "payload"
                    },
                )
                sequence += 1

    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config_path": str(config.config_path),
                "template_scenario": str(config.template_scenario),
                "runs": manifest_runs,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return run_specs


def run_batch(
    *,
    config: BatchConfig,
    batch_dir: Path,
    run_specs: list[dict[str, Any]],
    dry_run: bool,
) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = build_pythonpath()
    failures: list[dict[str, Any]] = []
    skipped = 0
    completed_runs = load_completed_runs(config.output_root) if config.skip_completed else []

    for spec in run_specs:
        command = list(spec["command"])
        combo_parts = [spec["client_key"], spec["run_key"]]
        if spec["override_key"]:
            combo_parts.append(spec["override_key"])
        print(
            f"[{spec['index']:02d}/{len(run_specs):02d}] "
            f"{' + '.join(combo_parts)} -> {spec['scenario_name']}"
        )
        print(f"  config          : {config.config_path}")
        print(f"  template        : {config.template_scenario}")
        print(f"  batch dir       : {batch_dir}")
        print(f"  generated file  : {spec['generated_path']}")
        print(f"  task bucket     : {spec['task_bucket']}")
        print(f"  task out root   : {spec['task_output_root']}")
        print(f"  session_prefix  : {spec['session_prefix']}")
        print(f"  overrides       : {json.dumps(spec['overrides'], ensure_ascii=True)}")
        print(f"  command         : {shlex.join(command)}")

        completed_match = None
        if config.skip_completed:
            completed_match = find_completed_match(
                spec_payload=spec["payload"],
                completed_runs=completed_runs,
            )
            if completed_match is not None:
                skipped += 1
                print("  status          : skip existing completed run")
                print(f"  completed dir   : {completed_match}")
                continue

        if dry_run:
            continue

        result = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
        if result.returncode == 0:
            continue

        failures.append(
            {
                "scenario_name": spec["scenario_name"],
                "returncode": result.returncode,
            },
        )
        print(
            f"  run failed with exit code {result.returncode}: {spec['scenario_name']}",
            file=sys.stderr,
        )
        if not config.continue_on_error:
            break

    if failures:
        print("", file=sys.stderr)
        print("Failed runs:", file=sys.stderr)
        for failure in failures:
            print(
                f"  - {failure['scenario_name']}: exit code {failure['returncode']}",
                file=sys.stderr,
            )
        if skipped:
            print(f"Skipped completed runs: {skipped}", file=sys.stderr)
        return 1

    if dry_run:
        print("")
        if skipped:
            print(f"Skipped {skipped} existing completed runs.")
        print("Dry run complete. No harness runs were launched.")
        return 0

    print("")
    if skipped:
        print(f"Skipped {skipped} existing completed runs.")
    print("All requested batch runs finished successfully.")
    return 0


def main() -> int:
    args = parse_args()
    config = load_batch_config(DEFAULT_CONFIG_PATH)

    batch_dir = config.generated_root / build_batch_id()
    batch_dir.mkdir(parents=True, exist_ok=True)

    run_specs = write_generated_scenarios(config, batch_dir=batch_dir)
    dry_run = args.dry_run or config.dry_run

    print(f"Loaded batch config: {config.config_path}")
    print(f"Generated {len(run_specs)} scenario variants under: {batch_dir}")
    return run_batch(
        config=config,
        batch_dir=batch_dir,
        run_specs=run_specs,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
