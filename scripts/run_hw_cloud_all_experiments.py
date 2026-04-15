#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "out"
DEFAULT_GENERATED_ROOT = REPO_ROOT / ".state" / "generated_scenarios" / "hw_cloud_all_experiments"


@dataclass(frozen=True, slots=True)
class ScenarioTemplate:
    key: str
    path: Path
    name_base: str
    session_prefix_base: str


@dataclass(frozen=True, slots=True)
class SessionVariant:
    key: str
    session_mode: str
    suffix: str


SCENARIO_TEMPLATES = [
    ScenarioTemplate(
        key="single",
        path=REPO_ROOT / "scenarios" / "vps" / "vps_docker_single_light.json",
        name_base="vps-docker-single-task-00-500",
        session_prefix_base="vps-docker-single-task-00-500",
    ),
    ScenarioTemplate(
        key="multi_stag300",
        path=REPO_ROOT / "scenarios" / "vps" / "vps_docker_multi_10x50_stag300.json",
        name_base="vps-docker-multi-task-00-500-stag300",
        session_prefix_base="vps-docker-multi-task-00-500-stag300",
    ),
    ScenarioTemplate(
        key="multi_stag150",
        path=REPO_ROOT / "scenarios" / "vps" / "vps_docker_multi_10x50_stag150.json",
        name_base="vps-docker-multi-task-00-500-stag150",
        session_prefix_base="vps-docker-multi-task-00-500-stag150",
    ),
]

SESSION_VARIANTS = [
    SessionVariant(key="worker", session_mode="per_worker", suffix="worker"),
    SessionVariant(key="request", session_mode="per_request", suffix="request"),
    SessionVariant(key="shared", session_mode="shared", suffix="shared"),
]

SCENARIO_BY_KEY = {spec.key: spec for spec in SCENARIO_TEMPLATES}
SESSION_BY_KEY = {spec.key: spec for spec in SESSION_VARIANTS}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and run the full hw cloud benchmark matrix from the VPS scenario templates.",
    )
    parser.add_argument(
        "--scenario-key",
        action="append",
        choices=list(SCENARIO_BY_KEY),
        help="Optional scenario subset. May be repeated. Defaults to all.",
    )
    parser.add_argument(
        "--mode",
        action="append",
        choices=list(SESSION_BY_KEY),
        help="Optional session-mode subset. May be repeated. Defaults to all.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Benchmark output root directory. Defaults to repo/out.",
    )
    parser.add_argument(
        "--generated-root",
        default=str(DEFAULT_GENERATED_ROOT),
        help="Directory used to persist generated scenario variants.",
    )
    parser.add_argument(
        "--run-tag",
        default="",
        help="Optional extra suffix appended to generated scenario names and session prefixes.",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python executable used for 'python -m openclaw_harness run'. Defaults to the current interpreter.",
    )
    parser.add_argument(
        "--keep-runtime",
        action="store_true",
        help="Pass through --keep-runtime to the harness.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep going after a failed run instead of stopping at the first error.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate scenarios and print commands without launching experiments.",
    )
    return parser.parse_args()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def resolve_user_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def safe_slug(value: str) -> str:
    chars: list[str] = []
    last_was_dash = False
    for char in value.strip().lower():
        if char.isalnum():
            chars.append(char)
            last_was_dash = False
            continue
        if not last_was_dash and chars:
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


def append_suffix(base: str, suffix: str) -> str:
    return f"{base}-{suffix}" if suffix else base


def load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"scenario file must decode to a JSON object: {path}")
    return raw


def build_variant_payload(
    raw_scenario: dict[str, Any],
    *,
    template: ScenarioTemplate,
    session_variant: SessionVariant,
    run_tag: str,
) -> dict[str, Any]:
    scenario = copy.deepcopy(raw_scenario)
    client = scenario.setdefault("client", {})
    if not isinstance(client, dict):
        raise ValueError(f"scenario.client must be a JSON object: {template.path}")

    scenario_name = append_suffix(template.name_base, session_variant.suffix)
    session_prefix = append_suffix(template.session_prefix_base, session_variant.suffix)
    if run_tag:
        scenario_name = append_suffix(scenario_name, run_tag)
        session_prefix = append_suffix(session_prefix, run_tag)

    scenario["name"] = scenario_name
    client["session_mode"] = session_variant.session_mode
    client["session_prefix"] = session_prefix
    return scenario


