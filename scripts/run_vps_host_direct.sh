#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIO_PATH="${1:-${ROOT_DIR}/scenarios/vps_host_direct_single.json}"
export PYTHONPATH="${ROOT_DIR}/.deps:${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 -m openclaw_harness run \
  --scenario "${SCENARIO_PATH}" \
  --output-root "${ROOT_DIR}/out"
