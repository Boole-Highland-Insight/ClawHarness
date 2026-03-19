# OpenClaw Client Harness

Python harness for local OpenClaw gateway load tests.

This first version is aimed at the local WSL2 + Docker workflow:

- builds a local OpenClaw image from the current repo when needed
- starts an isolated gateway container on a dedicated localhost port
- drives `chat.send -> agent.wait -> chat.history` over the gateway WebSocket API
- writes run artifacts to `out/<timestamp>_<scenario>/`
- captures `latency.csv`, `summary.json`, `meta.json`, `docker_stats.csv`
- wires `pidstat`, `perf stat`, and `perf record` as optional collectors
- parses `pidstat` and `perf stat` raw outputs into structured CSV/JSON reports
- writes `environment.json` so each run records what the host could actually measure

The default scenarios use `/context list` so they do not depend on model keys.
The local Docker scenarios follow the recommended WSL policy: `docker stats` + `pidstat`
first, with `perf` left off by default until you move to a Linux VPS.

## Setup

Preferred path:

```bash
cd ~/openclaw/benchmarks/client-harness
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Fallback when `python3-venv` is not installed:

```bash
cd ~/openclaw/benchmarks/client-harness
python3 -m pip install --break-system-packages --target .deps "websockets>=14,<16"
export PYTHONPATH="$PWD/.deps:$PWD/src"
```

## Run

With a virtualenv:

```bash
source .venv/bin/activate
python -m openclaw_harness run --scenario scenarios/docker_single.json
python -m openclaw_harness run --scenario scenarios/docker_multi.json
```

With the `.deps` fallback:

```bash
cd ~/openclaw/benchmarks/client-harness
export PYTHONPATH="$PWD/.deps:$PWD/src"
python3 -m openclaw_harness run --scenario scenarios/docker_single.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/docker_multi.json --output-root out
```

VPS templates:

```bash
python3 -m openclaw_harness run --scenario scenarios/vps_host_direct_single.json --output-root out
python3 -m openclaw_harness run --scenario scenarios/vps_docker_single.json --output-root out
```

Helper scripts:

```bash
bash scripts/install_ubuntu_tools.sh
bash scripts/run_local_wsl.sh
bash scripts/run_vps_host_direct.sh scenarios/vps_host_direct_single.json
bash scripts/run_vps_docker.sh scenarios/vps_docker_single.json
```

## Notes

- The harness manages its own Docker container and does not use `~/.openclaw`.
- Container runtime state is stored under each run directory inside `out/`.
- Client device identity is stored at `.state/device.json`.
- `environment.json` captures OS/kernel/tool availability and the recommended collector mix.
- `host_direct` scenarios assume the harness runs on the same VPS as the gateway.
- `host_direct` tries to auto-discover `host_pid` from the configured listening port.
- Fill `runtime.host_pid` only if you want to override auto-discovery.
- If `pidstat` or `perf` are not installed, the harness marks those collectors as
  `skipped` and still completes the run.
- On WSL, `/usr/bin/perf` may exist but still be unusable if the kernel-matched perf
  binary is missing; `environment.json` marks that case explicitly.
- Parsed collector artifacts are written next to the raw files, for example
  `pidstat_cpu.csv`, `pidstat.summary.json`, and `perf_stat.summary.json`.
