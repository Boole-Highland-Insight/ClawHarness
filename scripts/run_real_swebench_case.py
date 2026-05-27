#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = Path(
    "/root/ziruiw/ascend_fabric/multi_replica_20260426T075224Z/ai_profiler_cleaning/post7_datasets/swebench/data/test-00000-of-00001.parquet",
)
DEFAULT_WORKSPACE_ROOT = REPO_ROOT / ".state" / "swebench_real"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a real SWE-bench case checkout and optionally run its target pytest tests.",
    )
    parser.add_argument("--instance-id", required=True, help="SWE-bench instance id to materialize.")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the local SWE-bench parquet file.",
    )
    parser.add_argument(
        "--workspace-root",
        default=str(DEFAULT_WORKSPACE_ROOT),
        help="Root directory for prepared case workspaces.",
    )
    parser.add_argument(
        "--source-repo",
        default="",
        help="Optional local git repo to clone from instead of GitHub.",
    )
    parser.add_argument(
        "--candidate-patch",
        default="",
        help="Optional patch file to apply after test_patch and before running tests.",
    )
    parser.add_argument(
        "--apply-gold-patch",
        action="store_true",
        help="Apply the reference fix patch from the SWE-bench row before running tests.",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run pytest against the selected test targets after preparing the checkout.",
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
        help="Limit the number of pytest targets passed to pytest.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Only emit the checkout/test plan JSON without cloning or running tests.",
    )
    parser.add_argument(
        "--python-bin",
        default="",
        help="Optional Python interpreter to use for the case test environment.",
    )
    parser.add_argument(
        "--case-venv-name",
        default=".venv_case",
        help="Directory name for the per-case virtual environment under the case workspace.",
    )
    return parser.parse_args()


def load_record(dataset_path: Path, instance_id: str) -> dict[str, Any]:
    import pyarrow.parquet as pq

    table = pq.read_table(
        dataset_path,
        filters=[("instance_id", "=", instance_id)],
        columns=[
            "repo",
            "instance_id",
            "base_commit",
            "environment_setup_commit",
            "patch",
            "test_patch",
            "problem_statement",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
            "version",
        ],
    )
    rows = table.to_pylist()
    if not rows:
        raise ValueError(f"instance id not found in dataset: {instance_id}")
    return rows[0]


