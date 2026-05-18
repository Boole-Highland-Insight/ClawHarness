# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**ClawHarness** is a Python benchmark harness for OpenClaw gateway client/load testing. It drives the `chat.send -> agent.wait -> chat.history` WebSocket API flow, manages Docker containers for isolated gateway instances, and collects comprehensive system metrics (docker stats, pidstat, strace, perf, iostat, vmstat, npu-smi).

Target platforms: WSL2 + Docker, VPS direct hosting, VPS with Docker.

---

## Architecture & Key Modules

### Core Package: `src/openclaw_harness/`

**Entry Point: `cli.py`**
- Single subcommand: `run --scenario <file> --output-root <dir> [--keep-runtime]`
- Parses scenario JSON → loads config → calls `runner.run_scenario()`
- Exit code 0 on success

**Configuration: `scenario.py` + `task.py`**
- `ScenarioConfig` dataclass with nested configs:
  - `RuntimeConfig` - Docker/host settings, ports, container names
  - `ClientConfig` - Role, message, session handling, timeouts
  - `LoadConfig` - Concurrency, dispatch mode, staggering
  - `CollectorsConfig` - Metrics collection settings
  - `ArtifactsConfig` - Output retention strategy
- `load_scenario(path)` parses JSON, resolves `task_file` into `client.resolved_prompt`
- Task files: Markdown with YAML frontmatter (`---` delimiters); required fields: `id`, `name`, `category`, `prompt`
- **Key method**: `client.effective_message()` → returns `resolved_prompt` (from task) if set, else `message`

**Runtime Management: `runtime.py`**
- `DockerRuntimeManager`: Builds images, starts/stops containers, seeds `~/.openclaw` config
- `HostDirectRuntimeManager`: Connects to existing gateway running on host
- Both return `RuntimeInfo` with `url`, `host_pid`, `container_id`, `started_by_harness`
- Multi-OpenClaw support: `openclaw_num_per_instance > 1` runs multiple gateway processes in one container via bash subshell
- Auto-discovers `host_pid` via `docker top` → `ps` for collector attachment
- Health check: waits for `/healthz` endpoint before proceeding

**WebSocket Client: `gateway_client.py`**
- `GatewayClient.connect()` - Establishes WS connection, device auth handshake, protocol negotiation
- Methods: `send_chat()`, `wait_for_agent()`, `load_history()`
- Request-response protocol: each request gets UUID, awaited via `asyncio.Future`
- Connection uses `websockets` library, max_size=10MB

**Load Execution: `runner.py`**
- **Two dispatch modes**:
  - `worker_loop`: N concurrent workers, each loops M requests sequentially
  - `burst`: Single barrier fires all requests simultaneously; `max_in_flight` limits concurrency
- **Session resolution**:
  - `shared`: Single session key for all requests
  - `per_worker`: One session key per worker
  - `per_request`: Unique session key per request
- `execute_load()` returns list of latency records; written to `latency.csv`
- **Multi-instance**: Serial instance preparation → parallel load execution → serial finalization
- Writes: `scenario.resolved.json`, `preflight.json`, `meta.json`, `summary.json`, `latency.csv`

**Metrics Collection: `collectors.py`**
- `DockerStatsCollector` - Container CPU/memory via `docker stats --no-stream`
- `BackgroundCommandCollector` - Subprocess wrappers for `pidstat`, `strace`, `perf stat`, `perf record`, `iostat`, `vmstat`
- `NpuSmiCollector` - NPU utilization via `npu-smi info -t usages`
- All collectors have `start()` / `stop()` lifecycle; background threads
- Collectors auto-skip if tools unavailable

**Parsing: `parsers.py`**
- Parses raw collector output into structured CSV/JSON
- Output files: `*.summary.json`, `*.parsed.csv`

**Device Identity: `device_identity.py`**
- Stores device identity in `.state/device.json`
- Ed25519 keypair for device authentication
- Signs auth payloads with nonce challenge

---

## Data Flow

```
1. CLI parses: python -m openclaw_harness run --scenario scenarios/foo.json

2. load_scenario() → ScenarioConfig
   ├─ Reads JSON scenario file
   └─ If client.task_file: load_task() → client.resolved_prompt

3. run_scenario():
   ├─ probe_environment() → environment.json
   ├─ prepare_instance() × instance_num:
   │   ├─ runtime.start() → RuntimeInfo (url, host_pid)
   │   ├─ build_collectors() → [Collector]
   │   ├─ collectors[].start()
   │   └─ Write preflight.json
   │
   ├─ execute_load() × instance_num (parallel):
   │   ├─ asyncio.gather(worker tasks)
   │   ├─ Each worker: connect → (send_chat → wait_for_agent → load_history) × N
   │   └─ Collect latency records
   │
   └─ finalize_instance() × instance_num:
       ├─ collectors[].stop()
       ├─ runtime.stop()
       ├─ parse_collector_artifacts()
       ├─ write_latency_csv()
       ├─ build_summary()
       └─ Write summary.json, meta.json
```

---

## Latency Phases (Measured in `runner.execute_load()`)

