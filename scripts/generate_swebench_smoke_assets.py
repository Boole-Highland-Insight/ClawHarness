#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = Path(
    "/root/ziruiw/ascend_fabric/multi_replica_20260426T075224Z/ai_profiler_cleaning/post7_datasets/swebench/data/test-00000-of-00001.parquet",
)
DEFAULT_TASKS_DIR = REPO_ROOT / "tasks" / "swe_smoke"
DEFAULT_BATCH_CONFIG = REPO_ROOT / "scripts" / "batch_run_swe_multisample.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate prompt-level SWE smoke task files and a matching batch_harness config from local parquet data.",
    )
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the local SWE-bench parquet file.",
    )
    parser.add_argument(
        "--instance-id",
        action="append",
        required=True,
        help="Instance id to include. Repeat this flag for multiple samples.",
    )
    parser.add_argument(
        "--tasks-dir",
        default=str(DEFAULT_TASKS_DIR),
        help="Directory where generated task markdown files will be written.",
    )
    parser.add_argument(
        "--batch-config",
        default=str(DEFAULT_BATCH_CONFIG),
        help="Path to the generated batch JSON config.",
    )
    parser.add_argument(
        "--output-root",
        default="out/batch_run_swe_smoke_multisample",
        help="Output root to embed in the generated batch config, relative to repo root unless absolute.",
    )
    parser.add_argument(
        "--generated-root",
        default=".state/generated_scenarios/batch_harness_swe_multisample",
        help="Generated scenario root to embed in the generated batch config, relative to repo root unless absolute.",
    )
    return parser.parse_args()


def load_records(dataset_path: Path, instance_ids: list[str]) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    requested = list(dict.fromkeys(instance_ids))
    table = pq.read_table(
        dataset_path,
        filters=[("instance_id", "in", requested)],
        columns=[
            "repo",
            "instance_id",
            "base_commit",
            "problem_statement",
            "hints_text",
            "version",
        ],
    )
    rows = table.to_pylist()
    found = {str(row["instance_id"]): row for row in rows}
    missing = [instance_id for instance_id in requested if instance_id not in found]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing instance ids in dataset: {joined}")
    return [found[instance_id] for instance_id in requested]


def summarize_problem(problem_statement: str) -> str:
    lines = [line.strip() for line in problem_statement.splitlines() if line.strip()]
    if not lines:
        return "Problem statement unavailable in dataset row."
    summary = lines[0]
    if len(summary) > 280:
        return f"{summary[:277].rstrip()}..."
    return summary


def slugify_instance(instance_id: str) -> str:
    return instance_id.replace("__", "_").replace("-", "_")


def build_prompt(row: dict[str, Any]) -> str:
    prompt_lines = [
        "You are given a compact SWE-bench Verified issue instance for prompt-level benchmarking.",
        "This harness run does not execute the repository test environment or score an official SWE-bench patch.",
        "Instead, analyze the issue and return a concise debugging and fix plan.",
        "Base your answer only on the issue material below.",
        "Do not use web_search, web_fetch, browser navigation, external network access, or repository inspection tools.",
        "Do not assume the repository is checked out locally.",
        "",
        "Output format:",
        "1. Root cause hypothesis",
        "2. Files or functions most likely involved",
        "3. Minimal patch strategy",
        "4. Risks or edge cases to verify",
        "",
        f"Instance ID: {row['instance_id']}",
        f"Repository: {row['repo']}",
        f"Base commit: {row['base_commit']}",
        f"Version: {row.get('version') or 'unknown'}",
        "",
        "Problem statement:",
        summarize_problem(str(row.get("problem_statement") or "")).strip(),
    ]
    prompt_lines.extend(
        [
            "",
            "Focus only on the likely library fix strategy. Do not propose broad API redesign unless it is necessary.",
        ],
    )
    return "\n".join(prompt_lines)


def write_task_file(tasks_dir: Path, row: dict[str, Any], dataset_path: Path) -> Path:
    instance_id = str(row["instance_id"])
    task_stem = f"task_swebench_smoke_{slugify_instance(instance_id)}"
    task_path = tasks_dir / f"{task_stem}.md"
    prompt = build_prompt(row)
    content = "\n".join(
        [
            "---",
            f"id: swebench_smoke_{slugify_instance(instance_id)}",
            f"name: SWE smoke {instance_id}",
            "category: swebench",
            "description: Prompt-level SWE smoke task generated from local SWE-bench parquet data.",
            "prompt: |",
            *[f"  {line}" if line else "" for line in prompt.splitlines()],
            "---",
            "",
            f"Source dataset path: `{dataset_path}`",
            f"Original instance id: `{instance_id}`",
            f"Repository: `{row['repo']}`",
            f"Base commit: `{row['base_commit']}`",
        ],
    )
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text(f"{content}\n", encoding="utf-8")
    return task_path


