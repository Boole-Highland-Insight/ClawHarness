#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/.deps:${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 -m openclaw_harness run \
  --scenario "${ROOT_DIR}/scenarios/docker_single.json" \
  --output-root "${ROOT_DIR}/out"

python3 -m openclaw_harness run \
  --scenario "${ROOT_DIR}/scenarios/docker_multi.json" \
  --output-root "${ROOT_DIR}/out"
