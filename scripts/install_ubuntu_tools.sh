#!/usr/bin/env bash
set -euo pipefail

install_sysstat() {
  if command -v apt >/dev/null 2>&1; then
    sudo apt update
    sudo apt install -y sysstat
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y sysstat
  else
    echo "Unsupported package manager: need apt or dnf." >&2
    exit 1
  fi
}

install_perf_helpers() {
  if command -v apt >/dev/null 2>&1; then
    if sudo apt install -y linux-tools-common linux-tools-generic linux-cloud-tools-generic; then
      echo "Installed generic linux-tools packages."
      return 0
    fi
  elif command -v dnf >/dev/null 2>&1; then
    if sudo dnf install -y perf; then
      echo "Installed perf package."
      return 0
    fi
  else
    echo "Unsupported package manager: need apt or dnf." >&2
    exit 1
  fi

  return 1
}

echo "Detected host:"
uname -a
echo

echo "Installing pidstat/iostat via sysstat..."
install_sysstat

echo
echo "Attempting to install perf helper packages..."
if install_perf_helpers; then
  :
else
  cat <<'EOF'
perf packages were not fully installed.
This is expected on some kernels or minimal images.
If perf is still unavailable after this, keep using pidstat locally and collect perf data on the VPS.
EOF
fi

echo
echo "Verification:"
command -v pidstat || true
command -v iostat || true
command -v perf || true
pidstat -V || true
iostat -V || true
PERF_OUTPUT="$(perf --version 2>&1 || true)"
printf '%s\n' "${PERF_OUTPUT}"

if grep -qi "perf not found for kernel" <<<"${PERF_OUTPUT}"; then
  cat <<'EOF'

perf wrapper is present, but there is no kernel-matched perf binary for the current WSL kernel.
This is common on microsoft-standard-WSL2 kernels.

Recommendation:
- keep using pidstat + iostat locally
- keep docker stats locally for container telemetry
- collect perf stat / perf record on the Linux VPS
EOF
fi