| Phase | What | Notes |
|-------|------|-------|
| `connect` | `GatewayClient.connect()` | Per worker, NOT per request |
| `send` | `chat.send` API call | Submit prompt to gateway |
| `wait` | `agent.wait` | Main processing time |
| `history` | `chat.history` | Read back session messages |
| `total` | send → history | Excludes connect |

---

## Common Development Commands

### Environment Setup

```bash
cd ~/openclaw/benchmarks/client-harness
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Fallback (no venv):
```bash
python3 -m pip install --break-system-packages --target .deps "websockets>=14,<16"
export PYTHONPATH="$PWD/.deps:$PWD/src"
```

### Running Scenarios

```bash
# Basic smoke test (VPS Docker single)
python -m openclaw_harness run --scenario scenarios/vps/vps_docker_single.json --output-root out

# Burst mode: 100 requests, max_in_flight=100, session_pool_size=10
python -m openclaw_harness run --scenario scenarios/vllm/vps_docker_burst_task_01_100_session10.json --output-root out/burst_100

# Multi-OpenClaw smoke (1 container, 2 gateways on ports 19189, 19190)
python -m openclaw_harness run --scenario scenarios/vllm/vps_docker_single_multi_openclaw_smoke.json --output-root out/smoke_multi_openclaw

# Keep container after run for debugging
python -m openclaw_harness run --scenario scenarios/*.json --keep-runtime

# Using installed entry point
openclaw-harness run --scenario scenarios/*.json
```

### Scenario Categories

| Location | Purpose |
|----------|--------|
| `scenarios/vps/vps_docker_*` | VPS Docker scenarios |
| `scenarios/vps/vps_host_direct_*` | VPS direct (no Docker) |
| `scenarios/vllm/*` | vLLM integration, burst mode |
| `scenarios/wsl_docker/docker_*` | WSL2 Docker scenarios |

---

## Key Configuration Patterns

### Burst Mode with Session Pooling

```json
{
  "load": {
    "dispatch_mode": "burst",
    "total_requests": 100,
    "max_in_flight": 100,
    "concurrency": 1,
    "requests_per_worker": 1
  },
  "client": {
    "session_mode": "per_worker",
    "session_pool_size": 10
  }
}
```

**Semantics**: 100 requests fire simultaneously, reusing 10 session keys round-robin.

### Multi-OpenClaw in Single Container

```json
{
  "runtime": {
    "instance_num": 1,
    "openclaw_num_per_instance": 2,
    "host_port": 19189,
    "container_port": 18789
  }
}
```

**Result**: Two gateways on ports 19189 and 19190, each with isolated `~/.openclaw/openclaw-XX/` state.

### Multi-Instance Parallel Execution

```json
{
  "runtime": {
    "instance_num": 4,
    "host_port": 19189  /* base port, +stride per instance */
  }
}
```

**Result**: 4 containers, ports 19189, 19190, 19191, 19192; load runs in parallel;
aggregated summary at output root, per-instance summaries in `instances/instance-XX/`.

---

## Output Artifacts

```
out/<timestamp>_<scenario-name>/
├── scenario.resolved.json  # Final config with resolved task prompt
├── preflight.json         # Pre-load: URL, host_pid, collector targets
├── meta.json             # Full metadata, runtime info, environment
├── summary.json          # Aggregated latency summary
├── latency.csv           # Per-request latency breakdown
├── docker_stats.csv      # Container metrics (if enabled)
├── pidstat.log           # Process metrics (if enabled)
├── perf_stat.csv         # Perf events (if enabled)
├── perf_stat.summary.json
├── iostat.log
├── vmstat.log
├── npu_smi.log
└── runtime/
    ├── docker-build.log
    ├── docker-logs.txt
    └── config/           # Seeded ~.openclaw config
```

**With `artifacts.summary_only: true`**: Only summary files retained.

---

## Default Values

| Field | Default |
|-------|--------|
| `load.dispatch_mode` | `worker_loop` |
| `client.session_mode` | `per_worker` |
| `runtime.host_port` | 19189 |
| `runtime.container_port` | 18789 |
| `runtime.network_mode` | `bridge` |
| `client.message` | `/context list` |
| `client.wait_timeout_ms` | 15000 |
| `client.send_timeout_ms` | 15000 |
| `collectors.docker_stats.enabled` | true |
| `collectors.pidstat.enabled` | true |
| `collectors.strace.enabled` | false |
| `collectors.perf_stat.enabled` | true |
| `collectors.perf_record.enabled` | false |

---

## Notes

- **CoClaw** dashboard project has been split into separate `../CoClaw/` repo
- Device identity stored in `.state/device.json`
- `environment.json` records OS/capabilities; unavailable collectors marked as `skipped`
- Preflight file contains collector attachment targets; warnings if auto-discovery fails
- For WSL2: perf often unavailable due to kernel binary mismatch
- Default WSL strategy: `docker_stats` + `pidstat` + `iostat`; `perf` and `strace` off by default

---

## Related Projects

- **CoClaw**: `../CoClaw/` - Dashboard for monitoring instances/containers
  - Backend: FastAPI on port 18082
  - Frontend: Vite + React on port 15173
  - Start: `./start-dev.sh` from `../CoClaw/`