def parse_test_list(raw_value: Any) -> list[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    value = str(raw_value).strip()
    if not value:
        return []
    loaded = json.loads(value)
    if not isinstance(loaded, list):
        raise ValueError(f"expected list-encoded JSON, got: {value[:120]}")
    return [str(item).strip() for item in loaded if str(item).strip()]


def repo_url(repo_name: str) -> str:
    return f"https://github.com/{repo_name}.git"


def list_cached_repo_clones(record: dict[str, Any], exclude_case_dir: Path) -> list[Path]:
    state_dir = REPO_ROOT / ".state"
    if not state_dir.exists():
        return []
    target_repo = str(record.get("repo") or "")
    target_url = repo_url(target_repo)
    matches: list[Path] = []
    for candidate in sorted(state_dir.glob("swebench_real*/**/repo")):
        if exclude_case_dir in candidate.parents:
            continue
        git_dir = candidate / ".git"
        if not git_dir.exists():
            continue
        config_path = git_dir / "config"
        if not config_path.exists():
            continue
        config_text = config_path.read_text(encoding="utf-8", errors="ignore")
        if target_url in config_text or target_repo in config_text:
            matches.append(candidate)
    return matches


def resolve_python_bin(args: argparse.Namespace, record: dict[str, Any]) -> str:
    if args.python_bin.strip():
        return str(Path(args.python_bin).resolve())

    repo_name = str(record.get("repo") or "")
    version = str(record.get("version") or "")
    candidates: list[str] = []

    if repo_name == "astropy/astropy" and version.startswith(("4.", "5.")):
        candidates.extend([
            "/root/.local/bin/python3.10",
            "/root/.local/bin/python3.11",
            "/usr/bin/python3.9",
        ])

    candidates.extend([sys.executable, "/root/.local/bin/python3.10", "/root/.local/bin/python3.11", "/usr/bin/python3.9"])

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        resolved = shutil.which(candidate) if os.sep not in candidate else candidate
        if resolved and Path(resolved).exists():
            return str(Path(resolved).resolve())

    raise RuntimeError("no usable Python interpreter found for case environment")


def run_command(command: list[str], *, cwd: Path | None = None, log_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(
            "COMMAND: " + " ".join(command) + "\n\nSTDOUT:\n" + result.stdout + "\nSTDERR:\n" + result.stderr,
            encoding="utf-8",
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip() or result.stdout.strip()}",
        )
    return result


def git_network_command(*args: str) -> list[str]:
    return ["git", "-c", "http.version=HTTP/1.1", *args]


def fresh_checkout_issues(repo_dir: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "failed to inspect checkout status")
    return [line for line in result.stdout.splitlines() if line.strip()]


def validate_fresh_checkout(repo_dir: Path) -> None:
    issues = fresh_checkout_issues(repo_dir)
    if issues:
        preview = "\n".join(issues[:20])
        raise RuntimeError(
            "fresh checkout is incomplete or dirty; likely missing git objects or an unusable cached clone:\n"
            f"{preview}",
        )


def prime_checkout(repo_dir: Path, base_commit: str, *, fetch_remote: bool, log_path: Path) -> None:
    run_command(["git", "reset", "--hard", "HEAD"], cwd=repo_dir)
    run_command(["git", "clean", "-fdx"], cwd=repo_dir)
    if fetch_remote:
        try:
            run_command(git_network_command("fetch", "--all", "--tags", "--prune"), cwd=repo_dir, log_path=log_path)
        except RuntimeError:
            pass
    run_command(["git", "checkout", "--detach", base_commit], cwd=repo_dir)
    run_command(["git", "reset", "--hard", "HEAD"], cwd=repo_dir)
    run_command(["git", "clean", "-fdx"], cwd=repo_dir)
    validate_fresh_checkout(repo_dir)


def ensure_checkout(case_dir: Path, record: dict[str, Any], source_repo: Path | None) -> Path:
    repo_dir = case_dir / "repo"
    clone_log = case_dir / "clone.log"
    base_commit = str(record["base_commit"])
    if repo_dir.exists():
        try:
            prime_checkout(repo_dir, base_commit, fetch_remote=source_repo is None, log_path=clone_log)
            return repo_dir
        except RuntimeError:
            shutil.rmtree(repo_dir)

    clone_errors: list[str] = []
    clone_sources: list[tuple[str, str, Path]] = []
    if source_repo is not None:
        clone_sources.append(("source", str(source_repo), clone_log))
    else:
        clone_sources.append(("remote", repo_url(str(record["repo"])), clone_log))
        for index, cached_repo in enumerate(list_cached_repo_clones(record, case_dir), start=1):
            clone_sources.append(("cache", str(cached_repo), case_dir / f"clone-cache-{index}.log"))

    for source_kind, source_value, source_log in clone_sources:
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        try:
            if source_kind == "remote":
                run_command(git_network_command("clone", source_value, str(repo_dir)), log_path=source_log)
            else:
                run_command(["git", "clone", source_value, str(repo_dir)], log_path=source_log)
            prime_checkout(repo_dir, base_commit, fetch_remote=source_kind == "remote", log_path=source_log)
            return repo_dir
        except RuntimeError as clone_error:
            clone_errors.append(f"{source_kind} {source_value}: {clone_error}")
            if repo_dir.exists():
                shutil.rmtree(repo_dir)

    raise RuntimeError("failed to prepare checkout:\n" + "\n".join(clone_errors))


def apply_patch(repo_dir: Path, patch_text: str, *, label: str, log_path: Path) -> None:
    if not patch_text.strip():
        return
    process = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", "-"],
        cwd=repo_dir,
        input=patch_text,
        text=True,
        capture_output=True,
        check=False,
    )
    log_path.write_text(
        f"LABEL: {label}\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}",
        encoding="utf-8",
    )
    if process.returncode != 0:
        raise RuntimeError(f"failed to apply {label}: {process.stderr.strip() or process.stdout.strip()}")


