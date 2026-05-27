#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = Path(
    "/root/ziruiw/ascend_fabric/multi_replica_20260426T075224Z/ai_profiler_cleaning/post7_datasets/swebench/data/test-00000-of-00001.parquet",
)
DEFAULT_WORKSPACE_ROOT = REPO_ROOT / ".state" / "swebench_real_batch"
SINGLE_CASE_RUNNER = REPO_ROOT / "scripts" / "run_real_swebench_case.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multiple SWE-bench Verified cases through the real checkout/bootstrap/test flow and summarize pass rate.",
    )
    parser.add_argument(
        "--instance-id",
        action="append",
        required=True,
        help="SWE-bench instance id to run. Repeat this flag for multiple cases.",
    )
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the local SWE-bench parquet file.",
    )
    parser.add_argument(
        "--workspace-root",
        default=str(DEFAULT_WORKSPACE_ROOT),
        help="Root directory for the batch workspace and per-case outputs.",
    )
    parser.add_argument(
        "--python-bin",
        default="",
        help="Optional Python interpreter to pass through to each case run.",
    )
    parser.add_argument(
        "--case-venv-name",
        default=".venv_case",
        help="Per-case virtual environment directory name.",
    )
    parser.add_argument(
        "--source-repo",
        default="",
        help="Optional local git repo to clone from instead of GitHub.",
    )
    parser.add_argument(
        "--candidate-patch",
        default="",
        help="Optional patch file to apply to every case after test_patch.",
    )
    parser.add_argument(
        "--include-pass-to-pass",
        action="store_true",
        help="Include PASS_TO_PASS tests in the pytest target list.",
    )
    parser.add_argument(
        "--max-tests",
        type=int,
        default=0,
        help="Limit the number of pytest targets for each case.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep running later cases after a failure.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Emit per-case plans without cloning or testing.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_records(dataset_path: Path, instance_ids: list[str]) -> dict[str, dict[str, Any]]:
    import pyarrow.parquet as pq

    requested = list(dict.fromkeys(instance_ids))
    table = pq.read_table(
        dataset_path,
        filters=[("instance_id", "in", requested)],
        columns=["repo", "instance_id", "base_commit", "version", "FAIL_TO_PASS", "PASS_TO_PASS"],
    )
    rows = table.to_pylist()
    found = {str(row["instance_id"]): row for row in rows}
    missing = [instance_id for instance_id in requested if instance_id not in found]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing instance ids in dataset: {joined}")
    return found


def build_case_command(args: argparse.Namespace, dataset_path: Path, workspace_root: Path, instance_id: str) -> list[str]:
    command = [
        sys.executable,
        str(SINGLE_CASE_RUNNER),
        "--instance-id",
        instance_id,
        "--dataset",
        str(dataset_path),
        "--workspace-root",
        str(workspace_root),
        "--apply-gold-patch",
        "--run-tests",
        "--case-venv-name",
        args.case_venv_name,
    ]
    if args.python_bin.strip():
        command.extend(["--python-bin", args.python_bin.strip()])
    if args.source_repo.strip():
        command.extend(["--source-repo", args.source_repo.strip()])
    if args.candidate_patch.strip():
        command.extend(["--candidate-patch", args.candidate_patch.strip()])
    if args.include_pass_to_pass:
        command.append("--include-pass-to-pass")
    if args.max_tests > 0:
        command.extend(["--max-tests", str(args.max_tests)])
    if args.plan_only:
        command.append("--plan-only")
    return command


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_case(
    *,
    instance_id: str,
    record: dict[str, Any],
    case_dir: Path,
    returncode: int,
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    metadata_path = case_dir / "metadata.json"
    plan_path = case_dir / "plan.json"
    test_log_path = case_dir / "test.log"
    metadata = read_json_if_exists(metadata_path)
    plan = read_json_if_exists(plan_path)
    passed = returncode == 0 and test_log_path.exists()
    pytest_targets = metadata.get("pytest_targets") or plan.get("pytest_targets") or []
    return {
        "instance_id": instance_id,
        "repo": str(record.get("repo") or ""),
        "version": str(record.get("version") or ""),
        "base_commit": str(record.get("base_commit") or ""),
        "returncode": returncode,
        "passed": passed,
        "started_at": started_at,
        "finished_at": finished_at,
        "case_dir": str(case_dir),
        "plan_path": str(plan_path) if plan_path.exists() else "",
        "metadata_path": str(metadata_path) if metadata_path.exists() else "",
        "test_log_path": str(test_log_path) if test_log_path.exists() else "",
        "pytest_target_count": len(pytest_targets),
        "pytest_targets": pytest_targets,
        "case_python": metadata.get("case_python") or plan.get("case_python") or "",
    }


def write_summary(workspace_root: Path, batch_id: str, results: list[dict[str, Any]]) -> tuple[Path, Path]:
    batch_dir = workspace_root / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "batch_id": batch_id,
        "generated_at": utc_now(),
        "cases_total": len(results),
        "cases_passed": sum(1 for item in results if item["passed"]),
        "cases_failed": sum(1 for item in results if not item["passed"]),
        "pass_rate": (sum(1 for item in results if item["passed"]) / len(results)) if results else 0.0,
        "results": results,
    }
    summary_json_path = batch_dir / "summary.json"
    summary_md_path = batch_dir / "summary.md"
    summary_json_path.write_text(f"{json.dumps(summary, indent=2)}\n", encoding="utf-8")

    lines = [
        "# Real SWE Batch Summary",
        "",
        f"- batch_id: {batch_id}",
        f"- generated_at: {summary['generated_at']}",
        f"- cases_total: {summary['cases_total']}",
        f"- cases_passed: {summary['cases_passed']}",
        f"- cases_failed: {summary['cases_failed']}",
        f"- pass_rate: {summary['pass_rate']:.3f}",
        "",
        "| instance_id | repo | version | passed | returncode | pytest_target_count | case_dir | test_log |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in results:
        lines.append(
            "| {instance_id} | {repo} | {version} | {passed} | {returncode} | {pytest_target_count} | {case_dir} | {test_log_path} |".format(
                **item,
            ),
        )
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_json_path, summary_md_path


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    records = load_records(dataset_path, args.instance_id)

    results: list[dict[str, Any]] = []
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for instance_id in dict.fromkeys(args.instance_id):
        started_at = utc_now()
        command = build_case_command(args, dataset_path, workspace_root, instance_id)
        process = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
        finished_at = utc_now()

        case_dir = workspace_root / instance_id
        batch_log_path = case_dir / "batch_runner.log"
        batch_log_path.parent.mkdir(parents=True, exist_ok=True)
        batch_log_path.write_text(
            "COMMAND: " + " ".join(command) + "\n\nSTDOUT:\n" + process.stdout + "\nSTDERR:\n" + process.stderr,
            encoding="utf-8",
        )

        results.append(
            summarize_case(
                instance_id=instance_id,
                record=records[instance_id],
                case_dir=case_dir,
                returncode=process.returncode,
                started_at=started_at,
                finished_at=finished_at,
            ),
        )

        if process.returncode != 0 and not args.continue_on_error:
            break

    summary_json_path, summary_md_path = write_summary(workspace_root, batch_id, results)
    print(summary_json_path)
    print(summary_md_path)

    failed = any(not item["passed"] for item in results)
    if failed and not args.continue_on_error:
        return 1
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())