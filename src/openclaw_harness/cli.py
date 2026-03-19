from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .runner import run_scenario
from .scenario import load_scenario


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw local benchmark harness")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run one benchmark scenario")
    run_parser.add_argument("--scenario", required=True, help="path to a scenario JSON file")
    run_parser.add_argument("--output-root", default="out", help="directory for run artifacts")
    run_parser.add_argument(
        "--keep-runtime",
        action="store_true",
        help="leave the Docker container running after the benchmark finishes",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        scenario_path = Path(args.scenario).resolve()
        output_root = Path(args.output_root).resolve()
        scenario = load_scenario(scenario_path)
        run_dir = asyncio.run(run_scenario(scenario, output_root=output_root, keep_runtime=args.keep_runtime))
        print(run_dir)
        return 0
    parser.error(f"unsupported command: {args.command}")
    return 2