def build_test_targets(record: dict[str, Any], include_pass_to_pass: bool, max_tests: int) -> list[str]:
    targets = parse_test_list(record.get("FAIL_TO_PASS"))
    if include_pass_to_pass:
        targets.extend(parse_test_list(record.get("PASS_TO_PASS")))
    deduped = list(dict.fromkeys(targets))
    if max_tests > 0:
        return deduped[:max_tests]
    return deduped


def build_plan(args: argparse.Namespace, record: dict[str, Any], case_dir: Path) -> dict[str, Any]:
    python_bin = resolve_python_bin(args, record)
    case_venv_dir = case_dir / args.case_venv_name
    case_python = case_venv_dir / "bin" / "python"
    targets = build_test_targets(record, args.include_pass_to_pass, args.max_tests)
    pytest_command = [str(case_python), "-m", "pytest", "-q", *targets] if targets else []
    return {
        "instance_id": record["instance_id"],
        "repo": record["repo"],
        "base_commit": record["base_commit"],
        "environment_setup_commit": record.get("environment_setup_commit") or "",
        "version": record.get("version") or "",
        "case_dir": str(case_dir),
        "repo_dir": str(case_dir / "repo"),
        "clone_url": repo_url(str(record["repo"])),
        "source_repo": args.source_repo,
        "apply_test_patch": bool(str(record.get("test_patch") or "").strip()),
        "apply_gold_patch": bool(args.apply_gold_patch),
        "candidate_patch": args.candidate_patch,
        "python_executable": python_bin,
        "case_venv_dir": str(case_venv_dir),
        "case_python": str(case_python),
        "pytest_targets": targets,
        "pytest_command": pytest_command,
    }


def run_logged(command: list[str], *, cwd: Path, log_path: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "COMMAND: " + " ".join(command) + "\n\nSTDOUT:\n" + result.stdout + "\nSTDERR:\n" + result.stderr,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip() or result.stdout.strip()}",
        )


