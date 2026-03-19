#!/usr/bin/env bash
set -euo pipefail

echo "Detected host:"
uname -a
echo

echo "Installing pidstat via sysstat..."
sudo apt update
sudo apt install -y sysstat

echo
echo "Attempting to install perf helper packages..."
if sudo apt install -y linux-tools-common linux-tools-generic linux-cloud-tools-generic; then
  echo "Installed generic linux-tools packages."
else
  cat <<'EOF'
linux-tools packages were not fully installed.
This is expected on some WSL kernels, especially microsoft-standard-WSL2 builds.
If perf is still unavailable after this, keep using pidstat locally and collect perf data on the VPS.
EOF
fi

echo
echo "Verification:"
command -v pidstat || true
command -v perf || true
pidstat -V || true
PERF_OUTPUT="$(perf --version 2>&1 || true)"
printf '%s\n' "${PERF_OUTPUT}"

if grep -qi "perf not found for kernel" <<<"${PERF_OUTPUT}"; then
  cat <<'EOF'

perf wrapper is present, but there is no kernel-matched perf binary for the current WSL kernel.
This is common on microsoft-standard-WSL2 kernels.

Recommendation:
- keep using pidstat locally
- keep docker stats locally for container telemetry
- collect perf stat / perf record on the Linux VPS
EOF
fi