def build_batch_config(task_paths: list[Path], output_root: str, generated_root: str) -> dict[str, Any]:
    client_variants = [
        {
            "key": task_path.stem.removeprefix("task_"),
            "task_file": str(task_path.relative_to(REPO_ROOT)),
            "message": "",
        }
        for task_path in task_paths
    ]
    return {
        "template_scenario": "scenarios/vllm/vps_docker_burst_task_01_100_session10.json",
        "basename": "vps-docker-swebench-smoke-ms",
        "output_root": output_root,
        "generated_root": generated_root,
        "python_bin": "/root/Zehao/ClawHarness/.venv/bin/python",
        "run_tag": "smoke-ms",
        "keep_runtime": False,
        "continue_on_error": False,
        "skip_completed": True,
        "dry_run": False,
        "base_overrides": {
            "client.message": "",
            "client.task_file": "",
            "client.wait_timeout_ms": 180000,
            "client.send_timeout_ms": 60000,
            "runtime.image": "dr34m/openclaw:latest",
            "runtime.build_image_if_missing": False,
            "runtime.skip_channels": True,
            "load.dispatch_mode": "burst",
            "load.request_pause_ms": 0,
            "load.worker_stagger_ms": 0,
        },
        "client_variants": client_variants,
        "run_variants": [
            {
                "key": "burst-serial-2",
                "overrides": {
                    "runtime.instance_num": 1,
                    "runtime.openclaw_num_per_instance": 1,
                    "load.concurrency": 1,
                    "load.requests_per_worker": 2,
                    "load.total_requests": 2,
                    "load.max_in_flight": 1,
                    "load.connect_concurrency": 1,
                    "client.session_mode": "shared",
                    "client.session_pool_size": 1,
                },
            },
            {
                "key": "burst-single-container-single-instance-2w",
                "overrides": {
                    "runtime.instance_num": 1,
                    "runtime.openclaw_num_per_instance": 1,
                    "load.concurrency": 2,
                    "load.requests_per_worker": 1,
                    "load.total_requests": 2,
                    "load.max_in_flight": 2,
                    "load.connect_concurrency": 2,
                    "client.session_mode": "per_worker",
                    "client.session_pool_size": 2,
                },
            },
            {
                "key": "burst-single-container-multi-openclaw-2x1w",
                "overrides": {
                    "runtime.instance_num": 1,
                    "runtime.openclaw_num_per_instance": 2,
                    "runtime.host_port": 19489,
                    "runtime.container_port": 19489,
                    "load.concurrency": 2,
                    "load.requests_per_worker": 1,
                    "load.total_requests": 2,
                    "load.max_in_flight": 2,
                    "load.connect_concurrency": 2,
                    "client.session_mode": "per_worker",
                    "client.session_pool_size": 2,
                },
            },
            {
                "key": "burst-multi-container-single-openclaw-2x1x1w",
                "overrides": {
                    "runtime.instance_num": 2,
                    "runtime.openclaw_num_per_instance": 1,
                    "runtime.host_port": 19589,
                    "runtime.container_port": 19589,
                    "load.concurrency": 1,
                    "load.requests_per_worker": 1,
                    "load.total_requests": 1,
                    "load.max_in_flight": 1,
                    "load.connect_concurrency": 1,
                    "client.session_mode": "per_worker",
                    "client.session_pool_size": 1,
                },
            },
        ],
    }


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset).resolve()
    tasks_dir = Path(args.tasks_dir).resolve()
    batch_config_path = Path(args.batch_config).resolve()
    rows = load_records(dataset_path, args.instance_id)
    task_paths = [write_task_file(tasks_dir, row, dataset_path) for row in rows]
    payload = build_batch_config(task_paths, args.output_root, args.generated_root)
    batch_config_path.parent.mkdir(parents=True, exist_ok=True)
    batch_config_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    print(f"Generated {len(task_paths)} task files under: {tasks_dir}")
    for task_path in task_paths:
        print(task_path)
    print(f"Generated batch config: {batch_config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())