def python_version_tuple(python_bin: str | Path) -> tuple[int, int]:
    result = subprocess.run(
        [str(python_bin), "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"failed to inspect interpreter: {python_bin}")
    major_text, minor_text = result.stdout.strip().split(".", 1)
    return int(major_text), int(minor_text)


def bootstrap_case_environment(case_dir: Path, repo_dir: Path, plan: dict[str, Any]) -> Path:
    case_venv_dir = Path(plan["case_venv_dir"])
    case_python = Path(plan["case_python"])
    bootstrap_dir = case_dir / "bootstrap_logs"
    python_bin = str(plan["python_executable"])

    if case_python.exists():
        target_version = python_version_tuple(python_bin)
        current_version = python_version_tuple(case_python)
        if current_version != target_version:
            shutil.rmtree(case_venv_dir)

    if not case_python.exists():
        run_logged([python_bin, "-m", "venv", str(case_venv_dir)], cwd=case_dir, log_path=bootstrap_dir / "01-create-venv.log")

    pip_cmd = [str(case_python), "-m", "pip"]
    run_logged(
        [*pip_cmd, "install", "-U", "pip", "setuptools<70", "wheel", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
        cwd=repo_dir,
        log_path=bootstrap_dir / "02-bootstrap-pip.log",
    )

    repo_name = str(plan["repo"])
    repo_bootstrap_packages: list[str] = []
    if repo_name == "astropy/astropy":
        repo_bootstrap_packages = [
            "cython==0.29.22",
            "oldest-supported-numpy",
            "extension-helpers",
            "setuptools_scm",
            "numpy<2",
        ]

    if repo_bootstrap_packages:
        run_logged(
            [*pip_cmd, "install", *repo_bootstrap_packages, "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
            cwd=repo_dir,
            log_path=bootstrap_dir / "03-repo-bootstrap.log",
        )

    run_logged(
        [*pip_cmd, "install", "-e", ".[test]", "--no-build-isolation", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"],
        cwd=repo_dir,
        log_path=bootstrap_dir / "04-install-editable.log",
    )
    return case_python


def build_test_environment(case_dir: Path, plan: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    repo_name = str(plan["repo"])

    if repo_name == "astropy/astropy":
        startup_dir = case_dir / ".test_env"
        startup_dir.mkdir(parents=True, exist_ok=True)
        sitecustomize_path = startup_dir / "sitecustomize.py"
        sitecustomize_path.write_text(
            "from astropy.utils import iers\n"
            "iers.conf.auto_download = False\n"
            "iers.conf.auto_max_age = None\n",
            encoding="utf-8",
        )

        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            str(startup_dir)
            if not existing_pythonpath
            else str(startup_dir) + os.pathsep + existing_pythonpath
        )

    return env


def main() -> int:
    args = parse_args()
    dataset_path = Path(args.dataset).resolve()
    workspace_root = Path(args.workspace_root).resolve()
    record = load_record(dataset_path, args.instance_id)
    case_dir = workspace_root / str(record["instance_id"])
    case_dir.mkdir(parents=True, exist_ok=True)
    plan = build_plan(args, record, case_dir)
    plan_path = case_dir / "plan.json"
    plan_path.write_text(f"{json.dumps(plan, indent=2)}\n", encoding="utf-8")

    if args.plan_only:
        print(plan_path)
        return 0

    source_repo = Path(args.source_repo).resolve() if args.source_repo.strip() else None
    repo_dir = ensure_checkout(case_dir, record, source_repo)
    apply_patch(repo_dir, str(record.get("test_patch") or ""), label="test_patch", log_path=case_dir / "test_patch.apply.log")

    if args.apply_gold_patch:
        apply_patch(repo_dir, str(record.get("patch") or ""), label="gold_patch", log_path=case_dir / "gold_patch.apply.log")
    if args.candidate_patch.strip():
        candidate_patch_path = Path(args.candidate_patch).resolve()
        apply_patch(
            repo_dir,
            candidate_patch_path.read_text(encoding="utf-8"),
            label="candidate_patch",
            log_path=case_dir / "candidate_patch.apply.log",
        )

    metadata = {
        **plan,
        "repo_dir": str(repo_dir),
        "problem_statement": str(record.get("problem_statement") or ""),
    }
    metadata_path = case_dir / "metadata.json"
    metadata_path.write_text(f"{json.dumps(metadata, indent=2)}\n", encoding="utf-8")

    if not args.run_tests:
        print(metadata_path)
        return 0

    case_python = bootstrap_case_environment(case_dir, repo_dir, metadata)
    metadata["case_python"] = str(case_python)
    metadata["pytest_command"] = [str(case_python), "-m", "pytest", "-q", *metadata["pytest_targets"]]
    metadata_path.write_text(f"{json.dumps(metadata, indent=2)}\n", encoding="utf-8")

    pytest_command = metadata["pytest_command"]
    if not pytest_command:
        raise ValueError("no pytest targets available for this instance")
    test_log = case_dir / "test.log"
    test_env = build_test_environment(case_dir, metadata)
    result = subprocess.run(pytest_command, cwd=repo_dir, env=test_env, text=True, capture_output=True, check=False)
    test_log.write_text(
        "COMMAND: " + " ".join(pytest_command) + "\n\nSTDOUT:\n" + result.stdout + "\nSTDERR:\n" + result.stderr,
        encoding="utf-8",
    )
    print(test_log)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())