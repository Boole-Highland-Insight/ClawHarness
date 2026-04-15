#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/out-log"
OUT_FILE="${OUT_DIR}/npu_usage.log"
INTERVAL="1"
APPEND="false"

usage() {
  cat <<'EOF'
Usage:
  scripts/log_npu_usage.sh [--interval SECONDS] [--output PATH] [--append] [NPU_ID ...]

Examples:
  scripts/log_npu_usage.sh
  scripts/log_npu_usage.sh 0 1 2 3
  scripts/log_npu_usage.sh --interval 2 --output /tmp/npu_usage.log 0 1
EOF
}

trim() {
  local value="${1:-}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "${value}"
}

discover_npu_ids() {
  local listing
  listing="$(
    {
      npu-smi info -l 2>/dev/null || true
      npu-smi info 2>/dev/null || true
    } | sed '/^[[:space:]]*$/d'
  )"

  if [[ -z "${listing}" ]]; then
    return 1
  fi

  printf '%s\n' "${listing}" \
    | awk -F: '
        /NPU ID/ {
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2)
          if ($2 != "" && !seen[$2]++) {
            print $2
          }
        }
      '
}

collect_once() {
  local ids=("$@")
  local id

  date -Is
  for id in "${ids[@]}"; do
    echo "Requested NPU Index:${id}"
    npu-smi info -t usages -i "${id}" 2>&1 | awk -F: '
      /NPU ID|Chip Count|HBM Usage Rate\(%\)|NPU Utilization\(%\)|Aicore Usage Rate\(%\)|Aivector Usage Rate\(%\)|Aicpu Usage Rate\(%\)|Ctrlcpu Usage Rate\(%\)|Chip ID/ {
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2)
        print $1 ":" $2
      }
    '
    echo
  done
}

POSITIONAL_IDS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval)
      if [[ $# -lt 2 ]]; then
        echo "missing value for --interval" >&2
        exit 1
      fi
      INTERVAL="$(trim "$2")"
      shift 2
      ;;
    --output)
      if [[ $# -lt 2 ]]; then
        echo "missing value for --output" >&2
        exit 1
      fi
      OUT_FILE="$(trim "$2")"
      shift 2
      ;;
    --append)
      APPEND="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      POSITIONAL_IDS+=("$(trim "$1")")
      shift
      ;;
  esac
done

if ! [[ "${INTERVAL}" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
  echo "--interval must be a positive number" >&2
  exit 1
fi

if ! command -v npu-smi >/dev/null 2>&1; then
  echo "npu-smi not found in PATH" >&2
  exit 1
fi

if [[ "${OUT_FILE}" != /* ]]; then
  OUT_FILE="${ROOT_DIR}/${OUT_FILE}"
fi
OUT_DIR="$(dirname "${OUT_FILE}")"
mkdir -p "${OUT_DIR}"

NPU_IDS=()
if [[ ${#POSITIONAL_IDS[@]} -gt 0 ]]; then
  NPU_IDS=("${POSITIONAL_IDS[@]}")
else
  mapfile -t NPU_IDS < <(discover_npu_ids || true)
fi

if [[ ${#NPU_IDS[@]} -eq 0 ]]; then
  echo "failed to discover NPU IDs automatically; pass them explicitly, for example: scripts/log_npu_usage.sh 0 1" >&2
  exit 1
fi

for id in "${NPU_IDS[@]}"; do
  if ! [[ "${id}" =~ ^[0-9]+$ ]]; then
    echo "invalid NPU ID: ${id}" >&2
    exit 1
  fi
done

echo "Logging NPU usage every ${INTERVAL}s for IDs: ${NPU_IDS[*]}" >&2
echo "Output file: ${OUT_FILE}" >&2

if [[ "${APPEND}" == "true" ]]; then
  while true; do
    collect_once "${NPU_IDS[@]}"
    sleep "${INTERVAL}"
  done | tee -a "${OUT_FILE}"
else
  while true; do
    collect_once "${NPU_IDS[@]}"
    sleep "${INTERVAL}"
  done | tee "${OUT_FILE}"
fi