def build_pythonpath() -> str:
    paths = [str(REPO_ROOT / ".deps"), str(REPO_ROOT / "src")]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    return os.pathsep.join(paths)


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


def build_batch_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_generated_scenarios(
    *,
    batch_dir: Path,
    scenario_keys: list[str],
    mode_keys: list[str],
    run_tag: str,
    output_root: Path,
    keep_runtime: bool,
    python_bin: str,
) -> list[dict[str, Any]]:
    run_specs: list[dict[str, Any]] = []
    sequence = 1
    for scenario_key in scenario_keys:
        template = SCENARIO_BY_KEY[scenario_key]
        raw_scenario = load_json(template.path)
        for mode_key in mode_keys:
            session_variant = SESSION_BY_KEY[mode_key]
            payload = build_variant_payload(
                raw_scenario,
                template=template,
                session_variant=session_variant,
                run_tag=run_tag,
            )
            generated_path = batch_dir / f"{sequence:02d}_{scenario_key}_{mode_key}.json"
            generated_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )
            run_specs.append(
                {
                    "index": sequence,
                    "scenario_key": scenario_key,
                    "mode_key": mode_key,
                    "template_path": str(template.path),
                    "generated_path": str(generated_path),
                    "scenario_name": payload["name"],
                    "session_prefix": payload["client"]["session_prefix"],
                    "session_mode": payload["client"]["session_mode"],
                    "command": build_command(
                        python_bin=python_bin,
                        scenario_path=generated_path,
                        output_root=output_root,
                        keep_runtime=keep_runtime,
                    ),
                },
            )
            sequence += 1
    manifest_path = batch_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"runs": run_specs}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return run_specs


def run_matrix(
    *,
    run_specs: list[dict[str, Any]],
    dry_run: bool,
    continue_on_error: bool,
) -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = build_pythonpath()
    failures: list[dict[str, Any]] = []

    for spec in run_specs:
        command = list(spec["command"])
        print(
            f"[{spec['index']:02d}/{len(run_specs):02d}] "
            f"{spec['scenario_key']} + {spec['mode_key']} -> {spec['scenario_name']}"
        )
        print(f"  source scenario : {spec['template_path']}")
        print(f"  generated file  : {spec['generated_path']}")
        print(f"  session_prefix  : {spec['session_prefix']}")
        print(f"  session_mode    : {spec['session_mode']}")
        print(f"  command         : {shlex.join(command)}")

        if dry_run:
            continue

        result = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
        if result.returncode == 0:
            continue

        failures.append(
            {
                "scenario_name": spec["scenario_name"],
                "mode_key": spec["mode_key"],
                "returncode": result.returncode,
            },
        )
        print(
            f"  run failed with exit code {result.returncode}: {spec['scenario_name']}",
            file=sys.stderr,
        )
        if not continue_on_error:
            break

    if failures:
        print("", file=sys.stderr)
        print("Failed runs:", file=sys.stderr)
        for failure in failures:
            print(
                f"  - {failure['scenario_name']} ({failure['mode_key']}): exit code {failure['returncode']}",
                file=sys.stderr,
            )
        return 1

    if dry_run:
        print("")
        print("Dry run complete. No experiments were launched.")
        return 0

    print("")
    print("All requested experiments finished successfully.")
    return 0


def main() -> int:
    args = parse_args()

    scenario_keys = dedupe_preserve_order(args.scenario_key or [spec.key for spec in SCENARIO_TEMPLATES])
    mode_keys = dedupe_preserve_order(args.mode or [spec.key for spec in SESSION_VARIANTS])
    output_root = resolve_user_path(args.output_root)
    generated_root = resolve_user_path(args.generated_root)
    run_tag = normalize_tag(args.run_tag, label="run-tag")

    batch_dir = generated_root / build_batch_id()
    batch_dir.mkdir(parents=True, exist_ok=True)

    run_specs = write_generated_scenarios(
        batch_dir=batch_dir,
        scenario_keys=scenario_keys,
        mode_keys=mode_keys,
        run_tag=run_tag,
        output_root=output_root,
        keep_runtime=args.keep_runtime,
        python_bin=args.python_bin,
    )

    print(f"Generated {len(run_specs)} scenario variants under: {batch_dir}")
    return run_matrix(
        run_specs=run_specs,
        dry_run=args.dry_run,
        continue_on_error=args.continue_on_error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
